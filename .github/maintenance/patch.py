from __future__ import annotations

from pathlib import Path
import subprocess

VALIDATOR = Path("tools/validate_workshop.py")

# The comprehensive Unkillable patch was already validated by the unit suite;
# only this legacy Spawn Room text assertion was left stale. Fix it in the
# working tree before replaying that exact patch body.
text = VALIDATOR.read_text(encoding="utf-8")
old = 'and "Unkillable: 1 HP is unavailable in Spawn Room." in source,'
new = 'and "Unkillable modes are unavailable in Spawn Room." in source,'
if old not in text:
    raise SystemExit("legacy Spawn Room validator assertion not found")
VALIDATOR.write_text(text.replace(old, new, 1), encoding="utf-8")

script = subprocess.check_output(
    ["git", "show", "4e3a7c57100ead6ed437fed61261054f524f9e82:.github/maintenance/patch.py"],
    text=True,
)
exec(compile(script, "replayed_unkillable_patch.py", "exec"))
