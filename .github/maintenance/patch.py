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
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 occurrence, found {count}")
    return text.replace(old, new, 1)


def rule_bounds(text: str, prefix: str) -> tuple[int, int]:
    start = text.index(f'rule("{prefix}')
    end = text.find('\nrule("', start + 1)
    return start, len(text) if end < 0 else end


src = SOURCE.read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# Menu 5 opening must ONLY sync the cursor to the applied mode. The previous
# patch accidentally placed apply logic in this opening branch while leaving
# the legacy 2-state apply branch later in the same dispatcher.
# ---------------------------------------------------------------------------
s, e = rule_bounds(src, "10 - Menu:")
block = src[s:e]
open_start = block.index('\t\t\tElse If(Event Player.HalamanMenu == 5);')
open_end = block.index('\t\t\tElse If(Event Player.HalamanMenu == 6);', open_start)
open_branch = '''\t\t\tElse If(Event Player.HalamanMenu == 5);
\t\t\t\tEvent Player.KursorKebal = Event Player.ModeKebal;
'''
block = block[:open_start] + open_branch + block[open_end:]

# Replace the actual apply branch (the second Menu 5 branch) with the exclusive
# 3-state implementation. ModeKebal is the single source of truth:
# 0=OFF, 1=1 HP, 2=FULL HP.
apply_start = block.index('\t\tElse If(Event Player.HalamanMenu == 5);', open_end - (open_end - open_start))
# The first occurrence above can still be the nested opening branch; find the
# apply branch after the page-4 handler.
page4 = block.index('\t\tElse If(Event Player.HalamanMenu == 4);')
apply_start = block.index('\t\tElse If(Event Player.HalamanMenu == 5);', page4)
apply_end = block.index('\t\tElse If(Event Player.HalamanMenu == 6);', apply_start)
apply_branch = '''\t\tElse If(Event Player.HalamanMenu == 5);
\t\t\tIf(Event Player.ModeKebal != Event Player.KursorKebal);
\t\t\t\tIf(And(Event Player.KursorKebal == 1, Is In Spawn Room(Event Player) == True));
\t\t\t\t\tEvent Player.KursorKebal = Event Player.ModeKebal;
\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Unkillable: 1 HP is unavailable in Spawn Room. FULL HP is still available.") : Event Player.IndeksBahasa == 1 ? Custom String("Kebal: 1 HP tidak tersedia di ruang muncul. FULL HP tetap tersedia.") : Custom String("ใช้โหมดฆ่าไม่ตาย: 1 HP ในห้องเกิดไม่ได้ แต่ FULL HP ยังใช้ได้"));
\t\t\t\tElse;
\t\t\t\t\tEvent Player.ModeKebal = Event Player.KursorKebal;
\t\t\t\t\tEvent Player.KebalAktif = Event Player.ModeKebal != 0;
\t\t\t\t\tIf(Event Player.ModeKebal == 0);
\t\t\t\t\t\tCall Subroutine(EfekPulihkan);
\t\t\t\t\t\tClear Status(Event Player, Unkillable);
\t\t\t\t\t\tSet Damage Received(Event Player, 100);
\t\t\t\t\t\tIf(Is Alive(Event Player) == True);
\t\t\t\t\t\t\tSet Player Health(Event Player, Max Health(Event Player));
\t\t\t\t\t\tEnd;
\t\t\t\t\t\tIf(Event Player.IkonKebal != Null);
\t\t\t\t\t\t\tDestroy Icon(Event Player.IkonKebal);
\t\t\t\t\t\t\tEvent Player.IkonKebal = Null;
\t\t\t\t\t\tEnd;
\t\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Unkillable disabled.") : Event Player.IndeksBahasa == 1 ? Custom String("Mode Kebal nonaktif.") : Custom String("ปิดโหมดฆ่าไม่ตายแล้ว"));
\t\t\t\t\tElse;
\t\t\t\t\t\tCall Subroutine(EfekTerapkan);
\t\t\t\t\t\tClear Status(Event Player, Unkillable);
\t\t\t\t\t\tSet Status(Event Player, Null, Unkillable, 9999);
\t\t\t\t\t\tIf(Event Player.ModeKebal == 1);
\t\t\t\t\t\t\tSet Damage Received(Event Player, 100);
\t\t\t\t\t\t\tIf(Is Alive(Event Player) == True);
\t\t\t\t\t\t\t\tSet Player Health(Event Player, 1);
\t\t\t\t\t\t\tEnd;
\t\t\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Unkillable: 1 HP enabled.") : Event Player.IndeksBahasa == 1 ? Custom String("Kebal: 1 HP aktif.") : Custom String("เปิดโหมดฆ่าไม่ตาย: 1 HP แล้ว"));
\t\t\t\t\t\tElse;
\t\t\t\t\t\t\tSet Damage Received(Event Player, 0);
\t\t\t\t\t\t\tIf(Is Alive(Event Player) == True);
\t\t\t\t\t\t\t\tSet Player Health(Event Player, Max Health(Event Player));
\t\t\t\t\t\t\tEnd;
\t\t\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Unkillable: FULL HP enabled.") : Event Player.IndeksBahasa == 1 ? Custom String("Kebal: FULL HP aktif.") : Custom String("เปิดโหมดฆ่าไม่ตาย: FULL HP แล้ว"));
\t\t\t\t\t\tEnd;
\t\t\t\t\t\tIf(Event Player.IkonKebal == Null);
\t\t\t\t\t\t\tCreate Icon(All Players(All Teams), Event Player, Halo, Visible To and Position, Global.RGB, True);
\t\t\t\t\t\t\tEvent Player.IkonKebal = Last Created Entity;
\t\t\t\t\t\tEnd;
\t\t\t\t\tEnd;
\t\t\t\tEnd;
\t\t\tEnd;
\t\t\tCall Subroutine(GambarMenu);
'''
block = block[:apply_start] + apply_branch + block[apply_end:]
src = src[:s] + block + src[e:]

# ---------------------------------------------------------------------------
# Runtime: FULL HP is valid inside Spawn Room. 1 HP remains forbidden there.
# ---------------------------------------------------------------------------
s, e = rule_bounds(src, "18 - Kebal:")
block = src[s:e]
block = once(
    block,
    '\t\tIs In Spawn Room(Event Player) == False;\n',
    '\t\tOr(Event Player.ModeKebal == 2, Is In Spawn Room(Event Player) == False) == True;\n',
    "respawn guard allows FULL HP in Spawn Room",
)
src = src[:s] + block + src[e:]

s, e = rule_bounds(src, "18d - Kebal:")
block = src[s:e]
block = once(
    block,
    '\t\tIs In Spawn Room(Event Player) == False;\n',
    '',
    "FULL HP guard must also run in Spawn Room",
)
src = src[:s] + block + src[e:]

# Spawn Room auto-reset now applies ONLY to mode 1. FULL HP persists, keeps
# Unkillable/Damage Received 0 and keeps the public Halo.
s, e = rule_bounds(src, "18c - Kebal:")
spawn_rule = '''rule("18c - Kebal: Nonaktifkan hanya mode 1 HP di Spawn Room")
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
\t\tEvent Player.ModeKebal == 1;
\t\tIs In Spawn Room(Event Player) == True;
\t}

\tactions
\t{
\t\tEvent Player.KebalAktif = False;
\t\tEvent Player.ModeKebal = 0;
\t\tEvent Player.KursorKebal = 0;
\t\tCall Subroutine(EfekPulihkan);
\t\tClear Status(Event Player, Unkillable);
\t\tSet Damage Received(Event Player, 100);
\t\tIf(Is Alive(Event Player) == True);
\t\t\tSet Player Health(Event Player, Max Health(Event Player));
\t\tEnd;
\t\tIf(Event Player.IkonKebal != Null);
\t\t\tDestroy Icon(Event Player.IkonKebal);
\t\t\tEvent Player.IkonKebal = Null;
\t\tEnd;
\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Unkillable: 1 HP disabled in Spawn Room.") : Event Player.IndeksBahasa == 1 ? Custom String("Kebal: 1 HP dimatikan di ruang muncul.") : Custom String("ปิดโหมดฆ่าไม่ตาย: 1 HP ในห้องเกิดแล้ว"));
\t\tIf(And(Event Player.MenuTerbuka == True, Event Player.HalamanMenu == 5));
\t\t\tCall Subroutine(GambarMenu);
\t\tEnd;
\t}
}

'''
src = src[:s] + spawn_rule + src[e:]

# Guard against the exact legacy two-state dispatcher resurfacing.
for stale in (
    'If(Event Player.KebalAktif != And(Event Player.KursorKebal == 1, Is In Spawn Room(Event Player) == False));',
    'Event Player.KebalAktif = And(Event Player.KursorKebal == 1, Is In Spawn Room(Event Player) == False);',
):
    if stale in src:
        raise SystemExit(f"legacy two-state Unkillable logic still present: {stale}")

SOURCE.write_text(src, encoding="utf-8")

# ---------------------------------------------------------------------------
# Validator migration: assert exclusive transitions and FULL HP Spawn behavior.
# ---------------------------------------------------------------------------
val = VALIDATOR.read_text(encoding="utf-8")

# Replace the old Spawn Room detector and old 18/18b guard expectation.
old_arcade = '''    spawn_disable = [
        rule
        for rule in rules
        if code_contains(
            rule.body,
            "Is In Spawn Room(Event Player) == True;",
            "Event Player.KebalAktif = False;",
            "Event Player.ModeKebal = 0;",
            "Clear Status(Event Player, Unkillable);",
            "Set Damage Received(Event Player, 100);",
            "Set Player Health(Event Player, Max Health(Event Player));",
            "Destroy Icon(Event Player.IkonKebal);",
            "Event Player.HalamanMenu = -1;",
        )
    ]
    checks.equal(len(spawn_disable), 1, "regola auto-disattivazione Unkillable in Spawn Room")
    for title in ("18 - Kebal:", "18b - Kebal:"):
        matching = [rule for rule in rules if rule.name.startswith(title)]
        checks.equal(len(matching), 1, f"regola {title} per guard Spawn Room")
        if matching:
            checks.require(
                code_contains(matching[0].body, "Is In Spawn Room(Event Player) == False;"),
                f"{title} non esclude la Spawn Room",
            )'''
new_arcade = '''    spawn_disable = [
        rule
        for rule in rules
        if code_contains(
            rule.body,
            "Event Player.ModeKebal == 1;",
            "Is In Spawn Room(Event Player) == True;",
            "Event Player.KebalAktif = False;",
            "Event Player.ModeKebal = 0;",
            "Clear Status(Event Player, Unkillable);",
            "Set Damage Received(Event Player, 100);",
            "Set Player Health(Event Player, Max Health(Event Player));",
            "Destroy Icon(Event Player.IkonKebal);",
        )
    ]
    checks.equal(len(spawn_disable), 1, "regola auto-disattivazione solo 1 HP in Spawn Room")

    one_hp = [rule for rule in rules if rule.name.startswith("18b - Kebal:")]
    checks.equal(len(one_hp), 1, "regola 1 HP per guard Spawn Room")
    if one_hp:
        checks.require(
            code_contains(one_hp[0].body, "Is In Spawn Room(Event Player) == False;"),
            "1 HP deve restare escluso dalla Spawn Room",
        )

    reapply = [rule for rule in rules if rule.name.startswith("18 - Kebal:")]
    checks.equal(len(reapply), 1, "regola riapplicazione Unkillable")
    if reapply:
        body = mask_strings(reapply[0].body)
        checks.require(
            "Or(Event Player.ModeKebal == 2, Is In Spawn Room(Event Player) == False) == True;" in body,
            "riapplicazione: FULL HP non resta valido in Spawn Room",
        )

    full_hp = [rule for rule in rules if rule.name.startswith("18d - Kebal:")]
    checks.equal(len(full_hp), 1, "regola FULL HP per Spawn Room")
    if full_hp:
        checks.require(
            "Is In Spawn Room(Event Player) == False;" not in mask_strings(full_hp[0].body),
            "FULL HP non deve essere escluso dalla Spawn Room",
        )'''
val = once(val, old_arcade, new_arcade, "validator arcade Spawn Room contract")

# Replace the dedicated checker with a stricter one that catches the duplicate
# legacy apply branch and validates 1HP -> FULLHP / FULLHP -> 1HP transitions.
start = val.index('def check_unkillable_three_modes(')
end = val.index('\ndef main() -> None:', start)
new_checker = r'''def check_unkillable_three_modes(checks: Checks, source: str, rules: list[Rule]) -> None:
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

    handlers = [r for r in rules if code_contains(r.body, "Event Player.PerintahMenu == 1;", "Event Player.HalamanMenu = Global.KodeMenu")]
    checks.equal(len(handlers), 1, "Unkillable handler menu")
    if handlers:
        raw = handlers[0].body
        body = mask_strings(raw)
        compact = re.sub(r"\s+", "", body)

        # Opening page 5 only mirrors the applied mode; it must never apply it.
        checks.require(
            "ElseIf(EventPlayer.HalamanMenu==5);EventPlayer.KursorKebal=EventPlayer.ModeKebal;ElseIf(EventPlayer.HalamanMenu==6);" in compact,
            "Unkillable: apertura menu 5 non sincronizza soltanto il cursore",
        )
        checks.equal(body.count("Event Player.ModeKebal = Event Player.KursorKebal;"), 1, "Unkillable: una sola assegnazione modalità nel dispatcher")
        checks.require("KebalAktif != And(Event Player.KursorKebal == 1" not in body, "Unkillable: logica legacy ON/OFF ancora presente")
        checks.require("KebalAktif = And(Event Player.KursorKebal == 1" not in body, "Unkillable: assegnazione legacy ON/OFF ancora presente")

        # 1 HP cannot be enabled inside Spawn Room; FULL HP remains selectable.
        for token in (
            "If(Event Player.ModeKebal != Event Player.KursorKebal);",
            "If(And(Event Player.KursorKebal == 1, Is In Spawn Room(Event Player) == True));",
            "Event Player.KursorKebal = Event Player.ModeKebal;",
            "Event Player.ModeKebal = Event Player.KursorKebal;",
            "Event Player.KebalAktif = Event Player.ModeKebal != 0;",
            "If(Event Player.ModeKebal == 0);",
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

        mode_assignment = body.find("Event Player.ModeKebal = Event Player.KursorKebal;")
        one_hp_branch = body.find("If(Event Player.ModeKebal == 1);", mode_assignment)
        damage_100 = body.find("Set Damage Received(Event Player, 100);", one_hp_branch)
        hp_one = body.find("Set Player Health(Event Player, 1);", damage_100)
        full_else = body.find("Else;", hp_one)
        damage_zero = body.find("Set Damage Received(Event Player, 0);", full_else)
        hp_full = body.find("Set Player Health(Event Player, Max Health(Event Player));", damage_zero)
        checks.require(
            0 <= mode_assignment < one_hp_branch < damage_100 < hp_one < full_else < damage_zero < hp_full,
            "Unkillable: transizione esclusiva 1 HP / FULL HP in ordine errato",
        )

    one_hp = [r for r in rules if r.name.startswith("18b - Kebal:")]
    checks.equal(len(one_hp), 1, "Unkillable 1 HP guard")
    if one_hp:
        body = mask_strings(one_hp[0].body)
        checks.require("Event Player.ModeKebal == 1;" in body and "Is In Spawn Room(Event Player) == False;" in body, "Unkillable: 1 HP non confinato fuori Spawn Room")

    full = [r for r in rules if r.name.startswith("18d - Kebal:")]
    checks.equal(len(full), 1, "Unkillable FULL HP guard")
    if full:
        body = mask_strings(full[0].body)
        checks.require("Event Player.ModeKebal == 2;" in body and "Health(Event Player) < Max Health(Event Player);" in body and "Set Player Health(Event Player, Max Health(Event Player));" in body, "Unkillable FULL HP guard incompleta")
        checks.require("Is In Spawn Room(Event Player) == False;" not in body, "Unkillable FULL HP si resetta ancora in Spawn Room")

    spawn = [r for r in rules if r.name.startswith("18c - Kebal:")]
    checks.equal(len(spawn), 1, "Unkillable Spawn Room reset")
    if spawn:
        body = mask_strings(spawn[0].body)
        checks.require("Event Player.ModeKebal == 1;" in body, "Spawn Room reset non limitato a 1 HP")
        checks.require("Event Player.ModeKebal == 2;" not in body, "Spawn Room reset coinvolge FULL HP")
        checks.require("Event Player.HalamanMenu = -1;" not in body, "Spawn Room non deve chiudere il menu 5 per FULL HP")

    # Public icon is intentionally independent from Crouch Privacy and team.
    icon_calls = [call for call in call_texts(source, "Create Icon") if "Halo" in call and "Event Player" in call]
    checks.equal(len(icon_calls), 1, "Unkillable Halo public icon")
    if icon_calls:
        checks.require("All Players(All Teams)" in icon_calls[0] and "Global.RGB" in icon_calls[0] and "Visible To and Position" in icon_calls[0], "Unkillable Halo non è pubblico/RGB/follow")
        checks.require("PrivasiInspeksiAktif" not in icon_calls[0] and "Team Of(" not in icon_calls[0], "Unkillable Halo dipende dalla privacy/team")

    leave = [r for r in rules if code_contains(r.body, "Player Left Match;")]
    checks.require(bool(leave) and "Destroy Icon(Event Player.IkonKebal);" in mask_strings(leave[0].body), "Unkillable Halo cleanup leave assente")
'''
val = val[:start] + new_checker + val[end:]

VALIDATOR.write_text(val, encoding="utf-8")

# ---------------------------------------------------------------------------
# Documentation / live-test plan.
# ---------------------------------------------------------------------------
readme = README.read_text(encoding="utf-8")
readme = readme.replace(
    "OFF, Spawn Room e Player Left distruggono l'icona e ripristinano Damage Received a 100%.",
    "OFF e Player Left distruggono l'icona. La Spawn Room resetta solo la modalità 1 HP; FULL HP resta attiva, mantiene Damage Received a 0% e conserva l'Halo.",
)
if "FULL HP resta attiva nella Spawn Room" not in readme:
    readme += "\n**Correzione Spawn Room:** FULL HP resta attiva nella Spawn Room. Solo 1 HP viene disattivata automaticamente. Il passaggio 1 HP → FULL HP porta subito la salute al massimo e Damage Received a 0%; FULL HP → 1 HP ripristina Damage Received a 100% e porta la salute a 1.\n"
README.write_text(readme, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
project = project.replace(
    "OFF, Spawn Room e Player Left distruggono l'icona e ripristinano Damage Received a 100%.",
    "OFF e Player Left distruggono l'icona. La Spawn Room disattiva esclusivamente ModeKebal=1; ModeKebal=2 resta attivo con Damage Received 0%, Max Health e Halo pubblico.",
)
project += "\n\n### Transizioni Unkillable esclusive\n\n`ModeKebal` è l'unica modalità applicata: 0=OFF, 1=1 HP, 2=FULL HP. Aprire Menu 5 sincronizza soltanto il cursore e non cambia lo stato. Applicare FULL HP dopo 1 HP imposta prima `ModeKebal=2`, poi Damage Received 0% e Max Health: la regola 1 HP smette immediatamente di essere eleggibile. Applicare 1 HP dopo FULL HP imposta `ModeKebal=1`, Damage Received 100% e salute 1. Dentro Spawn Room 1 HP non può essere applicata e viene disattivata se il player vi entra; FULL HP rimane attiva.\n"
PROJECT.write_text(project, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
for line in (
    "- **Unkillable 1 HP → FULL HP:** attivare 1 HP, poi selezionare FULL HP senza passare da OFF; verificare Mode FULL HP, salute massima, Damage Received 0%, nessun ritorno a 1 HP e un solo Halo.\n",
    "- **Unkillable FULL HP → 1 HP:** fuori Spawn Room passare direttamente da FULL HP a 1 HP; verificare Damage Received 100%, salute 1 e nessun comportamento FULL HP residuo.\n",
    "- **FULL HP in Spawn Room:** entrare nello spawn con FULL HP attiva; verificare che ModeKebal resti FULL HP, salute massima, Damage Received 0%, Unkillable e Halo restino attivi.\n",
    "- **1 HP in Spawn Room:** entrare nello spawn con 1 HP attiva; verificare reset a OFF, salute massima, Damage Received 100%, status e Halo rimossi. Provare anche a selezionare 1 HP mentre si è già nello spawn: non deve sostituire OFF/FULL HP.\n",
):
    if line not in tests:
        tests += "\n" + line
TESTS.write_text(tests, encoding="utf-8")

report = REPORT.read_text(encoding="utf-8")
report += "\n- Unkillable: transizioni esclusive OFF/1 HP/FULL HP; Spawn Room resetta solo 1 HP, FULL HP persiste.\n"
# Refresh the exact Workshop git-blob marker required by validation.
data = SOURCE.read_bytes().replace(b"\r\n", b"\n")
blob = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
report, count = re.subn(r"```text\n[0-9a-f]{40}\n```", f"```text\n{blob}\n```", report, count=1)
if count != 1:
    raise SystemExit("validation report blob marker not found")
REPORT.write_text(report, encoding="utf-8")
