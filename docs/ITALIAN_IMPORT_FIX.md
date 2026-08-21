# Correzione import Workshop it-IT

Questa modifica rende `workshop/ruang_irama.it-IT.workshop` l'unico file Workshop destinato al copia/incolla nel client italiano.

Il problema osservato nel client (`richiesta un'opzione dopo 'Color('`) deriva da literal contestuali localizzati in modo troppo aggressivo. La correzione usa una conversione conservativa e mantiene i literal ambigui nella forma accettata dal parser.
