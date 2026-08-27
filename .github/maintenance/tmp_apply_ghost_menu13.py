from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IT = ROOT / "workshop" / "ruang_irama.it-IT.workshop"
EN = ROOT / "tests" / "fixtures" / "semantic_reference.txt"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"missing token for {label}: {old[:180]!r}")
    if text.count(old) != 1:
        raise RuntimeError(f"non-unique token for {label}: {text.count(old)}")
    return text.replace(old, new, 1)


def replace_all_expected(text: str, old: str, new: str, expected: int, label: str) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"{label}: expected {expected}, got {count}")
    return text.replace(old, new)


def ghost_render_rule(rule_kw: str, event_kw: str, actions_kw: str) -> str:
    return f'''{rule_kw}("91s - Subrutin: Gambar Ghost Mode")
{{
\t{event_kw}
\t{{
\t\tSubroutine;
\t\tGambarGhost;
\t}}

\t{actions_kw}
\t{{
\t\tCreate HUD Text(Event Player, Null, Event Player.IndeksBahasa == 0 ? Custom String("{{0}}\\n{{1}}", Custom String("Hold CROUCH + command\\n{{0}}: next | {{1}}: previous", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire))), Custom String("{{0}}: apply | {{1}}: back", Input Binding String(Button(Interact)), Input Binding String(Button(Reload)))) : Event Player.IndeksBahasa == 1 ? Custom String("{{0}}\\n{{1}}", Custom String("Tahan JONGKOK + perintah\\n{{0}}: berikutnya | {{1}}: sebelumnya", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire))), Custom String("{{0}}: pakai | {{1}}: kembali", Input Binding String(Button(Interact)), Input Binding String(Button(Reload)))) : Custom String("{{0}}\\n{{1}}", Custom String("กด ย่อ + คำสั่ง\\n{{0}}: ถัดไป | {{1}}: ก่อนหน้า", Input Binding String(Button(Primary Fire)), Input Binding String(Button(Secondary Fire))), Custom String("{{0}}: ใช้ | {{1}}: กลับ", Input Binding String(Button(Interact)), Input Binding String(Button(Reload)))), Event Player.IndeksBahasa == 0 ? Custom String("{{0}}\\n> {{1}}", Custom String("13 - GHOST MODE {{0}}/2\\nCURRENT: {{1}}", Event Player.KursorGhost + 1, Event Player.GhostAktif ? Custom String("ON") : Custom String("OFF")), Event Player.KursorGhost == 1 ? Custom String("ON - WALLS OFF") : Custom String("OFF - NORMAL COLLISION")) : Event Player.IndeksBahasa == 1 ? Custom String("{{0}}\\n> {{1}}", Custom String("13 - MODE GHOST {{0}}/2\\nSAAT INI: {{1}}", Event Player.KursorGhost + 1, Event Player.GhostAktif ? Custom String("AKTIF") : Custom String("MATI")), Event Player.KursorGhost == 1 ? Custom String("AKTIF - TEMBOK TEMBUS") : Custom String("MATI - TABRAKAN NORMAL")) : Custom String("{{0}}\\n> {{1}}", Custom String("13 - โหมดผี {{0}}/2\\nสถานะ: {{1}}", Event Player.KursorGhost + 1, Event Player.GhostAktif ? Custom String("เปิด") : Custom String("ปิด")), Event Player.KursorGhost == 1 ? Custom String("เปิด - ทะลุกำแพง") : Custom String("ปิด - ชนปกติ")), Top, 3, Custom Color(255, 255, 255, 255), Custom Color(205, 245, 255, 255), Custom Color(X Component Of(Event Player.WarnaMenu), Y Component Of(Event Player.WarnaMenu), Z Component Of(Event Player.WarnaMenu), 255), Visible To String and Color, Visible Never);
\t\tEvent Player.HudMenu = Last Text ID;
\t}}
}}

'''


def ghost_apply_rule(rule_kw: str, event_kw: str, actions_kw: str) -> str:
    return f'''{rule_kw}("99n - Subrutin: Terapkan Ghost Mode")
{{
\t{event_kw}
\t{{
\t\tSubroutine;
\t\tTerapkanHalamanGhost;
\t}}

\t{actions_kw}
\t{{
\t\tIf(Event Player.GhostAktif != (Event Player.KursorGhost == 1));
\t\t\tEvent Player.GhostAktif = Event Player.KursorGhost == 1;
\t\t\tIf(Event Player.GhostAktif == True);
\t\t\t\tDisable Movement Collision With Environment(Event Player, False);
\t\t\t\tCall Subroutine(EfekTerapkan);
\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Ghost Mode enabled. Wall and ceiling collision disabled; floors stay solid.") : Event Player.IndeksBahasa == 1 ? Custom String("Mode Ghost aktif. Tembok dan plafon bisa ditembus; lantai tetap solid.") : Custom String("เปิดโหมดผีแล้ว ทะลุกำแพงและเพดานได้ แต่พื้นยังชนปกติ"));
\t\t\tElse;
\t\t\t\tEnable Movement Collision With Environment(Event Player);
\t\t\t\tCall Subroutine(EfekPulihkan);
\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Ghost Mode disabled. Normal environment collision restored.") : Event Player.IndeksBahasa == 1 ? Custom String("Mode Ghost mati. Tabrakan lingkungan kembali normal.") : Custom String("ปิดโหมดผีแล้ว การชนกับฉากกลับเป็นปกติ"));
\t\t\tEnd;
\t\tEnd;
\t}}
}}

'''


def transform_source(text: str, *, italian: bool) -> str:
    G = "Globale" if italian else "Global"
    rule_kw = "regola" if italian else "rule"
    event_kw = "evento" if italian else "event"
    actions_kw = "azioni" if italian else "actions"

    text = replace_once(
        text,
        "\t\t106: SegarkanRosterTertunda\n\t\t107: NamaTampilan",
        "\t\t106: GhostAktif\n\t\t107: NamaTampilan\n\t\t108: KursorGhost",
        "repurpose pending var",
    )
    text = replace_once(
        text,
        "\t\t57: CariPosisiTeleportAman\n}",
        "\t\t57: CariPosisiTeleportAman\n\t\t58: GambarGhost\n\t\t59: TerapkanHalamanGhost\n}",
        "append ghost subroutines",
    )

    pending_block = "\t\tIf(Event Player.SegarkanRosterTertunda == True);\n\t\t\tEvent Player.SegarkanRosterTertunda = False;\n\t\tEnd;\n"
    text = replace_once(text, pending_block, "", "remove dead 02b pending block")

    text = replace_once(
        text,
        f"\t\t\t{G}.PemainAktif.SegarkanRosterTertunda = False;",
        f"\t\t\tIf({G}.PemainAktif.GhostAktif == True);\n\t\t\t\tDisable Movement Collision With Environment({G}.PemainAktif, False);\n\t\t\tElse;\n\t\t\t\tEnable Movement Collision With Environment({G}.PemainAktif);\n\t\t\tEnd;",
        "team-switch ghost reassert",
    )

    text = replace_once(
        text,
        f"\t\t\t{G}.PemainAktif.PahlawanTerakhir = Hero Of({G}.PemainAktif);\n\t\t\tIf(Or({G}.PemainAktif.KartuNasibAktif == True,",
        f"\t\t\t{G}.PemainAktif.PahlawanTerakhir = Hero Of({G}.PemainAktif);\n\t\t\tIf({G}.PemainAktif.GhostAktif == True);\n\t\t\t\tDisable Movement Collision With Environment({G}.PemainAktif, False);\n\t\t\tElse;\n\t\t\t\tEnable Movement Collision With Environment({G}.PemainAktif);\n\t\t\tEnd;\n\t\t\tIf(Or({G}.PemainAktif.KartuNasibAktif == True,",
        "hero-change ghost reassert",
    )

    text = replace_once(
        text,
        "\t\tEnable Movement Collision With Players(Event Player);\n\t\tEvent Player.WaktuMasuk = Total Time Elapsed;",
        "\t\tEnable Movement Collision With Players(Event Player);\n\t\tEnable Movement Collision With Environment(Event Player);\n\t\tEvent Player.WaktuMasuk = Total Time Elapsed;",
        "fresh environment normalization",
    )
    text = replace_once(
        text,
        "\t\tEvent Player.SegarkanRosterTertunda = False;\n\t\tEvent Player.NamaTampilan = Null;",
        "\t\tEvent Player.GhostAktif = False;\n\t\tEvent Player.KursorGhost = 0;\n\t\tEvent Player.NamaTampilan = Null;",
        "ghost setup defaults",
    )

    old_load = f"\t\t\tEvent Player.IzinkanDummyMengikuti = X Component Of({G}.ProfilSosial[Index Of Array Value({G}.ProfilNama, Event Player.NamaTampilan)]) == 1;"
    new_load = f"\t\t\tEvent Player.IzinkanDummyMengikuti = (X Component Of({G}.ProfilSosial[Index Of Array Value({G}.ProfilNama, Event Player.NamaTampilan)]) % 2) == 1;\n\t\t\tEvent Player.GhostAktif = X Component Of({G}.ProfilSosial[Index Of Array Value({G}.ProfilNama, Event Player.NamaTampilan)]) >= 2;"
    text = replace_once(text, old_load, new_load, "profile social unpack")
    text = replace_once(
        text,
        "\t\t\tEvent Player.KursorIkutiDummy = Event Player.IzinkanDummyMengikuti ? 1 : 0;",
        "\t\t\tEvent Player.KursorIkutiDummy = Event Player.IzinkanDummyMengikuti ? 1 : 0;\n\t\t\tEvent Player.KursorGhost = Event Player.GhostAktif ? 1 : 0;",
        "profile ghost cursor",
    )

    old_social = "Vector(Event Player.IzinkanDummyMengikuti ? 1 : 0, Event Player.JumlahPilihan, Event Player.KursorKamera)"
    new_social = "Vector((Event Player.IzinkanDummyMengikuti ? 1 : 0) + (Event Player.GhostAktif ? 2 : 0), Event Player.JumlahPilihan, Event Player.KursorKamera)"
    text = replace_all_expected(text, old_social, new_social, 3, "profile social pack")

    text = replace_once(
        text,
        "\t\tEnd;\n\t\tEvent Player.MenitLobi = Max(0, Round To Integer((Total Time Elapsed - Event Player.WaktuMasuk) / 60, Down));",
        "\t\tEnd;\n\t\tIf(Event Player.GhostAktif == True);\n\t\t\tDisable Movement Collision With Environment(Event Player, False);\n\t\tEnd;\n\t\tEvent Player.MenitLobi = Max(0, Round To Integer((Total Time Elapsed - Event Player.WaktuMasuk) / 60, Down));",
        "profile ghost engine apply",
    )

    text = replace_once(
        text,
        "Arcade Menu online. Thirteen extremely important decisions await.",
        "Arcade Menu online. Fourteen extremely important decisions await.",
        "english menu count message",
    )
    text = replace_once(text, "Menu Arcade online. Tiga belas keputusan yang sangat penting menunggu.", "Menu Arcade online. Empat belas keputusan yang sangat penting menunggu.", "id menu count message")
    text = replace_once(text, "เปิดเมนูอาร์เคดแล้ว มีสิบสามตัวเลือกสำคัญรอคุณอยู่", "เปิดเมนูอาร์เคดแล้ว มีสิบสี่ตัวเลือกสำคัญรอคุณอยู่", "thai menu count message")

    text = replace_once(
        text,
        "Event Player.KursorUtama = (Event Player.KursorUtama + (Event Player.PerintahMenu == 3 ? 1 : 12)) % 13;",
        "Event Player.KursorUtama = (Event Player.KursorUtama + (Event Player.PerintahMenu == 3 ? 1 : 13)) % 14;",
        "main menu 14-cycle",
    )
    text = replace_once(
        text,
        "\t\tElse If(Event Player.HalamanMenu == 12);\n\t\t\tEvent Player.KursorIkutiDummy = (Event Player.KursorIkutiDummy + 1) % 2;\n\t\tEnd;",
        "\t\tElse If(Event Player.HalamanMenu == 12);\n\t\t\tEvent Player.KursorIkutiDummy = (Event Player.KursorIkutiDummy + 1) % 2;\n\t\tElse If(Event Player.HalamanMenu == 13);\n\t\t\tEvent Player.KursorGhost = (Event Player.KursorGhost + 1) % 2;\n\t\tEnd;",
        "ghost submenu navigation",
    )

    text = replace_once(
        text,
        "\t\t\tElse If(Event Player.HalamanMenu == 12);\n\t\t\t\tEvent Player.KursorIkutiDummy = Event Player.IzinkanDummyMengikuti ? 1 : 0;\n\t\t\tEnd;",
        "\t\t\tElse If(Event Player.HalamanMenu == 12);\n\t\t\t\tEvent Player.KursorIkutiDummy = Event Player.IzinkanDummyMengikuti ? 1 : 0;\n\t\t\tElse If(Event Player.HalamanMenu == 13);\n\t\t\t\tEvent Player.KursorGhost = Event Player.GhostAktif ? 1 : 0;\n\t\t\tEnd;",
        "ghost cursor sync on open",
    )
    text = replace_once(
        text,
        "\t\tElse If(Event Player.HalamanMenu == 12);\n\t\t\tCall Subroutine(TerapkanHalamanIkutiDummy);\n\t\tEnd;",
        "\t\tElse If(Event Player.HalamanMenu == 12);\n\t\t\tCall Subroutine(TerapkanHalamanIkutiDummy);\n\t\tElse If(Event Player.HalamanMenu == 13);\n\t\t\tCall Subroutine(TerapkanHalamanGhost);\n\t\tEnd;",
        "ghost apply dispatch",
    )

    text = replace_once(
        text,
        "\t\tElse If(Event Player.HalamanMenu == 12);\n\t\t\tCall Subroutine(GambarIkutiDummy);\n\t\tEnd;",
        "\t\tElse If(Event Player.HalamanMenu == 12);\n\t\t\tCall Subroutine(GambarIkutiDummy);\n\t\tElse If(Event Player.HalamanMenu == 13);\n\t\t\tCall Subroutine(GambarGhost);\n\t\tEnd;",
        "ghost render dispatch",
    )

    en_tail = ' : Custom String("12 - DUMMY FOLLOW\\nCURRENT: {0}", Event Player.IzinkanDummyMengikuti ? Custom String("ON") : Custom String("OFF"))'
    en_new = ' : Event Player.KursorUtama == 12 ? Custom String("12 - DUMMY FOLLOW\\nCURRENT: {0}", Event Player.IzinkanDummyMengikuti ? Custom String("ON") : Custom String("OFF")) : Custom String("13 - GHOST MODE\\nCURRENT: {0}", Event Player.GhostAktif ? Custom String("ON") : Custom String("OFF"))'
    id_tail = ' : Custom String("12 - DUMMY MENGIKUTI\\nSAAT INI: {0}", Event Player.IzinkanDummyMengikuti ? Custom String("AKTIF") : Custom String("MATI"))'
    id_new = ' : Event Player.KursorUtama == 12 ? Custom String("12 - DUMMY MENGIKUTI\\nSAAT INI: {0}", Event Player.IzinkanDummyMengikuti ? Custom String("AKTIF") : Custom String("MATI")) : Custom String("13 - MODE GHOST\\nSAAT INI: {0}", Event Player.GhostAktif ? Custom String("AKTIF") : Custom String("MATI"))'
    th_tail = ' : Custom String("12 - ดัมมี่ติดตาม\\nสถานะ: {0}", Event Player.IzinkanDummyMengikuti ? Custom String("เปิด") : Custom String("ปิด"))'
    th_new = ' : Event Player.KursorUtama == 12 ? Custom String("12 - ดัมมี่ติดตาม\\nสถานะ: {0}", Event Player.IzinkanDummyMengikuti ? Custom String("เปิด") : Custom String("ปิด")) : Custom String("13 - โหมดผี\\nสถานะ: {0}", Event Player.GhostAktif ? Custom String("เปิด") : Custom String("ปิด"))'
    text = replace_once(text, en_tail, en_new, "main ghost EN label")
    text = replace_once(text, id_tail, id_new, "main ghost ID label")
    text = replace_once(text, th_tail, th_new, "main ghost TH label")

    transition_old = f"(Event Player.HalamanMenu == -1 ? Event Player.KursorUtama : Event Player.HalamanMenu) == 12 ? {G}.DaftarWarnaRGB[Event Player.IndeksWarna] * 0.700 + Vector(70, 220, 175) * 0.300 : {G}.DaftarWarnaRGB[Event Player.IndeksWarna]"
    transition_new = f"(Event Player.HalamanMenu == -1 ? Event Player.KursorUtama : Event Player.HalamanMenu) == 12 ? {G}.DaftarWarnaRGB[Event Player.IndeksWarna] * 0.700 + Vector(70, 220, 175) * 0.300 : (Event Player.HalamanMenu == -1 ? Event Player.KursorUtama : Event Player.HalamanMenu) == 13 ? {G}.DaftarWarnaRGB[Event Player.IndeksWarna] * 0.700 + Vector(90, 205, 255) * 0.300 : {G}.DaftarWarnaRGB[Event Player.IndeksWarna]"
    text = replace_once(text, transition_old, transition_new, "ghost menu tint")

    marker = f'{rule_kw}("91k - Subrutin: Transisi warna menu tanpa lompatan")'
    text = replace_once(text, marker, ghost_render_rule(rule_kw, event_kw, actions_kw) + marker, "insert ghost renderer")
    marker = f'{rule_kw}("99a - Subrutin: Terapkan halaman musik")'
    text = replace_once(text, marker, ghost_apply_rule(rule_kw, event_kw, actions_kw) + marker, "insert ghost apply")

    if "SegarkanRosterTertunda" in text:
        raise RuntimeError("dead SegarkanRosterTertunda survived source transform")
    return text


def patch_validator(text: str) -> str:
    text = text.replace('for name in ("IzinkanDummyMengikuti", "KursorIkutiDummy"):', 'for name in ("IzinkanDummyMengikuti", "KursorIkutiDummy", "GhostAktif", "KursorGhost"):')
    text = text.replace('f"stato pagina 12 Dummy Follow assente: {name}"', 'f"stato pagine toggle 12/13 assente: {name}"')
    text = text.replace('checks.equal(len(arcade_renderers), 14, "renderer menu principale + pagine 0..12")', 'checks.equal(len(arcade_renderers), 15, "renderer menu principale + pagine 0..13")')
    text = text.replace('for page in range(13):', 'for page in range(14):')
    text = text.replace('"router menu: pagina 12 deve aprire Dummy Follow",\n        )', '"router menu: pagina 12 deve aprire Dummy Follow",\n        )\n        checks.require(\n            re.search(r"HalamanMenu\\s*==\\s*13.*?Call Subroutine\\(GambarGhost\\);", router.body, re.DOTALL) is not None,\n            "router menu: pagina 13 deve aprire Ghost Mode",\n        )')
    text = text.replace('"12 - ดัมมี่ติดตาม",\n        ):', '"12 - ดัมมี่ติดตาม",\n            "13 - GHOST MODE",\n            "13 - MODE GHOST",\n            "13 - โหมดผี",\n        ):')
    text = text.replace('"Event Player.KursorUtama = (Event Player.KursorUtama + (Event Player.PerintahMenu == 3 ? 1 : 12)) % 13;"', '"Event Player.KursorUtama = (Event Player.KursorUtama + (Event Player.PerintahMenu == 3 ? 1 : 13)) % 14;"')
    text = text.replace('"navigazione menu principale non usa ciclo esatto 0..12",', '"navigazione menu principale non usa ciclo esatto 0..13",')
    needle = '''            "navigazione menu: pagina 12 deve alternare KursorIkutiDummy",
        )
'''
    insert = '''            "navigazione menu: pagina 12 deve alternare KursorIkutiDummy",
        )
        checks.require(
            re.search(
                r"HalamanMenu\\s*==\\s*13.*?KursorGhost\\s*=\\s*"
                r"\\(Event Player\\.KursorGhost\\s*\\+\\s*1\\)\\s*%\\s*2;",
                navigation_rule.body,
                re.DOTALL,
            ) is not None,
            "navigazione menu: pagina 13 deve alternare KursorGhost",
        )
'''
    text = replace_once(text, needle, insert, "validator ghost navigation")
    marker = '    input_router = next(\n'
    ghost_checks = '''    ghost_renderer = rule_by_subroutine(rules, "GambarGhost")
    ghost_apply = rule_by_subroutine(rules, "TerapkanHalamanGhost")
    checks.require(ghost_renderer is not None, "renderer pagina 13 Ghost Mode assente")
    checks.require(ghost_apply is not None, "apply pagina 13 Ghost Mode assente")
    checks.require("SegarkanRosterTertunda" not in source, "flag roster legacy SegarkanRosterTertunda deve essere rimosso")
    if ghost_renderer:
        for token in ("13 - GHOST MODE", "13 - MODE GHOST", "13 - โหมดผี", "KursorGhost", "GhostAktif"):
            checks.require(token in ghost_renderer.body, f"pagina 13 Ghost Mode incompleta: {token}")
    if ghost_apply:
        checks.require("Disable Movement Collision With Environment(Event Player, False);" in ghost_apply.body,
                       "Ghost Mode ON non disabilita collisione muri/soffitti")
        checks.require("Enable Movement Collision With Environment(Event Player);" in ghost_apply.body,
                       "Ghost Mode OFF non ripristina collisione ambiente")
        checks.require("Disable Movement Collision With Players" not in ghost_apply.body,
                       "Ghost Mode non deve modificare collisione player/bot")

'''
    text = replace_once(text, marker, ghost_checks + marker, "validator ghost invariants")
    return text


def patch_tests(text: str) -> str:
    replacements = {
        '% 13': '% 14',
        '? 1 : 12)) % 13': '? 1 : 13)) % 14',
        'Thirteen extremely important decisions await.': 'Fourteen extremely important decisions await.',
        'Tiga belas keputusan yang sangat penting menunggu.': 'Empat belas keputusan yang sangat penting menunggu.',
        'มีสิบสามตัวเลือกสำคัญรอคุณอยู่': 'มีสิบสี่ตัวเลือกสำคัญรอคุณอยู่',
        '0..12': '0..13',
        'range(13)': 'range(14)',
        'renderer menu principale + pagine 0..12': 'renderer menu principale + pagine 0..13',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.replace('SegarkanRosterTertunda', 'GhostAktif')
    return text


def patch_readme(text: str) -> str:
    text = text.replace('- 13 menu Arcade con preferenze individuali.', '- 14 menu Arcade con preferenze individuali.')
    text = text.replace('## I 13 menu', '## I 14 menu')
    text = text.replace('| 12 | Dummy Follow | consente o nega al dummy nemico di seguire il player; default OFF |', '| 12 | Dummy Follow | consente o nega al dummy nemico di seguire il player; default OFF |\n| 13 | Ghost Mode | OFF / ON; ON attraversa muri e soffitti ma lascia solidi i pavimenti |')
    old = 'Gli indici sono Main Menu `-1` e sottomenu `0..12`. Name Color (pagina `0`) parte da bianco e guida sfumature distinte delle altre pagine menu. Dummy Follow è OFF per default: il dummy resta fermo finché almeno un umano avversario non abilita volontariamente l\'opt-in; fra i player con preferenza ON sceglie sempre il più vicino e si ferma nuovamente quando non resta alcun target idoneo. I default e i cursori persistono tra chiusura, riapertura e cambio squadra reference-stable; un team switch di un umano già registrato aggiorna subito lo stato dipendente dal Team e chiude/riarma Menu Arcade e overlay Teleport, ma differisce di almeno 0,25 secondi la sostituzione dei due HUD roster finché il player non è nuovamente spawned e vivo. Gli handle vengono distrutti tramite gli array globali canonici e il renderer torna pronto soltanto dopo entrambe le righe. Durante il pending il player esce temporaneamente dai soli filtri Crouch, così un testo nel mondo già aperto viene invalidato e ricreato; Camera, status, effetti e voti attivi non vengono cancellati. Se il motore sostituisce davvero il riferimento e perde le player variables, il recovery usa invece il setup fresco e riapplica i default: è un fallback distinto dal refresh leggero.'
    new = 'Gli indici sono Main Menu `-1` e sottomenu `0..13`. Name Color (pagina `0`) parte da bianco e guida sfumature distinte delle altre pagine menu. Dummy Follow e Ghost Mode sono OFF per default. Ghost Mode usa la collisione ambiente nativa con `Include Floors = False`: il player attraversa muri e soffitti ma continua a stare sui pavimenti; non modifica la collisione con player/bot. Le 12 coppie di righe roster vengono create globalmente una sola volta e appartengono allo slot HUD, non all\'entità player. Un cambio squadra riassocia immediatamente la nuova entità allo slot riservato e conserva nome/profilo; un vero leave svuota soltanto il payload dello slot e non distrugge le righe permanenti. Camera, status, effetti, voti e preferenze persistenti non vengono cancellati dal rebind.'
    if old not in text:
        raise RuntimeError('README lifecycle paragraph not found')
    text = text.replace(old, new)
    text = text.replace('sincronizza Team, UI transitoria e ricreazione differita delle due righe roster.', 'sincronizza Team e UI transitoria mentre le due righe roster globali restano permanenti e vengono solo riassociate allo slot.')
    return text


def simple_doc_updates(path: Path) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding='utf-8')
    text = text.replace('13 menu', '14 menu').replace('I 13 menu', 'I 14 menu').replace('0..12', '0..13')
    if path.name == 'PROGETTO.md' and 'Ghost Mode' not in text:
        text += '\n\n### Menu 13 — Ghost Mode\n\nGhost Mode è OFF per default. Quando è ON usa `Disable Movement Collision With Environment(player, False)`: muri e soffitti diventano attraversabili, i pavimenti restano solidi e la collisione con player/bot non viene modificata. Lo stato è salvato nel profilo runtime e riapplicato dopo cambio squadra o cambio eroe.\n'
    if path.name == 'TEST.md' and 'Ghost Mode' not in text:
        text += '\n\n## Ghost Mode\n\n- [ ] Menu 13 mostra OFF/ON e applica solo con Crouch + Interact.\n- [ ] ON attraversa muri e soffitti ma non il pavimento.\n- [ ] OFF ripristina la collisione ambiente normale.\n- [ ] La collisione con player/bot non cambia.\n- [ ] Stato conservato dopo cambio squadra, cambio eroe e rejoin nello stesso match.\n'
    if path.name == 'VALIDAZIONE.md' and 'Ghost Mode' not in text:
        text += '\n\n## Gate Ghost Mode\n\nIl validator richiede la pagina 13, il ciclo Main Menu `0..13`, entrambi i comandi di collisione ambiente, assenza di modifiche alla collisione player/bot e rimozione del vecchio flag `SegarkanRosterTertunda`.\n'
    path.write_text(text, encoding='utf-8')


def main() -> None:
    IT.write_text(transform_source(IT.read_text(encoding='utf-8'), italian=True), encoding='utf-8')
    EN.write_text(transform_source(EN.read_text(encoding='utf-8'), italian=False), encoding='utf-8')

    validator = ROOT / 'tools' / 'validate_workshop.py'
    validator.write_text(patch_validator(validator.read_text(encoding='utf-8')), encoding='utf-8')

    for name in ('tests/test_validate_workshop.py', 'tests/test_runtime_maintenance.py', 'tests/test_dummy_bots.py'):
        path = ROOT / name
        path.write_text(patch_tests(path.read_text(encoding='utf-8')), encoding='utf-8')

    ghost_test = ROOT / 'tests' / 'test_ghost_mode.py'
    ghost_test.write_text('''from pathlib import Path\nimport unittest\n\nROOT = Path(__file__).resolve().parents[1]\n\n\nclass GhostModeTests(unittest.TestCase):\n    @classmethod\n    def setUpClass(cls):\n        cls.it = (ROOT / "workshop" / "ruang_irama.it-IT.workshop").read_text(encoding="utf-8")\n        cls.en = (ROOT / "tests" / "fixtures" / "semantic_reference.txt").read_text(encoding="utf-8")\n\n    def test_page_13_is_wired_end_to_end(self):\n        for source, g in ((self.it, "Globale"), (self.en, "Global")):\n            self.assertIn("108: KursorGhost", source)\n            self.assertIn("106: GhostAktif", source)\n            self.assertNotIn("SegarkanRosterTertunda", source)\n            self.assertIn("% 14;", source)\n            self.assertIn("HalamanMenu == 13", source)\n            self.assertIn("Call Subroutine(GambarGhost);", source)\n            self.assertIn("Call Subroutine(TerapkanHalamanGhost);", source)\n            self.assertIn("13 - GHOST MODE", source)\n            self.assertIn("13 - MODE GHOST", source)\n            self.assertIn("13 - โหมดผี", source)\n\n    def test_ghost_changes_only_environment_collision(self):\n        for source in (self.it, self.en):\n            start = source.index('"99n - Subrutin: Terapkan Ghost Mode"')\n            end = source.index('"99a - Subrutin: Terapkan halaman musik"', start)\n            block = source[start:end]\n            self.assertIn("Disable Movement Collision With Environment(Event Player, False);", block)\n            self.assertIn("Enable Movement Collision With Environment(Event Player);", block)\n            self.assertNotIn("Disable Movement Collision With Players", block)\n            self.assertNotIn("Enable Movement Collision With Players", block)\n\n    def test_ghost_persists_and_is_reasserted(self):\n        for source, g in ((self.it, "Globale"), (self.en, "Global")):\n            self.assertIn("(Event Player.GhostAktif ? 2 : 0)", source)\n            self.assertIn(f"{g}.PemainAktif.GhostAktif == True", source)\n            self.assertIn(f"Disable Movement Collision With Environment({g}.PemainAktif, False);", source)\n            self.assertIn("Enable Movement Collision With Environment(Event Player);", source)\n\n\nif __name__ == "__main__":\n    unittest.main()\n''', encoding='utf-8')

    readme = ROOT / 'README.md'
    readme.write_text(patch_readme(readme.read_text(encoding='utf-8')), encoding='utf-8')
    for rel in ('docs/PROGETTO.md', 'docs/TEST.md', 'docs/VALIDAZIONE.md'):
        simple_doc_updates(ROOT / rel)

    changelog = ROOT / 'CHANGELOG.md'
    ch = changelog.read_text(encoding='utf-8')
    marker = '## 0.8.1\n'
    bullet = '- Aggiunto Menu 13 **Ghost Mode**: collisione con muri/soffitti disattivabile mantenendo solidi i pavimenti; stato persistente e riapplicato dopo team/hero change. Audit statico: nessuna regola duplicata; il flag roster morto `SegarkanRosterTertunda` è stato riutilizzato come `GhostAktif`.\n'
    if marker in ch and bullet not in ch:
        ch = ch.replace(marker, marker + bullet, 1)
    changelog.write_text(ch, encoding='utf-8')

    print('ghost menu 13 patch applied')


if __name__ == '__main__':
    main()
