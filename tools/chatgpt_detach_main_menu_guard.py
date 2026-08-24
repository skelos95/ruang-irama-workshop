from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

for rel in ("workshop/ruang_irama.it-IT.workshop", "tests/fixtures/semantic_reference.txt"):
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    old = (
        "\t\tEvent Player.LampiranTeleportasiAktif == True;\n"
        "\t\tIs Button Held(Event Player, Button(Crouch)) == True;\n"
        "\t\tIs Button Held(Event Player, Button(Reload)) == True;"
    )
    new = (
        "\t\tEvent Player.LampiranTeleportasiAktif == True;\n"
        "\t\tEvent Player.MenuTerbuka == False;\n"
        "\t\tIs Button Held(Event Player, Button(Crouch)) == True;\n"
        "\t\tIs Button Held(Event Player, Button(Reload)) == True;"
    )
    if text.count(old) != 1:
        raise SystemExit(f"expected one detach condition block in {rel}, found {text.count(old)}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")

test_path = ROOT / "tests/test_runtime_maintenance.py"
test = test_path.read_text(encoding="utf-8")
old_test = '            self.assertIn("Is Button Held(Event Player, Button(Crouch)) == True;", manual_detach)\n            self.assertIn("Is Button Held(Event Player, Button(Reload)) == True;", manual_detach)'
new_test = '            self.assertIn("Event Player.MenuTerbuka == False;", manual_detach)\n            self.assertIn("Is Button Held(Event Player, Button(Crouch)) == True;", manual_detach)\n            self.assertIn("Is Button Held(Event Player, Button(Reload)) == True;", manual_detach)\n            self.assertNotIn("Event Player.TeleportasiJongkokAktif == False;", manual_detach)'
if test.count(old_test) != 1:
    raise SystemExit(f"expected one detach test block, found {test.count(old_test)}")
test_path.write_text(test.replace(old_test, new_test, 1), encoding="utf-8")

print("Detach now ignores Crouch+Reload while the Melee main menu is open, but still works in Crouch Travel")
