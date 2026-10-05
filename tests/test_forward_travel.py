"""Execute Forward's real scheduler, input latch and direct view-based movement.

Native geometry queries would report a blocking surface. Forward intentionally
ignores those queries; input timing and engine movement still require game QA.
"""
import re
import unittest

from tools import validate_workshop as validator
from tests.test_dummy_maintenance import DummyMaintenanceEvaluator
from tests.test_fly_motion import Vector
from tests.test_roster_rejoin_regressions import SOURCES


class ForwardTravelEvaluator(DummyMaintenanceEvaluator):
    BUTTONS = {value.replace(" ", ""): value for value in
               ("Crouch", "Interact", "Primary Fire", "Secondary Fire", "Melee")}
    DETACH_FIELDS = ("LampiranTeleportasiAktif", "TargetLampiranTeleportasi",
                     "PahlawanLampiranSendiri", "PahlawanLampiranTarget")

    def __init__(self, source):
        super().__init__(source)
        self.previous_conditions = {}
        self.actions = []
        self.geometry_queries = []
        self.forward_calls = []
        self.legacy_calls = []

    def add(self, identity, **changes):
        defaults = dict(position=Vector(0, 0, 0), facing=Vector(0, 0, 1),
                        eye_height=1.6, held={"Crouch"},
                        MenuTerbuka=False, KartuNasibAktif=False,
                        PrivasiNasibAktif=False, TeleportasiJongkokAktif=True,
                        TeleportasiJongkokDiaktifkan=True, KursorTeleportasi=5,
                        PerintahTeleportasi=0,
                        LampiranTeleportasiAktif=False, TargetLampiranTeleportasi=None,
                        PahlawanLampiranSendiri=None, PahlawanLampiranTarget=None,
                        PosisiTujuanTeleportasi=Vector(0, 0, 0), TeksTeleportasi=None,
                        TargetTeleportasiTeks=None, TeksDunia=None, TargetInspeksi=None,
                        InspeksiAktif=False, PelatNamaDinonaktifkan=False,
                        CalonTargetTeleportasi=None, HudMenu=None,
                        JenisTeleportasiTerkunci=-1, TargetTeleportasiTerkunci=None,
                        WaktuBunuhDiriBerikut=0, UrutanHUD=0)
        defaults.update(changes)
        return super().add(identity, **defaults)

    def resolve(self, name):
        if name in self.BUTTONS:
            return self.BUTTONS[name]
        if name == "Unkillable":
            return name
        if name in self.DETACH_FIELDS:
            return name
        return super().resolve(name)

    def call(self, name, args):
        if name == "Button":
            return args[0]
        if name == "IsButtonHeld":
            return args[1] in self.players[args[0]]["held"]
        if name == "PositionOf":
            return self.players[args[0]]["position"]
        if name == "FacingDirectionOf":
            return self.players[args[0]]["facing"]
        if name == "EyePosition":
            state = self.players[args[0]]
            return state["position"] + Vector(0, state["eye_height"], 0)
        if name == "Vector":
            return Vector(*args)
        if name in ("Min", "Max"):
            return (min if name == "Min" else max)(args)
        if name == "DistanceBetween":
            return (args[0] - args[1]).magnitude()
        if name in ("RayCastHitPosition", "NearestWalkablePosition"):
            self.geometry_queries.append((name, self.globals["PemainAktif"], tuple(args)))
            return args[0]  # A blocked ray cannot truncate the explicitly unrestricted movement.
        if name == "Teleport":
            owner, destination = args
            self.actions.append((name, owner, destination, self.now))
            self.players[owner]["position"] = destination
            return None
        if name == "DetachPlayers":
            self.actions.append((name, args[0], self.now))
            return None
        if name in ("AllowButton", "DisallowButton"):
            self.actions.append((name, *args))
            return None
        if name in ("ClearStatus", "SetDamageReceived"):
            self.actions.append((name, *args))
            return None
        if name == "Kill":
            self.actions.append((name, *args))
            self.players[args[0]]["alive"] = False
            return None
        return super().call(name, args)

    def execute_source(self, source):
        tokens = [token.strip() for token in validator.mask_strings(source).split(";") if token.strip()]
        frames, active, index = [], True, 0
        while index < len(tokens):
            token = tokens[index]
            if token.startswith("If("):
                condition = active and bool(self.evaluate(token[3:-1]))
                frames.append(dict(parent=active, taken=condition))
                active = condition
            elif token.startswith("Else If("):
                frame = frames[-1]
                active = frame["parent"] and not frame["taken"] and bool(self.evaluate(token[8:-1]))
                frame["taken"] |= active
            elif token == "Else":
                frame = frames[-1]
                active = frame["parent"] and not frame["taken"]
                frame["taken"] = True
            elif token == "End":
                active = frames.pop()["parent"]
            elif token.startswith("For Player Variable("):
                depth, stop = 1, index + 1
                while depth:
                    current = tokens[stop]
                    if current.startswith(("If(", "For Player Variable(")):
                        depth += 1
                    elif current == "End":
                        depth -= 1
                    if depth:
                        stop += 1
                if active:
                    call = next(validator.iter_calls(token, "For Player Variable"))
                    owner, field, start, end, step = call.args
                    for value in range(int(self.evaluate(start)), int(self.evaluate(end)), int(self.evaluate(step))):
                        self.players[self.evaluate(owner)][field] = value
                        self.execute_source(";".join(tokens[index + 1:stop]) + ";")
                index = stop
            elif active:
                if token == "Abort":
                    return
                if token.startswith("Abort If("):
                    if self.evaluate(token[9:-1]):
                        return
                elif token.startswith("Call Subroutine("):
                    name = token[len("Call Subroutine("):-1]
                    if name in ("GambarTeleportasi", "TransisiWarnaMenu", "SegarkanTargetTeleportasi"):
                        pass  # Rendering and target selection have separate regression tests.
                    elif name in ("TeleportasiKeRuangMuncul", "TeleportasiKeObjektif", "TeleportasiKeTarget"):
                        self.legacy_calls.append((name, self.event_player, self.now))
                    else:
                        self.run(name)
                elif token.startswith("Set Player Variable("):
                    args = next(validator.iter_calls(token, "Set Player Variable")).args
                    self.players[self.evaluate(args[0])][args[1].strip()] = self.evaluate(args[2])
                elif token.startswith(("Global.", "Event Player.")) and " = " in token:
                    target, value = token.rsplit(" = ", 1)
                    self.assign(target, self.evaluate(value))
                else:
                    self.evaluate(token)
            index += 1
        if frames:
            raise AssertionError("unbalanced Travel control flow")

    def rule(self, prefix):
        return next(rule for rule in self.rules if rule.name.startswith(prefix + " -"))

    def conditions(self, prefix, owner):
        self.event_player = owner
        return all(self.evaluate(token.strip()) for token in
                   validator.rule_block(self.rule(prefix), "conditions").split(";") if token.strip())

    def inputs(self, owner, now):
        self.now = now
        self.globals["PemainAktif"] = owner
        for prefix in ("19", "19b", "19a", "19c", "19e"):
            key = owner, prefix
            condition = self.conditions(prefix, owner)
            if condition and not self.previous_conditions.get(key, False):
                self.execute_source(validator.rule_block(self.rule(prefix), "actions"))
            self.previous_conditions[key] = condition

    def tick(self, owner, now):
        self.inputs(owner, now)
        self.globals["PemainAktif"] = owner
        scheduler = self.rule("04g")
        call = next(call for call in validator.iter_calls(scheduler.body, "Call Subroutine")
                    if call.args == ("ProsesTeleportasiMaju",))
        branches = validator.conditional_branches_containing(scheduler.body, call.start)
        if all(self.evaluate(branch.splitlines()[0].strip()[3:-2]) for branch in branches):
            self.forward_calls.append((owner, now))
            self.run("ProsesTeleportasiMaju")

    @property
    def teleports(self):
        return [action for action in self.actions if action[0] == "Teleport"]


class ForwardTravelTests(unittest.TestCase):
    def models(self):
        for path, _, _ in SOURCES:
            yield path.name, ForwardTravelEvaluator(path.read_text(encoding="utf-8"))

    def test_held_interact_repeats_three_metres_on_each_existing_scheduler_tick(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("owner", held={"Crouch", "Interact"})
                times = [100 + tick / 20 for tick in range(9)]
                for time in times:
                    model.tick("owner", time)
                self.assertEqual([action[3] for action in model.teleports], times)
                self.assertEqual(state["position"], Vector(0, 0, 27))
                self.assertEqual(state["PerintahTeleportasi"], 3)
                self.assertEqual(model.legacy_calls, [])

    def test_each_step_uses_the_current_full_view_direction_including_up_and_down(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("owner", held={"Crouch", "Interact"})
                for time, facing in ((100, Vector(1, 0, 0)), (100.21, Vector(0, 1, 0)),
                                     (100.42, Vector(0, -1, 0)), (100.63, Vector(0, 0, -1))):
                    state["facing"] = facing
                    previous = state["position"]
                    model.tick("owner", time)
                    self.assertAlmostEqual((state["position"] - previous - facing * 3).magnitude(), 0)
                self.assertEqual(len(model.teleports), 4)

    def test_release_stops_and_repress_resumes_on_next_tick_without_requiring_crouch_release(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("owner", held={"Crouch", "Interact"})
                model.tick("owner", 100)
                state["held"] = {"Crouch"}
                model.tick("owner", 100.05)
                self.assertEqual(state["PerintahTeleportasi"], 0)
                state["held"] = {"Crouch", "Interact"}
                model.tick("owner", 100.1)
                self.assertEqual(len(model.teleports), 2)
                state["held"] = {"Interact"}
                model.tick("owner", 100.5)
                self.assertEqual(len(model.teleports), 2)

    def test_full_step_ignores_obstacle_queries_and_nearest_walkable_projection(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("owner", held={"Crouch", "Interact"},
                                  PosisiTujuanTeleportasi=Vector(-100, -100, -100))
                model.tick("owner", 100)
                self.assertEqual(state["position"], Vector(0, 0, 3))
                self.assertEqual(model.geometry_queries, [])

    def test_forward_detaches_only_its_owner_and_clears_all_attachment_references_before_moving(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("owner", held={"Crouch", "Interact"}, LampiranTeleportasiAktif=True,
                                  TargetLampiranTeleportasi="other", PahlawanLampiranSendiri="Ana",
                                  PahlawanLampiranTarget="Ashe")
                other = model.add("other", LampiranTeleportasiAktif=True, TargetLampiranTeleportasi="third")
                model.tick("owner", 100)
                self.assertEqual([action[0] for action in model.actions], ["DetachPlayers", "Teleport"])
                self.assertFalse(state["LampiranTeleportasiAktif"])
                self.assertTrue(all(state[field] is None for field in model.DETACH_FIELDS[1:]))
                self.assertTrue(other["LampiranTeleportasiAktif"])
                self.assertEqual(other["TargetLampiranTeleportasi"], "third")

    def test_holding_advances_through_a_wall_or_ceiling_without_shortening_the_steps(self):
        for path, _, _ in SOURCES:
            for facing in (Vector(0, 0, 1), Vector(0, 1, 0)):
                with self.subTest(source=path.name, facing=facing):
                    model = ForwardTravelEvaluator(path.read_text(encoding="utf-8"))
                    state = model.add("owner", held={"Crouch", "Interact"}, facing=facing)
                    for tick in range(20):
                        model.tick("owner", 100 + tick / 20)
                    self.assertEqual(state["position"], facing * 60)
                    self.assertEqual(len(model.teleports), 20)
                    self.assertEqual(model.geometry_queries, [])

    def test_blocked_lifecycle_menu_or_input_never_queries_geometry_or_moves(self):
        blockers = ({"Manusia": False}, {"BotOtomatis": True}, {"dummy": True},
                    {"exists": False}, {"spawned": False}, {"alive": False},
                    {"SiklusPemainAktif": True}, {"PindahTimDiproses": True},
                    {"MenuTerbuka": True}, {"KartuNasibAktif": True},
                    {"PrivasiNasibAktif": True}, {"TeleportasiJongkokDiaktifkan": False},
                    {"TeleportasiJongkokAktif": False}, {"KursorTeleportasi": 4},
                    {"held": {"Crouch"}}, {"held": {"Interact"}})
        for path, _, _ in SOURCES:
            for changes in blockers:
                with self.subTest(source=path.name, changes=changes):
                    model = ForwardTravelEvaluator(path.read_text(encoding="utf-8"))
                    settings = dict(held={"Crouch", "Interact"}, PerintahTeleportasi=3)
                    settings.update(changes)
                    state = model.add("owner", **settings)
                    model.now = 100
                    model.globals["PemainAktif"] = "owner"
                    model.run("ProsesTeleportasiMaju")
                    self.assertEqual((model.teleports, model.geometry_queries), ([], []))
                    self.assertEqual(state["position"], Vector(0, 0, 0))

    def test_twelve_players_have_independent_inputs_and_destinations(self):
        for source, model in self.models():
            with self.subTest(source=source):
                for index in range(12):
                    model.add(str(index), held={"Crouch", "Interact"}, position=Vector(index * 10, 0, 0),
                              facing=Vector(1, 0, 0) if index % 2 else Vector(0, 0, 1))
                model.players["0"]["held"] = {"Crouch"}
                for time in (100, 100.05):
                    for index in range(12):
                        model.tick(str(index), time)
                self.assertEqual(len(model.teleports), 22)
                self.assertEqual(model.players["0"]["position"], Vector(0, 0, 0))
                for index in range(1, 12):
                    state = model.players[str(index)]
                    self.assertEqual(state["position"], Vector(index * 10, 0, 0) + state["facing"] * 6)

    def test_navigation_visits_six_pages_once_per_press_and_wraps_both_directions(self):
        for source, model in self.models():
            with self.subTest(source=source):
                state = model.add("owner", KursorTeleportasi=0)
                visited = []
                for _ in range(6):
                    state["held"] = {"Crouch", "Primary Fire"}
                    model.inputs("owner", model.now + 1)
                    visited.append(state["KursorTeleportasi"])
                    for _ in range(5):
                        model.inputs("owner", model.now + 0.05)
                    self.assertEqual(state["KursorTeleportasi"], visited[-1])
                    state["held"] = {"Crouch"}
                    model.inputs("owner", model.now + 0.05)
                self.assertEqual(visited, [1, 2, 3, 4, 5, 0])
                state["held"] = {"Crouch", "Secondary Fire"}
                model.inputs("owner", model.now + 1)
                self.assertEqual(state["KursorTeleportasi"], 5)

    def test_existing_spawn_objective_and_target_actions_still_fire_once_per_press(self):
        for path, _, _ in SOURCES:
            for page, routine in enumerate(("TeleportasiKeRuangMuncul", "TeleportasiKeObjektif", "TeleportasiKeTarget")):
                with self.subTest(source=path.name, page=page):
                    model = ForwardTravelEvaluator(path.read_text(encoding="utf-8"))
                    state = model.add("owner", KursorTeleportasi=page, held={"Crouch", "Interact"})
                    for tick in range(20):
                        model.tick("owner", 100 + tick / 20)
                    self.assertEqual(model.legacy_calls, [(routine, "owner", 100)])
                    self.assertEqual(model.forward_calls, [])
                    self.assertEqual(model.geometry_queries, [])
                    state["held"] = {"Crouch"}
                    model.tick("owner", 101)
                    state["held"] = {"Crouch", "Interact"}
                    model.tick("owner", 101.05)
                    self.assertEqual(len(model.legacy_calls), 2)


if __name__ == "__main__":
    unittest.main()
