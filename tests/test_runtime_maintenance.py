from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RuntimeMaintenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.it = (ROOT / "workshop" / "ruang_irama.it-IT.workshop").read_text(encoding="utf-8")
        cls.en = (ROOT / "tests" / "fixtures" / "semantic_reference.txt").read_text(encoding="utf-8")

    def test_display_name_is_not_used_as_cleanup_identity(self):
        for source, global_name in ((self.it, "Globale"), (self.en, "Global")):
            self.assertNotIn(f'Mapped Array({global_name}.PemainManusia, Custom String("{{0}}", Current Array Element))', source)

    def test_aim_scans_are_scheduler_cached(self):
        for source, rule_kw, global_name in ((self.it, "regola", "Globale"), (self.en, "rule", "Global")):
            inspect = source.split(f'{rule_kw}("13 - Intip Pahlawan: Nama mengikuti target bidikan tanpa Wait")', 1)[1].split(f'{rule_kw}("16a - Anran', 1)[0]
            self.assertNotIn("Sorted Array(Filtered Array", inspect)
            self.assertIn("CalonTargetInspeksi", inspect)
            self.assertNotIn("19d0 - Teleportasi Jongkok", source)
            scheduler = source.split(f'{rule_kw}("89b - Subrutin: Proses siklus pemain 10 Hz")', 1)[1].split(f'{rule_kw}("89c - Subrutin', 1)[0]
            self.assertIn("CalonTargetInspeksi", scheduler)
            self.assertIn("CalonTargetTeleportasi", scheduler)
            self.assertIn(f"Call Subroutine(SegarkanTargetPublikAktif);", scheduler)

    def test_safe_position_is_shared_by_player_teleports_and_resurrect(self):
        for source in (self.it, self.en):
            self.assertIn("57: CariPosisiTeleportAman", source)
            self.assertGreaterEqual(source.count("Call Subroutine(CariPosisiTeleportAman);"), 5)
            self.assertIn("Ray Cast Hit Position(Event Player.PosisiTeleportTujuan + Vector(0, 1, 0)", source)

    def test_burning_suspends_unkillable_and_scales_with_max_health(self):
        for source, global_name in ((self.it, "Globale"), (self.en, "Global")):
            self.assertIn(f"Set Status({global_name}.PemainAktif, Null, Burning, 10);", source)
            self.assertIn(f"Clear Status({global_name}.PemainAktif, Unkillable);", source)
            self.assertIn(f"Damage({global_name}.PemainAktif, {global_name}.PemainAktif, Max Health({global_name}.PemainAktif) * 0.050);", source)
            self.assertIn(f"{global_name}.PemainAktif.WaktuBakarNasibBerikut = Total Time Elapsed + 1.000;", source)
            self.assertIn(f"And({global_name}.PemainAktif.EfekNasib == 5, {global_name}.PemainAktif.EfekNasibBerakhir > Total Time Elapsed)", source)

    def test_shared_aim_distance_state_is_preserved(self):
        for source in (self.it, self.en):
            self.assertIn("JarakBidik", source)
            self.assertIn("JarakBidik = 25;", source)


    def test_crouch_teleport_has_four_pages_and_new_controls(self):
        for source in (self.it, self.en):
            self.assertIn("KursorTeleportasi %= 4;", source)
            self.assertIn("Event Player.PerintahTeleportasi = 1;", source)
            self.assertIn("Event Player.PerintahTeleportasi = 2;", source)
            self.assertIn("Event Player.PerintahTeleportasi = 3;", source)
            self.assertIn("PerintahTeleportasi == 3;", source)
            self.assertIn("(Event Player.KursorTeleportasi + (Event Player.PerintahTeleportasi == 1 ? 1 : 3)) % 4", source)
            self.assertIn("PLAYER / BOT ATTACH 4/4", source)

    def test_crouch_attach_uses_native_attach_and_crouch_reload_detach(self):
        for source, rule_kw in ((self.it, "regola"), (self.en, "rule")):
            self.assertIn("Attach Players(Event Player, Event Player.TargetLampiranTeleportasi, Vector(0,", source)
            self.assertIn("+ 0.750, 0));", source)
            self.assertIn("Detach Players(Event Player);", source)
            detach_rule = source.split(f'{rule_kw}("19f - Teleportasi Jongkok: Reload melepas lampiran")', 1)[1].split(f'{rule_kw}("19h - Teleportasi Jongkok', 1)[0]
            self.assertIn("Is Button Held(Event Player, Button(Crouch)) == True;", detach_rule)
            self.assertIn("Is Button Held(Event Player, Button(Reload)) == True;", detach_rule)
            self.assertIn("CROUCH + RELOAD: DETACH", source)
            self.assertIn("99: TargetLampiranTeleportasi", source)
            self.assertIn("100: LampiranTeleportasiAktif", source)

    def test_crouch_attach_auto_detaches_on_death_leave_or_hero_change(self):
        for source in (self.it, self.en):
            self.assertIn("Entity Exists(Event Player.TargetLampiranTeleportasi) == False", source)
            self.assertIn("Is Alive(Event Player.TargetLampiranTeleportasi) == False", source)
            self.assertIn("Hero Of(Event Player) != Event Player.PahlawanLampiranSendiri", source)
            self.assertIn("Hero Of(Event Player.TargetLampiranTeleportasi) != Event Player.PahlawanLampiranTarget", source)
            self.assertIn("TargetLampiranTeleportasi) == Global.PemainPembersihan", source.replace("Globale.", "Global."))

if __name__ == "__main__":
    unittest.main()
