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
src = src.replace(
    '\t\t36: DaftarNegaraVPN\n\t\t37: IndeksNegaraVPN\n\tplayer:',
    '\t\t36: DaftarNegaraVPN\n\t\t37: IndeksNegaraVPN\n\t\t38: RGB\n\t\t39: RGBFase\n\tplayer:',
    1,
)
src = src.replace(
    '\t\tGlobal.RestartSudahDiminta = False;\n\t\t"Tidak ada mode yang boleh mengakhiri pertandingan',
    '\t\tGlobal.RestartSudahDiminta = False;\n\t\tGlobal.RGBFase = 0;\n\t\tGlobal.RGB = Custom Color(255, 0, 0, 255);\n\t\t"Tidak ada mode yang boleh mengakhiri pertandingan',
    1,
)

# Title + timer color becomes live RGB.
src = src.replace(
    '\t\t\tTop, -100, Color(White), Custom Color(80, 235, 255, 255), Color(White), Visible To and String, Visible Never);',
    '\t\t\tTop, -100, Color(White), Custom Color(80, 235, 255, 255), Global.RGB, Visible To String and Color, Visible Never);',
    1,
)

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
if 'rule("00r - Global: RGB pelangi' not in src:
    src = src.replace('rule("00a1 - Global:', rgb_rule + 'rule("00a1 - Global:', 1)

# Shared visual effects use the RGB color at action time; sounds stay personal.
src = src.replace(
    'Play Effect(All Players(All Teams), Good Explosion, Custom Color(80, 220, 255, 255), Position Of(Event Player) + Vector(0, 1, 0), 2.500);',
    'Play Effect(All Players(All Teams), Good Explosion, Global.RGB, Position Of(Event Player) + Vector(0, 1, 0), 2.500);',
    1,
)
src = src.replace(
    'Play Effect(All Players(All Teams), Ring Explosion, Custom Color(205, 160, 255, 255), Position Of(Event Player) + Vector(0, 1, 0), 3);',
    'Play Effect(All Players(All Teams), Ring Explosion, Global.RGB, Position Of(Event Player) + Vector(0, 1, 0), 3);',
    1,
)

for required in (
    '\t\t38: RGB', '\t\t39: RGBFase',
    'Global.RGB = Custom Color(',
    'Global.RGBFase = (Global.RGBFase + 12) % 1530;',
    'Global.RGB, Visible To String and Color',
    'Good Explosion, Global.RGB',
    'Ring Explosion, Global.RGB',
):
    if required not in src:
        raise SystemExit(f'RGB source patch incomplete: {required}')
source_path.write_text(src, encoding='utf-8')

val = validator_path.read_text(encoding='utf-8')
# Existing feedback validator must follow the new RGB visual contract.
val = val.replace(
    'Play Effect(All Players(All Teams), Good Explosion, Custom Color(80, 220, 255, 255)',
    'Play Effect(All Players(All Teams), Good Explosion, Global.RGB',
)
val = val.replace(
    'Play Effect(All Players(All Teams), Ring Explosion, Custom Color(205, 160, 255, 255)',
    'Play Effect(All Players(All Teams), Ring Explosion, Global.RGB',
)

if 'def check_rgb_system(' not in val:
    rgb_check = r'''

def check_rgb_system(checks: Checks, source: str, rules: list[Rule]) -> None:
    globals_body = section_body(source, "variables")
    for slot, name in ((38, "RGB"), (39, "RGBFase")):
        checks.require(
            re.search(rf"(?m)^\s*{slot}\s*:\s*{name}\s*$", globals_body) is not None,
            f"RGB: slot global {slot} deve essere {name}",
        )
    clean = mask_strings(source)
    checks.require("Global.RGBFase = 0;" in clean, "RGB: fase iniziale assente")
    checks.require("Global.RGB = Custom Color(255, 0, 0, 255);" in clean, "RGB: colore iniziale assente")
    rgb_rules = [rule for rule in rules if code_contains(
        rule.body,
        "Ongoing - Global;",
        "Global.RGB = Custom Color(",
        "Wait(0.100, Ignore Condition);",
        "Global.RGBFase = (Global.RGBFase + 12) % 1530;",
        "Loop If Condition Is True;",
    )]
    checks.equal(len(rgb_rules), 1, "loop RGB globale")
    hud = [call for call in call_texts(source, "Create HUD Text") if "CHILL DEDICATED SERVER" in call and "Global.TeksWaktuServer" in call]
    checks.equal(len(hud), 1, "HUD principale RGB")
    if hud:
        checks.require("Global.RGB" in hud[0] and "Visible To String and Color" in hud[0], "titolo/timer non rivalutano Global.RGB")
    apply = rules_containing(rules, "Subroutine;", "EfekTerapkan;")
    restore = rules_containing(rules, "Subroutine;", "EfekPulihkan;")
    if apply:
        checks.require(code_contains(apply[0].body, "Good Explosion, Global.RGB"), "effetto applicazione non usa RGB")
    if restore:
        checks.require(code_contains(restore[0].body, "Ring Explosion, Global.RGB"), "effetto ripristino non usa RGB")
'''
    val = val.replace('\ndef main() -> None:\n', rgb_check + '\ndef main() -> None:\n', 1)
    val = val.replace(
        '        check_feedback_and_jump_respawn(checks, source, rules)\n',
        '        check_feedback_and_jump_respawn(checks, source, rules)\n        check_rgb_system(checks, source, rules)\n',
        1,
    )
validator_path.write_text(val, encoding='utf-8')

readme = readme_path.read_text(encoding='utf-8')
line = '- Sistema RGB globale animato: il titolo `CHILL DEDICATED SERVER`, il timer centrale e gli effetti visivi condividono lo stesso ciclo rainbow in tempo reale.'
if line not in readme:
    readme += '\n' + line + '\n'
readme_path.write_text(readme, encoding='utf-8')

project = project_path.read_text(encoding='utf-8')
if '### Sistema RGB globale' not in project:
    project += '''\n\n### Sistema RGB globale\n\n`Global.RGBFase` percorre 1530 step; `Global.RGB` viene aggiornato ogni 0,100 s e attraversa rosso → giallo → verde → ciano → blu → viola → rosso. Il passo è 12, quindi un giro dura circa 12,75 secondi. Titolo `CHILL DEDICATED SERVER` e timer rivalutano il colore in tempo reale; gli effetti visivi usano il colore RGB del momento, mentre i suoni restano personali.\n'''
project_path.write_text(project, encoding='utf-8')

tests = test_doc_path.read_text(encoding='utf-8')
line = '- **RGB live:** osservare per almeno 15 secondi titolo+timer e verificare rosso→giallo→verde→ciano→blu→viola→rosso; eseguire anche una modifica/ripristino e controllare che il visuale usi il colore RGB corrente.\n'
if line not in tests:
    tests += '\n' + line
test_doc_path.write_text(tests, encoding='utf-8')

data = source_path.read_bytes().replace(b'\r\n', b'\n')
blob = hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()
report = report_path.read_text(encoding='utf-8')
report, n = re.subn(r'```text\n[0-9a-f]{40}\n```', f'```text\n{blob}\n```', report, count=1)
if n != 1:
    raise SystemExit('validation report blob marker not found')
rule_count = len(re.findall(r'(?m)^\s*rule\s*\(', src))
report = re.sub(r'Generi: 100 \| Lingue: 3 \| Regole: \d+ \| Raycast camera: 1', f'Generi: 100 | Lingue: 3 | Regole: {rule_count} | Raycast camera: 1', report, count=1)
report_path.write_text(report, encoding='utf-8')
