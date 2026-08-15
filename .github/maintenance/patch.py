from __future__ import annotations

from pathlib import Path
import hashlib
import re

SOURCE = Path("workshop/ruang_irama.workshop")
VALIDATOR = Path("tools/validate_workshop.py")
README = Path("README.md")
PROJECT = Path("docs/PROGETTO.md")
TESTS = Path("docs/TEST.md")
REPORT = Path("docs/VALIDAZIONE.md")


def once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"{label}: expected 1 occurrence, found {n}")
    return text.replace(old, new, 1)


def bounds(text: str, prefix: str) -> tuple[int, int]:
    start = text.index(f'rule("{prefix}')
    end = text.find('\nrule("', start + 1)
    return start, len(text) if end < 0 else end


def replace_rule(text: str, prefix: str, old: str, new: str, label: str) -> str:
    s, e = bounds(text, prefix)
    block = once(text[s:e], old, new, label)
    return text[:s] + block + text[e:]


src = SOURCE.read_text(encoding="utf-8")

# State: 0 OFF, 1 = 1 HP, 2 = FULL HP. IkonKebal stores the public Halo.
src = once(src, '\t\t67: KursorPrivasiInspeksi\n}',
           '\t\t67: KursorPrivasiInspeksi\n\t\t68: ModeKebal\n\t\t69: IkonKebal\n}',
           'declare ModeKebal/IkonKebal')
src = once(src, '\t\tEvent Player.KursorPrivasiInspeksi = 0;',
           '\t\tEvent Player.KursorPrivasiInspeksi = 0;\n\t\tEvent Player.ModeKebal = 0;\n\t\tEvent Player.IkonKebal = Null;',
           'init ModeKebal/IkonKebal')

# Menu 5 navigation: OFF / 1 HP / FULL HP.
src = replace_rule(src, '06 - Menu:',
                   'Event Player.KursorKebal = (Event Player.KursorKebal + 1) % 2;',
                   'Event Player.KursorKebal = (Event Player.KursorKebal + 1) % 3;',
                   'menu5 next')
src = replace_rule(src, '07 - Menu:',
                   'Event Player.KursorKebal = (Event Player.KursorKebal + 1) % 2;',
                   'Event Player.KursorKebal = (Event Player.KursorKebal + 2) % 3;',
                   'menu5 previous')

# Spawn-room open message now covers both active modes.
src = src.replace('Unkillable: 1 HP is unavailable in Spawn Room.', 'Unkillable modes are unavailable in Spawn Room.')
src = src.replace('Kebal: 1 HP tidak tersedia di ruang muncul.', 'Mode Kebal tidak tersedia di ruang muncul.')
src = src.replace('ใช้โหมดฆ่าไม่ตาย: 1 HP ในห้องเกิดไม่ได้', 'ใช้โหมดฆ่าไม่ตายในห้องเกิดไม่ได้')

# Replace only the Menu 5 apply branch.
s, e = bounds(src, '10 - Menu:')
block = src[s:e]
a = block.index('\t\tElse If(Event Player.HalamanMenu == 5);')
b = block.index('\t\tElse If(Event Player.HalamanMenu == 6);', a)
branch = '''\t\tElse If(Event Player.HalamanMenu == 5);
\t\t\tIf(Event Player.ModeKebal != Event Player.KursorKebal);
\t\t\t\tEvent Player.ModeKebal = Event Player.KursorKebal;
\t\t\t\tEvent Player.KebalAktif = Event Player.ModeKebal != 0;
\t\t\t\tIf(Event Player.ModeKebal == 0);
\t\t\t\t\tCall Subroutine(EfekPulihkan);
\t\t\t\t\tClear Status(Event Player, Unkillable);
\t\t\t\t\tSet Damage Received(Event Player, 100);
\t\t\t\t\tIf(Is Alive(Event Player) == True);
\t\t\t\t\t\tSet Player Health(Event Player, Max Health(Event Player));
\t\t\t\t\tEnd;
\t\t\t\t\tIf(Event Player.IkonKebal != Null);
\t\t\t\t\t\tDestroy Icon(Event Player.IkonKebal);
\t\t\t\t\t\tEvent Player.IkonKebal = Null;
\t\t\t\t\tEnd;
\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Unkillable disabled.") : Event Player.IndeksBahasa == 1 ? Custom String("Mode Kebal nonaktif.") : Custom String("ปิดโหมดฆ่าไม่ตายแล้ว"));
\t\t\t\tElse;
\t\t\t\t\tCall Subroutine(EfekTerapkan);
\t\t\t\t\tSet Status(Event Player, Null, Unkillable, 9999);
\t\t\t\t\tIf(Event Player.ModeKebal == 1);
\t\t\t\t\t\tSet Damage Received(Event Player, 100);
\t\t\t\t\t\tIf(Is Alive(Event Player) == True);
\t\t\t\t\t\t\tSet Player Health(Event Player, 1);
\t\t\t\t\t\tEnd;
\t\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Unkillable: 1 HP enabled.") : Event Player.IndeksBahasa == 1 ? Custom String("Kebal: 1 HP aktif.") : Custom String("เปิดโหมดฆ่าไม่ตาย: 1 HP แล้ว"));
\t\t\t\t\tElse;
\t\t\t\t\t\tSet Damage Received(Event Player, 0);
\t\t\t\t\t\tIf(Is Alive(Event Player) == True);
\t\t\t\t\t\t\tSet Player Health(Event Player, Max Health(Event Player));
\t\t\t\t\t\tEnd;
\t\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Unkillable: FULL HP enabled.") : Event Player.IndeksBahasa == 1 ? Custom String("Kebal: FULL HP aktif.") : Custom String("เปิดโหมดฆ่าไม่ตาย: FULL HP แล้ว"));
\t\t\t\t\tEnd;
\t\t\t\t\tIf(Event Player.IkonKebal == Null);
\t\t\t\t\t\tCreate Icon(All Players(All Teams), Event Player, Halo, Visible To and Position, Global.RGB, True);
\t\t\t\t\t\tEvent Player.IkonKebal = Last Created Entity;
\t\t\t\t\tEnd;
\t\t\t\tEnd;
\t\t\tEnd;
\t\t\tCall Subroutine(GambarMenu);
'''
block = block[:a] + branch + block[b:]
src = src[:s] + block + src[e:]

# Respawn/re-application respects the selected mode.
s, e = bounds(src, '18 - Kebal:')
block = src[s:e]
block = once(block,
'''\tactions
\t{
\t\tSet Status(Event Player, Null, Unkillable, 9999);
\t}
}''',
'''\tactions
\t{
\t\tSet Status(Event Player, Null, Unkillable, 9999);
\t\tIf(Event Player.ModeKebal == 1);
\t\t\tSet Damage Received(Event Player, 100);
\t\t\tSet Player Health(Event Player, 1);
\t\tElse;
\t\t\tSet Damage Received(Event Player, 0);
\t\t\tSet Player Health(Event Player, Max Health(Event Player));
\t\tEnd;
\t}
}''', 'respawn mode behavior')
src = src[:s] + block + src[e:]

# Existing heal-to-full reset belongs only to 1 HP.
s, e = bounds(src, '18b - Kebal:')
block = src[s:e].replace('rule("18b - Kebal: Saat kesehatan penuh kembali ke satu HP")',
                         'rule("18b - Kebal: Mode 1 HP kembali ke satu saat penuh")')
block = once(block, '\t\tEvent Player.KebalAktif == True;\n',
             '\t\tEvent Player.KebalAktif == True;\n\t\tEvent Player.ModeKebal == 1;\n',
             '1HP runtime guard')
src = src[:s] + block + src[e:]

# FULL HP safety net. Damage Received 0 prevents normal damage; this catches
# external health edits and non-damage reductions.
insert = src.index('rule("18c - Kebal:')
full_rule = '''rule("18d - Kebal: Mode FULL HP selalu kembali penuh")
{
\tevent
\t{
\t\tOngoing - Each Player;
\t\tAll;
\t\tAll;
\t}

\tconditions
\t{
\t\tEvent Player.Manusia == True;
\t\tEvent Player.KebalAktif == True;
\t\tEvent Player.ModeKebal == 2;
\t\tIs In Spawn Room(Event Player) == False;
\t\tHas Spawned(Event Player) == True;
\t\tIs Alive(Event Player) == True;
\t\tHealth(Event Player) < Max Health(Event Player);
\t}

\tactions
\t{
\t\tSet Player Health(Event Player, Max Health(Event Player));
\t}
}

'''
src = src[:insert] + full_rule + src[insert:]

# Spawn-room cleanup restores all defaults and removes the Halo.
s, e = bounds(src, '18c - Kebal:')
block = src[s:e]
block = once(block,
'''\t\tIf(Event Player.KebalAktif == True);
\t\t\tEvent Player.KebalAktif = False;
\t\t\tEvent Player.KursorKebal = 0;
\t\t\tCall Subroutine(EfekPulihkan);
\t\t\tClear Status(Event Player, Unkillable);
\t\t\tIf(Is Alive(Event Player) == True);
\t\t\t\tSet Player Health(Event Player, Max Health(Event Player));
\t\t\tEnd;
\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Unkillable disabled: Spawn Room rules.") : Event Player.IndeksBahasa == 1 ? Custom String(
\t\t\t\t"Kebal dimatikan: aturan ruang muncul.") : Custom String("ปิดโหมดฆ่าไม่ตาย: 1 HP แล้ว: คุณเข้าไปในห้องเกิด"));
\t\tEnd;''',
'''\t\tIf(Event Player.KebalAktif == True);
\t\t\tEvent Player.KebalAktif = False;
\t\t\tEvent Player.ModeKebal = 0;
\t\t\tEvent Player.KursorKebal = 0;
\t\t\tCall Subroutine(EfekPulihkan);
\t\t\tClear Status(Event Player, Unkillable);
\t\t\tSet Damage Received(Event Player, 100);
\t\t\tIf(Is Alive(Event Player) == True);
\t\t\t\tSet Player Health(Event Player, Max Health(Event Player));
\t\t\tEnd;
\t\t\tIf(Event Player.IkonKebal != Null);
\t\t\t\tDestroy Icon(Event Player.IkonKebal);
\t\t\t\tEvent Player.IkonKebal = Null;
\t\t\tEnd;
\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Unkillable disabled: Spawn Room rules.") : Event Player.IndeksBahasa == 1 ? Custom String(
\t\t\t\t"Mode Kebal dimatikan: aturan ruang muncul.") : Custom String("ปิดโหมดฆ่าไม่ตาย: กฎห้องเกิด"));
\t\tEnd;''', 'spawn cleanup')
src = src[:s] + block + src[e:]

# Leave cleanup destroys the public icon if active.
src = replace_rule(src, '04 - Pemain Keluar:',
'''\t\tIf(Global.IndeksKeluar >= 0);
\t\t\tStop Camera(Event Player);''',
'''\t\tIf(Global.IndeksKeluar >= 0);
\t\t\tIf(Event Player.IkonKebal != Null);
\t\t\t\tDestroy Icon(Event Player.IkonKebal);
\t\t\t\tEvent Player.IkonKebal = Null;
\t\t\tEnd;
\t\t\tStop Camera(Event Player);''', 'leave icon cleanup')

# Main menu current mode labels.
for old, new in (
    ('Custom String("5 - UNKILLABLE: 1 HP\\nCURRENT: {0}", Event Player.KebalAktif ? Custom String("ON") : Custom String("OFF"))',
     'Custom String("5 - UNKILLABLE\\nCURRENT: {0}", Event Player.ModeKebal == 0 ? Custom String("OFF") : Event Player.ModeKebal == 1 ? Custom String("1 HP") : Custom String("FULL HP"))'),
    ('Custom String("5 - KEBAL: 1 HP\\nSAAT INI: {0}", Event Player.KebalAktif ? Custom String("AKTIF") : Custom String("MATI"))',
     'Custom String("5 - KEBAL\\nSAAT INI: {0}", Event Player.ModeKebal == 0 ? Custom String("MATI") : Event Player.ModeKebal == 1 ? Custom String("1 HP") : Custom String("FULL HP"))'),
    ('Custom String("5 - ฆ่าไม่ตาย: 1 HP\\nสถานะ: {0}", Event Player.KebalAktif ? Custom String("เปิด") : Custom String("ปิด"))',
     'Custom String("5 - ฆ่าไม่ตาย\\nสถานะ: {0}", Event Player.ModeKebal == 0 ? Custom String("ปิด") : Event Player.ModeKebal == 1 ? Custom String("1 HP") : Custom String("FULL HP"))'),
):
    src = once(src, old, new, 'main menu5 label')

# Replace Menu 5 renderer's language-dependent content while preserving layout.
s, e = bounds(src, '91h - Subrutin:')
block = src[s:e]
a = block.index('\t\t\tEvent Player.IndeksBahasa == 0 ? Custom String("{0}\\n> {1}", Custom String("5 - UNKILLABLE')
b = block.index(',\n\t\t\tTop, 100,', a)
content = '''\t\t\tEvent Player.IndeksBahasa == 0 ? Custom String("{0}\\n> {1}", Custom String("5 - UNKILLABLE {0}/3\\nCURRENT: {1}", Event Player.KursorKebal + 1,
\t\t\tEvent Player.ModeKebal == 0 ? Custom String("OFF") : Event Player.ModeKebal == 1 ? Custom String("1 HP") : Custom String("FULL HP")), Event Player.KursorKebal == 0 ? Custom String("OFF") : Event Player.KursorKebal == 1 ? Custom String("1 HP") : Custom String("FULL HP"))
\t\t\t: Event Player.IndeksBahasa == 1 ? Custom String("{0}\\n> {1}", Custom String("5 - KEBAL {0}/3\\nSAAT INI: {1}", Event Player.KursorKebal + 1,
\t\t\tEvent Player.ModeKebal == 0 ? Custom String("MATI") : Event Player.ModeKebal == 1 ? Custom String("1 HP") : Custom String("FULL HP")), Event Player.KursorKebal == 0 ? Custom String("MATI") : Event Player.KursorKebal == 1 ? Custom String("1 HP") : Custom String("FULL HP"))
\t\t\t: Custom String("{0}\\n> {1}", Custom String("5 - ฆ่าไม่ตาย {0}/3\\nสถานะ: {1}", Event Player.KursorKebal + 1,
\t\t\tEvent Player.ModeKebal == 0 ? Custom String("ปิด") : Event Player.ModeKebal == 1 ? Custom String("1 HP") : Custom String("FULL HP")), Event Player.KursorKebal == 0 ? Custom String("ปิด") : Event Player.KursorKebal == 1 ? Custom String("1 HP") : Custom String("FULL HP"))'''
block = block[:a] + content + block[b:]
src = src[:s] + block + src[e:]

SOURCE.write_text(src, encoding='utf-8')

# ---------------- validator ----------------
val = VALIDATOR.read_text(encoding='utf-8')
# Old Spawn Room message expectation.
val = val.replace('"Unkillable: 1 HP is unavailable in Spawn Room." in source', '"Unkillable modes are unavailable in Spawn Room." in source')
# Old idempotent boolean guard.
val = val.replace('"If(Event Player.KebalAktif != And(Event Player.KursorKebal == 1, Is In Spawn Room(Event Player) == False));",',
                  '"If(Event Player.ModeKebal != Event Player.KursorKebal);",')
# Old cursor-reset forbidden expression should now reference the applied mode.
val = val.replace('"Event Player.KursorKebal = Event Player.KebalAktif",', '"Event Player.KursorKebal = Event Player.ModeKebal",')
# Localization anchors use generic menu title.
val = val.replace('"5 - KEBAL: 1 HP",', '"5 - KEBAL",')
val = val.replace('"5 - ฆ่าไม่ตาย: 1 HP",', '"5 - ฆ่าไม่ตาย",')

# Spawn cleanup detector also requires mode/damage/icon cleanup.
old = '''            "Event Player.KebalAktif = False;",
            "Clear Status(Event Player, Unkillable);",
            "Set Player Health(Event Player, Max Health(Event Player));",
            "Event Player.HalamanMenu = -1;",'''
new = '''            "Event Player.KebalAktif = False;",
            "Event Player.ModeKebal = 0;",
            "Clear Status(Event Player, Unkillable);",
            "Set Damage Received(Event Player, 100);",
            "Set Player Health(Event Player, Max Health(Event Player));",
            "Destroy Icon(Event Player.IkonKebal);",
            "Event Player.HalamanMenu = -1;",'''
val = once(val, old, new, 'validator spawn cleanup')

# Ordered idempotence: mode assignment occurs after the inequality guard.
needle = '        ("If(Event Player.IndeksBahasa != Event Player.KursorBahasa);", "Event Player.IndeksBahasa = Event Player.KursorBahasa;"),\n'
if 'Event Player.ModeKebal = Event Player.KursorKebal;' not in val[val.find('ordered_pairs = ('):val.find('def check_menu_palette', val.find('ordered_pairs = ('))]:
    val = once(val, needle, needle + '        ("If(Event Player.ModeKebal != Event Player.KursorKebal);", "Event Player.ModeKebal = Event Player.KursorKebal;"),\n', 'validator ordered ModeKebal')

extra = r'''

def check_unkillable_three_modes(checks: Checks, source: str, rules: list[Rule]) -> None:
    clean = mask_strings(source)
    variables = section_body(source, "variables")
    for slot, name in ((68, "ModeKebal"), (69, "IkonKebal")):
        checks.require(re.search(rf"(?m)^\s*{slot}\s*:\s*{name}\s*$", variables) is not None, f"Unkillable: slot {slot} deve essere {name}")
    checks.require("Event Player.ModeKebal = 0;" in clean and "Event Player.IkonKebal = Null;" in clean, "Unkillable: default OFF/icon Null")
    checks.require("Event Player.KursorKebal = (Event Player.KursorKebal + 1) % 3;" in clean, "Unkillable: next non usa 3 modalità")
    checks.require("Event Player.KursorKebal = (Event Player.KursorKebal + 2) % 3;" in clean, "Unkillable: previous non usa 3 modalità")

    renderer = rules_containing(rules, "Subroutine;", "GambarKebal;")
    checks.equal(len(renderer), 1, "Unkillable renderer")
    if renderer:
        checks.require("/3" in renderer[0].body and "FULL HP" in renderer[0].body and "1 HP" in renderer[0].body, "Unkillable: menu non mostra OFF/1HP/FULLHP")

    menu = [r for r in rules if code_contains(r.body, "Event Player.PerintahMenu == 1;", "Else If(Event Player.HalamanMenu == 5);")]
    checks.equal(len(menu), 1, "Unkillable handler menu 5")
    if menu:
        body = mask_strings(menu[0].body)
        for token in (
            "If(Event Player.ModeKebal != Event Player.KursorKebal);",
            "Event Player.KebalAktif = Event Player.ModeKebal != 0;",
            "If(Event Player.ModeKebal == 1);",
            "Set Damage Received(Event Player, 100);",
            "Set Player Health(Event Player, 1);",
            "Set Damage Received(Event Player, 0);",
            "Set Player Health(Event Player, Max Health(Event Player));",
            "Create Icon(All Players(All Teams), Event Player, Halo, Visible To and Position, Global.RGB, True);",
            "Event Player.IkonKebal = Last Created Entity;",
            "Destroy Icon(Event Player.IkonKebal);",
        ):
            checks.require(token in body, f"Unkillable menu incompleto: {token}")

    full = [r for r in rules if r.name.startswith("18d - Kebal:")]
    checks.equal(len(full), 1, "Unkillable FULL HP guard")
    if full:
        body = mask_strings(full[0].body)
        checks.require("Event Player.ModeKebal == 2;" in body and "Health(Event Player) < Max Health(Event Player);" in body and "Set Player Health(Event Player, Max Health(Event Player));" in body, "Unkillable FULL HP guard incompleta")

    # Public icon is intentionally independent from Crouch Privacy and team.
    icon_calls = [call for call in call_texts(source, "Create Icon") if "Halo" in call and "Event Player" in call]
    checks.equal(len(icon_calls), 1, "Unkillable Halo public icon")
    if icon_calls:
        checks.require("All Players(All Teams)" in icon_calls[0] and "Global.RGB" in icon_calls[0] and "Visible To and Position" in icon_calls[0], "Unkillable Halo non è pubblico/RGB/follow")
        checks.require("PrivasiInspeksiAktif" not in icon_calls[0] and "Team Of(" not in icon_calls[0], "Unkillable Halo dipende dalla privacy/team")

    leave = [r for r in rules if code_contains(r.body, "Player Left Match;")]
    checks.require(bool(leave) and "Destroy Icon(Event Player.IkonKebal);" in mask_strings(leave[0].body), "Unkillable Halo cleanup leave assente")
'''
if 'def check_unkillable_three_modes(' not in val:
    val = once(val, '\ndef main() -> None:\n', extra + '\ndef main() -> None:\n', 'insert unkillable checker')
    val = once(val, '        check_arcade_features(checks, source, rules)\n',
               '        check_arcade_features(checks, source, rules)\n        check_unkillable_three_modes(checks, source, rules)\n',
               'call unkillable checker')

VALIDATOR.write_text(val, encoding='utf-8')

# ---------------- docs ----------------
readme = README.read_text(encoding='utf-8')
readme = readme.replace('`5 - Unkillable: 1 HP`', '`5 - Unkillable`')
readme += '''\n### Menu 5 — Unkillable\n\nTre modalità: **OFF**, **1 HP** e **FULL HP**. FULL HP usa Damage Received 0% e mantiene la salute al massimo. In 1 HP e FULL HP compare un **Halo pubblico** sopra al player, visibile a entrambe le squadre e indipendente da Crouch Privacy. L'Halo usa il valore `Global.RGB` presente quando viene creato e segue il player senza un loop di ricreazione.\n'''
README.write_text(readme, encoding='utf-8')

project = PROJECT.read_text(encoding='utf-8')
project += '''\n\n## Unkillable — OFF / 1 HP / FULL HP\n\n`ModeKebal`: 0=OFF, 1=1 HP, 2=FULL HP. FULL HP imposta Damage Received a 0% e ha una guardia che riporta la salute a Max Health se viene ridotta da altre modifiche. Le modalità 1 HP e FULL HP condividono un Halo creato con `Create Icon(All Players(All Teams), Event Player, Halo, Visible To and Position, Global.RGB, True)`, quindi l'indicatore non dipende da Crouch Privacy. OFF, Spawn Room e Player Left distruggono l'icona e ripristinano Damage Received a 100%.\n'''
PROJECT.write_text(project, encoding='utf-8')

tests = TESTS.read_text(encoding='utf-8')
for line in (
    '- **Unkillable 1 HP:** attivare 1 HP, verificare salute a 1, ritorno a 1 quando raggiunge il massimo e Halo visibile a tutti anche con Crouch Privacy ON.\n',
    '- **Unkillable FULL HP:** attivare FULL HP, subire danni normali e verificare che la salute non scenda; Halo visibile a tutti. Passare 1 HP ↔ FULL HP senza duplicare l’icona.\n',
    '- **Unkillable cleanup:** OFF, Spawn Room e Player Left devono rimuovere Halo; OFF/Spawn devono ripristinare Damage Received a 100%.\n',
):
    if line not in tests:
        tests += '\n' + line
TESTS.write_text(tests, encoding='utf-8')

report = REPORT.read_text(encoding='utf-8')
report += '\n- Menu 5: OFF / 1 HP / FULL HP con Halo pubblico indipendente dalla Crouch Privacy.\n'
data = SOURCE.read_bytes().replace(b'\r\n', b'\n')
blob = hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()
report, n = re.subn(r'```text\n[0-9a-f]{40}\n```', f'```text\n{blob}\n```', report, count=1)
if n != 1:
    raise SystemExit('validation blob marker missing')
REPORT.write_text(report, encoding='utf-8')
