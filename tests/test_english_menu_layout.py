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
INFO_CONTROLS = (
    ("Hold {0} + {1} / {2}: next / previous", ("Crouch", "Primary Fire", "Secondary Fire")),
    ("Hold {0} + {1}: select / apply | + {2}: back", ("Crouch", "Interact", "Reload")),
    ("Hold {0} 0.5s: open / close Arcade", ("Melee",)),
    ("Hold {0} 0.5s with {1} released: toggle camera", ("Interact", "Crouch")),
    ("Arcade closed: hold {0}: inspect hero + HP (Travel OFF or Teleport Player/Bot / Attach)", ("Crouch",)),
    ("Soundtrack: hold {0} + {1} / {2}: +10 / -10", ("Crouch", "Ability 1", "Ability 2")),
    ("Menu closed, Travel ON: hold {0}; {1} / {2}: next / previous", ("Crouch", "Primary Fire", "Secondary Fire")),
    ("Travel: {0}: use | release {1}: close", ("Interact", "Crouch")),
    ("Attached, menu closed: hold {0} + {1}: detach", ("Crouch", "Reload")),
    ("Dead: press {0} to resurrect on safe ground", ("Jump",)),
    ("Multijump ON: tap / hold {0} in air to boost", ("Jump",)),
    ("Superman Punch ON: use {0} to punch", ("Melee",)),
)


def rendered_control_lines(controls):
    return ["0 - INFO / CONTROLS", *(
        literal.format(*(f"<{button.replace(' ', '')}>" for button in buttons))
        for literal, buttons in controls)]


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


class MenuColorContext(CompactionContext):
    def call(self, name, args):
        if name == "CustomColor":
            return tuple(args)
        if name in ("XComponentOf", "YComponentOf", "ZComponentOf"):
            return args[0][("XComponentOf", "YComponentOf", "ZComponentOf").index(name)]
        return super().call(name, args)


class EnglishMenuLayoutTests(unittest.TestCase):
    def test_commands_and_info_use_subheader_and_functions_use_text_in_one_hud(self):
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
                        self.assertEqual(compiler._emit(main_menu_branch(content, 0)), 'Custom String("")')
                        _, fields, _, _ = validator.declaration_entries(path.read_text(encoding="utf-8"))
                        context = CompactionContext([field.name for field in fields])
                        for name in ("ColorNames", "GenreNames", "PlayerIcons", "IconNames"):
                            context.globals[name] = [f"{name}:{index}" for index in range(200)]
                        context.player.update(GenreIndex=-1, CustomSoundtrack=None,
                                              VotedPlayer=None, CameraTarget="camera target")
                        context.player["MainMenuCursor"] = 0
                        text_tree = context.parse(compiler.actor_text(content))
                        subtitle_tree = context.parse(compiler.actor_text(subtitle))
                        rendered = subtitle_tree.evaluate(context)
                        expected_lines = rendered_control_lines(MAIN_INFO_CONTROLS)
                        self.assertEqual(rendered.splitlines(), expected_lines)
                        self.assertEqual(text_tree.evaluate(context), "")
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
                        self.assertEqual(subtitle_tree.evaluate(context).splitlines(), expected_lines)
                        self.assertEqual(text_tree.evaluate(context), "")
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
                expected = rendered_control_lines(MAIN_INFO_CONTROLS)
                for cursor in (0, 1, 0):
                    context.player["MainMenuCursor"] = cursor
                    rendered_subtitle = subtitle.evaluate(context)
                    rendered_body = body.evaluate(context)
                    if cursor == 0:
                        self.assertEqual(rendered_subtitle.splitlines(), expected)
                        self.assertEqual(rendered_body, "")
                    else:
                        self.assertIn("<Interact>", rendered_subtitle)
                        self.assertIn("<Melee>", rendered_subtitle)
                        self.assertTrue(rendered_body.startswith("1 - NAME COLOR\n"))
                        self.assertIn("White", rendered_body)
                        self.assertNotIn("<Interact>", rendered_body)

    def test_info_has_all_controls_in_one_subheader_with_empty_header_and_text(self):
        expected = {"Crouch", "Primary Fire", "Secondary Fire", "Interact",
                    "Reload", "Melee", "Ability 1", "Ability 2", "Jump"}
        for path in ARTIFACTS:
            with self.subTest(artifact=path.name):
                rules = validator.extract_rules(path.read_text(encoding="utf-8"))
                info = validator.rule_by_subroutine(rules, "DrawInfoMenu")
                calls = list(validator.iter_calls(info.body, "Create HUD Text"))
                self.assertEqual(len(calls), 1)
                call = calls[0]
                self.assertEqual(call.args[1], "Null")
                self.assertEqual(call.args[3], "Null")
                self.assertEqual({button.args[0] for button in
                    validator.iter_calls(call.args[2], "Button")}, expected)
                _, fields, _, _ = validator.declaration_entries(path.read_text(encoding="utf-8"))
                context = CompactionContext([field.name for field in fields])
                rendered = context.parse(compiler.actor_text(call.args[2])).evaluate(context)
                self.assertEqual(rendered.splitlines(), rendered_control_lines(INFO_CONTROLS))

    def test_info_subheader_keeps_menu_color_and_other_main_commands_keep_their_color(self):
        for path in ARTIFACTS:
            with self.subTest(artifact=path.name):
                text = path.read_text(encoding="utf-8")
                rules = validator.extract_rules(text)
                _, fields, _, _ = validator.declaration_entries(text)
                context = MenuColorContext([field.name for field in fields])
                context.globals.update(TriggerPlayer=None, ActivePlayer=None)
                context.player["MenuColor"] = (190, 210, 230)
                main = validator.rule_by_subroutine(rules, "DrawMainMenu")
                main_hud = next(validator.iter_calls(main.body, "Create HUD Text"))
                color = context.parse(compiler.actor_text(main_hud.args[7]))
                for cursor in (0, 1, 15, 0):
                    context.player["MainMenuCursor"] = cursor
                    self.assertEqual(color.evaluate(context), (190, 210, 230, 255) if cursor == 0
                                     else (210, 230, 255, 255))
                info = validator.rule_by_subroutine(rules, "DrawInfoMenu")
                info_hud = next(validator.iter_calls(info.body, "Create HUD Text"))
                self.assertEqual(context.parse(compiler.actor_text(info_hud.args[7])).evaluate(context),
                                 (190, 210, 230, 255))

    def test_host_row_has_only_one_bottom_blank_row(self):
        for path in ARTIFACTS:
            with self.subTest(artifact=path.name):
                rules = validator.extract_rules(path.read_text(encoding="utf-8"))
                hosts = [call for rule in rules for call in validator.iter_calls(rule.body, "Create HUD Text")
                         if call.args[4].strip() == "Right" and call.args[5].strip() == "0"]
                self.assertEqual(len(hosts), 1)
                node = compiler._Expression(hosts[0].args[3]).tree
                self.assertEqual(node.kind, "conditional")
                row, absent = node.children[1:]
                self.assertEqual((row.kind, row.value), ("call", "Custom String"))
                self.assertEqual(validator.parse_literal(compiler._emit(row.children[0])), "{0} {1} {2}\n ")
                self.assertEqual(len(row.children), 4)
                self.assertEqual(compiler._emit(absent), 'Custom String("")')

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
