from __future__ import annotations

from pathlib import Path
import hashlib
import re

SOURCE = Path("workshop/ruang_irama.workshop")
VALIDATOR = Path("tools/validate_workshop.py")
README = Path("README.md")
PROJECT = Path("docs/PROGETTO.md")
TESTS = Path("docs/TEST.md")
REPORT = Path("docs/VALIDAZIONE.md")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 occurrence, found {count}")
    return text.replace(old, new, 1)


def replace_in_rule(text: str, prefix: str, old: str, new: str, label: str) -> str:
    start = text.index(f'rule("{prefix}')
    end = text.find('\nrule("', start + 1)
    if end < 0:
        end = len(text)
    block = text[start:end]
    block = replace_once(block, old, new, label)
    return text[:start] + block + text[end:]


src = SOURCE.read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# Player state + subroutines.
# ---------------------------------------------------------------------------
src = replace_once(
    src,
    '\t\t63: WarnaMenu\n}',
    '\t\t63: WarnaMenu\n\t\t64: TeleportasiJongkokDiaktifkan\n\t\t65: KursorTeleportasiJongkok\n\t\t66: NamaInspeksiTerlihat\n\t\t67: KursorPrivasiNama\n}',
    "declare menu 8/9 player state",
)
src = replace_once(
    src,
    '\t20: GambarIkon\n\t21: TransisiWarnaMenu\n}',
    '\t20: GambarIkon\n\t21: TransisiWarnaMenu\n\t22: GambarSakelarTeleportasi\n\t23: GambarPrivasiNama\n}',
    "declare menu 8/9 renderers",
)
src = replace_once(
    src,
    'Global.KodeMenu = Array(0, 1, 2, 3, 4, 5, 6, 7);',
    'Global.KodeMenu = Array(0, 1, 2, 3, 4, 5, 6, 7, 8, 9);',
    "extend main menu codes",
)

src = replace_once(
    src,
    '\t\tEvent Player.WarnaMenu = Vector(55, 235, 245);',
    '\t\tEvent Player.WarnaMenu = Vector(55, 235, 245);\n\t\tEvent Player.TeleportasiJongkokDiaktifkan = False;\n\t\tEvent Player.KursorTeleportasiJongkok = 0;\n\t\tEvent Player.NamaInspeksiTerlihat = False;\n\t\tEvent Player.KursorPrivasiNama = 0;',
    "initialize menu 8/9 defaults off",
)

# ---------------------------------------------------------------------------
# Main menu navigation: 10 pages, with persistent cursors for both toggles.
# ---------------------------------------------------------------------------
src = replace_in_rule(
    src,
    "06 - Menu:",
    'Event Player.KursorUtama = (Event Player.KursorUtama + 1) % 8;',
    'Event Player.KursorUtama = (Event Player.KursorUtama + 1) % 10;',
    "main next modulo 10",
)
src = replace_in_rule(
    src,
    "06 - Menu:",
    '''\t\tElse If(Event Player.HalamanMenu == 7);
\t\t\tEvent Player.KursorIkon = (Event Player.KursorIkon + 1) % Count Of(Global.DaftarIkon);
\t\tEnd;''',
    '''\t\tElse If(Event Player.HalamanMenu == 7);
\t\t\tEvent Player.KursorIkon = (Event Player.KursorIkon + 1) % Count Of(Global.DaftarIkon);
\t\tElse If(Event Player.HalamanMenu == 8);
\t\t\tEvent Player.KursorTeleportasiJongkok = (Event Player.KursorTeleportasiJongkok + 1) % 2;
\t\tElse If(Event Player.HalamanMenu == 9);
\t\t\tEvent Player.KursorPrivasiNama = (Event Player.KursorPrivasiNama + 1) % 2;
\t\tEnd;''',
    "main next menu 8/9",
)
src = replace_in_rule(
    src,
    "07 - Menu:",
    'Event Player.KursorUtama = (Event Player.KursorUtama + 7) % 8;',
    'Event Player.KursorUtama = (Event Player.KursorUtama + 9) % 10;',
    "main previous modulo 10",
)
src = replace_in_rule(
    src,
    "07 - Menu:",
    '''\t\tElse If(Event Player.HalamanMenu == 7);
\t\t\tEvent Player.KursorIkon = (Event Player.KursorIkon + Count Of(Global.DaftarIkon) - 1) % Count Of(Global.DaftarIkon);
\t\tEnd;''',
    '''\t\tElse If(Event Player.HalamanMenu == 7);
\t\t\tEvent Player.KursorIkon = (Event Player.KursorIkon + Count Of(Global.DaftarIkon) - 1) % Count Of(Global.DaftarIkon);
\t\tElse If(Event Player.HalamanMenu == 8);
\t\t\tEvent Player.KursorTeleportasiJongkok = (Event Player.KursorTeleportasiJongkok + 1) % 2;
\t\tElse If(Event Player.HalamanMenu == 9);
\t\t\tEvent Player.KursorPrivasiNama = (Event Player.KursorPrivasiNama + 1) % 2;
\t\tEnd;''',
    "main previous menu 8/9",
)

# Enter menu 8/9 without resetting their persistent cursors.
src = replace_in_rule(
    src,
    "10 - Menu:",
    '''\t\t\tElse If(Event Player.HalamanMenu == 6);
\t\t\t\tEvent Player.KursorSuara = Event Player.KursorSuara;
\t\t\tElse;
\t\t\t\tEvent Player.KursorIkon = Event Player.KursorIkon;
\t\t\tEnd;''',
    '''\t\t\tElse If(Event Player.HalamanMenu == 6);
\t\t\t\tEvent Player.KursorSuara = Event Player.KursorSuara;
\t\t\tElse If(Event Player.HalamanMenu == 7);
\t\t\t\tEvent Player.KursorIkon = Event Player.KursorIkon;
\t\t\tElse If(Event Player.HalamanMenu == 8);
\t\t\t\tEvent Player.KursorTeleportasiJongkok = Event Player.KursorTeleportasiJongkok;
\t\t\tElse;
\t\t\t\tEvent Player.KursorPrivasiNama = Event Player.KursorPrivasiNama;
\t\t\tEnd;''',
    "enter menu 8/9",
)

# Split old icon fallback into explicit page 7 and add pages 8/9. Feedback is
# intentionally emitted only when the applied bool actually changes.
src = replace_in_rule(
    src,
    "10 - Menu:",
    '''\t\tElse;
\t\t\tIf(Event Player.IndeksIkon != Event Player.KursorIkon);
\t\t\t\tEvent Player.IndeksIkon = Event Player.KursorIkon;
\t\t\t\tCall Subroutine(EfekTerapkan);
\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Player icon: {0}.", Event Player.IndeksIkon == 0 ? Custom String("NOTHING") : Global.NamaIkon[Event Player.IndeksIkon])
\t\t\t\t\t: Event Player.IndeksBahasa == 1 ? Custom String("Ikon pemain: {0}.", Event Player.IndeksIkon == 0 ? Custom String("TIDAK ADA") : Global.NamaIkon[Event Player.IndeksIkon])
\t\t\t\t\t: Custom String("ไอคอนผู้เล่น: {0}", Event Player.IndeksIkon == 0 ? Custom String("ไม่มี") : Global.NamaIkon[Event Player.IndeksIkon]));
\t\t\tEnd;
\t\t\tCall Subroutine(GambarMenu);
\t\tEnd;''',
    '''\t\tElse If(Event Player.HalamanMenu == 7);
\t\t\tIf(Event Player.IndeksIkon != Event Player.KursorIkon);
\t\t\t\tEvent Player.IndeksIkon = Event Player.KursorIkon;
\t\t\t\tCall Subroutine(EfekTerapkan);
\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Player icon: {0}.", Event Player.IndeksIkon == 0 ? Custom String("NOTHING") : Global.NamaIkon[Event Player.IndeksIkon])
\t\t\t\t\t: Event Player.IndeksBahasa == 1 ? Custom String("Ikon pemain: {0}.", Event Player.IndeksIkon == 0 ? Custom String("TIDAK ADA") : Global.NamaIkon[Event Player.IndeksIkon])
\t\t\t\t\t: Custom String("ไอคอนผู้เล่น: {0}", Event Player.IndeksIkon == 0 ? Custom String("ไม่มี") : Global.NamaIkon[Event Player.IndeksIkon]));
\t\t\tEnd;
\t\t\tCall Subroutine(GambarMenu);
\t\tElse If(Event Player.HalamanMenu == 8);
\t\t\tIf(Event Player.TeleportasiJongkokDiaktifkan != (Event Player.KursorTeleportasiJongkok == 1));
\t\t\t\tEvent Player.TeleportasiJongkokDiaktifkan = Event Player.KursorTeleportasiJongkok == 1;
\t\t\t\tIf(Event Player.TeleportasiJongkokDiaktifkan == True);
\t\t\t\t\tCall Subroutine(EfekTerapkan);
\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Crouch Teleport enabled.") : Event Player.IndeksBahasa == 1 ? Custom String("Teleport Jongkok aktif.") : Custom String("เปิดเทเลพอร์ตตอนย่อแล้ว"));
\t\t\t\tElse;
\t\t\t\t\tCall Subroutine(EfekPulihkan);
\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Crouch Teleport disabled.") : Event Player.IndeksBahasa == 1 ? Custom String("Teleport Jongkok nonaktif.") : Custom String("ปิดเทเลพอร์ตตอนย่อแล้ว"));
\t\t\t\tEnd;
\t\t\tEnd;
\t\t\tCall Subroutine(GambarMenu);
\t\tElse;
\t\t\tIf(Event Player.NamaInspeksiTerlihat != (Event Player.KursorPrivasiNama == 1));
\t\t\t\tEvent Player.NamaInspeksiTerlihat = Event Player.KursorPrivasiNama == 1;
\t\t\t\tIf(Event Player.NamaInspeksiTerlihat == True);
\t\t\t\t\tCall Subroutine(EfekTerapkan);
\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Crouch name visible. Others can see you.") : Event Player.IndeksBahasa == 1 ? Custom String("Nama saat intip terlihat. Pemain lain bisa melihatmu.") : Custom String("แสดงชื่อเมื่อตรวจแล้ว คนอื่นเห็นชื่อคุณได้"));
\t\t\t\tElse;
\t\t\t\t\tCall Subroutine(EfekPulihkan);
\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Crouch name hidden. Incognito mode.") : Event Player.IndeksBahasa == 1 ? Custom String("Nama saat intip disembunyikan. Mode penyamaran.") : Custom String("ซ่อนชื่อเมื่อตรวจแล้ว โหมดไม่เปิดเผยตัว"));
\t\t\t\tEnd;
\t\t\tEnd;
\t\t\tCall Subroutine(GambarMenu);
\t\tEnd;''',
    "apply menu 8/9 toggles",
)

# ---------------------------------------------------------------------------
# Crouch Teleport is opt-in. Inspection remains independent and always works.
# ---------------------------------------------------------------------------
src = replace_in_rule(
    src,
    "19 - Teleportasi Jongkok:",
    '\t\tEvent Player.TeleportasiJongkokAktif == False;\n',
    '\t\tEvent Player.TeleportasiJongkokAktif == False;\n\t\tEvent Player.TeleportasiJongkokDiaktifkan == True;\n',
    "gate crouch teleport by menu 8",
)

# Name privacy only affects other viewers inspecting this human. Hero icon and
# health remain visible; bot names and the viewer's own third-person text remain.
rule13_start = src.index('rule("13 - Intip Pahlawan:')
rule13_end = src.find('\nrule("', rule13_start + 1)
rule13 = src[rule13_start:rule13_end]
rule13 = replace_once(
    rule13,
    'Custom String("{0} {1} | {2}",',
    'Custom String("{0}{1} | {2}",',
    "privacy compact inspection format",
)
rule13 = replace_once(
    rule13,
    'Custom String("{0}", Event Player.TargetInspeksi)',
    'Player Variable(Event Player.TargetInspeksi, Manusia) == True ? Player Variable(Event Player.TargetInspeksi, NamaInspeksiTerlihat) == True ? Custom String(" {0}", Event Player.TargetInspeksi) : Custom String("") : Custom String(" {0}", Event Player.TargetInspeksi)',
    "privacy target name component",
)
src = src[:rule13_start] + rule13 + src[rule13_end:]

# ---------------------------------------------------------------------------
# Menu router + main labels.
# ---------------------------------------------------------------------------
src = replace_in_rule(
    src,
    "91 - Subrutin:",
    '''\t\tElse If(Event Player.HalamanMenu == 6);
\t\t\tCall Subroutine(GambarSuara);
\t\tElse;
\t\t\tCall Subroutine(GambarIkon);
\t\tEnd;''',
    '''\t\tElse If(Event Player.HalamanMenu == 6);
\t\t\tCall Subroutine(GambarSuara);
\t\tElse If(Event Player.HalamanMenu == 7);
\t\t\tCall Subroutine(GambarIkon);
\t\tElse If(Event Player.HalamanMenu == 8);
\t\t\tCall Subroutine(GambarSakelarTeleportasi);
\t\tElse;
\t\t\tCall Subroutine(GambarPrivasiNama);
\t\tEnd;''',
    "route menu 8/9",
)

# Main menu: turn page 7 from fallback into an explicit branch and append 8/9.
main_start = src.index('rule("91a - Subrutin:')
main_end = src.find('\nrule("', main_start + 1)
main = src[main_start:main_end]
main = replace_once(
    main,
    ''': Event Player.IndeksIkon == 0 ? Custom String("7 - ICON\\nCURRENT: NOTHING") : Custom String("7 - ICON\\nCURRENT: {0} {1}", Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon])
\t\t\t: Event Player.IndeksBahasa == 1 ?''',
    ''': Event Player.KursorUtama == 7 ? Event Player.IndeksIkon == 0 ? Custom String("7 - ICON\\nCURRENT: NOTHING") : Custom String("7 - ICON\\nCURRENT: {0} {1}", Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon])
\t\t\t: Event Player.KursorUtama == 8 ? Custom String("8 - CROUCH TELEPORT\\nCURRENT: {0}", Event Player.TeleportasiJongkokDiaktifkan ? Custom String("ON") : Custom String("OFF"))
\t\t\t: Custom String("9 - NAME PRIVACY\\nCURRENT: {0}", Event Player.NamaInspeksiTerlihat ? Custom String("VISIBLE") : Custom String("HIDDEN"))
\t\t\t: Event Player.IndeksBahasa == 1 ?''',
    "main menu EN pages 8/9",
)
main = replace_once(
    main,
    ''': Event Player.IndeksIkon == 0 ? Custom String("7 - IKON\\nSAAT INI: TIDAK ADA") : Custom String("7 - IKON\\nSAAT INI: {0} {1}", Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon])
\t\t\t: Event Player.KursorUtama == 0 ?''',
    ''': Event Player.KursorUtama == 7 ? Event Player.IndeksIkon == 0 ? Custom String("7 - IKON\\nSAAT INI: TIDAK ADA") : Custom String("7 - IKON\\nSAAT INI: {0} {1}", Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon])
\t\t\t: Event Player.KursorUtama == 8 ? Custom String("8 - TELEPORT JONGKOK\\nSAAT INI: {0}", Event Player.TeleportasiJongkokDiaktifkan ? Custom String("AKTIF") : Custom String("MATI"))
\t\t\t: Custom String("9 - PRIVASI NAMA\\nSAAT INI: {0}", Event Player.NamaInspeksiTerlihat ? Custom String("TERLIHAT") : Custom String("TERSEMBUNYI"))
\t\t\t: Event Player.KursorUtama == 0 ?''',
    "main menu ID pages 8/9",
)
main = replace_once(
    main,
    ''': Event Player.IndeksIkon == 0 ? Custom String("7 - ไอคอน\\nปัจจุบัน: ไม่มี") : Custom String("7 - ไอคอน\\nปัจจุบัน: {0} {1}", Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon]), Top, 100,''',
    ''': Event Player.KursorUtama == 7 ? Event Player.IndeksIkon == 0 ? Custom String("7 - ไอคอน\\nปัจจุบัน: ไม่มี") : Custom String("7 - ไอคอน\\nปัจจุบัน: {0} {1}", Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon])
\t\t\t: Event Player.KursorUtama == 8 ? Custom String("8 - เทเลพอร์ตตอนย่อ\\nสถานะ: {0}", Event Player.TeleportasiJongkokDiaktifkan ? Custom String("เปิด") : Custom String("ปิด"))
\t\t\t: Custom String("9 - ความเป็นส่วนตัวชื่อ\\nสถานะ: {0}", Event Player.NamaInspeksiTerlihat ? Custom String("แสดง") : Custom String("ซ่อน")), Top, 100,''',
    "main menu TH pages 8/9",
)
src = src[:main_start] + main + src[main_end:]

# ---------------------------------------------------------------------------
# Two lightweight toggle renderers.
# ---------------------------------------------------------------------------
new_renderers = r'''rule("91l - Subrutin: Gambar sakelar teleportasi Jongkok")
{
	event
	{
		Subroutine;
		GambarSakelarTeleportasi;
	}

	actions
	{
		Create HUD Text(Event Player, Null, Event Player.IndeksBahasa == 0 ? Custom String("{0}\n{1}", Custom String("\n{0}: next | {1}: previous", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire))), Custom String("{0}: apply | {1}: back", Input Binding String(Button(Interact)), Input Binding String(Button(Reload))))
			: Event Player.IndeksBahasa == 1 ? Custom String("{0}\n{1}", Custom String("\n{0}: berikutnya | {1}: sebelumnya", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire))), Custom String("{0}: pakai | {1}: kembali", Input Binding String(Button(Interact)), Input Binding String(Button(Reload))))
			: Custom String("{0}\n{1}", Custom String("\n{0}: ถัดไป | {1}: ก่อนหน้า", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire))), Custom String("{0}: ใช้ | {1}: กลับ", Input Binding String(Button(Interact)), Input Binding String(Button(Reload)))),
			Event Player.IndeksBahasa == 0 ? Custom String("{0}\n> {1}", Custom String("8 - CROUCH TELEPORT {0}/2\nCURRENT: {1}", Event Player.KursorTeleportasiJongkok + 1, Event Player.TeleportasiJongkokDiaktifkan ? Custom String("ON") : Custom String("OFF")), Event Player.KursorTeleportasiJongkok == 1 ? Custom String("ON") : Custom String("OFF"))
			: Event Player.IndeksBahasa == 1 ? Custom String("{0}\n> {1}", Custom String("8 - TELEPORT JONGKOK {0}/2\nSAAT INI: {1}", Event Player.KursorTeleportasiJongkok + 1, Event Player.TeleportasiJongkokDiaktifkan ? Custom String("AKTIF") : Custom String("MATI")), Event Player.KursorTeleportasiJongkok == 1 ? Custom String("AKTIF") : Custom String("MATI"))
			: Custom String("{0}\n> {1}", Custom String("8 - เทเลพอร์ตตอนย่อ {0}/2\nสถานะ: {1}", Event Player.KursorTeleportasiJongkok + 1, Event Player.TeleportasiJongkokDiaktifkan ? Custom String("เปิด") : Custom String("ปิด")), Event Player.KursorTeleportasiJongkok == 1 ? Custom String("เปิด") : Custom String("ปิด")), Top, 100,
			Color(White), Custom Color(230, 255, 210, 255), Custom Color(X Component Of(Event Player.WarnaMenu), Y Component Of(Event Player.WarnaMenu), Z Component Of(Event Player.WarnaMenu), 255), Visible To String and Color, Visible Never);
		Event Player.HudMenu = Last Text ID;
	}
}

rule("91m - Subrutin: Gambar privasi nama saat diintip")
{
	event
	{
		Subroutine;
		GambarPrivasiNama;
	}

	actions
	{
		Create HUD Text(Event Player, Null, Event Player.IndeksBahasa == 0 ? Custom String("{0}\n{1}", Custom String("\n{0}: next | {1}: previous", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire))), Custom String("{0}: apply | {1}: back", Input Binding String(Button(Interact)), Input Binding String(Button(Reload))))
			: Event Player.IndeksBahasa == 1 ? Custom String("{0}\n{1}", Custom String("\n{0}: berikutnya | {1}: sebelumnya", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire))), Custom String("{0}: pakai | {1}: kembali", Input Binding String(Button(Interact)), Input Binding String(Button(Reload))))
			: Custom String("{0}\n{1}", Custom String("\n{0}: ถัดไป | {1}: ก่อนหน้า", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire))), Custom String("{0}: ใช้ | {1}: กลับ", Input Binding String(Button(Interact)), Input Binding String(Button(Reload)))),
			Event Player.IndeksBahasa == 0 ? Custom String("{0}\n> {1}", Custom String("9 - NAME PRIVACY {0}/2\nOTHERS SEE YOUR NAME: {1}", Event Player.KursorPrivasiNama + 1, Event Player.NamaInspeksiTerlihat ? Custom String("ON") : Custom String("OFF")), Event Player.KursorPrivasiNama == 1 ? Custom String("ON") : Custom String("OFF"))
			: Event Player.IndeksBahasa == 1 ? Custom String("{0}\n> {1}", Custom String("9 - PRIVASI NAMA {0}/2\nORANG LAIN LIHAT NAMA: {1}", Event Player.KursorPrivasiNama + 1, Event Player.NamaInspeksiTerlihat ? Custom String("AKTIF") : Custom String("MATI")), Event Player.KursorPrivasiNama == 1 ? Custom String("AKTIF") : Custom String("MATI"))
			: Custom String("{0}\n> {1}", Custom String("9 - ความเป็นส่วนตัวชื่อ {0}/2\nคนอื่นเห็นชื่อคุณ: {1}", Event Player.KursorPrivasiNama + 1, Event Player.NamaInspeksiTerlihat ? Custom String("เปิด") : Custom String("ปิด")), Event Player.KursorPrivasiNama == 1 ? Custom String("เปิด") : Custom String("ปิด")), Top, 100,
			Color(White), Custom Color(255, 220, 238, 255), Custom Color(X Component Of(Event Player.WarnaMenu), Y Component Of(Event Player.WarnaMenu), Z Component Of(Event Player.WarnaMenu), 255), Visible To String and Color, Visible Never);
		Event Player.HudMenu = Last Text ID;
	}
}

'''
insert_at = src.index('rule("91k - Subrutin:')
src = src[:insert_at] + new_renderers + src[insert_at:]

# Extend the smooth palette with two distinct colors.
src = replace_in_rule(
    src,
    "91k - Subrutin:",
    ''': (Event Player.HalamanMenu == -1 ? Event Player.KursorUtama : Event Player.HalamanMenu) == 6 ? Vector(115, 235, 170)
\t\t\t: Vector(235, 135, 255), 0.350, Destination and Duration);''',
    ''': (Event Player.HalamanMenu == -1 ? Event Player.KursorUtama : Event Player.HalamanMenu) == 6 ? Vector(115, 235, 170)
\t\t\t: (Event Player.HalamanMenu == -1 ? Event Player.KursorUtama : Event Player.HalamanMenu) == 7 ? Vector(235, 135, 255)
\t\t\t: (Event Player.HalamanMenu == -1 ? Event Player.KursorUtama : Event Player.HalamanMenu) == 8 ? Vector(190, 255, 80)
\t\t\t: Vector(255, 120, 190), 0.350, Destination and Duration);''',
    "extend menu color transition",
)

SOURCE.write_text(src, encoding="utf-8")

# ---------------------------------------------------------------------------
# Validator updates for 10 menus and the two new privacy/toggle contracts.
# ---------------------------------------------------------------------------
val = VALIDATOR.read_text(encoding="utf-8")
val = val.replace(
    'checks.equal(codes, ["0", "1", "2", "3", "4", "5", "6", "7"], "codici degli otto menu")',
    'checks.equal(codes, ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"], "codici dei dieci menu")',
)
val = val.replace(
    're.search(r"KursorUtama\\s*=\\s*\\([^;]+\\)\\s*%\\s*8\\s*;", clean) is not None,\n        "navigazione principale non limitata a otto menu",',
    're.search(r"KursorUtama\\s*=\\s*\\([^;]+\\)\\s*%\\s*10\\s*;", clean) is not None,\n        "navigazione principale non limitata a dieci menu",',
)
val = val.replace(
    '''        "GambarBalasDendam", "GambarKebal", "GambarSuara", "GambarIkon",
    }''',
    '''        "GambarBalasDendam", "GambarKebal", "GambarSuara", "GambarIkon",
        "GambarSakelarTeleportasi", "GambarPrivasiNama",
    }''',
    1,
)
# Cursor persistence checks.
val = val.replace(
    '            "Event Player.KursorSuara = Event Player.IndeksSuara;",\n',
    '            "Event Player.KursorSuara = Event Player.IndeksSuara;",\n            "Event Player.KursorTeleportasiJongkok = Event Player.TeleportasiJongkokDiaktifkan;",\n            "Event Player.KursorPrivasiNama = Event Player.NamaInspeksiTerlihat;",\n',
    2,
)

# Idempotent guards for menus 8/9.
val = val.replace(
    '        "If(Event Player.IndeksIkon != Event Player.KursorIkon);",\n',
    '        "If(Event Player.IndeksIkon != Event Player.KursorIkon);",\n        "If(Event Player.TeleportasiJongkokDiaktifkan != (Event Player.KursorTeleportasiJongkok == 1));",\n        "If(Event Player.NamaInspeksiTerlihat != (Event Player.KursorPrivasiNama == 1));",\n',
    1,
)
val = val.replace(
    '        ("If(Event Player.IndeksIkon != Event Player.KursorIkon);", "Event Player.IndeksIkon = Event Player.KursorIkon;"),\n',
    '        ("If(Event Player.IndeksIkon != Event Player.KursorIkon);", "Event Player.IndeksIkon = Event Player.KursorIkon;"),\n        ("If(Event Player.TeleportasiJongkokDiaktifkan != (Event Player.KursorTeleportasiJongkok == 1));", "Event Player.TeleportasiJongkokDiaktifkan = Event Player.KursorTeleportasiJongkok == 1;"),\n        ("If(Event Player.NamaInspeksiTerlihat != (Event Player.KursorPrivasiNama == 1));", "Event Player.NamaInspeksiTerlihat = Event Player.KursorPrivasiNama == 1;"),\n',
    1,
)

# Palette validator renderers and input colors.
val = val.replace(
    '    icon = renderer("GambarIkon")\n',
    '    icon = renderer("GambarIkon")\n    crouch_teleport = renderer("GambarSakelarTeleportasi")\n    name_privacy = renderer("GambarPrivasiNama")\n',
    1,
)
val = val.replace(
    '        (icon, "Custom Color(225, 215, 255, 255)", "player icon"),\n',
    '        (icon, "Custom Color(225, 215, 255, 255)", "player icon"),\n        (crouch_teleport, "Custom Color(230, 255, 210, 255)", "crouch teleport"),\n        (name_privacy, "Custom Color(255, 220, 238, 255)", "name privacy"),\n',
    1,
)
val = val.replace(
    '        (icon, "player icon"),\n',
    '        (icon, "player icon"),\n        (crouch_teleport, "crouch teleport"),\n        (name_privacy, "name privacy"),\n',
    1,
)
# Add the two new transition vectors after the icon token in both palette and smooth checks.
val = val.replace(
    '        "Vector(235, 135, 255)",\n    ):\n        checks.require(token in transition, f"palette transizione incompleta: {token}")',
    '        "Vector(235, 135, 255)",\n        "Vector(190, 255, 80)",\n        "Vector(255, 120, 190)",\n    ):\n        checks.require(token in transition, f"palette transizione incompleta: {token}")',
    1,
)
val = val.replace(
    '            "Vector(235, 135, 255)",\n        ):\n            checks.require(token in body, f"menu smooth: destinazione vector assente {token}")',
    '            "Vector(235, 135, 255)",\n            "Vector(190, 255, 80)",\n            "Vector(255, 120, 190)",\n        ):\n            checks.require(token in body, f"menu smooth: destinazione vector assente {token}")',
    1,
)
val = val.replace(
    '    for sub in ("GambarUtama", "GambarMusik", "GambarKamera", "GambarWarna", "GambarBahasa", "GambarBalasDendam", "GambarKebal", "GambarSuara", "GambarIkon"):',
    '    for sub in ("GambarUtama", "GambarMusik", "GambarKamera", "GambarWarna", "GambarBahasa", "GambarBalasDendam", "GambarKebal", "GambarSuara", "GambarIkon", "GambarSakelarTeleportasi", "GambarPrivasiNama"):',
    1,
)
val = val.replace(
    '    for sub in ("GambarUtama", "GambarMusik", "GambarKamera", "GambarWarna", "GambarBahasa", "GambarBalasDendam", "GambarKebal", "GambarSuara", "GambarIkon"):',
    '    for sub in ("GambarUtama", "GambarMusik", "GambarKamera", "GambarWarna", "GambarBahasa", "GambarBalasDendam", "GambarKebal", "GambarSuara", "GambarIkon", "GambarSakelarTeleportasi", "GambarPrivasiNama"):',
    1,
)

# Dedicated contract for menus 8/9.
new_check = r'''

def check_crouch_toggle_and_name_privacy(checks: Checks, source: str, rules: list[Rule], subroutines: set[str]) -> None:
    variables = section_body(source, "variables")
    for slot, name in (
        (64, "TeleportasiJongkokDiaktifkan"),
        (65, "KursorTeleportasiJongkok"),
        (66, "NamaInspeksiTerlihat"),
        (67, "KursorPrivasiNama"),
    ):
        checks.require(re.search(rf"(?m)^\s*{slot}\s*:\s*{name}\s*$", variables) is not None, f"menu 8/9: slot player {slot} deve essere {name}")

    for token in (
        "Event Player.TeleportasiJongkokDiaktifkan = False;",
        "Event Player.KursorTeleportasiJongkok = 0;",
        "Event Player.NamaInspeksiTerlihat = False;",
        "Event Player.KursorPrivasiNama = 0;",
    ):
        checks.require(token in mask_strings(source), f"menu 8/9: default OFF mancante {token}")

    open_rules = [rule for rule in rules if rule.name.startswith("19 - Teleportasi Jongkok:")]
    checks.equal(len(open_rules), 1, "menu 8: regola apertura Teleport Jongkok")
    if open_rules:
        checks.require("Event Player.TeleportasiJongkokDiaktifkan == True;" in mask_strings(open_rules[0].body), "menu 8: Crouch apre Teleport anche quando OFF")

    for sub in ("GambarSakelarTeleportasi", "GambarPrivasiNama"):
        checks.require(sub in subroutines, f"menu 8/9: subroutine {sub} assente")
        renderers = rules_containing(rules, "Subroutine;", f"{sub};")
        checks.equal(len(renderers), 1, f"menu 8/9: renderer {sub}")
        if renderers:
            checks.require("/2" in renderers[0].body, f"menu 8/9: {sub} non mostra 2 voci")

    checks.require("8 - CROUCH TELEPORT" in source and "8 - TELEPORT JONGKOK" in source and "8 - เทเลพอร์ตตอนย่อ" in source, "menu 8 non localizzato EN/ID/TH")
    checks.require("9 - NAME PRIVACY" in source and "9 - PRIVASI NAMA" in source and "9 - ความเป็นส่วนตัวชื่อ" in source, "menu 9 non localizzato EN/ID/TH")

    inspect = [rule for rule in rules if rule.name.startswith("13 - Intip Pahlawan:")]
    checks.equal(len(inspect), 1, "menu 9: regola testo inspection")
    if inspect:
        body = mask_strings(inspect[0].body)
        checks.require("Player Variable(Event Player.TargetInspeksi, NamaInspeksiTerlihat) == True" in body, "menu 9: nome target non dipende dalla privacy")
        checks.require('Custom String("")' in inspect[0].body, "menu 9: ramo nome nascosto assente")
        checks.require("Hero Icon String" in body and "Health(Event Player.TargetInspeksi)" in body, "menu 9: privacy non deve nascondere eroe o salute")

    handler = [rule for rule in rules if code_contains(rule.body, "Event Player.PerintahMenu == 1;", "Event Player.HalamanMenu = Global.KodeMenu")]
    checks.equal(len(handler), 1, "menu 8/9: handler Interact")
    if handler:
        body = mask_strings(handler[0].body)
        for token in (
            "Event Player.TeleportasiJongkokDiaktifkan = Event Player.KursorTeleportasiJongkok == 1;",
            "Event Player.NamaInspeksiTerlihat = Event Player.KursorPrivasiNama == 1;",
        ):
            checks.require(token in body, f"menu 8/9: applicazione mancante {token}")
'''
if 'def check_crouch_toggle_and_name_privacy(' not in val:
    marker = '\ndef main() -> None:\n'
    if marker not in val:
        raise SystemExit("validator main marker missing")
    val = val.replace(marker, new_check + marker, 1)
    anchor = '        check_idempotent_menu_feedback(checks, source, rules)\n'
    if anchor not in val:
        raise SystemExit("validator call anchor missing")
    val = val.replace(anchor, anchor + '        check_crouch_toggle_and_name_privacy(checks, source, rules, subroutines)\n', 1)

VALIDATOR.write_text(val, encoding="utf-8")

# ---------------------------------------------------------------------------
# Keep GitHub documentation aligned with the new 10-menu state.
# ---------------------------------------------------------------------------
readme = README.read_text(encoding="utf-8")
readme = readme.replace("**8 menu Arcade**", "**10 menu Arcade**")
readme = readme.replace(
    "  8. `7 - Player Icon` — **37 voci**: `Nothing` + 36 icone Workshop standard.\n",
    "  8. `7 - Player Icon` — **37 voci**: `Nothing` + 36 icone Workshop standard.\n  9. `8 - Crouch Teleport` — abilita/disabilita l’HUD Teleport su Crouch; default OFF.\n  10. `9 - Name Privacy` — decide se gli altri vedono il tuo nome durante Crouch inspection; default OFF.\n",
)
readme = readme.replace("## Menu Arcade attuale", "## Menu Arcade attuale")
readme = readme.replace(
    "| 7 | Player Icon | Nothing + 36 icone |\n",
    "| 7 | Player Icon | Nothing + 36 icone |\n| 8 | Crouch Teleport | OFF / ON, default OFF |\n| 9 | Name Privacy | OFF / ON, default OFF |\n",
)
readme = readme.replace("**Teleport non è un nono menu**: è un overlay associato a Crouch.", "Il Teleport resta un overlay associato a Crouch; **Menu 8** decide soltanto se quell’overlay può aprirsi.")
README.write_text(readme, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
project = project.replace("Il Main Menu contiene **8 voci**:", "Il Main Menu contiene **10 voci**:")
project = project.replace(
    "| 7 | Player Icon | Nothing + 36 icone |\n",
    "| 7 | Player Icon | Nothing + 36 icone |\n| 8 | Crouch Teleport | abilita overlay Crouch, default OFF |\n| 9 | Name Privacy | mostra/nasconde il proprio nome agli altri, default OFF |\n",
)
section = '''\n\n## Menu 8 e 9 — controlli Crouch personali\n\n`Menu 8 - Crouch Teleport` usa `TeleportasiJongkokDiaktifkan`: OFF di default. Solo quando è ON la pressione di Crouch può aprire `GambarTeleportasi`; l'ispezione eroe/salute resta indipendente. `TeleportasiJongkokAktif` continua a rappresentare soltanto l'overlay attualmente aperto.\n\n`Menu 9 - Name Privacy` usa `NamaInspeksiTerlihat`: OFF di default. Quando è OFF, gli altri viewer che ispezionano quel player con Crouch vedono ancora icona eroe e salute ma ricevono una stringa nome vuota; quando è ON vedono anche il nome. Il testo personale del viewer e i bot non vengono nascosti da questa impostazione.\n'''
if "## Menu 8 e 9 — controlli Crouch personali" not in project:
    project += section
PROJECT.write_text(project, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
for line in (
    '- **Menu 8 Crouch Teleport:** nuovo player = OFF; Crouch non deve aprire Teleport. Attivare dal menu 8, chiudere il menu e tenere Crouch: HUD Teleport visibile. Disattivare: torna a non aprirsi.\n',
    '- **Menu 9 Name Privacy:** nuovo player = OFF; un secondo player in Crouch inspection deve vedere eroe + salute ma non il nome. Attivare Menu 9: il nome deve comparire live; disattivare: deve sparire senza rimuovere eroe/salute.\n',
    '- **10 menu:** scorrere Main Menu avanti/indietro e verificare wrap `0..9`, cursori persistenti e sfumatura colore anche tra menu 7/8/9.\n',
):
    if line not in tests:
        tests += '\n' + line
TESTS.write_text(tests, encoding="utf-8")

# Refresh the exact source blob marker in VALIDAZIONE.
data = SOURCE.read_bytes().replace(b"\r\n", b"\n")
blob = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
report = REPORT.read_text(encoding="utf-8")
report, n = re.subn(r"```text\n[0-9a-f]{40}\n```", f"```text\n{blob}\n```", report, count=1)
if n != 1:
    raise SystemExit("validation report blob marker not found")
report = report.replace("**8 menu Arcade** (`0..7`)", "**10 menu Arcade** (`0..9`)")
report = report.replace("- **37 Player Icon** (`Nothing` + 36 icone Workshop), default Nothing;", "- **37 Player Icon** (`Nothing` + 36 icone Workshop), default Nothing;\n- Menu 8 Crouch Teleport, default OFF;\n- Menu 9 Name Privacy, default OFF; eroe/salute restano visibili anche col nome nascosto;")
REPORT.write_text(report, encoding="utf-8")
