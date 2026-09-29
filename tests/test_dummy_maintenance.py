"""Execute the actual dummy manager with controlled native entity operations.

The Workshop source supplies all slot, cooldown and lifecycle decisions. Native
creation success and entity disappearance are inputs; engine stability and
movement still require a lobby test.
"""

import unittest

from tools import validate_workshop as validator
from tests.test_audit_lifecycle import AuditLifecycleEvaluator
from tests.test_roster_rejoin_regressions import SOURCES


class DummyMaintenanceEvaluator(AuditLifecycleEvaluator):
    def __init__(self, source):
        super().__init__(source)
        self.globals.update(Siap=True, WaktuCobaBotBuatanTim1=0,
                            WaktuCobaBotBuatanTim2=0, TimBotBuatanAktif=1,
                            PemilikTeksSementara=[], TeksVisiSementara=[],
                            LangkahPenjadwal=0)
        self.in_progress = True
        self.mode = "Skirmish"
        self.slots = {1: 6, 2: 6}
        self.spawns = {1: [1], 2: [2]}
        self.failed_teams = set()
        self.attempts = []
        self.removals = []
        self.native_actions = []
        self.follow_filters = 0

    def add(self, identity, team=1, dummy=False, **changes):
        state = dict(team=team, dummy=dummy, exists=True, spawned=True,
                     alive=True, slot=sum(p["team"] == team and p["exists"]
                                          for p in self.players.values()),
                     Manusia=not dummy, BotOtomatis=False, TeksVisiNasib=None,
                     KunciBotAktif=True, PindahTimDiproses=False,
                     SiklusPemainAktif=False, SudahDiperiksa=True,
                     IzinkanBotBuatanMengikuti=False, TargetIkutiBotBuatan=None,
                     DaftarTargetInspeksi=[], position=0)
        state.update(changes)
        self.players[identity] = state
        if state["Manusia"]:
            self.globals["PemainManusia"].append(identity)
        return state

    def resolve(self, name):
        values = {"Team1": 1, "Team2": 2, "IsGameInProgress": self.in_progress,
                  "CurrentGameMode": self.mode, "Skirmish": "Skirmish",
                  "AllHeroes": "all-heroes"}
        if name in values:
            return values[name]
        if name in {"TeksVisiNasib", "DaftarTargetInspeksi", "Manusia",
                    "IzinkanBotBuatanMengikuti", "TargetIkutiBotBuatan"}:
            return name
        return super().resolve(name)

    def call(self, name, args):
        if name == "AllPlayers":
            return [identity for identity, state in self.players.items()
                    if state["exists"] and (args[0] == "all-teams" or state["team"] == args[0])]
        if name == "NumberOfPlayers":
            return len(self.call("AllPlayers", args))
        if name == "NumberOfSlots": return self.slots[args[0]]
        if name == "GameMode": return args[0]
        if name == "SpawnPoints": return self.spawns[args[0]]
        if name == "PositionOf": return args[0]
        if name == "Vector": return tuple(args)
        if name == "OppositeTeamOf": return 3 - args[0]
        if name == "DistanceBetween":
            return abs(self.players[args[0]]["position"] - self.players[args[1]]["position"])
        if name == "CreateDummyBot":
            team = args[1]
            deadline = self.globals[f"WaktuCobaBotBuatanTim{team}"]
            self.attempts.append((team, self.now, deadline))
            if team not in self.failed_teams:
                self.add(f"dummy-{team}-{len(self.attempts)}", team=team, dummy=True)
            return None
        if name == "DestroyDummyBot":
            target = next(identity for identity, state in self.players.items()
                          if state["exists"] and state["dummy"] and
                          (state["team"], state["slot"]) == tuple(args))
            self.native_actions.append((name, target))
            self.players[target]["exists"] = False
            self.removals.append(target)
            return None
        if name in {"StopFacing", "StopThrottleInDirection", "DestroyInWorldText"}:
            self.native_actions.append((name, args[0]))
            return None
        return super().call(name, args)

    def execute_source(self, source):
        # Unlike the projected churn interpreter this executes every manager
        # action, including Else If and Abort If, plus its two native helpers.
        frames = []
        active = True
        for token in validator.mask_strings(source).split(";"):
            token = token.strip()
            if not token: continue
            if token.startswith("If("):
                condition = active and bool(self.evaluate(token[3:-1]))
                frames.append({"parent": active, "taken": condition})
                active = condition
            elif token.startswith("Else If("):
                frame = frames[-1]
                active = frame["parent"] and not frame["taken"] and bool(self.evaluate(token[8:-1]))
                frame["taken"] = frame["taken"] or active
            elif token == "Else":
                frame = frames[-1]
                active = frame["parent"] and not frame["taken"]
                frame["taken"] = True
            elif token == "End":
                active = frames.pop()["parent"]
            elif active:
                if token == "Abort": return
                if token.startswith("Abort If("):
                    if self.evaluate(token[9:-1]): return
                elif token.startswith("Call Subroutine("):
                    self.run(token[len("Call Subroutine("):-1])
                elif token.startswith("Set Player Variable("):
                    args = next(validator.iter_calls(token, "Set Player Variable")).args
                    self.players[self.evaluate(args[0])][args[1].strip()] = self.evaluate(args[2])
                    if args[1].strip() == "DaftarTargetInspeksi":
                        self.follow_filters += 1
                elif token.startswith("Global.") and " = " in token:
                    target, value = token.rsplit(" = ", 1)
                    self.assign(target, self.evaluate(value))
                elif token.startswith("Destroy In-World Text("):
                    self.call("DestroyInWorldText", [self.evaluate(token[len("Destroy In-World Text("):-1])])
                else:
                    self.evaluate(token)
        if frames: raise AssertionError("unbalanced dummy maintenance control flow")

    def run(self, routine="RawatBotBuatan", now=None):
        if now is not None: self.now = now
        rule = validator.rule_by_subroutine(self.rules, routine)
        if rule is None: raise AssertionError(f"missing dummy routine: {routine}")
        self.execute_source(validator.rule_block(rule, "actions"))


class DummyMaintenanceTests(unittest.TestCase):
    def models(self):
        for path, _, _ in SOURCES:
            yield path.name, DummyMaintenanceEvaluator(path.read_text(encoding="utf-8"))

    def test_empty_teams_create_one_dummy_each_with_cooldown_already_armed(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.run(now=100)
                self.assertEqual(model.attempts, [(1, 100, 101), (2, 100, 101)])
                model.run(now=101)
                self.assertEqual(len(model.attempts), 2)
                self.assertEqual(sum(p["dummy"] and p["exists"] for p in model.players.values()), 2)

    def test_failed_creation_retries_no_faster_than_once_per_second_per_team(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.failed_teams.add(1)
                for now in (100, 100, 100.05, 100.5, 100.999, 101, 101.05, 102):
                    model.run(now=now)
                self.assertEqual(model.attempts, [(1, 100, 101), (2, 100, 101),
                                                 (1, 101, 102), (1, 102, 103)])

    def test_team_cooldowns_do_not_block_the_other_team(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.globals["WaktuCobaBotBuatanTim1"] = 110
                model.run(now=100)
                self.assertEqual(model.attempts, [(2, 100, 101)])
                model.run(now=110)
                self.assertEqual(model.attempts[-1], (1, 110, 111))

    def test_full_team_releases_dummy_then_reserves_last_human_slot_without_oscillation(self):
        for source, model in self.models():
            with self.subTest(source=source):
                for index in range(4): model.add(f"human-{index}")
                model.run(now=100)
                model.add("last-human")
                model.run(now=101)
                self.assertEqual(len(model.removals), 1)
                self.assertEqual(model.globals["WaktuCobaBotBuatanTim1"], 102)
                self.assertEqual([name for name, _ in model.native_actions],
                                 ["StopFacing", "StopThrottleInDirection", "DestroyDummyBot"])
                for now in range(102, 122): model.run(now=now)
                self.assertEqual(len(model.attempts), 2)
                self.assertEqual(len(model.removals), 1)
                self.assertEqual(model.call("NumberOfPlayers", [1]), 5)

    def test_two_free_slots_allow_return_after_human_leaves(self):
        for source, model in self.models():
            with self.subTest(source=source):
                for index in range(5): model.add(f"human-{index}")
                model.run(now=100)
                self.assertEqual([team for team, _, _ in model.attempts], [2])
                model.players["human-4"]["exists"] = False
                model.run(now=101)
                self.assertEqual([team for team, _, _ in model.attempts], [2, 1])

    def test_lifecycle_reservation_suspends_both_creation_and_removal(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.add("existing", dummy=True)
                for index in range(5): model.add(f"human-{index}")
                model.globals["PemainSiklusGlobal"] = "human-0"
                model.run(now=100)
                self.assertEqual(model.attempts, [])
                self.assertEqual(model.removals, [])
                model.globals["PemainSiklusGlobal"] = None
                model.run(now=101)
                self.assertEqual(model.removals, ["existing"])
                self.assertEqual([team for team, _, _ in model.attempts], [2])

    def test_creation_requires_ready_running_skirmish_with_spawn_points(self):
        for source, model in self.models():
            for reason in ("not-ready", "not-running", "other-mode", "no-spawns"):
                with self.subTest(source=source, reason=reason):
                    model.globals["Siap"] = reason != "not-ready"
                    model.in_progress = reason != "not-running"
                    model.mode = "TeamDeathmatch" if reason == "other-mode" else "Skirmish"
                    model.spawns = {1: [], 2: []} if reason == "no-spawns" else {1: [1], 2: [2]}
                    model.run(now=100)
                    self.assertEqual(model.attempts, [])

    def test_disappeared_dummy_can_be_recreated_without_duplicates(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.run(now=100)
                model.players["dummy-1-1"]["exists"] = False
                model.run(now=100.5)
                self.assertEqual(len(model.attempts), 2)
                model.run(now=101)
                self.assertEqual(model.attempts[-1], (1, 101, 102))
                self.assertEqual(sum(p["dummy"] and p["exists"] and p["team"] == 1
                                     for p in model.players.values()), 1)

    def test_dummy_removal_destroys_only_its_registered_vision_text(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.add("existing", dummy=True, TeksVisiNasib=123)
                for index in range(5): model.add(f"human-{index}")
                model.globals["PemilikTeksSementara"] = ["existing", "human-0"]
                model.globals["TeksVisiSementara"] = [123, 456]
                model.run(now=100)
                self.assertEqual(model.globals["TeksVisiSementara"], [0, 456])
                self.assertEqual(model.native_actions[0], ("DestroyInWorldText", 123))
                self.assertEqual(model.removals, ["existing"])

    def test_dead_dummy_and_normal_ai_rearm_lock_in_bot_maintenance(self):
        for source, model in self.models():
            for dummy in (True, False):
                for alive, spawned in ((False, True), (True, False)):
                    with self.subTest(source=source, dummy=dummy, alive=alive, spawned=spawned):
                        player = model.add("bot", dummy=dummy, Manusia=False,
                                           BotOtomatis=not dummy, alive=alive, spawned=spawned)
                        model.globals["PemainAktif"] = "bot"
                        model.run("ProsesBotPemain", now=100)
                        self.assertFalse(player["KunciBotAktif"])

    def test_normal_ai_releases_pending_lifecycle_after_classification_and_lock(self):
        for source, model in self.models():
            with self.subTest(source=source):
                player = model.add("bot", Manusia=False, BotOtomatis=True,
                                   PindahTimDiproses=True, SiklusPemainAktif=True)
                model.globals["PemainAktif"] = "bot"
                model.globals["PemainSiklusGlobal"] = "bot"
                model.run("ProsesBotPemain", now=100)
                self.assertFalse(player["PindahTimDiproses"])
                self.assertFalse(player["SiklusPemainAktif"])
                self.assertIsNone(model.globals["PemainSiklusGlobal"])
                self.assertEqual(model.globals["WaktuSiklusGlobal"], 100.25)

    def test_dummy_follow_refreshes_five_times_a_second_and_keeps_nearest_enemy_opt_in(self):
        for source, model in self.models():
            with self.subTest(source=source):
                dummy = model.add("dummy", dummy=True, slot=0)
                model.add("friendly", team=1, position=1, IzinkanBotBuatanMengikuti=True)
                model.add("opt-out", team=2, position=2)
                model.add("far", team=2, position=8, IzinkanBotBuatanMengikuti=True)
                model.add("near", team=2, position=4, IzinkanBotBuatanMengikuti=True)
                model.globals["PemainAktif"] = "dummy"
                for step in range(1, 21):
                    model.globals["LangkahPenjadwal"] = step
                    if step % 2 == 0: model.run("ProsesBotPemain", now=100 + step / 20)
                self.assertEqual(model.follow_filters, 5)
                self.assertEqual(dummy["TargetIkutiBotBuatan"], "near")
                model.players["near"]["IzinkanBotBuatanMengikuti"] = False
                model.globals["LangkahPenjadwal"] = 24
                model.run("ProsesBotPemain", now=101.2)
                self.assertEqual(dummy["TargetIkutiBotBuatan"], "far")


if __name__ == "__main__":
    unittest.main()
