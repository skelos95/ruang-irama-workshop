from __future__ import annotations

import subprocess
from pathlib import Path

PATCH_PATH = ".github/maintenance/patch.py"
BASE_PATCH_COMMIT = "35213fa44c25a5ee226b3b34c2a22d4a8159649e"
VALIDATOR_PATH = Path("tools/validate_workshop.py")


def load_patch() -> str:
    return subprocess.run(
        ["git", "show", f"{BASE_PATCH_COMMIT}:{PATCH_PATH}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


# Apply the already-corrected feature patch (including the rule-18f scoped
# cleanup and menu-lock test correction).
code = load_patch()
exec(compile(code, PATCH_PATH, "exec"), {"__name__": "__main__", "__file__": PATCH_PATH})

# Tighten the two new validators: simply seeing the IsAlive call is not enough,
# because a negative mutation like `Is Alive(...) == False` still contains the
# same function name. Explicitly reject the negative predicate.
validator = VALIDATOR_PATH.read_text(encoding="utf-8")
old_camera = 'checks.require("EntityExists(CurrentArrayElement)" in refresh_code and "IsAlive(CurrentArrayElement)" in refresh_code, "Camera: candidati morti/non esistenti non filtrati")'
new_camera = 'checks.require("EntityExists(CurrentArrayElement)" in refresh_code and "IsAlive(CurrentArrayElement)" in refresh_code and "IsAlive(CurrentArrayElement)==False" not in refresh_code, "Camera: candidati morti/non esistenti non filtrati")'
old_teleport = 'checks.require("EntityExists(CurrentArrayElement)" in refresh_code and "IsAlive(CurrentArrayElement)" in refresh_code, "Teleport: candidati morti/non esistenti non filtrati")'
new_teleport = 'checks.require("EntityExists(CurrentArrayElement)" in refresh_code and "IsAlive(CurrentArrayElement)" in refresh_code and "IsAlive(CurrentArrayElement)==False" not in refresh_code, "Teleport: candidati morti/non esistenti non filtrati")'
for old, new, label in ((old_camera, new_camera, "camera validator"), (old_teleport, new_teleport, "teleport validator")):
    if validator.count(old) != 1:
        raise RuntimeError(f"{label}: expected 1 occurrence, found {validator.count(old)}")
    validator = validator.replace(old, new, 1)
VALIDATOR_PATH.write_text(validator, encoding="utf-8")

Path("PATCH_DIAGNOSTIC.txt").unlink(missing_ok=True)
