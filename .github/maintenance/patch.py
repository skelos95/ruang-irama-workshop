from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"

OLD_BLOB = "38929ac945c8571eb2bf4b1f72187f363957a5d1"


def git_blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def replace_exact(text: str, old: str, new: str, expected: int = 1) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"replacement mismatch: expected {expected}, found {count}: {old[:180]!r}")
    return text.replace(old, new)


def rule_bounds(text: str, title: str) -> tuple[int, int]:
    needle = f'rule("{title}")'
    start = text.index(needle)
    next_rule = text.find('\nrule("', start + len(needle))
    return start, len(text) if next_rule < 0 else next_rule


def replace_rule(text: str, title: str, new_block: str) -> str:
    start, end = rule_bounds(text, title)
    return text[:start] + new_block.rstrip() + "\n" + text[end:]


def edit_rule(text: str, title: str, editor) -> str:
    start, end = rule_bounds(text, title)
    block = text[start:end]
    edited = editor(block)
    if edited == block:
        raise RuntimeError(f"rule was not changed: {title}")
    return text[:start] + edited + text[end:]


source = SOURCE.read_text(encoding="utf-8")
if git_blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch a moving target")

# Dedicated handle: Teleport labels must never share TeksDunia with normal Inspection.
source = replace_exact(
    source,
    "\t\t96: TargetTeleportasiTeks\n",
    "\t\t96: TargetTeleportasiTeks\n\t\t97: TeksTeleportasi\n",
)

source = replace_rule(source, "04k - Global-first: Inspeksi dan target teleport terpusat 4 Hz", r'''rule("04k - Global-first: Inspeksi dan target teleport terpusat 4 Hz")
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
		For Global Variable(IndeksPemainGlobal, 0, Count Of(Global.PemainManusia) - 1, 1);
			Global.PemainAktif = Global.PemainManusia[Global.IndeksPemainGlobal];
			If(And(Global.PemainAktif.InspeksiAktif == True, And(Global.PemainAktif.TeleportasiJongkokAktif == False, And(Entity Exists(Global.PemainAktif),
				And(Is Alive(Global.PemainAktif) == True, And(Global.PemainAktif.MenuTerbuka == False, Is Button Held(Global.PemainAktif, Button(Crouch)) == True))))));
				Set Player Variable(Global.PemainAktif, DaftarTargetInspeksi, Filtered Array(All Players(All Teams), And(Current Array Element != Global.PemainAktif,
					And(Entity Exists(Current Array Element), And(Has Spawned(Current Array Element), Is Alive(Current Array Element))))));
				If(Count Of(Global.PemainAktif.DaftarTargetInspeksi) == 0);
					Set Player Variable(Global.PemainAktif, TargetInspeksi, Null);
				Else;
					Set Player Variable(Global.PemainAktif, TargetInspeksi, First Of(Sorted Array(Global.PemainAktif.DaftarTargetInspeksi,
						Angle Between Vectors(Facing Direction Of(Global.PemainAktif), Direction Towards(Eye Position(Global.PemainAktif), Eye Position(Current Array Element))))));
				End;
			End;

			If(And(Global.PemainAktif.TeleportasiJongkokAktif == True, Global.PemainAktif.KursorTeleportasi == 2));
				Set Player Variable(Global.PemainAktif, DaftarTargetTeleportasi, Filtered Array(All Players(All Teams), And(Current Array Element != Global.PemainAktif,
					And(Entity Exists(Current Array Element), And(Is Alive(Current Array Element), Or(Is Dummy Bot(Current Array Element) == True,
					Or(Player Variable(Current Array Element, BotOtomatis) == True, Player Variable(Current Array Element, PrivasiInspeksiAktif) == False)))))));
				If(Count Of(Global.PemainAktif.DaftarTargetTeleportasi) == 0);
					Set Player Variable(Global.PemainAktif, CalonTargetTeleportasi, Null);
				Else;
					Set Player Variable(Global.PemainAktif, CalonTargetTeleportasi, First Of(Sorted Array(Global.PemainAktif.DaftarTargetTeleportasi,
						Angle Between Vectors(Facing Direction Of(Global.PemainAktif), Direction Towards(Eye Position(Global.PemainAktif), Eye Position(Current Array Element))))));
				End;
				If(Global.PemainAktif.TargetTeleportasiTeks != Global.PemainAktif.CalonTargetTeleportasi);
					If(Global.PemainAktif.TeksTeleportasi != Null);
						Destroy In-World Text(Global.PemainAktif.TeksTeleportasi);
					End;
					Set Player Variable(Global.PemainAktif, TeksTeleportasi, Null);
					Set Player Variable(Global.PemainAktif, TargetTeleportasiTeks, Null);
				End;
			Else;
				If(Global.PemainAktif.TeksTeleportasi != Null);
					Destroy In-World Text(Global.PemainAktif.TeksTeleportasi);
				End;
				Set Player Variable(Global.PemainAktif, TeksTeleportasi, Null);
				Set Player Variable(Global.PemainAktif, TargetTeleportasiTeks, Null);
			End;
		End;
		Global.PemainAktif = Null;
		Wait(0.250, Ignore Condition);
		Loop If Condition Is True;
	}
}''')

source = replace_rule(source, "19c - Teleportasi Jongkok: Secondary Fire mengganti tiga halaman", r'''rule("19c - Teleportasi Jongkok: Secondary Fire mengganti tiga halaman")
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
			If(Event Player.TeksTeleportasi != Null);
				Destroy In-World Text(Event Player.TeksTeleportasi);
			End;
			Event Player.TeksTeleportasi = Null;
			Event Player.TargetTeleportasiTeks = Null;
			If(Event Player.PelatNamaDinonaktifkan == True);
				Enable Nameplates(All Players(All Teams), Event Player);
				Event Player.PelatNamaDinonaktifkan = False;
			End;
		Else;
			If(Event Player.TeksDunia != Null);
				Destroy In-World Text(Event Player.TeksDunia);
			End;
			If(Index Of Array Value(Global.PemainManusia, Event Player) >= 0);
				Global.TeksDuniaPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = 0;
			End;
			Event Player.TeksDunia = Null;
			Event Player.TargetInspeksi = Null;
			Event Player.InspeksiAktif = False;
			If(Event Player.TeksTeleportasi != Null);
				Destroy In-World Text(Event Player.TeksTeleportasi);
			End;
			Event Player.TeksTeleportasi = Null;
			Event Player.TargetTeleportasiTeks = Null;
			Call Subroutine(SegarkanTargetTeleportasi);
		End;
	}
}''')

source = replace_rule(source, "19d - Teleportasi Jongkok: Nama target publik mengikuti reticolo", r'''rule("19d - Teleportasi Jongkok: Nama target publik mengikuti reticolo")
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
		Event Player.TeleportasiJongkokAktif == True;
		Event Player.KursorTeleportasi == 2;
		Event Player.TeksTeleportasi == Null;
		Event Player.CalonTargetTeleportasi != Null;
		Is Alive(Event Player) == True;
		Is Button Held(Event Player, Button(Crouch)) == True;
	}

	actions
	{
		Disable Nameplates(All Players(All Teams), Event Player);
		Event Player.PelatNamaDinonaktifkan = True;
		Call Subroutine(SegarkanTargetTeleportasi);
		Abort If(Event Player.CalonTargetTeleportasi == Null);
		Event Player.TargetTeleportasiTeks = Event Player.CalonTargetTeleportasi;
		Create In-World Text(Event Player, Custom String("{0} {1} | {2}",
			Hero Icon String(Is Duplicating(Event Player.TargetTeleportasiTeks) ? Hero Being Duplicated(Event Player.TargetTeleportasiTeks) : Hero Of(Event Player.TargetTeleportasiTeks)),
			Custom String("{0}", Event Player.TargetTeleportasiTeks), Round To Integer(Health(Event Player.TargetTeleportasiTeks), Down)),
			Eye Position(Event Player.TargetTeleportasiTeks) + Vector(0, 0.450, 0), 1.100, Do Not Clip, Visible To Position String and Color,
			Player Variable(Event Player.TargetTeleportasiTeks, Manusia) == True ? Player Variable(Event Player.TargetTeleportasiTeks, WarnaNama) : Color(Orange), Visible Never);
		Event Player.TeksTeleportasi = Last Text ID;
	}
}''')

source = replace_rule(source, "19g - Teleportasi Jongkok: Tutup saat Jongkok dilepas", r'''rule("19g - Teleportasi Jongkok: Tutup saat Jongkok dilepas")
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
		Or(Or(Is Button Held(Event Player, Button(Crouch)) == False, Event Player.MenuTerbuka == True), Or(Has Spawned(Event Player) == False, Is Alive(Event Player) == False)) == True;
	}

	actions
	{
		If(Event Player.HudMenu != Null);
			Destroy HUD Text(Event Player.HudMenu);
		End;
		If(Index Of Array Value(Global.PemainManusia, Event Player) >= 0);
			Global.HudMenuPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = 0;
		End;
		Event Player.HudMenu = Null;
		Event Player.TeleportasiJongkokAktif = False;
		Event Player.PerintahTeleportasi = 0;
		Event Player.DaftarTargetTeleportasi = Empty Array;
		Event Player.CalonTargetTeleportasi = Null;
		If(Event Player.TeksTeleportasi != Null);
			Destroy In-World Text(Event Player.TeksTeleportasi);
		End;
		Event Player.TeksTeleportasi = Null;
		Event Player.TargetTeleportasiTeks = Null;
		Event Player.JenisTeleportasiTerkunci = -1;
		Event Player.TargetTeleportasiTerkunci = Null;
		If(Event Player.PelatNamaDinonaktifkan == True);
			Enable Nameplates(All Players(All Teams), Event Player);
			Event Player.PelatNamaDinonaktifkan = False;
		End;
		If(Event Player.TeksDunia != Null);
			Destroy In-World Text(Event Player.TeksDunia);
		End;
		If(Event Player.TeksDiri != Null);
			Destroy In-World Text(Event Player.TeksDiri);
		End;
		If(Index Of Array Value(Global.PemainManusia, Event Player) >= 0);
			Global.TeksDuniaPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = 0;
			Global.TeksDiriPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = 0;
		End;
		Event Player.TeksDunia = Null;
		Event Player.TeksDiri = Null;
		Event Player.TargetInspeksi = Null;
		Event Player.DaftarTargetInspeksi = Empty Array;
		Event Player.InspeksiAktif = False;
		Allow Button(Event Player, Button(Primary Fire));
		Allow Button(Event Player, Button(Secondary Fire));
		Allow Button(Event Player, Button(Interact));
	}
}''')

# Initialize the dedicated snapshot/handle during normal player setup.
def setup_label(block: str) -> str:
    old = '''\t\tEvent Player.DaftarTargetTeleportasi = Empty Array;\n\t\tEvent Player.CalonTargetTeleportasi = Null;\n\t\tEvent Player.TargetBalasDendamTerkunci = Null;'''
    new = '''\t\tEvent Player.DaftarTargetTeleportasi = Empty Array;\n\t\tEvent Player.CalonTargetTeleportasi = Null;\n\t\tEvent Player.TargetTeleportasiTeks = Null;\n\t\tEvent Player.TeksTeleportasi = Null;\n\t\tEvent Player.TargetBalasDendamTerkunci = Null;'''
    return replace_exact(block, old, new)

source = edit_rule(source, "94 - Subrutin: Siapkan pemain dari ujung rambut sampai variabel", setup_label)

# Leave/team-switch cleanup must destroy the dedicated text before the scratch-Global critical section.
def cleanup_label(block: str) -> str:
    marker = '''\t\tEvent Player.JedaKartuNasib = 0;\n\t\t"Satu yield sebelum bagian kritis; setelah scratch Global dipakai, cleanup harus atomik tanpa Wait."'''
    replacement = '''\t\tEvent Player.JedaKartuNasib = 0;\n\t\tIf(Event Player.TeksTeleportasi != Null);\n\t\t\tDestroy In-World Text(Event Player.TeksTeleportasi);\n\t\tEnd;\n\t\tEvent Player.TeksTeleportasi = Null;\n\t\tEvent Player.TargetTeleportasiTeks = Null;\n\t\t"Satu yield sebelum bagian kritis; setelah scratch Global dipakai, cleanup harus atomik senza Wait."'''
    replacement = replacement.replace("atomik senza Wait", "atomik tanpa Wait")
    return replace_exact(block, marker, replacement)

source = edit_rule(source, "93c - Subrutin: Bersihkan pemain saat keluar atau pindah tim", cleanup_label)

SOURCE.write_text(source, encoding="utf-8")
new_blob = git_blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_exact(validator, f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"', f'EXPECTED_SOURCE_BLOB = "{new_blob}"')
validator = replace_exact(
    validator,
    'for name in ("HalamanMenuTujuan", "HalamanSubmenuPramuat", "TargetTeleportasiTeks"):',
    'for name in ("HalamanMenuTujuan", "HalamanSubmenuPramuat", "TargetTeleportasiTeks", "TeksTeleportasi"):')
validator = replace_exact(
    validator,
    'checks.require("Destroy In-World Text(Event Player.TeksDunia);" in teleport_cycle.body, "uscita pagina 3 non rimuove il target world text")',
    'checks.require("Destroy In-World Text(Event Player.TeksTeleportasi);" in teleport_cycle.body, "uscita pagina 3 non rimuove il target world text dedicato")')
validator = replace_exact(
    validator,
    'checks.require("Event Player.CalonTargetTeleportasi" in teleport_label.body and "Visible To Position String and Color" in teleport_label.body, "19d non rivaluta il target live")',
    'checks.require("Event Player.CalonTargetTeleportasi" in teleport_label.body and "Visible To Position String and Color" in teleport_label.body, "19d non rivaluta il target live")\n        checks.require("Event Player.TeksTeleportasi = Last Text ID;" in teleport_label.body, "19d non salva il world text nell handle dedicato")\n        checks.require("Event Player.TeksDunia" not in teleport_label.body, "19d condivide ancora l handle TeksDunia con Inspection")')
validator = replace_exact(
    validator,
    'checks.require("Destroy In-World Text(Event Player.TeksDunia);" in teleport_close.body, "chiusura Teleport non distrugge il target world text")',
    'checks.require("Destroy In-World Text(Event Player.TeksTeleportasi);" in teleport_close.body, "chiusura Teleport non distrugge il target world text dedicato")')
validator = replace_exact(
    validator,
    'checks.require("Destroy In-World Text(Global.PemainAktif.TeksDunia);" in teleport_global.body, "target label Teleport non viene invalidato al cambio target")',
    'checks.require("Destroy In-World Text(Global.PemainAktif.TeksTeleportasi);" in teleport_global.body, "target label Teleport dedicato non viene invalidato al cambio target")\n        checks.require("Set Player Variable(Global.PemainAktif, TargetTeleportasiTeks, Null);" in teleport_global.body, "04k non forza la ricreazione del label sul nuovo target")')
validator = replace_exact(
    validator,
    'checks.require("Eye Position(Event Player.TargetTeleportasiTeks)" in teleport_label.body, "19d non usa il target label dedicato")',
    'checks.require("Eye Position(Event Player.TargetTeleportasiTeks)" in teleport_label.body, "19d non usa il target label dedicato")\n        checks.require("Event Player.TeksTeleportasi == Null;" in teleport_label.body, "19d non usa l handle dedicato come latch di ricreazione")')
VALIDATOR.write_text(validator, encoding="utf-8")

print(f"fixed 0.7.2 teleport label handle: {OLD_BLOB} -> {new_blob}")
