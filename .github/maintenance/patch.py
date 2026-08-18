from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"

OLD_BLOB = "e0d251683ae898177678ab6535e37ac5bc1c0d8c"


def blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


source = SOURCE.read_text(encoding="utf-8")
if blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch moving target")

old = 'Custom String("□"), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), 2.600, Do Not Clip'
new = 'Custom String("□"), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), 4.000, Do Not Clip'
if source.count(old) != 1:
    raise RuntimeError(f"expected one Try Your Luck square scale, found {source.count(old)}")
source = source.replace(old, new)
SOURCE.write_text(source, encoding="utf-8")
new_blob = blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
old_pin = f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"'
new_pin = f'EXPECTED_SOURCE_BLOB = "{new_blob}"'
if validator.count(old_pin) != 1:
    raise RuntimeError("validator blob pin mismatch")
validator = validator.replace(old_pin, new_pin)

anchor = '    checks.require("Set Move Speed(Event Player, 0);" in source, "Try Your Luck rosso non blocca la velocità")\n'
guard = '    checks.require(\'Custom String("□"), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), 4.000, Do Not Clip\' in source, "Try Your Luck card frame non usa la scala 4.000")\n'
if anchor not in validator:
    raise RuntimeError("validator Try Your Luck anchor missing")
validator = validator.replace(anchor, anchor + guard, 1)
VALIDATOR.write_text(validator, encoding="utf-8")

print(f"enlarged Try Your Luck card frame: {OLD_BLOB} -> {new_blob}")
