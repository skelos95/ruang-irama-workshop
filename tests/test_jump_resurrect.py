"""Run the real Jump revive rules with controlled engine death/geometry results.

The source chooses when to revive, teleport and release the input latch. Native
navigation, resurrection and collision responses are test inputs; these tests do
not simulate Overwatch map collision or prove client event timing.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from tests.test_dummy_spawn_retry import SpawnEvaluator
from tests.test_fly_motion import Vector
from tools import validate_workshop as validator


ROOT = Path(__file__).resolve().parents[1]


class JumpEvaluator(SpawnEvaluator):
    """Reuse the source interpreter, stubbing only native effects and queries."""

    def __init__(self, source):
        super().__init__(source)
        self.events = []
        self.navigation_queries = []
        self.ray_queries = []
        self.navigation_result = Vector(100, 20, 40)
        self.ray_result = Vector(100, 20, 40)

    def add_player(self, identity, **changes):
        defaults = dict(Manusia=True, dummy=False, alive=True, jump=False,
                        BangkitLompatDipakai=False, FisikaHantuTerbangDiterapkan=True,
                        WaktuMulaiTerbangMaju=20, PerintahMenu=1, PerintahTeleportasi=1,
                        resurrect_alive=True, resurrect_position=None,
                        corpse_teleport_honored=True)
        defaults.update(changes)
        return super().add_player(identity, **defaults)

    def resolve(self, name):
        if name in ("Jump", "TerapkanFisikaHantuTerbang"):
            return name
        return super().resolve(name)

    def call(self, name, args):
        if name == "Button":
            return args[0]
        if name == "IsButtonHeld":
            if args[1] != "Jump":
                raise AssertionError(f"unexpected input: {args[1]}")
            return self.players[args[0]]["jump"]
        if name == "LastOf":
            return args[0][-1] if isinstance(args[0], list) else args[0]
        if name == "NearestWalkablePosition":
            self.navigation_queries.append((self.selected, args[0]))
            return self.navigation_result
        if name == "RayCastHitPosition":
            self.ray_queries.append((self.selected, tuple(args)))
            return self.ray_result
        if name == "Resurrect":
            player = self.players[args[0]]
            self.events.append((name, args[0], player["position"]))
            player["alive"] = player["resurrect_alive"]
            if player["resurrect_position"] is not None:
                player["position"] = player["resurrect_position"]
            return None
        if name == "Teleport":
            self.events.append((name, args[0], args[1]))
            player = self.players[args[0]]
            old_position = player["position"]
            result = super().call(name, args)
            if not player["alive"] and not player["corpse_teleport_honored"]:
                player["position"] = old_position
            return result
        if name == "RecordSubroutine":
            player = self.players[self.selected]
            self.events.append((args[0], self.selected, player["position"], player["alive"]))
            return None
        if name == "RecordMessage":
            self.events.append((name, args[0]))
            return None
        if name in ("StopAccelerating", "SetMoveSpeed", "StopTransformingThrottle",
                    "SetGravity", "EnableMovementCollisionWithEnvironment"):
            return None
        return super().call(name, args)

    def execute(self, actions):
        # Feedback wording and physics helper internals have separate coverage.
        # Keep their original control flow and record the actual invocation order.
        for call in reversed(list(validator.iter_calls(actions, "Small Message"))):
            actions = actions[:call.start] + "Record Message(Event Player)" + actions[call.end:]
        actions = actions.replace("Call Subroutine(", "Record Subroutine(")
        return super().execute(actions)

    def die(self, selected="one", position=None):
        player = self.players[selected]
        player["alive"] = False
        if position is not None:
            player["position"] = position
        self.step(self.now, selected, "12e")

    def count(self, native, selected="one"):
        return sum(event[:2] == (native, selected) for event in self.events)


class JumpResurrectTests(unittest.TestCase):
    def models(self):
        for path in (ROOT / "workshop/ruang_irama.it-IT.workshop",
                     ROOT / "tests/fixtures/semantic_reference.txt"):
            yield path.name, JumpEvaluator(path.read_text(encoding="utf-8"))

    def test_holding_jump_does_not_restart_revive_after_an_immediate_new_death(self):
        for source, model in self.models():
            with self.subTest(source=source):
                player = model.players["one"]
                player["jump"] = True
                model.die()
                model.step(100, prefix="12f")
                for tick in range(1, 21):
                    if player["alive"]:
                        model.die()
                    model.step(100 + tick / 10, prefix="12f")
                self.assertEqual(model.count("Resurrect"), 1)
                self.assertTrue(player["BangkitLompatDipakai"])
                player["jump"] = False
                model.step(103, prefix="12g")
                player["jump"] = True
                model.step(104, prefix="12f")
                self.assertEqual(model.count("Resurrect"), 2)

    def test_releasing_jump_rearms_the_next_press_while_alive_or_dead(self):
        for source, model in self.models():
            for alive in (True, False):
                with self.subTest(source=source, alive_at_release=alive):
                    player = model.add_player("one", alive=False, jump=True)
                    before = model.count("Resurrect")
                    model.die()
                    model.step(100, prefix="12f")
                    self.assertTrue(player["BangkitLompatDipakai"])
                    player.update(alive=alive, jump=False)
                    model.step(101, prefix="12g")
                    self.assertFalse(player["BangkitLompatDipakai"])
                    model.die()
                    player["jump"] = True
                    model.step(102, prefix="12f")
                    self.assertEqual(model.count("Resurrect"), before + 2)

    def test_two_players_have_independent_jump_latches(self):
        for source, model in self.models():
            with self.subTest(source=source):
                first = model.players["one"]
                first["jump"] = True
                model.die()
                model.step(100, prefix="12f")
                model.die()
                first_snapshot = dict(first)
                second = model.add_player("two", jump=True)
                model.die("two")
                model.step(101, "two", "12f")
                second["jump"] = False
                model.step(102, "two", "12g")
                self.assertEqual(first, first_snapshot)
                model.step(103, "one", "12f")
                self.assertEqual(model.count("Resurrect", "one"), 1)
                self.assertEqual(model.count("Resurrect", "two"), 1)
                self.assertTrue(first["BangkitLompatDipakai"])
                self.assertFalse(second["BangkitLompatDipakai"])

    def test_nonhuman_players_do_not_enter_the_jump_revive_rules(self):
        for source, model in self.models():
            for excluded in (dict(dummy=True), dict(Manusia=False), dict(BotOtomatis=True)):
                with self.subTest(source=source, excluded=excluded):
                    player = model.add_player("one", alive=False, jump=True, **excluded)
                    before = dict(player)
                    model.die()
                    model.step(100, prefix="12f")
                    self.assertEqual(player, before)
                    self.assertEqual(model.events, [])

    def test_collision_near_a_void_death_does_not_hide_a_distant_walkable_point(self):
        for source, model in self.models():
            with self.subTest(source=source):
                death = Vector(10, -30, 20)
                model.navigation_result = Vector(25, 2, 20)
                model.ray_result = death + Vector(0, -1, 0)
                player = model.players["one"]
                player["jump"] = True
                model.die(position=death)
                model.step(100, prefix="12f")
                target = model.navigation_result + Vector(0, 0.5, 0)
                self.assertEqual(player["position"], target)
                self.assertEqual([event[2] for event in model.events if event[0] == "Teleport"],
                                 [target, target])
                self.assertEqual(model.navigation_queries, [("one", death)])
                self.assertFalse(player["BangkitPerluTeleportasi"])

    def test_downward_raycast_miss_still_requests_a_walkable_destination(self):
        for source, model in self.models():
            with self.subTest(source=source):
                death = Vector(10, -30, 20)
                # Isolate the raycast branch: native navigation happens to return
                # a point within 0.5 m, while the cast reaches its lower endpoint.
                model.navigation_result = death + Vector(0.1, 0.1, 0)
                model.ray_result = death - Vector(0, 3, 0)
                player = model.players["one"]
                player["jump"] = True
                model.die(position=death)
                model.step(100, prefix="12f")
                self.assertEqual(model.count("Teleport"), 2)
                self.assertEqual(player["position"], model.navigation_result + Vector(0, 0.5, 0))

    def test_nearby_walkable_edge_is_not_mistaken_for_safe_death_ground(self):
        for source, model in self.models():
            with self.subTest(source=source):
                death = Vector(10, -1, 20)
                model.navigation_result = death + Vector(0, 1, 0)
                model.ray_result = death
                player = model.players["one"]
                player["jump"] = True
                model.die(position=death)
                model.step(100, prefix="12f")
                self.assertEqual(model.count("Teleport"), 2)
                self.assertEqual(player["position"], model.navigation_result + Vector(0, 0.5, 0))

    def test_safe_ground_death_revives_in_place_without_teleporting(self):
        for source, model in self.models():
            with self.subTest(source=source):
                death = Vector(10, 20, 40)
                model.navigation_result = death + Vector(0.4, 0, 0.1)
                model.ray_result = death
                player = model.players["one"]
                player["jump"] = True
                model.die(position=death)
                model.step(100, prefix="12f")
                self.assertEqual(model.count("Resurrect"), 1)
                self.assertEqual(model.count("Teleport"), 0)
                self.assertEqual(player["position"], death)
                self.assertEqual(model.navigation_queries, [("one", death)])
                self.assertFalse(player["BangkitPerluTeleportasi"])

    def test_void_recovery_handles_engine_accepting_or_ignoring_corpse_teleport(self):
        for source, model in self.models():
            for honored in (True, False):
                with self.subTest(source=source, corpse_teleport_honored=honored):
                    death = Vector(10, -30, 20)
                    model.navigation_result = Vector(25, 2, 20)
                    model.ray_result = death
                    player = model.add_player("one", jump=True, corpse_teleport_honored=honored)
                    model.events.clear()
                    model.navigation_queries.clear()
                    model.die(position=death)
                    model.step(100, prefix="12f")
                    movement = [event for event in model.events if event[0] in ("Teleport", "Resurrect")]
                    self.assertEqual([event[0] for event in movement], ["Teleport", "Resurrect", "Teleport"])
                    target = model.navigation_result + Vector(0, 0.5, 0)
                    self.assertEqual(movement[1][2], target if honored else death)
                    self.assertEqual(player["position"], target)
                    self.assertEqual(model.navigation_queries, [("one", death)])

    def test_post_revive_engine_reposition_does_not_change_the_saved_destination(self):
        for source, model in self.models():
            with self.subTest(source=source):
                death = Vector(10, -30, 20)
                model.navigation_result = Vector(25, 2, 20)
                model.ray_result = death
                player = model.add_player("one", jump=True, resurrect_position=Vector(200, -40, 300))
                model.die(position=death)
                model.step(100, prefix="12f")
                self.assertEqual(player["position"], model.navigation_result + Vector(0, 0.5, 0))
                self.assertEqual(model.navigation_queries, [("one", death)])

    def test_feedback_and_fly_restore_run_after_relocation_only_if_alive(self):
        for source, model in self.models():
            for resurrection_succeeds in (True, False):
                with self.subTest(source=source, resurrection_succeeds=resurrection_succeeds):
                    death = Vector(10, -30, 20)
                    model.navigation_result = Vector(25, 2, 20)
                    model.ray_result = death
                    model.add_player("one", jump=True, resurrect_alive=resurrection_succeeds)
                    model.events.clear()
                    model.die(position=death)
                    model.step(100, prefix="12f")
                    helpers = [event for event in model.events
                               if event[0] == "TerapkanFisikaHantuTerbang"]
                    if resurrection_succeeds:
                        self.assertEqual([event[0] for event in helpers],
                                         ["TerapkanFisikaHantuTerbang"])
                        target = model.navigation_result + Vector(0, 0.5, 0)
                        self.assertEqual([event[2:] for event in helpers], [(target, True)])
                        self.assertEqual(model.events[-1:], helpers)
                    else:
                        self.assertEqual(helpers, [])


if __name__ == "__main__":
    unittest.main()
