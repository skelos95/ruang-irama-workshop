from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "exports" / "CHILL_0.7.0_GlobalFirst_candidate.txt"

text = OUT.read_text(encoding="utf-8")
old = "For Global Variable(Global.IndeksPemainGlobal, 0, Count Of(All Players(All Teams)) - 1, 1);"
new = "For Global Variable(IndeksPemainGlobal, 0, Count Of(All Players(All Teams)) - 1, 1);"
count = text.count(old)
if count != 2:
    raise RuntimeError(f"expected exactly 2 invalid Global-first loops, found {count}")
text = text.replace(old, new)
if "For Global Variable(Global." in text:
    raise RuntimeError("invalid For Global Variable(Global.* syntax remains")
OUT.write_text(text, encoding="utf-8")
print("fixed 2 Global-first For Global Variable declarations")
