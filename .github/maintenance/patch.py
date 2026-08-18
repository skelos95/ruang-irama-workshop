from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
TESTS = ROOT / "tests" / "test_validate_workshop.py"

OLD_BLOB = "d7ed31444e7ee214b96b44d81bb7fd76f3c98060"


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


def remove_rule(text: str, title: str) -> str:
    start, end = rule_bounds(text, title)
    return text[:start] + text[end:]


source = SOURCE.read_text(encoding="utf-8")
if git_blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch a moving target")

# No periodic inspection/teleport polling is needed anymore.
source = remove_rule(source, "04k - Global-first: Inspeksi terpusat 4 Hz")

# Normal crouch uses the same public-target eligibility as Teleport and updates only when
# the closest-to-reticle target changes. No Wait, no Loop, no global poller.
source = replace_rule(source, "13 - Intip Pahlawan: Tampilkan ikon, nama, dan kesehatan saat ini", r'''rule("13 - Intip Pahlawan: Nama mengikuti target reticolo tanpa Wait")
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
		Is Alive(Event Player) == True;
		Event Player.MenuTerbuka == False;
		Event Player.TeleportasiJongkokAktif == False;
		Event Player.TeleportasiJongkokDiaktifkan == False;
		Event Player.ModeKamera != 2;
		Is Button Held(Event Player, Button(Crouch)) == True;
		Event Player.TargetInspeksi != First Of(Sorted Array(Filtered Array(All Players(All Teams), And(Current Array Element != Event Player,
			And(Entity Exists(Current Array Element), And(Is Alive(Current Array Element), Or(Is Dummy Bot(Current Array Element) == True,
			Or(Player Variable(Current Array Element, BotOtomatis) == True, Player Variable(Current Array Element, PrivasiInspeksiAktif) == False)))))),
			Angle Between Vectors(Facing Direction Of(Event Player), Direction Towards(Eye Position(Event Player), Eye Position(Current Array Element)))));
	}

	actions
	{
		If(Event Player.InspeksiAktif == False);
			Event Player.InspeksiAktif = True;
			Disable Nameplates(All Players(All Teams), Event Player);
			Event Player.PelatNamaDinonaktifkan = True;
			Event Player.TeksDiri = Null;
			If(Event Player.ModeKamera == 1);
				Create In-World Text(Event Player, Custom String("{0} {1} | {2}", Hero Icon String(Is Duplicating(Event Player) ? Hero Being Duplicated(Event Player) : Hero Of(Event Player)),
					Custom String("{0}", Event Player), Round To Integer(Health(Event Player), Down)), Update Every Frame(Eye Position(Event Player) + Vector(0, 0.450, 0)),
					1.100, Do Not Clip, Visible To Position String and Color, Event Player.WarnaNama, Visible Never);
				Event Player.TeksDiri = Last Text ID;
				If(Index Of Array Value(Global.PemainManusia, Event Player) >= 0);
					Global.TeksDiriPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = Event Player.TeksDiri;
				End;
			End;
		End;
		Call Subroutine(SegarkanTargetInspeksi);
		If(Event Player.TeksDunia != Null);
			Destroy In-World Text(Event Player.TeksDunia);
		End;
		If(Index Of Array Value(Global.PemainManusia, Event Player) >= 0);
			Global.TeksDuniaPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = 0;
		End;
		Event Player.TeksDunia = Null;
		Abort If(Event Player.TargetInspeksi == Null);
		Create In-World Text(Event Player, Custom String("{0} {1} | {2}",
			Hero Icon String(Is Duplicating(Event Player.TargetInspeksi) ? Hero Being Duplicated(Event Player.TargetInspeksi) : Hero Of(Event Player.TargetInspeksi)),
			Custom String("{0}", Event Player.TargetInspeksi), Round To Integer(Health(Event Player.TargetInspeksi), Down)),
			Eye Position(Event Player.TargetInspeksi) + Vector(0, 0.450, 0), 1.100, Do Not Clip, Visible To Position String and Color,
			Player Variable(Event Player.TargetInspeksi, Manusia) == True ? Player Variable(Event Player.TargetInspeksi, WarnaNama) : Color(Orange), Visible Never);
		Event Player.TeksDunia = Last Text ID;
		If(Index Of Array Value(Global.PemainManusia, Event Player) >= 0);
			Global.TeksDuniaPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = Event Player.TeksDunia;
		End;
	}
}''')

# Split target detection from text rendering. The candidate changes first; the renderer keeps
# retrying while snapshot != candidate and only commits the snapshot after Create succeeds.
source = replace_rule(source, "19d - Teleportasi Jongkok: Nama target cambia subito col reticolo", r'''rule("19d0 - Teleportasi Jongkok: Aggiorna target reticolo senza Wait")
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
		Event Player.CalonTargetTeleportasi != First Of(Sorted Array(Filtered Array(All Players(All Teams), And(Current Array Element != Event Player,
			And(Entity Exists(Current Array Element), And(Is Alive(Current Array Element), Or(Is Dummy Bot(Current Array Element) == True,
			Or(Player Variable(Current Array Element, BotOtomatis) == True, Player Variable(Current Array Element, PrivasiInspeksiAktif) == False)))))),
			Angle Between Vectors(Facing Direction Of(Event Player), Direction Towards(Eye Position(Event Player), Eye Position(Current Array Element)))));
	}

	actions
	{
		Call Subroutine(SegarkanTargetTeleportasi);
	}
}

rule("19d - Teleportasi Jongkok: Distruggi e ricrea nome al cambio target")
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
		Event Player.TargetTeleportasiTeks != Event Player.CalonTargetTeleportasi;
	}

	actions
	{
		If(Event Player.TeksTeleportasi != Null);
			Destroy In-World Text(Event Player.TeksTeleportasi);
		End;
		Event Player.TeksTeleportasi = Null;
		If(Event Player.CalonTargetTeleportasi == Null);
			Event Player.TargetTeleportasiTeks = Null;
			Abort;
		End;
		Disable Nameplates(All Players(All Teams), Event Player);
		Event Player.PelatNamaDinonaktifkan = True;
		Create In-World Text(Event Player, Custom String("{0} {1} | {2}",
			Hero Icon String(Is Duplicating(Event Player.CalonTargetTeleportasi) ? Hero Being Duplicated(Event Player.CalonTargetTeleportasi) : Hero Of(Event Player.CalonTargetTeleportasi)),
			Custom String("{0}", Event Player.CalonTargetTeleportasi), Round To Integer(Health(Event Player.CalonTargetTeleportasi), Down)),
			Eye Position(Event Player.CalonTargetTeleportasi) + Vector(0, 0.450, 0), 1.100, Do Not Clip, Visible To Position String and Color,
			Player Variable(Event Player.CalonTargetTeleportasi, Manusia) == True ? Player Variable(Event Player.CalonTargetTeleportasi, WarnaNama) : Color(Orange), Visible Never);
		Event Player.TeksTeleportasi = Last Text ID;
		Event Player.TargetTeleportasiTeks = Event Player.CalonTargetTeleportasi;
	}
}''')

# Normal inspection refresh uses exactly the same public-target filter as Teleport.
source = replace_rule(source, "96 - Subrutin: Cari pemain terdekat dari bidikan", r'''rule("96 - Subrutin: Cari target publik terdekat dari bidikan")
{
	event
	{
		Subroutine;
		SegarkanTargetInspeksi;
	}

	actions
	{
		Event Player.DaftarTargetInspeksi = Filtered Array(All Players(All Teams), And(Current Array Element != Event Player,
			And(Entity Exists(Current Array Element), And(Is Alive(Current Array Element), Or(Is Dummy Bot(Current Array Element) == True,
			Or(Player Variable(Current Array Element, BotOtomatis) == True, Player Variable(Current Array Element, PrivasiInspeksiAktif) == False))))));
		If(Count Of(Event Player.DaftarTargetInspeksi) == 0);
			Event Player.TargetInspeksi = Null;
		Else;
			Event Player.TargetInspeksi = First Of(Sorted Array(Event Player.DaftarTargetInspeksi, Angle Between Vectors(Facing Direction Of(Event Player),
				Direction Towards(Eye Position(Event Player), Eye Position(Current Array Element)))));
		End;
	}
}''')

SOURCE.write_text(source, encoding="utf-8")
new_blob = git_blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_exact(validator, f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"', f'EXPECTED_SOURCE_BLOB = "{new_blob}"')
validator = replace_exact(
    validator,
    '        "19c - Teleportasi Jongkok:", "19d - Teleportasi Jongkok:", "19e - Teleportasi Jongkok:",\n',
    '        "19c - Teleportasi Jongkok:", "19d0 - Teleportasi Jongkok:", "19d - Teleportasi Jongkok:", "19e - Teleportasi Jongkok:",\n',
)
validator = replace_exact(
    validator,
    '    periodic_global = ("04i - Global-first:", "04j - Global-first:", "04k - Global-first:")',
    '    periodic_global = ("04i - Global-first:", "04j - Global-first:")',
)
validator = replace_exact(
    validator,
    '    teleport_label = find_rule(rules, "19d - Teleportasi Jongkok:")\n',
    '    teleport_detector = find_rule(rules, "19d0 - Teleportasi Jongkok:")\n    teleport_label = find_rule(rules, "19d - Teleportasi Jongkok:")\n',
)
validator = replace_exact(
    validator,
    '    teleport_global = find_rule(rules, "04k - Global-first:")\n',
    '    teleport_global = find_rule(rules, "04k - Global-first:")\n    checks.require(teleport_global is None, "04k polling Inspection/Teleport deve essere rimosso")\n',
)
old_label_checks = '''    if teleport_label:\n        checks.equal(event_type(teleport_label), "Ongoing - Each Player", "19d Teleport target label: scheduler")\n        checks.require("Event Player.TeleportasiJongkokAktif == True;" in teleport_label.body and "Event Player.KursorTeleportasi == 2;" in teleport_label.body, "19d non è limitata alla pagina 3")\n        checks.require("Event Player.CalonTargetTeleportasi" in teleport_label.body and "Visible To Position String and Color" in teleport_label.body, "19d non rivaluta il target live")\n        checks.require("Event Player.TeksTeleportasi = Last Text ID;" in teleport_label.body, "19d non salva il world text nell handle dedicato")\n        checks.require("Event Player.TeksDunia" not in teleport_label.body, "19d condivide ancora l handle TeksDunia con Inspection")\n        checks.require("Event Player.InspeksiAktif" not in teleport_label.body and "Event Player.TargetInspeksi" not in teleport_label.body, "19d condivide ancora stato Inspection")\n'''
new_label_checks = '''    if teleport_detector:\n        checks.equal(event_type(teleport_detector), "Ongoing - Each Player", "19d0 Teleport detector: scheduler")\n        checks.require("Event Player.CalonTargetTeleportasi != First Of(Sorted Array(Filtered Array(All Players(All Teams)" in teleport_detector.body, "19d0 non rileva direttamente il cambio closest-to-reticle")\n        checks.require("Call Subroutine(SegarkanTargetTeleportasi);" in teleport_detector.body, "19d0 non aggiorna il candidate Teleport")\n        checks.require("Wait(" not in teleport_detector.body and "Loop If Condition Is True;" not in teleport_detector.body, "19d0 non deve usare Wait o Loop")\n    if teleport_label:\n        checks.equal(event_type(teleport_label), "Ongoing - Each Player", "19d Teleport target label: scheduler")\n        checks.require("Event Player.TeleportasiJongkokAktif == True;" in teleport_label.body and "Event Player.KursorTeleportasi == 2;" in teleport_label.body, "19d non è limitata alla pagina 3")\n        checks.require("Event Player.TargetTeleportasiTeks != Event Player.CalonTargetTeleportasi;" in teleport_label.body, "19d non resta armata finché snapshot e candidate differiscono")\n        checks.require("Destroy In-World Text(Event Player.TeksTeleportasi);" in teleport_label.body and "Create In-World Text(" in teleport_label.body, "19d non distrugge e ricrea il nome")\n        checks.require("Event Player.TeksTeleportasi = Last Text ID;" in teleport_label.body, "19d non salva il world text nell handle dedicato")\n        checks.require(teleport_label.body.index("Event Player.TeksTeleportasi = Last Text ID;") < teleport_label.body.index("Event Player.TargetTeleportasiTeks = Event Player.CalonTargetTeleportasi;"), "19d aggiorna lo snapshot prima di creare il testo")\n        checks.require("Wait(" not in teleport_label.body and "Loop If Condition Is True;" not in teleport_label.body, "19d non deve usare Wait o Loop")\n        checks.require("Event Player.TeksDunia" not in teleport_label.body, "19d condivide ancora l handle TeksDunia con Inspection")\n'''
validator = replace_exact(validator, old_label_checks, new_label_checks)
validator = replace_exact(
    validator,
    '''    if teleport_global:\n        checks.require("DaftarTargetTeleportasi" not in teleport_global.body and "CalonTargetTeleportasi" not in teleport_global.body, "04k gestisce ancora il target Teleport con polling")\n''',
    '',
)
validator = replace_exact(
    validator,
    '''    if teleport_global:\n        checks.require("TeksTeleportasi" not in teleport_global.body and "TargetTeleportasiTeks" not in teleport_global.body, "04k gestisce ancora il refresh del nome Teleport")\n''',
    '',
)
old_tail_label = '''    if teleport_label:\n        checks.require("Event Player.TargetTeleportasiTeks = Event Player.CalonTargetTeleportasi;" in teleport_label.body, "19d non rivaluta il target live")\n        checks.require("Eye Position(Event Player.TargetTeleportasiTeks)" in teleport_label.body, "19d non usa il target label dedicato")\n        checks.require("Event Player.TargetTeleportasiTeks != First Of(Sorted Array(Filtered Array(All Players(All Teams)" in teleport_label.body, "19d non rileva direttamente il cambio closest-to-reticle")\n        checks.require(dummy_eligibility in teleport_label.body and bot_eligibility in teleport_label.body and privacy in teleport_label.body, "19d target live: bot pubblici e player privacy OFF richiesti")\n        checks.require("Destroy In-World Text(Event Player.TeksTeleportasi);" in teleport_label.body and "Create In-World Text(" in teleport_label.body, "19d non distrugge e ricrea subito il nome al cambio target")\n        checks.require("Wait(" not in teleport_label.body and "Loop If Condition Is True;" not in teleport_label.body, "19d target live non deve usare Wait o Loop")\n'''
new_tail_label = '''    if teleport_detector:\n        checks.require(dummy_eligibility in teleport_detector.body and bot_eligibility in teleport_detector.body and privacy in teleport_detector.body, "19d0 target live: bot pubblici e player privacy OFF richiesti")\n    if inspect_rule:\n        checks.require("Event Player.TargetInspeksi != First Of(Sorted Array(Filtered Array(All Players(All Teams)" in inspect_rule.body, "Crouch normale non rileva direttamente il cambio closest-to-reticle")\n        checks.require("Destroy In-World Text(Event Player.TeksDunia);" in inspect_rule.body and "Create In-World Text(" in inspect_rule.body, "Crouch normale non distrugge e ricrea il nome")\n        checks.require("Wait(" not in inspect_rule.body and "Loop If Condition Is True;" not in inspect_rule.body, "Crouch normale non deve usare Wait o Loop")\n        checks.require(dummy_eligibility in inspect_rule.body and bot_eligibility in inspect_rule.body and privacy in inspect_rule.body, "Crouch normale non usa lo stesso filtro pubblico del Teleport")\n'''
validator = replace_exact(validator, old_tail_label, new_tail_label)
VALIDATOR.write_text(validator, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
tests = replace_exact(
    tests,
    '        for prefix in ("04i - Global-first:", "04j - Global-first:", "04k - Global-first:"):',
    '        for prefix in ("04i - Global-first:", "04j - Global-first:"):')
TESTS.write_text(tests, encoding="utf-8")

print(f"event-driven crouch labels: {OLD_BLOB} -> {new_blob}")
