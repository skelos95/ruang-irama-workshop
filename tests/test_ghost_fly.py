"""Ghost/Fly contracts for the logical behavioral input, before compilation."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def workshop_rules(source: str) -> list[tuple[str, str]]:
    headers = list(re.finditer(r'(?m)^rule\("([^"]+)"\)\s*\{', source))
    return [
        (
            match.group(1),
            source[match.start() : headers[index + 1].start() if index + 1 < len(headers) else len(source)],
        )
        for index, match in enumerate(headers)
    ]


def rule_with(source: str, *tokens: str) -> str:
    matches = [body for _, body in workshop_rules(source) if all(token in body for token in tokens)]
    if len(matches) != 1:
        raise AssertionError(f"expected one Workshop rule containing {tokens!r}, found {len(matches)}")
    return matches[0]


def subroutine(source: str, name: str) -> str:
    return rule_with(source, "Subroutine;", f"\n\t\t{name};")


class GhostFlyRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.it = (ROOT / "source" / "ruang_irama.en-US.source").read_text(encoding="utf-8")
        cls.en = (ROOT / "tests" / "fixtures" / "semantic_reference.txt").read_text(encoding="utf-8")
        cls.sources = (
            (cls.it, "Global"),
            (cls.en, "Global"),
        )

    def test_page_thirteen_state_and_subroutines_are_declared_contiguously(self) -> None:
        declarations = (
            "101: GhostModeActive",
            "102: FlyModeActive",
            "103: GhostFlyCursor",
            "104: GhostFlyPhysicsApplied",
            "106: FlyRampStartTime",
            "107: FlyPercent",
            "108: FlyDirection",
            "109: FlyVelocityDelta",
        )
        for source, _ in self.sources:
            for declaration in declarations:
                with self.subTest(declaration=declaration):
                    self.assertEqual(source.count(declaration), 1)
            indices = []
            for name in ("DrawGhostFlyMenu", "ApplyGhostFlyPage", "ApplyGhostFlyPhysics", "ProcessPlayerFlight"):
                matches = re.findall(rf"(?m)^\s*(\d+): {name}$", source)
                self.assertEqual(len(matches), 1)
                indices.append(int(matches[0]))
            self.assertEqual(indices, list(range(indices[0], indices[0] + 4)))

    def test_main_menu_has_sixteen_pages_and_routes_page_thirteen(self) -> None:
        localized_titles = ("13 - GHOST MODE / FLY",)
        localized_tails = (("12 - DUMMY FOLLOW", "13 - GHOST MODE / FLY"),)
        for source, _ in self.sources:
            navigation = rule_with(source, "MainMenuCursor = (Event Player.MainMenuCursor", "MenuCommand == 3")
            self.assertIn(
                "Event Player.MainMenuCursor = (Event Player.MainMenuCursor + "
                "(Event Player.MenuCommand == 3 ? 1 : 15)) % 16;",
                navigation,
            )
            router = subroutine(source, "DrawActiveMenuPage")
            packed_router = compact(router)
            self.assertIn(
                "If(EventPlayer.MenuPage==-1);CallSubroutine(DrawMainMenu);ElseIf(EventPlayer.MenuPage==0);",
                packed_router,
            )
            self.assertNotIn("If(EventPlayer.MainMenuCursor==13);", packed_router)
            self.assertEqual(router.count("Call Subroutine(DrawGhostFlyMenu);"), 1)
            self.assertRegex(
                packed_router,
                r"MenuPage==13\);CallSubroutine\(DrawGhostFlyMenu\);",
            )
            main = subroutine(source, "DrawMainMenu")
            for page_twelve, page_thirteen in localized_tails:
                with self.subTest(page_twelve=page_twelve):
                    self.assertIn(
                        f'Event Player.MainMenuCursor == 12 ? Custom String("{page_twelve}',
                        main,
                    )
                    self.assertEqual(main.count(page_thirteen), 1)
            self.assertEqual(main.count("Event Player.GhostModeActive"), 1)
            self.assertEqual(main.count("Event Player.FlyModeActive"), 1)
            dispatcher = rule_with(source, "Event Player.MenuCommand == 1;", "ApplyDummyBotFollowPage")
            self.assertRegex(
                compact(dispatcher),
                r"MenuPage==13\);CallSubroutine\(ApplyGhostFlyPage\);",
            )
            transition = subroutine(source, "TransitionMenuColor")
            self.assertIn("EventPlayer.MenuPage)==13?", compact(transition))
            self.assertIn("Vector(0,234,234)*0.320", compact(transition))
            for token in localized_titles:
                self.assertIn(token, source)

    def test_page_thirteen_renderer_has_two_independent_english_rows(self) -> None:
        for source, _ in self.sources:
            renderer = subroutine(source, "DrawGhostFlyMenu")
            self.assertEqual(renderer.count("Create HUD Text("), 1)
            self.assertNotIn("Event Player.MenuPage == -1", renderer)
            for token in ("GhostFlyCursor", "GhostModeActive", "FlyModeActive", "/2",
                          "GHOST MODE", "FLY", "KEEP MOVING: 100% > 1000% / 20s"):
                self.assertIn(token, renderer)
            self.assertIn("Input Binding String(Button(Crouch))", renderer)

    def test_page_thirteen_navigation_selects_exactly_two_rows(self) -> None:
        for source, _ in self.sources:
            navigation = rule_with(source, "MainMenuCursor = (Event Player.MainMenuCursor", "GhostFlyCursor")
            self.assertRegex(
                compact(navigation),
                r"MenuPage==13\);EventPlayer.GhostFlyCursor="
                r"\(EventPlayer.GhostFlyCursor\+1\)%2;",
            )

    def test_apply_toggles_only_the_selected_feature_and_rearms_physics(self) -> None:
        toggle_patterns = {
            "GhostModeActive": re.compile(
                r"EventPlayer\.GhostModeActive="
                r"(?:EventPlayer\.GhostModeActive==False|Not\(EventPlayer\.GhostModeActive\)|!EventPlayer\.GhostModeActive);"
            ),
            "FlyModeActive": re.compile(
                r"EventPlayer\.FlyModeActive="
                r"(?:EventPlayer\.FlyModeActive==False|Not\(EventPlayer\.FlyModeActive\)|!EventPlayer\.FlyModeActive);"
            ),
        }
        for source, _ in self.sources:
            apply = subroutine(source, "ApplyGhostFlyPage")
            packed = compact(apply)
            cursor = packed.index("If(EventPlayer.GhostFlyCursor==0);")
            fly_toggle = packed.index("EventPlayer.FlyModeActive=", cursor)
            rearm = packed.index("EventPlayer.GhostFlyPhysicsApplied=False;", fly_toggle)
            wall_branch = packed[cursor:fly_toggle]
            fly_branch = packed[fly_toggle:rearm]
            self.assertRegex(wall_branch, toggle_patterns["GhostModeActive"])
            self.assertNotRegex(wall_branch, r"FlyModeActive=(?!=)")
            self.assertRegex(fly_branch, toggle_patterns["FlyModeActive"])
            self.assertNotRegex(fly_branch, r"GhostModeActive=(?!=)")
            self.assertIn("EventPlayer.GhostFlyPhysicsApplied=False;", packed)
            self.assertIn("CallSubroutine(ApplyGhostFlyPhysics);", packed)

    def test_wall_ghost_disables_only_walls_and_never_player_collision(self) -> None:
        for source, _ in self.sources:
            physics = subroutine(source, "ApplyGhostFlyPhysics")
            packed = compact(physics)
            self.assertRegex(
                packed,
                r"If\(EventPlayer.GhostModeActive==True\);"
                r"DisableMovementCollisionWithEnvironment\(EventPlayer,False\);"
                r"Else;EnableMovementCollisionWithEnvironment\(EventPlayer\);",
            )
            self.assertNotIn("Disable Movement Collision With Environment(Event Player, True);", source)
            self.assertNotIn("Movement Collision With Players", physics)

    def test_fly_disables_native_locomotion_and_uses_zero_gravity(self) -> None:
        for source, _ in self.sources:
            physics = subroutine(source, "ApplyGhostFlyPhysics")
            packed = compact(physics)
            self.assertRegex(
                packed,
                r"If\(EventPlayer.FlyModeActive==True\);"
                r"If\(Or\(EventPlayer\.LuckEffect!=2,EventPlayer\.LuckEffectEndTime<=TotalTimeElapsed\)\);"
                r"SetMoveSpeed\(EventPlayer,0\);End;"
                r"SetGravity\(EventPlayer,0\);",
            )
            self.assertRegex(
                packed,
                r"Else;If\(Or\(EventPlayer\.LuckEffect!=2,EventPlayer\.LuckEffectEndTime<=TotalTimeElapsed\)\);"
                r"SetMoveSpeed\(EventPlayer,100\);If\(MagnitudeOf\(VelocityOf\(EventPlayer\)\)>0.010\);"
                r"ApplyImpulse\(EventPlayer,VelocityOf\(EventPlayer\)\*-1,MagnitudeOf\(VelocityOf\(EventPlayer\)\),"
                r"ToWorld,IncorporateContraryMotion\);End;End;SetGravity\(EventPlayer,100\);",
            )
            self.assertIn("EventPlayer.GhostFlyPhysicsApplied=True;", packed)
            self.assertNotIn("Start Accelerating(", physics)
            self.assertNotIn("Stop Accelerating(", physics)
            self.assertNotIn("Movement Collision With Players", physics)
            self.assertNotIn("Start Transforming Throttle(", source)
            self.assertIn("EventPlayer.FlyRampStartTime=-1;", packed)

    def test_any_horizontal_direction_builds_the_per_player_speed_ramp(self) -> None:
        for source, global_name in self.sources:
            packed = compact(subroutine(source, "ProcessPlayerFlight"))
            owner = f"{global_name}.ActivePlayer"
            luck = (
                f"If(And({owner}.LuckEffect==2,{owner}.LuckEffectEndTime>TotalTimeElapsed));"
            )
            direction_guard = (
                f"If(MagnitudeOf(Vector(XComponentOf(ThrottleOf({owner})),0,"
                f"ZComponentOf(ThrottleOf({owner}))))>0.050);"
            )
            timestamp_start = (
                f"If({owner}.FlyRampStartTime<0);"
                f"{owner}.FlyRampStartTime=TotalTimeElapsed;End;"
            )
            speed_formula = (
                f"{owner}.FlyPercent=Min(1000,100+Max(0,TotalTimeElapsed-"
                f"{owner}.FlyRampStartTime)*45);"
            )
            reset = (
                "Else;"
                f"{owner}.FlyRampStartTime=-1;"
                f"{owner}.FlyPercent=100;End;"
            )

            for token in (luck, direction_guard, timestamp_start, speed_formula, reset):
                self.assertIn(token, packed)
            self.assertLess(packed.index(luck), packed.index(direction_guard))
            self.assertLess(packed.index(direction_guard), packed.index(reset))
            self.assertNotIn("DotProduct(ThrottleOf(", packed)
            self.assertNotIn("StartAccelerating(", packed)
            self.assertNotIn("StopAccelerating(", packed)
            self.assertNotIn(f"{global_name}.FlyRampStartTime", source)
            cycle = subroutine(source, "ProcessPlayerCycle")
            self.assertNotIn("Min(1000, 100 +", cycle)

    def test_only_directional_deadzone_takes_the_reset_branch(self) -> None:
        """The reset belongs to the input deadzone, rather than any direction change."""
        for source, global_name in self.sources:
            packed = compact(subroutine(source, "ProcessPlayerFlight"))
            owner = f"{global_name}.ActivePlayer"
            direction = packed.index(
                f"If(MagnitudeOf(Vector(XComponentOf(ThrottleOf({owner})),0,"
                f"ZComponentOf(ThrottleOf({owner}))))>0.050);"
            )
            reset = packed.index(
                f"Else;{owner}.FlyRampStartTime=-1;",
                direction,
            )
            self.assertLess(direction, reset)
            reset_branch = packed[reset : packed.index("End;", reset) + len("End;")]
            self.assertEqual(reset_branch.count(f"{owner}.FlyRampStartTime=-1;"), 1)
            self.assertEqual(reset_branch.count(f"{owner}.FlyPercent=100;"), 1)

    def test_fly_3d_controller_applies_only_the_velocity_difference(self) -> None:
        for source, global_name in self.sources:
            owner = f"{global_name}.ActivePlayer"
            packed = compact(subroutine(source, "ProcessPlayerFlight"))
            for token in (
                f"{owner}.IsHuman==True",
                f"{owner}.IsAutomaticBot==False",
                f"IsDummyBot({owner})==False",
                f"HasSpawned({owner})==True",
                f"IsAlive({owner})==True",
                f"{owner}.FlyModeActive==True",
                f"{owner}.GhostFlyPhysicsApplied==True",
                f"{owner}.FlyDirection=FacingDirectionOf({owner})*Max(0,ZComponentOf(ThrottleOf({owner})))"
                f"+DirectionFromAngles(HorizontalFacingAngleOf({owner}),0)*Min(0,ZComponentOf(ThrottleOf({owner})))"
                f"+CrossProduct(Vector(0,1,0),DirectionFromAngles(HorizontalFacingAngleOf({owner}),0))*"
                f"XComponentOf(ThrottleOf({owner}));",
                f"MagnitudeOf({owner}.FlyDirection)>0.050",
                f"{owner}.FlyVelocityDelta=Normalize({owner}.FlyDirection)*5.500*{owner}.FlyPercent/100"
                f"*Min(1,MagnitudeOf(ThrottleOf({owner})))-VelocityOf({owner});",
                f"Else;{owner}.FlyVelocityDelta=VelocityOf({owner})*-1;End;",
                f"If(MagnitudeOf({owner}.FlyVelocityDelta)>0.010);",
                f"ApplyImpulse({owner},{owner}.FlyVelocityDelta,MagnitudeOf({owner}.FlyVelocityDelta),"
                "ToWorld,IncorporateContraryMotion);",
            ):
                self.assertIn(token, packed)
            self.assertEqual(packed.count("ApplyImpulse("), 1)
            self.assertNotIn("StartAccelerating(", packed)
            self.assertNotIn("StopAccelerating(", packed)
            self.assertNotIn("SetGravity(", packed)
            self.assertNotIn("MovementCollisionWith", packed)

    def test_fly_controller_runs_at_twenty_hz_after_luck(self) -> None:
        for source, _ in self.sources:
            scheduler = rule_with(source, "Call Subroutine(ProcessPlayerLuck);", "Call Subroutine(ProcessPlayerFlight);")
            self.assertLess(scheduler.index("Call Subroutine(ProcessPlayerLuck);"), scheduler.index("Call Subroutine(ProcessPlayerFlight);"))
            self.assertIn("0.050", scheduler)
            self.assertEqual(source.count("Call Subroutine(ProcessPlayerFlight);"), 1)

    def test_try_your_luck_acceleration_does_not_override_fly_direction(self) -> None:
        for source, global_name in self.sources:
            luck = subroutine(source, "ProcessPlayerLuck")
            branch_start = luck.rfind(f"Else If({global_name}.ActivePlayer.LuckEffect == 2);")
            branch_end = luck.index(f"Else If({global_name}.ActivePlayer.LuckEffect == 3);", branch_start)
            acceleration_branch = compact(luck[branch_start:branch_end])
            self.assertIn(f"SetMoveSpeed({global_name}.ActivePlayer,1000);", acceleration_branch)
            self.assertIn(
                f"StartAccelerating({global_name}.ActivePlayer,"
                f"FacingDirectionOf(EvaluateOnce({global_name}.ActivePlayer)),50,25,ToWorld,DirectionRateandMaxSpeed);",
                acceleration_branch,
            )
            self.assertNotIn(f"If({global_name}.ActivePlayer.FlyModeActive==False);", acceleration_branch)

            fly_physics = subroutine(source, "ApplyGhostFlyPhysics")
            fly_cycle = subroutine(source, "ProcessPlayerCycle")
            self.assertNotIn("Start Accelerating(", fly_physics)
            self.assertNotIn("Stop Accelerating(", fly_physics)
            self.assertNotIn("Start Accelerating(", fly_cycle)
            self.assertNotIn("Stop Accelerating(", fly_cycle)

            packed_luck = compact(luck)
            self.assertIn(
                f"If({global_name}.ActivePlayer.LuckEffect==2);"
                f"StopAccelerating({global_name}.ActivePlayer);"
                f"SetMoveSpeed({global_name}.ActivePlayer,100);End;",
                packed_luck,
            )

    def test_death_preserves_jump_latch_and_resurrect_reapplies_fly_physics(self) -> None:
        for source, _ in self.sources:
            death = rule_with(source, "Player Died", "Event Player.DeathPosition = Position Of(Event Player);")
            normalization = (
                "Stop Accelerating(Event Player);",
                "Set Move Speed(Event Player, 100);",
                "Set Gravity(Event Player, 100);",
                "Enable Movement Collision With Environment(Event Player);",
                "Event Player.GhostFlyPhysicsApplied = False;",
                "Event Player.FlyRampStartTime = -1;",
            )
            positions = [death.index(token) for token in normalization]
            self.assertEqual(positions, sorted(positions))
            resurrect = rule_with(source, "Resurrect(Event Player);", "Button(Jump)")
            recovery_teleport = "Teleport(Event Player, Event Player.SafeRevivePosition + Vector(0, 0.500, 0));"
            self.assertEqual(resurrect.count(recovery_teleport), 2)
            self.assertIn("Event Player.SafeRevivePosition = Nearest Walkable Position(Position Of(Event Player));", resurrect)
            self.assertNotIn("JumpReviveConsumed = False", death)
            self.assertNotIn("Nearest Walkable Position(Event Player.DeathPosition)", resurrect)
            self.assertNotIn("Call Subroutine(FindSafeTravelPosition);", resurrect)
            self.assertNotIn("Abort;", resurrect)
            self.assertNotIn("Spawn Points(Team Of(Event Player))", resurrect)
            self.assertLess(resurrect.index(recovery_teleport), resurrect.index("Resurrect(Event Player);"))
            self.assertLess(resurrect.index("Resurrect(Event Player);"), resurrect.rindex(recovery_teleport))
            self.assertLess(resurrect.rindex(recovery_teleport), resurrect.index("Event Player.GhostFlyPhysicsApplied = False;"))
            self.assertNotIn("Play Effect(", resurrect)
            self.assertLess(resurrect.index("Event Player.GhostFlyPhysicsApplied = False;"), resurrect.index("Call Subroutine(ApplyGhostFlyPhysics);"))
            self.assertNotIn("Small Message(", resurrect)
            self.assertNotIn("Resurrect unavailable", source)
            self.assertNotIn("Bangkit tidak tersedia", source)
            self.assertNotIn("ยังฟื้นไม่ได้", source)

    def test_fresh_setup_and_true_cleanup_restore_safe_defaults(self) -> None:
        for source, _ in self.sources:
            setup = subroutine(source, "PreparePlayer")
            for token in (
                "Event Player.GhostModeActive = False;",
                "Event Player.FlyModeActive = False;",
                "Event Player.GhostFlyCursor = 0;",
                "Event Player.GhostFlyPhysicsApplied = False;",
                "Event Player.FlyRampStartTime = -1;",
                "Event Player.FlyPercent = 100;",
                "Event Player.FlyDirection = Vector(0, 0, 0);",
                "Event Player.FlyVelocityDelta = Vector(0, 0, 0);",
            ):
                self.assertIn(token, setup)

            cleanup = subroutine(source, "QuiescePlayer")
            for token in (
                "Event Player.GhostModeActive = False;",
                "Event Player.FlyModeActive = False;",
                "Enable Movement Collision With Environment(Event Player);",
                "Set Gravity(Event Player, 100);",
                "Set Move Speed(Event Player, 100);",
                "Event Player.FlyRampStartTime = -1;",
                "Event Player.FlyPercent = 100;",
                "Event Player.FlyDirection = Vector(0, 0, 0);",
                "Event Player.FlyVelocityDelta = Vector(0, 0, 0);",
            ):
                self.assertIn(token, cleanup)

    def test_physics_reapplies_after_engine_and_lifecycle_resets(self) -> None:
        for source, global_name in self.sources:
            reapply = subroutine(source, "ProcessPlayerCycle")
            for token in (
                f"{global_name}.ActivePlayer.IsHuman == True",
                f"{global_name}.ActivePlayer.IsAutomaticBot == False",
                f"Is Dummy Bot({global_name}.ActivePlayer) == False",
                f"Has Spawned({global_name}.ActivePlayer) == True",
                f"Is Alive({global_name}.ActivePlayer) == True",
                f"{global_name}.ActivePlayer.GhostFlyPhysicsApplied == False",
                f"Set Move Speed({global_name}.ActivePlayer, {global_name}.ActivePlayer.FlyModeActive == True ? 0 : 100);",
            ):
                self.assertIn(token, reapply)

            fast = subroutine(source, "ProcessPlayerFastState")
            self.assertNotIn("Call Subroutine(QuiescePlayer);", fast)
            self.assertNotIn("Call Subroutine(CleanupPlayer);", fast)
            team_rule = rule_with(source, '01a - Team cycle: Quarantine before preparation')
            self.assertIn("Ongoing - Each Player;", team_rule)
            self.assertIn("Event Player.LastTeam != Team Of(Event Player)", team_rule)
            self.assertIn("Event Player.PlayerListUpdatePending = False;", team_rule)
            self.assertIn("Event Player.TeamChangeProcessed = True;", team_rule)
            self.assertIn("Event Player.PlayerCycleActive = True;", team_rule)
            self.assertIn("Event Player.IsPrepared = False;", team_rule)
            self.assertIn("Event Player.IsHuman = False;", team_rule)
            self.assertIn("Event Player.TeamCycleDeadline = Total Time Elapsed + 0.500;", team_rule)
            self.assertNotIn("Call Subroutine(QuiescePlayer);", team_rule)
            self.assertNotIn("Call Subroutine(CleanupPlayer);", team_rule)
            self.assertNotIn("Event Player.PlayerListUpdatePending = True;", team_rule)
            self.assertNotIn(f"{global_name}.ActivePlayer", team_rule)
            self.assertNotIn("Wait(", team_rule)
            setup_worker = rule_with(source, '01b - Team cycle: Preparation worker from the global scheduler')
            self.assertIn("Call Subroutine(QuiescePlayer);", setup_worker)
            self.assertIn("Call Subroutine(CleanupPlayer);", setup_worker)
            self.assertIn("Call Subroutine(PreparePlayer);", setup_worker)

            hero_change = reapply.index(
                f"Hero Of({global_name}.ActivePlayer) != {global_name}.ActivePlayer.LastHero"
            )
            hero_branch = reapply[hero_change:]
            self.assertIn(f"{global_name}.ActivePlayer.GhostFlyPhysicsApplied = False;", hero_branch)
            self.assertIn(f"{global_name}.ActivePlayer.FlyRampStartTime = -1;", hero_branch)
            self.assertIn(f"Set Move Speed({global_name}.ActivePlayer, 100);", hero_branch)

    def test_try_your_luck_never_owns_gravity_or_fly_throttle(self) -> None:
        for source, _ in self.sources:
            for owner_name in (
                "ApplyLuckPage",
                "ProcessPlayerLuck",
                "RestorePlayerLuck",
                "RestoreActivePlayerLuck",
            ):
                owner = subroutine(source, owner_name)
                for forbidden in (
                    "Set Gravity(",
                    "Start Transforming Throttle(",
                    "Stop Transforming Throttle(",
                ):
                    with self.subTest(owner=owner_name, forbidden=forbidden):
                        self.assertNotIn(forbidden, owner)
                for variable in (
                    "GhostModeActive",
                    "FlyModeActive",
                    "GhostFlyPhysicsApplied",
                ):
                    with self.subTest(owner=owner_name, variable=variable):
                        self.assertIsNone(re.search(rf"{variable}\s*=(?!=)", owner))

    def test_ghost_fly_rules_add_no_wait_or_loop(self) -> None:
        for source, _ in self.sources:
            feature_rules = [
                body
                for name, body in workshop_rules(source)
                if not name.startswith("04g -") and any(
                    token in body
                    for token in (
                        "DrawGhostFlyMenu",
                        "ApplyGhostFlyPage",
                        "ApplyGhostFlyPhysics",
                        "GhostFlyPhysicsApplied == False",
                        "FlyModeActive",  # includes the idle controller
                    )
                )
            ]
            self.assertTrue(feature_rules)
            for body in feature_rules:
                self.assertNotIn("Wait(", body)
                self.assertNotRegex(body, r"\bLoop(?: If Condition Is True)?;")


if __name__ == "__main__":
    unittest.main()
