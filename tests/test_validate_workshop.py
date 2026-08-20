from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from tools import validate_workshop as validator


class SemanticWorkshop080Tests(unittest.TestCase):
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
        valid_name = "DaftarTargetTeleportasi"
        boundary_name = "DaftarTargetTeleportasiSekarangX"
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

    def test_chill_title_cannot_end_with_a_blank_spacer_line(self) -> None:
        call = next(
            call for call in validator.iter_calls(self.source, "Create HUD Text")
            if len(call.args) >= 4
            and "CHILL DEDICATED SERVER" in call.args[3]
            and "Global.TeksWaktuServer" in call.args[3]
        )
        mutated = self.replace_call_argument(
            call,
            3,
            f'Custom String("{{0}}\\n ", {call.args[3]})',
        )
        self.assert_rejected(mutated, "riga vuota finale prima del menu")

    def test_primary_secondary_must_not_redraw_menu(self) -> None:
        rule = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Each Player" and "PerintahMenu" in rule.body and "Button(Primary Fire)" in rule.body)
        mutated = self.inject_action(rule, "Destroy HUD Text(Event Player.HudMenu);")
        self.assert_rejected(mutated, "Primary/Secondary")

    def test_all_twelve_pages_are_routed(self) -> None:
        router = self.rule(lambda rule: validator.subroutine_target(rule) == "GambarHalamanAktif")
        mutated = self.replace_in_rule(router, "HalamanMenu == 11", "HalamanMenu == 12")
        self.assert_rejected(mutated, "pagina 11")

    def test_interact_dispatch_is_split_into_page_handlers(self) -> None:
        mutated = self.source.replace("TerapkanHalamanIkon", "TerapkanIkonLegacy")
        self.assert_rejected(mutated, "12 subroutine pagina")

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

    def test_jump_respawn_is_not_blocked_by_open_menu(self) -> None:
        respawn = self.rule(lambda rule: "Respawn(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        mutated = self.inject_action(respawn, "Abort If(Event Player.MenuTerbuka == False);")
        self.assert_rejected(mutated, "Jump respawn")

    def test_only_one_loop_is_allowed(self) -> None:
        mutated = self.source + "\nLoop;\n"
        self.assert_rejected(mutated, "numero Loop")

    def test_at_most_ten_waits_are_allowed(self) -> None:
        mutated = self.source + "\n" + "\n".join("Wait(0.001, Ignore Condition);" for _ in range(11))
        self.assert_rejected(mutated, "Wait oltre")

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

    def test_try_your_luck_skull_kill_is_inside_state_machine(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
        mutated = self.replace_in_rule(machine, "Kill(Global.PemainAktif, Null);", "")
        self.assertIn("Kill(Event Player.TargetBalasDendamTerkunci, Event Player);", mutated)
        self.assert_rejected(mutated, "Skull deve uccidere esattamente Global.PemainAktif")

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

    def test_roulette_icons_reevaluate_position_only(self) -> None:
        machine = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesNasibPemain")
        call = next(iter(validator.iter_calls(machine.body, "Create Icon")))
        absolute = validator.Call(call.name, call.raw, call.args, machine.start + call.start, machine.start + call.end)
        mutated = self.replace_call_argument(absolute, 3, "None")
        self.assert_rejected(mutated, "reevaluation deve essere Position")

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
        self.assertIn("), Eye, Position", self.source)
        self.assertIn("), Skull, Position", self.source)
        mutated = self.source.replace("), Eye, Position", "), IkonSementara, Position", 1)
        mutated = mutated.replace("), Skull, Position", "), Eye, Position", 1)
        mutated = mutated.replace("), IkonSementara, Position", "), Skull, Position", 1)
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
        death_cleanup = self.rule(
            lambda rule: validator.event_type(rule) == "Player Died" and "KartuNasibAktif" in rule.body
        )
        mutated = self.replace_in_rule(death_cleanup, "Stop Accelerating(Event Player);", "")
        self.assert_rejected(mutated, "cleanup accelerazione morte: Stop Accelerating assente")

    def test_roulette_icon_is_destroyed_and_cleared_on_all_lifecycle_paths(self) -> None:
        cleanup_rules = (
            (self.rule(lambda rule: validator.event_type(rule) == "Player Died" and "KartuNasibAktif" in rule.body), "morte"),
            (self.rule(lambda rule: validator.subroutine_target(rule) == "TenangkanPemain"), "quiete lifecycle"),
            (self.rule(lambda rule: validator.subroutine_target(rule) == "BersihkanPemain"), "cleanup lifecycle"),
        )
        for rule, label in cleanup_rules:
            with self.subTest(path=label, mutation="destroy"):
                mutated = self.replace_in_rule(rule, "Destroy Icon(Event Player.IkonKartuNasib);", "")
                self.assert_rejected(mutated, f"cleanup icona roulette {label}: Destroy Icon assente")
            with self.subTest(path=label, mutation="null"):
                mutated = self.replace_in_rule(rule, "Event Player.IkonKartuNasib = Null;", "")
                self.assert_rejected(mutated, f"cleanup icona roulette {label}: azzeramento handle assente")

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

    def test_join_requires_duplicate_guard(self) -> None:
        joined = self.rule(lambda rule: validator.event_type(rule) == "Player Joined Match")
        mutated = self.replace_in_rule(joined, "Event Player.PindahTimDiproses == False;", "Event Player.PindahTimDiproses == True;")
        self.assert_rejected(mutated, "PindahTimDiproses")

    def test_team_switch_lifecycle_excludes_classified_ibots(self) -> None:
        joined = self.rule(lambda rule: validator.event_type(rule) == "Player Joined Match")
        mutated = self.replace_in_rule(joined, "Event Player.BotOtomatis == False;", "Event Player.BotOtomatis == True;")
        self.assert_rejected(mutated, "join/team-switch umano può riattivare")

    def test_leave_cleanup_is_limited_to_the_human_roster(self) -> None:
        left = self.rule(lambda rule: validator.event_type(rule) == "Player Left Match")
        mutated = self.replace_in_rule(
            left,
            "Or(Event Player.Manusia == True, Array Contains(Global.PemainManusia, Event Player)) == True;",
            "Event Player.Manusia == False;",
        )
        self.assert_rejected(mutated, "leave/cleanup umano può essere eseguito")

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

    def test_bot_lock_neutralizes_player_interference(self) -> None:
        bot_lock = self.rule(lambda rule: validator.subroutine_target(rule) == "KunciBot")
        mutated = self.replace_in_rule(bot_lock, "Set Damage Dealt(Event Player, 0);", "")
        self.assert_rejected(mutated, "KunciBot incompleto")

    def test_player_hud_is_never_visible_to_bot_or_dummy_players(self) -> None:
        call = next(
            call for call in validator.iter_calls(self.source, "Create HUD Text")
            if call.args and call.args[0].strip() == "Global.PemainManusia"
        )
        mutated = self.replace_call_argument(call, 0, "All Players(All Teams)")
        self.assert_rejected(mutated, "Create HUD Text visibile a bot/dummy")

    def test_team_switch_performs_full_preferences_reset(self) -> None:
        setup = self.rule(lambda rule: validator.subroutine_target(rule) == "SiapkanPemain")
        mutated = self.replace_in_rule(setup, "Event Player.IndeksBahasa = 0;", "Event Player.IndeksBahasa = Event Player.IndeksBahasa;")
        self.assert_rejected(mutated, "IndeksBahasa = 0")

    def test_cleanup_critical_section_cannot_wait(self) -> None:
        cleanup = self.rule(lambda rule: validator.subroutine_target(rule) == "BersihkanPemain")
        token = "Global.IndeksKeluar = Index Of Array Value"
        position = cleanup.body.index(token)
        line_end = cleanup.body.index(";", position) + 1
        changed = cleanup.body[:line_end] + "\n\t\tWait(0.016, Ignore Condition);" + cleanup.body[line_end:]
        mutated = self.source[:cleanup.start] + changed + self.source[cleanup.end:]
        self.assert_rejected(mutated, "cleanup usa Wait")

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

    def test_privacy_is_on_by_default(self) -> None:
        setup = self.rule(lambda rule: validator.subroutine_target(rule) == "SiapkanPemain")
        mutated = self.replace_in_rule(
            setup,
            "Event Player.PrivasiInspeksiAktif = True;",
            "Event Player.PrivasiInspeksiAktif = False;",
        )
        self.assert_rejected(mutated, "Privacy deve essere ON di default")

    def test_privacy_cursor_defaults_to_on(self) -> None:
        setup = self.rule(lambda rule: validator.subroutine_target(rule) == "SiapkanPemain")
        mutated = self.replace_in_rule(
            setup,
            "Event Player.KursorPrivasiInspeksi = 1;",
            "Event Player.KursorPrivasiInspeksi = 0;",
        )
        self.assert_rejected(mutated, "cursore Privacy deve iniziare su ON")

    def test_real_camera_cache_missing_and_excessive_parenthesis_are_rejected(self) -> None:
        cache = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesCachePemain")
        call = next(
            call for call in validator.iter_calls(cache.body, "Set Player Variable")
            if len(call.args) >= 3
            and call.args[1].strip() == "DaftarTargetKamera"
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
        cache = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesCachePemain")
        call = next(
            call for call in validator.iter_calls(cache.body, "Set Player Variable")
            if len(call.args) >= 3
            and call.args[1].strip() == "DaftarTargetKamera"
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
        mutated_cache = next(
            rule for rule in validator.extract_rules(mutated)
            if validator.subroutine_target(rule) == "ProsesCachePemain"
        )
        mutated_actions = validator.mask_strings(validator.rule_block(mutated_cache, "actions") or "")
        self.assertEqual(mutated_actions.count("("), mutated_actions.count(")"))
        self.assert_rejected(mutated, "terminatore statement")

    def test_all_six_privacy_filters_have_balanced_call_parentheses(self) -> None:
        privacy_calls: list[tuple[validator.Rule, validator.Call]] = []
        for rule in validator.extract_rules(self.source):
            for call in validator.iter_calls(rule.body, "Filtered Array"):
                if "PrivasiInspeksiAktif" in call.raw:
                    privacy_calls.append((rule, call))
        self.assertEqual(len(privacy_calls), 6)
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
        refresh = self.rule(lambda rule: validator.subroutine_target(rule) == "SegarkanTargetKamera")
        mutated = self.replace_in_rule(
            refresh,
            "Player Variable(Current Array Element, PrivasiInspeksiAktif) == False",
            "Player Variable(Current Array Element, PrivasiInspeksiAktif) == True",
        )
        self.assert_rejected(mutated, "lista target Camera non esclude umani privati")

    def test_unclassified_human_is_not_treated_as_a_public_camera_target(self) -> None:
        refresh = self.rule(lambda rule: validator.subroutine_target(rule) == "SegarkanTargetKamera")
        mutated = self.replace_in_rule(
            refresh,
            "Player Variable(Current Array Element, Manusia) == True",
            "True",
        )
        self.assert_rejected(mutated, "Dummy OR iBot OR (umano AND Privacy OFF)")

    def test_all_inspection_and_teleport_filters_require_a_classified_human(self) -> None:
        protected_rules = (
            self.rule(lambda rule: validator.subroutine_target(rule) == "SegarkanTargetInspeksi"),
            self.rule(
                lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
                and "Event Player.TargetInspeksi != First Of(Sorted Array(Filtered Array(" in rule.body
            ),
            self.rule(lambda rule: validator.subroutine_target(rule) == "SegarkanTargetTeleportasi"),
            self.rule(
                lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
                and "Event Player.CalonTargetTeleportasi != First Of(Sorted Array(Filtered Array(" in rule.body
            ),
        )
        for rule in protected_rules:
            with self.subTest(rule=rule.name):
                mutated = self.replace_regex_in_rule(
                    rule,
                    r"Player Variable\(\s*Current Array Element\s*,\s*Manusia\)\s*==\s*True",
                    "True",
                )
                self.assert_rejected(mutated, "ogni Privacy OFF target richiede Manusia=True")

    def test_inspection_keeps_the_explicit_vision_bypass(self) -> None:
        refresh = self.rule(lambda rule: validator.subroutine_target(rule) == "SegarkanTargetInspeksi")
        mutated = self.replace_in_rule(
            refresh,
            "Event Player.PrivasiNasibAktif == True",
            "Event Player.PrivasiNasibAktif == False",
        )
        self.assert_rejected(mutated, "inspection non usa Dummy OR iBot OR Vision")

    def test_camera_target_cache_excludes_private_humans(self) -> None:
        cache = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesCachePemain")
        mutated = self.replace_in_rule(
            cache,
            "Player Variable(Current Array Element, BotOtomatis) == True",
            "Player Variable(Current Array Element, BotOtomatis) == False",
        )
        self.assert_rejected(mutated, "cache target Camera non esclude umani privati")

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
        mutated = self.source + "\nRay Cast Hit Position(Eye Position(Event Player), Vector(0, 0, 0), Null, Null, False);\n"
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


class RepositoryMetadataTests(unittest.TestCase):
    def make_repo(self, root: Path) -> None:
        (root / ".github" / "workflows").mkdir(parents=True)
        (root / "docs").mkdir()
        (root / "VERSION").write_text("0.8.0\n", encoding="utf-8")
        for relative in validator.CORE_DOCS:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("CHILL 0.8.0 — static-ready / live-pending\n", encoding="utf-8")
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

    def test_maintenance_workflow_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            (root / ".github" / "workflows" / "maintenance-patch.yml").write_text("on: workflow_dispatch\n", encoding="utf-8")
            self.assertTrue(any("workflow permanenti" in error for error in self.metadata_errors(root)))

    def test_validation_workflow_must_not_push(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            workflow = root / ".github" / "workflows" / "validate-workshop.yml"
            workflow.write_text(workflow.read_text(encoding="utf-8") + "      - run: git push\n", encoding="utf-8")
            self.assertTrue(any("non deve modificare" in error for error in self.metadata_errors(root)))


if __name__ == "__main__":
    unittest.main()
