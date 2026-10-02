"""Execute actual Multijump expressions; native collision/hero physics need live QA."""
from __future__ import annotations

import operator
import re
import unittest

from tools import validate_workshop as validator
from tests.test_menu_load_regressions import MenuLoadEvaluator
from tests.test_dummy_spawn_retry import SpawnExpression
from tests.test_fly_motion import Vector, ZERO
from tests.test_roster_rejoin_regressions import SOURCES


class MultijumpEvaluator(MenuLoadEvaluator):
    def __init__(self, source):
        super().__init__(source)
        self.impulses = []
        self.rings = []
        self.globals["RGB"] = "global-rgb"

    def add(self, name, **changes):
        defaults = dict(ModeLompatGanda=True, KursorLompatGanda=1, TingkatLompatGanda=1,
                        LompatGandaDipakai=False, LompatDiTanah=False, MenuTerbuka=False, ModeTerbangAktif=False,
                        LampiranTeleportasiAktif=False, BangkitLompatDipakai=False,
                        EfekNasib=0, EfekNasibBerakhir=0, jump=False, grounded=False,
                        position=Vector(2, 10, 3), velocity=ZERO)
        defaults.update(changes)
        return super().add(name, **defaults)

    def resolve(self, name):
        if name in ("Jump", "ToWorld", "IncorporateContraryMotion", "RingExplosion"):
            return name
        return super().resolve(name)

    def call(self, name, args):
        if name == "IsButtonHeld": return self.players[args[0]]["jump"]
        if name == "IsOnGround": return self.players[args[0]]["grounded"]
        if name == "VelocityOf": return self.players[args[0]]["velocity"]
        if name == "PositionOf": return self.players[args[0]]["position"]
        if name == "YComponentOf": return args[0].y
        if name == "Vector": return Vector(*args)
        if name == "AbsoluteValue": return abs(args[0])
        return super().call(name, args)

    def evaluate(self, expression):
        # Reuse the strict source parser with vector arithmetic and ternaries.
        def literal(match):
            key = f"_literal{len(self.literals)}"
            self.literals[key] = match[0][1:-1].replace(r"\n", "\n")
            return key
        expression = expression.replace("Global.PemainAktif.", "Event Player.").replace("Global.PemainAktif", "Event Player")
        if expression not in self.expressions:
            packed = re.sub(r'"(?:\\.|[^"\\])*"', literal, expression)
            self.expressions[expression] = SpawnExpression(re.sub(r"\s+", "", packed)).tree
        operations = {"+": operator.add, "-": operator.sub, "*": operator.mul,
                      "/": operator.truediv, "%": operator.mod, "==": operator.eq,
                      "!=": operator.ne, ">": operator.gt, "<": operator.lt,
                      ">=": operator.ge, "<=": operator.le}
        def visit(node):
            kind = node[0]
            if kind == "literal": return node[1]
            if kind == "name": return self.resolve(node[1])
            if kind == "negate": return -visit(node[1])
            if kind == "conditional": return visit(node[2] if visit(node[1]) else node[3])
            if kind != "call": return operations[kind](visit(node[1]), visit(node[2]))
            name, args = node[1:]
            if name in ("And", "Or"):
                return (all if name == "And" else any)(bool(visit(arg)) for arg in args)
            return self.call(name, [visit(arg) for arg in args])
        return visit(self.expressions[expression])

    def execute(self, actions):
        actions = re.sub(r'(?m)^\s*"(?:\\.|[^"\\])*"\s*$', "", actions)
        actions = actions.replace("Global.PemainAktif.", "Event Player.").replace("Global.PemainAktif", "Event Player")
        frames, active = [], True
        for statement in actions.split(";"):
            statement = statement.strip()
            if not statement: continue
            if statement.startswith("If("):
                branch = active and bool(self.evaluate(statement[3:-1]))
                frames.append((active, branch))
                active = branch
            elif statement == "Else":
                parent, taken = frames[-1]
                active = parent and not taken
                frames[-1] = (parent, True)
            elif statement.startswith("Else If("):
                parent, taken = frames[-1]
                active = parent and not taken and bool(self.evaluate(statement[8:-1]))
                frames[-1] = (parent, taken or active)
            elif statement == "End":
                active = frames.pop()[0]
            elif active:
                assignment = re.fullmatch(r"(Event Player\..+?)\s+(%?=)\s+(.+)", statement, re.S)
                if assignment:
                    value = self.evaluate(assignment[3])
                    if assignment[2] == "%=": value = self.evaluate(assignment[1]) % value
                    self.assign(assignment[1], value)
                elif statement.startswith("Apply Impulse("):
                    call = next(validator.iter_calls(statement, "Apply Impulse"))
                    player, direction, speed, frame, motion = [self.evaluate(arg) for arg in call.args]
                    self.impulses.append((player, direction, speed, frame, motion))
                    self.players[player]["velocity"] += direction * speed
                elif statement.startswith("Play Effect("):
                    call = next(validator.iter_calls(statement, "Play Effect"))
                    self.rings.append(tuple(self.evaluate(arg) for arg in call.args))
                else:
                    raise AssertionError(f"unsupported jump statement {statement}")
        if frames: raise AssertionError("unclosed jump branches")

    def tick(self, player):
        # Execute the state gate from the actual scheduler, not a hand-written gate.
        self.event_player = player
        scheduler = self.rule("04g")
        call = next(call for call in validator.iter_calls(scheduler.body, "Call Subroutine")
                    if call.args == ("ProsesLompatGanda",))
        branch = validator.conditional_branches_containing(scheduler.body, call.start)[0]
        if self.evaluate(branch.splitlines()[0].strip()[3:-2]):
            self.run("89h", player)


class MultijumpTests(unittest.TestCase):
    def models(self):
        for path, _, _ in SOURCES:
            yield path.name, MultijumpEvaluator(path.read_text(encoding="utf-8"))

    def test_off_executes_no_impulse_or_ring_even_while_jump_is_held(self):
        for name, model in self.models():
            with self.subTest(source=name):
                state = model.add("one", ModeLompatGanda=False, jump=True)
                for _ in range(200): model.tick("one")
                self.assertEqual(model.impulses, [])
                self.assertEqual(model.rings, [])
                self.assertFalse(state["LompatGandaDipakai"])

    def test_each_release_and_press_jumps_once_and_preserves_selected_boost(self):
        for name, model in self.models():
            for level in range(1, 20):
                with self.subTest(source=name, percent=100 + (level - 1) * 50):
                    state = model.add("one", TingkatLompatGanda=level, velocity=Vector(3, -30, -4))
                    count = len(model.impulses)
                    for _ in range(20):
                        state["jump"] = True
                        for _ in range(20): model.tick("one")
                        self.assertEqual(state["velocity"], Vector(3, 6 + 3 * (level - 1), -4))
                        self.assertEqual(state["TingkatLompatGanda"], level)
                        state["jump"] = False
                        model.tick("one")
                        state["velocity"] = Vector(3, -30, -4)
                    self.assertEqual(len(model.impulses) - count, 20)

    def test_fast_upward_motion_is_corrected_without_stacking_or_horizontal_braking(self):
        for name, model in self.models():
            with self.subTest(source=name):
                state = model.add("one", jump=True, TingkatLompatGanda=2, velocity=Vector(4, 80, -6))
                model.tick("one")
                self.assertEqual(state["velocity"], Vector(4, 9, -6))
                self.assertEqual(model.impulses[0][1], Vector(0, -1, 0))

    def test_ground_jump_keeps_native_velocity_but_plays_one_temporary_global_rgb_ring(self):
        for name, model in self.models():
            with self.subTest(source=name):
                state = model.add("one", jump=True, grounded=True, velocity=Vector(2, 7, 4))
                for _ in range(40): model.tick("one")
                self.assertEqual(model.impulses, [])
                self.assertEqual(state["velocity"], Vector(2, 7, 4))
                self.assertEqual(len(model.rings), 1)
                audience, kind, color, position, radius = model.rings[0]
                self.assertEqual((audience, kind, color, position, radius),
                                 (["one"], "RingExplosion", "global-rgb", Vector(2, 10.05, 3), 1.5))

    def test_first_takeoff_does_not_gain_an_impulse_when_native_jump_has_already_left_ground(self):
        for name, model in self.models():
            with self.subTest(source=name):
                state = model.add("one", LompatDiTanah=True, grounded=False, jump=True,
                                  velocity=Vector(3, 7, -4), TingkatLompatGanda=19)
                model.tick("one")
                self.assertEqual(model.impulses, [])
                self.assertEqual(len(model.rings), 1)
                self.assertEqual(state["velocity"], Vector(3, 7, -4))
                self.assertFalse(state["LompatDiTanah"])
                state["jump"] = False; model.tick("one")
                state["jump"] = True; model.tick("one")
                self.assertEqual(state["velocity"], Vector(3, 60, -4))
                self.assertEqual(len(model.impulses), 1)

    def test_blocked_press_is_consumed_until_release_after_recovery(self):
        blocked = ({"alive": False}, {"spawned": False}, {"Manusia": False},
                   {"MenuTerbuka": True}, {"ModeTerbangAktif": True},
                   {"LampiranTeleportasiAktif": True}, {"BangkitLompatDipakai": True},
                   {"EfekNasib": 2, "EfekNasibBerakhir": 20})
        for name, model in self.models():
            for changes in blocked:
                with self.subTest(source=name, changes=changes):
                    state = model.add("one", jump=True, **changes)
                    model.impulses.clear(); model.rings.clear()
                    model.tick("one")
                    self.assertTrue(state["LompatGandaDipakai"])
                    self.assertEqual((model.impulses, model.rings), ([], []))
                    state.update(alive=True, spawned=True, Manusia=True, MenuTerbuka=False,
                                 ModeTerbangAktif=False, LampiranTeleportasiAktif=False,
                                 BangkitLompatDipakai=False, EfekNasib=0)
                    model.tick("one")
                    self.assertEqual((model.impulses, model.rings), ([], []))
                    state["jump"] = False; model.tick("one")
                    state["jump"] = True; model.tick("one")
                    self.assertEqual(len(model.impulses), 1)

    def test_enabling_while_jump_held_and_off_preserve_level_without_spontaneous_jump(self):
        for name, model in self.models():
            with self.subTest(source=name):
                state = model.add("one", ModeLompatGanda=False, KursorLompatGanda=19, jump=True)
                model.run("99p", "one")
                self.assertTrue(state["ModeLompatGanda"])
                self.assertEqual(state["TingkatLompatGanda"], 19)
                model.tick("one")
                self.assertEqual(model.impulses, [])
                state["KursorLompatGanda"] = 0
                model.run("99p", "one")
                self.assertFalse(state["ModeLompatGanda"])
                self.assertEqual(state["TingkatLompatGanda"], 19)

    def test_twelve_players_have_independent_boosts_and_latches(self):
        for name, model in self.models():
            with self.subTest(source=name):
                for index in range(12): model.add(str(index), TingkatLompatGanda=index % 10 + 1, jump=index % 2 == 0)
                for _ in range(20):
                    for index in range(12): model.tick(str(index))
                self.assertEqual(len(model.impulses), 6)
                for index in range(12):
                    state = model.players[str(index)]
                    self.assertEqual(state["velocity"].y, 6 + 3 * (index % 10) if index % 2 == 0 else 0)

    def test_twenty_menu_choices_wrap_both_ways_and_preview_does_not_apply_them(self):
        for name, model in self.models():
            with self.subTest(source=name):
                state = model.add("one", HalamanMenu=14, KursorLompatGanda=0,
                                  TingkatLompatGanda=7, PerintahMenu=3)
                navigation = next(line for line in model.rule("06").body.splitlines()
                                  if "Event Player.KursorLompatGanda =" in line)
                model.event_player = "one"
                for index in range(1, 41):
                    model.execute(navigation)
                    self.assertEqual(state["KursorLompatGanda"], index % 20)
                    self.assertEqual(state["TingkatLompatGanda"], 7)
                state["PerintahMenu"] = 4
                for index in range(1, 41):
                    model.execute(navigation)
                    self.assertEqual(state["KursorLompatGanda"], -index % 20)
                for level in range(1, 20):
                    state["KursorLompatGanda"] = level
                    model.run("99p", "one")
                    self.assertEqual(state["TingkatLompatGanda"], level)
                    self.assertTrue(state["ModeLompatGanda"])

    def test_menu_shows_fifty_percent_steps_and_fixed_applied_value_in_all_languages(self):
        for name, model in self.models():
            for language in range(3):
                with self.subTest(source=name, language=language):
                    state = model.add("one", IndeksBahasa=language, TingkatLompatGanda=6,
                                      KursorLompatGanda=19)
                    model.event_player = "one"
                    renderer = validator.rule_by_subroutine(model.rules, "GambarLompatGanda")
                    hud = next(validator.iter_calls(renderer.body, "Create HUD Text"))
                    body = model.evaluate(hud.args[3])
                    self.assertIn("350%", body)
                    self.assertIn("1000%", body)
                    self.assertIn("20/20", body)
                    state["KursorLompatGanda"] = 2
                    self.assertIn("150%", model.evaluate(hud.args[3]))
                    self.assertEqual(state["TingkatLompatGanda"], 6)

    def test_setup_and_team_quiet_reset_owned_state_and_death_does_not_erase_preferences(self):
        fields = {"ModeLompatGanda", "KursorLompatGanda", "TingkatLompatGanda",
                  "LompatGandaDipakai", "LompatDiTanah"}
        for name, model in self.models():
            with self.subTest(source=name):
                for owner in ("SiapkanPemain", "TenangkanPemain"):
                    state = model.add("one", TingkatLompatGanda=19, KursorLompatGanda=19,
                                      ModeLompatGanda=True, LompatGandaDipakai=True)
                    model.event_player = "one"
                    rule = validator.rule_by_subroutine(model.rules, owner)
                    resets = "\n".join(line for line in rule.body.splitlines()
                                       if any("Event Player." + field + " =" in line for field in fields))
                    model.execute(resets)
                    self.assertEqual(tuple(state[field] for field in
                                           ("ModeLompatGanda", "KursorLompatGanda", "TingkatLompatGanda",
                                            "LompatGandaDipakai", "LompatDiTanah")), (False, 0, 1, False, True))
                death = model.rule("12e")
                self.assertFalse(any("Event Player." + field + " =" in death.body for field in fields))

    def test_validator_rejects_held_repeat_additive_velocity_persistent_effect_and_unbounded_choices(self):
        mutations = (
            ("LompatGandaDipakai == False", "LompatGandaDipakai == True", "guardia input"),
            ("6 + 3 * (Global.PemainAktif.TingkatLompatGanda - 1) - Y Component Of(Velocity Of(Global.PemainAktif))", "6 + 3 * (Global.PemainAktif.TingkatLompatGanda - 1)", "senza accumulo"),
            ("Play Effect(All Players(All Teams), Ring Explosion, Global.RGB", "Create Effect(All Players(All Teams), Ring, Global.RGB", "ring temporaneo"),
            ("KursorLompatGanda %= 20", "KursorLompatGanda %= 100", "apply deve"),
            ("Global.PemainAktif.LompatDiTanah == False", "Global.PemainAktif.LompatDiTanah == True", "guardia input"),
            ("Global.PemainAktif.LompatGandaDipakai = True;",
             "Global.PemainAktif.LompatGandaDipakai = True;\nGlobal.PemainAktif.TingkatLompatGanda = Global.PemainAktif.TingkatLompatGanda + 1;",
             "spinta fissa"),
        )
        # English fixture is selected explicitly for portable action spellings.
        english = next(path.read_text(encoding="utf-8") for path, _, _ in SOURCES if path.suffix == ".txt")
        for old, new, expected in mutations:
            with self.subTest(token=old):
                self.assertIn(old, english)
                mutated = english.replace(old, new)
                rules = validator.extract_rules(mutated)
                _, player_fields, subfields, _ = validator.declaration_entries(mutated)
                checks = validator.Checks()
                validator.validate_multijump(checks, mutated, rules, player_fields, {entry.name for entry in subfields})
                self.assertTrue(any(expected in error for error in checks.errors), checks.errors)


if __name__ == "__main__":
    unittest.main()
