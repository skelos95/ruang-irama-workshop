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


source = SOURCE.read_text(encoding="utf-8")

# Cache parallela: una voce per ogni pagina HUD realmente creata durante l'apertura corrente.
source = replace_once(
    source,
    "\t\t88: HudMenuArcade\n",
    "\t\t88: HudMenuArcade\n\t\t89: HalamanHudMenuArcade\n",
    "player variable HalamanHudMenuArcade",
)

# Inizializzazione giocatore.
_, setup_start, setup_end, setup_rule = find_subroutine_rule(source, "SiapkanPemain")
setup_rule = replace_once(
    setup_rule,
    "\t\tEvent Player.HudMenuArcade = Empty Array;\n",
    "\t\tEvent Player.HudMenuArcade = Empty Array;\n\t\tEvent Player.HalamanHudMenuArcade = Empty Array;\n",
    "SiapkanPemain lazy page cache init",
)
source = replace_rule(source, setup_start, setup_end, setup_rule)

# Ogni renderer registra anche il codice pagina corrispondente.
for page, subroutine in RENDERERS:
    _, start, end, rule = find_subroutine_rule(source, subroutine)
    marker = (
        "\t\tEvent Player.HudMenuArcade = Append To Array(Event Player.HudMenuArcade, Event Player.HudMenu);\n"
        "\t\tEvent Player.HudMenu = Null;\n"
    )
    replacement = (
        "\t\tEvent Player.HudMenuArcade = Append To Array(Event Player.HudMenuArcade, Event Player.HudMenu);\n"
        f"\t\tEvent Player.HalamanHudMenuArcade = Append To Array(Event Player.HalamanHudMenuArcade, {page});\n"
        "\t\tEvent Player.HudMenu = Null;\n"
    )
    rule = replace_once(rule, marker, replacement, f"{subroutine} lazy page registration")
    source = replace_rule(source, start, end, rule)

# GambarMenu crea solo la pagina richiesta se non è già nella cache.
router_name = "91 - Subrutin: Pilih gambar menu yang sedang dibuka"
router_start, router_end, router = get_rule(source, router_name)
branch_lines: list[str] = []
for i, (page, subroutine) in enumerate(RENDERERS):
    keyword = "If" if i == 0 else "Else If"
    branch_lines.append(f"\t\t\t{keyword}(Event Player.HalamanMenu == {page});")
    branch_lines.append(f"\t\t\t\tCall Subroutine({subroutine});")
branch_lines.append("\t\t\tEnd;")
branches = "\n".join(branch_lines)
router_actions = f'''\t\tCall Subroutine(TransisiWarnaMenu);
\t\tIf(Array Contains(Event Player.HalamanHudMenuArcade, Event Player.HalamanMenu) == False);
{branches}
\t\tEnd;
\t\tIf(Index Of Array Value(Global.PemainManusia, Event Player) >= 0);
\t\t\tGlobal.HudMenuPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = Count Of(Event Player.HudMenuArcade) > 0 ? First Of(Event Player.HudMenuArcade) : 0;
\t\tEnd;'''
router = replace_actions(router, router_actions)
source = replace_rule(source, router_start, router_end, router)

# Chiusura menu: reset anche della cache pagine.
_, close_start, close_end, close_rule = find_subroutine_rule(source, "TutupMenu")
close_rule = replace_once(
    close_rule,
    "\t\tEvent Player.HudMenuArcade = Empty Array;\n",
    "\t\tEvent Player.HudMenuArcade = Empty Array;\n\t\tEvent Player.HalamanHudMenuArcade = Empty Array;\n",
    "TutupMenu lazy page cache reset",
)
source = replace_rule(source, close_start, close_end, close_rule)

# Pulizia giocatore uscito: reset parallelo alla cache HUD.
_, cleanup_start, cleanup_end, cleanup_rule = find_subroutine_rule(source, "BersihkanPemain")
cleanup_rule = replace_once(
    cleanup_rule,
    "\t\t\tGlobal.PemainPembersihan.HudMenuArcade = Empty Array;\n",
    "\t\t\tGlobal.PemainPembersihan.HudMenuArcade = Empty Array;\n\t\t\tGlobal.PemainPembersihan.HalamanHudMenuArcade = Empty Array;\n",
    "BersihkanPemain lazy page cache reset",
)
source = replace_rule(source, cleanup_start, cleanup_end, cleanup_rule)

# Sanity sulla regola Melee: il timer resta esattamente 0,5 s e subito dopo apre via router lazy.
melee_name = "05 - Menu: Tahan serangan jarak dekat 0,5 detik untuk buka atau tutup"
_, _, melee_rule = get_rule(source, melee_name)
melee_code = mask_strings(melee_rule)
if "Wait(0.500, Abort When False);" not in melee_code:
    raise RuntimeError("Melee hold timer changed unexpectedly")
if "Call Subroutine(GambarMenu);" not in melee_code:
    raise RuntimeError("Melee no longer opens through GambarMenu")

_, _, router = get_rule(source, router_name)
router_code = mask_strings(router)
if "Array Contains(Event Player.HalamanHudMenuArcade, Event Player.HalamanMenu) == False" not in router_code:
    raise RuntimeError("lazy page gate missing")
if "Count Of(Event Player.HudMenuArcade) == 0" in router_code:
    raise RuntimeError("eager all-pages gate still present")
if len(router.encode("utf-8")) > 12_000:
    raise RuntimeError("lazy router unexpectedly large")

SOURCE.write_text(source, encoding="utf-8")

# Validator 0.6.11.
validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_once(validator, "della versione 0.6.10.", "della versione 0.6.11.", "validator doc version")
validator = replace_once(validator, 'CURRENT_VERSION = "0.6.10"', 'CURRENT_VERSION = "0.6.11"', "validator current version")

validator = replace_once(
    validator,
    '''    checks.require(
        re.search(r"(?m)^\\s*88:\\s*HudMenuArcade\\s*$", source) is not None,
        "array HudMenuArcade non dichiarato",
    )
''',
    '''    checks.require(
        re.search(r"(?m)^\\s*88:\\s*HudMenuArcade\\s*$", source) is not None,
        "array HudMenuArcade non dichiarato",
    )
    checks.require(
        re.search(r"(?m)^\\s*89:\\s*HalamanHudMenuArcade\\s*$", source) is not None,
        "cache HalamanHudMenuArcade non dichiarata",
    )
''',
    "validator cache declaration",
)

old_router_gate = '''        checks.require(
            "HudMenuArcade" in router_code and "TransisiWarnaMenu" in router_code,
            "GambarMenu non usa il gate di creazione split",
        )
        checks.require(len(router.encode("utf-8")) < 12000, "GambarMenu è tornato troppo grande")
        for renderer in sorted(expected_renderers):
            checks.require(f"Call Subroutine({renderer});" in router_code, f"GambarMenu non inizializza {renderer}")
'''
new_router_gate = '''        checks.require(
            "HalamanHudMenuArcade" in router_code
            and "Array Contains" in router_code
            and "TransisiWarnaMenu" in router_code,
            "GambarMenu non usa il gate lazy per pagina",
        )
        checks.require(
            "Count Of(Event Player.HudMenuArcade) == 0" not in router_code,
            "GambarMenu non deve pre-caricare tutte le pagine all'apertura",
        )
        checks.require(len(router.encode("utf-8")) < 12000, "GambarMenu è tornato troppo grande")
        for renderer, page in page_by_renderer.items():
            checks.require(f"Event Player.HalamanMenu == {page}" in router_code, f"GambarMenu non instrada pagina {page}")
            checks.require(f"Call Subroutine({renderer});" in router_code, f"GambarMenu non inizializza {renderer} on demand")
'''
validator = replace_once(validator, old_router_gate, new_router_gate, "validator lazy router")

old_renderer_check = '''            checks.require(
                code_contains(
                    body,
                    "Event Player.HudMenuArcade = Append To Array(Event Player.HudMenuArcade, Event Player.HudMenu);",
                    "Event Player.HudMenu = Null;",
                ),
                f"{renderer}: ID HUD non salvato nell'array split",
            )
'''
new_renderer_check = '''            checks.require(
                code_contains(
                    body,
                    "Event Player.HudMenuArcade = Append To Array(Event Player.HudMenuArcade, Event Player.HudMenu);",
                    f"Event Player.HalamanHudMenuArcade = Append To Array(Event Player.HalamanHudMenuArcade, {page});",
                    "Event Player.HudMenu = Null;",
                ),
                f"{renderer}: ID/pagina HUD non salvati nella cache lazy",
            )
'''
validator = replace_once(validator, old_renderer_check, new_renderer_check, "validator lazy renderer cache")

old_close_check = '''        checks.require("Event Player.HudMenuArcade = Empty Array;" in close_code, "TutupMenu non svuota HudMenuArcade")
        checks.require(close_code.count("Destroy HUD Text(Event Player.HudMenuArcade[") == 13, "TutupMenu non distrugge tutte le 13 pagine HUD")
'''
new_close_check = '''        checks.require("Event Player.HudMenuArcade = Empty Array;" in close_code, "TutupMenu non svuota HudMenuArcade")
        checks.require("Event Player.HalamanHudMenuArcade = Empty Array;" in close_code, "TutupMenu non svuota la cache pagine")
        checks.require(close_code.count("Destroy HUD Text(Event Player.HudMenuArcade[") == 13, "TutupMenu non distrugge tutte le pagine HUD caricate")
'''
validator = replace_once(validator, old_close_check, new_close_check, "validator lazy close cache")

# Invariante specifica sulla soglia Melee: 0,5 s deve restare il solo tempo intenzionale prima dell'apertura.
insert_at = validator.index("    dispatcher_candidates = [")
melee_validator = '''    melee_openers = [
        rule for rule in rules
        if code_contains(
            rule.body,
            "Is Button Held(Event Player, Button(Melee)) == True;",
            "Wait(0.500, Abort When False);",
            "Call Subroutine(GambarMenu);",
        )
        and code_contains(rule.body, "Event Player.MenuTerbuka = True;")
    ]
    checks.equal(len(melee_openers), 1, "apertura Menu Arcade con hold Melee 0,5 s")
    if melee_openers:
        melee_code = mask_strings(melee_openers[0].body)
        checks.equal(melee_code.count("Wait("), 1, "Melee opener deve avere un solo Wait")
        checks.require(
            "Wait(0.500, Abort When False);" in melee_code,
            "Melee opener non usa esattamente 0,5 s",
        )

'''
validator = validator[:insert_at] + melee_validator + validator[insert_at:]
VALIDATOR.write_text(validator, encoding="utf-8")

VERSION.write_text("0.6.11\n", encoding="utf-8")

# Docs.
readme = README.read_text(encoding="utf-8")
readme = replace_once(readme, "La versione **0.6.10** identifica lo stato funzionale e tecnico corrente del repository.", "La versione **0.6.11** identifica lo stato funzionale e tecnico corrente del repository.", "README version")
readme += '''\n\n### Apertura Melee immediata dopo 0,5 s — 0.6.11\n\nIl `Wait(0.500, Abort When False)` resta invariato: la soglia di hold non viene accorciata. Il ritardo extra osservato live dipendeva dal fatto che allo scadere dei 0,5 s `GambarMenu` creava tutte le 13 pagine HUD in sequenza. Ora il router usa una cache lazy (`HalamanHudMenuArcade`): all'apertura crea soltanto il Main Menu; ogni submenu viene creato soltanto al primo accesso e poi riutilizzato fino alla chiusura. `Reload` verso il Main e i ritorni a pagine già visitate non ricreano HUD.\n'''
README.write_text(readme, encoding="utf-8")

progetto = PROGETTO.read_text(encoding="utf-8")
progetto = replace_once(progetto, "# Note di progetto — versione 0.6.10", "# Note di progetto — versione 0.6.11", "PROGETTO title")
progetto = replace_once(progetto, "Workshop 0.6.10.", "Workshop 0.6.11.", "PROGETTO version")
progetto += '''\n\n## Lazy loading Menu Arcade 0.6.11\n\nLa soglia Melee rimane esattamente 0,5 s. `GambarMenu` non pre-carica più 13 HUD alla prima apertura: verifica `HalamanHudMenuArcade` e crea solo la pagina corrente se non è già presente. L'array degli ID HUD e l'array dei codici pagina vengono svuotati insieme alla chiusura o alla pulizia del giocatore.\n'''
PROGETTO.write_text(progetto, encoding="utf-8")

test_doc = TEST_DOC.read_text(encoding="utf-8")
test_doc = replace_once(test_doc, "# Piano di test — versione 0.6.10", "# Piano di test — versione 0.6.11", "TEST title")
test_doc = replace_once(test_doc, "Workshop 0.6.10.", "Workshop 0.6.11.", "TEST version")
test_doc += '''\n\n## Hold Melee 0,5 s / lazy loading 0.6.11\n\nTest live con cronometro percepito: da menu chiuso tenere Melee; il Main Menu deve comparire appena termina il mezzo secondo, senza la pausa aggiuntiva vista in 0.6.10. Rilasciare Melee, aprire una pagina con Interact: al primo accesso viene creato solo quel renderer. Tornare con Reload e riaprire la stessa pagina: nessun nuovo HUD deve essere creato e la risposta deve restare immediata. Verificare inoltre Script Diagnostics: il margine ottenuto in 0.6.10 non deve regredire in modo significativo.\n'''
TEST_DOC.write_text(test_doc, encoding="utf-8")

validazione = VALIDAZIONE.read_text(encoding="utf-8")
validazione = replace_once(validazione, "# Rapporto di validazione — versione 0.6.10", "# Rapporto di validazione — versione 0.6.11", "VALIDAZIONE title")
validazione = replace_once(validazione, "Release tecnica: **CHILL Dedicated Server 0.6.10**", "Release tecnica: **CHILL Dedicated Server 0.6.11**", "VALIDAZIONE release")
validazione = replace_once(validazione, "OK - controlli statici v0.6.10 superati", "OK - controlli statici v0.6.11 superati", "VALIDAZIONE result")
validazione += '''\n\n## Hold Melee e cache lazy 0.6.11\n\nIl gate richiede un unico opener Melee con `Wait(0.500, Abort When False)` e nessun secondo `Wait` nella stessa regola. `GambarMenu` deve usare `HalamanHudMenuArcade` + `Array Contains` e non può più usare il gate eager `Count Of(HudMenuArcade) == 0` che pre-caricava tutte le pagine. Ogni renderer registra ID e codice pagina nella cache; la chiusura svuota entrambe.\n'''

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

print("Applied CHILL 0.6.11 lazy Arcade page loading")
