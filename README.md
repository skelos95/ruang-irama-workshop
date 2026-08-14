# AFK Dedicated Server — Overwatch Workshop

**AFK Dedicated Server** è un overlay sociale/Arcade per Overwatch 2. Aggiunge timer di sessione, soundtrack personale, colori, telecamera in terza persona, Revenge, Unkillable + 1 HP, modifica voce e ispezione con Crouch senza imporre mappe o impostazioni lobby.

La versione **0.5.5** stabilizza i percorsi non-camera di menu, Crouch, nameplate, Teleport e lifecycle sulla base Season 4: **Heroes of Busan**. La camera in terza persona, i suoi parametri e i suoi menu restano invariati rispetto alla 0.5.4. Lo stato della release è **static-ready, live-pending**: il gate statico e le prove che richiedono il client Overwatch sono distinti in [`docs/VALIDAZIONE.md`](docs/VALIDAZIONE.md).

## Compatibilità 6v6

L'overlay è pensato per le modalità core 6v6:

- Control
- Escort
- Hybrid
- Push
- Flashpoint
- Clash

Il sorgente non contiene un blocco `settings`, quindi non seleziona né sovrascrive modalità, mappe, roster o regole della lobby. Durante la sessione disabilita il completamento e il punteggio nativi: nessuna squadra riceve punti, vittorie o pareggi. La partita termina soltanto quando il timer personalizzato arriva a `00:00`, quindi viene eseguito un unico `Restart Match` senza dichiarare un vincitore.

La durata è configurabile con `Server duration (minutes)` da 30 a 90 minuti. Il paese mostrato nell’HUD `SERVER VPN` è selezionabile con `VPN country ID (0-148)`; il default resta `62 = Indonesia`. La tabella completa è in [`docs/VPN_COUNTRIES.md`](docs/VPN_COUNTRIES.md).

## Funzioni principali

- HUD centrale con nome server, `SERVER VPN` configurabile e countdown personalizzato.
- Liste sociali degli umani con icona dell'eroe, tempo trascorso e soundtrack scelta.
- Sette menu: `0 - Soundtrack`, `1 - Third-Person Camera`, `2 - Name Color`, `3 - HUD Language`, `4 - Revenge`, `5 - Unkillable + 1 HP` e `6 - Voice Modifier`.
- 100 generi musicali e 20 colori, navigabili con wrap circolare.
- Tre localizzazioni indipendenti per viewer: **English**, **Bahasa Indonesia** e **ไทย**.
- Camera dinamica calcolata interamente dal renderer: arretramento sensibile al pitch, spalla orizzontale, collisione e mira condividono lo stesso fotogramma, con un solo raycast e senza loop server.
- Ispezione Crouch con candidati validi e visibili, ordinati per angolo rispetto al reticolo; nome, icona eroe e carica Ultimate usano il colore personale per gli umani e l'arancione per i bot.
- Revenge basato sulle eliminazioni dirette ricevute dagli altri umani, con identità del bersaglio preservata anche durante cambiamenti della lobby.
- Teleport verso l'ultima Spawn Room visitata, obiettivi disponibili e giocatori presenti, con identità del target bloccata prima del refresh per evitare retarget quando qualcuno esce.
- Classificazione degli umani e dei bot AI prima della creazione degli HUD sociali; i dummy bot seguono invece il lifecycle edge-triggered dedicato.
- Cleanup di HUD, testi nel mondo, camera e riferimenti Revenge in uscita, più ripristino di menu e Crouch durante morte, despawn, hero-select o passaggio a spettatore.
- Sincronizzazione delle nameplate quando un umano viene registrato o un bot viene bloccato/spawnato mentre altri viewer stanno già ispezionando.
- Slot HUD riutilizzabili e registri allineati, per evitare crescita permanente dopo cicli join/leave.
- Diagnostica prestazionale opzionale, visibile soltanto all'host e disattivata per impostazione predefinita.

## Controlli

| Contesto | Input | Azione |
|---|---|---|
| Sempre | Tieni Melee per 0,5 s | Apre o chiude il Menu Arcade |
| Fuori menu | Tieni Crouch e mira | Ispeziona il target vicino al reticolo |
| Menu principale | Primary / Secondary Fire | Voce successiva / precedente |
| Menu principale | Interact | Entra nel menu selezionato |
| Sottomenu | Primary / Secondary Fire | Scelta successiva / precedente (`±1`) |
| Menu Soundtrack | Jump / Crouch | Salta indietro / avanti di 10 generi (`−10` / `+10`) |
| Sottomenu | Interact | Applica la scelta o l'azione |
| Sottomenu | Reload | Torna al menu principale |
| Qualunque pagina menu | Tieni Melee per 0,5 s | Chiude il menu |

Quando più input vengono rilevati nello stesso ciclo, il dispatcher usa questa priorità: `Interact → Reload → Primary → Secondary → Jump → Crouch`.

## Installazione

1. Salva una copia delle impostazioni della Partita personalizzata.
2. Se necessario, imposta temporaneamente la lingua testo di Overwatch su **English (US)** per importare le keyword Workshop.
3. Apri [`workshop/ruang_irama.workshop`](workshop/ruang_irama.workshop) e copia il contenuto raw.
4. In Overwatch apri Partita personalizzata → Crea → Impostazioni → Workshop e incolla il sorgente.
5. Configura una delle modalità core 6v6 e le mappe desiderate nelle normali impostazioni lobby.
6. Imposta durata, `VPN country ID (0-148)` e diagnostica dalle opzioni Workshop; per gli ID consulta [`docs/VPN_COUNTRIES.md`](docs/VPN_COUNTRIES.md).
7. Prima di pubblicare, esegui i controlli live descritti in [`docs/TEST.md`](docs/TEST.md).

Il codice breve Blizzard può essere generato soltanto dal client di Overwatch.

## Note tecniche

- Le keyword e le API native Workshop restano in inglese; identificatori, regole e commenti personalizzati sono in Bahasa Indonesia.
- I dummy bot bypassano la classificazione degli umani e sono gestiti dal lifecycle edge-triggered tramite `Is Dummy Bot`. Per i normali bot AI resta necessario il workaround con due sentinelle `U+200B`, da ricontrollare dopo ogni patch.
- Bot AI e dummy bot non ricevono i menu o gli HUD sociali, ma possono restare destinazioni valide per camera e Crouch.
- Il timer usa una propria origine e una propria scadenza e aggiorna la stringa visualizzata una volta al secondo.
- Con `Performance diagnostics` disattivato non viene mantenuta la telemetria Inspector dedicata. Quando è attivo, soltanto l'host vede carico corrente, medio, picco e conteggi HUD/IWT.
- I controlli statici non possono certificare il comportamento live del parser, la sentinella bot o la stabilità a 12 giocatori. Lo stato verificato è riportato in [`docs/VALIDAZIONE.md`](docs/VALIDAZIONE.md).

## Struttura

```text
workshop/ruang_irama.workshop  sorgente Workshop importabile
docs/GENERI.md                  catalogo dei 100 generi
docs/PROGETTO.md                architettura e scelte di progetto
docs/TEST.md                    matrice di test statici e live
docs/VALIDAZIONE.md             rapporto di validazione della release
tools/validate_workshop.py      validatore statico read-only
```

## Versione attuale

**0.5.5 — Stabilizzazione non-camera**

- La chiusura del menu mantiene coerente il latch Melee anche durante morte, despawn, hero-select e passaggio a spettatore.
- Crouch filtra prima target non validi o occlusi e sceglie poi il candidato col minore angolo rispetto al reticolo, senza nuove soglie di distanza o angolo.
- Nameplate, HUD e testi vengono ripuliti nei percorsi di lifecycle e sincronizzati per i nuovi umani e bot mentre l'ispezione è già attiva.
- Teleport conserva l'identità selezionata prima del refresh; se il player esce, l'azione viene annullata invece di passare al nuovo elemento dello stesso indice.
- Lo stato vuoto di Revenge è localizzato; la lista continua intenzionalmente a mostrare gli altri umani anche con debito `0`, ma il claim resta bloccato.
- Validatore, test negativi e CI sono irrigiditi; la release resta **static-ready, live-pending** fino al completamento della matrice nel client.
- Logica, valori, raycast, comportamento e menu della camera in terza persona sono invariati.

Release precedente: **0.5.4 — Inquadratura verticale pitch-aware**

- Il braccio posteriore della camera segue sia yaw sia pitch, mantenendo l'eroe nell'inquadratura quando si guarda in alto o in basso.
- L'offset laterale resta sul piano orizzontale per evitare capovolgimenti o collassi della spalla agli angoli estremi.
- Restano invariati pipeline per-frame, singolo raycast, margine anti-muro e blend `0` della correzione fluida.

Release precedente alla 0.5.4: **0.5.3 — Camera interamente per-frame**

- Rimossi il loop camera e tutte le cache di posizione sincronizzate dal server.
- Anchor, spalla, raycast, margine parete e punto di mira sono rivalutati nella stessa pipeline visuale del client.
- Blend `0` per evitare un secondo inseguitore sopra coordinate già aggiornate per fotogramma.
- Il test live ha confermato la fluidità, ma ha anche mostrato che l'arretramento soltanto orizzontale lasciava uscire l'eroe dall'inquadratura con pitch elevato; la 0.5.4 corregge la geometria.

Release precedente: **0.5.2 — Primo intervento sulla fluidità camera**

- Eliminata l'oscillazione verticale causata da pitch e correzione variabile vicino agli spigoli.
- Il test live ha però mostrato che la traslazione per-frame combinata con un offset server e blend `80` poteva ancora produrre vibrazione; la 0.5.3 sostituisce quella pipeline.

Release precedente stabile per l'import: **0.5.1 — Correzione importazione Workshop**

- Sostituito il tipo evento inesistente `Player Spawned` con transizioni compatibili di morte/despawn e `Is Alive`.
- Il validatore ora rifiuta tipi evento non riconosciuti dal Workshop.

Base funzionale: **0.5.0 — Season 4: Heroes of Busan**.

Riferimento patch: [Overwatch Retail Patch Notes — August 11, 2026](https://us.forums.blizzard.com/en/overwatch/t/overwatch-retail-patch-notes-%E2%80%93-august-11-2026/1032368).
