from __future__ import annotations

import subprocess

ORIGINAL_COMMIT = "5ef4d51ca85bb8d017fb5c05bd2d1ecfdcf6ad35"
PATCH_PATH = ".github/maintenance/patch.py"


def original_patch() -> str:
    result = subprocess.run(
        ["git", "show", f"{ORIGINAL_COMMIT}:{PATCH_PATH}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


code = original_patch()

# replace_region keeps the end marker from the original source, therefore the
# replacement for rule 18e must not append the 18f marker a second time.
old = 'source = replace_region(source, luck_rule_start, luck_rule_end, luck_rule + luck_rule_end, "replace Try Your Luck outcome")'
new = 'source = replace_region(source, luck_rule_start, luck_rule_end, luck_rule, "replace Try Your Luck outcome")'
if code.count(old) != 1:
    raise RuntimeError(f"18e/18f correction: expected 1 occurrence, found {code.count(old)}")
code = code.replace(old, new, 1)

# Scope the new menu-lock negative test to rule 05c. The source already has a
# different KartuNasibAktif guard in rule 05, and a global replace could mutate
# the wrong rule instead of proving the dispatcher lock.
old = '''    def test_luck_menu_must_stay_open_and_locked(self) -> None:\n        mutated = self.source.replace(\n            "Event Player.KartuNasibAktif == False;",\n            '\"Event Player.KartuNasibAktif == False;\"',\n            1,\n        )\n        self.assertNotEqual(mutated, self.source)\n        checks = validator.Checks()\n        validator.check_arcade_features(checks, mutated, self.rules(mutated))\n        self.assertTrue(any("dispatcher menu non bloccato" in error for error in checks.errors), checks.errors)\n'''
new = '''    def test_luck_menu_must_stay_open_and_locked(self) -> None:\n        dispatcher_at = self.source.index('rule("05c - ')\n        dispatcher_end = self.source.index('\\nrule("05d - ', dispatcher_at)\n        dispatcher = self.source[dispatcher_at:dispatcher_end]\n        dispatcher2 = dispatcher.replace(\n            "Event Player.KartuNasibAktif == False;",\n            '\"Event Player.KartuNasibAktif == False;\"',\n            1,\n        )\n        self.assertNotEqual(dispatcher2, dispatcher)\n        mutated = self.source[:dispatcher_at] + dispatcher2 + self.source[dispatcher_end:]\n        checks = validator.Checks()\n        validator.check_arcade_features(checks, mutated, self.rules(mutated))\n        self.assertTrue(any("dispatcher menu non bloccato" in error for error in checks.errors), checks.errors)\n'''
if code.count(old) != 1:
    raise RuntimeError(f"menu lock test correction: expected 1 occurrence, found {code.count(old)}")
code = code.replace(old, new, 1)

exec(compile(code, PATCH_PATH, "exec"), {"__name__": "__main__", "__file__": PATCH_PATH})
