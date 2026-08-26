from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IT = ROOT / "workshop" / "ruang_irama.it-IT.workshop"
EN = ROOT / "tests" / "fixtures" / "semantic_reference.txt"
RUNTIME_TEST = ROOT / "tests" / "test_runtime_maintenance.py"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
VALIDATION_DOC = ROOT / "docs" / "VALIDAZIONE.md"
PROJECT_DOC = ROOT / "docs" / "PROGETTO.md"
CHANGELOG = ROOT / "CHANGELOG.md"


def replace_exact(text: str, old: str, new: str, label: str, expected: int = 1) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"{label}: expected {expected}, found {count}")
    return text.replace(old, new, expected)


def patch_source(path: Path, global_name: str) -> None:
    text = path.read_text(encoding="utf-8")
    if "Server Load < 150" not in text:
        print(f"{path.name}: lifecycle load gate already removed")
        return

    if text.count("Server Load < 150") != 5:
        raise RuntimeError(f"{path.name}: expected 5 lifecycle load gates, found {text.count('Server Load < 150')}")

    # Initial setup worker, classifier and roster renderer are one-shot/rare lifecycle
    # operations. A transient server-load spike must not leave a human unregistered
    # or prevent the two canonical roster HUD rows from being recreated.
    text = replace_exact(
        text,
        "\n\t\tServer Load < 150;",
        "",
        f"{path.name}: line-form lifecycle load gates",
        expected=3,
    )

    pending_old = (
        f"And(Index Of Array Value({global_name}.PemainManusia, {global_name}.PemainAktif) >= 0, Server Load < 150)"
    )
    pending_new = f"Index Of Array Value({global_name}.PemainManusia, {global_name}.PemainAktif) >= 0"
    text = replace_exact(text, pending_old, pending_new, f"{path.name}: pending roster consumer load gate")

    dispatch_old = f"And(Total Time Elapsed >= {global_name}.WaktuSiklusGlobal, Server Load < 150)"
    dispatch_new = f"Total Time Elapsed >= {global_name}.WaktuSiklusGlobal"
    text = replace_exact(text, dispatch_old, dispatch_new, f"{path.name}: fresh-identity dispatcher load gate")

    if "Server Load < 150" in text:
        raise RuntimeError(f"{path.name}: stale lifecycle load gate remains")

    path.write_text(text, encoding="utf-8")
    print(f"patched {path.relative_to(ROOT)}")


def patch_runtime_test() -> None:
    text = RUNTIME_TEST.read_text(encoding="utf-8")
    text = replace_exact(
        text,
        '            self.assertIn("Server Load < 150", fast)\n',
        '            self.assertNotIn("Server Load < 150", fast)\n',
        "runtime: fast lifecycle load assertion",
    )

    classifier_anchor = '            self.assertNotIn(f"Abort If(Count Of({global_name}.SlotHUDTersedia) == 0);", classifier)\n'
    classifier_add = classifier_anchor + '            self.assertNotIn("Server Load < 150", classifier)\n'
    text = replace_exact(text, classifier_anchor, classifier_add, "runtime: classifier no-load regression")

    roster_anchor = '            self.assertNotIn("Is Alive(Event Player) == True;", roster_hud)\n'
    roster_add = roster_anchor + '            self.assertNotIn("Server Load < 150", roster_hud)\n'
    text = replace_exact(text, roster_anchor, roster_add, "runtime: roster no-load regression")

    worker_anchor = '            self.assertNotIn("Call Subroutine(BersihkanPemain);", fast)\n'
    worker_add = (
        worker_anchor
        + f'            setup_worker = source.split(f\'{{rule_kw}}("01b - Siklus tim: Pekerja penyiapan dari penjadwal global")\', 1)[1].split(f\'{{rule_kw}}("02 - Pemain\', 1)[0]\n'
        + '            self.assertNotIn("Server Load < 150", setup_worker)\n'
    )
    text = replace_exact(text, worker_anchor, worker_add, "runtime: setup worker no-load regression")

    RUNTIME_TEST.write_text(text, encoding="utf-8")
    print("patched tests/test_runtime_maintenance.py")


def patch_validator() -> None:
    text = VALIDATOR.read_text(encoding="utf-8")

    text = replace_exact(
        text,
        '            "Server Load < 150",\n',
        "",
        "validator: dispatcher/pending load requirements",
        expected=2,
    )
    text = replace_exact(
        text,
        '            "Server Load < 150;",\n',
        "",
        "validator: setup-worker load requirement",
    )

    fast_anchor = '            checks.require(token in fast.body, f"dispatcher team-switch leggero incompleto: {token}")\n\n'
    fast_add = (
        fast_anchor
        + '        checks.require("Server Load < 150" not in fast.body,\n'
        + '                       "dispatcher team-switch non deve dipendere da Server Load < 150")\n\n'
    )
    text = replace_exact(text, fast_anchor, fast_add, "validator: fast no-load gate")

    pending_anchor = '                checks.require(token in pending_header, f"consumer roster pending senza guardia: {token}")\n'
    pending_add = (
        pending_anchor
        + '            checks.require("Server Load < 150" not in pending_header,\n'
        + '                           "consumer roster pending non deve dipendere dal carico server")\n'
    )
    text = replace_exact(text, pending_anchor, pending_add, "validator: pending no-load gate")

    setup_anchor = '            checks.require(token in conditions, f"worker setup iniziale senza guardia: {token}")\n'
    setup_add = (
        setup_anchor
        + '        checks.require("Server Load < 150" not in conditions,\n'
        + '                       "worker setup iniziale non deve dipendere dal carico server")\n'
    )
    text = replace_exact(text, setup_anchor, setup_add, "validator: setup no-load gate")

    roster_anchor = (
        '        checks.require(\n'
        '            "Is Alive(Event Player) == True;" not in roster_conditions,\n'
        '            "renderer roster non deve attendere Is Alive e bloccare il lifecycle globale",\n'
        '        )\n'
    )
    roster_add = (
        roster_anchor
        + '        checks.require("Server Load < 150" not in roster_conditions,\n'
        + '                       "renderer roster non deve dipendere dal carico server")\n'
    )
    text = replace_exact(text, roster_anchor, roster_add, "validator: roster no-load gate")

    VALIDATOR.write_text(text, encoding="utf-8")
    print("patched tools/validate_workshop.py")


def patch_docs() -> None:
    validation = VALIDATION_DOC.read_text(encoding="utf-8")
    validation = replace_exact(
        validation,
        "il consumer richiede scadenza raggiunta, Team stabile, spawned, alive, indice roster valido e carico sotto soglia, quindi sostituisce gli handle canonici",
        "il consumer richiede scadenza raggiunta, Team stabile, spawned, alive e indice roster valido, ma non dipende dal carico server; quindi sostituisce gli handle canonici",
        "VALIDAZIONE lifecycle load wording",
    )
    VALIDATION_DOC.write_text(validation, encoding="utf-8")

    project = PROJECT_DOC.read_text(encoding="utf-8")
    project = replace_exact(
        project,
        "Il consumer attende la scadenza, Team stabile, `Has Spawned`, `Is Alive`, indice roster valido e `Server Load < 150`; poi distrugge gli handle canonici negli array globali, azzera gli handle locali e permette a `02b` di ricreare `HudKiri/HudKanan`.",
        "Il consumer attende la scadenza, Team stabile, `Has Spawned`, `Is Alive` e indice roster valido; non usa un gate di `Server Load`, perché un picco di carico non deve lasciare `SegarkanRosterTertunda` bloccato. Poi distrugge gli handle canonici negli array globali, azzera gli handle locali e permette a `02b` di ricreare `HudKiri/HudKanan`.",
        "PROGETTO team-switch load wording",
    )
    PROJECT_DOC.write_text(project, encoding="utf-8")

    changelog = CHANGELOG.read_text(encoding="utf-8")
    note = "- Corretto il deadlock live del roster dopo il cambio squadra: il lifecycle essenziale (setup, classificazione, consumer `SegarkanRosterTertunda` e renderer `02b`) non è più bloccato da `Server Load < 150`. Un picco di carico non può quindi lasciare vuote le righe `LOBBY & CHILL TIME` / `PLAYER VIBES` né escludere indefinitamente il player dai target Crouch.\n"
    if note not in changelog:
        anchor = "Stato: **live-pending**.\n\n"
        changelog = replace_exact(changelog, anchor, anchor + note, "CHANGELOG load-gate note")
        CHANGELOG.write_text(changelog, encoding="utf-8")


patch_source(IT, "Globale")
patch_source(EN, "Global")
patch_runtime_test()
patch_validator()
patch_docs()
print("Roster lifecycle load-gate fix applied")
