from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"

OLD_BLOB = "3894f19f3ef0c97e0b84f28cb1d4d4baa9fb16ee"


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

# In subroutine 98 this is a direct assignment, not Set Player Variable.
# Therefore it needs six closing parentheses after Current Array Element, not seven.
old_refresh = '''\t\tEvent Player.DaftarTargetTeleportasi = Filtered Array(All Players(All Teams), And(Current Array Element != Event Player,\n\t\t\tAnd(Player Variable(Current Array Element, PrivasiInspeksiAktif) == False, And(Entity Exists(Current Array Element),\n\t\t\tAnd(Has Spawned(Current Array Element), Is Alive(Current Array Element)))))));'''
new_refresh = '''\t\tEvent Player.DaftarTargetTeleportasi = Filtered Array(All Players(All Teams), And(Current Array Element != Event Player,\n\t\t\tAnd(Player Variable(Current Array Element, PrivasiInspeksiAktif) == False, And(Entity Exists(Current Array Element),\n\t\t\tAnd(Has Spawned(Current Array Element), Is Alive(Current Array Element))))));'''
source = replace_exact(source, old_refresh, new_refresh)
SOURCE.write_text(source, encoding="utf-8")
new_blob = git_blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_exact(validator, f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"', f'EXPECTED_SOURCE_BLOB = "{new_blob}"')
old_guards = '''    checks.require(\n        "And(Has Spawned(Current Array Element), Is Alive(Current Array Element)))))));" in source,\n        "filtro Teleport privacy senza parentesi finale",\n    )\n    checks.require(\n        source.count("And(Has Spawned(Current Array Element), Is Alive(Current Array Element)))))));") >= 2,\n        "entrambi i filtri Teleport devono avere la chiusura completa",\n    )\n'''
new_guards = '''    if teleport_global:\n        checks.require(\n            "And(Has Spawned(Current Array Element), Is Alive(Current Array Element)))))));" in teleport_global.body,\n            "filtro Teleport globale senza chiusura Set Player Variable completa",\n        )\n    if teleport_refresh:\n        checks.require(\n            "And(Has Spawned(Current Array Element), Is Alive(Current Array Element))))));" in teleport_refresh.body,\n            "filtro Teleport refresh senza chiusura assegnazione completa",\n        )\n        checks.require(\n            "And(Has Spawned(Current Array Element), Is Alive(Current Array Element)))))));" not in teleport_refresh.body,\n            "filtro Teleport refresh contiene una parentesi finale di troppo",\n        )\n'''
validator = replace_exact(validator, old_guards, new_guards)
VALIDATOR.write_text(validator, encoding="utf-8")

print(f"hotfixed 0.7.2 refresh syntax: {OLD_BLOB} -> {new_blob}")
