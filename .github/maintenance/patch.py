from __future__ import annotations

import subprocess

BASE_PATCH_COMMIT = "264fcc882a77b3688d92ff81b13cfe505cbf76f5"
payload = subprocess.check_output(
    ["git", "show", f"{BASE_PATCH_COMMIT}:.github/maintenance/patch.py"],
    text=True,
)
payload = payload.replace(
    '    joined = "\\n".join(mask_strings(rule.body) for rule in managers)',
    '    joined = "\\\\n".join(mask_strings(rule.body) for rule in managers)',
    1,
)
if 'joined = "\\\\n".join' not in payload:
    raise RuntimeError("global-first newline escape patch did not apply")
exec(compile(payload, ".github/maintenance/global_first_070.py", "exec"))
