# Dummy bot nativi

Il server CHILL crea al massimo **un dummy bot per squadra** soltanto quando esistono uno Spawn Point valido e almeno **due slot liberi**. Il secondo slot resta riservato all'ingresso di un umano: quando la squadra risulta piena con il dummy presente, il bot viene rimosso e non viene ricreato finché non tornano disponibili due slot. In questo modo ogni team conserva capacità per 6 umani e le guardie impediscono spam di `Create Dummy Bot`.

Comportamento atteso:

- eroe casuale;
- respawn massimo di 3 secondi;
- nessun menu Arcade, HUD personale o input offensivo;
- velocità di movimento fissata al **20%** per bot AI e dummy;
- `Damage Dealt = 0` e `Knockback Dealt = 0`, quindi il dummy non danneggia né spinge i player;
- `Damage Received = 100` e `Knockback Received = 100`, quindi riceve normalmente ogni danno e urto;
- quando entra nella Spawn Room, registra una scadenza a 1 secondo; il controllo periodico attende il timestamp senza usare `Wait`, poi cerca una destinazione mode-specific vicina all'obiettivo o alla bandiera e teletrasporta soltanto verso una posizione percorribile con terreno valido;
- se la destinazione non è valida, resta in spawn e prova un candidato diverso al massimo una volta al secondo: otto direzioni orizzontali distanziate di 45°, prima a 8 m e poi a 12 m dall'obiettivo; dopo 16 candidati il cursore individuale riparte da zero;
- prima del teleport la destinazione dummy passa dalla stessa routine body-safe dei player: dopo le correzioni iniziali viene ricontrollato lo spazio libero finale sui quattro lati e sopra la testa; i punti troppo stretti vengono scartati e il punto valido viene rialzato di 0,5 m dal pavimento;
- conserva le collisioni native con pareti, soffitti, pavimenti, umani, bot e altri dummy: le vecchie istruzioni di collisione sono rimosse, senza riapplicazioni a spawn, respawn o cambio eroe;
- fuori dalla Spawn Room considera soltanto umani registrati, spawned, vivi, della squadra avversaria e con Dummy Follow ON; `Sorted Array` seleziona sempre il target idoneo più vicino e il dummy avanza automaticamente nella propria direzione `Forward`, senza dipendere da input direzionali;
- entro 4 m dal nemico porta il throttle a zero; se il nemico si allontana oltre la soglia riparte automaticamente;
- se tutti gli umani nemici validi hanno Dummy Follow OFF, o non esiste alcun target idoneo, interrompe sia facing sia throttle; quando un player torna ON riparte verso il più vicino;
- alla morte interrompe facing e throttle, azzera timestamp e cursore di ricerca e rientra nel normale ciclo di respawn.

Il throttle automatico è riservato ai dummy Workshop; gli iBot conservano collisioni e navigazione AI native, limitate al 20%. Il follow diretto può fermarsi contro un ostacolo: non viene aggiunto un sistema di navigazione intorno alle pareti. Il timestamp viene azzerato alla morte, riarmato al respawn e ripianificato dopo ogni tentativo. Prima di rimuovere un dummy vengono fermati facing e throttle, poi l'entità viene distrutta. La separazione tra guardia di creazione e guardia di rimozione evita il ciclo crea/distruggi quando una squadra oscilla vicino al limite.

## Menu 12 — Dummy Follow

La preferenza è per-player e parte **OFF**. ON consente al dummy avversario di includere quell'umano nella propria selezione; OFF lo esclude senza cambiare la logica nearest-target. Il cambio squadra leggero conserva la preferenza del player; se tutti i target restano OFF, il dummy non insegue nessuno. La stessa condizione di eleggibilità viene usata per avvio, facing, throttle e cleanup, così opt-out, morte o team-switch non lasciano il dummy agganciato a un riferimento obsoleto.

## Destinazioni dalla Spawn Room

- Hybrid prima della cattura: primo obiettivo, anche su Paraíso;
- Escort / Hybrid dopo la cattura: payload;
- Capture the Flag: bandiera avversaria;
- Push: player vivo sull'obiettivo, con fallback sull'obiettivo corrente;
- altre modalità supportate: obiettivo corrente.

Se la destinazione della modalità non è disponibile, viene provato l'obiettivo corrente. La posizione finale deve distare fra 6 e 16 m dal target e superare i controlli di spazio libero e terreno. I tentativi proseguono finché il motore rileva il dummy nella Spawn Room.

Le regole principali sono `03c`-`03i` e la subroutine `KunciBot`. I test automatici dedicati sono in `tests/test_dummy_bots.py` e `tests/test_dummy_spawn_retry.py`; questi ultimi eseguono il flusso reale con risposte geometriche controllate. La verifica della navmesh di Paraíso resta una prova nel client.
