from pathlib import Path

path = Path('workshop/ruang_irama.it-IT.workshop')
text = path.read_text(encoding='utf-8')
start = text.index('regola("02b - HUD Pemain: Hubungkan ke slot global")')
end = text.index('regola("03c - Bot/Dummy', start)
rule = text[start:end]
if rule.count('\n\t\tAll;') != 2:
    raise SystemExit(f'expected two All selectors in Italian 02b, found {rule.count(chr(10)+chr(9)+chr(9)+"All;")}')
rule = rule.replace('\n\t\tAll;', '\n\t\tTutti;')
text = text[:start] + rule + text[end:]
path.write_text(text, encoding='utf-8')
