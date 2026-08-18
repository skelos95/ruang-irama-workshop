from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"

OLD_BLOB = "13d77d875f9d5eff3f1bcd982b77052752e35fa2"


def git_blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def replace_exact(text: str, old: str, new: str, expected: int = 1) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"replacement mismatch: expected {expected}, found {count}: {old[:180]!r}")
    return text.replace(old, new)


source = SOURCE.read_text(encoding="utf-8")
if git_blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch a moving target")

# The Arcade menu does not use Crouch as an input. Keep physical crouching available while
# menu-only actions remain isolated by MenuTerbuka == False in normal Inspection/Teleport.
source = replace_exact(
    source,
    "\t\t\tDisallow Button(Event Player, Button(Crouch));\n",
    "",
)

SOURCE.write_text(source, encoding="utf-8")
new_blob = git_blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_exact(
    validator,
    f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"',
    f'EXPECTED_SOURCE_BLOB = "{new_blob}"',
)
validator = replace_exact(
    validator,
    '''    if menu_toggle:\n        checks.require("Wait(0.500, Abort When False);" in menu_toggle.body, "hold Melee 0,5 s assente")\n''',
    '''    if menu_toggle:\n        checks.require("Wait(0.500, Abort When False);" in menu_toggle.body, "hold Melee 0,5 s assente")\n        checks.require("Disallow Button(Event Player, Button(Crouch));" not in menu_toggle.body, "Menu Arcade non deve bloccare Crouch")\n''',
)
validator = replace_exact(
    validator,
    '''    if teleport_open:\n        checks.require("Event Player.KursorTeleportasi = 0;" not in teleport_open.body, "apertura Teleport resetta ancora la pagina")\n''',
    '''    if teleport_open:\n        checks.require("Event Player.KursorTeleportasi = 0;" not in teleport_open.body, "apertura Teleport resetta ancora la pagina")\n        checks.require("Event Player.MenuTerbuka == False;" in teleport_open.body, "Crouch Teleport deve restare disattivato mentre il Menu Arcade è aperto")\n''',
)
validator = replace_exact(
    validator,
    '''    if inspect_rule:\n        checks.require("Event Player.TeleportasiJongkokAktif == False;" in inspect_rule.body, "Inspection generica entra ancora nel Teleport")\n''',
    '''    if inspect_rule:\n        checks.require("Event Player.MenuTerbuka == False;" in inspect_rule.body, "Crouch Inspection deve restare disattivata mentre il Menu Arcade è aperto")\n        checks.require("Event Player.TeleportasiJongkokAktif == False;" in inspect_rule.body, "Inspection generica entra ancora nel Teleport")\n''',
)
VALIDATOR.write_text(validator, encoding="utf-8")

print(f"allowed crouch during menu: {OLD_BLOB} -> {new_blob}")
