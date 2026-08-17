from __future__ import annotations

import re
from pathlib import Path

root = Path(__file__).resolve().parents[2]
source = (root / 'workshop' / 'ruang_irama.workshop').read_text(encoding='utf-8')

pattern = re.compile(r'rule\("([^"]+)"\)\s*\{', re.M)
results = []
for match in pattern.finditer(source):
    start = match.start()
    next_match = pattern.search(source, match.end())
    end = next_match.start() if next_match else len(source)
    body = source[start:end]
    if 'Ongoing - Each Player;' not in body:
        continue
    waits = re.findall(r'Wait\s*\(([^;]+?)\);', body, re.S)
    loops = body.count('Loop If Condition Is True;')
    create_hud = body.count('Create HUD Text(')
    subcalls = re.findall(r'Call Subroutine\(([^)]+)\);', body)
    results.append((match.group(1), waits, loops, create_hud, subcalls))

print(f'GLOBAL-FIRST AUDIT: {len(results)} Ongoing - Each Player rules')
for index, (name, waits, loops, create_hud, subcalls) in enumerate(results, 1):
    wait_text = ' | '.join(' '.join(w.split()) for w in waits) if waits else '-'
    calls = ','.join(subcalls) if subcalls else '-'
    print(f'{index:02d}. {name} :: waits={wait_text} :: loops={loops} :: createHUD={create_hud} :: calls={calls}')

raise RuntimeError('audit-only: replace this patch with the global-first migration after reading the workflow log')
