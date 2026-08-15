from __future__ import annotations

from pathlib import Path
import subprocess

VALIDATOR = Path("tools/validate_workshop.py")

# The old Menu 5 assertion encoded the exact two-state implementation. Replace
# it with the stable part of the contract; the replayed patch adds a dedicated
# checker for OFF / 1 HP / FULL HP, damage handling and the public Halo.
text = VALIDATOR.read_text(encoding="utf-8")
old = '''    checks.require(
        "Else If(Event Player.HalamanMenu == 5);" in source
        and "If(Is In Spawn Room(Event Player) == True);" in source
        and "Event Player.HalamanMenu = -1;" in source
        and "Unkillable: 1 HP is unavailable in Spawn Room." in source,
        "Kebal: menu 5 non bloccato nella Spawn Room",
    )'''
new = '''    checks.require(
        "Else If(Event Player.HalamanMenu == 5);" in source
        and "Unkillable modes are unavailable in Spawn Room." in source,
        "Kebal: menu 5 non bloccato nella Spawn Room",
    )'''
if old not in text:
    raise SystemExit("legacy composite Spawn Room validator assertion not found")
VALIDATOR.write_text(text.replace(old, new, 1), encoding="utf-8")

script = subprocess.check_output(
    ["git", "show", "4e3a7c57100ead6ed437fed61261054f524f9e82:.github/maintenance/patch.py"],
    text=True,
)
exec(compile(script, "replayed_unkillable_patch.py", "exec"))
