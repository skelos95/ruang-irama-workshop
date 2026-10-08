"""Execute the emitted callback ring and global drain, not a copied queue model.

Engine event delivery is supplied explicitly. These tests verify source-derived
snapshots, admission, FIFO bookkeeping and worker guards, not Overwatch timing.
"""
from __future__ import annotations

from pathlib import Path
import re
import unittest

from tests.test_global_controller_execution import GeneratedControllerEvaluator
from tests.test_fly_motion import Vector
from tests.runtime_selection import rule_for_logical_id
from tools import validate_global_runtime as runtime
from tools import validate_workshop as semantic


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "workshop/ruang_irama.en-US.workshop"


class EventQueueEvaluator(GeneratedControllerEvaluator):
    """Strict interpreter of actual ring actions and selected event workers."""

    def __init__(self, source):
        super().__init__(source)
        self.globals.update(EventQueue=[], EventQueueHead=0,
                            EventQueueTail=0, EventCount=0,
                            InitialEventCount=0, DroppedEventCount=0,
                            TriggerPlayer=None, ActiveEvent=None,
                            SuperPunchTimes=[0] * 12, PendingLeaves=[])
        self.event = {}
        self.dispatched = []
        self.worker_mode = False
        self.after_dispatch = None

    def add_player(self, identity, **changes):
        state = super().add_player(identity, **changes)
        state.setdefault("hero", "Anran")
        state.setdefault("name", identity)
        state.setdefault("position", Vector(2, 5, 8))
        state.setdefault("statuses", set())
        state.setdefault("HudSlot", len(self.players) - 1)
        state.setdefault("RevengeKillers", [])
        state.setdefault("RevengeDebts", [])
        state[self.state_field] = [0] * 36 + [len(self.players)]
        return state

    def resolve(self, name):
        if name in self.event:
            return self.event[name]
        if name.startswith("EventPlayer."):
            return self.players[self.event["EventPlayer"]].get(name[12:], 0)
        return super().resolve(name)

    def call(self, name, args):
        if name in ("Hero", "EvaluateOnce"):
            return args[0]
        if name == "HeroOf":
            return self.players.get(args[0], {}).get("hero")
        if name == "PositionOf":
            return self.players.get(args[0], {}).get("position", Vector(0, 0, 0))
        if name == "HasStatus":
            return args[1] in self.players.get(args[0], {}).get("statuses", set())
        if name == "PlayerVariable":
            return self.players.get(args[0], {}).get(args[1], 0)
        if name == "CustomString":
            values = [self.players.get(value, {}).get("name", value) for value in args[1:]]
            return args[0].format(*values)
        if name == "IndexOfArrayValue":
            return args[0].index(args[1]) if args[1] in args[0] else -1
        if name == "AppendToArray":
            return args[0] + [args[1]]
        if name == "InputBindingString":
            return args[0]
        return super().call(name, args)

    def fire(self, prefix, owner, *, attacker=None, victim=None, damage=30):
        self.event = {"EventPlayer": owner, "Attacker": attacker,
                      "Victim": victim, "EventAbility": "Melee",
                      "EventDamage": damage}
        callback = rule_for_logical_id(self.rules, prefix)
        if semantic.event_type(callback) not in runtime.NATIVE_EVENTS:
            raise AssertionError((prefix, "expected a native callback"))
        condition = semantic.rule_block(callback, "conditions") or ""
        for expression in semantic.split_top_level(condition, ";"):
            if expression.strip() and not self.expression(expression):
                return False
        self.execute(callback)
        return True

    @staticmethod
    def nodes(rule):
        actions = semantic.rule_block(rule, "actions") or ""
        actions = re.sub(r'(?m)^[ \t]*"(?:\\.|[^"\\])*"[ \t]*(?:\r?\n|$)', "", actions)
        statements = [re.sub(r"\s+", "", text)
                      for text in semantic.split_top_level(actions, ";") if text.strip()]

        def block(index):
            result = []
            while index < len(statements):
                value = statements[index]
                if value == "End" or value == "Else" or value.startswith("ElseIf("):
                    break
                if value.startswith("If("):
                    branches = []
                    predicate = value[3:-1]
                    while True:
                        children, index = block(index + 1)
                        branches.append((predicate, children))
                        if statements[index] == "End":
                            index += 1
                            break
                        predicate = (None if statements[index] == "Else"
                                     else statements[index][7:-1])
                    result.append(("if", branches))
                elif value.startswith("ForGlobalVariable("):
                    children, end = block(index + 1)
                    if statements[end] != "End":
                        raise AssertionError("unclosed emitted loop")
                    result.append(("for", value[18:-1], children))
                    index = end + 1
                else:
                    result.append(("action", value))
                    index += 1
            return result, index

        output, consumed = block(0)
        if consumed != len(statements):
            raise AssertionError("unbalanced emitted branches")
        return output

    def execute(self, rule):
        def run(nodes):
            for node in nodes:
                if node[0] == "if":
                    for predicate, children in node[1]:
                        if predicate is None or self.expression(predicate):
                            if run(children):
                                return True
                            break
                elif node[0] == "for":
                    args = semantic.split_top_level(node[1], ",")
                    field = args[0]
                    start, end, step = [int(self.expression(arg)) for arg in args[1:]]
                    for value in range(start, end, step):
                        self.globals[field] = value
                        if run(node[2]):
                            return True
                else:
                    statement = node[1]
                    if statement == "Abort":
                        return True
                    if statement.startswith("AbortIf("):
                        if self.expression(statement[8:-1]):
                            return True
                        continue
                    if match := re.fullmatch(r"(Global\.\w+(?:\.\w+)?(?:\[.*\])?)([+\-*/%]?=)(?!=)(.+)", statement):
                        value = self.expression(match[3])
                        if match[2] != "=":
                            value = self.expression(f"{match[1]}{match[2][0]}({match[3]})")
                        self.assign(match[1], value)
                    elif statement.startswith("CallSubroutine("):
                        target = statement[15:-1]
                        packet = self.globals["ActiveEvent"]
                        self.dispatched.append((target, None if packet is None else list(packet)))
                        if self.worker_mode:
                            matches = [rule for rule in self.rules
                                       if semantic.event_type(rule) == "Subroutine"
                                       and semantic.subroutine_target(rule) == target]
                            if target.startswith("NativeEvent"):
                                if len(matches) != 1:
                                    raise AssertionError((target, len(matches)))
                                self.execute(matches[0])
                        if self.after_dispatch is not None:
                            self.after_dispatch(target)
                    else:
                        match = re.fullmatch(r"(\w+)\((.*)\)", statement)
                        if not match or match[1] not in {
                            "Kill", "StopFacing", "StopThrottleInDirection",
                            "StopAccelerating", "SetMoveSpeed", "StopTransformingThrottle",
                            "SetGravity", "EnableMovementCollisionWithEnvironment",
                            "SetUltimateCharge", "SmallMessage", "SetPlayerVariable",
                            "ModifyPlayerVariableAtIndex", "ModifyPlayerVariable",
                        }:
                            raise AssertionError(f"unsupported emitted action {statement}")
                        args = [self.expression(arg) for arg in
                                semantic.split_top_level(match[2], ",")]
                        self.native_calls.append((match[1], args))
                        if match[1] == "SetPlayerVariable":
                            self.players[args[0]][args[1]] = args[2]
                        elif match[1] == "ModifyPlayerVariableAtIndex":
                            values = self.players[args[0]][args[1]]
                            index = int(args[2])
                            if args[3] == "Add":
                                values[index] += args[4]
                            elif args[3] == "Subtract":
                                values[index] -= args[4]
                            else:
                                raise AssertionError(f"unsupported emitted operation {args[3]}")
            return False
        run(self.nodes(rule))

    def drain(self, *, workers=False):
        self.worker_mode = workers
        self.execute(semantic.rule_by_subroutine(self.rules, "ProcessGlobalEventQueue"))


class GlobalEventQueueTests(unittest.TestCase):
    def model(self):
        text = runtime.english(ARTIFACT.read_text(encoding="utf-8"))
        if "Ongoing - Each Player" in text:
            raise AssertionError("test requires actual generated global artifact")
        return EventQueueEvaluator(text)

    def test_snapshots_keep_death_position_and_revenge_state_at_delivery(self):
        model = self.model()
        player = model.add_player("p", alive=False, RevengeDeathPending=True,
                                  RevengeClaimant="collector")
        model.add_player("collector")
        model.now = 1.2
        self.assertTrue(model.fire("12e", "p", attacker="collector"))
        self.assertTrue(model.fire("17", "p", attacker="collector"))
        player.update(position=Vector(100, 2, 8), RevengeDeathPending=False,
                      RevengeClaimant=None)
        model.now = 1.25
        model.drain()
        first, second = [entry[1] for entry in model.dispatched]
        self.assertEqual(first[6], Vector(2, 5, 8))
        self.assertEqual(first[7], 1.2)
        self.assertTrue(second[8])
        self.assertEqual(second[9], "collector")
        self.assertEqual(second[2], "collector")
        self.assertTrue(second[10])

    def test_ring_wraps_fifo_and_releases_each_consumed_record(self):
        model = self.model()
        model.add_player("p", alive=False)
        for batch in range(8):
            expected = []
            for index in range(48):
                model.now = batch * 100 + index
                model.fire("12e", "p")
                expected.append(model.now)
            before = len(model.dispatched)
            model.drain()
            self.assertEqual([packet[7] for _, packet in model.dispatched[before:]], expected)
            self.assertEqual(model.globals["EventCount"], 0)
            self.assertEqual(model.globals["EventQueueHead"], model.globals["EventQueueTail"])
            self.assertTrue(all(value is None for value in model.globals["EventQueue"]))
            self.assertLessEqual(len(model.globals["EventQueue"]), 256)
            self.assertIsNone(model.globals["TriggerPlayer"])
            self.assertIsNone(model.globals["ActiveEvent"])

    def test_damage_reserves_capacity_for_twelve_deaths_and_leaves(self):
        model = self.model()
        for index in range(12):
            model.add_player(f"p{index}", LuckActive=True)
        model.globals["SuperPunchPlayers"] = ["p0"]
        for _ in range(256):
            model.fire("89i1", "p0", victim="p1")
        damage_count = model.globals["EventCount"]
        lost_before = model.globals["DroppedEventCount"]
        for index in range(12):
            identity = f"p{index}"
            model.players[identity]["alive"] = False
            for prefix in ("12e", "16a", "17", "18f", "04"):
                self.assertTrue(model.fire(prefix, identity, attacker="p0"))
        self.assertEqual(model.globals["DroppedEventCount"], lost_before)
        self.assertEqual(model.globals["EventCount"], damage_count + 60)
        self.assertLessEqual(len(model.globals["EventQueue"]), 256)

    def test_events_produced_during_drain_wait_for_next_fixed_batch(self):
        model = self.model()
        model.add_player("p", alive=False)
        model.fire("12e", "p")
        def emit_once(_):
            model.after_dispatch = None
            model.fire("17", "p", attacker="p")
        model.after_dispatch = emit_once
        model.drain()
        self.assertEqual(len(model.dispatched), 1)
        self.assertEqual(model.globals["EventCount"], 1)
        model.drain()
        self.assertEqual(len(model.dispatched), 2)
        self.assertEqual(model.dispatched[-1][0], "NativeEvent17")

    def test_full_ring_never_overwrites_already_queued_critical_records(self):
        model = self.model()
        model.add_player("p", alive=False)
        for index in range(300):
            model.now = index
            model.fire("12e", "p")
        self.assertEqual(model.globals["EventCount"], 256)
        self.assertEqual(model.globals["DroppedEventCount"], 44)
        self.assertEqual(len(model.globals["EventQueue"]), 256)
        model.drain()
        self.assertEqual([packet[7] for _, packet in model.dispatched], list(range(256)))

    def punch(self):
        model = self.model()
        model.add_player("p", HudSlot=0)
        model.add_player("v", HudSlot=1)
        model.globals["SuperPunchPlayers"] = ["p"]
        self.assertTrue(model.fire("89i1", "p", victim="v"))
        return model

    def test_punch_retains_protection_at_event_time_even_if_later_removed(self):
        model = self.model()
        model.add_player("p", HudSlot=0)
        victim = model.add_player("v", HudSlot=1, statuses={"Unkillable"})
        model.globals["SuperPunchPlayers"] = ["p"]
        self.assertTrue(model.fire("89i1", "p", victim="v"))
        victim["statuses"] = set()
        model.drain(workers=True)
        self.assertFalse(any(name == "Kill" for name, _ in model.native_calls))

    def test_punch_rechecks_current_protection_before_killing(self):
        model = self.punch()
        model.players["v"]["statuses"].add("Unkillable")
        model.drain(workers=True)
        self.assertFalse(any(name == "Kill" for name, _ in model.native_calls))

    def test_pending_punch_cannot_kill_reused_victim_or_recycled_attacker(self):
        for owner in ("p", "v"):
            with self.subTest(owner=owner):
                model = self.punch()
                model.players[owner][model.state_field][36] += 100
                model.drain(workers=True)
                self.assertFalse(any(name == "Kill" for name, _ in model.native_calls))

    def test_valid_punch_executes_once_with_original_victim_and_killer(self):
        model = self.punch()
        model.drain(workers=True)
        self.assertEqual([args for name, args in model.native_calls if name == "Kill"],
                         [["v", "p"]])
        model.drain(workers=True)
        self.assertEqual(sum(name == "Kill" for name, _ in model.native_calls), 1)

    def test_death_worker_uses_captured_position_after_live_position_moves(self):
        model = self.model()
        player = model.add_player("p", alive=False)
        model.fire("12e", "p")
        player["position"] = Vector(90, -500, 40)
        model.drain(workers=True)
        self.assertEqual(player["DeathPosition"], Vector(2, 5, 8))

    def test_queued_luck_cleanup_cannot_bypass_team_quarantine(self):
        model = self.model()
        player = model.add_player("p", alive=False, LuckActive=True)
        model.fire("18f", "p")
        player.update(IsHuman=False, PlayerCycleActive=True, TeamChangeProcessed=True)
        model.drain(workers=True)
        self.assertNotIn("RestorePlayerLuck", [name for name, _ in model.dispatched])

    def test_team_switch_death_cannot_reset_before_quarantine_is_detected(self):
        for prefix in ("12e", "18f"):
            with self.subTest(prefix=prefix):
                model = self.model()
                player = model.add_player("p", alive=False, LuckActive=True)
                # Native team movement may emit death before the global tick
                # gets its chance to mark the entity's quarantine flags.
                player["team"] = 2
                self.assertFalse(player["PlayerCycleActive"])
                self.assertTrue(model.fire(prefix, "p"))
                model.drain(workers=True)
                self.assertFalse(model.native_calls)
                self.assertNotIn("RestorePlayerLuck", [name for name, _ in model.dispatched])

    def test_revenge_counts_teammate_and_enemy_deaths_from_captured_killer(self):
        for killer_team in (1, 2):
            with self.subTest(killer_team=killer_team):
                model = self.model()
                victim = model.add_player("v", alive=False)
                model.add_player("killer", team=killer_team)
                for expected in (1, 2):
                    model.fire("17", "v", attacker="killer")
                    model.event["Attacker"] = "different-live-event"
                    model.drain(workers=True)
                    self.assertEqual(victim["RevengeKillers"], ["killer"])
                    self.assertEqual(victim["RevengeDebts"], [expected])

    def test_revenge_collection_uses_captured_claimant_after_flags_reset(self):
        model = self.model()
        victim = model.add_player("v", alive=False, RevengeDeathPending=True,
                                  RevengeClaimant="collector")
        collector = model.add_player("collector", RevengeKillers=["v"],
                                     RevengeDebts=[2])
        model.fire("17", "v", attacker="collector")
        victim.update(RevengeDeathPending=False, RevengeClaimant=None)
        model.drain(workers=True)
        self.assertEqual(collector["RevengeDebts"], [1])
        self.assertIsNone(collector["LockedRevengeTarget"])

    def test_revenge_cannot_add_debt_for_a_recycled_killer_identity(self):
        model = self.model()
        victim = model.add_player("v", alive=False)
        killer = model.add_player("killer")
        model.fire("17", "v", attacker="killer")
        killer[model.state_field][36] += 100
        model.drain(workers=True)
        self.assertEqual(victim["RevengeKillers"], [])
        self.assertEqual(victim["RevengeDebts"], [])

    def test_revenge_cannot_write_to_a_recycled_claimant_identity(self):
        model = self.model()
        model.add_player("v", alive=False, RevengeDeathPending=True,
                         RevengeClaimant="collector")
        collector = model.add_player("collector", RevengeKillers=["v"],
                                     RevengeDebts=[2], LockedRevengeTarget="replacement-own-target")
        model.fire("17", "v", attacker="collector")
        collector[model.state_field][36] += 100
        model.drain(workers=True)
        self.assertEqual(collector["RevengeDebts"], [2])
        self.assertEqual(collector["LockedRevengeTarget"], "replacement-own-target")

    def test_removing_victim_generation_guard_exposes_recycled_target(self):
        text = runtime.english(ARTIFACT.read_text(encoding="utf-8"))
        guard = "Player Variable(Global.ActiveEvent[3], ControllerState)[36] == Global.ActiveEvent[22]"
        self.assertIn(guard, text)
        model = EventQueueEvaluator(text.replace(guard, "True", 1))
        model.add_player("p", HudSlot=0)
        model.add_player("v", HudSlot=1)
        model.globals["SuperPunchPlayers"] = ["p"]
        model.fire("89i1", "p", victim="v")
        model.players["v"][model.state_field][36] += 100
        model.drain(workers=True)
        self.assertEqual([args for name, args in model.native_calls if name == "Kill"],
                         [["v", "p"]])


if __name__ == "__main__":
    unittest.main()
