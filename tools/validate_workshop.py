#!/usr/bin/env python3
"""Compatibility entry point for Workshop validation.

Workshop semantics live in validate_workshop_core.py. Release-state metadata is
selected separately so promoting a tested release does not require changing the
semantic gate.
"""

from __future__ import annotations

try:
    from tools import validate_workshop_core as _core
    from tools.validate_release_metadata import validate_live_ready_metadata
except ImportError:  # Direct execution: python tools/validate_workshop.py
    import validate_workshop_core as _core
    from validate_release_metadata import validate_live_ready_metadata

_pending_metadata_validator = _core.validate_metadata


def validate_metadata(checks, root) -> None:
    if not (root / "LIVE_READY").is_file():
        _pending_metadata_validator(checks, root)
        return
    validate_live_ready_metadata(
        checks,
        root,
        version=_core.CURRENT_VERSION,
        core_docs=_core.CORE_DOCS,
        current_release_claims=_core.current_release_claims,
        obsolete_patterns=_core.OBSOLETE_CURRENT_TEXT_PATTERNS,
        allowed_workflows=_core.ALLOWED_WORKFLOWS,
    )


_core.validate_metadata = validate_metadata

# Preserve the public API used by the existing mutation suite.
for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)

# Re-export the patched dispatcher rather than the original core function.
globals()["validate_metadata"] = validate_metadata


if __name__ == "__main__":
    raise SystemExit(_core.main())
