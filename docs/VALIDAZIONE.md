# Rapporto di validazione — versione 0.6.13

Data: 2026-08-16

Release tecnica: **CHILL Dedicated Server 0.6.13**

Stato corrente: **static-ready, live-pending**.

## Revisione Workshop

Blob Git del sorgente Workshop validato:

```text
4fa0d5e5e3cc09b42092991c927cc2026fa7f906
```

## Audit 0.6.5

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
- Menu 10: bracket + Heart/Skull persistenti, menu bloccato in pagina 10, FULL HP temporaneo senza perdere l'ultima scelta, verde = ripristino scelta, rosso = OFF + velocità 0 + Light Shaft/Ring RGB in chiusura + morte, senza forcing posizione o knockback lock; morte durante roulette = reset e menu lasciato aperto; cleanup completo leave/team switch;
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
OK - controlli statici v0.6.13 superati
```

## GitHub

Branch operativo e sorgente canonico: `main`.

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
- Try Your Luck verde/rosso durante movimento e camera 3P, inclusi velocità 0 senza forcing, Ring/Light Shaft, countdown, morte anticipata e menu che resta aperto;
- Vote Player con join/leave e pareggi;
- Server Load Average/Peak reale e assenza di crescita permanente HUD/IWT.

## Decisione

Il repository è **static-ready, live-pending**: il gate certifica coerenza strutturale e invarianti automatiche, mentre fluidità reale e stress 12-client restano prove da eseguire nel client Overwatch.


### Hotfix import 0.6.3

- lo slot globale `47` è dichiarato come `IndeksVote`;
- `IndeksHitungSuara` è vietato dal validatore;
- il cambio è nominale e non modifica il tally delle votazioni.

## Hotfix Try Your Luck 0.6.5

Lo status Menu 10 ora mostra lo stato reale della roulette; la morte interrompe e resetta la funzione senza chiudere il menu. Il rosso mantiene Ring/Light Shaft e countdown ma immobilizza esclusivamente tramite velocità a 0, senza forcing posizione né knockback lock.


## Hotfix Respawn Jump 0.6.6

Il gate verifica che la regola `12f - Bangkit Lompat` esista una sola volta e non contenga `Event Player.MenuTerbuka == False;`. In questo modo il respawn con `Jump` resta disponibile anche con Menu Arcade aperto, che deve restare visibile durante morte e respawn.


## Hotfix input da morto 0.6.7

Il gate statico richiede `Is Alive(Event Player) == True` su tutte le regole che eseguono comandi `PerintahMenu == N`, richiede l'azzeramento di `PerintahMenu`/`PerintahTeleportasi` alla morte e certifica che i due attivatori Crouch (inspection e Teleport) siano disponibili solo da vivi. La regola Jump respawn resta invece utilizzabile da morto anche con Menu Arcade aperto.


## Ottimizzazione menu 0.6.8

Il gate verifica release immediato, assenza dei Wait da 0,016 s nel percorso Interact Camera, navigazione primaria senza ricreazione HUD, Crouch Teleport senza redraw per ogni cursor step e transizione colore a 0,18 s. I redraw applicativi Interact restano intenzionalmente disponibili.


## HUD persistente 0.6.9

Il gate richiede un solo HUD runtime dentro `GambarMenu`, creazione lazy e nessuna chiamata ai renderer per-pagina dal router.


## Limite regola Workshop 0.6.10

Il gate impedisce il ritorno del renderer monolitico: `GambarMenu` non può contenere `Create HUD Text` o testi delle pagine, deve restare sotto 12 KB di sorgente e deve inizializzare i 13 renderer split. Ogni renderer deve avere visibilità rivalutata sulla propria `HalamanMenu` e registrare il Text ID in `HudMenuArcade`; `TutupMenu` deve distruggere tutte le 13 pagine. Il valore definitivo del limite compilato resta da verificare nel `Script Diagnostics` del client Overwatch.


## Hold Melee e cache lazy 0.6.11

Il gate richiede un unico opener Melee con `Wait(0.500, Abort When False)` e nessun secondo `Wait` nella stessa regola. `GambarMenu` deve usare `HalamanHudMenuArcade` + `Array Contains` e non può più usare il gate eager `Count Of(HudMenuArcade) == 0` che pre-caricava tutte le pagine. Ogni renderer registra ID e codice pagina nella cache; la chiusura svuota entrambe.


## Controlli input e privacy 0.6.12

Il gate certifica che l'apertura Menu non disabiliti Melee/Jump, che Ability 1/2 restino disabilitate come abilità reali e siano gli unici comandi ±10 del Soundtrack, che il dispatcher/release gate non usino più Jump/Crouch e che il renderer Soundtrack mostri i binding aggiornati. `SegarkanTargetTeleportasi` deve includere il filtro `PrivasiInspeksiAktif == False`.


## Palette menu 0.6.13

Il gate richiede 11 RGB fissi tutti diversi, mantiene Name Color dinamico e conserva `0.180, Destination and Duration`.
