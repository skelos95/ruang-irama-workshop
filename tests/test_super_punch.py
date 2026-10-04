"""Execute the real Super Punch runtime and death ledger with native query inputs.

The evaluator supplies melee animation, view-cone and world-LOS responses. It
does not certify native melee timing, geometry or ally kill credit in the client.
"""
import math
import re
import unittest

from tools import validate_workshop as validator
from tests.test_dummy_maintenance import DummyMaintenanceEvaluator
from tests.test_fly_motion import Vector
from tests.test_roster_rejoin_regressions import SOURCES


class SuperPunchEvaluator(DummyMaintenanceEvaluator):
    def __init__(self, source):
        super().__init__(source)
        for name in ("PemainPukulanSuper", "WaktuPukulanSuper", "TargetPukulanSuper"):
            initializer = re.search(rf"Global\.{name} = ([^;]+);", self.initializers)
            if initializer is None:
                raise AssertionError(f"missing Super Punch initializer: {name}")
            self.globals[name] = self.evaluate(initializer[1])
        self.attacker = None
        self.probes = 0
        self.punch_calls = []
        self.kills = []
        self.ledger = next(rule for rule in self.rules
                           if "Event Player.PembunuhBalasDendam = Append To Array(" in rule.body)

    def add(self, identity, **changes):
        self.join(identity)
        defaults = dict(team=1, dummy=False, exists=True, spawned=True, alive=True,
                        Manusia=True, BotOtomatis=False, SiklusPemainAktif=False,
                        PindahTimDiproses=False, MenuTerbuka=False,
                        TeleportasiJongkokAktif=False, SeranganDekatDipakai=False,
                        KebalAktif=False, ModeKebal=0, statuses=set(), melee=False,
                        position=Vector(0, 0, 0), facing=Vector(0, 0, 1), wall=False,
                        KematianBalasDendam=False, PembunuhBalasDendam=[],
                        JumlahBalasDendam=[], IndeksBalasDendam=-1)
        defaults.update(changes)
        self.players[identity].update(defaults)
        reset = re.search(r"Global\.WaktuPukulanSuper\[[^;]+\] = 0", self.classifier)
        self.execute_source(reset[0])
        return self.players[identity]

    def resolve(self, name):
        if name == "Attacker":
            return self.attacker
        if name in {"KebalAktif", "ModeKebal", "Unkillable", "PhasedOut",
                    "BarriersDoNotBlockLOS", "PembunuhBalasDendam",
                    "JumlahBalasDendam", "IndeksBalasDendam", "Add", "Subtract"}:
            return name
        return super().resolve(name)

    def call(self, name, args):
        if name == "IsMeleeing":
            return self.players[args[0]]["melee"]
        if name == "HasStatus":
            return args[1] in self.players[args[0]]["statuses"]
        if name == "PositionOf":
            return self.players[args[0]]["position"]
        if name == "EyePosition":
            return self.players[args[0]]["position"] + Vector(0, 1.6, 0)
        if name == "DistanceBetween":
            return (args[0] - args[1]).magnitude()
        if name == "IsInViewAngle":
            facing = self.players[args[0]]["facing"]
            direction = args[1] - self.call("EyePosition", [args[0]])
            if direction.magnitude() == 0:
                return True
            dot = facing.x * direction.x + facing.y * direction.y + facing.z * direction.z
            angle = math.degrees(math.acos(max(-1, min(1, dot / facing.magnitude() / direction.magnitude()))))
            return angle <= args[2] / 2
        if name == "IsInLineOfSight":
            return not any(state["wall"] and self.call("EyePosition", [identity]) == args[1]
                           for identity, state in self.players.items())
        if name == "AllPlayers":
            self.probes += 1
        if name == "FirstOf":
            return args[0][0] if args[0] else None
        if name == "RemoveFromArray":
            return [value for value in args[0] if value != args[1]]
        if name == "ModifyPlayerVariableAtIndex":
            target, field, index, operation, delta = args
            values = self.players[target][field]
            values[int(index)] += delta if operation == "Add" else -delta
            return None
        if name == "Kill":
            target, attacker = args
            self.kills.append((target, attacker, self.now))
            self.players[target]["alive"] = False
            previous = self.attacker
            self.attacker = attacker
            self.globals["PunchVictim"] = target
            # Run the existing Player Died ledger with the credited native killer.
            def victim_context(text):
                return text.replace("Event Player.", "Global.PunchVictim.").replace(
                    "Event Player", "Global.PunchVictim")
            conditions = victim_context(validator.rule_block(self.ledger, "conditions"))
            if all(self.evaluate(token.strip()) for token in conditions.split(";") if token.strip()):
                self.execute_source(victim_context(validator.rule_block(self.ledger, "actions")))
            self.attacker = previous
            return None
        return super().call(name, args)

    def enable(self, identity):
        self.globals["PemainPukulanSuper"].append(identity)
        self.globals["WaktuPukulanSuper"][int(self.players[identity]["UrutanHUD"])] = -1
        self.tick(identity, self.now)

    def tick(self, identity, now):
        self.now = now
        self.globals["PemainAktif"] = identity
        scheduler = next(rule for rule in self.rules if rule.name.startswith("04g -"))
        call = next(call for call in validator.iter_calls(scheduler.body, "Call Subroutine")
                    if call.args == ("ProsesPukulanSuper",))
        branches = validator.conditional_branches_containing(scheduler.body, call.start)
        if all(self.evaluate(branch.splitlines()[0].strip()[3:-2]) for branch in branches):
            self.punch_calls.append(identity)
            self.run("ProsesPukulanSuper")

    def swing(self, identity, start=100):
        self.players[identity]["melee"] = True
        self.tick(identity, start)
        self.tick(identity, start + 0.1)
        self.tick(identity, start + 0.2)

    def clear_registry(self, identity, routine):
        self.event_player = identity
        rule = validator.rule_by_subroutine(self.rules, routine)
        actions = validator.rule_block(rule, "actions")
        removal = next(token.strip() for token in actions.split(";")
                       if "Global.PemainPukulanSuper = Remove From Array(" in token)
        self.execute_source(removal)


class SuperPunchTests(unittest.TestCase):
    def models(self):
        for path, _, _ in SOURCES:
            yield path.name, SuperPunchEvaluator(path.read_text(encoding="utf-8"))

    def test_off_skips_runtime_and_target_scans_even_during_native_melee(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.add("attacker", melee=True)
                model.add("target", position=Vector(0, 0, 1))
                for tick in range(200):
                    model.tick("attacker", tick / 20)
                self.assertEqual((model.punch_calls, model.probes, model.kills), ([], 0, []))

    def test_actual_swing_has_one_impact_and_requires_a_new_native_swing(self):
        for source, model in self.models():
            with self.subTest(source=source):
                attacker = model.add("attacker")
                target = model.add("target", position=Vector(0, 0, 1))
                model.enable("attacker")
                for tick in range(20):
                    model.tick("attacker", tick / 20)
                self.assertEqual(model.probes, 0)
                attacker["melee"] = True
                model.tick("attacker", 100)
                model.tick("attacker", 100.1)
                self.assertEqual(model.kills, [])
                model.tick("attacker", 100.2)
                self.assertEqual(model.kills, [("target", "attacker", 100.2)])
                target["alive"] = True
                for tick in range(20):
                    model.tick("attacker", 101 + tick / 20)
                self.assertEqual(model.probes, 1)
                attacker["melee"] = False
                model.tick("attacker", 102)
                model.swing("attacker", 103)
                self.assertEqual(len(model.kills), 2)
                self.assertEqual(target["PembunuhBalasDendam"], ["attacker"])
                self.assertEqual(target["JumlahBalasDendam"], [2])
                self.assertIsNone(model.globals["TargetPukulanSuper"])

    def test_allies_and_enemies_credit_the_attacker_and_create_one_revenge_debt(self):
        for path, _, _ in SOURCES:
            for team in (1, 2):
                for hero in ("Ana", "Junker Queen"):
                    with self.subTest(source=path.name, target_team=team, hero=hero):
                        model = SuperPunchEvaluator(path.read_text(encoding="utf-8"))
                        model.add("attacker", team=1, hero=hero)
                        target = model.add("target", team=team, position=Vector(1, 0, 1.5))
                        model.enable("attacker")
                        model.swing("attacker")
                        self.assertEqual(len(model.kills), 1)
                        self.assertEqual(model.kills[0][:2], ("target", "attacker"))
                        self.assertEqual(target["PembunuhBalasDendam"], ["attacker"])
                        self.assertEqual(target["JumlahBalasDendam"], [1])

    def test_range_forward_view_world_los_and_target_lifecycle_limit_the_hit(self):
        blocked = (
            {"position": Vector(0, 0, 2.51)}, {"position": Vector(0, 0, -1)},
            {"position": Vector(2, 0, 0.1)}, {"wall": True},
            {"alive": False}, {"spawned": False}, {"exists": False},
            {"statuses": {"PhasedOut"}},
        )
        for path, _, _ in SOURCES:
            for changes in blocked:
                with self.subTest(source=path.name, target=changes):
                    model = SuperPunchEvaluator(path.read_text(encoding="utf-8"))
                    model.add("attacker")
                    model.add("target", **({"position": Vector(0, 0, 1)} | changes))
                    model.enable("attacker")
                    model.swing("attacker")
                    self.assertEqual(model.kills, [])
                    self.assertEqual(model.probes, 1)
                    self.assertIsNone(model.globals["TargetPukulanSuper"])

    def test_unkillable_status_or_active_mode_blocks_both_teams(self):
        for path, _, _ in SOURCES:
            for team in (1, 2):
                for protection in ({"statuses": {"Unkillable"}},
                                   {"KebalAktif": True, "ModeKebal": 1},
                                   {"KebalAktif": True, "ModeKebal": 2}):
                    with self.subTest(source=path.name, team=team, protection=protection):
                        model = SuperPunchEvaluator(path.read_text(encoding="utf-8"))
                        model.add("attacker")
                        model.add("target", team=team, position=Vector(0, 0, 1), **protection)
                        model.enable("attacker")
                        model.swing("attacker")
                        self.assertEqual(model.kills, [])

    def test_menu_travel_quarantine_and_invalid_actor_cancel_the_in_progress_swing(self):
        blocked = ({"MenuTerbuka": True}, {"TeleportasiJongkokAktif": True},
                   {"SeranganDekatDipakai": True}, {"SiklusPemainAktif": True},
                   {"PindahTimDiproses": True}, {"alive": False},
                   {"spawned": False}, {"exists": False}, {"Manusia": False},
                   {"BotOtomatis": True}, {"dummy": True})
        for path, _, _ in SOURCES:
            for changes in blocked:
                with self.subTest(source=path.name, actor=changes):
                    model = SuperPunchEvaluator(path.read_text(encoding="utf-8"))
                    actor = model.add("attacker")
                    model.add("target", position=Vector(0, 0, 1))
                    model.enable("attacker")
                    actor["melee"] = True
                    model.tick("attacker", 100)
                    actor.update(changes)
                    model.tick("attacker", 100.1)
                    self.assertEqual((model.probes, model.kills), (0, []))
                    # A scheduler-excluded bot cannot advance the pending swing.
                    if changes.keys() & {"dummy", "BotOtomatis"}:
                        continue
                    actor.update(MenuTerbuka=False, TeleportasiJongkokAktif=False,
                                 SeranganDekatDipakai=False, SiklusPemainAktif=False,
                                 PindahTimDiproses=False, alive=True, spawned=True, exists=True,
                                 Manusia=True, BotOtomatis=False, dummy=False)
                    model.tick("attacker", 101)
                    self.assertEqual((model.probes, model.kills), (0, []))
                    actor["melee"] = False
                    model.tick("attacker", 102)
                    model.swing("attacker", 103)
                    self.assertEqual(len(model.kills), 1)

    def test_two_attackers_keep_independent_swing_deadlines(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.add("first")
                model.add("second", position=Vector(8, 0, 0))
                model.add("first-far", position=Vector(0, 0, 2))
                model.add("first-target", position=Vector(0, 0, 1))
                model.add("second-target", position=Vector(8, 0, 1))
                model.enable("first")
                model.enable("second")
                model.players["first"]["melee"] = True
                model.tick("first", 100)
                model.players["second"]["melee"] = True
                model.tick("second", 100.1)
                model.tick("first", 100.2)
                model.tick("second", 100.2)
                self.assertEqual(model.kills, [("first-target", "first", 100.2)])
                model.tick("second", 100.3)
                self.assertEqual(model.kills[-1], ("second-target", "second", 100.3))
                self.assertTrue(model.players["first-far"]["alive"])
                self.assertEqual(model.probes, 2)

    def test_team_cleanup_and_leave_remove_preferences_without_slot_inheritance(self):
        for source, model in self.models():
            with self.subTest(source=source):
                for index in range(50):
                    identity = f"player-{index}"
                    actor = model.add(identity)
                    model.enable(identity)
                    actor["melee"] = True
                    model.tick(identity, 100 + index)
                    model.clear_registry(identity, "TenangkanPemain" if index % 2 else "BersihkanPemain")
                    self.assertNotIn(identity, model.globals["PemainPukulanSuper"])
                    model.remove(identity)
                    actor["exists"] = False
                replacement = model.add("replacement")
                self.assertNotIn("replacement", model.globals["PemainPukulanSuper"])
                self.assertEqual(model.globals["WaktuPukulanSuper"][int(replacement["UrutanHUD"])], 0)
                self.assertEqual(len(model.globals["WaktuPukulanSuper"]), 12)


if __name__ == "__main__":
    unittest.main()
