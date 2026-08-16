# Rapporto di validazione — versione 0.6.1

Data: 2026-08-16

Release tecnica: **CHILL Dedicated Server 0.6.1**

Stato corrente: **static-ready, live-pending**.

## Revisione Workshop

Blob Git del sorgente Workshop validato:

```text
244de67a2febf91f2a60de18f82167ecd489c06f
```

## Audit 0.6.1

Il gate verifica:

- struttura Workshop, delimitatori, dichiarazioni e titoli regola senza duplicati;
- inizializzazione esplicita in `SiapkanPemain` di ogni variabile player dichiarata;
- un solo percorso Player Left con cleanup degli array HUD/IWT, slot HUD, voti e riferimenti Camera/Revenge/Teleport/Inspection;
- assenza dello stato morto rimosso (`HudInfoKiri`, `HudInfoKanan`, `WaktuTercatat`, `PosisiKartuNasib`, `ModeKameraSebelumNasib`, `TargetKameraSebelumNasib`);
- 100 generi, 12 menu (`0..11`), 32 Name Color e 37 Player Icon;
- HUD e Small Message EN / Bahasa Indonesia / ไทย, inclusi minuti roster `MIN / MENIT / นาที`;
- titoli regola personalizzati in Bahasa Indonesia;
- Menu 5 OFF / 1 HP / FULL HP: Warning rosso per 1 HP, Halo RGB per FULL HP, Spawn Room reset solo 1 HP;
- Menu 10: bracket + Heart/Skull persistenti, nessun cambio camera, Unkillable OFF, reset morte/leave, 50/50;
- Menu 11: soli umani, self-vote, conteggio event-driven, pareggio = nessuna CHILL STAR;
- Camera con un solo raycast e `MulaiKamera` senza `Stop Camera` immediatamente prima del nuovo `Start Camera`;
- refresh passivi Camera/Revenge/Teleport a 1 Hz, Spawn cache a 1 Hz, minuti lobby a 0,1 Hz, inspection a 4 Hz, RGB globale a 8 Hz;
- workflow consentiti limitati ai due permanenti e nessuna automazione legacy.

## Unit test

```text
Ran 26 tests
OK
```

## Esito validatore registrato

```text
OK - controlli statici v0.6.1 superati
```

## GitHub

Branch operativo: `main` (unico branch del repository al momento dell'audit).

Workflow permanenti:

- `validate-workshop.yml`
- `maintenance-patch.yml`

Non risultano tag o release legacy da sincronizzare. `.github/maintenance/patch.py` è temporaneo e viene eliminato dal workflow di manutenzione dopo il commit validato.

## Verifiche live ancora obbligatorie

- importazione nel client Overwatch;
- tutti i 12 menu in EN / ID / TH;
- join/leave ripetuti e stress con 12 player;
- Camera self/target e cambi target rapidi senza micro-scatto;
- Crouch inspection/Teleport;
- Try Your Luck durante movimento/camera 3P;
- Vote Player con join/leave e pareggi;
- Server Load Average/Peak reale e assenza di crescita permanente HUD/IWT.

## Decisione

Il repository è **static-ready, live-pending**: il gate certifica coerenza strutturale e invarianti automatiche, mentre fluidità reale e stress 12-client restano prove da eseguire nel client Overwatch.
