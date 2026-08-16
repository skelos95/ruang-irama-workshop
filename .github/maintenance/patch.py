from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
PROJECT = ROOT / "docs" / "PROGETTO.md"
VALIDATION = ROOT / "docs" / "VALIDAZIONE.md"
README = ROOT / "README.md"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one occurrence, found {count}")
    return text.replace(old, new, 1)


def find_matching_call(text: str, start: int) -> int:
    opening = text.find("(", start)
    if opening < 0:
        raise RuntimeError("call opening parenthesis not found")
    depth = 1
    in_string = False
    escaped = False
    i = opening + 1
    while i < len(text):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    raise RuntimeError("call closing parenthesis not found")


def replace_call(text: str, marker: str, replacement: str, label: str) -> str:
    start = text.find(marker)
    if start < 0:
        raise RuntimeError(f"{label}: marker not found")
    end = find_matching_call(text, start)
    semi = text.find(";", end)
    if semi != end + 1:
        raise RuntimeError(f"{label}: call semicolon not found")
    return text[:start] + replacement + text[semi + 1:]


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    return hashlib.sha1(payload).hexdigest()


def vote_line(index: int, lang: str) -> str:
    if lang == "en":
        body = f'Custom String("{{0}} - {{1}} VOTES", Global.PemainManusia[{index}], Global.PemainManusia[{index}].NumeroVoti)'
    elif lang == "id":
        body = f'Custom String("{{0}} - {{1}} VOTE", Global.PemainManusia[{index}], Global.PemainManusia[{index}].NumeroVoti)'
    else:
        body = f'Custom String("{{0}} - {{1}} โหวต", Global.PemainManusia[{index}], Global.PemainManusia[{index}].NumeroVoti)'
    return (
        f'Count Of(Global.PemainManusia) > {index} ? '
        f'Custom String("{{0}} {{1}}", Event Player.KursorVoto == {index} ? Custom String(">") : Custom String(" "), {body}) '
        f': Custom String("")'
    )


def vote_list(lang: str) -> str:
    expr = vote_line(11, lang)
    for idx in range(10, -1, -1):
        expr = f'Custom String("{{0}}\\n{{1}}", {vote_line(idx, lang)}, {expr})'
    return expr


source = SOURCE.read_text(encoding="utf-8")

# ----- Variables and subroutines -------------------------------------------------
source = replace_once(
    source,
    "\t\t43: DaftarWarnaRGB\n\tplayer:",
    "\t\t43: DaftarWarnaRGB\n\t\t44: LeaderVoto\n\t\t45: MaxVoti\n\t\t46: PariVoti\n\t\t47: IndeksVoto\n\t\t48: HudVotoLeader\n\t\t49: HudDiagnostik\n\tplayer:",
    "vote global variables",
)
source = replace_once(
    source,
    "\t\t80: TargetKameraSebelumNasib\n}",
    "\t\t80: TargetKameraSebelumNasib\n\t\t81: KursorVoto\n\t\t82: TargetVoto\n\t\t83: NumeroVoti\n}",
    "vote player variables",
)
source = replace_once(
    source,
    "\t24: GambarNasib\n}",
    "\t24: GambarNasib\n\t25: GambarVoto\n\t26: AggiornaVoti\n}",
    "vote subroutines",
)

# ----- Global init ---------------------------------------------------------------
source = replace_once(
    source,
    "\t\tGlobal.SlotHUDTerakhir = -1;\n\t\tGlobal.KodeMenu = Array(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10);",
    "\t\tGlobal.SlotHUDTerakhir = -1;\n\t\tGlobal.LeaderVoto = Null;\n\t\tGlobal.MaxVoti = 0;\n\t\tGlobal.PariVoti = False;\n\t\tGlobal.IndeksVoto = 0;\n\t\tGlobal.HudVotoLeader = Null;\n\t\tGlobal.HudDiagnostik = Null;\n\t\tGlobal.KodeMenu = Array(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11);",
    "vote global init and menu code",
)

# Player rows no longer carry diagnostics in their Text field. Leader/diagnostics
# get their own HUD entries, which naturally sort after the last existing player.
left_row = '''\t\tCreate HUD Text(Global.PemainManusia, Null, Custom String("{0} {1} {2}",
\t\t\tGlobal.DaftarIkon[Event Player.IndeksIkon], Hero Icon String(Is Duplicating(Event Player) ? Hero Being Duplicated(Event Player) : Hero Of(Event Player)),
\t\t\tCustom String("{0} - {1} MIN", Event Player, Event Player.MenitLobi)), Null, Left, -99 + Event Player.UrutanHUD, Color(White), Event Player.WarnaNama,
\t\t\tColor(White), Visible To String and Color, Visible Never)'''
source = replace_call(
    source,
    '\t\tCreate HUD Text(Global.PemainManusia, Null, Custom String("{0} {1} {2}",',
    left_row,
    "left player HUD without diagnostics",
)

static_huds = '''\t\tGlobal.HudInfoKanan = Last Text ID;
\t\tCreate HUD Text(Global.PemainManusia, Null, Global.LeaderVoto != Null ? Player Variable(Local Player, IndeksBahasa) == 0
\t\t\t? Custom String("\\nMOST VOTED: {0} - {1} VOTES", Global.LeaderVoto, Global.MaxVoti) : Player Variable(Local Player, IndeksBahasa) == 1
\t\t\t? Custom String("\\nPALING BANYAK DIPILIH: {0} - {1} VOTE", Global.LeaderVoto, Global.MaxVoti) : Custom String("\\nโหวตสูงสุด: {0} - {1} โหวต", Global.LeaderVoto, Global.MaxVoti)
\t\t\t: Custom String(""), Null, Left, 90, Color(White), Global.LeaderVoto == Null ? Color(White) : Player Variable(Global.LeaderVoto, WarnaNama), Color(White),
\t\t\tVisible To String and Color, Visible Never);
\t\tGlobal.HudVotoLeader = Last Text ID;
\t\tCreate HUD Text(Global.PemainManusia, Null, And(Global.DiagnostikPerforma == True, Local Player == Host Player)
\t\t\t? Player Variable(Local Player, IndeksBahasa) == 2 ? Custom String("{0}\\n{1}", Custom String("\\nโหลด {0}% | เฉลี่ย {1}% | สูงสุด {2}%", Server Load,
\t\t\tServer Load Average, Server Load Peak), Custom String("HUD {0} | IWT {1}", 5 + Count Of(Global.HudKiriPemain) * 2 + Count Of(Filtered Array(
\t\t\tGlobal.HudMenuPemain, Current Array Element != 0)), Count Of(Filtered Array(Global.TeksDuniaPemain, Current Array Element != 0)) + Count Of(Filtered Array(
\t\t\tGlobal.TeksDiriPemain, Current Array Element != 0)))) : Player Variable(Local Player, IndeksBahasa) == 1 ? Custom String("{0}\\n{1}", Custom String(
\t\t\t"\\nBEBAN {0}% | RATA {1}% | PUNCAK {2}%", Server Load, Server Load Average, Server Load Peak), Custom String("HUD {0} | IWT {1}",
\t\t\t5 + Count Of(Global.HudKiriPemain) * 2 + Count Of(Filtered Array(Global.HudMenuPemain, Current Array Element != 0)), Count Of(Filtered Array(
\t\t\tGlobal.TeksDuniaPemain, Current Array Element != 0)) + Count Of(Filtered Array(Global.TeksDiriPemain, Current Array Element != 0)))) : Custom String("{0}\\n{1}",
\t\t\tCustom String("\\nLOAD {0}% | AVG {1}% | MAX {2}%", Server Load, Server Load Average, Server Load Peak), Custom String("HUD {0} | IWT {1}",
\t\t\t5 + Count Of(Global.HudKiriPemain) * 2 + Count Of(Filtered Array(Global.HudMenuPemain, Current Array Element != 0)), Count Of(Filtered Array(
\t\t\tGlobal.TeksDuniaPemain, Current Array Element != 0)) + Count Of(Filtered Array(Global.TeksDiriPemain, Current Array Element != 0)))) : Custom String(""), Null,
\t\t\tLeft, 91, Color(White), Color(White), Color(White), Visible To String and Color, Visible Never);
\t\tGlobal.HudDiagnostik = Last Text ID;'''
source = replace_once(
    source,
    "\t\tGlobal.HudInfoKanan = Last Text ID;",
    static_huds,
    "leader and diagnostics HUD",
)

# ----- Human registration / leave ------------------------------------------------
source = replace_once(
    source,
    "\t\tGlobal.PemainManusia = Append To Array(Global.PemainManusia, Event Player);\n\t\tDisable Nameplates(Event Player, Filtered Array(Global.PemainManusia, Player Variable(Current Array Element, InspeksiAktif) == True));",
    "\t\tGlobal.PemainManusia = Append To Array(Global.PemainManusia, Event Player);\n\t\tCall Subroutine(AggiornaVoti);\n\t\tDisable Nameplates(Event Player, Filtered Array(Global.PemainManusia, Player Variable(Current Array Element, InspeksiAktif) == True));",
    "recount votes on human registration",
)

leave_insert = '''\t\t\tGlobal.SlotHUDTerakhir = Count Of(Global.SlotHUDPemain) == 0 ? -1 : Last Of(Sorted Array(Global.SlotHUDPemain, Current Array Element));
\t\tEnd;
\t\tFor Global Variable(IndeksVoto, 0, Count Of(Global.PemainManusia), 1);
\t\t\tIf(Global.PemainManusia[Global.IndeksVoto].TargetVoto == Global.PemainPembersihan);
\t\t\t\tSet Player Variable(Global.PemainManusia[Global.IndeksVoto], TargetVoto, Null);
\t\t\tEnd;
\t\t\tSet Player Variable(Global.PemainManusia[Global.IndeksVoto], KursorVoto, Count Of(Global.PemainManusia) == 0 ? 0 : Min(Player Variable(
\t\t\t\tGlobal.PemainManusia[Global.IndeksVoto], KursorVoto), Count Of(Global.PemainManusia) - 1));
\t\tEnd;
\t\tCall Subroutine(AggiornaVoti);'''
source = replace_once(
    source,
    "\t\t\tGlobal.SlotHUDTerakhir = Count Of(Global.SlotHUDPemain) == 0 ? -1 : Last Of(Sorted Array(Global.SlotHUDPemain, Current Array Element));\n\t\tEnd;",
    leave_insert,
    "vote leave cleanup",
)

# ----- Menu count and navigation --------------------------------------------------
source = source.replace("(Event Player.KursorUtama + 1) % 11;", "(Event Player.KursorUtama + 1) % 12;", 1)
source = source.replace("(Event Player.KursorUtama + 10) % 11;", "(Event Player.KursorUtama + 11) % 12;", 1)
source = replace_once(
    source,
    "\t\tElse If(Event Player.HalamanMenu == 9);\n\t\t\tEvent Player.KursorPrivasiInspeksi = (Event Player.KursorPrivasiInspeksi + 1) % 2;\n\t\tEnd;",
    "\t\tElse If(Event Player.HalamanMenu == 9);\n\t\t\tEvent Player.KursorPrivasiInspeksi = (Event Player.KursorPrivasiInspeksi + 1) % 2;\n\t\tElse If(Event Player.HalamanMenu == 11);\n\t\t\tIf(Count Of(Global.PemainManusia) > 0);\n\t\t\t\tEvent Player.KursorVoto = (Event Player.KursorVoto + 1) % Count Of(Global.PemainManusia);\n\t\t\tEnd;\n\t\tEnd;",
    "vote next navigation",
)
source = replace_once(
    source,
    "\t\tElse If(Event Player.HalamanMenu == 9);\n\t\t\tEvent Player.KursorPrivasiInspeksi = (Event Player.KursorPrivasiInspeksi + 1) % 2;\n\t\tEnd;",
    "\t\tElse If(Event Player.HalamanMenu == 9);\n\t\t\tEvent Player.KursorPrivasiInspeksi = (Event Player.KursorPrivasiInspeksi + 1) % 2;\n\t\tElse If(Event Player.HalamanMenu == 11);\n\t\t\tIf(Count Of(Global.PemainManusia) > 0);\n\t\t\t\tEvent Player.KursorVoto = (Event Player.KursorVoto + Count Of(Global.PemainManusia) - 1) % Count Of(Global.PemainManusia);\n\t\t\tEnd;\n\t\tEnd;",
    "vote previous navigation",
)

# Opening Vote menu selects the current vote when it still exists.
source = replace_once(
    source,
    "\t\t\tElse If(Event Player.HalamanMenu == 9);\n\t\t\t\tEvent Player.KursorPrivasiInspeksi = Event Player.KursorPrivasiInspeksi;\n\t\t\tEnd;",
    "\t\t\tElse If(Event Player.HalamanMenu == 9);\n\t\t\t\tEvent Player.KursorPrivasiInspeksi = Event Player.KursorPrivasiInspeksi;\n\t\t\tElse If(Event Player.HalamanMenu == 11);\n\t\t\t\tEvent Player.KursorVoto = And(Event Player.TargetVoto != Null, Array Contains(Global.PemainManusia, Event Player.TargetVoto)) ? Index Of Array Value(\n\t\t\t\t\tGlobal.PemainManusia, Event Player.TargetVoto) : Min(Event Player.KursorVoto, Count Of(Global.PemainManusia) - 1);\n\t\t\tEnd;",
    "vote menu opening cursor",
)

# Menu 10 gets an explicit branch; the final branch becomes Menu 11 voting.
source = replace_once(
    source,
    "\t\tElse;\n\t\t\tIf(Event Player.KartuNasibAktif == True);",
    "\t\tElse If(Event Player.HalamanMenu == 10);\n\t\t\tIf(Event Player.KartuNasibAktif == True);",
    "explicit menu 10 branch",
)
vote_action = '''\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Luck roulette started. Red or green?") : Event Player.IndeksBahasa == 1 ? Custom String("Roulette nasib dimulai. Merah atau hijau?") : Custom String("เริ่มรูเล็ตเสี่ยงโชคแล้ว แดงหรือเขียว?"));
\t\t\tEnd;
\t\tElse;
\t\t\tIf(Count Of(Global.PemainManusia) > 0);
\t\t\t\tEvent Player.KursorVoto %= Count Of(Global.PemainManusia);
\t\t\t\tIf(Event Player.TargetVoto != Global.PemainManusia[Event Player.KursorVoto]);
\t\t\t\t\tEvent Player.TargetVoto = Global.PemainManusia[Event Player.KursorVoto];
\t\t\t\t\tCall Subroutine(AggiornaVoti);
\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Vote registered for {0}.", Event Player.TargetVoto) : Event Player.IndeksBahasa == 1 ? Custom String("Vote untuk {0} tersimpan.", Event Player.TargetVoto) : Custom String("โหวตให้ {0} แล้ว", Event Player.TargetVoto));
\t\t\t\tEnd;
\t\t\tEnd;
\t\t\tCall Subroutine(GambarMenu);
\t\tEnd;'''
source = replace_once(
    source,
    '''\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Luck roulette started. Red or green?") : Event Player.IndeksBahasa == 1 ? Custom String("Roulette nasib dimulai. Merah atau hijau?") : Custom String("เริ่มรูเล็ตเสี่ยงโชคแล้ว แดงหรือเขียว?"));
\t\t\tEnd;
\t\tEnd;''',
    vote_action,
    "vote interact action",
)

source = source.replace("Eleven extremely important decisions await.", "Twelve extremely important decisions await.", 1)
source = source.replace("Sebelas keputusan yang sangat penting menunggu.", "Dua belas keputusan yang sangat penting menunggu.", 1)
source = source.replace("มีสิบเอ็ดตัวเลือกสำคัญรอคุณอยู่", "มีสิบสองตัวเลือกสำคัญรอคุณอยู่", 1)

# ----- Main menu renderer and router ---------------------------------------------
source = replace_once(
    source,
    ': Event Player.KursorUtama == 9 ? Custom String("9 - CROUCH PRIVACY\\nCURRENT: {0}", Event Player.PrivasiInspeksiAktif ? Custom String("ON") : Custom String("OFF"))\n\t\t\t: Custom String("10 - TRY YOUR LUCK\\nSTATUS: {0}", Event Player.KartuNasibAktif ? Custom String("ACTIVE") : Custom String("READY"))',
    ': Event Player.KursorUtama == 9 ? Custom String("9 - CROUCH PRIVACY\\nCURRENT: {0}", Event Player.PrivasiInspeksiAktif ? Custom String("ON") : Custom String("OFF"))\n\t\t\t: Event Player.KursorUtama == 10 ? Custom String("10 - TRY YOUR LUCK\\nSTATUS: {0}", Event Player.KartuNasibAktif ? Custom String("ACTIVE") : Custom String("READY"))\n\t\t\t: Custom String("11 - VOTE PLAYER\\nYOUR VOTE: {0}", Event Player.TargetVoto != Null ? Event Player.TargetVoto : Custom String("NONE"))',
    "main EN vote entry",
)
source = replace_once(
    source,
    ': Event Player.KursorUtama == 9 ? Custom String("9 - PRIVASI JONGKOK\\nSAAT INI: {0}", Event Player.PrivasiInspeksiAktif ? Custom String("AKTIF") : Custom String("MATI"))\n\t\t\t: Custom String("10 - COBA NASIB\\nSTATUS: {0}", Event Player.KartuNasibAktif ? Custom String("AKTIF") : Custom String("SIAP"))',
    ': Event Player.KursorUtama == 9 ? Custom String("9 - PRIVASI JONGKOK\\nSAAT INI: {0}", Event Player.PrivasiInspeksiAktif ? Custom String("AKTIF") : Custom String("MATI"))\n\t\t\t: Event Player.KursorUtama == 10 ? Custom String("10 - COBA NASIB\\nSTATUS: {0}", Event Player.KartuNasibAktif ? Custom String("AKTIF") : Custom String("SIAP"))\n\t\t\t: Custom String("11 - VOTE PEMAIN\\nVOTE KAMU: {0}", Event Player.TargetVoto != Null ? Event Player.TargetVoto : Custom String("BELUM ADA"))',
    "main ID vote entry",
)
source = replace_once(
    source,
    ': Event Player.KursorUtama == 9 ? Custom String("9 - ความเป็นส่วนตัวตอนย่อ\\nสถานะ: {0}", Event Player.PrivasiInspeksiAktif ? Custom String("เปิด") : Custom String("ปิด"))\n\t\t\t: Custom String("10 - เสี่ยงโชค\\nสถานะ: {0}", Event Player.KartuNasibAktif ? Custom String("ทำงาน") : Custom String("พร้อม"))',
    ': Event Player.KursorUtama == 9 ? Custom String("9 - ความเป็นส่วนตัวตอนย่อ\\nสถานะ: {0}", Event Player.PrivasiInspeksiAktif ? Custom String("เปิด") : Custom String("ปิด"))\n\t\t\t: Event Player.KursorUtama == 10 ? Custom String("10 - เสี่ยงโชค\\nสถานะ: {0}", Event Player.KartuNasibAktif ? Custom String("ทำงาน") : Custom String("พร้อม"))\n\t\t\t: Custom String("11 - โหวตผู้เล่น\\nโหวตของคุณ: {0}", Event Player.TargetVoto != Null ? Event Player.TargetVoto : Custom String("ยังไม่ได้โหวต"))',
    "main TH vote entry",
)
source = replace_once(
    source,
    "\t\tElse If(Event Player.HalamanMenu == 9);\n\t\t\tCall Subroutine(GambarPrivasiInspeksi);\n\t\tElse;\n\t\t\tCall Subroutine(GambarNasib);",
    "\t\tElse If(Event Player.HalamanMenu == 9);\n\t\t\tCall Subroutine(GambarPrivasiInspeksi);\n\t\tElse If(Event Player.HalamanMenu == 10);\n\t\t\tCall Subroutine(GambarNasib);\n\t\tElse;\n\t\t\tCall Subroutine(GambarVoto);",
    "vote menu router",
)

# ----- Distinct Unkillable icons --------------------------------------------------
source = replace_once(
    source,
    '''\t\t\t\t\t\tIf(Event Player.IkonKebal == Null);
\t\t\t\t\t\t\tCreate Icon(All Players(All Teams), Event Player, Halo, Visible To and Position, Global.RGB, True);
\t\t\t\t\t\t\tEvent Player.IkonKebal = Last Created Entity;
\t\t\t\t\t\tEnd;''',
    '''\t\t\t\t\t\tIf(Event Player.IkonKebal != Null);
\t\t\t\t\t\t\tDestroy Icon(Event Player.IkonKebal);
\t\t\t\t\t\t\tEvent Player.IkonKebal = Null;
\t\t\t\t\t\tEnd;
\t\t\t\t\t\tIf(Event Player.ModeKebal == 1);
\t\t\t\t\t\t\tCreate Icon(All Players(All Teams), Event Player, Warning, Visible To and Position, Custom Color(255, 80, 80, 255), True);
\t\t\t\t\t\tElse;
\t\t\t\t\t\t\tCreate Icon(All Players(All Teams), Event Player, Halo, Visible To and Position, Global.RGB, True);
\t\t\t\t\t\tEnd;
\t\t\t\t\t\tEvent Player.IkonKebal = Last Created Entity;''',
    "distinct unkillable icons",
)

# ----- Vote renderer and tally subroutine ----------------------------------------
renderer = f'''rule("91o - Subrutin: Gambar menu vote pemain")
{{
\tevent
\t{{
\t\tSubroutine;
\t\tGambarVoto;
\t}}

\tactions
\t{{
\t\tCreate HUD Text(Event Player, Null, Event Player.IndeksBahasa == 0 ? Custom String("{{0}}\\n{{1}}", Custom String("\\n{{0}}: next | {{1}}: previous", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire))), Custom String("{{0}}: vote | {{1}}: back", Input Binding String(Button(Interact)), Input Binding String(Button(Reload))))
\t\t\t: Event Player.IndeksBahasa == 1 ? Custom String("{{0}}\\n{{1}}", Custom String("\\n{{0}}: berikutnya | {{1}}: sebelumnya", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire))), Custom String("{{0}}: vote | {{1}}: kembali", Input Binding String(Button(Interact)), Input Binding String(Button(Reload))))
\t\t\t: Custom String("{{0}}\\n{{1}}", Custom String("\\n{{0}}: ถัดไป | {{1}}: ก่อนหน้า", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire))), Custom String("{{0}}: โหวต | {{1}}: กลับ", Input Binding String(Button(Interact)), Input Binding String(Button(Reload)))),
\t\t\tEvent Player.IndeksBahasa == 0 ? Custom String("{{0}}\\n{{1}}", Custom String("11 - VOTE PLAYER {{0}}/{{1}}\\nYOUR VOTE: {{2}}", Event Player.KursorVoto + 1, Count Of(Global.PemainManusia), Event Player.TargetVoto != Null ? Event Player.TargetVoto : Custom String("NONE")), {vote_list('en')})
\t\t\t: Event Player.IndeksBahasa == 1 ? Custom String("{{0}}\\n{{1}}", Custom String("11 - VOTE PEMAIN {{0}}/{{1}}\\nVOTE KAMU: {{2}}", Event Player.KursorVoto + 1, Count Of(Global.PemainManusia), Event Player.TargetVoto != Null ? Event Player.TargetVoto : Custom String("BELUM ADA")), {vote_list('id')})
\t\t\t: Custom String("{{0}}\\n{{1}}", Custom String("11 - โหวตผู้เล่น {{0}}/{{1}}\\nโหวตของคุณ: {{2}}", Event Player.KursorVoto + 1, Count Of(Global.PemainManusia), Event Player.TargetVoto != Null ? Event Player.TargetVoto : Custom String("ยังไม่ได้โหวต")), {vote_list('th')}),
\t\t\tTop, 100, Color(White), Custom Color(235, 230, 190, 255), Custom Color(X Component Of(Event Player.WarnaMenu), Y Component Of(Event Player.WarnaMenu), Z Component Of(Event Player.WarnaMenu), 255), Visible To String and Color, Visible Never);
\t\tEvent Player.HudMenu = Last Text ID;
\t}}
}}

rule("91p - Subrutin: Hitung ulang vote dan leader unik")
{{
\tevent
\t{{
\t\tSubroutine;
\t\tAggiornaVoti;
\t}}

\tactions
\t{{
\t\tGlobal.LeaderVoto = Null;
\t\tGlobal.MaxVoti = 0;
\t\tGlobal.PariVoti = False;
\t\tFor Global Variable(IndeksVoto, 0, Count Of(Global.PemainManusia), 1);
\t\t\tSet Player Variable(Global.PemainManusia[Global.IndeksVoto], NumeroVoti, Count Of(Filtered Array(Global.PemainManusia, Player Variable(Current Array Element, TargetVoto) == Global.PemainManusia[Global.IndeksVoto])));
\t\t\tIf(Global.PemainManusia[Global.IndeksVoto].NumeroVoti > Global.MaxVoti);
\t\t\t\tGlobal.MaxVoti = Global.PemainManusia[Global.IndeksVoto].NumeroVoti;
\t\t\t\tGlobal.LeaderVoto = Global.PemainManusia[Global.IndeksVoto];
\t\t\t\tGlobal.PariVoti = False;
\t\t\tElse If(And(Global.PemainManusia[Global.IndeksVoto].NumeroVoti == Global.MaxVoti, Global.MaxVoti > 0));
\t\t\t\tGlobal.PariVoti = True;
\t\t\tEnd;
\t\tEnd;
\t\tIf(Or(Global.MaxVoti <= 0, Global.PariVoti == True));
\t\t\tGlobal.LeaderVoto = Null;
\t\tEnd;
\t}}
}}

'''
source = replace_once(
    source,
    'rule("93 - Subrutin: Mulai kamera dinamis di bahu kiri")',
    renderer + 'rule("93 - Subrutin: Mulai kamera dinamis di bahu kiri")',
    "insert vote renderer and tally",
)

# Initialize per-player vote state.
source = replace_once(
    source,
    "\t\tEvent Player.TargetKameraSebelumNasib = Null;\n\t\tEvent Player.KartuNasibMerah = False;",
    "\t\tEvent Player.TargetKameraSebelumNasib = Null;\n\t\tEvent Player.KursorVoto = 0;\n\t\tEvent Player.TargetVoto = Null;\n\t\tEvent Player.NumeroVoti = 0;\n\t\tEvent Player.KartuNasibMerah = False;",
    "initialize player vote state",
)

SOURCE.write_text(source, encoding="utf-8")

# ----- Validator -----------------------------------------------------------------
validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_once(
    validator,
    'checks.equal(codes, ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"], "codici degli undici menu")',
    'checks.equal(codes, ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"], "codici dei dodici menu")',
    "validator menu codes",
)
validator = replace_once(
    validator,
    're.search(r"KursorUtama\\s*=\\s*\\([^;]+\\)\\s*%\\s*11\\s*;", clean) is not None,\n        "navigazione principale non limitata a undici menu",',
    're.search(r"KursorUtama\\s*=\\s*\\([^;]+\\)\\s*%\\s*12\\s*;", clean) is not None,\n        "navigazione principale non limitata a dodici menu",',
    "validator menu modulo",
)
validator = replace_once(
    validator,
    '        "GambarSakelarTeleportasi", "GambarPrivasiInspeksi", "GambarNasib",\n    }',
    '        "GambarSakelarTeleportasi", "GambarPrivasiInspeksi", "GambarNasib", "GambarVoto",\n    }',
    "validator vote renderer expected",
)

# Replace old single-Halo contract with distinct Warning/Halo modes.
validator = replace_once(
    validator,
    '            "Create Icon(All Players(All Teams), Event Player, Halo, Visible To and Position, Global.RGB, True);",\n            "Event Player.IkonKebal = Last Created Entity;",',
    '            "Create Icon(All Players(All Teams), Event Player, Warning, Visible To and Position, Custom Color(255, 80, 80, 255), True);",\n            "Create Icon(All Players(All Teams), Event Player, Halo, Visible To and Position, Global.RGB, True);",\n            "Event Player.IkonKebal = Last Created Entity;",',
    "validator distinct unkillable token",
)
validator = replace_once(
    validator,
    '''    # Public icon is intentionally independent from Crouch Privacy and team.
    icon_calls = [call for call in call_texts(source, "Create Icon") if "Halo" in call and "Event Player" in call]
    checks.equal(len(icon_calls), 1, "Unkillable Halo public icon")
    if icon_calls:
        checks.require("All Players(All Teams)" in icon_calls[0] and "Global.RGB" in icon_calls[0] and "Visible To and Position" in icon_calls[0], "Unkillable Halo non è pubblico/RGB/follow")
        checks.require("PrivasiInspeksiAktif" not in icon_calls[0] and "Team Of(" not in icon_calls[0], "Unkillable Halo dipende dalla privacy/team")
''',
    '''    # 1 HP and FULL HP use different public icons.
    halo_calls = [call for call in call_texts(source, "Create Icon") if ", Halo," in call and "Event Player" in call]
    warning_calls = [call for call in call_texts(source, "Create Icon") if ", Warning," in call and "Event Player" in call]
    checks.equal(len(halo_calls), 1, "Unkillable FULL HP Halo public icon")
    checks.equal(len(warning_calls), 1, "Unkillable 1 HP Warning public icon")
    if halo_calls:
        checks.require("All Players(All Teams)" in halo_calls[0] and "Global.RGB" in halo_calls[0] and "Visible To and Position" in halo_calls[0], "Unkillable FULL HP Halo non è pubblico/RGB/follow")
    if warning_calls:
        checks.require("All Players(All Teams)" in warning_calls[0] and "Custom Color(255, 80, 80, 255)" in warning_calls[0] and "Visible To and Position" in warning_calls[0], "Unkillable 1 HP Warning non è pubblico/rosso/follow")
''',
    "validator distinct unkillable icons",
)

vote_check = r'''

def check_vote_menu(checks: Checks, source: str, rules: list[Rule], subroutines: set[str]) -> None:
    clean = mask_strings(source)
    variables = section_body(source, "variables")
    for token in (
        "44: LeaderVoto", "45: MaxVoti", "46: PariVoti", "47: IndeksVoto",
        "81: KursorVoto", "82: TargetVoto", "83: NumeroVoti",
    ):
        checks.require(token in variables, f"Vote: variabile mancante {token}")
    checks.require("GambarVoto" in subroutines and "AggiornaVoti" in subroutines, "Vote: subroutine mancanti")
    checks.require("Global.KodeMenu = Array(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11);" in clean, "Vote: Menu 11 non registrato")
    handlers = [r for r in rules if code_contains(r.body, "Event Player.PerintahMenu == 1;", "Event Player.HalamanMenu = Global.KodeMenu")]
    checks.equal(len(handlers), 1, "Vote: dispatcher Interact")
    if handlers:
        body = mask_strings(handlers[0].body)
        for token in (
            "Event Player.TargetVoto = Global.PemainManusia[Event Player.KursorVoto];",
            "Call Subroutine(AggiornaVoti);",
        ):
            checks.require(token in body, f"Vote: handler incompleto {token}")
        checks.require("All Players(All Teams)" not in body[body.find("Event Player.TargetVoto ="):body.find("Call Subroutine(GambarMenu);", body.find("Event Player.TargetVoto ="))], "Vote: i bot entrano nella selezione")
    tally = rules_containing(rules, "Subroutine;", "AggiornaVoti;")
    checks.equal(len(tally), 1, "Vote: tally subroutine")
    if tally:
        body = mask_strings(tally[0].body)
        for token in (
            "Filtered Array(Global.PemainManusia",
            "TargetVoto",
            "NumeroVoti",
            "Global.PariVoti = True;",
            "Global.LeaderVoto = Null;",
        ):
            checks.require(token in body, f"Vote: tally incompleto {token}")
    renderer = rules_containing(rules, "Subroutine;", "GambarVoto;")
    checks.equal(len(renderer), 1, "Vote: renderer")
    if renderer:
        raw = renderer[0].body
        checks.require("11 - VOTE PLAYER" in raw and "11 - VOTE PEMAIN" in raw and "11 - โหวตผู้เล่น" in raw, "Vote: localizzazione menu incompleta")
        checks.require(raw.count("Global.PemainManusia[") >= 24 and "NumeroVoti" in raw, "Vote: menu non mostra tutti i player con voti")
    checks.require("MOST VOTED:" in source and "PALING BANYAK DIPILIH:" in source and "โหวตสูงสุด:" in source, "Vote: HUD leader localizzato assente")
    checks.require("Global.LeaderVoto != Null" in clean, "Vote: HUD leader non è nascosto in pareggio")
    checks.require("Left, 90" in clean and "Left, 91" in clean, "Vote: leader/diagnostics non ordinati sotto roster sinistro")
    leave = [r for r in rules if code_contains(r.body, "Player Left Match;")]
    checks.require(bool(leave) and "TargetVoto == Global.PemainPembersihan" in mask_strings(leave[0].body), "Vote: cleanup target leave assente")
'''
insert_at = validator.index("\ndef main() -> None:")
validator = validator[:insert_at] + vote_check + validator[insert_at:]
validator = replace_once(
    validator,
    "        check_idempotent_menu_feedback(checks, source, rules)\n",
    "        check_idempotent_menu_feedback(checks, source, rules)\n        check_vote_menu(checks, source, rules, subroutines)\n",
    "call vote validator",
)
VALIDATOR.write_text(validator, encoding="utf-8")

# ----- Documentation --------------------------------------------------------------
project = PROJECT.read_text(encoding="utf-8")
project = project.replace("## Main Menu: 11 voci", "## Main Menu: 12 voci")
project = project.replace(
    "| 10 | Try Your Luck | crea una carta pubblica; solo il proprietario può attivarla, con esito 50/50 cura completa o morte |",
    "| 10 | Try Your Luck | crea una carta pubblica; solo il proprietario può attivarla, con esito 50/50 cura completa o morte |\n| 11 | Vote Player | voto personale verso qualsiasi umano della lobby, incluso se stessi; bot esclusi |",
)
project = project.replace(
    "`ModeKebal`: 0=OFF, 1=1 HP, 2=FULL HP. FULL HP imposta Damage Received a 0% e ha una guardia che riporta la salute a Max Health se viene ridotta da altre modifiche. Le modalità 1 HP e FULL HP condividono un Halo creato con `Create Icon(All Players(All Teams), Event Player, Halo, Visible To and Position, Global.RGB, True)`, quindi l'indicatore non dipende da Crouch Privacy. OFF e Player Left distruggono l'icona.",
    "`ModeKebal`: 0=OFF, 1=1 HP, 2=FULL HP. FULL HP imposta Damage Received a 0% e ha una guardia che riporta la salute a Max Health se viene ridotta da altre modifiche. Le due modalità hanno ora indicatori distinti e pubblici: 1 HP usa `Warning` rosso, FULL HP usa `Halo` con `Global.RGB`. Passando fra 1 HP e FULL HP la vecchia icona viene distrutta e sostituita; OFF e Player Left la eliminano.",
)
project += "\n\n## Menu 11 — Vote Player\n\nOgni umano può assegnare un solo voto attivo a qualsiasi umano presente in `Global.PemainManusia`, incluso se stesso. I bot non entrano mai nella lista. Cambiare scelta sposta il proprio voto al nuovo target. `AggiornaVoti` ricalcola i conteggi solo su join, leave o voto, senza loop periodico. Il menu mostra fino a 12 player con il rispettivo totale. Se esiste un unico leader con almeno un voto, il suo nome appare sotto il roster sinistro dopo una riga vuota; il diagnostics host-only segue dopo un'altra riga vuota. Se due o più player condividono il massimo, `LeaderVoto` viene impostato a `Null` e nessun nome viene mostrato. Se un target esce, i voti diretti a lui vengono azzerati e i conteggi vengono ricalcolati.\n"
PROJECT.write_text(project, encoding="utf-8")

readme = README.read_text(encoding="utf-8")
readme = readme.replace("- **10 menu Arcade**:", "- **12 menu Arcade**:")
readme = readme.replace(
    "  10. `9 - Crouch Privacy` — quando ON nasconde completamente icona/nome/salute ai nemici durante Crouch inspection; i compagni vedono sempre tutto; default OFF.",
    "  10. `9 - Crouch Privacy` — quando ON nasconde completamente icona/nome/salute ai nemici durante Crouch inspection; i compagni vedono sempre tutto; default OFF.\n  11. `10 - Try Your Luck` — roulette 50/50 cura completa o morte.\n  12. `11 - Vote Player` — vota qualsiasi umano della lobby, incluso te stesso; bot esclusi.",
)
readme = readme.replace(
    "| 9 | Crouch Privacy | OFF / ON; ON nasconde tutto ai nemici, alleati sempre visibili |",
    "| 9 | Crouch Privacy | OFF / ON; ON nasconde tutto ai nemici, alleati sempre visibili |\n| 10 | Try Your Luck | roulette rosso/verde 50/50 |\n| 11 | Vote Player | tutti gli umani + totale voti; self-vote consentito |",
)
readme = readme.replace(
    "In 1 HP e FULL HP compare un **Halo pubblico** sopra al player, visibile a entrambe le squadre e indipendente da Crouch Privacy. L'Halo usa il valore `Global.RGB` presente quando viene creato e segue il player senza un loop di ricreazione.",
    "Gli indicatori sono pubblici e indipendenti da Crouch Privacy: **1 HP usa Warning rosso**, mentre **FULL HP usa Halo RGB**. Quando si passa da una modalità all'altra l'icona viene sostituita.",
)
README.write_text(readme, encoding="utf-8")

validation = VALIDATION.read_text(encoding="utf-8")
validation = validation.replace("11 menu", "12 menu")
if "Menu 11 Vote Player" not in validation:
    validation += "\n- Menu 11 Vote Player: lista soli umani (self-vote consentito), un voto attivo per player, conteggio event-driven, leader HUD solo se unico, pareggio = nessun leader; diagnostics separato sotto con una riga vuota;\n- Unkillable: 1 HP usa Warning rosso, FULL HP usa Halo RGB e il cambio modalità sostituisce l'icona;\n"
new_blob = git_blob_sha(SOURCE)
validation, count = re.subn(
    r"(?s)(Blob Git del sorgente Workshop validato:\s*```text\s*)[0-9a-f]{40}(\s*```)",
    rf"\g<1>{new_blob}\g<2>",
    validation,
    count=1,
)
if count != 1:
    raise RuntimeError("validation blob not found")
VALIDATION.write_text(validation, encoding="utf-8")
