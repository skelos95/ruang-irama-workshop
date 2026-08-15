from __future__ import annotations

import subprocess

script = subprocess.check_output(
    ["git", "show", "e24282c99271c06c9e98a51eb4fddae201b3f29c:.github/maintenance/patch.py"],
    text=True,
)

old = r"""open_start = block.index('\\t\\t\\tElse If(Event Player.HalamanMenu == 5);')
open_end = block.index('\\t\\t\\tElse If(Event Player.HalamanMenu == 6);', open_start)
open_branch = '''\\t\\t\\tElse If(Event Player.HalamanMenu == 5);
\\t\\t\\t\\tEvent Player.KursorKebal = Event Player.ModeKebal;
'''
block = block[:open_start] + open_branch + block[open_end:]
"""
new = r"""open_start = block.index('\\t\\tIf(Event Player.HalamanMenu == -1);')
open_end = block.index('\\t\\tElse If(Event Player.HalamanMenu == 0);', open_start)
open_branch = '''\\t\\tIf(Event Player.HalamanMenu == -1);
\\t\\t\\tEvent Player.HalamanMenu = Global.KodeMenu[Event Player.KursorUtama];
\\t\\t\\tIf(Event Player.HalamanMenu == 0);
\\t\\t\\t\\tEvent Player.KursorGenre = Event Player.KursorGenre;
\\t\\t\\tElse If(Event Player.HalamanMenu == 1);
\\t\\t\\t\\tCall Subroutine(SegarkanTargetKamera);
\\t\\t\\tElse If(Event Player.HalamanMenu == 2);
\\t\\t\\t\\tEvent Player.KursorWarna = Event Player.KursorWarna;
\\t\\t\\tElse If(Event Player.HalamanMenu == 3);
\\t\\t\\t\\tEvent Player.KursorBahasa = Event Player.KursorBahasa;
\\t\\t\\tElse If(Event Player.HalamanMenu == 4);
\\t\\t\\t\\tEvent Player.KursorBalasDendam = Event Player.KursorBalasDendam;
\\t\\t\\t\\tCall Subroutine(SegarkanTargetBalasDendam);
\\t\\t\\tElse If(Event Player.HalamanMenu == 5);
\\t\\t\\t\\tEvent Player.KursorKebal = Event Player.ModeKebal;
\\t\\t\\tElse If(Event Player.HalamanMenu == 6);
\\t\\t\\t\\tEvent Player.KursorSuara = Event Player.KursorSuara;
\\t\\t\\tElse If(Event Player.HalamanMenu == 7);
\\t\\t\\t\\tEvent Player.KursorIkon = Event Player.KursorIkon;
\\t\\t\\tElse If(Event Player.HalamanMenu == 8);
\\t\\t\\t\\tEvent Player.KursorTeleportasiJongkok = Event Player.KursorTeleportasiJongkok;
\\t\\t\\tElse;
\\t\\t\\t\\tEvent Player.KursorPrivasiInspeksi = Event Player.KursorPrivasiInspeksi;
\\t\\t\\tEnd;
\\t\\t\\tCall Subroutine(GambarMenu);
'''
block = block[:open_start] + open_branch + block[open_end:]
"""
if old not in script:
    raise SystemExit("fragile opening patch block not found")
script = script.replace(old, new, 1)

old_probe = "apply_start = block.index('\\t\\tElse If(Event Player.HalamanMenu == 5);', open_end - (open_end - open_start))\n"
if old_probe not in script:
    raise SystemExit("legacy apply probe not found")
script = script.replace(old_probe, "apply_start = 0\n", 1)

exec(compile(script, "repaired_unkillable_patch.py", "exec"))
