"""Execute the source's first-hero deadline for both clipboard grammars.

The native force/release calls are recorded at the engine boundary. These tests
verify dispatch and ownership, not whether a particular game build imports the
Shion enum or how its client applies a force followed by an immediate release.
"""

import re
import unittest

from tools import validate_workshop as validator
from tests.test_audit_lifecycle import AuditLifecycleEvaluator, project, statements
from tests.test_roster_rejoin_regressions import SOURCES


class HeroSelectionEvaluator(AuditLifecycleEvaluator):
    NATIVE_ACTIONS = ("StartForcingPlayerToBeHero", "StopForcingPlayerToBeHero")

    def __init__(self, source):
        super().__init__(source)
        self.native = []
        scheduler = next(rule for rule in self.rules if rule.name.startswith("04g -"))
        self.scheduler = project(
            statements(validator.rule_block(scheduler, "actions")), self.keep
        )
        fast = validator.rule_by_subroutine(self.rules, "ProcessPlayerFastState")
        self.fast = project(statements(validator.rule_block(fast, "actions")), self.keep)
        setup = validator.rule_by_subroutine(self.rules, "PreparePlayer")
        self.setup = project(statements(validator.rule_block(setup, "actions")), self.keep)

    @staticmethod
    def keep(token):
        return bool(
            re.match(r"Global\.(ActivePlayer|PlayerListSnapshot) =", token)
            or re.match(
                r"(?:Global\.ActivePlayer|Event Player)\."
                r"(?:AutoHeroSelectionDeadline|AutoHeroSelectionComplete) =", token
            )
            or token.startswith("Start Forcing Player To Be Hero(")
            or token.startswith("Stop Forcing Player To Be Hero(")
            or token == "Call Subroutine(ProcessPlayerFastState)"
        )

    def add(self, identity, team=1, **changes):
        state = dict(
            team=team, exists=True, dummy=False, IsAutomaticBot=False,
            spawned=False, alive=False, IsHuman=False, slot=0,
            AutoHeroSelectionDeadline=0, AutoHeroSelectionComplete=False,
            hero=None, forced_hero=None,
        )
        state.update(changes)
        self.players[identity] = state
        return state

    def resolve(self, name):
        constants = {"Team1": 1, "Team2": 2, "Shion": "Shion"}
        if name in constants:
            return constants[name]
        return super().resolve(name)

    def call(self, name, args):
        if name == "Hero":
            return args[0]
        if name == "HeroOf":
            return self.players[args[0]]["hero"]
        if name in self.NATIVE_ACTIONS:
            self.native.append((name, *args))
            state = self.players[args[0]]
            if name == "StartForcingPlayerToBeHero":
                state["forced_hero"] = args[1]
                state["hero"] = args[1]
            else:
                state["forced_hero"] = None
            return None
        return super().call(name, args)

    def execute(self, nodes):
        for node in nodes:
            if node[0] == "Call Subroutine(ProcessPlayerFastState)":
                self.calls.append((self.globals["ActivePlayer"], "ProcessPlayerFastState"))
                self.execute(self.fast)
            elif node[0].startswith(("Start Forcing Player To Be Hero(",
                                     "Stop Forcing Player To Be Hero(")):
                self.evaluate(node[0])
            elif super().execute([node]):
                return True
        return False

    def tick(self, now, tick=20):
        self.now = now
        self.globals["SchedulerStep"] = tick
        self.execute(self.scheduler)

    def prepare(self, identity):
        self.event_player = identity
        self.execute(self.setup)

    def assignments(self, identity):
        return [event for event in self.native
                if event[0] == "StartForcingPlayerToBeHero" and event[1] == identity]


class HeroSelectionTimeoutTests(unittest.TestCase):
    def models(self):
        for path, _, _ in SOURCES:
            yield path.name, HeroSelectionEvaluator(path.read_text(encoding="utf-8"))

    def test_unclassified_player_starts_deadline_without_a_roster_slot(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("waiting")
                model.tick(10)
                self.assertEqual(state["AutoHeroSelectionDeadline"], 70)
                self.assertFalse(state["AutoHeroSelectionComplete"])
                self.assertEqual(model.globals["HumanPlayers"], [])
                self.assertEqual(model.globals["AvailableHudSlots"], list(range(12)))
                self.assertEqual(model.native, [])

    def test_exact_sixty_second_boundary_assigns_shion_once_and_releases_force(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("waiting")
                model.tick(10)
                model.tick(69.999)
                self.assertEqual(model.native, [])
                model.tick(70)
                self.assertEqual(model.native, [
                    ("StartForcingPlayerToBeHero", "waiting", "Shion"),
                    ("StopForcingPlayerToBeHero", "waiting"),
                ])
                self.assertTrue(state["AutoHeroSelectionComplete"])
                self.assertEqual(state["AutoHeroSelectionDeadline"], 0)
                self.assertIsNone(state["forced_hero"])
                for now in (70.05, 71, 120, 3600):
                    model.tick(now)
                self.assertEqual(len(model.assignments("waiting")), 1)

    def test_deadlines_use_elapsed_time_even_if_scheduler_resumes_late(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.add("waiting")
                model.tick(100)
                model.tick(170)
                self.assertEqual(model.assignments("waiting"),
                                 [("StartForcingPlayerToBeHero", "waiting", "Shion")])

    def test_deadline_arms_on_first_fast_tick_but_expiry_runs_only_at_one_hz(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("waiting")
                model.tick(1, 1)
                self.assertEqual(state["AutoHeroSelectionDeadline"], 61)
                for tick in range(2, 20):
                    model.tick(61, tick)
                self.assertEqual(model.native, [])
                model.tick(61, 20)
                self.assertEqual(len(model.assignments("waiting")), 1)

    def test_one_hz_expiry_is_staggered_by_entity_slot(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.add("slot-zero", slot=0)
                model.add("slot-five", slot=5)
                model.tick(1, 1)
                model.tick(61, 20)
                self.assertEqual(len(model.assignments("slot-zero")), 1)
                self.assertEqual(model.assignments("slot-five"), [])
                model.tick(61.25, 25)
                self.assertEqual(len(model.assignments("slot-five")), 1)

    def test_manual_spawn_before_timeout_cancels_assignment(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("waiting")
                model.tick(10)
                state.update(spawned=True, alive=True, hero="Ana")
                model.tick(69)
                self.assertTrue(state["AutoHeroSelectionComplete"])
                self.assertEqual(state["AutoHeroSelectionDeadline"], 0)
                model.tick(1000)
                self.assertEqual(model.native, [])
                self.assertEqual(state["hero"], "Ana")

    def test_manual_spawn_at_deadline_wins_over_default(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("waiting")
                model.tick(10)
                state.update(spawned=True, hero="Mercy")
                model.tick(70)
                self.assertEqual(model.native, [])
                self.assertEqual(state["hero"], "Mercy")

    def test_setup_marks_first_selection_complete_before_classification(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("spawned", spawned=True, hero="Ana", AutoHeroSelectionDeadline=100)
                model.prepare("spawned")
                self.assertTrue(state["AutoHeroSelectionComplete"])
                self.assertEqual(state["AutoHeroSelectionDeadline"], 0)
                state.update(spawned=False, alive=False)
                model.tick(200)
                self.assertEqual(model.native, [])

    def test_death_and_team_quarantine_do_not_restart_finished_timeout(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("selected", spawned=True, hero="Ana")
                model.tick(1)
                state.update(team=2, spawned=False, alive=False, IsHuman=False)
                for now in (2, 62, 120):
                    model.tick(now)
                self.assertTrue(state["AutoHeroSelectionComplete"])
                self.assertEqual(state["AutoHeroSelectionDeadline"], 0)
                self.assertEqual(model.native, [])

    def test_unselected_team_switch_preserves_existing_deadline(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("waiting", team=1)
                model.tick(10)
                state["team"] = 2
                model.tick(45)
                self.assertEqual(state["AutoHeroSelectionDeadline"], 70)
                model.tick(70)
                self.assertEqual(len(model.assignments("waiting")), 1)

    def test_players_have_independent_deadlines_and_completed_state(self):
        for source, model in self.models():
            with self.subTest(source=source):
                first = model.add("first")
                model.tick(100)
                second = model.add("second", team=2)
                model.tick(125)
                self.assertEqual(first["AutoHeroSelectionDeadline"], 160)
                self.assertEqual(second["AutoHeroSelectionDeadline"], 185)
                model.tick(160)
                self.assertEqual(len(model.assignments("first")), 1)
                self.assertEqual(model.assignments("second"), [])
                self.assertFalse(second["AutoHeroSelectionComplete"])
                model.tick(185)
                self.assertEqual(len(model.assignments("second")), 1)

    def test_dummy_and_ai_entities_never_enter_hero_timeout_even_with_stale_state(self):
        for source, model in self.models():
            with self.subTest(source=source):
                dummy = model.add("dummy", dummy=True, AutoHeroSelectionDeadline=1)
                bot = model.add("ai", IsAutomaticBot=True, AutoHeroSelectionDeadline=1)
                model.tick(100)
                self.assertEqual(model.native, [])
                self.assertFalse(dummy["AutoHeroSelectionComplete"])
                self.assertFalse(bot["AutoHeroSelectionComplete"])

    def test_non_playing_team_does_not_start_timer_and_clears_pending_deadline(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("spectator", team=None)
                model.tick(10)
                self.assertEqual(state["AutoHeroSelectionDeadline"], 0)
                state["team"] = 1
                model.tick(20)
                self.assertEqual(state["AutoHeroSelectionDeadline"], 80)
                state["team"] = None
                model.tick(40)
                self.assertEqual(state["AutoHeroSelectionDeadline"], 0)
                model.tick(100)
                self.assertEqual(model.native, [])
                state["team"] = 2
                model.tick(101)
                self.assertEqual(state["AutoHeroSelectionDeadline"], 161)

    def test_departed_player_is_skipped_and_new_entity_gets_a_fresh_minute(self):
        for source, model in self.models():
            with self.subTest(source=source):
                old = model.add("old")
                model.tick(10)
                old["exists"] = False
                model.tick(70)
                self.assertEqual(model.native, [])
                new = model.add("new")
                model.tick(100)
                self.assertEqual(new["AutoHeroSelectionDeadline"], 160)
                model.tick(159)
                self.assertEqual(model.native, [])
                model.tick(160)
                self.assertEqual(len(model.assignments("new")), 1)
                self.assertEqual(model.assignments("old"), [])

    def test_released_default_does_not_issue_another_force_after_manual_change(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("waiting")
                model.tick(1)
                model.tick(61)
                self.assertIsNone(state["forced_hero"])
                state.update(hero="Mercy", spawned=True, alive=True)
                model.tick(500)
                self.assertEqual(state["hero"], "Mercy")
                self.assertEqual(len(model.assignments("waiting")), 1)


if __name__ == "__main__":
    unittest.main()
