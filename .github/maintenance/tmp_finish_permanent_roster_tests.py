#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
runtime_path = ROOT / "tests" / "test_runtime_maintenance.py"
dummy_path = ROOT / "tests" / "test_dummy_bots.py"

runtime = runtime_path.read_text(encoding="utf-8")
old = '''            self.assertNotIn("Event Player.SegarkanRosterTertunda == False;", roster)\n            self.assertNotIn("If(Event Player.SegarkanRosterTertunda == True);", roster)\n            self.assertNotIn("Create HUD Text(", roster)'''
new = '''            self.assertNotIn("Event Player.SegarkanRosterTertunda == False;", roster)\n            self.assertNotIn("Event Player.SegarkanRosterTertunda = True;", roster)\n            self.assertIn("Event Player.SegarkanRosterTertunda = False;", roster)\n            self.assertNotIn("Create HUD Text(", roster)'''
if runtime.count(old) != 1:
    raise RuntimeError(f"expected one registered-team-switch stale block, found {runtime.count(old)}")
runtime = runtime.replace(old, new, 1)

old = '''            self.assertNotIn("Event Player.TimTerakhir == Team Of(Event Player);", roster)\n            self.assertNotIn("Event Player.SegarkanRosterTertunda", roster)\n            self.assertNotIn("Is Alive(Event Player) == True;", roster)'''
new = '''            self.assertNotIn("Event Player.TimTerakhir == Team Of(Event Player);", roster)\n            self.assertNotIn("Event Player.SegarkanRosterTertunda == False;", roster)\n            self.assertNotIn("Event Player.SegarkanRosterTertunda = True;", roster)\n            self.assertIn("Event Player.SegarkanRosterTertunda = False;", roster)\n            self.assertNotIn("Is Alive(Event Player) == True;", roster)'''
if runtime.count(old) != 1:
    raise RuntimeError(f"expected one lightweight stale block, found {runtime.count(old)}")
runtime = runtime.replace(old, new, 1)
runtime_path.write_text(runtime, encoding="utf-8")

dummy = dummy_path.read_text(encoding="utf-8")
old = '''        for source in (self.it, self.en):\n            self.assertIn('Custom String("{0} [{1}]", Custom String("CHILL DEDICATED SERVER")', source)'''
new = '''        for source, global_name in ((self.it, "Globale"), (self.en, "Global")):\n            self.assertIn('Custom String("{0} [{1}]", Custom String("CHILL DEDICATED SERVER")', source)'''
if dummy.count(old) != 1:
    raise RuntimeError(f"expected one dummy source loop, found {dummy.count(old)}")
dummy = dummy.replace(old, new, 1)
dummy = dummy.replace('self.assertIn("1 + Evaluate Once(Global.IndeksPemilih)", source)', 'self.assertIn(f"1 + Evaluate Once({global_name}.IndeksPemilih)", source)', 1)
dummy = dummy.replace('self.assertIn("-13 + Evaluate Once(Global.IndeksPemilih)", source)', 'self.assertIn(f"-13 + Evaluate Once({global_name}.IndeksPemilih)", source)', 1)
dummy = dummy.replace('self.assertNotIn("-99 + Evaluate Once(Global.IndeksPemilih)", source)', 'self.assertNotIn(f"-99 + Evaluate Once({global_name}.IndeksPemilih)", source)', 1)
dummy_path.write_text(dummy, encoding="utf-8")

print("final stale roster assertions aligned")
