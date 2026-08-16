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

# Dedicated one-shot guards for the initial phase skips and the per-player social HUD creation.
src = once(
    src,
    "\t\t47: IndeksVote\n\tplayer:\n",
    "\t\t47: IndeksVote\n\t\t48: PilihPahlawanDilewati\n\t\t49: PersiapanDilewati\n\tplayer:\n",
    "global phase latch declarations",
)
src = once(
    src,
    "\t\t89: HalamanHudMenuArcade\n}\n",
    "\t\t89: HalamanHudMenuArcade\n\t\t90: HudPemainDibuat\n}\n",
    "player HUD latch declaration",
)

src = once(
    src,
    "\t\tGlobal.IndeksVote = 0;\n",
    "\t\tGlobal.IndeksVote = 0;\n\t\tGlobal.PilihPahlawanDilewati = False;\n\t\tGlobal.PersiapanDilewati = False;\n",
    "initial phase latch setup",
)

old_assemble = '''rule("00a2 - Umum: Lewati pemilihan pahlawan")
{
	event
	{
		Ongoing - Global;
	}

	conditions
	{
		Global.Siap == True;
		Is Assembling Heroes == True;
	}

	actions
	{
		Set Match Time(0);
	}
}
'''
new_assemble = '''rule("00a2 - Umum: Lewati pemilihan pahlawan")
{
	event
	{
		Ongoing - Global;
	}

	conditions
	{
		Global.Siap == True;
		Global.PilihPahlawanDilewati == False;
		Is Game In Progress == False;
		Is Assembling Heroes == True;
	}

	actions
	{
		"Jalankan satu kali hanya pada fase awal; pindah tim saat pertandingan berjalan tidak boleh memicu spam Set Match Time."
		Global.PilihPahlawanDilewati = True;
		Set Match Time(0);
	}
}
'''
src = once(src, old_assemble, new_assemble, "assemble one-shot")

old_setup = '''rule("00a3 - Umum: Lewati persiapan awal")
{
	event
	{
		Ongoing - Global;
	}

	conditions
	{
		Global.Siap == True;
		Is In Setup == True;
	}

	actions
	{
		Set Match Time(0);
	}
}
'''
new_setup = '''rule("00a3 - Umum: Lewati persiapan awal")
{
	event
	{
		Ongoing - Global;
	}

	conditions
	{
		Global.Siap == True;
		Global.PersiapanDilewati == False;
		Is Game In Progress == False;
		Is In Setup == True;
	}

	actions
	{
		"Lewati persiapan sekali saja agar aturan global tidak menembak Set Match Time terus-menerus."
		Global.PersiapanDilewati = True;
		Set Match Time(0);
	}
}
'''
src = once(src, old_setup, new_setup, "setup one-shot")

# Re-arm the phase latches immediately before an intentional full match restart.
src = once(
    src,
    "\t\tGlobal.MulaiUlangSudahDiminta = True;\n\t\tRestart Match;\n",
    "\t\tGlobal.MulaiUlangSudahDiminta = True;\n\t\tGlobal.PilihPahlawanDilewati = False;\n\t\tGlobal.PersiapanDilewati = False;\n\t\tRestart Match;\n",
    "restart phase latch reset",
)

# If a team transition happens during the 0.016 classifier probes, stop cleanly and allow a retry.
first_probe = '''\t\tWait(0.016, Ignore Condition);
\t\tAbort If(Entity Exists(Event Player) == False);
\t\tIf(Custom String("{0}", Event Player) == Custom String("​"));
'''
first_probe_new = '''\t\tWait(0.016, Ignore Condition);
\t\tAbort If(Entity Exists(Event Player) == False);
\t\tIf(Or(Event Player.SudahSiap == False, Has Spawned(Event Player) == False));
\t\t\tStop Forcing Dummy Bot Name(Event Player);
\t\t\tEvent Player.SudahDiperiksa = False;
\t\t\tAbort;
\t\tEnd;
\t\tIf(Custom String("{0}", Event Player) == Custom String("​"));
'''
src = once(src, first_probe, first_probe_new, "first classifier transition guard")

second_probe = '''\t\tWait(0.016, Ignore Condition);
\t\tAbort If(Entity Exists(Event Player) == False);
\t\tStop Forcing Dummy Bot Name(Event Player);
'''
second_probe_new = '''\t\tWait(0.016, Ignore Condition);
\t\tAbort If(Entity Exists(Event Player) == False);
\t\tIf(Or(Event Player.SudahSiap == False, Has Spawned(Event Player) == False));
\t\t\tStop Forcing Dummy Bot Name(Event Player);
\t\t\tEvent Player.SudahDiperiksa = False;
\t\t\tAbort;
\t\tEnd;
\t\tStop Forcing Dummy Bot Name(Event Player);
'''
src = once(src, second_probe, second_probe_new, "second classifier transition guard")

# Social HUD creation is still zero-wait/zero-loop, but now absolutely one-shot per lifecycle.
src = once(
    src,
    "\t\tArray Contains(Global.PemainManusia, Event Player) == True;\n\t\tEvent Player.HudKiri == Null;\n\t\tEvent Player.HudKanan == Null;\n",
    "\t\tArray Contains(Global.PemainManusia, Event Player) == True;\n\t\tHas Spawned(Event Player) == True;\n\t\tEvent Player.HudPemainDibuat == False;\n\t\tEvent Player.HudKiri == Null;\n\t\tEvent Player.HudKanan == Null;\n",
    "social HUD stable conditions",
)
src = once(
    src,
    "\t\t\"Klasifikasi manusia dan bot sudah selesai. HUD pemain dibuat pada aturan terpisah tanpa tunda dan tanpa pengulangan.\"\n\t\tCreate HUD Text(",
    "\t\t\"Klasifikasi manusia dan bot sudah selesai. HUD pemain dibuat sekali pada keadaan spawn yang stabil.\"\n\t\tEvent Player.HudPemainDibuat = True;\n\t\tCreate HUD Text(",
    "social HUD one-shot action",
)

# Reset the player latch both on cleanup and fresh setup.
src = once(
    src,
    "\t\tEvent Player.Manusia = False;\n\n\t\tIf(Event Player.TeksKartuNasib != Null);\n",
    "\t\tEvent Player.Manusia = False;\n\t\tEvent Player.HudPemainDibuat = False;\n\n\t\tIf(Event Player.TeksKartuNasib != Null);\n",
    "cleanup player HUD latch",
)
src = once(
    src,
    "\t\tEvent Player.HudKiri = Null;\n\t\tEvent Player.HudKanan = Null;\n",
    "\t\tEvent Player.HudKiri = Null;\n\t\tEvent Player.HudKanan = Null;\n\t\tEvent Player.HudPemainDibuat = False;\n",
    "setup player HUD latch",
)

SRC.write_text(src, encoding="utf-8")

# Validator 0.6.16.
val = VAL.read_text(encoding="utf-8")
val = once(val, "della versione 0.6.15.", "della versione 0.6.16.", "validator doc version")
val = once(val, 'CURRENT_VERSION = "0.6.15"', 'CURRENT_VERSION = "0.6.16"', "validator version")

assemble_marker = '''    checks.equal(len(assembling), 1, "skip Assemble Heroes")

    setup = [
'''
assemble_checks = '''    checks.equal(len(assembling), 1, "skip Assemble Heroes")
    if assembling:
        assemble_code = mask_strings(assembling[0].body)
        checks.require(
            "Global.PilihPahlawanDilewati == False;" in assemble_code
            and "Is Game In Progress == False;" in assemble_code,
            "skip Assemble Heroes non protetto da latch one-shot/in-match",
        )
        latch_at = assemble_code.find("Global.PilihPahlawanDilewati = True;")
        set_time_at = assemble_code.find("Set Match Time(0);")
        checks.require(0 <= latch_at < set_time_at, "latch Assemble deve armarsi prima di Set Match Time")

    setup = [
'''
val = once(val, assemble_marker, assemble_checks, "validator assemble latch")

setup_marker = '''    checks.equal(len(setup), 1, "skip fase Setup")

    checks.require(
'''
setup_checks = '''    checks.equal(len(setup), 1, "skip fase Setup")
    if setup:
        setup_code = mask_strings(setup[0].body)
        checks.require(
            "Global.PersiapanDilewati == False;" in setup_code
            and "Is Game In Progress == False;" in setup_code,
            "skip Setup non protetto da latch one-shot/in-match",
        )
        latch_at = setup_code.find("Global.PersiapanDilewati = True;")
        set_time_at = setup_code.find("Set Match Time(0);")
        checks.require(0 <= latch_at < set_time_at, "latch Setup deve armarsi prima di Set Match Time")

    checks.require(
'''
val = once(val, setup_marker, setup_checks, "validator setup latch")

# Strengthen restart validation: phase latches must be re-armed before Restart Match.
restart_marker = '''        checks.require(
            0 <= set_guard < restart_at,
            "la guardia MulaiUlangSudahDiminta deve essere impostata prima del riavvio",
        )
'''
restart_checks = restart_marker + '''        checks.require(
            restart.find("Global.PilihPahlawanDilewati = False;") < restart_at
            and restart.find("Global.PersiapanDilewati = False;") < restart_at,
            "i latch delle fasi iniziali non vengono riarmati prima del Restart Match",
        )
'''
val = once(val, restart_marker, restart_checks, "validator restart latches")

hud_marker = '''    if player_hud:
        pc=mask_strings(player_hud[0].body)
        checks.equal(pc.count("Create HUD Text("),2,"HUD player sinistro/destra")
        checks.require("Wait(" not in pc and "Loop If Condition Is True;" not in pc,"HUD player contiene Wait/Loop")
'''
hud_checks = '''    if player_hud:
        pc=mask_strings(player_hud[0].body)
        checks.equal(pc.count("Create HUD Text("),2,"HUD player sinistro/destra")
        checks.require("Wait(" not in pc and "Loop If Condition Is True;" not in pc,"HUD player contiene Wait/Loop")
        checks.require(
            "Has Spawned(Event Player) == True;" in pc
            and "Event Player.HudPemainDibuat == False;" in pc,
            "HUD player non è protetto durante il cambio team",
        )
        latch_at = pc.find("Event Player.HudPemainDibuat = True;")
        first_hud_at = pc.find("Create HUD Text(")
        checks.require(0 <= latch_at < first_hud_at, "latch HUD player deve armarsi prima della prima Create HUD Text")
'''
val = once(val, hud_marker, hud_checks, "validator player HUD latch")

# Classifier must explicitly abandon transient team-change states and permit a retry.
classifier_marker = '''    if classification:
        body = classification[0].body
        code = mask_strings(body)
'''
classifier_checks = '''    if classification:
        body = classification[0].body
        code = mask_strings(body)
        checks.require(
            code.count("Has Spawned(Event Player) == False") >= 2
            and code.count("Event Player.SudahDiperiksa = False;") >= 2,
            "classificazione non abbandona in sicurezza una transizione di team",
        )
'''
val = once(val, classifier_marker, classifier_checks, "validator classifier team transition")

VAL.write_text(val, encoding="utf-8")
VERSION.write_text("0.6.16\n", encoding="utf-8")

# Documentation refresh.
readme = README.read_text(encoding="utf-8")
readme = once(readme, "La versione **0.6.15** identifica lo stato funzionale e tecnico corrente del repository.", "La versione **0.6.16** identifica lo stato funzionale e tecnico corrente del repository.", "README version")
readme += '''\n\n### Protezione cambio team 0.6.16\n\nIl cambio team durante una partita non può più riattivare in modo continuo le regole globali che saltano Assemble Heroes/Setup. Entrambe sono ora one-shot, valide solo prima che la partita sia in corso e riarmate soltanto prima di un vero `Restart Match`. La creazione dei due HUD sociali resta senza `Wait` e senza `Loop`, ma usa un latch per-player impostato **prima** del primo `Create HUD Text` e richiede uno spawn stabile. La classificazione umano/bot abbandona e ritenta se il player entra in una transizione di team durante i due probe da 0,016 s.\n'''
README.write_text(readme, encoding="utf-8")

progetto = PROGETTO.read_text(encoding="utf-8")
progetto = once(progetto, "# Note di progetto — versione 0.6.15", "# Note di progetto — versione 0.6.16", "PROGETTO title")
progetto = once(progetto, "Workshop 0.6.15.", "Workshop 0.6.16.", "PROGETTO version")
progetto += '''\n\n## Cambio team senza picchi di script load 0.6.16\n\nLe regole 00a2/00a3 non possono più eseguire `Set Match Time(0)` a raffica durante una selezione eroe in-match: hanno latch globali one-shot e `Is Game In Progress == False`. `02b` possiede inoltre `HudPemainDibuat`, armato prima della creazione HUD, così un ID HUD anomalo durante una transizione non può trasformare la regola Ongoing in una fabbrica HUD per-frame.\n'''
PROGETTO.write_text(progetto, encoding="utf-8")

test_doc = TEST.read_text(encoding="utf-8")
test_doc = once(test_doc, "# Piano di test — versione 0.6.15", "# Piano di test — versione 0.6.16", "TEST title")
test_doc = once(test_doc, "Workshop 0.6.15.", "Workshop 0.6.16.", "TEST version")
test_doc += '''\n\n## Cambio team 0.6.16\n\nTest live prioritario: durante una partita in corso cambiare Team 1 → Team 2 e viceversa, restare alcuni secondi nella schermata scelta eroe e poi scegliere un eroe. Il server non deve più mostrare `The server closed due to excessive Workshop script load`. Gli HUD sociali devono ricomparire una sola volta dopo lo spawn. Ripetere il cambio team più volte e controllare Script Diagnostics/server load se disponibile.\n'''
TEST.write_text(test_doc, encoding="utf-8")

validazione = VALIDAZIONE.read_text(encoding="utf-8")
validazione = once(validazione, "# Rapporto di validazione — versione 0.6.15", "# Rapporto di validazione — versione 0.6.16", "VALIDAZIONE title")
validazione = once(validazione, "Release tecnica: **CHILL Dedicated Server 0.6.15**", "Release tecnica: **CHILL Dedicated Server 0.6.16**", "VALIDAZIONE release")
validazione = once(validazione, "OK - controlli statici v0.6.15 superati", "OK - controlli statici v0.6.16 superati", "VALIDAZIONE result")
validazione += '''\n\n## Gate cambio team 0.6.16\n\nIl validatore richiede latch one-shot e guardia `Is Game In Progress == False` per Assemble Heroes/Setup, reset dei latch prima del vero restart, protezione one-shot `HudPemainDibuat` prima di ogni creazione HUD sociale e guardie di transizione nella classificazione umano/bot. Resta valida l'invariante 0.6.15: nessuna regola che contiene `Create HUD Text` può contenere `Wait` o `Loop If Condition Is True`.\n'''

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

print("Applied CHILL 0.6.16 team-change script-load guards")
