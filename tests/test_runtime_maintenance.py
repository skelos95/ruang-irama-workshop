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
            self.assertIn("104: NamaTampilan", source)

            classifier = source.split(f'{rule_kw}("02 - Pemain: Pisahkan manusia dari pasukan kaleng")', 1)[1].split(f'{rule_kw}("03c - Bot/Dummy', 1)[0]
            name_guard = "If(Or(Event Player.PernahDisiapkan == False, Or(Event Player.NamaTampilan == Null, Event Player.NamaTampilan == Custom String(\"\"))));"
            name_assign = 'Event Player.NamaTampilan = Evaluate Once(Custom String("{0}", Event Player));'
            empty_guard = 'If(Or(Event Player.NamaTampilan == Null, Event Player.NamaTampilan == Custom String("")));'
            self.assertIn(name_guard, classifier)
            self.assertIn(name_assign, classifier)
            self.assertIn(empty_guard, classifier)
            self.assertLess(classifier.index(name_guard), classifier.index(name_assign))
            self.assertLess(classifier.index(name_assign), classifier.index(empty_guard))
            self.assertIn('Event Player.NamaTampilan = Evaluate Once(Custom String("{0}", Event Player));', classifier)

            roster = source.split(f'{rule_kw}("02 - Pemain: Pisahkan manusia dari pasukan kaleng")', 1)[1].split(f'{rule_kw}("03c - Bot/Dummy', 1)[0]
            self.assertIn(
                'And(Event Player.NamaTampilan != Null, Event Player.NamaTampilan != Custom String(""))',
                roster,
            )
            self.assertNotIn('MenitLobi', source)
            self.assertNotIn('WaktuMasuk', source)
            self.assertIn('Custom String("{0} - {1}", Evaluate Once(Event Player.NamaTampilan),', roster)

            inspect = source.split(f'{rule_kw}("13 - Intip Pahlawan: Nama mengikuti target bidikan")', 1)[1].split(f'{rule_kw}("16a - Anran', 1)[0]
            self.assertIn("Player Variable(Event Player.TargetInspeksi, NamaTampilan)", inspect)
            self.assertIn(
                f"Array Contains({global_name}.PemainManusia, Event Player.TargetInspeksi) == True",
                inspect,
            )
            self.assertIn(
                f'Evaluate Once(Array Contains({global_name}.PemainManusia, '
                'Event Player.TargetInspeksi) == True ? '
                'Player Variable(Event Player.TargetInspeksi, NamaTampilan) : '
                'Custom String("{0}", Is Duplicating(Event Player.TargetInspeksi) ? '
                'Hero Being Duplicated(Event Player.TargetInspeksi) : '
                'Hero Of(Event Player.TargetInspeksi)))',
                inspect,
            )
            self.assertNotIn(
                'Custom String("{0}", Event Player.TargetInspeksi))',
                inspect,
            )
            self.assertIn(
                f"Evaluate Once(Array Contains({global_name}.PemainManusia, "
                "Event Player.TargetInspeksi) == True ? "
                "Player Variable(Event Player.TargetInspeksi, WarnaNama)",
                inspect,
            )
            self.assertNotIn(
                "Player Variable(Event Player.TargetInspeksi, Manusia) == True ? "
                "Player Variable(Event Player.TargetInspeksi, NamaTampilan)",
                inspect,
            )

            teleport = source.split(f'{rule_kw}("19d - Teleportasi Jongkok: Buat ulang nama saat target berubah")', 1)[1].split(f'{rule_kw}("19e - Teleportasi Jongkok', 1)[0]
            self.assertIn("Player Variable(Event Player.CalonTargetTeleportasi, NamaTampilan)", teleport)
            self.assertIn(
                f"Array Contains({global_name}.PemainManusia, Event Player.CalonTargetTeleportasi) == True",
                teleport,
            )
            self.assertIn(
                f'Evaluate Once(Array Contains({global_name}.PemainManusia, '
                'Event Player.CalonTargetTeleportasi) == True ? '
                'Player Variable(Event Player.CalonTargetTeleportasi, NamaTampilan) : '
                'Custom String("{0}", Is Duplicating(Event Player.CalonTargetTeleportasi) ? '
                'Hero Being Duplicated(Event Player.CalonTargetTeleportasi) : '
                'Hero Of(Event Player.CalonTargetTeleportasi)))',
                teleport,
            )
            self.assertNotIn(
                'Custom String("{0}", Event Player.CalonTargetTeleportasi))',
                teleport,
            )
            self.assertIn(
                f"Evaluate Once(Array Contains({global_name}.PemainManusia, "
                "Event Player.CalonTargetTeleportasi) == True ? "
                "Player Variable(Event Player.CalonTargetTeleportasi, WarnaNama)",
                teleport,
            )
            self.assertNotIn(
                "Player Variable(Event Player.CalonTargetTeleportasi, Manusia) == True ? "
                "Player Variable(Event Player.CalonTargetTeleportasi, NamaTampilan)",
                teleport,
            )

            vision = source.split(f'{rule_kw}("18i - Nasib: Visi', 1)[1].split(f'{rule_kw}("18j - Nasib: Bersihkan nama visi', 1)[0]
            self.assertIn(
                'Event Player.Manusia == True ? Event Player.NamaTampilan : Custom String("{0}", Event Player)',
                vision,
            )

            fast = source.split(f'{rule_kw}("89a - Subrutin: Proses status cepat pemain")', 1)[1].split(f'{rule_kw}("89b - Subrutin', 1)[0]
            cache_invalid = f'Or({global_name}.PemainAktif.NamaTampilan == Null, {global_name}.PemainAktif.NamaTampilan == Custom String("") )'.replace('"") )', '""))')
            self.assertIn(cache_invalid, fast)
            self.assertIn(f'Custom String("{{0}}", {global_name}.PemainAktif) != Custom String("")', fast)
            self.assertIn(f'{global_name}.PemainAktif.NamaTampilan = Evaluate Once(Custom String("{{0}}", {global_name}.PemainAktif));', fast)
            self.assertEqual(
                fast.count(
                    f'{global_name}.PemainAktif.NamaTampilan = Evaluate Once(Custom String("{{0}}", {global_name}.PemainAktif));'
                ),
                1,
            )
            self.assertLess(fast.index(cache_invalid), fast.index(f"{global_name}.PemainAktif.Manusia = True;"))

    def test_aim_scans_are_scheduler_cached(self):
        for source, rule_kw, global_name in ((self.it, "regola", "Globale"), (self.en, "rule", "Global")):
            inspect = source.split(f'{rule_kw}("13 - Intip Pahlawan: Nama mengikuti target bidikan")', 1)[1].split(f'{rule_kw}("16a - Anran', 1)[0]
            self.assertNotIn("Sorted Array(Filtered Array", inspect)
            self.assertIn("CalonTargetInspeksi", inspect)
            self.assertNotIn("19d0 - Teleportasi Jongkok", source)
            scheduler = source.split(f'{rule_kw}("89b - Subrutin: Proses siklus pemain 10 Hz")', 1)[1].split(f'{rule_kw}("89c - Subrutin', 1)[0]
            self.assertIn("CalonTargetInspeksi", scheduler)
            self.assertIn("CalonTargetTeleportasi", scheduler)
            self.assertIn(f"Call Subroutine(SegarkanTargetPublikAktif);", scheduler)

    def test_safe_position_validator_is_shared_by_player_teleports(self):
        for source in (self.it, self.en):
            self.assertRegex(source, r"(?m)^\s*\d+: CariPosisiTeleportasiAman$")
            self.assertGreaterEqual(source.count("Call Subroutine(CariPosisiTeleportasiAman);"), 4)
            self.assertIn("Ray Cast Hit Position(Event Player.PosisiTujuanTeleportasi + Vector(0, 1, 0)", source)

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

    def test_native_completion_and_timer_are_bound_to_custom_countdown(self):
        for source, global_name, rule_kw in (
            (self.it, "Globale", "regola"),
            (self.en, "Global", "rule"),
        ):
            self.assertIn("Disable Built-In Game Mode Completion;", source)
            self.assertIn(f"Set Match Time(Max(1, {global_name}.SisaWaktuServer));", source)
            self.assertNotIn("SisaWaktuServer + 5", source)
            self.assertIn("Is Game In Progress == True", source)
            self.assertIn(f"{global_name}.SisaWaktuServer > 0", source)
            scheduler = source.split(
                f'{rule_kw}("04g - Utama global: Penjadwal pusat 20 Hz")', 1
            )[1].split(f'{rule_kw}("05 - Menu:', 1)[0]
            cadence = (
                f"If(And({global_name}.LangkahPenjadwal % 20 == 0, "
                f"{global_name}.MulaiUlangSudahDiminta == False));"
            )
            cadence_position = scheduler.index(cadence)
            sync_position = scheduler.index(
                f"Set Match Time(Max(1, {global_name}.SisaWaktuServer));"
            )
            outer_end = scheduler.index("\n\t\tEnd;", cadence_position)
            self.assertLess(sync_position, outer_end)

    def test_initial_skip_rules_are_bootstrap_only_and_locked_after_match_start(self):
        for source, global_name, rule_kw in (
            (self.it, "Globale", "regola"),
            (self.en, "Global", "rule"),
        ):
            skip_heroes = source.split(
                f'{rule_kw}("00a2 - Umum: Lewati pemilihan pahlawan")', 1
            )[1].split(f'{rule_kw}("00a3 - Umum: Lewati persiapan awal")', 1)[0]
            self.assertIn(f"Count Of({global_name}.PemainManusia) == 0;", skip_heroes)
            self.assertIn(f"{global_name}.PemainSiklusGlobal == Null;", skip_heroes)
            self.assertEqual(skip_heroes.count("Set Match Time(0);"), 1)

            skip_setup = source.split(
                f'{rule_kw}("00a3 - Umum: Lewati persiapan awal")', 1
            )[1].split(
                f'{rule_kw}("00a4 - Umum: Kunci pelewatan fase awal setelah mode berjalan")', 1
            )[0]
            self.assertIn(f"Count Of({global_name}.PemainManusia) == 0;", skip_setup)
            self.assertIn(f"{global_name}.PemainSiklusGlobal == Null;", skip_setup)
            self.assertEqual(skip_setup.count("Set Match Time(0);"), 1)
            self.assertEqual(source.count("Set Match Time(0);"), 2)

            bootstrap_lock = source.split(
                f'{rule_kw}("00a4 - Umum: Kunci pelewatan fase awal setelah mode berjalan")', 1
            )[1].split(
                f'{rule_kw}("00c - Umum: Mulai ulang tepat sekali saat hitung mundur habis")', 1
            )[0]
            for token in (
                "Is Game In Progress == True;",
                f"Or({global_name}.PilihPahlawanDilewati == False, {global_name}.PersiapanDilewati == False) == True;",
                f"{global_name}.PilihPahlawanDilewati = True;",
                f"{global_name}.PersiapanDilewati = True;",
            ):
                self.assertIn(token, bootstrap_lock)

    def test_chill_star_uses_cached_name_and_color_in_a_dedicated_hud(self):
        for source, global_name, rule_kw in (
            (self.it, "Globale", "regola"),
            (self.en, "Global", "rule"),
        ):
            self.assertIn("57: NamaPemimpinPilihan", source)
            self.assertIn("58: WarnaPemimpinPilihan", source)
            self.assertIn(f"{global_name}.NamaPemimpinPilihan = Custom String(\"\");", source)
            self.assertIn(f"{global_name}.WarnaPemimpinPilihan = Custom Color(255, 255, 255, 255);", source)

            init = source.split(f'{rule_kw}("00 - Umum: Siapkan 200 genre, dari rebahan sampai kiamat")', 1)[1].split(
                f'{rule_kw}("00a1 - Umum: Mulai mode segera saat menunggu pemain")', 1
            )[0]
            self.assertIn(
                f"{global_name}.NamaPemimpinPilihan != Custom String(\"\") ?",
                init,
            )
            self.assertIn("Left, 13", init)
            self.assertIn(f"{global_name}.WarnaPemimpinPilihan", init)
            self.assertIn("\\nCHILL STAR: {0}", init)
            self.assertIn("\\nBINTANG CHILL: {0}", init)
            self.assertIn("\\nดาวสายชิล: {0}", init)

            roster = source.split(f'{rule_kw}("02 - Pemain: Pisahkan manusia dari pasukan kaleng")', 1)[1].split(
                f'{rule_kw}("03c - Bot/Dummy', 1
            )[0]
            self.assertNotIn('Custom String("{0}{1}{2}"', roster)
            self.assertNotIn("CHILL STAR:", roster)
            self.assertIn(
                f"9 + Count Of(Filtered Array({global_name}.HudKiriPemain, Current Array Element != 0))",
                roster,
            )

            leader_calc = source.split(f'{rule_kw}("91q - Subrutin: Hitung ulang pilihan dan pemimpin tunggal")', 1)[1].split(
                f'{rule_kw}("93 - Subrutin: Mulai kamera dinamis di bahu kiri")', 1
            )[0]
            self.assertIn(f"{global_name}.NamaPemimpinPilihan = Custom String(\"\");", leader_calc)
            self.assertIn(f"{global_name}.WarnaPemimpinPilihan = Custom Color(255, 255, 255, 255);", leader_calc)
            self.assertIn(f"If({global_name}.PemimpinPilihan != Null);", leader_calc)
            self.assertIn(
                f"{global_name}.NamaPemimpinPilihan = Player Variable({global_name}.PemimpinPilihan, NamaTampilan);",
                leader_calc,
            )
            self.assertIn(
                f"{global_name}.WarnaPemimpinPilihan = Player Variable({global_name}.PemimpinPilihan, WarnaNama);",
                leader_calc,
            )

            color_page = source.split(f'{rule_kw}("99c - Subrutin: Terapkan halaman warna")', 1)[1].split(
                f'{rule_kw}("99d - Subrutin: Terapkan halaman bahasa")', 1
            )[0]
            self.assertIn(f"If({global_name}.PemimpinPilihan == Event Player);", color_page)
            self.assertIn(f"{global_name}.WarnaPemimpinPilihan = Event Player.WarnaNama;", color_page)

    def test_crouch_teleport_has_five_pages_and_single_shot_self_kill(self):
        for source, rule_kw, global_name in ((self.it, "regola", "Globale"), (self.en, "rule", "Global")):
            self.assertIn("KursorTeleportasi %= 5;", source)
            self.assertIn("Event Player.PerintahTeleportasi = 1;", source)
            self.assertIn("Event Player.PerintahTeleportasi = 2;", source)
            self.assertIn("Event Player.PerintahTeleportasi = 3;", source)
            self.assertIn("PerintahTeleportasi == 3;", source)
            self.assertIn("(Event Player.KursorTeleportasi + (Event Player.PerintahTeleportasi == 1 ? 1 : 4)) % 5", source)
            teleport_render = source.split(f'{rule_kw}("91g - Subrutin: Gambar menu teleportasi")', 1)[1].split(f'{rule_kw}("', 1)[0]
            self.assertNotIn("\\", teleport_render)
            self.assertNotIn('Custom String("{0}n{1}"', teleport_render)
            self.assertIn('Custom String("{0}\n{1}", Custom String("HOLD'.replace("\\n", "\n"), teleport_render)
            for token in (
                "1/5 | SPAWN ROOM",
                "2/5 | OBJECTIVE",
                "3/5 | TELEPORT TO PLAYER/BOT",
                '4/5 | ATTACH TO PLAYER/BOT',
                "5/5 | SELF ELIMINATION",
                "1/5 | RUANG MUNCUL",
                "2/5 | OBJEKTIF",
                "3/5 | TELEPORT: PEMAIN/BOT",
                "4/5 | TEMPEL: PEMAIN/BOT",
                "5/5 | ELIMINASI DIRI",
                '1/5 | วาร์ปกลับห้องเกิด',
                '2/5 | วาร์ปใกล้ภารกิจ',
                '3/5 | วาร์ป: ผู้เล่น / บอต',
                "4/5 | เกาะ: ผู้เล่น / บอต",
                "5/5 | กำจัดตัวเอง",
                'NO PUBLIC TARGET AVAILABLE',
                'TAK ADA TARGET PUBLIK',
                'ไม่มีเป้าหมายที่เปิดให้ใช้',
            ):
                self.assertIn(token, teleport_render)
            self.assertIn("Custom Color(190 + X Component Of(Event Player.WarnaMenu) * 0.250", teleport_render)
            self.assertIn("Custom Color(X Component Of(Event Player.WarnaMenu)", teleport_render)
            self.assertIn("Visible To String and Color", teleport_render)
            transition = source.split(f'{rule_kw}("91k - Subrutin: Transisi warna menu tanpa lompatan")', 1)[1].split(f'{rule_kw}("91l - Subrutin', 1)[0]
            for color in (
                "Vector(80, 255, 160)",
                "Vector(65, 225, 255)",
                "Vector(95, 150, 255)",
                "Vector(195, 100, 255)",
                "Vector(255, 85, 135)",
            ):
                self.assertIn(color, transition)
            self.assertIn("Event Player.TeleportasiJongkokAktif == True", transition)
            self.assertIn("Chase Player Variable Over Time(Event Player, WarnaMenu, Event Player.KursorTeleportasi", transition)
            self.assertIn("0.180, Destination and Duration", transition)
            self.assertNotIn("Global.KursorTeleportasi", teleport_render)
            self.assertIn("Vector(1.500, 1, 0)", source)
            self.assertIn("Vector(-1.500, 1, 0)", source)
            self.assertIn("Vector(0, 1, 1.500)", source)
            self.assertIn("Vector(0, 1, -1.500)", source)
            self.assertIn("Event Player.PosisiBangkitAman += Vector(0, 0.500, 0);", source)
            self.assertIn("Vector(0, 2.750, 0)", source)
            self.assertIn("Vector(1.500, 1.000, 0)", source)
            self.assertIn("Vector(-1.500, 1.000, 0)", source)
            dummy_spawn = source.split(f'{rule_kw}("03f - Bot: Teleportasi dari ruang muncul ke objektif")', 1)[1].split(f'{rule_kw}("03g - Bot', 1)[0]
            self.assertIn("Call Subroutine(CariPosisiTeleportasiAman);", dummy_spawn)
            self.assertIn("Teleport(Event Player, Event Player.PosisiBangkitAman);", dummy_spawn)

            interact = source.split(f'{rule_kw}("19e - Teleportasi Jongkok: Interaksi menjalankan halaman aktif")', 1)[1].split(f'{rule_kw}("19f - Teleportasi Jongkok', 1)[0]
            self.assertEqual(interact.count("Kill(Event Player, Null);"), 1)
            self.assertIn("If(Total Time Elapsed >= Event Player.WaktuBunuhDiriBerikut);", interact)
            self.assertIn("Event Player.WaktuBunuhDiriBerikut = Total Time Elapsed + 3;", interact)
            self.assertIn("Round To Integer(Event Player.WaktuBunuhDiriBerikut - Total Time Elapsed, Up)", interact)
            self.assertIn("Clear Status(Event Player, Unkillable);", interact)
            self.assertIn("Set Damage Received(Event Player, 100);", interact)
            self.assertNotIn("Wait(", interact)
            self.assertNotIn("Loop;", interact)
            self.assertNotIn("BunuhDiriDiminta", source)

            fast = source.split(f'{rule_kw}("89a - Subrutin: Proses status cepat pemain")', 1)[1].split(f'{rule_kw}("89b - Subrutin: Proses siklus pemain 10 Hz")', 1)[0]
            self.assertNotIn("BunuhDiriDiminta", fast)
            self.assertEqual(fast.count("Kill("), 1)
            self.assertIn(f"Kill({global_name}.PemainAktif, {global_name}.PemainAktif.KematianBalasDendam == True ?", fast)
        self.assertEqual(source.count("Kill("), 4)

    def test_crouch_attach_auto_detach_reacts_to_invalidating_state(self):
        for source, rule_kw, conditions_kw, actions_kw in (
            (self.it, "regola", "condizioni", "azioni"),
            (self.en, "rule", "conditions", "actions"),
        ):
            auto_detach = source.split(
                f'{rule_kw}("19h - Teleportasi Jongkok: Lepas lampiran saat status berubah")', 1
            )[1].split(f'{rule_kw}("19g - Teleportasi Jongkok', 1)[0]
            conditions = auto_detach.split(f"\t{conditions_kw}\n\t{{", 1)[1].split(
                f"\n\t}}\n\n\t{actions_kw}", 1
            )[0]
            actions = auto_detach.split(f"\t{actions_kw}\n\t{{", 1)[1]

            for token in (
                "Event Player.LampiranTeleportasiAktif == True;",
                "Has Spawned(Event Player) == False",
                "Is Alive(Event Player) == False",
                "Event Player.TargetLampiranTeleportasi == Null",
                "Entity Exists(Event Player.TargetLampiranTeleportasi) == False",
                "Has Spawned(Event Player.TargetLampiranTeleportasi) == False",
                "Is Alive(Event Player.TargetLampiranTeleportasi) == False",
                "Hero Of(Event Player) != Event Player.PahlawanLampiranSendiri",
                "Hero Of(Event Player.TargetLampiranTeleportasi) != Event Player.PahlawanLampiranTarget",
                "Player Variable(Event Player.TargetLampiranTeleportasi, Manusia) == True",
                "Player Variable(Event Player.TargetLampiranTeleportasi, PrivasiInspeksiAktif) == True",
            ):
                self.assertIn(token, conditions)

            self.assertEqual(actions.count("Detach Players(Event Player);"), 1)
            for clear in (
                "Set Player Variable(Event Player, LampiranTeleportasiAktif, False);",
                "Set Player Variable(Event Player, TargetLampiranTeleportasi, Null);",
                "Set Player Variable(Event Player, PahlawanLampiranSendiri, Null);",
                "Set Player Variable(Event Player, PahlawanLampiranTarget, Null);",
            ):
                self.assertEqual(actions.count(clear), 1)
            self.assertNotIn("\t\tIf(", actions)
            self.assertNotIn("Wait(", auto_detach)
            self.assertNotIn("Loop", auto_detach)

    def test_crouch_attach_uses_native_attach_and_crouch_reload_detach(self):
        for source, rule_kw in ((self.it, "regola"), (self.en, "rule")):
            self.assertIn("Attach Players(Event Player, Event Player.TargetLampiranTeleportasi, Vector(0,", source)
            self.assertIn("+ 0.750, 0));", source)
            self.assertIn("Detach Players(Event Player);", source)
            attach_rule = source.split(f'{rule_kw}("19e - Teleportasi Jongkok: Interaksi menjalankan halaman aktif")', 1)[1].split(f'{rule_kw}("19f - Teleportasi Jongkok', 1)[0]
            detach_rules = source.split(f'{rule_kw}("19f - Teleportasi Jongkok: Isi ulang melepas lampiran")', 1)[1].split(f'{rule_kw}("19g - Teleportasi Jongkok', 1)[0]
            manual_detach = detach_rules.split(f'{rule_kw}("19h - Teleportasi Jongkok', 1)[0]
            self.assertIn("Event Player.MenuTerbuka == False;", manual_detach)
            self.assertIn("Is Button Held(Event Player, Button(Crouch)) == True;", manual_detach)
            self.assertIn("Is Button Held(Event Player, Button(Reload)) == True;", manual_detach)
            self.assertNotIn("Event Player.TeleportasiJongkokAktif == False;", manual_detach)
            self.assertNotIn("Disallow Button(Event Player, Button(Reload));", attach_rule)
            self.assertNotIn("Allow Button(Event Player, Button(Reload));", detach_rules)
            self.assertIn("{0} + {1}: DETACH", source)
            self.assertIn("Input Binding String(Button(Crouch))", source)
            self.assertIn("Input Binding String(Button(Reload))", source)
            self.assertNotIn("CROUCH + RELOAD: DETACH", source)
            self.assertIn("96: TargetLampiranTeleportasi", source)
            self.assertIn("97: LampiranTeleportasiAktif", source)

    def test_crouch_attach_auto_detaches_on_death_leave_or_hero_change(self):
        for source in (self.it, self.en):
            self.assertIn("Entity Exists(Event Player.TargetLampiranTeleportasi) == False", source)
            self.assertIn("Is Alive(Event Player.TargetLampiranTeleportasi) == False", source)
            self.assertIn("Hero Of(Event Player) != Event Player.PahlawanLampiranSendiri", source)
            self.assertIn("Hero Of(Event Player.TargetLampiranTeleportasi) != Event Player.PahlawanLampiranTarget", source)

    def test_jump_resurrect_keeps_safe_deaths_in_place_and_recovers_void_deaths(self):
        for source, rule_kw in ((self.it, "regola"), (self.en, "rule")):
            resurrect = source.split(f'{rule_kw}("12f - Bangkit Lompat: Bangkit di posisi aman yang bisa dilalui")', 1)[1].split(f'{rule_kw}("12g - Bangkit Lompat', 1)[0]
            recovery_teleport = "Teleport(Event Player, Event Player.PosisiBangkitAman + Vector(0, 0.500, 0));"
            self.assertIn("Event Player.PosisiBangkitAman = Nearest Walkable Position(Position Of(Event Player));", resurrect)
            self.assertIn("Distance Between(Event Player.PosisiBangkitAman, Event Player.PosisiMati) > 0.500", resurrect)
            self.assertNotIn("Nearest Walkable Position(Event Player.PosisiMati)", resurrect)
            self.assertEqual(resurrect.count("Ray Cast Hit Position(Event Player.PosisiMati + Vector(0, 1, 0), Event Player.PosisiMati - Vector(0, 3, 0)"), 1)
            self.assertNotIn("Call Subroutine(CariPosisiTeleportasiAman);", resurrect)
            self.assertNotIn("Abort;", resurrect)
            self.assertNotIn("Event Player.TeleportasiJongkokAktif == False;", resurrect)
            self.assertNotIn("Spawn Points(Team Of(Event Player))", resurrect)
            self.assertEqual(resurrect.count(recovery_teleport), 2)
            self.assertLess(resurrect.index(recovery_teleport), resurrect.index("Resurrect(Event Player);"))
            self.assertLess(resurrect.index("Resurrect(Event Player);"), resurrect.rindex(recovery_teleport))
            self.assertIn("Event Player.FisikaHantuTerbangDiterapkan = False;", resurrect)
            self.assertIn("Call Subroutine(TerapkanFisikaHantuTerbang);", resurrect)
            self.assertNotIn("Start Forcing Player Position(", source)

    def test_custom_string_uses_at_most_three_substitution_values(self):
        for source in (self.it, self.en):
            self.assertNotIn("{3}", source)
            self.assertIn('Custom String("{0}\\n{1}", Custom String("Hold CROUCH |', source)



    def test_team_switch_uses_full_cleanup_and_leave_cleanup_is_exact(self):
        for source, global_name, rule_kw in ((self.it, "Globale", "regola"), (self.en, "Global", "rule")):
            self.assertNotIn(f'{rule_kw}("01 - Siklus tim: Pekerja pembersihan dari penjadwal global")', source)

            fast = source.split(f'{rule_kw}("89a - Subrutin: Proses status cepat pemain")', 1)[1].split(f'{rule_kw}("89b - Subrutin: Proses siklus pemain 10 Hz")', 1)[0]
            self.assertIn(f"Array Contains({global_name}.PemainManusia, {global_name}.PemainAktif) == True", fast)
            self.assertNotIn(f"{global_name}.PemainAktif.TimTerakhir != Team Of({global_name}.PemainAktif)", fast)
            self.assertIn(f"{global_name}.PemainAktif.Manusia = True;", fast)
            self.assertIn(f"{global_name}.PemainAktif.SudahDiperiksa = True;", fast)
            self.assertIn(f"{global_name}.PemainAktif.SudahSiap = True;", fast)
            self.assertIn(f"{global_name}.PemainAktif.PernahDisiapkan = True;", fast)
            self.assertIn(
                f'If({global_name}.PemainAktif.NamaTampilan == Custom String("งูแรร์"));',
                fast,
            )
            self.assertNotIn(
                f'If(Custom String("{{0}}", {global_name}.PemainAktif) == Custom String("งูแรร์"));',
                fast,
            )
            self.assertIn(
                f'{global_name}.PemainAktif.MusikKhusus = Custom String("Draconian");',
                fast,
            )
            classifier = source.split(f'{rule_kw}("02 - Pemain: Pisahkan manusia dari pasukan kaleng")', 1)[1].split(f'{rule_kw}("03c - Bot/Dummy', 1)[0]
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
            self.assertNotIn("Call Subroutine(TenangkanPemain);", fast)
            self.assertNotIn("Call Subroutine(BersihkanPemain);", fast)
            self.assertIn(f"{global_name}.PemainAktif.SiklusPemainAktif == False", fast)
            switch = source.split(f'{rule_kw}("01a - Siklus tim: Karantina sebelum penyiapan ulang")', 1)[1].split(f'{rule_kw}("01b - Siklus tim:', 1)[0]
            self.assertIn("Ongoing - Each Player;", switch)
            self.assertIn(f"Array Contains({global_name}.PemainManusia, Event Player) == True;", switch)
            self.assertIn("Event Player.TimTerakhir != Team Of(Event Player);", switch)
            self.assertNotIn("Call Subroutine(TenangkanPemain);", switch)
            self.assertNotIn("Call Subroutine(BersihkanPemain);", switch)
            self.assertNotIn("Wait(", switch)
            self.assertNotIn(f"{global_name}.PemainAktif", switch)
            self.assertNotIn(f"{global_name}.PemainAktif.PembaruanDaftarTertunda = True;", fast)
            self.assertIn(f"{global_name}.PemainAktif.WaktuSiklusTim = Total Time Elapsed + 0.250;", fast)
            self.assertIn(f"Has Spawned({global_name}.PemainAktif) == True", fast)
            self.assertIn("Event Player.PembaruanDaftarTertunda = False;", switch)
            self.assertIn("Event Player.PindahTimDiproses = True;", switch)
            self.assertIn("Event Player.SiklusPemainAktif = True;", switch)
            self.assertIn("Event Player.SudahSiap = False;", switch)
            self.assertIn("Event Player.Manusia = False;", switch)
            self.assertIn("Event Player.WaktuSiklusTim = Total Time Elapsed + 0.500;", switch)
            self.assertIn(f"Array Contains({global_name}.PemainManusia, {global_name}.PemainAktif) == False", fast)
            self.assertIn(f"{global_name}.PemainAktif.PindahTimDiproses = True;", fast)
            self.assertNotIn("Server Load < 150", fast)
            setup_worker = source.split(f'{rule_kw}("01b - Siklus tim: Pekerja penyiapan dari penjadwal global")', 1)[1].split(f'{rule_kw}("02 - Pemain', 1)[0]
            self.assertNotIn("Server Load < 150", setup_worker)
            self.assertNotIn("Call Subroutine(SiapkanPemain);", fast)
            self.assertIn(
                f"Or(Array Contains({global_name}.PemainManusia, {global_name}.PemainAktif) == False, {global_name}.PemainAktif.SiklusPemainAktif == True)",
                fast,
            )
            self.assertIn(
                f"{global_name}.PemainAktif.TimSiklusTarget == Team Of({global_name}.PemainAktif)",
                fast,
            )
            self.assertNotIn(f'{rule_kw}("02b - HUD Pemain', source)
            self.assertNotIn(f'{rule_kw}("02x - DEBUG', source)
            self.assertNotIn("DBG 02", source)

            roster_hud = source.split(f'{rule_kw}("02 - Pemain: Pisahkan manusia dari pasukan kaleng")', 1)[1].split(f'{rule_kw}("03c - Bot', 1)[0]
            self.assertNotIn("Is Alive(Event Player) == True;", roster_hud)
            self.assertNotIn("Server Load < 150", roster_hud)
            vote_dirty = f"{global_name}.PilihanPerluDihitung = True;"
            self.assertIn(vote_dirty, roster_hud)
            self.assertIn("Create HUD Text(", roster_hud)
            append_roster = f"{global_name}.PemainManusia = Append To Array({global_name}.PemainManusia, Event Player);"
            left_create = roster_hud.index("Create HUD Text(")
            self.assertEqual(roster_hud.count("Create HUD Text("), 1)
            self.assertLess(roster_hud.index(append_roster), roster_hud.index("Event Player.Manusia = True;"))
            self.assertLess(roster_hud.index("Event Player.Manusia = True;"), roster_hud.index(vote_dirty))
            self.assertLess(
                roster_hud.index(vote_dirty),
                left_create,
            )
            self.assertLess(left_create, roster_hud.index("Event Player.HudKiri = Last Text ID;"))
            self.assertGreater(
                roster_hud.index("Event Player.HudPemainDibuat = True;"),
                roster_hud.index(f"{global_name}.HudKiriPemain[Index Of Array Value({global_name}.PemainManusia, Event Player)] = Event Player.HudKiri;"),
            )
            self.assertLess(
                roster_hud.index("Event Player.HudPemainDibuat = True;"),
                roster_hud.index('Welcome to CHILL! Pick a vibe & color. Stay weird.'),
            )
            self.assertEqual(
                source.count("Player Variable(Current Array Element, PembaruanDaftarTertunda) == False"),
                3,
            )

            setup = source.split(f'{rule_kw}("01b - Siklus tim: Pekerja penyiapan dari penjadwal global")', 1)[1].split(f'{rule_kw}("02 - Pemain: Pisahkan manusia dari pasukan kaleng")', 1)[0]
            self.assertNotIn("Disable Game Mode HUD(Event Player);", setup)
            self.assertNotIn("Disable Game Mode In-World UI(Event Player);", setup)
            self.assertIn("Call Subroutine(TenangkanPemain);", setup)
            self.assertIn(f"If(Array Contains({global_name}.PemainManusia, Event Player));", setup)
            self.assertIn("Call Subroutine(BersihkanPemain);", setup)
            self.assertIn("Call Subroutine(SiapkanPemain);", setup)
            self.assertNotIn("Wait(", setup)

            scheduler = source.split(f'{rule_kw}("04g - Utama global: Penjadwal pusat 20 Hz")', 1)[1].split(f'{rule_kw}("05 - Menu:', 1)[0]
            self.assertIn(f"{global_name}.SalinanDaftarPemain = All Players(All Teams);", scheduler)
            self.assertIn(
                f"{global_name}.PemainAktif = {global_name}.SalinanDaftarPemain[{global_name}.IndeksPemainGlobal];",
                scheduler,
            )

            left = source.split(f'{rule_kw}("04 - Pemain Keluar: Bersihkan hanya saat benar-benar keluar")', 1)[1].split(f'{rule_kw}("04g - Utama global: Penjadwal pusat 20 Hz")', 1)[0]
            self.assertIn("Wait(0.500,", left)
            self.assertIn("Abort If(Entity Exists(Event Player) == True);", left)
            self.assertNotIn("Call Subroutine(TenangkanPemain);", left)
            self.assertIn("Call Subroutine(BersihkanPemain);", left)

            cleanup = source.split(f'{rule_kw}("93c - Subrutin: Bersihkan referensi pemain yang benar-benar keluar")', 1)[1].split(f'{rule_kw}("', 1)[0]
            self.assertIn(f"{global_name}.PemainPembersihan = Event Player;", cleanup)
            self.assertIn(f"{global_name}.IndeksKeluar = Index Of Array Value({global_name}.PemainManusia, {global_name}.PemainPembersihan);", cleanup)
            self.assertNotIn("Index Of Array Value(" + global_name + ".SlotHUDPemain", cleanup)
            self.assertEqual(cleanup.count("For Global Variable("), 1)
            self.assertIn(
                f"For Global Variable(IndeksPemilih, 0, Count Of({global_name}.PemainManusia), 1);",
                cleanup,
            )
            self.assertEqual(cleanup.count("Filtered Array("), 1)
            self.assertIn(
                f"Set Player Variable(Filtered Array({global_name}.PemainManusia, Player Variable(Current Array Element, PemainDipilih) == {global_name}.PemainPembersihan), PemainDipilih, Null);",
                cleanup,
            )
            self.assertNotIn("Allow Button(", cleanup)
            self.assertNotIn("Clear Status(", cleanup)
            self.assertNotIn("Set Move Speed(", cleanup)
            self.assertIn(
                f"Modify Player Variable({global_name}.PemainManusia[{global_name}.IndeksPemilih], PembunuhBalasDendam, Remove From Array By Index, {global_name}.IndeksDendamKeluar);",
                cleanup,
            )
            self.assertIn(
                f"Modify Player Variable({global_name}.PemainManusia[{global_name}.IndeksPemilih], JumlahBalasDendam, Remove From Array By Index, {global_name}.IndeksDendamKeluar);",
                cleanup,
            )
            self.assertIn("Remove From Array By Index", cleanup)


if __name__ == "__main__":
    unittest.main()
