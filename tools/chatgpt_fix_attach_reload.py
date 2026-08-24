#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    ROOT / "workshop" / "ruang_irama.it-IT.workshop",
    ROOT / "tests" / "fixtures" / "semantic_reference.txt",
]

for path in SOURCES:
    text = path.read_text(encoding="utf-8")

    attach_line = "\t\t\t\tAttach Players(Event Player, Event Player.TargetLampiranTeleportasi, Vector(0, Y Component Of(Eye Position(Event Player.TargetLampiranTeleportasi)) - Y Component Of(Position Of(Event Player.TargetLampiranTeleportasi)) + 0.750, 0));\n"
    blocked = attach_line + "\t\t\t\tDisallow Button(Event Player, Button(Reload));\n"
    if text.count(blocked) != 1:
        raise RuntimeError(f"{path.name}: expected one attach Reload block, found {text.count(blocked)}")
    text = text.replace(blocked, attach_line, 1)

    rule_kw = "regola" if path.suffix == ".workshop" else "rule"
    start_marker = f'{rule_kw}("19f - Teleportasi Jongkok: Reload melepas lampiran")'
    end_marker = f'{rule_kw}("19g - Teleportasi Jongkok: Tutup saat Jongkok dilepas")'
    if start_marker not in text or end_marker not in text:
        raise RuntimeError(f"{path.name}: attach detach rule markers not found")
    before, rest = text.split(start_marker, 1)
    segment, after = rest.split(end_marker, 1)
    allow = "\t\tAllow Button(Event Player, Button(Reload));\n"
    if segment.count(allow) != 6:
        raise RuntimeError(f"{path.name}: expected 6 attach-owned Allow Button(Reload), found {segment.count(allow)}")
    segment = segment.replace(allow, "")
    text = before + start_marker + segment + end_marker + after
    path.write_text(text, encoding="utf-8")

# Strengthen focused regression coverage.
test_path = ROOT / "tests" / "test_runtime_maintenance.py"
test = test_path.read_text(encoding="utf-8")
old = '''            detach_rule = source.split(f'{rule_kw}("19f - Teleportasi Jongkok: Reload melepas lampiran")', 1)[1].split(f'{rule_kw}("19h - Teleportasi Jongkok', 1)[0]\n            self.assertIn("Is Button Held(Event Player, Button(Crouch)) == True;", detach_rule)\n            self.assertIn("Is Button Held(Event Player, Button(Reload)) == True;", detach_rule)\n            self.assertIn("CROUCH + RELOAD: DETACH", source)\n'''
new = '''            attach_rule = source.split(f'{rule_kw}("19e - Teleportasi Jongkok: Interact menjalankan halaman aktif")', 1)[1].split(f'{rule_kw}("19f - Teleportasi Jongkok', 1)[0]\n            detach_rules = source.split(f'{rule_kw}("19f - Teleportasi Jongkok: Reload melepas lampiran")', 1)[1].split(f'{rule_kw}("19g - Teleportasi Jongkok', 1)[0]\n            manual_detach = detach_rules.split(f'{rule_kw}("19h - Teleportasi Jongkok', 1)[0]\n            self.assertIn("Is Button Held(Event Player, Button(Crouch)) == True;", manual_detach)\n            self.assertIn("Is Button Held(Event Player, Button(Reload)) == True;", manual_detach)\n            self.assertNotIn("Disallow Button(Event Player, Button(Reload));", attach_rule)\n            self.assertNotIn("Allow Button(Event Player, Button(Reload));", detach_rules)\n            self.assertIn("CROUCH + RELOAD: DETACH", source)\n'''
if test.count(old) != 1:
    raise RuntimeError(f"focused regression anchor expected once, found {test.count(old)}")
test = test.replace(old, new, 1)
test_path.write_text(test, encoding="utf-8")

print("Attach no longer owns Reload; Crouch+Reload still detaches")
