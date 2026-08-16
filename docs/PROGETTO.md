# Note di progetto — versione 0.6.16

Questo documento descrive lo **stato funzionale e tecnico corrente** del Workshop 0.6.16.

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
| 10 | Try Your Luck | roulette 50/50; pagina 10 bloccata durante l'esecuzione, FULL HP temporaneo, verde ripristina l'ultima scelta Unkillable, rosso immobilizza e uccide dopo il countdown |
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

`WarnaMenu` è una Vector RGB animata con `Chase Player Variable Over Time` per circa **0,18 s**. I renderer convertono la vector in `Custom Color(...)`. Questo evita il problema del chase diretto su un valore Color e mantiene la transizione senza loop periodici per-player.

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

Interact avvia una carta pubblica con bracket e Heart/Skull persistenti. La roulette mantiene 20..24 cambi, intervallo iniziale 0,08 s e rallentamento +0,055 s per passaggio. La camera non viene modificata.

Durante `KartuNasibAktif == True` il Menu Arcade resta aperto sulla **pagina 10** e il dispatcher non accetta navigazione, back o nuove applicazioni. L'avvio salva la preferenza Unkillable in `ModeKebalTerakhir` e applica soltanto a runtime `ModeKebal = 2`, `KebalAktif = True`, status Unkillable, Damage Received 0% e Max Health. La preferenza del player non viene sovrascritta.

Esito verde:

- `ModeKebalTerakhir = 0` → OFF, Damage Received 100%, salute piena;
- `ModeKebalTerakhir = 1` → 1 HP fuori Spawn Room; dentro Spawn Room resta runtime OFF e la preferenza 1 HP resta memorizzata;
- `ModeKebalTerakhir = 2` → FULL HP con Damage Received 0%, Max Health e Halo RGB.

Esito rosso:

1. la protezione runtime passa a OFF;
2. vengono salvati `PosisiNasibTerkunci` e il colore corrente `Global.RGB` in `WarnaNasibTerkunci`;
3. Move Speed e Knockback Received passano a 0 e parte `Start Forcing Player Position`;
4. vengono creati `Light Shaft` e `Ring` a terra con il colore congelato;
5. `RadiusNasib` viene inseguito da 4 a 0,25 in 3 secondi mentre scorrono i messaggi 3-2-1;
6. il player viene ucciso.

Il cleanup su morte, leave e cambio team interrompe il chase, ferma il forcing, ripristina Move Speed/Knockback Received a 100 e distrugge entrambi gli effetti.

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

La CI esegue 33 unit test e il validatore statico. Il runner di manutenzione elimina `patch.py` prima del commit finale.

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

Ogni umano può mantenere un solo voto attivo verso qualsiasi umano in `Global.PemainManusia`, incluso se stesso; i bot sono esclusi. Il menu mostra tutti gli umani presenti con `JumlahSuara`. `HitungPilihan` ricalcola soltanto su join, leave o cambio voto. Se esiste un leader unico con almeno un voto, compare sotto l'ultimo player del roster sinistro dopo una riga vuota; il diagnostics host-only segue dopo un'altra riga vuota. In caso di parità al massimo `PemimpinSuara = Null` e nessun nome viene mostrato.


## Audit lifecycle 0.6.3

`SiapkanPemain` inizializza esplicitamente ogni variabile player dichiarata e il validatore verifica questa proprietà automaticamente. Il Player Left usa un solo percorso di cleanup: distrugge prima tutti gli oggetti temporanei della carta, poi rimuove gli HUD/IWT dagli array paralleli, restituisce lo slot HUD, cancella i voti verso il player uscito e ripulisce riferimenti Camera/Revenge/Teleport/Inspection dei player rimasti. Sono stati eliminati gli handle globali statici `HudInfoKiri/HudInfoKanan`, il legacy `WaktuTercatat` e lo stato Menu 10 non più usato `PosisiKartuNasib/ModeKameraSebelumNasib/TargetKameraSebelumNasib`.


## Nomenclatura Bahasa Indonesia 0.6.3

Le dichiarazioni personalizzate non usano più i residui misti `Voto/Voti/Numero/Leader/Max/Pari` o i suffissi `EN/TH`: sono stati sostituiti da `PemimpinSuara`, `SuaraTerbanyak`, `SuaraSeri`, `IndeksHitungSuara`, `KursorPilihan`, `PemainDipilih`, `JumlahSuara`, `NamaWarnaInggris` e `NamaWarnaThai`. Anche `GambarVoto` è diventata `GambarPilihan`. Titoli regola e commenti personalizzati usano Bahasa Indonesia; le keyword e azioni native di Overwatch Workshop restano nella sintassi ufficiale inglese.


## Cambio squadra e voto singolo 0.6.3

Un cambio Team viene trattato come un'uscita e un nuovo ingresso logico. `01 - Pemain Masuk atau Pindah Tim` controlla se l'entità è già in `Global.PemainManusia`; in tal caso chiama `BersihkanPemain`, che usa lo stesso percorso del vero `Player Left Match`, e solo dopo richiama `SiapkanPemain`. Il cleanup rimuove il vecchio HUD e tutti gli array paralleli, restituisce lo slot HUD, azzera il voto uscente, annulla i voti degli altri diretti al player, pulisce i riferimenti Camera/Revenge/Teleport/Inspection, ripristina input e modificatori e ricalcola i voti. La registrazione umana contiene anche una seconda guardia anti-duplicato prima dell'allocazione HUD.

Il voto resta una singola variabile `PemainDipilih`, non un array. Scegliendo un player diverso, l'handler esegue esplicitamente `PemainDipilih = Null`, assegna il nuovo player e poi chiama `HitungPilihan`; quindi il voto precedente viene sempre sottratto e il nuovo aggiunto nello stesso aggiornamento.


## Hotfix import Workshop 0.6.3

La variabile globale di appoggio del conteggio voti resta nello slot `47`, ma il nome è stato abbreviato da `IndeksHitungSuara` a `IndeksVote`. Il cambio è esclusivamente nominale: tutti i `For Global Variable` e gli accessi al tally usano lo stesso slot e mantengono identica la logica voto. Il validatore blocca il ritorno del vecchio identificatore perché il client Overwatch lo rifiuta in fase di importazione con `Global variable '47' has an invalid name`.


## Hotfix Try Your Luck 0.6.5

- lo status Menu 10 distingue READY / ROLLING / RED / GREEN (localizzato EN/ID/TH);
- morte durante la roulette = reset immediato della carta e ripristino di `ModeKebalTerakhir`;
- la morte non chiude più automaticamente un Menu Arcade già aperto, né tramite evento `Player Died` né tramite controllo `Is Alive == False`;
- l'esito rosso usa soltanto `Set Move Speed(..., 0)`: nessun `Start Forcing Player Position` e nessun blocco knockback; Ring/Light Shaft e countdown restano invariati.


## Hotfix Respawn Jump 0.6.6

Il respawn manuale con `Jump` resta disponibile da morto anche con il Menu Arcade aperto. La morte e il respawn non chiudono il menu; viene rimosso soltanto il guard `MenuTerbuka == False` dalla regola `12f`, mantenendo invariati `TeleportasiJongkokAktif`, il latch `BangkitLompatDipakai`, `Nearest Walkable Position`, `Respawn` e il teleport alla posizione sicura.


## Hotfix input da morto 0.6.7

Da morto il Menu Arcade non viene chiuso, ma tutte le regole che eseguono `PerintahMenu == N` richiedono `Is Alive(Event Player) == True`. La regola di morte azzera inoltre `PerintahMenu` e `PerintahTeleportasi` per eliminare input catturati nell'istante della morte. Gli attivatori Crouch inspection/Teleport restano protetti da `Is Alive == True`. `Jump` nella regola `12f` è l'unica eccezione e continua a eseguire il respawn manuale anche con menu aperto.


## Ottimizzazione input menu 0.6.8

Il dispatcher resta chord-safe ma il release gate non attende più 0,016 s. Primary/Secondary e i salti Soundtrack sfruttano la rivalutazione live dell'HUD. Interact Camera non inserisce più frame di attesa, mentre i redraw di applicazione restano per non indebolire Voice, Try Your Luck e gli altri cambi di stato. Anche Crouch Teleport usa release immediato e navigazione live. Transizione colore: 0,18 s.


## HUD Arcade persistente 0.6.9

`GambarMenu` crea lazy un solo HUD. Le pagine sono rami live selezionati da `HalamanMenu`; Interact/Reload non ricreano più il testo HUD.


## Menu split e limite regola 0.6.10

`GambarMenu` non contiene più testi o `Create HUD Text`: chiama i 13 renderer solo quando `HudMenuArcade` è vuoto. I renderer salvano i propri Text ID nell'array e usano rivalutazione `Visible To String and Color` con `MenuTerbuka + HalamanMenu`. Questo mantiene il cambio pagina immediato senza concentrare l'intero menu in una regola da 124 KB.


## Lazy loading Menu Arcade 0.6.11

La soglia Melee rimane esattamente 0,5 s. `GambarMenu` non pre-carica più 13 HUD alla prima apertura: verifica `HalamanHudMenuArcade` e crea solo la pagina corrente se non è già presente. L'array degli ID HUD e l'array dei codici pagina vengono svuotati insieme alla chiusura o alla pulizia del giocatore.


## Input menu e privacy Teleport 0.6.12

Il Menu Arcade non esegue più `Disallow Button` su Melee e Jump. Il dispatcher Soundtrack usa Ability 1/2 come comandi custom (+10/−10) mentre le abilità reali restano disabilitate dal menu. Crouch non è più usato per il salto +10. La lista Crouch Teleport esclude in fase di refresh ogni entità con `PrivasiInspeksiAktif == True`, mantenendo invariati Spawn Room e obiettivo.


## Palette menu 0.6.13

`TransisiWarnaMenu` usa RGB fissi unici per 0,1,3..11; il menu 2 Name Color continua a seguire `Global.DaftarWarnaRGB[Event Player.KursorWarna]`. Main e submenu condividono la stessa identità cromatica e la durata del chase resta 0,18 s.


## Preload HUD progressivo 0.6.14

La cache lazy resta la sorgente di verità, ma dopo la creazione del Main Menu (`HalamanHudMenuArcade` non vuoto) la regola 05e prepara le pagine 0..11 in ordine. Ogni iterazione inizia con un wait da 0,016 s e chiama al massimo un renderer, distribuendo la costruzione degli HUD su frame differenti. Le pagine restano nascoste finché `HalamanMenu` non coincide; non viene duplicato alcun `Create HUD Text` dentro il preload.


## HUD edge-triggered 0.6.15
La creazione HUD è separata da timer e loop. 05a prepara Main + pagina selezionata senza attese; 02b crea i due HUD sociali dopo la classificazione, anch’essa senza attese nella regola HUD.


## Cambio team senza picchi di script load 0.6.16

Le regole 00a2/00a3 non possono più eseguire `Set Match Time(0)` a raffica durante una selezione eroe in-match: hanno latch globali one-shot e `Is Game In Progress == False`. `02b` possiede inoltre `HudPemainDibuat`, armato prima della creazione HUD, così un ID HUD anomalo durante una transizione non può trasformare la regola Ongoing in una fabbrica HUD per-frame.
