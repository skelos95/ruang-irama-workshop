"""Dummy contracts for the logical behavioral input, before compilation."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DummyBotFeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.it = (ROOT / "source" / "ruang_irama.en-US.source").read_text(encoding="utf-8")
        cls.en = (ROOT / "tests" / "fixtures" / "semantic_reference.txt").read_text(encoding="utf-8")

    def test_static_hud_uses_recyclable_roster_slots_without_embedded_label_spacing(self):
        for source, global_name in ((self.it, "Global"), (self.en, "Global")):
            self.assertIn('Custom String("COZYWATCH [{0}]"', source)
            self.assertIn('"HERO + HP INSPECTION: hold Crouch ({0}); Arcade closed, Travel OFF or Teleport Player/Bot / Attach"', source)
            self.assertIn('"ARCADE: hold Melee ({0}) 0.5s: open / close"', source)
            self.assertIn("Input Binding String(Button(Crouch))", source)
            self.assertIn("Input Binding String(Button(Melee))", source)
            self.assertIn("Input Binding String(Button(Interact))", source)
            self.assertNotIn('"LOBBY & CHILL TIME"', source)
            self.assertIn('"PLAYER VIBES"', source)
            self.assertIn("6 + Count Of(Filtered Array(", source)
            self.assertIn("1 + Event Player.HudSlot", source)
            self.assertNotIn("-13 + Event Player.HudSlot", source)
            self.assertIn(f"{global_name}.AvailableHudSlots = Sorted Array(Append To Array(", source)
            self.assertIn('Custom String("{0} {1} {2}"', source)
            self.assertNotIn('Custom String("{0}{1}{2}"', source)
            self.assertNotIn(f"-99 + Evaluate Once({global_name}.VoterIndex)", source)
            self.assertNotIn("\\nLOBBY & CHILL TIME", source)
            self.assertNotIn("\\nPLAYER VIBES", source)
            self.assertNotIn(", Top, 100,", source)
            self.assertNotIn(", Top, -99,", source)

    def test_shared_dummy_creation_subroutine_is_single_and_safe(self):
        self.assertEqual(
            self.it.count("Create Dummy Bot(All Heroes, Global.ActiveDummyBotTeam, -1, Position Of(First Of(Spawn Points(Global.ActiveDummyBotTeam))), Vector(0, 0, 1));"),
            1,
        )
        self.assertEqual(
            self.en.count("Create Dummy Bot(All Heroes, Global.ActiveDummyBotTeam, -1, Position Of(First Of(Spawn Points(Global.ActiveDummyBotTeam))), Vector(0, 0, 1));"),
            1,
        )
        self.assertEqual(self.it.count("Call Subroutine(CreateTeamDummyBot);"), 2)
        self.assertEqual(self.en.count("Call Subroutine(CreateTeamDummyBot);"), 2)
        self.assertNotIn("Create Dummy Bot(All Heroes, Team 1, -1, Null, Null);", self.it)
        self.assertNotIn("Create Dummy Bot(All Heroes, Team 2, -1, Null, Null);", self.it)

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
        for source, rule_kw in ((self.it, "rule"), (self.en, "rule")):
            # Only the local human Ghost helper uses this Event Player action.
            self.assertEqual(source.count("Disable Movement Collision With Environment(Event Player, False);"), 1)
            bot_rule = source.split(
                f'{rule_kw}("03c - Bot: Lock on respawn or hero change")', 1
            )[1].split(f'{rule_kw}("', 1)[0]
            self.assertNotIn("Movement Collision", bot_rule)
            self.assertIn("Call Subroutine(LockBot);", bot_rule)
            self.assertIn("Set Respawn Max Time(Event Player, 3);", bot_rule)

    def test_dummy_reserves_the_last_human_slot_and_leaves_at_full_team(self):
        for team in ("Team 1", "Team 2"):
            self.assertIn(f"Number Of Players({team}) < Number Of Slots({team}) - 1,", self.it)
            self.assertIn(f"If(Number Of Players({team}) >= Number Of Slots({team}));", self.it)
            self.assertIn(
                f"If(Count Of(Filtered Array(All Players({team}), Is Dummy Bot(Current Array Element) == True)) > 0);",
                self.it,
            )
        self.assertEqual(self.it.count("Call Subroutine(RemoveTeamDummyBot);"), 2)
        self.assertEqual(self.en.count("Call Subroutine(RemoveTeamDummyBot);"), 2)
        self.assertEqual(
            self.it.count("Destroy Dummy Bot(Global.ActiveDummyBotTeam, Slot Of(First Of(Filtered Array(All Players(Global.ActiveDummyBotTeam), Is Dummy Bot(Current Array Element) == True))));"),
            1,
        )

    def test_spawn_teleport_uses_the_safe_skirmish_objective(self):
        self.assertIn("Is In Spawn Room(Event Player) == True;", self.it)
        self.assertNotIn("Wait(1.000, Annulla quando è False);", self.it)
        self.assertIn("If(Event Player.DummyBotTravelTime == 0);", self.it)
        self.assertIn(
            "Or(Event Player.DummyBotTravelTime == 0, Total Time Elapsed >= Event Player.DummyBotTravelTime) == True;",
            self.it,
        )
        self.assertIn("Event Player.DummyBotTravelTime = Total Time Elapsed + 1;", self.it)
        self.assertIn("Event Player.DummyBotTravelTime = 0;", self.it)
        self.assertIn("Direction From Angles(Horizontal Angle From Direction(Direction Towards(Event Player.DeathPosition, Position Of(First Of(Spawn Points(Team Of(Event Player)))))) + Event Player.DummyBotTravelCursor % 8 * 45, 0)", self.it)
        self.assertIn("(Event Player.DummyBotTravelCursor < 8 ? 8 : 12)", self.it)
        self.assertIn("Distance Between(Event Player.SafeRevivePosition, Event Player.DeathPosition) >= 6", self.it)
        for source, mode in ((self.it, "Skirmish"), (self.en, "Skirmish")):
            self.assertEqual(source.count(f"Current Game Mode == Game Mode({mode})"), 3)
            self.assertIn("Event Player.DeathPosition = Objective Position(Objective Index);", source)
            self.assertNotIn("Payload Position", source)
            self.assertNotIn("Flag Position(", source)
            self.assertNotIn("Is On Objective(", source)
        self.assertIn("Nearest Walkable Position", self.it)
        self.assertNotIn("All Players On Objective(All Teams)", self.it)
        self.assertNotIn("Teleport(Event Player, Objective Position(Objective Index));", self.it)
        self.assertIn("Event Player.SafeRevivePosition = Vector(0, 0, 0);", self.it)
        self.assertIn("Ray Cast Hit Position(Event Player.SafeRevivePosition + Vector(0, 5, 0)", self.it)
        self.assertIn("Distance Between(Event Player.SafeRevivePosition, Vector(0, 0, 0)) > 0.100", self.it)
        self.assertIn("Teleport(Event Player, Event Player.SafeRevivePosition);", self.it)
        dummy_rule = self.it.split('rule("03f - ', 1)[1].split('rule("03g -', 1)[0]
        self.assertIn("Event Player.TravelDestination = Event Player.SafeRevivePosition;", dummy_rule)
        self.assertIn("Call Subroutine(FindSafeTravelPosition);", dummy_rule)

    def test_dummy_receives_normal_damage(self):
        it_lock = self.it.split('rule("92 - ', 1)[1].split('rule("91o - ', 1)[0]
        en_lock = self.en.split('rule("92 - ', 1)[1].split('rule("91o - ', 1)[0]
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
        for source, global_name, rule_kw in ((self.it, "Global", "rule"), (self.en, "Global", "rule")):
            movement = source.split(f'{rule_kw}("03g - ', 1)[1].split(
                f'{rule_kw}("03h - Bot: Stop moving when no enemy human is alive")', 1
            )[0]
            self.assertIn("Event Player.DummyBotFollowTarget", movement)
            self.assertNotIn("Sorted Array(Filtered Array", movement)
            self.assertNotIn(f"Filtered Array({global_name}.HumanPlayers", movement)
            self.assertIn("Direction and Turn Rate", movement)
            self.assertIn("Direction and Magnitude", movement)

            scheduler = source.split(f'{rule_kw}("89b2 - ', 1)[1].split(
                f'{rule_kw}("89c - Subroutine: Process player maintenance at 1 Hz")', 1
            )[0]
            self.assertIn("DummyBotFollowTarget", scheduler)
            self.assertIn(f"Filtered Array({global_name}.HumanPlayers", scheduler)
            self.assertIn("AllowDummyBotFollow", scheduler)
            self.assertIn("Sorted Array", scheduler)
            self.assertIn(f"{global_name}.SchedulerStep % 4 == Slot Of({global_name}.ActivePlayer) % 4", scheduler)
        self.assertEqual(self.it.count("Loop If Condition Is True;"), 1)

    def test_dummy_follow_page_defaults_off_and_is_per_player(self):
        for source in (self.it, self.en):
            self.assertIn("Event Player.AllowDummyBotFollow = False;", source)
            self.assertNotIn("KursorIkutiBotBuatan", source)
            self.assertIn("Call Subroutine(ApplyDummyBotFollowPage);", source)
            self.assertNotIn("GambarIkutiBotBuatan", source)
            self.assertIn("Event Player.MainMenuCursor == 12", source)
            self.assertIn("12 - DUMMY FOLLOW", source)

    def test_native_dummy_walks_forward_automatically_and_stops_cleanly(self):
        for source, rule_kw in ((self.it, "rule"), (self.en, "rule")):
            self.assertEqual(source.count("Start Throttle In Direction(Event Player, Forward,"), 1)
            self.assertIn("Distance Between(Event Player, Event Player.DummyBotFollowTarget) <= 4", source)
            self.assertEqual(source.count("Stop Throttle In Direction(Event Player);"), 2)
            self.assertEqual(source.count("Stop Throttle In Direction(First Of(Filtered Array("), 1)

            movement = source.split(f'{rule_kw}("03g - ', 1)[1].split(
                f'{rule_kw}("03h - Bot: Stop moving when no enemy human is alive")', 1
            )[0]
            self.assertIn("Is Dummy Bot(Event Player) == True;", movement)
            self.assertIn("DummyBotFollowTarget", movement)
            self.assertNotIn("Wait(", movement)

            cleanup = source.split(f'{rule_kw}("03h - ', 1)[1].split(
                f'{rule_kw}("03i - Bot: Stop moving on death")', 1
            )[0]
            self.assertIn("DummyBotFollowTarget", cleanup)


if __name__ == "__main__":
    unittest.main()
