# Changelog

Le versioni seguono lo stato del sorgente Workshop e della relativa validazione. Uno stato `live-ready` indica gate statici verdi e regressione client completata; la pubblicazione di un tag/release resta un passaggio separato.

## Scheduler guidato dallo stato e carico inattivo — 2026-09-29

- Separati i percorsi umani/in attesa di classificazione e bot: Fly solo attivo, Luck solo con stato o icona pendente, cache Camera/Revenge solo per le relative pagine aperte. Ingressi, quarantena cambio squadra e pulizia delle icone residue mantengono i propri controlli.
- Vision evita il filtro del pubblico durante l'inattività e svuota l'ultimo pubblico una sola volta, conservando la reattività a 20 Hz quando in uso.
- Accorpati quattro controlli globali degli slot dummy in una subroutine a 1 Hz, con cooldown di creazione indipendente per squadra impostato prima del tentativo. Follow target a 5 Hz; manutenzione morte/classificazione bot a 10 Hz.
- Sorgente da 115 a 113 regole e da 62 a 64 subroutine, sempre 5 Wait e un Loop. Nessun cambiamento a testi, menu, Ghost/Fly, Travel, Revenge, Unkillable, esiti/durate della roulette o blocchi dei bot normali. Slot dummy e acquisizione del target seguono le nuove frequenze richieste.
- Test del dispatch reale, stati residui Luck, pubblico Vision inattivo e manutenzione dummy con creazioni fallite, squadre indipendenti, rilascio slot e cleanup. La riduzione di chiamate nel modello non certifica la scomparsa dei crash del motore; resta necessaria una sessione reale prolungata.

## Recupero Jump dopo cadute fuori mappa — 2026-09-27

- Corretto il latch di Jump: non viene più azzerato a ogni morte, evitando tentativi automatici continui quando una resurrezione fallisce mentre il tasto resta premuto. Il rilascio lo riabilita sia da vivi sia da morti.
- Adattato il posizionamento prima di Resurrect usato da Friendly. Un solo calcolo della destinazione camminabile alimenta il Teleport prima e dopo la resurrezione, con offset verticale di 0,5 m. Il recupero copre anche superfici vicine rilevate dal raycast ma lontane dalla navigazione; sul terreno vicino alla navigazione resta la resurrezione sul posto.
- Nessuna eccezione per singole mappe, attesa, loop o forcing aggiunto. Flag per-player riscritto e azzerato nella stessa azione, oltre che nel setup/quiete. Test delle regole reali per morte ripetuta, rilascio, geometria controllata, Teleport su morto ignorato e due player; verifica nativa sulle mappe Schermaglia ancora necessaria.

## Fly al 1000% e controllo dei nomi impostazioni — 2026-09-27

- Aumentato il limite Fly dal 500% al 1000%, mantenendo 25 secondi per la rampa Forward pura: 36 punti percentuali al secondo, da 5,5 a 55 m/s richiesti. Aggiornati HUD EN/ID/TH e test; reset degli input, indipendenza dei player, priorità Luck Acceleration e cleanup restano invariati.
- Aggiunto un controllo esplicito di categorie e nomi delle impostazioni Workshop: devono essere stringhe letterali non vuote e prive di `{`, `}` e `:`. Le tre impostazioni correnti sono già valide e identiche alla revisione precedente: non sono state rinominate. L'esportazione ricevuta conteneva tutti i testi personalizzati vuoti; una prova minima ASCII ha iniziato a funzionare dopo la chiusura e riapertura del gioco. Questa protezione statica non risolve quel problema del client: causa interna sconosciuta, reimportazione del codice completo ancora da verificare.

## Sola Schermaglia — 2026-09-27

- Limitate creazione e uscita spawn dei dummy alla Schermaglia; rimossi il ramo CTF e il fallback duplicato. Conservato il percorso di destinazione Schermaglia, inclusi stabilizzazione iniziale, 16 candidati, retry a 1 secondo, verifica geometrica, respawn e rilascio degli slot per gli umani.
- Rimossi dal Teleport manuale i percorsi payload, bandiera e proxy Push. La pagina Objective usa la posizione del motore e gli stessi controlli di sicurezza; il testo EN/ID/TH non cita più la bandiera nemica.
- Documentata la rotazione di tutte le mappe standard in Schermaglia, escludendo le mappe Workshop. Avvio, timer, HUD e cleanup del cambio squadra restano invariati; la selezione delle mappe rimane nelle impostazioni della lobby.

## Pulizia delle regole e istruzioni HUD compatte — 2026-09-26

- Unificate le due subroutine con lo stesso effetto visivo in `EfekTerapkan`; rimossi anche sette rami ON/OFF che ora chiamavano la stessa azione. Le chiamate restano negli stessi percorsi di applicazione e ripristino, senza nuovi effetti o frequenze.
- Rimossi il blocco condizionale vuoto dopo il Teleport e la selezione ridondante per Flashpoint/Control/Clash/Assault, già coperta dal fallback all'obiettivo corrente.
- Limitata la selezione destinazione dei dummy ai percorsi usati dalla creazione automatica: CTF e fallback per Schermaglia. Restano ritardo iniziale, ricerca dei 16 candidati, validazione geometrica e cleanup. Il Teleport manuale conserva le altre modalità.
- Il sorgente passa da 116 a 115 regole e da 63 a 62 subroutine, con 5 Wait e un solo Loop. Restano invariati gestione degli HUD, scheduler e lifecycle del cambio squadra. La pulizia non identifica né risolve la causa nativa della regressione Friendly ritirata.
- Accorciate le istruzioni HUD in English, Bahasa Indonesia e ไทย: i menu Arcade più comuni usano due righe di comandi, il menu musica tre per conservare i salti di dieci voci. Travel & Attach usa due righe di contenuto e due di comandi, mantenendo target, binding dinamici, pressioni prolungate e cooldown. Cambiano soltanto le stringhe, senza nuovi handle o rivalutazioni.

## Ripristino dopo crash al cambio squadra — 2026-09-25

- Ritirata integralmente la PR #76: l'utente ha segnalato un crash sistematico al primo cambio squadra, sia subito dopo l'ingresso sia successivamente, anche senza avere aperto il menu.
- Ripristinati byte per byte sorgente Workshop, fixture semantica e controlli compatibili della revisione `2529608`, con cui il cambio squadra funzionava secondo il riscontro utente. La cronologia Git conserva la revisione ritirata.
- Rimosse insieme cache Arcade, controllo periodico della cache, nuovo cooldown cosmetico e rallentamento automatico. Nessuna di queste modifiche viene indicata come causa certa: il guasto nativo non è stato riprodotto né isolato dai test Python.
- Le funzioni precedenti alla PR #76 restano presenti. Occorre reimportare il file e provare in una nuova lobby cambio squadra immediato, successivo all'uso dei menu e con altri player che osservano o votano il soggetto.

## Modalità dummy e colore Host — 2026-09-23

- Creazione automatica dei dummy limitata a Schermaglia e Cattura la bandiera per entrambe le squadre. Le altre modalità, compreso Deathmatch a squadre, non creano dummy; restano le protezioni degli slot umani e il cleanup esistente.
- L'intera riga Host usa il colore RGB globale del titolo e lo rivaluta durante l'animazione. Rimane nel campo Text, con una riga vuota sopra e sotto e senza nuovi handle, Wait o Loop.

## Camera durante cambio squadra e nuovo nome personalizzato — 2026-09-22

- La Camera che osserva un altro player torna normale quando il target entra in quarantena per cambio squadra, anche se l'entità risulta ancora viva e spawnata. La revoca usa il controllo periodico esistente, senza nuove regole, Wait, Loop o handle.
- Il nome visibile esatto del profilo dedicato passa da `งูแท้` a `งูแรร์`, sia nella registrazione sia nel ripristino. Restano Silver Mist, Poison 2 e Draconian bloccato.
- Il controllo generale di lifecycle, registri transitori, menu, Attach, roulette e dummy non ha individuato altri nuovi difetti dimostrati. Le prove della Camera valutano le condizioni del sorgente con 12 osservatori; non simulano la vita delle entità nel motore. La revisione richiede una nuova verifica in gioco.

## Host come testo con spazio sopra e sotto — 2026-09-21

- Spostata la riga Host dal campo Subheader al campo Text, con una riga vuota sopra e una sotto in tutte le lingue. Nome e icona continuano a seguire l'host corrente.
- La spaziatura appartiene allo stesso HUD: restano nove handle fissi e 21 handle di base con 12 umani. La distanza visiva dall'indicatore nativo va confermata nel client dopo il nuovo import.

## Riduzione dei picchi, Player Vibes e collisioni dummy — 2026-09-15

- Separata la diagnostica dalla registrazione Inspector: i contatori restano disponibili con la registrazione disabilitata in entrambi gli stati del toggle.
- Limitate le creazioni delle targhette Inspection/Travel tramite una scadenza individuale condivisa di 0,25 s. Il cleanup rimane immediato; un cambio rapido di bersaglio può mostrare una breve pausa prima della nuova targhetta.
- Distribuite le rotazioni delle icone roulette in quattro fasi dello slot HUD, con al massimo tre aggiornamenti per tick a 12 umani. Le prime rotazioni possono risultare meno rapide; durate degli effetti e gestione della morte restano basate sui propri timestamp.
- Rimosso tutto il conteggio dei minuti individuali, il vecchio roster e i relativi handle/array. Player Vibes passa a sinistra: una riga per umano e nove HUD fissi (21 handle a 12 player, prima 35); a destra compare Host con icona eroe e nome del player corrente. Countdown server e CHILL STAR restano disponibili.
- Rimosse le istruzioni che alteravano le collisioni dummy; restano quelle native, senza riapplicazioni nel lock. Il follow diretto può arrestarsi contro una parete.
- Nessun nuovo Wait o Loop. Le verifiche automatiche coprono limiti di creazione, distribuzione delle rotazioni e collisioni; l'assenza di crash richiede ancora la prova nel client.

## Compatibilità del titolo regola durante l'import — 2026-09-10

- Semplificato il titolo di `93d` in `93d - Subrutin: Bersihkan teks yatim` dopo la segnalazione client «commento non valido dopo regola(». Nessuna modifica ad azioni, variabili, condizioni o gestione delle risorse.
- Il titolo precedente conteneva una sottostringa inglese potenzialmente intercettata dal filtro dei commenti del client. Il titolo si trova alla riga fisica 4777: escludendo i 38 ritorni a capo interni alle stringhe precedenti, il conteggio corrisponde esattamente alla riga 4739 segnalata dal client. La localizzazione dell'errore è quindi coerente con `93d`; l'ipotesi sul filtro testuale e l'esito del nuovo import richiedono comunque conferma nel client.
- Aggiunta una regressione per evitare di ripristinare il frammento sospetto nei titoli. Il controllo non emula il filtro testuale nativo e non si applica ai nomi delle variabili.

## Stabilità con lobby piena e ingressi/uscite — 2026-09-09

- Registrati fuori dalle variabili del player gli identificatori di HUD effetti, testi Teleport e testi Vision, compresi i bot. Il registro ha capacità fissa e libera le risorse dei proprietari usciti anche quando le loro variabili non sono più leggibili; ogni distruzione normale azzera la copia per evitare cancellazioni di ID riutilizzati.
- Il menu Crouch Travel & Attach riutilizza lo stesso HUD durante la navigazione. Il pubblico di Vision parte da una cache condivisa, con verifica diretta di esistenza, appartenenza umana e Vision attiva per ogni destinatario.
- Distribuiti fra i player gli aggiornamenti a 10 Hz e 1 Hz, mantenendo le frequenze individuali. Le modifiche ai voti vengono accorpate in un solo conteggio al successivo tick globale, incluse le uscite simultanee.
- Le proprietà di danni, urti e collisioni di Unkillable vengono mantenute a 1 Hz, con ripristino anticipato quando manca lo status o cambia l'eroe; salute e macchina delle morti conservano il controllo a 20 Hz.
- Le prove automatiche verificano proprietà delle risorse, riuso degli identificatori, rotazione degli slot e carico logico simultaneo. Non costituiscono una misura del carico nativo di Overwatch né confermano la scomparsa dei crash: serve la regressione live con lobby piena.

## Durata, uscita dummy e profilo su main — 2026-09-08

- Durata configurabile limitata a 60 minuti dopo il riscontro utente di crash nelle sessioni impostate oltre un'ora. Su richiesta, il minimo scende a 10 minuti: l'intervallo diventa 10–60 minuti e il valore predefinito resta 30 minuti.

- Uscita dummy dalla spawn: su Hybrid la fase precedente alla cattura usa il primo obiettivo; il payload viene usato dopo la cattura, con fallback all'obiettivo corrente quando la destinazione non è disponibile. I tentativi esplorano 16 candidati orizzontali con cursore per-dummy, anziché ripetere sempre lo stesso punto; restano il limite di un tentativo al secondo e i controlli di sicurezza. La segnalazione riguarda Paraíso alla creazione: la geometria reale richiede conferma nel client.
- Il Player Vibes del profilo personalizzato `งูแท้` passa da `Caladan Brood` a `Draconian`, sia nel setup sia nel ripristino.

## Revisione testi su main — 2026-09-07

- Titolo HUD centrale in indonesiano: `SERVER KHUSUS CHILL`, con countdown e impaginazione invariati.

- Rivisti HUD e tutti gli Small Message in inglese, indonesiano e thailandese: istruzioni più compatte, abbreviazioni coerenti e conferme più leggere. Tempi, binding, destinazioni, effetti e segnaposto dinamici mantengono il significato originale.
- Uniformati all'indonesiano i nomi personalizzati di variabili, subroutine, regole e commenti; restano le parole chiave del motore, gli acronimi tecnici e i nomi propri. Ad esempio `DaftarPemainSnapshot` diventa `SalinanDaftarPemain`, `ProsesCachePemain` diventa `ProsesSimpananPemain`.
- Allineati fixture semantica, validatore e aspettative dei test. Nessuna modifica alla logica di menu/Attach, al lifecycle, ai 12 slot riutilizzabili o allo scheduler. Il controllo delle stringhe conserva i segnaposto; il confronto del codice eseguibile ammette soltanto le rinomine dichiarate.
- La revisione dei testi non aggiunge un nuovo riscontro visivo nel client; i test live precedenti restano riferiti alle rispettive revisioni.

## 0.8.1 — 2026-08-25

Stato: **live-ready**.

- Rifattorizzato `CHILL STAR`: rimosso dal Subheader dell'ultima riga roster Left e spostato in un HUD globale dedicato (`Left 13`) con cache stabile `NamaPemimpinPilihan`/`WarnaPemimpinPilihan`. `HitungPilihan` ora aggiorna la cache solo a leader definitivo (no pareggio), mentre la pagina colore sincronizza in tempo reale il colore del leader quando cambia senza ricalcolare i voti. La diagnostica Left resta nel Subheader ma conta ora undici handle fissi.
- Hardening del 6 settembre (validator/test): congelata l'architettura `02` inline. Il gate ora rifiuta ogni separazione asincrona tra classifier umano e renderer roster (es. una seconda `Ongoing - Each Player` tipo `02b`/`02x`), e la suite runtime blocca il reinserimento di regole/debug `DBG 02` nel sorgente.
- Hotfix del 6 settembre (profilo speciale): il matcher `งูแท้` usa ora `NamaTampilan` stabile sia nel classifier `02` sia nel repair `89a`, evitando il token player live durante il team-switch. Rimossi inoltre due write ridondanti di `BotOtomatis=False` nel classifier e il secondo repair duplicato di `NamaTampilan` nel worker 20 Hz.
- Hotfix del 4 settembre (import): corretta la condizione della regola `00a4` con confronto esplicito `Or(...) == True`, risolvendo l'errore parser Workshop "richiesto un operatore di confronto dopo 'False'" (riga 1015).
- Hotfix live del 4 settembre (post team-switch): il classifier `02` non sovrascrive più `NamaTampilan` già valido quando il token player torna temporaneamente vuoto dopo cambio squadra; il refresh nome resta consentito su primo join o cache vuota.
- Hotfix live del 4 settembre (HUD nativi): rimosso il reapply diretto da `01b` (`Disable Game Mode HUD` / `Disable Game Mode In-World UI`) perché reintroduceva crash nel team-switch. Le due istruzioni restano nel percorso normale di `SiapkanPemain`, raggiungibile ora grazie alla protezione di `NamaTampilan`.
- Hotfix live del 5 settembre (quarantena team-switch): il repair roster in `89a` ora richiede `SiklusPemainAktif == False`, evitando che la quarantena venga annullata prematuramente con `SudahSiap=True` prima del worker stabile `01b`.
- Stabilizzazione del 4 settembre (team-switch): `01a` non esegue più `TenangkanPemain`/`BersihkanPemain` durante il mismatch Team 1 ↔ Team 2. Ora apre soltanto una quarantena leggera (`PindahTimDiproses=True`, `SiklusPemainAktif=True`, `SudahSiap=False`, `Manusia=False`) e arma una finestra di stabilizzazione a `+0,500 s`.
- Stabilizzazione del 4 settembre (team-switch): `01b` finalizza in modo serializzato dopo team+spawn stabili (`TenangkanPemain` → `BersihkanPemain` condizionale su roster presente → `SiapkanPemain`), così il teardown pesante avviene fuori dalla transizione nativa Overwatch.
- Hardening del 4 settembre (scheduler): `04g` itera su `DaftarPemainSnapshot = All Players(All Teams)` e non più sulla lista nativa live, evitando churn della collezione durante il passaggio squadra.
- Hardening del 4 settembre (team-switch/loading): i due blocchi bootstrap hero/setup (`00a2`/`00a3`) non forzano più `Set Match Time(0)`. Mantengono solo il latch di bootstrap (roster vuoto + lock lifecycle libero), mentre `00a4` li blocca definitivamente appena il match è in progress. Il cambio squadra usa quindi la transizione/loading nativa di Overwatch senza forzature di fase.
- Hardening del 4 settembre (dummy/team-switch): le regole di create/release dummy (`03d`, `03d1`, `03e`, `03e1`) ora girano solo quando `PemainSiklusGlobal == Null`. Durante un cambio squadra in corso il sistema non fa churn create/destroy dei bot, riducendo i picchi di carico nel passaggio.
- Hotfix del 4 settembre: `BersihkanPemain` ora include un fallback di recovery su mismatch indici. Se roster e array canonici sono desincronizzati, il cleanup rimuove comunque l'entità e distrugge gli handle validi per evitare leak progressivi (HUD/IWT/Icon) e picchi di carico script durante cambio squadra.
- Hardening del 4 settembre (team-switch): aggiunte guardie bounds-safe anche sui punti menu/inspection che leggono `HudMenuPemain` e `TeksDuniaPemain` via indice roster. In stato desincronizzato, i rami non accedono più a indici invalidi, evitando retry incontrollati e nuovo carico script.
- Correzione del 2 settembre: il reset completo del cambio squadra viene eseguito dalla regola `01a - Siklus tim: Reset penuh pada konteks pemain` (`Ongoing - Each Player`), così `TenangkanPemain` e `BersihkanPemain` ricevono l'`Event Player` corretto. Gli effetti engine vengono fermati prima del nuovo setup; gli handle HUD canonici e i riferimenti vengono distrutti prima di liberare lo slot e riaccodare il setup con timestamp di 0,25 s, senza nuovi `Wait`. Il vero leave mantiene la guardia di 0,5 s e la rimozione per identità esatta, prima del riuso dello slot.
- Corretta la base laterale di Fly: `Cross Product(up, horizontalForward) * X` rispetta X positivo verso sinistra. Avanti mantiene il pitch; indietro e laterali restano orizzontali. Aggiornato l'interprete dei test alla formula effettiva e aggiunte regressioni per direzioni, contesto dei cleanup e isolamento tra player. HEART resta intenzionalmente Team Heal: cura tutti i vivi della squadra e notifica soltanto chi ha attivato la roulette.
- La conferma live del precedente motore Fly è registrata come riscontro della revisione precedente; la revisione corrente di strafe e cambio squadra è stata poi completata nella regressione live 0.8.1.
- Coperto anche un secondo cambio squadra mentre la registrazione è in coda: il target e il retry vengono riallineati, la prenotazione precedente viene rilasciata e il setup attende entrambe le scadenze globale e individuale. Un player non spawned non trattiene la prenotazione. `TutupMenu` distrugge prima l'handle canonico, anche se la copia locale è `Null`, e poi soltanto un eventuale handle locale distinto, evitando perdite o doppie distruzioni.

- Ripuliti gli `Small Message`: le conferme già evidenti da HUD o azione non vengono più accodate; restano errori, cooldown, istruzioni necessarie e risultati di Try Your Luck/Revenge. Rimosso in particolare il messaggio post-tentativo `Resurrect unavailable`: Jump resta riarmabile al rilascio senza notifiche di fallimento ridondanti.
- Le cinque pagine Crouch Travel & Attach mantengono la palette mint → cyan → blu → viola → rosa ma ora la interpolano in `0,18 s` tramite `WarnaMenu`, con colore HUD rivalutato durante la transizione come nei 14 menu Arcade.

- Hotfix Fly successivo al test utente: la revisione precedente manteneva velocità costante e non consentiva salita/discesa su diversi eroi. Sostituiti throttle trasformato e percentuale di movimento nativo con un motore 3D esplicito `ProsesTerbangPemain` a 20 Hz: nel volo normale `Move Speed = 0` e gravità zero, direzione ricavata da mira e input grezzi, impulso world sulla differenza fra velocità richiesta e corrente. Solo l'input Forward usa il pitch della mira; input Back e strafe restano orizzontali. La baseline uniforme Fly è `5,5 m/s = 100%`, non una percentuale esatta della velocità nativa di ogni eroe/buff; Forward puro aumenta di `16` punti al secondo fino a `27,5 m/s = 500%` dopo 25 secondi. Rilascio, laterali, diagonali e indietro riarmano la rampa; senza input la velocità desiderata è zero. Timer, percentuale, direzione e delta sono per-player; Try Your Luck: Acceleration mantiene priorità totale e lascia poi una rampa fresca. Cleanup e riapplicazione coprono OFF, morte, Resurrect, cambio eroe e cambio squadra. L'utente ha poi confermato il funzionamento di quel motore e la revisione corrente strafe + team-switch è stata verificata nella regressione live 0.8.1. Il fallimento originario non dimostrava da solo un guasto del timer.
- Jump Resurrect non può più essere bloccato dallo stato Crouch Travel né dal validatore Teleport: `Resurrect` viene sempre raggiunto. Una morte con terreno sotto il punto registrato rinasce nello stesso punto senza Teleport; soltanto il vuoto sposta il player dopo la resurrezione, calcolando direttamente `Nearest Walkable Position(Last Of(Position Of(Event Player)))` dalla posizione live invece di riusare un candidato salvato mentre era morto.
- Riordinati e resi più specifici i testi delle cinque pagine Crouch Travel & Attach in EN/ID/TH: titolo numerato, destinazione o posizione, target e azione seguono ora lo stesso schema e mostrano i binding reali del player. Il singolo renderer per-player usa una progressione mint → cyan → blu → viola → rosa, con istruzioni pastello e contenuto neon; Self Kill è presentato come Self Elimination della forma eroe corrente con cooldown di 3 secondi.
- Separato visivamente `SERVER LOCATION` da `LOBBY & CHILL TIME`: la località usa ora l'ambra neon `Custom Color(255, 205, 110, 255)` invece di una seconda tonalità cyan.
- La sincronizzazione del timer nativo e il blocco della completion sono stati spostati nel ramo scheduler a 1 Hz: il countdown CHILL resta l'unica autorità di fine partita senza riscrivere il timer 20 volte al secondo.
- Rafforzato l'isolamento per-player dei menu: l'esito HEART di Try Your Luck ora cura tutti i vivi della squadra del proprietario e notifica soltanto il proprietario; tutte le mutazioni di stato delle pagine restano legate all'owner. Camera, Revenge, Vote e Dummy Follow mantengono il targeting sociale dichiarato, mentre icone ed effetti cosmetici pubblici non trasferiscono stato fra player.
- Vision mostra volutamente icona, nome roster stabile e salute di tutti gli umani, inclusi quelli con Privacy ON, oltre a bot/dummy; Privacy continua a proteggere Camera, inspection e Teleport normali.
- Rese fluide le tre targhette IWT di inspection, Vision e Teleport: icona, nome e salute restano nello stesso testo, l'intera posizione usa `Update Every Frame`, `Evaluate Once` cattura soltanto l'identità e `Visible To Position String and Color` mantiene la rivalutazione completa.
- Stabilizzata la Camera in terza persona durante corsa, salto e osservazione: l'unico `Start Camera` condiviso mantiene posizione e mira `Update Every Frame` ma usa `Blend Speed 0`, evitando che un blend non nullo rincorra continuamente la traslazione del target e produca vibrazione.

- Corretto il Main Menu live: le pagine 12 e 13 ora condividono un unico renderer dinamico, con tail esplicita `12 ? Dummy Follow : Ghost Mode / Fly` in EN/ID/TH. Lo scroll `12→13→0` e `0→13→12` non può più duplicare la pagina 12 né restare bloccato sul renderer Ghost dopo una riapertura.
- Aggiunta pagina `13 - Ghost Mode / Fly`, portando il Main Menu a 14 pagine (`0..13`) in EN/ID/TH. Le due voci sono toggle indipendenti e partono OFF: Wall Phasing disattiva la collisione con pareti e soffitti tramite `Include Floors = False`, mantenendo sempre solidi i pavimenti; Fly usa gravità zero e il motore 3D a impulsi descritto sopra. Gli stati sopravvivono a cambio eroe, morte e Resurrect; cambio squadra e leave/rejoin li riportano ai default.
- Separata esplicitamente la fisica Fly da Try Your Luck: applicazione, avanzamento e cleanup della roulette non possono scrivere gravità, trasformazione throttle, toggle Ghost/Fly o relativo latch.
- Aggiunto un cooldown Self Kill per-player di 3 secondi, armato prima della kill e conservato durante la morte; cambio squadra e leave/rejoin eseguono setup fresco e lo riavviano. I tentativi anticipati mostrano il tempo residuo in EN/ID/TH.
- Rafforzata l'allocazione roster: un nome visibile ancora `Null` o vuoto non può consumare uno slot né essere registrato come identità temporanea; la classificazione viene ritentata soltanto quando il token è disponibile.
- Rafforzato il cleanup Vote Player: ogni voto che punta a un player realmente uscito viene azzerato e il leader viene ricalcolato dopo la rimozione, evitando riferimenti stale o voti ereditati da un rejoin.
- Corretto il secondo deadlock live del roster dopo il cambio squadra: `NamaTampilan` viene ora riparato per qualunque membro già presente in `PemainManusia`, anche quando `Manusia` e `PernahDisiapkan` restano `True`. Valori `Null` o stringa vuota non possono più bloccare `02b`; il cache viene scritto solo quando il nome live è nuovamente disponibile.
- Corretto il deadlock live del roster dopo il cambio squadra: il lifecycle essenziale (setup, classificazione e renderer `02b`) non è più bloccato da `Server Load < 150`. Un picco di carico non può quindi lasciare vuote le righe `LOBBY & CHILL TIME` / `PLAYER VIBES` né escludere indefinitamente il player dai target Crouch.
- Corretto il nome dopo il cambio squadra: gli umani salvano `NamaTampilan` con `Evaluate Once` durante la classificazione e le due righe roster, Crouch Inspect, Crouch Teleport e Try Your Luck Vision usano la copia stabile invece del token player live, anche dopo una nuova registrazione completa.
- Aggiunto il profilo riconosciuto dal nome visibile esatto `งูแท้`: Name Color `Silver Mist` e Player Icon `Poison 2` vengono applicati come default iniziali ma restano modificabili; Player Vibes è fissato a `Caladan Brood` e la pagina Soundtrack diventa read-only. Il catalogo globale resta di 100 generi. Il riconoscimento per nome visibile comporta la limitazione nota che gli omonimi condividono il profilo e una rinomina non viene riconosciuta; cambio squadra e leave/rejoin riapplicano i default.
- La posizione sicura condivisa di teleport/resurrect/dummy ora richiede spazio libero finale su quattro lati e sopra la testa e solleva il punto di 0,5 m, riducendo incastri in muri e pavimento. Il renderer Crouch Teleport conserva il layout multilinea senza caratteri `\`.
- Il repair di un umano già presente in `PemainManusia` ripristina i flag senza riclassificarlo come bot; il cambio squadra effettivo usa invece il reset completo individuale e poi un nuovo classifier/setup.
- Teleport rinforzato contro muri/pavimenti: dummy e player condividono il controllo body-safe, il teleport verso player prova più lati invece della posizione esatta e l'HUD Teleport torna multilinea senza mostrare backslash.
- Rifattorizzato il lifecycle cambio squadra su reset completo: al mismatch Team il detector individuale richiama in ordine `TenangkanPemain` e `BersihkanPemain` nel contesto del player, libera slot/handle/stati owner-scoped e riaccoda la nuova entità al classifier/setup con retry temporizzato. Il percorso non usa `Abort`, non dipende da `Server Load`, non usa più il modello pending leggero e impedisce riferimenti stale nelle liste CHILL/PLAYER VIBES e nei target Crouch.
- Player Left usa la rimozione esatta di roster/HUD senza reset engine o fallback slot HUD; prima di liberare lo slot distrugge gli handle temporanei del leaver, sottrae il suo voto dal target e rimuove in parallelo debiti e claim Revenge dai survivor, evitando entità, voti e riferimenti orfani dopo il riuso slot.

- Cambio squadra ripetuto allineato al cleanup/setup completo: ogni transizione libera prima la registrazione precedente e poi ricrea lo stato del player dalla nuova entità, con slot riutilizzabile pulito.
- Crouch Travel & Attach resta a 5 pagine ma il renderer Teleport non mostra più simboli `\`. `Self Kill` esegue una sola `Kill` immediata, senza Wait/Loop e senza condividere i retry di Skull/Revenge: su forme come il mech di D.Va termina soltanto la forma corrente, senza una seconda kill automatica sul pilota.

- La discriminazione `Player Left Match` attende 0,5 s prima del cleanup, così una transizione di squadra ha più tempo per riapparire come entità valida e non percorre accidentalmente anche il cleanup di leave.
- Il cleanup `Player Left Match` disabilita il fallback per slot HUD prima di rimuovere il roster: una vecchia entità distrutta dal cambio team non può più eliminare la nuova entità che eredita lo stesso slot.
- Documentazione riallineata al runtime reale: dummy respawn 3 s, Burning 5% Max Health ogni secondo con bypass temporaneo di Unkillable/Damage Received, e controlli completi Crouch Travel & Attach.
- GitHub Actions limitato ai push su `main` e alle PR, con concurrency/cancel-in-progress e timeout 30 minuti per evitare run duplicati, falsi timeout e X rossi obsoleti.

## 0.8.0 — 2026-08-24

Stato: **live-ready**.

- Runtime riorganizzato attorno a uno scheduler globale a 20 Hz, con attività scalate a 10 Hz, 1 Hz e 0,1 Hz.
- Menu Arcade ridotto a un solo handle HUD attivo per player, senza preload o pagine nascoste.
- Aggiunta pagina `12 - Dummy Follow`: ogni umano può consentire o negare al dummy nemico di sceglierlo; il default è OFF, quindi il dummy resta fermo senza opt-in e seleziona sempre il target consenziente più vicino. Il Main Menu copre ora 13 pagine (`0..12`) in EN/ID/TH.
- Controlli menu resi espliciti tramite modificatore Crouch; la Camera rapida funziona a menu aperto o chiuso soltanto con Crouch rilasciato, mentre inspection e Teleport restano confinati al menu chiuso.
- Try Your Luck convertito dalla vecchia logica binaria a una macchina a stati con sei esiti: Vision, accelerazione, Skull, cura team, Burning e Hacked.
- Lifecycle join/leave/cambio squadra consolidato con guardie anti-duplicato e reset completo delle preferenze al cambio squadra.
- Identificatori personalizzati, regole, subroutine e commenti Workshop uniformati in Bahasa Indonesia.
- Localizzazione runtime completata per English, Bahasa Indonesia e ไทย, incluse icone e località server.
- Validatore reso semantico e accompagnato da test negativi per le invarianti della release.
- Corretto il primo errore d'import live: la subroutine 42 è stata abbreviata da un identificatore di 33 byte a `TerapkanTeleportasiJongkok` (26 byte); il gate ora limita ogni identificatore dichiarato a 32 byte UTF-8.
- Corretto il secondo errore d'import live: aggiunte le due parentesi finali mancanti nei filtri Camera Privacy; il gate ora valida anche i delimitatori delle espressioni e rifiuta chiamate incomplete invece di ignorarle.
- Corretti i primi riscontri live su spaziatura HUD, duplicazione del promemoria Crouch e icone Try Your Luck non visibili.
- Corretto il rendering live della roulette: tutte le sei icone usano `Visible To and Position`, rivalutano la posizione con `Update Every Frame` su occhio/mirino del beneficiario e restano visibili a tutti gli umani anche quando il roster cambia.
- Corretta l'accelerazione live: `Facing Direction Of(Evaluate Once(player))` conserva il beneficiario ma segue la sua mira con `Direction Rate and Max Speed`, producendo propulsione automatica 3D senza input direzionali.
- Menu e Camera condividono ora il latch Interact: cambiare stato di Crouch durante lo stesso hold non può attivare entrambi.
- Crouch Privacy parte OFF per ogni umano; quando il player la attiva, lo esclude dalla Camera custom, interrompe una Camera già agganciata e nasconde nome/nameplate in inspection e Teleport. Vision costituisce l'eccezione esplicita e mostra comunque il player.
- Vision mostra icona, nome e salute live per bot/dummy e tutti gli umani; Crouch inspection/Teleport viene soppresso per tutta la durata per evitare sovrapposizioni.
- Corretto il latch Soundtrack: `Crouch + Ability 1/2` viene armato e consumato sulla pagina 2, ripristinando i comandi `+10/−10` generi.
- Aggiunto cleanup hero swap global-first: il tracker eroe condiviso viene aggiornato a 10 Hz e annulla roulette, status, HUD e accelerazione Try Your Luck senza creare un nuovo `Ongoing - Each Player` e senza sospendere Unkillable se il player è vivo.
- Rafforzata la separazione bot/dummy: lifecycle, HUD, menu, input e funzioni player non attraversano più il percorso bot dedicato.
- I dummy nativi ora escono dalla Spawn Room usando destinazioni mode-specific percorribili: payload per Escort/Hybrid, bandiera nemica per CTF, proxy/fallback obiettivo per Push e obiettivo corrente negli altri casi; una destinazione non valida non produce più un teleport nel vuoto.
- Il teleport automatico dei dummy verifica inoltre che il punto camminabile resti vicino al target e che un ray cast verso il basso trovi terreno prima di spostare il bot; la stabilizzazione iniziale di 1 secondo usa un timestamp, non un `Wait`.
- Confermati massimo un dummy nativo per squadra e respawn massimo 3 secondi. La creazione richiede almeno due slot liberi; quando la squadra è piena il dummy viene rimosso e non viene ricreato finché non torna la capacità necessaria, evitando spam di creazione e preservando 6 posti umani per team.
- I dummy restano offensivamente passivi (`Damage Dealt/Knockback Dealt = 0`) ma usano `Damage Received/Knockback Received = 100`: ricevono normalmente ogni danno e urto. Mantengono esplicitamente la collisione con player/bot, mentre soltanto la collisione con pareti e soffitti viene disattivata conservando il pavimento.
- Corretta la locomozione dummy: `KunciBot` mantiene `Move Speed = 20`; ogni dummy nativo attraversa pareti e soffitti ma conserva il pavimento, insegue soltanto l'umano nemico vivo opt-in più vicino e arresta il throttle entro 4 m. Se il nemico si allontana riparte automaticamente; opt-out totale, morte completa, assenza target o rimozione fermano il movimento, mentre de-mech/transizioni non lasciano il dummy bloccato e gli iBot mantengono collisioni e navigazione AI native.
- Rafforzato `FULL HP`: applicazione e riapplicazione globale impostano insieme danni ricevuti a 0, urti ricevuti a 0 e collisione con player disattivata; OFF, 1 HP e i reset lifecycle ripristinano atomicamente `100/100/collisione ON`. Try Your Luck, morte/Resurrect e Spawn Room conservano invece modalità e cursore; il tick globale riapplica la protezione e ricrea l'icona se non esiste più.
- Sostituito il Jump `Respawn` con `Resurrect`: nella versione corrente il ritorno in vita è incondizionato; un solo raycast limita il Teleport al recupero dal vuoto e la destinazione `Nearest Walkable Position(Last Of(Position Of(Event Player)))` viene valutata sulla posizione live dopo `Resurrect`, nello stesso tick e senza `Wait`, offset casuali o fallback spawn.
- Corretto il blocco casuale di Try Your Luck senza cancellare Unkillable: l'avvio e gli esiti mantengono la preferenza e la protezione attive; soltanto lo Skull finale, dopo la conclusione della roulette, usa il bypass temporaneo condiviso con Revenge e arma retry/deadline anti-stallo. D.Va, Echo e altre forme intermedie vengono eliminate fino alla morte completa, poi Resurrect riattiva la modalità scelta. Burning sospende temporaneamente Unkillable e la riduzione danni, applica il 5% della Max Health ogni secondo per 10 s e lascia quindi un danno assoluto maggiore ai tank; al termine la modalità Unkillable scelta viene riapplicata dallo scheduler.
- Revenge non consuma più il debito al click o alla sola perdita di una forma: decremento e messaggio di successo avvengono esclusivamente su `Player Died`, dopo `Is Alive == False` e con claimant/attacker coincidenti; timeout, doppio claim, leave e cambio squadra annullano il pending senza conteggio.
- Anche posizione e prompt del Resurrect con Jump vengono registrati soltanto alla morte completa, mai durante de-mech o transizioni di forma.
- Vision mostra icona eroe, nome e salute rivalutata di bot/dummy e di tutti gli umani, indipendentemente da Privacy; inspection e Teleport Crouch vengono chiusi e restano disattivati per tutta la durata, eliminando la sovrapposizione degli In-World Text.
- Il leave di un iBot durante Vision distrugge ora il relativo In-World Text senza attraversare setup/cleanup umano, evitando handle orfani.
- Riallineato l'intero HUD al riferimento live: dieci handle fissi, roster Left `1..12`, roster Right `-13..-2` e spaziatore finale che riserva una riga prima dell'area nativa; ripristinati i promemoria completi e `LOBBY & CHILL TIME`, mentre la diagnostica integrata nel Subheader elimina lo `0` generato dal client. Il confine effettivo con Team Status Indicator/kill feed resta parte del test live a 1/6/12 player.
- Repository semplificato a un solo file `.workshop` destinato all'utente (`workshop/ruang_irama.it-IT.workshop`); la grammatica `en-US` resta esclusivamente come fixture interna di validazione e la documentazione non cita più sorgenti/manifest rimossi.
- Aggiunta la parità semantica canonica tra il clipboard pubblico `it-IT` e la fixture `en-US`: rule, dichiarazioni e azioni equivalenti devono restare sincronizzate.
- Documentazione sincronizzata con le otto modalità native supportate e con le patch client di agosto 2026.
- Rimosso il workflow di manutenzione che generava commit automatici; l'allowlist di `.github` conserva soltanto il workflow permanente di validazione e rifiuta marker, trigger o patcher one-shot.
- Test live completati e stabilità della 0.8.0 confermata dall'utente il 24 agosto 2026; la release passa a `live-ready` senza attribuire valori numerici non registrati.
- Rimossi tre `Wait(0.016)` ridondanti da Jump Resurrect, cleanup roster e seconda fase della classificazione iBot: `BersihkanPemain` è ora interamente atomica e il classificatore conserva soltanto il frame necessario a leggere il nome forzato. Restano 5 Wait funzionali e un solo Loop, indispensabile per il tick dello scheduler globale.
- Crouch Teleport esteso a quattro pagine: Primary/Secondary navigano avanti e indietro, Interact esegue l'azione; la quarta pagina permette di agganciarsi sopra un player/bot pubblico con offset sopra la testa, Crouch + Reload sgancia soltanto con il menu Melee chiuso; morte/leave/cambio eroe di uno dei due interrompono automaticamente il collegamento.

- Cambio squadra reso global-first: il scheduler globale accoda il lifecycle, cleanup e setup sono separati da timestamp da 0,1 s e protetti da Server Load; Player Left evita il doppio cleanup quando l'entità esiste ancora sulla nuova squadra.

## 0.7.2 — baseline

- Teleport Crouch con selezione target vicina al reticolo e fallback obiettivo.
- Audit HUD e correzioni incrementali di join/leave, team switch e cache menu.
- Baseline conservata nella cronologia Git; il vecchio tag `v0.7.2` viene sostituito dal tag finale `v0.8.0` richiesto per la release stabile.

## 0.6.x — ricostruzione funzionale

- Introduzione dei 12 menu Arcade, della localizzazione EN/ID/TH e dei roster sociali.
- Estensione di Name Color, Player Icon, Camera, Unkillable, Teleport, Privacy e Vote Player.
- Prime ottimizzazioni di lifecycle e rendering HUD; i dettagli storici restano disponibili nella cronologia Git.
- Dummy bot: creazione iniziale su Spawn Point reale, uscita dalla spawn ritardata di 1 s e destinazione 6–16 m dal target; riallineato `PLAYER VIBES` senza spazi manuali.
