# Importare il Workshop

## Procedura

1. Salva il preset con le tue mappe e imposta la lingua testo di Overwatch su **Italiano**.
2. Apri [ruang_irama.it-IT.workshop](../workshop/ruang_irama.it-IT.workshop) e scegli **Raw**.
3. Copia tutto, da `variabili` alla graffa finale, senza numeri di riga o testo della pagina GitHub.
4. In **Partita personalizzata → Impostazioni → Workshop**, usa **Incolla regole**.
5. Apri **Diagnostica script** e annota Numero totale elementi e Regola più grande, insieme al commit importato.
6. Configura Schermaglia, mappe standard escluse quelle Workshop e durata 10–60 minuti. Le regole non includono il preset delle mappe.

Il clipboard italiano contiene sia keyword localizzate sia token inglesi accettati dal client: non tradurli manualmente. Le lingue EN/ID/TH degli HUD si scelgono nel gioco e non cambiano la grammatica del file.

`tests/fixtures/semantic_reference.txt` è il riferimento inglese interno dei test, non un secondo file da importare.

## Se l'importazione fallisce

| Sintomo | Verifica |
|---|---|
| Pulsante Incolla assente | Il testo completo deve iniziare con `variabili`; ricopia dalla vista Raw. |
| Errore con numero di riga | Conserva testo esatto, screenshot e commit; controlla di non avere incluso numeri di riga o delimitatori Markdown. |
| Categorie/impostazioni vuote o testi HUD vuoti | Salva il preset, chiudi e riapri completamente il gioco, poi reimporta. Se persiste, esporta con **Copia impostazioni** e confronta i testi con il sorgente. |
| Regola troppo lunga o limite elementi | Registra le metriche compilate del client e il messaggio completo. |

Il 27 settembre 2026 il problema dei testi vuoti si presentava anche con una sola impostazione e un HUD di prova; il riavvio completo del gioco ha ripristinato quel test. È un rimedio osservato, non una spiegazione della causa interna. Creare soltanto una nuova lobby non era bastato.

Il controllo locale del formato si esegue dalla radice del repository:

```text
python tools/check_clipboard_import.py workshop/ruang_irama.it-IT.workshop --language it-IT
```

Controlla UTF-8, stringhe, delimitatori, token strutturali e dimensioni testuali. La compilazione effettiva, Element Count e Largest Rule vanno verificati nel client: [limiti e test](TEST.md#metriche-e-rapporto).

[Torna alla guida](../README.md) · [Controlli completi](VALIDAZIONE.md)
