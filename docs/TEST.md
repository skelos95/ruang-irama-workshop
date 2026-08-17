# Piano di test — versione 0.6.25

Questa matrice descrive lo **stato funzionale e tecnico corrente** del Workshop 0.6.25.

## Gate statico

Da eseguire dalla radice del repository:

```powershell
python -m unittest discover -s tests -p 'test_*.py'
python tools/validate_workshop.py
```

Esito atteso:

```text
Ran 33 tests
OK
```

## Smoke test import

- Importare `workshop/ruang_irama.workshop` nel client Overwatch.
- Verificare che non compaiano errori parser.
- Confermare che il server parta senza countdown nativo lungo.

## 12 menu Arcade

Aprire il Menu Arcade con Melee 0,5 s e verificare esattamente 12 voci:

1. Soundtrack
2. Third-Person Camera
3. Name Color
4. HUD Language
5. Revenge
6. Unkillable (OFF / 1 HP / FULL HP)
7. Hero Voice
8. Player Icon
9. Crouch Teleport
10. Crouch Privacy
11. Try Your Luck
12. Vote Player

Teleport operativo resta nell'overlay Crouch; Menu 8 abilita/disabilita soltanto quell'overlay.

## Navigazione menu

- Primary / Secondary: avanti/indietro.
- Interact: entra/applica.
- Reload: torna al Main Menu.
- Soundtrack: Jump/Crouch fanno `−10/+10`.
- Chiudere e riaprire menu e sottomenu: i cursori devono restare sulla posizione precedente.

## Transizione colori menu

- Scorrere rapidamente tra tutte le 12 voci.
- Il colore principale deve sfumare in circa 0,18 s senza scatti.
- Entrando nel sottomenu, il colore principale deve restare coerente con la voce del Main Menu.
- Gli input devono mantenere il proprio colore fisso.
- Nessun contenuto principale HUD deve sparire durante la transizione.

## Feedback idempotente

Per Soundtrack, Camera, Name Color, HUD Language, Unkillable, Hero Voice e Player Icon:

1. applicare una scelta;
2. premere di nuovo Interact senza cambiare selezione;
3. verificare che non partano nuovi Small Message, suoni o effetti;
4. cambiare scelta e verificare un solo feedback.

## Soundtrack

- Scorrere i 100 generi.
- Verificare wrap 99 → 0 e 0 → 99.
- Testare salti ±10.
- Applicare più generi.
- La lista destra deve mostrare solo il genere scelto, senza prefisso `soundtrack:`.

## Name Color — 32 colori

- Scorrere tutte le 32 tonalità.
- Verificare i 20 colori originali e le 12 aggiunte pastel/neon.
- Applicare colori diversi.
- Il cursore deve persistere tra chiusura e riapertura.
- La preview menu deve seguire la tonalità selezionata.

## Player Icon — 37 voci

- Verificare 37 voci totali.
- Indice 0 = Nothing / nessuna icona.
- Default = Nothing.
- Verificare wrap 0 ↔ 36.
- Applicare Heart, Skull, Warning e altre icone.
- L'icona deve apparire prima dell'icona eroe nei due roster.
- Nessuna icona deve essere creata sopra il player.
- Il colore deve restare quello nativo di `Icon String`.

## HUD roster

Lista sinistra:

- icona personale opzionale;
- icona eroe;
- nome player;
- EN: `N MIN`;
- ID: `N MENIT`;
- TH: `N นาที`.

Lista destra:

- icona personale opzionale;
- icona eroe;
- nome player;
- genere scelto.

Verificare che non compaiano i vecchi prefissi `CHILL for` e `soundtrack:`.

## Localizzazione EN / ID / TH

Cambiare `HUD Language` tra:

- English
- Bahasa Indonesia
- ไทย

Per ogni lingua verificare:

- HUD superiore;
- roster;
- tutti i 12 menu;
- diagnostics;
- Small Message Camera;
- Soundtrack;
- Name Color;
- Revenge;
- Unkillable/Kebal;
- Hero Voice;
- Player Icon;
- Jump respawn;
- Teleport Crouch.

Controllare soprattutto wrapping e glifi Thai.

## Camera

- Fuori menu, tenere Interact 0,5 s: terza persona self.
- Ripetere: ritorno alla prima persona.
- Dal Menu Camera provare OFF, self e target remoti.
- Target morti/non spawnati non devono essere proposti; se il target selezionato esce, la camera deve tornare a uno stato valido.
- Verificare collisione pareti e pitch estremo.
- Passare rapidamente self → target → altro target: non deve comparire un frame in prima persona fra due `Start Camera`.

## Crouch inspection

- Tenere Crouch su diversi target.
- Il testo deve mostrare icona eroe, nome e salute.
- Non deve mostrare percentuale Ultimate.
- Verificare target dietro ostacoli secondo il comportamento previsto dalla selezione attuale.
- Verificare cleanup al rilascio Crouch, apertura menu, morte, despawn e cambio camera.
- Il refresh a 4 Hz deve risultare visivamente reattivo.

## Teleport Crouch

- Tenere Crouch e aprire l'overlay Teleport.
- Verificare cursore persistente.
- Spawn Room: disponibile solo dopo registrazione posizione.
- Escort/Hybrid: vicino al payload.
- CTF: vicino alla flag nemica solo quando la posizione della flag è valida.
- Push: proxy robot quando disponibile, fallback obiettivo altrimenti.
- Player target: posizione camminabile vicina al target; player/bot morti o non spawnati non devono comparire nell'elenco.
- Se il target esce o muore durante l'azione, il teleport deve annullarsi senza retarget accidentale.

## Unkillable — OFF / 1 HP / FULL HP

- Non deve essere attivabile nello Spawn Room.
- Fuori spawn: applicare ON e verificare 1 HP + status Unkillable.
- Curare fino al massimo: la salute deve tornare a 1 HP.
- Entrare nello Spawn Room: auto-disattivazione e ripristino salute/status.
- OFF manuale: ripristino corretto.
- FULL HP deve restare attivo anche nello Spawn Room, con Halo RGB e salute piena.

## Hero Voice

Testare i 5 preset:

- Normal
- Low 0.50x
- Low 0.75x
- High 1.25x
- High 1.50x

Verificare che la stessa scelta non riproduca feedback ripetuto.

## Jump respawn

- Morire con menu chiuso.
- Premere il tasto Jump mostrato dal binding.
- Verificare respawn vicino al punto di morte.
- Verificare fallback `Nearest Walkable Position`.

## Join/leave stress — 12 player

Con lobby piena o quasi piena:

- far entrare/uscire player ripetutamente;
- verificare riuso slot HUD;
- nessuna riga duplicata o orfana;
- diagnostics sempre sotto l'ultima riga sinistra;
- target Camera/Revenge/Teleport/Inspect senza riferimenti stale;
- nessuna crescita permanente di HUD/IWT.

## Stress menu concorrenti

Con 12 player attivi:

- più player aprono menu contemporaneamente;
- alcuni usano Camera;
- altri Crouch inspection/Teleport;
- altri cambiano Name Color, Voice e Player Icon.

Verificare:

- input reattivi;
- nessun HUD perso;
- nessun menu duplicato;
- nessun warning server persistente.

## Diagnostica

Con `Performance diagnostics` ON sull'host:

- LOAD corrente;
- AVG;
- MAX;
- HUD count;
- IWT count.

Obiettivi live consigliati:

- `Server Load Average < 80%`;
- `Server Load Peak < 100%`;
- nessuna crescita permanente dopo join/leave.

## Stato finale

Il repository può essere classificato **static-ready** quando unit test e validatore passano. La dicitura **live-ready** richiede invece il completamento della matrice sopra nel client Overwatch con 12 player reali/simulati.

- **Menu 8 Crouch Teleport:** nuovo player = OFF; Crouch non deve aprire Teleport. Attivare dal menu 8, chiudere il menu e tenere Crouch: HUD Teleport visibile. Disattivare: torna a non aprirsi.

- **Menu 9 Crouch Privacy:** nuovo player = OFF e un nemico vede icona + nome + salute. Attivare Privacy: un nemico non deve vedere assolutamente nulla sopra al target; un alleato deve continuare a vedere sempre icona + nome + salute. Disattivare Privacy: anche il nemico torna a vedere la riga completa.

- **10 menu:** scorrere Main Menu avanti/indietro e verificare wrap `0..9`, cursori persistenti e sfumatura colore anche tra menu 7/8/9.

- **Unkillable 1 HP:** attivare 1 HP, verificare salute a 1, ritorno a 1 quando raggiunge il massimo e Warning rosso visibile a tutti anche con Crouch Privacy ON.

- **Unkillable FULL HP:** attivare FULL HP, subire danni normali e verificare che la salute non scenda; Halo visibile a tutti. Passare 1 HP ↔ FULL HP senza duplicare l’icona.

- **Unkillable cleanup:** OFF, Spawn Room e Player Left devono rimuovere Halo; OFF/Spawn devono ripristinare Damage Received a 100%.

- **Unkillable 1 HP → FULL HP:** attivare 1 HP, poi selezionare FULL HP senza passare da OFF; verificare Mode FULL HP, salute massima, Damage Received 0%, nessun ritorno a 1 HP e un solo Halo.

- **Unkillable FULL HP → 1 HP:** fuori Spawn Room passare direttamente da FULL HP a 1 HP; verificare Damage Received 100%, salute 1 e nessun comportamento FULL HP residuo.

- **FULL HP in Spawn Room:** entrare nello spawn con FULL HP attiva; verificare che ModeKebal resti FULL HP, salute massima, Damage Received 0%, Unkillable e Halo restino attivi.

- **1 HP in Spawn Room:** entrare nello spawn con 1 HP attiva; verificare reset a OFF, salute massima, Damage Received 100%, status e Halo rimossi. Provare anche a selezionare 1 HP mentre si è già nello spawn: non deve sostituire OFF/FULL HP.

- **Feedback senza audio:** applicare e ripristinare più impostazioni del Menu Arcade; non deve essere riprodotto alcun effetto sonoro di conferma.

- **Ring RGB unico:** applicazione e ripristino devono mostrare solo `Ring Explosion` RGB sul giocatore; nessuna Good Explosion o altra forma visiva di feedback.


## Menu 10 / 11

- Try Your Luck: l'attivazione lascia il menu aperto e bloccato sulla pagina 10, forza temporaneamente FULL HP e non cambia la camera. Verde deve ripristinare l'ultima scelta Unkillable. Rosso deve passare runtime a OFF, bloccare movimento/knockback, forzare la posizione, creare Light Shaft + Ring con l'RGB congelato, restringere il Ring durante 3-2-1 e poi uccidere il player. Morte/leave/team switch devono ripristinare movimento/knockback, fermare forcing/chase e distruggere bracket, Heart/Skull, Light Shaft e Ring senza oggetti orfani.
- Vote Player: lista soli umani, self-vote consentito, conteggi aggiornati nel Menu 11; pareggio al primo posto = nessuna CHILL STAR; leave del target cancella i voti verso di lui e ricalcola.
- Ripetere join/leave mentre Menu 11 è aperto e verificare cursori validi e nessun riferimento stale.


## Cambio squadra

- Con un player già registrato, passare Team 1 → Team 2 → Team 1 più volte. Deve esistere sempre una sola riga roster per quel player e un solo elemento corrispondente in `Global.PemainManusia`.
- Se il player aveva votato A, dopo il cambio squadra il suo voto deve essere `NONE/BELUM ADA/ยังไม่ได้โหวต` e il totale di A deve diminuire di uno.
- Anche tutti i voti ricevuti dal player che cambia squadra devono essere eliminati, come in un vero leave/rejoin.
- Menu, Crouch Teleport, camera, Unkillable, voce, cursori e HUD temporanei devono ripartire dai valori iniziali.
- Votare A e poi B senza cambiare Team: A deve perdere immediatamente un voto e B deve guadagnarne uno; il votante non può contribuire a due target contemporaneamente.


## Import Workshop - slot globale 47

- Incollare l'intero sorgente nel Workshop: non deve comparire `Global variable '47' has an invalid name`.
- La tabella `variables` deve mostrare `47: IndeksVote`.
- Aprire Menu 11 e verificare che conteggio, cambio voto e cleanup su cambio squadra continuino a funzionare senza differenze rispetto alla 0.6.2.


## Hotfix Try Your Luck 0.6.5

- lo status Menu 10 distingue READY / ROLLING / RED / GREEN (localizzato EN/ID/TH);
- morte durante la roulette = reset immediato della carta e ripristino di `ModeKebalTerakhir`;
- la morte non chiude più automaticamente un Menu Arcade già aperto, né tramite evento `Player Died` né tramite controllo `Is Alive == False`;
- l'esito rosso usa soltanto `Set Move Speed(..., 0)`: nessun `Start Forcing Player Position` e nessun blocco knockback; Ring/Light Shaft e countdown restano invariati.


## Hotfix Respawn Jump 0.6.6

Verifica live obbligatoria: aprire il Menu Arcade, morire lasciandolo aperto, premere `Jump` e confermare che il player rinasca vicino al punto di morte senza che il menu venga chiuso. Ripetere sia dal Main Menu sia da un sottomenu.


## Hotfix input da morto 0.6.7

Verifica live obbligatoria: con Menu Arcade aperto, morire e provare Primary Fire, Secondary Fire, Interact, Reload, Crouch e Melee; nessuno deve modificare o chiudere il menu e Crouch non deve aprire inspection/Teleport. Premere quindi `Jump`: deve essere l'unico comando custom efficace, effettuare il respawn vicino al punto di morte e lasciare il menu aperto. Dopo il respawn, verificare che tutti i comandi menu tornino immediatamente disponibili.


## Menu fluido 0.6.8

Verifica live: scorrere rapidamente Main Menu e ogni submenu con Primary/Secondary; applicare con Interact, tornare con Reload e usare Jump/Crouch nel Soundtrack. Camera dal menu non deve mostrare il precedente frame di attesa. Verificare Hero Voice NORMAL e Try Your Luck READY->ROLLING. Ripetere nell'overlay Crouch Teleport. Melee 0,5 s resta volutamente invariato.


## Cambio pagina immediato 0.6.9

Con Menu Arcade aperto, premere ripetutamente `Interact` e `Reload`: Main/submenu deve cambiare senza flash e senza la pausa percepita di circa mezzo secondo.


## Diagnostica limiti Workshop 0.6.10

Dopo l'importazione aprire `Script Diagnostics`: **Size of Largest Rule deve risultare sotto 98 KB** e il Total Element Count deve rimanere sotto 32.768. Poi aprire il Menu Arcade e provare rapidamente Primary/Secondary -> Interact -> Reload su tutte le pagine: il cambio pagina deve restare immediato e senza flash. Chiudere/riaprire il menu più volte per verificare che gli HUD non si accumulino.


## Hold Melee 0,5 s / lazy loading 0.6.11

Test live con cronometro percepito: da menu chiuso tenere Melee; il Main Menu deve comparire appena termina il mezzo secondo, senza la pausa aggiuntiva vista in 0.6.10. Rilasciare Melee, aprire una pagina con Interact: al primo accesso viene creato solo quel renderer. Tornare con Reload e riaprire la stessa pagina: nessun nuovo HUD deve essere creato e la risposta deve restare immediata. Verificare inoltre Script Diagnostics: il margine ottenuto in 0.6.10 non deve regredire in modo significativo.


## Input menu / Soundtrack / privacy Teleport 0.6.12

Test live: aprire il Menu Arcade e verificare che un tap Melee esegua il normale attacco, mentre un hold di 0,5 s continui a chiudere il menu; Jump deve saltare normalmente e, da morto, continuare a fare respawn manuale. Nel Soundtrack Ability 1 deve avanzare di 10 generi e Ability 2 arretrare di 10 senza attivare le abilità dell'eroe. Attivare Crouch Privacy su un secondo player: quel player non deve comparire nel Crouch Teleport; disattivando privacy deve ricomparire al refresh successivo.


## Palette menu 0.6.13

Scorrere tutte le 12 voci: 0,1,3..11 devono avere tonalità chiaramente diverse con transizione sfumata. Aprire ogni submenu e verificare che mantenga il colore della voce. Name Color deve invece seguire il colore evidenziato.


## Preload progressivo sottomenu 0.6.14

Test live: aprire il Menu Arcade e attendere circa 0,2–0,3 s senza entrare in un sottomenu; poi visitare rapidamente tutte le pagine con Interact/Reload. Nessuna pagina dovrebbe più comparire con il precedente pop di creazione al primo accesso. Ripetere chiudendo e riaprendo il menu più volte, verificando che il Main continui ad apparire subito dopo 0,5 s e che Script Diagnostics non mostri regressioni rilevanti. Come stress test, aprire immediatamente un sottomenu appena appare il Main: il router lazy deve continuare a garantire la corretta visualizzazione anche se il preload non è ancora arrivato a quella pagina.


## Timing HUD 0.6.15
Verificare che il Main compaia esattamente alla soglia Melee di 0,5 s, che i sottomenu non abbiano pop al primo accesso e che i due HUD sociali compaiano dopo la classificazione senza ritardo aggiuntivo.


## Cambio team 0.6.16

Test live prioritario: durante una partita in corso cambiare Team 1 → Team 2 e viceversa, restare alcuni secondi nella schermata scelta eroe e poi scegliere un eroe. Il server non deve più mostrare `The server closed due to excessive Workshop script load`. Gli HUD sociali devono ricomparire una sola volta dopo lo spawn. Ripetere il cambio team più volte e controllare Script Diagnostics/server load se disponibile.


## Cambio team ripetuto 0.6.17

Test live prioritario: effettuare almeno cinque cambi consecutivi Team 1 ↔ Team 2, aspettando lo spawn fra un cambio e il successivo. Il primo, secondo e successivi cambi devono completarsi senza `excessive Workshop script load`; gli HUD sociali devono essere distrutti e ricreati una sola volta per ciclo. Ripetere anche un cambio rapido durante la schermata eroe per verificare che il lock impedisca doppie inizializzazioni.


## Team switch leggero 0.6.18

Test live prioritario: effettuare almeno dieci cambi Team 1 ↔ Team 2 sullo stesso player. Gli HUD sociali e le preferenze devono restare gli stessi, senza nuova welcome message e senza ricreazione del Menu Arcade. Il server non deve mostrare `excessive Workshop script load`. Poi uscire realmente dalla lobby e rientrare: il vero `Player Left Match` deve ancora pulire correttamente slot, HUD e riferimenti prima della nuova registrazione.


## Roster dopo cambio team 0.6.19

Test live prioritario: con almeno un player visibile nelle liste, alternare Team 1 ↔ Team 2 almeno dieci volte. Dopo ogni cambio devono ricomparire entrambe le righe sociali con nome, icona eroe, minuti e soundtrack; colore/icona personale/lingua devono restare invariati. Non deve comparire una nuova welcome message e non deve esserci `excessive Workshop script load`. Verificare anche un vero leave/rejoin, che continua invece a usare il cleanup completo.


## Team switch: roster + hero-select 0.6.20

Alternare Team 1 ↔ Team 2 più volte. Dopo lo spawn le righe sociali devono tornare nello stesso slot con nome/icona/minuti/soundtrack. Nella schermata scelta eroe non deve più comparire il riquadro anomalo `0`. Il server deve restare stabile senza excessive Workshop script load.


## Team switch clean rejoin 0.6.21

Test live: cambiare Team 1 ↔ Team 2 almeno dieci volte. Ogni cambio deve comportarsi come una nuova entrata: schermata eroe nativa pulita, nessun riquadro `0`, roster precedente rimosso, welcome/tempo/preferenze ripartono come per un rejoin e dopo lo spawn compare una sola nuova riga per lato con il nome corretto. Nessun `excessive Workshop script load` e nessuna riga duplicata/stale deve accumularsi.


## Regressione team switch 0.6.22

La 0.6.21 è live-failed: al primo cambio team il server ha mostrato `The server closed due to excessive Workshop script load.` Per la 0.6.22 provare Team 1 ↔ Team 2 almeno dieci volte. Non deve apparire alcuna chiusura per script load; ogni transizione deve rimuovere la vecchia riga e ricreare una sola registrazione/HUD dopo lo spawn.


## Team switch con menu/modifiche 0.6.23

La 0.6.22 è live-confirmed stabile per cambi ripetuti nello stato default, ma fallisce se il player cambia team con Menu Arcade aperto o dopo modifiche effettuate dal menu. Test 0.6.23: ripetere cambi Team 1 ↔ Team 2 con menu aperto su varie pagine e, separatamente, dopo avere applicato Soundtrack, Camera 3P, Name Color, Language, Unkillable 1 HP/FULL HP, Hero Voice, Icon, Crouch Teleport, Privacy e Vote. Provare anche Try Your Luck durante/alla fine del ciclo. Nessun caso deve produrre `excessive Workshop script load`; dopo lo spawn deve esistere una sola registrazione pulita.


## Team switch 0.6.24

La 0.6.23 è live-failed al primo cambio team. Provare prima Team 1 → Team 2 senza aprire il Menu Arcade, poi almeno 10 cambi alternati. Ripetere dopo avere visitato tutte le 12 pagine del menu e dopo Camera, Unkillable, Hero Voice, Crouch e Try Your Luck. Nessun `excessive Workshop script load` e una sola registrazione roster dopo ogni spawn.


## Test live cache HUD singola 0.6.25

La 0.6.24 è live-parzialmente confermata: cambio team senza usare il Menu Arcade funziona, ma dopo l'uso del menu il primo cambio può ancora chiudere il server per carico Workshop eccessivo. Per la 0.6.25 aprire il menu, scorrere tutte e dodici le voci del Main senza entrarci, quindi cambiare team: il server deve restare attivo. Ripetere entrando in ogni submenu uno alla volta, tornando al Main con Reload e cambiando team dopo ogni pagina.

Poi applicare Camera 3P, Name Color, Language, Unkillable, Hero Voice, Player Icon, Crouch Teleport/Privacy, Vote e Try Your Luck, chiudere il menu e fare almeno dieci cambi Team 1 ↔ Team 2. Interact/Reload devono restare immediati: è ammesso al massimo un singolo frame di sostituzione visiva fra Main e submenu, mai il vecchio ritardo da circa 0,5 s. Stato 0.6.25: static-ready dopo gate, live-pending fino a questa prova.
