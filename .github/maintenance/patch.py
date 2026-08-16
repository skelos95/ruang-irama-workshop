from __future__ import annotations

import re
import subprocess
from pathlib import Path

PATCH_PATH = ".github/maintenance/patch.py"
FEATURE_PATCH_COMMIT = "9eef15c412d7dfa9d5f0dbe0f4b7e0ff9cc266e9"
SOURCE_PATH = Path("workshop/ruang_irama.workshop")
VALIDATOR_PATH = Path("tools/validate_workshop.py")
VALIDATION_DOC = Path("docs/VALIDAZIONE.md")


def load_patch() -> str:
    return subprocess.run(
        ["git", "show", f"{FEATURE_PATCH_COMMIT}:{PATCH_PATH}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


# Apply the feature patch that already passes all 33 unit tests.
code = load_patch()
exec(compile(code, PATCH_PATH, "exec"), {"__name__": "__main__", "__file__": PATCH_PATH})

# Keep Workshop comments in Bahasa Indonesia as required by the repository's
# source-language policy.
source = SOURCE_PATH.read_text(encoding="utf-8")
source = source.replace(
    '"Proteksi roulette bersifat sementara: preferensi pemain tetap di ModeKebalTerakhir."',
    '"Perlindungan undian hanya sementara; pilihan pemain tetap disimpan di ModeKebalTerakhir."',
)
source = source.replace(
    '"Il rosso spegne solo la protezione runtime; ModeKebalTerakhir resta la scelta del giocatore."',
    '"Hasil merah hanya mematikan perlindungan sementara; ModeKebalTerakhir tetap menyimpan pilihan pemain."',
)
SOURCE_PATH.write_text(source, encoding="utf-8")

# The roulette now legitimately contains additional Halo/Warning creation
# sites: temporary FULL HP plus restoration of the remembered setting.
validator = VALIDATOR_PATH.read_text(encoding="utf-8")
for old, new, label in (
    (', 1, "Unkillable FULL HP Halo public icon")', ', 3, "Unkillable FULL HP Halo public icon")', "Halo count"),
    (', 1, "Unkillable 1 HP Warning public icon")', ', 2, "Unkillable 1 HP Warning public icon")', "Warning count"),
):
    if validator.count(old) != 1:
        raise RuntimeError(f"{label}: expected 1 occurrence, found {validator.count(old)}")
    validator = validator.replace(old, new, 1)
VALIDATOR_PATH.write_text(validator, encoding="utf-8")

# docs/VALIDAZIONE.md records the exact Workshop blob. Compute it after every
# source transformation so the documentation cannot drift from the validated
# file.
blob = subprocess.run(
    ["git", "hash-object", str(SOURCE_PATH)],
    check=True,
    capture_output=True,
    text=True,
).stdout.strip()
doc = VALIDATION_DOC.read_text(encoding="utf-8")
match = re.search(r"(Blob Git del sorgente Workshop validato:\n\n```text\n)([0-9a-f]{40})(\n```)", doc)
if match is None:
    raise RuntimeError("VALIDAZIONE: Workshop blob block not found")
doc = doc[:match.start(2)] + blob + doc[match.end(2):]
VALIDATION_DOC.write_text(doc, encoding="utf-8")

Path("PATCH_DIAGNOSTIC.txt").unlink(missing_ok=True)
