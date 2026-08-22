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
- Corretto il rendering live della roulette: ogni icona cattura il player corretto e segue il suo mirino ogni frame, restando visibile a tutti gli umani senza inseguire lo scratch dello scheduler.
- Corretta l'accelerazione live: il beneficiario viene catturato una volta e riceve propulsione automatica nella direzione 3D corrente della visuale anche senza input direzionali.
- Menu e Camera condividono ora il latch Interact: cambiare stato di Crouch durante lo stesso hold non può attivare entrambi.
- Crouch Privacy ora è ON per default, esclude gli umani privati dalla Camera custom e interrompe una Camera già agganciata quando il target attiva la privacy.
- Rafforzata la separazione bot/dummy: lifecycle, HUD, menu, input e funzioni player non attraversano più il percorso bot dedicato.
- I dummy nativi ora escono dalla Spawn Room usando destinazioni mode-specific percorribili: payload per Escort/Hybrid, bandiera nemica per CTF, proxy/fallback obiettivo per Push e obiettivo corrente negli altri casi; una destinazione non valida non produce più un teleport nel vuoto.
- Il teleport automatico dei dummy verifica inoltre che il punto camminabile resti vicino al target e che un ray cast verso il basso trovi terreno prima di spostare il bot; se il controllo fallisce, il bot resta in spawn e riprova.
- Confermati massimo un dummy nativo per squadra e respawn massimo 30 secondi, con regressioni statiche dedicate al routing dalla Spawn Room.
- I dummy restano offensivamente passivi (`Damage Dealt = 0`) ma usano `Damage Received = 100`: i player avversari possono danneggiarli e ucciderli normalmente.
- Repository semplificato a un solo file `.workshop` destinato all'utente (`workshop/ruang_irama.it-IT.workshop`); la grammatica `en-US` resta esclusivamente come fixture interna di validazione e la documentazione non cita più sorgenti/manifest rimossi.
- Documentazione sincronizzata con le otto modalità native supportate e con le patch client di agosto 2026.
- Rimosso il workflow di manutenzione che generava commit automatici; resta un solo workflow di validazione senza dipendenze Python esterne.

## 0.7.2 — baseline

- Teleport Crouch con selezione target vicina al reticolo e fallback obiettivo.
- Audit HUD e correzioni incrementali di join/leave, team switch e cache menu.
- Stato conservato nel tag baseline `v0.7.2` prima del refactor 0.8.0.

## 0.6.x — ricostruzione funzionale

- Introduzione dei 12 menu Arcade, della localizzazione EN/ID/TH e dei roster sociali.
- Estensione di Name Color, Player Icon, Camera, Unkillable, Teleport, Privacy e Vote Player.
- Prime ottimizzazioni di lifecycle e rendering HUD; i dettagli storici restano disponibili nella cronologia Git.
