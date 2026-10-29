"""Execute emitted movement preferences through physics and lifecycle paths.

Native speed, gravity and additive impulse calls are recorded boundaries; these
tests verify script state and ownership, not Overwatch's collision simulation.
"""
from pathlib import Path
import unittest

from tests.test_fly_motion import Vector, ZERO
from tests.test_global_spectator_rejoin import SpectatorRuntimeEvaluator
from tools import validate_workshop as semantic


RUNTIME = Path(__file__).resolve().parents[1] / "workshop/ruang_irama.en-US.workshop"


class MovementPhysicsEvaluator(SpectatorRuntimeEvaluator):
    def call(self, name, args):
        if name == "VelocityOf":
            return self.players[args[0]].get("native_velocity", ZERO)
        return super().call(name, args)

    def native(self, name, arguments):
        if name in ("SetMoveSpeed", "SetGravity", "ApplyImpulse",
                    "EnableMovementCollisionWithEnvironment", "DisableMovementCollisionWithEnvironment"):
            args = [self.expression(arg) for arg in semantic.split_top_level(arguments, ",")]
            owner = self.players[args[0]]
            if name == "SetMoveSpeed":
                owner["native_speed"] = args[1]
            elif name == "SetGravity":
                owner["native_gravity"] = args[1]
            elif name == "ApplyImpulse":
                owner["native_velocity"] = owner.get("native_velocity", ZERO) + args[1].normalized() * args[2]
            elif name == "EnableMovementCollisionWithEnvironment":
                owner.update(native_wall_collision=True, native_floor_collision=True)
            else:
                owner["native_wall_collision"] = False
                if args[1]:
                    owner["native_floor_collision"] = False
        super().native(name, arguments)

    def route(self, player, target):
        self.globals.update(TriggerPlayer=player, ActivePlayer=player)
        self.run(target)


class MovementPhysicsTests(unittest.TestCase):
    def model(self, **changes):
        model = MovementPhysicsEvaluator(RUNTIME.read_text(encoding="utf-8"))
        state = model.ready_player("viewer", **changes)
        return model, state

    def test_ground_speed_and_gravity_apply_independently_at_the_boundaries(self):
        for speed in (50, 100, 1000):
            for gravity in (0, 100, 500):
                for ghost in (False, True):
                    with self.subTest(speed=speed, gravity=gravity, ghost=ghost):
                        model, state = self.model(MovementSpeed=speed, MovementGravity=gravity,
                                                  GhostModeActive=ghost, FlyModeActive=False)
                        model.route("viewer", "ApplyGhostFlyPhysics")
                        self.assertEqual((state["native_speed"], state["native_gravity"]), (speed, gravity))
                        self.assertEqual((state["MovementSpeed"], state["MovementGravity"]), (speed, gravity))

    def test_fly_keeps_native_gravity_zero_and_restores_the_saved_selection_on_off(self):
        model, state = self.model(MovementSpeed=350, MovementGravity=500, FlyModeActive=True)
        model.route("viewer", "ApplyGhostFlyPhysics")
        self.assertEqual((state["native_speed"], state["native_gravity"]), (0, 0))
        state.update(MovementSpeed=700, MovementGravity=50)
        model.route("viewer", "ApplyGhostFlyPhysics")
        self.assertEqual((state["native_speed"], state["native_gravity"]), (0, 0))
        self.assertEqual((state["MovementSpeed"], state["MovementGravity"]), (700, 50))
        state.update(FlyModeActive=False, GhostFlyPhysicsApplied=False)
        model.route("viewer", "ApplyGhostFlyPhysics")
        self.assertEqual((state["native_speed"], state["native_gravity"]), (700, 50))

    def test_parameter_changes_preserve_momentum_but_disabling_fly_stops_drift(self):
        model, state = self.model(MovementSpeed=400, MovementGravity=150, FlyModeActive=False,
                                  GhostFlyPhysicsApplied=True, native_velocity=Vector(4, 8, 2))
        model.route("viewer", "ApplyGhostFlyPhysics")
        self.assertEqual(state["native_velocity"], Vector(4, 8, 2))
        state.update(MovementGravity=300, MovementSpeed=600)
        model.route("viewer", "ApplyGhostFlyPhysics")
        self.assertEqual(state["native_velocity"], Vector(4, 8, 2))
        self.assertEqual((state["native_speed"], state["native_gravity"]), (600, 300))
        state["GhostFlyPhysicsApplied"] = False
        model.route("viewer", "ApplyGhostFlyPhysics")
        self.assertEqual(state["native_velocity"], ZERO)

    def test_ghost_on_and_off_preserve_fall_and_knockback_with_every_fly_latch_state(self):
        for velocity in (Vector(0, -12, 0), Vector(4, 8, 2)):
            for fly in (False, True):
                for applied in (False, True):
                    for luck in (False, True):
                        with self.subTest(velocity=velocity, fly=fly, applied=applied, luck=luck):
                            speed = 1000 if luck else (0 if fly else 350)
                            gravity = 0 if fly else 450
                            model, state = self.model(
                                GhostFlyCursor=0, GhostModeActive=False, FlyModeActive=fly,
                                GhostFlyPhysicsApplied=applied, MovementSpeed=350, MovementGravity=450,
                                native_velocity=velocity, native_speed=speed, native_gravity=gravity,
                                native_wall_collision=True, native_floor_collision=True,
                                LuckEffect=2 if luck else 0, LuckEffectEndTime=20,
                            )
                            model.now = 10
                            for ghost in (True, False):
                                before_native = len(model.native_log)
                                before_calls = len(model.calls)
                                model.route("viewer", "ApplyGhostFlyPage")
                                self.assertEqual(state["GhostModeActive"], ghost)
                                self.assertEqual(state["native_wall_collision"], not ghost)
                                self.assertTrue(state["native_floor_collision"])
                                self.assertEqual(state["native_velocity"], velocity)
                                self.assertEqual((state["native_speed"], state["native_gravity"]), (speed, gravity))
                                self.assertEqual((state["MovementSpeed"], state["MovementGravity"]), (350, 450))
                                self.assertEqual(state["FlyModeActive"], fly)
                                self.assertEqual(state["GhostFlyPhysicsApplied"], applied)
                                self.assertEqual((state["LuckEffect"], state["LuckEffectEndTime"]), (2 if luck else 0, 20))
                                collision = ("DisableMovementCollisionWithEnvironment" if ghost
                                             else "EnableMovementCollisionWithEnvironment")
                                self.assertEqual(model.native_log[before_native:], [(10, collision, "viewer")])
                                self.assertEqual([call[2] for call in model.calls[before_calls:]], ["ApplyGhostFlyPage"])

    def test_fly_page_still_applies_physics_and_brakes_off_unless_luck_owns_motion(self):
        velocity = Vector(4, 8, 2)
        for ghost in (False, True):
            for fly in (False, True):
                for applied in (False, True):
                    for luck in (False, True):
                        with self.subTest(ghost=ghost, fly=fly, applied=applied, luck=luck):
                            model, state = self.model(
                                GhostFlyCursor=1, GhostModeActive=ghost, FlyModeActive=fly,
                                GhostFlyPhysicsApplied=applied, MovementSpeed=350, MovementGravity=450,
                                native_velocity=velocity, native_speed=1000 if luck else (0 if fly else 350),
                                native_gravity=0 if fly else 450,
                                LuckEffect=2 if luck else 0, LuckEffectEndTime=20,
                            )
                            model.now = 10
                            before_calls = len(model.calls)
                            model.route("viewer", "ApplyGhostFlyPage")
                            self.assertEqual(state["FlyModeActive"], not fly)
                            self.assertEqual(state["GhostModeActive"], ghost)
                            self.assertTrue(state["GhostFlyPhysicsApplied"])
                            self.assertEqual((state["MovementSpeed"], state["MovementGravity"]), (350, 450))
                            self.assertEqual(state["native_wall_collision"], not ghost)
                            self.assertTrue(state["native_floor_collision"])
                            self.assertEqual(state["native_gravity"], 450 if fly else 0)
                            self.assertEqual(state["native_speed"], 1000 if luck else (350 if fly else 0))
                            self.assertEqual(state["native_velocity"], ZERO if fly and not luck else velocity)
                            self.assertEqual([call[2] for call in model.calls[before_calls:]],
                                             ["ApplyGhostFlyPage", "ApplyGhostFlyPhysics"])

    def test_death_respawn_and_hero_change_preserve_preferences(self):
        for fly in (False, True):
            with self.subTest(fly=fly):
                model, state = self.model(MovementSpeed=450, MovementGravity=350,
                                          FlyModeActive=fly, GhostFlyPhysicsApplied=True)
                state["alive"] = False
                model.route("viewer", "ProcessPlayerCycle")
                self.assertEqual((state["native_speed"], state["native_gravity"]), (100, 100))
                self.assertEqual((state["MovementSpeed"], state["MovementGravity"]), (450, 350))
                state["alive"] = True
                model.route("viewer", "ProcessPlayerCycle")
                self.assertEqual((state["native_speed"], state["native_gravity"]), (0, 0) if fly else (450, 350))
                state["hero"] = "Reinhardt"
                model.route("viewer", "ProcessPlayerCycle")
                model.route("viewer", "ProcessPlayerCycle")
                self.assertEqual((state["MovementSpeed"], state["MovementGravity"]), (450, 350))
                self.assertEqual((state["native_speed"], state["native_gravity"]), (0, 0) if fly else (450, 350))

    def test_luck_acceleration_owns_speed_then_both_restore_routes_resume_the_selection(self):
        for restore in ("RestorePlayerLuck", "RestoreActivePlayerLuck"):
            for fly in (False, True):
                with self.subTest(restore=restore, fly=fly):
                    model, state = self.model(MovementSpeed=250, MovementGravity=450,
                                              FlyModeActive=fly, LuckEffect=2,
                                              LuckEffectEndTime=20, native_speed=1000)
                    model.now = 10
                    model.route("viewer", "ApplyGhostFlyPhysics")
                    self.assertEqual(state["native_speed"], 1000)
                    self.assertEqual(state["native_gravity"], 0 if fly else 450)
                    state.update(MovementSpeed=600, MovementGravity=500)
                    model.route("viewer", "ApplyGhostFlyPhysics")
                    self.assertEqual(state["native_speed"], 1000)
                    self.assertEqual(state["native_gravity"], 0 if fly else 500)
                    model.route("viewer", restore)
                    self.assertEqual(state["native_speed"], 0 if fly else 600)
                    self.assertEqual((state["MovementSpeed"], state["MovementGravity"]), (600, 500))

    def test_luck_expiry_restores_the_selection_without_waiting_for_another_spawn(self):
        for fly in (False, True):
            with self.subTest(fly=fly):
                model, state = self.model(MovementSpeed=800, MovementGravity=200,
                                          FlyModeActive=fly, LuckEffect=2, LuckActive=True,
                                          LuckSpinCount=0, LuckEffectEndTime=9, native_speed=1000)
                model.now = 10
                model.route("viewer", "ProcessPlayerLuck")
                self.assertEqual(state["native_speed"], 0 if fly else 800)
                self.assertEqual(state["LuckEffect"], 0)
                self.assertEqual((state["MovementSpeed"], state["MovementGravity"]), (800, 200))

    def test_prepare_resets_only_its_owner_to_default_preferences(self):
        model, state = self.model(MovementSpeed=900, MovementGravity=0)
        other = model.ready_player("other", MovementSpeed=550, MovementGravity=500)
        model.route("viewer", "PreparePlayer")
        self.assertEqual((state["MovementSpeed"], state["MovementGravity"]), (100, 100))
        self.assertEqual((other["MovementSpeed"], other["MovementGravity"]), (550, 500))


if __name__ == "__main__":
    unittest.main()
