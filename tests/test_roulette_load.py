"""Execute the source roulette with controlled clock, RNG and native calls.

The harness follows the actual phase guard, rotations, outcome application and
expiry branches. It measures script work and nominal timing, not server load or
Overwatch rendering cost. Decimal arithmetic avoids host-float tick drift.
"""

from collections import Counter
from decimal import Decimal
import operator
import random
import re
import unittest

from tools import validate_workshop as validator
from tests.test_audit_lifecycle import AuditExpression, AuditLifecycleEvaluator, arguments
from tests.test_roster_rejoin_regressions import SOURCES


STEP = Decimal("0.050")
PHASE = "Global.SchedulerStep % 4 == Global.ActivePlayer.HudSlot % 4"
OLD_GUARD = ("If(And(Global.ActivePlayer.LuckSpinCount > 0, "
             "Total Time Elapsed >= Global.ActivePlayer.NextLuckSpinTime));")
NEW_GUARD = ("If(And(" + PHASE + ", And(Global.ActivePlayer.LuckSpinCount > 0, "
             "Total Time Elapsed >= Global.ActivePlayer.NextLuckSpinTime)));")


class RouletteSourceEvaluator(AuditLifecycleEvaluator):
    NATIVE = {"Small Message", "Set Move Speed", "Start Accelerating", "Stop Accelerating",
              "Allow Button", "Set Player Health", "Set Status", "Clear Status",
              "Set Damage Received", "Damage", "Destroy HUD Text"}

    def __init__(self, source, baseline=False):
        self.expressions = {}
        super().__init__(source)
        self.last_icon = None
        self.next_icon = 1
        self.live_icons = {}
        self.rotations = []
        self.deletions = []
        self.completed = {}
        self.completion_counts = Counter()
        self.expired = {}
        self.native = []
        apply = validator.rule_by_subroutine(self.rules, "ApplyLuckPage")
        machine = validator.rule_by_subroutine(self.rules, "ProcessPlayerLuck")
        self.apply_actions = self.tokens(validator.rule_block(apply, "actions"))
        body = validator.rule_block(machine, "actions")
        if baseline:
            if body.count(NEW_GUARD) != 1:
                raise AssertionError("expected one source rotation phase")
            body = body.replace(NEW_GUARD, OLD_GUARD, 1)
        self.machine_actions = self.tokens(body)
        scheduler = next(rule for rule in self.rules
                         if "Global.SchedulerStep =" in rule.body
                         and "Call Subroutine(ProcessPlayerLuck);" in rule.body)
        self.advance = next(token for token in self.tokens(validator.rule_block(scheduler, "actions"))
                            if token.startswith("Global.SchedulerStep ="))
        self.globals["SchedulerStep"] = 0

    @staticmethod
    def tokens(body):
        return [token.strip() for token in validator.mask_strings(body).split(";") if token.strip()]

    def add(self, identity, rounds=24, outcome=1):
        if not self.join(identity):
            raise AssertionError("no free roster slot")
        self.players[identity].update(
            LuckActive=False, RevengeDeathPending=False, LuckSpinCount=0,
            LuckEffect=0, LuckEffectEndTime=0, NextLuckSpinTime=0,
            LuckIconEndTime=0, NextLuckBurnTime=0, LuckIcon=None,
            LuckEffectHud=None, MenuHud=None, MenuOpen=True, FlyModeActive=False,
            rounds=rounds, outcome=outcome,
        )

    def resolve(self, name):
        if name == "LastCreatedEntity":
            return self.last_icon
        return super().resolve(name)

    def call(self, name, args):
        if name == "RandomInteger":
            state = self.players[self.globals["ActivePlayer"] or self.event_player]
            if args == [20, 24]:
                return state["rounds"]
            if args == [1, 6]:
                return state["outcome"]
            raise AssertionError(f"unexpected random bounds: {args}")
        return super().call(name, args)

    def evaluate(self, expression):
        packed = re.sub(r"\s+", "", expression)
        while "[" in packed:
            converted = re.sub(r"([A-Za-z_][\w.]*)\[([^\[\]]+)\]", r"At(\1,\2)", packed)
            if converted == packed:
                raise AssertionError(f"unsupported index: {expression}")
            packed = converted
        if packed not in self.expressions:
            self.expressions[packed] = AuditExpression(packed).tree
        operations = {"+": operator.add, "-": operator.sub, "*": operator.mul,
                      "/": operator.truediv, "%": operator.mod, "==": operator.eq,
                      "!=": operator.ne, "<": operator.lt, ">": operator.gt,
                      "<=": operator.le, ">=": operator.ge}

        def visit(node):
            kind = node[0]
            if kind == "literal":
                return Decimal(str(node[1]))
            if kind == "name":
                return self.resolve(node[1])
            if kind == "negate":
                return -visit(node[1])
            if kind == "conditional":
                return visit(node[2] if visit(node[1]) else node[3])
            if kind != "call":
                return operations[kind](visit(node[1]), visit(node[2]))
            name, args = node[1:]
            if name in ("And", "Or"):
                return (all if name == "And" else any)(bool(visit(arg)) for arg in args)
            if name in ("FilteredArray", "SortedArray"):
                values = visit(args[0])
                previous = self.current

                def key(value):
                    self.current = value
                    return visit(args[1])

                try:
                    return ([value for value in values if key(value)] if name == "FilteredArray"
                            else sorted(values, key=key))
                finally:
                    self.current = previous
            return self.call(name, [visit(arg) for arg in args])

        return visit(self.expressions[packed])

    def execute_actions(self, tokens):
        frames = []
        active = True
        owner = self.globals["ActivePlayer"] or self.event_player
        for token in tokens:
            if token.startswith("If("):
                condition = active and bool(self.evaluate(token[3:-1]))
                frames.append({"parent": active, "taken": condition})
                active = condition
            elif token.startswith("Else If("):
                frame = frames[-1]
                active = frame["parent"] and not frame["taken"] and bool(self.evaluate(token[8:-1]))
                frame["taken"] = frame["taken"] or active
            elif token == "Else":
                frame = frames[-1]
                active = frame["parent"] and not frame["taken"]
                frame["taken"] = True
            elif token == "End":
                active = frames.pop()["parent"]
            elif active:
                if token.startswith("Create Icon("):
                    self.last_icon = self.next_icon
                    self.next_icon += 1
                    self.live_icons[self.last_icon] = owner
                    self.rotations.append((self.now, owner, self.last_icon))
                elif token.startswith("Destroy Icon("):
                    handle = self.evaluate(token[len("Destroy Icon("):-1])
                    if self.live_icons.pop(handle, None) != owner:
                        raise AssertionError(f"unowned icon destruction: {handle}")
                    self.deletions.append((self.now, owner, handle))
                elif token.startswith("Modify Player Variable("):
                    target, field, operation, value = arguments(token[len("Modify Player Variable("):-1])
                    state = self.players[self.evaluate(target)]
                    state[field] = {"Add": operator.add, "Subtract": operator.sub}[operation](
                        state[field], self.evaluate(value))
                elif re.match(r"(?:Global\.|Event Player\.)[^=]+=(?!=)", token):
                    target, expression = token.split("=", 1)
                    value = self.evaluate(expression)
                    state = self.players[owner]
                    if target.strip().endswith(".NextLuckSpinTime") and value == 0:
                        if state["NextLuckSpinTime"] > 0:
                            self.completed[owner] = self.now
                            self.completion_counts[owner] += 1
                    if target.strip().endswith(".LuckEffectEndTime") and value == 0:
                        if state["LuckEffectEndTime"] > 0:
                            self.expired[owner] = self.now
                    self.assign(target.strip(), value)
                elif token.split("(", 1)[0] in self.NATIVE:
                    self.native.append((self.now, owner, token.split("(", 1)[0]))
                else:
                    raise AssertionError(f"unsupported roulette action: {token}")
        if frames:
            raise AssertionError("unbalanced roulette source branches")

    def start(self, identity, now):
        self.now = Decimal(str(now))
        self.event_player = identity
        self.globals["ActivePlayer"] = identity
        self.execute_actions(self.apply_actions)
        self.globals["ActivePlayer"] = None

    def tick(self, now, order=None):
        self.now = Decimal(str(now))
        self.execute_assignment(self.advance)
        for identity in order or list(self.players):
            if self.players[identity].get("exists"):
                self.globals["ActivePlayer"] = identity
                self.execute_actions(self.machine_actions)
        self.globals["ActivePlayer"] = None

    def remove(self, identity):
        first = len(self.destroyed)
        super().remove(identity)
        for handle in self.destroyed[first:]:
            if self.live_icons.pop(handle, None) != identity:
                raise AssertionError(f"unowned departure icon destruction: {handle}")
            self.deletions.append((self.now, identity, handle))


class RouletteLoadTests(unittest.TestCase):
    def sources(self):
        return [(path.name, path.read_text(encoding="utf-8")) for path, _, _ in SOURCES]

    def test_twelve_simultaneous_spins_have_at_most_three_rotations_per_tick(self):
        for name, source in self.sources():
            for rounds in (20, 24):
                with self.subTest(source=name, rounds=rounds):
                    model = RouletteSourceEvaluator(source)
                    for slot in range(12):
                        model.add(f"p{slot}", rounds=rounds)
                        model.start(f"p{slot}", 0)
                    for tick in range(1, 601):
                        model.tick(tick * STEP)
                    counts = Counter(time for time, _, _ in model.rotations)
                    self.assertEqual(max(counts.values()), 3)
                    self.assertEqual(Counter(owner for _, owner, _ in model.rotations),
                                     Counter({f"p{slot}": rounds for slot in range(12)}))
                    self.assertEqual(len(model.completed), 12)
                    self.assertEqual(model.completion_counts, Counter({f"p{slot}": 1 for slot in range(12)}))
                    self.assertEqual(Counter(owner for _, owner, call in model.native if call == "Small Message"),
                                     model.completion_counts)
                    self.assertFalse(model.live_icons)

    def test_arbitrary_starts_and_reordered_roster_do_not_starve_any_owner(self):
        for name, source in self.sources():
            for initial_phase in (0, 1, 198, 199):
                with self.subTest(source=name, phase=initial_phase):
                    model = RouletteSourceEvaluator(source)
                    model.globals["SchedulerStep"] = initial_phase
                    rng = random.Random(91 + initial_phase)
                    starts = {f"p{slot}": rng.randrange(1, 81) for slot in range(12)}
                    for slot in range(12):
                        model.add(f"p{slot}", rounds=20 + slot % 5)
                    for tick in range(1, 601):
                        for owner, start in starts.items():
                            if tick == start:
                                model.start(owner, tick * STEP)
                        order = list(model.players)
                        rng.shuffle(order)
                        model.tick(tick * STEP, order)
                    self.assertLessEqual(max(Counter(t for t, _, _ in model.rotations).values()), 3)
                    self.assertEqual(len(model.completed), 12)
                    self.assertEqual(model.completion_counts, Counter({f"p{slot}": 1 for slot in range(12)}))
                    for slot in range(12):
                        self.assertEqual(sum(owner == f"p{slot}" for _, owner, _ in model.rotations),
                                         20 + slot % 5)

    def test_recycled_roster_slot_inherits_phase_without_stale_work(self):
        for name, source in self.sources():
            with self.subTest(source=name):
                model = RouletteSourceEvaluator(source)
                for slot in range(12):
                    model.add(f"p{slot}")
                    model.start(f"p{slot}", 0)
                for tick in range(1, 81):
                    model.tick(tick * STEP)
                model.remove("p3")  # Execute existing source roster/icon cleanup.
                self.assertNotIn("p3", model.live_icons.values())
                model.players["p3"]["exists"] = False
                departed_count = len(model.rotations)
                model.add("replacement", rounds=20)
                self.assertEqual(model.players["replacement"]["HudSlot"], 3)
                model.start("replacement", 80 * STEP)
                for tick in range(81, 601):
                    model.tick(tick * STEP)
                self.assertFalse(any(owner == "p3" for _, owner, _ in model.rotations[departed_count:]))
                self.assertEqual(sum(owner == "replacement" for _, owner, _ in model.rotations), 20)
                self.assertIn("replacement", model.completed)
                self.assertLessEqual(max(Counter(t for t, _, _ in model.rotations).values()), 3)
                self.assertFalse(model.live_icons)

    def test_real_time_outcome_and_effect_expiry_are_not_phase_gated(self):
        for name, source in self.sources():
            for outcome, duration in ((1, 15), (2, 10), (5, 10), (6, 5)):
                with self.subTest(source=name, outcome=outcome):
                    model = RouletteSourceEvaluator(source)
                    model.add("one", outcome=outcome)
                    state = model.players["one"]
                    state.update(LuckActive=True, LuckSpinCount=0, LuckEffect=outcome,
                                 NextLuckSpinTime=Decimal("10.037"))
                    # Slot 0 cannot rotate at phase 1; final outcome still applies here.
                    model.tick(Decimal("10.050"))
                    self.assertEqual(model.completed["one"], Decimal("10.050"))
                    self.assertEqual(state["LuckEffectEndTime"], Decimal("10.050") + duration)
                    state["LuckIconEndTime"] = 0
                    model.globals["SchedulerStep"] = 0
                    model.tick(Decimal("10.050") + duration)
                    self.assertEqual(model.expired["one"], Decimal("10.050") + duration)
                    self.assertFalse(state["LuckActive"])

    def test_all_six_final_outcomes_apply_once_without_waiting_for_the_icon_phase(self):
        for name, source in self.sources():
            with self.subTest(source=name):
                model = RouletteSourceEvaluator(source)
                for slot in range(12):
                    owner = f"p{slot}"
                    model.add(owner, outcome=1 + slot % 6)
                    model.players[owner].update(
                        LuckActive=True, LuckSpinCount=0, LuckEffect=1 + slot % 6,
                        NextLuckSpinTime=Decimal("10.037"))
                model.tick(Decimal("10.050"))
                self.assertEqual(set(model.completed.values()), {Decimal("10.050")})
                self.assertEqual(len(model.completed), 12)
                for tick in range(202, 521):
                    model.tick(tick * STEP)
                expected = Counter({f"p{slot}": 1 for slot in range(12)})
                self.assertEqual(model.completion_counts, expected)
                self.assertEqual(Counter(owner for _, owner, call in model.native if call == "Small Message"),
                                 expected)

    def test_wrapping_counter_keeps_four_equal_slot_phases(self):
        for name, source in self.sources():
            with self.subTest(source=name):
                model = RouletteSourceEvaluator(source)
                model.globals["SchedulerStep"] = 198
                for slot in range(12):
                    model.add(f"p{slot}")
                    model.start(f"p{slot}", 0)
                phases = []
                for tick in range(1, 5):
                    model.tick(tick * STEP)
                    phases.append(model.globals["SchedulerStep"])
                self.assertEqual(phases, [199, 0, 1, 2])
                self.assertEqual(Counter(owner for _, owner, _ in model.rotations),
                                 Counter({f"p{slot}": 1 for slot in range(12)}))

    def test_completion_delay_is_bounded_against_unphased_source(self):
        for name, source in self.sources():
            for rounds in (20, 24):
                with self.subTest(source=name, rounds=rounds):
                    phased = RouletteSourceEvaluator(source)
                    baseline = RouletteSourceEvaluator(source, baseline=True)
                    for model in (phased, baseline):
                        for slot in range(12):
                            model.add(f"p{slot}", rounds=rounds)
                            model.start(f"p{slot}", 0)
                        for tick in range(1, 481):
                            model.tick(tick * STEP)
                    for owner in phased.completed:
                        extra = phased.completed[owner] - baseline.completed[owner]
                        self.assertGreaterEqual(extra, 0)
                        self.assertLessEqual(extra, Decimal("0.150") * rounds)
                    self.assertEqual(max(Counter(time for time, _, _ in baseline.rotations).values()), 12)
                    self.assertEqual(max(Counter(time for time, _, _ in phased.rotations).values()), 3)

    def test_validator_rejects_missing_unstable_or_overbroad_phase(self):
        source = SOURCES[1][0].read_text(encoding="utf-8")
        mutations = [source.replace(NEW_GUARD, OLD_GUARD, 1),
                     source.replace(PHASE, PHASE.replace("Global.ActivePlayer.HudSlot", "Global.SchedulerPlayerIndex"), 1),
                     source.replace(PHASE, PHASE.replace("% 4", "% 3"), 1),
                     source.replace("If(Global.ActivePlayer.LuckIconEndTime > 0);",
                                    "If(And(" + PHASE + ", Global.ActivePlayer.LuckIconEndTime > 0));", 1)]
        for mutated in mutations:
            self.assertNotEqual(mutated, source)
            checks = validator.Checks()
            validator.validate_try_your_luck(checks, mutated, validator.extract_rules(mutated), set())
            self.assertTrue(any("fase" in error or "fasi" in error for error in checks.errors), checks.errors)


if __name__ == "__main__":
    unittest.main()
