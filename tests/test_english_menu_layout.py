"""Check the HUD fields and first-registration menu behavior.

Native HUD alignment remains a game-client check. These tests exercise the
actual string tree and registration assignments in the maintained artifacts.
"""
from pathlib import Path
import re
import unittest

from tools import build_global_runtime as compiler
from tools import validate_workshop as validator
from tests.test_roster_rejoin_regressions import LifecycleSourceEvaluator, SOURCES
from tests.runtime_selection import rule_for_logical_id
from tests.test_global_compaction import CompactionContext

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = (*[path for path, _, _ in SOURCES],
             ROOT / "workshop/ruang_irama.en-US.workshop")
MENU_PREFIXES = ("91a", "91b", "91c", "91d", "91f", "91g", "91h",
                 "91i", "91j", "91n", "91o", "91s", "91t")
MAIN_INFO_CONTROLS = (
    ("CAMERA: hold Interact ({0}) 0.5s with Crouch ({1}) released", ("Interact", "Crouch")),
    ("ARCADE: hold Melee ({0}) 0.5s: open / close", ("Melee",)),
    ("HERO + HP INSPECTION: hold Crouch ({0}); Arcade closed, Travel OFF or Teleport Player/Bot / Attach", ("Crouch",)),
    ("MENU: hold Crouch ({0}) + Primary Fire ({1}) / Secondary Fire ({2}): next / prev",
     ("Crouch", "Primary Fire", "Secondary Fire")),
    ("Hold Crouch ({0}) + Interact ({1}): all controls | in submenu: + Reload ({2}): back",
     ("Crouch", "Interact", "Reload")),
)


def main_menu_branch(expression, cursor):
    """Select only the explicit Info-zero exception in each native HUD field."""
    node = compiler._Expression(expression).tree
    if node.kind != "conditional":
        raise AssertionError("main menu HUD fields must branch explicitly on Info 0")
    condition = re.sub(r"\s+", "", compiler._emit(node.children[0])).strip("()")
    if condition not in ("EventPlayer.MainMenuCursor==0",
                         "PlayerVariable(LocalPlayer,MainMenuCursor)==0"):
        raise AssertionError(f"unexpected main menu Info guard: {condition}")
    return node.children[1 if cursor == 0 else 2]


def soundtrack_branch_bindings(node, locked):
    """Choose the actual lock branch before collecting its displayed buttons."""
    if node.kind == "conditional":
        condition = re.sub(r"\s+", "", compiler._emit(node.children[0]))
        if any(owner in condition for owner in (".CustomSoundtrack!=Null",
                                               "PlayerVariable(LocalPlayer,CustomSoundtrack)!=Null")):
            return soundtrack_branch_bindings(node.children[1 if locked else 2], locked)
    if node.kind == "call" and node.value == "Button":
        return [compiler._emit(node.children[0])]
    return [button for child in node.children
            for button in soundtrack_branch_bindings(child, locked)]


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
    def test_commands_use_subtitle_and_functions_use_text_in_one_hud(self):
        for path in ARTIFACTS:
            rules = validator.extract_rules(path.read_text(encoding="utf-8"))
            for prefix in MENU_PREFIXES:
                with self.subTest(artifact=path.name, menu=prefix):
                    rule = rule_for_logical_id(rules, prefix)
                    calls = list(validator.iter_calls(rule.body, "Create HUD Text"))
                    self.assertEqual(len(calls), 1)
                    self.assertEqual(calls[0].args[1], "Null")
                    self.assertNotEqual(calls[0].args[2], "Null")
                    self.assertNotEqual(calls[0].args[3], "Null")
                    subtitle, content = calls[0].args[2:4]
                    if prefix == "91a":
                        info_subtitle = main_menu_branch(subtitle, 0)
                        self.assertEqual(compiler._emit(info_subtitle), 'Custom String("")')
                        _, fields, _, _ = validator.declaration_entries(path.read_text(encoding="utf-8"))
                        context = CompactionContext([field.name for field in fields])
                        for name in ("ColorNames", "GenreNames", "PlayerIcons", "IconNames"):
                            context.globals[name] = [f"{name}:{index}" for index in range(200)]
                        context.player.update(GenreIndex=-1, CustomSoundtrack=None,
                                              VotedPlayer=None, CameraTarget="camera target")
                        context.player["MainMenuCursor"] = 0
                        text_tree = context.parse(compiler.actor_text(content))
                        subtitle_tree = context.parse(compiler.actor_text(subtitle))
                        rendered = text_tree.evaluate(context)
                        expected_lines = ["0 - INFO / CONTROLS", *(
                            literal.format(*(f"<{button.replace(' ', '')}>" for button in buttons))
                            for literal, buttons in MAIN_INFO_CONTROLS)]
                        self.assertEqual(rendered.splitlines(), expected_lines)
                        self.assertEqual(subtitle_tree.evaluate(context), "")
                        for cursor in range(1, 16):
                            with self.subTest(cursor=cursor):
                                normal_content = compiler._emit(main_menu_branch(content, cursor))
                                self.assertEqual(list(validator.iter_calls(normal_content, "Input Binding String")), [])
                                context.player["MainMenuCursor"] = cursor
                                rendered = text_tree.evaluate(context)
                                self.assertIn(len(rendered.splitlines()), (1, 2))
                                self.assertNotIn("\n\n", rendered)
                                self.assertTrue(rendered.startswith(f"{cursor} - "))
                                self.assertIn("<Interact>", subtitle_tree.evaluate(context))
                        context.player["MainMenuCursor"] = 0
                        self.assertEqual(text_tree.evaluate(context).splitlines(), expected_lines)
                        self.assertEqual(subtitle_tree.evaluate(context), "")
                        subtitle = compiler._emit(main_menu_branch(subtitle, 1))
                        content = compiler._emit(main_menu_branch(content, 1))
                    self.assertEqual(list(validator.iter_calls(content, "Input Binding String")), [])
                    for text in validator.iter_calls(subtitle, "Custom String"):
                        self.assertNotIn("\n", validator.parse_literal(text.args[0]))
                    all_buttons = [call.args[0] for call in validator.iter_calls(subtitle, "Button")]
                    self.assertIn("Crouch", all_buttons)
                    self.assertIn("Interact", all_buttons)
                    if prefix != "91g":
                        self.assertIn("Melee", all_buttons)
                    if prefix == "91b":
                        tree = compiler._Expression(subtitle).tree
                        self.assertEqual(soundtrack_branch_bindings(tree, True),
                                         ["Crouch", "Reload", "Melee"])
                        self.assertEqual(soundtrack_branch_bindings(tree, False),
                                         ["Crouch", "Primary Fire", "Secondary Fire",
                                          "Ability 1", "Ability 2", "Interact", "Reload", "Melee"])

    def test_compiled_main_hud_reevaluates_info_and_name_color_with_empty_global_actors(self):
        for path in (ROOT / "workshop/ruang_irama.en-US.workshop",
                     ROOT / "tests/fixtures/global_runtime_reference.txt"):
            with self.subTest(artifact=path.name):
                text = path.read_text(encoding="utf-8")
                rule = validator.rule_by_subroutine(validator.extract_rules(text), "DrawMainMenu")
                hud = next(validator.iter_calls(rule.body, "Create HUD Text"))
                _, fields, _, _ = validator.declaration_entries(text)
                context = CompactionContext([field.name for field in fields])
                context.globals["ColorNames"] = ["White"]
                subtitle = context.parse(hud.args[2])
                body = context.parse(hud.args[3])
                context.globals.update(TriggerPlayer=None, ActivePlayer=None)
                expected = ["0 - INFO / CONTROLS", *(
                    literal.format(*(f"<{button.replace(' ', '')}>" for button in buttons))
                    for literal, buttons in MAIN_INFO_CONTROLS)]
                for cursor in (0, 1, 0):
                    context.player["MainMenuCursor"] = cursor
                    rendered_subtitle = subtitle.evaluate(context)
                    rendered_body = body.evaluate(context)
                    if cursor == 0:
                        self.assertEqual(rendered_subtitle, "")
                        self.assertEqual(rendered_body.splitlines(), expected)
                    else:
                        self.assertIn("<Interact>", rendered_subtitle)
                        self.assertIn("<Melee>", rendered_subtitle)
                        self.assertTrue(rendered_body.startswith("1 - NAME COLOR\n"))
                        self.assertIn("White", rendered_body)
                        self.assertNotIn("<Interact>", rendered_body)

    def test_info_has_all_bindings_without_an_extra_commands_subtitle(self):
        expected = {"Crouch", "Primary Fire", "Secondary Fire", "Interact",
                    "Reload", "Melee", "Ability 1", "Ability 2", "Jump"}
        for path in ARTIFACTS:
            with self.subTest(artifact=path.name):
                rules = validator.extract_rules(path.read_text(encoding="utf-8"))
                info = validator.rule_by_subroutine(rules, "DrawInfoMenu")
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
