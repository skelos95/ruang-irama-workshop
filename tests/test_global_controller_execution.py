"""Execute actual generated controller predicates and bookkeeping actions.

Rendering and camera calls are mocked engine boundaries. These checks exercise
the emitted state/deadline branches; they do not simulate native event ordering.
"""

from __future__ import annotations

import operator
from pathlib import Path
import re
import unittest

from tools import validate_workshop as semantic
from tools import validate_global_runtime as runtime
from tests.test_fly_motion import Expression


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "workshop/ruang_irama.it-IT.workshop"


class ControllerExpression(Expression):
    TOKEN = re.compile(r"\d+(?:\.\d+)?|[A-Za-z_][A-Za-z_0-9.]*|==|!=|>=|<=|[()\[\]+\-*/,<>%?:]")
    PRECEDENCE = {**Expression.PRECEDENCE, "%": 3}

    def parse(self, minimum=0):
        token = self.take()
        if token == "-":
            left = ("negate", self.parse(4))
        elif token == "(":
            left = self.parse()
            self.take(")")
        elif token[0].isdigit():
            left = ("literal", float(token))
        elif self.peek() == "(":
            self.take("(")
            arguments = []
            if self.peek() != ")":
                while True:
                    arguments.append(self.parse())
                    if self.peek() != ",":
                        break
                    self.take(",")
            self.take(")")
            left = ("call", token, arguments)
        else:
            left = ("name", token)
        while True:
            if self.peek() == "[":
                self.take("[")
                left = ("index", left, self.parse())
                self.take("]")
            elif self.peek() == "?" and minimum == 0:
                self.take("?")
                yes = self.parse()
                self.take(":")
                left = ("conditional", left, yes, self.parse())
            elif self.peek() in self.PRECEDENCE and self.PRECEDENCE[self.peek()] >= minimum:
                operation = self.take()
                left = (operation, left, self.parse(self.PRECEDENCE[operation] + 1))
            else:
                return left

    def evaluate(self, context):
        operations = {
            "+": operator.add, "-": operator.sub, "*": operator.mul,
            "/": operator.truediv, "%": operator.mod, "==": operator.eq,
            "!=": operator.ne, ">=": operator.ge, "<=": operator.le,
            ">": operator.gt, "<": operator.lt,
        }

        def visit(node):
            kind = node[0]
            if kind == "literal": return node[1]
            if kind == "name": return context.resolve(node[1])
            if kind == "negate": return -visit(node[1])
            if kind == "call": return context.call(node[1], [visit(arg) for arg in node[2]])
            if kind == "index":
                array, index = visit(node[1]), int(visit(node[2]))
                return array[index] if isinstance(array, (list, tuple)) and 0 <= index < len(array) else 0
            if kind == "conditional": return visit(node[2] if visit(node[1]) else node[3])
            return operations[kind](visit(node[1]), visit(node[2]))

        return visit(self.tree)


class GeneratedControllerEvaluator:
    """A strict interpreter of the selected output rules, without a second FSM."""

    def __init__(self, source):
        self.rules = semantic.extract_rules(source)
        _, fields, _, _ = semantic.declaration_entries(source)
        self.state_field = next(field.name for field in fields if field.index == 60)
        self.deadline_field = next(field.name for field in fields if field.index == 92)
        self.players = {}
        self.globals = {"Siap": True, "PemainManusia": [], "PemainPukulanSuper": [],
                        "PemainSiklusGlobal": None, "WaktuSiklusGlobal": 0,
                        "PenontonVisiNasib": []}
        self.now = 0
        self.native_calls = []
        self.expressions = {}
        self.literals = {}

    def add_player(self, identity, **changes):
        state = dict(Manusia=True, BotOtomatis=False, MenuTerbuka=False,
                     SeranganDekatDipakai=False, TeleportasiJongkokAktif=False,
                     KartuNasibAktif=False, InteraksiKameraDipakai=False,
                     PerintahMenu=0, HalamanMenu=-1, ModeKamera=0,
                     SiklusPemainAktif=False, PindahTimDiproses=False,
                     TimTerakhir=1, TimSiklusTarget=1, SudahSiap=True,
                     WaktuSiklusTim=0, team=1, alive=True, spawned=True,
                     exists=True, dummy=False, slot=0, held=set())
        state[self.state_field] = []
        state[self.deadline_field] = []
        state.update(changes)
        self.players[identity] = state
        self.globals["PemainManusia"].append(identity)
        return state

    def controller(self, prefix):
        matching = [rule for rule in self.rules if prefix + " -" in rule.name]
        if len(matching) != 1:
            raise AssertionError(f"expected one generated controller {prefix}: {[rule.name for rule in matching]}")
        if semantic.event_type(matching[0]) != "Subroutine":
            raise AssertionError(f"controller {prefix} was not lowered")
        return matching[0]

    def expression(self, source):
        def literal(match):
            key = f"Literal{len(self.literals)}"
            self.literals[key] = match[0][1:-1]
            return key
        source = re.sub(r'"(?:\\.|[^"\\])*"', literal, source)
        packed = re.sub(r"\s+", "", source)
        if packed not in self.expressions:
            self.expressions[packed] = ControllerExpression(packed)
        return self.expressions[packed].evaluate(self)

    def resolve(self, name):
        if name in self.literals:
            return self.literals[name]
        constants = {"True": True, "False": False, "Null": None,
                     "EmptyArray": [], "TotalTimeElapsed": self.now,
                     "Team1": 1, "Team2": 2}
        if name in constants: return constants[name]
        if name.startswith("Global."):
            parts = name.split(".")
            value = self.globals.get(parts[1], 0)
            return self.players[value].get(parts[2], 0) if len(parts) == 3 else value
        return name  # Native enums and variable identifiers.

    def call(self, name, arguments):
        if name == "And": return all(arguments)
        if name == "Or": return any(arguments)
        if name == "Not": return not arguments[0]
        if name == "Array": return list(arguments)
        if name == "CountOf": return len(arguments[0])
        if name == "ArrayContains": return arguments[1] in arguments[0]
        if name == "RemoveFromArray": return [x for x in arguments[0] if x != arguments[1]]
        if name == "PlayerVariable": return self.players[arguments[0]].get(arguments[1], 0)
        if name == "Button": return arguments[0]
        if name == "IsButtonHeld": return arguments[1] in self.players[arguments[0]]["held"]
        if name in ("EntityExists", "HasSpawned", "IsAlive", "IsDummyBot", "TeamOf", "SlotOf"):
            field = {"EntityExists": "exists", "HasSpawned": "spawned", "IsAlive": "alive",
                     "IsDummyBot": "dummy", "TeamOf": "team", "SlotOf": "slot"}[name]
            return self.players.get(arguments[0], {}).get(field, False)
        raise AssertionError(f"unsupported emitted function {name}")

    def assign(self, target, value):
        indexed = re.fullmatch(r"(.+?)\[(.*)\]", target)
        if indexed:
            array = self.expression(indexed[1])
            index = int(self.expression(indexed[2]))
            array.extend([0] * max(0, index + 1 - len(array)))
            array[index] = value
            return
        parts = target.split(".")
        if len(parts) == 3:
            self.players[self.globals[parts[1]]][parts[2]] = value
        elif len(parts) == 2 and parts[0] == "Global":
            self.globals[parts[1]] = value
        else:
            raise AssertionError(f"unsupported emitted assignment {target}")

    def execute(self, rule):
        actions = semantic.rule_block(rule, "actions") or ""
        actions = re.sub(r'(?m)^[ \t]*"(?:\\.|[^"\\])*"[ \t]*(?:\r?\n|$)', "", actions)
        active = [True]
        chosen = [False]
        for raw in semantic.split_top_level(actions, ";"):
            statement = re.sub(r"\s+", "", raw)
            if not statement: continue
            if statement.startswith("If("):
                enabled = active[-1] and bool(self.expression(statement[3:-1]))
                active.append(enabled)
                chosen.append(enabled)
            elif statement.startswith("ElseIf("):
                enabled = active[-2] and not chosen[-1] and bool(self.expression(statement[7:-1]))
                active[-1] = enabled
                chosen[-1] |= enabled
            elif statement == "Else":
                active[-1] = active[-2] and not chosen[-1]
                chosen[-1] = True
            elif statement == "End":
                active.pop()
                chosen.pop()
            elif not active[-1]:
                continue
            elif statement == "Abort" or (statement.startswith("AbortIf(") and
                                            self.expression(statement[8:-1])):
                return
            elif statement.startswith("AbortIf("):
                continue
            elif match := re.fullmatch(r"(Global\.\w+(?:\.\w+)?(?:\[.*\])?)([+\-*/%]?=)(?!=)(.+)", statement):
                value = self.expression(match[3])
                if match[2] != "=":
                    value = self.expression(f"{match[1]}{match[2][0]}({match[3]})")
                self.assign(match[1], value)
            elif statement.startswith("CallSubroutine("):
                self.native_calls.append((self.globals["PemainPemicu"], statement, self.now))
            elif statement.startswith(("AllowButton(", "StopCamera(", "StopChasingPlayerVariable(")):
                self.native_calls.append((self.globals["PemainPemicu"], statement, self.now))
            else:
                raise AssertionError(f"unsupported emitted action {raw.strip()}")
        if len(active) != 1:
            raise AssertionError("unclosed emitted branch")

    def tick(self, identity, *prefixes):
        self.globals["PemainPemicu"] = identity
        self.globals["PemainAktif"] = "other-scheduler-owner"
        for prefix in prefixes:
            self.execute(self.controller(prefix))


class GlobalControllerExecutionTests(unittest.TestCase):
    def model(self):
        return GeneratedControllerEvaluator(runtime.english(RUNTIME.read_text(encoding="utf-8")))

    def test_twelve_players_have_independent_menu_and_camera_hold_deadlines(self):
        model = self.model()
        for index in range(12): model.add_player(f"p{index}", slot=index // 2, team=1 + index % 2)
        for step in range(26):
            model.now = round(step * 0.05, 3)
            for index, (identity, state) in enumerate(model.players.items()):
                start = round(index * 0.05, 3)
                state["held"] = {"Melee"} if model.now >= start else set()
                if model.now >= round(start + 0.15, 3): state["held"].add("Interact")
                model.tick(identity, "05", "12c")
                self.assertEqual(state["MenuTerbuka"], model.now >= round(start + 0.5, 3))
                self.assertEqual(state["ModeKamera"], int(model.now >= round(start + 0.65, 3)))

    def test_release_aborts_menu_hold_and_next_press_requires_full_half_second(self):
        model = self.model()
        state = model.add_player("p", held={"Melee"})
        model.tick("p", "05")
        model.now = 0.3
        state["held"] = set()
        model.tick("p", "05")
        model.now = 0.4
        state["held"] = {"Melee"}
        model.tick("p", "05")
        model.now = 0.899
        model.tick("p", "05")
        self.assertFalse(state["MenuTerbuka"])
        model.now = 0.9
        model.tick("p", "05")
        self.assertTrue(state["MenuTerbuka"])

    def test_command_priority_release_and_next_press_follow_emitted_actions(self):
        model = self.model()
        state = model.add_player("p", MenuTerbuka=True, held={"Crouch", "Interact", "PrimaryFire"})
        model.tick("p", "05c", "05d")
        self.assertEqual(state["PerintahMenu"], 1)
        model.tick("p", "05c", "05d")
        self.assertEqual(state["PerintahMenu"], 1)
        state["held"] = set()
        model.tick("p", "05c", "05d", "12d")
        self.assertEqual(state["PerintahMenu"], 0)
        state["held"] = {"Crouch", "PrimaryFire", "SecondaryFire"}
        model.tick("p", "05c", "05d")
        self.assertEqual(state["PerintahMenu"], 3)

    def test_team_quarantine_cancels_old_hold_and_reused_slot_starts_fresh(self):
        model = self.model()
        old = model.add_player("old", held={"Melee", "Interact"})
        model.tick("old", "05", "12c")
        model.now = 0.3
        old["team"] = 2
        model.tick("old", "01a")
        self.assertFalse(old["Manusia"])
        self.assertTrue(old["PindahTimDiproses"])
        self.assertFalse(any(old[model.deadline_field]))
        before = len(model.native_calls)
        model.execute(model.controller("04h"))
        emitted = [call[1] for call in model.native_calls[before:]]
        self.assertNotIn("CallSubroutine(Pengatur05)", emitted)
        self.assertNotIn("CallSubroutine(Pengatur12c)", emitted)
        replacement = model.add_player("replacement", slot=old["slot"], team=2, held={"Melee"})
        model.tick("replacement", "05")
        model.now = 0.5
        model.tick("replacement", "05")
        self.assertFalse(replacement["MenuTerbuka"])
        model.now = 0.8
        model.tick("replacement", "05")
        self.assertTrue(replacement["MenuTerbuka"])

    def test_same_owner_can_complete_two_separate_team_transition_phases(self):
        model = self.model()
        state = model.add_player("p")
        for transition, team in enumerate((2, 1)):
            start = 1 + transition * 2
            model.now = start
            state.update(Manusia=True, SudahSiap=True, PindahTimDiproses=False,
                         SiklusPemainAktif=False, team=team)
            model.tick("p", "01a")
            self.assertFalse(state["Manusia"])
            self.assertEqual(state["TimSiklusTarget"], team)
            model.globals["PemainSiklusGlobal"] = "p"
            calls_before = len(model.native_calls)
            for delay in (0.5, 0.551, 0.602):
                model.now = start + delay
                model.tick("p", "01b")
            emitted = [call[1] for call in model.native_calls[calls_before:]]
            self.assertEqual(emitted, ["CallSubroutine(TenangkanPemain)",
                                       "CallSubroutine(BersihkanPemain)",
                                       "CallSubroutine(SiapkanPemain)"])
            # The interpreter mocks native subroutines; this exercises the actual
            # emitted phase machine without claiming to emulate engine setup.

    def test_unspawned_owner_cannot_advance_pending_transition(self):
        model = self.model()
        state = model.add_player("p", team=2)
        model.now = 1
        model.tick("p", "01a")
        model.globals["PemainSiklusGlobal"] = "p"
        model.now = 1.5
        model.tick("p", "01b")
        before = list(model.native_calls)
        state["spawned"] = False
        model.now = 1.6
        model.tick("p", "01b")
        self.assertEqual(model.native_calls, before)

    def test_changing_team_mid_phase_restarts_cleanup_for_new_target(self):
        model = self.model()
        state = model.add_player("p", team=2)
        model.now = 1
        model.tick("p", "01a")
        model.globals["PemainSiklusGlobal"] = "p"
        model.now = 1.5
        model.tick("p", "01b")
        state["team"] = 1
        model.now = 1.52
        model.tick("p", "01a")
        self.assertEqual(state["TimSiklusTarget"], 1)
        self.assertIsNone(model.globals["PemainSiklusGlobal"])
        model.globals["PemainSiklusGlobal"] = "p"
        model.now = 2.02
        model.tick("p", "01b")
        self.assertEqual(model.native_calls[-1][1], "CallSubroutine(TenangkanPemain)")

    def test_idle_human_skips_closed_menu_navigation_and_inactive_travel(self):
        model = self.model()
        model.add_player("p")
        model.tick("p", "04h")
        emitted = {call[1] for call in model.native_calls}
        for prefix in ("05c", "05d", "05e", "05f", "06", "08", "10", "11",
                       "19a", "19b", "19c", "19d", "19e", "19f", "19h", "19g"):
            self.assertNotIn(f"CallSubroutine(Pengatur{prefix})", emitted)

    def test_skipped_closed_menu_and_travel_groups_rearm_their_press_latches(self):
        model = self.model()
        state = model.add_player("p")
        state[model.state_field] = [0] * 36 + [42]
        indices = []
        for prefix in ("06", "08", "10", "11", "19c", "19e"):
            controller = model.controller(prefix)
            pattern = re.escape(f"Global.PemainPemicu.{model.state_field}") + r"\[(\d+)\]\s*=\s*0;"
            index = int(re.search(pattern, controller.body)[1])
            indices.append(index)
            state[model.state_field][index] = 1
        model.tick("p", "04h")
        self.assertEqual([state[model.state_field][index] for index in indices], [0] * 6)
        self.assertEqual(state[model.state_field][36], 42)


if __name__ == "__main__":
    unittest.main()
