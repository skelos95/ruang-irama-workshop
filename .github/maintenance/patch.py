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


src = SOURCE.read_text(encoding="utf-8")

# 37th state: index 0 means no icon. All original Workshop icons shift by one.
src = replace_once(
    src,
    "\t\tGlobal.DaftarIkon = Array(\n\t\t\tIcon String(Arrow: Down),",
    "\t\tGlobal.DaftarIkon = Array(\n\t\t\tCustom String(\"\"),\n\t\t\tIcon String(Arrow: Down),",
    "prepend no-icon value",
)
src = replace_once(
    src,
    "\t\tGlobal.NamaIkon = Array(\n\t\t\tCustom String(\"ARROW: DOWN\"),",
    "\t\tGlobal.NamaIkon = Array(\n\t\t\tCustom String(\"NOTHING\"),\n\t\t\tCustom String(\"ARROW: DOWN\"),",
    "prepend no-icon name",
)

# The RGB loop does not claim that Icon String can be recolored.
src = replace_once(
    src,
    'rule("00r - Global: RGB pastel neon lento untuk judul, timer, ikon, dan efek")',
    'rule("00r - Global: RGB pastel neon lento untuk judul, timer, dan efek")',
    "RGB rule title",
)

# Restore MIN and restore the player's selected name color. Icon String remains
# the first value in the same HUD line; its native glyph color is engine-owned.
src = replace_once(
    src,
    'Custom String("{0} - {1}", Event Player, Event Player.MenitLobby)), And(Global.DiagnostikPerforma',
    'Custom String("{0} - {1} MIN", Event Player, Event Player.MenitLobby)), And(Global.DiagnostikPerforma',
    "restore MIN",
)
src = replace_once(
    src,
    'Custom String(" "), Left, -99 + Event Player.UrutanHUD, Color(White), Global.RGB, Color(White),',
    'Custom String(" "), Left, -99 + Event Player.UrutanHUD, Color(White), Event Player.WarnaNama, Color(White),',
    "left roster name color",
)
src = replace_once(
    src,
    'Right, -99 + Event Player.UrutanHUD,\n\t\t\tColor(White), Global.RGB, Color(White), Visible To String and Color, Visible Never);',
    'Right, -99 + Event Player.UrutanHUD,\n\t\t\tColor(White), Event Player.WarnaNama, Color(White), Visible To String and Color, Visible Never);',
    "right roster name color",
)

# Default selection is NOTHING.
src = replace_once(
    src,
    "\t\tEvent Player.IndeksIkon = 17;\n\t\tEvent Player.KursorIkon = 17;",
    "\t\tEvent Player.IndeksIkon = 0;\n\t\tEvent Player.KursorIkon = 0;",
    "default no icon",
)

# Main menu: localize the NOTHING state without altering the standardized names
# of the actual Workshop icons.
src = replace_once(
    src,
    'Custom String("7 - PLAYER ICON\\nCURRENT: {0} {1}", Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon])',
    'Event Player.IndeksIkon == 0 ? Custom String("7 - PLAYER ICON\\nCURRENT: NOTHING") : Custom String("7 - PLAYER ICON\\nCURRENT: {0} {1}", Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon])',
    "main menu EN no icon",
)
src = replace_once(
    src,
    'Custom String("7 - IKON PEMAIN\\nSAAT INI: {0} {1}", Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon])',
    'Event Player.IndeksIkon == 0 ? Custom String("7 - IKON PEMAIN\\nSAAT INI: TIDAK ADA") : Custom String("7 - IKON PEMAIN\\nSAAT INI: {0} {1}", Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon])',
    "main menu ID no icon",
)
src = replace_once(
    src,
    'Custom String("7 - ไอคอนผู้เล่น\\nปัจจุบัน: {0} {1}", Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon])',
    'Event Player.IndeksIkon == 0 ? Custom String("7 - ไอคอนผู้เล่น\\nปัจจุบัน: ไม่มี") : Custom String("7 - ไอคอนผู้เล่น\\nปัจจุบัน: {0} {1}", Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon])',
    "main menu TH no icon",
)

# Dedicated Menu 7: 37 entries and fixed menu colors. No Global.RGB here.
for old, new, label in (
    ('7 - PLAYER ICON {0}/36\\nCURRENT:', '7 - PLAYER ICON {0}/37\\nCURRENT:', "menu icon EN count"),
    ('7 - IKON PEMAIN {0}/36\\nSAAT INI:', '7 - IKON PEMAIN {0}/37\\nSAAT INI:', "menu icon ID count"),
    ('7 - ไอคอนผู้เล่น {0}/36\\nปัจจุบัน:', '7 - ไอคอนผู้เล่น {0}/37\\nปัจจุบัน:', "menu icon TH count"),
):
    src = replace_once(src, old, new, label)
src = replace_once(
    src,
    'Top, 100, Color(White), Global.RGB, Global.RGB, Visible To String and Color, Visible Never);',
    'Top, 100, Color(White), Custom Color(225, 215, 255, 255), Custom Color(195, 120, 255, 255), Visible To String and Color, Visible Never);',
    "remove RGB from icon menu",
)

# Localize the no-icon row inside the dedicated menu by making index 0 explicit.
old_en = 'Event Player.IndeksBahasa == 0 ? Custom String("{0}\\n> {1} {2}", Custom String("7 - PLAYER ICON {0}/37\\nCURRENT: {1} {2}", Event Player.KursorIkon + 1, Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon]), Global.DaftarIkon[Event Player.KursorIkon], Global.NamaIkon[Event Player.KursorIkon])'
new_en = 'Event Player.IndeksBahasa == 0 ? Custom String("{0}\\n> {1}", Event Player.IndeksIkon == 0 ? Custom String("7 - PLAYER ICON {0}/37\\nCURRENT: NOTHING", Event Player.KursorIkon + 1) : Custom String("7 - PLAYER ICON {0}/37\\nCURRENT: {1} {2}", Event Player.KursorIkon + 1, Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon]), Event Player.KursorIkon == 0 ? Custom String("NOTHING") : Custom String("{0} {1}", Global.DaftarIkon[Event Player.KursorIkon], Global.NamaIkon[Event Player.KursorIkon]))'
src = replace_once(src, old_en, new_en, "dedicated menu EN nothing")
old_id = ': Event Player.IndeksBahasa == 1 ? Custom String("{0}\\n> {1} {2}", Custom String("7 - IKON PEMAIN {0}/37\\nSAAT INI: {1} {2}", Event Player.KursorIkon + 1, Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon]), Global.DaftarIkon[Event Player.KursorIkon], Global.NamaIkon[Event Player.KursorIkon])'
new_id = ': Event Player.IndeksBahasa == 1 ? Custom String("{0}\\n> {1}", Event Player.IndeksIkon == 0 ? Custom String("7 - IKON PEMAIN {0}/37\\nSAAT INI: TIDAK ADA", Event Player.KursorIkon + 1) : Custom String("7 - IKON PEMAIN {0}/37\\nSAAT INI: {1} {2}", Event Player.KursorIkon + 1, Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon]), Event Player.KursorIkon == 0 ? Custom String("TIDAK ADA") : Custom String("{0} {1}", Global.DaftarIkon[Event Player.KursorIkon], Global.NamaIkon[Event Player.KursorIkon]))'
src = replace_once(src, old_id, new_id, "dedicated menu ID nothing")
old_th = ': Custom String("{0}\\n> {1} {2}", Custom String("7 - ไอคอนผู้เล่น {0}/37\\nปัจจุบัน: {1} {2}", Event Player.KursorIkon + 1, Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon]), Global.DaftarIkon[Event Player.KursorIkon], Global.NamaIkon[Event Player.KursorIkon]),'
new_th = ': Custom String("{0}\\n> {1}", Event Player.IndeksIkon == 0 ? Custom String("7 - ไอคอนผู้เล่น {0}/37\\nปัจจุบัน: ไม่มี", Event Player.KursorIkon + 1) : Custom String("7 - ไอคอนผู้เล่น {0}/37\\nปัจจุบัน: {1} {2}", Event Player.KursorIkon + 1, Global.DaftarIkon[Event Player.IndeksIkon], Global.NamaIkon[Event Player.IndeksIkon]), Event Player.KursorIkon == 0 ? Custom String("ไม่มี") : Custom String("{0} {1}", Global.DaftarIkon[Event Player.KursorIkon], Global.NamaIkon[Event Player.KursorIkon])), '
src = replace_once(src, old_th, new_th, "dedicated menu TH nothing")

# Apply message for index 0 is localized too.
src = replace_once(
    src,
    '"Player icon applied: {0}.", Global.NamaIkon[Event Player.IndeksIkon])',
    '"Player icon applied: {0}.", Event Player.IndeksIkon == 0 ? Custom String("NOTHING") : Global.NamaIkon[Event Player.IndeksIkon])',
    "apply EN nothing",
)
src = replace_once(
    src,
    '"Ikon pemain diterapkan: {0}.", Global.NamaIkon[Event Player.IndeksIkon])',
    '"Ikon pemain diterapkan: {0}.", Event Player.IndeksIkon == 0 ? Custom String("TIDAK ADA") : Global.NamaIkon[Event Player.IndeksIkon])',
    "apply ID nothing",
)
src = replace_once(
    src,
    '"ใช้ไอคอนผู้เล่นแล้ว: {0}", Global.NamaIkon[Event Player.IndeksIkon])',
    '"ใช้ไอคอนผู้เล่นแล้ว: {0}", Event Player.IndeksIkon == 0 ? Custom String("ไม่มี") : Global.NamaIkon[Event Player.IndeksIkon])',
    "apply TH nothing",
)

SOURCE.write_text(src, encoding="utf-8")

# ---------------- validator contract ----------------
val = VALIDATOR.read_text(encoding="utf-8")
val = replace_once(
    val,
    '    expected_icons = [\n        "Icon String(Arrow: Down)",',
    '    expected_icons = [\n        \'Custom String("")\',\n        "Icon String(Arrow: Down)",',
    "validator no-icon expression",
)
val = replace_once(
    val,
    '    expected_names = [\n        "ARROW: DOWN",',
    '    expected_names = [\n        "NOTHING",\n        "ARROW: DOWN",',
    "validator no-icon name",
)
val = replace_once(val, 'checks.equal(actual_icons, expected_icons, "36 icone Workshop del menu 7")', 'checks.equal(actual_icons, expected_icons, "37 voci del menu 7: niente + 36 icone Workshop")', "validator icon count label")
val = replace_once(val, 'checks.equal(custom_strings(array_body(source, "Global.NamaIkon")), expected_names, "nomi delle 36 icone")', 'checks.equal(custom_strings(array_body(source, "Global.NamaIkon")), expected_names, "nomi delle 37 voci icona")', "validator name count label")
val = replace_once(
    val,
    'checks.require("Event Player.IndeksIkon = 17;" in source and "Event Player.KursorIkon = 17;" in source, "icone: default Heart non inizializzato")',
    'checks.require("Event Player.IndeksIkon = 0;" in source and "Event Player.KursorIkon = 0;" in source, "icone: default NOTHING non inizializzato")',
    "validator default nothing",
)
val = replace_once(
    val,
    '        checks.require(body.count("Global.RGB") >= 2, "le due liste non usano il colore RGB per le icone")',
    '        checks.require("Global.RGB" not in body, "roster: RGB non deve colorare il nome player")\n        checks.require(body.count("Event Player.WarnaNama") >= 2, "roster: entrambe le liste devono usare il colore nome scelto")\n        checks.require('Custom String("{0} - {1} MIN", Event Player, Event Player.MenitLobby)' in body, "roster sinistro: MIN assente")',
    "validator roster colors/min",
)
val = replace_once(
    val,
    '        checks.require("/36" in renderers[0].body and "Global.RGB" in renderers[0].body, "menu 7 non mostra 36 icone con colore RGB")',
    '        checks.require("/37" in renderers[0].body, "menu 7 non mostra 37 voci")\n        checks.require("Global.RGB" not in renderers[0].body, "menu 7: RGB deve restare fuori dal menu icone")\n        checks.require("NOTHING" in renderers[0].body and "TIDAK ADA" in renderers[0].body and "ไม่มี" in renderers[0].body, "menu 7: voce niente non localizzata")',
    "validator fixed menu colors",
)
VALIDATOR.write_text(val, encoding="utf-8")

# ---------------- docs ----------------
readme = README.read_text(encoding="utf-8")
readme = readme.replace(
    '- Menu 7 `Player Icon`: 36 icone Workshop selezionabili, con cursore persistente e feedback di applicazione.',
    '- Menu 7 `Player Icon`: 37 voci (`Niente` + 36 icone Workshop), con `Niente` predefinito, cursore persistente e feedback di applicazione.',
)
readme = readme.replace(
    '- Nelle liste player l’icona scelta precede l’icona eroe; la riga sinistra mostra soltanto il tempo e la riga destra soltanto il genere scelto, senza i prefissi `CHILL for` / `soundtrack`.',
    '- Nelle liste player l’icona scelta precede l’icona eroe; la riga sinistra mostra il tempo come `N MIN` e la riga destra soltanto il genere scelto, senza i prefissi `CHILL for` / `soundtrack`. `Icon String` mantiene il colore nativo del client; il colore nome resta quello scelto nel menu colore.',
)
README.write_text(readme, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
project = project.replace(
    'Il menu 7 contiene le 36 icone standard disponibili tramite `Icon String`, da `Arrow: Down` a `X`. La scelta è memorizzata in `IndeksIkon` e il cursore in `KursorIkon`; il default è `Heart`.',
    'Il menu 7 contiene 37 voci: `Niente` all’indice 0 e le 36 icone standard disponibili tramite `Icon String`, da `Arrow: Down` a `X`. La scelta è memorizzata in `IndeksIkon` e il cursore in `KursorIkon`; il default è `Niente`.',
)
project = project.replace(
    'Le righe del roster sono state compattate: a sinistra resta il numero di minuti, a destra il genere scelto (o il placeholder se non è stato ancora scelto).',
    'Le righe del roster sono state compattate: a sinistra resta `N MIN`, a destra il genere scelto (o il placeholder se non è stato ancora scelto). Il Menu 7 usa colori fissi. In HUD, `Icon String` conserva il colore nativo del glifo del client; il colore testuale della riga resta il colore nome scelto dal player.',
)
PROJECT.write_text(project, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
tests = tests.replace(
    '- **Player Icon live:** aprire menu 7, scorrere tutte le 36 icone, applicarne varie e verificare che compaiano nelle due liste prima dell’icona eroe, senza alcuna icona sopra al personaggio.',
    '- **Player Icon live:** aprire menu 7, verificare 37 voci con `Niente` come default, scorrere le 36 icone reali e applicarne varie; l’icona deve comparire nelle due liste prima dell’icona eroe e non deve apparire nulla sopra al personaggio.',
)
tests = tests.replace(
    '- **Liste compatte live:** a sinistra verificare `icona + eroe + nome + N MIN` senza `CHILL for`; a destra `icona + eroe + nome + genere` senza il prefisso `soundtrack`.',
    '- **Liste compatte live:** a sinistra verificare `icona + eroe + nome + N MIN` senza `CHILL for`; a destra `icona + eroe + nome + genere` senza il prefisso `soundtrack`. Il nome deve conservare il colore scelto dal player e il Menu 7 non deve usare il ciclo RGB.',
)
TESTS.write_text(tests, encoding="utf-8")

# Refresh the source blob marker after the Workshop source change.
data = SOURCE.read_bytes().replace(b"\r\n", b"\n")
blob = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
report = REPORT.read_text(encoding="utf-8")
report, count = re.subn(r"```text\n[0-9a-f]{40}\n```", f"```text\n{blob}\n```", report, count=1)
if count != 1:
    raise SystemExit("docs/VALIDAZIONE.md blob marker not found")
REPORT.write_text(report, encoding="utf-8")
