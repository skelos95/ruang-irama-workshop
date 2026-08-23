# CHILL Dedicated Server — Overwatch Workshop

Overlay sociale e Arcade per lobby Overwatch 2 **6v6 fino a 12 player**, progettato per convivere con punteggi e obiettivi nativi di Push, Flashpoint, Capture the Flag, Control, Clash, Hybrid, Escort e Assault, mentre la conclusione automatica della partita è governata dal timer CHILL.

Versione: **0.8.0**

Stato: **static-ready / live-pending**

I gate automatici controllano struttura, localizzazione, invarianti del sorgente e compatibilità testuale del copia/incolla. La dicitura `live-ready` verrà usata soltanto dopo import, diagnostica client, matrice modalità e soak test nel client aggiornato.

## Funzioni

- HUD centrale con nome server, countdown e località configurabile, allineato su slot Top/Left/Right deterministici.
- Roster sinistro con icona, eroe, player e minuti; roster destro con genere musicale.
- 12 menu Arcade con preferenze individuali.
- English, Bahasa Indonesia e ไทย selezionabili per viewer.
- Camera in terza persona disponibile a menu aperto o chiuso con Crouch rilasciato; Crouch inspection e Teleport restano fuori dal menu.
- Respawn manuale con Jump da morto.
- Join/leave/cambio squadra protetti da duplicati e handle orfani.
- Un dummy nativo per squadra soltanto con almeno due slot liberi e uno Spawn Point valido: nasce direttamente nella propria spawn, libera il posto quando la squadra è piena, si muove automaticamente al 20% verso l'umano vivo più vicino e mantiene disponibile la capacità per 6 umani per team.
- Diagnostica host opzionale per carico, HUD e In-World Text.
- Completion nativa del game mode disabilitata: la partita viene riavviata solo allo scadere del timer CHILL, senza sostituire scoring o obiettivi nativi.

## I 12 menu

| Pagina | Menu | Contenuto |
|---:|---|---|
| 0 | Soundtrack | 100 generi internazionali |
| 1 | Third-Person Camera | OFF, self o target valido |
| 2 | Name Color | 32 colori |
| 3 | HUD Language | English, Bahasa Indonesia, ไทย |
| 4 | Revenge | debiti da kill dirette ricevute |
| 5 | Unkillable | OFF, 1 HP curabile, FULL HP |
| 6 | Hero Voice | 5 preset |
| 7 | Player Icon | Nothing + 36 icone |
| 8 | Crouch Teleport | OFF / ON, default OFF |
| 9 | Crouch Privacy | OFF / ON, default ON |
| 10 | Try Your Luck | roulette a sei esiti |
| 11 | Vote Player | umani, self-vote incluso |

Gli indici restano invariati: Main Menu `-1`, sottomenu `0..11`. I default e i cursori persistono tra chiusura e riapertura, ma il cambio squadra esegue intenzionalmente un **reset completo** delle preferenze.

## Controlli

| Contesto | Input | Azione |
|---|---|---|
| Vivo | Tieni Melee 0,5 s | apre o chiude il Menu Arcade |
| Menu aperto | Crouch + Primary / Secondary | voce successiva / precedente |
| Main Menu | Crouch + Interact | apre il sottomenu selezionato |
| Sottomenu | Crouch + Interact | applica la scelta |
| Sottomenu | Crouch + Reload | torna al Main Menu |
| Soundtrack | Crouch + Ability 1 / Ability 2 | `+10` / `−10` generi |
| Menu aperto o chiuso, Crouch rilasciato | Tieni Interact 0,5 s | alterna la Camera rapida |
| Menu chiuso | Tieni Crouch | inspection e, se abilitato, overlay Teleport |
| Overlay Teleport | Crouch + Secondary / Primary | cambia pagina / teletrasporta |
| Morto | Jump | respawn vicino al punto di morte |

Crouch è il modificatore obbligatorio degli input menu. Per questo `Crouch + Interact` resta riservato al menu, mentre `Interact` senza Crouch può alternare la Camera anche a menu aperto. Un latch condiviso obbliga a rilasciare `Interact` prima che l'altro sistema possa usarlo. Melee e Jump restano azioni normali dell'eroe. Da morto un menu già aperto resta visibile ma congelato: nessun comando Arcade viene eseguito e soltanto Jump attiva il respawn.

## Try Your Luck

L'attivazione disabilita Unkillable e avvia una macchina a stati senza loop per-player. I sei esiti sono:

| Esito | Durata | Effetto |
|---|---:|---|
| Vision | 15 s | mostra i target consentiti, senza esporre nome o nameplate degli umani con Privacy ON |
| Acceleration | 10 s | propulsione automatica 3D guidata dalla mira, senza input direzionali |
| Skull | immediato | morte del player |
| Team Heal | immediato | cura completa dei player umani della squadra |
| Burning | 10 s | 5% della salute massima al secondo, in tick da 2,5% ogni 0,5 s |
| Hacked | 5 s | stato Hacked |

Durante la roulette il Menu Arcade resta visibile. Al risultato finale viene chiuso soltanto per gli effetti con durata (Vision, Acceleration, Burning e Hacked), così l'HUD dell'effetto può prendere il suo posto; Skull e Team Heal sono immediati e non chiudono il menu.

Stati, messaggi ed effetti sono localizzati nelle tre lingue. Tutte le sei icone della roulette usano `Visible To and Position`: `Visible To` continua a rivalutare il roster, quindi ogni umano le vede anche dopo join/leave, mentre la posizione `Update Every Frame` resta agganciata a occhio e mirino del beneficiario catturato. L'accelerazione usa `Facing Direction Of(Evaluate Once(player))` con `Direction Rate and Max Speed`: l'identità resta stabile, la mira resta dinamica e il movimento parte senza input direzionali. Morte, leave e cambio squadra devono chiudere ogni stato temporaneo senza lasciare effetti o handle.

## Runtime 0.8.0

Il lavoro periodico è coordinato da un solo scheduler `Ongoing - Global` a 20 Hz:

- ogni tick: controlli rapidi e macchina a stati Try Your Luck;
- 10 Hz: lifecycle, RGB e refresh reattivi;
- 1 Hz: countdown e cache passive;
- ogni 10 secondi: minuti lobby.

Le scansioni globali non cedono l'esecuzione mentre usano il player e l'indice correnti. `Ongoing - Each Player` resta riservato a input, latch, classificazione one-shot e rendering realmente individuale.

Il sorgente mantiene un solo `Loop` e al massimo **10 `Wait`** autorizzati. Il ritardo di uscita dei dummy dalla Spawn Room non consuma un `Wait`: una scadenza timestamp di 1 secondo viene valutata dal runtime periodico.

Ogni player mantiene **un solo handle HUD Arcade attivo**. Non esistono preload o pagine nascoste: apertura, chiusura e cambio pagina sono gli unici eventi che ricreano il menu; la navigazione interna aggiorna variabili rivalutate.

## HUD e localizzazione

- Testi runtime, stati, effetti, 37 nomi icona e 26 località sono disponibili in EN/ID/TH.
- I 100 generi, `CHILL`, nomi player ed eroi restano nomi propri universali.
- Identificatori, titoli regola, subroutine e commenti personalizzati restano in Bahasa Indonesia.
- Il file Workshop destinato al client italiano usa la grammatica clipboard `it-IT`: alcuni token cambiano (`variables → variabili`, `rule → regola`, `event → evento`), mentre altri restano identici (`Ongoing - Global`, `Button(Secondary Fire)`).
- La fixture `tests/fixtures/semantic_reference.txt` usa grammatica `en-US` soltanto per il gate semantico e i test: **non è un file da importare nel client**. Il gate canonicalizza entrambi i formati e richiede parità semantica con il vero clipboard `it-IT`, così una modifica funzionale non può essere applicata a una sola copia.
- Ogni `Create HUD Text` usa `Null` nel campo Header; sono ammessi soltanto Subheader/Text e `Small Message`.
- `Big Message` e titoli HUD sono vietati. Gli In-World Text restano ammessi per inspection, Teleport e Vision.
- Menu e liste separano contenuto e comandi con la spaziatura HUD prevista.
- La griglia fissa usa nove handle: Top `0/1/2`, Left `-2/-1/0` e Right `-2/-1/0`; roster e menu occupano rispettivamente gli slot `1..12` e `Top 3`, senza newline di compensazione.

Le liste canoniche sono in [`docs/GENERI.md`](docs/GENERI.md) e [`docs/SERVER_LOCATIONS.md`](docs/SERVER_LOCATIONS.md).

## Modalità, timer e Teleport

Punteggio e obiettivi restano responsabilità del game mode nativo, ma `Disable Built-In Game Mode Completion` impedisce alla modalità di terminare automaticamente per i propri criteri. Quando il countdown CHILL raggiunge zero, una guardia one-shot esegue `Restart Match`.

La destinazione Objective/Flag viene valutata al click:

- Escort e Hybrid: `Payload Position`;
- Capture the Flag: bandiera nemica valida;
- Push: proxy dell'obiettivo con fallback alla posizione obiettivo;
- Flashpoint, Control, Clash e Assault: `Objective Position(Objective Index)`.

I dummy nativi nascono su uno Spawn Point reale della propria squadra, evitando l'origine della mappa, soltanto quando rimangono almeno due slot liberi. Se la squadra diventa piena, il dummy viene rimosso e la guardia di creazione non lo ricrea finché non tornano disponibili due slot, evitando spam di `Create Dummy Bot` e lasciando spazio a 6 umani. Per uscire dalla Spawn Room usano payload per Escort/Hybrid, bandiera nemica per CTF, proxy dell'obiettivo con fallback per Push e obiettivo corrente negli altri casi. Un timestamp stabilizza per 1 secondo lo spawn senza `Wait`; alla scadenza il punto di arrivo viene cercato circa 10 m verso la propria spawn e deve restare almeno 6 m dal target, oltre a passare `Nearest Walkable Position` e il controllo del pavimento. Se non esiste un punto valido, il dummy resta in spawn e riprova. Fuori dalla spawn, il lock limita bot e dummy al 20%; il dummy riceve inoltre un throttle `Forward` rivalutato che lo fa avanzare automaticamente verso l'umano vivo più vicino e viene fermato su morte, assenza target o rimozione.

La pagina All Players sceglie un target valido vicino al reticolo e rispetta Crouch Privacy. Privacy è ON per default: un umano privato non può essere scelto né mantenuto come target della Camera custom e Vision/inspection non ne mostrano nome o nameplate. Dummy e bot AI rimangono soltanto target passivi e non ricevono menu, HUD o input Arcade.

## Importazione tramite copia/incolla

Nel repository esiste **un solo file `.workshop` destinato all'utente**:

[`workshop/ruang_irama.it-IT.workshop`](workshop/ruang_irama.it-IT.workshop)

Con Overwatch impostato in italiano, apri la vista Raw di quel file e copia tutto, dalla prima riga `variabili` fino alla graffa finale. Il parser clipboard è sensibile alla localizzazione e alcuni literal contestuali devono restare nella forma effettivamente accettata dal client; per questo il file pubblicato viene mantenuto e testato direttamente come sorgente `it-IT`.

Il vecchio `workshop/ruang_irama.workshop` e il relativo manifest non fanno più parte del repository. La grammatica `en-US` necessaria ai test semantici vive esclusivamente nella fixture interna `tests/fixtures/semantic_reference.txt`, che non deve essere copiata in Overwatch.

La guida completa è in [`docs/IMPORTAZIONE_ITALIANO.md`](docs/IMPORTAZIONE_ITALIANO.md).

Dallo screenshot client del 21 agosto 2026 i limiti da verificare dopo il paste sono:

- Element Count: massimo `32768`;
- Largest Rule: `< 98 KB`;
- combinazioni eroe/modello: `12`;
- dummy bot extra-slot: `0` nella configurazione mostrata.

I valori `0 elementi` e `0 KB` dello screenshot con Workshop vuoto non misurano il progetto. Element Count e Largest Rule compilato devono essere letti nuovamente dopo un import riuscito.

## Validazione

Da eseguire dalla radice del repository, senza dipendenze Python esterne:

```powershell
python -m unittest discover -s tests -p 'test_*.py'
python tools/validate_workshop.py
python tools/check_clipboard_import.py workshop/ruang_irama.it-IT.workshop --language it-IT
```

`check_clipboard_import.py` verifica il formato testuale del paste (UTF-8/BOM, delimitatori, grammatica strutturale, caratteri invisibili e dimensione sorgente delle rule) ma non sostituisce la Diagnostica script del client. Il checker supporta anche il profilo `en-US` usato dalla fixture interna; per Largest Rule mantiene un target statico conservativo di `<= 80 KB` di testo per rule rispetto al limite client `< 98 KB`.

Il workflow permanente [`.github/workflows/validate-workshop.yml`](.github/workflows/validate-workshop.yml) esegue la suite `unittest` e il validatore semantico su push e pull request; i test del preflight clipboard sono inclusi automaticamente nella suite. L'allowlist di `.github` ammette soltanto questo workflow: marker, trigger, patcher e automazioni one-shot sono vietati, così nessun workflow può modificare o committare automaticamente il repository.

Documentazione operativa:

- [`docs/PROGETTO.md`](docs/PROGETTO.md) — architettura e invarianti;
- [`docs/TEST.md`](docs/TEST.md) — matrice statica e live;
- [`docs/VALIDAZIONE.md`](docs/VALIDAZIONE.md) — copertura del gate e stato release;
- [`docs/IMPORTAZIONE_ITALIANO.md`](docs/IMPORTAZIONE_ITALIANO.md) — copia/incolla con client italiano e diagnostica;
- [`CHANGELOG.md`](CHANGELOG.md) — cronologia essenziale.

## Contesto client agosto 2026

La [patch del 19 agosto 2026](https://overwatch.blizzard.com/en-us/news/patch-notes/live/2026/08/#patch-2026-08-19) richiede un nuovo import e rende inutilizzabili i replay precedenti, pur senza dichiarare modifiche Workshop. La matrice comprende inoltre D.Mon, il nuovo Team Status Indicator e le modifiche a Busan, Eichenwalde e Paraíso della [patch dell'11 agosto 2026](https://overwatch.blizzard.com/en-us/news/patch-notes/live/2026/08/#patch-2026-08-11).

Finché i risultati reali della Diagnostica script e gli altri test live non sono registrati, la release resta **static-ready / live-pending**.
