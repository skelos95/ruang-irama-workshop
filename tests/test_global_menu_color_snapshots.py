"""Exercise actual emitted colour values across global dispatch boundaries.

None snapshots a Chase destination at the command; the deferred-mode mutation
models a first reevaluation after dispatch clears its actor. This is a regression
model, not a simulation of native colour rendering or a team-change crash.
"""
from pathlib import Path
import unittest

from tests.test_fly_motion import Vector
from tests.test_global_compaction import CompactionContext
from tests.runtime_selection import rule_for_logical_id
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
        cls.text = gate.english((ROOT / 'workshop/ruang_irama.en-US.workshop').read_text(encoding='utf-8'))
        cls.rules = semantic.extract_rules(cls.text)
        cls.palette = semantic.rule_by_subroutine(cls.rules, "TransitionMenuColor")
        cls.chases = list(semantic.iter_calls(cls.palette.body, 'Chase Player Variable Over Time'))
        cls.travel, cls.menu = cls.chases
        _, fields, _, _ = semantic.declaration_entries(cls.text)
        cls.fields = {field.name for field in fields}
        bootstrap = rule_for_logical_id(cls.rules, "00")
        statement = next(statement for statement in semantic.split_top_level(
            semantic.rule_block(bootstrap, 'actions'), ';')
            if statement.strip().startswith('Global.NameColorRGBValues ='))
        cls.colors = MenuColors(cls.fields).value(statement.split('=', 1)[1].strip())

    def model(self, count=12):
        model = MenuColors(self.fields)
        model.globals['NameColorRGBValues'] = self.colors
        for index in range(count):
            model.players['owner' + str(index)] = dict(
                MenuPage=-1, MainMenuCursor=1, ColorCursor=index + 2,
                ColorIndex=index + 2, TravelCursor=index % 5)
        return model

    def test_only_two_menu_chases_snapshot_and_keep_native_smoothing_and_owner(self):
        self.assertEqual(len(self.chases), 2)
        for chase in self.chases:
            self.assertEqual(chase.args[0], 'Evaluate Once(Global.TriggerPlayer)')
            self.assertEqual(chase.args[1], 'MenuColor')
            self.assertEqual(chase.args[3:], ('0.180', 'None'))
        self.assertFalse(gate.validate_runtime(self.text))

    def test_twelve_players_keep_distinct_preview_colors_after_actor_is_cleared(self):
        model = self.model()
        for color in range(len(self.colors)):
            expected = {}
            for index, owner in enumerate(model.players):
                model.globals['TriggerPlayer'] = owner
                cursor = (color + index) % len(self.colors)
                model.players[owner]['ColorCursor'] = cursor
                expected[owner] = self.colors[cursor]
                model.command(self.menu)
            model.globals['TriggerPlayer'] = None
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
                model.globals['TriggerPlayer'] = owner
                model.players[owner]['TravelCursor'] = cursor
                expected[owner] = colors[cursor]
                model.command(self.travel)
            model.globals['TriggerPlayer'] = None
            for owner in model.players:
                self.assertEqual(model.frame_destination(owner), expected[owner])

    def test_repeated_main_and_submenu_navigation_retargets_only_its_owner(self):
        model = self.model(2)
        model.globals['TriggerPlayer'] = 'owner1'
        model.command(self.menu)
        untouched = model.frame_destination('owner1')
        for page in range(16):
            for main in (True, False):
                player = model.players['owner0']
                player.update(MenuPage=-1 if main else page, MainMenuCursor=page)
                model.globals['TriggerPlayer'] = 'owner0'
                expected = model.value(self.menu.args[2])
                model.command(self.menu)
                model.globals['TriggerPlayer'] = None
                self.assertEqual(model.frame_destination('owner0'), expected)
                self.assertEqual(model.frame_destination('owner1'), untouched)

    def test_info_and_default_name_color_remain_distinct_after_dispatch(self):
        model = self.model(2)
        for main in (True, False):
            for owner, page in (("owner0", 0), ("owner1", 1)):
                model.players[owner].update(MenuPage=-1 if main else page,
                                           MainMenuCursor=page, ColorCursor=0, ColorIndex=0)
                model.globals['TriggerPlayer'] = owner
                model.command(self.menu)
            model.globals['TriggerPlayer'] = None
            self.assertEqual(model.frame_destination('owner0'), Vector(160, 195, 235))
            self.assertEqual(model.frame_destination('owner1'), self.colors[0])
            self.assertNotEqual(model.frame_destination('owner0'), model.frame_destination('owner1'))

    def test_deferred_mode_mutation_reproduces_info_accent_and_green_with_zero_cursor(self):
        model = self.model(2)
        model.globals['TriggerPlayer'] = 'owner0'
        model.players['owner0'].update(ColorCursor=12, TravelCursor=4)
        intended_menu = model.value(self.menu.args[2])
        intended_travel = model.value(self.travel.args[2])
        model.command(self.menu, mode='Destination and Duration')
        model.globals['TriggerPlayer'] = 'owner1'
        model.players['owner1']['TravelCursor'] = 4
        model.command(self.travel, mode='Destination and Duration')
        model.globals['TriggerPlayer'] = None
        self.assertEqual(model.frame_destination('owner0'), Vector(160, 195, 235))
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
        extra = 'Chase Player Variable Over Time(Evaluate Once(Global.TriggerPlayer), MenuColor, Vector(1, 2, 3), 0.180, None);'
        body = self.palette.body.replace(self.travel.raw + ';', self.travel.raw + ';\n' + extra, 1)
        text = self.text[:self.palette.start] + body + self.text[self.palette.end:]
        self.assertTrue(any('colori menu' in error for error in gate.validate_runtime(text)))


if __name__ == '__main__':
    unittest.main()
