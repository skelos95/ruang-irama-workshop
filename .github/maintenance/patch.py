from __future__ import annotations

import base64
import gzip
import hashlib
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "exports" / "CHILL_0.7.0_GlobalFirst_menu_fix_candidate.txt"
WORKSHOP = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
TESTS = ROOT / "tests" / "test_validate_workshop.py"
VERSION = ROOT / "VERSION"
README = ROOT / "README.md"
PROGETTO = ROOT / "docs" / "PROGETTO.md"
TESTDOC = ROOT / "docs" / "TEST.md"
VALIDAZIONE = ROOT / "docs" / "VALIDAZIONE.md"
EXPECTED_BLOB = "f0940e494463c99d395e58ac9de0c67f75b61cb3"

DIFF_B64 = "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"

# Rebuild exactly the live-confirmed candidate from the saved menu-fix export.
if not BASE.exists():
    raise RuntimeError("Base candidate export missing")
shutil.copyfile(BASE, WORKSHOP)
patch_bytes = gzip.decompress(base64.b64decode(DIFF_B64))
with tempfile.NamedTemporaryFile("wb", delete=False, suffix=".diff") as fh:
    fh.write(patch_bytes)
    diff_path = Path(fh.name)
try:
    subprocess.run(["git", "apply", "--whitespace=nowarn", str(diff_path)], cwd=ROOT, check=True)
finally:
    diff_path.unlink(missing_ok=True)

# Remove live-test header comments; gameplay body remains byte-for-byte identical.
source = WORKSHOP.read_text(encoding="utf-8")
lines = source.splitlines()
while lines and lines[0].startswith("//"):
    lines.pop(0)
while lines and not lines[0].strip():
    lines.pop(0)
source = "\n".join(lines) + "\n"
WORKSHOP.write_text(source, encoding="utf-8")
raw = source.encode("utf-8")
blob = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
if blob != EXPECTED_BLOB:
    raise RuntimeError(f"Live candidate mismatch: expected {EXPECTED_BLOB}, got {blob}")

VERSION.write_text("0.7.0\n", encoding="utf-8")

VALIDATOR.write_text(r'''#!/usr/bin/env python3
from __future__ import annotations
import re, sys
from dataclasses import dataclass
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CURRENT_VERSION="0.7.0"
SOURCE=ROOT/"workshop"/"ruang_irama.workshop"
VERSION=ROOT/"VERSION"
WORKFLOWS=ROOT/".github"/"workflows"
ALLOWED={"validate-workshop.yml","maintenance-patch.yml"}
@dataclass(frozen=True)
class Rule:
    name:str; body:str; start:int
class Checks:
    def __init__(self): self.errors=[]
    def require(self,ok,msg):
        if not ok:self.errors.append(msg)
    def equal(self,a,b,msg):
        if a!=b:self.errors.append(f"{msg}: atteso {b!r}, trovato {a!r}")
    def finish(self):
        if self.errors:
            print(f"ERRORE - {len(self.errors)} controllo/i non superato/i:",file=sys.stderr)
            for e in self.errors: print(f"  - {e}",file=sys.stderr)
            raise SystemExit(1)
def matching(t,o):
    d=1;s=False;e=False
    for i in range(o+1,len(t)):
        c=t[i]
        if s:
            if e:e=False
            elif c=="\\":e=True
            elif c=='"':s=False
            continue
        if c=='"':s=True
        elif c=='{':d+=1
        elif c=='}':
            d-=1
            if d==0:return i
    raise ValueError("graffa non chiusa")
def rules(t):
    out=[]
    for m in re.finditer(r'^rule\("([^"]+)"\)\s*\{',t,re.M):
        o=t.find('{',m.start());z=matching(t,o);out.append(Rule(m.group(1),t[m.start():z+1],m.start()))
    return out
def by(rs,p):return next((r for r in rs if r.name.startswith(p)),None)
def evt(r):
    m=re.search(r"event\s*\{\s*([^;\n]+);",r.body,re.S);return m.group(1).strip() if m else ""
def declarations(t):
    vm=re.search(r"variables\s*\{(.*?)\}\s*subroutines",t,re.S);sm=re.search(r"subroutines\s*\{(.*?)\}\s*rule\(",t,re.S)
    if not vm or not sm:raise ValueError("declarations assenti")
    g=[];p=[];sec=None
    for line in vm.group(1).splitlines():
        x=line.strip()
        if x=="global:":sec="g";continue
        if x=="player:":sec="p";continue
        m=re.match(r"\d+:\s*([A-Za-z0-9_]+)",x)
        if m:(g if sec=="g" else p).append(m.group(1))
    s=[m.group(1) for m in re.finditer(r"(?m)^\s*\d+:\s*([A-Za-z0-9_]+)",sm.group(1))]
    return g,p,s
def validate(src):
    c=Checks();rs=rules(src);g,p,s=declarations(src)
    c.equal(VERSION.read_text().strip(),CURRENT_VERSION,"VERSION")
    c.equal({x.name for x in WORKFLOWS.glob("*.yml")},ALLOWED,"workflow consentiti")
    c.require(len(rs)>100,"numero regole troppo basso");c.equal(len(rs),len({r.name for r in rs}),"titoli univoci")
    for x in ("PemainAktif","IndeksPemainGlobal"):c.require(x in g,f"global-first {x}")
    for x in ("GambarMenu","GambarHalamanAktif","PramuatSubmenu"):c.require(x in s,f"submenu preload {x}")
    for x in ("HalamanMenuTujuan","HalamanSubmenuPramuat"):c.require(x in p,f"submenu var {x}")
    c.require("For Global Variable(Global." not in src,"For Global Variable(Global.*) non valido")
    mgr=[r for r in rs if r.name.startswith("04g - Global-first") or r.name.startswith("04h - Global-first")];c.equal(len(mgr),2,"manager Global-first")
    for r in mgr:c.equal(evt(r),"Ongoing - Global",r.name);c.require("For Global Variable(IndeksPemainGlobal" in r.body,r.name+" loop")
    for q in ("05b - Menu:","05c - Menu:","05d - Menu:","06 - Menu:","07 - Menu:","08 - Menu 0:","09 - Menu 0:","10 - Menu:","11 - Menu:"):
        r=by(rs,q);c.require(r is not None,"menu "+q);r and c.equal(evt(r),"Ongoing - Each Player","menu "+q)
    for q in ("12c - Kamera:","12d - Kamera:"):
        r=by(rs,q);c.require(r is not None,"camera "+q);r and c.equal(evt(r),"Ongoing - Each Player","camera "+q)
    for q in ("19 - Teleportasi Jongkok:","19a - Teleportasi Jongkok:","19b - Teleportasi Jongkok:","19c - Teleportasi Jongkok:","19d - Teleportasi Jongkok:","19e - Teleportasi Jongkok:","19f - Teleportasi Jongkok:","19g - Teleportasi Jongkok:"):
        r=by(rs,q);c.require(r is not None,"teleport "+q);r and c.equal(evt(r),"Ongoing - Each Player","teleport "+q)
    r10=by(rs,"10 - Menu:");r11=by(rs,"11 - Menu:");pre=by(rs,"91q - SubmenuPreload")
    if r10:c.require("Create HUD Text(" not in r10.body and "Destroy HUD Text(" not in r10.body,"Interact submenu ricrea HUD")
    if r11:c.require("Create HUD Text(" not in r11.body and "Destroy HUD Text(" not in r11.body,"Reload submenu ricrea HUD");c.require("Event Player.HalamanMenu = -1;" in r11.body,"Reload Main")
    c.require(pre is not None,"SubmenuPreload assente")
    if pre:c.require("Count Of(Event Player.HudMenuArcade) > 1" in pre.body,"preload max 2");c.require("Destroy HUD Text(Event Player.HudMenuArcade[1]);" in pre.body,"preload replace submenu")
    c.equal(src.count("Append To Array(Event Player.HudMenuArcade, Event Player.HudMenu)"),13,"renderer HUD")
    c.require("Global.PemainAktif.InteraksiKameraDipakai = False;" not in src,"camera release globale")
    c.require("Global.PemainAktif.PerintahTeleportasi = 1;" not in src,"teleport command globale")
    for r in rs:
        if "Create HUD Text(" in r.body:c.require("Wait(" not in r.body and "Loop If Condition Is True;" not in r.body,r.name+" Create HUD con Wait/Loop")
    c.require("Health(Event Player) >= Max Health(Event Player);" in src,"Unkillable 1 HP")
    c.require("Stop Modifying Hero Voice Lines(Event Player);" in src,"Hero Voice NORMAL")
    c.require("Set Move Speed(Event Player, 0);" in src,"Try Your Luck rosso");c.require("Start Forcing Player Position(Event Player" not in src,"forcing position vietato")
    m=by(rs,"05 - Menu:");m and c.require("Wait(0.500, Abort When False);" in m.body,"Menu hold 0,5")
    m=by(rs,"12c - Kamera:");m and c.require("Wait(0.500, Abort When False);" in m.body,"Camera hold 0,5")
    for r in [x for x in rs if evt(x)=="Player Died"]:c.require("Call Subroutine(TutupMenu);" not in r.body,"morte chiude menu")
    r=by(rs,"12f - Bangkit Lompat:");r and c.require("MenuTerbuka == False" not in r.body,"respawn Jump bloccato con menu")
    j=by(rs,"01 - Pemain Masuk");l=by(rs,"04 - Pemain Keluar");c.require(j is not None and l is not None,"lifecycle join/leave")
    if j:c.require(all(x in j.body for x in ("Call Subroutine(TenangkanPemain);","Call Subroutine(BersihkanPemain);","Call Subroutine(SiapkanPemain);")),"join lifecycle");c.equal(j.body.count("Wait(0.050, Ignore Condition);"),2,"join yield")
    if l:c.require("Call Subroutine(TenangkanPemain);" in l.body and "Call Subroutine(BersihkanPemain);" in l.body,"leave lifecycle")
    return c
def main():
    c=validate(SOURCE.read_text(encoding="utf-8"));c.finish();print("OK - controlli statici v0.7.0 Global-first superati");return 0
if __name__=="__main__":raise SystemExit(main())
''', encoding="utf-8")

TESTS.write_text(r'''from __future__ import annotations
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import validate_workshop as v
class T(unittest.TestCase):
 @classmethod
 def setUpClass(c):c.s=v.SOURCE.read_text(encoding="utf-8")
 def e(c,s):return v.validate(s).errors
 def test_source(c):c.assertEqual(c.e(c.s),[])
 def test_for(c):c.assertTrue(any("For Global Variable" in x for x in c.e(c.s.replace("For Global Variable(IndeksPemainGlobal","For Global Variable(Global.IndeksPemainGlobal",1))))
 def test_mgr(c):c.assertTrue(any("manager Global-first" in x for x in c.e(c.s.replace('rule("04g - Global-first','rule("04x - Global-first',1))))
 def test_menu(c):
  a=c.s.index('rule("05c - Menu:');p=c.s.index("Ongoing - Each Player;",a);s=c.s[:p]+c.s[p:].replace("Ongoing - Each Player;","Ongoing - Global;",1);c.assertTrue(any("menu 05c" in x for x in c.e(s)))
 def test_camera(c):
  a=c.s.index('rule("12d - Kamera:');p=c.s.index("Ongoing - Each Player;",a);s=c.s[:p]+c.s[p:].replace("Ongoing - Each Player;","Ongoing - Global;",1);c.assertTrue(any("camera 12d" in x for x in c.e(s)))
 def test_tp(c):
  a=c.s.index('rule("19a - Teleportasi Jongkok:');p=c.s.index("Ongoing - Each Player;",a);s=c.s[:p]+c.s[p:].replace("Ongoing - Each Player;","Ongoing - Global;",1);c.assertTrue(any("teleport 19a" in x for x in c.e(s)))
 def test_pre(c):c.assertTrue(any("SubmenuPreload" in x for x in c.e(c.s.replace('rule("91q - SubmenuPreload")','rule("91q - X")',1))))
 def test_hp(c):c.assertTrue(any("Unkillable 1 HP" in x for x in c.e(c.s.replace("Health(Event Player) >= Max Health(Event Player);","Health(Event Player) > 1;",1))))
 def test_voice(c):c.assertTrue(any("Hero Voice NORMAL" in x for x in c.e(c.s.replace("Stop Modifying Hero Voice Lines(Event Player);","",1))))
 def test_force(c):c.assertTrue(any("forcing position" in x for x in c.e(c.s+"\nStart Forcing Player Position(Event Player, Position Of(Event Player), False);\n")))
if __name__=="__main__":unittest.main()
''', encoding="utf-8")

# Documentation/current-version cleanup.
for path in (README, PROGETTO, TESTDOC, VALIDAZIONE):
    txt = path.read_text(encoding="utf-8")
    txt = txt.replace("0.6.25", "0.7.0", 1)
    path.write_text(txt, encoding="utf-8")

p = PROGETTO.read_text(encoding="utf-8")
if "## Architettura Global-first 0.7.0" not in p:
    p += "\n\n## Architettura Global-first 0.7.0\n\nDue manager `Ongoing - Global` gestiscono gli handler atomici tramite `Global.PemainAktif`. Menu Arcade, Camera Interact e Teleport Crouch restano intenzionalmente nello stesso scheduler `Ongoing - Each Player` per non separare producer e consumer degli input. Il Menu Arcade conserva al massimo Main + un submenu preselezionato; Interact/Reload cambiano solo visibilità e non ricreano HUD.\n"
PROGETTO.write_text(p, encoding="utf-8")

t = TESTDOC.read_text(encoding="utf-8")
if "## Conferma live 0.7.0" not in t:
    t += "\n\n## Conferma live 0.7.0\n\nConfermati live: cambi team ripetuti senza crash con menu/modifiche attive, Main/submenu fluidi, Camera 1P/3P e Teleport Crouch completi.\n"
TESTDOC.write_text(t, encoding="utf-8")

v = VALIDAZIONE.read_text(encoding="utf-8")
v = re.sub(r"(Blob Git del sorgente Workshop validato:\s*```text\n)[0-9a-f]{40}(\n```)", rf"\g<1>{EXPECTED_BLOB}\g<2>", v, count=1)
if "## Gate Global-first 0.7.0" not in v:
    v += "\n\n## Gate Global-first 0.7.0\n\nIl gate controlla manager globali, pipeline Menu/Camera/Teleport, preload Main + submenu, invarianti HUD e gameplay. Stato: **live-confirmed** per cambio team, Menu Arcade, Camera e Teleport Crouch.\n"
VALIDAZIONE.write_text(v, encoding="utf-8")

# Remove temporary candidate exports. The canonical source is now workshop/ruang_irama.workshop.
exports = ROOT / "exports"
if exports.exists():
    for item in exports.glob("CHILL_0.7.0_*candidate.txt"):
        item.unlink()
    try:
        exports.rmdir()
    except OSError:
        pass

print(f"Promoted CHILL 0.7.0, verified blob {blob}")
