from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
README = ROOT / "README.md"
PROGETTO = ROOT / "docs" / "PROGETTO.md"
TEST_DOC = ROOT / "docs" / "TEST.md"
VALIDAZIONE = ROOT / "docs" / "VALIDAZIONE.md"
VERSION = ROOT / "VERSION"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected 1 occurrence, found {count}")
    return text.replace(old, new, 1)


source = SOURCE.read_text(encoding="utf-8")

preload_rule = r'''rule("05e - Menu: Muat halaman lain bertahap setelah menu utama tampil")
{
	event
	{
		Ongoing - Each Player;
		All;
		All;
	}

	conditions
	{
		Event Player.Manusia == True;
		Event Player.BotOtomatis == False;
		Is Dummy Bot(Event Player) == False;
		Is Alive(Event Player) == True;
		Event Player.MenuTerbuka == True;
		Count Of(Event Player.HalamanHudMenuArcade) > 0;
		Count Of(Event Player.HalamanHudMenuArcade) < 13;
	}

	actions
	{
		"Main Menu sudah tampil. Buat maksimal satu HUD tersembunyi per siklus agar submenu siap tanpa pop dan tanpa beban besar dalam satu tick."
		Wait(0.016, Abort When False);
		If(Array Contains(Event Player.HalamanHudMenuArcade, 0) == False);
			Call Subroutine(GambarMusik);
		Else If(Array Contains(Event Player.HalamanHudMenuArcade, 1) == False);
			Call Subroutine(GambarKamera);
		Else If(Array Contains(Event Player.HalamanHudMenuArcade, 2) == False);
			Call Subroutine(GambarWarna);
		Else If(Array Contains(Event Player.HalamanHudMenuArcade, 3) == False);
			Call Subroutine(GambarBahasa);
		Else If(Array Contains(Event Player.HalamanHudMenuArcade, 4) == False);
			Call Subroutine(GambarBalasDendam);
		Else If(Array Contains(Event Player.HalamanHudMenuArcade, 5) == False);
			Call Subroutine(GambarKebal);
		Else If(Array Contains(Event Player.HalamanHudMenuArcade, 6) == False);
			Call Subroutine(GambarSuara);
		Else If(Array Contains(Event Player.HalamanHudMenuArcade, 7) == False);
			Call Subroutine(GambarIkon);
		Else If(Array Contains(Event Player.HalamanHudMenuArcade, 8) == False);
			Call Subroutine(GambarSakelarTeleportasi);
		Else If(Array Contains(Event Player.HalamanHudMenuArcade, 9) == False);
			Call Subroutine(GambarPrivasiInspeksi);
		Else If(Array Contains(Event Player.HalamanHudMenuArcade, 10) == False);
			Call Subroutine(GambarNasib);
		Else If(Array Contains(Event Player.HalamanHudMenuArcade, 11) == False);
			Call Subroutine(GambarPilihan);
		End;
		Loop If Condition Is True;
	}
}

'''

if 'rule("05e - Menu: Muat halaman lain bertahap setelah menu utama tampil")' in source:
    raise RuntimeError("progressive preload rule already exists")
source = replace_once(
    source,
    'rule("06 - Menu: Tembakan utama memilih berikutnya")',
    preload_rule + 'rule("06 - Menu: Tembakan utama memilih berikutnya")',
    "insert progressive preload rule",
)

# The existing lazy router remains as a correctness fallback if a player reaches a page
# before the background preload has prepared it.
if "Array Contains(Event Player.HalamanHudMenuArcade, Event Player.HalamanMenu) == False" not in source:
    raise RuntimeError("lazy GambarMenu fallback missing")

SOURCE.write_text(source, encoding="utf-8")

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_once(validator, "della versione 0.6.13.", "della versione 0.6.14.", "validator doc version")
validator = replace_once(validator, 'CURRENT_VERSION = "0.6.13"', 'CURRENT_VERSION = "0.6.14"', "validator current version")

# Certify that background preload is distributed and never recreates the Main Menu.
anchor = '''    router_rules = rules_containing(rules, "Subroutine;", "GambarMenu;")
    checks.equal(len(router_rules), 1, "router split GambarMenu")
'''
extra = '''    preload_rules = [
        rule for rule in rules
        if rule.name.startswith("05e - Menu: Muat halaman lain bertahap")
    ]
    checks.equal(len(preload_rules), 1, "preload progressivo HUD Arcade")
    if preload_rules:
        preload = preload_rules[0].body
        preload_code = mask_strings(preload)
        checks.require(
            code_contains(
                preload,
                "Event Player.MenuTerbuka == True;",
                "Count Of(Event Player.HalamanHudMenuArcade) > 0;",
                "Count Of(Event Player.HalamanHudMenuArcade) < 13;",
                "Wait(0.016, Abort When False);",
                "Loop If Condition Is True;",
            ),
            "preload progressivo non è bounded alla sessione Menu Arcade",
        )
        checks.require(
            "Create HUD Text" not in preload_code,
            "preload progressivo deve delegare ai renderer senza duplicare HUD",
        )
        checks.require(
            "Call Subroutine(GambarUtama);" not in preload_code,
            "preload progressivo non deve ricreare il Main Menu",
        )
        progressive_renderers = (
            "GambarMusik", "GambarKamera", "GambarWarna", "GambarBahasa",
            "GambarBalasDendam", "GambarKebal", "GambarSuara", "GambarIkon",
            "GambarSakelarTeleportasi", "GambarPrivasiInspeksi", "GambarNasib", "GambarPilihan",
        )
        for page, renderer in enumerate(progressive_renderers):
            checks.require(
                f"Array Contains(Event Player.HalamanHudMenuArcade, {page}) == False" in preload_code,
                f"preload progressivo privo del gate pagina {page}",
            )
            checks.require(
                f"Call Subroutine({renderer});" in preload_code,
                f"preload progressivo non prepara {renderer}",
            )
        checks.equal(
            preload_code.count("Call Subroutine("),
            12,
            "preload progressivo deve creare al massimo una delle 12 pagine per iterazione",
        )

''' + anchor
validator = replace_once(validator, anchor, extra, "validator progressive preload")
VALIDATOR.write_text(validator, encoding="utf-8")

VERSION.write_text("0.6.14\n", encoding="utf-8")

readme = README.read_text(encoding="utf-8")
readme = replace_once(
    readme,
    "La versione **0.6.13** identifica lo stato funzionale e tecnico corrente del repository.",
    "La versione **0.6.14** identifica lo stato funzionale e tecnico corrente del repository.",
    "README version",
)
readme += '''\n\n### Preload progressivo dei sottomenu 0.6.14\n\nIl Main Menu continua ad apparire appena termina il hold Melee da 0,5 s. Subito dopo, una regola separata prepara in background le altre 12 pagine **una sola per frame** (`Wait(0.016, Abort When False)`), mentre restano invisibili grazie alla visibilità dinamica già esistente. In questo modo il primo accesso a un sottomenu non deve più creare il relativo HUD nello stesso istante in cui viene mostrato. Il router lazy rimane come fallback se il player riesce ad aprire una pagina prima che il preload l'abbia preparata. Chiudendo il menu il preload si interrompe automaticamente e il cleanup continua a distruggere soltanto gli HUD effettivamente creati.\n'''
README.write_text(readme, encoding="utf-8")

progetto = PROGETTO.read_text(encoding="utf-8")
progetto = replace_once(progetto, "# Note di progetto — versione 0.6.13", "# Note di progetto — versione 0.6.14", "PROGETTO title")
progetto = replace_once(progetto, "Workshop 0.6.13.", "Workshop 0.6.14.", "PROGETTO version")
progetto += '''\n\n## Preload HUD progressivo 0.6.14\n\nLa cache lazy resta la sorgente di verità, ma dopo la creazione del Main Menu (`HalamanHudMenuArcade` non vuoto) la regola 05e prepara le pagine 0..11 in ordine. Ogni iterazione inizia con un wait da 0,016 s e chiama al massimo un renderer, distribuendo la costruzione degli HUD su frame differenti. Le pagine restano nascoste finché `HalamanMenu` non coincide; non viene duplicato alcun `Create HUD Text` dentro il preload.\n'''
PROGETTO.write_text(progetto, encoding="utf-8")

test_doc = TEST_DOC.read_text(encoding="utf-8")
test_doc = replace_once(test_doc, "# Piano di test — versione 0.6.13", "# Piano di test — versione 0.6.14", "TEST title")
test_doc = replace_once(test_doc, "Workshop 0.6.13.", "Workshop 0.6.14.", "TEST version")
test_doc += '''\n\n## Preload progressivo sottomenu 0.6.14\n\nTest live: aprire il Menu Arcade e attendere circa 0,2–0,3 s senza entrare in un sottomenu; poi visitare rapidamente tutte le pagine con Interact/Reload. Nessuna pagina dovrebbe più comparire con il precedente pop di creazione al primo accesso. Ripetere chiudendo e riaprendo il menu più volte, verificando che il Main continui ad apparire subito dopo 0,5 s e che Script Diagnostics non mostri regressioni rilevanti. Come stress test, aprire immediatamente un sottomenu appena appare il Main: il router lazy deve continuare a garantire la corretta visualizzazione anche se il preload non è ancora arrivato a quella pagina.\n'''
TEST_DOC.write_text(test_doc, encoding="utf-8")

validazione = VALIDAZIONE.read_text(encoding="utf-8")
validazione = replace_once(validazione, "# Rapporto di validazione — versione 0.6.13", "# Rapporto di validazione — versione 0.6.14", "VALIDAZIONE title")
validazione = replace_once(validazione, "Release tecnica: **CHILL Dedicated Server 0.6.13**", "Release tecnica: **CHILL Dedicated Server 0.6.14**", "VALIDAZIONE release")
validazione = replace_once(validazione, "OK - controlli statici v0.6.13 superati", "OK - controlli statici v0.6.14 superati", "VALIDAZIONE result")
validazione += '''\n\n## Preload progressivo 0.6.14\n\nIl gate richiede una sola regola 05e di preload, attiva soltanto con Menu Arcade aperto e cache già iniziata, con `Count Of(HalamanHudMenuArcade) < 13`, un `Wait(0.016, Abort When False)` prima di ogni iterazione e 12 renderer delegati senza `Create HUD Text` diretto. `GambarUtama` non può essere richiamato dal preload e il router lazy resta presente come fallback.\n'''

data = SOURCE.read_bytes().replace(b"\r\n", b"\n")
payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
blob = hashlib.sha1(payload).hexdigest()
validazione, count = re.subn(
    r"(Blob Git del sorgente Workshop validato:\n\n```text\n)[0-9a-f]{40}(\n```)",
    rf"\g<1>{blob}\g<2>",
    validazione,
    count=1,
)
if count != 1:
    raise RuntimeError("VALIDAZIONE blob marker not found")
VALIDAZIONE.write_text(validazione, encoding="utf-8")

print("Applied CHILL 0.6.14 progressive Arcade HUD preload")
