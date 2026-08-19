from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
OLD_BLOB = "4848ec9a689ee9ab2d9e6f7ee9c1dc61e4131c3c"


def blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def replace_exact(text: str, old: str, new: str, expected: int = 1) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"replacement mismatch: expected {expected}, found {count}: {old[:180]!r}")
    return text.replace(old, new)


def rule_bounds(text: str, title: str) -> tuple[int, int]:
    needle = f'rule("{title}")'
    start = text.index(needle)
    nxt = text.find('\nrule("', start + len(needle))
    return start, len(text) if nxt < 0 else nxt


def edit_rule(text: str, title: str, editor) -> str:
    start, end = rule_bounds(text, title)
    block = text[start:end]
    changed = editor(block)
    if changed == block:
        raise RuntimeError(f"rule unchanged: {title}")
    return text[:start] + changed + text[end:]


source = SOURCE.read_text(encoding="utf-8")
if blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob")

# Dedicated state for Crouch-held menu input capture.
source = replace_exact(source, "\t\t97: TeksTeleportasi\n", "\t\t97: TeksTeleportasi\n\t\t98: InputMenuDikunci\n")

# Opening the menu no longer disables hero controls permanently.
def menu_open(block: str) -> str:
    for line in (
        "\t\t\tDisallow Button(Event Player, Button(Primary Fire));\n",
        "\t\t\tDisallow Button(Event Player, Button(Secondary Fire));\n",
        "\t\t\tDisallow Button(Event Player, Button(Interact));\n",
        "\t\t\tDisallow Button(Event Player, Button(Reload));\n",
        "\t\t\tDisallow Button(Event Player, Button(Ability 1));\n",
        "\t\t\tDisallow Button(Event Player, Button(Ability 2));\n",
        "\t\t\tDisallow Button(Event Player, Button(Ultimate));\n",
    ):
        block = replace_exact(block, line, "")
    return block

source = edit_rule(source, "05 - Menu: Tahan serangan jarak dekat 0,5 detik untuk buka atau tutup", menu_open)

# Dispatcher listens to menu inputs only while Crouch is held.
def dispatcher(block: str) -> str:
    return replace_exact(
        block,
        "\t\tEvent Player.MenuTerbuka == True;\n\t\tEvent Player.PerintahMenu == 0;",
        "\t\tEvent Player.MenuTerbuka == True;\n\t\tIs Button Held(Event Player, Button(Crouch)) == True;\n\t\tEvent Player.PerintahMenu == 0;",
    )

source = edit_rule(source, "05c - Menu: Pengatur masukan dengan prioritas tetap", dispatcher)

menu_lock_rules = r'''
rule("05e - Menu: Crouch mengunci input hero hanya saat navigasi")
{
	event
	{
		Ongoing - Each Player;
		All;
		All;
	}

	conditions
	{
		Event Player.Manusia == True;
		Event Player.MenuTerbuka == True;
		Event Player.InputMenuDikunci == False;
		Is Button Held(Event Player, Button(Crouch)) == True;
	}

	actions
	{
		Event Player.InputMenuDikunci = True;
		Disallow Button(Event Player, Button(Primary Fire));
		Disallow Button(Event Player, Button(Secondary Fire));
		Disallow Button(Event Player, Button(Interact));
		Disallow Button(Event Player, Button(Reload));
		Disallow Button(Event Player, Button(Ability 1));
		Disallow Button(Event Player, Button(Ability 2));
		Disallow Button(Event Player, Button(Ultimate));
	}
}

rule("05f - Menu: Rilascia Crouch e restituisci subito gli input hero")
{
	event
	{
		Ongoing - Each Player;
		All;
		All;
	}

	conditions
	{
		Event Player.InputMenuDikunci == True;
		Or(Event Player.MenuTerbuka == False, Is Button Held(Event Player, Button(Crouch)) == False) == True;
	}

	actions
	{
		Allow Button(Event Player, Button(Primary Fire));
		Allow Button(Event Player, Button(Secondary Fire));
		Allow Button(Event Player, Button(Interact));
		Allow Button(Event Player, Button(Reload));
		Allow Button(Event Player, Button(Ability 1));
		Allow Button(Event Player, Button(Ability 2));
		Allow Button(Event Player, Button(Ultimate));
		Event Player.InputMenuDikunci = False;
		Event Player.PerintahMenu = 0;
	}
}

'''
source = source[:source.index('rule("06 - Menu:')] + menu_lock_rules + source[source.index('rule("06 - Menu:'):]

# Player setup and lifecycle always start unlocked.
def setup(block: str) -> str:
    return replace_exact(block, "\t\tEvent Player.TeksTeleportasi = Null;\n", "\t\tEvent Player.TeksTeleportasi = Null;\n\t\tEvent Player.InputMenuDikunci = False;\n")
source = edit_rule(source, "94 - Subrutin: Siapkan pemain dari ujung rambut sampai variabel", setup)


def quiet(block: str) -> str:
    return replace_exact(block, "\t\tEvent Player.PerintahMenu = 0;\n", "\t\tEvent Player.PerintahMenu = 0;\n\t\tEvent Player.InputMenuDikunci = False;\n", 1)
source = edit_rule(source, "93b2 - Subrutin: Tenangkan trigger sebelum cleanup", quiet)


def cleanup(block: str) -> str:
    return replace_exact(block, "\t\tEvent Player.MenuTerbuka = False;\n\t\tEvent Player.HudPemainDibuat = False;", "\t\tEvent Player.MenuTerbuka = False;\n\t\tEvent Player.InputMenuDikunci = False;\n\t\tEvent Player.HudPemainDibuat = False;")
source = edit_rule(source, "93c - Subrutin: Bersihkan pemain saat keluar atau pindah tim", cleanup)

SOURCE.write_text(source, encoding="utf-8")
new_blob = blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_exact(validator, f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"', f'EXPECTED_SOURCE_BLOB = "{new_blob}"')
validator = replace_exact(
    validator,
    'for name in ("HalamanMenuTujuan", "HalamanSubmenuPramuat", "TargetTeleportasiTeks", "TeksTeleportasi"): ',
    'for name in ("HalamanMenuTujuan", "HalamanSubmenuPramuat", "TargetTeleportasiTeks", "TeksTeleportasi", "InputMenuDikunci"): ',
)
validator = replace_exact(
    validator,
    '"05b - Menu:", "05c - Menu:", "05d - Menu:", "06 - Menu:", "07 - Menu:", "08 - Menu 0:", "09 - Menu 0:",',
    '"05b - Menu:", "05c - Menu:", "05d - Menu:", "05e - Menu:", "05f - Menu:", "06 - Menu:", "07 - Menu:", "08 - Menu 0:", "09 - Menu 0:",',
)
old_menu_guard = '''    if menu_toggle:\n        checks.require("Wait(0.500, Abort When False);" in menu_toggle.body, "hold Melee 0,5 s assente")\n        checks.require("Disallow Button(Event Player, Button(Crouch));" not in menu_toggle.body, "Menu Arcade non deve bloccare Crouch")\n'''
new_menu_guard = '''    if menu_toggle:\n        checks.require("Wait(0.500, Abort When False);" in menu_toggle.body, "hold Melee 0,5 s assente")\n        checks.require("Disallow Button(Event Player, Button(Crouch));" not in menu_toggle.body and "Disallow Button(Event Player, Button(Jump));" not in menu_toggle.body, "Menu Arcade non deve bloccare Crouch o Jump")\n        for button in ("Primary Fire", "Secondary Fire", "Interact", "Reload", "Ability 1", "Ability 2", "Ultimate"):\n            checks.require(f"Disallow Button(Event Player, Button({button}));" not in menu_toggle.body, f"Menu aperto blocca permanentemente {button}")\n    menu_dispatch = find_rule(rules, "05c - Menu:")\n    menu_lock = find_rule(rules, "05e - Menu:")\n    menu_unlock = find_rule(rules, "05f - Menu:")\n    if menu_dispatch:\n        checks.require("Is Button Held(Event Player, Button(Crouch)) == True;" in menu_dispatch.body, "dispatcher menu non richiede Crouch")\n    if menu_lock:\n        checks.require("Disallow Button(Event Player, Button(Crouch));" not in menu_lock.body and "Disallow Button(Event Player, Button(Jump));" not in menu_lock.body, "navigazione menu blocca Crouch o Jump")\n        for button in ("Primary Fire", "Secondary Fire", "Interact", "Reload", "Ability 1", "Ability 2", "Ultimate"):\n            checks.require(f"Disallow Button(Event Player, Button({button}));" in menu_lock.body, f"Crouch menu non cattura {button}")\n    if menu_unlock:\n        checks.require("Is Button Held(Event Player, Button(Crouch)) == False" in menu_unlock.body, "rilascio Crouch non restituisce gli input hero")\n        for button in ("Primary Fire", "Secondary Fire", "Interact", "Reload", "Ability 1", "Ability 2", "Ultimate"):\n            checks.require(f"Allow Button(Event Player, Button({button}));" in menu_unlock.body, f"rilascio Crouch non restituisce {button}")\n'''
validator = replace_exact(validator, old_menu_guard, new_menu_guard)
VALIDATOR.write_text(validator, encoding="utf-8")

print(f"crouch menu controls: {OLD_BLOB} -> {new_blob}")
