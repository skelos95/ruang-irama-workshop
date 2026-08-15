# Rapporto di validazione — versione 0.5.5

Data: 2026-08-15

Release tecnica: **CHILL Dedicated Server 0.5.5**

Stato corrente: **static-ready, live-pending**.

Questo rapporto descrive il feature set attuale del repository pur mantenendo il numero versione tecnico richiesto dal validatore esistente.

## Revisione Workshop

Blob Git del sorgente Workshop validato:

```text
64447f31db8b097f200babb5b0e131c1a738f825
```

## Controlli statici correnti

Il gate verifica:

- sintassi e struttura Workshop;
- dichiarazioni e regole senza duplicati invalidi;
- 100 generi;
- 3 lingue EN / ID / TH;
- **11 menu Arcade** (`0..10`);
- **32 Name Color** con array nomi allineati;
- **37 Player Icon** (`Nothing` + 36 icone);
- Menu 5 Unkillable/Kebal 1 HP;
- Menu 6 Hero Voice;
- Menu 7 Player Icon;
- Menu 10 Try Your Luck: roulette automatica rosso/verde progressivamente più lenta, verde cura completa, rosso uccide dopo countdown 3 s, esito 50/50;
- Teleport su overlay Crouch, non nel Main Menu;
- feedback menu idempotente;
- transizione colore menu Vector RGB a circa 0,35 s;
- RGB globale pastel/neon lento;
- pool HUD `0..11` e cleanup join/leave;
- cache `SlotHUDTerakhir`;
- Spawn cache 1 Hz;
- minuti lobby ogni 5 s;
- Camera/Revenge/Teleport passivi a 1 Hz;
- Crouch inspection a 5 Hz;
- un solo raycast Camera;
- nomenclatura personalizzata Bahasa Indonesia;
- localizzazione HUD/Small Message nelle tre lingue;
- assenza di scoring/vittoria built-in;
- workflow consentiti limitati ai due permanenti.

## Unit test

```text
Ran 20 tests
OK
```

## Esito validatore registrato

```text
OK - controlli statici v0.5.5 superati
Generi: 100 | Lingue: 3 | Regole: 72 | Raycast camera: 1
```

## Verifiche live ancora obbligatorie

- importazione nel client Overwatch;
- apertura e navigazione di tutti gli 11 menu;
- localizzazione EN / ID / TH;
- 32 Name Color;
- 37 Player Icon;
- transizione colore menu senza sparizione HUD;
- Crouch inspection;
- Teleport Crouch;
- Jump respawn;
- Unkillable entrando/uscendo dallo Spawn Room;
- Hero Voice;
- Try Your Luck con due giocatori: il non proprietario non deve poter attivare la carta;
- feedback audiovisivo solo su cambi reali;
- Camera self/target/first-person;
- join/leave ripetuti;
- stress con 12 player attivi;
- diagnostics host-only;
- wrapping/glifi Thai;
- Server Load reale.

## GitHub

Branch operativo previsto: `main`.

Workflow permanenti previsti:

- `validate-workshop.yml`
- `maintenance-patch.yml`

`.github/maintenance/patch.py` deve essere presente soltanto durante una manutenzione e rimosso al termine.

## Decisione

Il repository è **static-ready, live-pending**. Il gate statico può certificare coerenza strutturale e invarianti controllate, ma non sostituisce una sessione reale Overwatch con 12 player.

- Menu 5: OFF / 1 HP / FULL HP con Halo pubblico indipendente dalla Crouch Privacy.

- Unkillable: transizioni esclusive OFF/1 HP/FULL HP; Spawn Room resetta solo 1 HP, FULL HP persiste.

- Feedback impostazioni: zero effetti audio; entrambe le subroutine usano esclusivamente Ring Explosion RGB.
