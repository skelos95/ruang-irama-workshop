#!/usr/bin/env python3
"""Controlli statici minimi per il sorgente Workshop di Ruang Irama.

Non sostituisce l'importazione nel client di Overwatch. Serve a intercettare
regressioni facili da introdurre modificando a mano array, HUD e camera.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
GENRE_DOC = ROOT / "docs" / "GENERI.md"


def fail(message: str) -> None:
    print(f"ERRORE: {message}", file=sys.stderr)
    raise SystemExit(1)


def array_body(source: str, assignment: str) -> str:
    marker = f"{assignment} = Array("
    start = source.find(marker)
    if start < 0:
        fail(f"assegnazione non trovata: {assignment}")
    pos = start + len(marker)
    depth = 1
    in_string = False
    escaped = False
    for index in range(pos, len(source)):
        char = source[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return source[pos:index]
    fail(f"array non chiuso: {assignment}")
    return ""  # pragma: no cover


def strings_in(body: str) -> list[str]:
    return re.findall(r'Custom String\("((?:[^"\\]|\\.)*)"\)', body)


def assert_balanced(source: str) -> None:
    clean = []
    in_string = False
    escaped = False
    for char in source:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            clean.append(" ")
        elif char == '"':
            in_string = True
            clean.append(" ")
        else:
            clean.append(char)
    if in_string:
        fail("stringa non chiusa")
    text = "".join(clean)
    for opening, closing, label in (("{", "}", "graffe"), ("(", ")", "parentesi")):
        level = 0
        for char in text:
            if char == opening:
                level += 1
            elif char == closing:
                level -= 1
                if level < 0:
                    fail(f"{label} chiuse troppo presto")
        if level:
            fail(f"{label} non bilanciate: saldo {level}")


def main() -> None:
    if not SOURCE.exists():
        fail(f"file mancante: {SOURCE}")
    source = SOURCE.read_text(encoding="utf-8")
    assert_balanced(source)
    if not source.lstrip().startswith("variables"):
        fail("il file copy-safe deve iniziare con variables ed essere incollato nella schermata Workshop")
    if re.search(r"^settings\s*$", source, flags=re.MULTILINE):
        fail("trovato un blocco settings: questo progetto deve restare un overlay Workshop")
    for line_number, line in enumerate(source.splitlines(), start=1):
        if ("||" in line or "&&" in line) and re.match(r"^\s*[^\"].*;\s*$", line):
            if not re.search(r"\)\s*(==|!=)\s*(True|False)\s*;\s*$", line):
                fail(f"espressione booleana non confrontata nella condizione alla riga {line_number}")

    genres = strings_in(array_body(source, "Global.DaftarGenre"))
    pages = strings_in(array_body(source, "Global.NamaHalaman"))
    color_names = strings_in(array_body(source, "Global.NamaWarna"))
    if len(genres) != 100:
        fail(f"attesi 100 generi, trovati {len(genres)}")
    if len(set(genres)) != 100:
        duplicates = sorted({item for item in genres if genres.count(item) > 1})
        fail(f"generi duplicati: {duplicates}")
    if len(pages) != 10:
        fail(f"attese 10 pagine, trovate {len(pages)}")
    if len(color_names) != 10 or len(set(color_names)) != 10:
        fail(f"attesi 10 colori con nomi unici, trovati {len(color_names)}")
    if not GENRE_DOC.exists():
        fail(f"documentazione generi mancante: {GENRE_DOC}")
    documented_genres = re.findall(
        r"^\d+\. (.+)$", GENRE_DOC.read_text(encoding="utf-8"), flags=re.MULTILINE
    )
    if documented_genres != genres:
        fail("l'elenco in docs/GENERI.md non coincide con l'array Workshop")

    rule_names = re.findall(r'^rule\("([^"]+)"\)', source, flags=re.MULTILINE)
    if len(rule_names) < 20:
        fail(f"troppo poche regole: {len(rule_names)}")
    if any(name.startswith("Rule ") for name in rule_names):
        fail("trovato un nome regola generico non indonesiano")

    required = {
        "pressione Melee da 1,5 s": "Wait(1.500, Abort When False)",
        "filtro dummy bot": "Is Dummy Bot(Event Player)",
        "workaround bot AI": "Start Forcing Dummy Bot Name",
        "raycast giocatore": "Ray Cast Hit Player",
        "icona eroe": "Hero Icon String",
        "freccia sul giocatore": "Icon String(Arrow: Down)",
        "testo ancorato nel mondo": "Create In-World Text",
        "cleanup testo nel mondo": "Destroy In-World Text",
        "colore marker rivalutato": "Visible To Position String and Color",
        "gestione Echo": "Hero Being Duplicated",
        "camera": "Start Camera",
        "camera per-frame con collisione": "Update Every Frame(Ray Cast Hit Position",
        "registro HUD globale": "Global.HudKiriPemain",
        "cleanup per indice": "Remove From Array By Index",
        "menu numerati 0 1 3": "Global.KodeMenu = Array(0, 1, 3)",
        "colore personale": "Event Player.WarnaNama",
        "bot senza fuoco primario": "Set Primary Fire Enabled(Event Player, False)",
        "bot senza fuoco secondario": "Set Secondary Fire Enabled(Event Player, False)",
        "bot senza abilita 1": "Set Ability 1 Enabled(Event Player, False)",
        "bot senza abilita 2": "Set Ability 2 Enabled(Event Player, False)",
        "bot senza ultimate": "Set Ultimate Ability Enabled(Event Player, False)",
        "bot senza melee": "Set Melee Enabled(Event Player, False)",
    }
    for label, token in required.items():
        if token not in source:
            fail(f"requisito assente ({label}): {token}")
    if not re.search(
        r'rule\("03b - Bot: Senjata libur, kaki tetap boleh jalan"\).*?'
        r'Is Alive\(Event Player\) == True;',
        source,
        flags=re.DOTALL,
    ):
        fail("il blocco combattimento dei bot deve riattivarsi a ogni respawn")

    ai_sentinel = 'Custom String("")'
    if source.count(ai_sentinel) < 2:
        fail("la sentinella vuota del rilevamento AI è assente o danneggiata")
    if "\u200b" in source:
        fail("trovato U+200B: il sorgente da incollare deve restare copy-safe")
    if re.search(r"Create HUD Text\([^;]*,\s*Bottom\s*,", source, flags=re.DOTALL):
        fail("Create HUD Text usa Bottom, ma le posizioni valide sono Left, Top e Right")
    if source.count("Create HUD Text(") > 8:
        fail("troppe definizioni HUD statiche: possibile regressione verso 100 righe menu")
    titleless_hud = re.findall(r"Create HUD Text\([^,]+,\s*Null,", source)
    if len(titleless_hud) != source.count("Create HUD Text("):
        fail("ogni HUD deve avere Header Null: funzione in Text e input in Subheader")
    if source.count("Call Subroutine(TutupMenu)") != 2:
        fail("il menu deve chiudersi solo con Melee lungo o alla morte del giocatore")

    custom_literals = re.findall(r'Custom String\("((?:[^"\\]|\\.)*)"', source)
    too_long = [value for value in custom_literals if len(value) > 128]
    if too_long:
        fail(f"Custom String oltre 128 caratteri: {too_long[:3]}")

    print("OK - controlli statici superati")
    print(f"Generi: {len(genres)} unici | Pagine: {len(pages)} | Regole: {len(rule_names)}")
    print(f"HUD definiti nel sorgente: {source.count('Create HUD Text(')}")
    print("Nota: resta obbligatorio il test di importazione nel client Overwatch.")


if __name__ == "__main__":
    main()
