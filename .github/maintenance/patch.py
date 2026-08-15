from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
validator = ROOT / "tools" / "validate_workshop.py"
readme = ROOT / "README.md"
project = ROOT / "docs" / "PROGETTO.md"

text = validator.read_text(encoding="utf-8")

old_constants = '''WORKFLOW = ROOT / ".github" / "workflows" / "validate-workshop.yml"\nLEGACY_AUTOMATION = (\n    ROOT / ".github" / "trigger-camera-bots",\n    ROOT / ".github" / "workflows" / "patch-camera-bots.yml",\n)\n'''
new_constants = '''WORKFLOW = ROOT / ".github" / "workflows" / "validate-workshop.yml"\nMAINTENANCE_WORKFLOW = ROOT / ".github" / "workflows" / "maintenance-patch.yml"\nALLOWED_WORKFLOW_NAMES = {"validate-workshop.yml", "maintenance-patch.yml"}\nLEGACY_AUTOMATION = (\n    ROOT / ".github" / "trigger-camera-bots",\n    ROOT / ".github" / "workflows" / "patch-camera-bots.yml",\n)\n'''
if old_constants not in text:
    raise SystemExit("validator constants anchor not found")
text = text.replace(old_constants, new_constants, 1)

anchor = '''def check_documentation_and_ci(checks: Checks, genres: list[str]) -> None:\n'''
maintenance_check = r'''def check_maintenance_workflow_text(checks: Checks, workflow: str) -> None:
    """Valida il runner permanente usato per applicare patch senza YAML dinamico."""
    clean = strip_yaml_comments(workflow)
    checks.require("\t" not in clean, "maintenance workflow: vietati tab YAML")
    for token in (
        "name: Apply Maintenance Patch",
        "      - '.github/maintenance/patch.py'",
        "  contents: write",
        "  group: maintenance-patch-main",
        "  cancel-in-progress: false",
        "    if: github.actor != 'github-actions[bot]'",
        "    timeout-minutes: 10",
        "uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
        "uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97",
        "run: python .github/maintenance/patch.py",
        "run: python -m unittest discover -s tests -p 'test_*.py'",
        "run: python tools/validate_workshop.py",
        "Maintenance patches may not modify workflow files.",
        "git diff --check",
        "rm -f .github/maintenance/patch.py",
        "git diff --cached --check",
        "git commit -m \"Apply validated maintenance patch\"",
        "git push origin HEAD:main",
    ):
        checks.require(token in clean, f"maintenance workflow incompleto: {token}")

    checks.require(
        "workflow_dispatch:" not in clean,
        "maintenance workflow non deve poter essere avviato senza un patch.py versionato",
    )
    checks.require(
        "pull_request:" not in clean,
        "maintenance workflow non deve girare sulle pull request",
    )


'''
if anchor not in text:
    raise SystemExit("documentation checker anchor not found")
text = text.replace(anchor, maintenance_check + anchor, 1)

old_ci_tail = '''    checks.require(WORKFLOW.exists(), f"workflow read-only mancante: {WORKFLOW.relative_to(ROOT)}")\n    if WORKFLOW.exists():\n        check_workflow_text(checks, WORKFLOW.read_text(encoding="utf-8"))\n'''
new_ci_tail = '''    checks.require(WORKFLOW.exists(), f"workflow read-only mancante: {WORKFLOW.relative_to(ROOT)}")\n    if WORKFLOW.exists():\n        check_workflow_text(checks, WORKFLOW.read_text(encoding="utf-8"))\n\n    checks.require(\n        MAINTENANCE_WORKFLOW.exists(),\n        f"workflow manutenzione permanente mancante: {MAINTENANCE_WORKFLOW.relative_to(ROOT)}",\n    )\n    if MAINTENANCE_WORKFLOW.exists():\n        check_maintenance_workflow_text(\n            checks, MAINTENANCE_WORKFLOW.read_text(encoding="utf-8")\n        )\n\n    workflow_dir = ROOT / ".github" / "workflows"\n    workflow_names = {\n        path.name\n        for path in workflow_dir.iterdir()\n        if path.is_file() and path.suffix in {".yml", ".yaml"}\n    } if workflow_dir.exists() else set()\n    checks.equal(\n        workflow_names,\n        ALLOWED_WORKFLOW_NAMES,\n        "workflow consentiti; i runner temporanei sono vietati",\n    )\n'''
if old_ci_tail not in text:
    raise SystemExit("CI checker tail anchor not found")
text = text.replace(old_ci_tail, new_ci_tail, 1)
validator.write_text(text, encoding="utf-8")

r = readme.read_text(encoding="utf-8")
marker = "- I controlli statici non possono certificare il comportamento live del parser, la sentinella bot o la stabilità a 12 giocatori. Lo stato verificato è riportato in [`docs/VALIDAZIONE.md`](docs/VALIDAZIONE.md)."
addition = marker + "\n- Le modifiche automatizzate usano un runner permanente (`maintenance-patch.yml`) attivato solo da `.github/maintenance/patch.py`; il validatore vieta altri workflow temporanei, evitando YAML dinamico malformato e runner con `jobs: []`."
if marker not in r:
    raise SystemExit("README maintenance marker not found")
r = r.replace(marker, addition, 1)
readme.write_text(r, encoding="utf-8")

p = project.read_text(encoding="utf-8")
section = '''\n\n## Manutenzione automatizzata\n\nLe patch repository non richiedono più workflow YAML temporanei. Il workflow permanente `.github/workflows/maintenance-patch.yml` si attiva esclusivamente quando viene aggiunto `.github/maintenance/patch.py`, esegue la patch, i test unitari e il validatore, impedisce alla patch di modificare `.github/workflows`, quindi committa il risultato e rimuove lo script di manutenzione. Il validatore ammette soltanto `validate-workshop.yml` e `maintenance-patch.yml`: qualsiasi runner temporaneo aggiuntivo fa fallire il gate statico.\n'''
if "## Manutenzione automatizzata" not in p:
    p += section
project.write_text(p, encoding="utf-8")
