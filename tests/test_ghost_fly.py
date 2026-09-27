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
            "105: ModeHantuAktif",
            "106: ModeTerbangAktif",
            "107: KursorHantuTerbang",
            "108: FisikaHantuTerbangDiterapkan",
            "110: WaktuMulaiTerbangMaju",
            "111: PersenTerbang",
            "112: ArahTerbang",
            "113: DeltaTerbang",
            "57: GambarHantuTerbang",
            "58: TerapkanHalamanHantuTerbang",
            "59: TerapkanFisikaHantuTerbang",
            "60: ProsesTerbangPemain",
        )
        for source, _ in self.sources:
            for declaration in declarations:
                with self.subTest(declaration=declaration):
                    self.assertEqual(source.count(declaration), 1)

    def test_main_menu_has_fourteen_pages_and_routes_page_thirteen(self) -> None:
        localized_titles = (
            "13 - GHOST MODE / FLY",
            '13 - HANTU / TERBANG',
            "13 - โหมดผี / บิน",
        )
        localized_tails = (
            ("12 - DUMMY FOLLOW", "13 - GHOST MODE / FLY"),
            ('12 - BOT MENGIKUTI', '13 - HANTU / TERBANG'),
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
            dispatcher = rule_with(source, "Event Player.PerintahMenu == 1;", "TerapkanHalamanIkutiBotBuatan")
            self.assertRegex(
                compact(dispatcher),
                r"HalamanMenu==13\);CallSubroutine\(TerapkanHalamanHantuTerbang\);",
            )
            transition = subroutine(source, "TransisiWarnaMenu")
            self.assertIn("EventPlayer.HalamanMenu)==13);", compact(transition))
            self.assertIn("Vector(110,170,255)*0.320", compact(transition))
            for token in localized_titles:
                self.assertIn(token, source)

    def test_page_thirteen_renderer_has_two_independent_localized_rows(self) -> None:
        localized_words = (
            "GHOST MODE",
            "FLY",
                "HANTU",
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
                "Hold CROUCH",
                'Tahan JONGKOK',
                'ย่อค้าง',
            ):
                self.assertIn(instruction, renderer)
            for fly_hint in (
                "LOOK TO STEER | HOLD FORWARD: 100% > 1000% IN 25s",
                'ARAHKAN BIDIKAN | TAHAN MAJU: 100% > 1000% DALAM 25 dtk',
                'มองเพื่อเลี้ยว | เดินหน้าค้าง: 100% > 1000% ใน 25 วิ',
            ):
                self.assertIn(fly_hint, renderer)

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

    def test_fly_disables_native_locomotion_and_uses_zero_gravity(self) -> None:
        for source, _ in self.sources:
            physics = subroutine(source, "TerapkanFisikaHantuTerbang")
            packed = compact(physics)
            self.assertRegex(
                packed,
                r"If\(EventPlayer.ModeTerbangAktif==True\);"
                r"If\(Or\(EventPlayer\.EfekNasib!=2,EventPlayer\.EfekNasibBerakhir<=TotalTimeElapsed\)\);"
                r"SetMoveSpeed\(EventPlayer,0\);End;"
                r"SetGravity\(EventPlayer,0\);",
            )
            self.assertRegex(
                packed,
                r"Else;If\(Or\(EventPlayer\.EfekNasib!=2,EventPlayer\.EfekNasibBerakhir<=TotalTimeElapsed\)\);"
                r"SetMoveSpeed\(EventPlayer,100\);If\(MagnitudeOf\(VelocityOf\(EventPlayer\)\)>0.010\);"
                r"ApplyImpulse\(EventPlayer,VelocityOf\(EventPlayer\)\*-1,MagnitudeOf\(VelocityOf\(EventPlayer\)\),"
                r"ToWorld,IncorporateContraryMotion\);End;End;SetGravity\(EventPlayer,100\);",
            )
            self.assertIn("EventPlayer.FisikaHantuTerbangDiterapkan=True;", packed)
            self.assertNotIn("Start Accelerating(", physics)
            self.assertNotIn("Stop Accelerating(", physics)
            self.assertNotIn("Movement Collision With Players", physics)
            self.assertNotIn("Start Transforming Throttle(", source)
            self.assertIn("EventPlayer.WaktuMulaiTerbangMaju=-1;", packed)

    def test_only_pure_forward_builds_the_per_player_speed_ramp(self) -> None:
        for source, global_name in self.sources:
            packed = compact(subroutine(source, "ProsesTerbangPemain"))
            owner = f"{global_name}.PemainAktif"
            luck = (
                f"If(And({owner}.EfekNasib==2,{owner}.EfekNasibBerakhir>TotalTimeElapsed));"
            )
            pure_forward = (
                f"If(And(ZComponentOf(ThrottleOf({owner}))>0.050,"
                f"And(XComponentOf(ThrottleOf({owner}))>=-0.050,"
                f"XComponentOf(ThrottleOf({owner}))<=0.050)));"
            )
            timestamp_start = (
                f"If({owner}.WaktuMulaiTerbangMaju<0);"
                f"{owner}.WaktuMulaiTerbangMaju=TotalTimeElapsed;End;"
            )
            speed_formula = (
                f"{owner}.PersenTerbang=Min(1000,100+Max(0,TotalTimeElapsed-"
                f"{owner}.WaktuMulaiTerbangMaju)*36);"
            )
            reset = (
                "Else;"
                f"{owner}.WaktuMulaiTerbangMaju=-1;"
                f"{owner}.PersenTerbang=100;End;"
            )

            for token in (luck, pure_forward, timestamp_start, speed_formula, reset):
                self.assertIn(token, packed)
            self.assertLess(packed.index(luck), packed.index(pure_forward))
            self.assertLess(packed.index(pure_forward), packed.index(reset))
            self.assertNotIn("DotProduct(ThrottleOf(", packed)
            self.assertNotIn("StartAccelerating(", packed)
            self.assertNotIn("StopAccelerating(", packed)
            self.assertNotIn(f"{global_name}.WaktuMulaiTerbangMaju", source)
            cycle = subroutine(source, "ProsesSiklusPemain")
            self.assertNotIn("Min(1000, 100 +", cycle)

    def test_side_back_diagonal_and_release_all_take_the_reset_branch(self) -> None:
        """The sole ramp branch is pure Forward; every other Fly throttle resets it."""
        for source, global_name in self.sources:
            packed = compact(subroutine(source, "ProsesTerbangPemain"))
            owner = f"{global_name}.PemainAktif"
            forward = packed.index(
                f"ZComponentOf(ThrottleOf({owner}))>0.050"
            )
            lower_x = packed.index(
                f"XComponentOf(ThrottleOf({owner}))>=-0.050",
                forward,
            )
            upper_x = packed.index(
                f"XComponentOf(ThrottleOf({owner}))<=0.050",
                lower_x,
            )
            reset = packed.index(
                f"Else;{owner}.WaktuMulaiTerbangMaju=-1;",
                upper_x,
            )
            self.assertLess(forward, lower_x)
            self.assertLess(lower_x, upper_x)
            self.assertLess(upper_x, reset)
            reset_branch = packed[reset : packed.index("End;", reset) + len("End;")]
            self.assertEqual(reset_branch.count(f"{owner}.WaktuMulaiTerbangMaju=-1;"), 1)
            self.assertEqual(reset_branch.count(f"{owner}.PersenTerbang=100;"), 1)

    def test_fly_3d_controller_applies_only_the_velocity_difference(self) -> None:
        for source, global_name in self.sources:
            owner = f"{global_name}.PemainAktif"
            packed = compact(subroutine(source, "ProsesTerbangPemain"))
            for token in (
                f"{owner}.Manusia==True",
                f"{owner}.BotOtomatis==False",
                f"IsDummyBot({owner})==False",
                f"HasSpawned({owner})==True",
                f"IsAlive({owner})==True",
                f"{owner}.ModeTerbangAktif==True",
                f"{owner}.FisikaHantuTerbangDiterapkan==True",
                f"{owner}.ArahTerbang=FacingDirectionOf({owner})*Max(0,ZComponentOf(ThrottleOf({owner})))"
                f"+DirectionFromAngles(HorizontalFacingAngleOf({owner}),0)*Min(0,ZComponentOf(ThrottleOf({owner})))"
                f"+CrossProduct(Vector(0,1,0),DirectionFromAngles(HorizontalFacingAngleOf({owner}),0))*"
                f"XComponentOf(ThrottleOf({owner}));",
                f"MagnitudeOf({owner}.ArahTerbang)>0.050",
                f"{owner}.DeltaTerbang=Normalize({owner}.ArahTerbang)*5.500*{owner}.PersenTerbang/100"
                f"*Min(1,MagnitudeOf(ThrottleOf({owner})))-VelocityOf({owner});",
                f"Else;{owner}.DeltaTerbang=VelocityOf({owner})*-1;End;",
                f"If(MagnitudeOf({owner}.DeltaTerbang)>0.010);",
                f"ApplyImpulse({owner},{owner}.DeltaTerbang,MagnitudeOf({owner}.DeltaTerbang),"
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
            scheduler = rule_with(source, "Call Subroutine(ProsesNasibPemain);", "Call Subroutine(ProsesTerbangPemain);")
            self.assertLess(scheduler.index("Call Subroutine(ProsesNasibPemain);"), scheduler.index("Call Subroutine(ProsesTerbangPemain);"))
            self.assertIn("0.050", scheduler)
            self.assertEqual(source.count("Call Subroutine(ProsesTerbangPemain);"), 1)

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

            fly_physics = subroutine(source, "TerapkanFisikaHantuTerbang")
            fly_cycle = subroutine(source, "ProsesSiklusPemain")
            self.assertNotIn("Start Accelerating(", fly_physics)
            self.assertNotIn("Stop Accelerating(", fly_physics)
            self.assertNotIn("Start Accelerating(", fly_cycle)
            self.assertNotIn("Stop Accelerating(", fly_cycle)

            packed_luck = compact(luck)
            self.assertIn(
                f"If({global_name}.PemainAktif.EfekNasib==2);"
                f"StopAccelerating({global_name}.PemainAktif);"
                f"SetMoveSpeed({global_name}.PemainAktif,100);End;",
                packed_luck,
            )

    def test_death_preserves_jump_latch_and_resurrect_reapplies_fly_physics(self) -> None:
        for source, _ in self.sources:
            death = rule_with(source, "Player Died", "Event Player.PosisiMati = Position Of(Event Player);")
            normalization = (
                "Stop Accelerating(Event Player);",
                "Set Move Speed(Event Player, 100);",
                "Set Gravity(Event Player, 100);",
                "Enable Movement Collision With Environment(Event Player);",
                "Event Player.FisikaHantuTerbangDiterapkan = False;",
                "Event Player.WaktuMulaiTerbangMaju = -1;",
            )
            positions = [death.index(token) for token in normalization]
            self.assertEqual(positions, sorted(positions))
            resurrect = rule_with(source, "Resurrect(Event Player);", "Button(Jump)")
            recovery_teleport = "Teleport(Event Player, Event Player.PosisiBangkitAman + Vector(0, 0.500, 0));"
            self.assertEqual(resurrect.count(recovery_teleport), 2)
            self.assertIn("Event Player.PosisiBangkitAman = Nearest Walkable Position(Position Of(Event Player));", resurrect)
            self.assertNotIn("BangkitLompatDipakai = False", death)
            self.assertNotIn("Nearest Walkable Position(Event Player.PosisiMati)", resurrect)
            self.assertNotIn("Call Subroutine(CariPosisiTeleportasiAman);", resurrect)
            self.assertNotIn("Abort;", resurrect)
            self.assertNotIn("Spawn Points(Team Of(Event Player))", resurrect)
            self.assertLess(resurrect.index(recovery_teleport), resurrect.index("Resurrect(Event Player);"))
            self.assertLess(resurrect.index("Resurrect(Event Player);"), resurrect.rindex(recovery_teleport))
            self.assertLess(resurrect.rindex(recovery_teleport), resurrect.index("Call Subroutine(EfekTerapkan);"))
            self.assertLess(resurrect.index("Call Subroutine(EfekTerapkan);"), resurrect.index("Event Player.FisikaHantuTerbangDiterapkan = False;"))
            self.assertLess(resurrect.index("Event Player.FisikaHantuTerbangDiterapkan = False;"), resurrect.index("Call Subroutine(TerapkanFisikaHantuTerbang);"))
            self.assertNotIn("Small Message(", resurrect)
            self.assertNotIn("Resurrect unavailable", source)
            self.assertNotIn("Bangkit tidak tersedia", source)
            self.assertNotIn("ยังฟื้นไม่ได้", source)

    def test_fresh_setup_and_true_cleanup_restore_safe_defaults(self) -> None:
        for source, _ in self.sources:
            setup = subroutine(source, "SiapkanPemain")
            for token in (
                "Event Player.ModeHantuAktif = False;",
                "Event Player.ModeTerbangAktif = False;",
                "Event Player.KursorHantuTerbang = 0;",
                "Event Player.FisikaHantuTerbangDiterapkan = False;",
                "Event Player.WaktuMulaiTerbangMaju = -1;",
                "Event Player.PersenTerbang = 100;",
                "Event Player.ArahTerbang = Vector(0, 0, 0);",
                "Event Player.DeltaTerbang = Vector(0, 0, 0);",
            ):
                self.assertIn(token, setup)

            cleanup = subroutine(source, "TenangkanPemain")
            for token in (
                "Event Player.ModeHantuAktif = False;",
                "Event Player.ModeTerbangAktif = False;",
                "Enable Movement Collision With Environment(Event Player);",
                "Set Gravity(Event Player, 100);",
                "Set Move Speed(Event Player, 100);",
                "Event Player.WaktuMulaiTerbangMaju = -1;",
                "Event Player.PersenTerbang = 100;",
                "Event Player.ArahTerbang = Vector(0, 0, 0);",
                "Event Player.DeltaTerbang = Vector(0, 0, 0);",
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
                f"Set Move Speed({global_name}.PemainAktif, {global_name}.PemainAktif.ModeTerbangAktif == True ? 0 : 100);",
            ):
                self.assertIn(token, reapply)

            fast = subroutine(source, "ProsesCepatPemain")
            self.assertNotIn("Call Subroutine(TenangkanPemain);", fast)
            self.assertNotIn("Call Subroutine(BersihkanPemain);", fast)
            team_rule = rule_with(source, '01a - Siklus tim: Karantina sebelum penyiapan ulang')
            self.assertIn("Ongoing - Each Player;", team_rule)
            self.assertIn("Event Player.TimTerakhir != Team Of(Event Player)", team_rule)
            self.assertIn("Event Player.PembaruanDaftarTertunda = False;", team_rule)
            self.assertIn("Event Player.PindahTimDiproses = True;", team_rule)
            self.assertIn("Event Player.SiklusPemainAktif = True;", team_rule)
            self.assertIn("Event Player.SudahSiap = False;", team_rule)
            self.assertIn("Event Player.Manusia = False;", team_rule)
            self.assertIn("Event Player.WaktuSiklusTim = Total Time Elapsed + 0.500;", team_rule)
            self.assertNotIn("Call Subroutine(TenangkanPemain);", team_rule)
            self.assertNotIn("Call Subroutine(BersihkanPemain);", team_rule)
            self.assertNotIn("Event Player.PembaruanDaftarTertunda = True;", team_rule)
            self.assertNotIn(f"{global_name}.PemainAktif", team_rule)
            self.assertNotIn("Wait(", team_rule)
            setup_worker = rule_with(source, '01b - Siklus tim: Pekerja penyiapan dari penjadwal global')
            self.assertIn("Call Subroutine(TenangkanPemain);", setup_worker)
            self.assertIn("Call Subroutine(BersihkanPemain);", setup_worker)
            self.assertIn("Call Subroutine(SiapkanPemain);", setup_worker)

            hero_change = reapply.index(
                f"Hero Of({global_name}.PemainAktif) != {global_name}.PemainAktif.PahlawanTerakhir"
            )
            hero_branch = reapply[hero_change:]
            self.assertIn(f"{global_name}.PemainAktif.FisikaHantuTerbangDiterapkan = False;", hero_branch)
            self.assertIn(f"{global_name}.PemainAktif.WaktuMulaiTerbangMaju = -1;", hero_branch)
            self.assertIn(f"Set Move Speed({global_name}.PemainAktif, 100);", hero_branch)

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
