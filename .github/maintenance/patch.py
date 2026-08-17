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
old_join = '''rule("01 - Pemain Masuk atau Pindah Tim: Bersihkan lalu masuk kembali")
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
new_join = '''rule("01 - Pemain Masuk atau Pindah Tim: Tunggu pembersihan lalu masuk kembali")
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
\t\t"Jangan menumpuk pembersihan keluar dan masuk pada bingkai yang sama. Beri jeda agar acara keluar selesai lebih dulu."
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
\t}
}
'''
src = once(src, old_join, new_join, "deferred team join")
SRC.write_text(src, encoding="utf-8")

val = VAL.read_text(encoding="utf-8")
val = once(val, "della versione 0.6.21.", "della versione 0.6.22.", "validator doc version")
val = once(val, 'CURRENT_VERSION = "0.6.21"', 'CURRENT_VERSION = "0.6.22"', "validator version")
old_contract = '''        condition_lock = body.find("Event Player.PindahTimDiproses == False;")
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
'''
new_contract = '''        condition_lock = body.find("Event Player.PindahTimDiproses == False;")
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
        checks.equal(body.count("Call Subroutine(BersihkanPemain);"), 1,
            "audit lifecycle: cleanup fallback deve comparire una sola volta nel Player Joined")
        checks.require(
            "Array Contains(Global.PemainManusia, Event Player)" in body
            and "Array Contains(Global.SlotHUDPemain, Event Player.UrutanHUD)" in body
            and "Mapped Array(Global.PemainManusia, Custom String(" in body,
            "audit lifecycle: cleanup fallback non controlla riferimento, slot HUD e nome",
        )
        checks.require(
            body.count("Abort If(Entity Exists(Event Player) == False);") >= 2,
            "audit lifecycle: Player Joined non protegge i due yield da una vera uscita",
        )
        checks.require(
            "Global.PemainManusia[" not in body
            and "Global.HudKiriPemain[" not in body
            and "Global.HudKananPemain[" not in body,
            "audit lifecycle: Player Joined modifica ancora il roster in-place",
        )
'''
val = once(val, old_contract, new_contract, "deferred lifecycle validator")
VAL.write_text(val, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
old_test = '''    def test_team_rejoin_must_run_cleanup_before_fresh_setup(self) -> None:
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

'''
new_test = '''    def test_team_rejoin_must_defer_cleanup_and_fresh_setup(self) -> None:
        join_at = self.source.index('rule("01 - Pemain Masuk atau Pindah Tim:')
        join_end = self.source.index('\\nrule("01b - ', join_at)
        join_rule = self.source[join_at:join_end]
        mutated_join = join_rule.replace("\\t\\tWait(0.050, Ignore Condition);\\n", "", 1)
        self.assertNotEqual(mutated_join, join_rule)
        mutated = self.source[:join_at] + mutated_join + self.source[join_end:]
        _, player_names, _ = validator.declaration_tables(mutated)
        checks = validator.Checks()
        validator.check_lifecycle_hygiene(checks, mutated, self.rules(mutated), player_names)
        self.assertTrue(any("yield" in error for error in checks.errors), checks.errors)

'''
tests = once(tests, old_test, new_test, "deferred lifecycle regression test")
TESTS.write_text(tests, encoding="utf-8")

VERSION.write_text("0.6.22\n", encoding="utf-8")

readme = README.read_text(encoding="utf-8")
readme = once(readme, "La versione **0.6.21** identifica lo stato funzionale e tecnico corrente del repository.", "La versione **0.6.22** identifica lo stato funzionale e tecnico corrente del repository.", "README version")
readme += '''\n\n### Team switch differito 0.6.22\n\nIl test live della 0.6.21 ha mostrato `excessive Workshop script load` al primo cambio squadra. `Player Joined Match` non esegue più immediatamente `BersihkanPemain` e `SiapkanPemain` nello stesso frame: arma il lock, attende 0,05 s, verifica se `Player Left Match` ha già eliminato la vecchia registrazione e richiama il cleanup solo come fallback se serve. Dopo un secondo yield da 0,05 s avvia il setup fresco. In questo modo il risultato resta equivalente a leave/rejoin senza sovrapporre due lifecycle pesanti.\n'''
README.write_text(readme, encoding="utf-8")

progetto = PROGETTO.read_text(encoding="utf-8")
progetto = once(progetto, "# Note di progetto — versione 0.6.21", "# Note di progetto — versione 0.6.22", "PROGETTO title")
progetto = once(progetto, "Workshop 0.6.21.", "Workshop 0.6.22.", "PROGETTO version")
progetto += '''\n\n## Lifecycle team-switch differito 0.6.22\n\nLa 0.6.21 concentrava cleanup e setup nel `Player Joined Match`; il client live ha chiuso la lobby per carico Workshop eccessivo al primo cambio team. La 0.6.22 sfrutta prima il cleanup naturale di `Player Left Match`, attende un yield, esegue `BersihkanPemain` solo se una registrazione vecchia è ancora presente e separa il successivo `SiapkanPemain` con un secondo yield.\n'''
PROGETTO.write_text(progetto, encoding="utf-8")

test_doc = TEST_DOC.read_text(encoding="utf-8")
test_doc = once(test_doc, "# Piano di test — versione 0.6.21", "# Piano di test — versione 0.6.22", "TEST title")
test_doc = once(test_doc, "Workshop 0.6.21.", "Workshop 0.6.22.", "TEST version")
test_doc += '''\n\n## Regressione team switch 0.6.22\n\nLa 0.6.21 è live-failed: al primo cambio team il server ha mostrato `The server closed due to excessive Workshop script load.` Per la 0.6.22 provare Team 1 ↔ Team 2 almeno dieci volte. Non deve apparire alcuna chiusura per script load; ogni transizione deve rimuovere la vecchia riga e ricreare una sola registrazione/HUD dopo lo spawn.\n'''
TEST_DOC.write_text(test_doc, encoding="utf-8")

validazione = VALIDAZIONE.read_text(encoding="utf-8")
validazione = once(validazione, "# Rapporto di validazione — versione 0.6.21", "# Rapporto di validazione — versione 0.6.22", "VALIDAZIONE title")
validazione = once(validazione, "Release tecnica: **CHILL Dedicated Server 0.6.21**", "Release tecnica: **CHILL Dedicated Server 0.6.22**", "VALIDAZIONE release")
validazione = once(validazione, "OK - controlli statici v0.6.21 superati", "OK - controlli statici v0.6.22 superati", "VALIDAZIONE result")
validazione += '''\n\n## Gate team-switch differito 0.6.22\n\nIl validator richiede due `Wait(0.050, Ignore Condition)` nel `Player Joined Match`, cleanup fallback singolo e condizionale dopo il primo yield, controllo stale tramite riferimento/slot/nome, guardia `Entity Exists` dopo i yield e setup soltanto dopo il secondo yield. Il fallimento live 0.6.21 resta documentato e la 0.6.22 richiede nuova conferma nel client.\n'''

data = SRC.read_bytes().replace(b"\r\n", b"\n")
payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
blob = hashlib.sha1(payload).hexdigest()
validazione, n = re.subn(r"(Blob Git del sorgente Workshop validato:\n\n```text\n)[0-9a-f]{40}(\n```)", rf"\g<1>{blob}\g<2>", validazione, count=1)
if n != 1:
    raise RuntimeError("VALIDAZIONE blob marker not found")
VALIDAZIONE.write_text(validazione, encoding="utf-8")

print("Applied CHILL 0.6.22 deferred team rejoin lifecycle")
