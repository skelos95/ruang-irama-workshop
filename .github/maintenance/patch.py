from __future__ import annotations

import subprocess

# Reuse the complete previous maintenance patch, but fix the one overly strict
# replacement in rule 13. The target format appears twice (target + self HUD);
# only the first occurrence belongs to the inspected target privacy path.
patch = subprocess.check_output(
    ["git", "show", "HEAD^:.github/maintenance/patch.py"], text=True
)
old = '''rule13 = replace_once(
    rule13,
    'Custom String("{0} {1} | {2}",',
    'Custom String("{0}{1} | {2}",',
    "privacy compact inspection format",
)'''
new = '''old_privacy_format = 'Custom String("{0} {1} | {2}",'
if rule13.count(old_privacy_format) < 1:
    raise SystemExit("privacy compact inspection format: target format not found")
rule13 = rule13.replace(old_privacy_format, 'Custom String("{0}{1} | {2}",', 1)'''
if old not in patch:
    raise SystemExit("failed to locate strict privacy replacement in previous patch")
patch = patch.replace(old, new, 1)
exec(compile(patch, ".github/maintenance/patch.py", "exec"))
