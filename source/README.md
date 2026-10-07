# Specifica comportamentale

`ruang_irama.it-IT.source` è l'input del compilatore globale, equivalente alla
specifica inglese `tests/fixtures/semantic_reference.txt`. I contratti e i test
comportamentali si applicano a questi input.

Le regole per-player nella specifica vengono trasformate in controller atomici,
timer e registrazioni di eventi eseguiti dallo scheduler globale. Non copiare
questa specifica nel gioco: usa [il clipboard generato](../workshop/ruang_irama.it-IT.workshop).

```text
python tools/build_global_runtime.py
python tools/build_global_runtime.py --check
python tools/validate_workshop.py
```

La generazione e i gate del runtime non provano l'assenza di crash nel motore
Overwatch. [Architettura](../docs/PROGETTO.md) · [Validazione](../docs/VALIDAZIONE.md)
