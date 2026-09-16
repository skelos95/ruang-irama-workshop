"""Execute the source recording controls with telemetry both enabled and disabled."""
import unittest

from tools import validate_workshop as validator
from tests.test_audit_lifecycle import AuditLifecycleEvaluator, project, statements
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


class DiagnosticsRecordingTests(unittest.TestCase):
    def test_telemetry_toggle_never_enables_inspector_recording(self):
        for path, _, _ in SOURCES:
            for diagnostics in (False, True):
                with self.subTest(source=path.name, diagnostics=diagnostics):
                    model = RecordingEvaluator(path.read_text(encoding="utf-8"))
                    model.globals["DiagnostikPerforma"] = diagnostics
                    init = next(rule for rule in model.rules if rule.name.startswith("00 - "))
                    actions = validator.rule_block(init, "actions")
                    model.execute(project(statements(actions), lambda token: token in (
                        "Disable Inspector Recording", "Enable Inspector Recording")))
                    self.assertFalse(model.recording)
                    self.assertEqual(model.globals["DiagnostikPerforma"], diagnostics)

    def gate_errors(self, source):
        checks = validator.Checks()
        validator.validate_inspector_recording(checks, source, validator.extract_rules(source))
        return checks.errors

    def test_gate_rejects_recording_coupled_to_diagnostics(self):
        source = validator.SOURCE.read_text(encoding="utf-8")
        changed = source.replace("Disable Inspector Recording;",
            "If(Global.DiagnostikPerforma == False);\nDisable Inspector Recording;\nEnd;", 1)
        self.assertTrue(self.gate_errors(changed))

    def test_gate_rejects_missing_disable_and_later_enable(self):
        source = validator.SOURCE.read_text(encoding="utf-8")
        self.assertFalse(self.gate_errors(source))
        for replacement in ("", "Disable Inspector Recording;\nEnable Inspector Recording;"):
            with self.subTest(replacement=replacement):
                self.assertTrue(self.gate_errors(source.replace("Disable Inspector Recording;", replacement, 1)))


if __name__ == "__main__":
    unittest.main()
