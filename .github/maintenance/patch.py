from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
VALIDATION = ROOT / "docs" / "VALIDAZIONE.md"

# Reuse the already-tested feature patch from the parent commit. This wrapper
# only extends its validation contract; it does not duplicate the large source
# transformation and therefore cannot silently diverge from the first attempt.
parent_patch = subprocess.check_output(
    ["git", "show", "HEAD^:.github/maintenance/patch.py"],
    text=True,
    encoding="utf-8",
)
exec(compile(parent_patch, "parent-maintenance-patch.py", "exec"), {"__name__": "__main__"})


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one occurrence, found {count}")
    return text.replace(old, new, 1)


# The old validator deliberately counted every In-World Text as Crouch-only.
# Menu 10 adds exactly one public card text, while the two Crouch texts stay
# unchanged and are still checked inside the Crouch start rule below.
validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_once(
    validator,
    '        len(call_texts(source, "Create In-World Text")), 2,\n        "testi mondo Crouch",',
    '        len(call_texts(source, "Create In-World Text")), 3,\n        "due testi mondo Crouch più una carta Nasib",',
    "In-World Text count for luck card",
)

# The two generic setting-feedback rings remain exactly one per subroutine.
# Menu 10 legitimately adds one ring on creation and one on resolution.
validator = replace_once(
    validator,
    '    checks.equal(len(effect_calls), 2, "feedback: devono esistere solo i due Ring RGB delle subroutine")',
    '    checks.equal(len(effect_calls), 4, "feedback: due Ring RGB impostazioni più due Ring RGB carta Nasib")',
    "Ring Explosion count for luck card",
)

# Add explicit invariants so increasing the global counts does not weaken the
# gate: exactly one owner-only activation rule and exactly one public card text.
needle = '''    full_hp = [rule for rule in rules if rule.name.startswith("18d - Kebal:")]
    checks.equal(len(full_hp), 1, "regola FULL HP per Spawn Room")
    if full_hp:
        checks.require(
            "Is In Spawn Room(Event Player) == False;" not in mask_strings(full_hp[0].body),
            "FULL HP non deve essere escluso dalla Spawn Room",
        )
'''
replacement = needle + '''
    luck = [
        rule for rule in rules
        if code_contains(
            rule.body,
            "Event Player.KartuNasibAktif == True;",
            "Is Button Held(Event Player, Button(Primary Fire)) == True;",
            "Angle Between Vectors(",
            "Is In Line of Sight(",
            "Random Integer(0, 1)",
            "Set Player Health(Event Player, Max Health(Event Player));",
            "Kill(Event Player, Null);",
        )
    ]
    checks.equal(len(luck), 1, "Nasib: una sola regola di risoluzione proprietario-only")
    if luck:
        checks.equal(
            len(call_texts(luck[0].body, "Play Effect")),
            1,
            "Nasib: un solo Ring alla risoluzione",
        )
    card_texts = [
        call for call in call_texts(source, "Create In-World Text")
        if "KartuNasib" in call and "All Players(All Teams)" in call
    ]
    checks.equal(len(card_texts), 1, "Nasib: una sola carta pubblica")
    checks.require(
        "Chase Player Variable Over Time(Event Player, PosisiKartuNasib" in mask_strings(source),
        "Nasib: animazione di emersione dal terreno assente",
    )
    checks.require(
        "Event Player.KursorKebal = Event Player.ModeKebal;" not in mask_strings(
            next(rule.body for rule in rules if rule.name.startswith("10 - Menu:"))
        ),
        "Kebal: il rifiuto 1 HP nello Spawn Room non deve spostare il cursore",
    )
'''
validator = replace_once(
    validator,
    needle,
    replacement,
    "strict Menu 10 validator invariants",
)
VALIDATOR.write_text(validator, encoding="utf-8")

# Keep the human-readable validation report aligned with the generated source.
report = VALIDATION.read_text(encoding="utf-8")
report = report.replace("**10 menu Arcade** (`0..9`)", "**11 menu Arcade** (`0..10`)")
report = report.replace("apertura e navigazione di tutti gli 8 menu", "apertura e navigazione di tutti gli 11 menu")
report = report.replace(
    "- Menu 7 Player Icon;\n",
    "- Menu 7 Player Icon;\n- Menu 10 Try Your Luck: carta pubblica, attivazione solo proprietario, esito 50/50;\n",
)
report = report.replace(
    "- Hero Voice;\n",
    "- Hero Voice;\n- Try Your Luck con due giocatori: il non proprietario non deve poter attivare la carta;\n",
)

data = SOURCE.read_bytes().replace(b"\r\n", b"\n")
payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
blob_sha = hashlib.sha1(payload).hexdigest()
report, count = re.subn(
    r"(Blob Git del sorgente Workshop validato:\s*```text\s*)[0-9a-f]{40}",
    lambda match: match.group(1) + blob_sha,
    report,
    count=1,
)
if count != 1:
    raise RuntimeError("validation report: Workshop blob marker not found exactly once")
VALIDATION.write_text(report, encoding="utf-8")
