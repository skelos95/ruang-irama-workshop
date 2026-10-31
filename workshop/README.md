# Codice da importare

Codice corrente, versione nominale **0.8.3**, tema **Nocturne** e menu sociali **Unreleased**: **[ruang_irama.en-US.workshop](ruang_irama.en-US.workshop)** è l'unico file da copiare nel Workshop, con la lingua testo del client impostata su **English**. Apri **Raw** e copia tutto. Il tag e l'allegato v0.8.3 conservano il pacchetto pubblicato, senza queste modifiche successive; anche la release storica 0.8.2 conserva il contenuto pubblicato.

Le 134 regole seguono una numerazione unica da **0 a 133**, nell'ordine del file, senza numeri ripetuti o suffissi alfabetici.

Il codice e l'interfaccia personalizzata sono in inglese. Al primo spawn si apre il menu principale sulla voce **0 — Info / Controls**: Crouch + Interact apre la guida completa. Il titolo centrale conserva il formato originale **cozywatch.org [countdown]** e il ciclo RGB arcobaleno di 51 secondi, condiviso da HOST, effetti Luck e anello Multijump; il roster **SOULS & ECHOES** e il leader dei voti **CROWN OF ASH**. I testi e le tinte malva, argento lunare e osso seguono il romanticismo oscuro; i menu mantengono il proprio tema. La [palette dei 40 Name Color](../docs/NAME_COLORS.md) usa nomi a tema e 34 RGB rivisti; preview, nome e icona applicano il valore esatto selezionato.

Info 0 selezionata nel principale mostra titolo e binding interamente nel sottotitolo (`Subheader`), per una visualizzazione più piccola; il corpo (`Text`) è vuoto. Anche il sottomenu Info usa il `Subheader` per titolo e guida completa, mantenendo la guida completa e i binding dinamici senza duplicazioni. Il testo di anteprima e guida resta bianco fisso anche subito dopo Interact, indipendente dal Name Color e dal ciclo RGB. Le altre voci e pagine conservano comandi contestuali nel sottotitolo e funzioni/opzioni nel corpo. HOST usa una sola riga, senza spazio sopra e con una riga vuota sotto per il killfeed.

Il 28 ottobre l'utente ha confermato «funziona tutto» dopo la PR #114. È un riscontro qualitativo generale, senza SHA importato, build client, numero di player, durata o metriche native. Precede la correzione Ghost e i menu sociali, ancora da verificare nel client. La distanza tra HOST e killfeed era stata verificata e confermata dopo la PR #105.

La revisione aggiunge Crouch + Ultimate per ripristinare la sola pagina dove il comando è mostrato; Speed e Gravity usano passi 20/100, con Speed 20–1000%. Le icone seguono il proprietario entro 5 m tridimensionali; i dummy restano fermi dopo il teletrasporto iniziale sicuro e si orientano verso il nemico vivo più vicino con Dummy Target ON. Il reset non è disponibile in Info, Revenge, Luck e toggle 8/9/12/15, né sul Soundtrack Draconian bloccato. [Default e pagine abilitate](../README.md#menu-personali).

Il principale ha 21 voci: ai menu 0–16 si aggiungono **Presence 17**, stato manuale in Souls & Echoes; **Fates 18**, moneta/dadi/presagi locali; **Whispers 19**, messaggi predefiniti a un umano pubblico mirato; **Moonlit Aura 20**, tre aure personali con filtro delle aure altrui. Mantengono i comandi usuali e il reset di pagina; i cooldown di 5 secondi per Fates e 15 per Whispers non vengono cancellati dal reset. [Prove dei nuovi menu](../docs/TEST.md#presence-fates-whispers-e-moonlit-aura).

Applicare o alternare Ghost aggiorna soltanto la collisione con l'ambiente, conservando l'inerzia e senza richiamare la fisica Fly. Le transizioni Fly continuano a usare il proprio applicatore fisico.

[Guida di importazione](../docs/IMPORTAZIONE.md) · [Funzioni e comandi](../README.md) · [Controlli della revisione corrente](../docs/VALIDAZIONE.md)
