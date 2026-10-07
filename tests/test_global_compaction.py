"""Evaluate backend compactions against their uncompressed logical expressions.

This checks Boolean values, menu text and mathematical palette results. It does
not emulate native rendering, engine element counts or team-change crashes.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path
import re
import unittest

from tests.test_fly_motion import Vector
from tests.test_global_controller_execution import ControllerExpression
from tools import build_global_runtime as compiler
from tools import check_clipboard_import as clipboard
from tools import validate_workshop as semantic


ROOT = Path(__file__).resolve().parents[1]


class CompactionContext:
    """Strict expression inputs; no source text is passed to Python eval."""

    def __init__(self, fields):
        self.fields = set(fields)
        self.player = {field: False for field in fields}
        self.globals = {"PemainPemicu": "owner", "PemainAktif": "owner",
                        "PemainPukulanSuper": [], "Siap": True}
        self.values = {}
        self.native = {name: False for name in (
            "EntityExists", "IsAlive", "IsDummyBot", "HasSpawned",
            "IsOnGround", "IsInSpawnRoom", "IsButtonHeld", "HasStatus")}
        self.native["Health"] = 0

    def resolve(self, name):
        if name in self.values:
            return self.values[name]
        if name == "True": return True
        if name == "False": return False
        if name == "Null": return None
        if name == "EmptyArray": return []
        if name in ("LocalPlayer", "EventPlayer"): return "owner"
        if name in self.fields: return name
        if name.startswith("Global."):
            parts = name.split(".")
            if len(parts) == 3:
                return self.player[parts[2]]
            return self.globals[parts[1]]
        if name in ("PrimaryFire", "SecondaryFire", "Interact", "Melee", "Reload", "Jump", "Unkillable"):
            return name
        raise AssertionError(f"unsupported compaction value: {name}")

    def call(self, name, args):
        if name in ("EvaluateOnce", "Button"): return args[0]
        if name == "PlayerVariable":
            if args[0] != "owner":
                raise AssertionError("compaction resolved a different owner")
            return self.player[args[1]]
        if name == "Array": return args
        if name == "MappedArray": return [args[1] for _ in args[0]]
        if name == "And": return all(args)
        if name == "Or": return any(args)
        if name == "Not": return not args[0]
        if name == "ArrayContains": return args[1] in args[0]
        if name == "Vector": return Vector(*args)
        if name == "InputBindingString": return f"<{args[0]}>"
        if name == "CustomString":
            result = args[0]
            for index, value in enumerate(args[1:]):
                result = result.replace("{" + str(index) + "}", str(value))
            return result
        if name in self.native: return self.native[name]
        raise AssertionError(f"unsupported compaction function: {name}")

    def parse(self, expression):
        def literal(match):
            key = "_literal" + str(len(self.values))
            self.values[key] = json.loads(match[0], strict=False)
            return key
        packed = re.sub(r'"(?:\\.|[^"\\])*"', literal, expression)
        return ControllerExpression(re.sub(r"\s+", "", packed))


def rule_for(expression):
    return 'rule("Compaction")\n{\n event\n{\n Subroutine;\n Test;\n}\n actions\n{\n If(' + expression + ');\n End;\n}\n}'


def folded_operand(expression, initialization=""):
    source = rule_for(expression)
    if initialization:
        source = source.replace("If(", initialization + "\n If(", 1)
    folded = compiler.compact_booleans(source)
    return next(semantic.iter_calls(folded, "If")).args[0]


class GlobalCompactionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.logical = compiler.translate((ROOT / "source/ruang_irama.it-IT.source").read_text(encoding="utf-8"))
        cls.runtime, _ = compiler.build_english((ROOT / "source/ruang_irama.it-IT.source").read_text(encoding="utf-8"))
        cls.rules = semantic.extract_rules(cls.logical)
        cls.emitted = semantic.extract_rules(cls.runtime)
        _, fields, _, _ = semantic.declaration_entries(cls.logical)
        cls.fields = [field.name for field in fields]

    def context(self):
        return CompactionContext(self.fields)

    def assert_value_equal(self, before, after, context):
        left, right = before.evaluate(context), after.evaluate(context)
        if isinstance(left, Vector):
            self.assertIsInstance(right, Vector)
            for a, b in zip((left.x, left.y, left.z), (right.x, right.y, right.z)):
                self.assertAlmostEqual(a, b, places=9)
        else:
            self.assertEqual(left, right)

    def test_typed_boolean_functions_and_live_flags_keep_their_truth_table(self):
        functions = ("Entity Exists", "Is Alive", "Is Dummy Bot", "Has Spawned",
                     "Is On Ground", "Is In Spawn Room", "Is Button Held", "Has Status")
        operands = [f"{name}(Global.PemainPemicu)" for name in functions[:-2]]
        operands += ["Is Button Held(Global.PemainPemicu, Button(Jump))", "Has Status(Global.PemainPemicu, Unkillable)"]
        operands += ["Global.PemainPemicu.Manusia", "Global.PemainPemicu.MenuTerbuka",
                     "Player Variable(Local Player, ModeTerbangAktif)", "Global.Siap"]
        context = self.context()
        initialization = "Global.PemainPemicu.Manusia = True; Global.PemainPemicu.MenuTerbuka = False; Global.PemainPemicu.ModeTerbangAktif = True; Global.Siap = True;"
        for operand, operation, boolean in itertools.product(operands, ("==", "!="), ("True", "False")):
            expression = f"{operand} {operation} {boolean}"
            before = context.parse(expression)
            folded = folded_operand(expression, initialization)
            self.assertNotRegex(folded, r"==|!=", "typed comparisons should actually be compacted")
            after = context.parse(folded)
            for value in (False, True):
                context.player.update(Manusia=value, MenuTerbuka=value, ModeTerbangAktif=value)
                context.globals["Siap"] = value
                context.native.update({key: value for key in context.native if key != "Health"})
                with self.subTest(expression=expression, value=value):
                    self.assert_value_equal(before, after, context)

    def test_nested_boolean_logic_and_double_negation_preserve_results(self):
        expression = "Not(Not(And(Global.PemainPemicu.Manusia == True, Or(Is Alive(Global.PemainPemicu) == False, Global.Siap != False)))) == True"
        context = self.context()
        before, after = context.parse(expression), context.parse(folded_operand(expression))
        for human, alive, ready in itertools.product((False, True), repeat=3):
            context.player["Manusia"] = human
            context.native["IsAlive"] = alive
            context.globals["Siap"] = ready
            self.assert_value_equal(before, after, context)

    def test_unknown_numbers_are_not_reclassified_as_boolean_flags(self):
        context = self.context()
        for expression in ("Health(Global.PemainPemicu) == True", "Global.Number == False",
                           "Global.Number != True"):
            folded = folded_operand(expression)
            self.assertRegex(folded, r"==|!=", "unknown scalar comparison must remain explicit")
            before, after = context.parse(expression), context.parse(folded)
            for value in (0, 1, 2, -1, 100):
                context.native["Health"] = value
                context.globals["Number"] = value
                self.assert_value_equal(before, after, context)

    def test_double_negation_keeps_a_boolean_result_for_unknown_numbers(self):
        context = self.context()
        expression = "Not(Not(Health(Global.PemainPemicu)))"
        before, after = context.parse(expression), context.parse(folded_operand(expression))
        for value in (0, 1, 2, -1, 100):
            context.native["Health"] = value
            self.assert_value_equal(before, after, context)
            self.assertIs(type(after.evaluate(context)), bool)

    def test_fields_with_mixed_boolean_and_numeric_writes_keep_comparisons(self):
        source = rule_for("Global.Mixed == True").replace("If(", "Global.Mixed = True;\n Global.Mixed = 2;\n If(", 1)
        after = next(semantic.iter_calls(compiler.compact_booleans(source), "If")).args[0]
        self.assertIn("==", after)
        context = self.context()
        before, emitted = context.parse("Global.Mixed == True"), context.parse(after)
        for value in (False, True, 0, 1, 2):
            context.globals["Mixed"] = value
            self.assert_value_equal(before, emitted, context)

    def test_numeric_alias_dependencies_invalidate_boolean_inference(self):
        assignments = "Global.Broken = True; Global.Broken = 2; Global.Alias = True; Global.Alias = Global.Broken;"
        after = folded_operand("Global.Alias == True", assignments)
        self.assertIn("==", after)
        context = self.context()
        before, emitted = context.parse("Global.Alias == True"), context.parse(after)
        for value in (False, True, 0, 1, 2):
            context.globals["Alias"] = value
            self.assert_value_equal(before, emitted, context)

    def test_literal_bytes_are_preserved_even_when_they_look_like_code(self):
        quoted = json.dumps('งูแรร์ / COZYWATCH; {0}; "quote"; Global.PemainPemicu.Manusia == True', ensure_ascii=False)
        source = 'rule("Literal")\n{\n event\n{\n Subroutine;\n Test;\n}\n actions\n{\n Small Message(Global.PemainPemicu, Custom String(' + quoted + ', True));\n}\n}'
        before = list(re.findall(r'"(?:\\.|[^"\\])*"', source))
        after = list(re.findall(r'"(?:\\.|[^"\\])*"', compiler.compact_booleans(source)))
        self.assertEqual(before, after)

    def test_menu_palette_matches_all_pages_name_colours_and_fallbacks(self):
        original = next(rule for rule in self.rules if compiler.prefix(rule) == "91k")
        lowered = compiler.persistent(compiler.actor_text(original.body))
        compacted = compiler.compact_palette(lowered)
        before = list(semantic.iter_calls(lowered, "Chase Player Variable Over Time"))[-1]
        after = list(semantic.iter_calls(compacted, "Chase Player Variable Over Time"))[-1]
        self.assertEqual(before.args[:2] + before.args[3:4], after.args[:2] + after.args[3:4])
        self.assertEqual(before.args[4], 'Destination and Duration')
        self.assertEqual(after.args[4], 'None')
        original_vectors = [call.raw for call in semantic.iter_calls(before.args[2], "Vector")]
        compact_vectors = [call.raw for call in semantic.iter_calls(after.args[2], "Vector")]
        self.assertEqual(original_vectors, compact_vectors[1:])
        context = self.context()
        context.globals["DaftarWarnaRGB"] = [Vector(i * 6, 255 - i * 6, i * 3) for i in range(40)]
        left, right = context.parse(before.args[2]), context.parse(after.args[2])
        pages = [(-1, cursor) for cursor in range(16)] + [(page, 7) for page in range(16)] + [(-2, 7), (16, 7)]
        for (page, cursor), index in itertools.product(pages, range(40)):
            context.player.update(HalamanMenu=page, KursorUtama=cursor, IndeksWarna=index, KursorWarna=(index * 7) % 40)
            with self.subTest(page=page, cursor=cursor, colour=index):
                self.assert_value_equal(left, right, context)

    def test_main_menu_text_matches_every_language_and_cursor_with_live_states(self):
        original = next(rule for rule in self.rules if compiler.prefix(rule) == "91a")
        before = next(semantic.iter_calls(compiler.persistent(compiler.actor_text(original.body)), "Create HUD Text"))
        after = next(semantic.iter_calls(next(rule for rule in self.emitted if compiler.prefix(rule) == "91a").body, "Create HUD Text"))
        context = self.context()
        for name in ("NamaWarnaInggris", "NamaWarna", "NamaWarnaThai", "DaftarGenre", "NamaBahasa",
                     "DaftarIkon", "NamaIkonInggris", "NamaIkonIndonesia", "NamaIkonThai"):
            context.globals[name] = [f"{name}:{index}" for index in range(200)]
        context.player.update(IndeksWarna=3, KursorWarna=3, IndeksGenre=17, MusikKhusus=None,
                              PemainDipilih="vote target", TargetKamera="camera target", IndeksIkon=23,
                              TingkatLompatGanda=10)
        parsed = [(context.parse(before.args[index]), context.parse(after.args[index])) for index in (2, 3)]
        for language, cursor, state in itertools.product(range(3), range(16), range(4)):
            context.player.update(IndeksBahasa=language, KursorUtama=cursor, ModeKamera=state % 3,
                                  ModeKebal=state % 3, IndeksSuara=state, PutaranKartuNasib=state,
                                  TeleportasiJongkokDiaktifkan=bool(state % 2), PrivasiInspeksiAktif=bool(state % 2),
                                  KartuNasibAktif=bool(state % 2), IzinkanBotBuatanMengikuti=bool(state % 2),
                                  ModeLompatGanda=bool(state % 2), ModeHantuAktif=bool(state % 2), ModeTerbangAktif=bool(state % 2))
            context.globals["PemainPukulanSuper"] = ["owner"] if state % 2 else []
            with self.subTest(language=language, cursor=cursor, state=state):
                for left, right in parsed:
                    self.assert_value_equal(left, right, context)

    def test_fixed_registry_arrays_keep_lengths_contents_and_initialization_order(self):
        original = next(rule for rule in self.rules if compiler.prefix(rule) == "00")
        emitted = next(rule for rule in self.emitted if compiler.prefix(rule) == "00")
        wanted = {"SlotHUDTersedia"}
        for statement in semantic.split_top_level(semantic.rule_block(original, "actions"), ";"):
            match = re.search(r"Global\.(\w+)\s*=\s*(Array\(.*\))\s*$", statement.strip(), re.S)
            if match:
                calls = list(semantic.iter_calls(match[2], "Array"))
                if calls and len(calls[0].args) in (12, 24) and set(calls[0].args) in ({"0"}, {"Null"}):
                    wanted.add(match[1])
        results = []
        for rule in (original, emitted):
            context = self.context()
            uncommented = re.sub(r'(?m)^[ \t]*"(?:\\.|[^"\\])*"[ \t]*(?:\r?\n|$)', "", semantic.rule_block(rule, "actions"))
            for statement in semantic.split_top_level(uncommented, ";"):
                match = re.match(r"\s*Global\.(\w+)\s*=\s*(.*?)\s*$", statement, re.S)
                if match and match[1] in wanted:
                    context.globals[match[1]] = context.parse(match[2]).evaluate(context)
            results.append({name: context.globals[name] for name in wanted})
        self.assertGreaterEqual(len(wanted), 10)
        self.assertEqual(*results)

    def test_localized_catalogues_icons_and_colour_constants_are_unchanged(self):
        names = {"DaftarGenre", "DaftarWarna", "DaftarWarnaRGB", "DaftarIkon", "NamaBahasa",
                 "NamaWarna", "NamaWarnaInggris", "NamaWarnaThai", "NamaIkonInggris",
                 "NamaIkonIndonesia", "NamaIkonThai", "NamaHalaman", "NamaHalamanInggris",
                 "NamaHalamanThai"}
        tables = []
        for rules in (self.rules, self.emitted):
            rule = next(rule for rule in rules if compiler.prefix(rule) == "00")
            body = re.sub(r'(?m)^[ \t]*"(?:\\.|[^"\\])*"[ \t]*(?:\r?\n|$)', "", semantic.rule_block(rule, "actions"))
            catalogue = {}
            for statement in semantic.split_top_level(body, ";"):
                match = re.match(r"\s*Global\.(\w+)\s*=\s*(.*?)\s*$", statement, re.S)
                if match and match[1] in names:
                    catalogue[match[1]] = clipboard.canonical_semantic_text(match[2], "en-US")
            self.assertEqual(names, set(catalogue))
            tables.append(catalogue)
        self.assertEqual(*tables)

    def test_oversized_runtime_is_rejected_without_raising_the_offline_budget(self):
        self.assertEqual(clipboard.SOURCE_TOTAL_STRUCTURAL_TARGET, 32_000)
        extra = '\nrule("Overflow")\n{\nevent\n{\nOngoing - Global;\n}\nactions\n{\nGlobal.Siap = Array(' + ', '.join(["0"] * 1200) + ');\n}\n}\n'
        oversized = self.runtime + extra * 12
        self.assertLess(clipboard.structural_rule_units(extra, clipboard.LANGUAGE_PROFILES["en-US"]), 5000)
        with self.assertRaisesRegex(clipboard.ClipboardImportError, r"budget locale|structural"):
            clipboard.check_text(oversized, "en-US")


class GlobalExpressionEmissionTests(unittest.TestCase):
    def test_signed_numbers_keep_native_literal_syntax_in_every_value_position(self):
        source = '''rule("Angka")
{
 event { Subroutine; Angka; }
 actions {
  Global.IndeksKeluar = -1;
  Global.PemainPemicu.HalamanMenu = -1;
  Global.PemainPemicu.ModeKebal = +1;
  For Global Variable(IndeksKeluar, 0, -1, -1); End;
  If(Global.PemainPemicu.HalamanMenu == -1); End;
  Global.PemainPemicu.PosisiMati = Vector(-0.500, -2, 3);
 }
}
'''
        emitted = compiler.compact_booleans(source)
        for literal in ('= -1;', '= 1;', '0, -1, -1)', '== -1)', 'Vector(-0.500, -2, 3)'):
            self.assertIn(literal, emitted)
        self.assertNotRegex(emitted, r'[-+]\s*\(')

    def test_expression_negation_uses_native_values_and_keeps_grouping(self):
        for source, expected in (
            ('-(Global.Number + 1)', 'Multiply(-1, (Global.Number + 1))'),
            ('-Vector(1, 2, 3)', 'Multiply(-1, Vector(1, 2, 3))'),
            ('!Global.Flag', 'Not(Global.Flag)'),
            ('+(Global.Number + 1)', '(Global.Number + 1)'),
        ):
            with self.subTest(source=source):
                self.assertEqual(compiler._emit(compiler._Expression(source).tree), expected)

    def test_actual_import_restores_negative_sentinels_and_contains_no_unary_parentheses(self):
        runtime = (ROOT / 'workshop/ruang_irama.it-IT.workshop').read_text(encoding='utf-8')
        syntax = semantic.mask_strings(runtime)
        self.assertIn('Globale.IndeksKeluar = -1;', syntax)
        self.assertIn('Globale.SlotHUDTerakhir = -1;', syntax)
        self.assertIn('Globale.PemainPemicu.HalamanMenu = -1;', syntax)
        self.assertNotRegex(syntax, r'(?:^|[=,(\[?:<>+*/%\-])\s*[-+]\s*\(')


class GlobalTranslationTests(unittest.TestCase):
    def test_italian_translation_preserves_native_compound_identifiers(self):
        english = '''variables { global: 0: Daftar player: 0: Nilai }
Ongoing - Global;
Player Died; All; All;
Global.Daftar = All Players(All Teams);
For Global Variable(Daftar, 0, 1, 1); End;
Modify Global Variable(Daftar, Append To Array, 0);
If(Is True For All(Empty Array, True)); End;
Custom String("Global. All; Ongoing - Global; All Players");
'''
        expected = '''variabili { globale: 0: Daftar giocatore: 0: Nilai }
Ongoing - Global;
Player Died; Tutti; Tutti;
Globale.Daftar = All Players(All Teams);
For Global Variable(Daftar, 0, 1, 1); End;
Modify Global Variable(Daftar, Append To Array, 0);
If(Is True For All(Empty Array, True)); End;
Custom String("Global. All; Ongoing - Global; All Players");
'''
        self.assertEqual(compiler.translate(english, to_italian=True), expected)

    def test_import_artifact_keeps_all_native_function_identifiers(self):
        italian = (ROOT / 'workshop/ruang_irama.it-IT.workshop').read_text(encoding='utf-8')
        english = (ROOT / 'tests/fixtures/global_runtime_reference.txt').read_text(encoding='utf-8')
        syntax = semantic.mask_strings(english)
        names = set(re.findall(r'\b([A-Z][A-Za-z0-9]*(?:[ -][A-Za-z0-9]+)*)\s*\(', syntax))
        self.assertGreater(len(names), 80)
        for name in sorted(names):
            with self.subTest(native=name):
                self.assertEqual(len(list(semantic.iter_calls(italian, name))),
                                 len(list(semantic.iter_calls(english, name))), name)


if __name__ == "__main__":
    unittest.main()
