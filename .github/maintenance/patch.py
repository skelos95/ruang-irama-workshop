from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

feature_patch = subprocess.check_output(
    ["git", "show", "5deb58b6f9f42fd884c23acd67065c1ffcd2d9b4:.github/maintenance/patch.py"],
    cwd=ROOT,
    text=True,
)
exec(
    compile(feature_patch, "team_switch_0_6_2.py", "exec"),
    {"__name__": "__main__", "__file__": str(ROOT / ".github/maintenance/patch.py")},
)

validator_path = ROOT / "tools/validate_workshop.py"
validator = validator_path.read_text(encoding="utf-8")

# Remove the old source-wide Stop-voice token from the generic feature list.
generic_anchor = '    for token in (\n        "Set Status(Event Player, Null, Unkillable, 9999);",'
generic_at = validator.index(generic_anchor)
token = '        "Stop Modifying Hero Voice Lines(Event Player);",\n'
token_at = validator.index(token, generic_at)
validator = validator[:token_at] + validator[token_at + len(token):]

# Validate NORMAL inside the actual application guard, not the earlier submenu
# opening branch that also contains HalamanMenu == 6.
anchor = '    menu_interact = next(rule.body for rule in rules if rule.name.startswith("10 - Menu:"))\n'
scoped = '''    menu_dispatchers = [rule for rule in rules if rule.name.startswith("10 - Menu:")]\n    checks.equal(len(menu_dispatchers), 1, "Voce eroe: un solo dispatcher Menu 10")\n    if menu_dispatchers:\n        menu_code = mask_strings(menu_dispatchers[0].body)\n        voice_guard = menu_code.find("If(Event Player.IndeksSuara != Event Player.KursorSuara);")\n        voice_end = menu_code.find("Call Subroutine(GambarMenu);", voice_guard)\n        voice_block = menu_code[voice_guard:voice_end] if 0 <= voice_guard < voice_end else ""\n        checks.require(\n            "If(Event Player.IndeksSuara == 0);" in voice_block\n            and "Stop Modifying Hero Voice Lines(Event Player);" in voice_block,\n            "Voce eroe NORMAL: Stop Modifying Hero Voice Lines assente dal ramo applicazione Menu 6",\n        )\n\n''' + anchor
if validator.count(anchor) != 1:
    raise RuntimeError(f"menu_interact anchor count {validator.count(anchor)}")
validator = validator.replace(anchor, scoped, 1)
validator_path.write_text(validator, encoding="utf-8")

# Negative test: mutate only the Menu 10 dispatcher occurrence.
tests_path = ROOT / "tests/test_validate_workshop.py"
tests = tests_path.read_text(encoding="utf-8")
old = '''    def test_voice_normal_stop_is_required(self) -> None:\n        mutated = self.source.replace(\n            "Stop Modifying Hero Voice Lines(Event Player);",\n            '\"Stop Modifying Hero Voice Lines(Event Player);\"',\n            1,\n        )\n        self.assertNotEqual(mutated, self.source)\n        checks = validator.Checks()\n        validator.check_arcade_features(checks, mutated, self.rules(mutated))\n        self.assertTrue(any("Stop Modifying Hero Voice Lines" in error for error in checks.errors), checks.errors)\n'''
new = '''    def test_voice_normal_stop_is_required(self) -> None:\n        menu_at = self.source.index('rule("10 - Menu:')\n        menu_end = self.source.index('\\nrule("11 - ', menu_at)\n        menu = self.source[menu_at:menu_end]\n        menu2 = menu.replace(\n            "Stop Modifying Hero Voice Lines(Event Player);",\n            '\"Stop Modifying Hero Voice Lines(Event Player);\"',\n            1,\n        )\n        self.assertNotEqual(menu2, menu)\n        mutated = self.source[:menu_at] + menu2 + self.source[menu_end:]\n        checks = validator.Checks()\n        validator.check_arcade_features(checks, mutated, self.rules(mutated))\n        self.assertTrue(any("Stop Modifying Hero Voice Lines" in error for error in checks.errors), checks.errors)\n'''
if tests.count(old) != 1:
    raise RuntimeError(f"voice test block count {tests.count(old)}")
tests_path.write_text(tests.replace(old, new, 1), encoding="utf-8")
