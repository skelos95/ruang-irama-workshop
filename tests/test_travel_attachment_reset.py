"""Execute successful and rejected Travel routes with attachment metadata.

Native teleport/navigation remain controlled boundaries. These regressions check
the metadata consumed by Multijump after a teleport has released an attachment.
"""
import unittest

from tests.test_camera_reinitialization import CameraResetEvaluator, PATHS
from tests.test_fly_motion import Vector
from tests.test_multijump import MultijumpEvaluator
from tools import validate_workshop as semantic


ROUTES = ("TravelToSpawn", "TravelToObjective", "TravelToPlayer")
ATTACHMENT_FIELDS = (
    "TravelAttachmentActive", "TravelAttachmentTarget",
    "AttachmentOwnerHero", "AttachmentTargetHero",
)
CLEARED_ATTACHMENT = (False, None, None, None)


class ImportedMultijumpEvaluator(MultijumpEvaluator):
    """Also accept the generated runtime's native Boolean compaction."""

    def call(self, name, args):
        if name == "Not":
            return not args[0]
        return super().call(name, args)


class TravelAttachmentResetTests(unittest.TestCase):
    @staticmethod
    def metadata(state):
        return tuple(state[field] for field in ATTACHMENT_FIELDS)

    def setup_players(self, model, attached=True, camera=1):
        state = model.add(
            "viewer", CameraMode=camera,
            TravelAttachmentActive=attached,
            TravelAttachmentTarget="target" if attached else None,
            AttachmentOwnerHero="viewer-hero" if attached else None,
            AttachmentTargetHero="target-hero" if attached else None,
        )
        model.add("target")
        return state

    def test_each_successful_route_clears_all_attachment_metadata(self):
        for path in PATHS:
            for route in ROUTES:
                with self.subTest(artifact=path.name, route=route):
                    model = CameraResetEvaluator(path.read_text(encoding="utf-8"))
                    state = self.setup_players(model)
                    model.route("viewer", route)
                    self.assertEqual(model.steps, [
                        ("stop", "viewer"), ("teleport", "viewer"), ("start", "viewer"),
                    ])
                    self.assertEqual(self.metadata(state), CLEARED_ATTACHMENT)
                    self.assertEqual((state["CameraMode"], state["CameraTarget"]), (1, "viewer"))

    def test_rejected_or_noop_routes_preserve_the_existing_attachment(self):
        cases = (
            ("TravelToSpawn", "already_spawn"),
            ("TravelToSpawn", "missing_spawn"),
            ("TravelToObjective", "missing_objective"),
            ("TravelToObjective", "unsafe"),
            ("TravelToPlayer", "missing_target"),
            ("TravelToPlayer", "unsafe"),
        )
        for path in PATHS:
            for route, failure in cases:
                with self.subTest(artifact=path.name, route=route, failure=failure):
                    model = CameraResetEvaluator(path.read_text(encoding="utf-8"))
                    state = self.setup_players(model)
                    before = self.metadata(state)
                    if failure == "already_spawn": state["in_spawn"] = True
                    if failure == "missing_spawn": model.spawn_points = []
                    if failure == "missing_objective": model.objective = Vector(0, 0, 0)
                    if failure == "missing_target": state["LockedTravelTarget"] = None
                    if failure == "unsafe": model.safe_position = Vector(0, 0, 0)
                    model.route("viewer", route)
                    self.assertEqual(model.steps, [])
                    self.assertEqual(self.metadata(state), before)

    def test_unattached_player_keeps_camera_off_and_only_teleports(self):
        for path in PATHS:
            for route in ROUTES:
                with self.subTest(artifact=path.name, route=route):
                    model = CameraResetEvaluator(path.read_text(encoding="utf-8"))
                    state = self.setup_players(model, attached=False, camera=0)
                    model.route("viewer", route)
                    self.assertEqual(model.steps, [("teleport", "viewer")])
                    self.assertEqual(self.metadata(state), CLEARED_ATTACHMENT)
                    self.assertEqual(state["CameraMode"], 0)
                    self.assertEqual(model.native_cameras, {})

    def test_travel_does_not_reset_another_players_attachment_or_camera(self):
        for path in PATHS:
            for route in ROUTES:
                with self.subTest(artifact=path.name, route=route):
                    model = CameraResetEvaluator(path.read_text(encoding="utf-8"))
                    self.setup_players(model)
                    other = model.add(
                        "other", CameraMode=2, CameraTarget="target",
                        TravelAttachmentActive=True, TravelAttachmentTarget="target",
                        AttachmentOwnerHero="other-hero", AttachmentTargetHero="target-hero",
                    )
                    before = dict(other)
                    model.native_cameras["other"] = "target"
                    model.route("viewer", route)
                    self.assertEqual(other, before)
                    self.assertEqual(model.native_cameras["other"], "target")

    def test_multijump_resumes_after_each_successful_travel(self):
        for path in PATHS:
            text = path.read_text(encoding="utf-8")
            jump_rule = semantic.rule_by_subroutine(semantic.extract_rules(text), "ProcessMultijump")
            actions = semantic.rule_block(jump_rule, "actions")
            for route in ROUTES:
                with self.subTest(artifact=path.name, route=route):
                    travel = CameraResetEvaluator(text)
                    state = self.setup_players(travel)
                    jumps = ImportedMultijumpEvaluator(text)
                    jumper = jumps.add("viewer", jump=True, TravelAttachmentActive=True)
                    jumps.event_player = "viewer"
                    jumps.execute(actions)
                    self.assertEqual(jumps.impulses, [])
                    travel.route("viewer", route)
                    jumper.update({field: state[field] for field in ATTACHMENT_FIELDS})
                    jumps.now = 0.3
                    jumps.execute(actions)
                    self.assertEqual(len(jumps.impulses), 1)


if __name__ == "__main__":
    unittest.main()
