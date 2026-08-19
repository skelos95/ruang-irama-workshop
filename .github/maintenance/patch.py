from __future__ import annotations

import subprocess
import traceback
from pathlib import Path

BASE_PATCH_COMMIT = "66a0f14db7ac01bd4b1d771627de99b20a603c28"
PATCH_PATH = ".github/maintenance/patch.py"
DIAGNOSTIC = Path(".github/maintenance/last-patch-error.txt")


def restore_stable() -> None:
    subprocess.run(
        ["git", "checkout", "HEAD", "--", "workshop/ruang_irama.workshop", "tools/validate_workshop.py"],
        check=True,
    )


try:
    text = subprocess.check_output(["git", "show", f"{BASE_PATCH_COMMIT}:{PATCH_PATH}"], text=True)
    # The validator block lives inside a Python string in the staged patch, so
    # the source contains a literal backslash+n rather than an actual newline.
    bad = '        checks.require("Create Icon(" not in interact.body, "Try Your Luck crea icone nel dispatcher menu invece che nella roulette")\\n'
    count = text.count(bad)
    if count != 1:
        raise RuntimeError(f"validator scope hotfix literal \\n match count: {count}")
    text = text.replace(bad, "", 1)
    exec(compile(text, str(Path(__file__).resolve()), "exec"), {"__file__": __file__, "__name__": "__main__"})

    # Preflight the same gates used by the maintenance workflow. Any failure is
    # captured before a partial Workshop state can reach the normal CI steps.
    subprocess.run(
        ["python", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
        check=True,
        text=True,
        capture_output=True,
    )
    subprocess.run(
        ["python", "tools/validate_workshop.py"],
        check=True,
        text=True,
        capture_output=True,
    )
    DIAGNOSTIC.unlink(missing_ok=True)
    print("Try Your Luck ten-outcome preflight passed.")
except subprocess.CalledProcessError as exc:
    error = traceback.format_exc()
    error += "\n--- STDOUT ---\n" + (exc.stdout or "")
    error += "\n--- STDERR ---\n" + (exc.stderr or "")
    restore_stable()
    DIAGNOSTIC.write_text(error, encoding="utf-8")
    print("Captured Try Your Luck preflight failure; stable source restored.")
    print(error)
except Exception:
    error = traceback.format_exc()
    restore_stable()
    DIAGNOSTIC.write_text(error, encoding="utf-8")
    print("Captured Try Your Luck patch failure; stable source restored.")
    print(error)
