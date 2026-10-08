"""Execute diagnostic visibility, colors and recording controls from the source."""
import unittest

from tools import validate_workshop as validator
from tests.test_audit_lifecycle import AuditLifecycleEvaluator, project, statements
from tests.test_menu_load_regressions import MenuLoadEvaluator
from tests.test_roster_rejoin_regressions import SOURCES


class RecordingEvaluator(AuditLifecycleEvaluator):
    def __init__(self, source):
        super().__init__(source)
        self.recording = True

    def execute(self, nodes):
        for node in nodes:
            if node[0] == "Disable Inspector Recording":
                self.recording = False
            elif node[0] == "Enable Inspector Recording":
                self.recording = True
            elif super().execute([node]):
                return True
        return False


class DiagnosticsHudEvaluator(MenuLoadEvaluator):
    """Reuse the menu expression evaluator with controlled native HUD values."""

    def __init__(self, source):
        super().__init__(source)
        self.host = "host"
        self.viewer = self.host
        for slot in range(12):
            self.add(self.host if slot == 0 else f"player-{slot}", HudSlot=slot,
                     DisplayName=f"player-{slot}", IconIndex=0,
                     CustomSoundtrack=None, GenreIndex=-1, NameColor=(255, 255, 255, 255))
        self.globals.update(PerformanceDiagnostics=True, LastHudSlot=11,
                            PlayerListHudIds=list(range(100, 112)),
                            MenuHudIds=[0, 200, 0, 201] + [0] * 8,
                            TemporaryEffectHudIds=[300, 301, 0, 302] + [0] * 20,
                            InspectionTextIds=[0, 400, 0, 401] + [0] * 8,
                            TemporaryTravelTextIds=[500] + [0] * 23,
                            TemporaryVisionTextIds=[600, 0, 601] + [0] * 21,
                            ObjectiveIconIds=list(range(700, 712)),
                            PlayerIcons=["icon"], GenreNames=["soundtrack"])
        self.hud = next(validator.iter_calls(self.rule("02").body, "Create HUD Text"))

    def resolve(self, name):
        native = {"LocalPlayer": self.viewer, "HostPlayer": self.host,
                  "ServerLoad": 12,
                  "ServerLoadAverage": 23, "ServerLoadPeak": 34,
                  "White": (255, 255, 255, 255)}
        return native[name] if name in native else super().resolve(name)

    def call(self, name, args):
        if name == "CustomColor":
            return tuple(args)
        if name == "IsDuplicating":
            return False
        if name == "HeroOf":
            return "Ana"
        if name == "HeroIconString":
            return "hero-icon"
        if name in ("EvaluateOnce", "Color"):
            return args[0]
        return super().call(name, args)


class DiagnosticsRecordingTests(unittest.TestCase):
    def test_only_host_sees_diagnostics_on_the_current_last_roster_slot(self):
        for path, _, _ in SOURCES:
            model = DiagnosticsHudEvaluator(path.read_text(encoding="utf-8"))
            for enabled in (False, True):
                model.globals["PerformanceDiagnostics"] = enabled
                for viewer in (model.host, "player-1"):
                    model.viewer = viewer
                    for last_slot in (11, 5, 0):
                        model.globals["LastHudSlot"] = last_slot
                        visible = []
                        for owner, state in model.players.items():
                            with self.subTest(source=path.name, enabled=enabled,
                                              viewer=viewer, last_slot=last_slot, owner=owner):
                                model.event_player = owner
                                previous_filters = model.filter_builds
                                text = model.evaluate(model.hud.args[3])
                                show = enabled and viewer == model.host and state["HudSlot"] == last_slot
                                if show:
                                    visible.append(owner)
                                    self.assertEqual(text.strip(),
                                        "LOAD 12% | AVG 23% | MAX 34%\nHUD 23 | IWT 5")
                                else:
                                    self.assertEqual(text, "")
                                    self.assertEqual(model.filter_builds, previous_filters)
                        self.assertEqual(len(visible), int(enabled and viewer == model.host))

    def test_diagnostics_stay_white_when_player_and_title_colors_change(self):
        for path, _, _ in SOURCES:
            model = DiagnosticsHudEvaluator(path.read_text(encoding="utf-8"))
            model.event_player = "player-11"
            player = model.players[model.event_player]
            row = model.evaluate(model.hud.args[2])
            diagnostic = model.evaluate(model.hud.args[3])
            self.assertEqual(row, "icon hero-icon player-11 - no soundtrack yet")
            self.assertIn("LOAD 12%", diagnostic)
            for name_color, title_rgb in (
                ((0, 0, 0, 255), (255, 0, 0, 255)),
                ((50, 120, 220, 255), (0, 255, 0, 255)),
                ((255, 255, 255, 255), (0, 0, 255, 255)),
            ):
                with self.subTest(source=path.name, name_color=name_color, title_rgb=title_rgb):
                    player["NameColor"] = name_color
                    model.globals["RGB"] = title_rgb
                    self.assertEqual(model.evaluate(model.hud.args[2]), row)
                    self.assertEqual(model.evaluate(model.hud.args[3]), diagnostic)
                    self.assertEqual(model.evaluate(model.hud.args[7]), name_color)
                    self.assertEqual(model.evaluate(model.hud.args[8]), (255, 255, 255, 255))

    def test_telemetry_toggle_never_enables_inspector_recording(self):
        for path, _, _ in SOURCES:
            for diagnostics in (False, True):
                with self.subTest(source=path.name, diagnostics=diagnostics):
                    model = RecordingEvaluator(path.read_text(encoding="utf-8"))
                    model.globals["PerformanceDiagnostics"] = diagnostics
                    init = next(rule for rule in model.rules if rule.name.startswith("00 - "))
                    actions = validator.rule_block(init, "actions")
                    model.execute(project(statements(actions), lambda token: token in (
                        "Disable Inspector Recording", "Enable Inspector Recording")))
                    self.assertFalse(model.recording)
                    self.assertEqual(model.globals["PerformanceDiagnostics"], diagnostics)

    def gate_errors(self, source):
        checks = validator.Checks()
        validator.validate_inspector_recording(checks, source, validator.extract_rules(source))
        return checks.errors

    def test_gate_rejects_recording_coupled_to_diagnostics(self):
        source = validator.SOURCE.read_text(encoding="utf-8")
        changed = source.replace("Disable Inspector Recording;",
            "If(Global.PerformanceDiagnostics == False);\nDisable Inspector Recording;\nEnd;", 1)
        self.assertTrue(self.gate_errors(changed))

    def test_gate_rejects_missing_disable_and_later_enable(self):
        source = validator.SOURCE.read_text(encoding="utf-8")
        self.assertFalse(self.gate_errors(source))
        for replacement in ("", "Disable Inspector Recording;\nEnable Inspector Recording;"):
            with self.subTest(replacement=replacement):
                self.assertTrue(self.gate_errors(source.replace("Disable Inspector Recording;", replacement, 1)))


if __name__ == "__main__":
    unittest.main()
