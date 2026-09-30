from __future__ import annotations

import unittest
from unittest.mock import patch

from tools import validate_workshop as validator


class StringMaskCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        validator.mask_strings.cache_clear()
        self.addCleanup(validator.mask_strings.cache_clear)

    def test_masking_preserves_offsets_escapes_and_line_breaks(self) -> None:
        examples = (
            ('x = "quoted"; y', 'x =         ; y'),
            ('"a\\"b" after', '       after'),
            ('"งู\r\nแรร์" tail', '   \r\n      tail'),
            ('before "unterminated\\', 'before               '),
        )
        for source, expected in examples:
            with self.subTest(source=source):
                self.assertEqual(validator.mask_strings(source), expected)
                self.assertEqual(validator.mask_strings(source), expected)
                self.assertEqual(len(expected), len(source))

    def test_mutation_with_same_length_does_not_reuse_previous_mask(self) -> None:
        hidden = '"Wait(1)"; X(1);'
        visible = ' Wait(1) ; "X"; '
        self.assertEqual(len(hidden), len(visible))
        self.assertEqual(list(validator.iter_calls(hidden, 'Wait')), [])
        self.assertEqual([call.args for call in validator.iter_calls(visible, 'Wait')], [('1',)])
        self.assertEqual(list(validator.iter_calls(hidden, 'Wait')), [])

    def test_cache_evicts_old_inputs_and_keeps_results_immutable(self) -> None:
        first = 'prefix "first" tail'
        expected = validator.mask_strings(first)
        capacity = validator.mask_strings.cache_info().maxsize
        self.assertIsNotNone(capacity)
        for index in range(capacity):
            validator.mask_strings(f'"{index}"')
        before = validator.mask_strings.cache_info()
        self.assertEqual(before.currsize, capacity)
        self.assertIsInstance(expected, str)
        self.assertEqual(validator.mask_strings(first), expected)
        self.assertEqual(validator.mask_strings.cache_info().misses, before.misses + 1)

    def test_semantic_errors_match_without_cache_after_mutation(self) -> None:
        source = '''rule("global") {
            event { Ongoing - Global; }
            actions { "Stop Camera(Event Player);" }
        }'''
        changed = source.replace('"Stop Camera(Event Player);"', 'Stop Camera(Event Player);')
        candidates = (source, changed, source)

        def errors(candidate: str) -> list[str]:
            return validator.global_player_context_errors(validator.extract_rules(candidate))

        with patch.object(validator, 'mask_strings', validator.mask_strings.__wrapped__):
            expected = [errors(candidate) for candidate in candidates]
        actual = [errors(candidate) for candidate in candidates]
        self.assertEqual(expected[0], [])
        self.assertTrue(expected[1])
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
