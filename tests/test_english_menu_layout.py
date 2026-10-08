"""Check the rendered row structure and first-registration menu behavior.

Native HUD alignment remains a game-client check. These tests exercise the
actual string tree and registration assignments in the maintained artifacts.
"""
import json
from pathlib import Path
import re
import unittest

from tools import build_global_runtime as compiler
from tools import validate_workshop as validator
from tests.test_roster_rejoin_regressions import LifecycleSourceEvaluator, SOURCES

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = (*[path for path, _, _ in SOURCES],
             ROOT / "workshop/ruang_irama.en-US.workshop")
MENU_PREFIXES = ("91a", "91b", "91c", "91d", "91f", "91g", "91h",
                 "91i", "91j", "91n", "91o", "91s", "91t")


def string_format(node):
    if node.kind == "call" and node.value == "Custom String":
        return json.loads(node.children[0].value, strict=False)
    return None


def rows(node):
    if string_format(node) == "{0}\n{1}":
        return rows(node.children[1]) + rows(node.children[2])
    return [node]


class RegistrationMenuEvaluator(LifecycleSourceEvaluator):
    def register(self, identity):
        if not self.join(identity):
            return False
        after_hud = self.classifier[self.classifier.index("Create HUD Text("):]
        for statement in validator.split_top_level(after_hud, ";"):
            statement = statement.strip()
            if re.match(r"Event Player\.(?:MainMenuCursor|MenuPage|MenuOpen) =", statement):
                self.execute_assignment(statement)
        return True


class EnglishMenuLayoutTests(unittest.TestCase):
    def test_commands_and_options_share_paired_rows_in_one_hud(self):
        for path in ARTIFACTS:
            rules = validator.extract_rules(path.read_text(encoding="utf-8"))
            for prefix in MENU_PREFIXES:
                with self.subTest(artifact=path.name, menu=prefix):
                    rule = next(rule for rule in rules if compiler.prefix(rule) == prefix)
                    calls = list(validator.iter_calls(rule.body, "Create HUD Text"))
                    self.assertEqual(len(calls), 1)
                    self.assertEqual(calls[0].args[1:3], ("Null", "Null"))
                    paired = rows(compiler._Expression(calls[0].args[3]).tree)
                    self.assertLessEqual(len(paired), 5)
                    all_buttons = []
                    for row in paired:
                        self.assertEqual(string_format(row), "{0} | {1}")
                        self.assertEqual(len(row.children), 3)
                        left = compiler._emit(row.children[1])
                        for text in validator.iter_calls(left, "Custom String"):
                            self.assertNotIn("\n", validator.parse_literal(text.args[0]))
                        all_buttons.extend(call.args[0] for call in validator.iter_calls(left, "Button"))
                    self.assertIn("Crouch", all_buttons)
                    self.assertIn("Interact", all_buttons)

    def test_info_has_all_bindings_without_an_extra_commands_subtitle(self):
        expected = {"Crouch", "Primary Fire", "Secondary Fire", "Interact",
                    "Reload", "Melee", "Ability 1", "Ability 2", "Jump"}
        for path in ARTIFACTS:
            with self.subTest(artifact=path.name):
                rules = validator.extract_rules(path.read_text(encoding="utf-8"))
                info = next(rule for rule in rules if compiler.prefix(rule) == "91e")
                call = next(validator.iter_calls(info.body, "Create HUD Text"))
                self.assertEqual(call.args[1:3], ("Null", "Null"))
                self.assertEqual({button.args[0] for button in
                    validator.iter_calls(call.args[3], "Button")}, expected)
                literals = [validator.parse_literal(item.args[0]) for item in
                            validator.iter_calls(call.args[3], "Custom String")]
                for topic in ("0 - INFO / CONTROLS", "Soundtrack:", "Travel ON:",
                              "Attached, menu closed:", "Dead:", "Multijump ON:", "Superman Punch ON:"):
                    self.assertTrue(any(topic in text for text in literals))

    def test_registration_opens_info_preview_once_and_rejoin_resets_it(self):
        for path, _, _ in SOURCES:
            with self.subTest(artifact=path.name):
                model = RegistrationMenuEvaluator(path.read_text(encoding="utf-8"))
                self.assertTrue(model.register("newcomer"))
                state = model.players["newcomer"]
                self.assertEqual((state["MainMenuCursor"], state["MenuPage"], state["MenuOpen"]),
                                 (0, -1, True))
                state.update(MainMenuCursor=7, MenuPage=-1, MenuOpen=False)
                self.assertFalse(model.register("newcomer"))
                self.assertEqual((state["MainMenuCursor"], state["MenuPage"], state["MenuOpen"]),
                                 (7, -1, False))
                model.remove("newcomer")
                self.assertTrue(model.register("newcomer"))
                self.assertEqual((state["MainMenuCursor"], state["MenuPage"], state["MenuOpen"]),
                                 (0, -1, True))


if __name__ == "__main__":
    unittest.main()
