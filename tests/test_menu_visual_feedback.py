from pathlib import Path
import re
import unittest

from tools import check_clipboard_import as clipboard
from tools import validate_workshop as validator

ROOT = Path(__file__).resolve().parents[1]


class MenuVisualFeedbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        italian = (ROOT / "workshop/ruang_irama.it-IT.workshop").read_text(encoding="utf-8")
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

    def test_validator_rejects_color_animation(self):
        for source in self.sources:
            mutated = re.sub(r"Event Player.WarnaMenu = (Event Player.KursorTeleportasi[^;]*);",
                             r"Chase Player Variable Over Time(Event Player, WarnaMenu, \1, 0.180, Destination and Duration);", source, count=1)
            self.assertTrue(any("senza animazione" in error for error in self.feedback_checks(mutated).errors))

    def test_catalog_alignment_and_dynamic_wrap_are_guarded(self):
        for source in self.sources:
            for old, new, error in (
                ('Custom String("Plum")', '', "40 voci"),
                ('% Count Of(Global.DaftarGenre)', '% 100', "lunghezza corrente"),
                ('Count Of(Global.DaftarGenre) - 10', '90', "passo indietro dinamico"),
            ):
                with self.subTest(mutation=old):
                    self.assertIn(old, source)
                    self.assertTrue(any(error in issue for issue in self.feedback_checks(source.replace(old, new, 1)).errors))


if __name__ == "__main__":
    unittest.main()
