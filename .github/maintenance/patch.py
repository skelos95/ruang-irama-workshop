from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
TESTS = ROOT / "tests" / "test_validate_workshop.py"

OLD_BLOB = "476f2b08fed274b308480bd22bcb12bcee6740e8"


def git_blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def replace_exact(text: str, old: str, new: str, expected: int = 1) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"replacement mismatch: expected {expected}, found {count}: {old[:140]!r}")
    return text.replace(old, new)


source = SOURCE.read_text(encoding="utf-8")
if git_blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch a moving target")

# 04k: privacy adds one extra And(...), so this expression needs one extra closing parenthesis.
old_global = '''\t\t\t\tSet Player Variable(Global.PemainAktif, DaftarTargetTeleportasi, Filtered Array(All Players(All Teams), And(Current Array Element != Global.PemainAktif,\n\t\t\t\t\tAnd(Player Variable(Current Array Element, PrivasiInspeksiAktif) == False, And(Entity Exists(Current Array Element),\n\t\t\t\t\tAnd(Has Spawned(Current Array Element), Is Alive(Current Array Element))))));'''
new_global = '''\t\t\t\tSet Player Variable(Global.PemainAktif, DaftarTargetTeleportasi, Filtered Array(All Players(All Teams), And(Current Array Element != Global.PemainAktif,\n\t\t\t\t\tAnd(Player Variable(Current Array Element, PrivasiInspeksiAktif) == False, And(Entity Exists(Current Array Element),\n\t\t\t\t\tAnd(Has Spawned(Current Array Element), Is Alive(Current Array Element)))))));'''
source = replace_exact(source, old_global, new_global)

# 98: same privacy filter, same missing closing parenthesis.
old_refresh = '''\t\tEvent Player.DaftarTargetTeleportasi = Filtered Array(All Players(All Teams), And(Current Array Element != Event Player,\n\t\t\tAnd(Player Variable(Current Array Element, PrivasiInspeksiAktif) == False, And(Entity Exists(Current Array Element),\n\t\t\tAnd(Has Spawned(Current Array Element), Is Alive(Current Array Element))))));'''
new_refresh = '''\t\tEvent Player.DaftarTargetTeleportasi = Filtered Array(All Players(All Teams), And(Current Array Element != Event Player,\n\t\t\tAnd(Player Variable(Current Array Element, PrivasiInspeksiAktif) == False, And(Entity Exists(Current Array Element),\n\t\t\tAnd(Has Spawned(Current Array Element), Is Alive(Current Array Element)))))));'''
source = replace_exact(source, old_refresh, new_refresh)

SOURCE.write_text(source, encoding="utf-8")
new_blob = git_blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_exact(validator, f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"', f'EXPECTED_SOURCE_BLOB = "{new_blob}"')

helper_anchor = '''def extract_rules(text: str) -> list[Rule]:\n'''
helper = '''def parentheses_balanced(text: str) -> bool:\n    depth = 0\n    in_string = False\n    escaped = False\n    for ch in text:\n        if in_string:\n            if escaped:\n                escaped = False\n            elif ch == "\\\\":\n                escaped = True\n            elif ch == '"':\n                in_string = False\n            continue\n        if ch == '"':\n            in_string = True\n        elif ch == "(":\n            depth += 1\n        elif ch == ")":\n            depth -= 1\n            if depth < 0:\n                return False\n    return depth == 0 and not in_string\n\n\n'''
validator = replace_exact(validator, helper_anchor, helper + helper_anchor)
validator = replace_exact(
    validator,
    '    checks.equal(len(rules), len({rule.name for rule in rules}), "titoli regola univoci")\n',
    '    checks.equal(len(rules), len({rule.name for rule in rules}), "titoli regola univoci")\n    checks.require(parentheses_balanced(source), "parentesi Workshop non bilanciate")\n',
)
VALIDATOR.write_text(validator, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
anchor = '''    def test_invalid_for_global_variable_syntax_is_rejected(self) -> None:\n'''
new_test = '''    def test_unbalanced_parentheses_are_rejected(self) -> None:\n        mutated = self.source.replace(\n            "Is Alive(Current Array Element)))))));",\n            "Is Alive(Current Array Element))))));",\n            1,\n        )\n        self.assertTrue(any("parentesi Workshop" in error for error in self.errors(mutated)))\n\n'''
tests = replace_exact(tests, anchor, new_test + anchor)
TESTS.write_text(tests, encoding="utf-8")

print(f"hotfixed 0.7.2: {OLD_BLOB} -> {new_blob}")
