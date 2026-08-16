from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Reuse the complete 0.6.2 patch including the whitespace normalization.
previous = subprocess.check_output(
    ["git", "show", "d553fb1452e5e4ac06386c8090c8fde24c93f327:.github/maintenance/patch.py"],
    cwd=ROOT,
    text=True,
)
exec(
    compile(previous, "team_switch_0_6_2_clean.py", "exec"),
    {"__name__": "__main__", "__file__": str(ROOT / ".github/maintenance/patch.py")},
)

source_path = ROOT / "workshop/ruang_irama.workshop"
validation_path = ROOT / "docs/VALIDAZIONE.md"

data = source_path.read_bytes().replace(b"\r\n", b"\n")
payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
blob = hashlib.sha1(payload).hexdigest()

validation = validation_path.read_text(encoding="utf-8")
validation, count = re.subn(
    r"(?s)(Blob Git del sorgente Workshop validato:\s*```text\s*)[0-9a-f]{40}(\s*```)",
    rf"\g<1>{blob}\g<2>",
    validation,
    count=1,
)
if count != 1:
    raise RuntimeError("documented Workshop blob not found")
validation_path.write_text(validation, encoding="utf-8")
