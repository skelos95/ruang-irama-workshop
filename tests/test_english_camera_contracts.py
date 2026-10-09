"""Mutations of English-only naming and native camera reset boundaries."""

from __future__ import annotations

import unittest

from tools import validate_workshop as validator


class EnglishCameraContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = validator.SOURCE.read_text(encoding="utf-8")

    def changed_rule(self, name: str, old: str, new: str) -> str:
        rule = validator.rule_by_subroutine(validator.extract_rules(self.source), name)
        self.assertIsNotNone(rule)
        self.assertEqual(rule.body.count(old), 1, (name, old))
        return self.source[:rule.start] + rule.body.replace(old, new, 1) + self.source[rule.end:]

    def camera_errors(self, source: str) -> list[str]:
        checks = validator.Checks()
        validator.validate_modes_and_camera(checks, source, validator.extract_rules(source))
        return checks.errors

    def assert_camera_rejected(self, source: str, reason: str) -> None:
        self.assertTrue(any(reason in error for error in self.camera_errors(source)), reason)

    def test_current_camera_boundaries_pass(self) -> None:
        self.assertEqual(self.camera_errors(self.source), [])

    def test_camera_menu_rejects_same_mode_or_target_shortcuts(self) -> None:
        for target, mode, indent in (("Event Player", 1, "\t\t\t"),
                                     ("Event Player.CameraTargetCandidate", 2, "\t\t\t\t")):
            with self.subTest(mode=mode):
                block = "\n".join(indent + action for action in (
                    "Stop Camera(Event Player);",
                    f"Event Player.CameraTarget = {target};",
                    f"Event Player.CameraMode = {mode};",
                    "Global.CameraPlayer = Event Player;",
                    "Call Subroutine(StartCamera);",
                    "Global.CameraPlayer = Null;",
                ))
                guarded = (indent + f"If(Or(Event Player.CameraMode != {mode}, Event Player.CameraTarget != {target}));\n"
                           + block + "\n" + indent + "End;")
                changed = self.changed_rule("ApplyCameraPage", block, guarded)
                self.assert_camera_rejected(changed, "Camera menu: explicit apply must recreate the native camera")

    def test_camera_menu_requires_stop_before_both_native_start_branches(self) -> None:
        for target, mode, indent in (("Event Player", 1, "\t\t\t"),
                                     ("Event Player.CameraTargetCandidate", 2, "\t\t\t\t")):
            block = "\n".join(indent + action for action in (
                "Stop Camera(Event Player);",
                f"Event Player.CameraTarget = {target};",
                f"Event Player.CameraMode = {mode};",
                "Global.CameraPlayer = Event Player;",
                "Call Subroutine(StartCamera);",
                "Global.CameraPlayer = Null;",
            ))
            without_stop = block.replace(indent + "Stop Camera(Event Player);\n", "", 1)
            late_stop = without_stop.replace("Call Subroutine(StartCamera);",
                "Call Subroutine(StartCamera);\n" + indent + "Stop Camera(Event Player);", 1)
            for kind, replacement in (("missing", without_stop), ("late", late_stop)):
                with self.subTest(mode=mode, stop=kind):
                    changed = self.changed_rule("ApplyCameraPage", block, replacement)
                    self.assert_camera_rejected(changed, "Camera menu: stop before every valid start")

    def test_every_travel_route_requires_native_stop_before_teleport(self) -> None:
        for routine in ("TravelToSpawn", "TravelToObjective", "TravelToPlayer"):
            with self.subTest(routine=routine):
                changed = self.changed_rule(routine, "Stop Camera(Event Player);", "")
                self.assert_camera_rejected(changed, f"Camera Travel {routine}")

    def test_travel_restart_requires_same_explicit_owner(self) -> None:
        for routine in ("TravelToSpawn", "TravelToObjective", "TravelToPlayer"):
            with self.subTest(routine=routine):
                changed = self.changed_rule(routine, "Global.CameraPlayer = Event Player;",
                                            "Global.CameraPlayer = Global.ActivePlayer;")
                self.assert_camera_rejected(changed, "riavvio protetto immediatamente dopo")

    def test_own_hero_reset_cannot_run_on_unchanged_hero(self) -> None:
        changed = self.changed_rule("ProcessPlayerCycle",
                                    "Hero Of(Global.ActivePlayer) != Global.ActivePlayer.LastHero",
                                    "Hero Of(Global.ActivePlayer) == Global.ActivePlayer.LastHero")
        self.assert_camera_rejected(changed, "mai a ogni tick")

    def test_own_hero_reset_requires_the_active_players_camera(self) -> None:
        changed = self.changed_rule("ProcessPlayerCycle", "Global.CameraPlayer = Global.ActivePlayer;",
                                    "Global.CameraPlayer = Event Player;")
        self.assert_camera_rejected(changed, "Camera attiva con bersaglio esistente")

    def test_central_camera_requires_valid_target_before_native_start(self) -> None:
        changed = self.changed_rule("StartCamera",
                                    "Abort If(Entity Exists(Global.CameraPlayer.CameraTarget) == False);", "")
        self.assert_camera_rejected(changed, "guardia proprietario/bersaglio")

    def test_english_cleanup_comments_pass_and_legacy_titles_fail(self) -> None:
        rules = validator.extract_rules(self.source)
        checks = validator.Checks()
        validator.validate_english_and_duplicates(checks, self.source, rules)
        self.assertEqual(checks.errors, [])
        first = rules[0]
        changed = self.source[:first.start] + first.body.replace(first.name, "00 - Umum: Siapkan pemain", 1) + self.source[first.end:]
        checks = validator.Checks()
        validator.validate_english_and_duplicates(checks, changed, validator.extract_rules(changed))
        self.assertTrue(any("titolo regola non interamente inglese" in error for error in checks.errors))


if __name__ == "__main__":
    unittest.main()
