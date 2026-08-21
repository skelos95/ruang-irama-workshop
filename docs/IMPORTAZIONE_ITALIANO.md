# Importazione Workshop con client Overwatch in italiano

Questa guida riguarda l'importazione tramite **copia/incolla del testo Workshop** contenuto in `workshop/ruang_irama.workshop`.

## Regola fondamentale: la sintassi resta in inglese

Anche con Overwatch impostato in italiano, Blizzard mantiene in inglese i vocaboli di programmazione e la sintassi del Workshop. L'interfaccia e le descrizioni possono essere tradotte, ma nel testo da incollare devono rimanere token come:

- `variables`
- `subroutines`
- `rule`
- `event`
- `conditions`
- `actions`
- `Ongoing - Global`
- `Create HUD Text`
- `Filtered Array`
- `Restart Match`
- `Disable Built-In Game Mode Completion`

Non trasformare questi token in `variabili`, `regola`, `evento`, `azioni`, ecc.

I testi mostrati ai giocatori dentro `Custom String(...)` possono invece essere in qualsiasi lingua prevista dal progetto. Anche i nomi personalizzati delle variabili/subroutine restano quelli del sorgente.

## Procedura di copia/incolla

1. Apri `workshop/ruang_irama.workshop` dal repository.
2. Copia **solo il contenuto del file**, dalla prima riga `variables` fino all'ultima graffa finale.
3. Non copiare delimitatori Markdown come ``` e non aggiungere testo prima di `variables`.
4. Nel client Overwatch italiano apri la Partita personalizzata e il relativo editor Workshop.
5. Incolla il testo completo nell'editor con `Ctrl+V`.
6. Se il client rifiuta il paste, non tradurre la sintassi: controlla prima che il testo sia completo e senza virgolette tipografiche/BOM.
7. Dopo l'import, apri **Diagnostica script** e registra i valori effettivi del client.

Il file canonico è UTF-8 senza BOM. Il checker accetta sia terminatori LF sia CRLF, quindi il passaggio attraverso la clipboard di Windows non deve richiedere conversioni manuali.

## Limiti mostrati dal client italiano

Dallo screenshot del client del 21/08/2026:

| Diagnostica | Limite / configurazione mostrata | Politica del progetto |
|---|---:|---|
| Numero totale elementi | massimo `32768` | hard limit client; obiettivo operativo `<= 26000` |
| Regola più grande | deve essere `< 98 KB` | hard limit client; target statico sorgente `<= 80 KB` |
| Combinazioni massime di eroi unici e modelli | `12` | non introdurre dipendenze che richiedano più combinazioni simultanee |
| Bot di prova massimi non in slot giocatore | `0` nella configurazione mostrata | il progetto non deve dipendere da dummy bot extra-slot |

I primi due numeri devono essere verificati **dopo il paste**, perché Element Count e Largest Rule sono metriche compilate dal client e non possono essere certificate con precisione dal parser testuale del repository.

Lo screenshot con sorgente vuoto mostra `0` elementi e `0 KB`: non è ancora una misura del progetto importato.

## Preflight automatico

Prima del test live puoi eseguire:

```powershell
python tools/check_clipboard_import.py
```

Il comando controlla:

- UTF-8 senza BOM;
- nessun byte NUL;
- nessun fence Markdown;
- parentesi, graffe e quadre bilanciate;
- stringhe chiuse;
- blocchi strutturali Workshop in inglese;
- assenza di keyword strutturali italiane nel codice;
- assenza di virgolette tipografiche o NBSP fuori dalle stringhe;
- sorgente che inizia direttamente da `variables`;
- dimensione testuale di ogni `rule`, con target statico massimo di 80 KB.

Le parole italiane dentro `Custom String(...)` sono permesse e non vengono confuse con la sintassi.

## Se l'import fallisce

Controllare in quest'ordine:

1. il testo copiato inizia con `variables` e termina con la graffa finale dell'ultima rule;
2. non ci sono ``` o testo della pagina GitHub nel clipboard;
3. `rule`, `event`, `conditions`, `actions` e le azioni native sono rimaste in inglese;
4. non sono comparse virgolette “tipografiche” al posto di `"`;
5. il file non contiene BOM o caratteri invisibili introdotti da un editor;
6. eseguire `python tools/check_clipboard_import.py`;
7. se il preflight è verde ma Overwatch rifiuta ancora il paste, annotare l'errore del client o fare uno screenshot della finestra di importazione.

## Dopo un import riuscito

Inviare o registrare almeno questi due valori dalla schermata **Diagnostica script**:

- `Numero totale elementi`;
- `Regola più grande`.

Sono i dati necessari per chiudere il gate live rispetto ai limiti reali del client.
