"""Execute source-owned transient resources across lost state and ID recycling.

The projection runs the actual allocation, ownership guards and reaper actions;
rendered text contents and unrelated gameplay actions are outside this model.
"""

import copy
import re
import unittest

from tools import validate_workshop as validator
from tests.test_audit_lifecycle import AuditLifecycleEvaluator, arguments, project, statements
from tests.test_roster_rejoin_regressions import SOURCES


FIELDS = {
    "LuckEffectHud": ("TemporaryEffectHudIds", "HUD Text", "98a -"),
    "TravelText": ("TemporaryTravelTextIds", "In-World Text", "19g -"),
    "LuckVisionText": ("TemporaryVisionTextIds", "In-World Text", "18j -"),
}
REGISTRY = ("TemporaryTextOwners",) + tuple(value[0] for value in FIELDS.values())
SCRATCH = ("TextCleanupIndex", "TextCleanupPlayer", "TextCleanupCursor")


class TransientSourceEvaluator(AuditLifecycleEvaluator):
    FIELDS = AuditLifecycleEvaluator.FIELDS | set(FIELDS)

    def __init__(self, source):
        super().__init__(source)
        self.last_text = None
        self.next_text = 1
        self.live_texts = {}
        self.created_texts = []
        self.destroyed_texts = []
        self.array_writes = []
        for field in REGISTRY:
            initializer = re.search(rf"Global\.{field} = (Array\([^;]+\));", self.initializers)
            if initializer is None:
                raise AssertionError(f"missing durable registry {field}")
            self.globals[field] = self.evaluate(initializer.group(1))
        self.globals.update(TextCleanupIndex=-1, TextCleanupPlayer=None,
                            TextCleanupCursor=0)
        self.reaper = statements(validator.rule_block(
            validator.rule_by_subroutine(self.rules, "CleanupOrphanedText"), "actions"))
        self.creators = {}
        self.capacity = {}
        self.closers = {}
        for field, (_, kind, close_prefix) in FIELDS.items():
            creator = next(rule for rule in self.rules
                           if f"Event Player.{field} = Last Text ID;" in rule.body)
            actions = validator.rule_block(creator, "actions")
            self.creators[field] = project(statements(actions), self.keep(field, create=True))
            conditions = validator.rule_block(creator, "conditions")
            guard = next((token.strip() for token in conditions.split(";")
                          if "Array Contains(Global.TemporaryTextOwners" in token), None)
            if guard is None:
                raise AssertionError(f"creator cannot wake when registry capacity returns: {field}")
            self.capacity[field] = guard
            closer = next(rule for rule in self.rules if rule.name.startswith(close_prefix))
            self.closers[field] = project(statements(validator.rule_block(closer, "actions")),
                                          self.keep(field))

    def keep(self, field=None, create=False, cleanup=False):
        selected = set(FIELDS) if field is None else {field}
        arrays = {FIELDS[name][0] for name in selected} | {REGISTRY[0]} | set(SCRATCH)
        if cleanup:
            arrays |= {"CleanupSubject", "LeavingPlayerIndex", "CleanupPlayerIndex"}

        def keep(token):
            if token == "Call Subroutine(CleanupOrphanedText)":
                return True
            if token.startswith("Abort If(Global.TextCleanupIndex"):
                return True
            if token.startswith("Create "):
                return create
            if token.startswith("Destroy "):
                return any(re.search(rf"\b{name}\b", token) for name in selected)
            if re.match(r"Global\.(?:" + "|".join(arrays) + r")(?:\[| =)", token):
                return True
            return bool(re.match(r"(?:Event Player|Global\.ActivePlayer|Global\.CleanupSubject)\.(?:"
                                 + "|".join(selected) + r") =", token))
        return keep

    def resolve(self, name):
        if name == "LastTextID":
            return self.last_text
        return super().resolve(name)

    def call(self, name, args):
        if name == "At":
            index = int(args[1])
            if not 0 <= index < len(args[0]):
                raise AssertionError(f"out-of-bounds registry read: {index}")
        return super().call(name, args)

    def assign(self, target, value):
        indexed = re.fullmatch(r"Global\.(\w+)\[(.+)\]", target)
        if indexed and indexed[1] in REGISTRY:
            index = int(self.evaluate(indexed[2]))
            if not 0 <= index < len(self.globals[indexed[1]]):
                raise AssertionError(f"out-of-bounds registry write: {index}")
            self.array_writes.append((indexed[1], index, value))
        super().assign(target, value)

    def execute(self, nodes):
        for token, body, otherwise in nodes:
            if token.startswith("If("):
                if self.execute(body if self.evaluate(token[3:-1]) else otherwise):
                    return True
            elif token.startswith("For Global Variable("):
                name, first, last, step = arguments(token[len("For Global Variable("):-1])
                for index in range(int(self.evaluate(first)), int(self.evaluate(last)), int(self.evaluate(step))):
                    self.globals[name] = index
                    if self.execute(body):
                        return True
            elif token.startswith("Abort If("):
                if self.evaluate(token[len("Abort If("):-1]):
                    return True
            elif token.startswith("Create "):
                kind = token[len("Create "):token.index("(")]
                key = kind, self.next_text
                if key in self.live_texts:
                    raise AssertionError("test engine reused a live text ID")
                self.live_texts[key] = self.event_player
                self.created_texts.append((key, self.event_player))
                self.last_text = self.next_text
                self.next_text += 1
            elif token.startswith("Destroy "):
                kind = token[len("Destroy "):token.index("(")]
                key = kind, self.evaluate(token[token.index("(")+1:-1])
                if key not in self.live_texts:
                    raise AssertionError(f"destroyed an unowned or already destroyed resource: {key}")
                owner = self.live_texts.pop(key)
                self.destroyed_texts.append((key, owner))
            elif token == "Call Subroutine(CleanupOrphanedText)":
                self.execute(self.reaper)
            else:
                super().execute([(token, body, otherwise)])
        return False

    def add_player(self, identity, dummy=False):
        self.players[identity] = {"exists": True, "alive": True, "spawned": True,
                                  "dummy": dummy, **{field: None for field in FIELDS}}

    def create(self, identity, field, check_capacity=True):
        self.event_player = identity
        if check_capacity and not self.evaluate(self.capacity[field]):
            return False
        before = len(self.created_texts)
        aborted = self.execute(self.creators[field])
        created = self.created_texts[before:]
        if created and (len(created) != 1 or created[0][1] != identity
                        or created[0][0][0] != FIELDS[field][1]):
            raise AssertionError(f"creator produced unexpected resources: {created}")
        return not aborted and bool(created)

    def close(self, identity, field):
        self.event_player = identity
        self.globals["ActivePlayer"] = identity
        self.execute(self.closers[field])

    def reap(self, identity=None):
        self.globals["TextCleanupPlayer"] = identity
        self.execute(self.reaper)


class TransientOwnershipTests(unittest.TestCase):
    def models(self):
        for path, _, _ in SOURCES:
            yield path.name, TransientSourceEvaluator(path.read_text(encoding="utf-8"))

    def assert_bounded(self, model):
        for field in REGISTRY:
            self.assertEqual(len(model.globals[field]), 24)
        owners = [owner for owner in model.globals[REGISTRY[0]] if owner is not None]
        self.assertEqual(len(owners), len(set(owners)))

    def test_240_identities_and_twelve_departures_release_all_transients_without_local_state(self):
        for source, model in self.models():
            with self.subTest(source=source):
                active = []
                for number in range(240):
                    if len(active) == 12:
                        departed = active.pop(0)
                        model.players[departed] = {"exists": False}
                        model.reap()
                    identity = f"player-{number}"
                    model.add_player(identity, dummy=number % 3 == 0)
                    for field in FIELDS:
                        self.assertTrue(model.create(identity, field))
                    active.append(identity)
                    self.assert_bounded(model)
                    self.assertEqual(len(model.live_texts), len(active) * 3)
                for identity in active:
                    model.players[identity] = {"exists": False}
                model.reap()
                self.assertFalse(model.live_texts)
                self.assertEqual(len(model.destroyed_texts), 720)
                self.assertTrue(all(owner is None for owner in model.globals[REGISTRY[0]]))
                self.assert_bounded(model)
                writes = len(model.array_writes)
                model.reap()
                self.assertEqual(len(model.array_writes), writes, "empty rows must not be rewritten")
                self.assertEqual(len(model.destroyed_texts), 720)

    def test_reaper_then_recycled_id_survives_stale_local_cleanup_for_every_text_kind(self):
        for source, model in self.models():
            for field, (_, kind, _) in FIELDS.items():
                with self.subTest(source=source, field=field):
                    model.add_player("departed")
                    model.add_player("survivor")
                    self.assertTrue(model.create("departed", field))
                    handle = model.players["departed"][field]
                    model.players["departed"]["exists"] = False  # Deliberately retain stale locals.
                    model.reap()
                    model.next_text = handle
                    self.assertTrue(model.create("survivor", field))
                    destroyed = len(model.destroyed_texts)
                    model.close("departed", field)
                    model.reap("departed")
                    model.close("departed", field)
                    self.assertEqual(model.live_texts[(kind, handle)], "survivor")
                    self.assertEqual(len(model.destroyed_texts), destroyed)
                    model.close("survivor", field)
                    self.assertFalse(model.live_texts)
                    model.reap("survivor")

    def test_normal_close_clears_mirror_before_another_owner_reuses_the_id(self):
        for source, model in self.models():
            for field, (array, kind, _) in FIELDS.items():
                with self.subTest(source=source, field=field):
                    model.add_player("alice")
                    model.add_player("bob", dummy=True)
                    self.assertTrue(model.create("alice", field))
                    handle = model.players["alice"][field]
                    model.close("alice", field)
                    slot = model.globals[REGISTRY[0]].index("alice")
                    self.assertEqual(model.globals[array][slot], 0)
                    model.next_text = handle
                    self.assertTrue(model.create("bob", field))
                    model.players["alice"] = {"exists": False}
                    model.reap()
                    self.assertEqual(model.live_texts[(kind, handle)], "bob")
                    model.close("bob", field)
                    model.reap("bob")

    def test_full_registry_creates_nothing_then_wakes_after_reaping_capacity(self):
        for source, model in self.models():
            with self.subTest(source=source):
                for index in range(24):
                    identity = f"occupied-{index}"
                    model.add_player(identity)
                    self.assertTrue(model.create(identity, "LuckVisionText"))
                model.add_player("waiting")
                snapshot = copy.deepcopy(model.live_texts)
                for field in FIELDS:
                    self.assertFalse(model.create("waiting", field))
                    self.assertFalse(model.create("waiting", field, check_capacity=False))
                    self.assertEqual(model.live_texts, snapshot)
                model.players["occupied-3"] = {"exists": False}
                # The normal ongoing creator stays false until the 1 Hz reaper frees its row.
                self.assertFalse(model.create("waiting", "LuckVisionText"))
                model.reap()
                self.assertTrue(model.create("waiting", "LuckVisionText"))
                model.add_player("lazy-waiting")
                model.players["occupied-7"] = {"exists": False}
                self.assertTrue(model.create("lazy-waiting", "LuckVisionText", check_capacity=False))
                self.assert_bounded(model)

    def test_null_owner_with_retained_handles_is_reaped_before_reallocation(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.add_player("old-bot", dummy=True)
                self.assertTrue(model.create("old-bot", "LuckVisionText"))
                slot = model.globals[REGISTRY[0]].index("old-bot")
                old_id = model.players["old-bot"]["LuckVisionText"]
                model.players["old-bot"] = {"exists": False}
                model.globals[REGISTRY[0]][slot] = None  # Engine references may collapse to Null.
                model.add_player("new-bot", dummy=True)
                self.assertTrue(model.create("new-bot", "LuckVisionText"))
                self.assertIn((("In-World Text", old_id), "old-bot"), model.destroyed_texts)
                self.assertEqual(len(model.live_texts), 1)
                self.assert_bounded(model)

    def test_live_team_cleanup_releases_only_selected_owner_and_is_idempotent(self):
        for source, model in self.models():
            with self.subTest(source=source):
                for identity in ("changing-team", "other-human", "dummy"):
                    model.add_player(identity, dummy=identity == "dummy")
                    for field in FIELDS:
                        self.assertTrue(model.create(identity, field))
                model.reap("changing-team")
                self.assertEqual(len(model.live_texts), 6)
                self.assertNotIn("changing-team", model.globals[REGISTRY[0]])
                snapshot = copy.deepcopy(model.live_texts)
                model.reap("changing-team")
                self.assertEqual(model.live_texts, snapshot)
                self.assertEqual(len(model.destroyed_texts), 3)

    @staticmethod
    def walk_actions(nodes, guards=()):
        """Yield sibling position and only the positive branch guards in force."""
        for index, (token, body, otherwise) in enumerate(nodes):
            yield nodes, index, guards
            if body is not None:
                nested = guards + (token,) if token.startswith("If(") else guards
                yield from TransientOwnershipTests.walk_actions(body, nested)
                yield from TransientOwnershipTests.walk_actions(otherwise, guards)

    def test_every_local_destroy_checks_owner_then_mirror_and_clears_that_mirror(self):
        local_destroy = re.compile(
            r"Destroy (HUD Text|In-World Text)\(((?:Event Player|Global\.\w+)\."
            r"(LuckEffectHud|TravelText|LuckVisionText))\)")
        for source, model in self.models():
            counts = dict.fromkeys(FIELDS, 0)
            for rule in model.rules:
                actions = validator.rule_block(rule, "actions")
                if not local_destroy.search(actions):
                    continue
                nodes = statements(actions)
                for siblings, index, guards in self.walk_actions(nodes):
                    match = local_destroy.fullmatch(siblings[index][0])
                    if match is None:
                        continue
                    kind, local, field = match.groups()
                    owner = local.rsplit(".", 1)[0]
                    array, expected_kind, _ = FIELDS[field]
                    lookup = f"Index Of Array Value(Global.TemporaryTextOwners, {owner})"
                    owner_guard = f"If({lookup} >= 0)"
                    mirror = f"Global.{array}[{lookup}]"
                    mirror_guard = f"If({mirror} == {local})"
                    with self.subTest(source=source, rule=rule.name, local=local):
                        self.assertEqual(kind, expected_kind)
                        self.assertIn(owner_guard, guards)
                        self.assertIn(mirror_guard, guards)
                        self.assertLess(guards.index(owner_guard), guards.index(mirror_guard),
                                        "owner must be found before reading its mirror")
                        self.assertLess(index + 1, len(siblings))
                        self.assertEqual(siblings[index + 1], (f"{mirror} = 0", None, None),
                                         "destroy must clear the same owner's mirror immediately")
                    counts[field] += 1
            for field, count in counts.items():
                self.assertGreater(count, 1, f"{source}: missing cleanup coverage for {field}")

    def test_all_three_captures_allocate_before_create_and_persist_immediately(self):
        for source, model in self.models():
            counts = dict.fromkeys(FIELDS, 0)
            for rule in model.rules:
                actions = validator.rule_block(rule, "actions")
                if not any(f"Event Player.{field} = Last Text ID;" in actions for field in FIELDS):
                    continue
                nodes = statements(actions)
                for siblings, index, _ in self.walk_actions(nodes):
                    capture = re.fullmatch(
                        r"Event Player\.(LuckEffectHud|TravelText|LuckVisionText) = Last Text ID",
                        siblings[index][0])
                    if capture is None:
                        continue
                    field = capture[1]
                    array, kind, _ = FIELDS[field]
                    with self.subTest(source=source, field=field, rule=rule.name):
                        self.assertGreaterEqual(index, 3)
                        self.assertTrue(siblings[index - 1][0].startswith(f"Create {kind}("))
                        allocation_index = index - 2
                        if field == "TravelText":
                            # The creation deadline is armed after ownership is
                            # secured, so a failed allocation consumes no delay.
                            self.assertEqual(siblings[allocation_index], (
                                "Event Player.NextTargetTextTime = Total Time Elapsed + 0.250",
                                None, None))
                            allocation_index -= 1
                        self.assertEqual(siblings[allocation_index - 1], (
                            "Global.TextCleanupIndex = Index Of Array Value("
                            "Global.TemporaryTextOwners, Event Player)", None, None))
                        allocation, body, otherwise = siblings[allocation_index]
                        self.assertEqual(allocation, "If(Global.TextCleanupIndex < 0)")
                        self.assertFalse(otherwise)
                        self.assertEqual(body[0], (
                            "Global.TextCleanupIndex = Index Of Array Value("
                            "Global.TemporaryTextOwners, Null)", None, None))
                        self.assertEqual(body[-2], (
                            "Abort If(Global.TextCleanupIndex < 0)", None, None))
                        self.assertEqual(body[-1], (
                            "Global.TemporaryTextOwners[Global.TextCleanupIndex] = Event Player",
                            None, None))
                        self.assertLess(index + 1, len(siblings))
                        self.assertEqual(siblings[index + 1], (
                            f"Global.{array}[Index Of Array Value(Global.TemporaryTextOwners, "
                            f"Event Player)] = Event Player.{field}", None, None))
                        allocation_tokens = [items[position][0] for items, position, _
                                             in self.walk_actions([siblings[allocation_index]])]
                        self.assertFalse(any(token.startswith(("Wait(", "Loop"))
                                             for token in allocation_tokens))
                    counts[field] += 1
            self.assertEqual(counts, dict.fromkeys(FIELDS, 1), source)


if __name__ == "__main__":
    unittest.main()
