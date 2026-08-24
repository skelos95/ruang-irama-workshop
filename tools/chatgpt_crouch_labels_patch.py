#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    ROOT / "workshop" / "ruang_irama.it-IT.workshop",
    ROOT / "tests" / "fixtures" / "semantic_reference.txt",
]


def replace_exact(text: str, old: str, new: str, label: str, count: int = 1) -> str:
    found = text.count(old)
    if found != count:
        raise RuntimeError(f"{label}: expected {count}, found {found}")
    return text.replace(old, new, count)


for path in SOURCES:
    text = path.read_text(encoding="utf-8")
    text = replace_exact(text, "8 - CROUCH TELEPORT\\nCURRENT: {0}", "8 - CROUCH TRAVEL & ATTACH\\nCURRENT: {0}", "english main label")
    text = replace_exact(text, "8 - TELEPORT JONGKOK\\nSAAT INI: {0}", "8 - JONGKOK: PINDAH & TEMPEL\\nSAAT INI: {0}", "indonesian main label")
    text = replace_exact(text, "8 - เทเลพอร์ตตอนย่อ\\nสถานะ: {0}", "8 - ย่อ: เทเลพอร์ต + เกาะ\\nสถานะ: {0}", "thai main label")
    text = replace_exact(text, "8 - CROUCH TELEPORT {0}/2\\nCURRENT: {1}", "8 - CROUCH TRAVEL & ATTACH {0}/2\\nCURRENT: {1}", "english toggle label")
    text = replace_exact(text, "8 - TELEPORT JONGKOK {0}/2\\nSAAT INI: {1}", "8 - JONGKOK: PINDAH & TEMPEL {0}/2\\nSAAT INI: {1}", "indonesian toggle label")
    text = replace_exact(text, "8 - เทเลพอร์ตตอนย่อ {0}/2\\nสถานะ: {1}", "8 - ย่อ: เทเลพอร์ต + เกาะ {0}/2\\nสถานะ: {1}", "thai toggle label")

    text = replace_exact(text,
        'Custom String("{0}: next | {1}: previous | {2}: action", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire)), Input Binding String(Button(Interact))), Custom String("release {0}: close | {1}: detach", Input Binding String(Button(Crouch)), Input Binding String(Button(Reload)))',
        'Custom String("HOLD {0} FOR ALL COMMANDS\\n{1}: next | {2}: previous | {3}: action", Input Binding String(Button(Crouch)), Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire)), Input Binding String(Button(Interact))), Custom String("release {0}: close | {0} + {1}: detach", Input Binding String(Button(Crouch)), Input Binding String(Button(Reload)))',
        "english runtime instructions")
    text = replace_exact(text,
        'Custom String("{0}: berikutnya | {1}: sebelumnya | {2}: aksi", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire)), Input Binding String(Button(Interact))), Custom String("lepas {0}: tutup | {1}: lepas tempel", Input Binding String(Button(Crouch)), Input Binding String(Button(Reload)))',
        'Custom String("TAHAN {0} UNTUK SEMUA PERINTAH\\n{1}: berikutnya | {2}: sebelumnya | {3}: aksi", Input Binding String(Button(Crouch)), Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire)), Input Binding String(Button(Interact))), Custom String("lepas {0}: tutup | {0} + {1}: lepas tempel", Input Binding String(Button(Crouch)), Input Binding String(Button(Reload)))',
        "indonesian runtime instructions")
    text = replace_exact(text,
        'Custom String("{0}: ถัดไป | {1}: ก่อนหน้า | {2}: ใช้งาน", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire)), Input Binding String(Button(Interact))), Custom String("ปล่อย {0}: ปิด | {1}: ปล่อยตัว", Input Binding String(Button(Crouch)), Input Binding String(Button(Reload)))',
        'Custom String("กด {0} ค้างสำหรับทุกคำสั่ง\\n{1}: ถัดไป | {2}: ก่อนหน้า | {3}: ใช้งาน", Input Binding String(Button(Crouch)), Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire)), Input Binding String(Button(Interact))), Custom String("ปล่อย {0}: ปิด | {0} + {1}: ปล่อยตัว", Input Binding String(Button(Crouch)), Input Binding String(Button(Reload)))',
        "thai runtime instructions")

    replacements = {
        "TELEPORT 1/4\\n> SPAWN ROOM\\nINTERACT: TELEPORT": "SPAWN TRAVEL 1/4\\n> RETURN TO SPAWN ROOM\\nINTERACT: TELEPORT",
        "TELEPORT 2/4\\n> OBJECTIVE / FLAG\\nINTERACT: TELEPORT": "OBJECTIVE TRAVEL 2/4\\n> JUMP TO OBJECTIVE / ENEMY FLAG\\nINTERACT: TELEPORT",
        "TELEPORT 3/4\\n> PLAYER / BOT\\nTARGET: {0}\\nINTERACT: TELEPORT": "PLAYER / BOT TRAVEL 3/4\\n> TELEPORT NEXT TO TARGET\\nTARGET: {0}\\nINTERACT: TELEPORT",
        "TELEPORT 4/4\\n> ATTACH ABOVE PLAYER / BOT\\nTARGET: {0}\\nINTERACT: ATTACH | RELOAD: DETACH": "PLAYER / BOT ATTACH 4/4\\n> RIDE ABOVE TARGET\\nTARGET: {0}\\nINTERACT: ATTACH | CROUCH + RELOAD: DETACH",
        "TELEPORT 1/4\\n> RUANG MUNCUL\\nINTERACT: TELEPORT": "PINDAH KE SPAWN 1/4\\n> KEMBALI KE RUANG MUNCUL\\nINTERACT: TELEPORT",
        "TELEPORT 2/4\\n> OBJEKTIF / BENDERA\\nINTERACT: TELEPORT": "PINDAH KE OBJEKTIF 2/4\\n> LOMPAT KE OBJEKTIF / BENDERA MUSUH\\nINTERACT: TELEPORT",
        "TELEPORT 3/4\\n> PLAYER / BOT\\nTARGET: {0}\\nINTERACT: TELEPORT": "PINDAH KE PLAYER / BOT 3/4\\n> TELEPORT DI DEKAT TARGET\\nTARGET: {0}\\nINTERACT: TELEPORT",
        "TELEPORT 4/4\\n> TEMPEL DI ATAS PLAYER / BOT\\nTARGET: {0}\\nINTERACT: TEMPEL | RELOAD: LEPAS": "TEMPEL PLAYER / BOT 4/4\\n> NAIK DI ATAS TARGET\\nTARGET: {0}\\nINTERACT: TEMPEL | JONGKOK + RELOAD: LEPAS",
        "เทเลพอร์ต 1/4\\n> ห้องเกิด\\nใช้งาน: เทเลพอร์ต": "กลับห้องเกิด 1/4\\n> เทเลพอร์ตกลับห้องเกิด\\nใช้งาน: เทเลพอร์ต",
        "เทเลพอร์ต 2/4\\n> เป้าหมาย / ธง\\nใช้งาน: เทเลพอร์ต": "ไปเป้าหมาย 2/4\\n> เทเลพอร์ตไปเป้าหมาย / ธงศัตรู\\nใช้งาน: เทเลพอร์ต",
        "เทเลพอร์ต 3/4\\n> ผู้เล่น / บอต\\nเป้าหมาย: {0}\\nใช้งาน: เทเลพอร์ต": "ไปหาผู้เล่น / บอต 3/4\\n> เทเลพอร์ตข้างเป้าหมาย\\nเป้าหมาย: {0}\\nใช้งาน: เทเลพอร์ต",
        "เทเลพอร์ต 4/4\\n> เกาะเหนือผู้เล่น / บอต\\nเป้าหมาย: {0}\\nใช้งาน: เกาะ | รีโหลด: ปล่อย": "เกาะผู้เล่น / บอต 4/4\\n> เกาะเหนือเป้าหมาย\\nเป้าหมาย: {0}\\nใช้งาน: เกาะ | ย่อ + รีโหลด: ปล่อย",
    }
    for old, new in replacements.items():
        text = replace_exact(text, old, new, f"HUD label {old[:24]}")

    old_rule_guard = "\t\tEvent Player.LampiranTeleportasiAktif == True;\n\t\tIs Button Held(Event Player, Button(Reload)) == True;"
    new_rule_guard = "\t\tEvent Player.LampiranTeleportasiAktif == True;\n\t\tIs Button Held(Event Player, Button(Crouch)) == True;\n\t\tIs Button Held(Event Player, Button(Reload)) == True;"
    text = replace_exact(text, old_rule_guard, new_rule_guard, "crouch reload detach guard")

    text = replace_exact(text, "Attached above {0}. RELOAD detaches.", "Attached above {0}. CROUCH + RELOAD detaches.", "english attach hint")
    text = replace_exact(text, "Menempel di atas {0}. RELOAD untuk lepas.", "Menempel di atas {0}. JONGKOK + RELOAD untuk lepas.", "indonesian attach hint")
    text = replace_exact(text, "เกาะอยู่เหนือ {0} กดรีโหลดเพื่อปล่อย", "เกาะอยู่เหนือ {0} กดย่อ + รีโหลดเพื่อปล่อย", "thai attach hint")
    path.write_text(text, encoding="utf-8")

# Update focused regression test.
test_path = ROOT / "tests" / "test_runtime_maintenance.py"
test = test_path.read_text(encoding="utf-8")
old = '''    def test_crouch_attach_uses_native_attach_and_reload_detach(self):
        for source in (self.it, self.en):
            self.assertIn("Attach Players(Event Player, Event Player.TargetLampiranTeleportasi, Vector(0,", source)
            self.assertIn("+ 0.750, 0));", source)
            self.assertIn("Detach Players(Event Player);", source)
            self.assertIn("Is Button Held(Event Player, Button(Reload)) == True;", source)
            self.assertIn("99: TargetLampiranTeleportasi", source)
            self.assertIn("100: LampiranTeleportasiAktif", source)
'''
new = '''    def test_crouch_attach_uses_native_attach_and_crouch_reload_detach(self):
        for source, rule_kw in ((self.it, "regola"), (self.en, "rule")):
            self.assertIn("Attach Players(Event Player, Event Player.TargetLampiranTeleportasi, Vector(0,", source)
            self.assertIn("+ 0.750, 0));", source)
            self.assertIn("Detach Players(Event Player);", source)
            detach_rule = source.split(f'{rule_kw}("19f - Teleportasi Jongkok: Reload melepas lampiran")', 1)[1].split(f'{rule_kw}("19h - Teleportasi Jongkok', 1)[0]
            self.assertIn("Is Button Held(Event Player, Button(Crouch)) == True;", detach_rule)
            self.assertIn("Is Button Held(Event Player, Button(Reload)) == True;", detach_rule)
            self.assertIn("CROUCH + RELOAD: DETACH", source)
            self.assertIn("99: TargetLampiranTeleportasi", source)
            self.assertIn("100: LampiranTeleportasiAktif", source)
'''
test = replace_exact(test, old, new, "focused attach test")
test_path.write_text(test, encoding="utf-8")

changelog = ROOT / "CHANGELOG.md"
ch = changelog.read_text(encoding="utf-8")
anchor = "## Unreleased\n"
if anchor in ch and "Crouch Travel & Attach" not in ch:
    ch = ch.replace(anchor, anchor + "- Crouch Travel & Attach: HUD più descrittivo; detach manuale solo con Crouch + Reload.\n", 1)
    changelog.write_text(ch, encoding="utf-8")

print("Crouch Travel HUD labels and Crouch+Reload detach patched")
