from pathlib import Path
import re
import unittest

from tools import validate_workshop as validator
from tests.test_fly_motion import Expression


ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    (ROOT / "workshop" / "ruang_irama.it-IT.workshop", "regola", "Globale"),
    (ROOT / "tests" / "fixtures" / "semantic_reference.txt", "rule", "Global"),
)


def block(source: str, start: str, end: str) -> str:
    return source.split(start, 1)[1].split(end, 1)[0]


class LifecycleSourceEvaluator:
    """Execute source-derived roster operations and lifecycle guards, not engine physics.

    Only canonical array bookkeeping is projected from the cleanup/classifier.
    Engine HUD rendering, event ordering, and entity lifetime still need live QA.
    """

    ARRAYS = ("PemainManusia", "SlotHUDPemain", "HudKiriPemain", "HudKananPemain",
              "HudMenuPemain", "TeksDuniaPemain")

    def __init__(self, source: str) -> None:
        self.rules = validator.extract_rules(source)
        self.globals = {name: [] for name in self.ARRAYS}
        self.globals.update(SlotHUDTersedia=list(range(12)), PemainSiklusGlobal=None,
                            WaktuSiklusGlobal=0, PemainAktif=None)
        self.players = {}
        self.event_player = None
        self.now = 0
        self.destroyed = []
        cleanup = validator.rule_by_subroutine(self.rules, "BersihkanPemain")
        self.cleanup = validator.mask_strings(validator.rule_block(cleanup, "actions"))
        classifier = next(rule for rule in self.rules
                          if "Append To Array(Global.PemainManusia, Event Player)" in rule.body)
        self.classifier = validator.mask_strings(validator.rule_block(classifier, "actions"))

    def resolve(self, name):
        constants = {"True": True, "False": False, "Null": None,
                     "TotalTimeElapsed": self.now, "EventPlayer": self.event_player,
                     "CurrentArrayElement": "sort-key"}
        if name in constants:
            return constants[name]
        if name.startswith("EventPlayer."):
            return self.players[self.event_player].get(name.split(".", 1)[1], False)
        if name.startswith("Global."):
            parts = name.split(".")
            value = self.globals[parts[1]]
            return self.players[value].get(parts[2], False) if len(parts) == 3 else value
        raise AssertionError(f"unsupported lifecycle value {name}")

    def call(self, name, args):
        if name == "And": return all(args)
        if name == "Or": return any(args)
        if name == "CountOf": return len(args[0])
        if name == "ArrayContains": return args[1] in args[0]
        if name == "IndexOfArrayValue": return args[0].index(args[1]) if args[1] in args[0] else -1
        if name == "FirstOf": return args[0][0]
        if name == "AppendToArray": return args[0] + [args[1]]
        if name == "SortedArray": return sorted(args[0])
        if name == "At": return args[0][int(args[1])]
        if name in ("TeamOf", "HasSpawned", "EntityExists", "IsDummyBot"):
            key = {"TeamOf": "team", "HasSpawned": "spawned", "EntityExists": "exists", "IsDummyBot": "dummy"}[name]
            return self.players.get(args[0], {}).get(key, False)
        raise AssertionError(f"unsupported lifecycle function {name}")

    def evaluate(self, expression):
        packed = re.sub(r"\s+", "", expression)
        packed = re.sub(r"(Global\.[A-Za-z]+)\[([^\]]+)\]", r"At(\1,\2)", packed)
        return Expression(packed).evaluate(self)

    def assign(self, target, value):
        indexed = re.fullmatch(r"Global\.(\w+)\[(.+)\]", target)
        if indexed:
            self.globals[indexed.group(1)][int(self.evaluate(indexed.group(2)))] = value
            return
        parts = target.strip().split(".")
        if parts[0] == "Event Player":
            self.players[self.event_player][parts[1]] = value
        elif len(parts) == 3:
            self.players[self.globals[parts[1]]][parts[2]] = value
        else:
            self.globals[parts[1]] = value

    def execute_assignment(self, statement):
        target, expression = statement.split("=", 1)
        self.assign(target.strip(), self.evaluate(expression.strip()))

    def execute_atomic(self, source):
        enabled = [True]
        for statement in validator.mask_strings(source).split(";"):
            statement = statement.strip()
            if not statement:
                continue
            if statement.startswith("If("):
                enabled.append(enabled[-1] and bool(self.evaluate(statement[3:-1])))
            elif statement == "End":
                enabled.pop()
            elif enabled[-1]:
                if statement.startswith("Destroy HUD Text("):
                    self.destroyed.append(self.evaluate(statement[len("Destroy HUD Text("):-1]))
                elif re.match(r"(?:Global\.|Event Player\.)[^=]+=(?!=)", statement):
                    self.execute_assignment(statement)
                else:
                    raise AssertionError(f"unsupported lifecycle statement {statement}")
        if enabled != [True]:
            raise AssertionError("unclosed lifecycle branch")

    def source_branch(self, rule, marker):
        position = rule.body.index(marker)
        return min(validator.conditional_branches_containing(rule.body, position), key=len)

    def tick_pending(self, identity, now):
        self.now = now
        self.globals["PemainAktif"] = identity
        scheduler = next(rule for rule in self.rules
                         if validator.event_type(rule) == "Ongoing - Global"
                         and "Call Subroutine(ProsesCepatPemain);" in rule.body)
        self.execute_atomic(self.source_branch(scheduler, "Global.PemainSiklusGlobal = Null;"))
        fast = validator.rule_by_subroutine(self.rules, "ProsesCepatPemain")
        self.execute_atomic(self.source_branch(fast, "Global.PemainAktif.TimSiklusTarget = Team Of(Global.PemainAktif);"))
        self.execute_atomic(self.source_branch(fast, "Global.PemainSiklusGlobal = Global.PemainAktif;"))

    def close_menu(self, identity):
        self.event_player = identity
        rule = validator.rule_by_subroutine(self.rules, "TutupMenu")
        actions = validator.rule_block(rule, "actions")
        self.execute_atomic(actions.split("Event Player.MenuTerbuka = False;", 1)[0])

    def join(self, identity):
        self.event_player = identity
        self.players.setdefault(identity, {"team": 1, "spawned": True, "exists": True, "dummy": False})
        duplicate = re.search(r"Abort If\((Array Contains\(Global.PemainManusia, Event Player\))\);", self.classifier)
        empty = re.search(r"If\((Count Of\(Global.SlotHUDTersedia\) == 0)\);", self.classifier)
        if self.evaluate(duplicate.group(1)) or self.evaluate(empty.group(1)):
            return False
        for statement in self.classifier.split(";"):
            statement = statement.strip()
            if statement.startswith("Event Player.UrutanHUD ="):
                self.execute_assignment(statement)
            elif re.match(r"Global\.(?:" + "|".join(self.ARRAYS) + r") = Append To Array\(", statement):
                self.execute_assignment(statement)
            elif statement == "Modify Global Variable(SlotHUDTersedia, Remove From Array By Index, 0)":
                self.globals["SlotHUDTersedia"].pop(0)
        return True

    def remove(self, identity):
        self.event_player = identity
        for name in ("PemainPembersihan", "IndeksKeluar"):
            expression = re.search(rf"Global\.{name} = ([^;]+);", self.cleanup).group(1)
            self.globals[name] = self.evaluate(expression)
        recycle_position = self.cleanup.index("Global.SlotHUDTersedia =")
        branches = validator.conditional_branches_containing(self.cleanup, recycle_position)
        guard = branches[0].splitlines()[0].strip()[3:-2]
        if not self.evaluate(guard):
            return
        for statement in branches[0].split(";"):
            statement = statement.strip()
            if re.match(r"Global\.(IndeksPembersihan|IndeksUtangKeluar|SlotHUDTersedia) =", statement):
                self.execute_assignment(statement)
            elif re.match(r"Destroy (?:HUD|In-World) Text\(Global\.(?:HudKiriPemain|HudKananPemain|HudMenuPemain|TeksDuniaPemain)\[", statement):
                expression = statement[statement.index("(") + 1:-1]
                handle = self.evaluate(expression)
                if handle:
                    self.destroyed.append(handle)
            else:
                removal = re.fullmatch(r"Modify Global Variable\((\w+), Remove From Array By Index, (Global\.IndeksPembersihan)\)", statement)
                if removal:
                    self.globals[removal.group(1)].pop(int(self.evaluate(removal.group(2))))


class ExecutedRosterLifecycleTests(unittest.TestCase):
    def model(self):
        return LifecycleSourceEvaluator(validator.SOURCE.read_text(encoding="utf-8"))

    def test_leave_rejoin_reuses_only_the_freed_slot_without_inheriting_handles(self):
        model = self.model()
        for identity in ("alice", "bob", "carol"):
            self.assertTrue(model.join(identity))
        for offset, array in enumerate(model.ARRAYS[2:]):
            model.globals[array] = [100 + offset, 200 + offset, 300 + offset]
        model.remove("bob")
        self.assertEqual(model.destroyed, [200, 201, 202, 203])
        self.assertEqual(model.globals["PemainManusia"], ["alice", "carol"])
        self.assertEqual(model.globals["SlotHUDPemain"], [0, 2])
        model.remove("bob")
        self.assertTrue(model.join("dave"))
        self.assertEqual(model.globals["SlotHUDPemain"], [0, 2, 1])
        for array in model.ARRAYS[2:]:
            self.assertEqual(model.globals[array][-1], 0)
        before = {key: list(model.globals[key]) for key in model.ARRAYS + ("SlotHUDTersedia",)}
        model.remove("bob")
        self.assertEqual(before, {key: model.globals[key] for key in before})
        self.assertEqual(len(model.destroyed), 4)

    def test_repeated_team_reset_and_duplicate_join_keep_parallel_arrays_consistent(self):
        model = self.model()
        model.join("alice")
        model.join("bob")
        for _ in range(30):
            model.remove("alice")
            self.assertTrue(model.join("alice"))
            self.assertFalse(model.join("alice"))
            self.assertTrue(all(len(model.globals[array]) == 2 for array in model.ARRAYS))
            self.assertEqual(sorted(model.globals["SlotHUDPemain"] + model.globals["SlotHUDTersedia"]), list(range(12)))
            self.assertEqual(len(set(model.globals["SlotHUDTersedia"])), 10)

    def test_full_lobby_rejects_extra_join_then_admits_a_new_identity_to_freed_slot(self):
        model = self.model()
        for index in range(12):
            self.assertTrue(model.join(f"player-{index}"))
        self.assertFalse(model.join("extra"))
        model.remove("player-5")
        self.assertTrue(model.join("extra"))
        self.assertEqual(model.players["extra"]["UrutanHUD"], 5)
        self.assertEqual(model.globals["SlotHUDTersedia"], [])

    def test_rapid_second_team_switch_updates_pending_target_without_blocking_next_player(self):
        model = self.model()
        model.players["alice"] = {"team": 2, "spawned": True, "exists": True, "dummy": False,
                                  "PindahTimDiproses": True, "TimSiklusTarget": 1, "WaktuSiklusTim": 10}
        model.globals["PemainSiklusGlobal"] = "alice"
        model.tick_pending("alice", 10)
        self.assertEqual(model.players["alice"]["TimSiklusTarget"], 2)
        self.assertEqual(model.players["alice"]["WaktuSiklusTim"], 10.25)
        self.assertIsNone(model.globals["PemainSiklusGlobal"])
        model.tick_pending("alice", 10.24)
        self.assertIsNone(model.globals["PemainSiklusGlobal"])
        model.tick_pending("alice", 10.25)
        self.assertEqual(model.globals["PemainSiklusGlobal"], "alice")
        model.players["alice"]["spawned"] = False
        model.players["bob"] = {"team": 1, "spawned": True, "exists": True, "dummy": False,
                                "PindahTimDiproses": True, "TimSiklusTarget": 1, "WaktuSiklusTim": 10}
        model.tick_pending("bob", 10.30)
        self.assertIsNone(model.globals["PemainSiklusGlobal"])
        model.tick_pending("bob", 10.55)
        self.assertEqual(model.globals["PemainSiklusGlobal"], "bob")

    def test_menu_cleanup_finds_canonical_handle_even_when_local_handle_was_lost(self):
        for local_handle, expected_destroyed in ((None, [501]), (501, [501]), (502, [501, 502])):
            with self.subTest(local_handle=local_handle):
                model = self.model()
                model.join("alice")
                model.globals["HudMenuPemain"][0] = 501
                model.players["alice"]["HudMenu"] = local_handle
                model.close_menu("alice")
                self.assertEqual(model.destroyed, expected_destroyed)
                self.assertEqual(model.globals["HudMenuPemain"], [0])
                self.assertIsNone(model.players["alice"]["HudMenu"])
                model.close_menu("alice")
                self.assertEqual(model.destroyed, expected_destroyed)


class RosterRejoinRegressionTests(unittest.TestCase):
    def test_visible_name_is_never_persistent_roster_identity(self):
        for path, _, _ in SOURCES:
            source = path.read_text(encoding="utf-8")
            for forbidden in (
                "ProfilNama",
                "ProfilPreferensiA",
                "ProfilPreferensiB",
                "ProfilStatus",
                "ProfilSosial",
                "ProfilPilihanNama",
                "NamaSlotHUD",
                "PemainPengganti",
            ):
                self.assertNotIn(forbidden, source, f"{path.name}: {forbidden} must not own player identity")

    def test_true_leave_recycles_the_roster_slot(self):
        for path, rule_kw, global_name in SOURCES:
            source = path.read_text(encoding="utf-8")
            left = block(
                source,
                f'{rule_kw}("04 - Pemain Keluar: Bersihkan hanya saat benar-benar keluar")',
                f'{rule_kw}("04g - Utama global: Penjadwal pusat 20 Hz")',
            )
            self.assertIn("Wait(0.500,", left)
            self.assertIn("Abort If(Entity Exists(Event Player) == True);", left)
            self.assertIn("Call Subroutine(BersihkanPemain);", left)
            self.assertNotIn("Custom String(\"{0}\", Event Player)", left)

            cleanup = block(
                source,
                f'{rule_kw}("93c - Subrutin: Bersihkan referensi pemain yang benar-benar keluar")',
                f'{rule_kw}("94 - Subrutin: Siapkan pemain',
            )
            recycle = (
                f"{global_name}.SlotHUDTersedia = Sorted Array(Append To Array("
                f"{global_name}.SlotHUDTersedia, {global_name}.IndeksUtangKeluar), Current Array Element);"
            )
            self.assertIn(recycle, cleanup)
            self.assertIn("Modify Global Variable(SlotHUDPemain, Remove From Array By Index", cleanup)
            self.assertIn("Modify Global Variable(PemainManusia, Remove From Array By Index", cleanup)

    def test_duplicate_and_temporarily_blank_names_never_own_or_replace_roster_identity(self):
        for path, rule_kw, global_name in SOURCES:
            source = path.read_text(encoding="utf-8")
            classifier = block(
                source,
                f'{rule_kw}("02 - Pemain: Pisahkan manusia dari pasukan kaleng")',
                f'{rule_kw}("03c - Bot/Dummy',
            )
            capture = 'Event Player.NamaTampilan = Evaluate Once(Custom String("{0}", Event Player));'
            allocation = f"Event Player.UrutanHUD = First Of({global_name}.SlotHUDTersedia);"
            self.assertIn(capture, classifier)
            self.assertIn(allocation, classifier)
            self.assertIn(f"{global_name}.PemainManusia = Append To Array({global_name}.PemainManusia, Event Player);", classifier)
            between_capture_and_slot = classifier.split(capture, 1)[1].split(allocation, 1)[0]
            self.assertNotIn("Index Of Array Value", between_capture_and_slot)
            self.assertNotIn("NamaSlotHUD", classifier)
            self.assertNotIn("PemainPengganti", classifier)

            roster = block(
                source,
                f'{rule_kw}("02 - Pemain: Pisahkan manusia dari pasukan kaleng")',
                f'{rule_kw}("03c - Bot/Dummy',
            )
            self.assertIn(
                'And(Event Player.NamaTampilan != Null, Event Player.NamaTampilan != Custom String(""))',
                roster,
            )

            fast = block(
                source,
                f'{rule_kw}("89a - Subrutin: Proses status cepat pemain")',
                f'{rule_kw}("89b - Subrutin',
            )
            self.assertIn(
                f'Custom String("{{0}}", {global_name}.PemainAktif) != Custom String("")',
                fast,
            )
            self.assertIn(
                f'{global_name}.PemainAktif.NamaTampilan = Evaluate Once(Custom String("{{0}}", {global_name}.PemainAktif));',
                fast,
            )

    def test_temporarily_blank_visible_name_does_not_consume_a_roster_slot(self):
        for path, rule_kw, global_name in SOURCES:
            source = path.read_text(encoding="utf-8")
            classifier = block(
                source,
                f'{rule_kw}("02 - Pemain: Pisahkan manusia dari pasukan kaleng")',
                f'{rule_kw}("03c - Bot/Dummy',
            )
            capture = 'Event Player.NamaTampilan = Evaluate Once(Custom String("{0}", Event Player));'
            allocation = f"Event Player.UrutanHUD = First Of({global_name}.SlotHUDTersedia);"
            self.assertIn(capture, classifier)
            self.assertIn(allocation, classifier)
            before_allocation = classifier.split(capture, 1)[1].split(allocation, 1)[0]
            blank_name_gate = (
                'If(Or(Event Player.NamaTampilan == Null, '
                'Event Player.NamaTampilan == Custom String("")));'
            )
            self.assertIn(blank_name_gate, before_allocation)
            blank_retry = before_allocation.split(blank_name_gate, 1)[1]
            self.assertIn("Event Player.SudahDiperiksa = False;", blank_retry)
            self.assertIn("Event Player.SudahSiap = False;", blank_retry)
            self.assertIn("Abort;", blank_retry)
            self.assertNotIn("Remove From Array By Index", blank_retry)

    def test_true_leave_clears_other_players_votes_for_the_departed_entity(self):
        for path, rule_kw, global_name in SOURCES:
            source = path.read_text(encoding="utf-8")
            cleanup = block(
                source,
                f'{rule_kw}("93c - Subrutin: Bersihkan referensi pemain yang benar-benar keluar")',
                f'{rule_kw}("94 - Subrutin: Siapkan pemain',
            )
            voters = (
                f"Filtered Array({global_name}.PemainManusia, "
                f"Player Variable(Current Array Element, PemainDipilih) == "
                f"{global_name}.PemainPembersihan)"
            )
            clear_votes = f"Set Player Variable({voters}, PemainDipilih, Null);"
            roster_removal = "Modify Global Variable(PemainManusia, Remove From Array By Index"
            self.assertIn(clear_votes, cleanup)
            self.assertIn(roster_removal, cleanup)
            self.assertLess(cleanup.index(clear_votes), cleanup.index(roster_removal))

    def test_true_rejoin_starts_with_fresh_vote_and_unkillable_state(self):
        for path, rule_kw, _ in SOURCES:
            source = path.read_text(encoding="utf-8")
            setup = block(
                source,
                f'{rule_kw}("94 - Subrutin: Siapkan pemain',
                f'{rule_kw}("95 - Subrutin: Segarkan daftar tontonan',
            )
            for expected in (
                "Event Player.PemainDipilih = Null;",
                "Event Player.JumlahPilihan = 0;",
                "Event Player.KebalAktif = False;",
                "Event Player.KursorKebal = 0;",
                "Event Player.ModeKebal = 0;",
            ):
                self.assertIn(expected, setup)

    def test_unkillable_runtime_state_is_self_repaired(self):
        for path, rule_kw, global_name in SOURCES:
            source = path.read_text(encoding="utf-8")
            fast = block(
                source,
                f'{rule_kw}("89a - Subrutin: Proses status cepat pemain")',
                f'{rule_kw}("89b - Subrutin',
            )
            self.assertIn(f"{global_name}.PemainAktif.KebalAktif == True", fast)
            self.assertIn(f"Has Status({global_name}.PemainAktif, Unkillable) == False", fast)
            self.assertIn(f"Set Status({global_name}.PemainAktif, Null, Unkillable, 9999);", fast)
            self.assertIn(f"Set Damage Received({global_name}.PemainAktif, 0);", fast)

    def test_special_player_rejoin_uses_documented_defaults(self):
        for path, rule_kw, _ in SOURCES:
            source = path.read_text(encoding="utf-8")
            classifier = block(
                source,
                f'{rule_kw}("02 - Pemain: Pisahkan manusia dari pasukan kaleng")',
                f'{rule_kw}("03c - Bot/Dummy',
            )
            self.assertIn('If(Custom String("{0}", Event Player) == Custom String("งูแท้"));', classifier)
            self.assertIn('Event Player.MusikKhusus = Custom String("Caladan Brood");', classifier)
            self.assertIn("Event Player.IndeksWarna = 1;", classifier)
            self.assertIn("Event Player.KursorWarna = 1;", classifier)
            self.assertIn("Event Player.IndeksIkon = 23;", classifier)
            self.assertIn("Event Player.KursorIkon = 23;", classifier)
            self.assertNotIn("Profil", classifier)


if __name__ == "__main__":
    unittest.main()
