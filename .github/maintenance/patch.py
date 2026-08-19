from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
TESTS = ROOT / "tests" / "test_validate_workshop.py"

OLD_BLOB = "28633af72b6cfc7124949c4d98642e5117937d9b"


def blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def one(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one match, found {count}: {old[:180]!r}")
    return text.replace(old, new, 1)


source = SOURCE.read_text(encoding="utf-8")
if blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch moving target")

# 04g keeps only the continuous Ultimate refill. Expiry itself must no longer
# depend on the shared Global.PemainAktif loop.
old_fast = '''\t\tIf(And(Global.PemainAktif.Manusia == True, Entity Exists(Global.PemainAktif)));
\t\t\tIf(And(Global.PemainAktif.KartuNasibAktif == True, Global.PemainAktif.PutaranKartuNasib == 0));
\t\t\t\tIf(And(Global.PemainAktif.EfekNasib == 2, And(Global.PemainAktif.EfekNasibBerakhir > Total Time Elapsed, Is Alive(Global.PemainAktif) == True)));
\t\t\t\t\tSet Ultimate Charge(Global.PemainAktif, 100);
\t\t\t\tEnd;
\t\t\t\tIf(And(Global.PemainAktif.EfekNasibBerakhir > 0, Total Time Elapsed >= Global.PemainAktif.EfekNasibBerakhir));
\t\t\t\t\tIf(Global.PemainAktif.EfekNasib == 1);
\t\t\t\t\t\tClear Status(Global.PemainAktif, Hacked);
\t\t\t\t\tElse If(Global.PemainAktif.EfekNasib == 2);
\t\t\t\t\t\tSet Ultimate Charge(Global.PemainAktif, Global.PemainAktif.HasilNasibTerkunci);
\t\t\t\t\tElse If(Global.PemainAktif.EfekNasib == 4);
\t\t\t\t\t\tSet Move Speed(Global.PemainAktif, 100);
\t\t\t\t\t\tSet Jump Vertical Speed(Global.PemainAktif, 100);
\t\t\t\t\t\tSet Projectile Speed(Global.PemainAktif, 100);
\t\t\t\t\tElse If(Global.PemainAktif.EfekNasib == 5);
\t\t\t\t\t\tSet Gravity(Global.PemainAktif, 100);
\t\t\t\t\t\tSet Projectile Speed(Global.PemainAktif, 100);
\t\t\t\t\tElse If(Global.PemainAktif.EfekNasib == 6);
\t\t\t\t\t\tStop Forcing Player Outlines(All Players(All Teams), Global.PemainAktif);
\t\t\t\t\t\tSet Player Variable(Global.PemainAktif, PrivasiNasibAktif, False);
\t\t\t\t\tElse If(Global.PemainAktif.EfekNasib == 8);
\t\t\t\t\t\tStop Accelerating(Global.PemainAktif);
\t\t\t\t\t\tSet Move Speed(Global.PemainAktif, 100);
\t\t\t\t\tEnd;
\t\t\t\t\tSet Player Variable(Global.PemainAktif, EfekNasib, 0);
\t\t\t\t\tSet Player Variable(Global.PemainAktif, EfekNasibBerakhir, 0);
\t\t\t\t\tSet Player Variable(Global.PemainAktif, HasilNasibTerkunci, 0);
\t\t\t\t\tSet Player Variable(Global.PemainAktif, KartuNasibAktif, False);
\t\t\t\t\tSet Player Variable(Global.PemainAktif, MenuNasibHarusDibuka, True);
\t\t\t\tEnd;
\t\t\tEnd;
\t\tEnd;'''
new_fast = '''\t\tIf(And(Global.PemainAktif.Manusia == True, Entity Exists(Global.PemainAktif)));
\t\t\tIf(And(Global.PemainAktif.KartuNasibAktif == True, Global.PemainAktif.PutaranKartuNasib == 0));
\t\t\t\tIf(And(Global.PemainAktif.EfekNasib == 2, And(Global.PemainAktif.EfekNasibBerakhir > Total Time Elapsed, Is Alive(Global.PemainAktif) == True)));
\t\t\t\t\tSet Ultimate Charge(Global.PemainAktif, 100);
\t\t\t\tEnd;
\t\t\tEnd;
\t\tEnd;'''
source = one(source, old_fast, new_fast)

# Death reset is immediate. Then draw once in the death screen after the
# transition settles; keep MenuNasibHarusDibuka pending so respawn redraws it.
old_death_tail = '''\t\tIf(Event Player.IkonKebal != Null);
\t\t\tDestroy Icon(Event Player.IkonKebal);
\t\t\tEvent Player.IkonKebal = Null;
\t\tEnd;
\t\tIf(And(Event Player.MenuTerbuka == True, Event Player.HalamanMenu == 10));
\t\t\tCall Subroutine(GambarMenu);
\t\tEnd;
\t}
}'''
new_death_tail = '''\t\tIf(Event Player.IkonKebal != Null);
\t\t\tDestroy Icon(Event Player.IkonKebal);
\t\t\tEvent Player.IkonKebal = Null;
\t\tEnd;
\t\tWait(0.100, Ignore Condition);
\t\tEvent Player.InputMenuDikunci = False;
\t\tEvent Player.PerintahMenu = 0;
\t\tAllow Button(Event Player, Button(Primary Fire));
\t\tAllow Button(Event Player, Button(Secondary Fire));
\t\tAllow Button(Event Player, Button(Interact));
\t\tAllow Button(Event Player, Button(Reload));
\t\tAllow Button(Event Player, Button(Ability 1));
\t\tAllow Button(Event Player, Button(Ability 2));
\t\tAllow Button(Event Player, Button(Ultimate));
\t\tEvent Player.MenuTerbuka = True;
\t\tEvent Player.HalamanMenu = 10;
\t\tEvent Player.HalamanMenuTujuan = 10;
\t\tCall Subroutine(GambarMenu);
\t}
}'''
# Scope this replacement specifically to the 18f block by slicing.
start = source.index('rule("18f - Nasib:')
end = source.index('\n\n\nrule("18g - Nasib:', start)
death = source[start:end]
if old_death_tail not in death:
    raise RuntimeError("18f death tail marker mismatch")
death = death.replace(old_death_tail, new_death_tail, 1)
source = source[:start] + death + source[end:]

# Respawn redraw must be fresh: destroy the death-screen HUD first, then render
# page 10 again and consume the one-shot only after GambarMenu is called.
old_reopen_actions = '''\t\tactions
\t{
\t\tEvent Player.MenuNasibHarusDibuka = False;
\t\tEvent Player.InputMenuDikunci = False;
\t\tEvent Player.PerintahMenu = 0;'''
new_reopen_actions = '''\t\tactions
\t{
\t\tCall Subroutine(TutupMenu);
\t\tEvent Player.InputMenuDikunci = False;
\t\tEvent Player.PerintahMenu = 0;'''
start = source.index('rule("18g - Nasib:')
end = source.index('\nrule("19 - Teleportasi Jongkok:', start)
reopen = source[start:end]
if old_reopen_actions not in reopen:
    raise RuntimeError("18g action marker mismatch")
reopen = reopen.replace(old_reopen_actions, new_reopen_actions, 1)
old_reopen_tail = '''\t\tEvent Player.HalamanMenu = 10;
\t\tEvent Player.HalamanMenuTujuan = 10;
\t\tCall Subroutine(GambarMenu);
\t}
}'''
new_reopen_tail = '''\t\tEvent Player.HalamanMenu = 10;
\t\tEvent Player.HalamanMenuTujuan = 10;
\t\tCall Subroutine(GambarMenu);
\t\tEvent Player.MenuNasibHarusDibuka = False;
\t}
}'''
if old_reopen_tail not in reopen:
    raise RuntimeError("18g tail marker mismatch")
reopen = reopen.replace(old_reopen_tail, new_reopen_tail, 1)
source = source[:start] + reopen + source[end:]

# Per-player, event-driven expiry. Generic restoration deliberately resets every
# temporary Try Your Luck modifier, so one missing branch cannot leave an effect.
expiry_rule = '''

rule("18h - Nasib: Scadenza effetti temporanei per player")
{
\tevent
\t{
\t\tOngoing - Each Player;
\t\tAll;
\t\tAll;
\t}

\tconditions
\t{
\t\tEvent Player.Manusia == True;
\t\tEvent Player.KartuNasibAktif == True;
\t\tEvent Player.PutaranKartuNasib == 0;
\t\tEvent Player.EfekNasibBerakhir > 0;
\t\tTotal Time Elapsed >= Event Player.EfekNasibBerakhir;
\t}

\tactions
\t{
\t\tIf(Event Player.EfekNasib == 2);
\t\t\tSet Ultimate Charge(Event Player, Event Player.HasilNasibTerkunci);
\t\tEnd;
\t\tClear Status(Event Player, Hacked);
\t\tStop Accelerating(Event Player);
\t\tStop Forcing Player Outlines(All Players(All Teams), Event Player);
\t\tEnable Movement Collision With Environment(Event Player);
\t\tSet Move Speed(Event Player, 100);
\t\tSet Jump Vertical Speed(Event Player, 100);
\t\tSet Projectile Speed(Event Player, 100);
\t\tSet Gravity(Event Player, 100);
\t\tEvent Player.PrivasiNasibAktif = False;
\t\tEvent Player.EfekNasib = 0;
\t\tEvent Player.EfekNasibBerakhir = 0;
\t\tEvent Player.HasilNasibTerkunci = 0;
\t\tEvent Player.KartuNasibAktif = False;
\t\tEvent Player.MenuNasibHarusDibuka = True;
\t}
}
'''
insert = source.index('\nrule("19 - Teleportasi Jongkok:', source.index('rule("18g - Nasib:'))
source = source[:insert] + expiry_rule + source[insert:]

SOURCE.write_text(source, encoding="utf-8")
new_blob = blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = one(validator, f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"', f'EXPECTED_SOURCE_BLOB = "{new_blob}"')

validator = one(
    validator,
    '    luck_reopen = find_rule(rules, "18g - Nasib:")\n    checks.require(luck is not None and luck_death is not None and luck_reopen is not None, "pipeline Try Your Luck a dieci risultati assente")',
    '    luck_reopen = find_rule(rules, "18g - Nasib:")\n    luck_expiry = find_rule(rules, "18h - Nasib:")\n    checks.require(luck is not None and luck_death is not None and luck_reopen is not None and luck_expiry is not None, "pipeline Try Your Luck a dieci risultati assente")',
)

validator = one(
    validator,
    '        checks.require("Event Player.PutaranKartuNasib > 0" in luck_death.body and "Event Player.EfekNasib != 0" in luck_death.body, "reset morte Try Your Luck non copre roulette ed effetto")\n',
    '        checks.require("Event Player.PutaranKartuNasib > 0" in luck_death.body and "Event Player.EfekNasib != 0" in luck_death.body, "reset morte Try Your Luck non copre roulette ed effetto")\n'
    '        checks.require("Wait(0.100, Ignore Condition);" in luck_death.body, "morte Try Your Luck non attende la transizione HUD prima del redraw")\n'
    '        checks.require("Event Player.HalamanMenu = 10;" in luck_death.body and "Call Subroutine(GambarMenu);" in luck_death.body, "morte Try Your Luck non ridisegna il menu nella death screen")\n',
)

validator = one(
    validator,
    '        checks.require("Event Player.InputMenuDikunci = False;" in luck_reopen.body, "18g non libera il latch input del menu")\n',
    '        checks.require("Event Player.InputMenuDikunci = False;" in luck_reopen.body, "18g non libera il latch input del menu")\n'
    '        checks.require("Call Subroutine(TutupMenu);" in luck_reopen.body, "18g non forza un redraw fresco al respawn")\n'
    '        checks.require(luck_reopen.body.index("Call Subroutine(GambarMenu);") < luck_reopen.body.index("Event Player.MenuNasibHarusDibuka = False;"), "18g consuma la riapertura prima del redraw")\n',
)

old_fast_checks = '''    if fast_manager:
        checks.require("Set Ultimate Charge(Global.PemainAktif, 100);" in fast_manager.body, "Ultimate always-ready non è gestita dal manager globale")
        checks.require("Global.PemainAktif.EfekNasibBerakhir" in fast_manager.body, "timer Try Your Luck non è Global-first")
        checks.require("Set Player Variable(Global.PemainAktif, MenuNasibHarusDibuka, True);" in fast_manager.body, "scadenza Try Your Luck non consegna la riapertura al player")'''
new_fast_checks = '''    if luck_expiry:
        checks.equal(event_type(luck_expiry), "Ongoing - Each Player", "18h scadenza Try Your Luck: scheduler")
        checks.require("Event Player.EfekNasibBerakhir > 0;" in luck_expiry.body and "Total Time Elapsed >= Event Player.EfekNasibBerakhir;" in luck_expiry.body, "18h non scade sul timestamp per-player")
        checks.require("Wait(" not in luck_expiry.body and "Loop If Condition Is True;" not in luck_expiry.body, "18h scadenza Try Your Luck non deve usare Wait o Loop")
        for token in (
            "Clear Status(Event Player, Hacked);",
            "Stop Accelerating(Event Player);",
            "Stop Forcing Player Outlines(All Players(All Teams), Event Player);",
            "Enable Movement Collision With Environment(Event Player);",
            "Set Move Speed(Event Player, 100);",
            "Set Jump Vertical Speed(Event Player, 100);",
            "Set Projectile Speed(Event Player, 100);",
            "Set Gravity(Event Player, 100);",
            "Event Player.PrivasiNasibAktif = False;",
            "Event Player.KartuNasibAktif = False;",
            "Event Player.MenuNasibHarusDibuka = True;",
        ):
            checks.require(token in luck_expiry.body, f"18h reset scadenza incompleto: {token}")
    if fast_manager:
        checks.require("Set Ultimate Charge(Global.PemainAktif, 100);" in fast_manager.body, "Ultimate always-ready non è gestita dal manager globale")
        checks.require("Total Time Elapsed >= Global.PemainAktif.EfekNasibBerakhir" not in fast_manager.body, "04g gestisce ancora la scadenza Try Your Luck condivisa")
        checks.require("Set Player Variable(Global.PemainAktif, MenuNasibHarusDibuka, True);" not in fast_manager.body, "04g consegna ancora la riapertura Try Your Luck")'''
validator = one(validator, old_fast_checks, new_fast_checks)
VALIDATOR.write_text(validator, encoding="utf-8")

# Update the existing respawn guard test and add a dedicated expiry ownership test.
tests = TESTS.read_text(encoding="utf-8")
anchor = '''    def test_periodic_pollers_are_global(self) -> None:
'''
addition = '''    def test_try_your_luck_expiry_is_per_player(self) -> None:
        start = self.source.index('rule("18h - Nasib:')
        pos = self.source.index("Ongoing - Each Player;", start)
        mutated = self.source[:pos] + self.source[pos:].replace("Ongoing - Each Player;", "Ongoing - Global;", 1)
        self.assertTrue(any("18h scadenza Try Your Luck" in error for error in self.errors(mutated)))

    def test_try_your_luck_death_redraw_is_required(self) -> None:
        start = self.source.index('rule("18f - Nasib:')
        pos = self.source.index("Wait(0.100, Ignore Condition);", start)
        mutated = self.source[:pos] + self.source[pos:].replace("Wait(0.100, Ignore Condition);", "Wait(0.200, Ignore Condition);", 1)
        self.assertTrue(any("death screen" in error or "transizione HUD" in error for error in self.errors(mutated)))

'''
if anchor not in tests:
    raise RuntimeError("tests insertion anchor missing")
tests = tests.replace(anchor, addition + anchor, 1)
TESTS.write_text(tests, encoding="utf-8")

print(f"Try Your Luck expiry/death lifecycle: {OLD_BLOB} -> {new_blob}")
