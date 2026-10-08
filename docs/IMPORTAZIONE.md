# Importare il Workshop

## Procedura

1. Salva il preset con le tue mappe e imposta la lingua testo di Overwatch su **English**.
2. Apri [ruang_irama.en-US.workshop](../workshop/ruang_irama.en-US.workshop) e scegli **Raw**.
3. Copia tutto, da `variables` alla graffa finale, senza numeri di riga o testo della pagina GitHub.
4. In **Custom Game → Settings → Workshop**, usa **Paste Rules**.
5. Apri **Script Diagnostics** e annota Element Count e Largest Rule, insieme al commit importato.
6. Configura Skirmish, mappe standard escluse quelle Workshop e durata 10–60 minuti. Le regole non includono il preset delle mappe.

L'unico codice da importare usa la grammatica nativa inglese. Anche identificatori, nomi delle regole, commenti, menu, HUD, messaggi e impostazioni personalizzate sono in inglese. Non tradurre manualmente le keyword. Al primo spawn il principale si apre sulla voce 0, Info / Controls; Crouch + Interact mostra la guida completa ai comandi.

Le 127 regole sono numerate da 0 a 126 nell'ordine del file, senza ripetizioni né suffissi alfabetici. Questa numerazione è distinta da quella delle voci del menu.

Nel principale e negli altri menu i comandi contestuali sono nel sottotitolo (`Subheader`), mentre funzioni e opzioni sono nel corpo (`Text`). Info contiene tutti i comandi nel corpo e non li duplica nel sottotitolo. La leggibilità di questa nuova disposizione va verificata nel client.

I file in `source/` e `tests/fixtures/` sono specifiche e riferimenti interni dei test. Importa soltanto il file `.workshop` pubblico: contiene il runtime globale generato.

## Se l'importazione fallisce

| Sintomo | Verifica |
|---|---|
| Pulsante Paste Rules assente | Il testo completo deve iniziare con `variables`; ricopia dalla vista Raw. |
| Errore con numero di riga | Conserva testo esatto, screenshot e commit; controlla di non avere incluso numeri di riga o delimitatori Markdown. |
| Categorie/impostazioni vuote o testi HUD vuoti | Salva il preset, chiudi e riapri completamente il gioco, poi reimporta. Se persiste, esporta con **Copy Settings** e confronta i testi con il sorgente. |
| Regola troppo lunga o limite elementi | Registra le metriche compilate del client e il messaggio completo. |

Il 27 settembre 2026 il problema dei testi vuoti si presentava anche con una sola impostazione e un HUD di prova; il riavvio completo del gioco ha ripristinato quel test. È un rimedio osservato, non una spiegazione della causa interna. Creare soltanto una nuova lobby non era bastato.

Il controllo locale del formato si esegue dalla radice del repository:

```text
python tools/check_clipboard_import.py workshop/ruang_irama.en-US.workshop --language en-US
```

Controlla UTF-8, stringhe, delimitatori, token strutturali e dimensioni testuali. La compilazione effettiva, Element Count e Largest Rule vanno verificati nel client: [limiti e test](TEST.md#metriche-e-rapporto).

[Torna alla guida](../README.md) · [Controlli completi](VALIDAZIONE.md)
