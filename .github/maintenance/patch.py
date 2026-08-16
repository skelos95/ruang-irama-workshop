from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
README = ROOT / "README.md"
PROGETTO = ROOT / "docs" / "PROGETTO.md"
TEST_DOC = ROOT / "docs" / "TEST.md"
VALIDAZIONE = ROOT / "docs" / "VALIDAZIONE.md"
VERSION = ROOT / "VERSION"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected 1 occurrence, found {count}")
    return text.replace(old, new, 1)


# Workshop: Jump respawn must work whether the Arcade menu is open or closed.
source = SOURCE.read_text(encoding="utf-8")
start = source.index('rule("12f - Bangkit Lompat: Bangkit di posisi aman yang bisa dilalui")')
end = source.index('rule("13 - Intip Pahlawan:', start)
rule = source[start:end]
rule = replace_once(
    rule,
    '\t\tEvent Player.MenuTerbuka == False;\n',
    '',
    "remove closed-menu guard from Jump respawn",
)
source = source[:start] + rule + source[end:]
SOURCE.write_text(source, encoding="utf-8")

# Validator/version: lock the new invariant so the bug cannot silently return.
validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_once(
    validator,
    "della versione 0.6.5.",
    "della versione 0.6.6.",
    "validator docstring version",
)
validator = replace_once(
    validator,
    'CURRENT_VERSION = "0.6.5"',
    'CURRENT_VERSION = "0.6.6"',
    "validator current version",
)
anchor = '''    for token in (
        "58: PosisiMati", "59: PosisiBangkitAman", "60: BangkitLompatDipakai",
        "18: EfekTerapkan", "19: EfekPulihkan",
        "Play Effect(All Players(All Teams), Ring Explosion, Global.RGB",
        "Event Player.PosisiMati = Position Of(Event Player);",
        "Nearest Walkable Position(Event Player.PosisiMati + Vector(Random Real(-6, 6), 0, Random Real(-6, 6)))",
        "Respawn(Event Player);",
        "Teleport(Event Player, Event Player.PosisiBangkitAman);",
    ):
        checks.require(token in clean, f"feedback/respawn mancante: {token}")
'''
addition = anchor + '''    jump_respawn_rules = [
        rule for rule in rules if rule.name.startswith("12f - Bangkit Lompat:")
    ]
    checks.equal(len(jump_respawn_rules), 1, "regola Jump respawn")
    if jump_respawn_rules:
        jump_code = mask_strings(jump_respawn_rules[0].body)
        checks.require(
            "Event Player.MenuTerbuka == False;" not in jump_code,
            "Jump respawn non deve richiedere il Menu Arcade chiuso",
        )
'''
validator = replace_once(
    validator,
    anchor,
    addition,
    "insert Jump respawn menu invariant",
)
VALIDATOR.write_text(validator, encoding="utf-8")

# Project version.
VERSION.write_text("0.6.6\n", encoding="utf-8")

# README current-version marker and control table.
readme = README.read_text(encoding="utf-8")
readme = replace_once(
    readme,
    "La versione **0.6.5** identifica lo stato funzionale e tecnico corrente del repository.",
    "La versione **0.6.6** identifica lo stato funzionale e tecnico corrente del repository.",
    "README current version",
)
readme = replace_once(
    readme,
    "| Da morto, menu chiuso | Jump | Respawn vicino al punto di morte |",
    "| Da morto, menu aperto o chiuso | Jump | Respawn vicino al punto di morte |",
    "README Jump control",
)
if "### Respawn Jump 0.6.6" not in readme:
    readme += '''\n\n### Respawn Jump 0.6.6\n\nDa morto, `Jump` esegue il respawn vicino al punto di morte anche se il Menu Arcade è già aperto. Il menu non viene chiuso dal respawn e la regola `12f - Bangkit Lompat` non dipende più da `MenuTerbuka == False`.\n'''
README.write_text(readme, encoding="utf-8")

# Project notes current-version markers.
progetto = PROGETTO.read_text(encoding="utf-8")
progetto = replace_once(
    progetto,
    "# Note di progetto — versione 0.6.5",
    "# Note di progetto — versione 0.6.6",
    "PROGETTO title",
)
progetto = replace_once(
    progetto,
    "Questo documento descrive lo **stato funzionale e tecnico corrente** del Workshop 0.6.5.",
    "Questo documento descrive lo **stato funzionale e tecnico corrente** del Workshop 0.6.6.",
    "PROGETTO current version",
)
if "## Hotfix Respawn Jump 0.6.6" not in progetto:
    progetto += '''\n\n## Hotfix Respawn Jump 0.6.6\n\nIl respawn manuale con `Jump` resta disponibile da morto anche con il Menu Arcade aperto. La morte e il respawn non chiudono il menu; viene rimosso soltanto il guard `MenuTerbuka == False` dalla regola `12f`, mantenendo invariati `TeleportasiJongkokAktif`, il latch `BangkitLompatDipakai`, `Nearest Walkable Position`, `Respawn` e il teleport alla posizione sicura.\n'''
PROGETTO.write_text(progetto, encoding="utf-8")

# Test plan current-version markers and explicit live case.
test_doc = TEST_DOC.read_text(encoding="utf-8")
test_doc = replace_once(
    test_doc,
    "# Piano di test — versione 0.6.5",
    "# Piano di test — versione 0.6.6",
    "TEST title",
)
test_doc = replace_once(
    test_doc,
    "Questa matrice descrive lo **stato funzionale e tecnico corrente** del Workshop 0.6.5.",
    "Questa matrice descrive lo **stato funzionale e tecnico corrente** del Workshop 0.6.6.",
    "TEST current version",
)
if "## Hotfix Respawn Jump 0.6.6" not in test_doc:
    test_doc += '''\n\n## Hotfix Respawn Jump 0.6.6\n\nVerifica live obbligatoria: aprire il Menu Arcade, morire lasciandolo aperto, premere `Jump` e confermare che il player rinasca vicino al punto di morte senza che il menu venga chiuso. Ripetere sia dal Main Menu sia da un sottomenu.\n'''
TEST_DOC.write_text(test_doc, encoding="utf-8")

# Validation report current-version markers and exact Workshop blob.
validazione = VALIDAZIONE.read_text(encoding="utf-8")
validazione = replace_once(
    validazione,
    "# Rapporto di validazione — versione 0.6.5",
    "# Rapporto di validazione — versione 0.6.6",
    "VALIDAZIONE title",
)
validazione = replace_once(
    validazione,
    "Release tecnica: **CHILL Dedicated Server 0.6.5**",
    "Release tecnica: **CHILL Dedicated Server 0.6.6**",
    "VALIDAZIONE release",
)
validazione = replace_once(
    validazione,
    "OK - controlli statici v0.6.5 superati",
    "OK - controlli statici v0.6.6 superati",
    "VALIDAZIONE expected result",
)
if "## Hotfix Respawn Jump 0.6.6" not in validazione:
    validazione += '''\n\n## Hotfix Respawn Jump 0.6.6\n\nIl gate verifica che la regola `12f - Bangkit Lompat` esista una sola volta e non contenga `Event Player.MenuTerbuka == False;`. In questo modo il respawn con `Jump` resta disponibile anche con Menu Arcade aperto, che deve restare visibile durante morte e respawn.\n'''

data = SOURCE.read_bytes().replace(b"\r\n", b"\n")
payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
blob = hashlib.sha1(payload).hexdigest()
validazione, count = re.subn(
    r"(Blob Git del sorgente Workshop validato:\n\n```text\n)[0-9a-f]{40}(\n```)",
    rf"\g<1>{blob}\g<2>",
    validazione,
    count=1,
)
if count != 1:
    raise RuntimeError("VALIDAZIONE Workshop blob marker not found")
VALIDAZIONE.write_text(validazione, encoding="utf-8")

print("Applied CHILL 0.6.6 respawn-with-menu hotfix")
