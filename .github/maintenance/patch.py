from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "exports" / "CHILL_0.7.0_GlobalFirst_menu_fix_candidate.txt"
OUT = ROOT / "exports" / "CHILL_0.7.0_GlobalFirst_menu_camera_fix_candidate.txt"

text = SRC.read_text(encoding="utf-8")

# In candidate B, rule 12d was moved into the fast Global-first manager.
# Keep camera toggle producer/release in the same Each Player scheduler instead.
global_release = '''\t\tIf(Global.PemainAktif.InteraksiKameraDipakai == True);\n\t\tIf(Is Button Held(Global.PemainAktif, Button(Interact)) == False);\n\t\tGlobal.PemainAktif.InteraksiKameraDipakai = False;\n\t\tEnd;\n\t\tEnd;\n'''
count = text.count(global_release)
if count != 1:
    raise RuntimeError(f"expected one global camera release handler, found {count}")
text = text.replace(global_release, "", 1)

rule_12d = '''rule("12d - Kamera: Lepaskan Interact sebelum pakai lagi")\n{\n\tevent\n\t{\n\t\tOngoing - Each Player;\n\t\tAll;\n\t\tAll;\n\t}\n\n\tconditions\n\t{\n\t\tEvent Player.InteraksiKameraDipakai == True;\n\t\tIs Button Held(Event Player, Button(Interact)) == False;\n\t}\n\n\tactions\n\t{\n\t\tEvent Player.InteraksiKameraDipakai = False;\n\t}\n}\n\n'''
marker = 'rule("12e - Bangkit Lompat: Simpan posisi kematian")'
if marker not in text:
    raise RuntimeError("12e marker missing")
if 'rule("12d - Kamera: Lepaskan Interact sebelum pakai lagi")' in text:
    raise RuntimeError("12d already present")
text = text.replace(marker, rule_12d + marker, 1)

if "Global.PemainAktif.InteraksiKameraDipakai = False;" in text:
    raise RuntimeError("global camera latch release still present")
if text.count('rule("12d - Kamera: Lepaskan Interact sebelum pakai lagi")') != 1:
    raise RuntimeError("12d Each Player restore failed")
if "For Global Variable(Global." in text:
    raise RuntimeError("invalid For Global Variable syntax")

header_old = "// CHILL 0.7.0 GLOBAL-FIRST MENU-FIX LIVE TEST CANDIDATE\n"
header_new = "// CHILL 0.7.0 GLOBAL-FIRST MENU+CAMERA-FIX LIVE TEST CANDIDATE\n"
if header_old not in text:
    raise RuntimeError("candidate header missing")
text = text.replace(header_old, header_new, 1)

OUT.write_text(text, encoding="utf-8")
print("camera latch fix candidate exported")
