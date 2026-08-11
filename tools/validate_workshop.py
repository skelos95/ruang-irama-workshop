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


def array_item_count(body: str) -> int:
    """Conta gli elementi separati da virgole al livello principale."""
    depth = 0
    in_string = False
    escaped = False
    count = 1 if body.strip() else 0
    for char in body:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "," and depth == 0:
            count += 1
    return count


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
    pages_en = strings_in(array_body(source, "Global.NamaHalamanEN"))
    colors = array_item_count(array_body(source, "Global.DaftarWarna"))
    color_names = strings_in(array_body(source, "Global.NamaWarna"))
    color_names_en = strings_in(array_body(source, "Global.NamaWarnaEN"))
    languages = strings_in(array_body(source, "Global.NamaBahasa"))
    if len(genres) != 100:
        fail(f"attesi 100 generi, trovati {len(genres)}")
    if len(set(genres)) != 100:
        duplicates = sorted({item for item in genres if genres.count(item) > 1})
        fail(f"generi duplicati: {duplicates}")
    if len(pages) != 10:
        fail(f"attese 10 pagine, trovate {len(pages)}")
    if len(pages_en) != 10:
        fail(f"attese 10 pagine inglesi, trovate {len(pages_en)}")
    if colors != 20:
        fail(f"attese 20 sfumature, trovate {colors}")
    if len(color_names) != colors or len(set(color_names)) != colors:
        fail(f"attesi {colors} nomi colore indonesiani unici, trovati {len(color_names)}")
    if len(color_names_en) != colors or len(set(color_names_en)) != colors:
        fail(f"attesi {colors} nomi colore inglesi unici, trovati {len(color_names_en)}")
    if languages != ["English", "Bahasa Indonesia"]:
        fail(f"lingue inattese: {languages}")
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
    blocked_comment_fragments = ("cum", "sag")
    for name in rule_names:
        lowered = name.casefold()
        hit = next((fragment for fragment in blocked_comment_fragments if fragment in lowered), None)
        if hit is not None:
            fail(
                "nome regola a rischio filtro parole del client "
                f"({hit!r}): {name}"
            )
    menu_router = re.search(
        r'rule\("91 - Subrutin:.*?\)(.*?)rule\("91a - Subrutin:',
        source,
        flags=re.DOTALL,
    )
    if menu_router is None or "Create HUD Text" in menu_router.group(1):
        fail("GambarMenu deve restare un router leggero senza Create HUD Text")
    for renderer in (
        "GambarUtama",
        "GambarMusik",
        "GambarKamera",
        "GambarWarna",
        "GambarBahasa",
    ):
        if f"Call Subroutine({renderer})" not in menu_router.group(1):
            fail(f"renderer menu non instradato: {renderer}")

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
        "menu numerati 0 1 2 3": "Global.KodeMenu = Array(0, 1, 2, 3)",
        "lingua individuale per client": "Player Variable(Local Player, IndeksBahasa)",
        "inglese predefinito": "Event Player.IndeksBahasa = 0",
        "inizializzazione completa": "Call Subroutine(SiapkanPemain)",
        "lista camera aggiornata": "Call Subroutine(SegarkanTargetKamera)",
        "camera include umani e bot": "Filtered Array(All Players(All Teams)",
        "controllo target camera esistente": "Entity Exists(Event Player.TargetKamera)",
        "navigazione precedente": "06 - Menu: Tembakan utama memilih sebelumnya",
        "navigazione successiva": "07 - Menu: Tembakan sekunder memilih berikutnya",
        "colore personale": "Event Player.WarnaNama",
        "bot senza fuoco primario": "Set Primary Fire Enabled(Event Player, False)",
        "bot senza fuoco secondario": "Set Secondary Fire Enabled(Event Player, False)",
        "bot senza abilita 1": "Set Ability 1 Enabled(Event Player, False)",
        "bot senza abilita 2": "Set Ability 2 Enabled(Event Player, False)",
        "bot senza ultimate": "Set Ultimate Ability Enabled(Event Player, False)",
        "bot senza melee": "Set Melee Enabled(Event Player, False)",
        "bot senza danno residuo": "Set Damage Dealt(Event Player, 0)",
        "bot senza cura residua": "Set Healing Dealt(Event Player, 0)",
        "bot senza knockback residuo": "Set Knockback Dealt(Event Player, 0)",
        "ispezione include umani e bot": "All Players(All Teams)",
        "reload chiude il menu": "11 - Menu: Isi ulang menutup menu dari halaman mana pun",
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

    if source.count("\u200b") != 2:
        fail("la sentinella AI U+200B deve comparire esattamente due volte")
    if source.count('Custom String("\u200b")') != 2:
        fail("la sentinella AI U+200B non e racchiusa nelle due Custom String previste")
    if re.search(r"Create HUD Text\([^;]*,\s*Bottom\s*,", source, flags=re.DOTALL):
        fail("Create HUD Text usa Bottom, ma le posizioni valide sono Left, Top e Right")
    if source.count("Create HUD Text(") > 9:
        fail("troppe definizioni HUD statiche: possibile regressione verso 100 righe menu")
    titleless_hud = re.findall(r"Create HUD Text\([^,]+,\s*Null,", source)
    if len(titleless_hud) != source.count("Create HUD Text("):
        fail("ogni HUD deve avere Header Null: funzione in Text e input in Subheader")
    if source.count("Call Subroutine(TutupMenu)") != 3:
        fail("il menu deve chiudersi con Melee lungo, Reload o per cleanup alla morte")
    if source.count("Call Subroutine(SiapkanPemain)") != 2:
        fail("SiapkanPemain deve coprire sia join sia giocatori gia presenti")
    if source.count(
        "If(Index Of Array Value(Global.PemainManusia, Event Player) >= 0);"
    ) != 5:
        fail("mancano guardie su una scrittura HUD/testo indicizzata")
    leave_rule = re.search(
        r'rule\("04 - Pemain Keluar:.*?\)(.*?)rule\("05 - Menu:',
        source,
        flags=re.DOTALL,
    )
    if leave_rule is None or "Event Player." in leave_rule.group(1):
        fail("Player Left Match non deve leggere variabili del giocatore uscente")
    parallel_arrays = (
        "PemainManusia",
        "HudKiriPemain",
        "HudKananPemain",
        "HudMenuPemain",
        "TeksDuniaPemain",
    )
    for name in parallel_arrays:
        if source.count(f"Modify Global Variable({name}, Remove From Array By Index") != 1:
            fail(f"cleanup non allineato per Global.{name}")
    for stale in (
        "Menu 0 / 1 / 3",
        "Nomor 2 sedang cuti",
        "3 - Warna nama",
        "Global.PemainManusia, Event Player.TargetKamera",
    ):
        if stale in source:
            fail(f"testo o logica obsoleta ancora presente: {stale}")
    interact_rule = re.search(
        r'rule\("10 - Menu: Interaksi membuka atau menerapkan pilihan"\)(.*?)'
        r'rule\("11 - Menu:',
        source,
        flags=re.DOTALL,
    )
    if interact_rule is None:
        fail("dispatcher Interact non trovato")
    submenu_actions = interact_rule.group(1).split("Else If(Event Player.HalamanMenu == 0);", 1)[-1]
    if "Event Player.HalamanMenu = -1;" in submenu_actions:
        fail("Interact non deve uscire dal sottomenu dopo aver applicato una scelta")

    custom_literals = re.findall(r'Custom String\("((?:[^"\\]|\\.)*)"', source)
    too_long = [value for value in custom_literals if len(value) > 128]
    if too_long:
        fail(f"Custom String oltre 128 caratteri: {too_long[:3]}")
    bad_placeholders = [
        value
        for value in custom_literals
        if any(int(index) > 2 for index in re.findall(r"\{(\d+)\}", value))
    ]
    if bad_placeholders:
        fail(f"Custom String usa placeholder oltre {{2}}: {bad_placeholders[:3]}")

    print("OK - controlli statici superati")
    print(f"Generi: {len(genres)} unici | Pagine: {len(pages)} | Regole: {len(rule_names)}")
    print(
        f"Colori: {colors} | Lingue: {len(languages)} | "
        f"HUD definiti nel sorgente: {source.count('Create HUD Text(')}"
    )
    print("Nota: resta obbligatorio il test di importazione nel client Overwatch.")


if __name__ == "__main__":
    main()
