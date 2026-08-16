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
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected 1 occurrence, found {count}")
    return text.replace(old, new, 1)


src = SRC.read_text(encoding="utf-8")

# Global one-shot for Start Game Mode; per-player lifecycle serialization.
src = once(
    src,
    "\t\t49: PersiapanDilewati\n\tplayer:\n",
    "\t\t49: PersiapanDilewati\n\t\t50: ModeMulaiDiminta\n\tplayer:\n",
    "global start latch declaration",
)
src = once(
    src,
    "\t\t90: HudPemainDibuat\n}\n",
    "\t\t90: HudPemainDibuat\n\t\t91: SiklusPemainAktif\n\t\t92: PernahDisiapkan\n}\n",
    "player lifecycle declarations",
)

src = once(
    src,
    "\t\tGlobal.PersiapanDilewati = False;\n",
    "\t\tGlobal.PersiapanDilewati = False;\n\t\tGlobal.ModeMulaiDiminta = False;\n",
    "initial start latch",
)

# Start Game Mode can only fire once per full match lifecycle.
old_start = '''rule("00a1 - Umum: Mulai mode segera saat menunggu pemain")
{
	event
	{
		Ongoing - Global;
	}

	conditions
	{
		Global.Siap == True;
		Is Waiting For Players == True;
	}

	actions
	{
		Start Game Mode;
	}
}
'''
new_start = '''rule("00a1 - Umum: Mulai mode segera saat menunggu pemain")
{
	event
	{
		Ongoing - Global;
	}

	conditions
	{
		Global.Siap == True;
		Global.ModeMulaiDiminta == False;
		Is Game In Progress == False;
		Is Waiting For Players == True;
	}

	actions
	{
		"Permintaan mulai hanya boleh dikirim sekali sampai pertandingan berikutnya."
		Global.ModeMulaiDiminta = True;
		Start Game Mode;
	}
}
'''
src = once(src, old_start, new_start, "Start Game Mode one-shot")

# Re-arm it only for a deliberate full restart.
src = once(
    src,
    "\t\tGlobal.PersiapanDilewati = False;\n\t\tRestart Match;\n",
    "\t\tGlobal.PersiapanDilewati = False;\n\t\tGlobal.ModeMulaiDiminta = False;\n\t\tRestart Match;\n",
    "restart start latch",
)

# Serialize the Player Joined/team-change lifecycle.
old_join = '''\tconditions
\t{
\t\tIs Dummy Bot(Event Player) == False;
\t}

\tactions
\t{
\t\tIf(Array Contains(Global.PemainManusia, Event Player));
\t\t\tCall Subroutine(BersihkanPemain);
\t\tEnd;
\t\tCall Subroutine(SiapkanPemain);
\t}
}

rule("01b - Pemain Lama: Siapkan juga yang sudah telanjur ada")'''
new_join = '''\tconditions
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

rule("01b - Pemain Lama: Siapkan juga yang sudah telanjur ada")'''
src = once(src, old_join, new_join, "serialized joined lifecycle")

# 01b is now bootstrap-only. It can no longer wake up every time cleanup makes SudahSiap false.
old_fallback = '''\tconditions
\t{
\t\tGlobal.Siap == True;
\t\tIs Dummy Bot(Event Player) == False;
\t\tEvent Player.SudahSiap == False;
\t}

\tactions
\t{
\t\tCall Subroutine(SiapkanPemain);
\t}
}

rule("02 - Pemain: Pisahkan manusia dari pasukan kaleng")'''
new_fallback = '''\tconditions
\t{
\t\tGlobal.Siap == True;
\t\tIs Dummy Bot(Event Player) == False;
\t\tEvent Player.SudahSiap == False;
\t\tEvent Player.PernahDisiapkan == False;
\t\tEvent Player.SiklusPemainAktif == False;
\t}

\tactions
\t{
\t\t"Aturan cadangan ini hanya untuk pemain yang sudah ada saat skrip mulai, bukan untuk perpindahan tim berikutnya."
\t\tEvent Player.SiklusPemainAktif = True;
\t\tCall Subroutine(SiapkanPemain);
\t}
}

rule("02 - Pemain: Pisahkan manusia dari pasukan kaleng")'''
src = once(src, old_fallback, new_fallback, "bootstrap-only fallback")

# Classifier is forbidden while setup is still locked.
src = once(
    src,
    "\t\tEvent Player.SudahSiap == True;\n\t\tHas Spawned(Event Player) == True;\n",
    "\t\tEvent Player.SudahSiap == True;\n\t\tEvent Player.SiklusPemainAktif == False;\n\t\tHas Spawned(Event Player) == True;\n",
    "classifier lifecycle lock",
)

# SudahSiap used to be set halfway through SiapkanPemain. Move readiness to the final edge.
src = once(src, "\t\tEvent Player.SudahSiap = True;\n", "", "remove early SudahSiap")
src = once(
    src,
    "\t\tEvent Player.JedaKartuNasib = 0;\n\t}\n}\n\nrule(\"95 - Subrutin: Segarkan daftar tontonan, termasuk para bot\")",
    "\t\tEvent Player.JedaKartuNasib = 0;\n\t\tEvent Player.PernahDisiapkan = True;\n\t\tEvent Player.SiklusPemainAktif = False;\n\t\tEvent Player.SudahSiap = True;\n\t}\n}\n\nrule(\"95 - Subrutin: Segarkan daftar tontonan, termasuk para bot\")",
    "setup final readiness edge",
)

SRC.write_text(src, encoding="utf-8")

# Validator 0.6.17.
val = VAL.read_text(encoding="utf-8")
val = once(val, "della versione 0.6.16.", "della versione 0.6.17.", "validator doc version")
val = once(val, 'CURRENT_VERSION = "0.6.16"', 'CURRENT_VERSION = "0.6.17"', "validator version")

# Start Game Mode must now be guarded exactly like the other initial-phase actions.
waiting_marker = '''    checks.equal(len(waiting), 1, "avvio immediato da Waiting For Players")

    assembling = [
'''
waiting_checks = '''    checks.equal(len(waiting), 1, "avvio immediato da Waiting For Players")
    if waiting:
        waiting_code = mask_strings(waiting[0].body)
        checks.require(
            "Global.ModeMulaiDiminta == False;" in waiting_code
            and "Is Game In Progress == False;" in waiting_code,
            "Start Game Mode non protetto da latch one-shot/in-match",
        )
        latch_at = waiting_code.find("Global.ModeMulaiDiminta = True;")
        start_at = waiting_code.find("Start Game Mode;")
        checks.require(0 <= latch_at < start_at, "latch Start Game Mode deve armarsi prima dell'azione")

    assembling = [
'''
val = once(val, waiting_marker, waiting_checks, "validator start mode latch")

# Restart must re-arm all three initial-phase latches.
old_restart_latches = '''        checks.require(
            restart.find("Global.PilihPahlawanDilewati = False;") < restart_at
            and restart.find("Global.PersiapanDilewati = False;") < restart_at,
            "i latch delle fasi iniziali non vengono riarmati prima del Restart Match",
        )
'''
new_restart_latches = '''        checks.require(
            restart.find("Global.PilihPahlawanDilewati = False;") < restart_at
            and restart.find("Global.PersiapanDilewati = False;") < restart_at
            and restart.find("Global.ModeMulaiDiminta = False;") < restart_at,
            "i latch delle fasi iniziali non vengono riarmati prima del Restart Match",
        )
'''
val = once(val, old_restart_latches, new_restart_latches, "validator restart start latch")

# Lifecycle audit: fallback only for never-initialized players and readiness only at the very end.
old_fallback_validator = '''    fallback = [rule for rule in rules if code_contains(rule.body, "Ongoing - Each Player;", "Event Player.SudahSiap == False;", "Call Subroutine(SiapkanPemain);")]
    checks.equal(len(join), 1, "audit lifecycle: init Player Joined")
    checks.equal(len(fallback), 1, "audit lifecycle: init player già presenti")
'''
new_fallback_validator = '''    fallback = [rule for rule in rules if code_contains(rule.body, "Ongoing - Each Player;", "Event Player.SudahSiap == False;", "Call Subroutine(SiapkanPemain);")]
    checks.equal(len(join), 1, "audit lifecycle: init Player Joined")
    checks.equal(len(fallback), 1, "audit lifecycle: init player già presenti")
    if fallback:
        fallback_code = mask_strings(fallback[0].body)
        checks.require(
            "Event Player.PernahDisiapkan == False;" in fallback_code
            and "Event Player.SiklusPemainAktif == False;" in fallback_code,
            "audit lifecycle: fallback può riattivarsi durante un cambio team",
        )
        lock_at = fallback_code.find("Event Player.SiklusPemainAktif = True;")
        setup_at = fallback_code.find("Call Subroutine(SiapkanPemain);")
        checks.require(0 <= lock_at < setup_at, "audit lifecycle: fallback non blocca prima del setup")
'''
val = once(val, old_fallback_validator, new_fallback_validator, "validator bootstrap fallback")

old_join_validator = '''    if join:
        body = mask_strings(join[0].body)
        duplicate_at = body.find("If(Array Contains(Global.PemainManusia, Event Player));")
        cleanup_at = body.find("Call Subroutine(BersihkanPemain);", duplicate_at)
        setup_at = body.find("Call Subroutine(SiapkanPemain);", cleanup_at)
        checks.require(
            0 <= duplicate_at < cleanup_at < setup_at,
            "audit lifecycle: cambio team non esegue cleanup prima della nuova inizializzazione",
        )
'''
new_join_validator = '''    if join:
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
val = once(val, old_join_validator, new_join_validator, "validator serialized join")

# SiapkanPemain must publish readiness only after every other player assignment, and classifier observes the lifecycle lock.
setup_marker = '''    if setup:
        body = mask_strings(setup[0].body)
        for name in sorted(player_names):
            checks.require(
                re.search(rf"Event Player\\.{re.escape(name)}\\s*=", body) is not None,
                f"audit lifecycle: variabile player non inizializzata in SiapkanPemain: {name}",
            )
'''
setup_checks = setup_marker + '''        ready_positions = [m.start() for m in re.finditer(r"Event Player\\.SudahSiap\\s*=\\s*True\\s*;", body)]
        checks.equal(len(ready_positions), 1, "audit lifecycle: un solo publish SudahSiap=True")
        if ready_positions:
            checks.require(
                body.find("Event Player.PernahDisiapkan = True;") < body.find("Event Player.SiklusPemainAktif = False;") < ready_positions[0],
                "audit lifecycle: readiness pubblicata prima della fine del setup",
            )
            checks.require(
                not re.search(r"Event Player\\.[A-Za-z_][A-Za-z0-9_]*\\s*=", body[ready_positions[0] + 1:]),
                "audit lifecycle: assegnazioni player presenti dopo SudahSiap=True",
            )
'''
val = once(val, setup_marker, setup_checks, "validator setup final edge")

classification_marker = '''    if classification:
        body = mask_strings(classification[0].body)
        guard = body.find("Abort If(Array Contains(Global.PemainManusia, Event Player));")
'''
classification_checks = '''    if classification:
        body = mask_strings(classification[0].body)
        checks.require(
            "Event Player.SiklusPemainAktif == False;" in body,
            "audit lifecycle: classificatore può partire durante il setup",
        )
        guard = body.find("Abort If(Array Contains(Global.PemainManusia, Event Player));")
'''
val = once(val, classification_marker, classification_checks, "validator classifier lock")

VAL.write_text(val, encoding="utf-8")
VERSION.write_text("0.6.17\n", encoding="utf-8")

# Docs.
readme = README.read_text(encoding="utf-8")
readme = once(readme, "La versione **0.6.16** identifica lo stato funzionale e tecnico corrente del repository.", "La versione **0.6.17** identifica lo stato funzionale e tecnico corrente del repository.", "README version")
readme += '''\n\n### Cambio team ripetuto 0.6.17\n\nIl lifecycle player è ora serializzato. `01b` resta esclusivamente un bootstrap per i player già presenti quando lo script parte e non può più riattivarsi quando `BersihkanPemain` porta temporaneamente `SudahSiap` a false. `SiapkanPemain` pubblica `SudahSiap = True` soltanto come **ultima azione**, dopo avere completato tutti i reset; la classificazione 02 richiede inoltre che il lock lifecycle sia libero. È stato aggiunto anche un latch one-shot a `Start Game Mode`, l'ultima azione globale di fase che poteva ancora essere richiesta più volte.\n'''
README.write_text(readme, encoding="utf-8")

progetto = PROGETTO.read_text(encoding="utf-8")
progetto = once(progetto, "# Note di progetto — versione 0.6.16", "# Note di progetto — versione 0.6.17", "PROGETTO title")
progetto = once(progetto, "Workshop 0.6.16.", "Workshop 0.6.17.", "PROGETTO version")
progetto += '''\n\n## Lifecycle cambio team serializzato 0.6.17\n\n`SiklusPemainAktif` impedisce re-entry del percorso cleanup/setup. `PernahDisiapkan` rende 01b un fallback solo di bootstrap. La readiness `SudahSiap` viene impostata esclusivamente al termine di `SiapkanPemain`; fino a quel momento 02 non può partire. `ModeMulaiDiminta` rende one-shot anche `Start Game Mode` e viene riarmato soltanto prima del restart completo.\n'''
PROGETTO.write_text(progetto, encoding="utf-8")

test_doc = TEST.read_text(encoding="utf-8")
test_doc = once(test_doc, "# Piano di test — versione 0.6.16", "# Piano di test — versione 0.6.17", "TEST title")
test_doc = once(test_doc, "Workshop 0.6.16.", "Workshop 0.6.17.", "TEST version")
test_doc += '''\n\n## Cambio team ripetuto 0.6.17\n\nTest live prioritario: effettuare almeno cinque cambi consecutivi Team 1 ↔ Team 2, aspettando lo spawn fra un cambio e il successivo. Il primo, secondo e successivi cambi devono completarsi senza `excessive Workshop script load`; gli HUD sociali devono essere distrutti e ricreati una sola volta per ciclo. Ripetere anche un cambio rapido durante la schermata eroe per verificare che il lock impedisca doppie inizializzazioni.\n'''
TEST.write_text(test_doc, encoding="utf-8")

validazione = VALIDAZIONE.read_text(encoding="utf-8")
validazione = once(validazione, "# Rapporto di validazione — versione 0.6.16", "# Rapporto di validazione — versione 0.6.17", "VALIDAZIONE title")
validazione = once(validazione, "Release tecnica: **CHILL Dedicated Server 0.6.16**", "Release tecnica: **CHILL Dedicated Server 0.6.17**", "VALIDAZIONE release")
validazione = once(validazione, "OK - controlli statici v0.6.16 superati", "OK - controlli statici v0.6.17 superati", "VALIDAZIONE result")
validazione += '''\n\n## Gate lifecycle ripetuto 0.6.17\n\nIl validatore impone il lock `SiklusPemainAktif` sul Player Joined, limita 01b a `PernahDisiapkan == False`, richiede che `SudahSiap = True` sia l'ultima assegnazione player di `SiapkanPemain`, blocca la classificazione durante il setup e rende one-shot `Start Game Mode`. Restano valide le invarianti zero-Wait/zero-Loop per ogni regola che crea HUD.\n'''

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

print("Applied CHILL 0.6.17 serialized repeated team-change lifecycle")
