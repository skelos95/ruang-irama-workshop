#!/usr/bin/env python3
# Final one-shot alignment helper; self-deletes after a successful patch.
from pathlib import Path

path = Path("tools/validate_workshop.py")
text = path.read_text(encoding="utf-8")

old_objective = '    objective_rule = next((rule for rule in rules if "Payload Position" in rule.body and "Flag Position(" in rule.body and "Objective Position(Objective Index)" in rule.body), None)'
new_objective = '    objective_rule = next((rule for rule in rules if "PerintahTeleportasi == 1" in rule.body and "Payload Position" in rule.body and "Flag Position(" in rule.body and "Objective Position(Objective Index)" in rule.body), None)'
if old_objective not in text:
    raise SystemExit("objective dispatcher validator anchor missing")
text = text.replace(old_objective, new_objective, 1)

old_raycast = '    checks.equal(source.count("Ray Cast Hit Position("), 1, "raycast Camera")'
new_raycast = '''    camera_rule = rule_by_subroutine(rules, "MulaiKamera")
    checks.require(camera_rule is not None, "subroutine Camera assente")
    if camera_rule:
        checks.equal(camera_rule.body.count("Ray Cast Hit Position("), 1, "raycast Camera")'''
if old_raycast not in text:
    raise SystemExit("camera raycast validator anchor missing")
text = text.replace(old_raycast, new_raycast, 1)
path.write_text(text, encoding="utf-8")

test_path = Path("tests/test_validate_workshop.py")
tests = test_path.read_text(encoding="utf-8")
old_test = '''    def test_camera_has_exactly_one_raycast(self) -> None:
        mutated = self.source + "\\nRay Cast Hit Position(Eye Position(Event Player), Vector(0, 0, 0), Null, Null, False);\\n"
        self.assert_rejected(mutated, "raycast Camera")
'''
new_test = '''    def test_camera_has_exactly_one_raycast(self) -> None:
        camera_rule = validator.rule_by_subroutine(validator.extract_rules(self.source), "MulaiKamera")
        self.assertIsNotNone(camera_rule)
        assert camera_rule is not None
        mutated_body = camera_rule.body.replace(
            "Ray Cast Hit Position(",
            "Ray Cast Hit Position(Eye Position(Event Player), Vector(0, 0, 0), Empty Array, Empty Array, False) + Ray Cast Hit Position(",
            1,
        )
        mutated = self.source[:camera_rule.start] + mutated_body + self.source[camera_rule.end:]
        self.assert_rejected(mutated, "raycast Camera")
'''
if old_test not in tests:
    raise SystemExit("camera raycast unit-test anchor missing")
tests = tests.replace(old_test, new_test, 1)
test_path.write_text(tests, encoding="utf-8")

Path(__file__).unlink()
