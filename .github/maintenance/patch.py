from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"

OLD_BLOB = "4fce3ac2585e5d6d5091b9037e7c434fd047d981"


def git_blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def replace_exact(text: str, old: str, new: str, expected: int = 1) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"replacement mismatch: expected {expected}, found {count}: {old[:200]!r}")
    return text.replace(old, new)


def rule_bounds(text: str, title: str) -> tuple[int, int]:
    needle = f'rule("{title}")'
    start = text.index(needle)
    next_rule = text.find('\nrule("', start + len(needle))
    return start, len(text) if next_rule < 0 else next_rule


def replace_rule(text: str, title: str, new_block: str) -> str:
    start, end = rule_bounds(text, title)
    return text[:start] + new_block.rstrip() + "\n" + text[end:]


source = SOURCE.read_text(encoding="utf-8")
if git_blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch a moving target")

# 04k remains the global Inspection scheduler only. Teleport targeting is now fully event-driven in 19d.
source = replace_rule(source, "04k - Global-first: Inspeksi dan target teleport terpusat 4 Hz", r'''rule("04k - Global-first: Inspeksi terpusat 4 Hz")
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
		End;
		Global.PemainAktif = Null;
		Wait(0.250, Ignore Condition);
		Loop If Condition Is True;
	}
}''')

# No Wait/Loop: the condition itself compares the current closest public target with the label snapshot.
# When the reticle crosses to another target, the rule fires immediately and rebuilds the label.
source = replace_rule(source, "19d - Teleportasi Jongkok: Nama target publik mengikuti reticolo", r'''rule("19d - Teleportasi Jongkok: Nama target cambia subito col reticolo")
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
		Is Alive(Event Player) == True;
		Is Button Held(Event Player, Button(Crouch)) == True;
		Event Player.TargetTeleportasiTeks != First Of(Sorted Array(Filtered Array(All Players(All Teams), And(Current Array Element != Event Player, And(Entity Exists(Current Array Element), And(Is Alive(Current Array Element), Or(Is Dummy Bot(Current Array Element) == True, Or(Player Variable(Current Array Element, BotOtomatis) == True, Player Variable(Current Array Element, PrivasiInspeksiAktif) == False)))))), Angle Between Vectors(Facing Direction Of(Event Player), Direction Towards(Eye Position(Event Player), Eye Position(Current Array Element)))));
	}

	actions
	{
		Call Subroutine(SegarkanTargetTeleportasi);
		If(Event Player.TeksTeleportasi != Null);
			Destroy In-World Text(Event Player.TeksTeleportasi);
		End;
		Event Player.TeksTeleportasi = Null;
		Event Player.TargetTeleportasiTeks = Event Player.CalonTargetTeleportasi;
		If(Event Player.TargetTeleportasiTeks == Null);
			Abort;
		End;
		Disable Nameplates(All Players(All Teams), Event Player);
		Event Player.PelatNamaDinonaktifkan = True;
		Create In-World Text(Event Player, Custom String("{0} {1} | {2}",
			Hero Icon String(Is Duplicating(Event Player.TargetTeleportasiTeks) ? Hero Being Duplicated(Event Player.TargetTeleportasiTeks) : Hero Of(Event Player.TargetTeleportasiTeks)),
			Custom String("{0}", Event Player.TargetTeleportasiTeks), Round To Integer(Health(Event Player.TargetTeleportasiTeks), Down)),
			Eye Position(Event Player.TargetTeleportasiTeks) + Vector(0, 0.450, 0), 1.100, Do Not Clip, Visible To Position String and Color,
			Player Variable(Event Player.TargetTeleportasiTeks, Manusia) == True ? Player Variable(Event Player.TargetTeleportasiTeks, WarnaNama) : Color(Orange), Visible Never);
		Event Player.TeksTeleportasi = Last Text ID;
	}
}''')

SOURCE.write_text(source, encoding="utf-8")
new_blob = git_blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_exact(validator, f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"', f'EXPECTED_SOURCE_BLOB = "{new_blob}"')

old_global_checks = '''    if teleport_global:\n        checks.require("Global.PemainAktif.KursorTeleportasi == 2" in teleport_global.body and "CalonTargetTeleportasi" in teleport_global.body, "target Teleport non è aggiornato globalmente a 4 Hz")\n        checks.require(dummy_eligibility in teleport_global.body and bot_eligibility in teleport_global.body and privacy in teleport_global.body, "Teleport globale: bot pubblici (dummy/automatici) e player privacy OFF richiesti")\n        checks.require("Player Variable(Current Array Element, Manusia) == True" not in teleport_global.body.split("If(And(Global.PemainAktif.TeleportasiJongkokAktif == True", 1)[-1], "Teleport globale dipende ancora dal classificatore Manusia")\n        checks.require("Has Spawned(Current Array Element)" not in teleport_global.body.split("If(And(Global.PemainAktif.TeleportasiJongkokAktif == True", 1)[-1], "Teleport globale esclude dummy tramite Has Spawned")\n'''
new_global_checks = '''    if teleport_global:\n        checks.require("DaftarTargetTeleportasi" not in teleport_global.body and "CalonTargetTeleportasi" not in teleport_global.body, "04k gestisce ancora il target Teleport con polling")\n'''
validator = replace_exact(validator, old_global_checks, new_global_checks)

old_label_global = '''    if teleport_global:\n        checks.require("TargetTeleportasiTeks != Global.PemainAktif.CalonTargetTeleportasi" in teleport_global.body, "target label Teleport non rileva il cambio sotto il mirino")\n        checks.require("Destroy In-World Text(Global.PemainAktif.TeksTeleportasi);" in teleport_global.body, "target label Teleport dedicato non viene invalidato al cambio target")\n        checks.require("Set Player Variable(Global.PemainAktif, TargetTeleportasiTeks, Null);" in teleport_global.body, "04k non forza la ricreazione del label sul nuovo target")\n'''
new_label_global = '''    if teleport_global:\n        checks.require("TeksTeleportasi" not in teleport_global.body and "TargetTeleportasiTeks" not in teleport_global.body, "04k gestisce ancora il refresh del nome Teleport")\n'''
validator = replace_exact(validator, old_label_global, new_label_global)

old_label_checks = '''    if teleport_label:\n        checks.require("Event Player.TargetTeleportasiTeks = Event Player.CalonTargetTeleportasi;" in teleport_label.body, "19d non fotografa il target corrente")\n        checks.require("Eye Position(Event Player.TargetTeleportasiTeks)" in teleport_label.body, "19d non usa il target label dedicato")\n        checks.require("Event Player.TeksTeleportasi == Null;" in teleport_label.body, "19d non usa l handle dedicato come latch di ricreazione")\n'''
new_label_checks = '''    if teleport_label:\n        checks.require("Event Player.TargetTeleportasiTeks = Event Player.CalonTargetTeleportasi;" in teleport_label.body, "19d non rivaluta il target live")\n        checks.require("Eye Position(Event Player.TargetTeleportasiTeks)" in teleport_label.body, "19d non usa il target label dedicato")\n        checks.require("Event Player.TargetTeleportasiTeks != First Of(Sorted Array(Filtered Array(All Players(All Teams)" in teleport_label.body, "19d non rileva direttamente il cambio closest-to-reticle")\n        checks.require(dummy_eligibility in teleport_label.body and bot_eligibility in teleport_label.body and privacy in teleport_label.body, "19d target live: bot pubblici e player privacy OFF richiesti")\n        checks.require("Destroy In-World Text(Event Player.TeksTeleportasi);" in teleport_label.body and "Create In-World Text(" in teleport_label.body, "19d non distrugge e ricrea subito il nome al cambio target")\n        checks.require("Wait(" not in teleport_label.body and "Loop If Condition Is True;" not in teleport_label.body, "19d target live non deve usare Wait o Loop")\n'''
validator = replace_exact(validator, old_label_checks, new_label_checks)

VALIDATOR.write_text(validator, encoding="utf-8")
print(f"event-driven teleport label: {OLD_BLOB} -> {new_blob}")
