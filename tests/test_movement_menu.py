"""Execute the Movement page, its bounds, live text, and player ownership.

The shared menu interpreter executes the real branches. Native physics is a
recorded boundary here and has separate behavioral coverage.
"""
import unittest

from tests.test_direct_menu_toggles import DirectToggleEvaluator
from tests.test_global_compaction import CompactionContext
from tests.test_roster_rejoin_regressions import SOURCES
from tools import validate_workshop as validator


class MovementMenuEvaluator(DirectToggleEvaluator):
    def __init__(self, source):
        super().__init__(source)
        self.physics_updates = []
        rule = validator.rule_by_subroutine(self.rules, "ApplyGhostFlyPhysics")
        self.physics_actions = validator.rule_block(rule, "actions")

    def execute(self, actions):
        if actions == self.physics_actions:
            state = self.players[self.event_player]
            self.physics_updates.append((self.event_player, state["MovementSpeed"], state["MovementGravity"]))
            return
        super().execute(actions)

    def viewer(self, name="viewer", **changes):
        state = dict(MenuOpen=True, MenuPage=16, MainMenuCursor=16,
                     CrouchTravelActive=False, MovementCursor=0,
                     MovementSpeed=100, MovementGravity=100, MenuCommand=3)
        state.update(changes)
        return self.add(name, **state)


class MovementMenuTests(unittest.TestCase):
    def models(self):
        for path, _, _ in SOURCES:
            yield path.name, MovementMenuEvaluator(path.read_text(encoding="utf-8"))

    def test_main_menu_reaches_all_seventeen_entries_in_both_directions(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.viewer(MenuPage=-1, MainMenuCursor=0)
                visited = []
                for _ in range(17):
                    visited.append(state["MainMenuCursor"])
                    model.run("06", "viewer")
                self.assertEqual(visited, list(range(17)))
                self.assertEqual(state["MainMenuCursor"], 0)
                state["MenuCommand"] = 4
                model.run("06", "viewer")
                self.assertEqual(state["MainMenuCursor"], 16)

    def test_primary_and_secondary_apply_the_step_for_the_selected_value_immediately(self):
        for source, model in self.models():
            for cursor, field in ((0, "MovementSpeed"), (1, "MovementGravity")):
                for start, command, expected in ((100, 3, 150), (100, 4, 90),
                                                 (90, 3, 100), (90, 4, 80),
                                                 (150, 3, 200), (150, 4, 100)):
                    with self.subTest(source=source, field=field, start=start, command=command):
                        state = model.viewer(MovementCursor=cursor, MenuCommand=command, **{field: start})
                        model.run("06", "viewer")
                        self.assertEqual(state[field], expected)
                        self.assertEqual(state["MovementGravity" if cursor == 0 else "MovementSpeed"], 100)
                        self.assertEqual(model.physics_updates[-1],
                                         ("viewer", state["MovementSpeed"], state["MovementGravity"]))

    def test_speed_and_gravity_clamp_instead_of_wrapping(self):
        cases = ((0, "MovementSpeed", 10, 4, 10),
                 (0, "MovementSpeed", 1000, 3, 1000),
                 (1, "MovementGravity", 0, 4, 0),
                 (1, "MovementGravity", 500, 3, 500))
        for source, model in self.models():
            for cursor, field, start, command, expected in cases:
                with self.subTest(source=source, field=field, start=start):
                    state = model.viewer(MovementCursor=cursor, MenuCommand=command, **{field: start})
                    model.run("06", "viewer")
                    self.assertEqual(state[field], expected)

    def test_every_selectable_value_is_reachable_forward_and_backward(self):
        ranges = ((0, "MovementSpeed", list(range(10, 101, 10)) + list(range(150, 1001, 50))),
                  (1, "MovementGravity", list(range(0, 101, 10)) + list(range(150, 501, 50))))
        for source, model in self.models():
            for cursor, field, expected in ranges:
                with self.subTest(source=source, field=field):
                    state = model.viewer(MovementCursor=cursor, **{field: expected[0]})
                    forward = [state[field]]
                    for _ in expected[1:]:
                        model.run("06", "viewer")
                        forward.append(state[field])
                        self.assertEqual(model.physics_updates[-1],
                                         ("viewer", state["MovementSpeed"], state["MovementGravity"]))
                    self.assertEqual(forward, expected)
                    state["MenuCommand"] = 4
                    backward = [state[field]]
                    for _ in expected[1:]:
                        model.run("06", "viewer")
                        backward.append(state[field])
                    self.assertEqual(backward, list(reversed(expected)))
                    self.assertEqual(state["MovementGravity" if cursor == 0 else "MovementSpeed"], 100)

    def test_interact_selects_parameter_and_reload_keeps_values(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.viewer(MenuCommand=1, MovementSpeed=350, MovementGravity=250)
                for expected in (1, 0, 1):
                    model.run("10", "viewer")
                    self.assertEqual(state["MovementCursor"], expected)
                self.assertEqual(model.physics_updates, [])
                state["MenuCommand"] = 2
                model.run("11", "viewer")
                self.assertEqual(state["MenuPage"], -1)
                self.assertEqual((state["MovementSpeed"], state["MovementGravity"]), (350, 250))

    def test_values_and_parameter_selection_are_personal(self):
        for source, model in self.models():
            with self.subTest(source=source):
                first = model.viewer()
                second = model.viewer("other", MovementCursor=1, MovementSpeed=600, MovementGravity=0)
                before = dict(second)
                model.run("06", "viewer")
                first["MenuCommand"] = 1
                model.run("10", "viewer")
                self.assertEqual(second, before)
                self.assertEqual(model.physics_updates, [("viewer", 150, 100)])

    def test_held_input_changes_the_parameter_or_value_only_once(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.viewer(MenuPage=-1, MovementCursor=9, MenuCommand=0)
                model.input("viewer", "Interact", ticks=20)
                self.assertEqual((state["MenuPage"], state["MovementCursor"]), (16, 1))
                model.input("viewer")
                model.input("viewer", "Interact", ticks=20)
                self.assertEqual(state["MovementCursor"], 0)
                model.input("viewer")
                model.input("viewer", "Primary Fire", ticks=20)
                self.assertEqual((state["MovementSpeed"], state["MovementGravity"]), (150, 100))
                self.assertEqual(model.physics_updates, [("viewer", 150, 100)])
                model.input("viewer")
                model.input("viewer", "Secondary Fire", ticks=20)
                self.assertEqual(state["MovementSpeed"], 100)
                model.input("viewer")
                model.input("viewer", "Secondary Fire", ticks=20)
                self.assertEqual(state["MovementSpeed"], 90)
                self.assertEqual(model.physics_updates,
                                 [("viewer", 150, 100), ("viewer", 100, 100), ("viewer", 90, 100)])

    def test_one_live_hud_updates_values_and_selection_without_recreation(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.viewer()
                model.run("91u", "viewer")
                handle = state["MenuHud"]
                expression = model.hud_bodies[handle]
                self.assertIn("> Speed: 100% (10-1000%)", model.evaluate(expression))
                model.run("06", "viewer")
                self.assertIn("> Speed: 150% (10-1000%)", model.evaluate(expression))
                state["MenuCommand"] = 1
                model.run("10", "viewer")
                self.assertIn("> Gravity: 100% (0-500%)", model.evaluate(expression))
                state["MenuCommand"] = 4
                model.run("06", "viewer")
                self.assertIn("> Gravity: 90% (0-500%)", model.evaluate(expression))
                self.assertEqual(state["MenuHud"], handle)
                self.assertEqual(model.created_huds, [("viewer", handle)])
                self.assertEqual(model.destroyed_huds, [])

    def test_main_preview_and_movement_bindings_display_the_actual_values(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.viewer(MovementSpeed=450, MovementGravity=300)
                model.run("91a", "viewer")
                preview = model.evaluate(model.hud_bodies[state["MenuHud"]])
                self.assertIn("16 - MOVEMENT / GRAVITY", preview)
                self.assertIn("SPEED: 450% | GRAVITY: 300%", preview)
                rule = validator.rule_by_subroutine(model.rules, "DrawMovementMenu")
                hud = next(validator.iter_calls(rule.body, "Create HUD Text"))
                model.event_player = "viewer"
                controls = model.evaluate(hud.args[2])
                for label in ("Crouch", "Primary Fire: +50%", "Secondary Fire: -50%",
                              "Interact: select Speed / Gravity", "Reload: back", "Melee"):
                    self.assertIn(label, controls)

    def test_live_bindings_follow_the_selected_parameter_and_the_hundred_boundary(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.viewer(MovementSpeed=100, MovementGravity=90)
                model.event_player = "viewer"
                rule = validator.rule_by_subroutine(model.rules, "DrawMovementMenu")
                hud = next(validator.iter_calls(rule.body, "Create HUD Text"))
                for cursor, speed, gravity, up, down in (
                    (0, 100, 90, 50, 10),
                    (0, 90, 450, 10, 10),
                    (0, 150, 90, 50, 50),
                    (1, 450, 90, 10, 10),
                    (1, 90, 100, 50, 10),
                    (1, 90, 150, 50, 50),
                ):
                    state.update(MovementCursor=cursor, MovementSpeed=speed, MovementGravity=gravity)
                    controls = model.evaluate(hud.args[2])
                    self.assertIn(f"Primary Fire: +{up}%", controls)
                    self.assertIn(f"Secondary Fire: -{down}%", controls)

    def test_bootstrap_has_one_domain_title_with_timer_and_no_site_subtitle(self):
        for source, model in self.models():
            with self.subTest(source=source):
                bootstrap = model.rule("00")
                huds = list(validator.iter_calls(bootstrap.body, "Create HUD Text"))
                self.assertEqual(len(huds), 5)
                title = next(call for call in huds if call.args[4:6] == ("Top", "0"))
                self.assertEqual(title.args[3], 'Custom String("cozywatch.org [{0}]", Global.ServerTimeText)')
                self.assertFalse(any('Custom String("cozywatch.org")' in call.args[2] for call in huds))
                self.assertTrue(any(call.args[4:6] == ("Top", "2") for call in huds))

    def test_generated_hud_uses_live_viewer_values_after_global_dispatch_clears(self):
        root = SOURCES[0][0].parents[1]
        for path in (root / "workshop/ruang_irama.en-US.workshop",
                     root / "tests/fixtures/global_runtime_reference.txt"):
            with self.subTest(artifact=path.name):
                text = path.read_text(encoding="utf-8")
                rule = validator.rule_by_subroutine(validator.extract_rules(text), "DrawMovementMenu")
                self.assertIsNotNone(rule)
                huds = list(validator.iter_calls(rule.body, "Create HUD Text"))
                self.assertEqual(len(huds), 1)
                self.assertEqual(huds[0].args[0], "Evaluate Once(Global.TriggerPlayer)")
                _, fields, _, _ = validator.declaration_entries(text)
                context = CompactionContext([field.name for field in fields])
                content = context.parse(huds[0].args[3])
                context.globals["TriggerPlayer"] = None
                context.player.update(MovementCursor=0, MovementSpeed=350, MovementGravity=500)
                controls = context.parse(huds[0].args[2])
                self.assertIn("> Speed: 350% (10-1000%)", content.evaluate(context))
                context.player.update(MovementCursor=1, MovementSpeed=10, MovementGravity=0)
                rendered = content.evaluate(context)
                self.assertIn("  Speed: 10% (10-1000%)", rendered)
                self.assertIn("> Gravity: 0% (0-500%)", rendered)
                for cursor, speed, gravity, up, down in (
                    (0, 100, 90, 50, 10),
                    (0, 90, 450, 10, 10),
                    (1, 450, 100, 50, 10),
                    (1, 100, 90, 10, 10),
                ):
                    context.player.update(MovementCursor=cursor, MovementSpeed=speed, MovementGravity=gravity)
                    rendered = controls.evaluate(context)
                    self.assertRegex(rendered, rf"<PrimaryFire>: \+{up}(?:\.0)?%")
                    self.assertRegex(rendered, rf"<SecondaryFire>: -{down}(?:\.0)?%")


if __name__ == "__main__":
    unittest.main()
