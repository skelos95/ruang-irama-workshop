from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
PROJECT = ROOT / "docs" / "PROGETTO.md"
VALIDATION = ROOT / "docs" / "VALIDAZIONE.md"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one occurrence, found {count}")
    return text.replace(old, new, 1)


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    return hashlib.sha1(payload).hexdigest()


source = SOURCE.read_text(encoding="utf-8")

# Live fix: keep whatever camera the player is already using. The previous
# Stop Camera -> first person transition caused a visible snap when Menu 10 began.
source = replace_once(
    source,
    '''\t\t\t\tEvent Player.ModeKameraSebelumNasib = Event Player.ModeKamera;\n\t\t\t\tEvent Player.TargetKameraSebelumNasib = Event Player.TargetKamera;\n\t\t\t\tIf(Event Player.ModeKamera != 0);\n\t\t\t\t\tStop Camera(Event Player);\n\t\t\t\t\tEvent Player.ModeKamera = 0;\n\t\t\t\t\tEvent Player.TargetKamera = Null;\n\t\t\t\t\tWait(0.016, Ignore Condition);\n\t\t\t\tEnd;\n''',
    '',
    "remove Menu 10 camera transition",
)

# Since Menu 10 no longer changes camera, the post-result camera restore block is
# obsolete and must not restart the current camera later.
old_restore = '''\t\tIf(And(Is Alive(Event Player) == True, Event Player.ModeKameraSebelumNasib != 0));\n\t\t\tIf(Event Player.ModeKameraSebelumNasib == 1);\n\t\t\t\tEvent Player.TargetKamera = Event Player;\n\t\t\t\tWait(0.016, Ignore Condition);\n\t\t\t\tEvent Player.ModeKamera = 1;\n\t\t\t\tCall Subroutine(MulaiKamera);\n\t\t\tElse If(And(Event Player.TargetKameraSebelumNasib != Null, Entity Exists(Event Player.TargetKameraSebelumNasib)));\n\t\t\t\tEvent Player.TargetKamera = Event Player.TargetKameraSebelumNasib;\n\t\t\t\tWait(0.016, Ignore Condition);\n\t\t\t\tEvent Player.ModeKamera = 2;\n\t\t\t\tCall Subroutine(MulaiKamera);\n\t\t\tEnd;\n\t\t\tEvent Player.ModeKameraSebelumNasib = 0;\n\t\t\tEvent Player.TargetKameraSebelumNasib = Null;\n\t\tEnd;\n'''
source = replace_once(source, old_restore, '', "remove obsolete end restore")

# Remove the respawn restore rule for the same reason: Menu 10 never changes camera now.
start = source.index('rule("18g - Nasib: Pulihkan kamera setelah respawn")')
end = source.index('rule("19 - Teleportasi Jongkok:', start)
source = source[:start] + source[end:]

SOURCE.write_text(source, encoding="utf-8")

validator = VALIDATOR.read_text(encoding="utf-8")
old_camera_checks = '''    checks.require(
        "Event Player.ModeKameraSebelumNasib = Event Player.ModeKamera;" in menu_interact
        and "Stop Camera(Event Player);" in menu_interact
        and "Event Player.ModeKamera = 0;" in menu_interact,
        "Nasib: camera non viene temporaneamente bloccata in prima persona",
    )
    restore_rules = [rule for rule in rules if rule.name.startswith("18g - Nasib:")]
    checks.equal(len(restore_rules), 1, "Nasib: una sola regola ripristino camera dopo respawn")
    if restore_rules:
        checks.require(
            code_contains(restore_rules[0].body, "ModeKameraSebelumNasib", "Call Subroutine(MulaiKamera);"),
            "Nasib: ripristino camera incompleto",
        )
'''
new_camera_checks = '''    checks.require(
        "Event Player.ModeKameraSebelumNasib = Event Player.ModeKamera;" not in menu_interact
        and "Event Player.TargetKameraSebelumNasib = Event Player.TargetKamera;" not in menu_interact,
        "Nasib: l'avvio salva ancora una camera che non deve modificare",
    )
    luck_start_at = menu_interact.find("Event Player.KartuNasibAktif = True;")
    if luck_start_at >= 0:
        luck_activation_tail = menu_interact[max(0, luck_start_at - 500):luck_start_at + 500]
        checks.require(
            "Stop Camera(Event Player);" not in luck_activation_tail
            and "Event Player.ModeKamera = 0;" not in luck_activation_tail
            and "Event Player.TargetKamera = Null;" not in luck_activation_tail,
            "Nasib: attivazione cambia ancora la camera e può causare uno scatto",
        )
    restore_rules = [rule for rule in rules if rule.name.startswith("18g - Nasib:")]
    checks.equal(len(restore_rules), 0, "Nasib: la vecchia regola ripristino camera non deve più esistere")
'''
validator = replace_once(validator, old_camera_checks, new_camera_checks, "validator no camera switch")
VALIDATOR.write_text(validator, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
project = replace_once(
    project,
    "Interact crea una carta virtuale centrata sul mirino e visibile a tutti. Durante la roulette l'eventuale camera custom viene temporaneamente sospesa per usare la prima persona, poi ripristinata se il player sopravvive o al respawn.",
    "Interact crea una carta virtuale centrata sul mirino e visibile a tutti. La roulette non cambia più la camera del player: se Menu 10 viene attivato in terza persona, la terza persona resta attiva senza `Stop Camera`, passaggio in prima persona o successivo ripristino.",
    "project no camera snap",
)
PROJECT.write_text(project, encoding="utf-8")

validation = VALIDATION.read_text(encoding="utf-8")
validation = re.sub(
    r"- Menu 10 Try Your Luck: .*?esito 50/50;",
    "- Menu 10 Try Your Luck: due bracket separati a ±0,30 m, Heart/Skull persistenti con Update Every Frame; la roulette non modifica più la camera, quindi in 3P non esegue Stop Camera o switch 3P→1P; Unkillable OFF, menu bloccato, reset alla morte, verde cura completa, rosso uccide dopo countdown 3 s, esito 50/50;",
    validation,
    count=1,
)
new_blob = git_blob_sha(SOURCE)
validation, count = re.subn(
    r"(?s)(Blob Git del sorgente Workshop validato:\s*```text\s*)[0-9a-f]{40}(\s*```)",
    rf"\g<1>{new_blob}\g<2>",
    validation,
    count=1,
)
if count != 1:
    raise RuntimeError("validation blob not found")
VALIDATION.write_text(validation, encoding="utf-8")
