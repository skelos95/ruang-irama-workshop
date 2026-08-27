from pathlib import Path

runtime_path = Path('tests/test_runtime_maintenance.py')
runtime = runtime_path.read_text(encoding='utf-8')

replacements = [
    (
        '            self.assertIn("Event Player.NamaTampilan != Null;", player_bind)\n            self.assertIn(\'Event Player.NamaTampilan != Custom String("\");\', player_bind)\n',
        '            self.assertNotIn("Event Player.NamaTampilan != Null;", player_bind)\n            self.assertNotIn(\'Event Player.NamaTampilan != Custom String("\");\', player_bind)\n            self.assertIn(f\'{global_name}.NamaSlotHUD[Event Player.UrutanHUD] != Custom String("");\', player_bind)\n',
    ),
    (
        '            self.assertIn("Event Player.TimTerakhir == Team Of(Event Player);", roster)\n            self.assertNotIn("Event Player.SegarkanRosterTertunda == False;", roster)\n',
        '            self.assertNotIn("Event Player.TimTerakhir == Team Of(Event Player);", roster)\n            self.assertNotIn("Event Player.SegarkanRosterTertunda == False;", roster)\n',
    ),
]
for old, new in replacements:
    if runtime.count(old) != 1:
        raise SystemExit(f'runtime replacement count {runtime.count(old)} for {old!r}')
    runtime = runtime.replace(old, new, 1)
runtime_path.write_text(runtime, encoding='utf-8')

validator_test_path = Path('tests/test_validate_workshop.py')
test = validator_test_path.read_text(encoding='utf-8')

old = '''        mutated = self.replace_in_rule(
            roster,
            "Has Spawned(Event Player) == True;",
            "Has Spawned(Event Player) == True;\\n\\t\\tIs Alive(Event Player) == True;",
        )
'''
new = '''        mutated = self.replace_in_rule(
            roster,
            'Global.NamaSlotHUD[Event Player.UrutanHUD] != Custom String("");',
            'Global.NamaSlotHUD[Event Player.UrutanHUD] != Custom String("");\\n\\t\\tIs Alive(Event Player) == True;',
        )
'''
if test.count(old) != 1:
    raise SystemExit(f'ready-flag anchor replacement count {test.count(old)}')
test = test.replace(old, new, 1)

old = '''        for guard in (
            "Event Player.NamaTampilan != Null;",
            'Event Player.NamaTampilan != Custom String("");',
            "Event Player.UrutanHUD >= 0;",
            "Global.PemainSlotHUD[Event Player.UrutanHUD] == Event Player;",
        ):
            with self.subTest(guard=guard):
                self.assertIn(guard, conditions)
                mutated = self.replace_in_rule(renderer, guard, "")
                self.assert_rejected(mutated, "renderer roster lazy senza guardia identità")
'''
new = '''        for guard, error in (
            ("Event Player.UrutanHUD >= 0;", "renderer roster senza guardia slot stabile"),
            ("Event Player.UrutanHUD < 12;", "renderer roster senza guardia slot stabile"),
            ("Global.PemainSlotHUD[Event Player.UrutanHUD] == Event Player;", "renderer roster senza guardia slot stabile"),
            ('Global.NamaSlotHUD[Event Player.UrutanHUD] != Custom String("");', "renderer roster lazy senza identità globale"),
        ):
            with self.subTest(guard=guard):
                self.assertIn(guard, conditions)
                mutated = self.replace_in_rule(renderer, guard, "")
                self.assert_rejected(mutated, error)
        self.assertNotIn("Event Player.NamaTampilan != Null;", conditions)
        self.assertNotIn('Event Player.NamaTampilan != Custom String("");', conditions)
'''
if test.count(old) != 1:
    raise SystemExit(f'lazy roster guard replacement count {test.count(old)}')
test = test.replace(old, new, 1)

old = '''    def test_pending_roster_refresh_starts_false_in_fresh_setup(self) -> None:
        mutated = self.source.replace(
            "Event Player.SegarkanRosterTertunda = False;",
            "Event Player.SegarkanRosterTertunda = Null;",
            1,
        )
        self.assert_rejected(mutated, "reset setup iniziale mancante")
'''
new = '''    def test_pending_roster_refresh_cannot_block_roster_bootstrap(self) -> None:
        roster = self.rule(
            lambda rule: "Global.HudKiriPemain[Event Player.UrutanHUD] = Last Text ID;" in rule.body
            and "Global.HudKananPemain[Event Player.UrutanHUD] = Last Text ID;" in rule.body
        )
        conditions = validator.rule_block(roster, "conditions") or ""
        self.assertNotIn("Event Player.SegarkanRosterTertunda == False;", conditions)
        self.assertIn("If(Event Player.SegarkanRosterTertunda == True);", roster.body)
        self.assertIn("Event Player.SegarkanRosterTertunda = False;", roster.body)
'''
if test.count(old) != 1:
    raise SystemExit(f'pending refresh test replacement count {test.count(old)}')
test = test.replace(old, new, 1)

validator_test_path.write_text(test, encoding='utf-8')
