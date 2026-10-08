# Test nel gioco

Questa è la matrice operativa per il sorgente corrente, non una dichiarazione che tutte le prove siano già completate. Eseguire prima i [controlli automatici](VALIDAZIONE.md), poi associare ogni prova al commit importato.

## Riscontri disponibili

| Data / revisione | Riscontro | Limite |
|---|---|---|
| Release storica 0.8.1 | La documentazione precedente riporta la regressione client completata nell'agosto 2026. | Non valida automaticamente i successivi commit di `main`; metriche mancanti non vengono ricostruite. |
| 25 settembre, ripristino PR #77 | L'utente conferma la scomparsa del crash al cambio squadra introdotto dalla PR #76. | Singola istruzione responsabile non isolata. |
| 5 ottobre, dopo PR #94 | Nuovo crash al cambio squadra segnalato in lobby nuova con un umano, senza menu. | Forward rimosso nella PR #95; non ha eliminato il crash. |
| Riscontro successivo alle PR #95–96 | Il crash persisteva anche al primo cambio diretto, senza menu né icone; passando prima dagli spettatori l'utente non lo osservava. | Le attese per-player della PR #96 non avevano risolto; vedere il riscontro successivo sul runtime globale. |
| Riscontro sul runtime globale, precedente alla revisione Camera/Info | L'utente conferma importazione riuscita e cambio diretto di squadra senza il crash precedentemente osservato. | Conferma qualitativa; SHA importato, durata, numero di player e metriche native non registrati. Non valida le successive modifiche Camera e interfaccia. |
| 8 ottobre, revisione inglese con Info / Controls | L'utente conferma il funzionamento del codice nel gioco. | Conferma funzionale generale; SHA importato, durata e metriche native non registrati. La successiva disposizione dei comandi in `Subheader` non è ancora stata provata. |
| 27 settembre, PR #80 | L'utente conferma il recupero dal punto nel vuoto prima problematico e la resurrezione sul terreno. | Altre mappe e combinazioni richiedono prove dedicate. |
| 29 settembre, `68cbc832` / PR #81 | 591 test e 9 controlli GitHub superati; modello idle con 1 umano + 2 dummy + 2 AI: 355 → 70 chiamate complessive/s alle routine delle cinque entità. | Numero di chiamate, non consumo del server. |
| 30 settembre, riscontro utente dopo PR #81 | Il server sembra molto più stabile; l'utente prevede test più aggressivi. | Non sono stati forniti durata, configurazione completa o metriche di questo riscontro. |
| 2 ottobre, PR #85–86 | L'utente conferma il funzionamento di Multijump, Fly e tinte menu; 671 test e nove controlli GitHub superati. | Conferma funzionale, senza nuove misure di carico o durata. |
| 3 ottobre, riscontro utente su main dopo PR #88 | Dopo vari test, il server sembra stabile. | Durata, numero di player e metriche non specificati; le modifiche del 4 ottobre richiedono verifica nel client. |
| 4 ottobre, riscontro utente su PR #89 | Super Punch non produce sempre KO immediato; icone nel fascio bianche. | Correzioni nel sorgente corrente, ancora da confermare nel client. |
| 4 ottobre, `2e1c4ff` / PR #90 | Screenshot della diagnostica: 36.381 elementi, regola più grande 130 KB. | Entrambi oltre i limiti nativi; i controlli offline di quella revisione non lo avevano rilevato. |
| 4 ottobre, riscontro utente dopo PR #91 | L'utente conferma che le funzioni funzionano, ma nota pause nel movimento delle icone. | Rinnovo anticipato nel sorgente corrente; resa visiva da ricontrollare nel client. Nessun nuovo conteggio compilato fornito. |
| 4 ottobre, `9572d1` / PR #92 | L'utente conferma il funzionamento dopo Superman Punch a menu aperto e rinnovo anticipato delle icone. | Conferma funzionale generale, senza metriche native o nuova prova di durata; il raggio di 10 m è una modifica successiva. |

Il sorgente corrente compatta il blocco delle icone e aggiunge un budget strutturale preventivo. La modalità si chiama Cozywatch; il Light Shaft è rimosso e le icone hanno raggio fisso di 10 m. Prima di una nuova prova di carico, reimportarlo in una lobby nuova e registrare **Element Count e Largest Rule**: la stima offline e i byte del testo non sono queste due misure native.

Il funzionamento della revisione inglese con Info / Controls ha un riscontro positivo dell'utente. La nuova anteprima Info, con binding nel corpo e sottotitolo vuoto, richiede una prova dedicata nel client; il riscontro precedente non la comprende. Per Camera dopo Travel/cambio eroe, durata e carico restano utili le prove specifiche della matrice seguente: la conferma generale non ne registra separatamente gli esiti.

## Preparazione

Il clipboard corrente viene generato dalla specifica comportamentale. Importare soltanto `workshop/ruang_irama.en-US.workshop`: i test dei vecchi contratti sulla specifica non certificano il nuovo contesto di esecuzione.

Per il runtime globale iniziare con una lobby nuova, un umano e dummy presenti: primo cambio diretto 1→2, poi 2→1 senza usare menu. Confrontare il percorso via spettatori; ripetere ingresso/uscita e cambi rapidi con 12 umani. Provare Melee/Interact tenuti 0,5 s e i comandi simultanei: timer, testi e colori devono restare individuali. Verificare Revenge dopo KO nemici/alleati, morte e rinascita rapida, cambio eroe durante un evento pendente, e la pulizia dopo uscita e riuso dello stesso slot.

Usare una nuova lobby sulla build corrente del client, lingua testo English, Schermaglia e mappe standard escluse quelle Workshop. Importare il [file completo](../workshop/ruang_irama.en-US.workshop), annotando SHA e metriche di compilazione. Le mappe appartengono al preset della lobby.

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

Con 12 umani, menu chiusi e nessun overlay temporaneo, il baseline previsto è 18 HUD: sei fissi più una riga Player Vibes per umano. I menu si aprono alla registrazione: chiuderli prima di misurare questo baseline. Le icone e gli In-World Text vanno confrontati separatamente.

## Regressioni da provare

### Input, menu e HUD

- Percorrere tutte le 16 voci del principale inglese: Info / Controls 0, Name Color 1, Camera 2, Soundtrack 3, poi le funzioni 4–15. Per quelle con opzioni aprire il sottomenu, applicare, tornare e riaprire. Percorrere `15→0→1→2→3→4` e l'inverso. Navigare nella stessa pagina non deve creare altri HUD.
- Al primo spawn il principale deve aprirsi una sola volta su Info / Controls, senza entrare automaticamente nel sottomenu. Con il cursore principale su 0, verificare `Subheader` vuoto e i binding dinamici nel corpo della preview (`Text`): Camera, Arcade, ispezione eroe/HP, navigazione, apertura della guida e ritorno. Provare Interact tenuto 0,5 s con Crouch rilasciato, Melee tenuto 0,5 s e ispezione con Crouch a menu chiuso e Travel OFF. Crouch + Interact apre Info; Crouch + Reload torna al principale. Il sottomenu Info mantiene tutti i comandi in `Text` e `Subheader` vuoto. Con le altre voci principali selezionate e negli altri sottomenu, verificare comandi contestuali in `Subheader` e funzioni/opzioni in `Text`, senza troncamenti o sovrapposizioni. Nessun vecchio promemoria fisso agli angoli.
- Chiudere o cambiare pagina e poi morire/cambiare eroe: non riaprire Info né azzerare pagina/cursore. Cambio squadra e uscita/rientro devono invece ripristinare i default e aprire il principale su Info. Provare registrazioni simultanee e doppie notifiche di ingresso.
- Sulle voci principali 8, 9, 12 e 15, Crouch + Interact alterna subito lo stato senza aprire sottomenu: stesso cursore e HUD, stato aggiornato in inglese. Tenere premuto non ripete; rilascio e nuova pressione alternano di nuovo. Primary/Secondary navigano normalmente verso le altre voci. Provare player simultanei, Dummy Follow senza dummy avversario e OFF automatico alla sua scomparsa.
- Verificare Crouch come modificatore menu, hold Melee/Interact di 0,5 s, salto musica ±10 e wrap. Melee e Jump restano nativi da vivi.
- Tenere Interact e cambiare soltanto Crouch: menu e Camera non possono riutilizzare la stessa pressione. Serve rilasciare Interact.
- Da morto il menu resta visibile ma congelato; Jump funziona anche con menu, Camera o Luck precedentemente attivi.
- Controllare binding dinamici, righe inglesi leggibili, un unico Player Vibes, Host nel campo Text con spazio sopra/sotto e RGB del titolo; niente `0` diagnostico o sovrapposizioni con HUD nativi. L'HUD Top 1 deve mostrare esattamente `cozywatch.org`; nessuna impostazione, voce menu o etichetta per lingua/località deve rimanere.
- Diagnostica OFF/ON: testo sempre bianco solo per l'host, anche con Name Color e menu di colori diversi. Provare ingressi, uscite e cambio dell'ultima riga; nessuno `0` o righe fantasma quando nascosta. Verificare la leggibilità del campo Text, senza nuovi handle.
- Il profilo `งูแรร์` parte Charcoal / Poison 2 modificabili e Draconian fisso; il Soundtrack resta in sola lettura senza aggiungere un genere al catalogo globale.
- Sull'obiettivo devono apparire solo le icone, senza Light Shaft né nomi: raggio fisso di 10 m con 1/6/12 umani. AI e dummy non ne creano. Le icone conservano il colore esatto del proprietario anche quando cambia l'host; NONE non crea simboli.
- Le icone devono muoversi senza pause fra percorsi, anche con aggiornamenti leggermente sfalsati rispetto al secondo. Il rinnovo anticipato non deve spostarle istantaneamente. Devono restare entro il raggio di 10 m anche quando escono player e non accumularsi dopo 50 ricambi/cambi squadra. Provare NONE→icona→NONE, duplicati della stessa icona con colori diversi e obiettivo non visibile/assente. Create Icon aumenta al massimo di un'entità per umano con icona; IWT non cambia. Provare cambi colore senza ricreazioni, cambi tipo senza doppioni e traiettorie fino a 8 m sopra l'obiettivo. Il Chase del vecchio proprietario deve fermarsi al cleanup; il nuovo occupante non deve ereditare movimento o handle.
- Soundtrack, pagina 3: 200 generi, venti per gruppo, titoli inglesi, wrap 1↔200 e ±10 ai confini. Name Color, pagina 1: 40 colori, wrap 1↔40, ordine bianco → grigi → nero → colori caldi → rosa → viola → blu → verdi; etichette inglesi allineate ai colori, Black nero anche nella preview. Menu 0–15: stessa tinta tra preview e sottomenu. Tinte fluide in 0,180 s, senza pulsazioni all'apertura, applicazione o revoca Camera/Revenge.

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
- Con Camera attiva provare ciascun Travel riuscito verso spawn, obiettivo e player/bot: nessuna visuale bloccata nella vecchia posizione, stessa modalità e bersaglio valido dopo il reset. Provare Camera OFF, destinazione assente/non sicura e target invalidato al click: nessuna attivazione o riattivazione indesiderata. Ripetere rapidamente e con due giocatori indipendenti.
- Cambiare il proprio eroe con Camera personale e watch attive: visuale riagganciata al nuovo eroe e modalità/bersaglio validi conservati. Con Camera OFF deve restare OFF. Provare cambio eroe del bersaglio osservato, morte/respawn, Privacy e cambio squadra durante il refresh: una revoca deve prevalere, senza riavviare una Camera non valida.
- Verificare la revoca al cambio squadra anche con lo stesso eroe e prima della morte/respawn del target.
- Privacy ON esclude Camera, inspection, Teleport e Attach. Vision ignora intenzionalmente Privacy, ma elimina le targhette Crouch concorrenti.
- Provare tutte le 5 pagine Travel, navigazione senza esecuzione, esecuzione solo con Interact, binding reali e Self Elimination con cooldown per-player 3 s.
- Travel: verificare esattamente cinque pagine in inglese, incluso il passaggio 5→1 e 1→5. Spawn e Objective esplicitano il teletrasporto; Interact tenuto non deve ripetere alcuna azione. Forward non deve comparire né muovere il player. Provare un cambio squadra in una lobby nuova con un umano, chiudendo il principale iniziale, poi cambi ripetuti con dummy, menu, Attach e Superman Punch. Al cambio squadra Punch deve tornare OFF; la fase globale di cleanup deve fermare il Chase e rimuovere l'icona personale prima della nuova registrazione. Anche il profilo thailandese ha un'icona di default senza uso dei menu. Provare due player: l'icona del superstite deve continuare. Il crash storico non è riproducibile dal modello offline: ripetere la regressione nel client della revisione esatta.
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
- Superman Punch OFF: melee nativo. ON: provare nemici e compagni davanti, bersagli laterali vicini, fuori portata e dietro un muro; un solo bersaglio per attacco. Unkillable 1 HP/FULL HP deve proteggerli. Provare anche Junker Queen e gli eroi con melee diverso; non basta tenere Melee se l'attacco non viene realmente eseguito.
- Superman Punch: provare un melee breve e un bersaglio che entra in portata durante l'animazione, anche con menu principale, sottomenu e tutte le cinque pagine Travel aperte usando Crouch + Melee; nessun ritardo fisso. Un proiettile arrivato mentre si usa melee non deve diventare KO. Provare nemici anche fra campioni dell'animazione e Unkillable con menu aperto. Melee tenuto 0,5 s conserva il comando Arcade e richiede rilascio per riarmarsi.
- Con Superman Punch, uccidere un umano alleato e verificare un solo debito Revenge, poi riscattarlo. Provare menu aperto, Travel, morte, attivazione con Melee già tenuto, cambio squadra e riuso slot: nessun colpo vecchio o preferenza ereditata. Controllare il de-mech di D.Va separatamente dalla morte completa.

### Lifecycle e accumulo

- Restare alla scelta iniziale senza eroe per 60 s: Shion al successivo controllo 1 Hz, poi scelta libera di un altro eroe. Scegliere prima della scadenza deve annullare l'assegnazione; provare due ingressi distanziati, uscita/rientro, cambio squadra prima della scelta e presenza di dummy/AI.
- Dopo il primo spawn, morire o cambiare squadra/eroe e restare nella selezione oltre 60 s: nessuna nuova assegnazione automatica. Spettatori esclusi; verificare nel client l'assegnazione iniziale e il rilascio immediato della selezione forzata.
- Cambiare squadra subito dopo l'ingresso senza menu né icone, dopo alcuni minuti, con menu aperto e mentre altri osservano o hanno Camera/Vote aperti. Includere doppi cambi rapidi e uscite durante la quarantena e fra le due scadenze di 0,05 s del lifecycle globale. Il player deve tornare ai default una volta sola; gli HUD degli altri devono restare validi. Ripetere con 12 player in coda, controllando che la registrazione prosegua e gli slot vengano liberati. I test offline verificano annullamento e ordine delle fasi senza sospendere subroutine; non riproducono il crash nativo.
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
- Con il solo dummy della squadra 1, solo la squadra 2 può attivare Follow; ripetere invertendo i team. Senza dummy ON è bloccato, OFF resta disponibile. Con menu chiuso, rimuovere il dummy avversario: stato OFF entro un secondo; quando ritorna serve un nuovo Interact. Rimuovere il dummy dopo aver aperto il menu e verificare disponibilità e feedback inglesi senza un'errata conferma di attivazione.
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
