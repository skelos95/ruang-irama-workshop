from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

replacements = {
    "README.md": [
        ("Stato: **live-ready**", "Stato: **static-ready / live-pending**"),
        ("I test live sono stati completati dall'utente e la stabilità della 0.8.1 è stata confermata il 24 agosto 2026; i valori diagnostici numerici non forniti non vengono ricostruiti o inventati nel repository.",
         "La 0.8.1 ha superato i gate statici ma richiede una nuova regressione live del cambio squadra prima di essere dichiarata live-ready; i valori diagnostici numerici non forniti non vengono ricostruiti o inventati nel repository."),
    ],
    "docs/PROGETTO.md": [
        ("Stato: **live-ready**", "Stato: **static-ready / live-pending**"),
        ("Le prove statiche certificano le invarianti verificabili dal repository; i test live sono stati completati dall'utente e la stabilità è stata confermata il 24 agosto 2026.",
         "Le prove statiche certificano le invarianti verificabili dal repository; la 0.8.1 richiede una nuova regressione live del cambio squadra prima del passaggio a live-ready."),
    ],
    "docs/VALIDAZIONE.md": [
        ("Stato: **live-ready**", "Stato: **static-ready / live-pending**"),
    ],
    "docs/TEST.md": [
        ("Stato: **live-ready**", "Stato: **static-ready / live-pending**"),
        ("I test live della 0.8.1 sono stati completati dall'utente e la stabilità è stata confermata il 24 agosto 2026. La matrice e il modello di registrazione restano qui come procedura di regressione; eventuali valori diagnostici numerici non forniti non vengono inventati.",
         "I test live della 0.8.0 erano stati completati; la 0.8.1 introduce un lifecycle team-switch seriale e deve completare nuovamente la matrice live prima del passaggio a live-ready. Eventuali valori diagnostici numerici non forniti non vengono inventati."),
    ],
}

for rel, pairs in replacements.items():
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    for old, new in pairs:
        if old not in text:
            raise SystemExit(f"{rel}: expected release-status text not found: {old!r}")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")

print("Marked 0.8.1 core docs static-ready / live-pending")
