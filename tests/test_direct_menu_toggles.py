"""Run the source input latch, dispatcher and live HUD text for direct toggles.

Event transitions are simulated; native rendering and input timing need game QA.
"""
import re
import unittest

from tools import validate_workshop as validator
from tests.test_menu_load_regressions import MenuLoadEvaluator
from tests.test_roster_rejoin_regressions import SOURCES


PAGES = ((8, "CrouchTravelEnabled"),
         (9, "InspectionPrivacyActive"),
         (12, "AllowDummyBotFollow"),
         (15, "SuperPunchPlayers"))


class DirectToggleEvaluator(MenuLoadEvaluator):
    BUTTONS = {value.replace(" ", ""): value for value in
               ("Crouch", "Interact", "Reload", "Primary Fire", "Secondary Fire",
                "Ability 1", "Ability 2", "Melee")}

    def __init__(self, source):
        super().__init__(source)
        self.previous_conditions = {}
        self.globals.update(SuperPunchPlayers=[], SuperPunchTimes=[0] * 12)
        self.subroutine_calls = []
        self.hud_commands = {}

    def add(self, name, **changes):
        state = super().add(name, **changes)
        defaults = dict(held=set(), MenuOpen=True, MenuPage=-1, MainMenuCursor=8,
                        MenuCommand=0, CameraInteractConsumed=False,
                        LuckActive=False, CrouchTravelActive=False,
                        CrouchTravelEnabled=False, InspectionPrivacyActive=False,
                        AllowDummyBotFollow=False, HudSlot=len(self.globals["HumanPlayers"]) - 1,
                        VoteCursor=0, GhostFlyCursor=0, UnkillableMode=0,
                        team=1)
        for field, value in defaults.items():
            state[field] = changes.get(field, value)
        return state

    def resolve(self, name):
        if name in self.BUTTONS:
            return self.BUTTONS[name]
        return super().resolve(name)

    def call(self, name, args):
        if name == "InputBindingString":
            return args[0]
        if name in ("Min", "Max"):
            return (min if name == "Min" else max)(args)
        if name == "IsButtonHeld":
            return args[1] in self.players[args[0]]["held"]
        if name == "TeamOf":
            return self.players[args[0]]["team"]
        if name == "OppositeTeamOf":
            return 3 - args[0]
        if name == "AllPlayers":
            return [identity for identity, state in self.players.items()
                    if args[0] == "AllTeams" or state["team"] == args[0]]
        return super().call(name, args)

    def enabled(self, owner, field):
        if field == "SuperPunchPlayers":
            return owner in self.globals[field]
        return self.players[owner][field]

    def render_main(self, owner):
        self.event_player = owner
        rule = validator.rule_by_subroutine(self.rules, "DrawMainMenu")
        self.execute(validator.rule_block(rule, "actions"))

    def execute(self, actions):
        # Extend the shared source evaluator with the dispatcher's Else If chain.
        actions = re.sub(r'(?m)^\s*"(?:\\.|[^"\\])*"\s*$', "", actions)
        frames, active = [], True
        for statement in validator.split_top_level(actions, ";"):
            statement = statement.strip()
            if not statement:
                continue
            if statement.startswith("If("):
                branch = active and bool(self.evaluate(statement[3:-1]))
                frames.append(dict(parent=active, taken=branch))
                active = branch
            elif statement.startswith("Else If("):
                frame = frames[-1]
                active = frame["parent"] and not frame["taken"] and bool(self.evaluate(statement[8:-1]))
                frame["taken"] |= active
            elif statement == "Else":
                frame = frames[-1]
                active = frame["parent"] and not frame["taken"]
                frame["taken"] = True
            elif statement == "End":
                active = frames.pop()["parent"]
            elif active:
                if statement == "Abort":
                    return
                if statement.startswith("Abort If("):
                    if self.evaluate(statement[len("Abort If("):-1]):
                        return
                else:
                    if statement.startswith("Call Subroutine("):
                        name = statement[len("Call Subroutine("):-1]
                        self.subroutine_calls.append((self.event_player, name))
                        # These unrelated target queries have their own tests.
                        if name in ("RefreshCameraTargets", "RefreshRevengeTargets"):
                            continue
                    elif statement.startswith("Modify Global Variable("):
                        call = next(validator.iter_calls(statement, "Modify Global Variable"))
                        field, operation, expression = call.args
                        value = self.evaluate(expression)
                        if operation == "Append To Array":
                            self.globals[field].append(value)
                        elif operation == "Remove From Array By Value":
                            self.globals[field] = [item for item in self.globals[field] if item != value]
                        else:
                            raise AssertionError(f"unsupported registry action: {operation}")
                        continue
                    elif statement.startswith("Create HUD Text("):
                        call = next(validator.iter_calls(statement, "Create HUD Text"))
                        super().execute(statement + ";")
                        self.hud_commands[self.last_text] = call.args[2]
                        continue
                    super().execute(statement + ";")
        if frames:
            raise AssertionError("unbalanced menu source")

    def tick(self, owner):
        for prefix in ("05d", "12d", "05c", "06", "10"):
            key = owner, prefix
            condition = self.conditions(prefix, owner)
            if condition and not self.previous_conditions.get(key, False):
                self.run(prefix, owner)
            self.previous_conditions[key] = condition

    def input(self, owner, button=None, ticks=1):
        self.players[owner]["held"] = {"Crouch"} | ({button} if button else set())
        for _ in range(ticks):
            self.tick(owner)


class DirectMenuToggleTests(unittest.TestCase):
    def models(self):
        for path, _, _ in SOURCES:
            yield path.name, DirectToggleEvaluator(path.read_text(encoding="utf-8"))

    def test_interact_changes_each_state_once_per_press_and_only_for_owner(self):
        for source, model in self.models():
            for page, field in PAGES:
                with self.subTest(source=source, page=page):
                    owner = f"owner-{page}"
                    state = model.add(owner, MainMenuCursor=page, team=2)
                    other_name = f"other-{page}"
                    other = model.add(other_name, MainMenuCursor=page, team=2)
                    model.add(f"dummy-{page}", IsHuman=False, dummy=True, team=1)
                    model.input(owner, "Interact", ticks=20)
                    self.assertTrue(model.enabled(owner, field))
                    self.assertFalse(model.enabled(other_name, field))
                    self.assertEqual((state["MenuPage"], state["MainMenuCursor"]), (-1, page))
                    self.assertEqual(model.created_huds, [])
                    model.input(owner, ticks=2)
                    model.input(owner, "Interact", ticks=20)
                    self.assertFalse(model.enabled(owner, field))
                    self.assertFalse(model.enabled(other_name, field))
                    self.assertEqual((state["MenuPage"], state["MainMenuCursor"]), (-1, page))
                    self.assertEqual(model.created_huds, [])

    def test_primary_and_secondary_keep_main_navigation_without_toggling(self):
        for source, model in self.models():
            for page, field in PAGES:
                for enabled in (False, True):
                    with self.subTest(source=source, page=page, enabled=enabled):
                        owner = f"owner-{page}-{enabled}"
                        state = model.add(owner, MainMenuCursor=page)
                        if field == "SuperPunchPlayers":
                            if enabled:
                                model.globals[field].append(owner)
                        else:
                            state[field] = enabled
                        for button in ("Primary Fire", "Secondary Fire"):
                            model.input(owner, button, ticks=10)
                            self.assertEqual(model.enabled(owner, field), enabled)
                            self.assertEqual(state["MenuPage"], -1)
                            self.assertEqual(state["MainMenuCursor"], (page + 1) % 16 if button == "Primary Fire" else page)
                            model.input(owner, ticks=2)
                        self.assertEqual(model.created_huds, [])

    def test_other_main_entries_still_open_their_function_screen_once(self):
        for source, model in self.models():
            for page in sorted(set(range(16)) - {page for page, _ in PAGES}):
                with self.subTest(source=source, page=page):
                    owner = f"owner-{page}"
                    state = model.add(owner, MainMenuCursor=page, team=2)
                    model.input(owner, "Interact", ticks=20)
                    self.assertEqual(state["MenuPage"], page)
                    self.assertEqual(state["MainMenuCursor"], page)
                    self.assertFalse(state["CrouchTravelEnabled"])
                    self.assertFalse(state["InspectionPrivacyActive"])
                    self.assertFalse(state["AllowDummyBotFollow"])
                    self.assertEqual(model.globals["SuperPunchPlayers"], [])
                    self.assertEqual(len([hud for hud in model.created_huds if hud[0] == owner]), 1)

    def test_existing_hud_shows_applied_state_in_english_without_option_rows(self):
        for source, model in self.models():
            for page, field in PAGES:
                with self.subTest(source=source, page=page):
                    owner = f"owner-{page}"
                    state = model.add(owner, MainMenuCursor=page, team=2)
                    model.add(f"dummy-{page}", IsHuman=False, dummy=True, team=1)
                    model.render_main(owner)
                    handle = state["MenuHud"]
                    expression = model.hud_bodies[handle]
                    self.assertIn("OFF", model.evaluate(expression))
                    model.input(owner, "Interact", ticks=20)
                    rendered = model.evaluate(expression)
                    self.assertIn("ON", rendered)
                    self.assertNotIn("/2", rendered)
                    self.assertNotIn("\n>", rendered)
                    self.assertEqual(state["MenuHud"], handle)
                    self.assertEqual(len([hud for hud in model.created_huds if hud[0] == owner]), 1)

    def test_main_toggle_guard_still_requires_live_opposing_dummy_and_allows_off(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("owner", MainMenuCursor=12, team=2)
                model.add("own-dummy", IsHuman=False, dummy=True, team=2)
                stale = model.add("stale-enemy", IsHuman=False, dummy=True, team=1, exists=False)
                for _ in range(2):
                    model.input("owner", "Interact", ticks=20)
                    self.assertFalse(state["AllowDummyBotFollow"])
                    self.assertEqual(state["MenuPage"], -1)
                    model.input("owner", ticks=2)
                stale["exists"] = True
                model.input("owner", "Interact", ticks=20)
                self.assertTrue(state["AllowDummyBotFollow"])
                stale["exists"] = False
                model.input("owner", ticks=2)
                model.input("owner", "Interact", ticks=20)
                self.assertFalse(state["AllowDummyBotFollow"])
                self.assertEqual((state["MenuPage"], state["MainMenuCursor"]), (-1, 12))
                self.assertEqual((model.created_huds, model.destroyed_huds), ([], []))

    def test_twelve_owners_repeat_toggles_without_hud_or_registry_accumulation(self):
        for source, model in self.models():
            with self.subTest(source=source):
                owners = [f"player-{index}" for index in range(12)]
                handles = {}
                for index, owner in enumerate(owners):
                    state = model.add(owner)
                    model.render_main(owner)
                    handles[owner] = state["MenuHud"]
                for cycle in range(4):
                    expected = cycle % 2 == 0
                    for page, field in (entry for entry in PAGES if entry[0] != 12):
                        for owner in owners:
                            state = model.players[owner]
                            state["MainMenuCursor"] = page
                            model.input(owner, ticks=2)
                            model.input(owner, "Interact", ticks=3)
                            self.assertEqual(model.enabled(owner, field), expected)
                            self.assertEqual((state["MenuPage"], state["MainMenuCursor"]), (-1, page))
                            self.assertEqual(state["MenuHud"], handles[owner])
                            self.assertLessEqual(len(model.globals["SuperPunchPlayers"]), 12)
                            self.assertEqual(len(model.globals["SuperPunchPlayers"]),
                                             len(set(model.globals["SuperPunchPlayers"])))
                    self.assertEqual(model.globals["SuperPunchTimes"], [-1 if expected else 0] * 12)
                    self.assertEqual(len(model.created_huds), 12)
                    self.assertEqual(model.destroyed_huds, [])
                self.assertEqual(model.globals["SuperPunchPlayers"], [])

    def test_toggle_input_ignores_closed_menu_dead_player_and_consumed_interact(self):
        blocked = ({"MenuOpen": False}, {"alive": False}, {"IsHuman": False},
                   {"IsAutomaticBot": True}, {"dummy": True}, {"CameraInteractConsumed": True})
        for source, model in self.models():
            for page, field in PAGES:
                for changes in blocked:
                    with self.subTest(source=source, page=page, actor=changes):
                        owner = f"owner-{page}-{len(model.players)}"
                        state = model.add(owner, MainMenuCursor=page, team=2, HudSlot=0, **changes)
                        model.add(f"enemy-{owner}", IsHuman=False, dummy=True, team=1)
                        model.input(owner, "Interact", ticks=20)
                        self.assertFalse(model.enabled(owner, field))
                        self.assertEqual((state["MenuPage"], state["MainMenuCursor"]), (-1, page))

    def test_english_main_help_keeps_interact_and_melee_bindings(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("owner")
                model.render_main("owner")
                expression = model.hud_bodies[state["MenuHud"]]
                rendered = model.evaluate(expression)
                self.assertIn("Interact: select", rendered)
                self.assertIn("Melee", rendered)


if __name__ == "__main__":
    unittest.main()
