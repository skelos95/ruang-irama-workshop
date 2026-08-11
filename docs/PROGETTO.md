# Note di progetto

## Registro dei giocatori umani

`Global.PemainManusia` è la fonte unica per entrambe le liste, per il raycast dell'ispezione e per i bersagli della camera. La classificazione avviene una sola volta dopo `Has Spawned`:

1. `Is Dummy Bot == True`: escluso immediatamente.
2. Sugli altri viene tentato per un frame un nome vuoto.
3. Se il nome visualizzato diventa vuoto, il giocatore è classificato come normale bot AI della lobby.
4. Tutti gli altri vengono registrati come umani.

Il punto 2 è un workaround comunitario, non un contratto API di Blizzard. Le due `Custom String("")` vuote sono intenzionali e il comportamento va ricontrollato dopo ogni patch.

Dummy e bot AI riconosciuti non entrano mai in `PemainManusia`. Una regola separata, condizionata da `Is Alive`, disabilita fuoco primario/secondario, abilità 1/2, ultimate, melee, reload e interact a ogni respawn; movimento, salto e crouch restano disponibili.

## Vita degli HUD

I due blocchi strutturali sono globali e hanno sempre `Header = Null`: la funzione è nel campo `Text`, gli input nel `Subheader`. Ogni umano crea due righe condivise e, solo quando serve, un HUD menu. L'ispezione Crouch usa invece un testo nel mondo.

Gli ID sono copiati in quattro array globali allineati con `PemainManusia`: riga sinistra, riga destra, menu e testo nel mondo. È intenzionale: durante `Player Left Match` le variabili del giocatore uscente possono non essere più affidabili. Il cleanup usa l'indice globale e `Remove From Array By Index`.

Configurazione massima normale con 12 umani:

- 2 HUD globali;
- 24 righe lista;
- fino a 12 menu;
- fino a 12 testi nel mondo per l'ispezione;
- massimo teorico: 38 HUD e 12 testi nel mondo.

Le righe usano `Visible To String and Color`. Il colore scelto viene quindi aggiornato nelle due liste senza distruggere e ricreare gli HUD. Il Workshop colora l'intera riga, che comprende nome e dato; non supporta in modo nativo un colore diverso soltanto per una parte dello stesso `Custom String`.

## Tempo nella lobby

`WaktuMasuk` viene salvato su `Player Joined Match`, con fallback alla prima classificazione per chi era già presente quando il sorgente è stato incollato. Ogni secondo:

```text
floor((Total Time Elapsed - WaktuMasuk) / 60)
```

L'aggiornamento a un secondo è sufficiente perché il HUD mostra minuti interi e risparmia lavoro rispetto a `Update Every Frame`.

## Menu

La pressione lunga usa esattamente `Wait(1.500, Abort When False)`. `MeleeDipakai` impedisce un secondo toggle finché Melee non viene rilasciato. La stessa pressione apre il menu da chiuso e lo chiude da qualsiasi pagina.

Lo stato interno è `-1` per il menu principale e `0`, `1`, `3` per musica, camera e colori. Il numero 2 è saltato intenzionalmente. `Reload` torna soltanto al menu principale; non chiude il sistema. `Interact` entra o applica una scelta e torna al principale. Solo Melee lungo chiude normalmente il menu.

Quando il menu è aperto, i tasti usati dal menu sono disabilitati come azioni dell'eroe ma restano leggibili da `Is Button Held`. Un singolo dispatcher gestisce ciascun input e aspetta il rilascio, evitando che la stessa pressione venga eseguita di nuovo dopo un cambio pagina.

La palette contiene 10 colori leggibili. `WarnaNama` è il valore scelto dal singolo umano e viene usato nelle due liste e nel marker dell'ispezione.

## Ispezione eroe

Ogni 0,05 secondi, solo mentre Crouch è tenuto:

```text
Ray Cast Hit Player(
    Eye Position(viewer),
    Eye Position(viewer) + Facing Direction Of(viewer) * 100,
    Global.PemainManusia,
    viewer,
    False
)
```

Il primo umano colpito è l'unico mostrato. Il raycast contro il mondo impedisce di leggere giocatori dietro le pareti. Per Echo in duplicazione viene mostrato `Hero Being Duplicated`, non semplicemente Echo.

All'inizio dell'ispezione viene creato un unico `Create In-World Text`, visibile soltanto al viewer e ancorato al giocatore mirato. Contiene `Icon String(Arrow: Down)`, nome e `Hero Icon String`. `Visible To Position String and Color` rivaluta bersaglio, posizione, contenuto e colore; se il raycast restituisce `Null`, il testo sparisce. Al rilascio di Crouch, all'apertura del menu o alla morte viene distrutto con `Destroy In-World Text`.

## Camera e collisione

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
| `JarakBidik` | 100 m | Portata di ispezione e scelta bersaglio |

La camera usa un solo raggio. Un sistema multi-raggio o sphere cast ridurrebbe il clipping sugli spigoli, ma aumenterebbe sensibilmente il carico ed esula da questa prima versione.

## Estensioni naturali per una versione successiva

- preferenze persistenti durante più round della stessa sessione;
- indicatore di caricamento durante i 1,5 secondi di Melee;
- camera multi-raggio opzionale per angoli stretti;
- impostazioni Workshop per distanza, offset e portata senza modificare il sorgente;
- stato “assente/AFK” e pronome o lingua preferita accanto al genere.
