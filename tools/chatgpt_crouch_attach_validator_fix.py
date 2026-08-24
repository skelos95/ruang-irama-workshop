#!/usr/bin/env python3
from pathlib import Path

path = Path(__file__).resolve().parent / "validate_workshop.py"
text = path.read_text(encoding="utf-8")
start = text.index("        click_dispatch = next(")
end = text.index("    for token in FORBIDDEN_RESULT_ACTIONS:", start)
block = text[start:end]
if block.count('PerintahTeleportasi == 1') != 2:
    raise SystemExit(f"unexpected old teleport command guard count: {block.count('PerintahTeleportasi == 1')}")
if block.count('Button(Primary Fire)') != 1:
    raise SystemExit("old Primary Fire click fallback missing")
block = block.replace('PerintahTeleportasi == 1', 'PerintahTeleportasi == 3')
block = block.replace('Button(Primary Fire)', 'Button(Interact)')
text = text[:start] + block + text[end:]
path.write_text(text, encoding="utf-8")
print("validator teleport click gate updated for Interact")
