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
- I minuti partono da zero e aumentano a 1 dopo circa 60 secondi.
- Un umano entrato più tardi ha un tempo inferiore.
- Uscendo e rientrando, il suo timer riparte.
- Dopo l'uscita non resta una riga vuota e il conteggio testi non cresce a ogni ciclo join/leave.

Se il bot AI compare, considerare il workaround U+200B incompatibile con la patch corrente e rimuovere i bot AI normali dalle impostazioni lobby.

## 3. Pressione lunga e menu

- Rilasciare Melee a 1,49 s: il menu non deve aprirsi.
- Tenere Melee almeno 1,50 s: il menu si apre una volta sola.
- Continuare a tenere Melee, salvare/chiudere con un altro tasto: il menu non deve riaprirsi finché Melee non viene rilasciato.
- Verificare i binding mostrati con almeno tastiera/mouse e controller.
- Controllare wrap 1 ↔ 100, salti ±10 e tutte le intestazioni di pagina.
- Salvare `Lowercase`, una voce centrale ed `Extratone`; la lista destra deve aggiornarsi per tutti.
- Chiudere con Reload: il genere precedente deve rimanere.
- Morire con il menu aperto: il menu deve chiudersi e i comandi devono tornare disponibili al respawn.

## 4. Ispezione con Crouch

- Mirare un umano senza ostacoli: mostra nome, icona e nome eroe.
- Spostare la mira su un secondo umano: deve cambiare un solo target.
- Mettere due umani allineati: deve apparire soltanto il primo colpito.
- Interporre una parete: non deve apparire il giocatore dietro.
- Mirare il proprio eroe: non deve auto-selezionarsi.
- Cambiare eroe mentre si è osservati: HUD aggiornato.
- Con Echo in duplicazione: mostrare l'eroe duplicato.
- Aprire il menu durante Crouch: il pannello ispezione deve sparire.

## 5. Camera

- Ability 1 dal menu: terza persona over-shoulder su sé stessi.
- Ability 2 con un umano sotto il mirino: segue quel giocatore.
- Ability 2 mirando parete/vuoto/bot: resta nel menu e mostra il messaggio di errore.
- Ultimate dal menu: torna immediatamente alla camera normale.
- Provare pareti, colonne, porte, soffitti bassi, scale, salti e cadute.
- Con una parete dietro il target, la camera deve avanzare invece di attraversarla.
- Il target che esce dalla lobby deve far tornare il viewer alla visuale normale.
- Verificare consapevolmente che il corpo del viewer resta attivo: non è uno slot spectator reale.

## 6. Carico e durata

- Riempire la lobby con 12 umani.
- Aprire menu e ispezzione su più client contemporaneamente.
- Attivare più camere e osservare `Server Load Average` e `Server Load Peak` durante movimento rapido.
- Lasciare la sessione attiva almeno 30 minuti con join/leave ripetuti.
- Se il carico è eccessivo, ridurre per prima cosa il numero di camere simultanee; non rallentare il timer, che aggiorna già solo ogni secondo.

## Criterio di uscita dalla versione 0.1

La versione può ricevere un codice Blizzard condivisibile quando: import pulito, filtro umano verificato sulla patch corrente, nessuna perdita HUD dopo 20 join/leave, tutte le 100 scelte raggiungibili, ispezione corretta dietro pareti e camera stabile sulle mappe scelte.
