from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
PROJECT = ROOT / "docs" / "PROGETTO.md"
VALIDATION = ROOT / "docs" / "VALIDAZIONE.md"


def replace_count(text: str, old: str, new: str, expected: int, label: str) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"{label}: expected {expected} occurrences, found {count}")
    return text.replace(old, new)


def replace_once(text: str, old: str, new: str, label: str) -> str:
    return replace_count(text, old, new, 1, label)


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    return hashlib.sha1(payload).hexdigest()


source = SOURCE.read_text(encoding="utf-8")

# Create Icon renders visually above its supplied world point. Live testing at the
# current 4 m reticle distance shows ~0.45 m of compensation centers it inside the
# bracket IWT. Apply the same offset to initial creation and every roulette refresh.
source = replace_count(
    source,
    "Eye Position(Event Player) + Facing Direction Of(Event Player) * 4, Skull, Visible To and Position",
    "Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 - Vector(0, 0.450, 0), Skull, Visible To and Position",
    2,
    "Skull vertical compensation",
)
source = replace_count(
    source,
    "Eye Position(Event Player) + Facing Direction Of(Event Player) * 4, Heart, Visible To and Position",
    "Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 - Vector(0, 0.450, 0), Heart, Visible To and Position",
    2,
    "Heart vertical compensation",
)
SOURCE.write_text(source, encoding="utf-8")

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_once(
    validator,
    '                and "Eye Position(Event Player) + Facing Direction Of(Event Player) * 4" in call\n                and "Visible To and Position" in call,\n                "Nasib: icona nativa non è pubblica o non segue il mirino",',
    '                and "Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 - Vector(0, 0.450, 0)" in call\n                and "Visible To and Position" in call,\n                "Nasib: icona nativa non è pubblica, non segue il mirino o manca la compensazione verticale da 0,45 m",',
    "validator icon compensation",
)
VALIDATOR.write_text(validator, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
project = replace_once(
    project,
    "La carta usa parentesi separate (`[     ]`, dimensione 2,2) e un vero `Create Icon` nativo centrato nello stesso punto: `Heart` verde oppure `Skull` rosso. Il simbolo Unicode `☠` è stato rimosso perché il font Workshop lo sostituiva con un carattere generico; l'icona nativa viene distrutta e ricreata a ogni cambio della roulette per garantire sia il simbolo sia il colore corretti.",
    "La carta usa parentesi separate (`[     ]`, dimensione 2,2) e un vero `Create Icon` nativo: `Heart` verde oppure `Skull` rosso. Poiché `Create Icon` viene renderizzato visivamente più in alto rispetto all'In-World Text alla stessa coordinata, l'ancora dell'icona è compensata di `Vector(0, -0.450, 0)` rispetto al punto del mirino, così il simbolo cade dentro le parentesi. L'icona viene distrutta e ricreata a ogni cambio della roulette per garantire simbolo e colore corretti.",
    "project icon centering",
)
PROJECT.write_text(project, encoding="utf-8")

validation = VALIDATION.read_text(encoding="utf-8")
validation = validation.replace(
    "parentesi colorate + icona nativa `Heart` verde / `Skull` rossa agganciata al mirino",
    "parentesi colorate + icona nativa `Heart` verde / `Skull` rossa agganciata al mirino con compensazione verticale -0,45 m",
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
