from __future__ import annotations

from pathlib import Path
import hashlib
import re

source_path = Path('workshop/ruang_irama.workshop')
validator_path = Path('tools/validate_workshop.py')
readme_path = Path('README.md')
project_path = Path('docs/PROGETTO.md')
test_doc_path = Path('docs/TEST.md')
report_path = Path('docs/VALIDAZIONE.md')

src = source_path.read_text(encoding='utf-8')

# Global RGB state.
old_globals = '\t\t36: DaftarNegaraVPN\n\t\t37: IndeksNegaraVPN\n\tplayer:'
new_globals = '\t\t36: DaftarNegaraVPN\n\t\t37: IndeksNegaraVPN\n\t\t38: RGB\n\t\t39: RGBFase\n\tplayer:'
if src.count(old_globals) != 1:
    raise SystemExit(f'RGB global variables anchor: expected 1, found {src.count(old_globals)}')
src = src.replace(old_globals, new_globals, 1)

# Initialize RGB before HUD creation.
init_anchor = '\t\tGlobal.RestartSudahDiminta = False;\n\t\t"Tidak ada mode yang boleh mengakhiri pertandingan'
init_new = ('\t\tGlobal.RestartSudahDiminta = False;\n'
            '\t\tGlobal.RGBFase = 0;\n'
            '\t\tGlobal.RGB = Custom Color(255, 0, 0, 255);\n'
            '\t\t"Tidak ada mode yang boleh mengakhiri pertandingan')
if src.count(init_anchor) != 1:
    raise SystemExit(f'RGB initialization anchor: expected 1, found {src.count(init_anchor)}')
src = src.replace(init_anchor, init_new, 1)

# Main title + timer uses the animated RGB color and reevaluates color live.
hud_old = '''\t\t\tTop, -100, Color(White), Custom Color(80, 235, 255, 255), Color(White), Visible To and String, Visible Never);'''
hud_new = '''\t\t\tTop, -100, Color(White), Custom Color(80, 235, 255, 255), Global.RGB, Visible To String and Color, Visible Never);'''
if src.count(hud_old) != 1:
    raise SystemExit(f'main HUD RGB anchor: expected 1, found {src.count(hud_old)}')
src = src.replace(hud_old, hud_new, 1)

# Single lightweight rainbow loop: R -> Y -> G -> C -> B -> M -> R.
rgb_rule = r'''rule("00r - Global: RGB pelangi untuk judul, timer, dan efek")
{
	event
	{
		Ongoing - Global;
	}

	conditions
	{
		Global.Siap == True;
	}

	actions
	{
		Global.RGB = Custom Color(
			Global.RGBFase < 255 ? 255 : Global.RGBFase < 510 ? 510 - Global.RGBFase : Global.RGBFase < 1020 ? 0 : Global.RGBFase < 1275 ? Global.RGBFase - 1020 : 255,
			Global.RGBFase < 255 ? Global.RGBFase : Global.RGBFase < 765 ? 255 : Global.RGBFase < 1020 ? 1020 - Global.RGBFase : 0,
			Global.RGBFase < 510 ? 0 : Global.RGBFase < 765 ? Global.RGBFase - 510 : Global.RGBFase < 1275 ? 255 : 1530 - Global.RGBFase,
			255);
		Wait(0.100, Ignore Condition);
		Global.RGBFase = (Global.RGBFase + 12) % 1530;
		Loop If Condition Is True;
	}
}

'''
insert_at = src.index('rule("00a1 - Global:')
src = src[:insert_at] + rgb_rule + src[insert_at:]

# All shared visual feedback now uses the same current RGB; audio remains personal.
visual_replacements = {
    'Play Effect(All Players(All Teams), Good Explosion, Custom Color(80, 220, 255, 255), Position Of(Event Player) + Vector(0, 1, 0), 2.500);':
        'Play Effect(All Players(All Teams), Good Explosion, Global.RGB, Position Of(Event Player) + Vector(0, 1, 0), 2.500);',
    'Play Effect(All Players(All Teams), Ring Explosion, Custom Color(205, 160, 255, 255), Position Of(Event Player) + Vector(0, 1, 0), 3);':
        'Play Effect(All Players(All Teams), Ring Explosion, Global.RGB, Position Of(Event Player) + Vector(0, 1, 0), 3);',
}
for old, new in visual_replacements.items():
    if src.count(old) != 1:
        raise SystemExit(f'visual feedback RGB anchor not unique: {old!r} -> {src.count(old)}')
    src = src.replace(old, new, 1)

source_path.write_text(src, encoding='utf-8')

# Validator: lock in RGB architecture and usage.
val = validator_path.read_text(encoding='utf-8')
new_check = r'''

def check_rgb_system(checks: Checks, source: str, rules: list[Rule]) -> None:
    globals_body = section_body(source, "variables")
    for slot, name in ((38, "RGB"), (39, "RGBFase")):
        checks.require(
            re.search(rf"(?m)^\s*{slot}\s*:\s*{name}\s*$", globals_body) is not None,
            f"RGB: slot global {slot} deve essere {name}",
        )

    clean = mask_strings(source)
    checks.require("Global.RGBFase = 0;" in clean, "RGB: fase iniziale assente")
    checks.require(
        "Global.RGB = Custom Color(255, 0, 0, 255);" in clean,
        "RGB: colore iniziale rosso assente",
    )

    rgb_rules = [
        rule for rule in rules
        if code_contains(
            rule.body,
            "Ongoing - Global;",
            "Global.Siap == True;",
            "Global.RGB = Custom Color(",
            "Global.RGBFase < 255",
            "Global.RGBFase < 510",
            "Global.RGBFase < 765",
            "Global.RGBFase < 1020",
            "Global.RGBFase < 1275",
            "Wait(0.100, Ignore Condition);",
            "Global.RGBFase = (Global.RGBFase + 12) % 1530;",
            "Loop If Condition Is True;",
        )
    ]
    checks.equal(len(rgb_rules), 1, "loop RGB globale")

    main_hud = [
        call for call in call_texts(source, "Create HUD Text")
        if "CHILL DEDICATED SERVER" in call and "Global.TeksWaktuServer" in call
    ]
    checks.equal(len(main_hud), 1, "HUD principale RGB")
    if main_hud:
        checks.require(
            "Global.RGB" in main_hud[0]
            and "Visible To String and Color" in main_hud[0],
            "HUD principale: titolo/timer non usano RGB con rivalutazione colore",
        )

    apply = rules_containing(rules, "Subroutine;", "EfekTerapkan;")
    restore = rules_containing(rules, "Subroutine;", "EfekPulihkan;")
    checks.equal(len(apply), 1, "RGB feedback applicazione")
    checks.equal(len(restore), 1, "RGB feedback ripristino")
    if apply:
        checks.require(
            code_contains(apply[0].body, "Play Effect(All Players(All Teams), Good Explosion, Global.RGB"),
            "effetto applicazione non usa Global.RGB",
        )
    if restore:
        checks.require(
            code_contains(restore[0].body, "Play Effect(All Players(All Teams), Ring Explosion, Global.RGB"),
            "effetto ripristino non usa Global.RGB",
        )

    checks.require(
        "Custom Color(80, 220, 255, 255)" not in clean
        and "Custom Color(205, 160, 255, 255)" not in clean,
        "vecchi colori statici degli effetti ancora presenti",
    )
'''
main_marker = '\ndef main() -> None:\n'
if val.count(main_marker) != 1:
    raise SystemExit('validator main marker not found')
val = val.replace(main_marker, new_check + main_marker, 1)
call_anchor = '        check_feedback_and_jump_respawn(checks, source, rules)\n'
if val.count(call_anchor) != 1:
    raise SystemExit('validator RGB call anchor not found')
val = val.replace(call_anchor, call_anchor + '        check_rgb_system(checks, source, rules)\n', 1)
validator_path.write_text(val, encoding='utf-8')

# Documentation.
readme = readme_path.read_text(encoding='utf-8')
line = '- Sistema RGB globale animato: il titolo `CHILL DEDICATED SERVER`, il timer centrale e gli effetti visivi condividono lo stesso ciclo rainbow in tempo reale.'
if line not in readme:
    readme += '\n' + line + '\n'
readme_path.write_text(readme, encoding='utf-8')

project = project_path.read_text(encoding='utf-8')
section = '''\n\n### Sistema RGB globale\n\n`Global.RGBFase` percorre un ciclo di 1530 step e `Global.RGB` viene ricostruito ogni 0,100 s come `Custom Color`, attraversando rosso → giallo → verde → ciano → blu → viola → rosso. Il passo è 12 per tick, quindi il ciclo completo dura circa 12,75 secondi con un solo loop globale a 10 Hz. Il testo principale `CHILL DEDICATED SERVER` insieme al timer usa `Global.RGB` con rivalutazione `Visible To String and Color`; `EfekTerapkan` ed `EfekPulihkan` usano lo stesso colore RGB corrente per i visuali globali, mentre i suoni rimangono limitati a `Event Player`.\n'''
if '### Sistema RGB globale' not in project:
    project += section
project_path.write_text(project, encoding='utf-8')

tests = test_doc_path.read_text(encoding='utf-8')
line = '- **RGB live:** osservare per almeno 15 secondi titolo+timer e verificare transizione continua rosso→giallo→verde→ciano→blu→viola→rosso; durante il ciclo applicare/ripristinare una modifica e controllare che l’effetto visivo usi il colore RGB del momento.\n'
if line not in tests:
    tests += '\n' + line
test_doc_path.write_text(tests, encoding='utf-8')

# Keep validation report aligned with the new Workshop blob and rule count.
data = source_path.read_bytes().replace(b'\r\n', b'\n')
blob = hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()
report = report_path.read_text(encoding='utf-8')
report, n = re.subn(r'```text\n[0-9a-f]{40}\n```', f'```text\n{blob}\n```', report, count=1)
if n != 1:
    raise SystemExit('validation report blob marker not found')
rule_count = len(re.findall(r'(?m)^\s*rule\s*\(', src))
report = re.sub(
    r'Generi: 100 \| Lingue: 3 \| Regole: \d+ \| Raycast camera: 1',
    f'Generi: 100 | Lingue: 3 | Regole: {rule_count} | Raycast camera: 1',
    report,
    count=1,
)
report_path.write_text(report, encoding='utf-8')
