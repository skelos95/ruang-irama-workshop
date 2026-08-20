#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
ERROR = ROOT / ".github" / "maintenance" / "last-patch-error.txt"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: atteso 1 match, trovati {count}")
    return text.replace(old, new, 1)


def blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


source = SOURCE.read_text(encoding="utf-8")
validator = VALIDATOR.read_text(encoding="utf-8")

start = source.index('rule("18l - Nasib: Burning proporzionale globale a tick")')
end = source.index('\n\nrule("19 - Teleportasi Jongkok:', start)
old_rule = source[start:end]
new_rule = '''rule("18l - Nasib: Burning proporzionale globale a tick")
{
\tevent
\t{
\t\tOngoing - Global;
\t}

\tconditions
\t{
\t\tCount Of(Filtered Array(All Players(All Teams), And(Player Variable(Current Array Element, EfekNasib) == 5,
\t\t\tPlayer Variable(Current Array Element, TickBurnNasib) <= Total Time Elapsed))) > 0;
\t}

\tactions
\t{
\t\tFor Global Variable(IndeksPemainGlobal, 0, Count Of(All Players(All Teams)), 1);
\t\t\tGlobal.PemainAktif = All Players(All Teams)[Global.IndeksPemainGlobal];
\t\t\tIf(Global.PemainAktif.Manusia == True);
\t\t\t\tIf(Global.PemainAktif.EfekNasib == 5);
\t\t\t\t\tIf(Global.PemainAktif.EfekNasibBerakhir > Total Time Elapsed);
\t\t\t\t\t\tIf(Global.PemainAktif.TickBurnNasib <= Total Time Elapsed);
\t\t\t\t\t\t\tIf(Has Spawned(Global.PemainAktif) == True);
\t\t\t\t\t\t\t\tIf(Is Alive(Global.PemainAktif) == True);
\t\t\t\t\t\t\t\t\tDamage(Global.PemainAktif, Null, Max Health(Global.PemainAktif) * 0.025);
\t\t\t\t\t\t\t\t\tSet Player Variable(Global.PemainAktif, TickBurnNasib, Total Time Elapsed + 0.500);
\t\t\t\t\t\t\t\tEnd;
\t\t\t\t\t\t\tEnd;
\t\t\t\t\t\tEnd;
\t\t\t\t\tEnd;
\t\t\t\tEnd;
\t\t\tEnd;
\t\tEnd;
\t\tGlobal.PemainAktif = Null;
\t}
}'''
source = source[:start] + new_rule + source[end:]

validator = replace_once(
    validator,
    '        checks.require("Ongoing - Each Player" not in luck_burn_global.body, "18l Burning non deve diventare Each Player")',
    '        checks.require("Ongoing - Each Player" not in luck_burn_global.body, "18l Burning non deve diventare Each Player")\n        checks.require(luck_burn_global.body.count("(") == luck_burn_global.body.count(")"), "18l Burning contiene parentesi sbilanciate")',
    "guard parentesi Burning",
)

blob = blob_sha(source)
validator, n = re.subn(r'EXPECTED_SOURCE_BLOB = "[0-9a-f]{40}"', f'EXPECTED_SOURCE_BLOB = "{blob}"', validator, count=1)
if n != 1:
    raise RuntimeError("EXPECTED_SOURCE_BLOB non aggiornato")

SOURCE.write_text(source, encoding="utf-8")
VALIDATOR.write_text(validator, encoding="utf-8")
if ERROR.exists():
    ERROR.unlink()
print(f"patched source blob: {blob}")
