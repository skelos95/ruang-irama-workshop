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

Il workflow `.github/workflows/validate-workshop.yml` esegue gli stessi comandi con Python 3.12, sola standard library e permesso GitHub `contents: read`. È l'unico workflow permanente. `maintenance-patch.yml` è stato rimosso: la validazione non modifica, non committa e non pubblica file.

## Gate semantici

### Struttura e riferimenti

Il validatore controlla:

- delimitatori e blocchi Workshop completi;
- indici compatti e dichiarazioni univoche per global, player e subroutine;
- nomi global, player e subroutine lunghi al massimo 32 byte in UTF-8, per evitare il rifiuto dell'import da parte del client;
- ogni riferimento risolto alla relativa dichiarazione;
- nessuna variabile soltanto dichiarata, inizializzata o pulita;
- nessuna regola o subroutine inutilizzata o duplicata;
- ogni player variable inizializzata nel setup e ripulita dove necessario;
- assenza della vecchia roulette binaria e degli handle di preload.

Non esiste una lista rigida dell'intero blob: le invarianti vengono ricavate dai blocchi e dalle azioni effettive.

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

I 100 generi restano nomi internazionali e non richiedono traduzione.

### HUD e rendering

Ogni azione `Create HUD Text` deve:

- avere Header `Null`;
- usare soltanto Subheader/Text;
- registrare l'handle previsto per il cleanup.

Sono vietati `Big Message`, titoli HUD, preload, pagine nascoste e più di un handle Menu Arcade attivo per player. `Small Message` e gli In-World Text di inspection, Teleport e Vision restano ammessi.

Il gate controlla che il menu venga ricreato soltanto ad apertura, chiusura o cambio pagina; navigazione e applicazioni sulla stessa pagina devono usare valori rivalutati.

### Input

Le regole avanti/indietro e `±10` devono essere simmetriche. Il validatore richiede:

- hold Melee 0,5 s per apertura/chiusura;
- Crouch come modificatore di Primary, Secondary, Interact, Reload e Ability 1/2 a menu aperto;
- nessuna disabilitazione custom di Melee o Jump da vivi;
- Camera con Interact 0,5 s soltanto a menu chiuso;
- inspection e Teleport soltanto a menu chiuso e da vivi;
- menu congelato da morti e Jump come unico input custom di respawn;
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

Le categorie Wait autorizzabili sono: tick scheduler, ordinamento atomico join/leave, classificazione bot, hold input, respawn e cleanup atomico. Qualsiasi Wait fuori allowlist o secondo Loop fa fallire il gate.

### Try Your Luck

Il validatore riconosce una macchina a stati con timestamp e sei esiti, non il vecchio percorso binario:

| Esito | Invariante |
|---|---|
| Vision | durata 15 s e cleanup effetto/IWT |
| Acceleration | durata 10 s e controllo guidato dalla mira |
| Skull | morte immediata |
| Team Heal | cura completa del team |
| Burning | 5% max HP al secondo per 10 s, implementato come 2,5% ogni 0,5 s |
| Hacked | durata 5 s e cleanup status |

L'avvio disattiva Unkillable. Morte, leave e cambio squadra devono annullare timestamp, status, modificatori ed effetti. Un loop o Wait per-player associato alla roulette è vietato.

### Lifecycle

Il gate controlla:

- guardia anti-duplicato prima della registrazione roster;
- un solo setup e un solo set di handle per player;
- cleanup completo su leave;
- cambio squadra implementato come cleanup + setup fresco;
- reset completo delle preferenze dopo il cambio squadra;
- rimozione di riferimenti stale in Camera, Revenge, Vote, Teleport e inspection;
- ordine atomico delle operazioni sensibili e rilascio dei latch;
- cleanup di HUD, In-World Text, effetti, status e slot.

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
- input senza Crouch o Camera disponibile a menu aperto;
- dichiarazione, riferimento, regola o subroutine inutilizzata/duplicata;
- secondo Loop, Wait fuori allowlist o yield nella scansione scheduler;
- secondo raycast Camera;
- esito/durata Try Your Luck mancante o vecchio percorso binario;
- guardia Join, cleanup Leave o reset team-switch rimosso;
- una delle otto modalità o un ramo Teleport mancante;
- workflow di scrittura o automazione di commit reintrodotto.

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
