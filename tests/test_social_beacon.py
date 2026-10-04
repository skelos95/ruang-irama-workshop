"""Execute the beacon's actual ownership, waypoints and visual expressions.

Native text/effect creation and objective queries are controlled inputs. These
tests cover script bookkeeping and geometry, not the client's Light Shaft art,
glyph dimensions, custom icon rendering or the look of native effect presets.
"""

import math
import operator
import re
import unittest

from tools import validate_workshop as validator
from tests.test_audit_lifecycle import AuditExpression, AuditLifecycleEvaluator, statements
from tests.test_fly_motion import Vector
from tests.test_roster_rejoin_regressions import SOURCES


NATIVE_RGB = {
    "White": (255, 255, 255), "Aqua": (0, 234, 234), "Black": (0, 0, 0),
    "Blue": (39, 170, 255), "Gray": (127, 127, 127), "Green": (69, 255, 87),
    "Lime Green": (160, 232, 27), "Orange": (236, 153, 0),
    "Purple": (161, 73, 197), "Red": (200, 0, 19), "Rose": (255, 50, 145),
    "Sky Blue": (108, 190, 244), "Turquoise": (0, 230, 151),
    "Violet": (100, 50, 255), "Yellow": (255, 255, 0),
}


class SocialBeaconEvaluator(AuditLifecycleEvaluator):
    ARRAY_NAMES = ("PemilikIkonPilar", "TeksIkonPilar", "AwalIkonPilar",
                   "TujuanIkonPilar", "WaktuIkonPilar")

    def __init__(self, source):
        super().__init__(source)
        self.objective = Vector(10, 0, 20)
        self.host = "host"
        self.sample = 0
        self.random_calls = 0
        self.texts = {}
        self.next_text = 1000
        self.native_names = {re.sub(r"\s+", "", name): name for name in NATIVE_RGB}
        self.native_names.update(Bianco="White", Grigio="Gray")
        self.globals.update(IndeksIkonPilar=0, DaftarIkon=[""] + [f"glyph-{i}" for i in range(1, 21)])
        for name in self.ARRAY_NAMES + ("DaftarWarnaPilar",):
            init = re.search(rf"Global\.{name} = ([^;]+);", self.initializers)
            if init is None:
                raise AssertionError(f"missing beacon initializer: {name}")
            self.globals[name] = self.evaluate(init[1])
        self.effect = next(call for rule in self.rules
                           for call in validator.iter_calls(rule.body, "Create Effect")
                           if call.args[1] == "Light Shaft")

    def add(self, identity, **changes):
        self.join(identity)
        defaults = dict(Manusia=True, IndeksIkon=1, IndeksWarna=0,
                        PembaruanDaftarTertunda=False, PindahTimDiproses=False,
                        WarnaNama=(255, 255, 255, 255), exists=True)
        defaults.update(changes)
        self.players[identity].update(defaults)
        return self.players[identity]

    def resolve(self, name):
        if name in self.native_names:
            return self.native_names[name]
        if name == "HostPlayer": return self.host
        if name == "ObjectiveIndex": return 0
        if name == "LastTextID": return self.created[-1] if self.created else 0
        if name in {"IndeksIkon", "IndeksWarna", "UrutanHUD", "Manusia",
                    "PembaruanDaftarTertunda", "PindahTimDiproses", "WarnaNama"}:
            return name
        return super().resolve(name)

    def call(self, name, args):
        if name == "Vector": return Vector(*args)
        if name == "FirstOf": return args[0][0] if args[0] else None
        if name == "Color": return args[0]
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
            if token.startswith("Create In-World Text("):
                call = next(validator.iter_calls(token, "Create In-World Text"))
                # Evaluate Once freezes each native visual's slot at creation.
                index = int(self.globals["IndeksIkonPilar"])
                args = tuple(arg.replace("Evaluate Once(Global.IndeksIkonPilar)", str(index)) for arg in call.args)
                handle = self.next_text
                self.next_text += 1
                self.created.append(handle)
                self.texts[handle] = args
            elif token.startswith("Destroy In-World Text("):
                handle = self.evaluate(token[len("Destroy In-World Text("):-1])
                self.destroyed.append(handle)
                del self.texts[handle]
            elif super().execute([node]):
                return True
        return False

    def run(self, routine="PerbaruiPilarSosial", now=None):
        if now is not None: self.now = now
        rule = validator.rule_by_subroutine(self.rules, routine)
        self.execute(statements(validator.rule_block(rule, "actions")))

    def visual(self, owner):
        slot = self.globals["PemilikIkonPilar"].index(owner)
        return self.texts[self.globals["TeksIkonPilar"][slot]]

    def cleanup_beacon(self, identity, routine):
        self.event_player = identity
        rule = validator.rule_by_subroutine(self.rules, routine)
        actions = validator.rule_block(rule, "actions")
        if "Call Subroutine(BersihkanIkonPilar);" not in actions:
            raise AssertionError(f"missing beacon cleanup hook: {routine}")
        self.run("BersihkanIkonPilar")


class SocialBeaconTests(unittest.TestCase):
    def models(self):
        for path, _, _ in SOURCES:
            yield path.name, SocialBeaconEvaluator(path.read_text(encoding="utf-8"))

    def test_one_native_shaft_reevaluates_objective_radius_visibility_and_host_palette(self):
        for path, _, _ in SOURCES:
            source = path.read_text(encoding="utf-8")
            model = SocialBeaconEvaluator(source)
            with self.subTest(source=path.name):
                effects = [call for rule in model.rules for call in validator.iter_calls(rule.body, "Create Effect")
                           if call.args[1] == "Light Shaft"]
                self.assertEqual(len(effects), 1)
                self.assertEqual(model.effect.args[5], "Visible To Position Radius and Color")
                self.assertNotIn("Custom Color", model.effect.args[2])
                self.assertEqual(model.evaluate(model.effect.args[0]), [])
                for count in range(1, 13):
                    identity = "host" if count == 1 else f"human-{count}"
                    model.add(identity)
                    self.assertEqual(model.evaluate(model.effect.args[4]), 0.5 * count)
                    self.assertEqual(len(model.evaluate(model.effect.args[0])), count)
                for index, preset in enumerate(model.globals["DaftarWarnaPilar"]):
                    model.players["host"]["IndeksWarna"] = index
                    self.assertEqual(model.evaluate(model.effect.args[2]), preset)
                model.host = "absent-host"
                self.assertEqual(model.evaluate(model.effect.args[2]), "White")
                model.objective = Vector(0, 0, 0)
                self.assertEqual(model.evaluate(model.effect.args[0]), [])
                self.assertEqual(model.evaluate(model.effect.args[3]), model.objective)

    def test_all_forty_native_presets_are_the_nearest_declared_name_rgb(self):
        for source, model in self.models():
            with self.subTest(source=source):
                rgb_init = re.search(r"Global\.DaftarWarnaRGB = (Array\([^;]+\));", model.initializers)
                colors = model.evaluate(rgb_init[1])
                self.assertEqual(len(colors), 40)
                self.assertEqual(len(model.globals["DaftarWarnaPilar"]), 40)
                for rgb, actual in zip(colors, model.globals["DaftarWarnaPilar"]):
                    channels = (rgb.x, rgb.y, rgb.z)
                    distance = lambda native: sum((a - b) ** 2 for a, b in zip(channels, native))
                    self.assertEqual(distance(NATIVE_RGB[actual]), min(map(distance, NATIVE_RGB.values())))

    def test_twelve_glyph_handles_bind_distinct_owners_and_update_selection_and_rgb(self):
        for source, model in self.models():
            with self.subTest(source=source):
                for slot in range(12):
                    model.add(f"human-{slot}", IndeksIkon=slot + 1, WarnaNama=(slot, 90, 180, 255))
                model.run(now=100)
                self.assertEqual(len(model.created), 12)
                self.assertEqual(len(model.texts), 12)
                self.assertEqual(model.globals["PemilikIkonPilar"], [f"human-{i}" for i in range(12)])
                for slot in range(12):
                    visual = model.visual(f"human-{slot}")
                    self.assertNotIn("Custom String", visual[1])
                    self.assertNotIn("NamaTampilan", visual[1])
                    self.assertEqual(model.evaluate(visual[1]), f"glyph-{slot + 1}")
                    self.assertEqual(model.evaluate(visual[6]), (slot, 90, 180, 255))
                    self.assertEqual(len(model.evaluate(visual[0])), 12)
                model.globals["IndeksIkonPilar"] = 11
                state = model.players["human-0"]
                state.update(IndeksIkon=19, WarnaNama=(1, 2, 3, 255))
                visual = model.visual("human-0")
                self.assertEqual(model.evaluate(visual[1]), "glyph-19")
                self.assertEqual(model.evaluate(visual[6]), (1, 2, 3, 255))
                model.run(now=101)
                self.assertEqual(len(model.created), 12)

    def test_nonhuman_no_icon_and_quarantined_humans_never_allocate(self):
        cases = ({"Manusia": False}, {"IndeksIkon": 0},
                 {"PembaruanDaftarTertunda": True}, {"PindahTimDiproses": True}, {"exists": False})
        for path, _, _ in SOURCES:
            for changes in cases:
                with self.subTest(source=path.name, player=changes):
                    model = SocialBeaconEvaluator(path.read_text(encoding="utf-8"))
                    model.add("human", **changes)
                    model.run(now=100)
                    self.assertEqual(model.created, [])
                    self.assertEqual(model.globals["PemilikIkonPilar"], [None] * 12)
            model = SocialBeaconEvaluator(path.read_text(encoding="utf-8"))
            model.add("human")
            model.objective = Vector(0, 0, 0)
            model.run(now=100)
            self.assertEqual(model.created, [])

    def test_disabled_icon_hides_immediately_then_destroys_once_and_can_return(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("human")
                model.run(now=100)
                visual = model.visual("human")
                handle = model.created[-1]
                state["IndeksIkon"] = 0
                self.assertEqual(model.evaluate(visual[0]), [])
                model.run(now=101)
                model.run(now=102)
                self.assertEqual(model.destroyed, [handle])
                self.assertEqual(model.texts, {})
                state["IndeksIkon"] = 2
                model.run(now=103)
                self.assertEqual(len(model.created), 2)
                self.assertEqual(model.evaluate(model.visual("human")[1]), "glyph-2")

    def test_leave_and_team_cleanup_do_not_inherit_handles_or_grow_slot_arrays(self):
        for source, model in self.models():
            with self.subTest(source=source):
                for turn in range(100):
                    identity = f"human-{turn}"
                    model.add(identity)
                    model.run(now=100 + turn)
                    handle = model.created[-1]
                    model.players[identity]["exists"] = False
                    model.cleanup_beacon(identity, "TenangkanPemain" if turn % 2 else "BersihkanPemain")
                    model.cleanup_beacon(identity, "BersihkanPemain")
                    self.assertEqual(model.destroyed.count(handle), 1)
                    model.remove(identity)
                    self.assertEqual(model.texts, {})
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
                self.assertEqual(model.globals["PemilikIkonPilar"][0], "replacement")
                self.assertNotEqual(model.globals["TeksIkonPilar"][0], old_handle)

    def test_stored_waypoints_interpolate_smoothly_and_clamp_after_radius_shrinks(self):
        for source, model in self.models():
            with self.subTest(source=source):
                for slot in range(12): model.add(f"human-{slot}")
                model.run(now=100)
                self.assertEqual(model.random_calls, 72)
                visual = model.visual("human-0")
                start, target = model.globals["AwalIkonPilar"][0], model.globals["TujuanIkonPilar"][0]
                for fraction in (0, 0.2, 0.5, 0.8, 1):
                    model.now = 100 + 3 * fraction
                    actual = model.evaluate(visual[2]) - model.objective
                    expected = start + (target - start) * fraction
                    self.assertAlmostEqual((actual - expected).magnitude(), 0, places=8)
                    self.assertLessEqual(math.hypot(actual.x, actual.z), 6 * 0.85 + 1e-8)
                    self.assertTrue(0.5 <= actual.y <= 3)
                for now in (100, 101, 102): model.run(now=now)
                self.assertEqual(model.random_calls, 72)
                model.run(now=103)
                self.assertEqual(model.random_calls, 108)
                for identity in list(model.globals["PemainManusia"])[1:]: model.remove(identity)
                for now in (103, 103.5, 104, 104.5, 106):
                    model.now = now
                    actual = model.evaluate(visual[2]) - model.objective
                    self.assertLessEqual(math.hypot(actual.x, actual.z), 0.5 * 0.85 + 1e-8)
                    self.assertTrue(0.5 <= actual.y <= 3)
                self.assertEqual(model.random_calls, 108)


if __name__ == "__main__":
    unittest.main()
