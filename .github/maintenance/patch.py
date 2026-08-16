from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Reuse the complete 0.6.2 feature patch from the parent commit. The previous
# maintenance run failed only because one regression test became ambiguous after
# BersihkanPemain legitimately added another Stop Modifying Hero Voice Lines.
previous = subprocess.check_output(
    ["git", "show", "HEAD^:.github/maintenance/patch.py"],
    cwd=ROOT,
    text=True,
)
exec(compile(previous, "previous_maintenance_patch.py", "exec"), {"__name__": "__main__", "__file__": str(ROOT / ".github/maintenance/patch.py")})

# Scope the legacy voice test to the Menu 6 interaction region, so cleanup voice
# restoration does not satisfy the test accidentally.
tests_path = ROOT / "tests/test_validate_workshop.py"
tests = tests_path.read_text(encoding="utf-8")
old = '''    def test_voice_normal_stop_is_required(self) -> None:\n        mutated = self.source.replace(\n            "Stop Modifying Hero Voice Lines(Event Player);",\n            '\"Stop Modifying Hero Voice Lines(Event Player);\"',\n            1,\n        )\n        self.assertNotEqual(mutated, self.source)\n        checks = validator.Checks()\n        validator.check_arcade_features(checks, mutated, self.rules(mutated))\n        self.assertTrue(any("Stop Modifying Hero Voice Lines" in error for error in checks.errors), checks.errors)\n'''
new = '''    def test_voice_normal_stop_is_required(self) -> None:\n        menu_at = self.source.index('rule("10 - Menu:')\n        menu_end = self.source.index('\\nrule("11 - ', menu_at)\n        menu = self.source[menu_at:menu_end]\n        menu2 = menu.replace(\n            "Stop Modifying Hero Voice Lines(Event Player);",\n            '\"Stop Modifying Hero Voice Lines(Event Player);\"',\n            1,\n        )\n        self.assertNotEqual(menu2, menu)\n        mutated = self.source[:menu_at] + menu2 + self.source[menu_end:]\n        checks = validator.Checks()\n        validator.check_arcade_features(checks, mutated, self.rules(mutated))\n        self.assertTrue(any("Stop Modifying Hero Voice Lines" in error for error in checks.errors), checks.errors)\n'''
if tests.count(old) != 1:
    raise RuntimeError("voice regression test block not found exactly once")
tests_path.write_text(tests.replace(old, new, 1), encoding="utf-8")
