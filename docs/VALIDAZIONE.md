# Rapporto di validazione — versione 0.8.1

Data: 2026-09-02

Release tecnica: **CHILL Dedicated Server 0.8.1**

Stato: **static-ready / live-pending**

Il gate 0.8.1 analizza il significato e la struttura del sorgente Workshop. Non usa un hash dell'intero file: modifiche lecite di spaziatura o documentazione non invalidano il rilascio, mentre una mutazione che viola un'invariante deve fallire con un messaggio mirato.

## Esecuzione

Dalla radice del repository:

```powershell
python -m unittest discover -s tests -p 'test_*.py'
python tools/validate_workshop.py
```

Il workflow `.github/workflows/validate-workshop.yml` esegue gli stessi comandi con Python 3.12, sola standard library e permesso GitHub `contents: read`. È l'unico workflow permanente. L'allowlist copre l'intero albero `.github`: `maintenance-patch.yml`, marker, trigger, patcher e automazioni one-shot sono vietati, quindi la validazione non modifica, non committa e non pubblica file.

## Gate semantici

### Struttura e riferimenti

Il validatore controlla:

- delimitatori e blocchi Workshop completi;
- parentesi tonde e quadre bilanciate fuori da stringhe/commenti, incluse tutte le chiamate annidate nelle azioni;
- indici compatti e dichiarazioni univoche per global, player e subroutine;
- nomi global, player e subroutine lunghi al massimo 32 byte in UTF-8, per evitare il rifiuto dell'import da parte del client;
- ogni riferimento risolto alla relativa dichiarazione;
- nessuna variabile soltanto dichiarata, inizializzata o pulita;
- nessuna regola o subroutine inutilizzata o duplicata;
- ogni player variable inizializzata nel setup e ripulita dove necessario;
- assenza della vecchia roulette binaria e degli handle di preload.

Non esiste una lista rigida dell'intero blob: le invarianti vengono ricavate dai blocchi e dalle azioni effettive.

### Parità clipboard it-IT / fixture en-US

Il file realmente importabile `workshop/ruang_irama.it-IT.workshop` e la fixture interna `tests/fixtures/semantic_reference.txt` vengono trasformati in una rappresentazione canonica comune. Il gate richiede la stessa sequenza di dichiarazioni, subroutine, regole, condizioni e azioni dopo aver neutralizzato soltanto le differenze native della grammatica clipboard italiana/inglese. Una modifica funzionale presente in una sola copia deve fallire; il semplice conteggio delle regole non è considerato una prova sufficiente di equivalenza.

### Nomenclatura

Identificatori personalizzati, titoli regola, nomi subroutine e commenti Workshop devono essere in Bahasa Indonesia. Restano ammessi:

- keyword e azioni native Workshop;
- contenuto del ramo HUD English e ไทย;
- acronimi tecnici;
- `CHILL`, generi musicali, nomi degli eroi e player.

Il gate rifiuta residui noti italiano/inglese negli elementi personalizzati e i vecchi alias rimossi.

### Localizzazione EN/ID/TH

Il gate verifica:

- rami lingua `0/1/2` per istruzioni, stati, effetti e Small Message;
- 14 menu e tutte le pagine operative, con ciclo Main Menu esatto `0..13`;
- pagina 12 Dummy Follow completa di renderer, cursore OFF/ON, dispatcher, tinta dedicata e default OFF;
- pagina 13 Ghost Mode / Fly completa di renderer EN/ID/TH, due cursori/toggle indipendenti, dispatcher, tinta dedicata e default OFF; il messaggio di apertura deve annunciare quattordici pagine in EN/ID/TH e non può contenere le vecchie forme Thirteen/Tiga belas/สิบสาม; la riga Fly deve insegnare `LOOK TO STEER | HOLD FORWARD: 100% > 500% IN 25s`, `ARAHKAN PANDANGAN | TAHAN MAJU: 100% > 500% DALAM 25dtk` e `บังคับด้วยมุมมอง | กดเดินหน้าค้าง: 100% > 500% ใน 25วิ`;
- 37 nomi Player Icon in tre array allineati;
- 26 località server in tre array allineati e label localizzata in ambra neon `Custom Color(255, 205, 110, 255)`, distinta dal cyan di `LOBBY & CHILL TIME`;
- equivalenza di placeholder e argomenti tra le traduzioni;
- minuti roster `MIN / MENIT / นาที`;
- riga vuota coerente tra contenuto e comandi.
- promemoria del modificatore presente nei menu ma non duplicato nell'HUD globale, senza newline iniziale superfluo.

I 100 generi restano nomi internazionali e non richiedono traduzione. Il profilo per nome visibile esatto `งูแท้` usa `Caladan Brood` come Player Vibes dedicato e bloccato senza aggiungerlo al catalogo globale.

### HUD e rendering

Ogni azione `Create HUD Text` deve:

- avere Header `Null`;
- usare soltanto Subheader/Text;
- registrare l'handle previsto per il cleanup.

Sono vietati `Big Message`, titoli HUD, preload, pagine nascoste e più di un handle Menu Arcade attivo per player. `Small Message` e gli In-World Text di inspection, Teleport e Vision restano ammessi, ma il ramo post-tentativo Jump non può contenere “Resurrect unavailable” né le equivalenti stringhe ID/TH. Il gate richiede esattamente dieci HUD fissi negli slot Top `0/1/2`, Left `-2/-1/0` e Right `-16/-15/-14/-1`; i roster usano rispettivamente `1 + UrutanHUD` e `-13 + UrutanHUD`. Menu, Teleport ed effetto Try Your Luck condividono `Top 3` senza newline iniziali artificiali.

Il gate controlla che il menu venga ricreato soltanto ad apertura, chiusura o cambio pagina; navigazione e applicazioni sulla stessa pagina devono usare valori rivalutati.

### Input

Le regole avanti/indietro e `±10` devono essere simmetriche. Il validatore richiede:

- hold Melee 0,5 s per apertura/chiusura;
- Crouch come modificatore di Primary, Secondary, Interact, Reload e Ability 1/2 a menu aperto;
- nessuna disabilitazione custom di Melee o Jump da vivi;
- Camera con Interact 0,5 s a menu aperto o chiuso, ma soltanto con Crouch rilasciato;
- latch Interact condiviso tra menu e Camera, consumato da un solo sistema fino al rilascio;
- inspection e Teleport soltanto a menu chiuso e da vivi;
- menu congelato da morti e Jump come unico input custom di `Resurrect`; l'azione `Respawn` è vietata e posizione/prompt vengono registrati soltanto con `Is Alive == False`;
- sequenza Jump esatta e senza percorsi bloccanti: le sole condizioni ammesse sono identità umana, morte, latch e Jump; l'unico `Resurrect` è incondizionato e precede un'unica guardia raycast. Soltanto il ramo vuoto contiene l'unico `Teleport`, con destinazione esatta `Nearest Walkable Position(Last Of(Position Of(Event Player)))` calcolata dalla posizione live post-resurrezione; scratch `PosisiBangkitAman` e destinazioni calcolate dalla snapshot di morte sono vietati. Conferma `Is Alive`, ripristino effetti e riapplicazione Ghost/Fly restano obbligatori, così come l'assenza di validatore Travel, `Abort`, fallback Spawn Room, offset casuali, forcing, `Respawn`, `Wait`, `Loop` e qualunque `Small Message` di fallimento post-tentativo;
- latch rilasciati senza doppie attivazioni.

### Unkillable FULL HP

`FULL HP` è validato come stato composto indivisibile. Sia l'applicazione menu sia la riapplicazione globale devono eseguire insieme:

- `Damage Received = 0`;
- `Knockback Received = 0`;
- `Disable Movement Collision With Players`.

OFF, 1 HP, setup e cleanup locali/globali devono contenere il ripristino atomico `100/100/Enable Movement Collision With Players`. L'avvio di Try Your Luck, invece, non può scrivere `ModeKebal`, `KursorKebal`, `KebalAktif`, status, salute, tripletta o icona Unkillable. I cleanup possono normalizzare lo stato engine soltanto quando la modalità è OFF o il player è realmente morto; un cleanup live per timeout/hero swap conserva status e tripletta. Nessun cleanup può modificare modalità o cursore e deve poi assegnare logicamente `KebalAktif = ModeKebal != 0`; alla ripresa in vita la riapplicazione globale deve riportare 1 HP/FULL HP e ricreare l'icona quando l'handle è `Null` oppure l'entità non esiste più. In Spawn Room la modalità 2 conserva la tripletta protettiva, mentre soltanto il ramo 1 HP ripristina i valori normali. Le sole due disabilitazioni della collisione con player ammesse appartengono ai rami FULL HP locale e globale; una protezione parziale, una chiamata duplicata o l'applicazione della stessa immunità a dummy/iBot fa fallire il gate.

### Ghost Mode / Fly

Il gate assegna la proprietà esclusiva della fisica della pagina 13 ai relativi setup, applicazione locale, motore `ProsesTerbangPemain` a 20 Hz e manutenzione lifecycle globale a 10 Hz:

- Ghost usa `Disable Movement Collision With Environment(player, False)`, quindi attraversa pareti e soffitti ma conserva i pavimenti; non può modificare la collisione con player/bot;
- Fly normale usa gravità zero e `Move Speed` nativo zero; `Start Transforming Throttle` è vietato. La direzione esplicita separa le componenti: avanti con pitch (`Facing Direction * Max(0, Z)`), indietro orizzontale (`Direction From Angles(Horizontal Facing Angle, 0) * Min(0, Z)`) e strafe orizzontale (`Cross Product(up, horizontalForward) * X`), con X positivo verso sinistra e Z positivo in avanti; direzione normalizzata e intensità analogica limitata a 1 evitano bonus diagonali;
- soltanto Forward puro (`Z > 0.050` e X fra `-0.050` e `0.050` nel throttle locale) inizializza il timestamp e la percentuale per-player `Min(500, 100 + Max(0, Total Time Elapsed - start) * 16)`: la baseline uniforme `5,5 m/s = 100%` raggiunge `27,5 m/s = 500%` dopo 25 secondi. La percentuale non viene passata a `Set Move Speed` e non rappresenta una misura della velocità nativa di ogni eroe/buff;
- rilascio Forward e input diagonale/laterale/indietro riarmano il timer e la percentuale al `100%`; OFF, morte e transizioni lifecycle disarmano la rampa e normalizzano la fisica prevista. Setup e quiete reale inizializzano anche percentuale, direzione e delta per-player; ogni tick Fly normale li ricalcola prima dell'impulso, senza riutilizzare scratch precedenti. Il movimento nativo resta zero durante Fly normale; OFF lo ripristina insieme alla gravità senza interrompere Luck Acceleration ancora attiva;
- il motore calcola il delta fra velocità richiesta e corrente, quindi applica un impulso `To World` con `Incorporate Contrary Motion`; senza input la velocità richiesta è zero e lo stesso controllo annulla la deriva. Non usa forcing di posizione, Teleport, nuovi `Wait`, loop per-player, `Start Accelerating` o `Stop Accelerating`;
- toggle e cursori restano distinti, sono OFF al setup/cleanup reale e persistono durante morte, Resurrect e cambio eroe; cambio squadra e leave/rejoin passano da cleanup/setup completo e li riportano OFF; la morte disarma immediatamente il latch fisico e Jump Resurrect riapplica Ghost/Fly nello stesso tick dopo il ripristino effetti;
- Try Your Luck non può scrivere gravità, throttle trasformato o stato Ghost/Fly; Acceleration conserva il proprio `Start Accelerating` e la proprietà totale della velocità per tutti i 10 secondi: Fly non applica impulsi né blocco del movimento nativo. La rampa resta riarmata e riparte fresca da `100%` soltanto dopo la scadenza;
- il Main Menu usa sempre `GambarUtama`: la catena localizzata termina esplicitamente con indice 12 Dummy Follow e fallback 13 Ghost/Fly; il router non può scegliere staticamente un renderer diverso in base a `KursorUtama` né ridisegnare l'HUD durante lo scroll.

### Scheduler e prestazioni statiche

Il gate richiede:

- un solo scheduler `Ongoing - Global` a 20 Hz;
- un solo `Loop` nel sorgente;
- massimo 7 `Wait`, ciascuno fissato per ruolo, durata e quantità;
- subroutine scheduler senza `Wait`;
- nessun yield durante una scansione del roster;
- proprietà esclusiva dello scratch player/indice globale allo scheduler;
- attività 20 Hz, 10 Hz, 1 Hz e minuti ogni 10 secondi, incluso `ProsesTerbangPemain` a 20 Hz senza yield, riapplicazione Ghost/Fly a 10 Hz dopo normalizzazioni engine e sincronizzazione del timer nativo soltanto nel ramo 1 Hz;
- `Ongoing - Each Player` limitato a input, latch, classificazione one-shot e rendering individuale;
- un solo `Start Camera`, posseduto da `MulaiKamera`, con entrambi i vettori per-frame, `Blend Speed 0` e un solo raycast Camera; camera personale, watch e toggle rapido devono convergere nei tre richiami alla stessa subroutine;
- nessuna regola HUD contenente `Wait` o `Loop`.

Le categorie Wait autorizzabili sono soltanto: tick scheduler, ordinamento join/leave, primo frame della classificazione bot e hold input. Resurrect e cleanup roster sono atomici e senza `Wait`; la stabilizzazione dell'uscita dummy dalla Spawn Room usa una scadenza timestamp di 1 secondo. Qualsiasi Wait fuori allowlist, un ottavo `Wait`, una durata diversa o un secondo Loop fa fallire il gate.

### Try Your Luck

Il validatore riconosce una macchina a stati con timestamp e sei esiti, non il vecchio percorso binario:

| Esito | Invariante |
|---|---|
| Vision | durata 15 s, IWT con icona/nome/salute live per bot/dummy e tutti gli umani anche con Privacy ON, più blocco/cleanup di inspection e Teleport Crouch |
| Acceleration | durata 10 s e propulsione automatica 3D guidata dalla mira, senza dipendenza dal throttle |
| Skull | unico esito autorizzato a bypassare temporaneamente Unkillable; trigger soltanto sull'esito finale armato, retry globale ogni 0,25 s fino a `Is Alive == False`, con deadline anti-blocco di 5 s |
| Team Heal (Heart) | cura completa di tutti i player vivi della squadra del proprietario della roulette |
| Burning | 5% max HP ogni 1 s per 10 s; rimuove Unkillable e normalizza Damage Received per l'intera durata, quindi ripristina la modalità scelta |
| Hacked | durata 5 s e cleanup status |

L'avvio della roulette non può sospendere Unkillable e un'icona Skull intermedia non può armare la morte. Vision, Acceleration, Team Heal e Hacked restano protetti. Burning è l'eccezione non-Skull esplicitamente autorizzata a eseguire `Clear Status(Unkillable)` e `Damage Received = 100`: modalità e cursori restano invariati, la sospensione dura per tutto l'effetto da 10 secondi, il danno è 5% Max Health ogni secondo e la protezione selezionata viene ripristinata soltanto alla fine o nel cleanup anticipato, non fra i tick. Il ramo centralizzato Skull finale/Revenge resta l'unico a usare il bypass prima di `Kill`. Nessun ramo o cleanup Try Your Luck può impostare gravità, avviare/fermare il throttle trasformato o scrivere toggle/cursori Ghost/Fly. Morte e timeout annullano timestamp, status dell'esito, modificatori temporanei ed effetti senza cancellare modalità/cursore Unkillable. Il tracker `PahlawanTerakhir` deve rilevare il cambio eroe umano nel scheduler globale a 10 Hz, ripulire Try Your Luck e riaprire il menu quando necessario. Cambio squadra e leave/rejoin eseguono cleanup e setup fresco. Un loop o Wait per-player associato alla roulette è vietato.

Le sei icone devono usare `Visible To and Position`: il pubblico rivaluta l'intero roster umano quando cambia, mentre la posizione `Update Every Frame` segue occhio e mirino dell'identità catturata con `Evaluate Once`. L'indicatore off-screen resta attivo, i bot non diventano viewer e la posizione non può leggere direttamente lo scratch globale dopo la creazione. `Start Accelerating` deve usare `Facing Direction Of(Evaluate Once(player))` con `Direction Rate and Max Speed`, così soltanto l'identità è stabile mentre la direzione completa della visuale resta dinamica per tutti i 10 secondi; throttle, input richiesto e impulsi ripetuti sono vietati.

Le tre IWT di inspection, Vision e Teleport devono mantenere icona eroe, nome e salute dentro un unico `Custom String`. Il secondo argomento di posizione deve essere un solo `Update Every Frame` esterno che racchiude esattamente `Eye Position(Evaluate Once(identity)) + Vector(0, 0.450, 0)`; al suo interno deve quindi esistere un solo `Evaluate Once`, applicato esclusivamente all'identità prevista per quella targhetta. La reevaluation deve restare esattamente `Visible To Position String and Color`, così testo, colore, posizione e destinatari continuano ad aggiornarsi senza permettere all'handle di cambiare soggetto.

### Lifecycle

Il gate controlla:

- guardia anti-duplicato prima della registrazione roster;
- rifiuto di `Null` e nome visibile vuoto prima di allocare uno slot roster, con rilascio del lock e retry timestamp;
- un solo setup e un solo set di handle per player;
- secondo cambio squadra durante il setup in coda: riallineamento di `TimSiklusTarget`, nuovo retry individuale a `+0,25 s`, rilascio della sola prenotazione del player e nuova acquisizione solo dopo entrambe le scadenze globale e individuale; nessuna prenotazione trattenuta da un player non spawned;
- chiusura menu canonica prima del fallback locale: `TutupMenu` distrugge l'handle registrato anche con `HudMenu == Null` e non distrugge due volte un handle condiviso dalle due copie;
- cleanup completo su leave;
- cambio squadra di un umano registrato implementato come reset completo nella regola `01a - Siklus tim: Reset penuh pada konteks pemain`, `Ongoing - Each Player`: il detector mismatch richiama `TenangkanPemain` prima di `BersihkanPemain` con il giusto `Event Player`, distrugge gli handle dagli array canonici prima di liberare lo slot, azzera i latch lifecycle e programma il retry a 0,25 s senza `Wait`, `Abort` o dipendenza da `Server Load`; scheduler e `01b` riaccodano poi la nuova entità al classifier/setup;
- renderer roster privo del gate `Is Alive`, flag ready scritto solo dopo entrambi gli handle, menu distrutto tramite l'array globale canonico e classifier che, quando manca temporaneamente uno slot, riarma il lifecycle, rilascia il proprio lock globale e programma il retry dopo 0,25 secondi; il renderer roster deve restare inline nella stessa regola `02` del classifier (nessuna seconda `Ongoing - Each Player` dedicata alla creazione di `HudKiri`/`HudKanan`);
- filtri pubblici Crouch che richiedono sempre `SegarkanRosterTertunda == False`, così target non stabili non restano agganciati agli In-World Text;
- assenza del vecchio worker/consumer pending dedicato: il team-switch non usa più il modello pending leggero;
- cambio squadra e leave/rejoin passano da setup fresco: preferenze e cursori tornano ai default;
- repair del profilo `งูแท้`: `Caladan Brood` viene sempre riasserito, mentre Silver Mist/Poison 2 tornano ai default soltanto quando `PernahDisiapkan` segnala un reset reale;
- cambio squadra non deve conservare Camera, status, effetti o voti attivi: il reset completo deve fermare lo stato engine prima del nuovo setup e liberare ogni riferimento owner-scoped; le subroutine locali di cleanup non possono essere chiamate dal contesto globale dello scheduler;
- rimozione di riferimenti stale in Camera, Revenge, Vote, Teleport e inspection durante il cleanup di un leave vero;
- azzeramento owner-scoped di ogni `PemainDipilih` che punta al vero leaver prima della rimozione roster, seguito dal ricalcolo dei voti;
- Revenge armata senza decremento al click, claimant univoco, retry globale e consumo del debito soltanto alla morte completa con attacker coincidente;
- ordine atomico delle operazioni sensibili, lock lifecycle globale esclusivo per il setup iniziale e rilascio dei latch; il detector individuale del team switch non acquisisce quel lock;
- cleanup per identità esatta di HUD, In-World Text, effetti e slot sul leave vero dopo la guardia di 0,5 s, senza reset engine del leaver né fallback verso il nuovo occupante dello slot;
- profilo del nome visibile esatto `งูแท้`: default `Silver Mist` e `Poison 2` modificabili, Player Vibes `Caladan Brood` fisso, Soundtrack read-only, catalogo globale ancora di 100 generi, nessun match per nomi diversi e limitazione degli omonimi esatti esplicitamente coperta;
- Privacy iniziale OFF con cursore coerente, esclusione degli umani che attivano Privacy ON da Camera custom, inspection e Teleport, sgancio degli osservatori già attivi; Vision deve invece includere tutti gli umani, usare il nome roster stabile e non sovrapporre HUD Crouch; le tre IWT inspection/Vision/Teleport conservano testo unico icona/nome/salute, posizione interamente `Update Every Frame`, sola identità catturata con `Evaluate Once` e reevaluation completa;
- dummy e bot AI confinati al percorso di classificazione/lock dedicato, senza roster, HUD, menu, input o funzioni player; il leave di un iBot può soltanto distruggere e azzerare il proprio IWT Vision prima di abortire il lifecycle umano;
- massimo un dummy per squadra, creazione soltanto con almeno due slot liberi e Spawn Point valido, rimozione quando la squadra è piena e nessun ciclo di creazione ripetuta vicino al limite;
- uscita dummy stabilizzata da un timestamp di 1 secondo, respawn massimo 3 secondi e riarmo alla morte/respawn e ripianificato dopo ogni tentativo non riuscito.
- velocità bot/dummy esattamente al 20%; il dummy nativo mantiene esplicitamente la collisione con player/bot e disabilita soltanto le collisioni ambientali con `Include Floors = False`, mentre gli iBot mantengono tutte le collisioni native;
- `KunciBot` mantiene `Damage Received = 100` e `Knockback Received = 100`, senza disabilitare la collisione con player; i modificatori offensivi restano a zero;
- filtro di movimento identico in condition, facing, throttle e cleanup: soltanto umani registrati (`Manusia`), spawned, vivi, della squadra opposta e con Dummy Follow ON; il target viene ordinato per distanza, il throttle `Forward` rivalutato vale `0` entro 4 m e `1` oltre la soglia, con stop obbligatorio su opt-out/assenza target, morte completa e rimozione;
- ownership Dummy Follow limitata al default setup OFF, all'applicazione della pagina 12 e all'eventuale quiete lifecycle OFF; Camera e altri latch non possono scrivere la preferenza.
- ownership Ghost/Fly limitata al setup/cleanup reale, all'applicazione della pagina 13 e alla manutenzione fisica dedicata; il cambio squadra deve azzerare i toggle tramite cleanup/setup completo.
- Crouch Travel & Attach composto da cinque pagine — Teleport: Spawn Room, Teleport: Active Objective, Teleport: Player / Bot, Attach: Player / Bot e Self Elimination — con copia ordinata e localizzata EN/ID/TH, binding dinamici, un solo HUD/cursore per-player e palette mint → cyan → blu → viola → rosa (istruzioni pastello, contenuto neon). Primary/Secondary restano riservati alla navigazione e Interact all'esecuzione; Self Elimination usa un timestamp per-player, arma esattamente `+3` secondi prima di `Kill`, rifiuta lo spam durante la finestra e non viene azzerato dalla morte; cambio squadra e leave/rejoin lo reinizializzano nel setup fresco.

### Otto modalità

Il sorgente e la documentazione devono coprire esplicitamente:

1. Push;
2. Flashpoint;
3. Capture the Flag;
4. Control;
5. Clash;
6. Hybrid;
7. Escort;
8. Assault.

Il gate controlla il routing Teleport: Payload per Escort/Hybrid, flag nemica per CTF, proxy/fallback per Push e Objective Position per Flashpoint/Control/Clash/Assault. Sono vietate azioni custom che assegnano punti o vincitore al posto della modalità nativa.

## Test negativi

La suite crea mutazioni isolate e richiede il fallimento del validatore per almeno queste famiglie:

- traduzione o ramo lingua mancante;
- placeholder EN/ID/TH non allineati;
- Header diverso da `Null`, `Big Message` o secondo handle menu;
- preload/HUD nascosto reintrodotto;
- input menu senza Crouch, Camera bloccata a menu aperto o Camera attivabile con Crouch premuto;
- ciclo Main Menu diverso da `0..13`, tail dinamica `12 ? Dummy Follow : Ghost/Fly` assente o duplicata, router principale scelto staticamente dal cursore, pagina 12 priva di renderer/cursore/apply/tinta, pagina 13 priva di una lingua/toggle/applicazione/tinta, writer Dummy Follow o Ghost/Fly estraneo oppure messaggio di apertura rimasto a tredici pagine in una lingua;
- latch Interact non impostato dal menu o non consultato prima di un nuovo comando menu/Camera;
- Jump tornato a `Respawn`, guardie di Menu/Crouch/Camera/Luck aggiunte, raycast vuoto assente/duplicato/spostato prima di `Resurrect`, destinazione diversa da `Nearest Walkable Position(Last Of(Position Of(Event Player)))`, snapshot `PosisiMati` o scratch `PosisiBangkitAman` riutilizzati per il Teleport, dipendenza dal validatore Travel, `Abort` o fallback Spawn Room reintrodotti, `Resurrect` condizionale/dopo Teleport/duplicato, Teleport assente/fuori dal vuoto/duplicato, forcing/offset casuale/`Wait`/`Loop` reintrodotti, normalizzazione Ghost/Fly alla morte incompleta, conferma `Is Alive` rimossa, messaggio “Resurrect unavailable” reintrodotto, latch riarmato durante lo stesso hold o regola di rilascio Jump assente/non isolata dai bot;
- FULL HP privo di una voce della tripletta danni/urti/collisione, protezione zero posseduta da un ramo estraneo, ripristino `100/100/collisione ON` mancante in una delle uscite, oppure Try Your Luck che cancella modalità/cursore/status/icona;
- promemoria Crouch globale reintrodotto, istruzione menu rimossa o newline/gap iniziale reintrodotto;
- icona roulette senza `Visible To and Position`, senza posizione `Update Every Frame`, con identità catturata nel punto sbagliato, legata allo scratch globale nudo, invisibile ai nuovi umani del roster o resa visibile ai bot;
- Acceleration di Luck senza `Facing Direction Of(Evaluate Once(player))` o `Direction Rate and Max Speed`, legata al player scratch corrente, con direzione congelata, throttle/input richiesto o `Apply Impulse` reintrodotto nel ramo Luck; Try Your Luck che imposta gravità o trasforma il throttle di Fly;
- Ghost che include i pavimenti o altera la collisione con player; Fly senza motore esplicito a 20 Hz, gravità e movimento nativo zero, formula 3D forward-pitch/back-strafe orizzontale, normalizzazione analogica, delta esatto world o isolamento per-player; `Start Transforming Throttle` reintrodotto, rampa diversa da `5,5 → 27,5 m/s` / `100% → 500%` in 25 secondi, progressione attivata da diagonale/strafe/indietro, reset `100%` o ripristino OFF assenti, `Start Accelerating`/`Stop Accelerating` nel motore Fly, impulsi o blocco del movimento durante Luck Acceleration, toggle Ghost/Fly azzerati da morte/cambio eroe oppure non azzerati dal team-switch;
- Privacy default diverso da OFF, target con Privacy ON selezionabile o visibile in Camera/inspection/Teleport, osservatore non sganciato, Vision che filtra un umano privato, usa il token nome instabile, è priva di icona/nome/salute o sovrappone HUD Crouch; una delle tre IWT che separa icona/nome/salute, altera l'ancoraggio `Eye Position + Vector(0, 0.450, 0)`, rivaluta soltanto una parte della posizione, cattura più dell'identità o perde `Visible To Position String and Color`;
- guardia bot/dummy rimossa da lifecycle, UI, Anran o Try Your Luck;
- dummy creato con meno di due slot liberi, non rimosso a team pieno, ricreato in loop o stabilizzato con un nuovo `Wait` invece del timestamp;
- velocità bot/dummy diversa dal 20%, danni/urti ricevuti diversi da 100, collisione player disabilitata, collisione ambientale applicata agli iBot o con `Include Floors = True`, target non umano/non opt-in/alleato accettato, uno dei quattro filtri divergente, soglia dei 4 m alterata, throttle automatico assente/non rivalutato o cleanup facing/throttle incompleto;
- slot HUD fisso, roster, menu o effetto fuori dalla griglia di riferimento, spaziatore finale Right rimosso, oppure diagnostica riportata nel campo Text con il fallback `Null` che genera `0` nel client;
- dichiarazione, riferimento, regola o subroutine inutilizzata/duplicata;
- parentesi mancante o in eccesso in una chiamata annidata, inclusi i quattro filtri Privacy target-aware;
- secondo Loop, Wait fuori allowlist o yield nella scansione scheduler;
- secondo `Start Camera`, chiamata fuori da `MulaiKamera`, vettore non per-frame, `Blend Speed` diverso da 0, ingresso personale/watch/toggle non condiviso o secondo raycast Camera;
- esito/durata Try Your Luck mancante, vecchio percorso binario, Skull intermedio capace di armare la morte, Skull finale senza retry/deadline, Burning che non sospende Unkillable/Damage Received per tutti i 10 secondi, riapplica la protezione fra i tick, modifica Mode/Kursor o non la ripristina al termine, icona non ricreata dopo Resurrect, cleanup eseguito prima della morte completa oppure cambio eroe non gestito dal lifecycle globale;
- Revenge con `Kill`/decremento al click, indice debito cached, claimant non coincidente con l'attacker, pending non ripulito su timeout/leave oppure pending perso/duplicato durante cambio squadra;
- guardia Join, filtro nome `Null`/vuoto, cleanup Leave o cleanup team-switch rimossi, chiamata di cleanup `Event Player` dal contesto globale, perdita degli handle canonici prima della distruzione o mancato stop engine prima del nuovo setup, voti verso il leaver non ripuliti, oppure default non riapplicati dopo cambio squadra o vero rejoin;
- profilo `งูแท้` assente o applicato a un nome diverso, default colore/icona non modificabili, Vibes modificabile dalla pagina Soundtrack, `Caladan Brood` aggiunto al catalogo globale o conteggio generi diverso da 100;
- Crouch Travel & Attach con meno di cinque pagine, copia EN/ID/TH mancante o non specifica, binding hard-coded, palette pastello/neon incompleta, cursore condiviso, Self Elimination assente o priva del cooldown per-player di 3 secondi, Primary/Secondary capaci di eseguire un'azione oppure Interact incapace di eseguire la pagina attiva;
- una delle otto modalità o un ramo Teleport mancante;
- divergenza canonica tra clipboard `it-IT` e fixture `en-US` anche quando il numero totale di regole resta uguale;
- workflow di scrittura, automazione di commit, marker, trigger o patcher one-shot reintrodotto sotto `.github`.

Ogni mutazione deve fallire per la propria causa, così il test evita un falso positivo dovuto a un'altra invariante già rotta.

## Limiti della validazione statica

Il parser testuale non può certificare:

- importazione reale nel client;
- Element Count compilato e dimensione Largest Rule;
- fluidità a 12 slot e input simultanei;
- layout effettivo EN/ID/TH e glifi Thai;
- comportamento su D.Mon o sulle mappe modificate;
- leak osservabili soltanto tramite Text Count ed Entity Count;
- interferenze con Team Status Indicator.

Il gate statico non sostituisce queste verifiche client. Per la 0.8.1 la matrice live resta da completare e documentare; i valori numerici non forniti non vengono ricostruiti nel rapporto.

## Contesto patch

La [patch del 19 agosto 2026](https://overwatch.blizzard.com/en-us/news/patch-notes/live/2026/08/#patch-2026-08-19) non elenca modifiche Workshop, ma richiede un nuovo import e invalida i replay precedenti. La [patch dell'11 agosto 2026](https://overwatch.blizzard.com/en-us/news/patch-notes/live/2026/08/#patch-2026-08-11) introduce D.Mon, il nuovo Team Status Indicator e modifiche a Busan, Eichenwalde e Paraíso; questi casi hanno priorità nel test live.

## Gate live da completare

La matrice completa è in [`TEST.md`](TEST.md). I criteri obbligatori includono:

- import e D.Mon smoke test;
- 14 menu e input in EN/ID/TH, incluse pagina 12 Dummy Follow e pagina 13 Ghost Mode / Fly;
- profilo `งูแท้`, inclusi default modificabili, Vibes bloccato e Soundtrack read-only;
- cinque pagine Crouch Travel & Attach con copia ordinata EN/ID/TH, binding reali, palette pastello/neon per pagina, Primary/Secondary per navigare e Interact per eseguire;
- Ghost/Fly indipendenti: collisioni, volo 3D con yaw cardinali e pitch fino a ±90°, baseline uniforme `5,5 m/s` e rampa Forward pura fino a `27,5 m/s` / `500%` in 25 secondi, reset diagonal/side/back/release, analogico, hover/ripristino, due player indipendenti, fluidità/ergonomia e priorità totale Try Your Luck;
- Self Kill con cooldown per-player di 3 secondi;
- morte/Resurrect con Jump nello stesso punto su terreno e Teleport post-resurrezione nel vuoto verso `Nearest Walkable Position(Last Of(Position Of(Event Player)))`, inclusi Self Kill con Crouch aperto, retry latch, hero swap, spectator, join/leave e team switch;
- Burning 5% Max Health ogni secondo per 10 secondi, con sospensione e ripristino Unkillable corretti;
- respawn dummy entro 3 secondi;
- 20 cambi squadra singoli, 10 transizioni simultanee e cascata full-lobby, inclusi doppi cambi rapidi con menu, Camera, Luck e Fly attivi;
- leave/new join a 12 slot con identità diverse, guardia ritardata di 0,5 s, assenza di handle persi e isolamento di menu, timer e fisica di un secondo player;
- tutte le otto modalità;
- soak minimo 30 minuti a 12 slot;
- Element Count `< 32.768` con obiettivo `≤ 26.000`;
- Largest Rule `< 98 KB` con obiettivo `≤ 80 KB`;
- Text Count ed Entity Count di ritorno al baseline;
- nessuna crescita di HUD/IWT/effects e nessun conflitto con Team Status Indicator.

## Decisione

La versione 0.8.1 resta **static-ready / live-pending**: i gate repository devono risultare verdi sul commit finale, ma la matrice nel client e i relativi valori diagnostici non sono ancora documentati come completati. Il vecchio Fly basato sul movimento nativo aveva fallito il test utente su più eroi; il motore a impulsi successivo ha invece ricevuto conferma di funzionamento. Quella conferma non copre la nuova revisione della base strafe e del cleanup cambio squadra, che resta live-pending. I test numerici devono interpretare la formula effettiva del sorgente, compreso l'ordine del prodotto vettoriale, invece di assumere una formula precedente; non certificano comunque la fisica engine. La motivazione tecnica e le fonti primarie sono in [`PROGETTO.md`](PROGETTO.md), la matrice da compilare in [`TEST.md`](TEST.md). Non viene dichiarato alcun tag finale per questa versione; il branch `archive/0.6.23-before-rebuild` conserva separatamente la storia divergente utile.

- UX messaggi/Travel: il gate vieta le conferme Small Message ridondanti selezionate e richiede per Crouch Travel la chase `WarnaMenu` da 0,18 s, i cinque target cromatici e `Visible To String and Color`.
