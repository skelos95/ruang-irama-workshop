# Piano di test nel client Overwatch

Il validatore statico e la compilazione su Workshop.codes non sostituiscono questi test. Eseguirli dopo ogni patch importante di Overwatch, soprattutto per il rilevamento dei bot AI.

## 1. Importazione

- Impostare la lingua testuale del client su inglese.
- Incollare l'intero file `workshop/ruang_irama.workshop` dalla schermata Workshop.
- Verificare che non compaiano errori di parser e che tutte le 33 regole e le 12 subroutine siano presenti.
- Controllare che nomi delle regole e commenti siano in indonesiano.
- Controllare che gli HUD non usino Header: funzione nel testo principale, input nel sottotitolo.
- Controllare che il sorgente contenga 10 definizioni `Create HUD Text` e che nessuna palette HUD usi il grigio o una freccia.

## 2. Inizializzazione e lingua predefinita

- Entrare dopo l'avvio delle regole: liste, timer e variabili devono inizializzarsi una sola volta.
- Avviare o incollare le regole con un umano già presente: la regola fallback deve inizializzarlo e classificarlo senza richiedere un nuovo ingresso.
- Al primo ingresso, l'HUD deve essere in inglese e mostrare genere non ancora scelto, colore bianco e camera disattivata.
- In alto deve comparire `FRIENDLY DEDICATED SERVER` con `Server location: Indonesia`.
- Morire, cambiare eroe e respawnare: genere, colore e lingua scelti non devono azzerarsi.
- Uscire e rientrare: deve iniziare una nuova sessione con inglese predefinito e timer ripartito.

## 3. Classificazione, liste e blocco bot

Preparare una lobby con almeno due umani, un dummy bot Workshop e un normale bot AI della lobby.

- Le due persone compaiono a sinistra e a destra.
- Le righe delle due liste devono usare il formato compatto `Subheader`, mantenere il colore personale ed essere leggibili senza grigio.
- Nessuno dei due tipi di bot compare nelle liste.
- Dummy e bot AI non possono usare fuoco primario/secondario, abilità, ultimate, melee, reload o interact.
- Dummy e bot AI possono ancora camminare, saltare e usare crouch.
- Dopo morte, respawn e cambio eroe, il blocco combattimento deve restare attivo.
- I minuti partono da zero e aumentano a 1 dopo circa 60 secondi.
- Un umano entrato più tardi ha un tempo inferiore.
- Uscendo e rientrando, il suo timer riparte.
- Dopo l'uscita non resta una riga vuota e il conteggio testi non cresce a ogni ciclo join/leave.

Se il bot AI compare, verificare prima che le due sentinelle `U+200B` siano ancora presenti nel file copiato. Se lo sono, considerare il workaround incompatibile con la patch corrente e rimuovere i bot AI normali dalle impostazioni lobby.

## 4. Pressione lunga, Objective Description e menu principale

- Rilasciare Melee a 1,24 s: il menu non deve aprirsi.
- Tenere Melee almeno 1,25 s: compare il menu principale sulla voce `0`.
- Continuare a tenere Melee: il menu non deve chiudersi finché Melee non viene prima rilasciato.
- Con Primary Fire avanzare alla voce successiva e con Secondary Fire tornare alla precedente; verificare il wrap `0 ↔ 3` e l'ordine `0` musica, `1` camera, `2` colore, `3` lingua.
- Deve essere visibile una sola voce alla volta, non l'elenco completo dei quattro menu.
- Premere Interact: deve entrare soltanto nel sottomenu evidenziato.
- Dal menu principale e da ciascun sottomenu, tenere nuovamente Melee 1,25 s: il menu deve chiudersi.
- Nel menu principale, premere Reload: non deve succedere nulla.
- In ciascun sottomenu, premere Reload: deve tornare al menu principale sulla stessa voce senza chiudere il menu.
- Con una Objective Description attiva, verificare l'ordine verticale: titolo modalità sopra l'obiettivo, menu sotto l'obiettivo. Il menu deve avere una riga vuota iniziale e non sovrapporsi agli altri due elementi.
- Verificare i binding mostrati con almeno tastiera/mouse e controller.
- Morire con il menu aperto: il cleanup di sicurezza deve chiuderlo e i comandi devono tornare disponibili al respawn.

## 5. Menu `0` — genere musicale

- Con Primary Fire avanzare di un genere e con Secondary Fire tornare al precedente; verificare il wrap `1 ↔ 100`.
- Con Jump e Crouch verificare i salti rapidi −10 e +10, compreso il wrap.
- Deve apparire un solo genere alla volta, insieme alla corretta fascia da tranquilla a caotica.
- Verificare almeno la prima voce `Lowercase`, una voce centrale e l'ultima `Extratone`.
- Premere Interact: il genere si applica alla lista destra per tutti i viewer e il sottomenu resta aperto sulla stessa scelta.

## 6. Menu `1` — camera in terza persona

- Verificare le prime due scelte: camera disattivata e camera su sé stessi.
- Verificare che ogni altro giocatore spawnato abbia una voce con nome e icona eroe.
- La selezione deve includere un altro umano, un normale bot AI e un dummy bot; il viewer non deve essere duplicato nell'elenco perché dispone dell'opzione “sé stessi”.
- Con Primary Fire avanzare e con Secondary Fire tornare indietro di una scelta; verificare il wrap.
- Premere Interact su “sé stessi”: terza persona over-shoulder sul proprio eroe e menu ancora aperto.
- Premere Interact su ciascun tipo di bersaglio: la camera deve seguirlo e il menu deve restare aperto.
- Premere Interact su “camera disattivata”: ritorno alla prima persona senza chiusura del menu.
- Fare entrare o uscire giocatori mentre il sottomenu è aperto: la lista deve aggiornarsi senza indice fuori intervallo.
- Far uscire il bersaglio seguito: il viewer deve tornare automaticamente alla visuale normale.
- Provare pareti, colonne, porte, soffitti bassi, scale, salti e cadute.
- Con una parete dietro il target, la camera deve avanzare invece di attraversarla.
- Verificare che la camera sia sulla spalla destra.
- Con eroi di salute massima diversa, verificare che la distanza cresca con `Max Health` senza mai scendere sotto 3,5 m né superare 6 m.
- Verificare consapevolmente che il corpo del viewer resta attivo: non è uno slot spectator reale.

## 7. Menu `2` — colore personale

- Scorrere tutte le 20 sfumature con Primary Fire verso la successiva e Secondary Fire verso la precedente; verificare il wrap prima ↔ ultima.
- Ogni scelta deve mostrare un solo nome colore, in inglese o indonesiano secondo la lingua del viewer, con anteprima della sfumatura corretta.
- Premere Interact: il colore si applica e il menu resta aperto.
- La riga del giocatore deve aggiornarsi sia nella lista sinistra sia nella destra, per tutti gli umani.
- Due umani scelgono colori diversi: ognuno conserva il proprio colore nelle due liste.
- Cambiare colore mentre un altro umano sta ispezionando: il marker sul bersaglio deve aggiornarsi allo stesso colore.

## 8. Menu `3` — lingua HUD

- Al join, verificare che la scelta corrente sia `English`.
- Selezionare `Bahasa Indonesia` con Primary/Secondary Fire e applicare con Interact: menu, HUD strutturali, righe e messaggi successivi devono cambiare subito, senza chiudere il sottomenu.
- Il titolo resta `FRIENDLY DEDICATED SERVER`, mentre la seconda riga deve cambiare in `Lokasi server: Indonesia`; tornando a inglese deve mostrare `Server location: Indonesia`.
- Tornare a `English`: tutti gli stessi testi devono tornare a un inglese naturale e leggibile.
- Con due umani, lasciare uno in inglese e uno in indonesiano: ciascuno deve vedere entrambe le liste nella propria lingua, mentre nomi, valori e colori restano identici.
- La scelta linguistica di un giocatore non deve cambiare quella dell'altro.
- Nomi delle regole e commenti Workshop devono restare in indonesiano indipendentemente dalla lingua HUD.

## 9. Ispezione con Crouch

- Tenere Crouch: le nameplate native di tutti i giocatori devono sparire soltanto per quel viewer; gli altri client non devono essere influenzati.
- Deve comparire un testo personalizzato del viewer con nome, icona eroe e `ULT n%`, nel colore personale e in posizione stabile rispetto alla camera durante rotazioni e movimento.
- Il giocatore valido più vicino al reticolo deve mostrare sopra di sé nome, icona eroe e `ULT n%`. Non deve comparire alcuna freccia.
- Ripetere su un umano, un normale bot AI e un dummy bot: i bot restano fuori dalle liste ma sono ispezionabili; gli umani usano il proprio colore e i bot l'arancione.
- Spostare il reticolo fra due giocatori: deve essere mostrato un solo target, quello più vicino al reticolo, e il viewer non deve auto-selezionarsi.
- Un bersaglio morto, non spawnato o uscito deve essere rimosso dalla lettura senza errori.
- Cambiare eroe mentre si è osservati: icona e percentuale Ultimate devono aggiornarsi.
- Con Echo in duplicazione: mostrare l'eroe duplicato.
- Rilasciare Crouch: entrambi i testi personalizzati devono sparire e le nameplate native devono essere ripristinate subito.
- Ripetere l'uscita da ispezione aprendo il menu, morendo e avviando la camera su un altro giocatore: ogni percorso deve distruggere entrambi i testi e ripristinare le nameplate.

## 10. Cleanup, carico e durata

- Ripetere almeno 20 cicli join/leave alternando umani e bot.
- Verificare che righe, menu ed entrambi i testi nel mondo dell'umano uscito vengano distrutti e che le righe rimanenti continuino ad aggiornarsi.
- Controllare che anche il nuovo registro globale `TeksDiriPemain` resti allineato agli altri array dopo ogni uscita.
- Uscire mentre menu o ispezione sono attivi: non devono restare elementi orfani.
- Riempire la lobby con 12 umani.
- Aprire menu e ispezione su più client contemporaneamente; con 12 viewer in Crouch non devono esistere più di 24 IWT, due per viewer.
- Attivare più camere e osservare `Server Load Average` e `Server Load Peak` durante movimento rapido.
- Lasciare la sessione attiva almeno 30 minuti con join/leave ripetuti.
- Se il carico è eccessivo, ridurre per prima cosa il numero di camere simultanee; non rallentare il timer, che aggiorna già solo ogni secondo.

## Criterio di uscita dalla versione 0.4

La versione può ricevere un codice Blizzard condivisibile quando: import pulito, 33 regole e 12 subroutine riconosciute, filtro umano e blocco attacchi bot verificati, nessuna perdita HUD/IWT dopo 20 join/leave, menu `0/1/2/3` stabile sotto l'Objective Description, 100 generi e 20 colori raggiungibili, inglese/indonesiano indipendenti per viewer, nameplate Crouch ripristinate correttamente e camera destra stabile su umani, AI e dummy nelle mappe scelte.
