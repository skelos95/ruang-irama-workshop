# Importazione Workshop con client Overwatch in italiano

Questa guida riguarda l'importazione tramite **copia/incolla del testo Workshop** nel client Overwatch con lingua testo impostata su Italiano (`it-IT`).

## Il clipboard Workshop è localizzato

Il parser del clipboard Workshop usa token localizzati. Per `it-IT` alcune corrispondenze strutturali sono, per esempio:

| en-US | it-IT |
|---|---|
| `variables` | `variabili` |
| `subroutines` | `subroutine` |
| `rule` | `regola` |
| `event` | `evento` |
| `conditions` | `condizioni` |
| `actions` | `azioni` |
| `global` | `globale` |
| `player` | `giocatore` |

Non tutto però viene tradotto nello stesso modo: diversi token ed enum restano nella forma inglese accettata dal parser italiano. I test live hanno già mostrato, per esempio, che una localizzazione troppo aggressiva dei literal di `Color(...)` può produrre un errore anche quando la struttura generale è riconosciuta.

Per questo il progetto mantiene direttamente il file clipboard italiano e non applica sostituzioni manuali indiscriminate.

## Unico file da copiare

Con client italiano, copia esclusivamente:

`workshop/ruang_irama.it-IT.workshop`

Il file deve iniziare con:

```text
variabili
{
```

e deve contenere regole introdotte da `regola("...")`.

Nel repository non esistono più un secondo `.workshop` inglese né un manifest da scegliere. La fixture `tests/fixtures/semantic_reference.txt` usa grammatica `en-US` soltanto per i test e il validatore semantico: **non è un file destinato all'importazione nel client**.

## Procedura di copia/incolla

1. Apri `workshop/ruang_irama.it-IT.workshop` dal repository.
2. Apri la vista **Raw** di GitHub, oppure seleziona esclusivamente il contenuto del file.
3. Copia tutto, dalla prima riga `variabili` fino alla graffa finale.
4. Non copiare fence Markdown, numeri di riga o testo della pagina GitHub.
5. In Overwatch: Partita personalizzata > Impostazioni > Workshop.
6. Con il testo italiano negli appunti, il pulsante arancione **Incolla regole** deve comparire nella barra superiore.
7. Premi il pulsante arancione e attendi che il client elabori tutto il file.
8. Apri **Diagnostica script** e registra `Numero totale elementi` e `Regola più grande`.

Se il pulsante arancione non compare, oppure compare un errore con numero di riga, conserva lo screenshot e la riga indicata: il client resta l'autorità finale per i token contestuali che non possono essere certificati completamente dal controllo statico.

## Manutenzione del sorgente

`workshop/ruang_irama.it-IT.workshop` è il sorgente Workshop pubblicato e destinato al client italiano. Le modifiche funzionali devono essere applicate a questo file e accompagnate da test che ne verificano le invarianti rilevanti.

La fixture `tests/fixtures/semantic_reference.txt` è una rappresentazione interna in grammatica `en-US` usata dal validatore semantico. Serve a controllare struttura, ownership e invarianti del progetto, ma non viene presentata come file clipboard utente e non sostituisce il test del sorgente italiano.

## Preflight automatico

Per il file destinato al client:

```powershell
python tools/check_clipboard_import.py workshop/ruang_irama.it-IT.workshop --language it-IT
```

La suite completa esegue anche i controlli sul profilo interno `en-US`:

```powershell
python -m unittest discover -s tests -p 'test_*.py'
python tools/validate_workshop.py
```

Il checker controlla:

- UTF-8 senza BOM;
- nessun byte NUL;
- nessun fence Markdown;
- parentesi, graffe e quadre bilanciate;
- stringhe chiuse;
- grammatica strutturale coerente con il profilo selezionato;
- nessun miscuglio di token strutturali tra `en-US` e `it-IT`;
- assenza di virgolette tipografiche o NBSP fuori dalle stringhe;
- dimensione testuale di ogni regola, con target statico massimo di 80 KB.

Questo preflight non sostituisce la compilazione reale del client.

## Limiti mostrati dal client italiano

Dallo screenshot del client del 21/08/2026:

| Diagnostica | Limite / configurazione mostrata | Politica del progetto |
|---|---:|---|
| Numero totale elementi | massimo `32768` | hard limit client; obiettivo operativo `<= 26000` |
| Regola più grande | deve essere `< 98 KB` | hard limit client; target statico sorgente `<= 80 KB` |
| Combinazioni massime di eroi unici e modelli | `12` | non introdurre dipendenze che richiedano più combinazioni simultanee |
| Bot di prova massimi non in slot giocatore | `0` nella configurazione mostrata | il progetto non deve dipendere da dummy bot extra-slot |

`Numero totale elementi` e `Regola più grande` sono metriche compilate dal client e devono essere lette **dopo** un import riuscito.

## Se l'import fallisce

Controlla nell'ordine:

1. stai copiando `workshop/ruang_irama.it-IT.workshop` dalla vista Raw;
2. il clipboard inizia con `variabili`;
3. non ci sono ``` o testo della pagina GitHub;
4. non ci sono virgolette tipografiche o caratteri invisibili;
5. esegui il preflight `--language it-IT`;
6. se il checker è verde ma il client segnala una riga, invia lo screenshot con il numero esatto: il token contestuale va confrontato con la forma realmente accettata dal parser italiano.

## Dopo un import riuscito

Inviare o registrare almeno:

- `Numero totale elementi`;
- `Regola più grande`.

Sono i dati necessari per verificare i limiti reali del client e decidere se serve ulteriore ottimizzazione.
