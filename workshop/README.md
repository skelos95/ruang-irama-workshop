# Workshop source

`ruang_irama.it-IT.workshop` è il sorgente canonico da copiare negli Appunti del Workshop di Overwatch per la localizzazione italiana.

La versione corrente del progetto è definita nel file `VERSION` alla radice del repository. La **0.8.1** è `live-ready`: i gate statici sono verdi e la regressione nel client Overwatch è stata completata con esito positivo il 2 settembre 2026. I valori diagnostici numerici non forniti non vengono ricostruiti o inventati nel repository.

I check GitHub Actions correnti usano `.github/workflows/validate-workshop.yml`, con timeout di 45 minuti per lasciare margine alla suite regressiva completa. Sui push il controllo whitespace copre l'intero range `before..sha`; sulle pull request continua a controllare il range rispetto alla base.
