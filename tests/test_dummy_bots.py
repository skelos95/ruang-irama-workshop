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
            self.assertIn('Custom String("COZYWATCH [{0}]"', source)
            self.assertIn('"Hold {0}: hero + HP"', source)
            self.assertIn('"Hold {0} 0.5s: Arcade | Hold {1} 0.5s: Camera"', source)
            self.assertIn("Input Binding String(Button(Crouch))", source)
            self.assertIn("Input Binding String(Button(Melee))", source)
            self.assertIn("Input Binding String(Button(Interact))", source)
            self.assertNotIn('"LOBBY & CHILL TIME"', source)
            self.assertIn('"PLAYER VIBES"', source)
            self.assertIn("9 + Count Of(Filtered Array(", source)
            self.assertIn("1 + Event Player.UrutanHUD", source)
            self.assertNotIn("-13 + Event Player.UrutanHUD", source)
            self.assertIn(f"{global_name}.SlotHUDTersedia = Sorted Array(Append To Array(", source)
            self.assertIn('Custom String("{0} {1} {2}"', source)
            self.assertNotIn('Custom String("{0}{1}{2}"', source)
            self.assertNotIn(f"-99 + Evaluate Once({global_name}.IndeksPemilih)", source)
            self.assertNotIn("\\nLOBBY & CHILL TIME", source)
            self.assertNotIn("\\nPLAYER VIBES", source)
            self.assertNotIn(", Top, 100,", source)
            self.assertNotIn(", Top, -99,", source)

    def test_shared_dummy_creation_subroutine_is_single_and_safe(self):
        self.assertEqual(
            self.it.count("Create Dummy Bot(Tutti gli eroi, Globale.TimBotBuatanAktif, -1, Position Of(First Of(Spawn Points(Globale.TimBotBuatanAktif))), Vector(0, 0, 1));"),
            1,
        )
        self.assertEqual(
            self.en.count("Create Dummy Bot(All Heroes, Global.TimBotBuatanAktif, -1, Position Of(First Of(Spawn Points(Global.TimBotBuatanAktif))), Vector(0, 0, 1));"),
            1,
        )
        self.assertEqual(self.it.count("Call Subroutine(BuatBotBuatanTim);"), 2)
        self.assertEqual(self.en.count("Call Subroutine(BuatBotBuatanTim);"), 2)
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

    def test_native_dummy_collision_overrides_are_removed(self):
        for source, rule_kw in ((self.it, "regola"), (self.en, "rule")):
            # Only the local human Ghost helper uses this Event Player action.
            self.assertEqual(source.count("Disable Movement Collision With Environment(Event Player, False);"), 1)
            bot_rule = source.split(
                f'{rule_kw}("03c - Bot: Kunci saat hidup kembali atau pahlawan berganti")', 1
            )[1].split(f'{rule_kw}("', 1)[0]
            self.assertNotIn("Movement Collision", bot_rule)
            self.assertIn("Call Subroutine(KunciBot);", bot_rule)
            self.assertIn("Set Respawn Max Time(Event Player, 3);", bot_rule)

    def test_dummy_reserves_the_last_human_slot_and_leaves_at_full_team(self):
        for team in ("Team 1", "Team 2"):
            self.assertIn(f"Number Of Players({team}) < Number Of Slots({team}) - 1,", self.it)
            self.assertIn(f"If(Number Of Players({team}) >= Number Of Slots({team}));", self.it)
            self.assertIn(
                f"If(Count Of(Filtered Array(All Players({team}), Is Dummy Bot(Current Array Element) == True)) > 0);",
                self.it,
            )
        self.assertEqual(self.it.count("Call Subroutine(LepasBotBuatanTim);"), 2)
        self.assertEqual(self.en.count("Call Subroutine(LepasBotBuatanTim);"), 2)
        self.assertEqual(
            self.it.count("Destroy Dummy Bot(Globale.TimBotBuatanAktif, Slot Of(First Of(Filtered Array(All Players(Globale.TimBotBuatanAktif), Is Dummy Bot(Current Array Element) == True))));"),
            1,
        )

    def test_spawn_teleport_uses_the_safe_skirmish_objective(self):
        self.assertIn("Is In Spawn Room(Event Player) == True;", self.it)
        self.assertNotIn("Wait(1.000, Annulla quando è False);", self.it)
        self.assertIn("If(Event Player.WaktuTeleportasiBotBuatan == 0);", self.it)
        self.assertIn(
            "Or(Event Player.WaktuTeleportasiBotBuatan == 0, Total Time Elapsed >= Event Player.WaktuTeleportasiBotBuatan) == True;",
            self.it,
        )
        self.assertIn("Event Player.WaktuTeleportasiBotBuatan = Total Time Elapsed + 1;", self.it)
        self.assertIn("Event Player.WaktuTeleportasiBotBuatan = 0;", self.it)
        self.assertIn("Direction From Angles(Horizontal Angle From Direction(Direction Towards(Event Player.PosisiMati, Position Of(First Of(Spawn Points(Team Of(Event Player)))))) + (Event Player.KursorTeleportasiBotBuatan % 8) * 45, 0)", self.it)
        self.assertIn("(Event Player.KursorTeleportasiBotBuatan < 8 ? 8 : 12)", self.it)
        self.assertIn("Distance Between(Event Player.PosisiBangkitAman, Event Player.PosisiMati) >= 6", self.it)
        for source, mode in ((self.it, "Schermaglia"), (self.en, "Skirmish")):
            self.assertEqual(source.count(f"Current Game Mode == Game Mode({mode})"), 3)
            self.assertIn("Event Player.PosisiMati = Objective Position(Objective Index);", source)
            self.assertNotIn("Payload Position", source)
            self.assertNotIn("Flag Position(", source)
            self.assertNotIn("Is On Objective(", source)
        self.assertIn("Nearest Walkable Position", self.it)
        self.assertNotIn("All Players On Objective(All Teams)", self.it)
        self.assertNotIn("Teleport(Event Player, Objective Position(Objective Index));", self.it)
        self.assertIn("Event Player.PosisiBangkitAman = Vector(0, 0, 0);", self.it)
        self.assertIn("Ray Cast Hit Position(Event Player.PosisiBangkitAman + Vector(0, 5, 0)", self.it)
        self.assertIn("Distance Between(Event Player.PosisiBangkitAman, Vector(0, 0, 0)) > 0.100", self.it)
        self.assertIn("Teleport(Event Player, Event Player.PosisiBangkitAman);", self.it)
        dummy_rule = self.it.split('regola("03f - Bot: Teleportasi dari ruang muncul ke objektif")', 1)[1].split('regola("03g -', 1)[0]
        self.assertIn("Event Player.PosisiTujuanTeleportasi = Event Player.PosisiBangkitAman;", dummy_rule)
        self.assertIn("Call Subroutine(CariPosisiTeleportasiAman);", dummy_rule)

    def test_dummy_receives_normal_damage(self):
        it_lock = self.it.split('regola("92 - Subrutin: Kunci bot, kaki tetap bisa bergerak")', 1)[1].split('regola("91o - Subrutin: Gambar menu pilihan pemain")', 1)[0]
        en_lock = self.en.split('rule("92 - Subrutin: Kunci bot, kaki tetap bisa bergerak")', 1)[1].split('rule("91o - Subrutin: Gambar menu pilihan pemain")', 1)[0]
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
            movement = source.split(f'{rule_kw}("03g - Bot: Hadap dan dekati manusia musuh hidup terdekat")', 1)[1].split(
                f'{rule_kw}("03h - Bot: Hentikan gerak saat tidak ada manusia musuh hidup")', 1
            )[0]
            self.assertIn("Event Player.TargetIkutiBotBuatan", movement)
            self.assertNotIn("Sorted Array(Filtered Array", movement)
            self.assertNotIn(f"Filtered Array({global_name}.PemainManusia", movement)
            self.assertIn("Direction and Turn Rate", movement)
            self.assertIn("Direction and Magnitude", movement)

            scheduler = source.split(f'{rule_kw}("89b2 - Subrutin: Rawat bot 10 Hz dan target ikuti 5 Hz")', 1)[1].split(
                f'{rule_kw}("89c - Subrutin: Proses simpanan pemain 1 Hz")', 1
            )[0]
            self.assertIn("TargetIkutiBotBuatan", scheduler)
            self.assertIn(f"Filtered Array({global_name}.PemainManusia", scheduler)
            self.assertIn("IzinkanBotBuatanMengikuti", scheduler)
            self.assertIn("Sorted Array", scheduler)
            self.assertIn(f"{global_name}.LangkahPenjadwal % 4 == Slot Of({global_name}.PemainAktif) % 4", scheduler)
        self.assertEqual(self.it.count("Loop If Condition Is True;"), 1)

    def test_dummy_follow_page_defaults_off_and_is_per_player(self):
        for source in (self.it, self.en):
            self.assertIn("Event Player.IzinkanBotBuatanMengikuti = False;", source)
            self.assertNotIn("KursorIkutiBotBuatan", source)
            self.assertIn("Call Subroutine(TerapkanHalamanIkutiBotBuatan);", source)
            self.assertIn("Call Subroutine(GambarIkutiBotBuatan);", source)
            self.assertIn("12 - DUMMY FOLLOW", source)
            self.assertIn('12 - BOT MENGIKUTI', source)

    def test_native_dummy_walks_forward_automatically_and_stops_cleanly(self):
        for source, rule_kw in ((self.it, "regola"), (self.en, "rule")):
            self.assertEqual(source.count("Start Throttle In Direction(Event Player, Forward,"), 1)
            self.assertIn("Distance Between(Event Player, Event Player.TargetIkutiBotBuatan) <= 4", source)
            self.assertEqual(source.count("Stop Throttle In Direction(Event Player);"), 2)
            self.assertEqual(source.count("Stop Throttle In Direction(First Of(Filtered Array("), 1)

            movement = source.split(f'{rule_kw}("03g - Bot: Hadap dan dekati manusia musuh hidup terdekat")', 1)[1].split(
                f'{rule_kw}("03h - Bot: Hentikan gerak saat tidak ada manusia musuh hidup")', 1
            )[0]
            self.assertIn("Is Dummy Bot(Event Player) == True;", movement)
            self.assertIn("TargetIkutiBotBuatan", movement)
            self.assertNotIn("Wait(", movement)

            cleanup = source.split(f'{rule_kw}("03h - Bot: Hentikan gerak saat tidak ada manusia musuh hidup")', 1)[1].split(
                f'{rule_kw}("03i - Bot: Hentikan gerak saat bot mati")', 1
            )[0]
            self.assertIn("TargetIkutiBotBuatan", cleanup)


if __name__ == "__main__":
    unittest.main()
