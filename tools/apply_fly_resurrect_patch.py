from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_exact(text: str, old: str, new: str, label: str, count: int = 1) -> str:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"{label}: expected {count} occurrence(s), found {actual}")
    return text.replace(old, new, count)


def replace_method(text: str, start_name: str, next_name: str, body: str) -> str:
    start = text.index(f"    def {start_name}(")
    end = text.index(f"    def {next_name}(", start)
    return text[:start] + body.rstrip() + "\n\n" + text[end:]


def replace_rule_actions(text: str, keyword: str, rule_name: str, actions: str) -> str:
    start = text.index(f'{keyword}("{rule_name}")')
    next_rule = text.find(f'\n\n{keyword}("', start + 1)
    if next_rule < 0:
        next_rule = len(text)
    rule = text[start:next_rule]
    marker = "\n\tazioni\n\t{\n" if keyword == "regola" else "\n\tactions\n\t{\n"
    if marker not in rule:
        raise SystemExit(f"{rule_name}: actions marker missing")
    prefix = rule.split(marker, 1)[0] + marker
    new_rule = prefix + actions.rstrip() + "\n\t}\n}"
    return text[:start] + new_rule + text[next_rule:]


def patch_source(path: Path, g: str, keyword: str) -> None:
    text = path.read_text(encoding="utf-8")
    old_fly = f'''\t\t\tIf(And({g}.PemainAktif.ModeTerbangAktif == True, Magnitude Of(Throttle Of({g}.PemainAktif)) > 0.050));
\t\t\t\t"Impuls pitch hanya mengikuti input maju; input lain tetap ditangani throttle transform agar kontrol lengkap."
\t\t\t\tIf((Z Component Of(Throttle Of({g}.PemainAktif))) > 0.050);
\t\t\t\t\tApply Impulse({g}.PemainAktif, Facing Direction Of({g}.PemainAktif), (Z Component Of(Throttle Of({g}.PemainAktif))) * 9, To World, Cancel Contrary Motion);
\t\t\t\tEnd;
\t\t\tEnd;'''
    new_fly = f'''\t\t\tIf(And({g}.PemainAktif.ModeTerbangAktif == True, (Z Component Of(Throttle Of({g}.PemainAktif))) > 0.050));
\t\t\t\t"Menahan maju mempercepat Fly bertahap sampai 20 m/s; Acceleration Coba Nasib tetap punya prioritas."
\t\t\t\tIf(Or({g}.PemainAktif.EfekNasib != 2, {g}.PemainAktif.EfekNasibBerakhir <= Total Time Elapsed));
\t\t\t\t\tStart Accelerating({g}.PemainAktif, Facing Direction Of({g}.PemainAktif), 6, 20, To World, Direction Rate and Max Speed);
\t\t\t\tEnd;
\t\t\tElse If(And({g}.PemainAktif.ModeTerbangAktif == True, And((Z Component Of(Throttle Of({g}.PemainAktif))) <= 0.050, Or({g}.PemainAktif.EfekNasib != 2, {g}.PemainAktif.EfekNasibBerakhir <= Total Time Elapsed))));
\t\t\t\tStop Accelerating({g}.PemainAktif);
\t\t\tEnd;'''
    text = replace_exact(text, old_fly, new_fly, f"{path}: Fly")

    death_old = "\t\tEvent Player.PosisiMati = Position Of(Event Player);\n\t\tEvent Player.BangkitLompatDipakai = False;"
    death_new = "\t\tEvent Player.PosisiMati = Position Of(Event Player);\n\t\tEvent Player.FisikaHantuTerbangDiterapkan = False;\n\t\tStop Accelerating(Event Player);\n\t\tEvent Player.BangkitLompatDipakai = False;"
    text = replace_exact(text, death_old, death_new, f"{path}: death rearm")

    text = text.replace("Press {0}: resurrect here, or at safety if you fell into the void.", "Press {0}: resurrect at the nearest safe walkable position.")
    text = text.replace("Tekan {0}: bangkit di sini, atau di tempat aman jika jatuh ke jurang.", "Tekan {0}: bangkit di posisi aman terdekat.")
    text = text.replace("กด {0}: ฟื้นที่เดิม หรือจุดปลอดภัยหากตกเหว", "กด {0}: ฟื้นที่ตำแหน่งเดินได้ที่ปลอดภัยใกล้ที่สุด")

    actions = '''\t\tEvent Player.BangkitLompatDipakai = True;
\t\tEvent Player.PosisiBangkitAman = Vector(0, 0, 0);
\t\tEvent Player.PosisiTeleportTujuan = Nearest Walkable Position(Event Player.PosisiMati);
\t\tCall Subroutine(CariPosisiTeleportAman);
\t\tIf(Distance Between(Event Player.PosisiBangkitAman, Vector(0, 0, 0)) <= 0.100);
\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("No safe ground was found. Release {0} and try again.", Input Binding String(Button(Jump))) : Event Player.IndeksBahasa == 1 ? Custom String("Tidak ada tanah aman. Lepaskan {0} lalu coba lagi.", Input Binding String(Button(Jump))) : Custom String("ไม่พบพื้นปลอดภัย ปล่อย {0} แล้วลองอีกครั้ง", Input Binding String(Button(Jump))));
\t\t\tAbort;
\t\tEnd;
\t\tTeleport(Event Player, Event Player.PosisiBangkitAman);
\t\tResurrect(Event Player);
\t\tIf(Is Alive(Event Player) == True);
\t\t\tCall Subroutine(EfekPulihkan);
\t\t\tEvent Player.FisikaHantuTerbangDiterapkan = False;
\t\t\tCall Subroutine(TerapkanFisikaHantuTerbang);
\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Resurrected at the nearest safe walkable position.") : Event Player.IndeksBahasa == 1 ? Custom String("Bangkit kembali di posisi aman terdekat.") : Custom String("ฟื้นที่ตำแหน่งเดินได้ที่ปลอดภัยใกล้ที่สุดแล้ว"));
\t\tEnd;'''
    text = replace_rule_actions(text, keyword, "12f - Bangkit Lompat: Bangkit di posisi aman yang bisa dilalui", actions)
    path.write_text(text, encoding="utf-8")


patch_source(ROOT / "workshop/ruang_irama.it-IT.workshop", "Globale", "regola")
patch_source(ROOT / "tests/fixtures/semantic_reference.txt", "Global", "rule")

# Focused Fly tests.
p = ROOT / "tests/test_ghost_fly.py"
text = p.read_text(encoding="utf-8")
method = '''    def test_fly_forward_input_accelerates_gradually_along_the_full_view(self) -> None:
        for source, global_name in self.sources:
            packed = compact(subroutine(source, "ProsesSiklusPemain"))
            self.assertIn(f"(ZComponentOf(ThrottleOf({global_name}.PemainAktif)))>0.050", packed)
            self.assertIn(
                f"StartAccelerating({global_name}.PemainAktif,FacingDirectionOf({global_name}.PemainAktif),6,20,ToWorld,DirectionRateandMaxSpeed);",
                packed,
            )
            self.assertIn(
                f"Or({global_name}.PemainAktif.EfekNasib!=2,{global_name}.PemainAktif.EfekNasibBerakhir<=TotalTimeElapsed)",
                packed,
            )
            self.assertNotIn(f"FacingDirectionOf({global_name}.PemainAktif)*-1", packed)
'''
text = replace_method(text, "test_fly_forward_input_uses_view_direction_while_other_axes_stay_native", "test_fly_idle_cancels_velocity_with_an_exact_opposite_impulse", method)
insertion = '''    def test_death_rearms_and_jump_resurrect_reapplies_fly_physics(self) -> None:
        for source, _ in self.sources:
            death = rule_with(source, "Player Died", "Event Player.PosisiMati = Position Of(Event Player);")
            self.assertIn("Event Player.FisikaHantuTerbangDiterapkan = False;", death)
            self.assertIn("Stop Accelerating(Event Player);", death)
            resurrect = rule_with(source, "Resurrect(Event Player);", "Button(Jump)")
            self.assertIn("Event Player.PosisiTeleportTujuan = Nearest Walkable Position(Event Player.PosisiMati);", resurrect)
            self.assertNotIn("Spawn Points(Team Of(Event Player))", resurrect)
            self.assertLess(resurrect.index("Call Subroutine(EfekPulihkan);"), resurrect.index("Event Player.FisikaHantuTerbangDiterapkan = False;"))
            self.assertLess(resurrect.index("Event Player.FisikaHantuTerbangDiterapkan = False;"), resurrect.index("Call Subroutine(TerapkanFisikaHantuTerbang);"))

'''
anchor = "    def test_fresh_setup_and_true_cleanup_restore_safe_defaults(self) -> None:\n"
text = replace_exact(text, anchor, insertion + anchor, "ghost death test")
p.write_text(text, encoding="utf-8")

# Runtime resurrect tests.
p = ROOT / "tests/test_runtime_maintenance.py"
text = p.read_text(encoding="utf-8")
text = text.replace('self.assertGreaterEqual(source.count("Call Subroutine(CariPosisiTeleportAman);"), 5)', 'self.assertGreaterEqual(source.count("Call Subroutine(CariPosisiTeleportAman);"), 4)')
method = '''    def test_jump_resurrect_always_uses_nearest_walkable_without_spawn_fallback(self):
        for source, rule_kw in ((self.it, "regola"), (self.en, "rule")):
            resurrect = source.split(f'{rule_kw}("12f - Bangkit Lompat: Bangkit di posisi aman yang bisa dilalui")', 1)[1].split(f'{rule_kw}("12g - Bangkit Lompat', 1)[0]
            self.assertIn("Event Player.PosisiBangkitAman = Vector(0, 0, 0);", resurrect)
            self.assertIn("Event Player.PosisiTeleportTujuan = Nearest Walkable Position(Event Player.PosisiMati);", resurrect)
            self.assertIn("Call Subroutine(CariPosisiTeleportAman);", resurrect)
            self.assertNotIn("Spawn Points(Team Of(Event Player))", resurrect)
            self.assertNotIn("Ray Cast Hit Position(Event Player.PosisiMati + Vector(0, 1, 0)", resurrect)
            self.assertEqual(resurrect.count("Teleport(Event Player, Event Player.PosisiBangkitAman);"), 1)
            self.assertLess(resurrect.index("Teleport(Event Player, Event Player.PosisiBangkitAman);"), resurrect.index("Resurrect(Event Player);"))
            self.assertIn("Event Player.FisikaHantuTerbangDiterapkan = False;", resurrect)
            self.assertIn("Call Subroutine(TerapkanFisikaHantuTerbang);", resurrect)
            self.assertNotIn("Start Forcing Player Position(", source)
'''
text = replace_method(text, "test_jump_resurrect_keeps_safe_death_spot_and_teleports_only_void_rescue", "test_custom_string_uses_at_most_three_substitution_values", method)
p.write_text(text, encoding="utf-8")

# Validator Fly ownership.
p = ROOT / "tools/validate_workshop.py"
text = p.read_text(encoding="utf-8")
old = '''            ("MagnitudeOf(ThrottleOf(Global.PemainAktif))>0.050", "soglia input aktif per koreksi pitch"),
            (
                "If((ZComponentOf(ThrottleOf(Global.PemainAktif)))>0.050);"
                "ApplyImpulse(Global.PemainAktif,FacingDirectionOf(Global.PemainAktif),"
                "(ZComponentOf(ThrottleOf(Global.PemainAktif)))*9,"
                "ToWorld,CancelContraryMotion);End;",
                "koreksi arah 3D Fly untuk input maju tanpa merusak input lain",
            ),'''
new = '''            ("(ZComponentOf(ThrottleOf(Global.PemainAktif)))>0.050", "input maju Fly pada asse Z"),
            (
                "StartAccelerating(Global.PemainAktif,FacingDirectionOf(Global.PemainAktif),"
                "6,20,ToWorld,DirectionRateandMaxSpeed);",
                "accelerazione Fly graduale lungo la visuale",
            ),'''
text = replace_exact(text, old, new, "validator Fly pattern")
old = '''        global_acceleration_calls = list(iter_calls(source, "Start Accelerating"))
        checks.equal(len(global_acceleration_calls), 1, "Start Accelerating globale unico")
        acceleration_calls = list(iter_calls(state_machine.body, "Start Accelerating"))'''
new = '''        global_acceleration_calls = list(iter_calls(source, "Start Accelerating"))
        checks.equal(len(global_acceleration_calls), 2, "Start Accelerating globali Fly+Luck")
        fly_cycle = next((rule for rule in rules if subroutine_target(rule) == "ProsesSiklusPemain"), None)
        fly_acceleration_calls = list(iter_calls(fly_cycle.body, "Start Accelerating")) if fly_cycle else []
        checks.equal(len(fly_acceleration_calls), 1, "accelerazione Fly graduale unica")
        if len(fly_acceleration_calls) == 1:
            checks.equal(
                tuple(argument.strip() for argument in fly_acceleration_calls[0].args),
                ("Global.PemainAktif", "Facing Direction Of(Global.PemainAktif)", "6", "20", "To World", "Direction Rate and Max Speed"),
                "accelerazione Fly graduale: argomenti",
            )
        acceleration_calls = list(iter_calls(state_machine.body, "Start Accelerating"))'''
text = replace_exact(text, old, new, "validator acceleration owner")

start = text.index('        actions = rule_block(resurrect, "actions") or ""\n', text.index('checks.require(resurrect is not None'))
end = text.index('    resurrect_release = next(\n', start)
new_block = '''        actions = rule_block(resurrect, "actions") or ""
        masked = mask_strings(actions)
        ordered = (
            "Event Player.BangkitLompatDipakai = True;",
            "Event Player.PosisiBangkitAman = Vector(0, 0, 0);",
            "Event Player.PosisiTeleportTujuan = Nearest Walkable Position(Event Player.PosisiMati);",
            "Call Subroutine(CariPosisiTeleportAman);",
            "If(Distance Between(Event Player.PosisiBangkitAman, Vector(0, 0, 0)) <= 0.100);",
            "Abort;",
            "Teleport(Event Player, Event Player.PosisiBangkitAman);",
            "Resurrect(Event Player);",
            "If(Is Alive(Event Player) == True);",
            "Call Subroutine(EfekPulihkan);",
            "Event Player.FisikaHantuTerbangDiterapkan = False;",
            "Call Subroutine(TerapkanFisikaHantuTerbang);",
        )
        positions = [masked.find(token) for token in ordered]
        checks.require(
            all(position >= 0 for position in positions) and positions == sorted(positions),
            "Jump Resurrect deve usare sempre Nearest Walkable, teletrasportare, Resurrect e riapplicare Fly",
        )
        checks.require("Spawn Points(Team Of(Event Player))" not in masked,
                       "Jump Resurrect non deve usare fallback Spawn Room")
        checks.require("Ray Cast Hit Position(Event Player.PosisiMati" not in masked,
                       "Jump Resurrect deve usare sempre Nearest Walkable Position")
        checks.require("Random Real(" not in masked,
                       "Jump Resurrect sicuro non deve usare offset casuali")
        teleport_calls = list(iter_calls(actions, "Teleport"))
        resurrect_calls = list(iter_calls(actions, "Resurrect"))
        checks.equal(len(teleport_calls), 1, "Jump Resurrect: numero Teleport verso Nearest Walkable")
        checks.equal(len(resurrect_calls), 1, "Jump Resurrect: deve esistere un solo Resurrect")
        if teleport_calls and resurrect_calls:
            checks.require(teleport_calls[0].start < resurrect_calls[0].start,
                           "Jump Resurrect deve teletrasportare il cadavere prima di Resurrect")
        checks.require("Start Forcing Player Position(" not in masked,
                       "Jump Resurrect non deve usare forcing di posizione")
        checks.require(not wait_calls(resurrect.body) and action_loop_count(resurrect.body) == 0,
                       "Jump Resurrect deve funzionare senza Wait/Loop")
        checks.require("Event Player.BangkitLompatDipakai = False;" not in masked,
                       "Jump Resurrect non deve riarmarsi durante la stessa pressione")
        death_rearm = next((rule for rule in rules if event_type(rule) == "Player Died" and "Event Player.PosisiMati = Position Of(Event Player);" in rule.body), None)
        checks.require(death_rearm is not None, "morte umana per Jump Resurrect assente")
        if death_rearm:
            death_actions = rule_block(death_rearm, "actions") or ""
            checks.require("Event Player.FisikaHantuTerbangDiterapkan = False;" in death_actions,
                           "morte deve riarmare subito la fisica Ghost/Fly")
            checks.require("Stop Accelerating(Event Player);" in death_actions,
                           "morte deve fermare accelerazione Fly residua")

'''
text = text[:start] + new_block + text[end:]
p.write_text(text, encoding="utf-8")

# Validator mutation tests.
p = ROOT / "tests/test_validate_workshop.py"
text = p.read_text(encoding="utf-8")
method = '''    def test_fly_forward_requires_gradual_acceleration_along_full_view_direction(self) -> None:
        cycle = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesSiklusPemain")
        mutated = self.replace_in_rule(
            cycle,
            "Start Accelerating(Global.PemainAktif, Facing Direction Of(Global.PemainAktif), 6, 20, To World, Direction Rate and Max Speed);",
            "",
        )
        self.assert_rejected(mutated, "accelerazione Fly graduale")
'''
text = replace_method(text, "test_fly_pitch_requires_full_view_direction_impulse", "test_fly_backward_input_must_not_be_forced_by_view_impulse", method)
text = text.replace('"Start Accelerating globale unico"', '"Start Accelerating globali Fly+Luck"')
methods = '''    def test_jump_resurrect_always_requires_nearest_walkable_candidate(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        mutated = self.replace_in_rule(resurrect, "Event Player.PosisiTeleportTujuan = Nearest Walkable Position(Event Player.PosisiMati);", "Event Player.PosisiTeleportTujuan = Event Player.PosisiMati;")
        self.assert_rejected(mutated, "sempre Nearest Walkable")

    def test_jump_resurrect_cannot_use_spawn_room_fallback(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        mutated = self.inject_action(resurrect, "Event Player.PosisiTeleportTujuan = Position Of(First Of(Spawn Points(Team Of(Event Player))));")
        self.assert_rejected(mutated, "fallback Spawn Room")

    def test_jump_resurrect_teleports_the_corpse_before_resurrect(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        teleport = "Teleport(Event Player, Event Player.PosisiBangkitAman);"
        revive = "Resurrect(Event Player);"
        changed = resurrect.body.replace(teleport, "__TELEPORT_PLACEHOLDER__;", 1)
        changed = changed.replace(revive, teleport, 1).replace("__TELEPORT_PLACEHOLDER__;", revive, 1)
        mutated = self.source[:resurrect.start] + changed + self.source[resurrect.end:]
        self.assert_rejected(mutated, "teletrasportare il cadavere")

    def test_jump_resurrect_reapplies_fly_after_effect_restore(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        mutated = self.replace_in_rule(resurrect, "Call Subroutine(TerapkanFisikaHantuTerbang);", "")
        self.assert_rejected(mutated, "riapplicare Fly")

    def test_jump_resurrect_confirms_success_in_same_tick(self) -> None:
        resurrect = self.rule(lambda rule: "Resurrect(Event Player)" in rule.body and "Button(Jump)" in rule.body)
        mutated = self.replace_in_rule(resurrect, "If(Is Alive(Event Player) == True);", "If(True);")
        self.assert_rejected(mutated, "riapplicare Fly")

'''
text = replace_method(text, "test_jump_resurrect_detects_void_before_resurrect", "test_jump_resurrect_does_not_need_position_forcing", methods)
p.write_text(text, encoding="utf-8")

# Changelog.
p = ROOT / "CHANGELOG.md"
text = p.read_text(encoding="utf-8")
marker = "Stato: **live-pending**.\n"
if marker in text and "Fly accelera gradualmente" not in text:
    text = text.replace(marker, marker + "\n- Fly accelera gradualmente finché si mantiene avanti, seguendo il mirino: 6 m/s² fino a 20 m/s; Try Your Luck: Acceleration mantiene la priorità. La morte disarma subito il latch fisico e Jump Resurrect riapplica Ghost/Fly nello stesso tick.\n- Jump Resurrect usa sempre una `Nearest Walkable Position` validata dal punto di morte, teletrasporta il cadavere prima del `Resurrect` e non usa più fallback alla Spawn Room.\n")
p.write_text(text, encoding="utf-8")
