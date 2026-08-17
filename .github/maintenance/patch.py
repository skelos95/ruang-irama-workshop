from __future__ import annotations

import subprocess
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[2]

# Reuse the already-reviewed 0.6.21 migration from the immediately previous
# queue commit, then repair only the generated negative test whose quoting was
# invalid Python. The runtime Workshop migration itself is unchanged.
previous = subprocess.check_output(
    ["git", "show", "HEAD^:.github/maintenance/patch.py"],
    cwd=ROOT,
    text=True,
)
namespace = {"__name__": "__main__", "__file__": str(HERE)}
exec(compile(previous, str(HERE), "exec"), namespace)

test_path = ROOT / "tests" / "test_validate_workshop.py"
tests = test_path.read_text(encoding="utf-8")
start = tests.index("    def test_cleanup_team_switch_must_find_old_roster_by_slot_or_name")
end = tests.index("    def test_vote_change_must_clear_previous_choice", start)
fixed = '''    def test_cleanup_team_switch_must_find_old_roster_by_slot_or_name(self) -> None:
        target = """\t\tIf(Global.IndeksKeluar < 0);
\t\t\tGlobal.IndeksKeluar = Index Of Array Value(Mapped Array(Global.PemainManusia, Custom String("{0}", Current Array Element)),
\t\t\t\tCustom String("{0}", Event Player));
\t\tEnd;
"""
        mutated = self.source.replace(target, "", 1)
        self.assertNotEqual(mutated, self.source)
        checks = validator.Checks()
        validator.check_cleanup_and_revenge(checks, mutated, self.rules(mutated))
        self.assertTrue(any("slot HUD → nome" in error for error in checks.errors), checks.errors)

'''
tests = tests[:start] + fixed + tests[end:]
test_path.write_text(tests, encoding="utf-8")

print("Repaired 0.6.21 clean-rejoin regression test quoting")
