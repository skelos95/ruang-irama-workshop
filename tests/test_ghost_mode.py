from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class GhostModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.it = (ROOT / "workshop" / "ruang_irama.it-IT.workshop").read_text(encoding="utf-8")
        cls.en = (ROOT / "tests" / "fixtures" / "semantic_reference.txt").read_text(encoding="utf-8")

    def test_page_13_is_wired_end_to_end(self):
        for source, g in ((self.it, "Globale"), (self.en, "Global")):
            self.assertIn("108: KursorGhost", source)
            self.assertIn("106: GhostAktif", source)
            self.assertNotIn("SegarkanRosterTertunda", source)
            self.assertIn("% 14;", source)
            self.assertIn("HalamanMenu == 13", source)
            self.assertIn("Call Subroutine(GambarGhost);", source)
            self.assertIn("Call Subroutine(TerapkanHalamanGhost);", source)
            self.assertIn("13 - GHOST MODE", source)
            self.assertIn("13 - MODE GHOST", source)
            self.assertIn("13 - โหมดผี", source)

    def test_ghost_changes_only_environment_collision(self):
        for source in (self.it, self.en):
            start = source.index('"99n - Subrutin: Terapkan Ghost Mode"')
            end = source.index('"99a - Subrutin: Terapkan halaman musik"', start)
            block = source[start:end]
            self.assertIn("Disable Movement Collision With Environment(Event Player, False);", block)
            self.assertIn("Enable Movement Collision With Environment(Event Player);", block)
            self.assertNotIn("Disable Movement Collision With Players", block)
            self.assertNotIn("Enable Movement Collision With Players", block)

    def test_ghost_persists_and_is_reasserted(self):
        for source, g in ((self.it, "Globale"), (self.en, "Global")):
            self.assertIn("(Event Player.GhostAktif ? 2 : 0)", source)
            self.assertIn(f"{g}.PemainAktif.GhostAktif == True", source)
            self.assertIn(f"Disable Movement Collision With Environment({g}.PemainAktif, False);", source)
            self.assertIn("Enable Movement Collision With Environment(Event Player);", source)


if __name__ == "__main__":
    unittest.main()
