# Piano di test — versione 0.8.1

Stato: **static-ready / live-pending**

I test live della 0.8.0 erano stati completati; la 0.8.1 introduce il refresh leggero del cambio squadra, il profilo dedicato `งูแท้`, Ghost/Fly, il cooldown Self Kill, il Resurrect sempre su `Nearest Walkable Position` e la riapplicazione Fly post-morte, quindi deve completare nuovamente la matrice nel client. Eventuali valori diagnostici numerici non forniti non vengono inventati.

## 1. Gate statici

Eseguire dalla radice del repository:

```powershell
python -m unittest discover -s tests -p 'test_*.py'
python tools/validate_workshop.py
python tools/check_clipboard_import.py workshop/ruang_irama.it-IT.workshop --language it-IT
```

Accettazione:

- tutti gli unit test verdi;
- validatore semantico verde;
- preflight clipboard `it-IT` verde;
- parità semantica canonica tra `workshop/ruang_irama.it-IT.workshop` e `tests/fixtures/semantic_reference.txt`;
- nessuna dipendenza Python esterna;
- nessun errore da `git diff --check`;
- un solo `Loop` e massimo 7 `Wait`, senza `Wait` in Resurrect, cleanup roster o stabilizzazione dummy;
- un solo workflow permanente, `validate-workshop.yml`, e nessun marker, trigger o patcher one-shot sotto `.github`.

Le invarianti controllate automaticamente sono dettagliate in [`VALIDAZIONE.md`](VALIDAZIONE.md).

## 2. Preparazione client

1. Aggiornare Overwatch alla build del **19 agosto 2026**.
2. Impostare la lingua testo del client su Italiano e importare da zero `workshop/ruang_irama.it-IT.workshop` dalla vista Raw; non riutilizzare un replay precedente alla patch.
3. Annotare codice import, build client, regione, data/ora e piattaforma.
4. Abilitare la diagnostica host quando si acquisiscono le metriche.
5. Preparare 12 slot. I dummy possono occupare soltanto la capacità libera e devono auto-rimuoversi per consentire fino a 12 umani; la prova di input simultanei richiede più utenti reali.

Accettazione smoke:

- import senza errori parser;
- nessun errore `Subroutine '<indice>' is too long`, `Expected ')'` o altro rifiuto sintattico/delle dichiarazioni;
- avvio senza `excessive Workshop script load`;
- D.Mon può entrare, cambiare eroe, aprire/chiudere menu e usare i sistemi generici senza errori;
- nessuna collisione evidente con il nuovo Team Status Indicator.

## 3. Contratto input

Provare con un eroe che esponga chiaramente Melee, Jump, Primary, Secondary, Reload, Ability 1/2, Interact e Crouch.

| Stato | Prova | Esito atteso |
|---|---|---|
| Vivo, menu chiuso | Tieni Melee 0,5 s | il menu si apre una volta |
| Vivo, menu aperto | Tieni Melee 0,5 s | il menu si chiude una volta |
| Menu aperto | Primary/Secondary senza Crouch | nessun comando menu |
| Menu aperto | Crouch + Primary/Secondary | una sola navigazione per pressione |
| Menu aperto | Interact/Reload senza Crouch | nessun comando menu |
| Menu aperto | Crouch + Interact/Reload | entra/applica o torna indietro |
| Soundtrack | Crouch + Ability 1/2 | `+10/−10` con wrap |
| Menu aperto | Melee e Jump | azioni normali dell'eroe non disabilitate |
| Menu chiuso, Crouch rilasciato | Tieni Interact 0,5 s | alterna Camera, una volta per hold |
| Menu aperto, Crouch rilasciato | Tieni Interact 0,5 s | alterna Camera, senza applicare il menu |
| Menu chiuso | Tieni Crouch | inspection/Teleport disponibili |
| Menu aperto | Crouch + Interact | esegue soltanto il comando menu; Camera non parte |
| Menu aperto | Tieni Crouch | inspection/Teleport non partono |
| Morto | Menu già aperto | resta visibile ma congelato |
| Morto | Primary, Secondary, Interact, Reload, Crouch, abilità | nessun comando Arcade |
| Morto | Jump | `Teleport` alla `Nearest Walkable Position` validata e poi `Resurrect`; nessuna Spawn Room; menu ancora visibile |

Sul caso Jump, provare morte su terreno normale, vicino a un bordo e nel vuoto profondo. In tutti i casi deve essere calcolata una `Nearest Walkable Position`, validata e usata da un solo `Teleport` del cadavere prima di `Resurrect`; non deve comparire alcun percorso verso la Spawn Room. Se non esiste alcun punto sicuro, il player deve restare morto invece di entrare in un ciclo di morti. Non sono ammessi offset casuali, forcing di posizione, `Respawn` o `Wait`. Tenere premuto il pulsante dopo un tentativo fallito: non devono partire chiamate ripetute. Rilasciare Jump e premerlo di nuovo deve consentire esattamente un nuovo tentativo. Dopo un successo, effetto e messaggio devono apparire soltanto dopo la conferma del ritorno in vita.

Ripetere rapidamente gli input per cercare doppie attivazioni, latch bloccati e interferenze tra hold e click.

Verificare inoltre entrambe le transizioni senza rilasciare `Interact`: dopo `Crouch + Interact`, rilasciare soltanto Crouch e continuare l'hold oltre 0,5 s non deve attivare la Camera; dopo un hold Camera completato, premere Crouch mantenendo Interact non deve applicare il menu. Entrambi i sistemi si riarmano soltanto dopo il rilascio di Interact.

## 4. Menu e localizzazione

Verificare esattamente 14 voci, indici e contenuti:

1. Name Color — 32 colori.
2. Third-Person Camera — OFF, self e target valido.
3. Soundtrack — 100 generi.
4. HUD Language — English, Bahasa Indonesia, ไทย.
5. Revenge — debiti da kill dirette.
6. Unkillable — OFF, 1 HP, FULL HP.
7. Hero Voice — 5 preset.
8. Player Icon — Nothing + 36 icone.
9. Crouch Teleport — OFF/ON.
10. Crouch Privacy — OFF/ON (default OFF).
11. Try Your Luck — sei esiti.
12. Vote Player — umani, self-vote incluso.
13. Dummy Follow — il dummy nemico può seguire il player, OFF/ON (default OFF).
14. Ghost Mode / Fly — Ghost e Fly come toggle indipendenti (default entrambi OFF).

Per ogni pagina e per ciascuna lingua EN/ID/TH:

- aprire, navigare avanti/indietro, applicare, tornare e riaprire;
- nel Main Menu percorrere `11→12→13→0` e poi `0→13→12`; chiudere sul 13, riaprire e tornare a 0, verificando che Dummy Follow e Ghost/Fly restino distinti e che il renderer non si blocchi;
- verificare testo, stato, feedback e comando localizzati;
- verificare una riga vuota tra contenuto e comandi;
- controllare glifi Thai, wrapping e la griglia esatta: Top `0/1/2` + contenuto `3`, Left `-2/-1/0` + roster `1..12`, Right `-16/-15/-14`, roster `-13..-2` e spaziatore finale `-1`;
- verificare con 1, 6 e 12 player che il Team Status Indicator e il kill feed nativi seguano l'ultimo nome Right dopo una riga vuota, senza inserirsi fra `PLAYER VIBES` e il roster;
- confermare che sotto il roster Left non compaia uno `0` isolato con diagnostica disattivata e che i promemoria completi/`LOBBY & CHILL TIME` siano corretti in EN/ID/TH;
- confermare che non compaiano titoli HUD o `Big Message`;
- verificare che una scelta invariata non ripeta Small Message, audio o effetto;
- controllare che esista un solo HUD Arcade: nessuna copia appare durante scroll, cambio pagina, morte o riapertura;
- verificare che il promemoria `Crouch + command` compaia nel menu ma non sia duplicato nell'HUD globale, senza riga vuota prima dei comandi o gap eccessivo sotto il titolo server.

Focus dati:

- tutti i 100 generi, wrap `0 ↔ 99` e salti `±10`;
- tutti i 32 colori;
- Name Color parte da bianco (default) e la sua scelta aggiorna le sfumature degli altri menu senza renderle identiche tra loro;
- 37 icone con nome localizzato e indice 0 `Nothing`;
- 26 località server nello stesso ordine;
- roster con `MIN`, `MENIT` e `นาที` corretti;
- CHILL, generi, nomi player ed eroi invariati come nomi propri.

### Profilo `งูแท้`

- Entrare con il nome visibile esatto `งูแท้`: Name Color deve partire da `Silver Mist`, Player Icon da `Poison 2` e Player Vibes da `Caladan Brood`.
- Modificare colore e icona dal menu, chiudere/riaprire e cambiare squadra: entrambe le scelte devono restare modificabili e persistenti.
- Aprire Soundtrack: la pagina deve risultare read-only e Primary/Secondary, Interact e Ability 1/2 non devono cambiare `Caladan Brood`.
- Verificare che `Caladan Brood` non aumenti il catalogo globale: gli altri player continuano ad avere esattamente 100 generi e il normale wrap `0..99`.
- Uscire davvero dalla lobby e rientrare con lo stesso nome: il setup deve riapplicare `Silver Mist`, `Poison 2` e il Vibes bloccato.
- Entrare con un nome simile ma non identico: il profilo non deve attivarsi. Per verificare una rinomina dell'account, uscire davvero dalla lobby e rientrare con il nuovo nome prima di controllare che il profilo non venga riapplicato; nella stessa sessione resta invece attivo fino al rejoin. Entrare con un secondo player dallo stesso nome visibile esatto deve mostrare la limitazione nota del matching e applicare lo stesso profilo.

### Ghost Mode / Fly

- Al setup e dopo un vero leave/rejoin, verificare che Ghost e Fly siano entrambi OFF; il cambio squadra, il cambio eroe, la morte e il Resurrect devono invece conservarne separatamente le scelte.
- Con solo Ghost ON, attraversare pareti e soffitti ma non pavimenti; la collisione con player, bot e dummy deve restare normale.
- Con solo Fly ON, verificare gravità zero e collisione ambientale normale. Forward/Back e Left/Right devono muovere lungo la visuale e il relativo strafe 3D. Ripetere Forward guardando verso i quattro orientamenti cardinali della mappa e con pitch davanti/in alto/in basso: la rampa deve partire in tutti i casi, senza dipendere dall'asse X/Z. Usa `6 m/s²` con cap Workshop richiesto di `20 m/s`; registrare la velocità effettiva per eroi diversi perché il limite orizzontale del motore deve essere confermato live.
- In Fly, rilasciare tutti gli input dopo movimento o knockback: il player deve arrestarsi e restare immobile, senza deriva o fluttuazione. Riapplicando un input, il movimento deve riprendere subito nella direzione corrente dello sguardo.
- Attivare insieme Ghost e Fly, poi disattivarli in ordine inverso: i due toggle devono restare indipendenti; Fly OFF ripristina gravità 100, ferma il throttle trasformato e arresta la rampa normale senza interrompere un'eventuale Luck Acceleration ancora attiva; Ghost OFF ripristina la collisione ambientale completa. Con Fly ON, morire e usare Jump: al ritorno in vita il volo deve funzionare subito senza toggle OFF/ON manuale.
- Provare tutti gli esiti Try Your Luck con Fly attivo: nessun ramo deve impostare o ripristinare gravità, throttle trasformato o toggle Ghost/Fly. In particolare Acceleration deve restare attiva per tutti i 10 secondi senza essere annullata dal freno idle di Fly; alla sua scadenza, Fly deve tornare immobile quando non ci sono input.

### Unkillable FULL HP

- Applicare FULL HP e ricevere contemporaneamente fuoco, danni periodici e urti/knockback da eroi e bot: salute e posizione non devono essere alterate.
- Attraversare e farsi attraversare da un umano e da un dummy: FULL HP non deve avere collisione con player/bot.
- Passare da FULL HP a OFF e ripetere le prove: danni, urti e collisione devono tornare normali.
- Passare da FULL HP a 1 HP: collisione e urti devono tornare normali, mentre resta soltanto la semantica curabile della modalità 1 HP.
- Partire da FULL HP e attivare Try Your Luck: modalità e cursore devono restare invariati. Vision, Acceleration, Self Heal e Hacked conservano status, immunità a danni/urti, assenza di collisione e icona; Burning li sospende per tutti i 10 secondi e li ripristina al termine. Soltanto lo Skull finale sospende la protezione per completare la morte; dopo Resurrect la preferenza e l'icona devono riattivarsi. Un cambio squadra leggero conserva la preferenza; soltanto leave e rejoin eseguono setup fresco e ripristinano i default.
- Partire da FULL HP, entrare/uscire dalla Spawn Room e morire: la scelta non deve essere cancellata. Dopo Resurrect verificare nuovamente danni zero, urti zero e assenza di collisione con player/bot; la stessa protezione deve restare attiva dentro la Spawn Room.
- Verificare con più player che l'immunità di un utente non venga trasferita al player successivo dello scheduler e non venga mai applicata a dummy/iBot.

## 5. Try Your Luck

Forzare o ripetere l'attivazione fino a osservare tutti gli esiti:

| Esito | Verifica |
|---|---|
| Vision | icona eroe, nome roster stabile e salute live in EN/ID/TH per bot/dummy e tutti gli umani, compresi quelli con Privacy ON; Crouch non crea inspection/Teleport o altri HUD; cleanup dopo 15 s |
| Acceleration | da fermo e senza input direzionali, propulsione automatica lungo la mira 3D; cleanup dopo 10 s |
| Skull | unico esito che bypassa Unkillable; D.Va: distruzione mech seguita dalla morte pilota; Echo: fine duplicazione seguita dalla morte base; cleanup/menu soltanto alla morte completa; protezione ripristinata dopo Resurrect |
| Self Heal | salute completa e messaggio soltanto per il proprietario; nessun altro player o bot deve cambiare |
| Burning | 5% max HP ogni 1 s per 10 s; Unkillable e riduzione Damage Received sospesi per l'intera durata e ripristinati al termine; stop alla morte |
| Hacked | stato per 5 s, poi rimozione |

Per ciascun esito:

- durante ogni passaggio della roulette l'icona corrente deve restare agganciata a occhio/mirino con aggiornamento ogni frame; eseguire movimento, rotazione continua e inversione di 180° senza scatti o salti verso altri player;
- quando Skull compare soltanto come icona intermedia, il player deve restare vivo; il retry può iniziare esclusivamente se Skull è l'esito finale;
- durante la stessa roulette eseguire join/leave di un umano: la reevaluation `Visible To and Position` deve rendere tutte le sei icone visibili al roster umano corrente, senza includere bot;
- con Acceleration, lasciare completamente i tasti direzionali: il player deve partire da solo; ruotare poi la visuale davanti, in alto e in basso e verificare che `Facing Direction Of(Evaluate Once(player))` con `Direction Rate and Max Speed` segua continuamente la direzione 3D corrente;
- ripetere Acceleration con Fly ON: la propulsione Try Your Luck deve restare attiva per 10 secondi, mentre nessun ramo della roulette può scrivere gravità o avviare/fermare il throttle trasformato di Fly;
- Unkillable non cambia all'avvio: Mode, Kursor, flag runtime, status, modificatori e icona restano invariati;
- il menu non accetta comandi incompatibili durante lo stato bloccato;
- il countdown non salta o duplica tick;
- morte, timeout e hero swap annullano stato/status/effetti temporanei senza cancellare Mode/Kursor Unkillable; salvo il periodo Burning intenzionale, un hero swap da vivo non deve lasciare interrotti status/tripletta/icona Unkillable. Il cambio squadra leggero conserva preferenze, Camera, status, effetti e voti attivi, mentre leave e rejoin eseguono cleanup e setup fresco;
- rimuovere un iBot vivo durante Vision e verificare che il suo IWT sparisca senza creare roster, HUD o lifecycle umano;
- nessuna seconda roulette per lo stesso player parte mentre la prima è attiva;
- chiusure e riaperture non duplicano HUD, In-World Text o effetti.

Matrice obbligatoria Try Your Luck × Unkillable:

- ripetere i sei esiti con Unkillable OFF, 1 HP e FULL HP;
- con 1 HP e FULL HP, Vision, Acceleration, Self Heal e Hacked non devono mai rimuovere status, cambiare modalità/cursore o far sparire stabilmente l'icona;
- con Burning, verificare che ogni secondo venga applicato il 5% della Max Health anche partendo da 1 HP/FULL HP, senza modificare Mode/Kursor; Unkillable e la riduzione Damage Received devono restare sospesi per tutti i 10 secondi, senza riapplicazione fra i tick, e tornare immediatamente al termine o dopo un cleanup anticipato;
- con Skull finale, verificare il bypass temporaneo e la morte completa; premere Jump per Resurrect e confermare il ripristino della stessa modalità, della tripletta corretta e dell'icona entro il tick globale;
- lasciare scadere la deadline Skull quando `Kill` viene rifiutato: menu/input devono liberarsi e Unkillable deve tornare attivo senza alterare Mode/Kursor;
- ripetere un Revenge su target 1 HP e FULL HP: deve usare lo stesso bypass temporaneo, ma claimant, consumo debito, condizioni di commit e timeout devono restare identici ai test Revenge esistenti.

### Revenge e morte completa

- Con D.Va bersaglio, verificare che il debito resti invariato al demech e scenda di uno soltanto alla morte della pilota.
- Durante il demech non devono comparire il prompt Jump né una falsa posizione di morte; entrambi devono essere registrati soltanto alla morte completa.
- Con Echo duplicata, verificare che la fine della copia non consumi il debito e che il retry prosegua fino alla morte della forma base.
- Un secondo claimant sullo stesso target deve essere rifiutato; se un altro attacker completa la kill, il primo claimant non consuma alcun debito e la morte viene registrata normalmente.
- Il cambio squadra leggero di claimant o target deve conservare il pending senza consumare il debito, duplicare il claim o mostrare un falso successo; soltanto morte completa valida o timeout ne chiudono l'esecuzione. Un leave vero deve annullarlo e liberare i riferimenti.
- Mercy, Torbjörn e altre forme/armi alternative non devono essere trattate come casi speciali: il criterio terminale resta esclusivamente `Is Alive == False`.

## 6. Camera, inspection e Teleport

### Crouch Travel & Attach

- Tenere Crouch e verificare le cinque pagine: Spawn Travel, Objective Travel, Player/Bot Travel, Player/Bot Attach e Self Kill.
- Primary avanza, Secondary torna indietro e Interact esegue sempre la pagina attiva; Primary/Secondary non devono eseguire il teleport o la kill.
- Sulla pagina Self Kill, Interact deve eseguire una sola richiesta per pressione e nessun'altra pagina deve essere attivata nello stesso hold. Un secondo tentativo entro 3 secondi non deve uccidere e deve mostrare il tempo residuo localizzato; morte, Resurrect e cambio squadra non devono azzerare il cooldown, mentre un vero leave/rejoin deve inizializzarlo di nuovo.
- Agganciarsi a un umano e a un dummy: i piedi devono restare separati dalla testa del target tramite l'offset previsto.
- Da attaccati, Reload senza Crouch deve restare l'azione nativa dell'eroe.
- Con Menu Arcade Melee chiuso, Crouch + Reload deve sganciare; con Menu Arcade Melee aperto non deve sganciare.
- Morte, leave/despawn, cambio eroe proprio o del target e Privacy ON del target umano devono sganciare automaticamente.

### Cambio squadra / lifecycle 0.8.1

- Ripetere Team 1 → Team 2 → Team 1 almeno 20 volte con un solo umano, controllando che non compaia `excessive Workshop script load` e che il roster conservi una sola voce.
- Ripetere con 2, 6 e 12 umani cambiando squadra quasi simultaneamente: ciascun player già registrato deve percorrere il refresh leggero senza entrare nel setup iniziale serializzato.
- Durante la transizione verificare che vengano aggiornati soltanto stato dipendente dal Team, UI transitoria e, quando necessario, `HudKiri/HudKanan`; roster, preferenze e cursori devono restare stabili.
- Cambiare squadra mentre il player è morto e durante hero select/prima di `Has Spawned`: le righe esistenti non devono essere distrutte dal detector. Dopo spawn e ritorno in vita, entrambe le righe devono comparire una sola volta per tutti i viewer.
- Eseguire anche uno switch diretto mentre il player risulta ancora spawned/vivo: il consumer non deve partire nello stesso tick del detector, ma soltanto dopo almeno 0,25 secondi e con stato ancora stabile.
- Da un secondo player mantenere Crouch e la mira sul player per tutta la transizione: durante il pending il target deve uscire dal filtro, il vecchio In-World Text deve sparire e, appena concluso il pending, nome, icona eroe e HP devono tornare senza rilasciare Crouch o cambiare Privacy. Ripetere iniziando Crouch sia durante sia dopo il pending.
- Ripetere il cambio nel momento in cui il client sostituisce il riferimento dell'entità: il recovery non-roster deve riaccodare il setup, conservare una sola voce e non lasciare `Manusia=False` o il lock lifecycle occupato. Con tutti gli slot roster occupati, il classifier deve rilasciare il lock tra i retry, attendere il cleanup del vecchio riferimento e poi completare; nel fallback con player variables nuove è previsto il ripristino dei default. Per `งูแท้`, verificare inoltre che `Caladan Brood` resti bloccato e che un repair senza reset conservi le modifiche manuali a colore/icona.
- Confermare che menu e Teleport transitori vengano chiusi/riarmati senza handle orfani e che il fast-path non acquisisca il lock globale del join.
- Attivare Camera, status/effetti Try Your Luck e voti prima del cambio: il refresh leggero non deve cancellarli o ricrearli.
- Attivare Ghost e Fly separatamente prima del cambio: il refresh leggero deve conservarli e il runtime deve riapplicare la fisica selezionata dopo il ritorno in vita.
- Eseguire poi un leave vero durante o subito dopo il refresh: il cleanup deve rimuovere una sola volta roster e riferimenti, e il successivo rejoin deve passare dal setup fresco.

### Camera

- Alternare Camera rapida self/first-person con Interact 0,5 s sia a menu chiuso sia a menu aperto, sempre con Crouch rilasciato.
- A menu aperto provare `Crouch + Interact`: deve agire soltanto sul menu e non sulla Camera.
- Dal Menu Camera provare OFF, self e target diversi.
- Cambiare rapidamente target senza frame di Camera concorrenti.
- Uccidere, far uscire o despawnare il target: il riferimento deve tornare valido.
- Verificare collisione pareti e pitch estremo.
- Confermare che esista un solo raycast Camera dal punto di vista funzionale.

### Inspection e Privacy

- Con menu chiuso, tenere Crouch su alleati, nemici, bot e se stessi.
- Verificare icona eroe, nome e salute; nessuna percentuale Ultimate.
- Nuovo player o vero rejoin: Privacy OFF e cursore OFF per default; un cambio squadra leggero conserva invece lo stato e il cursore scelti.
- Privacy OFF: gli altri player vedono la riga completa e possono scegliere il player nella Camera custom; Vision ne mostra icona, nome e salute.
- Privacy ON: Camera custom, inspection, Teleport e Attach non possono scegliere o identificare il player; Vision deve comunque mostrarne icona, nome e salute.
- Attivare Privacy ON mentre uno o più player osservano il target con la Camera custom: tutti tornano alla visuale normale entro il ciclo lifecycle.
- Attivare Privacy ON mentre inspection sta già mostrando il target: nome/nameplate devono sparire entro il ciclo di cleanup e non ricomparire finché Privacy resta ON.
- Rilasciare Crouch, aprire menu, morire, cambiare Camera o target: cleanup immediato.

### Teleport

- Nuovo player: Menu 8 OFF, nessun overlay Teleport.
- Attivare Menu 8, chiudere menu e tenere Crouch.
- Crouch + Primary/Secondary navigano rispettivamente alla pagina successiva/precedente; Crouch + Interact esegue la pagina attiva.
- Spawn Room usa un punto valido della squadra.
- All Players sceglie un target vivo/spawnato vicino al reticolo e rispetta Privacy.
- Ricalcolare il target al click; morte/leave tra preview e click deve annullare o scegliere soltanto un fallback esplicito.
- Destinazione finale sempre camminabile o annullata in sicurezza.

## 7. Lifecycle e reset squadra

Eseguire con HUD, menu, Camera, inspection, Teleport, Unkillable, Revenge, voto e Try Your Luck in combinazioni diverse.

### Join/leave

- join umano e bot;
- evento Join duplicato o classificazione tardiva;
- ingresso transitorio con nome visibile `Null` o vuoto: non deve consumare uno slot roster e deve essere ritentato quando il nome diventa valido;
- leave con menu aperto e chiuso;
- leave durante ciascun sottosistema;
- leave di un target votato: ogni `PemainDipilih` che lo referenziava deve essere azzerato prima della rimozione dal roster e i conteggi devono essere ricalcolati;
- rientro nello stesso slot.

Accettazione: una sola riga roster, un solo set HUD, un solo messaggio di join/leave e nessun target stale.

### Bot e dummy

- verificare che dummy e bot AI non abbiano roster umano, HUD Arcade, menu o feedback/input Arcade;
- con due o più slot liberi, confermare al massimo un dummy nativo per squadra; con un solo slot libero, confermare che non venga creato;
- riempire la squadra: il dummy deve essere rimosso per rendere disponibile la capacità di 6 umani; ripetere ingressi e uscite vicino al limite e verificare assenza di cicli crea/distruggi o spam `Create Dummy Bot`;
- uccidere ciascun dummy e verificare respawn entro il limite configurato di 3 secondi; con D.Va/D.Mon, il de-mech non deve fermare definitivamente facing/throttle prima della morte completa;
- confermare che il lock dedicato resti applicato a spawn, respawn e cambio eroe senza attraversare setup/cleanup umano;
- verificare `Move Speed = 20%` sia per bot AI sia per dummy; gli iBot devono continuare a usare la propria navigazione nativa;
- colpire e spingere i dummy con sorgenti diverse: devono ricevere danni e knockback normali (`100%`), pur restando offensivamente passivi;
- a ogni spawn verificare che il dummy rimanga stabilizzato per circa 1 secondo e poi esca dalla Spawn Room solo verso una destinazione percorribile e valida per la modalità; se la destinazione non è disponibile deve restare in spawn, non finire a coordinate nulle o nel vuoto;
- fuori dalla Spawn Room, posizionare un alleato e un nemico vivo: il dummy deve ignorare l'alleato e avanzare automaticamente verso l'umano nemico più vicino;
- verificare che il dummy attraversi pareti e soffitti senza attraversare il pavimento o cadere fuori mappa, ma continui a collidere fisicamente con umani, bot e altri dummy; gli iBot devono conservare tutte le collisioni native;
- avvicinare il dummy entro 4 m dal nemico e verificare throttle zero; allontanare il nemico oltre la soglia e verificare la ripartenza automatica;
- con due umani nemici opt-in a distanze diverse, verificare che il dummy scelga sempre quello più vicino; invertire le distanze e controllare il riallineamento;
- sul player più vicino aprire pagina 12 e applicare Dummy Follow OFF: il dummy deve escluderlo subito e passare al successivo umano opt-in, anche se più lontano;
- portare tutti gli umani avversari a Dummy Follow OFF: facing e throttle devono fermarsi; riattivare ON per un player deve far ripartire l'inseguimento verso di lui;
- verificare che un iBot, un dummy, uno spectator, un umano morto/non spawned e un umano nel breve intervallo di cambio squadra non vengano mai scelti come target;
- uccidere/far uscire/cambiare squadra al target, eliminare tutti i nemici vivi, uccidere il dummy e riempire il team: facing e throttle devono essere fermati o riallineati senza riferimenti obsoleti;
- verificare che Anran e gli esiti Try Your Luck riservati agli umani non applichino funzioni o messaggi ai bot;
- mantenere bot/dummy come target passivi validi per Camera, inspection e Vision, senza consentire loro di attivare alcun sistema.

### Cambio squadra

- almeno **20 cambi squadra singoli** Team 1 ↔ Team 2;
- almeno **10 transizioni simultanee** di due o più player;
- una cascata di cambio squadra a lobby piena.

Dopo ogni cambio:

- nessun doppione roster o handle;
- Camera, status, effetti e voti attivi restano invariati; soltanto Menu Arcade e overlay Teleport vengono chiusi/riarmati e `HudKiri/HudKanan` vengono ricreati quando necessario;
- tutte le preferenze e i cursori restano invariati, inclusi lingua, colore, genere, icona, Teleport, Privacy, Dummy Follow, Ghost/Fly e il profilo dedicato `งูแท้`; soltanto stato dipendente dal Team e riferimenti transitori vengono aggiornati;
- Text Count ed Entity Count non crescono rispetto allo stato equivalente precedente al cambio;
- nessun `excessive Workshop script load`.

Eseguire separatamente un leave vero seguito da rejoin: non devono restare riferimenti stale e tutte le preferenze devono tornare ai default di setup; per `งูแท้` ciò significa `Silver Mist`, `Poison 2` e `Caladan Brood` bloccato.

## 8. Matrice modalità

Lo script non deve assegnare punti o vincitori. Scoring e obiettivi restano nativi, mentre completion, overtime ed estensioni del timer non devono sostituire il countdown CHILL, sincronizzato una volta al secondo. Eseguire almeno un segmento significativo per riga:

| Modalità | Objective/Teleport e uscita Spawn dummy | Transizioni da verificare |
|---|---|---|
| Push | proxy obiettivo + fallback Objective Position | robot/obiettivo, countdown CHILL invariato |
| Flashpoint | Objective Position dell'indice attivo | rotazione punti |
| Capture the Flag | bandiera nemica valida | presa, caduta, ritorno, score |
| Control | Objective Position | cattura/percentuale, countdown CHILL invariato |
| Clash | Objective Position | avanzamento/ritiro punti |
| Hybrid | Payload dopo la cattura | cattura → scorta |
| Escort | Payload | checkpoint/payload, countdown CHILL invariato |
| Assault | Objective Position | punto A → punto B |

Per ogni riga verificare sia il Teleport manuale sia l'uscita Spawn dei dummy: il punto finale deve essere percorribile, il fallback deve restare nella stessa famiglia di obiettivo e l'assenza temporanea della posizione non deve causare teleport a `Vector(0, 0, 0)` o nel vuoto.

Priorità mappe:

- Busan — modifiche dell'11 agosto;
- Eichenwalde — modifiche dell'11 agosto;
- Paraíso — modifiche dell'11 agosto.

In ogni modalità usare contemporaneamente Menu, Camera, inspection, Teleport e Try Your Luck senza alterare scoring o avanzamento degli obiettivi; il timer nativo deve essere riallineato al countdown CHILL a 1 Hz, non a ogni tick dello scheduler.

## 9. Soak 12 slot

Durata minima: **30 minuti** con 12 slot occupati.

Durante il soak:

- alternare combattimento, morti e Resurrect con Jump;
- aprire/chiudere e navigare menu su più player;
- usare Camera, inspection, Teleport e Try Your Luck;
- eseguire join/leave e alcuni cambi squadra;
- cambiare eroe, includendo D.Mon;
- lasciare attivi i dummy quando esistono almeno due slot liberi, quindi riempire progressivamente la lobby e verificare che vengano rimossi senza impedire l'ingresso di 12 umani;
- usare più utenti reali per la fase di input simultanei.

Accettazione:

- server fluido e input reattivi;
- nessun warning persistente di script load;
- nessuna crescita progressiva di HUD, In-World Text o effetti;
- countdown, RGB e minuti continuano con frequenze regolari;
- nessun conflitto con Team Status Indicator.

## 10. Diagnostica

Registrare baseline a lobby vuota, dopo 12 join, durante picco concorrente e dopo cleanup completo.

| Metrica | Limite | Obiettivo |
|---|---:|---:|
| Element Count | `< 32.768` | `≤ 26.000` |
| Largest Rule | `< 98 KB` | `≤ 80 KB` |
| Text Count | ritorno al baseline | nessuna crescita |
| Entity Count | ritorno al baseline | nessuna crescita |

Annotare anche Server Load corrente/medio/picco se disponibile. L'assenza di leak è più importante di un singolo picco transitorio: dopo chiusure, morti, leave e cambi squadra i contatori devono stabilizzarsi al baseline atteso per i player rimasti.

## 11. Rapporto da restituire

Usare questo schema:

```text
Build client:
Codice import:
Piattaforma/regione:
Data e durata:
Slot umani/dummy:

Import: PASS/FAIL
D.Mon: PASS/FAIL
EN/ID/TH e 14 menu: PASS/FAIL
Input simultanei: PASS/FAIL
Join/leave: PASS/FAIL
Dummy objective routing: PASS/FAIL
Dummy capacity/no-create-spam: PASS/FAIL
Dummy damage/knockback/collisions: PASS/FAIL
Dummy Follow nearest/opt-out: PASS/FAIL
FULL HP immunity/restore: PASS/FAIL
Try Your Luck Unkillable preserve/Skull bypass: PASS/FAIL
Try Your Luck × Fly physics preserve: PASS/FAIL
Ghost walls/floors/Fly 3D/idle: PASS/FAIL
Self Kill cooldown 3 s: PASS/FAIL
Jump Resurrect always-nearest-walkable/retry latch: PASS/FAIL
Privacy Camera/inspection/Teleport + override Vision: PASS/FAIL
Profilo งูแท้ default/editabilità/lock: PASS/FAIL
20 cambi singoli: PASS/FAIL
10 cambi simultanei: PASS/FAIL
Cascata full-lobby: PASS/FAIL
8 modalità: PASS/FAIL
Soak 30 min: PASS/FAIL

Element Count max:
Largest Rule:
Text Count baseline/max/finale:
Entity Count baseline/max/finale:
Server Load avg/max:

Screenshot/video:
Note e riproduzione problemi:
```

La 0.8.1 resta **static-ready / live-pending** finché i test obbligatori, i limiti e ogni anomalia riproducibile non vengono verificati nel client. Il blocco precedente è un modello da compilare, non un verbale numerico ricostruito retroattivamente.


### Dummy spawn iniziale

Con almeno due slot liberi per squadra, verificare live che entrambi i dummy compaiano vivi nella propria Spawn Room al primo avvio, senza morte all'origine della mappa. Il timestamp deve mantenerli stabili per circa 1 s prima dello spostamento a distanza visibile dall'obiettivo/bandiera (target 10 m, minimo accettato 6 m). Dopo una morte, il respawn resta 3 s e la stessa uscita sicura deve ripetersi. Portare poi una squadra alla capacità massima: il dummy deve essere rimosso, il sesto umano deve poter entrare e nessuna nuova creazione deve avvenire finché non tornano almeno due slot liberi.
