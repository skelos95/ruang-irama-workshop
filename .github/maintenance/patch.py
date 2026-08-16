from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE_COMMIT = "5cf5cc3b27bba31c05b924731e52419d57a7fd59"
base_patch = subprocess.check_output(
    ["git", "show", f"{BASE_COMMIT}:.github/maintenance/patch.py"],
    cwd=ROOT,
    text=True,
)
base_patch = base_patch.replace(
    'HUD pemain dibuat sekali pada keadaan spawn yang stabil.',
    'HUD pemain dibuat sekali pada keadaan muncul yang stabil.',
)
exec(compile(base_patch, f"{BASE_COMMIT}:patch.py", "exec"), {"__file__": str(Path(__file__).resolve()), "__name__": "__main__"})
