# Workshop source

`ruang_irama.it-IT.workshop` è il sorgente canonico da copiare negli Appunti del Workshop di Overwatch per la localizzazione italiana.

La versione corrente del progetto è definita nel file `VERSION` alla radice del repository. Lo stato `static-ready / live-pending` indica che validator, test automatici e preflight clipboard sono superati, mentre la conferma finale `live-ready` richiede il test nel client Overwatch.

I check GitHub Actions correnti usano `.github/workflows/validate-workshop.yml`, con timeout di 30 minuti per permettere alla suite regressiva completa di terminare. Lo stato di un commit precedente può restare visibile nella cronologia anche dopo che il problema CI è stato corretto in un commit successivo.
