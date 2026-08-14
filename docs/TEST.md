# Piano di test — versione 0.5.5

Il validatore statico riduce il rischio di errori strutturali, ma non sostituisce il parser e il runtime di Overwatch. Ogni prova è quindi classificata come **statica** oppure **live**. Una prova live non va dichiarata superata sulla sola base del sorgente.

## 1. Gate statico

Eseguire il validatore read-only sul sorgente finale e verificare:

- sintassi, `[]` e nesting dei delimitatori bilanciati;
- regole e dichiarazioni ben formate, senza nomi o slot duplicati;
- tipi evento limitati all'elenco riconosciuto dal Workshop;
- assenza di un blocco `settings`;
- tre localizzazioni complete: English, Bahasa Indonesia e ไทย;
- selettore lingua con tre stati e inglese predefinito;
- 100 generi unici e raggiungibili;
- 20 colori con nome in ciascuna lingua;
- placeholder delle stringhe coerenti per indice e arità con i relativi argomenti;
- stringhe entro i limiti gestiti dal Workshop;
- esattamente due sentinelle reali `U+200B` per il riconoscimento dei bot AI;
- sei menu con indici `0..5`;
- navigazione Soundtrack `Primary/Secondary ±1` e `Jump/Crouch ±10`;
- un solo raycast direttamente sotto `Update Every Frame` nell'unico `Start Camera`;
- nessun loop `0.016`, cache coordinate o combinazione `Position Of + PosisiRelatifKamera`;
- blend `0`, arretramento con pitch completo, spalla solo yaw e margine parete calcolati nella stessa espressione visuale;
- nessuna azione che assegni score, vittoria o pareggio;
- `Restart Match` confinato al completamento del timer personalizzato;
- invarianti degli array paralleli e slot HUD limitati a `0..11`;
- invarianti non-camera della chiusura Melee, selezione Crouch e identità Teleport;
- controlli semantici immuni ad azioni simulate dentro stringhe o commenti;
- CI read-only eseguita per ogni modifica alla repository, senza commit automatici o workflow che la modifichino.

Prima del validatore eseguire anche i test negativi:

```powershell
python -m unittest discover -s tests -p 'test_*.py'
python tools/validate_workshop.py
```

I test devono rifiutare almeno commenti/stringhe che simulano azioni, cattura cleanup mancante, delimitatori malformati, duplicati, localizzazione incompleta, placeholder con arità errata e regressioni negli invarianti Crouch/Teleport. Esito, versione Python e blob effettivamente validato vanno registrati in [`VALIDAZIONE.md`](VALIDAZIONE.md).

## 2. Importazione nel client

1. Impostare temporaneamente la lingua testuale del client su English (US), se necessaria.
2. Incollare `workshop/ruang_irama.workshop` nella schermata Workshop.
3. Verificare che il parser non segnali errori, inclusi i nomi in Bahasa Indonesia e i glifi thai.
4. Confermare che l'import non cambi modalità, mappe o impostazioni lobby.
5. Salvare un preset locale per ripetere la matrice senza modificare il sorgente.

Atteso: import pulito e overlay attivo sulle impostazioni già configurate.

## 3. Contratto comune delle sei modalità 6v6

Ripetere la prova su Control, Escort, Hybrid, Push, Flashpoint e Clash:

1. impostare una durata breve in un preset di test oppure osservare il countdown configurato;
2. raggiungere una condizione che normalmente assegnerebbe un punto o completerebbe la mappa prima dello zero;
3. controllare che non vengano assegnati punti, vittoria o pareggio e che la partita continui;
4. attendere `00:00`;
5. verificare un solo `Restart Match`, senza schermata vincitore;
6. controllare che la nuova sessione riparta con il countdown completo.

Ripetere almeno una volta con `Server duration (minutes) = 30` e una con `90`. Il timer deve restare indipendente da pause o variazioni del tempo nativo della modalità e aggiornare l'HUD una volta al secondo.

## 4. Season 4: eroe e mappe

### D.Mon

- Usare D.Mon come viewer e come bersaglio della camera.
- Attivare e disattivare la camera, cambiare stato/modello e verificare che altezza e distanza vengano ricalcolate senza richiedere un cambio eroe.
- Ispezionare D.Mon con Crouch: nome, icona e Ultimate devono essere corretti.
- Usare D.Mon come destinazione Teleport e come bersaglio Revenge valido quando controllato da un umano.
- Ripetere dopo morte, respawn e cambio eroe per escludere cache obsolete.

### Busan, Paraíso ed Eichenwalde

- Provare camera contro pareti, porte, colonne, soffitti bassi, scale, bordi e nuove geometrie.
- Provare Teleport verso Spawn Room, target mobili e posizioni vicine agli obiettivi disponibili.
- Verificare che Crouch non conservi target attraverso occlusioni, morte o uscita.
- Eseguire il contratto timer della modalità core applicabile alla mappa.

## 5. Inizializzazione e classificazione

Preparare una lobby con umani, dummy bot Workshop e normali bot AI.

- Un umano già presente quando si attivano le regole deve essere preparato e classificato una sola volta.
- Un nuovo umano deve comparire nelle liste soltanto dopo la classificazione completa, con l'icona dell'eroe in entrambe le liste.
- Dummy e bot AI non devono comparire negli HUD sociali né poter aprire i menu.
- I bot devono restare disponibili come target per le funzioni che li supportano.
- Un dummy deve bypassare preparazione e classificazione degli umani ed essere bloccato dal lifecycle edge-triggered dedicato.
- Far uscire un player durante ciascuno dei due intervalli di classificazione: non deve apparire in ritardo né lasciare uno slot occupato.
- Verificare il blocco bot subito dopo classificazione, spawn, respawn e cambio eroe.
- Con dodici viewer che tengono Crouch, registrare un umano e spawnare/bloccare bot AI e dummy: le nuove nameplate devono risultare subito disabilitate per tutti i viewer attivi.
- Confermare che non esista un'attività periodica ogni 0,5 secondi dedicata soltanto a riaffermare il blocco.

Se un bot AI viene classificato come umano, controllare che le due sentinelle `U+200B` siano sopravvissute a copia e import. Se sono presenti, segnare il workaround come incompatibile con la patch live invece di dichiarare superato il test.

## 6. Cleanup e riuso degli slot

Eseguire almeno 50 cicli join/leave, alternando i seguenti stati al momento dell'uscita:

- menu principale o sottomenu aperto;
- camera attiva su sé stessi o su un altro target;
- Crouch attivo con entrambi i testi visibili;
- voce Revenge posseduta o bersaglio in un ledger altrui;
- Teleport aperto con destinazione selezionata;
- player ancora in classificazione;
- player morto o in respawn;
- player in hero-select oppure in transizione team ↔ spettatore.

Dopo ogni uscita verificare:

- nessun HUD, IWT, nameplate disabilitata o camera orfana;
- nessuna destinazione Teleport o camera riferita all'entità uscita;
- nessuna voce Revenge fantasma nei ledger dei superstiti;
- registri globali ancora allineati, incluso `SlotHUDPemain`;
- slot HUD liberato e riutilizzato nell'intervallo `0..11`;
- conteggi HUD/IWT tornati al livello previsto, senza crescita cumulativa.

Ripetere l'apertura di menu e Crouch durante cambio round, morte, despawn, hero-select e transizione team ↔ spettatore. In ogni caso pulsanti e nameplate devono essere ripristinati e HUD/IWT distrutti senza attendere un'uscita dalla lobby.

## 7. Localizzazione per viewer

Usare tre client contemporanei, uno per lingua.

- Il join iniziale deve mostrare English.
- Selezionare e applicare English, Bahasa Indonesia e ไทย dal menu lingua.
- Titolo, posizione, liste, sei menu, 20 colori, messaggi, Revenge, Teleport, camera e Crouch devono usare la lingua del singolo viewer.
- Aprire Revenge senza altri umani e verificare lo stato vuoto in English, Bahasa Indonesia e ไทย.
- I nomi internazionali dei 100 generi devono restare invariati.
- Il cambio deve essere immediato e non modificare la scelta degli altri client.
- Verificare thai naturale, glifi integri, wrapping e leggibilità a più risoluzioni e rapporti d'aspetto.
- Controllare che l'inglese e l'indonesiano siano naturali e coerenti, senza residui italiani nei testi visibili.
- Nomi di regole, subroutine, variabili e commenti personalizzati devono risultare in Bahasa Indonesia; le sole parti inglesi ammesse sono keyword/API native e acronimi tecnici necessari.

## 8. Menu e priorità input

- Tenere Melee per meno di 0,5 s: il menu non deve aprirsi.
- Tenere Melee per almeno 0,5 s: il menu deve cambiare stato una sola volta fino al rilascio.
- Con il menu in chiusura e Melee ancora premuto, provocare la morte a `0,10`, `0,25` e `0,49` secondi; dopo il rilascio Melee deve essere riabilitato e il latch deve consentire una nuova apertura.
- Verificare ordine e wrap delle sei voci `0..5`.
- Entrare in ciascun sottomenu con Interact, applicare una scelta e tornare con Reload.
- Confermare che un sottomenu resti aperto dopo l'applicazione, salvo le azioni che per progetto lo chiudono.
- Premere combinazioni simultanee e verificare la priorità `Interact → Reload → Primary → Secondary → Jump → Crouch`; mantenendo il chord, nessun input inferiore deve scattare dopo quello selezionato e il dispatcher deve riarmarsi soltanto al rilascio di tutti i sei tasti.
- Morire o aprire un sistema incompatibile con il menu: gli input dell'eroe devono essere ripristinati.
- Lasciare Revenge e Teleport aperti mentre giocatori entrano ed escono: dati e cursore devono aggiornarsi senza ricreazione periodica dell'HUD, sfarfallio o indice fuori intervallo.

### Soundtrack

- Primary e Secondary spostano di una voce (`+1` e `−1`) con wrap `1 ↔ 100`.
- Jump e Crouch spostano di dieci (`−10` e `+10`) con wrap.
- Verificare `Lowercase`, una voce centrale ed `Extratone`.
- Interact applica la scelta e aggiorna la lista visibile agli altri viewer.

### Camera, colore e lingua

- Camera: Off, sé stessi e tutti i target validi devono essere raggiungibili.
- Colore: tutte le 20 scelte devono avere anteprima e nome corretto per lingua.
- Lingua: il wrap deve comprendere esattamente i tre indici `0`, `1`, `2`.

### Revenge e Teleport

- Revenge deve mostrare dati aggiornati e ignorare killer non validi.
- Revenge deve mostrare anche gli altri umani con debito `0`, ma rifiutare il claim senza modificare il ledger.
- Teleport deve aggiornare Spawn Room, obiettivi previsti e player presenti senza conservare destinazioni uscite.

## 9. Revenge

- Subire una kill diretta da un altro umano: viene aggiunta una singola voce al ledger.
- Assist, suicidio, ambiente, dummy bot e bot AI non devono creare una voce.
- Morire più volte contro lo stesso umano e riscuotere una voce alla volta.
- Con debito `0`, verificare che l'umano resti visibile nel menu ma che il claim sia bloccato; senza altri umani, verificare lo stato vuoto localizzato in tutte e tre le lingue.
- Avviare un claim mentre la lista cambia: flag, `Kill` e messaggio devono usare la stessa identità catturata, senza rileggere array o cursore.
- Far uscire il bersaglio prima di applicare il claim: nessuna azione deve trasferirsi a un altro player.
- Far uscire un umano presente in più ledger: deve essere rimosso da tutti.
- Verificare che il flag di morte sia azzerato dalla regola `Player Died` e non causi duplicazioni al respawn.

## 10. Teleport

- Memorizzare la Spawn Room entrando nella propria stanza e provarne il richiamo fuori da essa.
- In Escort e Hybrid raggiungere una spawn avanzata: il richiamo successivo deve usare l'ultima spawn visitata, non quella iniziale.
- Tentare il richiamo mentre si è già nella Spawn Room: non deve produrre un teletrasporto inutile.
- Teletrasportarsi verso umano, bot AI e dummy bot.
- Verificare una posizione camminabile vicina al target, senza sovrapposizione dei corpi.
- Far morire o uscire la destinazione fra selezione e applicazione: l'azione deve annullarsi in modo sicuro.
- Far uscire la destinazione nello stesso ciclo dell'applicazione mentre un altro player prende lo stesso indice dopo il refresh: l'azione deve annullarsi, senza retarget sul nuovo elemento.
- Verificare le destinazioni obiettivo sulle sei modalità e sulle mappe Season 4 previste.

## 11. Camera e Crouch

### Camera

- Verificare spalla, distanza dinamica, punto di mira e margine anti-muro.
- Con camera sul proprio eroe, provare idle, corsa, strafe, salto, atterraggio, Crouch, scale e rotazioni rapide: non devono comparire onde verticali o movimento a scalini percepibile.
- Ripetere il test a 30, 60, 120 e 144 Hz o superiori, se disponibili: il personaggio non deve vibrare rispetto alla visuale.
- Eseguire sweep lenti e rapidi da circa `-89°` a `+89°`, poi guardare dritto in alto e in basso ai quattro orientamenti cardinali: l'eroe deve restare visibile e la spalla non deve capovolgersi o collassare.
- Ripetere gli estremi di pitch durante idle, corsa, strafe, salto, Crouch e volo; includere D.Mon e modelli grandi.
- Attraversare porte e costeggiare muri, colonne e spigoli: la camera deve rientrare senza clipping e tornare alla distanza normale senza pompaggio verticale.
- Provare pavimenti, soffitti bassi, scale e angoli concavi o convessi durante il pitch estremo: il raycast deve accorciare la distanza senza attraversare la geometria.
- Ripetere su un bersaglio remoto; un eventuale residuo di rete va distinto da un'oscillazione riproducibile sulla camera del proprio eroe.
- Controllare che per ogni aggiornamento venga usato un solo risultato di raycast memorizzato.
- Provare eroi di dimensioni e salute diverse, Echo in Duplicate e D.Mon nei suoi cambi di modello.
- Far uscire, morire o cambiare eroe al target: nessuna cache obsoleta e ritorno sicuro alla visuale normale quando necessario.
- Attivare 12 camere contemporaneamente per 10 minuti con movimento rapido e geometrie complesse.

### Crouch

- Le nameplate native devono essere disabilitate una sola volta all'ingresso e ripristinate in ogni uscita.
- Target vicino al reticolo aggiornato ogni 0,10 s; viewer, morti, non spawnati, inesistenti e target senza line-of-sight esclusi prima dell'ordinamento angolare.
- Mirare un target morto, uno dietro una parete e uno non spawnato con un secondo target valido: deve essere scelto il target valido col minore angolo, senza soglia aggiuntiva di distanza o angolo.
- Testi: colore personale per umani, arancione per bot e scala `0.900` per una leggibilità leggermente maggiore.
- Cambiare colore durante l'ispezione: l'aggiornamento deve avvenire senza loop permanente.
- Ripetere rilascio, apertura menu, morte, despawn, hero-select, team ↔ spettatore, camera e uscita; entrambi i testi devono sparire e le nameplate devono tornare visibili.
- Attivare Crouch contemporaneamente su 12 player e controllare correttezza e carico.
- Mentre i 12 player tengono Crouch, aggiungere umani e spawnare bot: nessuna nuova nameplate deve apparire ai viewer già in ispezione.

## 12. Stress e diagnostica

Eseguire due configurazioni minime:

1. 12 umani attivi;
2. 6 umani + 6 bot, includendo se possibile sia bot AI sia dummy bot.

Per almeno 10 minuti combinare camere, Crouch, menu, Revenge, Teleport, morti, respawn e cambi eroe. Integrare i 50 cicli join/leave del test cleanup.

Con `Performance diagnostics = Off`:

- nessun HUD diagnostico visibile;
- nessuna registrazione Inspector dedicata mantenuta dal sistema.

Con `Performance diagnostics = On`:

- dati visibili soltanto all'host;
- etichette nella lingua HUD scelta dall'host, incluse English, Bahasa Indonesia e ไทย;
- carico corrente, medio, picco e conteggi HUD/IWT aggiornati;
- `Server Load Average < 80%`;
- `Server Load Peak < 100%`;
- nessun warning, arresto o crash;
- nessuna crescita permanente dei conteggi dopo il cleanup.

Un eventuale superamento delle soglie o crash rende la prova fallita: non va mascherato come limite del validatore.

## Criterio di rilascio 0.5.5

La release è pronta per un codice Blizzard condivisibile soltanto quando:

- il gate statico è superato sul blob finale;
- il client importa lo stesso blob senza errori;
- tutte e sei le modalità rispettano il contratto timer/no-score/no-winner;
- le tre lingue e i sei menu sono verificati dal vivo;
- D.Mon, Busan, Paraíso ed Eichenwalde non mostrano regressioni note;
- i test a 12 player e 50 join/leave rispettano i gate di carico e cleanup;
- Crouch, camera, Revenge e Teleport superano i rispettivi casi di uscita.

Fino ad allora lo stato resta **static-ready, live-pending** e [`VALIDAZIONE.md`](VALIDAZIONE.md) deve distinguere esplicitamente i controlli statici superati dalle prove live pendenti.
