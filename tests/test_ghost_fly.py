from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def workshop_rules(source: str) -> list[tuple[str, str]]:
    headers = list(re.finditer(r'(?m)^(?:rule|regola)\("([^"]+)"\)\s*\{', source))
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
        cls.it = (ROOT / "workshop" / "ruang_irama.it-IT.workshop").read_text(encoding="utf-8")
        cls.en = (ROOT / "tests" / "fixtures" / "semantic_reference.txt").read_text(encoding="utf-8")
        cls.sources = (
            (cls.it, "Globale"),
            (cls.en, "Global"),
        )

    def test_page_thirteen_state_and_subroutines_are_declared_contiguously(self) -> None:
        declarations = (
            "108: ModeHantuAktif",
            "109: ModeTerbangAktif",
            "110: KursorHantuTerbang",
            "111: FisikaHantuTerbangDiterapkan",
            "58: GambarHantuTerbang",
            "59: TerapkanHalamanHantuTerbang",
            "60: TerapkanFisikaHantuTerbang",
        )
        for source, _ in self.sources:
            for declaration in declarations:
                with self.subTest(declaration=declaration):
                    self.assertEqual(source.count(declaration), 1)

    def test_main_menu_has_fourteen_pages_and_routes_page_thirteen(self) -> None:
        localized_opening = (
            "Fourteen extremely important decisions",
            "Empat belas keputusan",
            "มีสิบสี่ตัวเลือก",
        )
        localized_titles = (
            "13 - GHOST MODE / FLY",
            "13 - MODE HANTU / TERBANG",
            "13 - โหมดผี / บิน",
        )
        localized_tails = (
            ("12 - DUMMY FOLLOW", "13 - GHOST MODE / FLY"),
            ("12 - DUMMY MENGIKUTI", "13 - MODE HANTU / TERBANG"),
            ("12 - ดัมมี่ติดตาม", "13 - โหมดผี / บิน"),
        )
        for source, _ in self.sources:
            navigation = rule_with(source, "KursorUtama = (Event Player.KursorUtama", "PerintahMenu == 3")
            self.assertIn(
                "Event Player.KursorUtama = (Event Player.KursorUtama + "
                "(Event Player.PerintahMenu == 3 ? 1 : 13)) % 14;",
                navigation,
            )
            router = subroutine(source, "GambarHalamanAktif")
            packed_router = compact(router)
            self.assertIn(
                "If(EventPlayer.HalamanMenu==-1);CallSubroutine(GambarUtama);ElseIf(EventPlayer.HalamanMenu==0);",
                packed_router,
            )
            self.assertNotIn("If(EventPlayer.KursorUtama==13);", packed_router)
            self.assertEqual(router.count("Call Subroutine(GambarHantuTerbang);"), 1)
            self.assertRegex(
                packed_router,
                r"HalamanMenu==13\);CallSubroutine\(GambarHantuTerbang\);",
            )
            main = subroutine(source, "GambarUtama")
            for page_twelve, page_thirteen in localized_tails:
                with self.subTest(page_twelve=page_twelve):
                    self.assertIn(
                        f'Event Player.KursorUtama == 12 ? Custom String("{page_twelve}',
                        main,
                    )
                    self.assertEqual(main.count(page_thirteen), 1)
            self.assertEqual(main.count("Event Player.ModeHantuAktif"), 3)
            self.assertEqual(main.count("Event Player.ModeTerbangAktif"), 3)
            dispatcher = rule_with(source, "Event Player.PerintahMenu == 1;", "TerapkanHalamanIkutiDummy")
            self.assertRegex(
                compact(dispatcher),
                r"HalamanMenu==13\);CallSubroutine\(TerapkanHalamanHantuTerbang\);",
            )
            transition = subroutine(source, "TransisiWarnaMenu")
            self.assertIn("EventPlayer.HalamanMenu)==13);", compact(transition))
            self.assertIn("Vector(110,170,255)*0.320", compact(transition))
            for token in localized_opening + localized_titles:
                self.assertIn(token, source)
            for legacy in (
                "Thirteen extremely important decisions",
                "Tiga belas keputusan",
                "มีสิบสามตัวเลือก",
            ):
                self.assertNotIn(legacy, source)

    def test_page_thirteen_renderer_has_two_independent_localized_rows(self) -> None:
        localized_words = (
            "GHOST MODE",
            "FLY",
            "MODE HANTU",
            "TERBANG",
            "โหมดผี",
            "บิน",
        )
        for source, _ in self.sources:
            renderer = subroutine(source, "GambarHantuTerbang")
            self.assertEqual(renderer.count("Create HUD Text("), 1)
            self.assertIn("Event Player.KursorHantuTerbang", renderer)
            self.assertIn("Event Player.ModeHantuAktif", renderer)
            self.assertIn("Event Player.ModeTerbangAktif", renderer)
            self.assertIn("/2", renderer)
            for token in localized_words:
                self.assertIn(token, renderer)
            for instruction in (
                "Hold CROUCH + command",
                "Tahan JONGKOK + perintah",
                "กด ย่อ + คำสั่ง",
            ):
                self.assertIn(instruction, renderer)

    def test_page_thirteen_navigation_selects_exactly_two_rows(self) -> None:
        for source, _ in self.sources:
            navigation = rule_with(source, "KursorUtama = (Event Player.KursorUtama", "KursorHantuTerbang")
            self.assertRegex(
                compact(navigation),
                r"HalamanMenu==13\);EventPlayer.KursorHantuTerbang="
                r"\(EventPlayer.KursorHantuTerbang\+1\)%2;",
            )

    def test_apply_toggles_only_the_selected_feature_and_rearms_physics(self) -> None:
        toggle_patterns = {
            "ModeHantuAktif": re.compile(
                r"EventPlayer\.ModeHantuAktif="
                r"(?:EventPlayer\.ModeHantuAktif==False|Not\(EventPlayer\.ModeHantuAktif\)|!EventPlayer\.ModeHantuAktif);"
            ),
            "ModeTerbangAktif": re.compile(
                r"EventPlayer\.ModeTerbangAktif="
                r"(?:EventPlayer\.ModeTerbangAktif==False|Not\(EventPlayer\.ModeTerbangAktif\)|!EventPlayer\.ModeTerbangAktif);"
            ),
        }
        for source, _ in self.sources:
            apply = subroutine(source, "TerapkanHalamanHantuTerbang")
            packed = compact(apply)
            cursor = packed.index("If(EventPlayer.KursorHantuTerbang==0);")
            fly_toggle = packed.index("EventPlayer.ModeTerbangAktif=", cursor)
            rearm = packed.index("EventPlayer.FisikaHantuTerbangDiterapkan=False;", fly_toggle)
            wall_branch = packed[cursor:fly_toggle]
            fly_branch = packed[fly_toggle:rearm]
            self.assertRegex(wall_branch, toggle_patterns["ModeHantuAktif"])
            self.assertNotRegex(wall_branch, r"ModeTerbangAktif=(?!=)")
            self.assertRegex(fly_branch, toggle_patterns["ModeTerbangAktif"])
            self.assertNotRegex(fly_branch, r"ModeHantuAktif=(?!=)")
            self.assertIn("EventPlayer.FisikaHantuTerbangDiterapkan=False;", packed)
            self.assertIn("CallSubroutine(TerapkanFisikaHantuTerbang);", packed)

    def test_wall_ghost_disables_only_walls_and_never_player_collision(self) -> None:
        for source, _ in self.sources:
            physics = subroutine(source, "TerapkanFisikaHantuTerbang")
            packed = compact(physics)
            self.assertRegex(
                packed,
                r"If\(EventPlayer.ModeHantuAktif==True\);"
                r"DisableMovementCollisionWithEnvironment\(EventPlayer,False\);"
                r"Else;EnableMovementCollisionWithEnvironment\(EventPlayer\);",
            )
            self.assertNotIn("Disable Movement Collision With Environment(Event Player, True);", source)
            self.assertNotIn("Movement Collision With Players", physics)

    def test_fly_uses_zero_gravity_and_transforms_throttle_along_the_view(self) -> None:
        for source, _ in self.sources:
            physics = subroutine(source, "TerapkanFisikaHantuTerbang")
            packed = compact(physics)
            self.assertRegex(
                packed,
                r"If\(EventPlayer.ModeTerbangAktif==True\);"
                r"SetGravity\(EventPlayer,0\);"
                r"StartTransformingThrottle\(EventPlayer,1,1,FacingDirectionOf\(EventPlayer\)\);",
            )
            self.assertRegex(
                packed,
                r"Else;If\(Or\(EventPlayer\.EfekNasib!=2,EventPlayer\.EfekNasibBerakhir<=TotalTimeElapsed\)\);"
                r"StopAccelerating\(EventPlayer\);End;StopTransformingThrottle\(EventPlayer\);SetGravity\(EventPlayer,100\);",
            )
            self.assertIn("EventPlayer.FisikaHantuTerbangDiterapkan=True;", packed)
            self.assertNotIn("Start Accelerating(", physics)
            self.assertNotIn("Movement Collision With Players", physics)

    def test_fly_forward_input_accelerates_gradually_along_the_full_view(self) -> None:
        for source, global_name in self.sources:
            packed = compact(subroutine(source, "ProsesSiklusPemain"))
            self.assertIn(f"(ZComponentOf(ThrottleOf({global_name}.PemainAktif)))>0.050", packed)
            self.assertIn(
                f"StartAccelerating({global_name}.PemainAktif,FacingDirectionOf({global_name}.PemainAktif),6,20,ToWorld,DirectionRateandMaxSpeed);",
                packed,
            )
            self.assertIn(
                f"Or({global_name}.PemainAktif.EfekNasib!=2,{global_name}.PemainAktif.EfekNasibBerakhir<=TotalTimeElapsed)",
                packed,
            )
            self.assertNotIn(f"FacingDirectionOf({global_name}.PemainAktif)*-1", packed)

    def test_fly_idle_cancels_velocity_with_an_exact_opposite_impulse(self) -> None:
        for source, global_name in self.sources:
            owner = rf"{global_name}\.PemainAktif"
            opposite_velocity = re.compile(
                rf"ApplyImpulse\({owner},VelocityOf\({owner}\)\*-1,"
                rf"MagnitudeOf\(VelocityOf\({owner}\)\),ToWorld,IncorporateContraryMotion\);"
            )
            idle = subroutine(source, "ProsesSiklusPemain")
            packed = compact(idle)
            self.assertIn(f"{global_name}.PemainAktif.Manusia==True", packed)
            self.assertIn(f"{global_name}.PemainAktif.BotOtomatis==False", packed)
            self.assertIn(f"IsDummyBot({global_name}.PemainAktif)==False", packed)
            self.assertRegex(
                packed,
                rf"MagnitudeOf\(ThrottleOf\({owner}\)\)<=0\.050",
            )
            self.assertIn(
                f"Or({global_name}.PemainAktif.EfekNasib!=2,"
                f"{global_name}.PemainAktif.EfekNasibBerakhir<=TotalTimeElapsed)",
                packed,
            )
            self.assertRegex(packed, opposite_velocity)
            idle_branch = packed[packed.index(f"MagnitudeOf(ThrottleOf({global_name}.PemainAktif))<=0.050") :]
            self.assertNotIn("FacingDirectionOf", idle_branch.split("End;", 1)[0])
            self.assertNotIn("MovementCollisionWithPlayers", idle_branch.split("End;", 1)[0])

    def test_try_your_luck_acceleration_does_not_override_fly_direction(self) -> None:
        for source, global_name in self.sources:
            luck = subroutine(source, "ProsesNasibPemain")
            branch_start = luck.rfind(f"Else If({global_name}.PemainAktif.EfekNasib == 2);")
            branch_end = luck.index(f"Else If({global_name}.PemainAktif.EfekNasib == 3);", branch_start)
            acceleration_branch = compact(luck[branch_start:branch_end])
            self.assertIn(f"SetMoveSpeed({global_name}.PemainAktif,1000);", acceleration_branch)
            self.assertIn(
                f"StartAccelerating({global_name}.PemainAktif,"
                f"FacingDirectionOf(EvaluateOnce({global_name}.PemainAktif)),50,25,ToWorld,DirectionRateandMaxSpeed);",
                acceleration_branch,
            )
            self.assertNotIn(f"If({global_name}.PemainAktif.ModeTerbangAktif==False);", acceleration_branch)

    def test_death_rearms_and_jump_resurrect_reapplies_fly_physics(self) -> None:
        for source, _ in self.sources:
            death = rule_with(source, "Player Died", "Event Player.PosisiMati = Position Of(Event Player);")
            self.assertIn("Event Player.FisikaHantuTerbangDiterapkan = False;", death)
            self.assertIn("Stop Accelerating(Event Player);", death)
            resurrect = rule_with(source, "Resurrect(Event Player);", "Button(Jump)")
            self.assertIn("Event Player.PosisiTeleportTujuan = Nearest Walkable Position(Event Player.PosisiMati);", resurrect)
            self.assertNotIn("Spawn Points(Team Of(Event Player))", resurrect)
            self.assertLess(resurrect.index("Call Subroutine(EfekPulihkan);"), resurrect.index("Event Player.FisikaHantuTerbangDiterapkan = False;"))
            self.assertLess(resurrect.index("Event Player.FisikaHantuTerbangDiterapkan = False;"), resurrect.index("Call Subroutine(TerapkanFisikaHantuTerbang);"))

    def test_fresh_setup_and_true_cleanup_restore_safe_defaults(self) -> None:
        for source, _ in self.sources:
            setup = subroutine(source, "SiapkanPemain")
            for token in (
                "Event Player.ModeHantuAktif = False;",
                "Event Player.ModeTerbangAktif = False;",
                "Event Player.KursorHantuTerbang = 0;",
                "Event Player.FisikaHantuTerbangDiterapkan = False;",
            ):
                self.assertIn(token, setup)

            cleanup = subroutine(source, "TenangkanPemain")
            for token in (
                "Event Player.ModeHantuAktif = False;",
                "Event Player.ModeTerbangAktif = False;",
                "Stop Transforming Throttle(Event Player);",
                "Enable Movement Collision With Environment(Event Player);",
                "Set Gravity(Event Player, 100);",
            ):
                self.assertIn(token, cleanup)

    def test_physics_reapplies_after_engine_and_lifecycle_resets(self) -> None:
        for source, global_name in self.sources:
            reapply = subroutine(source, "ProsesSiklusPemain")
            for token in (
                f"{global_name}.PemainAktif.Manusia == True",
                f"{global_name}.PemainAktif.BotOtomatis == False",
                f"Is Dummy Bot({global_name}.PemainAktif) == False",
                f"Has Spawned({global_name}.PemainAktif) == True",
                f"Is Alive({global_name}.PemainAktif) == True",
                f"{global_name}.PemainAktif.FisikaHantuTerbangDiterapkan == False",
                f"Start Transforming Throttle({global_name}.PemainAktif, 1, 1, Facing Direction Of({global_name}.PemainAktif));",
            ):
                self.assertIn(token, reapply)

            fast = subroutine(source, "ProsesCepatPemain")
            self.assertIn(f"{global_name}.PemainAktif.FisikaHantuTerbangDiterapkan = False;", fast)
            team_change = fast.index(f"{global_name}.PemainAktif.TimTerakhir != Team Of({global_name}.PemainAktif)")
            next_pending = fast.index(f"{global_name}.PemainAktif.SegarkanRosterTertunda == True", team_change)
            team_branch = fast[team_change:next_pending]
            self.assertNotIn(f"{global_name}.PemainAktif.ModeHantuAktif = False;", team_branch)
            self.assertNotIn(f"{global_name}.PemainAktif.ModeTerbangAktif = False;", team_branch)

    def test_try_your_luck_never_owns_gravity_or_fly_throttle(self) -> None:
        for source, _ in self.sources:
            for owner_name in (
                "TerapkanHalamanNasib",
                "ProsesNasibPemain",
                "PulihkanNasibPemain",
                "PulihkanNasibAktif",
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
                    "ModeHantuAktif",
                    "ModeTerbangAktif",
                    "FisikaHantuTerbangDiterapkan",
                ):
                    with self.subTest(owner=owner_name, variable=variable):
                        self.assertIsNone(re.search(rf"{variable}\s*=(?!=)", owner))

    def test_ghost_fly_rules_add_no_wait_or_loop(self) -> None:
        for source, _ in self.sources:
            feature_rules = [
                body
                for _, body in workshop_rules(source)
                if any(
                    token in body
                    for token in (
                        "GambarHantuTerbang",
                        "TerapkanHalamanHantuTerbang",
                        "TerapkanFisikaHantuTerbang",
                        "FisikaHantuTerbangDiterapkan == False",
                        "ModeTerbangAktif",  # includes the idle controller
                    )
                )
            ]
            self.assertTrue(feature_rules)
            for body in feature_rules:
                self.assertNotIn("Wait(", body)
                self.assertNotRegex(body, r"\bLoop(?: If Condition Is True)?;")


if __name__ == "__main__":
    unittest.main()
