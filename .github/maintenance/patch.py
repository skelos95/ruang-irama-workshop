from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"

OLD_BLOB = "7f80a30dd4ab08b082856e4a5c3a2cfd936cb623"


def blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


source = SOURCE.read_text(encoding="utf-8")
if blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch moving target")

old = 'Create In-World Text(All Players(All Teams), Custom String("□"), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), 4.000, Do Not Clip, Visible To Position String and Color, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Visible Never);'
new = 'Create In-World Text(All Players(All Teams), Custom String("□"), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), 8.000, Do Not Clip, Visible To Position String and Color, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Visible Never);'
if source.count(old) != 1:
    raise RuntimeError(f"expected one Try Your Luck square frame, found {source.count(old)}")
source = source.replace(old, new)
SOURCE.write_text(source, encoding="utf-8")

new_blob = blob_sha(source)
validator = VALIDATOR.read_text(encoding="utf-8")
old_pin = f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"'
new_pin = f'EXPECTED_SOURCE_BLOB = "{new_blob}"'
if validator.count(old_pin) != 1:
    raise RuntimeError("validator blob pin mismatch")
validator = validator.replace(old_pin, new_pin)
VALIDATOR.write_text(validator, encoding="utf-8")

print(f"enlarged Try Your Luck square: {OLD_BLOB} -> {new_blob}")
