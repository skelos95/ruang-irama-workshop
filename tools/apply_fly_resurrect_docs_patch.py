from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch(path_name: str, replacements: list[tuple[str, str]]) -> None:
    path = ROOT / path_name
    text = path.read_text(encoding="utf-8")
    for old, new in replacements:
        count = text.count(old)
        if count != 1:
            raise SystemExit(f"{path_name}: expected 1 occurrence, found {count}: {old[:80]!r}")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")


patch("README.md", [
    (
        "- Resurrect manuale con Jump da morto: mantiene esattamente la posizione di morte quando sotto esiste terreno valido; soltanto una caduta nel vuoto usa `Nearest Walkable Position` e un `Teleport` condizionale verso il punto sicuro, senza ricorrere a `Respawn`.",
        "- Resurrect manuale con Jump da morto: usa sempre `Nearest Walkable Position` rispetto al punto di morte, valida il punto sicuro, teletrasporta il cadavere e poi usa `Resurrect`, senza `Respawn` né fallback alla Spawn Room.",
    ),
    (
        "**Fly** imposta la gravità a zero e trasforma il throttle WASD rispetto alla direzione completa dello sguardo: avanti segue il mirino anche verso l'alto o il basso, indietro usa la direzione opposta e gli input laterali permettono lo strafe. Senza input, un impulso esattamente contrario alla velocità residua arresta il player senza deriva o fluttuazione.",
        "**Fly** imposta la gravità a zero e trasforma il throttle WASD rispetto alla direzione completa dello sguardo: avanti segue il mirino anche verso l'alto o il basso, indietro usa la direzione opposta e gli input laterali permettono lo strafe. Tenendo avanti, la rampa normale accelera gradualmente a `6 m/s²` fino a `20 m/s`; Try Your Luck: Acceleration mantiene la priorità. Senza input, un impulso esattamente contrario alla velocità residua arresta il player senza deriva o fluttuazione.",
    ),
    (
        "| Morto | Jump | Resurrect nello stesso punto; se la morte è nel vuoto, `Teleport` condizionale alla `Nearest Walkable Position` sicura |",
        "| Morto | Jump | `Teleport` alla `Nearest Walkable Position` sicura più vicina, poi `Resurrect`; mai fallback alla Spawn Room |",
    ),
    (
        "Il terreno sotto il punto di morte viene verificato nello stesso tick: se è valido, il Resurrect nativo conserva esattamente quel punto senza `Teleport`; se è vuoto, il runtime calcola e valida la `Nearest Walkable Position`, teletrasporta lì il cadavere e poi esegue `Resurrect`. Un fallback allo spawn viene usato soltanto se disponibile e validato; senza alcun terreno sicuro il player resta morto.",
        "Nello stesso tick il runtime calcola sempre una `Nearest Walkable Position` a partire dal punto di morte, la passa dalla validazione di sicurezza, teletrasporta lì il cadavere e poi esegue `Resurrect`. Non esiste più alcun fallback alla Spawn Room; se non viene trovato un terreno sicuro, il player resta morto e può riprovare dopo aver rilasciato Jump.",
    ),
])

patch("docs/PROGETTO.md", [
    (
        "Senza input e senza un effetto Acceleration esplicito, Fly annulla la velocità residua.",
        "Tenendo avanti, Fly usa una rampa normale di `6 m/s²` fino a `20 m/s` lungo la direzione completa della mira; senza input e senza un effetto Acceleration esplicito, annulla la velocità residua.",
    ),
    (
        "- Da morto, un menu aperto resta visibile ma congelato; soltanto Jump esegue `Resurrect`. Se un raycast corto trova terreno sotto `PosisiMati`, il Resurrect nativo conserva esattamente il punto di morte. Soltanto nel vuoto viene calcolata e validata una `Nearest Walkable Position`, con fallback allo spawn: dopo la conferma `Is Alive == True`, un unico `Teleport` condizionale applica il punto sicuro. Il ramo non usa `Respawn`, offset casuali o `Wait`. Se il player è ancora morto, una regola separata riapre il latch esclusivamente al rilascio di Jump.",
        "- Da morto, un menu aperto resta visibile ma congelato; soltanto Jump esegue il recupero. Il runtime calcola sempre `Nearest Walkable Position(PosisiMati)`, valida il candidato, teletrasporta il cadavere prima di `Resurrect` e non usa alcun fallback alla Spawn Room. Dopo `Is Alive == True` ripristina gli effetti, disarma il latch fisico e riapplica immediatamente Ghost/Fly. Il ramo non usa `Respawn`, offset casuali o `Wait`; se non esiste terreno sicuro il player resta morto e una regola separata riapre il latch esclusivamente al rilascio di Jump.",
    ),
])

patch("docs/TEST.md", [
    (
        "il cooldown Self Kill e il recupero sicuro del Resurrect nel vuoto",
        "il cooldown Self Kill, il Resurrect sempre su `Nearest Walkable Position` e la riapplicazione Fly post-morte",
    ),
    (
        "| Morto | Jump | `Resurrect`; stesso punto se sicuro, `Nearest Walkable Position` se morto nel vuoto; menu ancora visibile |",
        "| Morto | Jump | `Teleport` alla `Nearest Walkable Position` validata e poi `Resurrect`; nessuna Spawn Room; menu ancora visibile |",
    ),
    (
        "Sul caso Jump, verificare due rami distinti. Su terreno valido il player deve riapparire esattamente nella posizione di morte, senza `Teleport`; dopo una morte nel vuoto deve invece essere eseguito un solo `Teleport` condizionale del cadavere verso una `Nearest Walkable Position` già validata, seguito da `Resurrect`. Provare sia una caduta vicina al bordo sia un vuoto profondo: se il primo candidato fallisce, il fallback allo spawn deve essere usato soltanto quando disponibile e dopo la stessa validazione. Se non esiste alcun punto sicuro, il player deve restare morto invece di entrare in un ciclo di morti.",
        "Sul caso Jump, provare morte su terreno normale, vicino a un bordo e nel vuoto profondo. In tutti i casi deve essere calcolata una `Nearest Walkable Position`, validata e usata da un solo `Teleport` del cadavere prima di `Resurrect`; non deve comparire alcun percorso verso la Spawn Room. Se non esiste alcun punto sicuro, il player deve restare morto invece di entrare in un ciclo di morti.",
    ),
    (
        "- Con solo Fly ON, verificare gravità zero e collisione ambientale normale. Forward/Back e Left/Right devono muovere lungo la visuale e il relativo strafe 3D: guardando davanti si avanza, guardando in alto si sale e guardando in basso si scende.",
        "- Con solo Fly ON, verificare gravità zero e collisione ambientale normale. Forward/Back e Left/Right devono muovere lungo la visuale e il relativo strafe 3D: guardando davanti si avanza, guardando in alto si sale e guardando in basso si scende. Tenendo Forward, la velocità deve crescere gradualmente con rampa normale `6 m/s²` fino al cap `20 m/s`.",
    ),
    (
        "- Attivare insieme Ghost e Fly, poi disattivarli in ordine inverso: i due toggle devono restare indipendenti; Fly OFF ripristina gravità 100 e ferma il throttle trasformato, Ghost OFF ripristina la collisione ambientale completa.",
        "- Attivare insieme Ghost e Fly, poi disattivarli in ordine inverso: i due toggle devono restare indipendenti; Fly OFF ripristina gravità 100, ferma il throttle trasformato e arresta la rampa normale senza interrompere un'eventuale Luck Acceleration ancora attiva; Ghost OFF ripristina la collisione ambientale completa. Con Fly ON, morire e usare Jump: al ritorno in vita il volo deve funzionare subito senza toggle OFF/ON manuale.",
    ),
])

patch("docs/VALIDAZIONE.md", [
    (
        "- sequenza Jump esatta e senza `Wait`: latch, posizione sicura inizialmente uguale alla morte, raycast corto per distinguere terreno e vuoto, candidato `Nearest Walkable Position` validato con fallback allo spawn, `Resurrect`, conferma `Is Alive` e un unico `Teleport` condizionale soltanto quando il punto sicuro differisce dalla morte; offset casuali, forcing di posizione e `Respawn` sono vietati;",
        "- sequenza Jump esatta e senza `Wait`: latch, `Nearest Walkable Position(PosisiMati)` sempre calcolata e validata, un unico `Teleport` del cadavere prima di `Resurrect`, conferma `Is Alive`, ripristino effetti e riapplicazione immediata Ghost/Fly; fallback alla Spawn Room, offset casuali, forcing di posizione e `Respawn` sono vietati;",
    ),
    (
        "- Fly usa gravità zero e `Start Transforming Throttle(..., Facing Direction Of(player))`, così gli input seguono la visuale in 3D; OFF deve fermare il throttle trasformato e ripristinare gravità 100;",
        "- Fly usa gravità zero e `Start Transforming Throttle(..., Facing Direction Of(player))`, così gli input seguono la visuale in 3D; Forward avvia una rampa `Start Accelerating` da `6 m/s²` con cap `20 m/s`; OFF deve fermare la rampa normale senza interrompere Luck Acceleration, fermare il throttle trasformato e ripristinare gravità 100;",
    ),
    (
        "- toggle e cursori restano distinti, sono OFF soltanto al setup/cleanup reale e persistono durante morte, Resurrect, cambio eroe e cambio squadra leggero;",
        "- toggle e cursori restano distinti, sono OFF soltanto al setup/cleanup reale e persistono durante morte, Resurrect, cambio eroe e cambio squadra leggero; la morte disarma immediatamente il latch fisico e Jump Resurrect riapplica Ghost/Fly nello stesso tick dopo il ripristino effetti;",
    ),
])
