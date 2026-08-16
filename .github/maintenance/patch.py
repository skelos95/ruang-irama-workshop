from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
PROJECT = ROOT / "docs" / "PROGETTO.md"
VALIDATION = ROOT / "docs" / "VALIDAZIONE.md"
README = ROOT / "README.md"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one occurrence, found {count}")
    return text.replace(old, new, 1)


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    return hashlib.sha1(payload).hexdigest()


source = SOURCE.read_text(encoding="utf-8")
source = replace_once(
    source,
    'Custom String("\\n \\nโหวตสูงสุด: {0} - {1} โหวต", Global.LeaderVoto, Global.MaxVoti)',
    'Custom String("\\n \\nดาวสายชิล: {0}", Global.LeaderVoto)',
    "Thai chill leader HUD",
)
source = replace_once(
    source,
    'Custom String("\\n \\nPALING BANYAK DIPILIH: {0} - {1} VOTE", Global.LeaderVoto, Global.MaxVoti)',
    'Custom String("\\n \\nBINTANG CHILL: {0}", Global.LeaderVoto)',
    "Indonesian chill leader HUD",
)
source = replace_once(
    source,
    'Custom String("\\n \\nMOST VOTED: {0} - {1} VOTES", Global.LeaderVoto, Global.MaxVoti)',
    'Custom String("\\n \\nCHILL STAR: {0}", Global.LeaderVoto)',
    "English chill leader HUD",
)
SOURCE.write_text(source, encoding="utf-8")

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_once(
    validator,
    '    checks.require("MOST VOTED:" in source and "PALING BANYAK DIPILIH:" in source and "โหวตสูงสุด:" in source, "Vote: HUD leader assente")',
    '    checks.require("CHILL STAR:" in source and "BINTANG CHILL:" in source and "ดาวสายชิล:" in source, "Vote: HUD Chill Star assente")\n'
    '    checks.require("MOST VOTED:" not in source and "PALING BANYAK DIPILIH:" not in source and "โหวตสูงสุด:" not in source, "Vote: vecchio testo competitivo ancora presente")\n'
    '    checks.require(\'Custom String("\\\\n \\\\nCHILL STAR: {0}", Global.LeaderVoto)\' in source and \'Custom String("\\\\n \\\\nBINTANG CHILL: {0}", Global.LeaderVoto)\' in source and \'Custom String("\\\\n \\\\nดาวสายชิล: {0}", Global.LeaderVoto)\' in source, "Vote: HUD leader mostra ancora il conteggio voti")',
    "vote HUD validator",
)
VALIDATOR.write_text(validator, encoding="utf-8")

for path in (PROJECT, README):
    text = path.read_text(encoding="utf-8")
    text = text.replace("MOST VOTED", "CHILL STAR")
    text = text.replace("Most Voted", "Chill Star")
    text = text.replace("most voted", "Chill Star")
    text = text.replace("numero di voti", "numero di voti (visibile solo nel Menu 11)") if "numero di voti (visibile solo nel Menu 11)" not in text else text
    path.write_text(text, encoding="utf-8")

validation = VALIDATION.read_text(encoding="utf-8")
validation += "\n- Vote HUD: il leader unico viene mostrato come `CHILL STAR` / `BINTANG CHILL` / `ดาวสายชิล`, senza numero voti; i conteggi restano esclusivamente nel Menu 11;\n"
new_blob = git_blob_sha(SOURCE)
validation, count = re.subn(
    r"(?s)(Blob Git del sorgente Workshop validato:\s*```text\s*)[0-9a-f]{40}(\s*```)",
    rf"\g<1>{new_blob}\g<2>",
    validation,
    count=1,
)
if count != 1:
    raise RuntimeError("validation blob not found")
VALIDATION.write_text(validation, encoding="utf-8")
