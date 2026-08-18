from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
TESTS = ROOT / "tests" / "test_validate_workshop.py"
README = ROOT / "README.md"
PROJECT = ROOT / "docs" / "PROGETTO.md"

OLD_BLOB = "e9aa5276178c9355f4460dff643d213dd63c78a7"


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


source = SOURCE.read_text(encoding="utf-8")
if git_blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch a moving target")

# The global 4 Hz manager owns candidate selection only. The page-3 world label is a
# separate state-triggered renderer and reevaluates directly from CalonTargetTeleportasi.
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
					And(Entity Exists(Current Array Element), And(Has Spawned(Current Array Element), And(Is Alive(Current Array Element),
					Or(Is Dummy Bot(Current Array Element) == True, Or(Player Variable(Current Array Element, BotOtomatis) == True,
					And(Player Variable(Current Array Element, Manusia) == True, Player Variable(Current Array Element, PrivasiInspeksiAktif) == False)))))))));
				If(Count Of(Global.PemainAktif.DaftarTargetTeleportasi) == 0);
					Set Player Variable(Global.PemainAktif, CalonTargetTeleportasi, Null);
				Else;
					Set Player Variable(Global.PemainAktif, CalonTargetTeleportasi, First Of(Sorted Array(Global.PemainAktif.DaftarTargetTeleportasi,
						Angle Between Vectors(Facing Direction Of(Global.PemainAktif), Direction Towards(Eye Position(Global.PemainAktif), Eye Position(Current Array Element))))));
				End;
			End;
		End;
		Global.PemainAktif = Null;
		Wait(0.250, Ignore Condition);
		Loop If Condition Is True;
	}
}''')

# Generic crouch inspection must never render while the Crouch Teleport overlay is active.
source = replace_rule(source, "13 - Intip Pahlawan: Tampilkan ikon, nama, dan kesehatan saat ini", r'''rule("13 - Intip Pahlawan: Tampilkan ikon, nama, dan kesehatan saat ini")
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
		Event Player.ModeKamera != 2;
		Event Player.InspeksiAktif == False;
		Is Button Held(Event Player, Button(Crouch)) == True;
	}

	actions
	{
		Event Player.InspeksiAktif = True;
		Disable Nameplates(All Players(All Teams), Event Player);
		Event Player.PelatNamaDinonaktifkan = True;
		Call Subroutine(SegarkanTargetInspeksi);
		Create In-World Text(Event Player, Event Player.TargetInspeksi == Null ? Custom String("") : And(Player Variable(Event Player.TargetInspeksi, Manusia) == True, And(
			Player Variable(Event Player.TargetInspeksi, PrivasiInspeksiAktif) == True, Team Of(Event Player.TargetInspeksi) != Team Of(Event Player))) ? Custom String("")
			: Custom String("{0} {1} | {2}", Hero Icon String(Is Duplicating(Event Player.TargetInspeksi) ? Hero Being Duplicated(Event Player.TargetInspeksi) : Hero Of(
			Event Player.TargetInspeksi)), Custom String("{0}", Event Player.TargetInspeksi), Round To Integer(Health(Event Player.TargetInspeksi), Down)), Event Player.TargetInspeksi == Null ? Eye Position(Event Player) : Eye Position(
			Event Player.TargetInspeksi) + Vector(0, 0.450, 0), 1.100, Do Not Clip, Visible To Position String and Color, Event Player.TargetInspeksi == Null
			? Color(White) : Player Variable(Event Player.TargetInspeksi, Manusia) == True ? Player Variable(Event Player.TargetInspeksi, WarnaNama)
			: Color(Orange), Visible Never);
		Event Player.TeksDunia = Last Text ID;
		If(Index Of Array Value(Global.PemainManusia, Event Player) >= 0);
			Global.TeksDuniaPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = Event Player.TeksDunia;
		End;
		Event Player.TeksDiri = Null;
		If(Event Player.ModeKamera == 1);
			Create In-World Text(Event Player, Custom String("{0} {1} | {2}", Hero Icon String(Is Duplicating(Event Player) ? Hero Being Duplicated(
				Event Player) : Hero Of(Event Player)), Custom String("{0}", Event Player), Round To Integer(Health(Event Player), Down)),
				Update Every Frame(Eye Position(Event Player) + Vector(0, 0.450, 0)), 1.100, Do Not Clip, Visible To Position String and Color, Event Player.WarnaNama,
				Visible Never);
			Event Player.TeksDiri = Last Text ID;
			If(Index Of Array Value(Global.PemainManusia, Event Player) >= 0);
				Global.TeksDiriPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = Event Player.TeksDiri;
			End;
		End;
	}
}''')

# Secondary switches pages and removes the dedicated page-3 label immediately when leaving it.
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
			If(Event Player.TeksDunia != Null);
				Destroy In-World Text(Event Player.TeksDunia);
			End;
			If(Index Of Array Value(Global.PemainManusia, Event Player) >= 0);
				Global.TeksDuniaPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = 0;
			End;
			Event Player.TeksDunia = Null;
			If(Event Player.PelatNamaDinonaktifkan == True);
				Enable Nameplates(All Players(All Teams), Event Player);
				Event Player.PelatNamaDinonaktifkan = False;
			End;
		Else;
			Call Subroutine(SegarkanTargetTeleportasi);
		End;
	}
}''')

# Dedicated page-3 label. Re-evaluation follows CalonTargetTeleportasi directly, so the
# world text changes player while Crouch remains held and does not share Inspection state.
teleport_label = r'''rule("19d - Teleportasi Jongkok: Nama target publik mengikuti reticolo")
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
		Event Player.TeksDunia == Null;
		Is Alive(Event Player) == True;
		Is Button Held(Event Player, Button(Crouch)) == True;
	}

	actions
	{
		Disable Nameplates(All Players(All Teams), Event Player);
		Event Player.PelatNamaDinonaktifkan = True;
		Call Subroutine(SegarkanTargetTeleportasi);
		Create In-World Text(Event Player, Event Player.CalonTargetTeleportasi == Null ? Custom String("") : Custom String("{0} {1} | {2}",
			Hero Icon String(Is Duplicating(Event Player.CalonTargetTeleportasi) ? Hero Being Duplicated(Event Player.CalonTargetTeleportasi) : Hero Of(Event Player.CalonTargetTeleportasi)),
			Custom String("{0}", Event Player.CalonTargetTeleportasi), Round To Integer(Health(Event Player.CalonTargetTeleportasi), Down)),
			Event Player.CalonTargetTeleportasi == Null ? Eye Position(Event Player) : Eye Position(Event Player.CalonTargetTeleportasi) + Vector(0, 0.450, 0),
			1.100, Do Not Clip, Visible To Position String and Color, Event Player.CalonTargetTeleportasi == Null ? Color(White)
			: Player Variable(Event Player.CalonTargetTeleportasi, Manusia) == True ? Player Variable(Event Player.CalonTargetTeleportasi, WarnaNama) : Color(Orange), Visible Never);
		Event Player.TeksDunia = Last Text ID;
		If(Index Of Array Value(Global.PemainManusia, Event Player) >= 0);
			Global.TeksDuniaPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = Event Player.TeksDunia;
		End;
	}
}
'''
insert_at = source.index('rule("19e - Teleportasi Jongkok: Primary Fire menjalankan halaman aktif")')
source = source[:insert_at] + teleport_label + "\n" + source[insert_at:]

# Immediate click refresh uses the same eligibility policy as the 4 Hz manager.
source = replace_rule(source, "98 - Subrutin: Cari target teleport publik terdekat dari bidikan", r'''rule("98 - Subrutin: Cari target teleport publik terdekat dari bidikan")
{
	event
	{
		Subroutine;
		SegarkanTargetTeleportasi;
	}

	actions
	{
		Event Player.DaftarTargetTeleportasi = Filtered Array(All Players(All Teams), And(Current Array Element != Event Player,
			And(Entity Exists(Current Array Element), And(Has Spawned(Current Array Element), And(Is Alive(Current Array Element),
			Or(Is Dummy Bot(Current Array Element) == True, Or(Player Variable(Current Array Element, BotOtomatis) == True,
			And(Player Variable(Current Array Element, Manusia) == True, Player Variable(Current Array Element, PrivasiInspeksiAktif) == False))))))));
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
validator = replace_exact(validator, f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"', f'EXPECTED_SOURCE_BLOB = "{new_blob}"')
validator = replace_exact(
    validator,
    '        "19c - Teleportasi Jongkok:", "19e - Teleportasi Jongkok:",\n',
    '        "19c - Teleportasi Jongkok:", "19d - Teleportasi Jongkok:", "19e - Teleportasi Jongkok:",\n',
)
start = validator.index('    teleport_cycle = find_rule(rules, "19c - Teleportasi Jongkok:")')
end = validator.index('    interact = find_rule(rules, "10 - Menu:")', start)
new_checks = '''    teleport_cycle = find_rule(rules, "19c - Teleportasi Jongkok:")\n    teleport_label = find_rule(rules, "19d - Teleportasi Jongkok:")\n    teleport_exec = find_rule(rules, "19e - Teleportasi Jongkok:")\n    teleport_refresh = find_rule(rules, "98 - Subrutin:")\n    teleport_render = find_rule(rules, "91g - Subrutin:")\n    teleport_global = find_rule(rules, "04k - Global-first:")\n    teleport_open = find_rule(rules, "19 - Teleportasi Jongkok:")\n    teleport_close = find_rule(rules, "19g - Teleportasi Jongkok:")\n    inspect_rule = find_rule(rules, "13 - Intip Pahlawan:")\n    checks.require("Event Player.PerintahTeleportasi = 3;" not in source, "Teleport usa ancora il terzo comando legacy")\n    checks.equal(source.count("Event Player.KursorTeleportasi = 0;"), 1, "reset KursorTeleportasi deve restare solo in SiapkanPemain")\n    checks.require((chr(92) + chr(10)) not in source, "HUD/menu contiene ancora backslash visuali a fine riga")\n    if teleport_cycle:\n        checks.require("Event Player.KursorTeleportasi = (Event Player.KursorTeleportasi + 1) % 3;" in teleport_cycle.body, "Teleport non cicla tre pagine con Secondary")\n        checks.require("Destroy In-World Text(Event Player.TeksDunia);" in teleport_cycle.body, "uscita pagina 3 non rimuove il target world text")\n    if teleport_label:\n        checks.equal(event_type(teleport_label), "Ongoing - Each Player", "19d Teleport target label: scheduler")\n        checks.require("Event Player.TeleportasiJongkokAktif == True;" in teleport_label.body and "Event Player.KursorTeleportasi == 2;" in teleport_label.body, "19d non è limitata alla pagina 3")\n        checks.require("Event Player.CalonTargetTeleportasi" in teleport_label.body and "Visible To Position String and Color" in teleport_label.body, "19d non rivaluta il target live")\n        checks.require("Event Player.InspeksiAktif" not in teleport_label.body and "Event Player.TargetInspeksi" not in teleport_label.body, "19d condivide ancora stato Inspection")\n    if teleport_exec:\n        checks.require("Call Subroutine(SegarkanTargetTeleportasi);" in teleport_exec.body, "Primary Teleport non aggiorna il target al click")\n        checks.require("TargetTeleportasiTerkunci = Event Player.CalonTargetTeleportasi;" in teleport_exec.body, "Primary Teleport non blocca il closest-to-reticle")\n    eligibility = "Or(Is Dummy Bot(Current Array Element) == True, Or(Player Variable(Current Array Element, BotOtomatis) == True"\n    privacy = "And(Player Variable(Current Array Element, Manusia) == True, Player Variable(Current Array Element, PrivasiInspeksiAktif) == False)"\n    if teleport_refresh:\n        checks.require("First Of(Sorted Array(Event Player.DaftarTargetTeleportasi" in teleport_refresh.body, "Teleport non usa closest-to-reticle")\n        checks.require(eligibility in teleport_refresh.body and privacy in teleport_refresh.body, "Teleport refresh non distingue bot pubblici e umani privacy OFF")\n    if teleport_global:\n        checks.require("Global.PemainAktif.KursorTeleportasi == 2" in teleport_global.body and "CalonTargetTeleportasi" in teleport_global.body, "target Teleport non è aggiornato globalmente a 4 Hz")\n        checks.require(eligibility in teleport_global.body and privacy in teleport_global.body, "Teleport globale non distingue bot pubblici e umani privacy OFF")\n        checks.require("Destroy In-World Text(Global.PemainAktif.TeksDunia);" not in teleport_global.body, "manager 4 Hz ricrea ancora il world text ad ogni target")\n    if teleport_render:\n        checks.require("Event Player.KursorTeleportasi %= 3;" in teleport_render.body and "ALL PLAYERS" in teleport_render.body, "HUD Teleport non espone tre pagine")\n    if teleport_open:\n        checks.require("Event Player.KursorTeleportasi = 0;" not in teleport_open.body, "apertura Teleport resetta ancora la pagina")\n    if teleport_close:\n        checks.require("Event Player.KursorTeleportasi = 0;" not in teleport_close.body, "chiusura Teleport resetta ancora la pagina")\n        checks.require("Destroy In-World Text(Event Player.TeksDunia);" in teleport_close.body, "chiusura Teleport non distrugge il target world text")\n    if inspect_rule:\n        checks.require("Event Player.TeleportasiJongkokAktif == False;" in inspect_rule.body, "Inspection generica entra ancora nel Teleport")\n        checks.require("SegarkanTargetTeleportasi" not in inspect_rule.body and "CalonTargetTeleportasi" not in inspect_rule.body, "Inspection generica condivide ancora il target Teleport")\n'''
validator = validator[:start] + new_checks + validator[end:]
VALIDATOR.write_text(validator, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
anchor = '    def test_preloaded_submenu_is_required(self) -> None:\n'
extra = '''    def test_teleport_bots_remain_public_targets(self) -> None:\n        start = self.source.index('rule("98 - Subrutin:')\n        pos = self.source.index("Is Dummy Bot(Current Array Element) == True", start)\n        mutated = self.source[:pos] + self.source[pos:].replace("Is Dummy Bot(Current Array Element) == True", "Is Dummy Bot(Current Array Element) == False", 1)\n        self.assertTrue(any("bot pubblici" in error for error in self.errors(mutated)))\n\n    def test_teleport_world_label_is_independent_from_inspection(self) -> None:\n        start = self.source.index('rule("19d - Teleportasi Jongkok:')\n        pos = self.source.index("Event Player.CalonTargetTeleportasi", start)\n        mutated = self.source[:pos] + self.source[pos:].replace("Event Player.CalonTargetTeleportasi", "Event Player.TargetInspeksi", 1)\n        self.assertTrue(any("rivaluta il target live" in error or "stato Inspection" in error for error in self.errors(mutated)))\n\n'''
tests = replace_exact(tests, anchor, extra + anchor)
TESTS.write_text(tests, encoding="utf-8")

readme = README.read_text(encoding="utf-8")
readme += '''\n\n### Hotfix Crouch 0.7.2 — target pubblico dedicato\n\nLa pagina `All Players` non usa più `TargetInspeksi`. `04k` aggiorna soltanto `CalonTargetTeleportasi` a 4 Hz; una regola UI dedicata crea un singolo In-World Text rivalutato su Position/String/Color, che segue direttamente il candidato mentre Crouch resta premuto. Dummy bot e bot automatici sono sempre target pubblici; i player reali sono eleggibili soltanto con Crouch Privacy OFF.\n'''
README.write_text(readme, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
project += '''\n\n### Hotfix 0.7.2 — separazione Inspection / Teleport\n\nLa pagina 3 Teleport è stata separata dall'Inspection generica. `19d` gestisce il world label del candidato e rivaluta direttamente `CalonTargetTeleportasi`; `13` opera solo quando `TeleportasiJongkokAktif == False`. Il filtro target considera validi dummy bot, bot automatici e umani classificati con `PrivasiInspeksiAktif == False`, evitando che una variabile privacy non inizializzata sui bot produca `NO PUBLIC TARGET`.\n'''
PROJECT.write_text(project, encoding="utf-8")

print(f"hotfixed 0.7.2 public reticle targets: {OLD_BLOB} -> {new_blob}")
