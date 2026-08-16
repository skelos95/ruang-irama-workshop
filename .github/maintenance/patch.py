from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "workshop" / "ruang_irama.workshop"
VAL = ROOT / "tools" / "validate_workshop.py"
README = ROOT / "README.md"
PROGETTO = ROOT / "docs" / "PROGETTO.md"
TEST = ROOT / "docs" / "TEST.md"
VALIDAZIONE = ROOT / "docs" / "VALIDAZIONE.md"
VERSION = ROOT / "VERSION"


def once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise RuntimeError(f"{label}: expected 1 occurrence, found {n}")
    return text.replace(old, new, 1)


src = SRC.read_text(encoding="utf-8")

old_join = '''rule("01 - Pemain Masuk atau Pindah Tim: Bersihkan lalu siapkan ulang")
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
\t\tEvent Player.SiklusPemainAktif == False;
\t}

\tactions
\t{
\t\t"Kunci siklus mencegah pembersihan dan persiapan kedua berjalan bersamaan pada perpindahan tim."
\t\tEvent Player.SiklusPemainAktif = True;
\t\tIf(Array Contains(Global.PemainManusia, Event Player));
\t\t\tCall Subroutine(BersihkanPemain);
\t\tEnd;
\t\tCall Subroutine(SiapkanPemain);
\t}
}
'''
new_join = '''rule("01 - Pemain Masuk atau Pindah Tim: Jangan bangun ulang pemain yang sudah terdaftar")
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
\t\t"Pindah tim mempertahankan HUD, menu, pilihan, dan pendaftaran. Pembersihan penuh hanya untuk pemain yang benar-benar keluar."
\t\tIf(Array Contains(Global.PemainManusia, Event Player));
\t\t\tEvent Player.SiklusPemainAktif = False;
\t\t\tEvent Player.SudahSiap = True;
\t\t\tEvent Player.SudahDiperiksa = True;
\t\t\tEvent Player.Manusia = True;
\t\t\tDisable Game Mode HUD(Event Player);
\t\t\tDisable Game Mode In-World UI(Event Player);
\t\t\tDisable Nameplates(Event Player, Filtered Array(Global.PemainManusia, Player Variable(Current Array Element, InspeksiAktif) == True));
\t\t\tAbort;
\t\tEnd;
\t\tAbort If(Event Player.SiklusPemainAktif == True);
\t\tEvent Player.SiklusPemainAktif = True;
\t\tCall Subroutine(SiapkanPemain);
\t}
}
'''
src = once(src, old_join, new_join, "lightweight Player Joined/team switch")

SRC.write_text(src, encoding="utf-8")

val = VAL.read_text(encoding="utf-8")
val = once(val, "della versione 0.6.17.", "della versione 0.6.18.", "validator doc version")
val = once(val, 'CURRENT_VERSION = "0.6.17"', 'CURRENT_VERSION = "0.6.18"', "validator version")

old_audit = '''    if join:
        body = mask_strings(join[0].body)
        condition_lock = body.find("Event Player.SiklusPemainAktif == False;")
        set_lock = body.find("Event Player.SiklusPemainAktif = True;")
        duplicate_at = body.find("If(Array Contains(Global.PemainManusia, Event Player));")
        cleanup_at = body.find("Call Subroutine(BersihkanPemain);", duplicate_at)
        setup_at = body.find("Call Subroutine(SiapkanPemain);", cleanup_at)
        checks.require(
            0 <= condition_lock < set_lock < duplicate_at < cleanup_at < setup_at,
            "audit lifecycle: cambio team non è serializzato cleanup → setup",
        )
'''
new_audit = '''    if join:
        body = mask_strings(join[0].body)
        duplicate_at = body.find("If(Array Contains(Global.PemainManusia, Event Player));")
        abort_registered = body.find("Abort;", duplicate_at)
        setup_at = body.find("Call Subroutine(SiapkanPemain);", abort_registered)
        checks.require(
            0 <= duplicate_at < abort_registered < setup_at,
            "audit lifecycle: player già registrato non esce prima del setup",
        )
        checks.require(
            "Call Subroutine(BersihkanPemain);" not in body,
            "audit lifecycle: cambio team esegue ancora cleanup completo",
        )
        checks.require(
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
val = once(val, old_audit, new_audit, "validator lightweight team switch")

# Explicitly certify that only Player Left uses the heavy cleanup path.
leave_anchor = '''    if leave:
        checks.require(code_contains(leave[0].body, "Call Subroutine(BersihkanPemain);"), "audit lifecycle: Player Left non usa cleanup comune")
'''
leave_extra = leave_anchor + '''        checks.require(
            not any(code_contains(rule.body, "Player Joined Match;", "Call Subroutine(BersihkanPemain);") for rule in rules),
            "audit lifecycle: BersihkanPemain non deve essere chiamato da Player Joined/cambio team",
        )
'''
val = once(val, leave_anchor, leave_extra, "validator cleanup only on leave")

VAL.write_text(val, encoding="utf-8")
VERSION.write_text("0.6.18\n", encoding="utf-8")

readme = README.read_text(encoding="utf-8")
readme = once(readme, "La versione **0.6.17** identifica lo stato funzionale e tecnico corrente del repository.", "La versione **0.6.18** identifica lo stato funzionale e tecnico corrente del repository.", "README version")
readme += '''\n\n### Cambio team leggero 0.6.18\n\nIl cambio team non percorre più `BersihkanPemain → SiapkanPemain` quando il player è già presente in `Global.PemainManusia`. In quel caso vengono mantenuti gli stessi HUD, menu, preferenze, slot e riferimenti; la regola `Player Joined Match` si limita a confermare lo stato umano/pronto e a riapplicare le due disabilitazioni UI native. La pulizia pesante resta esclusivamente su un vero `Player Left Match`. Questo elimina la distruzione/ricreazione di fino a 15 HUD e la scansione di tutti i riferimenti ad ogni cambio squadra.\n'''
README.write_text(readme, encoding="utf-8")

progetto = PROGETTO.read_text(encoding="utf-8")
progetto = once(progetto, "# Note di progetto — versione 0.6.17", "# Note di progetto — versione 0.6.18", "PROGETTO title")
progetto = once(progetto, "Workshop 0.6.17.", "Workshop 0.6.18.", "PROGETTO version")
progetto += '''\n\n## Team switch senza rebuild 0.6.18\n\n`Player Joined Match` distingue ora il player già registrato dal vero ingresso. Se `Array Contains(Global.PemainManusia, Event Player)` è vero, la regola termina prima di qualsiasi setup e non chiama mai `BersihkanPemain`. Le strutture parallele HUD/slot non vengono mutate durante il cambio team. `BersihkanPemain` rimane associato a `Player Left Match`, dove la rimozione è realmente necessaria.\n'''
PROGETTO.write_text(progetto, encoding="utf-8")

test_doc = TEST.read_text(encoding="utf-8")
test_doc = once(test_doc, "# Piano di test — versione 0.6.17", "# Piano di test — versione 0.6.18", "TEST title")
test_doc = once(test_doc, "Workshop 0.6.17.", "Workshop 0.6.18.", "TEST version")
test_doc += '''\n\n## Team switch leggero 0.6.18\n\nTest live prioritario: effettuare almeno dieci cambi Team 1 ↔ Team 2 sullo stesso player. Gli HUD sociali e le preferenze devono restare gli stessi, senza nuova welcome message e senza ricreazione del Menu Arcade. Il server non deve mostrare `excessive Workshop script load`. Poi uscire realmente dalla lobby e rientrare: il vero `Player Left Match` deve ancora pulire correttamente slot, HUD e riferimenti prima della nuova registrazione.\n'''
TEST.write_text(test_doc, encoding="utf-8")

validazione = VALIDAZIONE.read_text(encoding="utf-8")
validazione = once(validazione, "# Rapporto di validazione — versione 0.6.17", "# Rapporto di validazione — versione 0.6.18", "VALIDAZIONE title")
validazione = once(validazione, "Release tecnica: **CHILL Dedicated Server 0.6.17**", "Release tecnica: **CHILL Dedicated Server 0.6.18**", "VALIDAZIONE release")
validazione = once(validazione, "OK - controlli statici v0.6.17 superati", "OK - controlli statici v0.6.18 superati", "VALIDAZIONE result")
validazione += '''\n\n## Gate team switch leggero 0.6.18\n\nIl validatore vieta `BersihkanPemain`, `Create HUD Text` e `Destroy HUD Text` nella regola `Player Joined Match`. Un player già presente nel roster deve terminare il percorso prima di `SiapkanPemain`; il cleanup completo resta obbligatorio sull'evento `Player Left Match`.\n'''

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

print("Applied CHILL 0.6.18 lightweight repeated team switching")
