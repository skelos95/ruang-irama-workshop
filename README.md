# CHILL Dedicated Server — Overwatch Workshop

Overlay sociale e Arcade per lobby Overwatch 2 **6v6 fino a 12 player**, progettato per convivere con punteggi e obiettivi nativi di Push, Flashpoint, Capture the Flag, Control, Clash, Hybrid, Escort e Assault, mentre la conclusione automatica della partita è governata dal timer CHILL.

Versione: **0.8.1**

Stato: **static-ready / live-pending**

I gate automatici controllano struttura, localizzazione, invarianti del sorgente e compatibilità testuale del copia/incolla. La 0.8.1 ha superato i gate statici ma resta in attesa della nuova regressione nel client, compreso il cambio squadra; i valori diagnostici numerici non forniti non vengono ricostruiti o inventati nel repository.

## Funzioni

- HUD centrale con nome server, countdown e località configurabile, allineato su slot Top/Left/Right deterministici.
- Roster sinistro con icona, eroe, player e minuti; roster destro con genere musicale.
- 14 menu Arcade con preferenze individuali.
- English, Bahasa Indonesia e ไทย selezionabili per viewer.
- Camera in terza persona disponibile a menu aperto o chiuso con Crouch rilasciato; il singolo `Start Camera` condiviso usa posizione e mira per-frame con `Blend Speed 0`, così la camera segue direttamente la traslazione sia in personale sia osservando altri player.
- Resurrect manuale con Jump da morto: rinasce nello stesso punto quando il terreno è presente; dopo una morte nel vuoto usa `Nearest Walkable Position` e sposta lì il player subito dopo `Resurrect`, senza `Respawn`, percorsi Abort o fallback alla Spawn Room.
- Join/leave/cambio squadra protetti da duplicati e handle orfani.
- Ghost Mode / Fly con due toggle indipendenti: attraversamento di pareti e soffitti senza perdere il pavimento, oppure volo 3D relativo alla direzione dello sguardo.
- Un dummy nativo per squadra soltanto con almeno due slot liberi e uno Spawn Point valido: nasce direttamente nella propria spawn, ha respawn massimo di 3 secondi, libera il posto quando la squadra è piena, attraversa pareti e soffitti mantenendo solidi i pavimenti, conserva la collisione con player/bot e riceve normalmente danni e urti. Si muove automaticamente al 20% verso l'umano nemico vivo opt-in più vicino, fermandosi entro 4 m.
- Diagnostica host opzionale per carico, HUD e In-World Text.
- Completion nativa del game mode disabilitata: la partita viene riavviata solo allo scadere del timer CHILL, senza sostituire scoring o obiettivi nativi.

## I 14 menu

| Pagina | Menu | Contenuto |
|---:|---|---|
| 0 | Name Color | 32 colori |
| 1 | Third-Person Camera | OFF, self o target valido |
| 2 | Soundtrack | 100 generi internazionali |
| 3 | HUD Language | English, Bahasa Indonesia, ไทย |
| 4 | Revenge | debiti da kill dirette, consumati solo alla morte completa |
| 5 | Unkillable | OFF, 1 HP curabile, FULL HP |
| 6 | Hero Voice | 5 preset |
| 7 | Player Icon | Nothing + 36 icone |
| 8 | Crouch Travel & Attach | OFF / ON, default OFF |
| 9 | Crouch Privacy | OFF / ON, default OFF |
| 10 | Try Your Luck | roulette a sei esiti |
| 11 | Vote Player | umani, self-vote incluso |
| 12 | Dummy Follow | consente o nega al dummy nemico di seguire il player; default OFF |
| 13 | Ghost Mode / Fly | Wall Phasing e Fly indipendenti; default entrambi OFF |

Gli indici sono Main Menu `-1` e sottomenu `0..13`. Name Color (pagina `0`) parte da bianco e guida sfumature distinte delle altre pagine menu. Dummy Follow è OFF per default: il dummy resta fermo finché almeno un umano avversario non abilita volontariamente l'opt-in; fra i player con preferenza ON sceglie sempre il più vicino e si ferma nuovamente quando non resta alcun target idoneo. I default e i cursori persistono tra chiusura, riapertura e cambio squadra reference-stable; un team switch di un umano già registrato aggiorna subito lo stato dipendente dal Team e chiude/riarma Menu Arcade e overlay Teleport, ma differisce di almeno 0,25 secondi la sostituzione dei due HUD roster finché il player non è nuovamente spawned e vivo. Gli handle vengono distrutti tramite gli array globali canonici e il renderer torna pronto soltanto dopo entrambe le righe. Durante il pending il player esce temporaneamente dai soli filtri Crouch, così un testo nel mondo già aperto viene invalidato e ricreato; Camera, status, effetti e voti attivi non vengono cancellati. Se il motore sostituisce davvero il riferimento e perde le player variables, il recovery usa invece il setup fresco e riapplica i default: è un fallback distinto dal refresh leggero.

La pagina 13 espone due selezioni indipendenti. Nel Main Menu la sua anteprima fa parte dello stesso HUD dinamico delle pagine `0..12`, quindi lo scroll fra `12`, `13` e `0` non ricrea il renderer e non può duplicare Dummy Follow. **Wall Phasing / Ghost** usa `Disable Movement Collision With Environment(..., False)`: pareti e soffitti diventano attraversabili, ma i pavimenti restano sempre solidi. **Fly** imposta la gravità a zero e trasforma il throttle WASD rispetto alla direzione completa dello sguardo: avanti segue il mirino anche verso l'alto o il basso, indietro usa la direzione opposta e gli input laterali permettono lo strafe. Il gate Forward legge la componente Z locale di `Throttle Of`, così riconosce correttamente avanti in qualunque orientamento della mappa; la trasformazione successiva applica il movimento alla visuale 3D. Tenendo avanti, la rampa normale usa `6 m/s²` con un cap Workshop richiesto di `20 m/s`; velocità effettiva e interazione con i limiti orizzontali dell'eroe restano parte del test live. Le azioni continue catturano l'identità del beneficiario con `Evaluate Once(player)` e rivalutano soltanto la sua mira; Try Your Luck: Acceleration mantiene la priorità. Senza input, un impulso esattamente contrario alla velocità residua arresta il player senza deriva o fluttuazione. Alla morte il runtime normalizza accelerazione, throttle, gravità e collisione ambientale, conserva i toggle e li riapplica dopo il Resurrect. I due toggle possono essere combinati; entrambi partono OFF, persistono durante cambio squadra, cambio eroe, morte e Resurrect, ma un vero leave seguito da rejoin esegue setup fresco e li riporta OFF.

Il profilo riconosciuto dal nome visibile esatto `งูแท้` entra con Name Color `Silver Mist` e Player Icon `Poison 2`: sono valori iniziali, quindi il player può modificarli normalmente. Il Player Vibes è invece fissato a `Caladan Brood`; la pagina Soundtrack resta visibile ma in sola lettura e non può cambiare il valore. Questa voce dedicata non amplia il catalogo globale, che resta di 100 generi per tutti gli altri player. Il riconoscimento non usa un identificatore account: un omonimo con lo stesso nome visibile riceve lo stesso profilo e una rinomina ne impedisce l'applicazione. Un cambio squadra leggero conserva anche le eventuali modifiche a colore e icona; il repair lifecycle riasserisce il Vibes bloccato e riapplica i due default soltanto se le player variables risultano davvero azzerate. Un leave seguito da un vero rejoin esegue un nuovo setup e riapplica `Silver Mist`, `Poison 2` e il Vibes bloccato.

La classificazione non prenota uno slot roster finché il nome visibile è `Null` o vuoto: il player viene ritentato quando il token torna disponibile e uno stato transitorio non può consumare erroneamente lo slot 0. Su un vero leave lo slot viene riciclato e ogni `PemainDipilih` che puntava al player uscito viene azzerato prima di ricalcolare il leader, evitando voti e riferimenti obsoleti al successivo join.

In Unkillable, `FULL HP` applica insieme invulnerabilità ai danni, immunità agli urti e assenza di collisione con player/bot. Il passaggio a OFF o 1 HP e l'inizializzazione di una nuova entità ripristinano danni, urti e collisione normali come un'unica transazione; un semplice cambio squadra non ricostruisce lo stato engine. Try Your Luck non cambia modalità o cursore Unkillable e non scrive mai gravità, trasformazione throttle o stato Ghost/Fly: Fly resta quindi attivo durante tutta la roulette. Vision, Acceleration, Self Heal e Hacked mantengono la protezione; Burning la sospende per tutta la propria durata e la ripristina al termine. Lo Skull finale e Revenge sospendono invece temporaneamente lo status per completare la morte; dopo Resurrect il runtime riapplica la modalità selezionata e ricrea l'icona se il motore l'ha eliminata. `FULL HP` resta protetto anche in Spawn Room.

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
| Crouch Travel & Attach | Crouch + Primary / Secondary | pagina successiva / precedente |
| Crouch Travel & Attach | Crouch + Interact | esegue la pagina attiva (Teleport: Spawn Room / Active Objective / Player-Bot, Attach: Player-Bot / Self Elimination); Self Elimination ha cooldown per-player di 3 s |
| Attaccato, Menu Arcade chiuso | Crouch + Reload | sgancia dal player/bot; Reload senza Crouch resta nativo |
| Morto | Jump | `Resurrect` sempre; stesso punto su terreno, oppure `Teleport` alla `Nearest Walkable Position` dopo una morte nel vuoto |

Crouch è il modificatore obbligatorio degli input menu. Per questo `Crouch + Interact` resta riservato al menu, mentre `Interact` senza Crouch può alternare la Camera anche a menu aperto. Un latch condiviso obbliga a rilasciare `Interact` prima che l'altro sistema possa usarlo. Melee e Jump restano azioni normali dell'eroe. Da morto un menu già aperto resta visibile ma congelato: nessun comando Arcade viene eseguito e soltanto Jump attiva `Resurrect`, senza dipendere da Crouch Travel, Camera o Try Your Luck. Un solo raycast verticale decide se serve il recupero dal vuoto: `Resurrect` è incondizionato e, soltanto dopo che il player è tornato vivo, il Teleport usa direttamente `Nearest Walkable Position(Last Of(Position Of(Event Player)))`. Sul terreno il Teleport non viene eseguito. Il percorso non dipende dal validatore delle pagine Travel e non contiene fallback alla Spawn Room, offset casuali, forcing, `Abort` o `Wait`; un raro rifiuto del motore mostra un messaggio e il latch si riapre al rilascio fisico di Jump.

Le cinque pagine dell'overlay Travel usano una terminologia uniforme e specifica in EN/ID/TH: ogni schermata indica pagina, destinazione o posizione, target quando serve e azione. I comandi mostrano sempre i binding effettivi del player. Un solo HUD per-player passa gradualmente da mint a cyan, blu, viola e rosa, con istruzioni pastello e contenuto neon; cursore, handle e azioni restano esclusivi del proprietario.

## Try Your Luck

L'attivazione conserva integralmente Unkillable e avvia una macchina a stati senza loop per-player. Modalità, cursore, flag runtime, status, modificatori e icona non vengono modificati all'avvio. Try Your Luck non scrive gravità né avvia o arresta la trasformazione throttle di Fly. I sei esiti sono:

| Esito | Durata | Effetto |
|---|---:|---|
| Vision | 15 s | mostra icona eroe, nome e salute di bot/dummy e di tutti i player, anche con Privacy ON; Crouch non apre inspection/Teleport |
| Acceleration | 10 s | propulsione automatica 3D guidata dalla mira, senza input direzionali |
| Skull | immediato | unico esito che sospende temporaneamente Unkillable per ottenere la morte completa, con retry per mech, duplicazioni e altre forme intermedie |
| Self Heal | immediato | cura completa soltanto del player che ha attivato la roulette |
| Burning | 10 s | 5% della salute massima ogni 1 s; Unkillable resta sospeso per l'intero effetto e viene ripristinato al termine |
| Hacked | 5 s | stato Hacked |

Durante la roulette il Menu Arcade resta visibile. Al risultato finale viene chiuso soltanto per gli effetti con durata (Vision, Acceleration, Burning e Hacked), così l'HUD dell'effetto può prendere il suo posto; Skull e Self Heal sono immediati e non chiudono il menu. Un'icona Skull comparsa durante i giri non può attivare la morte: soltanto lo Skull finale, con roulette conclusa e deadline armata, può sospendere Unkillable e viene ritentato ogni 0,25 s finché il player non è realmente morto. Una deadline di 5 s libera comunque menu e input se il motore rifiuta la morte, quindi riattiva logicamente la protezione senza cancellare modalità o cursore. Burning usa un bypass temporaneo dedicato: all'avvio rimuove Unkillable e normalizza Damage Received, applica il 5% della Max Health una volta al secondo per 10 secondi senza cambiare modalità o cursore, quindi ripristina la modalità scelta al termine o nel cleanup anticipato.

Stati, messaggi ed effetti sono localizzati nelle tre lingue. Tutte le sei icone della roulette usano `Visible To and Position`: `Visible To` continua a rivalutare il roster, quindi ogni umano le vede anche dopo join/leave, mentre la posizione `Update Every Frame` resta agganciata a occhio e mirino del beneficiario catturato. L'accelerazione usa `Facing Direction Of(Evaluate Once(player))` con `Direction Rate and Max Speed`: l'identità resta stabile, la mira resta dinamica e il movimento parte senza input direzionali. Vision crea un solo IWT per ogni bot, dummy e player umano, anche con Crouch Privacy ON, mostrando icona, nome e salute live; per gli umani usa la copia stabile del nome roster così il cambio squadra non lo svuota. L'avvio di Vision elimina inoltre eventuali handle Crouch già presenti e il leave di un iBot distrugge il proprio IWT senza entrare nel lifecycle umano. Morte, timeout e cambio eroe chiudono lo stato temporaneo ma preservano modalità, cursore e protezione Unkillable; il cambio eroe viene rilevato dal ciclo globale a 10 Hz senza una nuova regola per-player. Dopo una morte, il tick globale riapplica la protezione e ricrea l'icona quando il player torna vivo. Il leave vero rimuove roster e handle; il cambio squadra di un umano già registrato resta invece un refresh leggero.

Le tre targhette IWT di inspection, Vision e Teleport mantengono icona eroe, nome e salute nello stesso testo. La loro intera posizione `Eye Position(Evaluate Once(identity)) + Vector(0, 0.450, 0)` è racchiusa in `Update Every Frame`, con `Evaluate Once` applicato soltanto all'identità del soggetto; `Visible To Position String and Color` lascia invece rivalutare pubblico, posizione, contenuto e colore. In questo modo la targhetta segue il movimento senza trasferirsi a un target successivo e continua ad aggiornare salute, eroe e colore.

Revenge resta invariato: arma una morte forzata ma non modifica subito il debito ed è, insieme allo Skull finale, l'unico percorso autorizzato a sospendere temporaneamente Unkillable. La macchina globale ritenta la kill sul target vivo; soltanto l'evento di morte con `Is Alive == False` e attacker uguale al claimant ricalcola l'indice corrente e sottrae una carica. Una transizione D.Va/Echo, un altro attacker, un timeout, un leave o un cambio squadra non producono un falso successo. Anche posizione e prompt del Resurrect con Jump attendono `Is Alive == False`; dopo il ritorno in vita, la modalità Unkillable selezionata viene riapplicata.

## Runtime 0.8.1

Il lavoro periodico è coordinato da un solo scheduler `Ongoing - Global` a 20 Hz:

- ogni tick: controlli rapidi, morte completa Revenge/Skull e macchina a stati Try Your Luck;
- 10 Hz: lifecycle, RGB e refresh reattivi;
- 1 Hz: countdown, sincronizzazione del timer nativo e cache passive;
- ogni 10 secondi: minuti lobby.

Le scansioni globali non cedono l'esecuzione mentre usano il player e l'indice correnti. Il lifecycle iniziale resta serializzato da un lock globale; un cambio squadra reference-stable non entra nel cleanup/setup pesante e sincronizza Team, UI transitoria e ricreazione differita delle due righe roster. Se una nuova identità arriva mentre il cleanup ritardato occupa ancora l'ultimo slot, il classifier riarma `SudahDiperiksa` prima di uscire e riprova appena lo slot viene liberato, senza restare in uno stato senza uscita; la classificazione degli iBot avviene comunque prima di questo gate. `Ongoing - Each Player` resta riservato a input, latch, classificazione one-shot e rendering realmente individuale; riapplicazione Fly e arresto della deriva sono centralizzati nel ciclo globale a 10 Hz.

Il sorgente mantiene un solo `Loop` e al massimo **7 `Wait`** nominativamente autorizzati per ruolo, durata e quantità. Resurrect e cleanup roster sono atomici; il ritardo di uscita dei dummy dalla Spawn Room usa invece una scadenza timestamp di 1 secondo.

Ogni player mantiene **un solo handle HUD Arcade attivo**. Non esistono preload o pagine nascoste: apertura, chiusura e cambio pagina sono gli unici eventi che ricreano il menu; la navigazione interna aggiorna variabili rivalutate.

## HUD e localizzazione

- Testi runtime, stati, effetti, 37 nomi icona e 26 località sono disponibili in EN/ID/TH.
- I 100 generi, `CHILL`, nomi player ed eroi restano nomi propri universali.
- Identificatori, titoli regola, subroutine e commenti personalizzati restano in Bahasa Indonesia.
- Il file Workshop destinato al client italiano usa la grammatica clipboard `it-IT`: alcuni token cambiano (`variables → variabili`, `rule → regola`, `event → evento`), mentre altri restano identici (`Ongoing - Global`, `Button(Secondary Fire)`).
- La fixture `tests/fixtures/semantic_reference.txt` usa grammatica `en-US` soltanto per il gate semantico e i test: **non è un file da importare nel client**. Il gate canonicalizza entrambi i formati e richiede parità semantica con il vero clipboard `it-IT`, così una modifica funzionale non può essere applicata a una sola copia.
- Ogni `Create HUD Text` usa `Null` nel campo Header; sono ammessi soltanto Subheader/Text e `Small Message`.
- `Big Message` e titoli HUD sono vietati. Gli In-World Text restano ammessi per inspection, Teleport e Vision.
- Menu e liste separano contenuto e comandi con la spaziatura HUD prevista; i promemoria globali descrivono per intero inspection, Menu Arcade e Camera, mentre il blocco sinistro usa `LOBBY & CHILL TIME`.
- La griglia fissa usa dieci handle: Top `0/1/2`, Left `-2/-1/0` e Right `-16/-15/-14/-1`. Il roster sinistro usa `1..12`, quello destro `-13..-2`; lo spaziatore Right `-1` riserva una riga dopo il roster nell'area condivisa con Team Status Indicator/kill feed nativo, da confermare nel client con 1, 6 e 12 player. Menu ed effetti condividono `Top 3`.

Le liste canoniche sono in [`docs/GENERI.md`](docs/GENERI.md) e [`docs/SERVER_LOCATIONS.md`](docs/SERVER_LOCATIONS.md).

## Modalità, timer e Teleport

Punteggio e obiettivi restano responsabilità del game mode nativo, ma `Disable Built-In Game Mode Completion` impedisce alla modalità di terminare automaticamente per i propri criteri. Una volta al secondo il timer nativo viene mantenuto sopra zero e sincronizzato al countdown CHILL; checkpoint o overtime non diventano quindi autorità alternative di fine partita. Quando il countdown CHILL raggiunge zero, una guardia one-shot esegue `Restart Match`.

La destinazione Objective/Flag viene valutata al click:

- Escort e Hybrid: `Payload Position`;
- Capture the Flag: bandiera nemica valida;
- Push: proxy dell'obiettivo con fallback alla posizione obiettivo;
- Flashpoint, Control, Clash e Assault: `Objective Position(Objective Index)`.

I dummy nativi nascono su uno Spawn Point reale della propria squadra, evitando l'origine della mappa, soltanto quando rimangono almeno due slot liberi. Se la squadra diventa piena, il dummy viene rimosso e la guardia di creazione non lo ricrea finché non tornano disponibili due slot, evitando spam di `Create Dummy Bot` e lasciando spazio a 6 umani. Per uscire dalla Spawn Room usano payload per Escort/Hybrid, bandiera nemica per CTF, proxy dell'obiettivo con fallback per Push e obiettivo corrente negli altri casi. Un timestamp stabilizza per 1 secondo lo spawn senza `Wait`; alla scadenza il punto di arrivo viene cercato circa 10 m verso la propria spawn e deve restare almeno 6 m dal target, oltre a passare `Nearest Walkable Position` e il controllo del pavimento. Se non esiste un punto valido, il dummy resta in spawn e riprova. Fuori dalla spawn, il lock limita bot e dummy al 20%; soltanto il dummy nativo usa `Disable Movement Collision With Environment(..., False)`, attraversando pareti e soffitti senza perdere il pavimento, mentre `Enable Movement Collision With Players` mantiene esplicitamente gli urti fisici con player e bot. `Damage Received` e `Knockback Received` restano entrambi al 100%. Il throttle `Forward` rivalutato seleziona esclusivamente l'umano vivo, ancora registrato, della squadra avversaria che ha Dummy Follow ON; fra i target idonei sceglie sempre il più vicino, vale `0` entro 4 m e riparte se il bersaglio si allontana. Opt-out, morte, assenza di target e rimozione fermano o riallineano facing e throttle senza riferimenti obsoleti.

La pagina Player / Bot sceglie un target valido vicino al reticolo e rispetta Crouch Privacy. Privacy è OFF per default; con Privacy ON l'umano non è selezionabile nella Camera custom, inspection, Teleport o Attach e gli osservatori custom già agganciati vengono sganciati. **Vision è l'eccezione intenzionale:** durante i suoi 15 secondi mostra comunque icona, nome e salute di tutti i player, anche privati. Dummy e bot AI rimangono soltanto target passivi e non ricevono menu, HUD o input Arcade. Il Workshop può bloccare le proprie Camere custom, ma non può disabilitare la visuale spettatore nativa riservata a lobby e amministratori.

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

La release 0.8.1 resta **static-ready / live-pending**. I gate repository sono verdi, ma la nuova matrice nel client — inclusi profilo `งูแท้`, cambio squadra leggero, pagina 13 Ghost/Fly, identità/direzione/velocità effettiva del volo, arresto Fly senza input, Self Kill con cooldown 3 s, Resurrect nello stesso punto su terreno e recupero `Nearest Walkable Position` calcolato dalla posizione live dopo il ritorno in vita, Camera personale/watch senza vibrazione, Burning, cinque pagine Crouch Travel & Attach e respawn dummy a 3 secondi — deve ancora essere completata e documentata prima della chiusura della release; non viene dichiarato alcun tag finale per questa versione.
