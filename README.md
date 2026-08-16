# CHILL Dedicated Server — Overwatch Workshop

**CHILL Dedicated Server** è un overlay sociale/Arcade per Overwatch 2 pensato per lobby fino a **12 player attivi**.

La versione **0.6.9** identifica lo stato funzionale e tecnico corrente del repository.

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
- Colori menu diversi e coordinati con i rispettivi sottomenu.
- Transizione colore morbida di circa **0,18 s** tramite Vector RGB.
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
| Sempre | Tieni Melee 0,5 s | Apre/chiude il Menu Arcade |
| Fuori menu | Tieni Interact 0,5 s | Alterna terza / prima persona |
| Fuori menu | Tieni Crouch | Inspection + overlay Teleport |
| Da morto, menu aperto o chiuso | Jump | Respawn vicino al punto di morte |
| Main Menu | Primary / Secondary | Voce successiva / precedente |
| Main Menu | Interact | Apre il sottomenu |
| Sottomenu | Primary / Secondary | Scelta successiva / precedente |
| Soundtrack | Jump / Crouch | `−10` / `+10` generi |
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
- player/bot validi.

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
