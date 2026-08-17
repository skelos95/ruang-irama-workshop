from __future__ import annotations

import re
import subprocess
from pathlib import Path

BASE_PATCH_COMMIT = "264fcc882a77b3688d92ff81b13cfe505cbf76f5"
payload = subprocess.check_output(
    ["git", "show", f"{BASE_PATCH_COMMIT}:.github/maintenance/patch.py"],
    text=True,
)
payload = payload.replace(
    '    joined = "\\n".join(mask_strings(rule.body) for rule in managers)',
    '    joined = "\\\\n".join(mask_strings(rule.body) for rule in managers)',
    1,
)
payload = payload.replace(
    'main_call + "\\n    check_global_first_phase_one(checks, source, rules)"',
    'main_call + "\\n        check_global_first_phase_one(checks, source, rules)"',
    1,
)
exec(compile(payload, ".github/maintenance/global_first_070.py", "exec"))

ROOT = Path(__file__).resolve().parents[2]
VAL = ROOT / "tools" / "validate_workshop.py"
TESTS = ROOT / "tests" / "test_validate_workshop.py"

# Strengthen the new architecture check so migrated invariants are certified in their
# new global location rather than silently dropping legacy tests.
val = VAL.read_text(encoding="utf-8")
marker = "\n\n\ndef check_source_structure("
insert = '''
    fast = next((mask_strings(rule.body) for rule in managers if rule.name.startswith("04g - Global-first:")), "")
    slow = next((mask_strings(rule.body) for rule in managers if rule.name.startswith("04h - Global-first:")), "")
    checks.require(
        "If(Is Alive(Global.PemainAktif) == True);" in fast
        and "If(Global.PemainAktif.PerintahMenu == 3);" in fast,
        "global-first: Primary menu non protetto dal guard alive",
    )
    checks.require(
        "Global.PemainAktif.KartuNasibAktif == False" in fast
        and "Global.PemainAktif.PerintahMenu = 1;" in fast,
        "global-first: dispatcher menu non bloccato durante Try Your Luck",
    )
    checks.require(
        "Global.PemainAktif.PerintahTeleportasi == 0" in fast
        and "Global.PemainAktif.PerintahTeleportasi = 1;" in fast
        and "Global.PemainAktif.PerintahMenu" in fast,
        "global-first: dispatcher Teleport/Menu incompleto",
    )
    checks.require(
        "Health(Global.PemainAktif) >= Max Health(Global.PemainAktif)" in fast
        and "Set Health(Global.PemainAktif, 1);" in fast,
        "global-first: invariant 1 HP deve restare >= Max Health → Set Health 1",
    )
    checks.require(
        "Global.PemainAktif.ModeKebal == 2" in fast
        and "Set Health(Global.PemainAktif, Max Health(Global.PemainAktif));" in fast,
        "global-first: mantenimento FULL HP assente",
    )
    checks.require(
        "Global.PemainAktif.KunciBotAktif == True" in slow
        and "Global.PemainAktif.KunciBotAktif = False;" in slow
        and "Global.PemainAktif.PahlawanBotTerakhir = Null;" in slow,
        "global-first: reset latch bot dopo morte/despawn assente",
    )
    checks.require(
        "Global.PemainAktif.PindahTimDiproses == True" in slow
        and "Global.PemainAktif.Manusia == True" in slow
        and "Has Spawned(Global.PemainAktif) == True" in slow
        and "Global.PemainAktif.HudPemainDibuat == True" in slow
        and "Global.PemainAktif.PindahTimDiproses = False;" in slow,
        "global-first: release team-switch prima del nuovo roster/HUD",
    )
    join_rules = [rule for rule in rules if code_contains(rule.body, "Player Joined Match;")]
    checks.require(
        len(join_rules) == 1 and code_contains(join_rules[0].body, "Call Subroutine(TenangkanPemain);"),
        "global-first: Player Joined deve quiescere con TenangkanPemain prima del setup",
    )
'''
if marker not in val:
    raise RuntimeError("validator global-first insertion marker missing")
val = val.replace(marker, insert + marker, 1)
VAL.write_text(val, encoding="utf-8")


def replace_test(text: str, name: str, block: str) -> str:
    pattern = re.compile(
        rf"(?ms)^    def {re.escape(name)}\(self\) -> None:\n.*?(?=^    def |^if __name__ ==)")
    text2, count = pattern.subn(block.rstrip() + "\n\n", text, count=1)
    if count != 1:
        raise RuntimeError(f"test block not found: {name}")
    return text2


tests = TESTS.read_text(encoding="utf-8")
manager_helper = '''    def global_manager(self, prefix: str) -> str:
        matches = [rule for rule in self.rules(self.source) if rule.name.startswith(prefix)]
        self.assertEqual(len(matches), 1)
        return validator.mask_strings(matches[0].body)
'''
class_marker = "    def rules(self, source: str) -> list[validator.Rule]:\n"
helper_pos = tests.index(class_marker)
helper_end = tests.index("\n\n", helper_pos)
tests = tests[:helper_end + 2] + manager_helper + "\n" + tests[helper_end + 2:]

replacements = {
"test_bot_rapid_respawn_must_not_fall_back_to_periodic_watchdog": '''    def test_bot_rapid_respawn_must_not_fall_back_to_periodic_watchdog(self) -> None:
        slow = self.global_manager("04h - Global-first:")
        self.assertIn("Global.PemainAktif.KunciBotAktif == True", slow)
        self.assertIn("Global.PemainAktif.KunciBotAktif = False;", slow)
        self.assertIn("Global.PemainAktif.PahlawanBotTerakhir = Null;", slow)
        self.assertNotIn("Wait(0.500", slow)
''',
"test_dead_menu_primary_handler_requires_alive_guard": '''    def test_dead_menu_primary_handler_requires_alive_guard(self) -> None:
        fast = self.global_manager("04g - Global-first:")
        alive = fast.find("If(Is Alive(Global.PemainAktif) == True);")
        primary = fast.find("If(Global.PemainAktif.PerintahMenu == 3);", alive)
        self.assertTrue(0 <= alive < primary)
''',
"test_team_rejoin_lock_must_survive_until_new_roster_hud": '''    def test_team_rejoin_lock_must_survive_until_new_roster_hud(self) -> None:
        slow = self.global_manager("04h - Global-first:")
        for token in (
            "Global.PemainAktif.PindahTimDiproses == True",
            "Global.PemainAktif.Manusia == True",
            "Has Spawned(Global.PemainAktif) == True",
            "Global.PemainAktif.HudPemainDibuat == True",
            "Global.PemainAktif.PindahTimDiproses = False;",
        ):
            self.assertIn(token, slow)
''',
"test_team_rejoin_must_quiesce_before_first_yield": '''    def test_team_rejoin_must_quiesce_before_first_yield(self) -> None:
        join_at = self.source.index('rule("01 - Pemain Masuk atau Pindah Tim:')
        join_end = self.source.index('\\nrule("01b - ', join_at)
        join_rule = self.source[join_at:join_end]
        mutated_join = join_rule.replace("\\t\\tCall Subroutine(TenangkanPemain);\\n", "", 1)
        self.assertNotEqual(mutated_join, join_rule)
        mutated = self.source[:join_at] + mutated_join + self.source[join_end:]
        checks = validator.Checks()
        validator.check_global_first_phase_one(checks, mutated, self.rules(mutated))
        self.assertTrue(any("TenangkanPemain" in error for error in checks.errors), checks.errors)
''',
"test_team_rejoin_must_reset_session_state_and_release_boundary": '''    def test_team_rejoin_must_reset_session_state_and_release_boundary(self) -> None:
        slow = self.global_manager("04h - Global-first:")
        release = slow.find("Global.PemainAktif.PindahTimDiproses = False;")
        self.assertGreater(release, slow.find("Has Spawned(Global.PemainAktif) == True"))
        self.assertGreater(release, slow.find("Global.PemainAktif.HudPemainDibuat == True"))
        setup_at = self.source.index('rule("94 - ')
        setup = self.source[setup_at:]
        self.assertIn("Event Player.PernahDisiapkan = True;", setup)
        self.assertIn("Event Player.SudahSiap = True;", setup)
''',
"test_teleport_dispatcher_stays_separate": '''    def test_teleport_dispatcher_stays_separate(self) -> None:
        fast = self.global_manager("04g - Global-first:")
        self.assertIn("Global.PemainAktif.PerintahTeleportasi == 0", fast)
        self.assertIn("Global.PemainAktif.PerintahTeleportasi = 1;", fast)
        self.assertIn("Global.PemainAktif.PerintahMenu", fast)
        self.assertNotEqual(fast.find("Global.PemainAktif.PerintahTeleportasi"), fast.find("Global.PemainAktif.PerintahMenu"))
''',
"test_unkillable_mode_fixers_must_be_separate": '''    def test_unkillable_mode_fixers_must_be_separate(self) -> None:
        fast = self.global_manager("04g - Global-first:")
        one_hp = "Health(Global.PemainAktif) >= Max Health(Global.PemainAktif)"
        full_hp = "Set Health(Global.PemainAktif, Max Health(Global.PemainAktif));"
        self.assertIn(one_hp, fast)
        self.assertIn("Set Health(Global.PemainAktif, 1);", fast)
        self.assertIn(full_hp, fast)
        self.assertLess(fast.find(one_hp), fast.find(full_hp))
''',
"test_luck_menu_must_stay_open_and_locked": '''    def test_luck_menu_must_stay_open_and_locked(self) -> None:
        fast = self.global_manager("04g - Global-first:")
        self.assertIn("Global.PemainAktif.KartuNasibAktif == False", fast)
        self.assertIn("Global.PemainAktif.PerintahMenu = 1;", fast)
        self.assertNotIn("Global.PemainAktif.MenuTerbuka = False;", fast)
''',
"test_full_health_reset_to_one_is_required": '''    def test_full_health_reset_to_one_is_required(self) -> None:
        fast = self.global_manager("04g - Global-first:")
        self.assertIn("Health(Global.PemainAktif) >= Max Health(Global.PemainAktif)", fast)
        self.assertNotIn("Health(Global.PemainAktif) > Max Health(Global.PemainAktif)", fast)
''',
"test_english_word_in_rule_title_is_rejected": '''    def test_english_word_in_rule_title_is_rejected(self) -> None:
        mutated = self.source.replace(
            'rule("04g - Global-first: Pengatur pemain cepat terpusat")',
            'rule("04g - Global-first: fast respawn manager")', 1,
        )
        self.assertNotEqual(mutated, self.source)
        global_names, player_names, subroutines = validator.declaration_tables(mutated)
        checks = validator.Checks()
        validator.check_source_structure(checks, mutated, self.rules(mutated), global_names, player_names, subroutines)
        self.assertTrue(any("respawn" in error or "fast" in error for error in checks.errors), checks.errors)
''',
}
for name, block in replacements.items():
    if f"    def {name}(self) -> None:" in tests:
        tests = replace_test(tests, name, block)

TESTS.write_text(tests, encoding="utf-8")
