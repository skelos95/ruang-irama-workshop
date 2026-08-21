from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "check_clipboard_import.py"
SPEC = importlib.util.spec_from_file_location("check_clipboard_import", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
clipboard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(clipboard)


class ClipboardImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source_path = ROOT / "workshop" / "ruang_irama.workshop"
        cls.raw = cls.source_path.read_bytes()
        cls.source = cls.raw.decode("utf-8")

    def test_canonical_source_is_clipboard_safe(self) -> None:
        report = clipboard.check_path(self.source_path)
        self.assertGreater(report.rule_count, 0)
        self.assertLess(report.largest_rule.bytes_utf8, clipboard.CLIENT_LARGEST_RULE_LIMIT_BYTES)
        self.assertLessEqual(report.largest_rule.bytes_utf8, clipboard.SOURCE_RULE_SAFETY_TARGET_BYTES)

    def test_windows_crlf_clipboard_is_accepted(self) -> None:
        crlf = self.source.replace("\r\n", "\n").replace("\n", "\r\n")
        report = clipboard.check_text(crlf)
        self.assertGreater(report.rule_count, 0)

    def test_utf8_bom_is_rejected(self) -> None:
        with self.assertRaisesRegex(clipboard.ClipboardImportError, "BOM UTF-8"):
            clipboard.check_text("\ufeff" + self.source)

    def test_markdown_fence_is_rejected(self) -> None:
        with self.assertRaisesRegex(clipboard.ClipboardImportError, "Markdown"):
            clipboard.check_text("```\n" + self.source + "\n```")

    def test_localized_structural_keyword_is_rejected(self) -> None:
        mutated = self.source.replace("variables\n{", "variabili\n{", 1)
        with self.assertRaises(clipboard.ClipboardImportError):
            clipboard.check_text(mutated)

    def test_smart_quote_in_rule_header_is_rejected(self) -> None:
        mutated = self.source.replace('rule("', 'rule(“', 1)
        with self.assertRaises(clipboard.ClipboardImportError):
            clipboard.check_text(mutated)

    def test_italian_words_inside_custom_strings_are_allowed(self) -> None:
        mutated = self.source.replace('Custom String("Lowercase")', 'Custom String("azioni e condizioni")', 1)
        report = clipboard.check_text(mutated)
        self.assertGreater(report.rule_count, 0)

    def test_unclosed_string_is_rejected(self) -> None:
        mutated = self.source.replace('Custom String("Lowercase")', 'Custom String("Lowercase)', 1)
        with self.assertRaisesRegex(clipboard.ClipboardImportError, "stringa Workshop non chiusa"):
            clipboard.check_text(mutated)

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
            clipboard.check_text(oversized)


if __name__ == "__main__":
    unittest.main()
