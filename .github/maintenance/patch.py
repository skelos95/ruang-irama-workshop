from __future__ import annotations

import subprocess
from pathlib import Path

# Riusa la migrazione 0.6.15 già verificata nei due tentativi precedenti,
# poi corregge esclusivamente le ultime due assunzioni legacy del validatore.
ROOT = Path(__file__).resolve().parents[2]
BASE_COMMIT = "a7dcd4269f83579f181890a70489294e1ca8cba3"
base_patch = subprocess.check_output(
    ["git", "show", f"{BASE_COMMIT}:.github/maintenance/patch.py"],
    cwd=ROOT,
    text=True,
)
exec(compile(base_patch, f"{BASE_COMMIT}:patch.py", "exec"), {"__file__": str(Path(__file__).resolve()), "__name__": "__main__"})

validator_path = ROOT / "tools" / "validate_workshop.py"
validator = validator_path.read_text(encoding="utf-8")

# L'audit lifecycle deve osservare la vera registrazione umano in 02, non la nuova regola HUD 02b.
old_lifecycle = '''    classification = [rule for rule in rules if rule.name.startswith("02b - HUD Pemain:")]
    checks.equal(len(classification), 1, "audit lifecycle: una sola registrazione roster")
    if classification:
        body = mask_strings(classification[0].body)
        guard = body.find("Abort If(Array Contains(Global.PemainManusia, Event Player));")
        append = body.find("Global.PemainManusia = Append To Array(Global.PemainManusia, Event Player);")
        checks.require(0 <= guard < append, "audit lifecycle: append roster senza guardia anti-duplicato")
'''
new_lifecycle = '''    classification = [rule for rule in rules if rule.name.startswith("02 - Pemain:")]
    checks.equal(len(classification), 1, "audit lifecycle: una sola registrazione roster")
    if classification:
        body = mask_strings(classification[0].body)
        guard = body.find("Abort If(Array Contains(Global.PemainManusia, Event Player));")
        append = body.find("Global.PemainManusia = Append To Array(Global.PemainManusia, Event Player);")
        checks.require(0 <= guard < append, "audit lifecycle: append roster senza guardia anti-duplicato")
'''
if validator.count(old_lifecycle) != 1:
    raise RuntimeError("audit lifecycle 02/02b marker not found exactly once")
validator = validator.replace(old_lifecycle, new_lifecycle, 1)

# Il nuovo HUD sinistro non viene più appended dopo la creazione: il placeholder roster viene sostituito per indice.
old_diag = '''            "Global.HudKiriPemain = Append To Array",
            "Global.DiagnostikPerforma == True",
'''
new_diag = '''            "Global.HudKiriPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = Event Player.HudKiri;",
            "Global.DiagnostikPerforma == True",
'''
if validator.count(old_diag) != 1:
    raise RuntimeError("diagnostic left HUD legacy marker not found exactly once")
validator = validator.replace(old_diag, new_diag, 1)

validator_path.write_text(validator, encoding="utf-8")
print("Finished CHILL 0.6.15 validator migration for zero-wait HUD architecture")
