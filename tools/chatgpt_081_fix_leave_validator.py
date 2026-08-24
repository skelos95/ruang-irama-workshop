from pathlib import Path
p = Path(__file__).resolve().parents[1] / "tools" / "validate_workshop.py"
s = p.read_text(encoding="utf-8")
old = '''        checks.require("Wait(0.100, Ignore Condition);" in body,
                       "leave deve distinguere una vera uscita dal cambio squadra con 0,100 s")'''
new = '''        checks.require("Wait(0.500, Ignore Condition);" in body,
                       "leave deve distinguere una vera uscita dal cambio squadra con 0,500 s")'''
if s.count(old) != 1:
    raise SystemExit(f"leave validator contract occurrence count: {s.count(old)}")
p.write_text(s.replace(old, new, 1), encoding="utf-8")
print("Updated leave validator contract to 0.500 s")
