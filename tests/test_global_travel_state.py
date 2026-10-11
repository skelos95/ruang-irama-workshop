"""Execute emitted Travel controllers with native engine boundaries stubbed.

The complete controller bodies are interpreted, including the bounded Attach
loop. These checks cover controller state and dispatch, not native movement or
death timing.
"""

from __future__ import annotations

import re
import unittest

from tools import validate_global_runtime as runtime
from tools import validate_workshop as semantic
from tests.test_global_controller_execution import GeneratedControllerEvaluator, RUNTIME


class RuleAborted(Exception):
    """Abort terminates the current emitted subroutine, including nested blocks."""


class TravelControllerEvaluator(GeneratedControllerEvaluator):
    """Extend the shared interpreter locally with structured For/If execution."""

    ENGINE_ACTIONS = (
        "CallSubroutine(", "AllowButton(", "DestroyHUDText(",
        "DestroyIn-WorldText(", "EnableNameplates(", "DetachPlayers(",
        "AttachPlayers(", "SmallMessage(", "ClearStatus(",
        "SetDamageReceived(", "Kill(",
    )

    def __init__(self, source):
        super().__init__(source)
        self.programs = {}

    def call(self, name, arguments):
        if name == "IndexOfArrayValue":
            return arguments[0].index(arguments[1]) if arguments[1] in arguments[0] else -1
        if name == "AllPlayers":
            return list(self.players)
        if name == "HeroOf":
            return self.players[arguments[0]]["hero"]
        return super().call(name, arguments)

    def latch_index(self, prefix):
        pattern = re.escape(f"Global.TriggerPlayer.{self.state_field}") + r"\[(\d+)\]\s*=\s*0;"
        return int(re.search(pattern, self.controller(prefix).body)[1])

    def program(self, rule):
        if rule.body in self.programs:
            return self.programs[rule.body]
        actions = semantic.rule_block(rule, "actions") or ""
        actions = re.sub(r'(?m)^[ \t]*"(?:\\.|[^"\\])*"[ \t]*(?:\r?\n|$)', "", actions)
        statements = [re.sub(r"\s+", "", raw)
                      for raw in semantic.split_top_level(actions, ";") if raw.strip()]

        def block(index):
            result = []
            while index < len(statements):
                statement = statements[index]
                if statement == "End" or statement == "Else" or statement.startswith("ElseIf("):
                    return result, index
                if statement.startswith("If("):
                    branches = []
                    condition = statement[3:-1]
                    while True:
                        body, index = block(index + 1)
                        branches.append((condition, body))
                        if index >= len(statements):
                            raise AssertionError("unclosed emitted If")
                        boundary = statements[index]
                        if boundary == "End":
                            break
                        if boundary == "Else":
                            condition = None
                        elif boundary.startswith("ElseIf("):
                            condition = boundary[7:-1]
                        else:
                            raise AssertionError(f"unexpected emitted branch {boundary}")
                    result.append(("if", branches))
                elif statement.startswith("ForPlayerVariable("):
                    arguments = semantic.split_top_level(statement[len("ForPlayerVariable("):-1], ",")
                    if len(arguments) != 5:
                        raise AssertionError("expected five emitted For Player Variable arguments")
                    body, index = block(index + 1)
                    if index >= len(statements) or statements[index] != "End":
                        raise AssertionError("unclosed emitted For Player Variable")
                    result.append(("for", arguments, body))
                else:
                    result.append(("action", statement))
                index += 1
            return result, index

        program, end = block(0)
        if end != len(statements):
            raise AssertionError("unexpected emitted block boundary")
        self.programs[rule.body] = program
        return program

    def execute(self, rule):
        def execute_block(program):
            for node in program:
                if node[0] == "if":
                    for condition, branch in node[1]:
                        if condition is None or self.expression(condition):
                            execute_block(branch)
                            break
                elif node[0] == "for":
                    owner, variable, start, stop, step = node[1]
                    identity = self.expression(owner)
                    variable = self.expression(variable)
                    for value in range(int(self.expression(start)), int(self.expression(stop)),
                                       int(self.expression(step))):
                        self.players[identity][variable] = value
                        execute_block(node[2])
                else:
                    statement = node[1]
                    if statement == "Abort" or (statement.startswith("AbortIf(") and
                                                 self.expression(statement[8:-1])):
                        raise RuleAborted
                    if statement.startswith("AbortIf("):
                        continue
                    match = re.fullmatch(r"(Global\.\w+(?:\.\w+)?(?:\[.*\])?)([+\-*/%]?=)(?!=)(.+)",
                                         statement)
                    if match:
                        value = self.expression(match[3])
                        if match[2] != "=":
                            value = self.expression(f"{match[1]}{match[2][0]}({match[3]})")
                        self.assign(match[1], value)
                    elif statement.startswith(self.ENGINE_ACTIONS):
                        self.native_calls.append((self.globals["TriggerPlayer"], statement, self.now))
                    else:
                        raise AssertionError(f"unsupported emitted action {statement}")

        try:
            execute_block(self.program(rule))
        except RuleAborted:
            pass


class GlobalTravelStateTests(unittest.TestCase):
    INVALID_STATES = ((False, True), (True, False), (False, False))

    def model(self, **changes):
        model = TravelControllerEvaluator(runtime.english(RUNTIME.read_text(encoding="utf-8")))
        model.now = 10
        defaults = dict(
            CrouchTravelActive=True, TravelCommand=0, TravelCursor=0,
            TravelTargets=["target"], TravelTargetCandidate="target",
            TravelText=None, TravelTextTarget=None, MenuHud=None,
            LockedTravelType=-1, LockedTravelTarget=None,
            InspectionText=None, InspectionTarget=None, InspectionTargets=[],
            InspectionActive=False, NameplatesDisabled=False,
            TravelAttachmentActive=False, TravelAttachmentTarget=None,
            LuckPrivacyActive=False, NextSuicideTime=0, hero="Mercy",
            held={"Crouch", "Interact"},
        )
        defaults.update(changes)
        state = model.add_player("viewer", **defaults)
        model.add_player("target", TravelAttachmentActive=False,
                         TravelAttachmentTarget=None, hero="Reinhardt")
        state[model.state_field] = [0] * (max(model.latch_index("19c"), model.latch_index("19e")) + 1)
        model.globals.update(MenuHudIds=[0, 0], InspectionTextIds=[0, 0],
                             TemporaryTextOwners=["viewer"], TemporaryTravelTextIds=[0])
        return model, state

    @staticmethod
    def calls(model):
        return [call[1] for call in model.native_calls]

    def test_dead_or_unspawned_owner_cannot_create_any_travel_command(self):
        for alive, spawned in self.INVALID_STATES:
            for button in ("PrimaryFire", "SecondaryFire", "Interact"):
                with self.subTest(alive=alive, spawned=spawned, button=button):
                    model, state = self.model(alive=alive, spawned=spawned,
                                              held={"Crouch", button})
                    model.tick("viewer", "19a")
                    self.assertEqual(state["TravelCommand"], 0)
                    self.assertEqual(state["TravelCursor"], 0)
                    self.assertEqual(model.native_calls, [])

    def test_dead_or_unspawned_owner_cannot_navigate_a_queued_command(self):
        for alive, spawned in self.INVALID_STATES:
            for command in (1, 2):
                for cursor in range(5):
                    with self.subTest(alive=alive, spawned=spawned, command=command, cursor=cursor):
                        model, state = self.model(alive=alive, spawned=spawned,
                                                  TravelCommand=command, TravelCursor=cursor)
                        model.tick("viewer", "19c")
                        self.assertEqual(state["TravelCursor"], cursor)
                        self.assertEqual(state["TravelCommand"], command)
                        self.assertEqual(state[model.state_field][model.latch_index("19c")], 0)
                        self.assertEqual(model.native_calls, [])

    def test_dead_or_unspawned_owner_cannot_apply_any_of_the_five_pages(self):
        for alive, spawned in self.INVALID_STATES:
            for cursor in range(5):
                with self.subTest(alive=alive, spawned=spawned, cursor=cursor):
                    model, state = self.model(alive=alive, spawned=spawned,
                                              TravelCommand=3, TravelCursor=cursor)
                    before = dict(state)
                    model.tick("viewer", "19e")
                    self.assertEqual(state[model.state_field][model.latch_index("19e")], 0)
                    self.assertEqual({k: value for k, value in state.items() if k != model.state_field},
                                     {k: value for k, value in before.items() if k != model.state_field})
                    self.assertEqual(model.native_calls, [])

    def test_invalidated_owner_rearms_navigation_and_apply_press_latches(self):
        for alive, spawned in self.INVALID_STATES:
            for prefix, command in (("19c", 1), ("19e", 3)):
                with self.subTest(alive=alive, spawned=spawned, prefix=prefix):
                    model, state = self.model(alive=alive, spawned=spawned, TravelCommand=command)
                    state[model.state_field][model.latch_index(prefix)] = 1
                    model.tick("viewer", prefix)
                    self.assertEqual(state[model.state_field][model.latch_index(prefix)], 0)
                    self.assertEqual(model.native_calls, [])

    def test_invalid_owner_still_reaches_cleanup_after_rejected_queued_action(self):
        for alive, spawned in self.INVALID_STATES:
            for command in (1, 3):
                with self.subTest(alive=alive, spawned=spawned, command=command):
                    model, state = self.model(
                        alive=alive, spawned=spawned, TravelCommand=command,
                        TravelCursor=3, MenuHud=101, TravelText=202,
                        TravelTextTarget="target", InspectionText=303,
                        InspectionTarget="target", InspectionTargets=["target"],
                        InspectionActive=True, NameplatesDisabled=True,
                        LockedTravelType=3, LockedTravelTarget="target",
                    )
                    model.globals["MenuHudIds"][0] = 101
                    model.globals["TemporaryTravelTextIds"][0] = 202
                    model.globals["InspectionTextIds"][0] = 303
                    model.tick("viewer", "04h")
                    dispatched = self.calls(model)
                    travel = [call for call in dispatched if call.startswith("CallSubroutine(Controller19")]
                    self.assertLess(travel.index("CallSubroutine(Controller19a)"),
                                    travel.index("CallSubroutine(Controller19e)"))
                    self.assertLess(travel.index("CallSubroutine(Controller19e)"),
                                    travel.index("CallSubroutine(Controller19g)"))
                    model.native_calls.clear()
                    model.tick("viewer", "19a", "19c", "19e", "19g")
                    self.assertFalse(state["CrouchTravelActive"])
                    self.assertEqual(state["TravelCommand"], 0)
                    self.assertEqual(state["TravelTargets"], [])
                    self.assertIsNone(state["TravelTargetCandidate"])
                    self.assertIsNone(state["MenuHud"])
                    self.assertIsNone(state["TravelText"])
                    self.assertIsNone(state["InspectionText"])
                    self.assertFalse(state["InspectionActive"])
                    self.assertFalse(state["NameplatesDisabled"])
                    self.assertEqual(state["LockedTravelType"], -1)
                    self.assertIsNone(state["LockedTravelTarget"])
                    self.assertEqual(model.globals["MenuHudIds"][0], 0)
                    self.assertEqual(model.globals["TemporaryTravelTextIds"][0], 0)
                    self.assertEqual(model.globals["InspectionTextIds"][0], 0)
                    self.assertEqual(self.calls(model), [
                        "DestroyHUDText(Global.TriggerPlayer.MenuHud)",
                        "DestroyIn-WorldText(Global.TriggerPlayer.TravelText)",
                        "EnableNameplates(AllPlayers(AllTeams),Global.TriggerPlayer)",
                        "DestroyIn-WorldText(Global.TriggerPlayer.InspectionText)",
                        "AllowButton(Global.TriggerPlayer,Button(PrimaryFire))",
                        "AllowButton(Global.TriggerPlayer,Button(SecondaryFire))",
                        "AllowButton(Global.TriggerPlayer,Button(Interact))",
                    ])

    def test_valid_navigation_consumes_the_press_and_rearms_after_release(self):
        for cursor in range(5):
            for button, command, delta in (("PrimaryFire", 1, 1), ("SecondaryFire", 2, 4)):
                with self.subTest(cursor=cursor, button=button):
                    model, state = self.model(TravelCursor=cursor, held={"Crouch", button})
                    model.tick("viewer", "19a", "19c")
                    self.assertEqual(state["TravelCommand"], command)
                    self.assertEqual(state["TravelCursor"], (cursor + delta) % 5)
                    self.assertEqual(state[model.state_field][model.latch_index("19c")], 1)
                    before = list(model.native_calls)
                    model.tick("viewer", "19a", "19c")
                    self.assertEqual(state["TravelCursor"], (cursor + delta) % 5)
                    self.assertEqual(model.native_calls, before)
                    state["held"] = {"Crouch"}
                    model.tick("viewer", "19b", "19c")
                    self.assertEqual(state["TravelCommand"], 0)
                    self.assertEqual(state[model.state_field][model.latch_index("19c")], 0)
                    state["held"] = {"Crouch", button}
                    model.tick("viewer", "19a", "19c")
                    self.assertEqual(state["TravelCursor"], (cursor + delta * 2) % 5)

    def test_valid_apply_dispatches_each_page_once_per_press(self):
        for cursor, expected in enumerate((
            ["CallSubroutine(TravelToSpawn)"],
            ["CallSubroutine(TravelToObjective)"],
            ["CallSubroutine(RefreshTravelTarget)", "CallSubroutine(TravelToPlayer)"],
            ["CallSubroutine(RefreshTravelTarget)", "AttachPlayers(", "SmallMessage("],
            ["ClearStatus(Global.TriggerPlayer,Unkillable)",
             "SetDamageReceived(Global.TriggerPlayer,100)", "Kill(Global.TriggerPlayer,Null)"],
        )):
            with self.subTest(cursor=cursor):
                model, state = self.model(TravelCursor=cursor)
                model.tick("viewer", "19a", "19e")
                emitted = self.calls(model)
                self.assertEqual(len(emitted), len(expected))
                for actual, prefix in zip(emitted, expected):
                    self.assertTrue(actual.startswith(prefix), actual)
                self.assertEqual(state["TravelCommand"], 3)
                self.assertEqual(state[model.state_field][model.latch_index("19e")], 1)
                self.assertEqual(state["LockedTravelType"], -1)
                self.assertIsNone(state["LockedTravelTarget"])
                if cursor == 3:
                    self.assertTrue(state["TravelAttachmentActive"])
                    self.assertEqual(state["TravelAttachmentTarget"], "target")
                    self.assertFalse(state["AttachmentCycleDetected"])
                if cursor == 4:
                    self.assertEqual(state["NextSuicideTime"], 13)
                before = list(model.native_calls)
                model.tick("viewer", "19a", "19e")
                self.assertEqual(model.native_calls, before)
                state["held"] = {"Crouch"}
                model.tick("viewer", "19b", "19e")
                self.assertEqual(state["TravelCommand"], 0)
                self.assertEqual(state[model.state_field][model.latch_index("19e")], 0)
                model.now = 13
                state["held"] = {"Crouch", "Interact"}
                model.tick("viewer", "19a", "19e")
                self.assertGreater(len(model.native_calls), len(before))
                self.assertEqual(state[model.state_field][model.latch_index("19e")], 1)


if __name__ == "__main__":
    unittest.main()
