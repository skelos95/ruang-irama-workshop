from __future__ import annotations

import subprocess
from pathlib import Path

PATCH_PATH = ".github/maintenance/patch.py"
FEATURE_PATCH_COMMIT = "9eef15c412d7dfa9d5f0dbe0f4b7e0ff9cc266e9"
SOURCE_PATH = Path("workshop/ruang_irama.workshop")
VALIDATOR_PATH = Path("tools/validate_workshop.py")
TESTS_PATH = Path("tests/test_validate_workshop.py")
DIAGNOSTIC_PATH = Path("PATCH_DIAGNOSTIC.txt")


def load_patch() -> str:
    return subprocess.run(
        ["git", "show", f"{FEATURE_PATCH_COMMIT}:{PATCH_PATH}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


source_before = SOURCE_PATH.read_text(encoding="utf-8")
validator_before = VALIDATOR_PATH.read_text(encoding="utf-8")
tests_before = TESTS_PATH.read_text(encoding="utf-8")

code = load_patch()
exec(compile(code, PATCH_PATH, "exec"), {"__name__": "__main__", "__file__": PATCH_PATH})

result = subprocess.run(
    ["python", "tools/validate_workshop.py"],
    capture_output=True,
    text=True,
)
DIAGNOSTIC_PATH.write_text(
    f"returncode={result.returncode}\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}",
    encoding="utf-8",
)

# Restore accepted sources so the workflow can commit only the diagnostic.
SOURCE_PATH.write_text(source_before, encoding="utf-8")
VALIDATOR_PATH.write_text(validator_before, encoding="utf-8")
TESTS_PATH.write_text(tests_before, encoding="utf-8")
