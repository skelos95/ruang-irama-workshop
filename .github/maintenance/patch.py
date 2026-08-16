from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
README = ROOT / "README.md"
PROGETTO = ROOT / "docs" / "PROGETTO.md"
TEST_DOC = ROOT / "docs" / "TEST.md"
VALIDAZIONE = ROOT / "docs" / "VALIDAZIONE.md"
VERSION = ROOT / "VERSION"

PALETTE = {
    0: (55, 235, 245),
    1: (70, 135, 255),
    3: (185, 105, 255),
    4: (255, 75, 85),
    5: (255, 145, 55),
    6: (255, 80, 205),
    7: (170, 240, 85),
    8: (65, 225, 130),
    9: (55, 190, 170),
    10: (255, 210, 70),
    11: (255, 120, 155),
}

OLD_TO_NEW = {
    "Vector(90, 180, 255)": "Vector(70, 135, 255)",
    "Vector(190, 120, 255)": "Vector(185, 105, 255)",
    "Vector(255, 80, 80)": "Vector(255, 75, 85)",
    "Vector(255, 185, 90)": "Vector(255, 145, 55)",
    "Vector(115, 235, 170)": "Vector(65, 225, 130)",
    "Vector(235, 135, 255)": "Vector(255, 80, 205)",
    "Vector(190, 255, 80)": "Vector(170, 240, 85)",
    "Vector(255, 120, 190)": "Vector(255, 120, 155)",
}


def once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise RuntimeError(f"{label}: expected 1, found {n}")
    return text.replace(old, new, 1)


def mask(text: str) -> str:
    out=[]; q=False; esc=False
    for ch in text:
        if q:
            if esc: esc=False
            elif ch == "\\": esc=True
            elif ch == '"': q=False
            out.append("\n" if ch == "\n" else " ")
        elif ch == '"': q=True; out.append(" ")
        else: out.append(ch)
    if q: raise RuntimeError("unclosed string")
    return "".join(out)


def matching(text: str, opening: int) -> int:
    clean=mask(text); depth=1
    for i in range(opening+1, len(clean)):
        if clean[i] == "{": depth += 1
        elif clean[i] == "}":
            depth -= 1
            if depth == 0: return i
    raise RuntimeError("unclosed rule")


def rule_span(text: str, name: str):
    start=text.index(f'rule("{name}")'); opening=text.index("{", start); end=matching(text, opening)+1
    return start,end,text[start:end]


def replace_actions(rule: str, actions: str) -> str:
    clean=mask(rule); m=re.search(r"(?m)^\s*actions\s*\{", clean)
    if not m: raise RuntimeError("actions missing")
    opening=clean.find("{", m.start()); closing=matching(rule, opening)
    return rule[:opening+1] + "\n" + actions.rstrip() + "\n\t" + rule[closing:]

source=SOURCE.read_text(encoding="utf-8")
name="91k - Subrutin: Transisi warna menu tanpa lompatan"
start,end,rule=rule_span(source,name)
idx="(Event Player.HalamanMenu == -1 ? Event Player.KursorUtama : Event Player.HalamanMenu)"
parts=[]
for page in range(12):
    target=("Global.DaftarWarnaRGB[Event Player.KursorWarna]" if page==2 else f"Vector({PALETTE[page][0]}, {PALETTE[page][1]}, {PALETTE[page][2]})")
    parts.append(("" if page==0 else ": ") + f"{idx} == {page} ? {target}")
expr="\n\t\t\t".join(parts)+"\n\t\t\t: Vector(55, 235, 245)"
actions=f'''\t\t"Setiap menu memiliki warna identitas sendiri. Hanya Name Color mengikuti warna yang sedang dipilih; semuanya berpindah dengan chase lembut."
\t\tChase Player Variable Over Time(Event Player, WarnaMenu,
\t\t\t{expr}, 0.180, Destination and Duration);'''
rule=replace_actions(rule,actions)
source=source[:start]+rule+source[end:]
SOURCE.write_text(source,encoding="utf-8")

validator=VALIDATOR.read_text(encoding="utf-8")
validator=once(validator,"della versione 0.6.12.","della versione 0.6.13.","validator doc")
validator=once(validator,'CURRENT_VERSION = "0.6.12"','CURRENT_VERSION = "0.6.13"',"validator version")
for old,new in OLD_TO_NEW.items():
    validator=validator.replace(old,new)
anchor='''    transition_rules = rules_containing(rules, "Subroutine;", "TransisiWarnaMenu;")
    checks.equal(len(transition_rules), 1, "subroutine TransisiWarnaMenu")
    if transition_rules:
        checks.require(
            re.search(r"0\\.180\\s*,\\s*Destination and Duration", mask_strings(transition_rules[0].body)) is not None,
            "transizione colore menu non impostata a 0,18 s",
        )
'''
extra=anchor+'''        transition_code = mask_strings(transition_rules[0].body)
        checks.require(
            "Global.DaftarWarnaRGB[Event Player.KursorWarna]" in transition_code,
            "Name Color non segue più dinamicamente il colore selezionato",
        )
        fixed_menu_colors = {
            0: (55, 235, 245), 1: (70, 135, 255), 3: (185, 105, 255),
            4: (255, 75, 85), 5: (255, 145, 55), 6: (255, 80, 205),
            7: (170, 240, 85), 8: (65, 225, 130), 9: (55, 190, 170),
            10: (255, 210, 70), 11: (255, 120, 155),
        }
        checks.equal(len(set(fixed_menu_colors.values())), len(fixed_menu_colors), "palette fissa menu con colori duplicati")
        page_expr = "(Event Player.HalamanMenu == -1 ? Event Player.KursorUtama : Event Player.HalamanMenu)"
        for page, rgb in fixed_menu_colors.items():
            checks.require(
                f"{page_expr} == {page} ? Vector({rgb[0]}, {rgb[1]}, {rgb[2]})" in transition_code,
                f"colore dedicato menu {page} mancante o modificato",
            )
'''
validator=once(validator,anchor,extra,"new palette validator")
VALIDATOR.write_text(validator,encoding="utf-8")
VERSION.write_text("0.6.13\n",encoding="utf-8")

readme=README.read_text(encoding="utf-8")
readme=once(readme,"La versione **0.6.12** identifica lo stato funzionale e tecnico corrente del repository.","La versione **0.6.13** identifica lo stato funzionale e tecnico corrente del repository.","README version")
readme=once(readme,"- Colori menu diversi e coordinati con i rispettivi sottomenu.\n- Transizione colore morbida di circa **0,18 s** tramite Vector RGB.\n","- Ogni menu, tranne Name Color, ha una **tonalità identitaria unica**; Name Color segue invece il colore selezionato.\n- Tutti i passaggi colore restano sfumati con transizione morbida di circa **0,18 s** tramite Vector RGB.\n","README palette")
readme+='''\n\n### Palette menu unica 0.6.13\n\nOgni voce Arcade ha una tonalità dedicata: Soundtrack ciano, Camera blu, Language viola, Revenge rosso, Unkillable arancio, Hero Voice magenta, Player Icon lime, Crouch Teleport verde, Crouch Privacy teal, Try Your Luck oro e Vote Player rosa. **Name Color resta dinamico** e segue `DaftarWarnaRGB[KursorWarna]`. Tutti i passaggi continuano a usare il chase morbido da 0,18 s.\n'''
README.write_text(readme,encoding="utf-8")

progetto=PROGETTO.read_text(encoding="utf-8")
progetto=once(progetto,"# Note di progetto — versione 0.6.12","# Note di progetto — versione 0.6.13","PROGETTO title")
progetto=once(progetto,"Workshop 0.6.12.","Workshop 0.6.13.","PROGETTO version")
progetto+='''\n\n## Palette menu 0.6.13\n\n`TransisiWarnaMenu` usa RGB fissi unici per 0,1,3..11; il menu 2 Name Color continua a seguire `Global.DaftarWarnaRGB[Event Player.KursorWarna]`. Main e submenu condividono la stessa identità cromatica e la durata del chase resta 0,18 s.\n'''
PROGETTO.write_text(progetto,encoding="utf-8")

test=TEST_DOC.read_text(encoding="utf-8")
test=once(test,"# Piano di test — versione 0.6.12","# Piano di test — versione 0.6.13","TEST title")
test=once(test,"Workshop 0.6.12.","Workshop 0.6.13.","TEST version")
test+='''\n\n## Palette menu 0.6.13\n\nScorrere tutte le 12 voci: 0,1,3..11 devono avere tonalità chiaramente diverse con transizione sfumata. Aprire ogni submenu e verificare che mantenga il colore della voce. Name Color deve invece seguire il colore evidenziato.\n'''
TEST_DOC.write_text(test,encoding="utf-8")

val=VALIDAZIONE.read_text(encoding="utf-8")
val=once(val,"# Rapporto di validazione — versione 0.6.12","# Rapporto di validazione — versione 0.6.13","VALIDAZIONE title")
val=once(val,"Release tecnica: **CHILL Dedicated Server 0.6.12**","Release tecnica: **CHILL Dedicated Server 0.6.13**","VALIDAZIONE release")
val=once(val,"OK - controlli statici v0.6.12 superati","OK - controlli statici v0.6.13 superati","VALIDAZIONE result")
val+='''\n\n## Palette menu 0.6.13\n\nIl gate richiede 11 RGB fissi tutti diversi, mantiene Name Color dinamico e conserva `0.180, Destination and Duration`.\n'''
data=SOURCE.read_bytes().replace(b"\r\n",b"\n"); payload=b"blob "+str(len(data)).encode()+b"\0"+data; blob=hashlib.sha1(payload).hexdigest()
val,n=re.subn(r"(Blob Git del sorgente Workshop validato:\n\n```text\n)[0-9a-f]{40}(\n```)",rf"\g<1>{blob}\g<2>",val,count=1)
if n!=1: raise RuntimeError("blob marker missing")
VALIDAZIONE.write_text(val,encoding="utf-8")
print("Applied CHILL 0.6.13 unique smooth menu palette with migrated legacy checks")
