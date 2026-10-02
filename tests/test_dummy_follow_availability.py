"""Execute the real follow toggle against controlled entity/team queries.

This covers consent and availability decisions in both clipboard grammars.
Native HUD rendering and entity/event timing still require the game client.
"""

import operator
import re
import unittest

from tools import validate_workshop as validator
from tests.test_audit_lifecycle import AuditExpression, AuditLifecycleEvaluator, statements
from tests.test_roster_rejoin_regressions import SOURCES


class DummyFollowEvaluator(AuditLifecycleEvaluator):
    def __init__(self, source):
        super().__init__(source)
        apply = validator.rule_by_subroutine(self.rules, "TerapkanHalamanIkutiBotBuatan")
        self.program = statements(validator.rule_block(apply, "actions"))

    def add(self, identity, team=1, **changes):
        state = dict(team=team, exists=True, visible=True, dummy=False,
                     BotOtomatis=False, spawned=True, alive=True,
                     IzinkanBotBuatanMengikuti=False, KursorIkutiBotBuatan=0)
        state.update(changes)
        self.players[identity] = state
        return state

    def call(self, name, args):
        if name == "AllPlayers":
            # A stale engine entry can remain visible for a query; Entity Exists
            # must still reject it before allowing consent.
            return [identity for identity, state in self.players.items()
                    if state["visible"] and state["team"] == args[0]]
        if name == "OppositeTeamOf":
            return {1: 2, 2: 1}.get(args[0])
        return super().call(name, args)

    def evaluate(self, expression):
        tree = AuditExpression(re.sub(r"\s+", "", expression)).tree
        operations = {"==": operator.eq, "!=": operator.ne}

        def visit(node):
            kind = node[0]
            if kind == "literal":
                return node[1]
            if kind == "name":
                return self.resolve(node[1])
            if kind != "call":
                return operations[kind](visit(node[1]), visit(node[2]))
            name, args = node[1:]
            if name in ("And", "Or"):
                return (all if name == "And" else any)(bool(visit(arg)) for arg in args)
            if name == "IsTrueForAny":
                previous = self.current
                try:
                    for identity in visit(args[0]):
                        self.current = identity
                        if visit(args[1]):
                            return True
                    return False
                finally:
                    self.current = previous
            return self.call(name, [visit(arg) for arg in args])

        return visit(tree)

    def execute(self, nodes):
        for node in nodes:
            token = node[0]
            if token.startswith("Abort If("):
                if self.evaluate(token[len("Abort If("):-1]):
                    return True
            elif super().execute([node]):
                return True
        return False

    def apply(self, identity, on):
        self.event_player = identity
        self.players[identity]["KursorIkutiBotBuatan"] = int(on)
        self.execute(self.program)

    def applied_effects(self):
        return [name for _, name in self.calls if name == "EfekTerapkan"]


class DummyFollowAvailabilityTests(unittest.TestCase):
    def models(self):
        for path, _, _ in SOURCES:
            yield path.name, DummyFollowEvaluator(path.read_text(encoding="utf-8"))

    def test_no_dummy_blocks_activation_without_success_feedback(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("human")
                model.apply("human", True)
                self.assertFalse(state["IzinkanBotBuatanMengikuti"])
                self.assertEqual(model.applied_effects(), [])

    def test_same_team_dummy_does_not_allow_activation(self):
        for source, model in self.models():
            for team in (1, 2):
                with self.subTest(source=source, team=team):
                    state = model.add("human", team=team)
                    model.add("dummy", team=team, dummy=True)
                    model.apply("human", True)
                    self.assertFalse(state["IzinkanBotBuatanMengikuti"])
                    self.assertEqual(model.applied_effects(), [])

    def test_one_team_one_dummy_allows_only_team_two_consent(self):
        for source, model in self.models():
            with self.subTest(source=source):
                first = model.add("team-one", team=1)
                second = model.add("team-two", team=2)
                model.add("dummy-one", team=1, dummy=True)
                model.apply("team-one", True)
                model.apply("team-two", True)
                self.assertFalse(first["IzinkanBotBuatanMengikuti"])
                self.assertTrue(second["IzinkanBotBuatanMengikuti"])
                self.assertEqual(model.applied_effects(), [])

    def test_two_team_dummies_allow_each_player_independent_consent(self):
        for source, model in self.models():
            with self.subTest(source=source):
                first = model.add("team-one", team=1)
                second = model.add("team-two", team=2)
                observer = model.add("other", team=2)
                model.add("dummy-one", team=1, dummy=True)
                model.add("dummy-two", team=2, dummy=True)
                model.apply("team-one", True)
                model.apply("team-two", True)
                self.assertTrue(first["IzinkanBotBuatanMengikuti"])
                self.assertTrue(second["IzinkanBotBuatanMengikuti"])
                self.assertFalse(observer["IzinkanBotBuatanMengikuti"])

    def test_enemy_humans_and_normal_ai_do_not_enable_dummy_follow(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("human", team=2)
                model.add("enemy-human", team=1)
                model.add("normal-ai", team=1, BotOtomatis=True)
                model.apply("human", True)
                self.assertFalse(state["IzinkanBotBuatanMengikuti"])

    def test_stale_enemy_dummy_reference_does_not_enable_follow(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("human", team=2)
                model.add("gone", team=1, dummy=True, exists=False)
                model.apply("human", True)
                self.assertFalse(state["IzinkanBotBuatanMengikuti"])

    def test_respawning_enemy_dummy_still_counts_as_present(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("human", team=2)
                model.add("respawning", team=1, dummy=True, spawned=False, alive=False)
                model.apply("human", True)
                self.assertTrue(state["IzinkanBotBuatanMengikuti"])

    def test_disabled_consent_can_always_be_applied_after_dummy_removal(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("human", team=2)
                dummy = model.add("dummy", team=1, dummy=True)
                model.apply("human", True)
                dummy.update(exists=False, visible=False)
                model.apply("human", False)
                self.assertFalse(state["IzinkanBotBuatanMengikuti"])
                self.assertEqual(model.applied_effects(), [])

    def test_dummy_disappearing_between_menu_open_and_apply_blocks_activation(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("human", team=2, KursorIkutiBotBuatan=1)
                dummy = model.add("dummy", team=1, dummy=True)
                dummy.update(exists=False, visible=False)
                model.apply("human", True)
                self.assertFalse(state["IzinkanBotBuatanMengikuti"])
                dummy.update(exists=True, visible=True)
                model.apply("human", True)
                self.assertTrue(state["IzinkanBotBuatanMengikuti"])

    def test_reapplying_on_without_dummy_does_not_erase_existing_opt_in(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("human", IzinkanBotBuatanMengikuti=True)
                model.apply("human", True)
                self.assertTrue(state["IzinkanBotBuatanMengikuti"])
                self.assertEqual(model.applied_effects(), [])

    def test_open_menu_reports_unavailability_in_all_three_languages(self):
        for source, model in self.models():
            with self.subTest(source=source):
                page = validator.rule_by_subroutine(model.rules, "GambarIkutiBotBuatan")
                apply = validator.rule_by_subroutine(model.rules, "TerapkanHalamanIkutiBotBuatan")
                condition = (
                    "Is True For Any(All Players(Opposite Team Of(Team Of(Event Player))), "
                    "And(Entity Exists(Current Array Element), Is Dummy Bot(Current Array Element) == True))"
                )
                self.assertEqual(page.body.count(condition), 1)
                self.assertEqual(apply.body.count(condition), 1)
                for label in ("NO ENEMY DUMMY", "BOT MUSUH TIDAK ADA", "ไม่มีดัมมี่ศัตรู"):
                    self.assertIn(label, page.body)
                self.assertEqual(page.body.count("Create HUD Text("), 1)
                self.assertNotIn("Wait(", apply.body)
                self.assertNotIn("Filtered Array(", apply.body)


if __name__ == "__main__":
    unittest.main()
