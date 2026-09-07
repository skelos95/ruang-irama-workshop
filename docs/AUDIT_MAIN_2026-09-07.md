# Audit main del 7 settembre 2026

Base verificata: `687197d67619f89a0f034cafaa67857d00bf78a0` (main, versione nominale 0.8.1).
Le correzioni di questo audit richiedono una nuova prova nel client prima di essere considerate validate live.

## Esito e correzioni

| Area | Problema confermato nel sorgente | Correzione |
|---|---|---|
| Scheduler | La riserva di setup di un player sospendeva tick rapidi, roulette, Fly e cache degli altri. Un iBot morto durante la classificazione poteva trattenere la riserva fino al respawn. | Tick indipendenti per ogni player; riserva mantenuta solo per serializzare il setup. La classificazione bot rilascia la propria riserva prima di `KunciBot`, anche da morto. |
| Attach | La guardia riconosceva soltanto A → B → A. Catene di tre o più player potevano chiudersi in un ciclo. | Traversal senza Wait, limitato al numero di player presenti, eseguito soltanto al comando Attach. Rifiuta anche catene già cicliche e self-attach. |
| Team-switch / Attach | L'aggancio entrante non controllava la quarantena del target a parità di eroe. | La quarantena del target invalida immediatamente l'aggancio entrante. |
| Risorse globali | Le icone Unkillable/roulette create dallo scheduler erano recuperate al leave soltanto dalle variabili dell'entità uscita. | Due array globali fissi di 12 handle, indicizzati tramite lo slot HUD canonico. Creazione, distruzione e reset aggiornano il mirror; cleanup usa il mirror anche senza variabili del leaver. |
| Voti | Il decremento del voto uscente leggeva `PemainDipilih` dal leaver dopo la sua scomparsa. Se il valore è già azzerato, resta un voto fantasma. | `HitungPilihan` ricalcola i conteggi dalle scelte dei voter ancora nel roster, dopo la rimozione. Nessuna lettura del voto dall'entità uscita. |
| Menu | Tre chiamanti eseguivano la transizione colore subito dopo `GambarMenu`, che la esegue già. | Rimossa la seconda chiamata; scroll e Travel conservano le proprie transizioni. |
| Validatore | Un gate assumeva permanentemente che la release v0.8.1 non esistesse. Il gate Fly imponeva il blocco globale ora corretto. | Stato remoto delle release separato dai controlli offline; protezioni per tick indipendenti e mirror delle icone. I contatori For sono riconosciuti come letture implicite del motore. |
| Documentazione | Alcuni passaggi descrivevano ancora cleanup in 01a, timeout CI superati e un branch archivio non più presente. | Allineati a quarantena 01a, worker 01b e configurazione GitHub osservata. |

Le due routine effetto `EfekTerapkan` e `EfekPulihkan` hanno lo stesso effetto visivo, ma conservano ruoli distinti ON/applica e OFF/ripristina nei chiamanti. Non creano handle persistenti né loop; non sono state eliminate durante le correzioni lifecycle.

## Registro e isolamento

I 12 slot rappresentano i player registrati contemporaneamente. Non esiste un contatore massimo di 12 identità storiche: `SlotHUDTersedia` restituisce lo slot liberato e gli array del roster rimuovono la riga dell'identità uscita.

Il test di churn esegue 240 identità distinte, mantenendo piena la lobby dopo i primi 12 ingressi. Include variabili del leaver perse, join duplicati, leave duplicati/tardivi, riuso immediato dello slot libero e svuotamento finale. Verifica unicità e partizione degli slot `0..11`, allineamento degli array e distruzione di 480 icone senza doppie distruzioni. Un caso separato completa/resetta una roulette prima del leave e riusa il suo ID icona per un altro player, per verificare che il cleanup tardivo non lo distrugga.

Cursori, pagina menu, latch input, handle HUD Arcade, target Camera e stato degli effetti rimangono individuali. Le verifiche del sorgente non hanno rilevato un cursore globale condiviso. Le risorse create dallo scheduler catturano l'identità del beneficiario con `Evaluate Once`; le proprietà dinamiche continuano a essere rivalutate.

## GitHub osservato

- Main protetto con check obbligatorio `Required checks`, legato all'app GitHub Actions.
- Ultimo run del main base: [34056516970](https://github.com/skelos95/ruang-irama-workshop/actions/runs/34056516970), nove check verdi e 464 test.
- Nessuna PR o issue aperta all'inizio dell'audit.
- Un workflow permanente con permessi `contents: read`, Actions fissate a SHA, timeout e sei shard di test.
- [v0.8.1](https://github.com/skelos95/ruang-irama-workshop/releases/tag/v0.8.1) punta a `14ad403babb56c58f9b55f8ebe902f13b18cd02c`; il main base è avanti di sette commit. Il tag non è stato spostato.
- Il connettore restituisce 403 per la protezione completa del branch: obbligo reviewer, bypass amministratori e force-push non verificati. La proprietà `protected` e il check richiesto sono invece leggibili.

## Verifiche automatiche e limiti

Eseguire i comandi documentati nel README e consultare i check della PR per il risultato del commit esatto. I gate verificano parità semantica en-US/it-IT, grammatica clipboard, ownership, limiti testuali, struttura del scheduler e regressioni. Il sorgente conserva 115 regole, 5 Wait e un solo Loop. I test aggiunti eseguono proiezioni delle vere espressioni e azioni di bookkeeping; non emulano la fisica o il lifecycle nativo di Overwatch.

L'audit del codice non può certificare assenza di lag, leak nel motore, crash server o compatibilità compilata con il client corrente. Non è stato eseguito un server Overwatch durante questo audit. I vecchi riscontri live riportati nei documenti non sono una prova live di queste modifiche.

La difesa contro variabili già perse al leave è motivata anche da segnalazioni di prima mano nel forum Blizzard: [player variables al leave, 2020](https://us.forums.blizzard.com/en/overwatch/t/dummy-bot-bugs-player-leave/556229), [ownership delle risorse, 2023](https://us.forums.blizzard.com/en/overwatch/t/how-to-destroy-resource-of-player-left-match/856816). Sono osservazioni della community, non una specifica ufficiale del motore corrente.

## Prova live richiesta sul nuovo commit

Registrare SHA, build del client, mappa, player, durata e metriche in `docs/TEST.md`.

1. Importare il file italiano e controllare Diagnostica script, Element Count ≤32768 e Largest Rule <98 KB compilato.
2. Con 1, 6 e 12 umani, usare contemporaneamente menu diversi, Camera, roulette, Unkillable, Ghost/Fly e Travel; il comando di A deve modificare soltanto lo stato previsto per A.
3. Fare almeno 50 ingressi/uscite complessivi, anche simultanei; includere leave durante roulette/Fly/Attach, rientro rapido e slot riusato. A lobby vuota tutti gli slot devono tornare liberi e le risorse devono tornare al livello di base.
4. Alternare Team 1 ↔ Team 2, anche rapidamente e con lo stesso eroe. Verificare reset dei default, sgancio dei dipendenti e assenza di HUD/voti/icona ereditati.
5. Tentare A → B → C → A e una catena lunga; rifiutare la chiusura del ciclo mantenendo valide le relazioni già esistenti.
6. Fare morire un iBot durante l'ingresso/classificazione, anche con respawn ritardato: i player già registrati devono mantenere Fly, scadenze roulette e registrazione di altri nuovi ingressi.
7. Proseguire per almeno 30 minuti con diagnostica: confrontare Server Load medio/picco e numero di HUD/IWT prima/dopo il churn, osservando anche icone orfane e stabilità del server.
