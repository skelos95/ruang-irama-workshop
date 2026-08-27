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
            self.assertIn("63: PemainSlotHUD", source)
            self.assertIn("64: NamaSlotHUD", source)

            classifier = source.split(f'{rule_kw}("02 - Pemain: Pisahkan manusia dari pasukan kaleng")', 1)[1].split(f'{rule_kw}("02b - HUD Pemain', 1)[0]
            self.assertIn('Event Player.NamaTampilan = Evaluate Once(Custom String("{0}", Event Player));', classifier)
            self.assertIn(f'{global_name}.PemainSlotHUD[Event Player.UrutanHUD] = Event Player;', classifier)
            self.assertIn(f'{global_name}.NamaSlotHUD[Event Player.UrutanHUD] = Event Player.NamaTampilan;', classifier)

            roster = source.split(f'{rule_kw}("02b - HUD Pemain: Hubungkan ke slot global")', 1)[1].split(f'{rule_kw}("03c - Bot/Dummy', 1)[0]
            slot = 'Evaluate Once(Event Player.UrutanHUD)'
            self.assertIn(f'{global_name}.NamaSlotHUD[{slot}] != Custom String("")', roster)
            self.assertIn(f'Custom String("{{0}} - {{1}} MIN", {global_name}.NamaSlotHUD[{slot}]', roster)
            self.assertIn(f'Custom String("{{0}} - {{1}}", {global_name}.NamaSlotHUD[{slot}]', roster)
            self.assertIn(f'{global_name}.PemainSlotHUD[{slot}]', roster)
            self.assertIn(f'{global_name}.HudKiriPemain[Event Player.UrutanHUD] = Last Text ID;', roster)
            self.assertIn(f'{global_name}.HudKananPemain[Event Player.UrutanHUD] = Last Text ID;', roster)

            inspect = source.split(f'{rule_kw}("13 - Intip Pahlawan: Nama mengikuti target bidikan tanpa Wait")', 1)[1].split(f'{rule_kw}("16a - Anran', 1)[0]
            self.assertIn(f'{global_name}.NamaSlotHUD[Player Variable(Event Player.TargetInspeksi, UrutanHUD)]', inspect)

            teleport = source.split(f'{rule_kw}("19d - Teleportasi Jongkok: Buat ulang nama saat target berubah")', 1)[1].split(f'{rule_kw}("19e - Teleportasi Jongkok', 1)[0]
            self.assertIn(f'{global_name}.NamaSlotHUD[Player Variable(Event Player.CalonTargetTeleportasi, UrutanHUD)]', teleport)

            fast = source.split(f'{rule_kw}("89a - Subrutin: Proses status cepat pemain")', 1)[1].split(f'{rule_kw}("89b - Subrutin', 1)[0]
            cache_invalid = f'Or({global_name}.PemainAktif.NamaTampilan == Null, {global_name}.PemainAktif.NamaTampilan == Custom String(""))'
            self.assertIn(cache_invalid, fast)
            self.assertIn(f'{global_name}.NamaSlotHUD[{global_name}.PemainAktif.UrutanHUD] != Custom String("")', fast)
            self.assertIn(f'{global_name}.PemainAktif.NamaTampilan = {global_name}.NamaSlotHUD[{global_name}.PemainAktif.UrutanHUD];', fast)
            self.assertIn(f'Custom String("{{0}}", {global_name}.PemainAktif) != Custom String("")', fast)
            self.assertIn(f'{global_name}.PemainAktif.NamaTampilan = Evaluate Once(Custom String("{{0}}", {global_name}.PemainAktif));', fast)
            self.assertLess(fast.index(cache_invalid), fast.index(f"{global_name}.PemainAktif.TimTerakhir != Team Of({global_name}.PemainAktif)"))

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



    def test_roster_is_owned_by_persistent_global_hud_slots(self):
        for source, global_name, rule_kw in ((self.it, "Globale", "regola"), (self.en, "Global", "rule")):
            self.assertIn("63: PemainSlotHUD", source)
            self.assertIn("64: NamaSlotHUD", source)
            self.assertIn(f"{global_name}.PemainSlotHUD = Array(Null, Null, Null, Null, Null, Null, Null, Null, Null, Null, Null, Null);", source)
            self.assertNotIn(f'{rule_kw}("00b - HUD Roster: Dua belas slot global permanen")', source)
            zeros = "Array(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)"
            self.assertIn(f"{global_name}.HudKiriPemain = {zeros};", source)
            self.assertIn(f"{global_name}.HudKananPemain = {zeros};", source)

            player_bind = source.split(f'{rule_kw}("02b - HUD Pemain: Hubungkan ke slot global")', 1)[1].split(f'{rule_kw}("03c - Bot/Dummy', 1)[0]
            self.assertEqual(player_bind.count("Create HUD Text("), 2)
            self.assertIn("Event Player.NamaTampilan != Null;", player_bind)
            self.assertIn('Event Player.NamaTampilan != Custom String("");', player_bind)
            self.assertIn(f"{global_name}.PemainSlotHUD[Event Player.UrutanHUD] == Event Player;", player_bind)
            self.assertIn(f"{global_name}.HudKiriPemain[Event Player.UrutanHUD] = Last Text ID;", player_bind)
            self.assertIn(f"{global_name}.HudKananPemain[Event Player.UrutanHUD] = Last Text ID;", player_bind)
            self.assertIn(f"Event Player.HudKiri = {global_name}.HudKiriPemain[Event Player.UrutanHUD];", player_bind)
            self.assertIn(f"Event Player.HudKanan = {global_name}.HudKananPemain[Event Player.UrutanHUD];", player_bind)
            self.assertIn(f"Destroy HUD Text({global_name}.HudKiriPemain[{global_name}.IndeksUtangKeluar]);", source)
            self.assertIn(f"Destroy HUD Text({global_name}.HudKananPemain[{global_name}.IndeksUtangKeluar]);", source)

            self.assertIn(f"{global_name}.PemainSlotHUD[Event Player.UrutanHUD] = Event Player;", source)
            self.assertIn(f"{global_name}.NamaSlotHUD[Event Player.UrutanHUD] = Event Player.NamaTampilan;", source)
            self.assertNotIn("Modify Global Variable(HudKiriPemain, Remove From Array By Index", source)
            self.assertNotIn("Modify Global Variable(HudKananPemain, Remove From Array By Index", source)
            self.assertIn(f"{global_name}.PemainSlotHUD[{global_name}.IndeksUtangKeluar] = Null;", source)
            self.assertIn(f'{global_name}.NamaSlotHUD[{global_name}.IndeksUtangKeluar] = Custom String("");', source)
            self.assertIn(f"{global_name}.PemainSlotHUD[{global_name}.PemainPengganti.UrutanHUD] = {global_name}.PemainPengganti;", source)
            self.assertIn(f"{global_name}.PemainPengganti.NamaTampilan = {global_name}.NamaSlotHUD[{global_name}.PemainPengganti.UrutanHUD];", source)
            self.assertIn(f"{global_name}.NamaSlotHUD[Player Variable(Event Player.TargetInspeksi, UrutanHUD)]", source)
            self.assertIn(f"{global_name}.NamaSlotHUD[Player Variable(Event Player.CalonTargetTeleportasi, UrutanHUD)]", source)

    def test_roster_bootstrap_depends_only_on_persistent_slot_identity(self):
        for source, global_name, rule_kw in ((self.it, "Globale", "regola"), (self.en, "Global", "rule")):
            roster = source.split(f'{rule_kw}("02b - HUD Pemain: Hubungkan ke slot global")', 1)[1].split(f'{rule_kw}("03c - Bot/Dummy', 1)[0]
            self.assertNotIn("Has Spawned(Event Player) == True;", roster)
            self.assertNotIn("Event Player.TimTerakhir == Team Of(Event Player);", roster)
            self.assertNotIn("Event Player.SegarkanRosterTertunda == False;", roster)
            self.assertNotIn("Event Player.NamaTampilan != Null;", roster)
            self.assertIn(f"{global_name}.PemainSlotHUD[Event Player.UrutanHUD] == Event Player;", roster)
            self.assertIn(f'{global_name}.NamaSlotHUD[Event Player.UrutanHUD] != Custom String("");', roster)
            self.assertIn("Event Player.UrutanHUD < 12;", roster)
            self.assertIn("Event Player.HudPemainDibuat == False", roster)
            self.assertEqual(roster.count("Create HUD Text("), 2)

    def test_registered_team_switch_never_destroys_roster_or_hides_crouch_target(self):
        for source, global_name, rule_kw in ((self.it, "Globale", "regola"), (self.en, "Global", "rule")):
            fast = source.split(f'{rule_kw}("89a - Subrutin: Proses status cepat pemain")', 1)[1].split(f'{rule_kw}("89b - Subrutin: Proses siklus pemain 10 Hz")', 1)[0]
            self.assertIn(f"{global_name}.PemainAktif.TimTerakhir != Team Of({global_name}.PemainAktif)", fast)
            self.assertIn(f"{global_name}.PemainAktif.SegarkanRosterTertunda = False;", fast)
            self.assertNotIn(f"{global_name}.PemainAktif.SegarkanRosterTertunda = True;", fast)
            self.assertNotIn(f"{global_name}.PemainAktif.HudPemainDibuat = False;", fast)
            self.assertNotIn(f"Destroy HUD Text({global_name}.HudKiriPemain[", fast)
            self.assertNotIn(f"Destroy HUD Text({global_name}.HudKananPemain[", fast)
            self.assertEqual(source.count("Player Variable(Current Array Element, SegarkanRosterTertunda) == False"), 0)
            roster = source.split(f'{rule_kw}("02b - HUD Pemain', 1)[1].split(f'{rule_kw}("03c - Bot/Dummy', 1)[0]
            self.assertIn("Event Player.SegarkanRosterTertunda == False;", roster)

    def test_team_switch_is_lightweight_and_leave_cleanup_is_exact(self):
        for source, global_name, rule_kw in ((self.it, "Globale", "regola"), (self.en, "Global", "rule")):
            fast = source.split(f'{rule_kw}("89a - Subrutin: Proses status cepat pemain")', 1)[1].split(f'{rule_kw}("89b - Subrutin: Proses siklus pemain 10 Hz")', 1)[0]
            for token in (
                f"Array Contains({global_name}.PemainManusia, {global_name}.PemainAktif) == True",
                f"{global_name}.PemainAktif.TimTerakhir != Team Of({global_name}.PemainAktif)",
                f"{global_name}.PemainAktif.TimTerakhir = Team Of({global_name}.PemainAktif);",
                f"{global_name}.PemainAktif.Manusia = True;",
                f"{global_name}.PemainAktif.SudahDiperiksa = True;",
                f"{global_name}.PemainAktif.SudahSiap = True;",
                f"{global_name}.PemainAktif.PernahDisiapkan = True;",
                f"{global_name}.PemainAktif.SegarkanRosterTertunda = False;",
                f"Disable Game Mode HUD({global_name}.PemainAktif);",
                f"Disable Game Mode In-World UI({global_name}.PemainAktif);",
            ):
                self.assertIn(token, fast)
            for token in (
                f"{global_name}.PemainAktif.SegarkanRosterTertunda = True;",
                f"Destroy HUD Text({global_name}.HudKiriPemain[",
                f"Destroy HUD Text({global_name}.HudKananPemain[",
                f"{global_name}.PemainAktif.HudKiri = Null;",
                f"{global_name}.PemainAktif.HudKanan = Null;",
                f"{global_name}.PemainAktif.HudPemainDibuat = False;",
                "Call Subroutine(BersihkanPemain);",
                "Call Subroutine(SiapkanPemain);",
            ):
                self.assertNotIn(token, fast)

            classifier = source.split(f'{rule_kw}("02 - Pemain: Pisahkan manusia dari pasukan kaleng")', 1)[1].split(f'{rule_kw}("02b - HUD Pemain', 1)[0]
            self.assertIn(f"Array Contains({global_name}.PemainManusia, Event Player) == False;", classifier)
            self.assertIn(f"If(Count Of({global_name}.SlotHUDTersedia) == 0);", classifier)
            self.assertNotIn("Server Load < 150", classifier)

            roster = source.split(f'{rule_kw}("02b - HUD Pemain', 1)[1].split(f'{rule_kw}("03c - Bot/Dummy', 1)[0]
            self.assertIn("Event Player.TimTerakhir == Team Of(Event Player);", roster)
            self.assertIn("Event Player.SegarkanRosterTertunda == False;", roster)
            self.assertNotIn("Is Alive(Event Player) == True;", roster)
            self.assertNotIn("Server Load < 150", roster)

            left = source.split(f'{rule_kw}("04 - Pemain Keluar: Bersihkan hanya saat benar-benar keluar")', 1)[1].split(f'{rule_kw}("05 - ', 1)[0]
            self.assertIn("Wait(0.500, Ignora condizione);" if global_name == "Globale" else "Wait(0.500, Ignore Condition);", left)
            self.assertIn("Call Subroutine(BersihkanPemain);", left)
            self.assertIn(f"{global_name}.PemainManusia[{global_name}.IndeksKeluar] = {global_name}.PemainPengganti;", left)

