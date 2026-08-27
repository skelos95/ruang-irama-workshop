#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "tests" / "test_runtime_maintenance.py"
DUMMY = ROOT / "tests" / "test_dummy_bots.py"
VALIDATE = ROOT / "tests" / "test_validate_workshop.py"


def replace_method(text: str, name: str, body: str) -> str:
    pattern = re.compile(
        rf"^    def {re.escape(name)}\(self\).*?(?=^    def |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one method {name}, found {len(matches)}")
    return text[:matches[0].start()] + body.rstrip() + "\n\n" + text[matches[0].end():]


runtime = RUNTIME.read_text(encoding="utf-8")
runtime = replace_method(runtime, "test_cached_player_name_drives_roster_and_world_text", r'''    def test_cached_player_name_drives_roster_and_world_text(self):
        for source, global_name, rule_kw in ((self.it, "Globale", "regola"), (self.en, "Global", "rule")):
            self.assertIn("107: NamaTampilan", source)
            self.assertIn("63: PemainSlotHUD", source)
            self.assertIn("64: NamaSlotHUD", source)

            classifier = source.split(f'{rule_kw}("02 - Pemain: Pisahkan manusia dari pasukan kaleng")', 1)[1].split(f'{rule_kw}("02b - HUD Pemain', 1)[0]
            self.assertIn('Event Player.NamaTampilan = Evaluate Once(Custom String("{0}", Event Player));', classifier)
            self.assertIn(f'{global_name}.PemainSlotHUD[Event Player.UrutanHUD] = Event Player;', classifier)
            self.assertIn(f'{global_name}.NamaSlotHUD[Event Player.UrutanHUD] = Event Player.NamaTampilan;', classifier)

            init = source.split(f'{rule_kw}("00 - Umum:', 1)[1].split(f'{rule_kw}("00a1 - Umum:', 1)[0]
            slot = f'Evaluate Once({global_name}.IndeksPemilih)'
            self.assertIn(f'{global_name}.NamaSlotHUD[{slot}]', init)
            self.assertIn(f'{global_name}.PemainSlotHUD[{slot}]', init)
            self.assertIn(f'Custom String("{{0}} - {{1}} MIN", {global_name}.NamaSlotHUD[{slot}]', init)
            self.assertIn(f'Custom String("{{0}} - {{1}}", {global_name}.NamaSlotHUD[{slot}]', init)
            self.assertIn(f'{global_name}.HudKiriPemain[{global_name}.IndeksPemilih] = Last Text ID;', init)
            self.assertIn(f'{global_name}.HudKananPemain[{global_name}.IndeksPemilih] = Last Text ID;', init)

            roster = source.split(f'{rule_kw}("02b - HUD Pemain: Hubungkan ke roster global permanen")', 1)[1].split(f'{rule_kw}("03c - Bot/Dummy', 1)[0]
            self.assertNotIn("Create HUD Text(", roster)
            self.assertIn(f'Event Player.HudKiri = {global_name}.HudKiriPemain[Event Player.UrutanHUD];', roster)
            self.assertIn(f'Event Player.HudKanan = {global_name}.HudKananPemain[Event Player.UrutanHUD];', roster)

            inspect = source.split(f'{rule_kw}("13 - Intip Pahlawan: Nama mengikuti target bidikan tanpa Wait")', 1)[1].split(f'{rule_kw}("16a - Anran', 1)[0]
            self.assertIn(f'{global_name}.NamaSlotHUD[Player Variable(Event Player.TargetInspeksi, UrutanHUD)]', inspect)

            teleport = source.split(f'{rule_kw}("19d - Teleportasi Jongkok: Buat ulang nama saat target berubah")', 1)[1].split(f'{rule_kw}("19e - Teleportasi Jongkok', 1)[0]
            self.assertIn(f'{global_name}.NamaSlotHUD[Player Variable(Event Player.CalonTargetTeleportasi, UrutanHUD)]', teleport)

            fast = source.split(f'{rule_kw}("89a - Subrutin: Proses status cepat pemain")', 1)[1].split(f'{rule_kw}("89b - Subrutin', 1)[0]
            cache_invalid = f'Or({global_name}.PemainAktif.NamaTampilan == Null, {global_name}.PemainAktif.NamaTampilan == Custom String(""))'
            self.assertIn(cache_invalid, fast)
            self.assertIn(f'{global_name}.NamaSlotHUD[{global_name}.PemainAktif.UrutanHUD] != Custom String("")', fast)
            self.assertIn(f'{global_name}.PemainAktif.NamaTampilan = {global_name}.NamaSlotHUD[{global_name}.PemainAktif.UrutanHUD];', fast)
            self.assertLess(fast.index(cache_invalid), fast.index(f"{global_name}.PemainAktif.TimTerakhir != Team Of({global_name}.PemainAktif)"))''')

runtime = replace_method(runtime, "test_roster_is_owned_by_persistent_global_hud_slots", r'''    def test_roster_is_owned_by_persistent_global_hud_slots(self):
        for source, global_name, rule_kw in ((self.it, "Globale", "regola"), (self.en, "Global", "rule")):
            self.assertIn(f"{global_name}.PemainSlotHUD = Array(Null, Null, Null, Null, Null, Null, Null, Null, Null, Null, Null, Null);", source)
            zeros = "Array(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)"
            self.assertIn(f"{global_name}.HudKiriPemain = {zeros};", source)
            self.assertIn(f"{global_name}.HudKananPemain = {zeros};", source)

            init = source.split(f'{rule_kw}("00 - Umum:', 1)[1].split(f'{rule_kw}("00a1 - Umum:', 1)[0]
            self.assertIn("For Global Variable(IndeksPemilih, 0, 12, 1);", init)
            self.assertIn(f"{global_name}.HudKiriPemain[{global_name}.IndeksPemilih] = Last Text ID;", init)
            self.assertIn(f"{global_name}.HudKananPemain[{global_name}.IndeksPemilih] = Last Text ID;", init)

            player_bind = source.split(f'{rule_kw}("02b - HUD Pemain: Hubungkan ke roster global permanen")', 1)[1].split(f'{rule_kw}("03c - Bot/Dummy', 1)[0]
            self.assertEqual(player_bind.count("Create HUD Text("), 0)
            self.assertIn(f"{global_name}.PemainSlotHUD[Event Player.UrutanHUD] == Event Player;", player_bind)
            self.assertIn(f"Event Player.HudKiri = {global_name}.HudKiriPemain[Event Player.UrutanHUD];", player_bind)
            self.assertIn(f"Event Player.HudKanan = {global_name}.HudKananPemain[Event Player.UrutanHUD];", player_bind)

            classifier = source.split(f'{rule_kw}("02 - Pemain: Pisahkan manusia dari pasukan kaleng")', 1)[1].split(f'{rule_kw}("02b - HUD Pemain', 1)[0]
            self.assertIn(f"Event Player.UrutanHUD = Index Of Array Value({global_name}.NamaSlotHUD, Event Player.NamaTampilan);", classifier)
            self.assertIn(f"{global_name}.PemainManusia[{global_name}.IndeksKeluar] = Event Player;", classifier)
            self.assertIn(f"{global_name}.PemainSlotHUD[Event Player.UrutanHUD] = Event Player;", classifier)

            cleanup = source.split(f'{rule_kw}("93c - Subrutin:', 1)[1].split(f'{rule_kw}("94 - Subrutin:', 1)[0]
            self.assertNotIn(f"Destroy HUD Text({global_name}.HudKiriPemain[", cleanup)
            self.assertNotIn(f"Destroy HUD Text({global_name}.HudKananPemain[", cleanup)
            self.assertIn(f"{global_name}.PemainSlotHUD[{global_name}.IndeksUtangKeluar] = Null;", cleanup)
            self.assertNotIn(f'{global_name}.NamaSlotHUD[{global_name}.IndeksUtangKeluar] = Custom String("");', cleanup)
            self.assertNotIn("Modify Global Variable(SlotHUDTersedia, Append To Array", cleanup)

            self.assertIn(f"{global_name}.NamaSlotHUD[Player Variable(Event Player.TargetInspeksi, UrutanHUD)]", source)
            self.assertIn(f"{global_name}.NamaSlotHUD[Player Variable(Event Player.CalonTargetTeleportasi, UrutanHUD)]", source)''')

runtime = replace_method(runtime, "test_roster_bootstrap_depends_only_on_persistent_slot_identity", r'''    def test_roster_bootstrap_depends_only_on_persistent_slot_identity(self):
        for source, global_name, rule_kw in ((self.it, "Globale", "regola"), (self.en, "Global", "rule")):
            roster = source.split(f'{rule_kw}("02b - HUD Pemain: Hubungkan ke roster global permanen")', 1)[1].split(f'{rule_kw}("03c - Bot/Dummy', 1)[0]
            self.assertNotIn("Has Spawned(Event Player) == True;", roster)
            self.assertNotIn("Event Player.TimTerakhir == Team Of(Event Player);", roster)
            self.assertNotIn("Event Player.SegarkanRosterTertunda == False;", roster)
            self.assertNotIn("Event Player.NamaTampilan != Null;", roster)
            self.assertNotIn(f'{global_name}.NamaSlotHUD[Event Player.UrutanHUD] != Custom String("");', roster)
            self.assertIn(f"{global_name}.PemainSlotHUD[Event Player.UrutanHUD] == Event Player;", roster)
            self.assertIn("Event Player.UrutanHUD >= 0;", roster)
            self.assertIn("Event Player.UrutanHUD < 12;", roster)
            self.assertIn("Event Player.HudPemainDibuat == False;", roster)
            self.assertEqual(roster.count("Create HUD Text("), 0)''')

runtime = replace_method(runtime, "test_registered_team_switch_never_destroys_roster_or_hides_crouch_target", r'''    def test_registered_team_switch_never_destroys_roster_or_hides_crouch_target(self):
        for source, global_name, rule_kw in ((self.it, "Globale", "regola"), (self.en, "Global", "rule")):
            fast = source.split(f'{rule_kw}("89a - Subrutin: Proses status cepat pemain")', 1)[1].split(f'{rule_kw}("89b - Subrutin: Proses siklus pemain 10 Hz")', 1)[0]
            self.assertIn(f"{global_name}.PemainAktif.TimTerakhir != Team Of({global_name}.PemainAktif)", fast)
            self.assertNotIn(f"{global_name}.PemainAktif.SegarkanRosterTertunda = True;", fast)
            self.assertNotIn(f"{global_name}.PemainAktif.HudPemainDibuat = False;", fast)
            self.assertNotIn(f"Destroy HUD Text({global_name}.HudKiriPemain[", fast)
            self.assertNotIn(f"Destroy HUD Text({global_name}.HudKananPemain[", fast)
            self.assertEqual(source.count("Player Variable(Current Array Element, SegarkanRosterTertunda) == False"), 0)
            roster = source.split(f'{rule_kw}("02b - HUD Pemain', 1)[1].split(f'{rule_kw}("03c - Bot/Dummy', 1)[0]
            self.assertNotIn("Event Player.SegarkanRosterTertunda == False;", roster)
            self.assertNotIn("If(Event Player.SegarkanRosterTertunda == True);", roster)
            self.assertNotIn("Create HUD Text(", roster)''')

runtime = replace_method(runtime, "test_team_switch_is_lightweight_and_leave_cleanup_is_exact", r'''    def test_team_switch_is_lightweight_and_leave_cleanup_is_exact(self):
        for source, global_name, rule_kw in ((self.it, "Globale", "regola"), (self.en, "Global", "rule")):
            fast = source.split(f'{rule_kw}("89a - Subrutin: Proses status cepat pemain")', 1)[1].split(f'{rule_kw}("89b - Subrutin: Proses siklus pemain 10 Hz")', 1)[0]
            for token in (
                f"Array Contains({global_name}.PemainManusia, {global_name}.PemainAktif) == True",
                f"{global_name}.PemainAktif.TimTerakhir != Team Of({global_name}.PemainAktif)",
                f"{global_name}.PemainAktif.TimTerakhir = Team Of({global_name}.PemainAktif);",
                f"{global_name}.PemainAktif.Manusia = True;",
                f"{global_name}.PemainAktif.SudahDiperiksa = True;",
                f"{global_name}.PemainAktif.SudahSiap = True;",
                f"{global_name}.PemainAktif.PernahDisiapkan = True;",
                f"Disable Game Mode HUD({global_name}.PemainAktif);",
                f"Disable Game Mode In-World UI({global_name}.PemainAktif);",
            ):
                self.assertIn(token, fast)
            for token in (
                f"{global_name}.PemainAktif.SegarkanRosterTertunda = True;",
                f"Destroy HUD Text({global_name}.HudKiriPemain[",
                f"Destroy HUD Text({global_name}.HudKananPemain[",
                f"{global_name}.PemainAktif.HudKiri = Null;",
                f"{global_name}.PemainAktif.HudKanan = Null;",
                f"{global_name}.PemainAktif.HudPemainDibuat = False;",
                "Call Subroutine(BersihkanPemain);",
                "Call Subroutine(SiapkanPemain);",
            ):
                self.assertNotIn(token, fast)

            classifier = source.split(f'{rule_kw}("02 - Pemain: Pisahkan manusia dari pasukan kaleng")', 1)[1].split(f'{rule_kw}("02b - HUD Pemain', 1)[0]
            self.assertIn(f"Array Contains({global_name}.PemainManusia, Event Player) == False;", classifier)
            no_slot_guard = f'If(And(Count Of({global_name}.SlotHUDTersedia) == 0, Index Of Array Value({global_name}.NamaSlotHUD, Evaluate Once(Custom String("{{0}}", Event Player))) < 0));'
            self.assertIn(no_slot_guard, classifier)
            self.assertIn(f"{global_name}.PemainManusia[{global_name}.IndeksKeluar] = Event Player;", classifier)
            self.assertNotIn("Server Load < 150", classifier)

            roster = source.split(f'{rule_kw}("02b - HUD Pemain', 1)[1].split(f'{rule_kw}("03c - Bot/Dummy', 1)[0]
            self.assertNotIn("Event Player.TimTerakhir == Team Of(Event Player);", roster)
            self.assertNotIn("Event Player.SegarkanRosterTertunda", roster)
            self.assertNotIn("Is Alive(Event Player) == True;", roster)
            self.assertNotIn("Server Load < 150", roster)
            self.assertNotIn("Create HUD Text(", roster)

            left = source.split(f'{rule_kw}("04 - Pemain Keluar: Bersihkan hanya saat benar-benar keluar")', 1)[1].split(f'{rule_kw}("04g - Utama global:', 1)[0]
            self.assertIn("Wait(0.500, Ignora condizione);" if global_name == "Globale" else "Wait(0.500, Ignore Condition);", left)
            same_identity = left.index("Count Of(Filtered Array(All Players(All Teams)")
            self.assertLess(left.index("Abort;", same_identity), left.index("Call Subroutine(BersihkanPemain);", same_identity))
            self.assertNotIn(f"{global_name}.PemainManusia[{global_name}.IndeksKeluar] = {global_name}.PemainPengganti;", left)

            cleanup = source.split(f'{rule_kw}("93c - Subrutin:', 1)[1].split(f'{rule_kw}("94 - Subrutin:', 1)[0]
            self.assertIn(f"{global_name}.PemainSlotHUD[{global_name}.IndeksUtangKeluar] = Null;", cleanup)
            self.assertNotIn(f"Destroy HUD Text({global_name}.HudKiriPemain[", cleanup)
            self.assertNotIn(f"Destroy HUD Text({global_name}.HudKananPemain[", cleanup)
            self.assertNotIn(f'{global_name}.NamaSlotHUD[{global_name}.IndeksUtangKeluar] = Custom String("");', cleanup)''')
RUNTIME.write_text(runtime, encoding="utf-8")


dummy = DUMMY.read_text(encoding="utf-8")
dummy = dummy.replace("1 + Evaluate Once(Event Player.UrutanHUD)", "1 + Evaluate Once(Global.IndeksPemilih)")
dummy = dummy.replace("-13 + Evaluate Once(Event Player.UrutanHUD)", "-13 + Evaluate Once(Global.IndeksPemilih)")
dummy = dummy.replace("-99 + Evaluate Once(Event Player.UrutanHUD)", "-99 + Evaluate Once(Global.IndeksPemilih)")
DUMMY.write_text(dummy, encoding="utf-8")


validate = VALIDATE.read_text(encoding="utf-8")
validate = replace_method(validate, "test_special_player_roster_main_and_locked_renderers_are_guarded", r'''    def test_special_player_roster_main_and_locked_renderers_are_guarded(self) -> None:
        roster = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Global"
            and "Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)]" in rule.body
            and "Global.HudKananPemain[Global.IndeksPemilih] = Last Text ID;" in rule.body
        )
        roster_mutation = self.replace_in_rule(
            roster,
            "Player Variable(Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)], MusikKhusus) != Null ? Player Variable(Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)], MusikKhusus) : Player Variable(Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)], IndeksGenre)",
            "Player Variable(Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)], MusikKhusus) == Null ? Player Variable(Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)], MusikKhusus) : Player Variable(Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)], IndeksGenre)",
        )
        self.assert_rejected(roster_mutation, "profilo speciale roster globale: condizione profilo speciale")

        main = self.rule(lambda rule: validator.subroutine_target(rule) == "GambarUtama")
        main_mutation = self.replace_in_rule(
            main,
            'Custom String("2 - MUSIK\\nSAAT INI: {0}", Event Player.MusikKhusus != Null',
            'Custom String("2 - MUSIK\\nSAAT INI: {0}", Event Player.MusikKhusus == Null',
        )
        self.assert_rejected(main_mutation, "profilo speciale menu principale: condizione profilo speciale")

        music = self.rule(lambda rule: validator.subroutine_target(rule) == "GambarMusik")
        music_mutation = self.replace_in_rule(music, "Event Player.MusikKhusus != Null ?", "Event Player.MusikKhusus == Null ?")
        self.assert_rejected(music_mutation, "profilo speciale pagina musica")''')

validate = validate.replace(
    'self.assert_rejected(mutated, "numero HUD fissi nella regola iniziale")',
    'self.assert_rejected(mutated, "dieci HUD fissi più due renderer roster permanenti nella regola iniziale")',
    1,
)

validate = replace_method(validate, "test_left_roster_rows_start_immediately_below_their_label", r'''    def test_left_roster_rows_start_immediately_below_their_label(self) -> None:
        renderer = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Global" and "Global.HudKiriPemain[Global.IndeksPemilih] = Last Text ID;" in rule.body)
        mutated = self.replace_in_rule(renderer, "1 + Evaluate Once(Global.IndeksPemilih)", "2 + Evaluate Once(Global.IndeksPemilih)")
        self.assert_rejected(mutated, "renderer roster globale Left: ordinamento per slot congelato")''')

validate = replace_method(validate, "test_right_roster_stays_before_the_native_team_status_indicator", r'''    def test_right_roster_stays_before_the_native_team_status_indicator(self) -> None:
        renderer = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Global" and "Global.HudKananPemain[Global.IndeksPemilih] = Last Text ID;" in rule.body)
        mutated = self.replace_in_rule(renderer, "-13 + Evaluate Once(Global.IndeksPemilih)", "1 + Evaluate Once(Global.IndeksPemilih)")
        self.assert_rejected(mutated, "renderer roster globale Right: ordinamento per slot congelato")''')

validate = replace_method(validate, "test_left_roster_text_cannot_reintroduce_the_client_zero", r'''    def test_left_roster_text_cannot_reintroduce_the_client_zero(self) -> None:
        renderer = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Global" and "Global.HudKiriPemain[Global.IndeksPemilih] = Last Text ID;" in rule.body)
        call = next(
            call for call in validator.iter_calls(renderer.body, "Create HUD Text")
            if len(call.args) >= 6 and call.args[4].strip() == "Left" and call.args[5].strip() == "1 + Evaluate Once(Global.IndeksPemilih)"
        )
        absolute = validator.Call(call.name, call.raw, call.args, renderer.start + call.start, renderer.start + call.end)
        mutated = self.replace_call_argument(absolute, 3, 'Global.DiagnostikPerforma == True ? Custom String("diagnostics") : Null')
        self.assert_rejected(mutated, "renderer roster globale Left: Text deve essere Null")''')

validate = replace_method(validate, "test_left_diagnostics_remain_inside_the_subheader", r'''    def test_left_diagnostics_remain_inside_the_subheader(self) -> None:
        renderer = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Global" and "Global.HudKiriPemain[Global.IndeksPemilih] = Last Text ID;" in rule.body)
        call = next(
            call for call in validator.iter_calls(renderer.body, "Create HUD Text")
            if len(call.args) >= 6 and call.args[4].strip() == "Left" and call.args[5].strip() == "1 + Evaluate Once(Global.IndeksPemilih)"
        )
        outer = next(custom for custom in validator.iter_calls(call.args[2], "Custom String") if len(custom.args) == 4 and validator.parse_literal(custom.args[0]) == "{0}{1}{2}")
        changed = outer.raw.replace(outer.args[3], 'Custom String("")', 1)
        changed_subheader = call.args[2][:outer.start] + changed + call.args[2][outer.end:]
        absolute = validator.Call(call.name, call.raw, call.args, renderer.start + call.start, renderer.start + call.end)
        mutated = self.replace_call_argument(absolute, 2, changed_subheader)
        self.assert_rejected(mutated, "renderer roster globale Left: ternario diagnostica assente")''')

validate = replace_method(validate, "test_left_diagnostic_fallback_is_an_empty_string_not_null", r'''    def test_left_diagnostic_fallback_is_an_empty_string_not_null(self) -> None:
        renderer = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Global" and "Global.HudKiriPemain[Global.IndeksPemilih] = Last Text ID;" in rule.body)
        call = next(
            call for call in validator.iter_calls(renderer.body, "Create HUD Text")
            if len(call.args) >= 6 and call.args[4].strip() == "Left" and call.args[5].strip() == "1 + Evaluate Once(Global.IndeksPemilih)"
        )
        outer = next(custom for custom in validator.iter_calls(call.args[2], "Custom String") if len(custom.args) == 4 and validator.parse_literal(custom.args[0]) == "{0}{1}{2}")
        diagnostic = outer.args[3]
        self.assertTrue(diagnostic.rstrip().endswith('Custom String("")'))
        changed_diagnostic = diagnostic.rsplit('Custom String("")', 1)[0] + "Null"
        changed_subheader = call.args[2][:outer.start] + outer.raw.replace(diagnostic, changed_diagnostic, 1) + call.args[2][outer.end:]
        absolute = validator.Call(call.name, call.raw, call.args, renderer.start + call.start, renderer.start + call.end)
        mutated = self.replace_call_argument(absolute, 2, changed_subheader)
        self.assert_rejected(mutated, "renderer roster globale Left: fallback diagnostica deve essere stringa vuota")''')

validate = replace_method(validate, "test_roster_ready_flag_is_written_after_both_global_aliases", r'''    def test_roster_ready_flag_is_written_after_both_global_aliases(self) -> None:
        roster = self.rule(
            lambda rule: "Event Player.HudKiri = Global.HudKiriPemain[Event Player.UrutanHUD];" in rule.body
            and "Event Player.HudKanan = Global.HudKananPemain[Event Player.UrutanHUD];" in rule.body
        )
        ready = "\t\tEvent Player.HudPemainDibuat = And(And(Event Player.HudKiri != Null, Event Player.HudKiri != 0), And(Event Player.HudKanan != Null, Event Player.HudKanan != 0));\n"
        self.assertIn(ready, roster.body)
        changed = roster.body.replace(ready, "", 1)
        actions = changed.index("\tactions\n\t{\n") + len("\tactions\n\t{\n")
        changed = changed[:actions] + ready + changed[actions:]
        mutated = self.source[:roster.start] + changed + self.source[roster.end:]
        self.assert_rejected(mutated, "collegamento slot globale: HudPemainDibuat dopo entrambi gli handle")

        conditions = validator.rule_block(roster, "conditions") or ""
        self.assertNotIn("Is Alive(Event Player) == True;", conditions)
        mutated = self.replace_in_rule(
            roster,
            "Event Player.HudPemainDibuat == False;",
            "Event Player.HudPemainDibuat == False;\n\t\tIs Alive(Event Player) == True;",
        )
        self.assert_rejected(mutated, "collegamento slot globale non deve attendere Is Alive")''')

validate = replace_method(validate, "test_lazy_roster_rows_require_assigned_identity_before_creation", r'''    def test_lazy_roster_rows_require_assigned_identity_before_creation(self) -> None:
        renderer = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Global"
            and "For Global Variable(IndeksPemilih, 0, 12, 1);" in rule.body
            and "Global.HudKiriPemain[Global.IndeksPemilih] = Last Text ID;" in rule.body
            and "Global.HudKananPemain[Global.IndeksPemilih] = Last Text ID;" in rule.body
        )
        self.assertEqual(
            len([call for call in validator.iter_calls(renderer.body, "Create HUD Text") if len(call.args) >= 6 and call.args[5].strip() in {"1 + Evaluate Once(Global.IndeksPemilih)", "-13 + Evaluate Once(Global.IndeksPemilih)"}]),
            2,
        )
        self.assertIn("Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)] != Null ?", renderer.body)
        self.assertIn("Global.NamaSlotHUD[Evaluate Once(Global.IndeksPemilih)]", renderer.body)
        binder = self.rule(lambda rule: "Event Player.HudKiri = Global.HudKiriPemain[Event Player.UrutanHUD];" in rule.body)
        self.assertNotIn("Create HUD Text(", binder.body)
        self.assertNotIn("Has Spawned(Event Player) == True;", validator.rule_block(binder, "conditions") or "")''')

validate = replace_method(validate, "test_pending_roster_refresh_cannot_block_roster_bootstrap", r'''    def test_pending_roster_refresh_cannot_block_roster_bootstrap(self) -> None:
        roster = self.rule(
            lambda rule: "Event Player.HudKiri = Global.HudKiriPemain[Event Player.UrutanHUD];" in rule.body
            and "Event Player.HudKanan = Global.HudKananPemain[Event Player.UrutanHUD];" in rule.body
        )
        conditions = validator.rule_block(roster, "conditions") or ""
        self.assertNotIn("SegarkanRosterTertunda", conditions)
        self.assertNotIn("SegarkanRosterTertunda", roster.body)
        self.assertNotIn("Create HUD Text(", roster.body)
        self.assertIn("Global.PemainSlotHUD[Event Player.UrutanHUD] == Event Player;", conditions)''')

validate = replace_method(validate, "test_team_switch_rebinds_stale_entity_in_place", r'''    def test_team_switch_rebinds_stale_entity_in_place(self) -> None:
        classifier = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and 'Event Player.NamaTampilan = Evaluate Once(Custom String("{0}", Event Player));' in rule.body
            and "Global.NamaSlotHUD" in rule.body
        )
        mutated = self.replace_in_rule(
            classifier,
            "Global.PemainManusia[Global.IndeksKeluar] = Event Player;",
            "Global.PemainManusia[Global.IndeksKeluar] = Global.PemainPengganti;",
        )
        self.assert_rejected(mutated, "team-switch non sostituisce immediatamente il riferimento entità nel medesimo slot roster")''')

VALIDATE.write_text(validate, encoding="utf-8")

# Guard against the exact stale selectors that caused the official PR run to fail.
for path in (RUNTIME, VALIDATE):
    text = path.read_text(encoding="utf-8")
    if '02b - HUD Pemain: Hubungkan ke slot global' in text:
        raise RuntimeError(f"stale 02b title remains in {path}")

print("updated stale tests for permanent global roster architecture")
