from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"

OLD_BLOB = "37032467d7e305c77f82a18d53c23fe56c3aa45f"


def blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def replace_exact(text: str, old: str, new: str, expected: int = 1) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"replacement mismatch: expected {expected}, found {count}: {old[:180]!r}")
    return text.replace(old, new)


source = SOURCE.read_text(encoding="utf-8")
if blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch moving target")

# Remove the text frame entirely. Keep legacy text handles null for cleanup compatibility.
old_frame = '''\t\t\t\t"Satu Header/Title berbentuk kotak menggantikan pasangan [ ]. Ikon Skull/Heart tetap berada di tengah kartu."\n\t\t\t\tCreate In-World Text(All Players(All Teams), Custom String("□"), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), 20.000, Do Not Clip, Visible To Position String and Color, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Visible Never);\n\t\t\t\tEvent Player.TeksKartuNasib = Last Text ID;\n\t\t\t\tEvent Player.TeksKartuNasibKanan = Null;'''
new_frame = '''\t\t\t\t"Try Your Luck memakai hanya ikon Skull/Heart tepat di reticolo; tidak ada frame atau world text."\n\t\t\t\tEvent Player.TeksKartuNasib = Null;\n\t\t\t\tEvent Player.TeksKartuNasibKanan = Null;'''
source = replace_exact(source, old_frame, new_frame)

# Center both roulette icons exactly on the player's current reticle.
source = replace_exact(
    source,
    'Create Icon(Event Player.KartuNasibMerah ? All Players(All Teams) : Empty Array, Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 - Vector(0, 0.450, 0)), Skull, Visible To and Position, Custom Color(255, 70, 70, 255), False);',
    'Create Icon(Event Player.KartuNasibMerah ? All Players(All Teams) : Empty Array, Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Skull, Visible To and Position, Custom Color(255, 70, 70, 255), False);',
)
source = replace_exact(
    source,
    'Create Icon(Event Player.KartuNasibMerah ? Empty Array : All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 - Vector(0, 0.450, 0)), Heart, Visible To and Position, Custom Color(70, 255, 110, 255), False);',
    'Create Icon(Event Player.KartuNasibMerah ? Empty Array : All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Heart, Visible To and Position, Custom Color(70, 255, 110, 255), False);',
)

SOURCE.write_text(source, encoding="utf-8")
new_blob = blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_exact(
    validator,
    f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"',
    f'EXPECTED_SOURCE_BLOB = "{new_blob}"',
)
validator = replace_exact(
    validator,
    '    checks.require(\'Custom String("□"), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), 20.000, Do Not Clip\' in source, "Try Your Luck card frame non usa la scala 20.000")\n',
    '    checks.require(\'Custom String("□")\' not in source, "Try Your Luck crea ancora il quadrato della carta")\n',
)
validator = replace_exact(
    validator,
    '''    if interact:\n        checks.require('Custom String("□")' in interact.body, "Try Your Luck non usa il quadrato Title unico")\n        checks.require('Custom String("[")' not in interact.body and 'Custom String("]")' not in interact.body, "Try Your Luck usa ancora le parentesi della carta")\n        checks.require("Event Player.TeksKartuNasibKanan = Last Text ID;" not in interact.body, "Try Your Luck crea ancora un secondo testo laterale")\n''',
    '''    if interact:\n        checks.require('Custom String("□")' not in interact.body and 'Custom String("[")' not in interact.body and 'Custom String("]")' not in interact.body, "Try Your Luck deve mostrare solo l icona senza frame testuale")\n        checks.require("Event Player.TeksKartuNasib = Last Text ID;" not in interact.body and "Event Player.TeksKartuNasibKanan = Last Text ID;" not in interact.body, "Try Your Luck crea ancora world text della carta")\n        checks.require("Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Skull" in interact.body, "Skull Try Your Luck non resta centrato sul reticolo")\n        checks.require("Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Heart" in interact.body, "Heart Try Your Luck non resta centrato sul reticolo")\n        checks.require("Facing Direction Of(Event Player) * 4 - Vector" not in interact.body, "Try Your Luck mantiene ancora un offset sotto il reticolo")\n''',
)
VALIDATOR.write_text(validator, encoding="utf-8")

print(f"simplified Try Your Luck to reticle icon only: {OLD_BLOB} -> {new_blob}")
