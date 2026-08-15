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
source = replace_once(
    source,
    'Create In-World Text(All Players(All Teams), Custom String("[{0}]", Event Player.KartuNasibMerah ? Icon String(Skull) : Icon String(Heart)), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), 3.500, Do Not Clip, Visible To Position String and Color, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Visible Never);',
    'Create In-World Text(All Players(All Teams), Event Player.KartuNasibMerah ? Custom String("[ ☠ ]") : Custom String("[ ♥ ]"), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), 2.500, Do Not Clip, Visible To Position String and Color, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Visible Never);',
    "single colored card string",
)
SOURCE.write_text(source, encoding="utf-8")

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_once(
    validator,
    '"Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), 3.500, Do Not Clip" in card_texts[0],\n            "Nasib: la carta pubblica deve restare agganciata al mirino a 4 m e usare dimensione 3,5",',
    '"Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), 2.500, Do Not Clip" in card_texts[0],\n            "Nasib: la carta pubblica deve restare agganciata al mirino a 4 m e usare dimensione 2,5",',
    "validator card size",
)
validator = replace_once(
    validator,
    '"Custom String(\\\"[{0}]\\\", Event Player.KartuNasibMerah ? Icon String(Skull) : Icon String(Heart))" in card_texts[0]\n            and "TRY YOUR LUCK" not in card_texts[0]\n            and "COBA NASIB" not in card_texts[0],\n            "Nasib: la carta deve mostrare esattamente [teschio] rosso o [cuore] verde senza etichetta",',
    '"Custom String(\\\"[ ☠ ]\\\")" in card_texts[0]\n            and "Custom String(\\\"[ ♥ ]\\\")" in card_texts[0]\n            and "Icon String(" not in card_texts[0]\n            and "TRY YOUR LUCK" not in card_texts[0]\n            and "COBA NASIB" not in card_texts[0],\n            "Nasib: la carta deve usare simboli testuali centrati [ ☠ ] / [ ♥ ] colorabili, senza Icon String",',
    "validator colored symbol",
)
VALIDATOR.write_text(validator, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
project = project.replace(
    "La carta è resa come `[icona]`: `[Heart]` in verde oppure `[Skull]` in rosso, con parentesi e icona dello stesso colore.",
    "La carta è resa come un unico testo colorabile: `[ ♥ ]` in verde oppure `[ ☠ ]` in rosso, a dimensione 2,5. Non usa più `Icon String`, perché nel client quell'icona restava bianca e visivamente più grande delle parentesi.",
)
PROJECT.write_text(project, encoding="utf-8")

validation = VALIDATION.read_text(encoding="utf-8")
new_blob = git_blob_sha(SOURCE)
validation, count = re.subn(
    r"(?s)(Blob Git del sorgente Workshop validato:\s*```text\s*)[0-9a-f]{40}(\s*```)",
    rf"\g<1>{new_blob}\g<2>",
    validation,
    count=1,
)
if count != 1:
    raise RuntimeError("validation blob: expected one documented Workshop SHA")
validation = validation.replace(
    "carta `[icona]` agganciata al mirino, `[cuore]` verde / `[teschio]` rosso senza Ring Explosion",
    "carta `[ ♥ ]` verde / `[ ☠ ]` rossa agganciata al mirino, dimensione 2,5 e senza Ring Explosion",
)
VALIDATION.write_text(validation, encoding="utf-8")
