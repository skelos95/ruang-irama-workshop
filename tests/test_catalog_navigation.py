"""Exercise the source's catalog cursor expressions and localized headings.

The existing menu evaluator projects cursor assignments under the real rule's
guards. It does not emulate native HUD rendering or Workshop performance.
"""

import hashlib
import math
import re
import unittest

from tools import check_clipboard_import as clipboard
from tools import validate_workshop as validator
from tests.test_fly_motion import Expression
from tests.test_menu_load_regressions import MenuLoadEvaluator
from tests.test_roster_rejoin_regressions import ROOT, SOURCES


PALETTE_ARRAY_NAMES = (
    "NamaWarnaInggris", "DaftarWarna", "DaftarWarnaRGB", "NamaWarna", "NamaWarnaThai",
)
EXPECTED_PALETTE_ORDER = (
    "Snow White", "Silver Mist", "Charcoal", "Black", "Ivory", "Lemon Pop", "Sunny Gold",
    "Peach Glow", "Apricot Neon", "Warm Orange", "Bronze", "Coral Glow", "Crimson Red",
    "Wine Red", "Cherry Blossom", "Neon Pink", "Rose Pink", "Hot Magenta", "Soft Lavender",
    "Fuchsia Dream", "Electric Purple", "Neon Violet", "Plum", "Ice Blue", "Sky Blue",
    "Soft Periwinkle", "Ocean Blue", "Royal Blue", "Electric Indigo", "Midnight Blue",
    "Cyan Neon", "Cool Aqua", "Seafoam", "Fresh Mint", "Jade Glow", "Chill Turquoise",
    "Neon Chartreuse", "Lime Green", "Emerald Green", "Forest Green",
)
# Hash all forty records, sorted by English label, preserving each label's actual
# color, preview RGB, Indonesian label, and Thai label. Captured from main
# 23f892b70027c90cb0fc217e4f4e7da0d31c4d62 with Black's preview corrected to (0, 0, 0).
# The expected hash is available without Git in the workflow's shallow checkout.
PALETTE_RECORDS_DIGEST = "f3e22b795d8ab9e12c6dbc49d45902a504dec43c0462bf7e63cf39f2f2a25ed6"
OLD_GENRE_GROUPS = (
    "375e0d302f43aa81daf5343b19ed175097d024ea554ecb228754c0327e39fe1a",
    "4d19059cb1cf07e58a4eed4666c8efa8bb685c884052bc821f7602616c1d0251",
    "3e6c6dba7d4bc7c3268312ad7302fb7c6bcdf688f271bd6ed60e47b6df621cf2",
    "22d83292980f701fe4cfc38c49d9b85999951d4de938033714856e4767c420a4",
    "9193cd61df49786e972a1cd318ddd2569953bf252fdd89cee9aec4d98ec79a6b",
    "ab771ddc832c42efb49e08584b30d2306ade0cdbc80d02a0f3781c949eb8120d",
    "fa9fab75c020786b989b292b628bfe8913d0b3ef6be3c5692c09ad2939eeba01",
    "e81cc30e8b2d3604fd8b32933a325bd7db1658901cdbbdb7e8155310a4c85636",
    "b10d38b79a5c2bf410d17da736003c44d73fa879baf66791138d0e9175b89ac1",
    "c69ac8c3e50151699a23b10d10784cebd3c9bc7c429339a0cceb6a7e191a5855",
)


def prefix_digest(items):
    canonical = clipboard.canonical_semantic_text("Array(" + ",".join(items) + ")", "en-US")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class CatalogMenuEvaluator(MenuLoadEvaluator):
    def __init__(self, source):
        super().__init__(source)
        normalized = "\n".join(rule.body for rule in self.rules)
        names = (*PALETTE_ARRAY_NAMES, "DaftarGenre", "NamaHalaman", "NamaHalamanInggris", "NamaHalamanThai")
        self.items = {name: validator.array_assignment_items(normalized, name) for name in names}
        if any(items is None for items in self.items.values()):
            raise AssertionError("catalog initializer array missing")
        for name, items in self.items.items():
            self.globals[name] = [self.evaluate(item) for item in items]

    def resolve(self, name):
        named_colors = {re.sub(r"\s+", "", color) for _, color in clipboard.EQUIVALENT_NAMED_COLORS}
        if name == "Down" or name in named_colors:
            return name
        return super().resolve(name)

    def call(self, name, args):
        if name in ("CustomColor", "Vector"):
            return tuple(args)
        if name == "Color":
            return next(components for components, color in clipboard.EQUIVALENT_NAMED_COLORS
                        if re.sub(r"\s+", "", color) == args[0])
        if name == "RoundToInteger":
            if args[1] != "Down":
                raise AssertionError("catalog group uses an unsupported rounding mode")
            return math.floor(args[0])
        return super().call(name, args)

    def add_viewer(self, name="viewer", **changes):
        state = dict(MenuTerbuka=True, HalamanMenu=2, MusikKhusus=None,
                     KursorGenre=0, KursorWarna=0, PerintahMenu=3, IndeksGenre=-1)
        state.update(changes)
        return self.add(name, **state)

    def navigate(self, owner, field, command, *, jump=False):
        self.players[owner]["PerintahMenu"] = command
        prefix = "08" if jump else "06"
        if not self.conditions(prefix, owner):
            return
        if jump:
            self.run(prefix, owner)
            return
        # Project the actual assignment, rather than reimplementing its modulo.
        actions = validator.rule_block(self.rule(prefix), "actions")
        matches = re.findall(rf"Event Player\.{field}\s*=[^;]+;", actions)
        if len(matches) != 1:
            raise AssertionError(f"expected one source assignment for {field}")
        self.execute(matches[0])


class CatalogNavigationTests(unittest.TestCase):
    def models(self):
        for path, _, _ in SOURCES:
            yield path.name, CatalogMenuEvaluator(path.read_text(encoding="utf-8"))

    def test_single_genre_steps_cross_group_and_catalog_boundaries(self):
        cases = {0: (1, 199), 19: (20, 18), 20: (21, 19), 199: (0, 198)}
        for source, model in self.models():
            viewer = model.add_viewer()
            for start, expected in cases.items():
                for command, target in zip((3, 4), expected):
                    with self.subTest(source=source, start=start, command=command):
                        viewer["KursorGenre"] = start
                        model.navigate("viewer", "KursorGenre", command)
                        self.assertEqual(viewer["KursorGenre"], target)

    def test_ten_genre_jumps_cross_group_and_catalog_boundaries(self):
        cases = {0: (10, 190), 19: (29, 9), 20: (30, 10), 199: (9, 189)}
        for source, model in self.models():
            viewer = model.add_viewer()
            for start, expected in cases.items():
                for command, target in zip((5, 6), expected):
                    with self.subTest(source=source, start=start, command=command):
                        viewer["KursorGenre"] = start
                        model.navigate("viewer", "KursorGenre", command, jump=True)
                        self.assertEqual(viewer["KursorGenre"], target)

    def test_every_genre_is_reachable_in_one_cursor_cycle(self):
        for source, model in self.models():
            with self.subTest(source=source):
                viewer = model.add_viewer()
                visited = set()
                for _ in range(200):
                    visited.add(viewer["KursorGenre"])
                    model.navigate("viewer", "KursorGenre", 3)
                self.assertEqual(visited, set(range(200)))
                self.assertEqual(viewer["KursorGenre"], 0)

    def test_navigation_uses_loaded_array_lengths_instead_of_fixed_limits(self):
        for source, model in self.models():
            with self.subTest(source=source):
                viewer = model.add_viewer()
                model.globals["DaftarGenre"].extend(f"future-{i}" for i in range(10))
                model.navigate("viewer", "KursorGenre", 4)
                self.assertEqual(viewer["KursorGenre"], 209)
                model.navigate("viewer", "KursorGenre", 3)
                self.assertEqual(viewer["KursorGenre"], 0)
                viewer["KursorGenre"] = 199
                model.navigate("viewer", "KursorGenre", 5, jump=True)
                self.assertEqual(viewer["KursorGenre"], 209)
                model.navigate("viewer", "KursorGenre", 6, jump=True)
                self.assertEqual(viewer["KursorGenre"], 199)
                model.globals["DaftarWarna"].extend(((10, 20, 30, 255), (40, 50, 60, 255)))
                viewer["HalamanMenu"] = 0
                model.navigate("viewer", "KursorWarna", 4)
                self.assertEqual(viewer["KursorWarna"], 41)
                model.navigate("viewer", "KursorWarna", 3)
                self.assertEqual(viewer["KursorWarna"], 0)

    def test_navigation_of_two_players_keeps_independent_cursors(self):
        for source, model in self.models():
            with self.subTest(source=source):
                first = model.add_viewer("first", KursorGenre=199)
                second = model.add_viewer("second", KursorGenre=20)
                model.navigate("first", "KursorGenre", 3)
                self.assertEqual((first["KursorGenre"], second["KursorGenre"]), (0, 20))
                model.navigate("second", "KursorGenre", 4)
                self.assertEqual((first["KursorGenre"], second["KursorGenre"]), (0, 19))

    def test_ten_genre_jump_respects_locked_music_and_menu_guards(self):
        changes = ({"MusikKhusus": "Draconian"}, {"HalamanMenu": 0},
                   {"MenuTerbuka": False}, {"alive": False})
        for source, model in self.models():
            for index, change in enumerate(changes):
                with self.subTest(source=source, change=change):
                    owner = f"viewer-{index}"
                    viewer = model.add_viewer(owner, KursorGenre=199, **change)
                    model.navigate(owner, "KursorGenre", 5, jump=True)
                    self.assertEqual(viewer["KursorGenre"], 199)

    def test_two_hundred_unique_genres_keep_original_ten_first_in_each_group(self):
        requested = {"Synthwave", "Doom Metal", "Atmospheric Black Metal", "Gothic Metal",
                     "Hip-Hop", "Trap", "Moombahton"}
        for source, model in self.models():
            with self.subTest(source=source):
                genres = model.globals["DaftarGenre"]
                self.assertEqual(len(genres), 200)
                self.assertEqual(len(set(genres)), 200)
                self.assertLessEqual(requested, set(genres))
                for group, digest in enumerate(OLD_GENRE_GROUPS):
                    self.assertEqual(prefix_digest(model.items["DaftarGenre"][group*20:group*20+10]), digest)

    def test_documentation_lists_exact_runtime_catalog_and_group_headings(self):
        documentation = (ROOT / "docs" / "GENERI.md").read_text(encoding="utf-8")
        listed = re.findall(r"^([0-9]+)\. (.+)$", documentation, re.M)
        headings = re.findall(r"^## Gruppo ([0-9]+)/10 — (.+)$", documentation, re.M)
        for source, model in self.models():
            with self.subTest(source=source):
                self.assertEqual(listed, [(str(i+1), genre) for i, genre in enumerate(model.globals["DaftarGenre"])])
                self.assertEqual(headings, [(str(i+1), heading) for i, heading in enumerate(model.globals["NamaHalaman"])])
                for name in ("NamaHalaman", "NamaHalamanInggris", "NamaHalamanThai"):
                    self.assertEqual(len(model.globals[name]), 10)

    def test_music_hud_counter_displays_actual_catalog_length_in_all_languages(self):
        for source, model in self.models():
            viewer = model.add_viewer(IndeksGenre=199)
            model.event_player = "viewer"
            music = validator.rule_by_subroutine(model.rules, "GambarMusik")
            headers = [call for call in validator.iter_calls(music.body, "Custom String")
                       if call.args and (validator.parse_literal(call.args[0]) or "").startswith(
                           ("2 - SOUNDTRACK ", "2 - MUSIK ", "2 - เพลงประกอบ "))]
            self.assertEqual(len(headers), 3)
            for cursor in (0, 19, 20, 199):
                viewer["KursorGenre"] = cursor
                for header in headers:
                    with self.subTest(source=source, cursor=cursor, header=header.args[0]):
                        rendered = model.evaluate(header.raw)
                        self.assertIn(f"{cursor+1}/200", rendered)
                        self.assertIn(model.globals["DaftarGenre"][199], rendered)

    def test_music_hud_group_selection_uses_twenty_entries_per_group(self):
        for source, model in self.models():
            viewer = model.add_viewer()
            model.event_player = "viewer"
            music = validator.rule_by_subroutine(model.rules, "GambarMusik")
            selectors = list(validator.iter_calls(music.body, "Round To Integer"))
            self.assertEqual(len(selectors), 3)
            for cursor, group in ((0, 0), (19, 0), (20, 1), (39, 1), (180, 9), (199, 9)):
                viewer["KursorGenre"] = cursor
                for selector in selectors:
                    with self.subTest(source=source, cursor=cursor):
                        expression = Expression(re.sub(r"\s+", "", selector.raw))
                        self.assertEqual(expression.evaluate(model), group)

    def test_palette_reordering_preserves_all_forty_color_records(self):
        for source, model in self.models():
            for name in PALETTE_ARRAY_NAMES:
                with self.subTest(source=source, array=name):
                    self.assertEqual(len(model.items[name]), 40)
            with self.subTest(source=source):
                self.assertEqual(tuple(model.globals["NamaWarnaInggris"]), EXPECTED_PALETTE_ORDER)
                records = sorted(zip(*(model.items[name] for name in PALETTE_ARRAY_NAMES)),
                                 key=lambda record: record[0])
                self.assertEqual(prefix_digest(["Array(" + ",".join(record) + ")" for record in records]),
                                 PALETTE_RECORDS_DIGEST)

    def test_black_name_color_uses_pure_black_for_actual_color_and_menu_preview(self):
        for source, model in self.models():
            with self.subTest(source=source):
                self.assertEqual(model.globals["DaftarWarna"][3], (0, 0, 0, 255))
                self.assertEqual(model.globals["DaftarWarnaRGB"][3], (0, 0, 0))
                self.assertEqual(model.globals["NamaWarnaInggris"][3], "Black")
                self.assertEqual(model.globals["NamaWarna"][3], "Hitam")
                self.assertEqual(model.globals["NamaWarnaThai"][3], "ดำ")

    def test_color_navigation_crosses_black_and_wraps_all_forty_colors(self):
        cases = {0: (1, 39), 2: (3, 1), 3: (4, 2), 4: (5, 3), 39: (0, 38)}
        for source, model in self.models():
            viewer = model.add_viewer(HalamanMenu=0)
            for start, expected in cases.items():
                for command, target in zip((3, 4), expected):
                    with self.subTest(source=source, start=start, command=command):
                        viewer["KursorWarna"] = start
                        model.navigate("viewer", "KursorWarna", command)
                        self.assertEqual(viewer["KursorWarna"], target)


if __name__ == "__main__":
    unittest.main()
