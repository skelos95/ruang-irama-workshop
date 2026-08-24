# Changelog

Le versioni seguono lo stato del sorgente Workshop e della relativa validazione. Un rilascio `static-ready / live-pending` ha superato i controlli automatici, ma richiede ancora l'import e i test nel client Overwatch prima del tag finale `live-ready`.

## 0.8.0 — 2026-08-24

Stato: **live-ready**.

- Runtime riorganizzato attorno a uno scheduler globale a 20 Hz, con attività scalate a 10 Hz, 1 Hz e 0,1 Hz.
- Menu Arcade ridotto a un solo handle HUD attivo per player, senza preload o pagine nascoste.
- Aggiunta pagina `12 - Dummy Follow`: ogni umano può consentire o negare al dummy nemico di sceglierlo; il default è OFF, quindi il dummy resta fermo senza opt-in e seleziona sempre il target consenziente più vicino. Il Main Menu copre ora 13 pagine (`0..12`) in EN/ID/TH.
- Controlli menu resi espliciti tramite modificatore Crouch; la Camera rapida funziona a menu aperto o chiuso soltanto con Crouch rilasciato, mentre inspection e Teleport restano confinati al menu chiuso.
- Try Your Luck convertito dalla vecchia logica binaria a una macchina a stati con sei esiti: Vision, accelerazione, Skull, cura team, Burning e Hacked.
- Lifecycle join/leave/cambio squadra consolidato con guardie anti-duplicato e reset completo delle preferenze al cambio squadra.
- Identificatori personalizzati, regole, subroutine e commenti Workshop uniformati in Bahasa Indonesia.
- Localizzazione runtime completata per English, Bahasa Indonesia e ไทย, incluse icone e località server.
- Validatore reso semantico e accompagnato da test negativi per le invarianti della release.
- Corretto il primo errore d'import live: la subroutine 42 è stata abbreviata da un identificatore di 33 byte a `TerapkanTeleportasiJongkok` (26 byte); il gate ora limita ogni identificatore dichiarato a 32 byte UTF-8.
- Corretto il secondo errore d'import live: aggiunte le due parentesi finali mancanti nei filtri Camera Privacy; il gate ora valida anche i delimitatori delle espressioni e rifiuta chiamate incomplete invece di ignorarle.
- Corretti i primi riscontri live su spaziatura HUD, duplicazione del promemoria Crouch e icone Try Your Luck non visibili.
- Corretto il rendering live della roulette: tutte le sei icone usano `Visible To and Position`, rivalutano la posizione con `Update Every Frame` su occhio/mirino del beneficiario e restano visibili a tutti gli umani anche quando il roster cambia.
- Corretta l'accelerazione live: `Facing Direction Of(Evaluate Once(player))` conserva il beneficiario ma segue la sua mira con `Direction Rate and Max Speed`, producendo propulsione automatica 3D senza input direzionali.
- Menu e Camera condividono ora il latch Interact: cambiare stato di Crouch durante lo stesso hold non può attivare entrambi.
- Crouch Privacy parte OFF per ogni umano; quando il player la attiva, lo esclude dalla Camera custom, interrompe una Camera già agganciata e nasconde nome/nameplate in inspection e Vision.
- Vision mostra icona, nome e salute live soltanto per bot/dummy e umani pubblici; Crouch inspection/Teleport viene soppresso per tutta la durata per evitare sovrapposizioni.
- Corretto il latch Soundtrack: `Crouch + Ability 1/2` viene armato e consumato sulla pagina 2, ripristinando i comandi `+10/−10` generi.
- Aggiunto cleanup hero swap global-first: il tracker eroe condiviso viene aggiornato a 10 Hz e annulla roulette, status, HUD e accelerazione Try Your Luck senza creare un nuovo `Ongoing - Each Player` e senza sospendere Unkillable se il player è vivo.
- Rafforzata la separazione bot/dummy: lifecycle, HUD, menu, input e funzioni player non attraversano più il percorso bot dedicato.
- I dummy nativi ora escono dalla Spawn Room usando destinazioni mode-specific percorribili: payload per Escort/Hybrid, bandiera nemica per CTF, proxy/fallback obiettivo per Push e obiettivo corrente negli altri casi; una destinazione non valida non produce più un teleport nel vuoto.
- Il teleport automatico dei dummy verifica inoltre che il punto camminabile resti vicino al target e che un ray cast verso il basso trovi terreno prima di spostare il bot; la stabilizzazione iniziale di 1 secondo usa un timestamp, non un `Wait`.
- Confermati massimo un dummy nativo per squadra e respawn massimo 30 secondi. La creazione richiede almeno due slot liberi; quando la squadra è piena il dummy viene rimosso e non viene ricreato finché non torna la capacità necessaria, evitando spam di creazione e preservando 6 posti umani per team.
- I dummy restano offensivamente passivi (`Damage Dealt/Knockback Dealt = 0`) ma usano `Damage Received/Knockback Received = 100`: ricevono normalmente ogni danno e urto. Mantengono esplicitamente la collisione con player/bot, mentre soltanto la collisione con pareti e soffitti viene disattivata conservando il pavimento.
- Corretta la locomozione dummy: `KunciBot` mantiene `Move Speed = 20`; ogni dummy nativo attraversa pareti e soffitti ma conserva il pavimento, insegue soltanto l'umano nemico vivo opt-in più vicino e arresta il throttle entro 4 m. Se il nemico si allontana riparte automaticamente; opt-out totale, morte completa, assenza target o rimozione fermano il movimento, mentre de-mech/transizioni non lasciano il dummy bloccato e gli iBot mantengono collisioni e navigazione AI native.
- Rafforzato `FULL HP`: applicazione e riapplicazione globale impostano insieme danni ricevuti a 0, urti ricevuti a 0 e collisione con player disattivata; OFF, 1 HP e i reset lifecycle ripristinano atomicamente `100/100/collisione ON`. Try Your Luck, morte/Resurrect e Spawn Room conservano invece modalità e cursore; il tick globale riapplica la protezione e ricrea l'icona se non esiste più.
- Sostituito il Jump `Respawn` con `Resurrect`: Resurrect, teleport sicuro e verifica del successo avvengono nello stesso tick senza `Wait`. Un fallimento può essere ritentato soltanto dopo aver rilasciato Jump, senza spam durante lo stesso hold.
- Corretto il blocco casuale di Try Your Luck senza cancellare Unkillable: l'avvio e gli esiti mantengono la preferenza e la protezione attive; soltanto lo Skull finale, dopo la conclusione della roulette, usa il bypass temporaneo condiviso con Revenge e arma retry/deadline anti-stallo. D.Va, Echo e altre forme intermedie vengono eliminate fino alla morte completa, poi Resurrect riattiva la modalità scelta. Burning sospende temporaneamente Unkillable e la riduzione danni, applica il 5% della Max Health ogni secondo per 10 s e lascia quindi un danno assoluto maggiore ai tank; al termine la modalità Unkillable scelta viene riapplicata dallo scheduler.
- Revenge non consuma più il debito al click o alla sola perdita di una forma: decremento e messaggio di successo avvengono esclusivamente su `Player Died`, dopo `Is Alive == False` e con claimant/attacker coincidenti; timeout, doppio claim, leave e cambio squadra annullano il pending senza conteggio.
- Anche posizione e prompt del Resurrect con Jump vengono registrati soltanto alla morte completa, mai durante de-mech o transizioni di forma.
- Vision mostra icona eroe, nome e salute rivalutata dei soli target consentiti; inspection e Teleport Crouch vengono chiusi e restano disattivati per tutta la durata di Vision, eliminando la sovrapposizione degli In-World Text.
- Il leave di un iBot durante Vision distrugge ora il relativo In-World Text senza attraversare setup/cleanup umano, evitando handle orfani.
- Riallineato l'intero HUD al riferimento live: dieci handle fissi, roster Left `1..12`, roster Right `-13..-2` e spaziatore finale che riserva una riga prima dell'area nativa; ripristinati i promemoria completi e `LOBBY & CHILL TIME`, mentre la diagnostica integrata nel Subheader elimina lo `0` generato dal client. Il confine effettivo con Team Status Indicator/kill feed resta parte del test live a 1/6/12 player.
- Repository semplificato a un solo file `.workshop` destinato all'utente (`workshop/ruang_irama.it-IT.workshop`); la grammatica `en-US` resta esclusivamente come fixture interna di validazione e la documentazione non cita più sorgenti/manifest rimossi.
- Aggiunta la parità semantica canonica tra il clipboard pubblico `it-IT` e la fixture `en-US`: rule, dichiarazioni e azioni equivalenti devono restare sincronizzate.
- Documentazione sincronizzata con le otto modalità native supportate e con le patch client di agosto 2026.
- Rimosso il workflow di manutenzione che generava commit automatici; l'allowlist di `.github` conserva soltanto il workflow permanente di validazione e rifiuta marker, trigger o patcher one-shot.
- Test live completati e stabilità della 0.8.0 confermata dall'utente il 24 agosto 2026; la release passa a `live-ready` senza attribuire valori numerici non registrati.
- Rimossi tre `Wait(0.016)` ridondanti da Jump Resurrect, cleanup roster e seconda fase della classificazione iBot: `BersihkanPemain` è ora interamente atomica e il classificatore conserva soltanto il frame necessario a leggere il nome forzato. Restano 7 Wait funzionali e un solo Loop, indispensabile per il tick dello scheduler globale.
- Crouch Teleport esteso a quattro pagine: Primary/Secondary navigano avanti e indietro, Interact esegue l'azione; la quarta pagina permette di agganciarsi sopra un player/bot pubblico con offset sopra la testa, Reload sgancia e morte/leave/cambio eroe di uno dei due interrompono automaticamente il collegamento.

## 0.7.2 — baseline

- Teleport Crouch con selezione target vicina al reticolo e fallback obiettivo.
- Audit HUD e correzioni incrementali di join/leave, team switch e cache menu.
- Baseline conservata nella cronologia Git; il vecchio tag `v0.7.2` viene sostituito dal tag finale `v0.8.0` richiesto per la release stabile.

## 0.6.x — ricostruzione funzionale

- Introduzione dei 12 menu Arcade, della localizzazione EN/ID/TH e dei roster sociali.
- Estensione di Name Color, Player Icon, Camera, Unkillable, Teleport, Privacy e Vote Player.
- Prime ottimizzazioni di lifecycle e rendering HUD; i dettagli storici restano disponibili nella cronologia Git.
- Dummy bot: creazione iniziale su Spawn Point reale, uscita dalla spawn ritardata di 1 s e destinazione 6–16 m dal target; riallineato `PLAYER VIBES` senza spazi manuali.
