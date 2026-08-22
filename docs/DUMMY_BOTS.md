# Dummy bot nativi

Il server CHILL crea al massimo **un dummy bot per squadra** quando esiste uno slot libero.

Comportamento atteso:

- eroe casuale;
- respawn massimo di 30 secondi;
- nessun menu Arcade, HUD personale o input offensivo;
- `Damage Dealt = 0`, quindi il dummy non danneggia i player;
- `Damage Received = 100`, quindi i player avversari possono danneggiarlo e ucciderlo normalmente;
- quando resta nella Spawn Room, cerca una destinazione mode-specific vicina all'obiettivo o alla bandiera e teletrasporta soltanto verso una posizione percorribile con terreno valido;
- se la destinazione non è valida, resta in spawn e riprova invece di usare coordinate nulle;
- guarda continuamente il player umano vivo più vicino;
- alla morte interrompe il facing e rientra nel normale ciclo di respawn.

## Destinazioni dalla Spawn Room

- Escort / Hybrid: payload;
- Capture the Flag: bandiera avversaria;
- Push: player vivo sull'obiettivo, con fallback sull'obiettivo corrente;
- altre modalità supportate: obiettivo corrente.

Le regole principali sono `03c`-`03i` e la subroutine `KunciBot`. I test automatici dedicati sono in `tests/test_dummy_bots.py`.
