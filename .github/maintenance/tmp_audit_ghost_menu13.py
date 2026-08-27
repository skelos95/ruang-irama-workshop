from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from pathlib import Path

from tools import validate_workshop as validator

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.it-IT.workshop"
SEMANTIC = ROOT / "tests" / "fixtures" / "semantic_reference.txt"


def balance_block(text: str, start: int) -> tuple[str, int]:
    brace = text.find("{", start)
    if brace < 0:
        raise RuntimeError("opening brace missing")
    depth = 0
    in_string = False
    esc = False
    for i in range(brace, len(text)):
        ch = text[i]
        if in_string:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1], i + 1
    raise RuntimeError("unbalanced block")


def extract_named_rules(text: str, keyword: str) -> list[tuple[str, str]]:
    out = []
    pat = re.compile(rf'{re.escape(keyword)}\("([^"]+)"\)')
    pos = 0
    while True:
        m = pat.search(text, pos)
        if not m:
            break
        block, end = balance_block(text, m.start())
        out.append((m.group(1), block))
        pos = end
    return out


def parse_vars(text: str):
    start = text.index("variabili\n{")
    end = text.index("\n}\n\nsubroutine", start)
    block = text[start:end]
    global_block = block.split("\tglobale:\n", 1)[1].split("\tgiocatore:\n", 1)[0]
    player_block = block.split("\tgiocatore:\n", 1)[1]
    rx = re.compile(r"^\s*(\d+):\s*([A-Za-z0-9_]+)\s*$", re.M)
    return rx.findall(global_block), rx.findall(player_block)


def usage_counts(text: str, variables, scope: str):
    result = []
    for idx, name in variables:
        if scope == "global":
            patterns = [rf"\bGlobale\.{re.escape(name)}\b", rf"\bGlobal\.{re.escape(name)}\b"]
        else:
            patterns = [
                rf"\bEvent Player\.{re.escape(name)}\b",
                rf"\bGlobale\.[A-Za-z0-9_]+\.{re.escape(name)}\b",
                rf"\bGlobal\.[A-Za-z0-9_]+\.{re.escape(name)}\b",
                rf"Player Variable\([^,]+,\s*{re.escape(name)}\)",
            ]
        count = sum(len(re.findall(p, text)) for p in patterns)
        result.append((count, int(idx), name))
    return sorted(result)


def main():
    src = SOURCE.read_text(encoding="utf-8")
    sem = SEMANTIC.read_text(encoding="utf-8")
    print("=== BASIC ===")
    print("bytes", len(src.encode("utf-8")), "chars", len(src), "lines", src.count("\n") + 1)
    print("semantic bytes", len(sem.encode("utf-8")))
    print("rules it", len(extract_named_rules(src, "regola")), "rules en", len(extract_named_rules(sem, "rule")))
    print("Wait", src.count("Wait("), "Loop", src.count("Loop;"), "HUD", src.count("Create HUD Text("), "IWT", src.count("Create In-World Text("), "Icon", src.count("Create Icon("), "Effect", src.count("Create Effect("))

    rules = extract_named_rules(src, "regola")
    names = [n for n, _ in rules]
    dup_names = [n for n, c in Counter(names).items() if c > 1]
    print("duplicate rule titles", dup_names)

    exact = defaultdict(list)
    for name, body in rules:
        normalized = re.sub(r"\s+", " ", body).strip()
        exact[hashlib.sha256(normalized.encode()).hexdigest()].append(name)
    dup_bodies = [v for v in exact.values() if len(v) > 1]
    print("duplicate exact rule bodies", dup_bodies)

    print("=== TOP RULE SIZES ===")
    for name, body in sorted(rules, key=lambda x: len(x[1].encode("utf-8")), reverse=True)[:15]:
        print(len(body.encode("utf-8")), name)

    gvars, pvars = parse_vars(src)
    print("=== GLOBAL VARIABLE USAGE <= 2 ===")
    for row in usage_counts(src, gvars, "global"):
        if row[0] <= 2:
            print(row)
    print("=== PLAYER VARIABLE USAGE <= 3 ===")
    for row in usage_counts(src, pvars, "player"):
        if row[0] <= 3:
            print(row)

    sub_start = src.index("subroutine\n{")
    sub_end = src.index("\n}\n\nregola", sub_start)
    subs = re.findall(r"^\s*(\d+):\s*([A-Za-z0-9_]+)\s*$", src[sub_start:sub_end], re.M)
    print("=== SUBROUTINE CALL COUNTS ===")
    for idx, name in subs:
        count = src.count(f"Call Subroutine({name});")
        event_count = src.count(f"\n\t\t{name};\n")
        if count <= 1:
            print(idx, name, "calls", count, "event refs", event_count)

    print("=== SELECTED TOKEN COUNTS ===")
    for token in [
        "SegarkanRosterTertunda", "BantalanDinding", "JarakBidik", "SlotHUDTerakhir", "PilihPahlawanDilewati",
        "PersiapanDilewati", "ModeMulaiDiminta", "PindahTimDiproses", "HudPemainDibuat", "HudKiri", "HudKanan",
        "Disable Movement Collision With Environment", "Enable Movement Collision With Environment",
    ]:
        print(token, src.count(token))

    print("=== MENU / GHOST RELEVANT RULES ===")
    keys = (
        "menu utama", "Gambar halaman aktif", "Terapkan halaman", "Menu:", "Siapkan pemain", "Proses status cepat",
        "Pemain: Pisahkan", "Pemain Keluar", "Sakelar", "Ikuti Dummy",
    )
    for name, body in rules:
        if any(k.lower() in name.lower() for k in keys) or "KursorUtama" in body or "HalamanMenu == 12" in body:
            print("\n---", name, "---")
            print(body)

    print("=== VALIDATOR ===")
    report = validator.validate(src)
    print("validator errors", len(report.errors))
    for err in report.errors:
        print("ERROR", err)
    print("validator warnings", len(report.warnings))
    for warning in report.warnings:
        print("WARN", warning)


if __name__ == "__main__":
    main()
