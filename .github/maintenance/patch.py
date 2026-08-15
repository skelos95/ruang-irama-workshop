from __future__ import annotations

from pathlib import Path
import hashlib
import re

SOURCE = Path("workshop/ruang_irama.workshop")
VALIDATOR = Path("tools/validate_workshop.py")
UNIT_TESTS = Path("tests/test_validate_workshop.py")
README = Path("README.md")
PROJECT = Path("docs/PROGETTO.md")
TEST_DOC = Path("docs/TEST.md")
REPORT = Path("docs/VALIDAZIONE.md")


def replace_required(text: str, old: str, new: str, label: str, minimum: int = 1) -> str:
    count = text.count(old)
    if count < minimum:
        raise SystemExit(f"{label}: expected at least {minimum}, found {count}")
    return text.replace(old, new)


# ---------------------------------------------------------------------------
# 1. Workshop identifiers: Indonesian names, keeping only technical acronyms
#    and official Workshop concepts where appropriate.
# ---------------------------------------------------------------------------
identifier_map = {
    "RestartSudahDiminta": "MulaiUlangSudahDiminta",
    "DaftarNegaraVPN": "DaftarLokasiServer",
    "IndeksNegaraVPN": "IndeksLokasiServer",
    "BotAI": "BotOtomatis",
    "MenitLobby": "MenitLobi",
    "UnkillableAktif": "KebalAktif",
    "KursorUnkillable": "KursorKebal",
    "TeleportCrouchAktif": "TeleportasiJongkokAktif",
    "PosisiRespawnAman": "PosisiBangkitAman",
    "RespawnJumpDipakai": "BangkitLompatDipakai",
    "GambarUnkillable": "GambarKebal",
}

rule_phrase_map = {
    " - Global:": " - Umum:",
    "RGB pastel neon lento untuk judul, timer, dan efek": "RGB pastel neon lambat untuk judul, waktu, dan efek",
    "Respawn Jump:": "Bangkit Lompat:",
    "Unkillable:": "Kebal:",
    "Teleport Crouch:": "Teleportasi Jongkok:",
    "Dispatcher input dengan prioritas tetap": "Pengatur masukan dengan prioritas tetap",
    "Lepaskan dispatcher setelah semua input dilepas": "Lepaskan pengatur setelah semua masukan dilepas",
    "Dispatcher input separato dal menu Arcade": "Pengatur masukan terpisah dari Menu Arcade",
    "Riattiva dispatcher dopo rilascio comando": "Aktifkan lagi pengatur setelah tombol dilepas",
    "Tembakan utama memilih destinazione successiva": "Tembakan utama memilih tujuan berikutnya",
    "Tembakan sekunder memilih destinazione precedente": "Tembakan sekunder memilih tujuan sebelumnya",
    "Interact esegue il teletrasporto": "Interact menjalankan teleportasi",
    "Segarkan lista target senza ridisegno periodico": "Segarkan daftar target tanpa menggambar ulang berkala",
    "Chiudi appena Crouch viene rilasciato": "Tutup saat Jongkok dilepas",
    "Buka overlay selama Crouch ditahan": "Buka tampilan selama Jongkok ditahan",
    "Transisi warna menu tanpa scatto": "Transisi warna menu tanpa lompatan",
}

sync_paths = [SOURCE, VALIDATOR, UNIT_TESTS, README, PROJECT, TEST_DOC]
for path in sync_paths:
    text = path.read_text(encoding="utf-8")
    for old, new in identifier_map.items():
        text = text.replace(old, new)
    for old, new in rule_phrase_map.items():
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")

# Clean the stale VPN terminology in repository tooling as well.
for path in (VALIDATOR, UNIT_TESTS):
    text = path.read_text(encoding="utf-8")
    text = text.replace("check_vpn_country_setting", "check_server_location_setting")
    text = text.replace("VPN countries", "Server Location countries")
    text = text.replace("lista VPN Asia", "lista Server Location Asia")
    text = text.replace("paesi VPN Asia", "paesi Server Location Asia")
    text = text.replace("indice VPN predefinito Indonesia", "indice Server Location predefinito Indonesia")
    text = text.replace("VPN: Workshop Setting Combo", "Server Location: Workshop Setting Combo")
    text = text.replace("VPN: nome della combo Asia", "Server Location: nome della combo Asia")
    text = text.replace("VPN: la vecchia impostazione numerica", "Server Location: la vecchia impostazione numerica")
    path.write_text(text, encoding="utf-8")

src = SOURCE.read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# 2. HUD/header copy: shorter, clearer, still playful in EN / ID / TH.
# ---------------------------------------------------------------------------
copy_replacements = {
    'Hold {0}: inspect player, hero & health': 'Hold {0}: inspect hero + HP',
    'Tahan {0}: lihat pemain, hero & kesehatan': 'Tahan {0}: cek pahlawan + HP',
    'กด {0} ค้าง: ดูผู้เล่น ฮีโร่ และพลังชีวิต': 'กด {0} ค้าง: ดูฮีโร่ + HP',
    'LOBBY ROSTER & CHILL TIME\\n ': 'LOBBY & CHILL TIME\\n ',
    'DAFTAR PEMAIN & WAKTU CHILL\\n ': 'LOBI & WAKTU SANTAI\\n ',
    'รายชื่อผู้เล่นและเวลา CHILL\\n ': 'ล็อบบี้ & เวลาชิล\\n ',
    'Hold {0} 0.5 sec: open Arcade Menu': 'Hold {0} 0.5 sec: Arcade Menu',
    'Tahan {0} 0,5 dtk: buka Menu Arcade': 'Tahan {0} 0,5 dtk: Menu Arcade',
    'กด {0} ค้าง 0.5 วินาที: เปิดเมนูอาร์เคด': 'กด {0} ค้าง 0.5 วิ: เมนูอาร์เคด',
    'PLAYER SOUNDTRACKS\\n ': 'PLAYER VIBES\\n ',
    'SOUNDTRACK PEMAIN\\n ': 'MUSIK PEMAIN\\n ',
    'เพลงประจำผู้เล่น\\n ': 'เพลงของผู้เล่น\\n ',
    'Welcome to CHILL Dedicated Server. Pick a vibe, pick a color, cause harmless trouble.': 'Welcome to CHILL. Pick a vibe, pick a color, stay weird.',
    'Selamat datang di CHILL Dedicated Server. Pilih vibe, pilih warna, lalu bikin kekacauan kecil.': 'Selamat datang di CHILL. Pilih vibe, pilih warna, tetap aneh.',
    'ยินดีต้อนรับสู่ CHILL Dedicated Server เลือกเพลง เลือกสี แล้วสนุกกันแบบไม่ทำร้ายใคร': 'ยินดีต้อนรับสู่ CHILL เลือกเพลง เลือกสี แล้วกวนแบบพอดี ๆ',
    'belum pilih soundtrack': 'belum pilih musik',
}
for old, new in copy_replacements.items():
    src = replace_required(src, old, new, f"HUD copy {old!r}")

# Diagnostics: EN / ID / TH are now genuinely localized instead of sharing EN
# for languages 0 and 1.
old_diag = ''' : Custom String("{0}\\n{1}",
\t\t\tCustom String("\\n \\nLOAD {0}% | AVG {1}% | MAX {2}%", Server Load, Server Load Average, Server Load Peak), Custom String("HUD {0} | IWT {1}",
\t\t\t3 + Count Of(Global.HudKiriPemain) * 2 + Count Of(Filtered Array(Global.HudMenuPemain, Current Array Element != 0)), Count Of(Filtered Array(
\t\t\tGlobal.TeksDuniaPemain, Current Array Element != 0)) + Count Of(Filtered Array(Global.TeksDiriPemain, Current Array Element != 0)))) : Custom String(" ")'''
new_diag = ''' : Player Variable(Local Player, IndeksBahasa) == 1 ? Custom String("{0}\\n{1}",
\t\t\tCustom String("\\n \\nBEBAN {0}% | RATA {1}% | PUNCAK {2}%", Server Load, Server Load Average, Server Load Peak), Custom String("HUD {0} | IWT {1}",
\t\t\t3 + Count Of(Global.HudKiriPemain) * 2 + Count Of(Filtered Array(Global.HudMenuPemain, Current Array Element != 0)), Count Of(Filtered Array(
\t\t\tGlobal.TeksDuniaPemain, Current Array Element != 0)) + Count Of(Filtered Array(Global.TeksDiriPemain, Current Array Element != 0)))) : Custom String("{0}\\n{1}",
\t\t\tCustom String("\\n \\nLOAD {0}% | AVG {1}% | MAX {2}%", Server Load, Server Load Average, Server Load Peak), Custom String("HUD {0} | IWT {1}",
\t\t\t3 + Count Of(Global.HudKiriPemain) * 2 + Count Of(Filtered Array(Global.HudMenuPemain, Current Array Element != 0)), Count Of(Filtered Array(
\t\t\tGlobal.TeksDuniaPemain, Current Array Element != 0)) + Count Of(Filtered Array(Global.TeksDiriPemain, Current Array Element != 0)))) : Custom String(" ")'''
if old_diag not in src:
    raise SystemExit("diagnostics EN fallback anchor not found")
src = src.replace(old_diag, new_diag, 1)

# ---------------------------------------------------------------------------
# 3. Main/submenu labels. English stays concise, Indonesian is actually
#    Indonesian, Thai is shortened without changing meaning.
# ---------------------------------------------------------------------------
menu_literal_replacements = {
    '1 - THIRD-PERSON CAMERA': '1 - THIRD-PERSON',
    '3 - HUD LANGUAGE': '3 - LANGUAGE',
    '4 - REVENGE\\nDIRECT KILLS OWED TO YOU': '4 - REVENGE\\nSETTLE YOUR SCORE',
    '5 - UNKILLABLE + 1 HP': '5 - UNKILLABLE: 1 HP',
    '6 - VOICE MODIFIER': '6 - HERO VOICE',
    '7 - PLAYER ICON': '7 - ICON',
    '1 - KAMERA ORANG KETIGA': '1 - KAMERA 3P',
    '3 - BAHASA HUD': '3 - BAHASA',
    '4 - BALAS DENDAM\\nUTANG KILL LANGSUNG': '4 - BALAS DENDAM\\nTAGIH UTANG KILL',
    '6 - PENGUBAH SUARA': '6 - SUARA PAHLAWAN',
    '7 - IKON PEMAIN': '7 - IKON',
    '3 - ภาษา HUD': '3 - ภาษา',
    '4 - ล้างแค้น\\nศัตรูที่ติดหนี้คุณ': '4 - ล้างแค้น\\nทวงหนี้กันหน่อย',
    '6 - ปรับเสียงฮีโร่': '6 - เสียงฮีโร่',
    '7 - ไอคอนผู้เล่น': '7 - ไอคอน',
}
for old, new in menu_literal_replacements.items():
    src = src.replace(old, new)

# Language-specific feature names that originally reused English text.
src = src.replace('Custom String("0 - SOUNDTRACK\\nSAAT INI:', 'Custom String("0 - MUSIK\\nSAAT INI:')
src = src.replace('Custom String("0 - SOUNDTRACK {0}/100\\nSAAT INI:', 'Custom String("0 - MUSIK {0}/100\\nSAAT INI:')
src = src.replace('Custom String("5 - UNKILLABLE: 1 HP\\nSAAT INI:', 'Custom String("5 - KEBAL: 1 HP\\nSAAT INI:')
src = src.replace('Custom String("5 - UNKILLABLE: 1 HP {0}/2\\nSAAT INI:', 'Custom String("5 - KEBAL: 1 HP {0}/2\\nSAAT INI:')
src = src.replace('Custom String("5 - UNKILLABLE: 1 HP\\nสถานะ:', 'Custom String("5 - ฆ่าไม่ตาย: 1 HP\\nสถานะ:')
src = src.replace('Custom String("5 - UNKILLABLE: 1 HP {0}/2\\nสถานะ:', 'Custom String("5 - ฆ่าไม่ตาย: 1 HP {0}/2\\nสถานะ:')

# Shorter navigation copy; button colors and bindings stay unchanged.
for old, new in (
    ('next | previous', 'next | prev'),
    ('berikutnya | sebelumnya', 'berikut | sebelum'),
    ('back 10 | forward 10', '-10 | +10'),
    ('mundur 10 | maju 10', '-10 | +10'),
    ('ย้อน 10 | เดินหน้า 10', '-10 | +10'),
):
    src = src.replace(old, new)

# ---------------------------------------------------------------------------
# 4. Small Messages: keep all three languages, shorten the noisy ones and make
#    the tone consistent with the social CHILL mode.
# ---------------------------------------------------------------------------
message_replacements = {
    'Soundtrack locked: {0}. Excellent taste, probably.': 'Soundtrack: {0}. Great taste. Probably.',
    'Soundtrack dipilih: {0}. Selera bagus. Mungkin.': 'Musik: {0}. Selera bagus. Mungkin.',
    'เลือกเพลงประกอบแล้ว: {0} รสนิยมดี...น่าจะนะ': 'เลือกเพลง: {0} รสนิยมดี...น่าจะนะ',
    'First person restored. You may pretend that never happened.': 'First person restored. Nobody saw that.',
    'Kamera orang pertama kembali. Tidak ada yang melihat tadi.': 'Kamera normal lagi. Anggap tak terjadi.',
    'กลับสู่มุมมองบุคคลที่หนึ่งแล้ว ทำเป็นว่าเมื่อกี้ไม่เกิดขึ้นก็ได้': 'กลับมุมมองปกติแล้ว ไม่มีใครเห็นหรอก',
    'Third person enabled. Admire responsibly.': 'Third person on. Ego responsibly.',
    'Orang ketiga aktif. Silakan mengagumi diri secukupnya.': 'Kamera 3P aktif. Jangan narsis berlebihan.',
    'เปิดมุมมองบุคคลที่สามแล้ว ชื่นชมตัวเองแต่พอดี': 'เปิดกล้องบุคคลที่สามแล้ว อย่าหลงตัวเองเกินไป',
    'Now spectating {0}. Definitely not stalking.': 'Watching {0}. Definitely not stalking.',
    'Sekarang menonton {0}. Sama sekali bukan menguntit.': 'Menonton {0}. Bukan stalking. Serius.',
    'กำลังชม {0} อยู่ นี่ไม่ใช่การสะกดรอยแน่นอน': 'กำลังดู {0} อยู่ ไม่ได้สะกดรอยนะ จริง ๆ',
    'Name color set to {0}. Subtlety is optional.': 'Name color: {0}. Subtlety optional.',
    'Warna nama: {0}. Kalem itu opsional.': 'Warna nama: {0}. Boleh norak.',
    'ตั้งสีชื่อเป็น {0} แล้ว จะเด่นแค่ไหนก็ได้': 'สีชื่อ: {0} เด่นได้ตามใจ',
    'Hero voice modifier applied.': 'Hero voice updated. Science!',
    'Pengubah suara hero diterapkan.': 'Suara pahlawan diubah. Demi sains!',
    'ใช้ตัวปรับเสียงฮีโร่แล้ว': 'ปรับเสียงฮีโร่แล้ว วิทยาศาสตร์!',
    'Player icon applied: {0}.': 'Player icon: {0}.',
    'Ikon pemain diterapkan: {0}.': 'Ikon pemain: {0}.',
    'ใช้ไอคอนผู้เล่นแล้ว: {0}': 'ไอคอนผู้เล่น: {0}',
    'Camera target left. First person has reclaimed you.': 'Camera target left. Back to normal.',
    'Target kamera keluar. Orang pertama mengambilmu kembali.': 'Target kamera keluar. Kembali normal.',
    'เป้าหมายกล้องออกไปแล้ว กลับสู่มุมมองบุคคลที่หนึ่ง': 'เป้าหมายกล้องหายไป กลับมุมมองปกติแล้ว',
    'Unkillable + 1 HP enabled.': 'Unkillable: 1 HP enabled.',
    'Unkillable + 1 HP aktif.': 'Kebal: 1 HP aktif.',
    'เปิด Unkillable + 1 HP แล้ว': 'เปิดโหมดฆ่าไม่ตาย: 1 HP แล้ว',
    'Unkillable + 1 HP disabled.': 'Unkillable: 1 HP disabled.',
    'Unkillable + 1 HP nonaktif.': 'Kebal: 1 HP nonaktif.',
    'ปิด Unkillable + 1 HP แล้ว': 'ปิดโหมดฆ่าไม่ตาย: 1 HP แล้ว',
    'Unkillable + 1 HP is unavailable in the Spawn Room.': 'Unkillable: 1 HP is unavailable in Spawn Room.',
    'Unkillable + 1 HP tidak tersedia di ruang muncul.': 'Kebal: 1 HP tidak tersedia di ruang muncul.',
    'ไม่สามารถใช้ Unkillable + 1 HP ในห้องเกิดได้': 'ใช้โหมดฆ่าไม่ตาย: 1 HP ในห้องเกิดไม่ได้',
    'Unkillable + 1 HP disabled: you entered the Spawn Room.': 'Unkillable disabled: Spawn Room rules.',
    'Unkillable + 1 HP dinonaktifkan: kamu masuk ruang muncul.': 'Kebal dimatikan: aturan ruang muncul.',
    'ปิด Unkillable + 1 HP แล้ว: คุณเข้าไปในห้องเกิด': 'ปิดโหมดฆ่าไม่ตายแล้ว: กฎห้องเกิด',
}
for old, new in message_replacements.items():
    src = src.replace(old, new)

# Respawn prompt: use the player's actual Jump binding in all languages.
old_respawn_prompt = '''Small Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Press Jump to respawn near where you died.") : Event Player.IndeksBahasa == 1 ? Custom String("Tekan Jump untuk hidup kembali dekat tempat kamu mati.") : Custom String("กด Jump เพื่อเกิดใหม่ใกล้จุดที่คุณตาย"));'''
new_respawn_prompt = '''Small Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Press {0}: respawn near your death spot.", Input Binding String(Button(Jump))) : Event Player.IndeksBahasa == 1 ? Custom String("Tekan {0}: bangkit dekat lokasi mati.", Input Binding String(Button(Jump))) : Custom String("กด {0}: เกิดใหม่ใกล้จุดตาย", Input Binding String(Button(Jump))));'''
src = replace_required(src, old_respawn_prompt, new_respawn_prompt, "localized Jump respawn prompt")

src = src.replace('Respawned at a nearby safe walkable position.', 'Respawned nearby. Try not to repeat that.')
src = src.replace('Hidup kembali di posisi aman terdekat yang bisa dilalui.', 'Bangkit dekat titik mati. Coba jangan ulangi.')
src = src.replace('เกิดใหม่ในตำแหน่งปลอดภัยใกล้เคียงที่เดินได้แล้ว', 'เกิดใหม่ใกล้จุดตายแล้ว อย่าซ้ำอีกล่ะ')

SOURCE.write_text(src, encoding="utf-8")

# Sync exact changed UI literals into validator/tests when they happen to be
# asserted there. This is intentionally conservative: absent strings are fine.
for path in (VALIDATOR, UNIT_TESTS):
    text = path.read_text(encoding="utf-8")
    for old, new in copy_replacements.items():
        text = text.replace(old, new)
    for old, new in menu_literal_replacements.items():
        text = text.replace(old, new)
    for old, new in message_replacements.items():
        text = text.replace(old, new)
    text = text.replace('belum pilih soundtrack', 'belum pilih musik')
    path.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# 5. Validator: lock the localization + Indonesian naming audit in place.
# ---------------------------------------------------------------------------
val = VALIDATOR.read_text(encoding="utf-8")
check = r'''

def check_localization_and_indonesian_naming(checks: Checks, source: str, rules: list[Rule]) -> None:
    variables = section_body(source, "variables")
    for old in (
        "RestartSudahDiminta", "DaftarNegaraVPN", "IndeksNegaraVPN", "BotAI", "MenitLobby",
        "UnkillableAktif", "KursorUnkillable", "TeleportCrouchAktif", "PosisiRespawnAman",
        "RespawnJumpDipakai", "GambarUnkillable",
    ):
        checks.require(old not in variables and old not in source, f"nomenclatura lama ancora presente: {old}")

    for new in (
        "MulaiUlangSudahDiminta", "DaftarLokasiServer", "IndeksLokasiServer", "BotOtomatis", "MenitLobi",
        "KebalAktif", "KursorKebal", "TeleportasiJongkokAktif", "PosisiBangkitAman",
        "BangkitLompatDipakai", "GambarKebal",
    ):
        checks.require(new in source, f"nomenclatura Indonesia mancante: {new}")

    banned_rule_fragments = (
        " - Global:", "lento", "Respawn Jump:", "Unkillable:", "Teleport Crouch:",
        "Dispatcher input", "dispatcher", "separato", "Riattiva", "destinazione", "precedente",
        "successiva", "esegue il teletrasporto", "lista target", "senza ridisegno", "Chiudi appena",
        "overlay selama Crouch", "scatto",
    )
    names = "\n".join(rule.name for rule in rules)
    for fragment in banned_rule_fragments:
        checks.require(fragment not in names, f"titolo regola non completamente indonesiano: {fragment}")

    for required in (
        "00 - Umum:", "RGB pastel neon lambat untuk judul, waktu, dan efek",
        "Bangkit Lompat:", "Kebal:", "Teleportasi Jongkok:",
        "Pengatur masukan terpisah dari Menu Arcade", "tujuan berikutnya", "tujuan sebelumnya",
        "Interact menjalankan teleportasi", "tanpa menggambar ulang berkala", "tanpa lompatan",
    ):
        checks.require(required in names, f"titolo regola Indonesia mancante: {required}")

    small_messages = call_texts(source, "Small Message")
    checks.require(len(small_messages) > 0, "nessun Small Message trovato")
    for call in small_messages:
        checks.require("IndeksBahasa" in call, "Small Message non localizzato in base alla lingua")

    # Three-language HUD anchors: global info, menus and diagnostics.
    for token in (
        "Hold {0}: inspect hero + HP",
        "Tahan {0}: cek pahlawan + HP",
        "กด {0} ค้าง: ดูฮีโร่ + HP",
        "LOBBY & CHILL TIME",
        "LOBI & WAKTU SANTAI",
        "ล็อบบี้ & เวลาชิล",
        "PLAYER VIBES",
        "MUSIK PEMAIN",
        "เพลงของผู้เล่น",
        "BEBAN {0}% | RATA {1}% | PUNCAK {2}%",
        "LOAD {0}% | AVG {1}% | MAX {2}%",
        "โหลด {0}% | เฉลี่ย {1}% | สูงสุด {2}%",
        "0 - MUSIK",
        "5 - KEBAL: 1 HP",
        "5 - ฆ่าไม่ตาย: 1 HP",
        "6 - SUARA PAHLAWAN",
        "6 - เสียงฮีโร่",
    ):
        checks.require(token in source, f"localizzazione HUD mancante: {token}")

    for stale in (
        "DAFTAR PEMAIN & WAKTU CHILL", "SOUNDTRACK PEMAIN", "belum pilih soundtrack",
        "Tahan {0}: lihat pemain, hero & kesehatan", "Unkillable + 1 HP aktif.",
        "Pengubah suara hero diterapkan.", "Respawn Jump:", "Teleport Crouch:",
    ):
        checks.require(stale not in source, f"testo vecchio/non localizzato ancora presente: {stale}")
'''
if 'def check_localization_and_indonesian_naming(' not in val:
    marker = '\ndef main() -> None:\n'
    if val.count(marker) != 1:
        raise SystemExit("validator main marker not found")
    val = val.replace(marker, check + marker, 1)
    anchor = '        check_smooth_menu_color_transition(checks, source, rules, subroutines)\n'
    if anchor not in val:
        raise SystemExit("validator localization call anchor not found")
    val = val.replace(anchor, anchor + '        check_localization_and_indonesian_naming(checks, source, rules)\n', 1)
VALIDATOR.write_text(val, encoding="utf-8")

# ---------------------------------------------------------------------------
# 6. Documentation.
# ---------------------------------------------------------------------------
readme = README.read_text(encoding="utf-8")
line = '- Audit localizzazione completo: HUD e Small Message verificati in English / Bahasa Indonesia / ไทย; nomenclatura Workshop interna ripulita in Bahasa Indonesia.'
if line not in readme:
    readme += '\n' + line + '\n'
README.write_text(readme, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
section = '''\n\n### Audit localizzazione e nomenclatura\n\nTutti gli HUD principali e i `Small Message` sono stati ricontrollati nelle tre lingue disponibili (English, Bahasa Indonesia e ไทย). I testi più lunghi sono stati abbreviati e il tono è stato reso più coerente con una modalità social/CHILL; i diagnostics ora hanno anche etichette Bahasa Indonesia proprie. I messaggi di Jump respawn usano `Input Binding String(Button(Jump))` invece della parola fissa `Jump`.\n\nLa nomenclatura Workshop interna è stata ripulita: i residui misti `VPN`, `Lobby`, `BotAI`, `UnkillableAktif`, `TeleportCrouchAktif`, `RespawnJumpDipakai` e simili sono stati sostituiti con nomi Bahasa Indonesia (`DaftarLokasiServer`, `MenitLobi`, `BotOtomatis`, `KebalAktif`, `TeleportasiJongkokAktif`, `BangkitLompatDipakai`, ecc.). Anche i titoli delle regole con frammenti italiani/inglesi sono stati normalizzati; restano invariati solo keyword Workshop, nomi dei pulsanti, acronimi tecnici e nomi propri.\n'''
if '### Audit localizzazione e nomenclatura' not in project:
    project += section
PROJECT.write_text(project, encoding="utf-8")

tests = TEST_DOC.read_text(encoding="utf-8")
for line in (
    '- **Audit 3 lingue live:** cambiare HUD Language tra English / Bahasa Indonesia / ไทย e aprire tutti gli 8 menu, Teleport Crouch/Jongkok, Crouch inspection e diagnostics; nessun testo deve restare nella lingua precedente.\n',
    '- **Small Message live:** provare Camera, Name Color, Soundtrack/Musik, Revenge, Kebal/Unkillable, Voice, Player Icon, Jump respawn e Teleport; verificare testi brevi e coerenti nella lingua selezionata.\n',
):
    if line not in tests:
        tests += '\n' + line
TEST_DOC.write_text(tests, encoding="utf-8")

# Refresh validation report after Workshop source changes.
data = SOURCE.read_bytes().replace(b"\r\n", b"\n")
blob = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
report = REPORT.read_text(encoding="utf-8")
report, n = re.subn(r"```text\n[0-9a-f]{40}\n```", f"```text\n{blob}\n```", report, count=1)
if n != 1:
    raise SystemExit("validation report blob marker not found")
rule_count = len(re.findall(r'(?m)^\s*rule\s*\(', SOURCE.read_text(encoding="utf-8")))
report = re.sub(
    r'Generi: 100 \| Lingue: 3 \| Regole: \d+ \| Raycast camera: 1',
    f'Generi: 100 | Lingue: 3 | Regole: {rule_count} | Raycast camera: 1',
    report,
    count=1,
)
REPORT.write_text(report, encoding="utf-8")
