from __future__ import annotations

from pathlib import Path
import subprocess

# Re-run the complete audit/optimization patch from the first audit input.
previous = subprocess.run(
    ["git", "show", "HEAD^:.github/maintenance/patch.py"],
    check=True,
    capture_output=True,
    text=True,
).stdout
exec(compile(previous, "previous-maintenance-patch.py", "exec"), {})

validator = Path("tools/validate_workshop.py")
text = validator.read_text(encoding="utf-8")


def replace_check_by_label(label: str, replacement: str) -> None:
    """Replace the checks.require(...) whose message contains label."""
    global text
    label_at = text.find(label)
    if label_at < 0:
        raise SystemExit(f"validator label not found: {label}")
    start = text.rfind("    checks.require(", 0, label_at)
    if start < 0:
        raise SystemExit(f"checks.require start not found for: {label}")
    open_at = text.find("(", start)
    depth = 1
    in_string = False
    escaped = False
    end = -1
    for i in range(open_at + 1, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0 or not (start < label_at < end):
        raise SystemExit(f"checks.require block not resolved for: {label}")
    text = text[:start] + replacement + text[end:]


replace_check_by_label(
    "refresh Crouch non a 0,10 s",
    '''    checks.require(\n        "Wait(0.200, Abort When False);" in source,\n        "refresh Crouch non a 0,20 s",\n    )''',
)
replace_check_by_label(
    "diagnostica non ancorata all'ultimo player della lista sinistra",
    '''    checks.require(\n        "Event Player.UrutanHUD == Global.SlotHUDTerakhir" in source,\n        "diagnostica non ancorata alla cache dell'ultimo player della lista sinistra",\n    )''',
)

validator.write_text(text, encoding="utf-8")
