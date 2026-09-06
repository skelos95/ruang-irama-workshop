# Progetto tecnico — CHILL Dedicated Server 0.8.1

Stato: **static-ready / live-pending**

Questo documento descrive il contratto architetturale del sorgente pubblicato `workshop/ruang_irama.it-IT.workshop`. Le prove statiche certificano le invarianti verificabili dal repository; la 0.8.1 resta live-pending finché non viene completata una nuova regressione nel client, compreso il cambio squadra. La fixture `tests/fixtures/semantic_reference.txt` è un supporto interno al gate semantico e non un secondo file Workshop destinato all'utente: una rappresentazione canonica neutralizza le differenze di grammatica e deve risultare semanticamente identica al clipboard `it-IT`.

## Obiettivi

- Lobby 6v6 con massimo 12 player attivi.
- Overlay sociale e Arcade che non assegna punteggi o vincitori.
- Supporto a Push, Flashpoint, Capture the Flag, Control, Clash, Hybrid, Escort e Assault.
- UI completa in English, Bahasa Indonesia e ไทย.
- Priorità al lavoro globale condiviso rispetto ai loop per-player.
- Cleanup deterministico di HUD, In-World Text, effetti e riferimenti.

## Contratto stabile

### Lingue e pagine

| Indice | Lingua |
|---:|---|
| 0 | English |
| 1 | Bahasa Indonesia |
| 2 | ไทย |

Main Menu usa pagina `-1`; le 14 pagine mantengono gli indici `0..13`. La pagina 12, Dummy Follow, è una preferenza per-player: ON consente al dummy avversario di scegliere quel player, OFF lo esclude; il dummy ordina sempre i target idonei per distanza. La pagina 13 espone due toggle indipendenti, entrambi OFF per default: Ghost attraversa pareti e soffitti con `Include Floors = False`; Fly usa il motore 3D esplicito descritto sotto. Preferenze e cursori persistono durante chiusura, riapertura, cambio eroe, morte e Resurrect. Cambio squadra e leave/rejoin eseguono invece cleanup/setup completo e riapplicano i default.

### Motore Fly 3D

Il test utente del vecchio motore basato sul movimento nativo ha rilevato assenza di progressione della velocità e di salita/discesa su diversi eroi; il successivo motore 3D a impulsi ha invece ricevuto conferma di funzionamento. Questa conferma precede la revisione corrente di strafe e cambio squadra. Il solo esito visivo non identifica con certezza un guasto del timer. La precedente combinazione di `Start Transforming Throttle` e `Set Move Speed` viene sostituita: Blizzard descrive la prima azione come trasformazione dell'input direzionale, non come una propulsione verticale garantita. Questa distinzione motiva la scelta del motore esplicito, ma non sostituisce una verifica nel client. Fonte: [note Blizzard di agosto 2019](https://overwatch.blizzard.com/en-gb/news/patch-notes/live/2019/08/).

`ProsesTerbangPemain` viene richiamata dal solo scheduler globale a 20 Hz per ogni umano idoneo, senza nuovi `Wait` o loop per-player. Il volo normale imposta gravità zero e `Move Speed` nativo zero, evitando che il movimento engine si sommi a quello richiesto. Legge `Throttle Of(player)` non trasformato, dove X positivo è sinistra e Z positivo è avanti. Il vettore richiesto separa le componenti: `Facing Direction Of(player) * Max(0, Z)` per l'avanti con pitch, `Direction From Angles(Horizontal Facing Angle Of(player), 0) * Min(0, Z)` per l'indietro orizzontale e `Cross Product(Vector(0, 1, 0), Direction From Angles(Horizontal Facing Angle Of(player), 0)) * X` per lo strafe orizzontale relativo all'eroe. La normalizzazione mantiene la direzione e l'intensità analogica viene limitata a 1, evitando un bonus diagonale. La scelta di mira più strafe e impulsi, con movimento nativo disattivato, ha un precedente nell'[esempio originale di Shattered sul forum Blizzard](https://us.forums.blizzard.com/en/overwatch/t/%E2%9C%85-how-to-make-reaper-exc-changes/600253/2); qui è adattata al scheduler globale e alla rampa per-player, senza copiarne il loop.

La baseline Fly uniforme è `5,5 m/s = 100%`, una convenzione del motore e non la velocità nativa esatta di ogni eroe, buff o abilità. Soltanto Forward puro, con Z locale maggiore di `0.050` e X fra `-0.050` e `0.050`, arma il timestamp. La percentuale è `Min(500, 100 + Max(0, Total Time Elapsed - start) * 16)` e scala la baseline fino a `27,5 m/s = 500%` dopo 25 secondi. Rilascio, laterali, diagonali e indietro azzerano la rampa; il movimento successivo parte dal `100%`, mentre a input zero la velocità richiesta è zero. Timer, percentuale, direzione e delta di velocità sono player-local. A ogni tick il motore calcola `velocità richiesta - Velocity Of(player)` e applica il relativo impulso `To World` con `Incorporate Contrary Motion`, senza forcing o Teleport: lo stesso controllo governa movimento e hover.

Try Your Luck: Acceleration possiede velocità e propulsione per tutti i 10 secondi: durante quella finestra il motore Fly non applica impulsi né azzera il movimento nativo e riporta la rampa allo stato iniziale. La normale propulsione Fly non avvia né ferma `Start Accelerating`; al termine di Luck parte una rampa fresca. OFF e cleanup di morte, cambio eroe o cambio squadra ripuliscono lo stato transitorio; nel caso cambio squadra il setup successivo riapplica i default. Jump Resurrect riapplica le modalità selezionate. La formula laterale corretta, il reset squadra e la regressione completa di baseline, fluidità e interazioni con collisioni/abilità restano da validare nella matrice live di [`TEST.md`](TEST.md).

### Input

- Tieni Melee per 0,5 s: apre o chiude il Menu Arcade.
- A menu aperto e da vivi, Crouch è il modificatore obbligatorio per Primary, Secondary, Interact, Reload e Ability 1/2.
- Primary/Secondary navigano; Interact entra o applica; Reload torna al Main Menu.
- Nel Soundtrack, Ability 1/2 eseguono `+10/−10`.
- Melee e Jump restano azioni normali dell'eroe.
- A menu aperto o chiuso, Interact tenuto per 0,5 s cambia Camera soltanto con Crouch rilasciato.
- A menu chiuso, Crouch abilita inspection e l'eventuale overlay Teleport.
- Crouch Travel & Attach contiene cinque pagine: Teleport: Spawn Room, Teleport: Active Objective, Teleport: Player / Bot, Attach: Player / Bot e Self Elimination. Primary/Secondary navigano avanti/indietro; Interact esegue la pagina attiva. Un solo HUD per-player ordina ogni pagina come titolo, destinazione/posizione, target e azione, usa i binding effettivi e passa da mint a cyan, blu, viola e rosa con istruzioni pastello e contenuto neon. Self Elimination arma prima della morte un timestamp per-player di 3 secondi; un tentativo anticipato mostra il residuo e non può azzerare il cooldown alla morte. Cambio squadra e leave/rejoin ripartono invece dal setup fresco.
- Il renderer Travel usa `WarnaMenu` con chase da 0,18 s per passare fluidamente mint → cyan → blu → viola → rosa; le conferme Small Message ridondanti sono soppresse, mentre errori/cooldown/esiti restano espliciti.
- Da morto, un menu aperto resta visibile ma congelato; soltanto Jump esegue il recupero e la regola dipende esclusivamente da identità umana, morte, latch e pressione, non dallo stato Crouch Travel o da altre feature. `Resurrect` è incondizionato; l'unico raycast distingue il vuoto dal terreno e, solo nel primo caso, il Teleport successivo valuta direttamente `Nearest Walkable Position(Last Of(Position Of(Event Player)))` sulla posizione live del player già risorto. Sul terreno non viene eseguito alcun Teleport. Dopo `Is Alive == True` ripristina effetti e Ghost/Fly. Il ramo non usa il validatore Travel, `Respawn`, fallback Spawn Room, offset casuali, forcing, `Abort`, `Wait` o `Loop`; il rilascio di Jump riapre sempre il latch e nessun ramo post-tentativo può mostrare il vecchio `Small Message` “Resurrect unavailable”.

Le condizioni e il modificatore sono parte del contratto: `Crouch + Interact` alimenta il menu, `Interact` senza Crouch alimenta la Camera, mentre inspection e Teleport richiedono Crouch e menu chiuso. Menu e Camera condividono un latch consumabile: dopo che uno dei due usa `Interact`, soltanto il rilascio fisico del pulsante riabilita entrambi.

## Scheduler globale

Un'unica regola `Ongoing - Global` mantiene il ritmo base a 20 Hz. Dopo ciascun tick incrementa un contatore e delega a subroutine senza `Wait`:

| Frequenza | Responsabilità |
|---:|---|
| 20 Hz | controlli rapidi, retry morte completa Revenge/Skull, avanzamento Try Your Luck e motore Fly 3D `ProsesTerbangPemain` |
| 10 Hz | lifecycle reattivo, RGB, refresh visivi e riapplicazione Ghost/Fly dopo normalizzazioni engine |
| 1 Hz | countdown, sincronizzazione timer nativo e cache passive |
| 0,1 Hz | minuti di permanenza in lobby |

Il player globale corrente e il relativo indice appartengono esclusivamente allo scheduler. Una scansione non contiene `Wait`, `Loop` o altre azioni che cedono l'esecuzione; nessun'altra regola può riusare quei due scratch globali.

Anche la stabilizzazione dell'uscita dummy è event-driven: l'ingresso nella Spawn Room registra una scadenza di 1 secondo e il controllo periodico agisce soltanto dopo quel timestamp. Non esiste un `Wait` dedicato al dummy e il budget complessivo resta massimo 7 `Wait`.

`Ongoing - Each Player` è ammesso soltanto quando l'evento o lo stato è realmente individuale:

- lettura input e latch di pressione/hold;
- classificazione one-shot umano/bot;
- creazione o rivalutazione di rendering visibile a un singolo player;
- Resurrect o cleanup atomico che dipende dall'evento player.

## Menu Arcade

Ogni player possiede al massimo **un handle HUD Arcade**. Non esistono cache di pagine, preload progressivo o HUD nascosti.

Il lifecycle del menu è:

1. apertura: crea l'handle della pagina corrente;
2. Primary/Secondary o modifica della scelta: aggiorna variabili rivalutate senza ricreare l'HUD;
3. cambio Main Menu ↔ sottomenu: distrugge l'handle precedente e crea la nuova pagina;
4. chiusura, leave o cambio squadra: distrugge l'handle e azzera il riferimento.

Il dispatcher Interact delega alle subroutine delle singole pagine. Avanti/indietro e `±10` usano regole simmetriche condivise; ogni applicazione idempotente evita feedback ripetuti.

Il ciclo del Main Menu è esattamente modulo 14. Pagina 12 dispone di cursore OFF/ON separato dallo stato applicato, renderer EN/ID/TH e tinta dedicata. Pagina 13 possiede un cursore a due righe, renderer e tinta propri: applicare una riga cambia soltanto Ghost oppure Fly. I soli writer dei toggle sono setup/quiete OFF e il relativo handler; applicazione fisica e motore Fly dedicati possiedono `Gravity = 0` e il blocco del movimento nativo. Non è ammesso `Start Transforming Throttle`; il delta di velocità viene applicato soltanto al player della scansione in corso. Ghost non modifica mai la collisione fra player. Soltanto setup, applicazione della pagina e quiete lifecycle possono scrivere la preferenza Dummy Follow, impedendo che Camera o altri latch la modifichino accidentalmente.

### Profilo per nome visibile

Il nome visibile esatto `งูแท้` abilita un profilo dedicato durante il setup. Name Color `Silver Mist` e Player Icon `Poison 2` sono default iniziali e restano modificabili dal player; Player Vibes è invece fissato a `Caladan Brood`, perciò la pagina Soundtrack è visibile ma read-only e nessun input può modificarne il valore. `Caladan Brood` è una voce dedicata al profilo e non entra nel catalogo globale, che resta di 100 generi per i player generici.

Il matching usa esclusivamente il nome visibile, non un identificatore account: due omonimi esatti ricevono lo stesso profilo, mentre una rinomina non viene riconosciuta. Il matcher legge la cache stabile `NamaTampilan` dopo la cattura del nome, quindi durante un team-switch non dipende dal token player live che può risultare temporaneamente vuoto. Cambio squadra e leave/rejoin eseguono nuovamente il setup e riapplicano `Silver Mist`, `Poison 2` e `Caladan Brood`.

Tutti i menu seguono lo stesso layout:

```text
contenuto e stato

comandi disponibili
```

I placeholder devono avere stessa cardinalità nei tre rami linguistici.

## Unkillable FULL HP

FULL HP è uno stato composto e indivisibile: `Damage Received = 0`, `Knockback Received = 0` e `Disable Movement Collision With Players`. Sia l'applicazione dal menu sia il tick globale riapplicano la stessa tripletta. OFF, modalità 1 HP, setup fresco e cleanup di leave/team-switch ripristinano rispettivamente `100`, `100` e `Enable Movement Collision With Players`; una protezione parziale è vietata. Try Your Luck non modifica modalità o cursore Unkillable: Vision, Acceleration, Team Heal e Hacked conservano la tripletta, mentre Burning sospende status e riduzione del danno per l'intero effetto e li ripristina al termine. Un cleanup engine può normalizzare temporaneamente lo stato dopo morte o timeout, ma conserva `ModeKebal`/`KursorKebal`, ricava di nuovo `KebalAktif` dalla modalità e lascia al tick globale la riapplicazione e l'eventuale ricreazione dell'icona. Anche in Spawn Room la modalità 2 resta protetta; soltanto la modalità 1 HP usa il ramo di ripristino normale.

## Try Your Luck

Try Your Luck è una macchina a stati guidata da timestamp, non un loop per-player. All'avvio conserva Unkillable senza scrivere modalità, cursore o stato di protezione e mantiene la pagina bloccata finché la sequenza non termina. Nessun handler, tick o cleanup della roulette scrive gravità, trasformazione throttle, toggle Ghost/Fly o latch fisico: Fly non viene mai spento da Try Your Luck.

| Esito | Durata | Comportamento |
|---|---:|---|
| Vision | 15 s | mostra icona, nome e salute live di bot/dummy e di tutti gli umani, anche con Privacy ON, e sopprime inspection/Teleport Crouch |
| Acceleration | 10 s | applica propulsione automatica lungo la direzione 3D della mira, senza input direzionali |
| Skull | immediato | unico esito che bypassa temporaneamente Unkillable e ritenta la kill fino alla morte completa; deadline 5 s impedisce un latch permanente |
| Team Heal (Heart) | immediato | porta alla salute completa tutti i player vivi della squadra del proprietario; notifica soltanto il proprietario |
| Burning | 10 s | infligge il 5% della salute massima ogni 1 s; sospende Unkillable e normalizza Damage Received per l'intera durata, poi ripristina la modalità scelta |
| Hacked | 5 s | applica e poi rimuove Hacked |

Il tick globale valuta transizioni e scadenze. Vision, Acceleration, Team Heal e Hacked non sospendono Unkillable; Burning è l'eccezione a durata: conserva modalità e cursore ma sospende status e riduzione del danno per tutti i 10 secondi, applica il 5% della Max Health ogni secondo e ripristina la protezione al termine o nel cleanup anticipato. Soltanto lo Skull finale armato e Revenge passano invece dal bypass della macchina di morte completa. Alla morte o al timeout vengono annullati stato temporaneo, accelerazione, status dell'esito, HUD/IWT ed effetti associati, ma la preferenza Unkillable resta intatta e viene riapplicata dopo Resurrect. Un tracker eroe condiviso rileva inoltre a 10 Hz il cambio eroe umano e applica lo stesso cleanup temporaneo senza azzerare la preferenza sul player vivo e senza aggiungere un nuovo `Ongoing - Each Player`; cambio squadra e leave ripuliscono invece l'entità con cleanup completo, poi il player rientra dal setup fresco. Nessun esito può lasciare un timestamp o un riferimento riutilizzabile dal player successivo nello stesso slot.

Le sei icone della roulette usano la reevaluation `Visible To and Position`. `Visible To` rivaluta il roster umano anche dopo join/leave, mentre la posizione `Update Every Frame` resta agganciata a occhio e mirino dell'identità catturata, senza seguire lo scratch `Global.PemainAktif`. L'indicatore off-screen resta abilitato e i bot non entrano mai nel pubblico.

L'accelerazione usa `Facing Direction Of(Evaluate Once(player))`: viene congelata soltanto l'identità del beneficiario, non la sua direzione corrente. `Direction Rate and Max Speed` mantiene quindi la spinta automatica davanti, in alto e in basso senza throttle o input direzionali. Quando Fly è ON, tutto il suo motore a impulsi cede la precedenza all'esito Acceleration, compreso il freno idle; alla scadenza il cleanup ferma la spinta e Fly riparte con una rampa fresca o torna immobile senza input. Il ramo Luck del tick globale conserva soltanto avvio, timestamp e cleanup; Luck non usa impulsi periodici e non aggiunge loop o regole per-player.

## Lifecycle player

### Join

La registrazione verifica prima l'esistenza del player nel roster. Un evento Join duplicato non aggiunge una seconda voce e non crea un secondo messaggio o handle. Un nome visibile ancora `Null` o vuoto riapre il classifier prima dell'allocazione, quindi non può consumare uno slot con un'identità temporanea. Il setup inizializza ogni variabile player dichiarata, assegna lo slot sociale e crea una sola coppia di HUD roster. Su un leave vero ogni `PemainDipilih` che punta al leaver viene azzerato prima della rimozione dal roster e del ricalcolo Vote Player.

Dummy e bot AI seguono classificazione e lock dedicati: non vengono inseriti nel roster umano e non ricevono menu, HUD, input Arcade o funzioni riservate ai player. Possono restare target passivi di inspection, Vision e Camera dove previsto dal contratto. Per gli umani, Camera, inspection e Teleport rispettano Privacy; Vision è l'eccezione intenzionale e include tutti gli umani.

Revenge e lo Skull finale condividono l'unico percorso che bypassa temporaneamente Unkillable nel tick globale. Il comando `Kill` è centralizzato e rivalutato ogni 0,25 s finché il target è ancora vivo; non viene usato `Is In Alternate Form`, perché non identifica in modo univoco una vita intermedia. Revenge conserva invariati claimant e contabilità: ricalcola l'indice del debito al commit e decrementa soltanto su `Player Died` con `Is Alive == False` e attacker coincidente. Doppio claim, attacker diverso, timeout, leave e team switch non generano un falso conteggio. Dopo Resurrect il tick globale ripristina la modalità Unkillable selezionata e ricrea la relativa icona se il motore l'ha distrutta.

Per i dummy nativi il runtime mantiene al massimo un'istanza per Team 1 e una per Team 2. La creazione richiede almeno due slot liberi e uno Spawn Point valido; se la squadra diventa piena con il dummy presente, il bot viene rimosso per rendere disponibile il sesto posto umano. La soglia di due slot impedisce una ricreazione immediata e quindi lo spam di `Create Dummy Bot`. Il tempo massimo di respawn è 3 secondi. Quando un dummy vivo si trova nella Spawn Room, registra una scadenza di 1 secondo e, senza `Wait`, sceglie poi una destinazione coerente con la modalità e la passa sempre da `Nearest Walkable Position`; se la posizione richiesta non è valida, non viene eseguito alcun teleport e il controllo viene rivalutato al ciclo successivo. I dummy ricevono danni e urti al 100%, mantengono la collisione con player/bot e disabilitano soltanto le collisioni ambientali con `Include Floors = False`.

### Leave

`Player Left Match` attende 0,5 s per distinguere un'uscita reale da una transizione di squadra. Quando l'identità non esiste più, il cleanup:

1. distrugge gli handle HUD, In-World Text ed effetti registrati per il leaver;
2. rimuove soltanto la sua identità esatta dal roster, senza fallback al nuovo occupante dello stesso slot;
3. libera riferimenti in Camera, Revenge, Teleport, inspection e voti dei survivor;
4. rende lo slot riutilizzabile e ricostruisce soltanto le cache condivise necessarie.

Non esegue reset engine su un'entità ormai uscita. Il nuovo occupante passa dal setup fresco e non eredita preferenze, timer o riferimenti del leaver; la riutilizzabilità effettiva va verificata anche a 12 slot.

### Cambio squadra

Il cambio Team 1 ↔ Team 2 di un umano già registrato usa ora un lifecycle in due fasi. La regola `01a - Siklus tim: Reset penuh pada konteks pemain` (sempre `Ongoing - Each Player`) rileva il mismatch ma non esegue teardown pesante: attiva una quarantena leggera (`PindahTimDiproses=True`, `SiklusPemainAktif=True`, `SudahSiap=False`, `Manusia=False`), aggiorna `TimSiklusTarget`, conferma `TimTerakhir` e arma `WaktuSiklusTim = Total Time Elapsed + 0.500`. Se quel player possedeva già il lock lifecycle, `01a` rilascia solo la propria prenotazione globale.

Nel caso limite senza slot, l'attesa è cooperativa: il classifier ripristina `SudahDiperiksa`, `SudahSiap` e i latch lifecycle, rilascia soltanto il proprio `PemainSiklusGlobal` e programma il tentativo successivo dopo 0,25 secondi, così gli altri player continuano a essere processati. Nel repair di uno stato degradato su player ancora registrato (non nel percorso team-switch), il nome esatto `งูแท้` riasserisce sempre `Caladan Brood`; Silver Mist e Poison 2 vengono riapplicati solo se `PernahDisiapkan=False`.

La fase 2 è serializzata da `01b`: quando il player è spawned, il team resta uguale a `TimSiklusTarget` e la finestra `0,500 s` è scaduta, il worker esegue `TenangkanPemain`, poi `BersihkanPemain` soltanto se la vecchia registrazione roster è ancora presente, quindi `SiapkanPemain`. In questo modo il reset completo avviene fuori dalla transizione nativa del motore. Se il player cambia nuovamente squadra in attesa, il detector aggiorna target/scadenza e rilascia la vecchia prenotazione; la nuova acquisizione attende entrambe le scadenze (globale e individuale), e una prenotazione non resta occupata da un player non spawned.

## HUD, testi ed effetti

- `Create HUD Text` deve avere Header `Null`.
- Sono consentiti Subheader/Text, `Small Message` e gli In-World Text necessari a inspection, Teleport e Vision.
- `Big Message` e titoli HUD non sono consentiti.
- Gli handle vengono distrutti prima di essere sovrascritti; le variabili handle tornano a `Null`.
- `TutupMenu` usa prima l'handle canonico del roster, anche quando `HudMenu` locale è `Null`; elimina poi l'eventuale handle locale solo se diverso da quello canonico, senza distruggere due volte lo stesso HUD.
- Ogni testo operativo, stato, esito, nome icona e località ha rami EN/ID/TH.
- I 100 generi, `CHILL`, nomi player ed eroi sono nomi propri universali.
- Identificatori personalizzati, titoli regola, subroutine e commenti Workshop sono in Bahasa Indonesia; keyword native, acronimi tecnici e nomi degli eroi restano invariati.
- La riga Fly della pagina 13 comunica guida e rampa con testo equivalente nelle tre lingue: `LOOK TO STEER | HOLD FORWARD: 100% > 500% IN 25s`, `ARAHKAN PANDANGAN | TAHAN MAJU: 100% > 500% DALAM 25dtk` e `บังคับด้วยมุมมอง | กดเดินหน้าค้าง: 100% > 500% ใน 25วิ`.
- La label localizzata `SERVER LOCATION` / `LOKASI SERVER` / `ตำแหน่งเซิร์ฟเวอร์` usa l'ambra neon `Custom Color(255, 205, 110, 255)`, volutamente distinto dal cyan di `LOBBY & CHILL TIME`.

La griglia HUD usa dieci handle globali fissi e slot dinamici separati:

| Area | Slot fissi | Slot dinamici |
|---|---|---|
| Top | titolo/timer `0`, località `1`, spaziatore `2` | menu, Teleport o effetto `3` |
| Left | comando completo `-2`, spaziatore `-1`, `LOBBY & CHILL TIME` `0` | roster/minuti `1..12` |
| Right | comando completo `-16`, spaziatore superiore `-15`, `PLAYER VIBES` `-14`, spaziatore finale `-1` | roster/musica `-13..-2` |

Titolo, label e righe roster non contengono newline usati come compensazione verticale. Il contatore diagnostico include i dieci handle fissi. La diagnostica opzionale è il terzo segmento del Subheader dell'ultima riga Left e il campo Text resta direttamente `Null`: così il client non converte un ramo `Null` tipizzato come stringa nel numero `0`.

Il nuovo Team Status Indicator del client non è riposizionabile dal Workshop. Tutto il blocco Right custom usa sort negativi e termina con uno spaziatore reale `-1`, riservando una riga dopo l'ultimo nome nell'area che precede gli elementi nativi. Il test live con 1, 6 e 12 player deve confermare il confine effettivo con indicatore e kill feed.

## Camera, inspection e Teleport

La Camera usa un solo `Start Camera` e un solo raycast per risolvere la posizione. Posizione e punto osservato restano rivalutati ogni frame e `Blend Speed 0` applica direttamente la nuova traslazione: un blend non nullo inseguirebbe continuamente il target mobile e introdurrebbe correzioni visibili durante corsa, strafe e salto. La stessa subroutine serve camera personale, watch e toggle rapido. Target morti, non spawnati, inesistenti o umani con Privacy ON vengono rimossi; una perdita target porta a un fallback valido senza creare più Camera concorrenti. Se un target umano attiva Privacy mentre è osservato, gli osservatori custom già agganciati tornano alla visuale normale.

Inspection e Teleport sono disponibili soltanto a menu chiuso e da vivi. Le targhette di inspection, Vision e Teleport condividono lo stesso contratto: un solo IWT contiene insieme icona eroe, nome e salute; `Update Every Frame` racchiude l'intero ancoraggio `Eye Position(Evaluate Once(identity)) + Vector(0, 0.450, 0)`; `Evaluate Once` cattura esclusivamente l'identità del soggetto; `Visible To Position String and Color` mantiene la rivalutazione completa di pubblico, posizione, testo e colore. Durante Vision entrambi gli ingressi Crouch sono disattivati e gli handle eventualmente già aperti vengono rimossi, mentre Vision mantiene un solo IWT per ogni bot, dummy e umano; il nome umano proviene dal cache roster stabile. Privacy è OFF per default: quando passa ON, Camera custom, inspection, Teleport e Attach non possono creare o mantenere il riferimento identificativo dell'umano e gli osservatori Camera già attivi vengono sganciati. Vision ignora intenzionalmente questa preferenza e continua a mostrare tutti gli umani per l'intera durata dell'esito.

La destinazione Teleport viene rivalutata al click:

| Modalità | Destinazione |
|---|---|
| Escort, Hybrid | Payload |
| Capture the Flag | bandiera nemica valida |
| Push | proxy valido dell'obiettivo, poi fallback Objective Position |
| Flashpoint, Control, Clash, Assault | `Objective Position(Objective Index)` |

La pagina Player / Bot sceglie un target vivo/spawnato vicino al reticolo e rispetta Privacy; `Nearest Walkable Position` limita le destinazioni non praticabili.

La stessa matrice viene riutilizzata dalla regola di uscita Spawn dei dummy dopo la scadenza timestamp di 1 secondo: Escort/Hybrid → payload, CTF → bandiera nemica, Push → proxy/fallback obiettivo, altre modalità → obiettivo corrente. A differenza del Teleport manuale, in assenza di una destinazione valida il dummy non riceve un fallback arbitrario: resta in Spawn Room e riprova, senza introdurre un nuovo `Wait`.

## Modalità native

La logica Arcade non assegna punti, non completa round e non dichiara vincitori. Punteggio e avanzamento degli obiettivi restano nativi; l'unica eccezione intenzionale è l'autorità temporale: nel ramo scheduler a 1 Hz `Disable Built-In Game Mode Completion` e `Set Match Time` mantengono la partita aperta fino allo zero del countdown CHILL, quando una guardia one-shot esegue `Restart Match`. Overtime ed estensioni native non devono sostituire quel countdown. La verifica live attraversa tutte le otto modalità:

| Modalità | Focus |
|---|---|
| Push | proxy robot, avanzamento obiettivo e timer CHILL invariato |
| Flashpoint | indice obiettivo attivo |
| Capture the Flag | bandiera nemica |
| Control | cattura, percentuale e timer CHILL invariato |
| Clash | avanzamento tra punti |
| Hybrid | payload dopo la cattura |
| Escort | payload, checkpoint e timer CHILL invariato |
| Assault | transizione A/B |

Busan, Eichenwalde e Paraíso hanno priorità perché modificati nella patch dell'11 agosto 2026.

## Gate di prestazioni

Target statici:

- un solo `Loop` globale;
- massimo 7 `Wait`, ciascuno associato a un percorso autorizzato;
- stabilizzazione dummy a timestamp, mai tramite un ottavo `Wait`;
- un solo `Start Camera`, con posizione/look-at per-frame e `Blend Speed 0`, un solo raycast Camera e tre ingressi condivisi (personale, watch, toggle rapido);
- nessuna regola, variabile o subroutine inutilizzata/duplicata;
- nessun loop o Wait dentro le subroutine chiamate durante una scansione scheduler;
- un solo handle HUD Arcade attivo per player;
- sorgente sotto 32.768 elementi, obiettivo massimo 26.000;
- largest rule sotto 98 KB, obiettivo massimo 80 KB.

Gli ultimi due valori devono essere letti nel client: non sono deducibili con precisione dal solo testo Workshop.

## Repository e release

Il workflow permanente `validate-workshop.yml` usa Python 3.12 e sola standard library per eseguire unit test e validatore. Il vecchio workflow `maintenance-patch.yml`, che applicava e committava patch automatiche, è stato rimosso. L'allowlist dell'intero albero `.github` ammette soltanto il workflow permanente: file marker, trigger, patcher e automazioni one-shot sono errori di validazione. In `workshop/` viene mantenuto un solo file destinato all'importazione, `ruang_irama.it-IT.workshop`; il riferimento `en-US` vive soltanto sotto `tests/fixtures/` e la sua forma canonica deve restare semanticamente equivalente al clipboard pubblico.

La release 0.8.1 resta **static-ready / live-pending**: i gate statici devono risultare verdi sul commit finale, ma la matrice nel client non è ancora documentata come completata e non viene dichiarato alcun tag finale. Per chiudere la regressione restano obbligatorie le prove seguenti:

- import pulito nel client del 19 agosto 2026 e smoke test D.Mon;
- matrice input/menu/localizzazione;
- regressione della formula Fly dopo la conferma del motore precedente: pitch fino a ±90°, orientamenti cardinali, baseline uniforme 5,5 m/s e cap 27,5 m/s, rampa 25 s, hover, due player indipendenti, collisioni, ergonomia e priorità Luck;
- stress join/leave/team switch;
- matrice sulle otto modalità, compresa l'uscita Spawn dei dummy;
- soak di almeno 30 minuti con 12 slot;
- diagnostica senza crescita progressiva di HUD, In-World Text o effetti.

La procedura completa è in [`TEST.md`](TEST.md); il gate semantico è descritto in [`VALIDAZIONE.md`](VALIDAZIONE.md).


### Dummy bot: spawn e distanza sicura

I dummy vengono creati soltanto quando esistono uno Spawn Point della squadra e almeno due slot liberi; la posizione iniziale è quello Spawn Point, non `Null`. Se il team è pieno, il dummy viene rimosso per liberare capacità e la soglia di creazione evita cicli ripetuti. L'uscita automatica dalla spawn registra un timestamp di 1 secondo, senza `Wait`, quindi cerca una posizione camminabile circa 10 m verso la propria metà mappa e rifiuta destinazioni a meno di 6 m dall'obiettivo/bandiera. Bot AI e dummy hanno velocità di movimento al 20% e restano offensivamente passivi, ma ricevono danni e urti normalmente. Soltanto il dummy Workshop disabilita la collisione con pareti e soffitti mantenendo il pavimento; la collisione con player/bot resta esplicitamente abilitata. Il filtro considera esclusivamente umani registrati, vivi, spawned, avversari e con Dummy Follow ON; `Sorted Array` sceglie sempre il più vicino e il dummy avanza in `Forward` finché la distanza è maggiore di 4 m. Lo stesso filtro governa il cleanup senza target, così opt-out, morte o team-switch non lasciano facing/throttle verso un array vuoto. La magnitudine rivalutata consente arresto e ripartenza senza nuove regole, `Wait` o `Loop`.
