from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"

OLD_BLOB = "703cd57121cf564654568d286fb559d2388caa7b"


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

old_global = '''\t\t\t\tSet Player Variable(Global.PemainAktif, DaftarTargetTeleportasi, Filtered Array(All Players(All Teams), And(Current Array Element != Global.PemainAktif,\n\t\t\t\t\tAnd(Entity Exists(Current Array Element), And(Is Alive(Current Array Element), Or(Is Dummy Bot(Current Array Element) == True,\n\t\t\t\t\tAnd(Player Variable(Current Array Element, Manusia) == True, Player Variable(Current Array Element, PrivasiInspeksiAktif) == False)))))));'''
new_global = '''\t\t\t\tSet Player Variable(Global.PemainAktif, DaftarTargetTeleportasi, Filtered Array(All Players(All Teams), And(Current Array Element != Global.PemainAktif,\n\t\t\t\t\tAnd(Entity Exists(Current Array Element), And(Is Alive(Current Array Element), Or(Is Dummy Bot(Current Array Element) == True,\n\t\t\t\t\tOr(Player Variable(Current Array Element, BotOtomatis) == True, Player Variable(Current Array Element, PrivasiInspeksiAktif) == False)))))));'''
source = replace_once(source, old_global, new_global, "global teleport eligibility")

old_refresh = '''\t\tEvent Player.DaftarTargetTeleportasi = Filtered Array(All Players(All Teams), And(Current Array Element != Event Player,\n\t\t\tAnd(Entity Exists(Current Array Element), And(Is Alive(Current Array Element), Or(Is Dummy Bot(Current Array Element) == True,\n\t\t\tAnd(Player Variable(Current Array Element, Manusia) == True, Player Variable(Current Array Element, PrivasiInspeksiAktif) == False))))));'''
new_refresh = '''\t\tEvent Player.DaftarTargetTeleportasi = Filtered Array(All Players(All Teams), And(Current Array Element != Event Player,\n\t\t\tAnd(Entity Exists(Current Array Element), And(Is Alive(Current Array Element), Or(Is Dummy Bot(Current Array Element) == True,\n\t\t\tOr(Player Variable(Current Array Element, BotOtomatis) == True, Player Variable(Current Array Element, PrivasiInspeksiAktif) == False))))));'''
source = replace_once(source, old_refresh, new_refresh, "immediate teleport eligibility")

SOURCE.write_text(source, encoding="utf-8")
new_blob = git_blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_once(
    validator,
    f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"',
    f'EXPECTED_SOURCE_BLOB = "{new_blob}"',
    "validator blob",
)
validator = replace_once(
    validator,
    '    dummy_eligibility = "Is Dummy Bot(Current Array Element) == True"\n    human_eligibility = "Player Variable(Current Array Element, Manusia) == True"\n    privacy = "Player Variable(Current Array Element, PrivasiInspeksiAktif) == False"\n',
    '    dummy_eligibility = "Is Dummy Bot(Current Array Element) == True"\n    bot_eligibility = "Player Variable(Current Array Element, BotOtomatis) == True"\n    privacy = "Player Variable(Current Array Element, PrivasiInspeksiAktif) == False"\n',
    "validator eligibility declarations",
)
validator = replace_once(
    validator,
    '        checks.require(dummy_eligibility in teleport_refresh.body and human_eligibility in teleport_refresh.body and privacy in teleport_refresh.body, "Teleport refresh non distingue bot pubblici (dummy) e umani privacy OFF")\n',
    '        checks.require(dummy_eligibility in teleport_refresh.body and bot_eligibility in teleport_refresh.body and privacy in teleport_refresh.body, "Teleport refresh: bot pubblici (dummy/automatici) e player privacy OFF richiesti")\n        checks.require("Player Variable(Current Array Element, Manusia) == True" not in teleport_refresh.body, "Teleport refresh dipende ancora dal classificatore Manusia")\n',
    "validator refresh eligibility",
)
validator = replace_once(
    validator,
    '        checks.require(dummy_eligibility in teleport_global.body and human_eligibility in teleport_global.body and privacy in teleport_global.body, "Teleport globale non distingue bot pubblici (dummy) e umani privacy OFF")\n',
    '        checks.require(dummy_eligibility in teleport_global.body and bot_eligibility in teleport_global.body and privacy in teleport_global.body, "Teleport globale: bot pubblici (dummy/automatici) e player privacy OFF richiesti")\n        checks.require("Player Variable(Current Array Element, Manusia) == True" not in teleport_global.body.split("If(And(Global.PemainAktif.TeleportasiJongkokAktif == True", 1)[-1], "Teleport globale dipende ancora dal classificatore Manusia")\n',
    "validator global eligibility",
)
VALIDATOR.write_text(validator, encoding="utf-8")

print(f"hotfixed 0.7.2 target eligibility: {OLD_BLOB} -> {new_blob}")
