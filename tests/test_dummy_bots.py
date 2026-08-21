from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

# Live regression: dummy bots must never use a raw/zero objective teleport.
class DummyBotFeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.it = (ROOT / "workshop" / "ruang_irama.it-IT.workshop").read_text(encoding="utf-8")
        cls.en = (ROOT / "tests" / "fixtures" / "semantic_reference.txt").read_text(encoding="utf-8")

    def test_hold_sections_use_one_newline_before_labels(self):
        self.assertIn("\\nLOBBY & CHILL TIME", self.it)
        self.assertIn("\\nLOBI & WAKTU SANTAI", self.it)
        self.assertIn("\\n     PLAYER VIBES", self.it)
        self.assertIn("\\n     MUSIK PEMAIN", self.it)
        self.assertNotIn("\\n \\nLOBBY & CHILL TIME", self.it)
        self.assertNotIn("\\n \\n     PLAYER VIBES", self.it)

    def test_exactly_one_creation_rule_per_team(self):
        self.assertEqual(self.it.count("Create Dummy Bot(Tutti gli eroi, Team 1, -1, Null, Null);"), 1)
        self.assertEqual(self.it.count("Create Dummy Bot(Tutti gli eroi, Team 2, -1, Null, Null);"), 1)
        self.assertEqual(self.en.count("Create Dummy Bot(All Heroes, Team 1, -1, Null, Null);"), 1)
        self.assertEqual(self.en.count("Create Dummy Bot(All Heroes, Team 2, -1, Null, Null);"), 1)

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

    def test_spawn_teleport_uses_safe_mode_specific_destinations(self):
        self.assertIn("Is In Spawn Room(Event Player) == True;", self.it)
        self.assertIn("Payload Position", self.it)
        self.assertIn("Flag Position(Opposite Team Of(Team Of(Event Player)))", self.it)
        self.assertIn("Current Game Mode == Game Mode(Cattura la Bandiera)", self.it)
        self.assertIn("Current Game Mode == Game Mode(Scorta)", self.it)
        self.assertIn("Nearest Walkable Position", self.it)
        self.assertNotIn("Teleport(Event Player, Objective Position(Objective Index));", self.it)

    def test_dummy_faces_nearest_living_human_without_extra_loop(self):
        self.assertIn("Start Facing(Event Player", self.it)
        self.assertIn("Sorted Array(Filtered Array(Globale.PemainManusia", self.it)
        self.assertIn("Direction and Turn Rate", self.it)
        self.assertIn("Stop Facing(Event Player);", self.it)
        self.assertEqual(self.it.count("Loop If Condition Is True;"), 1)

if __name__ == "__main__":
    unittest.main()
