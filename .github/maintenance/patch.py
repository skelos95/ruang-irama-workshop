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


def replace_in_rule(text: str, prefix: str, old: str, new: str, label: str) -> str:
    start = text.index(f'rule("{prefix}')
    end = text.find('\nrule("', start + 1)
    if end < 0:
        end = len(text)
    block = text[start:end]
    block = replace_once(block, old, new, label)
    return text[:start] + block + text[end:]


src = SOURCE.read_text(encoding="utf-8")

# Per-player menu accent. It is chased only when GambarMenu redraws; there is no
# periodic per-player color loop.
src = replace_once(
    src,
    '\t\t61: IndeksIkon\n\t\t62: KursorIkon\n}',
    '\t\t61: IndeksIkon\n\t\t62: KursorIkon\n\t\t63: WarnaMenu\n}',
    "declare menu color variable",
)
src = replace_once(
    src,
    '\t20: GambarIkon\n}',
    '\t20: GambarIkon\n\t21: TransisiWarnaMenu\n}',
    "declare menu color transition subroutine",
)

# Undo the previous misunderstanding: Name Color must keep its last preview
# cursor like every other submenu.
src = replace_once(
    src,
    '\t\t\tElse If(Event Player.HalamanMenu == 2);\n\t\t\t\tEvent Player.KursorWarna = Event Player.IndeksWarna;',
    '\t\t\tElse If(Event Player.HalamanMenu == 2);\n\t\t\t\tEvent Player.KursorWarna = Event Player.KursorWarna;',
    "restore persistent name-color cursor",
)

# Initialize the animated menu color to Soundtrack aqua.
src = replace_once(
    src,
    '\t\tEvent Player.IndeksIkon = 0;\n\t\tEvent Player.KursorIkon = 0;',
    '\t\tEvent Player.IndeksIkon = 0;\n\t\tEvent Player.KursorIkon = 0;\n\t\tEvent Player.WarnaMenu = Custom Color(55, 235, 245, 255);',
    "initialize menu color",
)

# Every menu redraw updates only the chase destination. Rapid navigation simply
# redirects the active interpolation from its current color.
src = replace_in_rule(
    src,
    "91 - Subrutin:",
    '\t\tIf(Event Player.HalamanMenu == -1);',
    '\t\tCall Subroutine(TransisiWarnaMenu);\n\t\tIf(Event Player.HalamanMenu == -1);',
    "route menu color transition",
)

# Main menu: replace the hard switch ternary with the animated variable.
main_old = '''Event Player.KursorUtama == 0 ? Custom Color(55, 235, 245, 255)\n\t\t\t: Event Player.KursorUtama == 1 ? Custom Color(90, 180, 255, 255)\n\t\t\t: Event Player.KursorUtama == 2 ? Global.DaftarWarna[Event Player.IndeksWarna]\n\t\t\t: Event Player.KursorUtama == 3 ? Custom Color(190, 120, 255, 255)\n\t\t\t: Event Player.KursorUtama == 4 ? Custom Color(255, 80, 80, 255)\n\t\t\t: Event Player.KursorUtama == 5 ? Custom Color(255, 185, 90, 255)\n\t\t\t: Event Player.KursorUtama == 6 ? Custom Color(115, 235, 170, 255)\n\t\t\t: Custom Color(235, 135, 255, 255), Visible To and String, Visible Never);'''
main_new = '''Event Player.WarnaMenu, Visible To String and Color, Visible Never);'''
src = replace_in_rule(src, "91a - Subrutin:", main_old, main_new, "main animated menu color")

# Submenus keep their input/subheader colors, but their primary content color is
# the same animated WarnaMenu used by the parent Main Menu entry.
renderer_colors = (
    ("91b - Subrutin:", 'Custom Color(55, 235, 245, 255),\n\t\t\tVisible To and String, Visible Never);'),
    ("91c - Subrutin:", 'Custom Color(90, 180, 255, 255),\n\t\t\tVisible To and String, Visible Never);'),
    ("91d - Subrutin:", 'Global.DaftarWarna[Event Player.KursorWarna], Visible To String and Color, Visible Never);'),
    ("91e - Subrutin:", 'Custom Color(190, 120, 255, 255), Visible To and String, Visible Never);'),
    ("91f - Subrutin:", 'Custom Color(255, 80, 80, 255), Visible To and String, Visible Never);'),
    ("91h - Subrutin:", 'Custom Color(255, 185, 90, 255), Visible To and String, Visible Never);'),
    ("91i - Subrutin:", 'Custom Color(115, 235, 170, 255), Visible To and String, Visible Never);'),
    ("91j - Subrutin:", 'Custom Color(235, 135, 255, 255), Visible To String and Color, Visible Never);'),
)
for prefix, old in renderer_colors:
    src = replace_in_rule(
        src,
        prefix,
        old,
        'Event Player.WarnaMenu, Visible To String and Color, Visible Never);',
        f"animated primary color {prefix}",
    )

# One event-driven chase, no loop. 0.35 s is long enough to visibly blend but
# short enough to keep fast menu navigation responsive.
transition_rule = r'''rule("91k - Subrutin: Transisi warna menu tanpa scatto")
{
	event
	{
		Subroutine;
		TransisiWarnaMenu;
	}

	actions
	{
		Chase Player Variable Over Time(Event Player, WarnaMenu,
			(Event Player.HalamanMenu == -1 ? Event Player.KursorUtama : Event Player.HalamanMenu) == 0 ? Custom Color(55, 235, 245, 255)
			: (Event Player.HalamanMenu == -1 ? Event Player.KursorUtama : Event Player.HalamanMenu) == 1 ? Custom Color(90, 180, 255, 255)
			: (Event Player.HalamanMenu == -1 ? Event Player.KursorUtama : Event Player.HalamanMenu) == 2 ? Global.DaftarWarna[Event Player.KursorWarna]
			: (Event Player.HalamanMenu == -1 ? Event Player.KursorUtama : Event Player.HalamanMenu) == 3 ? Custom Color(190, 120, 255, 255)
			: (Event Player.HalamanMenu == -1 ? Event Player.KursorUtama : Event Player.HalamanMenu) == 4 ? Custom Color(255, 80, 80, 255)
			: (Event Player.HalamanMenu == -1 ? Event Player.KursorUtama : Event Player.HalamanMenu) == 5 ? Custom Color(255, 185, 90, 255)
			: (Event Player.HalamanMenu == -1 ? Event Player.KursorUtama : Event Player.HalamanMenu) == 6 ? Custom Color(115, 235, 170, 255)
			: Custom Color(235, 135, 255, 255), 0.350, Destination and Duration);
	}
}

'''
insert_at = src.index('rule("92 - Subrutin:')
src = src[:insert_at] + transition_rule + src[insert_at:]

SOURCE.write_text(src, encoding="utf-8")

# ---------------- validator ----------------
val = VALIDATOR.read_text(encoding="utf-8")

# The old correction represented the wrong interpretation of the bug. Replace
# it with the actual smooth-transition contract and restore cursor persistence.
pattern = re.compile(r'\ndef check_color_menu_cursor_sync\(.*?(?=\ndef main\(\) -> None:)', re.S)
match = pattern.search(val)
if not match:
    raise SystemExit("old color-menu sync validator not found")
new_check = r'''

def check_smooth_menu_color_transition(checks: Checks, source: str, rules: list[Rule], subroutines: set[str]) -> None:
    clean = mask_strings(source)
    variables = section_body(source, "variables")
    checks.require(
        re.search(r"(?m)^\s*63\s*:\s*WarnaMenu\s*$", variables) is not None,
        "menu smooth: player variable WarnaMenu assente",
    )
    checks.require("TransisiWarnaMenu" in subroutines, "menu smooth: subroutine TransisiWarnaMenu assente")
    checks.require(
        "Event Player.KursorWarna = Event Player.KursorWarna;" in clean,
        "menu smooth: Name Color deve conservare l'ultimo cursore",
    )
    checks.require(
        "Event Player.KursorWarna = Event Player.IndeksWarna;" not in clean,
        "menu smooth: Name Color non deve essere risincronizzato all'apertura",
    )

    transition = rules_containing(rules, "Subroutine;", "TransisiWarnaMenu;")
    checks.equal(len(transition), 1, "menu smooth: renderer transizione")
    if transition:
        body = mask_strings(transition[0].body)
        checks.require(
            "Chase Player Variable Over Time(Event Player, WarnaMenu," in body
            and "0.350, Destination and Duration);" in body,
            "menu smooth: chase WarnaMenu 0,35 s assente",
        )
        for token in (
            "Custom Color(55, 235, 245, 255)",
            "Custom Color(90, 180, 255, 255)",
            "Global.DaftarWarna[Event Player.KursorWarna]",
            "Custom Color(190, 120, 255, 255)",
            "Custom Color(255, 80, 80, 255)",
            "Custom Color(255, 185, 90, 255)",
            "Custom Color(115, 235, 170, 255)",
            "Custom Color(235, 135, 255, 255)",
        ):
            checks.require(token in body, f"menu smooth: destinazione palette assente {token}")
        checks.require("Loop If Condition Is True;" not in body, "menu smooth: transizione non deve usare loop")

    router = rules_containing(rules, "Subroutine;", "GambarMenu;")
    checks.equal(len(router), 1, "menu smooth: router GambarMenu")
    if router:
        checks.require(
            "Call Subroutine(TransisiWarnaMenu);" in mask_strings(router[0].body),
            "menu smooth: GambarMenu non aggiorna la destinazione colore",
        )

    for sub in ("GambarUtama", "GambarMusik", "GambarKamera", "GambarWarna", "GambarBahasa", "GambarBalasDendam", "GambarUnkillable", "GambarSuara", "GambarIkon"):
        matches = rules_containing(rules, "Subroutine;", f"{sub};")
        checks.equal(len(matches), 1, f"menu smooth: renderer {sub}")
        if matches:
            body = mask_strings(matches[0].body)
            checks.require("Event Player.WarnaMenu" in body, f"menu smooth: {sub} non usa WarnaMenu")
            checks.require("Visible To String and Color" in body, f"menu smooth: {sub} non rivaluta il colore")
'''
val = val[:match.start()] + new_check + val[match.end():]
val = val.replace(
    '        check_color_menu_cursor_sync(checks, source, rules)\n',
    '        check_smooth_menu_color_transition(checks, source, rules, subroutines)\n',
)

# Update the palette validator: fixed palette lives in TransisiWarnaMenu now;
# renderers intentionally share WarnaMenu so parent/submenu can blend smoothly.
start = val.index('    # Primary submenu colors are unique, except Name Color which intentionally')
end = val.index('\n\ndef check_runtime_efficiency_audit', start)
replacement = r'''    transition = renderer("TransisiWarnaMenu")
    for body, label in (
        (main, "main"),
        (soundtrack, "soundtrack"),
        (camera, "camera"),
        (name_color, "name color"),
        (language, "language"),
        (revenge, "revenge"),
        (unkillable, "unkillable"),
        (voice, "voice"),
        (icon, "player icon"),
    ):
        checks.require("Event Player.WarnaMenu" in body, f"palette animata assente per {label}")
        checks.require("Visible To String and Color" in body, f"rivalutazione colore assente per {label}")

    for token in (
        "Custom Color(55, 235, 245, 255)",
        "Custom Color(90, 180, 255, 255)",
        "Global.DaftarWarna[Event Player.KursorWarna]",
        "Custom Color(190, 120, 255, 255)",
        "Custom Color(255, 80, 80, 255)",
        "Custom Color(255, 185, 90, 255)",
        "Custom Color(115, 235, 170, 255)",
        "Custom Color(235, 135, 255, 255)",
    ):
        checks.require(token in transition, f"palette transizione incompleta: {token}")
'''
val = val[:start] + replacement + val[end:]
VALIDATOR.write_text(val, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
section = '''\n\n### Transizioni colore menu\n\nIl colore principale dei menu non cambia più istantaneamente tra una voce e l'altra. `Event Player.WarnaMenu` viene portato al colore destinazione con `Chase Player Variable Over Time` in 0,35 s dalla subroutine `TransisiWarnaMenu`. Tutti i renderer del Main Menu e dei submenu rivalutano soltanto il colore e condividono `WarnaMenu`; i colori degli input restano fissi. La transizione è event-driven su `GambarMenu` e non introduce loop periodici per player. Il cursore di Name Color resta persistente come gli altri submenu.\n'''
if '### Transizioni colore menu' not in project:
    project += section
PROJECT.write_text(project, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
line = '- **Transizione colori menu live:** scorrere rapidamente avanti/indietro tra tutte le 8 voci del Main Menu e aprire/chiudere i relativi submenu; il colore principale deve sfumare in circa 0,35 s senza scatti. Name Color deve continuare a riaprire sull’ultimo cursore salvato.\n'
if line not in tests:
    tests += '\n' + line
TESTS.write_text(tests, encoding="utf-8")

# Refresh Workshop source blob marker.
data = SOURCE.read_bytes().replace(b"\r\n", b"\n")
blob = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
report = REPORT.read_text(encoding="utf-8")
report, n = re.subn(r"```text\n[0-9a-f]{40}\n```", f"```text\n{blob}\n```", report, count=1)
if n != 1:
    raise SystemExit("validation report blob marker not found")
REPORT.write_text(report, encoding="utf-8")
