#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    (ROOT / "workshop" / "ruang_irama.it-IT.workshop", True),
    (ROOT / "tests" / "fixtures" / "semantic_reference.txt", False),
]


def match_brace(text: str, opening: int) -> int:
    depth = 1
    in_string = False
    escaped = False
    for i in range(opening + 1, len(text)):
        c = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                in_string = False
            continue
        if c == '"':
            in_string = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
    raise RuntimeError("unclosed brace")


def rule_span(text: str, name: str, italian: bool) -> tuple[int, int]:
    keyword = "regola" if italian else "rule"
    head = f'{keyword}("{name}")'
    start = text.find(head)
    if start < 0:
        raise RuntimeError(f"rule not found: {name}")
    opening = text.find("{", start)
    end = match_brace(text, opening) + 1
    while end < len(text) and text[end] in "\r\n":
        end += 1
    return start, end


def get_rule(text: str, name: str, italian: bool) -> str:
    a, b = rule_span(text, name, italian)
    return text[a:b]


def replace_rule(text: str, name: str, new_rule: str, italian: bool) -> str:
    a, b = rule_span(text, name, italian)
    return text[:a] + new_rule.rstrip() + "\n\n" + text[b:]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {text.count(old)}")
    return text.replace(old, new, 1)


def event_words(italian: bool) -> tuple[str, str, str, str, str, str]:
    return (
        "regola" if italian else "rule",
        "evento" if italian else "event",
        "condizioni" if italian else "conditions",
        "azioni" if italian else "actions",
        "Tutti" if italian else "All",
        "Globale" if italian else "Global",
    )


def clear_attachment_actions(player: str) -> str:
    return (
        f"\t\tDetach Players({player});\n"
        f"\t\tSet Player Variable({player}, LampiranTeleportasiAktif, False);\n"
        f"\t\tSet Player Variable({player}, TargetLampiranTeleportasi, Null);\n"
        f"\t\tSet Player Variable({player}, PahlawanLampiranSendiri, Null);\n"
        f"\t\tSet Player Variable({player}, PahlawanLampiranTarget, Null);\n"
        f"\t\tAllow Button({player}, Button(Reload));\n"
    )


def navigation_rule(italian: bool) -> str:
    r, ev, co, ac, all_, _ = event_words(italian)
    return f'''{r}("19a - Teleportasi Jongkok: Primary maju, Secondary mundur, Interact jalankan")
{{
\t{ev}
\t{{
\t\tOngoing - Each Player;
\t\t{all_};
\t\t{all_};
\t}}

\t{co}
\t{{
\t\tEvent Player.TeleportasiJongkokAktif == True;
\t\tEvent Player.PerintahTeleportasi == 0;
\t\tIs Button Held(Event Player, Button(Crouch)) == True;
\t\tOr(Or(Is Button Held(Event Player, Button(Primary Fire)), Is Button Held(Event Player, Button(Secondary Fire))), Is Button Held(Event Player, Button(Interact))) == True;
\t}}

\t{ac}
\t{{
\t\tIf(Is Button Held(Event Player, Button(Primary Fire)));
\t\t\tEvent Player.PerintahTeleportasi = 1;
\t\tElse If(Is Button Held(Event Player, Button(Secondary Fire)));
\t\t\tEvent Player.PerintahTeleportasi = 2;
\t\tElse;
\t\t\tEvent Player.PerintahTeleportasi = 3;
\t\tEnd;
\t}}
}}'''


def release_rule(italian: bool) -> str:
    r, ev, co, ac, all_, _ = event_words(italian)
    return f'''{r}("19b - Teleportasi Jongkok: Lepaskan pengunci navigasi dan aksi")
{{
\t{ev}
\t{{
\t\tOngoing - Each Player;
\t\t{all_};
\t\t{all_};
\t}}

\t{co}
\t{{
\t\tEvent Player.TeleportasiJongkokAktif == True;
\t\tEvent Player.PerintahTeleportasi != 0;
\t\tIs Button Held(Event Player, Button(Primary Fire)) == False;
\t\tIs Button Held(Event Player, Button(Secondary Fire)) == False;
\t\tIs Button Held(Event Player, Button(Interact)) == False;
\t}}

\t{ac}
\t{{
\t\tEvent Player.PerintahTeleportasi = 0;
\t}}
}}'''


def page_rule(italian: bool) -> str:
    r, ev, co, ac, all_, _ = event_words(italian)
    return f'''{r}("19c - Teleportasi Jongkok: Primary maju dan Secondary mundur empat halaman")
{{
\t{ev}
\t{{
\t\tOngoing - Each Player;
\t\t{all_};
\t\t{all_};
\t}}

\t{co}
\t{{
\t\tEvent Player.TeleportasiJongkokAktif == True;
\t\tOr(Event Player.PerintahTeleportasi == 1, Event Player.PerintahTeleportasi == 2) == True;
\t}}

\t{ac}
\t{{
\t\tEvent Player.KursorTeleportasi = (Event Player.KursorTeleportasi + (Event Player.PerintahTeleportasi == 1 ? 1 : 3)) % 4;
\t\tIf(And(Event Player.KursorTeleportasi != 2, Event Player.KursorTeleportasi != 3));
\t\t\tEvent Player.CalonTargetTeleportasi = Null;
\t\t\tIf(Event Player.TeksTeleportasi != Null);
\t\t\t\tDestroy In-World Text(Event Player.TeksTeleportasi);
\t\t\tEnd;
\t\t\tEvent Player.TeksTeleportasi = Null;
\t\t\tEvent Player.TargetTeleportasiTeks = Null;
\t\t\tIf(Event Player.PelatNamaDinonaktifkan == True);
\t\t\t\tEnable Nameplates(All Players(All Teams), Event Player);
\t\t\t\tEvent Player.PelatNamaDinonaktifkan = False;
\t\t\tEnd;
\t\tElse;
\t\t\tIf(Event Player.TeksDunia != Null);
\t\t\t\tDestroy In-World Text(Event Player.TeksDunia);
\t\t\tEnd;
\t\t\tIf(Index Of Array Value({event_words(italian)[5]}.PemainManusia, Event Player) >= 0);
\t\t\t\t{event_words(italian)[5]}.TeksDuniaPemain[Index Of Array Value({event_words(italian)[5]}.PemainManusia, Event Player)] = 0;
\t\t\tEnd;
\t\t\tEvent Player.TeksDunia = Null;
\t\t\tEvent Player.TargetInspeksi = Null;
\t\t\tEvent Player.InspeksiAktif = False;
\t\t\tIf(Event Player.TeksTeleportasi != Null);
\t\t\t\tDestroy In-World Text(Event Player.TeksTeleportasi);
\t\t\tEnd;
\t\t\tEvent Player.TeksTeleportasi = Null;
\t\t\tEvent Player.TargetTeleportasiTeks = Null;
\t\t\tCall Subroutine(SegarkanTargetTeleportasi);
\t\tEnd;
\t\tCall Subroutine(GambarTeleportasi);
\t}}
}}'''


def target_text_rule(italian: bool) -> str:
    old_name = "19d - Teleportasi Jongkok: Buat ulang nama saat target berubah"
    rule = get_rule(CURRENT_TEXT, old_name, italian)  # assigned by patch_source
    rule = rule.replace("Event Player.KursorTeleportasi == 2;", "Or(Event Player.KursorTeleportasi == 2, Event Player.KursorTeleportasi == 3) == True;", 1)
    return rule


def execute_rule(italian: bool) -> str:
    r, ev, co, ac, all_, _ = event_words(italian)
    return f'''{r}("19e - Teleportasi Jongkok: Interact menjalankan halaman aktif")
{{
\t{ev}
\t{{
\t\tOngoing - Each Player;
\t\t{all_};
\t\t{all_};
\t}}

\t{co}
\t{{
\t\tEvent Player.TeleportasiJongkokAktif == True;
\t\tEvent Player.PerintahTeleportasi == 3;
\t}}

\t{ac}
\t{{
\t\tEvent Player.JenisTeleportasiTerkunci = Event Player.KursorTeleportasi;
\t\tEvent Player.TargetTeleportasiTerkunci = Null;
\t\tIf(Or(Event Player.JenisTeleportasiTerkunci == 2, Event Player.JenisTeleportasiTerkunci == 3));
\t\t\tCall Subroutine(SegarkanTargetTeleportasi);
\t\t\tEvent Player.TargetTeleportasiTerkunci = Event Player.CalonTargetTeleportasi;
\t\tEnd;
\t\tIf(Event Player.JenisTeleportasiTerkunci == 0);
\t\t\tCall Subroutine(TeleportKeSpawn);
\t\tElse If(Event Player.JenisTeleportasiTerkunci == 1);
\t\t\tCall Subroutine(TeleportKeObjektif);
\t\tElse If(Event Player.JenisTeleportasiTerkunci == 2);
\t\t\tCall Subroutine(TeleportKeTarget);
\t\tElse;
\t\t\tIf(Or(Or(Event Player.TargetTeleportasiTerkunci == Null, Entity Exists(Event Player.TargetTeleportasiTerkunci) == False), Or(Has Spawned(Event Player.TargetTeleportasiTerkunci) == False, Is Alive(Event Player.TargetTeleportasiTerkunci) == False)));
\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Attach target unavailable.") : Event Player.IndeksBahasa == 1 ? Custom String("Target tempel tidak tersedia.") : Custom String("เป้าหมายสำหรับเกาะไม่พร้อมใช้งาน"));
\t\t\tElse If(And(Player Variable(Event Player.TargetTeleportasiTerkunci, LampiranTeleportasiAktif) == True, Player Variable(Event Player.TargetTeleportasiTerkunci, TargetLampiranTeleportasi) == Event Player));
\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Attach refused: that would create a loop.") : Event Player.IndeksBahasa == 1 ? Custom String("Tempel ditolak: itu akan membuat lingkaran.") : Custom String("ไม่สามารถเกาะได้ เพราะจะเกิดวงวน"));
\t\t\tElse;
\t\t\t\tIf(Event Player.LampiranTeleportasiAktif == True);
\t\t\t\t\tDetach Players(Event Player);
\t\t\t\tEnd;
\t\t\t\tEvent Player.TargetLampiranTeleportasi = Event Player.TargetTeleportasiTerkunci;
\t\t\t\tEvent Player.PahlawanLampiranSendiri = Hero Of(Event Player);
\t\t\t\tEvent Player.PahlawanLampiranTarget = Hero Of(Event Player.TargetLampiranTeleportasi);
\t\t\t\tEvent Player.LampiranTeleportasiAktif = True;
\t\t\t\tAttach Players(Event Player, Event Player.TargetLampiranTeleportasi, Vector(0, Y Component Of(Eye Position(Event Player.TargetLampiranTeleportasi)) - Y Component Of(Position Of(Event Player.TargetLampiranTeleportasi)) + 0.750, 0));
\t\t\t\tDisallow Button(Event Player, Button(Reload));
\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Attached above {0}. RELOAD detaches.", Event Player.TargetLampiranTeleportasi) : Event Player.IndeksBahasa == 1 ? Custom String("Menempel di atas {0}. RELOAD untuk lepas.", Event Player.TargetLampiranTeleportasi) : Custom String("เกาะอยู่เหนือ {0} กดรีโหลดเพื่อปล่อย", Event Player.TargetLampiranTeleportasi));
\t\t\tEnd;
\t\tEnd;
\t\tEvent Player.JenisTeleportasiTerkunci = -1;
\t\tEvent Player.TargetTeleportasiTerkunci = Null;
\t}}
}}'''


def detach_reload_rule(italian: bool) -> str:
    r, ev, co, ac, all_, _ = event_words(italian)
    return f'''{r}("19f - Teleportasi Jongkok: Reload melepas lampiran")
{{
\t{ev}
\t{{
\t\tOngoing - Each Player;
\t\t{all_};
\t\t{all_};
\t}}

\t{co}
\t{{
\t\tEvent Player.LampiranTeleportasiAktif == True;
\t\tIs Button Held(Event Player, Button(Reload)) == True;
\t}}

\t{ac}
\t{{
{clear_attachment_actions('Event Player').rstrip()}
\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Detached.") : Event Player.IndeksBahasa == 1 ? Custom String("Sudah lepas.") : Custom String("ปล่อยแล้ว"));
\t}}
}}'''


def invalid_detach_rule(italian: bool) -> str:
    r, ev, co, ac, all_, _ = event_words(italian)
    clear = clear_attachment_actions("Event Player").rstrip()
    return f'''{r}("19h - Teleportasi Jongkok: Lepas lampiran saat state berubah")
{{
\t{ev}
\t{{
\t\tOngoing - Each Player;
\t\t{all_};
\t\t{all_};
\t}}

\t{co}
\t{{
\t\tEvent Player.LampiranTeleportasiAktif == True;
\t}}

\t{ac}
\t{{
\t\tIf(Or(Has Spawned(Event Player) == False, Is Alive(Event Player) == False));
{clear}
\t\t\tAbort;
\t\tEnd;
\t\tIf(Or(Event Player.TargetLampiranTeleportasi == Null, Entity Exists(Event Player.TargetLampiranTeleportasi) == False));
{clear}
\t\t\tAbort;
\t\tEnd;
\t\tIf(Or(Has Spawned(Event Player.TargetLampiranTeleportasi) == False, Is Alive(Event Player.TargetLampiranTeleportasi) == False));
{clear}
\t\t\tAbort;
\t\tEnd;
\t\tIf(Or(Hero Of(Event Player) != Event Player.PahlawanLampiranSendiri, Hero Of(Event Player.TargetLampiranTeleportasi) != Event Player.PahlawanLampiranTarget));
{clear}
\t\t\tAbort;
\t\tEnd;
\t\tIf(And(Player Variable(Event Player.TargetLampiranTeleportasi, Manusia) == True, Player Variable(Event Player.TargetLampiranTeleportasi, PrivasiInspeksiAktif) == True));
{clear}
\t\tEnd;
\t}}
}}'''


def menu_rule(italian: bool) -> str:
    r, ev, _, ac, _, G = event_words(italian)
    return f'''{r}("91g - Subrutin: Gambar menu teleportasi")
{{
\t{ev}
\t{{
\t\tSubroutine;
\t\tGambarTeleportasi;
\t}}

\t{ac}
\t{{
\t\tIf(Event Player.HudMenu != Null);
\t\t\tDestroy HUD Text(Event Player.HudMenu);
\t\tEnd;
\t\tEvent Player.HudMenu = Null;
\t\tIf(Index Of Array Value({G}.PemainManusia, Event Player) >= 0);
\t\t\t{G}.HudMenuPemain[Index Of Array Value({G}.PemainManusia, Event Player)] = 0;
\t\tEnd;
\t\tEvent Player.KursorTeleportasi %= 4;
\t\tCreate HUD Text(Event Player, Null, Event Player.IndeksBahasa == 0 ? Custom String("{{0}}\\n{{1}}", Custom String("{{0}}: next | {{1}}: previous | {{2}}: action", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire)), Input Binding String(Button(Interact))), Custom String("release {{0}}: close | {{1}}: detach", Input Binding String(Button(Crouch)), Input Binding String(Button(Reload)))) : Event Player.IndeksBahasa == 1 ? Custom String("{{0}}\\n{{1}}", Custom String("{{0}}: berikutnya | {{1}}: sebelumnya | {{2}}: aksi", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire)), Input Binding String(Button(Interact))), Custom String("lepas {{0}}: tutup | {{1}}: lepas tempel", Input Binding String(Button(Crouch)), Input Binding String(Button(Reload)))) : Custom String("{{0}}\\n{{1}}", Custom String("{{0}}: ถัดไป | {{1}}: ก่อนหน้า | {{2}}: ใช้งาน", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire)), Input Binding String(Button(Interact))), Custom String("ปล่อย {{0}}: ปิด | {{1}}: ปล่อยตัว", Input Binding String(Button(Crouch)), Input Binding String(Button(Reload)))), Event Player.IndeksBahasa == 0 ? Event Player.KursorTeleportasi == 0 ? Custom String("TELEPORT 1/4\\n> SPAWN ROOM\\nINTERACT: TELEPORT") : Event Player.KursorTeleportasi == 1 ? Custom String("TELEPORT 2/4\\n> OBJECTIVE / FLAG\\nINTERACT: TELEPORT") : Event Player.KursorTeleportasi == 2 ? Custom String("TELEPORT 3/4\\n> PLAYER / BOT\\nTARGET: {{0}}\\nINTERACT: TELEPORT", Event Player.CalonTargetTeleportasi != Null ? Event Player.CalonTargetTeleportasi : Custom String("NO PUBLIC TARGET")) : Custom String("TELEPORT 4/4\\n> ATTACH ABOVE PLAYER / BOT\\nTARGET: {{0}}\\nINTERACT: ATTACH | RELOAD: DETACH", Event Player.CalonTargetTeleportasi != Null ? Event Player.CalonTargetTeleportasi : Custom String("NO PUBLIC TARGET")) : Event Player.IndeksBahasa == 1 ? Event Player.KursorTeleportasi == 0 ? Custom String("TELEPORT 1/4\\n> RUANG MUNCUL\\nINTERACT: TELEPORT") : Event Player.KursorTeleportasi == 1 ? Custom String("TELEPORT 2/4\\n> OBJEKTIF / BENDERA\\nINTERACT: TELEPORT") : Event Player.KursorTeleportasi == 2 ? Custom String("TELEPORT 3/4\\n> PLAYER / BOT\\nTARGET: {{0}}\\nINTERACT: TELEPORT", Event Player.CalonTargetTeleportasi != Null ? Event Player.CalonTargetTeleportasi : Custom String("TIDAK ADA TARGET PUBLIK")) : Custom String("TELEPORT 4/4\\n> TEMPEL DI ATAS PLAYER / BOT\\nTARGET: {{0}}\\nINTERACT: TEMPEL | RELOAD: LEPAS", Event Player.CalonTargetTeleportasi != Null ? Event Player.CalonTargetTeleportasi : Custom String("TIDAK ADA TARGET PUBLIK")) : Event Player.KursorTeleportasi == 0 ? Custom String("เทเลพอร์ต 1/4\\n> ห้องเกิด\\nใช้งาน: เทเลพอร์ต") : Event Player.KursorTeleportasi == 1 ? Custom String("เทเลพอร์ต 2/4\\n> เป้าหมาย / ธง\\nใช้งาน: เทเลพอร์ต") : Event Player.KursorTeleportasi == 2 ? Custom String("เทเลพอร์ต 3/4\\n> ผู้เล่น / บอต\\nเป้าหมาย: {{0}}\\nใช้งาน: เทเลพอร์ต", Event Player.CalonTargetTeleportasi != Null ? Event Player.CalonTargetTeleportasi : Custom String("ไม่มีเป้าหมายสาธารณะ")) : Custom String("เทเลพอร์ต 4/4\\n> เกาะเหนือผู้เล่น / บอต\\nเป้าหมาย: {{0}}\\nใช้งาน: เกาะ | รีโหลด: ปล่อย", Event Player.CalonTargetTeleportasi != Null ? Event Player.CalonTargetTeleportasi : Custom String("ไม่มีเป้าหมายสาธารณะ")), Top, 3, Custom Color(255, 255, 255, 255), Custom Color(205, 255, 225, 255), Custom Color(80, 255, 160, 255), Visible To and String, Visible Never);
\t\tEvent Player.HudMenu = Last Text ID;
\t\tIf(Index Of Array Value({G}.PemainManusia, Event Player) >= 0);
\t\t\t{G}.HudMenuPemain[Index Of Array Value({G}.PemainManusia, Event Player)] = Event Player.HudMenu;
\t\tEnd;
\t}}
}}'''


def patch_source(text: str, italian: bool) -> str:
    global CURRENT_TEXT
    CURRENT_TEXT = text
    _, _, _, _, _, G = event_words(italian)

    decl = "\t\t98: PosisiTeleportTujuan\n"
    decl_new = decl + (
        "\t\t99: TargetLampiranTeleportasi\n"
        "\t\t100: LampiranTeleportasiAktif\n"
        "\t\t101: PahlawanLampiranSendiri\n"
        "\t\t102: PahlawanLampiranTarget\n"
    )
    text = replace_once(text, decl, decl_new, "attachment declarations")

    open_old = "19 - Teleportasi Jongkok: Buka tiga halaman selama Jongkok ditahan"
    open_new = "19 - Teleportasi Jongkok: Buka empat halaman selama Jongkok ditahan"
    text = text.replace(f'("{open_old}")', f'("{open_new}")', 1)

    CURRENT_TEXT = text
    text = replace_rule(text, "19a - Teleportasi Jongkok: Primary berpindah, Secondary mengganti halaman", navigation_rule(italian), italian)
    text = replace_rule(text, "19b - Teleportasi Jongkok: Lepaskan pengunci Primary dan Secondary", release_rule(italian), italian)
    text = replace_rule(text, "19c - Teleportasi Jongkok: Secondary Fire mengganti tiga halaman", page_rule(italian), italian)
    CURRENT_TEXT = text
    text = replace_rule(text, "19d - Teleportasi Jongkok: Buat ulang nama saat target berubah", target_text_rule(italian), italian)
    text = replace_rule(text, "19e - Teleportasi Jongkok: Primary Fire menjalankan halaman aktif", execute_rule(italian), italian)

    insert_at, _ = rule_span(text, "19g - Teleportasi Jongkok: Tutup saat Jongkok dilepas", italian)
    text = text[:insert_at] + detach_reload_rule(italian) + "\n\n" + invalid_detach_rule(italian) + "\n\n" + text[insert_at:]

    text = replace_rule(text, "91g - Subrutin: Gambar menu teleportasi", menu_rule(italian), italian)

    scheduler = get_rule(text, "89b - Subrutin: Proses siklus pemain 10 Hz", italian)
    scheduler_old = f"If(And({G}.PemainAktif.TeleportasiJongkokAktif == True, And({G}.PemainAktif.KursorTeleportasi == 2, Is Button Held({G}.PemainAktif, Button(Crouch)) == True)));"
    scheduler_new = f"If(And({G}.PemainAktif.TeleportasiJongkokAktif == True, And(Or({G}.PemainAktif.KursorTeleportasi == 2, {G}.PemainAktif.KursorTeleportasi == 3), Is Button Held({G}.PemainAktif, Button(Crouch)) == True)));"
    scheduler = replace_once(scheduler, scheduler_old, scheduler_new, "scheduler target pages")
    inspect_old = f"And({G}.PemainAktif.TeleportasiJongkokAktif == True, {G}.PemainAktif.KursorTeleportasi != 2)"
    inspect_new = f"And({G}.PemainAktif.TeleportasiJongkokAktif == True, And({G}.PemainAktif.KursorTeleportasi != 2, {G}.PemainAktif.KursorTeleportasi != 3))"
    scheduler = replace_once(scheduler, inspect_old, inspect_new, "inspection close target pages")
    text = replace_rule(text, "89b - Subrutin: Proses siklus pemain 10 Hz", scheduler, italian)

    setup = get_rule(text, "94 - Subrutin: Siapkan pemain dari ujung rambut sampai variabel", italian)
    setup_anchor = "\t\tEvent Player.PosisiTeleportTujuan = Vector(0, 0, 0);\n"
    setup_insert = setup_anchor + (
        "\t\tEvent Player.TargetLampiranTeleportasi = Null;\n"
        "\t\tEvent Player.LampiranTeleportasiAktif = False;\n"
        "\t\tEvent Player.PahlawanLampiranSendiri = Null;\n"
        "\t\tEvent Player.PahlawanLampiranTarget = Null;\n"
    )
    setup = replace_once(setup, setup_anchor, setup_insert, "setup attachment state")
    text = replace_rule(text, "94 - Subrutin: Siapkan pemain dari ujung rambut sampai variabel", setup, italian)

    cleanup = get_rule(text, "93c - Subrutin: Bersihkan pemain saat keluar atau pindah tim", italian)
    cleanup_anchor = "\t\tStop Camera(Event Player);\n"
    cleanup_self = cleanup_anchor + (
        "\t\tDetach Players(Event Player);\n"
        "\t\tEvent Player.LampiranTeleportasiAktif = False;\n"
        "\t\tEvent Player.TargetLampiranTeleportasi = Null;\n"
        "\t\tEvent Player.PahlawanLampiranSendiri = Null;\n"
        "\t\tEvent Player.PahlawanLampiranTarget = Null;\n"
    )
    cleanup = replace_once(cleanup, cleanup_anchor, cleanup_self, "cleanup self attachment")
    loop_anchor = f"\t\tFor Global Variable(IndeksPembersihan, 0, Count Of({G}.PemainManusia), 1);\n"
    loop_insert = loop_anchor + (
        f"\t\t\tIf(Player Variable({G}.PemainManusia[{G}.IndeksPembersihan], TargetLampiranTeleportasi) == {G}.PemainPembersihan);\n"
        f"\t\t\t\tDetach Players({G}.PemainManusia[{G}.IndeksPembersihan]);\n"
        f"\t\t\t\tSet Player Variable({G}.PemainManusia[{G}.IndeksPembersihan], LampiranTeleportasiAktif, False);\n"
        f"\t\t\t\tSet Player Variable({G}.PemainManusia[{G}.IndeksPembersihan], TargetLampiranTeleportasi, Null);\n"
        f"\t\t\t\tSet Player Variable({G}.PemainManusia[{G}.IndeksPembersihan], PahlawanLampiranSendiri, Null);\n"
        f"\t\t\t\tSet Player Variable({G}.PemainManusia[{G}.IndeksPembersihan], PahlawanLampiranTarget, Null);\n"
        f"\t\t\t\tAllow Button({G}.PemainManusia[{G}.IndeksPembersihan], Button(Reload));\n"
        f"\t\t\tEnd;\n"
    )
    cleanup = replace_once(cleanup, loop_anchor, loop_insert, "cleanup dependent attachments")
    text = replace_rule(text, "93c - Subrutin: Bersihkan pemain saat keluar atau pindah tim", cleanup, italian)

    return text


CURRENT_TEXT = ""
for path, italian in SOURCES:
    original = path.read_text(encoding="utf-8")
    patched = patch_source(original, italian)
    path.write_text(patched, encoding="utf-8")

# Fix the stale negative-test expectation that caused the red X on the prior main commit.
test_path = ROOT / "tests" / "test_validate_workshop.py"
test = test_path.read_text(encoding="utf-8")
test = replace_once(
    test,
    'self.assert_rejected(mutated, "cache target dummy: filtro deve essere l\'umano nemico vivo opt-in")',
    'self.assert_rejected(mutated, "cache target dummy deve filtrare gli umani opt-in una sola volta per ciclo")',
    "stale dummy cache error expectation",
)
test_path.write_text(test, encoding="utf-8")

# Add focused behavior tests without depending on fragile line numbers.
runtime_path = ROOT / "tests" / "test_runtime_maintenance.py"
runtime = runtime_path.read_text(encoding="utf-8")
marker = "\nif __name__ == \"__main__\":\n"
if marker not in runtime:
    raise RuntimeError("runtime test insertion marker missing")
new_tests = r'''
    def test_crouch_teleport_has_four_pages_and_new_controls(self):
        for source in (self.it, self.en):
            self.assertIn("KursorTeleportasi %= 4;", source)
            self.assertIn("Event Player.PerintahTeleportasi = 1;", source)
            self.assertIn("Event Player.PerintahTeleportasi = 2;", source)
            self.assertIn("Event Player.PerintahTeleportasi = 3;", source)
            self.assertIn("PerintahTeleportasi == 3;", source)
            self.assertIn("(Event Player.KursorTeleportasi + (Event Player.PerintahTeleportasi == 1 ? 1 : 3)) % 4", source)
            self.assertIn("ATTACH ABOVE PLAYER / BOT", source)

    def test_crouch_attach_uses_native_attach_and_reload_detach(self):
        for source in (self.it, self.en):
            self.assertIn("Attach Players(Event Player, Event Player.TargetLampiranTeleportasi, Vector(0,", source)
            self.assertIn("+ 0.750, 0));", source)
            self.assertIn("Detach Players(Event Player);", source)
            self.assertIn("Is Button Held(Event Player, Button(Reload)) == True;", source)
            self.assertIn("99: TargetLampiranTeleportasi", source)
            self.assertIn("100: LampiranTeleportasiAktif", source)

    def test_crouch_attach_auto_detaches_on_death_leave_or_hero_change(self):
        for source in (self.it, self.en):
            self.assertIn("Entity Exists(Event Player.TargetLampiranTeleportasi) == False", source)
            self.assertIn("Is Alive(Event Player.TargetLampiranTeleportasi) == False", source)
            self.assertIn("Hero Of(Event Player) != Event Player.PahlawanLampiranSendiri", source)
            self.assertIn("Hero Of(Event Player.TargetLampiranTeleportasi) != Event Player.PahlawanLampiranTarget", source)
            self.assertIn("TargetLampiranTeleportasi) == Global.PemainPembersihan", source.replace("Globale.", "Global."))
'''
runtime = runtime.replace(marker, new_tests + marker, 1)
runtime_path.write_text(runtime, encoding="utf-8")

changelog = ROOT / "CHANGELOG.md"
cl = changelog.read_text(encoding="utf-8")
anchor = "- Rimossi tre `Wait(0.016)` ridondanti da Jump Resurrect, cleanup roster e seconda fase della classificazione iBot: `BersihkanPemain` è ora interamente atomica e il classificatore conserva soltanto il frame necessario a leggere il nome forzato. Restano 7 Wait funzionali e un solo Loop, indispensabile per il tick dello scheduler globale.\n"
if anchor not in cl:
    raise RuntimeError("changelog anchor missing")
cl = cl.replace(anchor, anchor + "- Crouch Teleport esteso a quattro pagine: Primary/Secondary navigano avanti e indietro, Interact esegue l'azione; la quarta pagina permette di agganciarsi sopra un player/bot pubblico con offset sopra la testa, Reload sgancia e morte/leave/cambio eroe di uno dei due interrompono automaticamente il collegamento.\n", 1)
changelog.write_text(cl, encoding="utf-8")

print("Crouch Teleport attach patch applied")
