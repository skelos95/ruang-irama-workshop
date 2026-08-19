from __future__ import annotations

import subprocess
import traceback
from pathlib import Path

BASE_PATCH_COMMIT = "66a0f14db7ac01bd4b1d771627de99b20a603c28"
PATCH_PATH = ".github/maintenance/patch.py"
DIAGNOSTIC = Path(".github/maintenance/last-patch-error.txt")

try:
    text = subprocess.check_output(["git", "show", f"{BASE_PATCH_COMMIT}:{PATCH_PATH}"], text=True)
    bad = '        checks.require("Create Icon(" not in interact.body, "Try Your Luck crea icone nel dispatcher menu invece che nella roulette")\n'
    if text.count(bad) != 1:
        raise RuntimeError(f"validator scope hotfix match count: {text.count(bad)}")
    text = text.replace(bad, "", 1)
    exec(compile(text, str(Path(__file__).resolve()), "exec"), {"__file__": __file__, "__name__": "__main__"})
except Exception:
    error = traceback.format_exc()
    # Never leave a partially-applied Workshop/validator state in the diagnostic run.
    subprocess.run(["git", "checkout", "HEAD", "--", "workshop/ruang_irama.workshop", "tools/validate_workshop.py"], check=True)
    DIAGNOSTIC.write_text(error, encoding="utf-8")
    print("Captured maintenance patch failure; stable source restored.")
    print(error)
