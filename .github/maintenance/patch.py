from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Reuse the complete, already test-passing 0.6.2 patch from the previous commit.
previous = subprocess.check_output(
    ["git", "show", "a971a57693d46980aea4fa7d823b3065b7bcf193:.github/maintenance/patch.py"],
    cwd=ROOT,
    text=True,
)
exec(
    compile(previous, "team_switch_0_6_2_validated.py", "exec"),
    {"__name__": "__main__", "__file__": str(ROOT / ".github/maintenance/patch.py")},
)

# The generated cleanup rule contained one tab-only blank line. Normalize trailing
# whitespace without changing Workshop statements or layout semantics.
source_path = ROOT / "workshop/ruang_irama.workshop"
text = source_path.read_text(encoding="utf-8")
ends_with_newline = text.endswith("\n")
text = "\n".join(line.rstrip() for line in text.splitlines())
if ends_with_newline:
    text += "\n"
source_path.write_text(text, encoding="utf-8")
