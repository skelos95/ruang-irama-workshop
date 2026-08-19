from __future__ import annotations

import hashlib
import re
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
        raise RuntimeError(f"expected one match, found {count}: {old[:160]!r}")
    return text.replace(old, new, 1)


def bounds(text: str, title: str) -> tuple[int, int]:
    start = text.index(f'rule("{title}')
    end = text.find('\nrule("', start + 6)
    return start, len(text) if end < 0 else end


def replace_rule(text: str, title: str, new_block: str) -> str:
    start, end = bounds(text, title)
    return text[:start] + new_block.rstrip() + "\n\n" + text[end:].lstrip("\n")


source = SOURCE.read_text(encoding="utf-8")
if blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch moving target")

# 04g: keep only continuous Ultimate refill. Timer completion moves to 18h.
start, end = bounds(source, "04g - Global-first:")
block = source[start:end]
marker = "\t\tIf(And(Global.PemainAktif.Manusia == True, Entity Exists(Global.PemainAktif)));"
ms = block.index(marker)
me = block.index("\n\t\tGlobal.PemainAktif = Null;", ms)
new_fast = '''\t\tIf(And(Global.PemainAktif.Manusia == True, Entity Exists(Global.PemainAktif)));
\t\t\tIf(And(Global.PemainAktif.KartuNasibAktif == True, Global.PemainAktif.PutaranKartuNasib == 0));
\t\t\t\tIf(And(Global.PemainAktif.EfekNasib == 2, And(Global.PemainAktif.EfekNasibBerakhir > Total Time Elapsed, Is Alive(Global.PemainAktif) == True)));
\t\t\t\t\tSet Ultimate Charge(Global.PemainAktif, 100);
\t\t\t\tEnd;
\t\t\tEnd;
\t\tEnd;'''
block = block[:ms] + new_fast + block[me:]
source = source[:start] + block + source[end:]

# 18f: full reset immediately, then redraw once in death screen after 0.1 s.
start, end = bounds(source, "18f - Nasib:")
block = source[start:end]
tail_start = block.rfind("\t\tIf(Event Player.IkonKebal != Null);")
actions_end = block.rfind("\n\t}\n}")
if tail_start < 0 or actions_end < 0:
    raise RuntimeError("18f tail not found")
new_tail = '''\t\tIf(Event Player.IkonKebal != Null);
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
\t\tCall Subroutine(GambarMenu);'''
block = block[:tail_start] + new_tail + block[actions_end:]
source = source[:start] + block + source[end:]

# 18g: after respawn, force a fresh page-10 redraw and only then consume flag.
reopen_rule = '''rule("18g - Nasib: Riapri menu solo quando la funzione finisce")
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
\t\tEvent Player.MenuNasibHarusDibuka == True;
\t\tEvent Player.KartuNasibAktif == False;
\t\tHas Spawned(Event Player) == True;
\t\tIs Alive(Event Player) == True;
\t}

\tactions
\t{
\t\tCall Subroutine(TutupMenu);
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
\t\tEvent Player.MenuNasibHarusDibuka = False;
\t}
}'''
source = replace_rule(source, "18g - Nasib:", reopen_rule)

expiry_rule = '''rule("18h - Nasib: Scadenza effetti temporanei per player")
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
}'''
insert = source.index('rule("19 - Teleportasi Jongkok:')
source = source[:insert] + expiry_rule + "\n\n" + source[insert:]

SOURCE.write_text(source, encoding="utf-8")
new_blob = blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = re.sub(r'EXPECTED_SOURCE_BLOB = "[0-9a-f]{40}"', f'EXPECTED_SOURCE_BLOB = "{new_blob}"', validator, count=1)
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

tests = TESTS.read_text(encoding="utf-8")
anchor = '    def test_periodic_pollers_are_global(self) -> None:\n'
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
if addition not in tests:
    tests = one(tests, anchor, addition + anchor)
TESTS.write_text(tests, encoding="utf-8")

print(f"Try Your Luck per-player expiry/death redraw: {OLD_BLOB} -> {new_blob}")
