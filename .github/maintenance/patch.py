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


def find_matching(text: str, opening: int, left: str, right: str) -> int:
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


def top_items(body: str) -> list[str]:
    items: list[str] = []
    start = 0
    stack: list[str] = []
    quoted = False
    escaped = False
    pairs = {")": "(", "]": "[", "}": "{"}
    for i, ch in enumerate(body):
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
        elif ch in "([{":
            stack.append(ch)
        elif ch in ")]}":
            if not stack or stack[-1] != pairs[ch]:
                raise RuntimeError("unbalanced call arguments")
            stack.pop()
        elif ch == "," and not stack:
            items.append(body[start:i].strip())
            start = i + 1
    tail = body[start:].strip()
    if tail:
        items.append(tail)
    return items


def get_rule(text: str, name: str) -> tuple[int, int, str]:
    marker = f'rule("{name}")'
    start = text.index(marker)
    opening = text.index("{", start)
    end = find_matching(text, opening, "{", "}") + 1
    return start, end, text[start:end]


def put_rule(text: str, name: str, rule: str) -> str:
    start, end, _ = get_rule(text, name)
    return text[:start] + rule + text[end:]


def replace_actions(rule: str, actions: str) -> str:
    clean = mask_strings(rule)
    match = re.search(r"(?m)^\s*actions\s*\{", clean)
    if match is None:
        raise RuntimeError("actions block not found")
    opening = clean.find("{", match.start())
    closing = find_matching(rule, opening, "{", "}")
    return rule[: opening + 1] + "\n" + actions.rstrip() + "\n\t" + rule[closing:]


def hud_call(rule: str) -> tuple[str, list[str]]:
    clean = mask_strings(rule)
    marker = "Create HUD Text("
    at = clean.find(marker)
    if at < 0 or clean.find(marker, at + 1) >= 0:
        raise RuntimeError("renderer must contain exactly one Create HUD Text")
    opening = clean.find("(", at)
    closing = find_matching(rule, opening, "(", ")")
    call = rule[at : closing + 1]
    args = top_items(rule[opening + 1 : closing])
    return call, args


def conditional(values: list[tuple[int, str]]) -> str:
    if [code for code, _ in values] != [-1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]:
        raise RuntimeError("unexpected Arcade page order")
    parts: list[str] = []
    for code, value in values[:-1]:
        parts.append(f"Event Player.HalamanMenu == {code} ? ({value})")
    return " : ".join(parts) + f" : ({values[-1][1]})"


source = SOURCE.read_text(encoding="utf-8")

# Collect the current page expressions before removing the per-page HUD renderers.
renderers = [
    (-1, "GambarUtama", "91a - Subrutin: Gambar menu utama"),
    (0, "GambarMusik", "91b - Subrutin: Gambar menu musik"),
    (1, "GambarKamera", "91c - Subrutin: Gambar menu kamera"),
    (2, "GambarWarna", "91d - Subrutin: Gambar menu warna nama"),
    (3, "GambarBahasa", "91e - Subrutin: Gambar menu bahasa"),
    (4, "GambarBalasDendam", "91f - Subrutin: Gambar menu balas dendam"),
    (5, "GambarKebal", "91h - Subrutin: Gambar menu kebal"),
    (6, "GambarSuara", "91i - Subrutin: Gambar menu suara pahlawan"),
    (7, "GambarIkon", "91j - Subrutin: Gambar menu ikon pemain"),
    (8, "GambarSakelarTeleportasi", "91l - Subrutin: Gambar sakelar teleportasi jongkok"),
    (9, "GambarPrivasiInspeksi", "91m - Subrutin: Gambar privasi inspeksi dari musuh"),
    (10, "GambarNasib", "91n - Subrutin: Gambar kartu nasib"),
    (11, "GambarPilihan", "91o - Subrutin: Gambar menu pilihan pemain"),
]

pages_help: list[tuple[int, str]] = []
pages_body: list[tuple[int, str]] = []
pages_secondary_color: list[tuple[int, str]] = []
pages_main_color: list[tuple[int, str]] = []

for code, subroutine, rule_name in renderers:
    _, _, rule = get_rule(source, rule_name)
    _, args = hud_call(rule)
    if len(args) != 11:
        raise RuntimeError(f"{rule_name}: expected 11 HUD args, found {len(args)}")
    expected = {
        0: "Event Player",
        1: "Null",
        4: "Top",
        5: "100",
        6: "Color(White)",
        9: "Visible To String and Color",
        10: "Visible Never",
    }
    for index, value in expected.items():
        if re.sub(r"\s+", "", args[index]) != re.sub(r"\s+", "", value):
            raise RuntimeError(f"{rule_name}: unexpected HUD arg {index}: {args[index]}")
    pages_help.append((code, args[2]))
    pages_body.append((code, args[3]))
    pages_secondary_color.append((code, args[7]))
    pages_main_color.append((code, args[8]))

help_expr = conditional(pages_help)
body_expr = conditional(pages_body)
secondary_expr = conditional(pages_secondary_color)
main_expr = conditional(pages_main_color)

# One persistent HUD for the whole Arcade session. HalamanMenu selects the page live.
name = "91 - Subrutin: Pilih gambar menu yang sedang dibuka"
_, _, router = get_rule(source, name)
new_actions = f'''\t\tCall Subroutine(TransisiWarnaMenu);
\t\tIf(Event Player.HudMenu == Null);
\t\t\tCreate HUD Text(Event Player, Null,
\t\t\t\t{help_expr},
\t\t\t\t{body_expr},
\t\t\t\tTop, 100, Color(White),
\t\t\t\t{secondary_expr},
\t\t\t\t{main_expr},
\t\t\t\tVisible To String and Color, Visible Never);
\t\t\tEvent Player.HudMenu = Last Text ID;
\t\tEnd;
\t\tIf(Index Of Array Value(Global.PemainManusia, Event Player) >= 0);
\t\t\tGlobal.HudMenuPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = Event Player.HudMenu;
\t\tEnd;'''
router = replace_actions(router, new_actions)
source = put_rule(source, name, router)

# Redirect any direct page-render calls to the persistent renderer, then remove the old page rules/declarations.
for _, subroutine, rule_name in renderers:
    source = source.replace(f"Call Subroutine({subroutine});", "Call Subroutine(GambarMenu);")
    start, end, _ = get_rule(source, rule_name)
    source = source[:start] + source[end:]
    pattern = re.compile(rf"(?m)^\s*\d+\s*:\s*{re.escape(subroutine)}\s*$\n?")
    source, count = pattern.subn("", source, count=1)
    if count != 1:
        raise RuntimeError(f"subroutine declaration not removed: {subroutine}")

# Persistent HUD means page switches never destroy/recreate the Arcade HUD.
_, _, router = get_rule(source, name)
if "Destroy HUD Text" in mask_strings(router):
    raise RuntimeError("GambarMenu still destroys HUD")
if len(re.findall(r"Create HUD Text\s*\(", mask_strings(router))) != 1:
    raise RuntimeError("GambarMenu must own exactly one persistent HUD creation")
for _, subroutine, _ in renderers:
    if subroutine in mask_strings(source):
        raise RuntimeError(f"legacy Arcade renderer still referenced: {subroutine}")

SOURCE.write_text(source, encoding="utf-8")

# Validator 0.6.9: enforce persistent HUD architecture.
validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_once(validator, "della versione 0.6.8.", "della versione 0.6.9.", "validator docstring")
validator = replace_once(validator, 'CURRENT_VERSION = "0.6.8"', 'CURRENT_VERSION = "0.6.9"', "validator version")

start = validator.index("    expected_renderers = {")
end = validator.index("    dispatcher_candidates = [", start)
legacy_names = [subroutine for _, subroutine, _ in renderers]
new_block = '''    legacy_arcade_renderers = {\n''' + "".join(f'        "{item}",\n' for item in legacy_names) + '''    }\n    checks.require(\n        not (legacy_arcade_renderers & subroutines),\n        f"renderer Arcade legacy ancora dichiarati: {sorted(legacy_arcade_renderers & subroutines)}",\n    )\n    router_rules = rules_containing(rules, "Subroutine;", "GambarMenu;")\n    checks.equal(len(router_rules), 1, "renderer persistente GambarMenu")\n    if router_rules:\n        router = router_rules[0].body\n        huds = call_texts(router, "Create HUD Text")\n        checks.equal(len(huds), 1, "HUD persistente unico del Menu Arcade")\n        checks.require(\n            "Destroy HUD Text" not in mask_strings(router),\n            "GambarMenu non deve distruggere l'HUD durante i cambi pagina",\n        )\n        checks.require(\n            code_contains(\n                router,\n                "Event Player.HudMenu == Null;",\n                "Event Player.HudMenu = Last Text ID;",\n                "Call Subroutine(TransisiWarnaMenu);",\n            ),\n            "GambarMenu non usa creazione lazy persistente",\n        )\n        if huds:\n            hud = huds[0]\n            checks.require(\n                "Visible To String and Color" in hud,\n                "HUD persistente non rivaluta pagina/stringhe/colori",\n            )\n            for page in range(-1, 11):\n                checks.require(\n                    f"Event Player.HalamanMenu == {page}" in hud,\n                    f"HUD persistente privo del ramo pagina {page}",\n                )\n            for text in ("4 - REVENGE", "4 - BALAS DENDAM", "4 - ล้างแค้น"):\n                checks.require(\n                    f'Custom String("{text}")' in hud,\n                    "BalasDendam: stato vuoto non localizzato in tutte e tre le lingue",\n                )\n\n'''
validator = validator[:start] + new_block + validator[end:]

revenge_start_marker = '    revenge_renderers = rules_containing(rules, "Subroutine;", "GambarBalasDendam;")'
if revenge_start_marker in validator:
    start = validator.index(revenge_start_marker)
    end = validator.index("\n\ndef check_camera", start)
    validator = validator[:start] + validator[end:]

VALIDATOR.write_text(validator, encoding="utf-8")
VERSION.write_text("0.6.9\n", encoding="utf-8")

# Docs.
readme = README.read_text(encoding="utf-8")
readme = replace_once(readme, "La versione **0.6.8** identifica lo stato funzionale e tecnico corrente del repository.", "La versione **0.6.9** identifica lo stato funzionale e tecnico corrente del repository.", "README version")
if "### HUD persistente 0.6.9" not in readme:
    readme += '''\n\n### HUD persistente 0.6.9\n\nIl Menu Arcade usa ora **un solo HUD persistente** per tutta la sessione di apertura. `Interact` e `Reload` cambiano `HalamanMenu`, ma non eseguono più `Destroy HUD Text` / `Create HUD Text` per cambiare pagina. Le 13 viste (Main + 12 pagine) sono rami rivalutati nello stesso HUD, quindi cambio pagina, cursori, stato Try Your Luck e dati dinamici restano nello stesso elemento visivo. Il ritardo percepito di circa mezzo secondo sui cambi pagina non dipende più dalla ricreazione dell'HUD.\n'''
README.write_text(readme, encoding="utf-8")

progetto = PROGETTO.read_text(encoding="utf-8")
progetto = replace_once(progetto, "# Note di progetto — versione 0.6.8", "# Note di progetto — versione 0.6.9", "PROGETTO title")
progetto = replace_once(progetto, "Workshop 0.6.8.", "Workshop 0.6.9.", "PROGETTO version")
if "## HUD Arcade persistente 0.6.9" not in progetto:
    progetto += '''\n\n## HUD Arcade persistente 0.6.9\n\nLa causa del ritardo residuo di `Interact`/`Reload` era architetturale: il cambio pagina distruggeva il vecchio HUD e ne creava uno nuovo. `GambarMenu` possiede ora un solo `Create HUD Text`, creato lazy soltanto quando `HudMenu == Null`; `HalamanMenu` seleziona live Main o una delle 12 pagine dentro lo stesso HUD. I renderer Arcade per-pagina sono stati rimossi; `GambarTeleportasi` resta separato perché appartiene all'overlay Crouch Teleport.\n'''
PROGETTO.write_text(progetto, encoding="utf-8")

test_doc = TEST_DOC.read_text(encoding="utf-8")
test_doc = replace_once(test_doc, "# Piano di test — versione 0.6.8", "# Piano di test — versione 0.6.9", "TEST title")
test_doc = replace_once(test_doc, "Workshop 0.6.8.", "Workshop 0.6.9.", "TEST version")
if "## Cambio pagina immediato 0.6.9" not in test_doc:
    test_doc += '''\n\n## Cambio pagina immediato 0.6.9\n\nTest live prioritario: aprire il Menu Arcade, premere `Interact` dal Main verso più pagine e `Reload` per tornare al Main. Il testo deve cambiare senza la precedente pausa di circa mezzo secondo e senza flash/scomparsa dell'HUD. Ripetere rapidamente Primary/Secondary -> Interact -> Reload. Verificare anche Camera, Hero Voice, Try Your Luck e Vote Player, perché ora condividono lo stesso HUD persistente.\n'''
TEST_DOC.write_text(test_doc, encoding="utf-8")

validazione = VALIDAZIONE.read_text(encoding="utf-8")
validazione = replace_once(validazione, "# Rapporto di validazione — versione 0.6.8", "# Rapporto di validazione — versione 0.6.9", "VALIDAZIONE title")
validazione = replace_once(validazione, "Release tecnica: **CHILL Dedicated Server 0.6.8**", "Release tecnica: **CHILL Dedicated Server 0.6.9**", "VALIDAZIONE release")
validazione = replace_once(validazione, "OK - controlli statici v0.6.8 superati", "OK - controlli statici v0.6.9 superati", "VALIDAZIONE result")
if "## HUD persistente 0.6.9" not in validazione:
    validazione += '''\n\n## HUD persistente 0.6.9\n\nIl validatore richiede un solo `Create HUD Text` dentro `GambarMenu`, creazione lazy con `HudMenu == Null`, assenza di `Destroy HUD Text` nel cambio pagina, rivalutazione `Visible To String and Color`, presenza dei rami `HalamanMenu` e assenza dei vecchi renderer Arcade per-pagina.\n'''

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

print("Applied CHILL 0.6.9 persistent Arcade Menu HUD")
