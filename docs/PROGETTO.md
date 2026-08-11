# Note di progetto

## Registro dei giocatori umani

`Global.PemainManusia` è la fonte unica per entrambe le liste, per il raycast dell'ispezione e per i bersagli della camera. La classificazione avviene una sola volta dopo `Has Spawned`:

1. `Is Dummy Bot == True`: escluso immediatamente.
2. Sugli altri viene tentato per un frame il nome invisibile U+200B.
3. Se il nome visualizzato diventa U+200B, il giocatore è classificato come normale bot AI della lobby.
4. Tutti gli altri vengono registrati come umani.

Il punto 2 è un workaround comunitario, non un contratto API di Blizzard. Non rimuovere o normalizzare il carattere invisibile nelle due `Custom String` coinvolte.

## Vita degli HUD

Le due intestazioni e il suggerimento comandi sono globali. Ogni umano crea due righe condivise e, solo quando servono, un HUD menu e un HUD ispezione.

Gli ID sono copiati in quattro array globali allineati con `PemainManusia`. È intenzionale: durante `Player Left Match` le variabili del giocatore uscente possono non essere più affidabili. Il cleanup usa l'indice globale e `Remove From Array By Index`, evitando testi orfani che consumerebbero il limite HUD.

Configurazione massima normale con 12 umani:

- 3 HUD globali;
- 24 righe lista;
- fino a 12 menu;
- fino a 12 pannelli ispezione;
- totale massimo teorico: 51 testi, ben sotto 128.

## Tempo nella lobby

`WaktuMasuk` viene salvato su `Player Joined Match`, con fallback alla prima classificazione per chi era già presente quando il sorgente è stato incollato. Ogni secondo:

```text
floor((Total Time Elapsed - WaktuMasuk) / 60)
```

L'aggiornamento a un secondo è sufficiente perché il HUD mostra minuti interi e risparmia lavoro rispetto a `Update Every Frame`.

## Menu

La pressione lunga usa esattamente `Wait(1.500, Abort When False)`. `MeleeDipakai` impedisce una riapertura involontaria finché Melee non viene rilasciato.

Quando il menu è aperto, i tasti usati dal menu sono disabilitati come azioni dell'eroe ma restano leggibili da `Is Button Held`. Ogni comando aspetta il rilascio per evitare rimbalzi.

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

- sottomenu dedicato alla camera con giocatore precedente/successivo;
- preferenze persistenti durante più round della stessa sessione;
- indicatore di caricamento durante i 1,5 secondi di Melee;
- camera multi-raggio opzionale per angoli stretti;
- impostazioni Workshop per distanza, offset e portata senza modificare il sorgente;
- stato “assente/AFK” e pronome o lingua preferita accanto al genere.
