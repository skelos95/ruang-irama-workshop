from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE_COMMIT = "5ffdb78d8567c841975b7b33aa095516d1032d6b"
base_patch = subprocess.check_output(
    ["git", "show", f"{BASE_COMMIT}:.github/maintenance/patch.py"],
    cwd=ROOT,
    text=True,
)

needle = 'TESTS_FILE.write_text(tests, encoding="utf-8")\n'
extra = r'''old_semantic_test = ''' + "'''" + r'''    def test_semantic_action_inside_comment_does_not_count(self) -> None:
        calls = validator.call_texts(self.source, "Disable Nameplates")
        self.assertGreaterEqual(len(calls), 1)
        simulated = self.source.replace(calls[0], f'"{calls[0]}"', 1)

        self.assertEqual(
            len(validator.call_texts(simulated, "Disable Nameplates")),
            len(calls) - 1,
        )
        checks = validator.Checks()
        validator.check_crouch(checks, simulated, self.rules(simulated))
        self.assertTrue(
            any("Disable Nameplates" in error for error in checks.errors),
            checks.errors,
        )
''' + "'''" + r'''
new_semantic_test = ''' + "'''" + r'''    def test_semantic_action_inside_comment_does_not_count(self) -> None:
        calls = validator.call_texts(self.source, "Disable Nameplates")
        self.assertGreaterEqual(len(calls), 1)
        found_required_crouch_action = False
        for call in calls:
            simulated = self.source.replace(call, f'"{call}"', 1)
            self.assertEqual(
                len(validator.call_texts(simulated, "Disable Nameplates")),
                len(calls) - 1,
            )
            checks = validator.Checks()
            validator.check_crouch(checks, simulated, self.rules(simulated))
            if any("Disable Nameplates" in error for error in checks.errors):
                found_required_crouch_action = True
                break
        self.assertTrue(found_required_crouch_action, "nessuna azione Disable Nameplates richiesta dal sistema Crouch individuata")
''' + "'''" + r'''
tests = once(tests, old_semantic_test, new_semantic_test, "semantic Disable Nameplates test")
TESTS_FILE.write_text(tests, encoding="utf-8")
'''
if base_patch.count(needle) != 1:
    raise RuntimeError("test write marker not found exactly once")
base_patch = base_patch.replace(needle, extra, 1)
exec(compile(base_patch, f"{BASE_COMMIT}:patch.py", "exec"), {"__file__": str(Path(__file__).resolve()), "__name__": "__main__"})
