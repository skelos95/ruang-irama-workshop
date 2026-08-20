# Piano di test — versione 0.8.0

Stato atteso dopo i gate repository: **static-ready / live-pending**. Nessun risultato live è presunto: import, input simultanei, rendering e stabilità devono essere registrati dal client Overwatch aggiornato al 19 agosto 2026.

## 1. Gate statici

Eseguire dalla radice del repository:

```powershell
python -m unittest discover -s tests -p 'test_*.py'
python tools/validate_workshop.py
```

Accettazione:

- tutti gli unit test verdi;
- validatore semantico verde;
- nessuna dipendenza Python esterna;
- nessun errore da `git diff --check`;
- un solo workflow permanente, `validate-workshop.yml`.

Le invarianti controllate automaticamente sono dettagliate in [`VALIDAZIONE.md`](VALIDAZIONE.md).

## 2. Preparazione client

1. Aggiornare Overwatch alla build del **19 agosto 2026**.
2. Importare da zero `workshop/ruang_irama.workshop`; non riutilizzare un replay precedente alla patch.
3. Annotare codice import, build client, regione, data/ora e piattaforma.
4. Abilitare la diagnostica host quando si acquisiscono le metriche.
5. Preparare 12 slot. I dummy sono sufficienti per il soak; la prova di input simultanei richiede più utenti reali.

Accettazione smoke:

- import senza errori parser;
- avvio senza `excessive Workshop script load`;
- D.Mon può entrare, cambiare eroe, aprire/chiudere menu e usare i sistemi generici senza errori;
- nessuna collisione evidente con il nuovo Team Status Indicator.

## 3. Contratto input

Provare con un eroe che esponga chiaramente Melee, Jump, Primary, Secondary, Reload, Ability 1/2, Interact e Crouch.

| Stato | Prova | Esito atteso |
|---|---|---|
| Vivo, menu chiuso | Tieni Melee 0,5 s | il menu si apre una volta |
| Vivo, menu aperto | Tieni Melee 0,5 s | il menu si chiude una volta |
| Menu aperto | Primary/Secondary senza Crouch | nessun comando menu |
| Menu aperto | Crouch + Primary/Secondary | una sola navigazione per pressione |
| Menu aperto | Interact/Reload senza Crouch | nessun comando menu |
| Menu aperto | Crouch + Interact/Reload | entra/applica o torna indietro |
| Soundtrack | Crouch + Ability 1/2 | `+10/−10` con wrap |
| Menu aperto | Melee e Jump | azioni normali dell'eroe non disabilitate |
| Menu chiuso | Tieni Interact 0,5 s | alterna Camera, una volta per hold |
| Menu chiuso | Tieni Crouch | inspection/Teleport disponibili |
| Menu aperto | Tieni Interact o Crouch | Camera/inspection/Teleport non partono |
| Morto | Menu già aperto | resta visibile ma congelato |
| Morto | Primary, Secondary, Interact, Reload, Crouch, abilità | nessun comando Arcade |
| Morto | Jump | respawn vicino alla morte; menu ancora visibile |

Ripetere rapidamente gli input per cercare doppie attivazioni, latch bloccati e interferenze tra hold e click.

## 4. Menu e localizzazione

Verificare esattamente 12 voci, indici e contenuti:

1. Soundtrack — 100 generi.
2. Third-Person Camera — OFF, self e target valido.
3. Name Color — 32 colori.
4. HUD Language — English, Bahasa Indonesia, ไทย.
5. Revenge — debiti da kill dirette.
6. Unkillable — OFF, 1 HP, FULL HP.
7. Hero Voice — 5 preset.
8. Player Icon — Nothing + 36 icone.
9. Crouch Teleport — OFF/ON.
10. Crouch Privacy — OFF/ON.
11. Try Your Luck — sei esiti.
12. Vote Player — umani, self-vote incluso.

Per ogni pagina e per ciascuna lingua EN/ID/TH:

- aprire, navigare avanti/indietro, applicare, tornare e riaprire;
- verificare testo, stato, feedback e comando localizzati;
- verificare una riga vuota tra contenuto e comandi;
- controllare glifi Thai, wrapping, allineamento Top/Left/Right e assenza di sovrapposizioni;
- confermare che non compaiano titoli HUD o `Big Message`;
- verificare che una scelta invariata non ripeta Small Message, audio o effetto;
- controllare che esista un solo HUD Arcade: nessuna copia appare durante scroll, cambio pagina, morte o riapertura.

Focus dati:

- tutti i 100 generi, wrap `0 ↔ 99` e salti `±10`;
- tutti i 32 colori;
- 37 icone con nome localizzato e indice 0 `Nothing`;
- 26 località server nello stesso ordine;
- roster con `MIN`, `MENIT` e `นาที` corretti;
- CHILL, generi, nomi player ed eroi invariati come nomi propri.

## 5. Try Your Luck

Forzare o ripetere l'attivazione fino a osservare tutti gli esiti:

| Esito | Verifica |
|---|---|
| Vision | effetto e testo EN/ID/TH; cleanup dopo 15 s |
| Acceleration | direzione coerente con la mira; cleanup dopo 10 s |
| Skull | morte immediata e cleanup completo |
| Team Heal | salute completa per la squadra, nessun effetto persistente |
| Burning | 5% max HP al secondo per 10 s, con tick da 2,5% ogni 0,5 s; stop alla scadenza/morte |
| Hacked | stato per 5 s, poi rimozione |

Per ciascun esito:

- Unkillable viene disattivato all'avvio;
- il menu non accetta comandi incompatibili durante lo stato bloccato;
- il countdown non salta o duplica tick;
- morte, leave, hero swap e cambio squadra annullano stato, status ed effetti;
- nessuna seconda roulette per lo stesso player parte mentre la prima è attiva;
- chiusure e riaperture non duplicano HUD, In-World Text o effetti.

## 6. Camera, inspection e Teleport

### Camera

- Alternare Camera rapida self/first-person con Interact 0,5 s a menu chiuso.
- Dal Menu Camera provare OFF, self e target diversi.
- Cambiare rapidamente target senza frame di Camera concorrenti.
- Uccidere, far uscire o despawnare il target: il riferimento deve tornare valido.
- Verificare collisione pareti e pitch estremo.
- Confermare che esista un solo raycast Camera dal punto di vista funzionale.

### Inspection e Privacy

- Con menu chiuso, tenere Crouch su alleati, nemici, bot e se stessi.
- Verificare icona eroe, nome e salute; nessuna percentuale Ultimate.
- Privacy OFF: il nemico vede la riga completa.
- Privacy ON: il nemico non vede la riga; l'alleato continua a vederla.
- Rilasciare Crouch, aprire menu, morire, cambiare Camera o target: cleanup immediato.

### Teleport

- Nuovo player: Menu 8 OFF, nessun overlay Teleport.
- Attivare Menu 8, chiudere menu e tenere Crouch.
- Crouch + Secondary cambia pagina; Crouch + Primary teletrasporta.
- Spawn Room usa un punto valido della squadra.
- All Players sceglie un target vivo/spawnato vicino al reticolo e rispetta Privacy.
- Ricalcolare il target al click; morte/leave tra preview e click deve annullare o scegliere soltanto un fallback esplicito.
- Destinazione finale sempre camminabile o annullata in sicurezza.

## 7. Lifecycle e reset squadra

Eseguire con HUD, menu, Camera, inspection, Teleport, Unkillable, Revenge, voto e Try Your Luck in combinazioni diverse.

### Join/leave

- join umano e bot;
- evento Join duplicato o classificazione tardiva;
- leave con menu aperto e chiuso;
- leave durante ciascun sottosistema;
- rientro nello stesso slot.

Accettazione: una sola riga roster, un solo set HUD, un solo messaggio di join/leave e nessun target stale.

### Cambio squadra

- almeno **20 cambi squadra singoli** Team 1 ↔ Team 2;
- almeno **10 transizioni simultanee** di due o più player;
- una cascata di cambio squadra a lobby piena.

Dopo ogni cambio:

- nessun doppione roster o handle;
- Camera, status, effetti, voti e riferimenti precedenti rimossi;
- tutte le preferenze tornano ai default, inclusi lingua, colore, genere, icona, Teleport e Privacy;
- Text Count ed Entity Count tornano al baseline;
- nessun `excessive Workshop script load`.

## 8. Matrice modalità

Lo script non deve assegnare punti o vincitori. Eseguire almeno un round o segmento significativo per riga:

| Modalità | Objective/Teleport | Transizioni da verificare |
|---|---|---|
| Push | proxy obiettivo + fallback Objective Position | robot/obiettivo, overtime |
| Flashpoint | Objective Position dell'indice attivo | rotazione punti |
| Capture the Flag | bandiera nemica valida | presa, caduta, ritorno, score |
| Control | Objective Position | cambio round e lato |
| Clash | Objective Position | avanzamento/ritiro punti |
| Hybrid | Payload dopo la cattura | cattura → scorta |
| Escort | Payload | checkpoint e overtime |
| Assault | Objective Position | punto A → punto B |

Priorità mappe:

- Busan — modifiche dell'11 agosto;
- Eichenwalde — modifiche dell'11 agosto;
- Paraíso — modifiche dell'11 agosto.

In ogni modalità usare contemporaneamente Menu, Camera, inspection, Teleport e Try Your Luck senza alterare il risultato nativo.

## 9. Soak 12 slot

Durata minima: **30 minuti** con 12 slot occupati.

Durante il soak:

- alternare combattimento e respawn;
- aprire/chiudere e navigare menu su più player;
- usare Camera, inspection, Teleport e Try Your Luck;
- eseguire join/leave e alcuni cambi squadra;
- cambiare eroe, includendo D.Mon;
- lasciare attivi i dummy per il carico di base;
- usare più utenti reali per la fase di input simultanei.

Accettazione:

- server fluido e input reattivi;
- nessun warning persistente di script load;
- nessuna crescita progressiva di HUD, In-World Text o effetti;
- countdown, RGB e minuti continuano con frequenze regolari;
- nessun conflitto con Team Status Indicator.

## 10. Diagnostica

Registrare baseline a lobby vuota, dopo 12 join, durante picco concorrente e dopo cleanup completo.

| Metrica | Limite | Obiettivo |
|---|---:|---:|
| Element Count | `< 32.768` | `≤ 26.000` |
| Largest Rule | `< 98 KB` | `≤ 80 KB` |
| Text Count | ritorno al baseline | nessuna crescita |
| Entity Count | ritorno al baseline | nessuna crescita |

Annotare anche Server Load corrente/medio/picco se disponibile. L'assenza di leak è più importante di un singolo picco transitorio: dopo chiusure, morti, leave e cambi squadra i contatori devono stabilizzarsi al baseline atteso per i player rimasti.

## 11. Rapporto da restituire

Usare questo schema:

```text
Build client:
Codice import:
Piattaforma/regione:
Data e durata:
Slot umani/dummy:

Import: PASS/FAIL
D.Mon: PASS/FAIL
EN/ID/TH e 12 menu: PASS/FAIL
Input simultanei: PASS/FAIL
Join/leave: PASS/FAIL
20 cambi singoli: PASS/FAIL
10 cambi simultanei: PASS/FAIL
Cascata full-lobby: PASS/FAIL
8 modalità: PASS/FAIL
Soak 30 min: PASS/FAIL

Element Count max:
Largest Rule:
Text Count baseline/max/finale:
Entity Count baseline/max/finale:
Server Load avg/max:

Screenshot/video:
Note e riproduzione problemi:
```

La release diventa **live-ready** soltanto quando tutti i test obbligatori sono PASS, le metriche rispettano i limiti e ogni anomalia riproducibile è stata corretta e rivalidata.
