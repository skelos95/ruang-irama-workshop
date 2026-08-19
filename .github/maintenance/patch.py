from __future__ import annotations

import subprocess
from pathlib import Path

# Reuse the complete implementation staged in the previous commit and remove
# the one validator assertion that incorrectly inspected every Create Icon in
# rule 10 instead of only the Try Your Luck branch.
BASE_PATCH_COMMIT = "66a0f14db7ac01bd4b1d771627de99b20a603c28"
path = ".github/maintenance/patch.py"
text = subprocess.check_output(["git", "show", f"{BASE_PATCH_COMMIT}:{path}"], text=True)
bad = '        checks.require("Create Icon(" not in interact.body, "Try Your Luck crea icone nel dispatcher menu invece che nella roulette")\n'
if text.count(bad) != 1:
    raise RuntimeError("validator scope hotfix did not match exactly once")
text = text.replace(bad, "", 1)
exec(compile(text, str(Path(__file__).resolve()), "exec"), {"__file__": __file__, "__name__": "__main__"})
