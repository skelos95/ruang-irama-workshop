from __future__ import annotations

import subprocess

BASE_PATCH_COMMIT = "798c33aecba4c0bd121a008f99afa3b2631fbe7f"
payload = subprocess.check_output(
    ["git", "show", f"{BASE_PATCH_COMMIT}:.github/maintenance/patch.py"],
    text=True,
)
payload = payload.replace(
    '    text2, count = pattern.subn(block.rstrip() + "\\n\\n", text, count=1)',
    '    text2, count = pattern.subn(lambda _match: block.rstrip() + "\\n\\n", text, count=1)',
    1,
)
if 'pattern.subn(lambda _match:' not in payload:
    raise RuntimeError("escape-safe test replacement fix did not apply")
exec(compile(payload, ".github/maintenance/global_first_070_tests.py", "exec"))
