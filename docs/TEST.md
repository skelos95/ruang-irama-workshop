# Test nel gioco

Questa è la matrice operativa per il sorgente corrente, non una dichiarazione che tutte le prove siano già completate. Eseguire prima i [controlli automatici](VALIDAZIONE.md), poi associare ogni prova al commit importato.

## Riscontri disponibili

| Data / revisione | Riscontro | Limite |
|---|---|---|
| Release storica 0.8.1 | La documentazione precedente riporta la regressione client completata nell'agosto 2026. | Non valida automaticamente i successivi commit di `main`; metriche mancanti non vengono ricostruite. |
| 25 settembre, ripristino PR #77 | L'utente conferma la scomparsa del crash al cambio squadra introdotto dalla PR #76. | Singola istruzione responsabile non isolata. |
| 27 settembre, PR #80 | L'utente conferma il recupero dal punto nel vuoto prima problematico e la resurrezione sul terreno. | Altre mappe e combinazioni richiedono prove dedicate. |
| 29 settembre, `68cbc832` / PR #81 | 591 test e 9 controlli GitHub superati; modello idle con 1 umano + 2 dummy + 2 AI: 355 → 70 chiamate complessive/s alle routine delle cinque entità. | Numero di chiamate, non consumo del server. |
| 30 settembre, riscontro utente dopo PR #81 | Il server sembra molto più stabile; l'utente prevede test più aggressivi. | Non sono stati forniti durata, configurazione completa o metriche di questo riscontro. |
| 2 ottobre, PR #85–86 | L'utente conferma il funzionamento di Multijump, Fly e tinte menu; 671 test e nove controlli GitHub superati. | Conferma funzionale, senza nuove misure di carico o durata. |

## Preparazione

Usare una nuova lobby sulla build corrente del client, lingua testo italiana, Schermaglia e mappe standard escluse quelle Workshop. Importare il [file completo](../workshop/ruang_irama.it-IT.workshop), annotando SHA e metriche di compilazione. Le mappe appartengono al preset della lobby.

Per il confronto di stabilità impostare **60 minuti**; il riavvio allo zero è previsto e va distinto dalla chiusura con errore. La diagnostica host mostra carico e risorse senza abilitare Inspector Recording. Per input simultanei servono più utenti reali, non solo bot.

## Sequenza di carico

| Prova | Esecuzione | Cosa osservare |
|---|---|---|
| Idle | Una sessione di 60 min con 1 umano + 2 dummy; ripetere con 2 bot normali aggiunti | Tempo dell'eventuale errore, LOAD/AVG/MAX, HUD/IWT |
| Uso simultaneo | 1, 6 e 12 umani aprono menu diversi, Camera, Luck, Fly e Travel | Comandi isolati, input reattivi, countdown/RGB regolari |
| Ricambio | Almeno 50 ingressi/uscite, anche simultanei; slot riusato prima del cleanup precedente | Nessun limite alle identità storiche, stato nuovo senza dati ereditati |
| Cambio squadra | 20 cambi singoli, 10 simultanei e una cascata a lobby piena | Nessun crash, doppione HUD o riferimento al vecchio player |
| Soak pieno | Almeno 30 min con 12 slot, alternando funzioni, morti e ricambio | Contatori stabili in stati equivalenti, nessuna crescita progressiva |
| Rotazione mappe | Entrambi i team su tutte le mappe scelte; priorità Paraíso | Uscita spawn, respawn dummy e teleport sicuri |

Misurare baseline vuota, dopo gli ingressi, durante il picco e dopo cleanup completo. Ripetere la stessa configurazione quando si confrontano revisioni; una singola sessione riuscita non copre tutte le combinazioni.

Con 12 umani, menu chiusi e nessun overlay temporaneo, il baseline previsto è 21 HUD: nove fissi più una riga Player Vibes per umano. Le icone e gli In-World Text vanno confrontati separatamente.

## Regressioni da provare

### Input, menu e HUD

- In EN/ID/TH aprire tutte le 15 pagine, applicare, tornare e riaprire; percorrere `11→12→13→14→0` e l'inverso. Navigare nella stessa pagina non deve creare altri HUD.
- Verificare Crouch come modificatore menu, hold Melee/Interact di 0,5 s, salto musica ±10 e wrap. Melee e Jump restano nativi da vivi.
- Tenere Interact e cambiare soltanto Crouch: menu e Camera non possono riutilizzare la stessa pressione. Serve rilasciare Interact.
- Da morto il menu resta visibile ma congelato; Jump funziona anche con menu, Camera o Luck precedentemente attivi.
- Controllare binding dinamici, glifi Thai, righe leggibili, un unico Player Vibes, Host nel campo Text con spazio sopra/sotto e RGB del titolo; niente `0` diagnostico o sovrapposizioni con HUD nativi.
- Il profilo `งูแรร์` parte Silver Mist / Poison 2 modificabili e Draconian fisso; il Soundtrack resta in sola lettura senza aggiungere un genere al catalogo globale.
- Soundtrack: 200 generi, venti per gruppo, wrap 1↔200 e ±10 ai confini. Name Color: 40 colori, wrap 1↔40, ordine bianco → grigi → nero → colori caldi → rosa → viola → blu → verdi; etichette EN/ID/TH allineate, Black nero anche nella preview. Menu 0–14: accenti nella stessa progressione, funzioni nelle posizioni abituali e stessa tinta tra preview e sottomenu. Tinte fluide in 0,180 s, senza pulsazioni all'apertura, applicazione o revoca Camera/Revenge.

### Jump, Ghost e Fly

- Multijump OFF: salto nativo. ON: scegliere 100%, 200% fino a 1000%; dopo il primo salto premere Jump in aria oppure tenerlo premuto per ripetere ogni 0,3 s. La forza scelta resta fissa. Provare menu aperto e chiuso, discesa rapida, salita e soffitti. Ring RGB breve sotto i piedi ai salti validi, mai persistente e senza ripetizioni da fermo a terra.
- Attivare Multijump con Jump già tenuto: prima ripetizione dopo 0,3 s. Provare Attach, Fly/Luck Acceleration e morte: nessuna spinta finché bloccato, ripresa con la cadenza prevista dopo lo sblocco. Resurrect conserva il rilascio necessario prima di un nuovo salto. Provare due player con forze diverse e 12 simultanei, navigazione menu, morte/cambio eroe e reset cambio squadra/leave. Verificare primo distacco da terra e atterraggi rapidi.
- Morire su terreno normale, vicino a bordi e nel vuoto profondo: conservare il punto sicuro, recuperare sul punto camminabile nei casi insicuri. Includere Self Elimination con Travel aperto.
- Tenere Jump durante una nuova morte immediata: nessun ciclo di tentativi. Rilasciare da vivo o morto e ripremere deve riarmarlo. Provare due player insieme, Ghost/Fly ON/OFF e cambio eroe.
- Ghost deve attraversare pareti/soffitti mantenendo pavimenti e collisioni player. Fly: avanti segue la mira fino a pitch ±90°; indietro/laterali rimangono orizzontali, anche con yaw cardinali e analogico.
- Rampa in ogni direzione: 100% iniziale, 325% a 5 s, 550% a 10 s, 1000% a 20 s; massimo richiesto 55 m/s sulla baseline 5,5 m/s. Passare avanti→laterale→indietro→diagonale senza perdere velocità o progressione. Solo rilascio completo entro la deadzone azzera la rampa; nessun input produce hover senza deriva. Includere diagonali analogiche vicine alla soglia e due player indipendenti.
- Verificare morte/rinascita, cambio eroe, OFF e due player indipendenti. Preferenze conservate a morte/cambio eroe, azzerate a cambio squadra/leave-rejoin.
- Con Luck Acceleration, nessun impulso o freno Fly deve interferire per i 10 s; alla scadenza la rampa Fly riparte dal 100%.

### Camera, Privacy e Travel

- Camera personale/watch fluida in corsa, strafe e salto. Target morto, uscito, privato o in quarantena fa tornare alla visuale normale; altre Camera valide restano indipendenti.
- Verificare la revoca al cambio squadra anche con lo stesso eroe e prima della morte/respawn del target.
- Privacy ON esclude Camera, inspection, Teleport e Attach. Vision ignora intenzionalmente Privacy, ma elimina le targhette Crouch concorrenti.
- Provare tutte le 5 pagine Travel, navigazione senza esecuzione, esecuzione solo con Interact, binding reali e Self Elimination con cooldown per-player 3 s.
- Teleport a spawn, obiettivo e Player/Bot: target riletto al click, destinazione sicura oppure azione annullata. Provare obiettivi non visibili e target che muore/esce tra preview e click.
- Attach: rifiutare self-attach, `A→B→C→A` e cicli lunghi senza rompere relazioni valide. Sgancio con Crouch+Reload; Reload solo resta nativo. Morte, uscita, Privacy e quarantena invalidano i collegamenti.
- Targhette: un solo IWT con icona/nome/salute segue il soggetto giusto durante movimento e cambio target, senza trasferire un vecchio handle a un altro player.
- Cambiare rapidamente target inspection/Travel: il refresh di creazione limitato a 0,25 s deve evitare picchi senza mantenere testi di target invalidi.

### Unkillable, Revenge e Try Your Luck

- FULL HP protegge insieme da danni, urti e collisioni player, anche in spawn; OFF/1 HP ripristinano i tre comportamenti normali. 1 HP resta curabile.
- Provare tutti i sei risultati Luck: Vision 15 s, Acceleration 10 s, Skull finale, Team Heal immediato, Burning 10 s, Hacked 5 s.
- Skull durante i giri non deve uccidere. Il finale gestisce de-mech/duplicazioni prima della morte completa e si sblocca alla deadline; testare D.Va e gli eroi disponibili con forme intermedie.
- Burning sospende Unkillable per tutti i 10 s e infligge 5% Max Health ogni secondo; alla fine o cleanup anticipato ripristina la scelta. Gli altri esiti compatibili mantengono la protezione.
- Team Heal cura la squadra viva e informa solo il proprietario; cambiare team durante l'icona HEART non lascia icone orfane.
- Attivare Vision con più viewer, poi far terminare/uscire l'ultimo: nessun pubblico residuo. Join/leave durante roulette aggiornano la visibilità delle icone.
- Revenge consuma una volta solo alla morte completa, non al click o al de-mech; testare timeout, rinascita, leave, cambio team e identità esatte di vittima/attaccante.

### Lifecycle e accumulo

- Restare alla scelta iniziale senza eroe per 60 s: Shion al successivo controllo 1 Hz, poi scelta libera di un altro eroe. Scegliere prima della scadenza deve annullare l'assegnazione; provare due ingressi distanziati, uscita/rientro, cambio squadra prima della scelta e presenza di dummy/AI.
- Dopo il primo spawn, morire o cambiare squadra/eroe e restare nella selezione oltre 60 s: nessuna nuova assegnazione automatica. Spettatori esclusi; verificare nel client l'assegnazione iniziale e il rilascio immediato della selezione forzata.
- Cambiare squadra subito dopo l'ingresso senza menu, dopo alcuni minuti, con menu aperto e mentre altri osservano o hanno Camera/Vote aperti. Includere doppi cambi rapidi durante quarantena.
- Lasciare con menu, Camera, Fly, Vision, Luck, voto e debiti attivi; far entrare un'identità diversa nello stesso slot. Il leave ritardato non deve distruggere risorse del nuovo occupante.
- Nomi temporaneamente vuoti e join duplicati non prenotano slot errati. Uccidere un AI durante classificazione non deve bloccare scheduler o altri ingressi.
- Dopo cleanup: default ripristinati, Camera/Attach sganciati, voti ricalcolati, nessun target obsoleto o icona orfana. Svuotando la lobby tornano liberi tutti i 12 slot.
- Ripetere morte, cambio eroe, Self Elimination e Resurrect con HUD/IWT/icone; confrontare contatori in stati equivalenti per individuare handle persi anche se non più presenti nei registri.

### Dummy e mappe

- Almeno due slot liberi consentono un dummy per team; uno solo non basta. A squadra piena il dummy lascia il posto; alternare ingressi/uscite vicino alla soglia senza cicli crea/distruggi.
- La manutenzione slot avviene al passaggio 1 Hz idoneo. Fallimento creazione o scomparsa dummy non devono causare retry ravvicinati; le squadre hanno cooldown indipendenti.
- Spawn iniziale, ritorno in spawn, morte e respawn: stabilizzazione di circa 1 s, ricerca sicura con retry, respawn massimo configurato 3 s. Su Paraíso provare entrambi i team e ripetere dopo cambio mappa.
- Senza destinazione valida restare in spawn, senza teleport all'origine o nel vuoto. Verificare anche mappe senza obiettivo visibile.
- Velocità 20%, danni/urti ricevuti normali, collisioni native e assenza di input offensivi/menu. Gli AI normali conservano la loro navigazione.
- Follow inizialmente OFF; ON seleziona solo il nemico umano vivo più vicino fra gli opt-in. Invertire distanze, opt-out, morte e squadra; stop entro 4 m e ripartenza oltre. Se nessun target resta idoneo, stop facing/throttle. La selezione è a 5 Hz.
- Con il solo dummy della squadra 1, solo la squadra 2 può attivare Follow; ripetere invertendo i team. Senza dummy ON è bloccato, OFF resta disponibile. Rimuovere il dummy dopo aver aperto il menu e verificare disponibilità e feedback EN/ID/TH senza un'errata conferma di attivazione.
- Nelle modalità escluse non devono essere creati dummy; i bot restano target validi per Camera/inspection/Vision senza attivare funzioni umane.

## Metriche e rapporto

| Metrica | Soglia del progetto |
|---|---|
| Element Count compilato | Inferiore a 32.768; obiettivo ≤26.000 |
| Largest Rule compilata | Inferiore a 98 KB; obiettivo ≤80 KB |
| HUD / In-World Text / icone / Entity Count | Ritorno al baseline dello stesso stato, nessuna crescita progressiva |
| LOAD / AVG / MAX | Registrare nel client; non dedurre dai soli test Python |

Compilare senza inventare misure mancanti:

```text
Commit importato / eventuale tag:
Build client, piattaforma, regione:
Data, mappa, modalità, durata e timer:
Umani / dummy / bot normali:
Prove eseguite e risultato PASS/FAIL/non provato:
Element Count / Largest Rule:
LOAD / AVG / MAX:
Risorse prima / picco / dopo cleanup:
Messaggio e minuto dell'errore, se presente:
Passi per riprodurre, screenshot o video:
```

La regressione della PR #76 resta un precedente utile: 561 test verdi non rilevarono il crash nativo al primo cambio squadra. Per estendere una conclusione sulla stabilità serve il risultato nel client della revisione esatta, non soltanto il numero dei test.
