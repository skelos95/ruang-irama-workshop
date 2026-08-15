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

# Card becomes exactly [icon], with the whole card and icon sharing the current
# roulette color. The In-World Text continues to follow the owner's reticle.
source = replace_once(
    source,
    "Create In-World Text(All Players(All Teams), Event Player.KartuNasibMerah ? Icon String(Skull) : Icon String(Heart), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), 3.500, Do Not Clip, Visible To Position String and Color, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Visible Never);",
    "Create In-World Text(All Players(All Teams), Custom String(\"[{0}]\", Event Player.KartuNasibMerah ? Icon String(Skull) : Icon String(Heart)), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), 3.500, Do Not Clip, Visible To Position String and Color, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Visible Never);",
    "bracketed luck card",
)

# Menu 10 no longer uses any Ring Explosion. The only remaining Play Effect calls
# belong to the generic apply/restore feedback system.
source = replace_once(
    source,
    "\t\t\t\tPlay Effect(All Players(All Teams), Ring Explosion, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Event Player.PosisiKartuNasib, 3);\n",
    "",
    "remove initial luck ring",
)
source = replace_once(
    source,
    "\t\tEvent Player.PosisiKartuNasib = Eye Position(Event Player) + Facing Direction Of(Event Player) * 4;\n\t\tPlay Effect(All Players(All Teams), Ring Explosion, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Event Player.PosisiKartuNasib, 1.500);\n",
    "",
    "remove roulette tick ring",
)

SOURCE.write_text(source, encoding="utf-8")

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_once(
    validator,
    '        checks.equal(len(call_texts(luck[0].body, "Play Effect")), 1, "Nasib: un solo Ring riutilizzato a ogni cambio colore")',
    '        checks.equal(len(call_texts(luck[0].body, "Play Effect")), 0, "Nasib: nessun Ring Explosion deve essere usato")',
    "validator no luck ring",
)
validator = replace_once(
    validator,
    '            "Event Player.KartuNasibMerah ? Icon String(Skull) : Icon String(Heart)" in card_texts[0]\n            and "TRY YOUR LUCK" not in card_texts[0]\n            and "COBA NASIB" not in card_texts[0],\n            "Nasib: la carta deve mostrare solo teschio rosso o cuore verde senza etichetta",',
    '            "Custom String(\\\"[{0}]\\\", Event Player.KartuNasibMerah ? Icon String(Skull) : Icon String(Heart))" in card_texts[0]\n            and "TRY YOUR LUCK" not in card_texts[0]\n            and "COBA NASIB" not in card_texts[0],\n            "Nasib: la carta deve mostrare esattamente [teschio] rosso o [cuore] verde senza etichetta",',
    "validator bracketed icon",
)
old_feedback = '''    effect_calls = call_texts(source, "Play Effect")
    checks.equal(len(effect_calls), 4, "feedback: due Ring RGB impostazioni più due Ring rosso/verde Nasib")
    system_effects = [call for call in effect_calls if "Global.RGB" in call]
    luck_effects = [call for call in effect_calls if "KartuNasibMerah" in call]
    checks.equal(len(system_effects), 2, "feedback: esattamente due Ring RGB di sistema")
    checks.equal(len(luck_effects), 2, "Nasib: esattamente due Ring rosso/verde")
    for index, call in enumerate(system_effects, 1):
        checks.require(
            "Ring Explosion" in call
            and "All Players(All Teams)" in call
            and "Sound" not in call,
            f"feedback sistema #{index}: deve essere Ring Explosion RGB visivo",
        )
    for index, call in enumerate(luck_effects, 1):
        checks.require(
            "Ring Explosion" in call
            and "Custom Color(255, 70, 70, 255)" in call
            and "Custom Color(70, 255, 110, 255)" in call
            and "All Players(All Teams)" in call
            and "Sound" not in call,
            f"Nasib effetto #{index}: deve alternare esclusivamente rosso/verde",
        )
'''
new_feedback = '''    effect_calls = call_texts(source, "Play Effect")
    checks.equal(len(effect_calls), 2, "feedback: solo i due Ring RGB generici; Menu 10 non usa effetti")
    system_effects = [call for call in effect_calls if "Global.RGB" in call]
    checks.equal(len(system_effects), 2, "feedback: esattamente due Ring RGB di sistema")
    checks.equal(
        len([call for call in effect_calls if "KartuNasibMerah" in call]),
        0,
        "Nasib: nessun Ring rosso/verde deve restare nel Menu 10",
    )
    for index, call in enumerate(system_effects, 1):
        checks.require(
            "Ring Explosion" in call
            and "All Players(All Teams)" in call
            and "Sound" not in call,
            f"feedback sistema #{index}: deve essere Ring Explosion RGB visivo",
        )
'''
validator = replace_once(validator, old_feedback, new_feedback, "validator feedback effect count")
VALIDATOR.write_text(validator, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
project = replace_once(
    project,
    "Interact crea una carta virtuale agganciata al mirino del proprietario, circa 4 m davanti agli occhi, rivalutata ogni frame e visibile a tutti. Non mostra più testo: usa soltanto `Icon String(Heart)` in verde oppure `Icon String(Skull)` in rosso. La roulette parte con colore casuale, esegue 20..24 cambi e parte da 0,08 s aggiungendo 0,055 s a ogni passaggio, quindi dura sensibilmente più a lungo e rallenta progressivamente.",
    "Interact crea una carta virtuale agganciata al mirino del proprietario, circa 4 m davanti agli occhi, rivalutata ogni frame e visibile a tutti. La carta è resa come `[icona]`: `[Heart]` in verde oppure `[Skull]` in rosso, con parentesi e icona dello stesso colore. Il Menu 10 non usa più alcun `Ring Explosion`. La roulette parte con colore casuale, esegue 20..24 cambi e parte da 0,08 s aggiungendo 0,055 s a ogni passaggio, quindi dura sensibilmente più a lungo e rallenta progressivamente.",
    "project bracket card",
)
PROJECT.write_text(project, encoding="utf-8")

validation = VALIDATION.read_text(encoding="utf-8")
validation = replace_once(
    validation,
    "a10f4fd19167d210056ec3a4c31ee84109f87617",
    git_blob_sha(SOURCE),
    "validation blob",
)
validation = replace_once(
    validation,
    "- Menu 10 Try Your Luck: cuore/teschio rosso-verde agganciato al mirino, 20..24 cambi progressivamente più lenti, reset completo alla morte, verde cura completa, rosso uccide dopo countdown 3 s, esito 50/50;",
    "- Menu 10 Try Your Luck: carta `[icona]` agganciata al mirino, `[cuore]` verde / `[teschio]` rosso senza Ring Explosion, 20..24 cambi progressivamente più lenti, reset completo alla morte, verde cura completa, rosso uccide dopo countdown 3 s, esito 50/50;",
    "validation Menu 10 note",
)
VALIDATION.write_text(validation, encoding="utf-8")
