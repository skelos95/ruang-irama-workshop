# Dummy bot nativi

Il server CHILL crea al massimo **un dummy bot per squadra** soltanto quando esistono uno Spawn Point valido e almeno **due slot liberi**. Il secondo slot resta riservato all'ingresso di un umano: quando la squadra risulta piena con il dummy presente, il bot viene rimosso e non viene ricreato finché non tornano disponibili due slot. In questo modo ogni team conserva capacità per 6 umani e le guardie impediscono spam di `Create Dummy Bot`.

Comportamento atteso:

- eroe casuale;
- respawn massimo di 30 secondi;
- nessun menu Arcade, HUD personale o input offensivo;
- `Damage Dealt = 0`, quindi il dummy non danneggia i player;
- `Damage Received = 100`, quindi i player avversari possono danneggiarlo e ucciderlo normalmente;
- quando entra nella Spawn Room, registra una scadenza a 1 secondo; il controllo periodico attende il timestamp senza usare `Wait`, poi cerca una destinazione mode-specific vicina all'obiettivo o alla bandiera e teletrasporta soltanto verso una posizione percorribile con terreno valido;
- se la destinazione non è valida, resta in spawn e riprova invece di usare coordinate nulle;
- guarda continuamente il player umano vivo più vicino;
- alla morte interrompe il facing e rientra nel normale ciclo di respawn.

Il timestamp viene azzerato alla morte, riarmato al respawn e ripianificato dopo ogni tentativo; quando il dummy viene rimosso scompare con la sua entità. La separazione tra guardia di creazione e guardia di rimozione evita il ciclo crea/distruggi quando una squadra oscilla vicino al limite.

## Destinazioni dalla Spawn Room

- Escort / Hybrid: payload;
- Capture the Flag: bandiera avversaria;
- Push: player vivo sull'obiettivo, con fallback sull'obiettivo corrente;
- altre modalità supportate: obiettivo corrente.

Le regole principali sono `03c`-`03i` e la subroutine `KunciBot`. I test automatici dedicati sono in `tests/test_dummy_bots.py`.
