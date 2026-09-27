"""Execute real dummy-spawn rules against controlled engine geometry responses.

The source chooses anchors, candidates, retries and final teleports. Only native
queries (objective positions, navigation mesh and ray casts) are supplied by this
harness; real map collision and Workshop event delivery still need client QA.
"""

from __future__ import annotations

import math
import operator
import re
import unittest
from pathlib import Path

from tools import check_clipboard_import as clipboard
from tools import validate_workshop as validator
from tests.test_fly_motion import Expression, Vector, ZERO


ROOT = Path(__file__).resolve().parents[1]


class SpawnExpression(Expression):
    TOKEN = re.compile(Expression.TOKEN.pattern + r"|[%?:]")
    PRECEDENCE = {**Expression.PRECEDENCE, "%": 3}

    def parse(self, minimum=0):
        node = super().parse(minimum)
        if minimum == 0 and self.peek() == "?":
            self.take("?")
            yes = self.parse()
            self.take(":")
            node = ("conditional", node, yes, self.parse())
        return node


class SpawnEvaluator:
    def __init__(self, source):
        if re.search(r"(?m)^regola\(", source):
            parts = re.split(r'("(?:\\.|[^"\\])*")', source)
            for index in range(0, len(parts), 2):
                for original, translated in clipboard.ITALIAN_TO_ENGLISH_TOKENS:
                    parts[index] = clipboard._replace_token(parts[index], original, translated)
            source = "".join(parts)
        self.rules = validator.extract_rules(source)
        self.players = {}
        self.selected = "one"
        self.now = 100.0
        self.mode = "Skirmish"
        self.objective_index = 0
        self.objectives = {0: Vector(100, 20, 100), 1: Vector(140, 20, 100)}
        self.ground = 20
        self.spawn = {1: Vector(100, 20, 40), 2: Vector(100, 20, 160)}
        self.candidates = []
        self.teleports = []
        self.reject_attempts = 0
        self.inside_helper = False
        self.expressions = {}
        self.add_player("one")

    def add_player(self, identity, **changes):
        state = dict(dummy=True, BotOtomatis=False, spawned=True, alive=True,
                     spawn_room=True, team=1, position=self.spawn[1], hero="Ana",
                     PahlawanTerakhir="Ana", KunciBotAktif=True,
                     WaktuTeleportasiBotBuatan=0, KursorTeleportasiBotBuatan=0)
        state.update(changes)
        self.players[identity] = state
        return state

    def rule(self, prefix):
        return next(rule for rule in self.rules if rule.name.startswith(prefix + " -"))

    def resolve(self, name):
        if name.startswith("EventPlayer."):
            return self.players[self.selected].get(name.split(".", 1)[1], 0)
        values = {"EventPlayer": self.selected, "True": True, "False": False, "Global.Siap": True,
                  "Null": None, "TotalTimeElapsed": self.now,
                  "CurrentGameMode": self.mode, "ObjectiveIndex": self.objective_index,
                  "EmptyArray": [], "Skirmish": "Skirmish"}
        if name not in values:
            raise AssertionError(f"unsupported spawn value: {name}")
        return values[name]

    def evaluate(self, text):
        packed = re.sub(r"\s+", "", text)
        if packed not in self.expressions:
            self.expressions[packed] = SpawnExpression(packed).tree
        operations = {"+": operator.add, "-": operator.sub, "*": operator.mul,
                      "/": operator.truediv, "%": operator.mod, "==": operator.eq,
                      "!=": operator.ne, "<": operator.lt, ">": operator.gt,
                      "<=": operator.le, ">=": operator.ge}

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

        return visit(self.expressions[packed])

    def position(self, value):
        if value is None: return ZERO
        return self.players[value]["position"] if isinstance(value, str) else value

    def call(self, name, args):
        if name == "Vector": return Vector(*args)
        if name == "GameMode": return args[0]
        if name == "ObjectivePosition": return self.objectives.get(int(args[0]), ZERO)
        if name == "SpawnPoints": return [self.spawn[args[0]]]
        if name == "PositionOf": return self.position(args[0])
        if name == "FirstOf": return args[0][0]
        if name == "CountOf": return len(args[0])
        if name == "DistanceBetween": return (self.position(args[1]) - self.position(args[0])).magnitude()
        if name == "DirectionTowards": return (self.position(args[1]) - self.position(args[0])).normalized()
        if name == "HorizontalAngleFromDirection": return math.degrees(math.atan2(args[0].x, args[0].z))
        if name == "DirectionFromAngles":
            yaw, pitch = map(math.radians, args)
            return Vector(math.sin(yaw) * math.cos(pitch), -math.sin(pitch), math.cos(yaw) * math.cos(pitch))
        if name == "NearestWalkablePosition":
            point = args[0]
            if not self.inside_helper:
                self.candidates.append((self.selected, self.now, point))
            if self.inside_helper and len(self.candidates) <= self.reject_attempts:
                return ZERO
            return Vector(point.x, self.ground, point.z)
        if name == "RayCastHitPosition":
            start, end = args[:2]
            return Vector(end.x, self.ground, end.z) if end.y < start.y else end
        player_queries = {"IsDummyBot": "dummy", "HasSpawned": "spawned", "IsAlive": "alive",
                          "IsInSpawnRoom": "spawn_room", "TeamOf": "team", "HeroOf": "hero"}
        if name in player_queries: return self.players[args[0]][player_queries[name]]
        if name == "Teleport":
            self.teleports.append((args[0], self.now, args[1]))
            self.players[args[0]]["position"] = args[1]
            return None
        if name in ("StopFacing", "StopThrottleInDirection", "EnableMovementCollisionWithPlayers",
                    "DisableMovementCollisionWithEnvironment", "SetRespawnMaxTime"):
            return None
        raise AssertionError(f"unsupported spawn primitive: {name}")

    def execute(self, actions):
        frames = []
        active = True
        for token in validator.mask_strings(actions).split(";"):
            token = token.strip()
            if not token:
                continue
            if token.startswith("If("):
                condition = active and bool(self.evaluate(token[3:-1]))
                frames.append({"parent": active, "taken": condition})
                active = condition
            elif token.startswith("Else If("):
                frame = frames[-1]
                active = frame["parent"] and not frame["taken"] and bool(self.evaluate(token[8:-1]))
                frame["taken"] = frame["taken"] or active
            elif token == "Else":
                frame = frames[-1]
                active = frame["parent"] and not frame["taken"]
                frame["taken"] = True
            elif token == "End":
                active = frames.pop()["parent"]
            elif active:
                if token == "Abort" or (token.startswith("Abort If(") and self.evaluate(token[9:-1])):
                    return
                if token.startswith("Abort If("):
                    continue
                assignment = re.fullmatch(r"Event Player\.(\w+) (\+?=) (?!=)(.*)", token)
                if assignment:
                    value = self.evaluate(assignment.group(3))
                    if assignment.group(2) == "+=":
                        value = self.players[self.selected][assignment.group(1)] + value
                    self.players[self.selected][assignment.group(1)] = value
                elif token.startswith("Call Subroutine("):
                    routine = token[len("Call Subroutine("):-1]
                    if routine == "KunciBot":
                        continue  # Hero ability locking is outside spawn placement.
                    if routine != "CariPosisiTeleportasiAman":
                        raise AssertionError(f"unexpected spawn helper: {routine}")
                    helper = validator.rule_by_subroutine(self.rules, routine)
                    self.inside_helper = True
                    try:
                        self.execute(validator.rule_block(helper, "actions"))
                    finally:
                        self.inside_helper = False
                else:
                    self.evaluate(token)
        if frames:
            raise AssertionError("unbalanced spawn control flow")

    def step(self, now, selected="one", prefix="03f"):
        self.now, self.selected = now, selected
        rule = self.rule(prefix)
        conditions = validator.mask_strings(validator.rule_block(rule, "conditions"))
        if all(self.evaluate(part.strip()) for part in conditions.split(";") if part.strip()):
            self.execute(validator.rule_block(rule, "actions"))


class DummySpawnRetryTests(unittest.TestCase):
    def models(self):
        for path in (ROOT / "workshop/ruang_irama.it-IT.workshop",
                     ROOT / "tests/fixtures/semantic_reference.txt"):
            yield path.name, SpawnEvaluator(path.read_text(encoding="utf-8"))

    def test_skirmish_uses_the_current_objective_for_both_teams(self):
        for source, model in self.models():
            for team in (1, 2):
                for objective_index in (0, 1):
                    with self.subTest(source=source, team=team, objective_index=objective_index):
                        model.objective_index = objective_index
                        model.teleports = []
                        model.add_player("one", team=team, position=model.spawn[team])
                        model.step(100)
                        model.step(101)
                        self.assertEqual(model.players["one"]["PosisiMati"], model.objectives[objective_index])
                        self.assertEqual(len(model.teleports), 1)

    def test_other_modes_do_not_start_dummy_spawn_teleports(self):
        for source, model in self.models():
            for team in (1, 2):
                for mode in ("CaptureTheFlag", "TeamDeathmatch", "Deathmatch", "Hybrid", "Escort",
                             "Push", "Control", "Assault", "Flashpoint", "Clash", "Elimination"):
                    with self.subTest(source=source, team=team, mode=mode):
                        model.mode = mode
                        before = dict(model.add_player("one", team=team, position=model.spawn[team]))
                        model.step(100)
                        model.step(101)
                        self.assertEqual(model.players["one"], before)
                        self.assertEqual(model.candidates, [])
                        self.assertEqual(model.teleports, [])

    def test_missing_destination_skips_teleport_until_a_valid_objective_is_available(self):
        for source, model in self.models():
            for team in (1, 2):
                with self.subTest(source=source, team=team):
                    model.objectives = {}
                    model.candidates = []
                    model.teleports = []
                    model.add_player("one", team=team, position=model.spawn[team])
                    model.step(100)
                    model.step(101)
                    self.assertEqual(model.candidates, [])
                    self.assertEqual(model.teleports, [])
                    self.assertEqual(model.players["one"]["WaktuTeleportasiBotBuatan"], 102)
                    model.objectives[0] = Vector(100, 20, 100)
                    model.step(102)
                    self.assertEqual(len(model.teleports), 1)

    def test_failed_first_candidate_retries_a_different_point_and_can_exit(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.reject_attempts = 1
                model.step(100)
                model.step(101)
                self.assertEqual(model.teleports, [])
                first = model.candidates[-1][2]
                model.step(102)
                second = model.candidates[-1][2]
                self.assertNotEqual(first, second)
                self.assertEqual(len(model.teleports), 1)
                self.assertEqual(model.players["one"]["KursorTeleportasiBotBuatan"], 2)
                # A Teleport call alone is not proof the engine moved it out of spawn.
                model.step(103)
                self.assertEqual(len(model.teleports), 2)
                self.assertNotEqual(model.candidates[-1][2], second)
                model.players["one"]["spawn_room"] = False
                model.step(104)
                self.assertEqual(len(model.teleports), 2)

    def test_large_spawn_height_difference_keeps_sixteen_distinct_horizontal_candidates(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.spawn[1] = Vector(100, 1000, 40)
                model.reject_attempts = 100
                model.step(100)
                for now in range(101, 117):
                    model.step(now)
                points = [row[2] for row in model.candidates]
                self.assertEqual(len(points), 16)
                self.assertEqual(len({(round(p.x, 7), round(p.z, 7)) for p in points}), 16)
                for index, point in enumerate(points):
                    self.assertAlmostEqual(point.y, model.objectives[0].y)
                    self.assertAlmostEqual((point - model.objectives[0]).magnitude(), 8 if index < 8 else 12)
                self.assertEqual(model.players["one"]["KursorTeleportasiBotBuatan"], 0)
                self.assertEqual(model.teleports, [])

    def test_attempts_are_one_second_apart_and_humans_dead_or_outside_spawn_are_excluded(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.reject_attempts = 100
                for tick in range(62):
                    model.step(100 + tick * 0.05)
                self.assertEqual([round(row[1], 2) for row in model.candidates], [101, 102, 103])
                before = len(model.candidates)
                for changed in (dict(dummy=False, BotOtomatis=True), dict(alive=False),
                                dict(spawned=False), dict(spawn_room=False)):
                    model.add_player("one", **changed)
                    model.step(200)
                    model.step(201)
                self.assertEqual(len(model.candidates), before)
                self.assertEqual(model.teleports, [])

    def test_two_bots_keep_independent_retry_cursors_and_deadlines(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.reject_attempts = 100
                model.add_player("two", team=2)
                model.step(100, "one")
                model.step(101, "one")
                model.step(102, "one")
                first = dict(model.players["one"])
                model.step(102.5, "two")
                model.step(103.5, "two")
                self.assertEqual(model.players["one"], first)
                self.assertEqual(model.players["one"]["KursorTeleportasiBotBuatan"], 2)
                self.assertEqual(model.players["two"]["KursorTeleportasiBotBuatan"], 1)
                self.assertEqual(model.players["one"]["WaktuTeleportasiBotBuatan"], 103)
                self.assertEqual(model.players["two"]["WaktuTeleportasiBotBuatan"], 104.5)

    def test_death_and_respawn_reset_the_search_and_require_the_initial_delay_again(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.reject_attempts = 100
                model.step(100)
                model.step(101)
                original = model.candidates[-1][2]
                model.step(102)
                player = model.players["one"]
                player["alive"] = False
                model.step(102.1, prefix="03i")
                self.assertEqual(player["KursorTeleportasiBotBuatan"], 0)
                self.assertEqual(player["WaktuTeleportasiBotBuatan"], 0)
                player.update(alive=True, KunciBotAktif=False, KursorTeleportasiBotBuatan=7)
                model.step(105, prefix="03c")
                self.assertEqual(player["KursorTeleportasiBotBuatan"], 0)
                self.assertEqual(player["WaktuTeleportasiBotBuatan"], 106)
                before = len(model.candidates)
                model.step(105)
                model.step(105.99)
                self.assertEqual(len(model.candidates), before)
                model.step(106)
                self.assertEqual(model.candidates[-1][2], original)


if __name__ == "__main__":
    unittest.main()
