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

Main Menu usa pagina `-1`; le 13 pagine mantengono gli indici `0..12`. La pagina 12, Dummy Follow, è una preferenza per-player: ON consente al dummy avversario di scegliere quel player, OFF lo esclude; il dummy ordina sempre i target idonei per distanza. Il default è OFF, quindi senza opt-in il dummy resta fermo. Preferenze e cursori persistono durante chiusura, riapertura e cambio squadra leggero. Soltanto un leave vero seguito da rejoin crea una nuova sessione player e riapplica i default di setup.

### Input

- Tieni Melee per 0,5 s: apre o chiude il Menu Arcade.
- A menu aperto e da vivi, Crouch è il modificatore obbligatorio per Primary, Secondary, Interact, Reload e Ability 1/2.
- Primary/Secondary navigano; Interact entra o applica; Reload torna al Main Menu.
- Nel Soundtrack, Ability 1/2 eseguono `+10/−10`.
- Melee e Jump restano azioni normali dell'eroe.
- A menu aperto o chiuso, Interact tenuto per 0,5 s cambia Camera soltanto con Crouch rilasciato.
- A menu chiuso, Crouch abilita inspection e l'eventuale overlay Teleport.
- Crouch Travel & Attach contiene cinque pagine: Spawn Travel, Objective Travel, Player/Bot Travel, Player/Bot Attach e Self Kill. Primary/Secondary navigano avanti/indietro; Interact esegue la pagina attiva.
- Da morto, un menu aperto resta visibile ma congelato; soltanto Jump esegue `Resurrect`. Resurrect, teleport alla posizione sicura e guardia `Is Alive == True` avvengono nello stesso tick senza `Wait`; effetto e feedback vengono emessi soltanto in caso di successo. Se il player è ancora morto, una regola separata riapre il latch esclusivamente al rilascio di Jump.

Le condizioni e il modificatore sono parte del contratto: `Crouch + Interact` alimenta il menu, `Interact` senza Crouch alimenta la Camera, mentre inspection e Teleport richiedono Crouch e menu chiuso. Menu e Camera condividono un latch consumabile: dopo che uno dei due usa `Interact`, soltanto il rilascio fisico del pulsante riabilita entrambi.

## Scheduler globale

Un'unica regola `Ongoing - Global` mantiene il ritmo base a 20 Hz. Dopo ciascun tick incrementa un contatore e delega a subroutine senza `Wait`:

| Frequenza | Responsabilità |
|---:|---|
| 20 Hz | controlli rapidi, retry morte completa Revenge/Skull e avanzamento Try Your Luck |
| 10 Hz | lifecycle reattivo, RGB e refresh visivi |
| 1 Hz | countdown e cache passive |
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

Il ciclo del Main Menu è esattamente modulo 13; pagina 12 dispone di cursore OFF/ON separato dallo stato applicato, renderer EN/ID/TH e tinta dedicata. Soltanto setup, applicazione della pagina e quiete lifecycle possono scrivere la preferenza Dummy Follow, impedendo che Camera o altri latch la modifichino accidentalmente.

### Profilo per nome visibile

Il nome visibile esatto `งูแท้` abilita un profilo dedicato durante il setup. Name Color `Silver Mist` e Player Icon `Poison 2` sono default iniziali e restano modificabili dal player; Player Vibes è invece fissato a `Caladan Brood`, perciò la pagina Soundtrack è visibile ma read-only e nessun input può modificarne il valore. `Caladan Brood` è una voce dedicata al profilo e non entra nel catalogo globale, che resta di 100 generi per i player generici.

Il matching usa esclusivamente il nome visibile, non un identificatore account: due omonimi esatti ricevono lo stesso profilo, mentre una rinomina non viene riconosciuta. Il cambio squadra leggero conserva colore e icona eventualmente scelti e mantiene il Vibes bloccato; un leave vero seguito da rejoin esegue nuovamente il setup e riapplica `Silver Mist`, `Poison 2` e `Caladan Brood`.

Tutti i menu seguono lo stesso layout:

```text
contenuto e stato

comandi disponibili
```

I placeholder devono avere stessa cardinalità nei tre rami linguistici.

## Unkillable FULL HP

FULL HP è uno stato composto e indivisibile: `Damage Received = 0`, `Knockback Received = 0` e `Disable Movement Collision With Players`. Sia l'applicazione dal menu sia il tick globale riapplicano la stessa tripletta. OFF, modalità 1 HP, setup fresco e cleanup di un leave vero ripristinano rispettivamente `100`, `100` e `Enable Movement Collision With Players`; una protezione parziale è vietata. Un cambio squadra leggero non ricostruisce lo stato engine. Try Your Luck non modifica modalità o cursore Unkillable: Vision, Acceleration, Team Heal e Hacked conservano la tripletta, mentre Burning sospende status e riduzione del danno per l'intero effetto e li ripristina al termine. Un cleanup engine può normalizzare temporaneamente lo stato dopo morte o timeout, ma conserva `ModeKebal`/`KursorKebal`, ricava di nuovo `KebalAktif` dalla modalità e lascia al tick globale la riapplicazione e l'eventuale ricreazione dell'icona. Anche in Spawn Room la modalità 2 resta protetta; soltanto la modalità 1 HP usa il ramo di ripristino normale.

## Try Your Luck

Try Your Luck è una macchina a stati guidata da timestamp, non un loop per-player. All'avvio conserva Unkillable senza scrivere modalità, cursore o stato di protezione e mantiene la pagina bloccata finché la sequenza non termina.

| Esito | Durata | Comportamento |
|---|---:|---|
| Vision | 15 s | mostra icona, nome e salute live dei target consentiti e sopprime inspection/Teleport Crouch |
| Acceleration | 10 s | applica propulsione automatica lungo la direzione 3D della mira, senza input direzionali |
| Skull | immediato | unico esito che bypassa temporaneamente Unkillable e ritenta la kill fino alla morte completa; deadline 5 s impedisce un latch permanente |
| Team Heal | immediato | porta i player umani della squadra alla salute completa |
| Burning | 10 s | infligge il 5% della salute massima ogni 1 s; sospende Unkillable e normalizza Damage Received per l'intera durata, poi ripristina la modalità scelta |
| Hacked | 5 s | applica e poi rimuove Hacked |

Il tick globale valuta transizioni e scadenze. Vision, Acceleration, Team Heal e Hacked non sospendono Unkillable; Burning è l'eccezione a durata: conserva modalità e cursore ma sospende status e riduzione del danno per tutti i 10 secondi, applica il 5% della Max Health ogni secondo e ripristina la protezione al termine o nel cleanup anticipato. Soltanto lo Skull finale armato e Revenge passano invece dal bypass della macchina di morte completa. Alla morte o al timeout vengono annullati stato temporaneo, accelerazione, status dell'esito, HUD/IWT ed effetti associati, ma la preferenza Unkillable resta intatta e viene riapplicata dopo Resurrect. Un tracker eroe condiviso rileva inoltre a 10 Hz il cambio eroe umano e applica lo stesso cleanup temporaneo senza azzerare la preferenza sul player vivo e senza aggiungere un nuovo `Ongoing - Each Player`; il cambio squadra leggero conserva preferenze, cursori, Camera, status, effetti e voti, mentre un leave vero ripulisce l'entità e il successivo rejoin esegue un setup fresco. Nessun esito può lasciare un timestamp o un riferimento riutilizzabile dal player successivo nello stesso slot.

Le sei icone della roulette usano la reevaluation `Visible To and Position`. `Visible To` rivaluta il roster umano anche dopo join/leave, mentre la posizione `Update Every Frame` resta agganciata a occhio e mirino dell'identità catturata, senza seguire lo scratch `Global.PemainAktif`. L'indicatore off-screen resta abilitato e i bot non entrano mai nel pubblico.

L'accelerazione usa `Facing Direction Of(Evaluate Once(player))`: viene congelata soltanto l'identità del beneficiario, non la sua direzione corrente. `Direction Rate and Max Speed` mantiene quindi la spinta automatica davanti, in alto e in basso senza throttle o input direzionali. Il tick globale conserva soltanto avvio, timestamp e cleanup; non vengono aggiunti loop, impulsi periodici o regole per-player.

## Lifecycle player

### Join

La registrazione verifica prima l'esistenza del player nel roster. Un evento Join duplicato non aggiunge una seconda voce e non crea un secondo messaggio o handle. Il setup inizializza ogni variabile player dichiarata, assegna lo slot sociale e crea una sola coppia di HUD roster.

Dummy e bot AI seguono classificazione e lock dedicati: non vengono inseriti nel roster umano e non ricevono menu, HUD, input Arcade o funzioni riservate ai player. Possono restare target passivi di inspection, Vision e Camera dove previsto dal contratto; per gli umani, inspection, Vision e Camera rispettano sempre Privacy.

Revenge e lo Skull finale condividono l'unico percorso che bypassa temporaneamente Unkillable nel tick globale. Il comando `Kill` è centralizzato e rivalutato ogni 0,25 s finché il target è ancora vivo; non viene usato `Is In Alternate Form`, perché non identifica in modo univoco una vita intermedia. Revenge conserva invariati claimant e contabilità: ricalcola l'indice del debito al commit e decrementa soltanto su `Player Died` con `Is Alive == False` e attacker coincidente. Doppio claim, attacker diverso, timeout, leave e team switch non generano un falso conteggio. Dopo Resurrect il tick globale ripristina la modalità Unkillable selezionata e ricrea la relativa icona se il motore l'ha distrutta.

Per i dummy nativi il runtime mantiene al massimo un'istanza per Team 1 e una per Team 2. La creazione richiede almeno due slot liberi e uno Spawn Point valido; se la squadra diventa piena con il dummy presente, il bot viene rimosso per rendere disponibile il sesto posto umano. La soglia di due slot impedisce una ricreazione immediata e quindi lo spam di `Create Dummy Bot`. Il tempo massimo di respawn è 3 secondi. Quando un dummy vivo si trova nella Spawn Room, registra una scadenza di 1 secondo e, senza `Wait`, sceglie poi una destinazione coerente con la modalità e la passa sempre da `Nearest Walkable Position`; se la posizione richiesta non è valida, non viene eseguito alcun teleport e il controllo viene rivalutato al ciclo successivo. I dummy ricevono danni e urti al 100%, mantengono la collisione con player/bot e disabilitano soltanto le collisioni ambientali con `Include Floors = False`.

### Leave

Il cleanup:

1. interrompe input e sottosistemi persistenti;
2. rimuove Camera, status ed effetti engine;
3. distrugge HUD, In-World Text ed effetti posseduti;
4. libera slot e riferimenti in Camera, Revenge, Teleport, inspection e voti;
5. ricostruisce soltanto le cache condivise necessarie.

### Cambio squadra

Il cambio Team 1 ↔ Team 2 di un umano già registrato usa un refresh leggero senza flag pending dedicati. Il detector aggiorna subito i campi dipendenti dal Team, preserva `Manusia` e l'appartenenza a `PemainManusia`, riassocia lo slot globale (`PemainSlotHUD`/`NamaSlotHUD`) e ripulisce solo UI/input transitori (menu, overlay teleport, latch di comando), senza distruggere le righe roster Left/Right. Il menu viene distrutto tramite `HudMenuPemain`, non tramite un handle player-local potenzialmente resettato. Il binder `02b` resta indipendente da `Server Load` e da `Is Alive`, così il lock lifecycle non si blocca durante picchi o morti transitorie. Se la nuova entità perde temporaneamente la membership, il recovery idempotente la riaccoda al setup evitando lo stato `Manusia=False` permanente; il classifier aspetta inoltre uno slot roster libero prima di iniziare, coprendo la finestra in cui il cleanup del vecchio riferimento deve ancora concludersi. Preferenze e cursori restano invariati nel percorso reference-stable. Se il motore fornisce una nuova identità senza player variables, il fallback usa necessariamente il setup fresco e riapplica i default; Camera, status, effetti e voti attivi non sono quindi promessi in questo solo ramo di nuova identità. Il fast-path non acquisisce il lock del setup iniziale. Un leave vero esegue invece il cleanup completo e rimuove il player dal roster; il rejoin successivo passa dal setup fresco e riapplica tutti i default.

Nel caso limite senza slot, l'attesa è cooperativa: il classifier ripristina `SudahDiperiksa`, `SudahSiap` e i latch lifecycle, rilascia soltanto il proprio `PemainSiklusGlobal` e programma il tentativo successivo dopo 0,25 secondi, così gli altri player continuano a essere processati. Nel repair di un player ancora registrato, il nome esatto `งูแท้` riasserisce sempre `Caladan Brood`; Silver Mist e Poison 2 vengono riapplicati solo se `PernahDisiapkan=False`, lasciando intatte le modifiche manuali durante un normale cambio squadra.

## HUD, testi ed effetti

- `Create HUD Text` deve avere Header `Null`.
- Sono consentiti Subheader/Text, `Small Message` e gli In-World Text necessari a inspection, Teleport e Vision.
- `Big Message` e titoli HUD non sono consentiti.
- Gli handle vengono distrutti prima di essere sovrascritti; le variabili handle tornano a `Null`.
- Ogni testo operativo, stato, esito, nome icona e località ha rami EN/ID/TH.
- I 100 generi, `CHILL`, nomi player ed eroi sono nomi propri universali.
- Identificatori personalizzati, titoli regola, subroutine e commenti Workshop sono in Bahasa Indonesia; keyword native, acronimi tecnici e nomi degli eroi restano invariati.

La griglia HUD usa dieci handle globali fissi e slot dinamici separati:

| Area | Slot fissi | Slot dinamici |
|---|---|---|
| Top | titolo/timer `0`, località `1`, spaziatore `2` | menu, Teleport o effetto `3` |
| Left | comando completo `-2`, spaziatore `-1`, `LOBBY & CHILL TIME` `0` | roster/minuti `1..12` |
| Right | comando completo `-16`, spaziatore superiore `-15`, `PLAYER VIBES` `-14`, spaziatore finale `-1` | roster/musica `-13..-2` |

Titolo, label e righe roster non contengono newline usati come compensazione verticale. Il contatore diagnostico include i dieci handle fissi. La diagnostica opzionale è il terzo segmento del Subheader dell'ultima riga Left e il campo Text resta direttamente `Null`: così il client non converte un ramo `Null` tipizzato come stringa nel numero `0`.

Il nuovo Team Status Indicator del client non è riposizionabile dal Workshop. Tutto il blocco Right custom usa sort negativi e termina con uno spaziatore reale `-1`, riservando una riga dopo l'ultimo nome nell'area che precede gli elementi nativi. Il test live con 1, 6 e 12 player deve confermare il confine effettivo con indicatore e kill feed.

## Camera, inspection e Teleport

La Camera usa un solo raycast per risolvere la posizione. Target morti, non spawnati, inesistenti o umani con Privacy ON vengono rimossi; una perdita target porta a un fallback valido senza creare più Camera concorrenti. Se un target umano attiva Privacy mentre è osservato, gli osservatori custom già agganciati tornano alla visuale normale.

Inspection e Teleport sono disponibili soltanto a menu chiuso e da vivi. Durante Vision entrambi gli ingressi Crouch sono disattivati e gli handle eventualmente già aperti vengono rimossi, mentre Vision mantiene un solo IWT con icona eroe, nome e salute rivalutata per ogni soggetto consentito. Privacy è OFF per default: il player è pubblico finché non sceglie ON. Con Privacy ON, inspection, Vision e Camera custom non possono creare o mantenere nome/nameplate dell'umano; ogni handle identificativo già esistente viene ripulito all'attivazione. Questa garanzia riguarda i sistemi Workshop della modalità, non la visuale spettatore nativa riservata a lobby e amministratori.

La destinazione Teleport viene rivalutata al click:

| Modalità | Destinazione |
|---|---|
| Escort, Hybrid | Payload |
| Capture the Flag | bandiera nemica valida |
| Push | proxy valido dell'obiettivo, poi fallback Objective Position |
| Flashpoint, Control, Clash, Assault | `Objective Position(Objective Index)` |

La pagina All Players sceglie un target vivo/spawnato vicino al reticolo e rispetta Privacy; `Nearest Walkable Position` limita le destinazioni non praticabili.

La stessa matrice viene riutilizzata dalla regola di uscita Spawn dei dummy dopo la scadenza timestamp di 1 secondo: Escort/Hybrid → payload, CTF → bandiera nemica, Push → proxy/fallback obiettivo, altre modalità → obiettivo corrente. A differenza del Teleport manuale, in assenza di una destinazione valida il dummy non riceve un fallback arbitrario: resta in Spawn Room e riprova, senza introdurre un nuovo `Wait`.

## Modalità native

La logica Arcade è neutrale rispetto all'esito della partita. Non chiama azioni custom per assegnare punti, completare round o dichiarare vincitori. La verifica live attraversa tutte le otto modalità:

| Modalità | Focus |
|---|---|
| Push | proxy robot e fallback obiettivo |
| Flashpoint | indice obiettivo attivo |
| Capture the Flag | bandiera nemica |
| Control | cambio round e obiettivo |
| Clash | avanzamento tra punti |
| Hybrid | payload dopo la cattura |
| Escort | payload |
| Assault | transizione A/B |

Busan, Eichenwalde e Paraíso hanno priorità perché modificati nella patch dell'11 agosto 2026.

## Gate di prestazioni

Target statici:

- un solo `Loop` globale;
- massimo 7 `Wait`, ciascuno associato a un percorso autorizzato;
- stabilizzazione dummy a timestamp, mai tramite un ottavo `Wait`;
- un solo raycast Camera;
- nessuna regola, variabile o subroutine inutilizzata/duplicata;
- nessun loop o Wait dentro le subroutine chiamate durante una scansione scheduler;
- un solo handle HUD Arcade attivo per player;
- sorgente sotto 32.768 elementi, obiettivo massimo 26.000;
- largest rule sotto 98 KB, obiettivo massimo 80 KB.

Gli ultimi due valori devono essere letti nel client: non sono deducibili con precisione dal solo testo Workshop.

## Repository e release

Il workflow permanente `validate-workshop.yml` usa Python 3.12 e sola standard library per eseguire unit test e validatore. Il vecchio workflow `maintenance-patch.yml`, che applicava e committava patch automatiche, è stato rimosso. L'allowlist dell'intero albero `.github` ammette soltanto il workflow permanente: file marker, trigger, patcher e automazioni one-shot sono errori di validazione. In `workshop/` viene mantenuto un solo file destinato all'importazione, `ruang_irama.it-IT.workshop`; il riferimento `en-US` vive soltanto sotto `tests/fixtures/` e la sua forma canonica deve restare semanticamente equivalente al clipboard pubblico.

La release 0.8.1 resta **static-ready / live-pending**: i gate statici sono soddisfatti, ma la matrice nel client non è ancora documentata come completata e non viene dichiarato alcun tag finale. Per chiudere la regressione restano obbligatorie le prove seguenti:

- import pulito nel client del 19 agosto 2026 e smoke test D.Mon;
- matrice input/menu/localizzazione;
- stress join/leave/team switch;
- matrice sulle otto modalità, compresa l'uscita Spawn dei dummy;
- soak di almeno 30 minuti con 12 slot;
- diagnostica senza crescita progressiva di HUD, In-World Text o effetti.

La procedura completa è in [`TEST.md`](TEST.md); il gate semantico è descritto in [`VALIDAZIONE.md`](VALIDAZIONE.md).


### Dummy bot: spawn e distanza sicura

I dummy vengono creati soltanto quando esistono uno Spawn Point della squadra e almeno due slot liberi; la posizione iniziale è quello Spawn Point, non `Null`. Se il team è pieno, il dummy viene rimosso per liberare capacità e la soglia di creazione evita cicli ripetuti. L'uscita automatica dalla spawn registra un timestamp di 1 secondo, senza `Wait`, quindi cerca una posizione camminabile circa 10 m verso la propria metà mappa e rifiuta destinazioni a meno di 6 m dall'obiettivo/bandiera. Bot AI e dummy hanno velocità di movimento al 20% e restano offensivamente passivi, ma ricevono danni e urti normalmente. Soltanto il dummy Workshop disabilita la collisione con pareti e soffitti mantenendo il pavimento; la collisione con player/bot resta esplicitamente abilitata. Il filtro considera esclusivamente umani registrati, vivi, spawned, avversari e con Dummy Follow ON; `Sorted Array` sceglie sempre il più vicino e il dummy avanza in `Forward` finché la distanza è maggiore di 4 m. Lo stesso filtro governa il cleanup senza target, così opt-out, morte o team-switch non lasciano facing/throttle verso un array vuoto. La magnitudine rivalutata consente arresto e ripartenza senza nuove regole, `Wait` o `Loop`.
