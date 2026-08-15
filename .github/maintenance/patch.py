from __future__ import annotations

from pathlib import Path
import hashlib
import re

SOURCE = Path("workshop/ruang_irama.workshop")
VALIDATOR = Path("tools/validate_workshop.py")
TESTS = Path("docs/TEST.md")
REPORT = Path("docs/VALIDAZIONE.md")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 occurrence, found {count}")
    return text.replace(old, new, 1)


src = SOURCE.read_text(encoding="utf-8")

# When opening NAME COLOR, always start the preview cursor from the actually
# applied color. A stale preview cursor made the visual state appear one input
# behind after leaving/re-entering the submenu.
src = replace_once(
    src,
    '\t\t\tElse If(Event Player.HalamanMenu == 2);\n\t\t\t\tEvent Player.KursorWarna = Event Player.KursorWarna;',
    '\t\t\tElse If(Event Player.HalamanMenu == 2);\n\t\t\t\tEvent Player.KursorWarna = Event Player.IndeksWarna;',
    "sync color cursor on submenu entry",
)

# The main-menu NAME COLOR accent represents CURRENT, therefore it must use the
# applied index, never an abandoned preview cursor.
src = replace_once(
    src,
    '\t\t\t: Event Player.KursorUtama == 2 ? Global.DaftarWarna[Event Player.KursorWarna]\n',
    '\t\t\t: Event Player.KursorUtama == 2 ? Global.DaftarWarna[Event Player.IndeksWarna]\n',
    "main menu uses applied color",
)

SOURCE.write_text(src, encoding="utf-8")

val = VALIDATOR.read_text(encoding="utf-8")

# Legacy validation treated every submenu cursor as persistent. NAME COLOR is
# different: its preview cursor must deliberately re-enter from CURRENT so an
# abandoned preview never looks one step behind.
interact_anchor = '    if interact_rules:\n        body = mask_strings(interact_rules[0].body)\n'
anchor_at = val.find(interact_anchor)
if anchor_at < 0:
    raise SystemExit("validator interact menu anchor not found")
next_section = val.find('\n    teleport_open_rules =', anchor_at)
if next_section < 0:
    raise SystemExit("validator interact menu end not found")
segment = val[anchor_at:next_section]
legacy_color_forbidden = '            "Event Player.KursorWarna = Event Player.IndeksWarna;",\n'
if segment.count(legacy_color_forbidden) != 1:
    raise SystemExit("validator color submenu legacy forbidden not found exactly once")
segment = segment.replace(legacy_color_forbidden, '', 1)
val = val[:anchor_at] + segment + val[next_section:]

# Main Menu displays CURRENT state, so its accent must follow IndeksWarna.
legacy_main = 'Event Player.KursorUtama == 2 ? Global.DaftarWarna[Event Player.KursorWarna]'
if val.count(legacy_main) != 1:
    raise SystemExit(f"validator legacy main-menu color expectation count={val.count(legacy_main)}")
val = val.replace(
    legacy_main,
    'Event Player.KursorUtama == 2 ? Global.DaftarWarna[Event Player.IndeksWarna]',
    1,
)

check = r'''

def check_color_menu_cursor_sync(checks: Checks, source: str, rules: list[Rule]) -> None:
    clean = mask_strings(source)
    checks.require(
        "Else If(Event Player.HalamanMenu == 2);\n\t\t\t\tEvent Player.KursorWarna = Event Player.IndeksWarna;" in clean,
        "menu colore: cursore non sincronizzato al colore applicato all'ingresso",
    )
    checks.require(
        ": Event Player.KursorUtama == 2 ? Global.DaftarWarna[Event Player.IndeksWarna]" in clean,
        "menu colore: main menu non usa il colore realmente applicato",
    )
    checks.require(
        ": Event Player.KursorUtama == 2 ? Global.DaftarWarna[Event Player.KursorWarna]" not in clean,
        "menu colore: main menu usa ancora il cursore preview stale",
    )
'''
if 'def check_color_menu_cursor_sync(' not in val:
    marker = '\ndef main() -> None:\n'
    if val.count(marker) != 1:
        raise SystemExit("validator main marker not found")
    val = val.replace(marker, check + marker, 1)
    anchor = '        check_runtime_efficiency_audit(checks, source, rules)\n'
    if val.count(anchor) != 1:
        raise SystemExit("validator audit call anchor not found")
    val = val.replace(anchor, anchor + '        check_color_menu_cursor_sync(checks, source, rules)\n', 1)
VALIDATOR.write_text(val, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
line = '- **Menu colore live:** applicare un colore, navigare su un altro senza applicarlo, tornare indietro e riaprire NAME COLOR; il cursore deve partire dal colore applicato e la tinta del Main Menu deve rappresentare subito CURRENT, senza essere un input/colpo indietro.\n'
if line not in tests:
    tests += '\n' + line
TESTS.write_text(tests, encoding="utf-8")

# Refresh Workshop source blob marker required by repository validation.
data = SOURCE.read_bytes().replace(b"\r\n", b"\n")
blob = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
report = REPORT.read_text(encoding="utf-8")
report, n = re.subn(r"```text\n[0-9a-f]{40}\n```", f"```text\n{blob}\n```", report, count=1)
if n != 1:
    raise SystemExit("validation report blob marker not found")
REPORT.write_text(report, encoding="utf-8")
