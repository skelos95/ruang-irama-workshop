# Note di progetto

## Registro e classificazione dei giocatori

`Global.PemainManusia` è la fonte unica per le due liste HUD. L'ispezione e la selezione camera usano invece tutti i giocatori validi, perché devono includere anche bot AI e dummy bot. La classificazione avviene una sola volta dopo `Has Spawned`:

1. `Is Dummy Bot == True`: escluso immediatamente dalle liste e passato a `KunciBot`.
2. Sugli altri viene tentato per due tick il carattere invisibile `U+200B` come nome.
3. Se il nome visualizzato diventa `U+200B`, il giocatore è classificato come normale bot AI della lobby.
4. Tutti gli altri vengono registrati come umani.

Il punto 2 è un workaround comunitario, non un contratto API di Blizzard. Le due stringhe apparentemente vuote contengono davvero `U+200B`; il validatore ne controlla il numero e il comportamento va ricontrollato dopo ogni patch.

Dummy e bot AI riconosciuti non entrano mai in `PemainManusia`. La subroutine `KunciBot`, riaffermata ogni 0,5 secondi mentre il bot è vivo, disabilita fuoco primario/secondario, abilità 1/2, ultimate, melee, reload e interact. Danno, cure e knockback inflitti sono inoltre impostati a zero come protezione residua; movimento, salto e crouch restano disponibili.

## Inizializzazione e cleanup

Tutto lo stato per-player viene azzerato nella subroutine `SiapkanPemain`. Viene chiamata sia da `Player Joined Match`, sia da una regola fallback per i giocatori che erano già presenti quando il sorgente è stato incollato o riavviato. `SudahSiap` impedisce inizializzazioni ripetute e la classificazione aspetta che questa preparazione sia conclusa.

Fra i valori iniziali più importanti:

- timer impostato a `Total Time Elapsed` e minuti a zero;
- lingua HUD `IndeksBahasa = 0`, cioè inglese;
- genere non ancora scelto, colore `Snow White / Putih Salju`;
- menu chiuso, cursori azzerati, ispezione e camera disattivate;
- riferimenti HUD, testo nel mondo e bersagli impostati a `Null` o array vuoto.

Gli ID delle due righe, del menu e del testo nel mondo sono copiati in quattro array globali allineati con `PemainManusia`. Durante `Player Left Match` le variabili dell'uscente possono diventare inaffidabili: il cleanup ricava quindi prima l'indice globale, distrugge gli oggetti ancora esistenti e usa `Remove From Array By Index` su tutti e cinque gli array. Se l'uscente non è umano, l'indice negativo interrompe il cleanup senza toccare altri giocatori.

Una regola separata controlla la camera: se un bersaglio seguito non esiste più, interrompe la terza persona e riporta il viewer alla visuale normale.

## HUD e localizzazione per spettatore

I due blocchi strutturali sono globali e hanno sempre `Header = Null`: la funzione è nel campo `Text`, gli input nel `Subheader`. Ogni umano crea due righe condivise e, solo quando apre il menu, un HUD personale. L'ispezione Crouch usa invece un testo nel mondo.

Le stringhe degli HUD strutturali e delle righe leggono:

```text
Player Variable(Local Player, IndeksBahasa)
```

`Local Player` fa rivalutare lo stesso testo in modo diverso su ogni client. Un viewer può quindi leggere inglese e un altro indonesiano senza creare copie delle liste. I menu personali e i messaggi usano la lingua del relativo `Event Player`. Regole, nomi delle regole e commenti del sorgente restano in indonesiano.

Il sorgente contiene 9 chiamate `Create HUD Text`: 2 strutturali, 2 per le righe e 5 schermate mutuamente esclusive per menu principale e quattro sottomenu. `GambarMenu` si limita a pulire e instradare; ogni schermata è disegnata da una subroutine separata, così nessuna singola regola menu diventa troppo complessa per il parser live. Configurazione massima normale con 12 umani:

- 2 HUD globali;
- 24 righe lista;
- fino a 12 menu attivi, uno per umano;
- fino a 12 testi nel mondo per l'ispezione;
- massimo teorico: 38 HUD e 12 testi nel mondo.

Le righe usano `Visible To String and Color`. Il colore scelto viene quindi aggiornato nelle due liste senza distruggere e ricreare gli HUD. Il Workshop colora l'intera riga, che comprende nome e dato; non supporta in modo nativo un colore diverso soltanto per una parte dello stesso `Custom String`.

## Tempo nella lobby

`WaktuMasuk` viene salvato nell'inizializzazione, sia per i nuovi ingressi sia per chi era già presente. Ogni secondo:

```text
floor((Total Time Elapsed - WaktuMasuk) / 60)
```

L'aggiornamento a un secondo è sufficiente perché il HUD mostra minuti interi e risparmia lavoro rispetto a `Update Every Frame`.

## Menu

La pressione lunga usa esattamente `Wait(1.500, Abort When False)`. `MeleeDipakai` impedisce un secondo toggle finché Melee non viene rilasciato. La stessa pressione apre il menu da chiuso e lo chiude da qualsiasi pagina.

Lo stato interno è `-1` per il menu principale e `0`, `1`, `2`, `3` per:

0. genere musicale;
1. camera in terza persona;
2. colore del nome;
3. lingua HUD.

Ogni schermata mostra una sola voce o scelta alla volta. Primary Fire seleziona la precedente e Secondary Fire la successiva, con wrap circolare. Nel menu musicale Jump e Crouch aggiungono le scorciatoie −10 e +10. `Interact` entra nel menu selezionato oppure applica la scelta senza lasciare il sottomenu. Il cambio lingua ridisegna subito il menu. `Reload` chiude da qualsiasi pagina; Melee lungo resta l'altra chiusura normale. La morte chiude soltanto come cleanup di sicurezza.

Quando il menu è aperto, i tasti usati dal menu sono disabilitati come azioni dell'eroe ma restano leggibili da `Is Button Held`. Ogni dispatcher aspetta il rilascio del proprio input, evitando ripetizioni involontarie dopo un cambio pagina.

La palette contiene 20 sfumature leggibili. I nomi sono memorizzati in due array paralleli, `NamaWarnaEN` e `NamaWarna`; `WarnaNama` è il valore scelto dal singolo umano e viene usato nelle due liste e nel marker dell'ispezione.

## Ispezione eroe

Ogni 0,05 secondi, solo mentre Crouch è tenuto:

```text
Ray Cast Hit Player(
    Eye Position(viewer),
    Eye Position(viewer) + Facing Direction Of(viewer) * 100,
    All Players(All Teams),
    viewer,
    False
)
```

Il primo giocatore colpito, umano, AI o dummy, è l'unico mostrato. Il viewer viene escluso dal raycast e il mondo impedisce di leggere giocatori dietro le pareti. Per Echo in duplicazione viene mostrato `Hero Being Duplicated`, non semplicemente Echo.

All'inizio dell'ispezione viene creato un unico `Create In-World Text` con viewer sempre uguale a `Event Player`; quando il raycast è vuoto viene rivalutata soltanto una stringa vuota. Questo evita che un testo creato inizialmente con `Visible To = Null` resti invisibile. Il testo contiene `Icon String(Arrow: Down)`, nome esplicito e `Hero Icon String`: usa il colore scelto dal bersaglio umano oppure arancione per un bot. Al rilascio di Crouch, all'apertura del menu o alla morte viene distrutto con `Destroy In-World Text`.

## Camera, bersagli e collisione

`SegarkanTargetKamera` ricostruisce l'elenco con:

```text
Filtered Array(
    All Players(All Teams),
    And(Current Array Element != viewer, Has Spawned(Current Array Element))
)
```

Il viewer è escluso perché dispone già dell'opzione “sé stesso”; tutti gli altri umani, normali bot AI e dummy bot spawnati sono selezionabili. Le scelte del sottomenu sono sempre: camera disattivata, camera su sé stessi e una voce per ogni elemento dell'array. Il refresh tenta di mantenere il bersaglio evidenziato; se non è più valido riporta il cursore a una posizione valida.

Per il bersaglio `T`:

```text
anchor  = EyePosition(T) + (0, 0.65, 0)
desired = anchor + WorldVector((0.65, 0, -4.0), T, Rotation)
hit     = RayCastHitPosition(anchor, desired, [], [], false)
camera  = hit + DirectionTowards(desired, anchor) * 0.20
lookAt  = anchor + FacingDirection(T) * 20
```

`camera` e `lookAt` sono entrambi calcolati direttamente dentro `Update Every Frame` nella chiamata a `Start Camera`. Il raycast non include giocatori o oggetti posseduti, quindi la visuale reagisce alla geometria senza saltare quando un eroe attraversa il percorso.

Valori regolabili nell'inizializzazione:

| Variabile | Default | Effetto |
|---|---:|---|
| `JarakKamera` | 4,00 m | Distanza dietro il bersaglio |
| `GeserKamera` | 0,65 m | Spostamento laterale “over shoulder” |
| `BantalanDinding` | 0,20 m | Margine che allontana la camera dalla parete |
| `JarakBidik` | 100 m | Portata dell'ispezione Crouch |

La camera usa un solo raggio. Un sistema multi-raggio o sphere cast ridurrebbe il clipping sugli spigoli, ma aumenterebbe sensibilmente il carico.

## Estensioni naturali per una versione successiva

- preferenze persistenti durante più round della stessa sessione;
- indicatore di caricamento durante i 1,5 secondi di Melee;
- camera multi-raggio opzionale per angoli stretti;
- impostazioni Workshop per distanza, offset e portata senza modificare il sorgente;
- stato “assente/AFK” e pronome preferito accanto al genere.
