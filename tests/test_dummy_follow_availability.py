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
        apply = validator.rule_by_subroutine(self.rules, "ApplyDummyBotFollowPage")
        self.program = statements(validator.rule_block(apply, "actions"))

    def add(self, identity, team=1, **changes):
        state = dict(team=team, exists=True, visible=True, dummy=False,
                     IsAutomaticBot=False, spawned=True, alive=True, IsHuman=True,
                     MenuOpen=False, MenuPage=-1, AllowDummyBotFollow=False)
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

    def resolve(self, name):
        if name == "AllowDummyBotFollow":
            return name
        return super().resolve(name)

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

    def apply(self, identity):
        self.event_player = identity
        self.execute(self.program)

    def cache_tick(self, identity):
        self.globals["ActivePlayer"] = identity
        cache = validator.rule_by_subroutine(self.rules, "ProcessPlayerMaintenance")
        self.execute(statements(validator.rule_block(cache, "actions")))

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
                model.apply("human")
                self.assertFalse(state["AllowDummyBotFollow"])
                self.assertEqual(model.applied_effects(), [])

    def test_same_team_dummy_does_not_allow_activation(self):
        for source, model in self.models():
            for team in (1, 2):
                with self.subTest(source=source, team=team):
                    state = model.add("human", team=team)
                    model.add("dummy", team=team, dummy=True)
                    model.apply("human")
                    self.assertFalse(state["AllowDummyBotFollow"])
                    self.assertEqual(model.applied_effects(), [])

    def test_one_team_one_dummy_allows_only_team_two_consent(self):
        for source, model in self.models():
            with self.subTest(source=source):
                first = model.add("team-one", team=1)
                second = model.add("team-two", team=2)
                model.add("dummy-one", team=1, dummy=True)
                model.apply("team-one")
                model.apply("team-two")
                self.assertFalse(first["AllowDummyBotFollow"])
                self.assertTrue(second["AllowDummyBotFollow"])
                self.assertEqual(model.applied_effects(), [])

    def test_two_team_dummies_allow_each_player_independent_consent(self):
        for source, model in self.models():
            with self.subTest(source=source):
                first = model.add("team-one", team=1)
                second = model.add("team-two", team=2)
                observer = model.add("other", team=2)
                model.add("dummy-one", team=1, dummy=True)
                model.add("dummy-two", team=2, dummy=True)
                model.apply("team-one")
                model.apply("team-two")
                self.assertTrue(first["AllowDummyBotFollow"])
                self.assertTrue(second["AllowDummyBotFollow"])
                self.assertFalse(observer["AllowDummyBotFollow"])

    def test_enemy_humans_and_normal_ai_do_not_enable_dummy_follow(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("human", team=2)
                model.add("enemy-human", team=1)
                model.add("normal-ai", team=1, IsAutomaticBot=True)
                model.apply("human")
                self.assertFalse(state["AllowDummyBotFollow"])

    def test_stale_enemy_dummy_reference_does_not_enable_follow(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("human", team=2)
                model.add("gone", team=1, dummy=True, exists=False)
                model.apply("human")
                self.assertFalse(state["AllowDummyBotFollow"])

    def test_respawning_enemy_dummy_still_counts_as_present(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("human", team=2)
                model.add("respawning", team=1, dummy=True, spawned=False, alive=False)
                model.apply("human")
                self.assertTrue(state["AllowDummyBotFollow"])

    def test_disabled_consent_can_always_be_applied_after_dummy_removal(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("human", team=2)
                dummy = model.add("dummy", team=1, dummy=True)
                model.apply("human")
                dummy.update(exists=False, visible=False)
                model.apply("human")
                self.assertFalse(state["AllowDummyBotFollow"])
                self.assertEqual(model.applied_effects(), [])

    def test_dummy_disappearing_between_menu_open_and_apply_blocks_activation(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("human", team=2)
                dummy = model.add("dummy", team=1, dummy=True)
                dummy.update(exists=False, visible=False)
                model.apply("human")
                self.assertFalse(state["AllowDummyBotFollow"])
                dummy.update(exists=True, visible=True)
                model.apply("human")
                self.assertTrue(state["AllowDummyBotFollow"])

    def test_interact_turns_existing_consent_off_even_without_dummy(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("human", AllowDummyBotFollow=True)
                model.apply("human")
                self.assertFalse(state["AllowDummyBotFollow"])
                self.assertEqual(model.applied_effects(), [])

    def test_disappearing_enemy_dummy_turns_follow_off_without_menu_and_return_requires_opt_in(self):
        for source, model in self.models():
            for team in (1, 2):
                with self.subTest(source=source, team=team):
                    model.players.clear()
                    state = model.add("human", team=team)
                    dummy = model.add("enemy", team=3 - team, dummy=True)
                    model.add("own", team=team, dummy=True)
                    model.apply("human")
                    self.assertTrue(state["AllowDummyBotFollow"])
                    model.cache_tick("human")
                    self.assertTrue(state["AllowDummyBotFollow"])
                    dummy.update(exists=False)
                    model.cache_tick("human")
                    self.assertFalse(state["AllowDummyBotFollow"])
                    dummy.update(exists=True)
                    model.cache_tick("human")
                    self.assertFalse(state["AllowDummyBotFollow"])
                    model.apply("human")
                    self.assertTrue(state["AllowDummyBotFollow"])

    def test_automatic_off_leaves_other_players_and_bot_permissions_untouched(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("human", AllowDummyBotFollow=True)
                other = model.add("other", AllowDummyBotFollow=True)
                bot = model.add("bot", IsHuman=False, dummy=True, AllowDummyBotFollow=True)
                model.cache_tick("human")
                self.assertFalse(state["AllowDummyBotFollow"])
                self.assertTrue(other["AllowDummyBotFollow"])
                model.cache_tick("bot")
                self.assertTrue(bot["AllowDummyBotFollow"])

    def test_main_menu_reads_consent_without_rebuilding_dummy_availability_queries(self):
        for source, model in self.models():
            with self.subTest(source=source):
                page = validator.rule_by_subroutine(model.rules, "DrawMainMenu")
                apply = validator.rule_by_subroutine(model.rules, "ApplyDummyBotFollowPage")
                condition = (
                    "Is True For Any(All Players(Opposite Team Of(Team Of(Event Player))), "
                    "And(Entity Exists(Current Array Element), Is Dummy Bot(Current Array Element) == True))"
                )
                self.assertEqual(page.body.count(condition), 0)
                self.assertEqual(apply.body.count(condition), 1)
                self.assertIn("LET ENEMY DUMMY FOLLOW YOU", page.body)
                self.assertNotIn("IndeksBahasa", page.body)
                self.assertNotIn("IZINKAN BOT MUSUH IKUTIMU", page.body)
                self.assertNotIn("ให้ดัมมี่ศัตรูตามคุณ", page.body)
                self.assertEqual(page.body.count("Create HUD Text("), 1)
                self.assertNotIn("Wait(", apply.body)
                self.assertNotIn("Filtered Array(", apply.body)


if __name__ == "__main__":
    unittest.main()
