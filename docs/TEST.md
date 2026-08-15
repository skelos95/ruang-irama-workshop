# Piano di test — versione 0.5.5

Questa matrice descrive lo **stato funzionale corrente** del Workshop, inclusi gli aggiornamenti successivi alla release tecnica 0.5.5.

## Gate statico

Da eseguire dalla radice del repository:

```powershell
python -m unittest discover -s tests -p 'test_*.py'
python tools/validate_workshop.py
```

Esito atteso:

```text
Ran 20 tests
OK
```

## Smoke test import

- Importare `workshop/ruang_irama.workshop` nel client Overwatch.
- Verificare che non compaiano errori parser.
- Confermare che il server parta senza countdown nativo lungo.

## 8 menu Arcade

Aprire il Menu Arcade con Melee 0,5 s e verificare esattamente 8 voci:

1. Soundtrack
2. Third-Person Camera
3. Name Color
4. HUD Language
5. Revenge
6. Unkillable: 1 HP
7. Hero Voice
8. Player Icon

Teleport non deve comparire come nona voce del Main Menu.

## Navigazione menu

- Primary / Secondary: avanti/indietro.
- Interact: entra/applica.
- Reload: torna al Main Menu.
- Soundtrack: Jump/Crouch fanno `−10/+10`.
- Chiudere e riaprire menu e sottomenu: i cursori devono restare sulla posizione precedente.

## Transizione colori menu

- Scorrere rapidamente tra tutte le 8 voci.
- Il colore principale deve sfumare in circa 0,35 s senza scatti.
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
- `N MIN`.

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
- tutti gli 8 menu;
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
- Se il target esce, la camera deve tornare a uno stato valido.
- Verificare collisione pareti e pitch estremo.

## Crouch inspection

- Tenere Crouch su diversi target.
- Il testo deve mostrare icona eroe, nome e salute.
- Non deve mostrare percentuale Ultimate.
- Verificare target dietro ostacoli secondo il comportamento previsto dalla selezione attuale.
- Verificare cleanup al rilascio Crouch, apertura menu, morte, despawn e cambio camera.
- Il refresh a 5 Hz deve risultare visivamente reattivo.

## Teleport Crouch

- Tenere Crouch e aprire l'overlay Teleport.
- Verificare cursore persistente.
- Spawn Room: disponibile solo dopo registrazione posizione.
- Escort/Hybrid: vicino al payload.
- CTF: vicino alla flag nemica.
- Push: proxy robot quando disponibile, fallback obiettivo altrimenti.
- Player target: posizione camminabile vicina al target.
- Se il target esce durante l'azione, il teleport deve annullarsi senza retarget accidentale.

## Unkillable: 1 HP

- Non deve essere attivabile nello Spawn Room.
- Fuori spawn: applicare ON e verificare 1 HP + status Unkillable.
- Curare fino al massimo: la salute deve tornare a 1 HP.
- Entrare nello Spawn Room: auto-disattivazione e ripristino salute/status.
- OFF manuale: ripristino corretto.

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

- **Unkillable 1 HP:** attivare 1 HP, verificare salute a 1, ritorno a 1 quando raggiunge il massimo e Halo visibile a tutti anche con Crouch Privacy ON.

- **Unkillable FULL HP:** attivare FULL HP, subire danni normali e verificare che la salute non scenda; Halo visibile a tutti. Passare 1 HP ↔ FULL HP senza duplicare l’icona.

- **Unkillable cleanup:** OFF, Spawn Room e Player Left devono rimuovere Halo; OFF/Spawn devono ripristinare Damage Received a 100%.

- **Unkillable 1 HP → FULL HP:** attivare 1 HP, poi selezionare FULL HP senza passare da OFF; verificare Mode FULL HP, salute massima, Damage Received 0%, nessun ritorno a 1 HP e un solo Halo.

- **Unkillable FULL HP → 1 HP:** fuori Spawn Room passare direttamente da FULL HP a 1 HP; verificare Damage Received 100%, salute 1 e nessun comportamento FULL HP residuo.

- **FULL HP in Spawn Room:** entrare nello spawn con FULL HP attiva; verificare che ModeKebal resti FULL HP, salute massima, Damage Received 0%, Unkillable e Halo restino attivi.

- **1 HP in Spawn Room:** entrare nello spawn con 1 HP attiva; verificare reset a OFF, salute massima, Damage Received 100%, status e Halo rimossi. Provare anche a selezionare 1 HP mentre si è già nello spawn: non deve sostituire OFF/FULL HP.

- **Feedback senza audio:** applicare e ripristinare più impostazioni del Menu Arcade; non deve essere riprodotto alcun effetto sonoro di conferma.

- **Ring RGB unico:** applicazione e ripristino devono mostrare solo `Ring Explosion` RGB sul giocatore; nessuna Good Explosion o altra forma visiva di feedback.
