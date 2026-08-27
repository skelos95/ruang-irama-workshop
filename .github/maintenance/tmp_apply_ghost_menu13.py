from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
WORKSHOP = ROOT / "workshop" / "ruang_irama.it-IT.workshop"
SEMANTIC = ROOT / "tests" / "fixtures" / "semantic_reference.txt"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
VERSION = ROOT / "VERSION"
README = ROOT / "README.md"
CHANGELOG = ROOT / "CHANGELOG.md"
PROGETTO = ROOT / "docs" / "PROGETTO.md"
VALIDAZIONE = ROOT / "docs" / "VALIDAZIONE.md"
TEST_DOC = ROOT / "docs" / "TEST.md"


def replace_exact(text: str, old: str, new: str, *, count: int = 1, label: str = "") -> str:
    found = text.count(old)
    if found != count:
        raise SystemExit(f"{label or old[:80]!r}: expected {count} occurrence(s), found {found}")
    return text.replace(old, new)


def rule_span(text: str, title: str) -> tuple[int, int]:
    match = re.search(rf'(?:regola|rule)\("{re.escape(title)}"\)\s*\{{', text)
    if not match:
        raise SystemExit(f"rule not found: {title}")
    start = match.start()
    brace = text.find("{", match.start())
    depth = 0
    in_string = False
    escaped = False
    for i in range(brace, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
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
                return start, i + 1
    raise SystemExit(f"unterminated rule: {title}")


def patch_rule(text: str, title: str, old: str, new: str, *, count: int = 1, label: str = "") -> str:
    start, end = rule_span(text, title)
    block = text[start:end]
    updated = replace_exact(block, old, new, count=count, label=label or title)
    return text[:start] + updated + text[end:]


def insert_after_rule(text: str, title: str, block: str) -> str:
    start, end = rule_span(text, title)
    return text[:end] + "\n\n" + block.strip() + text[end:]


def menu_renderer_block(it: bool) -> str:
    rule_kw = "regola" if it else "rule"
    event_kw = "evento" if it else "event"
    actions_kw = "azioni" if it else "actions"
    return f'''{rule_kw}("91s - Subrutin: Gambar mode hantu")
{{
\t{event_kw}
\t{{
\t\tSubroutine;
\t\tGambarModeHantu;
\t}}

\t{actions_kw}
\t{{
\t\tCreate HUD Text(Event Player, Null, Event Player.IndeksBahasa == 0 ? Custom String("{{0}}\\n{{1}}", Custom String("Hold CROUCH + command\\n{{0}}: next | {{1}}: previous", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire))), Custom String("{{0}}\\n{{1}}", Custom String("{{0}}: apply | {{1}}: back", Input Binding String(Button(Interact)), Input Binding String(Button(Reload))), Custom String("Hold {{0}} 0.5 sec: close", Input Binding String(Button(Melee))))) : Event Player.IndeksBahasa == 1 ? Custom String("{{0}}\\n{{1}}", Custom String("Tahan JONGKOK + perintah\\n{{0}}: berikutnya | {{1}}: sebelumnya", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire))), Custom String("{{0}}\\n{{1}}", Custom String("{{0}}: pakai | {{1}}: kembali", Input Binding String(Button(Interact)), Input Binding String(Button(Reload))), Custom String("Tahan {{0}} 0,5 dtk: tutup", Input Binding String(Button(Melee))))) : Custom String("{{0}}\\n{{1}}", Custom String("กด ย่อ + คำสั่ง\\n{{0}}: ถัดไป | {{1}}: ก่อนหน้า", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire))), Custom String("{{0}}\\n{{1}}", Custom String("{{0}}: ใช้ | {{1}}: กลับ", Input Binding String(Button(Interact)), Input Binding String(Button(Reload))), Custom String("กด {{0}} ค้าง 0.5 วินาที: ปิด", Input Binding String(Button(Melee))))), Event Player.IndeksBahasa == 0 ? Custom String("{{0}}\\n> {{1}}", Custom String("13 - GHOST MODE {{0}}/2\\nCURRENT: {{1}}", Event Player.KursorModeHantu + 1, Event Player.ModeHantuAktif ? Custom String("ON") : Custom String("OFF")), Event Player.KursorModeHantu == 1 ? Custom String("ON - PASS THROUGH WALLS") : Custom String("OFF - NORMAL WALLS")) : Event Player.IndeksBahasa == 1 ? Custom String("{{0}}\\n> {{1}}", Custom String("13 - MODE HANTU {{0}}/2\\nSAAT INI: {{1}}", Event Player.KursorModeHantu + 1, Event Player.ModeHantuAktif ? Custom String("AKTIF") : Custom String("MATI")), Event Player.KursorModeHantu == 1 ? Custom String("AKTIF - TEMBUS DINDING") : Custom String("MATI - DINDING NORMAL")) : Custom String("{{0}}\\n> {{1}}", Custom String("13 - โหมดผี {{0}}/2\\nสถานะ: {{1}}", Event Player.KursorModeHantu + 1, Event Player.ModeHantuAktif ? Custom String("เปิด") : Custom String("ปิด")), Event Player.KursorModeHantu == 1 ? Custom String("เปิด - ทะลุกำแพง") : Custom String("ปิด - ชนกำแพงปกติ")), Top, 3, Custom Color(255, 255, 255, 255), Custom Color(220, 235, 255, 255), Custom Color(X Component Of(Event Player.WarnaMenu), Y Component Of(Event Player.WarnaMenu), Z Component Of(Event Player.WarnaMenu), 255), Visible To String and Color, Visible Never);
\t\tEvent Player.HudMenu = Last Text ID;
\t}}
}}'''


def apply_block(it: bool) -> str:
    rule_kw = "regola" if it else "rule"
    event_kw = "evento" if it else "event"
    actions_kw = "azioni" if it else "actions"
    return f'''{rule_kw}("99n - Subrutin: Terapkan mode hantu")
{{
\t{event_kw}
\t{{
\t\tSubroutine;
\t\tTerapkanModeHantu;
\t}}

\t{actions_kw}
\t{{
\t\tIf(Event Player.ModeHantuAktif != (Event Player.KursorModeHantu == 1));
\t\t\tEvent Player.ModeHantuAktif = Event Player.KursorModeHantu == 1;
\t\t\tIf(Event Player.ModeHantuAktif == True);
\t\t\t\tDisable Movement Collision With Environment(Event Player, False);
\t\t\t\tCall Subroutine(EfekTerapkan);
\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Ghost Mode enabled. Walls and ceilings are pass-through; floors stay solid.") : Event Player.IndeksBahasa == 1 ? Custom String("Mode Hantu aktif. Dinding dan plafon bisa ditembus; lantai tetap padat.") : Custom String("เปิดโหมดผีแล้ว ทะลุกำแพงและเพดานได้ แต่พื้นยังชนตามปกติ"));
\t\t\tElse;
\t\t\t\tEnable Movement Collision With Environment(Event Player);
\t\t\t\tCall Subroutine(EfekPulihkan);
\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Ghost Mode disabled. Normal wall collision restored.") : Event Player.IndeksBahasa == 1 ? Custom String("Mode Hantu nonaktif. Tabrakan dinding normal dipulihkan.") : Custom String("ปิดโหมดผีแล้ว กลับมาชนกำแพงตามปกติ"));
\t\t\tEnd;
\t\tEnd;
\t}}
}}'''


def respawn_block(it: bool) -> str:
    rule_kw = "regola" if it else "rule"
    event_kw = "evento" if it else "event"
    cond_kw = "condizioni" if it else "conditions"
    actions_kw = "azioni" if it else "actions"
    all_kw = "Tutti" if it else "All"
    return f'''{rule_kw}("03d - Mode Hantu: Pulihkan tembus dinding setelah respawn")
{{
\t{event_kw}
\t{{
\t\tOngoing - Each Player;
\t\t{all_kw};
\t\t{all_kw};
\t}}

\t{cond_kw}
\t{{
\t\tEvent Player.Manusia == True;
\t\tEvent Player.ModeHantuAktif == True;
\t\tHas Spawned(Event Player) == True;
\t\tIs Alive(Event Player) == True;
\t}}

\t{actions_kw}
\t{{
\t\tDisable Movement Collision With Environment(Event Player, False);
\t}}
}}'''


def patch_source(text: str, *, it: bool) -> str:
    gp = "Globale" if it else "Global"

    text = replace_exact(
        text,
        "\t\t106: SegarkanRosterTertunda\n\t\t107: NamaTampilan\n",
        "\t\t106: ModeHantuAktif\n\t\t107: NamaTampilan\n\t\t108: KursorModeHantu\n",
        label="player declarations",
    )
    text = replace_exact(
        text,
        "\t57: CariPosisiTeleportAman\n}",
        "\t57: CariPosisiTeleportAman\n\t58: GambarModeHantu\n\t59: TerapkanModeHantu\n}",
        label="subroutine declarations",
    )

    dead_if = (
        "\t\tIf(Event Player.SegarkanRosterTertunda == True);\n"
        "\t\t\tEvent Player.SegarkanRosterTertunda = False;\n"
        "\t\tEnd;\n"
    )
    text = replace_exact(text, dead_if, "", label="dead roster pending branch")
    found_dead_assignments = text.count("\t\tEvent Player.SegarkanRosterTertunda = False;\n")
    if found_dead_assignments != 2:
        raise SystemExit(f"expected 2 remaining dead roster assignments, found {found_dead_assignments}")
    text = text.replace("\t\tEvent Player.SegarkanRosterTertunda = False;\n", "")

    social_expr = f"X Component Of({gp}.ProfilSosial[Index Of Array Value({gp}.ProfilNama, Event Player.NamaTampilan)])"
    text = patch_rule(
        text,
        "02 - Pemain: Pisahkan manusia dari pasukan kaleng",
        f"\t\t\tEvent Player.IzinkanDummyMengikuti = {social_expr} == 1;\n",
        f"\t\t\tEvent Player.IzinkanDummyMengikuti = {social_expr} % 2 == 1;\n\t\t\tEvent Player.ModeHantuAktif = {social_expr} >= 2;\n",
        label="profile unpack",
    )
    text = patch_rule(
        text,
        "02 - Pemain: Pisahkan manusia dari pasukan kaleng",
        "\t\t\tEvent Player.KursorIkutiDummy = Event Player.IzinkanDummyMengikuti ? 1 : 0;\n",
        "\t\t\tEvent Player.KursorIkutiDummy = Event Player.IzinkanDummyMengikuti ? 1 : 0;\n\t\t\tEvent Player.KursorModeHantu = Event Player.ModeHantuAktif ? 1 : 0;\n",
        label="profile ghost cursor",
    )
    packed_old = "Vector(Event Player.IzinkanDummyMengikuti ? 1 : 0, Event Player.JumlahPilihan, Event Player.KursorKamera)"
    packed_new = "Vector((Event Player.IzinkanDummyMengikuti ? 1 : 0) + (Event Player.ModeHantuAktif ? 2 : 0), Event Player.JumlahPilihan, Event Player.KursorKamera)"
    text = replace_exact(text, packed_old, packed_new, count=3, label="packed social profile")

    text = patch_rule(
        text,
        "02 - Pemain: Pisahkan manusia dari pasukan kaleng",
        "\t\tEvent Player.MenitLobi = Max(0, Round To Integer((Total Time Elapsed - Event Player.WaktuMasuk) / 60, Down));\n",
        "\t\tIf(Event Player.ModeHantuAktif == True);\n\t\t\tDisable Movement Collision With Environment(Event Player, False);\n\t\tElse;\n\t\t\tEnable Movement Collision With Environment(Event Player);\n\t\tEnd;\n\t\tEvent Player.MenitLobi = Max(0, Round To Integer((Total Time Elapsed - Event Player.WaktuMasuk) / 60, Down));\n",
        label="profile engine restore",
    )

    text = patch_rule(
        text,
        "05 - Menu: Tahan serangan jarak dekat 0,5 detik untuk buka atau tutup",
        "Thirteen extremely important decisions await.",
        "Fourteen extremely important decisions await.",
        label="menu open EN count",
    )
    text = patch_rule(text, "05 - Menu: Tahan serangan jarak dekat 0,5 detik untuk buka atau tutup", "Tiga belas keputusan yang sangat penting menunggu.", "Empat belas keputusan yang sangat penting menunggu.", label="menu open ID count")
    text = patch_rule(text, "05 - Menu: Tahan serangan jarak dekat 0,5 detik untuk buka atau tutup", "มีสิบสามตัวเลือกสำคัญรอคุณอยู่", "มีสิบสี่ตัวเลือกสำคัญรอคุณอยู่", label="menu open TH count")

    text = patch_rule(
        text,
        "06 - Menu: Navigasi berikutnya dan sebelumnya",
        "Event Player.KursorUtama = (Event Player.KursorUtama + (Event Player.PerintahMenu == 3 ? 1 : 12)) % 13;",
        "Event Player.KursorUtama = (Event Player.KursorUtama + (Event Player.PerintahMenu == 3 ? 1 : 13)) % 14;",
        label="main menu cycle",
    )
    text = patch_rule(
        text,
        "06 - Menu: Navigasi berikutnya dan sebelumnya",
        "\t\tElse If(Event Player.HalamanMenu == 12);\n\t\t\tEvent Player.KursorIkutiDummy = (Event Player.KursorIkutiDummy + 1) % 2;\n\t\tEnd;",
        "\t\tElse If(Event Player.HalamanMenu == 12);\n\t\t\tEvent Player.KursorIkutiDummy = (Event Player.KursorIkutiDummy + 1) % 2;\n\t\tElse If(Event Player.HalamanMenu == 13);\n\t\t\tEvent Player.KursorModeHantu = (Event Player.KursorModeHantu + 1) % 2;\n\t\tEnd;",
        label="ghost navigation",
    )

    text = patch_rule(
        text,
        "10 - Menu: Terapkan halaman aktif",
        "\t\t\tElse If(Event Player.HalamanMenu == 12);\n\t\t\t\tEvent Player.KursorIkutiDummy = Event Player.IzinkanDummyMengikuti ? 1 : 0;\n\t\t\tEnd;",
        "\t\t\tElse If(Event Player.HalamanMenu == 12);\n\t\t\t\tEvent Player.KursorIkutiDummy = Event Player.IzinkanDummyMengikuti ? 1 : 0;\n\t\t\tElse If(Event Player.HalamanMenu == 13);\n\t\t\t\tEvent Player.KursorModeHantu = Event Player.ModeHantuAktif ? 1 : 0;\n\t\t\tEnd;",
        label="ghost page entry cursor",
    )
    text = patch_rule(
        text,
        "10 - Menu: Terapkan halaman aktif",
        "\t\tElse If(Event Player.HalamanMenu == 12);\n\t\t\tCall Subroutine(TerapkanHalamanIkutiDummy);\n\t\tEnd;",
        "\t\tElse If(Event Player.HalamanMenu == 12);\n\t\t\tCall Subroutine(TerapkanHalamanIkutiDummy);\n\t\tElse If(Event Player.HalamanMenu == 13);\n\t\t\tCall Subroutine(TerapkanModeHantu);\n\t\tEnd;",
        label="ghost apply routing",
    )

    # Extend the three localized tails of the large main-menu renderer without adding a second HUD handle.
    text = patch_rule(
        text,
        "91a - Subrutin: Gambar menu utama",
        'Event Player.KursorUtama == 11 ? Custom String("11 - VOTE PLAYER\\nYOUR VOTE: {0}", Event Player.PemainDipilih != Null ? Event Player.PemainDipilih : Custom String("NONE")) : Custom String("12 - DUMMY FOLLOW\\nCURRENT: {0}", Event Player.IzinkanDummyMengikuti ? Custom String("ON") : Custom String("OFF"))',
        'Event Player.KursorUtama == 11 ? Custom String("11 - VOTE PLAYER\\nYOUR VOTE: {0}", Event Player.PemainDipilih != Null ? Event Player.PemainDipilih : Custom String("NONE")) : Event Player.KursorUtama == 12 ? Custom String("12 - DUMMY FOLLOW\\nCURRENT: {0}", Event Player.IzinkanDummyMengikuti ? Custom String("ON") : Custom String("OFF")) : Custom String("13 - GHOST MODE\\nCURRENT: {0}", Event Player.ModeHantuAktif ? Custom String("ON") : Custom String("OFF"))',
        label="main renderer EN ghost",
    )
    text = patch_rule(
        text,
        "91a - Subrutin: Gambar menu utama",
        'Event Player.KursorUtama == 11 ? Custom String("11 - PILIH PEMAIN\\nPILIHAN KAMU: {0}", Event Player.PemainDipilih != Null ? Event Player.PemainDipilih : Custom String("BELUM ADA")) : Custom String("12 - DUMMY MENGIKUTI\\nSAAT INI: {0}", Event Player.IzinkanDummyMengikuti ? Custom String("AKTIF") : Custom String("MATI"))',
        'Event Player.KursorUtama == 11 ? Custom String("11 - PILIH PEMAIN\\nPILIHAN KAMU: {0}", Event Player.PemainDipilih != Null ? Event Player.PemainDipilih : Custom String("BELUM ADA")) : Event Player.KursorUtama == 12 ? Custom String("12 - DUMMY MENGIKUTI\\nSAAT INI: {0}", Event Player.IzinkanDummyMengikuti ? Custom String("AKTIF") : Custom String("MATI")) : Custom String("13 - MODE HANTU\\nSAAT INI: {0}", Event Player.ModeHantuAktif ? Custom String("AKTIF") : Custom String("MATI"))',
        label="main renderer ID ghost",
    )
    text = patch_rule(
        text,
        "91a - Subrutin: Gambar menu utama",
        'Event Player.KursorUtama == 11 ? Custom String("11 - โหวตผู้เล่น\\nโหวตของคุณ: {0}", Event Player.PemainDipilih != Null ? Event Player.PemainDipilih : Custom String("ยังไม่ได้โหวต")) : Custom String("12 - ดัมมี่ติดตาม\\nสถานะ: {0}", Event Player.IzinkanDummyMengikuti ? Custom String("เปิด") : Custom String("ปิด"))',
        'Event Player.KursorUtama == 11 ? Custom String("11 - โหวตผู้เล่น\\nโหวตของคุณ: {0}", Event Player.PemainDipilih != Null ? Event Player.PemainDipilih : Custom String("ยังไม่ได้โหวต")) : Event Player.KursorUtama == 12 ? Custom String("12 - ดัมมี่ติดตาม\\nสถานะ: {0}", Event Player.IzinkanDummyMengikuti ? Custom String("เปิด") : Custom String("ปิด")) : Custom String("13 - โหมดผี\\nสถานะ: {0}", Event Player.ModeHantuAktif ? Custom String("เปิด") : Custom String("ปิด"))',
        label="main renderer TH ghost",
    )

    text = patch_rule(
        text,
        "91p - Subrutin: Gambar halaman aktif",
        "\t\tElse If(Event Player.HalamanMenu == 12);\n\t\t\tCall Subroutine(GambarIkutiDummy);\n\t\tEnd;",
        "\t\tElse If(Event Player.HalamanMenu == 12);\n\t\t\tCall Subroutine(GambarIkutiDummy);\n\t\tElse If(Event Player.HalamanMenu == 13);\n\t\t\tCall Subroutine(GambarModeHantu);\n\t\tEnd;",
        label="ghost renderer routing",
    )

    text = patch_rule(
        text,
        "91k - Subrutin: Transisi warna menu tanpa lompatan",
        f"(Event Player.HalamanMenu == -1 ? Event Player.KursorUtama : Event Player.HalamanMenu) == 12 ? {gp}.DaftarWarnaRGB[Event Player.IndeksWarna] * 0.700 + Vector(70, 220, 175) * 0.300 : {gp}.DaftarWarnaRGB[Event Player.IndeksWarna]",
        f"(Event Player.HalamanMenu == -1 ? Event Player.KursorUtama : Event Player.HalamanMenu) == 12 ? {gp}.DaftarWarnaRGB[Event Player.IndeksWarna] * 0.700 + Vector(70, 220, 175) * 0.300 : (Event Player.HalamanMenu == -1 ? Event Player.KursorUtama : Event Player.HalamanMenu) == 13 ? {gp}.DaftarWarnaRGB[Event Player.IndeksWarna] * 0.720 + Vector(175, 220, 255) * 0.280 : {gp}.DaftarWarnaRGB[Event Player.IndeksWarna]",
        label="ghost menu tint",
    )

    text = patch_rule(
        text,
        "89a - Subrutin: Proses status cepat pemain",
        f"\t\t\t{gp}.PemainAktif.PahlawanTerakhir = Hero Of({gp}.PemainAktif);\n",
        f"\t\t\t{gp}.PemainAktif.PahlawanTerakhir = Hero Of({gp}.PemainAktif);\n\t\t\tIf({gp}.PemainAktif.ModeHantuAktif == True);\n\t\t\t\tDisable Movement Collision With Environment({gp}.PemainAktif, False);\n\t\t\tElse;\n\t\t\t\tEnable Movement Collision With Environment({gp}.PemainAktif);\n\t\t\tEnd;\n",
        label="ghost hero-change restore",
    )

    text = patch_rule(
        text,
        "93b2 - Subrutin: Tenangkan pemicu sebelum pembersihan",
        "\t\tEvent Player.IzinkanDummyMengikuti = False;\n",
        "\t\tEvent Player.IzinkanDummyMengikuti = False;\n\t\tEvent Player.ModeHantuAktif = False;\n\t\tEvent Player.KursorModeHantu = 0;\n\t\tEnable Movement Collision With Environment(Event Player);\n",
        label="ghost heavy cleanup",
    )
    text = patch_rule(
        text,
        "94 - Subrutin: Siapkan pemain dari ujung rambut sampai variabel",
        "\t\tEnable Movement Collision With Players(Event Player);\n",
        "\t\tEnable Movement Collision With Players(Event Player);\n\t\tEnable Movement Collision With Environment(Event Player);\n",
        label="ghost setup engine baseline",
    )
    text = patch_rule(
        text,
        "94 - Subrutin: Siapkan pemain dari ujung rambut sampai variabel",
        "\t\tEvent Player.IzinkanDummyMengikuti = False;\n\t\tEvent Player.KursorIkutiDummy = 0;\n",
        "\t\tEvent Player.IzinkanDummyMengikuti = False;\n\t\tEvent Player.KursorIkutiDummy = 0;\n\t\tEvent Player.ModeHantuAktif = False;\n\t\tEvent Player.KursorModeHantu = 0;\n",
        label="ghost setup variables",
    )

    text = insert_after_rule(text, "03c - Bot/Dummy: Kunci saat hidup kembali atau pahlawan berganti", respawn_block(it))
    text = insert_after_rule(text, "91r - Subrutin: Gambar izin dummy mengikuti", menu_renderer_block(it))
    text = insert_after_rule(text, "99m - Subrutin: Terapkan izin dummy mengikuti", apply_block(it))

    if "SegarkanRosterTertunda" in text:
        raise SystemExit("dead SegarkanRosterTertunda survived patch")
    for token in ("ModeHantuAktif", "KursorModeHantu", "GambarModeHantu", "TerapkanModeHantu", "13 - GHOST MODE"):
        if token not in text:
            raise SystemExit(f"ghost token missing after patch: {token}")
    return text


def patch_validator(text: str) -> str:
    text = replace_exact(text, 'Workshop 0.8.1.', 'Workshop 0.8.2.', label='validator doc version')
    text = replace_exact(text, 'CURRENT_VERSION = "0.8.1"', 'CURRENT_VERSION = "0.8.2"', label='validator current version')
    text = replace_exact(
        text,
        '    "TerapkanHalamanIkutiDummy",\n}',
        '    "TerapkanHalamanIkutiDummy",\n    "TerapkanModeHantu",\n}',
        label='validator page apply set',
    )
    text = replace_exact(text, 'checks.equal(len(arcade_renderers), 14, "renderer menu principale + pagine 0..12")', 'checks.equal(len(arcade_renderers), 15, "renderer menu principale + pagine 0..13")', label='renderer count')
    text = replace_exact(text, 'for page in range(13):', 'for page in range(14):', count=1, label='router page range')
    text = replace_exact(
        text,
        '            re.search(r"HalamanMenu\\s*==\\s*12.*?Call Subroutine\\(GambarIkutiDummy\\);", router.body, re.DOTALL) is not None,\n            "router menu: pagina 12 deve aprire Dummy Follow",\n        )',
        '            re.search(r"HalamanMenu\\s*==\\s*12.*?Call Subroutine\\(GambarIkutiDummy\\);", router.body, re.DOTALL) is not None,\n            "router menu: pagina 12 deve aprire Dummy Follow",\n        )\n        checks.require(\n            re.search(r"HalamanMenu\\s*==\\s*13.*?Call Subroutine\\(GambarModeHantu\\);", router.body, re.DOTALL) is not None,\n            "router menu: pagina 13 deve aprire Ghost Mode",\n        )',
        label='validator ghost router',
    )
    text = replace_exact(
        text,
        '            "12 - DUMMY FOLLOW",\n            "0 - WARNA NAMA",',
        '            "12 - DUMMY FOLLOW",\n            "13 - GHOST MODE",\n            "0 - WARNA NAMA",',
        label='validator main EN ghost',
    )
    text = replace_exact(
        text,
        '            "12 - DUMMY MENGIKUTI",\n            "0 - สีชื่อ",',
        '            "12 - DUMMY MENGIKUTI",\n            "13 - MODE HANTU",\n            "0 - สีชื่อ",',
        label='validator main ID ghost',
    )
    text = replace_exact(
        text,
        '            "12 - ดัมมี่ติดตาม",\n        ):',
        '            "12 - ดัมมี่ติดตาม",\n            "13 - โหมดผี",\n        ):',
        label='validator main TH ghost',
    )
    text = replace_exact(
        text,
        '            "Event Player.KursorUtama = (Event Player.KursorUtama + (Event Player.PerintahMenu == 3 ? 1 : 12)) % 13;"\n            in navigation_rule.body,\n            "navigazione menu principale non usa ciclo esatto 0..12",',
        '            "Event Player.KursorUtama = (Event Player.KursorUtama + (Event Player.PerintahMenu == 3 ? 1 : 13)) % 14;"\n            in navigation_rule.body,\n            "navigazione menu principale non usa ciclo esatto 0..13",',
        label='validator main cycle',
    )
    text = replace_exact(
        text,
        '            "navigazione menu: pagina 12 deve alternare KursorIkutiDummy",\n        )',
        '            "navigazione menu: pagina 12 deve alternare KursorIkutiDummy",\n        )\n        checks.require(\n            re.search(\n                r"HalamanMenu\\s*==\\s*13.*?KursorModeHantu\\s*=\\s*"\n                r"\\(Event Player\\.KursorModeHantu\\s*\\+\\s*1\\)\\s*%\\s*2;",\n                navigation_rule.body,\n                re.DOTALL,\n            ) is not None,\n            "navigazione menu: pagina 13 deve alternare KursorModeHantu",\n        )',
        label='validator ghost navigation',
    )

    anchor = '    dummy_follow_renderer = rule_by_subroutine(rules, "GambarIkutiDummy")\n'
    if anchor not in text:
        raise SystemExit('validator ghost anchor missing')
    ghost_checks = '''    checks.require("SegarkanRosterTertunda" not in source,\n                   "variabile legacy SegarkanRosterTertunda deve essere rimossa")\n    for name in ("ModeHantuAktif", "KursorModeHantu"):\n        checks.require(name in players, f"stato Ghost Mode assente: {name}")\n    checks.require("GambarModeHantu" in subroutines and "TerapkanModeHantu" in subroutines,\n                   "subroutine Ghost Mode assenti")\n    ghost_renderer = rule_by_subroutine(rules, "GambarModeHantu")\n    checks.require(ghost_renderer is not None, "renderer pagina 13 Ghost Mode assente")\n    if ghost_renderer:\n        for token in ("13 - GHOST MODE", "13 - MODE HANTU", "13 - โหมดผี", "KursorModeHantu", "ModeHantuAktif"):\n            checks.require(token in ghost_renderer.body, f"pagina 13 Ghost Mode incompleta: {token}")\n    ghost_apply = rule_by_subroutine(rules, "TerapkanModeHantu")\n    checks.require(ghost_apply is not None, "apply Ghost Mode assente")\n    if ghost_apply:\n        checks.require("Disable Movement Collision With Environment(Event Player, False);" in ghost_apply.body,\n                       "Ghost Mode ON deve disabilitare pareti/soffitti mantenendo i pavimenti")\n        checks.require("Enable Movement Collision With Environment(Event Player);" in ghost_apply.body,\n                       "Ghost Mode OFF deve ripristinare collisione ambiente")\n    ghost_respawn = next((rule for rule in rules if rule.name.startswith("03d - Mode Hantu:")), None)\n    checks.require(ghost_respawn is not None, "ripristino Ghost Mode dopo respawn assente")\n    if ghost_respawn:\n        checks.require("Event Player.ModeHantuAktif == True;" in ghost_respawn.body\n                       and "Disable Movement Collision With Environment(Event Player, False);" in ghost_respawn.body,\n                       "ripristino Ghost Mode dopo respawn incompleto")\n    checks.require("(Event Player.IzinkanDummyMengikuti ? 1 : 0) + (Event Player.ModeHantuAktif ? 2 : 0)" in source,\n                   "profilo persistente non salva Ghost Mode")\n    checks.require("X Component Of(Global.ProfilSosial" in source and "% 2 == 1" in source and ">= 2" in source,\n                   "profilo persistente non separa Dummy Follow e Ghost Mode")\n\n'''
    text = text.replace(anchor, ghost_checks + anchor, 1)
    return text


def patch_docs() -> None:
    VERSION.write_text("0.8.2\n", encoding="utf-8")

    readme = README.read_text(encoding="utf-8")
    readme = readme.replace("Versione: **0.8.1**", "Versione: **0.8.2**")
    readme = readme.replace("La 0.8.1 ha superato", "La 0.8.2 ha superato")
    readme = readme.replace("- 13 menu Arcade con preferenze individuali.", "- 14 menu Arcade con preferenze individuali.")
    readme = readme.replace("## I 13 menu", "## I 14 menu")
    readme = readme.replace("Gli indici sono Main Menu `-1` e sottomenu `0..12`.", "Gli indici sono Main Menu `-1` e sottomenu `0..13`.")
    readme = readme.replace("| 12 | Dummy Follow | consente o nega al dummy nemico di seguire il player; default OFF |", "| 12 | Dummy Follow | consente o nega al dummy nemico di seguire il player; default OFF |\n| 13 | Ghost Mode | OFF / ON; con ON attraversa pareti e soffitti, mantenendo solidi i pavimenti |")
    readme = readme.replace("## Runtime 0.8.1", "## Runtime 0.8.2")
    readme = readme.replace("Il sorgente mantiene un solo `Loop` e al massimo **7 `Wait`** nominativamente autorizzati per ruolo, durata e quantità.", "Il sorgente non usa `Loop` e mantiene **5 `Wait`** nominativamente autorizzati per ruolo, durata e quantità.")
    README.write_text(readme, encoding="utf-8")

    changelog = CHANGELOG.read_text(encoding="utf-8")
    entry = '''## 0.8.2\n\n- Aggiunto **Menu 13 — Ghost Mode**: OFF ripristina la collisione ambiente normale; ON usa `Disable Movement Collision With Environment(..., False)` per attraversare pareti e soffitti mantenendo solidi i pavimenti. Lo stato viene riapplicato dopo respawn/cambio eroe e conservato nel profilo durante i cambi squadra senza aggiungere un nuovo array globale.\n- Audit completo del sorgente: nessun titolo regola duplicato e nessun corpo regola duplicato identico. Rimossa la variabile legacy `SegarkanRosterTertunda`, rimasta dal vecchio lifecycle HUD ma mai più armata dopo il passaggio agli slot HUD globali.\n- Aggiornati router, localizzazioni EN/ID/TH, validator, documentazione e conteggi runtime; restano 0 `Loop` e 5 `Wait`.\n\n'''
    if "## 0.8.2" not in changelog:
        changelog = entry + changelog
    CHANGELOG.write_text(changelog, encoding="utf-8")

    for path in (PROGETTO, VALIDAZIONE, TEST_DOC):
        doc = path.read_text(encoding="utf-8")
        doc = doc.replace("0.8.1", "0.8.2")
        doc = doc.replace("0..12", "0..13")
        doc = doc.replace("13 menu", "14 menu")
        doc = doc.replace("tredici menu", "quattordici menu")
        doc = doc.replace("un solo `Loop`", "nessun `Loop`")
        doc = doc.replace("al massimo **7 `Wait`**", "**5 `Wait`**")
        path.write_text(doc, encoding="utf-8")


def patch_tests() -> None:
    for path in (ROOT / "tests" / "test_validate_workshop.py", ROOT / "tests" / "test_runtime_maintenance.py", ROOT / "tests" / "test_dummy_bots.py"):
        text = path.read_text(encoding="utf-8")
        text = text.replace("0.8.1", "0.8.2")
        text = text.replace("0..12", "0..13")
        text = text.replace("% 13", "% 14") if "KursorUtama" in text else text
        text = text.replace("? 1 : 12)) % 13", "? 1 : 13)) % 14")
        text = text.replace("range(13)", "range(14)")
        text = text.replace("renderer menu principale + pagine 0..12", "renderer menu principale + pagine 0..13")
        path.write_text(text, encoding="utf-8")


def main() -> None:
    WORKSHOP.write_text(patch_source(WORKSHOP.read_text(encoding="utf-8"), it=True), encoding="utf-8")
    SEMANTIC.write_text(patch_source(SEMANTIC.read_text(encoding="utf-8"), it=False), encoding="utf-8")
    VALIDATOR.write_text(patch_validator(VALIDATOR.read_text(encoding="utf-8")), encoding="utf-8")
    patch_docs()
    patch_tests()

    # Final cheap consistency checks before the real validator/test suite.
    it = WORKSHOP.read_text(encoding="utf-8")
    en = SEMANTIC.read_text(encoding="utf-8")
    if it.count('regola("') != en.count('rule("'):
        raise SystemExit(f"rule count mismatch it={it.count('regola(\"')} en={en.count('rule(\"')}")
    if "SegarkanRosterTertunda" in it or "SegarkanRosterTertunda" in en:
        raise SystemExit("legacy variable still present")
    print("patched rules", it.count('regola("'))
    print("workshop bytes", len(it.encode("utf-8")))
    print("semantic bytes", len(en.encode("utf-8")))
    print("wait count", it.count("Wait("), "loop count", it.count("Loop;"))
    print("ghost disable count", it.count("Disable Movement Collision With Environment"))
    print("ghost enable count", it.count("Enable Movement Collision With Environment"))


if __name__ == "__main__":
    main()
