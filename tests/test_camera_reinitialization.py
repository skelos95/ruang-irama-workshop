"""Execute camera reset paths from the input and actual generated artifacts.

Native teleport/rendering and the walkable-position solver are controlled
boundaries. These tests assert ordering and ownership, not client rendering.
"""
from pathlib import Path
import operator
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


class CameraExpression(ControllerExpression):
    """Evaluate native array filters lazily with their current-element scope."""
    def evaluate(self, context):
        operations = {
            "+": operator.add, "-": operator.sub, "*": operator.mul,
            "/": operator.truediv, "%": operator.mod, "==": operator.eq,
            "!=": operator.ne, ">=": operator.ge, "<=": operator.le,
            ">": operator.gt, "<": operator.lt,
        }

        def visit(node):
            kind = node[0]
            if kind == "literal": return node[1]
            if kind == "name": return context.resolve(node[1])
            if kind == "negate": return -visit(node[1])
            if kind == "conditional": return visit(node[2] if visit(node[1]) else node[3])
            if kind == "index":
                array, index = visit(node[1]), int(visit(node[2]))
                return array[index] if 0 <= index < len(array) else 0
            if kind == "call":
                name, args = node[1:]
                if name in ("And", "Or"):
                    return (all if name == "And" else any)(bool(visit(arg)) for arg in args)
                if name == "FilteredArray":
                    context.filter_builds += 1
                    previous = context.element
                    try:
                        result = []
                        for context.element in visit(args[0]):
                            if visit(args[1]): result.append(context.element)
                        return result
                    finally:
                        context.element = previous
                return context.call(name, [visit(arg) for arg in args])
            return operations[kind](visit(node[1]), visit(node[2]))

        return visit(self.tree)


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
        self.element = None
        self.filter_builds = 0
        self.player_order = None
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
                     InspectionPrivacyActive=False, PlayerListUpdatePending=False,
                     IsAutomaticBot=False, dummy=False, CameraCursor=0, CameraTargets=[])
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
        if name == "CurrentArrayElement": return self.element
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
        if name == "IndexOfArrayValue": return args[0].index(args[1]) if args[1] in args[0] else -1
        if name == "AllPlayers": return list(self.players) if self.player_order is None else self.player_order
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
                "PositionOf": "position", "FacingDirectionOf": "facing", "IsDummyBot": "dummy"}
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
        return CameraExpression(re.sub(r"\s+", "", source)).evaluate(self)

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
                assignment = re.fullmatch(r"(Global\.\w+(?:\.\w+)?)\s*(=|%=)\s*(.+)", statement, re.S)
                if assignment:
                    value = self.expression(assignment[3])
                    if assignment[2] == "%=": value = self.expression(assignment[1]) % value
                    self.assign(assignment[1], value)
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

    def test_camera_menu_same_watch_recovers_after_native_camera_is_lost(self):
        for source, model in self.models():
            with self.subTest(source=source):
                viewer = model.add("viewer", CameraMode=0, CameraTarget=None,
                                   CameraCursor=2, CameraTargets=["target"])
                model.add("target")
                model.route("viewer", "ApplyCameraPage")
                self.assertEqual(model.native_cameras.get("viewer"), "target")
                self.assertGreaterEqual(model.filter_builds, 2)
                self.assertEqual((viewer["CameraMode"], viewer["CameraTarget"]), (2, "target"))
                model.native_cameras.pop("viewer")
                model.steps.clear()
                model.route("viewer", "ApplyCameraPage")
                self.assertEqual(model.steps, [("stop", "viewer"), ("start", "viewer")])
                self.assertEqual(model.native_cameras.get("viewer"), "target")
                self.assertIsNone(model.globals["CameraPlayer"])

    def test_camera_menu_switches_and_reapplies_self_and_other_targets(self):
        for source, model in self.models():
            with self.subTest(source=source):
                viewer = model.add("viewer", CameraMode=0, CameraTarget=None,
                                   CameraTargets=["first", "second"])
                model.add("first")
                model.add("second")
                for selection in ("first", "first", "second", "viewer", "viewer", "first"):
                    with self.subTest(selection=selection):
                        viewer["CameraCursor"] = 1 if selection == "viewer" else viewer["CameraTargets"].index(selection) + 2
                        model.steps.clear()
                        model.route("viewer", "ApplyCameraPage")
                        self.assertEqual(model.steps, [("stop", "viewer"), ("start", "viewer")])
                        self.assertEqual((viewer["CameraMode"], viewer["CameraTarget"]),
                                         (1 if selection == "viewer" else 2, selection))
                        self.assertEqual(model.native_cameras["viewer"], selection)
                        self.assertIsNone(model.globals["CameraPlayer"])
                # Native player order may change while the menu keeps the selected identity.
                viewer["CameraCursor"] = viewer["CameraTargets"].index("second") + 2
                model.player_order = ["second", "viewer", "first"]
                model.steps.clear()
                model.route("viewer", "ApplyCameraPage")
                self.assertEqual(viewer["CameraTarget"], "second")
                self.assertEqual(viewer["CameraCursor"], 2)
                self.assertEqual(model.steps, [("stop", "viewer"), ("start", "viewer")])

    def test_camera_menu_off_always_stops_and_clears_preferences(self):
        for source, model in self.models():
            for mode in (0, 1, 2):
                with self.subTest(source=source, mode=mode):
                    viewer = model.add("viewer", CameraMode=mode, CameraTarget="target", CameraCursor=0)
                    model.add("target")
                    model.native_cameras["viewer"] = "target"
                    for _ in range(2):
                        model.steps.clear()
                        model.route("viewer", "ApplyCameraPage")
                        self.assertEqual(model.steps, [("stop", "viewer")])
                        self.assertEqual((viewer["CameraMode"], viewer["CameraTarget"]), (0, None))
                        self.assertNotIn("viewer", model.native_cameras)

    def test_camera_menu_public_filter_never_starts_on_private_or_invalid_target(self):
        cases = ({"InspectionPrivacyActive": True}, {"alive": False},
                 {"exists": False}, {"spawned": False}, {"PlayerListUpdatePending": True})
        for path in PATHS:
            for changes in cases:
                with self.subTest(source=path.name, target=changes):
                    model = CameraResetEvaluator(path.read_text(encoding="utf-8"))
                    viewer = model.add("viewer", CameraMode=2, CameraTarget="target",
                                       CameraCursor=2, CameraTargets=["target"])
                    model.add("target", **changes)
                    model.native_cameras["viewer"] = "target"
                    model.route("viewer", "ApplyCameraPage")
                    self.assertEqual(viewer["CameraTargets"], [])
                    self.assertEqual((viewer["CameraMode"], viewer["CameraTarget"]), (0, None))
                    self.assertEqual(model.steps, [("stop", "viewer")])
                    self.assertNotIn("viewer", model.native_cameras)

    def test_camera_menu_reapply_keeps_two_viewers_independent(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.add("target")
                for owner in ("viewer", "other"):
                    model.add(owner, CameraMode=0, CameraTarget=None,
                              CameraCursor=2, CameraTargets=["target"])
                    model.route(owner, "ApplyCameraPage")
                self.assertEqual(model.native_cameras, {"viewer": "target", "other": "target"})
                model.native_cameras.pop("viewer")
                for owner, unchanged in (("viewer", "other"), ("other", "viewer")):
                    model.steps.clear()
                    model.route(owner, "ApplyCameraPage")
                    self.assertEqual(model.steps, [("stop", owner), ("start", owner)])
                    self.assertEqual(model.native_cameras[unchanged], "target")
                    self.assertIsNone(model.globals["CameraPlayer"])


if __name__ == "__main__":
    unittest.main()
