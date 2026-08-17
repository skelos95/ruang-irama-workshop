from __future__ import annotations

import subprocess
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[2]

# Reuse the reviewed 0.6.22 runtime migration from the immediately previous
# queue commit. This follow-up only aligns one legacy negative-test expectation.
original = subprocess.check_output(
    ["git", "show", "53278677cc646f99b84437c296bf28a590f67948:.github/maintenance/patch.py"],
    cwd=ROOT,
    text=True,
)
namespace = {"__name__": "__main__", "__file__": str(HERE)}
exec(compile(original, str(HERE), "exec"), namespace)

test_path = ROOT / "tests" / "test_validate_workshop.py"
tests = test_path.read_text(encoding="utf-8")
old = 'self.assertTrue(any("cleanup → setup" in error for error in checks.errors), checks.errors)'
new = 'self.assertTrue(any("lock → yield → cleanup condizionale → yield → setup" in error for error in checks.errors), checks.errors)'
if tests.count(old) != 1:
    raise RuntimeError(f"legacy team-lock expectation: expected 1 occurrence, found {tests.count(old)}")
tests = tests.replace(old, new, 1)
test_path.write_text(tests, encoding="utf-8")

print("Aligned 0.6.22 deferred lifecycle lock regression test")
