from __future__ import annotations

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

    def inject_action(self, rule: validator.Rule, action: str) -> str:
        closing = rule.body.rfind("\n\t}")
        self.assertGreater(closing, 0)
        changed = rule.body[:closing] + f"\n\t\t{action}" + rule.body[closing:]
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

    def test_declaration_indices_must_be_compact(self) -> None:
        globals_, _, _, _ = validator.declaration_entries(self.source)
        token = f"\t\t{globals_[1].index}: {globals_[1].name}"
        mutated = self.replace_once(token, f"\t\t{globals_[1].index + 1}: {globals_[1].name}")
        self.assert_rejected(mutated, "indici global compatti")

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

    def test_camera_requires_menu_closed(self) -> None:
        camera = self.rule(lambda rule: "Button(Interact)" in rule.body and "Wait(0.500, Abort When False)" in rule.body and "ModeKamera" in rule.body)
        mutated = self.replace_in_rule(camera, "Event Player.MenuTerbuka == False;", "Event Player.MenuTerbuka == True;")
        self.assert_rejected(mutated, "menu chiuso")

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

    def test_join_requires_duplicate_guard(self) -> None:
        joined = self.rule(lambda rule: validator.event_type(rule) == "Player Joined Match")
        mutated = self.replace_in_rule(joined, "Event Player.PindahTimDiproses == False;", "Event Player.PindahTimDiproses == True;")
        self.assert_rejected(mutated, "PindahTimDiproses")

    def test_roster_append_is_idempotent(self) -> None:
        classifier = self.rule(lambda rule: "Append To Array(Global.PemainManusia, Event Player)" in rule.body)
        mutated = self.replace_in_rule(classifier, "Abort If(Array Contains(Global.PemainManusia, Event Player));", "")
        self.assert_rejected(mutated, "due volte il roster")

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
