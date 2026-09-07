# Workshop source

`ruang_irama.it-IT.workshop` è il sorgente canonico da copiare negli Appunti del Workshop di Overwatch per la localizzazione italiana.

La versione corrente del progetto è definita nel file `VERSION` alla radice del repository. Lo stato `live-ready` riporta il completamento storico di validator, test automatici, preflight clipboard e regressione client della 0.8.1. Il tag pubblicato e le revisioni successive su `main` possono contenere sorgenti diversi mantenendo lo stesso `VERSION`: consultare il [`README principale`](../README.md) e registrare lo SHA del file importato nel verbale live.

I check GitHub Actions correnti usano `.github/workflows/validate-workshop.yml`: sei shard di unit test con timeout di 20 minuti ciascuno, job Whitespace e Semantic gates con timeout di 10 minuti e aggregatore Required checks con timeout di 5 minuti. L'aggregatore passa soltanto se tutti i job di validazione hanno successo. Lo stato di un commit precedente può restare visibile nella cronologia anche dopo che il problema CI è stato corretto in un commit successivo.
