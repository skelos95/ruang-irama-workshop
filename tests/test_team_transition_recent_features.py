"""Execute team quarantine across recent icon and Punch state.

The detector and worker eligibility guards are executed from the real source.
Stable cleanup projects canonical icons, text handles, roster bookkeeping and
player reset assignments; unrelated native physics is outside this model. These
tests cannot reproduce or establish the absence of an Overwatch engine crash.
"""

import copy
import re
import unittest

from tools import validate_workshop as validator
from tests.test_audit_lifecycle import project
from tests.test_fly_motion import Vector
from tests.test_roster_rejoin_regressions import SOURCES
from tests.test_social_beacon import SocialBeaconEvaluator, beacon_statements


class TeamTransitionEvaluator(SocialBeaconEvaluator):
    def __init__(self, source):
        super().__init__(source)
        self.text_destroyed = []
        self.detector = next(rule for rule in self.rules if rule.name.startswith("01a -"))
        self.worker = next(rule for rule in self.rules if rule.name.startswith("01b -"))
        self.programs = {"BersihkanPemain": self.cleanup_program}
        # Project only irrelevant native effects away. Keep resource destruction,
        # source reset assignments, and the real cleanup call order.
        for routine in ("TenangkanPemain", "TutupMenu", "PulihkanNasibPemain",
                        "SiapkanPemain", "BersihkanTeksYatim"):
            actions = validator.rule_block(validator.rule_by_subroutine(self.rules, routine), "actions")
            self.programs[routine] = project(beacon_statements(actions), lambda token: bool(
                re.match(r"(?:Global\.|Event Player\.)[^=]+=(?!=)", token)
                or token.startswith(("Destroy ", "Call Subroutine("))))
        actions = validator.rule_block(validator.rule_by_subroutine(self.rules, "BersihkanIkonPilar"), "actions")
        self.programs["BersihkanIkonPilar"] = beacon_statements(actions)
        for name in ("PemilikTeksSementara", "HudEfekSementara",
                     "TeksTeleportasiSementara", "TeksVisiSementara"):
            expression = re.search(rf"Global\.{name} = ([^;]+);", self.initializers)[1]
            self.globals[name] = self.evaluate(expression)

    def keep_cleanup(self, token):
        return (super().keep_cleanup(token)
                or token.startswith(("Destroy HUD Text(", "Destroy In-World Text(",
                                     "Global.PemainPukulanSuper =", "Global.PemainTeksPembersihan ="))
                or token in ("Call Subroutine(BersihkanIkonPilar)", "Call Subroutine(BersihkanTeksYatim)")
                or bool(re.match(r"(?:Global\.PemainPembersihan|Event Player)\.(?:Hud\w+|Teks\w+) =", token)))

    def resolve(self, name):
        if name in ("White", "Melee"):
            return name
        return super().resolve(name)

    def call(self, name, args):
        if name == "RemoveFromArray":
            return [value for value in args[0] if value != args[1]]
        if name == "Color":
            return (255, 255, 255, 255)
        if name == "Button":
            return args[0]
        if name == "IsButtonHeld":
            return False
        return super().call(name, args)

    def add(self, identity, **changes):
        defaults = dict(IndeksIkon=0, TimTerakhir=1, TimSiklusTarget=1,
                        SudahSiap=True, SiklusPemainAktif=False,
                        WaktuSiklusTim=0, HudKiri=None, HudMenu=None,
                        HudEfekNasib=None, TeksVisiNasib=None, TeksTeleportasi=None,
                        IkonKebal=None, IkonKartuNasib=None, ModeKebal=0)
        defaults.update(changes)
        state = super().add(identity, **defaults)
        # Allocate the permanent roster HUD through its actual classifier writes;
        # the menu has never been opened in these regression scenarios.
        self.event_player = identity
        rendering = self.classifier[self.classifier.index("Create HUD Text("):]
        for token in rendering.split(";"):
            token = token.strip()
            if token.startswith("Create HUD Text("):
                self.created.append(10000 + len(self.created))
            elif re.match(r"Event Player\.Hud\w+ = Last Text ID$", token):
                self.execute_assignment(token)
            elif re.match(r"Global\.Hud\w+Pemain\[.*\] = Event Player\.Hud\w+$", token):
                self.execute_assignment(token)
        return state

    def apply_special_icon_default(self, identity):
        classifier = next(rule for rule in self.rules if "Append To Array(Global.PemainManusia, Event Player)" in rule.body)
        marker = classifier.body.index("Event Player.IndeksIkon = 23;")
        branch = min(validator.conditional_branches_containing(classifier.body, marker), key=len)
        if 'If(Event Player.NamaTampilan == Custom String("งูแรร์"))' not in branch:
            raise AssertionError("special icon must remain an admission default")
        self.event_player = identity
        for token in validator.mask_strings(branch).split(";"):
            token = token.strip()
            if re.match(r"Event Player\.(?:IndeksIkon|KursorIkon) =", token):
                self.execute_assignment(token)

    def execute(self, nodes):
        for node in nodes:
            token = node[0]
            if token.startswith(("Destroy HUD Text(", "Destroy In-World Text(")):
                handle = self.evaluate(token[token.index("(") + 1:-1])
                self.text_destroyed.append(handle)
                self.destroyed.append(handle)
            elif token.startswith("Destroy Icon("):
                handle = self.evaluate(token[len("Destroy Icon("):-1])
                self.destroyed.append(handle)
                self.icons.pop(handle, None)
            elif token.startswith("Call Subroutine(") and token[len("Call Subroutine("):-1] in self.programs:
                routine = token[len("Call Subroutine("):-1]
                self.calls.append((self.event_player, routine))
                if self.execute(self.programs[routine]):
                    return True
            elif super().execute([node]):
                return True
        return False

    def trigger(self, rule, identity, now):
        self.event_player, self.now = identity, now
        conditions = validator.mask_strings(validator.rule_block(rule, "conditions"))
        if not all(self.evaluate(token.strip()) for token in conditions.split(";") if token.strip()):
            return False
        self.execute(beacon_statements(validator.rule_block(rule, "actions")))
        return True

    def change_team(self, identity, team, now):
        self.players[identity]["team"] = team
        return self.trigger(self.detector, identity, now)

    def worker_tick(self, identity, now):
        # The central scheduler chooses the identity; the actual worker still
        # enforces its team, spawn, quarantine, and half-second deadline guards.
        self.globals["PemainSiklusGlobal"] = identity
        return self.trigger(self.worker, identity, now)


class TeamTransitionRecentFeaturesTests(unittest.TestCase):
    def models(self):
        for path, _, _ in SOURCES:
            yield path.name, TeamTransitionEvaluator(path.read_text(encoding="utf-8"))

    def test_no_menu_special_default_hides_and_stops_owned_chase_immediately(self):
        for source, model in self.models():
            with self.subTest(source=source):
                changing = model.add("งูแรร์")
                model.apply_special_icon_default("งูแรร์")
                observer = model.add("observer", IndeksIkon=1)
                model.globals["PemainPukulanSuper"] = ["งูแรร์", "observer"]
                model.run(now=100)
                visual = model.visual("งูแรร์")
                other_visual, other_chase = model.visual("observer"), model.chases["observer"]
                self.assertEqual(changing["IndeksIkon"], 23)
                self.assertEqual(visual[2], model.icon_choices[22])
                self.assertFalse(changing["MenuTerbuka"])
                model.now = 100.1
                frozen = model.call("PlayerVariable", ["งูแรร์", "PosisiIkonPilar"])
                roster = {name: copy.deepcopy(model.globals[name]) for name in model.ARRAYS}
                self.assertTrue(model.change_team("งูแรร์", 2, 100.1))
                self.assertEqual(model.evaluate(visual[0]), [])
                self.assertNotIn("งูแรร์", model.chases)
                self.assertEqual(model.globals["PemainPukulanSuper"], ["observer"])
                self.assertEqual(model.chases["observer"], other_chase)
                self.assertTrue(model.evaluate(other_visual[0]))
                self.assertTrue(observer["Manusia"])
                self.assertEqual(changing["PosisiIkonPilar"], frozen)
                model.now = 100.2
                self.assertEqual(model.call("PlayerVariable", ["งูแรร์", "PosisiIkonPilar"]), frozen)
                self.assertEqual(model.destroyed, [])
                self.assertEqual(model.text_destroyed, [])
                self.assertEqual(roster, {name: model.globals[name] for name in model.ARRAYS})
                self.assertEqual(model.calls, [])

    def test_no_menu_no_punch_special_join_quiesces_and_cleans_after_stable_team(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("งูแรร์")
                model.apply_special_icon_default("งูแรร์")
                self.assertEqual(state["IndeksIkon"], 23)
                self.assertFalse(state["MenuTerbuka"])
                self.assertEqual(model.globals["PemainPukulanSuper"], [])
                model.run(now=100)
                visual = model.visual("งูแรร์")
                beacon = model.globals["EntitasIkonPilar"][0]
                hud = model.globals["HudKiriPemain"][0]
                self.assertIn("งูแรร์", model.chases)
                self.assertTrue(model.change_team("งูแรร์", 2, 100.1))
                self.assertEqual(model.evaluate(visual[0]), [])
                self.assertNotIn("งูแรร์", model.chases)
                self.assertEqual(model.chase_stopped, ["งูแรร์"])
                self.assertEqual(model.destroyed, [])
                self.assertEqual(model.text_destroyed, [])
                self.assertEqual(model.globals["PemainPukulanSuper"], [])
                self.assertFalse(model.worker_tick("งูแรร์", 100.599))
                self.assertEqual(model.destroyed, [])
                self.assertTrue(model.worker_tick("งูแรร์", 100.6))
                self.assertCountEqual(model.destroyed, [beacon, hud])
                self.assertEqual(model.text_destroyed, [hud])
                self.assertFalse(model.worker_tick("งูแรร์", 100.7))
                model.run(now=101)
                self.assertEqual(model.destroyed.count(beacon), 1)
                self.assertEqual(model.destroyed.count(hud), 1)
                self.assertEqual(model.icons, {})
                self.assertEqual(model.chases, {})
                self.assertEqual(model.globals["PemainManusia"], [])
                self.assertEqual(model.globals["PemainPukulanSuper"], [])
                self.assertEqual(model.globals["SlotHUDTersedia"], list(range(12)))
                for name in model.ARRAY_NAMES + tuple(model.ICONS):
                    self.assertEqual(len(model.globals[name]), 12)

    def test_stable_worker_releases_exact_handles_after_half_second_and_recycles_slot(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.add("changing", IndeksIkon=23)
                model.add("observer", IndeksIkon=1)
                own_static = model.install_icons("changing", 51)
                other_static = model.install_icons("observer", 52)
                model.globals["PemainPukulanSuper"] = ["changing", "observer"]
                model.run(now=100)
                own_beacon = model.globals["EntitasIkonPilar"][0]
                other_beacon = model.globals["EntitasIkonPilar"][1]
                own_hud = model.globals["HudKiriPemain"][0]
                other_hud = model.globals["HudKiriPemain"][1]
                slot = model.players["changing"]["UrutanHUD"]
                model.change_team("changing", 2, 100.1)
                self.assertFalse(model.worker_tick("changing", 100.599))
                self.assertEqual(model.destroyed, [])
                self.assertTrue(model.worker_tick("changing", 100.6))
                self.assertCountEqual(model.destroyed, [own_beacon, own_hud] + own_static)
                self.assertEqual(len(model.destroyed), len(set(model.destroyed)))
                self.assertEqual(model.globals["PemainManusia"], ["observer"])
                self.assertIn(slot, model.globals["SlotHUDTersedia"])
                self.assertEqual(model.globals["EntitasIkonPilar"][0], 0)
                self.assertEqual(model.globals["EntitasIkonPilar"][1], other_beacon)
                self.assertEqual(model.globals["HudKiriPemain"], [other_hud])
                self.assertTrue(all(handle not in model.destroyed for handle in other_static + [other_beacon, other_hud]))
                self.assertEqual(model.globals["PemainPukulanSuper"], ["observer"])
                self.assertEqual([routine for _, routine in model.calls if routine in
                                  ("TenangkanPemain", "BersihkanPemain", "SiapkanPemain")],
                                 ["TenangkanPemain", "BersihkanPemain", "SiapkanPemain"])
                model.add("replacement", IndeksIkon=2)
                self.assertEqual(model.players["replacement"]["UrutanHUD"], slot)
                model.run(now=100.7)
                replacement = model.visual("replacement")
                replacement_handle = model.globals["EntitasIkonPilar"][0]
                destroyed = list(model.destroyed)
                model.event_player = "changing"
                model.execute(model.programs["BersihkanPemain"])
                self.assertEqual(model.destroyed, destroyed)
                self.assertEqual(model.globals["PemilikIkonPilar"][0], "replacement")
                self.assertEqual(model.globals["EntitasIkonPilar"][0], replacement_handle)
                self.assertTrue(model.evaluate(replacement[0]))
                self.assertNotIn("replacement", model.globals["PemainPukulanSuper"])

    def test_ordinary_no_functions_join_can_change_team_without_allocating_icons(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.add("ordinary")
                model.run(now=100)
                self.assertEqual(model.icons, {})
                self.assertEqual(model.chases, {})
                self.assertEqual(model.globals["PemainPukulanSuper"], [])
                own_hud = model.globals["HudKiriPemain"][0]
                self.assertTrue(model.change_team("ordinary", 2, 100.1))
                self.assertEqual(model.destroyed, [])
                self.assertFalse(model.worker_tick("ordinary", 100.599))
                self.assertTrue(model.worker_tick("ordinary", 100.6))
                self.assertEqual(model.destroyed, [own_hud])
                self.assertEqual(model.icons, {})
                self.assertEqual(model.chase_started, [])

    def test_rapid_changes_extend_quarantine_without_new_chases_or_duplicate_cleanup(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("changing", IndeksIkon=23)
                model.add("observer", IndeksIkon=1)
                model.globals["PemainPukulanSuper"] = ["changing", "observer"]
                model.run(now=100)
                started = list(model.chase_started)
                self.assertTrue(model.change_team("changing", 2, 100.1))
                self.assertTrue(model.change_team("changing", 1, 100.2))
                self.assertFalse(model.change_team("changing", 1, 100.3))
                self.assertAlmostEqual(state["WaktuSiklusTim"], 100.7)
                self.assertEqual(model.chase_started, started)
                self.assertEqual(model.globals["PemainPukulanSuper"], ["observer"])
                self.assertEqual(model.chase_stopped, ["changing", "changing"])
                self.assertEqual(model.destroyed, [])
                self.assertFalse(model.worker_tick("changing", 100.6))
                self.assertTrue(model.worker_tick("changing", 100.7))
                destroyed = list(model.destroyed)
                self.assertFalse(model.worker_tick("changing", 100.8))
                model.event_player = "changing"
                model.execute(model.programs["BersihkanPemain"])
                self.assertEqual(model.destroyed, destroyed)
                model.run(now=101)
                self.assertEqual(model.chase_started, started)
                self.assertEqual(model.globals["PemainManusia"], ["observer"])

    def test_worker_waits_for_matching_team_and_spawn_after_quarantine(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("changing", IndeksIkon=23)
                model.run(now=100)
                model.change_team("changing", 2, 100.1)
                state["spawned"] = False
                self.assertFalse(model.worker_tick("changing", 100.6))
                state.update(spawned=True, team=1)
                self.assertFalse(model.worker_tick("changing", 100.6))
                self.assertEqual(model.destroyed, [])
                self.assertTrue(model.change_team("changing", 1, 100.6))
                self.assertFalse(model.worker_tick("changing", 101.099))
                self.assertTrue(model.worker_tick("changing", 101.1))


if __name__ == "__main__":
    unittest.main()
