# Changelog

Le date seguenti descrivono revisioni di `main`. `VERSION` resta nominalmente 0.8.1: il tag storico non coincide con tutti gli aggiornamenti successivi. Dettagli e diff restano nella [cronologia Git](https://github.com/skelos95/ruang-irama-workshop/commits/main/).

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
