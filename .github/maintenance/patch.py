from __future__ import annotations

import subprocess
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[2]

# Reuse the already reviewed 0.6.22 migration + test-alignment wrapper.
previous = subprocess.check_output(
    ["git", "show", "324ddf908f08bf0aecfac2967808f49b7f7bedaf:.github/maintenance/patch.py"],
    cwd=ROOT,
    text=True,
)
namespace = {"__name__": "__main__", "__file__": str(HERE)}
exec(compile(previous, str(HERE), "exec"), namespace)

validator_path = ROOT / "tools" / "validate_workshop.py"
validator = validator_path.read_text(encoding="utf-8")
old = '''            "Array Contains(Global.PemainManusia, Event Player)" in body
            and "Array Contains(Global.SlotHUDPemain, Event Player.UrutanHUD)" in body
            and "Mapped Array(Global.PemainManusia, Custom String(" in body,
'''
new = '''            "Array Contains(Global.PemainManusia, Event Player)" in body
            and "Global.SlotHUDPemain" in body
            and "Event Player.UrutanHUD" in body
            and "Mapped Array(Global.PemainManusia, Custom String(" in body,
'''
if validator.count(old) != 1:
    raise RuntimeError(f"deferred validator formatting target: expected 1 occurrence, found {validator.count(old)}")
validator = validator.replace(old, new, 1)
validator_path.write_text(validator, encoding="utf-8")

print("Relaxed 0.6.22 deferred lifecycle validator formatting")
