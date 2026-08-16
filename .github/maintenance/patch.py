from __future__ import annotations

import subprocess
from pathlib import Path

ORIGINAL_COMMIT = "5ef4d51ca85bb8d017fb5c05bd2d1ecfdcf6ad35"
PATCH_PATH = ".github/maintenance/patch.py"
TESTS_PATH = Path("tests/test_validate_workshop.py")


def original_patch() -> str:
    return subprocess.run(
        ["git", "show", f"{ORIGINAL_COMMIT}:{PATCH_PATH}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


code = original_patch()

# replace_region already preserves the end marker.
needle = "luck_rule + luck_rule_end"
if code.count(needle) != 1:
    raise RuntimeError(f"18e/18f correction: expected 1 occurrence, found {code.count(needle)}")
code = code.replace(needle, "luck_rule", 1)

# The old death anchor exists both in rule 18f and common lifecycle cleanup.
# Scope the replacement explicitly to rule 18f instead of requiring a global
# one-occurrence match.
old_call = 'source = replace_once(source, death_cleanup_anchor, death_cleanup_replacement, "death roulette cleanup")'
new_call = '''death_rule_at = source.find(luck_rule_end)\nif death_rule_at < 0:\n    raise RuntimeError("death roulette cleanup: rule 18f not found")\ndeath_rule_next = source.find('\\n\\nrule("19 - ', death_rule_at)\nif death_rule_next < 0:\n    raise RuntimeError("death roulette cleanup: rule 19 marker not found")\ndeath_rule_body = source[death_rule_at:death_rule_next]\nif death_rule_body.count(death_cleanup_anchor) != 1:\n    raise RuntimeError(f"death roulette cleanup: expected 1 occurrence in rule 18f, found {death_rule_body.count(death_cleanup_anchor)}")\ndeath_rule_body = death_rule_body.replace(death_cleanup_anchor, death_cleanup_replacement, 1)\nsource = source[:death_rule_at] + death_rule_body + source[death_rule_next:]'''
if code.count(old_call) != 1:
    raise RuntimeError(f"death cleanup call correction: expected 1 occurrence, found {code.count(old_call)}")
code = code.replace(old_call, new_call, 1)

exec(compile(code, PATCH_PATH, "exec"), {"__name__": "__main__", "__file__": PATCH_PATH})

# Fix the newly generated menu-lock negative test so it mutates rule 05c,
# rather than the older KartuNasibAktif guard in rule 05.
tests = TESTS_PATH.read_text(encoding="utf-8")
method_start = tests.find("    def test_luck_menu_must_stay_open_and_locked(self) -> None:\n")
method_end = tests.find("\n    def test_luck_red_must_force_position_and_shrink_ring", method_start)
if method_start < 0 or method_end < 0:
    raise RuntimeError("menu lock test correction: method markers not found")
new_method = '''    def test_luck_menu_must_stay_open_and_locked(self) -> None:\n        dispatcher_at = self.source.index('rule("05c - ')\n        dispatcher_end = self.source.index('\\nrule("05d - ', dispatcher_at)\n        dispatcher = self.source[dispatcher_at:dispatcher_end]\n        dispatcher2 = dispatcher.replace(\n            "Event Player.KartuNasibAktif == False;",\n            '\"Event Player.KartuNasibAktif == False;\"',\n            1,\n        )\n        self.assertNotEqual(dispatcher2, dispatcher)\n        mutated = self.source[:dispatcher_at] + dispatcher2 + self.source[dispatcher_end:]\n        checks = validator.Checks()\n        validator.check_arcade_features(checks, mutated, self.rules(mutated))\n        self.assertTrue(any("dispatcher menu non bloccato" in error for error in checks.errors), checks.errors)\n'''
tests = tests[:method_start] + new_method + tests[method_end:]
TESTS_PATH.write_text(tests, encoding="utf-8")

Path("PATCH_DIAGNOSTIC.txt").unlink(missing_ok=True)
