# Piano di test — versione 0.8.1

Stato: **live-ready**

I test live della 0.8.1 sono stati completati sul client aggiornato ad agosto 2026, inclusi reset completo al cambio squadra, profilo dedicato `งูแท้`, Ghost/Fly, cooldown Self Kill, Resurrect in-place con recupero dal vuoto, riapplicazione Fly post-morte e Camera per-frame senza blend traslazionale. Eventuali valori diagnostici numerici non forniti non vengono inventati.

Questa attestazione conserva il riscontro storico della 0.8.1. La release `v0.8.1` e il sorgente successivo su `main` sono revisioni distinte, come indicato nel [`README`](../README.md): associare ogni nuova esecuzione della matrice allo SHA effettivamente importato. In assenza di quel verbale, i gate automatici verdi non attestano da soli fluidità, isolamento degli input o assenza di leak nel client.

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
4. Abilitare la diagnostica host quando si acquisiscono le metriche. Il toggle lascia Inspector Recording disabilitato anche con Diagnostics ON, così il confronto non aggiunge il costo della registrazione.
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
| Morto | Jump | `Resurrect` sempre; resta sul punto con terreno, oppure usa `Nearest Walkable Position` e Teleport post-resurrezione nel vuoto; menu ancora visibile |

Sul caso Jump, provare morte su terreno normale, vicino a un bordo, durante Self Kill con overlay Crouch ancora attivo e nel vuoto profondo. Su terreno il player deve usare `Resurrect` nello stesso punto senza Teleport; nel vuoto l'unico raycast deve aprire il ramo di recupero, eseguire `Resurrect` senza condizioni e poi un solo `Teleport(Event Player, Nearest Walkable Position(Last Of(Position Of(Event Player))))` del player vivo. La destinazione non deve provenire da `PosisiMati` o da uno scratch calcolato prima della resurrezione. Jump deve funzionare anche con Menu, Crouch Travel, Camera o Try Your Luck in qualunque stato e non deve comparire alcun percorso `Abort` o verso la Spawn Room. Non sono ammessi validatore Travel condiviso, offset casuali, forcing di posizione, `Respawn`, `Wait` o `Loop`. Tenere premuto il pulsante non deve generare spam; rilasciare Jump e premerlo di nuovo deve sempre riarmare un nuovo tentativo. Gli effetti di ripristino devono partire soltanto dopo la conferma del ritorno in vita e non deve mai comparire il vecchio `Small Message` “Resurrect unavailable” o una sua traduzione.

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
9. Crouch Travel & Attach — OFF/ON.
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
- controllare glifi Thai, wrapping e la griglia esatta: Top `0/1/2` + contenuto `3`, Left `-2/-1/0/13` + Player Vibes `1..12`, Right `-16/0`;
- verificare con 1, 6 e 12 player Player Vibes a sinistra, una sola riga per umano e nessuna lista a destra; controllare che Team Status Indicator e kill feed nativi restino leggibili;
- confermare che sotto il roster Left non compaia uno `0` isolato con diagnostica disattivata, che i promemoria completi/`PLAYER VIBES` siano corretti in EN/ID/TH e che `CHILL STAR` compaia come HUD dedicato colorato (non incollato all'ultima riga roster);
- confermare che non compaiano titoli HUD o `Big Message`;
- verificare che una scelta invariata non ripeta Small Message, audio o effetto;
- controllare che esista un solo HUD Arcade: nessuna copia appare durante scroll, cambio pagina, morte o riapertura;
- verificare che il promemoria `Crouch + command` compaia nel menu ma non sia duplicato nell'HUD globale, senza riga vuota prima dei comandi o gap eccessivo sotto il titolo server.
- sulla riga Fly della pagina 13, verificare la guida `LOOK TO STEER | HOLD FORWARD: 100% > 500% IN 25s` / `ARAHKAN PANDANGAN | TAHAN MAJU: 100% > 500% DALAM 25dtk` / `บังคับด้วยมุมมอง | กดเดินหน้าค้าง: 100% > 500% ใน 25วิ`, senza testo obsoleto sulla sola direzione dello sguardo.

Focus dati:

- tutti i 100 generi, wrap `0 ↔ 99` e salti `±10`;
- tutti i 32 colori;
- Name Color parte da bianco (default) e la sua scelta aggiorna le sfumature degli altri menu senza renderle identiche tra loro;
- 37 icone con nome localizzato e indice 0 `Nothing`;
- 26 località server nello stesso ordine;
- label della località in ambra neon `Custom Color(255, 205, 110, 255)`, nettamente distinta dal cyan di `LOBBY & CHILL TIME`, in tutte e tre le lingue;
- nessun conteggio minuti individuale nel roster in EN/ID/TH; genere musicale e nome del player corretti;
- CHILL, generi, nomi player ed eroi invariati come nomi propri.

### Profilo `งูแท้`

- Entrare con il nome visibile esatto `งูแท้`: Name Color deve partire da `Silver Mist`, Player Icon da `Poison 2` e Player Vibes da `Draconian`.
- Modificare colore e icona dal menu, chiudere/riaprire e cambiare squadra: chiusura/riapertura deve conservare le modifiche, mentre il cambio squadra deve rieseguire il setup e riportare i default del profilo.
- Aprire Soundtrack: la pagina deve risultare read-only e Primary/Secondary, Interact e Ability 1/2 non devono cambiare `Draconian`.
- Verificare che `Draconian` non aumenti il catalogo globale: gli altri player continuano ad avere esattamente 100 generi e il normale wrap `0..99`.
- Uscire davvero dalla lobby e rientrare con lo stesso nome: il setup deve riapplicare `Silver Mist`, `Poison 2` e il Vibes bloccato.
- Entrare con un nome simile ma non identico: il profilo non deve attivarsi. Per verificare una rinomina dell'account, uscire davvero dalla lobby e rientrare con il nuovo nome prima di controllare che il profilo non venga riapplicato; nella stessa sessione resta invece attivo fino al rejoin. Entrare con un secondo player dallo stesso nome visibile esatto deve mostrare la limitazione nota del matching e applicare lo stesso profilo.

### Ghost Mode / Fly

- Al setup e dopo leave/rejoin o cambio squadra, verificare che Ghost e Fly siano entrambi OFF; cambio eroe, morte e Resurrect devono invece conservarne separatamente le scelte.
- Con solo Ghost ON, attraversare pareti e soffitti ma non pavimenti; la collisione con player, bot e dummy deve restare normale.
- Con solo Fly ON, verificare gravità zero, `Move Speed` nativo zero e collisione ambientale normale: il movimento deve provenire dal motore 3D, non dal throttle trasformato. Usare un'area libera sufficientemente ampia e registrare eroe, mappa, input, tempo e velocità effettiva; ripetere su più eroi senza buff di movimento prima delle prove con abilità. La baseline Fly uniforme è `5,5 m/s = 100%`, non una percentuale della velocità specifica dell'eroe.

| Prova | Risultato da verificare nel client |
|---|---|
| Orientamento | Con yaw nei quattro orientamenti cardinali e pitch `0°`, `+45°`, `−45°`, `+90°`, `−90°`, Forward segue sempre il mirino (anche verticale). Back resta opposto solo sul piano orizzontale; Left/Right restano strafe orizzontale relativo all'eroe senza inversioni durante la rotazione. |
| Rampa Forward pura | Con `Z > 0.050` e `−0.050 ≤ X ≤ 0.050`, partire da circa `5,5 m/s` (`100%`); dopo 5 s circa `9,9 m/s` (`180%`), dopo 10 s circa `14,3 m/s` (`260%`), dopo 25 s circa `27,5 m/s` (`500%`). Continuare oltre 25 s senza superare il cap e ripetere guardando in alto/basso. |
| Reset e analogico | Side/Back/diagonali non armano la rampa e restano alla baseline. Durante Forward aggiungere strafe, invertire o rilasciare: il timer si riarma e il nuovo Forward riparte dal `100%`. Con controller, input parziale riduce proporzionalmente la velocità; le diagonali non ricevono un bonus di modulo. |
| Hover | Rilasciare ogni input dopo volo orizzontale, verticale, rotazione e knockback: arresto al tick del motore e nessuna deriva persistente. Riprendere gli input senza scatto nella vecchia direzione. |
| Isolamento | Due player, anche con eroi diversi: uno tiene Forward per 25 s, l'altro fa strafe, hover o commuta Fly. Timer, velocità, direzione e toggle del primo non devono cambiare per azioni del secondo; ripetere invertendo i ruoli. |
| Unkillable | Ripetere salita/discesa, hover e misure a 0/5/25 s con Unkillable OFF, 1 HP e FULL HP. La protezione dagli urti non deve impedire gli impulsi di movimento Fly; questa interazione richiede conferma nel client. |
| Collisioni | Fly senza Ghost deve fermarsi contro muri/soffitti/pavimenti; con Ghost attraversa muri/soffitti ma non pavimenti. Verificare angoli, porte strette, cambi di pendenza e contatto con umani/dummy: nessun attraversamento non previsto o impulso trasferito a un altro player. |
| Ergonomia e fluidità | Provare rotazioni lente/rapide, inversioni avanti-indietro, passaggio per il pitch verticale e avvio/arresto sia in prima sia in terza persona. Annotare vibrazione, scatti, ritardo input, nausea e controllo a 500%; i gate statici non certificano questi aspetti. |

- Attivare insieme Ghost e Fly, poi disattivarli in ordine inverso: i due toggle devono restare indipendenti; Fly OFF ripristina gravità e movimento nativo normali e arresta la rampa senza interrompere un'eventuale Luck Acceleration ancora attiva; Ghost OFF ripristina la collisione ambientale completa. Con Fly ON, morire e usare Jump: al ritorno in vita il volo deve funzionare subito senza toggle OFF/ON manuale. Ripetere durante rampa e hover dopo cambio eroe, cambio squadra (riattivando Fly dal menu dopo il reset) e transizioni spawned/non-spawned; non deve rimanere `Move Speed = 0` quando Fly è OFF.
- Provare tutti gli esiti Try Your Luck con Fly attivo: nessun ramo deve impostare o ripristinare gravità, throttle trasformato o toggle Ghost/Fly. In particolare Acceleration deve possedere velocità e propulsione per tutti i 10 secondi: il motore Fly non deve applicare impulsi, freno idle o blocco del movimento nativo. Alla scadenza Fly riparte dal `100%` con una rampa fresca se Forward è tenuto, oppure resta immobile senza input. Ripetere entrando/uscendo da Fly a metà Acceleration e con un secondo player in Fly normale.

### Unkillable FULL HP

- Applicare FULL HP e ricevere contemporaneamente fuoco, danni periodici e urti/knockback da eroi e bot: salute e posizione non devono essere alterate.
- Attraversare e farsi attraversare da un umano e da un dummy: FULL HP non deve avere collisione con player/bot.
- Passare da FULL HP a OFF e ripetere le prove: danni, urti e collisione devono tornare normali.
- Passare da FULL HP a 1 HP: collisione e urti devono tornare normali, mentre resta soltanto la semantica curabile della modalità 1 HP.
- Partire da FULL HP e attivare Try Your Luck: modalità e cursore devono restare invariati. Vision, Acceleration, Team Heal e Hacked conservano status, immunità a danni/urti, assenza di collisione e icona; Burning li sospende per tutti i 10 secondi e li ripristina al termine. Soltanto lo Skull finale sospende la protezione per completare la morte; dopo Resurrect la preferenza e l'icona devono riattivarsi. Cambio squadra e leave/rejoin eseguono setup fresco e ripristinano i default.
- Partire da FULL HP, entrare/uscire dalla Spawn Room e morire: la scelta non deve essere cancellata. Dopo Resurrect verificare nuovamente danni zero, urti zero e assenza di collisione con player/bot; la stessa protezione deve restare attiva dentro la Spawn Room.
- Verificare con più player che l'immunità di un utente non venga trasferita al player successivo dello scheduler e non venga mai applicata a dummy/iBot.

## 5. Try Your Luck

Forzare o ripetere l'attivazione fino a osservare tutti gli esiti:

| Esito | Verifica |
|---|---|
| Vision | icona eroe, nome roster stabile e salute live in EN/ID/TH per bot/dummy e tutti gli umani, compresi quelli con Privacy ON; Crouch non crea inspection/Teleport o altri HUD; cleanup dopo 15 s |
| Acceleration | da fermo e senza input direzionali, propulsione automatica lungo la mira 3D; cleanup dopo 10 s |
| Skull | unico esito che bypassa Unkillable; D.Va: distruzione mech seguita dalla morte pilota; Echo: fine duplicazione seguita dalla morte base; cleanup/menu soltanto alla morte completa; protezione ripristinata dopo Resurrect |
| Team Heal (Heart) | salute completa a tutti i player vivi della squadra del proprietario; il messaggio resta solo al proprietario |
| Burning | 5% max HP ogni 1 s per 10 s; Unkillable e riduzione Damage Received sospesi per l'intera durata e ripristinati al termine; stop alla morte |
| Hacked | stato per 5 s, poi rimozione |

Per ciascun esito:

- durante ogni passaggio della roulette l'icona corrente deve restare agganciata a occhio/mirino con aggiornamento ogni frame; eseguire movimento, rotazione continua e inversione di 180° senza scatti o salti verso altri player;
- durante Vision seguire un soggetto che cammina, salta, cambia salute, colore ed eroe: un'unica targhetta con icona, nome e salute deve restare fluida sopra la stessa identità e aggiornare tutti i campi; ripetere mentre un altro player entra o esce;
- quando Skull compare soltanto come icona intermedia, il player deve restare vivo; il retry può iniziare esclusivamente se Skull è l'esito finale;
- durante la stessa roulette eseguire join/leave di un umano: la reevaluation `Visible To and Position` deve rendere tutte le sei icone visibili al roster umano corrente, senza includere bot;
- con Acceleration, lasciare completamente i tasti direzionali: il player deve partire da solo; ruotare poi la visuale davanti, in alto e in basso e verificare che `Facing Direction Of(Evaluate Once(player))` con `Direction Rate and Max Speed` segua continuamente la direzione 3D corrente;
- ripetere Acceleration con Fly ON: la propulsione Try Your Luck deve restare attiva per 10 secondi, mentre nessun ramo della roulette può scrivere gravità o avviare/fermare il throttle trasformato di Fly;
- Unkillable non cambia all'avvio: Mode, Kursor, flag runtime, status, modificatori e icona restano invariati;
- il menu non accetta comandi incompatibili durante lo stato bloccato;
- il countdown non salta o duplica tick;
- morte, timeout e hero swap annullano stato/status/effetti temporanei senza cancellare Mode/Kursor Unkillable; salvo il periodo Burning intenzionale, un hero swap da vivo non deve lasciare interrotti status/tripletta/icona Unkillable. Cambio squadra e leave/rejoin eseguono cleanup e setup fresco;
- rimuovere un iBot vivo durante Vision e verificare che il suo IWT sparisca senza creare roster, HUD o lifecycle umano;
- nessuna seconda roulette per lo stesso player parte mentre la prima è attiva;
- chiusure e riaperture non duplicano HUD, In-World Text o effetti.

Matrice obbligatoria Try Your Luck × Unkillable:

- ripetere i sei esiti con Unkillable OFF, 1 HP e FULL HP;
- con 1 HP e FULL HP, Vision, Acceleration, Team Heal e Hacked non devono mai rimuovere status, cambiare modalità/cursore o far sparire stabilmente l'icona;
- con Burning, verificare che ogni secondo venga applicato il 5% della Max Health anche partendo da 1 HP/FULL HP, senza modificare Mode/Kursor; Unkillable e la riduzione Damage Received devono restare sospesi per tutti i 10 secondi, senza riapplicazione fra i tick, e tornare immediatamente al termine o dopo un cleanup anticipato;
- con Skull finale, verificare il bypass temporaneo e la morte completa; premere Jump per Resurrect e confermare il ripristino della stessa modalità, della tripletta corretta e dell'icona entro il tick globale;
- lasciare scadere la deadline Skull quando `Kill` viene rifiutato: menu/input devono liberarsi e Unkillable deve tornare attivo senza alterare Mode/Kursor;
- ripetere un Revenge su target 1 HP e FULL HP: deve usare lo stesso bypass temporaneo, ma claimant, consumo debito, condizioni di commit e timeout devono restare identici ai test Revenge esistenti.

Verifica specifica HEART: ferire il proprietario, un alleato e un avversario, lasciando un altro alleato morto; l'esito deve riportare a salute piena soltanto tutti i vivi della squadra del proprietario, senza resuscitare i morti o curare gli avversari. Il messaggio resta soltanto al proprietario. Ripetere dopo un cambio squadra per verificare che venga usata la squadra corrente, senza cambiare menu, cursori o preferenze degli alleati.

### Revenge e morte completa

- Con D.Va bersaglio, verificare che il debito resti invariato al demech e scenda di uno soltanto alla morte della pilota.
- Durante il demech non devono comparire il prompt Jump né una falsa posizione di morte; entrambi devono essere registrati soltanto alla morte completa.
- Con Echo duplicata, verificare che la fine della copia non consumi il debito e che il retry prosegua fino alla morte della forma base.
- Un secondo claimant sullo stesso target deve essere rifiutato; se un altro attacker completa la kill, il primo claimant non consuma alcun debito e la morte viene registrata normalmente.
- Il cambio squadra di claimant o target deve annullare il pending senza consumare il debito, duplicare il claim o mostrare un falso successo; i riferimenti devono essere liberati come nel leave.
- Mercy, Torbjörn e altre forme/armi alternative non devono essere trattate come casi speciali: il criterio terminale resta esclusivamente `Is Alive == False`.

## 6. Camera, inspection e Teleport

### Crouch Travel & Attach

- Tenere Crouch e verificare le cinque pagine EN: `1/5 | TELEPORT: SPAWN ROOM`, `2/5 | TELEPORT: ACTIVE OBJECTIVE`, `3/5 | TELEPORT: PLAYER / BOT`, `4/5 | ATTACH: PLAYER / BOT` e `5/5 | SELF ELIMINATION`; ripetere con gli equivalenti specifici ID e TH.
- Verificare che ogni pagina mostri nell'ordine titolo, destinazione/posizione, target quando applicabile e azione; i comandi devono riflettere i binding reali, compreso dopo una rimappatura degli input.
- Verificare il singolo HUD per-player e la progressione 1→5 mint, cyan, blu, viola e rosa: istruzioni in tinta pastello e contenuto in tinta neon, senza contaminare cursore, colori o handle di un altro player.
- Primary avanza, Secondary torna indietro e Interact esegue sempre la pagina attiva; Primary/Secondary non devono eseguire il teleport o la kill.
- Sulla pagina Self Elimination, testo ed effetto devono specificare la forma eroe corrente. Interact deve eseguire una sola richiesta per pressione e nessun'altra pagina deve essere attivata nello stesso hold. Un secondo tentativo entro 3 secondi non deve uccidere e deve mostrare il tempo residuo localizzato; morte e Resurrect non devono azzerare il cooldown, mentre cambio squadra e vero leave/rejoin devono inizializzarlo di nuovo con il setup fresco.
- Agganciarsi a un umano e a un dummy: i piedi devono restare separati dalla testa del target tramite l'offset previsto.
- Da attaccati, Reload senza Crouch deve restare l'azione nativa dell'eroe.
- Con Menu Arcade Melee chiuso, Crouch + Reload deve sganciare; con Menu Arcade Melee aperto non deve sganciare.
- Morte, leave/despawn, cambio eroe proprio o del target e Privacy ON del target umano devono sganciare automaticamente.

### Cambio squadra / lifecycle 0.8.1

- Ripetere Team 1 → Team 2 → Team 1 almeno 20 volte con un solo umano, controllando che non compaia `excessive Workshop script load` e che il roster conservi una sola voce.
- Ripetere con 2, 6 e 12 umani cambiando squadra quasi simultaneamente: ciascun player già registrato deve attraversare il reset completo (`TenangkanPemain` + `BersihkanPemain`) e rientrare dal classifier/setup senza duplicazioni.
- Durante la transizione verificare che `01a` apra soltanto la quarantena e armi la stabilizzazione a 0,5 s, senza cleanup pesante. Con team e spawn stabili, `01b` deve usare il contesto già prenotato per lo stesso player ed eseguire `TenangkanPemain`, `BersihkanPemain` se l'identità è ancora nel roster e `SiapkanPemain` con l'`Event Player` corretto. La vecchia voce viene rimossa prima della nuova registrazione e ricreata una sola volta. Gli array canonici devono conservare gli handle fino alla distruzione e al rilascio dello slot; lo scheduler globale non deve eseguire cleanup locali fuori contesto.
- Cambiare squadra mentre il player è morto e durante hero select/prima di `Has Spawned`: la quarantena deve impedire l'uso dello stato precedente; dopo spawn e team stabili, cleanup e setup devono ricostruire correttamente HUD/stato senza trattenere il lock mentre il player non è spawned.
- Eseguire anche uno switch diretto mentre il player è ancora spawned/vivo: dopo la stabilizzazione il reset completo deve liberare lock e riferimenti prima della nuova registrazione, senza percorsi `Abort` o dipendenze da `Server Load` nel teardown.
- Da un secondo player mantenere Crouch e la mira sul player per tutta la transizione: il vecchio In-World Text deve sparire durante il cleanup e tornare solo dopo la nuova registrazione con nome, icona eroe e HP corretti.
- Ripetere il cambio nel momento in cui il client sostituisce il riferimento dell'entità: lo slot precedente deve tornare libero, il nuovo riferimento deve registrarsi senza lasciare `Manusia=False` o lock lifecycle occupato. Con tutti gli slot roster occupati, il classifier deve rilasciare il lock tra i retry e completare appena il cleanup libera lo slot. Per `งูแท้`, verificare che il setup riapplichi `Silver Mist`, `Poison 2` e `Draconian`.
- Confermare che menu e Teleport transitori vengano chiusi/riarmati senza handle orfani e che il detector individuale non acquisisca il lock globale del join.
- Attivare Camera, status/effetti Try Your Luck e voti prima del cambio: il reset completo deve chiuderli/pulirli in modo deterministico, senza riferimenti ereditati. Ripetere Team 1 → Team 2 → Team 1 rapidamente con menu, Camera self/watch, Fly e ciascun effetto Luck attivi: nessuna Camera, accelerazione, gravità zero o status deve sopravvivere al reset; con Fly OFF il movimento nativo deve essere normale.
- Attivare Ghost e Fly separatamente prima del cambio: dopo il reset devono tornare OFF e riattivarsi solo da menu.
- Eseguire poi un leave vero durante o subito dopo il cambio: il cleanup deve rimuovere una sola volta roster e riferimenti, senza doppio passaggio. Con due player, tenere il secondo su un menu diverso e in Fly/Luck mentre il primo cambia due volte squadra: cursore, timer, fisica e HUD del secondo devono restare invariati, salvo i riferimenti sociali esplicitamente invalidati.

### Camera

- Alternare Camera rapida self/first-person con Interact 0,5 s sia a menu chiuso sia a menu aperto, sempre con Crouch rilasciato.
- A menu aperto provare `Crouch + Interact`: deve agire soltanto sul menu e non sulla Camera.
- Dal Menu Camera provare OFF, self e target diversi.
- Cambiare rapidamente target senza frame di Camera concorrenti.
- Uccidere, far uscire o despawnare il target: il riferimento deve tornare valido.
- Verificare collisione pareti e pitch estremo.
- Ruotare lentamente, rapidamente e di 180° da fermi, in corsa, in strafe, in salto e vicino a pareti/angoli: posizione e look-at per-frame con `Blend Speed 0` devono seguire la traslazione senza vibrazione, recuperi ritardati o clipping persistente. Ripetere sia sulla propria Camera sia osservando ciascun altro player.
- Confermare che esista un solo raycast Camera dal punto di vista funzionale.

### Inspection e Privacy

- Con menu chiuso, tenere Crouch su alleati, nemici, bot e se stessi.
- Verificare icona eroe, nome e salute nello stesso IWT, ancorato 0,450 m sopra `Eye Position`; durante corsa, strafe, salto e rotazione continua la targhetta deve seguire fluidamente la stessa identità, aggiornando salute, eroe e colore senza vibrare o trasferirsi al target successivo. Nessuna percentuale Ultimate.
- Nuovo player, cambio squadra o vero rejoin: Privacy OFF e cursore OFF per default.
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
- Player / Bot sceglie un target vivo/spawnato vicino al reticolo e rispetta Privacy.
- Nelle pagine Player/Bot Travel e Attach, muovere e cambiare stato del target: la singola targhetta icona/nome/salute deve seguire fluidamente l'identità selezionata e aggiornare testo e colore; cambiando target il vecchio handle non deve spostarsi sul nuovo soggetto.
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
- rientro nello stesso slot;
- con tutti i 12 slot occupati, far uscire un umano con menu, Camera, Vision, effetto Luck e voti attivi e far entrare un player diverso: dopo la guardia leave di 0,5 s lo slot deve essere libero e il nuovo setup deve partire dai default, senza dati Revenge, voti, timer, privacy o HUD ereditati;
- ripetere alternando due identità nello stesso slot e facendo join mentre il cleanup è ancora in attesa: un evento leave tardivo non deve cancellare le nuove righe HUD. Confrontare Text Count ed Entity Count in stati equivalenti prima e dopo, per rilevare anche handle persi che non compaiono più negli array di tracking.

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
- verificare che muri, soffitti e pavimenti fermino il dummy e che le collisioni con umani, bot e altri dummy siano abilitate; ripetere dopo respawn e cambio eroe. Gli iBot devono conservare tutte le collisioni native;
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
- Camera, status, effetti, voti e overlay attivi devono essere puliti senza lasciare riferimenti stale;
- tutte le preferenze e i cursori devono tornare ai default di setup, inclusi lingua, colore, genere, icona, Teleport, Privacy, Dummy Follow, Ghost/Fly e profilo `งูแท้`;
- Text Count ed Entity Count non crescono rispetto allo stato equivalente precedente al cambio;
- nessun `excessive Workshop script load`.

Eseguire separatamente un leave vero seguito da rejoin: non devono restare riferimenti stale e tutte le preferenze devono tornare ai default di setup; il cambio squadra deve seguire lo stesso risultato. Per `งูแท้` ciò significa `Silver Mist`, `Poison 2` e `Draconian` bloccato.

## 8. Matrice modalità

Lo script non deve assegnare punti o vincitori. Scoring e obiettivi restano nativi, mentre completion, overtime ed estensioni del timer non devono sostituire il countdown CHILL, sincronizzato una volta al secondo. Eseguire almeno un segmento significativo per riga:

| Modalità | Objective/Teleport e uscita Spawn dummy | Transizioni da verificare |
|---|---|---|
| Push | proxy obiettivo + fallback Objective Position | robot/obiettivo, countdown CHILL invariato |
| Flashpoint | Objective Position dell'indice attivo | rotazione punti |
| Capture the Flag | bandiera nemica valida | presa, caduta, ritorno, score |
| Control | Objective Position | cattura/percentuale, countdown CHILL invariato |
| Clash | Objective Position | avanzamento/ritiro punti |
| Hybrid | Dummy: primo obiettivo prima della cattura, poi payload; Teleport manuale: payload | cattura → scorta |
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
- countdown e RGB continuano con frequenze regolari; non compare alcun conteggio dei minuti individuali;
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
Commit SHA del sorgente importato:
Tag/release di provenienza (se presente):
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
Ghost walls/floors and Fly collisions: PASS/FAIL
Fly yaw cardinali/pitch 0° ±45° ±90°/strafe: PASS/FAIL
Fly 5,5→27,5 m/s / rampa 100→500 in 25 s / reset: PASS/FAIL
Fly analogico/diagonali/hover/ergonomia: PASS/FAIL
Fly due player indipendenti/lifecycle: PASS/FAIL
Self Kill cooldown 3 s: PASS/FAIL
Jump Resurrect same-point/void-live-nearest-walkable/retry latch: PASS/FAIL
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

La 0.8.1 è **live-ready**: test obbligatori, limiti e anomalie riproducibili sono stati verificati nel client. Il blocco precedente resta il modello di raccolta da compilare ad ogni nuova revisione, non un verbale numerico ricostruito retroattivamente.


### Dummy spawn iniziale

Con almeno due slot liberi per squadra, verificare live che entrambi i dummy compaiano vivi nella propria Spawn Room al primo avvio, senza morte all'origine della mappa. Il timestamp deve mantenerli stabili per circa 1 s prima dello spostamento a distanza visibile dall'obiettivo/bandiera (candidati a 8 e 12 m su otto direzioni, posizione finale accettata fra 6 e 16 m). Dopo una morte, il respawn resta 3 s e la stessa uscita sicura deve ripetersi. Portare poi una squadra alla capacità massima: il dummy deve essere rimosso, il sesto umano deve poter entrare e nessuna nuova creazione deve avvenire finché non tornano almeno due slot liberi.

### Small Message e transizione Crouch Travel

- Navigare rapidamente `1→2→3→4→5→1` e in senso inverso: mint, cyan, blu, viola e rosa devono fondersi in circa 0,18 s senza scatti o ricreazioni extra del renderer.
- Verificare che apertura/chiusura menu, selezioni riuscite, toggle, camera normale e Teleport riusciti non generino conferme Small Message ridondanti. Errori delle altre funzioni, cooldown, Attach con istruzione di detach e risultati Try Your Luck/Revenge devono restare notificati; il percorso Jump Resurrect non deve invece mostrare “Resurrect unavailable” né le equivalenti stringhe ID/TH, anche se il motore non conferma subito il ritorno in vita.

## Regressione dummy Paraíso — 2026-09-08

- Su Paraíso, creare i dummy di entrambe le squadre prima della cattura del primo punto: dopo il ritardo iniziale devono cercare un'uscita nei pressi dell'obiettivo, anche se il primo candidato viene rifiutato.
- Ripetere dopo morte/respawn, rimozione/ricreazione e cambio lato; verificare anche la fase payload dopo la cattura.
- Confermare che un dummy già uscito dalla spawn smetta di essere teletrasportato e che due dummy ritentino in modo indipendente.
- I test automatici eseguono le regole reali con risposte geometriche controllate; non sostituiscono questa prova della navmesh e delle spawn room nel client.

## Regressione stabilità e accumulo — 2026-09-09

- Con 12 player, aprire e scorrere contemporaneamente Menu Arcade e tutte le cinque pagine Crouch Travel & Attach. Il cambio pagina deve mantenere un solo HUD per proprietario; chiusura, riapertura e cambio lingua devono restare corretti.
- Attivare Vision e altri effetti temporanei, poi uscire durante l'effetto. Ripetere anche con dummy e iBot. Dopo la pulizia, i testi del player uscito devono sparire e i contatori HUD/IWT devono tornare al livello previsto per le sole funzioni ancora attive.
- Eseguire gruppi di uscite simultanee, nuovi ingressi e cambi squadra. Ripetere il ricambio per 30–60 minuti: i 12 slot umani devono restare riutilizzabili e il numero delle risorse non deve crescere da un ciclo al successivo.
- Provare Unkillable 1 HP e FULL HP, cure, morte/rinascita, cambio eroe, Skull, Burning, Fly e Attach contemporaneamente. Confermare i bypass temporanei di Skull/Burning e il ripristino della protezione al termine.
- Effettuare voti contemporanei, auto-voto, cambio voto e uscita del candidato: i conteggi e CHILL STAR devono convergere al successivo tick, senza voti del player scomparso e senza un vincitore in caso di pareggio.
- Vision deve escludere immediatamente chi disattiva l'effetto o lascia la lobby. Nuovi ingressi devono rispettare le targhette nascoste dei viewer in ispezione o Teleport.
- Annotare l'eventuale messaggio preciso di chiusura e le funzioni attive al momento. I test Python eseguono il flusso del sorgente con primitive native controllate; non simulano collisioni, rete, durata degli oggetti nativi o limiti del server Overwatch.

## Regressione riduzione picchi, Player Vibes e collisioni — 2026-09-15

- Registrare SHA importato, build client, mappa, numero di player, messaggio esatto di eventuale chiusura e Server Load medio/picco. Confrontare Text Count ed Entity Count nativi a funzioni chiuse prima/dopo il ricambio, oltre agli array del pannello interno.
- Ripetere una lobby piena con menu e ingressi/uscite, poi aggiungere Camera, targhette Inspection/Travel, roulette e Fly/Attach separatamente prima della prova combinata. Mantenere Inspector Recording disabilitato durante i confronti.
- Alternare rapidamente bersagli in Inspection e Travel: nessuna targhetta precedente deve rimanere sul nuovo soggetto; ammettere fino a circa 0,25 s prima della nuova creazione. Target stabile: testo e posizione continuano ad aggiornarsi senza ricreare l'handle. Privacy, morte, leave e chiusura devono rimuovere subito i riferimenti rilevati dal runtime; Teleport/Attach devono ancora validare il bersaglio al comando.
- Verificare nove HUD fissi e una sola riga Player Vibes per umano: 21 handle a lobby piena e funzioni chiuse. Ripetere join/leave e cambio squadra: nessuna duplicazione, minuti individuali o seconda lista. Countdown server e CHILL STAR restano attivi. Verificare a destra `Host:` nel campo Text, con una riga vuota sopra e sotto e icona eroe e nome corretti, in EN/ID/TH e dopo cambio eroe, passaggio host e uscita dell’host precedente. Confermare la distanza dall'indicatore nativo e dal kill feed.
- Avviare 12 roulette insieme e con partenze sfalsate, includendo wrap del contatore, uscite e slot riutilizzati. Nessuna roulette deve restare bloccata; un esito si applica una sola volta e la durata dell'effetto parte dall'esito effettivo, non dall'avvio della rotazione.
- Provare dummy contro muri, soffitti, pavimenti e altri giocatori con collisione normale, prima/dopo respawn e cambio eroe. L'uscita automatica dalla spawn resta un teleport soltanto verso destinazioni validate; fuori spawn il follow può fermarsi contro gli ostacoli.
- Proseguire il ricambio per 30–60 minuti. Un run senza errore riduce l'incertezza per quella configurazione, ma non sostituisce la registrazione delle metriche e del commit provato.
