"""Execute the social menus and owned Aura registry at native boundaries.

These checks run the maintained source branches, not a second implementation of
the social rules. Rendering, random draws and geometry are controlled inputs;
their native appearance and cost still require the Overwatch client.
"""
from copy import deepcopy
import json
import operator
from pathlib import Path
import re
import unittest

from tools import build_global_runtime as compiler
from tools import validate_workshop as validator
from tests.test_direct_menu_toggles import DirectToggleEvaluator
from tests.test_fly_motion import Vector


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = (ROOT / "source/ruang_irama.en-US.source",
             ROOT / "tests/fixtures/semantic_reference.txt",
             ROOT / "workshop/ruang_irama.en-US.workshop")
DEFAULT = [0, 0, 0, 0, 0, True, 0, 0, 0, False, "The pages await your hand."]
CATALOGUES = ("PresenceNames", "FateNames", "WhisperNames", "AuraNames", "OmenLines")


def program(actions):
    actions = re.sub(r'(?m)^\s*"(?:\\.|[^"\\])*"\s*$', "", actions)
    tokens = [part.strip() for part in validator.split_top_level(actions, ";") if part.strip()]

    def branch(header, index):
        body, index = parse(index)
        otherwise = []
        if index < len(tokens) and tokens[index].startswith("Else If("):
            nested, index = branch(tokens[index].replace("Else If(", "If(", 1), index + 1)
            otherwise = [nested]
        elif index < len(tokens) and tokens[index] == "Else":
            otherwise, index = parse(index + 1)
        return (header, body, otherwise), index

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
                    raise AssertionError("unterminated social block")
                index += 1
                result.append(node)
            else:
                result.append((token, None, None))
        return result, index

    result, consumed = parse(0)
    if consumed != len(tokens):
        raise AssertionError("unexpected social block terminator")
    return result


class NocturneEvaluator(DirectToggleEvaluator):
    def __init__(self, source):
        super().__init__(source)
        self.source = source
        self.now = 100
        self.aim = None
        self.messages = []
        self.draws = []
        self.draw_high = False
        self.effects = {}
        self.created_effects = []
        self.destroyed_effects = []
        self.next_entity = 800
        self.capture_index = 0
        self.hud_arguments = {}
        self.destroyed_hud_text = {}
        self.trees = {}
        self.globals.update(MoonlitAuraOwners=[None] * 12, MoonlitAuraIds=[0] * 12,
                            MoonlitAuraChoices=[0] * 12, MoonlitAuraColors=[-1] * 12,
                            MoonlitAuraPlayer=None, MoonlitAuraIndex=0,
                            FateResultOwners=[None] * 12, FateResultHudIds=[0] * 12,
                            FateResultDeadlines=[0] * 12, FateResultPlayer=None, FateResultIndex=0,
                            PlayerHudSlots=[], PlayerIcons=[""] * 37,
                            GenreNames=[f"genre-{i}" for i in range(200)])
        for name in CATALOGUES:
            values = validator.array_assignment_items(source, name)
            if values is not None:
                self.globals[name] = [validator.parse_literal(next(validator.iter_calls(item, "Custom String")).args[0])
                                      for item in values]
        _, players, _, _ = validator.declaration_entries(source)
        self.fields = {entry.name for entry in players}

    def add(self, name, **changes):
        defaults = dict(NocturneState=deepcopy(DEFAULT), IsPrepared=True,
                        PlayerCycleActive=False, LastTeam=1, ColorIndex=0,
                        NameColor=(190, 210, 230, 255), position=Vector(0, 0, 0),
                        eye=Vector(0, 1.7, 0), in_view=True, los=True,
                        DisplayName=name, CustomSoundtrack=None, GenreIndex=-1,
                        MenuPage=17, MainMenuCursor=17, IconIndex=0,
                        MenuColor=Vector(10, 20, 30),
                        ControllerState=[0] * 128, ControllerTimes=[0] * 128)
        defaults.update(changes)
        state = super().add(name, **defaults)
        self.globals["PlayerHudSlots"].append(state["HudSlot"])
        return state

    def evaluate(self, expression):
        if expression not in self.trees:
            self.trees[expression] = compiler._Expression(expression).tree
        operations = {"+": operator.add, "-": operator.sub, "*": operator.mul,
                      "/": operator.truediv, "%": operator.mod, "==": operator.eq,
                      "!=": operator.ne, "<": operator.lt, ">": operator.gt,
                      "<=": operator.le, ">=": operator.ge}

        def visit(node):
            kind = node.kind
            if kind == "literal":
                return json.loads(node.value) if node.value.startswith('"') else float(node.value)
            if kind == "name":
                if node.value == "Global": return self.globals
                if node.value == "Event Player": return self.event_player
                if node.value == "Local Player": return self.event_player
                if node.value == "Current Array Element": return self.element
                if node.value == "Total Time Elapsed": return self.now
                if node.value == "Last Created Entity": return self.created_effects[-1] if self.created_effects else 0
                if node.value in self.fields: return node.value
                if node.value in ("All Teams", "Ring", "Cloud", "Barriers Do Not Block LOS", "Up"):
                    return node.value
                return self.resolve(node.value.replace(" ", ""))
            if kind == "member":
                base = visit(node.children[0])
                return base.get(node.value, 0) if isinstance(base, dict) else self.players.get(base, {}).get(node.value, 0)
            if kind == "index":
                base, index = visit(node.children[0]), int(visit(node.children[1]))
                return base[index] if isinstance(base, (list, tuple)) and 0 <= index < len(base) else 0
            if kind == "conditional": return visit(node.children[1 if visit(node.children[0]) else 2])
            if kind == "unary":
                value = visit(node.children[0])
                return not value if node.value == "!" else -value if node.value == "-" else value
            if kind == "binary": return operations[node.value](visit(node.children[0]), visit(node.children[1]))
            name = node.value.replace(" ", "")
            if name in ("And", "Or"):
                return (all if name == "And" else any)(bool(visit(child)) for child in node.children)
            if name == "FilteredArray":
                before = self.element
                result = []
                for item in visit(node.children[0]):
                    self.element = item
                    if visit(node.children[1]): result.append(item)
                self.element = before
                return result
            return self.call(name, [visit(child) for child in node.children])

        return visit(self.trees[expression])

    def call(self, name, args):
        if name == "Not": return not args[0]
        if name in ("EvaluateOnce", "UpdateEveryFrame"): return args[0]
        if name == "PlayerClosestToReticle": return self.aim
        if name == "RandomInteger":
            self.draws.append(tuple(args))
            return int(args[1] if self.draw_high else args[0])
        if name == "RandomValueInArray":
            self.draws.append((0, len(args[0]) - 1))
            return args[0][-1 if self.draw_high else 0]
        if name == "Vector": return Vector(*args)
        if name == "CustomColor": return tuple(args)
        if name in ("XComponentOf", "YComponentOf", "ZComponentOf"):
            return getattr(args[0], {"XComponentOf": "x", "YComponentOf": "y", "ZComponentOf": "z"}[name])
        if name in ("PositionOf", "EyePosition"):
            if isinstance(args[0], Vector): return args[0]
            return self.players[args[0]]["position" if name == "PositionOf" else "eye"]
        if name == "DistanceBetween":
            points = [self.players[item]["position"] if isinstance(item, str) and item in self.players else item for item in args]
            return (points[0] - points[1]).magnitude()
        if name in ("IsInViewAngle", "IsInLineOfSight"):
            return self.players.get(self.aim, {}).get("in_view" if name == "IsInViewAngle" else "los", True)
        if name == "RoundToInteger": return round(args[0])
        if name in ("IsDuplicating",): return False
        if name in ("HeroOf", "HeroIconString"): return "hero"
        return super().call(name, args)

    def assign(self, target, value):
        node = compiler._Expression(target).tree
        if node.kind == "index":
            base = self.evaluate(compiler._emit(node.children[0]))
            index = int(self.evaluate(compiler._emit(node.children[1])))
            base[index] = value
        elif node.kind == "member":
            base = self.evaluate(compiler._emit(node.children[0]))
            (base if isinstance(base, dict) else self.players[base])[node.value] = value
        else:
            raise AssertionError(f"unsupported social target: {target}")

    def capture(self, expression):
        captures = list(validator.iter_calls(expression, "Evaluate Once"))
        outer = [call for call in captures if not any(other.start < call.start and other.end >= call.end for other in captures)]
        for call in reversed(outer):
            name = f"TestCapture{self.capture_index}"
            self.capture_index += 1
            self.globals[name] = self.evaluate(call.args[0])
            expression = expression[:call.start] + "Global." + name + expression[call.end:]
        return expression

    def execute(self, actions):
        nodes = program(actions) if isinstance(actions, str) else actions
        for token, body, otherwise in nodes:
            if body is not None:
                if token.startswith("For Global Variable("):
                    call = next(validator.iter_calls(token, "For Global Variable"))
                    field, start, stop, step = call.args
                    for index in range(int(self.evaluate(start)), int(self.evaluate(stop)), int(self.evaluate(step))):
                        self.globals[field] = index
                        if self.execute(body): return True
                elif self.execute(body if self.evaluate(token[3:-1]) else otherwise): return True
                continue
            if token == "Abort": return True
            if token.startswith("Abort If("):
                if self.evaluate(token[len("Abort If("):-1]): return True
                continue
            assignment = re.fullmatch(r"((?:Event Player|Global)\..+?)\s+(=)\s+(.+)", token, re.S)
            if assignment:
                self.assign(assignment[1], self.evaluate(assignment[3]))
                continue
            name = token.split("(", 1)[0]
            call = next(validator.iter_calls(token, name))
            if name == "Call Subroutine":
                if call.args[0] == "TransitionMenuColor": continue
                rule = validator.rule_by_subroutine(self.rules, call.args[0])
                self.execute(validator.rule_block(rule, "actions"))
            elif name in ("Small Message", "Big Message"):
                self.messages.append((name, self.evaluate(call.args[0]), self.evaluate(call.args[1])))
            elif name == "Create HUD Text":
                installed = tuple(self.capture(arg) for arg in call.args)
                super().execute(token + ";")
                self.hud_arguments[self.last_text] = installed
                self.hud_bodies[self.last_text] = installed[3]
            elif name == "Destroy HUD Text":
                handle = self.evaluate(call.args[0])
                if handle in self.hud_arguments:
                    self.destroyed_hud_text[handle] = self.evaluate(self.hud_arguments[handle][3])
                super().execute(token + ";")
            elif name == "Create Effect":
                handle = self.next_entity
                self.next_entity += 1
                self.effects[handle] = tuple(self.capture(arg) for arg in call.args)
                self.created_effects.append(handle)
            elif name == "Destroy Effect":
                handle = self.evaluate(call.args[0])
                if handle not in self.effects: raise AssertionError(f"double/stale effect destruction: {handle}")
                del self.effects[handle]
                self.destroyed_effects.append(handle)
            else:
                super().execute(token + ";")
        return False

    def routine(self, name, owner=None):
        if owner is not None:
            self.event_player = owner
            self.globals["TriggerPlayer"] = owner
            self.globals["ActivePlayer"] = owner
        rule = validator.rule_by_subroutine(self.rules, name)
        self.execute(validator.rule_block(rule, "actions"))

    def apply(self, owner, page, cursor):
        state = self.players[owner]
        state["MenuPage"] = page
        state["NocturneState"][{17: 1, 18: 2, 19: 4, 20: 7}[page]] = cursor
        self.routine("ApplyNocturnePage", owner)

    def controller(self, prefix, owner):
        if "Ongoing - Each Player" not in self.source:
            self.routine("Controller" + prefix.capitalize(), owner)
            return
        self.event_player = owner
        rule = self.rule(prefix)
        conditions = validator.rule_block(rule, "conditions")
        if all(self.evaluate(condition.strip()) for condition in validator.split_top_level(conditions, ";") if condition.strip()):
            self.execute(validator.rule_block(rule, "actions"))


class NocturneSocialTests(unittest.TestCase):
    def models(self):
        for path in ARTIFACTS:
            yield path.name, NocturneEvaluator(path.read_text(encoding="utf-8"))

    def test_one_packed_state_fits_the_source_and_generated_capacity(self):
        for path in ARTIFACTS:
            source = path.read_text(encoding="utf-8")
            _, players, _, _ = validator.declaration_entries(source)
            with self.subTest(artifact=path.name):
                self.assertEqual([(item.name, item.index) for item in players if item.name == "NocturneState"],
                                 [("NocturneState", 125)])
                self.assertLessEqual(len(players), 128)
                self.assertLess(max(item.index for item in players), 128)

    def test_presence_applies_and_resets_only_its_owner(self):
        for artifact, model in self.models():
            owner = model.add("owner")
            other = model.add("other")
            before = deepcopy(other)
            for cursor in range(5):
                with self.subTest(artifact=artifact, choice=cursor):
                    model.apply("owner", 17, cursor)
                    self.assertEqual(owner["NocturneState"][0], cursor)
                    self.assertEqual(other, before)
            owner["NocturneState"][3] = 200
            owner["NocturneState"][6] = 300
            model.routine("ResetMenuPage", "owner")
            self.assertEqual(owner["NocturneState"][:2], [0, 0])
            self.assertEqual((owner["NocturneState"][3], owner["NocturneState"][6]), (200, 300))

    def test_opening_a_social_page_never_executes_its_selected_action(self):
        for artifact, model in self.models():
            for page in range(17, 21):
                owner = f"owner-{page}"
                state = model.add(owner, MainMenuCursor=page, MenuPage=-1, MenuCommand=1)
                model.event_player = owner
                model.globals.update(TriggerPlayer=owner, ActivePlayer=owner)
                before = deepcopy(state["NocturneState"])
                if "Ongoing - Each Player" in model.source:
                    rule = model.rule("10")
                else:
                    rule = validator.rule_by_subroutine(model.rules, "Controller10")
                with self.subTest(artifact=artifact, page=page):
                    model.execute(validator.rule_block(rule, "actions"))
                    self.assertEqual(state["MenuPage"], page)
                    self.assertEqual(state["NocturneState"], before)
                    self.assertEqual(model.draws, [])
                    self.assertEqual(model.messages, [])
                    self.assertEqual(model.created_effects, [])

    def test_installed_social_hud_keeps_its_page_identity_until_destroyed(self):
        titles = {17: "17 - PRESENCE", 18: "18 - FATES", 19: "19 - WHISPERS", 20: "20 - MOONLIT AURA"}
        for artifact, model in self.models():
            for page, title in titles.items():
                owner = f"owner-{page}"
                state = model.add(owner, MenuPage=page, MainMenuCursor=page)
                model.routine("DrawMenu", owner)
                handle = state["MenuHud"]
                expression = model.hud_bodies[handle]
                initial = model.evaluate(expression)
                with self.subTest(artifact=artifact, page=page):
                    self.assertEqual(initial.splitlines()[0], title)
                    for next_page in (-1, 20 if page != 20 else 17, page):
                        state["MenuPage"] = next_page
                        self.assertEqual(model.evaluate(expression), initial)
                        self.assertNotIn(handle, model.destroyed_huds)
                    model.routine("DrawMenu", owner)
                    self.assertIn(handle, model.destroyed_huds)
                    self.assertEqual(model.destroyed_hud_text[handle], initial)

    def test_reload_controller_returns_to_the_selected_main_entry_once(self):
        for artifact, model in self.models():
            for page in range(17, 21):
                owner = f"owner-{page}"
                state = model.add(owner, MenuPage=page, MainMenuCursor=page,
                                  MenuCommand=2, held={"Reload"})
                model.routine("DrawMenu", owner)
                old_handle = state["MenuHud"]
                initial = model.evaluate(model.hud_bodies[old_handle])
                start = len(model.created_huds)
                model.controller("11", owner)
                with self.subTest(artifact=artifact, page=page):
                    self.assertEqual((state["MenuPage"], state["MainMenuCursor"]), (-1, page))
                    self.assertEqual(model.destroyed_hud_text[old_handle], initial)
                    self.assertEqual(model.destroyed_huds.count(old_handle), 1)
                    self.assertEqual(model.evaluate(model.hud_bodies[state["MenuHud"]]).splitlines()[0],
                                     initial.splitlines()[0])
                    self.assertEqual(len(model.created_huds), start + 1)
                    model.controller("11", owner)
                    self.assertEqual(len(model.created_huds), start + 1)
                    state["held"].clear()
                    model.controller("05d", owner)
                    self.assertEqual(state["MenuCommand"], 0)

    def test_social_page_cursors_preferences_and_color_stay_live_after_installation(self):
        for artifact, model in self.models():
            for page, field, catalogue in ((17, 1, "PresenceNames"), (18, 2, "FateNames"),
                                            (19, 4, "WhisperNames"), (20, 7, "AuraNames")):
                owner = f"owner-{page}"
                state = model.add(owner, MenuPage=page, MainMenuCursor=page)
                model.routine("DrawMenu", owner)
                installed = model.hud_arguments[state["MenuHud"]]
                state["MenuPage"] = -1
                model.globals.update(TriggerPlayer=None, ActivePlayer=None)
                with self.subTest(artifact=artifact, page=page):
                    for cursor, label in enumerate(model.globals[catalogue]):
                        state["NocturneState"][field] = cursor
                        self.assertIn("> " + label, model.evaluate(installed[3]))
                    if page == 17:
                        for choice, label in enumerate(model.globals["PresenceNames"]):
                            state["NocturneState"][0] = choice
                            self.assertIn("NOW: " + label, model.evaluate(installed[3]))
                    elif page == 18:
                        self.assertIn("FATES: READY", model.evaluate(installed[3]))
                        state["NocturneState"][3] = model.now + 2
                        self.assertIn("FATES: RESTING 2s", model.evaluate(installed[3]))
                        model.now += 2
                        self.assertIn("FATES: READY", model.evaluate(installed[3]))
                    elif page == 19:
                        for receive in (False, True):
                            state["NocturneState"][5] = receive
                            self.assertIn("RECEIVE: " + ("ON" if receive else "OFF"), model.evaluate(installed[3]))
                    else:
                        for choice, label in enumerate(model.globals["AuraNames"][:4]):
                            state["NocturneState"][8] = choice
                            self.assertIn("NOW: " + label, model.evaluate(installed[3]))
                        for hidden in (True, False):
                            state["NocturneState"][9] = hidden
                            self.assertIn("HIDE OTHERS: " + ("ON" if hidden else "OFF"), model.evaluate(installed[3]))
                    state["MenuColor"] = Vector(70, 140, 210)
                    self.assertEqual(model.evaluate(installed[8]), (70, 140, 210, 255))

    def test_unfrozen_page_mutation_reproduces_the_aura_flash_on_reload(self):
        for path in ARTIFACTS:
            source = path.read_text(encoding="utf-8")
            rules = validator.extract_rules(source)
            renderer = validator.rule_by_subroutine(rules, "DrawNocturneMenu")
            body = renderer.body
            # Removing only the page snapshots restores the pre-fix renderer.
            for call in reversed(list(validator.iter_calls(body, "Evaluate Once"))):
                if "MenuPage" in call.args[0]:
                    body = body[:call.start] + call.args[0] + body[call.end:]
            model = NocturneEvaluator(source[:renderer.start] + body + source[renderer.end:])
            state = model.add("owner", MenuPage=17)
            model.routine("DrawMenu", "owner")
            expression = model.hud_bodies[state["MenuHud"]]
            self.assertEqual(model.evaluate(expression).splitlines()[0], "17 - PRESENCE")
            state["MenuPage"] = -1
            with self.subTest(artifact=path.name):
                self.assertEqual(model.evaluate(expression).splitlines()[0], "20 - MOONLIT AURA")

    def test_fates_uses_native_draw_bounds_and_respects_cooldown_after_reset(self):
        for artifact, model in self.models():
            owner = model.add("owner")
            for cursor, bounds in enumerate(((0, 1), (1, 6), (1, 20), (1, 100), (0, 5))):
                for high in (False, True):
                    with self.subTest(artifact=artifact, cursor=cursor, high=high):
                        model.now += 10
                        model.draw_high = high
                        model.apply("owner", 18, cursor)
                        self.assertEqual(model.draws[-1], bounds)
                        self.assertEqual(owner["NocturneState"][3], model.now + 5)
                        self.assertNotEqual(owner["NocturneState"][10], DEFAULT[10])
                        count = len(model.draws)
                        model.routine("ResetMenuPage", "owner")
                        self.assertEqual(owner["NocturneState"][10], DEFAULT[10])
                        self.assertEqual(owner["NocturneState"][3], model.now + 5)
                        model.apply("owner", 18, cursor)
                        self.assertEqual(len(model.draws), count)

    def test_fates_hud_is_a_private_snapshot_below_arcade_and_expires_after_three_seconds(self):
        for artifact, model in self.models():
            first = model.add("first")
            second = model.add("second")
            model.apply("first", 18, 1)
            first_id = model.globals["FateResultHudIds"][first["HudSlot"]]
            first_hud = model.hud_arguments[first_id]
            first_result = first["NocturneState"][10]
            model.apply("second", 18, 2)
            second_id = model.globals["FateResultHudIds"][second["HudSlot"]]
            second_hud = model.hud_arguments[second_id]
            second_result = second["NocturneState"][10]
            model.globals.update(TriggerPlayer=None, ActivePlayer=None)
            with self.subTest(artifact=artifact):
                for owner, hud, result in (("first", first_hud, first_result), ("second", second_hud, second_result)):
                    self.assertEqual(model.evaluate(hud[0]), owner)
                    self.assertEqual(hud[1:3], ("Null", "Null"))
                    self.assertEqual(hud[4:6], ("Top", "4"))
                    self.assertEqual(model.evaluate(hud[3]), "\n" + result)
                second["NocturneState"][10] = "The pages await your hand."
                model.routine("ResetMenuPage", "first")
                self.assertEqual(model.globals["FateResultHudIds"][first["HudSlot"]], 0)
                self.assertEqual(model.globals["FateResultHudIds"][second["HudSlot"]], second_id)
                self.assertEqual(model.evaluate(second_hud[3]), "\n" + second_result)
                model.now += 2.999
                model.routine("CleanupFateResults")
                self.assertNotIn(second_id, model.destroyed_huds)
                model.now += 0.001
                model.routine("CleanupFateResults")
                self.assertEqual(model.destroyed_huds.count(first_id), 1)
                self.assertEqual(model.destroyed_huds.count(second_id), 1)
                self.assertEqual(model.globals["FateResultHudIds"], [0] * 12)

    def test_repeated_fates_keep_at_most_one_result_per_owner_and_twelve_total(self):
        for artifact, model in self.models():
            owners = [f"owner-{index}" for index in range(12)]
            for owner in owners:
                model.add(owner)
            for turn in range(3):
                model.now += 6
                for owner in owners:
                    model.apply(owner, 18, turn)
                with self.subTest(artifact=artifact, turn=turn):
                    active = [handle for handle in model.globals["FateResultHudIds"] if handle]
                    self.assertEqual(len(active), 12)
                    self.assertEqual(len(set(active)), 12)
                    self.assertEqual(set(model.globals["FateResultOwners"]), set(owners))
                    self.assertEqual(len(model.created_huds) - len(model.destroyed_huds), 12)
            model.now += 3
            model.routine("CleanupFateResults")
            self.assertEqual(len(model.created_huds), len(model.destroyed_huds))

    def test_departed_fates_cleanup_uses_registry_when_player_state_is_lost(self):
        for artifact, model in self.models():
            first = model.add("first")
            second = model.add("second")
            model.apply("first", 18, 0)
            model.apply("second", 18, 1)
            first_id = model.globals["FateResultHudIds"][first["HudSlot"]]
            second_id = model.globals["FateResultHudIds"][second["HudSlot"]]
            model.players["first"] = {"exists": False}
            model.globals["HumanPlayers"].remove("first")
            model.globals["FateResultPlayer"] = "first"
            model.routine("CleanupFateResults")
            with self.subTest(artifact=artifact):
                self.assertIn(first_id, model.destroyed_huds)
                self.assertNotIn(second_id, model.destroyed_huds)
                model.add("replacement", HudSlot=0)
                model.apply("replacement", 18, 2)
                replacement = model.globals["FateResultHudIds"][0]
                model.globals["FateResultPlayer"] = "first"
                model.routine("CleanupFateResults")
                self.assertNotIn(replacement, model.destroyed_huds)
                self.assertNotIn(second_id, model.destroyed_huds)

    def test_whispers_are_private_and_require_reception_on_the_target(self):
        for artifact, model in self.models():
            owner = model.add("owner")
            target = model.add("target")
            model.add("bystander")
            model.aim = "target"
            for cursor in range(1, 6):
                with self.subTest(artifact=artifact, cursor=cursor):
                    model.now += 20
                    before = deepcopy(target)
                    start = len(model.messages)
                    model.apply("owner", 19, cursor)
                    received = model.messages[start:]
                    self.assertEqual({item[1] for item in received}, {"owner", "target"})
                    self.assertEqual(target, before)
                    self.assertEqual(owner["NocturneState"][6], model.now + 15)
                    start = len([item for item in model.messages if item[1] == "target"])
                    model.apply("owner", 19, cursor)
                    self.assertEqual(len([item for item in model.messages if item[1] == "target"]), start)
            model.now += 20
            target["NocturneState"][5] = False
            before = owner["NocturneState"][6]
            model.messages.clear()
            model.apply("owner", 19, 1)
            self.assertFalse(any(item[1] != "owner" for item in model.messages))
            self.assertEqual(owner["NocturneState"][6], before)

    def test_whispers_reject_invalid_private_dead_or_transitioning_targets(self):
        blocked = ({"alive": False}, {"spawned": False}, {"exists": False},
                   {"IsHuman": False}, {"IsPrepared": False}, {"PlayerCycleActive": True},
                   {"InspectionPrivacyActive": True}, {"LastTeam": 2},
                   {"in_view": False}, {"los": False})
        for artifact, model in self.models():
            owner = model.add("owner")
            for changes in blocked:
                target = model.add("target", **changes)
                model.aim = "target"
                model.messages.clear()
                with self.subTest(artifact=artifact, blocked=changes):
                    model.apply("owner", 19, 1)
                    self.assertFalse(any(item[1] == "target" for item in model.messages))
                    self.assertEqual(owner["NocturneState"][6], 0)
                model.globals["HumanPlayers"] = ["owner"]
            for invalid in (None, "owner", "missing"):
                model.aim = invalid
                model.messages.clear()
                model.apply("owner", 19, 1)
                self.assertEqual(owner["NocturneState"][6], 0)

    def test_whispers_reach_a_consented_visible_target_at_any_distance(self):
        for artifact, model in self.models():
            model.add("owner")
            target = model.add("target", position=Vector(500, 40, -800),
                               eye=Vector(500, 41.7, -800))
            model.aim = "target"
            before = deepcopy(target)
            model.apply("owner", 19, 1)
            with self.subTest(artifact=artifact):
                self.assertTrue(any(item[1] == "target" for item in model.messages))
                self.assertEqual(target, before)

    def test_whisper_reset_restores_reception_without_clearing_the_cooldown(self):
        for artifact, model in self.models():
            owner = model.add("owner")
            model.apply("owner", 19, 0)
            self.assertFalse(owner["NocturneState"][5])
            owner["NocturneState"][6] = model.now + 15
            model.routine("ResetMenuPage", "owner")
            with self.subTest(artifact=artifact):
                self.assertEqual(owner["NocturneState"][4:7], [0, True, model.now + 15])

    def test_aura_has_one_handle_per_owner_and_twelve_total_after_repeated_changes(self):
        for artifact, model in self.models():
            owners = [f"owner-{index}" for index in range(12)]
            for owner in owners: model.add(owner)
            for turn in range(3):
                for index, owner in enumerate(owners):
                    model.apply(owner, 20, (index + turn) % 3 + 1)
                    self.assertLessEqual(len(model.effects), 12)
                with self.subTest(artifact=artifact, turn=turn):
                    self.assertEqual(len(model.effects), 12)
                    self.assertEqual(len(set(model.globals["MoonlitAuraOwners"])), 12)
                    self.assertEqual(len(set(model.globals["MoonlitAuraIds"])), 12)
                    before = len(model.created_effects)
                    model.routine("UpdateMoonlitAuras")
                    self.assertEqual(len(model.created_effects), before)
            for owner in owners:
                model.apply(owner, 20, 0)
            self.assertEqual(model.effects, {})
            self.assertEqual(len(model.created_effects), len(model.destroyed_effects))

    def test_aura_visibility_follows_live_owner_and_viewer_preferences(self):
        for artifact, model in self.models():
            owner = model.add("owner")
            viewer = model.add("viewer")
            other = model.add("other")
            for choice in (1, 2, 3):
                model.apply("owner", 20, choice)
                visual = model.effects[model.globals["MoonlitAuraIds"][owner["HudSlot"]]]
                model.globals.update(MoonlitAuraPlayer="other", MoonlitAuraIndex=11,
                                     TriggerPlayer=None, ActivePlayer=None)
                with self.subTest(artifact=artifact, choice=choice):
                    self.assertEqual(model.evaluate(visual[0]), ["owner", "viewer", "other"])
                    viewer["NocturneState"][9] = True
                    owner["NocturneState"][9] = True
                    self.assertEqual(model.evaluate(visual[0]), ["owner", "other"])
                    owner["position"] = Vector(50, 4, -30)
                    owner["eye"] = Vector(50, 5.7, -30)
                    expected = owner["eye"] + Vector(0, 0.35, 0) if choice == 2 else owner["position"] + Vector(0, 0.05 if choice == 1 else 0.8, 0)
                    self.assertEqual(model.evaluate(visual[3]), expected)
                    self.assertEqual(model.evaluate(visual[2]), owner["NameColor"])
                    owner["ColorIndex"] += 1
                    owner["NameColor"] = (90, 100, 150, 255)
                    self.assertEqual(model.evaluate(visual[0]), [])
                    model.routine("UpdateMoonlitAuras")
                    fresh = model.effects[model.globals["MoonlitAuraIds"][owner["HudSlot"]]]
                    self.assertEqual(model.evaluate(fresh[2]), owner["NameColor"])
                    owner["alive"] = False
                    self.assertEqual(model.evaluate(fresh[0]), [])
                    model.routine("UpdateMoonlitAuras")
                    self.assertEqual(model.effects, {})
                    self.assertEqual(owner["NocturneState"][8], choice)
                    owner["alive"] = True
                    viewer["NocturneState"][9] = False
                    model.routine("UpdateMoonlitAuras")
                    self.assertEqual(len(model.effects), 1)

    def test_departed_aura_cleanup_survives_lost_player_state_and_recycled_ids(self):
        for artifact, model in self.models():
            first = model.add("first")
            second = model.add("second")
            model.apply("first", 20, 1)
            model.apply("second", 20, 2)
            old_handle = model.globals["MoonlitAuraIds"][first["HudSlot"]]
            second_handle = model.globals["MoonlitAuraIds"][second["HudSlot"]]
            model.players["first"] = {"exists": False}
            model.globals["HumanPlayers"].remove("first")
            model.globals["MoonlitAuraPlayer"] = "first"
            model.routine("CleanupMoonlitAura")
            with self.subTest(artifact=artifact):
                self.assertNotIn(old_handle, model.effects)
                self.assertIn(second_handle, model.effects)
                model.next_entity = old_handle
                model.add("replacement", HudSlot=0)
                model.apply("replacement", 20, 3)
                self.assertIn(old_handle, model.effects)
                model.globals["MoonlitAuraPlayer"] = "first"
                model.routine("CleanupMoonlitAura")
                self.assertIn(old_handle, model.effects)
                self.assertIn(second_handle, model.effects)

    def test_aura_reset_turns_off_only_the_owner_and_restores_viewer_visibility(self):
        for artifact, model in self.models():
            owner = model.add("owner")
            other = model.add("other")
            model.apply("owner", 20, 1)
            model.apply("other", 20, 2)
            model.apply("owner", 20, 4)
            before = deepcopy(other)
            model.routine("ResetMenuPage", "owner")
            with self.subTest(artifact=artifact):
                self.assertEqual(owner["NocturneState"][7:10], [0, 0, False])
                self.assertEqual(other, before)
                self.assertEqual(len(model.effects), 1)
                self.assertIn(model.globals["MoonlitAuraIds"][other["HudSlot"]], model.effects)


class NocturneMutationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = ARTIFACTS[0].read_text(encoding="utf-8")

    def errors(self, source):
        checks = validator.Checks()
        _, players, _, _ = validator.declaration_entries(source)
        validator.validate_nocturne_social(checks, source, validator.extract_rules(source), players)
        return checks.errors

    def test_social_gate_rejects_missing_consent_lifecycle_geometry_or_cooldown(self):
        cases = (
            ("Abort If(Player Variable(Event Player.InspectionTarget, NocturneState)[5] == False);", "", "consenso e target valido"),
            ("Abort If(Player Variable(Event Player.InspectionTarget, InspectionPrivacyActive) == True);", "", "consenso e target valido"),
            ("Abort If(Player Variable(Event Player.InspectionTarget, PlayerCycleActive) == True);", "", "consenso e target valido"),
            ("Event Player.NocturneState[3] = Total Time Elapsed + 5;", "Event Player.NocturneState[3] = Total Time Elapsed;", "cooldown 5s"),
            ("Event Player.NocturneState[6] = Total Time Elapsed + 15;", "Event Player.NocturneState[6] = Total Time Elapsed;", "cooldown 15s"),
        )
        self.assertEqual(self.errors(self.source), [])
        for old, new, expected in cases:
            with self.subTest(mutation=old):
                self.assertIn(old, self.source)
                self.assertTrue(any(expected in error for error in self.errors(self.source.replace(old, new, 1))))

    def test_social_gate_requires_fixed_page_identity_and_live_cursor_preferences_and_color(self):
        renderer = validator.rule_by_subroutine(validator.extract_rules(self.source), "DrawNocturneMenu")
        cases = (
            ("Evaluate Once(Event Player.MenuPage)", "Event Player.MenuPage", "identita pagina congelata"),
            ("Event Player.NocturneState[1]", "Evaluate Once(Event Player.NocturneState[1])", "restano live"),
            ("Event Player.NocturneState[5]", "Evaluate Once(Event Player.NocturneState[5])", "restano live"),
            ("X Component Of(Event Player.MenuColor)", "Evaluate Once(X Component Of(Event Player.MenuColor))", "restano live"),
        )
        for old, new, expected in cases:
            with self.subTest(mutation=old):
                self.assertIn(old, renderer.body)
                body = renderer.body.replace(old, new, 1)
                mutated = self.source[:renderer.start] + body + self.source[renderer.end:]
                self.assertTrue(any(expected in error for error in self.errors(mutated)))

    def test_whispers_gate_rejects_restoring_a_distance_limit(self):
        consent = "Abort If(Player Variable(Event Player.InspectionTarget, NocturneState)[5] == False);"
        mutated = self.source.replace(consent, consent + "\nAbort If(Distance Between(Event Player, Event Player.InspectionTarget) > 25);", 1)
        self.assertTrue(any("Whispers senza limite di distanza" in error for error in self.errors(mutated)))

    def test_fates_gate_requires_private_result_snapshot_spacing_and_expiration(self):
        fate = validator.rule_by_subroutine(validator.extract_rules(self.source), "ShowFateResult")
        cases = (
            ("Create HUD Text(Evaluate Once(Event Player)", "Create HUD Text(Global.HumanPlayers", "Fates privato"),
            ('Custom String("\\n{0}", Evaluate Once(Event Player.NocturneState[10]))',
             'Custom String("{0}", Evaluate Once(Event Player.NocturneState[10]))', "riga vuota"),
            ("Evaluate Once(Event Player.NocturneState[10])", "Event Player.NocturneState[10]", "snapshot del risultato"),
            ("Top, 4,", "Top, 3,", "sotto il menu"),
            ("Total Time Elapsed + 3;", "Total Time Elapsed + 30;", "scadenza 3s"),
        )
        for old, new, expected in cases:
            with self.subTest(mutation=old):
                self.assertIn(old, fate.body)
                body = fate.body.replace(old, new, 1)
                mutated = self.source[:fate.start] + body + self.source[fate.end:]
                self.assertTrue(any(expected in error for error in self.errors(mutated)))

    def test_aura_gate_rejects_global_reset_foreign_effects_and_unfrozen_ownership(self):
        cases = (
            ("If(Global.MoonlitAuraOwners[Global.MoonlitAuraIndex] == Global.MoonlitAuraPlayer);", "If(True);", "owner esatto"),
            ("For Global Variable(MoonlitAuraIndex, 0, 12, 1);", "For Global Variable(MoonlitAuraIndex, 0, 24, 1);", "dodici slot"),
            ("Ring, Evaluate Once(Player Variable(Evaluate Once(Global.MoonlitAuraPlayer), NameColor))", "Light Shaft, Evaluate Once(Player Variable(Evaluate Once(Global.MoonlitAuraPlayer), NameColor))", "Ring e Cloud"),
            ("Position Of(Evaluate Once(Global.MoonlitAuraPlayer))", "Position Of(Global.MoonlitAuraPlayer)", "congela proprietario"),
        )
        for old, new, expected in cases:
            with self.subTest(mutation=old):
                self.assertIn(old, self.source)
                self.assertTrue(any(expected in error for error in self.errors(self.source.replace(old, new, 1))))
        reset = validator.rule_by_subroutine(validator.extract_rules(self.source), "ResetMenuPage")
        changed = reset.body.replace("Event Player.NocturneState[2] = 0;", "Event Player.NocturneState[2] = 0;\n\t\t\tEvent Player.NocturneState[3] = 0;", 1)
        mutated = self.source[:reset.start] + changed + self.source[reset.end:]
        self.assertTrue(any("reset non deve azzerare cooldown" in error for error in self.errors(mutated)))


if __name__ == "__main__":
    unittest.main()
