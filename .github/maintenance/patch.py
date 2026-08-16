from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE_COMMIT = "0027b6a645e5400bcc66b2e76816cad3780ac271"
base_patch = subprocess.check_output(
    ["git", "show", f"{BASE_COMMIT}:.github/maintenance/patch.py"],
    cwd=ROOT,
    text=True,
)

old = '''src = once(
    src,
    "\\t\\tGlobal.PersiapanDilewati = False;\\n",
    "\\t\\tGlobal.PersiapanDilewati = False;\\n\\t\\tGlobal.ModeMulaiDiminta = False;\\n",
    "initial start latch",
)
'''
new = '''src = once(
    src,
    "\\t\\tGlobal.MulaiUlangSudahDiminta = False;\\n\\t\\tGlobal.RGBFase = 0;\\n",
    "\\t\\tGlobal.MulaiUlangSudahDiminta = False;\\n\\t\\tGlobal.ModeMulaiDiminta = False;\\n\\t\\tGlobal.RGBFase = 0;\\n",
    "initial start latch",
)
'''
if base_patch.count(old) != 1:
    raise RuntimeError("base patch initial start latch block not found exactly once")
base_patch = base_patch.replace(old, new, 1)
exec(compile(base_patch, f"{BASE_COMMIT}:patch.py", "exec"), {"__file__": str(Path(__file__).resolve()), "__name__": "__main__"})
