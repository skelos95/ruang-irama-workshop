# Rapporto di validazione

Data: 2026-08-11

## Controlli statici

Esito: superati.

```text
OK - controlli statici superati
Generi: 100 unici | Pagine: 10 | Regole: 23
HUD definiti nel sorgente: 8
```

Il validatore controlla anche 10 colori unici, menu `0/1/3`, Header nulli, marker nel mondo, freccia colorata, blocco combattimento dei bot, sentinella AI, gestione Echo, camera e cleanup globale.

## Editor Workshop.codes

Esito: importazione e compilazione della versione `0.2.1` superate.

- Il file completo è stato importato in un progetto temporaneo non autenticato.
- L'editor ha riconosciuto correttamente variabili, quattro subroutine e tutte le 23 regole.
- Il comando Compile è terminato con conferma di copia, senza segnalazioni di errore.
- Sono stati accettati `All Players(All Teams)` nel raycast, viewer fisso del testo nel mondo, sentinella `U+200B`, subroutine persistente per i bot e le azioni che azzerano danno, cura e knockback.
- La posizione HUD non valida `Bottom` è stata sostituita con `Top`; il validatore ora impedisce che ricompaia.
- Il sorgente contiene esattamente due `U+200B`, richiesti dal rilevamento live dei normali bot AI; il validatore impedisce che vengano rimossi o trasformati in stringhe vuote.
- Il progetto temporaneo è stato chiuso e non salvato online.

## Riscontro dal client Overwatch

- La versione `0.1.1` veniva riconosciuta dagli appunti, ma il client live rifiutava il blocco `settings` minimale con `Expected modes ... on line 7`.
- La versione `0.1.2` rimuove intenzionalmente tutto il blocco `settings`: va incollata dalla schermata Workshop e lascia intatte modalità, mappe e impostazioni lobby.
- Il client live ha poi segnalato `Expected a comparison operator ... on line 628`; nella versione `0.1.3` il risultato della condizione OR viene confrontato esplicitamente con `True`.
- Il test live della versione `0.2.0` ha mostrato che una stringa davvero vuota non identifica i bot AI: entravano nelle liste e non ricevevano il blocco combattimento. Lo stesso test ha evidenziato che il raycast Crouch limitato a `PemainManusia` non poteva vedere i bot e, con un solo umano, non aveva alcun bersaglio valido.

## Non ancora verificato

- Incolla della versione `0.2.1` nel client Overwatch 2.
- Comportamento della sentinella `U+200B` sulla patch live.
- Disabilitazione attacchi su dummy e bot AI normali.
- Rivalutazione dei 10 colori sulle due liste e sul testo nel mondo.
- Posizionamento HUD a diverse risoluzioni.
- Carico con 12 giocatori e più camere attive.
- Collisioni sulle mappe scelte.

La matrice completa è in `docs/TEST.md`.
