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
text = text.replace(old, new, 1)
old_regex = 'new_text, count = re.subn(pattern, replacement, text, flags=re.MULTILINE | re.DOTALL)'
new_regex = 'new_text, count = re.subn(pattern, lambda _match: replacement, text, flags=re.MULTILINE | re.DOTALL)'
if old_regex not in text:
    raise SystemExit('replace_regex helper not found')
text = text.replace(old_regex, new_regex, 1)
old_owners = 'owner in {"TerapkanHalamanGhost", "ProsesCepatPemain"}'
new_owners = 'owner in {"TerapkanHalamanGhost", "ProsesCepatPemain", "ProsesSiklusPemain"}'
if old_owners not in text:
    raise SystemExit('Ghost owner set not found')
text = text.replace(old_owners, new_owners, 1)
path.write_text(text, encoding='utf-8')
print('prepared remaining Ghost repair script')
