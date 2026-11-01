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
        # Reset confirmation is native presentation; this model checks state
        # and the immediate physics boundary, independently of message rendering.
        for call in reversed(list(validator.iter_calls(actions, "Small Message"))):
            actions = actions[:call.start] + actions[call.end:]
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

    def test_main_menu_reaches_all_twenty_one_entries_in_both_directions(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.viewer(MenuPage=-1, MainMenuCursor=0)
                visited = []
                for _ in range(21):
                    visited.append(state["MainMenuCursor"])
                    model.run("06", "viewer")
                self.assertEqual(visited, list(range(21)))
                self.assertEqual(state["MainMenuCursor"], 0)
                state["MenuCommand"] = 4
                model.run("06", "viewer")
                self.assertEqual(state["MainMenuCursor"], 20)

    def test_primary_and_secondary_apply_the_step_for_the_selected_value_immediately(self):
        for source, model in self.models():
            for cursor, field in ((0, "MovementSpeed"), (1, "MovementGravity")):
                for start, command, expected in ((100, 3, 200), (100, 4, 80),
                                                 (80, 3, 100), (80, 4, 60),
                                                 (200, 3, 300), (200, 4, 100)):
                    with self.subTest(source=source, field=field, start=start, command=command):
                        state = model.viewer(MovementCursor=cursor, MenuCommand=command, **{field: start})
                        model.run("06", "viewer")
                        self.assertEqual(state[field], expected)
                        self.assertEqual(state["MovementGravity" if cursor == 0 else "MovementSpeed"], 100)
                        self.assertEqual(model.physics_updates[-1],
                                         ("viewer", state["MovementSpeed"], state["MovementGravity"]))

    def test_speed_and_gravity_clamp_instead_of_wrapping(self):
        cases = ((0, "MovementSpeed", 20, 4, 20),
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
        ranges = ((0, "MovementSpeed", list(range(20, 101, 20)) + list(range(200, 1001, 100))),
                  (1, "MovementGravity", list(range(0, 101, 20)) + list(range(200, 501, 100))))
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
                state = model.viewer(MenuCommand=1, MovementSpeed=400, MovementGravity=300)
                for expected in (1, 0, 1):
                    model.run("10", "viewer")
                    self.assertEqual(state["MovementCursor"], expected)
                self.assertEqual(model.physics_updates, [])
                state["MenuCommand"] = 2
                model.run("11", "viewer")
                self.assertEqual(state["MenuPage"], -1)
                self.assertEqual((state["MovementSpeed"], state["MovementGravity"]), (400, 300))

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
                self.assertEqual(model.physics_updates, [("viewer", 200, 100)])

    def test_contextual_reset_restores_both_parameters_and_only_its_owner_immediately(self):
        for source, model in self.models():
            other = model.viewer("other", MovementCursor=1, MovementSpeed=600, MovementGravity=0)
            before = dict(other)
            for page in (-1, 16):
                for fly in (False, True):
                    owner = f"viewer-{page}-{fly}"
                    with self.subTest(source=source, page=page, fly=fly):
                        state = model.viewer(owner, MenuPage=page, MenuCommand=7, MovementCursor=1,
                                             MovementSpeed=1000, MovementGravity=0,
                                             GhostFlyPhysicsApplied=True, FlyModeActive=fly,
                                             GhostModeActive=True)
                        model.run("10", owner)
                        self.assertEqual((state["MovementSpeed"], state["MovementGravity"], state["MovementCursor"]),
                                         (100, 100, 0))
                        self.assertEqual((state["MenuPage"], state["MainMenuCursor"]), (page, 16))
                        self.assertEqual((state["FlyModeActive"], state["GhostModeActive"]), (fly, True))
                        self.assertFalse(state["GhostFlyPhysicsApplied"])
                        self.assertEqual(model.physics_updates[-1], (owner, 100, 100))
                        self.assertEqual(other, before)

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
                self.assertEqual((state["MovementSpeed"], state["MovementGravity"]), (200, 100))
                self.assertEqual(model.physics_updates, [("viewer", 200, 100)])
                model.input("viewer")
                model.input("viewer", "Secondary Fire", ticks=20)
                self.assertEqual(state["MovementSpeed"], 100)
                model.input("viewer")
                model.input("viewer", "Secondary Fire", ticks=20)
                self.assertEqual(state["MovementSpeed"], 80)
                self.assertEqual(model.physics_updates,
                                 [("viewer", 200, 100), ("viewer", 100, 100), ("viewer", 80, 100)])

    def test_one_live_hud_updates_values_and_selection_without_recreation(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.viewer()
                model.run("91u", "viewer")
                handle = state["MenuHud"]
                expression = model.hud_bodies[handle]
                self.assertIn("> Speed: 100% (20-1000%)", model.evaluate(expression))
                model.run("06", "viewer")
                self.assertIn("> Speed: 200% (20-1000%)", model.evaluate(expression))
                state["MenuCommand"] = 1
                model.run("10", "viewer")
                self.assertIn("> Gravity: 100% (0-500%)", model.evaluate(expression))
                state["MenuCommand"] = 4
                model.run("06", "viewer")
                self.assertIn("> Gravity: 80% (0-500%)", model.evaluate(expression))
                self.assertEqual(state["MenuHud"], handle)
                self.assertEqual(model.created_huds, [("viewer", handle)])
                self.assertEqual(model.destroyed_huds, [])

    def test_main_preview_and_movement_bindings_display_the_actual_values(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.viewer(MovementSpeed=400, MovementGravity=300)
                model.run("91a", "viewer")
                preview = model.evaluate(model.hud_bodies[state["MenuHud"]])
                self.assertIn("16 - SPEED / GRAVITY", preview)
                self.assertIn("SPEED: 400% | GRAVITY: 300%", preview)
                rule = validator.rule_by_subroutine(model.rules, "DrawMovementMenu")
                hud = next(validator.iter_calls(rule.body, "Create HUD Text"))
                model.event_player = "viewer"
                controls = model.evaluate(hud.args[2])
                for label in ("Crouch", "Primary Fire +100%", "Secondary Fire -100%",
                              "Interact Speed/Gravity", "Reload back", "Melee",
                              "Ultimate 100% both"):
                    self.assertIn(label, controls)

    def test_live_bindings_follow_the_selected_parameter_and_the_hundred_boundary(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.viewer(MovementSpeed=100, MovementGravity=80)
                model.event_player = "viewer"
                rule = validator.rule_by_subroutine(model.rules, "DrawMovementMenu")
                hud = next(validator.iter_calls(rule.body, "Create HUD Text"))
                for cursor, speed, gravity, up, down in (
                    (0, 100, 80, 100, 20),
                    (0, 80, 400, 20, 20),
                    (0, 200, 80, 100, 100),
                    (1, 400, 80, 20, 20),
                    (1, 80, 100, 100, 20),
                    (1, 80, 200, 100, 100),
                ):
                    state.update(MovementCursor=cursor, MovementSpeed=speed, MovementGravity=gravity)
                    controls = model.evaluate(hud.args[2])
                    self.assertIn(f"Primary Fire +{up}%", controls)
                    self.assertIn(f"Secondary Fire -{down}%", controls)

    def test_bootstrap_has_domain_and_timer_in_right_subheader_above_host(self):
        for source, model in self.models():
            with self.subTest(source=source):
                bootstrap = model.rule("00")
                huds = list(validator.iter_calls(bootstrap.body, "Create HUD Text"))
                self.assertEqual(len(huds), 3)
                title = next(call for call in huds if call.args[4:6] == ("Right", "0"))
                self.assertEqual(title.args[2], 'Custom String("cozywatch.org [{0}]", Global.ServerTimeText)')
                self.assertIn(r'Custom String("\n{0} {1} {2}\n "', title.args[3])
                self.assertIn('Custom String("Host:")', title.args[3])
                self.assertEqual(title.args[7:9], ("Global.RGB", "Global.RGB"))
                self.assertFalse(any(call.args[4] == "Top" for call in huds))

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
                context.player.update(MovementCursor=0, MovementSpeed=400, MovementGravity=500)
                controls = context.parse(huds[0].args[2])
                self.assertIn("> Speed: 400% (20-1000%)", content.evaluate(context))
                context.player.update(MovementCursor=1, MovementSpeed=20, MovementGravity=0)
                rendered = content.evaluate(context)
                self.assertIn("  Speed: 20% (20-1000%)", rendered)
                self.assertIn("> Gravity: 0% (0-500%)", rendered)
                for cursor, speed, gravity, up, down in (
                    (0, 100, 80, 100, 20),
                    (0, 80, 400, 20, 20),
                    (1, 400, 100, 100, 20),
                    (1, 100, 80, 20, 20),
                ):
                    context.player.update(MovementCursor=cursor, MovementSpeed=speed, MovementGravity=gravity)
                    rendered = controls.evaluate(context)
                    self.assertRegex(rendered, rf"<PrimaryFire> \+{up}(?:\.0)?%")
                    self.assertRegex(rendered, rf"<SecondaryFire> -{down}(?:\.0)?%")


if __name__ == "__main__":
    unittest.main()
