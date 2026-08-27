from pathlib import Path

path = Path("tests/test_runtime_maintenance.py")
text = path.read_text(encoding="utf-8")
old = '''            self.assertIn(f'{rule_kw}("00b - HUD Roster: Dua belas slot global permanen")', source)
            global_rows = source.split(f'{rule_kw}("00b - HUD Roster: Dua belas slot global permanen")', 1)[1].split(f'{rule_kw}("00a1 - Umum:', 1)[0]
            self.assertIn("Ongoing - Global;", global_rows)
            self.assertIn("For Global Variable(IndeksPemilih, 0, 12, 1);", global_rows)
            self.assertEqual(global_rows.count("Create HUD Text("), 2)
            self.assertIn(f"{global_name}.PemainSlotHUD[Evaluate Once({global_name}.IndeksPemilih)]", global_rows)
            self.assertIn(f"{global_name}.NamaSlotHUD[Evaluate Once({global_name}.IndeksPemilih)]", global_rows)

            player_bind = source.split(f'{rule_kw}("02b - HUD Pemain: Hubungkan ke slot global")', 1)[1].split(f'{rule_kw}("03c - Bot/Dummy', 1)[0]
            self.assertNotIn("Create HUD Text(", player_bind)
            self.assertIn(f"Event Player.HudKiri = {global_name}.HudKiriPemain[Event Player.UrutanHUD];", player_bind)
            self.assertIn(f"Event Player.HudKanan = {global_name}.HudKananPemain[Event Player.UrutanHUD];", player_bind)
'''
new = '''            self.assertNotIn(f'{rule_kw}("00b - HUD Roster: Dua belas slot global permanen")', source)
            zeros = "Array(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)"
            self.assertIn(f"{global_name}.HudKiriPemain = {zeros};", source)
            self.assertIn(f"{global_name}.HudKananPemain = {zeros};", source)

            player_bind = source.split(f'{rule_kw}("02b - HUD Pemain: Hubungkan ke slot global")', 1)[1].split(f'{rule_kw}("03c - Bot/Dummy', 1)[0]
            self.assertEqual(player_bind.count("Create HUD Text("), 2)
            self.assertIn("Event Player.NamaTampilan != Null;", player_bind)
            self.assertIn('Event Player.NamaTampilan != Custom String("");', player_bind)
            self.assertIn(f"{global_name}.PemainSlotHUD[Event Player.UrutanHUD] == Event Player;", player_bind)
            self.assertIn(f"{global_name}.HudKiriPemain[Event Player.UrutanHUD] = Last Text ID;", player_bind)
            self.assertIn(f"{global_name}.HudKananPemain[Event Player.UrutanHUD] = Last Text ID;", player_bind)
            self.assertIn(f"Event Player.HudKiri = {global_name}.HudKiriPemain[Event Player.UrutanHUD];", player_bind)
            self.assertIn(f"Event Player.HudKanan = {global_name}.HudKananPemain[Event Player.UrutanHUD];", player_bind)
            self.assertIn(f"Destroy HUD Text({global_name}.HudKiriPemain[{global_name}.IndeksUtangKeluar]);", source)
            self.assertIn(f"Destroy HUD Text({global_name}.HudKananPemain[{global_name}.IndeksUtangKeluar]);", source)
'''
if old not in text:
    raise SystemExit("expected stale roster test block not found")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
