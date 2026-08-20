# CHILL Dedicated Server — Overwatch Workshop

Overlay sociale e Arcade per lobby Overwatch 2 **6v6 fino a 12 player**, progettato per convivere con il risultato nativo di Push, Flashpoint, Capture the Flag, Control, Clash, Hybrid, Escort e Assault.

Versione: **0.8.0**

Stato: **static-ready / live-pending**

I gate automatici controllano struttura, localizzazione e invarianti del sorgente. La dicitura `live-ready` verrà usata soltanto dopo import, matrice modalità e soak test nel client aggiornato al 19 agosto 2026.

## Funzioni

- HUD centrale con nome server, countdown e località configurabile.
- Roster sinistro con icona, eroe, player e minuti; roster destro con genere musicale.
- 12 menu Arcade con preferenze individuali.
- English, Bahasa Indonesia e ไทย selezionabili per viewer.
- Camera in terza persona disponibile a menu aperto o chiuso con Crouch rilasciato; Crouch inspection e Teleport restano fuori dal menu.
- Respawn manuale con Jump da morto.
- Join/leave/cambio squadra protetti da duplicati e handle orfani.
- Diagnostica host opzionale per carico, HUD e In-World Text.

## I 12 menu

| Pagina | Menu | Contenuto |
|---:|---|---|
| 0 | Soundtrack | 100 generi internazionali |
| 1 | Third-Person Camera | OFF, self o target valido |
| 2 | Name Color | 32 colori |
| 3 | HUD Language | English, Bahasa Indonesia, ไทย |
| 4 | Revenge | debiti da kill dirette ricevute |
| 5 | Unkillable | OFF, 1 HP, FULL HP |
| 6 | Hero Voice | 5 preset |
| 7 | Player Icon | Nothing + 36 icone |
| 8 | Crouch Teleport | OFF / ON, default OFF |
| 9 | Crouch Privacy | OFF / ON, default ON |
| 10 | Try Your Luck | roulette a sei esiti |
| 11 | Vote Player | umani, self-vote incluso |

Gli indici restano invariati: Main Menu `-1`, sottomenu `0..11`. I default e i cursori persistono tra chiusura e riapertura, ma il cambio squadra esegue intenzionalmente un **reset completo** delle preferenze.

## Controlli

| Contesto | Input | Azione |
|---|---|---|
| Vivo | Tieni Melee 0,5 s | apre o chiude il Menu Arcade |
| Menu aperto | Crouch + Primary / Secondary | voce successiva / precedente |
| Main Menu | Crouch + Interact | apre il sottomenu selezionato |
| Sottomenu | Crouch + Interact | applica la scelta |
| Sottomenu | Crouch + Reload | torna al Main Menu |
| Soundtrack | Crouch + Ability 1 / Ability 2 | `+10` / `−10` generi |
| Menu aperto o chiuso, Crouch rilasciato | Tieni Interact 0,5 s | alterna la Camera rapida |
| Menu chiuso | Tieni Crouch | inspection e, se abilitato, overlay Teleport |
| Overlay Teleport | Crouch + Secondary / Primary | cambia pagina / teletrasporta |
| Morto | Jump | respawn vicino al punto di morte |

Crouch è il modificatore obbligatorio degli input menu. Per questo `Crouch + Interact` resta riservato al menu, mentre `Interact` senza Crouch può alternare la Camera anche a menu aperto. Un latch condiviso obbliga a rilasciare `Interact` prima che l'altro sistema possa usarlo. Melee e Jump restano azioni normali dell'eroe. Da morto un menu già aperto resta visibile ma congelato: nessun comando Arcade viene eseguito e soltanto Jump attiva il respawn.

## Try Your Luck

L'attivazione disabilita Unkillable e avvia una macchina a stati senza loop per-player. I sei esiti sono:

| Esito | Durata | Effetto |
|---|---:|---|
| Vision | 15 s | visione speciale |
| Acceleration | 10 s | accelerazione guidata dalla mira |
| Skull | immediato | morte del player |
| Team Heal | immediato | cura completa dei player umani della squadra |
| Burning | 10 s | 5% della salute massima al secondo, in tick da 2,5% ogni 0,5 s |
| Hacked | 5 s | stato Hacked |

Stati, messaggi ed effetti sono localizzati nelle tre lingue. Le icone della roulette vengono create da valori già risolti, senza dipendere dallo scratch globale dello scheduler, e restano segnalate anche quando lo snapshot esce dallo schermo. Menu, morte, leave e cambio squadra devono chiudere ogni stato temporaneo senza lasciare effetti o handle.

## Runtime 0.8.0

Il lavoro periodico è coordinato da un solo scheduler `Ongoing - Global` a 20 Hz:

- ogni tick: controlli rapidi e macchina a stati Try Your Luck;
- 10 Hz: lifecycle, RGB e refresh reattivi;
- 1 Hz: countdown e cache passive;
- ogni 10 secondi: minuti lobby.

Le scansioni globali non cedono l'esecuzione mentre usano il player e l'indice correnti. `Ongoing - Each Player` resta riservato a input, latch, classificazione one-shot e rendering realmente individuale.

Ogni player mantiene **un solo handle HUD Arcade attivo**. Non esistono preload o pagine nascoste: apertura, chiusura e cambio pagina sono gli unici eventi che ricreano il menu; la navigazione interna aggiorna variabili rivalutate.

## HUD e localizzazione

- Testi runtime, stati, effetti, 37 nomi icona e 26 località sono disponibili in EN/ID/TH.
- I 100 generi, `CHILL`, nomi player ed eroi restano nomi propri universali.
- Identificatori, regole, subroutine e commenti personalizzati Workshop sono in Bahasa Indonesia.
- Ogni `Create HUD Text` usa `Null` nel campo Header; sono ammessi soltanto Subheader/Text e `Small Message`.
- `Big Message` e titoli HUD sono vietati. Gli In-World Text restano ammessi per inspection, Teleport e Vision.
- Menu e liste separano contenuto e comandi con una riga vuota e placeholder equivalenti nelle tre lingue.
- Il promemoria del modificatore resta nei menu; l'HUD globale mostra soltanto il comando di inspection, senza duplicarlo e senza spaziatori iniziali superflui.

Le liste canoniche sono in [`docs/GENERI.md`](docs/GENERI.md) e [`docs/SERVER_LOCATIONS.md`](docs/SERVER_LOCATIONS.md).

## Modalità e Teleport

La modalità nativa assegna punti e vincitore; lo script non sostituisce il risultato. La destinazione Objective/Flag viene valutata al click:

- Escort e Hybrid: `Payload Position`;
- Capture the Flag: bandiera nemica valida;
- Push: proxy dell'obiettivo con fallback alla posizione obiettivo;
- Flashpoint, Control, Clash e Assault: `Objective Position(Objective Index)`.

La pagina All Players sceglie un target valido vicino al reticolo e rispetta Crouch Privacy. Privacy è ON per default: un umano privato non può essere scelto né mantenuto come target della Camera custom da alcun osservatore; dummy e bot AI rimangono soltanto target passivi e non ricevono menu, HUD o input Arcade.

## Validazione

Da eseguire dalla radice del repository, senza dipendenze Python esterne:

```powershell
python -m unittest discover -s tests -p 'test_*.py'
python tools/validate_workshop.py
```

Il workflow permanente [`.github/workflows/validate-workshop.yml`](.github/workflows/validate-workshop.yml) esegue gli stessi comandi su push e pull request. Non esiste più un workflow che modifica o committa automaticamente il repository.

Documentazione operativa:

- [`docs/PROGETTO.md`](docs/PROGETTO.md) — architettura e invarianti;
- [`docs/TEST.md`](docs/TEST.md) — matrice statica e live;
- [`docs/VALIDAZIONE.md`](docs/VALIDAZIONE.md) — copertura del gate e stato release;
- [`CHANGELOG.md`](CHANGELOG.md) — cronologia essenziale.

## Contesto client agosto 2026

La [patch del 19 agosto 2026](https://overwatch.blizzard.com/en-us/news/patch-notes/live/2026/08/#patch-2026-08-19) richiede un nuovo import e rende inutilizzabili i replay precedenti, pur senza dichiarare modifiche Workshop. La matrice comprende inoltre D.Mon, il nuovo Team Status Indicator e le modifiche a Busan, Eichenwalde e Paraíso della [patch dell'11 agosto 2026](https://overwatch.blizzard.com/en-us/news/patch-notes/live/2026/08/#patch-2026-08-11).

Finché questi test non sono registrati, la release resta **static-ready / live-pending**.
