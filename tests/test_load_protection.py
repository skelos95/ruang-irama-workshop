"""Execute real load/feedback guards from both Workshop exports.

Server Load, Total Time Elapsed, rendering and Slow Motion are simulated engine
values/actions. These tests verify thresholds, state transitions and bounded
feedback, not native wall-clock timing, server-load reduction or crash immunity.
"""
import re
import unittest

from tests.test_menu_load_regressions import MenuLoadEvaluator
from tests.test_roster_rejoin_regressions import SOURCES
from tools import validate_workshop as validator


class LoadEvaluator(MenuLoadEvaluator):
    def __init__(self, source):
        super().__init__(source)
        self.load = 0
        self.speed_changes = []
        self.feedback = []
        self.globals.update(WaktuBebanTinggi=-1, PerlindunganBebanAktif=False)
        actions = validator.rule_block(self.rule("04g"), "actions")
        start = actions.index("If(Global.PerlindunganBebanAktif == True);")
        stop = actions.index("If(Global.LangkahPenjadwal % 2 == 0);", start)
        self.load_actions = actions[start:stop]

    def resolve(self, name):
        if name == "ServerLoad":
            return self.load
        return super().resolve(name)

    def assign(self, target, value):
        if target == "Global._testSpeed":
            self.speed_changes.append((self.now, value))
        elif target == "Global._testFeedback":
            self.feedback.append((self.now, value))
        super().assign(target, value)

    def execute(self, actions):
        # Only native side effects are substituted. Conditions, assignments and
        # control flow still execute the statements extracted from the source.
        for name, replacement in (("Set Slow Motion", "Global._testSpeed = {0};"),
                                  ("Play Effect", "Global._testFeedback = Event Player;")):
            for call in reversed(list(validator.iter_calls(actions, name))):
                statement = replacement.format(call.args[0])
                end = call.end + (1 if actions[call.end:call.end + 1] == ";" else 0)
                actions = actions[:call.start] + statement + actions[end:]
        super().execute(actions)

    def tick(self, now, load):
        self.now, self.load = now, load
        self.execute(self.load_actions)

    def restore(self, prefix):
        actions = validator.rule_block(self.rule(prefix), "actions")
        start = actions.index("Global.WaktuBebanTinggi = -1;")
        last = next(call for call in validator.iter_calls(actions, "Set Slow Motion")
                    if call.start > start)
        self.execute(actions[start:last.end + 1])

    def lifecycle_feedback_reset(self, prefix, owner):
        self.event_player = owner
        actions = validator.rule_block(self.rule(prefix), "actions")
        statement = re.search(r"Event Player\.WaktuEfekMenuBerikut = [^;]+;", actions)
        if statement is None:
            raise AssertionError("Lifecycle must reset the feedback deadline")
        self.execute(statement[0])


class LoadProtectionTests(unittest.TestCase):
    def models(self):
        for path, _, _ in SOURCES:
            yield path.name, LoadEvaluator(path.read_text(encoding="utf-8"))

    def test_transient_spikes_and_load_of_200_reset_the_continuous_interval(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.tick(0, 201)
                model.tick(2.9, 300)
                self.assertEqual(model.speed_changes, [])
                model.tick(3, 200)
                self.assertEqual(model.globals["WaktuBebanTinggi"], -1)
                model.tick(3.05, 201)
                model.tick(5.9, 300)
                self.assertEqual(model.speed_changes, [])
                model.tick(6.1, 201)
                self.assertEqual(model.speed_changes, [(6.1, 10)])

    def test_time_zero_is_valid_and_activation_uses_elapsed_time_not_tick_count(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.tick(0, 201)
                for _ in range(100):
                    model.tick(2.99, 201)
                self.assertEqual(model.speed_changes, [])
                model.tick(3, 201)
                self.assertEqual(model.speed_changes, [(3, 10)])
                self.assertTrue(model.globals["PerlindunganBebanAktif"])
                # A delayed scheduler observation still triggers once the
                # actual elapsed timestamp crosses the sustained interval.
                model.tick(100, 201)
                self.assertEqual(model.speed_changes, [(3, 10)])

    def test_active_protection_holds_at_100_and_recovers_strictly_below_100(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.tick(10, 201)
                model.tick(13, 201)
                for now, load in ((14, 300), (15, 200), (16, 150), (17, 100)):
                    model.tick(now, load)
                self.assertEqual(model.speed_changes, [(13, 10)])
                model.tick(17.05, 99.9)
                self.assertEqual(model.speed_changes, [(13, 10), (17.05, 100)])
                self.assertFalse(model.globals["PerlindunganBebanAktif"])
                self.assertEqual(model.globals["WaktuBebanTinggi"], -1)
                model.tick(1000, 0)
                self.assertEqual(len(model.speed_changes), 2)

    def test_recovery_does_not_wait_for_time_and_reactivation_requires_new_interval(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.tick(20, 201)
                model.tick(23, 201)
                # Even an unchanged elapsed timestamp cannot hold recovery.
                model.tick(23, 99)
                model.tick(23, 201)
                model.tick(25.99, 201)
                self.assertEqual(model.speed_changes, [(23, 10), (23, 100)])
                model.tick(26, 201)
                model.tick(26, 99)
                self.assertEqual(model.speed_changes,
                                 [(23, 10), (23, 100), (26, 10), (26, 100)])

    def test_initialization_and_restart_explicitly_restore_normal_speed(self):
        for source, model in self.models():
            for prefix in ("00", "00c"):
                with self.subTest(source=source, rule=prefix):
                    model.globals.update(WaktuBebanTinggi=123, PerlindunganBebanAktif=True)
                    model.restore(prefix)
                    self.assertEqual(model.speed_changes[-1][1], 100)
                    self.assertFalse(model.globals["PerlindunganBebanAktif"])
                    self.assertEqual(model.globals["WaktuBebanTinggi"], -1)
                    if prefix == "00c":
                        body = model.rule(prefix).body
                        self.assertLess(body.index("Set Slow Motion(100)"),
                                        body.index("Restart Match"))

    def test_twelve_players_share_apply_reset_budget_only_with_themselves(self):
        for source, model in self.models():
            with self.subTest(source=source):
                owners = [f"player{index}" for index in range(12)]
                for owner in owners:
                    model.add(owner, WaktuEfekMenuBerikut=0)
                for step in range(32):
                    model.now = step / 32
                    for index, owner in enumerate(owners):
                        model.run("93a" if (step + index) % 2 else "93b", owner)
                for owner in owners:
                    self.assertEqual([time for time, actor in model.feedback if actor == owner],
                                     [0, .25, .5, .75])
                self.assertEqual(len(model.feedback), 48)

    def test_overload_discards_cosmetic_feedback_without_queue_or_extra_wait(self):
        for source, model in self.models():
            with self.subTest(source=source):
                owner = model.add("player", WaktuEfekMenuBerikut=0)
                model.globals["PerlindunganBebanAktif"] = True
                model.now = 10
                model.run("93a", "player")
                model.run("93b", "player")
                self.assertEqual(model.feedback, [])
                self.assertEqual(owner["WaktuEfekMenuBerikut"], 0)
                model.globals["PerlindunganBebanAktif"] = False
                model.run("93b", "player")
                model.run("93a", "player")
                self.assertEqual(model.feedback, [(10, "player")])
                self.assertEqual(owner["WaktuEfekMenuBerikut"], 10.25)
                for prefix in ("93a", "93b"):
                    body = model.rule(prefix).body
                    self.assertNotRegex(body, r"\b(?:Wait|Abort|Loop)\b")

    def test_player_lifecycle_resets_cooldown_without_touching_other_owners(self):
        for source, model in self.models():
            for prefix in ("93b2", "94"):
                with self.subTest(source=source, rule=prefix):
                    first = model.add("first", WaktuEfekMenuBerikut=999)
                    other = model.add("other", WaktuEfekMenuBerikut=500)
                    model.lifecycle_feedback_reset(prefix, "first")
                    self.assertEqual(first["WaktuEfekMenuBerikut"], 0)
                    self.assertEqual(other["WaktuEfekMenuBerikut"], 500)


if __name__ == "__main__":
    unittest.main()
