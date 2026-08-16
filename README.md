# CHILL Dedicated Server — Overwatch Workshop

**CHILL Dedicated Server** è un overlay sociale/Arcade per Overwatch 2 pensato per lobby fino a **12 player attivi**.

La versione **0.6.17** identifica lo stato funzionale e tecnico corrente del repository.

## Funzioni principali

- HUD centrale con `CHILL DEDICATED SERVER`, countdown personalizzato e `SERVER LOCATION` configurabile.
- Due roster sociali:
  - sinistra: icona personale + icona eroe + player + `N MIN`;
  - destra: icona personale + icona eroe + player + genere musicale scelto.
- **12 menu Arcade**:
  1. `0 - Soundtrack` — 100 generi.
  2. `1 - Third-Person Camera` — OFF, self o spectate.
  3. `2 - Name Color` — **32 colori**.
  4. `3 - HUD Language` — English / Bahasa Indonesia / ไทย.
  5. `4 - Revenge` — debiti basati sulle kill dirette ricevute.
  6. `5 - Unkillable` — OFF / 1 HP / FULL HP; solo 1 HP non è disponibile nello Spawn Room.
  7. `6 - Hero Voice` — 5 preset vocali.
  8. `7 - Player Icon` — **37 voci**: `Nothing` + 36 icone Workshop standard.
  9. `8 - Crouch Teleport` — abilita/disabilita l’HUD Teleport su Crouch; default OFF.
  10. `9 - Crouch Privacy` — quando ON nasconde completamente icona/nome/salute ai nemici durante Crouch inspection; i compagni vedono sempre tutto; default OFF.
  11. `10 - Try Your Luck` — roulette 50/50 con menu bloccato in pagina 10: protezione FULL HP temporanea; verde ripristina l'ultima modalità Unkillable scelta, rosso porta la velocità del player a 0 con Light Shaft + Ring RGB in chiusura e lo uccide dopo 3 secondi, senza forzare la posizione.
  12. `11 - Vote Player` — voto verso qualsiasi umano, incluso se stessi; bot esclusi.
- Player Icon predefinita: **Nothing**.
- Tutti i cursori menu restano memorizzati tra chiusura e riapertura.
- Ogni menu, tranne Name Color, ha una **tonalità identitaria unica**; Name Color segue invece il colore selezionato.
- Tutti i passaggi colore restano sfumati con transizione morbida di circa **0,18 s** tramite Vector RGB.
- RGB globale pastel/neon lento per titolo, timer ed effetti visivi.
- Feedback `Small Message` + visuale + audio soltanto quando una modifica cambia davvero; premere `Interact` sulla stessa scelta non ripete il feedback.
- Crouch inspection con icona eroe, nome e salute; la percentuale Ultimate non viene mostrata.
- Teleport spostato fuori dal Main Menu: viene gestito tramite **Crouch**.
- Jump da morto per respawn vicino al punto di morte tramite `Nearest Walkable Position`.
- Camera rapida fuori menu con `Interact` tenuto per 0,5 s.
- Diagnostica prestazionale opzionale host-only.

## Menu Arcade attuale

| # | Menu | Contenuto |
|---:|---|---|
| 0 | Soundtrack | 100 generi |
| 1 | Third-Person Camera | OFF / self / target |
| 2 | Name Color | 32 colori |
| 3 | HUD Language | EN / ID / TH |
| 4 | Revenge | debiti kill dirette |
| 5 | Unkillable | OFF / 1 HP / FULL HP |
| 6 | Hero Voice | 5 preset |
| 7 | Player Icon | Nothing + 36 icone |
| 8 | Crouch Teleport | OFF / ON, default OFF |
| 9 | Crouch Privacy | OFF / ON; ON nasconde tutto ai nemici, alleati sempre visibili |
| 10 | Try Your Luck | 50/50; menu bloccato, FULL HP temporaneo, verde ripristina Unkillable, rosso = velocità 0 + Ring/Light Shaft + morte |
| 11 | Vote Player | umani + conteggio voti, self-vote consentito |

Il Teleport resta un overlay associato a Crouch; **Menu 8** decide soltanto se quell’overlay può aprirsi.

## Controlli

| Contesto | Input | Azione |
|---|---|---|
| Sempre | Tieni Melee 0,5 s | Apre/chiude il Menu Arcade; il normale attacco Melee resta utilizzabile a menu aperto |
| Fuori menu | Tieni Interact 0,5 s | Alterna terza / prima persona |
| Fuori menu | Tieni Crouch | Inspection + overlay Teleport |
| Da morto, menu aperto o chiuso | Jump | Respawn vicino al punto di morte |
| Main Menu | Primary / Secondary | Voce successiva / precedente |
| Main Menu | Interact | Apre il sottomenu |
| Sottomenu | Primary / Secondary | Scelta successiva / precedente |
| Soundtrack | Ability 1 / Ability 2 | `+10` / `−10` generi |
| Sottomenu | Interact | Applica la scelta |
| Sottomenu | Reload | Torna al Main Menu |

## Localizzazione

Tutti gli HUD principali e i `Small Message` sono gestiti in tre lingue indipendenti per viewer:

- **English**
- **Bahasa Indonesia**
- **ไทย**

Le keyword native Workshop restano in inglese; identificatori, subroutine, titoli regole e commenti personalizzati sono mantenuti in Bahasa Indonesia.

## Prestazioni e 12 player

Il runtime è stato alleggerito per una lobby piena:

- pool HUD riutilizzabile `0..11`;
- cleanup completo join/leave;
- cache `SlotHUDTerakhir` per evitare sort continui nei roster;
- inspection Crouch a **4 Hz**;
- refresh passivi Camera/Revenge/Teleport a **1 Hz**;
- contatore minuti ogni **10 s**;
- cache Spawn Room a **1 Hz**;
- un solo loop RGB globale a 8 Hz;
- un solo raycast Camera;
- nessun loop per-player dedicato alla transizione colore menu.

## Teleport Crouch

L'overlay Teleport include:

- Spawn Room registrata;
- obiettivo della modalità quando disponibile;
- player/bot validi, esclusi i player con **Crouch Privacy ON**.

Escort/Hybrid usano `Payload Position`, CTF usa la flag nemica, Push prova un player sull'obiettivo come proxy del robot e usa il fallback obiettivo quando disponibile.

## Name Color

Sono disponibili **32 tonalità**. I primi 20 colori originali sono stati mantenuti e sono state aggiunte 12 tonalità pastel/neon. Gli array EN/ID/TH e la tabella Vector RGB sono allineati.

## Player Icon

Il Menu 7 contiene **37 voci**:

- indice 0: `Nothing`;
- indici 1..36: tutte le icone standard disponibili tramite `Icon String`.

L'icona mantiene il proprio colore nativo e viene mostrata prima dell'icona eroe nei due roster. Non viene creata alcuna icona sopra il player.

## GitHub

- branch operativo: `main`;
- workflow permanenti: `validate-workshop.yml` e `maintenance-patch.yml`;
- nessun workflow temporaneo permanente;
- test statici: 33 unit test + validatore Workshop.

## Stato validazione

Il repository è **static-ready, live-pending**. I controlli statici non possono certificare importazione reale, rendering HUD, input simultanei o stabilità effettiva con 12 client Overwatch.

Per i dettagli tecnici consulta:

- [`docs/PROGETTO.md`](docs/PROGETTO.md)
- [`docs/TEST.md`](docs/TEST.md)
- [`docs/VALIDAZIONE.md`](docs/VALIDAZIONE.md)

### Menu 5 — Unkillable

Tre modalità: **OFF**, **1 HP** e **FULL HP**. FULL HP usa Damage Received 0% e mantiene la salute al massimo. Gli indicatori sono pubblici e distinti: **1 HP usa Warning rosso**, mentre **FULL HP usa Halo RGB**. Passando da una modalità all'altra l'icona viene sostituita.

**Correzione Spawn Room:** FULL HP resta attiva nella Spawn Room. Solo 1 HP viene disattivata automaticamente. Il passaggio 1 HP → FULL HP porta subito la salute al massimo e Damage Received a 0%; FULL HP → 1 HP ripristina Damage Received a 100% e porta la salute a 1.

**Feedback visivo:** i feedback delle impostazioni non riproducono più suoni. `EfekTerapkan` e `EfekPulihkan` usano esclusivamente `Ring Explosion` con `Global.RGB`.


### Try Your Luck 0.6.5

Durante la roulette il Menu Arcade **resta aperto sulla pagina 10** e il dispatcher degli input viene bloccato finché `KartuNasibAktif` torna `False`. All'attivazione viene applicato temporaneamente **Unkillable FULL HP** senza modificare `ModeKebalTerakhir`, che conserva l'ultima scelta esplicita del player.

- **Verde:** ripristina OFF / 1 HP / FULL HP in base a `ModeKebalTerakhir`; la restrizione 1 HP nello Spawn Room resta invariata.
- **Rosso:** porta la protezione runtime a OFF, imposta solo la velocità di movimento a 0, congela il colore corrente di `Global.RGB`, crea `Light Shaft` e `Ring` sul pavimento e riduce gradualmente il raggio durante il countdown 3-2-1 prima della morte; la posizione non viene forzata e il knockback resta normale.
- Se il player muore prima della fine della roulette, la funzione si resetta subito, ripristina la modalità Unkillable ricordata e aggiorna la pagina 10 senza chiudere il Menu Arcade. Leave e cambio squadra continuano a fare cleanup completo degli effetti.
- Lo status della pagina 10 è dinamico: `READY` → `ROLLING` → `RED/GREEN` (con equivalenti ID/TH).

Camera e Teleport ora escludono dai rispettivi elenchi target entità non esistenti, non spawnate o morte. Il Teleport obiettivo usa inoltre la stessa sorgente della sua esecuzione: Payload per Escort/Hybrid, flag nemica valida per CTF, proxy/fallback per Push e `Objective Position` negli altri casi.


### Audit 0.6.3

La manutenzione 0.6.3 rimuove stato Workshop non più usato, unifica il cleanup Menu 10 nel Player Left, verifica automaticamente che ogni variabile player dichiarata sia inizializzata in `SiapkanPemain`, controlla riferimenti stale e titoli regola duplicati, localizza i minuti roster EN/ID/TH e rende il cambio target della camera diretto senza `Stop Camera` intermedio. Il repository mantiene un solo branch operativo (`main`) e soltanto i due workflow permanenti.


### Nomenclatura 0.6.3

Variabili, subroutine, titoli regola e commenti personalizzati sono controllati contro residui linguistici legacy. Restano in inglese soltanto keyword/azioni native Workshop e i contenuti HUD del ramo English.


### Team switch 0.6.3

`Player Joined Match` può essere generato anche da un cambio squadra. Se il player è già presente nel roster, `BersihkanPemain` esegue lo stesso cleanup del Player Left prima di `SiapkanPemain`: HUD, slot, Menu 10, camera, input, Unkillable, riferimenti e voto vengono azzerati. La regola di registrazione ha inoltre una guardia `Array Contains(Global.PemainManusia, Event Player)` che impedisce un secondo append della stessa entità. Ogni player mantiene un solo `PemainDipilih`; cambiando scelta il valore precedente viene prima impostato a `Null`, poi viene assegnato il nuovo target e `HitungPilihan` ricalcola i totali.


### Respawn Jump 0.6.6

Da morto, `Jump` esegue il respawn vicino al punto di morte anche se il Menu Arcade è già aperto. Il menu non viene chiuso dal respawn e la regola `12f - Bangkit Lompat` non dipende più da `MenuTerbuka == False`.


### Input da morto 0.6.7

Quando il player muore, un Menu Arcade già aperto resta visibile ma viene congelato: Primary Fire, Secondary Fire, Interact, Reload, Crouch e gli altri input Arcade non eseguono azioni. Anche Crouch inspection e Crouch Teleport restano inattivi. L'unico input custom attivo da morto è `Jump`, usato esclusivamente dal respawn manuale vicino al punto di morte. Dopo il respawn il menu rimane aperto e torna utilizzabile.


### Menu fluido 0.6.8

La navigazione pura riusa gli HUD con stringhe/colori rivalutati invece di distruggerli e ricrearli a ogni pressione. Primary/Secondary aggiornano cursore e transizione colore; Jump/Crouch nel Soundtrack aggiornano direttamente il cursore. Interact mantiene i redraw necessari all'applicazione dello stato, ma non contiene più i due `Wait(0.016)` della Camera. Anche Crouch Teleport elimina il frame di release e i redraw per ogni step. La transizione colore passa da circa 0,35 s a 0,18 s. Il hold Melee da 0,5 s resta intenzionale.


### HUD persistente 0.6.9

Il Menu Arcade mantiene un unico HUD durante tutta l'apertura. `Interact` e `Reload` cambiano pagina modificando `HalamanMenu`, senza distruggere e ricreare l'HUD. I renderer legacy restano definiti solo come struttura di compatibilità/validazione e non sono chiamati dal router runtime.


### Riduzione limiti Workshop 0.6.10

La 0.6.9 aveva reso `GambarMenu` un HUD monolitico con tutte le 13 viste duplicate nella stessa regola; il client ha misurato **124 KB**, oltre il limite Workshop di **98 KB**, con **25.654 elementi** totali. La 0.6.10 elimina quella duplicazione: `GambarMenu` torna a essere un router piccolo e inizializza una volta, per ogni apertura, i 13 renderer già esistenti. Ogni HUD è visibile solo quando `MenuTerbuka` e `HalamanMenu` corrispondono alla sua pagina, quindi `Interact`/`Reload` cambiano pagina senza Destroy/Create. Alla chiusura tutti i 13 HUD vengono distrutti e l'array viene svuotato.


### Apertura Melee immediata dopo 0,5 s — 0.6.11

Il `Wait(0.500, Abort When False)` resta invariato: la soglia di hold non viene accorciata. Il ritardo extra osservato live dipendeva dal fatto che allo scadere dei 0,5 s `GambarMenu` creava tutte le 13 pagine HUD in sequenza. Ora il router usa una cache lazy (`HalamanHudMenuArcade`): all'apertura crea soltanto il Main Menu; ogni submenu viene creato soltanto al primo accesso e poi riutilizzato fino alla chiusura. `Reload` verso il Main e i ritorni a pagine già visitate non ricreano HUD.


### Controlli menu e privacy Teleport 0.6.12

Con il Menu Arcade aperto, **Melee e Jump restano azioni normali dell'eroe**: Melee può comunque chiudere il menu se viene tenuto per 0,5 s, mentre Jump non viene più intercettato dal dispatcher. Nel Soundtrack i salti rapidi diventano **Ability 1 = +10** e **Ability 2 = −10**; le due abilità reali restano bloccate finché il menu è aperto, quindi la pressione agisce soltanto sul cursore musicale. `SegarkanTargetTeleportasi` filtra inoltre qualunque player con `PrivasiInspeksiAktif == True`: il suo nome non appare nel Crouch Teleport e un target diventato privato prima della conferma viene rifiutato perché non è più presente nella lista aggiornata.


### Palette menu unica 0.6.13

Ogni voce Arcade ha una tonalità dedicata: Soundtrack ciano, Camera blu, Language viola, Revenge rosso, Unkillable arancio, Hero Voice magenta, Player Icon lime, Crouch Teleport verde, Crouch Privacy teal, Try Your Luck oro e Vote Player rosa. **Name Color resta dinamico** e segue `DaftarWarnaRGB[KursorWarna]`. Tutti i passaggi continuano a usare il chase morbido da 0,18 s.


### Preload progressivo dei sottomenu 0.6.14

Il Main Menu continua ad apparire appena termina il hold Melee da 0,5 s. Subito dopo, una regola separata prepara in background le altre 12 pagine **una sola per frame** (`Wait(0.016, Abort When False)`), mentre restano invisibili grazie alla visibilità dinamica già esistente. In questo modo il primo accesso a un sottomenu non deve più creare il relativo HUD nello stesso istante in cui viene mostrato. Il router lazy rimane come fallback se il player riesce ad aprire una pagina prima che il preload l'abbia preparata. Chiudendo il menu il preload si interrompe automaticamente e il cleanup continua a distruggere soltanto gli HUD effettivamente creati.


### HUD edge-triggered 0.6.15
Il Main Menu viene creato invisibile mentre inizia il hold Melee e a 0,5 s cambia solo la visibilità. I sottomenu vengono preparati quando sono evidenziati. Nessuna regola che esegue `Create HUD Text` contiene `Wait` o `Loop`. Anche gli HUD sociali del giocatore sono separati dalla classificazione umano/bot.


### Protezione cambio team 0.6.16

Il cambio team durante una partita non può più riattivare in modo continuo le regole globali che saltano Assemble Heroes/Setup. Entrambe sono ora one-shot, valide solo prima che la partita sia in corso e riarmate soltanto prima di un vero `Restart Match`. La creazione dei due HUD sociali resta senza `Wait` e senza `Loop`, ma usa un latch per-player impostato **prima** del primo `Create HUD Text` e richiede uno spawn stabile. La classificazione umano/bot abbandona e ritenta se il player entra in una transizione di team durante i due probe da 0,016 s.


### Cambio team ripetuto 0.6.17

Il lifecycle player è ora serializzato. `01b` resta esclusivamente un bootstrap per i player già presenti quando lo script parte e non può più riattivarsi quando `BersihkanPemain` porta temporaneamente `SudahSiap` a false. `SiapkanPemain` pubblica `SudahSiap = True` soltanto come **ultima azione**, dopo avere completato tutti i reset; la classificazione 02 richiede inoltre che il lock lifecycle sia libero. È stato aggiunto anche un latch one-shot a `Start Game Mode`, l'ultima azione globale di fase che poteva ancora essere richiesta più volte.
