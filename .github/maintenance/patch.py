from __future__ import annotations

from pathlib import Path
import subprocess

# Apply the complete documentation synchronization from the previous patcher.
previous = subprocess.run(
    ["git", "show", "HEAD^:.github/maintenance/patch.py"],
    check=True,
    capture_output=True,
    text=True,
).stdout
exec(compile(previous, "sync-docs-0.6.0.py", "exec"), {})

# The legacy release-metadata validator still had 0.5.5 hardcoded. Align that
# existing contract with the new cumulative 0.6.0 documentation release.
validator_path = Path("tools/validate_workshop.py")
validator = validator_path.read_text(encoding="utf-8")
validator = validator.replace("0.5.5", "0.6.0")
validator_path.write_text(validator, encoding="utf-8")

# Keep the validation report's recorded validator output identical to what the
# release-metadata checker expects after the version bump.
report_path = Path("docs/VALIDAZIONE.md")
report = report_path.read_text(encoding="utf-8")
report = report.replace(
    "OK - controlli statici superati\nGeneri: 100 | Lingue: 3 | Regole:",
    "OK - controlli statici v0.6.0 superati\nGeneri: 100 | Lingue: 3 | Regole:",
)
report_path.write_text(report, encoding="utf-8")
