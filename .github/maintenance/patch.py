from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "workshop" / "ruang_irama.workshop"
VAL = ROOT / "tools" / "validate_workshop.py"
TESTS = ROOT / "tests" / "test_validate_workshop.py"
README = ROOT / "README.md"
PROGETTO = ROOT / "docs" / "PROGETTO.md"
TEST_DOC = ROOT / "docs" / "TEST.md"
VALIDAZIONE = ROOT / "docs" / "VALIDAZIONE.md"
VERSION = ROOT / "VERSION"


def once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected 1 occurrence, found {count}")
    return text.replace(old, new, 1)


src = SRC.read_text(encoding="utf-8")

# Lightweight, idempotent pre-clean phase. It must not destroy HUD/text arrays: it
# only stops rules/effects so the later atomic cleanup runs on a quiet player.
src = once(
    src,
    "\t28: PramuatHalamanTerpilih\n}\n",
    "\t28: PramuatHalamanTerpilih\n\t29: TenangkanPemain\n}\n",
    "quiesce subroutine declaration",
)

quiesce_rule = '''rule("93b2 - Subrutin: Tenangkan pemain sebelum pembersihan")
{
\tevent
\t{
\t\tSubroutine;
\t\tTenangkanPemain;
\t}

\tactions
\t{
\t\t"Matikan pemicu menu dan efek lebih dulu agar perpindahan tim tidak menjalankan banyak aturan bersamaan."
\t\tEvent Player.Manusia = False;
\t\tEvent Player.MenuTerbuka = False;
\t\tEvent Player.PerintahMenu = 0;
\t\tEvent Player.SeranganDekatDipakai = False;
\t\tEvent Player.TeleportasiJongkokAktif = False;
\t\tEvent Player.PerintahTeleportasi = 0;
\t\tEvent Player.InspeksiAktif = False;
\t\tEvent Player.TargetInspeksi = Null;
\t\tEvent Player.InteraksiKameraDipakai = False;
\t\tEvent Player.KartuNasibAktif = False;
\t\tEvent Player.PutaranKartuNasib = 0;
\t\tEvent Player.GerakNasibDikunci = False;
\t\tEvent Player.KebalAktif = False;
\t\tEvent Player.ModeKebal = 0;
\t\tStop Camera(Event Player);
\t\tEvent Player.ModeKamera = 0;
\t\tEvent Player.TargetKamera = Null;
\t\tStop Chasing Player Variable(Event Player, WarnaMenu);
\t\tStop Chasing Player Variable(Event Player, RadiusNasib);
\t\tClear Status(Event Player, Unkillable);
\t\tStop Modifying Hero Voice Lines(Event Player);
\t\tStop Forcing Player Position(Event Player);
\t\tSet Move Speed(Event Player, 100);
\t\tSet Damage Received(Event Player, 100);
\t\tSet Damage Dealt(Event Player, 100);
\t\tSet Healing Dealt(Event Player, 100);
\t\tSet Knockback Dealt(Event Player, 100);
\t\tSet Knockback Received(Event Player, 100);
\t\tAllow Button(Event Player, Button(Melee));
\t\tAllow Button(Event Player, Button(Jump));
\t\tAllow Button(Event Player, Button(Crouch));
\t\tAllow Button(Event Player, Button(Primary Fire));
\t\tAllow Button(Event Player, Button(Secondary Fire));
\t\tAllow Button(Event Player, Button(Interact));
\t\tAllow Button(Event Player, Button(Reload));
\t\tAllow Button(Event Player, Button(Ability 1));
\t\tAllow Button(Event Player, Button(Ability 2));
\t\tAllow Button(Event Player, Button(Ultimate));
\t\tSet Primary Fire Enabled(Event Player, True);
\t\tSet Secondary Fire Enabled(Event Player, True);
\t\tSet Ability 1 Enabled(Event Player, True);
\t\tSet Ability 2 Enabled(Event Player, True);
\t\tSet Ultimate Ability Enabled(Event Player, True);
\t\tSet Melee Enabled(Event Player, True);
\t\tIf(Event Player.PelatNamaDinonaktifkan == True);
\t\t\tEnable Nameplates(All Players(All Teams), Event Player);
\t\t\tEvent Player.PelatNamaDinonaktifkan = False;
\t\tEnd;
\t\tEnable Game Mode HUD(Event Player);
\t\tEnable Game Mode In-World UI(Event Player);
\t}
}

'''
src = once(
    src,
    'rule("93c - Subrutin: Bersihkan pemain saat keluar atau pindah tim")',
    quiesce_rule + 'rule("93c - Subrutin: Bersihkan pemain saat keluar atau pindah tim")',
    "insert quiesce subroutine",
)

# Player Left no longer starts the heavy cleanup while menu/effects are live.
old_leave = '''rule("04 - Pemain Keluar: Bersihkan pendaftaran dan semua referensi")
{
\tevent
\t{
\t\tPlayer Left Match;
\t\tAll;
\t\tAll;
\t}

\tactions
\t{
\t\tCall Subroutine(BersihkanPemain);
\t}
}
'''
new_leave = '''rule("04 - Pemain Keluar: Tenangkan lalu bersihkan pendaftaran")
{
\tevent
\t{
\t\tPlayer Left Match;
\t\tAll;
\t\tAll;
\t}

\tactions
\t{
\t\tCall Subroutine(TenangkanPemain);
\t\tWait(0.100, Ignore Condition);
\t\tCall Subroutine(BersihkanPemain);
\t}
}
'''
src = once(src, old_leave, new_leave, "deferred Player Left cleanup")

# Join side also quiesces immediately. It deliberately waits longer than Player Left,
# so the natural leave cleanup gets first chance before the stale-registration fallback.
old_join_actions = '''\t\t"Jangan menumpuk pembersihan keluar dan masuk pada bingkai yang sama. Beri jeda agar acara keluar selesai lebih dulu."
\t\tEvent Player.PindahTimDiproses = True;
\t\tEvent Player.SiklusPemainAktif = True;
\t\tWait(0.050, Ignore Condition);
\t\tAbort If(Entity Exists(Event Player) == False);
\t\t"Jika pendaftaran lama masih ada, acara keluar tidak membersihkannya dan kita jalankan pembersihan cadangan tepat sekali."
\t\tIf(Or(Or(Array Contains(Global.PemainManusia, Event Player), And(Event Player.PernahDisiapkan == True, Array Contains(
\t\t\tGlobal.SlotHUDPemain, Event Player.UrutanHUD))), Array Contains(Mapped Array(Global.PemainManusia, Custom String("{0}",
\t\t\tCurrent Array Element)), Custom String("{0}", Event Player))));
\t\t\tCall Subroutine(BersihkanPemain);
\t\tEnd;
\t\tWait(0.050, Ignore Condition);
\t\tAbort If(Entity Exists(Event Player) == False);
\t\tCall Subroutine(SiapkanPemain);
'''
new_join_actions = '''\t\t"Tenangkan keadaan aktif sebelum menunggu pembersihan dari acara keluar."
\t\tEvent Player.PindahTimDiproses = True;
\t\tEvent Player.SiklusPemainAktif = True;
\t\tCall Subroutine(TenangkanPemain);
\t\tWait(0.200, Ignore Condition);
\t\tAbort If(Entity Exists(Event Player) == False);
\t\t"Jika pendaftaran lama masih ada, jalankan pembersihan cadangan tepat sekali setelah keadaan sudah tenang."
\t\tIf(Or(Or(Array Contains(Global.PemainManusia, Event Player), And(Event Player.PernahDisiapkan == True, Array Contains(
\t\t\tGlobal.SlotHUDPemain, Event Player.UrutanHUD))), Array Contains(Mapped Array(Global.PemainManusia, Custom String("{0}",
\t\t\tCurrent Array Element)), Custom String("{0}", Event Player))));
\t\t\tCall Subroutine(BersihkanPemain);
\t\tEnd;
\t\tWait(0.100, Ignore Condition);
\t\tAbort If(Entity Exists(Event Player) == False);
\t\tCall Subroutine(SiapkanPemain);
'''
src = once(src, old_join_actions, new_join_actions, "quiesced join lifecycle")

# Remove the duplicated runtime-restoration burst from the atomic cleanup. All callers
# now pass through TenangkanPemain before the cleanup is allowed to run.
old_cleanup_prefix = '''\t\t"Pulihkan keadaan runtime sebelum data roster dihapus; ini membuat pindah tim setara dengan keluar lalu masuk lagi."
\t\tStop Camera(Event Player);
\t\tAllow Button(Event Player, Button(Melee));
\t\tAllow Button(Event Player, Button(Jump));
\t\tAllow Button(Event Player, Button(Crouch));
\t\tAllow Button(Event Player, Button(Primary Fire));
\t\tAllow Button(Event Player, Button(Secondary Fire));
\t\tAllow Button(Event Player, Button(Interact));
\t\tAllow Button(Event Player, Button(Reload));
\t\tAllow Button(Event Player, Button(Ability 1));
\t\tAllow Button(Event Player, Button(Ability 2));
\t\tAllow Button(Event Player, Button(Ultimate));
\t\tSet Primary Fire Enabled(Event Player, True);
\t\tSet Secondary Fire Enabled(Event Player, True);
\t\tSet Ability 1 Enabled(Event Player, True);
\t\tSet Ability 2 Enabled(Event Player, True);
\t\tSet Ultimate Ability Enabled(Event Player, True);
\t\tSet Melee Enabled(Event Player, True);
\t\tSet Damage Dealt(Event Player, 100);
\t\tSet Healing Dealt(Event Player, 100);
\t\tSet Knockback Dealt(Event Player, 100);
\t\tSet Knockback Received(Event Player, 100);
\t\tSet Damage Received(Event Player, 100);
\t\tSet Move Speed(Event Player, 100);
\t\tStop Forcing Player Position(Event Player);
\t\tStop Chasing Player Variable(Event Player, RadiusNasib);
\t\tClear Status(Event Player, Unkillable);
\t\tStop Modifying Hero Voice Lines(Event Player);
\t\tEnable Game Mode HUD(Event Player);
\t\tEnable Game Mode In-World UI(Event Player);
\t\tEvent Player.PemainDipilih = Null;
\t\tEvent Player.JumlahSuara = 0;
\t\tEvent Player.SudahSiap = False;
\t\tEvent Player.SudahDiperiksa = False;
\t\tEvent Player.Manusia = False;
\t\tEvent Player.HudPemainDibuat = False;
'''
new_cleanup_prefix = '''\t\t"Keadaan aktif sudah ditenangkan sebelum subrutin ini; sekarang hapus data dan objek yang tersisa."
\t\tEvent Player.PemainDipilih = Null;
\t\tEvent Player.JumlahSuara = 0;
\t\tEvent Player.SudahSiap = False;
\t\tEvent Player.SudahDiperiksa = False;
\t\tEvent Player.Manusia = False;
\t\tEvent Player.MenuTerbuka = False;
\t\tEvent Player.HudPemainDibuat = False;
'''
src = once(src, old_cleanup_prefix, new_cleanup_prefix, "deduplicate cleanup runtime reset")
SRC.write_text(src, encoding="utf-8")

# --- Validator 0.6.23 ----------------------------------------------------
val = VAL.read_text(encoding="utf-8")
val = once(val, "della versione 0.6.22.", "della versione 0.6.23.", "validator doc version")
val = once(val, 'CURRENT_VERSION = "0.6.22"', 'CURRENT_VERSION = "0.6.23"', "validator version")

old_join_contract = '''        condition_lock = body.find("Event Player.PindahTimDiproses == False;")
        set_team_lock = body.find("Event Player.PindahTimDiproses = True;")
        set_cycle_lock = body.find("Event Player.SiklusPemainAktif = True;")
        first_wait = body.find("Wait(0.050, Ignore Condition);")
        stale_guard = body.find("If(Or(Or(Array Contains(Global.PemainManusia, Event Player)", first_wait)
        cleanup_at = body.find("Call Subroutine(BersihkanPemain);", stale_guard)
        second_wait = body.find("Wait(0.050, Ignore Condition);", cleanup_at)
        setup_at = body.find("Call Subroutine(SiapkanPemain);", second_wait)
        checks.require(
            0 <= condition_lock < set_team_lock < set_cycle_lock < first_wait < stale_guard < cleanup_at < second_wait < setup_at,
            "audit lifecycle: cambio team deve fare lock → yield → cleanup condizionale → yield → setup",
        )
        checks.equal(body.count("Wait(0.050, Ignore Condition);"), 2,
            "audit lifecycle: due yield da 0,05 s nel cambio team")
'''
new_join_contract = '''        condition_lock = body.find("Event Player.PindahTimDiproses == False;")
        set_team_lock = body.find("Event Player.PindahTimDiproses = True;")
        set_cycle_lock = body.find("Event Player.SiklusPemainAktif = True;")
        quiesce_at = body.find("Call Subroutine(TenangkanPemain);")
        first_wait = body.find("Wait(0.200, Ignore Condition);", quiesce_at)
        stale_guard = body.find("If(Or(Or(Array Contains(Global.PemainManusia, Event Player)", first_wait)
        cleanup_at = body.find("Call Subroutine(BersihkanPemain);", stale_guard)
        second_wait = body.find("Wait(0.100, Ignore Condition);", cleanup_at)
        setup_at = body.find("Call Subroutine(SiapkanPemain);", second_wait)
        checks.require(
            0 <= condition_lock < set_team_lock < set_cycle_lock < quiesce_at < first_wait < stale_guard < cleanup_at < second_wait < setup_at,
            "audit lifecycle: cambio team deve fare lock → yield → cleanup condizionale → yield → setup; TenangkanPemain deve precedere il primo yield",
        )
        checks.equal(body.count("Wait(0.200, Ignore Condition);"), 1,
            "audit lifecycle: primo yield cambio team da 0,20 s")
        checks.equal(body.count("Wait(0.100, Ignore Condition);"), 1,
            "audit lifecycle: secondo yield cambio team da 0,10 s")
'''
val = once(val, old_join_contract, new_join_contract, "validator quiesced join timing")

# Player Left must quiesce and yield before the heavy common cleanup.
leave_anchor = '''        checks.require(code_contains(leave[0].body, "Call Subroutine(BersihkanPemain);"), "audit lifecycle: Player Left non usa cleanup comune")
'''
leave_extra = leave_anchor + '''        leave_code = mask_strings(leave[0].body)
        leave_quiet = leave_code.find("Call Subroutine(TenangkanPemain);")
        leave_wait = leave_code.find("Wait(0.100, Ignore Condition);", leave_quiet)
        leave_cleanup = leave_code.find("Call Subroutine(BersihkanPemain);", leave_wait)
        checks.require(
            0 <= leave_quiet < leave_wait < leave_cleanup,
            "audit lifecycle: Player Left deve fare TenangkanPemain → yield → cleanup",
        )
'''
val = once(val, leave_anchor, leave_extra, "validator quiesced leave")

# Certify that the quiesce phase is lightweight and stops every persistent menu subsystem.
classification_anchor = '''    classification = [rule for rule in rules if rule.name.startswith("02 - Pemain:")]
'''
quiesce_checks = '''    quiet_rules = rules_containing(rules, "Subroutine;", "TenangkanPemain;")
    checks.equal(len(quiet_rules), 1, "audit lifecycle: subroutine TenangkanPemain")
    if quiet_rules:
        quiet = mask_strings(quiet_rules[0].body)
        for token in (
            "Event Player.Manusia = False;",
            "Event Player.MenuTerbuka = False;",
            "Event Player.PerintahMenu = 0;",
            "Event Player.TeleportasiJongkokAktif = False;",
            "Event Player.InspeksiAktif = False;",
            "Event Player.KartuNasibAktif = False;",
            "Event Player.KebalAktif = False;",
            "Stop Camera(Event Player);",
            "Stop Chasing Player Variable(Event Player, WarnaMenu);",
            "Stop Chasing Player Variable(Event Player, RadiusNasib);",
            "Clear Status(Event Player, Unkillable);",
            "Stop Modifying Hero Voice Lines(Event Player);",
        ):
            checks.require(token in quiet, f"audit lifecycle: TenangkanPemain incompleto: {token}")
        checks.require(
            "Destroy HUD Text" not in quiet
            and "Destroy In-World Text" not in quiet
            and "Destroy Effect" not in quiet
            and "Wait(" not in quiet
            and "Loop If Condition Is True;" not in quiet,
            "audit lifecycle: TenangkanPemain deve solo fermare trigger/effetti, senza distruzioni o attese",
        )

''' + classification_anchor
val = once(val, classification_anchor, quiesce_checks, "validator quiesce subroutine")
VAL.write_text(val, encoding="utf-8")

# --- Tests ---------------------------------------------------------------
tests = TESTS.read_text(encoding="utf-8")
tests = once(
    tests,
    'mutated_join = join_rule.replace("\\t\\tWait(0.050, Ignore Condition);\\n", "", 1)',
    'mutated_join = join_rule.replace("\\t\\tWait(0.200, Ignore Condition);\\n", "", 1)',
    "deferred lifecycle test timing",
)

anchor = '''    def test_vote_change_must_clear_previous_choice(self) -> None:
'''
new_test = '''    def test_team_rejoin_must_quiesce_before_first_yield(self) -> None:
        join_at = self.source.index('rule("01 - Pemain Masuk atau Pindah Tim:')
        join_end = self.source.index('\\nrule("01b - ', join_at)
        join_rule = self.source[join_at:join_end]
        mutated_join = join_rule.replace("\\t\\tCall Subroutine(TenangkanPemain);\\n", "", 1)
        self.assertNotEqual(mutated_join, join_rule)
        mutated = self.source[:join_at] + mutated_join + self.source[join_end:]
        _, player_names, _ = validator.declaration_tables(mutated)
        checks = validator.Checks()
        validator.check_lifecycle_hygiene(checks, mutated, self.rules(mutated), player_names)
        self.assertTrue(any("TenangkanPemain" in error for error in checks.errors), checks.errors)

'''
tests = once(tests, anchor, new_test + anchor, "quiesce regression test")
TESTS.write_text(tests, encoding="utf-8")

# --- Version and docs ----------------------------------------------------
VERSION.write_text("0.6.23\n", encoding="utf-8")

readme = README.read_text(encoding="utf-8")
readme = once(readme, "La versione **0.6.22** identifica lo stato funzionale e tecnico corrente del repository.", "La versione **0.6.23** identifica lo stato funzionale e tecnico corrente del repository.", "README version")
readme += '''\n\n### Team switch con stato menu attivo 0.6.23\n\nIl test live della 0.6.22 ha mostrato che i cambi squadra ripetuti sono stabili soltanto quando il player non ha il Menu Arcade aperto e non porta modifiche persistenti del menu. La 0.6.23 introduce `TenangkanPemain`: prima del cleanup spegne `Manusia`, nasconde il menu senza distruggerlo, azzera i dispatcher, ferma Camera, Inspection, Crouch Teleport, Try Your Luck, Unkillable, Hero Voice e i chase `WarnaMenu/RadiusNasib`, e ripristina input/UI nativi. Questa fase non distrugge HUD o effetti.\n\n`Player Left Match` esegue ora `TenangkanPemain → 0,10 s → BersihkanPemain`. `Player Joined Match` esegue `lock → TenangkanPemain → 0,20 s → eventuale cleanup fallback → 0,10 s → SiapkanPemain`. Il cleanup comune non ripete più il grosso blocco di ripristino runtime, riducendo il picco di azioni nel momento in cui vengono distrutti HUD e riferimenti.\n'''
README.write_text(readme, encoding="utf-8")

progetto = PROGETTO.read_text(encoding="utf-8")
progetto = once(progetto, "# Note di progetto — versione 0.6.22", "# Note di progetto — versione 0.6.23", "PROGETTO title")
progetto = once(progetto, "Workshop 0.6.22.", "Workshop 0.6.23.", "PROGETTO version")
progetto += '''\n\n## Quiescenza prima del cleanup 0.6.23\n\nLa fase `TenangkanPemain` è idempotente e volutamente priva di Destroy/Wait/Loop. Disattiva prima tutte le condizioni Ongoing che possono essere state abilitate dal Menu Arcade, rende invisibili gli HUD menu tramite `MenuTerbuka = False` e ferma le modifiche engine persistenti. Solo dopo un yield viene eseguito `BersihkanPemain`, che resta atomico per non lasciare i global scratch `IndeksKeluar/PemainPembersihan` esposti fra più player.\n'''
PROGETTO.write_text(progetto, encoding="utf-8")

test_doc = TEST_DOC.read_text(encoding="utf-8")
test_doc = once(test_doc, "# Piano di test — versione 0.6.22", "# Piano di test — versione 0.6.23", "TEST title")
test_doc = once(test_doc, "Workshop 0.6.22.", "Workshop 0.6.23.", "TEST version")
test_doc += '''\n\n## Team switch con menu/modifiche 0.6.23\n\nLa 0.6.22 è live-confirmed stabile per cambi ripetuti nello stato default, ma fallisce se il player cambia team con Menu Arcade aperto o dopo modifiche effettuate dal menu. Test 0.6.23: ripetere cambi Team 1 ↔ Team 2 con menu aperto su varie pagine e, separatamente, dopo avere applicato Soundtrack, Camera 3P, Name Color, Language, Unkillable 1 HP/FULL HP, Hero Voice, Icon, Crouch Teleport, Privacy e Vote. Provare anche Try Your Luck durante/alla fine del ciclo. Nessun caso deve produrre `excessive Workshop script load`; dopo lo spawn deve esistere una sola registrazione pulita.\n'''
TEST_DOC.write_text(test_doc, encoding="utf-8")

validazione = VALIDAZIONE.read_text(encoding="utf-8")
validazione = once(validazione, "# Rapporto di validazione — versione 0.6.22", "# Rapporto di validazione — versione 0.6.23", "VALIDAZIONE title")
validazione = once(validazione, "Release tecnica: **CHILL Dedicated Server 0.6.22**", "Release tecnica: **CHILL Dedicated Server 0.6.23**", "VALIDAZIONE release")
validazione = once(validazione, "Ran 35 tests", "Ran 36 tests", "VALIDAZIONE test count")
validazione = once(validazione, "OK - controlli statici v0.6.22 superati", "OK - controlli statici v0.6.23 superati", "VALIDAZIONE result")
validazione += '''\n\n## Gate quiescenza team-switch 0.6.23\n\nIl validator richiede `TenangkanPemain` sia sul Player Left sia sul Player Joined prima di qualsiasi cleanup, timing 0,10/0,20/0,10 s, stop esplicito dei sottosistemi persistenti e assenza di Destroy/Wait/Loop nella fase di quiescenza. Un test negativo rimuove la chiamata dal Player Joined e deve essere intercettato. La conferma completa resta live-pending per i casi con Menu Arcade/modifiche attive.\n'''

data = SRC.read_bytes().replace(b"\r\n", b"\n")
payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
blob = hashlib.sha1(payload).hexdigest()
validazione, n = re.subn(
    r"(Blob Git del sorgente Workshop validato:\n\n```text\n)[0-9a-f]{40}(\n```)",
    rf"\g<1>{blob}\g<2>",
    validazione,
    count=1,
)
if n != 1:
    raise RuntimeError("VALIDAZIONE blob marker not found")
VALIDAZIONE.write_text(validazione, encoding="utf-8")

print("Applied CHILL 0.6.23 quiesced team-switch cleanup")
