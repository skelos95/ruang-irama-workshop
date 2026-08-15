from __future__ import annotations

from pathlib import Path
import hashlib
import re

SOURCE = Path("workshop/ruang_irama.workshop")
VALIDATOR = Path("tools/validate_workshop.py")
PROJECT = Path("docs/PROGETTO.md")
TESTS = Path("docs/TEST.md")
REPORT = Path("docs/VALIDAZIONE.md")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 occurrence, found {count}")
    return text.replace(old, new, 1)


src = SOURCE.read_text(encoding="utf-8")
start = src.index('rule("10 - Menu: Interaksi membuka atau menerapkan pilihan")')
end = src.index('\nrule("11 - Menu:', start)
rule = src[start:end]

# Soundtrack: applying the currently active genre is a true no-op.
old = '''\t\tElse If(Event Player.HalamanMenu == 0);\n\t\t\tEvent Player.IndeksGenre = Event Player.KursorGenre;\n\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String(\n\t\t\t\t"Soundtrack locked: {0}. Excellent taste, probably.", Global.DaftarGenre[Event Player.IndeksGenre]) : Event Player.IndeksBahasa == 1\n\t\t\t\t? Custom String("Soundtrack dipilih: {0}. Selera bagus. Mungkin.", Global.DaftarGenre[Event Player.IndeksGenre]) : Custom String(\n\t\t\t\t"เลือกเพลงประกอบแล้ว: {0} รสนิยมดี...น่าจะนะ", Global.DaftarGenre[Event Player.IndeksGenre]));\n\t\t\tCall Subroutine(GambarMenu);'''
new = '''\t\tElse If(Event Player.HalamanMenu == 0);\n\t\t\tIf(Event Player.IndeksGenre != Event Player.KursorGenre);\n\t\t\t\tEvent Player.IndeksGenre = Event Player.KursorGenre;\n\t\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String(\n\t\t\t\t\t"Soundtrack locked: {0}. Excellent taste, probably.", Global.DaftarGenre[Event Player.IndeksGenre]) : Event Player.IndeksBahasa == 1\n\t\t\t\t\t? Custom String("Soundtrack dipilih: {0}. Selera bagus. Mungkin.", Global.DaftarGenre[Event Player.IndeksGenre]) : Custom String(\n\t\t\t\t\t"เลือกเพลงประกอบแล้ว: {0} รสนิยมดี...น่าจะนะ", Global.DaftarGenre[Event Player.IndeksGenre]));\n\t\t\tEnd;\n\t\t\tCall Subroutine(GambarMenu);'''
rule = replace_once(rule, old, new, "soundtrack idempotence")

# Camera OFF: feedback only when leaving an active camera mode.
old = '''\t\t\tIf(Event Player.KursorKamera == 0);\n\t\t\t\tStop Camera(Event Player);\n\t\t\t\tEvent Player.ModeKamera = 0;\n\t\t\t\tEvent Player.TargetKamera = Null;\n\t\t\t\tCall Subroutine(EfekPulihkan);\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String(\n\t\t\t\t\t"First person restored. You may pretend that never happened.") : Event Player.IndeksBahasa == 1 ? Custom String(\n\t\t\t\t\t"Kamera orang pertama kembali. Tidak ada yang melihat tadi.") : Custom String(\n\t\t\t\t\t"กลับสู่มุมมองบุคคลที่หนึ่งแล้ว ทำเป็นว่าเมื่อกี้ไม่เกิดขึ้นก็ได้"));'''
new = '''\t\t\tIf(Event Player.KursorKamera == 0);\n\t\t\t\tIf(Event Player.ModeKamera != 0);\n\t\t\t\t\tStop Camera(Event Player);\n\t\t\t\t\tEvent Player.ModeKamera = 0;\n\t\t\t\t\tEvent Player.TargetKamera = Null;\n\t\t\t\t\tCall Subroutine(EfekPulihkan);\n\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String(\n\t\t\t\t\t\t"First person restored. You may pretend that never happened.") : Event Player.IndeksBahasa == 1 ? Custom String(\n\t\t\t\t\t\t"Kamera orang pertama kembali. Tidak ada yang melihat tadi.") : Custom String(\n\t\t\t\t\t\t"กลับสู่มุมมองบุคคลที่หนึ่งแล้ว ทำเป็นว่าเมื่อกี้ไม่เกิดขึ้นก็ได้"));\n\t\t\t\tEnd;'''
rule = replace_once(rule, old, new, "camera off idempotence")

# Camera self: do not restart/re-message when already viewing self in third person.
old = '''\t\t\tElse If(Event Player.KursorKamera == 1);\n\t\t\t\tEvent Player.TargetKamera = Event Player;\n\t\t\t\t"Biarkan frame Interact selesai sebelum mengganti render kamera."\n\t\t\t\tWait(0.016, Ignore Condition);\n\t\t\t\tEvent Player.ModeKamera = 1;\n\t\t\t\tCall Subroutine(MulaiKamera);\n\t\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String(\n\t\t\t\t\t"Third person enabled. Admire responsibly.") : Event Player.IndeksBahasa == 1 ? Custom String(\n\t\t\t\t\t"Orang ketiga aktif. Silakan mengagumi diri secukupnya.") : Custom String(\n\t\t\t\t\t"เปิดมุมมองบุคคลที่สามแล้ว ชื่นชมตัวเองแต่พอดี"));'''
new = '''\t\t\tElse If(Event Player.KursorKamera == 1);\n\t\t\t\tIf(Or(Event Player.ModeKamera != 1, Event Player.TargetKamera != Event Player));\n\t\t\t\t\tEvent Player.TargetKamera = Event Player;\n\t\t\t\t\t"Biarkan frame Interact selesai sebelum mengganti render kamera."\n\t\t\t\t\tWait(0.016, Ignore Condition);\n\t\t\t\t\tEvent Player.ModeKamera = 1;\n\t\t\t\t\tCall Subroutine(MulaiKamera);\n\t\t\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String(\n\t\t\t\t\t\t"Third person enabled. Admire responsibly.") : Event Player.IndeksBahasa == 1 ? Custom String(\n\t\t\t\t\t\t"Orang ketiga aktif. Silakan mengagumi diri secukupnya.") : Custom String(\n\t\t\t\t\t\t"เปิดมุมมองบุคคลที่สามแล้ว ชื่นชมตัวเองแต่พอดี"));\n\t\t\t\tEnd;'''
rule = replace_once(rule, old, new, "camera self idempotence")

# Spectating: only restart camera/feedback if target or mode actually changed.
old = '''\t\t\t\tIf(And(Event Player.CalonTargetKamera != Null, Entity Exists(Event Player.CalonTargetKamera)));\n\t\t\t\t\tEvent Player.TargetKamera = Event Player.CalonTargetKamera;\n\t\t\t\t\t"Gunakan jeda satu frame yang sama saat mulai menonton dari orang pertama."\n\t\t\t\t\tWait(0.016, Ignore Condition);\n\t\t\t\t\tEvent Player.ModeKamera = 2;\n\t\t\t\t\tCall Subroutine(MulaiKamera);\n\t\t\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String(\n\t\t\t\t\t\t"Now spectating {0}. Definitely not stalking.", Event Player.TargetKamera) : Event Player.IndeksBahasa == 1 ? Custom String(\n\t\t\t\t\t\t"Sekarang menonton {0}. Sama sekali bukan menguntit.", Event Player.TargetKamera) : Custom String(\n\t\t\t\t\t\t"กำลังชม {0} อยู่ นี่ไม่ใช่การสะกดรอยแน่นอน", Event Player.TargetKamera));'''
new = '''\t\t\t\tIf(And(Event Player.CalonTargetKamera != Null, Entity Exists(Event Player.CalonTargetKamera)));\n\t\t\t\t\tIf(Or(Event Player.ModeKamera != 2, Event Player.TargetKamera != Event Player.CalonTargetKamera));\n\t\t\t\t\t\tEvent Player.TargetKamera = Event Player.CalonTargetKamera;\n\t\t\t\t\t\t"Gunakan jeda satu frame yang sama saat mulai menonton dari orang pertama."\n\t\t\t\t\t\tWait(0.016, Ignore Condition);\n\t\t\t\t\t\tEvent Player.ModeKamera = 2;\n\t\t\t\t\t\tCall Subroutine(MulaiKamera);\n\t\t\t\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String(\n\t\t\t\t\t\t\t"Now spectating {0}. Definitely not stalking.", Event Player.TargetKamera) : Event Player.IndeksBahasa == 1 ? Custom String(\n\t\t\t\t\t\t\t"Sekarang menonton {0}. Sama sekali bukan menguntit.", Event Player.TargetKamera) : Custom String(\n\t\t\t\t\t\t\t"กำลังชม {0} อยู่ นี่ไม่ใช่การสะกดรอยแน่นอน", Event Player.TargetKamera));\n\t\t\t\t\tEnd;'''
rule = replace_once(rule, old, new, "camera target idempotence")

# Name color: compare before assignment/effects/message.
old = '''\t\tElse If(Event Player.HalamanMenu == 2);\n\t\t\tEvent Player.IndeksWarna = Event Player.KursorWarna;\n\t\t\tEvent Player.WarnaNama = Global.DaftarWarna[Event Player.IndeksWarna];\n\t\t\tIf(Event Player.IndeksWarna == 0);\n\t\t\t\tCall Subroutine(EfekPulihkan);\n\t\t\tElse;\n\t\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\tEnd;\n\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String(\n\t\t\t\t"Name color set to {0}. Subtlety is optional.", Global.NamaWarnaEN[Event Player.IndeksWarna]) : Event Player.IndeksBahasa == 1 ? Custom String(\n\t\t\t\t"Warna nama: {0}. Kalem itu opsional.", Global.NamaWarna[Event Player.IndeksWarna]) : Custom String(\n\t\t\t\t"ตั้งสีชื่อเป็น {0} แล้ว จะเด่นแค่ไหนก็ได้", Global.NamaWarnaTH[Event Player.IndeksWarna]));\n\t\t\tCall Subroutine(GambarMenu);'''
new = '''\t\tElse If(Event Player.HalamanMenu == 2);\n\t\t\tIf(Event Player.IndeksWarna != Event Player.KursorWarna);\n\t\t\t\tEvent Player.IndeksWarna = Event Player.KursorWarna;\n\t\t\t\tEvent Player.WarnaNama = Global.DaftarWarna[Event Player.IndeksWarna];\n\t\t\t\tIf(Event Player.IndeksWarna == 0);\n\t\t\t\t\tCall Subroutine(EfekPulihkan);\n\t\t\t\tElse;\n\t\t\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\t\tEnd;\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String(\n\t\t\t\t\t"Name color set to {0}. Subtlety is optional.", Global.NamaWarnaEN[Event Player.IndeksWarna]) : Event Player.IndeksBahasa == 1 ? Custom String(\n\t\t\t\t\t"Warna nama: {0}. Kalem itu opsional.", Global.NamaWarna[Event Player.IndeksWarna]) : Custom String(\n\t\t\t\t\t"ตั้งสีชื่อเป็น {0} แล้ว จะเด่นแค่ไหนก็ได้", Global.NamaWarnaTH[Event Player.IndeksWarna]));\n\t\t\tEnd;\n\t\t\tCall Subroutine(GambarMenu);'''
rule = replace_once(rule, old, new, "name color idempotence")

# Language: compare before switching language. The confirmation is shown in the new language.
old = '''\t\tElse If(Event Player.HalamanMenu == 3);\n\t\t\tEvent Player.IndeksBahasa = Event Player.KursorBahasa;\n\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String(\n\t\t\t\t"HUD language: English.") : Event Player.IndeksBahasa == 1 ? Custom String(\n\t\t\t\t"Bahasa HUD: Bahasa Indonesia.") : Custom String("ภาษา HUD: ไทย"));\n\t\t\tCall Subroutine(GambarMenu);'''
new = '''\t\tElse If(Event Player.HalamanMenu == 3);\n\t\t\tIf(Event Player.IndeksBahasa != Event Player.KursorBahasa);\n\t\t\t\tEvent Player.IndeksBahasa = Event Player.KursorBahasa;\n\t\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String(\n\t\t\t\t\t"HUD language: English.") : Event Player.IndeksBahasa == 1 ? Custom String(\n\t\t\t\t\t"Bahasa HUD: Bahasa Indonesia.") : Custom String("ภาษา HUD: ไทย"));\n\t\t\tEnd;\n\t\t\tCall Subroutine(GambarMenu);'''
rule = replace_once(rule, old, new, "language idempotence")

# Unkillable: compare desired state against actual state before applying/restoring.
old = '''\t\tElse If(Event Player.HalamanMenu == 5);\n\t\t\tEvent Player.UnkillableAktif = And(Event Player.KursorUnkillable == 1, Is In Spawn Room(Event Player) == False);\n\t\t\tIf(Event Player.UnkillableAktif == True);\n\t\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\t\tSet Status(Event Player, Null, Unkillable, 9999);\n\t\t\t\tIf(Is Alive(Event Player) == True);\n\t\t\t\t\tSet Player Health(Event Player, 1);\n\t\t\t\tEnd;\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Unkillable + 1 HP enabled.") : Event Player.IndeksBahasa == 1 ? Custom String(\n\t\t\t\t\t"Unkillable + 1 HP aktif.") : Custom String("เปิด Unkillable + 1 HP แล้ว"));\n\t\t\tElse;\n\t\t\t\tCall Subroutine(EfekPulihkan);\n\t\t\t\tClear Status(Event Player, Unkillable);\n\t\t\t\tIf(Is Alive(Event Player) == True);\n\t\t\t\t\tSet Player Health(Event Player, Max Health(Event Player));\n\t\t\t\tEnd;\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Unkillable + 1 HP disabled.") : Event Player.IndeksBahasa == 1 ? Custom String(\n\t\t\t\t\t"Unkillable + 1 HP nonaktif.") : Custom String("ปิด Unkillable + 1 HP แล้ว"));\n\t\t\tEnd;\n\t\t\tCall Subroutine(GambarMenu);'''
new = '''\t\tElse If(Event Player.HalamanMenu == 5);\n\t\t\tIf(Event Player.UnkillableAktif != And(Event Player.KursorUnkillable == 1, Is In Spawn Room(Event Player) == False));\n\t\t\t\tEvent Player.UnkillableAktif = And(Event Player.KursorUnkillable == 1, Is In Spawn Room(Event Player) == False);\n\t\t\t\tIf(Event Player.UnkillableAktif == True);\n\t\t\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\t\t\tSet Status(Event Player, Null, Unkillable, 9999);\n\t\t\t\t\tIf(Is Alive(Event Player) == True);\n\t\t\t\t\t\tSet Player Health(Event Player, 1);\n\t\t\t\t\tEnd;\n\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Unkillable + 1 HP enabled.") : Event Player.IndeksBahasa == 1 ? Custom String(\n\t\t\t\t\t\t"Unkillable + 1 HP aktif.") : Custom String("เปิด Unkillable + 1 HP แล้ว"));\n\t\t\t\tElse;\n\t\t\t\t\tCall Subroutine(EfekPulihkan);\n\t\t\t\t\tClear Status(Event Player, Unkillable);\n\t\t\t\t\tIf(Is Alive(Event Player) == True);\n\t\t\t\t\t\tSet Player Health(Event Player, Max Health(Event Player));\n\t\t\t\t\tEnd;\n\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Unkillable + 1 HP disabled.") : Event Player.IndeksBahasa == 1 ? Custom String(\n\t\t\t\t\t\t"Unkillable + 1 HP nonaktif.") : Custom String("ปิด Unkillable + 1 HP แล้ว"));\n\t\t\t\tEnd;\n\t\t\tEnd;\n\t\t\tCall Subroutine(GambarMenu);'''
rule = replace_once(rule, old, new, "unkillable idempotence")

# Voice modifier: do not reapply the same pitch or replay feedback.
old = '''\t\tElse If(Event Player.HalamanMenu == 6);\n\t\t\tEvent Player.IndeksSuara = Event Player.KursorSuara;\n\t\t\tIf(Event Player.IndeksSuara == 0);\n\t\t\t\tCall Subroutine(EfekPulihkan);\n\t\t\tElse;\n\t\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\tEnd;\n\t\t\tIf(Event Player.IndeksSuara == 0);\n\t\t\t\tStop Modifying Hero Voice Lines(Event Player);\n\t\t\tElse If(Event Player.IndeksSuara == 1);\n\t\t\t\tStart Modifying Hero Voice Lines(Event Player, 0.500, False);\n\t\t\tElse If(Event Player.IndeksSuara == 2);\n\t\t\t\tStart Modifying Hero Voice Lines(Event Player, 0.750, False);\n\t\t\tElse If(Event Player.IndeksSuara == 3);\n\t\t\t\tStart Modifying Hero Voice Lines(Event Player, 1.250, False);\n\t\t\tElse;\n\t\t\t\tStart Modifying Hero Voice Lines(Event Player, 1.500, False);\n\t\t\tEnd;\n\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Hero voice modifier applied.") : Event Player.IndeksBahasa == 1 ? Custom String(\n\t\t\t\t"Pengubah suara hero diterapkan.") : Custom String("ใช้ตัวปรับเสียงฮีโร่แล้ว"));\n\t\t\tCall Subroutine(GambarMenu);'''
new = '''\t\tElse If(Event Player.HalamanMenu == 6);\n\t\t\tIf(Event Player.IndeksSuara != Event Player.KursorSuara);\n\t\t\t\tEvent Player.IndeksSuara = Event Player.KursorSuara;\n\t\t\t\tIf(Event Player.IndeksSuara == 0);\n\t\t\t\t\tCall Subroutine(EfekPulihkan);\n\t\t\t\tElse;\n\t\t\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\t\tEnd;\n\t\t\t\tIf(Event Player.IndeksSuara == 0);\n\t\t\t\t\tStop Modifying Hero Voice Lines(Event Player);\n\t\t\t\tElse If(Event Player.IndeksSuara == 1);\n\t\t\t\t\tStart Modifying Hero Voice Lines(Event Player, 0.500, False);\n\t\t\t\tElse If(Event Player.IndeksSuara == 2);\n\t\t\t\t\tStart Modifying Hero Voice Lines(Event Player, 0.750, False);\n\t\t\t\tElse If(Event Player.IndeksSuara == 3);\n\t\t\t\t\tStart Modifying Hero Voice Lines(Event Player, 1.250, False);\n\t\t\t\tElse;\n\t\t\t\t\tStart Modifying Hero Voice Lines(Event Player, 1.500, False);\n\t\t\t\tEnd;\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Hero voice modifier applied.") : Event Player.IndeksBahasa == 1 ? Custom String(\n\t\t\t\t\t"Pengubah suara hero diterapkan.") : Custom String("ใช้ตัวปรับเสียงฮีโร่แล้ว"));\n\t\t\tEnd;\n\t\t\tCall Subroutine(GambarMenu);'''
rule = replace_once(rule, old, new, "voice idempotence")

# Player icon: same selection is a no-op, including NOTHING.
old = '''\t\tElse;\n\t\t\tEvent Player.IndeksIkon = Event Player.KursorIkon;\n\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Player icon applied: {0}.", Event Player.IndeksIkon == 0 ? Custom String("NOTHING") : Global.NamaIkon[Event Player.IndeksIkon])\n\t\t\t\t: Event Player.IndeksBahasa == 1 ? Custom String("Ikon pemain diterapkan: {0}.", Event Player.IndeksIkon == 0 ? Custom String("TIDAK ADA") : Global.NamaIkon[Event Player.IndeksIkon])\n\t\t\t\t: Custom String("ใช้ไอคอนผู้เล่นแล้ว: {0}", Event Player.IndeksIkon == 0 ? Custom String("ไม่มี") : Global.NamaIkon[Event Player.IndeksIkon]));\n\t\t\tCall Subroutine(GambarMenu);'''
new = '''\t\tElse;\n\t\t\tIf(Event Player.IndeksIkon != Event Player.KursorIkon);\n\t\t\t\tEvent Player.IndeksIkon = Event Player.KursorIkon;\n\t\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Player icon applied: {0}.", Event Player.IndeksIkon == 0 ? Custom String("NOTHING") : Global.NamaIkon[Event Player.IndeksIkon])\n\t\t\t\t\t: Event Player.IndeksBahasa == 1 ? Custom String("Ikon pemain diterapkan: {0}.", Event Player.IndeksIkon == 0 ? Custom String("TIDAK ADA") : Global.NamaIkon[Event Player.IndeksIkon])\n\t\t\t\t\t: Custom String("ใช้ไอคอนผู้เล่นแล้ว: {0}", Event Player.IndeksIkon == 0 ? Custom String("ไม่มี") : Global.NamaIkon[Event Player.IndeksIkon]));\n\t\t\tEnd;\n\t\t\tCall Subroutine(GambarMenu);'''
rule = replace_once(rule, old, new, "icon idempotence")

src = src[:start] + rule + src[end:]
SOURCE.write_text(src, encoding="utf-8")

# Lock the no-op behavior into static validation.
val = VALIDATOR.read_text(encoding="utf-8")
check = r'''

def check_idempotent_menu_feedback(checks: Checks, source: str, rules: list[Rule]) -> None:
    handlers = [
        rule for rule in rules
        if code_contains(rule.body, "Event Player.PerintahMenu == 1;", "Event Player.HalamanMenu = Global.KodeMenu")
    ]
    checks.equal(len(handlers), 1, "handler Interact idempotente")
    if not handlers:
        return
    body = mask_strings(handlers[0].body)
    for token in (
        "If(Event Player.IndeksGenre != Event Player.KursorGenre);",
        "If(Event Player.ModeKamera != 0);",
        "If(Or(Event Player.ModeKamera != 1, Event Player.TargetKamera != Event Player));",
        "If(Or(Event Player.ModeKamera != 2, Event Player.TargetKamera != Event Player.CalonTargetKamera));",
        "If(Event Player.IndeksWarna != Event Player.KursorWarna);",
        "If(Event Player.IndeksBahasa != Event Player.KursorBahasa);",
        "If(Event Player.UnkillableAktif != And(Event Player.KursorUnkillable == 1, Is In Spawn Room(Event Player) == False));",
        "If(Event Player.IndeksSuara != Event Player.KursorSuara);",
        "If(Event Player.IndeksIkon != Event Player.KursorIkon);",
    ):
        checks.require(token in body, f"feedback menu non protetto da cambio reale: {token}")

    # Each state assignment must occur after its corresponding inequality guard.
    ordered_pairs = (
        ("If(Event Player.IndeksGenre != Event Player.KursorGenre);", "Event Player.IndeksGenre = Event Player.KursorGenre;"),
        ("If(Event Player.IndeksWarna != Event Player.KursorWarna);", "Event Player.IndeksWarna = Event Player.KursorWarna;"),
        ("If(Event Player.IndeksBahasa != Event Player.KursorBahasa);", "Event Player.IndeksBahasa = Event Player.KursorBahasa;"),
        ("If(Event Player.IndeksSuara != Event Player.KursorSuara);", "Event Player.IndeksSuara = Event Player.KursorSuara;"),
        ("If(Event Player.IndeksIkon != Event Player.KursorIkon);", "Event Player.IndeksIkon = Event Player.KursorIkon;"),
    )
    for guard, assignment in ordered_pairs:
        checks.require(0 <= body.find(guard) < body.find(assignment), f"assegnazione menu fuori dalla guardia: {assignment}")
'''
if 'def check_idempotent_menu_feedback(' not in val:
    marker = '\ndef main() -> None:\n'
    if val.count(marker) != 1:
        raise SystemExit("validator main marker not found")
    val = val.replace(marker, check + marker, 1)
    call = '        check_player_icon_menu(checks, source, rules, subroutines)\n'
    if val.count(call) != 1:
        raise SystemExit("validator call anchor not found")
    val = val.replace(call, call + '        check_idempotent_menu_feedback(checks, source, rules)\n', 1)
VALIDATOR.write_text(val, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
section = '''\n\n### Feedback solo su cambi reali\n\nIl dispatcher `Interact` dei menu è idempotente: Soundtrack, Camera, Name Color, HUD Language, Unkillable, Voice Modifier e Player Icon confrontano prima la selezione con lo stato già applicato. Se coincidono, non vengono rieseguite azioni di modifica e non partono `Small Message`, `EfekTerapkan`/`EfekPulihkan` né i relativi suoni. Gli avvisi di errore o indisponibilità restano separati perché descrivono un'azione non eseguibile, non una conferma di modifica.\n'''
if '### Feedback solo su cambi reali' not in project:
    project += section
PROJECT.write_text(project, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
line = '- **Feedback idempotente live:** in Soundtrack, Camera, Name Color, HUD Language, Unkillable, Voice Modifier e Player Icon applicare una scelta, poi premere `Interact` più volte senza cambiare cursore; dopo la prima applicazione non devono comparire altri Small Message, effetti visivi o suoni. Cambiando voce, il feedback deve partire una sola volta.\n'
if line not in tests:
    tests += '\n' + line
TESTS.write_text(tests, encoding="utf-8")

# Refresh source blob marker.
data = SOURCE.read_bytes().replace(b"\r\n", b"\n")
blob = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
report = REPORT.read_text(encoding="utf-8")
report, n = re.subn(r"```text\n[0-9a-f]{40}\n```", f"```text\n{blob}\n```", report, count=1)
if n != 1:
    raise SystemExit("validation report blob marker not found")
REPORT.write_text(report, encoding="utf-8")
