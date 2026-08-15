from __future__ import annotations

import hashlib
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

# Longer roulette: ~12-17 seconds instead of ~4-8 seconds, while preserving
# independent random starting color so the final result remains exactly 50/50.
source = replace_once(
    source,
    "Event Player.PutaranKartuNasib = Random Integer(12, 16);",
    "Event Player.PutaranKartuNasib = Random Integer(20, 24);",
    "longer roulette rounds",
)

# Anchor the public card to the owner's reticle. No label text remains: the card
# itself is represented by the Workshop Heart/Skull icon string and dynamic color.
old_creation = '''\t\t\t\tEvent Player.PosisiKartuNasib = Position Of(Event Player) + Direction From Angles(Horizontal Facing Angle Of(Event Player), 0) * 2.500 - Vector(0, 0.450, 0);\n\t\t\t\tCreate In-World Text(All Players(All Teams), Player Variable(Local Player, IndeksBahasa) == 0 ? Custom String("[ ? ]\\nTRY YOUR LUCK") : Player Variable(Local Player, IndeksBahasa) == 1 ? Custom String("[ ? ]\\nCOBA NASIB") : Custom String("[ ? ]\\nเสี่ยงโชค"), Event Player.PosisiKartuNasib, 3.500, Do Not Clip, Visible To Position String and Color, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Visible Never);\n\t\t\t\tEvent Player.TeksKartuNasib = Last Text ID;\n\t\t\t\tPlay Effect(All Players(All Teams), Ring Explosion, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Event Player.PosisiKartuNasib + Vector(0, 0.450, 0), 3);\n\t\t\t\tChase Player Variable Over Time(Event Player, PosisiKartuNasib, Event Player.PosisiKartuNasib + Vector(0, 1.000, 0), 0.600, Destination and Duration);'''
new_creation = '''\t\t\t\tEvent Player.PosisiKartuNasib = Eye Position(Event Player) + Facing Direction Of(Event Player) * 4;\n\t\t\t\tCreate In-World Text(All Players(All Teams), Event Player.KartuNasibMerah ? Icon String(Skull) : Icon String(Heart), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), 3.500, Do Not Clip, Visible To Position String and Color, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Visible Never);\n\t\t\t\tEvent Player.TeksKartuNasib = Last Text ID;\n\t\t\t\tPlay Effect(All Players(All Teams), Ring Explosion, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Event Player.PosisiKartuNasib, 3);'''
source = replace_once(source, old_creation, new_creation, "reticle card creation")

# Every roulette tick refreshes the effect position from the current reticle.
source = replace_once(
    source,
    "\t\tModify Player Variable(Event Player, PutaranKartuNasib, Subtract, 1);\n\t\tPlay Effect(All Players(All Teams), Ring Explosion, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Event Player.PosisiKartuNasib, 1.500);",
    "\t\tModify Player Variable(Event Player, PutaranKartuNasib, Subtract, 1);\n\t\tEvent Player.PosisiKartuNasib = Eye Position(Event Player) + Facing Direction Of(Event Player) * 4;\n\t\tPlay Effect(All Players(All Teams), Ring Explosion, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Event Player.PosisiKartuNasib, 1.500);",
    "reticle effect refresh",
)
source = replace_once(
    source,
    "\t\tLoop If Condition Is True;\n\t\tStop Chasing Player Variable(Event Player, PosisiKartuNasib);\n\t\tIf(Event Player.KartuNasibMerah == True);",
    "\t\tLoop If Condition Is True;\n\t\tIf(Event Player.KartuNasibMerah == True);",
    "remove obsolete roulette chase stop",
)

# Once Putaran reaches zero the rule condition is false. Outcome waits therefore
# must ignore the original condition. Explicit guards cancel an old countdown if
# the owner dies and starts a fresh card after respawning.
source = replace_once(
    source,
    '''\t\t\tWait(1, Abort When False);\n\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("RED! Death in 2...") : Event Player.IndeksBahasa == 1 ? Custom String("MERAH! Mati dalam 2...") : Custom String("แดง! ตายใน 2..."));\n\t\t\tWait(1, Abort When False);\n\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("RED! Death in 1...") : Event Player.IndeksBahasa == 1 ? Custom String("MERAH! Mati dalam 1...") : Custom String("แดง! ตายใน 1..."));\n\t\t\tWait(1, Abort When False);\n\t\t\tClear Status(Event Player, Unkillable);''',
    '''\t\t\tWait(1, Ignore Condition);\n\t\t\tAbort If(Event Player.KartuNasibAktif == False);\n\t\t\tAbort If(Event Player.PutaranKartuNasib > 0);\n\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("RED! Death in 2...") : Event Player.IndeksBahasa == 1 ? Custom String("MERAH! Mati dalam 2...") : Custom String("แดง! ตายใน 2..."));\n\t\t\tWait(1, Ignore Condition);\n\t\t\tAbort If(Event Player.KartuNasibAktif == False);\n\t\t\tAbort If(Event Player.PutaranKartuNasib > 0);\n\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("RED! Death in 1...") : Event Player.IndeksBahasa == 1 ? Custom String("MERAH! Mati dalam 1...") : Custom String("แดง! ตายใน 1..."));\n\t\t\tWait(1, Ignore Condition);\n\t\t\tAbort If(Event Player.KartuNasibAktif == False);\n\t\t\tAbort If(Event Player.PutaranKartuNasib > 0);\n\t\t\tClear Status(Event Player, Unkillable);''',
    "safe red countdown",
)
source = replace_once(
    source,
    "\t\t\tWait(1.500, Abort When False);\n\t\tEnd;",
    "\t\t\tWait(1.500, Ignore Condition);\n\t\t\tAbort If(Event Player.KartuNasibAktif == False);\n\t\t\tAbort If(Event Player.PutaranKartuNasib > 0);\n\t\tEnd;",
    "safe green linger",
)

# Death before completion is a hard reset. The running Wait uses Abort When False,
# so clearing KartuNasibAktif also terminates the roulette action sequence.
old_death = '''\t\tactions\n\t{\n\t\tStop Chasing Player Variable(Event Player, PosisiKartuNasib);\n\t\tIf(Event Player.TeksKartuNasib != Null);\n\t\t\tDestroy In-World Text(Event Player.TeksKartuNasib);\n\t\tEnd;\n\t\tEvent Player.TeksKartuNasib = Null;\n\t\tEvent Player.KartuNasibAktif = False;\n\t}\n}'''.replace("\t\tactions", "\tactions")
new_death = '''\tactions\n\t{\n\t\tIf(Event Player.TeksKartuNasib != Null);\n\t\t\tDestroy In-World Text(Event Player.TeksKartuNasib);\n\t\tEnd;\n\t\tEvent Player.TeksKartuNasib = Null;\n\t\tEvent Player.KartuNasibAktif = False;\n\t\tEvent Player.KartuNasibMerah = False;\n\t\tEvent Player.PutaranKartuNasib = 0;\n\t\tEvent Player.JedaKartuNasib = 0;\n\t\tEvent Player.PosisiKartuNasib = Vector(0, 0, 0);\n\t}\n}'''
# Limit the replacement to the death rule region so another cleanup cannot match it.
death_start = source.index('rule("18f - Nasib: Hapus kartu saat pemilik mati")')
death_end = source.index('rule("19 - Teleportasi Jongkok:', death_start)
death_region = source[death_start:death_end]
old_actions = '''\tactions\n\t{\n\t\tStop Chasing Player Variable(Event Player, PosisiKartuNasib);\n\t\tIf(Event Player.TeksKartuNasib != Null);\n\t\t\tDestroy In-World Text(Event Player.TeksKartuNasib);\n\t\tEnd;\n\t\tEvent Player.TeksKartuNasib = Null;\n\t\tEvent Player.KartuNasibAktif = False;\n\t}\n}\n\n'''
new_actions = '''\tactions\n\t{\n\t\tIf(Event Player.TeksKartuNasib != Null);\n\t\t\tDestroy In-World Text(Event Player.TeksKartuNasib);\n\t\tEnd;\n\t\tEvent Player.TeksKartuNasib = Null;\n\t\tEvent Player.KartuNasibAktif = False;\n\t\tEvent Player.KartuNasibMerah = False;\n\t\tEvent Player.PutaranKartuNasib = 0;\n\t\tEvent Player.JedaKartuNasib = 0;\n\t\tEvent Player.PosisiKartuNasib = Vector(0, 0, 0);\n\t}\n}\n\n'''
if death_region.count(old_actions) != 1:
    raise RuntimeError("death reset: expected one cleanup action block")
death_region = death_region.replace(old_actions, new_actions, 1)
source = source[:death_start] + death_region + source[death_end:]

SOURCE.write_text(source, encoding="utf-8")

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_once(
    validator,
    'checks.require(luck_code.count("Wait(1, Abort When False);") == 3, "Nasib: countdown rosso deve durare tre secondi")',
    'checks.require(luck_code.count("Wait(1, Ignore Condition);") == 3, "Nasib: countdown rosso deve durare tre secondi anche dopo Putaran == 0")\n        checks.require(luck_code.count("Abort If(Event Player.KartuNasibAktif == False);") >= 4, "Nasib: outcome non si annulla dopo morte/reset")\n        checks.require(luck_code.count("Abort If(Event Player.PutaranKartuNasib > 0);") >= 4, "Nasib: una vecchia outcome può interferire con una nuova roulette")',
    "validator safe outcome waits",
)
validator = replace_once(
    validator,
    '"Event Player.PosisiKartuNasib, 3.500, Do Not Clip" in card_texts[0],\n            "Nasib: la carta pubblica deve usare dimensione 3,5",',
    '"Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), 3.500, Do Not Clip" in card_texts[0],\n            "Nasib: la carta pubblica deve restare agganciata al mirino a 4 m e usare dimensione 3,5",',
    "validator reticle card position",
)
validator = replace_once(
    validator,
    '        checks.require(\n            "Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255)" in card_texts[0],\n            "Nasib: il testo mondo non cambia dinamicamente rosso/verde",\n        )',
    '        checks.require(\n            "Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255)" in card_texts[0],\n            "Nasib: il testo mondo non cambia dinamicamente rosso/verde",\n        )\n        checks.require(\n            "Event Player.KartuNasibMerah ? Icon String(Skull) : Icon String(Heart)" in card_texts[0]\n            and "TRY YOUR LUCK" not in card_texts[0]\n            and "COBA NASIB" not in card_texts[0],\n            "Nasib: la carta deve mostrare solo teschio rosso o cuore verde senza etichetta",\n        )',
    "validator heart skull only",
)
validator = replace_once(
    validator,
    '    checks.require(\n        "Event Player.PosisiKartuNasib = Position Of(Event Player) + Direction From Angles(Horizontal Facing Angle Of(Event Player), 0) * 2.500 - Vector(0, 0.450, 0);" in mask_strings(source),\n        "Nasib: posizione bassa davanti al proprietario assente",\n    )\n    checks.require(\n        "Chase Player Variable Over Time(Event Player, PosisiKartuNasib, Event Player.PosisiKartuNasib + Vector(0, 1.000, 0), 0.600, Destination and Duration);" in mask_strings(source),\n        "Nasib: animazione bassa di emersione dal terreno assente",\n    )',
    '    checks.require(\n        "Event Player.PosisiKartuNasib = Eye Position(Event Player) + Facing Direction Of(Event Player) * 4;" in mask_strings(source),\n        "Nasib: cache effetto non segue il mirino del proprietario",\n    )\n    checks.require(\n        "Chase Player Variable Over Time(Event Player, PosisiKartuNasib" not in mask_strings(source),\n        "Nasib: la vecchia animazione dal terreno non deve restare attiva",\n    )',
    "validator remove ground chase",
)
validator = replace_once(
    validator,
    'and "Event Player.PutaranKartuNasib = Random Integer(12, 16);" in clean\n        and "Event Player.JedaKartuNasib = 0.080;" in clean,\n        "Nasib: inizializzazione casuale 50/50 e 12..16 passaggi assente",',
    'and "Event Player.PutaranKartuNasib = Random Integer(20, 24);" in clean\n        and "Event Player.JedaKartuNasib = 0.080;" in clean,\n        "Nasib: inizializzazione casuale 50/50 e 20..24 passaggi assente",',
    "validator longer roulette",
)
# Explicit death reset contract.
marker = '    menu_interact = next(rule.body for rule in rules if rule.name.startswith("10 - Menu:"))\n'
death_check = '''    death_reset = [rule for rule in rules if rule.name.startswith("18f - Nasib:")]\n    checks.equal(len(death_reset), 1, "Nasib: una sola regola reset alla morte")\n    if death_reset:\n        checks.require(\n            code_contains(\n                death_reset[0].body,\n                "Event Player.KartuNasibAktif = False;",\n                "Event Player.KartuNasibMerah = False;",\n                "Event Player.PutaranKartuNasib = 0;",\n                "Event Player.JedaKartuNasib = 0;",\n                "Event Player.PosisiKartuNasib = Vector(0, 0, 0);",\n                "Destroy In-World Text(Event Player.TeksKartuNasib);",\n            ),\n            "Nasib: morte prima della fine non resetta completamente la carta",\n        )\n\n'''
validator = replace_once(validator, marker, death_check + marker, "validator death reset")
VALIDATOR.write_text(validator, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
project = replace_once(
    project,
    "Interact crea 2,5 m davanti al giocatore una carta virtuale che emerge dal terreno con un `Ring Explosion`. La posizione resta calcolata dal piano dei piedi del proprietario e il testo usa dimensione 3,5. Appena compare, la carta avvia automaticamente una roulette rosso/verde: il colore iniziale è casuale, esegue 12..16 cambi e parte con intervallo 0,08 s aggiungendo 0,055 s a ogni passaggio, quindi rallenta progressivamente. La carta è visibile a tutti e non occupa slot bot.",
    "Interact crea una carta virtuale agganciata al mirino del proprietario, circa 4 m davanti agli occhi, rivalutata ogni frame e visibile a tutti. Non mostra più testo: usa soltanto `Icon String(Heart)` in verde oppure `Icon String(Skull)` in rosso. La roulette parte con colore casuale, esegue 20..24 cambi e parte da 0,08 s aggiungendo 0,055 s a ogni passaggio, quindi dura sensibilmente più a lungo e rallenta progressivamente.",
    "project reticle roulette",
)
project = replace_once(
    project,
    "Non serve più sparare. Quando la roulette termina, il colore finale decide l'esito: verde ripristina immediatamente la salute massima; rosso mantiene la carta rossa e mostra un countdown di 3 secondi, poi rimuove `Unkillable` e uccide il proprietario. Poiché colore iniziale e numero di cambi sono indipendenti, l'esito finale resta 50/50. Testo e stato vengono ripuliti anche alla morte o all'uscita del giocatore.",
    "Non serve sparare. Quando la roulette termina, il colore finale decide l'esito: verde ripristina immediatamente la salute massima; rosso mantiene il teschio rosso e mostra un countdown di 3 secondi, poi rimuove `Unkillable` e uccide il proprietario. Se il proprietario muore prima che la sequenza finisca, la carta viene distrutta e `KartuNasibAktif`, colore, contatore, intervallo e posizione vengono azzerati; una vecchia outcome non può colpire una nuova carta dopo il respawn. L'esito finale resta 50/50.",
    "project death reset",
)
PROJECT.write_text(project, encoding="utf-8")

validation = VALIDATION.read_text(encoding="utf-8")
validation = replace_once(
    validation,
    "64447f31db8b097f200babb5b0e131c1a738f825",
    git_blob_sha(SOURCE),
    "validation blob",
)
validation = replace_once(
    validation,
    "- Menu 10 Try Your Luck: roulette automatica rosso/verde progressivamente più lenta, verde cura completa, rosso uccide dopo countdown 3 s, esito 50/50;",
    "- Menu 10 Try Your Luck: cuore/teschio rosso-verde agganciato al mirino, 20..24 cambi progressivamente più lenti, reset completo alla morte, verde cura completa, rosso uccide dopo countdown 3 s, esito 50/50;",
    "validation Menu 10 note",
)
VALIDATION.write_text(validation, encoding="utf-8")
