from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import validate_workshop as validator  # noqa: E402


class ValidatorNegativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = validator.SOURCE.read_text(encoding="utf-8")

    def rules(self, source: str) -> list[validator.Rule]:
        self.assertEqual(validator.balanced_errors(source), [])
        return validator.extract_rules(source)

    def test_semantic_action_inside_comment_does_not_count(self) -> None:
        calls = validator.call_texts(self.source, "Disable Nameplates")
        self.assertGreaterEqual(len(calls), 1)
        simulated = self.source.replace(calls[0], f'"{calls[0]}"', 1)
        self.assertEqual(
            len(validator.call_texts(simulated, "Disable Nameplates")),
            len(calls) - 1,
        )

    def test_commented_leave_identity_capture_is_rejected(self) -> None:
        target = "Global.PemainPembersihan = Global.IndeksKeluar >= 0 ? Global.PemainManusia[Global.IndeksKeluar] : Event Player;"
        self.assertIn(target, self.source)
        mutated = self.source.replace(target, f'"{target}"', 1)
        checks = validator.Checks()
        validator.check_cleanup_and_revenge(checks, mutated, self.rules(mutated))
        self.assertTrue(
            any("diretta → slot HUD → nome" in error for error in checks.errors),
            checks.errors,
        )

    def test_array_assignment_inside_comment_is_rejected(self) -> None:
        with self.assertRaisesRegex(validator.ParseError, "assegnazione Array non trovata"):
            validator.array_body(
                '"Global.DaftarPalsu = Array(1, 2, 3);"\n',
                "Global.DaftarPalsu",
            )

    def test_square_and_cross_nested_delimiters_are_rejected(self) -> None:
        for malformed in ("Foo[Bar;", "Foo([)];", "Foo{Bar]};"):
            with self.subTest(malformed=malformed):
                self.assertTrue(validator.balanced_errors(malformed))

    def test_malformed_rule_header_is_rejected(self) -> None:
        with self.assertRaisesRegex(validator.ParseError, "rule malformata"):
            validator.extract_rules("rule(Bad Header)\n{\n}\n")

    def test_unknown_rule_block_and_wrong_section_order_are_rejected(self) -> None:
        typo = self.source.replace("\n\tactions\n\t{", "\n\tactons\n\t{", 1)
        self.assertNotEqual(typo, self.source)
        with self.assertRaisesRegex(validator.ParseError, "blocchi top-level non validi"):
            validator.extract_rules(typo)

        malformed_rules = (
            'rule("ordine") { actions { } event { Ongoing - Global; } }',
            'rule("duplicato") { event { Ongoing - Global; } event { Ongoing - Global; } actions { } }',
        )
        for malformed in malformed_rules:
            with self.subTest(source=malformed):
                with self.assertRaisesRegex(validator.ParseError, "blocchi top-level non validi"):
                    validator.extract_rules(malformed)

    def test_duplicate_declaration_slots_and_names_are_rejected(self) -> None:
        template = """variables
{
    global:
        0: GlobalSatu
        1: GlobalDua
    player:
        0: PlayerSatu
}
subroutines
{
    0: SubrutinSatu
}
"""
        duplicate_slot = template.replace("1: GlobalDua", "0: GlobalDua")
        duplicate_name = template.replace("1: GlobalDua", "1: GlobalSatu")
        for malformed in (duplicate_slot, duplicate_name):
            with self.subTest(source=malformed):
                with self.assertRaisesRegex(validator.ParseError, "duplicati"):
                    validator.declaration_tables(malformed)

    def test_custom_string_placeholder_requires_matching_argument(self) -> None:
        mutated = self.source.replace(
            'Custom String("{0}", Event Player)',
            'Custom String("{0}")',
            1,
        )
        self.assertNotEqual(mutated, self.source)
        global_names, player_names, subroutines = validator.declaration_tables(mutated)
        checks = validator.Checks()
        validator.check_source_structure(
            checks,
            mutated,
            self.rules(mutated),
            global_names,
            player_names,
            subroutines,
        )
        self.assertTrue(
            any("arità placeholder" in error for error in checks.errors),
            checks.errors,
        )

    def test_incomplete_revenge_empty_state_localization_is_rejected(self) -> None:
        mutated = self.source.replace(
            'Custom String("4 - ล้างแค้น")',
            'Custom String("4 - REVENGE")',
            1,
        )
        self.assertNotEqual(mutated, self.source)
        _, _, subroutines = validator.declaration_tables(mutated)
        checks = validator.Checks()
        validator.check_menus(checks, mutated, self.rules(mutated), subroutines)
        self.assertTrue(
            any("stato vuoto non localizzato" in error for error in checks.errors),
            checks.errors,
        )

    def test_visible_text_requires_language_branches(self) -> None:
        mutated, replacements = re.subn(
            r'(Event Player\.IndeksBahasa == )1(\s*\? Custom String\(\s*"Selamat datang)',
            r"\g<1>0\2",
            self.source,
            count=1,
        )
        self.assertEqual(replacements, 1)
        checks = validator.Checks()
        validator.check_language_arrays(checks, mutated)
        self.assertTrue(
            any("rami lingua EN/ID/TH" in error for error in checks.errors),
            checks.errors,
        )

    def test_crouch_line_of_sight_filter_is_rejected(self) -> None:
        refresh_at = self.source.index('rule("96 - ')
        mutated = self.source[:refresh_at] + self.source[refresh_at:].replace(
            "Is Alive(Current Array Element)",
            "And(Is Alive(Current Array Element), Is In Line of Sight(Eye Position(Event Player), Eye Position(Current Array Element), All Barriers Block LOS))",
            1,
        )
        self.assertNotEqual(mutated, self.source)
        checks = validator.Checks()
        validator.check_crouch(checks, mutated, self.rules(mutated))
        self.assertTrue(
            any("predicate positivo" in error or "linea di vista" in error for error in checks.errors),
            checks.errors,
        )

    def test_crouch_dead_candidate_must_be_filtered_positively(self) -> None:
        refresh_at = self.source.index('rule("96 - ')
        mutated = self.source[:refresh_at] + self.source[refresh_at:].replace(
            "Is Alive(Current Array Element)",
            "Is Alive(Current Array Element) == False",
            1,
        )
        self.assertNotEqual(mutated, self.source)
        checks = validator.Checks()
        validator.check_crouch(checks, mutated, self.rules(mutated))
        self.assertTrue(
            any("predicate positivo" in error for error in checks.errors),
            checks.errors,
        )

    def test_crouch_distance_and_angle_thresholds_are_rejected(self) -> None:
        mutations = (
            (
                "Current Array Element != Event Player",
                "And(Current Array Element != Event Player, Distance Between(Position Of(Event Player), Position Of(Current Array Element)) < 20)",
            ),
            (
                "Current Array Element != Event Player",
                "And(Current Array Element != Event Player, Angle Between Vectors(Facing Direction Of(Event Player), Direction Towards(Eye Position(Event Player), Eye Position(Current Array Element))) < 30)",
            ),
        )
        refresh_at = self.source.index('rule("96 - ')
        for old, new in mutations:
            with self.subTest(threshold=new):
                mutated = (
                    self.source[:refresh_at]
                    + self.source[refresh_at:].replace(old, new, 1)
                )
                self.assertNotEqual(mutated, self.source)
                checks = validator.Checks()
                validator.check_crouch(checks, mutated, self.rules(mutated))
                self.assertTrue(
                    any(
                        "predicate positivo" in error
                        or "soglie di distanza" in error
                        or "Angle Between Vectors" in error
                        for error in checks.errors
                    ),
                    checks.errors,
                )

    def test_menu_must_not_close_on_death_or_despawn(self) -> None:
        bad_rules = (
            '''
rule("TEST - bad death menu close")
{
    event
    {
        Player Died;
        All;
        All;
    }
    conditions
    {
        Event Player.MenuTerbuka == True;
    }
    actions
    {
        Call Subroutine(TutupMenu);
    }
}
''',
            '''
rule("TEST - bad dead-state menu close")
{
    event
    {
        Ongoing - Each Player;
        All;
        All;
    }
    conditions
    {
        Event Player.MenuTerbuka == True;
        Is Alive(Event Player) == False;
    }
    actions
    {
        Call Subroutine(TutupMenu);
    }
}
''',
        )
        _, _, subroutines = validator.declaration_tables(self.source)
        for bad_rule in bad_rules:
            with self.subTest(bad_rule=bad_rule.splitlines()[1]):
                mutated = self.source + "\n" + bad_rule
                checks = validator.Checks()
                validator.check_menus(checks, mutated, self.rules(mutated), subroutines)
                self.assertTrue(
                    any("non deve chiudere" in error or "non devono chiudere" in error for error in checks.errors),
                    checks.errors,
                )

    def test_crouch_cleanup_requires_or(self) -> None:
        mutated = self.source.replace(
            "Or(Or(Or(Or(Is Button Held(Event Player, Button(Crouch))",
            "Or(Or(And(Or(Is Button Held(Event Player, Button(Crouch))",
            1,
        )
        self.assertNotEqual(mutated, self.source)
        checks = validator.Checks()
        validator.check_crouch(checks, mutated, self.rules(mutated))
        self.assertTrue(
            any("alternative OR" in error for error in checks.errors),
            checks.errors,
        )

    def legacy_test_teleport_without_pre_refresh_identity_capture_is_rejected(self) -> None:
        mutated, replacements = re.subn(
            r"Event Player\.TargetTeleportasiTerkunci\s*=\s*"
            r"Event Player\.DaftarTargetTeleportasi\s*\[\s*"
            r"Event Player\.KursorTeleportasi\s*\]\s*;",
            "Event Player.TargetTeleportasiTerkunci = Null;",
            self.source,
            count=1,
        )
        self.assertEqual(replacements, 1)
        checks = validator.Checks()
        validator.check_teleport(checks, mutated, self.rules(mutated))
        self.assertTrue(
            any("identità non catturata prima del refresh" in error for error in checks.errors),
            checks.errors,
        )

    def legacy_test_teleport_kind_cannot_be_constant_two(self) -> None:
        mutated, replacements = re.subn(
            r"Event Player\.JenisTeleportasiTerkunci\s*=\s*"
            r"Event Player\.KursorTeleportasi\s*<\s*2\s*\?\s*"
            r"Event Player\.KursorTeleportasi\s*:\s*2\s*;",
            "Event Player.JenisTeleportasiTerkunci = 2;",
            self.source,
            count=1,
        )
        self.assertEqual(replacements, 1)
        checks = validator.Checks()
        validator.check_teleport(checks, mutated, self.rules(mutated))
        self.assertTrue(
            any("tipo deve essere catturato esattamente" in error for error in checks.errors),
            checks.errors,
        )

    def legacy_test_teleport_cannot_reread_cursor_after_refresh(self) -> None:
        mutated = self.source.replace(
            "Position Of(Event Player.TargetTeleportasiTerkunci)",
            "Position Of(Event Player.DaftarTargetTeleportasi[Event Player.KursorTeleportasi])",
            1,
        )
        self.assertNotEqual(mutated, self.source)
        checks = validator.Checks()
        validator.check_teleport(checks, mutated, self.rules(mutated))
        self.assertTrue(
            any("riletto per indice dopo il refresh" in error for error in checks.errors),
            checks.errors,
        )

    def test_unkillable_status_is_required(self) -> None:
        mutated = self.source.replace(
            "Set Status(Event Player, Null, Unkillable, 9999);",
            '"Set Status(Event Player, Null, Unkillable, 9999);"',
        )
        self.assertNotEqual(mutated, self.source)
        checks = validator.Checks()
        validator.check_arcade_features(checks, mutated, self.rules(mutated))
        self.assertTrue(any("Set Status" in error for error in checks.errors), checks.errors)

    def test_full_health_reset_to_one_is_required(self) -> None:
        mutated = self.source.replace(
            "Health(Event Player) >= Max Health(Event Player);",
            "Health(Event Player) > Max Health(Event Player);",
            1,
        )
        self.assertNotEqual(mutated, self.source)
        checks = validator.Checks()
        validator.check_arcade_features(checks, mutated, self.rules(mutated))
        self.assertTrue(any("Health(Event Player)" in error for error in checks.errors), checks.errors)

    def test_luck_menu_must_stay_open_and_locked(self) -> None:
        dispatcher_at = self.source.index('rule("05c - ')
        dispatcher_end = self.source.index('\nrule("05d - ', dispatcher_at)
        dispatcher = self.source[dispatcher_at:dispatcher_end]
        dispatcher2 = dispatcher.replace(
            "Event Player.KartuNasibAktif == False;",
            '"Event Player.KartuNasibAktif == False;"',
            1,
        )
        self.assertNotEqual(dispatcher2, dispatcher)
        mutated = self.source[:dispatcher_at] + dispatcher2 + self.source[dispatcher_end:]
        checks = validator.Checks()
        validator.check_arcade_features(checks, mutated, self.rules(mutated))
        self.assertTrue(any("dispatcher menu non bloccato" in error for error in checks.errors), checks.errors)

    def test_luck_red_must_use_speed_lock_without_forcing(self) -> None:
        forcing = self.source.replace(
            "Set Move Speed(Event Player, 0);",
            "Set Move Speed(Event Player, 0);\n\t\t\tStart Forcing Player Position(Event Player, Event Player.PosisiNasibTerkunci, False);",
            1,
        )
        self.assertNotEqual(forcing, self.source)
        checks = validator.Checks()
        validator.check_arcade_features(checks, forcing, self.rules(forcing))
        self.assertTrue(any("posizione forzata" in error for error in checks.errors), checks.errors)

        no_speed_lock = self.source.replace(
            "Set Move Speed(Event Player, 0);",
            '"Set Move Speed(Event Player, 0);"',
            1,
        )
        self.assertNotEqual(no_speed_lock, self.source)
        checks = validator.Checks()
        validator.check_arcade_features(checks, no_speed_lock, self.rules(no_speed_lock))
        self.assertTrue(any("sequenza rosso/verde incompleta" in error for error in checks.errors), checks.errors)

    def test_camera_dead_candidate_is_rejected(self) -> None:
        refresh_at = self.source.index('rule("95 - ')
        mutated = self.source[:refresh_at] + self.source[refresh_at:].replace(
            "Is Alive(Current Array Element)",
            "Is Alive(Current Array Element) == False",
            1,
        )
        checks = validator.Checks()
        _, player_names, _ = validator.declaration_tables(mutated)
        validator.check_camera(checks, mutated, self.rules(mutated), player_names)
        self.assertTrue(any("candidati morti" in error for error in checks.errors), checks.errors)

    def test_teleport_dead_candidate_is_rejected(self) -> None:
        refresh_at = self.source.index('rule("98 - ')
        mutated = self.source[:refresh_at] + self.source[refresh_at:].replace(
            "Is Alive(Current Array Element)",
            "Is Alive(Current Array Element) == False",
            1,
        )
        checks = validator.Checks()
        validator.check_teleport(checks, mutated, self.rules(mutated))
        self.assertTrue(any("candidati morti" in error for error in checks.errors), checks.errors)

    def test_voice_normal_stop_is_required(self) -> None:
        menu_at = self.source.index('rule("10 - Menu:')
        menu_end = self.source.index('\nrule("11 - ', menu_at)
        menu = self.source[menu_at:menu_end]
        menu2 = menu.replace(
            "Stop Modifying Hero Voice Lines(Event Player);",
            '"Stop Modifying Hero Voice Lines(Event Player);"',
            1,
        )
        self.assertNotEqual(menu2, menu)
        mutated = self.source[:menu_at] + menu2 + self.source[menu_end:]
        checks = validator.Checks()
        validator.check_arcade_features(checks, mutated, self.rules(mutated))
        self.assertTrue(any("Stop Modifying Hero Voice Lines" in error for error in checks.errors), checks.errors)

    def test_diagnostics_toggle_condition_cannot_be_a_comment(self) -> None:
        mutated = self.source.replace(
            "Global.DiagnostikPerforma == True",
            'Custom String("Global.DiagnostikPerforma == True") == Custom String("Global.DiagnostikPerforma == True")',
            1,
        )
        self.assertNotEqual(mutated, self.source)
        checks = validator.Checks()
        validator.check_diagnostics(checks, mutated, self.rules(mutated))
        self.assertTrue(
            any("diagnostica integrata nella lista sinistra" in error for error in checks.errors),
            checks.errors,
        )

    def test_workflow_parser_rejects_comment_spoofing_and_write_permissions(self) -> None:
        workflow = validator.WORKFLOW.read_text(encoding="utf-8")
        good_checks = validator.Checks()
        validator.check_workflow_text(good_checks, workflow)
        self.assertEqual(good_checks.errors, [])
        self.assertIn(
            'name: "Gate #1"',
            validator.strip_yaml_comments('name: "Gate #1" # commento'),
        )

        checkout = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
        malicious = (
            workflow.replace(
                f"uses: {checkout} # v7.0.1",
                f"uses: actions/checkout@v4 # {checkout}",
                1,
            ),
            workflow.replace(
                "  validate:\n",
                "  validate:\n    permissions: write-all\n",
                1,
            ),
            workflow.replace("  push:", "  # push:", 1),
            workflow.replace(
                "run: python tools/validate_workshop.py",
                "run: python tools/validate_workshop.py && git push # python tools/validate_workshop.py",
                1,
            ),
        )
        for mutated in malicious:
            with self.subTest(workflow=mutated):
                self.assertNotEqual(mutated, workflow)
                checks = validator.Checks()
                validator.check_workflow_text(checks, mutated)
                self.assertTrue(checks.errors)


    def test_lifecycle_requires_every_player_variable_initialized(self) -> None:
        setup_at = self.source.index('rule("94 - ')
        tail = self.source[setup_at:]
        tail2 = tail.replace(
            "Event Player.PemainDipilih = Null;",
            '"Event Player.PemainDipilih = Null;"',
            1,
        )
        self.assertNotEqual(tail2, tail)
        mutated = self.source[:setup_at] + tail2
        _, player_names, _ = validator.declaration_tables(mutated)
        checks = validator.Checks()
        validator.check_lifecycle_hygiene(checks, mutated, self.rules(mutated), player_names)
        self.assertTrue(any("PemainDipilih" in error and "non inizializzata" in error for error in checks.errors), checks.errors)

    def test_obsolete_luck_state_is_rejected(self) -> None:
        mutated = self.source.replace(
            "\t\t80: JumlahSuara\n",
            "\t\t80: JumlahSuara\n\t\t84: PosisiKartuNasib\n",
            1,
        )
        self.assertNotEqual(mutated, self.source)
        checks = validator.Checks()
        validator.check_arcade_features(checks, mutated, self.rules(mutated))
        self.assertTrue(any("stato obsoleto" in error for error in checks.errors), checks.errors)

    def test_camera_subroutine_must_not_stop_before_start(self) -> None:
        camera_at = self.source.index('rule("93 - ')
        tail = self.source[camera_at:]
        tail2 = tail.replace(
            "\t\tStart Camera(Event Player,",
            "\t\tStop Camera(Event Player);\n\t\tStart Camera(Event Player,",
            1,
        )
        self.assertNotEqual(tail2, tail)
        mutated = self.source[:camera_at] + tail2
        _, player_names, _ = validator.declaration_tables(mutated)
        checks = validator.Checks()
        validator.check_camera(checks, mutated, self.rules(mutated), player_names)
        self.assertTrue(any("micro-scatto" in error for error in checks.errors), checks.errors)

    def test_roster_minutes_need_three_languages(self) -> None:
        mutated = self.source.replace(
            'Custom String("{0} - {1} MENIT", Event Player, Event Player.MenitLobi)',
            'Custom String("{0} - {1} MIN", Event Player, Event Player.MenitLobi)',
            1,
        )
        self.assertNotEqual(mutated, self.source)
        checks = validator.Checks()
        validator.check_localization_and_indonesian_naming(checks, mutated, self.rules(mutated))
        self.assertTrue(any("localizzazione roster/voto" in error for error in checks.errors), checks.errors)


    def test_mixed_language_vote_identifier_is_rejected(self) -> None:
        mutated = self.source.replace("PemimpinSuara", "LeaderVoto", 1)
        self.assertNotEqual(mutated, self.source)
        global_names, player_names, subroutines = validator.declaration_tables(mutated)
        checks = validator.Checks()
        validator.check_source_structure(checks, mutated, self.rules(mutated), global_names, player_names, subroutines)
        self.assertTrue(any("LeaderVoto" in error and "non indonesiano" in error for error in checks.errors), checks.errors)

    def test_english_word_in_rule_title_is_rejected(self) -> None:
        mutated = self.source.replace(
            'rule("18 - Kebal: Pasang kembali status setelah muncul kembali")',
            'rule("18 - Kebal: Pasang kembali status setelah respawn")', 1,
        )
        self.assertNotEqual(mutated, self.source)
        global_names, player_names, subroutines = validator.declaration_tables(mutated)
        checks = validator.Checks()
        validator.check_source_structure(checks, mutated, self.rules(mutated), global_names, player_names, subroutines)
        self.assertTrue(any("respawn" in error and "nome regola" in error for error in checks.errors), checks.errors)


    def test_team_rejoin_must_run_cleanup_before_fresh_setup(self) -> None:
        join_at = self.source.index('rule("01 - Pemain Masuk atau Pindah Tim:')
        join_end = self.source.index('\nrule("01b - ', join_at)
        join_rule = self.source[join_at:join_end]
        mutated_join = join_rule.replace("\t\tCall Subroutine(BersihkanPemain);\n", "", 1)
        self.assertNotEqual(mutated_join, join_rule)
        mutated = self.source[:join_at] + mutated_join + self.source[join_end:]
        _, player_names, _ = validator.declaration_tables(mutated)
        checks = validator.Checks()
        validator.check_lifecycle_hygiene(checks, mutated, self.rules(mutated), player_names)
        self.assertTrue(any("cleanup → setup" in error or "leave/rejoin" in error for error in checks.errors), checks.errors)

    def test_team_rejoin_lock_must_survive_until_new_roster_hud(self) -> None:
        mutated = self.source.replace("\t\tEvent Player.PindahTimDiproses = True;\n\t\tEvent Player.SiklusPemainAktif = True;", "\t\tEvent Player.SiklusPemainAktif = True;", 1)
        self.assertNotEqual(mutated, self.source)
        _, player_names, _ = validator.declaration_tables(mutated)
        checks = validator.Checks()
        validator.check_lifecycle_hygiene(checks, mutated, self.rules(mutated), player_names)
        self.assertTrue(any("cleanup → setup" in error for error in checks.errors), checks.errors)

    def test_cleanup_team_switch_must_find_old_roster_by_slot_or_name(self) -> None:
        target = """		If(Global.IndeksKeluar < 0);
			Global.IndeksKeluar = Index Of Array Value(Mapped Array(Global.PemainManusia, Custom String("{0}", Current Array Element)),
				Custom String("{0}", Event Player));
		End;
"""
        mutated = self.source.replace(target, "", 1)
        self.assertNotEqual(mutated, self.source)
        checks = validator.Checks()
        validator.check_cleanup_and_revenge(checks, mutated, self.rules(mutated))
        self.assertTrue(any("slot HUD → nome" in error for error in checks.errors), checks.errors)

    def test_vote_change_must_clear_previous_choice(self) -> None:
        mutated = self.source.replace(
            "\t\t\t\t\tEvent Player.PemainDipilih = Null;\n\t\t\t\t\tEvent Player.PemainDipilih = Global.PemainManusia[Event Player.KursorPilihan];",
            "\t\t\t\t\tEvent Player.PemainDipilih = Global.PemainManusia[Event Player.KursorPilihan];",
            1,
        )
        self.assertNotEqual(mutated, self.source)
        _, _, subroutines = validator.declaration_tables(mutated)
        checks = validator.Checks()
        validator.check_vote_menu(checks, mutated, self.rules(mutated), subroutines)
        self.assertTrue(any("voto precedente" in error for error in checks.errors), checks.errors)


    def test_vote_global_slot_47_name_must_stay_client_safe(self) -> None:
        mutated = self.source.replace("47: IndeksVote", "47: IndeksHitungSuara", 1)
        self.assertNotEqual(mutated, self.source)
        _, _, subroutines = validator.declaration_tables(mutated)
        checks = validator.Checks()
        validator.check_vote_menu(checks, mutated, self.rules(mutated), subroutines)
        self.assertTrue(any("slot 47" in error for error in checks.errors), checks.errors)


if __name__ == "__main__":
    unittest.main()
