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
        defaults = dict(MultijumpEnabled=True, MultijumpCursor=1, MultijumpLevel=1,
                        MultijumpConsumed=False, JumpWasGrounded=False, MenuOpen=False, FlyModeActive=False,
                        NextMultijumpTime=0,
                        TravelAttachmentActive=False, JumpReviveConsumed=False,
                        LuckEffect=0, LuckEffectEndTime=0, jump=False, grounded=False,
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
        expression = expression.replace("Global.ActivePlayer.", "Event Player.").replace("Global.ActivePlayer", "Event Player")
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
        actions = actions.replace("Global.ActivePlayer.", "Event Player.").replace("Global.ActivePlayer", "Event Player")
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
                    if call.args == ("ProcessMultijump",))
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
                state = model.add("one", MultijumpEnabled=False, jump=True)
                for step in range(200):
                    model.now = step / 20
                    model.tick("one")
                self.assertEqual(model.impulses, [])
                self.assertEqual(model.rings, [])
                self.assertFalse(state["MultijumpConsumed"])

    def test_fresh_presses_before_repeat_deadline_preserve_selected_boost(self):
        for name, model in self.models():
            for level in range(1, 11):
                with self.subTest(source=name, percent=100 * level):
                    state = model.add("one", MultijumpLevel=level, velocity=Vector(3, -30, -4))
                    count = len(model.impulses)
                    for cycle in range(20):
                        state["jump"] = True
                        for step in range(20):
                            model.now = cycle * 0.25 + step * 0.01
                            model.tick("one")
                        self.assertEqual(state["velocity"], Vector(3, 6 * level, -4))
                        self.assertEqual(state["MultijumpLevel"], level)
                        state["jump"] = False
                        model.now = cycle * 0.25 + 0.20
                        model.tick("one")
                        state["velocity"] = Vector(3, -30, -4)
                    self.assertEqual(len(model.impulses) - count, 20)

    def test_fast_upward_motion_is_corrected_without_stacking_or_horizontal_braking(self):
        for name, model in self.models():
            with self.subTest(source=name):
                state = model.add("one", jump=True, MultijumpLevel=2, velocity=Vector(4, 80, -6))
                model.tick("one")
                self.assertEqual(state["velocity"], Vector(4, 12, -6))
                self.assertEqual(model.impulses[0][1], Vector(0, -1, 0))

    def test_ground_jump_keeps_native_velocity_but_plays_one_temporary_global_rgb_ring(self):
        for name, model in self.models():
            with self.subTest(source=name):
                state = model.add("one", jump=True, grounded=True, velocity=Vector(2, 7, 4))
                for step in range(40):
                    model.now = step / 20
                    model.tick("one")
                self.assertEqual(model.impulses, [])
                self.assertEqual(state["velocity"], Vector(2, 7, 4))
                self.assertEqual(len(model.rings), 1)
                audience, kind, color, position, radius = model.rings[0]
                self.assertEqual((audience, kind, color, position, radius),
                                 (["one"], "RingExplosion", "global-rgb", Vector(2, 10.05, 3), 1.5))

    def test_first_takeoff_does_not_gain_an_impulse_when_native_jump_has_already_left_ground(self):
        for name, model in self.models():
            with self.subTest(source=name):
                state = model.add("one", JumpWasGrounded=True, grounded=False, jump=True,
                                  velocity=Vector(3, 7, -4), MultijumpLevel=10)
                model.tick("one")
                self.assertEqual(model.impulses, [])
                self.assertEqual(len(model.rings), 1)
                self.assertEqual(state["velocity"], Vector(3, 7, -4))
                self.assertFalse(state["JumpWasGrounded"])
                state["jump"] = False; model.tick("one")
                state["jump"] = True; model.tick("one")
                self.assertEqual(state["velocity"], Vector(3, 60, -4))
                self.assertEqual(len(model.impulses), 1)

    def test_blocked_held_press_waits_until_cadence_then_resumes_after_recovery(self):
        blocked = ({"alive": False}, {"spawned": False}, {"IsHuman": False},
                   {"FlyModeActive": True},
                   {"TravelAttachmentActive": True},
                   {"LuckEffect": 2, "LuckEffectEndTime": 20})
        for name, model in self.models():
            for changes in blocked:
                with self.subTest(source=name, changes=changes):
                    state = model.add("one", jump=True, **changes)
                    model.impulses.clear(); model.rings.clear()
                    model.now = 0
                    model.tick("one")
                    self.assertTrue(state["MultijumpConsumed"])
                    self.assertAlmostEqual(state["NextMultijumpTime"], 0.3)
                    self.assertEqual((model.impulses, model.rings), ([], []))
                    model.now = 0.3
                    model.tick("one")
                    self.assertEqual((model.impulses, model.rings), ([], []))
                    self.assertAlmostEqual(state["NextMultijumpTime"], 0.6)
                    state.update(alive=True, spawned=True, IsHuman=True, MenuOpen=False,
                                 FlyModeActive=False, TravelAttachmentActive=False,
                                 JumpReviveConsumed=False, LuckEffect=0)
                    model.now = 0.59
                    model.tick("one")
                    self.assertEqual((model.impulses, model.rings), ([], []))
                    model.now = 0.6
                    model.tick("one")
                    self.assertEqual(len(model.impulses), 1)
                    self.assertAlmostEqual(state["NextMultijumpTime"], 0.9)

    def test_resurrect_latch_blocks_held_repeats_until_native_release_rule_clears_it(self):
        for name, model in self.models():
            with self.subTest(source=name):
                state = model.add("one", jump=True, JumpReviveConsumed=True)
                for now in (0, 0.3, 0.6):
                    model.now = now
                    model.tick("one")
                    self.assertFalse(model.conditions("12g", "one"))
                self.assertEqual((model.impulses, model.rings), ([], []))
                state["jump"] = False
                model.now = 0.65
                self.assertTrue(model.conditions("12g", "one"))
                model.run("12g", "one")
                model.tick("one")
                self.assertFalse(state["JumpReviveConsumed"])
                self.assertEqual(state["NextMultijumpTime"], 0)
                state["jump"] = True
                model.now = 0.66
                model.tick("one")
                self.assertEqual(len(model.impulses), 1)

    def test_fresh_press_is_immediate_even_with_a_future_repeat_deadline(self):
        for name, model in self.models():
            with self.subTest(source=name):
                state = model.add("one", jump=True, MultijumpConsumed=False,
                                  NextMultijumpTime=50)
                model.now = 1
                model.tick("one")
                self.assertEqual(len(model.impulses), 1)
                self.assertAlmostEqual(state["NextMultijumpTime"], 1.3)

    def test_enabling_while_jump_held_delays_repeat_and_off_preserves_selected_level(self):
        for name, model in self.models():
            with self.subTest(source=name):
                state = model.add("one", MultijumpEnabled=False, MultijumpCursor=10, jump=True)
                model.run("99p", "one")
                self.assertTrue(state["MultijumpEnabled"])
                self.assertEqual(state["MultijumpLevel"], 10)
                model.tick("one")
                self.assertEqual(model.impulses, [])
                self.assertAlmostEqual(state["NextMultijumpTime"], 0.3)
                model.now = 0.29
                model.tick("one")
                self.assertEqual(model.impulses, [])
                model.now = 0.3
                model.tick("one")
                self.assertEqual(len(model.impulses), 1)
                state["MultijumpCursor"] = 0
                model.run("99p", "one")
                self.assertFalse(state["MultijumpEnabled"])
                self.assertEqual(state["MultijumpLevel"], 10)

    def test_open_menu_repeats_held_air_jump_on_cadence_while_navigating(self):
        for name, model in self.models():
            with self.subTest(source=name):
                state = model.add("one", MenuOpen=True, MenuPage=14,
                                  MultijumpLevel=3, MultijumpCursor=3,
                                  jump=True, velocity=Vector(2, -15, -4), MenuCommand=3)
                model.tick("one")
                self.assertEqual(state["velocity"], Vector(2, 18, -4))
                self.assertEqual((len(model.impulses), len(model.rings)), (1, 1))
                navigation = next(line for line in model.rule("06").body.splitlines()
                                  if "Event Player.MultijumpCursor =" in line)
                model.execute(navigation)
                self.assertEqual(state["MultijumpCursor"], 4)
                for now, expected in ((0.29, 1), (0.3, 2), (0.59, 2), (0.6, 3)):
                    model.now = now
                    model.tick("one")
                    self.assertEqual((len(model.impulses), len(model.rings)), (expected, expected))
                self.assertEqual(state["MultijumpLevel"], 3)
                self.assertEqual(state["velocity"], Vector(2, 18, -4))
                state["jump"] = False
                model.now = 0.61
                model.tick("one")
                state["jump"] = True
                model.now = 0.62
                model.tick("one")
                self.assertEqual((len(model.impulses), len(model.rings)), (4, 4))
                self.assertTrue(state["MenuOpen"])

    def test_open_menu_preview_and_apply_keep_strength_and_repeat_deadlines_per_player(self):
        for name, model in self.models():
            with self.subTest(source=name):
                first = model.add("first", MenuOpen=True, MenuPage=14,
                                  MultijumpLevel=2, MultijumpCursor=2,
                                  MenuCommand=4, jump=True)
                second = model.add("second", MenuOpen=True, MenuPage=14,
                                   MultijumpLevel=6, MultijumpCursor=6, jump=True)
                navigation = next(line for line in model.rule("06").body.splitlines()
                                  if "Event Player.MultijumpCursor =" in line)
                model.event_player = "first"
                model.execute(navigation)
                model.execute(navigation)
                self.assertEqual(first["MultijumpCursor"], 0)  # Preview OFF only.
                self.assertTrue(first["MultijumpEnabled"])
                self.assertEqual(first["MultijumpLevel"], 2)
                model.tick("first")
                model.tick("second")
                self.assertEqual((first["velocity"].y, second["velocity"].y), (12, 36))
                self.assertEqual(len(model.impulses), 2)

                first["MultijumpCursor"] = 10
                model.now = 0.1
                model.run("99p", "first")  # Apply 1000% while Jump remains held.
                self.assertEqual(first["MultijumpLevel"], 10)
                self.assertEqual((second["MultijumpLevel"], second["MultijumpCursor"]), (6, 6))
                self.assertAlmostEqual(first["NextMultijumpTime"], 0.4)
                self.assertAlmostEqual(second["NextMultijumpTime"], 0.3)
                model.now = 0.29
                model.tick("first")
                model.tick("second")
                self.assertEqual(len(model.impulses), 2)
                self.assertEqual((first["velocity"].y, second["velocity"].y), (12, 36))
                model.now = 0.3
                model.tick("first")
                model.tick("second")
                self.assertEqual([impulse[0] for impulse in model.impulses], ["first", "second", "second"])
                self.assertEqual((first["velocity"].y, second["velocity"].y), (12, 36))
                model.now = 0.4
                model.tick("first")
                model.tick("second")
                self.assertEqual((first["velocity"].y, second["velocity"].y), (60, 36))
                self.assertEqual([impulse[0] for impulse in model.impulses], ["first", "second", "second", "first"])

    def test_twelve_players_have_independent_boosts_and_latches(self):
        for name, model in self.models():
            with self.subTest(source=name):
                for index in range(12):
                    model.add(str(index), MultijumpLevel=index % 10 + 1,
                              jump=index % 2 == 0, MenuOpen=index % 3 == 0)
                for _ in range(20):
                    for index in range(12): model.tick(str(index))
                self.assertEqual(len(model.impulses), 6)
                for index in range(12):
                    state = model.players[str(index)]
                    self.assertEqual(state["velocity"].y, 6 * (index % 10 + 1) if index % 2 == 0 else 0)

    def test_twelve_simultaneous_held_jumps_share_cadence_without_sharing_state(self):
        for name, model in self.models():
            with self.subTest(source=name):
                for index in range(12):
                    model.add(str(index), MultijumpLevel=index % 10 + 1,
                              jump=True, MenuOpen=index % 2 == 0)
                for now, expected in ((0, 12), (0.29, 12), (0.3, 24), (0.59, 24), (0.6, 36)):
                    model.now = now
                    for index in range(12):
                        model.tick(str(index))
                    self.assertEqual((len(model.impulses), len(model.rings)), (expected, expected))
                    for index in range(12):
                        state = model.players[str(index)]
                        self.assertEqual(state["velocity"].y, 6 * (index % 10 + 1))
                        self.assertEqual(state["MultijumpLevel"], index % 10 + 1)
                self.assertEqual([sum(impulse[0] == str(index) for impulse in model.impulses)
                                  for index in range(12)], [3] * 12)

    def test_eleven_menu_choices_wrap_both_ways_and_preview_does_not_apply_them(self):
        for name, model in self.models():
            with self.subTest(source=name):
                state = model.add("one", MenuPage=14, MultijumpCursor=0,
                                  MultijumpLevel=7, MenuCommand=3)
                navigation = next(line for line in model.rule("06").body.splitlines()
                                  if "Event Player.MultijumpCursor =" in line)
                model.event_player = "one"
                for index in range(1, 23):
                    model.execute(navigation)
                    self.assertEqual(state["MultijumpCursor"], index % 11)
                    self.assertEqual(state["MultijumpLevel"], 7)
                state["MenuCommand"] = 4
                for index in range(1, 23):
                    model.execute(navigation)
                    self.assertEqual(state["MultijumpCursor"], -index % 11)
                for level in range(1, 11):
                    state["MultijumpCursor"] = level
                    model.run("99p", "one")
                    self.assertEqual(state["MultijumpLevel"], level)
                    self.assertTrue(state["MultijumpEnabled"])

    def test_menu_shows_hundred_percent_steps_and_fixed_applied_value_in_english(self):
        for name, model in self.models():
            with self.subTest(source=name):
                state = model.add("one", MultijumpLevel=6, MultijumpCursor=10)
                model.event_player = "one"
                renderer = validator.rule_by_subroutine(model.rules, "DrawMultijumpMenu")
                hud = next(validator.iter_calls(renderer.body, "Create HUD Text"))
                body = model.evaluate(hud.args[3])
                self.assertIn("600%", body)
                self.assertIn("1000%", body)
                self.assertIn("11/11", body)
                state["MultijumpCursor"] = 2
                self.assertIn("200%", model.evaluate(hud.args[3]))
                self.assertEqual(state["MultijumpLevel"], 6)

    def test_setup_and_team_quiet_reset_owned_state_and_death_does_not_erase_preferences(self):
        fields = {"MultijumpEnabled", "MultijumpCursor", "MultijumpLevel",
                  "MultijumpConsumed", "JumpWasGrounded", "NextMultijumpTime"}
        for name, model in self.models():
            with self.subTest(source=name):
                for owner in ("PreparePlayer", "QuiescePlayer"):
                    state = model.add("one", MultijumpLevel=10, MultijumpCursor=10,
                                      MultijumpEnabled=True, MultijumpConsumed=True,
                                      NextMultijumpTime=500)
                    model.event_player = "one"
                    rule = validator.rule_by_subroutine(model.rules, owner)
                    resets = "\n".join(line for line in rule.body.splitlines()
                                       if any("Event Player." + field + " =" in line for field in fields))
                    model.execute(resets)
                    self.assertEqual(tuple(state[field] for field in
                                           ("MultijumpEnabled", "MultijumpCursor", "MultijumpLevel",
                                            "MultijumpConsumed", "JumpWasGrounded")), (False, 0, 1, False, True))
                    self.assertEqual(state["NextMultijumpTime"], 0)
                death = model.rule("12e")
                self.assertFalse(any("Event Player." + field + " =" in death.body for field in fields))

    def test_validator_rejects_unbounded_repeat_additive_velocity_persistent_effect_and_unbounded_choices(self):
        mutations = (
            ("MultijumpConsumed == False", "MultijumpConsumed == True", "guardia input"),
            ("Global.ActivePlayer.NextMultijumpTime = Total Time Elapsed + 0.300;",
             "Global.ActivePlayer.NextMultijumpTime = Total Time Elapsed + 0.050;",
             "guardia input"),
            ("6 * Global.ActivePlayer.MultijumpLevel - Y Component Of(Velocity Of(Global.ActivePlayer))", "6 * Global.ActivePlayer.MultijumpLevel", "senza accumulo"),
            ("Play Effect(All Players(All Teams), Ring Explosion, Global.RGB", "Create Effect(All Players(All Teams), Ring, Global.RGB", "ring temporaneo"),
            ("MultijumpCursor %= 11", "MultijumpCursor %= 100", "apply deve"),
            ("Global.ActivePlayer.JumpWasGrounded == False", "Global.ActivePlayer.JumpWasGrounded == True", "guardia input"),
            ("Global.ActivePlayer.MultijumpConsumed = True;",
             "Global.ActivePlayer.MultijumpConsumed = True;\nGlobal.ActivePlayer.MultijumpLevel = Global.ActivePlayer.MultijumpLevel + 1;",
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
