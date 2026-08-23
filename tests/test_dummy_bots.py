from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DummyBotFeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.it = (ROOT / "workshop" / "ruang_irama.it-IT.workshop").read_text(encoding="utf-8")
        cls.en = (ROOT / "tests" / "fixtures" / "semantic_reference.txt").read_text(encoding="utf-8")

    def test_static_hud_uses_the_reference_grid_without_embedded_label_spacing(self):
        for source in (self.it, self.en):
            self.assertIn('Custom String("{0} [{1}]", Custom String("CHILL DEDICATED SERVER")', source)
            self.assertIn('"HOLD {0}:"', source)
            self.assertIn('"HOLD {0} 0.5 SEC"', source)
            self.assertIn("Input Binding String(Button(Crouch))", source)
            self.assertIn("Input Binding String(Button(Melee))", source)
            self.assertIn('"LOBBY TIME"', source)
            self.assertIn('"PLAYER VIBES"', source)
            self.assertIn("9 + Count Of(Filtered Array(", source)
            self.assertIn("1 + Event Player.UrutanHUD", source)
            self.assertNotIn("-99 + Event Player.UrutanHUD", source)
            self.assertNotIn("\\nLOBBY & CHILL TIME", source)
            self.assertNotIn("\\nPLAYER VIBES", source)
            self.assertNotIn(", Top, 100,", source)
            self.assertNotIn(", Top, -99,", source)

    def test_exactly_one_creation_rule_per_team(self):
        self.assertEqual(self.it.count("Create Dummy Bot(Tutti gli eroi, Team 1, -1, Position Of(First Of(Spawn Points(Team 1))), Vector(0, 0, 1));"), 1)
        self.assertEqual(self.it.count("Create Dummy Bot(Tutti gli eroi, Team 2, -1, Position Of(First Of(Spawn Points(Team 2))), Vector(0, 0, 1));"), 1)
        self.assertEqual(self.en.count("Create Dummy Bot(All Heroes, Team 1, -1, Position Of(First Of(Spawn Points(Team 1))), Vector(0, 0, 1));"), 1)
        self.assertEqual(self.en.count("Create Dummy Bot(All Heroes, Team 2, -1, Position Of(First Of(Spawn Points(Team 2))), Vector(0, 0, 1));"), 1)
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

    def test_dummy_respawn_is_30_seconds(self):
        self.assertIn("Set Respawn Max Time(Event Player, 30);", self.it)

    def test_dummy_reserves_the_last_human_slot_and_leaves_at_full_team(self):
        for team in ("Team 1", "Team 2"):
            self.assertIn(f"Number Of Players({team}) < Number Of Slots({team}) - 1;", self.it)
            self.assertIn(f"Number Of Players({team}) >= Number Of Slots({team});", self.it)
            self.assertEqual(self.it.count(f"Destroy Dummy Bot({team}, Slot Of("), 1)
            self.assertIn(
                f"Count Of(Filtered Array(All Players({team}), Is Dummy Bot(Current Array Element) == True)) > 0;",
                self.it,
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

    def test_dummy_receives_normal_damage(self):
        it_lock = self.it.split('regola("92 - Subrutin: Kunci bot/dummy, kaki tetap bisa bergerak")', 1)[1].split('regola("91o - Subrutin: Gambar menu pilihan pemain")', 1)[0]
        en_lock = self.en.split('rule("92 - Subrutin: Kunci bot/dummy, kaki tetap bisa bergerak")', 1)[1].split('rule("91o - Subrutin: Gambar menu pilihan pemain")', 1)[0]
        self.assertEqual(it_lock.count("Set Damage Received(Event Player, 100);"), 1)
        self.assertEqual(en_lock.count("Set Damage Received(Event Player, 100);"), 1)
        self.assertNotIn("Set Damage Received(Event Player, 0);", it_lock)
        self.assertNotIn("Set Damage Received(Event Player, 0);", en_lock)
        self.assertIn("Set Knockback Received(Event Player, 0);", it_lock)
        self.assertEqual(it_lock.count("Set Move Speed(Event Player, 20);"), 1)
        self.assertEqual(en_lock.count("Set Move Speed(Event Player, 20);"), 1)
        self.assertNotIn("Set Move Speed(Event Player, 0);", it_lock)
        self.assertNotIn("Set Move Speed(Event Player, 0);", en_lock)

    def test_dummy_faces_nearest_living_human_without_extra_loop(self):
        self.assertIn("Start Facing(Event Player", self.it)
        self.assertIn("Sorted Array(Filtered Array(Globale.PemainManusia", self.it)
        self.assertIn("Direction and Turn Rate", self.it)
        self.assertIn("Stop Facing(Event Player);", self.it)
        self.assertEqual(self.it.count("Loop If Condition Is True;"), 1)

    def test_native_dummy_walks_forward_automatically_and_stops_cleanly(self):
        throttle = (
            "Start Throttle In Direction(Event Player, Forward, Is In Spawn Room(Event Player) ? 0 : 1, "
            "To Player, Replace Existing Throttle, Direction and Magnitude);"
        )
        for source in (self.it, self.en):
            self.assertEqual(source.count(throttle), 1)
            self.assertEqual(source.count("Stop Throttle In Direction(Event Player);"), 2)
            self.assertEqual(source.count("Stop Throttle In Direction(First Of(Filtered Array("), 2)

        movement = self.en.split('rule("03g - Bot/Dummy: Hadap dan dekati pemain hidup terdekat")', 1)[1].split(
            'rule("03h - Bot/Dummy: Hentikan gerak saat tidak ada pemain hidup")', 1
        )[0]
        self.assertIn("Is Dummy Bot(Event Player) == True;", movement)
        self.assertNotIn("Event Player.BotOtomatis", movement)
        self.assertNotIn("Wait(", movement)


if __name__ == "__main__":
    unittest.main()
