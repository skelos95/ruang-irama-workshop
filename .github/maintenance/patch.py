from __future__ import annotations

from pathlib import Path
import hashlib
import re

source_path = Path('workshop/ruang_irama.workshop')
validator_path = Path('tools/validate_workshop.py')
readme_path = Path('README.md')
project_path = Path('docs/PROGETTO.md')
test_doc_path = Path('docs/TEST.md')
report_path = Path('docs/VALIDAZIONE.md')

src = source_path.read_text(encoding='utf-8')

# 1) Arcade menu: keep the last cursor positions when reopening.
open_start = src.index('Event Player.MenuTerbuka = True;')
open_end = src.index('Disallow Button(Event Player, Button(Melee));', open_start)
open_block = src[open_start:open_end]
old_open = '''Event Player.MenuTerbuka = True;\n\t\t\tEvent Player.HalamanMenu = -1;\n\t\t\tEvent Player.KursorUtama = 0;\n\t\t\tEvent Player.KursorGenre = Event Player.IndeksGenre >= 0 ? Event Player.IndeksGenre : 0;\n\t\t\tEvent Player.KursorKamera = 0;\n\t\t\tCall Subroutine(SegarkanTargetKamera);\n\t\t\tIf(Event Player.ModeKamera == 1);\n\t\t\t\tEvent Player.KursorKamera = 1;\n\t\t\tElse If(And(Event Player.ModeKamera == 2, Array Contains(Event Player.DaftarTargetKamera, Event Player.TargetKamera)));\n\t\t\t\tEvent Player.KursorKamera = Index Of Array Value(Event Player.DaftarTargetKamera, Event Player.TargetKamera) + 2;\n\t\t\tEnd;\n\t\t\tEvent Player.KursorWarna = Event Player.IndeksWarna;\n\t\t\tEvent Player.KursorBahasa = Event Player.IndeksBahasa;\n\t\t\tEvent Player.KursorBalasDendam = 0;\n\t\t\tCall Subroutine(SegarkanTargetBalasDendam);\n\t\t\tEvent Player.KursorUnkillable = Event Player.UnkillableAktif ? 1 : 0;\n\t\t\tEvent Player.KursorSuara = Event Player.IndeksSuara;\n\t\t\t'''
new_open = '''Event Player.MenuTerbuka = True;\n\t\t\tEvent Player.HalamanMenu = -1;\n\t\t\tCall Subroutine(SegarkanTargetKamera);\n\t\t\tCall Subroutine(SegarkanTargetBalasDendam);\n\t\t\t'''
if old_open not in open_block:
    raise SystemExit('Arcade menu open reset block not found')
open_block = open_block.replace(old_open, new_open, 1)
src = src[:open_start] + open_block + src[open_end:]

# 2) Entering each submenu must preserve its own cursor, only refreshing dynamic lists.
rule10_start = src.index('rule("10 - Menu: Interaksi membuka atau menerapkan pilihan")')
rule10_end = src.index('\nrule("11 -', rule10_start)
rule10 = src[rule10_start:rule10_end]

replacements = {
    'Event Player.KursorGenre = Event Player.IndeksGenre >= 0 ? Event Player.IndeksGenre : 0;': 'Event Player.KursorGenre = Event Player.KursorGenre;',
    'Event Player.KursorWarna = Event Player.IndeksWarna;': 'Event Player.KursorWarna = Event Player.KursorWarna;',
    'Event Player.KursorBahasa = Event Player.IndeksBahasa;': 'Event Player.KursorBahasa = Event Player.KursorBahasa;',
    'Event Player.KursorBalasDendam = 0;': 'Event Player.KursorBalasDendam = Event Player.KursorBalasDendam;',
    'Event Player.KursorUnkillable = Event Player.UnkillableAktif ? 1 : 0;': 'Event Player.KursorUnkillable = Event Player.KursorUnkillable;',
    'Event Player.KursorSuara = Event Player.IndeksSuara;': 'Event Player.KursorSuara = Event Player.KursorSuara;',
}
for old, new in replacements.items():
    if old not in rule10:
        raise SystemExit(f'submenu reset not found: {old}')
    rule10 = rule10.replace(old, new, 1)

old_camera = '''\t\t\tElse If(Event Player.HalamanMenu == 1);\n\t\t\t\tEvent Player.KursorKamera = 0;\n\t\t\t\tCall Subroutine(SegarkanTargetKamera);\n\t\t\t\tIf(Event Player.ModeKamera == 1);\n\t\t\t\t\tEvent Player.KursorKamera = 1;\n\t\t\t\tElse If(And(Event Player.ModeKamera == 2, Array Contains(Event Player.DaftarTargetKamera, Event Player.TargetKamera)));\n\t\t\t\t\tEvent Player.KursorKamera = Index Of Array Value(Event Player.DaftarTargetKamera, Event Player.TargetKamera) + 2;\n\t\t\t\tEnd;'''
new_camera = '''\t\t\tElse If(Event Player.HalamanMenu == 1);\n\t\t\t\tCall Subroutine(SegarkanTargetKamera);'''
if old_camera not in rule10:
    raise SystemExit('camera submenu reset block not found')
rule10 = rule10.replace(old_camera, new_camera, 1)
src = src[:rule10_start] + rule10 + src[rule10_end:]

# 3) Standalone Crouch teleport overlay also remembers its last index.
tele_start = src.index('Event Player.TeleportCrouchAktif = True;')
tele_end = src.index('Disallow Button(Event Player, Button(Primary Fire));', tele_start)
tele_block = src[tele_start:tele_end]
if '\t\tEvent Player.KursorTeleportasi = 0;\n' not in tele_block:
    raise SystemExit('teleport overlay cursor reset not found')
tele_block = tele_block.replace('\t\tEvent Player.KursorTeleportasi = 0;\n', '', 1)
src = src[:tele_start] + tele_block + src[tele_end:]

# 4) CTF objective status in the teleport HUD: Flag Position is valid even when Objective Position is unavailable.
# We only change the visual availability predicate; teleport execution already uses Flag Position(enemy team).
old_pred = 'Distance Between(Objective Position(Objective Index), Vector(0, 0, 0)) <= 0.100 ? Custom String('
new_pred = 'And(Current Game Mode != Game Mode(Capture The Flag), Distance Between(Objective Position(Objective Index), Vector(0, 0, 0)) <= 0.100) ? Custom String('
count = src.count(old_pred)
if count != 3:
    raise SystemExit(f'expected 3 objective HUD availability predicates, found {count}')
src = src.replace(old_pred, new_pred)

source_path.write_text(src, encoding='utf-8')

# Validator protections.
val = validator_path.read_text(encoding='utf-8')
anchor = '''    checks.require(\n        re.search(r"KursorGenre\\s*=\\s*\\([^;]+\\+\\s*90\\)\\s*%\\s*100", clean) is not None,\n        "salto musicale -10 assente",\n    )\n'''
extra = anchor + '''    menu_open_rules = [\n        rule for rule in rules\n        if code_contains(rule.body, "Event Player.MenuTerbuka = True;", "Event Player.HalamanMenu = -1;")\n    ]\n    checks.equal(len(menu_open_rules), 1, "apertura Arcade Menu")\n    if menu_open_rules:\n        opening = mask_strings(menu_open_rules[0].body)\n        for forbidden in (\n            "Event Player.KursorUtama = 0;",\n            "Event Player.KursorGenre = Event Player.IndeksGenre",\n            "Event Player.KursorKamera = 0;",\n            "Event Player.KursorWarna = Event Player.IndeksWarna;",\n            "Event Player.KursorBahasa = Event Player.IndeksBahasa;",\n            "Event Player.KursorBalasDendam = 0;",\n            "Event Player.KursorUnkillable = Event Player.UnkillableAktif",\n            "Event Player.KursorSuara = Event Player.IndeksSuara;",\n        ):\n            checks.require(forbidden not in opening, f"menu reopen resetta il cursore: {forbidden}")\n\n    interact_rules = [rule for rule in rules if code_contains(rule.body, "Event Player.PerintahMenu == 1;", "Event Player.HalamanMenu = Global.KodeMenu[Event Player.KursorUtama];")]\n    checks.equal(len(interact_rules), 1, "dispatcher Interact menu")\n    if interact_rules:\n        body = mask_strings(interact_rules[0].body)\n        for forbidden in (\n            "Event Player.KursorGenre = Event Player.IndeksGenre",\n            "Event Player.KursorKamera = 0;",\n            "Event Player.KursorWarna = Event Player.IndeksWarna;",\n            "Event Player.KursorBahasa = Event Player.IndeksBahasa;",\n            "Event Player.KursorBalasDendam = 0;",\n            "Event Player.KursorUnkillable = Event Player.UnkillableAktif",\n            "Event Player.KursorSuara = Event Player.IndeksSuara;",\n        ):\n            checks.require(forbidden not in body, f"submenu resetta il cursore: {forbidden}")\n\n    teleport_open_rules = [rule for rule in rules if code_contains(rule.body, "Event Player.TeleportCrouchAktif = True;")]\n    checks.equal(len(teleport_open_rules), 1, "apertura teleport Crouch")\n    if teleport_open_rules:\n        checks.require(\n            "Event Player.KursorTeleportasi = 0;" not in mask_strings(teleport_open_rules[0].body),\n            "teleport Crouch resetta ancora il cursore a zero",\n        )\n\n    checks.equal(\n        source.count('And(Current Game Mode != Game Mode(Capture The Flag), Distance Between(Objective Position(Objective Index), Vector(0, 0, 0)) <= 0.100) ? Custom String('),\n        3,\n        "HUD teleport CTF non deve mostrare unavailable basandosi su Objective Position",\n    )\n'''
if val.count(anchor) != 1:
    raise SystemExit('validator menu anchor not found')
val = val.replace(anchor, extra, 1)
validator_path.write_text(val, encoding='utf-8')

# Documentation.
readme = readme_path.read_text(encoding='utf-8')
line = '- I cursori del menu restano memorizzati: chiudendo e riaprendo Arcade Menu o un submenu si riparte dall’ultima voce selezionata; anche il menu Teleport Crouch conserva l’ultimo indice.'
if line not in readme:
    readme += '\n' + line + '\n'
readme_path.write_text(readme, encoding='utf-8')

project = project_path.read_text(encoding='utf-8')
section = '''\n\n### Memoria cursori menu\n\nI cursori di Main Menu, Soundtrack, Camera, Name Color, HUD Language, Revenge, Unkillable, Voice Modifier e Teleport Crouch non vengono più riallineati alla prima voce o al valore applicato quando il menu viene riaperto. Le liste dinamiche Camera/Revenge continuano a essere aggiornate e clampate quando i target cambiano. In Capture the Flag lo stato visivo di `Current Objective` non dipende più da `Objective Position`, perché il teleport usa la bandiera nemica tramite `Flag Position`.\n'''
if '### Memoria cursori menu' not in project:
    project += section
project_path.write_text(project, encoding='utf-8')

tests = test_doc_path.read_text(encoding='utf-8')
for line in (
    '- **Memoria menu live:** spostare ogni menu/submenu su una voce diversa dalla prima, chiudere e riaprire; deve ripartire dalla stessa voce. Ripetere anche con Teleport Crouch.\n',
    '- **CTF teleport HUD live:** su `Current Objective` non deve comparire `UNAVAILABLE IN THIS MODE`; il teleport deve continuare a portare vicino alla bandiera nemica.\n',
):
    if line not in tests:
        tests += '\n' + line

test_doc_path.write_text(tests, encoding='utf-8')

# Update source blob marker.
data = source_path.read_bytes().replace(b'\r\n', b'\n')
blob = hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()
report = report_path.read_text(encoding='utf-8')
report, n = re.subn(r'```text\n[0-9a-f]{40}\n```', f'```text\n{blob}\n```', report, count=1)
if n != 1:
    raise SystemExit('validation report blob marker not found')
report_path.write_text(report, encoding='utf-8')
