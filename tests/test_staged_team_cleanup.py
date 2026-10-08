"""Execute the real staged worker with controlled changes at both Waits.

This is a source-level lifecycle model, not an Overwatch engine/crash emulator.
It retains Event Player identity across waits and reads shared lease, roster and
cleanup state afresh. Native entity/spawn changes are explicit test inputs.
"""

import unittest

from tests.test_roster_rejoin_regressions import SOURCES
from tests.test_team_transition_recent_features import TeamTransitionEvaluator


class StagedTeamCleanupTests(unittest.TestCase):
    def sources(self):
        for path, _, _ in SOURCES:
            yield path.name, path.read_text(encoding="utf-8")

    def paused(self, source, boundary, other=False):
        model = TeamTransitionEvaluator(source)
        model.add("changing")
        if other:
            model.add("observer")
        model.change_team("changing", 2, 100.1)
        self.assertTrue(model.start_worker("changing", 100.6, reserve=True))
        if boundary == 2:
            self.assertTrue(model.resume_worker("changing", 100.65))
        self.assertIn("changing", model.workers)
        return model, 100.625 if boundary == 1 else 100.675, 100.65 if boundary == 1 else 100.7

    def test_plain_join_separates_quiet_cleanup_and_setup_before_new_hud(self):
        for name, source in self.sources():
            with self.subTest(source=name):
                model = TeamTransitionEvaluator(source)
                state = model.add("changing")
                old_hud = model.globals["PlayerListHudIds"][0]
                self.assertFalse(state["MenuOpen"])
                self.assertEqual(state["IconIndex"], 0)
                self.assertEqual(model.globals["SuperPunchPlayers"], [])
                model.change_team("changing", 2, 100.1)
                self.assertTrue(model.start_worker("changing", 100.6, reserve=True))
                self.assertEqual(model.phase_calls, [("changing", "QuiescePlayer", 100.6)])
                self.assertEqual(model.destroyed, [])
                self.assertEqual(model.globals["HumanPlayers"], ["changing"])
                self.assertFalse(model.resume_worker("changing", 100.649))
                self.assertFalse(model.register_ready("changing", 100.649))
                self.assertTrue(model.resume_worker("changing", 100.65))
                self.assertEqual(model.destroyed, [old_hud])
                self.assertEqual(model.globals["HumanPlayers"], [])
                self.assertFalse(state["IsPrepared"])
                self.assertFalse(model.register_ready("changing", 100.699))
                self.assertEqual(model.created, [old_hud])
                self.assertTrue(model.resume_worker("changing", 100.7))
                self.assertTrue(state["IsPrepared"])
                self.assertEqual(model.phase_calls,
                                 [("changing", "QuiescePlayer", 100.6),
                                  ("changing", "CleanupPlayer", 100.65),
                                  ("changing", "PreparePlayer", 100.7)])
                self.assertTrue(model.register_ready("changing", 100.7))
                self.assertEqual(len(model.created), 2)
                self.assertNotEqual(model.globals["PlayerListHudIds"][0], old_hud)
                self.assertEqual(model.icons, {})
                self.assertEqual(model.globals["SuperPunchPlayers"], [])

    def test_leave_or_despawn_at_either_wait_cancels_remaining_phases(self):
        for name, source in self.sources():
            for boundary in (1, 2):
                for field in ("exists", "spawned"):
                    with self.subTest(source=name, boundary=boundary, field=field):
                        model, interruption, wake = self.paused(source, boundary)
                        calls, destroyed = list(model.phase_calls), list(model.destroyed)
                        model.native_update("changing", interruption, **{field: False})
                        self.assertNotIn("changing", model.workers)
                        self.assertFalse(model.resume_worker("changing", wake))
                        self.assertEqual(model.phase_calls, calls)
                        self.assertEqual(model.destroyed, destroyed)
                        self.assertFalse(model.players["changing"]["IsPrepared"])

    def test_transient_native_loss_cannot_revive_an_aborted_wait(self):
        for name, source in self.sources():
            for boundary in (1, 2):
                for field in ("exists", "spawned"):
                    with self.subTest(source=name, boundary=boundary, field=field):
                        model, interruption, wake = self.paused(source, boundary)
                        calls = list(model.phase_calls)
                        model.native_update("changing", interruption, **{field: False})
                        model.native_update("changing", interruption + 0.01, **{field: True})
                        self.assertNotIn("changing", model.workers)
                        self.assertFalse(model.resume_worker("changing", wake))
                        self.assertEqual(model.phase_calls, calls)

    def test_team_change_uses_registered_detector_then_unregistered_fast_invalidation(self):
        for name, source in self.sources():
            for boundary in (1, 2):
                with self.subTest(source=name, boundary=boundary):
                    model, interruption, wake = self.paused(source, boundary)
                    calls, destroyed = list(model.phase_calls), list(model.destroyed)
                    registered = model.change_team("changing", 1, interruption)
                    self.assertEqual(registered, boundary == 1)
                    model.fast_tick("changing", interruption)
                    self.assertEqual(model.players["changing"]["TeamCycleTargetTeam"], 1)
                    self.assertGreater(model.players["changing"]["TeamCycleDeadline"], wake)
                    self.assertIsNone(model.globals["TeamCyclePlayer"])
                    self.assertNotIn("changing", model.workers)
                    self.assertFalse(model.resume_worker("changing", wake))
                    self.assertEqual(model.phase_calls, calls)
                    self.assertEqual(model.destroyed, destroyed)
                    deadline = model.players["changing"]["TeamCycleDeadline"]
                    model.fast_tick("changing", deadline + 0.001)
                    self.assertEqual(model.globals["TeamCyclePlayer"], "changing")
                    self.assertFalse(model.resume_worker("changing", deadline + 0.001))
                    self.assertEqual(model.globals["TeamCyclePlayer"], "changing")
                    self.assertFalse(model.players["changing"]["IsPrepared"])

    def test_team_out_and_back_requires_a_fresh_stability_deadline(self):
        for name, source in self.sources():
            for boundary in (1, 2):
                with self.subTest(source=name, boundary=boundary):
                    model, interruption, wake = self.paused(source, boundary)
                    calls = list(model.phase_calls)
                    model.change_team("changing", 1, interruption)
                    model.fast_tick("changing", interruption)
                    model.change_team("changing", 2, interruption + 0.01)
                    model.fast_tick("changing", interruption + 0.01)
                    state = model.players["changing"]
                    self.assertEqual(state["TeamCycleTargetTeam"], 2)
                    self.assertGreater(state["TeamCycleDeadline"], wake)
                    self.assertNotIn("changing", model.workers)
                    self.assertFalse(model.resume_worker("changing", wake))
                    self.assertFalse(model.start_worker("changing", wake, reserve=True))
                    self.assertEqual(model.phase_calls, calls)
                    self.assertFalse(state["IsPrepared"])

    def test_new_owner_lease_survives_old_worker_resume_at_either_boundary(self):
        for name, source in self.sources():
            for boundary in (1, 2):
                with self.subTest(source=name, boundary=boundary):
                    model, interruption, wake = self.paused(source, boundary, other=True)
                    model.change_team("observer", 2, 100.12)
                    model.globals["TeamCyclePlayer"] = "observer"
                    model.observe_waits(interruption)
                    self.assertNotIn("changing", model.workers)
                    self.assertTrue(model.start_worker("observer", interruption))
                    observer_wait = model.workers["observer"]["waiting"]
                    self.assertFalse(model.resume_worker("changing", wake))
                    self.assertEqual(model.globals["TeamCyclePlayer"], "observer")
                    self.assertEqual(model.workers["observer"]["waiting"], observer_wait)
                    self.assertFalse(model.players["changing"]["IsPrepared"])
                    self.assertFalse(any(owner == "changing" and routine == "PreparePlayer"
                                         for owner, routine, _ in model.phase_calls))

    def test_post_wait_native_change_is_caught_by_explicit_wake_guard(self):
        for name, source in self.sources():
            for boundary in (1, 2):
                with self.subTest(source=name, boundary=boundary):
                    model, _, wake = self.paused(source, boundary)
                    calls, destroyed = list(model.phase_calls), list(model.destroyed)
                    self.assertFalse(model.resume_worker("changing", wake, wake_changes={"exists": False}))
                    self.assertNotIn("changing", model.workers)
                    self.assertEqual(model.phase_calls, calls)
                    self.assertEqual(model.destroyed, destroyed)
                    self.assertFalse(model.players["changing"]["IsPrepared"])

    def test_twelve_queued_plain_owners_keep_identity_and_cleanup_scratch_separate(self):
        for name, source in self.sources():
            with self.subTest(source=name):
                model = TeamTransitionEvaluator(source)
                owners = [f"human-{index}" for index in range(12)]
                for owner in owners:
                    model.add(owner)
                    model.change_team(owner, 2, 100.1)
                old_huds = set(model.globals["PlayerListHudIds"])
                for index, owner in enumerate(owners):
                    now = 100.6 + index * 0.351
                    for queued in owners[index:]:
                        model.fast_tick(queued, now)
                    self.assertEqual(model.globals["TeamCyclePlayer"], owner)
                    self.assertTrue(model.start_worker(owner, now))
                    # Interleave another player's scheduler context while this
                    # worker sleeps; resumed cleanup must still own Event Player.
                    if index + 1 < len(owners):
                        model.fast_tick(owners[index + 1], now + 0.025)
                    self.assertTrue(model.resume_worker(owner, now + 0.05))
                    self.assertIsNone(model.globals["CleanupSubject"])
                    self.assertEqual(model.globals["CleanupPlayerIndex"], -1)
                    self.assertTrue(model.resume_worker(owner, now + 0.1))
                    self.assertTrue(model.register_ready(owner, now + 0.1))
                    model.fast_tick(owner, now + 0.1)
                    self.assertIsNone(model.globals["TeamCyclePlayer"])
                    self.assertFalse(model.players[owner]["TeamChangeProcessed"])
                    self.assertEqual(len(model.globals["HumanPlayers"]), 12)
                    self.assertEqual(model.globals["AvailableHudSlots"], [])
                self.assertCountEqual(model.destroyed, old_huds)
                self.assertEqual(len(model.destroyed), 12)
                self.assertEqual(len(set(model.globals["PlayerListHudIds"])), 12)
                self.assertTrue(old_huds.isdisjoint(model.globals["PlayerListHudIds"]))
                self.assertEqual(model.globals["SuperPunchPlayers"], [])
                self.assertEqual(model.icons, {})
                self.assertEqual(model.workers, {})
                for owner in owners:
                    self.assertEqual([routine for current, routine, _ in model.phase_calls if current == owner],
                                     ["QuiescePlayer", "CleanupPlayer", "PreparePlayer"])


if __name__ == "__main__":
    unittest.main()
