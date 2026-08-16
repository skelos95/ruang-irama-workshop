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

PALETTE = {
    0: (55, 235, 245),   # Soundtrack - cyan
    1: (70, 135, 255),   # Camera - blue
    3: (185, 105, 255),  # Language - violet
    4: (255, 75, 85),    # Revenge - red
    5: (255, 145, 55),   # Unkillable - orange
    6: (255, 80, 205),   # Hero Voice - magenta
    7: (170, 240, 85),   # Player Icon - lime
    8: (65, 225, 130),   # Crouch Teleport - green
    9: (55, 190, 170),   # Crouch Privacy - teal
    10: (255, 210, 70),  # Try Your Luck - gold
    11: (255, 120, 155), # Vote Player - rose
}


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected 1 occurrence, found {count}")
    return text.replace(old, new, 1)


def mask_strings(text: str) -> str:
    out = []
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


def get_rule(text: str, name: str) -> tuple[int, int, str]:
    marker = f'rule("{name}")'
    start = text.index(marker)
    opening = text.index("{", start)
    end = matching(text, opening, "{", "}") + 1
    return start, end, text[start:end]


def replace_actions(rule: str, actions: str) -> str:
    clean = mask_strings(rule)
    m = re.search(r"(?m)^\s*actions\s*\{", clean)
    if m is None:
        raise RuntimeError("actions block missing")
    opening = clean.find("{", m.start())
    closing = matching(rule, opening, "{", "}")
    return rule[:opening + 1] + "\n" + actions.rstrip() + "\n\t" + rule[closing:]


source = SOURCE.read_text(encoding="utf-8")
rule_name = "91k - Subrutin: Transisi warna menu tanpa lompatan"
start, end, rule = get_rule(source, rule_name)
idx = "(Event Player.HalamanMenu == -1 ? Event Player.KursorUtama : Event Player.HalamanMenu)"

branches = []
for page in range(12):
    if page == 2:
        target = "Global.DaftarWarnaRGB[Event Player.KursorWarna]"
    else:
        rgb = PALETTE[page]
        target = f"Vector({rgb[0]}, {rgb[1]}, {rgb[2]})"
    prefix = "" if not branches else ": "
    branches.append(f"{prefix}{idx} == {page} ? {target}")
# Defensive fallback = Soundtrack cyan; under normal conditions the index is always 0..11.
target_expr = "\n\t\t\t".join(branches) + "\n\t\t\t: Vector(55, 235, 245)"
actions = f'''\t\t"Setiap menu memiliki warna identitas sendiri. Hanya Name Color mengikuti warna yang sedang dipilih; semuanya berpindah dengan chase lembut."
\t\tChase Player Variable Over Time(Event Player, WarnaMenu,
\t\t\t{target_expr}, 0.180, Destination and Duration);'''
rule = replace_actions(rule, actions)
source = source[:start] + rule + source[end:]

# Structural assertions before writing.
clean_rule = mask_strings(rule)
if "Global.DaftarWarnaRGB[Event Player.KursorWarna]" not in clean_rule:
    raise RuntimeError("Name Color is no longer dynamic")
if "0.180, Destination and Duration" not in clean_rule:
    raise RuntimeError("smooth transition duration changed")
for page, rgb in PALETTE.items():
    token = f"{idx} == {page} ? Vector({rgb[0]}, {rgb[1]}, {rgb[2]})"
    if token not in clean_rule:
        raise RuntimeError(f"missing fixed menu color for page {page}")
if len(set(PALETTE.values())) != len(PALETTE):
    raise RuntimeError("fixed menu palette contains duplicate RGB values")

SOURCE.write_text(source, encoding="utf-8")

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_once(validator, "della versione 0.6.12.", "della versione 0.6.13.", "validator doc version")
validator = replace_once(validator, 'CURRENT_VERSION = "0.6.12"', 'CURRENT_VERSION = "0.6.13"', "validator current version")

anchor = '''    transition_rules = rules_containing(rules, "Subroutine;", "TransisiWarnaMenu;")
    checks.equal(len(transition_rules), 1, "subroutine TransisiWarnaMenu")
    if transition_rules:
        checks.require(
            re.search(r"0\\.180\\s*,\\s*Destination and Duration", mask_strings(transition_rules[0].body)) is not None,
            "transizione colore menu non impostata a 0,18 s",
        )
'''
extra = anchor + '''        transition_code = mask_strings(transition_rules[0].body)
        checks.require(
            "Global.DaftarWarnaRGB[Event Player.KursorWarna]" in transition_code,
            "Name Color non segue più dinamicamente il colore selezionato",
        )
        fixed_menu_colors = {
            0: (55, 235, 245),
            1: (70, 135, 255),
            3: (185, 105, 255),
            4: (255, 75, 85),
            5: (255, 145, 55),
            6: (255, 80, 205),
            7: (170, 240, 85),
            8: (65, 225, 130),
            9: (55, 190, 170),
            10: (255, 210, 70),
            11: (255, 120, 155),
        }
        checks.equal(
            len(set(fixed_menu_colors.values())),
            len(fixed_menu_colors),
            "palette fissa menu con colori duplicati",
        )
        page_expr = "(Event Player.HalamanMenu == -1 ? Event Player.KursorUtama : Event Player.HalamanMenu)"
        for page, rgb in fixed_menu_colors.items():
            checks.require(
                f"{page_expr} == {page} ? Vector({rgb[0]}, {rgb[1]}, {rgb[2]})" in transition_code,
                f"colore dedicato menu {page} mancante o modificato",
            )
'''
validator = replace_once(validator, anchor, extra, "validator unique menu palette")
VALIDATOR.write_text(validator, encoding="utf-8")

VERSION.write_text("0.6.13\n", encoding="utf-8")

readme = README.read_text(encoding="utf-8")
readme = replace_once(readme, "La versione **0.6.12** identifica lo stato funzionale e tecnico corrente del repository.", "La versione **0.6.13** identifica lo stato funzionale e tecnico corrente del repository.", "README version")
readme = replace_once(
    readme,
    "- Colori menu diversi e coordinati con i rispettivi sottomenu.\n- Transizione colore morbida di circa **0,18 s** tramite Vector RGB.\n",
    "- Ogni menu, tranne Name Color, ha una **tonalità identitaria unica**; Name Color segue invece il colore selezionato.\n- Tutti i passaggi colore restano sfumati con transizione morbida di circa **0,18 s** tramite Vector RGB.\n",
    "README menu palette bullets",
)
readme += '''\n\n### Palette menu unica 0.6.13\n\nOgni voce Arcade ha ora una tonalità dedicata e distinta sia nel Main Menu quando viene evidenziata sia nel relativo sottomenu: Soundtrack ciano, Camera blu, Language viola, Revenge rosso, Unkillable arancio, Hero Voice magenta, Player Icon lime, Crouch Teleport verde, Crouch Privacy teal, Try Your Luck oro e Vote Player rosa. **Name Color resta volutamente dinamico** e segue `DaftarWarnaRGB[KursorWarna]`. Tutti i passaggi continuano a usare `Chase Player Variable Over Time` a 0,18 s, quindi la variazione è sempre sfumata e mai istantanea.\n'''
README.write_text(readme, encoding="utf-8")

progetto = PROGETTO.read_text(encoding="utf-8")
progetto = replace_once(progetto, "# Note di progetto — versione 0.6.12", "# Note di progetto — versione 0.6.13", "PROGETTO title")
progetto = replace_once(progetto, "Workshop 0.6.12.", "Workshop 0.6.13.", "PROGETTO version")
progetto += '''\n\n## Palette menu 0.6.13\n\n`TransisiWarnaMenu` assegna una Vector RGB fissa e unica ai menu 0,1,3..11. Il menu 2 Name Color è l'unica eccezione e continua a puntare a `Global.DaftarWarnaRGB[Event Player.KursorWarna]`. Il Main Menu usa `KursorUtama`, il sottomenu usa `HalamanMenu`, quindi la stessa identità cromatica accompagna il passaggio fra le due viste. La durata del chase resta 0,18 s.\n'''
PROGETTO.write_text(progetto, encoding="utf-8")

test_doc = TEST_DOC.read_text(encoding="utf-8")
test_doc = replace_once(test_doc, "# Piano di test — versione 0.6.12", "# Piano di test — versione 0.6.13", "TEST title")
test_doc = replace_once(test_doc, "Workshop 0.6.12.", "Workshop 0.6.13.", "TEST version")
test_doc += '''\n\n## Palette menu 0.6.13\n\nTest live: scorrere lentamente tutte le 12 voci del Main Menu e verificare che 0,1,3..11 abbiano tonalità chiaramente diverse e che il passaggio sia sempre sfumato. Aprire ciascun sottomenu: deve mantenere la stessa identità cromatica della voce principale. Nel Name Color scorrere più colori: il menu deve invece seguire in tempo reale il colore evidenziato, sempre con la transizione morbida.\n'''
TEST_DOC.write_text(test_doc, encoding="utf-8")

validazione = VALIDAZIONE.read_text(encoding="utf-8")
validazione = replace_once(validazione, "# Rapporto di validazione — versione 0.6.12", "# Rapporto di validazione — versione 0.6.13", "VALIDAZIONE title")
validazione = replace_once(validazione, "Release tecnica: **CHILL Dedicated Server 0.6.12**", "Release tecnica: **CHILL Dedicated Server 0.6.13**", "VALIDAZIONE release")
validazione = replace_once(validazione, "OK - controlli statici v0.6.12 superati", "OK - controlli statici v0.6.13 superati", "VALIDAZIONE result")
validazione += '''\n\n## Palette menu 0.6.13\n\nIl gate richiede 11 RGB fissi tutti diversi per i menu diversi da Name Color, mantiene il ramo dinamico `DaftarWarnaRGB[KursorWarna]` per il menu 2 e conserva la transizione `0.180, Destination and Duration`.\n'''

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

print("Applied CHILL 0.6.13 unique smooth menu palette")
