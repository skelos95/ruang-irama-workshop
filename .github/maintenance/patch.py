from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
TESTS = ROOT / "tests" / "test_validate_workshop.py"

OLD_BLOB = "93dac1fb4ca624981842d54df041acb49f824166"


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

# Workshop For Range Stop is exclusive: using Count-1 skips the last player
# and executes zero iterations for a one-player array. Use Count everywhere.
source = replace_exact(
    source,
    "For Global Variable(IndeksPemainGlobal, 0, Count Of(All Players(All Teams)) - 1, 1);",
    "For Global Variable(IndeksPemainGlobal, 0, Count Of(All Players(All Teams)), 1);",
    expected=2,
)
source = replace_exact(
    source,
    "For Global Variable(IndeksPemainGlobal, 0, Count Of(Global.PemainManusia) - 1, 1);",
    "For Global Variable(IndeksPemainGlobal, 0, Count Of(Global.PemainManusia), 1);",
    expected=2,
)
source = replace_exact(
    source,
    "For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia) - 1, 1);",
    "For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia), 1);",
)
source = replace_exact(
    source,
    "For Global Variable(IndeksPembersihan, 0, Count Of(Global.PemainManusia) - 1, 1);",
    "For Global Variable(IndeksPembersihan, 0, Count Of(Global.PemainManusia), 1);",
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
    '        checks.require("For Global Variable(IndeksPemainGlobal" in manager.body, f"{manager.name}: loop player globale assente")\n        checks.require("Global.PemainAktif = All Players(All Teams)" in manager.body, f"{manager.name}: contesto player assente")',
    '        checks.require("For Global Variable(IndeksPemainGlobal" in manager.body, f"{manager.name}: loop player globale assente")\n        checks.require("Count Of(All Players(All Teams)), 1);" in manager.body, f"{manager.name}: Range Stop deve usare Count perché è esclusivo")\n        checks.require("Global.PemainAktif = All Players(All Teams)" in manager.body, f"{manager.name}: contesto player assente")',
)

validator = replace_exact(
    validator,
    '            checks.require("For Global Variable(IndeksPemainGlobal" in rule.body, f"{prefix}: loop globale assente")\n            checks.require("Global.PemainAktif = Global.PemainManusia[Global.IndeksPemainGlobal]" in rule.body, f"{prefix}: contesto umano globale assente")',
    '            checks.require("For Global Variable(IndeksPemainGlobal" in rule.body, f"{prefix}: loop globale assente")\n            checks.require("Count Of(Global.PemainManusia), 1);" in rule.body, f"{prefix}: Range Stop deve usare Count perché è esclusivo")\n            checks.require("Global.PemainAktif = Global.PemainManusia[Global.IndeksPemainGlobal]" in rule.body, f"{prefix}: contesto umano globale assente")',
)

validator = replace_exact(
    validator,
    '    checks.require("For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia), 1);" not in source, "loop voto fuori limite Count anziché Count-1")\n    checks.require("For Global Variable(IndeksPemilihVote, 0, Count Of(Global.PemainManusia), 1);" not in source, "loop votanti fuori limite Count anziché Count-1")',
    '    checks.require("For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia) - 1, 1);" not in source, "loop voto usa Count-1 ma Range Stop è esclusivo")\n    checks.require("For Global Variable(IndeksPemilihVote, 0, Count Of(Global.PemainManusia) - 1, 1);" not in source, "loop votanti usa Count-1 ma Range Stop è esclusivo")',
)
validator = replace_exact(
    validator,
    '    checks.require("For Global Variable(IndeksPembersihan, 0, Count Of(Global.PemainManusia), 1);" not in source, "loop cleanup fuori limite Count anziché Count-1")',
    '    checks.require("For Global Variable(IndeksPembersihan, 0, Count Of(Global.PemainManusia) - 1, 1);" not in source, "loop cleanup usa Count-1 ma Range Stop è esclusivo")',
)
VALIDATOR.write_text(validator, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
old_test = '''    def test_vote_loop_count_stop_is_rejected(self) -> None:\n        mutated = self.source.replace(\n            "For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia) - 1, 1);",\n            "For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia), 1);",\n            1,\n        )\n        self.assertTrue(any("fuori limite" in error for error in self.errors(mutated)))\n'''
new_test = '''    def test_vote_loop_count_minus_one_is_rejected(self) -> None:\n        mutated = self.source.replace(\n            "For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia), 1);",\n            "For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia) - 1, 1);",\n            1,\n        )\n        self.assertTrue(any("Range Stop" in error for error in self.errors(mutated)))\n\n    def test_fast_manager_count_minus_one_is_rejected(self) -> None:\n        mutated = self.source.replace(\n            "For Global Variable(IndeksPemainGlobal, 0, Count Of(All Players(All Teams)), 1);",\n            "For Global Variable(IndeksPemainGlobal, 0, Count Of(All Players(All Teams)) - 1, 1);",\n            1,\n        )\n        self.assertTrue(any("Range Stop" in error for error in self.errors(mutated)))\n'''
tests = replace_exact(tests, old_test, new_test)
TESTS.write_text(tests, encoding="utf-8")

print(f"fixed exclusive Workshop loop bounds: {OLD_BLOB} -> {new_blob}")
