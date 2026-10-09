# Codice da importare

Codice corrente di `main`, versione **0.8.2**: **[ruang_irama.en-US.workshop](ruang_irama.en-US.workshop)** è l'unico file da copiare nel Workshop, con la lingua testo del client impostata su **English**. Apri **Raw** e copia tutto. Comprende la correzione del margine inferiore di HOST successiva alla release 0.8.2; il tag pubblicato conserva il proprio contenuto.

Le 127 regole seguono una numerazione unica da **0 a 126**, nell'ordine del file, senza numeri ripetuti o suffissi alfabetici.

Il codice e l'interfaccia personalizzata sono in inglese. Al primo spawn si apre il menu principale sulla voce **0 — Info / Controls**: Crouch + Interact apre la guida completa. Il sito **[cozywatch.org](https://cozywatch.org)** compare nell'HUD centrale.

Info 0 selezionata nel principale mostra titolo e binding interamente nel sottotitolo (`Subheader`), per una visualizzazione più piccola; il corpo (`Text`) è vuoto. Anche il sottomenu Info usa il `Subheader` per titolo e guida completa, mantenendo tutti i dodici comandi e i binding dinamici senza duplicazioni. Le altre voci e pagine conservano comandi contestuali nel sottotitolo e funzioni/opzioni nel corpo. HOST usa una sola riga, senza spazio sopra e con una riga vuota sotto per il killfeed.

L'utente conferma che il server è stabile, la modalità funziona e tutto il codice provato supera i test nel gioco. Anche la distanza tra HOST e killfeed è stata verificata e confermata dopo il ripristino del margine inferiore nella PR #105.

[Guida di importazione](../docs/IMPORTAZIONE.md) · [Funzioni e comandi](../README.md) · [Controlli della revisione corrente](../docs/VALIDAZIONE.md)
