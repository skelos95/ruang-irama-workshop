from __future__ import annotations

from pathlib import Path
import hashlib
import re
import subprocess

# Rebuild the complete feature patch from the original implementation commit.
# HEAD~2 is the first full Player Icon / pastel RGB patch; the intermediate
# wrapper commit only fixed the roster placeholder shape.
base_patch = subprocess.run(
    ["git", "show", "HEAD~2:.github/maintenance/patch.py"],
    check=True,
    capture_output=True,
    text=True,
).stdout
exec(compile(base_patch, "player-icon-pastel-rgb-base.py", "exec"), {})

source_path = Path("workshop/ruang_irama.workshop")
src = source_path.read_text(encoding="utf-8")

# Keep Workshop Custom String placeholders within {0}..{2} and leave only the
# raw time value on the left (no CHILL for / MIN label).
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

# The left player HUD also contains host-only diagnostics. Since its player row
# is now language-neutral, localize only this technical diagnostics expression
# so the visible-text validator still sees complete EN/ID/TH branches without
# adding any label back to the player's time.
old_diag = '''And(Global.DiagnostikPerforma == True, And(Local Player == Host Player, Event Player == Last Of(Sorted Array(\n\t\t\tGlobal.PemainManusia, Player Variable(Current Array Element, UrutanHUD))))) ? Custom String("{0}\\n{1}", Custom String("\\n \\nLOAD {0}% | AVG {1}% | MAX {2}%",\n\t\t\tServer Load, Server Load Average, Server Load Peak), Custom String("HUD {0} | IWT {1}", 3 + Count Of(Global.HudKiriPemain) * 2 + Count Of(Filtered Array(\n\t\t\tGlobal.HudMenuPemain, Current Array Element != 0)), Count Of(Filtered Array(Global.TeksDuniaPemain, Current Array Element != 0)) + Count Of(Filtered Array(\n\t\t\tGlobal.TeksDiriPemain, Current Array Element != 0)))) : Custom String(" ")'''
new_diag = '''And(Global.DiagnostikPerforma == True, And(Local Player == Host Player, Event Player == Last Of(Sorted Array(\n\t\t\tGlobal.PemainManusia, Player Variable(Current Array Element, UrutanHUD))))) ? Player Variable(Local Player, IndeksBahasa) == 2 ? Custom String("{0}\\n{1}",\n\t\t\tCustom String("\\n \\nโหลด {0}% | เฉลี่ย {1}% | สูงสุด {2}%", Server Load, Server Load Average, Server Load Peak), Custom String("HUD {0} | IWT {1}",\n\t\t\t3 + Count Of(Global.HudKiriPemain) * 2 + Count Of(Filtered Array(Global.HudMenuPemain, Current Array Element != 0)), Count Of(Filtered Array(\n\t\t\tGlobal.TeksDuniaPemain, Current Array Element != 0)) + Count Of(Filtered Array(Global.TeksDiriPemain, Current Array Element != 0)))) : Custom String("{0}\\n{1}",\n\t\t\tCustom String("\\n \\nLOAD {0}% | AVG {1}% | MAX {2}%", Server Load, Server Load Average, Server Load Peak), Custom String("HUD {0} | IWT {1}",\n\t\t\t3 + Count Of(Global.HudKiriPemain) * 2 + Count Of(Filtered Array(Global.HudMenuPemain, Current Array Element != 0)), Count Of(Filtered Array(\n\t\t\tGlobal.TeksDuniaPemain, Current Array Element != 0)) + Count Of(Filtered Array(Global.TeksDiriPemain, Current Array Element != 0)))) : Custom String(" ")'''
if src.count(old_diag) != 1:
    raise SystemExit(f"compact diagnostics block: expected 1, found {src.count(old_diag)}")
src = src.replace(old_diag, new_diag, 1)
source_path.write_text(src, encoding="utf-8")

# Keep documentation validation tied to the final Workshop source.
report_path = Path("docs/VALIDAZIONE.md")
data = source_path.read_bytes().replace(b"\r\n", b"\n")
blob = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
report = report_path.read_text(encoding="utf-8")
report, n = re.subn(r"```text\n[0-9a-f]{40}\n```", f"```text\n{blob}\n```", report, count=1)
if n != 1:
    raise SystemExit("validation report blob marker not found")
report_path.write_text(report, encoding="utf-8")
