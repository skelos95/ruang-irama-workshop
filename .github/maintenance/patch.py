from __future__ import annotations

import subprocess
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[2]

# Re-run the original reviewed 0.6.23 maintenance patch from its clean queue commit.
original = subprocess.check_output(
    ["git", "show", "446214196424a01ed8f795a22e5037dce876a02c:.github/maintenance/patch.py"],
    cwd=ROOT,
    text=True,
)
namespace = {"__name__": "__main__", "__file__": str(HERE)}
exec(compile(original, str(HERE), "exec"), namespace)

print("Retriggered clean CHILL 0.6.23 maintenance patch")
