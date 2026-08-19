from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"

OLD_BLOB = "690f0a39954976b03ecbac37bb894c7833153900"


def blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def one(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one match, found {count}: {old[:180]!r}")
    return text.replace(old, new, 1)


source = SOURCE.read_text(encoding="utf-8")
if blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch moving target")

old_accel = '''\t\tElse If(Event Player.EfekNasib == 8);\n\t\t\tEvent Player.ArahNasib = Direction From Angles(Random Real(-180, 180), Random Real(-45, 45));\n\t\t\tSet Move Speed(Event Player, 1000);\n\t\t\tStart Accelerating(Event Player, Event Player.ArahNasib, 50, 25, To World, None);\n\t\t\tEvent Player.EfekNasibBerakhir = Total Time Elapsed + 5;\n\t\t\tSmall Message(Event Player, Custom String("TRY YOUR LUCK: RANDOM ACCELERATION — 5s"));\n'''
new_accel = '''\t\tElse If(Event Player.EfekNasib == 8);\n\t\t\tEvent Player.ArahNasib = Facing Direction Of(Event Player);\n\t\t\tSet Move Speed(Event Player, 1000);\n\t\t\tStart Accelerating(Event Player, Facing Direction Of(Event Player), 50, 25, To World, Direction Rate and Max Speed);\n\t\t\tEvent Player.EfekNasibBerakhir = Total Time Elapsed + 5;\n\t\t\tSmall Message(Event Player, Custom String("TRY YOUR LUCK: AIM-STEERED ACCELERATION — 5s"));\n'''
source = one(source, old_accel, new_accel)
SOURCE.write_text(source, encoding="utf-8")
new_blob = blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = one(validator, f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"', f'EXPECTED_SOURCE_BLOB = "{new_blob}"')
validator = one(
    validator,
    '            "Start Accelerating(Event Player, Event Player.ArahNasib, 50, 25, To World, None);",\n',
    '            "Start Accelerating(Event Player, Facing Direction Of(Event Player), 50, 25, To World, Direction Rate and Max Speed);",\n',
)
anchor = '        checks.require("Start Forcing Player Position(" not in luck.body, "Try Your Luck non deve forzare la posizione")\n'
guard = anchor + '        checks.require("Direction From Angles(Random Real(-180, 180), Random Real(-45, 45))" not in luck.body, "Accelerazione Try Your Luck non deve usare una direzione casuale")\n        checks.require("AIM-STEERED ACCELERATION — 5s" in luck.body, "Accelerazione Try Your Luck non è etichettata come guidata dalla mira")\n'
validator = one(validator, anchor, guard)
VALIDATOR.write_text(validator, encoding="utf-8")

print(f"patched Workshop blob: {new_blob}")
