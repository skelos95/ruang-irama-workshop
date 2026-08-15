from __future__ import annotations

from pathlib import Path
import hashlib
import re

source_path = Path('workshop/ruang_irama.workshop')
validator_path = Path('tools/validate_workshop.py')
report_path = Path('docs/VALIDAZIONE.md')
test_doc_path = Path('docs/TEST.md')

src = source_path.read_text(encoding='utf-8')
old = ')) : Null, Left, -99 + Event Player.UrutanHUD, Color(White), Event Player.WarnaNama, Color(White),'
new = ')) : Custom String(" "), Left, -99 + Event Player.UrutanHUD, Color(White), Event Player.WarnaNama, Color(White),'
count = src.count(old)
if count != 1:
    raise SystemExit(f'diagnostics fallback: expected 1 occurrence, found {count}')
src = src.replace(old, new, 1)
source_path.write_text(src, encoding='utf-8')

val = validator_path.read_text(encoding='utf-8')
anchor = '''    checks.require(\n        'Custom String("HUD {0} | IWT {1}"' in source,\n        "diagnostica priva della riga HUD/IWT compatta",\n    )\n'''
insert = anchor + '''    checks.require(\n        ')) : Custom String(" "), Left, -99 + Event Player.UrutanHUD' in source,\n        "diagnostica OFF deve usare testo vuoto esplicito e non Null/0",\n    )\n    checks.require(\n        ')) : Null, Left, -99 + Event Player.UrutanHUD' not in source,\n        "diagnostica OFF usa ancora Null e può renderizzare 0 nel roster",\n    )\n'''
if val.count(anchor) != 1:
    raise SystemExit('validator diagnostics anchor not found')
val = val.replace(anchor, insert, 1)
validator_path.write_text(val, encoding='utf-8')

tests = test_doc_path.read_text(encoding='utf-8')
line = '- **Diagnostics OFF live:** verificare che sotto l’ultimo player del roster sinistro non compaia più `0`; il campo deve restare visivamente vuoto.\n'
if line not in tests:
    tests += '\n' + line
test_doc_path.write_text(tests, encoding='utf-8')

data = source_path.read_bytes().replace(b'\r\n', b'\n')
blob = hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()
report = report_path.read_text(encoding='utf-8')
report, n = re.subn(r'```text\n[0-9a-f]{40}\n```', f'```text\n{blob}\n```', report, count=1)
if n != 1:
    raise SystemExit('validation report blob marker not found')
report_path.write_text(report, encoding='utf-8')
