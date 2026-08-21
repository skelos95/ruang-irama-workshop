# Importazione Workshop con client Overwatch in italiano

Questa guida riguarda l'importazione tramite **copia/incolla del testo Workshop** nel client Overwatch con lingua testo impostata su Italiano (`it-IT`).

## Correzione importante: il clipboard Workshop è localizzato

Il sorgente canonico del progetto resta in `workshop/ruang_irama.workshop` e usa il formato `en-US`, ma **non è il file da incollare nel client italiano**.

Il parser del clipboard Workshop usa token localizzati. Per `it-IT`, OverPy espone per esempio queste corrispondenze:

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

Anche azioni, valori, enum, eventi e nomi che fanno parte del linguaggio Workshop possono avere una rappresentazione localizzata. Per questo una semplice sostituzione manuale di poche parole non è affidabile.

Il sintomo tipico di una lingua clipboard non compatibile è esattamente quello osservato nel client: **il pulsante arancione di incolla non compare** anche se il testo è presente negli appunti.

## File corretto da copiare

Con client italiano, copia il contenuto di:

`workshop/ruang_irama.it-IT.workshop`

Il file deve iniziare con:

```text
variabili
{
```

e deve contenere regole introdotte da `regola("...")`.

Non copiare `workshop/ruang_irama.workshop` direttamente nel client italiano: quello è il sorgente canonico `en-US` usato per manutenzione e validazione semantica.

## Procedura di copia/incolla

1. Apri `workshop/ruang_irama.it-IT.workshop` dal repository.
2. Apri la vista **Raw** di GitHub, oppure seleziona esclusivamente il contenuto del file.
3. Copia tutto, dalla prima riga `variabili` fino alla graffa finale.
4. Non copiare fence Markdown, numeri di riga o testo della pagina GitHub.
5. In Overwatch: Partita personalizzata > Impostazioni > Workshop.
6. Con il testo italiano negli appunti, il pulsante arancione **Incolla regole** deve comparire nella barra superiore.
7. Premi il pulsante arancione e attendi che il client elabori tutto il file.
8. Apri **Diagnostica script** e registra `Numero totale elementi` e `Regola più grande`.

Se il pulsante arancione non compare nemmeno con il file `it-IT`, fai uno screenshot e conserva il contenuto esatto degli appunti: a quel punto si tratta di un token non riconosciuto o di un errore di sintassi/localizzazione da isolare.

## Come viene mantenuto sincronizzato

`workshop/ruang_irama.it-IT.workshop` è un artefatto generato dal sorgente canonico tramite OverPy, con:

- input: `workshop/ruang_irama.workshop` (`en-US`);
- decompilazione: OverPy con lingua `en-US`;
- ricompilazione: OverPy con lingua `it-IT`;
- output: `workshop/ruang_irama.it-IT.workshop`.

Il file `workshop/ruang_irama.it-IT.manifest` registra l'hash SHA-256 del sorgente canonico e il commit OverPy usato. I test falliscono se il sorgente canonico cambia senza rigenerare la variante italiana.

Non modificare manualmente il file `it-IT`: le modifiche funzionali vanno fatte sul sorgente canonico e poi rigenerate.

## Preflight automatico

Per il sorgente canonico:

```powershell
python tools/check_clipboard_import.py workshop/ruang_irama.workshop --language en-US
```

Per il file italiano:

```powershell
python tools/check_clipboard_import.py workshop/ruang_irama.it-IT.workshop --language it-IT
```

Il checker controlla:

- UTF-8 senza BOM;
- nessun byte NUL;
- nessun fence Markdown;
- parentesi, graffe e quadre bilanciate;
- stringhe chiuse;
- grammatica strutturale coerente con `en-US` oppure `it-IT`;
- nessun miscuglio di token strutturali tra i due profili;
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

1. stai copiando `workshop/ruang_irama.it-IT.workshop`, non il canonico `en-US`;
2. il clipboard inizia con `variabili`;
3. non ci sono ``` o testo della pagina GitHub;
4. non ci sono virgolette tipografiche o caratteri invisibili;
5. esegui il preflight `--language it-IT`;
6. se il checker è verde ma il pulsante arancione non compare, invia uno screenshot e ispezioneremo il primo token non accettato dal client.

## Dopo un import riuscito

Inviare o registrare almeno:

- `Numero totale elementi`;
- `Regola più grande`.

Sono i dati necessari per verificare i limiti reali del client e decidere se serve ulteriore ottimizzazione.
