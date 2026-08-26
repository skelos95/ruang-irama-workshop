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

    def test_cached_player_name_drives_roster_and_world_text(self):
        for source, global_name, rule_kw in ((self.it, "Globale", "regola"), (self.en, "Global", "rule")):
            self.assertIn("107: NamaTampilan", source)

            classifier = source.split(f'{rule_kw}("02 - Pemain: Pisahkan manusia dari pasukan kaleng")', 1)[1].split(f'{rule_kw}("02b - HUD Pemain', 1)[0]
            self.assertIn('Event Player.NamaTampilan = Evaluate Once(Custom String("{0}", Event Player));', classifier)

            roster = source.split(f'{rule_kw}("02b - HUD Pemain', 1)[1].split(f'{rule_kw}("03c - Bot/Dummy', 1)[0]
            self.assertIn("Event Player.NamaTampilan != Null;", roster)
            self.assertIn('Custom String("{0} - {1} MIN", Event Player.NamaTampilan, Event Player.MenitLobi)', roster)
            self.assertIn('Custom String("{0} - {1}", Event Player.NamaTampilan,', roster)

            inspect = source.split(f'{rule_kw}("13 - Intip Pahlawan: Nama mengikuti target bidikan tanpa Wait")', 1)[1].split(f'{rule_kw}("16a - Anran', 1)[0]
            self.assertIn("Player Variable(Event Player.TargetInspeksi, NamaTampilan)", inspect)

            teleport = source.split(f'{rule_kw}("19d - Teleportasi Jongkok: Buat ulang nama saat target berubah")', 1)[1].split(f'{rule_kw}("19e - Teleportasi Jongkok', 1)[0]
            self.assertIn("Player Variable(Event Player.CalonTargetTeleportasi, NamaTampilan)", teleport)

            fast = source.split(f'{rule_kw}("89a - Subrutin: Proses status cepat pemain")', 1)[1].split(f'{rule_kw}("89b - Subrutin', 1)[0]
            self.assertIn(f"If({global_name}.PemainAktif.NamaTampilan == Null);", fast)
            self.assertIn(f'{global_name}.PemainAktif.NamaTampilan = Evaluate Once(Custom String("{{0}}", {global_name}.PemainAktif));', fast)

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


    def test_crouch_teleport_has_five_pages_and_single_shot_self_kill(self):
        for source, rule_kw, global_name in ((self.it, "regola", "Globale"), (self.en, "rule", "Global")):
            self.assertIn("KursorTeleportasi %= 5;", source)
            self.assertIn("Event Player.PerintahTeleportasi = 1;", source)
            self.assertIn("Event Player.PerintahTeleportasi = 2;", source)
            self.assertIn("Event Player.PerintahTeleportasi = 3;", source)
            self.assertIn("PerintahTeleportasi == 3;", source)
            self.assertIn("(Event Player.KursorTeleportasi + (Event Player.PerintahTeleportasi == 1 ? 1 : 4)) % 5", source)
            self.assertIn("PLAYER / BOT ATTACH 4/5", source)
            self.assertIn("SELF KILL 5/5", source)

            teleport_render = source.split(f'{rule_kw}("91g - Subrutin: Gambar menu teleportasi")', 1)[1].split(f'{rule_kw}("', 1)[0]
            self.assertNotIn("\\", teleport_render)
            self.assertNotIn('Custom String("{0}n{1}"', teleport_render)
            self.assertIn('Custom String("{0}\n{1}", Custom String("{0}\n{1}",'.replace("\\n", "\n"), teleport_render)
            self.assertIn("Vector(1.500, 1, 0)", source)
            self.assertIn("Vector(-1.500, 1, 0)", source)
            self.assertIn("Vector(0, 1, 1.500)", source)
            self.assertIn("Vector(0, 1, -1.500)", source)
            self.assertIn("Event Player.PosisiBangkitAman += Vector(0, 0.500, 0);", source)
            self.assertIn("Vector(0, 2.750, 0)", source)
            self.assertIn("Vector(1.500, 1.000, 0)", source)
            self.assertIn("Vector(-1.500, 1.000, 0)", source)
            dummy_spawn = source.split(f'{rule_kw}("03f - Bot/Dummy: Teleport dari ruang spawn ke objektif")', 1)[1].split(f'{rule_kw}("03g - Bot/Dummy', 1)[0]
            self.assertIn("Call Subroutine(CariPosisiTeleportAman);", dummy_spawn)
            self.assertIn("Teleport(Event Player, Event Player.PosisiBangkitAman);", dummy_spawn)

            interact = source.split(f'{rule_kw}("19e - Teleportasi Jongkok: Interact menjalankan halaman aktif")', 1)[1].split(f'{rule_kw}("19f - Teleportasi Jongkok', 1)[0]
            self.assertEqual(interact.count("Kill(Event Player, Null);"), 1)
            self.assertIn("Clear Status(Event Player, Unkillable);", interact)
            self.assertIn("Set Damage Received(Event Player, 100);", interact)
            self.assertNotIn("Wait(", interact)
            self.assertNotIn("Loop;", interact)
            self.assertNotIn("BunuhDiriDiminta", source)

            fast = source.split(f'{rule_kw}("89a - Subrutin: Proses status cepat pemain")', 1)[1].split(f'{rule_kw}("89b - Subrutin: Proses siklus pemain 10 Hz")', 1)[0]
            self.assertNotIn("BunuhDiriDiminta", fast)
            self.assertEqual(fast.count("Kill("), 1)
            self.assertIn(f"Kill({global_name}.PemainAktif, {global_name}.PemainAktif.KematianBalasDendam == True ?", fast)
            self.assertEqual(source.count("Kill("), 2)

    def test_crouch_attach_uses_native_attach_and_crouch_reload_detach(self):
        for source, rule_kw in ((self.it, "regola"), (self.en, "rule")):
            self.assertIn("Attach Players(Event Player, Event Player.TargetLampiranTeleportasi, Vector(0,", source)
            self.assertIn("+ 0.750, 0));", source)
            self.assertIn("Detach Players(Event Player);", source)
            attach_rule = source.split(f'{rule_kw}("19e - Teleportasi Jongkok: Interact menjalankan halaman aktif")', 1)[1].split(f'{rule_kw}("19f - Teleportasi Jongkok', 1)[0]
            detach_rules = source.split(f'{rule_kw}("19f - Teleportasi Jongkok: Reload melepas lampiran")', 1)[1].split(f'{rule_kw}("19g - Teleportasi Jongkok', 1)[0]
            manual_detach = detach_rules.split(f'{rule_kw}("19h - Teleportasi Jongkok', 1)[0]
            self.assertIn("Event Player.MenuTerbuka == False;", manual_detach)
            self.assertIn("Is Button Held(Event Player, Button(Crouch)) == True;", manual_detach)
            self.assertIn("Is Button Held(Event Player, Button(Reload)) == True;", manual_detach)
            self.assertNotIn("Event Player.TeleportasiJongkokAktif == False;", manual_detach)
            self.assertNotIn("Disallow Button(Event Player, Button(Reload));", attach_rule)
            self.assertNotIn("Allow Button(Event Player, Button(Reload));", detach_rules)
            self.assertIn("CROUCH + RELOAD: DETACH", source)
            self.assertIn("99: TargetLampiranTeleportasi", source)
            self.assertIn("100: LampiranTeleportasiAktif", source)

    def test_crouch_attach_auto_detaches_on_death_leave_or_hero_change(self):
        for source in (self.it, self.en):
            self.assertIn("Entity Exists(Event Player.TargetLampiranTeleportasi) == False", source)
            self.assertIn("Is Alive(Event Player.TargetLampiranTeleportasi) == False", source)
            self.assertIn("Hero Of(Event Player) != Event Player.PahlawanLampiranSendiri", source)
            self.assertIn("Hero Of(Event Player.TargetLampiranTeleportasi) != Event Player.PahlawanLampiranTarget", source)

    def test_jump_resurrect_always_has_non_aborting_fallbacks(self):
        for source in (self.it, self.en):
            self.assertNotIn("No safe resurrection position was found.", source)
            self.assertNotIn("Tidak ada posisi bangkit yang aman.", source)
            self.assertIn("Event Player.PosisiBangkitAman = Nearest Walkable Position(Event Player.PosisiMati);", source)
            self.assertIn("Event Player.PosisiBangkitAman = Nearest Walkable Position(Position Of(First Of(Spawn Points(Team Of(Event Player)))));", source)
            self.assertIn("Event Player.PosisiBangkitAman = Event Player.PosisiMati;", source)
            self.assertIn("Resurrect(Event Player);\n\t\tTeleport(Event Player, Event Player.PosisiBangkitAman);", source)


    def test_custom_string_uses_at_most_three_substitution_values(self):
        for source in (self.it, self.en):
            self.assertNotIn("{3}", source)
            self.assertIn('Custom String("{0}\\n{1}", Custom String("Hold CROUCH + command', source)



    def test_team_switch_is_lightweight_and_leave_cleanup_is_exact(self):
        for source, global_name, rule_kw in ((self.it, "Globale", "regola"), (self.en, "Global", "rule")):
            self.assertNotIn(f'{rule_kw}("01 - Siklus tim: Pekerja pembersihan dari penjadwal global")', source)

            fast = source.split(f'{rule_kw}("89a - Subrutin: Proses status cepat pemain")', 1)[1].split(f'{rule_kw}("89b - Subrutin: Proses siklus pemain 10 Hz")', 1)[0]
            self.assertIn(f"Array Contains({global_name}.PemainManusia, {global_name}.PemainAktif) == True", fast)
            self.assertIn(f"{global_name}.PemainAktif.TimTerakhir != Team Of({global_name}.PemainAktif)", fast)
            self.assertIn(f"{global_name}.PemainAktif.TimTerakhir = Team Of({global_name}.PemainAktif);", fast)
            self.assertIn(f"{global_name}.PemainAktif.Manusia = True;", fast)
            self.assertIn(f"{global_name}.PemainAktif.SudahDiperiksa = True;", fast)
            self.assertIn(f"{global_name}.PemainAktif.SudahSiap = True;", fast)
            self.assertIn(f"{global_name}.PemainAktif.PernahDisiapkan = True;", fast)
            self.assertIn(
                f'If(Custom String("{{0}}", {global_name}.PemainAktif) == Custom String("งูแท้"));',
                fast,
            )
            self.assertIn(
                f'{global_name}.PemainAktif.MusikKhusus = Custom String("Caladan Brood");',
                fast,
            )
            classifier = source.split(f'{rule_kw}("02 - Pemain: Pisahkan manusia dari pasukan kaleng")', 1)[1].split(f'{rule_kw}("02b - HUD Pemain', 1)[0]
            self.assertIn(f"Array Contains({global_name}.PemainManusia, Event Player) == False;", classifier)
            self.assertIn(f"If(Count Of({global_name}.SlotHUDTersedia) == 0);", classifier)
            self.assertIn("Event Player.SudahDiperiksa = False;", classifier)
            self.assertIn("Event Player.SudahSiap = False;", classifier)
            self.assertIn("Event Player.PindahTimDiproses = False;", classifier)
            self.assertIn(f"If({global_name}.PemainSiklusGlobal == Event Player);", classifier)
            self.assertIn(f"{global_name}.PemainSiklusGlobal = Null;", classifier)
            self.assertIn(f"{global_name}.WaktuSiklusGlobal = Total Time Elapsed + 0.250;", classifier)
            self.assertNotIn(f"Abort If(Count Of({global_name}.SlotHUDTersedia) == 0);", classifier)
            self.assertNotIn("Server Load < 150", classifier)
            self.assertLess(
                classifier.index("Call Subroutine(KunciBot);"),
                classifier.index(f"If(Count Of({global_name}.SlotHUDTersedia) == 0);"),
            )
            self.assertIn(f"Disable Game Mode HUD({global_name}.PemainAktif);", fast)
            self.assertIn(f"Disable Game Mode In-World UI({global_name}.PemainAktif);", fast)
            self.assertIn(f"{global_name}.PemainAktif.SegarkanRosterTertunda = True;", fast)
            self.assertIn(f"{global_name}.PemainAktif.SegarkanRosterTertunda == True", fast)
            self.assertIn(f"{global_name}.PemainAktif.WaktuSiklusTim = Total Time Elapsed + 0.250;", fast)
            self.assertIn(f"Total Time Elapsed >= {global_name}.PemainAktif.WaktuSiklusTim", fast)
            self.assertIn(f"Has Spawned({global_name}.PemainAktif) == True", fast)
            self.assertIn(f"Is Alive({global_name}.PemainAktif) == True", fast)
            self.assertIn(f"Destroy HUD Text({global_name}.HudKiriPemain[", fast)
            self.assertIn(f"Destroy HUD Text({global_name}.HudKananPemain[", fast)
            self.assertNotIn(f"Destroy HUD Text({global_name}.PemainAktif.HudKiri);", fast)
            self.assertNotIn(f"Destroy HUD Text({global_name}.PemainAktif.HudKanan);", fast)
            self.assertNotIn(f"Destroy HUD Text({global_name}.PemainAktif.HudMenu);", fast)
            self.assertIn(f"Destroy HUD Text({global_name}.HudMenuPemain[", fast)
            self.assertIn(f"{global_name}.PemainAktif.HudKiri = Null;", fast)
            self.assertIn(f"{global_name}.PemainAktif.HudKanan = Null;", fast)
            self.assertIn(f"{global_name}.PemainAktif.HudPemainDibuat = False;", fast)
            self.assertIn(f"{global_name}.PemainAktif.SegarkanRosterTertunda = False;", fast)
            self.assertIn(
                f"Array Contains({global_name}.PemainManusia, {global_name}.PemainAktif) == False, "
                f"{global_name}.PemainAktif.SegarkanRosterTertunda == True",
                fast,
            )
            self.assertIn(f"{global_name}.HudKiriPemain[Index Of Array Value({global_name}.PemainManusia, {global_name}.PemainAktif)] = 0;", fast)
            self.assertIn(f"{global_name}.HudKananPemain[Index Of Array Value({global_name}.PemainManusia, {global_name}.PemainAktif)] = 0;", fast)
            self.assertIn(f"{global_name}.PemainAktif.SeranganDekatDipakai = False;", fast)
            self.assertIn(f"{global_name}.PemainAktif.MenuTerbuka = False;", fast)
            self.assertIn(f"{global_name}.PemainAktif.PerintahMenu = 0;", fast)
            self.assertIn(f"{global_name}.PemainAktif.InputMenuDikunci = False;", fast)
            self.assertIn(f"{global_name}.PemainAktif.InteraksiKameraDipakai = False;", fast)
            self.assertIn(f"{global_name}.PemainAktif.TeleportasiJongkokAktif = False;", fast)
            self.assertIn(f"Allow Button({global_name}.PemainAktif, Button(Melee));", fast)
            self.assertIn(f"Allow Button({global_name}.PemainAktif, Button(Interact));", fast)
            self.assertIn(f"{global_name}.PemainAktif.PindahTimDiproses = False;", fast)
            self.assertIn(f"Array Contains({global_name}.PemainManusia, {global_name}.PemainAktif) == False", fast)
            self.assertIn(f"{global_name}.PemainAktif.PindahTimDiproses = True;", fast)
            self.assertNotIn("Server Load < 150", fast)
            self.assertNotIn("Call Subroutine(BersihkanPemain);", fast)
            setup_worker = source.split(f'{rule_kw}("01b - Siklus tim: Pekerja penyiapan dari penjadwal global")', 1)[1].split(f'{rule_kw}("02 - Pemain', 1)[0]
            self.assertNotIn("Server Load < 150", setup_worker)
            self.assertNotIn("Call Subroutine(SiapkanPemain);", fast)

            roster_hud = source.split(f'{rule_kw}("02b - HUD Pemain', 1)[1].split(f'{rule_kw}("03c - Bot/Dummy', 1)[0]
            self.assertNotIn("Is Alive(Event Player) == True;", roster_hud)
            self.assertNotIn("Server Load < 150", roster_hud)
            self.assertIn("Event Player.TimTerakhir == Team Of(Event Player);", roster_hud)
            self.assertIn("Event Player.SegarkanRosterTertunda == False;", roster_hud)
            self.assertGreater(
                roster_hud.index("Event Player.HudPemainDibuat = True;"),
                roster_hud.index(f"{global_name}.HudKananPemain[Index Of Array Value({global_name}.PemainManusia, Event Player)] = Event Player.HudKanan;"),
            )
            self.assertEqual(
                source.count("Player Variable(Current Array Element, SegarkanRosterTertunda) == False"),
                2,
            )

            setup = source.split(f'{rule_kw}("01b - Siklus tim: Pekerja penyiapan dari penjadwal global")', 1)[1].split(f'{rule_kw}("02 - Pemain: Pisahkan manusia dari pasukan kaleng")', 1)[0]
            self.assertIn(f"Array Contains({global_name}.PemainManusia, Event Player) == False;", setup)
            self.assertIn("Call Subroutine(TenangkanPemain);", setup)
            self.assertIn("Call Subroutine(SiapkanPemain);", setup)
            self.assertNotIn("Call Subroutine(BersihkanPemain);", setup)

            left = source.split(f'{rule_kw}("04 - Pemain Keluar: Bersihkan hanya saat benar-benar keluar")', 1)[1].split(f'{rule_kw}("04g - Utama global: Penjadwal pusat 20 Hz")', 1)[0]
            self.assertIn("Wait(0.500,", left)
            self.assertIn("Abort If(Entity Exists(Event Player) == True);", left)
            self.assertNotIn("Call Subroutine(TenangkanPemain);", left)
            self.assertIn("Call Subroutine(BersihkanPemain);", left)

            cleanup = source.split(f'{rule_kw}("93c - Subrutin: Bersihkan referensi pemain yang benar-benar keluar")', 1)[1].split(f'{rule_kw}("94 - Subrutin: Siapkan pemain', 1)[0]
            self.assertIn(f"{global_name}.PemainPembersihan = Event Player;", cleanup)
            self.assertIn(f"{global_name}.IndeksKeluar = Index Of Array Value({global_name}.PemainManusia, {global_name}.PemainPembersihan);", cleanup)
            self.assertNotIn("Index Of Array Value(" + global_name + ".SlotHUDPemain", cleanup)
            self.assertNotIn("For Global Variable(", cleanup)
            self.assertNotIn("Filtered Array(", cleanup)
            self.assertNotIn("Allow Button(", cleanup)
            self.assertNotIn("Clear Status(", cleanup)
            self.assertNotIn("Set Move Speed(", cleanup)
            self.assertIn("Remove From Array By Index", cleanup)


if __name__ == "__main__":
    unittest.main()
