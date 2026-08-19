#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
TESTS = ROOT / "tests" / "test_validate_workshop.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: atteso 1 match, trovati {count}")
    return text.replace(old, new, 1)


def git_blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


source = SOURCE.read_text(encoding="utf-8")
validator = VALIDATOR.read_text(encoding="utf-8")
tests = TESTS.read_text(encoding="utf-8")

# 1) 04g non deve più fare polling dell'Ultimate Try Your Luck.
old_fast_ultimate = '''\t\tIf(And(Global.PemainAktif.Manusia == True, Entity Exists(Global.PemainAktif)));
\t\t\tIf(And(Global.PemainAktif.EfekNasib == 2, And(Global.PemainAktif.EfekNasibBerakhir > Total Time Elapsed,
\t\t\t\tAnd(Has Spawned(Global.PemainAktif) == True, Is Alive(Global.PemainAktif) == True))));
\t\t\t\tSet Ultimate Charge(Global.PemainAktif, 100);
\t\t\tEnd;
\t\tEnd;
'''
source = replace_once(source, old_fast_ultimate, "", "rimozione Ultimate da 04g")

# 2) Regola globale event-driven: scatta solo quando almeno un player valido scende sotto 100%.
ultimate_rule = '''

rule("18l - Nasib: Ultimate sempre al 100 globale senza polling")
{
\tevent
\t{
\t\tOngoing - Global;
\t}

\tconditions
\t{
\t\tCount Of(Filtered Array(All Players(All Teams), And(Player Variable(Current Array Element, Manusia) == True,
\t\t\tAnd(Player Variable(Current Array Element, EfekNasib) == 2, And(Player Variable(Current Array Element, EfekNasibBerakhir) > Total Time Elapsed,
\t\t\tAnd(Has Spawned(Current Array Element) == True, And(Is Alive(Current Array Element) == True,
\t\t\tUltimate Charge Percent(Current Array Element) < 100))))))) > 0;
\t}

\tactions
\t{
\t\tSet Ultimate Charge(Filtered Array(All Players(All Teams), And(Player Variable(Current Array Element, Manusia) == True,
\t\t\tAnd(Player Variable(Current Array Element, EfekNasib) == 2, And(Player Variable(Current Array Element, EfekNasibBerakhir) > Total Time Elapsed,
\t\t\tAnd(Has Spawned(Current Array Element) == True, And(Is Alive(Current Array Element) == True,
\t\t\tUltimate Charge Percent(Current Array Element) < 100)))))), 100);
\t}
}
'''
source = replace_once(
    source,
    '\nrule("19 - Teleportasi Jongkok: Buka tiga halaman selama Jongkok ditahan")',
    ultimate_rule + '\nrule("19 - Teleportasi Jongkok: Buka tiga halaman selama Jongkok ditahan")',
    "inserimento 18l Ultimate globale",
)

# 3) Validator: 18l fa parte della pipeline e 04g non deve più gestire l'Ultimate.
validator = replace_once(
    validator,
    '    luck_effect_hud = find_rule(rules, "18k - Nasib:")\n    checks.require(luck is not None and luck_death is not None and luck_reopen is not None and luck_expiry is not None and luck_vision_create is not None and luck_vision_cleanup is not None and luck_effect_hud is not None, "pipeline Try Your Luck a dieci risultati assente")',
    '    luck_effect_hud = find_rule(rules, "18k - Nasib:")\n    luck_ultimate_global = find_rule(rules, "18l - Nasib:")\n    checks.require(luck is not None and luck_death is not None and luck_reopen is not None and luck_expiry is not None and luck_vision_create is not None and luck_vision_cleanup is not None and luck_effect_hud is not None and luck_ultimate_global is not None, "pipeline Try Your Luck a dieci risultati assente")',
    "validator pipeline 18l",
)

old_fast_guard = '''    if fast_manager:
        checks.require("Set Ultimate Charge(Global.PemainAktif, 100);" in fast_manager.body, "Ultimate always-ready non è gestita dal manager globale")
        checks.require("Total Time Elapsed >= Global.PemainAktif.EfekNasibBerakhir" not in fast_manager.body, "04g gestisce ancora la scadenza Try Your Luck condivisa")
        checks.require("Set Player Variable(Global.PemainAktif, MenuNasibHarusDibuka, True);" not in fast_manager.body, "04g consegna ancora la riapertura Try Your Luck")
'''
new_fast_guard = '''    if luck_ultimate_global:
        checks.equal(event_type(luck_ultimate_global), "Ongoing - Global", "18l Ultimate sustain: scheduler")
        checks.require(luck_ultimate_global.body.count("Filtered Array(All Players(All Teams)") >= 2, "18l Ultimate sustain non filtra globalmente i player attivi")
        for token in (
            "Player Variable(Current Array Element, Manusia) == True",
            "Player Variable(Current Array Element, EfekNasib) == 2",
            "Player Variable(Current Array Element, EfekNasibBerakhir) > Total Time Elapsed",
            "Has Spawned(Current Array Element) == True",
            "Is Alive(Current Array Element) == True",
            "Ultimate Charge Percent(Current Array Element) < 100",
            "Set Ultimate Charge(Filtered Array(All Players(All Teams)",
        ):
            checks.require(token in luck_ultimate_global.body, f"18l Ultimate sustain incompleto: {token}")
        checks.require("KartuNasibAktif" not in luck_ultimate_global.body, "18l Ultimate sustain non deve dipendere dal lifecycle menu/roulette")
        checks.require("Button(Ultimate)" not in luck_ultimate_global.body, "18l Ultimate sustain non deve dipendere dall input Ultimate")
        checks.require("Wait(" not in luck_ultimate_global.body and "Loop If Condition Is True;" not in luck_ultimate_global.body and "For Global Variable(" not in luck_ultimate_global.body and "For Player Variable(" not in luck_ultimate_global.body, "18l Ultimate sustain deve essere event-driven senza Wait o Loop")
    if fast_manager:
        checks.require("Set Ultimate Charge(" not in fast_manager.body, "04g non deve più gestire Ultimate Try Your Luck")
        checks.require("Total Time Elapsed >= Global.PemainAktif.EfekNasibBerakhir" not in fast_manager.body, "04g gestisce ancora la scadenza Try Your Luck condivisa")
        checks.require("Set Player Variable(Global.PemainAktif, MenuNasibHarusDibuka, True);" not in fast_manager.body, "04g consegna ancora la riapertura Try Your Luck")
'''
validator = replace_once(validator, old_fast_guard, new_fast_guard, "validator Ultimate globale")

# 4) Test di regressione: 18l deve restare globale e senza polling.
test_anchor = '''    def test_periodic_pollers_are_global(self) -> None:
'''
new_test = '''    def test_try_your_luck_ultimate_sustain_is_global_event_driven(self) -> None:
        start = self.source.index('rule("18l - Nasib:')
        pos = self.source.index("Ongoing - Global;", start)
        mutated_scheduler = self.source[:pos] + self.source[pos:].replace("Ongoing - Global;", "Ongoing - Each Player;", 1)
        self.assertTrue(any("18l Ultimate sustain" in error and "scheduler" in error for error in self.errors(mutated_scheduler)))

        actions = self.source.index("\\tactions\\n\\t{", start) + len("\\tactions\\n\\t{")
        mutated_wait = self.source[:actions] + "\\n\\t\\tWait(0.016, Ignore Condition);" + self.source[actions:]
        self.assertTrue(any("18l Ultimate sustain" in error and "senza Wait o Loop" in error for error in self.errors(mutated_wait)))

        fast_start = self.source.index('rule("04g - Global-first:')
        fast_end = self.source.index('rule("04h - Global-first:', fast_start)
        mutated_fast = self.source[:fast_end] + "\\n\\tSet Ultimate Charge(Global.PemainAktif, 100);\\n" + self.source[fast_end:]
        self.assertTrue(any("04g non deve più gestire Ultimate" in error for error in self.errors(mutated_fast)))

'''
tests = replace_once(tests, test_anchor, new_test + test_anchor, "test Ultimate globale")

# Pin del blob sorgente finale.
blob = git_blob_sha(source)
validator, n = re.subn(r'EXPECTED_SOURCE_BLOB = "[0-9a-f]{40}"', f'EXPECTED_SOURCE_BLOB = "{blob}"', validator, count=1)
if n != 1:
    raise RuntimeError("EXPECTED_SOURCE_BLOB non aggiornato")

SOURCE.write_text(source, encoding="utf-8")
VALIDATOR.write_text(validator, encoding="utf-8")
TESTS.write_text(tests, encoding="utf-8")
print(f"patched source blob: {blob}")
