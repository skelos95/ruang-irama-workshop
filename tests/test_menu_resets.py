"""Execute page resets and input latches; native rendering/physics stay mocked."""
from copy import deepcopy
from pathlib import Path
import unittest

from tools import validate_workshop as validator
from tests.test_direct_menu_toggles import DirectToggleEvaluator
from tests.test_global_controller_execution import GeneratedControllerEvaluator
from tests.test_roster_rejoin_regressions import SOURCES


ROOT = Path(__file__).resolve().parents[1]
PAGES = (1, 2, 3, 5, 6, 7, 11, 13, 14)


class MenuResetEvaluator(DirectToggleEvaluator):
    """Run the actual Reset/Apply helpers, recording only native boundaries."""

    def __init__(self, text):
        super().__init__(text)
        self.source = text
        self.globals.update(NameColors=[f"color-{i}" for i in range(40)],
                            VoteLeader=None, VoteRecountNeeded=False,
                            PlayerHudSlots=[], UnkillableIconIds=[0] * 12)
        self.native_calls = []
        self.messages = []

    def add(self, name, **changes):
        defaults = dict(DisplayName=name, ColorCursor=9, ColorIndex=9, NameColor="color-9",
                        CameraCursor=2, CameraMode=2, CameraTarget="target", CameraTargets=[],
                        GenreIndex=50, GenreCursor=50, CustomSoundtrack=None,
                        UnkillableCursor=2, UnkillableMode=2, UnkillableActive=True,
                        UnkillableIcon=900 + len(self.players), VoiceCursor=4, VoiceIndex=4,
                        IconCursor=10, IconIndex=10, VotedPlayer="target", VoteCursor=4,
                        GhostModeActive=True, FlyModeActive=True, GhostFlyCursor=1,
                        GhostFlyPhysicsApplied=True, MovementSpeed=200, MovementGravity=70,
                        MultijumpEnabled=True, MultijumpLevel=10, MultijumpCursor=10,
                        MultijumpConsumed=False, JumpWasGrounded=False, NextMultijumpTime=0,
                        LuckEffect=0, LuckEffectEndTime=0, max_health=250, grounded=True,
                        velocity=(0, 0, 0), native_camera=True, voice_modified=True,
                        player_collision=False, damage_received=0, knockback_received=0,
                        health=10, statuses={"Unkillable"}, MenuInputLocked=False,
                        TeamChangeProcessed=False, PlayerCycleActive=False)
        defaults.update(changes)
        state = super().add(name, **defaults)
        self.globals["PlayerHudSlots"].append(state["HudSlot"])
        self.globals["UnkillableIconIds"][state["HudSlot"]] = state["UnkillableIcon"]
        return state

    def resolve(self, name):
        if name in ("Jump", "Unkillable"):
            return name
        return super().resolve(name)

    def call(self, name, args):
        if name == "MaxHealth":
            return self.players[args[0]]["max_health"]
        if name == "IsOnGround":
            return self.players[args[0]]["grounded"]
        if name == "VelocityOf":
            return self.players[args[0]]["velocity"]
        if name == "MagnitudeOf":
            return sum(component ** 2 for component in args[0]) ** 0.5
        return super().call(name, args)

    def native_boundary(self, name, expressions):
        boundary = {
            "Small Message", "Stop Camera", "Stop Modifying Hero Voice Lines", "Clear Status",
            "Set Damage Received", "Set Knockback Received", "Enable Movement Collision With Players",
            "Set Player Health", "Destroy Icon", "Enable Movement Collision With Environment",
            "Stop Transforming Throttle", "Set Move Speed", "Set Gravity", "Allow Button", "Disallow Button",
        }
        if name in boundary:
            args = [self.evaluate(arg) for arg in expressions]
            self.native_calls.append((name, tuple(args)))
            if name == "Destroy Icon":
                return True
            owner = self.players[args[0]]
            if name == "Small Message": self.messages.append((args[0], args[1]))
            elif name == "Stop Camera": owner["native_camera"] = False
            elif name == "Stop Modifying Hero Voice Lines": owner["voice_modified"] = False
            elif name == "Clear Status": owner["statuses"].discard(args[1])
            elif name == "Enable Movement Collision With Players": owner["player_collision"] = True
            elif name == "Enable Movement Collision With Environment": owner["environment_collision"] = True
            elif name == "Set Damage Received": owner["damage_received"] = args[1]
            elif name == "Set Knockback Received": owner["knockback_received"] = args[1]
            elif name == "Set Player Health": owner["health"] = args[1]
            elif name == "Set Move Speed": owner["move_speed"] = args[1]
            elif name == "Set Gravity": owner["gravity"] = args[1]
            return True
        return False

    def tick(self, owner):
        for prefix in ("05d", "12d", "05c", "05e", "05f", "06", "10"):
            key = owner, prefix
            condition = self.conditions(prefix, owner)
            if condition and not self.previous_conditions.get(key, False):
                self.run(prefix, owner)
            self.previous_conditions[key] = condition


class MenuResetTests(unittest.TestCase):
    def models(self):
        for path, _, _ in SOURCES:
            yield path.name, MenuResetEvaluator(path.read_text(encoding="utf-8"))

    def assert_default(self, page, state, model):
        if page == 1:
            self.assertEqual((state["ColorCursor"], state["ColorIndex"], state["NameColor"]), (0, 0, "color-0"))
        elif page == 2:
            self.assertEqual((state["CameraCursor"], state["CameraMode"], state["CameraTarget"]), (0, 0, None))
            self.assertFalse(state["native_camera"])
        elif page == 3:
            self.assertEqual((state["GenreCursor"], state["GenreIndex"]), (0, -1))
        elif page == 5:
            self.assertEqual((state["UnkillableCursor"], state["UnkillableMode"], state["UnkillableActive"]), (0, 0, False))
            self.assertNotIn("Unkillable", state["statuses"])
            self.assertEqual((state["damage_received"], state["knockback_received"]), (100, 100))
            self.assertTrue(state["player_collision"])
            self.assertEqual(state["health"], 250)
            self.assertIsNone(state["UnkillableIcon"])
            self.assertEqual(model.globals["UnkillableIconIds"][state["HudSlot"]], 0)
        elif page == 6:
            self.assertEqual((state["VoiceCursor"], state["VoiceIndex"]), (0, 0))
            self.assertFalse(state["voice_modified"])
        elif page == 7:
            self.assertEqual((state["IconCursor"], state["IconIndex"]), (0, 0))
        elif page == 11:
            self.assertEqual((state["VoteCursor"], state["VotedPlayer"]), (0, None))
            self.assertTrue(model.globals["VoteRecountNeeded"])
        elif page == 13:
            self.assertFalse(state["GhostModeActive"] or state["FlyModeActive"])
            self.assertEqual(state["GhostFlyCursor"], 0)
            self.assertTrue(state["GhostFlyPhysicsApplied"])
            self.assertTrue(state["environment_collision"])
            self.assertEqual((state["move_speed"], state["gravity"]), (200, 70))
        elif page == 14:
            self.assertEqual((state["MultijumpCursor"], state["MultijumpLevel"], state["MultijumpEnabled"]), (0, 1, False))
            self.assertFalse(state["MultijumpConsumed"])
            self.assertTrue(state["JumpWasGrounded"])
            self.assertAlmostEqual(state["NextMultijumpTime"], model.now + 0.3)

    def test_each_page_resets_from_main_preview_and_submenu_without_rebuilding_hud(self):
        for source, model in self.models():
            for page in PAGES:
                for submenu in (False, True):
                    with self.subTest(source=source, page=page, submenu=submenu):
                        model = MenuResetEvaluator(model.source)
                        owner = f"owner-{page}-{submenu}"
                        state = model.add(owner, MainMenuCursor=page, MenuPage=page if submenu else -1)
                        other = model.add(f"other-{page}-{submenu}")
                        before = deepcopy(other)
                        model.input(owner, "Ultimate", ticks=20)
                        self.assert_default(page, state, model)
                        self.assertEqual(other, before)
                        self.assertEqual((state["MenuPage"], state["MainMenuCursor"]), (page if submenu else -1, page))
                        self.assertEqual(model.created_huds, [])
                        self.assertEqual(model.messages[-1], (owner, "Page reset to defaults."))

    def test_held_reset_consumes_one_command_and_release_repress_arms_it_again(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("owner", MainMenuCursor=3)
                model.input("owner", "Ultimate", ticks=20)
                self.assertEqual((state["MenuCommand"], state["GenreIndex"]), (8, -1))
                state["GenreIndex"] = 42
                model.input("owner", "Ultimate", ticks=20)
                self.assertEqual(state["GenreIndex"], 42)
                self.assertEqual(len(model.messages), 1)
                model.input("owner", ticks=2)
                self.assertEqual(state["MenuCommand"], 0)
                model.input("owner", "Ultimate", ticks=20)
                self.assertEqual(state["GenreIndex"], -1)
                self.assertEqual(len(model.messages), 2)

    def test_closed_dead_no_crouch_and_luck_states_do_not_reset(self):
        cases = ({"MenuOpen": False}, {"alive": False}, {"LuckActive": True})
        for source, model in self.models():
            for index, changes in enumerate(cases):
                with self.subTest(source=source, changes=changes):
                    owner = f"blocked-{index}"
                    state = model.add(owner, MainMenuCursor=3, **changes)
                    model.input(owner, "Ultimate", ticks=3)
                    self.assertEqual(state["GenreIndex"], 50)
                    self.assertEqual(state["MenuCommand"], 0)
            state = model.add("no-crouch", MainMenuCursor=3, held={"Ultimate"})
            for _ in range(3): model.tick("no-crouch")
            self.assertEqual(state["GenreIndex"], 50)
            self.assertEqual(state["MenuCommand"], 0)
            self.assertEqual(model.messages, [])

    def test_releasing_and_repressing_crouch_cannot_repeat_a_held_reset(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("owner", MainMenuCursor=3)
                model.input("owner", "Ultimate", ticks=20)
                self.assertEqual(len(model.messages), 1)
                mark = len(model.native_calls)
                state["held"] = {"Ultimate"}
                for _ in range(3): model.tick("owner")
                self.assertEqual(state["MenuCommand"], 8)
                self.assertNotIn(("Allow Button", ("owner", "Ultimate")), model.native_calls[mark:])
                model.input("owner", "Ultimate", ticks=20)
                self.assertEqual(len(model.messages), 1)
                model.input("owner", ticks=3)
                self.assertEqual(state["MenuCommand"], 0)
                model.input("owner", "Ultimate", ticks=20)
                self.assertEqual(len(model.messages), 2)

    def test_unsupported_actions_toggles_and_locked_soundtrack_are_unchanged(self):
        for source, model in self.models():
            for page in (0, 4, 8, 9, 10, 12, 15):
                with self.subTest(source=source, page=page):
                    owner = f"unsupported-{page}"
                    state = model.add(owner, MainMenuCursor=page, CrouchTravelEnabled=True,
                                      InspectionPrivacyActive=True, AllowDummyBotFollow=True)
                    before = deepcopy(state)
                    model.input(owner, "Ultimate", ticks=20)
                    for key, value in before.items():
                        if key not in ("held", "MenuCommand", "MenuInputLocked"):
                            self.assertEqual(state[key], value, key)
                    self.assertEqual(model.messages, [])
            state = model.add("locked", MainMenuCursor=3, CustomSoundtrack="Draconian")
            model.input("locked", "Ultimate", ticks=20)
            self.assertEqual((state["GenreIndex"], state["GenreCursor"], state["CustomSoundtrack"]), (50, 50, "Draconian"))
            self.assertEqual(model.messages, [])

    def test_special_profile_restores_charcoal_and_poison_without_changing_soundtrack(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("special", DisplayName="งูแรร์", CustomSoundtrack="Draconian", MainMenuCursor=1)
                model.globals["VoteLeader"] = "special"
                model.input("special", "Ultimate")
                self.assertEqual((state["ColorCursor"], state["ColorIndex"], state["NameColor"]), (2, 2, "color-2"))
                self.assertEqual(model.globals["VoteLeaderColor"], "color-2")
                model.input("special", ticks=2)
                state["MainMenuCursor"] = 7
                model.input("special", "Ultimate")
                self.assertEqual((state["IconCursor"], state["IconIndex"]), (23, 23))
                self.assertEqual(state["CustomSoundtrack"], "Draconian")

    def test_closing_and_reopening_the_menu_preserves_a_held_reset_consumption(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("owner", MainMenuCursor=3)
                model.input("owner", "Ultimate", ticks=5)
                self.assertEqual(len(model.messages), 1)
                marker = len(model.native_calls)
                model.event_player = "owner"
                close = validator.rule_by_subroutine(model.rules, "CloseMenu")
                model.execute(validator.rule_block(close, "actions"))
                self.assertEqual(state["MenuCommand"], 8)
                self.assertFalse(state["MenuOpen"])
                self.assertNotIn(("Allow Button", ("owner", "Ultimate")), model.native_calls[marker:])
                state["MenuOpen"] = True
                model.input("owner", "Ultimate", ticks=20)
                self.assertEqual(len(model.messages), 1)
                model.input("owner", ticks=3)
                model.input("owner", "Ultimate", ticks=20)
                self.assertEqual(len(model.messages), 2)


class GeneratedResetInputTests(unittest.TestCase):
    def models(self):
        for path in ("workshop/ruang_irama.en-US.workshop", "tests/fixtures/global_runtime_reference.txt"):
            yield path, GeneratedControllerEvaluator((ROOT / path).read_text(encoding="utf-8"))

    def test_generated_press_hold_release_repress_dispatches_only_the_reset_owner(self):
        for path, model in self.models():
            with self.subTest(artifact=path):
                state = model.add_player("owner", MenuOpen=True, MainMenuCursor=3, held={"Crouch", "Ultimate"})
                other = model.add_player("other", MainMenuCursor=3)
                before = deepcopy(other)
                for _ in range(20): model.tick("owner", "05d", "05c", "10")
                calls = [call for call in model.native_calls if "CallSubroutine(ResetMenuPage)" in call[1]]
                self.assertEqual([call[0] for call in calls], ["owner"])
                self.assertEqual(state["MenuCommand"], 8)
                self.assertEqual(other, before)
                state["held"] = {"Crouch"}
                model.tick("owner", "05d", "05c", "10")
                self.assertEqual(state["MenuCommand"], 0)
                state["held"].add("Ultimate")
                model.tick("owner", "05d", "05c", "10")
                calls = [call for call in model.native_calls if "CallSubroutine(ResetMenuPage)" in call[1]]
                self.assertEqual([call[0] for call in calls], ["owner", "owner"])

    def test_generated_crouch_release_cannot_repeat_or_enable_a_held_reset(self):
        for path, model in self.models():
            with self.subTest(artifact=path):
                state = model.add_player("owner", MenuOpen=True, MainMenuCursor=3,
                                         MenuInputLocked=False, held={"Crouch", "Ultimate"})
                prefixes = ("05c", "05d", "05e", "05f", "10")
                for _ in range(4): model.tick("owner", *prefixes)
                marker = len(model.native_calls)
                state["held"] = {"Ultimate"}
                for _ in range(4): model.tick("owner", *prefixes)
                self.assertEqual(state["MenuCommand"], 8)
                self.assertFalse(any("AllowButton(Global.TriggerPlayer,Button(Ultimate))" in call[1]
                                     for call in model.native_calls[marker:]))
                state["held"].add("Crouch")
                for _ in range(4): model.tick("owner", *prefixes)
                calls = [call for call in model.native_calls if "CallSubroutine(ResetMenuPage)" in call[1]]
                self.assertEqual([call[0] for call in calls], ["owner"])

    def test_generated_reset_has_lower_priority_than_every_existing_command(self):
        for path, model in self.models():
            for button, expected in (("Interact", 1), ("Reload", 2), ("PrimaryFire", 3),
                                     ("SecondaryFire", 4), ("Ability1", 5), ("Ability2", 6)):
                with self.subTest(artifact=path, button=button):
                    owner = f"owner-{button}"
                    state = model.add_player(owner, MenuOpen=True, MenuPage=3,
                                             held={"Crouch", "Ultimate", button})
                    model.tick(owner, "05c")
                    self.assertEqual(state["MenuCommand"], expected)


if __name__ == "__main__":
    unittest.main()
