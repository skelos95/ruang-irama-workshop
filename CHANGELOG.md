# Changelog

## Interruttori dal menu principale e coerenza lingue — 2026-10-05

- Crouch + Interact alterna direttamente Travel/Attach, Privacy, Dummy Follow e Superman Punch nella voce principale. Pagina, cursore e HUD restano invariati; ogni pressione è consumata una sola volta. Le altre funzioni mantengono i propri sottomenu.
- Rimossi i quattro renderer e i rami dei sottomenu non più utilizzati; 117 regole e 67 subroutine, senza nuove variabili o frequenze. Le protezioni e il consenso al Dummy Follow restano gli stessi.
- Istruzione principale coerente in EN/ID/TH, HP completo tradotto in ID/TH e icona del bersaglio Camera aggiunta anche in thailandese. Controllati HUD e Small Message; nomi custom di regole, variabili e subroutine restano indonesiani.

## Raggio icone 10 m e controllo generale — 2026-10-04

- Raggio orizzontale delle icone sull'obiettivo aumentato da 5 a 10 m; altezza, colore del proprietario, movimento continuo e manutenzione a 1 Hz conservati. Nessuna nuova regola, variabile, attesa o entità.
- Allineati fixture, validatore, test geometrici e documentazione. La prova geometrica campiona anche il confine di 10 m e verifica il percorso dopo variazioni del roster.
- Revisione di regole, subroutine, variabili, scheduler, menu, cleanup, dummy, movimento, resurrect, Revenge e Luck: nessun nuovo difetto concreto o regola inutilizzata individuato. Le azioni simili in eventi o contesti diversi restano necessarie.

Le date seguenti descrivono revisioni di `main`. `VERSION` resta nominalmente 0.8.1: il tag storico non coincide con tutti gli aggiornamenti successivi. Dettagli e diff restano nella [cronologia Git](https://github.com/skelos95/ruang-irama-workshop/commits/main/).

## Superman Punch e movimento continuo delle icone — 2026-10-04

- Menu 15 rinominato Superman Punch: titoli principali e sottomenu EN/ID/TH aggiornati. Il colpo funziona anche con qualsiasi menu aperto; rimangono un solo bersaglio per attacco, Unkillable e il conteggio Revenge anche fra compagni.
- Il percorso delle icone dura 4,5 s e viene rinnovato dopo 3 s dalla posizione corrente. Il margine copre il controllo a 1 Hz, che poteva arrivare dopo la fine del vecchio percorso e lasciare le icone ferme.
- Raggio di 5 m, altezza 0,5–8 m, colori individuali e cleanup conservati; nessuna nuova regola, variabile o frequenza e nessun aumento del peso strutturale.

## Cozywatch, compattazione delle icone e budget strutturale — 2026-10-04

- La diagnostica del client sulla revisione `2e1c4ff` mostra 36.381 elementi e una regola da 130 KB: entrambi oltre il limite. I byte UTF-8 del sorgente non avevano rilevato questo superamento.
- Le 36 scelte Create Icon leggono un vettore individuale animato dal Chase nativo; eliminate le formule ripetute di interpolazione e gli array di waypoint ridondanti. Colore personale, altezza 0,5–8 m, limite di 12 icone e cleanup conservati. Nessun nuovo Wait, Loop o frequenza dello scheduler.
- Il preflight aggiunge un budget strutturale offline distinto dalle metriche compilate del client; controlli aggiornati per proprietari, animazione e regressioni del peso. Con la stessa stima il totale passa da 36.491 a 31.097 unità (−14,8%); la regola maggiore usa 4.500 unità, entro il budget locale di 5.000.
- Modalità rinominata Cozywatch nell'HUD, nelle impostazioni Workshop e nel benvenuto EN/ID/TH. Le tinte equivalenti già predefinite usano il valore colore nativo, conservando le palette personalizzate.
- Light Shaft rimosso su richiesta: restano solo icone sociali sull'obiettivo, entro un raggio fisso di 5 m. Eliminati effetto, palette del fascio e scala dinamica del roster.
- 121 regole, 71 subroutine, 126 campi player e 81 globali. Il conteggio compilato della nuova revisione richiede conferma nel gioco.

## Correzioni melee, icone native e interruttori diretti — 2026-10-04

- Super Punch cerca durante l'animazione senza ritardo fisso e consuma il colpo solo al contatto; l'evento melee nativo copre gli impatti fra campioni. Latch condiviso, Unkillable rispettato e Kill attribuito al player per Revenge.
- Icone testuali bianche sostituite con 12 entità Create Icon native al massimo, colorate con Name Color rivalutato. Cambio tipo e cleanup distruggono l'handle precedente; nuove traiettorie casuali a 0,5–8 m. Il fascio conserva il preset colore host più vicino.
- Travel/Attach, Privacy e Dummy Follow alternano direttamente lo stato con Interact nella schermata; rimossi tre cursori inutilizzati. Follow ON torna OFF entro 1 s senza dummy avversario e non riparte da solo.
- Profilo `งูแรร์`: default Charcoal / Poison 2, Draconian invariato.
- 121 regole, 71 subroutine, 125 campi player, 5 Wait e un Loop. Test automatici aggiornati ai casi segnalati; comportamento nativo e risorse compilate da confermare nel client.

## Super Punch, Light Shaft e testi menu — 2026-10-04

- Accorciate le descrizioni dei menu EN/ID/TH: restano comandi, stato attivo, selezione e indicazioni necessarie; rimosse spiegazioni ripetute o superflue. Comportamento, opzioni e tinte conservati.
- Diagnostica nel campo Text bianco dello stesso HUD Player Vibes, indipendente dal Name Color e dal ciclo RGB. Visibilità solo host e ultima riga; stringa vuota quando nascosta, senza nuovi handle, regole, variabili o timer.
- Menu 15 Super Punch, inizialmente OFF: Interact alterna il toggle. Un melee reale seleziona il più vicino davanti entro 2,5 m e con linea di vista libera; KO su nemici e alleati, rispettando Unkillable. Kill attribuito all'attaccante usa il ledger Revenge esistente, già compatibile con gli alleati. Registro opt-in e 12 timestamp globali, senza superare i 128 campi player.
- Un Light Shaft sull'obiettivo, raggio 0,5 m per umano fino a 6 m, colore nativo più vicino al Name Color dell'host. Fino a 12 icone fluttuanti senza nomi, nel colore esatto del proprietario; destinazioni casuali ogni 3 s e manutenzione a 1 Hz, cleanup su NONE/uscita/cambio squadra e conteggio IWT diagnostico.
- 120 regole, 71 subroutine, 5 Wait e un Loop. Le nuove collisioni melee, forme intermedie degli eroi e la resa del fascio richiedono verifica nel client.

## Palette e progressione menu — 2026-10-02

- Riordinati insieme tutti i 40 colori e le etichette EN/ID/TH: bianco, grigi, nero, colori caldi, rosa, viola, blu e verdi. White e Silver Mist conservano gli indici dei default; nessun colore eliminato.
- Black mostra nero puro anche nella preview Name Color, correggendo il precedente grigio del menu.
- Accenti delle pagine 1–14 nella stessa progressione, mescolati al Name Color attivo con rapporto costante 68/32. Funzioni e colori Travel conservati; transizioni native di 0,180 s, senza nuove routine, timer o risorse.

## Controllo generale e ridondanze — 2026-10-02

- Rimossi i rami del menu principale irraggiungibili nel renderer Ghost/Fly, chiamato soltanto per il sottomenu 13; testi e layout del sottomenu conservati.
- La tinta Ghost/Fly entra nel ternario condiviso: eliminato il primo `Chase` subito sostituito dall'override della pagina 13. Due transizioni native nella routine, stessa durata 0,180 s e stessi colori.
- Aggiornato lo stato corrente del README con 671 test e il riscontro funzionale dell'utente; le prove storiche di stabilità restano distinte dalle misure ancora da fare nel client.

## Tinta Multijump — 2026-10-02

- Il menu 14 e la sua preview hanno una tinta ambra dedicata, invece del colore Name Color di fallback. La transizione resta fluida in 0,180 s, nello stesso comando esistente; nessuna nuova routine, attesa o risorsa.

## Salto tenuto, tinte e rampa Fly — 2026-10-02

- Multijump funziona anche con menu aperto; forza fissa 100–1000% a passi del 100%. Jump tenuto ripete ogni 0,3 s in aria; nuove pressioni restano immediate. Cooldown individuale, ring temporaneo e protezioni Fly, Attach, Luck e Resurrect conservati.
- Ripristinata la transizione fluida delle tinte menu e della preview Name Color in 0,180 s, con stop durante cleanup. Gli effetti visivi dei comandi restano rimossi.
- Fly raggiunge il 1000% in 20 s con qualsiasi direzione di movimento. Cambiare direzione conserva la rampa; rilascio completo entro la deadzone la riporta al 100%. Mira, normalizzazione analogica, limite 55 m/s e priorità Luck conservati; HUD EN/ID/TH aggiornati.
- 115 regole, 66 subroutine, 128 campi player, 5 Wait e un Loop. Fisica e fluidità da verificare nel client.

## Cataloghi, salti multipli e feedback — 2026-10-02

- Aggiunti cento generi: venti per ciascuno dei dieci gruppi, con navigazione ±1/±10 e conteggio HUD dinamici. Palette da 32 a 40 colori, incluso Black; indici dei colori precedenti preservati.
- Menu 14 Multijump, inizialmente OFF: forza fissa 100–1000% a passi del 50%, salto aggiuntivo a ogni nuova pressione in aria. Stato individuale e motore chiamato solo ON; separato da Resurrect e sospeso con menu, Attach, Fly e Luck Acceleration.
- Rimossi gli effetti visivi dei menu e le pulsazioni di Revenge/Camera; tinte applicate immediatamente. Ring RGB temporaneo soltanto a ogni salto valido con Multijump ON, senza entità persistenti.
- Revisionati HUD e Small Message EN/ID/TH: messaggi Revenge più naturali, terminologia indonesiana coerente, testi Thai abbreviati e modificatore Crouch esplicito anche nel Soundtrack personalizzato bloccato. Identificatori, regole e commenti custom mantengono l'indonesiano.
- 115 regole, 66 subroutine, 5 Wait e un Loop. Comportamento fisico, resa dei testi e metriche compilate da verificare nel client.

## Scelta iniziale automatica — 2026-10-02

- Dopo 60 s senza primo spawn, il giocatore riceve Shion al controllo individuale 1 Hz. La scelta resta libera subito dopo; morte, cambio eroe e cambio squadra non riarmano il timer.
- Scadenza e latch individuali, nessun nuovo HUD, `Wait`, `Loop` o registro globale. Bot classificati e dummy esclusi dal ramo; assegnazione e cambio successivo da verificare nel client.
- Dummy Follow può essere attivato solo con un dummy nella squadra avversaria presente. Menu e comando verificano la disponibilità; disattivazione sempre libera e consenso già ON conservato durante un'assenza temporanea del dummy.

## Documentazione e controlli — 2026-09-30

- Guide accorciate e divise per uso: avvio, architettura, controlli automatici e test nel client. Accorpate le note dummy e rimosso l'audit ormai superato dalla documentazione corrente.
- Eliminato l'obbligo del validatore di dichiarare ogni guida “live-ready”; i risultati storici restano distinti dal riscontro attuale e dalle prove da completare.
- Parser dei validatori ottimizzato con cache limitata delle stringhe immutabili; conservati tutti i controlli semantici e aggiunte prove contro risultati obsoleti dopo una mutazione.
- L'utente riferisce stabilità migliorata dopo la PR #81; ulteriori stress test sono previsti. Nessuna modifica al codice Workshop in questa pulizia.

## Scheduler guidato dallo stato — 2026-09-29

[PR #81](https://github.com/skelos95/ruang-irama-workshop/pull/81), main `68cbc832`.

- Dispatch distinto per umani e bot; Fly/Luck/cache soltanto quando necessari, incluso lo stato residuo delle icone.
- Vision evita il filtro in idle. Slot dummy gestiti a 1 Hz con cooldown per squadra; target follow a 5 Hz, manutenzione bot a 10 Hz.
- 113 regole, 64 subroutine, 5 Wait e un Loop. Modello idle 1 umano + 2 dummy + 2 AI: 355 → 70 chiamate complessive/s alle routine delle cinque entità; non una misura del carico nativo.
- 591 test e nove controlli superati; stabilità prolungata da verificare nel client.

## Resurrect, Fly e sola Schermaglia — 2026-09-27

- Jump conserva il punto sicuro e prepara/conferma la destinazione camminabile prima e dopo Resurrect nei punti insicuri. Una morte immediata non riarma Jump tenuto. L'utente conferma il recupero nel punto prima problematico e la resurrezione sul posto ([PR #80](https://github.com/skelos95/ruang-irama-workshop/pull/80)).
- Fly sale da 100% a 1000% in 25 s di avanti puro; velocità richiesta massima 55 m/s ([PR #79](https://github.com/skelos95/ruang-irama-workshop/pull/79)).
- Rimossi i rami CTF, payload e Push: dummy e teleport automatico limitati alla Schermaglia. Le mappe restano nel preset della lobby.
- Preflight esteso ai nomi delle impostazioni. Il problema dei testi vuoti nel client si è risolto sul test minimo dopo riavvio completo del gioco.

## Regole e testi compatti — 2026-09-26

- Accorpati feedback identici, rimossi rami equivalenti e un blocco vuoto; istruzioni HUD EN/ID/TH abbreviate mantenendo binding, target e tempi.

## Ripristino dopo crash al cambio squadra — 2026-09-25

- Ritirata la [PR #76](https://github.com/skelos95/ruang-irama-workshop/pull/76): cache Arcade, aggiornamento periodico, cooldown cosmetico e rallentamento automatico introdotti insieme alla revisione Friendly.
- La [PR #77](https://github.com/skelos95/ruang-irama-workshop/pull/77) ripristina runtime e controlli precedenti (`2529608`). L'utente conferma che il cambio squadra non crasha più.
- Causa nativa non isolata: i 561 test della revisione ritirata non riproducevano il crash. Conservata la prova specifica in [TEST.md](docs/TEST.md#lifecycle-e-accumulo).

## Camera, Host e profilo — 2026-09-21–23

- Host nel campo Text, una riga vuota sopra/sotto e RGB animato del titolo.
- Revoca Camera durante quarantena del target anche senza cambio eroe; nome del profilo aggiornato a `งูแรร์`.
- In questa fase i dummy erano ammessi in Schermaglia/CTF; dal 27 settembre è supportata soltanto Schermaglia.

## Carico, risorse e collisioni — 2026-09-09–15

- Ridotti picchi di targhette e icone roulette; registri di proprietà e cleanup proteggono anche da handle persi o ID riciclati.
- Rimosso il conteggio minuti individuali: unico roster Player Vibes a sinistra. Diagnostica senza Inspector Recording.
- Dummy e AI conservano collisioni native, senza disabilitazioni o riapplicazioni dedicate.
- Semplificato un titolo regola dopo un errore d'importazione; causa del filtro client non confermata. Aggiunte regressioni sintattiche e clipboard dedicate.

## Timer, spawn e audit — 2026-09-07–08

- Durata Workshop 10–60 min, default 30; titolo Server Khusus Chill e Vibes dedicato Draconian.
- Retry uscita spawn dummy con 16 candidati e controlli geometrici, incluso il caso Paraíso.
- Tick dei player indipendenti dalla prenotazione setup; Attach rifiuta cicli lunghi, slot riutilizzabili e voti ricalcolati senza leggere entità uscite.
- Identificatori/commenti in Bahasa Indonesia; testi e Small Message rivisti in EN/ID/TH.

## 0.8.1 — release storica e revisioni iniziali

Stato: **live-ready** nella documentazione della regressione storica di agosto 2026; questa attestazione non si applica automaticamente al `main` successivo.

Il [tag v0.8.1](https://github.com/skelos95/ruang-irama-workshop/releases/tag/v0.8.1) identifica `14ad403babb56c58f9b55f8ebe902f13b18cd02c`. Le successive correzioni hanno mantenuto la versione nominale.

- Completati menu personali EN/ID/TH, Dummy Follow, Ghost/Fly, Camera condivisa, Travel & Attach e diagnostica.
- Regressioni su input, ownership, roster e cambio squadra. Il limite Fly storico era 500%; profilo e comportamento Resurrect hanno ricevuto correzioni successive.
- I resoconti precedenti sono conservati nella cronologia Git; le metriche live non fornite non vengono ricostruite.

## 0.8.0 — 2026-08-24

Consolidamento delle funzioni sociali, roulette a sei esiti, menu e localizzazione, con validazione semantica e regressioni automatiche.

## 0.7.2 — baseline

Base di riferimento precedente al consolidamento 0.8.x.

## 0.6.x — ricostruzione funzionale

Ricostruzione iniziale di menu, HUD e sistemi per-player.
