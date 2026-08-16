from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
TESTS = ROOT / "tests" / "test_validate_workshop.py"
README = ROOT / "README.md"
PROJECT = ROOT / "docs" / "PROGETTO.md"
TESTDOC = ROOT / "docs" / "TEST.md"
VALIDATION = ROOT / "docs" / "VALIDAZIONE.md"
VERSION = ROOT / "VERSION"


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    return hashlib.sha1(payload).hexdigest()


IDENTIFIER_RENAMES = {
    "NamaWarnaEN": "NamaWarnaInggris",
    "NamaHalamanEN": "NamaHalamanInggris",
    "NamaWarnaTH": "NamaWarnaThai",
    "NamaHalamanTH": "NamaHalamanThai",
    "LeaderVoto": "PemimpinSuara",
    "MaxVoti": "SuaraTerbanyak",
    "PariVoti": "SuaraSeri",
    "IndeksVoto": "IndeksHitungSuara",
    "KursorVoto": "KursorPilihan",
    "TargetVoto": "PemainDipilih",
    "NumeroVoti": "JumlahSuara",
    "GambarVoto": "GambarPilihan",
}

FILES = [SOURCE, VALIDATOR, TESTS, README, PROJECT, TESTDOC, VALIDATION]
for path in FILES:
    text = path.read_text(encoding="utf-8")
    for old, new in IDENTIFIER_RENAMES.items():
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")

# Rule titles and Workshop-only comments: use Bahasa Indonesia rather than
# English/Italian leftovers. Native Workshop actions/keywords remain untouched.
source = SOURCE.read_text(encoding="utf-8")
TITLE_RENAMES = {
    'rule("18 - Kebal: Pasang kembali status setelah respawn")': 'rule("18 - Kebal: Pasang kembali status setelah muncul kembali")',
    'rule("18d - Kebal: Mode FULL HP selalu kembali penuh")': 'rule("18d - Kebal: Mode HP PENUH selalu kembali penuh")',
    'rule("18c - Kebal: Nonaktifkan hanya mode 1 HP di Spawn Room")': 'rule("18c - Kebal: Nonaktifkan hanya mode 1 HP di Ruang Muncul")',
    'rule("19a - Teleportasi Jongkok: Pengatur masukan terpisah dari Menu Arcade")': 'rule("19a - Teleportasi Jongkok: Pengatur masukan terpisah dari Menu Arkade")',
}
for old, new in TITLE_RENAMES.items():
    if old not in source:
        raise RuntimeError(f"rule title not found: {old}")
    source = source.replace(old, new, 1)

COMMENT_RENAMES = {
    '"Tunda satu frame agar handler menyelesaikan perintah sebelum dispatcher diaktifkan kembali."': '"Tunda satu bingkai agar pengendali menyelesaikan perintah sebelum pengatur masukan diaktifkan kembali."',
    '"Biarkan frame Interact selesai sebelum mengganti render kamera."': '"Biarkan satu bingkai Interact selesai sebelum mengganti tampilan kamera."',
    '"Ganti kamera langsung tanpa Stop Camera agar perpindahan target tidak berkedip satu frame."': '"Ganti kamera langsung tanpa Stop Camera agar perpindahan target tidak berkedip satu bingkai."',
}
for old, new in COMMENT_RENAMES.items():
    if old in source:
        source = source.replace(old, new)
SOURCE.write_text(source, encoding="utf-8")

# Version patch.
VERSION.write_text("0.6.1\n", encoding="utf-8")
for path in (README, PROJECT, TESTDOC, VALIDATION, VALIDATOR):
    text = path.read_text(encoding="utf-8").replace("0.6.0", "0.6.1")
    path.write_text(text, encoding="utf-8")

# Strengthen validator: identifiers must not contain the known legacy
# English/Italian fragments, while technical Indonesian loanwords and native
# Workshop terms remain allowed.
validator = VALIDATOR.read_text(encoding="utf-8")
anchor = '''ITALIAN_WORDS = {
'''
insert = '''FOREIGN_IDENTIFIER_WORDS = {
    "leader", "voto", "voti", "numero", "max", "pari", "en", "th",
}

FOREIGN_RULE_OR_COMMENT_WORDS = {
    "respawn", "spawn", "full", "arcade", "vote", "leader", "roulette",
    "frame", "handler", "dispatcher", "client", "cache", "render",
}

'''
if insert not in validator:
    validator = validator.replace(anchor, insert + anchor, 1)

old_identifier_check = '''            hits = set(identifier_tokens(name)) & ITALIAN_WORDS
            checks.require(
                not hits,
                f"identificatore {table_name} non indonesiano {name!r}: {sorted(hits)}",
            )
'''
new_identifier_check = '''            tokens = set(identifier_tokens(name))
            hits = tokens & (ITALIAN_WORDS | FOREIGN_IDENTIFIER_WORDS)
            checks.require(
                not hits,
                f"identificatore {table_name} non indonesiano {name!r}: {sorted(hits)}",
            )
'''
if old_identifier_check not in validator:
    raise RuntimeError("validator identifier-language block not found")
validator = validator.replace(old_identifier_check, new_identifier_check, 1)

old_rule_check = '''    for rule in rules:
        hits = italian_hits(rule.name)
        checks.require(
            not hits,
            f"nome regola non indonesiano {rule.name!r}: {sorted(hits)}",
        )
    for number, comment in standalone_comments(source):
        hits = italian_hits(comment)
        checks.require(
            not hits,
            f"commento non indonesiano alla riga {number}: {sorted(hits)}",
        )
'''
new_rule_check = '''    for rule in rules:
        tokens = set(word_tokens(rule.name))
        hits = tokens & (ITALIAN_WORDS | FOREIGN_RULE_OR_COMMENT_WORDS)
        checks.require(
            not hits,
            f"nome regola non indonesiano {rule.name!r}: {sorted(hits)}",
        )
    for number, comment in standalone_comments(source):
        tokens = set(word_tokens(comment))
        hits = tokens & (ITALIAN_WORDS | FOREIGN_RULE_OR_COMMENT_WORDS)
        checks.require(
            not hits,
            f"commento non indonesiano alla riga {number}: {sorted(hits)}",
        )
'''
if old_rule_check not in validator:
    raise RuntimeError("validator rule/comment-language block not found")
validator = validator.replace(old_rule_check, new_rule_check, 1)

# Extend stale identifier guard so old mixed-language names can never return.
old_stale = '''        "PosSpawnRoom", "NomorUrut",
    }
'''
new_stale = '''        "PosSpawnRoom", "NomorUrut", "NamaWarnaEN", "NamaHalamanEN",
        "NamaWarnaTH", "NamaHalamanTH", "LeaderVoto", "MaxVoti", "PariVoti",
        "IndeksVoto", "KursorVoto", "TargetVoto", "NumeroVoti", "GambarVoto",
    }
'''
if old_stale not in validator:
    raise RuntimeError("validator stale identifier block not found")
validator = validator.replace(old_stale, new_stale, 1)
VALIDATOR.write_text(validator, encoding="utf-8")

# Two regression tests for identifier/rule naming. 24 -> 26 tests.
tests = TESTS.read_text(encoding="utf-8")
marker = '\n\nif __name__ == "__main__":\n    unittest.main()'
extra = r'''

    def test_mixed_language_vote_identifier_is_rejected(self) -> None:
        mutated = self.source.replace("PemimpinSuara", "LeaderVoto", 1)
        self.assertNotEqual(mutated, self.source)
        global_names, player_names, subroutines = validator.declaration_tables(mutated)
        checks = validator.Checks()
        validator.check_source_structure(
            checks, mutated, self.rules(mutated), global_names, player_names, subroutines
        )
        self.assertTrue(any("LeaderVoto" in error and "non indonesiano" in error for error in checks.errors), checks.errors)

    def test_english_word_in_rule_title_is_rejected(self) -> None:
        mutated = self.source.replace(
            'rule("18 - Kebal: Pasang kembali status setelah muncul kembali")',
            'rule("18 - Kebal: Pasang kembali status setelah respawn")',
            1,
        )
        self.assertNotEqual(mutated, self.source)
        global_names, player_names, subroutines = validator.declaration_tables(mutated)
        checks = validator.Checks()
        validator.check_source_structure(
            checks, mutated, self.rules(mutated), global_names, player_names, subroutines
        )
        self.assertTrue(any("respawn" in error and "nama regola" in error for error in checks.errors), checks.errors)
'''
if extra.strip() not in tests:
    if marker not in tests:
        raise RuntimeError("test insertion marker not found")
    tests = tests.replace(marker, extra + marker, 1)
TESTS.write_text(tests, encoding="utf-8")

# Documentation consistency.
for path in (README, PROJECT, TESTDOC, VALIDATION):
    text = path.read_text(encoding="utf-8")
    text = text.replace("24 unit test", "26 unit test").replace("Ran 24 tests", "Ran 26 tests")
    path.write_text(text, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
if "## Nomenclatura Bahasa Indonesia 0.6.1" not in project:
    project += '''\n\n## Nomenclatura Bahasa Indonesia 0.6.1\n\nLe dichiarazioni personalizzate non usano più i residui misti `Voto/Voti/Numero/Leader/Max/Pari` o i suffissi `EN/TH`: sono stati sostituiti da nomi Bahasa Indonesia come `PemimpinSuara`, `SuaraTerbanyak`, `SuaraSeri`, `IndeksHitungSuara`, `KursorPilihan`, `PemainDipilih`, `JumlahSuara`, `NamaWarnaInggris` e `NamaWarnaThai`. Anche `GambarVoto` è diventata `GambarPilihan`. I titoli regola e i commenti personalizzati evitano ora termini come `respawn`, `Spawn Room`, `FULL HP`, `Arcade`, `frame`, `handler` e `dispatcher` quando esiste una formulazione Bahasa Indonesia. Le keyword e azioni native di Overwatch Workshop restano necessariamente nella sintassi ufficiale inglese.\n'''
PROJECT.write_text(project, encoding="utf-8")

readme = README.read_text(encoding="utf-8")
if "Nomenclatura 0.6.1" not in readme:
    readme += '''\n\n### Nomenclatura 0.6.1\n\nVariabili, subroutine, titoli regola e commenti personalizzati sono ora controllati contro i residui linguistici legacy. Restano in inglese soltanto keyword/azioni native Workshop e i contenuti HUD del ramo English.\n'''
README.write_text(readme, encoding="utf-8")

# Refresh validation report's source blob after all source edits.
validation = VALIDATION.read_text(encoding="utf-8")
blob = git_blob_sha(SOURCE)
import re
validation = re.sub(
    r"(Blob Git del sorgente Workshop validato:\s*```text\s*)[0-9a-f]{40}(\s*```)",
    rf"\g<1>{blob}\g<2>",
    validation,
    count=1,
)
validation = validation.replace("24 unit test", "26 unit test").replace("Ran 24 tests", "Ran 26 tests")
if "nomenclatura Bahasa Indonesia" not in validation:
    validation = validation.replace(
        "## Audit 0.6.1\n",
        "## Audit 0.6.1\n\n- nomenclatura Bahasa Indonesia verificata anche per identificatori, titoli regola e commenti personalizzati;\n",
        1,
    )
VALIDATION.write_text(validation, encoding="utf-8")
