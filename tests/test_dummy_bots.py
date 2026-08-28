from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DummyBotFeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.it = (ROOT / "workshop" / "ruang_irama.it-IT.workshop").read_text(encoding="utf-8")
        cls.en = (ROOT / "tests" / "fixtures" / "semantic_reference.txt").read_text(encoding="utf-8")

    def test_static_hud_uses_recyclable_roster_slots_without_embedded_label_spacing(self):
        for source, global_name in ((self.it, "Globale"), (self.en, "Global")):
            self.assertIn('Custom String("{0} [{1}]", Custom String("CHILL DEDICATED SERVER")', source)
            self.assertIn('"Hold {0}: inspect hero + HP"', source)
            self.assertIn('"Hold {0} 0.5s: Arcade Menu | {1} 0.5s: Camera"', source)
            self.assertIn("Input Binding String(Button(Crouch))", source)
            self.assertIn("Input Binding String(Button(Melee))", source)
            self.assertIn("Input Binding String(Button(Interact))", source)
            self.assertIn('"LOBBY & CHILL TIME"', source)
            self.assertIn('"PLAYER VIBES"', source)
            self.assertIn("10 + Count Of(Filtered Array(", source)
            self.assertIn("1 + Event Player.UrutanHUD", source)
            self.assertIn("-13 + Event Player.UrutanHUD", source)
            self.assertIn(f"{global_name}.SlotHUDTersedia = Sorted Array(Append To Array(", source)
            self.assertIn('Custom String("{0}{1}{2}"', source)
            self.assertNotIn(f"-99 + Evaluate Once({global_name}.IndeksPemilih)", source)
            self.assertNotIn("\\nLOBBY & CHILL TIME", source)
            self.assertNotIn("\\nPLAYER VIBES", source)
            self.assertNotIn(", Top, 100,", source)
            self.assertNotIn(", Top, -99,", source)

    def test_shared_dummy_creation_subroutine_is_single_and_safe(self):
        self.assertEqual(
            self.it.count("Create Dummy Bot(Tutti gli eroi, Globale.TimDummyAktif, -1, Position Of(First Of(Spawn Points(Globale.TimDummyAktif))), Vector(0, 0, 1));"),
            1,
        )
        self.assertEqual(
            self.en.count("Create Dummy Bot(All Heroes, Global.TimDummyAktif, -1, Position Of(First Of(Spawn Points(Global.TimDummyAktif))), Vector(0, 0, 1));"),
            1,
        )
        self.assertEqual(self.it.count("Call Subroutine(BuatDummyTim);"), 2)
        self.assertEqual(self.en.count("Call Subroutine(BuatDummyTim);"), 2)
        self.assertNotIn("Create Dummy Bot(Tutti gli eroi, Team 1, -1, Null, Null);", self.it)
        self.assertNotIn("Create Dummy Bot(Tutti gli eroi, Team 2, -1, Null, Null);", self.it)

    def test_runtime_team_literals_stay_english_in_it_clipboard(self):
        self.assertIn("Number Of Slots(Team 1)", self.it)
        self.assertIn("Number Of Slots(Team 2)", self.it)
        self.assertIn("All Players(Team 1)", self.it)
        self.assertIn("All Players(Team 2)", self.it)
        self.assertNotIn("Number Of Slots(Squadra 1)", self.it)
        self.assertNotIn("Number Of Slots(Squadra 2)", self.it)
        self.assertNotIn("All Players(Squadra 1)", self.it)
        self.assertNotIn("All Players(Squadra 2)", self.it)

    def test_dummy_respawn_is_3_seconds(self):
        for source in (self.it, self.en):
            self.assertIn("Set Respawn Max Time(Event Player, 3);", source)
            self.assertNotIn("Set Respawn Max Time(Event Player, 30);", source)

    def test_native_dummy_wall_phasing_remains_isolated_from_player_ghost_mode(self):
        action = "Disable Movement Collision With Environment(Event Player, False);"
        for source, rule_kw in ((self.it, "regola"), (self.en, "rule")):
            self.assertEqual(source.count(action), 2)
            self.assertNotIn("Disable Movement Collision With Environment(Event Player, True);", source)
            bot_rule = source.split(
                f'{rule_kw}("03c - Bot/Dummy: Kunci saat hidup kembali atau pahlawan berganti")', 1
            )[1].split(f'{rule_kw}("', 1)[0]
            self.assertEqual(bot_rule.count(action), 1)
            self.assertIn(
                "If(Is Dummy Bot(Event Player) == True);\n"
                "\t\t\tEnable Movement Collision With Players(Event Player);\n"
                f"\t\t\t{action}",
                bot_rule,
            )

    def test_dummy_reserves_the_last_human_slot_and_leaves_at_full_team(self):
        for team in ("Team 1", "Team 2"):
            self.assertIn(f"Number Of Players({team}) < Number Of Slots({team}) - 1;", self.it)
            self.assertIn(f"Number Of Players({team}) >= Number Of Slots({team});", self.it)
            self.assertIn(
                f"Count Of(Filtered Array(All Players({team}), Is Dummy Bot(Current Array Element) == True)) > 0;",
                self.it,
            )
        self.assertEqual(self.it.count("Call Subroutine(LepasDummyTim);"), 2)
        self.assertEqual(self.en.count("Call Subroutine(LepasDummyTim);"), 2)
        self.assertEqual(
            self.it.count("Destroy Dummy Bot(Globale.TimDummyAktif, Slot Of(First Of(Filtered Array(All Players(Globale.TimDummyAktif), Is Dummy Bot(Current Array Element) == True))));"),
            1,
        )

    def test_spawn_teleport_uses_safe_mode_specific_destinations(self):
        self.assertIn("Is In Spawn Room(Event Player) == True;", self.it)
        self.assertNotIn("Wait(1.000, Annulla quando è False);", self.it)
        self.assertIn("If(Event Player.WaktuTeleportasiDummy == 0);", self.it)
        self.assertIn(
            "Or(Event Player.WaktuTeleportasiDummy == 0, Total Time Elapsed >= Event Player.WaktuTeleportasiDummy) == True;",
            self.it,
        )
        self.assertIn("Event Player.WaktuTeleportasiDummy = Total Time Elapsed + 1;", self.it)
        self.assertIn("Event Player.WaktuTeleportasiDummy = 0;", self.it)
        self.assertIn("Direction Towards(Event Player.PosisiMati, Position Of(First Of(Spawn Points(Team Of(Event Player))))) * 10", self.it)
        self.assertIn("Distance Between(Event Player.PosisiBangkitAman, Event Player.PosisiMati) >= 6", self.it)
        self.assertIn("Current Game Mode == Game Mode(Trasporto)", self.it)
        self.assertIn("Current Game Mode == Game Mode(Ibrida)", self.it)
        self.assertIn("Current Game Mode == Game Mode(Cattura la Bandiera)", self.it)
        self.assertIn("Current Game Mode == Game Mode(Scorta)", self.it)
        self.assertIn("Payload Position", self.it)
        self.assertIn("Flag Position(Opposite Team Of(Team Of(Event Player)))", self.it)
        self.assertIn("Is On Objective(Current Array Element) == True", self.it)
        self.assertIn("Nearest Walkable Position", self.it)
        self.assertNotIn("All Players On Objective(All Teams)", self.it)
        self.assertNotIn("Teleport(Event Player, Objective Position(Objective Index));", self.it)
        self.assertIn("Event Player.PosisiBangkitAman = Vector(0, 0, 0);", self.it)
        self.assertIn("Ray Cast Hit Position(Event Player.PosisiBangkitAman + Vector(0, 5, 0)", self.it)
        self.assertIn("Distance Between(Event Player.PosisiBangkitAman, Vector(0, 0, 0)) > 0.100", self.it)
        self.assertIn("Teleport(Event Player, Event Player.PosisiBangkitAman);", self.it)
        dummy_rule = self.it.split('regola("03f - Bot/Dummy: Teleport dari ruang spawn ke objektif")', 1)[1].split('regola("03g -', 1)[0]
        self.assertIn("Event Player.PosisiTeleportTujuan = Event Player.PosisiBangkitAman;", dummy_rule)
        self.assertIn("Call Subroutine(CariPosisiTeleportAman);", dummy_rule)

    def test_dummy_receives_normal_damage(self):
        it_lock = self.it.split('regola("92 - Subrutin: Kunci bot/dummy, kaki tetap bisa bergerak")', 1)[1].split('regola("91o - Subrutin: Gambar menu pilihan pemain")', 1)[0]
        en_lock = self.en.split('rule("92 - Subrutin: Kunci bot/dummy, kaki tetap bisa bergerak")', 1)[1].split('rule("91o - Subrutin: Gambar menu pilihan pemain")', 1)[0]
        self.assertEqual(it_lock.count("Set Damage Received(Event Player, 100);"), 1)
        self.assertEqual(en_lock.count("Set Damage Received(Event Player, 100);"), 1)
        self.assertNotIn("Set Damage Received(Event Player, 0);", it_lock)
        self.assertNotIn("Set Damage Received(Event Player, 0);", en_lock)
        self.assertIn("Set Knockback Received(Event Player, 100);", it_lock)
        self.assertIn("Set Knockback Received(Event Player, 100);", en_lock)
        self.assertNotIn("Disable Movement Collision With Players", it_lock)
        self.assertNotIn("Disable Movement Collision With Players", en_lock)
        self.assertEqual(it_lock.count("Set Move Speed(Event Player, 20);"), 1)
        self.assertEqual(en_lock.count("Set Move Speed(Event Player, 20);"), 1)
        self.assertNotIn("Set Move Speed(Event Player, 0);", it_lock)
        self.assertNotIn("Set Move Speed(Event Player, 0);", en_lock)

    def test_dummy_faces_nearest_living_enemy_human_without_extra_loop(self):
        for source, global_name, rule_kw in ((self.it, "Globale", "regola"), (self.en, "Global", "rule")):
            movement = source.split(f'{rule_kw}("03g - Bot/Dummy: Hadap dan dekati manusia musuh hidup terdekat")', 1)[1].split(
                f'{rule_kw}("03h - Bot/Dummy: Hentikan gerak saat tidak ada manusia musuh hidup")', 1
            )[0]
            self.assertIn("Event Player.TargetDummyIkuti", movement)
            self.assertNotIn("Sorted Array(Filtered Array", movement)
            self.assertNotIn(f"Filtered Array({global_name}.PemainManusia", movement)
            self.assertIn("Direction and Turn Rate", movement)
            self.assertIn("Direction and Magnitude", movement)

            scheduler = source.split(f'{rule_kw}("89b - Subrutin: Proses siklus pemain 10 Hz")', 1)[1].split(
                f'{rule_kw}("89c - Subrutin: Proses simpanan pemain 1 Hz")', 1
            )[0]
            self.assertIn("TargetDummyIkuti", scheduler)
            self.assertIn(f"Filtered Array({global_name}.PemainManusia", scheduler)
            self.assertIn("IzinkanDummyMengikuti", scheduler)
            self.assertIn("Sorted Array", scheduler)
        self.assertEqual(self.it.count("Loop If Condition Is True;"), 1)

    def test_dummy_follow_page_defaults_off_and_is_per_player(self):
        for source in (self.it, self.en):
            self.assertIn(
                "Event Player.IzinkanDummyMengikuti = False;\n"
                "\t\tEvent Player.KursorIkutiDummy = 0;",
                source,
            )
            self.assertIn("Call Subroutine(TerapkanHalamanIkutiDummy);", source)
            self.assertIn("Call Subroutine(GambarIkutiDummy);", source)
            self.assertIn("12 - DUMMY FOLLOW", source)
            self.assertIn("12 - DUMMY MENGIKUTI", source)

    def test_native_dummy_walks_forward_automatically_and_stops_cleanly(self):
        for source, rule_kw in ((self.it, "regola"), (self.en, "rule")):
            self.assertEqual(source.count("Start Throttle In Direction(Event Player, Forward,"), 1)
            self.assertIn("Distance Between(Event Player, Event Player.TargetDummyIkuti) <= 4", source)
            self.assertEqual(source.count("Stop Throttle In Direction(Event Player);"), 2)
            self.assertEqual(source.count("Stop Throttle In Direction(First Of(Filtered Array("), 1)

            movement = source.split(f'{rule_kw}("03g - Bot/Dummy: Hadap dan dekati manusia musuh hidup terdekat")', 1)[1].split(
                f'{rule_kw}("03h - Bot/Dummy: Hentikan gerak saat tidak ada manusia musuh hidup")', 1
            )[0]
            self.assertIn("Is Dummy Bot(Event Player) == True;", movement)
            self.assertIn("TargetDummyIkuti", movement)
            self.assertNotIn("Wait(", movement)

            cleanup = source.split(f'{rule_kw}("03h - Bot/Dummy: Hentikan gerak saat tidak ada manusia musuh hidup")', 1)[1].split(
                f'{rule_kw}("03i - Bot/Dummy: Hentikan gerak saat bot mati")', 1
            )[0]
            self.assertIn("TargetDummyIkuti", cleanup)


if __name__ == "__main__":
    unittest.main()
