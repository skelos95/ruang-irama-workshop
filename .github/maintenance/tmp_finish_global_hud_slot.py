from pathlib import Path


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 occurrence, found {count}")
    return text.replace(old, new, 1)

# 1) Static grid expectations now use the frozen global slot loop index.
path = Path("tests/test_dummy_bots.py")
text = path.read_text(encoding="utf-8")
text = replace_once(text, '            self.assertIn("1 + Event Player.UrutanHUD", source)\n', '            self.assertIn("1 + Evaluate Once(Globale.IndeksPemilih)" if source is self.it else "1 + Evaluate Once(Global.IndeksPemilih)", source)\n', "dummy left order")
text = replace_once(text, '            self.assertIn("-13 + Event Player.UrutanHUD", source)\n', '            self.assertIn("-13 + Evaluate Once(Globale.IndeksPemilih)" if source is self.it else "-13 + Evaluate Once(Global.IndeksPemilih)", source)\n', "dummy right order")
text = replace_once(text, '            self.assertNotIn("-99 + Event Player.UrutanHUD", source)\n', '            self.assertNotIn("-99 + Evaluate Once(Globale.IndeksPemilih)" if source is self.it else "-99 + Evaluate Once(Global.IndeksPemilih)", source)\n', "dummy no legacy order")
path.write_text(text, encoding="utf-8")

# 2) Runtime cached-name test follows the persistent slot identity tables.
path = Path("tests/test_runtime_maintenance.py")
text = path.read_text(encoding="utf-8")
start = text.index("    def test_cached_player_name_drives_roster_and_world_text(self):\n")
end = text.index("    def test_aim_scans_are_scheduler_cached(self):\n", start)
replacement = '''    def test_cached_player_name_drives_roster_and_world_text(self):
        for source, global_name, rule_kw in ((self.it, "Globale", "regola"), (self.en, "Global", "rule")):
            self.assertIn("107: NamaTampilan", source)
            self.assertIn("63: PemainSlotHUD", source)
            self.assertIn("64: NamaSlotHUD", source)

            classifier = source.split(f'{rule_kw}("02 - Pemain: Pisahkan manusia dari pasukan kaleng")', 1)[1].split(f'{rule_kw}("02b - HUD Pemain', 1)[0]
            self.assertIn('Event Player.NamaTampilan = Evaluate Once(Custom String("{0}", Event Player));', classifier)
            self.assertIn(f'{global_name}.PemainSlotHUD[Event Player.UrutanHUD] = Event Player;', classifier)
            self.assertIn(f'{global_name}.NamaSlotHUD[Event Player.UrutanHUD] = Event Player.NamaTampilan;', classifier)

            roster = source.split(f'{rule_kw}("00b - HUD Roster: Dua belas slot global permanen")', 1)[1].split(f'{rule_kw}("00a1 - Umum:', 1)[0]
            slot = f'Evaluate Once({global_name}.IndeksPemilih)'
            self.assertIn(f'{global_name}.NamaSlotHUD[{slot}] != Custom String("")', roster)
            self.assertIn(f'Custom String("{{0}} - {{1}} MIN", {global_name}.NamaSlotHUD[{slot}]', roster)
            self.assertIn(f'Custom String("{{0}} - {{1}}", {global_name}.NamaSlotHUD[{slot}]', roster)
            self.assertIn(f'{global_name}.PemainSlotHUD[{slot}]', roster)

            inspect = source.split(f'{rule_kw}("13 - Intip Pahlawan: Nama mengikuti target bidikan tanpa Wait")', 1)[1].split(f'{rule_kw}("16a - Anran', 1)[0]
            self.assertIn(f'{global_name}.NamaSlotHUD[Player Variable(Event Player.TargetInspeksi, UrutanHUD)]', inspect)

            teleport = source.split(f'{rule_kw}("19d - Teleportasi Jongkok: Buat ulang nama saat target berubah")', 1)[1].split(f'{rule_kw}("19e - Teleportasi Jongkok', 1)[0]
            self.assertIn(f'{global_name}.NamaSlotHUD[Player Variable(Event Player.CalonTargetTeleportasi, UrutanHUD)]', teleport)

            fast = source.split(f'{rule_kw}("89a - Subrutin: Proses status cepat pemain")', 1)[1].split(f'{rule_kw}("89b - Subrutin', 1)[0]
            cache_invalid = f'Or({global_name}.PemainAktif.NamaTampilan == Null, {global_name}.PemainAktif.NamaTampilan == Custom String(""))'
            self.assertIn(cache_invalid, fast)
            self.assertIn(f'{global_name}.NamaSlotHUD[{global_name}.PemainAktif.UrutanHUD] != Custom String("")', fast)
            self.assertIn(f'{global_name}.PemainAktif.NamaTampilan = {global_name}.NamaSlotHUD[{global_name}.PemainAktif.UrutanHUD];', fast)
            self.assertIn(f'Custom String("{{0}}", {global_name}.PemainAktif) != Custom String("")', fast)
            self.assertIn(f'{global_name}.PemainAktif.NamaTampilan = Evaluate Once(Custom String("{{0}}", {global_name}.PemainAktif));', fast)
            self.assertLess(fast.index(cache_invalid), fast.index(f"{global_name}.PemainAktif.TimTerakhir != Team Of({global_name}.PemainAktif)"))

'''
text = text[:start] + replacement + text[end:]
path.write_text(text, encoding="utf-8")

# 3) Strengthen validator coverage for the new global renderer and player->slot binding.
path = Path("tools/validate_workshop.py")
text = path.read_text(encoding="utf-8")
old = '''                checks.require(
                    "Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)]" in calls[0].raw,
                    f"renderer roster globale {side}: occupante non letto dallo slot",
                )
        checks.require(
            "Player Variable(Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)], WarnaNama)"
            in global_slot_roster.body,
            "renderer roster globale non segue Name Color dell'occupante corrente",
        )
        checks.require(
            "Player Variable(Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)], MusikKhusus)"
            in global_slot_roster.body,
            "renderer roster globale non conserva il profilo musicale speciale",
        )
'''
new = '''                checks.require(
                    "Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)]" in calls[0].raw,
                    f"renderer roster globale {side}: occupante non letto dallo slot",
                )
                checks.equal(calls[0].args[3].strip(), "Null",
                             f"renderer roster globale {side}: Text deve essere Null")
                if side == "Left":
                    outer_rows = [
                        custom for custom in iter_calls(calls[0].args[2], "Custom String")
                        if custom.args and parse_literal(custom.args[0]) == "{0}{1}{2}"
                    ]
                    checks.equal(len(outer_rows), 1,
                                 "renderer roster globale Left: diagnostica non integrata nel Subheader")
                    if outer_rows:
                        checks.equal(len(outer_rows[0].args), 4,
                                     "renderer roster globale Left: segmenti Subheader")
                        if len(outer_rows[0].args) == 4:
                            diagnostic_branches = parse_top_level_ternary(outer_rows[0].args[3])
                            checks.require(diagnostic_branches is not None,
                                           "renderer roster globale Left: ternario diagnostica assente")
                            if diagnostic_branches:
                                diagnostic_condition, diagnostic_text, diagnostic_fallback = diagnostic_branches
                                for token in (
                                    "Global.DiagnostikPerforma == True",
                                    "Local Player == Host Player",
                                    "Evaluate Once(Global.IndeksPemilih) == Global.SlotHUDTerakhir",
                                ):
                                    checks.require(token in diagnostic_condition,
                                                   f"renderer roster globale Left: guardia diagnostica assente: {token}")
                                checks.require("10 + Count Of(Filtered Array(Global.HudKiriPemain" in diagnostic_text,
                                               "renderer roster globale Left: conteggio diagnostica non nel ramo visibile")
                                checks.equal(diagnostic_fallback.strip(), 'Custom String("")',
                                             "renderer roster globale Left: fallback diagnostica deve essere stringa vuota")
        checks.require(
            "Player Variable(Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)], WarnaNama)"
            in global_slot_roster.body,
            "renderer roster globale non segue Name Color dell'occupante corrente",
        )
        checks.require(
            "Player Variable(Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)], MusikKhusus) != Null ? Player Variable(Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)], MusikKhusus) : Player Variable(Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)], IndeksGenre)"
            in global_slot_roster.body,
            "profilo speciale roster globale: condizione profilo speciale",
        )
'''
text = replace_once(text, old, new, "global renderer validator detail")

anchor = '''    for forbidden, label in (
        ("Destroy HUD Text(Global.HudKiriPemain[", "destroy righe Left permanenti"),
'''
binding = '''    global_slot_binding = next(
        (
            rule for rule in rules
            if event_type(rule) == "Ongoing - Each Player"
            and "Event Player.HudKiri = Global.HudKiriPemain[Event Player.UrutanHUD];" in rule.body
            and "Event Player.HudKanan = Global.HudKananPemain[Event Player.UrutanHUD];" in rule.body
        ),
        None,
    )
    checks.require(global_slot_binding is not None, "collegamento player ai due handle roster globali assente")
    if global_slot_binding:
        left_alias = "Event Player.HudKiri = Global.HudKiriPemain[Event Player.UrutanHUD];"
        right_alias = "Event Player.HudKanan = Global.HudKananPemain[Event Player.UrutanHUD];"
        ready_alias = "Event Player.HudPemainDibuat = And(Event Player.HudKiri != Null, Event Player.HudKanan != Null);"
        checks.require(ready_alias in global_slot_binding.body,
                       "collegamento slot globale: ready flag deve verificare entrambi gli handle")
        if ready_alias in global_slot_binding.body:
            checks.require(
                global_slot_binding.body.index(left_alias) < global_slot_binding.body.index(right_alias) < global_slot_binding.body.index(ready_alias),
                "collegamento slot globale: HudPemainDibuat dopo entrambi gli handle",
            )
        binding_conditions = rule_block(global_slot_binding, "conditions") or ""
        checks.require("Is Alive(Event Player) == True;" not in binding_conditions,
                       "collegamento slot globale non deve attendere Is Alive")

'''
text = replace_once(text, anchor, binding + anchor, "global binding validator")
path.write_text(text, encoding="utf-8")

# 4) Rewrite the stale semantic mutation tests around global ownership.
path = Path("tests/test_validate_workshop.py")
text = path.read_text(encoding="utf-8")

old = '''    def test_special_player_roster_main_and_locked_renderers_are_guarded(self) -> None:
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
'''
new = '''    def test_special_player_roster_main_and_locked_renderers_are_guarded(self) -> None:
        roster = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Global"
            and "Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)]" in rule.body
            and "Global.HudKananPemain = Append To Array" in rule.body
        )
        roster_mutation = self.replace_in_rule(
            roster,
            "Player Variable(Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)], MusikKhusus) != Null ? Player Variable(Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)], MusikKhusus) : Player Variable(Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)], IndeksGenre)",
            "Player Variable(Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)], MusikKhusus) == Null ? Player Variable(Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)], MusikKhusus) : Player Variable(Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)], IndeksGenre)",
        )
        self.assert_rejected(roster_mutation, "profilo speciale roster globale: condizione profilo speciale")
'''
text = replace_once(text, old, new, "special roster test")

old = '''    def test_left_roster_rows_start_immediately_below_their_label(self) -> None:
        renderer = self.rule(lambda rule: "Event Player.HudKiri = Last Text ID;" in rule.body)
        mutated = self.replace_in_rule(renderer, "1 + Event Player.UrutanHUD", "2 + Event Player.UrutanHUD")
        self.assert_rejected(mutated, "renderer HUD roster Left: ordinamento")

    def test_right_roster_stays_before_the_native_team_status_indicator(self) -> None:
        renderer = self.rule(lambda rule: "Event Player.HudKanan = Last Text ID;" in rule.body)
        mutated = self.replace_in_rule(renderer, "-13 + Event Player.UrutanHUD", "1 + Event Player.UrutanHUD")
        self.assert_rejected(mutated, "renderer HUD roster Right: ordinamento")
'''
new = '''    def test_left_roster_rows_start_immediately_below_their_label(self) -> None:
        renderer = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Global" and "Global.HudKiriPemain = Append To Array" in rule.body)
        mutated = self.replace_in_rule(renderer, "1 + Evaluate Once(Global.IndeksPemilih)", "2 + Evaluate Once(Global.IndeksPemilih)")
        self.assert_rejected(mutated, "renderer roster globale Left: ordinamento per slot congelato")

    def test_right_roster_stays_before_the_native_team_status_indicator(self) -> None:
        renderer = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Global" and "Global.HudKananPemain = Append To Array" in rule.body)
        mutated = self.replace_in_rule(renderer, "-13 + Evaluate Once(Global.IndeksPemilih)", "1 + Evaluate Once(Global.IndeksPemilih)")
        self.assert_rejected(mutated, "renderer roster globale Right: ordinamento per slot congelato")
'''
text = replace_once(text, old, new, "roster order tests")

old = '''    def test_left_roster_text_cannot_reintroduce_the_client_zero(self) -> None:
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
'''
new = '''    def test_left_roster_text_cannot_reintroduce_the_client_zero(self) -> None:
        renderer = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Global" and "Global.HudKiriPemain = Append To Array" in rule.body)
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
        self.assert_rejected(mutated, "renderer roster globale Left: Text deve essere Null")

    def test_left_diagnostics_remain_inside_the_subheader(self) -> None:
        renderer = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Global" and "Global.HudKiriPemain = Append To Array" in rule.body)
        call = next(
            call for call in validator.iter_calls(renderer.body, "Create HUD Text")
            if len(call.args) >= 6 and call.args[4].strip() == "Left"
        )
        outer = next(
            custom for custom in validator.iter_calls(call.args[2], "Custom String")
            if len(custom.args) == 4 and validator.parse_literal(custom.args[0]) == "{0}{1}{2}"
        )
        changed = outer.raw.replace(outer.args[3], 'Custom String("")', 1)
        changed_subheader = call.args[2][:outer.start] + changed + call.args[2][outer.end:]
        absolute = validator.Call(call.name, call.raw, call.args, renderer.start + call.start, renderer.start + call.end)
        mutated = self.replace_call_argument(absolute, 2, changed_subheader)
        self.assert_rejected(mutated, "renderer roster globale Left: ternario diagnostica assente")

    def test_left_diagnostic_fallback_is_an_empty_string_not_null(self) -> None:
        renderer = self.rule(lambda rule: validator.event_type(rule) == "Ongoing - Global" and "Global.HudKiriPemain = Append To Array" in rule.body)
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
        self.assert_rejected(mutated, "renderer roster globale Left: fallback diagnostica deve essere stringa vuota")
'''
text = replace_once(text, old, new, "left global renderer tests")

old = '''    def test_roster_ready_flag_is_written_after_both_recreated_handles(self) -> None:
        roster = self.rule(
            lambda rule: "Event Player.HudKiri = Last Text ID;" in rule.body
            and "Event Player.HudKanan = Last Text ID;" in rule.body
        )
        ready = "\\t\\tEvent Player.HudPemainDibuat = True;\\n"
        self.assertIn(ready, roster.body)
        changed = roster.body.replace(ready, "", 1)
        actions = changed.index("\\tactions\\n\\t{\\n") + len("\\tactions\\n\\t{\\n")
        changed = changed[:actions] + ready + changed[actions:]
        mutated = self.source[:roster.start] + changed + self.source[roster.end:]
        self.assert_rejected(mutated, "dopo entrambi gli handle")

        conditions = validator.rule_block(roster, "conditions") or ""
        self.assertNotIn("Is Alive(Event Player) == True;", conditions)
        mutated = self.replace_in_rule(
            roster,
            "Has Spawned(Event Player) == True;",
            "Has Spawned(Event Player) == True;\\n\\t\\tIs Alive(Event Player) == True;",
        )
        self.assert_rejected(mutated, "non deve attendere Is Alive")
'''
new = '''    def test_roster_ready_flag_is_written_after_both_global_aliases(self) -> None:
        roster = self.rule(
            lambda rule: "Event Player.HudKiri = Global.HudKiriPemain[Event Player.UrutanHUD];" in rule.body
            and "Event Player.HudKanan = Global.HudKananPemain[Event Player.UrutanHUD];" in rule.body
        )
        ready = "\\t\\tEvent Player.HudPemainDibuat = And(Event Player.HudKiri != Null, Event Player.HudKanan != Null);\\n"
        self.assertIn(ready, roster.body)
        changed = roster.body.replace(ready, "", 1)
        actions = changed.index("\\tactions\\n\\t{\\n") + len("\\tactions\\n\\t{\\n")
        changed = changed[:actions] + ready + changed[actions:]
        mutated = self.source[:roster.start] + changed + self.source[roster.end:]
        self.assert_rejected(mutated, "collegamento slot globale: HudPemainDibuat dopo entrambi gli handle")

        conditions = validator.rule_block(roster, "conditions") or ""
        self.assertNotIn("Is Alive(Event Player) == True;", conditions)
        mutated = self.replace_in_rule(
            roster,
            "Has Spawned(Event Player) == True;",
            "Has Spawned(Event Player) == True;\\n\\t\\tIs Alive(Event Player) == True;",
        )
        self.assert_rejected(mutated, "collegamento slot globale non deve attendere Is Alive")
'''
text = replace_once(text, old, new, "ready flag global alias test")

old = '''        token = 'Abort If(Count Of(Filtered Array(All Players(All Teams), And(Is Dummy Bot(Current Array Element) == False, Or(Player Variable(Current Array Element, NamaTampilan) == Event Player.NamaTampilan, Custom String("{0}", Current Array Element) == Event Player.NamaTampilan)))) > 0);'
        mutated = self.replace_in_rule(left, token, 'Abort If(False);')
'''
new = '''        token = 'If(Count Of(Filtered Array(All Players(All Teams), And(Is Dummy Bot(Current Array Element) == False, Or(Player Variable(Current Array Element, NamaTampilan) == Event Player.NamaTampilan, Custom String("{0}", Current Array Element) == Event Player.NamaTampilan)))) > 0);'
        mutated = self.replace_in_rule(left, token, 'If(False);')
'''
text = replace_once(text, old, new, "team switch identity token test")
path.write_text(text, encoding="utf-8")

# 5) Document the architectural change.
path = Path("CHANGELOG.md")
text = path.read_text(encoding="utf-8")
anchor = "## 0.8.1\n"
if anchor not in text:
    raise SystemExit("CHANGELOG 0.8.1 anchor missing")
note = "- Roster team-switch: le 12 righe Left/Right ora appartengono a slot HUD globali permanenti (`PemainSlotHUD` / `NamaSlotHUD`); il cambio squadra riassocia l'occupante senza distruggere o ricreare le righe, e Crouch usa la stessa identità globale.\n"
if note not in text:
    pos = text.index(anchor) + len(anchor)
    text = text[:pos] + "\n" + note + text[pos:]
path.write_text(text, encoding="utf-8")
