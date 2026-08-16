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

# replace_region already preserves the end marker from the source.
needle = "luck_rule + luck_rule_end"
if code.count(needle) != 1:
    raise RuntimeError(f"18e/18f correction: expected 1 occurrence, found {code.count(needle)}")
code = code.replace(needle, "luck_rule", 1)

# Scope the menu-lock negative test to rule 05c. There is an older roulette
# guard in rule 05, so a whole-file replace would mutate the wrong occurrence.
method_start = code.find("    def test_luck_menu_must_stay_open_and_locked(self) -> None:\\n")
method_end = code.find("\\n    def test_luck_red_must_force_position_and_shrink_ring", method_start)
if method_start < 0 or method_end < 0:
    raise RuntimeError("menu lock test correction: method markers not found")
old_method = code[method_start:method_end]
new_method = '''    def test_luck_menu_must_stay_open_and_locked(self) -> None:\n        dispatcher_at = self.source.index('rule("05c - ')\n        dispatcher_end = self.source.index('\\nrule("05d - ', dispatcher_at)\n        dispatcher = self.source[dispatcher_at:dispatcher_end]\n        dispatcher2 = dispatcher.replace(\n            "Event Player.KartuNasibAktif == False;",\n            '\"Event Player.KartuNasibAktif == False;\"',\n            1,\n        )\n        self.assertNotEqual(dispatcher2, dispatcher)\n        mutated = self.source[:dispatcher_at] + dispatcher2 + self.source[dispatcher_end:]\n        checks = validator.Checks()\n        validator.check_arcade_features(checks, mutated, self.rules(mutated))\n        self.assertTrue(any("dispatcher menu non bloccato" in error for error in checks.errors), checks.errors)\n'''
code = code[:method_start] + new_method.replace("\n", "\\n") + code[method_end:]

exec(compile(code, PATCH_PATH, "exec"), {"__name__": "__main__", "__file__": PATCH_PATH})
