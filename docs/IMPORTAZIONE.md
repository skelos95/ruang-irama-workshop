# Importare il Workshop

## Procedura

1. Salva il preset con le tue mappe e imposta la lingua testo di Overwatch su **English**.
2. Apri il codice della revisione desiderata, [ruang_irama.en-US.workshop](../workshop/ruang_irama.en-US.workshop), e scegli **Raw**. La versione nominale resta **0.8.3**; il codice corrente include i menu sociali **Unreleased**. Il tag e l'allegato v0.8.3 conservano il pacchetto pubblicato, senza queste modifiche successive; anche la release storica 0.8.2 conserva il contenuto pubblicato.
3. Copia tutto, da `variables` alla graffa finale, senza numeri di riga o testo della pagina GitHub.
4. In **Custom Game → Settings → Workshop**, usa **Paste Rules**.
5. Apri **Script Diagnostics** e annota Element Count e Largest Rule, insieme al commit importato.
6. Configura Skirmish, mappe standard escluse quelle Workshop e durata 30–60 minuti. Le regole non includono il preset delle mappe.

L'unico codice da importare usa la grammatica nativa inglese. Anche identificatori, nomi delle regole, commenti, menu, HUD, messaggi e impostazioni personalizzate sono in inglese. Non tradurre manualmente le keyword. Al primo spawn il principale si apre sulla voce 0, Info / Controls; Crouch + Interact mostra la guida completa ai comandi.

Le 136 regole sono numerate da 0 a 135 nell'ordine del file, senza ripetizioni né suffissi alfabetici. Questa numerazione è distinta da quella delle 21 voci del menu, da 0 a 20.

Il tema Nocturne mostra `cozywatch.org [countdown]`, il roster `SOULS & ECHOES` e il leader `CROWN OF ASH`. Argento lunare e toni osso accompagnano i testi ispirati al romanticismo oscuro; titolo, HOST, effetti Luck e anello Multijump usano il ciclo RGB arcobaleno originale di 51 secondi. Il tema dei menu è conservato; le [40 scelte Name Color](NAME_COLORS.md) conservano gli indici con nomi a tema e 34 valori RGB aggiornati. Verifica nel client leggibilità e testi della revisione importata.

Con Info 0 selezionata nel principale, titolo e anteprima sono interamente nel sottotitolo (`Subheader`), per una visualizzazione più piccola, e il corpo (`Text`) è vuoto. L'anteprima mostra i binding per Camera, Arcade, ispezione eroe/HP, navigazione e apertura della guida completa. Il sottomenu Info mantiene titolo e la guida completa nel `Subheader`, con i binding reali del giocatore e senza duplicazioni. Anteprima e guida restano bianche subito, anche dopo Interact, indipendenti dal Name Color e dal ciclo RGB. Le altre voci e pagine mostrano i comandi contestuali nel sottotitolo e funzioni/opzioni nel corpo. HOST usa una sola riga, senza spazio sopra e con una riga vuota sotto per il killfeed. L'utente ha verificato e confermato questa distanza nel gioco il 9 ottobre, dopo la PR #105.

I file in `source/` e `tests/fixtures/` sono specifiche e riferimenti interni dei test. Importa soltanto il file `.workshop` pubblico: contiene il runtime globale generato.

La revisione aggiunge Crouch + Ultimate per ripristinare la sola pagina dove il comando è mostrato; Speed e Gravity usano passi 20/100, con Speed 20–1000%. Le icone seguono il proprietario entro 5 m tridimensionali; i dummy restano fermi dopo il teletrasporto iniziale sicuro e si orientano verso il nemico vivo più vicino con Dummy Target ON. Il reset non è disponibile in Info, Revenge, Luck e toggle 8/9/12/15, né sul Soundtrack Draconian bloccato. [Default e pagine abilitate](../README.md#menu-personali).

Le nuove pagine sono **Presence 17**, stato sociale manuale nel roster; **Fates 18**, moneta/dadi/presagi locali con cooldown di 5 secondi; **Whispers 19**, messaggi predefiniti a un umano pubblico mirato a qualsiasi distanza, con mira entro 12°, linea di vista, ricezione ON e cooldown di 15 secondi; **Moonlit Aura 20**, tre aure personali e filtro delle aure altrui. Verificare il ritorno con Crouch + Reload da ciascuna pagina: nessun passaggio visibile a Moonlit Aura prima del principale. Fates mostra il risultato soltanto in un HUD privato sotto Arcade, con una riga vuota prima del testo e durata di 3–4 secondi; nel menu resta lo stato READY/RESTING. Crouch + Ultimate ripristina anche queste pagine senza cancellare i cooldown e rimuove il risultato temporaneo Fates. Le aure hanno un limite di un effetto per umano, massimo 12, e richiedono una verifica visiva e di cleanup nel client. [Matrice delle nuove funzioni](TEST.md#presence-fates-whispers-e-moonlit-aura).

Applicare o alternare Ghost modifica soltanto la collisione con l'ambiente e conserva l'inerzia; Fly continua a gestire la propria fisica. Il 28 ottobre l'utente ha confermato «funziona tutto» dopo la PR #114; SHA importato, build client, numero di player, durata e metriche native non sono stati forniti. La successiva correzione Ghost e i nuovi menu sociali richiedono una nuova prova sul commit importato: [matrice Ghost e Fly](TEST.md#jump-ghost-e-fly).

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
