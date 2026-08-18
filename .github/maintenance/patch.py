from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
README = ROOT / "README.md"
PROJECT = ROOT / "docs" / "PROGETTO.md"

OLD_BLOB = "80fd6ea3ae2fc766d36500395955b03d8c7806a4"


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

# Convert every accidental backslash + physical newline inside HUD/menu Custom Strings
# to the intended Workshop newline escape. This removes the visible '\\' glyph without
# flattening the HUD layout.
continuations = source.count("\\\n")
if continuations == 0:
    raise RuntimeError("no HUD backslash-newline sequences found")
source = source.replace("\\\n", "\\n")

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
			If(And(Global.PemainAktif.InspeksiAktif == True, And(Entity Exists(Global.PemainAktif), And(Is Alive(Global.PemainAktif) == True,
				And(Global.PemainAktif.MenuTerbuka == False, Is Button Held(Global.PemainAktif, Button(Crouch)) == True)))));
				If(Or(Global.PemainAktif.TeleportasiJongkokAktif == False, Global.PemainAktif.KursorTeleportasi != 2));
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

			If(And(Global.PemainAktif.TeleportasiJongkokAktif == True, Global.PemainAktif.KursorTeleportasi == 2));
				Set Player Variable(Global.PemainAktif, DaftarTargetTeleportasi, Filtered Array(All Players(All Teams), And(Current Array Element != Global.PemainAktif,
					And(Player Variable(Current Array Element, PrivasiInspeksiAktif) == False, And(Entity Exists(Current Array Element),
					And(Has Spawned(Current Array Element), Is Alive(Current Array Element)))))));
				If(Count Of(Global.PemainAktif.DaftarTargetTeleportasi) == 0);
					Set Player Variable(Global.PemainAktif, CalonTargetTeleportasi, Null);
				Else;
					Set Player Variable(Global.PemainAktif, CalonTargetTeleportasi, First Of(Sorted Array(Global.PemainAktif.DaftarTargetTeleportasi,
						Angle Between Vectors(Facing Direction Of(Global.PemainAktif), Direction Towards(Eye Position(Global.PemainAktif), Eye Position(Current Array Element))))));
				End;
				If(And(Global.PemainAktif.InspeksiAktif == True, Global.PemainAktif.TargetInspeksi != Global.PemainAktif.CalonTargetTeleportasi));
					If(Global.PemainAktif.TeksDunia != Null);
						Destroy In-World Text(Global.PemainAktif.TeksDunia);
					End;
					If(Global.PemainAktif.TeksDiri != Null);
						Destroy In-World Text(Global.PemainAktif.TeksDiri);
					End;
					If(Index Of Array Value(Global.PemainManusia, Global.PemainAktif) >= 0);
						Global.TeksDuniaPemain[Index Of Array Value(Global.PemainManusia, Global.PemainAktif)] = 0;
						Global.TeksDiriPemain[Index Of Array Value(Global.PemainManusia, Global.PemainAktif)] = 0;
					End;
					Set Player Variable(Global.PemainAktif, TeksDunia, Null);
					Set Player Variable(Global.PemainAktif, TeksDiri, Null);
					Set Player Variable(Global.PemainAktif, TargetInspeksi, Null);
					Set Player Variable(Global.PemainAktif, InspeksiAktif, False);
				End;
			End;
		End;
		Global.PemainAktif = Null;
		Wait(0.250, Ignore Condition);
		Loop If Condition Is True;
	}
}''')

SOURCE.write_text(source, encoding="utf-8")
new_blob = git_blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_exact(validator, f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"', f'EXPECTED_SOURCE_BLOB = "{new_blob}"')
anchor = '    interact = find_rule(rules, "10 - Menu:")\n'
guards = '''    checks.require("\\\\\n" not in source, "HUD/menu contiene ancora backslash visuali a fine riga")\n    if teleport_global:\n        checks.require(\n            "If(Or(Global.PemainAktif.TeleportasiJongkokAktif == False, Global.PemainAktif.KursorTeleportasi != 2));" in teleport_global.body,\n            "Inspection generica sovrascrive ancora il target della pagina 3 Teleport",\n        )\n        checks.require(\n            "Global.PemainAktif.TargetInspeksi != Global.PemainAktif.CalonTargetTeleportasi" in teleport_global.body,\n            "pagina 3 Teleport non rileva il cambio target sotto il mirino",\n        )\n        checks.require(\n            "Set Player Variable(Global.PemainAktif, InspeksiAktif, False);" in teleport_global.body\n            and "Destroy In-World Text(Global.PemainAktif.TeksDunia);" in teleport_global.body,\n            "pagina 3 Teleport non forza il refresh del nome quando cambia target",\n        )\n'''
validator = replace_exact(validator, anchor, guards + anchor)
VALIDATOR.write_text(validator, encoding="utf-8")

readme = README.read_text(encoding="utf-8")
readme += f'''\n\n### Hotfix Crouch 0.7.2 — target live e HUD puliti\n\nLa pagina `All Players` non lascia più che l'Inspection generica sovrascriva `TargetInspeksi`. A 4 Hz viene confrontato il target già mostrato con il nuovo `CalonTargetTeleportasi`; quando cambia, il vecchio In-World Text viene distrutto e ricreato sul nuovo player senza richiedere il rilascio di Crouch. Sono inoltre state convertite {continuations} sequenze di continuazione `backslash + newline` in newline Workshop normali, eliminando il simbolo `\\` visibile dagli HUD/menu interessati.\n'''
README.write_text(readme, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
project += f'''\n\n### Hotfix 0.7.2 — reticle live durante Crouch\n\nSu pagina 3 Teleport, `TargetInspeksi` rappresenta ora davvero il target già renderizzato. `04k` calcola `CalonTargetTeleportasi` senza far passare prima l'Inspection generica; se candidato e target mostrato differiscono, distrugge gli handle `TeksDunia/TeksDiri`, azzera `InspeksiAktif` e lascia alla regola 13 la ricreazione immediata sul nuovo target. Il refresh resta a 4 Hz. Rimossi anche {continuations} backslash di continuazione visibili dai Custom String HUD/menu, convertendoli in `\\n`.\n'''
PROJECT.write_text(project, encoding="utf-8")

print(f"hotfixed 0.7.2 crouch live target: {OLD_BLOB} -> {new_blob}; cleaned {continuations} HUD continuations")
