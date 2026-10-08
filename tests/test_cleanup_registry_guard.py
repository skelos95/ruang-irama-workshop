"""Exercise the actual emergency cleanup path when canonical arrays are short."""
import copy
import re
import unittest

from tools import validate_workshop as validator
from tests.test_audit_lifecycle import AuditLifecycleEvaluator
from tests.test_roster_rejoin_regressions import SOURCES


class RegistryCleanupEvaluator(AuditLifecycleEvaluator):
    RESOURCE = re.compile(r"Destroy (?:HUD|In-World) Text\(Global\.(?:PlayerListHudIds|MenuHudIds|InspectionTextIds)\[")

    def keep_cleanup(self, token):
        return super().keep_cleanup(token) or bool(self.RESOURCE.match(token))

    def execute(self, nodes):
        for node in nodes:
            token = node[0]
            if self.RESOURCE.match(token):
                self.destroyed.append(self.evaluate(token[token.index("(") + 1:-1]))
            elif super().execute([node]):
                return True
        return False


class CleanupRegistryGuardTests(unittest.TestCase):
    ARRAYS = ("PlayerHudSlots", "PlayerListHudIds", "MenuHudIds", "InspectionTextIds")

    def test_each_short_registry_uses_safe_cleanup_and_preserves_survivors(self):
        for path, _, _ in SOURCES:
            for short_array in self.ARRAYS:
                with self.subTest(source=path.name, short_array=short_array):
                    model = RegistryCleanupEvaluator(path.read_text(encoding="utf-8"))
                    for identity in ("alice", "bob", "departed"):
                        model.join(identity)
                    for offset, array in enumerate(self.ARRAYS[1:]):
                        model.globals[array] = [100 + offset, 200 + offset, 300 + offset]
                    model.install_icons("departed", 50)
                    model.globals[short_array].pop()
                    before = copy.deepcopy(model.globals)
                    # Out-of-range indexing raises in this evaluator, exposing a missing guard.
                    model.remove("departed")
                    self.assertEqual(model.globals["HumanPlayers"], ["alice", "bob"])
                    for array in self.ARRAYS:
                        self.assertEqual(model.globals[array], before[array][:2])
                    expected_texts = [before[array][2] for array in self.ARRAYS[1:] if len(before[array]) > 2]
                    self.assertCountEqual([handle for handle in model.destroyed if 300 <= handle < 400], expected_texts)
                    self.assertFalse(any(handle < 300 for handle in model.destroyed))
                    expected_free = list(range(3, 12)) if short_array == "PlayerHudSlots" else list(range(2, 12))
                    self.assertEqual(model.globals["AvailableHudSlots"], expected_free)
                    snapshot = copy.deepcopy(model.globals)
                    destroyed = list(model.destroyed)
                    model.remove("departed")
                    for array in self.ARRAYS + ("HumanPlayers", "AvailableHudSlots"):
                        self.assertEqual(model.globals[array], snapshot[array])
                    self.assertEqual(model.destroyed, destroyed)

    def test_validator_rejects_missing_guard_and_each_missing_array_check(self):
        source = validator.SOURCE.read_text(encoding="utf-8")
        cleanup = validator.rule_by_subroutine(validator.extract_rules(source), "CleanupPlayer")
        marker = cleanup.body.index("Global.LeavingPlayerIndex = -2;")
        branch = min(validator.conditional_branches_containing(cleanup.body, marker), key=len)
        mutations = [cleanup.body.replace(branch, "", 1)]
        mutations += [cleanup.body.replace(f"Global.LeavingPlayerIndex >= Count Of(Global.{array})", "False", 1)
                      for array in self.ARRAYS]
        for body in mutations:
            with self.subTest(body=body[:60]):
                changed = validator.extract_rules(body)[0]
                checks = validator.Checks()
                validator.validate_cleanup_registry_guard(checks, changed)
                self.assertTrue(checks.errors)


if __name__ == "__main__":
    unittest.main()
