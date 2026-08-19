from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"

OLD_BLOB = "f08a3199b8b700fe49016a7509f0e75c604b71cc"


def blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def one(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one match, found {count}: {old[:180]!r}")
    return text.replace(old, new, 1)


def rule_bounds(text: str, title: str) -> tuple[int, int]:
    needle = f'rule("{title}")'
    start = text.index(needle)
    nxt = text.find('\nrule("', start + len(needle))
    return start, len(text) if nxt < 0 else nxt


def edit_rule(text: str, title: str, editor) -> str:
    start, end = rule_bounds(text, title)
    block = text[start:end]
    new = editor(block)
    if new == block:
        raise RuntimeError(f"rule unchanged: {title}")
    return text[:start] + new + text[end:]


source = SOURCE.read_text(encoding="utf-8")
if blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch moving target")

# ---------------------------------------------------------------------------
# Persistent HUD hints: Crouch also navigates menus; Interact toggles camera.
# Keep all bindings dynamic so remapped controls remain correct.
# ---------------------------------------------------------------------------
source = one(
    source,
    '"Hold {0}: inspect hero + HP", Input Binding String(Button(Crouch)))',
    '"Hold {0}: inspect hero + HP / navigate menus", Input Binding String(Button(Crouch)))',
)
source = one(
    source,
    '"Tahan {0}: cek pahlawan + HP", Input Binding String(Button(Crouch)))',
    '"Tahan {0}: cek pahlawan + HP / navigasi menu", Input Binding String(Button(Crouch)))',
)
source = one(
    source,
    '"กด {0} ค้าง: ดูฮีโร่ + HP", Input Binding String(Button(Crouch)))',
    '"กด {0} ค้าง: ดูฮีโร่ + HP / นำทางเมนู", Input Binding String(Button(Crouch)))',
)
source = one(
    source,
    '"Hold {0} 0.5 sec: Arcade Menu", Input Binding String(Button(Melee)))',
    '"Hold {0} 0.5s: Arcade Menu | {1} 0.5s: Camera", Input Binding String(Button(Melee)), Input Binding String(Button(Interact)))',
)
source = one(
    source,
    '"Tahan {0} 0,5 dtk: Menu Arcade", Input Binding String(Button(Melee)))',
    '"Tahan {0} 0,5dtk: Menu Arcade | {1} 0,5dtk: Kamera", Input Binding String(Button(Melee)), Input Binding String(Button(Interact)))',
)
source = one(
    source,
    '"กด {0} ค้าง 0.5 วิ: เมนูอาร์เคด", Input Binding String(Button(Melee)))',
    '"กด {0} 0.5วิ: เมนูอาร์เคด | {1} 0.5วิ: กล้อง", Input Binding String(Button(Melee)), Input Binding String(Button(Interact)))',
)

# ---------------------------------------------------------------------------
# Camera toggle: Interact works while Arcade Menu is open as long as Crouch is
# NOT held. When Crouch is held, the validated menu lock still owns Interact.
# ---------------------------------------------------------------------------
def edit_camera(block: str) -> str:
    block = one(
        block,
        'rule("12c - Kamera: Tahan Interact setengah detik untuk beralih di luar menu")',
        'rule("12c - Kamera: Tahan Interact setengah detik untuk beralih")',
    )
    block = one(block, "\t\tEvent Player.MenuTerbuka == False;\n", "")
    return block

source = edit_rule(source, "12c - Kamera: Tahan Interact setengah detik untuk beralih di luar menu", edit_camera)

# ---------------------------------------------------------------------------
# Try Your Luck: unique reticle icons, no Knocked Down for floor fall, and
# abort Skull immediately so its common tail cannot reopen the menu twice.
# ---------------------------------------------------------------------------
def edit_luck(block: str) -> str:
    block = one(
        block,
        "Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Halo, Visible To and Position, Custom Color(255, 220, 70, 255), False);",
        "Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Asterisk, Visible To and Position, Custom Color(255, 220, 70, 255), False);",
    )
    block = one(
        block,
        "Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Warning, Visible To and Position, Color(Orange), False);",
        "Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Arrow: Down, Visible To and Position, Color(Orange), False);",
    )
    block = one(block, "\t\t\tSet Status(Event Player, Null, Knocked Down, 9999);\n", "")
    block = one(
        block,
        "\t\t\tKill(Event Player, Null);\n\t\tElse;",
        "\t\t\tKill(Event Player, Null);\n\t\t\tAbort;\n\t\tElse;",
    )
    return block

source = edit_rule(source, "18e - Nasib: Roulette sepuluh efek dengan hasil terkunci", edit_luck)

# Death while either the roulette OR a result is active must be a hard reset.
# Close first to release every captured button and destroy the old menu HUD;
# 18g then reopens a fresh Try Your Luck page immediately after this reset.
def edit_death(block: str) -> str:
    block = one(
        block,
        "\t\tEvent Player.KartuNasibAktif == True;\n",
        "\t\tOr(Event Player.KartuNasibAktif == True, Or(Event Player.PutaranKartuNasib > 0, Event Player.EfekNasib != 0)) == True;\n",
    )
    marker = "\tactions\n\t{\n"
    block = one(
        block,
        marker,
        marker + "\t\tEvent Player.MenuNasibHarusDibuka = False;\n\t\tCall Subroutine(TutupMenu);\n",
    )
    block = one(block, "\t\tClear Status(Event Player, Knocked Down);\n", "")
    return block

source = edit_rule(source, "18f - Nasib: Reset lengkap semua efek saat pemilik mati", edit_death)

# No Try Your Luck path sets Knocked Down anymore, so remove the redundant
# lifecycle cleanup too.
def edit_cleanup(block: str) -> str:
    return one(block, "\t\tClear Status(Event Player, Knocked Down);\n", "")

source = edit_rule(source, "93c - Subrutin: Bersihkan pemain saat keluar atau pindah tim", edit_cleanup)

SOURCE.write_text(source, encoding="utf-8")
new_blob = blob_sha(source)

# ---------------------------------------------------------------------------
# Static guards: pin the new source and protect the live-tested behavior.
# ---------------------------------------------------------------------------
validator = VALIDATOR.read_text(encoding="utf-8")
validator = one(validator, f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"', f'EXPECTED_SOURCE_BLOB = "{new_blob}"')

validator = one(
    validator,
    'for icon in ("Poison 2", "Halo", "Spiral", "Bolt", "Moon", "Eye", "Warning", "Dizzy", "Skull", "Heart"):',
    'for icon in ("Poison 2", "Asterisk", "Spiral", "Bolt", "Moon", "Eye", "Arrow: Down", "Dizzy", "Skull", "Heart"):',
)
validator = one(
    validator,
    '            "Set Status(Event Player, Null, Knocked Down, 9999);",\n',
    '',
)
validator = one(
    validator,
    '            "Clear Status(Event Player, Knocked Down);",\n',
    '',
)
validator = one(
    validator,
    '        checks.require("Start Forcing Player Position(" not in luck.body, "Try Your Luck non deve forzare la posizione")\n',
    '        checks.require("Start Forcing Player Position(" not in luck.body, "Try Your Luck non deve forzare la posizione")\n'
    '        checks.require("Set Status(Event Player, Null, Knocked Down" not in luck.body, "Try Your Luck caduta nel vuoto non deve usare Knocked Down")\n'
    '        checks.require("Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Halo" not in luck.body, "Try Your Luck riusa ancora Halo di Unkillable")\n'
    '        checks.require("Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Warning" not in luck.body, "Try Your Luck riusa ancora Warning di Unkillable")\n'
    '        checks.require("Kill(Event Player, Null);\\n\\t\\t\\tAbort;" in luck.body, "Skull Try Your Luck non interrompe subito la pipeline dopo la morte")\n',
)
validator = one(
    validator,
    '        checks.require("Event Player.MenuNasibHarusDibuka = True;" in luck_death.body, "morte Try Your Luck non richiede la riapertura dopo il reset")\n',
    '        checks.require("Event Player.MenuNasibHarusDibuka = True;" in luck_death.body, "morte Try Your Luck non richiede la riapertura dopo il reset")\n'
    '        checks.require("Call Subroutine(TutupMenu);" in luck_death.body, "morte Try Your Luck non chiude e libera il menu prima della riapertura")\n'
    '        checks.require("Event Player.PutaranKartuNasib > 0" in luck_death.body and "Event Player.EfekNasib != 0" in luck_death.body, "reset morte Try Your Luck non copre roulette ed effetto")\n',
)
validator = one(
    validator,
    '    for rule in rules:\n        if event_type(rule) == "Player Died":\n            checks.require("Call Subroutine(TutupMenu);" not in rule.body, f"{rule.name}: morte chiude il Menu Arcade")\n',
    '    for rule in rules:\n        if event_type(rule) == "Player Died" and not rule.name.startswith("18f - Nasib:"):\n            checks.require("Call Subroutine(TutupMenu);" not in rule.body, f"{rule.name}: morte chiude il Menu Arcade")\n',
)
validator = one(
    validator,
    '        checks.require("Wait(0.016, Ignore Condition);" not in camera_toggle.body, "Camera mantiene un frame Wait superfluo")\n',
    '        checks.require("Wait(0.016, Ignore Condition);" not in camera_toggle.body, "Camera mantiene un frame Wait superfluo")\n'
    '        checks.require("Event Player.MenuTerbuka == False;" not in camera_toggle.body, "Interact Camera deve funzionare anche con Menu Arcade aperto")\n'
    '        checks.require("Is Button Held(Event Player, Button(Crouch)) == False;" in camera_toggle.body, "Interact Camera deve restare separata dalla navigazione Crouch")\n',
)
validator = one(
    validator,
    '    checks.require(\'KartuNasibMerah ? Custom String("RED")\' not in source and \'KartuNasibMerah ? Custom String("MERAH")\' not in source, "HUD Try Your Luck usa ancora RED/GREEN")\n',
    '    checks.require(\'KartuNasibMerah ? Custom String("RED")\' not in source and \'KartuNasibMerah ? Custom String("MERAH")\' not in source, "HUD Try Your Luck usa ancora RED/GREEN")\n'
    '    checks.require("inspect hero + HP / navigate menus" in source, "HUD sinistro non indica Crouch per navigare i menu")\n'
    '    checks.require("0.5s: Camera" in source and "Input Binding String(Button(Interact))" in source, "HUD destro non indica Interact Camera")\n',
)

VALIDATOR.write_text(validator, encoding="utf-8")
print(f"Try Your Luck death/camera/HUD refinement: {OLD_BLOB} -> {new_blob}")
