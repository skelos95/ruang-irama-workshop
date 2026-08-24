#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    ROOT / "workshop" / "ruang_irama.it-IT.workshop",
    ROOT / "tests" / "fixtures" / "semantic_reference.txt",
]

REPLACEMENTS = {
    'Custom String("HOLD {0} FOR ALL COMMANDS\\n{1}: next | {2}: previous | {3}: action", Input Binding String(Button(Crouch)), Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire)), Input Binding String(Button(Interact)))':
        'Custom String("{0}\\n{1}", Custom String("HOLD {0} FOR ALL COMMANDS", Input Binding String(Button(Crouch))), Custom String("{0}: next | {1}: previous | {2}: action", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire)), Input Binding String(Button(Interact))))',
    'Custom String("TAHAN {0} UNTUK SEMUA PERINTAH\\n{1}: berikutnya | {2}: sebelumnya | {3}: aksi", Input Binding String(Button(Crouch)), Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire)), Input Binding String(Button(Interact)))':
        'Custom String("{0}\\n{1}", Custom String("TAHAN {0} UNTUK SEMUA PERINTAH", Input Binding String(Button(Crouch))), Custom String("{0}: berikutnya | {1}: sebelumnya | {2}: aksi", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire)), Input Binding String(Button(Interact))))',
    'Custom String("กด {0} ค้างสำหรับทุกคำสั่ง\\n{1}: ถัดไป | {2}: ก่อนหน้า | {3}: ใช้งาน", Input Binding String(Button(Crouch)), Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire)), Input Binding String(Button(Interact)))':
        'Custom String("{0}\\n{1}", Custom String("กด {0} ค้างสำหรับทุกคำสั่ง", Input Binding String(Button(Crouch))), Custom String("{0}: ถัดไป | {1}: ก่อนหน้า | {2}: ใช้งาน", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire)), Input Binding String(Button(Interact))))',
}

for path in SOURCES:
    text = path.read_text(encoding="utf-8")
    for old, new in REPLACEMENTS.items():
        found = text.count(old)
        if found != 1:
            raise RuntimeError(f"{path.name}: expected exactly one occurrence, found {found}: {old[:72]}")
        text = text.replace(old, new, 1)
    if "{3}" in text:
        raise RuntimeError(f"{path.name}: unsupported Custom String placeholder {{3}} remains")
    path.write_text(text, encoding="utf-8")

# Add a regression test so Workshop's max-three substitution-value limit is enforced.
test_path = ROOT / "tests" / "test_runtime_maintenance.py"
test = test_path.read_text(encoding="utf-8")
anchor = '\nif __name__ == "__main__":\n    unittest.main()\n'
method = '''\n    def test_custom_string_uses_at_most_three_substitution_values(self):\n        for source in (self.it, self.en):\n            self.assertNotIn("{3}", source)\n            self.assertIn('Custom String("{0}\\\\n{1}", Custom String("HOLD {0} FOR ALL COMMANDS"', source)\n\n'''
if method.strip() not in test:
    if anchor not in test:
        raise RuntimeError("test insertion anchor not found")
    test = test.replace(anchor, method + anchor, 1)
test_path.write_text(test, encoding="utf-8")

print("Fixed four-value Custom String HUD instructions and added regression coverage")
