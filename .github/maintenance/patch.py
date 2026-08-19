from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"

OLD_BLOB = "8d7aa48c96e5c39dae693c62d992fa7adf159c48"


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

# Reopening directly on page 10 needs the page renderer too: GambarMenu alone
# only recreates the preloaded main HUD, which is invisible while HalamanMenu == 10.
old_reopen = '''\t\tEvent Player.MenuTerbuka = True;
\t\tEvent Player.HalamanMenu = 10;
\t\tEvent Player.HalamanMenuTujuan = 10;
\t\tCall Subroutine(GambarMenu);
\t\tEvent Player.MenuNasibHarusDibuka = False;
'''
new_reopen = '''\t\tEvent Player.MenuTerbuka = True;
\t\tEvent Player.HalamanMenu = 10;
\t\tEvent Player.HalamanMenuTujuan = 10;
\t\tCall Subroutine(GambarMenu);
\t\tCall Subroutine(GambarNasib);
\t\tEvent Player.MenuNasibHarusDibuka = False;
'''
source = one(source, old_reopen, new_reopen)

# Vision shows native player names/nameplates instead of outlines.
old_vision = '''\t\tElse If(Event Player.EfekNasib == 6);
\t\t\tEvent Player.PrivasiNasibAktif = True;
\t\t\tStart Forcing Player Outlines(All Players(All Teams), Event Player, True, Color(White), Always);
\t\t\tEvent Player.EfekNasibBerakhir = Total Time Elapsed + 15;
'''
new_vision = '''\t\tElse If(Event Player.EfekNasib == 6);
\t\t\tEvent Player.PrivasiNasibAktif = True;
\t\t\tEnable Nameplates(All Players(All Teams), Event Player);
\t\t\tEvent Player.PelatNamaDinonaktifkan = False;
\t\t\tEvent Player.EfekNasibBerakhir = Total Time Elapsed + 15;
'''
source = one(source, old_vision, new_vision)

# Crouch inspection must not hide all names while Vision is active.
old_inspect = '''\t\tIf(Event Player.InspeksiAktif == False);
\t\t\tEvent Player.InspeksiAktif = True;
\t\t\tDisable Nameplates(All Players(All Teams), Event Player);
\t\t\tEvent Player.PelatNamaDinonaktifkan = True;
'''
new_inspect = '''\t\tIf(Event Player.InspeksiAktif == False);
\t\t\tEvent Player.InspeksiAktif = True;
\t\t\tIf(Event Player.PrivasiNasibAktif == False);
\t\t\t\tDisable Nameplates(All Players(All Teams), Event Player);
\t\t\t\tEvent Player.PelatNamaDinonaktifkan = True;
\t\t\tElse;
\t\t\t\tEnable Nameplates(All Players(All Teams), Event Player);
\t\t\t\tEvent Player.PelatNamaDinonaktifkan = False;
\t\t\tEnd;
'''
source = one(source, old_inspect, new_inspect)

# Same rule for the player-target teleport label.
old_tp = '''\t\tIf(Event Player.CalonTargetTeleportasi == Null);
\t\t\tEvent Player.TargetTeleportasiTeks = Null;
\t\t\tAbort;
\t\tEnd;
\t\tDisable Nameplates(All Players(All Teams), Event Player);
\t\tEvent Player.PelatNamaDinonaktifkan = True;
\t\tCreate In-World Text(Event Player, Custom String("{0} {1} | {2}",
'''
new_tp = '''\t\tIf(Event Player.CalonTargetTeleportasi == Null);
\t\t\tEvent Player.TargetTeleportasiTeks = Null;
\t\t\tAbort;
\t\tEnd;
\t\tIf(Event Player.PrivasiNasibAktif == False);
\t\t\tDisable Nameplates(All Players(All Teams), Event Player);
\t\t\tEvent Player.PelatNamaDinonaktifkan = True;
\t\tElse;
\t\t\tEnable Nameplates(All Players(All Teams), Event Player);
\t\t\tEvent Player.PelatNamaDinonaktifkan = False;
\t\tEnd;
\t\tCreate In-World Text(Event Player, Custom String("{0} {1} | {2}",
'''
source = one(source, old_tp, new_tp)

SOURCE.write_text(source, encoding="utf-8")
new_blob = blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = one(validator, f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"', f'EXPECTED_SOURCE_BLOB = "{new_blob}"')
validator = one(
    validator,
    '            "Start Forcing Player Outlines(All Players(All Teams), Event Player, True, Color(White), Always);",\n',
    '            "Enable Nameplates(All Players(All Teams), Event Player);",\n            "Event Player.PelatNamaDinonaktifkan = False;",\n',
)
old_luck_guard = '        checks.require("Event Player.MenuNasibHarusDibuka = True;" in luck.body, "Try Your Luck istantaneo non richiede la riapertura dopo il risultato")\n'
new_luck_guard = old_luck_guard + '        checks.require("Start Forcing Player Outlines(" not in luck.body, "Vision Try Your Luck non deve usare outline")\n'
validator = one(validator, old_luck_guard, new_luck_guard)
old_reopen_guard = '        checks.require("Event Player.HalamanMenu = 10;" in luck_reopen.body and "Call Subroutine(GambarMenu);" in luck_reopen.body, "18g non riapre la pagina Try Your Luck")\n'
new_reopen_guard = old_reopen_guard + '        checks.require("Call Subroutine(GambarNasib);" in luck_reopen.body, "18g riapre lo stato menu ma non rende direttamente HUD Try Your Luck")\n        checks.require(luck_reopen.body.index("Call Subroutine(GambarMenu);") < luck_reopen.body.index("Call Subroutine(GambarNasib);") < luck_reopen.body.index("Event Player.MenuNasibHarusDibuka = False;"), "18g deve renderizzare pagina 10 prima di consumare la riapertura")\n'
validator = one(validator, old_reopen_guard, new_reopen_guard)
old_inspect_guard = '        checks.require("Event Player.TeleportasiJongkokDiaktifkan == False;" in inspect_rule.body, "Inspection generica può vincere il primo frame Crouch")\n'
new_inspect_guard = old_inspect_guard + '        checks.require("If(Event Player.PrivasiNasibAktif == False);" in inspect_rule.body and "Enable Nameplates(All Players(All Teams), Event Player);" in inspect_rule.body, "Vision deve mantenere visibili i nameplate anche durante Crouch Inspection")\n'
validator = one(validator, old_inspect_guard, new_inspect_guard)
VALIDATOR.write_text(validator, encoding="utf-8")

print(f"patched Workshop blob: {new_blob}")
