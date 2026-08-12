# AFK Dedicated Server — Overwatch Workshop

Modalità sociale/Arcade per Overwatch 2 pensata come una piccola lobby AFK piena di strumenti inutilmente importanti: soundtrack personale, colori, telecamera, Revenge e teletrasporto. Nel gioco il nome visibile è **AFK Dedicated Server** e la posizione mostrata è **Indonesia**.

Gli HUD sono disponibili in **English** e **Bahasa Indonesia**, con testi adattati in modo naturale e leggermente ironico invece di traduzioni letterali. Le keyword del Workshop restano in inglese per mantenere il file importabile.

## Funzioni principali

- HUD centrale con `AFK Dedicated Server`, timer da 30:00 a 00:00 e posizione server.
- Lista a sinistra con i giocatori umani e il loro tempo AFK.
- Lista a destra con la soundtrack scelta da ogni giocatore umano.
- Menu Arcade aperto/chiuso tenendo premuto Melee per 0,5 secondi.
- Menu `0 - Soundtrack`: 100 generi ordinati dal più tranquillo al più caotico.
- Menu `1 - Third-Person Camera`: prima persona, terza persona sul proprio eroe o visuale di un altro player/bot. La distanza parte da circa 3,5 m e aumenta in base alla salute massima del bersaglio fino a circa 6,5 m; la camera è spostata verso sinistra per lasciare il mirino più a destra e dare più spazio visivo all'eroe.
- Menu `2 - Name Color`: 20 colori con nomi localizzati in inglese e indonesiano.
- Menu `3 - HUD Language`: English / Bahasa Indonesia.
- Menu `4 - Revenge`: tiene conto solo delle kill dirette ricevute dagli altri umani e permette di riscuoterle una alla volta.
- Menu `5 - Teleport`: prima voce Spawn Room, poi tutti gli altri player presenti, inclusi bot AI e dummy bot. Il proprio player non compare come destinazione.
- Teleport verso un target effettuato vicino al bersaglio usando una posizione camminabile invece di sovrapporsi al suo corpo.
- Spawn Room memorizzata quando il giocatore entra nella propria stanza di spawn; non è possibile riutilizzarla se si è già dentro.
- Crouch mostra nome, eroe e percentuale Ultimate del target vicino al reticolo; in terza persona mostra anche il proprio nome sopra la testa.
- Dummy bot e bot AI non ricevono gli HUD sociali e non possono aprire, navigare o usare il Menu Arcade. Restano però disponibili agli umani come destinazione Teleport e come target Camera.
- Gli attacchi e le abilità dei bot restano disabilitati, mentre il movimento rimane disponibile.

Il sorgente principale è [`workshop/ruang_irama.workshop`](workshop/ruang_irama.workshop).

## Controlli

| Contesto | Input | Azione |
|---|---|---|
| Sempre | Tieni Melee 0,5 s | Apre o chiude il Menu Arcade |
| Fuori menu | Tieni Crouch + mira | Mostra nome, eroe e ULT del target |
| Menu principale | Primary / Secondary Fire | Voce successiva / precedente |
| Menu principale | Interact | Entra nel menu selezionato |
| Sottomenu | Primary / Secondary Fire | Scelta successiva / precedente |
| Menu Soundtrack | Jump / Crouch | Salta indietro / avanti di 10 generi |
| Sottomenu | Interact | Applica la scelta |
| Sottomenu | Reload | Torna al menu principale |
| Qualunque pagina menu | Tieni Melee 0,5 s | Chiude il menu |

## Installazione

1. Fai una copia delle impostazioni della Partita personalizzata.
2. Imposta temporaneamente la lingua testo di Overwatch su **English (US)** se il client non accetta le keyword Workshop inglesi.
3. Apri [`workshop/ruang_irama.workshop`](workshop/ruang_irama.workshop) su GitHub e usa **Copy raw file**.
4. In Overwatch: Partita personalizzata → Crea → Impostazioni → Workshop.
5. Usa il pulsante per incollare l'intero script Workshop.
6. Dopo l'importazione puoi tornare alla lingua testo che preferisci.
7. Prova almeno un umano, un dummy bot e un normale bot AI prima di pubblicare.
8. Il codice breve Blizzard può essere generato solo dal client di Overwatch.

## Note tecniche

- Il file è un blocco Workshop e non un preset completo: non contiene `settings`, quindi non sovrascrive mappe, modalità o configurazione lobby.
- `Is Dummy Bot` identifica direttamente i dummy Workshop. Per distinguere i normali bot AI dagli umani viene mantenuto il workaround già presente basato su `Start Forcing Dummy Bot Name`.
- Gli HUD sociali vengono creati solo dopo che un giocatore è stato confermato umano.
- Il menu Teleport usa `All Players(All Teams)` per includere umani, bot AI e dummy bot.
- Tutte le regole di input del Menu Arcade verificano esplicitamente che il viewer sia umano, non sia un bot AI e non sia un dummy bot.
- Il sistema Revenge riguarda solo gli umani e non considera assist.
- Il timer centrale usa `Match Time` e viene inizializzato a 1800 secondi.
- La camera in terza persona usa `Max Health` per adattare la distanza, con raycast anti-clipping e offset laterale sinistro.

## Struttura

```text
workshop/ruang_irama.workshop  sorgente Workshop
docs/GENERI.md                  elenco generi
docs/PROGETTO.md                note di progetto
docs/TEST.md                    matrice di test
tools/validate_workshop.py      validatore statico
```

## Versione attuale

**AFK Dedicated Server** — lobby Arcade sociale bilingue con soundtrack, telecamera dinamica, colori, Revenge, Teleport e supporto player/bot.