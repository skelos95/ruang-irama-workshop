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

# Native Create Icon is used for Heart/Skull because the Workshop font does not
# render the Unicode skull reliably. The brackets remain a separate, small IWT.
source = replace_once(
    source,
    "\t\t75: JedaKartuNasib\n",
    "\t\t75: JedaKartuNasib\n\t\t76: IkonKartuNasib\n",
    "luck icon variable",
)

source = replace_once(
    source,
    "\t\tEvent Player.MenitLobi = 0;\n\t\tEvent Player.UrutanHUD = First Of(Global.SlotHUDTersedia);",
    "\t\tEvent Player.MenitLobi = 0;\n\t\tEvent Player.IkonKartuNasib = Null;\n\t\tEvent Player.UrutanHUD = First Of(Global.SlotHUDTersedia);",
    "luck icon initialization",
)

old_card = '''\t\t\t\tCreate In-World Text(All Players(All Teams), Event Player.KartuNasibMerah ? Custom String("[ ☠ ]") : Custom String("[ ♥ ]"), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), 2.500, Do Not Clip, Visible To Position String and Color, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Visible Never);\n\t\t\t\tEvent Player.TeksKartuNasib = Last Text ID;'''
new_card = '''\t\t\t\tCreate In-World Text(All Players(All Teams), Custom String("[     ]"), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), 2.200, Do Not Clip, Visible To Position String and Color, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Visible Never);\n\t\t\t\tEvent Player.TeksKartuNasib = Last Text ID;\n\t\t\t\tIf(Event Player.KartuNasibMerah == True);\n\t\t\t\t\tCreate Icon(All Players(All Teams), Eye Position(Event Player) + Facing Direction Of(Event Player) * 4, Skull, Visible To and Position, Custom Color(255, 70, 70, 255), False);\n\t\t\t\tElse;\n\t\t\t\t\tCreate Icon(All Players(All Teams), Eye Position(Event Player) + Facing Direction Of(Event Player) * 4, Heart, Visible To and Position, Custom Color(70, 255, 110, 255), False);\n\t\t\t\tEnd;\n\t\t\t\tEvent Player.IkonKartuNasib = Last Created Entity;'''
source = replace_once(source, old_card, new_card, "native luck icon creation")

# Recreate the native icon whenever the roulette changes color/icon. This makes
# both the glyph and its color deterministic instead of depending on reevaluation.
source = replace_once(
    source,
    "\t\tEvent Player.KartuNasibMerah = Event Player.KartuNasibMerah == False;\n\t\tModify Player Variable(Event Player, PutaranKartuNasib, Subtract, 1);\n\t\tModify Player Variable(Event Player, JedaKartuNasib, Add, 0.055);",
    "\t\tEvent Player.KartuNasibMerah = Event Player.KartuNasibMerah == False;\n\t\tIf(Event Player.IkonKartuNasib != Null);\n\t\t\tDestroy Icon(Event Player.IkonKartuNasib);\n\t\tEnd;\n\t\tIf(Event Player.KartuNasibMerah == True);\n\t\t\tCreate Icon(All Players(All Teams), Eye Position(Event Player) + Facing Direction Of(Event Player) * 4, Skull, Visible To and Position, Custom Color(255, 70, 70, 255), False);\n\t\tElse;\n\t\t\tCreate Icon(All Players(All Teams), Eye Position(Event Player) + Facing Direction Of(Event Player) * 4, Heart, Visible To and Position, Custom Color(70, 255, 110, 255), False);\n\t\tEnd;\n\t\tEvent Player.IkonKartuNasib = Last Created Entity;\n\t\tModify Player Variable(Event Player, PutaranKartuNasib, Subtract, 1);\n\t\tModify Player Variable(Event Player, JedaKartuNasib, Add, 0.055);",
    "roulette native icon refresh",
)

# Normal resolution cleanup.
source = replace_once(
    source,
    "\t\tIf(Event Player.TeksKartuNasib != Null);\n\t\t\tDestroy In-World Text(Event Player.TeksKartuNasib);\n\t\tEnd;\n\t\tEvent Player.TeksKartuNasib = Null;\n\t\tEvent Player.KartuNasibAktif = False;",
    "\t\tIf(Event Player.TeksKartuNasib != Null);\n\t\t\tDestroy In-World Text(Event Player.TeksKartuNasib);\n\t\tEnd;\n\t\tIf(Event Player.IkonKartuNasib != Null);\n\t\t\tDestroy Icon(Event Player.IkonKartuNasib);\n\t\tEnd;\n\t\tEvent Player.TeksKartuNasib = Null;\n\t\tEvent Player.IkonKartuNasib = Null;\n\t\tEvent Player.KartuNasibAktif = False;",
    "normal luck cleanup",
)

# Death cleanup, scoped by the rule name to avoid replacing the normal cleanup twice.
death_start = source.index('rule("18f - Nasib: Hapus kartu saat pemilik mati")')
death_end = source.index('rule("19 - Teleportasi Jongkok:', death_start)
death = source[death_start:death_end]
death = replace_once(
    death,
    "\t\tIf(Event Player.TeksKartuNasib != Null);\n\t\t\tDestroy In-World Text(Event Player.TeksKartuNasib);\n\t\tEnd;\n\t\tEvent Player.TeksKartuNasib = Null;",
    "\t\tIf(Event Player.TeksKartuNasib != Null);\n\t\t\tDestroy In-World Text(Event Player.TeksKartuNasib);\n\t\tEnd;\n\t\tIf(Event Player.IkonKartuNasib != Null);\n\t\t\tDestroy Icon(Event Player.IkonKartuNasib);\n\t\tEnd;\n\t\tEvent Player.TeksKartuNasib = Null;\n\t\tEvent Player.IkonKartuNasib = Null;",
    "death luck icon cleanup",
)
source = source[:death_start] + death + source[death_end:]

# Player-left cleanup.
source = replace_once(
    source,
    "\t\t\t\tIf(Event Player.TeksKartuNasib != Null);\n\t\t\t\t\tDestroy In-World Text(Event Player.TeksKartuNasib);\n\t\t\t\tEnd;\n\t\t\t\tEvent Player.TeksKartuNasib = Null;\n\t\t\t\tEvent Player.KartuNasibAktif = False;",
    "\t\t\t\tIf(Event Player.TeksKartuNasib != Null);\n\t\t\t\t\tDestroy In-World Text(Event Player.TeksKartuNasib);\n\t\t\t\tEnd;\n\t\t\t\tIf(Event Player.IkonKartuNasib != Null);\n\t\t\t\t\tDestroy Icon(Event Player.IkonKartuNasib);\n\t\t\t\tEnd;\n\t\t\t\tEvent Player.TeksKartuNasib = Null;\n\t\t\t\tEvent Player.IkonKartuNasib = Null;\n\t\t\t\tEvent Player.KartuNasibAktif = False;",
    "leave luck icon cleanup",
)

SOURCE.write_text(source, encoding="utf-8")

validator = VALIDATOR.read_text(encoding="utf-8")

# New dedicated variable.
validator = replace_once(
    validator,
    '        (54, "KursorSuara"),\n    ):',
    '        (54, "KursorSuara"),\n        (76, "IkonKartuNasib"),\n    ):',
    "validator luck icon slot",
)

# Card IWT is brackets only, while native Create Icon owns the visible glyph/color.
old_card_check = '''        checks.require(\n            "Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), 2.500, Do Not Clip" in card_texts[0],\n            "Nasib: la carta pubblica deve restare agganciata al mirino a 4 m e usare dimensione 2,5",\n        )\n        checks.require(\n            "Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255)" in card_texts[0],\n            "Nasib: il testo mondo non cambia dinamicamente rosso/verde",\n        )\n        checks.require(\n            "Custom String(\\\"[ ☠ ]\\\")" in card_texts[0]\n            and "Custom String(\\\"[ ♥ ]\\\")" in card_texts[0]\n            and "Icon String(" not in card_texts[0]\n            and "TRY YOUR LUCK" not in card_texts[0]\n            and "COBA NASIB" not in card_texts[0],\n            "Nasib: la carta deve usare simboli testuali centrati [ ☠ ] / [ ♥ ] colorabili, senza Icon String",\n        )'''
new_card_check = '''        checks.require(\n            "Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), 2.200, Do Not Clip" in card_texts[0],\n            "Nasib: le parentesi della carta devono restare agganciate al mirino a 4 m e usare dimensione 2,2",\n        )\n        checks.require(\n            "Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255)" in card_texts[0],\n            "Nasib: le parentesi non cambiano dinamicamente rosso/verde",\n        )\n        checks.require(\n            "Custom String(\\\"[     ]\\\")" in card_texts[0]\n            and "Icon String(" not in card_texts[0]\n            and "☠" not in card_texts[0]\n            and "♥" not in card_texts[0]\n            and "TRY YOUR LUCK" not in card_texts[0]\n            and "COBA NASIB" not in card_texts[0],\n            "Nasib: le parentesi devono essere testo semplice; il simbolo è un Create Icon nativo",\n        )'''
validator = replace_once(validator, old_card_check, new_card_check, "validator native icon card")

marker = '''    checks.require(\n        "Event Player.PosisiKartuNasib = Eye Position(Event Player) + Facing Direction Of(Event Player) * 4;" in mask_strings(source),\n        "Nasib: cache effetto non segue il mirino del proprietario",\n    )'''
native_checks = '''    luck_icons = [call for call in call_texts(source, "Create Icon") if "KartuNasib" not in call and (", Skull," in call or ", Heart," in call)]\n    checks.equal(len(luck_icons), 4, "Nasib: due Create Icon iniziali più due per i cambi roulette")\n    if luck_icons:\n        checks.equal(len([call for call in luck_icons if ", Skull," in call]), 2, "Nasib: due rami Skull nativi")\n        checks.equal(len([call for call in luck_icons if ", Heart," in call]), 2, "Nasib: due rami Heart nativi")\n        for call in luck_icons:\n            checks.require(\n                "All Players(All Teams)" in call\n                and "Eye Position(Event Player) + Facing Direction Of(Event Player) * 4" in call\n                and "Visible To and Position" in call,\n                "Nasib: icona nativa non è pubblica o non segue il mirino",\n            )\n        for call in [call for call in luck_icons if ", Skull," in call]:\n            checks.require("Custom Color(255, 70, 70, 255)" in call, "Nasib: Skull non rosso")\n        for call in [call for call in luck_icons if ", Heart," in call]:\n            checks.require("Custom Color(70, 255, 110, 255)" in call, "Nasib: Heart non verde")\n    checks.require(\n        "Destroy Icon(Event Player.IkonKartuNasib);" in clean,\n        "Nasib: cleanup icona nativa assente",\n    )\n\n''' + marker
validator = replace_once(validator, marker, native_checks, "validator native icon behavior")

# Death reset must destroy and null both text and native icon.
validator = replace_once(
    validator,
    '                "Destroy In-World Text(Event Player.TeksKartuNasib);",\n            ),',
    '                "Destroy In-World Text(Event Player.TeksKartuNasib);",\n                "Destroy Icon(Event Player.IkonKartuNasib);",\n                "Event Player.IkonKartuNasib = Null;",\n            ),',
    "validator death native icon cleanup",
)
VALIDATOR.write_text(validator, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
project = replace_once(
    project,
    "La carta è resa come un unico testo colorabile: `[ ♥ ]` in verde oppure `[ ☠ ]` in rosso, a dimensione 2,5. Non usa più `Icon String`, perché nel client quell'icona restava bianca e visivamente più grande delle parentesi.",
    "La carta usa parentesi separate (`[     ]`, dimensione 2,2) e un vero `Create Icon` nativo centrato nello stesso punto: `Heart` verde oppure `Skull` rosso. Il simbolo Unicode `☠` è stato rimosso perché il font Workshop lo sostituiva con un carattere generico; l'icona nativa viene distrutta e ricreata a ogni cambio della roulette per garantire sia il simbolo sia il colore corretti.",
    "project native luck icon",
)
PROJECT.write_text(project, encoding="utf-8")

validation = VALIDATION.read_text(encoding="utf-8")
validation = replace_once(
    validation,
    "- Menu 10 Try Your Luck: carta `[ ♥ ]` verde / `[ ☠ ]` rossa agganciata al mirino, dimensione 2,5 e senza Ring Explosion; all'avvio forza Unkillable OFF, chiude e blocca l'Arcade Menu fino alla fine; 20..24 cambi progressivamente più lenti, reset completo alla morte, verde cura completa, rosso uccide dopo countdown 3 s, esito 50/50;",
    "- Menu 10 Try Your Luck: parentesi colorate + icona nativa `Heart` verde / `Skull` rossa agganciata al mirino, senza Ring Explosion; all'avvio forza Unkillable OFF, chiude e blocca l'Arcade Menu fino alla fine; 20..24 cambi progressivamente più lenti, reset completo alla morte, verde cura completa, rosso uccide dopo countdown 3 s, esito 50/50;",
    "validation native luck icon note",
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
