from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools import validate_release_metadata as release
from tools import validate_workshop_core as core


class LiveReadyMetadataTests(unittest.TestCase):
    def make_repo(self, root: Path) -> None:
        (root / ".github" / "workflows").mkdir(parents=True)
        (root / "docs").mkdir()
        (root / "VERSION").write_text("0.8.1\n", encoding="utf-8")
        (root / "LIVE_READY").write_text(
            "version: 0.8.1\ndate: 2026-09-02\n", encoding="utf-8"
        )
        doc = (
            "Versione 0.8.1\n"
            "Stato: **live-ready**\n"
            "La versione 0.8.1 ha raggiunto live-ready dopo la regressione nel client.\n"
        )
        for relative in core.CORE_DOCS:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(doc, encoding="utf-8")
        (root / "CHANGELOG.md").write_text(
            "# Changelog\n\n## v0.8.1 — 2026-08-25\n\n"
            "Stato: **live-ready**.\n\n"
            "La versione 0.8.1 ha raggiunto live-ready dopo la regressione nel client.\n",
            encoding="utf-8",
        )
        (root / ".github" / "workflows" / "validate-workshop.yml").write_text(
            "name: Validate Workshop\n"
            "on:\n  push:\n  pull_request:\n"
            "jobs:\n  validate:\n    timeout-minutes: 45\n    steps:\n"
            "      - run: |\n"
            "          if [[ \"${{ github.event_name }}\" == \"push\" ]]; then\n"
            "            git diff --check \"${{ github.event.before }}..${{ github.sha }}\"\n"
            "          fi\n"
            "      - run: python -m unittest discover -s tests -p 'test_*.py'\n"
            "      - run: python tools/validate_workshop.py\n",
            encoding="utf-8",
        )

    def validate(self, root: Path) -> list[str]:
        checks = core.Checks()
        release.validate_live_ready_metadata(
            checks,
            root,
            version=core.CURRENT_VERSION,
            core_docs=core.CORE_DOCS,
            current_release_claims=core.current_release_claims,
            obsolete_patterns=core.OBSOLETE_CURRENT_TEXT_PATTERNS,
            allowed_workflows=core.ALLOWED_WORKFLOWS,
        )
        return checks.errors

    def test_live_ready_contract_accepts_confirmed_release(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            self.assertEqual(self.validate(root), [])

    def test_live_ready_contract_rejects_stale_pending_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            path = root / "README.md"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "Stato: **live-ready**", "Stato: **static-ready / live-pending**"
                ),
                encoding="utf-8",
            )
            self.assertTrue(any("live-ready" in error for error in self.validate(root)))

    def test_live_ready_contract_requires_full_push_diff_range(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            workflow = root / ".github" / "workflows" / "validate-workshop.yml"
            workflow.write_text(
                workflow.read_text(encoding="utf-8").replace(
                    '${{ github.event.before }}..${{ github.sha }}', "HEAD^ HEAD"
                ),
                encoding="utf-8",
            )
            self.assertTrue(any("before..sha" in error for error in self.validate(root)))


if __name__ == "__main__":
    unittest.main()
