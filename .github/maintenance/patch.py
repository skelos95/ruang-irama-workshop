from __future__ import annotations

from pathlib import Path
import subprocess

# Reuse the complete palette/name-color transformation from the previous commit.
previous = subprocess.run(
    ["git", "show", "HEAD^:.github/maintenance/patch.py"],
    check=True,
    capture_output=True,
    text=True,
).stdout
exec(compile(previous, "previous-maintenance-patch.py", "exec"), {})

validator = Path("tools/validate_workshop.py")
text = validator.read_text(encoding="utf-8")
text = text.replace('checks.equal(len(colors), 20, "numero di colori")', 'checks.equal(len(colors), 32, "numero di colori")')
text = text.replace('"colori indonesiani": ("Global.NamaWarna", 20, False)', '"colori indonesiani": ("Global.NamaWarna", 32, False)')
text = text.replace('"colori inglesi": ("Global.NamaWarnaEN", 20, False)', '"colori inglesi": ("Global.NamaWarnaEN", 32, False)')
text = text.replace('"colori thailandesi": ("Global.NamaWarnaTH", 20, True)', '"colori thailandesi": ("Global.NamaWarnaTH", 32, True)')
validator.write_text(text, encoding="utf-8")
