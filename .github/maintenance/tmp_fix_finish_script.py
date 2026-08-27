from pathlib import Path

path = Path('.github/maintenance/tmp_finish_global_hud_slot.py')
text = path.read_text(encoding='utf-8')
old = 'anchor = "## 0.8.1\\n"'
new = 'anchor = "## 0.8.1 — 2026-08-25\\n"'
if text.count(old) != 1:
    raise SystemExit(f'expected one changelog anchor, found {text.count(old)}')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
