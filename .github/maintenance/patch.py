from __future__ import annotations

from pathlib import Path
import subprocess

# Re-run the complete audit/optimization patch from the previous input commit.
previous = subprocess.run(
    ["git", "show", "HEAD^:.github/maintenance/patch.py"],
    check=True,
    capture_output=True,
    text=True,
).stdout
exec(compile(previous, "previous-maintenance-patch.py", "exec"), {})

validator = Path("tools/validate_workshop.py")
text = validator.read_text(encoding="utf-8")

# Update two legacy assertions that deliberately described the pre-audit design.
def replace_nearest_before(label: str, candidates: tuple[tuple[str, str], ...]) -> None:
    global text
    label_at = text.find(label)
    if label_at < 0:
        raise SystemExit(f"validator label not found: {label}")
    for old, new in candidates:
        old_at = text.rfind(old, max(0, label_at - 1800), label_at)
        if old_at >= 0:
            text = text[:old_at] + new + text[old_at + len(old):]
            return
    raise SystemExit(f"validator legacy expectation not found before: {label}")

replace_nearest_before(
    "refresh Crouch non a 0,10 s",
    (
        (r"0\.100", r"0\.200"),
        ("0.100", "0.200"),
    ),
)
text = text.replace("refresh Crouch non a 0,10 s", "refresh Crouch non a 0,20 s", 1)

replace_nearest_before(
    "diagnostica non ancorata all'ultimo player della lista sinistra",
    (
        (
            "Event Player == Last Of(Sorted Array(Global.PemainManusia, Player Variable(Current Array Element, UrutanHUD)))",
            "Event Player.UrutanHUD == Global.SlotHUDTerakhir",
        ),
        (
            "EventPlayer==LastOf(SortedArray(Global.PemainManusia,PlayerVariable(CurrentArrayElement,UrutanHUD)))",
            "EventPlayer.UrutanHUD==Global.SlotHUDTerakhir",
        ),
    ),
)

validator.write_text(text, encoding="utf-8")
