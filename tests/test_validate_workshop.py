"""Semantic mutations of the logical behavioral input, before compilation."""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from tools import validate_workshop as validator


class PlayerContextCallGraphTests(unittest.TestCase):
    def errors(self, source: str) -> list[str]:
        return validator.global_player_context_errors(validator.extract_rules(source))

    def fixture(self, origin_actions: str, middle_actions: str = "") -> str:
        return f'''
rule("global") {{ event {{ Ongoing - Global; }} actions {{ {origin_actions} }} }}
rule("middle") {{ event {{ Subroutine; Middle; }} actions {{ {middle_actions} }} }}
rule("local") {{ event {{ Subroutine; Local; }} actions {{ Stop Camera(Event Player); }} }}
'''

    def test_logical_input_has_no_global_event_player_dependencies(self) -> None:
        self.assertEqual(self.errors(validator.SOURCE.read_text(encoding="utf-8")), [])

    def test_direct_global_event_player_use_is_rejected(self) -> None:
        self.assertTrue(self.errors(self.fixture("Stop Camera(Event Player);")))

    def test_direct_and_indirect_player_subroutines_are_rejected(self) -> None:
        self.assertTrue(self.errors(self.fixture("Call Subroutine(Local);")))
        errors = self.errors(self.fixture("Call Subroutine(Middle);", "Call Subroutine(Local);"))
        self.assertTrue(any("global -> Middle -> Local" in error for error in errors))

    def test_start_rule_also_inherits_global_context(self) -> None:
        errors = self.errors(self.fixture("Start Rule(Middle, Do Nothing);", "Call Subroutine(Local);"))
        self.assertTrue(any("global -> Middle -> Local" in error for error in errors))

    def test_recursive_subroutines_terminate_context_analysis(self) -> None:
        errors = self.errors(self.fixture("Call Subroutine(Middle);",
                                         "Call Subroutine(Middle); Call Subroutine(Local);"))
        self.assertEqual(len(errors), 1)

    def test_player_local_callers_and_comment_tokens_are_not_false_positives(self) -> None:
        source = self.fixture('"Call Subroutine(Local); Event Player"', "")
        source += 'rule("player") { event { Ongoing - Each Player; All; All; } actions { Call Subroutine(Local); } }'
        self.assertEqual(self.errors(source), [])

    def test_old_team_switch_calls_fail_even_through_an_extra_shared_subroutine(self) -> None:
        source = validator.SOURCE.read_text(encoding="utf-8")
        rules = validator.extract_rules(source)
        fast = validator.rule_by_subroutine(rules, "ProcessPlayerFastState")
        shared = validator.rule_by_subroutine(rules, "RecountVotes")
        self.assertIsNotNone(fast)
        self.assertIsNotNone(shared)
        for callee in ("QuiescePlayer", "CleanupPlayer"):
            with self.subTest(callee=callee):
                changed_fast = fast.body.replace("\tactions\n\t{", "\tactions\n\t{\n\t\tCall Subroutine(RecountVotes);", 1)
                changed_shared = shared.body.replace("\tactions\n\t{", f"\tactions\n\t{{\n\t\tCall Subroutine({callee});", 1)
                mutated = source.replace(fast.body, changed_fast, 1).replace(shared.body, changed_shared, 1)
                # Recount is also called directly by the scheduler; either global
                # path must still reject the shared routine's player context.
                self.assertTrue(any(f"RecountVotes -> {callee}" in error
                                    for error in self.errors(mutated)))


class WorkshopSettingMetadataTests(unittest.TestCase):
    SETTING_TAILS = {
        "Workshop Setting Integer": "30, 10, 60, 0",
        "Workshop Setting Combo": '0, Array(Custom String("Option: one")), 1',
        "Workshop Setting Toggle": "False, 2",
    }

    def call(self, action: str, category: str, name: str) -> validator.Call:
        source = f"{action}({category}, {name}, {self.SETTING_TAILS[action]})"
        return next(validator.iter_calls(source, action))

    def test_current_categories_and_english_names_are_valid(self) -> None:
        for path in (validator.SOURCE, validator.BEHAVIORAL_SOURCE):
            source = path.read_text(encoding="utf-8")
            for action in self.SETTING_TAILS:
                with self.subTest(path=path.name, action=action):
                    calls = list(validator.iter_calls(source, action))
                    self.assertEqual(len(calls), 0 if action == "Workshop Setting Combo" else 1)
                    for call in calls:
                        self.assertEqual(validator.workshop_setting_text_errors(call), [])

    def test_empty_whitespace_and_forbidden_characters_are_rejected_in_both_keys(self) -> None:
        for action in self.SETTING_TAILS:
            for index, field in enumerate(("categoria", "nome")):
                for invalid in ("", "   ", r"\t", r"\n", "bad{", "bad}", "bad:"):
                    with self.subTest(action=action, field=field, invalid=invalid):
                        keys = ['Custom String("CHILL")', 'Custom String("Duration / Durasi / ระยะเวลา")']
                        keys[index] = f'Custom String("{invalid}")'
                        errors = validator.workshop_setting_text_errors(self.call(action, *keys))
                        self.assertEqual(len(errors), 1)
                        self.assertTrue(errors[0].startswith(f"{field} {action}"))

    def test_setting_keys_remain_complete_literal_expressions(self) -> None:
        invalid_expressions = (
            "Global.NamaHalaman",
            'Custom String("{0}", Global.NamaHalaman)',
            'Custom String("{0}", Custom String("CHILL"))',
            'Custom String("CHILL") + Global.NamaHalaman',
            'Custom String("CHILL" + Global.NamaHalaman)',
            'True ? Custom String("CHILL") : Custom String("")',
        )
        for action in self.SETTING_TAILS:
            for index in (0, 1):
                for expression in invalid_expressions:
                    with self.subTest(action=action, index=index, expression=expression):
                        keys = ['Custom String("CHILL")', 'Custom String("Duration / Durasi / ระยะเวลา")']
                        keys[index] = expression
                        self.assertTrue(validator.workshop_setting_text_errors(self.call(action, *keys)))

    def test_unicode_spaces_slashes_parentheses_and_combo_option_colons_are_allowed(self) -> None:
        for action in self.SETTING_TAILS:
            with self.subTest(action=action):
                call = self.call(action, 'Custom String(" COZYWATCH ")',
                                 'Custom String("Duration / Durasi / ระยะเวลา (min)")')
                self.assertEqual(validator.workshop_setting_text_errors(call), [])

    def test_missing_name_is_rejected(self) -> None:
        for action in self.SETTING_TAILS:
            with self.subTest(action=action):
                call = next(validator.iter_calls(f'{action}(Custom String("CHILL"))', action))
                self.assertEqual(validator.workshop_setting_text_errors(call), [f"nome {action} assente"])


class SemanticWorkshop081Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = validator.SOURCE.read_text(encoding="utf-8")

    def errors(self, source: str) -> list[str]:
        return validator.validate(source, include_metadata=False).errors

    def assert_rejected(self, source: str, fragment: str) -> None:
        errors = self.errors(source)
        self.assertTrue(
            any(fragment.lower() in error.lower() for error in errors),
            f"expected an error containing {fragment!r}; got:\n" + "\n".join(errors),
        )

    def replace_once(self, old: str, new: str) -> str:
        self.assertIn(old, self.source, f"fixture token not found: {old}")
        return self.source.replace(old, new, 1)

    def rule(self, predicate) -> validator.Rule:
        match = next((rule for rule in validator.extract_rules(self.source) if predicate(rule)), None)
        self.assertIsNotNone(match, "fixture role not found")
        return match  # type: ignore[return-value]

    def replace_in_rule(self, rule: validator.Rule, old: str, new: str) -> str:
        self.assertIn(old, rule.body, f"rule fixture token not found: {old}")
        changed = rule.body.replace(old, new, 1)
        return self.source[:rule.start] + changed + self.source[rule.end:]

    def replace_regex_in_rule(self, rule: validator.Rule, pattern: str, replacement: str) -> str:
        changed, count = re.subn(pattern, replacement, rule.body, count=1, flags=re.DOTALL)
        self.assertEqual(count, 1, f"rule fixture pattern not found: {pattern}")
        return self.source[:rule.start] + changed + self.source[rule.end:]

    def inject_action(self, rule: validator.Rule, action: str) -> str:
        closing = rule.body.rfind("\n\t}")
        self.assertGreater(closing, 0)
        changed = rule.body[:closing] + f"\n\t\t{action}" + rule.body[closing:]
        return self.source[:rule.start] + changed + self.source[rule.end:]

    def inject_condition(self, rule: validator.Rule, condition: str) -> str:
        match = re.search(r"\bconditions\s*\{", rule.body)
        self.assertIsNotNone(match, "rule fixture has no conditions block")
        opening = rule.body.find("{", match.start())  # type: ignore[union-attr]
        closing = validator.matching_brace(rule.body, opening)
        changed = rule.body[:closing] + f"\n\t\t{condition}" + rule.body[closing:]
        return self.source[:rule.start] + changed + self.source[rule.end:]

    def replace_call_argument(self, call: validator.Call, index: int, value: str) -> str:
        args = list(call.args)
        self.assertLess(index, len(args))
        args[index] = value
        replacement = f"{call.name}(" + ", ".join(args) + ")"
        return self.source[:call.start] + replacement + self.source[call.end:]

    def left_roster_call(self) -> validator.Call:
        renderer = self.rule(lambda rule: "Event Player.PlayerListHud = Last Text ID;" in rule.body)
        call = next(call for call in validator.iter_calls(renderer.body, "Create HUD Text")
                    if len(call.args) >= 6 and call.args[4].strip() == "Left")
        return validator.Call(call.name, call.raw, call.args, renderer.start + call.start, renderer.start + call.end)

    def add_player_declaration_and_setup_init(self, name: str, initial_value: str) -> str:
        _, players, _, declaration_span = validator.declaration_entries(self.source)
        self.assertNotIn(name, {entry.name for entry in players})
        subroutines_start = self.source.index("\nsubroutines", declaration_span[0])
        variables_close = self.source.rfind("}", declaration_span[0], subroutines_start)
        declaration = f"\t\t{len(players)}: {name}\n"
        mutated = self.source[:variables_close] + declaration + self.source[variables_close:]
        setup = next(
            rule for rule in validator.extract_rules(mutated)
            if validator.subroutine_target(rule) == "PreparePlayer"
        )
        closing = setup.body.rfind("\n\t}")
        changed_setup = setup.body[:closing] + f"\n\t\tEvent Player.{name} = {initial_value};" + setup.body[closing:]
        return mutated[:setup.start] + changed_setup + mutated[setup.end:]

    def world_name_iwts(self) -> dict[str, tuple[validator.Rule, validator.Call, str]]:
        specs = (
            (
                "inspection",
                "Event Player.InspectionTarget != Event Player.InspectionTargetCandidate",
                "Event Player.InspectionTarget",
            ),
            (
                "Vision",
                "Event Player.LuckVisionText = Last Text ID;",
                "Event Player",
            ),
            (
                "Teleport",
                "Event Player.TravelTextTarget != Event Player.TravelTargetCandidate",
                "Event Player.TravelTargetCandidate",
            ),
        )
        contracts: dict[str, tuple[validator.Rule, validator.Call, str]] = {}
        for label, marker, subject in specs:
            rule = self.rule(
                lambda candidate, marker=marker: marker in candidate.body
                and "Create In-World Text(" in candidate.body
            )
            calls = list(validator.iter_calls(rule.body, "Create In-World Text"))
            self.assertEqual(len(calls), 1, f"IWT {label}: numero Create In-World Text")
            call = calls[0]
            self.assertGreaterEqual(len(call.args), 6, f"IWT {label}: chiamata malformata")
            contracts[label] = (
                rule,
                validator.Call(
                    call.name,
                    call.raw,
                    call.args,
                    rule.start + call.start,
                    rule.start + call.end,
                ),
                subject,
            )
        return contracts

    def start_camera_calls(self) -> list[tuple[validator.Rule, validator.Call]]:
        calls: list[tuple[validator.Rule, validator.Call]] = []
        for rule in validator.extract_rules(self.source):
            for call in validator.iter_calls(rule.body, "Start Camera"):
                calls.append(
                    (
                        rule,
                        validator.Call(
                            call.name,
                            call.raw,
                            call.args,
                            rule.start + call.start,
                            rule.start + call.end,
                        ),
                    )
                )
        return calls

    def test_official_source_passes_all_semantic_checks(self) -> None:
        self.assertEqual(self.errors(self.source), [])

    def test_special_player_declaration_setup_and_exact_unicode_are_guarded(self) -> None:
        mutations = (
            (
                self.source.replace("\t\t98: CustomSoundtrack", "\t\t97: CustomSoundtrack", 1),
                "indice CustomSoundtrack",
            ),
            (
                self.source.replace(
                    "Event Player.CustomSoundtrack = Null;",
                    "Event Player.CustomSoundtrack = False;",
                    1,
                ),
                "inizializzazione CustomSoundtrack",
            ),
            (
                self.source.replace('Custom String("งูแรร์")', 'Custom String("งูเท้")', 1),
                "matcher งูแรร์ deve usare DisplayName stabile",
            ),
        )
        for mutated, fragment in mutations:
            with self.subTest(fragment=fragment):
                self.assert_rejected(mutated, fragment)

    def test_special_profile_must_use_cached_display_name(self) -> None:
        mutated = self.replace_once(
            'If(Event Player.DisplayName == Custom String("งูแรร์"));',
            'If(Custom String("{0}", Event Player) == Custom String("งูแรร์"));',
        )
        self.assert_rejected(mutated, "matcher งูแรร์ deve usare DisplayName stabile")

    def test_special_player_indices_and_cursors_are_guarded(self) -> None:
        classifier = self.rule(
            lambda rule: "Append To Array(Global.HumanPlayers, Event Player)" in rule.body
        )
        mutations = (
            ("Event Player.ColorIndex = 2;", "Event Player.ColorIndex = 1;"),
            ("Event Player.ColorCursor = 2;", "Event Player.ColorCursor = 1;"),
            ("Event Player.IconIndex = 23;", "Event Player.IconIndex = 22;"),
            ("Event Player.IconCursor = 23;", "Event Player.IconCursor = 22;"),
        )
        for old, new in mutations:
            with self.subTest(field=old):
                self.assert_rejected(
                    self.replace_in_rule(classifier, old, new),
                    "blocco default isolato",
                )

    def test_special_player_matcher_must_follow_bot_exclusion(self) -> None:
        classifier = self.rule(
            lambda rule: "Append To Array(Global.HumanPlayers, Event Player)" in rule.body
        )
        marker = classifier.body.index('Custom String("งูแรร์")')
        spans = [
            span for span in validator.conditional_branch_spans(classifier.body)
            if span[0] <= marker < span[1]
        ]
        self.assertTrue(spans)
        start, end = min(spans, key=lambda span: span[1] - span[0])
        profile_branch = classifier.body[start:end]
        without_profile = classifier.body[:start] + classifier.body[end:]
        bot_start = without_profile.index("If(Event Player.IsAutomaticBot == True);")
        moved = (
            without_profile[:bot_start]
            + profile_branch
            + "\n\t\t"
            + without_profile[bot_start:]
        )
        mutated = self.source[:classifier.start] + moved + self.source[classifier.end:]
        self.assert_rejected(mutated, "matcher deve seguire esclusione/Abort degli iBot")

    def test_special_player_lifecycle_repair_reasserts_lock_and_reset_defaults(self) -> None:
        fast = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerFastState")
        mutations = (
            (
                'Global.ActivePlayer.CustomSoundtrack = Custom String("Draconian");',
                "Global.ActivePlayer.CustomSoundtrack = Null;",
            ),
            (
                "If(Global.ActivePlayer.WasPrepared == False);",
                "If(True);",
            ),
            (
                "Global.ActivePlayer.IconIndex = 23;",
                "Global.ActivePlayer.IconIndex = 22;",
            ),
        )
        for old, new in mutations:
            with self.subTest(token=old):
                self.assert_rejected(
                    self.replace_in_rule(fast, old, new),
                    "repair default/lock isolato",
                )

    def test_special_player_catalog_mappings_are_guarded(self) -> None:
        mutations = (
            (
                self.source.replace(
                    'Custom String("Lowercase")',
                    'Custom String("Draconian")',
                    1,
                ),
                "Draconian inserito nei 200 generi ordinari",
            ),
            (
                self.source.replace(
                    "Custom Color(190, 210, 230, 255)",
                    "Custom Color(191, 210, 230, 255)",
                    1,
                ),
                "valore Silver Mist indice 1",
            ),
            (
                self.source.replace(
                    "Vector(190, 210, 230)",
                    "Vector(191, 210, 230)",
                    1,
                ),
                "vettore Silver Mist indice 1",
            ),
            (
                self.source.replace("Icon String(Poison 2)", "Icon String(Poison)", 1),
                "icona indice 23",
            ),
        )
        for mutated, fragment in mutations:
            with self.subTest(fragment=fragment):
                self.assert_rejected(mutated, fragment)

    def test_special_player_roster_main_and_locked_renderers_are_guarded(self) -> None:
        roster = self.rule(
            lambda rule: "Event Player.PlayerHudCreated = True;" in rule.body
        )
        roster_mutation = self.replace_in_rule(
            roster,
            "Event Player.CustomSoundtrack != Null ? Event Player.CustomSoundtrack : Event Player.GenreIndex",
            "Event Player.CustomSoundtrack == Null ? Event Player.CustomSoundtrack : Event Player.GenreIndex",
        )
        self.assert_rejected(roster_mutation, "profilo speciale roster: condizione profilo speciale")

        main = self.rule(lambda rule: validator.subroutine_target(rule) == "DrawMainMenu")
        main_mutation = self.replace_in_rule(
            main,
            'Custom String("2 - MUSIK\\nKINI: {0}", Event Player.CustomSoundtrack != Null',
            'Custom String("2 - MUSIK\\nKINI: {0}", Event Player.CustomSoundtrack == Null',
        )
        self.assert_rejected(main_mutation, "profilo speciale menu principale: condizione profilo speciale")

        music = self.rule(lambda rule: validator.subroutine_target(rule) == "DrawSoundtrackMenu")
        locked_mutation = self.replace_in_rule(
            music,
            'Custom String("เพลงล็อกอยู่\\nใช้: {0}", Event Player.CustomSoundtrack)',
            'Custom String("เพลงถูกล็อก\\nตอนนี้: {0}", Event Player.CustomSoundtrack)',
        )
        self.assert_rejected(locked_mutation, "testo locked")

    def test_special_player_music_navigation_guards_are_required(self) -> None:
        navigation = self.rule(
            lambda rule: "Event Player.MenuCommand == 3" in rule.body
            and "Event Player.MenuCommand == 4" in rule.body
            and "Event Player.GenreCursor = (Event Player.GenreCursor" in rule.body
        )
        plus_minus_one = self.replace_in_rule(
            navigation,
            "Else If(And(Event Player.MenuPage == 3, Event Player.CustomSoundtrack == Null));",
            "Else If(Event Player.MenuPage == 3);",
        )
        self.assert_rejected(plus_minus_one, "guardia Soundtrack ±1")

        jump = self.rule(
            lambda rule: "Event Player.MenuCommand == 5" in rule.body
            and "Event Player.MenuCommand == 6" in rule.body
            and "Event Player.GenreCursor = (Event Player.GenreCursor" in rule.body
        )
        plus_minus_ten = self.replace_in_rule(
            jump,
            "\n\t\tEvent Player.CustomSoundtrack == Null;",
            "",
        )
        self.assert_rejected(plus_minus_ten, "guardia Soundtrack ±10")

        apply_music = self.rule(
            lambda rule: validator.subroutine_target(rule) == "ApplySoundtrackPage"
        )
        apply_mutation = self.replace_in_rule(
            apply_music,
            "Abort If(Event Player.CustomSoundtrack != Null);",
            "Abort If(False);",
        )
        self.assert_rejected(apply_mutation, "deve iniziare con la guardia locked")

    def test_special_player_writer_ownership_is_guarded(self) -> None:
        main = self.rule(lambda rule: validator.subroutine_target(rule) == "DrawMainMenu")
        mutations = (
            (
                self.inject_action(main, "Global.ActivePlayer.CustomSoundtrack = Null;"),
                "writer property CustomSoundtrack",
            ),
            (
                self.inject_action(
                    main,
                    "Chase Player Variable At Rate(Event Player, CustomSoundtrack, 1, 1);",
                ),
                "writer azione inattesi CustomSoundtrack",
            ),
        )
        for mutated, fragment in mutations:
            with self.subTest(fragment=fragment):
                self.assert_rejected(mutated, fragment)

    def test_source_is_not_pinned_by_whole_file_hash(self) -> None:
        mutated = self.source.replace("\n\nrule(", "\n\n\nrule(", 1)
        self.assertEqual(self.errors(mutated), [])

    def test_delimiter_scanner_ignores_parentheses_inside_strings(self) -> None:
        expression = 'Small Message(Event Player, Custom String("literal [ ( ) ]"));'
        self.assertIsNone(validator.delimiter_error(expression))

    def test_delimiter_scanner_detects_crossed_call_and_index_delimiters(self) -> None:
        self.assertIsNotNone(validator.delimiter_error("Value In Array(Array(1, 2), 0])"))

    def test_declaration_indices_must_be_compact(self) -> None:
        globals_, _, _, _ = validator.declaration_entries(self.source)
        token = f"\t\t{globals_[1].index}: {globals_[1].name}"
        mutated = self.replace_once(token, f"\t\t{globals_[1].index + 1}: {globals_[1].name}")
        self.assert_rejected(mutated, "indici global compatti")

    def test_subroutine_name_over_32_utf8_bytes_is_rejected(self) -> None:
        valid_name = "ApplyCrouchTravel"
        overlong_name = "TerapkanHalamanTeleportasiJongkok"
        self.assertLessEqual(len(valid_name.encode("utf-8")), validator.MAX_DECLARATION_NAME_BYTES)
        self.assertGreater(len(overlong_name.encode("utf-8")), validator.MAX_DECLARATION_NAME_BYTES)
        mutated = self.source.replace(valid_name, overlong_name)
        _, _, declarations, _ = validator.declaration_entries(self.source)
        index = next(entry.index for entry in declarations if entry.name == valid_name)
        self.assert_rejected(
            mutated,
            f"nome subroutine oltre 32 byte UTF-8: indice {index}, {overlong_name}",
        )

    def test_player_variable_name_over_32_utf8_bytes_is_rejected(self) -> None:
        valid_name = "TravelTargets"
        overlong_name = "CurrentTravelTargetSelectionState"
        self.assertEqual(len(overlong_name.encode("utf-8")), validator.MAX_DECLARATION_NAME_BYTES + 1)
        mutated = self.source.replace(valid_name, overlong_name)
        self.assert_rejected(
            mutated,
            "nome player oltre 32 byte UTF-8: indice 31, CurrentTravelTargetSelectionState",
        )

    def test_declaration_name_at_32_utf8_bytes_is_accepted(self) -> None:
        valid_name = "SelectedRevengeTarget"
        boundary_name = "SelectedRevengeTargetCurrentName"
        self.assertEqual(len(boundary_name.encode("utf-8")), validator.MAX_DECLARATION_NAME_BYTES)
        mutated = self.source.replace(valid_name, boundary_name)
        self.assertEqual(self.errors(mutated), [])

    def test_write_only_variable_is_rejected(self) -> None:
        mutated = self.add_player_declaration_and_setup_init("JejakTakTerpakai", "0")
        self.assert_rejected(mutated, "soltanto inizializzata")

    def test_undeclared_global_property_is_rejected(self) -> None:
        mutated = self.replace_once("Global.RGB =", "Global.WarnaTakDideklarasikan =")
        self.assert_rejected(mutated, "Global non dichiarato")

    def test_undeclared_player_property_is_rejected(self) -> None:
        mutated = self.replace_once("Event Player.MenuOpen", "Event Player.StatusTakDideklarasikan")
        self.assert_rejected(mutated, "player non dichiarato")

    def test_undeclared_player_variable_action_argument_is_rejected(self) -> None:
        mutated = self.replace_once(
            "Set Player Variable(Global.ActivePlayer, DummyBotFollowTarget,",
            "Set Player Variable(Global.ActivePlayer, TargetTakDideklarasikan,",
        )
        self.assert_rejected(mutated, "player non dichiarato")

    def test_every_player_variable_is_initialized_in_setup(self) -> None:
        setup = self.rule(lambda rule: validator.subroutine_target(rule) == "PreparePlayer")
        mutated = self.replace_in_rule(setup, "\n\t\tEvent Player.MenuOpen = False;", "")
        self.assert_rejected(mutated, "non inizializzata in PreparePlayer")

    def test_removed_teks_diri_leaves_compact_initialized_declarations(self) -> None:
        _, players, _, _ = validator.declaration_entries(self.source)
        self.assertNotIn("TeksDiri", {entry.name for entry in players})
        # Removing the three binary menu cursors preserves all other native IDs.
        self.assertEqual([entry.index for entry in players],
                         [index for index in range(128) if index not in {60, 92}])
        self.assertFalse(any("non inizializzata in PreparePlayer" in error for error in self.errors(self.source)))

    def test_teks_diri_would_be_rejected_if_only_declared_and_initialized(self) -> None:
        mutated = self.add_player_declaration_and_setup_init("TeksDiri", "Null")
        self.assert_rejected(mutated, "soltanto inizializzata/pulita e mai letta: TeksDiri")

    def test_teks_diri_init_cleanup_and_counting_still_is_dead_legacy_state(self) -> None:
        mutated = self.add_player_declaration_and_setup_init("TeksDiri", "Null")
        cleanup = next(
            rule for rule in validator.extract_rules(mutated)
            if validator.subroutine_target(rule) == "CleanupPlayer"
        )
        closing = cleanup.body.rfind("\n\t}")
        extra = (
            "\n\t\tIf(Event Player.TeksDiri != Null);"
            "\n\t\t\tDestroy In-World Text(Event Player.TeksDiri);"
            "\n\t\tEnd;"
            "\n\t\tAbort If(Count Of(Array(Event Player.TeksDiri)) < 0);"
            "\n\t\tEvent Player.TeksDiri = Null;"
        )
        changed = cleanup.body[:closing] + extra + cleanup.body[closing:]
        mutated = mutated[:cleanup.start] + changed + mutated[cleanup.end:]
        self.assert_rejected(mutated, "identificatore legacy o non indonesiano presente: TeksDiri")

    def test_self_assignment_no_op_is_rejected(self) -> None:
        setup = self.rule(lambda rule: validator.subroutine_target(rule) == "PreparePlayer")
        mutated = self.inject_action(setup, "Event Player.MenuOpen = Event Player.MenuOpen;")
        self.assert_rejected(mutated, "self-assignment no-op")

    def test_disabled_rule_is_rejected(self) -> None:
        rule = validator.extract_rules(self.source)[0]
        mutated = self.source[:rule.start] + "disabled\n" + self.source[rule.start:]
        self.assert_rejected(mutated, "disabled rule")

    def test_unused_subroutine_is_rejected(self) -> None:
        _, _, subs, span = validator.declaration_entries(self.source)
        closing = self.source.rfind("}", span[0], span[1])
        mutated = self.source[:closing] + f"\n\t{len(subs)}: SubrutinTidakDipakai\n" + self.source[closing:]
        self.assert_rejected(mutated, "mai chiamata")

    def test_legacy_or_non_indonesian_identifier_is_rejected(self) -> None:
        mutated = self.source.replace("VoterIndex", "IndeksVote")
        self.assert_rejected(mutated, "IndeksVote")

    def test_english_icon_labels_are_required(self) -> None:
        mutated = self.source.replace("IconNames", "IconLabels")
        self.assert_rejected(mutated, "IconNames")

    def test_icon_localization_requires_exactly_37_entries(self) -> None:
        items = validator.array_assignment_items(self.source, "IconNames")
        self.assertIsNotNone(items)
        self.assertEqual(len(items), 37)
        assignment = self.source.index("Global.IconNames = Array(")
        opening = self.source.index("(", assignment)
        closing = validator.matching_parenthesis(self.source, opening)
        body = self.source[opening + 1:closing]
        last = body.rfind((items or [])[-1])
        comma = body.rfind(",", 0, last)
        self.assertGreaterEqual(comma, 0)
        shorter_body = body[:comma] + body[last + len((items or [])[-1]):]
        mutated = self.source[:opening + 1] + shorter_body + self.source[closing:]
        self.assert_rejected(mutated, "numero voci IconNames")

    def test_removed_language_selection_cannot_return(self) -> None:
        mutated = self.add_player_declaration_and_setup_init("IndeksBahasa", "0")
        self.assert_rejected(mutated, "English UI: stato lingua/località rimosso")

    def test_removed_server_location_setting_cannot_return(self) -> None:
        init = self.rule(lambda rule: rule.name.startswith("00 -"))
        action = 'Global.IndeksLokasiServer = Workshop Setting Combo(Custom String("COZYWATCH"), Custom String("Location"), 0, Array(Custom String("Europe")), 1);'
        mutated = self.inject_action(init, action)
        self.assert_rejected(mutated, "English UI: stato lingua/località rimosso")

    def test_small_messages_cannot_restore_the_removed_thai_ui(self) -> None:
        call = next(iter(validator.iter_calls(self.source, "Small Message")))
        mutated = self.replace_call_argument(call, 1, 'Custom String("เปิด")')
        self.assert_rejected(mutated, "English UI: testo Thai visibile")

    def test_placeholder_out_of_range_is_rejected(self) -> None:
        mutated = self.replace_once('Custom String("{0}"', 'Custom String("{1}"')
        self.assert_rejected(mutated, "placeholder fuori intervallo")

    def test_removed_language_cursor_cannot_return(self) -> None:
        mutated = self.add_player_declaration_and_setup_init("KursorBahasa", "0")
        self.assert_rejected(mutated, "English UI: stato lingua/località rimosso")

    def test_hud_header_must_be_null(self) -> None:
        call = next(iter(validator.iter_calls(self.source, "Create HUD Text")))
        mutated = self.replace_call_argument(call, 1, 'Custom String("TITLE")')
        self.assert_rejected(mutated, "Header Create HUD Text")

    def test_big_message_is_rejected(self) -> None:
        mutated = self.source + "\nBig Message(All Players(All Teams), Custom String(\"TITLE\"));\n"
        self.assert_rejected(mutated, "Big Message")

    def test_single_menu_handle_is_required(self) -> None:
        mutated = self.source.replace("MenuHud", "HudMenuArcade")
        self.assert_rejected(mutated, "HudMenuArcade")

    def test_hidden_or_preloaded_menu_hud_is_rejected(self) -> None:
        renderer = self.rule(lambda rule: validator.subroutine_target(rule) == "DrawMainMenu")
        call = next(iter(validator.iter_calls(renderer.body, "Create HUD Text")))
        absolute_call = validator.Call(call.name, call.raw, call.args, renderer.start + call.start, renderer.start + call.end)
        mutated = self.replace_call_argument(absolute_call, 0, "Empty Array")
        self.assert_rejected(mutated, "nascosto/precaricato")

    def test_global_hud_must_not_repeat_the_menu_modifier_explanation(self) -> None:
        mutated = self.replace_once(
            '"Hold {0}: hero + HP"',
            '"Hold {0}: hero + HP | in menu: modifier for every command"',
        )
        self.assert_rejected(mutated, "clausola modifier Crouch duplicata")

    def test_every_menu_keeps_the_trilingual_crouch_instruction(self) -> None:
        renderer = self.rule(lambda rule: validator.subroutine_target(rule) == "DrawMainMenu")
        mutated = self.replace_in_rule(renderer, "Hold CROUCH", "Hold DUCK")
        self.assert_rejected(mutated, "istruzione Crouch menu assente")

    def test_thai_menu_close_help_keeps_the_half_second_hold(self) -> None:
        renderer = self.rule(lambda rule: validator.subroutine_target(rule) == "DrawMainMenu")
        mutated = self.replace_in_rule(
            renderer,
            'กด {1} ค้าง 0.5 วิ: ปิด',
            "กด {1} ค้างเพื่อปิด",
        )
        self.assert_rejected(mutated, "help Thai chiusura menu")

    def test_menu_instruction_cannot_start_with_an_artificial_blank_line(self) -> None:
        renderer = self.rule(lambda rule: validator.subroutine_target(rule) == "DrawMainMenu")
        mutated = self.replace_in_rule(renderer, "Hold CROUCH", "\\nHold CROUCH")
        self.assert_rejected(mutated, "riga vuota artificiale")

    def test_teleport_menu_requires_specific_trilingual_copy(self) -> None:
        renderer = self.rule(lambda rule: validator.subroutine_target(rule) == "DrawTravelMenu")
        mutations = (
            ("CURRENT HERO FORM | COOLDOWN: 3s", "SELF KILL"),
            ("1/5 | TELEPORT: RUANG MUNCUL\nTIMMU", "TUJUAN: SPAWN"),
            ('2/5 | วาร์ป: ภารกิจ', "ปลายทาง: เป้าหมาย"),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                mutated = self.replace_in_rule(renderer, old, new)
                self.assert_rejected(mutated, "testo pagina specifico EN/ID/TH assente")

    def test_teleport_menu_keeps_dynamic_binding_help(self) -> None:
        renderer = self.rule(lambda rule: validator.subroutine_target(rule) == "DrawTravelMenu")
        mutated = self.replace_in_rule(
            renderer,
            "{0}: USE | RELEASE {1}: CLOSE",
            "INTERACT: USE | RELEASE CROUCH: CLOSE",
        )
        self.assert_rejected(mutated, "istruzione ordinata EN/ID/TH assente")

    def test_travel_navigation_and_renderer_keep_five_pages(self) -> None:
        navigation = self.rule(lambda rule: rule.name.startswith("19c - Crouch Travel: Navigate five pages with Primary and Secondary Fire"))
        renderer = self.rule(lambda rule: validator.subroutine_target(rule) == "DrawTravelMenu")
        for rule, old, new, error in (
            (navigation, "Event Player.TravelCommand == 1 ? 1 : 4", "Event Player.TravelCommand == 1 ? 1 : 5", "navigazione deve includere cinque pagine avanti e indietro"),
            (navigation, ") % 5;", ") % 6;", "navigazione deve includere cinque pagine avanti e indietro"),
            (renderer, "Event Player.TravelCursor %= 5;", "Event Player.TravelCursor %= 6;", "normalizzare il cursore a cinque pagine"),
        ):
            with self.subTest(mutation=old):
                self.assert_rejected(self.replace_in_rule(rule, old, new), "Travel: " + error)

    def test_travel_forward_declaration_and_runtime_stay_removed(self) -> None:
        declaration = re.sub(r"(\bsubroutines\s*\{)", r"\1\n\t67: ProsesTeleportasiMaju", self.source, count=1)
        self.assert_rejected(declaration, "Travel: subroutine Forward deve restare rimossa")
        runtime = self.source + '\nrule("89j - removed Forward") { event { Subroutine; ProsesTeleportasiMaju; } actions { Abort; } }'
        self.assert_rejected(runtime, "Travel: subroutine Forward deve restare rimossa")

    def test_travel_forward_has_no_scheduler_caller(self) -> None:
        scheduler = self.rule(lambda rule: validator.action_loop_count(rule.body) == 1)
        for action in ("Call Subroutine(ProsesTeleportasiMaju);", "Start Rule(ProsesTeleportasiMaju, Do Nothing);"):
            with self.subTest(action=action):
                self.assert_rejected(self.inject_action(scheduler, action), "Travel: nessun caller della subroutine Forward rimossa")

    def test_teleport_menu_uses_smooth_readable_tint(self) -> None:
        renderer = self.rule(lambda rule: validator.subroutine_target(rule) == "DrawTravelMenu")
        for token in (
            "Custom Color(190 + X Component Of(Event Player.MenuColor) * 0.250",
            "Custom Color(X Component Of(Event Player.MenuColor)",
            "Visible To String and Color",
        ):
            self.assertIn(token, renderer.body)
        transition = self.rule(lambda rule: validator.subroutine_target(rule) == "TransitionMenuColor")
        for token in (
            "Event Player.CrouchTravelActive == True",
            "Vector(80, 255, 160)",
            "Vector(65, 225, 255)",
            "Vector(95, 150, 255)",
            "Vector(195, 100, 255)",
            "Vector(255, 85, 135)",
            "Chase Player Variable Over Time(Event Player, MenuColor, Event Player.TravelCursor",
            "0.180, Destination and Duration",
        ):
            self.assertIn(token, transition.body)
        mutated = self.replace_in_rule(renderer, "Visible To String and Color", "Visible To and String")
        self.assert_rejected(mutated, "colore deve rivalutarsi")

    def test_revenge_no_target_branch_keeps_trilingual_crouch_help(self) -> None:
        renderer = self.rule(lambda rule: validator.subroutine_target(rule) == "DrawRevengeMenu")
        call = next(iter(validator.iter_calls(renderer.body, "Create HUD Text")))
        branches = validator.parse_top_level_ternary(call.args[2])
        self.assertIsNotNone(branches)
        _, no_targets, _ = branches  # type: ignore[misc]
        changed_branch = no_targets.replace("Hold CROUCH", "Hold DUCK", 1)
        self.assertNotEqual(changed_branch, no_targets)
        changed_argument = call.args[2].replace(no_targets, changed_branch, 1)
        absolute = validator.Call(call.name, call.raw, call.args, renderer.start + call.start, renderer.start + call.end)
        mutated = self.replace_call_argument(absolute, 2, changed_argument)
        self.assert_rejected(mutated, "Revenge no-target senza istruzione Crouch")

    def test_chill_grid_requires_a_dedicated_top_spacer(self) -> None:
        call = next(
            call for call in validator.iter_calls(self.source, "Create HUD Text")
            if len(call.args) >= 4
            and call.args[4].strip() == "Top"
            and call.args[5].strip() == "2"
        )
        mutated = self.replace_call_argument(call, 3, "Null")
        self.assert_rejected(mutated, "HUD fisso Top sort 2: contenuto text errato")

    def test_roster_hud_slots_are_exactly_zero_through_eleven(self) -> None:
        mutated = self.replace_once(
            "Global.AvailableHudSlots = Array(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11);",
            "Global.AvailableHudSlots = Array(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12);",
        )
        self.assert_rejected(mutated, "slot HUD roster devono essere esattamente 0..11")

    def test_retired_minutes_and_duplicate_roster_handles_cannot_return(self) -> None:
        for name in ("WaktuMasuk", "MenitLobi", "HudKanan"):
            with self.subTest(name=name):
                mutated = self.add_player_declaration_and_setup_init(name, "0")
                self.assert_rejected(mutated, f"roster unico: stato rimosso ancora presente: {name}")

    def test_host_row_follows_the_current_host_without_caching_or_a_loop(self) -> None:
        host = next(call for call in validator.iter_calls(self.source, "Create HUD Text")
                    if call.args[4].strip() == "Right" and call.args[5].strip() == "0")
        changed = host.args[3].replace("Hero Of(Host Player)", "Hero Of(Evaluate Once(Host Player))")
        self.assert_rejected(self.replace_call_argument(host, 3, changed),
                             "HUD Host: nome e icona devono seguire l'host corrente")
        self.assert_rejected(self.replace_call_argument(host, 9, "Visible To and String"),
                             "HUD Host: rivalutazione testo e colore")
        self.assert_rejected(self.replace_call_argument(host, 8, "Custom Color(255, 255, 255, 255)"),
                             "HUD Host: colore RGB globale del titolo")

    def test_host_row_handles_host_absence_without_the_client_zero(self) -> None:
        host = next(call for call in validator.iter_calls(self.source, "Create HUD Text")
                    if call.args[4].strip() == "Right" and call.args[5].strip() == "0")
        changed = host.args[3].rsplit(': Custom String("")', 1)[0] + ": Null"
        self.assert_rejected(self.replace_call_argument(host, 3, changed),
                             "HUD Host: fallback senza host deve essere stringa vuota")

    def test_chill_grid_rejects_a_seventh_fixed_hud(self) -> None:
        init = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Global"
            and "COZYWATCH" in rule.body
            and "Global.IsReady = True;" in rule.body
        )
        extra = (
            'Create HUD Text(Global.HumanPlayers, Null, Null, Custom String("  "), Top, 4, '
            'Color(White), Color(White), Color(White), Visible To and String, Visible Never);'
        )
        mutated = self.inject_action(init, extra)
        self.assert_rejected(mutated, "numero HUD fissi nella regola iniziale")

    def test_chill_grid_rejects_an_eighth_global_hud_outside_initialization(self) -> None:
        scheduler = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Global"
            and "Global.SchedulerStep" in rule.body
        )
        extra = (
            'Create HUD Text(Global.HumanPlayers, Null, Null, Custom String("  "), Top, 99, '
            'Color(White), Color(White), Color(White), Visible To and String, Visible Never);'
        )
        mutated = self.inject_action(scheduler, extra)
        self.assert_rejected(mutated, "numero HUD globali: sei fissi e un roster")

    def test_diagnostic_fixed_hud_baseline_cannot_be_satisfied_by_a_comment(self) -> None:
        token = "6 + Count Of(Filtered Array(Global.PlayerListHudIds"
        mutated = self.replace_once(token, "7 + Count Of(Filtered Array(Global.PlayerListHudIds")
        comment_anchor = '"This order deliberately runs from calm to chaotic. Keep the musical progression intact."'
        self.assertIn(comment_anchor, mutated)
        mutated = mutated.replace(comment_anchor, f'"{token}"\n\t\t{comment_anchor}', 1)
        self.assert_rejected(mutated, "diagnostica HUD non include gli sei handle fissi")
        call = self.left_roster_call()
        for handle in ("PlayerListHudIds", "MenuHudIds", "TemporaryEffectHudIds", "InspectionTextIds",
                       "TemporaryTravelTextIds", "TemporaryVisionTextIds"):
            with self.subTest(handle=handle):
                count = f"Count Of(Filtered Array(Global.{handle}, Current Array Element != 0))"
                changed = call.args[3].replace(count, "0", 1)
                self.assertNotEqual(changed, call.args[3])
                mutated = self.replace_call_argument(call, 3, changed)
                self.assert_rejected(mutated, "conteggio HUD diagnostica" if handle in
                                     ("PlayerListHudIds", "MenuHudIds", "TemporaryEffectHudIds")
                                     else "conteggio IWT diagnostica")

    def test_left_roster_rows_start_immediately_below_their_label(self) -> None:
        renderer = self.rule(lambda rule: "Event Player.PlayerListHud = Last Text ID;" in rule.body)
        mutated = self.replace_in_rule(renderer, "1 + Event Player.HudSlot", "2 + Event Player.HudSlot")
        self.assert_rejected(mutated, "renderer HUD roster Left: ordinamento")

    def test_vibes_roster_cannot_move_back_to_the_right(self) -> None:
        mutated = self.replace_call_argument(self.left_roster_call(), 4, "Right")
        self.assert_rejected(mutated, "renderer HUD roster Left")

    def test_removed_pre_roster_spacer_cannot_return(self) -> None:
        init = self.rule(lambda rule: rule.name.startswith("00 -"))
        extra = 'Create HUD Text(Global.HumanPlayers, Null, Custom String("old help"), Null, Left, -1, Color(White), Color(White), Color(White), Visible To and String, Visible Never);'
        mutated = self.inject_action(init, extra)
        self.assert_rejected(mutated, "numero HUD fissi nella regola iniziale")

    def test_removed_top_corner_help_cannot_return(self) -> None:
        init = self.rule(lambda rule: rule.name.startswith("00 -"))
        extra = 'Create HUD Text(Global.HumanPlayers, Null, Custom String("old help"), Null, Left, -2, Color(White), Color(White), Color(White), Visible To and String, Visible Never);'
        mutated = self.inject_action(init, extra)
        self.assert_rejected(mutated, "numero HUD fissi nella regola iniziale")

    def test_left_roster_text_cannot_reintroduce_the_client_zero(self) -> None:
        call = self.left_roster_call()
        branches = validator.parse_top_level_ternary(call.args[3])
        self.assertIsNotNone(branches)
        condition, visible, fallback = branches  # type: ignore[misc]
        for replacement in ("Null", "0"):
            with self.subTest(visible=replacement):
                changed = f"{condition} ? {replacement} : {fallback}"
                self.assert_rejected(self.replace_call_argument(call, 3, changed),
                                     "ramo visibile diagnostica deve essere stringa")
        changed = visible.replace("Server Load Average", "Null", 1)
        self.assertNotEqual(changed, visible)
        mutated = self.replace_call_argument(call, 3, f"{condition} ? {changed} : {fallback}")
        self.assert_rejected(mutated, "ramo visibile diagnostica non deve usare Null")

    def test_left_diagnostics_are_separate_and_always_white(self) -> None:
        call = self.left_roster_call()
        mutations = (
            (2, f'Custom String("{{0}}{{1}}", {call.args[2]}, {call.args[3]})', "Subheader deve contenere soltanto la riga player"),
            (3, "Null", "ternario diagnostica nel Text assente"),
            (7, "Color(White)", "colore Subheader deve usare NameColor"),
            (8, "Global.RGB", "diagnostica Text deve essere sempre bianca"),
            (8, "Event Player.NameColor", "diagnostica Text deve essere sempre bianca"),
            (8, "Event Player.MenuColor", "diagnostica Text deve essere sempre bianca"),
        )
        for index, replacement, error in mutations:
            with self.subTest(field=index, replacement=replacement):
                self.assert_rejected(self.replace_call_argument(call, index, replacement), error)

    def test_left_diagnostic_visibility_and_empty_string_fallback_are_preserved(self) -> None:
        call = self.left_roster_call()
        branches = validator.parse_top_level_ternary(call.args[3])
        self.assertIsNotNone(branches)
        condition, visible, fallback = branches  # type: ignore[misc]
        self.assertEqual(fallback, 'Custom String("")')
        for replacement in ("Null", "0"):
            with self.subTest(fallback=replacement):
                self.assert_rejected(self.replace_call_argument(call, 3, f"{condition} ? {visible} : {replacement}"),
                                     "fallback diagnostica deve essere stringa vuota")
        for token in ("Global.PerformanceDiagnostics == True", "Local Player == Host Player",
                      "Event Player.HudSlot == Global.LastHudSlot", "And("):
            with self.subTest(guard=token):
                changed = condition.replace(token, "Or(" if token == "And(" else "True", 1)
                self.assertNotEqual(changed, condition)
                self.assert_rejected(self.replace_call_argument(call, 3, f"{changed} ? {visible} : {fallback}"),
                                     "guardia diagnostica richiede toggle, host e ultimo slot")

    def test_chill_star_hud_uses_cached_name_instead_of_leader_dereference(self) -> None:
        call = next(
            call for call in validator.iter_calls(self.source, "Create HUD Text")
            if len(call.args) >= 6
            and call.args[4].strip() == "Left"
            and call.args[5].strip() == "13"
        )
        changed_text = call.args[2].replace(
            "Custom String(\"\\nCHILL STAR: {0}\", Global.VoteLeaderName)",
            "Custom String(\"\\nCHILL STAR: {0}\", Player Variable(Global.VoteLeader, DisplayName))",
            1,
        )
        self.assertNotEqual(changed_text, call.args[2])
        mutated = self.replace_call_argument(call, 2, changed_text)
        self.assert_rejected(mutated, "non deve dereferenziare direttamente VoteLeader per il nome")

    def test_chill_star_hud_uses_cached_color(self) -> None:
        call = next(
            call for call in validator.iter_calls(self.source, "Create HUD Text")
            if len(call.args) >= 9
            and call.args[4].strip() == "Left"
            and call.args[5].strip() == "13"
        )
        mutated = self.replace_call_argument(call, 7, "Color(White)")
        self.assert_rejected(mutated, "colore Subheader deve usare la cache leader")

    def test_complete_global_control_help_is_required(self) -> None:
        mutated = self.replace_once('Hold {0}: hero + HP', "Hold {0}:")
        self.assert_rejected(mutated, "testo localizzato assente: Hold {0}: hero + HP")

    def test_info_controls_keep_the_crouch_binding(self) -> None:
        info = self.rule(lambda rule: validator.subroutine_target(rule) == "DrawInfoMenu")
        changed = info.body.replace("Button(Crouch)", "Button(Melee)", 1)
        self.assertNotEqual(changed, info.body)
        mutated = self.source[:info.start] + changed + self.source[info.end:]
        self.assert_rejected(mutated, "Info")

    def test_info_controls_keep_the_menu_and_camera_bindings(self) -> None:
        info = self.rule(lambda rule: validator.subroutine_target(rule) == "DrawInfoMenu")
        old = "Input Binding String(Button(Melee)), Input Binding String(Button(Interact))"
        new = "Input Binding String(Button(Interact)), Input Binding String(Button(Melee))"
        changed = info.body.replace(old, new, 1)
        self.assertNotEqual(changed, info.body)
        mutated = self.source[:info.start] + changed + self.source[info.end:]
        self.assert_rejected(mutated, "Info")

    def test_website_hud_keeps_its_distinct_pastel_gold_color(self) -> None:
        calls = list(validator.iter_calls(self.source, "Create HUD Text"))
        server_location = next(
            call for call in calls
            if len(call.args) >= 9
            and call.args[4].strip() == "Top"
            and call.args[5].strip() == "1"
        )
        lobby_time = next(
            call for call in calls
            if len(call.args) >= 9
            and call.args[4].strip() == "Left"
            and call.args[5].strip() == "0"
        )
        mutated = self.replace_call_argument(
            server_location,
            7,
            "Custom Color(254, 205, 110, 255)",
        )
        self.assert_rejected(mutated, 'cozywatch.org: colore subheader pastel gold esatto')
        mutated = self.replace_call_argument(server_location, 7, lobby_time.args[8])
        self.assert_rejected(mutated, "colore distinto da PLAYER VIBES")

    def test_menu_renderers_use_the_top_three_slot(self) -> None:
        renderer = self.rule(lambda rule: validator.subroutine_target(rule) == "DrawMainMenu")
        call = next(iter(validator.iter_calls(renderer.body, "Create HUD Text")))
        absolute = validator.Call(call.name, call.raw, call.args, renderer.start + call.start, renderer.start + call.end)
        mutated = self.replace_call_argument(absolute, 5, "100")
        self.assert_rejected(mutated, "DrawMainMenu: ordinamento HUD menu")

    def test_luck_effect_uses_the_same_top_three_slot_without_a_leading_gap(self) -> None:
        renderer = self.rule(lambda rule: "Event Player.LuckEffectHud = Last Text ID;" in rule.body)
        call = next(iter(validator.iter_calls(renderer.body, "Create HUD Text")))
        absolute = validator.Call(call.name, call.raw, call.args, renderer.start + call.start, renderer.start + call.end)
        mutated = self.replace_call_argument(absolute, 5, "-99")
        self.assert_rejected(mutated, "HUD effetto Try Your Luck: ordinamento")

    def test_primary_secondary_must_not_redraw_menu(self) -> None:
        rule = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Each Player" and "MenuCommand" in rule.body and "Button(Primary Fire)" in rule.body)
        mutated = self.inject_action(rule, "Destroy HUD Text(Event Player.MenuHud);")
        self.assert_rejected(mutated, "Primary/Secondary")

    def test_all_twelve_option_submenus_are_routed_and_main_toggles_have_no_submenu(self) -> None:
        router = self.rule(lambda rule: validator.subroutine_target(rule) == "DrawActiveMenuPage")
        for page in (0, 1, 2, 3, 4, 5, 6, 7, 10, 11, 13, 14):
            with self.subTest(page=page):
                mutated = self.replace_in_rule(router, f"MenuPage == {page}", "MenuPage == 16")
                self.assert_rejected(mutated, f"pagina {page}")
        for page in (8, 9, 12, 15):
            with self.subTest(main_toggle=page):
                mutated = self.replace_in_rule(router, "MenuPage == 0", f"MenuPage == {page}")
                self.assert_rejected(mutated, f"pagina {page} non deve avere un sottomenu")

    def test_page_thirteen_keeps_the_progressive_fly_copy_in_english(self) -> None:
        renderer = self.rule(lambda rule: validator.subroutine_target(rule) == "DrawGhostFlyMenu")
        mutated = self.replace_in_rule(renderer,
            "KEEP MOVING: 100% > 1000% / 20s",
            "LOOK TO STEER | HOLD FORWARD TO ACCELERATE")
        self.assert_rejected(mutated, "pagina 13 Ghost/Fly")

    def test_main_menu_cycles_exactly_over_pages_zero_through_fifteen(self) -> None:
        navigation = self.rule(
            lambda rule: "Event Player.MainMenuCursor = (Event Player.MainMenuCursor" in rule.body
        )
        mutated = self.replace_in_rule(
            navigation,
            "(Event Player.MenuCommand == 3 ? 1 : 15)) % 16;",
            "(Event Player.MenuCommand == 3 ? 1 : 14)) % 15;",
        )
        self.assert_rejected(mutated, "ciclo esatto 0..15")

    def test_main_menu_preview_keeps_pages_twelve_and_thirteen_distinct(self) -> None:
        main = self.rule(lambda rule: validator.subroutine_target(rule) == "DrawMainMenu")
        mutated = self.replace_in_rule(
            main,
            'Event Player.MainMenuCursor == 12 ? Custom String("12 - DUMMY FOLLOW',
            'Event Player.MainMenuCursor == 13 ? Custom String("12 - DUMMY FOLLOW',
        )
        self.assert_rejected(mutated, "pagina 12 e pagina 13 non sono distinte")

    def test_main_menu_router_cannot_choose_a_static_renderer_for_page_thirteen(self) -> None:
        router = self.rule(lambda rule: validator.subroutine_target(rule) == "DrawActiveMenuPage")
        mutated = self.replace_in_rule(
            router,
            "Call Subroutine(DrawMainMenu);",
            "If(Event Player.MainMenuCursor == 13);\n"
            "\t\t\t\tCall Subroutine(DrawGhostFlyMenu);\n"
            "\t\t\tElse;\n"
            "\t\t\t\tCall Subroutine(DrawMainMenu);\n"
            "\t\t\tEnd;",
        )
        self.assert_rejected(mutated, "renderer principale non deve essere scelto staticamente")

    def test_soundtrack_ability_latch_arms_only_on_page_two(self) -> None:
        router = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Event Player.MenuCommand == 0;" in rule.body
            and "Event Player.MenuCommand = 5;" in rule.body
            and "Event Player.MenuCommand = 6;" in rule.body
        )
        mutated = self.replace_in_rule(
            router,
            "And(Event Player.MenuPage == 3, Or(Is Button Held(Event Player, Button(Ability 1)), Is Button Held(Event Player, Button(Ability 2))))",
            "And(Event Player.MenuPage == 0, Or(Is Button Held(Event Player, Button(Ability 1)), Is Button Held(Event Player, Button(Ability 2))))",
        )
        self.assert_rejected(mutated, "Ability 1/2 devono armarsi sulla pagina 2 Soundtrack")

    def test_soundtrack_ability_commands_are_emitted_on_page_two(self) -> None:
        router = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Event Player.MenuCommand = 5;" in rule.body
            and "Event Player.MenuCommand = 6;" in rule.body
        )
        mutated = self.replace_in_rule(
            router,
            "Else If(And(Is Button Held(Event Player, Button(Ability 1)), Event Player.MenuPage == 3));",
            "Else If(And(Is Button Held(Event Player, Button(Ability 1)), Event Player.MenuPage == 0));",
        )
        self.assert_rejected(mutated, "Ability 1 non produce il comando 5 sulla pagina 2 Soundtrack")

    def test_soundtrack_jump_consumes_commands_on_page_two(self) -> None:
        jump = self.rule(
            lambda rule: "Event Player.GenreCursor = (Event Player.GenreCursor" in rule.body
            and "Event Player.MenuCommand == 5" in rule.body
            and "Event Player.MenuCommand == 6" in rule.body
        )
        mutated = self.replace_in_rule(
            jump,
            "Event Player.MenuPage == 3;",
            "Event Player.MenuPage == 0;",
        )
        self.assert_rejected(mutated, "salto Soundtrack ±10 deve consumare i comandi sulla pagina 2")

    def test_routine_small_messages_stay_suppressed(self) -> None:
        noisy = (
            "Arcade Menu online.",
            "Arcade Menu closed.",
            "Soundtrack: {0}.",
            "Third person on.",
            "Name color: {0}.",
            "Hero voice updated.",
            "Player icon: {0}.",
            "Crouch Teleport enabled.",
            "Crouch privacy enabled.",
            "Vote registered for {0}.",
            "Enemy dummy follow enabled.",
            "Wall phasing enabled.",
            "Fly enabled.",
            "Resurrected safely.",
            "Teleported to your Spawn Room.",
        )
        for marker in noisy:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, self.source)

    def test_menu_open_message_rejects_legacy_thirteen_page_wording(self) -> None:
        for legacy in (
            "Thirteen extremely important decisions",
            "Tiga belas keputusan",
            "มีสิบสามตัวเลือก",
        ):
            with self.subTest(legacy=legacy):
                mutated = self.source + f"\n// {legacy}\n"
                self.assert_rejected(mutated, "messaggio apertura menu obsoleto")

    def test_main_toggle_cannot_reopen_a_dedicated_submenu(self) -> None:
        dispatcher = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
                               and "Event Player.MenuCommand == 1;" in rule.body
                               and "ApplyDummyBotFollowPage" in rule.body)
        for name in ("ApplyCrouchTravel", "ApplyInspectionPrivacyPage",
                     "ApplyDummyBotFollowPage", "ApplySuperPunchPage"):
            with self.subTest(handler=name):
                mutated = self.replace_in_rule(dispatcher, f"Call Subroutine({name});",
                                               f"Call Subroutine({name});\n"
                                               "Event Player.MenuPage = Event Player.MainMenuCursor;\n"
                                               "Call Subroutine(DrawMenu);")
                self.assert_rejected(mutated, "deve conservare schermata, cursore e HUD")

    def test_main_toggle_must_dispatch_by_main_cursor_not_submenu_page(self) -> None:
        dispatcher = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
                               and "Event Player.MenuCommand == 1;" in rule.body
                               and "ApplyDummyBotFollowPage" in rule.body)
        for page in (8, 9, 12, 15):
            with self.subTest(page=page):
                mutated = self.replace_in_rule(dispatcher, f"Event Player.MainMenuCursor == {page}",
                                               f"Event Player.MenuPage == {page}")
                self.assert_rejected(mutated, "deve agire dal cursore principale")

    def test_direct_toggle_cannot_restore_retired_on_off_cursor(self) -> None:
        dispatcher = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Event Player.MenuCommand == 1;" in rule.body
            and "ApplyDummyBotFollowPage" in rule.body
        )
        mutated = self.inject_action(dispatcher, "Event Player.KursorIkutiBotBuatan = 0;")
        self.assert_rejected(mutated, "cursore ON/OFF obsoleto")

    def test_page_twelve_apply_dispatcher_is_required(self) -> None:
        dispatcher = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Event Player.MenuCommand == 1;" in rule.body
            and "ApplyDummyBotFollowPage" in rule.body
        )
        mutated = self.replace_in_rule(
            dispatcher,
            "Call Subroutine(ApplyDummyBotFollowPage);",
            "Abort;",
        )
        self.assert_rejected(mutated, "pagina 12 deve usare ApplyDummyBotFollowPage")

    def test_dummy_follow_renderer_is_localized_and_explicitly_enemy_scoped(self) -> None:
        renderer = self.rule(lambda rule: validator.subroutine_target(rule) == "DrawMainMenu")
        mutated = self.replace_in_rule(renderer, 'BOT MUSUH', "DUMMY")
        self.assert_rejected(mutated, 'BOT MUSUH')

    def test_page_twelve_has_a_dedicated_menu_tint(self) -> None:
        transition = self.rule(lambda rule: validator.subroutine_target(rule) == "TransitionMenuColor")
        mutated = self.replace_in_rule(
            transition,
            "Event Player.MenuPage) == 12 ?",
            "Event Player.MenuPage) == 13 ?",
        )
        self.assert_rejected(mutated, "pagina 12 Dummy Follow non ha una tinta")

    def test_dummy_follow_state_cannot_be_written_by_camera_or_other_features(self) -> None:
        camera_release = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Event Player.CameraInteractConsumed = False;" in rule.body
        )
        mutated = self.inject_action(camera_release, "Event Player.AllowDummyBotFollow = False;")
        self.assert_rejected(mutated, "scritto fuori da setup/apply/quiete")

    def test_dummy_follow_defaults_to_off(self) -> None:
        setup = self.rule(lambda rule: validator.subroutine_target(rule) == "PreparePlayer")
        mutated = self.replace_in_rule(setup, "Event Player.AllowDummyBotFollow = False;",
                                       "Event Player.AllowDummyBotFollow = True;")
        self.assert_rejected(mutated, "reset setup iniziale mancante")

    def test_dummy_follow_automatic_off_requires_live_enemy_dummy_and_on_state(self) -> None:
        cache = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerMaintenance")
        for current, wrong in (
            ("If(Global.ActivePlayer.AllowDummyBotFollow == True);", "If(True);"),
            ("Opposite Team Of(Team Of(Global.ActivePlayer))", "Team Of(Global.ActivePlayer)"),
            ("Set Player Variable(Global.ActivePlayer, AllowDummyBotFollow, False);", "Abort;"),
        ):
            with self.subTest(mutation=current):
                mutated = self.replace_in_rule(cache, current, wrong)
                self.assert_rejected(mutated, "OFF automatico 1 Hz")

    def test_interact_dispatch_is_split_into_page_handlers(self) -> None:
        mutated = self.source.replace("ApplyPlayerIconPage", "TerapkanIkonLegacy")
        self.assert_rejected(mutated, "16 subroutine pagina")

    def test_super_punch_contract_preserves_local_toggle_and_native_hit_guards(self) -> None:
        apply = self.rule(lambda rule: validator.subroutine_target(rule) == "ApplySuperPunchPage")
        runtime = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessSuperPunch")
        impact = self.rule(lambda rule: rule.name.startswith("89i1 -"))
        mutations = (
            (apply, "Event Player.HudSlot >= 12", "Event Player.HudSlot >= 13", "toggle registrato locale"),
            (apply, "Global.SuperPunchTimes[Event Player.HudSlot] = -1;",
             "Global.SuperPunchTimes[Event Player.HudSlot] = 0;", "toggle registrato locale"),
            (runtime, "Has Status(Global.SuperPunchTarget, Unkillable) == False", "True", "protezione stato Unkillable"),
            (runtime, "All Players(All Teams)", "All Players(Opposite Team Of(Team Of(Global.ActivePlayer)))", "entrambi i team"),
            (runtime, "<= 2.500", "<= 25", "portata melee limitata"),
            (runtime, "If(Global.SuperPunchTarget != Null);", "If(True);", "consumo soltanto dopo contatto"),
            (runtime, "If(Is Meleeing(Global.ActivePlayer) == False);",
             "Abort If(Global.ActivePlayer.MenuOpen == True);\n\t\tIf(Is Meleeing(Global.ActivePlayer) == False);",
             "menu aperto non deve bloccare l'ayunan"),
            (runtime, "Global.ActivePlayer.MeleeConsumed == True", "False", "guardia owner MeleeConsumed"),
            (runtime, "If(Is Meleeing(Global.ActivePlayer) == False);",
             "Abort If(Global.ActivePlayer.CrouchTravelActive == True);\n\t\tIf(Is Meleeing(Global.ActivePlayer) == False);",
             "Travel attivo non deve bloccare l'ayunan"),
            (impact, "Event Ability == Button(Melee);", "Event Ability == Button(Primary Fire);", "guardia impatto"),
            (impact, "Event Ability == Button(Melee);",
             "Event Player.MenuOpen == False;\n\t\tEvent Ability == Button(Melee);",
             "menu aperto non deve bloccare l'impatto nativo"),
            (impact, "Event Player.MeleeConsumed == False;", "", "guardia impatto"),
            (impact, "Event Ability == Button(Melee);",
             "Event Player.CrouchTravelActive == False;\n\t\tEvent Ability == Button(Melee);",
             "Travel attivo non deve bloccare l'impatto nativo"),
            (impact, "Hero Of(Event Player) != Hero(Junker Queen);", "", "guardia impatto"),
            (impact, "Has Status(Victim, Unkillable) == False", "True", "contratto impatto"),
            (impact, "Kill(Victim, Event Player);", "Kill(Victim, Global.ActivePlayer);", "contratto impatto"),
        )
        for rule, old, new, error in mutations:
            with self.subTest(mutation=old):
                self.assert_rejected(self.replace_in_rule(rule, old, new), "Super Punch: " + error)
        camera = self.rule(lambda rule: validator.subroutine_target(rule) == "StartCamera")
        changed = self.inject_action(camera, "Modify Global Variable(SuperPunchPlayers, Append To Array, Event Player);")
        self.assert_rejected(changed, "Super Punch: writer registro non autorizzato")

    def test_social_beacon_contract_preserves_fixed_radius_native_icons_and_bounded_owners(self) -> None:
        manager = self.rule(lambda rule: validator.subroutine_target(rule) == "UpdateSocialObjectiveIcons")
        mutated = self.replace_in_rule(manager, "For Global Variable(ObjectiveIconIndex, 0, 12, 1);",
                                       "For Global Variable(ObjectiveIconIndex, 0, 13, 1);")
        self.assert_rejected(mutated, "Pilar: manutenzione e cleanup limitati a dodici slot")
        call = next(validator.iter_calls(manager.body, "Create Icon"))
        absolute = validator.Call(call.name, call.raw, call.args, manager.start + call.start, manager.start + call.end)
        mutated = self.replace_call_argument(absolute, 2, 'Custom String("player name")')
        self.assert_rejected(mutated, "Pilar: ciascuna scelta deve conservare lo stesso tipo icona")
        mutated = self.replace_call_argument(absolute, 4, "Global.RGB")
        self.assert_rejected(mutated, "Pilar: RGB icona segue owner")
        mutated = self.replace_call_argument(absolute, 1, "Evaluate Once(" + call.args[1] + ")")
        self.assert_rejected(mutated, "Pilar: posizione fluida condivisa")
        mutated = self.replace_call_argument(absolute, 0, call.args[0].replace(
            "Player Variable(Evaluate Once(Global.ObjectiveIconPlayer), IsHuman) == True", "True"))
        self.assert_rejected(mutated, "Pilar: owner in uscita o cambio squadra nascosto subito")
        chase = next(validator.iter_calls(manager.body, "Chase Player Variable Over Time"))
        absolute_chase = validator.Call(chase.name, chase.raw, chase.args,
                                       manager.start + chase.start, manager.start + chase.end)
        mutated = self.replace_call_argument(absolute_chase, 4, "Destination and Duration")
        self.assert_rejected(mutated, "Pilar: chase Vector nativo congela destinazione")
        mutated = self.replace_call_argument(absolute_chase, 3, "3")
        self.assert_rejected(mutated, "Pilar: chase Vector nativo congela destinazione")
        mutated = self.replace_in_rule(manager, "Total Time Elapsed >= Global.ObjectiveIconTimes[Global.ObjectiveIconIndex] + 3",
                                       "Total Time Elapsed >= Global.ObjectiveIconTimes[Global.ObjectiveIconIndex] + 4.500")
        self.assert_rejected(mutated, "Pilar: rinnovo anticipato dopo tre secondi")
        renewal_chase = list(validator.iter_calls(manager.body, "Chase Player Variable Over Time"))[-1]
        renewal_start = manager.start + renewal_chase.start
        mutated = self.source[:renewal_start] + "Set Player Variable(" + renewal_chase.args[0] + ", ObjectiveIconPosition, Vector(0, 0.500, 0));" + self.source[renewal_start:]
        self.assert_rejected(mutated, "Pilar: rinnovo parte dalla posizione corrente")
        mutated = self.replace_in_rule(manager, "Stop Chasing Player Variable(Global.ObjectiveIconOwners[Global.ObjectiveIconIndex], ObjectiveIconPosition);", "")
        self.assert_rejected(mutated, "Pilar: manutenzione ferma la chase")
        mutated = self.replace_call_argument(absolute_chase, 2, chase.args[2].replace("Random Real(0, 10)", "Random Real(0, 11)"))
        self.assert_rejected(mutated, "Pilar: chase Vector nativo congela destinazione")
        mutated = self.replace_call_argument(absolute, 0, call.args[0].replace(
            "Array Contains(Global.HumanPlayers, Evaluate Once(Global.ObjectiveIconPlayer))", "True"))
        self.assert_rejected(mutated, "Pilar: visibilita richiede owner nel roster e obiettivo valido")
        init = self.rule(lambda rule: "Global.ObjectiveIconOwners = Array(" in rule.body)
        mutated = self.inject_action(init, "Create Effect(All Players(All Teams), Light Shaft, Color(White), Objective Position(Objective Index), 5, Visible To Position Radius and Color);")
        self.assert_rejected(mutated, "Pilar: nessun Light Shaft o Create Effect persistente")

    def test_menu_page_engine_actions_cannot_target_all_players(self) -> None:
        apply_color = self.rule(
            lambda rule: validator.subroutine_target(rule) == "ApplyNameColorPage"
        )
        mutated = self.inject_action(
            apply_color,
            "Set Gravity(All Players(All Teams), 50);",
        )
        self.assert_rejected(mutated, "isolamento menu per-player")

    def test_menu_subroutines_cannot_use_scheduler_scratch_or_local_viewer(self) -> None:
        apply_color = self.rule(
            lambda rule: validator.subroutine_target(rule) == "ApplyNameColorPage"
        )
        mutated = self.inject_action(
            apply_color,
            "Global.ActivePlayer.ColorCursor = 2;",
        )
        self.assert_rejected(mutated, "scratch globale o viewer locale")

        renderer = self.rule(lambda rule: validator.subroutine_target(rule) == "DrawNameColorMenu")
        mutated = self.inject_action(
            renderer,
            'Small Message(Local Player, Custom String("leak"));',
        )
        self.assert_rejected(mutated, "scratch globale o viewer locale")

    def test_menu_dispatch_requires_crouch(self) -> None:
        dispatcher = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Each Player" and "MenuCommand" in rule.body and "Button(Ability 2)" in rule.body)
        mutated = self.replace_in_rule(dispatcher, "Is Button Held(Event Player, Button(Crouch)) == True;", "Is Button Held(Event Player, Button(Crouch)) == False;")
        self.assert_rejected(mutated, "modificatore Crouch")

    def test_menu_dispatch_rejects_interact_already_consumed_by_camera(self) -> None:
        dispatcher = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Each Player" and "MenuCommand" in rule.body and "Button(Ability 2)" in rule.body)
        mutated = self.replace_in_rule(
            dispatcher,
            "Event Player.CameraInteractConsumed == False;",
            "Event Player.CameraInteractConsumed == True;",
        )
        self.assert_rejected(mutated, "non blocca Interact già consumato")

    def test_menu_interact_acquires_the_shared_camera_latch(self) -> None:
        dispatcher = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Each Player" and "MenuCommand" in rule.body and "Button(Ability 2)" in rule.body)
        mutated = self.replace_in_rule(
            dispatcher,
            "Event Player.CameraInteractConsumed = True;",
            "Event Player.CameraInteractConsumed = False;",
        )
        self.assert_rejected(mutated, "non acquisisce il latch Camera")

    def test_dead_menu_is_frozen(self) -> None:
        dispatcher = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Each Player" and "MenuCommand" in rule.body and "Button(Ability 2)" in rule.body)
        mutated = self.replace_in_rule(dispatcher, "Is Alive(Event Player) == True;", "Is Alive(Event Player) == False;")
        self.assert_rejected(mutated, "menu morto")

    def test_menu_input_allow_disallow_sets_are_symmetric(self) -> None:
        unlock = self.rule(lambda rule: "Allow Button(Event Player" in rule.body and "MenuInputLocked" in rule.body and "Crouch" in rule.body)
        mutated = self.replace_in_rule(unlock, "Allow Button(Event Player, Button(Ability 2));", "")
        self.assert_rejected(mutated, "simmetria")

    def test_melee_jump_and_crouch_are_never_locked(self) -> None:
        lock = self.rule(lambda rule: "Disallow Button(Event Player" in rule.body and "MenuInputLocked" in rule.body)
        mutated = self.inject_action(lock, "Disallow Button(Event Player, Button(Jump));")
        self.assert_rejected(mutated, "Melee, Jump e Crouch")

    def test_camera_is_available_with_the_menu_open_or_closed(self) -> None:
        camera = self.rule(lambda rule: "Button(Interact)" in rule.body and "Wait(0.500, Abort When False)" in rule.body and "CameraMode" in rule.body)
        self.assertNotIn("MenuOpen", validator.mask_strings(camera.body))
        mutated = self.inject_condition(camera, "Event Player.MenuOpen == False;")
        self.assert_rejected(mutated, "non deve dipendere dallo stato aperto/chiuso")

    def test_camera_requires_crouch_released_to_avoid_menu_interact_collision(self) -> None:
        camera = self.rule(lambda rule: "Button(Interact)" in rule.body and "Wait(0.500, Abort When False)" in rule.body and "CameraMode" in rule.body)
        mutated = self.replace_in_rule(
            camera,
            "Is Button Held(Event Player, Button(Crouch)) == False;",
            "Is Button Held(Event Player, Button(Crouch)) == True;",
        )
        self.assert_rejected(mutated, "interferisce con il modificatore Crouch")

    def test_interact_release_resets_the_shared_menu_camera_latch(self) -> None:
        release = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Event Player.CameraInteractConsumed == True;" in rule.body
            and "Is Button Held(Event Player, Button(Interact)) == False;" in rule.body
        )
        mutated = self.replace_in_rule(
            release,
            "Event Player.CameraInteractConsumed = False;",
            "Event Player.CameraInteractConsumed = True;",
        )
        self.assert_rejected(mutated, "rilascio Interact non azzera")

    def test_crouch_inspection_requires_menu_closed(self) -> None:
        inspection = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Each Player" and "InspectionActive = True" in rule.body and "Button(Crouch)" in rule.body)
        mutated = self.replace_in_rule(inspection, "Event Player.MenuOpen == False;", "Event Player.MenuOpen == True;")
        self.assert_rejected(mutated, "inspection/teleport")

    def test_player_death_must_not_close_visible_menu(self) -> None:
        death = self.rule(lambda rule: validator.event_type(rule) == "Player Died")
        mutated = self.inject_action(death, "Call Subroutine(CloseMenu);")
        self.assert_rejected(mutated, "morte non deve chiudere")

    def test_jump_resurrect_is_not_blocked_by_open_menu(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        mutated = self.inject_action(resurrect, "Abort If(Event Player.MenuOpen == False);")
        self.assert_rejected(mutated, "Jump Resurrect")

    def test_jump_resurrect_cannot_regress_to_respawn(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        mutated = self.replace_in_rule(
            resurrect,
            "Resurrect(Event Player);",
            "Respawn(Event Player);",
        )
        self.assert_rejected(mutated, "senza azioni Respawn")

    def test_jump_resurrect_uses_current_position_instead_of_death_snapshot(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        mutated = self.replace_in_rule(
            resurrect,
            "Nearest Walkable Position(Position Of(Event Player))",
            "Nearest Walkable Position(Event Player.DeathPosition)",
        )
        self.assert_rejected(mutated, "posizione live")

    def test_jump_resurrect_rejects_a_stale_walkable_candidate(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        mutated = self.replace_in_rule(
            resurrect,
            "Event Player.SafeRevivePosition = Nearest Walkable Position(Position Of(Event Player));",
            "",
        )
        self.assert_rejected(mutated, "posizione live")

    def test_jump_resurrect_cannot_be_gated_by_crouch_or_other_features(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        for condition in (
            "Event Player.CrouchTravelActive == False;",
            "Event Player.MenuOpen == False;",
            "Event Player.CameraMode == 0;",
            "Event Player.LuckActive == False;",
        ):
            with self.subTest(condition=condition):
                mutated = self.inject_condition(resurrect, condition)
                self.assert_rejected(mutated, "deve dipendere solo da identità umana, morte, latch e Jump")

    def test_jump_resurrect_cannot_use_spawn_room_fallback(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        mutated = self.inject_action(resurrect, "Event Player.TravelDestination = Position Of(First Of(Spawn Points(Team Of(Event Player))));")
        self.assert_rejected(mutated, "fallback Spawn Room")

    def test_jump_resurrect_requires_recovery_teleport_before_and_after_revive(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        teleports = list(validator.iter_calls(resurrect.body, "Teleport"))
        self.assertEqual(len(teleports), 2)
        for index, teleport in enumerate(teleports):
            with self.subTest(index=index):
                changed = resurrect.body[:teleport.start] + resurrect.body[teleport.end + 1:]
                mutated = self.source[:resurrect.start] + changed + self.source[resurrect.end:]
                self.assert_rejected(mutated, "Teleport prima e dopo Resurrect")

    def test_jump_resurrect_uses_one_fresh_candidate_for_both_teleports(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        for index, teleport in enumerate(validator.iter_calls(resurrect.body, "Teleport")):
            with self.subTest(index=index):
                absolute = validator.Call(teleport.name, teleport.raw, teleport.args,
                                          resurrect.start + teleport.start, resurrect.start + teleport.end)
                mutated = self.replace_call_argument(absolute, 1, "Event Player.DeathPosition")
                self.assert_rejected(mutated, "stesso candidato fresco con margine verticale")

    def test_jump_resurrect_rejects_candidate_overwrites(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        mutated = self.replace_in_rule(
            resurrect,
            "Resurrect(Event Player);",
            "Event Player.SafeRevivePosition = Event Player.DeathPosition;\n\t\tResurrect(Event Player);",
        )
        self.assert_rejected(mutated, "candidato e guardia sicurezza freschi")

    def test_jump_resurrect_walkable_query_is_done_once_before_recovery(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        candidate = "Event Player.SafeRevivePosition = Nearest Walkable Position(Position Of(Event Player));"
        changed = resurrect.body.replace(candidate, "", 1).replace(
            "Resurrect(Event Player);", "Resurrect(Event Player);\n\t\t" + candidate, 1,
        )
        mutated = self.source[:resurrect.start] + changed + self.source[resurrect.end:]
        self.assert_rejected(mutated, "candidato e guardia sicurezza freschi")
        self.assert_rejected(self.inject_action(resurrect, candidate), "unico Nearest Walkable")

    def test_jump_resurrect_has_no_abort_or_generic_safe_teleport_dependency(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        for action, message in (
            ("Abort;", "non deve avere percorsi Abort"),
            ("Call Subroutine(FindSafeTravelPosition);", "non deve dipendere dal validatore Teleport"),
        ):
            with self.subTest(action=action):
                mutated = self.inject_action(resurrect, action)
                self.assert_rejected(mutated, message)

    def test_jump_resurrect_never_shows_an_unavailable_small_message(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        mutated = self.inject_action(
            resurrect,
            'Small Message(Event Player, Custom String("Resurrect unavailable"));',
        )
        self.assert_rejected(mutated, "non deve mostrare Small Message dopo il tentativo")

    def test_jump_resurrect_is_unconditional_outside_the_void_branch(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        mutated = self.replace_in_rule(
            resurrect,
            "Resurrect(Event Player);",
            "If(True);\n\t\t\tResurrect(Event Player);\n\t\tEnd;",
        )
        self.assert_rejected(mutated, "deve essere incondizionato")

    def test_jump_resurrect_teleport_remains_confined_to_the_unsafe_branch(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        unsafe_guard = "If(Event Player.ReviveTeleportNeeded == True);"
        self.assertEqual(resurrect.body.count(unsafe_guard), 2)
        for index in range(2):
            with self.subTest(index=index):
                parts = resurrect.body.split(unsafe_guard)
                parts[index] += "If(True);"
                changed = unsafe_guard.join(parts[:index + 1]) + unsafe_guard.join(parts[index + 1:])
                mutated = self.source[:resurrect.start] + changed + self.source[resurrect.end:]
                self.assert_rejected(mutated, "guardia sicurezza")

    def test_jump_resurrect_detects_unwalkable_surfaces_even_when_raycast_hits(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        mutated = self.replace_in_rule(
            resurrect,
            "Distance Between(Event Player.SafeRevivePosition, Event Player.DeathPosition) > 0.500",
            "False",
        )
        self.assert_rejected(mutated, "guardia sicurezza include vuoto verticale e distanza")

    def test_jump_resurrect_refreshes_and_clears_its_recovery_flag(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        flag = re.search(r"Event Player\.ReviveTeleportNeeded = Or\([^;]+;", resurrect.body)
        self.assertIsNotNone(flag)
        assert flag is not None
        for assignment in (flag.group(0), "Event Player.ReviveTeleportNeeded = False;"):
            with self.subTest(assignment=assignment):
                mutated = self.replace_in_rule(resurrect, assignment, "")
                self.assert_rejected(mutated, "candidato e guardia sicurezza freschi")

    def test_jump_resurrect_recovery_flag_is_cleared_by_setup_and_cleanup(self) -> None:
        for lifecycle_name in ("PreparePlayer", "QuiescePlayer"):
            with self.subTest(lifecycle=lifecycle_name):
                lifecycle = self.rule(lambda rule: validator.subroutine_target(rule) == lifecycle_name)
                mutated = self.replace_in_rule(lifecycle, "Event Player.ReviveTeleportNeeded = False;", "")
                self.assert_rejected(mutated, f"reset flag recupero in {lifecycle_name}")

    def test_jump_resurrect_recovery_flag_cannot_be_written_by_another_feature(self) -> None:
        menu = self.rule(lambda rule: validator.subroutine_target(rule) == "DrawMainMenu")
        mutated = self.inject_action(menu, "Event Player.ReviveTeleportNeeded = True;")
        self.assert_rejected(mutated, "writer flag recupero Resurrect fuori dal tentativo o lifecycle")

    def test_jump_resurrect_reapplies_fly_after_effect_restore(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        mutated = self.replace_in_rule(resurrect, "Call Subroutine(ApplyGhostFlyPhysics);", "")
        self.assert_rejected(mutated, "riapplicare Fly")

    def test_jump_resurrect_confirms_success_in_same_tick(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        mutated = self.replace_in_rule(resurrect, "If(Is Alive(Event Player) == True);", "If(True);")
        self.assert_rejected(mutated, "riapplicare Fly")

    def test_jump_resurrect_does_not_need_position_forcing(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        mutated = self.inject_action(
            resurrect,
            "Start Forcing Player Position(Event Player, Event Player.SafeRevivePosition, False);",
        )
        self.assert_rejected(mutated, "forcing di posizione")

    def test_jump_resurrect_cannot_wait_or_loop(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        for action in ("Wait(0.016, Ignore Condition);", "Loop;"):
            with self.subTest(action=action):
                mutated = self.inject_action(resurrect, action)
                self.assert_rejected(mutated, "senza Wait/Loop")

    def test_jump_resurrect_cannot_rearm_during_same_press(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        mutated = self.inject_action(resurrect, "Event Player.JumpReviveConsumed = False;")
        self.assert_rejected(mutated, "non deve riarmarsi durante la stessa pressione")

    def test_redeath_cannot_rearm_jump_resurrect_while_jump_is_held(self) -> None:
        death = self.rule(
            lambda rule: validator.event_type(rule) == "Player Died"
            and "Event Player.DeathPosition = Position Of(Event Player);" in rule.body
        )
        mutated = self.inject_action(death, "Event Player.JumpReviveConsumed = False;")
        self.assert_rejected(mutated, "morte non deve riarmare il latch Resurrect")

    def test_self_kill_requires_an_exact_three_second_timestamp(self) -> None:
        self_kill = self.rule(
            lambda rule: "Kill(Event Player, Null);" in rule.body
            and "TravelCommand == 3" in rule.body
        )
        mutated = self.replace_in_rule(
            self_kill,
            "Event Player.NextSuicideTime = Total Time Elapsed + 3;",
            "Event Player.NextSuicideTime = Total Time Elapsed + 2;",
        )
        self.assert_rejected(mutated, "arming esatto a 3 secondi")

    def test_self_kill_cannot_run_before_its_cooldown_expires(self) -> None:
        self_kill = self.rule(
            lambda rule: "Kill(Event Player, Null);" in rule.body
            and "TravelCommand == 3" in rule.body
        )
        mutated = self.replace_in_rule(
            self_kill,
            "If(Total Time Elapsed >= Event Player.NextSuicideTime);",
            "If(True);",
        )
        self.assert_rejected(mutated, "protetto dal cooldown per-player")

    def test_self_kill_cooldown_cannot_reset_on_death(self) -> None:
        death = self.rule(
            lambda rule: validator.event_type(rule) == "Player Died"
            and "Event Player.DeathPosition = Position Of(Event Player);" in rule.body
        )
        mutated = self.inject_action(death, "Event Player.NextSuicideTime = 0;")
        self.assert_rejected(mutated, "numero writer setup/quiete/arming")

    def test_failed_jump_resurrect_releases_latch_only_after_jump_release(self) -> None:
        release = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Is Button Held(Event Player, Button(Jump)) == False;" in rule.body
            and "Event Player.JumpReviveConsumed = False;" in rule.body
        )
        mutated = self.replace_in_rule(
            release,
            "Is Button Held(Event Player, Button(Jump)) == False;",
            "Is Button Held(Event Player, Button(Jump)) == True;",
        )
        self.assert_rejected(mutated, "rilascio Jump deve riarmare")

    def test_jump_resurrect_release_requires_human_guards(self) -> None:
        release = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Is Button Held(Event Player, Button(Jump)) == False;" in rule.body
            and "Event Player.JumpReviveConsumed = False;" in rule.body
        )
        for guard in (
            "Event Player.IsHuman == True;",
            "Event Player.IsAutomaticBot == False;",
            "Is Dummy Bot(Event Player) == False;",
            "Event Player.JumpReviveConsumed == True;",
        ):
            with self.subTest(guard=guard):
                mutated = self.replace_in_rule(release, guard, "")
                self.assert_rejected(mutated, "rilascio latch Resurrect senza guardia")

    def test_jump_resurrect_release_works_alive_and_dead(self) -> None:
        release = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Is Button Held(Event Player, Button(Jump)) == False;" in rule.body
            and "Event Player.JumpReviveConsumed = False;" in rule.body
        )
        for alive in ("True", "False"):
            with self.subTest(alive=alive):
                mutated = self.inject_condition(release, f"Is Alive(Event Player) == {alive};")
                self.assert_rejected(mutated, "rilascio latch Resurrect deve funzionare da vivo e da morto")

    def test_ghost_wall_phasing_must_keep_floors_solid(self) -> None:
        physics = self.rule(lambda rule: validator.subroutine_target(rule) == "ApplyGhostFlyPhysics")
        mutated = self.replace_in_rule(
            physics,
            "Disable Movement Collision With Environment(Event Player, False);",
            "Disable Movement Collision With Environment(Event Player, True);",
        )
        self.assert_rejected(mutated, "pavimenti solidi")

    def test_fly_uses_raw_input_without_transforming_throttle(self) -> None:
        physics = self.rule(lambda rule: validator.subroutine_target(rule) == "ApplyGhostFlyPhysics")
        mutated = self.inject_action(
            physics,
            "Start Transforming Throttle(Event Player, 1, 1, Facing Direction Of(Event Player));",
        )
        self.assert_rejected(mutated, "input devono restare locali")

    def test_fly_ramp_requires_the_exact_progressive_percentage_formula(self) -> None:
        cycle = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerFlight")
        mutations = (
            (
                "Min(1000, 100 + Max(0, Total Time Elapsed - Global.ActivePlayer.FlyRampStartTime) * 45)",
                "Min(500, 100 + Max(0, Total Time Elapsed - Global.ActivePlayer.FlyRampStartTime) * 45)",
                "cap 1000%",
            ),
            (
                "Min(1000, 100 + Max(0, Total Time Elapsed - Global.ActivePlayer.FlyRampStartTime) * 45)",
                "Min(1000, 120 + Max(0, Total Time Elapsed - Global.ActivePlayer.FlyRampStartTime) * 45)",
                "base 100%",
            ),
            (
                "Min(1000, 100 + Max(0, Total Time Elapsed - Global.ActivePlayer.FlyRampStartTime) * 45)",
                "Min(1000, 100 + Max(0, Total Time Elapsed - Global.ActivePlayer.FlyRampStartTime) * 36)",
                "pendenza 45 punti/s",
            ),
        )
        for old, new, contract in mutations:
            with self.subTest(contract=contract):
                mutated = self.replace_in_rule(cycle, old, new)
                self.assert_rejected(mutated, "rampa Fly lineare 100%-1000% in 20 secondi")

    def test_fly_ramp_requires_local_directional_input(self) -> None:
        cycle = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerFlight")
        mutated = self.replace_in_rule(
            cycle,
            "Z Component Of(Throttle Of(Global.ActivePlayer))",
            "Dot Product(Throttle Of(Global.ActivePlayer), Facing Direction Of(Global.ActivePlayer))",
        )
        self.assert_rejected(mutated, "qualsiasi input direzionale locale")

    def test_fly_ramp_rejects_direction_filters_or_changed_deadzone(self) -> None:
        cycle = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerFlight")
        guard = (
            "Magnitude Of(Vector(X Component Of(Throttle Of(Global.ActivePlayer)), 0, "
            "Z Component Of(Throttle Of(Global.ActivePlayer)))) > 0.050"
        )
        mutations = (
            (
                guard,
                "Z Component Of(Throttle Of(Global.ActivePlayer)) > 0.050",
            ),
            (
                guard,
                "Magnitude Of(Vector(X Component Of(Throttle Of(Global.ActivePlayer)), 0, 0)) > 0.050",
            ),
            (
                guard,
                guard.replace("> 0.050", "> 0.100"),
            ),
        )
        for old, new in mutations:
            with self.subTest(gate=new):
                mutated = self.replace_in_rule(cycle, old, new)
                self.assert_rejected(mutated, "qualsiasi input direzionale locale")

    def test_fly_idle_input_rearms_speed_and_timestamp(self) -> None:
        cycle = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerFlight")
        mutated = self.replace_in_rule(
            cycle,
            "Global.ActivePlayer.FlyRampStartTime = -1;\n"
            "\t\t\t\t\tGlobal.ActivePlayer.FlyPercent = 100;",
            "Global.ActivePlayer.FlyRampStartTime = -1;\n"
            "\t\t\t\t\tGlobal.ActivePlayer.FlyPercent = 150;",
        )
        self.assert_rejected(mutated, "solo assenza di input direzionale")

    def test_fly_luck_acceleration_has_priority_over_directional_ramp(self) -> None:
        cycle = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerFlight")
        mutated = self.replace_in_rule(
            cycle,
            "If(And(Global.ActivePlayer.LuckEffect == 2, Global.ActivePlayer.LuckEffectEndTime > Total Time Elapsed));",
            "If(And(Global.ActivePlayer.LuckEffect == 1, Global.ActivePlayer.LuckEffectEndTime > Total Time Elapsed));",
        )
        self.assert_rejected(mutated, "Try Your Luck Acceleration deve avere precedenza")

    def test_fly_cycle_and_motor_cannot_use_start_or_stop_accelerating(self) -> None:
        for owner in ("ProcessPlayerCycle", "ProcessPlayerFlight"):
            cycle = self.rule(lambda rule: validator.subroutine_target(rule) == owner)
            for action in (
                "Start Accelerating(Global.ActivePlayer, Facing Direction Of(Global.ActivePlayer), 1, 1, To World, Direction Rate and Max Speed);",
                "Stop Accelerating(Global.ActivePlayer);",
            ):
                with self.subTest(owner=owner, action=action):
                    mutated = self.inject_action(cycle, action)
                    self.assert_rejected(mutated, "Start/Stop Accelerating")

    def test_fly_motor_rejects_another_player_as_the_movement_target(self) -> None:
        motor = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerFlight")
        mutated = self.replace_in_rule(motor, "Apply Impulse(Global.ActivePlayer,", "Apply Impulse(Host Player,")
        self.assert_rejected(mutated, "unico impulso delta non nullo")

    def test_fly_backward_input_must_not_be_forced_by_view_impulse(self) -> None:
        cycle = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerFlight")
        mutated = self.inject_action(
            cycle,
            "Apply Impulse(Global.ActivePlayer, Facing Direction Of(Global.ActivePlayer) * -1, 9, To World, Cancel Contrary Motion);",
        )
        self.assert_rejected(mutated, "input indietro")

    def test_fly_idle_brake_requires_the_exact_opposite_impulse(self) -> None:
        cycle = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerFlight")
        mutated = self.replace_in_rule(
            cycle,
            "Global.ActivePlayer.FlyVelocityDelta = Velocity Of(Global.ActivePlayer) * -1;",
            "Global.ActivePlayer.FlyVelocityDelta = Vector(0, 0, 0);",
        )
        self.assert_rejected(mutated, "impulso esattamente opposto alla deriva")

    def test_fly_actions_cannot_escape_their_per_player_input_guards(self) -> None:
        cycle = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerFlight")
        for action, fragment in (
            (
                "Global.ActivePlayer.FlyPercent = Min(1000, 100 + Max(0, Total Time Elapsed - Global.ActivePlayer.FlyRampStartTime) * 45);",
                "guardia di qualsiasi input direzionale",
            ),
            (
                "Apply Impulse(Global.ActivePlayer, Global.ActivePlayer.FlyVelocityDelta, Magnitude Of(Global.ActivePlayer.FlyVelocityDelta), To World, Incorporate Contrary Motion);",
                "guardia per-player umano vivo",
            ),
        ):
            with self.subTest(action=action):
                self.assertIn(action, cycle.body)
                changed = cycle.body.replace(action, "", 1)
                closing = changed.rfind("\n\t}")
                self.assertGreater(closing, 0)
                changed = changed[:closing] + f"\n\t\t{action}" + changed[closing:]
                mutated = self.source[:cycle.start] + changed + self.source[cycle.end:]
                self.assert_rejected(mutated, fragment)

    def test_fly_motor_requires_every_per_player_lifecycle_guard(self) -> None:
        motor = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerFlight")
        for token in (
            "Global.ActivePlayer.IsHuman == True",
            "Global.ActivePlayer.IsAutomaticBot == False",
            "Is Dummy Bot(Global.ActivePlayer) == False",
            "Has Spawned(Global.ActivePlayer) == True",
            "Is Alive(Global.ActivePlayer) == True",
            "Global.ActivePlayer.FlyModeActive == True",
            "Global.ActivePlayer.GhostFlyPhysicsApplied == True",
        ):
            with self.subTest(guard=token):
                mutated = self.replace_in_rule(motor, token, "True")
                self.assert_rejected(mutated, "guardia per-player umano vivo")

    def test_fly_motor_requires_forward_pitch_only_and_horizontal_back_strafe(self) -> None:
        motor = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerFlight")
        for old, new in (
            (
                "Facing Direction Of(Global.ActivePlayer) * Max(0, Z Component Of(Throttle Of(Global.ActivePlayer)))",
                "Direction From Angles(Horizontal Facing Angle Of(Global.ActivePlayer), 0) * Max(0, Z Component Of(Throttle Of(Global.ActivePlayer)))",
            ),
            (
                "Direction From Angles(Horizontal Facing Angle Of(Global.ActivePlayer), 0) * Min(0, Z Component Of(Throttle Of(Global.ActivePlayer)))",
                "Facing Direction Of(Global.ActivePlayer) * Min(0, Z Component Of(Throttle Of(Global.ActivePlayer)))",
            ),
            (
                "Cross Product(Vector(0, 1, 0), Direction From Angles(Horizontal Facing Angle Of(Global.ActivePlayer), 0)) * X Component Of(Throttle Of(Global.ActivePlayer))",
                "Cross Product(Vector(0, 1, 0), Direction From Angles(Horizontal Facing Angle Of(Global.ActivePlayer), 0)) * 1",
            ),
        ):
            with self.subTest(direction=old):
                mutated = self.replace_in_rule(motor, old, new)
                self.assert_rejected(mutated, "solo l'input avanti usa il pitch")

    def test_fly_target_velocity_is_normalized_capped_and_subtracts_current_velocity(self) -> None:
        motor = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerFlight")
        for old, new in (
            ("Normalize(Global.ActivePlayer.FlyDirection)", "Global.ActivePlayer.FlyDirection"),
            ("* 5.500 *", "* 10 *"),
            ("Min(1, Magnitude Of(Throttle Of(Global.ActivePlayer)))", "Magnitude Of(Throttle Of(Global.ActivePlayer))"),
            ("- Velocity Of(Global.ActivePlayer);", "+ Velocity Of(Global.ActivePlayer);"),
        ):
            with self.subTest(target=old):
                mutated = self.replace_in_rule(motor, old, new)
                self.assert_rejected(mutated, "velocità target 3D")

    def test_fly_delta_impulse_cannot_cancel_or_repeat_existing_motion(self) -> None:
        motor = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerFlight")
        for old, new in (
            ("To World, Incorporate Contrary Motion);", "To World, Cancel Contrary Motion);"),
            ("If(Magnitude Of(Global.ActivePlayer.FlyVelocityDelta) > 0.010);", "If(True);"),
        ):
            with self.subTest(impulse=old):
                mutated = self.replace_in_rule(motor, old, new)
                self.assert_rejected(mutated, "unico impulso delta non nullo")

    def test_fly_motor_must_disable_native_locomotion(self) -> None:
        for owner, old, new, fragment in (
            ("ApplyGhostFlyPhysics", "Set Move Speed(Event Player, 0);",
             "Set Move Speed(Event Player, 100);", "locomozione nativa disabilitata"),
            ("ProcessPlayerFlight", "Set Move Speed(Global.ActivePlayer, 0);",
             "Set Move Speed(Global.ActivePlayer, 100);", "senza scritture fisiche"),
        ):
            with self.subTest(owner=owner):
                rule = self.rule(lambda rule: validator.subroutine_target(rule) == owner)
                self.assert_rejected(self.replace_in_rule(rule, old, new), fragment)

    def test_fly_motor_must_run_at_twenty_hz_after_luck(self) -> None:
        scheduler = self.rule(lambda rule: validator.action_loop_count(rule.body) == 1)
        call = "Call Subroutine(ProcessPlayerFlight);"
        mutated = self.replace_in_rule(scheduler, call, "If(Global.SchedulerStep % 2 == 0);\n"
                                       f"\t\t\t\t\t{call}\n\t\t\t\tEnd;")
        self.assert_rejected(mutated, "scheduler a stati: Fly solo umano attivo")

    def test_fly_state_cannot_be_written_from_another_controller(self) -> None:
        cycle = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerCycle")
        for variable in ("FlyPercent", "FlyDirection", "FlyVelocityDelta"):
            with self.subTest(variable=variable):
                mutated = self.inject_action(cycle, f"Global.ActivePlayer.{variable} = 0;")
                self.assert_rejected(mutated, f"owner per-player esclusivi di {variable}")

    def test_fly_state_cannot_be_written_to_another_player(self) -> None:
        motor = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerFlight")
        for variable in ("FlyPercent", "FlyDirection", "FlyVelocityDelta"):
            with self.subTest(variable=variable):
                mutated = self.inject_action(motor, f"Set Player Variable(Host Player, {variable}, 0);")
                self.assert_rejected(mutated, f"scritture {variable} fuori dai target per-player")

    def test_fly_off_brake_must_not_cancel_luck_acceleration(self) -> None:
        physics = self.rule(lambda rule: validator.subroutine_target(rule) == "ApplyGhostFlyPhysics")
        action = "Apply Impulse(Event Player, Velocity Of(Event Player) * -1, Magnitude Of(Velocity Of(Event Player)), To World, Incorporate Contrary Motion);"
        changed = physics.body.replace(action, "", 1)
        closing = changed.rfind("\n\t}")
        changed = changed[:closing] + f"\n\t\t{action}" + changed[closing:]
        mutated = self.source[:physics.start] + changed + self.source[physics.end:]
        self.assert_rejected(mutated, "freno locale non deve cancellare Acceleration")

    def test_try_your_luck_cannot_restore_gravity_or_fly_throttle(self) -> None:
        cleanup = self.rule(lambda rule: validator.subroutine_target(rule) == "RestorePlayerLuck")
        for action, expected in (
            ("Set Gravity(Event Player, 100);", "gravità"),
            ("Stop Transforming Throttle(Event Player);", "arresto throttle Fly"),
        ):
            with self.subTest(action=action):
                mutated = self.inject_action(cleanup, action)
                self.assert_rejected(mutated, f"Try Your Luck non deve modificare {expected}")

    def test_full_hp_application_requires_damage_knockback_and_player_phasing(self) -> None:
        apply = self.rule(lambda rule: validator.subroutine_target(rule) == "ApplyUnkillablePage")
        for token in (
            "Set Damage Received(Event Player, 0);",
            "Set Knockback Received(Event Player, 0);",
            "Disable Movement Collision With Players(Event Player);",
        ):
            with self.subTest(token=token):
                mutated = self.replace_in_rule(apply, token, "")
                self.assert_rejected(mutated, "FULL HP applicazione")

    def test_full_hp_global_reapply_requires_the_complete_protection_triplet(self) -> None:
        processor = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerFastState")
        for token in (
            "Set Damage Received(Global.ActivePlayer, 0);",
            "Set Knockback Received(Global.ActivePlayer, 0);",
            "Disable Movement Collision With Players(Global.ActivePlayer);",
        ):
            with self.subTest(token=token):
                mutated = self.replace_in_rule(processor, token, "")
                self.assert_rejected(mutated, "FULL HP riapplicazione globale")

    def test_full_hp_off_restores_damage_knockback_and_player_collision(self) -> None:
        apply = self.rule(lambda rule: validator.subroutine_target(rule) == "ApplyUnkillablePage")
        off_anchor = apply.body.index("If(Event Player.UnkillableMode == 0);")
        mode_one_anchor = apply.body.index("If(Event Player.UnkillableMode == 1);", off_anchor)
        off_body = apply.body[off_anchor:mode_one_anchor]
        self.assertIn("Enable Movement Collision With Players(Event Player);", off_body)
        changed = off_body.replace("Enable Movement Collision With Players(Event Player);", "", 1)
        mutated_body = apply.body[:off_anchor] + changed + apply.body[mode_one_anchor:]
        mutated = self.source[:apply.start] + mutated_body + self.source[apply.end:]
        self.assert_rejected(mutated, "FULL HP uscita OFF")

    def test_try_your_luck_start_preserves_unkillable_preference_and_runtime(self) -> None:
        luck = self.rule(lambda rule: validator.subroutine_target(rule) == "ApplyLuckPage")
        mutations = (
            ("Event Player.UnkillableMode = 0;", "non deve modificare UnkillableMode"),
            ("Event Player.UnkillableCursor = 0;", "non deve modificare UnkillableCursor"),
            ("Event Player.UnkillableActive = False;", "non deve modificare UnkillableActive"),
            ("Clear Status(Event Player, Unkillable);", "non deve sospendere status Unkillable"),
            ("Set Status(Event Player, Null, Unkillable, 9999);", "non deve sospendere status Unkillable"),
            ("Set Damage Received(Event Player, 100);", "non deve sospendere Damage Received"),
            ("Set Knockback Received(Event Player, 100);", "non deve sospendere Knockback Received"),
            ("Enable Movement Collision With Players(Event Player);", "non deve sospendere collisione player"),
            ("Set Player Health(Event Player, Max Health(Event Player));", "non deve sospendere salute Unkillable"),
            ("Destroy Icon(Event Player.UnkillableIcon);", "non deve sospendere icona Unkillable"),
        )
        for action, expected in mutations:
            with self.subTest(action=action):
                self.assert_rejected(self.inject_action(luck, action), expected)

    def test_full_hp_shared_cleanup_restores_knockback(self) -> None:
        cleanup = self.rule(lambda rule: validator.subroutine_target(rule) == "RestorePlayerLuck")
        mutated = self.replace_in_rule(cleanup, "Set Knockback Received(Event Player, 100);", "")
        self.assert_rejected(mutated, "FULL HP cleanup RestorePlayerLuck")

    def test_luck_cleanup_preserves_mode_and_cursor_and_reactivates_unkillable(self) -> None:
        for subroutine, target in (
            ("RestorePlayerLuck", "Event Player"),
            ("RestoreActivePlayerLuck", "Global.ActivePlayer"),
        ):
            cleanup = self.rule(lambda rule, name=subroutine: validator.subroutine_target(rule) == name)
            logical_restore = f"{target}.UnkillableActive = {target}.UnkillableMode != 0;"
            with self.subTest(subroutine=subroutine, mutation="logical restore"):
                mutated = self.replace_in_rule(cleanup, logical_restore, f"{target}.UnkillableActive = False;")
                self.assert_rejected(mutated, "deve riattivare logicamente Kebal")
            for field in ("UnkillableMode", "UnkillableCursor"):
                with self.subTest(subroutine=subroutine, field=field):
                    mutated = self.inject_action(cleanup, f"{target}.{field} = 0;")
                    self.assert_rejected(mutated, f"non deve cancellare la preferenza {field}")

    def test_luck_cleanup_reactivates_unkillable_after_engine_normalization(self) -> None:
        cleanup = self.rule(lambda rule: validator.subroutine_target(rule) == "RestorePlayerLuck")
        clear = "Clear Status(Event Player, Unkillable);"
        restore = "Event Player.UnkillableActive = Event Player.UnkillableMode != 0;"
        self.assertLess(cleanup.body.index(clear), cleanup.body.index(restore))
        changed = cleanup.body.replace(clear, "__CLEAR_UNKILLABLE__", 1)
        changed = changed.replace(restore, clear, 1).replace("__CLEAR_UNKILLABLE__", restore, 1)
        mutated = self.source[:cleanup.start] + changed + self.source[cleanup.end:]
        self.assert_rejected(mutated, "deve riattivare Kebal dopo la normalizzazione")

    def test_only_one_loop_is_allowed(self) -> None:
        mutated = self.source + "\nLoop;\n"
        self.assert_rejected(mutated, "numero Loop")

    def test_at_most_seven_waits_are_allowed(self) -> None:
        scheduler = self.rule(lambda rule: validator.action_loop_count(rule.body) == 1)
        mutated = self.source
        for delay in ("0.001", "0.002", "0.003"):
            current = next(
                rule for rule in validator.extract_rules(mutated)
                if validator.action_loop_count(rule.body) == 1
            )
            closing = current.body.rfind("\n\t}")
            changed = current.body[:closing] + f"\n\t\tWait({delay}, Ignore Condition);" + current.body[closing:]
            mutated = mutated[:current.start] + changed + mutated[current.end:]
        self.assertGreater(len(validator.wait_calls(mutated)), 7)
        self.assert_rejected(mutated, "Wait oltre")

    def test_wait_allowlist_rejects_changed_delay(self) -> None:
        classifier = self.rule(lambda rule: "Start Forcing Dummy Bot Name(Event Player" in rule.body)
        mutated = self.replace_in_rule(
            classifier,
            "Wait(0.016, Ignore Condition);",
            "Wait(0.100, Ignore Condition);",
        )
        self.assert_rejected(mutated, "Wait nominativamente consentiti")

    def test_wait_outside_allowlist_is_rejected(self) -> None:
        renderer = self.rule(lambda rule: validator.subroutine_target(rule) == "DrawMainMenu")
        mutated = self.inject_action(renderer, "Wait(0.050, Ignore Condition);")
        self.assert_rejected(mutated, "Wait non allowlisted")

    def test_scheduler_cadences_are_required(self) -> None:
        scheduler = self.rule(lambda rule: validator.action_loop_count(rule.body) == 1)
        self.assertIn("SchedulerStep % 20", scheduler.body)
        changed = scheduler.body.replace("SchedulerStep % 20", "SchedulerStep % 21")
        mutated = self.source[:scheduler.start] + changed + self.source[scheduler.end:]
        self.assert_rejected(mutated, "cadenza scheduler %20")

    def test_scheduler_scratch_is_exclusively_written_by_scheduler(self) -> None:
        renderer = self.rule(lambda rule: validator.subroutine_target(rule) == "DrawMainMenu")
        mutated = self.inject_action(renderer, "Global.ActivePlayer = Event Player;")
        self.assert_rejected(mutated, "scrittura ActivePlayer")

    def test_scans_cannot_yield(self) -> None:
        scheduler = self.rule(lambda rule: validator.action_loop_count(rule.body) == 1)
        token = "Global.ActivePlayer = Global.PlayerListSnapshot[Global.SchedulerPlayerIndex];"
        mutated = self.replace_in_rule(scheduler, token, token + "\n\t\t\tWait(0.001, Ignore Condition);")
        self.assert_rejected(mutated, "yield durante scansione")

    def test_scheduler_subroutines_have_no_wait_or_loop(self) -> None:
        process = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerMaintenance")
        mutated = self.inject_action(process, "Wait(0.050, Ignore Condition);")
        self.assert_rejected(mutated, "subroutine scheduler")

    def test_try_your_luck_has_exactly_six_outcomes(self) -> None:
        self.assertIn("Random Integer(1, 6)", self.source)
        mutated = self.source.replace("Random Integer(1, 6)", "Random Integer(1, 5)")
        self.assert_rejected(mutated, "sei esiti")

    def test_try_your_luck_skull_arms_full_death_machine(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerLuck")
        mutated = self.replace_in_rule(
            machine,
            "Global.ActivePlayer.ForcedRevengeEndTime = Total Time Elapsed + 5;",
            "Global.ActivePlayer.ForcedRevengeEndTime = 0;",
        )
        self.assert_rejected(mutated, "Skull non arma deadline anti-blocco")

    def test_burning_temporarily_bypasses_unkillable_and_scales_with_max_health(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerLuck")
        mutated = self.replace_in_rule(
            machine,
            "Clear Status(Global.ActivePlayer, Unkillable);",
            "Clear Status(Global.ActivePlayer, Burning);",
        )
        self.assert_rejected(mutated, "Burning deve sospendere Unkillable")

        mutated = self.replace_in_rule(
            machine,
            "Damage(Global.ActivePlayer, Global.ActivePlayer, Max Health(Global.ActivePlayer) * 0.050);",
            "Damage(Global.ActivePlayer, Global.ActivePlayer, 25);",
        )
        self.assert_rejected(mutated, "5% della Max Health")

        mutated = self.replace_in_rule(
            machine,
            "Global.ActivePlayer.NextLuckBurnTime = Total Time Elapsed + 1.000;",
            "Global.ActivePlayer.NextLuckBurnTime = Total Time Elapsed + 0.500;",
        )
        self.assert_rejected(mutated, "tick da un secondo")
    def test_unkillable_reapply_is_blocked_for_revenge_skull_and_active_burning(self) -> None:
        processor = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerFastState")
        exact_exception = (
            "And(And(Global.ActivePlayer.LuckActive == True, Global.ActivePlayer.LuckSpinCount == 0), "
            "Or(And(Global.ActivePlayer.LuckEffect == 3, Global.ActivePlayer.ForcedRevengeEndTime > 0), "
            "And(Global.ActivePlayer.LuckEffect == 5, Global.ActivePlayer.LuckEffectEndTime > Total Time Elapsed))) == False"
        )
        mutated = self.replace_in_rule(
            processor,
            exact_exception,
            "Global.ActivePlayer.LuckActive == False",
        )
        self.assert_rejected(mutated, "blocco riapplicazione Kebal durante Skull/Burning finali")
    def test_global_unkillable_reapply_recreates_missing_or_destroyed_icon(self) -> None:
        processor = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerFastState")
        safe_guard = (
            "If(Or(Global.ActivePlayer.UnkillableIcon == Null, "
            "Entity Exists(Global.ActivePlayer.UnkillableIcon) == False));"
        )
        mutated = self.replace_in_rule(
            processor,
            safe_guard,
            "If(Global.ActivePlayer.UnkillableIcon == Null);",
        )
        self.assert_rejected(mutated, "non ricrea in sicurezza un'icona assente o non più esistente")

        mutated = self.replace_in_rule(
            processor,
            "Create Icon(All Players(All Teams), Evaluate Once(Global.ActivePlayer), Halo, Visible To and Position, Global.RGB, True);",
            "",
        )
        self.assert_rejected(mutated, "deve ricreare le icone 1 HP e FULL HP")

        mutated = self.replace_in_rule(
            processor,
            "Create Icon(All Players(All Teams), Evaluate Once(Global.ActivePlayer), Halo, Visible To and Position, Global.RGB, True);",
            "Create Icon(All Players(All Teams), Global.ActivePlayer, Halo, Visible To and Position, Global.RGB, True);",
        )
        self.assert_rejected(mutated, "identità owner catturata")

        mutated = self.replace_in_rule(
            processor,
            "Global.ActivePlayer.UnkillableIcon = Last Created Entity;",
            "",
        )
        self.assert_rejected(mutated, "salvataggio handle icona")

    def test_full_death_machine_owns_the_only_kill(self) -> None:
        processor = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerFastState")
        kill = next(iter(validator.iter_calls(processor.body, "Kill")))
        absolute = validator.Call(kill.name, kill.raw, kill.args, processor.start + kill.start, processor.start + kill.end)
        mutated = self.source[:absolute.start] + "" + self.source[absolute.end:]
        self.assert_rejected(mutated, "un solo Kill nel processor globale")

    def test_full_death_kill_branch_requires_a_live_target(self) -> None:
        processor = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerFastState")
        mutated = self.replace_in_rule(
            processor,
            "Else If(And(Has Spawned(Global.ActivePlayer) == True, "
            "And(Is Alive(Global.ActivePlayer) == True, "
            "Total Time Elapsed >= Global.ActivePlayer.NextForcedRevengeTime)));",
            "Else If(And(Has Spawned(Global.ActivePlayer) == True, "
            "And(Is Alive(Global.ActivePlayer) == False, "
            "Total Time Elapsed >= Global.ActivePlayer.NextForcedRevengeTime)));",
        )
        self.assert_rejected(mutated, "retry soltanto se ancora vivo nello stesso ramo di Kill")

    def test_revenge_timeout_clears_the_pending_flag(self) -> None:
        processor = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerFastState")
        mutated = self.replace_in_rule(
            processor,
            "Set Player Variable(Global.ActivePlayer.RevengeClaimant, "
            "LockedRevengeTarget, Null);\n"
            "\t\t\t\t\tGlobal.ActivePlayer.RevengeDeathPending = False;",
            "Set Player Variable(Global.ActivePlayer.RevengeClaimant, "
            "LockedRevengeTarget, Null);",
        )
        self.assert_rejected(mutated, "timeout Revenge non azzera flag pending")

    def test_skull_timeout_destroys_the_roulette_icon(self) -> None:
        processor = self.rule(lambda rule: validator.subroutine_target(rule) == "RestoreActivePlayerLuck")
        mutated = self.replace_in_rule(
            processor,
            "Destroy Icon(Global.ActivePlayer.LuckIcon);",
            "",
        )
        self.assert_rejected(mutated, "timeout Skull deve distruggere l'icona")

    def test_skull_cannot_trigger_from_a_transient_roulette_icon(self) -> None:
        processor = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerFastState")
        mutated = self.replace_in_rule(
            processor,
            "And(Global.ActivePlayer.LuckSpinCount == 0, Global.ActivePlayer.ForcedRevengeEndTime > 0)",
            "True",
        )
        self.assert_rejected(mutated, "Skull finale armato dopo la roulette")

    def test_revenge_cannot_consume_debt_at_click(self) -> None:
        apply = self.rule(lambda rule: validator.subroutine_target(rule) == "ApplyRevengePage")
        mutated = self.inject_action(
            apply,
            "Modify Player Variable At Index(Event Player, RevengeDebts, Event Player.RevengeIndex, Subtract, 1);",
        )
        self.assert_rejected(mutated, "non deve consumare il debito prima della morte completa")

    def test_revenge_commit_requires_actual_death(self) -> None:
        recorder = self.rule(
            lambda rule: validator.event_type(rule) == "Player Died"
            and "RevengeClaimant" in rule.body
            and "RevengeKillers" in rule.body
        )
        mutated = self.replace_in_rule(
            recorder,
            "If(Is Alive(Event Player) == False);",
            "If(Is Alive(Event Player) == True);",
        )
        self.assert_rejected(mutated, "conferma Is Alive falso")

    def test_revenge_recomputes_debt_index_at_commit(self) -> None:
        recorder = self.rule(
            lambda rule: validator.event_type(rule) == "Player Died"
            and "RevengeClaimant" in rule.body
            and "RevengeKillers" in rule.body
        )
        recompute = (
            "Index Of Array Value(Player Variable(Event Player.RevengeClaimant, "
            "RevengeKillers), Event Player)"
        )
        mutated = self.replace_in_rule(recorder, recompute, "Event Player.RevengeIndex")
        self.assert_rejected(mutated, "ricalcolo indice debito al commit")

    def test_revenge_commit_aborts_before_the_natural_recorder(self) -> None:
        recorder = self.rule(
            lambda rule: validator.event_type(rule) == "Player Died"
            and "RevengeClaimant" in rule.body
            and "RevengeKillers" in rule.body
        )
        mutated = self.replace_in_rule(
            recorder,
            "Event Player.ForcedRevengeEndTime = 0;\n\t\t\t\t\tAbort;",
            "Event Player.ForcedRevengeEndTime = 0;",
        )
        self.assert_rejected(mutated, "Abort prima del recorder naturale")

    def test_try_your_luck_cleanup_waits_for_full_death(self) -> None:
        cleanup = self.rule(
            lambda rule: validator.event_type(rule) == "Player Died"
            and "LuckActive" in rule.body
            and "Call Subroutine(RestorePlayerLuck);" in rule.body
        )
        mutated = self.replace_in_rule(cleanup, "\n\t\tIs Alive(Event Player) == False;", "")
        self.assert_rejected(mutated, "deve attendere la morte completa")

    def test_jump_respawn_prompt_waits_for_full_death(self) -> None:
        death_prompt = self.rule(
            lambda rule: validator.event_type(rule) == "Player Died"
            and "Event Player.DeathPosition = Position Of(Event Player);" in rule.body
        )
        mutated = self.replace_in_rule(death_prompt, "\n\t\tIs Alive(Event Player) == False;", "")
        self.assert_rejected(mutated, "Bangkit Lompat deve attendere la morte completa")

    def test_dummy_death_stop_waits_for_full_death(self) -> None:
        dummy_death = self.rule(
            lambda rule: validator.event_type(rule) == "Player Died"
            and "Is Dummy Bot(Event Player) == True;" in rule.body
            and "Stop Facing(Event Player);" in rule.body
            and "Stop Throttle In Direction(Event Player);" in rule.body
        )
        mutated = self.replace_in_rule(dummy_death, "\n\t\tIs Alive(Event Player) == False;", "")
        self.assert_rejected(mutated, "arresto dummy morto deve attendere la morte completa")

    def test_try_your_luck_requires_all_timestamp_state(self) -> None:
        mutated = self.source.replace("NextLuckBurnTime", "WaktuBakarLegacy")
        self.assert_rejected(mutated, "NextLuckBurnTime")

    def test_try_your_luck_state_machine_cannot_wait(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerLuck")
        mutated = self.inject_action(machine, "Wait(1, Ignore Condition);")
        self.assert_rejected(mutated, "timestamp, non Wait")

    def test_roulette_icons_capture_scheduler_identity_before_position_reevaluation(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerLuck")
        call = next(iter(validator.iter_calls(machine.body, "Create Icon")))
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        naked_position = call.args[1].replace("Evaluate Once(Global.ActivePlayer)", "Global.ActivePlayer", 1)
        self.assertNotEqual(naked_position, call.args[1])
        mutated = self.replace_call_argument(absolute, 1, naked_position)
        self.assert_rejected(mutated, "scratch Global.ActivePlayer dinamico senza Evaluate Once")

    def test_roulette_icon_position_must_update_every_frame(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerLuck")
        call = next(iter(validator.iter_calls(machine.body, "Create Icon")))
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        dynamic = next(iter(validator.iter_calls(call.args[1], "Update Every Frame")))
        mutated = self.replace_call_argument(absolute, 1, dynamic.args[0])
        self.assert_rejected(mutated, "posizione fluida Update Every Frame")

    def test_roulette_icon_position_tracks_eye_and_facing_direction(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerLuck")
        call = next(iter(validator.iter_calls(machine.body, "Create Icon")))
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        changed_position, count = re.subn(
            r"Facing Direction Of\(\s*Evaluate Once\(Global\.ActivePlayer\)\s*\)",
            "Vector(0, 0, 1)",
            call.args[1],
            count=1,
        )
        self.assertEqual(count, 1)
        mutated = self.replace_call_argument(absolute, 1, changed_position)
        self.assert_rejected(mutated, "ancoraggio fluido a occhio e mirino")

    def test_roulette_icon_cannot_freeze_the_whole_position_expression(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerLuck")
        call = next(iter(validator.iter_calls(machine.body, "Create Icon")))
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        dynamic = next(iter(validator.iter_calls(call.args[1], "Update Every Frame")))
        naked_inner = re.sub(
            r"Evaluate Once\(Global\.ActivePlayer\)",
            "Global.ActivePlayer",
            dynamic.args[0],
        )
        frozen_position = f"Update Every Frame(Evaluate Once({naked_inner}))"
        mutated = self.replace_call_argument(absolute, 1, frozen_position)
        self.assert_rejected(mutated, "catture identità player")

    def test_roulette_icons_are_visible_only_to_humans(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerLuck")
        call = next(iter(validator.iter_calls(machine.body, "Create Icon")))
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        mutated = self.replace_call_argument(absolute, 0, "All Players(All Teams)")
        self.assert_rejected(mutated, "visibilità riservata agli umani")

    def test_roulette_icons_reevaluate_visibility_and_position(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerLuck")
        call = next(iter(validator.iter_calls(machine.body, "Create Icon")))
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        mutated = self.replace_call_argument(absolute, 3, "Position")
        self.assert_rejected(mutated, "reevaluation deve essere Visible To and Position")

    def test_roulette_icons_remain_visible_when_offscreen(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerLuck")
        call = next(iter(validator.iter_calls(machine.body, "Create Icon")))
        self.assertGreaterEqual(len(call.args), 6)
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        mutated = self.replace_call_argument(absolute, 5, "False")
        self.assert_rejected(mutated, "Show When Offscreen deve essere True")

    def test_roulette_icons_cover_each_outcome_once(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerLuck")
        call = next(iter(validator.iter_calls(machine.body, "Create Icon")))
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        mutated = self.replace_call_argument(absolute, 2, "Skull")
        self.assert_rejected(mutated, "icone roulette univoche")

    def test_roulette_icon_types_cannot_be_swapped_between_outcomes(self) -> None:
        self.assertIn("), Eye, Visible To and Position", self.source)
        self.assertIn("), Skull, Visible To and Position", self.source)
        mutated = self.source.replace("), Eye, Visible To and Position", "), IkonSementara, Visible To and Position", 1)
        mutated = mutated.replace("), Skull, Visible To and Position", "), Eye, Visible To and Position", 1)
        mutated = mutated.replace("), IkonSementara, Visible To and Position", "), Skull, Visible To and Position", 1)
        self.assert_rejected(mutated, "ordine tipi icona per esiti roulette 1..6")

    def test_roulette_icon_is_destroyed_before_each_replacement(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerLuck")
        mutated = self.replace_in_rule(machine, "Destroy Icon(Global.ActivePlayer.LuckIcon);", "")
        self.assert_rejected(mutated, "destroy-before-replace icona roulette")

    def test_roulette_icon_handle_is_stored_immediately_after_creation(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerLuck")
        store = "Global.ActivePlayer.LuckIcon = Last Created Entity;"
        mutated = self.replace_in_rule(
            machine,
            store,
            "Global.ActivePlayer.LuckIconEndTime = 0;\n\t\t\t\t" + store,
        )
        self.assert_rejected(mutated, "handle roulette non salvato immediatamente")

    def test_roulette_icon_handle_store_cannot_be_removed(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerLuck")
        mutated = self.replace_in_rule(
            machine,
            "Global.ActivePlayer.LuckIcon = Last Created Entity;",
            "",
        )
        self.assert_rejected(mutated, "salvataggio handle della nuova icona roulette")

    def test_roulette_final_timer_destroys_and_clears_the_icon_handle(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerLuck")
        final_destroy = machine.body.rfind("Destroy Icon(Global.ActivePlayer.LuckIcon);")
        self.assertGreaterEqual(final_destroy, 0)
        changed = machine.body[:final_destroy] + machine.body[final_destroy:].replace(
            "Destroy Icon(Global.ActivePlayer.LuckIcon);", "", 1
        )
        mutated = self.source[:machine.start] + changed + self.source[machine.end:]
        self.assert_rejected(mutated, "cleanup finale icona roulette incompleto: Destroy Icon")

        final_null = machine.body.rfind("Global.ActivePlayer.LuckIcon = Null;")
        self.assertGreaterEqual(final_null, 0)
        changed = machine.body[:final_null] + machine.body[final_null:].replace(
            "Global.ActivePlayer.LuckIcon = Null;", "", 1
        )
        mutated = self.source[:machine.start] + changed + self.source[machine.end:]
        self.assert_rejected(mutated, "cleanup finale icona roulette incompleto: azzeramento handle")

    def test_roulette_rendering_cannot_move_to_an_each_player_rule(self) -> None:
        extra_rule = r'''

rule("999x - Nasib: Renderer pemain tambahan")
{
	event
	{
		Ongoing - Each Player;
		All;
		All;
	}

	actions
	{
		Create Icon(Global.HumanPlayers, Event Player, Eye, Position, Color(Aqua), True);
		Event Player.LuckIcon = Last Created Entity;
	}
}
'''
        self.assert_rejected(self.source + extra_rule, "global-first, senza regole Each Player")

    def test_luck_acceleration_captures_scheduler_identity(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerLuck")
        call = next(iter(validator.iter_calls(machine.body, "Start Accelerating")))
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        naked_direction = call.args[1].replace("Evaluate Once(Global.ActivePlayer)", "Global.ActivePlayer", 1)
        self.assertNotEqual(naked_direction, call.args[1])
        mutated = self.replace_call_argument(absolute, 1, naked_direction)
        self.assert_rejected(mutated, "direzione accelerazione usa scratch Global.ActivePlayer senza Evaluate Once")

    def test_luck_acceleration_cannot_freeze_the_facing_vector(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerLuck")
        call = next(iter(validator.iter_calls(machine.body, "Start Accelerating")))
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        mutated = self.replace_call_argument(
            absolute,
            1,
            "Evaluate Once(Facing Direction Of(Global.ActivePlayer))",
        )
        self.assert_rejected(mutated, "accelerazione automatica 3D nella Facing Direction")

    def test_luck_acceleration_uses_automatic_facing_direction(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerLuck")
        call = next(iter(validator.iter_calls(machine.body, "Start Accelerating")))
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        mutated = self.replace_call_argument(absolute, 1, "Vector(0, 0, 1)")
        self.assert_rejected(mutated, "accelerazione automatica 3D nella Facing Direction")

    def test_luck_acceleration_cannot_depend_on_directional_input(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerLuck")
        call = next(iter(validator.iter_calls(machine.body, "Start Accelerating")))
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        mutated = self.replace_call_argument(absolute, 1, "Throttle Of(Evaluate Once(Global.ActivePlayer))")
        self.assert_rejected(mutated, "dipende da input/impulsi: Throttle Of(")

    def test_luck_acceleration_requires_world_space_and_dynamic_direction(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerLuck")
        call = next(iter(validator.iter_calls(machine.body, "Start Accelerating")))
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        mutated = self.replace_call_argument(absolute, 4, "To Player")
        self.assert_rejected(mutated, "accelerazione automatica 3D nella Facing Direction")
        mutated = self.replace_call_argument(absolute, 5, "None")
        self.assert_rejected(mutated, "accelerazione automatica 3D nella Facing Direction")

    def test_luck_acceleration_cannot_use_apply_impulse(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerLuck")
        mutated = self.inject_action(
            machine,
            "Apply Impulse(Global.ActivePlayer, Facing Direction Of(Global.ActivePlayer), 1, To World, Cancel Contrary Motion);",
        )
        self.assert_rejected(mutated, "non deve simulare l'accelerazione con Apply Impulse")

    def test_luck_acceleration_is_globally_unique(self) -> None:
        quick = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerFastState")
        mutated = self.inject_action(
            quick,
            "Start Accelerating(Global.ActivePlayer, Facing Direction Of(Evaluate Once(Global.ActivePlayer)), 50, 25, To World, Direction Rate and Max Speed);",
        )
        self.assert_rejected(mutated, "Start Accelerating globale riservato a Try Your Luck")

    def test_luck_acceleration_must_remain_automatic_while_fly_is_active(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerLuck")
        start_call = "Start Accelerating(Global.ActivePlayer, Facing Direction Of(Evaluate Once(Global.ActivePlayer)), 50, 25, To World, Direction Rate and Max Speed);"
        mutated = self.replace_in_rule(
            machine,
            start_call,
            "If(Global.ActivePlayer.FlyModeActive == False);\n\t\t\t\t\t\t"
            + start_call
            + "\n\t\t\t\t\tEnd;",
        )
        self.assert_rejected(mutated, "restare automatica anche in Fly")

    def test_fly_idle_brake_must_skip_active_luck_acceleration(self) -> None:
        cycle = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerFlight")
        mutated = self.replace_in_rule(
            cycle,
            "Global.ActivePlayer.FlyRampStartTime = -1;",
            "Global.ActivePlayer.FlyRampStartTime = -1;\n"
            "\t\t\t\tApply Impulse(Global.ActivePlayer, Global.ActivePlayer.FlyVelocityDelta, Magnitude Of(Global.ActivePlayer.FlyVelocityDelta), To World, Incorporate Contrary Motion);",
        )
        self.assert_rejected(mutated, "esito Acceleration ancora attivo")

    def test_luck_acceleration_call_cannot_be_shadowed_by_a_comment(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerLuck")
        call = next(iter(validator.iter_calls(machine.body, "Start Accelerating")))
        start = machine.start + call.start
        end = machine.start + call.end
        self.assertEqual(self.source[end], ";")
        mutated = self.source[:start] + '"Start Accelerating(Global.ActivePlayer, ...)"' + self.source[end + 1:]
        self.assert_rejected(mutated, "Start Accelerating globale riservato a Try Your Luck")

    def test_luck_acceleration_has_its_own_ten_second_timestamp(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerLuck")
        mutated = self.replace_in_rule(
            machine,
            "Global.ActivePlayer.LuckEffectEndTime = Total Time Elapsed + 10;",
            "Global.ActivePlayer.LuckEffectEndTime = Total Time Elapsed + 9;",
        )
        self.assert_rejected(mutated, "timestamp esatto di 10 secondi")

    def test_luck_expiry_condition_cannot_be_shadowed_by_a_comment(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerLuck")
        condition = "Total Time Elapsed >= Global.ActivePlayer.LuckEffectEndTime"
        self.assertIn(condition, machine.body)
        changed = machine.body.replace(condition, "False", 1)
        closing = changed.rfind("\n\t}")
        self.assertGreater(closing, 0)
        changed = changed[:closing] + f'\n\t\t"{condition}"' + changed[closing:]
        mutated = self.source[:machine.start] + changed + self.source[machine.end:]
        self.assert_rejected(mutated, "cleanup timestamp Try Your Luck non analizzabile")

    def test_luck_acceleration_expiry_restores_speed_and_stops_acceleration(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerLuck")
        mutated = self.replace_in_rule(machine, "Stop Accelerating(Global.ActivePlayer);", "")
        self.assert_rejected(mutated, "cleanup scadenza accelerazione incompleto: Stop Accelerating")
        mutated = self.replace_in_rule(machine, "Set Move Speed(Global.ActivePlayer, 100);", "")
        self.assert_rejected(mutated, "cleanup scadenza accelerazione incompleto: ripristino Move Speed 100")

    def test_luck_acceleration_stop_cannot_be_shadowed_by_a_comment(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerLuck")
        mutated = self.replace_in_rule(
            machine,
            "Stop Accelerating(Global.ActivePlayer);",
            '"Stop Accelerating(Global.ActivePlayer);"',
        )
        self.assert_rejected(mutated, "cleanup scadenza accelerazione incompleto: Stop Accelerating")

    def test_luck_acceleration_is_stopped_on_death(self) -> None:
        death_cleanup = self.rule(lambda rule: validator.subroutine_target(rule) == "RestorePlayerLuck")
        mutated = self.replace_in_rule(death_cleanup, "Stop Accelerating(Event Player);", "")
        self.assert_rejected(mutated, "cleanup accelerazione morte: Stop Accelerating assente")

    def test_player_death_normalizes_ghost_fly_engine_state_before_rearming(self) -> None:
        death = self.rule(
            lambda rule: validator.event_type(rule) == "Player Died"
            and "Event Player.DeathPosition = Position Of(Event Player);" in rule.body
        )
        for action in (
            "Stop Transforming Throttle(Event Player);",
            "Set Gravity(Event Player, 100);",
            "Enable Movement Collision With Environment(Event Player);",
        ):
            with self.subTest(action=action):
                mutated = self.replace_in_rule(death, action, "")
                self.assert_rejected(mutated, "morte deve normalizzare")

    def test_death_prompt_describes_automatic_void_recovery(self) -> None:
        death = self.rule(
            lambda rule: validator.event_type(rule) == "Player Died"
            and "Event Player.DeathPosition = Position Of(Event Player);" in rule.body
        )
        mutated = self.replace_in_rule(
            death,
            'Press {0}: revive here. Void death? Back to walkable ground.',
            "Press {0}: resurrect here, or move to walkable ground after a void death.",
        )
        self.assert_rejected(mutated, "prompt morte non descrive il recupero automatico dal vuoto: EN")

    def test_roulette_icon_is_destroyed_and_cleared_on_all_lifecycle_paths(self) -> None:
        reset = self.rule(lambda rule: validator.subroutine_target(rule) == "RestorePlayerLuck")
        mutated = self.replace_in_rule(reset, "Destroy Icon(Event Player.LuckIcon);", "")
        self.assert_rejected(mutated, "cleanup icona roulette morte: Destroy Icon assente")
        mutated = self.replace_in_rule(reset, "Event Player.LuckIcon = Null;", "")
        self.assert_rejected(mutated, "cleanup icona roulette morte: azzeramento handle assente")

    def test_heart_heal_targets_the_owner_team_at_max_value(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerLuck")
        call = next(
            call for call in validator.iter_calls(machine.body, "Set Player Health")
            if len(call.args) >= 2 and "All Living Players(Team Of(Global.ActivePlayer))" in call.args[0]
        )
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        mutated = self.replace_call_argument(
            absolute,
            0,
            "All Living Players(Opposite Team Of(Team Of(Global.ActivePlayer)))",
        )
        self.assert_rejected(mutated, "tutta la squadra del proprietario")

        mutated = self.replace_call_argument(absolute, 1, "Max Health(Global.ActivePlayer)")
        self.assert_rejected(mutated, "tutta la squadra del proprietario")

    def test_heart_message_is_exclusive_to_the_roulette_owner(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerLuck")
        call = next(
            call for call in validator.iter_calls(machine.body, "Small Message")
            if len(call.args) >= 2 and "HEART" in call.args[1]
        )
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        mutated = self.replace_call_argument(absolute, 0, "All Living Players(Team Of(Global.ActivePlayer))")
        self.assert_rejected(mutated, "notificare soltanto il proprietario")

    def test_global_lifecycle_dispatch_requires_duplicate_guard(self) -> None:
        fast = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerFastState")
        mutated = self.replace_in_rule(
            fast,
            "Global.ActivePlayer.TeamChangeProcessed == False",
            "Global.ActivePlayer.TeamChangeProcessed == True",
        )
        self.assert_rejected(mutated, "dispatcher team-switch cleanup incompleto")

    def test_global_lifecycle_dispatch_excludes_classified_ibots(self) -> None:
        fast = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerFastState")
        mutated = self.replace_in_rule(
            fast,
            "Global.ActivePlayer.IsAutomaticBot == False",
            "Global.ActivePlayer.IsAutomaticBot == True",
        )
        self.assert_rejected(mutated, "dispatcher team-switch deve escludere gli iBot")

    def test_roster_repair_is_blocked_during_team_switch_quarantine(self) -> None:
        fast = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerFastState")
        mutated = self.replace_in_rule(
            fast,
            "Global.ActivePlayer.PlayerCycleActive == False",
            "Global.ActivePlayer.PlayerCycleActive == True",
        )
        self.assert_rejected(mutated, "team-switch è in quarantena")

    def test_team_switch_detector_requires_quarantine_and_defers_heavy_cleanup(self) -> None:
        worker = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
                           and "Event Player.LastTeam != Team Of(Event Player)" in rule.body)
        for token in (
            "Event Player.TeamChangeProcessed = True;",
            "Event Player.PlayerCycleActive = True;",
            "Event Player.IsPrepared = False;",
            "Event Player.IsHuman = False;",
            "Event Player.TeamCycleDeadline = Total Time Elapsed + 0.500;",
        ):
            with self.subTest(token=token):
                mutated = self.replace_in_rule(worker, token, "")
                self.assert_rejected(mutated, "detector team-switch cleanup incompleto")
        for token in ("Call Subroutine(QuiescePlayer);", "Call Subroutine(CleanupPlayer);"):
            with self.subTest(token=token):
                mutated = self.inject_action(worker, token)
                self.assert_rejected(mutated, "transizione nativa")

    def test_team_switch_quiescence_precedes_team_commit_and_deadline(self) -> None:
        detector = self.rule(lambda rule: rule.name.startswith("01a -"))
        quiescence = (
            "Global.SuperPunchPlayers = Remove From Array(Global.SuperPunchPlayers, Event Player);\n"
            "\t\tIf(Entity Exists(Event Player) == True);\n"
            "\t\t\tStop Chasing Player Variable(Event Player, ObjectiveIconPosition);\n"
            "\t\tEnd;"
        )
        self.assertIn(quiescence, detector.body)
        deadline = "Event Player.TeamCycleDeadline = Total Time Elapsed + 0.500;"
        changed = detector.body.replace(quiescence, "", 1).replace(deadline, deadline + "\n\t\t" + quiescence, 1)
        mutated = self.source[:detector.start] + changed + self.source[detector.end:]
        self.assert_rejected(mutated, "prima del commit/scadenza")

    def test_team_switch_stops_only_its_local_icon_chase(self) -> None:
        detector = self.rule(lambda rule: rule.name.startswith("01a -"))
        stop = "Stop Chasing Player Variable(Event Player, ObjectiveIconPosition);"
        for replacement in (
            "Stop Chasing Player Variable(All Players(All Teams), ObjectiveIconPosition);",
            "Stop Chasing Player Variable(Event Player, MenuColor);",
            stop + "\n\t\t\t" + stop,
            "",
        ):
            with self.subTest(replacement=replacement):
                self.assert_rejected(self.replace_in_rule(detector, stop, replacement),
                                     "unica chase fermata deve essere ObjectiveIconPosition del proprio Event Player")

    def test_team_switch_icon_stop_requires_only_local_entity_guard(self) -> None:
        detector = self.rule(lambda rule: rule.name.startswith("01a -"))
        guard = "If(Entity Exists(Event Player) == True);"
        for replacement in ("If(True);", "If(Entity Exists(Event Player) == False);",
                            "If(Entity Exists(All Players(All Teams)) == True);"):
            with self.subTest(replacement=replacement):
                self.assert_rejected(self.replace_in_rule(detector, guard, replacement),
                                     "Stop chase richiede la guardia Entity Exists locale")

    def test_team_switch_keeps_full_cleanup_and_icon_reset_deferred(self) -> None:
        detector = self.rule(lambda rule: rule.name.startswith("01a -"))
        for action in ("Destroy Icon(Global.ObjectiveIconIds[Event Player.HudSlot]);",
                       "Call Subroutine(CleanupObjectiveIcon);",
                       "Set Player Variable(Event Player, ObjectiveIconPosition, Vector(0, 0.500, 0));"):
            with self.subTest(action=action):
                self.assert_rejected(self.inject_action(detector, action), "unica azione engine consentita")
        self.assert_rejected(self.inject_action(detector, "Event Player.ObjectiveIconPosition = Vector(0, 0.500, 0);"),
                             "non deve resettare ObjectiveIconPosition")
        self.assert_rejected(self.inject_action(detector, "Global.ObjectiveIconIndex = 0;"),
                             "nessuna nuova assegnazione scratch")

    def test_team_switch_removes_only_its_punch_identity_unconditionally(self) -> None:
        detector = self.rule(lambda rule: rule.name.startswith("01a -"))
        removal = "Global.SuperPunchPlayers = Remove From Array(Global.SuperPunchPlayers, Event Player);"
        self.assert_rejected(self.replace_in_rule(detector, removal, ""),
                             "rimozione registro Punch deve essere unica e incondizionata")
        self.assert_rejected(self.replace_in_rule(detector, removal, "If(False); " + removal + " End;"),
                             "rimozione registro Punch deve essere unica e incondizionata")
        self.assert_rejected(self.replace_in_rule(detector, removal, removal.replace("Event Player", "All Players(All Teams)")),
                             "assegnazione registro fuori inizializzazione OFF o cleanup locale")
        classifier = self.rule(lambda rule: "Append To Array(Global.HumanPlayers, Event Player)" in rule.body)
        self.assert_rejected(self.inject_action(classifier, removal),
                             "assegnazione registro fuori inizializzazione OFF o cleanup locale")

    def test_old_global_team_cleanup_is_rejected_by_transitive_context_gate(self) -> None:
        fast = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerFastState")
        mutated = self.inject_action(fast, "Call Subroutine(QuiescePlayer);")
        self.assert_rejected(mutated, "contesto Event Player non disponibile da Ongoing - Global")

    def test_team_switch_worker_requires_owner_and_registered_identity_guards(self) -> None:
        worker = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
                           and "Event Player.LastTeam != Team Of(Event Player)" in rule.body)
        for token in ("Is Dummy Bot(Event Player) == False;",
                      "Event Player.IsAutomaticBot == False;",
                      "Array Contains(Global.HumanPlayers, Event Player) == True;"):
            with self.subTest(token=token):
                self.assert_rejected(self.replace_in_rule(worker, token, ""),
                                     "detector team-switch senza guardia")

    def test_team_reset_restores_engine_before_discarding_runtime_latches(self) -> None:
        quiet = self.rule(lambda rule: validator.subroutine_target(rule) == "QuiescePlayer")
        for token in ("Stop Camera(Event Player);",
                      "Stop Modifying Hero Voice Lines(Event Player);",
                      "Stop Chasing Player Variable(Event Player, MenuColor);",
                      "Detach Players(Event Player);",
                      "Enable Nameplates(All Players(All Teams), Event Player);",
                      "Allow Button(Event Player, Button(Melee));",
                      "Call Subroutine(RestorePlayerLuck);"):
            with self.subTest(token=token):
                self.assert_rejected(self.replace_in_rule(quiet, token, ""), "reset engine completo")
        token = "Call Subroutine(CloseMenu);"
        mutated = self.replace_in_rule(quiet, token, f"If(Event Player.MenuOpen == True); {token} End;")
        self.assert_rejected(mutated, "reset engine completo deve essere incondizionato")

    def test_slot_cleanup_cannot_recycle_twice_or_discard_undestroyed_handles(self) -> None:
        cleanup = self.rule(lambda rule: validator.subroutine_target(rule) == "CleanupPlayer")
        mutated = self.replace_in_rule(cleanup, "If(Global.LeavingPlayerIndex >= 0);", "If(True);")
        self.assert_rejected(mutated, "riciclo slot deve essere idempotente")
        for array, action in (("PlayerListHudIds", "Destroy HUD Text"),
                              ("MenuHudIds", "Destroy HUD Text"),
                              ("InspectionTextIds", "Destroy In-World Text")):
            with self.subTest(array=array):
                token = f"{action}(Global.{array}[Global.CleanupPlayerIndex]);"
                self.assert_rejected(self.replace_in_rule(cleanup, token, ""), "distruzione handle prima del riciclo")

    def test_pending_lifecycle_rejects_stale_team_target_and_early_reservation(self) -> None:
        fast = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerFastState")
        mutated = self.replace_in_rule(fast, "Global.ActivePlayer.TeamCycleTargetTeam != Team Of(Global.ActivePlayer)", "False")
        self.assert_rejected(mutated, "secondo cambio squadra")
        mutated = self.replace_in_rule(fast, "Total Time Elapsed >= Global.ActivePlayer.TeamCycleDeadline", "True")
        self.assert_rejected(mutated, "entrambe le scadenze")
        scheduler = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Global"
                              and "Call Subroutine(ProcessPlayerFastState);" in rule.body)
        mutated = self.replace_in_rule(scheduler, "Has Spawned(Global.TeamCyclePlayer) == False", "False")
        self.assert_rejected(mutated, "player non spawned")

    def test_scheduler_iterates_players_from_a_snapshot(self) -> None:
        scheduler = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Global"
                              and "Call Subroutine(ProcessPlayerFastState);" in rule.body)
        mutated = self.replace_in_rule(
            scheduler,
            "Global.PlayerListSnapshot = All Players(All Teams);",
            "",
        )
        self.assert_rejected(mutated, "snapshot roster")
        mutated = self.replace_in_rule(
            scheduler,
            "Global.ActivePlayer = Global.PlayerListSnapshot[Global.SchedulerPlayerIndex];",
            "Global.ActivePlayer = All Players(All Teams)[Global.SchedulerPlayerIndex];",
        )
        self.assert_rejected(mutated, "non deve iterare direttamente")

    def test_menu_canonical_handle_must_be_destroyed_before_its_reference_is_lost(self) -> None:
        close_menu = self.rule(lambda rule: validator.subroutine_target(rule) == "CloseMenu")
        canonical = "Global.MenuHudIds[Index Of Array Value(Global.HumanPlayers, Event Player)]"
        mutated = self.replace_in_rule(close_menu, f"Destroy HUD Text({canonical});", "")
        self.assert_rejected(mutated, "chiusura menu deve distruggere prima il canonico")

    def test_team_switch_detector_disallows_abort_paths(self) -> None:
        worker = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
                           and "Event Player.LastTeam != Team Of(Event Player)" in rule.body)
        mutated = self.inject_action(worker, "Abort;")
        self.assert_rejected(mutated, "detector non deve usare Abort")

    def test_team_switch_detector_rejects_pending_roster_model(self) -> None:
        worker = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
                           and "Event Player.LastTeam != Team Of(Event Player)" in rule.body)
        mutated = self.replace_in_rule(
            worker,
            "Event Player.PlayerListUpdatePending = False;",
            "Event Player.PlayerListUpdatePending = True;",
        )
        self.assert_rejected(mutated, "pending roster ringan")

    def test_roster_ready_flag_is_written_after_the_registered_vibes_handle(self) -> None:
        roster = self.rule(
            lambda rule: "Event Player.PlayerListHud = Last Text ID;" in rule.body
        )
        ready = "\t\tEvent Player.PlayerHudCreated = True;\n"
        self.assertIn(ready, roster.body)
        changed = roster.body.replace(ready, "", 1)
        actions = changed.index("\tactions\n\t{\n") + len("\tactions\n\t{\n")
        changed = changed[:actions] + ready + changed[actions:]
        mutated = self.source[:roster.start] + changed + self.source[roster.end:]
        self.assert_rejected(mutated, "dopo la registrazione del singolo handle")

        conditions = validator.rule_block(roster, "conditions") or ""
        self.assertNotIn("Is Alive(Event Player) == True;", conditions)
        mutated = self.replace_in_rule(
            roster,
            "Has Spawned(Event Player) == True;",
            "Has Spawned(Event Player) == True;\n\t\tIs Alive(Event Player) == True;",
        )
        self.assert_rejected(mutated, "non deve attendere Is Alive")

    def test_classifier_and_roster_renderer_must_stay_in_the_same_rule(self) -> None:
        classifier = self.rule(
            lambda rule: "Append To Array(Global.HumanPlayers, Event Player)" in rule.body
            and "Create HUD Text(" in rule.body
            and "Event Player.PlayerListHud = Last Text ID;" in rule.body
            and "Event Player.PlayerHudCreated = True;" in rule.body
        )
        duplicate = re.sub(
            r'(regola|rule)\("([^"]+)"\)',
            r'\1("02c - DEBUG split renderer")',
            classifier.body,
            count=1,
        )
        self.assertNotEqual(duplicate, classifier.body)
        mutated = self.source + "\n\n" + duplicate
        self.assert_rejected(
            mutated,
            "classifier e renderer roster devono restare nella stessa regola",
        )

    def test_classifier_rearms_when_a_roster_slot_is_temporarily_unavailable(self) -> None:
        classifier = self.rule(
            lambda rule: "Append To Array(Global.HumanPlayers, Event Player)" in rule.body
        )
        start = classifier.body.index("If(Count Of(Global.AvailableHudSlots) == 0);")
        end = classifier.body.index("Abort;", start) + len("Abort;")
        retry = classifier.body[start:end]
        mutated = self.replace_in_rule(classifier, retry, retry.replace(
            "Global.TeamCyclePlayer = Null;", "Global.TeamCyclePlayer = Event Player;"))
        self.assert_rejected(mutated, "liberare lifecycle/lock")

    def test_public_crouch_filters_exclude_pending_team_switch_targets(self) -> None:
        protected_rules = (
            self.rule(lambda rule: validator.subroutine_target(rule) == "RefreshPlayerPublicTargets"),
            self.rule(lambda rule: validator.subroutine_target(rule) == "RefreshActivePlayerPublicTargets"),
        )
        for rule in protected_rules:
            with self.subTest(rule=rule.name):
                mutated = self.replace_in_rule(
                    rule,
                    "Player Variable(Current Array Element, PlayerListUpdatePending) == False",
                    "True",
                )
                self.assert_rejected(mutated, "deve escludere il pending team-switch")

    def test_team_switch_cleanup_branch_requires_requeue_reset(self) -> None:
        worker = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
                           and "Event Player.LastTeam != Team Of(Event Player)" in rule.body)
        mutated = self.replace_in_rule(
            worker,
            "Event Player.TeamChangeProcessed = True;",
            "",
        )
        self.assert_rejected(mutated, "detector team-switch cleanup incompleto")

    def test_setup_worker_performs_cleanup_only_after_stability_gate(self) -> None:
        setup_worker = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Call Subroutine(PreparePlayer);" in rule.body
            and "Event Player.TeamCycleDeadline" in rule.body
        )
        mutated = self.replace_in_rule(setup_worker, "Call Subroutine(CleanupPlayer);", "")
        self.assert_rejected(mutated, "cleanup solo dopo stabilizzazione")

    def test_setup_worker_waits_require_exact_duration_and_abort_policy(self) -> None:
        worker = self.rule(lambda rule: rule.name.startswith("01b -"))
        wait = "Wait(0.050, Abort When False);"
        for replacement in ("Wait(0.100, Abort When False);", "Wait(0.050, Ignore Condition);"):
            with self.subTest(replacement=replacement):
                self.assert_rejected(self.replace_in_rule(worker, wait, replacement),
                                     "soltanto due Wait 0.050 Abort When False")
        self.assert_rejected(self.inject_action(worker, wait), "soltanto due Wait 0.050 Abort When False")
        self.assert_rejected(self.replace_in_rule(worker, wait, ""), "soltanto due Wait 0.050 Abort When False")

    def test_setup_worker_waits_must_separate_all_three_atomic_stages(self) -> None:
        worker = self.rule(lambda rule: rule.name.startswith("01b -"))
        before_wait = "Call Subroutine(QuiescePlayer);\n\t\tWait(0.050, Abort When False);"
        self.assert_rejected(self.replace_in_rule(worker, before_wait,
                             "Wait(0.050, Abort When False);\n\t\tCall Subroutine(QuiescePlayer);"),
                             "Wait/guardie complete")
        first = "Call Subroutine(QuiescePlayer);"
        last = "Call Subroutine(PreparePlayer);"
        changed = worker.body.replace(first, "__FIRST_STAGE__", 1).replace(last, first, 1).replace("__FIRST_STAGE__", last, 1)
        self.assert_rejected(self.source[:worker.start] + changed + self.source[worker.end:], "Wait/guardie complete")
        branch = "If(Array Contains(Global.HumanPlayers, Event Player));"
        changed = worker.body.replace("Wait(0.050, Abort When False);", "", 1)
        changed = changed.replace(branch, branch + "\n\t\t\tWait(0.050, Abort When False);", 1)
        self.assert_rejected(self.source[:worker.start] + changed + self.source[worker.end:],
                             "i Wait devono separare le fasi anche al join iniziale")

    def test_setup_worker_rechecks_every_guard_after_each_wait(self) -> None:
        worker = self.rule(lambda rule: rule.name.startswith("01b -"))
        for guard in (
            "Abort If(Global.IsReady == False);",
            "Abort If(Entity Exists(Event Player) == False);",
            "Abort If(Is Dummy Bot(Event Player) == True);",
            "Abort If(Event Player.IsAutomaticBot == True);",
            "Abort If(Event Player.IsHuman == True);",
            "Abort If(Event Player.TeamChangeProcessed == False);",
            "Abort If(Global.TeamCyclePlayer != Event Player);",
            "Abort If(Event Player.TeamCycleTargetTeam != Team Of(Event Player));",
            "Abort If(Has Spawned(Event Player) == False);",
            "Abort If(Event Player.IsPrepared == True);",
            "Abort If(Total Time Elapsed < Event Player.TeamCycleDeadline);",
        ):
            occurrences = [match.start() for match in re.finditer(re.escape(guard), worker.body)]
            self.assertEqual(len(occurrences), 2)
            for stage, position in enumerate(occurrences):
                with self.subTest(guard=guard, stage=stage):
                    changed = worker.body[:position] + worker.body[position + len(guard):]
                    self.assert_rejected(self.source[:worker.start] + changed + self.source[worker.end:],
                                         "Wait/guardie complete")

    def test_setup_worker_requires_existing_entity_and_quarantined_human_conditions(self) -> None:
        worker = self.rule(lambda rule: rule.name.startswith("01b -"))
        for guard in ("Entity Exists(Event Player) == True;", "Global.IsReady == True;", "Event Player.IsHuman == False;"):
            with self.subTest(guard=guard):
                self.assert_rejected(self.replace_in_rule(worker, guard, ""), "worker setup iniziale senza guardia")

    def test_setup_worker_yields_cannot_move_into_shared_cleanup_or_scheduler(self) -> None:
        rules = [self.rule(lambda rule: validator.subroutine_target(rule) == name)
                 for name in ("QuiescePlayer", "CleanupPlayer", "PreparePlayer")]
        rules.append(self.rule(lambda rule: validator.action_loop_count(rule.body) == 1))
        for rule in rules:
            with self.subTest(rule=rule.name):
                self.assert_rejected(self.inject_action(rule, "Wait(0.050, Abort When False);"),
                                     "Wait nominativamente consentiti")

    def test_travel_inputs_require_live_human_outside_team_quarantine(self) -> None:
        for prefix in ("19", "19a", "19c", "19e"):
            handler = self.rule(lambda rule: rule.name.startswith(prefix + " -"))
            for guard in ("Event Player.IsHuman == True;", "Event Player.TeamChangeProcessed == False;",
                          "Event Player.PlayerCycleActive == False;"):
                with self.subTest(handler=prefix, guard=guard):
                    self.assert_rejected(self.replace_in_rule(handler, guard, ""), "escludere owner in quarantena")

    def test_menu_and_travel_cleanup_controllers_exclude_quarantined_owners(self) -> None:
        for prefix in ("05f", "19f", "19g", "19h", "18j"):
            handler = self.rule(lambda rule: rule.name.startswith(prefix + " -"))
            guards = ("Event Player.TeamChangeProcessed == False;", "Event Player.PlayerCycleActive == False;")
            if prefix != "18j":
                guards += ("Event Player.IsHuman == True;",)
            for guard in guards:
                with self.subTest(handler=prefix, guard=guard):
                    self.assert_rejected(self.replace_in_rule(handler, guard, ""), "escludere owner in quarantena")
        vision = self.rule(lambda rule: rule.name.startswith("18j -"))
        self.assert_rejected(self.inject_condition(vision, "Event Player.IsHuman == True;"),
                             "cleanup Vision 18j deve conservare anche gli owner bot")

    def test_setup_worker_keeps_native_hud_toggles_inside_siapkan_only(self) -> None:
        setup_worker = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Call Subroutine(PreparePlayer);" in rule.body
            and "Event Player.TeamCycleDeadline" in rule.body
        )
        self.assertNotIn("Disable Game Mode HUD(Event Player);", setup_worker.body)
        self.assertNotIn("Disable Game Mode In-World UI(Event Player);", setup_worker.body)
        mutated = self.inject_action(setup_worker, "Disable Game Mode HUD(Event Player);")
        self.assert_rejected(mutated, "non deve toccare HUD nativo")
        mutated = self.inject_action(setup_worker, "Disable Game Mode In-World UI(Event Player);")
        self.assert_rejected(mutated, "non deve toccare objective marker")

    def test_classifier_preserves_cached_name_on_team_switch_rejoin(self) -> None:
        classifier = self.rule(
            lambda rule: "Append To Array(Global.HumanPlayers, Event Player)" in rule.body
        )
        guard = "If(Or(Event Player.WasPrepared == False, Or(Event Player.DisplayName == Null, Event Player.DisplayName == Custom String(\"\"))));"
        mutated = self.replace_in_rule(classifier, guard, "")
        self.assert_rejected(mutated, "proteggere DisplayName cache")
        mutated = self.replace_in_rule(
            classifier,
            "Event Player.DisplayName = Evaluate Once(Custom String(\"{0}\", Event Player));",
            "",
        )
        self.assert_rejected(mutated, "acquisire DisplayName su join iniziale")

    def test_pending_roster_refresh_starts_false_in_fresh_setup(self) -> None:
        setup = self.rule(lambda rule: validator.subroutine_target(rule) == "PreparePlayer")
        mutated = self.replace_in_rule(
            setup,
            "Event Player.PlayerListUpdatePending = False;",
            "Event Player.PlayerListUpdatePending = Null;",
        )
        self.assert_rejected(mutated, "reset setup iniziale mancante")

    def test_leave_cleanup_is_limited_to_the_human_roster(self) -> None:
        left = self.rule(lambda rule: validator.event_type(rule) == "Player Left Match")
        mutated = self.replace_in_rule(
            left,
            "Or(Event Player.IsHuman == True, Array Contains(Global.HumanPlayers, Event Player))",
            "Event Player.IsHuman == False",
        )
        self.assert_rejected(mutated, "Player Left Match deve includere iBot e umani registrati")

    def test_player_left_match_includes_classified_ibots(self) -> None:
        left = self.rule(lambda rule: validator.event_type(rule) == "Player Left Match")
        mutated = self.replace_in_rule(
            left,
            "Or(Event Player.IsAutomaticBot == True, "
            "Or(Event Player.IsHuman == True, Array Contains(Global.HumanPlayers, Event Player))) == True;",
            "Or(Event Player.IsHuman == True, Array Contains(Global.HumanPlayers, Event Player)) == True;",
        )
        self.assert_rejected(mutated, "Player Left Match deve includere iBot e umani registrati")

    def test_ibot_leave_destroys_vision_text_before_human_lifecycle(self) -> None:
        left = self.rule(lambda rule: validator.event_type(rule) == "Player Left Match")
        mutated = self.replace_in_rule(
            left,
            "Destroy In-World Text(Event Player.LuckVisionText);",
            "",
        )
        self.assert_rejected(mutated, "leave iBot deve distruggere LuckVisionText")

    def test_ibot_leave_clears_vision_handle_before_human_lifecycle(self) -> None:
        left = self.rule(lambda rule: validator.event_type(rule) == "Player Left Match")
        mutated = self.replace_in_rule(
            left,
            "\n\t\t\tEvent Player.LuckVisionText = Null;",
            "",
        )
        self.assert_rejected(mutated, "leave iBot deve distruggere LuckVisionText")

    def test_ibot_leave_aborts_before_human_lifecycle(self) -> None:
        left = self.rule(lambda rule: validator.event_type(rule) == "Player Left Match")
        mutated = self.replace_in_rule(left, "\n\t\t\tAbort;", "")
        self.assert_rejected(mutated, "leave iBot deve distruggere LuckVisionText")

    def test_roster_append_is_idempotent(self) -> None:
        classifier = self.rule(lambda rule: "Append To Array(Global.HumanPlayers, Event Player)" in rule.body)
        mutated = self.replace_in_rule(classifier, "Abort If(Array Contains(Global.HumanPlayers, Event Player));", "")
        self.assert_rejected(mutated, "due volte il roster")

    def test_ibot_aborts_before_human_roster_append(self) -> None:
        classifier = self.rule(lambda rule: "Append To Array(Global.HumanPlayers, Event Player)" in rule.body)
        mutated = self.replace_in_rule(
            classifier,
            "Call Subroutine(LockBot);\n\t\t\tAbort;",
            "Call Subroutine(LockBot);",
        )
        self.assert_rejected(mutated, "iBot può raggiungere il roster umano")

    def test_human_menu_dispatcher_has_all_bot_guards(self) -> None:
        dispatcher = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "MenuCommand" in rule.body
            and "Button(Ability 2)" in rule.body
        )
        mutated = self.replace_in_rule(
            dispatcher,
            "Event Player.IsHuman == True;",
            "Event Player.IsHuman == False;",
        )
        self.assert_rejected(mutated, "dispatcher menu non isola bot/dummy")

    def test_only_classifier_can_mark_a_player_as_human(self) -> None:
        camera = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Button(Interact)" in rule.body
            and "Wait(0.500, Abort When False)" in rule.body
            and "CameraMode" in rule.body
        )
        mutated = self.inject_action(camera, "Event Player.IsHuman = True;")
        self.assert_rejected(mutated, "numero writer di IsHuman=True")

    def test_anran_passive_has_all_bot_guards(self) -> None:
        anran = self.rule(lambda rule: validator.event_type(rule) == "Player Died" and "Hero(Anran)" in rule.body)
        mutated = self.replace_in_rule(anran, "Is Dummy Bot(Event Player) == False;", "Is Dummy Bot(Event Player) == True;")
        self.assert_rejected(mutated, "passiva Anran non isola bot/dummy")

    def test_dedicated_bot_rule_is_required(self) -> None:
        bot_rule = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Or(Is Dummy Bot(Event Player), Event Player.IsAutomaticBot) == True;" in rule.body
            and "Call Subroutine(LockBot);" in rule.body
        )
        mutated = self.replace_in_rule(bot_rule, "Call Subroutine(LockBot);", "")
        self.assert_rejected(mutated, "regola dedicata di lock bot/dummy assente")

    def test_native_dummy_rejects_all_collision_overrides(self) -> None:
        bot_rule = self.rule(lambda rule: rule.name.startswith("03c - "))
        for action in (
            "Enable Movement Collision With Environment(Event Player);",
            "Disable Movement Collision With Environment(Event Player, False);",
            "Enable Movement Collision With Players(Event Player);",
            "Disable Movement Collision With Players(Event Player);",
        ):
            with self.subTest(action=action):
                self.assert_rejected(self.inject_action(bot_rule, action),
                                     "bot/dummy: conservare le collisioni native senza riapplicarle")

    def test_native_dummy_setup_does_not_apply_to_ibots(self) -> None:
        bot_rule = self.rule(lambda rule: rule.name.startswith("03c - "))
        mutated = self.replace_in_rule(bot_rule, "If(Is Dummy Bot(Event Player) == True);",
                                       "If(Event Player.IsAutomaticBot == True);")
        self.assert_rejected(mutated, "bot/dummy: sequenza raggiungibile e isolata")

    def test_native_dummy_setup_branch_cannot_be_made_unreachable(self) -> None:
        bot_rule = self.rule(lambda rule: rule.name.startswith("03c - "))
        mutated = self.replace_in_rule(bot_rule, "Call Subroutine(LockBot);",
                                       "Call Subroutine(LockBot); Abort;")
        self.assert_rejected(mutated, "bot/dummy: sequenza raggiungibile e isolata")

    def test_native_dummy_setup_rule_cannot_have_an_impossible_condition(self) -> None:
        bot_rule = self.rule(lambda rule: rule.name.startswith("03c - "))
        mutated = self.inject_condition(bot_rule, "False == True;")
        self.assert_rejected(mutated, "bot/dummy: condizioni esatte e raggiungibili")

    def test_bot_lock_neutralizes_player_interference(self) -> None:
        bot_lock = self.rule(lambda rule: validator.subroutine_target(rule) == "LockBot")
        mutated = self.replace_in_rule(bot_lock, "Set Damage Dealt(Event Player, 0);", "")
        self.assert_rejected(mutated, "LockBot incompleto")

    def test_bot_lock_receives_normal_damage_and_knockback(self) -> None:
        bot_lock = self.rule(lambda rule: validator.subroutine_target(rule) == "LockBot")
        expected_messages = {
            "Damage": "danni ricevuti normali",
            "Knockback": "urti ricevuti normali",
        }
        for action, expected_message in expected_messages.items():
            with self.subTest(action=action):
                mutated = self.replace_in_rule(
                    bot_lock,
                    f"Set {action} Received(Event Player, 100);",
                    f"Set {action} Received(Event Player, 0);",
                )
                self.assert_rejected(mutated, expected_message)

    def test_bot_lock_must_not_modify_native_collisions(self) -> None:
        bot_lock = self.rule(lambda rule: validator.subroutine_target(rule) == "LockBot")
        for action in (
            "Enable Movement Collision With Environment(Event Player);",
            "Disable Movement Collision With Environment(Event Player, False);",
            "Enable Movement Collision With Players(Event Player);",
            "Disable Movement Collision With Players(Event Player);",
        ):
            with self.subTest(action=action):
                self.assert_rejected(self.inject_action(bot_lock, action),
                                     "LockBot: conservare le collisioni native senza riapplicarle")

    def test_bot_lock_requires_exactly_twenty_percent_move_speed(self) -> None:
        bot_lock = self.rule(lambda rule: validator.subroutine_target(rule) == "LockBot")
        mutated = self.replace_in_rule(bot_lock, "Set Move Speed(Event Player, 20);", "Set Move Speed(Event Player, 0);")
        self.assert_rejected(mutated, "LockBot: velocità bot/dummy")

    def test_native_dummy_requires_automatic_forward_throttle(self) -> None:
        movement = self.rule(lambda rule: "Start Throttle In Direction(Event Player," in rule.body)
        mutated = self.replace_in_rule(movement, "Start Throttle In Direction(Event Player,", "Start Throttle Towards Player(Event Player,")
        self.assert_rejected(mutated, "movimento automatico dummy assente")

    def test_native_dummy_movement_requires_a_valid_cached_target(self) -> None:
        movement = self.rule(lambda rule: "Start Throttle In Direction(Event Player," in rule.body)
        mutated = self.replace_in_rule(
            movement,
            "Event Player.DummyBotFollowTarget != Null;",
            "Event Player.DummyBotFollowTarget == Null;",
        )
        self.assert_rejected(mutated, "movimento automatico dummy incompleto")
    def test_native_dummy_movement_cannot_abort_before_facing(self) -> None:
        movement = self.rule(lambda rule: "Start Throttle In Direction(Event Player," in rule.body)
        mutated = self.replace_in_rule(
            movement,
            "\n\t\tStart Facing(Event Player,",
            "\n\t\tAbort;\n\t\tStart Facing(Event Player,",
        )
        self.assert_rejected(mutated, "movimento dummy: azioni esatte senza abort o arresti aggiuntivi")

    def test_native_dummy_movement_cannot_be_stopped_after_throttle(self) -> None:
        movement = self.rule(lambda rule: "Start Throttle In Direction(Event Player," in rule.body)
        throttle = next(validator.iter_calls(movement.body, "Start Throttle In Direction"))
        absolute = validator.Call(
            throttle.name,
            throttle.raw,
            throttle.args,
            movement.start + throttle.start,
            movement.start + throttle.end,
        )
        mutated = self.source[:absolute.end] + ";\n\t\tStop Throttle In Direction(Event Player)" + self.source[absolute.end:]
        self.assert_rejected(mutated, "movimento dummy: azioni esatte senza abort o arresti aggiuntivi")

    def test_native_dummy_facing_requires_a_nonzero_turn_rate(self) -> None:
        movement = self.rule(lambda rule: "Start Throttle In Direction(Event Player," in rule.body)
        facing = next(validator.iter_calls(movement.body, "Start Facing"))
        absolute = validator.Call(
            facing.name,
            facing.raw,
            facing.args,
            movement.start + facing.start,
            movement.start + facing.end,
        )
        mutated = self.replace_call_argument(absolute, 2, "0")
        self.assert_rejected(mutated, "movimento dummy: facing argomento 2")

    def test_native_dummy_facing_reevaluates_direction_and_turn_rate(self) -> None:
        movement = self.rule(lambda rule: "Start Throttle In Direction(Event Player," in rule.body)
        facing = next(validator.iter_calls(movement.body, "Start Facing"))
        absolute = validator.Call(
            facing.name,
            facing.raw,
            facing.args,
            movement.start + facing.start,
            movement.start + facing.end,
        )
        mutated = self.replace_call_argument(absolute, 4, "None")
        self.assert_rejected(mutated, "movimento dummy: facing argomento 4")

    def test_native_dummy_cache_targets_only_the_opposing_team(self) -> None:
        cycle = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerBot")
        mutated = self.replace_in_rule(
            cycle,
            "Team Of(Current Array Element) == Opposite Team Of(Team Of(Global.ActivePlayer))",
            "Team Of(Current Array Element) == Team Of(Global.ActivePlayer)",
        )
        self.assert_rejected(mutated, "cache target dummy: filtro deve essere l'umano nemico vivo opt-in")
    def test_native_dummy_cache_enemy_predicate_cannot_be_negated(self) -> None:
        cycle = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerBot")
        predicate = (
            "And(Entity Exists(Current Array Element), And(Player Variable(Current Array Element, IsHuman) == True, "
            "And(Player Variable(Current Array Element, AllowDummyBotFollow) == True, "
            "And(Has Spawned(Current Array Element), And(Is Alive(Current Array Element), "
            "Team Of(Current Array Element) == Opposite Team Of(Team Of(Global.ActivePlayer)))))))"
        )
        self.assertEqual(cycle.body.count(predicate), 1)
        changed = cycle.body.replace(predicate, f"Not({predicate})")
        mutated = self.source[:cycle.start] + changed + self.source[cycle.end:]
        self.assert_rejected(mutated, "cache target dummy: filtro deve essere l'umano nemico vivo opt-in")
    def test_native_dummy_cache_targets_only_currently_registered_humans(self) -> None:
        cycle = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerBot")
        mutated = self.replace_in_rule(
            cycle,
            "Player Variable(Current Array Element, IsHuman) == True",
            "Player Variable(Current Array Element, IsHuman) == False",
        )
        self.assert_rejected(mutated, "cache target dummy: filtro deve essere l'umano nemico vivo opt-in")
    def test_native_dummy_cache_respects_per_player_follow_opt_out(self) -> None:
        cycle = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerBot")
        mutated = self.replace_in_rule(
            cycle,
            "Player Variable(Current Array Element, AllowDummyBotFollow) == True",
            "True",
        )
        self.assert_rejected(mutated, "cache target dummy deve filtrare gli umani opt-in una sola volta per ciclo")
    def test_no_target_cleanup_rejects_cached_target_opt_out(self) -> None:
        cleanup = self.rule(
            lambda rule: "Event Player.DummyBotFollowTarget == Null" in rule.body
            and "Stop Facing(Event Player);" in rule.body
        )
        mutated = self.replace_in_rule(
            cleanup,
            "Player Variable(Event Player.DummyBotFollowTarget, AllowDummyBotFollow) == False",
            "Player Variable(Event Player.DummyBotFollowTarget, AllowDummyBotFollow) == True",
        )
        self.assert_rejected(mutated, "cleanup movimento dummy cache incompleto")
    def test_native_dummy_stops_at_exactly_four_metres(self) -> None:
        movement = self.rule(lambda rule: "Start Throttle In Direction(Event Player," in rule.body)
        mutated = self.replace_in_rule(movement, "<= 4) ? 0 : 1", "<= 0) ? 0 : 1")
        self.assert_rejected(mutated, "arresto deve usare il target cache")
    def test_native_dummy_stop_condition_cannot_be_negated(self) -> None:
        movement = self.rule(lambda rule: "Start Throttle In Direction(Event Player," in rule.body)
        call = next(validator.iter_calls(movement.body, "Start Throttle In Direction"))
        magnitude = validator.parse_top_level_ternary(call.args[2])
        self.assertIsNotNone(magnitude)
        stop_condition, stopped, moving = magnitude  # type: ignore[misc]
        absolute = validator.Call(call.name, call.raw, call.args, movement.start + call.start, movement.start + call.end)
        mutated = self.replace_call_argument(absolute, 2, f"Not({stop_condition}) ? {stopped} : {moving}")
        self.assert_rejected(mutated, "arresto deve usare il target cache")
    def test_native_dummy_stopped_magnitude_is_zero(self) -> None:
        movement = self.rule(lambda rule: "Start Throttle In Direction(Event Player," in rule.body)
        mutated = self.replace_in_rule(movement, "<= 4) ? 0 : 1", "<= 4) ? 1 : 1")
        self.assert_rejected(mutated, "magnitudine entro quattro metri")

    def test_native_dummy_throttle_reevaluates_direction_and_magnitude(self) -> None:
        movement = self.rule(lambda rule: "Start Throttle In Direction(Event Player," in rule.body)
        mutated = self.replace_in_rule(movement, "Direction and Magnitude);", "None);")
        self.assert_rejected(mutated, "movimento dummy: throttle argomento 5")

    def test_native_dummy_stops_throttle_when_cached_target_is_invalid(self) -> None:
        cleanup = self.rule(
            lambda rule: "Event Player.DummyBotFollowTarget == Null" in rule.body
            and "Stop Facing(Event Player);" in rule.body
        )
        mutated = self.replace_in_rule(cleanup, "Stop Throttle In Direction(Event Player);", "")
        self.assert_rejected(mutated, "cleanup movimento dummy cache incompleto")
    def test_native_dummy_cleanup_stops_when_cached_target_changes_team(self) -> None:
        cleanup = self.rule(
            lambda rule: "Event Player.DummyBotFollowTarget == Null" in rule.body
            and "Stop Facing(Event Player);" in rule.body
        )
        mutated = self.replace_in_rule(
            cleanup,
            "Team Of(Event Player.DummyBotFollowTarget) != Opposite Team Of(Team Of(Event Player))",
            "Team Of(Event Player.DummyBotFollowTarget) == Opposite Team Of(Team Of(Event Player))",
        )
        self.assert_rejected(mutated, "cleanup movimento dummy cache incompleto")
    def test_dummy_release_stops_facing_before_destroy(self) -> None:
        release = self.rule(lambda rule: validator.subroutine_target(rule) == "RemoveTeamDummyBot")
        mutated = self.replace_in_rule(release, "Stop Facing(First Of(Filtered Array(", "Start Facing(First Of(Filtered Array(")
        self.assert_rejected(mutated, "RemoveTeamDummyBot incompleta")

    def test_dummy_creation_reserves_the_last_human_slot(self) -> None:
        manager = self.rule(lambda rule: validator.subroutine_target(rule) == "MaintainDummyBots")
        mutated = self.replace_in_rule(manager,
            "Number Of Players(Team 1) < Number Of Slots(Team 1) - 1",
            "Number Of Players(Team 1) < Number Of Slots(Team 1)")
        self.assert_rejected(mutated, "slot dummy: condizioni, cooldown e azioni esatte")

    def test_dummy_creation_cannot_have_an_impossible_condition(self) -> None:
        manager = self.rule(lambda rule: validator.subroutine_target(rule) == "MaintainDummyBots")
        mutated = self.replace_in_rule(manager, "Abort If(Global.IsReady == False);",
                                       "Abort If(Global.IsReady == False); Abort If(True);")
        self.assert_rejected(mutated, "slot dummy: condizioni, cooldown e azioni esatte")

    def test_dummy_creation_is_limited_to_skirmish(self) -> None:
        manager = self.rule(lambda rule: validator.subroutine_target(rule) == "MaintainDummyBots")
        for team in (1, 2):
            gate = f"Current Game Mode == Game Mode(Skirmish), And(Number Of Players(Team {team})"
            for replacement in ("True", "Current Game Mode == Game Mode(Team Deathmatch)"):
                with self.subTest(team=team, replacement=replacement):
                    mutated = self.replace_in_rule(manager, gate,
                        f"{replacement}, And(Number Of Players(Team {team})")
                    self.assert_rejected(mutated, "slot dummy: condizioni, cooldown e azioni esatte")

    def test_dummy_creation_cooldown_cannot_be_removed_or_shared_between_teams(self) -> None:
        manager = self.rule(lambda rule: validator.subroutine_target(rule) == "MaintainDummyBots")
        for team in (1, 2):
            for old, new in (
                (f"Total Time Elapsed >= Global.WaktuCobaBotBuatanTim{team}", "True"),
                (f"Global.WaktuCobaBotBuatanTim{team} = Total Time Elapsed + 1;", f"Global.WaktuCobaBotBuatanTim{team} = Total Time Elapsed;"),
                (f"Global.WaktuCobaBotBuatanTim{team}", f"Global.WaktuCobaBotBuatanTim{3-team}"),
            ):
                with self.subTest(team=team, old=old):
                    self.assert_rejected(self.replace_in_rule(manager, old, new),
                                         "slot dummy: condizioni, cooldown e azioni esatte")

    def test_scheduler_requires_state_gates_and_bot_cadences(self) -> None:
        scheduler = self.rule(lambda rule: rule.name.startswith("04g -"))
        for old, new in (
            ("Is Dummy Bot(Global.ActivePlayer) == False", "True"),
            ("Global.ActivePlayer.IsAutomaticBot == False", "True"),
            ("Global.ActivePlayer.LuckIconEndTime > 0", "False"),
            ("Global.ActivePlayer.FlyModeActive == True", "True"),
            ("Global.ActivePlayer.MenuOpen == True", "True"),
            ("Global.ActivePlayer.MenuPage == 4", "Global.ActivePlayer.MenuPage == 3"),
            ("If(Global.SchedulerStep % 2 == Slot Of(Global.ActivePlayer) % 2);", "If(True);"),
        ):
            with self.subTest(old=old):
                self.assert_rejected(self.replace_in_rule(scheduler, old, new), "scheduler a stati:")

    def test_vision_cache_requires_active_vision_and_last_viewer_cleanup(self) -> None:
        scheduler = self.rule(lambda rule: rule.name.startswith("04g -"))
        for old, new, error in (
            ("Is True For Any(Global.PlayerListSnapshot, Player Variable(Current Array Element, LuckPrivacyActive) == True)", "True", "Vision: filtro pubblico"),
            ("Global.LuckVisionViewers = Empty Array;", "", "Vision: svuotare il pubblico"),
        ):
            with self.subTest(old=old):
                self.assert_rejected(self.replace_in_rule(scheduler, old, new), error)

    def test_dummy_follow_requires_five_hz_phase(self) -> None:
        routine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerBot")
        mutated = self.replace_in_rule(routine,
            "If(Global.SchedulerStep % 4 == Slot Of(Global.ActivePlayer) % 4);", "If(True);")
        self.assert_rejected(mutated, "target dummy: fase 5 Hz assente")

    def test_dummy_spawn_teleport_is_limited_to_skirmish(self) -> None:
        spawn = self.rule(lambda rule: rule.name.startswith("03f -"))
        gate = "Current Game Mode == Game Mode(Skirmish);"
        for replacement in ("", gate.replace("Skirmish", "Capture The Flag")):
            with self.subTest(replacement=replacement):
                mutated = self.replace_in_rule(spawn, gate, replacement)
                self.assert_rejected(mutated, "teleport dummy: condizioni esatte solo Schermaglia")

    def test_dummy_is_removed_when_the_team_needs_the_last_slot(self) -> None:
        manager = self.rule(lambda rule: validator.subroutine_target(rule) == "MaintainDummyBots")
        mutated = self.replace_in_rule(manager, "Call Subroutine(RemoveTeamDummyBot);", "Abort;")
        self.assert_rejected(mutated, "slot dummy: condizioni, cooldown e azioni esatte")

    def test_dummy_release_cannot_abort_before_cleanup(self) -> None:
        release = self.rule(lambda rule: validator.subroutine_target(rule) == "RemoveTeamDummyBot")
        mutated = self.replace_in_rule(
            release,
            "\n\t\tIf(Player Variable(",
            "\n\t\tAbort;\n\t\tIf(Player Variable(",
        )
        self.assert_rejected(mutated, "RemoveTeamDummyBot: cleanup atomico esatto senza abort")

    def test_dummy_spawn_delay_uses_a_rearmed_timestamp(self) -> None:
        arming = self.rule(
            lambda rule: "If(Event Player.DummyBotTravelTime == 0);" in rule.body
            and "Event Player.DummyBotTravelTime = Total Time Elapsed + 1;" in rule.body
        )
        mutated = self.replace_in_rule(
            arming,
            "If(Event Player.DummyBotTravelTime == 0);",
            "If(Event Player.DummyBotTravelTime > 0);",
        )
        self.assert_rejected(mutated, "arming timestamp teleport dummy assente")

    def test_dummy_death_cleanup_cannot_have_an_impossible_condition(self) -> None:
        death = self.rule(
            lambda rule: validator.event_type(rule) == "Player Died"
            and "Stop Facing(Event Player);" in rule.body
            and "DummyBotTravelTime = 0;" in rule.body
        )
        mutated = self.inject_condition(death, "False == True;")
        self.assert_rejected(mutated, "cleanup morte dummy: condizioni esatte dopo la morte completa")

    def test_dummy_death_cleanup_cannot_abort_before_stopping(self) -> None:
        death = self.rule(
            lambda rule: validator.event_type(rule) == "Player Died"
            and "Stop Facing(Event Player);" in rule.body
            and "DummyBotTravelTime = 0;" in rule.body
        )
        mutated = self.replace_in_rule(
            death,
            "\n\t\tStop Facing(Event Player);",
            "\n\t\tAbort;\n\t\tStop Facing(Event Player);",
        )
        self.assert_rejected(mutated, "cleanup morte dummy: azioni esatte senza abort")

    def test_player_hud_is_never_visible_to_bot_or_dummy_players(self) -> None:
        call = next(
            call for call in validator.iter_calls(self.source, "Create HUD Text")
            if call.args and call.args[0].strip() == "Global.HumanPlayers"
        )
        mutated = self.replace_call_argument(call, 0, "All Players(All Teams)")
        self.assert_rejected(mutated, "Create HUD Text visibile a bot/dummy")

    def test_initial_setup_performs_full_preferences_reset(self) -> None:
        setup = self.rule(lambda rule: validator.subroutine_target(rule) == "PreparePlayer")
        mutated = self.replace_in_rule(setup, "Event Player.MainMenuCursor = 0;", "Event Player.MainMenuCursor = Event Player.MainMenuCursor;")
        self.assert_rejected(mutated, "MainMenuCursor = 0")

    def test_cleanup_is_fully_atomic_without_wait_or_loop(self) -> None:
        cleanup = self.rule(lambda rule: validator.subroutine_target(rule) == "CleanupPlayer")
        for action in ("Wait(0.016, Ignore Condition);", "Loop;"):
            with self.subTest(action=action):
                mutated = self.inject_action(cleanup, action)
                self.assert_rejected(mutated, "CleanupPlayer deve essere atomica")

    def test_registration_reservation_cannot_gate_other_players_runtime(self) -> None:
        scheduler = self.rule(lambda rule: rule.name.startswith("04g -"))
        cadence = "Global.SchedulerStep % 20 == (Global.ActivePlayer.IsHuman == True ? Global.ActivePlayer.HudSlot : Slot Of(Global.ActivePlayer)) % 20"
        mutated = self.replace_in_rule(scheduler, f"If({cadence});",
                                       f"If(And({cadence}, Global.TeamCyclePlayer == Null));")
        self.assert_rejected(mutated, "non deve sospendere gli altri player")

    def test_icon_mirrors_are_required_on_global_creation_and_effect_reset(self) -> None:
        for routine, owner, icon, value in (
            ("ProcessPlayerFastState", "Global.ActivePlayer", "UnkillableIcon", "Global.ActivePlayer.UnkillableIcon"),
            ("RestorePlayerLuck", "Event Player", "LuckIcon", "0"),
            ("RestoreActivePlayerLuck", "Global.ActivePlayer", "LuckIcon", "0"),
        ):
            with self.subTest(routine=routine):
                rule = self.rule(lambda rule: validator.subroutine_target(rule) == routine)
                token = (f"Global.{icon}Ids[Global.PlayerHudSlots["
                         f"Index Of Array Value(Global.HumanPlayers, {owner})]] = {value};")
                mutated = self.replace_in_rule(rule, token, "")
                self.assert_rejected(mutated, "mirror icona canonico mancante")

    def test_leave_cleanup_destroys_every_player_owned_temporary_handle(self) -> None:
        cleanup = self.rule(lambda rule: validator.subroutine_target(rule) == "CleanupPlayer")
        for token, handle in (
            ("Destroy Icon(Global.LuckIconIds[Global.LeavingDebtIndex]);", "LuckIcon"),
            ("Destroy Icon(Global.UnkillableIconIds[Global.LeavingDebtIndex]);", "UnkillableIcon"),
            ("Destroy HUD Text(Global.CleanupSubject.LuckEffectHud);", "LuckEffectHud"),
            ("Destroy In-World Text(Global.CleanupSubject.LuckVisionText);", "LuckVisionText"),
            ("Destroy In-World Text(Global.CleanupSubject.TravelText);", "TravelText"),
        ):
            with self.subTest(handle=handle):
                mutated = self.replace_in_rule(cleanup, token, "")
                self.assert_rejected(mutated, f"handle orfano: {handle}")

    def test_leave_cleanup_recounts_votes_from_surviving_voters(self) -> None:
        recount = self.rule(lambda rule: validator.subroutine_target(rule) == "RecountVotes")
        mutated = self.replace_in_rule(
            recount,
            "Player Variable(Current Array Element, VotedPlayer) == Global.HumanPlayers[Global.VoterIndex]",
            "True",
        )
        self.assert_rejected(mutated, "riferimenti dei voter rimasti")

    def test_leave_cleanup_removes_revenge_attacker_and_debt_in_tandem(self) -> None:
        cleanup = self.rule(lambda rule: validator.subroutine_target(rule) == "CleanupPlayer")
        mutated = self.replace_in_rule(
            cleanup,
            "Modify Player Variable(Global.HumanPlayers[Global.VoterIndex], RevengeDebts, Remove From Array By Index, Global.LeavingRevengeIndex);",
            "",
        )
        self.assert_rejected(mutated, "rimozione debito parallela")

    def test_team_switch_lock_releases_only_after_stable_registration(self) -> None:
        cycle = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerCycle")
        mutated = self.replace_in_rule(
            cycle,
            "Global.ActivePlayer.PlayerHudCreated == True",
            "Global.ActivePlayer.PlayerHudCreated == False",
        )
        self.assert_rejected(mutated, "rilascio stabile lock")

    def test_team_switch_lock_waits_for_stable_automatic_bot(self) -> None:
        cycle = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerBot")
        mutated = self.replace_in_rule(
            cycle,
            "Global.ActivePlayer.IsClassified == True",
            "Global.ActivePlayer.IsClassified == False",
        )
        self.assert_rejected(mutated, "registrazione bot IsAutomaticBot/IsClassified")

    def test_human_classification_initializes_the_shared_hero_tracker(self) -> None:
        classifier = self.rule(
            lambda rule: "Append To Array(Global.HumanPlayers, Event Player)" in rule.body
        )
        mutated = self.replace_in_rule(
            classifier,
            "Event Player.LastHero = Hero Of(Event Player);",
            "Event Player.LastHero = Null;",
        )
        self.assert_rejected(mutated, "classificazione umana non inizializza LastHero")

    def test_human_hero_swap_cleans_luck_in_the_global_scheduler(self) -> None:
        cycle = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerCycle")
        mutated = self.replace_in_rule(
            cycle,
            "Call Subroutine(RestoreActivePlayerLuck);",
            "Abort;",
        )
        self.assert_rejected(mutated, "hero swap umano non pulisce Try Your Luck")

    def test_live_luck_cleanup_preserves_physical_unkillable(self) -> None:
        cleanup = self.rule(lambda rule: validator.subroutine_target(rule) == "RestoreActivePlayerLuck")
        mutated = self.replace_in_rule(
            cleanup,
            "Is Alive(Global.ActivePlayer) == False",
            "Is Alive(Global.ActivePlayer) == True",
        )
        self.assert_rejected(mutated, "cleanup Try vivo non deve sospendere Unkillable")

    def test_privacy_is_off_by_default(self) -> None:
        setup = self.rule(lambda rule: validator.subroutine_target(rule) == "PreparePlayer")
        mutated = self.replace_in_rule(
            setup,
            "Event Player.InspectionPrivacyActive = False;",
            "Event Player.InspectionPrivacyActive = True;",
        )
        self.assert_rejected(mutated, "Privacy deve essere OFF di default")

    def test_direct_toggle_handlers_invert_actual_state_once(self) -> None:
        for name, field in (("ApplyCrouchTravel", "CrouchTravelEnabled"),
                            ("ApplyInspectionPrivacyPage", "InspectionPrivacyActive"),
                            ("ApplyDummyBotFollowPage", "AllowDummyBotFollow")):
            with self.subTest(handler=name):
                apply = self.rule(lambda rule: validator.subroutine_target(rule) == name)
                mutated = self.replace_in_rule(apply, f"Event Player.{field} = Event Player.{field} == False;",
                                               f"Event Player.{field} = Event Player.{field};")
                self.assert_rejected(mutated, "deve invertire lo stato applicato una sola volta")

    def test_real_camera_cache_missing_and_excessive_parenthesis_are_rejected(self) -> None:
        cache = self.rule(lambda rule: validator.subroutine_target(rule) == "RefreshActivePlayerPublicTargets")
        call = next(
            call for call in validator.iter_calls(cache.body, "Set Player Variable")
            if len(call.args) >= 3
            and call.args[1].strip() == "InspectionTargets"
            and "InspectionPrivacyActive" in call.args[2]
        )
        absolute_end = cache.start + call.end
        self.assertEqual(self.source[absolute_end - 1], ")")
        mutations = {
            "missing": self.source[:absolute_end - 1] + self.source[absolute_end:],
            "excessive": self.source[:absolute_end] + ")" + self.source[absolute_end:],
        }
        for kind, mutated in mutations.items():
            with self.subTest(kind=kind):
                self.assert_rejected(mutated, "sintassi actions non bilanciata")

    def test_parentheses_cannot_be_compensated_across_statement_terminators(self) -> None:
        cache = self.rule(lambda rule: validator.subroutine_target(rule) == "RefreshActivePlayerPublicTargets")
        call = next(
            call for call in validator.iter_calls(cache.body, "Set Player Variable")
            if len(call.args) >= 3
            and call.args[1].strip() == "InspectionTargets"
            and "InspectionPrivacyActive" in call.args[2]
        )
        absolute_end = cache.start + call.end
        self.assertEqual(self.source[absolute_end - 1], ")")
        next_if = self.source.index("If(", absolute_end)
        next_terminator = self.source.index(";", next_if)
        mutated = (
            self.source[:absolute_end - 1]
            + self.source[absolute_end:next_terminator]
            + ")"
            + self.source[next_terminator:]
        )
        self.assertIsNone(validator.delimiter_error(validator.rule_block(cache, "actions") or ""))
        self.assert_rejected(mutated, "terminatore statement")

    def test_shared_privacy_filters_have_balanced_call_parentheses(self) -> None:
        privacy_calls: list[tuple[validator.Rule, validator.Call]] = []
        for rule in validator.extract_rules(self.source):
            for call in validator.iter_calls(rule.body, "Filtered Array"):
                if "InspectionPrivacyActive" in call.raw:
                    privacy_calls.append((rule, call))
        self.assertEqual(len(privacy_calls), 2)
        for rule, call in privacy_calls:
            absolute_end = rule.start + call.end
            self.assertEqual(self.source[absolute_end - 1], ")")
            mutations = {
                "missing": self.source[:absolute_end - 1] + self.source[absolute_end:],
                "excessive": self.source[:absolute_end] + ")" + self.source[absolute_end:],
            }
            for kind, mutated in mutations.items():
                with self.subTest(rule=rule.name, kind=kind):
                    self.assert_rejected(mutated, "non bilanciata")
    def test_camera_target_refresh_excludes_private_humans(self) -> None:
        refresh = self.rule(lambda rule: validator.subroutine_target(rule) == "RefreshPlayerPublicTargets")
        mutated = self.replace_in_rule(
            refresh,
            "Player Variable(Current Array Element, InspectionPrivacyActive) == False",
            "Player Variable(Current Array Element, InspectionPrivacyActive) == True",
        )
        self.assert_rejected(mutated, "numero filtri Privacy target-aware")

    def test_unclassified_human_is_not_treated_as_a_public_camera_target(self) -> None:
        refresh = self.rule(lambda rule: validator.subroutine_target(rule) == "RefreshPlayerPublicTargets")
        mutated = self.replace_in_rule(
            refresh,
            "Player Variable(Current Array Element, IsHuman) == True",
            "True",
        )
        self.assert_rejected(mutated, "ogni Privacy OFF target richiede IsHuman=True")

    def test_shared_public_filters_require_a_classified_human(self) -> None:
        protected_rules = (
            self.rule(lambda rule: validator.subroutine_target(rule) == "RefreshPlayerPublicTargets"),
            self.rule(lambda rule: validator.subroutine_target(rule) == "RefreshActivePlayerPublicTargets"),
        )
        for rule in protected_rules:
            with self.subTest(rule=rule.name):
                mutated = self.replace_regex_in_rule(
                    rule,
                    r"Player Variable\(\s*Current Array Element\s*,\s*IsHuman\)\s*==\s*True",
                    "True",
                )
                self.assert_rejected(mutated, "ogni Privacy OFF target richiede IsHuman=True")
    def test_inspection_rejects_a_vision_privacy_bypass(self) -> None:
        refresh = self.rule(lambda rule: validator.subroutine_target(rule) == "RefreshInspectionTarget")
        mutated = self.inject_action(
            refresh,
            "If(Event Player.LuckPrivacyActive == True);\n\t\t\tAbort;\n\t\tEnd;",
        )
        self.assert_rejected(mutated, "bypass Privacy tramite Vision")
    def test_vision_names_include_humans_even_with_privacy_enabled(self) -> None:
        vision = self.rule(
            lambda rule: "Event Player.LuckVisionText = Last Text ID;" in rule.body
            and "Create In-World Text(" in rule.body
        )
        mutated = self.replace_in_rule(
            vision,
            "Event Player.IsHuman == True",
            "And(Event Player.IsHuman == True, Event Player.InspectionPrivacyActive == False)",
        )
        self.assert_rejected(mutated, "anche con Privacy ON")

    def test_vision_hud_declares_that_all_player_names_are_visible(self) -> None:
        mutated = self.replace_once(
            'VISION: ALL PLAYER/BOT NAMES',
            "VISION: PUBLIC PLAYER / BOT NAMES",
        )
        self.assert_rejected(mutated, "testo Vision non dichiara tutti i nomi")

    def test_vision_uses_the_cached_roster_name_for_human_subjects(self) -> None:
        vision = self.rule(
            lambda rule: "Event Player.LuckVisionText = Last Text ID;" in rule.body
            and "Create In-World Text(" in rule.body
        )
        mutated = self.replace_in_rule(
            vision,
            'Event Player.IsHuman == True ? Event Player.DisplayName : Custom String("{0}", Event Player)',
            'Custom String("{0}", Event Player)',
        )
        self.assert_rejected(mutated, "nome roster stabile")

    def test_vision_shows_hero_icon_name_and_live_health(self) -> None:
        vision = self.rule(
            lambda rule: "Event Player.LuckVisionText = Last Text ID;" in rule.body
            and "Create In-World Text(" in rule.body
        )
        call = next(iter(validator.iter_calls(vision.body, "Create In-World Text")))
        absolute = validator.Call(call.name, call.raw, call.args, vision.start + call.start, vision.start + call.end)
        mutated = self.replace_call_argument(absolute, 1, 'Custom String("{0}", Event Player)')
        self.assert_rejected(mutated, "Vision non mostra icona eroe")

    def test_vision_recipients_are_only_other_humans_with_vision_active(self) -> None:
        vision = self.rule(
            lambda rule: "Event Player.LuckVisionText = Last Text ID;" in rule.body
            and "Create In-World Text(" in rule.body
        )
        call = next(iter(validator.iter_calls(vision.body, "Create In-World Text")))
        absolute = validator.Call(call.name, call.raw, call.args, vision.start + call.start, vision.start + call.end)
        mutated = self.replace_call_argument(absolute, 0, "All Players(All Teams)")
        self.assert_rejected(mutated, "destinatari Vision devono essere gli altri umani")

    def test_vision_text_keeps_icon_name_health_order(self) -> None:
        vision = self.rule(
            lambda rule: "Event Player.LuckVisionText = Last Text ID;" in rule.body
            and "Create In-World Text(" in rule.body
        )
        call = next(iter(validator.iter_calls(vision.body, "Create In-World Text")))
        outer = next(
            nested for nested in validator.iter_calls(call.args[1], "Custom String")
            if nested.start == 0 and nested.end == len(call.args[1])
        )
        swapped = list(outer.args)
        swapped[1], swapped[2] = swapped[2], swapped[1]
        changed_text = "Custom String(" + ", ".join(swapped) + ")"
        absolute = validator.Call(call.name, call.raw, call.args, vision.start + call.start, vision.start + call.end)
        mutated = self.replace_call_argument(absolute, 1, changed_text)
        self.assert_rejected(mutated, "ordine icona, nome e salute")

    def test_world_name_iwts_use_one_full_frame_updated_position(self) -> None:
        for label, (_, call, subject) in self.world_name_iwts().items():
            with self.subTest(iwt=label):
                expected_position = (
                    f"Update Every Frame(Eye Position(Evaluate Once({subject})) "
                    "+ Vector(0, 0.450, 0))"
                )
                self.assertEqual(
                    re.sub(r"\s+", "", call.args[2]),
                    re.sub(r"\s+", "", expected_position),
                )
                updates = list(validator.iter_calls(call.args[2], "Update Every Frame"))
                self.assertEqual(len(updates), 1)
                self.assertEqual(updates[0].raw.strip(), call.args[2].strip())
                captures = list(validator.iter_calls(call.args[2], "Evaluate Once"))
                self.assertEqual(len(captures), 1)
                self.assertEqual(len(captures[0].args), 1)
                self.assertEqual(captures[0].args[0].strip(), subject)
                self.assertEqual(call.args[5].strip(), "Visible To Position String and Color")

    def test_world_name_iwt_update_every_frame_must_wrap_the_whole_position_once(self) -> None:
        for label, (_, call, subject) in self.world_name_iwts().items():
            mutations = {
                "missing": (
                    f"Eye Position(Evaluate Once({subject})) + Vector(0, 0.450, 0)"
                ),
                "partial": (
                    f"Update Every Frame(Eye Position(Evaluate Once({subject}))) "
                    "+ Vector(0, 0.450, 0)"
                ),
                "duplicate": (
                    "Update Every Frame(Update Every Frame("
                    f"Eye Position(Evaluate Once({subject})) + Vector(0, 0.450, 0)))"
                ),
            }
            for kind, position in mutations.items():
                with self.subTest(iwt=label, mutation=kind):
                    mutated = self.replace_call_argument(call, 2, position)
                    self.assert_rejected(
                        mutated,
                        f"IWT {label}: posizione fluida Update Every Frame",
                    )

    def test_world_name_iwt_evaluate_once_captures_only_the_correct_subject(self) -> None:
        wrong_subjects = {
            "inspection": "Event Player.InspectionTargetCandidate",
            "Vision": "Event Player.InspectionTarget",
            "Teleport": "Event Player.TravelTextTarget",
        }
        for label, (_, call, subject) in self.world_name_iwts().items():
            mutations = {
                "missing": (
                    f"Update Every Frame(Eye Position({subject}) + Vector(0, 0.450, 0))"
                ),
                "duplicate": (
                    "Update Every Frame(Eye Position(Evaluate Once(Evaluate Once("
                    f"{subject}))) + Vector(0, 0.450, 0))"
                ),
                "whole-position": (
                    "Update Every Frame(Evaluate Once("
                    f"Eye Position({subject}) + Vector(0, 0.450, 0)))"
                ),
                "wrong-subject": (
                    "Update Every Frame(Eye Position(Evaluate Once("
                    f"{wrong_subjects[label]})) + Vector(0, 0.450, 0))"
                ),
            }
            for kind, position in mutations.items():
                with self.subTest(iwt=label, mutation=kind):
                    mutated = self.replace_call_argument(call, 2, position)
                    self.assert_rejected(
                        mutated,
                        f"IWT {label}: Evaluate Once deve catturare soltanto l'identità",
                    )

    def test_world_name_iwt_anchor_keeps_the_head_offset(self) -> None:
        for label, (_, call, subject) in self.world_name_iwts().items():
            with self.subTest(iwt=label):
                wrong_anchor = (
                    f"Update Every Frame(Eye Position(Evaluate Once({subject})) "
                    "+ Vector(0, 1, 0))"
                )
                mutated = self.replace_call_argument(call, 2, wrong_anchor)
                self.assert_rejected(
                    mutated,
                    f"IWT {label}: ancoraggio fluido sopra l'identità",
                )

    def test_world_name_iwts_keep_full_reevaluation(self) -> None:
        for label, (_, call, _) in self.world_name_iwts().items():
            with self.subTest(iwt=label):
                mutated = self.replace_call_argument(call, 5, "Visible To String and Color")
                self.assert_rejected(mutated, f"IWT {label}: reevaluation completa")

    def test_inspection_crouch_is_blocked_during_vision(self) -> None:
        inspection = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Event Player.InspectionTarget != Event Player.InspectionTargetCandidate" in rule.body
        )
        mutated = self.replace_in_rule(inspection, "\n\t\tEvent Player.LuckPrivacyActive == False;", "")
        self.assert_rejected(mutated, "inspection Crouch non è bloccata durante Vision")

    def test_teleport_crouch_is_blocked_during_vision(self) -> None:
        teleport = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Event Player.CrouchTravelActive = True;" in rule.body
            and "Button(Crouch)" in rule.body
        )
        mutated = self.replace_in_rule(teleport, "\n\t\tEvent Player.LuckPrivacyActive == False;", "")
        self.assert_rejected(mutated, "Teleport Crouch non è bloccato durante Vision")

    def test_inspection_cleanup_runs_when_vision_starts(self) -> None:
        cycle = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerCycle")
        mutated = self.replace_in_rule(
            cycle,
            "Global.ActivePlayer.LuckPrivacyActive == True",
            "Global.ActivePlayer.LuckPrivacyActive == False",
        )
        self.assert_rejected(mutated, "cleanup inspection non reagisce all'avvio di Vision")

    def test_teleport_cleanup_runs_when_vision_starts(self) -> None:
        cleanup = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Event Player.CrouchTravelActive == True;" in rule.body
            and "Event Player.CrouchTravelActive = False;" in rule.body
            and "Destroy HUD Text(Event Player.MenuHud);" in rule.body
        )
        mutated = self.replace_in_rule(
            cleanup,
            "Event Player.LuckPrivacyActive == True",
            "Event Player.LuckPrivacyActive == False",
        )
        self.assert_rejected(mutated, "cleanup Teleport Crouch non reagisce all'avvio di Vision")

    def test_vision_name_cleanup_does_not_run_when_subject_enables_privacy(self) -> None:
        cleanup = self.rule(
            lambda rule: "Destroy In-World Text(Event Player.LuckVisionText);" in rule.body
            and "Event Player.LuckVisionText = Null;" in rule.body
            and validator.event_type(rule) == "Ongoing - Each Player"
        )
        mutated = self.replace_in_rule(
            cleanup,
            "Is Alive(Event Player) == False",
            "Or(Is Alive(Event Player) == False, And(Event Player.IsHuman == True, Event Player.InspectionPrivacyActive == True))",
        )
        self.assert_rejected(mutated, "non deve rimuovere un umano che attiva Privacy")

    def test_inspection_and_teleport_never_enable_native_nameplates(self) -> None:
        protected = (
            self.rule(
                lambda rule: "Event Player.InspectionTarget != Event Player.InspectionTargetCandidate" in rule.body
            ),
            self.rule(
                lambda rule: "Event Player.TravelTextTarget != Event Player.TravelTargetCandidate" in rule.body
                and "Create In-World Text(Event Player" in rule.body
            ),
        )
        for rule in protected:
            with self.subTest(rule=rule.name):
                mutated = self.replace_in_rule(
                    rule,
                    "Disable Nameplates(All Players(All Teams), Event Player);",
                    "Enable Nameplates(All Players(All Teams), Event Player);",
                )
                self.assert_rejected(mutated, "nameplate")

    def test_inspection_renderer_uses_roster_membership_for_cached_name(self) -> None:
        inspection = self.rule(
            lambda rule: "Event Player.InspectionTarget != Event Player.InspectionTargetCandidate" in rule.body
            and "Create In-World Text(Event Player" in rule.body
        )
        mutated = self.replace_in_rule(
            inspection,
            "Array Contains(Global.HumanPlayers, Event Player.InspectionTarget) == True ? "
            "Player Variable(Event Player.InspectionTarget, DisplayName)",
            "Player Variable(Event Player.InspectionTarget, IsHuman) == True ? "
            "Player Variable(Event Player.InspectionTarget, DisplayName)",
        )
        self.assert_rejected(mutated, "inspection non deve usare IsHuman come guardia DisplayName")

    def test_teleport_renderer_uses_roster_membership_for_cached_name(self) -> None:
        teleport = self.rule(
            lambda rule: "Event Player.TravelTextTarget != Event Player.TravelTargetCandidate" in rule.body
            and "Create In-World Text(Event Player" in rule.body
        )
        mutated = self.replace_in_rule(
            teleport,
            "Array Contains(Global.HumanPlayers, Event Player.TravelTargetCandidate) == True ? "
            "Player Variable(Event Player.TravelTargetCandidate, DisplayName)",
            "Player Variable(Event Player.TravelTargetCandidate, IsHuman) == True ? "
            "Player Variable(Event Player.TravelTargetCandidate, DisplayName)",
        )
        self.assert_rejected(mutated, "teleport non deve usare IsHuman come guardia DisplayName")

    def test_inspection_renderer_snapshots_cached_name_with_evaluate_once(self) -> None:
        inspection = self.rule(
            lambda rule: "Event Player.InspectionTarget != Event Player.InspectionTargetCandidate" in rule.body
            and "Create In-World Text(Event Player" in rule.body
        )
        mutated = self.replace_in_rule(
            inspection,
            'Evaluate Once(Array Contains(Global.HumanPlayers, Event Player.InspectionTarget) == True ? '
            'Player Variable(Event Player.InspectionTarget, DisplayName) : '
            'Custom String("{0}", Is Duplicating(Event Player.InspectionTarget) ? '
            'Hero Being Duplicated(Event Player.InspectionTarget) : '
            'Hero Of(Event Player.InspectionTarget)))',
            'Array Contains(Global.HumanPlayers, Event Player.InspectionTarget) == True ? '
            'Player Variable(Event Player.InspectionTarget, DisplayName) : '
            'Custom String("{0}", Is Duplicating(Event Player.InspectionTarget) ? '
            'Hero Being Duplicated(Event Player.InspectionTarget) : '
            'Hero Of(Event Player.InspectionTarget))',
        )
        self.assert_rejected(mutated, "inspection deve usare Evaluate Once sul nome target")

    def test_teleport_renderer_snapshots_cached_name_with_evaluate_once(self) -> None:
        teleport = self.rule(
            lambda rule: "Event Player.TravelTextTarget != Event Player.TravelTargetCandidate" in rule.body
            and "Create In-World Text(Event Player" in rule.body
        )
        mutated = self.replace_in_rule(
            teleport,
            'Evaluate Once(Array Contains(Global.HumanPlayers, Event Player.TravelTargetCandidate) == True ? '
            'Player Variable(Event Player.TravelTargetCandidate, DisplayName) : '
            'Custom String("{0}", Is Duplicating(Event Player.TravelTargetCandidate) ? '
            'Hero Being Duplicated(Event Player.TravelTargetCandidate) : '
            'Hero Of(Event Player.TravelTargetCandidate)))',
            'Array Contains(Global.HumanPlayers, Event Player.TravelTargetCandidate) == True ? '
            'Player Variable(Event Player.TravelTargetCandidate, DisplayName) : '
            'Custom String("{0}", Is Duplicating(Event Player.TravelTargetCandidate) ? '
            'Hero Being Duplicated(Event Player.TravelTargetCandidate) : '
            'Hero Of(Event Player.TravelTargetCandidate))',
        )
        self.assert_rejected(mutated, "teleport deve usare Evaluate Once sul nome target")

    def test_inspection_renderer_nonhuman_fallback_uses_hero_name(self) -> None:
        inspection = self.rule(
            lambda rule: "Event Player.InspectionTarget != Event Player.InspectionTargetCandidate" in rule.body
            and "Create In-World Text(Event Player" in rule.body
        )
        mutated = self.replace_in_rule(
            inspection,
            'Custom String("{0}", Is Duplicating(Event Player.InspectionTarget) ? '
            'Hero Being Duplicated(Event Player.InspectionTarget) : '
            'Hero Of(Event Player.InspectionTarget))',
            'Custom String("{0}", Event Player.InspectionTarget)',
        )
        self.assert_rejected(mutated, "inspection non deve mostrare identity token grezzo ai dummy")

    def test_teleport_renderer_nonhuman_fallback_uses_hero_name(self) -> None:
        teleport = self.rule(
            lambda rule: "Event Player.TravelTextTarget != Event Player.TravelTargetCandidate" in rule.body
            and "Create In-World Text(Event Player" in rule.body
        )
        mutated = self.replace_in_rule(
            teleport,
            'Custom String("{0}", Is Duplicating(Event Player.TravelTargetCandidate) ? '
            'Hero Being Duplicated(Event Player.TravelTargetCandidate) : '
            'Hero Of(Event Player.TravelTargetCandidate))',
            'Custom String("{0}", Event Player.TravelTargetCandidate)',
        )
        self.assert_rejected(mutated, "teleport non deve mostrare identity token grezzo ai dummy")

    def test_camera_target_cache_excludes_private_humans(self) -> None:
        cache = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerMaintenance")
        mutated = self.replace_in_rule(
            cache,
            "Call Subroutine(RefreshActivePlayerPublicTargets);",
            "Abort;",
        )
        self.assert_rejected(mutated, "cache target Camera non riusa la subroutine pubblica globale")

    def test_active_observer_is_stopped_when_target_turns_private(self) -> None:
        cycle = self.rule(lambda rule: validator.subroutine_target(rule) == "ProcessPlayerCycle")
        mutated = self.replace_in_rule(
            cycle,
            "Global.ActivePlayer.CameraTarget.InspectionPrivacyActive == True",
            "Global.ActivePlayer.CameraTarget.InspectionPrivacyActive == False",
        )
        self.assert_rejected(mutated, "osservatore attivo non viene fermato")

    def test_workshop_setting_labels_are_trilingual(self) -> None:
        call = next(iter(validator.iter_calls(self.source, "Workshop Setting Integer")))
        mutated = self.replace_call_argument(call, 1, 'Custom String("Server duration")')
        self.assert_rejected(mutated, "label Workshop Setting Integer")

    def test_workshop_setting_category_validation_is_integrated(self) -> None:
        call = next(iter(validator.iter_calls(self.source, "Workshop Setting Integer")))
        mutated = self.replace_call_argument(call, 0, 'Custom String("SERVER: CHILL")')
        self.assert_rejected(mutated, "categoria Workshop Setting Integer contiene un carattere vietato")

    def test_objective_teleport_requires_the_current_objective(self) -> None:
        objective = self.rule(lambda rule: validator.subroutine_target(rule) == "TravelToObjective")
        for replacement in ("Vector(0, 0, 0)", "Flag Position(Opposite Team Of(Team Of(Event Player)))"):
            with self.subTest(replacement=replacement):
                mutated = self.replace_in_rule(objective, "Objective Position(Objective Index)", replacement)
                self.assert_rejected(mutated, "obiettivo corrente, controlli anti-origine e sicurezza obbligatori")

    def test_objective_teleport_rejects_missing_or_unsafe_destinations(self) -> None:
        objective = self.rule(lambda rule: validator.subroutine_target(rule) == "TravelToObjective")
        for target in ("TravelDestination", "SafeRevivePosition"):
            guard = f"If(Distance Between(Event Player.{target}, Vector(0, 0, 0)) <= 0.100);"
            with self.subTest(target=target):
                mutated = self.replace_in_rule(objective, guard, "If(False);")
                self.assert_rejected(mutated, "obiettivo corrente, controlli anti-origine e sicurezza obbligatori")

    def test_native_mode_result_cannot_be_overridden(self) -> None:
        mutated = self.source + "\nSet Team Score(Team 1, 99);\n"
        self.assert_rejected(mutated, "modalità nativa")

    def test_camera_has_exactly_one_raycast(self) -> None:
        camera_rule = validator.rule_by_subroutine(validator.extract_rules(self.source), "StartCamera")
        self.assertIsNotNone(camera_rule)
        assert camera_rule is not None
        mutated_body = camera_rule.body.replace(
            "Ray Cast Hit Position(",
            "Ray Cast Hit Position(Eye Position(Event Player), Vector(0, 0, 0), Empty Array, Empty Array, False) + Ray Cast Hit Position(",
            1,
        )
        mutated = self.source[:camera_rule.start] + mutated_body + self.source[camera_rule.end:]
        self.assert_rejected(mutated, "raycast Camera")

    def test_camera_start_is_shared_once_with_per_frame_blend_speed_zero(self) -> None:
        calls = self.start_camera_calls()
        self.assertEqual(len(calls), 1)
        rule, call = calls[0]
        self.assertEqual(validator.subroutine_target(rule), "StartCamera")
        self.assertEqual(len(call.args), 4)
        self.assertTrue(call.args[1].strip().startswith("Update Every Frame("))
        self.assertTrue(call.args[2].strip().startswith("Update Every Frame("))
        self.assertEqual(call.args[3].strip(), "0")

    def test_camera_nonzero_blend_cannot_chase_a_per_frame_target(self) -> None:
        calls = self.start_camera_calls()
        self.assertEqual(len(calls), 1)
        _, call = calls[0]
        mutated = self.replace_call_argument(call, 3, "75")
        self.assert_rejected(mutated, "Camera per-frame deve usare Blend Speed 0")

    def test_camera_eye_and_look_at_remain_per_frame(self) -> None:
        calls = self.start_camera_calls()
        self.assertEqual(len(calls), 1)
        _, call = calls[0]
        for argument in (1, 2):
            with self.subTest(argument=argument):
                mutated = self.replace_call_argument(call, argument, "Eye Position(Event Player.CameraTarget)")
                self.assert_rejected(mutated, "Camera per-frame deve usare Blend Speed 0")

    def test_camera_self_watch_and_quick_toggle_share_the_same_subroutine(self) -> None:
        rules = validator.extract_rules(self.source)
        callers = [
            rule
            for rule in rules
            if "Call Subroutine(StartCamera);" in rule.body
        ]
        self.assertEqual(sum(rule.body.count("Call Subroutine(StartCamera);") for rule in callers), 3)
        quick_toggle = next(rule for rule in callers if "Wait(0.500, Abort When False);" in rule.body)
        mutated = self.replace_in_rule(quick_toggle, "Call Subroutine(StartCamera);", "Abort;")
        self.assert_rejected(mutated, "Camera personale, watch e toggle rapido devono condividere StartCamera")

    def test_camera_start_cannot_escape_the_shared_subroutine(self) -> None:
        calls = self.start_camera_calls()
        self.assertEqual(len(calls), 1)
        _, call = calls[0]
        foreign_rule = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Event Player.CameraInteractConsumed = False;" in rule.body
        )
        mutated = self.inject_action(foreign_rule, call.raw + ";")
        self.assert_rejected(mutated, "un solo Start Camera in StartCamera")

    def test_safe_position_cannot_lose_the_vertical_floor_check(self) -> None:
        safe = self.rule(
            lambda rule: validator.subroutine_target(rule) == "FindSafeTravelPosition"
        )
        branch = (
            "If(Distance Between(Ray Cast Hit Position(Event Player.SafeRevivePosition + Vector(0, 5, 0), "
            "Event Player.SafeRevivePosition - Vector(0, 20, 0), Empty Array, Empty Array, False), "
            "Event Player.SafeRevivePosition) > 6);\n"
            "\t\t\tEvent Player.SafeRevivePosition = Vector(0, 0, 0);\n"
            "\t\t\tAbort;\n"
            "\t\tEnd;"
        )
        mutated = self.replace_in_rule(safe, branch, "")
        self.assert_rejected(mutated, "raycast terreno verticale")

    def test_foreign_custom_rule_title_is_rejected(self) -> None:
        rule = validator.extract_rules(self.source)[0]
        mutated = self.source[:rule.start] + rule.body.replace(rule.name, rule.name + " - English comment", 1) + self.source[rule.end:]
        self.assert_rejected(mutated, "non interamente indonesiano")

    def test_duplicate_rule_body_is_rejected(self) -> None:
        rule = validator.extract_rules(self.source)[0]
        clone = rule.body.replace(rule.name, rule.name + " duplikat", 1)
        mutated = self.source + "\n\n" + clone
        self.assert_rejected(mutated, "corpo identico")


    def test_builtin_completion_is_disabled_exactly_once(self) -> None:
        token = "Disable Built-In Game Mode Completion;"
        self.assertEqual(self.source.count(token), 1)
        mutated = self.source.replace(token, "", 1)
        self.assert_rejected(mutated, "completamento nativo fino al timer CHILL")
        mutated = self.source.replace(token, token + "\n\t\t" + token, 1)
        self.assert_rejected(mutated, "completamento nativo fino al timer CHILL")
        sync_token = "Set Match Time(Max(1, Global.ServerTimeRemaining));"
        self.assertNotIn("ServerTimeRemaining + 5", self.source)
        self.assertIn(sync_token, self.source)
        mutated = self.source.replace(sync_token, "", 1)
        self.assert_rejected(mutated, "timer mode bawaan tidak disinkronkan")
        sync_rule = self.rule(
            lambda rule: sync_token in rule.body and "Disable Built-In Game Mode Completion;" in rule.body
        )
        mutated = self.replace_in_rule(sync_rule, "Is Game In Progress == True", "Is Game In Progress == False")
        self.assert_rejected(mutated, "hanya saat pertandingan berjalan")
        mutated = self.replace_in_rule(sync_rule, "Global.ServerTimeRemaining > 0", "Global.ServerTimeRemaining >= 0")
        self.assert_rejected(mutated, "pemicu tunggal restart")

    def test_bootstrap_skips_use_exactly_two_match_time_zero_calls(self) -> None:
        token = "Set Match Time(0);"
        self.assertEqual(self.source.count(token), 2)
        mutated = self.source.replace(token, "", 1)
        self.assert_rejected(mutated, "tepat dua Set Match Time(0)")
        mutated = self.source.replace(token, token + "\n\t\t" + token, 1)
        self.assert_rejected(mutated, "tepat dua Set Match Time(0)")

    def test_bootstrap_skip_heroes_keeps_assemble_guard_and_latch_order(self) -> None:
        skip_heroes = self.rule(
            lambda rule: rule.name.startswith("00a2 - Global: Skip hero selection")
        )
        self.assertEqual(skip_heroes.body.count("Set Match Time(0);"), 1)
        mutated = self.replace_in_rule(skip_heroes, "Is Assembling Heroes == True;", "Is Assembling Heroes == False;")
        self.assert_rejected(mutated, "Is Assembling Heroes == True")
        mutated = self.replace_regex_in_rule(
            skip_heroes,
            r"Global\.HeroSelectionSkipped\s*=\s*True;\s*Set Match Time\(0\);",
            "Set Match Time(0);\n\t\tGlobal.HeroSelectionSkipped = True;",
        )
        self.assert_rejected(mutated, "latch sebelum Set Match Time(0)")

    def test_bootstrap_skip_setup_keeps_setup_guard_and_latch_order(self) -> None:
        skip_setup = self.rule(
            lambda rule: rule.name.startswith("00a3 - Global: Skip initial setup")
        )
        self.assertEqual(skip_setup.body.count("Set Match Time(0);"), 1)
        mutated = self.replace_in_rule(skip_setup, "Is In Setup == True;", "Is In Setup == False;")
        self.assert_rejected(mutated, "Is In Setup == True")
        mutated = self.replace_regex_in_rule(
            skip_setup,
            r"Global\.SetupSkipped\s*=\s*True;\s*Set Match Time\(0\);",
            "Set Match Time(0);\n\t\tGlobal.SetupSkipped = True;",
        )
        self.assert_rejected(mutated, "latch sebelum Set Match Time(0)")

    def test_bootstrap_lock_rule_never_sets_match_time_zero(self) -> None:
        lock = self.rule(
            lambda rule: rule.name.startswith('00a4 - Global: Lock initial phase skipping after the game starts')
        )
        self.assertEqual(lock.body.count("Set Match Time(0);"), 0)
        mutated = self.inject_action(lock, "Set Match Time(0);")
        self.assert_rejected(mutated, "00a4 tidak boleh menembak Set Match Time(0)")

    def test_native_timer_sync_must_stay_inside_the_one_hz_scheduler_branch(self) -> None:
        sync_token = "Set Match Time(Max(1, Global.ServerTimeRemaining));"
        scheduler = self.rule(lambda rule: sync_token in rule.body)
        nested = (
            "\t\t\tIf(And(Is Game In Progress == True, Global.ServerTimeRemaining > 0));\n"
            '\t\t\t\t"Satu kali per detik, tahan penyelesaian mode bawaan dan sinkronkan penghitung waktu bawaan di atas nol sampai waktu server habis."\n'
            "\t\t\t\tDisable Built-In Game Mode Completion;\n"
            f"\t\t\t\t{sync_token}\n"
            "\t\t\tEnd;\n"
        )
        self.assertIn(nested, scheduler.body)
        changed = scheduler.body.replace(nested, "", 1)
        insertion = changed.index("\n\t\tIf(And(Global.TeamCyclePlayer")
        changed = changed[:insertion] + "\n" + nested + changed[insertion:]
        mutated = self.source[:scheduler.start] + changed + self.source[scheduler.end:]
        self.assert_rejected(mutated, "ramo scheduler 1 Hz")

    def test_native_completion_block_cannot_run_outside_the_one_hz_branch(self) -> None:
        token = "Disable Built-In Game Mode Completion;"
        scheduler = self.rule(lambda rule: token in rule.body)
        self.assertIn(token, scheduler.body)
        changed = scheduler.body.replace(token, "", 1)
        closing = changed.rfind("\n\t}")
        self.assertGreater(closing, 0)
        changed = changed[:closing] + f"\n\t\t{token}" + changed[closing:]
        mutated = self.source[:scheduler.start] + changed + self.source[scheduler.end:]
        self.assert_rejected(mutated, "blocco completion fuori dal ramo scheduler 1 Hz")

class RepositoryMetadataTests(unittest.TestCase):
    def make_repo(self, root: Path) -> None:
        (root / ".github" / "workflows").mkdir(parents=True)
        (root / "docs").mkdir()
        (root / "VERSION").write_text("0.8.1\n", encoding="utf-8")
        for relative in validator.CORE_DOCS:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Guida operativa del progetto.\n", encoding="utf-8")
        (root / "CHANGELOG.md").write_text(
            "## 0.8.1\n\nStato: **live-ready** (release storica).\n",
            encoding="utf-8",
        )
        (root / ".github" / "workflows" / "validate-workshop.yml").write_text(
            "on:\n  push:\njobs:\n  validate:\n    steps:\n      - run: python tools/validate_workshop.py\n"
            "      - run: python -m unittest discover -s tests\n",
            encoding="utf-8",
        )

    def metadata_errors(self, root: Path) -> list[str]:
        checks = validator.Checks()
        validator.validate_metadata(checks, root)
        return checks.errors

    def test_operational_docs_need_no_repeated_version_or_status_marker(self) -> None:
        with tempfile.TemporaryDirectory(dir=validator.ROOT.parent) as directory:
            root = Path(directory)
            self.make_repo(root)
            self.assertEqual(self.metadata_errors(root), [])

    def test_missing_version_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=validator.ROOT.parent) as directory:
            root = Path(directory)
            self.make_repo(root)
            (root / "VERSION").unlink()
            self.assertIn("VERSION assente", self.metadata_errors(root))

    def test_stale_version_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=validator.ROOT.parent) as directory:
            root = Path(directory)
            self.make_repo(root)
            (root / "VERSION").write_text("0.7.2\n", encoding="utf-8")
            self.assertTrue(any("VERSION" in error for error in self.metadata_errors(root)))

    def test_missing_required_document_is_rejected(self) -> None:
        for relative in validator.CORE_DOCS:
            with self.subTest(path=relative), tempfile.TemporaryDirectory(dir=validator.ROOT.parent) as directory:
                root = Path(directory)
                self.make_repo(root)
                (root / relative).unlink()
                self.assertIn(
                    f"documento obbligatorio assente: {relative}",
                    self.metadata_errors(root),
                )

    def test_empty_required_document_is_rejected(self) -> None:
        for relative in validator.CORE_DOCS:
            for content in ("", " \t\r\n\n"):
                with self.subTest(path=relative, content=content), tempfile.TemporaryDirectory(dir=validator.ROOT.parent) as directory:
                    root = Path(directory)
                    self.make_repo(root)
                    (root / relative).write_text(content, encoding="utf-8")
                    self.assertIn(
                        f"documento obbligatorio vuoto: {relative}",
                        self.metadata_errors(root),
                    )

    def test_new_revision_can_honestly_await_client_validation(self) -> None:
        with tempfile.TemporaryDirectory(dir=validator.ROOT.parent) as directory:
            root = Path(directory)
            self.make_repo(root)
            for relative in validator.CORE_DOCS:
                (root / relative).write_text(
                    "Stato: **static-ready / live-pending** (nuova revisione main).\n"
                    "I test automatici non attestano la stabilità nel client.\n",
                    encoding="utf-8",
                )
            self.assertEqual(self.metadata_errors(root), [])

    def test_offline_metadata_does_not_claim_a_remote_release_is_missing(self) -> None:
        claims = (
            "Il tag finale v0.8.1 identifica il commit pubblicato e validato.",
            "La release 0.8.1 è stata pubblicata.",
            "La release v0.8.1 è stata pubblicata.",
            "https://github.com/skelos95/ruang-irama-workshop/releases/tag/v0.8.1",
        )
        for claim in claims:
            with self.subTest(claim=claim), tempfile.TemporaryDirectory(dir=validator.ROOT.parent) as directory:
                root = Path(directory)
                self.make_repo(root)
                readme = root / "README.md"
                readme.write_text(
                    readme.read_text(encoding="utf-8") + f"\n{claim}\n",
                    encoding="utf-8",
                )
                self.assertEqual(self.metadata_errors(root), [])

    def test_missing_changelog_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=validator.ROOT.parent) as directory:
            root = Path(directory)
            self.make_repo(root)
            (root / "CHANGELOG.md").unlink()
            self.assertIn("CHANGELOG.md assente", self.metadata_errors(root))

    def test_missing_historical_release_section_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=validator.ROOT.parent) as directory:
            root = Path(directory)
            self.make_repo(root)
            (root / "CHANGELOG.md").write_text(
                "# Changelog\n\nVersione nominale 0.8.1.\n\n## 0.8.0\n",
                encoding="utf-8",
            )
            self.assertIn(
                "CHANGELOG.md senza sezione storica 0.8.1",
                self.metadata_errors(root),
            )

    def test_historical_release_accepts_tag_heading_without_forced_status(self) -> None:
        with tempfile.TemporaryDirectory(dir=validator.ROOT.parent) as directory:
            root = Path(directory)
            self.make_repo(root)
            (root / "CHANGELOG.md").write_text(
                "## v0.8.1 — 2026-08-25\n\nRiscontri storici conservati.\n",
                encoding="utf-8",
            )
            self.assertEqual(self.metadata_errors(root), [])

    def test_newer_changelog_revision_does_not_inherit_historical_live_ready(self) -> None:
        with tempfile.TemporaryDirectory(dir=validator.ROOT.parent) as directory:
            root = Path(directory)
            self.make_repo(root)
            (root / "CHANGELOG.md").write_text(
                "## Revisione main — 2026-09-29\n"
                "Stato: **static-ready / live-pending**.\n"
                "## 0.8.1\nStato: **live-ready** (release storica).\n"
                "## 0.8.0\nStato: **live-pending**.\n",
                encoding="utf-8",
            )
            self.assertEqual(self.metadata_errors(root), [])

    def test_obsolete_lifecycle_claims_are_rejected_in_docs_and_release_history(self) -> None:
        claims = (
            "Dopo un cambio squadra il refresh leggero attende che il player sia spawned e vivo.",
            "Cambio squadra ripetuto senza cleanup/setup completo, ricostruzione HUD o reset engine.",
            "Un cambio squadra aggiorna soltanto i campi Team.",
            "Jump Resurrect teletrasporta sempre su Nearest Walkable Position.",
            "Se non esiste un terreno sicuro il player resta morto.",
            "Nel vuoto usa Nearest Walkable Position(DeathPosition).",
        )
        for relative in (*validator.CORE_DOCS, "CHANGELOG.md"):
            for claim in claims:
                with self.subTest(path=relative, claim=claim), tempfile.TemporaryDirectory(dir=validator.ROOT.parent) as directory:
                    root = Path(directory)
                    self.make_repo(root)
                    path = root / relative
                    path.write_text(
                        path.read_text(encoding="utf-8") + f"\n{claim}\n",
                        encoding="utf-8",
                    )
                    self.assertTrue(
                        any(
                            "testo lifecycle obsoleto" in error
                            for error in self.metadata_errors(root)
                        )
                    )

    def test_current_jump_resurrect_preparation_is_allowed_in_docs(self) -> None:
        claims = (
            "Calcola sempre Nearest Walkable Position dalla posizione corrente prima di Resurrect.",
            "Solo se il punto è insicuro: Teleport del cadavere prima di Resurrect e di nuovo dopo.",
        )
        for claim in claims:
            with self.subTest(claim=claim):
                self.assertFalse(any(pattern.search(claim) for _, pattern in validator.OBSOLETE_CURRENT_TEXT_PATTERNS))

    def test_maintenance_workflow_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=validator.ROOT.parent) as directory:
            root = Path(directory)
            self.make_repo(root)
            (root / ".github" / "workflows" / "maintenance-patch.yml").write_text("on: workflow_dispatch\n", encoding="utf-8")
            self.assertTrue(any("workflow permanenti" in error for error in self.metadata_errors(root)))

    def test_stale_github_marker_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=validator.ROOT.parent) as directory:
            root = Path(directory)
            self.make_repo(root)
            (root / ".github" / ".validator-wait-policy-trigger").write_text("one-shot\n", encoding="utf-8")
            self.assertTrue(any("contenuti permanenti .github" in error for error in self.metadata_errors(root)))

    def test_non_workflow_file_inside_workflows_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=validator.ROOT.parent) as directory:
            root = Path(directory)
            self.make_repo(root)
            (root / ".github" / "workflows" / "patcher.py").write_text("# one-shot\n", encoding="utf-8")
            self.assertTrue(any("contenuti permanenti .github" in error for error in self.metadata_errors(root)))

    def test_validation_workflow_must_not_push(self) -> None:
        with tempfile.TemporaryDirectory(dir=validator.ROOT.parent) as directory:
            root = Path(directory)
            self.make_repo(root)
            workflow = root / ".github" / "workflows" / "validate-workshop.yml"
            workflow.write_text(workflow.read_text(encoding="utf-8") + "      - run: git push\n", encoding="utf-8")
            self.assertTrue(any("non deve modificare" in error for error in self.metadata_errors(root)))


if __name__ == "__main__":
    unittest.main()
