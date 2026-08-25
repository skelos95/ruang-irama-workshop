from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from tools import validate_workshop as validator


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

    def add_player_declaration_and_setup_init(self, name: str, initial_value: str) -> str:
        _, players, _, declaration_span = validator.declaration_entries(self.source)
        self.assertNotIn(name, {entry.name for entry in players})
        subroutines_start = self.source.index("\nsubroutines", declaration_span[0])
        variables_close = self.source.rfind("}", declaration_span[0], subroutines_start)
        declaration = f"\t\t{len(players)}: {name}\n"
        mutated = self.source[:variables_close] + declaration + self.source[variables_close:]
        setup = next(
            rule for rule in validator.extract_rules(mutated)
            if validator.subroutine_target(rule) == "SiapkanPemain"
        )
        closing = setup.body.rfind("\n\t}")
        changed_setup = setup.body[:closing] + f"\n\t\tEvent Player.{name} = {initial_value};" + setup.body[closing:]
        return mutated[:setup.start] + changed_setup + mutated[setup.end:]

    def test_official_source_passes_all_semantic_checks(self) -> None:
        self.assertEqual(self.errors(self.source), [])

    def test_special_player_declaration_setup_and_exact_unicode_are_guarded(self) -> None:
        mutations = (
            (
                self.source.replace("\t\t105: MusikKhusus", "\t\t104: MusikKhusus", 1),
                "indice MusikKhusus",
            ),
            (
                self.source.replace(
                    "Event Player.MusikKhusus = Null;",
                    "Event Player.MusikKhusus = False;",
                    1,
                ),
                "inizializzazione MusikKhusus",
            ),
            (
                self.source.replace('Custom String("งูแท้")', 'Custom String("งูเท้")', 1),
                "matcher Unicode esatto งูแท้",
            ),
        )
        for mutated, fragment in mutations:
            with self.subTest(fragment=fragment):
                self.assert_rejected(mutated, fragment)

    def test_special_player_indices_and_cursors_are_guarded(self) -> None:
        classifier = self.rule(
            lambda rule: "Append To Array(Global.PemainManusia, Event Player)" in rule.body
        )
        mutations = (
            ("Event Player.IndeksWarna = 1;", "Event Player.IndeksWarna = 2;"),
            ("Event Player.KursorWarna = 1;", "Event Player.KursorWarna = 2;"),
            ("Event Player.IndeksIkon = 23;", "Event Player.IndeksIkon = 22;"),
            ("Event Player.KursorIkon = 23;", "Event Player.KursorIkon = 22;"),
        )
        for old, new in mutations:
            with self.subTest(field=old):
                self.assert_rejected(
                    self.replace_in_rule(classifier, old, new),
                    "blocco default isolato",
                )

    def test_special_player_matcher_must_follow_bot_exclusion(self) -> None:
        classifier = self.rule(
            lambda rule: "Append To Array(Global.PemainManusia, Event Player)" in rule.body
        )
        marker = classifier.body.index('Custom String("งูแท้")')
        spans = [
            span for span in validator.conditional_branch_spans(classifier.body)
            if span[0] <= marker < span[1]
        ]
        self.assertTrue(spans)
        start, end = min(spans, key=lambda span: span[1] - span[0])
        profile_branch = classifier.body[start:end]
        without_profile = classifier.body[:start] + classifier.body[end:]
        bot_start = without_profile.index("If(Event Player.BotOtomatis == True);")
        moved = (
            without_profile[:bot_start]
            + profile_branch
            + "\n\t\t"
            + without_profile[bot_start:]
        )
        mutated = self.source[:classifier.start] + moved + self.source[classifier.end:]
        self.assert_rejected(mutated, "matcher deve seguire esclusione/Abort degli iBot")

    def test_special_player_catalog_mappings_are_guarded(self) -> None:
        mutations = (
            (
                self.source.replace(
                    'Custom String("Lowercase")',
                    'Custom String("Caladan Brood")',
                    1,
                ),
                "Caladan Brood inserito nei 100 generi ordinari",
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
            lambda rule: "Event Player.HudPemainDibuat = True;" in rule.body
            and "Event Player.HudKanan = Last Text ID;" in rule.body
        )
        roster_mutation = self.replace_in_rule(
            roster,
            "Event Player.MusikKhusus != Null ? Event Player.MusikKhusus : Event Player.IndeksGenre",
            "Event Player.MusikKhusus == Null ? Event Player.MusikKhusus : Event Player.IndeksGenre",
        )
        self.assert_rejected(roster_mutation, "profilo speciale roster: condizione profilo speciale")

        main = self.rule(lambda rule: validator.subroutine_target(rule) == "GambarUtama")
        main_mutation = self.replace_in_rule(
            main,
            'Custom String("2 - MUSIK\\nSAAT INI: {0}", Event Player.MusikKhusus != Null',
            'Custom String("2 - MUSIK\\nSAAT INI: {0}", Event Player.MusikKhusus == Null',
        )
        self.assert_rejected(main_mutation, "profilo speciale menu principale: condizione profilo speciale")

        music = self.rule(lambda rule: validator.subroutine_target(rule) == "GambarMusik")
        locked_mutation = self.replace_in_rule(
            music,
            'Custom String("เพลงถูกล็อก\\nปัจจุบัน: {0}", Event Player.MusikKhusus)',
            'Custom String("เพลงถูกล็อก\\nตอนนี้: {0}", Event Player.MusikKhusus)',
        )
        self.assert_rejected(locked_mutation, "testo locked")

    def test_special_player_music_navigation_guards_are_required(self) -> None:
        navigation = self.rule(
            lambda rule: "Event Player.PerintahMenu == 3" in rule.body
            and "Event Player.PerintahMenu == 4" in rule.body
            and "Event Player.KursorGenre = (Event Player.KursorGenre" in rule.body
        )
        plus_minus_one = self.replace_in_rule(
            navigation,
            "Else If(And(Event Player.HalamanMenu == 2, Event Player.MusikKhusus == Null));",
            "Else If(Event Player.HalamanMenu == 2);",
        )
        self.assert_rejected(plus_minus_one, "guardia Soundtrack ±1")

        jump = self.rule(
            lambda rule: "Event Player.PerintahMenu == 5" in rule.body
            and "Event Player.PerintahMenu == 6" in rule.body
            and "Event Player.KursorGenre = (Event Player.KursorGenre" in rule.body
        )
        plus_minus_ten = self.replace_in_rule(
            jump,
            "\n\t\tEvent Player.MusikKhusus == Null;",
            "",
        )
        self.assert_rejected(plus_minus_ten, "guardia Soundtrack ±10")

        apply_music = self.rule(
            lambda rule: validator.subroutine_target(rule) == "TerapkanHalamanMusik"
        )
        apply_mutation = self.replace_in_rule(
            apply_music,
            "Abort If(Event Player.MusikKhusus != Null);",
            "Abort If(False);",
        )
        self.assert_rejected(apply_mutation, "deve iniziare con la guardia locked")

    def test_special_player_writer_ownership_is_guarded(self) -> None:
        main = self.rule(lambda rule: validator.subroutine_target(rule) == "GambarUtama")
        mutations = (
            (
                self.inject_action(main, "Global.PemainAktif.MusikKhusus = Null;"),
                "writer property MusikKhusus",
            ),
            (
                self.inject_action(
                    main,
                    "Chase Player Variable At Rate(Event Player, MusikKhusus, 1, 1);",
                ),
                "writer azione inattesi MusikKhusus",
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
        valid_name = "TerapkanTeleportasiJongkok"
        overlong_name = "TerapkanHalamanTeleportasiJongkok"
        self.assertLessEqual(len(valid_name.encode("utf-8")), validator.MAX_DECLARATION_NAME_BYTES)
        self.assertGreater(len(overlong_name.encode("utf-8")), validator.MAX_DECLARATION_NAME_BYTES)
        mutated = self.source.replace(valid_name, overlong_name)
        self.assert_rejected(
            mutated,
            "nome subroutine oltre 32 byte UTF-8: indice 42, TerapkanHalamanTeleportasiJongkok",
        )

    def test_player_variable_name_over_32_utf8_bytes_is_rejected(self) -> None:
        valid_name = "DaftarTargetTeleportasi"
        overlong_name = "DaftarTargetTeleportasiSekarangXX"
        self.assertEqual(len(overlong_name.encode("utf-8")), validator.MAX_DECLARATION_NAME_BYTES + 1)
        mutated = self.source.replace(valid_name, overlong_name)
        self.assert_rejected(
            mutated,
            "nome player oltre 32 byte UTF-8: indice 36, DaftarTargetTeleportasiSekarangXX",
        )

    def test_declaration_name_at_32_utf8_bytes_is_accepted(self) -> None:
        valid_name = "TargetBalasDendamDipilih"
        boundary_name = "TargetBalasDendamDipilihSekarang"
        self.assertEqual(len(boundary_name.encode("utf-8")), validator.MAX_DECLARATION_NAME_BYTES)
        mutated = self.source.replace(valid_name, boundary_name)
        self.assertEqual(self.errors(mutated), [])

    def test_write_only_variable_is_rejected(self) -> None:
        mutated = self.source.replace("Global.PemainAktif.WaktuMasuk", "Total Time Elapsed")
        self.assert_rejected(mutated, "soltanto inizializzata")

    def test_undeclared_global_property_is_rejected(self) -> None:
        mutated = self.replace_once("Global.RGB =", "Global.WarnaTakDideklarasikan =")
        self.assert_rejected(mutated, "Global non dichiarato")

    def test_undeclared_player_property_is_rejected(self) -> None:
        mutated = self.replace_once("Event Player.MenuTerbuka", "Event Player.StatusTakDideklarasikan")
        self.assert_rejected(mutated, "player non dichiarato")

    def test_undeclared_player_variable_action_argument_is_rejected(self) -> None:
        mutated = self.replace_once(
            "Set Player Variable(Global.PemainAktif, MenitLobi,",
            "Set Player Variable(Global.PemainAktif, MenitTakDideklarasikan,",
        )
        self.assert_rejected(mutated, "player non dichiarato")

    def test_every_player_variable_is_initialized_in_setup(self) -> None:
        setup = self.rule(lambda rule: validator.subroutine_target(rule) == "SiapkanPemain")
        mutated = self.replace_in_rule(setup, "\n\t\tEvent Player.WaktuMasuk = Total Time Elapsed;", "")
        self.assert_rejected(mutated, "non inizializzata in SiapkanPemain")

    def test_removed_teks_diri_leaves_compact_initialized_declarations(self) -> None:
        _, players, _, _ = validator.declaration_entries(self.source)
        self.assertNotIn("TeksDiri", {entry.name for entry in players})
        self.assertEqual([entry.index for entry in players], list(range(len(players))))
        self.assertFalse(any("non inizializzata in SiapkanPemain" in error for error in self.errors(self.source)))

    def test_teks_diri_would_be_rejected_if_only_declared_and_initialized(self) -> None:
        mutated = self.add_player_declaration_and_setup_init("TeksDiri", "Null")
        self.assert_rejected(mutated, "soltanto inizializzata/pulita e mai letta: TeksDiri")

    def test_teks_diri_init_cleanup_and_counting_still_is_dead_legacy_state(self) -> None:
        mutated = self.add_player_declaration_and_setup_init("TeksDiri", "Null")
        cleanup = next(
            rule for rule in validator.extract_rules(mutated)
            if validator.subroutine_target(rule) == "BersihkanPemain"
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
        setup = self.rule(lambda rule: validator.subroutine_target(rule) == "SiapkanPemain")
        mutated = self.inject_action(setup, "Event Player.MenuTerbuka = Event Player.MenuTerbuka;")
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
        mutated = self.source.replace("IndeksPemilih", "IndeksVote")
        self.assert_rejected(mutated, "IndeksVote")

    def test_icon_localization_triplet_is_required(self) -> None:
        mutated = self.source.replace("NamaIkonThai", "NamaIkonSiam")
        self.assert_rejected(mutated, "NamaIkonThai")

    def test_icon_localization_requires_exactly_37_entries(self) -> None:
        items = validator.array_assignment_items(self.source, "NamaIkonInggris")
        self.assertIsNotNone(items)
        self.assertEqual(len(items), 37)
        assignment = self.source.index("Global.NamaIkonInggris = Array(")
        opening = self.source.index("(", assignment)
        closing = validator.matching_parenthesis(self.source, opening)
        body = self.source[opening + 1:closing]
        last = body.rfind((items or [])[-1])
        comma = body.rfind(",", 0, last)
        self.assertGreaterEqual(comma, 0)
        shorter_body = body[:comma] + body[last + len((items or [])[-1]):]
        mutated = self.source[:opening + 1] + shorter_body + self.source[closing:]
        self.assert_rejected(mutated, "numero voci NamaIkonInggris")

    def test_icon_arrays_follow_runtime_language_branches(self) -> None:
        token = "Global.NamaIkonIndonesia[Event Player.IndeksIkon]"
        self.assertIn(token, self.source)
        mutated = self.source.replace(token, "Global.NamaIkonInggris[Event Player.IndeksIkon]", 1)
        self.assertIn("Global.NamaIkonIndonesia = Array(", mutated)
        self.assert_rejected(mutated, "ramo IndeksBahasa 1 usa array icone errato")

    def test_location_arrays_follow_runtime_language_branches(self) -> None:
        token = "Global.NamaLokasiIndonesia[Global.IndeksLokasiServer]"
        self.assertIn(token, self.source)
        mutated = self.source.replace(token, "Global.NamaLokasiInggris[Global.IndeksLokasiServer]", 1)
        self.assertIn("Global.NamaLokasiIndonesia = Array(", mutated)
        self.assert_rejected(mutated, "ramo IndeksBahasa 1 usa array località errato")

    def test_small_message_without_three_languages_is_rejected(self) -> None:
        call = next(iter(validator.iter_calls(self.source, "Small Message")))
        self.assertIn("IndeksBahasa", call.args[1])
        mutated = self.replace_call_argument(call, 1, 'Custom String("ONLY ENGLISH")')
        self.assert_rejected(mutated, "Small Message senza traduzione")

    def test_placeholder_out_of_range_is_rejected(self) -> None:
        mutated = self.replace_once('Custom String("{0}"', 'Custom String("{1}"')
        self.assert_rejected(mutated, "placeholder fuori intervallo")

    def test_placeholder_parity_across_languages_is_required(self) -> None:
        call = next(
            call for call in validator.iter_calls(self.source, "Small Message")
            if validator.language_triads(call.args[1])
            and all(validator.outer_format_signature(branch) is not None for branch in validator.language_triads(call.args[1])[0])
            and bool(validator.outer_format_signature(validator.language_triads(call.args[1])[0][0]))
        )
        english, indonesian, thai = validator.language_triads(call.args[1])[0]
        self.assertIn("{0}", indonesian)
        changed_indonesian = indonesian.replace("{0}", "{0}{0}", 1)
        changed_expr = call.args[1].replace(indonesian, changed_indonesian, 1)
        mutated = self.replace_call_argument(call, 1, changed_expr)
        self.assert_rejected(mutated, "parità placeholder")

    def test_hud_header_must_be_null(self) -> None:
        call = next(iter(validator.iter_calls(self.source, "Create HUD Text")))
        mutated = self.replace_call_argument(call, 1, 'Custom String("TITLE")')
        self.assert_rejected(mutated, "Header Create HUD Text")

    def test_big_message_is_rejected(self) -> None:
        mutated = self.source + "\nBig Message(All Players(All Teams), Custom String(\"TITLE\"));\n"
        self.assert_rejected(mutated, "Big Message")

    def test_single_menu_handle_is_required(self) -> None:
        mutated = self.source.replace("HudMenu", "HudMenuArcade")
        self.assert_rejected(mutated, "HudMenuArcade")

    def test_hidden_or_preloaded_menu_hud_is_rejected(self) -> None:
        renderer = self.rule(lambda rule: validator.subroutine_target(rule) == "GambarUtama")
        call = next(iter(validator.iter_calls(renderer.body, "Create HUD Text")))
        absolute_call = validator.Call(call.name, call.raw, call.args, renderer.start + call.start, renderer.start + call.end)
        mutated = self.replace_call_argument(absolute_call, 0, "Empty Array")
        self.assert_rejected(mutated, "nascosto/precaricato")

    def test_global_hud_must_not_repeat_the_menu_modifier_explanation(self) -> None:
        mutated = self.replace_once(
            '"Hold {0}: inspect hero + HP"',
            '"Hold {0}: inspect hero + HP | in menu: modifier for every command"',
        )
        self.assert_rejected(mutated, "clausola modifier Crouch duplicata")

    def test_every_menu_keeps_the_trilingual_crouch_instruction(self) -> None:
        renderer = self.rule(lambda rule: validator.subroutine_target(rule) == "GambarUtama")
        mutated = self.replace_in_rule(renderer, "Hold CROUCH + command", "Hold DUCK + command")
        self.assert_rejected(mutated, "istruzione Crouch menu assente")

    def test_menu_instruction_cannot_start_with_an_artificial_blank_line(self) -> None:
        renderer = self.rule(lambda rule: validator.subroutine_target(rule) == "GambarUtama")
        mutated = self.replace_in_rule(renderer, "Hold CROUCH + command", "\\nHold CROUCH + command")
        self.assert_rejected(mutated, "riga vuota artificiale")

    def test_revenge_no_target_branch_keeps_trilingual_crouch_help(self) -> None:
        renderer = self.rule(lambda rule: validator.subroutine_target(rule) == "GambarBalasDendam")
        call = next(iter(validator.iter_calls(renderer.body, "Create HUD Text")))
        branches = validator.parse_top_level_ternary(call.args[2])
        self.assertIsNotNone(branches)
        _, no_targets, _ = branches  # type: ignore[misc]
        changed_branch = no_targets.replace("Hold CROUCH + command", "Hold DUCK + command", 1)
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
            "Global.SlotHUDTersedia = Array(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11);",
            "Global.SlotHUDTersedia = Array(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12);",
        )
        self.assert_rejected(mutated, "slot HUD roster devono essere esattamente 0..11")

    def test_chill_grid_rejects_an_eleventh_fixed_hud(self) -> None:
        init = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Global"
            and "CHILL DEDICATED SERVER" in rule.body
            and "Global.Siap = True;" in rule.body
        )
        extra = (
            'Create HUD Text(Global.PemainManusia, Null, Null, Custom String("  "), Top, 4, '
            'Color(White), Color(White), Color(White), Visible To and String, Visible Never);'
        )
        mutated = self.inject_action(init, extra)
        self.assert_rejected(mutated, "numero HUD fissi nella regola iniziale")

    def test_chill_grid_rejects_a_thirteenth_global_hud_outside_initialization(self) -> None:
        scheduler = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Global"
            and "Global.LangkahPenjadwal" in rule.body
        )
        extra = (
            'Create HUD Text(Global.PemainManusia, Null, Null, Custom String("  "), Top, 99, '
            'Color(White), Color(White), Color(White), Visible To and String, Visible Never);'
        )
        mutated = self.inject_action(scheduler, extra)
        self.assert_rejected(mutated, "numero HUD globali: dieci fissi e due roster")

    def test_diagnostic_fixed_hud_baseline_cannot_be_satisfied_by_a_comment(self) -> None:
        token = "10 + Count Of(Filtered Array(Global.HudKiriPemain"
        mutated = self.replace_once(token, "9 + Count Of(Filtered Array(Global.HudKiriPemain")
        comment_anchor = '"Urutan ini sengaja bergerak dari paling tenang ke paling kacau. Jangan diacak tanpa alasan yang sangat musikal."'
        self.assertIn(comment_anchor, mutated)
        mutated = mutated.replace(comment_anchor, f'"{token}"\n\t\t{comment_anchor}', 1)
        self.assert_rejected(mutated, "diagnostica HUD non include i dieci handle fissi")

    def test_left_roster_rows_start_immediately_below_their_label(self) -> None:
        renderer = self.rule(lambda rule: "Event Player.HudKiri = Last Text ID;" in rule.body)
        mutated = self.replace_in_rule(renderer, "1 + Event Player.UrutanHUD", "2 + Event Player.UrutanHUD")
        self.assert_rejected(mutated, "renderer HUD roster Left: ordinamento")

    def test_right_roster_stays_before_the_native_team_status_indicator(self) -> None:
        renderer = self.rule(lambda rule: "Event Player.HudKanan = Last Text ID;" in rule.body)
        mutated = self.replace_in_rule(renderer, "-13 + Event Player.UrutanHUD", "1 + Event Player.UrutanHUD")
        self.assert_rejected(mutated, "renderer HUD roster Right: ordinamento")

    def test_right_grid_requires_the_post_roster_spacer(self) -> None:
        call = next(
            call for call in validator.iter_calls(self.source, "Create HUD Text")
            if len(call.args) >= 6
            and call.args[4].strip() == "Right"
            and call.args[5].strip() == "-1"
        )
        mutated = self.replace_call_argument(call, 3, "Null")
        self.assert_rejected(mutated, "HUD fisso Right sort -1: contenuto text errato")

    def test_right_post_roster_spacer_must_be_unconditional(self) -> None:
        call = next(
            call for call in validator.iter_calls(self.source, "Create HUD Text")
            if len(call.args) >= 6
            and call.args[4].strip() == "Right"
            and call.args[5].strip() == "-1"
        )
        mutated = self.replace_call_argument(call, 3, 'True ? Custom String("  ") : Null')
        self.assert_rejected(mutated, "HUD fisso Right sort -1: contenuto text errato")

    def test_left_roster_text_cannot_reintroduce_the_client_zero(self) -> None:
        renderer = self.rule(lambda rule: "Event Player.HudKiri = Last Text ID;" in rule.body)
        call = next(
            call for call in validator.iter_calls(renderer.body, "Create HUD Text")
            if len(call.args) >= 6 and call.args[4].strip() == "Left"
        )
        absolute = validator.Call(call.name, call.raw, call.args, renderer.start + call.start, renderer.start + call.end)
        mutated = self.replace_call_argument(
            absolute,
            3,
            'Global.DiagnostikPerforma == True ? Custom String("diagnostics") : Null',
        )
        self.assert_rejected(mutated, "Text deve essere Null per evitare lo zero client")

    def test_left_diagnostics_remain_inside_the_subheader(self) -> None:
        mutated = self.replace_once('Custom String("{0}{1}{2}"', 'Custom String("{0}{1}"')
        self.assert_rejected(mutated, "diagnostica non integrata nel Subheader")

    def test_left_diagnostic_fallback_is_an_empty_string_not_null(self) -> None:
        renderer = self.rule(lambda rule: "Event Player.HudKiri = Last Text ID;" in rule.body)
        call = next(
            call for call in validator.iter_calls(renderer.body, "Create HUD Text")
            if len(call.args) >= 6 and call.args[4].strip() == "Left"
        )
        outer = next(
            custom for custom in validator.iter_calls(call.args[2], "Custom String")
            if len(custom.args) == 4 and validator.parse_literal(custom.args[0]) == "{0}{1}{2}"
        )
        diagnostic = outer.args[3]
        self.assertTrue(diagnostic.rstrip().endswith('Custom String("")'))
        changed_diagnostic = diagnostic.rsplit('Custom String("")', 1)[0] + "Null"
        changed_subheader = call.args[2][:outer.start] + outer.raw.replace(diagnostic, changed_diagnostic, 1) + call.args[2][outer.end:]
        absolute = validator.Call(call.name, call.raw, call.args, renderer.start + call.start, renderer.start + call.end)
        mutated = self.replace_call_argument(absolute, 2, changed_subheader)
        self.assert_rejected(mutated, "fallback diagnostica deve essere stringa vuota")

    def test_complete_global_control_help_is_required(self) -> None:
        mutated = self.replace_once("Hold {0}: inspect hero + HP", "Hold {0}:")
        self.assert_rejected(mutated, "testo localizzato assente: Hold {0}: inspect hero + HP")

    def test_left_global_control_help_keeps_its_crouch_binding_in_every_language(self) -> None:
        call = next(
            call for call in validator.iter_calls(self.source, "Create HUD Text")
            if len(call.args) >= 6
            and call.args[4].strip() == "Left"
            and call.args[5].strip() == "-2"
        )
        changed_subheader = call.args[2].replace("Button(Crouch)", "Button(Melee)", 1)
        self.assertNotEqual(changed_subheader, call.args[2])
        mutated = self.replace_call_argument(call, 2, changed_subheader)
        self.assert_rejected(mutated, "HUD comando Left EN: binding Crouch ordinato")

    def test_right_global_control_help_keeps_both_bindings(self) -> None:
        call = next(
            call for call in validator.iter_calls(self.source, "Create HUD Text")
            if len(call.args) >= 6
            and call.args[4].strip() == "Right"
            and call.args[5].strip() == "-16"
        )
        changed_subheader = call.args[2].replace(
            "Input Binding String(Button(Melee)), Input Binding String(Button(Interact))",
            "Input Binding String(Button(Interact)), Input Binding String(Button(Melee))",
            1,
        )
        self.assertNotEqual(changed_subheader, call.args[2])
        mutated = self.replace_call_argument(call, 2, changed_subheader)
        self.assert_rejected(mutated, "HUD comando Right EN: binding Melee/Interact ordinati")

    def test_menu_renderers_use_the_top_three_slot(self) -> None:
        renderer = self.rule(lambda rule: validator.subroutine_target(rule) == "GambarUtama")
        call = next(iter(validator.iter_calls(renderer.body, "Create HUD Text")))
        absolute = validator.Call(call.name, call.raw, call.args, renderer.start + call.start, renderer.start + call.end)
        mutated = self.replace_call_argument(absolute, 5, "100")
        self.assert_rejected(mutated, "GambarUtama: ordinamento HUD menu")

    def test_luck_effect_uses_the_same_top_three_slot_without_a_leading_gap(self) -> None:
        renderer = self.rule(lambda rule: "Event Player.HudEfekNasib = Last Text ID;" in rule.body)
        call = next(iter(validator.iter_calls(renderer.body, "Create HUD Text")))
        absolute = validator.Call(call.name, call.raw, call.args, renderer.start + call.start, renderer.start + call.end)
        mutated = self.replace_call_argument(absolute, 5, "-99")
        self.assert_rejected(mutated, "HUD effetto Try Your Luck: ordinamento")

    def test_primary_secondary_must_not_redraw_menu(self) -> None:
        rule = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Each Player" and "PerintahMenu" in rule.body and "Button(Primary Fire)" in rule.body)
        mutated = self.inject_action(rule, "Destroy HUD Text(Event Player.HudMenu);")
        self.assert_rejected(mutated, "Primary/Secondary")

    def test_all_thirteen_pages_are_routed(self) -> None:
        router = self.rule(lambda rule: validator.subroutine_target(rule) == "GambarHalamanAktif")
        mutated = self.replace_in_rule(router, "HalamanMenu == 12", "HalamanMenu == 13")
        self.assert_rejected(mutated, "pagina 12")

    def test_main_menu_cycles_exactly_over_pages_zero_through_twelve(self) -> None:
        navigation = self.rule(
            lambda rule: "Event Player.KursorUtama = (Event Player.KursorUtama" in rule.body
        )
        mutated = self.replace_in_rule(
            navigation,
            "(Event Player.PerintahMenu == 3 ? 1 : 12)) % 13;",
            "(Event Player.PerintahMenu == 3 ? 1 : 11)) % 12;",
        )
        self.assert_rejected(mutated, "ciclo esatto 0..12")

    def test_soundtrack_ability_latch_arms_only_on_page_two(self) -> None:
        router = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Event Player.PerintahMenu == 0;" in rule.body
            and "Event Player.PerintahMenu = 5;" in rule.body
            and "Event Player.PerintahMenu = 6;" in rule.body
        )
        mutated = self.replace_in_rule(
            router,
            "And(Event Player.HalamanMenu == 2, Or(Is Button Held(Event Player, Button(Ability 1)), Is Button Held(Event Player, Button(Ability 2))))",
            "And(Event Player.HalamanMenu == 0, Or(Is Button Held(Event Player, Button(Ability 1)), Is Button Held(Event Player, Button(Ability 2))))",
        )
        self.assert_rejected(mutated, "Ability 1/2 devono armarsi sulla pagina 2 Soundtrack")

    def test_soundtrack_ability_commands_are_emitted_on_page_two(self) -> None:
        router = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Event Player.PerintahMenu = 5;" in rule.body
            and "Event Player.PerintahMenu = 6;" in rule.body
        )
        mutated = self.replace_in_rule(
            router,
            "Else If(And(Is Button Held(Event Player, Button(Ability 1)), Event Player.HalamanMenu == 2));",
            "Else If(And(Is Button Held(Event Player, Button(Ability 1)), Event Player.HalamanMenu == 0));",
        )
        self.assert_rejected(mutated, "Ability 1 non produce il comando 5 sulla pagina 2 Soundtrack")

    def test_soundtrack_jump_consumes_commands_on_page_two(self) -> None:
        jump = self.rule(
            lambda rule: "Event Player.KursorGenre = (Event Player.KursorGenre" in rule.body
            and "Event Player.PerintahMenu == 5" in rule.body
            and "Event Player.PerintahMenu == 6" in rule.body
        )
        mutated = self.replace_in_rule(
            jump,
            "Event Player.HalamanMenu == 2;",
            "Event Player.HalamanMenu == 0;",
        )
        self.assert_rejected(mutated, "salto Soundtrack ±10 deve consumare i comandi sulla pagina 2")

    def test_menu_open_message_announces_thirteen_pages_in_all_languages(self) -> None:
        translations = (
            (
                "Arcade Menu online. Thirteen extremely important decisions await.",
                "Arcade Menu online. Twelve extremely important decisions await.",
            ),
            (
                "Menu Arcade online. Tiga belas keputusan yang sangat penting menunggu.",
                "Menu Arcade online. Dua belas keputusan yang sangat penting menunggu.",
            ),
            (
                "เปิดเมนูอาร์เคดแล้ว มีสิบสามตัวเลือกสำคัญรอคุณอยู่",
                "เปิดเมนูอาร์เคดแล้ว มีสิบสองตัวเลือกสำคัญรอคุณอยู่",
            ),
        )
        for current, legacy in translations:
            with self.subTest(language=current):
                mutated = self.replace_once(current, legacy)
                self.assert_rejected(mutated, "messaggio apertura menu a 13 pagine assente")

    def test_menu_open_message_rejects_legacy_twelve_page_wording(self) -> None:
        for legacy in (
            "Twelve extremely important decisions",
            "Dua belas keputusan",
            "มีสิบสองตัวเลือก",
        ):
            with self.subTest(legacy=legacy):
                mutated = self.source + f"\n// {legacy}\n"
                self.assert_rejected(mutated, "messaggio apertura menu ancora fermo a 12")

    def test_page_twelve_navigation_toggles_dummy_follow_cursor(self) -> None:
        navigation = self.rule(
            lambda rule: "Event Player.KursorUtama = (Event Player.KursorUtama" in rule.body
        )
        mutated = self.replace_in_rule(
            navigation,
            "Event Player.KursorIkutiDummy = (Event Player.KursorIkutiDummy + 1) % 2;",
            "Event Player.KursorIkutiDummy = Event Player.KursorIkutiDummy;",
        )
        self.assert_rejected(mutated, "pagina 12 deve alternare KursorIkutiDummy")

    def test_opening_page_twelve_syncs_preview_with_applied_preference(self) -> None:
        dispatcher = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Event Player.PerintahMenu == 1;" in rule.body
            and "TerapkanHalamanIkutiDummy" in rule.body
        )
        mutated = self.replace_in_rule(
            dispatcher,
            "Event Player.KursorIkutiDummy = Event Player.IzinkanDummyMengikuti ? 1 : 0;",
            "Event Player.KursorIkutiDummy = 0;",
        )
        self.assert_rejected(mutated, "apertura pagina 12 non sincronizza")

    def test_page_twelve_apply_dispatcher_is_required(self) -> None:
        dispatcher = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Event Player.PerintahMenu == 1;" in rule.body
            and "TerapkanHalamanIkutiDummy" in rule.body
        )
        mutated = self.replace_in_rule(
            dispatcher,
            "Call Subroutine(TerapkanHalamanIkutiDummy);",
            "Abort;",
        )
        self.assert_rejected(mutated, "pagina 12 deve usare TerapkanHalamanIkutiDummy")

    def test_dummy_follow_renderer_is_localized_and_explicitly_enemy_scoped(self) -> None:
        renderer = self.rule(lambda rule: validator.subroutine_target(rule) == "GambarIkutiDummy")
        mutated = self.replace_in_rule(renderer, "DUMMY MUSUH", "DUMMY")
        self.assert_rejected(mutated, "DUMMY MUSUH")

    def test_page_twelve_has_a_dedicated_menu_tint(self) -> None:
        transition = self.rule(lambda rule: validator.subroutine_target(rule) == "TransisiWarnaMenu")
        mutated = self.replace_in_rule(
            transition,
            "Event Player.HalamanMenu) == 12 ?",
            "Event Player.HalamanMenu) == 13 ?",
        )
        self.assert_rejected(mutated, "pagina 12 Dummy Follow non ha una tinta")

    def test_dummy_follow_state_cannot_be_written_by_camera_or_other_features(self) -> None:
        camera_release = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Event Player.InteraksiKameraDipakai = False;" in rule.body
        )
        mutated = self.inject_action(camera_release, "Event Player.IzinkanDummyMengikuti = False;")
        self.assert_rejected(mutated, "scritto fuori da setup/apply/quiete")

    def test_dummy_follow_defaults_to_off(self) -> None:
        setup = self.rule(lambda rule: validator.subroutine_target(rule) == "SiapkanPemain")
        for current, wrong in (
            (
                "Event Player.IzinkanDummyMengikuti = False;",
                "Event Player.IzinkanDummyMengikuti = True;",
            ),
            (
                "Event Player.KursorIkutiDummy = 0;",
                "Event Player.KursorIkutiDummy = 1;",
            ),
        ):
            mutated = self.replace_in_rule(setup, current, wrong)
            self.assert_rejected(mutated, "reset setup iniziale mancante")

    def test_interact_dispatch_is_split_into_page_handlers(self) -> None:
        mutated = self.source.replace("TerapkanHalamanIkon", "TerapkanIkonLegacy")
        self.assert_rejected(mutated, "13 subroutine pagina")

    def test_menu_dispatch_requires_crouch(self) -> None:
        dispatcher = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Each Player" and "PerintahMenu" in rule.body and "Button(Ability 2)" in rule.body)
        mutated = self.replace_in_rule(dispatcher, "Is Button Held(Event Player, Button(Crouch)) == True;", "Is Button Held(Event Player, Button(Crouch)) == False;")
        self.assert_rejected(mutated, "modificatore Crouch")

    def test_menu_dispatch_rejects_interact_already_consumed_by_camera(self) -> None:
        dispatcher = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Each Player" and "PerintahMenu" in rule.body and "Button(Ability 2)" in rule.body)
        mutated = self.replace_in_rule(
            dispatcher,
            "Event Player.InteraksiKameraDipakai == False;",
            "Event Player.InteraksiKameraDipakai == True;",
        )
        self.assert_rejected(mutated, "non blocca Interact già consumato")

    def test_menu_interact_acquires_the_shared_camera_latch(self) -> None:
        dispatcher = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Each Player" and "PerintahMenu" in rule.body and "Button(Ability 2)" in rule.body)
        mutated = self.replace_in_rule(
            dispatcher,
            "Event Player.InteraksiKameraDipakai = True;",
            "Event Player.InteraksiKameraDipakai = False;",
        )
        self.assert_rejected(mutated, "non acquisisce il latch Camera")

    def test_dead_menu_is_frozen(self) -> None:
        dispatcher = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Each Player" and "PerintahMenu" in rule.body and "Button(Ability 2)" in rule.body)
        mutated = self.replace_in_rule(dispatcher, "Is Alive(Event Player) == True;", "Is Alive(Event Player) == False;")
        self.assert_rejected(mutated, "menu morto")

    def test_menu_input_allow_disallow_sets_are_symmetric(self) -> None:
        unlock = self.rule(lambda rule: "Allow Button(Event Player" in rule.body and "InputMenuDikunci" in rule.body and "Crouch" in rule.body)
        mutated = self.replace_in_rule(unlock, "Allow Button(Event Player, Button(Ability 2));", "")
        self.assert_rejected(mutated, "simmetria")

    def test_melee_jump_and_crouch_are_never_locked(self) -> None:
        lock = self.rule(lambda rule: "Disallow Button(Event Player" in rule.body and "InputMenuDikunci" in rule.body)
        mutated = self.inject_action(lock, "Disallow Button(Event Player, Button(Jump));")
        self.assert_rejected(mutated, "Melee, Jump e Crouch")

    def test_camera_is_available_with_the_menu_open_or_closed(self) -> None:
        camera = self.rule(lambda rule: "Button(Interact)" in rule.body and "Wait(0.500, Abort When False)" in rule.body and "ModeKamera" in rule.body)
        self.assertNotIn("MenuTerbuka", validator.mask_strings(camera.body))
        mutated = self.inject_condition(camera, "Event Player.MenuTerbuka == False;")
        self.assert_rejected(mutated, "non deve dipendere dallo stato aperto/chiuso")

    def test_camera_requires_crouch_released_to_avoid_menu_interact_collision(self) -> None:
        camera = self.rule(lambda rule: "Button(Interact)" in rule.body and "Wait(0.500, Abort When False)" in rule.body and "ModeKamera" in rule.body)
        mutated = self.replace_in_rule(
            camera,
            "Is Button Held(Event Player, Button(Crouch)) == False;",
            "Is Button Held(Event Player, Button(Crouch)) == True;",
        )
        self.assert_rejected(mutated, "interferisce con il modificatore Crouch")

    def test_interact_release_resets_the_shared_menu_camera_latch(self) -> None:
        release = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Event Player.InteraksiKameraDipakai == True;" in rule.body
            and "Is Button Held(Event Player, Button(Interact)) == False;" in rule.body
        )
        mutated = self.replace_in_rule(
            release,
            "Event Player.InteraksiKameraDipakai = False;",
            "Event Player.InteraksiKameraDipakai = True;",
        )
        self.assert_rejected(mutated, "rilascio Interact non azzera")

    def test_crouch_inspection_requires_menu_closed(self) -> None:
        inspection = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Each Player" and "InspeksiAktif = True" in rule.body and "Button(Crouch)" in rule.body)
        mutated = self.replace_in_rule(inspection, "Event Player.MenuTerbuka == False;", "Event Player.MenuTerbuka == True;")
        self.assert_rejected(mutated, "inspection/teleport")

    def test_player_death_must_not_close_visible_menu(self) -> None:
        death = self.rule(lambda rule: validator.event_type(rule) == "Player Died")
        mutated = self.inject_action(death, "Call Subroutine(TutupMenu);")
        self.assert_rejected(mutated, "morte non deve chiudere")

    def test_jump_resurrect_is_not_blocked_by_open_menu(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        mutated = self.inject_action(resurrect, "Abort If(Event Player.MenuTerbuka == False);")
        self.assert_rejected(mutated, "Jump Resurrect")

    def test_jump_resurrect_cannot_regress_to_respawn(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        mutated = self.replace_in_rule(
            resurrect,
            "Resurrect(Event Player);",
            "Respawn(Event Player);",
        )
        self.assert_rejected(mutated, "senza azioni Respawn")

    def test_jump_resurrect_teleports_and_confirms_in_same_tick(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        mutated = self.replace_in_rule(
            resurrect,
            "Resurrect(Event Player);\n\t\tTeleport(Event Player, Event Player.PosisiBangkitAman);",
            "Teleport(Event Player, Event Player.PosisiBangkitAman);\n\t\tResurrect(Event Player);",
        )
        self.assert_rejected(mutated, "teletrasportare e confermare")

    def test_jump_resurrect_confirms_success_in_same_tick(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        mutated = self.replace_in_rule(resurrect, "If(Is Alive(Event Player) == True);", "If(True);")
        self.assert_rejected(mutated, "confermare il successo nello stesso tick")

    def test_jump_resurrect_cannot_wait_or_loop(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        for action in ("Wait(0.016, Ignore Condition);", "Loop;"):
            with self.subTest(action=action):
                mutated = self.inject_action(resurrect, action)
                self.assert_rejected(mutated, "senza Wait/Loop")

    def test_jump_resurrect_cannot_rearm_during_same_press(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        mutated = self.inject_action(resurrect, "Event Player.BangkitLompatDipakai = False;")
        self.assert_rejected(mutated, "non deve riarmarsi durante la stessa pressione")

    def test_failed_jump_resurrect_releases_latch_only_after_jump_release(self) -> None:
        release = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Is Button Held(Event Player, Button(Jump)) == False;" in rule.body
            and "Event Player.BangkitLompatDipakai = False;" in rule.body
        )
        mutated = self.replace_in_rule(
            release,
            "Is Button Held(Event Player, Button(Jump)) == False;",
            "Is Button Held(Event Player, Button(Jump)) == True;",
        )
        self.assert_rejected(mutated, "rilascio Jump deve riarmare")

    def test_jump_resurrect_release_requires_human_dead_guards(self) -> None:
        release = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Is Button Held(Event Player, Button(Jump)) == False;" in rule.body
            and "Event Player.BangkitLompatDipakai = False;" in rule.body
        )
        for guard in (
            "Event Player.Manusia == True;",
            "Is Dummy Bot(Event Player) == False;",
            "Is Alive(Event Player) == False;",
        ):
            with self.subTest(guard=guard):
                mutated = self.replace_in_rule(release, guard, "")
                self.assert_rejected(mutated, "rilascio latch Resurrect senza guardia")

    def test_full_hp_application_requires_damage_knockback_and_player_phasing(self) -> None:
        apply = self.rule(lambda rule: validator.subroutine_target(rule) == "TerapkanHalamanKebal")
        for token in (
            "Set Damage Received(Event Player, 0);",
            "Set Knockback Received(Event Player, 0);",
            "Disable Movement Collision With Players(Event Player);",
        ):
            with self.subTest(token=token):
                mutated = self.replace_in_rule(apply, token, "")
                self.assert_rejected(mutated, "FULL HP applicazione")

    def test_full_hp_global_reapply_requires_the_complete_protection_triplet(self) -> None:
        processor = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesCepatPemain")
        for token in (
            "Set Damage Received(Global.PemainAktif, 0);",
            "Set Knockback Received(Global.PemainAktif, 0);",
            "Disable Movement Collision With Players(Global.PemainAktif);",
        ):
            with self.subTest(token=token):
                mutated = self.replace_in_rule(processor, token, "")
                self.assert_rejected(mutated, "FULL HP riapplicazione globale")

    def test_full_hp_off_restores_damage_knockback_and_player_collision(self) -> None:
        apply = self.rule(lambda rule: validator.subroutine_target(rule) == "TerapkanHalamanKebal")
        off_anchor = apply.body.index("If(Event Player.ModeKebal == 0);")
        mode_one_anchor = apply.body.index("If(Event Player.ModeKebal == 1);", off_anchor)
        off_body = apply.body[off_anchor:mode_one_anchor]
        self.assertIn("Enable Movement Collision With Players(Event Player);", off_body)
        changed = off_body.replace("Enable Movement Collision With Players(Event Player);", "", 1)
        mutated_body = apply.body[:off_anchor] + changed + apply.body[mode_one_anchor:]
        mutated = self.source[:apply.start] + mutated_body + self.source[apply.end:]
        self.assert_rejected(mutated, "FULL HP uscita OFF")

    def test_try_your_luck_start_preserves_unkillable_preference_and_runtime(self) -> None:
        luck = self.rule(lambda rule: validator.subroutine_target(rule) == "TerapkanHalamanNasib")
        mutations = (
            ("Event Player.ModeKebal = 0;", "non deve modificare ModeKebal"),
            ("Event Player.KursorKebal = 0;", "non deve modificare KursorKebal"),
            ("Event Player.KebalAktif = False;", "non deve modificare KebalAktif"),
            ("Clear Status(Event Player, Unkillable);", "non deve sospendere status Unkillable"),
            ("Set Status(Event Player, Null, Unkillable, 9999);", "non deve sospendere status Unkillable"),
            ("Set Damage Received(Event Player, 100);", "non deve sospendere Damage Received"),
            ("Set Knockback Received(Event Player, 100);", "non deve sospendere Knockback Received"),
            ("Enable Movement Collision With Players(Event Player);", "non deve sospendere collisione player"),
            ("Set Player Health(Event Player, Max Health(Event Player));", "non deve sospendere salute Unkillable"),
            ("Destroy Icon(Event Player.IkonKebal);", "non deve sospendere icona Unkillable"),
        )
        for action, expected in mutations:
            with self.subTest(action=action):
                self.assert_rejected(self.inject_action(luck, action), expected)

    def test_full_hp_shared_cleanup_restores_knockback(self) -> None:
        cleanup = self.rule(lambda rule: validator.subroutine_target(rule) == "PulihkanNasibPemain")
        mutated = self.replace_in_rule(cleanup, "Set Knockback Received(Event Player, 100);", "")
        self.assert_rejected(mutated, "FULL HP cleanup PulihkanNasibPemain")

    def test_luck_cleanup_preserves_mode_and_cursor_and_reactivates_unkillable(self) -> None:
        for subroutine, target in (
            ("PulihkanNasibPemain", "Event Player"),
            ("PulihkanNasibAktif", "Global.PemainAktif"),
        ):
            cleanup = self.rule(lambda rule, name=subroutine: validator.subroutine_target(rule) == name)
            logical_restore = f"{target}.KebalAktif = {target}.ModeKebal != 0;"
            with self.subTest(subroutine=subroutine, mutation="logical restore"):
                mutated = self.replace_in_rule(cleanup, logical_restore, f"{target}.KebalAktif = False;")
                self.assert_rejected(mutated, "deve riattivare logicamente Kebal")
            for field in ("ModeKebal", "KursorKebal"):
                with self.subTest(subroutine=subroutine, field=field):
                    mutated = self.inject_action(cleanup, f"{target}.{field} = 0;")
                    self.assert_rejected(mutated, f"non deve cancellare la preferenza {field}")

    def test_luck_cleanup_reactivates_unkillable_after_engine_normalization(self) -> None:
        cleanup = self.rule(lambda rule: validator.subroutine_target(rule) == "PulihkanNasibPemain")
        clear = "Clear Status(Event Player, Unkillable);"
        restore = "Event Player.KebalAktif = Event Player.ModeKebal != 0;"
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
        renderer = self.rule(lambda rule: validator.subroutine_target(rule) == "GambarUtama")
        mutated = self.inject_action(renderer, "Wait(0.050, Ignore Condition);")
        self.assert_rejected(mutated, "Wait non allowlisted")

    def test_scheduler_cadences_are_required(self) -> None:
        scheduler = self.rule(lambda rule: validator.action_loop_count(rule.body) == 1)
        self.assertIn("LangkahPenjadwal % 20", scheduler.body)
        changed = scheduler.body.replace("LangkahPenjadwal % 20", "LangkahPenjadwal % 21")
        mutated = self.source[:scheduler.start] + changed + self.source[scheduler.end:]
        self.assert_rejected(mutated, "cadenza scheduler %20")

    def test_scheduler_scratch_is_exclusively_written_by_scheduler(self) -> None:
        renderer = self.rule(lambda rule: validator.subroutine_target(rule) == "GambarUtama")
        mutated = self.inject_action(renderer, "Global.PemainAktif = Event Player;")
        self.assert_rejected(mutated, "scrittura PemainAktif")

    def test_scans_cannot_yield(self) -> None:
        scheduler = self.rule(lambda rule: validator.action_loop_count(rule.body) == 1)
        token = "Global.PemainAktif = All Players(All Teams)[Global.IndeksPemainGlobal];"
        mutated = self.replace_in_rule(scheduler, token, token + "\n\t\t\tWait(0.001, Ignore Condition);")
        self.assert_rejected(mutated, "yield durante scansione")

    def test_scheduler_subroutines_have_no_wait_or_loop(self) -> None:
        process = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesCachePemain")
        mutated = self.inject_action(process, "Wait(0.050, Ignore Condition);")
        self.assert_rejected(mutated, "subroutine scheduler")

    def test_try_your_luck_has_exactly_six_outcomes(self) -> None:
        self.assertIn("Random Integer(1, 6)", self.source)
        mutated = self.source.replace("Random Integer(1, 6)", "Random Integer(1, 5)")
        self.assert_rejected(mutated, "sei esiti")

    def test_try_your_luck_skull_arms_full_death_machine(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
        mutated = self.replace_in_rule(
            machine,
            "Global.PemainAktif.WaktuPaksaBerakhir = Total Time Elapsed + 5;",
            "Global.PemainAktif.WaktuPaksaBerakhir = 0;",
        )
        self.assert_rejected(mutated, "Skull non arma deadline anti-blocco")

    def test_burning_temporarily_bypasses_unkillable_and_scales_with_max_health(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
        mutated = self.replace_in_rule(
            machine,
            "Clear Status(Global.PemainAktif, Unkillable);",
            "Clear Status(Global.PemainAktif, Burning);",
        )
        self.assert_rejected(mutated, "Burning deve sospendere Unkillable")

        mutated = self.replace_in_rule(
            machine,
            "Damage(Global.PemainAktif, Global.PemainAktif, Max Health(Global.PemainAktif) * 0.050);",
            "Damage(Global.PemainAktif, Global.PemainAktif, 25);",
        )
        self.assert_rejected(mutated, "5% della Max Health")

        mutated = self.replace_in_rule(
            machine,
            "Global.PemainAktif.WaktuBakarNasibBerikut = Total Time Elapsed + 1.000;",
            "Global.PemainAktif.WaktuBakarNasibBerikut = Total Time Elapsed + 0.500;",
        )
        self.assert_rejected(mutated, "tick da un secondo")
    def test_unkillable_reapply_is_blocked_for_revenge_skull_and_active_burning(self) -> None:
        processor = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesCepatPemain")
        exact_exception = (
            "And(And(Global.PemainAktif.KartuNasibAktif == True, Global.PemainAktif.PutaranKartuNasib == 0), "
            "Or(And(Global.PemainAktif.EfekNasib == 3, Global.PemainAktif.WaktuPaksaBerakhir > 0), "
            "And(Global.PemainAktif.EfekNasib == 5, Global.PemainAktif.EfekNasibBerakhir > Total Time Elapsed))) == False"
        )
        mutated = self.replace_in_rule(
            processor,
            exact_exception,
            "Global.PemainAktif.KartuNasibAktif == False",
        )
        self.assert_rejected(mutated, "blocco riapplicazione Kebal durante Skull/Burning finali")
    def test_global_unkillable_reapply_recreates_missing_or_destroyed_icon(self) -> None:
        processor = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesCepatPemain")
        safe_guard = (
            "If(Or(Global.PemainAktif.IkonKebal == Null, "
            "Entity Exists(Global.PemainAktif.IkonKebal) == False));"
        )
        mutated = self.replace_in_rule(
            processor,
            safe_guard,
            "If(Global.PemainAktif.IkonKebal == Null);",
        )
        self.assert_rejected(mutated, "non ricrea in sicurezza un'icona assente o non più esistente")

        mutated = self.replace_in_rule(
            processor,
            "Create Icon(All Players(All Teams), Global.PemainAktif, Halo, Visible To and Position, Global.RGB, True);",
            "",
        )
        self.assert_rejected(mutated, "deve ricreare le icone 1 HP e FULL HP")

        mutated = self.replace_in_rule(
            processor,
            "Global.PemainAktif.IkonKebal = Last Created Entity;",
            "",
        )
        self.assert_rejected(mutated, "salvataggio handle icona")

    def test_full_death_machine_owns_the_only_kill(self) -> None:
        processor = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesCepatPemain")
        kill = next(iter(validator.iter_calls(processor.body, "Kill")))
        absolute = validator.Call(kill.name, kill.raw, kill.args, processor.start + kill.start, processor.start + kill.end)
        mutated = self.source[:absolute.start] + "" + self.source[absolute.end:]
        self.assert_rejected(mutated, "un solo Kill nel processor globale")

    def test_full_death_kill_branch_requires_a_live_target(self) -> None:
        processor = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesCepatPemain")
        mutated = self.replace_in_rule(
            processor,
            "Else If(And(Has Spawned(Global.PemainAktif) == True, "
            "And(Is Alive(Global.PemainAktif) == True, "
            "Total Time Elapsed >= Global.PemainAktif.WaktuPaksaBerikut)));",
            "Else If(And(Has Spawned(Global.PemainAktif) == True, "
            "And(Is Alive(Global.PemainAktif) == False, "
            "Total Time Elapsed >= Global.PemainAktif.WaktuPaksaBerikut)));",
        )
        self.assert_rejected(mutated, "retry soltanto se ancora vivo nello stesso ramo di Kill")

    def test_revenge_timeout_clears_the_pending_flag(self) -> None:
        processor = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesCepatPemain")
        mutated = self.replace_in_rule(
            processor,
            "Set Player Variable(Global.PemainAktif.PenagihBalasDendam, "
            "TargetBalasDendamTerkunci, Null);\n"
            "\t\t\t\t\tGlobal.PemainAktif.KematianBalasDendam = False;",
            "Set Player Variable(Global.PemainAktif.PenagihBalasDendam, "
            "TargetBalasDendamTerkunci, Null);",
        )
        self.assert_rejected(mutated, "timeout Revenge non azzera flag pending")

    def test_skull_timeout_destroys_the_roulette_icon(self) -> None:
        processor = self.rule(lambda rule: validator.subroutine_target(rule) == "PulihkanNasibAktif")
        mutated = self.replace_in_rule(
            processor,
            "Destroy Icon(Global.PemainAktif.IkonKartuNasib);",
            "",
        )
        self.assert_rejected(mutated, "timeout Skull deve distruggere l'icona")

    def test_skull_cannot_trigger_from_a_transient_roulette_icon(self) -> None:
        processor = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesCepatPemain")
        mutated = self.replace_in_rule(
            processor,
            "And(Global.PemainAktif.PutaranKartuNasib == 0, Global.PemainAktif.WaktuPaksaBerakhir > 0)",
            "True",
        )
        self.assert_rejected(mutated, "Skull finale armato dopo la roulette")

    def test_revenge_cannot_consume_debt_at_click(self) -> None:
        apply = self.rule(lambda rule: validator.subroutine_target(rule) == "TerapkanHalamanBalasDendam")
        mutated = self.inject_action(
            apply,
            "Modify Player Variable At Index(Event Player, JumlahBalasDendam, Event Player.IndeksBalasDendam, Subtract, 1);",
        )
        self.assert_rejected(mutated, "non deve consumare il debito prima della morte completa")

    def test_revenge_commit_requires_actual_death(self) -> None:
        recorder = self.rule(
            lambda rule: validator.event_type(rule) == "Player Died"
            and "PenagihBalasDendam" in rule.body
            and "PembunuhBalasDendam" in rule.body
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
            and "PenagihBalasDendam" in rule.body
            and "PembunuhBalasDendam" in rule.body
        )
        recompute = (
            "Index Of Array Value(Player Variable(Event Player.PenagihBalasDendam, "
            "PembunuhBalasDendam), Event Player)"
        )
        mutated = self.replace_in_rule(recorder, recompute, "Event Player.IndeksBalasDendam")
        self.assert_rejected(mutated, "ricalcolo indice debito al commit")

    def test_revenge_commit_aborts_before_the_natural_recorder(self) -> None:
        recorder = self.rule(
            lambda rule: validator.event_type(rule) == "Player Died"
            and "PenagihBalasDendam" in rule.body
            and "PembunuhBalasDendam" in rule.body
        )
        mutated = self.replace_in_rule(
            recorder,
            "Event Player.WaktuPaksaBerakhir = 0;\n\t\t\t\t\tAbort;",
            "Event Player.WaktuPaksaBerakhir = 0;",
        )
        self.assert_rejected(mutated, "Abort prima del recorder naturale")

    def test_try_your_luck_cleanup_waits_for_full_death(self) -> None:
        cleanup = self.rule(
            lambda rule: validator.event_type(rule) == "Player Died"
            and "KartuNasibAktif" in rule.body
            and "Call Subroutine(PulihkanNasibPemain);" in rule.body
        )
        mutated = self.replace_in_rule(cleanup, "\n\t\tIs Alive(Event Player) == False;", "")
        self.assert_rejected(mutated, "deve attendere la morte completa")

    def test_jump_respawn_prompt_waits_for_full_death(self) -> None:
        death_prompt = self.rule(
            lambda rule: validator.event_type(rule) == "Player Died"
            and "Event Player.PosisiMati = Position Of(Event Player);" in rule.body
            and "Event Player.BangkitLompatDipakai = False;" in rule.body
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
        mutated = self.source.replace("WaktuBakarNasibBerikut", "WaktuBakarLegacy")
        self.assert_rejected(mutated, "WaktuBakarNasibBerikut")

    def test_try_your_luck_state_machine_cannot_wait(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
        mutated = self.inject_action(machine, "Wait(1, Ignore Condition);")
        self.assert_rejected(mutated, "timestamp, non Wait")

    def test_roulette_icons_capture_scheduler_identity_before_position_reevaluation(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
        call = next(iter(validator.iter_calls(machine.body, "Create Icon")))
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        naked_position = call.args[1].replace("Evaluate Once(Global.PemainAktif)", "Global.PemainAktif", 1)
        self.assertNotEqual(naked_position, call.args[1])
        mutated = self.replace_call_argument(absolute, 1, naked_position)
        self.assert_rejected(mutated, "scratch Global.PemainAktif dinamico senza Evaluate Once")

    def test_roulette_icon_position_must_update_every_frame(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
        call = next(iter(validator.iter_calls(machine.body, "Create Icon")))
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        dynamic = next(iter(validator.iter_calls(call.args[1], "Update Every Frame")))
        mutated = self.replace_call_argument(absolute, 1, dynamic.args[0])
        self.assert_rejected(mutated, "posizione fluida Update Every Frame")

    def test_roulette_icon_position_tracks_eye_and_facing_direction(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
        call = next(iter(validator.iter_calls(machine.body, "Create Icon")))
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        changed_position, count = re.subn(
            r"Facing Direction Of\(\s*Evaluate Once\(Global\.PemainAktif\)\s*\)",
            "Vector(0, 0, 1)",
            call.args[1],
            count=1,
        )
        self.assertEqual(count, 1)
        mutated = self.replace_call_argument(absolute, 1, changed_position)
        self.assert_rejected(mutated, "ancoraggio fluido a occhio e mirino")

    def test_roulette_icon_cannot_freeze_the_whole_position_expression(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
        call = next(iter(validator.iter_calls(machine.body, "Create Icon")))
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        dynamic = next(iter(validator.iter_calls(call.args[1], "Update Every Frame")))
        naked_inner = re.sub(
            r"Evaluate Once\(Global\.PemainAktif\)",
            "Global.PemainAktif",
            dynamic.args[0],
        )
        frozen_position = f"Update Every Frame(Evaluate Once({naked_inner}))"
        mutated = self.replace_call_argument(absolute, 1, frozen_position)
        self.assert_rejected(mutated, "catture identità player")

    def test_roulette_icons_are_visible_only_to_humans(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
        call = next(iter(validator.iter_calls(machine.body, "Create Icon")))
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        mutated = self.replace_call_argument(absolute, 0, "All Players(All Teams)")
        self.assert_rejected(mutated, "visibilità riservata agli umani")

    def test_roulette_icons_reevaluate_visibility_and_position(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
        call = next(iter(validator.iter_calls(machine.body, "Create Icon")))
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        mutated = self.replace_call_argument(absolute, 3, "Position")
        self.assert_rejected(mutated, "reevaluation deve essere Visible To and Position")

    def test_roulette_icons_remain_visible_when_offscreen(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
        call = next(iter(validator.iter_calls(machine.body, "Create Icon")))
        self.assertGreaterEqual(len(call.args), 6)
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        mutated = self.replace_call_argument(absolute, 5, "False")
        self.assert_rejected(mutated, "Show When Offscreen deve essere True")

    def test_roulette_icons_cover_each_outcome_once(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
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
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
        mutated = self.replace_in_rule(machine, "Destroy Icon(Global.PemainAktif.IkonKartuNasib);", "")
        self.assert_rejected(mutated, "destroy-before-replace icona roulette")

    def test_roulette_icon_handle_is_stored_immediately_after_creation(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
        store = "Global.PemainAktif.IkonKartuNasib = Last Created Entity;"
        mutated = self.replace_in_rule(
            machine,
            store,
            "Global.PemainAktif.WaktuIkonNasibBerakhir = 0;\n\t\t\t\t" + store,
        )
        self.assert_rejected(mutated, "handle roulette non salvato immediatamente")

    def test_roulette_icon_handle_store_cannot_be_removed(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
        mutated = self.replace_in_rule(
            machine,
            "Global.PemainAktif.IkonKartuNasib = Last Created Entity;",
            "",
        )
        self.assert_rejected(mutated, "salvataggio handle della nuova icona roulette")

    def test_roulette_final_timer_destroys_and_clears_the_icon_handle(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
        final_destroy = machine.body.rfind("Destroy Icon(Global.PemainAktif.IkonKartuNasib);")
        self.assertGreaterEqual(final_destroy, 0)
        changed = machine.body[:final_destroy] + machine.body[final_destroy:].replace(
            "Destroy Icon(Global.PemainAktif.IkonKartuNasib);", "", 1
        )
        mutated = self.source[:machine.start] + changed + self.source[machine.end:]
        self.assert_rejected(mutated, "cleanup finale icona roulette incompleto: Destroy Icon")

        final_null = machine.body.rfind("Global.PemainAktif.IkonKartuNasib = Null;")
        self.assertGreaterEqual(final_null, 0)
        changed = machine.body[:final_null] + machine.body[final_null:].replace(
            "Global.PemainAktif.IkonKartuNasib = Null;", "", 1
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
		Create Icon(Global.PemainManusia, Event Player, Eye, Position, Color(Aqua), True);
		Event Player.IkonKartuNasib = Last Created Entity;
	}
}
'''
        self.assert_rejected(self.source + extra_rule, "global-first, senza regole Each Player")

    def test_luck_acceleration_captures_scheduler_identity(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
        call = next(iter(validator.iter_calls(machine.body, "Start Accelerating")))
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        naked_direction = call.args[1].replace("Evaluate Once(Global.PemainAktif)", "Global.PemainAktif", 1)
        self.assertNotEqual(naked_direction, call.args[1])
        mutated = self.replace_call_argument(absolute, 1, naked_direction)
        self.assert_rejected(mutated, "direzione accelerazione usa scratch Global.PemainAktif senza Evaluate Once")

    def test_luck_acceleration_cannot_freeze_the_facing_vector(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
        call = next(iter(validator.iter_calls(machine.body, "Start Accelerating")))
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        mutated = self.replace_call_argument(
            absolute,
            1,
            "Evaluate Once(Facing Direction Of(Global.PemainAktif))",
        )
        self.assert_rejected(mutated, "accelerazione automatica 3D nella Facing Direction")

    def test_luck_acceleration_uses_automatic_facing_direction(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
        call = next(iter(validator.iter_calls(machine.body, "Start Accelerating")))
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        mutated = self.replace_call_argument(absolute, 1, "Vector(0, 0, 1)")
        self.assert_rejected(mutated, "accelerazione automatica 3D nella Facing Direction")

    def test_luck_acceleration_cannot_depend_on_directional_input(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
        call = next(iter(validator.iter_calls(machine.body, "Start Accelerating")))
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        mutated = self.replace_call_argument(absolute, 1, "Throttle Of(Evaluate Once(Global.PemainAktif))")
        self.assert_rejected(mutated, "dipende da input/impulsi: Throttle Of(")

    def test_luck_acceleration_requires_world_space_and_dynamic_direction(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
        call = next(iter(validator.iter_calls(machine.body, "Start Accelerating")))
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        mutated = self.replace_call_argument(absolute, 4, "To Player")
        self.assert_rejected(mutated, "accelerazione automatica 3D nella Facing Direction")
        mutated = self.replace_call_argument(absolute, 5, "None")
        self.assert_rejected(mutated, "accelerazione automatica 3D nella Facing Direction")

    def test_luck_acceleration_cannot_use_apply_impulse(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
        mutated = self.inject_action(
            machine,
            "Apply Impulse(Global.PemainAktif, Facing Direction Of(Global.PemainAktif), 1, To World, Cancel Contrary Motion);",
        )
        self.assert_rejected(mutated, "non deve simulare l'accelerazione con Apply Impulse")

    def test_luck_acceleration_is_globally_unique(self) -> None:
        quick = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesCepatPemain")
        mutated = self.inject_action(
            quick,
            "Start Accelerating(Global.PemainAktif, Facing Direction Of(Evaluate Once(Global.PemainAktif)), 50, 25, To World, Direction Rate and Max Speed);",
        )
        self.assert_rejected(mutated, "Start Accelerating globale unico")

    def test_luck_acceleration_call_cannot_be_shadowed_by_a_comment(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
        call = next(iter(validator.iter_calls(machine.body, "Start Accelerating")))
        start = machine.start + call.start
        end = machine.start + call.end
        self.assertEqual(self.source[end], ";")
        mutated = self.source[:start] + '"Start Accelerating(Global.PemainAktif, ...)"' + self.source[end + 1:]
        self.assert_rejected(mutated, "Start Accelerating globale unico")

    def test_luck_acceleration_has_its_own_ten_second_timestamp(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
        mutated = self.replace_in_rule(
            machine,
            "Global.PemainAktif.EfekNasibBerakhir = Total Time Elapsed + 10;",
            "Global.PemainAktif.EfekNasibBerakhir = Total Time Elapsed + 9;",
        )
        self.assert_rejected(mutated, "timestamp esatto di 10 secondi")

    def test_luck_expiry_condition_cannot_be_shadowed_by_a_comment(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
        condition = "Total Time Elapsed >= Global.PemainAktif.EfekNasibBerakhir"
        self.assertIn(condition, machine.body)
        changed = machine.body.replace(condition, "False", 1)
        closing = changed.rfind("\n\t}")
        self.assertGreater(closing, 0)
        changed = changed[:closing] + f'\n\t\t"{condition}"' + changed[closing:]
        mutated = self.source[:machine.start] + changed + self.source[machine.end:]
        self.assert_rejected(mutated, "cleanup timestamp Try Your Luck non analizzabile")

    def test_luck_acceleration_expiry_restores_speed_and_stops_acceleration(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
        mutated = self.replace_in_rule(machine, "Stop Accelerating(Global.PemainAktif);", "")
        self.assert_rejected(mutated, "cleanup scadenza accelerazione incompleto: Stop Accelerating")
        mutated = self.replace_in_rule(machine, "Set Move Speed(Global.PemainAktif, 100);", "")
        self.assert_rejected(mutated, "cleanup scadenza accelerazione incompleto: ripristino Move Speed 100")

    def test_luck_acceleration_stop_cannot_be_shadowed_by_a_comment(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
        mutated = self.replace_in_rule(
            machine,
            "Stop Accelerating(Global.PemainAktif);",
            '"Stop Accelerating(Global.PemainAktif);"',
        )
        self.assert_rejected(mutated, "cleanup scadenza accelerazione incompleto: Stop Accelerating")

    def test_luck_acceleration_is_stopped_on_death(self) -> None:
        death_cleanup = self.rule(lambda rule: validator.subroutine_target(rule) == "PulihkanNasibPemain")
        mutated = self.replace_in_rule(death_cleanup, "Stop Accelerating(Event Player);", "")
        self.assert_rejected(mutated, "cleanup accelerazione morte: Stop Accelerating assente")

    def test_roulette_icon_is_destroyed_and_cleared_on_all_lifecycle_paths(self) -> None:
        reset = self.rule(lambda rule: validator.subroutine_target(rule) == "PulihkanNasibPemain")
        mutated = self.replace_in_rule(reset, "Destroy Icon(Event Player.IkonKartuNasib);", "")
        self.assert_rejected(mutated, "cleanup icona roulette morte: Destroy Icon assente")
        mutated = self.replace_in_rule(reset, "Event Player.IkonKartuNasib = Null;", "")
        self.assert_rejected(mutated, "cleanup icona roulette morte: azzeramento handle assente")

    def test_heart_heal_excludes_bot_and_dummy_players(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
        call = next(
            call for call in validator.iter_calls(machine.body, "Set Player Health")
            if len(call.args) >= 2 and call.args[1].strip() == "9999"
        )
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        mutated = self.replace_call_argument(absolute, 0, "All Living Players(Team Of(Global.PemainAktif))")
        self.assert_rejected(mutated, "cura anche bot/dummy")

    def test_heart_message_excludes_bot_and_dummy_players(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
        call = next(
            call for call in validator.iter_calls(machine.body, "Small Message")
            if len(call.args) >= 2 and "HEART" in call.args[1]
        )
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        mutated = self.replace_call_argument(absolute, 0, "All Living Players(Team Of(Global.PemainAktif))")
        self.assert_rejected(mutated, "invia HUD anche a bot/dummy")

    def test_global_lifecycle_dispatch_requires_duplicate_guard(self) -> None:
        fast = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesCepatPemain")
        mutated = self.replace_in_rule(
            fast,
            "Global.PemainAktif.PindahTimDiproses == False",
            "Global.PemainAktif.PindahTimDiproses == True",
        )
        self.assert_rejected(mutated, "dispatcher team-switch leggero")

    def test_global_lifecycle_dispatch_excludes_classified_ibots(self) -> None:
        fast = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesCepatPemain")
        mutated = self.replace_in_rule(
            fast,
            "Global.PemainAktif.BotOtomatis == False",
            "Global.PemainAktif.BotOtomatis == True",
        )
        self.assert_rejected(mutated, "dispatcher team-switch leggero")

    def test_global_lifecycle_dispatch_does_not_abort_refresh_while_waiting_spawn(self) -> None:
        fast = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesCepatPemain")
        mutated = self.inject_action(
            fast,
            "Abort If(Or(Has Spawned(Global.PemainAktif) == False, Is Alive(Global.PemainAktif) == False));",
        )
        self.assert_rejected(mutated, "guardia spawn/hidup")

    def test_leave_cleanup_is_limited_to_the_human_roster(self) -> None:
        left = self.rule(lambda rule: validator.event_type(rule) == "Player Left Match")
        mutated = self.replace_in_rule(
            left,
            "Or(Event Player.Manusia == True, Array Contains(Global.PemainManusia, Event Player))",
            "Event Player.Manusia == False",
        )
        self.assert_rejected(mutated, "Player Left Match deve includere iBot e umani registrati")

    def test_player_left_match_includes_classified_ibots(self) -> None:
        left = self.rule(lambda rule: validator.event_type(rule) == "Player Left Match")
        mutated = self.replace_in_rule(
            left,
            "Or(Event Player.BotOtomatis == True, "
            "Or(Event Player.Manusia == True, Array Contains(Global.PemainManusia, Event Player))) == True;",
            "Or(Event Player.Manusia == True, Array Contains(Global.PemainManusia, Event Player)) == True;",
        )
        self.assert_rejected(mutated, "Player Left Match deve includere iBot e umani registrati")

    def test_ibot_leave_destroys_vision_text_before_human_lifecycle(self) -> None:
        left = self.rule(lambda rule: validator.event_type(rule) == "Player Left Match")
        mutated = self.replace_in_rule(
            left,
            "\n\t\t\t\tDestroy In-World Text(Event Player.TeksVisiNasib);",
            "",
        )
        self.assert_rejected(mutated, "leave iBot deve distruggere TeksVisiNasib")

    def test_ibot_leave_clears_vision_handle_before_human_lifecycle(self) -> None:
        left = self.rule(lambda rule: validator.event_type(rule) == "Player Left Match")
        mutated = self.replace_in_rule(
            left,
            "\n\t\t\tEvent Player.TeksVisiNasib = Null;",
            "",
        )
        self.assert_rejected(mutated, "leave iBot deve distruggere TeksVisiNasib")

    def test_ibot_leave_aborts_before_human_lifecycle(self) -> None:
        left = self.rule(lambda rule: validator.event_type(rule) == "Player Left Match")
        mutated = self.replace_in_rule(left, "\n\t\t\tAbort;", "")
        self.assert_rejected(mutated, "leave iBot deve distruggere TeksVisiNasib")

    def test_roster_append_is_idempotent(self) -> None:
        classifier = self.rule(lambda rule: "Append To Array(Global.PemainManusia, Event Player)" in rule.body)
        mutated = self.replace_in_rule(classifier, "Abort If(Array Contains(Global.PemainManusia, Event Player));", "")
        self.assert_rejected(mutated, "due volte il roster")

    def test_ibot_aborts_before_human_roster_append(self) -> None:
        classifier = self.rule(lambda rule: "Append To Array(Global.PemainManusia, Event Player)" in rule.body)
        mutated = self.replace_in_rule(
            classifier,
            "Call Subroutine(KunciBot);\n\t\t\tAbort;",
            "Call Subroutine(KunciBot);",
        )
        self.assert_rejected(mutated, "iBot può raggiungere il roster umano")

    def test_human_menu_dispatcher_has_all_bot_guards(self) -> None:
        dispatcher = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "PerintahMenu" in rule.body
            and "Button(Ability 2)" in rule.body
        )
        mutated = self.replace_in_rule(
            dispatcher,
            "Event Player.Manusia == True;",
            "Event Player.Manusia == False;",
        )
        self.assert_rejected(mutated, "dispatcher menu non isola bot/dummy")

    def test_only_classifier_can_mark_a_player_as_human(self) -> None:
        camera = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Button(Interact)" in rule.body
            and "Wait(0.500, Abort When False)" in rule.body
            and "ModeKamera" in rule.body
        )
        mutated = self.inject_action(camera, "Event Player.Manusia = True;")
        self.assert_rejected(mutated, "numero writer di Manusia=True")

    def test_anran_passive_has_all_bot_guards(self) -> None:
        anran = self.rule(lambda rule: validator.event_type(rule) == "Player Died" and "Hero(Anran)" in rule.body)
        mutated = self.replace_in_rule(anran, "Is Dummy Bot(Event Player) == False;", "Is Dummy Bot(Event Player) == True;")
        self.assert_rejected(mutated, "passiva Anran non isola bot/dummy")

    def test_dedicated_bot_rule_is_required(self) -> None:
        bot_rule = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Or(Is Dummy Bot(Event Player), Event Player.BotOtomatis) == True;" in rule.body
            and "Call Subroutine(KunciBot);" in rule.body
        )
        mutated = self.replace_in_rule(bot_rule, "Call Subroutine(KunciBot);", "")
        self.assert_rejected(mutated, "regola dedicata di lock bot/dummy assente")

    def test_native_dummy_wall_collision_keeps_floors_enabled(self) -> None:
        mutated = self.replace_once(
            "Disable Movement Collision With Environment(Event Player, False);",
            "Disable Movement Collision With Environment(Event Player, True);",
        )
        self.assert_rejected(mutated, "collisione ambiente dummy: Event Player con Include Floors False")

    def test_native_dummy_wall_collision_does_not_apply_to_ibots(self) -> None:
        bot_rule = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Call Subroutine(KunciBot);" in rule.body
            and "Disable Movement Collision With Environment" in rule.body
        )
        mutated = self.replace_in_rule(
            bot_rule,
            "If(Is Dummy Bot(Event Player) == True);\n\t\t\tEnable Movement Collision With Players",
            "If(Event Player.BotOtomatis == True);\n\t\t\tEnable Movement Collision With Players",
        )
        self.assert_rejected(mutated, "collisioni dummy non protette dal ramo nativo")

    def test_native_dummy_explicitly_keeps_player_collision_enabled(self) -> None:
        bot_rule = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Call Subroutine(KunciBot);" in rule.body
            and "Disable Movement Collision With Environment" in rule.body
        )
        mutated = self.replace_in_rule(
            bot_rule,
            "Enable Movement Collision With Players(Event Player);",
            "",
        )
        self.assert_rejected(mutated, "collisioni dummy non protette dal ramo nativo")

    def test_native_dummy_wall_collision_branch_cannot_be_made_unreachable(self) -> None:
        bot_rule = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Call Subroutine(KunciBot);" in rule.body
            and "Disable Movement Collision With Environment" in rule.body
        )
        mutated = self.replace_in_rule(
            bot_rule,
            "Call Subroutine(KunciBot);\n\t\tIf(Is Dummy Bot(Event Player) == True);",
            "Call Subroutine(KunciBot);\n\t\tAbort;\n\t\tIf(Is Dummy Bot(Event Player) == True);",
        )
        self.assert_rejected(mutated, "collisione ambiente dummy: sequenza raggiungibile e isolata")

    def test_native_dummy_wall_collision_rule_cannot_have_an_impossible_condition(self) -> None:
        bot_rule = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Call Subroutine(KunciBot);" in rule.body
            and "Disable Movement Collision With Environment" in rule.body
        )
        mutated = self.inject_condition(bot_rule, "False == True;")
        self.assert_rejected(mutated, "collisione ambiente dummy: condizioni esatte e raggiungibili")

    def test_bot_lock_neutralizes_player_interference(self) -> None:
        bot_lock = self.rule(lambda rule: validator.subroutine_target(rule) == "KunciBot")
        mutated = self.replace_in_rule(bot_lock, "Set Damage Dealt(Event Player, 0);", "")
        self.assert_rejected(mutated, "KunciBot incompleto")

    def test_bot_lock_receives_normal_damage_and_knockback(self) -> None:
        bot_lock = self.rule(lambda rule: validator.subroutine_target(rule) == "KunciBot")
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

    def test_bot_lock_must_not_disable_collision_with_players(self) -> None:
        bot_lock = self.rule(lambda rule: validator.subroutine_target(rule) == "KunciBot")
        mutated = self.inject_action(bot_lock, "Disable Movement Collision With Players(Event Player);")
        self.assert_rejected(mutated, "non deve disattivare la collisione dummy con i player")

    def test_bot_lock_requires_exactly_twenty_percent_move_speed(self) -> None:
        bot_lock = self.rule(lambda rule: validator.subroutine_target(rule) == "KunciBot")
        mutated = self.replace_in_rule(bot_lock, "Set Move Speed(Event Player, 20);", "Set Move Speed(Event Player, 0);")
        self.assert_rejected(mutated, "KunciBot: velocità bot/dummy")

    def test_native_dummy_requires_automatic_forward_throttle(self) -> None:
        movement = self.rule(lambda rule: "Start Throttle In Direction(Event Player," in rule.body)
        mutated = self.replace_in_rule(movement, "Start Throttle In Direction(Event Player,", "Start Throttle Towards Player(Event Player,")
        self.assert_rejected(mutated, "movimento automatico dummy assente")

    def test_native_dummy_movement_requires_a_valid_cached_target(self) -> None:
        movement = self.rule(lambda rule: "Start Throttle In Direction(Event Player," in rule.body)
        mutated = self.replace_in_rule(
            movement,
            "Event Player.TargetDummyIkuti != Null;",
            "Event Player.TargetDummyIkuti == Null;",
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
        cycle = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesSiklusPemain")
        mutated = self.replace_in_rule(
            cycle,
            "Team Of(Current Array Element) == Opposite Team Of(Team Of(Global.PemainAktif))",
            "Team Of(Current Array Element) == Team Of(Global.PemainAktif)",
        )
        self.assert_rejected(mutated, "cache target dummy: filtro deve essere l'umano nemico vivo opt-in")
    def test_native_dummy_cache_enemy_predicate_cannot_be_negated(self) -> None:
        cycle = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesSiklusPemain")
        predicate = (
            "And(Entity Exists(Current Array Element), And(Player Variable(Current Array Element, Manusia) == True, "
            "And(Player Variable(Current Array Element, IzinkanDummyMengikuti) == True, "
            "And(Has Spawned(Current Array Element), And(Is Alive(Current Array Element), "
            "Team Of(Current Array Element) == Opposite Team Of(Team Of(Global.PemainAktif)))))))"
        )
        self.assertEqual(cycle.body.count(predicate), 1)
        changed = cycle.body.replace(predicate, f"Not({predicate})")
        mutated = self.source[:cycle.start] + changed + self.source[cycle.end:]
        self.assert_rejected(mutated, "cache target dummy: filtro deve essere l'umano nemico vivo opt-in")
    def test_native_dummy_cache_targets_only_currently_registered_humans(self) -> None:
        cycle = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesSiklusPemain")
        mutated = self.replace_in_rule(
            cycle,
            "Player Variable(Current Array Element, Manusia) == True",
            "Player Variable(Current Array Element, Manusia) == False",
        )
        self.assert_rejected(mutated, "cache target dummy: filtro deve essere l'umano nemico vivo opt-in")
    def test_native_dummy_cache_respects_per_player_follow_opt_out(self) -> None:
        cycle = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesSiklusPemain")
        mutated = self.replace_in_rule(
            cycle,
            "Player Variable(Current Array Element, IzinkanDummyMengikuti) == True",
            "True",
        )
        self.assert_rejected(mutated, "cache target dummy deve filtrare gli umani opt-in una sola volta per ciclo")
    def test_no_target_cleanup_rejects_cached_target_opt_out(self) -> None:
        cleanup = self.rule(
            lambda rule: "Event Player.TargetDummyIkuti == Null" in rule.body
            and "Stop Facing(Event Player);" in rule.body
        )
        mutated = self.replace_in_rule(
            cleanup,
            "Player Variable(Event Player.TargetDummyIkuti, IzinkanDummyMengikuti) == False",
            "Player Variable(Event Player.TargetDummyIkuti, IzinkanDummyMengikuti) == True",
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
            lambda rule: "Event Player.TargetDummyIkuti == Null" in rule.body
            and "Stop Facing(Event Player);" in rule.body
        )
        mutated = self.replace_in_rule(cleanup, "Stop Throttle In Direction(Event Player);", "")
        self.assert_rejected(mutated, "cleanup movimento dummy cache incompleto")
    def test_native_dummy_cleanup_stops_when_cached_target_changes_team(self) -> None:
        cleanup = self.rule(
            lambda rule: "Event Player.TargetDummyIkuti == Null" in rule.body
            and "Stop Facing(Event Player);" in rule.body
        )
        mutated = self.replace_in_rule(
            cleanup,
            "Team Of(Event Player.TargetDummyIkuti) != Opposite Team Of(Team Of(Event Player))",
            "Team Of(Event Player.TargetDummyIkuti) == Opposite Team Of(Team Of(Event Player))",
        )
        self.assert_rejected(mutated, "cleanup movimento dummy cache incompleto")
    def test_dummy_release_stops_facing_before_destroy(self) -> None:
        release = self.rule(lambda rule: validator.subroutine_target(rule) == "LepasDummyTim")
        mutated = self.replace_in_rule(release, "Stop Facing(First Of(Filtered Array(", "Start Facing(First Of(Filtered Array(")
        self.assert_rejected(mutated, "LepasDummyTim incompleta")

    def test_dummy_creation_reserves_the_last_human_slot(self) -> None:
        create = self.rule(
            lambda rule: "Number Of Players(Team 1) < Number Of Slots(Team 1) - 1;" in rule.body
            and "Call Subroutine(BuatDummyTim);" in rule.body
        )
        mutated = self.replace_in_rule(
            create,
            "Number Of Players(Team 1) < Number Of Slots(Team 1) - 1;",
            "Number Of Players(Team 1) < Number Of Slots(Team 1);",
        )
        self.assert_rejected(mutated, "numero regole creazione dummy Team 1")

    def test_dummy_creation_cannot_have_an_impossible_condition(self) -> None:
        create = self.rule(
            lambda rule: "Number Of Players(Team 1) < Number Of Slots(Team 1) - 1;" in rule.body
            and "Call Subroutine(BuatDummyTim);" in rule.body
        )
        mutated = self.inject_condition(create, "False == True;")
        self.assert_rejected(mutated, "creazione dummy Team 1: condizioni esatte e raggiungibili")

    def test_dummy_is_removed_when_the_team_needs_the_last_slot(self) -> None:
        release = self.rule(
            lambda rule: "Number Of Players(Team 1) >= Number Of Slots(Team 1);" in rule.body
            and "Call Subroutine(LepasDummyTim);" in rule.body
        )
        mutated = self.replace_in_rule(release, "Call Subroutine(LepasDummyTim);", "Abort;")
        self.assert_rejected(mutated, "numero regole rilascio slot dummy Team 1")

    def test_dummy_release_cannot_abort_before_cleanup(self) -> None:
        release = self.rule(lambda rule: validator.subroutine_target(rule) == "LepasDummyTim")
        mutated = self.replace_in_rule(
            release,
            "\n\t\tIf(Player Variable(",
            "\n\t\tAbort;\n\t\tIf(Player Variable(",
        )
        self.assert_rejected(mutated, "LepasDummyTim: cleanup atomico esatto senza abort")

    def test_dummy_spawn_delay_uses_a_rearmed_timestamp(self) -> None:
        arming = self.rule(
            lambda rule: "If(Event Player.WaktuTeleportasiDummy == 0);" in rule.body
            and "Event Player.WaktuTeleportasiDummy = Total Time Elapsed + 1;" in rule.body
        )
        mutated = self.replace_in_rule(
            arming,
            "If(Event Player.WaktuTeleportasiDummy == 0);",
            "If(Event Player.WaktuTeleportasiDummy > 0);",
        )
        self.assert_rejected(mutated, "arming timestamp teleport dummy assente")

    def test_dummy_death_cleanup_cannot_have_an_impossible_condition(self) -> None:
        death = self.rule(
            lambda rule: validator.event_type(rule) == "Player Died"
            and "Stop Facing(Event Player);" in rule.body
            and "WaktuTeleportasiDummy = 0;" in rule.body
        )
        mutated = self.inject_condition(death, "False == True;")
        self.assert_rejected(mutated, "cleanup morte dummy: condizioni esatte dopo la morte completa")

    def test_dummy_death_cleanup_cannot_abort_before_stopping(self) -> None:
        death = self.rule(
            lambda rule: validator.event_type(rule) == "Player Died"
            and "Stop Facing(Event Player);" in rule.body
            and "WaktuTeleportasiDummy = 0;" in rule.body
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
            if call.args and call.args[0].strip() == "Global.PemainManusia"
        )
        mutated = self.replace_call_argument(call, 0, "All Players(All Teams)")
        self.assert_rejected(mutated, "Create HUD Text visibile a bot/dummy")

    def test_initial_setup_performs_full_preferences_reset(self) -> None:
        setup = self.rule(lambda rule: validator.subroutine_target(rule) == "SiapkanPemain")
        mutated = self.replace_in_rule(setup, "Event Player.IndeksBahasa = 0;", "Event Player.IndeksBahasa = Event Player.IndeksBahasa;")
        self.assert_rejected(mutated, "IndeksBahasa = 0")

    def test_cleanup_is_fully_atomic_without_wait_or_loop(self) -> None:
        cleanup = self.rule(lambda rule: validator.subroutine_target(rule) == "BersihkanPemain")
        for action in ("Wait(0.016, Ignore Condition);", "Loop;"):
            with self.subTest(action=action):
                mutated = self.inject_action(cleanup, action)
                self.assert_rejected(mutated, "BersihkanPemain deve essere atomica")

    def test_team_switch_lock_releases_only_after_stable_registration(self) -> None:
        cycle = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesSiklusPemain")
        mutated = self.replace_in_rule(
            cycle,
            "Global.PemainAktif.HudPemainDibuat == True",
            "Global.PemainAktif.HudPemainDibuat == False",
        )
        self.assert_rejected(mutated, "rilascio stabile lock")

    def test_team_switch_lock_waits_for_stable_automatic_bot(self) -> None:
        cycle = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesSiklusPemain")
        mutated = self.replace_in_rule(
            cycle,
            "Global.PemainAktif.SudahDiperiksa == True",
            "Global.PemainAktif.SudahDiperiksa == False",
        )
        self.assert_rejected(mutated, "registrazione bot BotOtomatis/SudahDiperiksa")

    def test_human_classification_initializes_the_shared_hero_tracker(self) -> None:
        classifier = self.rule(
            lambda rule: "Append To Array(Global.PemainManusia, Event Player)" in rule.body
        )
        mutated = self.replace_in_rule(
            classifier,
            "Event Player.PahlawanTerakhir = Hero Of(Event Player);",
            "Event Player.PahlawanTerakhir = Null;",
        )
        self.assert_rejected(mutated, "classificazione umana non inizializza PahlawanTerakhir")

    def test_human_hero_swap_cleans_luck_in_the_global_scheduler(self) -> None:
        cycle = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesSiklusPemain")
        mutated = self.replace_in_rule(
            cycle,
            "Call Subroutine(PulihkanNasibAktif);",
            "Abort;",
        )
        self.assert_rejected(mutated, "hero swap umano non pulisce Try Your Luck")

    def test_live_luck_cleanup_preserves_physical_unkillable(self) -> None:
        cleanup = self.rule(lambda rule: validator.subroutine_target(rule) == "PulihkanNasibAktif")
        mutated = self.replace_in_rule(
            cleanup,
            "Is Alive(Global.PemainAktif) == False",
            "Is Alive(Global.PemainAktif) == True",
        )
        self.assert_rejected(mutated, "cleanup Try vivo non deve sospendere Unkillable")

    def test_privacy_is_off_by_default(self) -> None:
        setup = self.rule(lambda rule: validator.subroutine_target(rule) == "SiapkanPemain")
        mutated = self.replace_in_rule(
            setup,
            "Event Player.PrivasiInspeksiAktif = False;",
            "Event Player.PrivasiInspeksiAktif = True;",
        )
        self.assert_rejected(mutated, "Privacy deve essere OFF di default")

    def test_privacy_cursor_defaults_to_off(self) -> None:
        setup = self.rule(lambda rule: validator.subroutine_target(rule) == "SiapkanPemain")
        mutated = self.replace_in_rule(
            setup,
            "Event Player.KursorPrivasiInspeksi = 0;",
            "Event Player.KursorPrivasiInspeksi = 1;",
        )
        self.assert_rejected(mutated, "cursore Privacy deve iniziare su OFF")

    def test_real_camera_cache_missing_and_excessive_parenthesis_are_rejected(self) -> None:
        cache = self.rule(lambda rule: validator.subroutine_target(rule) == "SegarkanTargetPublikAktif")
        call = next(
            call for call in validator.iter_calls(cache.body, "Set Player Variable")
            if len(call.args) >= 3
            and call.args[1].strip() == "DaftarTargetInspeksi"
            and "PrivasiInspeksiAktif" in call.args[2]
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
        cache = self.rule(lambda rule: validator.subroutine_target(rule) == "SegarkanTargetPublikAktif")
        call = next(
            call for call in validator.iter_calls(cache.body, "Set Player Variable")
            if len(call.args) >= 3
            and call.args[1].strip() == "DaftarTargetInspeksi"
            and "PrivasiInspeksiAktif" in call.args[2]
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
                if "PrivasiInspeksiAktif" in call.raw:
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
        refresh = self.rule(lambda rule: validator.subroutine_target(rule) == "SegarkanTargetPublikPemain")
        mutated = self.replace_in_rule(
            refresh,
            "Player Variable(Current Array Element, PrivasiInspeksiAktif) == False",
            "Player Variable(Current Array Element, PrivasiInspeksiAktif) == True",
        )
        self.assert_rejected(mutated, "numero filtri Privacy target-aware")

    def test_unclassified_human_is_not_treated_as_a_public_camera_target(self) -> None:
        refresh = self.rule(lambda rule: validator.subroutine_target(rule) == "SegarkanTargetPublikPemain")
        mutated = self.replace_in_rule(
            refresh,
            "Player Variable(Current Array Element, Manusia) == True",
            "True",
        )
        self.assert_rejected(mutated, "ogni Privacy OFF target richiede Manusia=True")

    def test_shared_public_filters_require_a_classified_human(self) -> None:
        protected_rules = (
            self.rule(lambda rule: validator.subroutine_target(rule) == "SegarkanTargetPublikPemain"),
            self.rule(lambda rule: validator.subroutine_target(rule) == "SegarkanTargetPublikAktif"),
        )
        for rule in protected_rules:
            with self.subTest(rule=rule.name):
                mutated = self.replace_regex_in_rule(
                    rule,
                    r"Player Variable\(\s*Current Array Element\s*,\s*Manusia\)\s*==\s*True",
                    "True",
                )
                self.assert_rejected(mutated, "ogni Privacy OFF target richiede Manusia=True")
    def test_inspection_rejects_a_vision_privacy_bypass(self) -> None:
        refresh = self.rule(lambda rule: validator.subroutine_target(rule) == "SegarkanTargetInspeksi")
        mutated = self.inject_action(
            refresh,
            "If(Event Player.PrivasiNasibAktif == True);\n\t\t\tAbort;\n\t\tEnd;",
        )
        self.assert_rejected(mutated, "bypass Privacy tramite Vision")
    def test_vision_names_exclude_private_human_subjects(self) -> None:
        vision = self.rule(
            lambda rule: "Event Player.TeksVisiNasib = Last Text ID;" in rule.body
            and "Create In-World Text(" in rule.body
        )
        mutated = self.replace_in_rule(
            vision,
            "And(Event Player.Manusia == True, Event Player.PrivasiInspeksiAktif == False)",
            "Event Player.Manusia == True",
        )
        self.assert_rejected(mutated, "Vision espone un umano con Privacy ON")

    def test_vision_shows_hero_icon_name_and_live_health(self) -> None:
        vision = self.rule(
            lambda rule: "Event Player.TeksVisiNasib = Last Text ID;" in rule.body
            and "Create In-World Text(" in rule.body
        )
        call = next(iter(validator.iter_calls(vision.body, "Create In-World Text")))
        absolute = validator.Call(call.name, call.raw, call.args, vision.start + call.start, vision.start + call.end)
        mutated = self.replace_call_argument(absolute, 1, 'Custom String("{0}", Event Player)')
        self.assert_rejected(mutated, "Vision non mostra icona eroe")

    def test_vision_recipients_are_only_other_humans_with_vision_active(self) -> None:
        vision = self.rule(
            lambda rule: "Event Player.TeksVisiNasib = Last Text ID;" in rule.body
            and "Create In-World Text(" in rule.body
        )
        call = next(iter(validator.iter_calls(vision.body, "Create In-World Text")))
        absolute = validator.Call(call.name, call.raw, call.args, vision.start + call.start, vision.start + call.end)
        mutated = self.replace_call_argument(absolute, 0, "All Players(All Teams)")
        self.assert_rejected(mutated, "destinatari Vision devono essere gli altri umani")

    def test_vision_text_keeps_icon_name_health_order(self) -> None:
        vision = self.rule(
            lambda rule: "Event Player.TeksVisiNasib = Last Text ID;" in rule.body
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

    def test_inspection_crouch_is_blocked_during_vision(self) -> None:
        inspection = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Event Player.TargetInspeksi != Event Player.CalonTargetInspeksi;" in rule.body
        )
        mutated = self.replace_in_rule(inspection, "\n\t\tEvent Player.PrivasiNasibAktif == False;", "")
        self.assert_rejected(mutated, "inspection Crouch non è bloccata durante Vision")

    def test_teleport_crouch_is_blocked_during_vision(self) -> None:
        teleport = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Event Player.TeleportasiJongkokAktif = True;" in rule.body
            and "Button(Crouch)" in rule.body
        )
        mutated = self.replace_in_rule(teleport, "\n\t\tEvent Player.PrivasiNasibAktif == False;", "")
        self.assert_rejected(mutated, "Teleport Crouch non è bloccato durante Vision")

    def test_inspection_cleanup_runs_when_vision_starts(self) -> None:
        cycle = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesSiklusPemain")
        mutated = self.replace_in_rule(
            cycle,
            "Global.PemainAktif.PrivasiNasibAktif == True",
            "Global.PemainAktif.PrivasiNasibAktif == False",
        )
        self.assert_rejected(mutated, "cleanup inspection non reagisce all'avvio di Vision")

    def test_teleport_cleanup_runs_when_vision_starts(self) -> None:
        cleanup = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Event Player.TeleportasiJongkokAktif == True;" in rule.body
            and "Event Player.TeleportasiJongkokAktif = False;" in rule.body
            and "Destroy HUD Text(Event Player.HudMenu);" in rule.body
        )
        mutated = self.replace_in_rule(
            cleanup,
            "Event Player.PrivasiNasibAktif == True",
            "Event Player.PrivasiNasibAktif == False",
        )
        self.assert_rejected(mutated, "cleanup Teleport Crouch non reagisce all'avvio di Vision")

    def test_vision_name_cleanup_runs_when_subject_enables_privacy(self) -> None:
        cleanup = self.rule(
            lambda rule: "Destroy In-World Text(Event Player.TeksVisiNasib);" in rule.body
            and "Event Player.TeksVisiNasib = Null;" in rule.body
            and validator.event_type(rule) == "Ongoing - Each Player"
        )
        mutated = self.replace_in_rule(
            cleanup,
            "And(Event Player.Manusia == True, Event Player.PrivasiInspeksiAktif == True)",
            "And(Event Player.Manusia == True, Event Player.PrivasiInspeksiAktif == False)",
        )
        self.assert_rejected(mutated, "cleanup Vision non rimuove subito un umano che attiva Privacy")

    def test_inspection_and_teleport_never_enable_native_nameplates(self) -> None:
        protected = (
            self.rule(
                lambda rule: "Event Player.TargetInspeksi != Event Player.CalonTargetInspeksi;" in rule.body
            ),
            self.rule(
                lambda rule: "Event Player.TargetTeleportasiTeks != Event Player.CalonTargetTeleportasi;" in rule.body
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

    def test_camera_target_cache_excludes_private_humans(self) -> None:
        cache = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesCachePemain")
        mutated = self.replace_in_rule(
            cache,
            "Call Subroutine(SegarkanTargetPublikAktif);",
            "Abort;",
        )
        self.assert_rejected(mutated, "cache target Camera non riusa la subroutine pubblica globale")

    def test_active_observer_is_stopped_when_target_turns_private(self) -> None:
        cycle = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesSiklusPemain")
        mutated = self.replace_in_rule(
            cycle,
            "Global.PemainAktif.TargetKamera.PrivasiInspeksiAktif == True",
            "Global.PemainAktif.TargetKamera.PrivasiInspeksiAktif == False",
        )
        self.assert_rejected(mutated, "osservatore attivo non viene fermato")

    def test_workshop_setting_labels_are_trilingual(self) -> None:
        call = next(iter(validator.iter_calls(self.source, "Workshop Setting Integer")))
        mutated = self.replace_call_argument(call, 1, 'Custom String("Server duration")')
        self.assert_rejected(mutated, "label Workshop Setting Integer")

    def test_all_eight_objective_modes_are_explicit(self) -> None:
        mutated = self.replace_once("Game Mode(Flashpoint)", "Game Mode(Practice Range)")
        self.assert_rejected(mutated, "Flashpoint")

    def test_native_mode_result_cannot_be_overridden(self) -> None:
        mutated = self.source + "\nSet Team Score(Team 1, 99);\n"
        self.assert_rejected(mutated, "modalità nativa")

    def test_camera_has_exactly_one_raycast(self) -> None:
        camera_rule = validator.rule_by_subroutine(validator.extract_rules(self.source), "MulaiKamera")
        self.assertIsNotNone(camera_rule)
        assert camera_rule is not None
        mutated_body = camera_rule.body.replace(
            "Ray Cast Hit Position(",
            "Ray Cast Hit Position(Eye Position(Event Player), Vector(0, 0, 0), Empty Array, Empty Array, False) + Ray Cast Hit Position(",
            1,
        )
        mutated = self.source[:camera_rule.start] + mutated_body + self.source[camera_rule.end:]
        self.assert_rejected(mutated, "raycast Camera")

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

class RepositoryMetadataTests(unittest.TestCase):
    def make_repo(self, root: Path) -> None:
        (root / ".github" / "workflows").mkdir(parents=True)
        (root / "docs").mkdir()
        (root / "VERSION").write_text("0.8.1\n", encoding="utf-8")
        for relative in validator.CORE_DOCS:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("CHILL 0.8.1\nStato: **static-ready / live-pending**\n", encoding="utf-8")
        (root / "CHANGELOG.md").write_text(
            "## 0.8.1\n\nStato: **live-pending**.\n",
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

    def test_valid_repository_metadata_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            self.assertEqual(self.metadata_errors(root), [])

    def test_stale_version_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            (root / "VERSION").write_text("0.7.2\n", encoding="utf-8")
            self.assertTrue(any("VERSION" in error for error in self.metadata_errors(root)))

    def test_live_ready_document_is_rejected_before_client_regression(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            (root / "README.md").write_text(
                "CHILL 0.8.1\nStato: **live-ready**\n",
                encoding="utf-8",
            )
            errors = self.metadata_errors(root)
            self.assertTrue(any("live-ready" in error or "live-pending" in error for error in errors))

    def test_assertive_current_live_ready_claim_is_rejected_with_valid_state_marker(self) -> None:
        claims = (
            "La versione 0.8.1 è live-ready.",
            "La versione v0.8.1 è live-ready.",
        )
        for claim in claims:
            with self.subTest(claim=claim), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.make_repo(root)
                readme = root / "README.md"
                readme.write_text(
                    readme.read_text(encoding="utf-8") + f"\n{claim}\n",
                    encoding="utf-8",
                )
                self.assertTrue(
                    any(
                        "affermazione live-ready assertiva" in error
                        for error in self.metadata_errors(root)
                    )
                )

    def test_published_current_tag_or_release_claim_is_rejected(self) -> None:
        claims = (
            "Il tag finale v0.8.1 identifica il commit pubblicato e validato.",
            "La release 0.8.1 è stata pubblicata.",
            "La release v0.8.1 è stata pubblicata.",
            "https://github.com/skelos95/ruang-irama-workshop/releases/tag/v0.8.1",
        )
        for claim in claims:
            with self.subTest(claim=claim), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.make_repo(root)
                readme = root / "README.md"
                readme.write_text(
                    readme.read_text(encoding="utf-8") + f"\n{claim}\n",
                    encoding="utf-8",
                )
                self.assertTrue(
                    any("tag/release v0.8.1" in error for error in self.metadata_errors(root))
                )

    def test_future_live_ready_explanation_and_planned_tag_are_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            readme = root / "README.md"
            readme.write_text(
                readme.read_text(encoding="utf-8")
                + "\nLo stato live-ready richiede i test client completi. "
                "Il tag finale v0.8.1 verrà creato soltanto dopo quei test.\n",
                encoding="utf-8",
            )
            self.assertEqual(self.metadata_errors(root), [])

    def test_historical_changelog_live_ready_is_not_treated_as_current_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            (root / "CHANGELOG.md").write_text(
                "## 0.8.1\nStato: **live-pending**.\n"
                "## 0.8.0\nStato: **live-ready**\n",
                encoding="utf-8",
            )
            self.assertEqual(self.metadata_errors(root), [])

    def test_assertive_current_changelog_claim_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            (root / "CHANGELOG.md").write_text(
                "## 0.8.1 — 2026-08-25\n\n"
                "Stato: **live-pending**.\n\n"
                "La versione v0.8.1 è live-ready.\n\n"
                "## 0.8.0\n\nStato: **live-ready**.\n",
                encoding="utf-8",
            )
            self.assertTrue(
                any(
                    "CHANGELOG.md contiene un'affermazione live-ready" in error
                    for error in self.metadata_errors(root)
                )
            )

    def test_maintenance_workflow_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            (root / ".github" / "workflows" / "maintenance-patch.yml").write_text("on: workflow_dispatch\n", encoding="utf-8")
            self.assertTrue(any("workflow permanenti" in error for error in self.metadata_errors(root)))

    def test_stale_github_marker_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            (root / ".github" / ".validator-wait-policy-trigger").write_text("one-shot\n", encoding="utf-8")
            self.assertTrue(any("contenuti permanenti .github" in error for error in self.metadata_errors(root)))

    def test_non_workflow_file_inside_workflows_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            (root / ".github" / "workflows" / "patcher.py").write_text("# one-shot\n", encoding="utf-8")
            self.assertTrue(any("contenuti permanenti .github" in error for error in self.metadata_errors(root)))

    def test_validation_workflow_must_not_push(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            workflow = root / ".github" / "workflows" / "validate-workshop.yml"
            workflow.write_text(workflow.read_text(encoding="utf-8") + "      - run: git push\n", encoding="utf-8")
            self.assertTrue(any("non deve modificare" in error for error in self.metadata_errors(root)))


if __name__ == "__main__":
    unittest.main()
