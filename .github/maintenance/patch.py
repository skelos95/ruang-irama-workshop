from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"

OLD_BLOB = "479d89eacf09b081557ec636e79285da48c282e1"


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

old_card = '''\t\t\t\tCreate In-World Text(All Players(All Teams), Custom String("["), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 - Cross Product(Direction From Angles(Horizontal Facing Angle Of(Event Player), 0), Vector(0, 1, 0)) * 0.300), 2.200, Do Not Clip, Visible To Position String and Color, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Visible Never);\n\t\t\t\tEvent Player.TeksKartuNasib = Last Text ID;\n\t\t\t\tCreate In-World Text(All Players(All Teams), Custom String("]"), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 + Cross Product(Direction From Angles(Horizontal Facing Angle Of(Event Player), 0), Vector(0, 1, 0)) * 0.300), 2.200, Do Not Clip, Visible To Position String and Color, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Visible Never);\n\t\t\t\tEvent Player.TeksKartuNasibKanan = Last Text ID;'''

new_card = '''\t\t\t\t"Satu Header/Title berbentuk kotak menggantikan pasangan [ ]. Ikon Skull/Heart tetap berada di tengah kartu."\n\t\t\t\tCreate In-World Text(All Players(All Teams), Custom String("□"), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), 2.600, Do Not Clip, Visible To Position String and Color, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Visible Never);\n\t\t\t\tEvent Player.TeksKartuNasib = Last Text ID;\n\t\t\t\tEvent Player.TeksKartuNasibKanan = Null;'''

source = replace_exact(source, old_card, new_card)
SOURCE.write_text(source, encoding="utf-8")
new_blob = blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_exact(
    validator,
    f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"',
    f'EXPECTED_SOURCE_BLOB = "{new_blob}"',
)
marker = '    checks.require("Start Forcing Player Position(" not in source, "Try Your Luck non deve forzare la posizione")\n'
extra = marker + '''    if interact:\n        checks.require('Custom String("□")' in interact.body, "Try Your Luck non usa il quadrato Title unico")\n        checks.require('Custom String("[")' not in interact.body and 'Custom String("]")' not in interact.body, "Try Your Luck usa ancora le parentesi della carta")\n        checks.require("Event Player.TeksKartuNasibKanan = Last Text ID;" not in interact.body, "Try Your Luck crea ancora un secondo testo laterale")\n'''
validator = replace_exact(validator, marker, extra)
VALIDATOR.write_text(validator, encoding="utf-8")

print(f"Try Your Luck title-square card: {OLD_BLOB} -> {new_blob}")
