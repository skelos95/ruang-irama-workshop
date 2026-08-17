from __future__ import annotations

import subprocess

BASE_PATCH_COMMIT = "665a09095085e7b18e5b6f6353b9f36113fa749f"
patch = subprocess.check_output(
    ["git", "show", f"{BASE_PATCH_COMMIT}:.github/maintenance/patch.py"],
    text=True,
)
patch = patch.replace(
    '"Buang satu-satunya HUD Arkade lama sebelum membuat halaman baru; cache tidak pernah boleh tumbuh melebihi satu elemen."',
    '"Buang satu-satunya HUD Arkade lama sebelum membuat halaman baru; simpanan tidak pernah boleh tumbuh melebihi satu elemen."',
)
exec(compile(patch, ".github/maintenance/patch.py", "exec"))
