# Changelog

Le versioni seguono lo stato del sorgente Workshop e della relativa validazione. Un rilascio `static-ready / live-pending` ha superato i controlli automatici, ma richiede ancora l'import e i test nel client Overwatch prima del tag finale `live-ready`.

## 0.8.0 — 2026-08-20

Stato: **static-ready / live-pending**.

- Runtime riorganizzato attorno a uno scheduler globale a 20 Hz, con attività scalate a 10 Hz, 1 Hz e 0,1 Hz.
- Menu Arcade ridotto a un solo handle HUD attivo per player, senza preload o pagine nascoste.
- Controlli menu resi espliciti tramite modificatore Crouch; Camera, inspection e Teleport sono confinati al menu chiuso.
- Try Your Luck convertito dalla vecchia logica binaria a una macchina a stati con sei esiti: Vision, accelerazione, Skull, cura team, Burning e Hacked.
- Lifecycle join/leave/cambio squadra consolidato con guardie anti-duplicato e reset completo delle preferenze al cambio squadra.
- Identificatori personalizzati, regole, subroutine e commenti Workshop uniformati in Bahasa Indonesia.
- Localizzazione runtime completata per English, Bahasa Indonesia e ไทย, incluse icone e località server.
- Validatore reso semantico e accompagnato da test negativi per le invarianti della release.
- Corretto il primo errore d'import live: la subroutine 42 è stata abbreviata da un identificatore di 33 byte a `TerapkanTeleportasiJongkok` (26 byte); il gate ora limita ogni identificatore dichiarato a 32 byte UTF-8.
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
