"""Execute the real persistent menu, cache detector and cleanup statements.

Native rendering/hero queries and input bindings are controlled values. This
checks cache freshness and ownership, not Overwatch rendering or server load.
"""
from __future__ import annotations

import math
import operator
import re
import unittest

from tests.test_menu_load_regressions import MenuLoadEvaluator
from tests.test_roster_rejoin_regressions import SOURCES
from tests.test_dummy_spawn_retry import SpawnExpression
from tools import validate_workshop as validator


class IndexedMenuExpression(SpawnExpression):
    TOKEN = re.compile(SpawnExpression.TOKEN.pattern + r"|[\[\]]|\.[A-Za-z_][A-Za-z_0-9]*")

    def parse(self, minimum=0):
        token = self.take()
        if token == "-":
            left = ("negate", self.parse(4))
        elif token == "(":
            left = self.parse()
            self.take(")")
        elif token[0].isdigit():
            left = ("literal", float(token))
        elif self.peek() == "(":
            self.take("(")
            args = []
            if self.peek() != ")":
                while True:
                    args.append(self.parse())
                    if self.peek() != ",":
                        break
                    self.take(",")
            self.take(")")
            left = ("call", token, args)
        else:
            left = ("name", token)
        while self.peek() == "[" or (self.peek() or "").startswith("."):
            if self.peek() == "[":
                self.take("[")
                left = ("index", left, self.parse())
                self.take("]")
            else:
                left = ("field", left, self.take()[1:])
        while self.peek() in self.PRECEDENCE and self.PRECEDENCE[self.peek()] >= minimum:
            op = self.take()
            left = (op, left, self.parse(self.PRECEDENCE[op] + 1))
        if minimum == 0 and self.peek() == "?":
            self.take("?")
            yes = self.parse()
            self.take(":")
            left = ("conditional", left, yes, self.parse())
        return left


class PersistentMenuEvaluator(MenuLoadEvaluator):
    def __init__(self, source):
        super().__init__(source)
        self.hud_args = {}
        self.body_writes = []
        self.bindings = {}
        self.hero_queries = []
        self.globals["Siap"] = True
        for name in ("DaftarGenre", "NamaHalaman", "NamaHalamanInggris", "NamaHalamanThai",
                     "NamaWarna", "NamaWarnaInggris", "NamaWarnaThai", "DaftarWarna",
                     "DaftarIkon", "NamaIkonIndonesia", "NamaIkonInggris", "NamaIkonThai"):
            self.globals[name] = [f"{name}-{index}" for index in range(100)]
        self.globals["NamaBahasa"] = ["English", "Indonesia", "ไทย"]

    def add(self, name, **changes):
        state = super().add(name, **changes)
        defaults = dict(MenuTerbuka=True, TeleportasiJongkokAktif=False,
                        HalamanMenu=-1, MusikKhusus=None, TargetKamera=None,
                        PemainDipilih=None, SalinanMenu=[], TeksMenuIsi=None,
                        PetunjukMenu=None, WarnaPetunjukMenu=None,
                        DaftarTargetKamera=[], DaftarTargetBalasDendam=[],
                        PembunuhBalasDendam=[], JumlahBalasDendam=[],
                        hero="Echo", duplicate=None, WarnaMenu=(255, 255, 255))
        for key, value in defaults.items():
            if key not in changes:
                state[key] = value
        return state

    def field(self, owner, field):
        return self.players.get(owner, {}).get(field, 0)

    def resolve(self, name):
        if name.startswith("EventPlayer."):
            value = self.event_player
            for field in name.split(".")[1:]:
                value = self.field(value, field)
            return value
        if name.startswith("Global."):
            parts = name.split(".")
            value = self.globals.get(parts[1], 0)
            for field in parts[2:]:
                value = self.field(value, field)
            return value
        constants = {"PrimaryFire", "SecondaryFire", "Interact", "Reload", "Ability1",
                     "Ability2", "Jump", "Crouch", "Ultimate", "Down", "Up", "White",
                     "MenuPerluDigambar"}
        if name in constants:
            return name
        return super().resolve(name)

    @staticmethod
    def at(values, index):
        # Workshop's absent array element behaves as an empty value, never as
        # Python's negative index into the end of a list.
        return values[int(index)] if isinstance(values, list) and 0 <= index < len(values) else None

    def evaluate(self, expression):
        if expression not in self.expressions:
            def literal(match):
                key = f"_literal{len(self.literals)}"
                self.literals[key] = match[0][1:-1].replace(r"\n", "\n").replace(r'\"', '"')
                return key
            packed = re.sub(r'"(?:\\.|[^"\\])*"', literal, expression)
            self.expressions[expression] = IndexedMenuExpression(re.sub(r"\s+", "", packed)).tree
        ops = {"+": operator.add, "-": operator.sub, "*": operator.mul,
               "/": operator.truediv, "%": operator.mod, "==": operator.eq,
               "!=": operator.ne, ">": operator.gt, "<": operator.lt,
               ">=": operator.ge, "<=": operator.le}

        def visit(node):
            kind = node[0]
            if kind == "literal": return node[1]
            if kind == "name": return self.resolve(node[1])
            if kind == "negate": return -visit(node[1])
            if kind == "index": return self.at(visit(node[1]), visit(node[2]))
            if kind == "field": return self.field(visit(node[1]), node[2])
            if kind == "conditional": return visit(node[2] if visit(node[1]) else node[3])
            if kind != "call": return ops[kind](visit(node[1]), visit(node[2]))
            name, args = node[1:]
            if name in ("And", "Or"):
                return (all if name == "And" else any)(bool(visit(arg)) for arg in args)
            if name == "IsTrueForAny":
                previous = self.element
                try:
                    for self.element in visit(args[0]):
                        if visit(args[1]): return True
                    return False
                finally:
                    self.element = previous
            return self.call(name, [visit(arg) for arg in args])
        return visit(self.expressions[expression])

    def call(self, name, args):
        if name == "Array": return args
        if name == "CustomColor": return tuple(args)
        if name == "Color": return args[0]
        if name == "RoundToInteger": return (math.floor if args[1] == "Down" else math.ceil)(args[0])
        if name == "Min": return min(args)
        if name == "Max": return max(args)
        if name in ("HeroOf", "IsDuplicating", "HeroBeingDuplicated"):
            self.hero_queries.append((name, args[0]))
            value = self.field(args[0], "hero" if name == "HeroOf" else "duplicate")
            return bool(value) if name == "IsDuplicating" else value
        if name == "HeroIconString": return f"ICON<{args[0]}>"
        if name == "StringReplace": return args[0].replace(args[1], args[2])
        if name == "InputBindingString":
            return self.bindings.get((self.event_player, args[0]), f"{self.event_player}:{args[0]}")
        return super().call(name, args)

    def assign(self, target, value):
        if target.endswith(".TeksMenuIsi"):
            self.body_writes.append((self.event_player, value))
        nested = re.fullmatch(r"Global\.(PemainAktif|PemainPembersihan)\.(\w+)", target)
        if nested:
            self.players[self.globals[nested[1]]][nested[2]] = value
        else:
            super().assign(target, value)

    def execute(self, actions):
        actions = re.sub(r'(?m)^\s*"(?:\\.|[^"\\])*"\s*$', "", actions)
        # Preserve semicolons inside strings when walking actual actions.
        masked = validator.mask_strings(actions)
        ends = [match.start() for match in re.finditer(";", masked)]
        start, active, frames = 0, True, []
        for end in ends:
            statement, start = actions[start:end].strip(), end + 1
            if not statement: continue
            if statement.startswith("If("):
                branch = active and bool(self.evaluate(statement[3:-1]))
                frames.append([active, branch])
                active = branch
            elif statement.startswith("Else If("):
                parent, taken = frames[-1]
                active = parent and not taken and bool(self.evaluate(statement[8:-1]))
                frames[-1][1] = taken or active
            elif statement == "Else":
                parent, taken = frames[-1]
                active = parent and not taken
                frames[-1][1] = True
            elif statement == "End":
                active = frames.pop()[0]
            elif active:
                if statement == "Abort": return
                if statement.startswith("Abort If("):
                    if self.evaluate(statement[9:-1]): return
                    continue
                assignment = re.fullmatch(r"((?:Event Player|Global)\..+?)\s+(%?=)\s+(.+)", statement, re.S)
                if assignment:
                    value = self.evaluate(assignment[3])
                    if assignment[2] == "%=": value = self.evaluate(assignment[1]) % value
                    self.assign(assignment[1], value)
                    continue
                call = next(validator.iter_calls(statement + ";", statement.split("(", 1)[0]))
                name, args = statement.split("(", 1)[0], call.args
                if name == "Set Player Variable":
                    self.players[self.evaluate(args[0])][args[1]] = self.evaluate(args[2])
                elif name == "Create HUD Text":
                    super().execute(statement + ";")
                    self.hud_args[self.last_text] = args
                elif name == "Call Subroutine":
                    if args[0] in ("TransisiWarnaMenu", "SegarkanTargetKamera", "SegarkanTargetBalasDendam"):
                        continue  # Native color and target scanning have their own tests.
                    rule = validator.rule_by_subroutine(self.rules, args[0])
                    self.execute(validator.rule_block(rule, "actions"))
                else:
                    super().execute(statement + ";")
        if frames:
            raise AssertionError("unbalanced menu branches")

    def refresh(self, owner):
        self.event_player = owner
        self.globals["PemainAktif"] = owner
        self.execute(validator.rule_block(self.rule("91u"), "actions"))
        if self.conditions("91t", owner):
            self.run("91t", owner)

    def text(self, owner, argument=3):
        self.event_player = owner
        return self.evaluate(self.hud_args[self.players[owner]["HudMenu"]][argument])


class PersistentMenuCacheTests(unittest.TestCase):
    def models(self):
        for path, _, _ in SOURCES:
            yield path.name, PersistentMenuEvaluator(path.read_text(encoding="utf-8"))

    def test_twelve_independent_menus_reuse_handles_on_all_pages_and_idle_ticks(self):
        for source, model in self.models():
            with self.subTest(source=source):
                owners = [f"player{index}" for index in range(12)]
                for owner in owners:
                    model.add(owner)
                    model.run("91", owner)
                handles = {p: model.players[p]["HudMenu"] for p in owners}
                for page in range(-1, 14):
                    for owner in owners:
                        player = model.players[owner]
                        player["HalamanMenu"] = page
                        model.refresh(owner)
                        self.assertEqual(player["HudMenu"], handles[owner])
                        self.assertTrue(model.text(owner))
                written = len(model.body_writes)
                for _ in range(25):
                    for owner in owners:
                        model.refresh(owner)
                self.assertEqual(len(model.body_writes), written)
                self.assertEqual(len(model.created_huds), 12)
                self.assertEqual(model.destroyed_huds, [])
                self.assertEqual(model.globals["HudMenuPemain"], [handles[p] for p in owners])

    def test_navigation_and_ten_genre_jumps_update_only_the_acting_player(self):
        for source, model in self.models():
            with self.subTest(source=source):
                alice = model.add("alice", HalamanMenu=2)
                model.add("bob", HalamanMenu=2)
                for owner in ("alice", "bob"): model.run("91", owner)
                original_bob = dict(model.players["bob"])
                alice["PerintahMenu"] = 3
                model.run("06", "alice")
                self.assertIn("DaftarGenre-1", model.text("alice"))
                alice["PerintahMenu"] = 5
                model.run("08", "alice")
                self.assertIn("DaftarGenre-11", model.text("alice"))
                self.assertEqual(model.players["bob"], original_bob)
                self.assertEqual(len(model.created_huds), 2)
                self.assertEqual(model.destroyed_huds, [])

    def test_camera_cache_tracks_selected_hero_echo_and_same_length_target_changes(self):
        for source, model in self.models():
            with self.subTest(source=source):
                viewer = model.add("viewer", HalamanMenu=1, KursorKamera=2,
                                   DaftarTargetKamera=["alice"])
                alice = model.add("alice", hero="Ana")
                model.add("bob", hero="Mercy")
                model.run("91", "viewer")
                self.assertIn("ICON<Ana>", model.text("viewer"))
                for hero in ("D.Va", "Echo"):
                    alice["hero"] = hero
                    model.refresh("viewer")
                    self.assertIn(f"ICON<{hero}>", model.text("viewer"))
                alice["duplicate"] = "Reinhardt"
                model.refresh("viewer")
                self.assertIn("ICON<Reinhardt>", model.text("viewer"))
                alice["duplicate"] = None
                model.refresh("viewer")
                self.assertIn("ICON<Echo>", model.text("viewer"))
                viewer["DaftarTargetKamera"] = ["bob"]
                model.refresh("viewer")
                self.assertIn("bob", model.text("viewer"))
                self.assertNotIn("alice", model.text("viewer"))
                self.assertEqual(len(model.created_huds), 1)

    def test_vote_counts_identity_replacement_and_revenge_debt_invalidate(self):
        for source, model in self.models():
            with self.subTest(source=source):
                viewer = model.add("viewer", HalamanMenu=11, KursorPilihan=1)
                alice = model.add("alice", JumlahPilihan=1)
                model.add("bob", JumlahPilihan=3)
                model.run("91", "viewer")
                alice["JumlahPilihan"] = 5
                model.refresh("viewer")
                self.assertIn("alice - 5 VOTES", model.text("viewer"))
                model.globals["PemainManusia"][1:] = ["bob", "alice"]
                model.refresh("viewer")
                self.assertIn("bob - 3 VOTES", model.text("viewer"))
                viewer.update(HalamanMenu=4, DaftarTargetBalasDendam=["alice"],
                              PembunuhBalasDendam=["alice"], JumlahBalasDendam=[1])
                model.refresh("viewer")
                old_text = model.text("viewer")
                viewer["JumlahBalasDendam"] = [7]
                model.refresh("viewer")
                self.assertNotEqual(model.text("viewer"), old_text)
                self.assertIn("7", model.text("viewer"))
                self.assertEqual(len(model.created_huds), 1)

    def test_camera_off_self_and_empty_lists_do_not_read_an_absent_target_hero(self):
        for path, _, _ in SOURCES:
            for cursor, targets in ((0, ["alice"]), (1, ["alice"]), (2, [])):
                with self.subTest(source=path.name, cursor=cursor, targets=targets):
                    model = PersistentMenuEvaluator(path.read_text(encoding="utf-8"))
                    model.add("viewer", HalamanMenu=1, KursorKamera=cursor,
                              DaftarTargetKamera=targets)
                    target = model.add("alice", hero="Ana")
                    if targets:
                        model.run("91", "viewer")
                    else:
                        # A stale cursor can reach the detector while another
                        # routine refreshes its list. The renderer's normal
                        # caller clamps it first; here only exercise its real
                        # snapshot assignment and the asynchronous detector.
                        model.event_player = "viewer"
                        snapshot = re.search(r"Event Player\.SalinanMenu = [^;]+;",
                                             validator.rule_block(model.rule("91c"), "actions"))
                        model.execute(snapshot[0])
                    before = len(model.body_writes)
                    target["hero"] = "Mercy"
                    model.refresh("viewer")
                    self.assertEqual(model.hero_queries, [])
                    self.assertEqual(len(model.body_writes), before)

    def test_language_changes_and_client_bindings_remain_live_without_cache_rebuild(self):
        for source, model in self.models():
            with self.subTest(source=source):
                player = model.add("viewer", HalamanMenu=3)
                model.run("91", "viewer")
                texts = []
                for language in range(3):
                    player["IndeksBahasa"] = language
                    model.refresh("viewer")
                    texts.append(model.text("viewer"))
                    self.assertNotRegex(model.text("viewer", 2), r"\[(?:PRIMARY|INTERACT|RELOAD)")
                self.assertEqual(len(set(texts)), 3)
                before = len(model.body_writes)
                first = model.text("viewer", 2)
                model.bindings[("viewer", "PrimaryFire")] = "CUSTOM LEFT BUTTON"
                second = model.text("viewer", 2)
                self.assertNotEqual(first, second)
                self.assertIn("CUSTOM LEFT BUTTON", second)
                self.assertEqual(len(model.body_writes), before)

    def test_close_reopen_and_missing_local_handle_clean_only_their_owner(self):
        for source, model in self.models():
            with self.subTest(source=source):
                alice = model.add("alice")
                bob = model.add("bob")
                for owner in ("alice", "bob"): model.run("91", owner)
                first, other = alice["HudMenu"], bob["HudMenu"]
                alice["HudMenu"] = None
                model.run("91", "alice")
                replacement = alice["HudMenu"]
                self.assertEqual(model.destroyed_huds, [first])
                self.assertNotEqual(replacement, first)
                model.run("90", "alice")
                self.assertEqual(model.destroyed_huds, [first, replacement])
                self.assertEqual(model.globals["HudMenuPemain"], [0, other])
                for field in ("TeksMenuIsi", "PetunjukMenu", "WarnaPetunjukMenu"):
                    self.assertIsNone(alice[field])
                self.assertEqual(alice["SalinanMenu"], [])
                self.assertFalse(alice["MenuPerluDigambar"])
                model.refresh("alice")
                self.assertIsNone(alice["HudMenu"])
                alice["MenuTerbuka"] = True
                model.run("91", "alice")
                self.assertNotEqual(alice["HudMenu"], replacement)
                self.assertEqual(bob["HudMenu"], other)

    def test_inactive_players_and_travel_cannot_create_a_main_menu(self):
        for source, model in self.models():
            for changes in (dict(Manusia=False), dict(SiklusPemainAktif=True),
                            dict(MenuTerbuka=False), dict(TeleportasiJongkokAktif=True)):
                with self.subTest(source=source, changes=changes):
                    model.add("viewer", **changes)
                    model.run("91", "viewer")
                    self.assertEqual(model.created_huds, [])

    def test_all_hud_release_paths_clear_cache_including_roulette_and_departure(self):
        fields = ("TeksMenuIsi", "PetunjukMenu", "WarnaPetunjukMenu", "SalinanMenu", "MenuPerluDigambar")
        for source, model in self.models():
            for prefix, owner_ref in (("90", "Event Player"), ("89d", "Global.PemainAktif"),
                                      ("93c", "Global.PemainPembersihan"), ("94", "Event Player")):
                with self.subTest(source=source, rule=prefix):
                    owner = model.add("viewer", TeksMenuIsi="old", PetunjukMenu="old",
                                      WarnaPetunjukMenu="old", SalinanMenu=["old"], MenuPerluDigambar=True)
                    model.event_player = "viewer"
                    model.globals.update(PemainAktif="viewer", PemainPembersihan="viewer")
                    actions = validator.rule_block(model.rule(prefix), "actions")
                    marker = owner_ref + ".HudMenu = Null;"
                    start = actions.rfind(marker) if prefix == "90" else actions.index(marker)
                    tail = actions[start + len(marker):]
                    # Execute the actual five consecutive releases directly
                    # after the handle reset, independent of native effects.
                    releases = re.match(r"(?:\s*" + re.escape(owner_ref) +
                                        r"\.(?:" + "|".join(fields) + r") = [^;]+;){5}", tail)
                    self.assertIsNotNone(releases)
                    model.execute(releases[0])
                    self.assertEqual([owner[field] for field in fields], [None, None, None, [], False])


if __name__ == "__main__":
    unittest.main()
