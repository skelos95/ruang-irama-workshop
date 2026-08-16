from __future__ import annotations

import hashlib
import re
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


def blob_sha(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


renames = {
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

for path in (SOURCE, VALIDATOR, TESTS, README, PROJECT, TESTDOC, VALIDATION):
    text = path.read_text(encoding="utf-8")
    for old, new in renames.items():
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")

source = SOURCE.read_text(encoding="utf-8")
source_replacements = {
    'rule("18 - Kebal: Pasang kembali status setelah respawn")': 'rule("18 - Kebal: Pasang kembali status setelah muncul kembali")',
    'rule("18d - Kebal: Mode FULL HP selalu kembali penuh")': 'rule("18d - Kebal: Mode HP PENUH selalu kembali penuh")',
    'rule("18c - Kebal: Nonaktifkan hanya mode 1 HP di Spawn Room")': 'rule("18c - Kebal: Nonaktifkan hanya mode 1 HP di Ruang Muncul")',
    'rule("19a - Teleportasi Jongkok: Pengatur masukan terpisah dari Menu Arcade")': 'rule("19a - Teleportasi Jongkok: Pengatur masukan terpisah dari Menu Arkade")',
    '"Tunda satu frame agar handler menyelesaikan perintah sebelum dispatcher diaktifkan kembali."': '"Tunda satu bingkai agar pengendali menyelesaikan perintah sebelum pengatur masukan diaktifkan kembali."',
    '"Biarkan frame Interact selesai sebelum mengganti render kamera."': '"Biarkan satu bingkai Interact selesai sebelum mengganti tampilan kamera."',
    '"Ganti kamera langsung tanpa Stop Camera agar perpindahan target tidak berkedip satu frame."': '"Ganti kamera langsung tanpa Stop Camera agar perpindahan target tidak berkedip satu bingkai."',
    '"Gunakan jeda satu frame yang sama saat mulai menonton dari orang pertama."': '"Gunakan jeda satu bingkai yang sama saat mulai menonton dari orang pertama."',
}
for old, new in source_replacements.items():
    if old in source:
        source = source.replace(old, new)
SOURCE.write_text(source, encoding="utf-8")

VERSION.write_text("0.6.1\n", encoding="utf-8")
for path in (README, PROJECT, TESTDOC, VALIDATION, VALIDATOR):
    path.write_text(path.read_text(encoding="utf-8").replace("0.6.0", "0.6.1"), encoding="utf-8")

validator = VALIDATOR.read_text(encoding="utf-8")
foreign_sets = '''FOREIGN_IDENTIFIER_WORDS = {
    "leader", "voto", "voti", "numero", "max", "pari", "en", "th",
}

FOREIGN_RULE_OR_COMMENT_WORDS = {
    "respawn", "spawn", "full", "arcade", "vote", "leader", "roulette",
    "frame", "handler", "dispatcher", "client", "cache", "render",
}

'''
if "FOREIGN_IDENTIFIER_WORDS" not in validator:
    validator = validator.replace("ITALIAN_WORDS = {\n", foreign_sets + "ITALIAN_WORDS = {\n", 1)

old = '''            hits = set(identifier_tokens(name)) & ITALIAN_WORDS
            checks.require(
                not hits,
                f"identificatore {table_name} non indonesiano {name!r}: {sorted(hits)}",
            )
'''
new = '''            tokens = set(identifier_tokens(name))
            hits = tokens & (ITALIAN_WORDS | FOREIGN_IDENTIFIER_WORDS)
            checks.require(
                not hits,
                f"identificatore {table_name} non indonesiano {name!r}: {sorted(hits)}",
            )
'''
if old in validator:
    validator = validator.replace(old, new, 1)

old = '''    for rule in rules:
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
new = '''    for rule in rules:
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
if old in validator:
    validator = validator.replace(old, new, 1)

validator = validator.replace(
    '        "PosSpawnRoom", "NomorUrut",\n    }',
    '        "PosSpawnRoom", "NomorUrut", "NamaWarnaEN", "NamaHalamanEN",\n'
    '        "NamaWarnaTH", "NamaHalamanTH", "LeaderVoto", "MaxVoti", "PariVoti",\n'
    '        "IndeksVoto", "KursorVoto", "TargetVoto", "NumeroVoti", "GambarVoto",\n    }',
    1,
)
# The previous invariant intentionally pinned the old title; update it together
# with the source so the validator checks the Indonesian spelling.
validator = validator.replace("Pengatur masukan terpisah dari Menu Arcade", "Pengatur masukan terpisah dari Menu Arkade")
VALIDATOR.write_text(validator, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
marker = '\n\nif __name__ == "__main__":\n    unittest.main()'
extra = r'''

    def test_mixed_language_vote_identifier_is_rejected(self) -> None:
        mutated = self.source.replace("PemimpinSuara", "LeaderVoto", 1)
        self.assertNotEqual(mutated, self.source)
        global_names, player_names, subroutines = validator.declaration_tables(mutated)
        checks = validator.Checks()
        validator.check_source_structure(checks, mutated, self.rules(mutated), global_names, player_names, subroutines)
        self.assertTrue(any("LeaderVoto" in error and "non indonesiano" in error for error in checks.errors), checks.errors)

    def test_english_word_in_rule_title_is_rejected(self) -> None:
        mutated = self.source.replace(
            'rule("18 - Kebal: Pasang kembali status setelah muncul kembali")',
            'rule("18 - Kebal: Pasang kembali status setelah respawn")', 1,
        )
        self.assertNotEqual(mutated, self.source)
        global_names, player_names, subroutines = validator.declaration_tables(mutated)
        checks = validator.Checks()
        validator.check_source_structure(checks, mutated, self.rules(mutated), global_names, player_names, subroutines)
        self.assertTrue(any("respawn" in error and "nome regola" in error for error in checks.errors), checks.errors)
'''
if "test_mixed_language_vote_identifier_is_rejected" not in tests:
    tests = tests.replace(marker, extra + marker, 1)
TESTS.write_text(tests, encoding="utf-8")

for path in (README, PROJECT, TESTDOC, VALIDATION):
    text = path.read_text(encoding="utf-8").replace("24 unit test", "26 unit test").replace("Ran 24 tests", "Ran 26 tests")
    path.write_text(text, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
if "## Nomenclatura Bahasa Indonesia 0.6.1" not in project:
    project += '''\n\n## Nomenclatura Bahasa Indonesia 0.6.1\n\nLe dichiarazioni personalizzate non usano più i residui misti `Voto/Voti/Numero/Leader/Max/Pari` o i suffissi `EN/TH`: sono stati sostituiti da `PemimpinSuara`, `SuaraTerbanyak`, `SuaraSeri`, `IndeksHitungSuara`, `KursorPilihan`, `PemainDipilih`, `JumlahSuara`, `NamaWarnaInggris` e `NamaWarnaThai`. Anche `GambarVoto` è diventata `GambarPilihan`. Titoli regola e commenti personalizzati usano Bahasa Indonesia; le keyword e azioni native di Overwatch Workshop restano nella sintassi ufficiale inglese.\n'''
PROJECT.write_text(project, encoding="utf-8")

readme = README.read_text(encoding="utf-8")
if "Nomenclatura 0.6.1" not in readme:
    readme += '''\n\n### Nomenclatura 0.6.1\n\nVariabili, subroutine, titoli regola e commenti personalizzati sono controllati contro residui linguistici legacy. Restano in inglese soltanto keyword/azioni native Workshop e i contenuti HUD del ramo English.\n'''
README.write_text(readme, encoding="utf-8")

validation = VALIDATION.read_text(encoding="utf-8")
validation = re.sub(
    r"(Blob Git del sorgente Workshop validato:\s*```text\s*)[0-9a-f]{40}(\s*```)",
    rf"\g<1>{blob_sha(SOURCE)}\g<2>", validation, count=1,
)
validation = validation.replace("24 unit test", "26 unit test").replace("Ran 24 tests", "Ran 26 tests")
VALIDATION.write_text(validation, encoding="utf-8")
