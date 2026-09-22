"""Evaluate the real watch-camera guards; native entity timing is not simulated."""
import unittest

from tests.test_menu_load_regressions import MenuLoadEvaluator
from tests.test_roster_rejoin_regressions import SOURCES
from tools import validate_workshop as validator


class CameraEvaluator(MenuLoadEvaluator):
    def __init__(self, source):
        super().__init__(source)
        cycle = validator.rule_by_subroutine(self.rules, "ProsesSiklusPemain")
        stop = next(validator.iter_calls(cycle.body, "Stop Camera"))
        self.branches = validator.conditional_branches_containing(cycle.body, stop.start)
        self.camera_block = max(self.branches, key=len)
        self.stopped = []

    def resolve(self, name):
        if name.startswith("Global.PemainAktif"):
            value = self.globals["PemainAktif"]
            for field in name.split(".")[2:]:
                value = self.players.get(value, {}).get(field, False)
            return value
        return super().resolve(name)

    def tick(self, viewer):
        self.globals["PemainAktif"] = viewer
        for branch in self.branches:
            condition = next(validator.iter_calls(branch, "If")).args[0]
            if not self.evaluate(condition):
                return
        # Project the real stop/reset actions. Native effects and messages have
        # no bearing on camera ownership and are intentionally not simulated.
        for call in validator.iter_calls(self.camera_block, "Stop Camera"):
            self.stopped.append(self.evaluate(call.args[0]))
        for call in validator.iter_calls(self.camera_block, "Set Player Variable"):
            self.players[self.evaluate(call.args[0])][call.args[1].strip()] = self.evaluate(call.args[2])


class CameraTargetLifecycleTests(unittest.TestCase):
    def models(self):
        for path, _, _ in SOURCES:
            yield path.name, CameraEvaluator(path.read_text(encoding="utf-8"))

    def test_watch_stops_while_target_is_alive_but_in_team_quarantine(self):
        for source, model in self.models():
            with self.subTest(source=source):
                viewer = model.add("viewer", ModeKamera=2, TargetKamera="target")
                target = model.add("target", SiklusPemainAktif=False)
                model.tick("viewer")
                self.assertEqual(model.stopped, [])
                # These are the quarantine values set by rule 01a; existence,
                # spawn and life deliberately remain valid during transition.
                target.update(Manusia=False, SiklusPemainAktif=True)
                model.tick("viewer")
                self.assertEqual(model.stopped, ["viewer"])
                self.assertEqual(viewer["ModeKamera"], 0)
                self.assertIsNone(viewer["TargetKamera"])
                model.tick("viewer")
                self.assertEqual(model.stopped, ["viewer"])

    def test_twelve_viewers_reset_only_watchers_of_the_changing_target(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.add("changing", Manusia=False, SiklusPemainAktif=True)
                model.add("stable", SiklusPemainAktif=False)
                for index in range(12):
                    mode = 1 if index % 3 == 0 else 2
                    target = "stable" if index % 3 == 2 else "changing"
                    model.add(f"viewer{index}", ModeKamera=mode, TargetKamera=target)
                for index in range(12):
                    model.tick(f"viewer{index}")
                self.assertEqual(model.stopped, ["viewer1", "viewer4", "viewer7", "viewer10"])
                for index in (0, 3, 6, 9):
                    self.assertEqual(model.players[f"viewer{index}"]["ModeKamera"], 1)
                for index in (2, 5, 8, 11):
                    self.assertEqual(model.players[f"viewer{index}"]["TargetKamera"], "stable")

    def test_existing_invalid_targets_and_public_bots_keep_their_behavior(self):
        cases = (({"alive": False}, True), ({"exists": False}, True),
                 ({"spawned": False}, True), ({"PrivasiInspeksiAktif": True}, True),
                 ({"Manusia": False, "dummy": True}, False),
                 ({"Manusia": False, "BotOtomatis": True}, False))
        for path, _, _ in SOURCES:
            source = path.read_text(encoding="utf-8")
            for changes, should_stop in cases:
                with self.subTest(source=path.name, changes=changes):
                    model = CameraEvaluator(source)
                    model.add("viewer", ModeKamera=2, TargetKamera="target")
                    model.add("target", SiklusPemainAktif=False, **changes)
                    model.tick("viewer")
                    self.assertEqual(model.stopped, ["viewer"] if should_stop else [])


if __name__ == "__main__":
    unittest.main()
