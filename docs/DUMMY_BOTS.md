# Dummy bot nativi

Il server CHILL crea al massimo **un dummy bot per squadra** soltanto quando esistono uno Spawn Point valido e almeno **due slot liberi**. Il secondo slot resta riservato all'ingresso di un umano: quando la squadra risulta piena con il dummy presente, il bot viene rimosso e non viene ricreato finché non tornano disponibili due slot. In questo modo ogni team conserva capacità per 6 umani e le guardie impediscono spam di `Create Dummy Bot`.

Comportamento atteso:

- eroe casuale;
- respawn massimo di 30 secondi;
- nessun menu Arcade, HUD personale o input offensivo;
- velocità di movimento fissata al **20%** per bot AI e dummy;
- `Damage Dealt = 0`, quindi il dummy non danneggia i player;
- `Damage Received = 100`, quindi i player avversari possono danneggiarlo e ucciderlo normalmente;
- quando entra nella Spawn Room, registra una scadenza a 1 secondo; il controllo periodico attende il timestamp senza usare `Wait`, poi cerca una destinazione mode-specific vicina all'obiettivo o alla bandiera e teletrasporta soltanto verso una posizione percorribile con terreno valido;
- se la destinazione non è valida, resta in spawn e riprova invece di usare coordinate nulle;
- attraversa pareti e soffitti con `Disable Movement Collision With Environment(Event Player, False)`, mantenendo attiva la collisione con i pavimenti;
- fuori dalla Spawn Room guarda soltanto il player umano vivo della squadra avversaria più vicino e avanza automaticamente nella propria direzione `Forward`, senza dipendere da input direzionali;
- entro 4 m dal nemico porta il throttle a zero; se il nemico si allontana oltre la soglia riparte automaticamente;
- se non esiste un umano nemico vivo interrompe sia facing sia throttle;
- alla morte interrompe facing e throttle, azzera il timestamp e rientra nel normale ciclo di respawn.

Il throttle automatico e la disattivazione delle collisioni ambientali sono riservati ai dummy Workshop; gli iBot conservano collisioni e navigazione AI native, limitate al 20%. Il parametro `Include Floors = False` segue il comportamento documentato nelle [note Blizzard Workshop](https://overwatch.blizzard.com/it-it/news/patch-notes/ptr/2020/08/): muri e soffitti vengono attraversati, i pavimenti restano solidi. Il timestamp viene azzerato alla morte, riarmato al respawn e ripianificato dopo ogni tentativo. Prima di rimuovere un dummy vengono fermati facing e throttle, poi l'entità viene distrutta. La separazione tra guardia di creazione e guardia di rimozione evita il ciclo crea/distruggi quando una squadra oscilla vicino al limite.

## Destinazioni dalla Spawn Room

- Escort / Hybrid: payload;
- Capture the Flag: bandiera avversaria;
- Push: player vivo sull'obiettivo, con fallback sull'obiettivo corrente;
- altre modalità supportate: obiettivo corrente.

Le regole principali sono `03c`-`03i` e la subroutine `KunciBot`. I test automatici dedicati sono in `tests/test_dummy_bots.py`.
