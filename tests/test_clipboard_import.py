from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


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

    def assert_semantic_mismatch(self, mutated_italian: str) -> None:
        error = clipboard.semantic_equivalence_error(self.source, mutated_italian)
        self.assertIsNotNone(error)
        self.assertIn("equivalenza semantica EN/IT fallita", error)
        with self.assertRaisesRegex(
            clipboard.ClipboardImportError, "equivalenza semantica EN/IT fallita"
        ):
            clipboard.require_semantic_equivalence(self.source, mutated_italian)

    def test_internal_semantic_fixture_is_clipboard_safe(self) -> None:
        report = clipboard.check_path(self.source_path, "en-US")
        self.assertEqual(report.language, "en-US")
        self.assertGreater(report.rule_count, 0)
        self.assertLessEqual(report.largest_rule.bytes_utf8, clipboard.SOURCE_RULE_SAFETY_TARGET_BYTES)
        self.assertLessEqual(report.structural_units, clipboard.SOURCE_TOTAL_STRUCTURAL_TARGET)
        self.assertLessEqual(report.largest_structural_rule.structural_units,
                             clipboard.SOURCE_RULE_STRUCTURAL_TARGET)

    def test_italian_clipboard_source_is_clipboard_safe(self) -> None:
        report = clipboard.check_path(self.italian_path, "it-IT")
        self.assertEqual(report.language, "it-IT")
        self.assertGreater(report.rule_count, 0)
        self.assertLessEqual(report.largest_rule.bytes_utf8, clipboard.SOURCE_RULE_SAFETY_TARGET_BYTES)
        self.assertLessEqual(report.structural_units, clipboard.SOURCE_TOTAL_STRUCTURAL_TARGET)
        self.assertLessEqual(report.largest_structural_rule.structural_units,
                             clipboard.SOURCE_RULE_STRUCTURAL_TARGET)

    def test_only_italian_workshop_is_user_facing(self) -> None:
        self.assertTrue(self.italian_path.is_file())
        self.assertFalse((ROOT / "workshop" / "ruang_irama.workshop").exists())
        self.assertFalse((ROOT / "workshop" / "ruang_irama.it-IT.manifest").exists())

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
        self.assertNotIn("Color(White)", without_custom_colors)
        self.assertNotIn("Color(Gray)", without_custom_colors)
        self.assertNotIn("Danneggia(", self.italian)
        self.assertIn("Damage(", self.italian)
        self.assertNotIn("If(And(Globale.PemainAktif.Manusia == True, And(Globale.PemainAktif.EfekNasib == 5", self.italian)
        self.assertNotIn("If(And(Globale.PemainAktif.Manusia == True, And(Globale.PemainAktif.KartuNasibAktif == True, And(Globale.PemainAktif.PutaranKartuNasib == 0, And(Globale.PemainAktif.EfekNasibBerakhir > 0", self.italian)
        self.assertNotIn("If(And(Globale.PemainAktif.WaktuIkonNasibBerakhir > 0", self.italian)
        self.assertNotIn("If(And(Globale.PemainAktif.KartuNasibAktif == False, Globale.PemainAktif.MenuTerbuka == False", self.italian)

    def test_semantic_fixture_and_italian_are_exactly_equivalent(self) -> None:
        english = clipboard.check_path(self.source_path, "en-US")
        italian = clipboard.check_path(self.italian_path, "it-IT")
        self.assertEqual(english.rule_count, italian.rule_count)
        self.assertIsNone(
            clipboard.semantic_equivalence_error(self.source, self.italian)
        )
        self.assertEqual(
            clipboard.canonical_semantic_text(self.source, "en-US"),
            clipboard.canonical_semantic_text(self.italian, "it-IT"),
        )

    def test_semantic_gate_ignores_only_whitespace_outside_strings(self) -> None:
        mutated = self.italian.replace("variabili\n{", "  variabili \n  {  ", 1)
        self.assertIsNone(clipboard.semantic_equivalence_error(self.source, mutated))

    def test_semantic_gate_knows_every_localized_token(self) -> None:
        for italian, english in clipboard.ITALIAN_TO_ENGLISH_TOKENS:
            with self.subTest(italian=italian):
                self.assertEqual(
                    clipboard.canonical_semantic_text(italian, "it-IT"),
                    clipboard.canonical_semantic_text(english, "en-US"),
                )

    def test_semantic_gate_knows_the_nine_equivalent_colors(self) -> None:
        for components, name in clipboard.EQUIVALENT_NAMED_COLORS:
            italian = f"Custom Color({', '.join(map(str, components))})"
            english = f"Color({name})"
            with self.subTest(color=name):
                self.assertEqual(
                    clipboard.canonical_semantic_text(italian, "it-IT"),
                    clipboard.canonical_semantic_text(english, "en-US"),
                )

    def test_native_italian_named_color_palette_is_importable_and_canonical(self) -> None:
        names = ("White", "Aqua", "Black", "Blue", "Gray", "Green", "Lime Green", "Orange",
                 "Purple", "Red", "Rose", "Sky Blue", "Turquoise", "Violet", "Yellow")
        localized = {"White": "Bianco", "Gray": "Grigio"}
        english_palette = ", ".join(f"Color({name})" for name in names)
        italian_palette = ", ".join(f"Color({localized.get(name, name)})" for name in names)
        english = (
            "variables\n{\n global:\n 0: PaletUji\n}\nsubroutines\n{}\n"
            'rule("palette")\n{\n event\n{\n Ongoing - Global;\n}\n conditions\n{\n True == True;\n}\n actions\n{\n'
            f"Global.PaletUji = Array({english_palette});\n}}\n}}\n"
        )
        italian = (
            "variabili\n{\n globale:\n 0: PaletUji\n}\nsubroutine\n{}\n"
            'regola("palette")\n{\n evento\n{\n Ongoing - Global;\n}\n condizioni\n{\n True == True;\n}\n azioni\n{\n'
            f"Globale.PaletUji = Array({italian_palette});\n}}\n}}\n"
        )
        self.assertEqual(clipboard.check_text(italian, "it-IT").rule_count, 1)
        self.assertIsNone(clipboard.semantic_equivalence_error(english, italian))
        self.assertEqual(clipboard.canonical_semantic_text('Custom String("Bianco Grigio")', "it-IT"),
                         'CustomString("Bianco Grigio")')
        for name in ("White", "Gray"):
            with self.subTest(unlocalized=name):
                changed = italian.replace(f"Color({localized[name]})", f"Color({name})", 1)
                with self.assertRaisesRegex(clipboard.ClipboardImportError, "colore nominale"):
                    clipboard.check_text(changed, "it-IT")

    def test_semantic_gate_rejects_italian_only_privacy_default_change(self) -> None:
        needle = "Event Player.PrivasiInspeksiAktif = False;"
        self.assertIn(needle, self.italian)
        self.assert_semantic_mismatch(
            self.italian.replace(
                needle, "Event Player.PrivasiInspeksiAktif = True;", 1
            )
        )

    def test_check_path_rejects_semantically_divergent_italian_source(self) -> None:
        mutated = self.italian.replace(
            "Event Player.PrivasiInspeksiAktif = False;",
            "Event Player.PrivasiInspeksiAktif = True;",
            1,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            reference_path = temp_root / "semantic_reference.txt"
            italian_path = temp_root / "ruang_irama.it-IT.workshop"
            reference_path.write_text(self.source, encoding="utf-8")
            italian_path.write_text(mutated, encoding="utf-8")
            with (
                patch.object(clipboard, "ITALIAN_SOURCE", italian_path),
                patch.object(clipboard, "SEMANTIC_REFERENCE", reference_path),
                self.assertRaisesRegex(
                    clipboard.ClipboardImportError,
                    "equivalenza semantica EN/IT fallita",
                ),
            ):
                clipboard.check_path(italian_path, "it-IT")

    def test_semantic_gate_rejects_italian_only_acceleration_direction(self) -> None:
        needle = "Facing Direction Of(Evaluate Once(Globale.PemainAktif))"
        self.assertIn(needle, self.italian)
        self.assert_semantic_mismatch(
            self.italian.replace(needle, "Vector(1, 0, 0)", 1)
        )

    def test_semantic_gate_rejects_italian_only_privacy_polarity(self) -> None:
        needle = "Player Variable(Current Array Element, PrivasiInspeksiAktif) == False"
        self.assertIn(needle, self.italian)
        self.assert_semantic_mismatch(
            self.italian.replace(
                needle, "Player Variable(Current Array Element, PrivasiInspeksiAktif) == True", 1
            )
        )

    def test_semantic_gate_rejects_italian_only_color_change(self) -> None:
        needle = "Custom Color(255, 255, 255, 255)"
        self.assertIn(needle, self.italian)
        self.assert_semantic_mismatch(
            self.italian.replace(needle, "Custom Color(254, 255, 255, 255)", 1)
        )

    def test_semantic_gate_rejects_italian_only_custom_string_change(self) -> None:
        needle = 'Custom String("Lowercase")'
        self.assertIn(needle, self.italian)
        self.assert_semantic_mismatch(
            self.italian.replace(needle, 'Custom String("LOWERCASE")', 1)
        )

    def test_semantic_gate_rejects_italian_only_rule_structure_change(self) -> None:
        needle = "\t\tGlobale.Siap == False;\n"
        self.assertIn(needle, self.italian)
        self.assert_semantic_mismatch(self.italian.replace(needle, "", 1))

    def test_italian_profile_rejects_english_namespace_even_if_semantics_match(self) -> None:
        mutated = self.italian.replace("Globale.Siap", "Global.Siap", 1)
        self.assertIsNone(clipboard.semantic_equivalence_error(self.source, mutated))
        with self.assertRaisesRegex(clipboard.ClipboardImportError, "namespace Global en-US"):
            clipboard.check_text(mutated, "it-IT")

    def test_italian_profile_rejects_english_mode_and_all_heroes_tokens(self) -> None:
        for italian, english, message in (
            ("Game Mode(Schermaglia)", "Game Mode(Skirmish)", "modalità Game Mode en-US"),
            ("Tutti gli eroi", "All Heroes", "All Heroes en-US"),
            ("Hero(Regina dei Junker)", "Hero(Junker Queen)", "eroe Junker Queen en-US"),
        ):
            with self.subTest(token=english):
                self.assertIn(italian, self.italian)
                mutated = self.italian.replace(italian, english, 1)
                self.assertIsNone(clipboard.semantic_equivalence_error(self.source, mutated))
                with self.assertRaisesRegex(clipboard.ClipboardImportError, message):
                    clipboard.check_text(mutated, "it-IT")

    def test_italian_profile_rejects_equivalent_named_color_syntax(self) -> None:
        mutated = self.italian.replace(
            "Custom Color(255, 255, 255, 255)",
            "Color(White)",
            1,
        )
        self.assertIsNone(clipboard.semantic_equivalence_error(self.source, mutated))
        with self.assertRaisesRegex(clipboard.ClipboardImportError, "colore nominale"):
            clipboard.check_text(mutated, "it-IT")

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


class StructuralBudgetTests(unittest.TestCase):
    @staticmethod
    def source(actions: str, copies: int = 1) -> str:
        rules = "\n".join(
            f'rule("budget {index}")\n{{\n event\n{{\n Ongoing - Global;\n}}\n'
            f' conditions\n{{\n True == True;\n}}\n actions\n{{\n{actions}\n}}\n}}'
            for index in range(copies)
        )
        return "variables\n{\n global:\n 0: Nilai\n}\nsubroutines\n{}\n" + rules

    @staticmethod
    def units(expression: str) -> int:
        return clipboard._StructuralExpression.units(
            clipboard._StructuralExpression(expression).tree)

    def test_weights_include_variable_access_comparisons_and_string_defaults(self) -> None:
        # Small independent examples from the public emitter's node rules.
        for expression, expected in (
            ("42", 2), ("Global.Nilai", 2), ("Event Player.Nilai", 3),
            ("Global.Pemain.Nilai", 4), ("Global.Nilai[2]", 5),
            ("1 == 2", 6), ("Array(1, 2)", 6),
            ("Evaluate Once(Global.Nilai)", 4),
            ('Custom String("x")', 5),
            ('Custom String("{0}", Global.Nilai)', 6),
            ('Custom String("{0}", Global.Nilai, Null, Null)', 6),
            ('String("Hello")', 6),
        ):
            with self.subTest(expression=expression):
                self.assertEqual(self.units(expression), expected)

    def test_titles_comments_whitespace_and_string_content_do_not_inflate_nodes(self) -> None:
        base = self.source('Global.Nilai = Custom String("plain");')
        decorated = base.replace('"budget 0"', '"a much longer rule title"').replace(
            'Global.Nilai = Custom String("plain");',
            '"Komentar: + Array(999) ; tidak menjadi ekspresi"\n'
            ' Global . Nilai  =  Custom String("Thai ไทย ; () + quotes: \\\"ok\\\"") ;'
        )
        before = clipboard.check_text(base)
        after = clipboard.check_text(decorated)
        self.assertEqual(before.structural_units, after.structural_units)
        self.assertGreater(after.source_bytes_utf8, before.source_bytes_utf8)

    def test_identifier_length_and_native_icon_enum_are_not_extra_values(self) -> None:
        short = self.units('Create Icon(All Players(All Teams), Vector(0, 1, 0), '
                           'Arrow: Down, Visible To Position and Color, Global.Nilai, False)')
        long = self.units('Create Icon(All Players(All Teams), Vector(0, 1, 0), '
                          'Arrow: Up, Visible To Position and Color, Global.NamaSangatPanjang, False)')
        self.assertEqual(short, long)

    def test_semantically_equivalent_color_spellings_keep_their_actual_cost(self) -> None:
        named = 'Color(White)'
        rgba = 'Custom Color(255, 255, 255, 255)'
        self.assertEqual(clipboard.canonical_semantic_text(named, 'en-US'),
                         clipboard.canonical_semantic_text(rgba, 'en-US'))
        self.assertEqual(self.units(named), 2)
        self.assertEqual(self.units(rgba), 9)

    def test_chained_array_access_and_nested_ternaries_are_fully_counted(self) -> None:
        expression = 'Player Variable(Event Player, Nilai)[2][3]'
        self.assertEqual(self.units(expression), 9)
        nested = 'True ? (False ? Global.Nilai : 1) : 2'
        self.assertEqual(self.units(nested), 10)

    def test_duplicate_nested_expressions_hit_rule_budget_before_text_limit(self) -> None:
        repeated = ', '.join(['Vector(0, 0, 0)'] * 715)
        source = self.source(f'Global.Nilai = Array({repeated});')
        self.assertLess(len(source.encode('utf-8')), clipboard.SOURCE_RULE_SAFETY_TARGET_BYTES)
        with self.assertRaisesRegex(clipboard.ClipboardImportError, 'unità/regola'):
            clipboard.check_text(source)

    def test_splitting_repeated_work_across_rules_cannot_evade_total_budget(self) -> None:
        repeated = ', '.join(['Vector(0, 0, 0)'] * 650)
        source = self.source(f'Global.Nilai = Array({repeated});', copies=8)
        sizes = clipboard._extract_rule_sizes(source, clipboard.LANGUAGE_PROFILES['en-US'])
        self.assertTrue(all(rule.structural_units < clipboard.SOURCE_RULE_STRUCTURAL_TARGET
                            for rule in sizes))
        with self.assertRaisesRegex(clipboard.ClipboardImportError, 'budget locale.*unità'):
            clipboard.check_text(source)


if __name__ == "__main__":
    unittest.main()
