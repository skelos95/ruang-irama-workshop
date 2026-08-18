from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"

OLD_BLOB = "b57e518637bc052d7b497d9d698022b8e30b4b82"


def git_blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def replace_exact(text: str, old: str, new: str, expected: int = 1) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"replacement mismatch: expected {expected}, found {count}: {old[:180]!r}")
    return text.replace(old, new)


source = SOURCE.read_text(encoding="utf-8")
if git_blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch a moving target")

old_self_label = '''\t\tIf(Event Player.InspeksiAktif == False);\n\t\t\tEvent Player.InspeksiAktif = True;\n\t\t\tDisable Nameplates(All Players(All Teams), Event Player);\n\t\t\tEvent Player.PelatNamaDinonaktifkan = True;\n\t\t\tEvent Player.TeksDiri = Null;\n\t\t\tIf(Event Player.ModeKamera == 1);\n\t\t\t\tCreate In-World Text(Event Player, Custom String("{0} {1} | {2}", Hero Icon String(Is Duplicating(Event Player) ? Hero Being Duplicated(Event Player) : Hero Of(Event Player)),\n\t\t\t\t\tCustom String("{0}", Event Player), Round To Integer(Health(Event Player), Down)), Update Every Frame(Eye Position(Event Player) + Vector(0, 0.450, 0)),\n\t\t\t\t\t1.100, Do Not Clip, Visible To Position String and Color, Event Player.WarnaNama, Visible Never);\n\t\t\t\tEvent Player.TeksDiri = Last Text ID;\n\t\t\t\tIf(Index Of Array Value(Global.PemainManusia, Event Player) >= 0);\n\t\t\t\t\tGlobal.TeksDiriPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = Event Player.TeksDiri;\n\t\t\t\tEnd;\n\t\t\tEnd;\n\t\tEnd;'''

new_self_label = '''\t\tIf(Event Player.InspeksiAktif == False);\n\t\t\tEvent Player.InspeksiAktif = True;\n\t\t\tDisable Nameplates(All Players(All Teams), Event Player);\n\t\t\tEvent Player.PelatNamaDinonaktifkan = True;\n\t\t\tIf(Event Player.TeksDiri != Null);\n\t\t\t\tDestroy In-World Text(Event Player.TeksDiri);\n\t\t\tEnd;\n\t\t\tIf(Index Of Array Value(Global.PemainManusia, Event Player) >= 0);\n\t\t\t\tGlobal.TeksDiriPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = 0;\n\t\t\tEnd;\n\t\t\tEvent Player.TeksDiri = Null;\n\t\tEnd;'''

source = replace_exact(source, old_self_label, new_self_label)
SOURCE.write_text(source, encoding="utf-8")
new_blob = git_blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_exact(validator, f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"', f'EXPECTED_SOURCE_BLOB = "{new_blob}"')
anchor = '''    if inspect_rule:\n        checks.require("Event Player.TeleportasiJongkokAktif == False;" in inspect_rule.body, "Inspection generica entra ancora nel Teleport")\n'''
replacement = '''    if inspect_rule:\n        checks.require("Event Player.TeleportasiJongkokAktif == False;" in inspect_rule.body, "Inspection generica entra ancora nel Teleport")\n        checks.require("Event Player.TeksDiri = Last Text ID;" not in inspect_rule.body, "Crouch normale mostra ancora il proprio nome")\n        checks.require("Destroy In-World Text(Event Player.TeksDiri);" in inspect_rule.body, "Crouch normale non pulisce un eventuale nome personale residuo")\n'''
validator = replace_exact(validator, anchor, replacement)
VALIDATOR.write_text(validator, encoding="utf-8")

print(f"hid own crouch label: {OLD_BLOB} -> {new_blob}")
