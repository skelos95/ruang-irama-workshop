"""Execute camera reset paths from the input and actual generated artifacts.

Native teleport/rendering and the walkable-position solver are controlled
boundaries. These tests assert ordering and ownership, not client rendering.
"""
from pathlib import Path
import re
import unittest

from tests.test_fly_motion import Vector
from tests.test_global_controller_execution import ControllerExpression
from tools import validate_global_runtime as runtime
from tools import validate_workshop as semantic

ROOT = Path(__file__).resolve().parents[1]
PATHS = (
    ROOT / "source/ruang_irama.en-US.source",
    ROOT / "tests/fixtures/semantic_reference.txt",
    ROOT / "workshop/ruang_irama.en-US.workshop",
    ROOT / "tests/fixtures/global_runtime_reference.txt",
)


class CameraResetEvaluator:
    def __init__(self, text):
        text = runtime.english(text) if text.lstrip().startswith("variabili") else text
        # Logical per-player callers and compiled dispatch share the same owner.
        text = re.sub(r"\bEvent Player\b", "Global.TriggerPlayer", text)
        self.rules = semantic.extract_rules(text)
        self.players = {}
        self.globals = {"TriggerPlayer": None, "ActivePlayer": None, "CameraPlayer": None}
        self.literals = {}
        self.steps = []
        self.native_cameras = {}
        self.now = 10
        self.spawn_points = [Vector(100, 2, 10)]
        self.objective = Vector(50, 2, 20)
        self.safe_position = Vector(40, 2, 20)

    def add(self, name, **changes):
        state = dict(IsHuman=True, CameraMode=1, CameraTarget=name,
                     exists=True, alive=True, spawned=True, team=1, in_spawn=False,
                     position=Vector(1, 2, 3), facing=Vector(0, 0, 1), hero="new",
                     LastHero="old", LuckActive=False,
                     LuckSpinCount=0, LuckEffect=0, LuckEffectEndTime=0,
                     MenuOpen=False, LockedTravelTarget="target",
                     TravelTargets=["target"], PlayerCycleActive=False,
                     InspectionPrivacyActive=False)
        state.update(changes)
        self.players[name] = state
        return state

    def resolve(self, name):
        if name in self.literals:
            return self.literals[name]
        constants = {"True": True, "False": False, "Null": None,
                     "EmptyArray": [], "TotalTimeElapsed": self.now,
                     "ObjectiveIndex": 0, "Team1": 1, "Team2": 2}
        if name in constants:
            return constants[name]
        if name.startswith("Global."):
            parts = name.split(".")
            value = self.globals.get(parts[1])
            for field in parts[2:]:
                value = self.players.get(value, {}).get(field, False)
            return value
        return name

    def call(self, name, args):
        if name == "And": return all(args)
        if name == "Or": return any(args)
        if name == "Not": return not args[0]
        if name == "Array": return list(args)
        if name == "CountOf": return len(args[0])
        if name == "ArrayContains": return args[1] in args[0]
        if name == "PlayerVariable": return self.players.get(args[0], {}).get(args[1], False)
        if name == "EvaluateOnce": return args[0]
        if name == "Vector": return Vector(*args)
        if name == "DistanceBetween": return (args[0] - args[1]).magnitude()
        if name == "SpawnPoints": return self.spawn_points
        if name == "FirstOf": return args[0][0] if args[0] else None
        if name == "ObjectivePosition": return self.objective
        if name == "CustomString": return args[0].format(*args[1:])
        keys = {"EntityExists": "exists", "HasSpawned": "spawned", "IsAlive": "alive",
                "TeamOf": "team", "IsInSpawnRoom": "in_spawn", "HeroOf": "hero",
                "PositionOf": "position", "FacingDirectionOf": "facing"}
        if name in keys:
            if name == "PositionOf" and isinstance(args[0], Vector): return args[0]
            return self.players.get(args[0], {}).get(keys[name], False)
        raise AssertionError(f"unsupported camera expression {name}")

    def expression(self, source):
        def literal(match):
            key = f"Literal{len(self.literals)}"
            self.literals[key] = match[0][1:-1]
            return key
        source = re.sub(r'"(?:\\.|[^"\\])*"', literal, source)
        return ControllerExpression(re.sub(r"\s+", "", source)).evaluate(self)

    def assign(self, target, value):
        parts = re.sub(r"\s+", "", target).split(".")
        if len(parts) == 2:
            self.globals[parts[1]] = value
        elif len(parts) == 3:
            self.players[self.globals[parts[1]]][parts[2]] = value
        else:
            raise AssertionError(f"unsupported camera assignment {target}")

    def body(self, target):
        rule = semantic.rule_by_subroutine(self.rules, target)
        if rule is None: raise AssertionError(f"missing subroutine {target}")
        return semantic.rule_block(rule, "actions")

    def execute(self, actions):
        actions = re.sub(r'(?m)^[ \t]*"(?:\\.|[^"\\])*"[ \t]*(?:\r?\n|$)', "", actions)
        frames, active = [], True
        for raw in semantic.split_top_level(actions, ";"):
            statement = raw.strip()
            if not statement: continue
            if statement.startswith("If("):
                taken = active and bool(self.expression(statement[3:-1]))
                frames.append((active, taken))
                active = taken
            elif statement.startswith("Else If("):
                parent, taken = frames[-1]
                active = parent and not taken and bool(self.expression(statement[8:-1]))
                frames[-1] = (parent, taken or active)
            elif statement == "Else":
                parent, taken = frames[-1]
                active = parent and not taken
                frames[-1] = (parent, True)
            elif statement == "End":
                active = frames.pop()[0]
            elif active:
                if statement == "Abort": return
                if statement.startswith("Abort If("):
                    if self.expression(statement[9:-1]): return
                    continue
                assignment = re.fullmatch(r"(Global\.\w+(?:\.\w+)?)\s*=\s*(.+)", statement, re.S)
                if assignment:
                    self.assign(assignment[1], self.expression(assignment[2]))
                    continue
                name = statement.split("(", 1)[0]
                call = next(semantic.iter_calls(statement, name))
                if name == "Call Subroutine":
                    target = call.args[0]
                    if target == "FindSafeTravelPosition":
                        self.players[self.globals["TriggerPlayer"]]["SafeRevivePosition"] = self.safe_position
                    elif target == "RestoreActivePlayerLuck":
                        self.players[self.globals["ActivePlayer"]]["LuckEffect"] = 0
                    else:
                        self.execute(self.body(target))
                elif name == "Stop Camera":
                    owner = self.expression(call.args[0])
                    self.steps.append(("stop", owner))
                    self.native_cameras.pop(owner, None)
                elif name == "Teleport":
                    owner, destination = map(self.expression, call.args)
                    self.steps.append(("teleport", owner))
                    self.players[owner]["position"] = destination
                elif name == "Start Camera":
                    owner = self.expression(call.args[0])
                    self.steps.append(("start", owner))
                    self.native_cameras[owner] = self.players[owner]["CameraTarget"]
                elif name == "Set Player Variable":
                    owner = self.expression(call.args[0])
                    self.players[owner][call.args[1]] = self.expression(call.args[2])
                elif name in {"Small Message", "Set Move Speed"}:
                    pass
                else:
                    raise AssertionError(f"unsupported camera action {name}")
        if frames: raise AssertionError("unclosed camera branch")

    def route(self, owner, target):
        self.globals.update(TriggerPlayer=owner, ActivePlayer=owner)
        self.execute(self.body(target))

    def hero_change(self, owner):
        self.globals.update(TriggerPlayer=owner, ActivePlayer=owner)
        cycle = semantic.rule_by_subroutine(self.rules, "ProcessPlayerCycle")
        marker = re.search(r"Global\.ActivePlayer\.LastHero\s*=\s*Hero Of", cycle.body)
        branches = semantic.conditional_branches_containing(cycle.body, marker.start())
        self.execute(max(branches, key=len))


class CameraReinitializationTests(unittest.TestCase):
    def models(self):
        for path in PATHS:
            yield path.name, CameraResetEvaluator(path.read_text(encoding="utf-8"))

    def setup_players(self, model, mode=1):
        state = model.add("viewer", CameraMode=mode,
                          CameraTarget="target" if mode == 2 else "viewer")
        model.add("target")
        return state

    def test_each_travel_success_stops_before_teleport_and_restarts_once(self):
        for source, model in self.models():
            for mode in (1, 2):
                for target in ("TravelToSpawn", "TravelToObjective", "TravelToPlayer"):
                    with self.subTest(source=source, mode=mode, target=target):
                        state = self.setup_players(model, mode)
                        previous = state["CameraTarget"]
                        model.steps.clear()
                        model.route("viewer", target)
                        self.assertEqual(model.steps, [("stop", "viewer"), ("teleport", "viewer"), ("start", "viewer")])
                        self.assertEqual((state["CameraMode"], state["CameraTarget"]), (mode, previous))
                        self.assertIsNone(model.globals["CameraPlayer"])

    def test_camera_off_teleports_without_camera_calls(self):
        for source, model in self.models():
            for target in ("TravelToSpawn", "TravelToObjective", "TravelToPlayer"):
                with self.subTest(source=source, target=target):
                    self.setup_players(model, 0)
                    model.steps.clear()
                    model.route("viewer", target)
                    self.assertEqual(model.steps, [("teleport", "viewer")])

    def test_rejected_and_noop_routes_do_not_touch_camera(self):
        cases = (("TravelToSpawn", "already_spawn"),
                 ("TravelToSpawn", "missing_spawn"),
                 ("TravelToObjective", "missing_objective"),
                 ("TravelToObjective", "unsafe"),
                 ("TravelToPlayer", "missing_target"),
                 ("TravelToPlayer", "unsafe"))
        for path in PATHS:
            for target, failure in cases:
                with self.subTest(source=path.name, target=target, failure=failure):
                    model = CameraResetEvaluator(path.read_text(encoding="utf-8"))
                    state = self.setup_players(model)
                    if failure == "already_spawn": state["in_spawn"] = True
                    if failure == "missing_spawn": model.spawn_points = []
                    if failure == "missing_objective": model.objective = Vector(0, 0, 0)
                    if failure == "missing_target": state["LockedTravelTarget"] = None
                    if failure == "unsafe": model.safe_position = Vector(0, 0, 0)
                    model.route("viewer", target)
                    self.assertEqual(model.steps, [])
                    self.assertEqual(state["CameraMode"], 1)

    def test_hero_change_restarts_once_preserving_camera_preferences(self):
        for source, model in self.models():
            for mode in (1, 2):
                with self.subTest(source=source, mode=mode):
                    state = self.setup_players(model, mode)
                    previous = state["CameraTarget"]
                    model.steps.clear()
                    model.hero_change("viewer")
                    self.assertEqual(model.steps, [("stop", "viewer"), ("start", "viewer")])
                    self.assertEqual((state["CameraMode"], state["CameraTarget"]), (mode, previous))
                    self.assertIsNone(model.globals["CameraPlayer"])
                    model.steps.clear()
                    model.hero_change("viewer")
                    self.assertEqual(model.steps, [])

    def test_hero_change_with_off_or_missing_target_does_not_restart(self):
        for path in PATHS:
            for mode, target in ((0, "viewer"), (1, None), (2, "gone")):
                with self.subTest(source=path.name, mode=mode, target=target):
                    model = CameraResetEvaluator(path.read_text(encoding="utf-8"))
                    model.add("viewer", CameraMode=mode, CameraTarget=target)
                    model.hero_change("viewer")
                    self.assertEqual(model.steps, [])

    def test_two_players_reset_only_their_own_native_camera(self):
        for source, model in self.models():
            with self.subTest(source=source):
                self.setup_players(model)
                model.add("other", CameraMode=2, CameraTarget="target")
                model.native_cameras["other"] = "target"
                model.route("viewer", "TravelToObjective")
                self.assertEqual(model.native_cameras["other"], "target")
                model.hero_change("other")
                self.assertEqual(model.steps[-2:], [("stop", "other"), ("start", "other")])
                self.assertEqual(model.native_cameras["viewer"], "viewer")


if __name__ == "__main__":
    unittest.main()
