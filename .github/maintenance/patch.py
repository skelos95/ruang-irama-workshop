from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
PROJECT = ROOT / "docs" / "PROGETTO.md"
VALIDATION = ROOT / "docs" / "VALIDAZIONE.md"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one occurrence, found {count}")
    return text.replace(old, new, 1)


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    return hashlib.sha1(payload).hexdigest()


source = SOURCE.read_text(encoding="utf-8")

# Live fix: do not use Nearest Walkable Position here. On stacked interiors it can
# snap to an upper walkable surface, which made the card appear near the ceiling.
source = replace_once(
    source,
    "Event Player.PosisiKartuNasib = Nearest Walkable Position(Position Of(Event Player) + Direction From Angles(Horizontal Facing Angle Of(Event Player), 0) * 3) - Vector(0, 1.200, 0);",
    "Event Player.PosisiKartuNasib = Position Of(Event Player) + Direction From Angles(Horizontal Facing Angle Of(Event Player), 0) * 2.500 - Vector(0, 0.450, 0);",
    "luck card base position",
)

# Make the public card much more readable and explicitly tell players to shoot it.
source = replace_once(
    source,
    'Custom String("[ ? ]\\nTRY YOUR LUCK")',
    'Custom String("[ ? ]\\nTRY YOUR LUCK\\nSHOOT ME")',
    "luck card English text",
)
source = replace_once(
    source,
    'Custom String("[ ? ]\\nCOBA NASIB")',
    'Custom String("[ ? ]\\nCOBA NASIB\\nTEMBAK")',
    "luck card Indonesian text",
)
source = replace_once(
    source,
    'Custom String("[ ? ]\\nเสี่ยงโชค")',
    'Custom String("[ ? ]\\nเสี่ยงโชค\\nยิงเลย")',
    "luck card Thai text",
)
source = replace_once(
    source,
    "Event Player.PosisiKartuNasib, 1.500, Do Not Clip",
    "Event Player.PosisiKartuNasib, 3.500, Do Not Clip",
    "luck card world-text size",
)

# Ring starts exactly at the owner's floor plane, while the text rises from
# 0.45 m below it to about 0.55 m above it.
source = replace_once(
    source,
    "Event Player.PosisiKartuNasib + Vector(0, 1.200, 0), 3);",
    "Event Player.PosisiKartuNasib + Vector(0, 0.450, 0), 3);",
    "luck card spawn ring height",
)
source = replace_once(
    source,
    "Chase Player Variable Over Time(Event Player, PosisiKartuNasib, Event Player.PosisiKartuNasib + Vector(0, 2.200, 0), 0.600, Destination and Duration);",
    "Chase Player Variable Over Time(Event Player, PosisiKartuNasib, Event Player.PosisiKartuNasib + Vector(0, 1.000, 0), 0.600, Destination and Duration);",
    "luck card rise distance",
)

# Live fix: use actual weapon firing plus a generous virtual spherical hitbox
# projected onto the owner's reticle. This is independent of text dimensions and
# is substantially more reliable than the old fixed 7-degree angular test.
old_hit = """\t\tIs Button Held(Event Player, Button(Primary Fire)) == True;\n\t\tAngle Between Vectors(Facing Direction Of(Event Player), Direction Towards(Eye Position(Event Player), Event Player.PosisiKartuNasib)) <= 7;\n\t\tIs In Line of Sight(Eye Position(Event Player), Event Player.PosisiKartuNasib, All Barriers Block LOS) == True;"""
new_hit = """\t\tIs Firing Primary(Event Player) == True;\n\t\tDistance Between(Event Player.PosisiKartuNasib, Eye Position(Event Player) + Facing Direction Of(Event Player) * Distance Between(Eye Position(Event Player), Event Player.PosisiKartuNasib)) <= 1.250;\n\t\tIs In Line of Sight(Eye Position(Event Player), Event Player.PosisiKartuNasib, All Barriers Block LOS) == True;"""
source = replace_once(source, old_hit, new_hit, "luck card hit detection")

SOURCE.write_text(source, encoding="utf-8")

# Tighten the validator around the exact live fixes instead of merely accepting them.
validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_once(
    validator,
    '"Is Button Held(Event Player, Button(Primary Fire)) == True;",\n            "Angle Between Vectors(",\n            "Is In Line of Sight(",',
    '"Is Firing Primary(Event Player) == True;",\n            "Distance Between(Event Player.PosisiKartuNasib, Eye Position(Event Player) + Facing Direction Of(Event Player) * Distance Between(Eye Position(Event Player), Event Player.PosisiKartuNasib)) <= 1.250;",\n            "Is In Line of Sight(",',
    "validator luck hit detection",
)
validator = replace_once(
    validator,
    '    checks.equal(len(card_texts), 1, "Nasib: una sola carta pubblica")\n    checks.require(\n        "Chase Player Variable Over Time(Event Player, PosisiKartuNasib" in mask_strings(source),\n        "Nasib: animazione di emersione dal terreno assente",\n    )',
    '    checks.equal(len(card_texts), 1, "Nasib: una sola carta pubblica")\n    if card_texts:\n        checks.require(\n            "Event Player.PosisiKartuNasib, 3.500, Do Not Clip" in card_texts[0],\n            "Nasib: la carta pubblica deve usare dimensione 3,5",\n        )\n    checks.require(\n        "Event Player.PosisiKartuNasib = Position Of(Event Player) + Direction From Angles(Horizontal Facing Angle Of(Event Player), 0) * 2.500 - Vector(0, 0.450, 0);" in mask_strings(source),\n        "Nasib: posizione bassa davanti al proprietario assente",\n    )\n    checks.require(\n        "Chase Player Variable Over Time(Event Player, PosisiKartuNasib, Event Player.PosisiKartuNasib + Vector(0, 1.000, 0), 0.600, Destination and Duration);" in mask_strings(source),\n        "Nasib: animazione bassa di emersione dal terreno assente",\n    )\n    if luck:\n        checks.require(\n            "Angle Between Vectors(" not in mask_strings(luck[0].body),\n            "Nasib: il vecchio test angolare fragile non deve restare nella risoluzione",\n        )',
    "validator luck visual geometry",
)
VALIDATOR.write_text(validator, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
project = replace_once(
    project,
    "Interact crea davanti al giocatore una carta virtuale che emerge dal terreno con un `Ring Explosion`. La carta usa `Create In-World Text`, è visibile a tutti e non occupa slot bot. Ogni giocatore può avere una sola carta attiva.",
    "Interact crea 2,5 m davanti al giocatore una carta virtuale che emerge dal terreno con un `Ring Explosion`. La posizione è calcolata direttamente dal piano dei piedi del proprietario, senza `Nearest Walkable Position`, per evitare agganci a piani superiori. Il testo sale da 0,45 m sotto il suolo fino a circa 0,55 m sopra e usa dimensione 3,5. La carta usa `Create In-World Text`, è visibile a tutti e non occupa slot bot. Ogni giocatore può avere una sola carta attiva.",
    "project luck card live position",
)
project = replace_once(
    project,
    "L'attivazione è proprietario-only: la regola legge esclusivamente `KartuNasibAktif` e `PosisiKartuNasib` dell'`Event Player`, richiede Primary Fire, mira entro 7° e linea di vista libera. Al colpo estrae `Random Integer(0, 1)`: un esito ripristina la salute massima, l'altro forza la morte del proprietario. Testo e stato vengono ripuliti anche alla morte o all'uscita del giocatore.",
    "L'attivazione è proprietario-only: la regola legge esclusivamente `KartuNasibAktif` e `PosisiKartuNasib` dell'`Event Player`, richiede `Is Firing Primary`, una hitbox virtuale di 1,25 m attorno al punto attraversato dal reticolo alla distanza della carta e linea di vista libera. Il vecchio limite angolare fisso da 7° è stato rimosso. Al colpo estrae `Random Integer(0, 1)`: un esito ripristina la salute massima, l'altro forza la morte del proprietario. Testo e stato vengono ripuliti anche alla morte o all'uscita del giocatore.",
    "project luck card live hitbox",
)
PROJECT.write_text(project, encoding="utf-8")

validation = VALIDATION.read_text(encoding="utf-8")
new_blob = git_blob_sha(SOURCE)
validation = replace_once(
    validation,
    "223da9ac0c21dce11f8ff15a20d922e8716bdf8b",
    new_blob,
    "validation Workshop blob",
)
validation = replace_once(
    validation,
    "- Menu 10 Try Your Luck: carta pubblica, attivazione solo proprietario, esito 50/50;",
    "- Menu 10 Try Your Luck: carta pubblica bassa/grande, hitbox reticolo 1,25 m solo proprietario, esito 50/50;",
    "validation luck card note",
)
VALIDATION.write_text(validation, encoding="utf-8")
