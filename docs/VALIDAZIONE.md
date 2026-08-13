# Rapporto di validazione — versione 0.5.4

Data: 2026-08-13

Release: **AFK Dedicated Server 0.5.4 — Season 4: Heroes of Busan**

Questo rapporto separa intenzionalmente ciò che può essere dimostrato sul repository da ciò che richiede il client Overwatch. Un controllo statico superato non certifica stabilità, prestazioni o compatibilità live.

## Controlli statici

**Stato: superati sul sorgente finale della 0.5.4.**

Il gate della release deve essere eseguito sul blob finale di `workshop/ruang_irama.workshop`, insieme alla documentazione e al validatore della stessa revisione. Il controllo comprende:

- struttura sintattica e delimitatori bilanciati;
- tipi evento limitati all'elenco riconosciuto dal Workshop;
- overlay privo di blocco `settings`;
- tre lingue complete e selettore modulo 3;
- 100 generi e 20 colori per lingua;
- placeholder e limiti delle stringhe;
- due sentinelle reali `U+200B`;
- sei menu e navigazione Soundtrack corretta;
- singolo raycast nel percorso camera;
- camera interamente per-frame, nessuna cache/loop server, arretramento pitch-aware, spalla solo yaw, un solo raycast con margine e blend `0`;
- assenza di azioni di score, vittoria o pareggio;
- `Restart Match` usato soltanto allo zero del timer personalizzato;
- invarianti degli array paralleli e pool slot `0..11`;
- CI read-only, senza workflow auto-modificanti.

Comando eseguito dalla radice del repository:

```powershell
& 'C:\Users\Skelos\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' tools\validate_workshop.py
```

Esito:

```text
OK - controlli statici v0.5.4 superati
Generi: 100 | Lingue: 3 | Regole: 48 | Raycast camera: 1
Nota: importazione, stress a 12 giocatori e test modalità restano prove live obbligatorie.
```

Il gate ha confermato, fra gli altri invarianti, 100 generi, tre lingue, un solo raycast camera e l'assenza della pipeline server che vibrava. Non vengono usati come gate rigido i conteggi di subroutine o HUD perché non sono criteri stabili della release.

## Verifiche live

**Stato: pendenti.**

Non sono certificabili dal solo repository:

- reimportazione del blob 0.5.4 nel parser del client Overwatch;
- comportamento del workaround bot AI con `U+200B` sulla patch dell'11 agosto 2026;
- riapplicazione event-driven del blocco bot dopo spawn, respawn e cambio eroe;
- contratto no-score/no-winner e riavvio esclusivo allo zero su Control, Escort, Hybrid, Push, Flashpoint e Clash;
- D.Mon come viewer e target di camera, Crouch, Teleport, Revenge, icona e Ultimate;
- collisioni e posizioni su Busan, Paraíso ed Eichenwalde aggiornate;
- indipendenza per viewer di English, Bahasa Indonesia e ไทย;
- naturalezza, glifi, wrapping e leggibilità dei testi thai;
- cleanup completo dopo almeno 50 cicli join/leave;
- stabilità con 12 umani e con 6 umani + 6 bot;
- 12 camere per 10 minuti e 12 ispezioni Crouch simultanee;
- inquadratura dell'eroe da `-89°` a `+89°`, fluidità durante movimento e collisioni, oltre al comportamento su bersagli remoti;
- `Server Load Average < 80%`, `Server Load Peak < 100%`, assenza di warning/crash e nessuna crescita permanente di HUD/IWT;
- diagnostica visibile soltanto all'host quando attiva e completamente inattiva quando disabilitata.

La procedura dettagliata e i criteri di accettazione sono in [`TEST.md`](TEST.md).

## Compatibilità Season 4

La release prende come riferimento le [Overwatch Retail Patch Notes — August 11, 2026](https://us.forums.blizzard.com/en/overwatch/t/overwatch-retail-patch-notes-%E2%80%93-august-11-2026/1032368). La presenza di D.Mon e gli aggiornamenti di Busan, Paraíso ed Eichenwalde sono inclusi nella matrice live, non dichiarati automaticamente compatibili dal controllo statico.

## Riscontri storici ancora rilevanti

- Un blocco `settings` minimale era stato rifiutato dal client; il progetto resta intenzionalmente un overlay Workshop senza quel blocco.
- Il parser live può filtrare sottostringhe nei nomi delle regole anche quando la sintassi è valida; i nomi personalizzati vanno quindi ricontrollati durante l'import.
- Una stringa realmente vuota non distingueva i normali bot AI. Le due sentinelle `U+200B` devono restare byte reali nel file e il loro comportamento va verificato a ogni patch.
- L'import live della 0.5.0 si interrompeva con `Expected an event type after 'event {' on line 702`: `Player Spawned` non è un tipo evento Workshop valido. La 0.5.1 usa transizioni `Ongoing - Each Player` per morte/despawn e ritorno in vita, e il validatore ora rifiuta qualsiasi tipo evento fuori dall'elenco supportato.
- Il test live della 0.5.2 ha confermato ondulazione e vibrazione: la causa era la combinazione fra traslazione client per-frame, offset/collisione aggiornati dal server e blend `80`. La 0.5.3 ha eliminato quella pipeline e il test live ne ha confermato la fluidità.
- La 0.5.3 manteneva però l'arretramento della camera solo sul piano orizzontale mentre il punto osservato seguiva il pitch completo: guardando molto in alto o in basso l'eroe usciva dall'inquadratura. La 0.5.4 rende pitch-aware il braccio posteriore e lascia orizzontale soltanto la spalla; il risultato visivo resta da verificare nel client.
- Bot esclusi dalle liste sociali possono comunque essere target validi per camera, Crouch e Teleport; i test devono coprire entrambe le proprietà.

## Decisione di rilascio

Il repository può superare il gate statico prima delle prove live, ma ciò non autorizza a descrivere la 0.5.4 come verificata a 12 giocatori o con inquadratura corretta su ogni client. Un codice Blizzard condivisibile richiede il completamento della matrice live con lo stesso sorgente validato staticamente.
