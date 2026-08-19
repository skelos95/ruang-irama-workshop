from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
OLD_BLOB = "b7130b2d9478e3cac2a4934c29dc21f10532d59f"


def blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def one(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"expected one match: {old!r}")
    return text.replace(old, new)


source = SOURCE.read_text(encoding="utf-8")
if blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob")
source = one(
    source,
    "\t\t98: InputMenuDikunci\n",
    "\t\t98: InputMenuDikunci\n"
    "\t\t99: EfekNasib\n"
    "\t\t100: EfekNasibBerakhir\n"
    "\t\t101: DaftarTujuanNasib\n"
    "\t\t102: TujuanNasib\n"
    "\t\t103: ArahNasib\n"
    "\t\t104: PrivasiNasibAktif\n"
    "\t\t105: KategoriTeleportNasib\n"
    "\t\t106: HasilNasibTerkunci\n",
)
SOURCE.write_text(source, encoding="utf-8")
new_blob = blob_sha(source)
validator = VALIDATOR.read_text(encoding="utf-8")
validator = one(validator, f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"', f'EXPECTED_SOURCE_BLOB = "{new_blob}"')
VALIDATOR.write_text(validator, encoding="utf-8")
print(f"Try Your Luck state variables: {OLD_BLOB} -> {new_blob}")
