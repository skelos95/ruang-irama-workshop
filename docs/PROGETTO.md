# Note di progetto — versione 0.5.5

## Identità e obiettivo

Il nome mostrato nel gioco è **CHILL Dedicated Server** e l’HUD superiore mostra **SERVER LOCATION** con un paese configurabile dalle Workshop Settings; il valore predefinito è **Indonesia**. Il progetto è un overlay Workshop sociale per lobby personalizzate: aggiunge strumenti CHILL e Arcade senza diventare un preset completo.

La release 0.5.5 stabilizza i percorsi non-camera di menu, Crouch, nameplate, Teleport e lifecycle sulla base Season 4 **Heroes of Busan**. La camera in terza persona conserva byte-per-byte logica, valori, raycast e menu della 0.5.4. La compatibilità da verificare nel client comprende D.Mon e gli aggiornamenti di Busan, Paraíso ed Eichenwalde indicati nelle [note ufficiali della patch](https://us.forums.blizzard.com/en/overwatch/t/overwatch-retail-patch-notes-%E2%80%93-august-11-2026/1032368).

Lo stato di release è **static-ready, live-pending**: un gate statico superato non equivale al completamento delle prove nel client.

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

Gli umani e i normali bot AI seguono questa sequenza di preparazione e classificazione:

1. lo stato per-player viene preparato una sola volta, anche per chi era già presente quando le regole sono state avviate;
2. viene applicato il workaround del nome invisibile `U+200B` per distinguere i normali bot AI;
3. dopo ciascuno dei due `Wait(0.016)` viene verificato `Entity Exists`;
4. prima di registrare un umano viene eseguito un ultimo controllo di esistenza e classificazione.

La registrazione è quindi atomica dal punto di vista del Workshop: un giocatore che esce durante i due tick di riconoscimento non può essere aggiunto in ritardo alle liste. Il carattere `U+200B` resta un workaround comunitario e non un contratto API Blizzard; va verificato nel client dopo ogni patch.

I dummy bot non entrano in questa pipeline e non attraversano il ramo di classificazione: il lifecycle edge-triggered li riconosce direttamente con `Is Dummy Bot` e richiama `KunciBot` quando diventano entità valide e spawnate. Per i normali bot AI il blocco viene applicato al termine della classificazione. In entrambi i casi la transizione a morto o non spawnato abbassa il latch e la regola lifecycle lo riafferma soltanto quando il bot torna vivo oppure cambia eroe. Questo copre anche despawn e passaggi di round, usa esclusivamente tipi evento riconosciuti dal parser ed evita un watchdog permanente ogni mezzo secondo. Fuoco, abilità, Ultimate e comandi sociali restano bloccati; il movimento necessario alla lobby può rimanere disponibile.

Quando un umano viene registrato oppure un bot viene bloccato/spawnato, la sua nameplate viene disabilitata per tutti i viewer che stanno già ispezionando. In questo modo l'insieme nascosto non resta congelato alla fotografia iniziale del Crouch.

### Cleanup dell'uscita

Il cleanup usa i registri globali perché le variabili del player uscente possono non essere più affidabili. Anche lo slot riutilizzabile è conservato nel registro parallelo `SlotHUDPemain`, anziché essere letto dall'entità già uscita. Prima di rimuovere lo slot:

- distrugge HUD, menu e testi nel mondo ancora esistenti;
- interrompe camera e ispezione e invalida i rispettivi riferimenti;
- ripristina le nameplate dove ancora applicabile;
- elimina il player da tutti i ledger Revenge dei superstiti;
- rimuove in modo allineato gli elementi degli array paralleli;
- restituisce lo slot HUD al pool limitato a `0..11`.

Il riuso degli slot evita che il numero d'ordine cresca senza limite dopo molti cicli join/leave. Se l'uscente non è un umano registrato, il cleanup non altera gli array sociali.

Menu e ispezione hanno inoltre cleanup per-player sui passaggi di stato in cui l'entità resta nel server ma non è più giocabile: morte, despawn, hero-select e passaggio a spettatore. I percorsi ripristinano pulsanti e nameplate e distruggono HUD e testi prima di azzerare i latch.

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

Melee tenuto per 0,5 secondi apre o chiude il menu. Alla chiusura, se Melee è ancora premuto il latch resta armato fino al rilascio; altrimenti il pulsante viene riabilitato immediatamente e il latch azzerato. Questo evita che morte o despawn durante i 0,5 secondi lascino Melee bloccato.

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

Revenge registra soltanto il killer diretto umano, non assist, bot o danno ambientale. Alla morte il relativo flag viene azzerato immediatamente, poi il ledger viene aggiornato. Il menu mostra intenzionalmente tutti gli altri umani, compresi quelli con debito `0`; il claim resta però vietato finché il debito non è positivo. Anche lo stato vuoto è localizzato in English, Bahasa Indonesia e ไทย.

Quando un claim parte, il bersaglio viene catturato per identità prima di `Kill`. Lo stesso riferimento viene usato per flag, eliminazione e messaggio; non esiste una rilettura differita di array, cursore o claimant. La regola `Player Died` azzera il flag del bersaglio, mentre l'uscita di un giocatore lo rimuove dai ledger di tutti i superstiti, evitando voci fantasma o indici spostati.

## Teleport

Il menu Teleport comprende l'ultima Spawn Room visitata, la destinazione dell'obiettivo corrente quando disponibile e i giocatori presenti, inclusi bot AI e dummy bot validi. La posizione salvata viene aggiornata a ogni nuovo ingresso in spawn, così segue anche le spawn avanzate di Escort e Hybrid. Il viewer non compare come propria destinazione.

Il teletrasporto verso un giocatore cerca una posizione camminabile vicina al bersaglio invece di sovrapporre i due corpi. Tipo e identità della destinazione vengono catturati prima di aggiornare la lista. Dopo il refresh il riferimento bloccato viene ricontrollato per esistenza, vita e appartenenza all'elenco: se il target è uscito, morto o non più disponibile, l'azione viene annullata con un messaggio localizzato invece di trasferirsi al nuovo elemento dello stesso indice.

## Crouch e ispezione

Fuori dal menu, Crouch attiva l'ispezione per quel viewer. Le nameplate native vengono disabilitate una sola volta all'ingresso e ripristinate in ogni percorso di uscita: rilascio, apertura menu, morte, despawn, hero-select, passaggio a spettatore, cambio modalità camera o uscita dalla partita.

Il target vicino al reticolo viene aggiornato ogni 0,10 secondi. Lo slot player libero `47` conserva l'array di candidati, che esclude viewer, entità inesistenti, non spawnate, morte o senza line-of-sight, considerando geometria e barriere come occludenti. Solo dopo il filtro viene scelto il candidato col minore angolo rispetto al reticolo. Non sono introdotte soglie massime di distanza o angolo. Nome, eroe effettivo e percentuale Ultimate restano rivalutati; durante Duplicate di Echo viene mostrato l'eroe duplicato.

I due testi di ispezione usano il colore personale per gli umani e arancione per i bot e sono mostrati a scala 0,90 per una leggibilità leggermente maggiore. Il cleanup distrugge entrambi i testi in ogni percorso, prevenendo residui IWT. Il sistema non usa più `Start/Stop Forcing Player Outlines`.

## Camera in terza persona

La camera può seguire il viewer o un altro giocatore valido, inclusi bot. La 0.5.2 mescolava la posizione del bersaglio rivalutata dal client con un offset assoluto calcolato da un loop server: il test live ha confermato che la differenza fra i due tempi produceva ondulazione e vibrazione del modello.

La 0.5.3 elimina il loop, il `Wait(0.016)` e tutte le cache coordinate. Un solo `Start Camera` rivaluta nello stesso fotogramma visuale:

1. l'anchor ricavato da `Eye Position` e dal modello corrente;
2. la direzione dietro l'eroe e l'offset laterale della spalla;
3. l'unico raycast contro la geometria;
4. il margine dalla parete, riutilizzando il risultato del raycast senza variabili;
5. il punto di mira con pitch completo.

Il test live della 0.5.3 ha confermato la fluidità, ma ha evidenziato un disallineamento geometrico: il punto osservato seguiva il pitch completo mentre l'arretramento restava sul piano orizzontale, facendo uscire l'eroe dall'inquadratura guardando molto in alto o in basso.

La 0.5.4 usa quindi due vettori distinti. Il braccio posteriore segue la `Facing Direction` completa, così camera, occhio dell'eroe e punto di mira restano quasi collineari durante il pitch. Soltanto l'offset laterale usa `Horizontal Facing Angle Of`, mantenendo la spalla stabile anche vicino a ±90°. Il raycast comprime la distanza vicino a pavimenti e soffitti senza introdurre un secondo controllo collisione. La stabilizzazione non-camera 0.5.5 non modifica questo percorso.

Il blend resta `0`: non è uno scatto a bassa frequenza, perché l'intera espressione è già aggiornata per fotogramma; evita invece un secondo ritardo sopra la posizione visuale. Altezza, distanza e offset continuano ad adattarsi al modello corrente, incluso D.Mon. Inquadratura agli estremi, fluidità percepita e collisioni restano verifiche live; un target remoto può mostrare jitter di rete non presente sulla camera del proprio eroe.

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


## Avvio immediato

Quando il server entra in `Waiting for Players`, il Workshop esegue `Start Game Mode`. `Is Assembling Heroes` e `Is In Setup` sono gestiti da due regole globali separate che impostano `Set Match Time(0)`, così ogni fase viene saltata anche quando le transizioni sono consecutive. Il countdown CHILL resta indipendente perché usa `Total Time Elapsed` e non `Match Time`.


## Manutenzione automatizzata

Le patch repository non richiedono più workflow YAML temporanei. Il workflow permanente `.github/workflows/maintenance-patch.yml` si attiva esclusivamente quando viene aggiunto `.github/maintenance/patch.py`, esegue la patch, i test unitari e il validatore, impedisce alla patch di modificare `.github/workflows`, quindi committa il risultato e rimuove lo script di manutenzione. Il validatore ammette soltanto `validate-workshop.yml` e `maintenance-patch.yml`: qualsiasi runner temporaneo aggiuntivo fa fallire il gate statico.


### Teleport obiettivo dinamico

`Current Objective` usa il payload reale in Escort/Hybrid, la bandiera nemica in Capture the Flag e, in Push, un player vivo attualmente sull’obiettivo come proxy del robot. Se nessuno è sul robot, resta il fallback alla posizione obiettivo. Le altre modalità continuano a usare `Objective Position(Objective Index)`.


### Memoria cursori menu

I cursori di Main Menu, Soundtrack, Camera, Name Color, HUD Language, Revenge, Unkillable, Voice Modifier e Teleport Crouch non vengono più riallineati alla prima voce o al valore applicato quando il menu viene riaperto. Le liste dinamiche Camera/Revenge continuano a essere aggiornate e clampate quando i target cambiano. In Capture the Flag lo stato visivo di `Current Objective` non dipende più da `Objective Position`, perché il teleport usa la bandiera nemica tramite `Flag Position`.


### Feedback audiovisivo e Jump respawn

Le modifiche applicate usano un `Good Explosion` azzurro-turchese visibile a tutti e `Buff Impact Sound` solo per il player che agisce. I ripristini usano un `Ring Explosion` violetto chiaro visibile a tutti e `Ring Explosion Sound` soltanto per il player interessato.

Alla morte viene salvata la posizione. Premendo `Jump` a menu chiuso viene scelto un punto casuale entro ±6 m, corretto con `Nearest Walkable Position`, poi il player viene respawnato e teletrasportato al punto sicuro.
