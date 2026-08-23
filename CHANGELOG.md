# Changelog

Le versioni seguono lo stato del sorgente Workshop e della relativa validazione. Un rilascio `static-ready / live-pending` ha superato i controlli automatici, ma richiede ancora l'import e i test nel client Overwatch prima del tag finale `live-ready`.

## 0.8.0 — 2026-08-20

Stato: **static-ready / live-pending**.

- Runtime riorganizzato attorno a uno scheduler globale a 20 Hz, con attività scalate a 10 Hz, 1 Hz e 0,1 Hz.
- Menu Arcade ridotto a un solo handle HUD attivo per player, senza preload o pagine nascoste.
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
- Crouch Privacy ora è ON per default, esclude gli umani privati dalla Camera custom e interrompe una Camera già agganciata quando il target attiva la privacy.
- Vision e inspection applicano la stessa Privacy: nome e nameplate di un umano con Privacy ON non vengono mai creati o mantenuti per gli altri player.
- Rafforzata la separazione bot/dummy: lifecycle, HUD, menu, input e funzioni player non attraversano più il percorso bot dedicato.
- I dummy nativi ora escono dalla Spawn Room usando destinazioni mode-specific percorribili: payload per Escort/Hybrid, bandiera nemica per CTF, proxy/fallback obiettivo per Push e obiettivo corrente negli altri casi; una destinazione non valida non produce più un teleport nel vuoto.
- Il teleport automatico dei dummy verifica inoltre che il punto camminabile resti vicino al target e che un ray cast verso il basso trovi terreno prima di spostare il bot; la stabilizzazione iniziale di 1 secondo usa un timestamp, non un `Wait`, riportando il limite statico a massimo 10 `Wait`.
- Confermati massimo un dummy nativo per squadra e respawn massimo 30 secondi. La creazione richiede almeno due slot liberi; quando la squadra è piena il dummy viene rimosso e non viene ricreato finché non torna la capacità necessaria, evitando spam di creazione e preservando 6 posti umani per team.
- I dummy restano offensivamente passivi (`Damage Dealt = 0`) ma usano `Damage Received = 100`: i player avversari possono danneggiarli e ucciderli normalmente.
- Repository semplificato a un solo file `.workshop` destinato all'utente (`workshop/ruang_irama.it-IT.workshop`); la grammatica `en-US` resta esclusivamente come fixture interna di validazione e la documentazione non cita più sorgenti/manifest rimossi.
- Aggiunta la parità semantica canonica tra il clipboard pubblico `it-IT` e la fixture `en-US`: rule, dichiarazioni e azioni equivalenti devono restare sincronizzate.
- Documentazione sincronizzata con le otto modalità native supportate e con le patch client di agosto 2026.
- Rimosso il workflow di manutenzione che generava commit automatici; l'allowlist di `.github` conserva soltanto il workflow permanente di validazione e rifiuta marker, trigger o patcher one-shot.

## 0.7.2 — baseline

- Teleport Crouch con selezione target vicina al reticolo e fallback obiettivo.
- Audit HUD e correzioni incrementali di join/leave, team switch e cache menu.
- Stato conservato nel tag baseline `v0.7.2` prima del refactor 0.8.0.

## 0.6.x — ricostruzione funzionale

- Introduzione dei 12 menu Arcade, della localizzazione EN/ID/TH e dei roster sociali.
- Estensione di Name Color, Player Icon, Camera, Unkillable, Teleport, Privacy e Vote Player.
- Prime ottimizzazioni di lifecycle e rendering HUD; i dettagli storici restano disponibili nella cronologia Git.
- Dummy bot: creazione iniziale su Spawn Point reale, uscita dalla spawn ritardata di 1 s e destinazione 6–16 m dal target; riallineato `PLAYER VIBES` senza spazi manuali.
