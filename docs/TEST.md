# Piano di test nel client Overwatch

Il validatore statico non sostituisce questi test. Eseguirli dopo ogni patch importante di Overwatch, soprattutto per il rilevamento dei bot AI.

## 1. Importazione

- Impostare la lingua testuale del client su inglese.
- Incollare l'intero file `workshop/ruang_irama.workshop`.
- Verificare che non compaiano errori di parser e che tutte le regole siano abilitate.
- Controllare che la descrizione e tutti i nomi delle regole siano in indonesiano.

## 2. Classificazione e liste

Preparare una lobby con almeno due umani, un dummy bot Workshop e un normale bot AI della lobby.

- Le due persone compaiono a sinistra e a destra.
- Nessuno dei due tipi di bot compare.
- Dummy e bot AI non possono usare fuoco primario/secondario, abilità, ultimate, melee, reload o interact.
- Dummy e bot AI possono ancora camminare, saltare e usare crouch.
- Dopo morte, respawn e cambio eroe, il blocco combattimento deve restare attivo.
- I minuti partono da zero e aumentano a 1 dopo circa 60 secondi.
- Un umano entrato più tardi ha un tempo inferiore.
- Uscendo e rientrando, il suo timer riparte.
- Dopo l'uscita non resta una riga vuota e il conteggio testi non cresce a ogni ciclo join/leave.

Se il bot AI compare, considerare il workaround del nome vuoto incompatibile con la patch corrente e rimuovere i bot AI normali dalle impostazioni lobby.

## 3. Pressione lunga e menu

- Rilasciare Melee a 1,49 s: il menu non deve aprirsi.
- Tenere Melee almeno 1,50 s: compare il menu principale con le sole voci numerate `0`, `1`, `3`.
- Continuare a tenere Melee: il menu non deve chiudersi finché Melee non viene prima rilasciato.
- Da menu principale e da ciascun sottomenu, tenere nuovamente Melee 1,5 s: il menu deve chiudersi.
- Verificare i binding mostrati con almeno tastiera/mouse e controller.
- Verificare che ogni HUD abbia funzione nel testo principale, input nel sottotitolo e nessun Header.
- Nel menu `0`, controllare wrap 1 ↔ 100, salti ±10 e tutte le pagine.
- Salvare `Lowercase`, una voce centrale ed `Extratone`; la lista destra deve aggiornarsi per tutti.
- Da un sottomenu, premere Reload: deve tornare al menu principale senza chiudere tutto.
- Nel menu principale, Reload non deve chiudere né applicare nulla.
- Morire con il menu aperto: il menu deve chiudersi e i comandi devono tornare disponibili al respawn.

## 4. Colore personale

- Aprire il menu `3` e scorrere tutti i 10 colori con wrap primo ↔ ultimo.
- Verificare che il testo del menu mostri l'anteprima del colore selezionato.
- Applicare un colore: la riga del giocatore deve aggiornarsi sia nella lista sinistra sia nella destra, per tutti gli umani.
- Due umani scelgono colori diversi: ognuno conserva il proprio colore nelle due liste.
- Cambiare colore mentre un altro umano sta ispezionando: il marker sul bersaglio deve aggiornarsi allo stesso colore.

## 5. Ispezione con Crouch

- Mirare un umano senza ostacoli: nome, freccia verso il basso e icona eroe compaiono direttamente sopra quel giocatore, non nel HUD.
- Freccia, nome e icona devono usare il colore scelto dal bersaglio.
- Spostare la mira su un secondo umano: deve cambiare un solo target.
- Mettere due umani allineati: deve apparire soltanto il primo colpito.
- Interporre una parete: non deve apparire il giocatore dietro.
- Mirare il proprio eroe: non deve auto-selezionarsi.
- Cambiare eroe mentre si è osservati: icona nel mondo aggiornata.
- Con Echo in duplicazione: mostrare l'eroe duplicato.
- Aprire il menu durante Crouch: il testo nel mondo deve sparire.

## 6. Camera

- Menu `1`, opzione “Diri sendiri”: terza persona over-shoulder su sé stessi.
- Menu `1`, opzione bersaglio con un umano sotto il mirino: segue quel giocatore.
- Opzione bersaglio mirando parete/vuoto/bot: resta nel sottomenu e mostra il messaggio di errore.
- Menu `1`, opzione “Matikan kamera”: torna alla visuale normale.
- Provare pareti, colonne, porte, soffitti bassi, scale, salti e cadute.
- Con una parete dietro il target, la camera deve avanzare invece di attraversarla.
- Il target che esce dalla lobby deve far tornare il viewer alla visuale normale.
- Verificare consapevolmente che il corpo del viewer resta attivo: non è uno slot spectator reale.

## 7. Carico e durata

- Riempire la lobby con 12 umani.
- Aprire menu e ispezione su più client contemporaneamente.
- Attivare più camere e osservare `Server Load Average` e `Server Load Peak` durante movimento rapido.
- Lasciare la sessione attiva almeno 30 minuti con join/leave ripetuti.
- Se il carico è eccessivo, ridurre per prima cosa il numero di camere simultanee; non rallentare il timer, che aggiorna già solo ogni secondo.

## Criterio di uscita dalla versione 0.2

La versione può ricevere un codice Blizzard condivisibile quando: import pulito, filtro umano e blocco attacchi bot verificati, nessuna perdita HUD/testi nel mondo dopo 20 join/leave, menu `0/1/3` stabile, 100 generi e 10 colori raggiungibili, marker Crouch corretto e camera stabile sulle mappe scelte.
