# Controlli automatici

I controlli del codice corrente di `main`, con versione **0.8.2**, richiedono **Python 3.12**, senza pacchetti esterni. La correzione del margine inferiore di HOST è successiva alla release pubblicata; i controlli vanno associati al commit verificato. Eseguire dalla radice del repository:

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
| Struttura | Riferimenti risolti, numerazione delle regole importabili consecutiva 0–126, indici compatti, nomi entro 32 byte, regole/variabili/subroutine utilizzate |
| Scheduler | Un solo Loop e un solo Wait centrale; scadenze per comandi/lifecycle, nessuna attesa nelle subroutine, frequenze e condizioni per tipo/stato |
| Risorse | Proprietà degli handle, cleanup canonico, ID riciclati, slot riutilizzabili e isolamento fra player |
| Funzioni | Input, menu Info e apertura iniziale, reset Camera dopo Travel/cambio eroe, Travel/Attach, Resurrect, Ghost/Fly, Revenge, Unkillable, Luck e dummy |
| Testi | Codice e interfaccia inglesi, binding e placeholder; titolo e contenuto Info in Subheader, Text vuoto senza `0` e colore MenuColor dinamico; altre voci/pagine con comandi in Subheader e opzioni in Text; HOST su una sola riga con il solo margine inferiore; cataloghi e nomenclatura interna, assenza del vecchio sistema lingue/località |
| Repository | Versione nominale, documenti essenziali e unico workflow di sola validazione |

I test comportamentali esistenti eseguono porzioni della specifica inglese con risposte native controllate. Il codice importabile usa la stessa grammatica inglese della specifica. Verificano le funzioni d'ingresso al compilatore e non certificano da soli il runtime globale. Test separati leggono l'output effettivamente importabile e verificano controller, timer, eventi accodati e proprietari catturati. I test di compattazione confrontano gli stessi valori prima/dopo: Booleani tipizzati, palette, testi dei menu e inizializzazione dei registri. Rifiutano coercizioni di numeri in Booleani e verificano che cataloghi, colori e stringhe restino identici. I gate ricompilano la specifica e confrontano entrambi gli output, quindi controllano direttamente contesti, dichiarazioni, attese e peso del runtime. I test di mutazione devono rifiutare ciascuna violazione per la propria causa. Nessuno di questi controlli è un server Overwatch.

Le regressioni di ownership includono 240 identità successive sui 12 slot, variabili del leaver perse, eventi tardivi e ID riciclati. Il caso del roster controlla la distruzione di 480 icone senza doppie distruzioni; il registro dei testi temporanei ha prove separate di cleanup e riuso.

Il parser riutilizza la mascheratura delle stringhe tramite una cache limitata a 512 voci, identificata dal contenuto completo. Il risultato è testo immutabile: una modifica al sorgente produce una nuova analisi. Non vengono memorizzati gli esiti della validazione né saltati test o controlli semantici.

Il preflight conta anche le espressioni con pesi ispirati al [compilatore OverPy](https://github.com/Zezombye/overpy/blob/master/src/compiler/astToWorkshop.ts): numeri, accessi alle variabili, confronti, array e parametri impliciti delle stringhe. Colori nominali e RGBA vengono contati nella forma reale, anche quando hanno lo stesso aspetto. Budget locali: **32.000 unità totali, 5.000 per regola**, più un limite testuale autonomo di 80 KB per regola. Titoli, commenti e spazi non contano; spezzare una regola non riduce il totale delle sue espressioni. La cache di questo conteggio è anch'essa limitata a 512 regole e usa il contenuto completo.

Questa è una stima offline, non un compilatore Overwatch né un limite superiore garantito. Non modella tutti i default o l'overhead nativo. Il sorgente `2e1c4ff`, che il client ha mostrato a 36.381 elementi, produce 36.491 unità nella stima e viene rifiutato. Il preflight riporta i conteggi della revisione corrente e li confronta con i budget locali invariati. Il peso del testo UTF-8 viene riportato separatamente: non equivale alla dimensione compilata della regola. Element Count e Largest Rule del nuovo runtime vanno misurati nel client prima delle prove di carico.

Rispetto al precedente `main` (`fcf7dfd`), il runtime inglese usa **26.336 unità strutturali invece di 31.966 (−17,6%)**, con 2.566 unità nella regola maggiore invece di 4.270. Il clipboard passa da 348.732 a 289.224 byte UTF-8 (−17,1%). Le soglie del progetto restano 32.000/5.000; queste misure non sono Element Count o Largest Rule del client.

| Misura corrente | Specifica inglese | Runtime da importare |
|---|---:|---:|
| Regole | 116 | 127 |
| Variabili globali | 71 | 89 |
| Variabili player | 124 | 126 |
| Subroutine | 66 | 113 |
| Byte di testo UTF-8 | 270.315 | 289.224 |

La regola più grande per testo usa 22.472 byte UTF-8; la regola con più unità strutturali ne usa 2.566. Sono regole diverse: dimensione del testo e peso delle espressioni vengono controllati separatamente.

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
