# Progetto tecnico — CHILL Dedicated Server 0.8.0

Stato release: **static-ready / live-pending**.

Questo documento descrive il contratto architetturale del sorgente `workshop/ruang_irama.workshop`. Le prove statiche certificano le invarianti verificabili dal repository; import, rendering, carico e concorrenza restano da confermare nel client Overwatch aggiornato al 19 agosto 2026.

## Obiettivi

- Lobby 6v6 con massimo 12 player attivi.
- Overlay sociale e Arcade che non assegna punteggi o vincitori.
- Supporto a Push, Flashpoint, Capture the Flag, Control, Clash, Hybrid, Escort e Assault.
- UI completa in English, Bahasa Indonesia e ไทย.
- Priorità al lavoro globale condiviso rispetto ai loop per-player.
- Cleanup deterministico di HUD, In-World Text, effetti e riferimenti.

## Contratto stabile

### Lingue e pagine

| Indice | Lingua |
|---:|---|
| 0 | English |
| 1 | Bahasa Indonesia |
| 2 | ไทย |

Main Menu usa pagina `-1`; le 12 pagine mantengono gli indici `0..11`. Default, effetti e risultati funzionali non cambiano rispetto al contratto della modalità. I cursori persistono durante la permanenza nella stessa squadra; un cambio squadra equivale invece a leave + fresh join e ripristina tutte le preferenze.

### Input

- Tieni Melee per 0,5 s: apre o chiude il Menu Arcade.
- A menu aperto e da vivi, Crouch è il modificatore obbligatorio per Primary, Secondary, Interact, Reload e Ability 1/2.
- Primary/Secondary navigano; Interact entra o applica; Reload torna al Main Menu.
- Nel Soundtrack, Ability 1/2 eseguono `+10/−10`.
- Melee e Jump restano azioni normali dell'eroe.
- A menu aperto o chiuso, Interact tenuto per 0,5 s cambia Camera soltanto con Crouch rilasciato.
- A menu chiuso, Crouch abilita inspection e l'eventuale overlay Teleport.
- Da morto, un menu aperto resta visibile ma congelato; soltanto Jump esegue il respawn custom.

Le condizioni e il modificatore sono parte del contratto: `Crouch + Interact` alimenta il menu, `Interact` senza Crouch alimenta la Camera, mentre inspection e Teleport richiedono Crouch e menu chiuso. Menu e Camera condividono un latch consumabile: dopo che uno dei due usa `Interact`, soltanto il rilascio fisico del pulsante riabilita entrambi.

## Scheduler globale

Un'unica regola `Ongoing - Global` mantiene il ritmo base a 20 Hz. Dopo ciascun tick incrementa un contatore e delega a subroutine senza `Wait`:

| Frequenza | Responsabilità |
|---:|---|
| 20 Hz | controlli rapidi e avanzamento Try Your Luck |
| 10 Hz | lifecycle reattivo, RGB e refresh visivi |
| 1 Hz | countdown e cache passive |
| 0,1 Hz | minuti di permanenza in lobby |

Il player globale corrente e il relativo indice appartengono esclusivamente allo scheduler. Una scansione non contiene `Wait`, `Loop` o altre azioni che cedono l'esecuzione; nessun'altra regola può riusare quei due scratch globali.

`Ongoing - Each Player` è ammesso soltanto quando l'evento o lo stato è realmente individuale:

- lettura input e latch di pressione/hold;
- classificazione one-shot umano/bot;
- creazione o rivalutazione di rendering visibile a un singolo player;
- respawn o cleanup atomico che dipende dall'evento player.

## Menu Arcade

Ogni player possiede al massimo **un handle HUD Arcade**. Non esistono cache di pagine, preload progressivo o HUD nascosti.

Il lifecycle del menu è:

1. apertura: crea l'handle della pagina corrente;
2. Primary/Secondary o modifica della scelta: aggiorna variabili rivalutate senza ricreare l'HUD;
3. cambio Main Menu ↔ sottomenu: distrugge l'handle precedente e crea la nuova pagina;
4. chiusura, leave o cambio squadra: distrugge l'handle e azzera il riferimento.

Il dispatcher Interact delega alle subroutine delle singole pagine. Avanti/indietro e `±10` usano regole simmetriche condivise; ogni applicazione idempotente evita feedback ripetuti.

Tutti i menu seguono lo stesso layout:

```text
contenuto e stato

comandi disponibili
```

I placeholder devono avere stessa cardinalità nei tre rami linguistici.

## Try Your Luck

Try Your Luck è una macchina a stati guidata da timestamp, non un loop per-player. All'avvio disattiva Unkillable come nel comportamento 0.8.0 e mantiene la pagina bloccata finché la sequenza non termina.

| Esito | Durata | Comportamento |
|---|---:|---|
| Vision | 15 s | crea e poi rimuove l'effetto Vision |
| Acceleration | 10 s | applica accelerazione orientata dalla mira |
| Skull | immediato | uccide il player |
| Team Heal | immediato | porta i player umani della squadra alla salute completa |
| Burning | 10 s | infligge il 5% della salute massima al secondo, come 2,5% ogni 0,5 s |
| Hacked | 5 s | applica e poi rimuove Hacked |

Il tick globale valuta transizioni e scadenze. Morte, leave e cambio squadra annullano stato, accelerazione, status, HUD/IWT ed effetti associati. Nessun esito può lasciare un timestamp o un riferimento riutilizzabile dal player successivo nello stesso slot.

Le icone della roulette sono visibili soltanto agli umani e ricevono posizione e tipo già valutati al momento della creazione. Non rivalutano lo scratch `Global.PemainAktif`, che viene azzerato al termine di ogni scansione scheduler; l'indicatore off-screen resta abilitato se movimento o rotazione portano lo snapshot fuori visuale.

## Lifecycle player

### Join

La registrazione verifica prima l'esistenza del player nel roster. Un evento Join duplicato non aggiunge una seconda voce e non crea un secondo messaggio o handle. Il setup inizializza ogni variabile player dichiarata, assegna lo slot sociale e crea una sola coppia di HUD roster.

Dummy e bot AI seguono classificazione e lock dedicati: non vengono inseriti nel roster umano e non ricevono menu, HUD, input Arcade o funzioni riservate ai player. Possono restare target passivi di inspection, Vision e Camera dove previsto dal contratto.

### Leave

Il cleanup:

1. interrompe input e sottosistemi persistenti;
2. rimuove Camera, status ed effetti engine;
3. distrugge HUD, In-World Text ed effetti posseduti;
4. libera slot e riferimenti in Camera, Revenge, Teleport, inspection e voti;
5. ricostruisce soltanto le cache condivise necessarie.

### Cambio squadra

Il cambio Team 1 ↔ Team 2 usa lo stesso cleanup completo del leave seguito da setup fresco. Il reset totale delle preferenze è intenzionale. La sequenza impedisce doppioni anche durante transizioni simultanee o una cascata full-lobby.

## HUD, testi ed effetti

- `Create HUD Text` deve avere Header `Null`.
- Sono consentiti Subheader/Text, `Small Message` e gli In-World Text necessari a inspection, Teleport e Vision.
- `Big Message` e titoli HUD non sono consentiti.
- Gli handle vengono distrutti prima di essere sovrascritti; le variabili handle tornano a `Null`.
- Ogni testo operativo, stato, esito, nome icona e località ha rami EN/ID/TH.
- I 100 generi, `CHILL`, nomi player ed eroi sono nomi propri universali.
- Identificatori personalizzati, titoli regola, subroutine e commenti Workshop sono in Bahasa Indonesia; keyword native, acronimi tecnici e nomi degli eroi restano invariati.

Il nuovo Team Status Indicator del client non deve essere coperto da blocchi Top/Left/Right: il test live verifica leggibilità, spaziatori e assenza di collisioni.

## Camera, inspection e Teleport

La Camera usa un solo raycast per risolvere la posizione. Target morti, non spawnati, inesistenti o umani con Privacy ON vengono rimossi; una perdita target porta a un fallback valido senza creare più Camera concorrenti. Se un target umano attiva Privacy mentre è osservato, gli osservatori custom già agganciati tornano alla visuale normale.

Inspection e Teleport sono disponibili soltanto a menu chiuso e da vivi. Privacy è ON per default: nasconde icona, nome e salute agli altri player e impedisce a qualunque osservatore di scegliere l'umano come target della Camera custom. Questa garanzia riguarda i sistemi Workshop della modalità, non la visuale spettatore nativa riservata a lobby e amministratori.

La destinazione Teleport viene rivalutata al click:

| Modalità | Destinazione |
|---|---|
| Escort, Hybrid | Payload |
| Capture the Flag | bandiera nemica valida |
| Push | proxy valido dell'obiettivo, poi fallback Objective Position |
| Flashpoint, Control, Clash, Assault | `Objective Position(Objective Index)` |

La pagina All Players sceglie un target vivo/spawnato vicino al reticolo e rispetta Privacy; `Nearest Walkable Position` limita le destinazioni non praticabili.

## Modalità native

La logica Arcade è neutrale rispetto all'esito della partita. Non chiama azioni custom per assegnare punti, completare round o dichiarare vincitori. La verifica live attraversa tutte le otto modalità:

| Modalità | Focus |
|---|---|
| Push | proxy robot e fallback obiettivo |
| Flashpoint | indice obiettivo attivo |
| Capture the Flag | bandiera nemica |
| Control | cambio round e obiettivo |
| Clash | avanzamento tra punti |
| Hybrid | payload dopo la cattura |
| Escort | payload |
| Assault | transizione A/B |

Busan, Eichenwalde e Paraíso hanno priorità perché modificati nella patch dell'11 agosto 2026.

## Gate di prestazioni

Target statici:

- un solo `Loop` globale;
- massimo 10 `Wait`, ciascuno associato a un percorso autorizzato;
- un solo raycast Camera;
- nessuna regola, variabile o subroutine inutilizzata/duplicata;
- nessun loop o Wait dentro le subroutine chiamate durante una scansione scheduler;
- un solo handle HUD Arcade attivo per player;
- sorgente sotto 32.768 elementi, obiettivo massimo 26.000;
- largest rule sotto 98 KB, obiettivo massimo 80 KB.

Gli ultimi due valori devono essere letti nel client: non sono deducibili con precisione dal solo testo Workshop.

## Repository e release

Il workflow permanente `validate-workshop.yml` usa Python 3.12 e sola standard library per eseguire unit test e validatore. Il vecchio workflow `maintenance-patch.yml`, che applicava e committava patch automatiche, è stato rimosso.

La release 0.8.0 resta **live-pending** finché non vengono registrati:

- import pulito nel client del 19 agosto 2026 e smoke test D.Mon;
- matrice input/menu/localizzazione;
- stress join/leave/team switch;
- matrice sulle otto modalità;
- soak di almeno 30 minuti con 12 slot;
- diagnostica senza crescita progressiva di HUD, In-World Text o effetti.

La procedura completa è in [`TEST.md`](TEST.md); il gate semantico è descritto in [`VALIDAZIONE.md`](VALIDAZIONE.md).
