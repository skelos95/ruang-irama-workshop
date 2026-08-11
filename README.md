# Ruang Irama — Overwatch Workshop

Prototipo di modalità/social layer per Overwatch 2. Il nome significa, più o meno, “stanza del ritmo”. Regole e commenti del Workshop restano in indonesiano colloquiale; gli HUD possono invece essere letti in inglese o indonesiano, con inglese predefinito per ogni nuovo ingresso. Le parole chiave del linguaggio Workshop restano in inglese per consentire l'importazione del sorgente.

## Cosa fa

- A sinistra mostra soltanto gli umani e i minuti trascorsi nell'istanza della lobby; a destra mostra il loro genere musicale.
- Ogni spettatore vede gli HUD nella propria lingua grazie a `Local Player`: due persone possono scegliere lingue diverse senza duplicare le righe condivise.
- Gli HUD non usano il campo Header: la funzione è nel testo principale e gli input sono nel sottotitolo, con spaziatura più leggibile.
- Tenendo premuto Melee per 1,5 secondi apre o chiude il menu principale numerato: `0` genere musicale, `1` camera in terza persona, `2` colore del nome, `3` lingua HUD.
- Ogni menu mostra una sola scelta alla volta. Primary Fire e Secondary Fire scorrono indietro e avanti; Interact entra nel sottomenu o applica la scelta senza chiuderlo.
- Il menu musica contiene 100 generi e sottogeneri, ordinati da `Lowercase` a `Extratone`.
- Il menu camera può disattivare la camera, usarla su sé stessi oppure seguire un altro giocatore selezionato, compresi umani, normali bot AI e dummy bot.
- Ogni umano sceglie una fra 20 sfumature con nome inglese e indonesiano; la propria riga usa quel colore in entrambe le liste.
- Tenendo premuto Crouch e mirando un umano o un bot mostra direttamente sopra il bersaglio nome, icona eroe e freccia verso il basso. Gli umani usano il proprio colore scelto; i bot usano l'arancione.
- La telecamera usa `Update Every Frame` e accorcia la distanza con un raycast quando incontra una parete.
- Dummy bot e normali bot AI non compaiono nelle liste; attacchi, abilità, ultimate e melee restano disabilitati, mentre possono ancora muoversi.
- Una inizializzazione comune copre sia i nuovi ingressi sia i giocatori già presenti; all'uscita vengono rimossi HUD e testi nel mondo associati.

Il sorgente principale è [workshop/ruang_irama.workshop](workshop/ruang_irama.workshop).

## Comandi

Il HUD usa `Input Binding String`, quindi mostra i tasti realmente associati dal singolo giocatore.

| Contesto | Input | Azione |
|---|---|---|
| Sempre | Tieni Melee 1,5 s | Apre il menu se chiuso; lo chiude da qualunque pagina se aperto |
| Fuori menu | Tieni Crouch + mira | Mostra nome, freccia colorata e icona eroe sull'umano o bot in linea visiva |
| Menu principale | Primary / Secondary Fire | Seleziona il menu precedente / successivo fra `0`, `1`, `2`, `3` |
| Menu principale | Interact | Entra nel menu selezionato |
| Qualunque sottomenu | Primary / Secondary Fire | Mostra la scelta precedente / successiva |
| Menu `0` | Jump / Crouch | Salta indietro / avanti di 10 generi |
| Qualunque sottomenu | Interact | Applica la scelta e resta nello stesso sottomenu |
| Qualunque pagina menu | Reload | Chiude immediatamente il menu |
| Qualunque pagina menu | Tieni Melee 1,5 s | Chiude il menu |

## Installazione

1. Fai una copia delle impostazioni della tua Partita personalizzata.
2. Chiudi Overwatch e imposta temporaneamente la **lingua testo** del client su **English (US)**: le parole chiave del file sono quelle dell'export inglese. Su Battle.net: Overwatch 2 → ingranaggio accanto a Gioca → Impostazioni di gioco → Lingua testo.
3. Apri [workshop/ruang_irama.workshop](workshop/ruang_irama.workshop) su GitHub e premi **Copy raw file** (icona con due quadratini). Non usare `Ctrl+A` sulla pagina GitHub e non copiare un blocco Markdown.
4. In Overwatch vai in Partita personalizzata → Crea → Impostazioni → **Workshop**.
5. Nella schermata Workshop compare il pulsante arancione per incollare lo script completo: premilo dalla barra superiore, non dentro una singola regola. Non serve `Ctrl+V`.
6. Se il pulsante non appare, verifica in Blocco note che gli appunti inizino esattamente con `variables`, ricopia con **Copy raw file**, controlla che la lingua testo sia inglese e riapri la schermata Workshop. Dopo l'importazione puoi tornare all'italiano.
7. Mantieni o modifica liberamente modalità, mappe e regole di gioco di base: questo progetto è pensato come sistema HUD/camera sovrapponibile.
8. Prova almeno un umano, un dummy bot e un normale bot AI della lobby prima di pubblicare.
9. Solo dopo il test nel gioco, usa il comando di condivisione di Overwatch per generare il codice breve Blizzard.

Il file è intenzionalmente un **blocco Workshop**, non un preset completo: non contiene `settings`, quindi non sovrascrive modalità, mappe o lobby. GitHub conserva il sorgente copiabile, ma non può generare il codice condivisibile di Overwatch: quel codice nasce esclusivamente dal client di gioco. La [guida introduttiva ufficiale di Blizzard](https://news.blizzard.com/en-gb/article/22938941/introducing-the-overwatch-workshop) descrive il flusso Workshop; una guida comunitaria aggiornata mostra anche il comportamento dei [codici di condivisione](https://workshop.codes/wiki/articles/workshop-basics).

## Stato del prototipo

La versione `0.3.0` separa i quattro menu, aggiunge la selezione diretta dei bersagli camera, porta la palette a 20 sfumature e introduce HUD bilingui per singolo spettatore con inglese predefinito. Rafforza inoltre inizializzazione dei giocatori, aggiornamento dei bersagli e cleanup all'uscita.

Per eseguire i controlli locali:

```text
python tools/validate_workshop.py
```

Il controllo verifica, tra le altre cose: 100 generi, 10 fasce musicali, 20 colori, menu `0/1/2/3`, due lingue, uso di `Local Player`, HUD senza Header, marker nel mondo con freccia e colore dinamico, blocco degli attacchi dei bot, sentinella AI, camera per-frame, inizializzazione e cleanup globale.

## Limiti da conoscere

1. **Il genere è un'etichetta, non audio riprodotto.** Il Workshop non può caricare brani, URL o file audio personalizzati. La scelta serve come stato sociale visibile.
2. **I bot AI richiedono un workaround.** `Is Dummy Bot` riconosce i dummy Workshop ma non i normali bot AI. Il progetto forza per due tick il carattere invisibile `U+200B` con `Start Forcing Dummy Bot Name`: il client applica il cambio soltanto ai bot AI. Il file e gli appunti devono quindi conservare quel carattere. Il metodo può comunque rompersi dopo una patch. Vedi [rilevamento AI/dummy/umani](https://workshop.codes/wiki/articles/detect-ai-dummy-and-real-players-separately).
3. **Il timer parte quando il Workshop vede il giocatore.** Misura l'istanza corrente con `Total Time Elapsed`; non include il tempo passato nel browser delle partite o prima dell'avvio delle regole.
4. **“Segui giocatore” non è uno slot spettatore vero.** `Start Camera` cambia la visuale, ma il corpo del viewer resta nella partita e controllabile. Non viene reso invulnerabile né immobilizzato.
5. **La collisione è a raggio singolo.** Le pareti normali vengono rispettate; angoli molto stretti, porte sottili e geometrie irregolari possono ancora produrre un po' di clipping.
6. **Gli spettatori neutrali non sono elencati.** Il registro HUD usa i giocatori nelle due squadre/slot di gioco; il menu camera seleziona i giocatori spawnati delle squadre.

## Struttura

```text
workshop/ruang_irama.workshop  sorgente da incollare nel Workshop
docs/GENERI.md                  elenco completo e criterio di ordinamento
docs/PROGETTO.md                architettura, formule e punti regolabili
docs/TEST.md                    matrice di prova nel client
tools/validate_workshop.py      validatore statico senza dipendenze
```

## Riferimenti tecnici

- [Create HUD Text](https://workshop.codes/wiki/articles/create-hud-text) e [Local Player](https://workshop.codes/wiki/articles/local-player)
- [Is Button Held](https://workshop.codes/wiki/articles/is-button-held) e [Wait](https://workshop.codes/wiki/articles/wait)
- [Ray Cast Hit Player](https://workshop.codes/wiki/articles/ray-cast-hit-player) e [Hero Icon String](https://workshop.codes/wiki/articles/hero-icon-string)
- [Create In-World Text](https://workshop.codes/wiki/articles/create-inworld-text), [Icon String](https://workshop.codes/wiki/articles/icon-string) e [Destroy In-World Text](https://workshop.codes/wiki/articles/destroy-inworld-text)
- [Set Primary Fire Enabled](https://workshop.codes/wiki/articles/set-primary-fire-enabled) e [Set Ability 1 Enabled](https://workshop.codes/wiki/articles/set-ability-1-enabled)
- [Start Camera](https://workshop.codes/wiki/articles/start-camera), [Update Every Frame](https://workshop.codes/wiki/articles/update-every-frame) e [Ray Cast Hit Position](https://workshop.codes/wiki/articles/ray-cast-hit-position)
- [Player Left Match](https://workshop.codes/wiki/articles/player-left-match) per il motivo del registro globale degli ID HUD

## Versione

`0.3.0` — quattro menu separati, camera su qualunque giocatore spawnato, 20 sfumature, HUD inglese/indonesiano per spettatore e lifecycle più robusto.
