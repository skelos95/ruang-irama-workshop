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


def replace_count(text: str, old: str, new: str, expected: int, label: str) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"{label}: expected {expected} occurrences, found {count}")
    return text.replace(old, new)


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    return hashlib.sha1(payload).hexdigest()


source = SOURCE.read_text(encoding="utf-8")

# Do not stop/restart the custom camera when Menu 10 starts. That transition was
# the visible snap reported in live third-person testing.
source = replace_once(
    source,
    '''\t\t\t\tEvent Player.ModeKameraSebelumNasib = Event Player.ModeKamera;\n\t\t\t\tEvent Player.TargetKameraSebelumNasib = Event Player.TargetKamera;\n\t\t\t\tIf(Event Player.ModeKamera != 0);\n\t\t\t\t\tStop Camera(Event Player);\n\t\t\t\t\tEvent Player.ModeKamera = 0;\n\t\t\t\t\tEvent Player.TargetKamera = Null;\n\t\t\t\t\tWait(0.016, Ignore Condition);\n\t\t\t\tEnd;\n''',
    '',
    "remove luck camera switch",
)

# Same camera-origin formula used by MulaiKamera. The card center is projected
# four metres along the real custom-camera look ray, so third-person stays active
# without introducing the old Eye/Facing parallax.
camera_origin = '''First Of(Mapped Array(Array(Ray Cast Hit Position(Eye Position(Event Player.TargetKamera)
\t\t\t\t\t+ Vector(0, Min(0.750, Max(0.450, 0.450 + (Max Health(Event Player.TargetKamera) - 200) * 0.0006)), 0), Eye Position(
\t\t\t\t\tEvent Player.TargetKamera) + Vector(0, Min(0.750, Max(0.450, 0.450 + (Max Health(Event Player.TargetKamera) - 200) * 0.0006)), 0)
\t\t\t\t\t- Facing Direction Of(Event Player.TargetKamera) * Min(4.500, Max(Global.JarakKamera, Global.JarakKamera + (Max Health(
\t\t\t\t\tEvent Player.TargetKamera) - 200) * 0.0055)) + Cross Product(Direction From Angles(Horizontal Facing Angle Of(Event Player.TargetKamera), 0),
\t\t\t\t\tVector(0, 1, 0)) * Min(1.350, Max(Global.GeserKamera, Global.GeserKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0016)),
\t\t\t\t\tEmpty Array, Empty Array, False)), Current Array Element + Direction Towards(Current Array Element, Eye Position(Event Player.TargetKamera)
\t\t\t\t\t+ Vector(0, Min(0.750, Max(0.450, 0.450 + (Max Health(Event Player.TargetKamera) - 200) * 0.0006)), 0)) * Min(Global.BantalanDinding,
\t\t\t\t\tDistance Between(Current Array Element, Eye Position(Event Player.TargetKamera) + Vector(0, Min(0.750, Max(0.450, 0.450 + (Max Health(
\t\t\t\t\tEvent Player.TargetKamera) - 200) * 0.0006)), 0)) * 0.250))))'''
third_center = f'''First Of(Mapped Array(Array({camera_origin}), Current Array Element + Direction Towards(Current Array Element, Eye Position(
\t\t\t\t\tEvent Player.TargetKamera) + Facing Direction Of(Event Player.TargetKamera) * Global.JarakBidik) * 4))'''
center = f'''Or(Event Player.ModeKamera == 0, Event Player.TargetKamera == Null) ? Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 : {third_center}'''

left = f'''Update Every Frame(Or(Event Player.ModeKamera == 0, Event Player.TargetKamera == Null) ? Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 - Cross Product(Direction From Angles(Horizontal Facing Angle Of(Event Player), 0), Vector(0, 1, 0)) * 0.300 : {third_center} - Cross Product(Direction From Angles(Horizontal Facing Angle Of(Event Player.TargetKamera), 0), Vector(0, 1, 0)) * 0.300)'''
right = f'''Update Every Frame(Or(Event Player.ModeKamera == 0, Event Player.TargetKamera == Null) ? Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 + Cross Product(Direction From Angles(Horizontal Facing Angle Of(Event Player), 0), Vector(0, 1, 0)) * 0.300 : {third_center} + Cross Product(Direction From Angles(Horizontal Facing Angle Of(Event Player.TargetKamera), 0), Vector(0, 1, 0)) * 0.300)'''
icon = f'''Update Every Frame(({center}) - Vector(0, 0.450, 0))'''

source = replace_once(
    source,
    'Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 - Cross Product(Direction From Angles(Horizontal Facing Angle Of(Event Player), 0), Vector(0, 1, 0)) * 0.300)',
    left,
    "camera-aware left bracket",
)
source = replace_once(
    source,
    'Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 + Cross Product(Direction From Angles(Horizontal Facing Angle Of(Event Player), 0), Vector(0, 1, 0)) * 0.300)',
    right,
    "camera-aware right bracket",
)
source = replace_count(
    source,
    'Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 - Vector(0, 0.450, 0))',
    icon,
    2,
    "camera-aware native icons",
)
SOURCE.write_text(source, encoding="utf-8")

validator = VALIDATOR.read_text(encoding="utf-8")

# The card must now explicitly support the custom-camera look ray on both brackets
# and both persistent native icons.
validator = replace_once(
    validator,
    '        checks.require(joined.count("Update Every Frame(") >= 2, "Nasib: bracket non aggiornati ogni frame")',
    '        checks.require(joined.count("Update Every Frame(") >= 2, "Nasib: bracket non aggiornati ogni frame")\n        checks.require(joined.count("Event Player.ModeKamera == 0") >= 2 and joined.count("Global.JarakBidik") >= 2, "Nasib: bracket non seguono la linea reale della camera 3P")',
    "validator bracket camera ray",
)
validator = replace_once(
    validator,
    '        checks.require("Update Every Frame(" in skull and "Update Every Frame(" in heart, "Nasib: icone non agganciate client-side ogni frame")',
    '        checks.require("Update Every Frame(" in skull and "Update Every Frame(" in heart, "Nasib: icone non agganciate client-side ogni frame")\n        checks.require("Event Player.ModeKamera == 0" in skull and "Global.JarakBidik" in skull and "Event Player.ModeKamera == 0" in heart and "Global.JarakBidik" in heart, "Nasib: Heart/Skull non seguono la linea reale della camera 3P")',
    "validator icon camera ray",
)

old_camera_gate = '''    checks.require(
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
new_camera_gate = '''    if luck_start >= 0:
        checks.require(
            "Event Player.ModeKameraSebelumNasib = Event Player.ModeKamera;" not in before_luck
            and "Stop Camera(Event Player);" not in before_luck
            and "Event Player.ModeKamera = 0;" not in before_luck,
            "Nasib: l'avvio della carta cambia ancora la camera e può produrre uno scatto",
        )
    restore_rules = [rule for rule in rules if rule.name.startswith("18g - Nasib:")]
    checks.equal(len(restore_rules), 1, "Nasib: regola compatibilità ripristino camera")
'''
validator = replace_once(validator, old_camera_gate, new_camera_gate, "validator no camera snap")
VALIDATOR.write_text(validator, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
project = replace_once(
    project,
    "Interact crea una carta virtuale centrata sul mirino e visibile a tutti. Durante la roulette l'eventuale camera custom viene temporaneamente sospesa per usare la prima persona, poi ripristinata se il player sopravvive o al respawn. Le parentesi sono due In-World Text distinti posti fisicamente a ±0,30 m dal centro, quindi la loro apertura non dipende dagli spazi del font. Heart e Skull sono due Create Icon persistenti, entrambi con posizione racchiusa in Update Every Frame; il cambio rosso/verde alterna soltanto la visibilità, senza Destroy/Create per tick. La roulette resta a 20..24 cambi con intervallo iniziale 0,08 s e +0,055 s per passaggio.",
    "Interact crea una carta virtuale centrata sul mirino e visibile a tutti. La roulette non cambia più la modalità camera: in prima persona usa `Eye Position + Facing Direction`, mentre in terza persona riusa la stessa origine raycast della subroutine `MulaiKamera` e proietta la carta lungo il medesimo punto di mira `Global.JarakBidik`. In questo modo l'attivazione non esegue più `Stop Camera` e non produce lo scatto 3P→1P. Le parentesi restano due In-World Text distinti a ±0,30 m dal centro; Heart e Skull restano due Create Icon persistenti con `Update Every Frame`, senza Destroy/Create per tick. La roulette resta a 20..24 cambi con intervallo iniziale 0,08 s e +0,055 s per passaggio.",
    "project no camera snap",
)
PROJECT.write_text(project, encoding="utf-8")

validation = VALIDATION.read_text(encoding="utf-8")
validation = re.sub(
    r"- Menu 10 Try Your Luck: .*?esito 50/50;",
    "- Menu 10 Try Your Luck: due bracket separati a ±0,30 m, Heart/Skull persistenti con Update Every Frame e aggancio alla stessa linea di mira della camera 3P senza Stop Camera o switch in prima persona, Unkillable OFF, menu bloccato, reset alla morte, verde cura completa, rosso uccide dopo countdown 3 s, esito 50/50;",
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
