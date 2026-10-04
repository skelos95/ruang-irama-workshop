# Cozywatch

Modalità sociale per Overwatch 2: **Schermaglia, 6v6, fino a 12 giocatori contemporanei**, con menu personali, Player Vibes, Camera, Travel, Ghost/Fly e Try Your Luck. I 12 slot vengono riutilizzati quando qualcuno esce: non c'è un limite di 12 registrazioni nell'intera lobby.

**[Apri il codice da importare](workshop/ruang_irama.it-IT.workshop)** · [Istruzioni di importazione](docs/IMPORTAZIONE_ITALIANO.md)

Il client deve avere il testo in italiano; gli HUD possono essere scelti in **English, Bahasa Indonesia e ไทย** da ciascun giocatore. Le mappe si configurano nella lobby: tutte quelle standard disponibili in Schermaglia, escluse le mappe Workshop come Isola.

## Stato attuale

Il 3 ottobre 2026 l'utente ha riferito stabilità dopo vari test. Il 4 ottobre la diagnostica della revisione `2e1c4ff` ha mostrato **36.381 elementi e una regola da 130 KB**, oltre i limiti del gioco. Il sorgente corrente compatta le formule duplicate delle icone, rimuove il Light Shaft e aggiunge un budget strutturale offline al preflight. Le 36 scelte delle icone restano disponibili, ora entro un raggio fisso di 5 m sull'obiettivo. I controlli automatici verificano codice e flussi simulati; il nuovo conteggio compilato richiede un'importazione nel client.

La versione nominale in [VERSION](VERSION) resta `0.8.1`; il tag storico e il contenuto corrente di `main` sono revisioni diverse. Per confrontare due prove usa il commit del codice importato. [Storia delle modifiche](CHANGELOG.md) · [Procedura di test](docs/TEST.md)

## Avvio rapido

1. Salva il preset della lobby e imposta Schermaglia e le mappe desiderate.
2. Apri il codice qui sopra, scegli **Raw** e copia tutto nelle regole Workshop.
3. Nelle impostazioni Workshop scegli durata **10–60 minuti** (default **30**), località mostrata nell'HUD (default Indonesia) e diagnostica host, se necessaria.
4. Avvia una nuova lobby. Allo zero del countdown la partita si riavvia.

Il file contiene le regole, non il preset delle mappe. La località è un'etichetta dell'HUD e non cambia la regione di hosting.

Chi resta senza eroe alla scelta iniziale riceve **Shion dopo 60 secondi**, al successivo controllo di un secondo. Poi può cambiare eroe liberamente; il timer non riparte dopo morti o cambi squadra.

## Comandi

| Contesto | Comando | Azione |
|---|---|---|
| Vivo | Melee tenuto 0,5 s | Apre/chiude Arcade |
| Menu con elenco | Crouch + Primary / Secondary | Voce successiva / precedente |
| Menu aperto | Crouch + Interact | Entra o applica |
| Sottomenu | Crouch + Reload | Torna al menu principale |
| Soundtrack | Crouch + Ability 1 / 2 | Salta avanti / indietro di 10 generi |
| Crouch rilasciato | Interact tenuto 0,5 s | Alterna Camera, anche con menu aperto |
| Menu chiuso | Crouch tenuto | Inspection e, se abilitato, Travel & Attach |
| Travel & Attach | Crouch + Primary / Secondary, poi Interact | Cambia pagina, poi esegue |
| Attaccato, menu chiuso | Crouch + Reload | Sgancia |
| Morto | Jump | Resuscita sul posto sicuro o recupera dal vuoto |
| Vivo, Multijump ON | Premi o tieni Jump in aria, anche con menu aperto | Salti aggiuntivi con la forza scelta |
| Vivo, Superman Punch ON | Attacco melee, anche con menu aperto | KO ravvicinato, anche sui compagni; rispetta Unkillable |

Ogni pressione dei comandi menu viene consumata una volta; Interact va rilasciato prima di passare da menu a Camera. Da morto il menu resta visibile ma non accetta comandi. Melee resta nativo; con Multijump OFF anche Jump resta nativo da vivi.

## Menu personali

| Pagina | Menu | Opzioni |
|---:|---|---|
| 0 | Name Color | 40 colori |
| 1 | Third-Person Camera | OFF, sé stesso o target valido |
| 2 | Soundtrack | [200 generi](docs/GENERI.md) |
| 3 | HUD Language | EN / ID / TH |
| 4 | Revenge | Debiti da uccisioni dirette |
| 5 | Unkillable | OFF / 1 HP curabile / FULL HP |
| 6 | Hero Voice | 5 preset |
| 7 | Player Icon | Nessuna + 36 icone |
| 8 | Crouch Travel & Attach | Interact alterna OFF / ON; Travel conserva 5 pagine |
| 9 | Crouch Privacy | Interact alterna OFF / ON |
| 10 | Try Your Luck | Vision, Acceleration, Skull, Team Heal, Burning, Hacked |
| 11 | Vote Player | Umani, incluso sé stesso |
| 12 | Dummy Follow | Interact alterna OFF / ON, con dummy avversario presente |
| 13 | Ghost Mode / Fly | Due interruttori indipendenti, inizialmente OFF |
| 14 | Multijump | OFF oppure forza fissa 100–1000%, passi del 100% |
| 15 | Superman Punch | Interact alterna OFF / ON nella schermata della funzione |

Ghost attraversa pareti e soffitti mantenendo il pavimento. Fly segue lo sguardo con avanti; indietro e laterali restano orizzontali. Con input direzionale continuo accelera dal **100% al 1000% in 20 secondi**: cambiare direzione conserva la rampa, rilasciare del tutto il movimento la azzera.

Multijump aggiunge salti in aria premendo Jump o tenendolo premuto: la ripetizione avviene ogni 0,3 s e il valore scelto resta fisso. Funziona anche con un menu aperto; si sospende con Attach, Fly o Luck Acceleration. La percentuale indica la spinta verticale del salto aggiuntivo, non l'altezza in metri. Ogni salto valido mostra un breve anello RGB sotto i piedi; i comandi dei menu non generano effetti visivi.

Superman Punch è inizialmente OFF e funziona anche con il menu principale o un sottomenu aperto. Durante un attacco melee cerca subito un bersaglio vicino davanti, anche della propria squadra, senza attraversare muri. Un impatto melee nativo sui nemici viene riconosciuto anche fra due aggiornamenti dell'animazione. Un solo contatto per attacco, rispettando Unkillable. Revenge registra anche queste uccisioni fra umani alleati. La preferenza si conserva dopo morte o cambio eroe e torna OFF al cambio squadra o all'uscita.

La diagnostica server rimane bianca ed è visibile solo all'host. I testi dei menu EN/ID/TH mantengono comandi e stato con descrizioni più brevi.

Name Color ordina i 40 colori per sfumatura: bianco, grigi, nero, colori caldi, rosa, viola, blu e verdi. Black usa nero puro sia per il nome sia per la preview. Le tinte dei menu seguono la stessa progressione di accenti, mescolati al Name Color scelto, con transizioni fluide di 0,180 s; le funzioni mantengono le posizioni attuali.

Sull'obiettivo fluttuano solo le icone native scelte dagli umani, **entro un raggio fisso di 5 m**, senza fascio luminoso né nomi. Ciascuna segue il proprio Name Color esatto, con traiettorie casuali fino a **8 m sopra l'obiettivo**. Il percorso successivo parte dalla posizione corrente prima che il precedente finisca, evitando pause fra gli aggiornamenti. Senza icona non compare alcun simbolo; ingressi, uscite e cambi squadra aggiornano e ripuliscono i 12 slot. Dummy e AI non creano icone. Nella lista Player Vibes le icone incorporate nel testo mantengono invece il bianco nativo; il Name Color si applica al testo della riga.

Privacy impedisce Camera, inspection, Teleport e Attach verso il giocatore; l'effetto Vision di Try Your Luck mostra intenzionalmente anche i giocatori privati. Preferenze e cursori persistono tra chiusura menu, morte e cambio eroe; **cambio squadra e uscita/rientro ripartono dai default**.

Privacy riguarda le funzioni personalizzate del Workshop: non limita la visuale spettatore o gli strumenti amministrativi nativi.

I dummy compaiono solo in Schermaglia, al massimo uno per squadra con almeno due slot liberi. Lasciano spazio quando la squadra si riempie; seguono solo il nemico vivo più vicino con Dummy Follow ON, fermandosi a 4 m. Follow si può attivare solo con un dummy nella squadra avversaria; si può sempre disattivare. Se il dummy avversario scompare, Follow torna OFF entro il successivo controllo di un secondo e richiede una nuova attivazione. [Dettagli tecnici dei dummy](docs/PROGETTO.md#dummy-e-bot-normali)

Il nome visibile esatto `งูแรร์` riceve i default modificabili Charcoal / Poison 2 e il Vibes fisso `Draconian`. Il riconoscimento avviene per nome, quindi vale anche per un omonimo.

## Documentazione

| Documento | Quando serve |
|---|---|
| [Importazione](docs/IMPORTAZIONE_ITALIANO.md) | Copia/incolla e problemi dell'editor |
| [Architettura](docs/PROGETTO.md) | Scheduler, risorse, lifecycle e interazioni |
| [Controlli automatici](docs/VALIDAZIONE.md) | Eseguire e comprendere la validazione |
| [Test nel gioco](docs/TEST.md) | Regressioni, carico e rapporto di prova |
| [Generi](docs/GENERI.md) / [Località](docs/SERVER_LOCATIONS.md) | Cataloghi ordinati |
| [Changelog](CHANGELOG.md) | Evoluzione e correzioni storiche |
