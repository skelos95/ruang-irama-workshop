# CHILL Dedicated Server — Overwatch Workshop

**CHILL Dedicated Server** è un overlay sociale/Arcade per Overwatch 2 pensato per lobby fino a **12 player attivi**.

La versione **0.5.5** resta il numero tecnico corrente del repository, ma questo README descrive lo **stato funzionale attuale** del Workshop dopo gli aggiornamenti successivi.

## Funzioni principali

- HUD centrale con `CHILL DEDICATED SERVER`, countdown personalizzato e `SERVER LOCATION` configurabile.
- Due roster sociali:
  - sinistra: icona personale + icona eroe + player + `N MIN`;
  - destra: icona personale + icona eroe + player + genere musicale scelto.
- **10 menu Arcade**:
  1. `0 - Soundtrack` — 100 generi.
  2. `1 - Third-Person Camera` — OFF, self o spectate.
  3. `2 - Name Color` — **32 colori**.
  4. `3 - HUD Language` — English / Bahasa Indonesia / ไทย.
  5. `4 - Revenge` — debiti basati sulle kill dirette ricevute.
  6. `5 - Unkillable: 1 HP` — non disponibile nello Spawn Room.
  7. `6 - Hero Voice` — 5 preset vocali.
  8. `7 - Player Icon` — **37 voci**: `Nothing` + 36 icone Workshop standard.
  9. `8 - Crouch Teleport` — abilita/disabilita l’HUD Teleport su Crouch; default OFF.
  10. `9 - Crouch Privacy` — quando ON nasconde completamente icona/nome/salute ai nemici durante Crouch inspection; i compagni vedono sempre tutto; default OFF.
- Player Icon predefinita: **Nothing**.
- Tutti i cursori menu restano memorizzati tra chiusura e riapertura.
- Colori menu diversi e coordinati con i rispettivi sottomenu.
- Transizione colore morbida di circa **0,35 s** tramite Vector RGB.
- RGB globale pastel/neon lento per titolo, timer ed effetti visivi.
- Feedback `Small Message` + visuale + audio soltanto quando una modifica cambia davvero; premere `Interact` sulla stessa scelta non ripete il feedback.
- Crouch inspection con icona eroe, nome e salute; la percentuale Ultimate non viene mostrata.
- Teleport spostato fuori dal Main Menu: viene gestito tramite **Crouch**.
- Jump da morto per respawn vicino al punto di morte tramite `Nearest Walkable Position`.
- Camera rapida fuori menu con `Interact` tenuto per 0,5 s.
- Diagnostica prestazionale opzionale host-only.

## Menu Arcade attuale

| # | Menu | Contenuto |
|---:|---|---|
| 0 | Soundtrack | 100 generi |
| 1 | Third-Person Camera | OFF / self / target |
| 2 | Name Color | 32 colori |
| 3 | HUD Language | EN / ID / TH |
| 4 | Revenge | debiti kill dirette |
| 5 | Unkillable: 1 HP | ON / OFF |
| 6 | Hero Voice | 5 preset |
| 7 | Player Icon | Nothing + 36 icone |
| 8 | Crouch Teleport | OFF / ON, default OFF |
| 9 | Crouch Privacy | OFF / ON; ON nasconde tutto ai nemici, alleati sempre visibili |

Il Teleport resta un overlay associato a Crouch; **Menu 8** decide soltanto se quell’overlay può aprirsi.

## Controlli

| Contesto | Input | Azione |
|---|---|---|
| Sempre | Tieni Melee 0,5 s | Apre/chiude il Menu Arcade |
| Fuori menu | Tieni Interact 0,5 s | Alterna terza / prima persona |
| Fuori menu | Tieni Crouch | Inspection + overlay Teleport |
| Da morto, menu chiuso | Jump | Respawn vicino al punto di morte |
| Main Menu | Primary / Secondary | Voce successiva / precedente |
| Main Menu | Interact | Apre il sottomenu |
| Sottomenu | Primary / Secondary | Scelta successiva / precedente |
| Soundtrack | Jump / Crouch | `−10` / `+10` generi |
| Sottomenu | Interact | Applica la scelta |
| Sottomenu | Reload | Torna al Main Menu |

## Localizzazione

Tutti gli HUD principali e i `Small Message` sono gestiti in tre lingue indipendenti per viewer:

- **English**
- **Bahasa Indonesia**
- **ไทย**

Le keyword native Workshop restano in inglese; identificatori, subroutine, titoli regole e commenti personalizzati sono mantenuti in Bahasa Indonesia.

## Prestazioni e 12 player

Il runtime è stato alleggerito per una lobby piena:

- pool HUD riutilizzabile `0..11`;
- cleanup completo join/leave;
- cache `SlotHUDTerakhir` per evitare sort continui nei roster;
- inspection Crouch a **5 Hz**;
- refresh passivi Camera/Revenge/Teleport a **1 Hz**;
- contatore minuti ogni **5 s**;
- cache Spawn Room a **1 Hz**;
- un solo loop RGB globale a 10 Hz;
- un solo raycast Camera;
- nessun loop per-player dedicato alla transizione colore menu.

## Teleport Crouch

L'overlay Teleport include:

- Spawn Room registrata;
- obiettivo della modalità quando disponibile;
- player/bot validi.

Escort/Hybrid usano `Payload Position`, CTF usa la flag nemica, Push prova un player sull'obiettivo come proxy del robot e usa il fallback obiettivo quando disponibile.

## Name Color

Sono disponibili **32 tonalità**. I primi 20 colori originali sono stati mantenuti e sono state aggiunte 12 tonalità pastel/neon. Gli array EN/ID/TH e la tabella Vector RGB sono allineati.

## Player Icon

Il Menu 7 contiene **37 voci**:

- indice 0: `Nothing`;
- indici 1..36: tutte le icone standard disponibili tramite `Icon String`.

L'icona mantiene il proprio colore nativo e viene mostrata prima dell'icona eroe nei due roster. Non viene creata alcuna icona sopra il player.

## GitHub

- branch operativo: `main`;
- workflow permanenti: `validate-workshop.yml` e `maintenance-patch.yml`;
- nessun workflow temporaneo permanente;
- test statici: 20 unit test + validatore Workshop.

## Stato validazione

Il repository è **static-ready, live-pending**. I controlli statici non possono certificare importazione reale, rendering HUD, input simultanei o stabilità effettiva con 12 client Overwatch.

Per i dettagli tecnici consulta:

- [`docs/PROGETTO.md`](docs/PROGETTO.md)
- [`docs/TEST.md`](docs/TEST.md)
- [`docs/VALIDAZIONE.md`](docs/VALIDAZIONE.md)
