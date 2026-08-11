# Rapporto di validazione

Data: 2026-08-11

## Controlli statici

Esito: superati.

```text
OK - controlli statici superati
Generi: 100 unici | Pagine: 10 | Regole: 33
Colori: 20 | Lingue: 2 | HUD definiti nel sorgente: 10
```

Il validatore controlla anche 12 subroutine, 20 colori e relativi nomi bilingui, menu `0/1/2/3`, due lingue con inglese predefinito, uso per-viewer di `Local Player`, Header nulli, titolo `FRIENDLY DEDICATED SERVER`, posizione Indonesia bilingue, righe lista nel `Subheader`, palette senza grigio, menu `Top, 100`, assenza della vecchia freccia, due IWT Crouch per viewer, ULT%, hide/restore delle nameplate, blocco combattimento dei bot, due sentinelle AI `U+200B`, gestione Echo, camera destra proporzionale a `Max Health`, inizializzazione fallback e cleanup globale con `TeksDiriPemain`.

## Editor Workshop.codes

Esito: importazione della versione `0.4.0` superata nel progetto temporaneo; il comando Compile non ha prodotto errori visibili. Il risultato negli appunti isolati del browser non era leggibile, quindi il paste finale nel client Overwatch resta il controllo decisivo.

- Il file completo è stato importato in un progetto temporaneo non autenticato.
- L'editor ha riconosciuto correttamente variabili, 12 subroutine e tutte le 33 regole della `0.4.0`.
- Il comando Compile è stato eseguito senza segnalazioni di errore; il browser temporaneo non esponeva il contenuto copiato dal sito.
- Sono stati accettati i quattro menu separati, le 20 sfumature `Color`/`Custom Color`, la selezione camera costruita da `All Players(All Teams)`, i testi bilingui con `Player Variable(Local Player, IndeksBahasa)` e l'inizializzazione comune dei giocatori.
- Sono stati accettati `Update Every Frame`, `Player Closest To Reticle`, `Disable/Enable Nameplates`, i due testi Crouch con `Ultimate Charge Percent`, la sentinella `U+200B`, la subroutine persistente per i bot e le azioni che azzerano danno, cura e knockback.
- Tutte le chiamate `Create HUD Text` usano `Header = Null`; il validatore impedisce inoltre la posizione HUD non valida `Bottom`.
- Il sorgente contiene esattamente due `U+200B`, richiesti dal rilevamento live dei normali bot AI; il validatore impedisce che vengano rimossi o trasformati in stringhe vuote.
- Il progetto temporaneo è stato chiuso e non salvato online.

L'import della `0.4.0` ha confermato specificamente: 33 regole, 12 subroutine, 10 definizioni HUD, titolo server, `Player Closest To Reticle`, `Disable/Enable Nameplates`, due `Create In-World Text`, `Ultimate Charge Percent`, menu sotto l'Objective Description e camera dinamica 3,5–6 m sulla spalla destra.

## Correzione filtro commenti del client

- Il client live ha rifiutato la versione `0.3.0` con `Invalid comment after 'rule(' on line 1114`.
- La sintassi della riga era valida, ma il nome della regola conteneva la parola indonesiana `cuma`; la sottostringa inglese iniziale veniva bloccata dal filtro parole di Overwatch.
- La versione `0.3.1` usa `Kunci bot, kaki tetap bisa bergerak` e il validatore controlla i frammenti già noti per evitare la stessa regressione nei nomi delle regole.
- Il renderer monolitico `GambarMenu` è stato inoltre trasformato in un router verso cinque subroutine più piccole; le schermate e gli input restano identici.

## Riscontro storico dal client Overwatch

- La versione `0.1.1` veniva riconosciuta dagli appunti, ma il client live rifiutava il blocco `settings` minimale con `Expected modes ... on line 7`.
- La versione `0.1.2` ha rimosso intenzionalmente tutto il blocco `settings`: il sorgente va incollato dalla schermata Workshop e lascia intatte modalità, mappe e impostazioni lobby.
- Il client live ha poi segnalato `Expected a comparison operator ... on line 628`; dalla versione `0.1.3` il risultato della condizione OR viene confrontato esplicitamente con `True`.
- Il test live della versione `0.2.0` ha mostrato che una stringa davvero vuota non identifica i bot AI: entravano nelle liste e non ricevevano il blocco combattimento. Lo stesso test ha evidenziato che il raycast Crouch limitato a `PemainManusia` non poteva vedere i bot.
- La versione `0.2.1` ha introdotto la sentinella reale `U+200B`, il blocco persistente dei bot e il raycast Crouch su `All Players(All Teams)`.

## Non ancora verificato nel client live

- Incolla della versione `0.4.0` nel client Overwatch 2.
- Comportamento della sentinella `U+200B` sulla patch live.
- Disabilitazione attacchi su dummy e bot AI normali.
- Presenza di umani, AI e dummy nella selezione camera e gestione del bersaglio che esce.
- Rivalutazione per-viewer inglese/indonesiano con due client reali.
- Rivalutazione delle 20 sfumature sulle due liste `Subheader`, nel menu e sui due testi nel mondo.
- Inizializzazione di ingressi tardivi e giocatori già presenti; cleanup dopo join/leave ripetuti.
- Titolo Friendly Dedicated Server, posizione Indonesia localizzata e menu sotto l'Objective Description a diverse risoluzioni.
- Hide/restore delle nameplate per-viewer, target più vicino al reticolo e ULT% di viewer e bersaglio.
- Carico con 12 giocatori e più camere attive.
- Collisioni e distanza 3,5–6 m della camera destra sulle mappe e sugli eroi scelti.

La matrice completa è in `docs/TEST.md`.
