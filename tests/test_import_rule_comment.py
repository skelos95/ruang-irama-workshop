"""Guard the conservative title workaround for the reported native import error.

This is a project regression check, not an implementation of Blizzard's filter.
The native rejection and the pasted text's line numbering still need client QA.
"""
import re
import unittest

from tests.test_roster_rejoin_regressions import SOURCES
from tools import validate_workshop as validator


class RuleCommentImportTests(unittest.TestCase):
    def test_rule_comments_avoid_the_reported_title_fragment(self):
        for path, _, _ in SOURCES:
            with self.subTest(source=path.name):
                source = path.read_text(encoding='utf-8')
                titles = re.findall(r'(?m)^(?:rule|regola)\("([^"\n]*)"\)', source)
                self.assertTrue(titles)
                for title in titles:
                    # "sementara" is valid Indonesian, but contains a possible
                    # English filter match. Keep this safeguard title-only.
                    self.assertNotIn('semen', title.casefold(), title)
                self.assertIn('TemporaryTextOwners', source)

    def test_renamed_rule_keeps_the_same_cleanup_subroutine(self):
        for path, _, _ in SOURCES:
            with self.subTest(source=path.name):
                source = path.read_text(encoding='utf-8')
                source = re.sub(r'(?m)^regola\(', 'rule(', source)
                source = source.replace('\tevento\n', '\tevent\n')
                rules = validator.extract_rules(source)
                cleanup = validator.rule_by_subroutine(rules, 'CleanupOrphanedText')
                self.assertIsNotNone(cleanup)
                self.assertEqual(cleanup.name, '93d - Subroutine: Clean up orphaned text')


if __name__ == '__main__':
    unittest.main()
