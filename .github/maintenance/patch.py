from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"

OLD_BLOB = "476f2b08fed274b308480bd22bcb12bcee6740e8"


def git_blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def replace_exact(text: str, old: str, new: str, expected: int = 1) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"replacement mismatch: expected {expected}, found {count}: {old[:140]!r}")
    return text.replace(old, new)


source = SOURCE.read_text(encoding="utf-8")
if git_blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch a moving target")

# 04k: privacy adds one extra And(...), therefore Set Player Variable needs one extra closing parenthesis.
old_global = '''\t\t\t\tSet Player Variable(Global.PemainAktif, DaftarTargetTeleportasi, Filtered Array(All Players(All Teams), And(Current Array Element != Global.PemainAktif,\n\t\t\t\t\tAnd(Player Variable(Current Array Element, PrivasiInspeksiAktif) == False, And(Entity Exists(Current Array Element),\n\t\t\t\t\tAnd(Has Spawned(Current Array Element), Is Alive(Current Array Element))))));'''
new_global = '''\t\t\t\tSet Player Variable(Global.PemainAktif, DaftarTargetTeleportasi, Filtered Array(All Players(All Teams), And(Current Array Element != Global.PemainAktif,\n\t\t\t\t\tAnd(Player Variable(Current Array Element, PrivasiInspeksiAktif) == False, And(Entity Exists(Current Array Element),\n\t\t\t\t\tAnd(Has Spawned(Current Array Element), Is Alive(Current Array Element)))))));'''
source = replace_exact(source, old_global, new_global)

# 98 uses the same privacy filter and needs the same closing parenthesis.
old_refresh = '''\t\tEvent Player.DaftarTargetTeleportasi = Filtered Array(All Players(All Teams), And(Current Array Element != Event Player,\n\t\t\tAnd(Player Variable(Current Array Element, PrivasiInspeksiAktif) == False, And(Entity Exists(Current Array Element),\n\t\t\tAnd(Has Spawned(Current Array Element), Is Alive(Current Array Element))))));'''
new_refresh = '''\t\tEvent Player.DaftarTargetTeleportasi = Filtered Array(All Players(All Teams), And(Current Array Element != Event Player,\n\t\t\tAnd(Player Variable(Current Array Element, PrivasiInspeksiAktif) == False, And(Entity Exists(Current Array Element),\n\t\t\tAnd(Has Spawned(Current Array Element), Is Alive(Current Array Element)))))));'''
source = replace_exact(source, old_refresh, new_refresh)

SOURCE.write_text(source, encoding="utf-8")
new_blob = git_blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_exact(validator, f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"', f'EXPECTED_SOURCE_BLOB = "{new_blob}"')

# Targeted regression guards for the two expressions that failed the live Overwatch parser.
anchor = '    interact = find_rule(rules, "10 - Menu:")\n'
guards = '''    checks.require(\n        "And(Has Spawned(Current Array Element), Is Alive(Current Array Element)))))));" in source,\n        "filtro Teleport privacy senza parentesi finale",\n    )\n    checks.require(\n        source.count("And(Has Spawned(Current Array Element), Is Alive(Current Array Element)))))));") >= 2,\n        "entrambi i filtri Teleport devono avere la chiusura completa",\n    )\n'''
validator = replace_exact(validator, anchor, guards + anchor)
VALIDATOR.write_text(validator, encoding="utf-8")

print(f"hotfixed 0.7.2 syntax: {OLD_BLOB} -> {new_blob}")
