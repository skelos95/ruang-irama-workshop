"""Execute menu navigation and Vision audiences from the Workshop source.

Native rendering and aim selection are recorded/stubbed; these tests check owned
handle lifetime and audience membership, not actual Workshop server timings.
"""
from __future__ import annotations

import operator
import re
import unittest

from tools import check_clipboard_import as clipboard
from tools import validate_workshop as validator
from tests.test_dummy_spawn_retry import SpawnExpression
from tests.test_roster_rejoin_regressions import SOURCES


class MenuLoadEvaluator:
    def __init__(self, source):
        if re.search(r"(?m)^regola\(", source):
            parts = re.split(r'("(?:\\.|[^"\\])*")', source)
            for index in range(0, len(parts), 2):
                for original, translated in clipboard.ITALIAN_TO_ENGLISH_TOKENS:
                    parts[index] = clipboard._replace_token(parts[index], original, translated)
            source = "".join(parts)
        self.rules = validator.extract_rules(source)
        self.players = {}
        self.globals = {"HumanPlayers": [], "MenuHudIds": [], "InspectionTextIds": [],
                        "LuckVisionViewers": [], "TemporaryTextOwners": [None] * 24,
                        "TemporaryEffectHudIds": [0] * 24, "TemporaryTravelTextIds": [0] * 24,
                        "TemporaryVisionTextIds": [0] * 24}
        self.event_player = None
        self.element = None
        self.last_text = None
        self.next_handle = 100
        self.created_huds = []
        self.destroyed_huds = []
        self.created_world = []
        self.destroyed_world = []
        self.nameplate_hides = []
        self.hud_bodies = {}
        self.literals = {}
        self.expressions = {}
        self.now = 0.0
        self.stub_aim = True
        self.filter_builds = 0

    def rule(self, prefix):
        return next(rule for rule in self.rules if rule.name.startswith(prefix + " -"))

    def add(self, name, **changes):
        state = dict(IsHuman=True, LuckPrivacyActive=False, alive=True, exists=True,
                     dummy=False, IsAutomaticBot=False, TravelCursor=0,
                     MenuHud=None, InspectionText=None,
                     TravelText=None, LuckVisionText=None,
                     NameplatesDisabled=False, CrouchTravelActive=True,
                     TravelTargetCandidate=None, InspectionActive=False,
                     TravelTextTarget=None, InspectionTarget=None,
                     InspectionTargetCandidate=None, NextTargetTextTime=0,
                     spawned=True, InspectionPrivacyActive=False,
                     PlayerListUpdatePending=False)
        state.update(changes)
        self.players[name] = state
        if state["IsHuman"]:
            self.globals["HumanPlayers"].append(name)
            self.globals["MenuHudIds"].append(0)
            self.globals["InspectionTextIds"].append(0)
        return state

    def resolve(self, name):
        values = {"True": True, "False": False, "Null": None, "EmptyArray": [],
                  "AllTeams": "AllTeams", "EventPlayer": self.event_player,
                  "CurrentArrayElement": self.element, "LastTextID": self.last_text,
                  "IsHuman": "IsHuman", "LuckPrivacyActive": "LuckPrivacyActive",
                  "NameplatesDisabled": "NameplatesDisabled",
                  "Melee": "Melee", "TotalTimeElapsed": self.now,
                  "IsAutomaticBot": "IsAutomaticBot", "InspectionPrivacyActive": "InspectionPrivacyActive",
                  "PlayerListUpdatePending": "PlayerListUpdatePending"}
        if name in ("Crouch", "PrimaryFire", "SecondaryFire", "Interact", "Reload", "Melee", "Ability1", "Ability2", "Jump"):
            return name
        if name in values: return values[name]
        if name in self.literals: return self.literals[name]
        if name.startswith("EventPlayer."):
            return self.players[self.event_player].get(name.split(".", 1)[1], False)
        if name.startswith("Global."): return self.globals[name.split(".", 1)[1]]
        raise AssertionError(f"unsupported menu value {name}")

    def evaluate(self, expression):
        def literal(match):
            key = f"_literal{len(self.literals)}"
            self.literals[key] = match[0][1:-1].replace(r"\n", "\n").replace(r'\"', '"')
            return key
        if expression not in self.expressions:
            packed = re.sub(r'"(?:\\.|[^"\\])*"', literal, expression)
            packed = re.sub(r"\s+", "", packed)
            packed = re.sub(r"((?:Global|EventPlayer)\.\w+)\[([^\]]+)\]", r"At(\1,\2)", packed)
            self.expressions[expression] = SpawnExpression(packed).tree
        operations = {"+": operator.add, "-": operator.sub, "%": operator.mod,
                      "/": operator.truediv,
                      "==": operator.eq, "!=": operator.ne, ">": operator.gt,
                      "<": operator.lt, ">=": operator.ge, "<=": operator.le}

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
            if name == "IsTrueForAny":
                previous = self.element
                try:
                    for self.element in visit(args[0]):
                        if visit(args[1]):
                            return True
                    return False
                finally:
                    self.element = previous
            if name == "FilteredArray":
                self.filter_builds += 1
                previous = self.element
                result = []
                for self.element in visit(args[0]):
                    if visit(args[1]): result.append(self.element)
                self.element = previous
                return result
            if name == "SortedArray":
                previous = self.element
                ranked = []
                for index, self.element in enumerate(visit(args[0])):
                    ranked.append((visit(args[1]), index, self.element))
                self.element = previous
                return [element for _, _, element in sorted(ranked)]
            return self.call(name, [visit(arg) for arg in args])
        return visit(self.expressions[expression])

    def call(self, name, args):
        if name == "AllPlayers": return [p for p, s in self.players.items() if s["exists"]]
        if name == "CountOf": return len(args[0])
        if name == "ArrayContains": return args[1] in args[0]
        if name == "IndexOfArrayValue": return args[0].index(args[1]) if args[1] in args[0] else -1
        if name == "PlayerVariable": return self.players.get(args[0], {}).get(args[1], False)
        if name == "At": return args[0][int(args[1])]
        if name in ("IsAlive", "EntityExists", "IsDummyBot", "HasSpawned"):
            key = {"IsAlive": "alive", "EntityExists": "exists", "IsDummyBot": "dummy", "HasSpawned": "spawned"}[name]
            return self.players.get(args[0], {}).get(key, False)
        if name == "CustomString":
            values = [int(value) if isinstance(value, float) and value.is_integer() else value
                      for value in args[1:]]
            return args[0].format(*values)
        if name in ("Button", "InputBindingString"): return args[0]
        if name == "IsButtonHeld": return False
        raise AssertionError(f"unsupported menu call {name}")

    def assign(self, target, value):
        indexed = re.fullmatch(r"Global\.(\w+)\[(.+)\]", target)
        if indexed:
            self.globals[indexed[1]][int(self.evaluate(indexed[2]))] = value
        elif target.startswith("Event Player."):
            self.players[self.event_player][target.split(".", 1)[1]] = value
        else:
            self.globals[target.split(".", 1)[1]] = value

    def execute(self, actions):
        actions = re.sub(r'(?m)^\s*"(?:\\.|[^"\\])*"\s*$', "", actions)
        frames, active = [], True
        for statement in validator.split_top_level(actions, ";"):
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
            elif statement == "End":
                active = frames.pop()[0]
            elif active:
                if statement == "Abort": return
                if statement.startswith("Abort If("):
                    if self.evaluate(statement[len("Abort If("):-1]): return
                    continue
                assignment = re.fullmatch(r"((?:Event Player|Global)\..+?)\s+(%?=)\s+(.+)", statement, re.S)
                if assignment:
                    value = self.evaluate(assignment[3])
                    if assignment[2] == "%=": value = self.evaluate(assignment[1]) % value
                    self.assign(assignment[1], value)
                    continue
                call = next(validator.iter_calls(statement + ";", statement.split("(", 1)[0]))
                name, args = statement.split("(", 1)[0], call.args
                if name == "Call Subroutine":
                    if args[0] == "TransitionMenuColor": continue  # Color animation is native.
                    if args[0] == "RefreshTravelTarget" and self.stub_aim: continue
                    rule = validator.rule_by_subroutine(self.rules, args[0])
                    self.execute(validator.rule_block(rule, "actions"))
                elif name == "Create HUD Text":
                    self.last_text = self.next_handle
                    self.next_handle += 1
                    self.created_huds.append((self.event_player, self.last_text))
                    self.hud_bodies[self.last_text] = args[3]
                elif name == "Destroy HUD Text":
                    self.destroyed_huds.append(self.evaluate(args[0]))
                elif name == "Create In-World Text":
                    self.last_text = self.next_handle
                    self.next_handle += 1
                    self.created_world.append(self.last_text)
                elif name == "Disable Nameplates":
                    self.nameplate_hides.append(self.event_player)
                elif name == "Destroy In-World Text":
                    self.destroyed_world.append(self.evaluate(args[0]))
                elif name in ("Enable Nameplates", "Allow Button"):
                    pass
                else:
                    raise AssertionError(f"unsupported menu action {name}")

    def run(self, prefix, owner):
        self.event_player = owner
        self.execute(validator.rule_block(self.rule(prefix), "actions"))

    def cache_tick(self):
        actions = validator.rule_block(self.rule("04g"), "actions")
        start = actions.index("Global.PlayerListSnapshot =")
        end = actions.index("For Global Variable(", start)
        self.execute(actions[start:end])

    def audience(self, owner):
        self.event_player = owner
        create = next(validator.iter_calls(self.rule("18i").body, "Create In-World Text"))
        return self.evaluate(create.args[0])

    def conditions(self, prefix, owner):
        self.event_player = owner
        return all(self.evaluate(item.strip()) for item in
                   validator.rule_block(self.rule(prefix), "conditions").split(";") if item.strip())


class MenuLoadRegressionTests(unittest.TestCase):
    def models(self):
        for path, _, _ in SOURCES:
            yield path.name, MenuLoadEvaluator(path.read_text(encoding="utf-8"))

    def test_twelve_players_keep_one_menu_handle_while_navigating_all_five_pages(self):
        for name, model in self.models():
            with self.subTest(source=name):
                owners = [f"player-{index}" for index in range(12)]
                for owner in owners:
                    model.add(owner)
                    model.run("91g", owner)
                handles = {owner: model.players[owner]["MenuHud"] for owner in owners}
                for step in range(50):
                    for index, owner in enumerate(owners):
                        model.players[owner]["TravelCommand"] = 1 if index % 2 == 0 else 2
                        model.run("19c", owner)
                        self.assertEqual(model.players[owner]["TravelCursor"],
                                         ((step + 1) * (1 if index % 2 == 0 else -1)) % 5)
                        self.assertEqual(model.players[owner]["MenuHud"], handles[owner])
                self.assertEqual(len(model.created_huds), 12)
                self.assertEqual(model.destroyed_huds, [])
                model.run("90", owners[0])
                self.assertEqual(model.destroyed_huds, [handles[owners[0]]])
                self.assertEqual(model.globals["MenuHudIds"][1:], [handles[p] for p in owners[1:]])

    def test_existing_teleport_hud_keeps_live_page_and_target_text(self):
        for name, model in self.models():
            with self.subTest(source=name):
                player = model.add("viewer")
                model.run("91g", "viewer")
                expression = model.hud_bodies[player["MenuHud"]]
                player["TravelCursor"] = 2
                player["TravelTargetCandidate"] = "alice"
                self.assertIn("3/5", model.evaluate(expression))
                self.assertIn("alice", model.evaluate(expression))
                player["TravelCursor"] = 3
                player["TravelTargetCandidate"] = "bob"
                self.assertIn("4/5", model.evaluate(expression))
                self.assertIn("bob", model.evaluate(expression))
                self.assertNotIn("alice", model.evaluate(expression))

    def test_removed_forward_cursor_normalizes_before_the_five_page_hud_is_created(self):
        for path, _, _ in SOURCES:
            source = path.read_text(encoding="utf-8")
            for cursor in (5, 6, 9, 10, 25):
                with self.subTest(source=path.name, cursor=cursor):
                    model = MenuLoadEvaluator(source)
                    player = model.add("viewer", TravelCursor=cursor)
                    model.run("91g", "viewer")
                    self.assertEqual(player["TravelCursor"], cursor % 5)
                    body = model.evaluate(model.hud_bodies[player["MenuHud"]])
                    self.assertIn(f"{cursor % 5 + 1}/5", body)
                    self.assertNotIn("/6", body)
                    self.assertEqual(len(model.created_huds), 1)

    def test_vision_cache_is_shared_but_audiences_exclude_self_and_inactive_players(self):
        for name, model in self.models():
            with self.subTest(source=name):
                model.add("alice", LuckPrivacyActive=True)
                model.add("bob", LuckPrivacyActive=True)
                model.add("inactive")
                model.add("dummy", IsHuman=False, dummy=True, LuckPrivacyActive=True)
                model.cache_tick()
                self.assertEqual(model.globals["LuckVisionViewers"], ["alice", "bob"])
                self.assertEqual(model.audience("alice"), ["bob"])
                self.assertEqual(model.audience("bob"), ["alice"])
                self.assertEqual(model.audience("dummy"), ["alice", "bob"])
                self.assertTrue(model.conditions("18i", "dummy"))
                actions = validator.rule_block(model.rule("04g"), "actions")
                self.assertEqual(actions.count("Global.LuckVisionViewers = Filtered Array"), 1)
                self.assertLess(actions.index("Global.LuckVisionViewers ="), actions.index("For Global Variable("))
                for prefix in ("18i", "18j"):
                    self.assertNotIn("Filtered Array(All Players", model.rule(prefix).body)

    def test_idle_vision_builds_no_filtered_arrays_and_clears_last_viewer_once(self):
        for name, model in self.models():
            with self.subTest(source=name):
                viewer = model.add("viewer")
                model.add("dummy", IsHuman=False, dummy=True)
                initial = model.globals["LuckVisionViewers"]
                for _ in range(40):
                    model.cache_tick()
                self.assertEqual(model.filter_builds, 0)
                self.assertIs(model.globals["LuckVisionViewers"], initial)
                viewer["LuckPrivacyActive"] = True
                model.cache_tick()
                self.assertEqual(model.globals["LuckVisionViewers"], ["viewer"])
                self.assertEqual(model.filter_builds, 1)
                viewer["LuckPrivacyActive"] = False
                model.cache_tick()
                cleared = model.globals["LuckVisionViewers"]
                self.assertEqual(cleared, [])
                for _ in range(40):
                    model.cache_tick()
                self.assertIs(model.globals["LuckVisionViewers"], cleared)
                self.assertEqual(model.filter_builds, 1)
                viewer["LuckPrivacyActive"] = True
                model.cache_tick()
                viewer["exists"] = False
                model.cache_tick()
                self.assertEqual(model.globals["LuckVisionViewers"], [])

    def test_vision_revocation_and_departure_apply_before_next_cache_tick(self):
        for name, model in self.models():
            with self.subTest(source=name):
                model.add("target", LuckVisionText=15)
                model.add("viewer", LuckPrivacyActive=True)
                model.cache_tick()
                self.assertEqual(model.audience("target"), ["viewer"])
                for changes in ({"LuckPrivacyActive": False}, {"IsHuman": False}, {"exists": False}):
                    model.players["viewer"].update(LuckPrivacyActive=True, IsHuman=True, exists=True)
                    model.players["viewer"].update(changes)
                    self.assertEqual(model.audience("target"), [])
                    self.assertTrue(model.conditions("18j", "target"))

    def test_vision_cache_replaces_departed_identities_during_repeated_joins(self):
        for name, model in self.models():
            with self.subTest(source=name):
                model.add("target", IsHuman=False, dummy=True)
                previous = None
                for index in range(100):
                    if previous: model.players[previous]["exists"] = False
                    viewer = f"viewer-{index}"
                    model.add(viewer, LuckPrivacyActive=True)
                    model.cache_tick()
                    self.assertEqual(model.globals["LuckVisionViewers"], [viewer])
                    self.assertEqual(model.audience("target"), [viewer])
                    previous = viewer

    def test_nameplates_hide_once_per_viewer_and_newcomers_inherit_both_viewer_modes(self):
        for name, model in self.models():
            with self.subTest(source=name):
                model.add("teleport", TravelTargetCandidate="target")
                model.add("target")
                model.add("inspect", InspectionActive=True, NameplatesDisabled=True)
                model.add("normal")
                model.run("19d", "teleport")
                for _ in range(20):
                    model.now += 0.05
                    # A stable selection does not recreate its current label.
                    self.assertFalse(model.conditions("19d", "teleport"))
                self.assertEqual(model.nameplate_hides, ["teleport"])
                self.assertEqual(model.destroyed_world, model.created_world[:-1])
                self.assertEqual(model.globals["TemporaryTextOwners"].count("teleport"), 1)
                slot = model.globals["TemporaryTextOwners"].index("teleport")
                self.assertEqual(model.globals["TemporaryTravelTextIds"][slot], model.created_world[-1])
                model.event_player = "newcomer"
                for prefix in ("02", "92"):
                    call = next(validator.iter_calls(model.rule(prefix).body, "Disable Nameplates"))
                    self.assertEqual(model.evaluate(call.args[1]), ["teleport", "inspect"])


if __name__ == "__main__":
    unittest.main()
