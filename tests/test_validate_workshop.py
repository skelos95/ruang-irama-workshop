from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import validate_workshop as validator


class GlobalFirst072Tests(unittest.TestCase):
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

    def test_teleport_uses_three_pages(self) -> None:
        mutated = self.source.replace(
            "Event Player.KursorTeleportasi = (Event Player.KursorTeleportasi + 1) % 3;",
            "Event Player.KursorTeleportasi = (Event Player.KursorTeleportasi + 1) % 2;",
            1,
        )
        self.assertTrue(any("tre pagine" in error for error in self.errors(mutated)))

    def test_teleport_privacy_filter_is_required(self) -> None:
        start = self.source.index('rule("98 - Subrutin:')
        pos = self.source.index("Player Variable(Current Array Element, PrivasiInspeksiAktif) == False", start)
        mutated = self.source[:pos] + self.source[pos:].replace(
            "Player Variable(Current Array Element, PrivasiInspeksiAktif) == False",
            "Player Variable(Current Array Element, PrivasiInspeksiAktif) == True",
            1,
        )
        self.assertTrue(any("privacy" in error for error in self.errors(mutated)))

    def test_teleport_closest_to_reticle_is_required(self) -> None:
        start = self.source.index('rule("98 - Subrutin:')
        pos = self.source.index("First Of(Sorted Array(Event Player.DaftarTargetTeleportasi", start)
        mutated = self.source[:pos] + self.source[pos:].replace(
            "First Of(Sorted Array(Event Player.DaftarTargetTeleportasi",
            "First Of(Event Player.DaftarTargetTeleportasi",
            1,
        )
        self.assertTrue(any("closest-to-reticle" in error for error in self.errors(mutated)))

    def test_teleport_bots_remain_public_targets(self) -> None:
        start = self.source.index('rule("98 - Subrutin:')
        pos = self.source.index("Is Dummy Bot(Current Array Element) == True", start)
        mutated = self.source[:pos] + self.source[pos:].replace("Is Dummy Bot(Current Array Element) == True", "Is Dummy Bot(Current Array Element) == False", 1)
        self.assertTrue(any("bot pubblici" in error for error in self.errors(mutated)))

    def test_teleport_world_label_is_independent_from_inspection(self) -> None:
        start = self.source.index('rule("19d - Teleportasi Jongkok:')
        pos = self.source.index("Event Player.CalonTargetTeleportasi", start)
        mutated = self.source[:pos] + self.source[pos:].replace("Event Player.CalonTargetTeleportasi", "Event Player.TargetInspeksi", 1)
        self.assertTrue(any("rivaluta il target live" in error or "stato Inspection" in error for error in self.errors(mutated)))

    def test_preloaded_submenu_is_required(self) -> None:
        mutated = self.source.replace('rule("91q - SubmenuPreload")', 'rule("91q - X")', 1)
        self.assertTrue(any("SubmenuPreload" in error for error in self.errors(mutated)))

    def test_unkillable_one_hp_guard_is_required(self) -> None:
        mutated = self.source.replace("If(Health(Global.PemainAktif) >= Max Health(Global.PemainAktif));", "If(Health(Global.PemainAktif) > 1);", 1)
        self.assertTrue(any("Unkillable 1 HP" in error for error in self.errors(mutated)))

    def test_try_your_luck_forcing_position_is_rejected(self) -> None:
        mutated = self.source + "\nStart Forcing Player Position(Event Player, Position Of(Event Player), False);\n"
        self.assertTrue(any("forzare la posizione" in error for error in self.errors(mutated)))

    def test_try_your_luck_reopen_waits_for_alive_respawn(self) -> None:
        start = self.source.index('rule(\"18g - Nasib:')
        pos = self.source.index("Is Alive(Event Player) == True;", start)
        mutated = self.source[:pos] + self.source[pos:].replace(
            "Is Alive(Event Player) == True;",
            "Is Alive(Event Player) == False;",
            1,
        )
        self.assertTrue(any("respawn vivo" in error for error in self.errors(mutated)))

    def test_try_your_luck_expiry_is_per_player(self) -> None:
        start = self.source.index('rule("18h - Nasib:')
        pos = self.source.index("Ongoing - Each Player;", start)
        mutated = self.source[:pos] + self.source[pos:].replace("Ongoing - Each Player;", "Ongoing - Global;", 1)
        self.assertTrue(any("18h scadenza Try Your Luck" in error for error in self.errors(mutated)))

    def test_try_your_luck_death_redraw_is_required(self) -> None:
        start = self.source.index('rule("18f - Nasib:')
        pos = self.source.index("Wait(0.100, Ignore Condition);", start)
        mutated = self.source[:pos] + self.source[pos:].replace("Wait(0.100, Ignore Condition);", "Wait(0.200, Ignore Condition);", 1)
        self.assertTrue(any("death screen" in error or "transizione HUD" in error for error in self.errors(mutated)))

    def test_periodic_pollers_are_global(self) -> None:
        for prefix in ("04i - Global-first:", "04j - Global-first:"):
            start = self.source.index(f'rule("{prefix}')
            pos = self.source.index("Ongoing - Global;", start)
            mutated = self.source[:pos] + self.source[pos:].replace("Ongoing - Global;", "Ongoing - Each Player;", 1)
            self.assertTrue(any(prefix in error and "scheduler" in error for error in self.errors(mutated)))

    def test_cleanup_critical_section_has_no_wait(self) -> None:
        mutated = self.source.replace(
            "Global.IndeksKeluar = Index Of Array Value(Global.PemainManusia, Event Player);",
            "Global.IndeksKeluar = Index Of Array Value(Global.PemainManusia, Event Player);\n\t\tWait(0.016, Ignore Condition);",
            1,
        )
        self.assertTrue(any("scratch Global" in error for error in self.errors(mutated)))

    def test_vote_loop_count_minus_one_is_rejected(self) -> None:
        mutated = self.source.replace(
            "For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia), 1);",
            "For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia) - 1, 1);",
            1,
        )
        self.assertTrue(any("Range Stop" in error for error in self.errors(mutated)))

    def test_fast_manager_count_minus_one_is_rejected(self) -> None:
        mutated = self.source.replace(
            "For Global Variable(IndeksPemainGlobal, 0, Count Of(All Players(All Teams)), 1);",
            "For Global Variable(IndeksPemainGlobal, 0, Count Of(All Players(All Teams)) - 1, 1);",
            1,
        )
        self.assertTrue(any("Range Stop" in error for error in self.errors(mutated)))

    def test_live_confirmed_blob_is_pinned(self) -> None:
        mutated = self.source.replace("Global.PemainAktif = Null;", "Global.PemainAktif = Null;\n", 1)
        self.assertTrue(any("blob sorgente live-confirmato" in error for error in self.errors(mutated)))


if __name__ == "__main__":
    unittest.main()
