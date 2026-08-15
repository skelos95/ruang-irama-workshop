from __future__ import annotations

import subprocess

script = subprocess.check_output(
    ["git", "show", "e24282c99271c06c9e98a51eb4fddae201b3f29c:.github/maintenance/patch.py"],
    text=True,
)

# Repair the malformed opening branch by replacing that patch section using
# stable section markers.
start = script.index("open_start = block.index(")
end = script.index("\n# Replace the actual apply branch", start)
replacement_lines = [
    "open_start = block.index('\\t\\tIf(Event Player.HalamanMenu == -1);')",
    "open_end = block.index('\\t\\tElse If(Event Player.HalamanMenu == 0);', open_start)",
    "open_branch = '''\\t\\tIf(Event Player.HalamanMenu == -1);",
    "\\t\\t\\tEvent Player.HalamanMenu = Global.KodeMenu[Event Player.KursorUtama];",
    "\\t\\t\\tIf(Event Player.HalamanMenu == 0);",
    "\\t\\t\\t\\tEvent Player.KursorGenre = Event Player.KursorGenre;",
    "\\t\\t\\tElse If(Event Player.HalamanMenu == 1);",
    "\\t\\t\\t\\tCall Subroutine(SegarkanTargetKamera);",
    "\\t\\t\\tElse If(Event Player.HalamanMenu == 2);",
    "\\t\\t\\t\\tEvent Player.KursorWarna = Event Player.KursorWarna;",
    "\\t\\t\\tElse If(Event Player.HalamanMenu == 3);",
    "\\t\\t\\t\\tEvent Player.KursorBahasa = Event Player.KursorBahasa;",
    "\\t\\t\\tElse If(Event Player.HalamanMenu == 4);",
    "\\t\\t\\t\\tEvent Player.KursorBalasDendam = Event Player.KursorBalasDendam;",
    "\\t\\t\\t\\tCall Subroutine(SegarkanTargetBalasDendam);",
    "\\t\\t\\tElse If(Event Player.HalamanMenu == 5);",
    "\\t\\t\\t\\tEvent Player.KursorKebal = Event Player.ModeKebal;",
    "\\t\\t\\tElse If(Event Player.HalamanMenu == 6);",
    "\\t\\t\\t\\tEvent Player.KursorSuara = Event Player.KursorSuara;",
    "\\t\\t\\tElse If(Event Player.HalamanMenu == 7);",
    "\\t\\t\\t\\tEvent Player.KursorIkon = Event Player.KursorIkon;",
    "\\t\\t\\tElse If(Event Player.HalamanMenu == 8);",
    "\\t\\t\\t\\tEvent Player.KursorTeleportasiJongkok = Event Player.KursorTeleportasiJongkok;",
    "\\t\\t\\tElse;",
    "\\t\\t\\t\\tEvent Player.KursorPrivasiInspeksi = Event Player.KursorPrivasiInspeksi;",
    "\\t\\t\\tEnd;",
    "\\t\\t\\tCall Subroutine(GambarMenu);",
    "'''",
    "block = block[:open_start] + open_branch + block[open_end:]",
]
script = script[:start] + "\n".join(replacement_lines) + "\n" + script[end:]

# Target the actual legacy two-state apply branch by its unique old statement.
section = script.index("# Replace the actual apply branch")
locator_start = script.index("apply_start = block.index(", section)
locator_end = script.index("apply_branch = '''", locator_start)
locator_lines = [
    "legacy_apply = block.index('If(Event Player.KebalAktif != And(Event Player.KursorKebal == 1, Is In Spawn Room(Event Player) == False));')",
    "apply_start = block.rfind('\\t\\tElse If(Event Player.HalamanMenu == 5);', 0, legacy_apply)",
    "if apply_start < 0:",
    "    raise SystemExit('outer legacy Menu 5 apply branch not found')",
    "apply_end = block.index('\\t\\tElse If(Event Player.HalamanMenu == 6);', legacy_apply)",
]
script = script[:locator_start] + "\n".join(locator_lines) + "\n" + script[locator_end:]

# Menu 5 is stateful rather than a free preview: opening it must synchronize
# the cursor to ModeKebal so the selected row reflects the actually applied
# exclusive state. Remove the old generic "persistent cursor" prohibition.
validator_marker = 'val = VALIDATOR.read_text(encoding="utf-8")\n'
insert = (
    validator_marker
    + "val = val.replace('        \\\"Event Player.KursorKebal = Event Player.ModeKebal\\\",\\n', '')\n"
)
if validator_marker not in script:
    raise SystemExit("validator read marker not found")
script = script.replace(validator_marker, insert, 1)

exec(compile(script, "final_unkillable_patch.py", "exec"))
