# AFK Dedicated Server — Overwatch Workshop

**AFK Dedicated Server** è un overlay sociale/Arcade per Overwatch 2. Aggiunge timer di sessione, soundtrack personale, colori, telecamera in terza persona, Revenge, Teleport e ispezione con Crouch senza imporre mappe o impostazioni lobby.

La versione **0.5.3** è allineata alla Season 4: **Heroes of Busan**, iniziata l'11 agosto 2026. La matrice di compatibilità comprende D.Mon e le versioni aggiornate di Busan, Paraíso ed Eichenwalde; le prove che richiedono il client live sono elencate separatamente in [`docs/TEST.md`](docs/TEST.md).

## Compatibilità 6v6

L'overlay è pensato per le modalità core 6v6:

- Control
- Escort
- Hybrid
- Push
- Flashpoint
- Clash

Il sorgente non contiene un blocco `settings`, quindi non seleziona né sovrascrive modalità, mappe, roster o regole della lobby. Durante la sessione disabilita il completamento e il punteggio nativi: nessuna squadra riceve punti, vittorie o pareggi. La partita termina soltanto quando il timer personalizzato arriva a `00:00`, quindi viene eseguito un unico `Restart Match` senza dichiarare un vincitore.

La durata è configurabile con `Server duration (minutes)` da 30 a 90 minuti.

## Funzioni principali

- HUD centrale con nome server, posizione Indonesia e countdown personalizzato.
- Liste sociali degli umani con tempo trascorso e soundtrack scelta.
- Sei menu: `0 - Soundtrack`, `1 - Third-Person Camera`, `2 - Name Color`, `3 - HUD Language`, `4 - Revenge` e `5 - Teleport`.
- 100 generi musicali e 20 colori, navigabili con wrap circolare.
- Tre localizzazioni indipendenti per viewer: **English**, **Bahasa Indonesia** e **ไทย**.
- Camera dinamica calcolata interamente dal renderer: posizione, arretramento orizzontale, collisione e mira condividono lo stesso fotogramma, con un solo raycast e senza loop server.
- Ispezione Crouch con nome, eroe e carica Ultimate; gli umani usano il proprio colore e i bot un outline arancione.
- Revenge basato sulle eliminazioni dirette ricevute dagli altri umani, con identità del bersaglio preservata anche durante cambiamenti della lobby.
- Teleport verso l'ultima Spawn Room visitata, obiettivi disponibili e giocatori presenti, inclusi bot AI e dummy bot quando validi.
- Classificazione umani/bot prima della creazione degli HUD sociali e ripristino del blocco bot dopo spawn, respawn o cambio eroe.
- Cleanup di HUD, testi nel mondo, camera, menu e riferimenti Revenge quando un giocatore esce.
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
6. Imposta durata e diagnostica dalle opzioni Workshop.
7. Prima di pubblicare, esegui i controlli live descritti in [`docs/TEST.md`](docs/TEST.md).

Il codice breve Blizzard può essere generato soltanto dal client di Overwatch.

## Note tecniche

- Le keyword e le API native Workshop restano in inglese; identificatori, regole e commenti personalizzati sono in Bahasa Indonesia.
- I dummy bot sono riconosciuti tramite `Is Dummy Bot`. Per i normali bot AI resta necessario il workaround con due sentinelle `U+200B`, da ricontrollare dopo ogni patch.
- Bot AI e dummy bot non ricevono i menu o gli HUD sociali, ma possono restare destinazioni valide per camera, Crouch e Teleport.
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

**0.5.3 — Camera interamente per-frame**

- Rimossi il loop camera e tutte le cache di posizione sincronizzate dal server.
- Anchor, spalla, raycast, margine parete e punto di mira sono rivalutati nella stessa pipeline visuale del client.
- Blend `0` per evitare un secondo inseguitore sopra coordinate già aggiornate per fotogramma.

Release precedente: **0.5.2 — Primo intervento sulla fluidità camera**

- Eliminata l'oscillazione verticale causata da pitch e correzione variabile vicino agli spigoli.
- Il test live ha però mostrato che la traslazione per-frame combinata con un offset server e blend `80` poteva ancora produrre vibrazione; la 0.5.3 sostituisce quella pipeline.

Release precedente stabile per l'import: **0.5.1 — Correzione importazione Workshop**

- Sostituito il tipo evento inesistente `Player Spawned` con transizioni compatibili di morte/despawn e `Is Alive`.
- Il validatore ora rifiuta tipi evento non riconosciuti dal Workshop.

Base funzionale: **0.5.0 — Season 4: Heroes of Busan**.

Riferimento patch: [Overwatch Retail Patch Notes — August 11, 2026](https://us.forums.blizzard.com/en/overwatch/t/overwatch-retail-patch-notes-%E2%80%93-august-11-2026/1032368).
