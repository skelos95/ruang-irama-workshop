from __future__ import annotations

from pathlib import Path
import re

README = Path("README.md")
VERSION = Path("VERSION")
PROJECT = Path("docs/PROGETTO.md")
VALIDATION = Path("docs/VALIDAZIONE.md")
TESTS = Path("docs/TEST.md")
VALIDATOR = Path("tools/validate_workshop.py")
SOURCE = Path("workshop/ruang_irama.workshop")

VERSION.write_text("0.6.0\n", encoding="utf-8")

readme = r'''# CHILL Dedicated Server — Overwatch Workshop

**CHILL Dedicated Server** è un overlay sociale/Arcade per Overwatch 2 pensato per lobby fino a **12 player attivi**. Aggiunge HUD sociali, soundtrack personale, colori nome, camera, Revenge, modalità 1 HP, modifica voce, icona personale, teleport rapido, respawn manuale e strumenti di ispezione senza imporre mappe o preset lobby.

Versione corrente: **0.6.0 — Social Arcade Refresh**. Lo stato resta **static-ready, live-pending**: validatore e CI verificano struttura e invarianti, mentre importazione, rendering e stress reale richiedono il client Overwatch.

## Funzioni principali

- HUD centrale con `CHILL DEDICATED SERVER`, countdown personalizzato e `SERVER LOCATION` configurabile tra 26 località asiatiche.
- Avvio immediato: Waiting for Players, Assemble Heroes e Setup vengono saltati senza usare `Match Time` per il countdown CHILL.
- Due roster sociali: a sinistra icona personale + icona eroe + player + minuti (`N MIN`), a destra icona personale + icona eroe + player + genere scelto.
- **8 menu Arcade**:
  1. `0 - Soundtrack` — 100 generi.
  2. `1 - Third-Person Camera` — OFF, self o spectate di player/bot validi.
  3. `2 - Name Color` — **32 colori**.
  4. `3 - HUD Language` — English / Bahasa Indonesia / ไทย.
  5. `4 - Revenge` — debiti basati sulle kill dirette ricevute.
  6. `5 - Unkillable: 1 HP` — bloccato in Spawn Room e auto-disattivato entrando nello spawn.
  7. `6 - Hero Voice` — Normal, Low 0.50x / 0.75x, High 1.25x / 1.50x.
  8. `7 - Player Icon` — **37 voci**: `Nothing` + tutte le 36 icone Workshop standard; default `Nothing`.
- I cursori dei menu persistono tra chiusura e riapertura.
- Il colore principale di ogni menu corrisponde al relativo sottomenu e passa da una palette all'altra con una sfumatura di circa **0,35 s**; gli input mantengono i propri colori fissi.
- Feedback `Small Message` + effetto visivo + audio solo quando una scelta cambia davvero; premere `Interact` sulla stessa opzione è un no-op.
- RGB globale pastel/neon lento (~51 s per ciclo) per titolo, timer ed effetti visuali.
- Crouch inspection: mostra icona eroe, nome e salute del target anche oltre gli ostacoli previsti dal sistema di selezione, senza percentuale Ultimate.
- Crouch Teleport: overlay tenuto con Crouch per Spawn Room, obiettivo/modalità e player validi; non è più una voce del Menu Arcade.
- `Jump` da morto forza un respawn vicino al punto di morte tramite `Nearest Walkable Position`.
- Camera rapida fuori menu: tieni `Interact` per 0,5 s per alternare terza/prima persona.
- Diagnostica prestazionale opzionale host-only con LOAD/AVG/MAX e conteggi HUD/IWT.

## Controlli

| Contesto | Input | Azione |
|---|---|---|
| Sempre | Tieni Melee 0,5 s | Apre/chiude il Menu Arcade |
| Fuori menu | Tieni Interact 0,5 s | Alterna terza persona / prima persona |
| Fuori menu | Tieni Crouch | Apre il sistema Crouch (inspect + Teleport overlay) |
| Da morto, menu chiuso | Jump | Respawn vicino al punto di morte |
| Main Menu | Primary / Secondary | Voce successiva / precedente |
| Main Menu | Interact | Apre il sottomenu selezionato |
| Sottomenu | Primary / Secondary | Scelta successiva / precedente |
| Soundtrack | Jump / Crouch | `−10` / `+10` generi |
| Sottomenu | Interact | Applica la modifica |
| Sottomenu | Reload | Torna al Main Menu |
| Qualunque menu | Tieni Melee 0,5 s | Chiude il menu |

Il dispatcher Menu usa priorità deterministica `Interact → Reload → Primary → Secondary → Jump → Crouch` e attende il rilascio completo prima di accettare un nuovo comando.

## Localizzazione

Tutti gli HUD e i `Small Message` hanno tre varianti indipendenti per viewer:

- **English**
- **Bahasa Indonesia**
- **ไทย**

Le keyword native Workshop restano in inglese; identificatori, subroutine, regole e commenti personalizzati sono mantenuti in **Bahasa Indonesia**.

## Prestazioni e 12 player

Il sistema è progettato per evitare crescita permanente e lavoro inutile con 12 umani attivi:

- pool HUD riutilizzabile `0..11` e cleanup join/leave;
- cache `SlotHUDTerakhir` al posto di sort continui nelle stringhe roster;
- Crouch inspection a **5 Hz**;
- refresh passivi Camera/Revenge/Teleport a **1 Hz**, con refresh immediato sugli input;
- contatore minuti campionato ogni **5 s**;
- Spawn Room cache a **1 Hz**;
- RGB: un solo loop **globale** a 10 Hz;
- camera: un solo raycast nel renderer, senza loop camera server per-frame;
- transizione colore menu event-driven, senza loop colore per-player.

La stabilità reale a 12 client va comunque confermata con la matrice live in [`docs/TEST.md`](docs/TEST.md).

## Compatibilità modalità

Il sorgente non contiene un blocco `settings`: non forza modalità, mappe, roster o composizione squadre. Il contratto principale è pensato per Control, Escort, Hybrid, Push, Flashpoint e Clash; CTF è inoltre gestito dal sistema Teleport tramite `Flag Position`.

La sessione CHILL disabilita scoring e completamento nativi e termina soltanto allo zero del countdown personalizzato, quando esegue un solo `Restart Match`.

## Installazione

1. Apri [`workshop/ruang_irama.workshop`](workshop/ruang_irama.workshop) e copia il contenuto raw.
2. In Overwatch: Partita personalizzata → Crea → Impostazioni → Workshop.
3. Incolla il sorgente.
4. Configura normalmente modalità, mappe e roster della lobby.
5. Configura `Server duration (minutes)`, `Server location (Asia)` e `Performance diagnostics` dalle Workshop Settings.
6. Consulta [`docs/TEST.md`](docs/TEST.md) prima di considerare una build live verificata.

## Struttura repository

```text
workshop/ruang_irama.workshop   sorgente Workshop importabile
README.md                        panoramica dello stato corrente
docs/PROGETTO.md                 architettura corrente
docs/TEST.md                     matrice test statici/live
docs/VALIDAZIONE.md              rapporto del gate corrente
docs/GENERI.md                   catalogo dei 100 generi
docs/SERVER_LOCATIONS.md         26 località Asia
tools/validate_workshop.py       validatore statico
```

## Stato GitHub

- branch operativo: **`main`**;
- workflow permanenti: `validate-workshop.yml` e `maintenance-patch.yml`;
- nessun workflow temporaneo viene mantenuto;
- le patch automatizzate passano unit test, validatore e guardia anti-mutazione workflow prima del commit finale.

## Versione attuale

**0.6.0 — Social Arcade Refresh**

Questa versione documenta lo stato cumulativo corrente: 8 menu, Player Icon, 32 Name Color, Crouch Teleport, Unkillable 1 HP, Hero Voice, feedback idempotente, menu con transizione colore, RGB pastel/neon, localizzazione EN/ID/TH e alleggerimenti per lobby a 12 player.

Lo stato è **static-ready, live-pending**: il repository non può certificare da solo importazione, resa HUD o stabilità runtime nel client Overwatch.
'''
README.write_text(readme, encoding="utf-8")

project = r'''# Note di progetto — versione 0.6.0

## Identità e obiettivo

**CHILL Dedicated Server** è un overlay Workshop sociale/Arcade. Non contiene un blocco `settings` e quindi non impone mappe, modalità, roster o composizione delle squadre. Il countdown CHILL, gli HUD e gli strumenti sociali restano indipendenti dalle normali impostazioni lobby.

Versione corrente: **0.6.0 — Social Arcade Refresh**. Stato: **static-ready, live-pending**.

## Architettura runtime

Gli umani registrati vivono in `Global.PemainManusia`; gli HUD sociali e i relativi ID sono conservati in array paralleli. Gli slot HUD sono limitati a `0..11`, vengono restituiti al pool all'uscita e possono essere riutilizzati dai nuovi join.

La cache `Global.SlotHUDTerakhir` identifica l'ultima riga occupata senza rivalutare continuamente `Sorted Array` dentro gli HUD. Il cleanup leave elimina HUD/IWT, riferimenti Camera/Revenge/Teleport/Inspect e aggiorna gli array in modo allineato.

I dummy bot e i normali bot automatici non ricevono menu o roster sociali; possono però essere target validi per Camera, Crouch e Teleport quando l'entità è disponibile.

## HUD principali

- alto centro: `SERVER LOCATION`, `CHILL DEDICATED SERVER` e countdown;
- sinistra: roster `icona personale + icona eroe + player + N MIN`;
- destra: roster `icona personale + icona eroe + player + genere`;
- diagnostics opzionali sotto l'ultima riga sinistra, solo host.

L'icona personale usa il colore nativo di `Icon String`. Il nome e il resto del campo roster condividono il colore HUD del nome selezionato, limite del normale `Create HUD Text` per una singola sezione di testo.

## Localizzazione

Lingue disponibili per viewer:

| Indice | Lingua |
|---:|---|
| 0 | English |
| 1 | Bahasa Indonesia |
| 2 | ไทย |

HUD, menu, diagnostics e `Small Message` selezionano la lingua tramite `IndeksBahasa`. I 100 nomi internazionali dei generi non vengono tradotti. Keyword native Workshop restano in inglese; nomenclatura personalizzata del sorgente è in Bahasa Indonesia.

## Menu Arcade

Il Main Menu contiene **8 voci**:

| Indice | Menu | Stato |
|---:|---|---|
| 0 | Soundtrack / Musik | 100 generi |
| 1 | Third-Person Camera | OFF / self / target |
| 2 | Name Color | 32 colori |
| 3 | HUD Language | EN / ID / TH |
| 4 | Revenge | debiti kill dirette |
| 5 | Unkillable: 1 HP / Kebal | ON / OFF, non nello Spawn Room |
| 6 | Hero Voice | 5 preset |
| 7 | Player Icon | Nothing + 36 icone |

Melee tenuto 0,5 s apre/chiude il Menu Arcade. Primary e Secondary navigano, Interact entra/applica, Reload torna al Main Menu. Nel Soundtrack, Jump/Crouch saltano di ±10.

I cursori persistono. Interact è idempotente: se il valore scelto è già applicato, non viene generato un nuovo `Small Message`, effetto visivo, suono o riapplicazione inutile.

### Colori menu

Ogni voce usa una palette distinta. Main Menu e sottomenu condividono lo stesso colore principale. `WarnaMenu` è una **Vector RGB** interpolata con `Chase Player Variable Over Time` per circa 0,35 s e poi convertita in `Custom Color(...)` dai renderer. In questo modo la transizione è morbida senza inseguire direttamente un valore `Color` e senza loop periodici per-player.

## Soundtrack

100 generi ordinati da ambient/minimal fino alle categorie più estreme. `IndeksGenre` conserva la scelta applicata e `KursorGenre` la posizione di navigazione. Le liste player mostrano soltanto il genere scelto, senza prefisso `soundtrack:`.

## Name Color

`Global.DaftarWarna` contiene **32 colori**: 20 originali + 12 tonalità aggiuntive pastel/neon. Gli array dei nomi EN/ID/TH hanno la stessa lunghezza. `DaftarWarnaRGB` è la rappresentazione Vector parallela usata esclusivamente dalla transizione menu.

## Player Icon

Menu 7: **37 voci**. Indice 0 = nessuna icona; indici 1..36 = tutte le icone standard disponibili tramite `Icon String`. Default: nessuna icona. La scelta viene inserita prima dell'icona eroe nei due roster e non crea un'icona sopra al player.

## Camera

Fuori menu, Interact tenuto 0,5 s alterna self third-person e first-person. Dal Menu Camera è possibile selezionare OFF, il proprio eroe o altri target validi. La camera usa un solo raycast e non mantiene un loop server per-frame dedicato.

## Revenge

Registra soltanto le kill dirette ricevute da altri umani. Il claim blocca l'identità del target prima dell'azione, decrementa il debito e non crea un debito reciproco per la morte causata dal Revenge stesso. Join/leave e target invalidi vengono ripuliti.

## Unkillable: 1 HP

Menu 5. Quando attivo, applica `Unkillable` e porta la salute a 1; quando la salute torna al massimo viene riportata a 1. La funzione non può essere attivata nello Spawn Room e viene disattivata automaticamente entrando nello spawn.

## Hero Voice

Menu 6: Normal, Low 0.50x, Low 0.75x, High 1.25x, High 1.50x. La scelta viene riapplicata solo quando cambia davvero.

## Crouch: inspection e Teleport

Crouch fuori menu attiva i sistemi associati al tasto. L'inspection mantiene nameplate e testo personalizzato e aggiorna il target a **5 Hz**. Il testo mostra icona eroe, nome e salute; non mostra più la carica Ultimate.

Il Teleport non è più una voce del Main Menu. L'overlay Crouch mantiene un cursore persistente e permette destinazioni Spawn Room, obiettivo/modalità e player validi. Escort/Hybrid usano Payload Position, CTF usa la flag nemica, Push prova un player sull'obiettivo come proxy del robot e usa il fallback obiettivo quando disponibile.

## Jump respawn

Alla morte viene salvata la posizione. Con menu chiuso, Jump calcola una posizione vicina con `Nearest Walkable Position`, esegue `Respawn`, attende un frame e teleporta il player. La correzione è geometrica/camminabile: non garantisce assenza di nemici o pericoli.

## RGB ed effetti

Un solo loop globale a 10 Hz aggiorna `Global.RGB` con un rainbow pastel/neon rallentato; incremento fase +3 su 1530, ciclo completo di circa 51 s. Titolo, timer ed effetti applicazione/ripristino condividono il colore. L'audio degli effetti resta personale al player che esegue l'azione.

## Prestazioni

Ottimizzazioni conservative per 12 player:

- `SlotHUDTerakhir` al posto di sort continui nel roster;
- refresh Camera/Revenge/Teleport passivi a 1 Hz, con refresh immediato sugli input;
- inspection Crouch a 5 Hz;
- `MenitLobi` aggiornato ogni 5 s;
- Spawn Room cache a 1 Hz;
- RGB unico globale;
- nessun loop periodico dedicato alla transizione colore menu;
- cleanup completo degli array e degli ID al leave.

## Contratto modalità e timer

Scoring e completamento built-in sono disabilitati. Il server usa una propria scadenza basata su `Total Time Elapsed`; allo zero esegue una sola richiesta di `Restart Match`. Waiting for Players, Assemble Heroes e Setup vengono saltati rapidamente.

## GitHub e manutenzione

Il repository operativo usa soltanto `main`. I due workflow permanenti sono:

- `.github/workflows/validate-workshop.yml`
- `.github/workflows/maintenance-patch.yml`

Il runner di manutenzione applica `.github/maintenance/patch.py`, esegue i 20 unit test, il validatore, rifiuta mutazioni dei workflow, elimina il patcher e crea il commit finale.

## Limiti della validazione statica

Il validatore non può eseguire il parser/runtime di Overwatch. Restano live-pending: import reale, wrapping Thai, comportamento input simultanei, 12 player concorrenti, join/leave stress, rendering Camera/Crouch e carico server effettivo.
'''
PROJECT.write_text(project, encoding="utf-8")

# Rewrite validation report around the actual current feature set while keeping
# the exact existing Workshop blob marker (source is unchanged in this patch).
old_validation = VALIDATION.read_text(encoding="utf-8")
blob_match = re.search(r"```text\n([0-9a-f]{40})\n```", old_validation)
if not blob_match:
    raise SystemExit("validation blob marker not found")
blob = blob_match.group(1)
rule_count = len(re.findall(r'(?m)^\s*rule\s*\(', SOURCE.read_text(encoding="utf-8")))
validation = f'''# Rapporto di validazione — versione 0.6.0

Data: 2026-08-15

Release: **CHILL Dedicated Server 0.6.0 — Social Arcade Refresh**

Stato: **static-ready, live-pending**.

## Revisione Workshop

Blob Git del sorgente Workshop attualmente documentato:

```text
{blob}
```

La patch 0.6.0 di documentazione non modifica il sorgente Workshop, quindi il marker resta quello dell'ultima modifica funzionale validata.

## Gate statico

Il gate corrente verifica, tra le altre cose:

- 100 generi;
- 3 lingue EN / ID / TH;
- **8 menu Arcade** (`0..7`);
- **32 Name Color** con array EN/ID/TH e Vector RGB parallele;
- **37 Player Icon** (`Nothing` + 36 icone Workshop), default Nothing;
- Menu 5 Unkillable/Kebal 1 HP e Menu 6 Hero Voice;
- Menu 7 Player Icon;
- Teleport gestito dall'overlay Crouch, non dal Main Menu;
- feedback menu idempotente, quindi effetti/messaggi solo su cambi reali;
- transizione colore menu Vector RGB a 0,35 s senza loop per-player;
- RGB globale pastel/neon lento per titolo/timer/effetti;
- pool HUD 0..11, cache ultima riga e cleanup join/leave;
- frequenze bounded: Spawn cache 1 Hz, minuti 5 s, Camera/Revenge/Teleport 1 Hz, inspection 5 Hz;
- nomenclatura personalizzata Bahasa Indonesia e HUD/Small Message localizzati;
- un solo raycast Camera;
- assenza di scoring/vittoria built-in e restart confinato al countdown CHILL;
- nessuna mutazione dei workflow attraverso il runner di manutenzione.

Suite negativa:

```text
Ran 20 tests
OK
```

Validatore atteso:

```text
OK - controlli statici superati
Generi: 100 | Lingue: 3 | Regole: {rule_count} | Raycast camera: 1
```

## Verifiche live ancora obbligatorie

- importazione del sorgente nel client Overwatch;
- apertura e navigazione di tutti gli 8 menu in EN/ID/TH;
- sfumatura colore menu senza sparizioni HUD;
- 32 Name Color e 37 Player Icon;
- Crouch inspection + Teleport con target dinamici;
- Jump respawn;
- Unkillable entrando/uscendo dallo Spawn Room;
- Voice Modifier;
- feedback audiovisivo solo al cambio reale;
- Camera self/target/first-person;
- join/leave ripetuti e riuso slot HUD;
- stress con 12 player attivi e più menu aperti;
- diagnostics host-only e soglie Server Load;
- wrapping/glifi Thai.

## GitHub

Branch operativo previsto: `main`.

Workflow permanenti previsti:

- `validate-workshop.yml`
- `maintenance-patch.yml`

Il file `.github/maintenance/patch.py` deve esistere soltanto durante una manutenzione e viene eliminato dal runner prima del commit finale.

## Decisione

La repository è **static-ready, live-pending**. Il gate statico dimostra coerenza del sorgente e delle invarianti controllate; non sostituisce una sessione reale Overwatch a 12 player.
'''
VALIDATION.write_text(validation, encoding="utf-8")

# TEST.md: update stale version/count claims globally without deleting the
# detailed historical test cases.
tests = TESTS.read_text(encoding="utf-8")
tests = tests.replace("versione 0.5.5", "versione 0.6.0")
tests = tests.replace("release 0.5.5", "release 0.6.0")
tests = tests.replace("sette menu", "otto menu")
tests = tests.replace("Sette menu", "Otto menu")
tests = tests.replace("20 colori", "32 colori")
tests = tests.replace("20 tonalità", "32 tonalità")
tests = tests.replace("0,10 secondi", "0,20 secondi")
tests = tests.replace("0,10 s", "0,20 s")
header = "# Matrice test — CHILL Dedicated Server 0.6.0"
if tests.startswith("# "):
    tests = re.sub(r"^# .*", header, tests, count=1)
else:
    tests = header + "\n\n" + tests
current_note = '''\n\n## Stato corrente 0.6.0\n\nLa matrice corrente deve coprire **8 menu**, 100 generi, **32 Name Color**, **37 Player Icon**, Teleport su Crouch, Jump respawn, transizione colore menu, RGB globale lento, feedback solo su modifiche reali, localizzazione EN/ID/TH e stress join/leave con 12 player. Le sezioni storiche sottostanti restano utili come regressione, ma in caso di conflitto prevale questo stato corrente.\n'''
if "## Stato corrente 0.6.0" not in tests:
    tests = current_note + "\n" + tests
TESTS.write_text(tests, encoding="utf-8")

# Add a repository-doc consistency guard to stop this exact regression.
validator = VALIDATOR.read_text(encoding="utf-8")
check = r'''

def check_repository_docs_current(checks: Checks) -> None:
    version = Path("VERSION").read_text(encoding="utf-8").strip()
    readme = Path("README.md").read_text(encoding="utf-8")
    project = Path("docs/PROGETTO.md").read_text(encoding="utf-8")
    validation = Path("docs/VALIDAZIONE.md").read_text(encoding="utf-8")
    docs = readme + "\n" + project + "\n" + validation

    checks.equal(version, "0.6.0", "VERSION corrente")
    for token in (
        "8 menu", "32", "37", "Player Icon", "Teleport", "0.6.0",
    ):
        checks.require(token in docs, f"documentazione corrente mancante: {token}")
    for stale in (
        "Sette menu", "sette menu", "sei voci", "20 colori per lingua",
        "Il menu principale contiene sei voci", "| `5` | Teleport |",
        "percentuale Ultimate restano rivalutati",
    ):
        checks.require(stale not in docs, f"documentazione obsoleta ancora presente: {stale}")
'''
if "def check_repository_docs_current(" not in validator:
    marker = "\ndef main() -> None:\n"
    if marker not in validator:
        raise SystemExit("validator main marker missing")
    validator = validator.replace(marker, check + marker, 1)
    anchor = "        check_localization_and_indonesian_naming(checks, source, rules)\n"
    if anchor not in validator:
        raise SystemExit("validator docs call anchor missing")
    validator = validator.replace(anchor, anchor + "        check_repository_docs_current(checks)\n", 1)
# Update any hardcoded release text in validator output if present.
validator = validator.replace("v0.5.5", "v0.6.0")
VALIDATOR.write_text(validator, encoding="utf-8")
