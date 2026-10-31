# Cozywatch — Nocturne

Modalità sociale per Overwatch 2: **Schermaglia, 6v6, fino a 12 giocatori contemporanei**, con menu personali, Souls & Echoes, Camera, Travel, Ghost/Fly e Try Your Luck. I 12 slot vengono riutilizzati quando qualcuno esce: non c'è un limite di 12 registrazioni nell'intera lobby.

Il tema **Nocturne** si ispira al romanticismo oscuro e al melodic death metal: argento lunare, malva, rosa cenere e toni osso accompagnano testi di cappelle silenziose, elegie ed echi. La [palette dei 40 Name Color](docs/NAME_COLORS.md) usa nomi a tema e 34 valori RGB rivisti verso tinte più attenuate; nome, preview e icona mantengono sempre il colore esatto selezionato.

**[Apri il codice da importare](workshop/ruang_irama.en-US.workshop)** · [Istruzioni di importazione](docs/IMPORTAZIONE.md)

Imposta la lingua testo del client su **English** per importare il codice. **Grammatica Workshop, identificatori, regole, commenti, menu, HUD, messaggi e impostazioni personalizzate sono in inglese**. Le mappe si configurano nella lobby: tutte quelle standard disponibili in Schermaglia, escluse le mappe Workshop come Isola.

Le 136 regole del file da importare sono numerate consecutivamente da **0 a 135**, nell'ordine in cui compaiono, senza numeri ripetuti o suffissi alfabetici.

## Stato attuale

Il codice corrente aggiunge quattro menu Nocturne: **Presence 17**, **Fates 18**, **Whispers 19** e **Moonlit Aura 20**. Include la correzione del passaggio visibile a Moonlit Aura tornando al principale con Reload, il risultato Fates in un HUD privato sotto Arcade e Whispers senza limite di distanza. Sono modifiche successive al pacchetto pubblicato 0.8.3, elencate in **Unreleased** nel changelog e ancora da verificare nel client. Il tag e l'allegato v0.8.3 conservano il codice della release.

Il 28 ottobre, dopo la PR #114, l'utente ha confermato: «funziona tutto». È un riscontro qualitativo generale sulla revisione provata: SHA importato, build client, durata, numero di player e metriche native non sono stati forniti. La successiva correzione dell'inerzia Ghost richiede una nuova prova nel client. Restano i riscontri storici sul menu 2 dopo la PR #103 e sulla distanza tra HOST e killfeed dopo la PR #105.

Il file da importare esegue comandi, HUD, fisica e pulizia nel contesto globale, senza regole `Ongoing - Each Player`. Gli eventi nativi registrano soltanto il lavoro da elaborare; timer e stato individuali separano sospensione, pulizia e nuova registrazione. Le preferenze restano personali.

Il codice corrente usa **30.262 unità strutturali stimate**, massimo per regola 2.789 e 325.518 byte UTF-8 di testo da importare; il pacchetto pubblicato 0.8.3 usava 27.496 unità, massimo 2.605 e 299.838 byte. I dettagli sono nei [controlli automatici](docs/VALIDAZIONE.md). Sono misure offline; gli elementi compilati e il carico del server si misurano nel gioco. Il riscontro generale dopo la PR #114 non registra le singole prove visive del tema o i nuovi menu sociali.

Il 3 ottobre 2026 l'utente ha riferito stabilità dopo vari test. Il 4 ottobre la diagnostica della revisione `2e1c4ff` ha mostrato **36.381 elementi e una regola da 130 KB**, oltre i limiti del gioco. Il sorgente corrente compatta le formule duplicate delle icone, rimuove il Light Shaft e aggiunge un budget strutturale offline al preflight. Le 36 scelte delle icone restano disponibili, entro 5 m tridimensionali dal proprietario e indipendenti dall’obiettivo. I controlli automatici verificano codice e flussi simulati; il nuovo conteggio compilato richiede un'importazione nel client.

La versione in [VERSION](VERSION) è **0.8.3**; la [release 0.8.3](https://github.com/skelos95/ruang-irama-workshop/releases/tag/v0.8.3) e il tag v0.8.3 identificano il commit del pacchetto. Riunisce gli aggiornamenti successivi alla [release storica 0.8.2](https://github.com/skelos95/ruang-irama-workshop/releases/tag/v0.8.2): tema Nocturne e 40 Name Color, titolo e RGB originali, Info bianca, correzioni HOST/Travel/lifecycle, Movement con passi 20/100, reset personali, icone entro 5 m, Dummy Target fermo e conservazione dell'inerzia quando si applica Ghost. Il tag e l'allegato 0.8.2 conservano il contenuto pubblicato. Per confrontare due prove usa il commit del codice importato. [Storia delle modifiche](CHANGELOG.md) · [Procedura di test](docs/TEST.md)

## Avvio rapido

1. Salva il preset della lobby, imposta la lingua testo del client su English e scegli Schermaglia e le mappe desiderate.
2. Apri il codice qui sopra, scegli **Raw** e copia tutto nelle regole Workshop.
3. Nelle impostazioni Workshop scegli durata **30–60 minuti** (default **30**) e diagnostica host, se necessaria.
4. Avvia una nuova lobby. Al primo spawn si apre il menu principale sulla voce **Info / Controls**, con i comandi principali già nel sottotitolo; tieni Crouch e premi Interact per aprire la guida completa. Allo zero del countdown la partita si riavvia.

Il file contiene le regole, non il preset delle mappe. Il titolo centrale mostra **cozywatch.org [countdown]**. Il roster si intitola **SOULS & ECHOES** e il leader dei voti **CROWN OF ASH**. Il benvenuto è «Enter the Nocturne. Where sorrow becomes melody.». Il sottotitolo separato del sito e il precedente sistema Server Location sono rimossi.

Chi resta senza eroe alla scelta iniziale riceve **Shion dopo 60 secondi**, al successivo controllo di un secondo. Poi può cambiare eroe liberamente; il timer non riparte dopo morti o cambi squadra.

## Comandi

| Contesto | Comando | Azione |
|---|---|---|
| Vivo | Melee tenuto 0,5 s | Apre/chiude Arcade |
| Menu con elenco | Crouch + Primary / Secondary | Voce successiva / precedente |
| Menu aperto | Crouch + Interact | Apre/applica; nel principale alterna ON/OFF per le voci 8, 9, 12 e 15 |
| Sottomenu | Crouch + Reload | Torna al menu principale |
| Voce principale selezionata o relativo sottomenu, dove indicato | Crouch + Ultimate | Ripristina i default della sola pagina |
| Soundtrack | Crouch + Ability 1 / 2 | Salta avanti / indietro di 10 generi |
| Crouch rilasciato | Interact tenuto 0,5 s | Alterna Camera, anche con menu aperto |
| Arcade chiuso, Travel OFF o pagine Travel Player/Bot / Attach | Crouch tenuto | Inspection: eroe e HP del bersaglio |
| Menu chiuso, Travel ON | Crouch tenuto | Travel & Attach |
| Travel & Attach | Crouch + Primary / Secondary, poi Interact | Cambia pagina, poi esegue |
| Attaccato, menu chiuso | Crouch + Reload | Sgancia |
| Morto | Jump | Resuscita sul posto sicuro o recupera dal vuoto |
| Vivo, Multijump ON | Premi o tieni Jump in aria, anche con menu aperto | Salti aggiuntivi con la forza scelta |
| Vivo, Superman Punch ON | Attacco melee, anche con menu aperto | KO ravvicinato, anche sui compagni; rispetta Unkillable |

Ogni pressione dei comandi menu viene consumata una volta; Interact va rilasciato prima di passare da menu a Camera. Da morto il menu resta visibile ma non accetta comandi. Melee resta nativo; con Multijump OFF anche Jump resta nativo da vivi.

Quando Info / Controls 0 è selezionata nel principale, titolo e anteprima sono interamente nel sottotitolo dell'HUD (`Subheader`), per una visualizzazione più piccola; il corpo (`Text`) è vuoto. I binding del giocatore mostrano Interact tenuto 0,5 s con Crouch rilasciato per Camera, Melee tenuto 0,5 s per Arcade, Crouch con Arcade chiuso e Travel OFF, oppure nelle pagine Teleport Player/Bot e Attach per vedere eroe e HP. Sono inclusi Crouch + Primary / Secondary per navigare, Crouch + Interact per aprire tutti i comandi e Crouch + Reload per tornare dal sottomenu. Anche il sottomenu Info mantiene titolo e guida completa nel `Subheader`, con la guida completa e i binding dinamici, senza duplicazioni. Le altre voci e pagine conservano comandi contestuali nel sottotitolo e funzioni/opzioni nel corpo. Ogni pagina usa un solo HUD Arcade; i due promemoria fissi agli angoli dello schermo sono rimossi.

HOST compare in una sola riga a destra, senza spazio sopra e con una riga vuota sotto per distanziarlo dal killfeed. Icona e nome seguono l'host corrente; la riga si svuota quando l'host è assente.

## Menu personali

| Pagina | Menu | Opzioni |
|---:|---|---|
| 0 | Info / Controls | Guida completa ai comandi |
| 1 | Name Color | 40 colori |
| 2 | Third-Person Camera | OFF, sé stesso o target valido |
| 3 | Soundtrack | [200 generi](docs/GENERI.md) |
| 4 | Revenge | Debiti da uccisioni dirette |
| 5 | Unkillable | OFF / 1 HP curabile / FULL HP |
| 6 | Hero Voice | 5 preset |
| 7 | Player Icon | Nessuna + 36 icone |
| 8 | Crouch: Teleport / Attach / Self Kill | ON/OFF dal menu principale; 5 pagine Travel |
| 9 | Crouch Privacy | ON/OFF dal menu principale |
| 10 | Try Your Luck | Vision, Acceleration, Skull, Team Heal, Burning, Hacked |
| 11 | Vote Player | Umani, incluso sé stesso |
| 12 | Dummy Target | ON/OFF dal principale: consente al dummy nemico fermo di guardarti |
| 13 | Ghost Mode / Fly | Due interruttori indipendenti, inizialmente OFF |
| 14 | Multijump | OFF oppure forza fissa 100–1000%, passi del 100% |
| 15 | Superman Punch | ON/OFF dal menu principale |
| 16 | Movement / Gravity | Velocità 20–1000% e gravità 0–500%, passi di 20 sotto 100 e di 100 sopra |
| 17 | Presence | Unspoken, Seeking company, Listening in silence, Lost in thought, Away beyond the veil |
| 18 | Fates | Moneta Moon/Ash, d6, d20, percentuale e sei presagi |
| 19 | Whispers | Ricezione ON/OFF e cinque messaggi personali predefiniti |
| 20 | Moonlit Aura | OFF, Moonlit Ring, Withered Halo, Veil of Ash; filtro personale delle aure altrui |

Il ripristino con **Crouch + Ultimate** agisce sulla voce selezionata nel principale o sul relativo sottomenu e compare nell’aiuto soltanto dove disponibile. Richiede un giocatore vivo e applica una sola azione per pressione: Ultimate va rilasciato prima di un nuovo reset. Non modifica le preferenze degli altri.

| Pagina | Default ripristinati |
|---|---|
| 1 — Name Color | Moon White; Charcoal per il profilo speciale |
| 2 — Camera | OFF |
| 3 — Soundtrack | Nessuna selezione, cursore al primo genere; Draconian bloccato escluso |
| 5 — Unkillable | OFF |
| 6 — Hero Voice | NORMAL |
| 7 — Icon | NONE; Poison 2 per il profilo speciale |
| 11 — Vote Player | Annulla soltanto il proprio voto |
| 13 — Ghost / Fly | Entrambi OFF |
| 14 — Multijump | OFF, livello 1 |
| 16 — Movement / Gravity | Entrambi 100%, cursore Speed |
| 17 — Presence | Unspoken |
| 18 — Fates | Prima scelta e risultato temporaneo rimosso; cooldown conservato |
| 19 — Whispers | Ricezione ON, cursore sulla ricezione; cooldown conservato |
| 20 — Moonlit Aura | Aura OFF, filtro delle aure altrui OFF |

Info, Revenge, Luck e i toggle 8, 9, 12 e 15 non offrono questo reset. Il reset non cambia pagina né chiude il menu.

Presence aggiunge uno stato alla propria riga **Souls & Echoes**, senza creare una targhetta sopra al personaggio. `Unspoken` è il default e non aggiunge testo. Tutti gli stati, compreso `Away beyond the veil`, sono scelte manuali: non rilevano automaticamente l'inattività e non modificano movimento, protezioni o Privacy.

Fates mostra risultati soltanto al proprietario: **Moon/Ash**, d6, d20, percentuale intera **1–100%** o uno dei sei presagi a tema. Un HUD privato sotto Arcade mostra il risultato acquisito al tiro, con una riga vuota prima del testo: dura **3 secondi**, con rimozione al controllo successivo di un secondo, quindi entro **4 secondi**. Il menu mostra soltanto lo stato **READY** o **RESTING Xs**, senza ripetere il risultato. Ogni esecuzione richiede **5 secondi** prima della successiva; il reset pulisce scelta e risultato temporaneo senza annullare l'attesa. Sono risposte cosmetiche, senza gli effetti fisici di Try Your Luck.

Whispers offre **Greeting, Respect, Rose, Embrace e Resonance**, oltre alla ricezione inizialmente **ON**. Per inviare, mirare a un altro umano vivo e disponibile, entro un angolo di **12°** e con linea di vista libera, poi applicare il messaggio. **La distanza non limita l'invio.** Crouch Privacy e ricezione OFF del destinatario bloccano l'invio. Il destinatario riceve il testo e il mittente una conferma; nessun altro riceve messaggi. Ogni invio riuscito avvia un cooldown personale di **15 secondi**, conservato dal reset. Non è chat libera e non modifica il microfono o le animazioni.

Moonlit Aura offre **Moonlit Ring, Withered Halo e Veil of Ash**, inizialmente OFF. Ogni umano può avere un solo effetto personale, con il proprio Name Color esatto e la posizione legata al proprietario: al massimo **12 aure**. Il filtro **Hide other auras** nasconde soltanto le aure altrui sul proprio schermo, lasciando visibile la propria e conservando le preferenze degli altri. Morte e perdita dello spawn nascondono e rimuovono l'effetto conservando la scelta; alla rinascita l'aura torna al successivo controllo di un secondo. Un cambio colore nasconde subito la vecchia tinta e ricrea l'effetto entro lo stesso intervallo. Il reset spegne la propria aura e disattiva il filtro. Le preferenze dei quattro menu persistono tra morte e cambio eroe; cambio squadra e uscita/rientro ripristinano i default.

Travel contiene cinque pagine: Teleport Spawn, Teleport Objective, Teleport Player/Bot, Attach e Self Elimination. Interact esegue una sola azione per pressione; Primary e Secondary scorrono le cinque pagine in entrambe le direzioni. Input, navigazione e applicazione richiedono un giocatore vivo e spawnato; alla morte o alla perdita dello spawn la chiusura e la pulizia restano attive.

Un teletrasporto Travel riuscito chiude anche lo stato Attach del proprietario: Multijump può riprendere e il controllo delle catene non conserva il vecchio collegamento. Se la destinazione viene rifiutata o il giocatore è già nello spawn, l'aggancio resta attivo.

Nel menu 2 ogni applicazione di Your Hero o di un bersaglio valido ferma e ricrea la Camera, anche se la stessa scelta era già attiva. Camera OFF ferma sempre la camera nativa. La Camera attiva viene riavviata dopo un teletrasporto Travel riuscito e al cambio del proprio eroe, conservando modalità e bersaglio valido. Un bersaglio morto, uscito, privato o in transizione viene invece revocato; le Camera degli altri giocatori restano indipendenti.

Il menu 16 modifica due valori personali, inizialmente al **100%**. Tieni Crouch e premi Interact per scegliere Speed o Gravity; Primary / Secondary aumentano o diminuiscono subito il valore: passi di **20 punti percentuali sotto il 100%**, di **100 sopra il 100%**. Il passaggio tra le fasce è `60 ↔ 80 ↔ 100 ↔ 200 ↔ 300`; al 100% Primary sale a 200 e Secondary scende a 80. La velocità va da **20% a 1000%**, la gravità da **0% a 500%**. Reload torna al principale. Crouch + Ultimate ripristina insieme Speed e Gravity al 100% e seleziona Speed. Le scelte restano dopo morte e cambio eroe e tornano al 100% dopo cambio squadra o uscita/rientro.

Ghost attraversa pareti e soffitti mantenendo il pavimento. Applicare o alternare Ghost aggiorna soltanto la collisione con l'ambiente e conserva l'inerzia, anche durante un salto o mentre Fly è attiva. Fly segue lo sguardo con avanti; indietro e laterali restano orizzontali. La velocità è fissa sul valore scelto nel menu 16: **100% equivale a 5,5 m/s**, senza accelerazione automatica. Con Fly attiva la gravità è sempre **0**; disattivandola torna al valore scelto nel menu 16. Luck Acceleration mantiene il suo effetto temporaneo e, alla fine, vengono ripristinate le impostazioni personali.

Multijump aggiunge salti in aria premendo Jump o tenendolo premuto: la ripetizione avviene ogni 0,3 s e il valore scelto resta fisso. Funziona anche con un menu aperto; si sospende con Attach, Fly o Luck Acceleration. La percentuale indica la spinta verticale del salto aggiuntivo, non l'altezza in metri. Ogni salto valido mostra un breve anello RGB arcobaleno sotto i piedi; i comandi dei menu non generano effetti visivi.

Superman Punch è inizialmente OFF e funziona anche con il menu principale, un sottomenu o Travel aperto, usando Melee. Durante un attacco melee cerca subito un bersaglio vicino davanti, anche della propria squadra, senza attraversare muri. Un impatto melee nativo sui nemici viene riconosciuto anche fra due aggiornamenti dell'animazione. Un solo contatto per attacco, rispettando Unkillable. Revenge registra anche queste uccisioni fra umani alleati. La preferenza si conserva dopo morte o cambio eroe e torna OFF al cambio squadra o all'uscita.

La diagnostica server rimane bianca ed è visibile solo all'host. Tutti i testi dell'interfaccia sono in inglese; il nome personale `งูแรร์` conserva i suoi caratteri originali.

Name Color ordina i [40 colori Nocturne](docs/NAME_COLORS.md) per sfumatura: bianco, grigi, nero, ori antichi, terre autunnali, rose appassite, viola crepuscolari, blu lunari e verdi muschio. Le scelte e gli indici restano 40; 34 valori RGB cambiano, mentre quelli degli indici interni 0–4 e 29 sono conservati. La pagina 1, il nome e l’icona mostrano esattamente il colore selezionato, inizialmente Moon White; Black usa nero puro anche nella preview. Charcoal resta all’indice 2 per il profilo speciale. Info / Controls 0 resta bianca sia nell’anteprima sia nella guida aperta con Interact: usa `Color(White)` direttamente, indipendente da Name Color, MenuColor e ciclo RGB, senza attendere la transizione del colore. Le altre pagine mescolano il 32% del Name Color scelto al 68% del proprio accento Nocturne, con transizioni fluide di 0,180 s; i sottotitoli usano un tono osso RGB (210, 200, 192) e Travel cinque tinte attenuate. Titolo, HOST, effetti Luck e anello Multijump condividono il ciclo RGB arcobaleno originale di 51 secondi.

Le icone native scelte dagli umani fluttuano attorno al **proprietario, sempre entro 5 m di distanza tridimensionale**, senza fascio luminoso né nomi. Seguono subito la sua posizione, anche dopo movimento o teletrasporto, e mantengono il suo Name Color esatto. L’offset casuale ha distanza orizzontale 0–4 m e altezza 0,5–3 m: anche la combinazione massima resta entro 5 m. Non richiedono un obiettivo disponibile. Il percorso successivo parte dalla posizione corrente prima che il precedente finisca, evitando pause fra gli aggiornamenti. Senza icona non compare alcun simbolo; ingressi, uscite e cambi squadra aggiornano e ripuliscono i 12 slot. Dummy e AI non creano icone. Nella lista Souls & Echoes le icone incorporate nel testo mantengono invece il bianco nativo; il Name Color si applica al testo della riga.

Privacy impedisce Camera, inspection, Teleport, Attach e Whispers verso il giocatore; l'effetto Vision di Try Your Luck mostra intenzionalmente anche i giocatori privati. Whispers ha inoltre un filtro di ricezione personale indipendente. Preferenze, pagina e cursore persistono tra morte e cambio eroe. **Cambio squadra e uscita/rientro ripartono dai default**, aprendo nuovamente il principale su Info / Controls al completamento della registrazione.

Privacy riguarda le funzioni personalizzate del Workshop: non limita la visuale spettatore o gli strumenti amministrativi nativi.

I dummy compaiono solo in Schermaglia, al massimo uno per squadra con almeno due slot liberi. Lasciano spazio quando la squadra si riempie. Dopo il teletrasporto iniziale verso un punto sicuro restano fermi, senza inseguire: guardano soltanto il nemico umano vivo più vicino con **Dummy Target ON**. La voce `12 - DUMMY TARGET` mostra `ENEMY DUMMY TARGETING: ON/OFF`; ON richiede un dummy avversario presente, OFF è sempre disponibile. Se il dummy avversario scompare, la preferenza torna OFF entro un secondo e richiede una nuova attivazione. Privacy conserva il proprio significato e non viene modificata da questo consenso. [Dettagli tecnici dei dummy](docs/PROGETTO.md#dummy-e-bot-normali)

Il nome visibile esatto `งูแรร์` riceve i default modificabili Charcoal / Poison 2 e il Vibes fisso `Draconian`. Il riconoscimento avviene per nome, quindi vale anche per un omonimo.

## Documentazione

| Documento | Quando serve |
|---|---|
| [Importazione](docs/IMPORTAZIONE.md) | Copia/incolla e problemi dell'editor |
| [Architettura](docs/PROGETTO.md) | Scheduler, risorse, lifecycle e interazioni |
| [Controlli automatici](docs/VALIDAZIONE.md) | Eseguire e comprendere la validazione |
| [Test nel gioco](docs/TEST.md) | Regressioni, carico e rapporto di prova |
| [Generi](docs/GENERI.md) | Catalogo musicale e gruppi in inglese |
| [Name Color](docs/NAME_COLORS.md) | I 40 nomi e valori RGB/HEX della palette Nocturne |
| [Changelog](CHANGELOG.md) | Evoluzione e correzioni storiche |
