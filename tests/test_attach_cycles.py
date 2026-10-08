"""Execute the source's bounded attach traversal; engine movement needs live QA."""
import re
import unittest

from tools import validate_workshop as validator
from tests.test_roster_rejoin_regressions import LifecycleSourceEvaluator


class AttachEvaluator(LifecycleSourceEvaluator):
    def call(self, name, args):
        if name == 'AllPlayers':
            return list(self.players)
        if name == 'PlayerVariable':
            return self.players.get(args[0], {}).get(args[1], None)
        return super().call(name, args)

    def resolve(self, name):
        if name in ('AllTeams', 'TravelAttachmentActive', 'TravelAttachmentTarget'):
            return name
        return super().resolve(name)

    def execute(self, statements):
        """Small strict interpreter for If/Else and bounded For Player Variable."""
        index = 0
        while index < len(statements):
            statement = statements[index]
            if statement.startswith(('If(', 'For Player Variable(')):
                depth = 1
                end = index + 1
                branches = [index]
                while depth:
                    token = statements[end]
                    if token.startswith(('If(', 'For Player Variable(')):
                        depth += 1
                    elif token == 'End':
                        depth -= 1
                    elif depth == 1 and token.startswith(('Else If(', 'Else')):
                        branches.append(end)
                    if depth:
                        end += 1
                if statement.startswith('For Player Variable('):
                    call = next(validator.iter_calls(statement + ';', 'For Player Variable'))
                    owner, variable, start, stop, step = call.args
                    self.assert_event_owner(owner)
                    for value in range(int(self.evaluate(start)), int(self.evaluate(stop)), int(self.evaluate(step))):
                        self.assign('Event Player.' + variable, value)
                        self.execute(statements[index + 1:end])
                else:
                    branches.append(end)
                    for first, last in zip(branches, branches[1:]):
                        condition = statements[first]
                        if condition == 'Else' or self.evaluate(condition[condition.index('(') + 1:-1]):
                            self.execute(statements[first + 1:last])
                            break
                index = end + 1
            else:
                self.execute_assignment(statement)
                index += 1

    @staticmethod
    def assert_event_owner(owner):
        if owner != 'Event Player':
            raise AssertionError('attach traversal must own its player counter')

    def refused(self, owner, target):
        self.event_player = owner
        self.players[owner]['LockedTravelTarget'] = target
        rule = next(rule for rule in self.rules if rule.name.startswith('19e -'))
        actions = validator.mask_strings(validator.rule_block(rule, 'actions'))
        start = actions.index('Event Player.AttachmentChain =')
        stop = actions.index('If(Or(Or(Event Player.LockedTravelTarget', start)
        self.execute([s.strip() for s in actions[start:stop].split(';') if s.strip()])
        gate = next(call for call in validator.iter_calls(actions, 'Else If')
                    if 'AttachmentCycleDetected' in call.raw)
        return bool(self.evaluate(gate.args[0]))


class AttachCycleTests(unittest.TestCase):
    def model(self, edges, extra=()):
        model = AttachEvaluator(validator.SOURCE.read_text(encoding='utf-8'))
        for identity in set(edges) | set(edges.values()) | set(extra):
            model.players[identity] = {
                'TravelAttachmentActive': identity in edges,
                'TravelAttachmentTarget': edges.get(identity),
            }
        return model

    def test_three_player_and_longer_cycles_are_rejected_without_changing_edges(self):
        for count in (3, 6, 12):
            with self.subTest(count=count):
                edges = {f'p{i}': f'p{i+1}' for i in range(count-1)}
                model = self.model(edges)
                self.assertTrue(model.refused(f'p{count-1}', 'p0'))
                self.assertEqual({p: state['TravelAttachmentTarget'] for p, state in model.players.items()},
                                 {p: edges.get(p) for p in model.players})

    def test_valid_chain_and_bot_endpoint_are_allowed(self):
        model = self.model({'alice': 'bob', 'bob': 'dummy'}, extra=('carol',))
        self.assertFalse(model.refused('carol', 'alice'))
        self.assertFalse(model.refused('carol', 'dummy'))

    def test_self_two_player_and_preexisting_disconnected_cycle_are_rejected(self):
        model = self.model({'alice': 'bob', 'bob': 'alice'}, extra=('carol',))
        self.assertTrue(model.refused('carol', 'carol'))
        self.assertTrue(model.refused('bob', 'alice'))
        self.assertTrue(model.refused('carol', 'alice'))

    def test_one_players_failed_attempt_does_not_poison_another_players_attempt(self):
        model = self.model({'alice': 'bob'}, extra=('carol',))
        self.assertTrue(model.refused('bob', 'alice'))
        self.assertFalse(model.refused('carol', 'alice'))
        self.assertTrue(model.players['bob']['AttachmentCycleDetected'])

    def test_team_quarantine_detaches_incoming_attachment_even_with_same_hero(self):
        rule = next(rule for rule in validator.extract_rules(validator.SOURCE.read_text(encoding='utf-8'))
                    if rule.name.startswith('19h -'))
        conditions = validator.rule_block(rule, 'conditions')
        self.assertIn('Player Variable(Event Player.TravelAttachmentTarget, PlayerCycleActive) == True', conditions)
        self.assertIn('Detach Players(Event Player);', validator.rule_block(rule, 'actions'))


if __name__ == '__main__':
    unittest.main()
