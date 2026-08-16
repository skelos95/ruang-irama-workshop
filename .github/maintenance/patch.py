from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
PROJECT = ROOT / "docs" / "PROGETTO.md"
TEST = ROOT / "docs" / "TEST.md"
VALIDATION = ROOT / "docs" / "VALIDAZIONE.md"
VERSION = ROOT / "VERSION"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected 1 occurrence, found {count}")
    return text.replace(old, new, 1)


VERSION.write_text("0.6.4\n", encoding="utf-8")
validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_once(validator, "della versione 0.6.3.", "della versione 0.6.4.", "validator docstring version")
validator = replace_once(validator, 'CURRENT_VERSION = "0.6.3"', 'CURRENT_VERSION = "0.6.4"', "validator current version")
VALIDATOR.write_text(validator, encoding="utf-8")

# README --------------------------------------------------------------------
text = README.read_text(encoding="utf-8")
text = replace_once(text, "La versione **0.6.3** identifica lo stato funzionale e tecnico corrente del repository.", "La versione **0.6.4** identifica lo stato funzionale e tecnico corrente del repository.", "README version")
text = replace_once(text, "11. `10 - Try Your Luck` — roulette 50/50 cura completa o morte.", "11. `10 - Try Your Luck` — roulette 50/50 con menu bloccato in pagina 10: protezione FULL HP temporanea; verde ripristina l'ultima modalità Unkillable scelta, rosso immobilizza il player con Light Shaft + Ring RGB in chiusura e lo uccide dopo 3 secondi.", "README luck bullet")
text = replace_once(text, "| 10 | Try Your Luck | roulette 50/50 |", "| 10 | Try Your Luck | 50/50; menu bloccato, FULL HP temporaneo, verde ripristina Unkillable, rosso = freeze + Ring/Light Shaft + morte |", "README luck table")
text = replace_once(text, "- test statici: 29 unit test + validatore Workshop.", "- test statici: 33 unit test + validatore Workshop.", "README test count")
anchor = "\n\n### Audit 0.6.3\n"
new_section = '''\n\n### Try Your Luck 0.6.4\n\nDurante la roulette il Menu Arcade **resta aperto sulla pagina 10** e il dispatcher degli input viene bloccato finché `KartuNasibAktif` torna `False`. All'attivazione viene applicato temporaneamente **Unkillable FULL HP** senza modificare `ModeKebalTerakhir`, che conserva l'ultima scelta esplicita del player.\n\n- **Verde:** ripristina OFF / 1 HP / FULL HP in base a `ModeKebalTerakhir`; la restrizione 1 HP nello Spawn Room resta invariata.\n- **Rosso:** porta la protezione runtime a OFF, blocca movimento e knockback, forza la posizione, congela il colore corrente di `Global.RGB`, crea `Light Shaft` e `Ring` sul pavimento e riduce gradualmente il raggio durante il countdown 3-2-1 prima della morte.\n- Morte, leave e cambio squadra fermano il forcing/chase, ripristinano movimento e knockback e distruggono gli effetti senza lasciare entità orfane.\n\nCamera e Teleport ora escludono dai rispettivi elenchi target entità non esistenti, non spawnate o morte. Il Teleport obiettivo usa inoltre la stessa sorgente della sua esecuzione: Payload per Escort/Hybrid, flag nemica valida per CTF, proxy/fallback per Push e `Objective Position` negli altri casi.\n'''
if anchor not in text:
    raise RuntimeError("README audit anchor not found")
text = text.replace(anchor, new_section + anchor, 1)
README.write_text(text, encoding="utf-8")

# PROGETTO ------------------------------------------------------------------
text = PROJECT.read_text(encoding="utf-8")
text = replace_once(text, "# Note di progetto — versione 0.6.3", "# Note di progetto — versione 0.6.4", "project title")
text = replace_once(text, "Questo documento descrive lo **stato funzionale e tecnico corrente** del Workshop 0.6.3.", "Questo documento descrive lo **stato funzionale e tecnico corrente** del Workshop 0.6.4.", "project intro")
text = replace_once(text, "| 10 | Try Your Luck | crea una carta pubblica; solo il proprietario può attivarla, con esito 50/50 cura completa o morte |", "| 10 | Try Your Luck | roulette 50/50; pagina 10 bloccata durante l'esecuzione, FULL HP temporaneo, verde ripristina l'ultima scelta Unkillable, rosso immobilizza e uccide dopo il countdown |", "project menu row")
start = text.find("## Menu 10 — Try Your Luck\n")
end = text.find("\n## Jump respawn\n", start)
if start < 0 or end < 0:
    raise RuntimeError("project Try Your Luck section markers not found")
section = '''## Menu 10 — Try Your Luck\n\nInteract avvia una carta pubblica con bracket e Heart/Skull persistenti. La roulette mantiene 20..24 cambi, intervallo iniziale 0,08 s e rallentamento +0,055 s per passaggio. La camera non viene modificata.\n\nDurante `KartuNasibAktif == True` il Menu Arcade resta aperto sulla **pagina 10** e il dispatcher non accetta navigazione, back o nuove applicazioni. L'avvio salva la preferenza Unkillable in `ModeKebalTerakhir` e applica soltanto a runtime `ModeKebal = 2`, `KebalAktif = True`, status Unkillable, Damage Received 0% e Max Health. La preferenza del player non viene sovrascritta.\n\nEsito verde:\n\n- `ModeKebalTerakhir = 0` → OFF, Damage Received 100%, salute piena;\n- `ModeKebalTerakhir = 1` → 1 HP fuori Spawn Room; dentro Spawn Room resta runtime OFF e la preferenza 1 HP resta memorizzata;\n- `ModeKebalTerakhir = 2` → FULL HP con Damage Received 0%, Max Health e Halo RGB.\n\nEsito rosso:\n\n1. la protezione runtime passa a OFF;\n2. vengono salvati `PosisiNasibTerkunci` e il colore corrente `Global.RGB` in `WarnaNasibTerkunci`;\n3. Move Speed e Knockback Received passano a 0 e parte `Start Forcing Player Position`;\n4. vengono creati `Light Shaft` e `Ring` a terra con il colore congelato;\n5. `RadiusNasib` viene inseguito da 4 a 0,25 in 3 secondi mentre scorrono i messaggi 3-2-1;\n6. il player viene ucciso.\n\nIl cleanup su morte, leave e cambio team interrompe il chase, ferma il forcing, ripristina Move Speed/Knockback Received a 100 e distrugge entrambi gli effetti.\n'''
text = text[:start] + section + text[end:]
text = replace_once(text, "La CI esegue 29 unit test e il validatore statico.", "La CI esegue 33 unit test e il validatore statico.", "project test count")
PROJECT.write_text(text, encoding="utf-8")

# TEST ----------------------------------------------------------------------
text = TEST.read_text(encoding="utf-8")
text = replace_once(text, "# Piano di test — versione 0.6.3", "# Piano di test — versione 0.6.4", "test title")
text = replace_once(text, "Questa matrice descrive lo **stato funzionale e tecnico corrente** del Workshop 0.6.3.", "Questa matrice descrive lo **stato funzionale e tecnico corrente** del Workshop 0.6.4.", "test intro")
text = replace_once(text, "Ran 29 tests", "Ran 33 tests", "test count")
text = replace_once(text, "- CTF: vicino alla flag nemica.", "- CTF: vicino alla flag nemica solo quando la posizione della flag è valida.", "test CTF")
text = replace_once(text, "- Player target: posizione camminabile vicina al target.", "- Player target: posizione camminabile vicina al target; player/bot morti o non spawnati non devono comparire nell'elenco.", "test teleport live target")
text = replace_once(text, "- Se il target esce durante l'azione, il teleport deve annullarsi senza retarget accidentale.", "- Se il target esce o muore durante l'azione, il teleport deve annullarsi senza retarget accidentale.", "test teleport invalidation")
text = replace_once(text, "- Se il target esce, la camera deve tornare a uno stato valido.", "- Target morti/non spawnati non devono essere proposti; se il target selezionato esce, la camera deve tornare a uno stato valido.", "test camera targets")
old = "- Try Your Luck: attivazione chiude e blocca il menu, forza Unkillable OFF e non cambia la camera; morte/leave devono distruggere entrambi i bracket e Heart/Skull senza oggetti orfani."
new = "- Try Your Luck: l'attivazione lascia il menu aperto e bloccato sulla pagina 10, forza temporaneamente FULL HP e non cambia la camera. Verde deve ripristinare l'ultima scelta Unkillable. Rosso deve passare runtime a OFF, bloccare movimento/knockback, forzare la posizione, creare Light Shaft + Ring con l'RGB congelato, restringere il Ring durante 3-2-1 e poi uccidere il player. Morte/leave/team switch devono ripristinare movimento/knockback, fermare forcing/chase e distruggere bracket, Heart/Skull, Light Shaft e Ring senza oggetti orfani."
text = replace_once(text, old, new, "test menu10")
text = text.replace("- **Unkillable 1 HP:** attivare 1 HP, verificare salute a 1, ritorno a 1 quando raggiunge il massimo e Halo visibile a tutti anche con Crouch Privacy ON.", "- **Unkillable 1 HP:** attivare 1 HP, verificare salute a 1, ritorno a 1 quando raggiunge il massimo e Warning rosso visibile a tutti anche con Crouch Privacy ON.")
TEST.write_text(text, encoding="utf-8")

# VALIDAZIONE ---------------------------------------------------------------
text = VALIDATION.read_text(encoding="utf-8")
text = replace_once(text, "# Rapporto di validazione — versione 0.6.3", "# Rapporto di validazione — versione 0.6.4", "validation title")
text = replace_once(text, "Release tecnica: **CHILL Dedicated Server 0.6.3**", "Release tecnica: **CHILL Dedicated Server 0.6.4**", "validation release")
text = replace_once(text, "## Audit 0.6.3", "## Audit 0.6.4", "validation audit")
text = replace_once(text, "- Menu 10: bracket + Heart/Skull persistenti, nessun cambio camera, Unkillable OFF, reset morte/leave, 50/50;", "- Menu 10: bracket + Heart/Skull persistenti, menu bloccato in pagina 10, FULL HP temporaneo senza perdere l'ultima scelta, verde = ripristino scelta, rosso = OFF + forcing posizione + Light Shaft/Ring RGB in chiusura + morte; cleanup completo morte/leave/team switch;", "validation menu10")
text = replace_once(text, "- Camera con un solo raycast e `MulaiKamera` senza `Stop Camera` immediatamente prima del nuovo `Start Camera`;", "- Camera con un solo raycast, target list limitata a entità esistenti/spawnate/vive e `MulaiKamera` senza `Stop Camera` immediatamente prima del nuovo `Start Camera`;", "validation camera")
text = replace_once(text, "Ran 29 tests", "Ran 33 tests", "validation tests")
text = replace_once(text, "OK - controlli statici v0.6.3 superati", "OK - controlli statici v0.6.4 superati", "validation result")
text = replace_once(text, "- Crouch inspection/Teleport;", "- Crouch inspection/Teleport, inclusi target morti/non spawnati e disponibilità obiettivo per Escort/Hybrid/CTF/Push;", "validation live teleport")
text = replace_once(text, "- Try Your Luck durante movimento/camera 3P;", "- Try Your Luck verde/rosso durante movimento e camera 3P, inclusi forcing posizione, Ring/Light Shaft, countdown e cleanup;", "validation live luck")
VALIDATION.write_text(text, encoding="utf-8")
