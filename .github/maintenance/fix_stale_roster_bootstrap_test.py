from pathlib import Path

path = Path('tests/test_runtime_maintenance.py')
text = path.read_text(encoding='utf-8')
old = '            self.assertIn("Event Player.SegarkanRosterTertunda == False;", roster)\n'
new = '            self.assertNotIn("Event Player.SegarkanRosterTertunda == False;", roster)\n            self.assertIn("If(Event Player.SegarkanRosterTertunda == True);", roster)\n'
if text.count(old) != 1:
    raise SystemExit(f'expected one stale roster pending assertion, found {text.count(old)}')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
