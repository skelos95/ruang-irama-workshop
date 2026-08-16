from __future__ import annotations

import subprocess
import traceback
from pathlib import Path

ORIGINAL_COMMIT = "5ef4d51ca85bb8d017fb5c05bd2d1ecfdcf6ad35"
PATCH_PATH = ".github/maintenance/patch.py"


def original_patch() -> str:
    result = subprocess.run(
        ["git", "show", f"{ORIGINAL_COMMIT}:{PATCH_PATH}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


try:
    code = original_patch()
    needle = "luck_rule + luck_rule_end"
    if code.count(needle) != 1:
        raise RuntimeError(f"18e/18f correction: expected 1 occurrence, found {code.count(needle)}")
    code = code.replace(needle, "luck_rule", 1)
    exec(compile(code, PATCH_PATH, "exec"), {"__name__": "__main__", "__file__": PATCH_PATH})
except Exception:
    Path("PATCH_DIAGNOSTIC.txt").write_text(traceback.format_exc(), encoding="utf-8")
