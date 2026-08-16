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


def matching_close(text: str, opening: int) -> int:
    depth = 1
    in_string = False
    escaped = False
    for i in range(opening + 1, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
    raise RuntimeError("unclosed rule")


def rule_spans(text: str):
    pattern = re.compile(r'^rule\("([^"]+)"\)\s*\{', re.MULTILINE)
    for match in pattern.finditer(text):
        opening = text.find("{", match.start(), match.end())
        closing = matching_close(text, opening)
        yield match.group(1), match.start(), closing + 1, text[match.start():closing + 1]


def add_alive_condition(rule: str, label: str) -> str:
    if "Is Alive(Event Player) == True;" in rule:
        return rule
    marker = "\tconditions\n\t{\n"
    if marker not in rule:
        raise RuntimeError(f"{label}: conditions block not found")
    return rule.replace(marker, marker + "\t\tIs Alive(Event Player) == True;\n", 1)


source = SOURCE.read_text(encoding="utf-8")

# Freeze every menu command while dead. 05d (release/reset latch) is deliberately
# not included because it only clears an internal latch and does not execute a menu action.
patches = []
for name, start, end, rule in rule_spans(source):
    if (
        "Event Player.MenuTerbuka == True;" in rule
        and re.search(r"Event Player\.PerintahMenu == \d+;", rule)
    ):
        patched = add_alive_condition(rule, name)
        if patched != rule:
            patches.append((start, end, patched))

if not patches:
    raise RuntimeError("no menu command rules needed the alive guard")
for start, end, patched in reversed(patches):
    source = source[:start] + patched + source[end:]

# Drop any command captured immediately before the death event. Keep the menu open.
rule_name = 'rule("12e - Bangkit Lompat: Simpan posisi kematian")'
start = source.index(rule_name)
end = source.index('rule("12f - Bangkit Lompat:', start)
death_rule = source[start:end]
death_rule = replace_once(
    death_rule,
    "\t\tEvent Player.BangkitLompatDipakai = False;\n",
    "\t\tEvent Player.BangkitLompatDipakai = False;\n\t\tEvent Player.PerintahMenu = 0;\n\t\tEvent Player.PerintahTeleportasi = 0;\n",
    "clear queued commands on death",
)
source = source[:start] + death_rule + source[end:]
SOURCE.write_text(source, encoding="utf-8")

# Validator/version.
validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_once(validator, "della versione 0.6.6.", "della versione 0.6.7.", "validator docstring version")
validator = replace_once(validator, 'CURRENT_VERSION = "0.6.6"', 'CURRENT_VERSION = "0.6.7"', "validator version")

menu_anchor = '''def check_menus(checks: Checks, source: str, rules: list[Rule], subroutines: set[str]) -> None:\n    clean = mask_strings(source)\n'''
menu_checks = menu_anchor + '''    # Da morto il Menu Arcade resta visibile ma non accetta comandi.\n    menu_command_rules = [\n        rule for rule in rules\n        if code_contains(rule.body, "Event Player.MenuTerbuka == True;")\n        and re.search(r"Event Player\\.PerintahMenu == \\d+;", mask_strings(rule.body)) is not None\n    ]\n    checks.require(menu_command_rules, "menu: nessuna regola comando trovata")\n    for rule in menu_command_rules:\n        checks.require(\n            code_contains(rule.body, "Is Alive(Event Player) == True;"),\n            f"menu da morto non bloccato nella regola: {rule.name}",\n        )\n\n    death_input_reset = [\n        rule for rule in rules if rule.name.startswith("12e - Bangkit Lompat:")\n    ]\n    checks.equal(len(death_input_reset), 1, "regola morte/respawn")\n    if death_input_reset:\n        checks.require(\n            code_contains(\n                death_input_reset[0].body,\n                "Event Player.PerintahMenu = 0;",\n                "Event Player.PerintahTeleportasi = 0;",\n            ),\n            "morte: comandi Menu/Teleport in coda non vengono azzerati",\n        )\n\n    crouch_activators = [\n        rule for rule in rules\n        if code_contains(rule.body, "Is Button Held(Event Player, Button(Crouch)) == True;")\n        and (\n            code_contains(rule.body, "Event Player.InspeksiAktif = True;")\n            or code_contains(rule.body, "Event Player.TeleportasiJongkokAktif = True;")\n        )\n    ]\n    checks.equal(len(crouch_activators), 2, "attivatori Crouch vivi")\n    for rule in crouch_activators:\n        checks.require(\n            code_contains(rule.body, "Is Alive(Event Player) == True;"),\n            f"Crouch non deve attivarsi da morto: {rule.name}",\n        )\n'''
validator = replace_once(validator, menu_anchor, menu_checks, "insert dead-input menu checks")
VALIDATOR.write_text(validator, encoding="utf-8")

VERSION.write_text("0.6.7\n", encoding="utf-8")

# README.
readme = README.read_text(encoding="utf-8")
readme = replace_once(readme, "La versione **0.6.6** identifica lo stato funzionale e tecnico corrente del repository.", "La versione **0.6.7** identifica lo stato funzionale e tecnico corrente del repository.", "README version")
if "### Input da morto 0.6.7" not in readme:
    readme += '''\n\n### Input da morto 0.6.7\n\nQuando il player muore, un Menu Arcade già aperto resta visibile ma viene congelato: Primary Fire, Secondary Fire, Interact, Reload, Crouch e gli altri input Arcade non eseguono azioni. Anche Crouch inspection e Crouch Teleport restano inattivi. L'unico input custom attivo da morto è `Jump`, usato esclusivamente dal respawn manuale vicino al punto di morte. Dopo il respawn il menu rimane aperto e torna utilizzabile.\n'''
README.write_text(readme, encoding="utf-8")

# Project notes.
progetto = PROGETTO.read_text(encoding="utf-8")
progetto = replace_once(progetto, "# Note di progetto — versione 0.6.6", "# Note di progetto — versione 0.6.7", "PROGETTO title")
progetto = replace_once(progetto, "Workshop 0.6.6.", "Workshop 0.6.7.", "PROGETTO version text")
if "## Hotfix input da morto 0.6.7" not in progetto:
    progetto += '''\n\n## Hotfix input da morto 0.6.7\n\nDa morto il Menu Arcade non viene chiuso, ma tutte le regole che eseguono `PerintahMenu == N` richiedono `Is Alive(Event Player) == True`. La regola di morte azzera inoltre `PerintahMenu` e `PerintahTeleportasi` per eliminare input catturati nell'istante della morte. Gli attivatori Crouch inspection/Teleport restano protetti da `Is Alive == True`. `Jump` nella regola `12f` è l'unica eccezione e continua a eseguire il respawn manuale anche con menu aperto.\n'''
PROGETTO.write_text(progetto, encoding="utf-8")

# Test plan.
test_doc = TEST_DOC.read_text(encoding="utf-8")
test_doc = replace_once(test_doc, "# Piano di test — versione 0.6.6", "# Piano di test — versione 0.6.7", "TEST title")
test_doc = replace_once(test_doc, "Workshop 0.6.6.", "Workshop 0.6.7.", "TEST version text")
if "## Hotfix input da morto 0.6.7" not in test_doc:
    test_doc += '''\n\n## Hotfix input da morto 0.6.7\n\nVerifica live obbligatoria: con Menu Arcade aperto, morire e provare Primary Fire, Secondary Fire, Interact, Reload, Crouch e Melee; nessuno deve modificare o chiudere il menu e Crouch non deve aprire inspection/Teleport. Premere quindi `Jump`: deve essere l'unico comando custom efficace, effettuare il respawn vicino al punto di morte e lasciare il menu aperto. Dopo il respawn, verificare che tutti i comandi menu tornino immediatamente disponibili.\n'''
TEST_DOC.write_text(test_doc, encoding="utf-8")

# Validation report.
validazione = VALIDAZIONE.read_text(encoding="utf-8")
validazione = replace_once(validazione, "# Rapporto di validazione — versione 0.6.6", "# Rapporto di validazione — versione 0.6.7", "VALIDAZIONE title")
validazione = replace_once(validazione, "Release tecnica: **CHILL Dedicated Server 0.6.6**", "Release tecnica: **CHILL Dedicated Server 0.6.7**", "VALIDAZIONE release")
validazione = replace_once(validazione, "OK - controlli statici v0.6.6 superati", "OK - controlli statici v0.6.7 superati", "VALIDAZIONE result")
if "## Hotfix input da morto 0.6.7" not in validazione:
    validazione += '''\n\n## Hotfix input da morto 0.6.7\n\nIl gate statico richiede `Is Alive(Event Player) == True` su tutte le regole che eseguono comandi `PerintahMenu == N`, richiede l'azzeramento di `PerintahMenu`/`PerintahTeleportasi` alla morte e certifica che i due attivatori Crouch (inspection e Teleport) siano disponibili solo da vivi. La regola Jump respawn resta invece utilizzabile da morto anche con Menu Arcade aperto.\n'''

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

print(f"Applied CHILL 0.6.7 dead-input lock to {len(patches)} menu command rules")
