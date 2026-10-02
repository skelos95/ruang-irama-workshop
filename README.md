# Ruang Irama — Server Khusus Chill

Modalità sociale per Overwatch 2: **Schermaglia, 6v6, fino a 12 giocatori contemporanei**, con menu personali, Player Vibes, Camera, Travel, Ghost/Fly e Try Your Luck. I 12 slot vengono riutilizzati quando qualcuno esce: non c'è un limite di 12 registrazioni nell'intera lobby.

**[Apri il codice da importare](workshop/ruang_irama.it-IT.workshop)** · [Istruzioni di importazione](docs/IMPORTAZIONE_ITALIANO.md)

Il client deve avere il testo in italiano; gli HUD possono essere scelti in **English, Bahasa Indonesia e ไทย** da ciascun giocatore. Le mappe si configurano nella lobby: tutte quelle standard disponibili in Schermaglia, escluse le mappe Workshop come Isola.

## Stato attuale

Il 30 settembre 2026 l'utente ha riferito una stabilità sensibilmente migliore dopo l'ottimizzazione dello scheduler; ulteriori stress test sono ancora previsti. La revisione funzionale `68cbc832` ha superato 591 test e tutti i controlli GitHub. Questi test verificano il codice e flussi simulati, senza eseguire il server Overwatch.

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
| Menu aperto | Crouch + Primary / Secondary | Voce successiva / precedente |
| Menu aperto | Crouch + Interact | Entra o applica |
| Sottomenu | Crouch + Reload | Torna al menu principale |
| Soundtrack | Crouch + Ability 1 / 2 | Salta avanti / indietro di 10 generi |
| Crouch rilasciato | Interact tenuto 0,5 s | Alterna Camera, anche con menu aperto |
| Menu chiuso | Crouch tenuto | Inspection e, se abilitato, Travel & Attach |
| Travel & Attach | Crouch + Primary / Secondary, poi Interact | Cambia pagina, poi esegue |
| Attaccato, menu chiuso | Crouch + Reload | Sgancia |
| Morto | Jump | Resuscita sul posto sicuro o recupera dal vuoto |

Ogni pressione viene consumata una volta; Interact va rilasciato prima di passare da menu a Camera. Da morto il menu resta visibile ma non accetta comandi. Melee e Jump restano disponibili come azioni native da vivi.

## Menu personali

| Pagina | Menu | Opzioni |
|---:|---|---|
| 0 | Name Color | 32 colori |
| 1 | Third-Person Camera | OFF, sé stesso o target valido |
| 2 | Soundtrack | [100 generi](docs/GENERI.md) |
| 3 | HUD Language | EN / ID / TH |
| 4 | Revenge | Debiti da uccisioni dirette |
| 5 | Unkillable | OFF / 1 HP curabile / FULL HP |
| 6 | Hero Voice | 5 preset |
| 7 | Player Icon | Nessuna + 36 icone |
| 8 | Crouch Travel & Attach | OFF / ON; 5 pagine, Self Elimination con cooldown 3 s |
| 9 | Crouch Privacy | OFF / ON |
| 10 | Try Your Luck | Vision, Acceleration, Skull, Team Heal, Burning, Hacked |
| 11 | Vote Player | Umani, incluso sé stesso |
| 12 | Dummy Follow | OFF / ON, partecipazione volontaria |
| 13 | Ghost Mode / Fly | Due interruttori indipendenti, inizialmente OFF |

Ghost attraversa pareti e soffitti mantenendo il pavimento. Fly segue lo sguardo con avanti; indietro e laterali restano orizzontali. Tenendo solo avanti accelera dal **100% al 1000% in 25 secondi**; cambiare input azzera la rampa.

Privacy impedisce Camera, inspection, Teleport e Attach verso il giocatore; l'effetto Vision di Try Your Luck mostra intenzionalmente anche i giocatori privati. Preferenze e cursori persistono tra chiusura menu, morte e cambio eroe; **cambio squadra e uscita/rientro ripartono dai default**.

Privacy riguarda le funzioni personalizzate del Workshop: non limita la visuale spettatore o gli strumenti amministrativi nativi.

I dummy compaiono solo in Schermaglia, al massimo uno per squadra con almeno due slot liberi. Lasciano spazio quando la squadra si riempie; seguono solo il nemico vivo più vicino con Dummy Follow ON, fermandosi a 4 m. Follow si può attivare solo con un dummy nella squadra avversaria; si può sempre disattivare. [Dettagli tecnici dei dummy](docs/PROGETTO.md#dummy-e-bot-normali)

Il nome visibile esatto `งูแรร์` riceve i default modificabili Silver Mist / Poison 2 e il Vibes fisso `Draconian`. Il riconoscimento avviene per nome, quindi vale anche per un omonimo.

## Documentazione

| Documento | Quando serve |
|---|---|
| [Importazione](docs/IMPORTAZIONE_ITALIANO.md) | Copia/incolla e problemi dell'editor |
| [Architettura](docs/PROGETTO.md) | Scheduler, risorse, lifecycle e interazioni |
| [Controlli automatici](docs/VALIDAZIONE.md) | Eseguire e comprendere la validazione |
| [Test nel gioco](docs/TEST.md) | Regressioni, carico e rapporto di prova |
| [Generi](docs/GENERI.md) / [Località](docs/SERVER_LOCATIONS.md) | Cataloghi ordinati |
| [Changelog](CHANGELOG.md) | Evoluzione e correzioni storiche |
