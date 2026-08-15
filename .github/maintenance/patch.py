from __future__ import annotations

from pathlib import Path
import hashlib
import re

SOURCE = Path("workshop/ruang_irama.workshop")
VALIDATOR = Path("tools/validate_workshop.py")
README = Path("README.md")
PROJECT = Path("docs/PROGETTO.md")
TESTS = Path("docs/TEST.md")
REPORT = Path("docs/VALIDAZIONE.md")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 occurrence, found {count}")
    return text.replace(old, new, 1)


def replace_in_rule(text: str, prefix: str, old: str, new: str, label: str) -> str:
    start = text.index(f'rule("{prefix}')
    end = text.find('\nrule("', start + 1)
    if end < 0:
        end = len(text)
    block = text[start:end]
    block = replace_once(block, old, new, label)
    return text[:start] + block + text[end:]


src = SOURCE.read_text(encoding="utf-8")

# Expand Name Color from 20 to 32 choices. Existing indexes stay unchanged.
src = replace_once(
    src,
    '\t\t\tColor(Lime Green)\n\t\t);\n\t\tGlobal.NamaWarna = Array(',
    '''\t\t\tColor(Lime Green),
\t\t\tCustom Color(255, 180, 145, 255),
\t\t\tCustom Color(255, 145, 90, 255),
\t\t\tCustom Color(255, 165, 205, 255),
\t\t\tCustom Color(255, 70, 220, 255),
\t\t\tCustom Color(230, 100, 255, 255),
\t\t\tCustom Color(155, 165, 255, 255),
\t\t\tCustom Color(105, 100, 255, 255),
\t\t\tCustom Color(80, 110, 255, 255),
\t\t\tCustom Color(70, 255, 255, 255),
\t\t\tCustom Color(110, 245, 210, 255),
\t\t\tCustom Color(80, 240, 170, 255),
\t\t\tCustom Color(190, 255, 80, 255)
\t\t);
\t\tGlobal.NamaWarna = Array(''',
    "append 12 name colors",
)

src = replace_once(
    src,
    '\t\t\tCustom String("Hijau Limau")\n\t\t);\n\t\tGlobal.NamaWarnaEN = Array(',
    '''\t\t\tCustom String("Hijau Limau"),
\t\t\tCustom String("Persik Bersinar"),
\t\t\tCustom String("Aprikot Neon"),
\t\t\tCustom String("Bunga Sakura"),
\t\t\tCustom String("Magenta Panas"),
\t\t\tCustom String("Fuchsia Mimpi"),
\t\t\tCustom String("Periwinkle Lembut"),
\t\t\tCustom String("Indigo Elektrik"),
\t\t\tCustom String("Biru Royal"),
\t\t\tCustom String("Cyan Neon"),
\t\t\tCustom String("Busa Laut"),
\t\t\tCustom String("Giok Bersinar"),
\t\t\tCustom String("Chartreuse Neon")
\t\t);
\t\tGlobal.NamaWarnaEN = Array(''',
    "append Indonesian color names",
)

src = replace_once(
    src,
    '\t\t\tCustom String("Lime Green")\n\t\t);\n\t\tGlobal.NamaWarnaTH = Array(',
    '''\t\t\tCustom String("Lime Green"),
\t\t\tCustom String("Peach Glow"),
\t\t\tCustom String("Apricot Neon"),
\t\t\tCustom String("Cherry Blossom"),
\t\t\tCustom String("Hot Magenta"),
\t\t\tCustom String("Fuchsia Dream"),
\t\t\tCustom String("Soft Periwinkle"),
\t\t\tCustom String("Electric Indigo"),
\t\t\tCustom String("Royal Blue"),
\t\t\tCustom String("Cyan Neon"),
\t\t\tCustom String("Seafoam"),
\t\t\tCustom String("Jade Glow"),
\t\t\tCustom String("Neon Chartreuse")
\t\t);
\t\tGlobal.NamaWarnaTH = Array(''',
    "append English color names",
)

src = replace_once(
    src,
    '\t\t\tCustom String("เขียวมะนาว")\n\t\t);\n\t\tGlobal.NamaBahasa = Array(',
    '''\t\t\tCustom String("เขียวมะนาว"),
\t\t\tCustom String("พีชเรืองแสง"),
\t\t\tCustom String("แอปริคอตนีออน"),
\t\t\tCustom String("ซากุระอ่อน"),
\t\t\tCustom String("แมเจนตาร้อน"),
\t\t\tCustom String("ฟูเชียฝัน"),
\t\t\tCustom String("เพอริวิงเคิลอ่อน"),
\t\t\tCustom String("อินดิโกไฟฟ้า"),
\t\t\tCustom String("น้ำเงินรอยัล"),
\t\t\tCustom String("ไซแอนนีออน"),
\t\t\tCustom String("ซีโฟม"),
\t\t\tCustom String("หยกเรืองแสง"),
\t\t\tCustom String("ชาร์เทรสนีออน")
\t\t);
\t\tGlobal.NamaBahasa = Array(''',
    "append Thai color names",
)

# Main Menu keeps its input/instruction color, while the selected page uses
# exactly the primary color of its corresponding submenu.
main_color = '''Event Player.KursorUtama == 0 ? Custom Color(55, 235, 245, 255)
\t\t\t: Event Player.KursorUtama == 1 ? Custom Color(90, 180, 255, 255)
\t\t\t: Event Player.KursorUtama == 2 ? Global.DaftarWarna[Event Player.KursorWarna]
\t\t\t: Event Player.KursorUtama == 3 ? Custom Color(190, 120, 255, 255)
\t\t\t: Event Player.KursorUtama == 4 ? Custom Color(255, 80, 80, 255)
\t\t\t: Event Player.KursorUtama == 5 ? Custom Color(255, 185, 90, 255)
\t\t\t: Event Player.KursorUtama == 6 ? Custom Color(115, 235, 170, 255)
\t\t\t: Custom Color(235, 135, 255, 255)'''
src = replace_in_rule(
    src,
    "91a - Subrutin:",
    'Color(White), Custom Color(210, 230, 255, 255), Custom Color(255, 185, 65, 255), Visible To and String, Visible Never);',
    f'Color(White), Custom Color(210, 230, 255, 255), {main_color}, Visible To and String, Visible Never);',
    "main menu page palette",
)

# Keep input colors untouched; only change duplicated submenu primary colors.
src = replace_in_rule(
    src,
    "91h - Subrutin:",
    'Custom Color(255, 85, 85, 255), Visible To and String, Visible Never);',
    'Custom Color(255, 185, 90, 255), Visible To and String, Visible Never);',
    "Unkillable amber",
)
src = replace_in_rule(
    src,
    "91i - Subrutin:",
    'Custom Color(195, 120, 255, 255), Visible To and String, Visible Never);',
    'Custom Color(115, 235, 170, 255), Visible To and String, Visible Never);',
    "Voice mint",
)
src = replace_in_rule(
    src,
    "91j - Subrutin:",
    'Custom Color(195, 120, 255, 255), Visible To String and Color, Visible Never);',
    'Custom Color(235, 135, 255, 255), Visible To String and Color, Visible Never);',
    "Player Icon fuchsia lavender",
)

SOURCE.write_text(src, encoding="utf-8")

# Static contract: palette, matching parent/submenu colors and 32 name colors.
val = VALIDATOR.read_text(encoding="utf-8")
check = r'''

def check_menu_palette_and_name_colors(checks: Checks, source: str, rules: list[Rule]) -> None:
    colors = [re.sub(r"\s+", " ", item).strip() for item in top_level_items(array_body(source, "Global.DaftarWarna"))]
    id_names = custom_strings(array_body(source, "Global.NamaWarna"))
    en_names = custom_strings(array_body(source, "Global.NamaWarnaEN"))
    th_names = custom_strings(array_body(source, "Global.NamaWarnaTH"))
    checks.equal(len(colors), 32, "Name Color: 32 colori")
    checks.equal(len(id_names), 32, "Name Color: 32 nomi ID")
    checks.equal(len(en_names), 32, "Name Color: 32 nomi EN")
    checks.equal(len(th_names), 32, "Name Color: 32 nomi TH")

    expected_tail = [
        "Custom Color(255, 180, 145, 255)",
        "Custom Color(255, 145, 90, 255)",
        "Custom Color(255, 165, 205, 255)",
        "Custom Color(255, 70, 220, 255)",
        "Custom Color(230, 100, 255, 255)",
        "Custom Color(155, 165, 255, 255)",
        "Custom Color(105, 100, 255, 255)",
        "Custom Color(80, 110, 255, 255)",
        "Custom Color(70, 255, 255, 255)",
        "Custom Color(110, 245, 210, 255)",
        "Custom Color(80, 240, 170, 255)",
        "Custom Color(190, 255, 80, 255)",
    ]
    checks.equal(colors[-12:], expected_tail, "Name Color: nuove 12 tonalità")
    checks.equal(
        en_names[-12:],
        ["Peach Glow", "Apricot Neon", "Cherry Blossom", "Hot Magenta", "Fuchsia Dream", "Soft Periwinkle", "Electric Indigo", "Royal Blue", "Cyan Neon", "Seafoam", "Jade Glow", "Neon Chartreuse"],
        "Name Color: nomi EN nuove tonalità",
    )

    def renderer(subroutine: str) -> str:
        matches = rules_containing(rules, "Subroutine;", f"{subroutine};")
        checks.equal(len(matches), 1, f"palette renderer {subroutine}")
        return matches[0].body if matches else ""

    main = renderer("GambarUtama")
    soundtrack = renderer("GambarMusik")
    camera = renderer("GambarKamera")
    name_color = renderer("GambarWarna")
    language = renderer("GambarBahasa")
    revenge = renderer("GambarBalasDendam")
    unkillable = renderer("GambarUnkillable")
    voice = renderer("GambarSuara")
    icon = renderer("GambarIkon")

    # Inputs/subheaders keep their established light colors.
    for body, token, label in (
        (main, "Custom Color(210, 230, 255, 255)", "main"),
        (soundtrack, "Custom Color(205, 235, 255, 255)", "soundtrack"),
        (camera, "Custom Color(205, 235, 255, 255)", "camera"),
        (name_color, "Custom Color(220, 235, 255, 255)", "name color"),
        (language, "Custom Color(225, 210, 255, 255)", "language"),
        (revenge, "Custom Color(255, 220, 220, 255)", "revenge"),
        (unkillable, "Custom Color(255, 220, 220, 255)", "unkillable"),
        (voice, "Custom Color(225, 215, 255, 255)", "voice"),
        (icon, "Custom Color(225, 215, 255, 255)", "player icon"),
    ):
        checks.require(token in body, f"palette input modificata per {label}")

    # Primary submenu colors are unique, except Name Color which intentionally
    # previews the currently highlighted name color.
    for body, token, label in (
        (soundtrack, "Custom Color(55, 235, 245, 255)", "soundtrack aqua"),
        (camera, "Custom Color(90, 180, 255, 255)", "camera blue"),
        (name_color, "Global.DaftarWarna[Event Player.KursorWarna]", "name color preview"),
        (language, "Custom Color(190, 120, 255, 255)", "language violet"),
        (revenge, "Custom Color(255, 80, 80, 255)", "revenge red"),
        (unkillable, "Custom Color(255, 185, 90, 255)", "unkillable amber"),
        (voice, "Custom Color(115, 235, 170, 255)", "voice mint"),
        (icon, "Custom Color(235, 135, 255, 255)", "player icon fuchsia"),
    ):
        checks.require(token in body, f"palette submenu errata: {label}")

    for token in (
        "Event Player.KursorUtama == 0 ? Custom Color(55, 235, 245, 255)",
        "Event Player.KursorUtama == 1 ? Custom Color(90, 180, 255, 255)",
        "Event Player.KursorUtama == 2 ? Global.DaftarWarna[Event Player.KursorWarna]",
        "Event Player.KursorUtama == 3 ? Custom Color(190, 120, 255, 255)",
        "Event Player.KursorUtama == 4 ? Custom Color(255, 80, 80, 255)",
        "Event Player.KursorUtama == 5 ? Custom Color(255, 185, 90, 255)",
        "Event Player.KursorUtama == 6 ? Custom Color(115, 235, 170, 255)",
        "Custom Color(235, 135, 255, 255)",
    ):
        checks.require(token in main, f"Main Menu non corrisponde al sottomenu: {token}")
'''
if 'def check_menu_palette_and_name_colors(' not in val:
    marker = '\ndef main() -> None:\n'
    if val.count(marker) != 1:
        raise SystemExit("validator main marker not found")
    val = val.replace(marker, check + marker, 1)
    call = '        check_menus(checks, source, rules, subroutines)\n'
    if val.count(call) != 1:
        raise SystemExit("validator check_menus call not found")
    val = val.replace(call, call + '        check_menu_palette_and_name_colors(checks, source, rules)\n', 1)
VALIDATOR.write_text(val, encoding="utf-8")

readme = README.read_text(encoding="utf-8")
for line in (
    '- Palette menu coordinata: ogni voce del Main Menu usa lo stesso colore principale del proprio sottomenu, mentre i colori degli input restano invariati.',
    '- `Name Color` offre 32 tonalità: le 20 originali più 12 nuove sfumature pastel/neon.',
):
    if line not in readme:
        readme += '\n' + line
readme += '\n'
README.write_text(readme, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
section = '''\n\n### Palette menu coordinata\n\nIl Main Menu ora eredita visivamente il colore principale del sottomenu evidenziato: Soundtrack aqua, Camera blu elettrico, Name Color usa la preview del colore evidenziato, HUD Language viola, Revenge rosso corallo, Unkillable ambra, Voice Modifier mint e Player Icon fucsia-lavanda. I colori chiari degli input/comandi non sono stati modificati. `DaftarWarna` è stato esteso da 20 a 32 voci mantenendo invariati i primi 20 indici e aggiungendo 12 tonalità pastel/neon con nomi EN/ID/TH allineati.\n'''
if '### Palette menu coordinata' not in project:
    project += section
PROJECT.write_text(project, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
for line in (
    '- **Palette menu live:** scorrere le 8 voci del Main Menu e aprire ogni sottomenu; il colore principale della voce deve coincidere con quello del sottomenu, mentre il colore degli input deve restare quello precedente.\n',
    '- **Name Color 32 live:** scorrere tutte le 32 tonalità, incluse le nuove da Peach Glow a Neon Chartreuse, applicarne diverse e verificare persistenza cursore e colore nome.\n',
):
    if line not in tests:
        tests += '\n' + line
TESTS.write_text(tests, encoding="utf-8")

# Update Workshop blob marker in validation report.
data = SOURCE.read_bytes().replace(b"\r\n", b"\n")
blob = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
report = REPORT.read_text(encoding="utf-8")
report, n = re.subn(r"```text\n[0-9a-f]{40}\n```", f"```text\n{blob}\n```", report, count=1)
if n != 1:
    raise SystemExit("validation report blob marker not found")
REPORT.write_text(report, encoding="utf-8")
