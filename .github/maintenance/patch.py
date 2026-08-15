from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
PROJECT = ROOT / "docs" / "PROGETTO.md"
VALIDATION = ROOT / "docs" / "VALIDAZIONE.md"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one occurrence, found {count}")
    return text.replace(old, new, 1)


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    return hashlib.sha1(payload).hexdigest()


source = SOURCE.read_text(encoding="utf-8")

# The Arcade Menu cannot be opened while the luck roulette is active.
source = replace_once(
    source,
    "\t\tEvent Player.TeleportasiJongkokAktif == False;\n\t\tIs Button Held(Event Player, Button(Melee)) == True;",
    "\t\tEvent Player.TeleportasiJongkokAktif == False;\n\t\tEvent Player.KartuNasibAktif == False;\n\t\tIs Button Held(Event Player, Button(Melee)) == True;",
    "block menu during luck roulette",
)

old_luck = '''\t\tElse;\n\t\t\tIf(Event Player.KartuNasibAktif == True);\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("The luck card is already rolling. Wait for the result.") : Event Player.IndeksBahasa == 1 ? Custom String("Kartu nasib sedang berputar. Tunggu hasilnya.") : Custom String("การ์ดเสี่ยงโชคกำลังสุ่มอยู่ รอผลก่อน"));\n\t\t\tElse;\n\t\t\t\tEvent Player.KartuNasibAktif = True;\n\t\t\t\tEvent Player.KartuNasibMerah = Random Integer(0, 1) == 0;\n\t\t\t\tEvent Player.PutaranKartuNasib = Random Integer(20, 24);\n\t\t\t\tEvent Player.JedaKartuNasib = 0.080;\n\t\t\t\tEvent Player.PosisiKartuNasib = Eye Position(Event Player) + Facing Direction Of(Event Player) * 4;\n\t\t\t\tCreate In-World Text(All Players(All Teams), Event Player.KartuNasibMerah ? Custom String("[ ☠ ]") : Custom String("[ ♥ ]"), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), 2.500, Do Not Clip, Visible To Position String and Color, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Visible Never);\n\t\t\t\tEvent Player.TeksKartuNasib = Last Text ID;\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Luck roulette started. Red or green?") : Event Player.IndeksBahasa == 1 ? Custom String("Roulette nasib dimulai. Merah atau hijau?") : Custom String("เริ่มรูเล็ตเสี่ยงโชคแล้ว แดงหรือเขียว?"));\n\t\t\tEnd;\n\t\t\tCall Subroutine(GambarMenu);\n\t\tEnd;'''
new_luck = '''\t\tElse;\n\t\t\tIf(Event Player.KartuNasibAktif == True);\n\t\t\t\tCall Subroutine(TutupMenu);\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("The luck card is already rolling. Wait for the result.") : Event Player.IndeksBahasa == 1 ? Custom String("Kartu nasib sedang berputar. Tunggu hasilnya.") : Custom String("การ์ดเสี่ยงโชคกำลังสุ่มอยู่ รอผลก่อน"));\n\t\t\tElse;\n\t\t\t\tEvent Player.KebalAktif = False;\n\t\t\t\tEvent Player.ModeKebal = 0;\n\t\t\t\tEvent Player.KursorKebal = 0;\n\t\t\t\tClear Status(Event Player, Unkillable);\n\t\t\t\tSet Damage Received(Event Player, 100);\n\t\t\t\tIf(Event Player.IkonKebal != Null);\n\t\t\t\t\tDestroy Icon(Event Player.IkonKebal);\n\t\t\t\t\tEvent Player.IkonKebal = Null;\n\t\t\t\tEnd;\n\t\t\t\tEvent Player.KartuNasibAktif = True;\n\t\t\t\tEvent Player.KartuNasibMerah = Random Integer(0, 1) == 0;\n\t\t\t\tEvent Player.PutaranKartuNasib = Random Integer(20, 24);\n\t\t\t\tEvent Player.JedaKartuNasib = 0.080;\n\t\t\t\tEvent Player.PosisiKartuNasib = Eye Position(Event Player) + Facing Direction Of(Event Player) * 4;\n\t\t\t\tCreate In-World Text(All Players(All Teams), Event Player.KartuNasibMerah ? Custom String("[ ☠ ]") : Custom String("[ ♥ ]"), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), 2.500, Do Not Clip, Visible To Position String and Color, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Visible Never);\n\t\t\t\tEvent Player.TeksKartuNasib = Last Text ID;\n\t\t\t\tCall Subroutine(TutupMenu);\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Luck roulette started. Red or green?") : Event Player.IndeksBahasa == 1 ? Custom String("Roulette nasib dimulai. Merah atau hijau?") : Custom String("เริ่มรูเล็ตเสี่ยงโชคแล้ว แดงหรือเขียว?"));\n\t\t\tEnd;\n\t\tEnd;'''
source = replace_once(source, old_luck, new_luck, "luck activation closes and locks menu")
SOURCE.write_text(source, encoding="utf-8")

validator = VALIDATOR.read_text(encoding="utf-8")

# Opening rule must be structurally gated by the active luck card.
validator = replace_once(
    validator,
    '''    if menu_open_rules:\n        opening = mask_strings(menu_open_rules[0].body)\n        for forbidden in (''',
    '''    if menu_open_rules:\n        opening = mask_strings(menu_open_rules[0].body)\n        checks.require(\n            "Event Player.KartuNasibAktif == False;" in opening,\n            "Menu 10: Arcade Menu può ancora aprirsi durante la roulette",\n        )\n        for forbidden in (''',
    "validator menu lock",
)

# Luck activation must force Unkillable OFF, close the menu, and not redraw it.
needle = '''    menu_interact = next(rule.body for rule in rules if rule.name.startswith("10 - Menu:"))\n    blocked_one_hp = menu_interact['''
insert = '''    menu_interact = next(rule.body for rule in rules if rule.name.startswith("10 - Menu:"))\n    luck_start = menu_interact.find("Event Player.KartuNasibAktif = True;")\n    checks.require(luck_start >= 0, "Nasib: avvio carta non trovato nel dispatcher")\n    if luck_start >= 0:\n        before_luck = mask_strings(menu_interact[max(0, luck_start - 900):luck_start])\n        after_luck = mask_strings(menu_interact[luck_start:])\n        for token in (\n            "Event Player.KebalAktif = False;",\n            "Event Player.ModeKebal = 0;",\n            "Event Player.KursorKebal = 0;",\n            "Clear Status(Event Player, Unkillable);",\n            "Set Damage Received(Event Player, 100);",\n            "Destroy Icon(Event Player.IkonKebal);",\n        ):\n            checks.require(token in before_luck, f"Nasib: avvio carta non forza Unkillable OFF: {token}")\n        checks.require(\n            "Call Subroutine(TutupMenu);" in after_luck,\n            "Nasib: il menu non viene chiuso quando parte la carta",\n        )\n        checks.require(\n            "Call Subroutine(GambarMenu);" not in after_luck,\n            "Nasib: il menu viene ridisegnato dopo l'avvio della carta",\n        )\n\n    blocked_one_hp = menu_interact['''
validator = replace_once(validator, needle, insert, "validator luck menu lock and unkillable reset")
VALIDATOR.write_text(validator, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
project = replace_once(
    project,
    "Non serve sparare. Quando la roulette termina, il colore finale decide l'esito: verde ripristina immediatamente la salute massima; rosso mantiene il teschio rosso e mostra un countdown di 3 secondi, poi rimuove `Unkillable` e uccide il proprietario.",
    "Non serve sparare. All'avvio della roulette, il Menu 5 Unkillable viene forzato su OFF (`ModeKebal = 0`, `KursorKebal = 0`, status rimosso e danno ricevuto riportato a 100) senza curare automaticamente il player; l'Arcade Menu viene chiuso e non può essere riaperto finché `KartuNasibAktif` resta `True`. Quando la roulette termina, il colore finale decide l'esito: verde ripristina immediatamente la salute massima; rosso mantiene il teschio rosso e mostra un countdown di 3 secondi, poi uccide il proprietario.",
    "project luck lock behavior",
)
PROJECT.write_text(project, encoding="utf-8")

validation = VALIDATION.read_text(encoding="utf-8")
validation = replace_once(
    validation,
    "- Menu 10 Try Your Luck: carta `[ ♥ ]` verde / `[ ☠ ]` rossa agganciata al mirino, dimensione 2,5 e senza Ring Explosion, 20..24 cambi progressivamente più lenti, reset completo alla morte, verde cura completa, rosso uccide dopo countdown 3 s, esito 50/50;",
    "- Menu 10 Try Your Luck: carta `[ ♥ ]` verde / `[ ☠ ]` rossa agganciata al mirino, dimensione 2,5 e senza Ring Explosion; all'avvio forza Unkillable OFF, chiude e blocca l'Arcade Menu fino alla fine; 20..24 cambi progressivamente più lenti, reset completo alla morte, verde cura completa, rosso uccide dopo countdown 3 s, esito 50/50;",
    "validation luck lock note",
)
new_blob = git_blob_sha(SOURCE)
validation, count = re.subn(
    r"(?s)(Blob Git del sorgente Workshop validato:\s*```text\s*)[0-9a-f]{40}(\s*```)",
    rf"\g<1>{new_blob}\g<2>",
    validation,
    count=1,
)
if count != 1:
    raise RuntimeError("validation blob: expected one documented Workshop SHA")
VALIDATION.write_text(validation, encoding="utf-8")
