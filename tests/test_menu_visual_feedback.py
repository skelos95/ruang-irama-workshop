"""Menu visual contracts for the logical input, before global compilation."""

from pathlib import Path
import re
import unittest

from tools import check_clipboard_import as clipboard
from tools import validate_workshop as validator

ROOT = Path(__file__).resolve().parents[1]


class MenuVisualFeedbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        italian = (ROOT / "source/ruang_irama.it-IT.source").read_text(encoding="utf-8")
        segments = re.split(r'("(?:\\.|[^"\\])*")', italian)
        for index in range(0, len(segments), 2):
            for original, translated in clipboard.ITALIAN_TO_ENGLISH_TOKENS:
                segments[index] = clipboard._replace_token(segments[index], original, translated)
        cls.sources = ((ROOT / "tests/fixtures/semantic_reference.txt").read_text(encoding="utf-8"), "".join(segments))

    def feedback_checks(self, source):
        checks = validator.Checks()
        validator.validate_catalog_feedback(checks, source, validator.extract_rules(source))
        return checks

    def test_ring_is_only_emitted_by_jump_and_has_no_persistent_handle(self):
        for source in self.sources:
            checks = self.feedback_checks(source)
            self.assertEqual(checks.errors, [])
            effects = [(validator.subroutine_target(rule), call) for rule in validator.extract_rules(source)
                       for call in validator.iter_calls(rule.body, "Play Effect")]
            self.assertEqual(len(effects), 1)
            self.assertEqual(effects[0][0], "ProsesLompatGanda")
            self.assertEqual(effects[0][1].args[1].strip(), "Ring Explosion")
            self.assertNotIn("EfekTerapkan", source)

    def test_validator_rejects_reintroduced_menu_ring(self):
        for source in self.sources:
            rule = validator.rule_by_subroutine(validator.extract_rules(source), "TerapkanHalamanWarna")
            mutated = source[:rule.start] + rule.body.replace("Event Player.IndeksWarna =", "Play Effect(All Players(All Teams), Ring Explosion, Global.RGB, Position Of(Event Player), 3);\n\t\tEvent Player.IndeksWarna =", 1) + source[rule.end:]
            self.assertTrue(any("effetti consentiti soltanto" in error for error in self.feedback_checks(mutated).errors))

    def test_validator_rejects_persistent_ring(self):
        for source in self.sources:
            mutated = source.replace("Play Effect(All Players(All Teams), Ring Explosion", "Create Effect(All Players(All Teams), Ring", 1)
            self.assertTrue(any("nessun effetto persistente" in error for error in self.feedback_checks(mutated).errors))

    def test_validator_guards_smooth_color_duration_and_cleanup(self):
        for source in self.sources:
            rules = validator.extract_rules(source)
            transition = validator.rule_by_subroutine(rules, "TransisiWarnaMenu")
            quiet = validator.rule_by_subroutine(rules, "TenangkanPemain")
            for rule, old, new, error in (
                (transition, "0.180, Destination and Duration", "0.000, Destination and Duration", "transizione colore di 0.180"),
                (transition, "Chase Player Variable Over Time", "Chase Player Variable At Rate", "proprietario consentito"),
                (transition, "HalamanMenu) == 14 ? Global.DaftarWarnaRGB", "HalamanMenu) == 15 ? Global.DaftarWarnaRGB", "progressione sfumata Multijump"),
                (transition, "HalamanMenu) == 13 ? Global.DaftarWarnaRGB", "HalamanMenu) == 15 ? Global.DaftarWarnaRGB", "progressione sfumata Ghost/Fly"),
                (transition, "HalamanMenu) == 15 ? Global.DaftarWarnaRGB", "HalamanMenu) == 16 ? Global.DaftarWarnaRGB", "progressione sfumata Super Punch"),
                (transition, "* 0.680 + Vector(190, 210, 230) * 0.320", "* 0.700 + Vector(190, 210, 230) * 0.300", "progressione sfumata pagina 1"),
                (transition, "Vector(236, 153, 0)", "Vector(0, 153, 236)", "progressione sfumata pagina 6"),
                (transition, "HalamanMenu) == 8 ?", "HalamanMenu) == 7 ?", "sedici tinte menu in ordine"),
                (transition, "Global.DaftarWarnaRGB[Event Player.KursorWarna]", "Global.DaftarWarnaRGB[Event Player.IndeksWarna]", "colore esatto della preview"),
                (transition, "If(Event Player.TeleportasiJongkokAktif == True);", "Chase Player Variable Over Time(Event Player, WarnaMenu, Vector(1, 2, 3), 0.180, Destination and Duration);\n\t\tIf(Event Player.TeleportasiJongkokAktif == True);", "due transizioni fluide senza override"),
                (quiet, "Stop Chasing Player Variable(Event Player, WarnaMenu);", "", "cleanup transizione colore"),
            ):
                with self.subTest(mutation=old):
                    self.assertIn(old, rule.body)
                    mutated = source[:rule.start] + rule.body.replace(old, new, 1) + source[rule.end:]
                    self.assertTrue(any(error in issue for issue in self.feedback_checks(mutated).errors))

    def test_catalog_alignment_and_dynamic_wrap_are_guarded(self):
        for source in self.sources:
            for old, new, error in (
                ('Custom String("Plum")', '', "40 voci"),
                ('Custom String("Charcoal")', 'Custom String("Black")', "nomi colore unici"),
                ('Custom String("Arang")', 'Custom String("Hitam")', "nomi colore unici"),
                ('Custom String("ถ่าน")', 'Custom String("ดำ")', "nomi colore unici"),
                ('Vector(190, 210, 230)', 'Vector(191, 210, 230)', "RGB nome e menu allineati"),
                ('% Count Of(Global.DaftarGenre)', '% 100', "lunghezza corrente"),
                ('Count Of(Global.DaftarGenre) - 10', '90', "passo indietro dinamico"),
                ('Hold CROUCH | {0}: back', '{0}: back', "Soundtrack bloccato: Reload"),
            ):
                with self.subTest(mutation=old):
                    self.assertIn(old, source)
                    self.assertTrue(any(error in issue for issue in self.feedback_checks(source.replace(old, new, 1)).errors))


if __name__ == "__main__":
    unittest.main()
