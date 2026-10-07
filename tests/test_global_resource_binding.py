"""Reevaluate persistent resource arguments from the actual compiled artifact.

Evaluate Once is captured when a resource is installed; other player data stays
live. This verifies generated expression ownership, not native rendering or
whether the Overwatch team-change crash is resolved.
"""
from __future__ import annotations

import operator
import re
import unittest
from pathlib import Path

from tests.test_dummy_spawn_retry import SpawnExpression
from tests.test_fly_motion import Vector
from tools import validate_global_runtime as runtime
from tools import validate_workshop as semantic


ROOT = Path(__file__).resolve().parents[1]


class ResourceExpressions:
    """Strict source-expression evaluator with installation-time captures."""
    def __init__(self, text: str):
        self.rules = semantic.extract_rules(runtime.english(text))
        _, fields, _, _ = semantic.declaration_entries(runtime.english(text))
        self.fields = {item.name for item in fields}
        self.players = {}
        self.globals = {"PemainPemicu": None, "PemainAktif": None,
                        "PemainIkonPilar": None, "PemainManusia": [],
                        "JarakBidik": 25}
        self.values = {}
        self.trees = {}
        self.viewer = None
        self.objective = Vector(100, 2, 40)

    def actor(self, identity):
        self.globals["PemainPemicu"] = identity
        self.globals["PemainAktif"] = identity
        self.globals["PemainIkonPilar"] = identity

    def resolve(self, name):
        if name in self.values:
            return self.values[name]
        if name in self.fields:
            return name
        if name == "LocalPlayer":
            return self.viewer
        if name == "ObjectiveIndex":
            return 0
        if name.startswith("Global."):
            parts = name.split(".")
            value = self.globals[parts[1]]
            return self.players[value].get(parts[2], 0) if len(parts) == 3 else value
        constants = {"True": True, "False": False, "Null": None,
                     "EmptyArray": [], "White": "White", "Orange": "Orange"}
        if name in constants:
            return constants[name]
        raise AssertionError(f"unsupported resource value: {name}")

    def call(self, name, args):
        if name in ("EvaluateOnce", "UpdateEveryFrame"):
            return args[0]
        if name == "PlayerVariable":
            return self.players.get(args[0], {}).get(args[1], 0)
        if name == "Vector":
            return Vector(*args)
        if name in ("XComponentOf", "YComponentOf", "ZComponentOf"):
            return getattr(args[0], {"XComponentOf": "x", "YComponentOf": "y", "ZComponentOf": "z"}[name])
        if name == "CustomColor":
            return tuple(args)
        if name == "ObjectivePosition":
            return self.objective
        if name == "Color":
            return args[0]
        if name in ("EyePosition", "FacingDirectionOf", "PositionOf", "Health"):
            key = {"EyePosition": "eye", "FacingDirectionOf": "facing",
                   "PositionOf": "position", "Health": "health"}[name]
            return self.players.get(args[0], {}).get(key, 0)
        if name == "ArrayContains":
            return args[1] in args[0]
        if name == "CountOf":
            return len(args[0])
        if name == "At":
            return args[0][int(args[1])]
        raise AssertionError(f"unsupported resource call: {name}")

    def evaluate(self, expression):
        def literal(match):
            key = f"_literal{len(self.values)}"
            self.values[key] = match[0][1:-1]
            return key
        if expression not in self.trees:
            packed = re.sub(r'"(?:\\.|[^"\\])*"', literal, expression)
            packed = re.sub(r"\s+", "", packed)
            packed = re.sub(r"(Global\.\w+)\[([^\]]+)\]", r"At(\1,\2)", packed)
            self.trees[expression] = SpawnExpression(packed).tree
        operations = {"+": operator.add, "-": operator.sub,
                      "*": operator.mul, "/": operator.truediv,
                      "%": operator.mod, "==": operator.eq, "!=": operator.ne,
                      ">": operator.gt, "<": operator.lt,
                      ">=": operator.ge, "<=": operator.le}

        def visit(node):
            kind = node[0]
            if kind == "literal":
                return node[1]
            if kind == "name":
                return self.resolve(node[1])
            if kind == "negate":
                return -visit(node[1])
            if kind == "conditional":
                return visit(node[2] if visit(node[1]) else node[3])
            if kind == "call":
                if node[1] in ("And", "Or"):
                    return (all if node[1] == "And" else any)(bool(visit(arg)) for arg in node[2])
                return self.call(node[1], [visit(arg) for arg in node[2]])
            return operations[kind](visit(node[1]), visit(node[2]))
        return visit(self.trees[expression])

    def install(self, expression):
        captures = list(semantic.iter_calls(expression, "Evaluate Once"))
        outer = [call for call in captures if not any(
            other.start < call.start and other.end >= call.end for other in captures)]
        for call in reversed(outer):
            key = f"_capture{len(self.values)}"
            self.values[key] = self.evaluate(call.args[0])
            expression = expression[:call.start] + key + expression[call.end:]
        return expression

    def call_in(self, prefix, action):
        rule = next(item for item in self.rules if item.name.startswith(prefix + " -"))
        calls = list(semantic.iter_calls(rule.body, action))
        if len(calls) != 1:
            raise AssertionError((prefix, action, len(calls)))
        return calls[0]


class GlobalResourceBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (ROOT / "workshop/ruang_irama.it-IT.workshop").read_text(encoding="utf-8")
        cls.normalized = runtime.english(cls.text)
        if "Ongoing - Each Player" in cls.normalized:
            raise AssertionError("tests must exercise the generated global artifact")

    def model(self, count=12):
        model = ResourceExpressions(self.text)
        for index in range(count):
            owner = f"owner{index}"
            target = f"target{index}"
            model.players[owner] = {
                "WarnaNama": (index, index + 30, index + 70, 255),
                "WarnaMenu": Vector(index, index + 20, index + 40),
                "TargetKamera": target, "TargetInspeksi": target,
                "NamaTampilan": owner,
            }
            model.players[target] = {"eye": Vector(index, 5, index * 2),
                                     "facing": Vector(0, 0, 1), "health": 200}
            model.globals["PemainManusia"].append(owner)
        return model

    def test_twelve_roster_huds_keep_owner_while_name_color_updates(self):
        model = self.model()
        # The actual lowered registrar still contains the native HUD call.
        color = model.call_in("02", "Create HUD Text").args[7]
        installed = {}
        for index in range(12):
            owner = f"owner{index}"
            model.actor(owner)
            installed[owner] = model.install(color)
        for scratch in ("owner11", None, "owner0"):
            model.actor(scratch)
            for index in range(12):
                owner = f"owner{index}"
                value = (255 - index, index, 150 + index, 255)
                model.players[owner]["WarnaNama"] = value
                self.assertEqual(model.evaluate(installed[owner]), value)

    def test_two_menu_colors_remain_live_and_do_not_follow_shared_actor(self):
        model = self.model(2)
        hud = model.call_in("91a", "Create HUD Text")
        color = hud.args[8]
        installed = {}
        viewers = {}
        for owner in ("owner0", "owner1"):
            model.actor(owner)
            model.viewer = owner
            installed[owner] = model.install(color)
            viewers[owner] = model.install(hud.args[0])
        model.actor(None)
        model.players["owner0"]["WarnaMenu"] = Vector(220, 10, 30)
        model.players["owner1"]["WarnaMenu"] = Vector(15, 160, 240)
        for owner, value in (("owner0", (220, 10, 30, 255)),
                             ("owner1", (15, 160, 240, 255))):
            model.viewer = owner
            self.assertEqual(model.evaluate(viewers[owner]), owner)
            self.assertEqual(model.evaluate(installed[owner]), value)
        model.actor("owner1")
        model.viewer = "owner0"
        model.players["owner0"]["WarnaMenu"] = Vector(100, 75, 20)
        self.assertEqual(model.evaluate(installed["owner0"]), (100, 75, 20, 255))

    def test_twelve_cameras_follow_owned_targets_after_actor_changes(self):
        model = self.model()
        camera = model.call_in("93", "Start Camera")
        installed = {}
        for index in range(12):
            owner = f"owner{index}"
            model.actor(owner)
            installed[owner] = (model.install(camera.args[0]), model.install(camera.args[2]))
        model.actor(None)
        for index in range(12):
            owner = f"owner{index}"
            target = f"target{index}"
            eye = Vector(index + 30, 10, index * 3)
            facing = Vector(1, 0, 0)
            model.players[target].update(eye=eye, facing=facing)
            self.assertEqual(model.evaluate(installed[owner][0]), owner)
            self.assertEqual(model.evaluate(installed[owner][1]), eye + facing * 25)
        # A fresh identity using the same synthetic slot must not steal a capture.
        model.players["replacement"] = {"TargetKamera": "target11", "slot": 0}
        model.players["owner0"]["slot"] = 0
        model.actor("replacement")
        self.assertEqual(model.evaluate(installed["owner0"][0]), "owner0")
        self.assertEqual(model.evaluate(installed["owner0"][1]),
                         model.players["target0"]["eye"] + Vector(1, 0, 0) * 25)

    def test_inspection_label_captures_target_identity_but_tracks_target_motion(self):
        model = self.model(2)
        position = model.call_in("13", "Create In-World Text").args[2]
        model.actor("owner0")
        installed = model.install(position)
        model.players["owner0"]["TargetInspeksi"] = "target1"
        model.actor("owner1")
        model.players["target0"]["eye"] = Vector(90, 12, 3)
        self.assertEqual(model.evaluate(installed), Vector(90, 12.45, 3))

    def test_twelve_world_icons_track_owned_color_and_motion_after_shared_cursor_changes(self):
        model = self.model()
        rule = next(item for item in model.rules if item.name.startswith("89e -"))
        icon = next(semantic.iter_calls(rule.body, "Create Icon"))
        installed = {}
        for index in range(12):
            owner = f"owner{index}"
            model.actor(owner)
            model.players[owner]["PosisiIkonPilar"] = Vector(index, 1, -index)
            installed[owner] = (model.install(icon.args[1]), model.install(icon.args[4]))
        model.actor(None)
        model.objective = Vector(200, 10, -30)
        for index in range(12):
            owner = f"owner{index}"
            offset = Vector(-index, index / 2 + 0.5, index)
            color = (index, index * 2, 255 - index, 255)
            model.players[owner].update(PosisiIkonPilar=offset, WarnaNama=color)
            self.assertEqual(model.evaluate(installed[owner][0]), model.objective + offset)
            self.assertEqual(model.evaluate(installed[owner][1]), color)

    def test_missing_owner_capture_is_observable_when_actor_advances(self):
        model = self.model(2)
        color = model.call_in("02", "Create HUD Text").args[7]
        captures = list(semantic.iter_calls(color, "Evaluate Once"))
        identity = next(call for call in captures if call.args[0] in runtime.ACTORS)
        mutated = color[:identity.start] + identity.args[0] + color[identity.end:]
        model.actor("owner0")
        installed = model.install(mutated)
        model.actor("owner1")
        self.assertNotEqual(model.evaluate(installed), model.players["owner0"]["WarnaNama"])

    def test_freezing_name_color_data_is_observable_after_owner_changes_color(self):
        model = self.model(2)
        color = model.call_in("02", "Create HUD Text").args[7]
        model.actor("owner0")
        installed = model.install(f"Evaluate Once({color})")
        original = model.evaluate(installed)
        model.players["owner0"]["WarnaNama"] = (0, 0, 0, 255)
        self.assertEqual(model.evaluate(installed), original)
        self.assertNotEqual(model.evaluate(installed), model.players["owner0"]["WarnaNama"])


if __name__ == "__main__":
    unittest.main()
