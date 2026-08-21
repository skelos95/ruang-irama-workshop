from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class DummyBotFeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.it = (ROOT / "workshop" / "ruang_irama.it-IT.workshop").read_text(encoding="utf-8")
        cls.en = (ROOT / "tests" / "fixtures" / "semantic_reference.txt").read_text(encoding="utf-8")

    def test_player_vibes_title_is_shifted_right(self):
        self.assertIn("\\n \\n     PLAYER VIBES", self.it)
        self.assertIn("\\n \\n     MUSIK PEMAIN", self.it)

    def test_exactly_one_creation_rule_per_team(self):
        self.assertEqual(self.it.count("Create Dummy Bot(Tutti gli eroi, Squadra 1, -1, Null, Null);"), 1)
        self.assertEqual(self.it.count("Create Dummy Bot(Tutti gli eroi, Squadra 2, -1, Null, Null);"), 1)
        self.assertEqual(self.en.count("Create Dummy Bot(All Heroes, Team 1, -1, Null, Null);"), 1)
        self.assertEqual(self.en.count("Create Dummy Bot(All Heroes, Team 2, -1, Null, Null);"), 1)

    def test_dummy_respawn_is_30_seconds(self):
        self.assertIn("Set Respawn Max Time(Event Player, 30);", self.it)

    def test_spawn_teleport_targets_objective(self):
        self.assertIn("Is In Spawn Room(Event Player) == True;", self.it)
        self.assertIn("All Players On Objective(All Teams)", self.it)
        self.assertIn("Objective Position(Objective Index)", self.it)

    def test_dummy_faces_nearest_living_human_without_extra_loop(self):
        self.assertIn("Start Facing(Event Player", self.it)
        self.assertIn("Sorted Array(Filtered Array(Globale.PemainManusia", self.it)
        self.assertIn("Direction and Turn Rate", self.it)
        self.assertIn("Stop Facing(Event Player);", self.it)
        self.assertEqual(self.it.count("Loop If Condition Is True;"), 1)

if __name__ == "__main__":
    unittest.main()
