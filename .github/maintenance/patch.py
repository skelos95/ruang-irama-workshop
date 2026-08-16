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


def remove_call_lines(rule: str, call: str, keep_first: bool = False) -> tuple[str, int]:
    pattern = re.compile(rf"(?m)^\s*Call Subroutine\({re.escape(call)}\);\n")
    matches = list(pattern.finditer(rule))
    removed = 0
    if keep_first and matches:
        matches = matches[1:]
    for match in reversed(matches):
        rule = rule[:match.start()] + rule[match.end():]
        removed += 1
    return rule, removed


source = SOURCE.read_text(encoding="utf-8")

# 1) Release gates: re-arm on the same evaluation where every button is released.
name = "05d - Menu: Lepaskan pengatur setelah semua masukan dilepas"
_, _, rule = get_rule(source, name)
rule = replace_once(
    rule,
    '\t\t"Tunda satu bingkai agar pengendali menyelesaikan perintah sebelum pengatur masukan diaktifkan kembali."\n\t\tWait(0.016, Ignore Condition);\n',
    '\t\t"Aktifkan kembali pengatur segera setelah semua tombol dilepas; latch tetap mencegah pengulangan saat tombol ditahan."\n',
    "Arcade release wait",
)
source = put_rule(source, name, rule)

# 2) Cursor navigation: HUD strings are reevaluated live, so do not destroy/recreate the HUD.
# Main menu and Name Color still need only the lightweight color-target chase update.
for name in (
    "06 - Menu: Tembakan utama memilih berikutnya",
    "07 - Menu: Tembakan sekunder memilih sebelumnya",
):
    _, _, rule = get_rule(source, name)
    rule = replace_once(
        rule,
        "\t\tCall Subroutine(GambarMenu);\n",
        "\t\tCall Subroutine(TransisiWarnaMenu);\n",
        f"lightweight navigation redraw {name}",
    )
    source = put_rule(source, name, rule)

for name in (
    "08 - Menu 0: Lompat mundur sepuluh genre",
    "09 - Menu 0: Jongkok maju sepuluh genre",
):
    _, _, rule = get_rule(source, name)
    rule = replace_once(
        rule,
        "\t\tCall Subroutine(GambarMenu);\n",
        "",
        f"remove genre redraw {name}",
    )
    source = put_rule(source, name, rule)

# 3) Interact: keep a full renderer switch only when opening a submenu.
# Applying a choice stays on the same renderer, whose String/Color are already live-reevaluated.
name = "10 - Menu: Interaksi membuka atau menerapkan pilihan"
_, _, rule = get_rule(source, name)
wait_count = rule.count("Wait(0.016, Ignore Condition);")
if wait_count != 2:
    raise RuntimeError(f"Interact camera: expected 2 one-frame waits, found {wait_count}")
rule = rule.replace(
    '\t\t\t\t\t"Biarkan satu bingkai Interact selesai sebelum mengganti tampilan kamera."\n\t\t\t\t\tWait(0.016, Ignore Condition);\n',
    '',
)
rule = rule.replace(
    '\t\t\t\t\t\t"Gunakan jeda satu bingkai yang sama saat mulai menonton dari orang pertama."\n\t\t\t\t\t\tWait(0.016, Ignore Condition);\n',
    '',
)
if "Wait(0.016, Ignore Condition);" in rule:
    raise RuntimeError("Interact menu still contains a one-frame wait")
rule, removed = remove_call_lines(rule, "GambarMenu", keep_first=True)
if removed < 8:
    raise RuntimeError(f"Interact optimization removed too few redundant redraws: {removed}")
if rule.count("Call Subroutine(GambarMenu);") != 1:
    raise RuntimeError("Interact must keep exactly one GambarMenu call for main -> submenu")
source = put_rule(source, name, rule)

# 4) Crouch Teleport overlay gets the same immediate release and live-HUD navigation.
name = "19b - Teleportasi Jongkok: Aktifkan lagi pengatur setelah tombol dilepas"
_, _, rule = get_rule(source, name)
rule = replace_once(
    rule,
    "\t\tWait(0.016, Ignore Condition);\n",
    "",
    "Crouch Teleport release wait",
)
source = put_rule(source, name, rule)

for name in (
    "19c - Teleportasi Jongkok: Tembakan utama memilih tujuan berikutnya",
    "19d - Teleportasi Jongkok: Tembakan sekunder memilih tujuan sebelumnya",
):
    _, _, rule = get_rule(source, name)
    rule = replace_once(
        rule,
        "\t\tCall Subroutine(GambarTeleportasi);\n",
        "",
        f"remove Crouch Teleport navigation redraw {name}",
    )
    source = put_rule(source, name, rule)

name = "19e - Teleportasi Jongkok: Interact menjalankan teleportasi"
_, _, rule = get_rule(source, name)
rule = replace_once(
    rule,
    "\t\tIf(Event Player.TeleportasiJongkokAktif == True);\n\t\t\tCall Subroutine(GambarTeleportasi);\n\t\tEnd;\n",
    "",
    "remove post-teleport redraw",
)
source = put_rule(source, name, rule)

# 5) Keep the smooth palette transition but make it substantially snappier.
source = replace_once(
    source,
    ": Vector(255, 210, 70), 0.350, Destination and Duration);",
    ": Vector(255, 210, 70), 0.180, Destination and Duration);",
    "menu color transition duration",
)
SOURCE.write_text(source, encoding="utf-8")

# Validator/version.
validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_once(validator, "della versione 0.6.7.", "della versione 0.6.8.", "validator docstring version")
validator = replace_once(validator, 'CURRENT_VERSION = "0.6.7"', 'CURRENT_VERSION = "0.6.8"', "validator current version")

old_release = '''    if release_candidates:\n        checks.require(\n            re.search(r"Wait\\s*\\(\\s*0\\.016\\s*,\\s*Ignore Condition\\s*\\)", release_candidates[0].body)\n            is not None,\n            "release gate dispatcher privo del tick di arbitraggio prima del reset",\n        )\n'''
new_release = '''    if release_candidates:\n        checks.require(\n            "Wait(" not in mask_strings(release_candidates[0].body),\n            "release gate dispatcher deve riarmarsi subito dopo il rilascio completo",\n        )\n'''
validator = replace_once(validator, old_release, new_release, "validator immediate release gate")

# Add structural latency checks after the six dispatcher handlers are validated.
anchor = '''    for command in range(1, 7):\n        handlers = [\n            rule\n            for rule in rules\n            if code_contains(rule.body, f"Event Player.PerintahMenu == {command};")\n        ]\n        checks.equal(len(handlers), 1, f"handler dispatcher comando {command}")\n        if handlers:\n            checks.require(\n                "Event Player.PerintahMenu = 0;" not in handlers[0].body,\n                f"handler {command} resetta il dispatcher prima del rilascio di tutti gli input",\n            )\n'''
extra = anchor + '''\n    handler_by_command = {\n        command: next(\n            (rule for rule in rules if code_contains(rule.body, f"Event Player.PerintahMenu == {command};")),\n            None,\n        )\n        for command in range(1, 7)\n    }\n    interact_handler = handler_by_command[1]\n    reload_handler = handler_by_command[2]\n    next_handler = handler_by_command[3]\n    previous_handler = handler_by_command[4]\n    jump_handler = handler_by_command[5]\n    crouch_handler = handler_by_command[6]\n    if interact_handler is not None:\n        interact_code = mask_strings(interact_handler.body)\n        checks.require("Wait(" not in interact_code, "Interact menu contiene ancora un Wait bloccante")\n        checks.equal(\n            interact_code.count("Call Subroutine(GambarMenu);"),\n            1,\n            "Interact deve ridisegnare solo nel passaggio Main -> submenu",\n        )\n    if reload_handler is not None:\n        checks.require(\n            code_contains(reload_handler.body, "Call Subroutine(GambarMenu);"),\n            "Reload deve ridisegnare nel passaggio submenu -> Main",\n        )\n    for label, handler in (("Primary", next_handler), ("Secondary", previous_handler)):\n        if handler is not None:\n            checks.require(\n                not code_contains(handler.body, "Call Subroutine(GambarMenu);"),\n                f"{label}: navigazione non deve distruggere/ricreare HUD",\n            )\n            checks.require(\n                code_contains(handler.body, "Call Subroutine(TransisiWarnaMenu);"),\n                f"{label}: aggiornamento colore leggero mancante",\n            )\n    for label, handler in (("Jump x10", jump_handler), ("Crouch x10", crouch_handler)):\n        if handler is not None:\n            checks.require(\n                not code_contains(handler.body, "Call Subroutine(GambarMenu);"),\n                f"{label}: navigazione non deve distruggere/ricreare HUD",\n            )\n\n    teleport_release = [\n        rule for rule in rules\n        if rule.name.startswith("19b - Teleportasi Jongkok:")\n    ]\n    checks.equal(len(teleport_release), 1, "release gate Crouch Teleport")\n    if teleport_release:\n        checks.require(\n            "Wait(" not in mask_strings(teleport_release[0].body),\n            "Crouch Teleport: release gate deve riarmarsi subito",\n        )\n    for prefix in (\n        "19c - Teleportasi Jongkok:",\n        "19d - Teleportasi Jongkok:",\n    ):\n        candidates = [rule for rule in rules if rule.name.startswith(prefix)]\n        checks.equal(len(candidates), 1, f"handler overlay {prefix}")\n        if candidates:\n            checks.require(\n                not code_contains(candidates[0].body, "Call Subroutine(GambarTeleportasi);"),\n                f"{prefix} non deve ridisegnare l'HUD a ogni cursor step",\n            )\n\n    transition_rules = rules_containing(rules, "Subroutine;", "TransisiWarnaMenu;")\n    checks.equal(len(transition_rules), 1, "subroutine TransisiWarnaMenu")\n    if transition_rules:\n        checks.require(\n            re.search(r"0\\.180\\s*,\\s*Destination and Duration", mask_strings(transition_rules[0].body)) is not None,\n            "transizione colore menu non impostata a 0,18 s",\n        )\n'''
validator = replace_once(validator, anchor, extra, "validator menu latency checks")

# Existing palette check follows the same new transition duration if it pins 0.350.
validator = validator.replace("0\\.350", "0\\.180")
validator = validator.replace("0.350", "0.180")
VALIDATOR.write_text(validator, encoding="utf-8")

VERSION.write_text("0.6.8\n", encoding="utf-8")

# Documentation.
readme = README.read_text(encoding="utf-8")
readme = replace_once(readme, "La versione **0.6.7** identifica lo stato funzionale e tecnico corrente del repository.", "La versione **0.6.8** identifica lo stato funzionale e tecnico corrente del repository.", "README version")
readme = readme.replace("circa **0,35 s**", "circa **0,18 s**")
if "### Menu fluido 0.6.8" not in readme:
    readme += '''\n\n### Menu fluido 0.6.8\n\nGli HUD dei menu usano già rivalutazione dinamica di stringa/colore, quindi la navigazione non distrugge e ricrea più l'HUD a ogni input. Primary/Secondary aggiornano soltanto cursore e target colore, Jump/Crouch del menu Soundtrack aggiornano direttamente il cursore, e Interact ridisegna soltanto quando cambia realmente renderer (Main -> submenu). Rimossi i `Wait(0.016)` dai release gate e dalla selezione Camera nel menu; anche l'overlay Crouch Teleport riutilizza l'HUD live senza redraw per ogni step. La transizione colore resta morbida ma passa da circa 0,35 s a 0,18 s. Il hold Melee da 0,5 s resta intenzionale per evitare aperture/chiusure accidentali.\n'''
README.write_text(readme, encoding="utf-8")

progetto = PROGETTO.read_text(encoding="utf-8")
progetto = replace_once(progetto, "# Note di progetto — versione 0.6.7", "# Note di progetto — versione 0.6.8", "PROGETTO title")
progetto = replace_once(progetto, "Workshop 0.6.7.", "Workshop 0.6.8.", "PROGETTO current version")
progetto = progetto.replace("0,35", "0,18")
if "## Ottimizzazione input menu 0.6.8" not in progetto:
    progetto += '''\n\n## Ottimizzazione input menu 0.6.8\n\nLa pipeline input mantiene il dispatcher chord-safe, ma elimina i ritardi artificiali: i release gate Menu Arcade/Crouch Teleport non aspettano più 0,016 s e Interact Camera non inserisce più frame di attesa. Gli HUD menu sono `Visible To String and Color`, quindi cursor/status vengono rivalutati senza distruggere e ricreare il testo: `GambarMenu` resta necessario solo quando cambia renderer (Main/submenu), mentre la navigazione usa al massimo `TransisiWarnaMenu`. La durata della transizione colore scende a 0,18 s.\n'''
PROGETTO.write_text(progetto, encoding="utf-8")

test_doc = TEST_DOC.read_text(encoding="utf-8")
test_doc = replace_once(test_doc, "# Piano di test — versione 0.6.7", "# Piano di test — versione 0.6.8", "TEST title")
test_doc = replace_once(test_doc, "Workshop 0.6.7.", "Workshop 0.6.8.", "TEST current version")
test_doc = test_doc.replace("0,35", "0,18")
if "## Menu fluido 0.6.8" not in test_doc:
    test_doc += '''\n\n## Menu fluido 0.6.8\n\nVerifica live: scorrere rapidamente Main Menu e ogni submenu con Primary/Secondary, applicare ripetutamente con Interact dopo ogni rilascio, tornare con Reload e usare Jump/Crouch nel Soundtrack. Non devono comparire micro-pause o input persi. Camera da Menu deve cambiare immediatamente senza il precedente frame da 0,016 s. Verificare anche l'overlay Crouch Teleport con Primary/Secondary/Interact. La pressione lunga Melee da 0,5 s resta volutamente invariata.\n'''
TEST_DOC.write_text(test_doc, encoding="utf-8")

validazione = VALIDAZIONE.read_text(encoding="utf-8")
validazione = replace_once(validazione, "# Rapporto di validazione — versione 0.6.7", "# Rapporto di validazione — versione 0.6.8", "VALIDAZIONE title")
validazione = replace_once(validazione, "Release tecnica: **CHILL Dedicated Server 0.6.7**", "Release tecnica: **CHILL Dedicated Server 0.6.8**", "VALIDAZIONE release")
validazione = replace_once(validazione, "OK - controlli statici v0.6.7 superati", "OK - controlli statici v0.6.8 superati", "VALIDAZIONE result")
if "## Ottimizzazione menu 0.6.8" not in validazione:
    validazione += '''\n\n## Ottimizzazione menu 0.6.8\n\nIl gate certifica che i release gate Menu/Teleport non contengano `Wait`, che Interact Menu non contenga attese e ridisegni solo nel passaggio Main -> submenu, che Primary/Secondary usino il solo aggiornamento leggero del colore senza `GambarMenu`, che Jump/Crouch Soundtrack e la navigazione Crouch Teleport non ridisegnino l'HUD a ogni step, e che la transizione colore sia 0,18 s.\n'''

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

print(f"Applied CHILL 0.6.8 fluid menu optimization; removed {removed} redundant Interact redraws")
