"""Execute the real Super Punch runtime and death ledger with native query inputs.

The evaluator supplies melee animation, view-cone and world-LOS responses. It
does not certify native melee timing, geometry or ally kill credit in the client.
"""
import copy
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
        for name in ("SuperPunchPlayers", "SuperPunchTimes", "SuperPunchTarget"):
            initializer = re.search(rf"Global\.{name} = ([^;]+);", self.initializers)
            if initializer is None:
                raise AssertionError(f"missing Super Punch initializer: {name}")
            self.globals[name] = self.evaluate(initializer[1])
        self.attacker = None
        self.victim = None
        self.event_ability = "Melee"
        self.event_damage = 40
        self.probes = 0
        self.punch_calls = []
        self.kills = []
        self.ledger = next(rule for rule in self.rules
                           if "Event Player.RevengeKillers = Append To Array(" in rule.body)

    def add(self, identity, **changes):
        self.join(identity)
        defaults = dict(team=1, dummy=False, exists=True, spawned=True, alive=True,
                        IsHuman=True, IsAutomaticBot=False, PlayerCycleActive=False,
                        TeamChangeProcessed=False, MenuOpen=False,
                        CrouchTravelActive=False, MeleeConsumed=False,
                        CrouchTravelEnabled=False, LuckActive=False,
                        LuckPrivacyActive=False, buttons=set(),
                        UnkillableActive=False, UnkillableMode=0, statuses=set(), melee=False,
                        position=Vector(0, 0, 0), facing=Vector(0, 0, 1), wall=False,
                        RevengeDeathPending=False, RevengeKillers=[],
                        RevengeDebts=[], RevengeIndex=-1, hero="Ana")
        defaults.update(changes)
        self.players[identity].update(defaults)
        reset = re.search(r"Global\.SuperPunchTimes\[[^;]+\] = 0", self.classifier)
        self.execute_source(reset[0])
        return self.players[identity]

    def resolve(self, name):
        if name == "Attacker":
            return self.attacker
        if name == "Victim":
            return self.victim
        if name == "EventAbility":
            return self.event_ability
        if name == "EventDamage":
            return self.event_damage
        if name == "JunkerQueen":
            return "Junker Queen"
        if name in {"UnkillableActive", "UnkillableMode", "Unkillable", "PhasedOut",
                    "BarriersDoNotBlockLOS", "RevengeKillers",
                    "RevengeDebts", "RevengeIndex", "Add", "Subtract", "Melee",
                    "Crouch"}:
            return name
        return super().resolve(name)

    def call(self, name, args):
        if name == "Hero":
            return args[0]
        if name == "HeroOf":
            return self.players[args[0]]["hero"]
        if name == "Button":
            return args[0]
        if name == "IsButtonHeld":
            return args[1] in self.players[args[0]]["buttons"]
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
        self.globals["SuperPunchPlayers"].append(identity)
        self.globals["SuperPunchTimes"][int(self.players[identity]["HudSlot"])] = -1
        self.tick(identity, self.now)

    def tick(self, identity, now):
        self.now = now
        self.globals["ActivePlayer"] = identity
        scheduler = next(rule for rule in self.rules if rule.name.startswith("04g -"))
        call = next(call for call in validator.iter_calls(scheduler.body, "Call Subroutine")
                    if call.args == ("ProcessSuperPunch",))
        branches = validator.conditional_branches_containing(scheduler.body, call.start)
        if all(self.evaluate(branch.splitlines()[0].strip()[3:-2]) for branch in branches):
            self.punch_calls.append(identity)
            self.run("ProcessSuperPunch")

    def swing(self, identity, start=100):
        self.players[identity]["melee"] = True
        self.tick(identity, start)
        self.tick(identity, start + 0.1)
        self.tick(identity, start + 0.2)

    def native_hit(self, identity, victim, now=100, ability="Melee", damage=40):
        self.now = now
        self.event_player = identity
        self.victim = victim
        self.event_ability = ability
        self.event_damage = damage
        impact = next(rule for rule in self.rules if rule.name.startswith("89i1 -"))
        self.globals["IsReady"] = True
        conditions = validator.rule_block(impact, "conditions")
        if all(self.evaluate(token.strip()) for token in conditions.split(";") if token.strip()):
            self.execute_source(validator.rule_block(impact, "actions"))

    def enter_travel(self, identity, page):
        """Run real Crouch admission and state setup, projecting away HUD rendering."""
        self.event_player = identity
        actor = self.players[identity]
        actor.update(CrouchTravelEnabled=True, TravelCursor=page,
                     buttons={"Crouch"})
        entry = next(rule for rule in self.rules if rule.name.startswith("19 -"))
        conditions = validator.rule_block(entry, "conditions")
        if not all(self.evaluate(token.strip()) for token in conditions.split(";") if token.strip()):
            raise AssertionError("Crouch did not enter the real Travel rule")
        actions = validator.rule_block(entry, "actions")
        self.execute_atomic(actions.split("Disallow Button(", 1)[0])

    def travel_state(self, identity):
        actor = self.players[identity]
        return copy.deepcopy({field: value for field, value in actor.items()
                              if "Teleportasi" in field or field in {"buttons", "MenuOpen"}})

    def clear_registry(self, identity, routine):
        self.event_player = identity
        rule = validator.rule_by_subroutine(self.rules, routine)
        actions = validator.rule_block(rule, "actions")
        removal = next(token.strip() for token in actions.split(";")
                       if "Global.SuperPunchPlayers = Remove From Array(" in token)
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
                self.assertEqual(model.kills, [("target", "attacker", 100)])
                target["alive"] = True
                for tick in range(20):
                    model.tick("attacker", 101 + tick / 20)
                self.assertEqual(model.probes, 1)
                attacker["melee"] = False
                model.tick("attacker", 102)
                model.swing("attacker", 103)
                self.assertEqual(len(model.kills), 2)
                self.assertEqual(target["RevengeKillers"], ["attacker"])
                self.assertEqual(target["RevengeDebts"], [2])
                self.assertIsNone(model.globals["SuperPunchTarget"])

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
                        self.assertEqual(target["RevengeKillers"], ["attacker"])
                        self.assertEqual(target["RevengeDebts"], [1])

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
                    # No target keeps the swing eligible; protected contact consumes it.
                    self.assertEqual(model.probes, 1 if changes.get("statuses") else 3)
                    self.assertIsNone(model.globals["SuperPunchTarget"])

    def test_unkillable_status_or_active_mode_blocks_both_teams(self):
        for path, _, _ in SOURCES:
            for team in (1, 2):
                for protection in ({"statuses": {"Unkillable"}},
                                   {"UnkillableActive": True, "UnkillableMode": 1},
                                   {"UnkillableActive": True, "UnkillableMode": 2}):
                    with self.subTest(source=path.name, team=team, protection=protection):
                        model = SuperPunchEvaluator(path.read_text(encoding="utf-8"))
                        model.add("attacker")
                        model.add("target", team=team, position=Vector(0, 0, 1), **protection)
                        model.enable("attacker")
                        model.swing("attacker")
                        self.assertEqual(model.kills, [])

    def test_input_consumption_quarantine_and_invalid_actor_cancel_the_in_progress_swing(self):
        blocked = ({"MeleeConsumed": True}, {"PlayerCycleActive": True},
                   {"TeamChangeProcessed": True}, {"alive": False},
                   {"spawned": False}, {"exists": False}, {"IsHuman": False},
                   {"IsAutomaticBot": True}, {"dummy": True})
        for path, _, _ in SOURCES:
            for changes in blocked:
                with self.subTest(source=path.name, actor=changes):
                    model = SuperPunchEvaluator(path.read_text(encoding="utf-8"))
                    actor = model.add("attacker")
                    target = model.add("target", position=Vector(0, 0, 5))
                    model.enable("attacker")
                    actor["melee"] = True
                    model.tick("attacker", 100)
                    actor.update(changes)
                    model.tick("attacker", 100.1)
                    self.assertEqual((model.probes, model.kills), (1, []))
                    # A scheduler-excluded bot cannot advance the pending swing.
                    if changes.keys() & {"dummy", "IsAutomaticBot"}:
                        continue
                    actor.update(MenuOpen=False, CrouchTravelActive=False,
                                 MeleeConsumed=False, PlayerCycleActive=False,
                                 TeamChangeProcessed=False, alive=True, spawned=True, exists=True,
                                 IsHuman=True, IsAutomaticBot=False, dummy=False)
                    model.tick("attacker", 101)
                    self.assertEqual((model.probes, model.kills), (1, []))
                    actor["melee"] = False
                    model.tick("attacker", 102)
                    target["position"] = Vector(0, 0, 1)
                    model.swing("attacker", 103)
                    self.assertEqual(len(model.kills), 1)

    def test_each_travel_page_allows_crouch_melee_without_changing_travel_or_revenge(self):
        for path, _, _ in SOURCES:
            for page in range(6):
                for native, team in ((False, 1), (False, 2), (True, 2)):
                    with self.subTest(source=path.name, page=page, native=native, team=team):
                        model = SuperPunchEvaluator(path.read_text(encoding="utf-8"))
                        attacker = model.add("attacker")
                        target = model.add("target", team=team, position=Vector(0, 0, 1))
                        model.enable("attacker")
                        model.enter_travel("attacker", page)
                        self.assertTrue(attacker["CrouchTravelActive"])
                        before = model.travel_state("attacker")
                        if native:
                            model.globals["ActivePlayer"] = "unrelated"
                            model.native_hit("attacker", "target")
                            self.assertEqual(model.globals["ActivePlayer"], "unrelated")
                        else:
                            attacker["melee"] = True
                            model.tick("attacker", 100)
                        self.assertEqual(model.kills, [("target", "attacker", 100)])
                        self.assertEqual(target["RevengeKillers"], ["attacker"])
                        self.assertEqual(target["RevengeDebts"], [1])
                        self.assertEqual(model.travel_state("attacker"), before)
                        # Scanner/native impact share one contact even while Crouch stays held.
                        target["alive"] = True
                        attacker["melee"] = True
                        model.tick("attacker", 100.01)
                        model.native_hit("attacker", "target", now=100.02)
                        self.assertEqual(len(model.kills), 1)
                        self.assertEqual(target["RevengeDebts"], [1])
                        self.assertEqual(model.travel_state("attacker"), before)

    def test_crouch_travel_melee_preserves_unkillable_and_consumes_protected_contact(self):
        protections = ({"statuses": {"Unkillable"}}, {"statuses": {"PhasedOut"}},
                       {"UnkillableActive": True, "UnkillableMode": 1},
                       {"UnkillableActive": True, "UnkillableMode": 2})
        for path, _, _ in SOURCES:
            for native, team in ((False, 1), (False, 2), (True, 2)):
                for protection in protections:
                    with self.subTest(source=path.name, native=native, team=team,
                                      protection=protection):
                        model = SuperPunchEvaluator(path.read_text(encoding="utf-8"))
                        attacker = model.add("attacker")
                        target = model.add("target", team=team, position=Vector(0, 0, 1),
                                           **protection)
                        model.enable("attacker")
                        model.enter_travel("attacker", 5)
                        before = model.travel_state("attacker")
                        if native:
                            model.native_hit("attacker", "target")
                        else:
                            attacker["melee"] = True
                            model.tick("attacker", 100)
                        self.assertEqual((model.kills, target["RevengeDebts"]), ([], []))
                        self.assertEqual(model.globals["SuperPunchTimes"][
                            int(attacker["HudSlot"])], -1)
                        target.update(UnkillableActive=False, UnkillableMode=0, statuses=set())
                        model.native_hit("attacker", "target", now=100.01)
                        self.assertEqual(model.kills, [])
                        self.assertEqual(model.travel_state("attacker"), before)

    def test_two_attackers_keep_independent_swing_latches(self):
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
                self.assertEqual(model.kills, [("first-target", "first", 100),
                                              ("second-target", "second", 100.1)])
                self.assertTrue(model.players["first-far"]["alive"])
                self.assertEqual(model.probes, 2)

    def test_short_native_swing_and_late_target_entry_do_not_miss_the_hit(self):
        for source, model in self.models():
            with self.subTest(source=source):
                attacker = model.add("attacker")
                target = model.add("target", position=Vector(0, 0, 5))
                model.enable("attacker")
                attacker["melee"] = True
                model.tick("attacker", 100)
                self.assertEqual(model.kills, [])
                target["position"] = Vector(0, 0, 1)
                model.tick("attacker", 100.05)
                self.assertEqual(model.kills, [("target", "attacker", 100.05)])
                attacker["melee"] = False
                model.tick("attacker", 100.1)
                self.assertEqual(target["RevengeDebts"], [1])

    def test_real_enemy_impact_works_outside_sampled_animation_and_without_scheduler_scratch(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.add("attacker", melee=False)
                target = model.add("target", team=2, position=Vector(0, 0, 5))
                model.enable("attacker")
                model.globals["ActivePlayer"] = "unrelated"
                model.native_hit("attacker", "target")
                self.assertEqual(model.kills, [("target", "attacker", 100)])
                self.assertEqual(target["RevengeDebts"], [1])
                self.assertEqual(model.probes, 0)
                self.assertEqual(model.globals["ActivePlayer"], "unrelated")

    def test_each_open_menu_keeps_the_first_scanned_hit_instant_and_credits_revenge(self):
        for path, _, _ in SOURCES:
            for page in range(-1, 16):
                with self.subTest(source=path.name, page=page):
                    model = SuperPunchEvaluator(path.read_text(encoding="utf-8"))
                    attacker = model.add("attacker", MenuOpen=True, MenuPage=page,
                                         hero="Junker Queen" if page == 15 else "Ana")
                    target = model.add("target", team=1 if page % 2 else 2,
                                       position=Vector(0, 0, 1))
                    model.enable("attacker")
                    attacker["melee"] = True
                    model.tick("attacker", 100)
                    self.assertEqual(model.kills, [("target", "attacker", 100)])
                    self.assertEqual(target["RevengeKillers"], ["attacker"])
                    self.assertEqual(target["RevengeDebts"], [1])
                    self.assertTrue(attacker["MenuOpen"])
                    self.assertEqual(attacker["MenuPage"], page)
                    target["alive"] = True
                    model.native_hit("attacker", "target", now=100.01)
                    self.assertEqual(len(model.kills), 1)
                    self.assertEqual(model.probes, 1)

    def test_each_open_menu_allows_native_melee_impact_without_scheduler_scratch(self):
        for path, _, _ in SOURCES:
            for page in range(-1, 16):
                with self.subTest(source=path.name, page=page):
                    model = SuperPunchEvaluator(path.read_text(encoding="utf-8"))
                    attacker = model.add("attacker", MenuOpen=True, MenuPage=page)
                    target = model.add("target", team=2, position=Vector(0, 0, 5))
                    model.enable("attacker")
                    model.globals["ActivePlayer"] = "unrelated"
                    model.native_hit("attacker", "target")
                    self.assertEqual(model.kills, [("target", "attacker", 100)])
                    self.assertEqual(target["RevengeDebts"], [1])
                    self.assertTrue(attacker["MenuOpen"])
                    self.assertEqual(model.probes, 0)
                    self.assertEqual(model.globals["ActivePlayer"], "unrelated")

    def test_open_menu_still_respects_protection_and_consumes_one_contact(self):
        protections = ({"statuses": {"Unkillable"}}, {"statuses": {"PhasedOut"}},
                       {"UnkillableActive": True, "UnkillableMode": 1},
                       {"UnkillableActive": True, "UnkillableMode": 2})
        for path, _, _ in SOURCES:
            for native in (False, True):
                for team in (1, 2):
                    for protection in protections:
                        with self.subTest(source=path.name, native=native, team=team,
                                          protection=protection):
                            model = SuperPunchEvaluator(path.read_text(encoding="utf-8"))
                            attacker = model.add("attacker", MenuOpen=True, MenuPage=15)
                            target = model.add("target", team=team, position=Vector(0, 0, 1),
                                               **protection)
                            model.enable("attacker")
                            if native:
                                model.native_hit("attacker", "target")
                            else:
                                attacker["melee"] = True
                                model.tick("attacker", 100)
                            self.assertEqual(model.kills, [])
                            self.assertEqual(target["RevengeDebts"], [])
                            self.assertEqual(model.globals["SuperPunchTimes"][
                                int(attacker["HudSlot"])], -1)
                            target.update(UnkillableActive=False, UnkillableMode=0, statuses=set())
                            model.native_hit("attacker", "target", now=100.01)
                            self.assertEqual(model.kills, [])

    def test_open_menu_hold_consumption_still_requires_a_new_melee_swing(self):
        for source, model in self.models():
            with self.subTest(source=source):
                attacker = model.add("attacker", MenuOpen=True, MenuPage=15)
                target = model.add("target", team=2, position=Vector(0, 0, 1))
                model.enable("attacker")
                # The existing 0.5 s menu toggle owns this latch until release.
                attacker.update(melee=True, MeleeConsumed=True)
                model.tick("attacker", 100)
                model.native_hit("attacker", "target", now=100.01)
                self.assertEqual((model.probes, model.kills), (0, []))
                attacker["MeleeConsumed"] = False
                model.tick("attacker", 100.1)
                model.native_hit("attacker", "target", now=100.11)
                self.assertEqual((model.probes, model.kills), (0, []))
                attacker["melee"] = False
                model.tick("attacker", 100.2)
                attacker["melee"] = True
                model.tick("attacker", 101)
                self.assertEqual(model.kills, [("target", "attacker", 101)])
                self.assertEqual(target["RevengeDebts"], [1])
                self.assertTrue(attacker["MenuOpen"])

    def test_native_impact_shares_consumption_and_ignores_non_melee_damage(self):
        for source, model in self.models():
            with self.subTest(source=source):
                attacker = model.add("attacker")
                ally = model.add("ally", position=Vector(0, 0, 1))
                enemy = model.add("enemy", team=2, position=Vector(0, 0, 5))
                model.enable("attacker")
                model.native_hit("attacker", "enemy", ability="PrimaryFire")
                model.native_hit("attacker", "enemy", damage=0)
                attacker["hero"] = "Junker Queen"
                model.native_hit("attacker", "enemy", ability="Melee")
                self.assertEqual(model.kills, [])
                # Queen uses the real swing scanner; bleed must not look like a new punch.
                model.swing("attacker")
                attacker["hero"] = "Ana"
                model.native_hit("attacker", "enemy", now=100.25)
                self.assertEqual(len(model.kills), 1)
                self.assertFalse(ally["alive"])
                self.assertTrue(enemy["alive"])

    def test_native_impact_obeys_off_state_lifecycle_input_latch_and_unkillable(self):
        blocked = ({"MeleeConsumed": True}, {"PlayerCycleActive": True},
                   {"TeamChangeProcessed": True}, {"alive": False}, {"IsHuman": False},
                   {"dummy": True}, {"IsAutomaticBot": True})
        for path, _, _ in SOURCES:
            for changes in blocked:
                with self.subTest(source=path.name, actor=changes):
                    model = SuperPunchEvaluator(path.read_text(encoding="utf-8"))
                    attacker = model.add("attacker")
                    model.add("target", team=2, position=Vector(0, 0, 5))
                    model.enable("attacker")
                    attacker.update(changes)
                    model.native_hit("attacker", "target")
                    self.assertEqual(model.kills, [])
            for protection in ({"statuses": {"Unkillable"}}, {"statuses": {"PhasedOut"}},
                               {"UnkillableActive": True, "UnkillableMode": 1},
                               {"UnkillableActive": True, "UnkillableMode": 2}, {}):
                with self.subTest(source=path.name, protection=protection):
                    model = SuperPunchEvaluator(path.read_text(encoding="utf-8"))
                    model.add("attacker")
                    model.add("target", team=2, position=Vector(0, 0, 5), **protection)
                    if protection:
                        model.enable("attacker")
                    model.native_hit("attacker", "target")
                    self.assertEqual(model.kills, [])

    def test_team_cleanup_and_leave_remove_preferences_without_slot_inheritance(self):
        for source, model in self.models():
            with self.subTest(source=source):
                for index in range(50):
                    identity = f"player-{index}"
                    actor = model.add(identity)
                    model.enable(identity)
                    actor["melee"] = True
                    model.tick(identity, 100 + index)
                    model.clear_registry(identity, "QuiescePlayer" if index % 2 else "CleanupPlayer")
                    self.assertNotIn(identity, model.globals["SuperPunchPlayers"])
                    model.remove(identity)
                    actor["exists"] = False
                replacement = model.add("replacement")
                self.assertNotIn("replacement", model.globals["SuperPunchPlayers"])
                self.assertEqual(model.globals["SuperPunchTimes"][int(replacement["HudSlot"])], 0)
                self.assertEqual(len(model.globals["SuperPunchTimes"]), 12)


if __name__ == "__main__":
    unittest.main()
