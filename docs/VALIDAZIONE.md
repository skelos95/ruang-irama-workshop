# Controlli automatici

I controlli del codice corrente, con versione nominale **0.8.3**, tema **Nocturne** e menu sociali **Unreleased**, richiedono **Python 3.12**, senza pacchetti esterni. I controlli vanno associati al commit verificato; il tag e l'allegato v0.8.3 identificano il codice del pacchetto pubblicato, senza includere automaticamente le modifiche successive. Anche la release storica 0.8.2 conserva il contenuto pubblicato. Eseguire dalla radice del repository:

```text
python tools/validate_workshop.py
python tools/build_global_runtime.py --check
python tools/validate_global_runtime.py
python tools/check_clipboard_import.py workshop/ruang_irama.en-US.workshop --language en-US
python -m unittest discover -s tests -p "test_*.py"
git diff --check
```

## Cosa viene controllato

| Area | Verifiche |
|---|---|
| Importazione | UTF-8, stringhe/delimitatori, grammatica inglese, nomi impostazioni validi, dimensioni testuali e budget strutturale |
| Parità | Specifica comportamentale inglese equivalente al riferimento dei test; clipboard generato equivalente al riferimento runtime, distinto dalla specifica |
| Generazione | Ricompilazione deterministica della specifica; rifiuto di output importabile obsoleto o modificato senza rigenerazione |
| Runtime globale | Nessun Each Player, callback solo di registrazione, nessuna attesa nelle subroutine, cattura del proprietario delle espressioni persistenti |
| Struttura | Riferimenti risolti, numerazione delle regole importabili consecutiva a partire da 0, indici compatti, nomi entro 32 byte, regole/variabili/subroutine utilizzate |
| Scheduler | Un solo Loop e un solo Wait centrale; scadenze per comandi/lifecycle, nessuna attesa nelle subroutine, frequenze e condizioni per tipo/stato |
| Risorse | Proprietà degli handle, cleanup canonico, ID riciclati, slot riutilizzabili e isolamento fra player |
| Funzioni | Input, menu Info e apertura iniziale, reset Camera dopo Travel/cambio eroe, Travel/Attach, Resurrect, Ghost con inerzia conservata, Fly a velocità fissa, menu 16 Speed/Gravity con passi 20/100, reset della pagina tramite Crouch + Ultimate, icone personali entro 5 m, Revenge, Unkillable, Luck, Dummy Target fermo e pagine 17–20 Presence/Fates/Whispers/Aura |
| Testi | Codice e interfaccia inglesi, binding e placeholder; titolo e contenuto Info in Subheader, Text vuoto senza `0` e `Color(White)` diretto nella preview e nella guida Info, indipendente da MenuColor; altre voci/pagine con comandi in Subheader e opzioni in Text; testi e palette Nocturne, 40 nomi e vettori RGB allineati con resa esatta della scelta; HOST su una sola riga con il solo margine inferiore; cataloghi e nomenclatura interna, assenza del vecchio sistema lingue/località |
| Repository | Versione nominale, documenti essenziali e unico workflow di sola validazione |

I test comportamentali esistenti eseguono porzioni della specifica inglese con risposte native controllate. Il codice importabile usa la stessa grammatica inglese della specifica. Verificano le funzioni d'ingresso al compilatore e non certificano da soli il runtime globale. Test separati leggono l'output effettivamente importabile e verificano controller, timer, eventi accodati e proprietari catturati. I test di compattazione confrontano gli stessi valori prima/dopo: Booleani tipizzati, palette, testi dei menu e inizializzazione dei registri. Rifiutano coercizioni di numeri in Booleani e verificano che cataloghi, colori e stringhe restino identici. I gate ricompilano la specifica e confrontano entrambi gli output, quindi controllano direttamente contesti, dichiarazioni, attese e peso del runtime. I test di mutazione devono rifiutare ciascuna violazione per la propria causa. Nessuno di questi controlli è un server Overwatch.

I test delle icone eseguono posizioni live del proprietario, teletrasporti, traiettorie interpolate e il limite tridimensionale di 5 m; controllano anche le 36 espressioni Create Icon e la cache di visibilità del clipboard e del riferimento runtime. Le mutazioni devono respingere il ritorno al centro obiettivo e gli offset fuori limite. Le prove del reset verificano isolamento della pagina, default, latch e pagine escluse; il targeting dummy conserva selezione e consenso senza inseguimento.

I nuovi contratti sociali distinguono stato personale, cooldown e risorse persistenti. Il renderer delle pagine 17–20 cattura la sola pagina dell'HUD, evitando il passaggio a Moonlit Aura durante Reload senza congelare cursori o preferenze. Presence aggiorna il roster esistente senza una nuova targhetta. Fates verifica intervalli dei risultati, HUD privato Top 4 con una riga vuota prima del testo, identità e risultato catturati anche dopo lo svuotamento degli attori dello scheduler, TTL 3 secondi e cleanup a 1 Hz entro 4 secondi, reset e ownership canonica dopo perdita delle variabili del proprietario o riciclo degli ID. Il menu mostra READY/RESTING, senza duplicare il risultato. Whispers valida il bersaglio umano a qualsiasi distanza, mira entro 12°, linea di vista, Privacy, ricezione e destinatari esatti; Aura controlla un solo effetto per proprietario, posizione/colore rivalutati, filtro personale e cleanup. Il reset delle pagine 18 e 19 deve conservare la scadenza dei rispettivi cooldown di 5 e 15 secondi. La conferma storica dopo PR #114 non comprende queste nuove funzioni.

Le regressioni Ghost verificano che applicare o alternare la sola collisione non richiami il motore Fly né introduca un freno o alteri velocità e gravità. Le transizioni Fly conservano il proprio applicatore fisico. Il 28 ottobre l'utente ha confermato «funziona tutto» dopo la PR #114, senza SHA importato, build client, numero di player, durata o metriche native; questo riscontro precede la correzione Ghost e non ne verifica la resa nel client.

Le regressioni di ownership includono 240 identità successive sui 12 slot, variabili del leaver perse, eventi tardivi e ID riciclati. Il caso del roster controlla la distruzione di 480 icone senza doppie distruzioni; il registro dei testi temporanei ha prove separate di cleanup e riuso.

Il parser riutilizza la mascheratura delle stringhe tramite una cache limitata a 512 voci, identificata dal contenuto completo. Il risultato è testo immutabile: una modifica al sorgente produce una nuova analisi. Non vengono memorizzati gli esiti della validazione né saltati test o controlli semantici.

Il preflight conta anche le espressioni con pesi ispirati al [compilatore OverPy](https://github.com/Zezombye/overpy/blob/master/src/compiler/astToWorkshop.ts): numeri, accessi alle variabili, confronti, array e parametri impliciti delle stringhe. Colori nominali e RGBA vengono contati nella forma reale, anche quando hanno lo stesso aspetto. Budget locali: **32.000 unità totali, 5.000 per regola**, più un limite testuale autonomo di 80 KB per regola. Titoli, commenti e spazi non contano; spezzare una regola non riduce il totale delle sue espressioni. La cache di questo conteggio è anch'essa limitata a 512 regole e usa il contenuto completo.

Questa è una stima offline, non un compilatore Overwatch né un limite superiore garantito. Non modella tutti i default o l'overhead nativo. Il sorgente `2e1c4ff`, che il client ha mostrato a 36.381 elementi, produce 36.491 unità nella stima e viene rifiutato. Il preflight riporta i conteggi della revisione corrente e li confronta con i budget locali invariati. Il peso del testo UTF-8 viene riportato separatamente: non equivale alla dimensione compilata della regola. Element Count e Largest Rule del nuovo runtime vanno misurati nel client prima delle prove di carico.

Il codice corrente Unreleased usa **30.262 unità strutturali** nel clipboard, massimo 2.789 per regola e 325.518 byte UTF-8; il pacchetto pubblicato 0.8.3 usava 27.496 unità, massimo 2.605 e 299.838 byte. Il nuovo stato sociale occupa un solo array personale: il generato arriva a 128 variabili player, senza aggiungere un campo distinto per ogni scelta. Il registro dedicato dei risultati Fates aggiunge cinque globali e due subroutine, senza nuovi campi player; gli HUD del registro sono inclusi nella diagnostica. I byte del testo sono misurati in UTF-8 con terminatori LF. Le soglie del progetto restano 32.000/5.000; queste misure non sono Element Count o Largest Rule del client.

| Misura corrente | Specifica inglese | Runtime da importare |
|---|---:|---:|
| Regole | 125 | 136 |
| Variabili globali | 87 | 105 |
| Variabili player | 126 | 128 |
| Subroutine | 75 | 122 |
| Byte di testo UTF-8 (LF) | 300.140 | 325.518 |
| Unità strutturali stimate | 27.792 | 30.262 |
| Massimo unità strutturali per regola | 3.137 | 2.789 |

La regola del runtime più grande per testo usa 23.063 byte UTF-8; la regola con più unità strutturali ne usa 2.789. La specifica ha un massimo testuale di 29.490 byte e strutturale di 3.137 unità per regola. Dimensione del testo e peso delle espressioni vengono controllati separatamente.

## GitHub Actions

L'unico workflow presente su `main` è [validate-workshop.yml](../.github/workflows/validate-workshop.yml). Parte sulle pull request, sui push a `main` e manualmente. Usa Actions fissate a SHA e permessi `contents: read`; non modifica né pubblica file. Il registro storico di GitHub può conservare nomi di workflow rimossi: non sono file aggiuntivi presenti nella revisione corrente.

Sei gruppi eseguono tutti i test, distribuendoli deterministicamente per nome. `Whitespace` e `Semantic gates` lavorano in parallelo. `Required checks` passa soltanto quando tutti i gruppi richiesti hanno successo: nove controlli complessivi. Timeout: 20 minuti per gruppo test, 10 per i due gate, 5 per l'aggregatore.

Un nuovo aggiornamento della stessa PR annulla l'esecuzione precedente. Quel vecchio commit può mostrare test annullati e un aggregatore rosso: controllare sempre il commit finale della PR o di `main`. Un'esecuzione annullata non certifica né successo né fallimento del sorgente completo.

## Modificare e verificare

1. Modificare `source/ruang_irama.en-US.source` e la specifica `tests/fixtures/semantic_reference.txt` in modo equivalente. Modificare il compilatore se cambia l'architettura globale.
2. Eseguire `python tools/build_global_runtime.py` per generare il clipboard e il riferimento runtime EN; `--check` verifica senza modificare file.
3. Eseguire i test pertinenti e i due gate; eseguire la suite completa prima dell'unione.
4. Per documentazione e strumenti mantenere collegamenti validi e distinguere stato corrente da risultati storici.
5. Per cambi funzionali importare il commit esatto nel client e registrare il risultato in base a [TEST.md](TEST.md).

Il validatore richiede i documenti essenziali e la storia della versione nominale; non obbliga a dichiarare una revisione “live-ready”. Una versione invariata in `VERSION` non significa che due commit contengano lo stesso Workshop.

## Limiti

I controlli offline non misurano il carico nativo, non compilano il clipboard nel client e non provano assenza di crash/leak. Element Count e Largest Rule compilati, leggibilità di Info e binding, reset Camera, collisioni/mappe, fisica e concorrenza di 12 client richiedono prove nel gioco. Dimensione del testo e numero di chiamate sono indicatori distinti da CPU e memoria del server.

I risultati sono legati alla revisione verificata: consulta i controlli della PR o del commit, senza estendere automaticamente l'esito a modifiche successive. [Stato corrente](../README.md#stato-attuale) · [Architettura](PROGETTO.md)
