"""Evaluate logical input Fly expressions and branches before compilation.

This deliberately small evaluator covers only the mathematical expressions and
control flow used by ProsesTerbangPemain. It is not an Overwatch engine simulator:
collision, friction, networking, and native hero behavior still require live QA.
The controller's standard Fly 100% is 5.5 m/s, not an individual hero's speed.

The test pose uses a synthetic world frame: yaw zero faces +Z, positive yaw
turns toward +X, and positive test pitch looks up. These are not assertions
about the client's displayed angle zero/sign. HorizontalFacingAngleOf and
DirectionFromAngles(angle, 0) form a paired round trip in this frame; only that
horizontal form is supported here. The directional conventions are Workshop's:
raw throttle +X means left, +Z means forward, +Y world means up, and left cross
up equals forward. Thus up cross horizontal-forward must mean player-left.
"""

from __future__ import annotations

import math
import re
import unittest
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Vector:
    x: float
    y: float
    z: float

    def __add__(self, other: Vector) -> Vector:
        return Vector(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vector) -> Vector:
        return Vector(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> Vector:
        return Vector(self.x * scalar, self.y * scalar, self.z * scalar)

    __rmul__ = __mul__

    def __truediv__(self, scalar: float) -> Vector:
        return self * (1 / scalar)

    def __neg__(self) -> Vector:
        return self * -1

    def magnitude(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def normalized(self) -> Vector:
        return self / self.magnitude() if self.magnitude() else self


ZERO = Vector(0, 0, 0)


class Expression:
    """A strict arithmetic/function parser; source text is never passed to eval."""

    TOKEN = re.compile(r"\d+(?:\.\d+)?|[A-Za-z_][A-Za-z_0-9.]*|==|!=|>=|<=|[()+\-*/,<>]")
    PRECEDENCE = {"==": 1, "!=": 1, ">=": 1, "<=": 1, ">": 1, "<": 1, "+": 2, "-": 2, "*": 3, "/": 3}

    def __init__(self, source: str) -> None:
        self.tokens = self.TOKEN.findall(source)
        if "".join(self.tokens) != source:
            raise AssertionError(f"unsupported Workshop expression: {source}")
        self.index = 0
        self.tree = self.parse()
        if self.index != len(self.tokens):
            raise AssertionError(f"unconsumed Workshop expression: {source}")

    def take(self, wanted: str | None = None) -> str:
        value = self.tokens[self.index]
        self.index += 1
        if wanted is not None and value != wanted:
            raise AssertionError(f"expected {wanted!r}, got {value!r}")
        return value

    def peek(self) -> str | None:
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def parse(self, minimum: int = 0):
        token = self.take()
        if token == "-":
            left = ("negate", self.parse(4))
        elif token == "(":
            left = self.parse()
            self.take(")")
        elif token[0].isdigit():
            left = ("literal", float(token))
        elif self.peek() == "(":
            self.take("(")
            arguments = []
            if self.peek() != ")":
                while True:
                    arguments.append(self.parse())
                    if self.peek() != ",":
                        break
                    self.take(",")
            self.take(")")
            left = ("call", token, arguments)
        else:
            left = ("name", token)
        while self.peek() in self.PRECEDENCE and self.PRECEDENCE[self.peek()] >= minimum:
            operator = self.take()
            left = (operator, left, self.parse(self.PRECEDENCE[operator] + 1))
        return left

    def evaluate(self, context: FlySourceEvaluator):
        def visit(node):
            operator = node[0]
            if operator == "literal":
                return node[1]
            if operator == "name":
                return context.resolve(node[1])
            if operator == "call":
                return context.call(node[1], [visit(argument) for argument in node[2]])
            if operator == "negate":
                return -visit(node[1])
            left, right = visit(node[1]), visit(node[2])
            if operator == "+":
                return left + right
            if operator == "-":
                return left - right
            if operator == "*":
                return left * right
            if operator == "/":
                return left / right
            if operator == "==":
                return left == right
            if operator == "!=":
                return left != right
            if operator == ">":
                return left > right
            if operator == "<":
                return left < right
            if operator == ">=":
                return left >= right
            if operator == "<=":
                return left <= right
            raise AssertionError(f"unsupported operator: {operator}")

        return visit(self.tree)


def motion_statements(source: str) -> tuple[str, ...]:
    headers = list(re.finditer(r'(?m)^(?:rule|regola)\("[^"\n]+"\)', source))
    rules = [source[header.start():headers[index + 1].start() if index + 1 < len(headers) else len(source)] for index, header in enumerate(headers)]
    matches = [rule for rule in rules if re.search(r"Subroutine\s*;\s*ProsesTerbangPemain\s*;", rule)]
    if len(matches) != 1:
        raise AssertionError("expected exactly one ProsesTerbangPemain rule")
    actions = re.search(r"\b(?:actions|azioni)\s*\{(.*)\}\s*\}\s*$", matches[0], re.DOTALL)
    if actions is None:
        raise AssertionError("Fly actions missing")
    uncommented = re.sub(r'"(?:\\.|[^"\\])*"', "", actions.group(1))
    packed = re.sub(r"\s+", "", uncommented)
    return tuple(statement for statement in packed.split(";") if statement)


def player_state(**changes) -> dict:
    state = {
        "Manusia": True,
        "BotOtomatis": False,
        "dummy": False,
        "spawned": True,
        "alive": True,
        "ModeTerbangAktif": True,
        "FisikaHantuTerbangDiterapkan": True,
        "EfekNasib": 0,
        "EfekNasibBerakhir": 0,
        "WaktuMulaiTerbangMaju": -1,
        "PersenTerbang": 100,
        "ArahTerbang": ZERO,
        "DeltaTerbang": ZERO,
        "throttle": ZERO,
        "velocity": ZERO,
        "yaw": 0,
        "pitch": 0,
        "move_speed": 100,
    }
    state.update(changes)
    return state


class FlySourceEvaluator:
    """Select the source's actual branches and evaluate its actual assignments."""

    OWNER = re.compile(r"^(?:Global|Globale)\.PemainAktif(?:\.(\w+))?$")

    def __init__(self, statements: tuple[str, ...], players: dict[str, dict] | None = None) -> None:
        self.statements = statements
        self.players = players if players is not None else {"one": player_state()}
        self.expressions: dict[str, Expression] = {}
        self.actions: list[tuple] = []
        self.selected = "one"
        self.now = 0.0

    def expression(self, source: str):
        if source not in self.expressions:
            self.expressions[source] = Expression(source)
        return self.expressions[source].evaluate(self)

    def resolve(self, name: str):
        owner = self.OWNER.fullmatch(name)
        if owner:
            return self.players[self.selected][owner.group(1)] if owner.group(1) else self.selected
        constants = {"True": True, "False": False, "TotalTimeElapsed": self.now, "Rotation": "Rotation", "ToWorld": "ToWorld", "IncorporateContraryMotion": "IncorporateContraryMotion"}
        if name not in constants:
            raise AssertionError(f"unsupported value: {name}")
        return constants[name]

    def call(self, name: str, arguments: list):
        if name == "Vector":
            return Vector(*arguments)
        if name == "And":
            return all(arguments)
        if name == "Or":
            return any(arguments)
        if name == "Min":
            return min(arguments)
        if name == "Max":
            return max(arguments)
        if name == "MagnitudeOf":
            return arguments[0].magnitude()
        if name == "Normalize":
            return arguments[0].normalized()
        if name in ("XComponentOf", "YComponentOf", "ZComponentOf"):
            return getattr(arguments[0], name[0].lower())
        if name == "CrossProduct":
            left, right = arguments
            return Vector(
                left.y * right.z - left.z * right.y,
                left.z * right.x - left.x * right.z,
                left.x * right.y - left.y * right.x,
            )
        if name == "DirectionFromAngles":
            horizontal, vertical = arguments
            if vertical != 0:
                raise AssertionError("only the source's horizontal DirectionFromAngles(angle, 0) is modeled")
            yaw = math.radians(horizontal)
            return Vector(math.sin(yaw), 0, math.cos(yaw))
        player_functions = {"ThrottleOf": "throttle", "VelocityOf": "velocity", "HasSpawned": "spawned", "IsAlive": "alive", "IsDummyBot": "dummy", "HorizontalFacingAngleOf": "yaw"}
        if name in player_functions:
            return self.players[arguments[0]][player_functions[name]]
        if name == "FacingDirectionOf":
            player = self.players[arguments[0]]
            yaw, pitch = math.radians(player["yaw"]), math.radians(player["pitch"])
            return Vector(math.sin(yaw) * math.cos(pitch), math.sin(pitch), math.cos(yaw) * math.cos(pitch))
        if name == "WorldVectorOf":
            vector, player_name, transform = arguments
            if transform != "Rotation":
                raise AssertionError("directions must not include translation")
            yaw = math.radians(self.players[player_name]["yaw"])
            return Vector(vector.x * math.cos(yaw) + vector.z * math.sin(yaw), vector.y, vector.z * math.cos(yaw) - vector.x * math.sin(yaw))
        if name == "SetMoveSpeed":
            player_name, speed = arguments
            self.players[player_name]["move_speed"] = speed
            self.actions.append((name, *arguments))
            return None
        if name == "ApplyImpulse":
            player_name, direction, speed, relative, motion = arguments
            if (relative, motion) != ("ToWorld", "IncorporateContraryMotion"):
                raise AssertionError("delta velocity needs world-space additive impulse")
            self.players[player_name]["velocity"] += direction.normalized() * speed
            self.actions.append((name, *arguments))
            return None
        raise AssertionError(f"unsupported function/action: {name}")

    def step(self, now: float, selected: str = "one") -> None:
        self.now, self.selected = now, selected
        self.actions = []
        frames = []
        active = True
        for statement in self.statements:
            if statement.startswith("If("):
                condition = bool(self.expression(statement[3:-1])) if active else False
                frames.append({"parent": active, "taken": condition})
                active = active and condition
            elif statement.startswith("ElseIf("):
                frame = frames[-1]
                active = frame["parent"] and not frame["taken"] and bool(self.expression(statement[7:-1]))
                frame["taken"] = frame["taken"] or active
            elif statement == "Else":
                frame = frames[-1]
                active = frame["parent"] and not frame["taken"]
                frame["taken"] = True
            elif statement == "End":
                active = frames.pop()["parent"]
            elif active:
                assignment = re.fullmatch(r"((?:Global|Globale)\.PemainAktif\.\w+)=(?!=)(.*)", statement)
                if assignment:
                    member = self.OWNER.fullmatch(assignment.group(1)).group(1)
                    self.players[self.selected][member] = self.expression(assignment.group(2))
                else:
                    self.expression(statement)
        if frames:
            raise AssertionError("unbalanced Fly control flow")


class FlyMotionExpressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.programs = tuple(
            (path.name, motion_statements(path.read_text(encoding="utf-8")))
            for path in (
                ROOT / "source" / "ruang_irama.it-IT.source",
                ROOT / "tests" / "fixtures" / "semantic_reference.txt",
            )
        )

    def assertVectorClose(self, actual: Vector, expected: Vector) -> None:
        for axis in ("x", "y", "z"):
            self.assertAlmostEqual(getattr(actual, axis), getattr(expected, axis), places=8, msg=f"{axis}: {actual} != {expected}")

    def test_evaluator_preserves_workshop_cross_product_handedness_and_horizontal_round_trip(self) -> None:
        evaluator = FlySourceEvaluator(())
        left, up, forward = Vector(1, 0, 0), Vector(0, 1, 0), Vector(0, 0, 1)
        for first, second, expected in ((left, up, forward), (up, forward, left), (forward, up, -left)):
            self.assertVectorClose(evaluator.call("CrossProduct", [first, second]), expected)
        for yaw, forward in ((0, Vector(0, 0, 1)), (90, Vector(1, 0, 0)), (180, Vector(0, 0, -1)), (270, Vector(-1, 0, 0))):
            evaluator.players["one"].update(yaw=yaw, pitch=90)
            angle = evaluator.call("HorizontalFacingAngleOf", ["one"])
            self.assertVectorClose(evaluator.call("DirectionFromAngles", [angle, 0]), forward)
        with self.assertRaisesRegex(AssertionError, "only the source's horizontal"):
            evaluator.call("DirectionFromAngles", [0, 45])

    def test_standard_fly_ramp_uses_the_source_formula_and_caps_after_twenty_seconds(self) -> None:
        """100% is the explicit 5.5 m/s Fly baseline, irrespective of hero selection."""
        for name, program in self.programs:
            for elapsed, percent, speed in ((0, 100, 5.5), (5, 325, 17.875), (10, 550, 30.25), (19.999, 999.955, 54.997525), (20, 1000, 55), (20.001, 1000, 55), (60, 1000, 55)):
                with self.subTest(source=name, elapsed=elapsed):
                    player = player_state(throttle=Vector(0, 0, 1))
                    evaluator = FlySourceEvaluator(program, {"one": player})
                    evaluator.step(100)
                    evaluator.step(100 + elapsed)
                    self.assertAlmostEqual(player["PersenTerbang"], percent)
                    self.assertEqual(player["WaktuMulaiTerbangMaju"], 100)
                    self.assertEqual(player["move_speed"], 0)
                    self.assertVectorClose(player["velocity"], Vector(0, 0, speed))

    def test_looking_up_and_down_preserves_full_vertical_motion(self) -> None:
        for name, program in self.programs:
            for pitch, expected in ((90, Vector(0, 5.5, 0)), (-90, Vector(0, -5.5, 0)), (45, Vector(0, 5.5 / math.sqrt(2), 5.5 / math.sqrt(2))), (-45, Vector(0, -5.5 / math.sqrt(2), 5.5 / math.sqrt(2)))):
                with self.subTest(source=name, pitch=pitch):
                    player = player_state(throttle=Vector(0, 0, 1), pitch=pitch)
                    FlySourceEvaluator(program, {"one": player}).step(100)
                    self.assertVectorClose(player["velocity"], expected)

    def test_forward_follows_all_cardinal_yaws(self) -> None:
        for name, program in self.programs:
            for yaw, expected in ((0, Vector(0, 0, 5.5)), (90, Vector(5.5, 0, 0)), (180, Vector(0, 0, -5.5)), (270, Vector(-5.5, 0, 0))):
                with self.subTest(source=name, yaw=yaw):
                    player = player_state(throttle=Vector(0, 0, 1), yaw=yaw)
                    FlySourceEvaluator(program, {"one": player}).step(100)
                    self.assertVectorClose(player["velocity"], expected)

    def test_positive_x_is_left_and_negative_x_is_right_even_when_looking_vertical(self) -> None:
        for name, program in self.programs:
            for yaw, left in ((0, Vector(5.5, 0, 0)), (90, Vector(0, 0, -5.5)), (180, Vector(-5.5, 0, 0)), (270, Vector(0, 0, 5.5))):
                for pitch in (-90, -45, 0, 45, 90):
                    for x in (-1, 1):
                        with self.subTest(source=name, yaw=yaw, pitch=pitch, throttle_x=x):
                            player = player_state(throttle=Vector(x, 0, 0), yaw=yaw, pitch=pitch)
                            FlySourceEvaluator(program, {"one": player}).step(100)
                            self.assertVectorClose(player["velocity"], left * x)
                            self.assertEqual(player["WaktuMulaiTerbangMaju"], 100)

    def test_swapping_the_source_cross_product_operands_reverses_strafe_and_fails_the_oracle(self) -> None:
        for name, program in self.programs:
            with self.subTest(source=name):
                pattern = re.compile(
                    r"CrossProduct\(Vector\(0,1,0\),(DirectionFromAngles\(HorizontalFacingAngleOf\("
                    r"(?:Global|Globale)\.PemainAktif\),0\))\)"
                )
                mutations = [pattern.subn(r"CrossProduct(\1,Vector(0,1,0))", statement) for statement in program]
                self.assertEqual(sum(count for _, count in mutations), 1)
                mutated_program = tuple(statement for statement, _ in mutations)
                expected_left = Vector(5.5, 0, 0)
                original = player_state(throttle=Vector(1, 0, 0), pitch=90)
                mutated = player_state(throttle=Vector(1, 0, 0), pitch=90)
                FlySourceEvaluator(program, {"one": original}).step(100)
                FlySourceEvaluator(mutated_program, {"one": mutated}).step(100)
                self.assertVectorClose(original["velocity"], expected_left)
                self.assertVectorClose(mutated["velocity"], -expected_left)
                with self.assertRaises(AssertionError):
                    self.assertVectorClose(mutated["velocity"], expected_left)

    def test_backward_stays_horizontal_for_every_pitch_while_ramping(self) -> None:
        for name, program in self.programs:
            for yaw, backward in ((0, Vector(0, 0, -5.5)), (90, Vector(-5.5, 0, 0)), (180, Vector(0, 0, 5.5)), (270, Vector(5.5, 0, 0))):
                for pitch in (-90, -45, 0, 45, 90):
                    with self.subTest(source=name, yaw=yaw, pitch=pitch):
                        player = player_state(throttle=Vector(0, 0, -1), yaw=yaw, pitch=pitch)
                        evaluator = FlySourceEvaluator(program, {"one": player})
                        evaluator.step(100)
                        self.assertVectorClose(player["velocity"], backward)
                        evaluator.step(130)
                        self.assertVectorClose(player["velocity"], backward * 10)
                        self.assertEqual(player["PersenTerbang"], 1000)
                        self.assertEqual(player["WaktuMulaiTerbangMaju"], 100)

    def test_forward_and_backward_diagonals_keep_the_correct_side_and_height(self) -> None:
        diagonal = 5.5 / math.sqrt(2)
        cases = (
            (Vector(1, 0, 1), 45, Vector(diagonal, 2.75, 2.75)),
            (Vector(-1, 0, 1), 45, Vector(-diagonal, 2.75, 2.75)),
            (Vector(1, 0, -1), 45, Vector(diagonal, 0, -diagonal)),
            (Vector(-1, 0, -1), -45, Vector(-diagonal, 0, -diagonal)),
            (Vector(1, 0, 1), 90, Vector(diagonal, diagonal, 0)),
            (Vector(-1, 0, 1), -90, Vector(-diagonal, -diagonal, 0)),
        )
        for name, program in self.programs:
            for throttle, pitch, expected in cases:
                with self.subTest(source=name, throttle=throttle, pitch=pitch):
                    player = player_state(throttle=throttle, pitch=pitch)
                    evaluator = FlySourceEvaluator(program, {"one": player})
                    evaluator.step(100)
                    self.assertVectorClose(player["velocity"], expected)
                    evaluator.step(130)
                    self.assertVectorClose(player["velocity"], expected * 10)
                    self.assertEqual(player["PersenTerbang"], 1000)

    def test_diagonal_input_is_normalized_and_ramps_to_the_same_speed_cap(self) -> None:
        for name, program in self.programs:
            for magnitude in (1, 1 / math.sqrt(2)):
                with self.subTest(source=name, component=magnitude):
                    player = player_state(throttle=Vector(magnitude, 0, magnitude), pitch=45)
                    evaluator = FlySourceEvaluator(program, {"one": player})
                    evaluator.step(100)
                    evaluator.step(130)
                    self.assertAlmostEqual(player["velocity"].magnitude(), 55)
                    self.assertEqual(player["PersenTerbang"], 1000)
                    self.assertEqual(player["WaktuMulaiTerbangMaju"], 100)
                    self.assertGreater(player["velocity"].y, 0)

    def test_analog_intensity_scales_actual_velocity_and_deadzone_stays_still(self) -> None:
        for name, program in self.programs:
            for throttle, expected in (
                (Vector(0, 0, 0.5), 2.75), (Vector(0, 0, -0.5), 2.75),
                (Vector(0.5, 0, 0), 2.75), (Vector(-0.5, 0, 0), 2.75),
                (Vector(0.04, 0, 0.04), 5.5 * math.sqrt(0.0032)),
                (Vector(0, 0, 0.05), 0), (Vector(0.05, 0, 0), 0), (ZERO, 0),
            ):
                with self.subTest(source=name, throttle=throttle):
                    player = player_state(throttle=throttle)
                    evaluator = FlySourceEvaluator(program, {"one": player})
                    evaluator.step(100)
                    self.assertAlmostEqual(player["velocity"].magnitude(), expected)
                    if expected > 0:
                        self.assertEqual(player["WaktuMulaiTerbangMaju"], 100)
                        evaluator.step(125)
                        self.assertAlmostEqual(player["velocity"].magnitude(), expected * 10)
                        self.assertEqual(player["PersenTerbang"], 1000)
                    else:
                        self.assertEqual(player["WaktuMulaiTerbangMaju"], -1)
                        self.assertEqual(player["PersenTerbang"], 100)

    def test_direction_changes_continue_the_same_ramp_without_restarting(self) -> None:
        directions = (
            (100, Vector(0, 0, 1), 100, Vector(0, 0, 5.5)),
            (105, Vector(-1, 0, 0), 325, Vector(-17.875, 0, 0)),
            (110, Vector(0, 0, -1), 550, Vector(0, 0, -30.25)),
            (115, Vector(1, 0, -1), 775, Vector(42.625 / math.sqrt(2), 0, -42.625 / math.sqrt(2))),
            (120, Vector(-1, 0, 1), 1000, Vector(-55 / math.sqrt(2), 0, 55 / math.sqrt(2))),
            (125, Vector(1, 0, 0), 1000, Vector(55, 0, 0)),
        )
        for name, program in self.programs:
            with self.subTest(source=name):
                player = player_state()
                evaluator = FlySourceEvaluator(program, {"one": player})
                for now, throttle, percent, velocity in directions:
                    player["throttle"] = throttle
                    evaluator.step(now)
                    self.assertEqual(player["WaktuMulaiTerbangMaju"], 100)
                    self.assertEqual(player["PersenTerbang"], percent)
                    self.assertVectorClose(player["velocity"], velocity)

    def test_release_or_directional_deadzone_resets_the_actual_source_timer(self) -> None:
        for name, program in self.programs:
            for throttle in (ZERO, Vector(0.05, 0, 0), Vector(-0.05, 0, 0),
                             Vector(0, 0, 0.05), Vector(0, 0, -0.05), Vector(0.03, 0, 0.03)):
                with self.subTest(source=name, throttle=throttle):
                    player = player_state(throttle=Vector(0, 0, 1))
                    evaluator = FlySourceEvaluator(program, {"one": player})
                    evaluator.step(100)
                    evaluator.step(125)
                    self.assertEqual(player["PersenTerbang"], 1000)
                    self.assertVectorClose(player["velocity"], Vector(0, 0, 55))
                    player["throttle"] = throttle
                    evaluator.step(126)
                    self.assertEqual(player["PersenTerbang"], 100)
                    self.assertEqual(player["WaktuMulaiTerbangMaju"], -1)
                    player["throttle"] = Vector(0, 0, 1)
                    evaluator.step(140)
                    self.assertEqual(player["WaktuMulaiTerbangMaju"], 140)
                    self.assertVectorClose(player["velocity"], Vector(0, 0, 5.5))

    def test_twelve_players_keep_independent_ramps_across_direction_changes(self) -> None:
        directions = (Vector(0, 0, 1), Vector(1, 0, 0), Vector(0, 0, -1), Vector(-1, 0, 1))
        for name, program in self.programs:
            with self.subTest(source=name):
                players = {str(index): player_state(throttle=directions[index % 4]) for index in range(12)}
                evaluator = FlySourceEvaluator(program, players)
                for index in range(12):
                    evaluator.step(100 + index * 2, str(index))
                for index in range(12):
                    player = players[str(index)]
                    player["throttle"] = directions[(index + 1) % 4]
                    evaluator.step(125, str(index))
                    percent = min(1000, 100 + (25 - index * 2) * 45)
                    self.assertEqual(player["WaktuMulaiTerbangMaju"], 100 + index * 2)
                    self.assertEqual(player["PersenTerbang"], percent)
                    self.assertAlmostEqual(player["velocity"].magnitude(), 5.5 * percent / 100)
                snapshots = {key: state.copy() for key, state in players.items() if key != "0"}
                players["0"]["throttle"] = ZERO
                evaluator.step(126, "0")
                self.assertEqual(players["0"]["WaktuMulaiTerbangMaju"], -1)
                self.assertEqual(players["0"]["PersenTerbang"], 100)
                self.assertVectorClose(players["0"]["velocity"], ZERO)
                for key, snapshot in snapshots.items():
                    self.assertEqual(players[key], snapshot)

    def test_two_players_keep_independent_directions_timers_and_speed(self) -> None:
        for name, program in self.programs:
            with self.subTest(source=name):
                one = player_state(throttle=Vector(0, 0, 1))
                two = player_state(throttle=Vector(0, 0, 1), pitch=90)
                evaluator = FlySourceEvaluator(program, {"one": one, "two": two})
                evaluator.step(100, "one")
                evaluator.step(125, "one")
                evaluator.step(125, "two")
                self.assertVectorClose(one["velocity"], Vector(0, 0, 55))
                self.assertVectorClose(two["velocity"], Vector(0, 5.5, 0))
                self.assertEqual((one["WaktuMulaiTerbangMaju"], two["WaktuMulaiTerbangMaju"]), (100, 125))
                one["throttle"] = ZERO
                evaluator.step(130, "one")
                self.assertEqual(one["PersenTerbang"], 100)
                self.assertVectorClose(two["velocity"], Vector(0, 5.5, 0))
                evaluator.step(130, "two")
                self.assertVectorClose(two["velocity"], Vector(0, 17.875, 0))

    def test_idle_cancels_residual_velocity_without_zero_direction_impulses(self) -> None:
        for name, program in self.programs:
            with self.subTest(source=name):
                player = player_state(velocity=Vector(8, -9, 4))
                evaluator = FlySourceEvaluator(program, {"one": player})
                evaluator.step(100)
                self.assertVectorClose(player["DeltaTerbang"], Vector(-8, 9, -4))
                self.assertVectorClose(player["velocity"], ZERO)
                self.assertEqual(sum(action[0] == "ApplyImpulse" for action in evaluator.actions), 1)
                evaluator.step(101)
                self.assertFalse(any(action[0] == "ApplyImpulse" for action in evaluator.actions))

    def test_luck_acceleration_owns_velocity_until_expiry_then_fly_restarts_at_baseline(self) -> None:
        for name, program in self.programs:
            with self.subTest(source=name):
                player = player_state(throttle=Vector(0, 0, 1), EfekNasib=2, EfekNasibBerakhir=200, move_speed=1000, velocity=Vector(7, 8, 9), WaktuMulaiTerbangMaju=100, PersenTerbang=1000, ArahTerbang=Vector(1, 1, 1), DeltaTerbang=Vector(2, 2, 2))
                evaluator = FlySourceEvaluator(program, {"one": player})
                evaluator.step(150)
                self.assertEqual(evaluator.actions, [])
                self.assertEqual(player["move_speed"], 1000)
                self.assertVectorClose(player["velocity"], Vector(7, 8, 9))
                self.assertEqual(player["WaktuMulaiTerbangMaju"], -1)
                self.assertEqual(player["PersenTerbang"], 100)
                self.assertEqual(player["ArahTerbang"], ZERO)
                self.assertEqual(player["DeltaTerbang"], ZERO)
                evaluator.step(200)
                self.assertEqual(player["WaktuMulaiTerbangMaju"], 200)
                self.assertEqual(player["move_speed"], 0)
                self.assertVectorClose(player["velocity"], Vector(0, 0, 5.5))

    def test_ineligible_players_receive_no_fly_motion_actions(self) -> None:
        for name, program in self.programs:
            for flag, value in (("Manusia", False), ("BotOtomatis", True), ("dummy", True), ("spawned", False), ("alive", False), ("ModeTerbangAktif", False), ("FisikaHantuTerbangDiterapkan", False)):
                with self.subTest(source=name, flag=flag):
                    player = player_state(throttle=Vector(0, 0, 1), velocity=Vector(1, 2, 3), **{flag: value})
                    evaluator = FlySourceEvaluator(program, {"one": player})
                    evaluator.step(100)
                    self.assertEqual(evaluator.actions, [])
                    self.assertVectorClose(player["velocity"], Vector(1, 2, 3))


if __name__ == "__main__":
    unittest.main()
