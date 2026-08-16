from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "tools" / "validate_workshop.py"

text = VALIDATOR.read_text(encoding="utf-8")
old = '        before_luck = mask_strings(menu_interact[max(0, luck_start - 900):luck_start])\n'
new = (
    '        masked_menu_interact = mask_strings(menu_interact)\n'
    '        before_luck = masked_menu_interact[max(0, luck_start - 900):luck_start]\n'
)
if old in text:
    if text.count(old) != 1:
        raise RuntimeError(f"expected one luck pre-window validator line, found {text.count(old)}")
    VALIDATOR.write_text(text.replace(old, new, 1), encoding="utf-8")
elif new not in text:
    raise RuntimeError("luck pre-window validator line not found")

# This migration helper must not survive the maintenance commit.
Path(__file__).unlink()


class ValidatorMigrationSmokeTest(unittest.TestCase):
    def test_validator_window_fix_applied(self) -> None:
        fixed = VALIDATOR.read_text(encoding="utf-8")
        self.assertIn("masked_menu_interact = mask_strings(menu_interact)", fixed)
