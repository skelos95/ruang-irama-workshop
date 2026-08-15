from __future__ import annotations

from pathlib import Path
import hashlib
import re

SOURCE = Path("workshop/ruang_irama.workshop")
VALIDATOR = Path("tools/validate_workshop.py")
README = Path("README.md")
PROJECT = Path("docs/PROGETTO.md")
TESTS = Path("docs/TEST.md")
REPORT = Path("docs/VALIDAZIONE.md")


def once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 occurrence, found {count}")
    return text.replace(old, new, 1)


src = SOURCE.read_text(encoding="utf-8")

old_apply = '''\t\tPlay Effect(All Players(All Teams), Good Explosion, Global.RGB, Position Of(Event Player) + Vector(0, 1, 0), 2.500);\n\t\tPlay Effect(Event Player, Buff Impact Sound, Color(White), Position Of(Event Player), 35);'''
ring_only = '''\t\tPlay Effect(All Players(All Teams), Ring Explosion, Global.RGB, Position Of(Event Player) + Vector(0, 1, 0), 3);'''
src = once(src, old_apply, ring_only, "EfekTerapkan ring-only")

old_restore = '''\t\tPlay Effect(All Players(All Teams), Ring Explosion, Global.RGB, Position Of(Event Player) + Vector(0, 1, 0), 3);\n\t\tPlay Effect(Event Player, Ring Explosion Sound, Color(White), Position Of(Event Player), 35);'''
src = once(src, old_restore, ring_only, "EfekPulihkan ring-only")

for forbidden in ("Good Explosion", "Buff Impact Sound", "Ring Explosion Sound"):
    if forbidden in src:
        raise SystemExit(f"forbidden audiovisual feedback still present: {forbidden}")

SOURCE.write_text(src, encoding="utf-8")

val = VALIDATOR.read_text(encoding="utf-8")

old_tokens = '''        "18: EfekTerapkan", "19: EfekPulihkan",\n        "Play Effect(All Players(All Teams), Good Explosion, Global.RGB",\n        "Play Effect(Event Player, Buff Impact Sound",\n        "Play Effect(All Players(All Teams), Ring Explosion, Global.RGB",\n        "Play Effect(Event Player, Ring Explosion Sound",'''
new_tokens = '''        "18: EfekTerapkan", "19: EfekPulihkan",\n        "Play Effect(All Players(All Teams), Ring Explosion, Global.RGB",'''
val = once(val, old_tokens, new_tokens, "validator feedback required tokens")

old_sound_guard = '''    checks.require(\n        "Play Effect(All Players(All Teams), Buff Impact Sound" not in clean\n        and "Play Effect(All Players(All Teams), Ring Explosion Sound" not in clean,\n        "gli effetti sonori devono essere personali, non globali",\n    )'''
new_sound_guard = '''    effect_calls = call_texts(source, "Play Effect")\n    checks.equal(len(effect_calls), 2, "feedback: devono esistere solo i due Ring RGB delle subroutine")\n    for index, call in enumerate(effect_calls, 1):\n        checks.require(\n            "Ring Explosion" in call\n            and "Global.RGB" in call\n            and "All Players(All Teams)" in call\n            and "Sound" not in call,\n            f"feedback #{index}: deve essere esclusivamente Ring Explosion RGB visivo",\n        )\n    for forbidden in ("Good Explosion", "Buff Impact Sound", "Ring Explosion Sound"):\n        checks.require(forbidden not in clean, f"feedback vietato ancora presente: {forbidden}")'''
val = once(val, old_sound_guard, new_sound_guard, "validator no-audio/ring-only guard")

val = once(
    val,
    'checks.require(code_contains(apply[0].body, "Good Explosion, Global.RGB"), "effetto applicazione non usa RGB")',
    'checks.require(code_contains(apply[0].body, "Ring Explosion, Global.RGB"), "effetto applicazione non usa Ring RGB")',
    "RGB apply must use Ring",
)
val = once(
    val,
    'checks.require(code_contains(restore[0].body, "Ring Explosion, Global.RGB"), "effetto ripristino non usa RGB")',
    'checks.require(code_contains(restore[0].body, "Ring Explosion, Global.RGB"), "effetto ripristino non usa Ring RGB")',
    "RGB restore must use Ring",
)

# Make the invariant explicit per semantic subroutine as well as globally.
anchor = '''    checks.equal(len(apply), 1, "subroutine EfekTerapkan")\n    checks.equal(len(restore), 1, "subroutine EfekPulihkan")'''
replacement = anchor + '''\n    for label, matches in (("EfekTerapkan", apply), ("EfekPulihkan", restore)):\n        if matches:\n            calls = call_texts(matches[0].body, "Play Effect")\n            checks.equal(len(calls), 1, f"{label}: un solo effetto visivo")\n            if calls:\n                checks.require(\n                    "Ring Explosion" in calls[0]\n                    and "Global.RGB" in calls[0]\n                    and "Sound" not in calls[0],\n                    f"{label}: effetto diverso da Ring RGB visivo",\n                )'''
val = once(val, anchor, replacement, "validator per-subroutine ring guard")

VALIDATOR.write_text(val, encoding="utf-8")

readme = README.read_text(encoding="utf-8")
note = "\n**Feedback visivo:** i feedback delle impostazioni non riproducono più suoni. `EfekTerapkan` e `EfekPulihkan` usano esclusivamente `Ring Explosion` con `Global.RGB`.\n"
if note.strip() not in readme:
    readme += note
README.write_text(readme, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
section = "\n\n### Feedback solo visivo\n\nTutti i feedback audio delle impostazioni sono rimossi. Le subroutine `EfekTerapkan` e `EfekPulihkan` mantengono una sola chiamata `Play Effect` ciascuna: `Ring Explosion`, visibile a tutti e colorata con `Global.RGB`. `Good Explosion`, `Buff Impact Sound` e `Ring Explosion Sound` non devono comparire nel sorgente. La feature Hero Voice resta indipendente perché modifica le voice line del giocatore e non è un effetto di feedback.\n"
if "### Feedback solo visivo" not in project:
    project += section
PROJECT.write_text(project, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
for line in (
    "- **Feedback senza audio:** applicare e ripristinare più impostazioni del Menu Arcade; non deve essere riprodotto alcun effetto sonoro di conferma.\n",
    "- **Ring RGB unico:** applicazione e ripristino devono mostrare solo `Ring Explosion` RGB sul giocatore; nessuna Good Explosion o altra forma visiva di feedback.\n",
):
    if line.strip() not in tests:
        tests += "\n" + line
TESTS.write_text(tests, encoding="utf-8")

report = REPORT.read_text(encoding="utf-8")
report_note = "\n- Feedback impostazioni: zero effetti audio; entrambe le subroutine usano esclusivamente Ring Explosion RGB.\n"
if report_note.strip() not in report:
    report += report_note

data = SOURCE.read_bytes().replace(b"\r\n", b"\n")
blob = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
report, count = re.subn(r"```text\n[0-9a-f]{40}\n```", f"```text\n{blob}\n```", report, count=1)
if count != 1:
    raise SystemExit("validation report blob marker not found")
REPORT.write_text(report, encoding="utf-8")
