"""Logical input mutations for the first-selection deadline before compilation."""

from __future__ import annotations

import re
import unittest

from tools import check_clipboard_import as clipboard
from tools import validate_workshop as validator


class HeroTimeoutValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = validator.SOURCE.read_text(encoding="utf-8")
        cls.rules = validator.extract_rules(cls.source)
        cls.player = "Global.PemainAktif"
        cls.clock = cls.player + ".WaktuPilihPahlawan"
        cls.latch = cls.player + ".PilihanPahlawanSelesai"
        cls.arm = cls.clock + " = Total Time Elapsed + 60;"
        cls.start = f"Start Forcing Player To Be Hero({cls.player}, Hero(Shion));"
        cls.stop = f"Stop Forcing Player To Be Hero({cls.player});"

    def errors(self, source):
        checks = validator.Checks()
        validator.validate_hero_selection_timeout(checks, validator.extract_rules(source))
        return checks.errors

    def mutation(self, old, new, source=None):
        source = self.source if source is None else source
        self.assertIn(old, source)
        return source.replace(old, new, 1)

    def routine_mutation(self, routine, old, new):
        rule = validator.rule_by_subroutine(self.rules, routine)
        changed = self.mutation(old, new, rule.body)
        return self.mutation(rule.body, changed)

    def test_current_runtime_passes_in_both_grammars(self):
        self.assertEqual(self.errors(self.source), [])
        source = clipboard.BEHAVIORAL_SOURCE.read_text(encoding="utf-8")
        parts = re.split(r'("(?:\\.|[^"\\])*")', source)
        for index in range(0, len(parts), 2):
            for original, translated in clipboard.ITALIAN_TO_ENGLISH_TOKENS:
                parts[index] = clipboard._replace_token(parts[index], original, translated)
        self.assertEqual(self.errors("".join(parts)), [])

    def test_arming_must_be_sixty_seconds_and_once_per_connection(self):
        for old, new in (
            (self.arm, self.arm.replace("+ 60", "+ 59")),
            (f"{self.clock} == 0", f"{self.clock} >= 0"),
            (f"And({self.latch} == False, {self.clock} == 0)", f"{self.clock} == 0"),
        ):
            with self.subTest(new=new):
                self.assertTrue(self.errors(self.mutation(old, new)))

    def test_arming_cannot_wait_for_human_classification_or_world_entity(self):
        for condition in (f"{self.player}.Manusia == True", f"Has Spawned({self.player}) == True",
                          f"Entity Exists({self.player}) == True"):
            with self.subTest(condition=condition):
                self.assertTrue(self.errors(self.mutation(
                    self.arm, f"If({condition});\n{self.arm}\nEnd;")))

    def test_force_must_keep_one_hz_bot_and_team_guards(self):
        for old, new in (
            (f"If(Global.LangkahPenjadwal % 20 == ({self.player}.Manusia == True ? "
             f"{self.player}.UrutanHUD : Slot Of({self.player})) % 20);", "If(True);"),
            (f"If(And(Is Dummy Bot({self.player}) == False, {self.player}.BotOtomatis == False));",
             "If(True);"),
            (f"If(Or(Team Of({self.player}) == Team 1, Team Of({self.player}) == Team 2));", "If(True);"),
        ):
            with self.subTest(old=old):
                # The team guard also occurs in arming; mutate its scheduler occurrence.
                scheduler = next(rule for rule in self.rules if rule.name.startswith("04g -"))
                changed = self.mutation(old, new, scheduler.body)
                self.assertTrue(self.errors(self.mutation(scheduler.body, changed)))

    def test_spawned_selection_cancels_before_deadline_assignment(self):
        scheduler = next(rule for rule in self.rules if rule.name.startswith("04g -"))
        changed = self.mutation(f"If(Has Spawned({self.player}) == True);",
                                f"If(Has Spawned({self.player}) == False);", scheduler.body)
        self.assertTrue(self.errors(self.mutation(scheduler.body, changed)))

    def test_force_remains_reachable_before_classification_and_world_spawn(self):
        pattern = re.escape(self.start) + r"\s*" + re.escape(self.stop)
        match = re.search(pattern, self.source)
        self.assertIsNotNone(match)
        for condition in (f"{self.player}.Manusia == True", f"Has Spawned({self.player}) == True",
                          f"Entity Exists({self.player}) == True"):
            with self.subTest(condition=condition):
                changed = self.mutation(match.group(0), f"If({condition});\n{match.group(0)}\nEnd;")
                self.assertTrue(self.errors(changed))

    def test_deadline_cannot_run_early_or_without_positive_arming(self):
        for old, new in ((f"Total Time Elapsed >= {self.clock}", f"Total Time Elapsed <= {self.clock}"),
                         (f"{self.clock} > 0", f"{self.clock} >= 0"),
                         (f"If({self.latch} == False);", "If(True);")):
            with self.subTest(old=old):
                self.assertTrue(self.errors(self.mutation(old, new)))

    def test_latch_is_consumed_before_the_adjacent_force_release_pair(self):
        pattern = (rf"{re.escape(self.latch)} = True;\s*{re.escape(self.clock)} = 0;\s*"
                   rf"{re.escape(self.start)}\s*{re.escape(self.stop)}")
        match = re.search(pattern, self.source)
        self.assertIsNotNone(match)
        changed = self.mutation(match.group(0),
            f"{self.clock} = 0;\n{self.start}\n{self.stop}\n{self.latch} = True;")
        self.assertTrue(self.errors(changed))
        self.assertTrue(self.errors(self.mutation(self.stop, "")))

    def test_default_and_release_target_must_match(self):
        for old, new in ((self.start, self.start.replace("Hero(Shion)", "Hero(Ana)")),
                         (self.stop, "Stop Forcing Player To Be Hero(Host Player);")):
            with self.subTest(new=new):
                self.assertTrue(self.errors(self.mutation(old, new)))

    def test_no_second_force_owner_or_wait_is_added(self):
        for replacement in (self.start + "\nWait(0.016, Ignore Condition);",
                            self.start + "\n" + self.start,
                            "Wait(0.016, Ignore Condition);\n" + self.arm):
            old = self.arm if replacement.endswith(self.arm) else self.start
            with self.subTest(replacement=replacement):
                self.assertTrue(self.errors(self.mutation(old, replacement)))
        changed = self.routine_mutation("ProsesCepatPemain", self.arm,
                                       self.arm + "\n" + self.start + "\n" + self.stop)
        self.assertTrue(self.errors(changed))

    def test_setup_and_cleanup_never_rearm_finished_selection(self):
        for routine, old, new in (
            ("SiapkanPemain", "Event Player.PilihanPahlawanSelesai = True;",
             "Event Player.PilihanPahlawanSelesai = False;"),
            ("SiapkanPemain", "Event Player.WaktuPilihPahlawan = 0;",
             "Event Player.WaktuPilihPahlawan = Total Time Elapsed + 60;"),
            ("TenangkanPemain", "Call Subroutine(TutupMenu);",
             "Call Subroutine(TutupMenu);\nEvent Player.PilihanPahlawanSelesai = False;"),
            ("BersihkanPemain", "Global.PemainPembersihan = Event Player;",
             "Global.PemainPembersihan = Event Player;\n"
             "Set Player Variable(Event Player, PilihanPahlawanSelesai, False);"),
        ):
            with self.subTest(routine=routine, new=new):
                self.assertTrue(self.errors(self.routine_mutation(routine, old, new)))


if __name__ == "__main__":
    unittest.main()
