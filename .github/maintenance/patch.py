from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
TESTS = ROOT / "tests" / "test_validate_workshop.py"
README = ROOT / "README.md"
PROGETTO = ROOT / "docs" / "PROGETTO.md"
TEST_DOC = ROOT / "docs" / "TEST.md"
VALIDAZIONE = ROOT / "docs" / "VALIDAZIONE.md"
VERSION = ROOT / "VERSION"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly 1 occurrence, found {count}")
    return text.replace(old, new, 1)


def replace_between(text: str, start: str, end: str, replacement: str, label: str) -> str:
    start_at = text.find(start)
    if start_at < 0:
        raise RuntimeError(f"{label}: start marker not found")
    end_at = text.find(end, start_at)
    if end_at < 0:
        raise RuntimeError(f"{label}: end marker not found")
    return text[:start_at] + replacement + text[end_at:]


source = SOURCE.read_text(encoding="utf-8")

# 1) Never auto-close an already open Arcade menu because the player died/despawned.
source = replace_between(
    source,
    'rule("12 - Menu: Kematian juga menutup warung")',
    'rule("12c - Kamera: Tahan Interact setengah detik untuk beralih di luar menu")',
    '',
    "remove death/despawn menu auto-close rules",
)

# 2) Give Try Your Luck a meaningful live status instead of a permanently-looking READY label.
status_replacements = {
    'Event Player.KartuNasibAktif ? Custom String("ACTIVE") : Custom String("READY")':
        'Event Player.KartuNasibAktif ? Event Player.PutaranKartuNasib > 0 ? Custom String("ROLLING") : Event Player.KartuNasibMerah ? Custom String("RED") : Custom String("GREEN") : Custom String("READY")',
    'Event Player.KartuNasibAktif ? Custom String("AKTIF") : Custom String("SIAP")':
        'Event Player.KartuNasibAktif ? Event Player.PutaranKartuNasib > 0 ? Custom String("BERPUTAR") : Event Player.KartuNasibMerah ? Custom String("MERAH") : Custom String("HIJAU") : Custom String("SIAP")',
    'Event Player.KartuNasibAktif ? Custom String("ทำงาน") : Custom String("พร้อม")':
        'Event Player.KartuNasibAktif ? Event Player.PutaranKartuNasib > 0 ? Custom String("กำลังสุ่ม") : Event Player.KartuNasibMerah ? Custom String("แดง") : Custom String("เขียว") : Custom String("พร้อม")',
}
for old, new in status_replacements.items():
    count = source.count(old)
    if count < 2:
        raise RuntimeError(f"status replacement {old!r}: expected at least 2 occurrences, found {count}")
    source = source.replace(old, new)

# 3) Red outcome: only zero movement speed. No position forcing and no knockback lock.
red_rule_start = source.index('rule("18e - Nasib: Undian merah hijau makin lambat")')
red_rule_end = source.index('rule("18f - Nasib: Hapus kartu saat pemilik mati")', red_rule_start)
red_rule = source[red_rule_start:red_rule_end]
red_rule = replace_once(
    red_rule,
    '\t\t\tSet Knockback Received(Event Player, 0);\n',
    '',
    "remove luck knockback lock",
)
red_rule = replace_once(
    red_rule,
    '\t\t\tStart Forcing Player Position(Event Player, Event Player.PosisiNasibTerkunci, False);\n',
    '',
    "remove luck position forcing",
)
source = source[:red_rule_start] + red_rule + source[red_rule_end:]

# All luck-specific cleanup blocks now restore only movement speed.
luck_cleanup_old = (
    '\t\tIf(Event Player.GerakNasibDikunci == True);\n'
    '\t\t\tStop Forcing Player Position(Event Player);\n'
    '\t\t\tSet Move Speed(Event Player, 100);\n'
    '\t\t\tSet Knockback Received(Event Player, 100);\n'
    '\t\tEnd;\n'
)
luck_cleanup_new = (
    '\t\tIf(Event Player.GerakNasibDikunci == True);\n'
    '\t\t\tSet Move Speed(Event Player, 100);\n'
    '\t\tEnd;\n'
)
cleanup_count = source.count(luck_cleanup_old)
if cleanup_count < 1:
    raise RuntimeError("luck cleanup speed block not found")
source = source.replace(luck_cleanup_old, luck_cleanup_new)

# 4) If the player dies before roulette completion, cancel it and restore the remembered Unkillable mode.
death_start = source.index('rule("18f - Nasib: Hapus kartu saat pemilik mati")')
death_end = source.index('rule("19 - Teleportasi Jongkok: Buka tampilan selama Jongkok ditahan")', death_start)
death_rule = source[death_start:death_end]
insert_after = '\t\tEvent Player.JedaKartuNasib = 0;\n'
if death_rule.count(insert_after) != 1:
    raise RuntimeError(f"luck death reset anchor count={death_rule.count(insert_after)}")
restore_block = (
    insert_after
    + '\t\tClear Status(Event Player, Unkillable);\n'
    + '\t\tEvent Player.ModeKebal = Event Player.ModeKebalTerakhir;\n'
    + '\t\tEvent Player.KursorKebal = Event Player.ModeKebalTerakhir;\n'
    + '\t\tIf(Event Player.ModeKebalTerakhir == 0);\n'
    + '\t\t\tEvent Player.KebalAktif = False;\n'
    + '\t\t\tSet Damage Received(Event Player, 100);\n'
    + '\t\tElse;\n'
    + '\t\t\tEvent Player.KebalAktif = True;\n'
    + '\t\t\tSet Status(Event Player, Null, Unkillable, 9999);\n'
    + '\t\t\tIf(Event Player.ModeKebalTerakhir == 1);\n'
    + '\t\t\t\tSet Damage Received(Event Player, 100);\n'
    + '\t\t\tElse;\n'
    + '\t\t\t\tSet Damage Received(Event Player, 0);\n'
    + '\t\t\tEnd;\n'
    + '\t\tEnd;\n'
    + '\t\tIf(Event Player.IkonKebal != Null);\n'
    + '\t\t\tDestroy Icon(Event Player.IkonKebal);\n'
    + '\t\t\tEvent Player.IkonKebal = Null;\n'
    + '\t\tEnd;\n'
    + '\t\tIf(And(Event Player.MenuTerbuka == True, Event Player.HalamanMenu == 10));\n'
    + '\t\t\tCall Subroutine(GambarMenu);\n'
    + '\t\tEnd;\n'
)
death_rule = death_rule.replace(insert_after, restore_block, 1)
source = source[:death_start] + death_rule + source[death_end:]

if 'Start Forcing Player Position(Event Player, Event Player.PosisiNasibTerkunci, False);' in source:
    raise RuntimeError("luck position forcing still present")

SOURCE.write_text(source, encoding="utf-8")

# Validator: new menu invariant, speed-only red outcome, and death reset coverage.
validator = VALIDATOR.read_text(encoding="utf-8")
validator = validator.replace('versione 0.6.4', 'versione 0.6.5', 1)
validator = validator.replace('CURRENT_VERSION = "0.6.4"', 'CURRENT_VERSION = "0.6.5"', 1)

menu_block_start = '    invalid_state_cleanup = [\n'
menu_block_end = '    revenge_renderers = rules_containing(rules, "Subroutine;", "GambarBalasDendam;")\n'
new_menu_checks = '''    death_menu_closers = [
        rule
        for rule in rules_containing(rules, "Player Died;", "Call Subroutine(TutupMenu);")
        if code_contains(rule.body, "Event Player.MenuTerbuka == True;")
    ]
    checks.equal(
        len(death_menu_closers),
        0,
        "menu: la morte non deve chiudere automaticamente un menu aperto",
    )

    invalid_state_cleanup = [
        rule
        for rule in rules_containing(rules, "Event Player.MenuTerbuka == True;", "Call Subroutine(TutupMenu);")
        if code_contains(rule.body, "Has Spawned(Event Player) == False")
        or code_contains(rule.body, "Is Alive(Event Player) == False")
    ]
    checks.equal(
        len(invalid_state_cleanup),
        0,
        "menu: morte/despawn non devono chiudere automaticamente un menu aperto",
    )

'''
validator = replace_between(
    validator,
    menu_block_start,
    menu_block_end,
    new_menu_checks,
    "validator menu death policy",
)

validator = validator.replace(
    '            "Set Knockback Received(Event Player, 0);",\n',
    '',
    1,
)
validator = validator.replace(
    '            "Start Forcing Player Position(Event Player, Event Player.PosisiNasibTerkunci, False);",\n',
    '',
    1,
)
luck_require_line = '            checks.require(token in luck_code, f"Nasib: sequenza rosso/verde incompleta: {token}")\n'
if validator.count(luck_require_line) != 1:
    raise RuntimeError("validator luck token loop anchor not unique")
validator = validator.replace(
    luck_require_line,
    luck_require_line
    + '        checks.require("Start Forcing Player Position" not in luck_code, "Nasib: il rosso deve bloccare solo la velocità, senza posizione forzata")\n'
    + '        checks.require("Set Knockback Received(Event Player, 0);" not in luck_code, "Nasib: il rosso non deve bloccare il knockback")\n',
    1,
)

card_anchor = '    card_texts = [\n'
death_checks = '''    luck_death_cleanup = [
        rule
        for rule in rules_containing(
            rules,
            "Player Died;",
            "Event Player.KartuNasibAktif == True;",
            "Event Player.KartuNasibAktif = False;",
        )
    ]
    checks.equal(len(luck_death_cleanup), 1, "Nasib: un solo reset della roulette su morte")
    if luck_death_cleanup:
        death_code = mask_strings(luck_death_cleanup[0].body)
        for token in (
            "Event Player.ModeKebal = Event Player.ModeKebalTerakhir;",
            "Event Player.KursorKebal = Event Player.ModeKebalTerakhir;",
            "Event Player.PutaranKartuNasib = 0;",
            "Event Player.JedaKartuNasib = 0;",
            "Call Subroutine(GambarMenu);",
        ):
            checks.require(token in death_code, f"Nasib: reset su morte incompleto: {token}")

    for status_text in (
        "ROLLING", "RED", "GREEN",
        "BERPUTAR", "MERAH", "HIJAU",
        "กำลังสุ่ม", "แดง", "เขียว",
    ):
        checks.require(
            source.count(f'Custom String("{status_text}")') >= 2,
            f"Nasib: stato menu dinamico mancante o incompleto: {status_text}",
        )

'''
if validator.count(card_anchor) != 1:
    raise RuntimeError("validator card anchor not unique")
validator = validator.replace(card_anchor, death_checks + card_anchor, 1)
VALIDATOR.write_text(validator, encoding="utf-8")

# Tests: replace the two old expectations with the new invariants; keep total test count unchanged.
tests = TESTS.read_text(encoding="utf-8")
old_menu_method = '    def test_menu_inactive_cleanup_requires_or(self) -> None:\n'
next_menu_method = '    def test_crouch_cleanup_requires_or(self) -> None:\n'
new_menu_method = '''    def test_menu_must_not_close_on_death_or_despawn(self) -> None:
        bad_rules = (
            ''' + "'''" + '''
rule("TEST - bad death menu close")
{
    event
    {
        Player Died;
        All;
        All;
    }
    conditions
    {
        Event Player.MenuTerbuka == True;
    }
    actions
    {
        Call Subroutine(TutupMenu);
    }
}
''' + "'''" + ''',
            ''' + "'''" + '''
rule("TEST - bad dead-state menu close")
{
    event
    {
        Ongoing - Each Player;
        All;
        All;
    }
    conditions
    {
        Event Player.MenuTerbuka == True;
        Is Alive(Event Player) == False;
    }
    actions
    {
        Call Subroutine(TutupMenu);
    }
}
''' + "'''" + ''',
        )
        _, _, subroutines = validator.declaration_tables(self.source)
        for bad_rule in bad_rules:
            with self.subTest(bad_rule=bad_rule.splitlines()[1]):
                mutated = self.source + "\\n" + bad_rule
                checks = validator.Checks()
                validator.check_menus(checks, mutated, self.rules(mutated), subroutines)
                self.assertTrue(
                    any("non deve chiudere" in error or "non devono chiudere" in error for error in checks.errors),
                    checks.errors,
                )

'''
tests = replace_between(
    tests,
    old_menu_method,
    next_menu_method,
    new_menu_method,
    "replace menu death test",
)

old_luck_method = '    def test_luck_red_must_force_position_and_shrink_ring(self) -> None:\n'
next_luck_method = '    def test_camera_dead_candidate_is_rejected(self) -> None:\n'
new_luck_method = '''    def test_luck_red_must_use_speed_lock_without_forcing(self) -> None:
        forcing = self.source.replace(
            "Set Move Speed(Event Player, 0);",
            "Set Move Speed(Event Player, 0);\\n\\t\\t\\tStart Forcing Player Position(Event Player, Event Player.PosisiNasibTerkunci, False);",
            1,
        )
        self.assertNotEqual(forcing, self.source)
        checks = validator.Checks()
        validator.check_arcade_features(checks, forcing, self.rules(forcing))
        self.assertTrue(any("posizione forzata" in error for error in checks.errors), checks.errors)

        no_speed_lock = self.source.replace(
            "Set Move Speed(Event Player, 0);",
            '"Set Move Speed(Event Player, 0);"',
            1,
        )
        self.assertNotEqual(no_speed_lock, self.source)
        checks = validator.Checks()
        validator.check_arcade_features(checks, no_speed_lock, self.rules(no_speed_lock))
        self.assertTrue(any("sequenza rosso/verde incompleta" in error for error in checks.errors), checks.errors)

'''
tests = replace_between(
    tests,
    old_luck_method,
    next_luck_method,
    new_luck_method,
    "replace luck forcing test",
)
TESTS.write_text(tests, encoding="utf-8")

# Version and docs.
VERSION.write_text("0.6.5\n", encoding="utf-8")

readme = README.read_text(encoding="utf-8").replace("0.6.4", "0.6.5")
readme = readme.replace(
    "rosso immobilizza il player con Light Shaft + Ring RGB in chiusura e lo uccide dopo 3 secondi.",
    "rosso porta la velocità del player a 0 con Light Shaft + Ring RGB in chiusura e lo uccide dopo 3 secondi, senza forzare la posizione.",
)
readme = readme.replace(
    "rosso = freeze + Ring/Light Shaft + morte",
    "rosso = velocità 0 + Ring/Light Shaft + morte",
)
readme = readme.replace(
    "- **Rosso:** porta la protezione runtime a OFF, blocca movimento e knockback, forza la posizione, congela il colore corrente di `Global.RGB`, crea `Light Shaft` e `Ring` sul pavimento e riduce gradualmente il raggio durante il countdown 3-2-1 prima della morte.\n- Morte, leave e cambio squadra fermano il forcing/chase, ripristinano movimento e knockback e distruggono gli effetti senza lasciare entità orfane.",
    "- **Rosso:** porta la protezione runtime a OFF, imposta solo la velocità di movimento a 0, congela il colore corrente di `Global.RGB`, crea `Light Shaft` e `Ring` sul pavimento e riduce gradualmente il raggio durante il countdown 3-2-1 prima della morte; la posizione non viene forzata e il knockback resta normale.\n- Se il player muore prima della fine della roulette, la funzione si resetta subito, ripristina la modalità Unkillable ricordata e aggiorna la pagina 10 senza chiudere il Menu Arcade. Leave e cambio squadra continuano a fare cleanup completo degli effetti.\n- Lo status della pagina 10 è dinamico: `READY` → `ROLLING` → `RED/GREEN` (con equivalenti ID/TH).",
)
README.write_text(readme, encoding="utf-8")

for path in (PROGETTO, TEST_DOC):
    text = path.read_text(encoding="utf-8").replace("0.6.4", "0.6.5")
    note = (
        "\n\n## Hotfix Try Your Luck 0.6.5\n\n"
        "- lo status Menu 10 distingue READY / ROLLING / RED / GREEN (localizzato EN/ID/TH);\n"
        "- morte durante la roulette = reset immediato della carta e ripristino di `ModeKebalTerakhir`;\n"
        "- la morte non chiude più automaticamente un Menu Arcade già aperto, né tramite evento `Player Died` né tramite controllo `Is Alive == False`;\n"
        "- l'esito rosso usa soltanto `Set Move Speed(..., 0)`: nessun `Start Forcing Player Position` e nessun blocco knockback; Ring/Light Shaft e countdown restano invariati.\n"
    )
    if "## Hotfix Try Your Luck 0.6.5" not in text:
        text += note
    path.write_text(text, encoding="utf-8")

validazione = VALIDAZIONE.read_text(encoding="utf-8").replace("0.6.4", "0.6.5")
validazione = validazione.replace(
    "rosso = OFF + forcing posizione + Light Shaft/Ring RGB in chiusura + morte; cleanup completo morte/leave/team switch;",
    "rosso = OFF + velocità 0 + Light Shaft/Ring RGB in chiusura + morte, senza forcing posizione o knockback lock; morte durante roulette = reset e menu lasciato aperto; cleanup completo leave/team switch;",
)
validazione = validazione.replace(
    "- Try Your Luck verde/rosso durante movimento e camera 3P, inclusi forcing posizione, Ring/Light Shaft, countdown e cleanup;",
    "- Try Your Luck verde/rosso durante movimento e camera 3P, inclusi velocità 0 senza forcing, Ring/Light Shaft, countdown, morte anticipata e menu che resta aperto;",
)
validazione = validazione.replace(
    "Branch operativo: `main` (unico branch del repository al momento dell'audit).",
    "Branch operativo e sorgente canonico: `main`.",
)
validazione += (
    "\n## Hotfix Try Your Luck 0.6.5\n\n"
    "Lo status Menu 10 ora mostra lo stato reale della roulette; la morte interrompe e resetta la funzione senza chiudere il menu. "
    "Il rosso mantiene Ring/Light Shaft e countdown ma immobilizza esclusivamente tramite velocità a 0, senza forcing posizione né knockback lock.\n"
)

# Record the exact Git blob of the modified Workshop source before validation.
data = SOURCE.read_bytes().replace(b"\r\n", b"\n")
payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
blob = hashlib.sha1(payload).hexdigest()
validazione, replaced = re.subn(
    r"(Blob Git del sorgente Workshop validato:\n\n```text\n)[0-9a-f]{40}(\n```)",
    rf"\g<1>{blob}\g<2>",
    validazione,
    count=1,
)
if replaced != 1:
    raise RuntimeError("docs/VALIDAZIONE.md Workshop blob marker not found")
VALIDAZIONE.write_text(validazione, encoding="utf-8")

print("Applied Try Your Luck 0.6.5 death/menu/speed hotfix")
