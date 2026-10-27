# Codice da importare

Codice corrente, versione **0.8.2** e tema **Nocturne**: **[ruang_irama.en-US.workshop](ruang_irama.en-US.workshop)** è l'unico file da copiare nel Workshop, con la lingua testo del client impostata su **English**. Apri **Raw** e copia tutto. Comprende il nuovo tema e la correzione del margine inferiore di HOST successivi alla release 0.8.2; il tag e l'allegato pubblicati conservano il proprio contenuto.

Le 129 regole seguono una numerazione unica da **0 a 128**, nell'ordine del file, senza numeri ripetuti o suffissi alfabetici.

Il codice e l'interfaccia personalizzata sono in inglese. Al primo spawn si apre il menu principale sulla voce **0 — Info / Controls**: Crouch + Interact apre la guida completa. Il titolo centrale conserva il formato originale **cozywatch.org [countdown]** e il ciclo RGB arcobaleno di 51 secondi, condiviso da HOST, effetti Luck e anello Multijump; il roster **SOULS & ECHOES** e il leader dei voti **CROWN OF ASH**. I testi e le tinte malva, argento lunare e osso seguono il romanticismo oscuro; menu, comandi e funzioni restano invariati. La [palette dei 40 Name Color](../docs/NAME_COLORS.md) usa nomi a tema e 34 RGB rivisti; preview, nome e icona applicano il valore esatto selezionato.

Info 0 selezionata nel principale mostra titolo e binding interamente nel sottotitolo (`Subheader`), per una visualizzazione più piccola; il corpo (`Text`) è vuoto. Anche il sottomenu Info usa il `Subheader` per titolo e guida completa, mantenendo tutti i dodici comandi e i binding dinamici senza duplicazioni. Il testo di anteprima e guida resta bianco fisso anche subito dopo Interact, indipendente dal Name Color e dal ciclo RGB. Le altre voci e pagine conservano comandi contestuali nel sottotitolo e funzioni/opzioni nel corpo. HOST usa una sola riga, senza spazio sopra e con una riga vuota sotto per il killfeed.

Il 9 ottobre l'utente ha confermato che il server era stabile, la modalità funzionava e tutto il codice provato superava i test nel gioco. Anche la distanza tra HOST e killfeed è stata verificata e confermata dopo il ripristino del margine inferiore nella PR #105. Questo riscontro storico non verifica il tema Nocturne: la nuova resa visiva richiede una prova nel client.

[Guida di importazione](../docs/IMPORTAZIONE.md) · [Funzioni e comandi](../README.md) · [Controlli della revisione corrente](../docs/VALIDAZIONE.md)
