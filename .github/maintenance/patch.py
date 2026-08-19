from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
TESTS = ROOT / "tests" / "test_validate_workshop.py"

OLD_BLOB = "ea8ca635d7baa82ce8c328bf19ef55cab06921c5"


def blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def one(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one match, found {count}: {old[:180]!r}")
    return text.replace(old, new, 1)


source = SOURCE.read_text(encoding="utf-8")
if blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch moving target")

old_conditions = """\tconditions
\t{
\t\tEvent Player.Manusia == True;
\t\tEvent Player.MenuNasibHarusDibuka == True;
\t\tEvent Player.KartuNasibAktif == False;
\t}

\tactions
\t{
\t\tEvent Player.MenuNasibHarusDibuka = False;"""
new_conditions = """\tconditions
\t{
\t\tEvent Player.Manusia == True;
\t\tEvent Player.MenuNasibHarusDibuka == True;
\t\tEvent Player.KartuNasibAktif == False;
\t\tHas Spawned(Event Player) == True;
\t\tIs Alive(Event Player) == True;
\t}

\tactions
\t{
\t\tEvent Player.MenuNasibHarusDibuka = False;"""
source = one(source, old_conditions, new_conditions)
SOURCE.write_text(source, encoding="utf-8")
new_blob = blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = one(validator, f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"', f'EXPECTED_SOURCE_BLOB = "{new_blob}"')
old_guard = '        checks.require("Event Player.KartuNasibAktif == False;" in luck_reopen.body, "18g riapre il menu prima che la funzione sia finita")\n'
new_guard = (
    old_guard
    + '        checks.require("Has Spawned(Event Player) == True;" in luck_reopen.body and "Is Alive(Event Player) == True;" in luck_reopen.body, "18g deve attendere il respawn vivo prima di consumare la riapertura")\n'
)
validator = one(validator, old_guard, new_guard)
VALIDATOR.write_text(validator, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
anchor = '''    def test_try_your_luck_forcing_position_is_rejected(self) -> None:\n        mutated = self.source + "\\nStart Forcing Player Position(Event Player, Position Of(Event Player), False);\\n"\n        self.assertTrue(any("forzare la posizione" in error for error in self.errors(mutated)))\n\n'''
addition = anchor + '''    def test_try_your_luck_reopen_waits_for_alive_respawn(self) -> None:\n        start = self.source.index('rule(\\"18g - Nasib:')\n        pos = self.source.index("Is Alive(Event Player) == True;", start)\n        mutated = self.source[:pos] + self.source[pos:].replace(\n            "Is Alive(Event Player) == True;",\n            "Is Alive(Event Player) == False;",\n            1,\n        )\n        self.assertTrue(any("respawn vivo" in error for error in self.errors(mutated)))\n\n'''
tests = one(tests, anchor, addition)
TESTS.write_text(tests, encoding="utf-8")

print(f"Try Your Luck respawn-visible menu: {OLD_BLOB} -> {new_blob}")
