from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"

OLD_BLOB = "49a8d2d9c07680061b9d8d76931a1723fdf2ec01"


def git_blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected 1 match, found {count}")
    return text.replace(old, new, 1)


source = SOURCE.read_text(encoding="utf-8")
if git_blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch a moving target")

# 1) Generic inspection must never compete with Crouch Teleport on the first frame.
source = replace_once(
    source,
    "\t\tEvent Player.TeleportasiJongkokAktif == False;\n\t\tEvent Player.ModeKamera != 2;",
    "\t\tEvent Player.TeleportasiJongkokAktif == False;\n\t\tEvent Player.TeleportasiJongkokDiaktifkan == False;\n\t\tEvent Player.ModeKamera != 2;",
    "inspection first-frame guard",
)

# 2) Dummy bots are valid live targets without Has Spawned/privacy player variables.
old_global = '''\t\t\t\tSet Player Variable(Global.PemainAktif, DaftarTargetTeleportasi, Filtered Array(All Players(All Teams), And(Current Array Element != Global.PemainAktif,\n\t\t\t\t\tAnd(Entity Exists(Current Array Element), And(Has Spawned(Current Array Element), And(Is Alive(Current Array Element),\n\t\t\t\t\tOr(Is Dummy Bot(Current Array Element) == True, Or(Player Variable(Current Array Element, BotOtomatis) == True,\n\t\t\t\t\tAnd(Player Variable(Current Array Element, Manusia) == True, Player Variable(Current Array Element, PrivasiInspeksiAktif) == False)))))))));'''
new_global = '''\t\t\t\tSet Player Variable(Global.PemainAktif, DaftarTargetTeleportasi, Filtered Array(All Players(All Teams), And(Current Array Element != Global.PemainAktif,\n\t\t\t\t\tAnd(Entity Exists(Current Array Element), And(Is Alive(Current Array Element), Or(Is Dummy Bot(Current Array Element) == True,\n\t\t\t\t\tAnd(Player Variable(Current Array Element, Manusia) == True, Player Variable(Current Array Element, PrivasiInspeksiAktif) == False)))))));'''
source = replace_once(source, old_global, new_global, "global teleport eligibility")

old_refresh = '''\t\tEvent Player.DaftarTargetTeleportasi = Filtered Array(All Players(All Teams), And(Current Array Element != Event Player,\n\t\t\tAnd(Entity Exists(Current Array Element), And(Has Spawned(Current Array Element), And(Is Alive(Current Array Element),\n\t\t\tOr(Is Dummy Bot(Current Array Element) == True, Or(Player Variable(Current Array Element, BotOtomatis) == True,\n\t\t\tAnd(Player Variable(Current Array Element, Manusia) == True, Player Variable(Current Array Element, PrivasiInspeksiAktif) == False))))))));'''
new_refresh = '''\t\tEvent Player.DaftarTargetTeleportasi = Filtered Array(All Players(All Teams), And(Current Array Element != Event Player,\n\t\t\tAnd(Entity Exists(Current Array Element), And(Is Alive(Current Array Element), Or(Is Dummy Bot(Current Array Element) == True,\n\t\t\tAnd(Player Variable(Current Array Element, Manusia) == True, Player Variable(Current Array Element, PrivasiInspeksiAktif) == False))))));'''
source = replace_once(source, old_refresh, new_refresh, "immediate teleport eligibility")

# 3) Entering page 3 clears any stale generic-inspection handle before 19d creates its dedicated label.
old_page3 = '''\t\tElse;\n\t\t\tCall Subroutine(SegarkanTargetTeleportasi);\n\t\tEnd;'''
new_page3 = '''\t\tElse;\n\t\t\tIf(Event Player.TeksDunia != Null);\n\t\t\t\tDestroy In-World Text(Event Player.TeksDunia);\n\t\t\tEnd;\n\t\t\tIf(Index Of Array Value(Global.PemainManusia, Event Player) >= 0);\n\t\t\t\tGlobal.TeksDuniaPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = 0;\n\t\t\tEnd;\n\t\t\tEvent Player.TeksDunia = Null;\n\t\t\tEvent Player.TargetInspeksi = Null;\n\t\t\tEvent Player.InspeksiAktif = False;\n\t\t\tCall Subroutine(SegarkanTargetTeleportasi);\n\t\tEnd;'''
source = replace_once(source, old_page3, new_page3, "page 3 cleanup")

SOURCE.write_text(source, encoding="utf-8")
new_blob = git_blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_once(
    validator,
    f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"',
    f'EXPECTED_SOURCE_BLOB = "{new_blob}"',
    "validator blob",
)

# Replace only the old eligibility-validation section with simple multiline-safe checks.
start = validator.find('    eligibility = "Or(Is Dummy Bot(Current Array Element)')
end = validator.find('    if teleport_render:', start)
if start < 0 or end < 0:
    raise RuntimeError("validator teleport eligibility block not found")
new_checks = '''    dummy_eligibility = "Is Dummy Bot(Current Array Element) == True"\n    human_eligibility = "Player Variable(Current Array Element, Manusia) == True"\n    privacy = "Player Variable(Current Array Element, PrivasiInspeksiAktif) == False"\n    if teleport_refresh:\n        checks.require("First Of(Sorted Array(Event Player.DaftarTargetTeleportasi" in teleport_refresh.body, "Teleport non usa closest-to-reticle")\n        checks.require(dummy_eligibility in teleport_refresh.body and human_eligibility in teleport_refresh.body and privacy in teleport_refresh.body, "Teleport refresh non distingue dummy pubblici e umani privacy OFF")\n        checks.require("Has Spawned(Current Array Element)" not in teleport_refresh.body, "Teleport refresh esclude dummy tramite Has Spawned")\n    if teleport_global:\n        checks.require("Global.PemainAktif.KursorTeleportasi == 2" in teleport_global.body and "CalonTargetTeleportasi" in teleport_global.body, "target Teleport non è aggiornato globalmente a 4 Hz")\n        checks.require(dummy_eligibility in teleport_global.body and human_eligibility in teleport_global.body and privacy in teleport_global.body, "Teleport globale non distingue dummy pubblici e umani privacy OFF")\n        checks.require("Has Spawned(Current Array Element)" not in teleport_global.body.split("If(And(Global.PemainAktif.TeleportasiJongkokAktif == True", 1)[-1], "Teleport globale esclude dummy tramite Has Spawned")\n'''
validator = validator[:start] + new_checks + validator[end:]

# Enforce the first-frame separation without touching other validator sections.
needle = '        checks.require("Event Player.TeleportasiJongkokAktif == False;" in inspect_rule.body, "Inspection generica entra ancora nel Teleport")\n'
if needle in validator and "primo frame Crouch" not in validator:
    validator = validator.replace(
        needle,
        needle + '        checks.require("Event Player.TeleportasiJongkokDiaktifkan == False;" in inspect_rule.body, "Inspection generica può vincere il primo frame Crouch")\n',
        1,
    )

VALIDATOR.write_text(validator, encoding="utf-8")
print(f"hotfixed 0.7.2 minimal crouch target: {OLD_BLOB} -> {new_blob}")
