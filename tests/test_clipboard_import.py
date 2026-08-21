from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_clipboard_import as clipboard  # noqa: E402


class ClipboardImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source_path = ROOT / "tests" / "fixtures" / "semantic_reference.txt"
        cls.italian_path = ROOT / "workshop" / "ruang_irama.it-IT.workshop"
        cls.source = cls.source_path.read_text(encoding="utf-8")
        cls.italian = cls.italian_path.read_text(encoding="utf-8")

    def test_canonical_english_source_is_clipboard_safe(self) -> None:
        report = clipboard.check_path(self.source_path, "en-US")
        self.assertEqual(report.language, "en-US")
        self.assertGreater(report.rule_count, 0)
        self.assertLess(report.largest_rule.bytes_utf8, clipboard.CLIENT_LARGEST_RULE_LIMIT_BYTES)
        self.assertLessEqual(report.largest_rule.bytes_utf8, clipboard.SOURCE_RULE_SAFETY_TARGET_BYTES)

    def test_generated_italian_source_is_clipboard_safe(self) -> None:
        report = clipboard.check_path(self.italian_path, "it-IT")
        self.assertEqual(report.language, "it-IT")
        self.assertGreater(report.rule_count, 0)
        self.assertLess(report.largest_rule.bytes_utf8, clipboard.CLIENT_LARGEST_RULE_LIMIT_BYTES)
        self.assertLessEqual(report.largest_rule.bytes_utf8, clipboard.SOURCE_RULE_SAFETY_TARGET_BYTES)

    def test_italian_source_uses_localized_structural_grammar(self) -> None:
        stripped = self.italian.lstrip()
        self.assertTrue(stripped.startswith("variabili\n{"))
        self.assertIn("\nsubroutine\n{", self.italian)
        self.assertIn('\nregola("', self.italian)
        self.assertIn("\n\tevento\n", self.italian)
        self.assertIn("\n\tcondizioni\n", self.italian)
        self.assertIn("\n\tazioni\n", self.italian)

    def test_italian_identity_tokens_are_not_partially_localized(self) -> None:
        self.assertIn("Ongoing - Global;", self.italian)
        self.assertNotIn("Ongoing - Globale;", self.italian)
        self.assertIn("Button(Secondary Fire)", self.italian)
        without_custom_colors = self.italian.replace("Custom Color(", "")
        self.assertNotIn("Color(", without_custom_colors)
        self.assertNotIn("If(And(Globale.PemainAktif.Manusia == True, And(Globale.PemainAktif.EfekNasib == 5", self.italian)
        self.assertNotIn("If(And(Globale.PemainAktif.Manusia == True, And(Globale.PemainAktif.KartuNasibAktif == True, And(Globale.PemainAktif.PutaranKartuNasib == 0, And(Globale.PemainAktif.EfekNasibBerakhir > 0", self.italian)
        self.assertNotIn("If(And(Globale.PemainAktif.WaktuIkonNasibBerakhir > 0", self.italian)
        self.assertNotIn("If(And(Globale.PemainAktif.KartuNasibAktif == False, Globale.PemainAktif.MenuTerbuka == False", self.italian)

    def test_english_and_italian_have_same_rule_count(self) -> None:
        english = clipboard.check_path(self.source_path, "en-US")
        italian = clipboard.check_path(self.italian_path, "it-IT")
        self.assertEqual(english.rule_count, italian.rule_count)


    def test_auto_detects_both_profiles(self) -> None:
        self.assertEqual(clipboard.check_text(self.source).language, "en-US")
        self.assertEqual(clipboard.check_text(self.italian).language, "it-IT")

    def test_windows_crlf_clipboard_is_accepted_for_both_profiles(self) -> None:
        english_crlf = self.source.replace("\r\n", "\n").replace("\n", "\r\n")
        italian_crlf = self.italian.replace("\r\n", "\n").replace("\n", "\r\n")
        self.assertEqual(clipboard.check_text(english_crlf).language, "en-US")
        self.assertEqual(clipboard.check_text(italian_crlf).language, "it-IT")

    def test_wrong_explicit_language_is_rejected(self) -> None:
        with self.assertRaisesRegex(clipboard.ClipboardImportError, "fornita al controllo"):
            clipboard.check_text(self.source, "it-IT")
        with self.assertRaisesRegex(clipboard.ClipboardImportError, "fornita al controllo"):
            clipboard.check_text(self.italian, "en-US")

    def test_mixed_structural_grammar_is_rejected(self) -> None:
        mutated = self.source.replace("\tactions\n", "\tazioni\n", 1)
        with self.assertRaises(clipboard.ClipboardImportError):
            clipboard.check_text(mutated, "en-US")

    def test_utf8_bom_is_rejected(self) -> None:
        with self.assertRaisesRegex(clipboard.ClipboardImportError, "BOM UTF-8"):
            clipboard.check_text("\ufeff" + self.source)

    def test_markdown_fence_is_rejected(self) -> None:
        with self.assertRaisesRegex(clipboard.ClipboardImportError, "Markdown"):
            clipboard.check_text("```\n" + self.source + "\n```")

    def test_smart_quote_in_rule_header_is_rejected(self) -> None:
        mutated = self.source.replace('rule("', 'rule(“', 1)
        with self.assertRaises(clipboard.ClipboardImportError):
            clipboard.check_text(mutated, "en-US")

    def test_italian_words_inside_custom_strings_are_allowed(self) -> None:
        mutated = self.source.replace(
            'Custom String("Lowercase")',
            'Custom String("azioni e condizioni")',
            1,
        )
        report = clipboard.check_text(mutated, "en-US")
        self.assertGreater(report.rule_count, 0)

    def test_unclosed_string_is_rejected(self) -> None:
        mutated = self.source.replace(
            'Custom String("Lowercase")', 'Custom String("Lowercase)', 1
        )
        with self.assertRaisesRegex(
            clipboard.ClipboardImportError, "stringa Workshop non chiusa"
        ):
            clipboard.check_text(mutated, "en-US")

    def test_static_rule_safety_target_is_enforced(self) -> None:
        oversized = (
            "variables\n{\n}\n\n"
            "subroutines\n{\n}\n\n"
            'rule("test")\n{\n'
            "\tevent\n\t{\n\t\tOngoing - Global;\n\t}\n"
            "\tconditions\n\t{\n\t\tTrue == True;\n\t}\n"
            "\tactions\n\t{\n\t\t"
            + 'Custom String("'
            + ("x" * (clipboard.SOURCE_RULE_SAFETY_TARGET_BYTES + 1024))
            + '");\n\t}\n}\n'
        )
        with self.assertRaisesRegex(clipboard.ClipboardImportError, "80 KB"):
            clipboard.check_text(oversized, "en-US")


if __name__ == "__main__":
    unittest.main()
