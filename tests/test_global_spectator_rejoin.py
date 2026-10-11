"""Execute emitted spectator reconciliation and the existing phased reentry.

The actual scheduler, controllers and lifecycle subroutines supply every branch
and assignment. Native membership, spawn and clock are controlled inputs; HUD
rendering and engine physics are explicit boundaries, not simulated lifetimes.
"""

from copy import deepcopy
import math
from pathlib import Path
import re
import unittest

from tests.test_camera_reinitialization import CameraExpression
from tests.test_global_event_queue import EventQueueEvaluator
from tests.test_fly_motion import Vector
from tests.runtime_selection import rule_for_logical_id
from tools import validate_global_runtime as runtime
from tools import validate_workshop as semantic


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "workshop/ruang_irama.en-US.workshop"


class SpectatorExpression(CameraExpression):
    """Extend the existing parser with scoped native array transformations."""

    def evaluate(self, context):
        import operator

        operations = {"+": operator.add, "-": operator.sub, "*": operator.mul,
                      "/": operator.truediv, "%": operator.mod,
                      "==": operator.eq, "!=": operator.ne, ">=": operator.ge,
                      "<=": operator.le, ">": operator.gt, "<": operator.lt}

        def visit(node):
            kind = node[0]
            if kind == "literal": return node[1]
            if kind == "name": return context.resolve(node[1])
            if kind == "negate": return -visit(node[1])
            if kind == "conditional": return visit(node[2] if visit(node[1]) else node[3])
            if kind == "index":
                values, index = visit(node[1]), int(visit(node[2]))
                return values[index] if isinstance(values, (list, tuple)) and 0 <= index < len(values) else 0
            if kind == "call":
                name, args = node[1:]
                if name in ("And", "Or"):
                    return (all if name == "And" else any)(bool(visit(arg)) for arg in args)
                if name in ("FilteredArray", "SortedArray", "MappedArray", "IsTrueForAny", "IsTrueForAll"):
                    values, previous = visit(args[0]), context.element

                    def key(value):
                        context.element = value
                        return visit(args[1])

                    try:
                        if name == "IsTrueForAny": return any(key(value) for value in values)
                        if name == "IsTrueForAll": return all(key(value) for value in values)
                        if name == "MappedArray": return [key(value) for value in values]
                        if name == "SortedArray": return sorted(values, key=key)
                        return [value for value in values if key(value)]
                    finally:
                        context.element = previous
                return context.call(name, [visit(arg) for arg in args])
            return operations[kind](visit(node[1]), visit(node[2]))

        return visit(self.tree)


class SpectatorRuntimeEvaluator(EventQueueEvaluator):
    """Interpret emitted ASTs recursively; reject unknown native boundaries."""

    PASSIVE_NATIVE = {
        "AllowButton", "DisallowButton", "StopCamera", "StopModifyingHeroVoiceLines",
        "StopChasingPlayerVariable", "StopAccelerating", "StopTransformingThrottle",
        "SetMoveSpeed", "SetGravity", "EnableMovementCollisionWithEnvironment",
        "EnableMovementCollisionWithPlayers", "DisableMovementCollisionWithEnvironment",
        "SetDamageReceived", "SetKnockbackReceived", "SetJumpVerticalSpeed",
        "SetProjectileSpeed", "ClearStatus", "EnableNameplates", "DisableNameplates",
        "DetachPlayers", "DisableGameModeHUD", "DisableGameModeIn-WorldUI",
        "ChasePlayerVariableOverTime", "SmallMessage", "CancelPrimaryAction",
        "StartForcingDummyBotName", "StopForcingDummyBotName", "SetMatchTime",
        "SetStatus", "SetPlayerHealth", "SetUltimateCharge", "StopFacing",
        "StopThrottleInDirection", "DisableBuilt-InGameModeCompletion",
        "DisableBuilt-InGameModeAnnouncer", "DisableBuilt-InGameModeMusic",
        "DisableInspectorRecording",
        "ApplyImpulse",
    }
    LIFECYCLE = {"QuiescePlayer", "CleanupPlayer", "PreparePlayer"}

    def __init__(self, text):
        super().__init__(text)
        self.element = None
        self.members = []
        self.last_id = 100
        self.resources = {}
        self.destroyed = []
        self.calls = []
        self.native_log = []
        self.now = 0
        self.execute(rule_for_logical_id(self.rules, "00"))

    def expression(self, source):
        def literal(match):
            key = f"Literal{len(self.literals)}"
            self.literals[key] = match[0][1:-1]
            return key

        packed = re.sub(r"\s+", "", re.sub(r'"(?:\\.|[^"\\])*"', literal, source))
        # Icon enum names contain colons, which are otherwise ternary syntax.
        packed = re.sub(r"IconString\(([\w:]+)\)",
                        lambda match: "IconString(" + literal('"' + match[1] + '"') + ")", packed)
        if packed not in self.expressions:
            self.expressions[packed] = SpectatorExpression(packed)
        return self.expressions[packed].evaluate(self)

    def resolve(self, name):
        if name == "CurrentArrayElement": return self.element
        if name in ("LastTextID", "LastCreatedEntity"): return self.last_id
        if name in ("IsGameInProgress", "IsWaitingForPlayers", "IsAssemblingHeroes"):
            return False
        if name == "HostPlayer": return self.members[0] if self.members else None
        if name.startswith("Global.") and len(name.split(".")) == 3:
            _, pointer, field = name.split(".")
            return self.players.get(self.globals.get(pointer), {}).get(field, 0)
        return super().resolve(name)

    def call(self, name, args):
        if name == "AllPlayers": return list(self.members)
        if name == "FirstOf": return args[0][0] if args[0] else None
        if name == "LastOf": return args[0][-1] if args[0] else None
        if name == "Color": return args[0]
        if name == "CustomColor": return tuple(args)
        if name == "IconString": return args[0]
        if name == "Vector": return Vector(*args)
        if name == "ThrottleOf": return Vector(0, 0, 0)
        if name in ("XComponentOf", "YComponentOf", "ZComponentOf"):
            return getattr(args[0], name[0].lower())
        if name == "MagnitudeOf": return args[0].magnitude()
        if name == "FacingDirectionOf": return Vector(0, 0, 1)
        if name == "HorizontalFacingAngleOf": return 0
        if name == "DirectionFromAngles":
            if args[1] != 0: raise AssertionError("only horizontal native direction is supplied")
            yaw = math.radians(args[0])
            return Vector(math.sin(yaw), 0, math.cos(yaw))
        if name == "CrossProduct":
            first, second = args
            return Vector(first.y * second.z - first.z * second.y,
                          first.z * second.x - first.x * second.z,
                          first.x * second.y - first.y * second.x)
        if name == "Normalize": return args[0].normalized()
        if name == "VelocityOf": return Vector(0, 0, 0)
        if name == "Max": return max(args)
        if name == "Min": return min(args)
        if name == "RoundToInteger": return math.ceil(args[0]) if args[1] == "Up" else math.floor(args[0])
        if name in ("WorkshopSettingInteger", "WorkshopSettingToggle"): return args[2]
        if name == "ObjectivePosition": return Vector(0, 0, 0)
        if name == "DistanceBetween": return (args[0] - args[1]).magnitude()
        if name == "IsInSpawnRoom": return False
        if name == "IsOnGround": return True
        if name == "RemoveFromArray": return [value for value in args[0] if value != args[1]]
        return super().call(name, args)

    def run(self, target):
        self.calls.append((self.now, self.globals.get("TriggerPlayer"), target))
        rule = semantic.rule_by_subroutine(self.rules, target)
        if rule is None: raise AssertionError(f"missing emitted subroutine {target}")
        self.execute(rule)

    def native(self, name, arguments):
        args = semantic.split_top_level(arguments, ",") if arguments else []
        if name in ("CreateHUDText", "CreateInWorldText", "CreateIcon"):
            # The renderer cannot change script state; freeze only its recipient.
            self.last_id += 1
            owner = self.expression(args[0])
            self.resources[self.last_id] = (name, deepcopy(owner))
            self.native_log.append((self.now, name, owner))
            return
        if name in ("DestroyHUDText", "DestroyInWorldText", "DestroyIcon"):
            handle = self.expression(args[0])
            if handle:
                if handle not in self.resources:
                    raise AssertionError(f"destroy of unowned or already released handle {handle}")
                self.destroyed.append(handle)
                self.resources.pop(handle)
            self.native_log.append((self.now, name, handle))
            return
        if name in ("Wait", "LoopIfConditionIsTrue"):
            # One actual scheduler pass; the caller supplies the following clock.
            self.native_log.append((self.now, name, tuple(args)))
            return
        if name not in self.PASSIVE_NATIVE:
            raise AssertionError(f"unsupported emitted native action {name}")
        # Dynamic render/physics payloads belong to the native boundary; the
        # recipient itself is evaluated to check isolation between owners.
        owner = self.expression(args[0]) if args else None
        self.native_log.append((self.now, name, deepcopy(owner)))

    def execute(self, rule):
        def sequence(nodes):
            for node in nodes:
                if node[0] == "if":
                    for predicate, children in node[1]:
                        if predicate is None or self.expression(predicate):
                            if sequence(children): return True
                            break
                elif node[0] == "for":
                    args = semantic.split_top_level(node[1], ",")
                    for value in range(*[int(self.expression(arg)) for arg in args[1:]]):
                        self.globals[args[0]] = value
                        if sequence(node[2]): return True
                else:
                    statement = node[1]
                    if statement == "Abort": return True
                    if statement.startswith("AbortIf("):
                        if self.expression(statement[8:-1]): return True
                        continue
                    assignment = re.fullmatch(r"(Global\.\w+(?:\.\w+)?(?:\[.*\])?)([+\-*/%]?=)(?!=)(.+)", statement)
                    if assignment:
                        value = self.expression(assignment[3])
                        if assignment[2] != "=":
                            value = self.expression(f"{assignment[1]}{assignment[2][0]}({assignment[3]})")
                        self.assign(assignment[1], value)
                    elif statement.startswith("CallSubroutine("):
                        self.run(statement[15:-1])
                    elif statement.startswith("ModifyGlobalVariable("):
                        args = semantic.split_top_level(statement[21:-1], ",")
                        if args[1] != "RemoveFromArrayByIndex":
                            raise AssertionError(f"unsupported emitted array mutation {statement}")
                        self.globals[args[0]].pop(int(self.expression(args[2])))
                    elif statement.startswith("SetPlayerVariable("):
                        args = semantic.split_top_level(statement[18:-1], ",")
                        owners = self.expression(args[0])
                        owners = owners if isinstance(owners, list) else [owners]
                        for owner in owners:
                            self.players[owner][args[1]] = self.expression(args[2])
                    else:
                        match = re.fullmatch(r"([\w-]+)(?:\((.*)\))?", statement)
                        if not match: raise AssertionError(f"unsupported emitted statement {statement}")
                        self.native(match[1], match[2])
            return False

        sequence(self.nodes(rule))

    def ready_player(self, identity, **changes):
        state = super().add_player(identity, DisplayName=identity)
        self.globals["HumanPlayers"].remove(identity)  # Base helper's convenience, not runtime admission.
        self.members.append(identity)
        self.globals.update(TriggerPlayer=identity, ActivePlayer=identity)
        self.run("PreparePlayer")
        self.run("Controller02")
        self.run("CloseMenu")
        self.run("ProcessPlayerCycle")
        self.run("ProcessGlobalController")
        state.update(changes)
        return state

    def tick(self, now):
        self.now = now
        self.execute(rule_for_logical_id(self.rules, "04g"))

    def lifecycle(self, owner, after=0):
        return [(when, target) for when, actor, target in self.calls[after:]
                if actor == owner and target in self.LIFECYCLE]


class GlobalSpectatorRejoinTests(unittest.TestCase):
    def model(self):
        return SpectatorRuntimeEvaluator(runtime.english(ARTIFACT.read_text(encoding="utf-8")))

    def prepared_lobby(self):
        model = self.model()
        owner = model.ready_player("returning", CameraMode=1, CameraTarget="returning",
                                   GhostModeActive=True, FlyModeActive=True,
                                   CrouchTravelEnabled=True, InspectionPrivacyActive=True,
                                   VoiceIndex=4, MultijumpEnabled=True,
                                   TravelAttachmentActive=True, TravelAttachmentTarget="other",
                                   VotedPlayer="other")
        other = model.ready_player("other")
        return model, owner, other

    def leave_for_spectators(self, model, queued):
        if queued:
            model.now = 10
            self.assertTrue(model.fire("04", "returning"))
        model.members.remove("returning")
        model.globals["SchedulerStep"] = 20
        model.tick(10)
        if queued:
            model.tick(10.499)
            self.assertIn("returning", model.globals["HumanPlayers"])
            model.tick(10.5)
        else:
            model.globals["SchedulerStep"] = 40
            model.tick(11)

    def assert_defaults(self, state):
        for field in ("GhostModeActive", "FlyModeActive", "CrouchTravelEnabled",
                      "InspectionPrivacyActive", "MultijumpEnabled", "TravelAttachmentActive"):
            self.assertFalse(state[field], field)
        self.assertEqual(state["CameraMode"], 0)
        self.assertIsNone(state["CameraTarget"])
        self.assertIsNone(state["TravelAttachmentTarget"])
        self.assertIsNone(state["VotedPlayer"])
        self.assertEqual(state["VoiceIndex"], 0)
        self.assertTrue(state["MenuOpen"])
        self.assertEqual((state["MenuPage"], state["MainMenuCursor"]), (-1, 0))

    def test_both_departure_paths_invalidate_only_retained_owner_and_do_not_quiesce(self):
        for queued in (False, True):
            with self.subTest(queued=queued):
                model, owner, other = self.prepared_lobby()
                saved_other, other_hud = deepcopy(other), other["PlayerListHud"]
                before = len(model.calls)
                before_native = len(model.native_log)
                self.leave_for_spectators(model, queued)
                self.assertEqual(model.globals["HumanPlayers"], ["other"])
                self.assertFalse(owner["IsPrepared"])
                self.assertFalse(owner["IsHuman"])
                self.assertFalse(owner["TeamChangeProcessed"])
                self.assertFalse(owner["PlayerCycleActive"])
                cleanup_time = 10.5 if queued else 11
                self.assertEqual(model.lifecycle("returning", before), [(cleanup_time, "CleanupPlayer")])
                self.assertEqual(other, saved_other)
                self.assertIn(other_hud, model.resources)
                self.assertEqual(model.lifecycle("other", before), [])
                for _, _, recipient in model.native_log[before_native:]:
                    self.assertNotIn(recipient, ("returning", "other"))

    def test_same_and_different_team_returns_use_both_wait_phases_and_open_info(self):
        for queued in (False, True):
            for team in (1, 2):
                with self.subTest(queued=queued, team=team):
                    model, owner, other = self.prepared_lobby()
                    self.leave_for_spectators(model, queued)
                    saved_other, other_hud = deepcopy(other), other["PlayerListHud"]
                    owner["team"] = team
                    model.members.append("returning")
                    before = len(model.calls)
                    before_native = len(model.native_log)
                    model.tick(20)
                    self.assertNotIn("returning", model.globals["HumanPlayers"])
                    model.tick(20.249)
                    self.assertEqual(model.lifecycle("returning", before), [])
                    model.tick(20.251)
                    self.assertEqual(model.globals["TeamCyclePlayer"], "returning")
                    model.tick(20.30)
                    self.assertEqual(model.lifecycle("returning", before), [(20.30, "QuiescePlayer")])
                    self.assertFalse(owner["IsPrepared"])
                    model.tick(20.349)
                    self.assertEqual(model.globals["TeamCyclePhase"], 1)
                    model.tick(20.351)
                    self.assertEqual(model.globals["TeamCyclePhase"], 2)
                    self.assertNotIn("returning", model.globals["HumanPlayers"])
                    model.tick(20.400)
                    self.assertFalse(owner["IsPrepared"])
                    model.tick(20.402)
                    self.assertEqual(model.lifecycle("returning", before),
                                     [(20.30, "QuiescePlayer"), (20.402, "PreparePlayer")])
                    self.assertIn("returning", model.globals["HumanPlayers"])
                    self.assert_defaults(owner)
                    self.assertEqual(other, saved_other)
                    self.assertIn(other_hud, model.resources)
                    self.assertEqual(model.lifecycle("other", before), [])
                    for _, _, recipient in model.native_log[before_native:]:
                        self.assertNotEqual(recipient, "other")

    def test_native_despawn_or_departure_cancels_pending_phase(self):
        for loss in ("spawned", "exists"):
            with self.subTest(loss=loss):
                model, owner, _ = self.prepared_lobby()
                self.leave_for_spectators(model, True)
                model.members.append("returning")
                for now in (20, 20.251, 20.30): model.tick(now)
                before = len(model.calls)
                owner[loss] = False
                if loss == "exists": model.members.remove("returning")
                model.tick(20.351)
                model.tick(20.402)
                self.assertEqual(model.lifecycle("returning", before), [])
                self.assertNotIn("returning", model.globals["HumanPlayers"])
                self.assertIsNone(model.globals["TeamCyclePhaseOwner"])
                self.assertFalse(owner["IsPrepared"])

    def test_dead_but_spawned_return_preserves_existing_worker_eligibility(self):
        model, owner, _ = self.prepared_lobby()
        self.leave_for_spectators(model, False)
        owner["alive"] = False
        model.members.append("returning")
        for now in (20, 20.251, 20.30, 20.351, 20.402): model.tick(now)
        self.assertFalse(owner["alive"])
        self.assertTrue(owner["IsPrepared"])
        self.assertIn("returning", model.globals["HumanPlayers"])
        self.assert_defaults(owner)

    def test_late_leave_does_not_invalidate_present_reused_entity_or_another_hud_owner(self):
        for same_entity in (False, True):
            with self.subTest(same_entity=same_entity):
                model, owner, _ = self.prepared_lobby()
                model.now = 9
                self.assertTrue(model.fire("04", "returning"))
                old_record = deepcopy(model.globals["EventQueue"][int(model.globals["EventQueueHead"])])
                model.globals.update(EventQueue=[], EventCount=0, EventQueueHead=0, EventQueueTail=0)
                self.leave_for_spectators(model, False)
                if same_entity:
                    model.members.append("returning")
                    for now in (20, 20.251, 20.30, 20.351, 20.402): model.tick(now)
                    current = owner
                    current[model.state_field][36] += 100
                    current.update(DisplayName="replacement", GhostModeActive=True)
                else:
                    current = model.ready_player("replacement", GhostModeActive=True)
                saved = deepcopy(current)
                handle = current["PlayerListHud"]
                model.globals.update(EventQueue=[old_record], EventQueueHead=0,
                                     EventQueueTail=1, EventCount=1)
                before = len(model.calls)
                model.tick(21)
                self.assertEqual(current, saved)
                self.assertIn(handle, model.resources)
                if same_entity:
                    self.assertEqual(model.lifecycle("returning", before), [])
                self.assertEqual(len(model.globals["HumanPlayers"]), 2)


if __name__ == "__main__":
    unittest.main()
