"""Execute the objective icons' ownership, captured paths and expressions.

Native icon creation and objective queries are controlled inputs. These tests
cover script bookkeeping and geometry, not the client's icon dimensions or art.
"""

import math
import operator
import re
import unittest

from tools import validate_workshop as validator
from tests.test_audit_lifecycle import AuditExpression, AuditLifecycleEvaluator
from tests.test_fly_motion import Vector
from tests.test_roster_rejoin_regressions import SOURCES


def beacon_statements(source):
    """Parse exclusive native enum branches as nested If/Else source nodes."""
    tokens = [part.strip() for part in validator.mask_strings(source).split(";") if part.strip()]

    def branch(token, index):
        body, index = parse(index)
        otherwise = []
        if index < len(tokens) and tokens[index].startswith("Else If("):
            nested, index = branch(tokens[index].replace("Else If(", "If(", 1), index + 1)
            otherwise = [nested]
        elif index < len(tokens) and tokens[index] == "Else":
            otherwise, index = parse(index + 1)
        return (token, body, otherwise), index

    def parse(index):
        result = []
        while index < len(tokens):
            token = tokens[index]
            if token in ("Else", "End") or token.startswith("Else If("):
                break
            index += 1
            if token.startswith(("If(", "For Global Variable(")):
                node, index = branch(token, index)
                if index >= len(tokens) or tokens[index] != "End":
                    raise AssertionError("unterminated beacon block")
                index += 1
                result.append(node)
            else:
                result.append((token, None, None))
        return result, index

    result, consumed = parse(0)
    if consumed != len(tokens):
        raise AssertionError("unexpected beacon End/Else")
    return result


class SocialBeaconEvaluator(AuditLifecycleEvaluator):
    ARRAY_NAMES = ("ObjectiveIconOwners", "ObjectiveIconIds",
                   "ObjectiveIconTimes", "ObjectiveIconChoices")

    def __init__(self, source):
        super().__init__(source)
        self.objective = Vector(10, 0, 20)
        self.sample = 0
        self.random_calls = 0
        self.icons = {}
        self.next_entity = 1000
        self.chases = {}
        self.chase_started = []
        self.chase_stopped = []
        self.icon_choices = re.findall(r'Icon String\(([^)]+)\)',
                                      source[source.index("PlayerIcons = Array("):source.index("IconNames = Array(")])
        self.globals.update(ObjectiveIconIndex=0, PlayerIcons=[""] + [f"glyph-{i}" for i in range(1, 21)])
        for name in self.ARRAY_NAMES:
            init = re.search(rf"Global\.{name} = ([^;]+);", self.initializers)
            if init is None:
                raise AssertionError(f"missing beacon initializer: {name}")
            self.globals[name] = self.evaluate(init[1])

    def add(self, identity, **changes):
        self.join(identity)
        defaults = dict(IsHuman=True, IconIndex=1, ColorIndex=0,
                        PlayerListUpdatePending=False, TeamChangeProcessed=False,
                        NameColor=(255, 255, 255, 255), ObjectiveIconPosition=Vector(0, 0.5, 0), exists=True)
        defaults.update(changes)
        self.players[identity].update(defaults)
        return self.players[identity]

    def resolve(self, name):
        if name == "ObjectiveIndex": return 0
        if name == "LastCreatedEntity": return self.created[-1] if self.created else 0
        if name in {"IconIndex", "ColorIndex", "HudSlot", "IsHuman",
                    "PlayerListUpdatePending", "TeamChangeProcessed", "NameColor"}:
            return name
        if name == "ObjectiveIconPosition": return name
        return super().resolve(name)

    def call(self, name, args):
        if name == "PlayerVariable" and args[1] == "ObjectiveIconPosition" and args[0] in self.chases:
            start, target, when, duration = self.chases[args[0]]
            fraction = min(1, max(0, (self.now - when) / duration))
            self.players[args[0]][args[1]] = start + (target - start) * fraction
        if name == "Vector": return Vector(*args)
        if name == "FirstOf": return args[0][0] if args[0] else None
        if name == "ObjectivePosition": return self.objective
        if name == "DistanceBetween": return (args[0] - args[1]).magnitude()
        if name == "MagnitudeOf": return args[0].magnitude()
        if name == "XComponentOf": return args[0].x
        if name == "YComponentOf": return args[0].y
        if name == "ZComponentOf": return args[0].z
        if name == "Min": return min(args)
        if name == "Max": return max(args)
        if name in {"EvaluateOnce", "UpdateEveryFrame"}: return args[0]
        if name == "DirectionFromAngles":
            angle = math.radians(args[0])
            return Vector(math.sin(angle), 0, math.cos(angle))
        if name == "RandomReal":
            self.random_calls += 1
            # Deterministic native responses exercise changing nonzero directions.
            self.sample = (self.sample + 7) % 11
            return args[0] + (args[1] - args[0]) * self.sample / 10
        return super().call(name, args)

    def evaluate(self, expression):
        packed = re.sub(r"\s+", "", expression)
        while "[" in packed:
            converted = re.sub(r"([A-Za-z_][\w.]*)\[([^\[\]]+)\]", r"At(\1,\2)", packed)
            if converted == packed:
                raise AssertionError(f"unsupported array access: {expression}")
            packed = converted
        tree = AuditExpression(packed).tree
        def multiply(left, right):
            if isinstance(left, Vector) and isinstance(right, Vector):
                return Vector(left.x * right.x, left.y * right.y, left.z * right.z)
            return left * right

        operations = {"+": operator.add, "-": operator.sub, "*": multiply,
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
            if name in ("FilteredArray", "SortedArray", "MappedArray"):
                values, previous = visit(args[0]), self.current

                def key(value):
                    self.current = value
                    return visit(args[1])

                try:
                    if name == "MappedArray": return [key(value) for value in values]
                    return [value for value in values if key(value)] if name == "FilteredArray" else sorted(values, key=key)
                finally:
                    self.current = previous
            return self.call(name, [visit(arg) for arg in args])

        return visit(tree)

    def execute(self, nodes):
        for node in nodes:
            token = node[0]
            if token.startswith("Create Icon("):
                call = next(validator.iter_calls(token, "Create Icon"))
                # Freeze the owner PLAYER identity, while its animated position
                # and Name Color remain dynamically read by the native icon.
                owner = self.globals["ObjectiveIconPlayer"]
                self.globals[f"CapturedOwner{self.next_entity}"] = owner
                captured = f"Global.CapturedOwner{self.next_entity}"
                args = tuple(arg.replace("Evaluate Once(Global.ObjectiveIconPlayer)", captured) for arg in call.args)
                handle = self.next_entity
                self.next_entity += 1
                self.created.append(handle)
                self.icons[handle] = args
            elif token.startswith("Destroy Icon("):
                handle = self.evaluate(token[len("Destroy Icon("):-1])
                self.destroyed.append(handle)
                del self.icons[handle]
            elif token.startswith("Chase Player Variable Over Time("):
                call = next(validator.iter_calls(token, "Chase Player Variable Over Time"))
                owner, field = self.evaluate(call.args[0]), call.args[1]
                self.assert_chase_field(field)
                start = self.call("PlayerVariable", [owner, field])
                target, duration = self.evaluate(call.args[2]), self.evaluate(call.args[3])
                if not isinstance(start, Vector) or not isinstance(target, Vector):
                    raise AssertionError("native chase requires initialized matching Vector types")
                if call.args[4] != "None":
                    raise AssertionError("beacon must freeze destination and duration once")
                self.chases[owner] = (start, target, self.now, duration)
                self.chase_started.append(owner)
            elif token.startswith("Stop Chasing Player Variable("):
                call = next(validator.iter_calls(token, "Stop Chasing Player Variable"))
                owner, field = self.evaluate(call.args[0]), call.args[1]
                self.assert_chase_field(field)
                self.call("PlayerVariable", [owner, field])
                self.chases.pop(owner, None)
                self.chase_stopped.append(owner)
            elif super().execute([node]):
                return True
        return False

    def run(self, routine="UpdateSocialObjectiveIcons", now=None):
        if now is not None: self.now = now
        # The native engine releases player variables when an entity disappears.
        self.chases = {owner: chase for owner, chase in self.chases.items()
                       if self.players.get(owner, {}).get("exists")}
        rule = validator.rule_by_subroutine(self.rules, routine)
        self.execute(beacon_statements(validator.rule_block(rule, "actions")))

    @staticmethod
    def assert_chase_field(field):
        if field != "ObjectiveIconPosition":
            raise AssertionError(f"unexpected beacon chase field: {field}")

    def visual(self, owner):
        slot = self.globals["ObjectiveIconOwners"].index(owner)
        return self.icons[self.globals["ObjectiveIconIds"][slot]]

    def cleanup_beacon(self, identity, routine):
        self.event_player = identity
        rule = validator.rule_by_subroutine(self.rules, routine)
        actions = validator.rule_block(rule, "actions")
        if "Call Subroutine(CleanupObjectiveIcon);" not in actions:
            raise AssertionError(f"missing beacon cleanup hook: {routine}")
        self.run("CleanupObjectiveIcon")


class SocialBeaconTests(unittest.TestCase):
    def models(self):
        for path, _, _ in SOURCES:
            yield path.name, SocialBeaconEvaluator(path.read_text(encoding="utf-8"))

    def test_only_native_icons_reevaluate_objective_position_and_hide_without_objective(self):
        for source, model in self.models():
            with self.subTest(source=source):
                self.assertFalse([call for rule in model.rules
                                  for call in validator.iter_calls(rule.body, "Create Effect")])
                model.add("human")
                model.run(now=100)
                self.assertEqual(len(model.icons), 1)
                visual = model.visual("human")
                offset = model.evaluate(visual[1]) - model.objective
                model.objective = Vector(35, 7, 60)
                self.assertEqual(model.evaluate(visual[1]), model.objective + offset)
                self.assertEqual(model.evaluate(visual[0]), ["human"])
                model.objective = Vector(0, 0, 0)
                self.assertEqual(model.evaluate(visual[0]), [])

    def test_ten_metre_radius_does_not_depend_on_roster_size(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.add("human-0")
                model.run(now=100)
                visual = model.visual("human-0")
                captured = model.chases["human-0"]
                model.now = 101.5
                position = model.evaluate(visual[1])
                for slot in range(1, 12):
                    model.add(f"human-{slot}")
                    self.assertEqual(model.evaluate(visual[1]), position)
                    self.assertEqual(model.chases["human-0"], captured)
                for slot in range(1, 12):
                    model.remove(f"human-{slot}")
                    self.assertEqual(model.evaluate(visual[1]), position)
                    self.assertEqual(model.chases["human-0"], captured)
                self.assertLessEqual(math.hypot(position.x - model.objective.x,
                                               position.z - model.objective.z), 10)

    def test_twelve_native_icons_bind_distinct_owners_and_reevaluate_rgb_without_recreation(self):
        for source, model in self.models():
            with self.subTest(source=source):
                for slot in range(12):
                    model.add(f"human-{slot}", IconIndex=slot + 1, NameColor=(slot, 90, 180, 255))
                model.run(now=100)
                self.assertEqual(len(model.created), 12)
                self.assertEqual(len(model.icons), 12)
                self.assertEqual(model.globals["ObjectiveIconOwners"], [f"human-{i}" for i in range(12)])
                for slot in range(12):
                    visual = model.visual(f"human-{slot}")
                    self.assertEqual(visual[2], model.icon_choices[slot])
                    self.assertEqual(visual[3], "Visible To Position and Color")
                    self.assertEqual(visual[5], "False")
                    self.assertEqual(model.evaluate(visual[4]), (slot, 90, 180, 255))
                    self.assertEqual(len(model.evaluate(visual[0])), 12)
                model.globals["ObjectiveIconIndex"] = 11
                state = model.players["human-0"]
                state.update(NameColor=(1, 2, 3, 255))
                visual = model.visual("human-0")
                self.assertEqual(model.evaluate(visual[4]), (1, 2, 3, 255))
                model.run(now=101)
                self.assertEqual(len(model.created), 12)

    def test_all_36_selected_types_replace_one_entity_and_hide_stale_type_immediately(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("human")
                for selected, expected in enumerate(model.icon_choices, 1):
                    if selected > 1:
                        old = model.visual("human")
                        state["IconIndex"] = selected
                        self.assertEqual(model.evaluate(old[0]), [])
                    model.run(now=100 + selected)
                    self.assertEqual(len(model.icons), 1)
                    self.assertEqual(model.visual("human")[2], expected)
                    self.assertEqual(model.globals["ObjectiveIconChoices"][0], selected)
                    self.assertEqual(len(model.created), selected)
                    self.assertEqual(len(model.destroyed), selected - 1)
                    model.run(now=100 + selected)
                    self.assertEqual(len(model.created), selected)

    def test_nonhuman_no_icon_and_quarantined_humans_never_allocate(self):
        cases = ({"IsHuman": False}, {"IconIndex": 0},
                 {"PlayerListUpdatePending": True}, {"TeamChangeProcessed": True}, {"exists": False})
        for path, _, _ in SOURCES:
            visible_changes = ({"IsHuman": False, "TeamChangeProcessed": True},
                               {"exists": False}, {"IconIndex": 0})
            for changes in cases:
                with self.subTest(source=path.name, player=changes):
                    model = SocialBeaconEvaluator(path.read_text(encoding="utf-8"))
                    model.add("human", **changes)
                    model.run(now=100)
                    self.assertEqual(model.created, [])
                    self.assertEqual(model.globals["ObjectiveIconOwners"], [None] * 12)
            model = SocialBeaconEvaluator(path.read_text(encoding="utf-8"))
            model.add("human")
            model.objective = Vector(0, 0, 0)
            model.run(now=100)
            self.assertEqual(model.created, [])
            # The roster remains populated briefly during a native team-change
            # quarantine; its owned icon must hide before serial cleanup runs.
            for changes in visible_changes:
                with self.subTest(source=path.name, visible_owner=changes):
                    model = SocialBeaconEvaluator(path.read_text(encoding="utf-8"))
                    state = model.add("human")
                    model.run(now=100)
                    visual = model.visual("human")
                    self.assertTrue(model.evaluate(visual[0]))
                    state.update(changes)
                    self.assertEqual(model.evaluate(visual[0]), [])

    def test_disabled_icon_hides_immediately_then_destroys_once_and_can_return(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("human")
                model.run(now=100)
                visual = model.visual("human")
                handle = model.created[-1]
                state["IconIndex"] = 0
                self.assertEqual(model.evaluate(visual[0]), [])
                model.run(now=101)
                model.run(now=102)
                self.assertEqual(model.destroyed, [handle])
                self.assertEqual(model.icons, {})
                state["IconIndex"] = 2
                model.run(now=103)
                self.assertEqual(len(model.created), 2)
                self.assertEqual(model.visual("human")[2], model.icon_choices[1])

    def test_leave_and_team_cleanup_do_not_inherit_handles_or_grow_slot_arrays(self):
        for source, model in self.models():
            with self.subTest(source=source):
                for turn in range(100):
                    identity = f"human-{turn}"
                    model.add(identity)
                    model.run(now=100 + turn)
                    handle = model.created[-1]
                    model.players[identity]["exists"] = bool(turn % 2)
                    model.cleanup_beacon(identity, "QuiescePlayer" if turn % 2 else "CleanupPlayer")
                    model.cleanup_beacon(identity, "CleanupPlayer")
                    self.assertEqual(model.destroyed.count(handle), 1)
                    model.remove(identity)
                    model.players[identity]["exists"] = False
                    self.assertEqual(model.icons, {})
                    self.assertEqual(model.chases, {})
                    for array in model.ARRAY_NAMES:
                        self.assertEqual(len(model.globals[array]), 12)
                self.assertEqual(set(model.created), set(model.destroyed))

    def test_lost_owner_is_released_before_reusing_a_slot(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.add("departed")
                model.run(now=100)
                old_handle = model.created[-1]
                model.remove("departed")
                model.players["departed"]["exists"] = False
                model.add("replacement")
                model.run(now=101)
                self.assertEqual(model.destroyed, [old_handle])
                self.assertEqual(model.globals["ObjectiveIconOwners"][0], "replacement")
                self.assertNotEqual(model.globals["ObjectiveIconIds"][0], old_handle)

    def test_captured_waypoints_interpolate_smoothly_inside_fixed_radius(self):
        for source, model in self.models():
            with self.subTest(source=source):
                for slot in range(12): model.add(f"human-{slot}")
                model.run(now=100)
                self.assertEqual(model.random_calls, 72)
                # Samples must use the expanded area, not merely fit inside it.
                sampled_radius = max(math.hypot(point.x, point.z)
                                     for start, target, _, _ in model.chases.values()
                                     for point in (start, target))
                self.assertAlmostEqual(sampled_radius, 10, places=8)
                visual = model.visual("human-0")
                start, target, _, duration = model.chases["human-0"]
                for fraction in (0, 0.2, 0.5, 0.8, 1):
                    model.now = 100 + duration * fraction
                    actual = model.evaluate(visual[1]) - model.objective
                    expected = start + (target - start) * fraction
                    self.assertAlmostEqual((actual - expected).magnitude(), 0, places=8)
                    self.assertLessEqual(math.hypot(actual.x, actual.z), 10 + 1e-8)
                    self.assertTrue(0.5 <= actual.y <= 8)
                vertical_moves = [abs(start.y - target.y) for start, target, _, _ in model.chases.values()]
                self.assertGreater(max(vertical_moves), 6)
                for now in (100, 101, 102): model.run(now=now)
                self.assertEqual(model.random_calls, 72)
                self.assertEqual(len(model.chase_started), 12)
                model.run(now=103)
                self.assertEqual(model.random_calls, 108)
                self.assertEqual(len(model.chase_started), 24)
                for identity in list(model.globals["HumanPlayers"])[1:]: model.remove(identity)
                for now in (103, 103.5, 104, 104.5, 106):
                    model.now = now
                    actual = model.evaluate(visual[1]) - model.objective
                    self.assertLessEqual(math.hypot(actual.x, actual.z), 10 + 1e-8)
                    self.assertTrue(0.5 <= actual.y <= 8)
                self.assertEqual(model.random_calls, 108)

    def test_cleanup_stops_only_the_exact_owner_native_chase(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.add("first")
                model.add("second")
                model.run(now=100)
                second = model.chases["second"]
                model.cleanup_beacon("first", "QuiescePlayer")
                self.assertNotIn("first", model.chases)
                self.assertEqual(model.players["first"]["ObjectiveIconPosition"], Vector(0, 0.5, 0))
                self.assertEqual(model.chases["second"], second)
                self.assertEqual(model.chase_stopped, ["first"])

    def test_shifted_one_second_ticks_renew_before_completion_without_position_jumps(self):
        for source, model in self.models():
            with self.subTest(source=source):
                for slot in range(12): model.add(f"human-{slot}")
                model.run(now=100)
                for elapsed in (0.99, 1.98, 2.97, 3.96, 4.95, 5.94, 6.93, 7.92, 8.91):
                    model.now = 100 + elapsed
                    positions = {}
                    for owner, (_, _, started, duration) in model.chases.items():
                        self.assertLess(model.now - started, duration,
                                        "native path must still move before the next one-second manager tick")
                        positions[owner] = model.evaluate(model.visual(owner)[1])
                    previous_chases = len(model.chase_started)
                    model.run()
                    if len(model.chase_started) > previous_chases:
                        for owner, position in positions.items():
                            self.assertAlmostEqual((model.evaluate(model.visual(owner)[1]) - position).magnitude(),
                                                   0, places=10)
                self.assertEqual(len(model.chase_started), 36)
                self.assertEqual(model.random_calls, 144)
                self.assertEqual(len(model.created), 12)


if __name__ == "__main__":
    unittest.main()
