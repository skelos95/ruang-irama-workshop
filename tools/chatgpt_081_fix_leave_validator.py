from pathlib import Path
p = Path(__file__).resolve().parents[1] / "tools" / "validate_workshop.py"
s = p.read_text(encoding="utf-8")
old = '''        checks.require("Wait(0.100, Ignore Condition);" in body,
                       "leave deve distinguere una vera uscita dal cambio squadra con 0,100 s")'''
new = '''        checks.require("Wait(0.500, Ignore Condition);" in body,
                       "leave deve distinguere una vera uscita dal cambio squadra con 0,500 s")'''
if s.count(old) != 1:
    raise SystemExit(f"leave validator contract occurrence count: {s.count(old)}")
s = s.replace(old, new, 1)
label_old = "OK - gate semantici v0.8.0 superati"
if s.count(label_old) != 1:
    raise SystemExit(f"validator success label occurrence count: {s.count(label_old)}")
s = s.replace(label_old, "OK - gate semantici v0.8.1 superati", 1)
p.write_text(s, encoding="utf-8")
print("Updated leave validator contract and 0.8.1 success label")
