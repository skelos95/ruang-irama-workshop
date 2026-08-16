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


# --- Workshop runtime -----------------------------------------------------
src = SRC.read_text(encoding="utf-8")
old_registered = '''\t\tIf(Array Contains(Global.PemainManusia, Event Player));
\t\t\tEvent Player.SiklusPemainAktif = False;
\t\t\tEvent Player.SudahSiap = True;
\t\t\tEvent Player.SudahDiperiksa = True;
\t\t\tEvent Player.Manusia = True;
\t\t\tDisable Game Mode HUD(Event Player);
\t\t\tDisable Game Mode In-World UI(Event Player);
\t\t\tAbort;
\t\tEnd;
'''
new_registered = '''\t\tIf(Array Contains(Global.PemainManusia, Event Player));
\t\t\t"Overwatch membuang dua HUD roster yang dibuat dari konteks pemain saat pindah tim. Jangan cleanup penuh: kosongkan hanya ID lama lalu biarkan 02b membuat dua baris lagi."
\t\t\tGlobal.HudKiriPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = 0;
\t\t\tGlobal.HudKananPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = 0;
\t\t\tEvent Player.HudKiri = Null;
\t\t\tEvent Player.HudKanan = Null;
\t\t\tEvent Player.HudPemainDibuat = False;
\t\t\tEvent Player.SiklusPemainAktif = False;
\t\t\tEvent Player.SudahSiap = True;
\t\t\tEvent Player.SudahDiperiksa = True;
\t\t\tEvent Player.Manusia = True;
\t\t\tDisable Game Mode HUD(Event Player);
\t\t\tDisable Game Mode In-World UI(Event Player);
\t\t\tAbort;
\t\tEnd;
'''
src = once(src, old_registered, new_registered, "team-switch social HUD rearm")
SRC.write_text(src, encoding="utf-8")

# --- Static validator -----------------------------------------------------
val = VAL.read_text(encoding="utf-8")
val = once(val, "della versione 0.6.18.", "della versione 0.6.19.", "validator doc version")
val = once(val, 'CURRENT_VERSION = "0.6.18"', 'CURRENT_VERSION = "0.6.19"', "validator current version")
old_join_checks = '''        checks.require(
            "Destroy HUD Text" not in body and "Create HUD Text" not in body,
            "audit lifecycle: cambio team crea/distrugge HUD",
        )
        for token in (
            "Event Player.SudahSiap = True;",
            "Event Player.SudahDiperiksa = True;",
            "Event Player.Manusia = True;",
            "Disable Game Mode HUD(Event Player);",
            "Disable Game Mode In-World UI(Event Player);",
        ):
            checks.require(token in body, f"audit lifecycle: refresh leggero cambio team incompleto: {token}")
'''
new_join_checks = '''        checks.require(
            "Destroy HUD Text" not in body and "Create HUD Text" not in body,
            "audit lifecycle: cambio team crea/distrugge HUD direttamente",
        )
        social_rearm_tokens = (
            "Global.HudKiriPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = 0;",
            "Global.HudKananPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = 0;",
            "Event Player.HudKiri = Null;",
            "Event Player.HudKanan = Null;",
            "Event Player.HudPemainDibuat = False;",
        )
        social_rearm_positions = [body.find(token, duplicate_at) for token in social_rearm_tokens]
        checks.require(
            all(duplicate_at < position < abort_registered for position in social_rearm_positions),
            "audit lifecycle: cambio team non riarma i due HUD sociali prima dell'uscita leggera",
        )
        for token in (
            "Event Player.SudahSiap = True;",
            "Event Player.SudahDiperiksa = True;",
            "Event Player.Manusia = True;",
            "Disable Game Mode HUD(Event Player);",
            "Disable Game Mode In-World UI(Event Player);",
        ):
            checks.require(token in body, f"audit lifecycle: refresh leggero cambio team incompleto: {token}")
'''
val = once(val, old_join_checks, new_join_checks, "validator team-switch roster rearm")
VAL.write_text(val, encoding="utf-8")

# --- Negative regression test -------------------------------------------
tests = TESTS.read_text(encoding="utf-8")
anchor = '''    def test_vote_change_must_clear_previous_choice(self) -> None:
'''
new_test = '''    def test_team_rejoin_must_rearm_social_roster_without_rebuild(self) -> None:
        join_at = self.source.index('rule("01 - Pemain Masuk atau Pindah Tim:')
        join_end = self.source.index('\\nrule("01b - ', join_at)
        join_rule = self.source[join_at:join_end]
        mutated_join = join_rule.replace(
            "\\t\\t\\tEvent Player.HudPemainDibuat = False;\\n",
            "",
            1,
        )
        self.assertNotEqual(mutated_join, join_rule)
        mutated = self.source[:join_at] + mutated_join + self.source[join_end:]
        _, player_names, _ = validator.declaration_tables(mutated)
        checks = validator.Checks()
        validator.check_lifecycle_hygiene(checks, mutated, self.rules(mutated), player_names)
        self.assertTrue(
            any("non riarma i due HUD sociali" in error for error in checks.errors),
            checks.errors,
        )

'''
tests = once(tests, anchor, new_test + anchor, "social roster rearm regression test")
TESTS.write_text(tests, encoding="utf-8")

# --- Version + docs -------------------------------------------------------
VERSION.write_text("0.6.19\n", encoding="utf-8")

readme = README.read_text(encoding="utf-8")
readme = once(
    readme,
    "La versione **0.6.18** identifica lo stato funzionale e tecnico corrente del repository.",
    "La versione **0.6.19** identifica lo stato funzionale e tecnico corrente del repository.",
    "README version",
)
readme += '''\n\n### Roster dopo cambio team 0.6.19\n\nIl cambio team resta leggero: nessun `BersihkanPemain`, nessun `SiapkanPemain` e nessun `Destroy HUD Text` nel percorso `Player Joined Match` di un umano già registrato. Overwatch rimuove però i due HUD sociali creati dal precedente contesto player; per questo il ramo azzera solo gli ID paralleli `HudKiriPemain/HudKananPemain`, porta `HudKiri/HudKanan` a `Null` e riapre il latch `HudPemainDibuat`. La regola `02b` ricrea quindi soltanto le due righe roster, conservando slot, lingua, colore, icona, soundtrack e tutte le altre preferenze.\n'''
README.write_text(readme, encoding="utf-8")

progetto = PROGETTO.read_text(encoding="utf-8")
progetto = once(progetto, "# Note di progetto — versione 0.6.18", "# Note di progetto — versione 0.6.19", "PROGETTO title")
progetto = once(progetto, "Workshop 0.6.18.", "Workshop 0.6.19.", "PROGETTO version")
progetto += '''\n\n## Rearm roster sociale 0.6.19\n\nUn cambio team non ricostruisce più l'intero lifecycle, ma deve riarmare i soli HUD sociali perché il client elimina le due righe create dal vecchio contesto player. Il ramo per player già presente in `Global.PemainManusia` azzera i due ID paralleli, mette `HudKiri/HudKanan = Null` e `HudPemainDibuat = False`; `02b` ricrea due soli `Create HUD Text` quando il player è di nuovo spawnato. Nessuna preferenza o slot viene riallocato.\n'''
PROGETTO.write_text(progetto, encoding="utf-8")

test_doc = TEST_DOC.read_text(encoding="utf-8")
test_doc = once(test_doc, "# Piano di test — versione 0.6.18", "# Piano di test — versione 0.6.19", "TEST title")
test_doc = once(test_doc, "Workshop 0.6.18.", "Workshop 0.6.19.", "TEST version")
test_doc += '''\n\n## Roster dopo cambio team 0.6.19\n\nTest live prioritario: con almeno un player visibile nelle liste, alternare Team 1 ↔ Team 2 almeno dieci volte. Dopo ogni cambio devono ricomparire entrambe le righe sociali con nome, icona eroe, minuti e soundtrack; colore/icona personale/lingua devono restare invariati. Non deve comparire una nuova welcome message e non deve esserci `excessive Workshop script load`. Verificare anche un vero leave/rejoin, che continua invece a usare il cleanup completo.\n'''
TEST_DOC.write_text(test_doc, encoding="utf-8")

validazione = VALIDAZIONE.read_text(encoding="utf-8")
validazione = once(validazione, "# Rapporto di validazione — versione 0.6.18", "# Rapporto di validazione — versione 0.6.19", "VALIDAZIONE title")
validazione = once(validazione, "Data: 2026-08-16", "Data: 2026-08-17", "VALIDAZIONE date")
validazione = once(validazione, "Release tecnica: **CHILL Dedicated Server 0.6.18**", "Release tecnica: **CHILL Dedicated Server 0.6.19**", "VALIDAZIONE release")
validazione = once(validazione, "Ran 33 tests", "Ran 34 tests", "VALIDAZIONE test count")
validazione = once(validazione, "OK - controlli statici v0.6.18 superati", "OK - controlli statici v0.6.19 superati", "VALIDAZIONE result")
validazione += '''\n\n## Gate roster team-switch 0.6.19\n\nIl gate vieta ancora cleanup completo e `Create/Destroy HUD Text` diretto nella regola `Player Joined Match`. Per il ramo di un player già registrato richiede invece il rearm dei due soli HUD sociali: ID globali a `0`, `HudKiri/HudKanan = Null` e `HudPemainDibuat = False` prima dell'`Abort`. Un nuovo test negativo rimuove il rearm e deve essere intercettato dal validatore.\n'''

data = SRC.read_bytes().replace(b"\r\n", b"\n")
payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
blob = hashlib.sha1(payload).hexdigest()
validazione, replacements = re.subn(
    r"(Blob Git del sorgente Workshop validato:\n\n```text\n)[0-9a-f]{40}(\n```)",
    rf"\g<1>{blob}\g<2>",
    validazione,
    count=1,
)
if replacements != 1:
    raise RuntimeError("VALIDAZIONE blob marker not found")
VALIDAZIONE.write_text(validazione, encoding="utf-8")

print("Applied CHILL 0.6.19 social roster rearm after team switch")
