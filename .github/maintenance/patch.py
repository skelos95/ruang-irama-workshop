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
    n = text.count(old)
    if n != 1:
        raise RuntimeError(f"{label}: expected 1 occurrence, found {n}")
    return text.replace(old, new, 1)


src = SRC.read_text(encoding="utf-8")

# Remove the 0.6.20 in-place sync state and reuse player slot 93 as a real transition lock.
src = once(src, "\t\t50: ModeMulaiDiminta\n\t\t51: IndeksSinkronTim\n\tplayer:\n", "\t\t50: ModeMulaiDiminta\n\tplayer:\n", "remove sync global")
src = once(src, "\t\t93: AntarmukaModeDiterapkan\n", "\t\t93: PindahTimDiproses\n", "team transition player latch")
src = once(src, "\t\tGlobal.ModeMulaiDiminta = False;\n\t\tGlobal.IndeksSinkronTim = -1;\n\t\tGlobal.RGBFase = 0;\n", "\t\tGlobal.ModeMulaiDiminta = False;\n\t\tGlobal.RGBFase = 0;\n", "remove sync init")

old_join = '''rule("01 - Pemain Masuk atau Pindah Tim: Sinkronkan pemain tanpa bangun ulang")
{
\tevent
\t{
\t\tPlayer Joined Match;
\t\tAll;
\t\tAll;
\t}

\tconditions
\t{
\t\tIs Dummy Bot(Event Player) == False;
\t}

\tactions
\t{
\t\t"Cari referensi yang masih aktif lebih dulu. Jika Overwatch mengganti konteks pemain saat pindah tim, slot HUD lama menjadi kunci cadangan yang stabil."
\t\tGlobal.IndeksSinkronTim = Index Of Array Value(Global.PemainManusia, Event Player);
\t\tIf(And(Global.IndeksSinkronTim < 0, Event Player.PernahDisiapkan == True));
\t\t\tGlobal.IndeksSinkronTim = Index Of Array Value(Global.SlotHUDPemain, Event Player.UrutanHUD);
\t\tEnd;
\t\tIf(Global.IndeksSinkronTim >= 0);
\t\t\tGlobal.PemainManusia[Global.IndeksSinkronTim] = Event Player;
\t\t\tGlobal.HudKiriPemain[Global.IndeksSinkronTim] = 0;
\t\t\tGlobal.HudKananPemain[Global.IndeksSinkronTim] = 0;
\t\t\tEvent Player.HudKiri = Null;
\t\t\tEvent Player.HudKanan = Null;
\t\t\tEvent Player.HudPemainDibuat = False;
\t\t\tEvent Player.AntarmukaModeDiterapkan = False;
\t\t\tEvent Player.SiklusPemainAktif = False;
\t\t\tEvent Player.SudahSiap = True;
\t\t\tEvent Player.SudahDiperiksa = True;
\t\t\tEvent Player.Manusia = True;
\t\t\tGlobal.IndeksSinkronTim = -1;
\t\t\tAbort;
\t\tEnd;
\t\tGlobal.IndeksSinkronTim = -1;
\t\tAbort If(Event Player.SiklusPemainAktif == True);
\t\tEvent Player.SiklusPemainAktif = True;
\t\tCall Subroutine(SiapkanPemain);
\t}
}
'''
new_join = '''rule("01 - Pemain Masuk atau Pindah Tim: Bersihkan lalu masuk kembali")
{
\tevent
\t{
\t\tPlayer Joined Match;
\t\tAll;
\t\tAll;
\t}

\tconditions
\t{
\t\tIs Dummy Bot(Event Player) == False;
\t\tEvent Player.PindahTimDiproses == False;
\t}

\tactions
\t{
\t\t"Pindah tim memakai siklus yang sama seperti keluar lalu masuk. Kunci tetap aktif sampai roster baru selesai dibuat."
\t\tEvent Player.PindahTimDiproses = True;
\t\tEvent Player.SiklusPemainAktif = True;
\t\tCall Subroutine(BersihkanPemain);
\t\tCall Subroutine(SiapkanPemain);
\t}
}
'''
src = once(src, old_join, new_join, "clean team join rule")

# Bootstrap fallback uses the same transition lock and cannot overlap a team-switch event.
src = once(
    src,
    "\t\tEvent Player.PernahDisiapkan == False;\n\t\tEvent Player.SiklusPemainAktif == False;\n",
    "\t\tEvent Player.PernahDisiapkan == False;\n\t\tEvent Player.SiklusPemainAktif == False;\n\t\tEvent Player.PindahTimDiproses == False;\n",
    "fallback condition lock",
)
src = once(
    src,
    "\t\t\"Aturan cadangan ini hanya untuk pemain yang sudah ada saat skrip mulai, bukan untuk perpindahan tim berikutnya.\"\n\t\tEvent Player.SiklusPemainAktif = True;\n",
    "\t\t\"Aturan cadangan ini hanya untuk pemain yang sudah ada saat skrip mulai, bukan untuk perpindahan tim berikutnya.\"\n\t\tEvent Player.PindahTimDiproses = True;\n\t\tEvent Player.SiklusPemainAktif = True;\n",
    "fallback action lock",
)

# 0.6.20 post-spawn UI workaround is no longer needed: cleanup enables native UI and classification disables it after spawn.
start = src.index('rule("02d - Antarmuka: Terapkan kembali setelah pemain muncul")')
end = src.index('rule("03 - Waktu:', start)
src = src[:start] + src[end:]
src = once(src, "\t\tEvent Player.AntarmukaModeDiterapkan = True;\n", "", "remove classification UI latch")
src = once(src, "\t\tEvent Player.AntarmukaModeDiterapkan = False;\n", "\t\tEvent Player.PindahTimDiproses = Event Player.PindahTimDiproses;\n", "preserve transition latch in setup")

# Release the transition only after the freshly classified roster HUD really exists.
release_rule = '''rule("02e - Siklus Pemain: Lepaskan kunci setelah roster baru siap")
{
\tevent
\t{
\t\tOngoing - Each Player;
\t\tAll;
\t\tAll;
\t}

\tconditions
\t{
\t\tEvent Player.PindahTimDiproses == True;
\t\tEvent Player.Manusia == True;
\t\tHas Spawned(Event Player) == True;
\t\tEvent Player.HudPemainDibuat == True;
\t}

\tactions
\t{
\t\t"Roster baru sudah aktif; perpindahan berikutnya sekarang boleh memulai siklus baru."
\t\tEvent Player.PindahTimDiproses = False;
\t}
}

'''
src = once(src, 'rule("02c - Ruang Muncul:', release_rule + 'rule("02c - Ruang Muncul:', "insert lifecycle release")

# Cleanup must find the old registration even if Overwatch changed the entity reference during the team switch.
old_lookup = '''\t\tGlobal.PemainPembersihan = Event Player;
\t\tGlobal.IndeksKeluar = Index Of Array Value(Global.PemainManusia, Event Player);
\t\tIf(Global.IndeksKeluar >= 0);
'''
new_lookup = '''\t\tGlobal.IndeksKeluar = Index Of Array Value(Global.PemainManusia, Event Player);
\t\tIf(And(Global.IndeksKeluar < 0, Event Player.UrutanHUD >= 0));
\t\t\tGlobal.IndeksKeluar = Index Of Array Value(Global.SlotHUDPemain, Event Player.UrutanHUD);
\t\tEnd;
\t\tIf(Global.IndeksKeluar < 0);
\t\t\tGlobal.IndeksKeluar = Index Of Array Value(Mapped Array(Global.PemainManusia, Custom String("{0}", Current Array Element)),
\t\t\t\tCustom String("{0}", Event Player));
\t\tEnd;
\t\tGlobal.PemainPembersihan = Global.IndeksKeluar >= 0 ? Global.PemainManusia[Global.IndeksKeluar] : Event Player;
\t\tIf(Global.IndeksKeluar >= 0);
'''
src = once(src, old_lookup, new_lookup, "robust cleanup lookup")
SRC.write_text(src, encoding="utf-8")

# --- Validator 0.6.21 ----------------------------------------------------
val = VAL.read_text(encoding="utf-8")
val = once(val, "della versione 0.6.20.", "della versione 0.6.21.", "validator doc version")
val = once(val, 'CURRENT_VERSION = "0.6.20"', 'CURRENT_VERSION = "0.6.21"', "validator version")

# Cleanup identity audit: direct entity, persistent HUD slot, then name fallback.
old_cleanup_identity = '''        capture_at = leave.find("Global.PemainPembersihan = Event Player;")
        index_at = leave.find(
            "Global.IndeksKeluar = Index Of Array Value(Global.PemainManusia, Event Player);"
        )
        checks.require(
            0 <= capture_at < index_at,
            "cleanup uscita non cattura subito l'identità del giocatore",
        )
'''
new_cleanup_identity = '''        index_at = leave.find("Global.IndeksKeluar = Index Of Array Value(Global.PemainManusia, Event Player);")
        slot_at = leave.find("Global.IndeksKeluar = Index Of Array Value(Global.SlotHUDPemain, Event Player.UrutanHUD);", index_at)
        name_at = leave.find("Mapped Array(Global.PemainManusia, Custom String(", slot_at)
        capture_at = leave.find("Global.PemainPembersihan = Global.IndeksKeluar >= 0 ? Global.PemainManusia[Global.IndeksKeluar] : Event Player;", name_at)
        checks.require(
            0 <= index_at < slot_at < name_at < capture_at,
            "cleanup uscita/cambio team non risolve identità diretta → slot HUD → nome",
        )
'''
val = once(val, old_cleanup_identity, new_cleanup_identity, "cleanup robust identity validator")

# Replace the 0.6.20 lightweight lifecycle contract with clean leave+rejoin semantics.
start = val.index("    if join:\n        body = mask_strings(join[0].body)\n        direct_lookup =")
end = val.index("\n    classification = [rule for rule in rules if rule.name.startswith(\"02 - Pemain:\")]", start)
new_lifecycle = '''    if join:
        body = mask_strings(join[0].body)
        condition_lock = body.find("Event Player.PindahTimDiproses == False;")
        set_team_lock = body.find("Event Player.PindahTimDiproses = True;")
        set_cycle_lock = body.find("Event Player.SiklusPemainAktif = True;")
        cleanup_at = body.find("Call Subroutine(BersihkanPemain);")
        setup_at = body.find("Call Subroutine(SiapkanPemain);")
        checks.require(
            0 <= condition_lock < set_team_lock < set_cycle_lock < cleanup_at < setup_at,
            "audit lifecycle: cambio team non esegue un solo ciclo pulito cleanup → setup",
        )
        checks.require(
            "Global.PemainManusia[" not in body
            and "Global.HudKiriPemain[" not in body
            and "Global.HudKananPemain[" not in body,
            "audit lifecycle: Player Joined modifica ancora il roster in-place",
        )

    release = [rule for rule in rules if rule.name.startswith("02e - Siklus Pemain:")]
    checks.equal(len(release), 1, "audit lifecycle: rilascio lock team-switch")
    if release:
        release_body = mask_strings(release[0].body)
        for token in (
            "Event Player.PindahTimDiproses == True;",
            "Event Player.Manusia == True;",
            "Has Spawned(Event Player) == True;",
            "Event Player.HudPemainDibuat == True;",
            "Event Player.PindahTimDiproses = False;",
        ):
            checks.require(token in release_body, f"audit lifecycle: rilascio team-switch incompleto: {token}")
        checks.require("Wait(" not in release_body and "Loop If Condition Is True;" not in release_body,
            "audit lifecycle: rilascio team-switch non deve usare Wait/Loop")

    checks.equal(len([rule for rule in rules if rule.name.startswith("02d - Antarmuka:")]), 0,
        "audit lifecycle: workaround UI 0.6.20 deve essere rimosso")
'''
val = val[:start] + new_lifecycle + val[end:]

val = once(val,
'''        checks.require(
            "Event Player.PernahDisiapkan == False;" in fallback_code
            and "Event Player.SiklusPemainAktif == False;" in fallback_code,
            "audit lifecycle: fallback può riattivarsi durante un cambio team",
        )
        lock_at = fallback_code.find("Event Player.SiklusPemainAktif = True;")
        setup_at = fallback_code.find("Call Subroutine(SiapkanPemain);")
        checks.require(0 <= lock_at < setup_at, "audit lifecycle: fallback non blocca prima del setup")
''',
'''        checks.require(
            "Event Player.PernahDisiapkan == False;" in fallback_code
            and "Event Player.SiklusPemainAktif == False;" in fallback_code
            and "Event Player.PindahTimDiproses == False;" in fallback_code,
            "audit lifecycle: fallback può riattivarsi durante un cambio team",
        )
        team_lock_at = fallback_code.find("Event Player.PindahTimDiproses = True;")
        lock_at = fallback_code.find("Event Player.SiklusPemainAktif = True;")
        setup_at = fallback_code.find("Call Subroutine(SiapkanPemain);")
        checks.require(0 <= team_lock_at < lock_at < setup_at, "audit lifecycle: fallback non blocca prima del setup")
''', "fallback validator")

val = once(val,
'''        checks.require(code_contains(leave[0].body, "Call Subroutine(BersihkanPemain);"), "audit lifecycle: Player Left non usa cleanup comune")
        checks.require(
            not any(code_contains(rule.body, "Player Joined Match;", "Call Subroutine(BersihkanPemain);") for rule in rules),
            "audit lifecycle: BersihkanPemain non deve essere chiamato da Player Joined/cambio team",
        )
''',
'''        checks.require(code_contains(leave[0].body, "Call Subroutine(BersihkanPemain);"), "audit lifecycle: Player Left non usa cleanup comune")
        checks.require(
            any(code_contains(rule.body, "Player Joined Match;", "Call Subroutine(BersihkanPemain);", "Call Subroutine(SiapkanPemain);") for rule in rules),
            "audit lifecycle: cambio team non usa lo stesso cleanup/setup di un leave/rejoin",
        )
''', "leave/join cleanup validator")

val = once(val,
'''        capture = body.find("Global.PemainPembersihan = Event Player;")
        checks.require(capture >= 0, "audit lifecycle: cleanup non cattura identità")
''',
'''        direct = body.find("Global.IndeksKeluar = Index Of Array Value(Global.PemainManusia, Event Player);")
        slot = body.find("Global.IndeksKeluar = Index Of Array Value(Global.SlotHUDPemain, Event Player.UrutanHUD);", direct)
        name = body.find("Mapped Array(Global.PemainManusia, Custom String(", slot)
        capture = body.find("Global.PemainPembersihan = Global.IndeksKeluar >= 0 ? Global.PemainManusia[Global.IndeksKeluar] : Event Player;", name)
        checks.require(0 <= direct < slot < name < capture, "audit lifecycle: cleanup non risolve il vecchio riferimento del team-switch")
''', "lifecycle cleanup capture validator")

VAL.write_text(val, encoding="utf-8")

# --- Regression tests: replace lightweight 0.6.18-0.6.20 assumptions ------
tests = TESTS.read_text(encoding="utf-8")
start = tests.index("    def test_team_rejoin_must_not_run_heavy_cleanup")
end = tests.index("    def test_vote_change_must_clear_previous_choice", start)
replacement = '''    def test_team_rejoin_must_run_cleanup_before_fresh_setup(self) -> None:
        join_at = self.source.index('rule("01 - Pemain Masuk atau Pindah Tim:')
        join_end = self.source.index('\\nrule("01b - ', join_at)
        join_rule = self.source[join_at:join_end]
        mutated_join = join_rule.replace("\\t\\tCall Subroutine(BersihkanPemain);\\n", "", 1)
        self.assertNotEqual(mutated_join, join_rule)
        mutated = self.source[:join_at] + mutated_join + self.source[join_end:]
        _, player_names, _ = validator.declaration_tables(mutated)
        checks = validator.Checks()
        validator.check_lifecycle_hygiene(checks, mutated, self.rules(mutated), player_names)
        self.assertTrue(any("cleanup → setup" in error or "leave/rejoin" in error for error in checks.errors), checks.errors)

    def test_team_rejoin_lock_must_survive_until_new_roster_hud(self) -> None:
        mutated = self.source.replace("\\t\\tEvent Player.PindahTimDiproses = True;\\n\\t\\tEvent Player.SiklusPemainAktif = True;", "\\t\\tEvent Player.SiklusPemainAktif = True;", 1)
        self.assertNotEqual(mutated, self.source)
        _, player_names, _ = validator.declaration_tables(mutated)
        checks = validator.Checks()
        validator.check_lifecycle_hygiene(checks, mutated, self.rules(mutated), player_names)
        self.assertTrue(any("cleanup → setup" in error for error in checks.errors), checks.errors)

    def test_cleanup_team_switch_must_find_old_roster_by_slot_or_name(self) -> None:
        mutated = self.source.replace("\\t\\tIf(Global.IndeksKeluar < 0);\\n\\t\\t\\tGlobal.IndeksKeluar = Index Of Array Value(Mapped Array(Global.PemainManusia, Custom String(\"{0}\", Current Array Element)),\\n\\t\\t\\t\\tCustom String(\"{0}\", Event Player));\\n\\t\\tEnd;\\n", "", 1)
        self.assertNotEqual(mutated, self.source)
        checks = validator.Checks()
        validator.check_cleanup_and_revenge(checks, mutated, self.rules(mutated))
        self.assertTrue(any("slot HUD → nome" in error for error in checks.errors), checks.errors)

'''
tests = tests[:start] + replacement + tests[end:]
TESTS.write_text(tests, encoding="utf-8")

# --- Version/docs ---------------------------------------------------------
VERSION.write_text("0.6.21\n", encoding="utf-8")

readme = README.read_text(encoding="utf-8")
readme = once(readme, "La versione **0.6.20** identifica lo stato funzionale e tecnico corrente del repository.", "La versione **0.6.21** identifica lo stato funzionale e tecnico corrente del repository.", "README version")
readme += '''\n\n### Cambio team come leave/rejoin reale 0.6.21\n\nIl cambio squadra non conserva più la registrazione precedente. Ogni `Player Joined Match` umano entra in un ciclo protetto: `BersihkanPemain` completo, poi `SiapkanPemain`, classificazione e nuova creazione del roster. Il lock `PindahTimDiproses` resta attivo fino a quando `HudPemainDibuat == True`, quindi eventi duplicati della stessa transizione non possono avviare un secondo cleanup/setup. `BersihkanPemain` risolve la vecchia registrazione con riferimento diretto, poi slot HUD persistente e infine nome come fallback, così può eliminare davvero HUD/array/riferimenti del contesto precedente.\n'''
README.write_text(readme, encoding="utf-8")

progetto = PROGETTO.read_text(encoding="utf-8")
progetto = once(progetto, "# Note di progetto — versione 0.6.20", "# Note di progetto — versione 0.6.21", "PROGETTO title")
progetto = once(progetto, "Workshop 0.6.20.", "Workshop 0.6.21.", "PROGETTO version")
progetto += '''\n\n## Lifecycle team-switch pulito 0.6.21\n\nLa strategia in-place 0.6.18–0.6.20 è rimossa. Il player che cambia team viene prima rimosso dalle strutture parallele e da tutti i riferimenti tramite `BersihkanPemain`, poi inizializzato da zero con `SiapkanPemain`. Il cleanup usa direct reference → `UrutanHUD/SlotHUDPemain` → nome visuale per individuare la vecchia riga anche se Overwatch ha già cambiato il contesto entità.\n'''
PROGETTO.write_text(progetto, encoding="utf-8")

test_doc = TEST_DOC.read_text(encoding="utf-8")
test_doc = once(test_doc, "# Piano di test — versione 0.6.20", "# Piano di test — versione 0.6.21", "TEST title")
test_doc = once(test_doc, "Workshop 0.6.20.", "Workshop 0.6.21.", "TEST version")
test_doc += '''\n\n## Team switch clean rejoin 0.6.21\n\nTest live: cambiare Team 1 ↔ Team 2 almeno dieci volte. Ogni cambio deve comportarsi come una nuova entrata: schermata eroe nativa pulita, nessun riquadro `0`, roster precedente rimosso, welcome/tempo/preferenze ripartono come per un rejoin e dopo lo spawn compare una sola nuova riga per lato con il nome corretto. Nessun `excessive Workshop script load` e nessuna riga duplicata/stale deve accumularsi.\n'''
TEST_DOC.write_text(test_doc, encoding="utf-8")

validazione = VALIDAZIONE.read_text(encoding="utf-8")
validazione = once(validazione, "# Rapporto di validazione — versione 0.6.20", "# Rapporto di validazione — versione 0.6.21", "VALIDAZIONE title")
validazione = once(validazione, "Release tecnica: **CHILL Dedicated Server 0.6.20**", "Release tecnica: **CHILL Dedicated Server 0.6.21**", "VALIDAZIONE release")
validazione = once(validazione, "OK - controlli statici v0.6.20 superati", "OK - controlli statici v0.6.21 superati", "VALIDAZIONE result")
validazione += '''\n\n## Gate clean team rejoin 0.6.21\n\nIl validator richiede `PindahTimDiproses` prima del cleanup, ordine `BersihkanPemain → SiapkanPemain`, rilascio del lock solo dopo roster HUD stabile e lookup cleanup direct → slot HUD → nome. Sono vietate le vecchie modifiche in-place del roster e il workaround UI 02d della 0.6.20.\n'''

data = SRC.read_bytes().replace(b"\r\n", b"\n")
payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
blob = hashlib.sha1(payload).hexdigest()
validazione, n = re.subn(r"(Blob Git del sorgente Workshop validato:\n\n```text\n)[0-9a-f]{40}(\n```)", rf"\g<1>{blob}\g<2>", validazione, count=1)
if n != 1:
    raise RuntimeError("VALIDAZIONE blob marker not found")
VALIDAZIONE.write_text(validazione, encoding="utf-8")

print("Applied CHILL 0.6.21 clean team leave-rejoin lifecycle")
