from __future__ import annotations

from pathlib import Path
import hashlib
import re

SOURCE = Path("workshop/ruang_irama.workshop")
VALIDATOR = Path("tools/validate_workshop.py")
PROJECT = Path("docs/PROGETTO.md")
TESTS = Path("docs/TEST.md")
REPORT = Path("docs/VALIDAZIONE.md")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 occurrence, found {count}")
    return text.replace(old, new, 1)


src = SOURCE.read_text(encoding="utf-8")

# Chase actions support Number/Vector, not Color. Keep the 32 real name colors
# for application, and add an exact parallel RGB-vector table for animation.
src = replace_once(
    src,
    '\t\t42: SlotHUDTerakhir\n\tplayer:',
    '\t\t42: SlotHUDTerakhir\n\t\t43: DaftarWarnaRGB\n\tplayer:',
    "declare RGB vector palette",
)

rgb_vectors = '''\t\tGlobal.DaftarWarnaRGB = Array(
\t\t\tVector(255, 255, 255),
\t\t\tVector(190, 210, 230),
\t\t\tVector(255, 200, 70),
\t\t\tVector(255, 255, 0),
\t\t\tVector(236, 153, 0),
\t\t\tVector(255, 120, 105),
\t\t\tVector(255, 75, 75),
\t\t\tVector(255, 50, 145),
\t\t\tVector(255, 90, 190),
\t\t\tVector(205, 160, 255),
\t\t\tVector(100, 50, 255),
\t\t\tVector(175, 95, 255),
\t\t\tVector(70, 145, 255),
\t\t\tVector(108, 190, 244),
\t\t\tVector(120, 205, 255),
\t\t\tVector(0, 234, 234),
\t\t\tVector(0, 230, 151),
\t\t\tVector(120, 255, 200),
\t\t\tVector(70, 220, 110),
\t\t\tVector(160, 232, 27),
\t\t\tVector(255, 180, 145),
\t\t\tVector(255, 145, 90),
\t\t\tVector(255, 165, 205),
\t\t\tVector(255, 70, 220),
\t\t\tVector(230, 100, 255),
\t\t\tVector(155, 165, 255),
\t\t\tVector(105, 100, 255),
\t\t\tVector(80, 110, 255),
\t\t\tVector(70, 255, 255),
\t\t\tVector(110, 245, 210),
\t\t\tVector(80, 240, 170),
\t\t\tVector(190, 255, 80)
\t\t);\n'''
src = replace_once(
    src,
    '\t\t\tCustom Color(190, 255, 80, 255)\n\t\t);\n\t\tGlobal.NamaWarna = Array(',
    '\t\t\tCustom Color(190, 255, 80, 255)\n\t\t);\n' + rgb_vectors + '\t\tGlobal.NamaWarna = Array(',
    "insert RGB vector palette",
)

src = replace_once(
    src,
    'Event Player.WarnaMenu = Custom Color(55, 235, 245, 255);',
    'Event Player.WarnaMenu = Vector(55, 235, 245);',
    "initialize WarnaMenu as vector",
)

# Convert the chased Vector back into an actual HUD Color. This preserves live
# color reevaluation while keeping the chase input type valid.
render_color = ('Custom Color(X Component Of(Event Player.WarnaMenu), Y Component Of(Event Player.WarnaMenu), '
                'Z Component Of(Event Player.WarnaMenu), 255)')
old_renderer_color = 'Event Player.WarnaMenu, Visible To'
count = src.count(old_renderer_color)
if count != 9:
    raise SystemExit(f"menu renderer color references: expected 9, found {count}")
src = src.replace(old_renderer_color, render_color + ', Visible To')

# Convert only the transition destinations to Vector. Name Color uses the exact
# parallel vector table so its preview remains faithful to the actual choice.
start = src.index('rule("91k - Subrutin: Transisi warna menu')
end = src.find('\nrule("', start + 1)
if end < 0:
    end = len(src)
transition = src[start:end]
for old, new in (
    ('Custom Color(55, 235, 245, 255)', 'Vector(55, 235, 245)'),
    ('Custom Color(90, 180, 255, 255)', 'Vector(90, 180, 255)'),
    ('Global.DaftarWarna[Event Player.KursorWarna]', 'Global.DaftarWarnaRGB[Event Player.KursorWarna]'),
    ('Custom Color(190, 120, 255, 255)', 'Vector(190, 120, 255)'),
    ('Custom Color(255, 80, 80, 255)', 'Vector(255, 80, 80)'),
    ('Custom Color(255, 185, 90, 255)', 'Vector(255, 185, 90)'),
    ('Custom Color(115, 235, 170, 255)', 'Vector(115, 235, 170)'),
    ('Custom Color(235, 135, 255, 255)', 'Vector(235, 135, 255)'),
):
    if transition.count(old) != 1:
        raise SystemExit(f"transition destination {old!r}: expected 1, found {transition.count(old)}")
    transition = transition.replace(old, new, 1)
src = src[:start] + transition + src[end:]

SOURCE.write_text(src, encoding="utf-8")

# ---------------- validator ----------------
val = VALIDATOR.read_text(encoding="utf-8")

# Palette validator: the animated transition now contains vectors, not Color.
old_tokens = '''    for token in (
        "Custom Color(55, 235, 245, 255)",
        "Custom Color(90, 180, 255, 255)",
        "Global.DaftarWarna[Event Player.KursorWarna]",
        "Custom Color(190, 120, 255, 255)",
        "Custom Color(255, 80, 80, 255)",
        "Custom Color(255, 185, 90, 255)",
        "Custom Color(115, 235, 170, 255)",
        "Custom Color(235, 135, 255, 255)",
    ):
        checks.require(token in transition, f"palette transizione incompleta: {token}")'''
new_tokens = '''    for token in (
        "Vector(55, 235, 245)",
        "Vector(90, 180, 255)",
        "Global.DaftarWarnaRGB[Event Player.KursorWarna]",
        "Vector(190, 120, 255)",
        "Vector(255, 80, 80)",
        "Vector(255, 185, 90)",
        "Vector(115, 235, 170)",
        "Vector(235, 135, 255)",
    ):
        checks.require(token in transition, f"palette transizione incompleta: {token}")'''
val = replace_once(val, old_tokens, new_tokens, "palette transition validator")

# Replace the smooth-transition checker with a type-safe contract.
pattern = re.compile(r'\ndef check_smooth_menu_color_transition\(.*?(?=\ndef main\(\) -> None:)', re.S)
match = pattern.search(val)
if not match:
    raise SystemExit("smooth menu validator not found")
new_check = r'''

def check_smooth_menu_color_transition(checks: Checks, source: str, rules: list[Rule], subroutines: set[str]) -> None:
    clean = mask_strings(source)
    variables = section_body(source, "variables")
    checks.require(re.search(r"(?m)^\s*43\s*:\s*DaftarWarnaRGB\s*$", variables) is not None, "menu smooth: global DaftarWarnaRGB assente")
    checks.require(re.search(r"(?m)^\s*63\s*:\s*WarnaMenu\s*$", variables) is not None, "menu smooth: player WarnaMenu assente")
    rgb_vectors = [re.sub(r"\s+", " ", item).strip() for item in top_level_items(array_body(source, "Global.DaftarWarnaRGB"))]
    checks.equal(len(rgb_vectors), 32, "menu smooth: 32 vettori RGB name-color")
    checks.require("Event Player.WarnaMenu = Vector(55, 235, 245);" in clean, "menu smooth: WarnaMenu deve iniziare come Vector")
    checks.require("TransisiWarnaMenu" in subroutines, "menu smooth: subroutine TransisiWarnaMenu assente")
    checks.require("Event Player.KursorWarna = Event Player.KursorWarna;" in clean, "menu smooth: Name Color deve conservare il cursore")

    transition = rules_containing(rules, "Subroutine;", "TransisiWarnaMenu;")
    checks.equal(len(transition), 1, "menu smooth: renderer transizione")
    if transition:
        body = mask_strings(transition[0].body)
        checks.require("Chase Player Variable Over Time(Event Player, WarnaMenu," in body and "0.350, Destination and Duration);" in body, "menu smooth: chase 0,35 s assente")
        for token in (
            "Vector(55, 235, 245)",
            "Vector(90, 180, 255)",
            "Global.DaftarWarnaRGB[Event Player.KursorWarna]",
            "Vector(190, 120, 255)",
            "Vector(255, 80, 80)",
            "Vector(255, 185, 90)",
            "Vector(115, 235, 170)",
            "Vector(235, 135, 255)",
        ):
            checks.require(token in body, f"menu smooth: destinazione vector assente {token}")
        checks.require("Custom Color(" not in body, "menu smooth: Chase non deve ricevere Color")
        checks.require("Global.DaftarWarna[Event Player.KursorWarna]" not in body, "menu smooth: Chase non deve ricevere un Color da DaftarWarna")
        checks.require("Loop If Condition Is True;" not in body, "menu smooth: transizione non deve usare loop")

    router = rules_containing(rules, "Subroutine;", "GambarMenu;")
    checks.equal(len(router), 1, "menu smooth: router GambarMenu")
    if router:
        checks.require("Call Subroutine(TransisiWarnaMenu);" in mask_strings(router[0].body), "menu smooth: GambarMenu non aggiorna destinazione")

    converted = "Custom Color(X Component Of(Event Player.WarnaMenu), Y Component Of(Event Player.WarnaMenu), Z Component Of(Event Player.WarnaMenu), 255)"
    for sub in ("GambarUtama", "GambarMusik", "GambarKamera", "GambarWarna", "GambarBahasa", "GambarBalasDendam", "GambarUnkillable", "GambarSuara", "GambarIkon"):
        matches = rules_containing(rules, "Subroutine;", f"{sub};")
        checks.equal(len(matches), 1, f"menu smooth: renderer {sub}")
        if matches:
            body = mask_strings(matches[0].body)
            checks.require(converted in body, f"menu smooth: {sub} non converte WarnaMenu Vector in Custom Color")
            checks.require("Visible To String and Color" in body, f"menu smooth: {sub} non rivaluta il colore")
    checks.require("Event Player.WarnaMenu, Visible To" not in clean, "menu smooth: Color raw non valido ancora passato agli HUD")
'''
val = val[:match.start()] + new_check + val[match.end():]
VALIDATOR.write_text(val, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
section = '''\n\n### Fix HUD menu invisibili — Vector RGB\n\nLa prima implementazione della sfumatura inseguiva direttamente un valore `Color` con `Chase Player Variable Over Time`; nel client il campo principale dei menu risultava invisibile mentre gli input a colore fisso restavano visibili. `WarnaMenu` è ora una `Vector(R,G,B)`, cioè un tipo supportato dal chase, e ciascun renderer la converte con `Custom Color(X Component Of(...), Y Component Of(...), Z Component Of(...), 255)`. `DaftarWarnaRGB` contiene 32 vettori paralleli a `DaftarWarna`, inclusi i valori RGB reali delle costanti Workshop, così Name Color mantiene una preview coerente durante la transizione. Nessun loop per-player è stato aggiunto.\n'''
if '### Fix HUD menu invisibili — Vector RGB' not in project:
    project += section
PROJECT.write_text(project, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
line = '- **HUD menu + sfumatura live:** aprire il Main Menu e tutti gli 8 submenu: input e contenuto principale devono essere sempre visibili. Scorrere rapidamente tra le voci e verificare la sfumatura ~0,35 s; in Name Color la tonalità di preview deve seguire le 32 scelte senza far sparire il testo.\n'
if line not in tests:
    tests += '\n' + line
TESTS.write_text(tests, encoding="utf-8")

# Refresh Workshop blob marker.
data = SOURCE.read_bytes().replace(b"\r\n", b"\n")
blob = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
report = REPORT.read_text(encoding="utf-8")
report, n = re.subn(r"```text\n[0-9a-f]{40}\n```", f"```text\n{blob}\n```", report, count=1)
if n != 1:
    raise SystemExit("validation report blob marker not found")
REPORT.write_text(report, encoding="utf-8")
