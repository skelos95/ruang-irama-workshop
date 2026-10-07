"""Exercise actual emitted colour values across global dispatch boundaries.

None snapshots a Chase destination at the command; the deferred-mode mutation
models a first reevaluation after dispatch clears its actor. This is a regression
model, not a simulation of native colour rendering or a team-change crash.
"""
from pathlib import Path
import unittest

from tests.test_fly_motion import Vector
from tests.test_global_compaction import CompactionContext
from tools import validate_global_runtime as gate
from tools import validate_workshop as semantic


ROOT = Path(__file__).resolve().parents[1]


class MenuColors(CompactionContext):
    def __init__(self, fields):
        super().__init__(fields)
        self.players = {}
        self.jobs = {}

    def resolve(self, name):
        if name.startswith('Global.') and len(name.split('.')) == 3:
            _, actor, field = name.split('.')
            return self.players.get(self.globals[actor], {}).get(field, 0)
        return super().resolve(name)

    def call(self, name, args):
        if name == 'PlayerVariable':
            return self.players.get(args[0], {}).get(args[1], 0)
        return super().call(name, args)

    def value(self, expression):
        return self.parse(expression).evaluate(self)

    def snapshot(self, expression):
        captures = list(semantic.iter_calls(expression, 'Evaluate Once'))
        outer = [call for call in captures if not any(
            other.start < call.start and other.end >= call.end for other in captures)]
        for call in reversed(outer):
            key = 'Capture' + str(len(self.values))
            self.values[key] = self.value(call.args[0])
            expression = expression[:call.start] + key + expression[call.end:]
        return expression

    def command(self, chase, mode=None):
        owner = self.value(chase.args[0])
        reevaluation = mode or chase.args[4]
        destination = self.value(chase.args[2]) if reevaluation == 'None' else None
        self.jobs[owner] = (destination, chase.args[2])

    def frame_destination(self, owner):
        destination, deferred = self.jobs[owner]
        if destination is None:
            destination = self.value(self.snapshot(deferred))
            self.jobs[owner] = (destination, deferred)
        return destination


class GlobalMenuColorSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = gate.english((ROOT / 'workshop/ruang_irama.it-IT.workshop').read_text(encoding='utf-8'))
        cls.rules = semantic.extract_rules(cls.text)
        cls.palette = next(rule for rule in cls.rules if rule.name.startswith('91k -'))
        cls.chases = list(semantic.iter_calls(cls.palette.body, 'Chase Player Variable Over Time'))
        cls.travel, cls.menu = cls.chases
        _, fields, _, _ = semantic.declaration_entries(cls.text)
        cls.fields = {field.name for field in fields}
        bootstrap = next(rule for rule in cls.rules if rule.name.startswith('00 -'))
        statement = next(statement for statement in semantic.split_top_level(
            semantic.rule_block(bootstrap, 'actions'), ';')
            if statement.strip().startswith('Global.DaftarWarnaRGB ='))
        cls.colors = MenuColors(cls.fields).value(statement.split('=', 1)[1].strip())

    def model(self, count=12):
        model = MenuColors(self.fields)
        model.globals['DaftarWarnaRGB'] = self.colors
        for index in range(count):
            model.players['owner' + str(index)] = dict(
                HalamanMenu=-1, KursorUtama=0, KursorWarna=index + 2,
                IndeksWarna=index + 2, KursorTeleportasi=index % 5)
        return model

    def test_only_two_menu_chases_snapshot_and_keep_native_smoothing_and_owner(self):
        self.assertEqual(len(self.chases), 2)
        for chase in self.chases:
            self.assertEqual(chase.args[0], 'Evaluate Once(Global.PemainPemicu)')
            self.assertEqual(chase.args[1], 'WarnaMenu')
            self.assertEqual(chase.args[3:], ('0.180', 'None'))
        self.assertFalse(gate.validate_runtime(self.text))

    def test_twelve_players_keep_distinct_preview_colors_after_actor_is_cleared(self):
        model = self.model()
        for color in range(len(self.colors)):
            expected = {}
            for index, owner in enumerate(model.players):
                model.globals['PemainPemicu'] = owner
                cursor = (color + index) % len(self.colors)
                model.players[owner]['KursorWarna'] = cursor
                expected[owner] = self.colors[cursor]
                model.command(self.menu)
            model.globals['PemainPemicu'] = None
            for owner in model.players:
                self.assertEqual(model.frame_destination(owner), expected[owner])

    def test_all_five_travel_colors_work_for_twelve_owners_across_dispatch(self):
        model = self.model()
        colors = [Vector(80, 255, 160), Vector(65, 225, 255), Vector(95, 150, 255),
                  Vector(195, 100, 255), Vector(255, 85, 135)]
        for page in range(5):
            expected = {}
            for index, owner in enumerate(model.players):
                cursor = (page + index) % 5
                model.globals['PemainPemicu'] = owner
                model.players[owner]['KursorTeleportasi'] = cursor
                expected[owner] = colors[cursor]
                model.command(self.travel)
            model.globals['PemainPemicu'] = None
            for owner in model.players:
                self.assertEqual(model.frame_destination(owner), expected[owner])

    def test_repeated_main_and_submenu_navigation_retargets_only_its_owner(self):
        model = self.model(2)
        model.globals['PemainPemicu'] = 'owner1'
        model.command(self.menu)
        untouched = model.frame_destination('owner1')
        for page in range(16):
            for main in (True, False):
                player = model.players['owner0']
                player.update(HalamanMenu=-1 if main else page, KursorUtama=page)
                model.globals['PemainPemicu'] = 'owner0'
                expected = model.value(self.menu.args[2])
                model.command(self.menu)
                model.globals['PemainPemicu'] = None
                self.assertEqual(model.frame_destination('owner0'), expected)
                self.assertEqual(model.frame_destination('owner1'), untouched)

    def test_deferred_mode_mutation_reproduces_white_and_green_with_zero_cursor(self):
        model = self.model(2)
        model.globals['PemainPemicu'] = 'owner0'
        model.players['owner0'].update(KursorWarna=12, KursorTeleportasi=4)
        intended_menu = model.value(self.menu.args[2])
        intended_travel = model.value(self.travel.args[2])
        model.command(self.menu, mode='Destination and Duration')
        model.globals['PemainPemicu'] = 'owner1'
        model.players['owner1']['KursorTeleportasi'] = 4
        model.command(self.travel, mode='Destination and Duration')
        model.globals['PemainPemicu'] = None
        self.assertEqual(model.frame_destination('owner0'), self.colors[0])
        self.assertEqual(model.frame_destination('owner1'), Vector(80, 255, 160))
        self.assertNotEqual(model.frame_destination('owner0'), intended_menu)
        self.assertNotEqual(model.frame_destination('owner1'), intended_travel)

    def test_gate_rejects_async_destination_duration_or_extra_menu_chase(self):
        for call in self.chases:
            for old, new in ((', 0.180, None)', ', 0.180, Destination and Duration)'),
                             (', 0.180, None)', ', 0.000, None)')):
                body = self.palette.body[:call.start] + call.raw.replace(old, new) + self.palette.body[call.end:]
                text = self.text[:self.palette.start] + body + self.text[self.palette.end:]
                self.assertTrue(any('colori menu' in error for error in gate.validate_runtime(text)))
        extra = 'Chase Player Variable Over Time(Evaluate Once(Global.PemainPemicu), WarnaMenu, Vector(1, 2, 3), 0.180, None);'
        body = self.palette.body.replace(self.travel.raw + ';', self.travel.raw + ';\n' + extra, 1)
        text = self.text[:self.palette.start] + body + self.text[self.palette.end:]
        self.assertTrue(any('colori menu' in error for error in gate.validate_runtime(text)))


if __name__ == '__main__':
    unittest.main()
