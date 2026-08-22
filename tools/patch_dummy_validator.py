#!/usr/bin/env python3
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
Path(__file__).unlink()
