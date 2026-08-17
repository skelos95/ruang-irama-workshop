from __future__ import annotations

import subprocess

BASE_PATCH_COMMIT = "20b90f965b82b89e31da7aad40e0cd8c27394242"
payload = subprocess.check_output(
    ["git", "show", f"{BASE_PATCH_COMMIT}:.github/maintenance/patch.py"],
    text=True,
)
payload = payload.replace(
    '"11 - Menu: Muat ulang kembali ke menu utama"',
    '"11 - Menu: Isi ulang kembali dari submenu ke menu utama"',
    1,
)
if '11 - Menu: Isi ulang kembali dari submenu ke menu utama' not in payload:
    raise RuntimeError("Reload title fix did not apply")
exec(compile(payload, ".github/maintenance/menu_fix_candidate.py", "exec"))
