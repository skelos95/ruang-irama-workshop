from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
PROJECT = ROOT / "docs" / "PROGETTO.md"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one occurrence, found {count}")
    return text.replace(old, new, 1)


def regex_once(text: str, pattern: str, repl: str, label: str) -> str:
    result, count = re.subn(pattern, repl, text, count=1, flags=re.MULTILINE | re.DOTALL)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one regex match, found {count}")
    return result


source = SOURCE.read_text(encoding="utf-8")

# Player state and renderer for Menu 10.
source = replace_once(
    source,
    "\t\t68: ModeKebal\n\t\t69: IkonKebal\n",
    "\t\t68: ModeKebal\n\t\t69: IkonKebal\n\t\t70: KartuNasibAktif\n\t\t71: PosisiKartuNasib\n\t\t72: TeksKartuNasib\n",
    "luck-card player variables",
)
source = replace_once(
    source,
    "\t22: GambarSakelarTeleportasi\n\t23: GambarPrivasiInspeksi\n",
    "\t22: GambarSakelarTeleportasi\n\t23: GambarPrivasiInspeksi\n\t24: GambarNasib\n",
    "luck-card renderer subroutine",
)
source = replace_once(
    source,
    "Global.KodeMenu = Array(0, 1, 2, 3, 4, 5, 6, 7, 8, 9);",
    "Global.KodeMenu = Array(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10);",
    "eleven menu codes",
)

# Main menu navigation now has eleven entries.
source = replace_once(
    source,
    "Event Player.KursorUtama = (Event Player.KursorUtama + 1) % 10;",
    "Event Player.KursorUtama = (Event Player.KursorUtama + 1) % 11;",
    "main menu next",
)
source = replace_once(
    source,
    "Event Player.KursorUtama = (Event Player.KursorUtama + 9) % 10;",
    "Event Player.KursorUtama = (Event Player.KursorUtama + 10) % 11;",
    "main menu previous",
)

# Opening page 10 needs no cursor synchronization; page 9 remains privacy.
source = replace_once(
    source,
    "\t\t\tElse If(Event Player.HalamanMenu == 8);\n\t\t\t\tEvent Player.KursorTeleportasiJongkok = Event Player.KursorTeleportasiJongkok;\n\t\t\tElse;\n\t\t\t\tEvent Player.KursorPrivasiInspeksi = Event Player.KursorPrivasiInspeksi;\n\t\t\tEnd;\n\t\t\tCall Subroutine(GambarMenu);",
    "\t\t\tElse If(Event Player.HalamanMenu == 8);\n\t\t\t\tEvent Player.KursorTeleportasiJongkok = Event Player.KursorTeleportasiJongkok;\n\t\t\tElse If(Event Player.HalamanMenu == 9);\n\t\t\t\tEvent Player.KursorPrivasiInspeksi = Event Player.KursorPrivasiInspeksi;\n\t\t\tEnd;\n\t\t\tCall Subroutine(GambarMenu);",
    "submenu opening routing",
)

# Spawn Room rejection must keep the visible cursor on option 2/3 (1 HP).
source = replace_once(
    source,
    "\t\t\t\t\tEvent Player.KursorKebal = Event Player.ModeKebal;\n\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String(\"Unkillable: 1 HP is unavailable in Spawn Room. FULL HP is still available.\")",
    "\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String(\"Unkillable: 1 HP is unavailable in Spawn Room. FULL HP is still available.\")",
    "keep 1 HP cursor on blocked apply",
)
source = replace_once(
    source,
    "\t\tEvent Player.ModeKebal = 0;\n\t\tEvent Player.KursorKebal = 0;\n\t\tCall Subroutine(EfekPulihkan);",
    "\t\tEvent Player.ModeKebal = 0;\n\t\tEvent Player.KursorKebal = 1;\n\t\tCall Subroutine(EfekPulihkan);",
    "keep 1 HP cursor on spawn auto-disable",
)

# Menu 10 application: create one public card per owner, rising from the floor.
privacy_tail = '''\t\tElse;\n\t\t\tIf(Event Player.PrivasiInspeksiAktif != (Event Player.KursorPrivasiInspeksi == 1));\n\t\t\t\tEvent Player.PrivasiInspeksiAktif = Event Player.KursorPrivasiInspeksi == 1;\n\t\t\t\tIf(Event Player.PrivasiInspeksiAktif == True);\n\t\t\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String(\"Crouch privacy enabled. Enemies see nothing.\") : Event Player.IndeksBahasa == 1 ? Custom String(\"Privasi Jongkok aktif. Musuh tidak melihat apa pun.\") : Custom String(\"เปิดความเป็นส่วนตัวตอนย่อ ศัตรูจะไม่เห็นอะไรเลย\"));\n\t\t\t\tElse;\n\t\t\t\t\tCall Subroutine(EfekPulihkan);\n\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String(\"Crouch privacy disabled. HUD visible to everyone.\") : Event Player.IndeksBahasa == 1 ? Custom String(\"Privasi Jongkok nonaktif. HUD terlihat oleh semua.\") : Custom String(\"ปิดความเป็นส่วนตัวตอนย่อ ทุกคนเห็น HUD ได้\"));\n\t\t\t\tEnd;\n\t\t\tEnd;\n\t\t\tCall Subroutine(GambarMenu);\n\t\tEnd;'''
luck_tail = '''\t\tElse If(Event Player.HalamanMenu == 9);\n\t\t\tIf(Event Player.PrivasiInspeksiAktif != (Event Player.KursorPrivasiInspeksi == 1));\n\t\t\t\tEvent Player.PrivasiInspeksiAktif = Event Player.KursorPrivasiInspeksi == 1;\n\t\t\t\tIf(Event Player.PrivasiInspeksiAktif == True);\n\t\t\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String(\"Crouch privacy enabled. Enemies see nothing.\") : Event Player.IndeksBahasa == 1 ? Custom String(\"Privasi Jongkok aktif. Musuh tidak melihat apa pun.\") : Custom String(\"เปิดความเป็นส่วนตัวตอนย่อ ศัตรูจะไม่เห็นอะไรเลย\"));\n\t\t\t\tElse;\n\t\t\t\t\tCall Subroutine(EfekPulihkan);\n\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String(\"Crouch privacy disabled. HUD visible to everyone.\") : Event Player.IndeksBahasa == 1 ? Custom String(\"Privasi Jongkok nonaktif. HUD terlihat oleh semua.\") : Custom String(\"ปิดความเป็นส่วนตัวตอนย่อ ทุกคนเห็น HUD ได้\"));\n\t\t\t\tEnd;\n\t\t\tEnd;\n\t\t\tCall Subroutine(GambarMenu);\n\t\tElse;\n\t\t\tIf(Event Player.KartuNasibAktif == True);\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String(\"A luck card is already active. Close the menu and shoot it first.\") : Event Player.IndeksBahasa == 1 ? Custom String(\"Kartu nasib masih aktif. Tutup menu lalu tembak dulu.\") : Custom String(\"การ์ดเสี่ยงโชคยังทำงานอยู่ ปิดเมนูแล้วค่อยยิงมันก่อน\"));\n\t\t\tElse;\n\t\t\t\tEvent Player.KartuNasibAktif = True;\n\t\t\t\tEvent Player.PosisiKartuNasib = Nearest Walkable Position(Position Of(Event Player) + Direction From Angles(Horizontal Facing Angle Of(Event Player), 0) * 3) - Vector(0, 1.200, 0);\n\t\t\t\tCreate In-World Text(All Players(All Teams), Player Variable(Local Player, IndeksBahasa) == 0 ? Custom String(\"[ ? ]\\nTRY YOUR LUCK\") : Player Variable(Local Player, IndeksBahasa) == 1 ? Custom String(\"[ ? ]\\nCOBA NASIB\") : Custom String(\"[ ? ]\\nเสี่ยงโชค\"), Event Player.PosisiKartuNasib, 1.500, Do Not Clip, Visible To Position String and Color, Global.RGB, Visible Never);\n\t\t\t\tEvent Player.TeksKartuNasib = Last Text ID;\n\t\t\t\tPlay Effect(All Players(All Teams), Ring Explosion, Global.RGB, Event Player.PosisiKartuNasib + Vector(0, 1.200, 0), 3);\n\t\t\t\tChase Player Variable Over Time(Event Player, PosisiKartuNasib, Event Player.PosisiKartuNasib + Vector(0, 2.200, 0), 0.600, Destination and Duration);\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String(\"Luck card created. Close the menu and shoot it to reveal your fate.\") : Event Player.IndeksBahasa == 1 ? Custom String(\"Kartu nasib dibuat. Tutup menu lalu tembak untuk melihat nasibmu.\") : Custom String(\"สร้างการ์ดเสี่ยงโชคแล้ว ปิดเมนูแล้วยิงเพื่อดูชะตาของคุณ\"));\n\t\t\tEnd;\n\t\t\tCall Subroutine(GambarMenu);\n\t\tEnd;'''
source = replace_once(source, privacy_tail, luck_tail, "Menu 10 apply branch")

# Luck card owner-only activation and cleanup.
luck_rules = r'''
rule("18e - Nasib: Pemilik menembak kartu sendiri")
{
	event
	{
		Ongoing - Each Player;
		All;
		All;
	}

	conditions
	{
		Event Player.Manusia == True;
		Event Player.KartuNasibAktif == True;
		Event Player.MenuTerbuka == False;
		Has Spawned(Event Player) == True;
		Is Alive(Event Player) == True;
		Is Button Held(Event Player, Button(Primary Fire)) == True;
		Angle Between Vectors(Facing Direction Of(Event Player), Direction Towards(Eye Position(Event Player), Event Player.PosisiKartuNasib)) <= 7;
		Is In Line of Sight(Eye Position(Event Player), Event Player.PosisiKartuNasib, All Barriers Block LOS) == True;
	}

	actions
	{
		Stop Chasing Player Variable(Event Player, PosisiKartuNasib);
		If(Event Player.TeksKartuNasib != Null);
			Destroy In-World Text(Event Player.TeksKartuNasib);
		End;
		Event Player.TeksKartuNasib = Null;
		Event Player.KartuNasibAktif = False;
		Play Effect(All Players(All Teams), Ring Explosion, Global.RGB, Event Player.PosisiKartuNasib, 3);
		If(Random Integer(0, 1) == 0);
			Set Player Health(Event Player, Max Health(Event Player));
			Small Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("LUCK! Full health restored.") : Event Player.IndeksBahasa == 1 ? Custom String("BERUNTUNG! Kesehatan penuh dipulihkan.") : Custom String("โชคดี! ฟื้นพลังชีวิตเต็มแล้ว"));
		Else;
			Small Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("BAD LUCK! The card chose death.") : Event Player.IndeksBahasa == 1 ? Custom String("SIAL! Kartunya memilih kematian.") : Custom String("โชคร้าย! การ์ดเลือกความตาย"));
			Clear Status(Event Player, Unkillable);
			Kill(Event Player, Null);
		End;
	}
}

rule("18f - Nasib: Hapus kartu saat pemilik mati")
{
	event
	{
		Player Died;
		All;
		All;
	}

	conditions
	{
		Event Player.KartuNasibAktif == True;
	}

	actions
	{
		Stop Chasing Player Variable(Event Player, PosisiKartuNasib);
		If(Event Player.TeksKartuNasib != Null);
			Destroy In-World Text(Event Player.TeksKartuNasib);
		End;
		Event Player.TeksKartuNasib = Null;
		Event Player.KartuNasibAktif = False;
	}
}

'''
source = replace_once(
    source,
    'rule("19 - Teleportasi Jongkok: Buka tampilan selama Jongkok ditahan")',
    luck_rules + 'rule("19 - Teleportasi Jongkok: Buka tampilan selama Jongkok ditahan")',
    "luck-card runtime rules",
)

# Player-left cleanup before Event Player is removed from the parallel roster arrays.
source = replace_once(
    source,
    "\t\tIf(Global.IndeksKeluar >= 0);\n\t\t\tIf(Event Player.IkonKebal != Null);",
    "\t\tIf(Global.IndeksKeluar >= 0);\n\t\t\tIf(Event Player.KartuNasibAktif == True);\n\t\t\t\tStop Chasing Player Variable(Event Player, PosisiKartuNasib);\n\t\t\t\tIf(Event Player.TeksKartuNasib != Null);\n\t\t\t\t\tDestroy In-World Text(Event Player.TeksKartuNasib);\n\t\t\t\tEnd;\n\t\t\t\tEvent Player.TeksKartuNasib = Null;\n\t\t\t\tEvent Player.KartuNasibAktif = False;\n\t\t\tEnd;\n\t\t\tIf(Event Player.IkonKebal != Null);",
    "luck-card leave cleanup",
)

# Initialization.
source = replace_once(
    source,
    "\t\tEvent Player.ModeKebal = 0;\n\t\tEvent Player.IkonKebal = Null;\n",
    "\t\tEvent Player.ModeKebal = 0;\n\t\tEvent Player.IkonKebal = Null;\n\t\tEvent Player.KartuNasibAktif = False;\n\t\tEvent Player.PosisiKartuNasib = Vector(0, 0, 0);\n\t\tEvent Player.TeksKartuNasib = Null;\n",
    "luck-card initialization",
)

# Main-menu text for index 10 in all supported languages.
source = replace_once(
    source,
    ': Event Player.KursorUtama == 8 ? Custom String("8 - CROUCH TELEPORT\\nCURRENT: {0}", Event Player.TeleportasiJongkokDiaktifkan ? Custom String("ON") : Custom String("OFF"))\n\t\t\t: Custom String("9 - CROUCH PRIVACY\\nCURRENT: {0}", Event Player.PrivasiInspeksiAktif ? Custom String("ON") : Custom String("OFF"))',
    ': Event Player.KursorUtama == 8 ? Custom String("8 - CROUCH TELEPORT\\nCURRENT: {0}", Event Player.TeleportasiJongkokDiaktifkan ? Custom String("ON") : Custom String("OFF"))\n\t\t\t: Event Player.KursorUtama == 9 ? Custom String("9 - CROUCH PRIVACY\\nCURRENT: {0}", Event Player.PrivasiInspeksiAktif ? Custom String("ON") : Custom String("OFF"))\n\t\t\t: Custom String("10 - TRY YOUR LUCK\\nSTATUS: {0}", Event Player.KartuNasibAktif ? Custom String("ACTIVE") : Custom String("READY"))',
    "English main menu luck card",
)
source = replace_once(
    source,
    ': Event Player.KursorUtama == 8 ? Custom String("8 - TELEPORT JONGKOK\\nSAAT INI: {0}", Event Player.TeleportasiJongkokDiaktifkan ? Custom String("AKTIF") : Custom String("MATI"))\n\t\t\t: Custom String("9 - PRIVASI JONGKOK\\nSAAT INI: {0}", Event Player.PrivasiInspeksiAktif ? Custom String("AKTIF") : Custom String("MATI"))',
    ': Event Player.KursorUtama == 8 ? Custom String("8 - TELEPORT JONGKOK\\nSAAT INI: {0}", Event Player.TeleportasiJongkokDiaktifkan ? Custom String("AKTIF") : Custom String("MATI"))\n\t\t\t: Event Player.KursorUtama == 9 ? Custom String("9 - PRIVASI JONGKOK\\nSAAT INI: {0}", Event Player.PrivasiInspeksiAktif ? Custom String("AKTIF") : Custom String("MATI"))\n\t\t\t: Custom String("10 - COBA NASIB\\nSTATUS: {0}", Event Player.KartuNasibAktif ? Custom String("AKTIF") : Custom String("SIAP"))',
    "Indonesian main menu luck card",
)
source = replace_once(
    source,
    ': Event Player.KursorUtama == 8 ? Custom String("8 - เทเลพอร์ตตอนย่อ\\nสถานะ: {0}", Event Player.TeleportasiJongkokDiaktifkan ? Custom String("เปิด") : Custom String("ปิด"))\n\t\t\t: Custom String("9 - ความเป็นส่วนตัวตอนย่อ\\nสถานะ: {0}", Event Player.PrivasiInspeksiAktif ? Custom String("เปิด") : Custom String("ปิด")), Top, 100,',
    ': Event Player.KursorUtama == 8 ? Custom String("8 - เทเลพอร์ตตอนย่อ\\nสถานะ: {0}", Event Player.TeleportasiJongkokDiaktifkan ? Custom String("เปิด") : Custom String("ปิด"))\n\t\t\t: Event Player.KursorUtama == 9 ? Custom String("9 - ความเป็นส่วนตัวตอนย่อ\\nสถานะ: {0}", Event Player.PrivasiInspeksiAktif ? Custom String("เปิด") : Custom String("ปิด"))\n\t\t\t: Custom String("10 - เสี่ยงโชค\\nสถานะ: {0}", Event Player.KartuNasibAktif ? Custom String("ทำงาน") : Custom String("พร้อม")), Top, 100,',
    "Thai main menu luck card",
)

# Router and gold color for Menu 10.
source = replace_once(
    source,
    "\t\tElse If(Event Player.HalamanMenu == 8);\n\t\t\tCall Subroutine(GambarSakelarTeleportasi);\n\t\tElse;\n\t\t\tCall Subroutine(GambarPrivasiInspeksi);\n\t\tEnd;",
    "\t\tElse If(Event Player.HalamanMenu == 8);\n\t\t\tCall Subroutine(GambarSakelarTeleportasi);\n\t\tElse If(Event Player.HalamanMenu == 9);\n\t\t\tCall Subroutine(GambarPrivasiInspeksi);\n\t\tElse;\n\t\t\tCall Subroutine(GambarNasib);\n\t\tEnd;",
    "menu renderer router",
)
source = replace_once(
    source,
    ": (Event Player.HalamanMenu == -1 ? Event Player.KursorUtama : Event Player.HalamanMenu) == 8 ? Vector(190, 255, 80)\n\t\t\t: Vector(255, 120, 190), 0.350, Destination and Duration);",
    ": (Event Player.HalamanMenu == -1 ? Event Player.KursorUtama : Event Player.HalamanMenu) == 8 ? Vector(190, 255, 80)\n\t\t\t: (Event Player.HalamanMenu == -1 ? Event Player.KursorUtama : Event Player.HalamanMenu) == 9 ? Vector(255, 120, 190)\n\t\t\t: Vector(255, 210, 70), 0.350, Destination and Duration);",
    "Menu 10 color transition",
)

# Menu 10 HUD renderer.
luck_renderer = r'''
rule("91n - Subrutin: Gambar kartu nasib")
{
	event
	{
		Subroutine;
		GambarNasib;
	}

	actions
	{
		Create HUD Text(Event Player, Null, Event Player.IndeksBahasa == 0 ? Custom String("{0}\n{1}", Custom String("\n{0}: create | {1}: back", Input Binding String(Button(Interact)), Input Binding String(Button(Reload))), Custom String("Hold {0} 0.5 sec: close", Input Binding String(Button(Melee))))
			: Event Player.IndeksBahasa == 1 ? Custom String("{0}\n{1}", Custom String("\n{0}: buat | {1}: kembali", Input Binding String(Button(Interact)), Input Binding String(Button(Reload))), Custom String("Tahan {0} 0,5 dtk: tutup", Input Binding String(Button(Melee))))
			: Custom String("{0}\n{1}", Custom String("\n{0}: สร้าง | {1}: กลับ", Input Binding String(Button(Interact)), Input Binding String(Button(Reload))), Custom String("กด {0} ค้าง 0.5 วิ: ปิด", Input Binding String(Button(Melee)))),
			Event Player.IndeksBahasa == 0 ? Custom String("10 - TRY YOUR LUCK\nSTATUS: {0}\n> {1}", Event Player.KartuNasibAktif ? Custom String("ACTIVE") : Custom String("READY"), Event Player.KartuNasibAktif ? Custom String("SHOOT YOUR CARD") : Custom String("CREATE CARD"))
			: Event Player.IndeksBahasa == 1 ? Custom String("10 - COBA NASIB\nSTATUS: {0}\n> {1}", Event Player.KartuNasibAktif ? Custom String("AKTIF") : Custom String("SIAP"), Event Player.KartuNasibAktif ? Custom String("TEMBAK KARTUMU") : Custom String("BUAT KARTU"))
			: Custom String("10 - เสี่ยงโชค\nสถานะ: {0}\n> {1}", Event Player.KartuNasibAktif ? Custom String("ทำงาน") : Custom String("พร้อม"), Event Player.KartuNasibAktif ? Custom String("ยิงการ์ดของคุณ") : Custom String("สร้างการ์ด")), Top, 100,
			Color(White), Custom Color(255, 240, 190, 255), Custom Color(X Component Of(Event Player.WarnaMenu), Y Component Of(Event Player.WarnaMenu), Z Component Of(Event Player.WarnaMenu), 255), Visible To String and Color, Visible Never);
		Event Player.HudMenu = Last Text ID;
	}
}

'''
source = replace_once(
    source,
    'rule("91k - Subrutin: Transisi warna menu tanpa lompatan")',
    luck_renderer + 'rule("91k - Subrutin: Transisi warna menu tanpa lompatan")',
    "luck-card renderer rule",
)

# Keep the Menu-open message accurate.
source = replace_once(source, "Arcade Menu online. Eight extremely important decisions await.", "Arcade Menu online. Eleven extremely important decisions await.", "English menu count message")
source = replace_once(source, "Menu Arcade online. Delapan keputusan yang sangat penting menunggu.", "Menu Arcade online. Sebelas keputusan yang sangat penting menunggu.", "Indonesian menu count message")
source = replace_once(source, "เปิดเมนูอาร์เคดแล้ว มีแปดตัวเลือกสำคัญรอคุณอยู่", "เปิดเมนูอาร์เคดแล้ว มีสิบเอ็ดตัวเลือกสำคัญรอคุณอยู่", "Thai menu count message")

SOURCE.write_text(source, encoding="utf-8")

# Static validator: eleven menu codes and the new renderer.
validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_once(
    validator,
    'checks.equal(codes, ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"], "codici dei dieci menu")',
    'checks.equal(codes, ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"], "codici degli undici menu")',
    "validator menu codes",
)
validator = replace_once(
    validator,
    're.search(r"KursorUtama\\s*=\\s*\\([^;]+\\)\\s*%\\s*10\\s*;", clean) is not None,\n        "navigazione principale non limitata a dieci menu",',
    're.search(r"KursorUtama\\s*=\\s*\\([^;]+\\)\\s*%\\s*11\\s*;", clean) is not None,\n        "navigazione principale non limitata a undici menu",',
    "validator main menu modulo",
)
validator = replace_once(
    validator,
    '"GambarSakelarTeleportasi", "GambarPrivasiInspeksi",',
    '"GambarSakelarTeleportasi", "GambarPrivasiInspeksi", "GambarNasib",',
    "validator renderer set",
)
VALIDATOR.write_text(validator, encoding="utf-8")

# Project notes.
project = PROJECT.read_text(encoding="utf-8")
project = replace_once(project, "## Main Menu: 8 voci", "## Main Menu: 11 voci", "project menu heading")
project = replace_once(
    project,
    "| 9 | Crouch Privacy | ON nasconde l’intero HUD inspection ai nemici; alleati sempre completi; default OFF |",
    "| 9 | Crouch Privacy | ON nasconde l’intero HUD inspection ai nemici; alleati sempre completi; default OFF |\n| 10 | Try Your Luck | crea una carta pubblica; solo il proprietario può attivarla, con esito 50/50 cura completa o morte |",
    "project Menu 10 row",
)
project = replace_once(project, "- 8 menu EN/ID/TH;", "- 11 menu EN/ID/TH;", "project test menu count")
project = replace_once(
    project,
    "Non può essere attivato nello Spawn Room e viene disattivato automaticamente entrando nello spawn.",
    "Non può essere attivato nello Spawn Room e viene disattivato automaticamente entrando nello spawn. Se l'opzione 1 HP viene rifiutata mentre il menu è aperto, il cursore resta sulla voce 2/3 e lo `Small Message` spiega il blocco.",
    "project 1 HP cursor note",
)
menu10_doc = '''\n\n## Menu 10 — Try Your Luck\n\nInteract crea davanti al giocatore una carta virtuale che emerge dal terreno con un `Ring Explosion`. La carta usa `Create In-World Text`, è visibile a tutti e non occupa slot bot. Ogni giocatore può avere una sola carta attiva.\n\nL'attivazione è proprietario-only: la regola legge esclusivamente `KartuNasibAktif` e `PosisiKartuNasib` dell'`Event Player`, richiede Primary Fire, mira entro 7° e linea di vista libera. Al colpo estrae `Random Integer(0, 1)`: un esito ripristina la salute massima, l'altro forza la morte del proprietario. Testo e stato vengono ripuliti anche alla morte o all'uscita del giocatore.\n'''
project = replace_once(project, "\n## Jump respawn\n", menu10_doc + "\n## Jump respawn\n", "project Menu 10 section")
PROJECT.write_text(project, encoding="utf-8")
