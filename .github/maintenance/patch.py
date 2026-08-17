from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "workshop" / "ruang_irama.workshop"
OUT = ROOT / "exports" / "CHILL_0.7.0_GlobalFirst_menu_fix_candidate.txt"


def find_matching(text: str, opening: int) -> int:
    depth = 1
    in_string = False
    escaped = False
    for i in range(opening + 1, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"': in_string = True
        elif ch == '{': depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0: return i
    raise RuntimeError("unbalanced rule")


def rule_spans(text: str):
    pat = re.compile(r'^rule\("([^"]+)"\)\s*\{', re.M)
    out = []
    for m in pat.finditer(text):
        opening = text.find('{', m.start())
        closing = find_matching(text, opening)
        out.append((m.group(1), m.start(), closing + 1, text[m.start():closing + 1]))
    return out


def section(rule: str, name: str) -> str:
    m = re.search(rf'(?m)^\s*{re.escape(name)}\s*\{{', rule)
    if not m: return ""
    opening = rule.find('{', m.start())
    closing = find_matching(rule, opening)
    return rule[opening + 1:closing]


def split_conditions(body: str) -> list[str]:
    items=[]; start=0; paren=bracket=0; in_string=False; escaped=False
    for i,ch in enumerate(body):
        if in_string:
            if escaped: escaped=False
            elif ch == "\\": escaped=True
            elif ch == '"': in_string=False
            continue
        if ch == '"': in_string=True
        elif ch == '(': paren += 1
        elif ch == ')': paren -= 1
        elif ch == '[': bracket += 1
        elif ch == ']': bracket -= 1
        elif ch == ';' and paren == 0 and bracket == 0:
            item=body[start:i].strip()
            if item and not item.startswith('"'): items.append(item)
            start=i+1
    return items


def indent_block(text: str, tabs: int) -> str:
    p="\t"*tabs
    return "\n".join(p+line.lstrip("\t") for line in text.strip("\n").splitlines() if line.strip())


def make_handler(rule_text: str) -> str:
    if any(t in rule_text for t in ("Wait(","Loop If Condition Is True;","Create HUD Text(","Call Subroutine(")):
        raise RuntimeError("non-atomic handler")
    conds=[x.replace("Event Player","Global.PemainAktif") for x in split_conditions(section(rule_text,"conditions"))]
    actions=section(rule_text,"actions").replace("Event Player","Global.PemainAktif").strip()
    parts=[f"If({c});" for c in conds]+[actions]+["End;" for _ in conds]
    return indent_block("\n".join(parts),2)

src=SRC.read_text(encoding="utf-8")
src=src.replace("\t\t50: ModeMulaiDiminta\n\tplayer:","\t\t50: ModeMulaiDiminta\n\t\t51: PemainAktif\n\t\t52: IndeksPemainGlobal\n\tplayer:",1)
src=src.replace("\t\tGlobal.ModeMulaiDiminta = False;","\t\tGlobal.ModeMulaiDiminta = False;\n\t\tGlobal.PemainAktif = Null;\n\t\tGlobal.IndeksPemainGlobal = 0;",1)

atomic_names=[
"02e - Siklus Pemain: Lepaskan kunci setelah roster baru siap",
"03b - Bot: Tandai kunci untuk dipasang ulang setelah mati atau hilang",
"12d - Kamera: Lepaskan Interact sebelum pakai lagi",
"15 - Intip Pahlawan: Hapus tulisan saat berdiri atau membuka menu",
"18 - Kebal: Pasang kembali status setelah muncul kembali",
"18b - Kebal: Mode 1 HP kembali ke satu saat penuh",
"18d - Kebal: Mode HP PENUH selalu kembali penuh",
"19a - Teleportasi Jongkok: Pengatur masukan terpisah dari Menu Arkade",
"19b - Teleportasi Jongkok: Aktifkan lagi pengatur setelah tombol dilepas",
"19g - Teleportasi Jongkok: Tutup saat Jongkok dilepas"]
spans={n:(a,b,blk) for n,a,b,blk in rule_spans(src)}
if any(n not in spans for n in atomic_names): raise RuntimeError("missing atomic rule")
fast_names=atomic_names[2:]
slow_names=atomic_names[:2]+["15 - Intip Pahlawan: Hapus tulisan saat berdiri atau membuka menu"]
fast_names=[n for n in fast_names if n != "15 - Intip Pahlawan: Hapus tulisan saat berdiri atau membuka menu"]
fast="\n".join(make_handler(spans[n][2]) for n in fast_names)
slow="\n".join(make_handler(spans[n][2]) for n in slow_names)
manager_fast=f'''rule("04g - Global-first: Pengatur status cepat terpusat")
{{
\tevent
\t{{
\t\tOngoing - Global;
\t}}
\tactions
\t{{
\t\tFor Global Variable(IndeksPemainGlobal, 0, Count Of(All Players(All Teams)) - 1, 1);
\t\t\tGlobal.PemainAktif = All Players(All Teams)[Global.IndeksPemainGlobal];
{fast}
\t\tEnd;
\t\tGlobal.PemainAktif = Null;
\t\tWait(0.016, Ignore Condition);
\t\tLoop If Condition Is True;
\t}}
}}

'''
manager_slow=f'''rule("04h - Global-first: Pengatur lifecycle ringan terpusat")
{{
\tevent
\t{{
\t\tOngoing - Global;
\t}}
\tactions
\t{{
\t\tFor Global Variable(IndeksPemainGlobal, 0, Count Of(All Players(All Teams)) - 1, 1);
\t\t\tGlobal.PemainAktif = All Players(All Teams)[Global.IndeksPemainGlobal];
{slow}
\t\tEnd;
\t\tGlobal.PemainAktif = Null;
\t\tWait(0.100, Ignore Condition);
\t\tLoop If Condition Is True;
\t}}
}}

'''
for n,a,b,blk in sorted((x for x in rule_spans(src) if x[0] in atomic_names),key=lambda x:x[1],reverse=True): src=src[:a]+src[b:]
insert_at=src.index('rule("05 - Menu:')
src=src[:insert_at]+manager_fast+manager_slow+src[insert_at:]
if "For Global Variable(Global." in src: raise RuntimeError("bad For syntax")
for n in ("05b - Menu: Lepaskan serangan jarak dekat sebelum pakai lagi","05c - Menu: Pengatur masukan dengan prioritas tetap","05d - Menu: Lepaskan pengatur setelah semua masukan dilepas","06 - Menu: Tembakan utama memilih berikutnya","07 - Menu: Tembakan sekunder memilih sebelumnya","08 - Menu 0: Kemampuan 1 maju sepuluh genre","09 - Menu 0: Kemampuan 2 mundur sepuluh genre","10 - Menu: Interaksi membuka atau menerapkan pilihan","11 - Menu: Muat ulang kembali ke menu utama"):
    blk=next((blk for name,_a,_b,blk in rule_spans(src) if name==n),None)
    if blk is None or "Ongoing - Each Player;" not in blk: raise RuntimeError(f"menu pipeline split: {n}")
if src.count("Ongoing - Each Player;") != 31: raise RuntimeError(f"unexpected each count {src.count('Ongoing - Each Player;')}")
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text("// CHILL 0.7.0 GLOBAL-FIRST MENU-FIX LIVE TEST CANDIDATE\n// Lifecycle/status partially global-first; Arcade Menu pipeline intentionally kept together.\n\n"+src,encoding="utf-8")
print("menu-fix candidate exported")
