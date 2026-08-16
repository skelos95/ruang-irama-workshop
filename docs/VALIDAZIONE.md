# Rapporto di validazione — versione 0.6.4

Data: 2026-08-16

Release tecnica: **CHILL Dedicated Server 0.6.4**

Stato corrente: **static-ready, live-pending**.

## Revisione Workshop

Blob Git del sorgente Workshop validato:

```text
c255608fe0b3624a79fea8ff07164141bd408bf0
```

## Audit 0.6.4

- team-switch trattato come leave + fresh join con cleanup riutilizzabile e guardia anti-duplicato roster;
- voto singolo certificato: cambio scelta azzera il target precedente prima di assegnare il nuovo;

Il gate verifica:

- struttura Workshop, delimitatori, dichiarazioni e titoli regola senza duplicati;
- inizializzazione esplicita in `SiapkanPemain` di ogni variabile player dichiarata;
- un solo percorso Player Left con cleanup degli array HUD/IWT, slot HUD, voti e riferimenti Camera/Revenge/Teleport/Inspection;
- assenza dello stato morto rimosso (`HudInfoKiri`, `HudInfoKanan`, `WaktuTercatat`, `PosisiKartuNasib`, `ModeKameraSebelumNasib`, `TargetKameraSebelumNasib`);
- 100 generi, 12 menu (`0..11`), 32 Name Color e 37 Player Icon;
- HUD e Small Message EN / Bahasa Indonesia / ไทย, inclusi minuti roster `MIN / MENIT / นาที`;
- titoli regola personalizzati in Bahasa Indonesia;
- Menu 5 OFF / 1 HP / FULL HP: Warning rosso per 1 HP, Halo RGB per FULL HP, Spawn Room reset solo 1 HP;
- Menu 10: bracket + Heart/Skull persistenti, menu bloccato in pagina 10, FULL HP temporaneo senza perdere l'ultima scelta, verde = ripristino scelta, rosso = OFF + forcing posizione + Light Shaft/Ring RGB in chiusura + morte; cleanup completo morte/leave/team switch;
- Menu 11: soli umani, self-vote, conteggio event-driven, pareggio = nessuna CHILL STAR;
- Camera con un solo raycast, target list limitata a entità esistenti/spawnate/vive e `MulaiKamera` senza `Stop Camera` immediatamente prima del nuovo `Start Camera`;
- refresh passivi Camera/Revenge/Teleport a 1 Hz, Spawn cache a 1 Hz, minuti lobby a 0,1 Hz, inspection a 4 Hz, RGB globale a 8 Hz;
- workflow consentiti limitati ai due permanenti e nessuna automazione legacy.

## Unit test

```text
Ran 33 tests
OK
```

## Esito validatore registrato

```text
OK - controlli statici v0.6.4 superati
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
- Crouch inspection/Teleport, inclusi target morti/non spawnati e disponibilità obiettivo per Escort/Hybrid/CTF/Push;
- Try Your Luck verde/rosso durante movimento e camera 3P, inclusi forcing posizione, Ring/Light Shaft, countdown e cleanup;
- Vote Player con join/leave e pareggi;
- Server Load Average/Peak reale e assenza di crescita permanente HUD/IWT.

## Decisione

Il repository è **static-ready, live-pending**: il gate certifica coerenza strutturale e invarianti automatiche, mentre fluidità reale e stress 12-client restano prove da eseguire nel client Overwatch.


### Hotfix import 0.6.3

- lo slot globale `47` è dichiarato come `IndeksVote`;
- `IndeksHitungSuara` è vietato dal validatore;
- il cambio è nominale e non modifica il tally delle votazioni.
