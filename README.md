# Ruang Irama — Overwatch Workshop

Prototipo di modalità/social layer per Overwatch 2. Il nome significa, più o meno, “stanza del ritmo”. Tutti i testi visibili, i nomi delle regole e i commenti nel Workshop sono scritti in indonesiano colloquiale; le parole chiave del linguaggio Workshop restano in inglese per consentire l'importazione del sorgente.

## Cosa fa

- A sinistra mostra soltanto i giocatori umani nelle slot di gioco e i minuti trascorsi nell'istanza della lobby.
- A destra mostra il genere musicale scelto da ogni umano.
- Tenendo premuto Melee per 1,5 secondi apre un menu con 100 generi e sottogeneri, ordinati da `Lowercase` a `Extratone`.
- Tenendo premuto Crouch e mirando un umano mostra nome, nome eroe e icona eroe, un bersaglio alla volta e rispettando pareti/linea visiva.
- Dal menu abilita la terza persona su sé stessi oppure segue l'umano sotto il mirino.
- La telecamera usa `Update Every Frame` e accorcia la distanza con un raycast quando incontra una parete.
- Esclude dummy bot e tenta di escludere anche i normali bot AI aggiunti dalla lobby.

Il sorgente principale è [workshop/ruang_irama.workshop](workshop/ruang_irama.workshop).

## Comandi

Il HUD usa `Input Binding String`, quindi mostra i tasti realmente associati dal singolo giocatore.

| Contesto | Input | Azione |
|---|---|---|
| Sempre | Tieni Melee 1,5 s | Apre il menu |
| Fuori menu | Tieni Crouch + mira | Ispeziona nome ed eroe dell'umano in linea visiva |
| Menu | Jump / Crouch | Genere precedente / successivo |
| Menu | Primary / Secondary Fire | Salta indietro / avanti di 10 generi |
| Menu | Interact | Salva il genere e chiude |
| Menu | Reload | Chiude senza cambiare genere |
| Menu | Ability 1 | Terza persona su sé stessi |
| Menu | Ability 2 | Segue l'umano attualmente sotto il mirino |
| Menu | Ultimate | Disattiva la telecamera personalizzata |

## Installazione

1. Fai una copia delle impostazioni della tua Partita personalizzata.
2. Per la massima compatibilità, imposta temporaneamente la lingua testuale del client su inglese: le parole chiave del file sono quelle dell'export inglese.
3. Copia tutto il contenuto di [workshop/ruang_irama.workshop](workshop/ruang_irama.workshop) e incollalo nell'editor Workshop della partita personalizzata.
4. Mantieni o modifica liberamente modalità, mappe e regole di gioco di base: questo progetto è pensato come sistema HUD/camera sovrapponibile.
5. Prova almeno un umano, un dummy bot e un normale bot AI della lobby prima di pubblicare.
6. Solo dopo il test nel gioco, usa il comando di condivisione di Overwatch per generare il codice breve Blizzard.

GitHub conserva il sorgente copiabile, ma non può generare il codice condivisibile di Overwatch: quel codice nasce esclusivamente dal client di gioco. La [guida introduttiva ufficiale di Blizzard](https://news.blizzard.com/en-gb/article/22938941/introducing-the-overwatch-workshop) descrive il flusso Workshop; una guida comunitaria aggiornata mostra anche il comportamento dei [codici di condivisione](https://workshop.codes/wiki/articles/workshop-basics).

## Stato del prototipo

La struttura e i requisiti sono coperti. Il 2026-08-11 il file è stato importato e compilato con successo nell'editor di Workshop.codes: tutte le 23 regole sono state riconosciute. I controlli statici locali sono inclusi. Resta necessario il test nel client Overwatch per comportamento, carico server e compatibilità della patch corrente.

Per eseguire i controlli locali:

```text
python tools/validate_workshop.py
```

Il controllo verifica, tra le altre cose: 100 generi unici e identici alla documentazione, 10 pagine, parentesi e graffe bilanciate, presenza di U+200B nel filtro AI, camera con `Update Every Frame`, collisione raycast, gestione Echo e registro globale per il cleanup HUD.

## Limiti da conoscere

1. **Il genere è un'etichetta, non audio riprodotto.** Il Workshop non può caricare brani, URL o file audio personalizzati. La scelta serve come stato sociale visibile.
2. **I bot AI richiedono un workaround.** `Is Dummy Bot` riconosce i dummy Workshop ma non i normali bot AI. Il progetto usa il trucco comunitario del nome invisibile U+200B con `Start Forcing Dummy Bot Name`; può rompersi dopo una patch. Il fallback davvero affidabile è non aggiungere bot AI normali alla lobby. Vedi [rilevamento AI/dummy/umani](https://workshop.codes/wiki/articles/detect-ai-dummy-and-real-players-separately).
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
- [Start Camera](https://workshop.codes/wiki/articles/start-camera), [Update Every Frame](https://workshop.codes/wiki/articles/update-every-frame) e [Ray Cast Hit Position](https://workshop.codes/wiki/articles/ray-cast-hit-position)
- [Player Left Match](https://workshop.codes/wiki/articles/player-left-match) per il motivo del registro globale degli ID HUD

## Versione

`0.1.0` — prima base giocabile da importare e collaudare.
