# Architettura del Workshop

Questa pagina descrive il sorgente corrente. Comandi e menu sono nel [README](../README.md); storia e revisioni ritirate nel [changelog](../CHANGELOG.md).

## Sorgenti e confini

- `workshop/ruang_irama.en-US.workshop`: unico clipboard pubblico, generato per client inglese e con esecuzione globale.
- `source/ruang_irama.en-US.source` e `tests/fixtures/semantic_reference.txt`: specifica comportamentale inglese e riferimento dei test. Le regole per-player descrivono il comportamento d'ingresso al compilatore; non vengono importate nel gioco.
- `tools/build_global_runtime.py`: trasforma la specifica in controller globali e produce anche `tests/fixtures/global_runtime_reference.txt`, equivalente al clipboard finale. `--check` rifiuta output non aggiornati.
- Identificatori, nomi regola, commenti e keyword native usano soltanto l’inglese. HUD, feedback, cataloghi e impostazioni personalizzate sono in inglese, senza selettore o stato della lingua.
- La modalità si chiama Cozywatch. Le regole supportano Schermaglia; mappe e slot si configurano nella lobby. Il timer dura 10–60 minuti, default 30. L'HUD centrale mostra `cozywatch.org`; impostazione e cataloghi delle località sono rimossi.

Il clipboard pubblico numera le 127 regole da 0 a 126 nel loro ordine fisico, senza duplicati o suffissi alfabetici. I riferimenti alle regole della specifica usati in questa pagina restano identificatori interni stabili: la nuova numerazione dei titoli generati non cambia controller, subroutine o comportamento.

## Scheduler

Il runtime non contiene `Ongoing - Each Player`. `04g` prende uno snapshot dei player e scandisce le entità ogni 0,05 s. Controller di input, classificazione, HUD, eventi e pulizia sono subroutine atomiche dello scheduler globale. Esistono un solo `Wait` e un solo `Loop`, entrambi nello scheduler; le attese dei comandi e delle transizioni sono scadenze individuali. `ActivePlayer` e `TriggerPlayer` sono attori temporanei distinti, svuotati prima dell'attesa. Le espressioni persistenti congelano l'identità del proprietario, mantenendo dinamici colori, testi e posizioni.

| Frequenza | Lavoro |
|---:|---|
| 20 Hz | Controlli rapidi umani/ingressi non classificati; Luck solo con stato o icona pendente; Fly, Multijump e Superman Punch solo con toggle attivo |
| 10 Hz | Lifecycle umano e bot, RGB, riapplicazione fisica e revoca Camera/inspection |
| 5 Hz | Selezione del target follow dummy, distribuita per slot |
| 1 Hz | Countdown, timer nativo, scelta iniziale eroe, slot dummy, testi orfani e icone sociali; cache Camera/Revenge solo nelle relative pagine aperte; controllo disponibilità Follow solo per umani ON |

`ProcessPlayerFastState` deve restare raggiungibile prima di `IsHuman=True`, altrimenti si blocca la registrazione. Anche manutenzione umana e scadenza delle icone Luck residue restano raggiungibili durante la quarantena del cambio squadra. La guardia Luck considera `LuckActive`, `LuckSpinCount > 0`, `LuckEffect != 0` e `LuckIconEndTime > 0`: HEART può aver già concluso l'effetto ma avere un'icona ancora da distruggere.

Per Vision un controllo booleano sullo snapshot evita `Filtered Array` quando nessuno la usa; il vecchio pubblico viene svuotato una sola volta. Quando attiva, l'aggiornamento resta a 20 Hz. I bot classificati ricevono soltanto `ProcessPlayerBot`.

Il ramo 1 Hz mantiene disabilitata la completion nativa e sincronizza il timer fino allo zero; una guardia one-shot esegue `Restart Match`. Scoring e obiettivi nativi non vengono riscritti.

## Registrazione e risorse

I 12 slot identificano occupanti simultanei, non identità storiche. Nome temporaneamente nullo/vuoto significa ritentare, senza prenotare erroneamente uno slot. Bot normali e dummy non entrano nel roster umano né creano menu personali.

| Evento | Contratto |
|---|---|
| Ingresso | Classificazione, slot libero, setup e un solo set di HUD; al primo spawn il principale si apre sulla voce Info / Controls. Eventi duplicati non duplicano il roster o riaprono il menu. |
| Cambio squadra | Il controller globale `01a` mette in quarantena; dopo team/spawn stabili per 0,5 s, `01b` serializza quiete, scadenza 0,05 s, cleanup, scadenza 0,05 s e setup. Tutte le preferenze tornano ai default e il principale si apre su Info / Controls. |
| Uscita | Dopo 0,5 s distingue la vera uscita dalla transizione di team, distrugge risorse e riferimenti dell'identità esatta e libera lo slot. |
| Morte/cambio eroe | Normalizza lo stato fisico transitorio; conserva preferenze, pagina e cursore, riapplicando le funzioni compatibili al ritorno in vita. Non riapre il principale come un nuovo ingresso. |

La prenotazione lifecycle non sospende gli altri player. Un bot in classificazione o un player non spawned non deve trattenerla indefinitamente; i retry rispettano le scadenze individuali/globali. Un evento leave tardivo non può cancellare il nuovo occupante dello stesso slot.

Le fasi di `01b` non sospendono una subroutine: salvano fase e scadenza e riprendono in un tick successivo. Prima di riprendere riconfermano esistenza, tipo di entità, spawn, team, quarantena e prenotazione. Un cambio osservato revoca la prenotazione e sposta la scadenza nel futuro, anche se il player torna subito nella squadra precedente. Una transizione annullata non libera la prenotazione di un altro. Nessun attore temporaneo o indice di cleanup viene conservato attraverso il solo `Wait` dello scheduler.

`QuiescePlayer` normalizza lo stato e rimuove risorse transitorie di menu, Luck e icone. La prima scadenza precede la pulizia canonica del roster; la seconda separa la pulizia dalla nuova classificazione e creazione globale degli HUD. Non viene distanziata ogni singola operazione nativa. I controller rispettano la quarantena; i player stabili continuano a poter invalidare i propri target. Gli eventi nativi di morte, danno e uscita catturano i dati dell'evento in una coda limitata; lo scheduler elabora i record senza assumere che `Event Player`, `Attacker` o `Victim` esistano nel contesto globale. L'utente ha confermato importazione e cambio squadra nella revisione precedente; durata, carico e nuove modifiche richiedono prove distinte.

Prima del primo spawn, `ProcessPlayerFastState` arma una sola scadenza individuale di 60 s. Al controllo 1 Hz, un player ancora non spawned riceve Shion; latch consumato prima di `Start Forcing Player To Be Hero` e immediato `Stop Forcing Player To Be Hero` evitano ripetizioni e lasciano libera la scelta successiva. Setup dopo spawn chiude il timer, senza riarmarlo a morte o cambio team. Le due variabili appartengono all'entità: nessun registro globale, HUD o `Wait` aggiunto. Dummy e AI classificati non entrano in questo ramo; un AI non ancora spawned resta non classificabile fino allo spawn, come nel lifecycle esistente.

Gli handle hanno un proprietario e un registro canonico che sopravvive alla perdita delle variabili del leaver. Distruggere prima di sovrascrivere; svuotare anche i mirror e non distruggere ID già riciclati da altri. Cleanup e voti leggono gli occupanti rimasti, senza dipendere dal voto di un'entità scomparsa. Camera, Revenge, Attach, Teleport, inspection e voti non conservano riferimenti al leaver.

## HUD e input

Ogni umano ha al massimo un HUD Arcade: la navigazione sulla stessa pagina aggiorna valori rivalutati; apertura, chiusura e cambio pagina gestiscono l'handle. Niente preload o cache di pagine nascoste. Header è `Null`; si usano Subheader/Text, feedback `Small Message` necessari e IWT per targhette.

| Area | HUD fissi | Contenuti dinamici |
|---|---|---|
| Top | Titolo/countdown 0, cozywatch.org 1, spazio 2 | Menu, Travel o effetto in 3 |
| Left | Player Vibes 0, Chill Star 13 | Unico roster in 1–12 |
| Right | Host 0 | Host nel campo Text, una riga con spazio sopra e sotto, RGB del titolo |

I sei handle globali sono inclusi nella diagnostica: rimossi i due promemoria laterali e lo spazio Left −1. Il leader usa nome/colore stabili. Il roster mantiene il Name Color nel Subheader; la diagnostica usa il campo Text bianco dello stesso handle, visibile solo all'host sull'ultima riga. Il ramo nascosto restituisce una stringa vuota, evitando lo `0` derivato da un `Null` tipizzato come testo. IWT e icone catturano soltanto l'identità con `Evaluate Once`; posizione/testo/pubblico necessari restano rivalutati. Le targhette riuniscono icona, nome e salute, ancorati a `Eye Position + Vector(0, 0.450, 0)`.

Il principale conserva 16 voci: Info / Controls 0, Name Color 1, Camera 2, Soundtrack 3 e funzioni 4–15 invariate. Quando il cursore principale è 0, `Subheader` è vuoto e `Text` contiene la preview Info con binding dinamici: Camera da Interact tenuto 0,5 s con Crouch rilasciato, Arcade da Melee tenuto 0,5 s, ispezione eroe/HP da Crouch a menu chiuso con Travel OFF, navigazione e apertura della guida da Crouch + Primary/Secondary/Interact, ritorno da Crouch + Reload. Con le altre voci selezionate e negli altri sottomenu, i comandi contestuali occupano `Subheader` e funzioni/opzioni occupano `Text`. La pagina Info mantiene la guida completa in `Text` e `Subheader` vuoto. Ogni pagina mantiene un solo handle Arcade.

Travel/Attach, Privacy, Dummy Follow e Superman Punch mostrano lo stato corrente nella voce principale: Crouch + Interact lo alterna senza aprire un sottomenu o ricreare l'HUD. La pagina rimane −1 e il cursore resta sulla stessa voce; Primary/Secondary continuano a navigare nel menu principale. I quattro renderer esclusivi e i loro rami non più raggiungibili sono rimossi. I tre cursori ON/OFF precedenti restano rimossi; gli indici già assegnati alle preferenze restano stabili. Input, cursori ancora necessari, target, latch e timer appartengono al player. Menu e Camera condividono il latch Interact fino al rilascio fisico; Crouch decide quale comando può consumarlo. La pressione tenuta usa una scadenza nel controller globale: nessun `Wait` nei comandi, nel cleanup o in Resurrect.

Il catalogo contiene 200 generi in dieci gruppi da venti: i dieci precedenti restano primi in ciascun gruppo. Navigazione ±1/±10 e denominatore HUD usano la lunghezza corrente; i titoli inglesi del gruppo usano divisione per venti. Le etichette inglesi e i valori della palette contengono 40 colori ordinati per famiglie e sfumature: bianco, grigi, nero, colori caldi, rosa, viola, blu e verdi. White resta all'indice 0 e Silver Mist all'indice 1; il profilo งูแรร์ parte da Charcoal, indice 2; Black è all'indice 3 e usa RGB (0, 0, 0) sia per il nome sia per la preview.

La pagina Info / Controls 0 usa l'azzurro fisso RGB (160, 195, 235), indipendente dal Name Color. La pagina Name Color 1 mostra esattamente il colore selezionato, bianco per il default ordinario. Le pagine 2–15 usano il 68% del Name Color attivo e il 32% del proprio accento. Preview del menu principale e sottomenu condividono la stessa tinta. Restano un solo Chase per ramo, la transizione di 0,180 s e i cinque colori Travel indipendenti.

Rimosso il vecchio effetto di applicazione, comprese le pulsazioni di Revenge e revoca Camera. Le tinte dei menu conservano la transizione nativa `Chase` di 0,180 s, interrotta dal cleanup del proprietario; non aggiungono cicli o attese. L'unico `Play Effect` è il Ring Explosion dei salti multipli: effetto nativo temporaneo, senza handle persistenti o distruzioni periodiche.

Le icone sociali usano `Objective Position(Objective Index)` come centro e un raggio orizzontale fisso di 10 m. Il Light Shaft, la palette approssimata del colore host e la scala legata al numero di umani sono rimossi. Create Icon mantiene il Name Color esatto del proprietario; senza obiettivo valido l'icona rimane nascosta. Icon String inserito in un testo non eredita il colore nel client, quindi questo sistema usa entità native.

Quattro array fissi di 12 slot conservano proprietario, handle entità, selezione e timestamp. Il runtime aggiunge una cache di visibilità per i 12 slot, aggiornata a 20 Hz; le 36 scelte leggono quella cache e verificano direttamente l'esistenza del proprietario, evitando di ripetere l'intero predicato. `UpdateSocialObjectiveIcons` lavora a 1 Hz e rinnova il percorso dopo 3 s. Il Chase dura 4,5 s: il rinnovo parte dalla posizione corrente prima della scadenza, anche se il controllo arriva al secondo successivo. Non imposta di nuovo la posizione né aumenta la frequenza della manutenzione. Un `Chase Player Variable Over Time` anima il vettore individuale `ObjectiveIconPosition`, inizializzato come Vector prima del primo Chase. Il motore cattura direttamente la destinazione casuale e la durata con `None`, senza un array di waypoint. Le 36 scelte leggono la stessa posizione animata, evitando la formula di interpolazione duplicata. Nessuna chiamata Random viene rivalutata per frame e non vengono aggiunte attese. Gli offset sono in metri reali: distanza orizzontale 0–10 m, altezza 0,5–8 m sopra l'obiettivo. Identità del proprietario congelata e Name Color rivalutato conservano isolamento e colore esatto. Il cambio colore riusa l'entità; il cambio tipo distrugge prima il vecchio handle. `CleanupObjectiveIcon` ferma il Chase e rimuove l'identità esatta al leave/team reset; la manutenzione recupera anche gli orfani e rimuove l'entità quando l'icona diventa NONE. Le icone non entrano nel contatore IWT. Il [compilatore OverPy](https://github.com/Zezombye/overpy/blob/master/src/data/actions.ts) documenta Vector/None e rivalutazione di Create Icon. Resa visiva e conteggio compilato richiedono verifica nel client.

## Movimento e interazioni

- **Fly:** impulsi a 20 Hz correggono velocità corrente verso quella richiesta. Avanti usa la mira 3D; indietro/strafe il piano orizzontale. Normalizzazione e intensità analogica evitano un bonus diagonale. Gravità e movimento nativo sono zero durante il volo normale; niente `Start Transforming Throttle`.
- **Rampa:** `Min(1000, 100 + Max(0, tempo − inizio) * 45)`, con input direzionale orizzontale di intensità maggiore di 0,050. Baseline uniforme 5,5 m/s, massimo richiesto 55 m/s dopo 20 s. Avanti, indietro, laterali e diagonali mantengono la stessa progressione; solo assenza di input entro la deadzone riporta al 100%. Senza input la velocità richiesta è zero. Disattivazione, morte e priorità Luck mantengono i reset fisici del lifecycle.
- **Ghost:** `Disable Movement Collision With Environment(player, False)` attraversa pareti/soffitti conservando pavimenti; non modifica la collisione con player.
- **Multijump:** sei campi individuali, default OFF. Il runtime aggiunge alla specifica i campi per stato e scadenze dei controller globali; le dichiarazioni vengono rinumerate senza indici riservati alle lingue. Il menu 14 seleziona una forza fissa 100–1000% a passi del 100%; il 100% corrisponde alla velocità verticale richiesta di 6 m/s, il 1000% a 60 m/s. Una nuova pressione in aria corregge subito la sola componente verticale con `Apply Impulse` e `Incorporate Contrary Motion`; Jump tenuto ripete ogni 0,300 s e non accumula velocità. Funziona anche con menu aperto. Lo stato a terra corrente e precedente protegge il primo distacco nativo; tenere Jump a terra non ripete ring senza un salto. Attach, Fly, Luck Acceleration e morte sospendono la spinta. Il latch Resurrect resta separato e richiede rilascio dopo la resurrezione. Applicare la scelta sincronizza Jump e stato a terra, rimandando di 0,300 s la ripetizione già tenuta. Ring RGB breve per ogni salto valido. Preferenza conservata a morte/cambio eroe, azzerata a cambio squadra/uscita; nessun `Wait`, `Loop`, HUD o effetto persistente per salto. Timing del distacco, velocità effettiva e collisioni richiedono prove nel client.
- **Camera:** un solo `Start Camera` condiviso in `StartCamera`, posizione/mira per-frame, `Blend Speed 0` e un raycast. Il destinatario transitorio `CameraPlayer` viene catturato nelle espressioni persistenti e poi svuotato. Dopo un Travel riuscito, la sequenza atomica è Stop Camera → Teleport → riavvio della Camera attiva; il cambio del proprio eroe riavvia la stessa modalità e il bersaglio ancora valido. Nessun Wait e nessuna attivazione se OFF. Target morto, assente, non spawned, in quarantena o umano privato viene revocato a 10 Hz; una revoca non riattiva la Camera.
- **Travel/Attach:** cinque pagine con cursore normalizzato modulo 5; navigazione avanti/indietro e azione singola tramite Interact. Forward, il suo ramo nello scheduler e la sua subroutine sono stati rimossi dopo la segnalazione di crash al cambio squadra. `01a` mette in quarantena e revoca il Punch; non esegue uno Stop Chase immediato sul player in transizione. Il lifecycle stabilizzato esegue dal contesto globale la pulizia completa di HUD, Chase, icona, roster e slot. Superman Punch durante Travel conserva la correzione precedente. La rimozione di Forward non identifica da sola la causa del crash nativo.
- **Travel:** obiettivo riletto al click e validazione geometrica condivisa; punto assente/non sicuro annulla il teleport. Attach rifiuta self-attach e cicli di qualsiasi lunghezza con traversal limitato al roster, senza attese. Privacy, morte, uscita e team-switch revocano il collegamento.
- **Jump Resurrect:** un tentativo per pressione. Calcola una destinazione camminabile dalla posizione corrente; raycast e distanza dalla navigazione distinguono terreno sicuro e vuoto. Solo nel recupero teletrasporta alla stessa destinazione +0,5 m prima e dopo `Resurrect`. Una morte immediata non riarma Jump tenuto; serve rilasciarlo da vivo o morto. Nessun `Wait`, forcing o `Respawn`.

## Unkillable, Revenge e Luck

FULL HP combina danni ricevuti zero, urti zero e collisione player disabilitata. OFF/1 HP e cleanup ripristinano insieme danni, urti e collisioni; Ghost è indipendente. Morte, setup e respawn rispettano l'ownership della fisica.

Superman Punch (menu 15) funziona con menu principale o sottomenu aperti. La pressione melee tenuta 0,5 s mantiene il toggle Arcade e il consumo fino al rilascio; non viene alterata la gestione dei comandi. Usa un registro globale dei soli umani ON e un latch per ciascuno dei 12 slot; non aggiunge campi player dedicati al Punch. A 20 Hz, `Is Meleeing` cerca subito un bersaglio vicino davanti con linea di vista libera e consuma il contatto soltanto quando lo trova, compresa una vittima protetta. `89i1`, evento `Player Dealt Damage` con `Event Ability == Button(Melee)`, registra soltanto lo snapshot di attaccante, vittima, protezioni e identità. La subroutine globale elabora quel record, riconferma le identità e lo stato della vittima e applica l'eventuale KO senza un nuovo controllo geometrico. Junker Queen usa il solo rilevamento dell'animazione, evitando che il suo sanguinamento sia scambiato per un nuovo colpo. I due percorsi condividono il latch per evitare due KO nello stesso attacco. Unkillable e i bersagli invulnerabili restano protetti; non viene abilitato il danno amico per gli altri attacchi. Cambio squadra e uscita cancellano il consenso; il nuovo occupante resetta il latch. Il ledger Revenge già include tutti gli altri umani, anche alleati; anche gli eventi di morte sono elaborati globalmente da snapshot con identità e generazione. La semantica dell'evento è descritta nella [guida Blizzard](https://news.blizzard.com/en-gb/article/22938941/introducing-the-overwatch-workshop); timing e forme degli eroi richiedono verifica nel client.

| Esito Luck | Durata | Interazione |
|---|---:|---|
| Vision | 15 s | Un IWT per soggetto, inclusi bot e umani privati; disabilita gli ingressi inspection/Travel |
| Acceleration | 10 s | Propulsione guidata dalla mira; ha priorità sul motore Fly, che riparte con rampa fresca |
| Skull | Immediato | Solo l'esito finale sospende Unkillable; retry 0,25 s, deadline 5 s |
| Team Heal | Immediato | Cura completa della squadra viva; feedback al proprietario |
| Burning | 10 s | 5% della salute massima ogni secondo; sospende Unkillable per tutto l'effetto e poi lo ripristina |
| Hacked | 5 s | Stato Hacked |

Luck non cambia preferenze Ghost/Fly o Unkillable. Gli effetti temporizzati chiudono il menu al risultato; quelli immediati no. Le icone residue hanno una propria scadenza. Revenge consuma il debito soltanto alla morte completa, con claimant/target esatti; timeout, uscita e cambi squadra non duplicano né consumano anticipatamente il debito.

## Dummy e bot normali

`MaintainDummyBots` controlla entrambe le squadre a 1 Hz. In Schermaglia crea al massimo un dummy per team, solo con uno Spawn Point valido e almeno due slot liberi. A squadra piena dà priorità alla rimozione. Ogni team ha un cooldown impostato a tempo corrente +1 prima del tentativo, anche se la creazione fallisce; una registrazione riservata rinvia la manutenzione.

Dummy e bot normali sono offensivamente passivi, velocità 20%, danni/urti ricevuti 100% e collisioni native. Il dummy nasce nello Spawn Point del proprio team, ha respawn massimo 3 s e aspetta un timestamp di 1 s prima di cercare l'uscita dalla spawn. Usa `Objective Position(Objective Index)` anche senza obiettivo visibile; nessuna coordinata fissa o dipendenza da player fuori spawn.

La ricerca prova otto direzioni a 8 e 12 m: 16 candidati, al massimo uno al secondo. Il punto finale deve avere spazio per il corpo, terreno valido e distanza 6–16 m dall'obiettivo; viene rialzato di 0,5 m. Se manca un punto valido il dummy resta in spawn e riprova; morte/respawn azzerano e riarmano la ricerca.

Il follow sceglie a 5 Hz il più vicino fra gli umani nemici registrati, vivi, spawned e con Dummy Follow ON. Facing/throttle restano rivalutati: arresto entro 4 m, stop se nessun target idoneo o alla morte/rimozione. Il movimento è diretto e può fermarsi contro un muro; gli AI normali conservano la navigazione nativa. Manutenzione morte/respawn e rilascio classificazione restano a 10 Hz. I bot non ricevono routine di menu, cache, Luck o Fly.

Il menu permette ON soltanto con un dummy della squadra avversaria presente; OFF resta sempre disponibile. La disponibilità viene riletta al comando, anche se il menu era già aperto. Un consenso ON viene azzerato al successivo controllo 1 Hz se manca il dummy avversario; il suo ritorno non riattiva la preferenza. Il ramo OFF e i bot non ricevono questa manutenzione.

## Verifica delle modifiche

Il validatore confronta sorgente e riferimenti inglesi e controlla questi contratti; i test eseguono anche mutazioni e flussi con risposte native simulate. Il motore reale, le collisioni delle mappe e i crash richiedono la [matrice nel client](TEST.md). I [controlli automatici](VALIDAZIONE.md) restano separati dai risultati live.
