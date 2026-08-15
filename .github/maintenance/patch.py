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


def one(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"{label}: expected 1, found {n}")
    return text.replace(old, new, 1)


src = SOURCE.read_text(encoding="utf-8")

src = one(src,
    "\t\tGlobal.DaftarIkon = Array(\n\t\t\tIcon String(Arrow: Down),",
    "\t\tGlobal.DaftarIkon = Array(\n\t\t\tCustom String(\"\"),\n\t\t\tIcon String(Arrow: Down),",
    "prepend nothing icon")
src = one(src,
    "\t\tGlobal.NamaIkon = Array(\n\t\t\tCustom String(\"ARROW: DOWN\"),",
    "\t\tGlobal.NamaIkon = Array(\n\t\t\tCustom String(\"NOTHING\"),\n\t\t\tCustom String(\"ARROW: DOWN\"),",
    "prepend nothing name")
src = one(src,
    'rule("00r - Global: RGB pastel neon lento untuk judul, timer, ikon, dan efek")',
    'rule("00r - Global: RGB pastel neon lento untuk judul, timer, dan efek")',
    "RGB rule title")
src = one(src,
    'Custom String("{0} - {1}", Event Player, Event Player.MenitLobby)), And(Global.DiagnostikPerforma',
    'Custom String("{0} - {1} MIN", Event Player, Event Player.MenitLobby)), And(Global.DiagnostikPerforma',
    "restore MIN")
src = one(src,
    'Custom String(" "), Left, -99 + Event Player.UrutanHUD, Color(White), Global.RGB, Color(White),',
    'Custom String(" "), Left, -99 + Event Player.UrutanHUD, Color(White), Event Player.WarnaNama, Color(White),',
    "left name color")
src = one(src,
    'Right, -99 + Event Player.UrutanHUD,\n\t\t\tColor(White), Global.RGB, Color(White), Visible To String and Color, Visible Never);',
    'Right, -99 + Event Player.UrutanHUD,\n\t\t\tColor(White), Event Player.WarnaNama, Color(White), Visible To String and Color, Visible Never);',
    "right name color")
src = one(src,
    "\t\tEvent Player.IndeksIkon = 17;\n\t\tEvent Player.KursorIkon = 17;",
    "\t\tEvent Player.IndeksIkon = 0;\n\t\tEvent Player.KursorIkon = 0;",
    "default nothing")

for old, new in (
    ('7 - PLAYER ICON {0}/36\\nCURRENT:', '7 - PLAYER ICON {0}/37\\nCURRENT:'),
    ('7 - IKON PEMAIN {0}/36\\nSAAT INI:', '7 - IKON PEMAIN {0}/37\\nSAAT INI:'),
    ('7 - ไอคอนผู้เล่น {0}/36\\nปัจจุบัน:', '7 - ไอคอนผู้เล่น {0}/37\\nปัจจุบัน:'),
):
    src = one(src, old, new, old)

src = one(src,
    'Top, 100, Color(White), Global.RGB, Global.RGB, Visible To String and Color, Visible Never);',
    'Top, 100, Color(White), Custom Color(225, 215, 255, 255), Custom Color(195, 120, 255, 255), Visible To String and Color, Visible Never);',
    "fixed icon menu colors")

src = one(src,
    'Custom String("7 - PLAYER ICON\\nCURRENT: {0} {1}", Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon])',
    'Event Player.IndeksIkon == 0 ? Custom String("7 - PLAYER ICON\\nCURRENT: NOTHING") : Custom String("7 - PLAYER ICON\\nCURRENT: {0} {1}", Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon])',
    "main EN nothing")
src = one(src,
    'Custom String("7 - IKON PEMAIN\\nSAAT INI: {0} {1}", Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon])',
    'Event Player.IndeksIkon == 0 ? Custom String("7 - IKON PEMAIN\\nSAAT INI: TIDAK ADA") : Custom String("7 - IKON PEMAIN\\nSAAT INI: {0} {1}", Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon])',
    "main ID nothing")
src = one(src,
    'Custom String("7 - ไอคอนผู้เล่น\\nปัจจุบัน: {0} {1}", Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon])',
    'Event Player.IndeksIkon == 0 ? Custom String("7 - ไอคอนผู้เล่น\\nปัจจุบัน: ไม่มี") : Custom String("7 - ไอคอนผู้เล่น\\nปัจจุบัน: {0} {1}", Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon])',
    "main TH nothing")

src = one(src,
    'Event Player.IndeksBahasa == 0 ? Custom String("{0}\\n> {1} {2}", Custom String("7 - PLAYER ICON {0}/37\\nCURRENT: {1} {2}", Event Player.KursorIkon + 1, Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon]), Global.DaftarIkon[Event Player.KursorIkon], Global.NamaIkon[Event Player.KursorIkon])',
    'Event Player.IndeksBahasa == 0 ? Custom String("{0}\\n> {1}", Event Player.IndeksIkon == 0 ? Custom String("7 - PLAYER ICON {0}/37\\nCURRENT: NOTHING", Event Player.KursorIkon + 1) : Custom String("7 - PLAYER ICON {0}/37\\nCURRENT: {1} {2}", Event Player.KursorIkon + 1, Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon]), Event Player.KursorIkon == 0 ? Custom String("NOTHING") : Custom String("{0} {1}", Global.DaftarIkon[Event Player.KursorIkon], Global.NamaIkon[Event Player.KursorIkon]))',
    "menu EN nothing")
src = one(src,
    ': Event Player.IndeksBahasa == 1 ? Custom String("{0}\\n> {1} {2}", Custom String("7 - IKON PEMAIN {0}/37\\nSAAT INI: {1} {2}", Event Player.KursorIkon + 1, Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon]), Global.DaftarIkon[Event Player.KursorIkon], Global.NamaIkon[Event Player.KursorIkon])',
    ': Event Player.IndeksBahasa == 1 ? Custom String("{0}\\n> {1}", Event Player.IndeksIkon == 0 ? Custom String("7 - IKON PEMAIN {0}/37\\nSAAT INI: TIDAK ADA", Event Player.KursorIkon + 1) : Custom String("7 - IKON PEMAIN {0}/37\\nSAAT INI: {1} {2}", Event Player.KursorIkon + 1, Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon]), Event Player.KursorIkon == 0 ? Custom String("TIDAK ADA") : Custom String("{0} {1}", Global.DaftarIkon[Event Player.KursorIkon], Global.NamaIkon[Event Player.KursorIkon]))',
    "menu ID nothing")
src = one(src,
    ': Custom String("{0}\\n> {1} {2}", Custom String("7 - ไอคอนผู้เล่น {0}/37\\nปัจจุบัน: {1} {2}", Event Player.KursorIkon + 1, Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon]), Global.DaftarIkon[Event Player.KursorIkon], Global.NamaIkon[Event Player.KursorIkon]),',
    ': Custom String("{0}\\n> {1}", Event Player.IndeksIkon == 0 ? Custom String("7 - ไอคอนผู้เล่น {0}/37\\nปัจจุบัน: ไม่มี", Event Player.KursorIkon + 1) : Custom String("7 - ไอคอนผู้เล่น {0}/37\\nปัจจุบัน: {1} {2}", Event Player.KursorIkon + 1, Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon]), Event Player.KursorIkon == 0 ? Custom String("ไม่มี") : Custom String("{0} {1}", Global.DaftarIkon[Event Player.KursorIkon], Global.NamaIkon[Event Player.KursorIkon])),',
    "menu TH nothing")

for old, new in (
    ('"Player icon applied: {0}.", Global.NamaIkon[Event Player.IndeksIkon])', '"Player icon applied: {0}.", Event Player.IndeksIkon == 0 ? Custom String("NOTHING") : Global.NamaIkon[Event Player.IndeksIkon])'),
    ('"Ikon pemain diterapkan: {0}.", Global.NamaIkon[Event Player.IndeksIkon])', '"Ikon pemain diterapkan: {0}.", Event Player.IndeksIkon == 0 ? Custom String("TIDAK ADA") : Global.NamaIkon[Event Player.IndeksIkon])'),
    ('"ใช้ไอคอนผู้เล่นแล้ว: {0}", Global.NamaIkon[Event Player.IndeksIkon])', '"ใช้ไอคอนผู้เล่นแล้ว: {0}", Event Player.IndeksIkon == 0 ? Custom String("ไม่มี") : Global.NamaIkon[Event Player.IndeksIkon])'),
):
    src = one(src, old, new, "localized apply nothing")

SOURCE.write_text(src, encoding="utf-8")

val = VALIDATOR.read_text(encoding="utf-8")
val = one(val,
    '    expected_icons = [\n        "Icon String(Arrow: Down)",',
    '    expected_icons = [\n        \'Custom String("")\',\n        "Icon String(Arrow: Down)",',
    "validator icon nothing")
val = one(val,
    '    expected_names = [\n        "ARROW: DOWN",',
    '    expected_names = [\n        "NOTHING",\n        "ARROW: DOWN",',
    "validator icon name nothing")
val = one(val, 'checks.equal(actual_icons, expected_icons, "36 icone Workshop del menu 7")', 'checks.equal(actual_icons, expected_icons, "37 voci menu 7: niente + 36 icone Workshop")', "validator count")
val = one(val, 'checks.equal(custom_strings(array_body(source, "Global.NamaIkon")), expected_names, "nomi delle 36 icone")', 'checks.equal(custom_strings(array_body(source, "Global.NamaIkon")), expected_names, "nomi delle 37 voci icona")', "validator names")
val = one(val,
    'checks.require("Event Player.IndeksIkon = 17;" in source and "Event Player.KursorIkon = 17;" in source, "icone: default Heart non inizializzato")',
    'checks.require("Event Player.IndeksIkon = 0;" in source and "Event Player.KursorIkon = 0;" in source, "icone: default NOTHING non inizializzato")',
    "validator default")
old_roster = '        checks.require(body.count("Global.RGB") >= 2, "le due liste non usano il colore RGB per le icone")'
new_roster = '''        checks.require("Global.RGB" not in body, "roster: RGB non deve colorare il nome player")
        checks.require(body.count("Event Player.WarnaNama") >= 2, "roster: entrambe le liste devono usare il colore nome scelto")
        checks.require('Custom String("{0} - {1} MIN", Event Player, Event Player.MenitLobby)' in body, "roster sinistro: MIN assente")'''
val = one(val, old_roster, new_roster, "validator roster")
old_renderer = '        checks.require("/36" in renderers[0].body and "Global.RGB" in renderers[0].body, "menu 7 non mostra 36 icone con colore RGB")'
new_renderer = '''        checks.require("/37" in renderers[0].body, "menu 7 non mostra 37 voci")
        checks.require("Global.RGB" not in renderers[0].body, "menu 7: RGB deve restare fuori dal menu icone")
        checks.require("NOTHING" in renderers[0].body and "TIDAK ADA" in renderers[0].body and "ไม่มี" in renderers[0].body, "menu 7: voce niente non localizzata")'''
val = one(val, old_renderer, new_renderer, "validator menu renderer")
VALIDATOR.write_text(val, encoding="utf-8")

readme = README.read_text(encoding="utf-8")
readme = readme.replace('Menu 7 `Player Icon`: 36 icone Workshop selezionabili', 'Menu 7 `Player Icon`: 37 voci (`Niente` + 36 icone Workshop)')
readme = readme.replace('la riga sinistra mostra soltanto il tempo', 'la riga sinistra mostra il tempo come `N MIN`')
README.write_text(readme, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
project = project.replace('Il menu 7 contiene le 36 icone standard disponibili tramite `Icon String`, da `Arrow: Down` a `X`.', 'Il menu 7 contiene 37 voci: `Niente` all’indice 0 più le 36 icone standard disponibili tramite `Icon String`, da `Arrow: Down` a `X`.')
project = project.replace('il default è `Heart`.', 'il default è `Niente`.')
project = project.replace('a sinistra resta il numero di minuti,', 'a sinistra resta `N MIN`,')
if 'Icon String` mantiene il colore nativo' not in project:
    project += '\n\nNota live: `Icon String` mantiene il colore nativo del glifo e non accetta il colore del campo HUD. Per questo il Menu 7 usa colori fissi e il nome player conserva il colore scelto; non viene dichiarato un falso RGB sul glifo nativo.\n'
PROJECT.write_text(project, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
tests = tests.replace('scorrere tutte le 36 icone', 'verificare 37 voci con `Niente` predefinito e scorrere le 36 icone reali')
TESTS.write_text(tests, encoding="utf-8")

data = SOURCE.read_bytes().replace(b"\r\n", b"\n")
blob = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
report = REPORT.read_text(encoding="utf-8")
report, n = re.subn(r"```text\n[0-9a-f]{40}\n```", f"```text\n{blob}\n```", report, count=1)
if n != 1:
    raise SystemExit("validation blob marker not found")
REPORT.write_text(report, encoding="utf-8")
