# Ruang Irama — Overwatch Workshop

Prototipo di modalità/social layer per Overwatch 2. Il nome significa, più o meno, “stanza del ritmo”. Tutti i testi visibili, i nomi delle regole e i commenti nel Workshop sono scritti in indonesiano colloquiale; le parole chiave del linguaggio Workshop restano in inglese per consentire l'importazione del sorgente.

## Cosa fa

- A sinistra mostra soltanto gli umani e i minuti trascorsi nell'istanza della lobby; a destra mostra il loro genere musicale.
- Gli HUD non usano il campo Header: la funzione è nel testo principale e gli input sono nel sottotitolo, con spaziatura più leggibile.
- Tenendo premuto Melee per 1,5 secondi apre o chiude il menu principale numerato: `0` musica, `1` camera, `3` colore del nome.
- Il menu musica contiene 100 generi e sottogeneri, ordinati da `Lowercase` a `Extratone`.
- Ogni umano sceglie uno fra 10 colori; la propria riga usa quel colore in entrambe le liste.
- Tenendo premuto Crouch e mirando un umano o un bot mostra direttamente sopra il bersaglio nome, icona eroe e freccia verso il basso. Gli umani usano il proprio colore scelto; i bot usano l'arancione.
- Il menu camera abilita la terza persona su sé stessi, segue l'umano sotto il mirino oppure ripristina la visuale normale.
- La telecamera usa `Update Every Frame` e accorcia la distanza con un raycast quando incontra una parete.
- Esclude dummy bot e normali bot AI dalle liste; inoltre disabilita i loro attacchi, abilità, ultimate e melee, lasciando disponibile il movimento.

Il sorgente principale è [workshop/ruang_irama.workshop](workshop/ruang_irama.workshop).

## Comandi

Il HUD usa `Input Binding String`, quindi mostra i tasti realmente associati dal singolo giocatore.

| Contesto | Input | Azione |
|---|---|---|
| Sempre | Tieni Melee 1,5 s | Apre il menu se chiuso; lo chiude da qualunque pagina se aperto |
| Fuori menu | Tieni Crouch + mira | Mostra nome, freccia colorata e icona eroe sull'umano o bot in linea visiva |
| Menu principale | Jump / Crouch | Seleziona `0` musica, `1` camera o `3` colore |
| Menu principale | Interact | Entra nel menu selezionato |
| Menu `0` | Jump / Crouch | Genere precedente / successivo |
| Menu `0` | Primary / Secondary Fire | Salta indietro / avanti di 10 generi |
| Menu `1` | Jump / Crouch | Seleziona camera su sé, sul bersaglio o disattivata |
| Menu `3` | Jump / Crouch | Cambia l'anteprima del colore del nome |
| Sottomenu | Interact | Applica la scelta e resta nello stesso sottomenu |
| Qualunque pagina menu | Reload | Chiude immediatamente il menu |

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

La versione `0.2.1` corregge i problemi osservati nel client live: filtro dei normali bot AI, blocco persistente del combattimento, ispezione Crouch su umani e bot e permanenza nei sottomenu dopo `Interact`. Resta necessario il test finale nel client Overwatch per comportamento e carico server.

Per eseguire i controlli locali:

```text
python tools/validate_workshop.py
```

Il controllo verifica, tra le altre cose: 100 generi, 10 pagine, 10 colori, menu `0/1/3`, HUD senza Header, marker nel mondo con freccia e colore dinamico, blocco degli attacchi dei bot, sentinella AI, camera per-frame e cleanup globale.

## Limiti da conoscere

1. **Il genere è un'etichetta, non audio riprodotto.** Il Workshop non può caricare brani, URL o file audio personalizzati. La scelta serve come stato sociale visibile.
2. **I bot AI richiedono un workaround.** `Is Dummy Bot` riconosce i dummy Workshop ma non i normali bot AI. Il progetto forza per due tick il carattere invisibile `U+200B` con `Start Forcing Dummy Bot Name`: il client applica il cambio soltanto ai bot AI. Il file e gli appunti devono quindi conservare quel carattere. Il metodo può comunque rompersi dopo una patch. Vedi [rilevamento AI/dummy/umani](https://workshop.codes/wiki/articles/detect-ai-dummy-and-real-players-separately).
3. **Il timer parte quando il Workshop vede il giocatore.** Misura l'istanza corrente con `Total Time Elapsed`; non include il tempo passato nel browser delle partite o prima dell'avvio delle regole.
4. **“Segui giocatore” non è uno slot spettatore vero.** `Start Camera` cambia la visuale, ma il corpo del viewer resta nella partita e controllabile. Non viene reso invulnerabile né immobilizzato.
5. **La collisione è a raggio singolo.** Le pareti normali vengono rispettate; angoli molto stretti, porte sottili e geometrie irregolari possono ancora produrre un po' di clipping.
6. **Gli spettatori neutrali non sono elencati.** Il registro usa i giocatori nelle due squadre/slot di gioco.

## Struttura

```text
workshop/ruang_irama.workshop  sorgente da incollare nel Workshop
docs/GENERI.md                  elenco completo e criterio di ordinamento
docs/PROGETTO.md                architettura, formule e punti regolabili
docs/TEST.md                    matrice di prova nel client
tools/validate_workshop.py      validatore statico senza dipendenze
```

## Riferimenti tecnici

- [Create HUD Text](https://workshop.codes/wiki/articles/create-hud-text)
- [Is Button Held](https://workshop.codes/wiki/articles/is-button-held) e [Wait](https://workshop.codes/wiki/articles/wait)
- [Ray Cast Hit Player](https://workshop.codes/wiki/articles/ray-cast-hit-player) e [Hero Icon String](https://workshop.codes/wiki/articles/hero-icon-string)
- [Create In-World Text](https://workshop.codes/wiki/articles/create-inworld-text), [Icon String](https://workshop.codes/wiki/articles/icon-string) e [Destroy In-World Text](https://workshop.codes/wiki/articles/destroy-inworld-text)
- [Set Primary Fire Enabled](https://workshop.codes/wiki/articles/set-primary-fire-enabled) e [Set Ability 1 Enabled](https://workshop.codes/wiki/articles/set-ability-1-enabled)
- [Start Camera](https://workshop.codes/wiki/articles/start-camera), [Update Every Frame](https://workshop.codes/wiki/articles/update-every-frame) e [Ray Cast Hit Position](https://workshop.codes/wiki/articles/ray-cast-hit-position)
- [Player Left Match](https://workshop.codes/wiki/articles/player-left-match) per il motivo del registro globale degli ID HUD

## Versione

`0.2.1` — filtro bot AI live corretto, bot resi innocui, Crouch su umani e bot e menu chiudibile con Reload o Melee.
