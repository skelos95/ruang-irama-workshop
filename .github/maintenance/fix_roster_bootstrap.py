from pathlib import Path

FILES = (
    (Path('workshop/ruang_irama.it-IT.workshop'), 'Globale', 'regola'),
    (Path('tests/fixtures/semantic_reference.txt'), 'Global', 'rule'),
)

for path, g, rule_kw in FILES:
    text = path.read_text(encoding='utf-8')
    start = text.index(f'{rule_kw}("02b - HUD Pemain: Hubungkan ke slot global")')
    end = text.index(f'{rule_kw}("03c - Bot/Dummy', start)
    rule = text[start:end]

    old = f'''\t\tArray Contains({g}.PemainManusia, Event Player) == True;\n\t\tHas Spawned(Event Player) == True;\n\t\tEvent Player.TimTerakhir == Team Of(Event Player);\n\t\tEvent Player.SegarkanRosterTertunda == False;\n\t\tEvent Player.NamaTampilan != Null;\n\t\tEvent Player.NamaTampilan != Custom String("");\n\t\tEvent Player.UrutanHUD >= 0;\n\t\t{g}.PemainSlotHUD[Event Player.UrutanHUD] == Event Player;\n\t\tEvent Player.HudPemainDibuat == False;'''

    new = f'''\t\tArray Contains({g}.PemainManusia, Event Player) == True;\n\t\tEvent Player.UrutanHUD >= 0;\n\t\tEvent Player.UrutanHUD < 12;\n\t\t{g}.PemainSlotHUD[Event Player.UrutanHUD] == Event Player;\n\t\t{g}.NamaSlotHUD[Event Player.UrutanHUD] != Custom String("");\n\t\tOr(Event Player.HudPemainDibuat == False, Or(Or({g}.HudKiriPemain[Event Player.UrutanHUD] == 0, {g}.HudKiriPemain[Event Player.UrutanHUD] == Null), Or({g}.HudKananPemain[Event Player.UrutanHUD] == 0, {g}.HudKananPemain[Event Player.UrutanHUD] == Null))) == True;'''

    if rule.count(old) != 1:
        raise SystemExit(f'{path}: expected old 02b guard block once, found {rule.count(old)}')
    rule = rule.replace(old, new, 1)
    text = text[:start] + rule + text[end:]
    path.write_text(text, encoding='utf-8')

runtime = Path('tests/test_runtime_maintenance.py')
text = runtime.read_text(encoding='utf-8')
anchor = '    def test_registered_team_switch_never_destroys_roster_or_hides_crouch_target(self):\n'
if anchor not in text:
    raise SystemExit('runtime test anchor missing')

test = '''    def test_roster_bootstrap_depends_only_on_persistent_slot_identity(self):
        for source, global_name, rule_kw in ((self.it, "Globale", "regola"), (self.en, "Global", "rule")):
            roster = source.split(f'{rule_kw}("02b - HUD Pemain: Hubungkan ke slot global")', 1)[1].split(f'{rule_kw}("03c - Bot/Dummy', 1)[0]
            self.assertNotIn("Has Spawned(Event Player) == True;", roster)
            self.assertNotIn("Event Player.TimTerakhir == Team Of(Event Player);", roster)
            self.assertNotIn("Event Player.SegarkanRosterTertunda == False;", roster)
            self.assertNotIn("Event Player.NamaTampilan != Null;", roster)
            self.assertIn(f"{global_name}.PemainSlotHUD[Event Player.UrutanHUD] == Event Player;", roster)
            self.assertIn(f'{global_name}.NamaSlotHUD[Event Player.UrutanHUD] != Custom String("");', roster)
            self.assertIn("Event Player.UrutanHUD < 12;", roster)
            self.assertIn("Event Player.HudPemainDibuat == False", roster)
            self.assertEqual(roster.count("Create HUD Text("), 2)

'''
if 'def test_roster_bootstrap_depends_only_on_persistent_slot_identity' not in text:
    text = text.replace(anchor, test + anchor, 1)
runtime.write_text(text, encoding='utf-8')
