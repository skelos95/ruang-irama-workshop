# Rapporto di validazione — versione 0.5.5

Data: 2026-08-14

Release: **AFK Dedicated Server 0.5.5 — Stabilizzazione non-camera**

Stato release: **static-ready, live-pending**.

Questo rapporto separa intenzionalmente ciò che può essere dimostrato sul repository da ciò che richiede il client Overwatch. Un gate statico superato non certifica importazione, stabilità, prestazioni o compatibilità live.

## Revisione validata

Il gate deve riferirsi all'esatto blob Git di `workshop/ruang_irama.workshop` usato dalla release:

```text
6650e06bb8a735fb93c04944a38c04fa348085f0
```

Il valore sopra è l'oggetto staged restituito da `git rev-parse :workshop/ruang_irama.workshop` dopo l'ultima modifica. Dopo il commit deve coincidere con `git rev-parse HEAD:workshop/ruang_irama.workshop`; la CI va eseguita su quell'esatto commit.

## Controlli statici

**Stato: superati sul tree di release 0.5.5; verifica live ancora pendente.**

Il gate comprende:

- sintassi, `[]` e nesting dei delimitatori;
- regole e dichiarazioni ben formate, senza nomi o slot duplicati;
- tipi evento limitati all'elenco riconosciuto dal Workshop;
- overlay privo di blocco `settings`;
- tre lingue complete, selettore modulo 3 e stato vuoto Revenge localizzato;
- 100 generi, 20 colori per lingua e placeholder con arità coerente;
- due sentinelle reali `U+200B` per i normali bot AI;
- sei menu e navigazione Soundtrack corretta;
- invarianti di chiusura Melee e cleanup su morte, despawn, hero-select e spettatore;
- selezione Crouch candidate-first con line-of-sight e ordinamento angolare;
- sincronizzazione nameplate per umani e bot aggiunti durante un'ispezione attiva;
- cattura per identità della destinazione Teleport prima del refresh;
- invarianti degli array paralleli e pool slot HUD `0..11`;
- assenza di azioni di score, vittoria o pareggio e `Restart Match` confinato allo zero del timer;
- camera invariata rispetto a `main@02bcedc`, con un solo raycast nel percorso per-frame;
- controlli semantici eseguiti sul codice, senza accettare token simulati dentro stringhe o commenti;
- workflow read-only eseguito per ogni modifica alla repository.

I test negativi `unittest` coprono commenti/stringhe che simulano azioni, cattura cleanup mancante, delimitatori e regole malformati, duplicati, localizzazione incompleta, placeholder con arità errata e regressioni Crouch/Teleport.

Comandi da eseguire dalla radice del repository con Python 3.12:

```powershell
python -m unittest discover -s tests -p 'test_*.py'
python tools/validate_workshop.py
```

Runtime usato per il gate locale registrato: **Python 3.12.13**.

Esito della suite negativa:

```text
Ran 20 tests
OK
```

Esito del validatore:

```text
OK - controlli statici v0.5.5 superati
Generi: 100 | Lingue: 3 | Regole: 49 | Raycast camera: 1
Nota: importazione, stress a 12 giocatori e test modalità restano prove live obbligatorie.
```

Il workflow non usa filtri `paths`, imposta `permissions.contents: read` e `persist-credentials: false`, quindi ogni modifica alla repository attraversa il gate senza lasciare credenziali Git nel checkout. Le Actions sono fissate ai commit completi:

- `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1` (`v7.0.1`);
- `actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97` (`v7.0.0`).

## Invarianti della camera

La release 0.5.5 non modifica logica, parametri, raycast, comportamento o menu della camera in terza persona. Il confronto con `main@02bcedc` deve risultare senza differenze per i blocchi Workshop della camera. La matrice live della camera resta necessaria come smoke test, non come giustificazione per cambiare la geometria in questa release.

## Verifiche live

**Stato: pendenti. Nessuna delle prove seguenti è dichiarata completata dal gate statico.**

- importazione dello stesso blob nel parser del client Overwatch;
- morte a `0,10`, `0,25` e `0,49` secondi durante la chiusura del menu con Melee premuto;
- Crouch con target morto, dietro parete e non spawnato mentre esiste un secondo target valido;
- registrazione/spawn di umani e bot mentre dodici viewer tengono Crouch;
- menu e Crouch durante cambio round, hero-select, despawn e passaggio team ↔ spettatore;
- uscita simultanea della destinazione Teleport senza retarget sul nuovo elemento dello stesso indice;
- comportamento del workaround bot AI `U+200B` e del lifecycle edge-triggered dei dummy;
- indipendenza per viewer di English, Bahasa Indonesia e ไทย, incluso lo stato vuoto Revenge;
- contratto no-score/no-winner su Control, Escort, Hybrid, Push, Flashpoint e Clash;
- D.Mon e geometrie aggiornate di Busan, Paraíso ed Eichenwalde;
- 50 cicli join/leave e stress a 12 player senza crescita permanente di HUD/IWT;
- soglie `Server Load Average < 80%` e `Server Load Peak < 100%`, senza warning o crash;
- smoke test della camera invariata su movimento, pitch estremo, collisioni e target remoti.

La procedura dettagliata e i criteri di accettazione sono in [`TEST.md`](TEST.md).

## Semantica Revenge preservata

Il menu Revenge continua intenzionalmente a mostrare tutti gli altri umani, anche quando il loro debito è `0`. In quel caso il claim resta bloccato. La 0.5.5 localizza anche lo stato in cui non esistono altri umani, senza cambiare questa semantica.

## Decisione di rilascio

Il repository è classificato **static-ready, live-pending**. Un codice Blizzard condivisibile richiede il completamento dell'intera matrice live con lo stesso blob registrato sopra; fino ad allora non è corretto dichiarare la release verificata nel client o stabile a 12 giocatori.
