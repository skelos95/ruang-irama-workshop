from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def replace_exact(path: str, old: str, new: str, expected: int = 1) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"{path}: expected {expected} occurrence(s), found {count}: {old[:180]!r}")
    target.write_text(text.replace(old, new), encoding="utf-8")
    print(f"patched {path}: {count} exact replacement(s)")


def replace_regex(path: str, pattern: str, replacement: str, expected: int = 1) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    new_text, count = re.subn(pattern, replacement, text, flags=re.MULTILINE | re.DOTALL)
    if count != expected:
        raise SystemExit(f"{path}: expected {expected} regex replacement(s), found {count}: {pattern[:180]!r}")
    target.write_text(new_text, encoding="utf-8")
    print(f"patched {path}: {count} regex replacement(s)")


# Dummy Follow and Ghost share the X component of ProfilSosial as two independent bits.
replace_exact(
    "tools/validate_workshop.py",
    '("02 - Pemain: Pisahkan manusia dari pasukan kaleng", "X Component Of(Global.ProfilSosial[Index Of Array Value(Global.ProfilNama, Event Player.NamaTampilan)]) == 1"),',
    '("02 - Pemain: Pisahkan manusia dari pasukan kaleng", "(X Component Of(Global.ProfilSosial[Index Of Array Value(Global.ProfilNama, Event Player.NamaTampilan)]) % 2) == 1"),',
)

# The global-slot roster no longer uses the old pending flag. Require the real Ghost defaults instead.
replace_exact(
    "tools/validate_workshop.py",
    '            "KursorPrivasiInspeksi = 0;", "IzinkanDummyMengikuti = False;", "KursorIkutiDummy = 0;",\n            "KartuNasibAktif = False;", "HudMenu = Null;",\n            "SegarkanRosterTertunda = False;",\n',
    '            "KursorPrivasiInspeksi = 0;", "IzinkanDummyMengikuti = False;", "KursorIkutiDummy = 0;",\n            "GhostAktif = False;", "KursorGhost = 0;",\n            "KartuNasibAktif = False;", "HudMenu = Null;",\n',
)
replace_exact(
    "tools/validate_workshop.py",
    '            "Global.PemainAktif.SegarkanRosterTertunda = False;",\n',
    "",
    expected=1,
)
replace_exact(
    "tools/validate_workshop.py",
    '                    "Global.PemainAktif.SegarkanRosterTertunda = False;",\n',
    "",
    expected=1,
)

# Native dummy wall collision remains isolated, while Ghost is allowed to use the same environment action
# only in its classifier restore, apply page, and fast lifecycle reassertion.
replace_regex(
    "tools/validate_workshop.py",
    r'''    environment_collision_calls = \[\n        \(rule, call\)\n        for rule in rules\n        for call in iter_calls\(rule\.body, "Disable Movement Collision With Environment"\)\n    \]\n.*?\n    bot_lock = rule_by_subroutine\(rules, "KunciBot"\)''',
    '''    environment_collision_calls = [\n        (rule, call)\n        for rule in rules\n        for call in iter_calls(rule.body, "Disable Movement Collision With Environment")\n    ]\n    native_environment_collision_calls = [\n        (rule, call)\n        for rule, call in environment_collision_calls\n        if bot_rule is not None and rule.start == bot_rule.start\n    ]\n    checks.equal(len(native_environment_collision_calls), 1,\n                 "numero disattivazioni collisione ambiente dummy")\n    if native_environment_collision_calls and bot_rule:\n        collision_rule, collision_call = native_environment_collision_calls[0]\n        checks.equal(collision_call.args, ("Event Player", "False"),\n                     "collisione ambiente dummy: Event Player con Include Floors False")\n        checks.require(\n            re.search(\n                r"If\\(Is Dummy Bot\\(Event Player\\) == True\\);\\s*"\n                r"Enable Movement Collision With Players\\(Event Player\\);\\s*"\n                r"Disable Movement Collision With Environment\\(Event Player, False\\);",\n                collision_rule.body,\n            ) is not None,\n            "collisioni dummy non protette dal ramo nativo o in ordine errato",\n        )\n        collision_actions = rule_block(collision_rule, "actions")\n        checks.require(collision_actions is not None,\n                       "collisione ambiente dummy: blocco actions assente")\n        if collision_actions is not None:\n            expected_collision_actions = """\n                Call Subroutine(KunciBot);\n                If(Is Dummy Bot(Event Player) == True);\n                    Enable Movement Collision With Players(Event Player);\n                    Disable Movement Collision With Environment(Event Player, False);\n                    Event Player.WaktuTeleportasiDummy = Total Time Elapsed + 1;\n                    Set Respawn Max Time(Event Player, 3);\n                End;\n            """\n            checks.equal(\n                re.sub(r"\\s+", "", collision_actions),\n                re.sub(r"\\s+", "", expected_collision_actions),\n                "collisione ambiente dummy: sequenza raggiungibile e isolata",\n            )\n\n    for collision_rule, collision_call in environment_collision_calls:\n        if bot_rule is not None and collision_rule.start == bot_rule.start:\n            continue\n        owner = subroutine_target(collision_rule)\n        approved_ghost_owner = (\n            owner in {"TerapkanHalamanGhost", "ProsesCepatPemain"}\n            or collision_rule.name.startswith("02 - Pemain: Pisahkan manusia")\n        )\n        checks.require(approved_ghost_owner,\n                       f"collisione ambiente disabilitata fuori da Dummy/Ghost: {collision_rule.name}")\n        checks.equal(collision_call.args[-1].strip() if len(collision_call.args) > 1 else None,\n                     "False",\n                     f"Ghost deve mantenere solidi i pavimenti: {collision_rule.name}")\n        checks.require("GhostAktif" in collision_rule.body,\n                       f"collisione ambiente Ghost senza stato GhostAktif: {collision_rule.name}")\n\n    bot_lock = rule_by_subroutine(rules, "KunciBot")''',
)

# Dummy feature test must scope the native-dummy invariant to the native-dummy rule,
# because Ghost legitimately uses the same Workshop action for human players.
replace_regex(
    "tests/test_dummy_bots.py",
    r'''    def test_only_native_dummies_ignore_walls_but_keep_floor_collision\(self\):\n.*?\n    def test_dummy_reserves_the_last_human_slot_and_leaves_at_full_team''',
    '''    def test_only_native_dummies_ignore_walls_but_keep_floor_collision(self):\n        action = "Disable Movement Collision With Environment(Event Player, False);"\n        for source in (self.it, self.en):\n            start = source.index('"03c - Bot/Dummy: Kunci saat hidup kembali atau pahlawan berganti"')\n            end = source.index('"04 - Pemain Keluar: Bersihkan hanya saat benar-benar keluar"', start)\n            block = source[start:end]\n            self.assertEqual(block.count(action), 1)\n            self.assertNotIn("Disable Movement Collision With Environment(Event Player, True);", block)\n            self.assertIn(\n                "If(Is Dummy Bot(Event Player) == True);\\n"\n                "\\t\\t\\tEnable Movement Collision With Players(Event Player);\\n"\n                f"\\t\\t\\t{action}",\n                block,\n            )\n\n    def test_dummy_reserves_the_last_human_slot_and_leaves_at_full_team''',
)

# Restore the intended global-slot lifecycle tests: they guard absence of the deleted pending flag,
# not absence of Ghost, which is intentionally reasserted after team/hero changes.
replace_exact(
    "tests/test_validate_workshop.py",
    '        self.assertNotIn("Global.PemainAktif.GhostAktif == True", fast.body)\n',
    '        self.assertNotIn("SegarkanRosterTertunda", fast.body)\n',
    expected=2,
)
replace_exact(
    "tests/test_validate_workshop.py",
    '        self.assertIn("Global.PemainAktif.GhostAktif = False;", fast.body)\n',
    '        self.assertNotIn("SegarkanRosterTertunda", fast.body)\n',
    expected=1,
)
replace_exact(
    "tests/test_validate_workshop.py",
    '        self.assertIn("Event Player.GhostAktif = False;", roster.body)\n',
    '        self.assertNotIn("SegarkanRosterTertunda", roster.body)\n',
    expected=1,
)
replace_exact(
    "tests/test_validate_workshop.py",
    '        mutated = self.replace_in_rule(fast, "Global.PemainAktif.GhostAktif = False;", "Global.PemainAktif.GhostAktif = True;")\n        self.assert_rejected(mutated, "dispatcher team-switch leggero incompleto")\n',
    '        self.assertNotIn("SegarkanRosterTertunda", fast.body)\n',
    expected=1,
)
replace_exact(
    "tests/test_validate_workshop.py",
    '        self.assert_rejected(mutated, "13 subroutine pagina")\n',
    '        self.assert_rejected(mutated, "14 subroutine pagina")\n',
    expected=1,
)

# Mutation tests for native dummy collision now target the actual 03c native-dummy rule.
dummy_rule_selector = '''        dummy = self.rule(\n            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"\n            and "Or(Is Dummy Bot(Event Player), Event Player.BotOtomatis) == True;" in rule.body\n            and "Disable Movement Collision With Environment(Event Player, False);" in rule.body\n        )\n'''
replace_regex(
    "tests/test_validate_workshop.py",
    r'''    def test_native_dummy_wall_collision_does_not_apply_to_ibots\(self\) -> None:\n.*?\n    def test_native_dummy_explicitly_keeps_player_collision_enabled''',
    '''    def test_native_dummy_wall_collision_does_not_apply_to_ibots(self) -> None:\n''' + dummy_rule_selector + '''        mutated = self.replace_in_rule(\n            dummy,\n            "If(Is Dummy Bot(Event Player) == True);",\n            "If(Event Player.BotOtomatis == True);",\n        )\n        self.assert_rejected(mutated, "collisioni dummy non protette")\n\n    def test_native_dummy_explicitly_keeps_player_collision_enabled''',
)
replace_regex(
    "tests/test_validate_workshop.py",
    r'''    def test_native_dummy_explicitly_keeps_player_collision_enabled\(self\) -> None:\n.*?\n    def test_native_dummy_wall_collision_branch_cannot_be_made_unreachable''',
    '''    def test_native_dummy_explicitly_keeps_player_collision_enabled(self) -> None:\n''' + dummy_rule_selector + '''        mutated = self.replace_in_rule(\n            dummy,\n            "Enable Movement Collision With Players(Event Player);",\n            "Disable Movement Collision With Players(Event Player);",\n        )\n        self.assert_rejected(mutated, "collisioni dummy non protette")\n\n    def test_native_dummy_wall_collision_branch_cannot_be_made_unreachable''',
)
replace_regex(
    "tests/test_validate_workshop.py",
    r'''    def test_native_dummy_wall_collision_branch_cannot_be_made_unreachable\(self\) -> None:\n.*?\n    def test_native_dummy_wall_collision_rule_cannot_have_an_impossible_condition''',
    '''    def test_native_dummy_wall_collision_branch_cannot_be_made_unreachable(self) -> None:\n''' + dummy_rule_selector + '''        mutated = self.replace_in_rule(\n            dummy,\n            "Call Subroutine(KunciBot);\\n\\t\\tIf(Is Dummy Bot(Event Player) == True);",\n            "Call Subroutine(KunciBot);\\n\\t\\tAbort;\\n\\t\\tIf(Is Dummy Bot(Event Player) == True);",\n        )\n        self.assert_rejected(mutated, "sequenza raggiungibile e isolata")\n\n    def test_native_dummy_wall_collision_rule_cannot_have_an_impossible_condition''',
)
replace_regex(
    "tests/test_validate_workshop.py",
    r'''    def test_native_dummy_wall_collision_rule_cannot_have_an_impossible_condition\(self\) -> None:\n.*?\n    def ''',
    '''    def test_native_dummy_wall_collision_rule_cannot_have_an_impossible_condition(self) -> None:\n''' + dummy_rule_selector + '''        mutated = self.inject_condition(dummy, "Is Dummy Bot(Event Player) == False;")\n        self.assert_rejected(mutated, "collisione ambiente dummy: condizioni esatte e raggiungibili")\n\n    def ''',
)

# Changelog wording: the obsolete roster flag is removed, not repurposed.
replace_exact(
    "CHANGELOG.md",
    "il vecchio flag roster morto `SegarkanRosterTertunda` è stato riutilizzato senza aggiungere un nuovo array globale.",
    "il vecchio flag roster morto `SegarkanRosterTertunda` è stato rimosso; Ghost riusa il profilo sociale già esistente senza aggiungere un nuovo array globale.",
)

print("Remaining Ghost validation repair complete")
