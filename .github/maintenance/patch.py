from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
TESTS = ROOT / "tests" / "test_validate_workshop.py"
VERSION = ROOT / "VERSION"
README = ROOT / "README.md"
PROJECT = ROOT / "docs" / "PROGETTO.md"
TESTDOC = ROOT / "docs" / "TEST.md"
VALIDATION = ROOT / "docs" / "VALIDAZIONE.md"


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    return hashlib.sha1(payload).hexdigest()


# Workshop client rejects the previous identifier used by global slot 47.
# Keep the same slot and behavior, only use a short conservative ASCII name.
source = SOURCE.read_text(encoding="utf-8")
old_count = source.count("IndeksHitungSuara")
if old_count < 2:
    raise RuntimeError(f"expected slot 47 plus runtime references, found {old_count}")
source = source.replace("IndeksHitungSuara", "IndeksVote")
if "\t\t47: IndeksVote\n" not in source:
    raise RuntimeError("global slot 47 was not renamed to IndeksVote")
if "IndeksHitungSuara" in source:
    raise RuntimeError("legacy invalid slot 47 name still present")
SOURCE.write_text(source, encoding="utf-8")

# Validator 0.6.3: explicitly lock the client-safe name for slot 47.
validator = VALIDATOR.read_text(encoding="utf-8")
validator = validator.replace("versione 0.6.2", "versione 0.6.3")
validator = validator.replace('CURRENT_VERSION = "0.6.2"', 'CURRENT_VERSION = "0.6.3"')
needle = '''def check_vote_menu(checks: Checks, source: str, rules: list[Rule], subroutines: set[str]) -> None:
    clean = mask_strings(source)
'''
replacement = '''def check_vote_menu(checks: Checks, source: str, rules: list[Rule], subroutines: set[str]) -> None:
    clean = mask_strings(source)
    variables = section_body(source, "variables")
    checks.require(
        re.search(r"(?m)^\\s*47\\s*:\\s*IndeksVote\\s*$", variables) is not None,
        "Vote: global slot 47 deve usare il nome client-safe IndeksVote",
    )
    checks.require("IndeksHitungSuara" not in source, "Vote: nome legacy non valido dello slot 47 ancora presente")
'''
if needle not in validator:
    raise RuntimeError("check_vote_menu insertion point missing")
validator = validator.replace(needle, replacement, 1)
VALIDATOR.write_text(validator, encoding="utf-8")

# Add a regression test so the invalid identifier cannot return.
tests = TESTS.read_text(encoding="utf-8")
tests = tests.replace("0.6.2", "0.6.3")
marker = '\n\nif __name__ == "__main__":\n    unittest.main()'
extra = r'''

    def test_vote_global_slot_47_name_must_stay_client_safe(self) -> None:
        mutated = self.source.replace("47: IndeksVote", "47: IndeksHitungSuara", 1)
        self.assertNotEqual(mutated, self.source)
        _, _, subroutines = validator.declaration_tables(mutated)
        checks = validator.Checks()
        validator.check_vote_menu(checks, mutated, self.rules(mutated), subroutines)
        self.assertTrue(any("slot 47" in error for error in checks.errors), checks.errors)
'''
if "test_vote_global_slot_47_name_must_stay_client_safe" not in tests:
    if marker not in tests:
        raise RuntimeError("unit-test insertion marker missing")
    tests = tests.replace(marker, extra + marker, 1)
TESTS.write_text(tests, encoding="utf-8")

VERSION.write_text("0.6.3\n", encoding="utf-8")

# Keep technical docs synchronized. Do not alter gameplay semantics.
for path in (README, PROJECT, TESTDOC, VALIDATION):
    text = path.read_text(encoding="utf-8")
    text = text.replace("0.6.2", "0.6.3")
    text = text.replace("28 unit test", "29 unit test").replace("Ran 28 tests", "Ran 29 tests")
    path.write_text(text, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
if "## Hotfix import Workshop 0.6.3" not in project:
    project += '''\n\n## Hotfix import Workshop 0.6.3\n\nLa variabile globale di appoggio del conteggio voti resta nello slot `47`, ma il nome è stato abbreviato da `IndeksHitungSuara` a `IndeksVote`. Il cambio è esclusivamente nominale: tutti i `For Global Variable` e gli accessi al tally usano lo stesso slot e mantengono identica la logica voto. Il validatore blocca il ritorno del vecchio identificatore perché il client Overwatch lo rifiuta in fase di importazione con `Global variable '47' has an invalid name`.\n'''
PROJECT.write_text(project, encoding="utf-8")

testdoc = TESTDOC.read_text(encoding="utf-8")
if "slot globale 47" not in testdoc.lower():
    testdoc += '''\n\n## Import Workshop - slot globale 47\n\n- Incollare l'intero sorgente nel Workshop: non deve comparire `Global variable '47' has an invalid name`.\n- La tabella `variables` deve mostrare `47: IndeksVote`.\n- Aprire Menu 11 e verificare che conteggio, cambio voto e cleanup su cambio squadra continuino a funzionare senza differenze rispetto alla 0.6.2.\n'''
TESTDOC.write_text(testdoc, encoding="utf-8")

# Source blob changed because the identifier is part of the Workshop text.
validation = VALIDATION.read_text(encoding="utf-8")
blob = git_blob_sha(SOURCE)
validation = re.sub(
    r"(Blob Git del sorgente Workshop validato:\s*```text\s*)[0-9a-f]{40}(\s*```)",
    rf"\g<1>{blob}\g<2>",
    validation,
    count=1,
)
if "IndeksVote" not in validation:
    validation += '''\n\n### Hotfix import 0.6.3\n\n- lo slot globale `47` è dichiarato come `IndeksVote`;\n- `IndeksHitungSuara` è vietato dal validatore;\n- il cambio è nominale e non modifica il tally delle votazioni.\n'''
VALIDATION.write_text(validation, encoding="utf-8")
