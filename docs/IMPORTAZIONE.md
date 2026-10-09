# Importare il Workshop

## Procedura

1. Salva il preset con le tue mappe e imposta la lingua testo di Overwatch su **English**.
2. Apri il codice corrente di `main`, [ruang_irama.en-US.workshop](../workshop/ruang_irama.en-US.workshop), e scegli **Raw**. La versione resta **0.8.2**; il margine inferiore di HOST è una correzione successiva alla release pubblicata.
3. Copia tutto, da `variables` alla graffa finale, senza numeri di riga o testo della pagina GitHub.
4. In **Custom Game → Settings → Workshop**, usa **Paste Rules**.
5. Apri **Script Diagnostics** e annota Element Count e Largest Rule, insieme al commit importato.
6. Configura Skirmish, mappe standard escluse quelle Workshop e durata 10–60 minuti. Le regole non includono il preset delle mappe.

L'unico codice da importare usa la grammatica nativa inglese. Anche identificatori, nomi delle regole, commenti, menu, HUD, messaggi e impostazioni personalizzate sono in inglese. Non tradurre manualmente le keyword. Al primo spawn il principale si apre sulla voce 0, Info / Controls; Crouch + Interact mostra la guida completa ai comandi.

Le 127 regole sono numerate da 0 a 126 nell'ordine del file, senza ripetizioni né suffissi alfabetici. Questa numerazione è distinta da quella delle voci del menu.

Con Info 0 selezionata nel principale, titolo e anteprima sono interamente nel sottotitolo (`Subheader`), per una visualizzazione più piccola, e il corpo (`Text`) è vuoto. L'anteprima mostra i binding per Camera, Arcade, ispezione eroe/HP, navigazione e apertura della guida completa. Il sottomenu Info mantiene titolo e tutti i dodici comandi nel `Subheader`, con i binding reali del giocatore e senza duplicazioni. Le altre voci e pagine mostrano i comandi contestuali nel sottotitolo e funzioni/opzioni nel corpo. HOST usa una sola riga, senza spazio sopra e con una riga vuota sotto per il killfeed. L'utente ha verificato e confermato questa distanza nel gioco il 9 ottobre, dopo la PR #105.

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
