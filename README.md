# CHILL Dedicated Server — Overwatch Workshop

Overlay sociale e Arcade per lobby Overwatch 2 **6v6 fino a 12 player**, dedicato alla sola **Schermaglia** sulle mappe standard, con durata governata dal timer CHILL. La rotazione scelta esclude le mappe Workshop (Isola, Camera e simili); la selezione mappe resta nelle impostazioni della lobby.

Versione: **0.8.1**

Stato: **live-ready** (release storica 0.8.1).

**Revisione del 27 settembre 2026:** eliminati i percorsi specifici delle altre modalità e limitati creazione/teletrasporto automatico dei dummy alla Schermaglia. Conservato il percorso di destinazione già usato in Schermaglia, con ricerca geometrica, retry e cleanup. Incluse la pulizia delle regole duplicate e le istruzioni HUD abbreviate EN/ID/TH. Le note datate sotto descrivono le revisioni precedenti.

**Ripristino del 25 settembre 2026:** ritirata la revisione Friendly della PR #76 dopo la segnalazione di crash sistematico al primo cambio squadra, anche senza aprire menu. Il sorgente Workshop, la fixture semantica e i controlli tornano esattamente alla revisione `2529608` precedente alla PR. Rimossi quindi la nuova cache Arcade, il suo aggiornamento periodico, il cooldown cosmetico introdotto insieme e il rallentamento automatico. Restano tutte le modifiche precedenti, inclusi dummy limitati a Schermaglia/CTF, Host RGB e profilo `งูแรร์`. La causa nativa non è stata isolata; il passaggio dei test automatici della PR #76 non aveva rilevato la regressione. Dopo il nuovo import, verificare il cambio squadra in una nuova lobby.

**Revisione del 15 settembre 2026:** ridotti i picchi di creazione delle targhette e delle icone roulette; la diagnostica lascia disabilitata la registrazione Inspector. Rimossa la registrazione dei minuti individuali e il vecchio roster: Player Vibes è l’unica lista e si trova a sinistra; a destra compare Host con icona eroe e nome del player corrente. Rimosse le istruzioni che modificavano le collisioni dei dummy, lasciando quelle native senza riapplicarle. Queste modifiche richiedono una nuova prova con lobby piena e ricambio dei player: i test automatici e i riscontri live precedenti non certificano la scomparsa dei crash.

I gate automatici controllano struttura, localizzazione, invarianti del sorgente e compatibilità testuale del copia/incolla. La regressione live della 0.8.1 è stata completata sul client aggiornato ad agosto 2026, includendo team-switch con cleanup/setup completo, profilo `งูแท้`, pagina 13 Ghost/Fly, Crouch Travel & Attach e diagnostica. I valori numerici non presenti nei report restano non ricostruiti nel repository.

La release pubblicata [`v0.8.1`](https://github.com/skelos95/ruang-irama-workshop/releases/tag/v0.8.1) identifica il commit `14ad403babb56c58f9b55f8ebe902f13b18cd02c`. Al controllo del 7 settembre 2026, `main` era al commit `687197d67619f89a0f034cafaa67857d00bf78a0`, sette commit successivi, pur mantenendo `VERSION = 0.8.1`. I riscontri live storici non certificano automaticamente ogni revisione successiva: per la build effettivamente importata occorre registrare SHA, build client e risultati della matrice in [`docs/TEST.md`](docs/TEST.md), compresi rotazione dei player e contatori dopo il cleanup.

## Funzioni

- HUD centrale con nome server, countdown e località configurabile, allineato su slot Top/Left/Right deterministici; `LOCATION` usa un ambra neon distinto dal cyan di `PLAYER VIBES`.
- Riga Host a destra nel campo Text, con una riga vuota sopra e sotto e lo stesso RGB animato del titolo.
- Unico roster `PLAYER VIBES` a sinistra con player e genere musicale, senza conteggio dei minuti individuali.
- 14 menu Arcade con preferenze individuali.
- English, Bahasa Indonesia e ไทย selezionabili per viewer.
- Camera in terza persona disponibile a menu aperto o chiuso con Crouch rilasciato; il singolo `Start Camera` condiviso usa posizione e mira per-frame con `Blend Speed 0`, così la camera segue direttamente la traslazione sia in personale sia osservando altri player.
- Resurrect manuale con Jump da morto: rinasce nello stesso punto quando il terreno è presente; dopo una morte nel vuoto usa `Nearest Walkable Position` e sposta lì il player subito dopo `Resurrect`, senza `Respawn`, percorsi Abort o fallback alla Spawn Room.
- Join/leave/cambio squadra protetti da duplicati e handle orfani.
- Ghost Mode / Fly con due toggle indipendenti: attraversamento di pareti e soffitti senza perdere il pavimento, oppure volo 3D relativo alla direzione dello sguardo con rampa Forward dal 100% al 500% in 25 secondi.
- Dummy automatici solo in Schermaglia: uno per squadra soltanto con almeno due slot liberi e uno Spawn Point valido. Nasce direttamente nella propria spawn, ha respawn massimo di 3 secondi, libera il posto quando la squadra è piena, mantiene tutte le collisioni con ambiente e player/bot e riceve normalmente danni e urti. Si muove automaticamente al 20% verso l'umano nemico vivo opt-in più vicino, fermandosi entro 4 m.
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

Gli indici sono Main Menu `-1` e sottomenu `0..13`. Name Color (pagina `0`) parte da bianco e guida sfumature distinte delle altre pagine menu. Dummy Follow è OFF per default: il dummy resta fermo finché almeno un umano avversario non abilita volontariamente l'opt-in; fra i player con preferenza ON sceglie sempre il più vicino e si ferma nuovamente quando non resta alcun target idoneo. I default e i cursori persistono tra chiusura, riapertura, cambio eroe, morte e Resurrect. Un cambio squadra di un umano già registrato apre invece una quarantena leggera nella regola individuale `01a`, con stabilizzazione di 0,5 s. Dopo team e spawn stabili, `01b` esegue `TenangkanPemain`, `BersihkanPemain` se l'identità è ancora nel roster e `SiapkanPemain`, nel contesto del player e sotto il lock lifecycle. Slot e handle precedenti vengono liberati prima della nuova registrazione: preferenze, cursori e stati temporanei tornano quindi al setup iniziale, come su leave/rejoin.

La pagina 13 espone due selezioni indipendenti. Nel Main Menu la sua anteprima fa parte dello stesso HUD dinamico delle pagine `0..12`, quindi lo scroll fra `12`, `13` e `0` non ricrea il renderer e non può duplicare Dummy Follow. **Wall Phasing / Ghost** usa `Disable Movement Collision With Environment(..., False)`: pareti e soffitti diventano attraversabili, ma i pavimenti restano sempre solidi.

**Fly** usa un motore 3D esplicito a 20 Hz: nel volo normale gravità e `Move Speed` nativo sono a zero, mentre gli impulsi impostano la velocità richiesta dallo sguardo e dagli input grezzi. Solo l'input avanti segue il mirino anche verso l'alto o il basso; indietro e strafe restano invece orizzontali rispetto alla rotazione dell'eroe. Non viene usato `Start Transforming Throttle`. Il gate Forward richiede componente Z locale di `Throttle Of` maggiore di `0.050` e componente X compresa fra `-0.050` e `0.050`, così riconosce l'avanti puro in qualunque orientamento della mappa. Il `100%` Fly è una baseline uniforme di **5,5 m/s**, non una misura della velocità nativa specifica di ogni eroe o buff. Mantenendo Forward puro cresce linearmente di `16` punti percentuali al secondo fino al `500%` (**27,5 m/s**) dopo 25 secondi. Rilasciare Forward oppure aggiungere destra/sinistra o usare indietro riporta la rampa al `100%`; con nessun input la velocità richiesta è zero. L'intensità analogica viene preservata e le diagonali non superano il modulo dell'input pieno.

Il testo della riga Fly insegna la progressione in EN/ID/TH: `LOOK TO STEER | HOLD FORWARD: 100% > 500% IN 25s`, `ARAHKAN PANDANGAN | TAHAN MAJU: 100% > 500% DALAM 25dtk` e `บังคับด้วยมุมมอง | กดเดินหน้าค้าง: 100% > 500% ใน 25วิ`. Timer, percentuale, direzione e correzione di velocità appartengono a ciascun player. A ogni tick l'impulso corregge la differenza fra velocità desiderata e corrente; senza input annulla quindi la deriva senza forzare la posizione. Try Your Luck: Acceleration mantiene la priorità totale per l'intera finestra, senza impulsi o modifiche di velocità del motore Fly; alla scadenza la rampa riparte fresca. OFF, morte, cambio eroe e cambio squadra ripuliscono lo stato fisico transitorio; il ritorno in vita riapplica le modalità scelte. I toggle partono entrambi OFF e persistono durante cambio eroe, morte e Resurrect, ma cambio squadra e leave/rejoin eseguono cleanup/setup completo e li riportano OFF. La revisione con strafe orizzontale corretto e reset squadra è stata verificata nella regressione client 0.8.1: procedura e matrice in [`docs/TEST.md`](docs/TEST.md), motivazione tecnica e fonti in [`docs/PROGETTO.md`](docs/PROGETTO.md).

Il profilo riconosciuto dal nome visibile esatto `งูแรร์` entra con Name Color `Silver Mist` e Player Icon `Poison 2`: sono valori iniziali, quindi il player può modificarli normalmente. Il Player Vibes è invece fissato a `Draconian`; la pagina Soundtrack resta visibile ma in sola lettura e non può cambiare il valore. Questa voce dedicata non amplia il catalogo globale, che resta di 100 generi per tutti gli altri player. Il riconoscimento non usa un identificatore account: un omonimo con lo stesso nome visibile riceve lo stesso profilo e una rinomina ne impedisce l'applicazione. Il matcher usa la cache stabile `NamaTampilan` dopo la cattura del nome visibile, evitando dipendenze dal token player live durante la transizione di team. Cambio squadra e leave/rejoin passano da cleanup/setup completo: il setup riapplica quindi `Silver Mist`, `Poison 2` e il Vibes bloccato.

La classificazione non prenota uno slot roster finché il nome visibile è `Null` o vuoto: il player viene ritentato quando il token torna disponibile e uno stato transitorio non può consumare erroneamente lo slot 0. Su un vero leave, dopo la finestra di discriminazione di 0,5 s, il cleanup rimuove esattamente la vecchia identità e i suoi handle prima di riciclare lo slot; non può cancellare un nuovo occupante per il solo riuso dello stesso indice. Ogni `PemainDipilih` che puntava al player uscito viene azzerato prima di ricalcolare il leader, evitando voti e riferimenti obsoleti al successivo join.

In Unkillable, `FULL HP` applica insieme invulnerabilità ai danni, immunità agli urti e assenza di collisione con player/bot. Il passaggio a OFF o 1 HP e l'inizializzazione di una nuova entità ripristinano danni, urti e collisione normali come un'unica transazione; cambio squadra e leave/rejoin passano dal reset completo dello stato engine e dal setup iniziale. Try Your Luck non cambia modalità o cursore Unkillable e non scrive mai gravità, trasformazione throttle o stato Ghost/Fly: Fly resta quindi attivo durante tutta la roulette. Vision, Acceleration, Team Heal e Hacked mantengono la protezione; Burning la sospende per tutta la propria durata e la ripristina al termine. Lo Skull finale e Revenge sospendono invece temporaneamente lo status per completare la morte; dopo Resurrect il runtime riapplica la modalità selezionata e ricrea l'icona se il motore l'ha eliminata. `FULL HP` resta protetto anche in Spawn Room.

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

Crouch è il modificatore obbligatorio degli input menu. Per questo `Crouch + Interact` resta riservato al menu, mentre `Interact` senza Crouch può alternare la Camera anche a menu aperto. Un latch condiviso obbliga a rilasciare `Interact` prima che l'altro sistema possa usarlo. Melee e Jump restano azioni normali dell'eroe. Da morto un menu già aperto resta visibile ma congelato: nessun comando Arcade viene eseguito e soltanto Jump attiva `Resurrect`, senza dipendere da Crouch Travel, Camera o Try Your Luck. Un solo raycast verticale decide se serve il recupero dal vuoto: `Resurrect` è incondizionato e, soltanto dopo che il player è tornato vivo, il Teleport usa direttamente `Nearest Walkable Position(Last Of(Position Of(Event Player)))`. Sul terreno il Teleport non viene eseguito. Il percorso non dipende dal validatore delle pagine Travel e non contiene fallback alla Spawn Room, offset casuali, forcing, `Abort` o `Wait`; il latch si riapre al rilascio fisico di Jump e il vecchio `Small Message` “Resurrect unavailable” non deve comparire.

Le cinque pagine dell'overlay Travel usano una terminologia uniforme e specifica in EN/ID/TH: ogni schermata indica pagina, destinazione o posizione, target quando serve e azione. La palette mint → cyan → blu → viola → rosa viene interpolata in 0,18 s sulla stessa `WarnaMenu` dei menu Arcade; gli `Small Message` sono riservati a errori, cooldown, istruzioni necessarie e risultati non già visibili nel HUD, con l'eccezione intenzionale che il fallimento post-`Resurrect` resta silenzioso. I comandi mostrano sempre i binding effettivi del player. Un solo HUD per-player passa gradualmente da mint a cyan, blu, viola e rosa, con istruzioni pastello e contenuto neon; cursore, handle e azioni restano esclusivi del proprietario.

## Try Your Luck

L'attivazione conserva integralmente Unkillable e avvia una macchina a stati senza loop per-player. Modalità, cursore, flag runtime, status, modificatori e icona non vengono modificati all'avvio. Try Your Luck non scrive gravità né avvia o arresta la trasformazione throttle di Fly. I sei esiti sono:

| Esito | Durata | Effetto |
|---|---:|---|
| Vision | 15 s | mostra icona eroe, nome e salute di bot/dummy e di tutti i player, anche con Privacy ON; Crouch non apre inspection/Teleport |
| Acceleration | 10 s | propulsione automatica 3D guidata dalla mira, senza input direzionali |
| Skull | immediato | unico esito che sospende temporaneamente Unkillable per ottenere la morte completa, con retry per mech, duplicazioni e altre forme intermedie |
| Team Heal (Heart) | immediato | cura completa di tutti i player vivi nella squadra del proprietario della roulette; messaggio soltanto al proprietario |
| Burning | 10 s | 5% della salute massima ogni 1 s; Unkillable resta sospeso per l'intero effetto e viene ripristinato al termine |
| Hacked | 5 s | stato Hacked |

Durante la roulette il Menu Arcade resta visibile. Al risultato finale viene chiuso soltanto per gli effetti con durata (Vision, Acceleration, Burning e Hacked), così l'HUD dell'effetto può prendere il suo posto; Skull e Team Heal sono immediati e non chiudono il menu. Un'icona Skull comparsa durante i giri non può attivare la morte: soltanto lo Skull finale, con roulette conclusa e deadline armata, può sospendere Unkillable e viene ritentato ogni 0,25 s finché il player non è realmente morto. Una deadline di 5 s libera comunque menu e input se il motore rifiuta la morte, quindi riattiva logicamente la protezione senza cancellare modalità o cursore. Burning usa un bypass temporaneo dedicato: all'avvio rimuove Unkillable e normalizza Damage Received, applica il 5% della Max Health una volta al secondo per 10 secondi senza cambiare modalità o cursore, quindi ripristina la modalità scelta al termine o nel cleanup anticipato.

Stati, messaggi ed effetti sono localizzati nelle tre lingue. Tutte le sei icone della roulette usano `Visible To and Position`: `Visible To` continua a rivalutare il roster, quindi ogni umano le vede anche dopo join/leave, mentre la posizione `Update Every Frame` resta agganciata a occhio e mirino del beneficiario catturato. L'accelerazione usa `Facing Direction Of(Evaluate Once(player))` con `Direction Rate and Max Speed`: l'identità resta stabile, la mira resta dinamica e il movimento parte senza input direzionali. Vision crea un solo IWT per ogni bot, dummy e player umano, anche con Crouch Privacy ON, mostrando icona, nome e salute live; per gli umani usa la copia stabile del nome roster così il cambio squadra non lo svuota. L'avvio di Vision elimina inoltre eventuali handle Crouch già presenti e il leave di un iBot distrugge il proprio IWT senza entrare nel lifecycle umano. Morte, timeout e cambio eroe chiudono lo stato temporaneo ma preservano modalità, cursore e protezione Unkillable; il cambio eroe viene rilevato dal ciclo globale a 10 Hz senza una nuova regola per-player. Dopo una morte, il tick globale riapplica la protezione e ricrea l'icona quando il player torna vivo. Il leave resta cleanup immediato dopo la guardia `0,5 s`; il cambio squadra usa quarantena e stabilizzazione (`0,5 s`) prima del teardown completo.

Le tre targhette IWT di inspection, Vision e Teleport mantengono icona eroe, nome e salute nello stesso testo. La loro intera posizione `Eye Position(Evaluate Once(identity)) + Vector(0, 0.450, 0)` è racchiusa in `Update Every Frame`, con `Evaluate Once` applicato soltanto all'identità del soggetto; `Visible To Position String and Color` lascia invece rivalutare pubblico, posizione, contenuto e colore. In questo modo la targhetta segue il movimento senza trasferirsi a un target successivo e continua ad aggiornare salute, eroe e colore.

Revenge resta invariato: arma una morte forzata ma non modifica subito il debito ed è, insieme allo Skull finale, l'unico percorso autorizzato a sospendere temporaneamente Unkillable. La macchina globale ritenta la kill sul target vivo; soltanto l'evento di morte con `Is Alive == False` e attacker uguale al claimant ricalcola l'indice corrente e sottrae una carica. Una transizione D.Va/Echo, un altro attacker, un timeout, un leave o un cambio squadra non producono un falso successo. Anche posizione e prompt del Resurrect con Jump attendono `Is Alive == False`; dopo il ritorno in vita, la modalità Unkillable selezionata viene riapplicata.

## Runtime 0.8.1

Il lavoro periodico è coordinato da un solo scheduler `Ongoing - Global` a 20 Hz:

- ogni tick: controlli rapidi, morte completa Revenge/Skull, macchina a stati Try Your Luck e motore Fly 3D;
- 10 Hz: lifecycle, RGB e refresh reattivi;
- 1 Hz: countdown, sincronizzazione del timer nativo e cache passive.

Le scansioni globali non cedono l'esecuzione mentre usano il player e l'indice correnti, ma iterano uno snapshot (`SalinanDaftarPemain`) per evitare modifiche concorrenti della lista nativa durante Team 1 ↔ Team 2. Il lifecycle iniziale resta serializzato da un lock globale; quando un umano registrato cambia squadra, `01a` apre solo una quarantena leggera (`PindahTimDiproses=True`, `SiklusPemainAktif=True`, `SudahSiap=False`, `Manusia=False`) e arma la stabilizzazione a `+0,500 s`, senza chiamare cleanup/quiete pesanti nel frame critico. Dopo spawn e team stabile, `01b` esegue in modo serializzato `TenangkanPemain`, `BersihkanPemain` (solo se il player era ancora nel roster) e `SiapkanPemain`. Lo scheduler non richiama cleanup dipendenti da `Event Player` dal contesto globale. In questo modo lo slot viene riutilizzato pulito, senza teardown nel mezzo della transizione nativa e senza riferimenti stale tra player diversi. `Ongoing - Each Player` resta riservato a input, latch, classificazione one-shot e rendering realmente individuale. `ProsesTerbangPemain` governa propulsione, rampa e arresto Fly nel ciclo globale a 20 Hz; la manutenzione lifecycle e la riapplicazione Ghost/Fly dopo normalizzazioni engine restano a 10 Hz.

Il sorgente mantiene un solo `Loop` e al massimo **7 `Wait`** nominativamente autorizzati per ruolo, durata e quantità. Resurrect e cleanup roster sono atomici; il ritardo di uscita dei dummy dalla Spawn Room usa invece una scadenza timestamp di 1 secondo.

Ogni player mantiene **un solo handle HUD Arcade attivo**. Non esistono preload o pagine nascoste: apertura, chiusura e cambio pagina sono gli unici eventi che ricreano il menu; la navigazione interna aggiorna variabili rivalutate.

Gli aggiornamenti a 10 Hz e 1 Hz sono distribuiti fra i player: con 12 presenze stabili, un tick elabora al massimo 6 manutenzioni a 10 Hz e una cache a 1 Hz. Fly e le scadenze delle funzioni mantengono il ciclo a 20 Hz. Ingressi, uscite e voti marcano un conteggio pendente, eseguito una sola volta al prossimo tick globale (circa 0,05 s a carico normale).

Gli HUD effetti e i testi Teleport/Vision hanno una proprietà persistente in un registro globale di capacità fissa, inclusi i testi dei bot. La pulizia periodica recupera le risorse dei player usciti anche se il motore ha già perso le loro variabili. La navigazione Crouch Travel & Attach aggiorna l'HUD esistente. La revisione richiede comunque conferma in gioco con 12 player e ricambio prolungato della lobby.

## HUD e localizzazione

- Testi runtime, stati, effetti, 37 nomi icona e 26 località sono disponibili in EN/ID/TH.
- I 100 generi, `CHILL`, nomi player ed eroi restano nomi propri universali.
- Identificatori, titoli regola, subroutine e commenti personalizzati restano in Bahasa Indonesia.
- Il file Workshop destinato al client italiano usa la grammatica clipboard `it-IT`: alcuni token cambiano (`variables → variabili`, `rule → regola`, `event → evento`), mentre altri restano identici (`Ongoing - Global`, `Button(Secondary Fire)`).
- La fixture `tests/fixtures/semantic_reference.txt` usa grammatica `en-US` soltanto per il gate semantico e i test: **non è un file da importare nel client**. Il gate canonicalizza entrambi i formati e richiede parità semantica con il vero clipboard `it-IT`, così una modifica funzionale non può essere applicata a una sola copia.
- Ogni `Create HUD Text` usa `Null` nel campo Header; sono ammessi soltanto Subheader/Text e `Small Message`.
- `Big Message` e titoli HUD sono vietati. Gli In-World Text restano ammessi per inspection, Teleport e Vision.
- Menu e liste separano contenuto e comandi con la spaziatura HUD prevista; i promemoria globali descrivono per intero inspection, Menu Arcade e Camera, mentre il blocco sinistro usa `PLAYER VIBES`.
- La griglia fissa usa nove handle: Top `0/1/2`, Left `-2/-1/0/13` e Right `-16/0`. Player Vibes usa una riga Left `1..12` per umano; `Left 13` ospita `CHILL STAR`. A destra compaiono il promemoria Arcade/Camera e `Host:` con icona eroe e nome dell’host corrente, rivalutati quando cambia eroe o host. Con 12 umani e funzioni chiuse, il budget del roster e degli HUD fissi scende da 35 a 21 handle. Menu ed effetti condividono `Top 3`.

Le liste canoniche sono in [`docs/GENERI.md`](docs/GENERI.md) e [`docs/SERVER_LOCATIONS.md`](docs/SERVER_LOCATIONS.md).

## Modalità, timer e Teleport

La durata nelle impostazioni Workshop è configurabile da **10 a 60 minuti**, con valore predefinito di **30 minuti**.

Punteggio e obiettivi restano responsabilità del game mode nativo, ma `Disable Built-In Game Mode Completion` impedisce alla modalità di terminare automaticamente per i propri criteri. Una volta al secondo il timer nativo viene mantenuto sopra zero e sincronizzato al countdown CHILL; checkpoint o overtime non diventano quindi autorità alternative di fine partita. Quando il countdown CHILL raggiunge zero, una guardia one-shot esegue `Restart Match`.

La pagina Objective valuta `Objective Position(Objective Index)` al click e usa la routine condivisa di ricerca di una posizione percorribile. Non esistono più rami per payload, bandiere o robot Push. Se il motore non fornisce una posizione valida, il comando mostra il messaggio di indisponibilità senza teletrasportare il player.

I dummy nativi nascono su uno Spawn Point reale della propria squadra, evitando l'origine della mappa, soltanto quando rimangono almeno due slot liberi. Se la squadra diventa piena, il dummy viene rimosso e la guardia di creazione non lo ricrea finché non tornano disponibili due slot, evitando spam di `Create Dummy Bot` e lasciando spazio a 6 umani. Per uscire dalla Spawn Room usano `Objective Position(Objective Index)`, conservando il percorso Schermaglia già in uso anche sulle mappe senza un obiettivo di gioco visibile. La creazione e il teletrasporto automatico sono limitati alla Schermaglia. Una posizione nulla non produce teletrasporti: il dummy attende il tentativo successivo. Un timestamp stabilizza per 1 secondo lo spawn senza `Wait`; ogni tentativo successivo esplora una direzione orizzontale diversa, alternando otto angoli su due distanze (8 e 12 m). La posizione finale deve restare fra 6 e 16 m dal target e superare i controlli condivisi di spazio libero e pavimento. Il cursore è individuale e viene azzerato a morte/respawn e nel cleanup. Finché il motore rileva il dummy in spawn, la ricerca prosegue al massimo una volta al secondo; dopo 16 candidati riparte dal primo. Fuori dalla spawn, il lock limita bot e dummy al 20%; la regola di setup dummy e `KunciBot` non modificano le collisioni native a spawn, respawn o cambio eroe. Muri, soffitti e pavimenti restano solidi anche per i dummy. Il follow usa una direzione diretta e può fermarsi contro un ostacolo: non aggiunge navigazione intorno alle pareti. `Damage Received` e `Knockback Received` restano entrambi al 100%. Il throttle `Forward` rivalutato seleziona esclusivamente l'umano vivo, ancora registrato, della squadra avversaria che ha Dummy Follow ON; fra i target idonei sceglie sempre il più vicino, vale `0` entro 4 m e riparte se il bersaglio si allontana. Opt-out, morte, assenza di target e rimozione fermano o riallineano facing e throttle senza riferimenti obsoleti.

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

**Riduzione dei picchi:** Inspection e Travel condividono una scadenza individuale di 0,25 s fra le creazioni delle targhette. Un vecchio target viene rimosso subito; se si cambia mira rapidamente, la nuova targhetta può comparire dopo una breve pausa. Le icone roulette sono distribuite in quattro fasi tramite lo slot HUD: con 12 umani si aggiornano al massimo tre icone per tick, senza ritardare le scadenze degli effetti. Le prime rotazioni possono quindi essere meno rapide. Il toggle Diagnostics mostra i contatori ma lascia Inspector Recording disabilitato; i contatori interni vanno confrontati con Text Count ed Entity Count nativi per cercare eventuali oggetti non tracciati.

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

La release 0.8.1 è **live-ready**. I gate repository risultano verdi e la matrice client — inclusi profilo `งูแท้`, cambio squadra con cleanup/setup completo, pagina 13 Ghost/Fly, rampa Forward pura `100% → 500%` in 25 secondi, reset diagonale/laterale/indietro/rilascio, priorità Luck Acceleration, arresto Fly senza input, copia Fly EN/ID/TH, `SERVER LOCATION` ambra neon, Self Kill con cooldown 3 s, Resurrect nello stesso punto su terreno e recupero `Nearest Walkable Position` calcolato dalla posizione live dopo il ritorno in vita senza messaggio “unavailable”, Camera personale/watch senza vibrazione, Burning, cinque pagine Crouch Travel & Attach e respawn dummy a 3 secondi — è stata completata e documentata.
