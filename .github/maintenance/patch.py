from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
TESTS = ROOT / "tests" / "test_validate_workshop.py"
VERSION = ROOT / "VERSION"
README = ROOT / "README.md"
PROJECT = ROOT / "docs" / "PROGETTO.md"

OLD_BLOB = "c808d7be03f2e7cf2d1f9c05ad39c63ff0cff8b0"
NEW_VERSION = "0.7.2"


def git_blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def replace_exact(text: str, old: str, new: str, expected: int = 1) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"replacement mismatch: expected {expected}, found {count}: {old[:120]!r}")
    return text.replace(old, new)


def rule_bounds(text: str, title: str) -> tuple[int, int]:
    needle = f'rule("{title}")'
    start = text.index(needle)
    next_rule = text.find('\nrule("', start + len(needle))
    return start, len(text) if next_rule < 0 else next_rule


def edit_rule(text: str, title: str, editor) -> str:
    start, end = rule_bounds(text, title)
    block = text[start:end]
    edited = editor(block)
    if edited == block:
        raise RuntimeError(f"rule was not changed: {title}")
    return text[:start] + edited + text[end:]


def replace_rule(text: str, title: str, new_block: str) -> str:
    start, end = rule_bounds(text, title)
    return text[:start] + new_block.rstrip() + "\n" + text[end:]


def remove_rule(text: str, title: str) -> str:
    start, end = rule_bounds(text, title)
    return text[:start] + text[end:]


source = SOURCE.read_text(encoding="utf-8")
if git_blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch a moving target")

# Inspection world text belongs only to the player-target page while Crouch Teleport is open.
def tighten_inspection_lifecycle(block: str) -> str:
    old = '''\t\tIf(Global.PemainAktif.InspeksiAktif == True);\n\t\tIf(Or(Or(Or(Or(Is Button Held(Global.PemainAktif, Button(Crouch)) == False, Global.PemainAktif.MenuTerbuka == True), Has Spawned(Global.PemainAktif) == False),\n\t\tIs Alive(Global.PemainAktif) == False),\n\t\tGlobal.PemainAktif.ModeKamera == 2) == True);'''
    new = '''\t\tIf(Global.PemainAktif.InspeksiAktif == True);\n\t\tIf(Or(Or(Or(Or(Or(Is Button Held(Global.PemainAktif, Button(Crouch)) == False, Global.PemainAktif.MenuTerbuka == True), Has Spawned(Global.PemainAktif) == False),\n\t\tIs Alive(Global.PemainAktif) == False), Global.PemainAktif.ModeKamera == 2), And(Global.PemainAktif.TeleportasiJongkokAktif == True,\n\t\tGlobal.PemainAktif.KursorTeleportasi != 2)) == True);'''
    return replace_exact(block, old, new)


source = edit_rule(source, "04h - Global-first: Pengatur lifecycle ringan terpusat", tighten_inspection_lifecycle)

# Teleport player targeting is no longer a passive 1 Hz list. Remove that old section from 04i.
def remove_old_teleport_cache(block: str) -> str:
    start = block.index("\t\t\t\tIf(Global.PemainAktif.TeleportasiJongkokAktif == True);")
    end_marker = "\n\t\t\t\tEnd;\n\t\t\tEnd;\n\t\tEnd;"
    end = block.index(end_marker, start)
    return block[:start] + block[end + len("\n\t\t\t\tEnd;"):]


source = edit_rule(source, "04i - Global-first: Cache dan daftar pasif 1 Hz", remove_old_teleport_cache)

# Extend the existing 4 Hz reticle manager with the privacy-filtered Teleport target.
def add_reticle_teleport(block: str) -> str:
    block = block.replace(
        'rule("04k - Global-first: Inspeksi aktif terpusat 4 Hz")',
        'rule("04k - Global-first: Inspeksi dan target teleport terpusat 4 Hz")',
        1,
    )
    marker = "\t\t\tEnd;\n\t\tEnd;\n\t\tGlobal.PemainAktif = Null;"
    insert = '''\t\t\tEnd;\n\n\t\t\tIf(And(Global.PemainAktif.TeleportasiJongkokAktif == True, Global.PemainAktif.KursorTeleportasi == 2));\n\t\t\t\tSet Player Variable(Global.PemainAktif, DaftarTargetTeleportasi, Filtered Array(All Players(All Teams), And(Current Array Element != Global.PemainAktif,\n\t\t\t\t\tAnd(Player Variable(Current Array Element, PrivasiInspeksiAktif) == False, And(Entity Exists(Current Array Element),\n\t\t\t\t\tAnd(Has Spawned(Current Array Element), Is Alive(Current Array Element))))));\n\t\t\t\tIf(Count Of(Global.PemainAktif.DaftarTargetTeleportasi) == 0);\n\t\t\t\t\tSet Player Variable(Global.PemainAktif, CalonTargetTeleportasi, Null);\n\t\t\t\tElse;\n\t\t\t\t\tSet Player Variable(Global.PemainAktif, CalonTargetTeleportasi, First Of(Sorted Array(Global.PemainAktif.DaftarTargetTeleportasi,\n\t\t\t\t\t\tAngle Between Vectors(Facing Direction Of(Global.PemainAktif), Direction Towards(Eye Position(Global.PemainAktif), Eye Position(Current Array Element))))));\n\t\t\t\tEnd;\n\t\t\t\tIf(Global.PemainAktif.InspeksiAktif == True);\n\t\t\t\t\tSet Player Variable(Global.PemainAktif, TargetInspeksi, Global.PemainAktif.CalonTargetTeleportasi);\n\t\t\t\tEnd;\n\t\t\tEnd;\n\t\tEnd;\n\t\tGlobal.PemainAktif = Null;'''
    return replace_exact(block, marker, insert)


source = edit_rule(source, "04k - Global-first: Inspeksi aktif terpusat 4 Hz", add_reticle_teleport)

# Do not create inspection text on Spawn/Objective pages; page 3 reuses it for the visible target name.
def gate_inspection_to_player_page(block: str) -> str:
    return replace_exact(
        block,
        "\t\tEvent Player.MenuTerbuka == False;\n\t\tEvent Player.ModeKamera != 2;",
        "\t\tEvent Player.MenuTerbuka == False;\n\t\tOr(Event Player.TeleportasiJongkokAktif == False, Event Player.KursorTeleportasi == 2) == True;\n\t\tEvent Player.ModeKamera != 2;",
    )


source = edit_rule(source, "13 - Intip Pahlawan: Tampilkan ikon, nama, dan kesehatan saat ini", gate_inspection_to_player_page)

# Opening Crouch Teleport always starts on page 1 and clears stale target state.
def reset_teleport_overlay(block: str) -> str:
    block = block.replace(
        'rule("19 - Teleportasi Jongkok: Buka tampilan selama Jongkok ditahan")',
        'rule("19 - Teleportasi Jongkok: Buka tiga halaman selama Jongkok ditahan")',
        1,
    )
    return replace_exact(
        block,
        "\t\tEvent Player.TeleportasiJongkokAktif = True;\n\t\tEvent Player.PerintahTeleportasi = 0;\n\t\tEvent Player.JenisTeleportasiTerkunci = -1;\n\t\tEvent Player.TargetTeleportasiTerkunci = Null;",
        "\t\tEvent Player.TeleportasiJongkokAktif = True;\n\t\tEvent Player.PerintahTeleportasi = 0;\n\t\tEvent Player.KursorTeleportasi = 0;\n\t\tEvent Player.DaftarTargetTeleportasi = Empty Array;\n\t\tEvent Player.CalonTargetTeleportasi = Null;\n\t\tEvent Player.JenisTeleportasiTerkunci = -1;\n\t\tEvent Player.TargetTeleportasiTerkunci = Null;",
    )


source = edit_rule(source, "19 - Teleportasi Jongkok: Buka tampilan selama Jongkok ditahan", reset_teleport_overlay)

source = replace_rule(source, "19a - Teleportasi Jongkok: Pengatur masukan terpisah dari Menu Arkade", r'''rule("19a - Teleportasi Jongkok: Primary teleport, Secondary ganti halaman")
{
	event
	{
		Ongoing - Each Player;
		All;
		All;
	}

	conditions
	{
		Event Player.TeleportasiJongkokAktif == True;
		Event Player.PerintahTeleportasi == 0;
		Is Button Held(Event Player, Button(Crouch)) == True;
		Or(Is Button Held(Event Player, Button(Primary Fire)), Is Button Held(Event Player, Button(Secondary Fire))) == True;
	}

	actions
	{
		If(Is Button Held(Event Player, Button(Primary Fire)));
			Event Player.PerintahTeleportasi = 1;
		Else;
			Event Player.PerintahTeleportasi = 2;
		End;
	}
}''')

source = replace_rule(source, "19b - Teleportasi Jongkok: Aktifkan lagi pengatur setelah tombol dilepas", r'''rule("19b - Teleportasi Jongkok: Lepaskan latch Primary dan Secondary")
{
	event
	{
		Ongoing - Each Player;
		All;
		All;
	}

	conditions
	{
		Event Player.TeleportasiJongkokAktif == True;
		Event Player.PerintahTeleportasi != 0;
		Is Button Held(Event Player, Button(Primary Fire)) == False;
		Is Button Held(Event Player, Button(Secondary Fire)) == False;
	}

	actions
	{
		Event Player.PerintahTeleportasi = 0;
	}
}''')

source = replace_rule(source, "19c - Teleportasi Jongkok: Tembakan utama memilih tujuan berikutnya", r'''rule("19c - Teleportasi Jongkok: Secondary Fire mengganti tiga halaman")
{
	event
	{
		Ongoing - Each Player;
		All;
		All;
	}

	conditions
	{
		Event Player.TeleportasiJongkokAktif == True;
		Event Player.PerintahTeleportasi == 2;
	}

	actions
	{
		Event Player.KursorTeleportasi = (Event Player.KursorTeleportasi + 1) % 3;
		If(Event Player.KursorTeleportasi != 2);
			Event Player.CalonTargetTeleportasi = Null;
		End;
	}
}''')

source = remove_rule(source, "19d - Teleportasi Jongkok: Tembakan sekunder memilih tujuan sebelumnya")

# Primary Fire executes whichever of the three pages is active. Page 3 locks the current reticle target.
def primary_exec(block: str) -> str:
    block = block.replace(
        'rule("19e - Teleportasi Jongkok: Interact menjalankan teleportasi")',
        'rule("19e - Teleportasi Jongkok: Primary Fire menjalankan halaman aktif")',
        1,
    )
    old = '''\t\tEvent Player.JenisTeleportasiTerkunci = Event Player.KursorTeleportasi < 2 ? Event Player.KursorTeleportasi : 2;\n\t\tEvent Player.TargetTeleportasiTerkunci = Null;\n\t\tIf(And(Event Player.JenisTeleportasiTerkunci == 2, And(Event Player.KursorTeleportasi >= 0, Event Player.KursorTeleportasi < Count Of(Event Player.DaftarTargetTeleportasi))));\n\t\t\tEvent Player.TargetTeleportasiTerkunci = Event Player.DaftarTargetTeleportasi[Event Player.KursorTeleportasi];\n\t\tEnd;\n\t\tCall Subroutine(SegarkanTargetTeleportasi);'''
    new = '''\t\tEvent Player.JenisTeleportasiTerkunci = Event Player.KursorTeleportasi;\n\t\tEvent Player.TargetTeleportasiTerkunci = Null;\n\t\tCall Subroutine(SegarkanTargetTeleportasi);\n\t\tIf(Event Player.JenisTeleportasiTerkunci == 2);\n\t\t\tEvent Player.TargetTeleportasiTerkunci = Event Player.CalonTargetTeleportasi;\n\t\tEnd;'''
    return replace_exact(block, old, new)


source = edit_rule(source, "19e - Teleportasi Jongkok: Interact menjalankan teleportasi", primary_exec)

# Clear page/reticle state when Crouch is released.
def clean_overlay_close(block: str) -> str:
    return replace_exact(
        block,
        "\t\tEvent Player.PerintahTeleportasi = 0;\n\t\tEvent Player.JenisTeleportasiTerkunci = -1;\n\t\tEvent Player.TargetTeleportasiTerkunci = Null;",
        "\t\tEvent Player.PerintahTeleportasi = 0;\n\t\tEvent Player.KursorTeleportasi = 0;\n\t\tEvent Player.DaftarTargetTeleportasi = Empty Array;\n\t\tEvent Player.CalonTargetTeleportasi = Null;\n\t\tEvent Player.JenisTeleportasiTerkunci = -1;\n\t\tEvent Player.TargetTeleportasiTerkunci = Null;",
    )


source = edit_rule(source, "19g - Teleportasi Jongkok: Tutup saat Jongkok dilepas", clean_overlay_close)

# Three-page HUD: Secondary cycles pages; Primary executes. Page 3 follows the closest public target to the reticle.
source = replace_rule(source, "91g - Subrutin: Gambar menu teleportasi", r'''rule("91g - Subrutin: Gambar menu teleportasi")
{
	event
	{
		Subroutine;
		GambarTeleportasi;
	}

	actions
	{
		If(Event Player.HudMenu != Null);
			Destroy HUD Text(Event Player.HudMenu);
		End;
		Event Player.HudMenu = Null;
		If(Index Of Array Value(Global.PemainManusia, Event Player) >= 0);
			Global.HudMenuPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = 0;
		End;
		Event Player.KursorTeleportasi %= 3;
		Create HUD Text(Event Player, Null, Event Player.IndeksBahasa == 0 ? Custom String("{0}\
{1}",
			Custom String("\
{0}: teleport | {1}: next page", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire))),
			Custom String("release {0}: close", Input Binding String(Button(Crouch)))) : Event Player.IndeksBahasa == 1 ? Custom String("{0}\
{1}",
			Custom String("\
{0}: teleport | {1}: halaman berikutnya", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire))),
			Custom String("lepas {0}: tutup", Input Binding String(Button(Crouch)))) : Custom String("{0}\
{1}", Custom String(
			"\
{0}: เทเลพอร์ต | {1}: หน้าถัดไป", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire))),
			Custom String("ปล่อย {0}: ปิด", Input Binding String(Button(Crouch)))), Event Player.IndeksBahasa == 0
			? Event Player.KursorTeleportasi == 0 ? Custom String("TELEPORT 1/3\
> SPAWN ROOM\
{0}", Is In Spawn Room(Event Player) ? Custom String("YOU ARE ALREADY HERE") : Event Player.PunyaPosisiMuncul ? Custom String("READY") : Custom String("VISIT SPAWN TO REGISTER IT"))
			: Event Player.KursorTeleportasi == 1 ? Custom String("TELEPORT 2/3\
> OBJECTIVE / FLAG\
PRIMARY FIRE: TELEPORT")
			: Custom String("TELEPORT 3/3\
> ALL PLAYERS\
TARGET: {0}\
AIM AT A VISIBLE NAME", Event Player.CalonTargetTeleportasi != Null ? Event Player.CalonTargetTeleportasi : Custom String("NO PUBLIC TARGET"))
			: Event Player.IndeksBahasa == 1 ? Event Player.KursorTeleportasi == 0 ? Custom String("TELEPORT 1/3\
> RUANG MUNCUL\
{0}", Is In Spawn Room(Event Player) ? Custom String("KAMU SUDAH DI SINI") : Event Player.PunyaPosisiMuncul ? Custom String("SIAP") : Custom String("MASUK SPAWN UNTUK MENYIMPANNYA"))
			: Event Player.KursorTeleportasi == 1 ? Custom String("TELEPORT 2/3\
> OBJEKTIF / BENDERA\
PRIMARY FIRE: TELEPORT")
			: Custom String("TELEPORT 3/3\
> SEMUA PLAYER\
TARGET: {0}\
ARAHKAN KE NAMA YANG TERLIHAT", Event Player.CalonTargetTeleportasi != Null ? Event Player.CalonTargetTeleportasi : Custom String("TIDAK ADA TARGET PUBLIK"))
			: Event Player.KursorTeleportasi == 0 ? Custom String("เทเลพอร์ต 1/3\
> ห้องเกิด\
{0}", Is In Spawn Room(Event Player) ? Custom String("คุณอยู่ที่นี่แล้ว") : Event Player.PunyaPosisiMuncul ? Custom String("พร้อม") : Custom String("ไปห้องเกิดเพื่อบันทึกตำแหน่ง"))
			: Event Player.KursorTeleportasi == 1 ? Custom String("เทเลพอร์ต 2/3\
> เป้าหมาย / ธง\
ยิงหลัก: เทเลพอร์ต")
			: Custom String("เทเลพอร์ต 3/3\
> ผู้เล่นทั้งหมด\
เป้าหมาย: {0}\
เล็งไปที่ชื่อที่มองเห็น", Event Player.CalonTargetTeleportasi != Null ? Event Player.CalonTargetTeleportasi : Custom String("ไม่มีเป้าหมายสาธารณะ")), Top, 100,
			Color(White), Custom Color(205, 255, 225, 255), Custom Color(80, 255, 160, 255), Visible To and String, Visible Never);
		Event Player.HudMenu = Last Text ID;
		If(Index Of Array Value(Global.PemainManusia, Event Player) >= 0);
			Global.HudMenuPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = Event Player.HudMenu;
		End;
	}
}''')

# The Teleport target list now contains players only; selection is closest angle to the reticle and privacy OFF.
source = replace_rule(source, "98 - Subrutin: Segarkan ruang muncul, objektif, dan target teleportasi", r'''rule("98 - Subrutin: Cari target teleport publik terdekat dari bidikan")
{
	event
	{
		Subroutine;
		SegarkanTargetTeleportasi;
	}

	actions
	{
		Event Player.DaftarTargetTeleportasi = Filtered Array(All Players(All Teams), And(Current Array Element != Event Player,
			And(Player Variable(Current Array Element, PrivasiInspeksiAktif) == False, And(Entity Exists(Current Array Element),
			And(Has Spawned(Current Array Element), Is Alive(Current Array Element))))));
		If(Count Of(Event Player.DaftarTargetTeleportasi) == 0);
			Event Player.CalonTargetTeleportasi = Null;
		Else;
			Event Player.CalonTargetTeleportasi = First Of(Sorted Array(Event Player.DaftarTargetTeleportasi, Angle Between Vectors(Facing Direction Of(Event Player),
				Direction Towards(Eye Position(Event Player), Eye Position(Current Array Element)))));
		End;
	}
}''')

SOURCE.write_text(source, encoding="utf-8")
new_blob = git_blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_exact(validator, '"""Static gate for CHILL Dedicated Server 0.7.1 Global-first."""', '"""Static gate for CHILL Dedicated Server 0.7.2 Global-first."""')
validator = replace_exact(validator, 'CURRENT_VERSION = "0.7.1"', f'CURRENT_VERSION = "{NEW_VERSION}"')
validator = replace_exact(validator, f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"', f'EXPECTED_SOURCE_BLOB = "{new_blob}"')
validator = replace_exact(validator, 'checks.require(len(rules) >= 76, "numero regole inatteso")', 'checks.require(len(rules) >= 75, "numero regole inatteso")')
validator = replace_exact(
    validator,
    '        "19c - Teleportasi Jongkok:", "19d - Teleportasi Jongkok:", "19e - Teleportasi Jongkok:",\n',
    '        "19c - Teleportasi Jongkok:", "19e - Teleportasi Jongkok:",\n',
)
validator = replace_exact(validator, '    interact = find_rule(rules, "10 - Menu:")\n', '''    teleport_cycle = find_rule(rules, "19c - Teleportasi Jongkok:")\n    teleport_exec = find_rule(rules, "19e - Teleportasi Jongkok:")\n    teleport_refresh = find_rule(rules, "98 - Subrutin:")\n    teleport_render = find_rule(rules, "91g - Subrutin:")\n    checks.require(find_rule(rules, "19d - Teleportasi Jongkok:") is None, "selector manuale Teleport 19d ancora presente")\n    checks.require("Event Player.PerintahTeleportasi = 3;" not in source, "Teleport usa ancora il terzo comando legacy")\n    if teleport_cycle:\n        checks.require("Event Player.KursorTeleportasi = (Event Player.KursorTeleportasi + 1) % 3;" in teleport_cycle.body, "Teleport non cicla tre pagine con Secondary")\n    if teleport_exec:\n        checks.require("Call Subroutine(SegarkanTargetTeleportasi);" in teleport_exec.body, "Primary Teleport non aggiorna il target al click")\n        checks.require("TargetTeleportasiTerkunci = Event Player.CalonTargetTeleportasi;" in teleport_exec.body, "Primary Teleport non blocca il closest-to-reticle")\n    if teleport_refresh:\n        checks.require("First Of(Sorted Array(Event Player.DaftarTargetTeleportasi" in teleport_refresh.body, "Teleport non usa closest-to-reticle")\n        checks.require("Player Variable(Current Array Element, PrivasiInspeksiAktif) == False" in teleport_refresh.body, "Teleport ignora la privacy")\n        checks.require("Append To Array(Array(Event Player, Null)" not in teleport_refresh.body, "Teleport usa ancora sentinelle Spawn/Objective nella lista player")\n    if teleport_render:\n        checks.require("Event Player.KursorTeleportasi %= 3;" in teleport_render.body and "ALL PLAYERS" in teleport_render.body, "HUD Teleport non espone tre pagine")\n    teleport_global = find_rule(rules, "04k - Global-first:")\n    if teleport_global:\n        checks.require("Global.PemainAktif.KursorTeleportasi == 2" in teleport_global.body and "CalonTargetTeleportasi" in teleport_global.body, "target Teleport non è aggiornato globalmente a 4 Hz")\n    interact = find_rule(rules, "10 - Menu:")\n''')
validator = replace_exact(
    validator,
    '        checks.require("Is Alive(Global.PemainAktif.TargetKamera) == False" in lifecycle.body, "Camera globale non rilascia target morto")\n',
    '        checks.require("Is Alive(Global.PemainAktif.TargetKamera) == False" in lifecycle.body, "Camera globale non rilascia target morto")\n        checks.require("Global.PemainAktif.KursorTeleportasi != 2" in lifecycle.body, "Inspection resta visibile fuori dalla pagina player Teleport")\n',
)
validator = replace_exact(validator, 'print("OK - controlli statici v0.7.0 Global-first superati")', 'print("OK - controlli statici v0.7.2 Global-first superati")')
VALIDATOR.write_text(validator, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
tests = replace_exact(tests, "class GlobalFirst071Tests", "class GlobalFirst072Tests")
extra_tests = '''    def test_teleport_uses_three_pages(self) -> None:\n        mutated = self.source.replace(\n            "Event Player.KursorTeleportasi = (Event Player.KursorTeleportasi + 1) % 3;",\n            "Event Player.KursorTeleportasi = (Event Player.KursorTeleportasi + 1) % 2;",\n            1,\n        )\n        self.assertTrue(any("tre pagine" in error for error in self.errors(mutated)))\n\n    def test_teleport_privacy_filter_is_required(self) -> None:\n        start = self.source.index('rule("98 - Subrutin:')\n        pos = self.source.index("Player Variable(Current Array Element, PrivasiInspeksiAktif) == False", start)\n        mutated = self.source[:pos] + self.source[pos:].replace(\n            "Player Variable(Current Array Element, PrivasiInspeksiAktif) == False",\n            "Player Variable(Current Array Element, PrivasiInspeksiAktif) == True",\n            1,\n        )\n        self.assertTrue(any("privacy" in error for error in self.errors(mutated)))\n\n    def test_teleport_closest_to_reticle_is_required(self) -> None:\n        start = self.source.index('rule("98 - Subrutin:')\n        pos = self.source.index("First Of(Sorted Array(Event Player.DaftarTargetTeleportasi", start)\n        mutated = self.source[:pos] + self.source[pos:].replace(\n            "First Of(Sorted Array(Event Player.DaftarTargetTeleportasi",\n            "First Of(Event Player.DaftarTargetTeleportasi",\n            1,\n        )\n        self.assertTrue(any("closest-to-reticle" in error for error in self.errors(mutated)))\n\n'''
tests = replace_exact(tests, "    def test_preloaded_submenu_is_required(self) -> None:\n", extra_tests + "    def test_preloaded_submenu_is_required(self) -> None:\n")
TESTS.write_text(tests, encoding="utf-8")

VERSION.write_text(NEW_VERSION + "\n", encoding="utf-8")

readme = README.read_text(encoding="utf-8")
readme = replace_exact(readme, "La versione **0.7.1** identifica lo stato funzionale e tecnico corrente del repository.", "La versione **0.7.2** identifica lo stato funzionale e tecnico corrente del repository.")
readme = readme.replace("- refresh passivi Camera/Revenge/Teleport a **1 Hz**;", "- refresh passivi Camera/Revenge a **1 Hz**;\n- target player Teleport closest-to-reticle a **4 Hz** solo sulla pagina `All Players`;")
old_tp = '''## Teleport Crouch\n\nL'overlay Teleport include:\n\n- Spawn Room registrata;\n- obiettivo della modalità quando disponibile;\n- player/bot validi, esclusi i player con **Crouch Privacy ON**.\n\nEscort/Hybrid usano `Payload Position`, CTF usa la flag nemica, Push prova un player sull'obiettivo come proxy del robot e usa il fallback obiettivo quando disponibile.\n'''
new_tp = '''## Teleport Crouch\n\nL'overlay Teleport ha **tre pagine fisse**: `Spawn Room`, `Objective / Flag` e `All Players`. Tenendo Crouch, **Secondary Fire** passa alla pagina successiva e **Primary Fire** esegue subito il teleport della pagina attiva.\n\nNella pagina `All Players` non esiste più uno scorrimento manuale: il target è il player/bot valido **più vicino al reticolo**, aggiornato a 4 Hz e ricalcolato anche al click. Sono eleggibili solo target vivi/spawnati con **Crouch Privacy OFF**; il nome mostrato dall'inspection corrisponde al target che verrà usato dal teleport.\n\nEscort/Hybrid usano `Payload Position`, CTF usa la flag nemica, Push prova un player sull'obiettivo come proxy del robot e usa il fallback obiettivo quando disponibile.\n'''
readme = replace_exact(readme, old_tp, new_tp)
readme += '''\n\n### Teleport reticle 0.7.2\n\nCrouch Teleport è stato ridisegnato su tre sole pagine. Secondary Fire cicla `Spawn Room → Objective / Flag → All Players`; Primary Fire teletrasporta immediatamente. La pagina player usa il closest-to-reticle con privacy OFF e non mantiene più cursori manuali per i singoli player. Il calcolo continuo vive nel manager globale 4 Hz e il click esegue un refresh immediato prima di bloccare l'identità del target.\n'''
README.write_text(readme, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
project = replace_exact(project, "# Note di progetto — versione 0.7.1", "# Note di progetto — versione 0.7.2")
project = replace_exact(project, "Questo documento descrive lo **stato funzionale e tecnico corrente** del Workshop 0.7.1.", "Questo documento descrive lo **stato funzionale e tecnico corrente** del Workshop 0.7.2.")
old_project_tp = '''## Teleport Crouch\n\nL'overlay Crouch conserva il proprio cursore e può selezionare:\n\n- ultima Spawn Room registrata;\n- destinazione obiettivo/modalità;\n- player/bot validi.\n\nGestione modalità:\n\n- Escort/Hybrid → `Payload Position`;\n- CTF → flag nemica;\n- Push → player sull'obiettivo come proxy robot, poi fallback obiettivo;\n- altre modalità → `Objective Position` quando disponibile.\n\nIl target player viene bloccato per identità prima del refresh per evitare retarget accidentali se qualcuno esce.\n'''
new_project_tp = '''## Teleport Crouch\n\nL'overlay Crouch usa tre pagine fisse: **Spawn Room**, **Objective / Flag**, **All Players**. Secondary Fire avanza ciclicamente tra le tre pagine; Primary Fire esegue il teleport. Interact non seleziona più la destinazione.\n\nSulla pagina `All Players`, `DaftarTargetTeleportasi` contiene solo entità diverse dal viewer, esistenti, spawnate, vive e con `PrivasiInspeksiAktif == False`. `CalonTargetTeleportasi` è il primo elemento di un `Sorted Array` ordinato per angolo rispetto al reticolo. Il manager globale `04k` lo aggiorna a 4 Hz e `SegarkanTargetTeleportasi` lo ricalcola immediatamente al click; solo dopo viene copiato in `TargetTeleportasiTerkunci`.\n\nGestione modalità:\n\n- Escort/Hybrid → `Payload Position`;\n- CTF → flag nemica;\n- Push → player sull'obiettivo come proxy robot, poi fallback obiettivo;\n- altre modalità → `Objective Position` quando disponibile.\n'''
project = replace_exact(project, old_project_tp, new_project_tp)
project = project.replace("- refresh Camera/Revenge/Teleport passivi a 1 Hz;", "- refresh Camera/Revenge passivi a 1 Hz;\n- target player Teleport closest-to-reticle a 4 Hz solo sulla terza pagina;")
project = project.replace("- inspection a 5 Hz;", "- inspection a 4 Hz;")
project += '''\n\n## Audit 0.7.2 — Teleport closest-to-reticle\n\nIl selettore manuale dei player è stato rimosso. Crouch Teleport mantiene soltanto tre pagine, con Secondary Fire per cambiare pagina e Primary Fire per eseguire. La pagina player condivide il ritmo 4 Hz del reticolo, filtra privacy ON e allinea `TargetInspeksi` al `CalonTargetTeleportasi`, così il nome visibile corrisponde al target effettivo. Il vecchio refresh Teleport a 1 Hz e la regola `19d` di navigazione inversa sono stati eliminati.\n'''
PROJECT.write_text(project, encoding="utf-8")

print(f"patched {NEW_VERSION}: {OLD_BLOB} -> {new_blob}")
