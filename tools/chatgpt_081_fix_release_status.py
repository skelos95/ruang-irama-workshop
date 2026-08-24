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

# 0.8.1 must remain live-pending until the new team-switch lifecycle passes client tests.
validator = ROOT / "tools" / "validate_workshop.py"
v = validator.read_text(encoding="utf-8")
old_policy = '''            checks.require(
                "Stato: **live-ready**" in text,
                f"documento non dichiara Stato: **live-ready**: {relative}",
            )
            checks.require(
                "Stato: **static-ready / live-pending**" not in text,
                f"documento conserva lo stato live-pending: {relative}",
            )'''
new_policy = '''            checks.require(
                "Stato: **static-ready / live-pending**" in text,
                f"documento non dichiara Stato: **static-ready / live-pending**: {relative}",
            )
            checks.require(
                "Stato: **live-ready**" not in text,
                f"documento dichiara live-ready prima della regressione client: {relative}",
            )'''
if v.count(old_policy) != 1:
    raise SystemExit(f"validator release policy occurrence count: {v.count(old_policy)}")
v = v.replace(old_policy, new_policy, 1)
validator.write_text(v, encoding="utf-8")

# Keep repository metadata tests aligned with the 0.8.1 release phase.
test_path = ROOT / "tests" / "test_validate_workshop.py"
t = test_path.read_text(encoding="utf-8")
t = t.replace("class SemanticWorkshop080Tests", "class SemanticWorkshop081Tests", 1)
start = t.index("class RepositoryMetadataTests")
head, tail = t[:start], t[start:]
tail = tail.replace("0.8.0", "0.8.1")
old_make = 'path.write_text("CHILL 0.8.1\\nStato: **live-ready**\\n", encoding="utf-8")'
new_make = 'path.write_text("CHILL 0.8.1\\nStato: **static-ready / live-pending**\\n", encoding="utf-8")'
if tail.count(old_make) != 1:
    raise SystemExit(f"metadata make_repo live-ready occurrence count: {tail.count(old_make)}")
tail = tail.replace(old_make, new_make, 1)
old_test = '''    def test_live_pending_document_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            (root / "README.md").write_text(
                "CHILL 0.8.1\\nStato: **static-ready / live-pending**\\n",
                encoding="utf-8",
            )
            errors = self.metadata_errors(root)
            self.assertTrue(any("live-ready" in error or "live-pending" in error for error in errors))
'''
new_test = '''    def test_live_ready_document_is_rejected_before_client_regression(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            (root / "README.md").write_text(
                "CHILL 0.8.1\\nStato: **live-ready**\\n",
                encoding="utf-8",
            )
            errors = self.metadata_errors(root)
            self.assertTrue(any("live-ready" in error or "live-pending" in error for error in errors))
'''
if tail.count(old_test) != 1:
    raise SystemExit(f"metadata live-pending test occurrence count: {tail.count(old_test)}")
tail = tail.replace(old_test, new_test, 1)
test_path.write_text(head + tail, encoding="utf-8")

print("Marked 0.8.1 static-ready / live-pending and aligned metadata gate/tests")
