from __future__ import annotations

from pathlib import Path
import subprocess

# Reuse the complete validated transformation from the previous commit, then
# fix the two roster strings before the workflow runs tests/validator.
previous = subprocess.run(
    ["git", "show", "HEAD^:.github/maintenance/patch.py"],
    check=True,
    capture_output=True,
    text=True,
).stdout
exec(compile(previous, "previous-maintenance-patch.py", "exec"), {})

source_path = Path("workshop/ruang_irama.workshop")
src = source_path.read_text(encoding="utf-8")

old_left = '''Custom String("{0} {1} {2} - {3} MIN",\n\t\t\tGlobal.DaftarIkon[Event Player.IndeksIkon], Hero Icon String(Is Duplicating(Event Player) ? Hero Being Duplicated(Event Player) : Hero Of(Event Player)),\n\t\t\tEvent Player, Event Player.MenitLobby)'''
new_left = '''Custom String("{0} {1} {2}",\n\t\t\tGlobal.DaftarIkon[Event Player.IndeksIkon], Hero Icon String(Is Duplicating(Event Player) ? Hero Being Duplicated(Event Player) : Hero Of(Event Player)),\n\t\t\tCustom String("{0} - {1}", Event Player, Event Player.MenitLobby))'''
if src.count(old_left) != 1:
    raise SystemExit(f"left compact roster string: expected 1, found {src.count(old_left)}")
src = src.replace(old_left, new_left, 1)

old_right = '''Custom String("{0} {1} {2} - {3}", Global.DaftarIkon[Event Player.IndeksIkon],\n\t\t\tHero Icon String(Is Duplicating(Event Player) ? Hero Being Duplicated(Event Player) : Hero Of(Event Player)), Event Player,\n\t\t\tEvent Player.IndeksGenre >= 0 ? Global.DaftarGenre[Event Player.IndeksGenre] : Player Variable(Local Player, IndeksBahasa) == 0 ? Custom String("no soundtrack yet")\n\t\t\t: Player Variable(Local Player, IndeksBahasa) == 1 ? Custom String("belum pilih soundtrack") : Custom String("ยังไม่ได้เลือกเพลง"))'''
new_right = '''Custom String("{0} {1} {2}", Global.DaftarIkon[Event Player.IndeksIkon],\n\t\t\tHero Icon String(Is Duplicating(Event Player) ? Hero Being Duplicated(Event Player) : Hero Of(Event Player)), Custom String("{0} - {1}", Event Player,\n\t\t\tEvent Player.IndeksGenre >= 0 ? Global.DaftarGenre[Event Player.IndeksGenre] : Player Variable(Local Player, IndeksBahasa) == 0 ? Custom String("no soundtrack yet")\n\t\t\t: Player Variable(Local Player, IndeksBahasa) == 1 ? Custom String("belum pilih soundtrack") : Custom String("ยังไม่ได้เลือกเพลง")))'''
if src.count(old_right) != 1:
    raise SystemExit(f"right compact roster string: expected 1, found {src.count(old_right)}")
src = src.replace(old_right, new_right, 1)
source_path.write_text(src, encoding="utf-8")

# The previous patch already updated docs/VALIDAZIONE.md. Recompute its source
# blob after this final Workshop-only correction.
import hashlib
import re
report_path = Path("docs/VALIDAZIONE.md")
data = source_path.read_bytes().replace(b"\r\n", b"\n")
blob = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
report = report_path.read_text(encoding="utf-8")
report, n = re.subn(r"```text\n[0-9a-f]{40}\n```", f"```text\n{blob}\n```", report, count=1)
if n != 1:
    raise SystemExit("validation report blob marker not found")
report_path.write_text(report, encoding="utf-8")
