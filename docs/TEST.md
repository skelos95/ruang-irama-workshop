# Piano di test nel client Overwatch

Il validatore statico e la compilazione su Workshop.codes non sostituiscono questi test. Eseguirli dopo ogni patch importante di Overwatch, soprattutto per il rilevamento dei bot AI.

## 1. Importazione

- Impostare la lingua testuale del client su inglese.
- Incollare l'intero file `workshop/ruang_irama.workshop` dalla schermata Workshop.
- Verificare che non compaiano errori di parser e che tutte le 27 regole siano abilitate.
- Controllare che nomi delle regole e commenti siano in indonesiano.
- Controllare che gli HUD non usino Header: funzione nel testo principale, input nel sottotitolo.

## 2. Inizializzazione e lingua predefinita

- Entrare dopo l'avvio delle regole: liste, timer e variabili devono inizializzarsi una sola volta.
- Avviare o incollare le regole con un umano già presente: la regola fallback deve inizializzarlo e classificarlo senza richiedere un nuovo ingresso.
- Al primo ingresso, l'HUD deve essere in inglese e mostrare genere non ancora scelto, colore bianco e camera disattivata.
- Morire, cambiare eroe e respawnare: genere, colore e lingua scelti non devono azzerarsi.
- Uscire e rientrare: deve iniziare una nuova sessione con inglese predefinito e timer ripartito.

## 3. Classificazione, liste e blocco bot

Preparare una lobby con almeno due umani, un dummy bot Workshop e un normale bot AI della lobby.

- Le due persone compaiono a sinistra e a destra.
- Nessuno dei due tipi di bot compare nelle liste.
- Dummy e bot AI non possono usare fuoco primario/secondario, abilità, ultimate, melee, reload o interact.
- Dummy e bot AI possono ancora camminare, saltare e usare crouch.
- Dopo morte, respawn e cambio eroe, il blocco combattimento deve restare attivo.
- I minuti partono da zero e aumentano a 1 dopo circa 60 secondi.
- Un umano entrato più tardi ha un tempo inferiore.
- Uscendo e rientrando, il suo timer riparte.
- Dopo l'uscita non resta una riga vuota e il conteggio testi non cresce a ogni ciclo join/leave.

Se il bot AI compare, verificare prima che le due sentinelle `U+200B` siano ancora presenti nel file copiato. Se lo sono, considerare il workaround incompatibile con la patch corrente e rimuovere i bot AI normali dalle impostazioni lobby.

## 4. Pressione lunga e menu principale

- Rilasciare Melee a 1,49 s: il menu non deve aprirsi.
- Tenere Melee almeno 1,50 s: compare il menu principale sulla voce `0`.
- Continuare a tenere Melee: il menu non deve chiudersi finché Melee non viene prima rilasciato.
- Con Primary Fire e Secondary Fire verificare wrap `0 ↔ 3` e ordine `0` musica, `1` camera, `2` colore, `3` lingua.
- Deve essere visibile una sola voce alla volta, non l'elenco completo dei quattro menu.
- Premere Interact: deve entrare soltanto nel sottomenu evidenziato.
- Da menu principale e da ciascun sottomenu, tenere nuovamente Melee 1,5 s: il menu deve chiudersi.
- Dal menu principale e da ciascun sottomenu, premere Reload: il menu deve chiudersi.
- Verificare i binding mostrati con almeno tastiera/mouse e controller.
- Morire con il menu aperto: il cleanup di sicurezza deve chiuderlo e i comandi devono tornare disponibili al respawn.

## 5. Menu `0` — genere musicale

- Con Primary Fire e Secondary Fire scorrere un genere alla volta e verificare il wrap `1 ↔ 100`.
- Con Jump e Crouch verificare i salti rapidi −10 e +10, compreso il wrap.
- Deve apparire un solo genere alla volta, insieme alla corretta fascia da tranquilla a caotica.
- Verificare almeno la prima voce `Lowercase`, una voce centrale e l'ultima `Extratone`.
- Premere Interact: il genere si applica alla lista destra per tutti i viewer e il sottomenu resta aperto sulla stessa scelta.

## 6. Menu `1` — camera in terza persona

- Verificare le prime due scelte: camera disattivata e camera su sé stessi.
- Verificare che ogni altro giocatore spawnato abbia una voce con nome e icona eroe.
- La selezione deve includere un altro umano, un normale bot AI e un dummy bot; il viewer non deve essere duplicato nell'elenco perché dispone dell'opzione “sé stessi”.
- Con Primary Fire e Secondary Fire scorrere una sola scelta per volta e verificare il wrap.
- Premere Interact su “sé stessi”: terza persona over-shoulder sul proprio eroe e menu ancora aperto.
- Premere Interact su ciascun tipo di bersaglio: la camera deve seguirlo e il menu deve restare aperto.
- Premere Interact su “camera disattivata”: ritorno alla prima persona senza chiusura del menu.
- Fare entrare o uscire giocatori mentre il sottomenu è aperto: la lista deve aggiornarsi senza indice fuori intervallo.
- Far uscire il bersaglio seguito: il viewer deve tornare automaticamente alla visuale normale.
- Provare pareti, colonne, porte, soffitti bassi, scale, salti e cadute.
- Con una parete dietro il target, la camera deve avanzare invece di attraversarla.
- Verificare consapevolmente che il corpo del viewer resta attivo: non è uno slot spectator reale.

## 7. Menu `2` — colore personale

- Scorrere tutte le 20 sfumature con Primary Fire e Secondary Fire e verificare il wrap prima ↔ ultima.
- Ogni scelta deve mostrare un solo nome colore, in inglese o indonesiano secondo la lingua del viewer, con anteprima della sfumatura corretta.
- Premere Interact: il colore si applica e il menu resta aperto.
- La riga del giocatore deve aggiornarsi sia nella lista sinistra sia nella destra, per tutti gli umani.
- Due umani scelgono colori diversi: ognuno conserva il proprio colore nelle due liste.
- Cambiare colore mentre un altro umano sta ispezionando: il marker sul bersaglio deve aggiornarsi allo stesso colore.

## 8. Menu `3` — lingua HUD

- Al join, verificare che la scelta corrente sia `English`.
- Selezionare `Bahasa Indonesia` con Primary/Secondary Fire e applicare con Interact: menu, HUD strutturali, righe e messaggi successivi devono cambiare subito, senza chiudere il sottomenu.
- Tornare a `English`: tutti gli stessi testi devono tornare a un inglese naturale e leggibile.
- Con due umani, lasciare uno in inglese e uno in indonesiano: ciascuno deve vedere entrambe le liste nella propria lingua, mentre nomi, valori e colori restano identici.
- La scelta linguistica di un giocatore non deve cambiare quella dell'altro.
- Nomi delle regole e commenti Workshop devono restare in indonesiano indipendentemente dalla lingua HUD.

## 9. Ispezione con Crouch

- Mirare un umano senza ostacoli: nome, freccia verso il basso e icona eroe compaiono direttamente sopra quel giocatore, non nel HUD.
- Ripetere su un normale bot AI e su un dummy: entrambi devono mostrare nome, freccia arancione e icona eroe pur restando fuori dalle liste.
- Su un bersaglio umano, freccia, nome e icona devono usare il colore scelto da quel giocatore.
- Spostare la mira su un secondo giocatore: deve cambiare un solo target.
- Mettere due giocatori allineati: deve apparire soltanto il primo colpito.
- Interporre una parete: non deve apparire il giocatore dietro.
- Mirare il proprio eroe: non deve auto-selezionarsi.
- Cambiare eroe mentre si è osservati: icona nel mondo aggiornata.
- Con Echo in duplicazione: mostrare l'eroe duplicato.
- Aprire il menu durante Crouch: il testo nel mondo deve sparire.

## 10. Cleanup, carico e durata

- Ripetere almeno 20 cicli join/leave alternando umani e bot.
- Verificare che righe, menu e testi nel mondo dell'umano uscito vengano distrutti e che le righe rimanenti continuino ad aggiornarsi.
- Uscire mentre menu o ispezione sono attivi: non devono restare elementi orfani.
- Riempire la lobby con 12 umani.
- Aprire menu e ispezione su più client contemporaneamente.
- Attivare più camere e osservare `Server Load Average` e `Server Load Peak` durante movimento rapido.
- Lasciare la sessione attiva almeno 30 minuti con join/leave ripetuti.
- Se il carico è eccessivo, ridurre per prima cosa il numero di camere simultanee; non rallentare il timer, che aggiorna già solo ogni secondo.

## Criterio di uscita dalla versione 0.3

La versione può ricevere un codice Blizzard condivisibile quando: import pulito, filtro umano e blocco attacchi bot verificati, nessuna perdita HUD/testi nel mondo dopo 20 join/leave, menu `0/1/2/3` stabile, 100 generi e 20 colori raggiungibili, inglese/indonesiano indipendenti per viewer, marker Crouch corretto e camera stabile su umani, AI e dummy nelle mappe scelte.
