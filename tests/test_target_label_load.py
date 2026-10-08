"""Execute target-label rules and their engine conditions from both sources.

The clock and rendering engine are simulated. This verifies allocation rate,
invalidation and captured subjects, not measured Workshop server load.
"""
import unittest

from tests.test_menu_load_regressions import MenuLoadEvaluator
from tests.test_roster_rejoin_regressions import SOURCES
from tools import validate_workshop as validator


VIEWS = (("13", "InspectionTarget", "InspectionTargetCandidate", "InspectionText"),
         ("19d", "TravelTextTarget", "TravelTargetCandidate", "TravelText"))


class LabelEvaluator(MenuLoadEvaluator):
    def __init__(self, source):
        super().__init__(source)
        self.rendered = {}
        self.allocations = []

    def resolve(self, name):
        if name in ("Crouch", "PrimaryFire", "SecondaryFire", "Interact", "Down",
                    "DisplayName", "NameColor"):
            return name
        return super().resolve(name)

    def call(self, name, args):
        if name == "IsButtonHeld": return self.players[args[0]].get("crouching", True)
        if name in ("IsDuplicating", "HeroBeingDuplicated", "HeroOf", "Health"):
            key = {"IsDuplicating": "duplicating", "HeroBeingDuplicated": "copy",
                   "HeroOf": "hero", "Health": "health"}[name]
            return self.players[args[0]].get(key, False)
        if name == "HeroIconString": return "icon:" + args[0]
        if name == "RoundToInteger": return int(args[0])
        return super().call(name, args)

    def capture(self, expression):
        # Replace each outer Evaluate Once exactly when the source creates the
        # text. Remaining hero/health expressions continue to reevaluate.
        captures = list(validator.iter_calls(expression, "Evaluate Once"))
        outer = [call for call in captures if not any(
            other.start < call.start and other.end >= call.end for other in captures)]
        for call in reversed(outer):
            key = f"_snapshot{len(self.literals)}"
            self.literals[key] = self.evaluate(call.args[0])
            expression = expression[:call.start] + key + expression[call.end:]
        return expression

    def run(self, prefix, owner):
        count = len(self.created_world)
        super().run(prefix, owner)
        if len(self.created_world) > count:
            create = next(validator.iter_calls(self.rule(prefix).body, "Create In-World Text"))
            for handle in self.created_world[count:]:
                self.allocations.append((self.now, owner, handle))
                self.rendered[handle] = self.capture(create.args[1])

    def tick(self, prefix, owner):
        if self.conditions(prefix, owner): self.run(prefix, owner)

    def viewer(self, prefix, owner="viewer"):
        return self.add(owner, MenuOpen=False, CameraMode=0,
                        CrouchTravelActive=prefix == "19d",
                        CrouchTravelEnabled=prefix == "19d",
                        TravelCursor=2, crouching=True)

    def target(self, name, **changes):
        return self.add(name, DisplayName=name, hero="Ana", health=200, **changes)


class TargetLabelLoadTests(unittest.TestCase):
    def models(self):
        for path, _, _ in SOURCES:
            yield path.name, LabelEvaluator(path.read_text(encoding="utf-8"))

    def test_rapid_target_changes_destroy_immediately_and_stable_pending_target_wakes(self):
        for source, model in self.models():
            for prefix, target, candidate, handle in VIEWS:
                with self.subTest(source=source, view=prefix):
                    player = model.viewer(prefix)
                    model.target("alice")
                    model.target("bob")
                    model.now = 10
                    player[candidate] = "alice"
                    model.tick(prefix, "viewer")
                    previous = player[handle]
                    self.assertIsNotNone(previous)
                    model.now = 10.1
                    player[candidate] = "bob"
                    model.tick(prefix, "viewer")
                    self.assertIn(previous, model.destroyed_world)
                    self.assertIsNone(player[handle])
                    self.assertEqual(player[target], "bob")
                    self.assertFalse(model.conditions(prefix, "viewer"))
                    model.now = 10.25
                    self.assertTrue(model.conditions(prefix, "viewer"))
                    model.tick(prefix, "viewer")
                    self.assertIsNotNone(player[handle])
                    self.assertNotEqual(player[handle], previous)
                    self.assertFalse(model.conditions(prefix, "viewer"))

    def test_twelve_viewers_cannot_allocate_more_than_four_labels_per_second(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.target("alice")
                model.target("bob")
                for index in range(12): model.viewer(VIEWS[index % 2][0], f"viewer{index}")
                for step in range(100):
                    model.now = step / 10
                    for index in range(12):
                        prefix, _, candidate, _ = VIEWS[index % 2]
                        owner = f"viewer{index}"
                        model.players[owner][candidate] = "alice" if step % 2 else "bob"
                        model.tick(prefix, owner)
                for index in range(12):
                    times = [time for time, owner, _ in model.allocations if owner == f"viewer{index}"]
                    self.assertTrue(times)
                    self.assertTrue(all(b - a >= .25 - 1e-9 for a, b in zip(times, times[1:])))
                    self.assertLessEqual(len(times), 40)
                live = set(model.created_world) - set(model.destroyed_world)
                self.assertLessEqual(len(live), 12)
                self.assertEqual(len(model.destroyed_world), len(set(model.destroyed_world)))

    def test_invalid_targets_are_removed_during_cooldown_without_cached_target_change(self):
        invalidations = ({"alive": False}, {"spawned": False}, {"exists": False},
                         {"IsHuman": False}, {"InspectionPrivacyActive": True},
                         {"PlayerListUpdatePending": True})
        for source, model in self.models():
            for prefix, target, candidate, handle in VIEWS:
                for invalid in invalidations:
                    with self.subTest(source=source, view=prefix, invalid=invalid):
                        player = model.viewer(prefix)
                        subject = model.target("alice")
                        model.now = 10
                        player[candidate] = "alice"
                        model.tick(prefix, "viewer")
                        previous = player[handle]
                        model.now = 10.05
                        subject.update(invalid)
                        self.assertTrue(model.conditions(prefix, "viewer"))
                        model.tick(prefix, "viewer")
                        self.assertIn(previous, model.destroyed_world)
                        self.assertIsNone(player[handle])
                        self.assertIsNone(player[target])
                        self.assertIsNone(player[candidate])
                        model.now = 11
                        self.assertFalse(model.conditions(prefix, "viewer"))

    def test_public_dummy_targets_remain_allowed(self):
        for source, model in self.models():
            for prefix, _, candidate, handle in VIEWS:
                for kind in ({"dummy": True}, {"IsAutomaticBot": True}):
                    with self.subTest(source=source, view=prefix, kind=kind):
                        player = model.viewer(prefix)
                        model.target("dummy", IsHuman=False, InspectionPrivacyActive=True, **kind)
                        player[candidate] = "dummy"
                        model.tick(prefix, "viewer")
                        self.assertIsNotNone(player[handle])

    def test_cooldown_survives_view_switch_close_death_and_menu_open(self):
        for source, model in self.models():
            for closing in ({"crouching": False}, {"alive": False}, {"MenuOpen": True}):
                with self.subTest(source=source, closing=closing):
                    player = model.viewer("19d")
                    model.target("alice")
                    player["TravelTargetCandidate"] = "alice"
                    model.now = 10
                    model.tick("19d", "viewer")
                    previous = player["TravelText"]
                    model.now = 10.05
                    player.update(closing)
                    model.tick("19g", "viewer")
                    self.assertIn(previous, model.destroyed_world)
                    self.assertIsNone(player["TravelText"])
                    self.assertEqual(player["NextTargetTextTime"], 10.25)
                    player.update(crouching=True, alive=True, MenuOpen=False,
                                  CrouchTravelEnabled=False, InspectionTargetCandidate="alice")
                    model.tick("13", "viewer")
                    self.assertIsNone(player["InspectionText"])
                    model.now = 10.25
                    model.tick("13", "viewer")
                    self.assertIsNotNone(player["InspectionText"])

    def test_live_hero_and_health_keep_the_captured_identity_when_candidate_changes(self):
        for source, model in self.models():
            for prefix, target, candidate, handle in VIEWS:
                with self.subTest(source=source, view=prefix):
                    player = model.viewer(prefix)
                    alice = model.target("alice")
                    model.target("bob")
                    player[candidate] = "alice"
                    model.tick(prefix, "viewer")
                    text = model.rendered[player[handle]]
                    self.assertEqual(model.evaluate(text), "icon:Ana alice | 200")
                    # Simulate a cache write before the engine dispatches the
                    # invalidation rule: all rendered fields still refer to Alice.
                    player[candidate] = player[target] = "bob"
                    alice.update(hero="Echo", health=37, duplicating=True, copy="Mercy")
                    self.assertEqual(model.evaluate(text), "icon:Mercy alice | 37")

    def test_inspection_close_and_death_cleanup_do_not_wait_for_the_label_deadline(self):
        for source, model in self.models():
            for closing in ({"crouching": False}, {"alive": False}, {"MenuOpen": True}):
                with self.subTest(source=source, closing=closing):
                    player = model.viewer("13")
                    model.target("alice")
                    player["InspectionTargetCandidate"] = "alice"
                    model.now = 10
                    model.tick("13", "viewer")
                    previous = player["InspectionText"]
                    model.now = 10.05
                    player.update(closing)
                    scheduler = validator.rule_by_subroutine(model.rules, "ProcessPlayerCycle")
                    position = scheduler.body.index("Destroy In-World Text(Global.ActivePlayer.InspectionText);")
                    branch = next(branch for branch in validator.conditional_branches_containing(scheduler.body, position)
                                  if "Global.ActivePlayer.InspectionActive == True" in branch.split(";", 1)[0])
                    # Bind the scheduler's player parameter to the same viewer;
                    # execute the complete cleanup branch, including its guard.
                    model.execute(branch.replace("Global.ActivePlayer", "Event Player"))
                    self.assertIn(previous, model.destroyed_world)
                    self.assertIsNone(player["InspectionText"])
                    self.assertFalse(player["InspectionActive"])
                    self.assertEqual(player["NextTargetTextTime"], 10.25)

    def test_narrow_validator_rejects_deadline_invalidation_and_identity_regressions(self):
        for source, model in self.models():
            original = "\n".join(rule.body for rule in model.rules)
            checks = validator.Checks()
            validator.validate_target_label_budget(checks, model.rules)
            self.assertEqual(checks.errors, [], source)
            for prefix, target, candidate, handle in VIEWS:
                rule = model.rule(prefix)
                identity = target if prefix == "13" else candidate
                mutations = (
                    ("Total Time Elapsed >= Event Player.NextTargetTextTime", "False", "risveglio"),
                    (f"Is Alive(Event Player.{target}) == False", "False", "invalidazione"),
                    ("Total Time Elapsed + 0.250", "Total Time Elapsed + 0.100", "0.250"),
                    ("Abort If(Total Time Elapsed < Event Player.NextTargetTextTime);", "", "distruzione"),
                    (f"Health(Evaluate Once(Event Player.{identity}))", f"Health(Event Player.{identity})", "identità"),
                )
                for before, after, diagnostic in mutations:
                    with self.subTest(source=source, view=prefix, mutation=before):
                        self.assertIn(before, rule.body)
                        mutated = original.replace(rule.body, rule.body.replace(before, after, 1), 1)
                        checks = validator.Checks()
                        validator.validate_target_label_budget(checks, validator.extract_rules(mutated))
                        self.assertTrue(any(diagnostic in error for error in checks.errors), checks.errors)


if __name__ == "__main__":
    unittest.main()
