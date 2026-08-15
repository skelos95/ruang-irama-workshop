from __future__ import annotations

from pathlib import Path
import hashlib
import re

source_path = Path('workshop/ruang_irama.workshop')
validator_path = Path('tools/validate_workshop.py')
readme_path = Path('README.md')
project_path = Path('docs/PROGETTO.md')
test_doc_path = Path('docs/TEST.md')
report_path = Path('docs/VALIDAZIONE.md')

src = source_path.read_text(encoding='utf-8')

ICONS = [
    'Arrow: Down', 'Arrow: Left', 'Arrow: Right', 'Arrow: Up', 'Asterisk', 'Bolt', 'Checkmark', 'Circle', 'Club',
    'Diamond', 'Dizzy', 'Exclamation Mark', 'Eye', 'Fire', 'Flag', 'Halo', 'Happy', 'Heart', 'Moon', 'No', 'Plus',
    'Poison', 'Poison 2', 'Question Mark', 'Radioactive', 'Recycle', 'Ring Thick', 'Ring Thin', 'Sad', 'Skull', 'Spade',
    'Spiral', 'Stop', 'Trashcan', 'Warning', 'X',
]
ICON_NAMES = [name.upper() for name in ICONS]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1, found {count}')
    return text.replace(old, new, 1)


def replace_rule(text: str, title_prefix: str, replacement: str) -> str:
    start = text.index(f'rule("{title_prefix}')
    next_rule = text.find('\nrule("', start + 1)
    if next_rule < 0:
        return text[:start] + replacement.rstrip() + '\n'
    return text[:start] + replacement.rstrip() + '\n\n' + text[next_rule + 1:]

# Declarations.
src = replace_once(
    src,
    '\t\t38: RGB\n\t\t39: RGBFase\n\tplayer:',
    '\t\t38: RGB\n\t\t39: RGBFase\n\t\t40: DaftarIkon\n\t\t41: NamaIkon\n\tplayer:',
    'global icon variables',
)
src = replace_once(
    src,
    '\t\t60: RespawnJumpDipakai\n}',
    '\t\t60: RespawnJumpDipakai\n\t\t61: IndeksIkon\n\t\t62: KursorIkon\n}',
    'player icon variables',
)
src = replace_once(
    src,
    '\t19: EfekPulihkan\n}',
    '\t19: EfekPulihkan\n\t20: GambarIkon\n}',
    'icon renderer subroutine',
)

# All 36 standard Workshop icon strings and their readable names.
icon_values = ',\n'.join(f'\t\t\tIcon String({name})' for name in ICONS)
icon_names = ',\n'.join(f'\t\t\tCustom String("{name}")' for name in ICON_NAMES)
icon_arrays = f'''\t\tGlobal.DaftarIkon = Array(\n{icon_values}\n\t\t);\n\t\tGlobal.NamaIkon = Array(\n{icon_names}\n\t\t);\n'''
src = replace_once(
    src,
    '\t\tGlobal.SlotHUDTersedia = Array(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11);',
    icon_arrays + '\t\tGlobal.SlotHUDTersedia = Array(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11);',
    'icon arrays insertion',
)

# Main menu now contains page 7.
src = replace_once(src, 'Global.KodeMenu = Array(0, 1, 2, 3, 4, 5, 6);', 'Global.KodeMenu = Array(0, 1, 2, 3, 4, 5, 6, 7);', 'main menu codes')

# Slower pastel/neon RGB: 51 seconds per loop, channels never drop below 80.
src = replace_once(src, 'Global.RGB = Custom Color(255, 0, 0, 255);', 'Global.RGB = Custom Color(255, 80, 80, 255);', 'RGB initial color')
rgb_rule = r'''rule("00r - Global: RGB pastel neon lento untuk judul, timer, ikon, dan efek")
{
	event
	{
		Ongoing - Global;
	}

	conditions
	{
		Global.Siap == True;
	}

	actions
	{
		Global.RGB = Custom Color(
			80 + (Global.RGBFase < 255 ? 255 : Global.RGBFase < 510 ? 510 - Global.RGBFase : Global.RGBFase < 1020 ? 0 : Global.RGBFase < 1275 ? Global.RGBFase - 1020 : 255) * 0.686,
			80 + (Global.RGBFase < 255 ? Global.RGBFase : Global.RGBFase < 765 ? 255 : Global.RGBFase < 1020 ? 1020 - Global.RGBFase : 0) * 0.686,
			80 + (Global.RGBFase < 510 ? 0 : Global.RGBFase < 765 ? Global.RGBFase - 510 : Global.RGBFase < 1275 ? 255 : 1530 - Global.RGBFase) * 0.686,
			255);
		Wait(0.100, Ignore Condition);
		Global.RGBFase = (Global.RGBFase + 3) % 1530;
		Loop If Condition Is True;
	}
}'''
src = replace_rule(src, '00r - Global:', rgb_rule)

# Main menu opening copy: seven -> eight choices.
src = src.replace('Seven extremely important decisions await.', 'Eight extremely important decisions await.')
src = src.replace('Tujuh keputusan yang sangat penting menunggu.', 'Delapan keputusan yang sangat penting menunggu.')
src = src.replace('มีเจ็ดตัวเลือกสำคัญรอคุณอยู่', 'มีแปดตัวเลือกสำคัญรอคุณอยู่')

# Compact player rows: selected icon -> hero icon -> player -> time/genre.
rule02_start = src.index('rule("02 - Pemain:')
rule02_end = src.index('\nrule("02c -', rule02_start)
rule02 = src[rule02_start:rule02_end]
row_start = rule02.index('\t\tCreate HUD Text(Global.PemainManusia, Null, Player Variable(Local Player, IndeksBahasa)')
row_end_marker = '\t\tGlobal.HudKananPemain = Append To Array(Global.HudKananPemain, Event Player.HudKanan);'
row_end = rule02.index(row_end_marker, row_start) + len(row_end_marker)
new_rows = r'''		Create HUD Text(Global.PemainManusia, Null, Custom String("{0} {1} {2} - {3} MIN",
			Global.DaftarIkon[Event Player.IndeksIkon], Hero Icon String(Is Duplicating(Event Player) ? Hero Being Duplicated(Event Player) : Hero Of(Event Player)),
			Event Player, Event Player.MenitLobby), And(Global.DiagnostikPerforma == True, And(Local Player == Host Player, Event Player == Last Of(Sorted Array(
			Global.PemainManusia, Player Variable(Current Array Element, UrutanHUD))))) ? Custom String("{0}\n{1}", Custom String("\n \nLOAD {0}% | AVG {1}% | MAX {2}%",
			Server Load, Server Load Average, Server Load Peak), Custom String("HUD {0} | IWT {1}", 3 + Count Of(Global.HudKiriPemain) * 2 + Count Of(Filtered Array(
			Global.HudMenuPemain, Current Array Element != 0)), Count Of(Filtered Array(Global.TeksDuniaPemain, Current Array Element != 0)) + Count Of(Filtered Array(
			Global.TeksDiriPemain, Current Array Element != 0)))) : Custom String(" "), Left, -99 + Event Player.UrutanHUD, Color(White), Global.RGB, Color(White),
			Visible To String and Color, Visible Never);
		Event Player.HudKiri = Last Text ID;
		Global.HudKiriPemain = Append To Array(Global.HudKiriPemain, Event Player.HudKiri);
		Create HUD Text(Global.PemainManusia, Null, Custom String("{0}{1}", Custom String("{0} {1} {2} - {3}", Global.DaftarIkon[Event Player.IndeksIkon],
			Hero Icon String(Is Duplicating(Event Player) ? Hero Being Duplicated(Event Player) : Hero Of(Event Player)), Event Player,
			Event Player.IndeksGenre >= 0 ? Global.DaftarGenre[Event Player.IndeksGenre] : Player Variable(Local Player, IndeksBahasa) == 0 ? Custom String("no soundtrack yet")
			: Player Variable(Local Player, IndeksBahasa) == 1 ? Custom String("belum pilih soundtrack") : Custom String("ยังไม่ได้เลือกเพลง")), Event Player == Last Of(Sorted Array(
			Global.PemainManusia, Player Variable(Current Array Element, UrutanHUD))) ? Custom String("\n ") : Custom String("")), Null, Right, -99 + Event Player.UrutanHUD,
			Color(White), Global.RGB, Color(White), Visible To String and Color, Visible Never);
		Event Player.HudKanan = Last Text ID;
		Global.HudKananPemain = Append To Array(Global.HudKananPemain, Event Player.HudKanan);'''
rule02 = rule02[:row_start] + new_rows + rule02[row_end:]
src = src[:rule02_start] + rule02 + src[rule02_end:]

# Main selection navigation now wraps 8 pages; page 7 cycles through all icons.
src = replace_once(src, 'Event Player.KursorUtama = (Event Player.KursorUtama + 1) % 7;', 'Event Player.KursorUtama = (Event Player.KursorUtama + 1) % 8;', 'main menu next')
src = replace_once(src, 'Event Player.KursorUtama = (Event Player.KursorUtama + 6) % 7;', 'Event Player.KursorUtama = (Event Player.KursorUtama + 7) % 8;', 'main menu previous')
src = replace_once(
    src,
    '\t\tElse If(Event Player.HalamanMenu == 6);\n\t\t\tEvent Player.KursorSuara = (Event Player.KursorSuara + 1) % 5;\n\t\tEnd;',
    '\t\tElse If(Event Player.HalamanMenu == 6);\n\t\t\tEvent Player.KursorSuara = (Event Player.KursorSuara + 1) % 5;\n\t\tElse If(Event Player.HalamanMenu == 7);\n\t\t\tEvent Player.KursorIkon = (Event Player.KursorIkon + 1) % Count Of(Global.DaftarIkon);\n\t\tEnd;',
    'icon next navigation',
)
src = replace_once(
    src,
    '\t\tElse If(Event Player.HalamanMenu == 6);\n\t\t\tEvent Player.KursorSuara = (Event Player.KursorSuara + 4) % 5;\n\t\tEnd;',
    '\t\tElse If(Event Player.HalamanMenu == 6);\n\t\t\tEvent Player.KursorSuara = (Event Player.KursorSuara + 4) % 5;\n\t\tElse If(Event Player.HalamanMenu == 7);\n\t\t\tEvent Player.KursorIkon = (Event Player.KursorIkon + Count Of(Global.DaftarIkon) - 1) % Count Of(Global.DaftarIkon);\n\t\tEnd;',
    'icon previous navigation',
)

# Interact handler: preserve cursor on open, apply icon on page 7.
r10_start = src.index('rule("10 - Menu:')
r10_end = src.index('\nrule("11 - Menu:', r10_start)
r10 = src[r10_start:r10_end]
r10 = replace_once(
    r10,
    '\t\t\tElse;\n\t\t\t\tEvent Player.KursorSuara = Event Player.KursorSuara;\n\t\t\tEnd;',
    '\t\t\tElse If(Event Player.HalamanMenu == 6);\n\t\t\t\tEvent Player.KursorSuara = Event Player.KursorSuara;\n\t\t\tElse;\n\t\t\t\tEvent Player.KursorIkon = Event Player.KursorIkon;\n\t\t\tEnd;',
    'icon cursor persistence',
)
r10 = replace_once(
    r10,
    '\t\tElse;\n\t\t\tEvent Player.IndeksSuara = Event Player.KursorSuara;',
    '\t\tElse If(Event Player.HalamanMenu == 6);\n\t\t\tEvent Player.IndeksSuara = Event Player.KursorSuara;',
    'voice branch explicit page 6',
)
final_end = r10.rfind('\t\tEnd;\n\t}\n}')
if final_end < 0:
    raise SystemExit('Interact handler final End not found')
icon_apply = r'''		Else;
			Event Player.IndeksIkon = Event Player.KursorIkon;
			Call Subroutine(EfekTerapkan);
			Small Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Player icon applied: {0}.", Global.NamaIkon[Event Player.IndeksIkon])
				: Event Player.IndeksBahasa == 1 ? Custom String("Ikon pemain diterapkan: {0}.", Global.NamaIkon[Event Player.IndeksIkon])
				: Custom String("ใช้ไอคอนผู้เล่นแล้ว: {0}", Global.NamaIkon[Event Player.IndeksIkon]));
			Call Subroutine(GambarMenu);
'''
r10 = r10[:final_end] + icon_apply + r10[final_end:]
src = src[:r10_start] + r10 + src[r10_end:]

# Menu router page 7.
r91_start = src.index('rule("91 - Subrutin:')
r91_end = src.index('\nrule("91a -', r91_start)
r91 = src[r91_start:r91_end]
r91 = replace_once(
    r91,
    '\t\tElse If(Event Player.HalamanMenu == 5);\n\t\t\tCall Subroutine(GambarUnkillable);\n\t\tElse;\n\t\t\tCall Subroutine(GambarSuara);\n\t\tEnd;',
    '\t\tElse If(Event Player.HalamanMenu == 5);\n\t\t\tCall Subroutine(GambarUnkillable);\n\t\tElse If(Event Player.HalamanMenu == 6);\n\t\t\tCall Subroutine(GambarSuara);\n\t\tElse;\n\t\t\tCall Subroutine(GambarIkon);\n\t\tEnd;',
    'menu icon router',
)
src = src[:r91_start] + r91 + src[r91_end:]

# Replace main menu renderer with an 8-page version.
main_renderer = r'''rule("91a - Subrutin: Gambar menu utama")
{
	event
	{
		Subroutine;
		GambarUtama;
	}

	actions
	{
		Create HUD Text(Event Player, Null, Event Player.IndeksBahasa == 0 ? Custom String("{0}\n{1}", Custom String("\n{0}: next | {1}: previous",
			Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire))), Custom String("{0}: open | hold {1} 0.5 sec: close",
			Input Binding String(Button(Interact)), Input Binding String(Button(Melee)))) : Event Player.IndeksBahasa == 1 ? Custom String("{0}\n{1}",
			Custom String("\n{0}: berikutnya | {1}: sebelumnya", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire))), Custom String(
			"{0}: buka | tahan {1} 0,5 dtk: tutup", Input Binding String(Button(Interact)), Input Binding String(Button(Melee)))) : Custom String("{0}\n{1}",
			Custom String("\n{0}: ถัดไป | {1}: ก่อนหน้า", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire))), Custom String(
			"{0}: เปิด | กด {1} ค้างเพื่อปิด", Input Binding String(Button(Interact)), Input Binding String(Button(Melee)))),
			Event Player.IndeksBahasa == 0 ? Event Player.KursorUtama == 0 ? Custom String("0 - SOUNDTRACK\nCURRENT: {0}", Event Player.IndeksGenre >= 0 ? Global.DaftarGenre[Event Player.IndeksGenre] : Custom String("no soundtrack yet"))
			: Event Player.KursorUtama == 1 ? Custom String("1 - THIRD-PERSON CAMERA\nCURRENT: {0}", Event Player.ModeKamera == 0 ? Custom String("off") : Event Player.ModeKamera == 1 ? Custom String("your hero") : Custom String("watching {0}", Event Player.TargetKamera))
			: Event Player.KursorUtama == 2 ? Custom String("2 - NAME COLOR\nCURRENT: {0}", Global.NamaWarnaEN[Event Player.IndeksWarna])
			: Event Player.KursorUtama == 3 ? Custom String("3 - HUD LANGUAGE\nCURRENT: {0}", Global.NamaBahasa[Event Player.IndeksBahasa])
			: Event Player.KursorUtama == 4 ? Custom String("4 - REVENGE\nDIRECT KILLS OWED TO YOU")
			: Event Player.KursorUtama == 5 ? Custom String("5 - UNKILLABLE + 1 HP\nCURRENT: {0}", Event Player.UnkillableAktif ? Custom String("ON") : Custom String("OFF"))
			: Event Player.KursorUtama == 6 ? Custom String("6 - VOICE MODIFIER\nCURRENT: {0}", Event Player.IndeksSuara == 0 ? Custom String("NORMAL") : Event Player.IndeksSuara == 1 ? Custom String("LOW 0.50x") : Event Player.IndeksSuara == 2 ? Custom String("LOW 0.75x") : Event Player.IndeksSuara == 3 ? Custom String("HIGH 1.25x") : Custom String("HIGH 1.50x"))
			: Custom String("7 - PLAYER ICON\nCURRENT: {0} {1}", Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon])
			: Event Player.IndeksBahasa == 1 ? Event Player.KursorUtama == 0 ? Custom String("0 - SOUNDTRACK\nSAAT INI: {0}", Event Player.IndeksGenre >= 0 ? Global.DaftarGenre[Event Player.IndeksGenre] : Custom String("belum pilih soundtrack"))
			: Event Player.KursorUtama == 1 ? Custom String("1 - KAMERA ORANG KETIGA\nSAAT INI: {0}", Event Player.ModeKamera == 0 ? Custom String("mati") : Event Player.ModeKamera == 1 ? Custom String("hero sendiri") : Custom String("menonton {0}", Event Player.TargetKamera))
			: Event Player.KursorUtama == 2 ? Custom String("2 - WARNA NAMA\nSAAT INI: {0}", Global.NamaWarna[Event Player.IndeksWarna])
			: Event Player.KursorUtama == 3 ? Custom String("3 - BAHASA HUD\nSAAT INI: {0}", Global.NamaBahasa[Event Player.IndeksBahasa])
			: Event Player.KursorUtama == 4 ? Custom String("4 - BALAS DENDAM\nUTANG KILL LANGSUNG")
			: Event Player.KursorUtama == 5 ? Custom String("5 - UNKILLABLE + 1 HP\nSAAT INI: {0}", Event Player.UnkillableAktif ? Custom String("AKTIF") : Custom String("MATI"))
			: Event Player.KursorUtama == 6 ? Custom String("6 - PENGUBAH SUARA\nSAAT INI: {0}", Event Player.IndeksSuara == 0 ? Custom String("NORMAL") : Event Player.IndeksSuara == 1 ? Custom String("RENDAH 0.50x") : Event Player.IndeksSuara == 2 ? Custom String("RENDAH 0.75x") : Event Player.IndeksSuara == 3 ? Custom String("TINGGI 1.25x") : Custom String("TINGGI 1.50x"))
			: Custom String("7 - IKON PEMAIN\nSAAT INI: {0} {1}", Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon])
			: Event Player.KursorUtama == 0 ? Custom String("0 - เพลงประกอบ\nปัจจุบัน: {0}", Event Player.IndeksGenre >= 0 ? Global.DaftarGenre[Event Player.IndeksGenre] : Custom String("ยังไม่ได้เลือกเพลง"))
			: Event Player.KursorUtama == 1 ? Custom String("1 - กล้องบุคคลที่สาม\nสถานะ: {0}", Event Player.ModeKamera == 0 ? Custom String("ปิด") : Event Player.ModeKamera == 1 ? Custom String("ฮีโร่ของคุณ") : Custom String("กำลังดู {0}", Event Player.TargetKamera))
			: Event Player.KursorUtama == 2 ? Custom String("2 - สีชื่อ\nปัจจุบัน: {0}", Global.NamaWarnaTH[Event Player.IndeksWarna])
			: Event Player.KursorUtama == 3 ? Custom String("3 - ภาษา HUD\nปัจจุบัน: {0}", Global.NamaBahasa[Event Player.IndeksBahasa])
			: Event Player.KursorUtama == 4 ? Custom String("4 - ล้างแค้น\nศัตรูที่ติดหนี้คุณ")
			: Event Player.KursorUtama == 5 ? Custom String("5 - UNKILLABLE + 1 HP\nสถานะ: {0}", Event Player.UnkillableAktif ? Custom String("เปิด") : Custom String("ปิด"))
			: Event Player.KursorUtama == 6 ? Custom String("6 - ปรับเสียงฮีโร่\nสถานะ: {0}", Event Player.IndeksSuara == 0 ? Custom String("ปกติ") : Event Player.IndeksSuara == 1 ? Custom String("ต่ำ 0.50x") : Event Player.IndeksSuara == 2 ? Custom String("ต่ำ 0.75x") : Event Player.IndeksSuara == 3 ? Custom String("สูง 1.25x") : Custom String("สูง 1.50x"))
			: Custom String("7 - ไอคอนผู้เล่น\nปัจจุบัน: {0} {1}", Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon]), Top, 100,
			Color(White), Custom Color(210, 230, 255, 255), Custom Color(255, 185, 65, 255), Visible To and String, Visible Never);
		Event Player.HudMenu = Last Text ID;
	}
}'''
src = replace_rule(src, '91a - Subrutin:', main_renderer)

# Dedicated page 7 renderer with RGB icon preview.
icon_renderer = r'''rule("91j - Subrutin: Gambar menu ikon pemain")
{
	event
	{
		Subroutine;
		GambarIkon;
	}

	actions
	{
		Create HUD Text(Event Player, Null, Event Player.IndeksBahasa == 0 ? Custom String("{0}\n{1}", Custom String("\n{0}: next | {1}: previous",
			Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire))), Custom String("{0}: apply | {1}: back", Input Binding String(Button(Interact)), Input Binding String(Button(Reload))))
			: Event Player.IndeksBahasa == 1 ? Custom String("{0}\n{1}", Custom String("\n{0}: berikutnya | {1}: sebelumnya", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire))), Custom String("{0}: pakai | {1}: kembali", Input Binding String(Button(Interact)), Input Binding String(Button(Reload))))
			: Custom String("{0}\n{1}", Custom String("\n{0}: ถัดไป | {1}: ก่อนหน้า", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire))), Custom String("{0}: ใช้ | {1}: กลับ", Input Binding String(Button(Interact)), Input Binding String(Button(Reload)))),
			Event Player.IndeksBahasa == 0 ? Custom String("{0}\n> {1} {2}", Custom String("7 - PLAYER ICON {0}/36\nCURRENT: {1} {2}", Event Player.KursorIkon + 1, Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon]), Global.DaftarIkon[Event Player.KursorIkon], Global.NamaIkon[Event Player.KursorIkon])
			: Event Player.IndeksBahasa == 1 ? Custom String("{0}\n> {1} {2}", Custom String("7 - IKON PEMAIN {0}/36\nSAAT INI: {1} {2}", Event Player.KursorIkon + 1, Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon]), Global.DaftarIkon[Event Player.KursorIkon], Global.NamaIkon[Event Player.KursorIkon])
			: Custom String("{0}\n> {1} {2}", Custom String("7 - ไอคอนผู้เล่น {0}/36\nปัจจุบัน: {1} {2}", Event Player.KursorIkon + 1, Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon]), Global.DaftarIkon[Event Player.KursorIkon], Global.NamaIkon[Event Player.KursorIkon]),
			Top, 100, Color(White), Global.RGB, Global.RGB, Visible To String and Color, Visible Never);
		Event Player.HudMenu = Last Text ID;
	}
}'''
insert_92 = src.index('rule("92 - Subrutin:')
src = src[:insert_92] + icon_renderer + '\n\n' + src[insert_92:]

# Initialize Heart as the friendly default and keep both cursors persistent thereafter.
src = replace_once(
    src,
    '\t\tEvent Player.RespawnJumpDipakai = False;\n\t}\n}\n\nrule("95 -',
    '\t\tEvent Player.RespawnJumpDipakai = False;\n\t\tEvent Player.IndeksIkon = 17;\n\t\tEvent Player.KursorIkon = 17;\n\t}\n}\n\nrule("95 -',
    'icon player initialization',
)

source_path.write_text(src, encoding='utf-8')

# ---------- validator ----------
val = validator_path.read_text(encoding='utf-8')
val = val.replace('["0", "1", "2", "3", "4", "5", "6"], "codici dei sette menu"', '["0", "1", "2", "3", "4", "5", "6", "7"], "codici degli otto menu"')
val = val.replace(r'KursorUtama\s*=\s*\([^;]+\)\s*%\s*7\s*;', r'KursorUtama\s*=\s*\([^;]+\)\s*%\s*8\s*;')
val = val.replace('navigazione principale non limitata a sette menu', 'navigazione principale non limitata a otto menu')
val = val.replace('"GambarBalasDendam", "GambarUnkillable", "GambarSuara",', '"GambarBalasDendam", "GambarUnkillable", "GambarSuara", "GambarIkon",')
val = val.replace('"Global.RGB = Custom Color(255, 0, 0, 255);"', '"Global.RGB = Custom Color(255, 80, 80, 255);"')
val = val.replace('"Global.RGBFase = (Global.RGBFase + 12) % 1530;"', '"Global.RGBFase = (Global.RGBFase + 3) % 1530;"')
val = val.replace('"RGB: colore iniziale assente"', '"RGB: colore iniziale pastel-neon assente"')

icon_check = '''\n\ndef check_player_icon_menu(checks: Checks, source: str, rules: list[Rule], subroutines: set[str]) -> None:\n    expected_icons = [\n'''
for icon in ICONS:
    icon_check += f'        "Icon String({icon})",\n'
icon_check += '''    ]\n    expected_names = [\n'''
for name in ICON_NAMES:
    icon_check += f'        "{name}",\n'
icon_check += '''    ]\n    actual_icons = [re.sub(r"\\s+", " ", item).strip() for item in top_level_items(array_body(source, "Global.DaftarIkon"))]\n    checks.equal(actual_icons, expected_icons, "36 icone Workshop del menu 7")\n    checks.equal(custom_strings(array_body(source, "Global.NamaIkon")), expected_names, "nomi delle 36 icone")\n\n    variables = section_body(source, "variables")\n    for slot, name in ((40, "DaftarIkon"), (41, "NamaIkon")):\n        checks.require(re.search(rf"(?m)^\\s*{slot}\\s*:\\s*{name}\\s*$", variables) is not None, f"icone: slot global {slot} deve essere {name}")\n    for slot, name in ((61, "IndeksIkon"), (62, "KursorIkon")):\n        checks.require(re.search(rf"(?m)^\\s*{slot}\\s*:\\s*{name}\\s*$", variables) is not None, f"icone: slot player {slot} deve essere {name}")\n    checks.require("GambarIkon" in subroutines, "icone: subroutine GambarIkon assente")\n    checks.require("Event Player.IndeksIkon = 17;" in source and "Event Player.KursorIkon = 17;" in source, "icone: default Heart non inizializzato")\n\n    classification = [rule for rule in rules if rule.name.startswith("02 - Pemain:")]\n    checks.equal(len(classification), 1, "regola roster per icona player")\n    if classification:\n        body = classification[0].body\n        checks.require(body.count("Global.DaftarIkon[Event Player.IndeksIkon]") >= 2, "icona player non presente in entrambe le liste")\n        for segment in re.findall(r'Custom String\\(\\"\\{0\\} \\{1\\} \\{2\\}[^;]+', body):\n            icon_at = segment.find("Global.DaftarIkon[Event Player.IndeksIkon]")\n            hero_at = segment.find("Hero Icon String")\n            checks.require(0 <= icon_at < hero_at, "icona player deve precedere l'icona eroe")\n        checks.require("CHILL for" not in body and " - CHILL " not in body, "roster sinistro contiene ancora CHILL for")\n        checks.require(" - soundtrack:" not in body and " - เพลงประกอบ:" not in body, "roster destro contiene ancora il prefisso soundtrack")\n        checks.require(body.count("Global.RGB") >= 2, "le due liste non usano il colore RGB per le icone")\n\n    next_rules = [rule for rule in rules if code_contains(rule.body, "Event Player.PerintahMenu == 3;", "Event Player.KursorIkon = (Event Player.KursorIkon + 1) % Count Of(Global.DaftarIkon);")]\n    prev_rules = [rule for rule in rules if code_contains(rule.body, "Event Player.PerintahMenu == 4;", "Event Player.KursorIkon = (Event Player.KursorIkon + Count Of(Global.DaftarIkon) - 1) % Count Of(Global.DaftarIkon);")]\n    checks.equal(len(next_rules), 1, "menu 7: navigazione icona successiva")\n    checks.equal(len(prev_rules), 1, "menu 7: navigazione icona precedente")\n\n    interact = [rule for rule in rules if code_contains(rule.body, "Event Player.PerintahMenu == 1;", "Event Player.IndeksIkon = Event Player.KursorIkon;", "Call Subroutine(EfekTerapkan);")]\n    checks.equal(len(interact), 1, "menu 7: applicazione icona")\n    renderers = rules_containing(rules, "Subroutine;", "GambarIkon;")\n    checks.equal(len(renderers), 1, "renderer menu 7")\n    if renderers:\n        checks.require("/36" in renderers[0].body and "Global.RGB" in renderers[0].body, "menu 7 non mostra 36 icone con colore RGB")\n\n'''
main_marker = '\ndef main() -> None:\n'
if 'def check_player_icon_menu(' not in val:
    if val.count(main_marker) != 1:
        raise SystemExit('validator main marker not found')
    val = val.replace(main_marker, icon_check + main_marker, 1)
    call_anchor = '        check_rgb_system(checks, source, rules)\n'
    if val.count(call_anchor) != 1:
        raise SystemExit('validator icon call anchor not found')
    val = val.replace(call_anchor, call_anchor + '        check_player_icon_menu(checks, source, rules, subroutines)\n', 1)

# Strengthen the pastel/neon RGB contract.
rgb_anchor = '    checks.require("Global.RGBFase = 0;" in clean, "RGB: fase iniziale assente")\n'
if rgb_anchor in val and 'RGB: floor pastel/neon' not in val:
    val = val.replace(rgb_anchor, rgb_anchor + '    checks.require("80 + (Global.RGBFase" in clean and "* 0.686" in clean, "RGB: floor pastel/neon 80..255 assente")\n', 1)

validator_path.write_text(val, encoding='utf-8')

# Documentation.
readme = readme_path.read_text(encoding='utf-8')
readme = readme.replace('ciclo rainbow in tempo reale', 'ciclo rainbow pastel/neon lento in tempo reale')
for line in (
    '- Menu 7 `Player Icon`: 36 icone Workshop selezionabili, con cursore persistente e feedback di applicazione.',
    '- Nelle liste player l’icona scelta precede l’icona eroe; la riga sinistra mostra soltanto il tempo e la riga destra soltanto il genere scelto, senza i prefissi `CHILL for` / `soundtrack`.',
):
    if line not in readme:
        readme += '\n' + line
readme += '\n'
readme_path.write_text(readme, encoding='utf-8')

project = project_path.read_text(encoding='utf-8')
project = project.replace('Il passo è 12 per tick, quindi il ciclo completo dura circa 12,75 secondi', 'Il passo è 3 per tick, quindi il ciclo completo dura circa 51 secondi')
project = project.replace('attraversando rosso → giallo → verde → ciano → blu → viola → rosso.', 'attraversando rosso → giallo → verde → ciano → blu → viola → rosso con canali compressi nel range circa 80–255 per una resa pastel/neon.')
if '### Menu 7 — Player Icon' not in project:
    project += '''\n\n### Menu 7 — Player Icon\n\nIl menu 7 contiene le 36 icone standard disponibili tramite `Icon String`, da `Arrow: Down` a `X`. La scelta è memorizzata in `IndeksIkon` e il cursore in `KursorIkon`; il default è `Heart`. L’icona viene inserita direttamente nelle due righe HUD prima della `Hero Icon String`, quindi non viene creato alcun `Create Icon` sopra al personaggio. Le righe del roster sono state compattate: a sinistra resta il numero di minuti, a destra il genere scelto (o il placeholder se non è stato ancora scelto).\n'''
project_path.write_text(project, encoding='utf-8')

tests = test_doc_path.read_text(encoding='utf-8')
for line in (
    '- **RGB pastel/neon live:** osservare il titolo per almeno 55 secondi; il ciclo deve essere più lento, luminoso e senza passare per canali scuri sotto circa 80.\n',
    '- **Player Icon live:** aprire menu 7, scorrere tutte le 36 icone, applicarne varie e verificare che compaiano nelle due liste prima dell’icona eroe, senza alcuna icona sopra al personaggio.\n',
    '- **Liste compatte live:** a sinistra verificare `icona + eroe + nome + N MIN` senza `CHILL for`; a destra `icona + eroe + nome + genere` senza il prefisso `soundtrack`.\n',
):
    if line not in tests:
        tests += '\n' + line
test_doc_path.write_text(tests, encoding='utf-8')

# Validation report source blob + rule count.
data = source_path.read_bytes().replace(b'\r\n', b'\n')
blob = hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()
report = report_path.read_text(encoding='utf-8')
report, n = re.subn(r'```text\n[0-9a-f]{40}\n```', f'```text\n{blob}\n```', report, count=1)
if n != 1:
    raise SystemExit('validation report blob marker not found')
rule_count = len(re.findall(r'(?m)^\s*rule\s*\(', src))
report = re.sub(r'Generi: 100 \| Lingue: 3 \| Regole: \d+ \| Raycast camera: 1', f'Generi: 100 | Lingue: 3 | Regole: {rule_count} | Raycast camera: 1', report, count=1)
report_path.write_text(report, encoding='utf-8')
