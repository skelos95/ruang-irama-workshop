from pathlib import Path

path = Path('.github/maintenance/tmp_fix_ghost_remaining.py')
text = path.read_text(encoding='utf-8')
old = '''replace_exact(
    "tools/validate_workshop.py",
    '            "Global.PemainAktif.SegarkanRosterTertunda = False;",\\n',
    "",
    expected=1,
)
replace_exact(
    "tools/validate_workshop.py",
    '                    "Global.PemainAktif.SegarkanRosterTertunda = False;",\\n',
    "",
    expected=1,
)
'''
new = '''replace_exact(
    "tools/validate_workshop.py",
    '            "Global.PemainAktif.SegarkanRosterTertunda = False;",\\n',
    "",
    expected=2,
)
'''
if old not in text:
    raise SystemExit('remaining repair block not found')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
print('prepared remaining Ghost repair script')
