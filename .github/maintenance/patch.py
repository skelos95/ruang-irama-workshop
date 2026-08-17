from __future__ import annotations

import subprocess
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[2]

# Execute the original 0.6.21 migration directly. The two follow-up queue
# commits only repair generated Python regression tests; runtime Workshop code
# stays byte-for-byte identical to the reviewed migration.
original = subprocess.check_output(
    ["git", "show", "f451097fd3cf6cc036967c132b0e34b1b4514306:.github/maintenance/patch.py"],
    cwd=ROOT,
    text=True,
)
namespace = {"__name__": "__main__", "__file__": str(HERE)}
exec(compile(original, str(HERE), "exec"), namespace)

test_path = ROOT / "tests" / "test_validate_workshop.py"
tests = test_path.read_text(encoding="utf-8")

# Repair the generated slot/name fallback negative test quoting.
start = tests.index("    def test_cleanup_team_switch_must_find_old_roster_by_slot_or_name")
end = tests.index("    def test_vote_change_must_clear_previous_choice", start)
fixed_fallback = '''    def test_cleanup_team_switch_must_find_old_roster_by_slot_or_name(self) -> None:
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
tests = tests[:start] + fixed_fallback + tests[end:]

# The old regression expected the pre-0.6.21 direct capture. Test the new
# resolved old-roster capture instead, preserving the same comment-safety goal.
start = tests.index("    def test_commented_leave_identity_capture_is_rejected")
end = tests.index("    def test_array_assignment_inside_comment_is_rejected", start)
fixed_identity = '''    def test_commented_leave_identity_capture_is_rejected(self) -> None:
        target = "Global.PemainPembersihan = Global.IndeksKeluar >= 0 ? Global.PemainManusia[Global.IndeksKeluar] : Event Player;"
        self.assertIn(target, self.source)
        mutated = self.source.replace(target, f'"{target}"', 1)
        checks = validator.Checks()
        validator.check_cleanup_and_revenge(checks, mutated, self.rules(mutated))
        self.assertTrue(
            any("diretta → slot HUD → nome" in error for error in checks.errors),
            checks.errors,
        )

'''
tests = tests[:start] + fixed_identity + tests[end:]
test_path.write_text(tests, encoding="utf-8")

print("Repaired 0.6.21 clean-rejoin regression tests")
