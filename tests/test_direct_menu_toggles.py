"""Run the source input latch, dispatcher and live HUD text for direct toggles.

Event transitions are simulated; native rendering and input timing need game QA.
"""
import re
import unittest

from tools import validate_workshop as validator
from tests.test_menu_load_regressions import MenuLoadEvaluator
from tests.test_roster_rejoin_regressions import SOURCES


PAGES = ((8, "TeleportasiJongkokDiaktifkan"),
         (9, "PrivasiInspeksiAktif"),
         (12, "IzinkanBotBuatanMengikuti"))


class DirectToggleEvaluator(MenuLoadEvaluator):
    BUTTONS = {value.replace(" ", ""): value for value in
               ("Crouch", "Interact", "Reload", "Primary Fire", "Secondary Fire",
                "Ability 1", "Ability 2", "Melee")}

    def __init__(self, source):
        super().__init__(source)
        self.previous_conditions = {}

    def add(self, name, **changes):
        state = super().add(name, **changes)
        defaults = dict(held=set(), MenuTerbuka=True, HalamanMenu=-1, KursorUtama=8,
                        PerintahMenu=0, InteraksiKameraDipakai=False,
                        KartuNasibAktif=False, TeleportasiJongkokAktif=False,
                        TeleportasiJongkokDiaktifkan=False, PrivasiInspeksiAktif=False,
                        IzinkanBotBuatanMengikuti=False, UrutanHUD=len(self.globals["PemainManusia"]) - 1,
                        team=1)
        for field, value in defaults.items():
            state[field] = changes.get(field, value)
        return state

    def resolve(self, name):
        if name in self.BUTTONS:
            return self.BUTTONS[name]
        return super().resolve(name)

    def call(self, name, args):
        if name == "IsButtonHeld":
            return args[1] in self.players[args[0]]["held"]
        if name == "TeamOf":
            return self.players[args[0]]["team"]
        if name == "OppositeTeamOf":
            return 3 - args[0]
        if name == "AllPlayers":
            return [identity for identity, state in self.players.items()
                    if args[0] == "AllTeams" or state["team"] == args[0]]
        return super().call(name, args)

    def execute(self, actions):
        # Extend the shared source evaluator with the dispatcher's Else If chain.
        actions = re.sub(r'(?m)^\s*"(?:\\.|[^"\\])*"\s*$', "", actions)
        frames, active = [], True
        for statement in actions.split(";"):
            statement = statement.strip()
            if not statement:
                continue
            if statement.startswith("If("):
                branch = active and bool(self.evaluate(statement[3:-1]))
                frames.append(dict(parent=active, taken=branch))
                active = branch
            elif statement.startswith("Else If("):
                frame = frames[-1]
                active = frame["parent"] and not frame["taken"] and bool(self.evaluate(statement[8:-1]))
                frame["taken"] |= active
            elif statement == "Else":
                frame = frames[-1]
                active = frame["parent"] and not frame["taken"]
                frame["taken"] = True
            elif statement == "End":
                active = frames.pop()["parent"]
            elif active:
                if statement == "Abort":
                    return
                if statement.startswith("Abort If("):
                    if self.evaluate(statement[len("Abort If("):-1]):
                        return
                else:
                    super().execute(statement + ";")
        if frames:
            raise AssertionError("unbalanced menu source")

    def tick(self, owner):
        for prefix in ("05d", "12d", "05c", "06", "10"):
            key = owner, prefix
            condition = self.conditions(prefix, owner)
            if condition and not self.previous_conditions.get(key, False):
                self.run(prefix, owner)
            self.previous_conditions[key] = condition

    def input(self, owner, button=None, ticks=1):
        self.players[owner]["held"] = {"Crouch"} | ({button} if button else set())
        for _ in range(ticks):
            self.tick(owner)


class DirectMenuToggleTests(unittest.TestCase):
    def models(self):
        for path, _, _ in SOURCES:
            yield path.name, DirectToggleEvaluator(path.read_text(encoding="utf-8"))

    def test_interact_changes_each_state_once_per_press_and_only_for_owner(self):
        for source, model in self.models():
            for page, field in PAGES:
                with self.subTest(source=source, page=page):
                    owner = f"owner-{page}"
                    state = model.add(owner, HalamanMenu=page, team=2)
                    other = model.add(f"other-{page}", HalamanMenu=page, team=2)
                    model.add(f"dummy-{page}", Manusia=False, dummy=True, team=1)
                    model.input(owner, "Interact", ticks=20)
                    self.assertTrue(state[field])
                    self.assertFalse(other[field])
                    self.assertEqual(model.created_huds, [])
                    model.input(owner, ticks=2)
                    model.input(owner, "Interact", ticks=20)
                    self.assertFalse(state[field])
                    self.assertFalse(other[field])
                    self.assertEqual(model.created_huds, [])

    def test_primary_and_secondary_do_not_change_direct_toggle_pages(self):
        for source, model in self.models():
            for page, field in PAGES:
                for enabled in (False, True):
                    with self.subTest(source=source, page=page, enabled=enabled):
                        owner = f"owner-{page}-{enabled}"
                        state = model.add(owner, HalamanMenu=page, **{field: enabled})
                        for button in ("Primary Fire", "Secondary Fire"):
                            model.input(owner, button, ticks=10)
                            self.assertEqual(state[field], enabled)
                            self.assertEqual(state["HalamanMenu"], page)
                            model.input(owner, ticks=2)
                        self.assertEqual(model.created_huds, [])

    def test_entering_function_screen_does_not_apply_toggle(self):
        for source, model in self.models():
            for page, field in PAGES:
                with self.subTest(source=source, page=page):
                    owner = f"owner-{page}"
                    state = model.add(owner, KursorUtama=page, team=2)
                    model.add(f"dummy-{page}", Manusia=False, dummy=True, team=1)
                    model.input(owner, "Interact", ticks=20)
                    self.assertEqual(state["HalamanMenu"], page)
                    self.assertFalse(state[field])
                    self.assertEqual(len([hud for hud in model.created_huds if hud[0] == owner]), 1)

    def test_existing_hud_shows_applied_state_in_three_languages_without_option_rows(self):
        for source, model in self.models():
            for page, field in PAGES:
                for language, words in enumerate((("ON", "OFF"), ("AKTIF", "MATI"), ("เปิด", "ปิด"))):
                    with self.subTest(source=source, page=page, language=language):
                        owner = f"owner-{page}-{language}"
                        state = model.add(owner, HalamanMenu=page, IndeksBahasa=language, team=2)
                        model.add(f"dummy-{page}-{language}", Manusia=False, dummy=True, team=1)
                        model.run("91p", owner)
                        handle = state["HudMenu"]
                        expression = model.hud_bodies[handle]
                        self.assertIn(words[1], model.evaluate(expression))
                        model.input(owner, "Interact", ticks=20)
                        rendered = model.evaluate(expression)
                        self.assertIn(words[0], rendered)
                        self.assertNotIn("/2", rendered)
                        self.assertNotIn("\n>", rendered)
                        self.assertEqual(state["HudMenu"], handle)
                        self.assertEqual(len([hud for hud in model.created_huds if hud[0] == owner]), 1)


if __name__ == "__main__":
    unittest.main()
