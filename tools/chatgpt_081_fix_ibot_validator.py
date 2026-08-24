from pathlib import Path

p = Path(__file__).resolve().parents[1] / "tools" / "validate_workshop.py"
s = p.read_text(encoding="utf-8")
old = '''        checks.require("Global.PemainAktif.BotOtomatis == False" in lifecycle_dispatcher.body,
                       "dispatcher lifecycle globale può riattivare il lifecycle di un iBot")'''
new = '''        checks.require(lifecycle_dispatcher.body.count("Global.PemainAktif.BotOtomatis == False") >= 2,
                       "dispatcher lifecycle globale può riattivare il lifecycle di un iBot")'''
if s.count(old) != 1:
    raise SystemExit(f"iBot lifecycle validator occurrence count: {s.count(old)}")
p.write_text(s.replace(old, new, 1), encoding="utf-8")
print("Strengthened iBot lifecycle validator guard")
