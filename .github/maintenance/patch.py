from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "tools" / "validate_workshop.py"

# Reuse the complete 0.6.5 maintenance patch from the earlier commit, then
# align the one remaining legacy validator invariant with speed-only luck.
original = subprocess.run(
    ["git", "show", "a431d202263d109f9b64ea88976a7edc559071b6:.github/maintenance/patch.py"],
    cwd=ROOT,
    check=True,
    capture_output=True,
    text=True,
).stdout
exec(
    compile(original, ".github/maintenance/patch.py@a431d202", "exec"),
    {
        "__name__": "__main__",
        "__file__": str(ROOT / ".github" / "maintenance" / "patch.py"),
    },
)

validator = VALIDATOR.read_text(encoding="utf-8")
old = '''    death_reset = [rule for rule in rules if rule.name.startswith("18f - Nasib:")]
    checks.equal(len(death_reset), 1, "Nasib: una sola regola reset alla morte")
    if death_reset:
        checks.require(
            code_contains(
                death_reset[0].body,
                "Event Player.KartuNasibAktif = False;",
                "Event Player.KartuNasibMerah = False;",
                "Event Player.PutaranKartuNasib = 0;",
                "Event Player.JedaKartuNasib = 0;",
                "Destroy In-World Text(Event Player.TeksKartuNasib);",
                "Destroy In-World Text(Event Player.TeksKartuNasibKanan);",
                "Destroy Icon(Event Player.IkonKartuNasib);",
                "Destroy Icon(Event Player.IkonKartuNasibHijau);",
                "Event Player.IkonKartuNasib = Null;",
                "Event Player.IkonKartuNasibHijau = Null;",
                "Stop Forcing Player Position(Event Player);",
                "Set Move Speed(Event Player, 100);",
                "Set Knockback Received(Event Player, 100);",
                "Destroy Effect(Event Player.EfekNasibCahaya);",
                "Destroy Effect(Event Player.EfekNasibLingkaran);",
            ),
            "Nasib: morte prima della fine non resetta completamente la carta",
        )
'''
new = '''    death_reset = [rule for rule in rules if rule.name.startswith("18f - Nasib:")]
    checks.equal(len(death_reset), 1, "Nasib: una sola regola reset alla morte")
    if death_reset:
        death_code = mask_strings(death_reset[0].body)
        for token in (
            "Event Player.KartuNasibAktif = False;",
            "Event Player.KartuNasibMerah = False;",
            "Event Player.PutaranKartuNasib = 0;",
            "Event Player.JedaKartuNasib = 0;",
            "Destroy In-World Text(Event Player.TeksKartuNasib);",
            "Destroy In-World Text(Event Player.TeksKartuNasibKanan);",
            "Destroy Icon(Event Player.IkonKartuNasib);",
            "Destroy Icon(Event Player.IkonKartuNasibHijau);",
            "Event Player.IkonKartuNasib = Null;",
            "Event Player.IkonKartuNasibHijau = Null;",
            "Set Move Speed(Event Player, 100);",
            "Destroy Effect(Event Player.EfekNasibCahaya);",
            "Destroy Effect(Event Player.EfekNasibLingkaran);",
            "Event Player.ModeKebal = Event Player.ModeKebalTerakhir;",
            "Event Player.KursorKebal = Event Player.ModeKebalTerakhir;",
        ):
            checks.require(token in death_code, f"Nasib: reset morte incompleto: {token}")
        checks.require(
            "Stop Forcing Player Position(Event Player);" not in death_code,
            "Nasib: cleanup morte contiene ancora forcing posizione",
        )
        checks.require(
            "Set Knockback Received(Event Player, 100);" not in death_code,
            "Nasib: cleanup morte ripristina ancora un knockback non modificato dalla roulette",
        )
'''
if validator.count(old) != 1:
    raise RuntimeError(f"legacy death-reset validator block count={validator.count(old)}")
VALIDATOR.write_text(validator.replace(old, new, 1), encoding="utf-8")
print("Aligned Try Your Luck death-reset validator with speed-only behavior")
