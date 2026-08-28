from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    (ROOT / "workshop" / "ruang_irama.it-IT.workshop", "regola", "Globale"),
    (ROOT / "tests" / "fixtures" / "semantic_reference.txt", "rule", "Global"),
)


def block(source: str, start: str, end: str) -> str:
    return source.split(start, 1)[1].split(end, 1)[0]


class RosterRejoinRegressionTests(unittest.TestCase):
    def test_visible_name_is_never_persistent_roster_identity(self):
        for path, _, _ in SOURCES:
            source = path.read_text(encoding="utf-8")
            for forbidden in (
                "ProfilNama",
                "ProfilPreferensiA",
                "ProfilPreferensiB",
                "ProfilStatus",
                "ProfilSosial",
                "ProfilPilihanNama",
                "NamaSlotHUD",
                "PemainPengganti",
            ):
                self.assertNotIn(forbidden, source, f"{path.name}: {forbidden} must not own player identity")

    def test_true_leave_recycles_the_roster_slot(self):
        for path, rule_kw, global_name in SOURCES:
            source = path.read_text(encoding="utf-8")
            left = block(
                source,
                f'{rule_kw}("04 - Pemain Keluar: Bersihkan hanya saat benar-benar keluar")',
                f'{rule_kw}("04g - Utama global: Penjadwal pusat 20 Hz")',
            )
            self.assertIn("Wait(0.500,", left)
            self.assertIn("Abort If(Entity Exists(Event Player) == True);", left)
            self.assertIn("Call Subroutine(BersihkanPemain);", left)
            self.assertNotIn("Custom String(\"{0}\", Event Player)", left)

            cleanup = block(
                source,
                f'{rule_kw}("93c - Subrutin: Bersihkan referensi pemain yang benar-benar keluar")',
                f'{rule_kw}("94 - Subrutin: Siapkan pemain',
            )
            recycle = (
                f"{global_name}.SlotHUDTersedia = Sorted Array(Append To Array("
                f"{global_name}.SlotHUDTersedia, {global_name}.IndeksUtangKeluar), Current Array Element);"
            )
            self.assertIn(recycle, cleanup)
            self.assertIn("Modify Global Variable(SlotHUDPemain, Remove From Array By Index", cleanup)
            self.assertIn("Modify Global Variable(PemainManusia, Remove From Array By Index", cleanup)

    def test_duplicate_and_temporarily_blank_names_never_own_or_replace_roster_identity(self):
        for path, rule_kw, global_name in SOURCES:
            source = path.read_text(encoding="utf-8")
            classifier = block(
                source,
                f'{rule_kw}("02 - Pemain: Pisahkan manusia dari pasukan kaleng")',
                f'{rule_kw}("02b - HUD Pemain',
            )
            capture = 'Event Player.NamaTampilan = Evaluate Once(Custom String("{0}", Event Player));'
            allocation = f"Event Player.UrutanHUD = First Of({global_name}.SlotHUDTersedia);"
            self.assertIn(capture, classifier)
            self.assertIn(allocation, classifier)
            self.assertIn(f"{global_name}.PemainManusia = Append To Array({global_name}.PemainManusia, Event Player);", classifier)
            between_capture_and_slot = classifier.split(capture, 1)[1].split(allocation, 1)[0]
            self.assertNotIn("Index Of Array Value", between_capture_and_slot)
            self.assertNotIn("NamaSlotHUD", classifier)
            self.assertNotIn("PemainPengganti", classifier)

            roster = block(
                source,
                f'{rule_kw}("02b - HUD Pemain',
                f'{rule_kw}("03c - Bot/Dummy',
            )
            self.assertIn("Event Player.NamaTampilan != Null;", roster)
            self.assertIn('Event Player.NamaTampilan != Custom String("");', roster)

            fast = block(
                source,
                f'{rule_kw}("89a - Subrutin: Proses status cepat pemain")',
                f'{rule_kw}("89b - Subrutin',
            )
            self.assertIn(
                f'Custom String("{{0}}", {global_name}.PemainAktif) != Custom String("")',
                fast,
            )
            self.assertIn(
                f'{global_name}.PemainAktif.NamaTampilan = Evaluate Once(Custom String("{{0}}", {global_name}.PemainAktif));',
                fast,
            )

    def test_temporarily_blank_visible_name_does_not_consume_a_roster_slot(self):
        for path, rule_kw, global_name in SOURCES:
            source = path.read_text(encoding="utf-8")
            classifier = block(
                source,
                f'{rule_kw}("02 - Pemain: Pisahkan manusia dari pasukan kaleng")',
                f'{rule_kw}("02b - HUD Pemain',
            )
            capture = 'Event Player.NamaTampilan = Evaluate Once(Custom String("{0}", Event Player));'
            allocation = f"Event Player.UrutanHUD = First Of({global_name}.SlotHUDTersedia);"
            self.assertIn(capture, classifier)
            self.assertIn(allocation, classifier)
            before_allocation = classifier.split(capture, 1)[1].split(allocation, 1)[0]
            blank_name_gate = (
                'If(Or(Event Player.NamaTampilan == Null, '
                'Event Player.NamaTampilan == Custom String("")));'
            )
            self.assertIn(blank_name_gate, before_allocation)
            blank_retry = before_allocation.split(blank_name_gate, 1)[1]
            self.assertIn("Event Player.SudahDiperiksa = False;", blank_retry)
            self.assertIn("Event Player.SudahSiap = False;", blank_retry)
            self.assertIn("Abort;", blank_retry)
            self.assertNotIn("Remove From Array By Index", blank_retry)

    def test_true_leave_clears_other_players_votes_for_the_departed_entity(self):
        for path, rule_kw, global_name in SOURCES:
            source = path.read_text(encoding="utf-8")
            cleanup = block(
                source,
                f'{rule_kw}("93c - Subrutin: Bersihkan referensi pemain yang benar-benar keluar")',
                f'{rule_kw}("94 - Subrutin: Siapkan pemain',
            )
            voters = (
                f"Filtered Array({global_name}.PemainManusia, "
                f"Player Variable(Current Array Element, PemainDipilih) == "
                f"{global_name}.PemainPembersihan)"
            )
            clear_votes = f"Set Player Variable({voters}, PemainDipilih, Null);"
            roster_removal = "Modify Global Variable(PemainManusia, Remove From Array By Index"
            self.assertIn(clear_votes, cleanup)
            self.assertIn(roster_removal, cleanup)
            self.assertLess(cleanup.index(clear_votes), cleanup.index(roster_removal))

    def test_true_rejoin_starts_with_fresh_vote_and_unkillable_state(self):
        for path, rule_kw, _ in SOURCES:
            source = path.read_text(encoding="utf-8")
            setup = block(
                source,
                f'{rule_kw}("94 - Subrutin: Siapkan pemain',
                f'{rule_kw}("95 - Subrutin: Segarkan daftar tontonan',
            )
            for expected in (
                "Event Player.PemainDipilih = Null;",
                "Event Player.JumlahPilihan = 0;",
                "Event Player.KebalAktif = False;",
                "Event Player.KursorKebal = 0;",
                "Event Player.ModeKebal = 0;",
            ):
                self.assertIn(expected, setup)

    def test_unkillable_runtime_state_is_self_repaired(self):
        for path, rule_kw, global_name in SOURCES:
            source = path.read_text(encoding="utf-8")
            fast = block(
                source,
                f'{rule_kw}("89a - Subrutin: Proses status cepat pemain")',
                f'{rule_kw}("89b - Subrutin',
            )
            self.assertIn(f"{global_name}.PemainAktif.KebalAktif == True", fast)
            self.assertIn(f"Has Status({global_name}.PemainAktif, Unkillable) == False", fast)
            self.assertIn(f"Set Status({global_name}.PemainAktif, Null, Unkillable, 9999);", fast)
            self.assertIn(f"Set Damage Received({global_name}.PemainAktif, 0);", fast)

    def test_special_player_rejoin_uses_documented_defaults(self):
        for path, rule_kw, _ in SOURCES:
            source = path.read_text(encoding="utf-8")
            classifier = block(
                source,
                f'{rule_kw}("02 - Pemain: Pisahkan manusia dari pasukan kaleng")',
                f'{rule_kw}("02b - HUD Pemain',
            )
            self.assertIn('If(Custom String("{0}", Event Player) == Custom String("งูแท้"));', classifier)
            self.assertIn('Event Player.MusikKhusus = Custom String("Caladan Brood");', classifier)
            self.assertIn("Event Player.IndeksWarna = 1;", classifier)
            self.assertIn("Event Player.KursorWarna = 1;", classifier)
            self.assertIn("Event Player.IndeksIkon = 23;", classifier)
            self.assertIn("Event Player.KursorIkon = 23;", classifier)
            self.assertNotIn("Profil", classifier)


if __name__ == "__main__":
    unittest.main()
