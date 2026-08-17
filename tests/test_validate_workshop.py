from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import validate_workshop as validator


class GlobalFirst070Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = validator.SOURCE.read_text(encoding="utf-8")

    def errors(self, source: str) -> list[str]:
        return validator.validate(source).errors

    def test_official_source_passes(self) -> None:
        self.assertEqual(self.errors(self.source), [])

    def test_invalid_for_global_variable_syntax_is_rejected(self) -> None:
        mutated = self.source.replace("For Global Variable(IndeksPemainGlobal", "For Global Variable(Global.IndeksPemainGlobal", 1)
        self.assertTrue(any("For Global Variable" in error for error in self.errors(mutated)))

    def test_fast_global_manager_is_required(self) -> None:
        mutated = self.source.replace('rule("04g - Global-first', 'rule("04x - Global-first', 1)
        self.assertTrue(any("manager Global-first" in error for error in self.errors(mutated)))

    def test_menu_dispatcher_must_stay_each_player(self) -> None:
        start = self.source.index('rule("05c - Menu:')
        pos = self.source.index("Ongoing - Each Player;", start)
        mutated = self.source[:pos] + self.source[pos:].replace("Ongoing - Each Player;", "Ongoing - Global;", 1)
        self.assertTrue(any("05c - Menu:" in error and "scheduler" in error for error in self.errors(mutated)))

    def test_camera_release_must_stay_each_player(self) -> None:
        start = self.source.index('rule("12d - Kamera:')
        pos = self.source.index("Ongoing - Each Player;", start)
        mutated = self.source[:pos] + self.source[pos:].replace("Ongoing - Each Player;", "Ongoing - Global;", 1)
        self.assertTrue(any("12d - Kamera:" in error and "scheduler" in error for error in self.errors(mutated)))

    def test_teleport_dispatcher_must_stay_each_player(self) -> None:
        start = self.source.index('rule("19a - Teleportasi Jongkok:')
        pos = self.source.index("Ongoing - Each Player;", start)
        mutated = self.source[:pos] + self.source[pos:].replace("Ongoing - Each Player;", "Ongoing - Global;", 1)
        self.assertTrue(any("19a - Teleportasi" in error and "scheduler" in error for error in self.errors(mutated)))

    def test_preloaded_submenu_is_required(self) -> None:
        mutated = self.source.replace('rule("91q - SubmenuPreload")', 'rule("91q - X")', 1)
        self.assertTrue(any("SubmenuPreload" in error for error in self.errors(mutated)))

    def test_unkillable_one_hp_guard_is_required(self) -> None:
        mutated = self.source.replace("If(Health(Global.PemainAktif) >= Max Health(Global.PemainAktif));", "If(Health(Global.PemainAktif) > 1);", 1)
        self.assertTrue(any("Unkillable 1 HP" in error for error in self.errors(mutated)))

    def test_try_your_luck_forcing_position_is_rejected(self) -> None:
        mutated = self.source + "\nStart Forcing Player Position(Event Player, Position Of(Event Player), False);\n"
        self.assertTrue(any("forzare la posizione" in error for error in self.errors(mutated)))

    def test_live_confirmed_blob_is_pinned(self) -> None:
        mutated = self.source.replace("Global.PemainAktif = Null;", "Global.PemainAktif = Null;\n", 1)
        self.assertTrue(any("blob sorgente live-confirmato" in error for error in self.errors(mutated)))


if __name__ == "__main__":
    unittest.main()
