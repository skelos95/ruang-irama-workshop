from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

# Reuse the complete, already unit-tested migration from the parent commit.
previous = subprocess.check_output(
    ["git", "show", "HEAD^:.github/maintenance/patch.py"],
    text=True,
    encoding="utf-8",
)
namespace = {"__file__": __file__, "__name__": "__maintenance_previous__"}
exec(compile(previous, ".github/maintenance/patch.previous.py", "exec"), namespace)

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
PROJECT = ROOT / "docs" / "PROGETTO.md"
VALIDATION = ROOT / "docs" / "VALIDAZIONE.md"

# Project naming convention: keep custom identifiers in Bahasa Indonesia.
source = SOURCE.read_text(encoding="utf-8")
if "AggiornaVoti" not in source:
    raise RuntimeError("vote tally identifier not found")
source = source.replace("AggiornaVoti", "HitungPilihan")
SOURCE.write_text(source, encoding="utf-8")

validator = VALIDATOR.read_text(encoding="utf-8")
validator = validator.replace("AggiornaVoti", "HitungPilihan")
old_scope = '        after_luck = mask_strings(menu_interact[luck_start:])\n'
new_scope = (
    '        after_luck = mask_strings(menu_interact[luck_start:])\n'
    '        vote_branch_at = after_luck.find("Event Player.KursorVoto %=")\n'
    '        luck_only = after_luck[:vote_branch_at] if vote_branch_at >= 0 else after_luck\n'
)
if validator.count(old_scope) != 1:
    raise RuntimeError(f"expected one Nasib after_luck scope, found {validator.count(old_scope)}")
validator = validator.replace(old_scope, new_scope, 1)
old_redraw = '            "Call Subroutine(GambarMenu);" not in after_luck,\n'
new_redraw = '            "Call Subroutine(GambarMenu);" not in luck_only,\n'
if validator.count(old_redraw) != 1:
    raise RuntimeError(f"expected one Nasib redraw assertion, found {validator.count(old_redraw)}")
validator = validator.replace(old_redraw, new_redraw, 1)
VALIDATOR.write_text(validator, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8").replace("AggiornaVoti", "HitungPilihan")
PROJECT.write_text(project, encoding="utf-8")

# The source changed after the parent migration calculated its documented blob.
data = SOURCE.read_bytes().replace(b"\r\n", b"\n")
payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
blob = hashlib.sha1(payload).hexdigest()
validation = VALIDATION.read_text(encoding="utf-8").replace("AggiornaVoti", "HitungPilihan")
validation, count = re.subn(
    r"(?s)(Blob Git del sorgente Workshop validato:\s*```text\s*)[0-9a-f]{40}(\s*```)",
    rf"\g<1>{blob}\g<2>",
    validation,
    count=1,
)
if count != 1:
    raise RuntimeError("validation blob not found")
VALIDATION.write_text(validation, encoding="utf-8")
