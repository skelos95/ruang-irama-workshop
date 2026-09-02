#!/usr/bin/env python3
"""Release-state metadata checks kept separate from Workshop semantics.

The semantic validator remains intentionally independent from the release
promotion. A LIVE_READY marker opts the repository into this stricter metadata
contract after the client regression has been completed.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Iterable

LIVE_READY_DATE = "2026-09-02"


def validate_live_ready_metadata(
    checks,
    root: Path,
    *,
    version: str,
    core_docs: Iterable[str],
    current_release_claims: Callable[[str], tuple[bool, bool]],
    obsolete_patterns,
    allowed_workflows: set[str],
) -> None:
    version_file = root / "VERSION"
    checks.require(version_file.is_file(), "VERSION assente")
    if version_file.is_file():
        checks.equal(version_file.read_text(encoding="utf-8").strip(), version, "VERSION")

    marker = root / "LIVE_READY"
    checks.require(marker.is_file(), "marker LIVE_READY assente")
    if marker.is_file():
        expected_marker = f"version: {version}\ndate: {LIVE_READY_DATE}\n"
        checks.equal(marker.read_text(encoding="utf-8"), expected_marker, "contenuto LIVE_READY")

    for relative in core_docs:
        path = root / relative
        checks.require(path.is_file(), f"documento obbligatorio assente: {relative}")
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        checks.require(version in text, f"documento non allineato a {version}: {relative}")
        checks.require(
            "Stato: **live-ready**" in text,
            f"documento non dichiara Stato: **live-ready**: {relative}",
        )
        checks.require(
            "Stato: **static-ready / live-pending**" not in text,
            f"documento conserva lo stato pre-release: {relative}",
        )
        live_ready, published = current_release_claims(text)
        checks.require(
            live_ready,
            f"documento non contiene un'affermazione live-ready assertiva per {version}: {relative}",
        )
        checks.require(
            not published,
            f"documento dichiara pubblicato un tag/release v{version} non creato: {relative}",
        )
        for label, pattern in obsolete_patterns:
            checks.require(
                pattern.search(text) is None,
                f"documento contiene testo lifecycle obsoleto ({relative}): {label}",
            )

    changelog = root / "CHANGELOG.md"
    checks.require(changelog.is_file(), "CHANGELOG.md assente")
    if changelog.is_file():
        changelog_text = changelog.read_text(encoding="utf-8")
        current_section_match = re.search(
            rf"(?ms)^##\s+v?{re.escape(version)}\b.*?(?=^##\s+|\Z)",
            changelog_text,
        )
        checks.require(current_section_match is not None, f"CHANGELOG.md senza sezione corrente {version}")
        if current_section_match is not None:
            current_section = current_section_match.group(0)
            checks.require(
                re.search(r"(?im)^\s*Stato:\s*\*\*live-ready\*\*\.\s*$", current_section) is not None,
                f"CHANGELOG.md: la sezione {version} deve essere live-ready",
            )
            live_ready, published = current_release_claims(current_section)
            checks.require(live_ready, f"CHANGELOG.md non dichiara live-ready per {version}")
            checks.require(
                not published,
                f"CHANGELOG.md dichiara pubblicato un tag/release v{version} non creato",
            )
            for label, pattern in obsolete_patterns:
                checks.require(
                    pattern.search(current_section) is None,
                    f"CHANGELOG.md contiene testo lifecycle obsoleto: {label}",
                )

    github = root / ".github"
    github_entries = {
        path.relative_to(github).as_posix()
        for path in github.rglob("*")
    } if github.is_dir() else set()
    checks.equal(
        github_entries,
        {"workflows", "workflows/validate-workshop.yml"},
        "contenuti permanenti .github",
    )

    workflows = github / "workflows"
    found = {path.name for path in workflows.glob("*.yml")} | {path.name for path in workflows.glob("*.yaml")}
    checks.equal(found, allowed_workflows, "workflow permanenti")
    validation = workflows / "validate-workshop.yml"
    if validation.is_file():
        workflow_text = validation.read_text(encoding="utf-8")
        checks.require(re.search(r"(?m)^\s*push\s*:", workflow_text) is not None,
                       "workflow validazione deve attivarsi su push")
        checks.require("tools/validate_workshop.py" in workflow_text,
                       "workflow non esegue il validatore semantico")
        checks.require("unittest" in workflow_text,
                       "workflow non esegue gli unit test")
        checks.require("timeout-minutes: 45" in workflow_text,
                       "workflow validazione deve avere 45 minuti di margine")
        checks.require('${{ github.event.before }}..${{ github.sha }}' in workflow_text,
                       "push diff-check deve coprire l'intero range before..sha")
        checks.require('github.event_name == "push"' in workflow_text,
                       "workflow diff-check deve distinguere esplicitamente i push")
        checks.require("git add -A" not in workflow_text and "git push" not in workflow_text,
                       "workflow validazione non deve modificare o pubblicare il repository")
