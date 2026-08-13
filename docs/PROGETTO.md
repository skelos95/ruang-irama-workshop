# Note di progetto — versione 0.5.2

## Identità e obiettivo

Il nome mostrato nel gioco è **AFK Dedicated Server** e la posizione visualizzata è **Indonesia**. Il progetto è un overlay Workshop sociale per lobby personalizzate: aggiunge strumenti AFK e Arcade senza diventare un preset completo.

La release 0.5.2 migliora la fluidità della camera sulla base Season 4 **Heroes of Busan**, iniziata l'11 agosto 2026. La compatibilità da verificare nel client comprende D.Mon e gli aggiornamenti di Busan, Paraíso ed Eichenwalde indicati nelle [note ufficiali della patch](https://us.forums.blizzard.com/en/overwatch/t/overwatch-retail-patch-notes-%E2%80%93-august-11-2026/1032368).

Il sorgente non contiene `settings`. L'importazione non cambia modalità, mappe, roster, slot, composizione delle squadre o altre opzioni della lobby.

## Contratto delle modalità 6v6

L'overlay supporta le modalità core Control, Escort, Hybrid, Push, Flashpoint e Clash. Le loro logiche native sono diverse, ma condividono un unico contratto di sessione:

- obiettivi e condizioni native non assegnano punti;
- nessuna squadra o giocatore viene dichiarato vincitore;
- non viene dichiarato un pareggio;
- la partita non termina quando una modalità raggiunge la propria condizione nativa;
- la sessione termina soltanto allo zero del countdown personalizzato;
- allo zero viene eseguito una sola volta `Restart Match`, che resetta la sessione senza assegnare un risultato.

Il timer non dipende da `Match Time`. All'avvio conserva una propria origine e calcola una scadenza dalla durata configurata con `Server duration (minutes)`, compresa tra 30 e 90 minuti. Il valore visualizzato viene aggiornato una volta al secondo, sufficiente per un countdown in secondi e meno costoso di una rivalutazione per frame.

## Registro, classificazione e ciclo di vita

La lista degli umani è la fonte dei due elenchi sociali. Camera, Crouch e Teleport possono invece usare tutti i giocatori presenti e validi, perché devono includere anche bot AI e dummy bot.

La classificazione segue questa sequenza:

1. lo stato per-player viene preparato una sola volta, anche per chi era già presente quando le regole sono state avviate;
2. un dummy bot viene riconosciuto direttamente tramite `Is Dummy Bot`;
3. per gli altri viene applicato il workaround del nome invisibile `U+200B` per distinguere i normali bot AI;
4. dopo ciascuno dei due `Wait(0.016)` viene verificato `Entity Exists`;
5. prima di registrare un umano viene eseguito un ultimo controllo di esistenza e classificazione.

La registrazione è quindi atomica dal punto di vista del Workshop: un giocatore che esce durante i due tick di riconoscimento non può essere aggiunto in ritardo alle liste. Il carattere `U+200B` resta un workaround comunitario e non un contratto API Blizzard; va verificato nel client dopo ogni patch.

Il blocco dei bot è edge-triggered. Viene applicato al termine della classificazione; la transizione a morto o non spawnato abbassa il latch e una seconda regola `Ongoing - Each Player` lo riafferma soltanto quando il bot torna vivo oppure cambia eroe. Questo copre anche despawn e passaggi di round, usa esclusivamente tipi evento riconosciuti dal parser ed evita un watchdog permanente ogni mezzo secondo. Fuoco, abilità, Ultimate e comandi sociali restano bloccati; il movimento necessario alla lobby può rimanere disponibile.

### Cleanup dell'uscita

Il cleanup usa i registri globali perché le variabili del player uscente possono non essere più affidabili. Anche lo slot riutilizzabile è conservato nel registro parallelo `SlotHUDPemain`, anziché essere letto dall'entità già uscita. Prima di rimuovere lo slot:

- distrugge HUD, menu e testi nel mondo ancora esistenti;
- interrompe camera e ispezione e invalida le rispettive cache;
- ripristina nameplate e outline dove ancora applicabile;
- elimina il player da tutti i ledger Revenge dei superstiti;
- rimuove in modo allineato gli elementi degli array paralleli;
- restituisce lo slot HUD al pool limitato a `0..11`.

Il riuso degli slot evita che il numero d'ordine cresca senza limite dopo molti cicli join/leave. Se l'uscente non è un umano registrato, il cleanup non altera gli array sociali.

## HUD e localizzazione per viewer

Ogni viewer sceglie in modo indipendente una delle tre lingue:

| Indice | Lingua |
|---:|---|
| `0` | English |
| `1` | Bahasa Indonesia |
| `2` | ไทย |

Il cambio lingua usa modulo 3 e rivaluta immediatamente HUD, menu, nomi dei colori, messaggi e titoli musicali. I 100 nomi internazionali dei generi restano invariati. L'inglese è la lingua iniziale.

Le traduzioni sono scritte per risultare naturali nella lingua di destinazione, non come calchi parola per parola. La localizzazione thai deve inoltre essere verificata nel client per glifi, wrapping e dimensioni alle diverse risoluzioni.

Gli elementi condivisi leggono la lingua di `Local Player`, così due client possono vedere gli stessi dati con etichette diverse senza duplicare gli HUD globali. Le keyword e le azioni native Workshop restano obbligatoriamente in inglese; identificatori, subroutine, regole e commenti personalizzati sono in Bahasa Indonesia.

## Menu e dispatcher degli input

Melee tenuto per 0,5 secondi apre o chiude il menu. Il rilascio arma il toggle successivo, impedendo ripetizioni mentre il tasto resta premuto.

Il menu principale contiene sei voci:

| Indice | Funzione |
|---:|---|
| `0` | Soundtrack |
| `1` | Third-Person Camera |
| `2` | Name Color |
| `3` | HUD Language |
| `4` | Revenge |
| `5` | Teleport |

Un solo dispatcher gestisce gli input con priorità deterministica `Interact → Reload → Primary → Secondary → Jump → Crouch`. Dopo aver scelto l'azione, consuma l'intero chord e si riarma soltanto quando tutti e sei gli input sono stati rilasciati: i tasti a priorità inferiore non possono quindi scattare in coda. Primary e Secondary cambiano la selezione di `+1` e `−1`; nel menu Soundtrack Jump e Crouch saltano rispettivamente `−10` e `+10`. Interact entra nel sottomenu o applica la scelta, mentre Reload ritorna al menu principale.

I menu dinamici Revenge e Teleport aggiornano dati e cursore senza distruggere e ricreare periodicamente l'intero HUD. Le stringhe rivalutate leggono lo stato corrente, riducendo churn di entità e rischio di ID orfani.

## Revenge

Revenge registra soltanto il killer diretto umano, non assist, bot o danno ambientale. Alla morte il relativo flag viene azzerato immediatamente, poi il ledger viene aggiornato.

Quando un claim parte, il bersaglio viene catturato per identità prima di `Kill`. Lo stesso riferimento viene usato per flag, eliminazione e messaggio; non esiste una rilettura differita di array, cursore o claimant. La regola `Player Died` azzera il flag del bersaglio, mentre l'uscita di un giocatore lo rimuove dai ledger di tutti i superstiti, evitando voci fantasma o indici spostati.

## Teleport

Il menu Teleport comprende l'ultima Spawn Room visitata, la destinazione dell'obiettivo corrente quando disponibile e i giocatori presenti, inclusi bot AI e dummy bot validi. La posizione salvata viene aggiornata a ogni nuovo ingresso in spawn, così segue anche le spawn avanzate di Escort e Hybrid. Il viewer non compare come propria destinazione.

Il teletrasporto verso un giocatore cerca una posizione camminabile vicina al bersaglio invece di sovrapporre i due corpi. Prima dell'azione vengono ricontrollati esistenza e validità della destinazione; se il target è uscito, morto o non più disponibile, l'azione viene annullata con un messaggio localizzato.

## Crouch e ispezione

Fuori dal menu, Crouch attiva l'ispezione per quel viewer. Le nameplate native vengono disabilitate una sola volta all'ingresso e ripristinate in ogni percorso di uscita: rilascio, apertura menu, morte, cambio modalità camera o uscita dalla partita.

Il target vicino al reticolo viene aggiornato ogni 0,10 secondi scorrendo soltanto i giocatori presenti. Viewer, entità non spawnate, morte o inesistenti vengono escluse. Nome, eroe effettivo e percentuale Ultimate restano rivalutati; durante Duplicate di Echo viene mostrato l'eroe duplicato.

Gli outline e i testi usano il colore personale per gli umani e arancione per i bot. Gli aggiornamenti che dipendono dal colore sono event-driven, per esempio dopo join o applicazione di un nuovo colore. Il cleanup arresta gli outline e distrugge entrambi i testi in ogni percorso, prevenendo residui IWT.

## Camera in terza persona

La camera può seguire il viewer o un altro giocatore valido, inclusi bot. Per ogni aggiornamento calcola e conserva in cache:

1. l'anchor sopra il bersaglio;
2. la posizione ideale dietro la spalla;
3. l'unico risultato del raycast contro la geometria;
4. la posizione finale con margine dalla parete;
5. l'offset relativo rispetto alla posizione del bersaglio;
6. il punto verso cui guardare.

Il singolo raycast per tick sostituisce espressioni duplicate e riduce il carico con più camere simultanee. La posizione base del bersaglio viene rivalutata per fotogramma e combinata con l'offset relativo in cache; `Start Camera` usa un blend nativo pari a `80`. L'arretramento usa soltanto lo yaw, così pitch e rinculo non fanno orbitare verticalmente la camera. La collisione conserva il margine lungo il raggio ma non applica più un abbassamento verticale variabile vicino agli spigoli.

Altezza, distanza e offset vengono comunque ricalcolati dal modello corrente: questo è importante per D.Mon e per trasformazioni che possono cambiare ingombro senza un normale cambio eroe. La fluidità percepita, le collisioni e il minimo jitter possibile sui bersagli remoti restano verifiche live. Se il bersaglio esce o non è più valido, la camera termina e il viewer torna alla visuale normale.

## Diagnostica e prestazioni

`Performance diagnostics` è disattivato per impostazione predefinita. In questo stato non mantiene la registrazione Inspector dedicata. Quando l'host lo abilita, un HUD privato mostra:

- carico server corrente;
- carico medio;
- picco;
- conteggio HUD;
- conteggio IWT.

Le etichette seguono la lingua HUD scelta dall'host. Nessun altro giocatore riceve la diagnostica. Gli obiettivi live per una lobby piena sono `Server Load Average < 80%`, `Server Load Peak < 100%`, nessun warning o arresto e nessuna crescita permanente degli oggetti dopo join/leave.

Il validatore statico può controllare struttura, invarianti e assenza di azioni di scoring, ma non può simulare il runtime di Overwatch. Stabilità con 12 giocatori, rendering thai, compatibilità D.Mon/mappe e workaround bot restano prove live obbligatorie.

## Vincoli noti

- Il progetto non crea automaticamente il preset 6v6: modalità e mappe devono essere configurate nella lobby.
- Le patch Blizzard possono cambiare parser, limiti Workshop, comportamento dei bot o geometrie delle mappe.
- Una compilazione statica pulita non equivale a una sessione live stabile.
- Il codice breve condivisibile può essere generato soltanto dal client Overwatch.
