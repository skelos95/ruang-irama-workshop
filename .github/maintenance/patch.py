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
    raise RuntimeError("unclosed Workshop rule")


def get_rule(text: str, name: str) -> tuple[int, int, str]:
    marker = f'rule("{name}")'
    start = text.index(marker)
    opening = text.index("{", start)
    end = matching_close(text, opening) + 1
    return start, end, text[start:end]


def put_rule(text: str, name: str, rule: str) -> str:
    start, end, _ = get_rule(text, name)
    return text[:start] + rule + text[end:]


def remove_calls(segment: str, call: str) -> tuple[str, int]:
    pattern = re.compile(rf"(?m)^\s*Call Subroutine\({re.escape(call)}\);\n")
    matches = list(pattern.finditer(segment))
    for match in reversed(matches):
        segment = segment[:match.start()] + segment[match.end():]
    return segment, len(matches)


def branch_segment(rule: str, start_marker: str, end_marker: str | None) -> tuple[int, int, str]:
    start = rule.index(start_marker)
    end = len(rule) if end_marker is None else rule.index(end_marker, start + len(start_marker))
    return start, end, rule[start:end]


source = SOURCE.read_text(encoding="utf-8")

# Menu Arcade: re-arm the input latch immediately after every menu button is released.
name = "05d - Menu: Lepaskan pengatur setelah semua masukan dilepas"
_, _, rule = get_rule(source, name)
rule = replace_once(
    rule,
    '\t\t"Tunda satu bingkai agar pengendali menyelesaikan perintah sebelum pengatur masukan diaktifkan kembali."\n\t\tWait(0.016, Ignore Condition);\n',
    '\t\t"Aktifkan kembali pengatur segera setelah semua tombol dilepas; latch tetap mencegah pengulangan saat tombol ditahan."\n',
    "Arcade release wait",
)
source = put_rule(source, name, rule)

# Cursor movement does not need to destroy/recreate the HUD: all menu HUDs use
# live string/color reevaluation. Main and Name Color still need the lightweight
# palette chase update, which is harmless on other pages.
for name in (
    "06 - Menu: Tembakan utama memilih berikutnya",
    "07 - Menu: Tembakan sekunder memilih sebelumnya",
):
    _, _, rule = get_rule(source, name)
    rule = replace_once(
        rule,
        "\t\tCall Subroutine(GambarMenu);\n",
        "\t\tCall Subroutine(TransisiWarnaMenu);\n",
        f"lightweight navigation {name}",
    )
    source = put_rule(source, name, rule)

for name in (
    "08 - Menu 0: Lompat mundur sepuluh genre",
    "09 - Menu 0: Jongkok maju sepuluh genre",
):
    _, _, rule = get_rule(source, name)
    rule = replace_once(rule, "\t\tCall Subroutine(GambarMenu);\n", "", f"live HUD {name}")
    source = put_rule(source, name, rule)

# Interact: remove the two artificial one-frame waits used by Camera. Also avoid
# same-renderer redraws for ordinary apply operations. Two explicit redraws stay:
# Menu 6 (voice NORMAL/apply semantics) and Menu 10 (roulette READY->ROLLING status),
# plus the required Main -> submenu renderer switch.
name = "10 - Menu: Interaksi membuka atau menerapkan pilihan"
_, _, rule = get_rule(source, name)
for old in (
    '\t\t\t\t\t"Biarkan satu bingkai Interact selesai sebelum mengganti tampilan kamera."\n\t\t\t\t\tWait(0.016, Ignore Condition);\n',
    '\t\t\t\t\t\t"Gunakan jeda satu bingkai yang sama saat mulai menonton dari orang pertama."\n\t\t\t\t\t\tWait(0.016, Ignore Condition);\n',
):
    if old not in rule:
        raise RuntimeError("expected Camera one-frame wait not found")
    rule = rule.replace(old, "", 1)

# Remove redraws only from ordinary apply branches. Preserve branch 6 and 10.
markers = {
    0: "\t\tElse If(Event Player.HalamanMenu == 0);",
    1: "\t\tElse If(Event Player.HalamanMenu == 1);",
    2: "\t\tElse If(Event Player.HalamanMenu == 2);",
    3: "\t\tElse If(Event Player.HalamanMenu == 3);",
    4: "\t\tElse If(Event Player.HalamanMenu == 4);",
    5: "\t\tElse If(Event Player.HalamanMenu == 5);",
    6: "\t\tElse If(Event Player.HalamanMenu == 6);",
    7: "\t\tElse If(Event Player.HalamanMenu == 7);",
    8: "\t\tElse If(Event Player.HalamanMenu == 8);",
    9: "\t\tElse If(Event Player.HalamanMenu == 9);",
    10: "\t\tElse If(Event Player.HalamanMenu == 10);",
}
# The final Else is Menu 11 / vote.
ordered = [markers[i] for i in range(11)]
removed_redraws = 0
for i in (9, 8, 7, 5, 4, 3, 2, 1, 0):
    start_marker = markers[i]
    end_marker = markers[i + 1]
    start, end, segment = branch_segment(rule, start_marker, end_marker)
    segment, removed = remove_calls(segment, "GambarMenu")
    removed_redraws += removed
    rule = rule[:start] + segment + rule[end:]
# Menu 11 follows Menu 10's closing End + final Else; remove only the last GambarMenu
# in the whole rule, while keeping the Menu 10 redraw immediately before it.
last_call = rule.rfind("\t\t\tCall Subroutine(GambarMenu);\n")
menu10_at = rule.index(markers[10])
if last_call <= menu10_at:
    raise RuntimeError("Menu 11 redraw not found after Menu 10")
rule = rule[:last_call] + rule[last_call + len("\t\t\tCall Subroutine(GambarMenu);\n"):]
removed_redraws += 1

if "Wait(0.016, Ignore Condition);" in rule:
    raise RuntimeError("Interact still contains a one-frame wait")
if rule.count("Call Subroutine(GambarMenu);") != 3:
    raise RuntimeError(f"Interact must keep exactly 3 targeted redraws, found {rule.count('Call Subroutine(GambarMenu);')}")
source = put_rule(source, name, rule)

# Crouch Teleport overlay: same immediate release and live cursor rendering.
name = "19b - Teleportasi Jongkok: Aktifkan lagi pengatur setelah tombol dilepas"
_, _, rule = get_rule(source, name)
rule = replace_once(rule, "\t\tWait(0.016, Ignore Condition);\n", "", "Crouch Teleport release wait")
source = put_rule(source, name, rule)

for name in (
    "19c - Teleportasi Jongkok: Tembakan utama memilih tujuan berikutnya",
    "19d - Teleportasi Jongkok: Tembakan sekunder memilih tujuan sebelumnya",
):
    _, _, rule = get_rule(source, name)
    rule = replace_once(rule, "\t\tCall Subroutine(GambarTeleportasi);\n", "", f"live overlay {name}")
    source = put_rule(source, name, rule)

# Post-teleport target/status expressions are already live; no need to recreate HUD.
name = "19e - Teleportasi Jongkok: Interact menjalankan teleportasi"
_, _, rule = get_rule(source, name)
rule = replace_once(
    rule,
    "\t\tIf(Event Player.TeleportasiJongkokAktif == True);\n\t\t\tCall Subroutine(GambarTeleportasi);\n\t\tEnd;\n",
    "",
    "post teleport redraw",
)
source = put_rule(source, name, rule)

# Keep the palette transition smooth but visibly quicker.
source = replace_once(
    source,
    ": Vector(255, 210, 70), 0.350, Destination and Duration);",
    ": Vector(255, 210, 70), 0.180, Destination and Duration);",
    "menu color transition duration",
)
SOURCE.write_text(source, encoding="utf-8")

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_once(validator, "della versione 0.6.7.", "della versione 0.6.8.", "validator docstring version")
validator = replace_once(validator, 'CURRENT_VERSION = "0.6.7"', 'CURRENT_VERSION = "0.6.8"', "validator current version")

old_release = '''    if release_candidates:\n        checks.require(\n            re.search(r"Wait\\s*\\(\\s*0\\.016\\s*,\\s*Ignore Condition\\s*\\)", release_candidates[0].body)\n            is not None,\n            "release gate dispatcher privo del tick di arbitraggio prima del reset",\n        )\n'''
new_release = '''    if release_candidates:\n        checks.require(\n            "Wait(" not in mask_strings(release_candidates[0].body),\n            "release gate dispatcher deve riarmarsi subito dopo il rilascio completo",\n        )\n'''
validator = replace_once(validator, old_release, new_release, "validator immediate release")

anchor = '''    for command in range(1, 7):\n        handlers = [\n            rule\n            for rule in rules\n            if code_contains(rule.body, f"Event Player.PerintahMenu == {command};")\n        ]\n        checks.equal(len(handlers), 1, f"handler dispatcher comando {command}")\n        if handlers:\n            checks.require(\n                "Event Player.PerintahMenu = 0;" not in handlers[0].body,\n                f"handler {command} resetta il dispatcher prima del rilascio di tutti gli input",\n            )\n'''
extra = anchor + '''\n    handler_by_command = {\n        command: next((rule for rule in rules if code_contains(rule.body, f"Event Player.PerintahMenu == {command};")), None)\n        for command in range(1, 7)\n    }\n    interact_handler = handler_by_command[1]\n    if interact_handler is not None:\n        interact_code = mask_strings(interact_handler.body)\n        checks.require("Wait(" not in interact_code, "Interact menu contiene ancora un Wait bloccante")\n        checks.equal(\n            interact_code.count("Call Subroutine(GambarMenu);"),\n            3,\n            "Interact deve ridisegnare solo Main->submenu, Voice apply e Try Your Luck",\n        )\n        checks.require(\n            code_contains(interact_handler.body, "Stop Modifying Hero Voice Lines(Event Player);"),\n            "Voice NORMAL deve restare applicabile nel ramo Menu 6",\n        )\n        checks.require(\n            code_contains(interact_handler.body, "Event Player.KartuNasibAktif = True;", "Call Subroutine(GambarMenu);"),\n            "Try Your Luck deve aggiornare esplicitamente READY -> ROLLING",\n        )\n    for label, command in (("Primary", 3), ("Secondary", 4)):\n        handler = handler_by_command[command]\n        if handler is not None:\n            checks.require(not code_contains(handler.body, "Call Subroutine(GambarMenu);"), f"{label}: redraw HUD inutile")\n            checks.require(code_contains(handler.body, "Call Subroutine(TransisiWarnaMenu);"), f"{label}: transizione colore leggera assente")\n    for label, command in (("Jump x10", 5), ("Crouch x10", 6)):\n        handler = handler_by_command[command]\n        if handler is not None:\n            checks.require(not code_contains(handler.body, "Call Subroutine(GambarMenu);"), f"{label}: redraw HUD inutile")\n\n    teleport_release = [rule for rule in rules if rule.name.startswith("19b - Teleportasi Jongkok:")]\n    checks.equal(len(teleport_release), 1, "release gate Crouch Teleport")\n    if teleport_release:\n        checks.require("Wait(" not in mask_strings(teleport_release[0].body), "Crouch Teleport release gate non immediato")\n    for prefix in ("19c - Teleportasi Jongkok:", "19d - Teleportasi Jongkok:"):\n        candidates = [rule for rule in rules if rule.name.startswith(prefix)]\n        checks.equal(len(candidates), 1, f"handler overlay {prefix}")\n        if candidates:\n            checks.require(not code_contains(candidates[0].body, "Call Subroutine(GambarTeleportasi);"), f"{prefix}: redraw HUD inutile")\n\n    transition_rules = rules_containing(rules, "Subroutine;", "TransisiWarnaMenu;")\n    checks.equal(len(transition_rules), 1, "subroutine TransisiWarnaMenu")\n    if transition_rules:\n        checks.require(\n            re.search(r"0\\.180\\s*,\\s*Destination and Duration", mask_strings(transition_rules[0].body)) is not None,\n            "transizione colore menu non impostata a 0,18 s",\n        )\n'''
validator = replace_once(validator, anchor, extra, "validator latency invariants")
validator = validator.replace("0\\.350", "0\\.180").replace("0.350", "0.180")
VALIDATOR.write_text(validator, encoding="utf-8")

VERSION.write_text("0.6.8\n", encoding="utf-8")

readme = README.read_text(encoding="utf-8")
readme = replace_once(readme, "La versione **0.6.7** identifica lo stato funzionale e tecnico corrente del repository.", "La versione **0.6.8** identifica lo stato funzionale e tecnico corrente del repository.", "README version")
readme = readme.replace("circa **0,35 s**", "circa **0,18 s**")
if "### Menu fluido 0.6.8" not in readme:
    readme += '''\n\n### Menu fluido 0.6.8\n\nLa navigazione riusa gli HUD con stringhe/colori rivalutati invece di distruggerli e ricrearli a ogni pressione. Primary/Secondary aggiornano cursore e transizione colore; Jump/Crouch nel Soundtrack aggiornano direttamente il cursore. Interact non contiene più attese da 0,016 s e ridisegna soltanto quando cambia renderer oppure nei due casi che richiedono un refresh esplicito dello stato applicato: Hero Voice e Try Your Luck. Anche Crouch Teleport elimina il frame di release e i redraw per ogni step. La transizione colore passa da circa 0,35 s a 0,18 s. Il hold Melee da 0,5 s resta intenzionale.\n'''
README.write_text(readme, encoding="utf-8")

progetto = PROGETTO.read_text(encoding="utf-8")
progetto = replace_once(progetto, "# Note di progetto — versione 0.6.7", "# Note di progetto — versione 0.6.8", "PROGETTO title")
progetto = replace_once(progetto, "Workshop 0.6.7.", "Workshop 0.6.8.", "PROGETTO version")
progetto = progetto.replace("0,35", "0,18")
if "## Ottimizzazione input menu 0.6.8" not in progetto:
    progetto += '''\n\n## Ottimizzazione input menu 0.6.8\n\nIl dispatcher resta chord-safe ma i release gate Menu Arcade/Crouch Teleport non attendono più 0,016 s. I cursor step sfruttano la rivalutazione live dell'HUD e non ricreano il testo. Interact Camera non inserisce più frame di attesa; i redraw Interact sono confinati a cambio renderer, Voice apply e Try Your Luck READY->ROLLING. La transizione colore è 0,18 s.\n'''
PROGETTO.write_text(progetto, encoding="utf-8")

test_doc = TEST_DOC.read_text(encoding="utf-8")
test_doc = replace_once(test_doc, "# Piano di test — versione 0.6.7", "# Piano di test — versione 0.6.8", "TEST title")
test_doc = replace_once(test_doc, "Workshop 0.6.7.", "Workshop 0.6.8.", "TEST version")
test_doc = test_doc.replace("0,35", "0,18")
if "## Menu fluido 0.6.8" not in test_doc:
    test_doc += '''\n\n## Menu fluido 0.6.8\n\nVerifica live: scorrere rapidamente Main Menu e ogni submenu con Primary/Secondary; applicare con Interact, tornare con Reload e usare Jump/Crouch nel Soundtrack. Verificare Hero Voice NORMAL e Try Your Luck: devono aggiornarsi subito. Camera dal menu non deve mostrare il precedente frame di attesa. Ripetere nell'overlay Crouch Teleport con Primary/Secondary/Interact. Melee 0,5 s resta volutamente invariato.\n'''
TEST_DOC.write_text(test_doc, encoding="utf-8")

validazione = VALIDAZIONE.read_text(encoding="utf-8")
validazione = replace_once(validazione, "# Rapporto di validazione — versione 0.6.7", "# Rapporto di validazione — versione 0.6.8", "VALIDAZIONE title")
validazione = replace_once(validazione, "Release tecnica: **CHILL Dedicated Server 0.6.7**", "Release tecnica: **CHILL Dedicated Server 0.6.8**", "VALIDAZIONE release")
validazione = replace_once(validazione, "OK - controlli statici v0.6.7 superati", "OK - controlli statici v0.6.8 superati", "VALIDAZIONE result")
if "## Ottimizzazione menu 0.6.8" not in validazione:
    validazione += '''\n\n## Ottimizzazione menu 0.6.8\n\nIl gate verifica release immediato, assenza di Wait nel percorso Interact, navigazione senza ricreazione HUD, redraw mirati per Voice/Try Your Luck e Crouch Teleport senza redraw per ogni cursor step. La transizione colore è fissata a 0,18 s.\n'''

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

print(f"Applied CHILL 0.6.8 fluid menu optimization; removed {removed_redraws} ordinary Interact redraws")
