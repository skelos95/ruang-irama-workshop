"""Execute source dispatch and protection/vote branches under a full lobby.

Counts are script calls and native property writes, not measured server load.
Engine scheduling, entity lifetime and client stress still require live QA.
"""

from collections import Counter
import re
import unittest

from tools import validate_workshop as validator
from tests.test_audit_lifecycle import AuditLifecycleEvaluator, project, statements
from tests.test_roster_rejoin_regressions import SOURCES


class LoadSourceEvaluator(AuditLifecycleEvaluator):
    PROPERTY_ACTIONS = {
        "SetDamageReceived", "SetKnockbackReceived",
        "EnableMovementCollisionWithPlayers", "DisableMovementCollisionWithPlayers",
    }

    def __init__(self, source):
        super().__init__(source)
        self.native = []
        self.run_icon_cleanup = False
        fast = validator.rule_by_subroutine(self.rules, "ProsesCepatPemain")
        position = fast.body.index("Set Player Health(Global.PemainAktif, 1);")
        branches = validator.conditional_branches_containing(fast.body, position)
        self.protection = next(branch for branch in branches
                               if "Global.PemainAktif.KebalAktif == True" in branch.split(";", 1)[0])
        vote = validator.rule_by_subroutine(self.rules, "TerapkanHalamanPilihan")
        self.apply_vote = statements(validator.rule_block(vote, "actions"))
        luck = validator.rule_by_subroutine(self.rules, "ProsesNasibPemain")
        self.icon_cleanup = next(node for node in statements(validator.rule_block(luck, "actions"))
                                 if node[0] == "If(Global.PemainAktif.WaktuIkonNasibBerakhir > 0)")

    def resolve(self, name):
        if name == "Unkillable":
            return name
        return super().resolve(name)

    def call(self, name, args):
        fields = {"HeroOf": "hero", "Health": "health", "MaxHealth": "max_health",
                  "IsInSpawnRoom": "in_spawn", "SlotOf": "slot"}
        if name in fields:
            return self.players[args[0]][fields[name]]
        if name == "HasStatus":
            return args[1] in self.players[args[0]]["statuses"]
        if name in self.PROPERTY_ACTIONS or name in ("SetStatus", "SetPlayerHealth"):
            self.native.append((name, *args))
            if name == "SetStatus":
                self.players[args[0]]["statuses"].add(args[2])
            elif name == "SetPlayerHealth":
                self.players[args[0]]["health"] = args[1]
            return None
        return super().call(name, args)

    def execute(self, nodes):
        for node in nodes:
            token = node[0]
            compound = re.fullmatch(r"(Event Player\.\w+) %= (.+)", token)
            if compound:
                target, value = compound.groups()
                self.assign(target, self.evaluate(target) % self.evaluate(value))
            else:
                if super().execute([node]):
                    return True
                if self.run_icon_cleanup and token == "Call Subroutine(ProsesNasibPemain)":
                    self.execute([self.icon_cleanup])
        return False

    def join(self, identity):
        admitted = super().join(identity)
        if admitted:
            # Execute the classifier's dirty marker rather than synthesizing a recount.
            self.execute(project(statements(self.classifier),
                                 lambda token: token == "Global.PilihanPerluDihitung = True"))
        return admitted

    def vote_for(self, identity, target):
        self.event_player = identity
        self.players[identity]["KursorPilihan"] = self.globals["PemainManusia"].index(target)
        self.execute(self.apply_vote)

    def prepare_protection(self, identity, mode):
        self.join(identity)
        self.players[identity].update(
            Manusia=True, KebalAktif=True, KematianBalasDendam=False,
            KartuNasibAktif=False, PutaranKartuNasib=0, EfekNasib=0,
            WaktuPaksaBerakhir=0, EfekNasibBerakhir=0, ModeKebal=mode,
            PahlawanTerakhir="Ana", hero="Ana", health=50, max_health=250,
            in_spawn=False, statuses={"Unkillable"}, IkonKebal=identity,
        )

    def protection_tick(self, identity, tick, index):
        self.globals.update(PemainAktif=identity, LangkahPenjadwal=tick, IndeksPemainGlobal=index)
        self.now = 10 + tick / 20
        # The same flat branch interpreter as the Fly tests, including Else If.
        frames = []
        active = True
        for token in validator.mask_strings(self.protection).split(";"):
            token = token.strip()
            if not token:
                continue
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
                self.evaluate(token)
        if frames:
            raise AssertionError("unbalanced protection branches")


class SchedulerLoadTests(unittest.TestCase):
    def models(self):
        for path, _, _ in SOURCES:
            yield path.name, LoadSourceEvaluator(path.read_text(encoding="utf-8"))

    def test_twelve_idle_players_skip_inactive_features_and_keep_balanced_cycle_work(self):
        for source, model in self.models():
            with self.subTest(source=source):
                players = [f"player-{index}" for index in range(12)]
                for identity in players:
                    model.join(identity)
                loads = []
                for tick in range(1, 21):
                    before = len(model.calls)
                    model.scheduler_tick(tick)
                    loads.append(Counter(name for _, name in model.calls[before:]))
                for identity in players:
                    for routine, expected in (("ProsesCepatPemain", 20), ("ProsesNasibPemain", 0),
                                              ("ProsesTerbangPemain", 0), ("ProsesSiklusPemain", 10),
                                              ("ProsesSimpananPemain", 0)):
                        self.assertEqual(model.calls.count((identity, routine)), expected, (identity, routine))
                self.assertEqual({load["ProsesSiklusPemain"] for load in loads}, {6})
                self.assertEqual(sum(load["ProsesSimpananPemain"] for load in loads), 0)
                self.assertIsNone(model.globals["PemainAktif"])
                self.assertEqual(model.globals["SalinanDaftarPemain"], [])

    def test_twelve_active_players_keep_fast_feature_timing_and_staggered_menu_caches(self):
        for source, model in self.models():
            with self.subTest(source=source):
                players = [f"player-{index}" for index in range(12)]
                for index, identity in enumerate(players):
                    model.join(identity)
                    model.players[identity].update(ModeTerbangAktif=True, KartuNasibAktif=True,
                                                   MenuTerbuka=True, HalamanMenu=1 if index % 2 else 4)
                loads = []
                for tick in range(1, 21):
                    before = len(model.calls)
                    model.scheduler_tick(tick)
                    loads.append(Counter(name for _, name in model.calls[before:]))
                for identity in players:
                    for routine, expected in (("ProsesCepatPemain", 20), ("ProsesNasibPemain", 20),
                                              ("ProsesTerbangPemain", 20), ("ProsesSiklusPemain", 10),
                                              ("ProsesSimpananPemain", 1)):
                        self.assertEqual(model.calls.count((identity, routine)), expected, (identity, routine))
                self.assertEqual({load["ProsesSiklusPemain"] for load in loads}, {6})
                self.assertEqual(max(load["ProsesSimpananPemain"] for load in loads), 1)
                self.assertEqual(sum(load["ProsesSimpananPemain"] for load in loads), 12)

    def test_each_pending_luck_state_keeps_twenty_hz_dispatch_until_cleared(self):
        for source, model in self.models():
            for field, value in (("KartuNasibAktif", True), ("PutaranKartuNasib", 3),
                                 ("EfekNasib", 2), ("WaktuIkonNasibBerakhir", 10)):
                with self.subTest(source=source, field=field):
                    identity = f"luck-{field}"
                    model.join(identity)
                    model.players[identity][field] = value
                    for tick in range(1, 21):
                        model.scheduler_tick(tick)
                    self.assertEqual(model.calls.count((identity, "ProsesNasibPemain")), 20)
                    model.players[identity][field] = 0
                    for tick in range(21, 41):
                        model.scheduler_tick(tick)
                    self.assertEqual(model.calls.count((identity, "ProsesNasibPemain")), 20)

    def test_fly_toggle_changes_dispatch_on_the_next_tick_only_for_humans(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.join("human")
                model.scheduler_tick(1)
                self.assertNotIn(("human", "ProsesTerbangPemain"), model.calls)
                model.players["human"]["ModeTerbangAktif"] = True
                model.scheduler_tick(2)
                self.assertEqual(model.calls.count(("human", "ProsesTerbangPemain")), 1)
                model.players["human"]["ModeTerbangAktif"] = False
                model.scheduler_tick(3)
                self.assertEqual(model.calls.count(("human", "ProsesTerbangPemain")), 1)
                model.players["human"].update(ModeTerbangAktif=True, Manusia=False)
                model.scheduler_tick(4)
                self.assertEqual(model.calls.count(("human", "ProsesTerbangPemain")), 1)

    def test_mixed_lobby_excludes_bots_even_with_stale_human_feature_flags(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.join("human")
                for identity, dummy, automatic in (("dummy", True, False), ("ai", False, True)):
                    model.players[identity] = dict(exists=True, spawned=True, alive=True, slot=5,
                                                   dummy=dummy, BotOtomatis=automatic, Manusia=True,
                                                   ModeTerbangAktif=True, KartuNasibAktif=True,
                                                   PutaranKartuNasib=3, EfekNasib=2,
                                                   WaktuIkonNasibBerakhir=10, MenuTerbuka=True,
                                                   HalamanMenu=1, UrutanHUD=0)
                for tick in range(1, 21):
                    model.scheduler_tick(tick)
                for identity in ("dummy", "ai"):
                    calls = Counter(name for owner, name in model.calls if owner == identity)
                    self.assertEqual(calls, Counter({"ProsesBotPemain": 10}))
                self.assertEqual(model.calls.count(("human", "ProsesCepatPemain")), 20)
                self.assertEqual(model.calls.count(("human", "ProsesSiklusPemain")), 10)

    def test_pending_human_keeps_lifecycle_and_cycle_without_menu_or_fly_work(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.players["pending"] = dict(exists=True, spawned=False, alive=False, slot=3,
                                                 dummy=False, BotOtomatis=False, Manusia=False,
                                                 ModeTerbangAktif=True, KartuNasibAktif=False,
                                                 PutaranKartuNasib=0, EfekNasib=0,
                                                 WaktuIkonNasibBerakhir=0, MenuTerbuka=True, HalamanMenu=1)
                for tick in range(1, 21):
                    model.scheduler_tick(tick)
                self.assertEqual(Counter(name for owner, name in model.calls if owner == "pending"),
                                 Counter({"ProsesCepatPemain": 20, "ProsesSiklusPemain": 10}))

    def test_idle_human_two_dummies_two_ai_use_seventy_entity_calls_and_one_slot_pass(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.join("human")
                for index in range(4):
                    model.players[f"bot-{index}"] = dict(exists=True, dummy=index < 2,
                        BotOtomatis=index >= 2, Manusia=False, slot=index % 2)
                for tick in range(1, 21):
                    model.scheduler_tick(tick)
                entity_calls = [name for owner, name in model.calls if owner is not None]
                self.assertEqual(Counter(entity_calls), Counter({"ProsesCepatPemain": 20,
                    "ProsesSiklusPemain": 10, "ProsesBotPemain": 40}))
                self.assertEqual(len(entity_calls), 70)
                self.assertEqual(model.calls.count((None, "RawatBotBuatan")), 1)
                self.assertEqual(model.calls.count((None, "BersihkanTeksYatim")), 1)

    def test_quarantined_human_luck_icon_expires_then_stops_dispatching(self):
        for source, model in self.models():
            with self.subTest(source=source):
                model.join("human")
                slot = model.players["human"]["UrutanHUD"]
                model.players["human"].update(Manusia=False, IkonKartuNasib=77,
                                               WaktuIkonNasibBerakhir=1)
                model.globals["IkonKartuNasibPemain"][int(slot)] = 77
                model.run_icon_cleanup = True
                model.now = 0.95
                model.scheduler_tick(19)
                self.assertEqual(model.destroyed, [])
                model.now = 1
                model.scheduler_tick(20)
                self.assertEqual(model.destroyed, [77])
                self.assertEqual(model.globals["IkonKartuNasibPemain"][int(slot)], 0)
                self.assertEqual(model.players["human"]["WaktuIkonNasibBerakhir"], 0)
                self.assertIsNone(model.players["human"]["IkonKartuNasib"])
                self.assertTrue(model.players["human"]["MenuNasibHarusDibuka"])
                model.scheduler_tick(21)
                self.assertEqual(model.calls.count(("human", "ProsesNasibPemain")), 2)

    def test_menu_cache_runs_only_on_camera_or_revenge_pages(self):
        for source, model in self.models():
            for page in range(-1, 15):
                for opened in (False, True):
                    with self.subTest(source=source, page=page, opened=opened):
                        if "human" not in model.players:
                            model.join("human")
                        model.players["human"].update(MenuTerbuka=opened, HalamanMenu=page)
                        model.calls.clear()
                        for tick in range(1, 21):
                            model.scheduler_tick(tick)
                        self.assertEqual(model.calls.count(("human", "ProsesSimpananPemain")),
                                         int(opened and page in (1, 4)))

    def test_stable_protection_has_36_property_writes_per_second_for_twelve_players(self):
        for source, model in self.models():
            for mode in (1, 2):
                with self.subTest(source=source, mode=mode):
                    for index in range(12):
                        model.prepare_protection(f"player-{index}", mode)
                    model.native.clear()
                    per_tick = []
                    for tick in range(1, 21):
                        before = len(model.native)
                        for index in range(12):
                            model.protection_tick(f"player-{index}", tick, index)
                        per_tick.append(sum(action[0] in model.PROPERTY_ACTIONS
                                            for action in model.native[before:]))
                    writes = [action for action in model.native if action[0] in model.PROPERTY_ACTIONS]
                    self.assertEqual(len(writes), 36)  # Former unconditional 20 Hz path wrote 720.
                    self.assertEqual(max(per_tick), 3)
                    self.assertEqual(Counter(action[1] for action in writes),
                                     Counter({f"player-{index}": 3 for index in range(12)}))
                    self.assertFalse(any(action[0] == "SetStatus" for action in model.native))

    def test_changing_preceding_slot_cannot_starve_a_stable_player(self):
        for source, model in self.models():
            with self.subTest(source=source):
                # Alternating availability changes the compact All Players index
                # every tick. The same player's assigned HUD slot stays stable.
                model.players["changing-slot"] = {
                    "exists": False, "spawned": True, "alive": True,
                    "dummy": True, "BotOtomatis": True, "Manusia": False, "slot": 5,
                }
                model.prepare_protection("stable-player", 2)
                seen_indices = set()
                for tick in range(1, 61):
                    model.players["changing-slot"]["exists"] = tick % 2 == 0
                    model.scheduler_tick(tick)
                    current = [identity for identity, state in model.players.items() if state["exists"]]
                    index = current.index("stable-player")
                    seen_indices.add(index)
                    model.protection_tick("stable-player", tick, index)
                self.assertEqual(seen_indices, {0, 1})
                for routine, expected in (("ProsesCepatPemain", 60), ("ProsesSiklusPemain", 30),
                                          ("ProsesSimpananPemain", 0)):
                    self.assertEqual(model.calls.count(("stable-player", routine)), expected, routine)
                self.assertEqual(sum(action[0] in model.PROPERTY_ACTIONS for action in model.native), 9)

    def test_reordering_twelve_players_preserves_each_phase_and_balanced_work(self):
        for source, model in self.models():
            with self.subTest(source=source):
                players = [f"player-{index}" for index in range(12)]
                for identity in players:
                    model.join(identity)
                    model.players[identity].update(MenuTerbuka=True, HalamanMenu=1)
                for tick in range(1, 21):
                    offset = tick % len(players)
                    order = players[offset:] + players[:offset]
                    model.players = {identity: model.players[identity] for identity in order}
                    before = len(model.calls)
                    model.scheduler_tick(tick)
                    load = Counter(name for _, name in model.calls[before:])
                    self.assertEqual(load["ProsesSiklusPemain"], 6)
                    self.assertLessEqual(load["ProsesSimpananPemain"], 1)
                for identity in players:
                    self.assertEqual(model.calls.count((identity, "ProsesSiklusPemain")), 10)
                    self.assertEqual(model.calls.count((identity, "ProsesSimpananPemain")), 1)

    def test_health_guard_still_runs_every_fast_tick(self):
        for source, model in self.models():
            for mode, start, expected in ((1, 250, 1), (2, 1, 250)):
                with self.subTest(source=source, mode=mode):
                    model.prepare_protection("one", mode)
                    model.native.clear()
                    for tick in range(1, 21):
                        model.players["one"]["health"] = start
                        model.protection_tick("one", tick, 0)
                        self.assertEqual(model.players["one"]["health"], expected)
                    self.assertEqual(sum(action[0] == "SetPlayerHealth" for action in model.native), 20)

    def test_status_loss_and_hero_change_restore_properties_before_the_scheduled_phase(self):
        for source, model in self.models():
            for mode in (1, 2):
                for change in ("status", "hero"):
                    with self.subTest(source=source, mode=mode, change=change):
                        model.prepare_protection("one", mode)
                        if change == "status":
                            model.players["one"]["statuses"].clear()
                        else:
                            model.players["one"]["hero"] = "Mercy"
                        model.native.clear()
                        model.protection_tick("one", 1, 0)
                        writes = [action for action in model.native if action[0] in model.PROPERTY_ACTIONS]
                        self.assertEqual(len(writes), 3)
                        self.assertEqual(writes[0], ("SetDamageReceived", "one", 100 if mode == 1 else 0))
                        self.assertEqual(sum(action[0] == "SetStatus" for action in model.native), change == "status")
                        self.assertIn("Unkillable", model.players["one"]["statuses"])

    def test_forced_death_and_active_burning_never_reapply_protection(self):
        exclusions = (
            {"KematianBalasDendam": True},
            {"KartuNasibAktif": True, "EfekNasib": 3, "WaktuPaksaBerakhir": 30},
            {"KartuNasibAktif": True, "EfekNasib": 5, "EfekNasibBerakhir": 30},
            {"alive": False},
            {"spawned": False},
        )
        for source, model in self.models():
            for mode in (1, 2):
                for changes in exclusions:
                    with self.subTest(source=source, mode=mode, changes=changes):
                        model.prepare_protection("one", mode)
                        model.players["one"].update(alive=True, spawned=True)
                        model.players["one"].update(changes)
                        model.players["one"]["statuses"].clear()
                        model.native.clear()
                        model.protection_tick("one", 20, 0)
                        self.assertEqual(model.native, [])

    def test_twelve_votes_are_counted_once_with_self_votes_and_ties_preserved(self):
        for source, model in self.models():
            with self.subTest(source=source):
                players = [f"player-{index}" for index in range(12)]
                for identity in players:
                    model.join(identity)
                    model.vote_for(identity, players[0])
                self.assertEqual(model.calls, [])
                model.scheduler_tick(1)
                self.assertEqual(model.calls.count((None, "HitungPilihan")), 1)
                self.assertEqual(model.players[players[0]]["JumlahPilihan"], 12)
                self.assertEqual(model.globals["PemimpinPilihan"], players[0])
                self.assertFalse(model.globals["PilihanPerluDihitung"])
                for identity in players:
                    model.vote_for(identity, players[0])
                model.scheduler_tick(2)
                self.assertEqual(model.calls.count((None, "HitungPilihan")), 1)
                for identity in players[6:]:
                    model.vote_for(identity, players[1])
                model.scheduler_tick(3)
                self.assertEqual(model.calls.count((None, "HitungPilihan")), 2)
                self.assertEqual(model.players[players[0]]["JumlahPilihan"], 6)
                self.assertEqual(model.players[players[1]]["JumlahPilihan"], 6)
                self.assertTrue(model.globals["PilihanSeri"])
                self.assertIsNone(model.globals["PemimpinPilihan"])

    def test_vote_batch_with_lost_departures_and_rejoins_has_no_stale_owner(self):
        for source, model in self.models():
            with self.subTest(source=source):
                players = [f"player-{index}" for index in range(12)]
                for identity in players:
                    model.join(identity)
                for index, identity in enumerate(players):
                    model.vote_for(identity, players[0] if index < 6 else players[1])
                for identity in (players[0], players[6]):
                    model.players[identity] = {"exists": False}
                    model.remove(identity)
                for identity in ("new-a", "new-b"):
                    self.assertTrue(model.join(identity))
                    model.vote_for(identity, players[1])
                self.assertEqual(model.calls, [])
                model.scheduler_tick(1)
                self.assertEqual(model.calls.count((None, "HitungPilihan")), 1)
                self.assertEqual(model.players[players[1]]["JumlahPilihan"], 7)
                self.assertEqual(model.globals["PemimpinPilihan"], players[1])
                self.assertFalse(model.globals["PilihanSeri"])
                for identity in model.globals["PemainManusia"]:
                    self.assertNotIn(model.players[identity]["PemainDipilih"], (players[0], players[6]))
                self.assertEqual(len(model.globals["PemainManusia"]), 12)
                self.assertEqual(sorted(model.globals["SlotHUDPemain"]), list(range(12)))
                model.scheduler_tick(2)
                self.assertEqual(model.calls.count((None, "HitungPilihan")), 1)


if __name__ == "__main__":
    unittest.main()
