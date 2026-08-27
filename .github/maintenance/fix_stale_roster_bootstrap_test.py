from pathlib import Path

path = Path('tests/test_runtime_maintenance.py')
text = path.read_text(encoding='utf-8')
old = '            self.assertIn("Event Player.SegarkanRosterTertunda == False;", roster)\n'
new = '            self.assertNotIn("Event Player.SegarkanRosterTertunda == False;", roster)\n            self.assertIn("If(Event Player.SegarkanRosterTertunda == True);", roster)\n'
count = text.count(old)
if count < 1:
    raise SystemExit('no stale roster pending assertions found')
path.write_text(text.replace(old, new), encoding='utf-8')
