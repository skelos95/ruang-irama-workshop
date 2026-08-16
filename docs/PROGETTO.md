# Note di progetto — versione 0.6.0

Questo documento descrive lo **stato funzionale e tecnico corrente** del Workshop 0.6.0.

## Architettura generale

CHILL Dedicated Server è un overlay sociale/Arcade. Non contiene un blocco `settings`, quindi non forza mappe, modalità, roster o composizione squadre.

Gli umani registrati vivono in `Global.PemainManusia`; HUD e ID associati sono mantenuti in array paralleli. Gli slot HUD sono limitati a `0..11`, vengono restituiti al pool al leave e possono essere riutilizzati dai nuovi join.

`Global.SlotHUDTerakhir` memorizza l'ultima riga occupata per evitare `Sorted Array` continui dentro i roster.

## HUD e roster

HUD principali:

- alto centro: server location + nome server + countdown;
- sinistra: `icona personale + icona eroe + player + N MIN`;
- destra: `icona personale + icona eroe + player + genere`;
- diagnostics sotto l'ultima riga sinistra, host-only.

L'icona personale usa il colore nativo di `Icon String`. Il campo testuale del roster usa il colore selezionato dal player.

## Localizzazione

Lingue disponibili:

| Indice | Lingua |
|---:|---|
| 0 | English |
| 1 | Bahasa Indonesia |
| 2 | ไทย |

HUD, menu, diagnostics e `Small Message` usano `IndeksBahasa`. Le keyword native Workshop restano in inglese; identificatori, subroutine, regole e commenti personalizzati sono in Bahasa Indonesia.

## Main Menu: 12 voci

| Indice | Menu | Contenuto |
|---:|---|---|
| 0 | Soundtrack / Musik | 100 generi |
| 1 | Third-Person Camera | OFF / self / target |
| 2 | Name Color | 32 colori |
| 3 | HUD Language | EN / ID / TH |
| 4 | Revenge | debiti kill dirette |
| 5 | Unkillable / Kebal | OFF / 1 HP / FULL HP |
| 6 | Hero Voice | 5 preset |
| 7 | Player Icon | Nothing + 36 icone |
| 8 | Crouch Teleport | abilita overlay Crouch, default OFF |
| 9 | Crouch Privacy | ON nasconde l’intero HUD inspection ai nemici; alleati sempre completi; default OFF |
| 10 | Try Your Luck | crea una carta pubblica; solo il proprietario può attivarla, con esito 50/50 cura completa o morte |
| 11 | Vote Player | vota qualsiasi umano della lobby, incluso se stessi; bot esclusi |

Teleport **non** è una voce del Main Menu: è gestito dall'overlay Crouch.

Melee tenuto 0,5 s apre/chiude il Menu Arcade. Primary/Secondary navigano, Interact entra o applica, Reload torna al Main Menu. Nel Soundtrack Jump/Crouch fanno `−10/+10`.

I cursori persistono tra chiusura e riapertura.

## Feedback idempotente

Prima di applicare una scelta viene confrontato il valore corrente con quello selezionato. Se non cambia nulla:

- niente `Small Message`;
- niente effetto visuale;
- niente audio;
- niente riapplicazione inutile.

Vale per Soundtrack, Camera, Name Color, HUD Language, Unkillable, Hero Voice e Player Icon.

## Colori menu

Ogni menu ha una palette distinta. Main Menu e relativo sottomenu condividono lo stesso colore principale.

`WarnaMenu` è una Vector RGB animata con `Chase Player Variable Over Time` per circa **0,35 s**. I renderer convertono la vector in `Custom Color(...)`. Questo evita il problema del chase diretto su un valore Color e mantiene la transizione senza loop periodici per-player.

## Soundtrack

100 generi ordinati da ambient/minimal fino alle categorie più estreme.

- `IndeksGenre`: scelta applicata;
- `KursorGenre`: posizione di navigazione.

La lista destra mostra soltanto il genere scelto, senza prefisso `soundtrack:`.

## Name Color

`Global.DaftarWarna` contiene **32 colori**: 20 originali + 12 aggiunte pastel/neon.

Gli array dei nomi EN/ID/TH hanno la stessa lunghezza. `Global.DaftarWarnaRGB` è la tabella Vector parallela usata dalla transizione colore menu.

## Player Icon

Menu 7: **37 voci**.

- indice 0 = nessuna icona;
- indici 1..36 = tutte le icone standard disponibili tramite `Icon String`.

Default: nessuna icona. La scelta appare prima dell'icona eroe nei due roster e non crea oggetti sopra al player.

## Camera

Fuori menu, Interact tenuto 0,5 s alterna terza e prima persona.

Dal Menu Camera è possibile selezionare:

- OFF;
- proprio eroe;
- altro target valido.

La pipeline usa un solo raycast e non mantiene un loop camera server per-frame dedicato. `MulaiKamera` passa direttamente a `Start Camera` senza un `Stop Camera` intermedio: quando si cambia target evita il frame di ritorno alla camera normale che può apparire come micro-scatto. `Stop Camera` resta soltanto nei veri percorsi di disattivazione/cleanup.

## Revenge

Revenge registra soltanto le kill dirette ricevute da altri umani. Il target viene bloccato per identità prima dell'azione; la morte Revenge non crea debito reciproco. Join/leave e riferimenti invalidi vengono ripuliti.

## Unkillable: 1 HP

Menu 5.

Quando attivo:

- applica `Unkillable`;
- porta la salute a 1 HP;
- quando la salute torna al massimo, viene riportata a 1 HP.

Non può essere attivato nello Spawn Room e viene disattivato automaticamente entrando nello spawn. Se l'opzione 1 HP viene rifiutata mentre il menu è aperto, il cursore resta sulla voce 2/3 e lo `Small Message` spiega il blocco.

## Hero Voice

Menu 6 con 5 preset:

- Normal;
- Low 0.50x;
- Low 0.75x;
- High 1.25x;
- High 1.50x.

## Crouch inspection

L'inspection aggiorna il target a **4 Hz** e mostra:

- icona eroe;
- nome player;
- salute corrente.

Non mostra più la percentuale Ultimate. Le nameplate native vengono gestite e ripristinate nei percorsi di cleanup.

## Teleport Crouch

L'overlay Crouch conserva il proprio cursore e può selezionare:

- ultima Spawn Room registrata;
- destinazione obiettivo/modalità;
- player/bot validi.

Gestione modalità:

- Escort/Hybrid → `Payload Position`;
- CTF → flag nemica;
- Push → player sull'obiettivo come proxy robot, poi fallback obiettivo;
- altre modalità → `Objective Position` quando disponibile.

Il target player viene bloccato per identità prima del refresh per evitare retarget accidentali se qualcuno esce.


## Menu 10 — Try Your Luck

Interact crea una carta virtuale centrata sul mirino e visibile a tutti. La roulette non cambia più la camera del player: se Menu 10 viene attivato in terza persona, la terza persona resta attiva senza `Stop Camera`, passaggio in prima persona o successivo ripristino. Le parentesi sono due In-World Text distinti posti fisicamente a ±0,30 m dal centro, quindi la loro apertura non dipende dagli spazi del font. Heart e Skull sono due Create Icon persistenti, entrambi con posizione racchiusa in Update Every Frame; il cambio rosso/verde alterna soltanto la visibilità, senza Destroy/Create per tick. La roulette resta a 20..24 cambi con intervallo iniziale 0,08 s e +0,055 s per passaggio.

Non serve sparare. All'avvio della roulette, il Menu 5 Unkillable viene forzato su OFF (`ModeKebal = 0`, `KursorKebal = 0`, status rimosso e danno ricevuto riportato a 100) senza curare automaticamente il player; l'Arcade Menu viene chiuso e non può essere riaperto finché `KartuNasibAktif` resta `True`. Quando la roulette termina, il colore finale decide l'esito: verde ripristina immediatamente la salute massima; rosso mantiene il teschio rosso e mostra un countdown di 3 secondi, poi uccide il proprietario. Se il proprietario muore prima che la sequenza finisca, la carta viene distrutta e `KartuNasibAktif`, colore, contatore e intervallo vengono azzerati; una vecchia outcome non può colpire una nuova carta dopo il respawn. L'esito finale resta 50/50.

## Jump respawn

Alla morte viene salvata la posizione. Con menu chiuso, Jump:

1. calcola una posizione vicina con `Nearest Walkable Position`;
2. esegue `Respawn`;
3. attende un frame;
4. teleporta il player.

La posizione è geometricamente camminabile, non garantita sicura da nemici/pericoli.

## RGB ed effetti

Un solo loop globale a 10 Hz aggiorna `Global.RGB` con un ciclo pastel/neon lento. L'incremento è +3 su 1530 step, circa **51 s** per ciclo completo.

Usano questo RGB:

- titolo;
- timer;
- effetti visuali applicazione/ripristino.

L'audio degli effetti resta personale al player che esegue l'azione.

## Prestazioni per 12 player

Ottimizzazioni correnti:

- `SlotHUDTerakhir` al posto di sort continui nei roster;
- refresh Camera/Revenge/Teleport passivi a 1 Hz;
- refresh immediato quando un input usa davvero la lista;
- inspection a 5 Hz;
- `MenitLobi` ogni 10 s;
- Spawn Room cache a 1 Hz;
- RGB unico globale a 8 Hz;
- nessun loop periodico per-player per la transizione menu;
- cleanup completo degli array e ID al leave.

## GitHub

Branch operativo: `main`.

Workflow permanenti:

- `.github/workflows/validate-workshop.yml`
- `.github/workflows/maintenance-patch.yml`

La CI esegue 24 unit test e il validatore statico. Il runner di manutenzione elimina `patch.py` prima del commit finale.

## Limiti

La validazione statica non sostituisce il client Overwatch. Restano da testare live:

- import del sorgente;
- 12 menu EN/ID/TH;
- 32 Name Color;
- 37 Player Icon;
- transizione colori HUD;
- Crouch inspect/Teleport;
- Jump respawn;
- Camera;
- join/leave ripetuti;
- stress con 12 player attivi;
- rendering Thai;
- Server Load reale.


## Menu 8 e 9 — controlli Crouch personali

`Menu 8 - Crouch Teleport` usa `TeleportasiJongkokDiaktifkan`: OFF di default. Solo quando è ON la pressione di Crouch può aprire `GambarTeleportasi`; l'ispezione eroe/salute resta indipendente. `TeleportasiJongkokAktif` continua a rappresentare soltanto l'overlay attualmente aperto.

`Menu 9 - Crouch Privacy` usa `PrivasiInspeksiAktif`: OFF di default. Quando è ON, un viewer della squadra nemica riceve una stringa completamente vuota per quel target, quindi sopra al player non compaiono icona eroe, nome o salute. Un viewer della stessa squadra vede invece sempre la riga completa `icona + nome + salute`, indipendentemente dalla privacy. Con Privacy OFF la riga completa è visibile anche ai nemici. Il testo personale del viewer e i bot non vengono nascosti da questa impostazione.


## Unkillable — OFF / 1 HP / FULL HP

`ModeKebal`: 0=OFF, 1=1 HP, 2=FULL HP. FULL HP imposta Damage Received a 0% e ha una guardia che riporta la salute a Max Health se viene ridotta da altre modifiche. Gli indicatori sono distinti e pubblici: 1 HP usa `Warning` rosso, FULL HP usa `Halo` con `Global.RGB`; entrambi restano indipendenti da Crouch Privacy. OFF e Player Left distruggono l'icona. La Spawn Room disattiva esclusivamente ModeKebal=1; ModeKebal=2 resta attivo con Damage Received 0%, Max Health e Halo pubblico.


### Transizioni Unkillable esclusive

`ModeKebal` è l'unica modalità applicata: 0=OFF, 1=1 HP, 2=FULL HP. Aprire Menu 5 sincronizza soltanto il cursore e non cambia lo stato. Applicare FULL HP dopo 1 HP imposta prima `ModeKebal=2`, poi Damage Received 0% e Max Health: la regola 1 HP smette immediatamente di essere eleggibile. Applicare 1 HP dopo FULL HP imposta `ModeKebal=1`, Damage Received 100% e salute 1. Dentro Spawn Room 1 HP non può essere applicata e viene disattivata se il player vi entra; FULL HP rimane attiva.


### Feedback solo visivo

Tutti i feedback audio delle impostazioni sono rimossi. Le subroutine `EfekTerapkan` e `EfekPulihkan` mantengono una sola chiamata `Play Effect` ciascuna: `Ring Explosion`, visibile a tutti e colorata con `Global.RGB`. `Good Explosion`, `Buff Impact Sound` e `Ring Explosion Sound` non devono comparire nel sorgente. La feature Hero Voice resta indipendente perché modifica le voice line del giocatore e non è un effetto di feedback.


## Menu 11 — Vote Player

Ogni umano può mantenere un solo voto attivo verso qualsiasi umano in `Global.PemainManusia`, incluso se stesso; i bot sono esclusi. Il menu mostra tutti gli umani presenti con `NumeroVoti`. `HitungPilihan` ricalcola soltanto su join, leave o cambio voto. Se esiste un leader unico con almeno un voto, compare sotto l'ultimo player del roster sinistro dopo una riga vuota; il diagnostics host-only segue dopo un'altra riga vuota. In caso di parità al massimo `LeaderVoto = Null` e nessun nome viene mostrato.


## Audit lifecycle 0.6.0

`SiapkanPemain` inizializza esplicitamente ogni variabile player dichiarata e il validatore verifica questa proprietà automaticamente. Il Player Left usa un solo percorso di cleanup: distrugge prima tutti gli oggetti temporanei della carta, poi rimuove gli HUD/IWT dagli array paralleli, restituisce lo slot HUD, cancella i voti verso il player uscito e ripulisce riferimenti Camera/Revenge/Teleport/Inspection dei player rimasti. Sono stati eliminati gli handle globali statici `HudInfoKiri/HudInfoKanan`, il legacy `WaktuTercatat` e lo stato Menu 10 non più usato `PosisiKartuNasib/ModeKameraSebelumNasib/TargetKameraSebelumNasib`.
