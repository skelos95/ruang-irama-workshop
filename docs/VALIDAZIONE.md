# Rapporto di validazione

Data: 2026-08-11

## Controlli statici

Esito: superati.

```text
OK - controlli statici superati
Generi: 100 unici | Pagine: 10 | Regole: 23
HUD definiti nel sorgente: 7
```

Il validatore controlla anche la corrispondenza esatta tra l'array nel sorgente e `docs/GENERI.md`, U+200B, gestione Echo, camera, collisione e cleanup HUD globale.

## Editor Workshop.codes

Esito: importazione e compilazione superate.

- Il file completo è stato importato in un progetto temporaneo non autenticato.
- L'editor ha separato correttamente Settings e tutte le 23 regole.
- Il comando Compile è terminato con conferma di copia, senza segnalazioni di errore.
- Il progetto temporaneo è stato chiuso e non salvato online.

## Non ancora verificato

- Incolla nel client Overwatch 2.
- Comportamento del workaround U+200B sulla patch live.
- Posizionamento HUD a diverse risoluzioni.
- Carico con 12 giocatori e più camere attive.
- Collisioni sulle mappe scelte.

La matrice completa è in `docs/TEST.md`.
