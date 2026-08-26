from pathlib import Path

path = Path('tests/test_runtime_maintenance.py')
text = path.read_text(encoding='utf-8')
old = '            self.assertIn(f"{global_name}.NamaSlotHUD[{global_name}.IndeksUtangKeluar] = Custom String(\"\");", source)\n'
new = "            self.assertIn(f'{global_name}.NamaSlotHUD[{global_name}.IndeksUtangKeluar] = Custom String(\"\");', source)\n"
if text.count(old) != 1:
    raise SystemExit(f'expected one malformed NamaSlotHUD assertion, found {text.count(old)}')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
