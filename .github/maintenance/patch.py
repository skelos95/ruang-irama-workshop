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


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 occurrence, found {count}")
    return text.replace(old, new, 1)


def rule_bounds(text: str, prefix: str) -> tuple[int, int]:
    start = text.index(f'rule("{prefix}')
    end = text.find('\nrule("', start + 1)
    if end < 0:
        end = len(text)
    return start, end


def replace_in_rule(text: str, prefix: str, old: str, new: str, label: str) -> str:
    start, end = rule_bounds(text, prefix)
    block = text[start:end]
    block = replace_once(block, old, new, label)
    return text[:start] + block + text[end:]


src = SOURCE.read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# State: keep KebalAktif as the fast active flag, add the actual mode index and
# the persistent Create Icon entity reference.
# 0 = OFF, 1 = 1 HP, 2 = FULL HP.
# ---------------------------------------------------------------------------
src = replace_once(
    src,
    '\t\t67: KursorPrivasiInspeksi\n}',
    '\t\t67: KursorPrivasiInspeksi\n\t\t68: ModeKebal\n\t\t69: IkonKebal\n}',
    "declare unkillable mode/icon variables",
)
src = replace_once(
    src,
    '\t\tEvent Player.KursorPrivasiInspeksi = 0;',
    '\t\tEvent Player.KursorPrivasiInspeksi = 0;\n\t\tEvent Player.ModeKebal = 0;\n\t\tEvent Player.IkonKebal = Null;',
    "initialize unkillable mode/icon",
)

# Menu 5 now has three choices.
src = replace_in_rule(
    src,
    "06 - Menu:",
    'Event Player.KursorKebal = (Event Player.KursorKebal + 1) % 2;',
    'Event Player.KursorKebal = (Event Player.KursorKebal + 1) % 3;',
    "menu 5 next modulo 3",
)
src = replace_in_rule(
    src,
    "07 - Menu:",
    'Event Player.KursorKebal = (Event Player.KursorKebal + 1) % 2;',
    'Event Player.KursorKebal = (Event Player.KursorKebal + 2) % 3;',
    "menu 5 previous modulo 3",
)

# Spawn-room opening message is now mode-agnostic.
src = src.replace(
    'Custom String("Unkillable: 1 HP is unavailable in Spawn Room.") : Event Player.IndeksBahasa == 1 ? Custom String(\n\t\t\t\t\t\t"Kebal: 1 HP tidak tersedia di ruang muncul.") : Custom String("ใช้โหมดฆ่าไม่ตาย: 1 HP ในห้องเกิดไม่ได้")',
    'Custom String("Unkillable modes are unavailable in Spawn Room.") : Event Player.IndeksBahasa == 1 ? Custom String(\n\t\t\t\t\t\t"Mode Kebal tidak tersedia di ruang muncul.") : Custom String("ใช้โหมดฆ่าไม่ตายในห้องเกิดไม่ได้")',
)
if "Unkillable: 1 HP is unavailable in Spawn Room." in src:
    raise SystemExit("spawn-room menu message was not replaced")

# ---------------------------------------------------------------------------
# Replace Menu 5 apply logic.
# ---------------------------------------------------------------------------
start, end = rule_bounds(src, "10 - Menu:")
block = src[start:end]
branch_start = block.index('\t\tElse If(Event Player.HalamanMenu == 5);')
branch_end = block.index('\t\tElse If(Event Player.HalamanMenu == 6);', branch_start)
new_branch = '''\t\tElse If(Event Player.HalamanMenu == 5);
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
\t\t\t\t\tIf(Event Player.IkonKebal != Null);
\t\t\t\t\t\tDestroy Icon(Event Player.IkonKebal);
\t\t\t\t\tEnd;
\t\t\t\t\tCreate Icon(All Players(All Teams), Event Player, Halo, Visible To and Position, Global.RGB, True);
\t\t\t\t\tEvent Player.IkonKebal = Last Created Entity;
\t\t\t\tEnd;
\t\t\tEnd;
\t\t\tCall Subroutine(GambarMenu);
'''
block = block[:branch_start] + new_branch + block[branch_end:]
src = src[:start] + block + src[end:]

# ---------------------------------------------------------------------------
# Runtime rules: reapply correct mode after respawn, keep 1HP behavior, force
# FULL HP as a safety net, and recreate the public icon only when necessary.
# ---------------------------------------------------------------------------
start, end = rule_bounds(src, "18 - Kebal:")
old18 = src[start:end]
old18_actions = '''\t\tactions
\t{
\t\tSet Status(Event Player, Null, Unkillable, 9999);
\t}
}'''
new18_actions = '''\tactions
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
}'''
# tolerate exact one-tab actions formatting from source
if old18_actions not in old18:
    old18_actions = '''\tactions
\t{
\t\tSet Status(Event Player, Null, Unkillable, 9999);
\t}
}'''
old18 = replace_once(old18, old18_actions, new18_actions, "mode-aware respawn reapply")
src = src[:start] + old18 + src[end:]

# 1HP reset only belongs to mode 1.
start, end = rule_bounds(src, "18b - Kebal:")
rule18b = src[start:end]
rule18b = rule18b.replace('rule("18b - Kebal: Saat kesehatan penuh kembali ke satu HP")', 'rule("18b - Kebal: Mode 1 HP kembali ke satu saat penuh")')
rule18b = replace_once(
    rule18b,
    '\t\tEvent Player.KebalAktif == True;\n',
    '\t\tEvent Player.KebalAktif == True;\n\t\tEvent Player.ModeKebal == 1;\n',
    "1HP mode guard",
)
src = src[:start] + rule18b + src[end:]

# Insert FULL HP guard and icon lifecycle before Spawn Room auto-disable.
insert_at = src.index('rule("18c - Kebal:')
new_rules = '''rule("18d - Kebal: Mode FULL HP selalu kembali penuh")
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

rule("18e - Kebal: Pastikan ikon Halo terlihat oleh semua")
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
\t\tEvent Player.ModeKebal != 0;
\t\tIs In Spawn Room(Event Player) == False;
\t\tHas Spawned(Event Player) == True;
\t\tIs Alive(Event Player) == True;
\t\tOr(Event Player.IkonKebal == Null, Entity Exists(Event Player.IkonKebal) == False) == True;
\t}

\tactions
\t{
\t\tEvent Player.IkonKebal = Null;
\t\tCreate Icon(All Players(All Teams), Event Player, Halo, Visible To and Position, Global.RGB, True);
\t\tEvent Player.IkonKebal = Last Created Entity;
\t}
}

'''
src = src[:insert_at] + new_rules + src[insert_at:]

# Spawn Room cleanup: turn mode fully off, restore damage, and remove icon.
start, end = rule_bounds(src, "18c - Kebal:")
rule18c = src[start:end]
rule18c = replace_once(
    rule18c,
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
\t\tEnd;''',
    "spawn-room unkillable cleanup",
)
src = src[:start] + rule18c + src[end:]

# Player leave cleanup prevents an orphan icon entity.
src = replace_in_rule(
    src,
    "04 - Pemain Keluar:",
    '''\t\tIf(Global.IndeksKeluar >= 0);
\t\t\tStop Camera(Event Player);''',
    '''\t\tIf(Global.IndeksKeluar >= 0);
\t\t\tIf(Event Player.IkonKebal != Null);
\t\t\t\tDestroy Icon(Event Player.IkonKebal);
\t\t\t\tEvent Player.IkonKebal = Null;
\t\t\tEnd;
\t\t\tStop Camera(Event Player);''',
    "leave icon cleanup",
)

# ---------------------------------------------------------------------------
# Main menu and submenu text in EN / ID / TH.
# ---------------------------------------------------------------------------
main_replacements = {
    'Custom String("5 - UNKILLABLE: 1 HP\\nCURRENT: {0}", Event Player.KebalAktif ? Custom String("ON") : Custom String("OFF"))':
        'Custom String("5 - UNKILLABLE\\nCURRENT: {0}", Event Player.ModeKebal == 0 ? Custom String("OFF") : Event Player.ModeKebal == 1 ? Custom String("1 HP") : Custom String("FULL HP"))',
    'Custom String("5 - KEBAL: 1 HP\\nSAAT INI: {0}", Event Player.KebalAktif ? Custom String("AKTIF") : Custom String("MATI"))':
        'Custom String("5 - KEBAL\\nSAAT INI: {0}", Event Player.ModeKebal == 0 ? Custom String("MATI") : Event Player.ModeKebal == 1 ? Custom String("1 HP") : Custom String("FULL HP"))',
    'Custom String("5 - ฆ่าไม่ตาย: 1 HP\\nสถานะ: {0}", Event Player.KebalAktif ? Custom String("เปิด") : Custom String("ปิด"))':
        'Custom String("5 - ฆ่าไม่ตาย\\nสถานะ: {0}", Event Player.ModeKebal == 0 ? Custom String("ปิด") : Event Player.ModeKebal == 1 ? Custom String("1 HP") : Custom String("FULL HP"))',
}
for old, new in main_replacements.items():
    src = replace_once(src, old, new, f"main unkillable text {old[:30]}")

# Replace the renderer content expression only; keep its input colors and layout.
start, end = rule_bounds(src, "91h - Subrutin:")
renderer = src[start:end]
content_start = renderer.index('\t\t\tEvent Player.IndeksBahasa == 0 ? Custom String("{0}\\n> {1}", Custom String("5 - UNKILLABLE')
content_end = renderer.index(',\n\t\t\tTop, 100,', content_start)
new_content = '''\t\t\tEvent Player.IndeksBahasa == 0 ? Custom String("{0}\\n> {1}", Custom String("5 - UNKILLABLE {0}/3\\nCURRENT: {1}",
\t\t\tEvent Player.KursorKebal + 1, Event Player.ModeKebal == 0 ? Custom String("OFF") : Event Player.ModeKebal == 1 ? Custom String("1 HP") : Custom String("FULL HP")), Event Player.KursorKebal == 0 ? Custom String("OFF") : Event Player.KursorKebal == 1 ? Custom String("1 HP") : Custom String("FULL HP"))
\t\t\t: Event Player.IndeksBahasa == 1 ? Custom String("{0}\\n> {1}", Custom String("5 - KEBAL {0}/3\\nSAAT INI: {1}", Event Player.KursorKebal + 1,
\t\t\tEvent Player.ModeKebal == 0 ? Custom String("MATI") : Event Player.ModeKebal == 1 ? Custom String("1 HP") : Custom String("FULL HP")), Event Player.KursorKebal == 0 ? Custom String("MATI") : Event Player.KursorKebal == 1 ? Custom String("1 HP") : Custom String("FULL HP"))
\t\t\t: Custom String("{0}\\n> {1}", Custom String("5 - ฆ่าไม่ตาย {0}/3\\nสถานะ: {1}", Event Player.KursorKebal + 1, Event Player.ModeKebal == 0 ? Custom String("ปิด") : Event Player.ModeKebal == 1 ? Custom String("1 HP") : Custom String("FULL HP")),
\t\t\tEvent Player.KursorKebal == 0 ? Custom String("ปิด") : Event Player.KursorKebal == 1 ? Custom String("1 HP") : Custom String("FULL HP"))'''
renderer = renderer[:content_start] + new_content + renderer[content_end:]
src = src[:start] + renderer + src[end:]

SOURCE.write_text(src, encoding="utf-8")

# ---------------------------------------------------------------------------
# Validator: update old two-state assumptions and add public-icon invariants.
# ---------------------------------------------------------------------------
val = VALIDATOR.read_text(encoding="utf-8")

val = val.replace('(51, "KebalAktif"),\n        (52, "KursorKebal"),', '(51, "KebalAktif"),\n        (52, "KursorKebal"),\n        (68, "ModeKebal"),\n        (69, "IkonKebal"),', 1)
val = val.replace(
    '        "Set Player Health(Event Player, 1);",\n        "Health(Event Player) >= Max Health(Event Player);",',
    '        "Set Player Health(Event Player, 1);",\n        "Health(Event Player) >= Max Health(Event Player);",\n        "Health(Event Player) < Max Health(Event Player);",\n        "Set Damage Received(Event Player, 0);",\n        "Set Damage Received(Event Player, 100);",\n        "Create Icon(All Players(All Teams), Event Player, Halo, Visible To and Position, Global.RGB, True);",\n        "Destroy Icon(Event Player.IkonKebal);",\n        "Event Player.ModeKebal = Event Player.KursorKebal;",',
    1,
)
val = val.replace(
    'and "Unkillable: 1 HP is unavailable in Spawn Room." in source,',
    'and "Unkillable modes are unavailable in Spawn Room." in source,',
    1,
)
val = val.replace(
    '            "Event Player.KebalAktif = False;",\n            "Clear Status(Event Player, Unkillable);",',
    '            "Event Player.KebalAktif = False;",\n            "Event Player.ModeKebal = 0;",\n            "Clear Status(Event Player, Unkillable);",\n            "Set Damage Received(Event Player, 100);",\n            "Destroy Icon(Event Player.IkonKebal);",',
    1,
)
val = val.replace(
    '    for title in ("18 - Kebal:", "18b - Kebal:"):',
    '    for title in ("18 - Kebal:", "18b - Kebal:", "18d - Kebal:", "18e - Kebal:"):',
    1,
)

# Idempotent menu 5 is now based on mode index, not a bool.
val = val.replace(
    '"If(Event Player.KebalAktif != And(Event Player.KursorKebal == 1, Is In Spawn Room(Event Player) == False));",',
    '"If(Event Player.ModeKebal != Event Player.KursorKebal);",',
    1,
)
# Add ordered pair for mode application.
needle = '        ("If(Event Player.IndeksBahasa != Event Player.KursorBahasa);", "Event Player.IndeksBahasa = Event Player.KursorBahasa;"),\n'
addition = '        ("If(Event Player.ModeKebal != Event Player.KursorKebal);", "Event Player.ModeKebal = Event Player.KursorKebal;"),\n'
if addition not in val:
    if needle not in val:
        raise SystemExit("validator idempotent insertion anchor missing")
    val = val.replace(needle, needle + addition, 1)

# Any cursor persistence check that still assumes a boolean state must not be reintroduced.
val = val.replace('"Event Player.KursorKebal = Event Player.KebalAktif",', '"Event Player.KursorKebal = Event Player.ModeKebal",')

# Localization anchors for menu 5 changed from ': 1 HP' to the generic title.
val = val.replace('"5 - KEBAL: 1 HP",', '"5 - KEBAL",')
val = val.replace('"5 - ฆ่าไม่ตาย: 1 HP",', '"5 - ฆ่าไม่ตาย",')

# Dedicated invariant checker for the three Unkillable modes and icon privacy bypass.
new_check = r'''

def check_unkillable_modes_and_icon(checks: Checks, source: str, rules: list[Rule]) -> None:
    clean = mask_strings(source)
    variables = section_body(source, "variables")
    for slot, name in ((68, "ModeKebal"), (69, "IkonKebal")):
        checks.require(re.search(rf"(?m)^\s*{slot}\s*:\s*{name}\s*$", variables) is not None, f"Unkillable: slot player {slot} deve essere {name}")
    checks.require("Event Player.ModeKebal = 0;" in clean and "Event Player.IkonKebal = Null;" in clean, "Unkillable: default OFF/icon Null assente")

    checks.require("Event Player.KursorKebal = (Event Player.KursorKebal + 1) % 3;" in clean, "Unkillable: navigazione avanti non usa 3 modalità")
    checks.require("Event Player.KursorKebal = (Event Player.KursorKebal + 2) % 3;" in clean, "Unkillable: navigazione indietro non usa 3 modalità")

    renderers = rules_containing(rules, "Subroutine;", "GambarKebal;")
    checks.equal(len(renderers), 1, "Unkillable: renderer menu 5")
    if renderers:
        body = renderers[0].body
        checks.require("/3" in body and "FULL HP" in body and "1 HP" in body, "Unkillable: renderer non mostra OFF / 1 HP / FULL HP")

    handlers = [rule for rule in rules if code_contains(rule.body, "Event Player.PerintahMenu == 1;", "Else If(Event Player.HalamanMenu == 5);")]
    checks.equal(len(handlers), 1, "Unkillable: handler Interact menu 5")
    if handlers:
        body = mask_strings(handlers[0].body)
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
        ):
            checks.require(token in body, f"Unkillable: applicazione incompleta {token}")

    full_hp = [rule for rule in rules if rule.name.startswith("18d - Kebal:")]
    checks.equal(len(full_hp), 1, "Unkillable: guard FULL HP")
    if full_hp:
        body = mask_strings(full_hp[0].body)
        checks.require("Event Player.ModeKebal == 2;" in body and "Health(Event Player) < Max Health(Event Player);" in body and "Set Player Health(Event Player, Max Health(Event Player));" in body, "Unkillable: FULL HP non garantito")

    icon_rules = [rule for rule in rules if rule.name.startswith("18e - Kebal:")]
    checks.equal(len(icon_rules), 1, "Unkillable: lifecycle icona")
    if icon_rules:
        body = mask_strings(icon_rules[0].body)
        checks.require("All Players(All Teams)" in body, "Unkillable: icona non visibile a tutti")
        checks.require("PrivasiInspeksiAktif" not in body and "Team Of(" not in body, "Unkillable: icona dipende dalla Crouch Privacy")
        checks.require("Global.RGB" in body and "Visible To and Position" in body and "Halo" in body, "Unkillable: icona Halo/RGB/follow mancante")

    leave = [rule for rule in rules if code_contains(rule.body, "Player Left Match;")]
    checks.require(bool(leave) and "Destroy Icon(Event Player.IkonKebal);" in mask_strings(leave[0].body), "Unkillable: cleanup icona al leave assente")
'''
if 'def check_unkillable_modes_and_icon(' not in val:
    marker = '\ndef main() -> None:\n'
    if marker not in val:
        raise SystemExit("validator main marker missing")
    val = val.replace(marker, new_check + marker, 1)
    anchor = '        check_arcade_features(checks, source, rules)\n'
    if anchor not in val:
        raise SystemExit("validator unkillable call anchor missing")
    val = val.replace(anchor, anchor + '        check_unkillable_modes_and_icon(checks, source, rules)\n', 1)

VALIDATOR.write_text(val, encoding="utf-8")

# ---------------------------------------------------------------------------
# Documentation.
# ---------------------------------------------------------------------------
readme = README.read_text(encoding="utf-8")
readme = readme.replace(
    '`5 - Unkillable: 1 HP` — bloccato in Spawn Room e auto-disattivato entrando nello spawn.',
    '`5 - Unkillable` — OFF / 1 HP / FULL HP; bloccato in Spawn Room. Le modalità attive mostrano un Halo pubblico sopra al player.',
)
readme = readme.replace(
    '| 5 | Unkillable: 1 HP | ON / OFF, non nello Spawn Room |',
    '| 5 | Unkillable | OFF / 1 HP / FULL HP; Halo pubblico quando attivo |',
)
section = '''\n\n### Unkillable: 1 HP / FULL HP\n\nMenu 5 ha tre stati: OFF, 1 HP e FULL HP. In 1 HP resta attivo `Unkillable` e la salute torna a 1 ogni volta che raggiunge il massimo. In FULL HP, oltre a `Unkillable`, `Set Damage Received(..., 0)` impedisce alla barra vita di scendere per i danni normali e una guardia ripristina comunque `Max Health` se qualche altra modifica abbassa la salute. Entrambe le modalità creano un'icona `Halo` sopra al player visibile a `All Players(All Teams)`, indipendente da Crouch Privacy. L'icona usa il valore `Global.RGB` presente al momento della creazione; non viene ricreata in loop per inseguire il colore.\n'''
if '### Unkillable: 1 HP / FULL HP' not in readme:
    readme += section
README.write_text(readme, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
project = project.replace(
    '| 5 | Unkillable: 1 HP / Kebal | ON / OFF, non nello Spawn Room |',
    '| 5 | Unkillable / Kebal | OFF / 1 HP / FULL HP; Halo pubblico |',
)
project = project.replace(
    '## Unkillable: 1 HP\n\nMenu 5. Quando attivo, applica `Unkillable` e porta la salute a 1; quando la salute torna al massimo viene riportata a 1. La funzione non può essere attivata nello Spawn Room e viene disattivata automaticamente entrando nello spawn.',
    '## Unkillable: 1 HP / FULL HP\n\nMenu 5 usa `ModeKebal`: 0=OFF, 1=1 HP, 2=FULL HP. In 1 HP applica `Unkillable` e riporta la salute a 1 quando torna al massimo. In FULL HP applica `Unkillable`, imposta Damage Received a 0% e mantiene la salute al massimo. Le due modalità attive creano un Halo pubblico, separato dalla Crouch Privacy. Entrando nello Spawn Room il sistema torna a OFF, ripristina Damage Received a 100%, rimuove lo status e distrugge l’icona.',
)
PROJECT.write_text(project, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
for line in (
    '- **Menu 5 Unkillable 1 HP:** selezionare 1 HP, verificare status Unkillable, salute a 1 e ritorno a 1 quando viene curata al massimo; Halo visibile ad alleati e nemici anche con Crouch Privacy ON.\n',
    '- **Menu 5 Unkillable FULL HP:** selezionare FULL HP, verificare salute al massimo senza cali da danno normale, status Unkillable e Halo pubblico; passando a OFF devono tornare Damage Received 100%, salute massima normale e nessuna icona.\n',
    '- **Unkillable Spawn Room:** con 1 HP o FULL HP entrare nello spawn: modalità OFF, cursore 0, status rimosso, Damage Received 100% e Halo distrutto.\n',
):
    if line not in tests:
        tests += '\n' + line
TESTS.write_text(tests, encoding="utf-8")

report = REPORT.read_text(encoding="utf-8")
report = report.replace(
    '- Menu 5 Unkillable/Kebal 1 HP e Menu 6 Hero Voice;',
    '- Menu 5 Unkillable/Kebal con OFF / 1 HP / FULL HP, Halo pubblico RGB-snapshot e Menu 6 Hero Voice;',
)

# Refresh exact Workshop blob marker.
data = SOURCE.read_bytes().replace(b"\r\n", b"\n")
blob = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
report, n = re.subn(r"```text\n[0-9a-f]{40}\n```", f"```text\n{blob}\n```", report, count=1)
if n != 1:
    raise SystemExit("validation report blob marker not found")
REPORT.write_text(report, encoding="utf-8")
