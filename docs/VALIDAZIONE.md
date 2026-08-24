# Rapporto di validazione — versione 0.8.0

Data: 2026-08-20

Release tecnica: **CHILL Dedicated Server 0.8.0**

Stato: **static-ready / live-pending**

Il gate 0.8.0 analizza il significato e la struttura del sorgente Workshop. Non usa un hash dell'intero file: modifiche lecite di spaziatura o documentazione non invalidano il rilascio, mentre una mutazione che viola un'invariante deve fallire con un messaggio mirato.

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
- 12 menu e tutte le pagine operative;
- 37 nomi Player Icon in tre array allineati;
- 26 località server in tre array allineati;
- equivalenza di placeholder e argomenti tra le traduzioni;
- minuti roster `MIN / MENIT / นาที`;
- riga vuota coerente tra contenuto e comandi.
- promemoria del modificatore presente nei menu ma non duplicato nell'HUD globale, senza newline iniziale superfluo.

I 100 generi restano nomi internazionali e non richiedono traduzione.

### HUD e rendering

Ogni azione `Create HUD Text` deve:

- avere Header `Null`;
- usare soltanto Subheader/Text;
- registrare l'handle previsto per il cleanup.

Sono vietati `Big Message`, titoli HUD, preload, pagine nascoste e più di un handle Menu Arcade attivo per player. `Small Message` e gli In-World Text di inspection, Teleport e Vision restano ammessi. Il gate richiede esattamente dieci HUD fissi negli slot Top `0/1/2`, Left `-2/-1/0` e Right `-16/-15/-14/-1`; i roster usano rispettivamente `1 + UrutanHUD` e `-13 + UrutanHUD`. Menu, Teleport ed effetto Try Your Luck condividono `Top 3` senza newline iniziali artificiali.

Il gate controlla che il menu venga ricreato soltanto ad apertura, chiusura o cambio pagina; navigazione e applicazioni sulla stessa pagina devono usare valori rivalutati.

### Input

Le regole avanti/indietro e `±10` devono essere simmetriche. Il validatore richiede:

- hold Melee 0,5 s per apertura/chiusura;
- Crouch come modificatore di Primary, Secondary, Interact, Reload e Ability 1/2 a menu aperto;
- nessuna disabilitazione custom di Melee o Jump da vivi;
- Camera con Interact 0,5 s a menu aperto o chiuso, ma soltanto con Crouch rilasciato;
- latch Interact condiviso tra menu e Camera, consumato da un solo sistema fino al rilascio;
- inspection e Teleport soltanto a menu chiuso e da vivi;
- menu congelato da morti e Jump come unico input custom di respawn; posizione e prompt vengono registrati soltanto con `Is Alive == False`;
- latch rilasciati senza doppie attivazioni.

### Scheduler e prestazioni statiche

Il gate richiede:

- un solo scheduler `Ongoing - Global` a 20 Hz;
- un solo `Loop` nel sorgente;
- massimo 10 `Wait`, ognuno in una categoria consentita e riconoscibile;
- subroutine scheduler senza `Wait`;
- nessun yield durante una scansione del roster;
- proprietà esclusiva dello scratch player/indice globale allo scheduler;
- attività 20 Hz, 10 Hz, 1 Hz e minuti ogni 10 secondi;
- `Ongoing - Each Player` limitato a input, latch, classificazione one-shot e rendering individuale;
- un solo raycast Camera;
- nessuna regola HUD contenente `Wait` o `Loop`.

Le categorie Wait autorizzabili sono: tick scheduler, ordinamento atomico join/leave, classificazione bot, hold input, respawn e cleanup atomico. La stabilizzazione dell'uscita dummy dalla Spawn Room usa una scadenza timestamp di 1 secondo e non appartiene all'allowlist `Wait`. Qualsiasi Wait fuori allowlist, un undicesimo `Wait` o un secondo Loop fa fallire il gate.

### Try Your Luck

Il validatore riconosce una macchina a stati con timestamp e sei esiti, non il vecchio percorso binario:

| Esito | Invariante |
|---|---|
| Vision | durata 15 s, IWT con icona/nome/salute live e blocco/cleanup di inspection e Teleport Crouch |
| Acceleration | durata 10 s e propulsione automatica 3D guidata dalla mira, senza dipendenza dal throttle |
| Skull | trigger soltanto sull'esito finale armato, retry globale ogni 0,25 s fino a `Is Alive == False`, con deadline anti-blocco di 5 s |
| Team Heal | cura completa dei soli player umani del team |
| Burning | 5% max HP al secondo per 10 s, implementato come 2,5% ogni 0,5 s |
| Hacked | durata 5 s e cleanup status |

L'avvio disattiva Unkillable. Morte, leave e cambio squadra devono annullare timestamp, status, modificatori ed effetti. Un loop o Wait per-player associato alla roulette è vietato.

Le sei icone devono usare `Visible To and Position`: il pubblico rivaluta l'intero roster umano quando cambia, mentre la posizione `Update Every Frame` segue occhio e mirino dell'identità catturata con `Evaluate Once`. L'indicatore off-screen resta attivo, i bot non diventano viewer e la posizione non può leggere direttamente lo scratch globale dopo la creazione. `Start Accelerating` deve usare `Facing Direction Of(Evaluate Once(player))` con `Direction Rate and Max Speed`, così soltanto l'identità è stabile mentre la direzione completa della visuale resta dinamica per tutti i 10 secondi; throttle, input richiesto e impulsi ripetuti sono vietati.

### Lifecycle

Il gate controlla:

- guardia anti-duplicato prima della registrazione roster;
- un solo setup e un solo set di handle per player;
- cleanup completo su leave;
- cambio squadra implementato come cleanup + setup fresco;
- reset completo delle preferenze dopo il cambio squadra;
- rimozione di riferimenti stale in Camera, Revenge, Vote, Teleport e inspection;
- Revenge armata senza decremento al click, claimant univoco, retry globale e consumo del debito soltanto alla morte completa con attacker coincidente;
- ordine atomico delle operazioni sensibili e rilascio dei latch;
- cleanup di HUD, In-World Text, effetti, status e slot.
- Privacy iniziale OFF con cursore coerente, esclusione degli umani privati dalla Camera custom, sgancio degli osservatori già attivi, assenza di nome/nameplate privato in inspection e nessun HUD Crouch sovrapposto durante Vision;
- dummy e bot AI confinati al percorso di classificazione/lock dedicato, senza roster, HUD, menu, input o funzioni player; il leave di un iBot può soltanto distruggere e azzerare il proprio IWT Vision prima di abortire il lifecycle umano;
- massimo un dummy per squadra, creazione soltanto con almeno due slot liberi e Spawn Point valido, rimozione quando la squadra è piena e nessun ciclo di creazione ripetuta vicino al limite;
- uscita dummy stabilizzata da un timestamp di 1 secondo, riarmato alla morte/respawn e ripianificato dopo ogni tentativo non riuscito.
- velocità bot/dummy esattamente al 20%; soltanto il dummy nativo disabilita le collisioni ambientali con `Include Floors = False`, mentre gli iBot mantengono le collisioni native;
- filtro di movimento limitato agli umani vivi della squadra opposta, throttle `Forward` rivalutato con magnitudine `0` entro 4 m e `1` oltre la soglia, più stop obbligatorio su assenza target, morte completa e rimozione; de-mech/transizioni ancora vive non possono eseguire lo stop terminale.

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
- latch Interact non impostato dal menu o non consultato prima di un nuovo comando menu/Camera;
- promemoria Crouch globale reintrodotto, istruzione menu rimossa o newline/gap iniziale reintrodotto;
- icona roulette senza `Visible To and Position`, senza posizione `Update Every Frame`, con identità catturata nel punto sbagliato, legata allo scratch globale nudo, invisibile ai nuovi umani del roster o resa visibile ai bot;
- accelerazione senza `Facing Direction Of(Evaluate Once(player))` o `Direction Rate and Max Speed`, legata al player scratch corrente, con direzione congelata, throttle/input richiesto o `Apply Impulse` reintrodotto;
- Privacy default OFF, target privato selezionabile, osservatore non sganciato, Vision priva di icona/nome/salute o HUD Crouch sovrapposto durante Vision;
- guardia bot/dummy rimossa da lifecycle, UI, Anran o Try Your Luck;
- dummy creato con meno di due slot liberi, non rimosso a team pieno, ricreato in loop o stabilizzato con un nuovo `Wait` invece del timestamp;
- velocità bot/dummy diversa dal 20%, collisione ambientale applicata agli iBot o con `Include Floors = True`, target alleato accettato, soglia dei 4 m alterata, throttle automatico assente/non rivalutato o cleanup facing/throttle incompleto;
- slot HUD fisso, roster, menu o effetto fuori dalla griglia di riferimento, spaziatore finale Right rimosso, oppure diagnostica riportata nel campo Text con il fallback `Null` che genera `0` nel client;
- dichiarazione, riferimento, regola o subroutine inutilizzata/duplicata;
- parentesi mancante o in eccesso in una chiamata annidata, inclusi i quattro filtri Privacy target-aware;
- secondo Loop, Wait fuori allowlist o yield nella scansione scheduler;
- secondo raycast Camera;
- esito/durata Try Your Luck mancante, vecchio percorso binario, Skull intermedio capace di armare la morte, Skull finale senza retry/deadline o cleanup eseguito prima della morte completa;
- Revenge con `Kill`/decremento al click, indice debito cached, claimant non coincidente con l'attacker o pending non ripulito su timeout/leave/team switch;
- guardia Join, cleanup Leave o reset team-switch rimosso;
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

Per questo la release resta `live-pending` anche con gate verde.

## Contesto patch

La [patch del 19 agosto 2026](https://overwatch.blizzard.com/en-us/news/patch-notes/live/2026/08/#patch-2026-08-19) non elenca modifiche Workshop, ma richiede un nuovo import e invalida i replay precedenti. La [patch dell'11 agosto 2026](https://overwatch.blizzard.com/en-us/news/patch-notes/live/2026/08/#patch-2026-08-11) introduce D.Mon, il nuovo Team Status Indicator e modifiche a Busan, Eichenwalde e Paraíso; questi casi hanno priorità nel test live.

## Gate live ancora aperto

La matrice completa è in [`TEST.md`](TEST.md). I criteri obbligatori includono:

- import e D.Mon smoke test;
- 12 menu e input in EN/ID/TH;
- morte/respawn, hero swap, spectator, join/leave e team switch;
- 20 cambi squadra singoli, 10 transizioni simultanee e cascata full-lobby;
- tutte le otto modalità;
- soak minimo 30 minuti a 12 slot;
- Element Count `< 32.768` con obiettivo `≤ 26.000`;
- Largest Rule `< 98 KB` con obiettivo `≤ 80 KB`;
- Text Count ed Entity Count di ritorno al baseline;
- nessuna crescita di HUD/IWT/effects e nessun conflitto con Team Status Indicator.

## Decisione

La versione 0.8.0 è **static-ready / live-pending**: il repository può essere pubblicato come candidata statica dopo unit test e validatore verdi. Il tag finale `v0.8.0` e la dicitura **live-ready** restano sospesi finché i risultati client non vengono registrati e ogni eventuale correzione non supera nuovamente entrambi i gate.
