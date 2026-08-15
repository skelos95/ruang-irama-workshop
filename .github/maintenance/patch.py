from __future__ import annotations

import subprocess

OBSOLETE_BRANCHES = (
    "agent/crouch-unkillable-voice",
    "__noop__",
)

for branch in OBSOLETE_BRANCHES:
    subprocess.run(
        ["git", "push", "origin", "--delete", branch],
        check=True,
    )
