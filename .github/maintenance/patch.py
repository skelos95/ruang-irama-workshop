from __future__ import annotations

import subprocess
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[2]
BACKUP_REF = "backup/main-0.6.23-before-rebuild"
FILES = (
    "workshop/ruang_irama.workshop",
    "tools/validate_workshop.py",
    "tests/test_validate_workshop.py",
    "README.md",
    "docs/PROGETTO.md",
    "docs/TEST.md",
    "docs/VALIDAZIONE.md",
    "VERSION",
)

# Fetch the safety branch explicitly; do not depend on the broken recent main metadata.
subprocess.run(
    ["git", "fetch", "origin", f"{BACKUP_REF}:refs/remotes/origin/{BACKUP_REF}"],
    cwd=ROOT,
    check=True,
)

for relative in FILES:
    data = subprocess.check_output(
        ["git", "show", f"refs/remotes/origin/{BACKUP_REF}:{relative}"],
        cwd=ROOT,
    )
    target = ROOT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)

print("Restored exact validated CHILL 0.6.23 files from safety branch")
