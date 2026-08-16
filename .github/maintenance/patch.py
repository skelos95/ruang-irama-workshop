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

RENDERERS = [
    (-1, "GambarUtama"),
    (0, "GambarMusik"),
    (1, "GambarKamera"),
    (2, "GambarWarna"),
    (3, "GambarBahasa"),
    (4, "GambarBalasDendam"),
    (5, "GambarKebal"),
    (6, "GambarSuara"),
    (7, "GambarIkon"),
    (8, "GambarSakelarTeleportasi"),
    (9, "GambarPrivasiInspeksi"),
    (10, "GambarNasib"),
    (11, "GambarPilihan"),
]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected 1 occurrence, found {count}")
    return text.replace(old, new, 1)


def mask_strings(text: str) -> str:
    out: list[str] = []
    quoted = False
    escaped = False
    for ch in text:
        if quoted:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                quoted = False
            out.append("\n" if ch == "\n" else " ")
        elif ch == '"':
            quoted = True
            out.append(" ")
        else:
            out.append(ch)
    if quoted:
        raise RuntimeError("unclosed string")
    return "".join(out)


def matching(text: str, opening: int, left: str, right: str) -> int:
    clean = mask_strings(text)
    depth = 1
    for i in range(opening + 1, len(clean)):
        if clean[i] == left:
            depth += 1
        elif clean[i] == right:
            depth -= 1
            if depth == 0:
                return i
    raise RuntimeError(f"unclosed {left}")


def rule_spans(text: str):
    for match in re.finditer(r'^rule\("([^"]+)"\)\s*\{', text, re.M):
        opening = text.find("{", match.start(), match.end())
        end = matching(text, opening, "{", "}") + 1
        yield match.group(1), match.start(), end, text[match.start():end]


def get_rule(text: str, name: str):
    for rule_name, start, end, rule in rule_spans(text):
        if rule_name == name:
            return start, end, rule
    raise RuntimeError(f"rule not found: {name}")


def find_subroutine_rule(text: str, subroutine: str):
    found = []
    for name, start, end, rule in rule_spans(text):
        clean = mask_strings(rule)
        if "Subroutine;" in clean and re.search(rf'(?m)^\s*{re.escape(subroutine)}\s*;', clean):
            found.append((name, start, end, rule))
    if len(found) != 1:
        raise RuntimeError(f"subroutine {subroutine}: expected 1 rule, found {len(found)}")
    return found[0]


def replace_rule(text: str, start: int, end: int, rule: str) -> str:
    return text[:start] + rule + text[end:]


def replace_actions(rule: str, actions: str) -> str:
    clean = mask_strings(rule)
    match = re.search(r'(?m)^\s*actions\s*\{', clean)
    if match is None:
        raise RuntimeError("actions block missing")
    opening = clean.find("{", match.start())
    closing = matching(rule, opening, "{", "}")
    return rule[:opening + 1] + "\n" + actions.rstrip() + "\n\t" + rule[closing:]


def replace_first_arg_of_only_hud(rule: str, expression: str) -> str:
    clean = mask_strings(rule)
    marker = "Create HUD Text("
    at = clean.find(marker)
    if at < 0 or clean.find(marker, at + 1) >= 0:
        raise RuntimeError("renderer must have exactly one Create HUD Text")
    opening = clean.find("(", at)
    depth = 0
    quoted = False
    escaped = False
    comma = None
    for i in range(opening + 1, len(rule)):
        ch = rule[i]
        if quoted:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                quoted = False
            continue
        if ch == '"':
            quoted = True
        elif ch in "([{" :
            depth += 1
        elif ch in ")]}":
            if depth == 0:
                raise RuntimeError("HUD first argument ended before comma")
            depth -= 1
        elif ch == "," and depth == 0:
            comma = i
            break
    if comma is None:
        raise RuntimeError("HUD first argument comma missing")
    return rule[:opening + 1] + expression + rule[comma:]


def cleanup_lines(owner: str, array_expr: str, indent: str = "\t\t") -> str:
    lines = []
    for index in range(13):
        lines.extend([
            f"{indent}If(Count Of({array_expr}) > {index});",
            f"{indent}\tDestroy HUD Text({array_expr}[{index}]);",
            f"{indent}End;",
        ])
    lines.append(f"{indent}{owner}.HudMenuArcade = Empty Array;")
    return "\n".join(lines)


source = SOURCE.read_text(encoding="utf-8")

source = replace_once(
    source,
    "\t\t87: GerakNasibDikunci\n",
    "\t\t87: GerakNasibDikunci\n\t\t88: HudMenuArcade\n",
    "player variable HudMenuArcade",
)

_, setup_start, setup_end, setup_rule = find_subroutine_rule(source, "SiapkanPemain")
setup_rule = replace_once(
    setup_rule,
    "\t\tEvent Player.HudMenu = Null;\n",
    "\t\tEvent Player.HudMenu = Null;\n\t\tEvent Player.HudMenuArcade = Empty Array;\n",
    "SiapkanPemain HudMenuArcade init",
)
source = replace_rule(source, setup_start, setup_end, setup_rule)

for page, subroutine in RENDERERS:
    _, start, end, rule = find_subroutine_rule(source, subroutine)
    if "Destroy HUD Text(Event Player.HudMenu);" in mask_strings(rule):
        raise RuntimeError(f"{subroutine}: unexpected destructive HUD preamble")
    visible = f"And(Event Player.MenuTerbuka == True, Event Player.HalamanMenu == {page}) ? Event Player : Empty Array"
    rule = replace_first_arg_of_only_hud(rule, visible)
    marker = "\t\tEvent Player.HudMenu = Last Text ID;\n"
    replacement = (
        marker
        + "\t\tEvent Player.HudMenuArcade = Append To Array(Event Player.HudMenuArcade, Event Player.HudMenu);\n"
        + "\t\tEvent Player.HudMenu = Null;\n"
    )
    rule = replace_once(rule, marker, replacement, f"{subroutine} store persistent HUD")
    source = replace_rule(source, start, end, rule)

router_name = "91 - Subrutin: Pilih gambar menu yang sedang dibuka"
router_start, router_end, router = get_rule(source, router_name)
calls = "\n".join(f"\t\t\tCall Subroutine({subroutine});" for _, subroutine in RENDERERS)
router_actions = f'''\t\tCall Subroutine(TransisiWarnaMenu);
\t\tIf(Count Of(Event Player.HudMenuArcade) == 0);
{calls}
\t\tEnd;
\t\tIf(Index Of Array Value(Global.PemainManusia, Event Player) >= 0);
\t\t\tGlobal.HudMenuPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = Count Of(Event Player.HudMenuArcade) > 0 ? First Of(Event Player.HudMenuArcade) : 0;
\t\tEnd;'''
router = replace_actions(router, router_actions)
source = replace_rule(source, router_start, router_end, router)

_, close_start, close_end, close_rule = find_subroutine_rule(source, "TutupMenu")
old_close = '''\t\tIf(Event Player.HudMenu != Null);\n\t\t\tDestroy HUD Text(Event Player.HudMenu);\n\t\tEnd;\n\t\tIf(Index Of Array Value(Global.PemainManusia, Event Player) >= 0);\n\t\t\tGlobal.HudMenuPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = 0;\n\t\tEnd;\n\t\tEvent Player.HudMenu = Null;\n'''
new_close = cleanup_lines("Event Player", "Event Player.HudMenuArcade") + '''\n\t\tIf(Event Player.HudMenu != Null);\n\t\t\tDestroy HUD Text(Event Player.HudMenu);\n\t\tEnd;\n\t\tIf(Index Of Array Value(Global.PemainManusia, Event Player) >= 0);\n\t\t\tGlobal.HudMenuPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = 0;\n\t\tEnd;\n\t\tEvent Player.HudMenu = Null;\n'''
close_rule = replace_once(close_rule, old_close, new_close, "TutupMenu split HUD cleanup")
source = replace_rule(source, close_start, close_end, close_rule)

_, cleanup_start, cleanup_end, cleanup_rule = find_subroutine_rule(source, "BersihkanPemain")
old_leave_menu = '''\t\t\tIf(Global.HudMenuPemain[Global.IndeksKeluar] != 0);\n\t\t\t\tDestroy HUD Text(Global.HudMenuPemain[Global.IndeksKeluar]);\n\t\t\tEnd;\n'''
leave_cleanup = cleanup_lines(
    "Global.PemainPembersihan",
    "Player Variable(Global.PemainPembersihan, HudMenuArcade)",
    "\t\t\t",
) + "\n"
cleanup_rule = replace_once(cleanup_rule, old_leave_menu, leave_cleanup, "BersihkanPemain split HUD cleanup")
source = replace_rule(source, cleanup_start, cleanup_end, cleanup_rule)

_, _, router = get_rule(source, router_name)
router_clean = mask_strings(router)
if "Create HUD Text" in router_clean or "Custom String" in router_clean:
    raise RuntimeError("GambarMenu is still monolithic")
if len(router.encode("utf-8")) > 12_000:
    raise RuntimeError(f"GambarMenu source unexpectedly large: {len(router.encode('utf-8'))} bytes")
for _, subroutine in RENDERERS:
    if f"Call Subroutine({subroutine});" not in router_clean:
        raise RuntimeError(f"GambarMenu missing split renderer call {subroutine}")

SOURCE.write_text(source, encoding="utf-8")

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_once(validator, "della versione 0.6.9.", "della versione 0.6.10.", "validator doc version")
validator = replace_once(validator, 'CURRENT_VERSION = "0.6.9"', 'CURRENT_VERSION = "0.6.10"', "validator current version")

block_start = validator.index("    expected_renderers = {")
block_end = validator.index("    dispatcher_candidates = [", block_start)
new_validator_block = '''    expected_renderers = {
        "GambarUtama", "GambarMusik", "GambarKamera", "GambarWarna", "GambarBahasa",
        "GambarBalasDendam", "GambarKebal", "GambarSuara", "GambarIkon",
        "GambarSakelarTeleportasi", "GambarPrivasiInspeksi", "GambarNasib", "GambarPilihan",
    }
    page_by_renderer = {
        "GambarUtama": -1,
        "GambarMusik": 0,
        "GambarKamera": 1,
        "GambarWarna": 2,
        "GambarBahasa": 3,
        "GambarBalasDendam": 4,
        "GambarKebal": 5,
        "GambarSuara": 6,
        "GambarIkon": 7,
        "GambarSakelarTeleportasi": 8,
        "GambarPrivasiInspeksi": 9,
        "GambarNasib": 10,
        "GambarPilihan": 11,
    }
    missing_renderers = sorted(expected_renderers - subroutines)
    checks.require(not missing_renderers, f"renderer menu mancanti: {missing_renderers}")
    checks.require(
        re.search(r"(?m)^\\s*88:\\s*HudMenuArcade\\s*$", source) is not None,
        "array HudMenuArcade non dichiarato",
    )
    router_rules = rules_containing(rules, "Subroutine;", "GambarMenu;")
    checks.equal(len(router_rules), 1, "router split GambarMenu")
    if router_rules:
        router = router_rules[0].body
        router_code = mask_strings(router)
        checks.require("Create HUD Text" not in router_code, "GambarMenu non deve contenere un HUD monolitico")
        checks.require("Custom String" not in router_code, "GambarMenu non deve duplicare i testi delle pagine")
        checks.require(
            "HudMenuArcade" in router_code and "TransisiWarnaMenu" in router_code,
            "GambarMenu non usa il gate di creazione split",
        )
        checks.require(len(router.encode("utf-8")) < 12000, "GambarMenu è tornato troppo grande")
        for renderer in sorted(expected_renderers):
            checks.require(f"Call Subroutine({renderer});" in router_code, f"GambarMenu non inizializza {renderer}")

    for renderer, page in page_by_renderer.items():
        candidates = rules_containing(rules, "Subroutine;", f"{renderer};")
        checks.equal(len(candidates), 1, f"renderer split {renderer}")
        if candidates:
            body = candidates[0].body
            huds = call_texts(body, "Create HUD Text")
            checks.equal(len(huds), 1, f"HUD split {renderer}")
            if huds:
                checks.require(
                    f"Event Player.HalamanMenu == {page}" in huds[0]
                    and "Event Player.MenuTerbuka == True" in huds[0]
                    and "Visible To String and Color" in huds[0],
                    f"{renderer}: visibilità pagina non rivalutata",
                )
            checks.require(
                code_contains(
                    body,
                    "Event Player.HudMenuArcade = Append To Array(Event Player.HudMenuArcade, Event Player.HudMenu);",
                    "Event Player.HudMenu = Null;",
                ),
                f"{renderer}: ID HUD non salvato nell'array split",
            )

    close_rules = rules_containing(rules, "Subroutine;", "TutupMenu;")
    checks.equal(len(close_rules), 1, "cleanup Menu Arcade split")
    if close_rules:
        close_code = mask_strings(close_rules[0].body)
        checks.require("Event Player.HudMenuArcade = Empty Array;" in close_code, "TutupMenu non svuota HudMenuArcade")
        checks.require(close_code.count("Destroy HUD Text(Event Player.HudMenuArcade[") == 13, "TutupMenu non distrugge tutte le 13 pagine HUD")

'''
validator = validator[:block_start] + new_validator_block + validator[block_end:]
VALIDATOR.write_text(validator, encoding="utf-8")

VERSION.write_text("0.6.10\n", encoding="utf-8")

readme = README.read_text(encoding="utf-8")
readme = replace_once(readme, "La versione **0.6.9** identifica lo stato funzionale e tecnico corrente del repository.", "La versione **0.6.10** identifica lo stato funzionale e tecnico corrente del repository.", "README version")
readme += '''\n\n### Riduzione limiti Workshop 0.6.10\n\nLa 0.6.9 aveva reso `GambarMenu` un HUD monolitico con tutte le 13 viste duplicate nella stessa regola; il client ha misurato **124 KB**, oltre il limite Workshop di **98 KB**, con **25.654 elementi** totali. La 0.6.10 elimina quella duplicazione: `GambarMenu` torna a essere un router piccolo e inizializza una volta, per ogni apertura, i 13 renderer già esistenti. Ogni HUD è visibile solo quando `MenuTerbuka` e `HalamanMenu` corrispondono alla sua pagina, quindi `Interact`/`Reload` cambiano pagina senza Destroy/Create. Alla chiusura tutti i 13 HUD vengono distrutti e l'array viene svuotato.\n'''
README.write_text(readme, encoding="utf-8")

progetto = PROGETTO.read_text(encoding="utf-8")
progetto = replace_once(progetto, "# Note di progetto — versione 0.6.9", "# Note di progetto — versione 0.6.10", "PROGETTO title")
progetto = replace_once(progetto, "Workshop 0.6.9.", "Workshop 0.6.10.", "PROGETTO version")
progetto += '''\n\n## Menu split e limite regola 0.6.10\n\n`GambarMenu` non contiene più testi o `Create HUD Text`: chiama i 13 renderer solo quando `HudMenuArcade` è vuoto. I renderer salvano i propri Text ID nell'array e usano rivalutazione `Visible To String and Color` con `MenuTerbuka + HalamanMenu`. Questo mantiene il cambio pagina immediato senza concentrare l'intero menu in una regola da 124 KB.\n'''
PROGETTO.write_text(progetto, encoding="utf-8")

test_doc = TEST_DOC.read_text(encoding="utf-8")
test_doc = replace_once(test_doc, "# Piano di test — versione 0.6.9", "# Piano di test — versione 0.6.10", "TEST title")
test_doc = replace_once(test_doc, "Workshop 0.6.9.", "Workshop 0.6.10.", "TEST version")
test_doc += '''\n\n## Diagnostica limiti Workshop 0.6.10\n\nDopo l'importazione aprire `Script Diagnostics`: **Size of Largest Rule deve risultare sotto 98 KB** e il Total Element Count deve rimanere sotto 32.768. Poi aprire il Menu Arcade e provare rapidamente Primary/Secondary -> Interact -> Reload su tutte le pagine: il cambio pagina deve restare immediato e senza flash. Chiudere/riaprire il menu più volte per verificare che gli HUD non si accumulino.\n'''
TEST_DOC.write_text(test_doc, encoding="utf-8")

validazione = VALIDAZIONE.read_text(encoding="utf-8")
validazione = replace_once(validazione, "# Rapporto di validazione — versione 0.6.9", "# Rapporto di validazione — versione 0.6.10", "VALIDAZIONE title")
validazione = replace_once(validazione, "Release tecnica: **CHILL Dedicated Server 0.6.9**", "Release tecnica: **CHILL Dedicated Server 0.6.10**", "VALIDAZIONE release")
validazione = replace_once(validazione, "OK - controlli statici v0.6.9 superati", "OK - controlli statici v0.6.10 superati", "VALIDAZIONE result")
validazione += '''\n\n## Limite regola Workshop 0.6.10\n\nIl gate impedisce il ritorno del renderer monolitico: `GambarMenu` non può contenere `Create HUD Text` o testi delle pagine, deve restare sotto 12 KB di sorgente e deve inizializzare i 13 renderer split. Ogni renderer deve avere visibilità rivalutata sulla propria `HalamanMenu` e registrare il Text ID in `HudMenuArcade`; `TutupMenu` deve distruggere tutte le 13 pagine. Il valore definitivo del limite compilato resta da verificare nel `Script Diagnostics` del client Overwatch.\n'''

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
    raise RuntimeError("VALIDAZIONE blob marker not found")
VALIDAZIONE.write_text(validazione, encoding="utf-8")

print("Applied CHILL 0.6.10 split Arcade HUD / Workshop limit reduction")
