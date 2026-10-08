"""Maintenance contracts for the logical behavioral input before compilation."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RuntimeMaintenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.it = (ROOT / "source" / "ruang_irama.en-US.source").read_text(encoding="utf-8")
        cls.en = (ROOT / "tests" / "fixtures" / "semantic_reference.txt").read_text(encoding="utf-8")

    def test_display_name_is_not_used_as_cleanup_identity(self):
        for source, global_name in ((self.it, "Global"), (self.en, "Global")):
            self.assertNotIn(f'Mapped Array({global_name}.HumanPlayers, Custom String("{{0}}", Current Array Element))', source)

    def test_cached_player_name_drives_roster_and_world_text(self):
        for source, global_name, rule_kw in ((self.it, "Global", "rule"), (self.en, "Global", "rule")):
            self.assertIn("100: DisplayName", source)

            classifier = source.split(f'{rule_kw}("02 - ', 1)[1].split(f'{rule_kw}("03c - ', 1)[0]
            name_guard = "If(Or(Event Player.WasPrepared == False, Or(Event Player.DisplayName == Null, Event Player.DisplayName == Custom String(\"\"))));"
            name_assign = 'Event Player.DisplayName = Evaluate Once(Custom String("{0}", Event Player));'
            empty_guard = 'If(Or(Event Player.DisplayName == Null, Event Player.DisplayName == Custom String("")));'
            self.assertIn(name_guard, classifier)
            self.assertIn(name_assign, classifier)
            self.assertIn(empty_guard, classifier)
            self.assertLess(classifier.index(name_guard), classifier.index(name_assign))
            self.assertLess(classifier.index(name_assign), classifier.index(empty_guard))
            self.assertIn('Event Player.DisplayName = Evaluate Once(Custom String("{0}", Event Player));', classifier)

            roster = source.split(f'{rule_kw}("02 - ', 1)[1].split(f'{rule_kw}("03c - ', 1)[0]
            self.assertIn(
                'And(Event Player.DisplayName != Null, Event Player.DisplayName != Custom String(""))',
                roster,
            )
            self.assertNotIn('MenitLobi', source)
            self.assertNotIn('WaktuMasuk', source)
            self.assertIn('Custom String("{0} - {1}", Evaluate Once(Event Player.DisplayName),', roster)

            inspect = source.split(f'{rule_kw}("13 - ', 1)[1].split(f'{rule_kw}("16a - ', 1)[0]
            self.assertIn("Player Variable(Event Player.InspectionTarget, DisplayName)", inspect)
            self.assertIn(
                f"Array Contains({global_name}.HumanPlayers, Event Player.InspectionTarget) == True",
                inspect,
            )
            self.assertIn(
                f'Evaluate Once(Array Contains({global_name}.HumanPlayers, '
                'Event Player.InspectionTarget) == True ? '
                'Player Variable(Event Player.InspectionTarget, DisplayName) : '
                'Custom String("{0}", Is Duplicating(Event Player.InspectionTarget) ? '
                'Hero Being Duplicated(Event Player.InspectionTarget) : '
                'Hero Of(Event Player.InspectionTarget)))',
                inspect,
            )
            self.assertNotIn(
                'Custom String("{0}", Event Player.InspectionTarget))',
                inspect,
            )
            self.assertIn(
                f"Evaluate Once(Array Contains({global_name}.HumanPlayers, "
                "Event Player.InspectionTarget) == True ? "
                "Player Variable(Event Player.InspectionTarget, NameColor)",
                inspect,
            )
            self.assertNotIn(
                "Player Variable(Event Player.InspectionTarget, IsHuman) == True ? "
                "Player Variable(Event Player.InspectionTarget, DisplayName)",
                inspect,
            )

            teleport = source.split(f'{rule_kw}("19d - ', 1)[1].split(f'{rule_kw}("19e - ', 1)[0]
            self.assertIn("Player Variable(Event Player.TravelTargetCandidate, DisplayName)", teleport)
            self.assertIn(
                f"Array Contains({global_name}.HumanPlayers, Event Player.TravelTargetCandidate) == True",
                teleport,
            )
            self.assertIn(
                f'Evaluate Once(Array Contains({global_name}.HumanPlayers, '
                'Event Player.TravelTargetCandidate) == True ? '
                'Player Variable(Event Player.TravelTargetCandidate, DisplayName) : '
                'Custom String("{0}", Is Duplicating(Event Player.TravelTargetCandidate) ? '
                'Hero Being Duplicated(Event Player.TravelTargetCandidate) : '
                'Hero Of(Event Player.TravelTargetCandidate)))',
                teleport,
            )
            self.assertNotIn(
                'Custom String("{0}", Event Player.TravelTargetCandidate))',
                teleport,
            )
            self.assertIn(
                f"Evaluate Once(Array Contains({global_name}.HumanPlayers, "
                "Event Player.TravelTargetCandidate) == True ? "
                "Player Variable(Event Player.TravelTargetCandidate, NameColor)",
                teleport,
            )
            self.assertNotIn(
                "Player Variable(Event Player.TravelTargetCandidate, IsHuman) == True ? "
                "Player Variable(Event Player.TravelTargetCandidate, DisplayName)",
                teleport,
            )

            vision = source.split(f'{rule_kw}("18i - ', 1)[1].split(f'{rule_kw}("18j - ', 1)[0]
            self.assertIn(
                'Event Player.IsHuman == True ? Event Player.DisplayName : Custom String("{0}", Event Player)',
                vision,
            )

            fast = source.split(f'{rule_kw}("89a - ', 1)[1].split(f'{rule_kw}("89b - ', 1)[0]
            cache_invalid = f'Or({global_name}.ActivePlayer.DisplayName == Null, {global_name}.ActivePlayer.DisplayName == Custom String("") )'.replace('"") )', '""))')
            self.assertIn(cache_invalid, fast)
            self.assertIn(f'Custom String("{{0}}", {global_name}.ActivePlayer) != Custom String("")', fast)
            self.assertIn(f'{global_name}.ActivePlayer.DisplayName = Evaluate Once(Custom String("{{0}}", {global_name}.ActivePlayer));', fast)
            self.assertEqual(
                fast.count(
                    f'{global_name}.ActivePlayer.DisplayName = Evaluate Once(Custom String("{{0}}", {global_name}.ActivePlayer));'
                ),
                1,
            )
            self.assertLess(fast.index(cache_invalid), fast.index(f"{global_name}.ActivePlayer.IsHuman = True;"))

    def test_aim_scans_are_scheduler_cached(self):
        for source, rule_kw, global_name in ((self.it, "rule", "Global"), (self.en, "rule", "Global")):
            inspect = source.split(f'{rule_kw}("13 - ', 1)[1].split(f'{rule_kw}("16a - ', 1)[0]
            self.assertNotIn("Sorted Array(Filtered Array", inspect)
            self.assertIn("InspectionTargetCandidate", inspect)
            self.assertNotIn("19d0 - Teleportasi Jongkok", source)
            scheduler = source.split(f'{rule_kw}("89b - ', 1)[1].split(f'{rule_kw}("89c - ', 1)[0]
            self.assertIn("InspectionTargetCandidate", scheduler)
            self.assertIn("TravelTargetCandidate", scheduler)
            self.assertIn(f"Call Subroutine(RefreshActivePlayerPublicTargets);", scheduler)

    def test_safe_position_validator_is_shared_by_player_teleports(self):
        for source in (self.it, self.en):
            self.assertRegex(source, r"(?m)^\s*\d+: FindSafeTravelPosition$")
            self.assertGreaterEqual(source.count("Call Subroutine(FindSafeTravelPosition);"), 4)
            self.assertIn("Ray Cast Hit Position(Event Player.TravelDestination + Vector(0, 1, 0)", source)

    def test_burning_suspends_unkillable_and_scales_with_max_health(self):
        for source, global_name in ((self.it, "Global"), (self.en, "Global")):
            self.assertIn(f"Set Status({global_name}.ActivePlayer, Null, Burning, 10);", source)
            self.assertIn(f"Clear Status({global_name}.ActivePlayer, Unkillable);", source)
            self.assertIn(f"Damage({global_name}.ActivePlayer, {global_name}.ActivePlayer, Max Health({global_name}.ActivePlayer) * 0.050);", source)
            self.assertIn(f"{global_name}.ActivePlayer.NextLuckBurnTime = Total Time Elapsed + 1.000;", source)
            self.assertIn(f"And({global_name}.ActivePlayer.LuckEffect == 5, {global_name}.ActivePlayer.LuckEffectEndTime > Total Time Elapsed)", source)

    def test_shared_aim_distance_state_is_preserved(self):
        for source in (self.it, self.en):
            self.assertIn("AimDistance", source)
            self.assertIn("AimDistance = 25;", source)

    def test_native_completion_and_timer_are_bound_to_custom_countdown(self):
        for source, global_name, rule_kw in (
            (self.it, "Global", "rule"),
            (self.en, "Global", "rule"),
        ):
            self.assertIn("Disable Built-In Game Mode Completion;", source)
            self.assertIn(f"Set Match Time(Max(1, {global_name}.ServerTimeRemaining));", source)
            self.assertNotIn("ServerTimeRemaining + 5", source)
            self.assertIn("Is Game In Progress == True", source)
            self.assertIn(f"{global_name}.ServerTimeRemaining > 0", source)
            scheduler = source.split(
                f'{rule_kw}("04g - Global main loop: Central scheduler at 20 Hz")', 1
            )[1].split(f'{rule_kw}("05 - ', 1)[0]
            cadence = (
                f"If(And({global_name}.SchedulerStep % 20 == 0, "
                f"{global_name}.RestartRequested == False));"
            )
            cadence_position = scheduler.index(cadence)
            sync_position = scheduler.index(
                f"Set Match Time(Max(1, {global_name}.ServerTimeRemaining));"
            )
            outer_end = scheduler.index("\n\t\tEnd;", cadence_position)
            self.assertLess(sync_position, outer_end)

    def test_initial_skip_rules_are_bootstrap_only_and_locked_after_match_start(self):
        for source, global_name, rule_kw in (
            (self.it, "Global", "rule"),
            (self.en, "Global", "rule"),
        ):
            skip_heroes = source.split(
                f'{rule_kw}("00a2 - Global: Skip hero selection")', 1
            )[1].split(f'{rule_kw}("00a3 - ', 1)[0]
            self.assertIn(f"Count Of({global_name}.HumanPlayers) == 0;", skip_heroes)
            self.assertIn(f"{global_name}.TeamCyclePlayer == Null;", skip_heroes)
            self.assertEqual(skip_heroes.count("Set Match Time(0);"), 1)

            skip_setup = source.split(
                f'{rule_kw}("00a3 - Global: Skip initial setup")', 1
            )[1].split(
                f'{rule_kw}("00a4 - Global: Lock initial phase skipping after the game starts")', 1
            )[0]
            self.assertIn(f"Count Of({global_name}.HumanPlayers) == 0;", skip_setup)
            self.assertIn(f"{global_name}.TeamCyclePlayer == Null;", skip_setup)
            self.assertEqual(skip_setup.count("Set Match Time(0);"), 1)
            self.assertEqual(source.count("Set Match Time(0);"), 2)

            bootstrap_lock = source.split(
                f'{rule_kw}("00a4 - Global: Lock initial phase skipping after the game starts")', 1
            )[1].split(
                f'{rule_kw}("00c - Global: Restart exactly once when the countdown ends")', 1
            )[0]
            for token in (
                "Is Game In Progress == True;",
                f"Or({global_name}.HeroSelectionSkipped == False, {global_name}.SetupSkipped == False) == True;",
                f"{global_name}.HeroSelectionSkipped = True;",
                f"{global_name}.SetupSkipped = True;",
            ):
                self.assertIn(token, bootstrap_lock)

    def test_chill_star_uses_cached_name_and_color_in_a_dedicated_hud(self):
        for source, global_name, rule_kw in (
            (self.it, "Global", "rule"),
            (self.en, "Global", "rule"),
        ):
            self.assertIn("46: VoteLeaderName", source)
            self.assertIn("47: VoteLeaderColor", source)
            self.assertIn(f"{global_name}.VoteLeaderName = Custom String(\"\");", source)
            self.assertIn(f"{global_name}.VoteLeaderColor = Color(White);", source)

            init = source.split(f'{rule_kw}("00 - ', 1)[1].split(
                f'{rule_kw}("00a1 - Global: Start the game immediately while waiting for players")', 1
            )[0]
            self.assertIn(
                f"{global_name}.VoteLeaderName != Custom String(\"\") ?",
                init,
            )
            self.assertIn("Left, 13", init)
            self.assertIn(f"{global_name}.VoteLeaderColor", init)
            self.assertIn("\\nCHILL STAR: {0}", init)

            roster = source.split(f'{rule_kw}("02 - ', 1)[1].split(
                f'{rule_kw}("03c - Bot/Dummy', 1
            )[0]
            self.assertNotIn('Custom String("{0}{1}{2}"', roster)
            self.assertNotIn("CHILL STAR:", roster)
            self.assertIn(
                f"6 + Count Of(Filtered Array({global_name}.PlayerListHudIds, Current Array Element != 0))",
                roster,
            )

            leader_calc = source.split(f'{rule_kw}("91q - ', 1)[1].split(
                f'{rule_kw}("93 - Subroutine: Start the dynamic left shoulder camera")', 1
            )[0]
            self.assertIn(f"{global_name}.VoteLeaderName = Custom String(\"\");", leader_calc)
            self.assertIn(f"{global_name}.VoteLeaderColor = Color(White);", leader_calc)
            self.assertIn(f"If({global_name}.VoteLeader != Null);", leader_calc)
            self.assertIn(
                f"{global_name}.VoteLeaderName = Player Variable({global_name}.VoteLeader, DisplayName);",
                leader_calc,
            )
            self.assertIn(
                f"{global_name}.VoteLeaderColor = Player Variable({global_name}.VoteLeader, NameColor);",
                leader_calc,
            )

            color_page = source.split(f'{rule_kw}("99c - ', 1)[1].split(
                f'{rule_kw}("99d - Subrutin: Terapkan halaman bahasa")', 1
            )[0]
            self.assertIn(f"If({global_name}.VoteLeader == Event Player);", color_page)
            self.assertIn(f"{global_name}.VoteLeaderColor = Event Player.NameColor;", color_page)

    def test_crouch_teleport_has_five_pages_and_single_shot_self_kill(self):
        for source, rule_kw, global_name in ((self.it, "rule", "Global"), (self.en, "rule", "Global")):
            self.assertIn("TravelCursor %= 5;", source)
            self.assertIn("Event Player.TravelCommand = 1;", source)
            self.assertIn("Event Player.TravelCommand = 2;", source)
            self.assertIn("Event Player.TravelCommand = 3;", source)
            self.assertIn("TravelCommand == 3;", source)
            self.assertIn("(Event Player.TravelCursor + (Event Player.TravelCommand == 1 ? 1 : 4)) % 5", source)
            teleport_render = source.split(f'{rule_kw}("91g - ', 1)[1].split(f'{rule_kw}("', 1)[0]
            self.assertNotIn("\\\\", teleport_render)
            self.assertNotIn('Custom String("{0}n{1}"', teleport_render)
            self.assertIn('Custom String("{0} | {1}", Custom String("Hold {0} / release: close"', teleport_render)
            for token in (
                "1/5 | TELEPORT: SPAWN ROOM",
                "2/5 | TELEPORT: OBJECTIVE",
                "3/5 | TELEPORT TO PLAYER/BOT",
                '4/5 | ATTACH TO PLAYER/BOT',
                "5/5 | SELF ELIMINATION",
                'NO PUBLIC TARGET AVAILABLE',
            ):
                self.assertIn(token, teleport_render)
            self.assertIn("Custom Color(190 + X Component Of(Event Player.MenuColor) * 0.250", teleport_render)
            self.assertIn("Custom Color(X Component Of(Event Player.MenuColor)", teleport_render)
            self.assertIn("Visible To String and Color", teleport_render)
            transition = source.split(f'{rule_kw}("91k - ', 1)[1].split(f'{rule_kw}("91l - ', 1)[0]
            for color in (
                "Vector(80, 255, 160)",
                "Vector(65, 225, 255)",
                "Vector(95, 150, 255)",
                "Vector(195, 100, 255)",
                "Vector(255, 85, 135)",
            ):
                self.assertIn(color, transition)
            self.assertIn("Event Player.CrouchTravelActive == True", transition)
            self.assertIn("Chase Player Variable Over Time(Event Player, MenuColor, Event Player.TravelCursor", transition)
            self.assertIn("0.180, Destination and Duration", transition)
            self.assertNotIn("Global.TravelCursor", teleport_render)
            self.assertIn("Vector(1.500, 1, 0)", source)
            self.assertIn("Vector(-1.500, 1, 0)", source)
            self.assertIn("Vector(0, 1, 1.500)", source)
            self.assertIn("Vector(0, 1, -1.500)", source)
            self.assertIn("Event Player.SafeRevivePosition += Vector(0, 0.500, 0);", source)
            self.assertIn("Vector(0, 2.750, 0)", source)
            self.assertIn("Vector(1.500, 1.000, 0)", source)
            self.assertIn("Vector(-1.500, 1.000, 0)", source)
            dummy_spawn = source.split(f'{rule_kw}("03f - ', 1)[1].split(f'{rule_kw}("03g - ', 1)[0]
            self.assertIn("Call Subroutine(FindSafeTravelPosition);", dummy_spawn)
            self.assertIn("Teleport(Event Player, Event Player.SafeRevivePosition);", dummy_spawn)

            interact = source.split(f'{rule_kw}("19e - ', 1)[1].split(f'{rule_kw}("19f - ', 1)[0]
            self.assertEqual(interact.count("Kill(Event Player, Null);"), 1)
            self.assertIn("If(Total Time Elapsed >= Event Player.NextSuicideTime);", interact)
            self.assertIn("Event Player.NextSuicideTime = Total Time Elapsed + 3;", interact)
            self.assertIn("Round To Integer(Event Player.NextSuicideTime - Total Time Elapsed, Up)", interact)
            self.assertIn("Clear Status(Event Player, Unkillable);", interact)
            self.assertIn("Set Damage Received(Event Player, 100);", interact)
            self.assertNotIn("Wait(", interact)
            self.assertNotIn("Loop;", interact)
            self.assertNotIn("BunuhDiriDiminta", source)

            fast = source.split(f'{rule_kw}("89a - ', 1)[1].split(f'{rule_kw}("89b - ', 1)[0]
            self.assertNotIn("BunuhDiriDiminta", fast)
            self.assertEqual(fast.count("Kill("), 1)
            self.assertIn(f"Kill({global_name}.ActivePlayer, {global_name}.ActivePlayer.RevengeDeathPending == True ?", fast)
        self.assertEqual(source.count("Kill("), 4)

    def test_crouch_attach_auto_detach_reacts_to_invalidating_state(self):
        for source, rule_kw, conditions_kw, actions_kw in (
            (self.it, "rule", "conditions", "actions"),
            (self.en, "rule", "conditions", "actions"),
        ):
            auto_detach = source.split(
                f'{rule_kw}("19h - Crouch Travel: Detach when player state changes")', 1
            )[1].split(f'{rule_kw}("19g - ', 1)[0]
            conditions = auto_detach.split(f"\t{conditions_kw}\n\t{{", 1)[1].split(
                f"\n\t}}\n\n\t{actions_kw}", 1
            )[0]
            actions = auto_detach.split(f"\t{actions_kw}\n\t{{", 1)[1]

            for token in (
                "Event Player.TravelAttachmentActive == True;",
                "Has Spawned(Event Player) == False",
                "Is Alive(Event Player) == False",
                "Event Player.TravelAttachmentTarget == Null",
                "Entity Exists(Event Player.TravelAttachmentTarget) == False",
                "Has Spawned(Event Player.TravelAttachmentTarget) == False",
                "Is Alive(Event Player.TravelAttachmentTarget) == False",
                "Hero Of(Event Player) != Event Player.AttachmentOwnerHero",
                "Hero Of(Event Player.TravelAttachmentTarget) != Event Player.AttachmentTargetHero",
                "Player Variable(Event Player.TravelAttachmentTarget, IsHuman) == True",
                "Player Variable(Event Player.TravelAttachmentTarget, InspectionPrivacyActive) == True",
            ):
                self.assertIn(token, conditions)

            self.assertEqual(actions.count("Detach Players(Event Player);"), 1)
            for clear in (
                "Set Player Variable(Event Player, TravelAttachmentActive, False);",
                "Set Player Variable(Event Player, TravelAttachmentTarget, Null);",
                "Set Player Variable(Event Player, AttachmentOwnerHero, Null);",
                "Set Player Variable(Event Player, AttachmentTargetHero, Null);",
            ):
                self.assertEqual(actions.count(clear), 1)
            self.assertNotIn("\t\tIf(", actions)
            self.assertNotIn("Wait(", auto_detach)
            self.assertNotIn("Loop", auto_detach)

    def test_crouch_attach_uses_native_attach_and_crouch_reload_detach(self):
        for source, rule_kw in ((self.it, "rule"), (self.en, "rule")):
            self.assertIn("Attach Players(Event Player, Event Player.TravelAttachmentTarget, Vector(0,", source)
            self.assertIn("+ 0.750, 0));", source)
            self.assertIn("Detach Players(Event Player);", source)
            attach_rule = source.split(f'{rule_kw}("19e - ', 1)[1].split(f'{rule_kw}("19f - ', 1)[0]
            detach_rules = source.split(f'{rule_kw}("19f - ', 1)[1].split(f'{rule_kw}("19g - ', 1)[0]
            manual_detach = detach_rules.split(f'{rule_kw}("19h - ', 1)[0]
            self.assertIn("Event Player.MenuOpen == False;", manual_detach)
            self.assertIn("Is Button Held(Event Player, Button(Crouch)) == True;", manual_detach)
            self.assertIn("Is Button Held(Event Player, Button(Reload)) == True;", manual_detach)
            self.assertNotIn("Event Player.CrouchTravelActive == False;", manual_detach)
            self.assertNotIn("Disallow Button(Event Player, Button(Reload));", attach_rule)
            self.assertNotIn("Allow Button(Event Player, Button(Reload));", detach_rules)
            self.assertIn("{0}: use / {1}+{2}: detach", source)
            self.assertIn("Input Binding String(Button(Crouch))", source)
            self.assertIn("Input Binding String(Button(Reload))", source)
            self.assertNotIn("CROUCH + RELOAD: DETACH", source)
            self.assertIn("92: TravelAttachmentTarget", source)
            self.assertIn("93: TravelAttachmentActive", source)

    def test_crouch_attach_auto_detaches_on_death_leave_or_hero_change(self):
        for source in (self.it, self.en):
            self.assertIn("Entity Exists(Event Player.TravelAttachmentTarget) == False", source)
            self.assertIn("Is Alive(Event Player.TravelAttachmentTarget) == False", source)
            self.assertIn("Hero Of(Event Player) != Event Player.AttachmentOwnerHero", source)
            self.assertIn("Hero Of(Event Player.TravelAttachmentTarget) != Event Player.AttachmentTargetHero", source)

    def test_jump_resurrect_keeps_safe_deaths_in_place_and_recovers_void_deaths(self):
        for source, rule_kw in ((self.it, "rule"), (self.en, "rule")):
            resurrect = source.split(f'{rule_kw}("12f - ', 1)[1].split(f'{rule_kw}("12g - ', 1)[0]
            recovery_teleport = "Teleport(Event Player, Event Player.SafeRevivePosition + Vector(0, 0.500, 0));"
            self.assertIn("Event Player.SafeRevivePosition = Nearest Walkable Position(Position Of(Event Player));", resurrect)
            self.assertIn("Distance Between(Event Player.SafeRevivePosition, Event Player.DeathPosition) > 0.500", resurrect)
            self.assertNotIn("Nearest Walkable Position(Event Player.DeathPosition)", resurrect)
            self.assertEqual(resurrect.count("Ray Cast Hit Position(Event Player.DeathPosition + Vector(0, 1, 0), Event Player.DeathPosition - Vector(0, 3, 0)"), 1)
            self.assertNotIn("Call Subroutine(FindSafeTravelPosition);", resurrect)
            self.assertNotIn("Abort;", resurrect)
            self.assertNotIn("Event Player.CrouchTravelActive == False;", resurrect)
            self.assertNotIn("Spawn Points(Team Of(Event Player))", resurrect)
            self.assertEqual(resurrect.count(recovery_teleport), 2)
            self.assertLess(resurrect.index(recovery_teleport), resurrect.index("Resurrect(Event Player);"))
            self.assertLess(resurrect.index("Resurrect(Event Player);"), resurrect.rindex(recovery_teleport))
            self.assertIn("Event Player.GhostFlyPhysicsApplied = False;", resurrect)
            self.assertIn("Call Subroutine(ApplyGhostFlyPhysics);", resurrect)
            self.assertNotIn("Start Forcing Player Position(", source)

    def test_custom_string_uses_at_most_three_substitution_values(self):
        for source in (self.it, self.en):
            self.assertNotIn("{3}", source)
            self.assertIn('Custom String("{0} | {1}", Custom String("Hold {0}"', source)



    def test_team_switch_uses_full_cleanup_and_leave_cleanup_is_exact(self):
        for source, global_name, rule_kw in ((self.it, "Global", "rule"), (self.en, "Global", "rule")):
            self.assertNotIn(f'{rule_kw}("01 - Siklus tim: Pekerja pembersihan dari penjadwal global")', source)

            fast = source.split(f'{rule_kw}("89a - ', 1)[1].split(f'{rule_kw}("89b - ', 1)[0]
            self.assertIn(f"Array Contains({global_name}.HumanPlayers, {global_name}.ActivePlayer) == True", fast)
            self.assertNotIn(f"{global_name}.ActivePlayer.LastTeam != Team Of({global_name}.ActivePlayer)", fast)
            self.assertIn(f"{global_name}.ActivePlayer.IsHuman = True;", fast)
            self.assertIn(f"{global_name}.ActivePlayer.IsClassified = True;", fast)
            self.assertIn(f"{global_name}.ActivePlayer.IsPrepared = True;", fast)
            self.assertIn(f"{global_name}.ActivePlayer.WasPrepared = True;", fast)
            self.assertIn(
                f'If({global_name}.ActivePlayer.DisplayName == Custom String("งูแรร์"));',
                fast,
            )
            self.assertNotIn(
                f'If(Custom String("{{0}}", {global_name}.ActivePlayer) == Custom String("งูแรร์"));',
                fast,
            )
            self.assertIn(
                f'{global_name}.ActivePlayer.CustomSoundtrack = Custom String("Draconian");',
                fast,
            )
            classifier = source.split(f'{rule_kw}("02 - ', 1)[1].split(f'{rule_kw}("03c - ', 1)[0]
            self.assertIn(f"Array Contains({global_name}.HumanPlayers, Event Player) == False;", classifier)
            self.assertIn(f"If(Count Of({global_name}.AvailableHudSlots) == 0);", classifier)
            self.assertIn("Event Player.IsClassified = False;", classifier)
            self.assertIn("Event Player.IsPrepared = False;", classifier)
            self.assertIn("Event Player.TeamChangeProcessed = False;", classifier)
            self.assertIn(f"If({global_name}.TeamCyclePlayer == Event Player);", classifier)
            self.assertIn(f"{global_name}.TeamCyclePlayer = Null;", classifier)
            self.assertIn(f"{global_name}.TeamCycleTime = Total Time Elapsed + 0.250;", classifier)
            self.assertNotIn(f"Abort If(Count Of({global_name}.AvailableHudSlots) == 0);", classifier)
            self.assertNotIn("Server Load < 150", classifier)
            self.assertLess(
                classifier.index("Call Subroutine(LockBot);"),
                classifier.index(f"If(Count Of({global_name}.AvailableHudSlots) == 0);"),
            )
            self.assertNotIn("Call Subroutine(QuiescePlayer);", fast)
            self.assertNotIn("Call Subroutine(CleanupPlayer);", fast)
            self.assertIn(f"{global_name}.ActivePlayer.PlayerCycleActive == False", fast)
            switch = source.split(f'{rule_kw}("01a - ', 1)[1].split(f'{rule_kw}("01b - ', 1)[0]
            self.assertIn("Ongoing - Each Player;", switch)
            self.assertIn(f"Array Contains({global_name}.HumanPlayers, Event Player) == True;", switch)
            self.assertIn("Event Player.LastTeam != Team Of(Event Player);", switch)
            self.assertNotIn("Call Subroutine(QuiescePlayer);", switch)
            self.assertNotIn("Call Subroutine(CleanupPlayer);", switch)
            self.assertNotIn("Wait(", switch)
            self.assertNotIn(f"{global_name}.ActivePlayer", switch)
            self.assertNotIn(f"{global_name}.ActivePlayer.PlayerListUpdatePending = True;", fast)
            self.assertIn(f"{global_name}.ActivePlayer.TeamCycleDeadline = Total Time Elapsed + 0.250;", fast)
            self.assertIn(f"Has Spawned({global_name}.ActivePlayer) == True", fast)
            self.assertIn("Event Player.PlayerListUpdatePending = False;", switch)
            self.assertIn("Event Player.TeamChangeProcessed = True;", switch)
            self.assertIn("Event Player.PlayerCycleActive = True;", switch)
            self.assertIn("Event Player.IsPrepared = False;", switch)
            self.assertIn("Event Player.IsHuman = False;", switch)
            self.assertIn("Event Player.TeamCycleDeadline = Total Time Elapsed + 0.500;", switch)
            self.assertIn(f"Array Contains({global_name}.HumanPlayers, {global_name}.ActivePlayer) == False", fast)
            self.assertIn(f"{global_name}.ActivePlayer.TeamChangeProcessed = True;", fast)
            self.assertNotIn("Server Load < 150", fast)
            setup_worker = source.split(f'{rule_kw}("01b - ', 1)[1].split(f'{rule_kw}("02 - ', 1)[0]
            self.assertNotIn("Server Load < 150", setup_worker)
            self.assertNotIn("Call Subroutine(PreparePlayer);", fast)
            self.assertIn(
                f"Or(Array Contains({global_name}.HumanPlayers, {global_name}.ActivePlayer) == False, {global_name}.ActivePlayer.PlayerCycleActive == True)",
                fast,
            )
            self.assertIn(
                f"{global_name}.ActivePlayer.TeamCycleTargetTeam == Team Of({global_name}.ActivePlayer)",
                fast,
            )
            self.assertNotIn(f'{rule_kw}("02b - HUD Pemain', source)
            self.assertNotIn(f'{rule_kw}("02x - DEBUG', source)
            self.assertNotIn("DBG 02", source)

            roster_hud = source.split(f'{rule_kw}("02 - ', 1)[1].split(f'{rule_kw}("03c - ', 1)[0]
            self.assertNotIn("Is Alive(Event Player) == True;", roster_hud)
            self.assertNotIn("Server Load < 150", roster_hud)
            vote_dirty = f"{global_name}.VoteRecountNeeded = True;"
            self.assertIn(vote_dirty, roster_hud)
            self.assertIn("Create HUD Text(", roster_hud)
            append_roster = f"{global_name}.HumanPlayers = Append To Array({global_name}.HumanPlayers, Event Player);"
            left_create = roster_hud.index("Create HUD Text(")
            self.assertEqual(roster_hud.count("Create HUD Text("), 1)
            self.assertLess(roster_hud.index(append_roster), roster_hud.index("Event Player.IsHuman = True;"))
            self.assertLess(roster_hud.index("Event Player.IsHuman = True;"), roster_hud.index(vote_dirty))
            self.assertLess(
                roster_hud.index(vote_dirty),
                left_create,
            )
            self.assertLess(left_create, roster_hud.index("Event Player.PlayerListHud = Last Text ID;"))
            self.assertGreater(
                roster_hud.index("Event Player.PlayerHudCreated = True;"),
                roster_hud.index(f"{global_name}.PlayerListHudIds[Index Of Array Value({global_name}.HumanPlayers, Event Player)] = Event Player.PlayerListHud;"),
            )
            self.assertLess(
                roster_hud.index("Event Player.PlayerHudCreated = True;"),
                roster_hud.index('Welcome to Cozywatch! Pick a vibe & color. Stay weird.'),
            )
            self.assertEqual(
                source.count("Player Variable(Current Array Element, PlayerListUpdatePending) == False"),
                3,
            )

            setup = source.split(f'{rule_kw}("01b - ', 1)[1].split(f'{rule_kw}("02 - ', 1)[0]
            self.assertNotIn("Disable Game Mode HUD(Event Player);", setup)
            self.assertNotIn("Disable Game Mode In-World UI(Event Player);", setup)
            self.assertIn("Call Subroutine(QuiescePlayer);", setup)
            self.assertIn(f"If(Array Contains({global_name}.HumanPlayers, Event Player));", setup)
            self.assertIn("Call Subroutine(CleanupPlayer);", setup)
            self.assertIn("Call Subroutine(PreparePlayer);", setup)
            wait_mode = "Abort When False"
            wait = f"Wait(0.050, {wait_mode});"
            self.assertEqual(setup.count("Wait("), 2)
            self.assertEqual(setup.count(wait), 2)
            first_wait, second_wait = setup.index(wait), setup.rindex(wait)
            self.assertLess(setup.index("Call Subroutine(QuiescePlayer);"), first_wait)
            self.assertLess(first_wait, setup.index("Call Subroutine(CleanupPlayer);"))
            self.assertLess(setup.index("Call Subroutine(CleanupPlayer);"), second_wait)
            self.assertLess(second_wait, setup.index("Call Subroutine(PreparePlayer);"))

            scheduler = source.split(f'{rule_kw}("04g - ', 1)[1].split(f'{rule_kw}("05 - ', 1)[0]
            self.assertIn(f"{global_name}.PlayerListSnapshot = All Players(All Teams);", scheduler)
            self.assertIn(
                f"{global_name}.ActivePlayer = {global_name}.PlayerListSnapshot[{global_name}.SchedulerPlayerIndex];",
                scheduler,
            )

            left = source.split(f'{rule_kw}("04 - ', 1)[1].split(f'{rule_kw}("04g - ', 1)[0]
            self.assertIn("Wait(0.500,", left)
            self.assertIn("Abort If(Entity Exists(Event Player) == True);", left)
            self.assertNotIn("Call Subroutine(QuiescePlayer);", left)
            self.assertIn("Call Subroutine(CleanupPlayer);", left)

            cleanup = source.split(f'{rule_kw}("93c - ', 1)[1].split(f'{rule_kw}("', 1)[0]
            self.assertIn(f"{global_name}.CleanupSubject = Event Player;", cleanup)
            self.assertIn(f"{global_name}.LeavingPlayerIndex = Index Of Array Value({global_name}.HumanPlayers, {global_name}.CleanupSubject);", cleanup)
            self.assertNotIn("Index Of Array Value(" + global_name + ".PlayerHudSlots", cleanup)
            self.assertEqual(cleanup.count("For Global Variable("), 1)
            self.assertIn(
                f"For Global Variable(VoterIndex, 0, Count Of({global_name}.HumanPlayers), 1);",
                cleanup,
            )
            self.assertEqual(cleanup.count("Filtered Array("), 1)
            self.assertIn(
                f"Set Player Variable(Filtered Array({global_name}.HumanPlayers, Player Variable(Current Array Element, VotedPlayer) == {global_name}.CleanupSubject), VotedPlayer, Null);",
                cleanup,
            )
            self.assertNotIn("Allow Button(", cleanup)
            self.assertNotIn("Clear Status(", cleanup)
            self.assertNotIn("Set Move Speed(", cleanup)
            self.assertIn(
                f"Modify Player Variable({global_name}.HumanPlayers[{global_name}.VoterIndex], RevengeKillers, Remove From Array By Index, {global_name}.LeavingRevengeIndex);",
                cleanup,
            )
            self.assertIn(
                f"Modify Player Variable({global_name}.HumanPlayers[{global_name}.VoterIndex], RevengeDebts, Remove From Array By Index, {global_name}.LeavingRevengeIndex);",
                cleanup,
            )
            self.assertIn("Remove From Array By Index", cleanup)


if __name__ == "__main__":
    unittest.main()
