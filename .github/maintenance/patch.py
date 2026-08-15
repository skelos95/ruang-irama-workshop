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

def one(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1, found {count}')
    return text.replace(old, new, 1)

# New state + subroutines.
src = one(src, '\t\t57: InteraksiKameraDipakai\n}', '\t\t57: InteraksiKameraDipakai\n\t\t58: PosisiMati\n\t\t59: PosisiRespawnAman\n\t\t60: RespawnJumpDipakai\n}', 'player vars')
src = one(src, '\t17: GambarSuara\n}', '\t17: GambarSuara\n\t18: EfekTerapkan\n\t19: EfekPulihkan\n}', 'subroutines')

# Initialize.
src = one(
    src,
    '\t\tEvent Player.InteraksiKameraDipakai = False;\n\t}\n}\n\nrule("95 - Subrutin:',
    '\t\tEvent Player.InteraksiKameraDipakai = False;\n\t\tEvent Player.PosisiMati = Vector(0, 0, 0);\n\t\tEvent Player.PosisiRespawnAman = Vector(0, 0, 0);\n\t\tEvent Player.RespawnJumpDipakai = False;\n\t}\n}\n\nrule("95 - Subrutin:',
    'player init',
)

feedback = r'''rule("93a - Subrutin: Efek perubahan diterapkan")
{
	event
	{
		Subroutine;
		EfekTerapkan;
	}

	actions
	{
		Play Effect(All Players(All Teams), Good Explosion, Custom Color(80, 220, 255, 255), Position Of(Event Player) + Vector(0, 1, 0), 2.500);
		Play Effect(Event Player, Buff Impact Sound, Color(White), Position Of(Event Player), 35);
	}
}

rule("93b - Subrutin: Efek pengaturan dipulihkan")
{
	event
	{
		Subroutine;
		EfekPulihkan;
	}

	actions
	{
		Play Effect(All Players(All Teams), Ring Explosion, Custom Color(205, 160, 255, 255), Position Of(Event Player) + Vector(0, 1, 0), 3);
		Play Effect(Event Player, Ring Explosion Sound, Color(White), Position Of(Event Player), 35);
	}
}

'''
idx = src.index('rule("94 - Subrutin: Siapkan pemain')
src = src[:idx] + feedback + src[idx:]

respawn = r'''rule("12e - Respawn Jump: Simpan posisi kematian")
{
	event
	{
		Player Died;
		All;
		All;
	}

	conditions
	{
		Event Player.Manusia == True;
		Event Player.BotAI == False;
		Is Dummy Bot(Event Player) == False;
	}

	actions
	{
		Event Player.PosisiMati = Position Of(Event Player);
		Event Player.RespawnJumpDipakai = False;
		Small Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Press Jump to respawn near where you died.") : Event Player.IndeksBahasa == 1 ? Custom String("Tekan Jump untuk hidup kembali dekat tempat kamu mati.") : Custom String("กด Jump เพื่อเกิดใหม่ใกล้จุดที่คุณตาย"));
	}
}

rule("12f - Respawn Jump: Bangkit di posisi aman yang bisa dilalui")
{
	event
	{
		Ongoing - Each Player;
		All;
		All;
	}

	conditions
	{
		Event Player.Manusia == True;
		Event Player.BotAI == False;
		Is Dummy Bot(Event Player) == False;
		Is Alive(Event Player) == False;
		Event Player.MenuTerbuka == False;
		Event Player.TeleportCrouchAktif == False;
		Event Player.RespawnJumpDipakai == False;
		Is Button Held(Event Player, Button(Jump)) == True;
	}

	actions
	{
		Event Player.RespawnJumpDipakai = True;
		Event Player.PosisiRespawnAman = Nearest Walkable Position(Event Player.PosisiMati + Vector(Random Real(-6, 6), 0, Random Real(-6, 6)));
		If(Distance Between(Event Player.PosisiRespawnAman, Vector(0, 0, 0)) <= 0.100);
			Event Player.PosisiRespawnAman = Nearest Walkable Position(Event Player.PosisiMati);
		End;
		Respawn(Event Player);
		Wait(0.016, Ignore Condition);
		Teleport(Event Player, Event Player.PosisiRespawnAman);
		Call Subroutine(EfekPulihkan);
		Small Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Respawned at a nearby safe walkable position.") : Event Player.IndeksBahasa == 1 ? Custom String("Hidup kembali di posisi aman terdekat yang bisa dilalui.") : Custom String("เกิดใหม่ในตำแหน่งปลอดภัยใกล้เคียงที่เดินได้แล้ว"));
	}
}

'''
idx = src.index('rule("13 - Intip Pahlawan:')
src = src[:idx] + respawn + src[idx:]

# Menu apply feedback.
r10s = src.index('rule("10 - Menu: Interaksi membuka atau menerapkan pilihan")')
r10e = src.index('\nrule("11 - Menu:', r10s)
r10 = src[r10s:r10e]
r10 = one(r10, '\t\t\tEvent Player.IndeksGenre = Event Player.KursorGenre;\n', '\t\t\tEvent Player.IndeksGenre = Event Player.KursorGenre;\n\t\t\tCall Subroutine(EfekTerapkan);\n', 'soundtrack')
r10 = one(r10, '\t\t\t\tEvent Player.TargetKamera = Null;\n\t\t\t\tSmall Message', '\t\t\t\tEvent Player.TargetKamera = Null;\n\t\t\t\tCall Subroutine(EfekPulihkan);\n\t\t\t\tSmall Message', 'camera off')
r10 = one(r10, '\t\t\t\tCall Subroutine(MulaiKamera);\n\t\t\t\tSmall Message', '\t\t\t\tCall Subroutine(MulaiKamera);\n\t\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\t\tSmall Message', 'camera self')
r10 = one(r10, '\t\t\t\t\tCall Subroutine(MulaiKamera);\n\t\t\t\t\tSmall Message', '\t\t\t\t\tCall Subroutine(MulaiKamera);\n\t\t\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\t\t\tSmall Message', 'camera spectate')
r10 = one(r10, '\t\t\tEvent Player.WarnaNama = Global.DaftarWarna[Event Player.IndeksWarna];\n', '\t\t\tEvent Player.WarnaNama = Global.DaftarWarna[Event Player.IndeksWarna];\n\t\t\tIf(Event Player.IndeksWarna == 0);\n\t\t\t\tCall Subroutine(EfekPulihkan);\n\t\t\tElse;\n\t\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\tEnd;\n', 'color')
r10 = one(r10, '\t\t\tEvent Player.IndeksBahasa = Event Player.KursorBahasa;\n', '\t\t\tEvent Player.IndeksBahasa = Event Player.KursorBahasa;\n\t\t\tCall Subroutine(EfekTerapkan);\n', 'language')
r10 = one(r10, '\t\t\t\t\tModify Player Variable At Index(Event Player, JumlahBalasDendam, Event Player.IndeksBalasDendam, Subtract, 1);\n', '\t\t\t\t\tModify Player Variable At Index(Event Player, JumlahBalasDendam, Event Player.IndeksBalasDendam, Subtract, 1);\n\t\t\t\t\tCall Subroutine(EfekTerapkan);\n', 'revenge')
r10 = one(r10, '\t\t\tIf(Event Player.UnkillableAktif == True);\n\t\t\t\tSet Status', '\t\t\tIf(Event Player.UnkillableAktif == True);\n\t\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\t\tSet Status', 'unkillable on')
r10 = one(r10, '\t\t\tElse;\n\t\t\t\tClear Status(Event Player, Unkillable);', '\t\t\tElse;\n\t\t\t\tCall Subroutine(EfekPulihkan);\n\t\t\t\tClear Status(Event Player, Unkillable);', 'unkillable off')
r10 = one(r10, '\t\t\tEvent Player.IndeksSuara = Event Player.KursorSuara;\n', '\t\t\tEvent Player.IndeksSuara = Event Player.KursorSuara;\n\t\t\tIf(Event Player.IndeksSuara == 0);\n\t\t\t\tCall Subroutine(EfekPulihkan);\n\t\t\tElse;\n\t\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\tEnd;\n', 'voice')
src = src[:r10s] + r10 + src[r10e:]

# Outside-menu camera shortcut.
cs = src.index('rule("12c - Kamera: Tahan Interact')
ce = src.index('\nrule("12d - Kamera:', cs)
cam = src[cs:ce]
cam = one(cam, '\t\t\tCall Subroutine(MulaiKamera);\n\t\t\tSmall Message', '\t\t\tCall Subroutine(MulaiKamera);\n\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\tSmall Message', 'outside cam on')
cam = one(cam, '\t\t\tEvent Player.TargetKamera = Null;\n\t\t\tSmall Message', '\t\t\tEvent Player.TargetKamera = Null;\n\t\t\tCall Subroutine(EfekPulihkan);\n\t\t\tSmall Message', 'outside cam off')
src = src[:cs] + cam + src[ce:]

# Auto camera restore.
s16 = src.index('rule("16 - Kamera: Target pergi')
e16 = src.index('\nrule("17 - Balas Dendam:', s16)
b16 = src[s16:e16]
b16 = one(b16, '\t\tEvent Player.TargetKamera = Null;\n\t\tSmall Message', '\t\tEvent Player.TargetKamera = Null;\n\t\tCall Subroutine(EfekPulihkan);\n\t\tSmall Message', 'target-left')
src = src[:s16] + b16 + src[e16:]

# Auto Unkillable restore in spawn.
s18 = src.index('rule("18c - Unkillable:')
e18 = src.index('\nrule("19 - Teleport Crouch:', s18)
b18 = src[s18:e18]
b18 = one(b18, '\t\t\tEvent Player.KursorUnkillable = 0;\n\t\t\tClear Status', '\t\t\tEvent Player.KursorUnkillable = 0;\n\t\t\tCall Subroutine(EfekPulihkan);\n\t\t\tClear Status', 'spawn restore')
src = src[:s18] + b18 + src[e18:]
source_path.write_text(src, encoding='utf-8')

# Validator checks.
val = validator_path.read_text(encoding='utf-8')
check = r'''

def check_feedback_and_jump_respawn(checks: Checks, source: str, rules: list[Rule]) -> None:
    clean = mask_strings(source)
    for token in (
        "58: PosisiMati", "59: PosisiRespawnAman", "60: RespawnJumpDipakai",
        "18: EfekTerapkan", "19: EfekPulihkan",
        "Play Effect(All Players(All Teams), Good Explosion, Custom Color(80, 220, 255, 255)",
        "Play Effect(Event Player, Buff Impact Sound",
        "Play Effect(All Players(All Teams), Ring Explosion, Custom Color(205, 160, 255, 255)",
        "Play Effect(Event Player, Ring Explosion Sound",
        "Event Player.PosisiMati = Position Of(Event Player);",
        "Nearest Walkable Position(Event Player.PosisiMati + Vector(Random Real(-6, 6), 0, Random Real(-6, 6)))",
        "Respawn(Event Player);",
        "Teleport(Event Player, Event Player.PosisiRespawnAman);",
    ):
        checks.require(token in clean, f"feedback/respawn mancante: {token}")
    checks.require(
        "Play Effect(All Players(All Teams), Buff Impact Sound" not in clean
        and "Play Effect(All Players(All Teams), Ring Explosion Sound" not in clean,
        "gli effetti sonori devono essere personali, non globali",
    )
    apply = rules_containing(rules, "Subroutine;", "EfekTerapkan;")
    restore = rules_containing(rules, "Subroutine;", "EfekPulihkan;")
    checks.equal(len(apply), 1, "subroutine EfekTerapkan")
    checks.equal(len(restore), 1, "subroutine EfekPulihkan")
    death = rules_containing(rules, "Player Died;", "Event Player.PosisiMati = Position Of(Event Player);")
    checks.equal(len(death), 1, "cattura posizione morte")
    jump = [rule for rule in rules if code_contains(rule.body, "Is Alive(Event Player) == False;", "Button(Jump)", "Respawn(Event Player);", "PosisiRespawnAman")]
    checks.equal(len(jump), 1, "Jump respawn")
    if jump:
        body = mask_strings(jump[0].body)
        checks.require(
            body.find("Nearest Walkable Position") < body.find("Respawn(Event Player);") < body.find("Teleport(Event Player, Event Player.PosisiRespawnAman);"),
            "Jump respawn: ordine posizione sicura -> respawn -> teleport errato",
        )
'''
marker = '\ndef main() -> None:\n'
if val.count(marker) != 1:
    raise SystemExit('validator main marker')
val = val.replace(marker, check + marker, 1)
anchor = '        check_arcade_features(checks, source, rules)\n'
if val.count(anchor) != 1:
    raise SystemExit('validator call anchor')
val = val.replace(anchor, anchor + '        check_feedback_and_jump_respawn(checks, source, rules)\n', 1)
validator_path.write_text(val, encoding='utf-8')

# Docs.
readme = readme_path.read_text(encoding='utf-8')
for line in (
    '- Le modifiche e i ripristini hanno feedback audiovisivo: visuale visibile a tutti, audio solo per chi esegue l’azione.',
    '- Da morto, con menu chiuso, `Jump` forza il respawn vicino al punto di morte su una posizione corretta da `Nearest Walkable Position`.',
):
    if line not in readme:
        readme += '\n' + line
readme += '\n'
readme_path.write_text(readme, encoding='utf-8')

project = project_path.read_text(encoding='utf-8')
if '### Feedback audiovisivo e Jump respawn' not in project:
    project += '''\n\n### Feedback audiovisivo e Jump respawn\n\nLe modifiche applicate usano un `Good Explosion` azzurro-turchese visibile a tutti e `Buff Impact Sound` solo per il player che agisce. I ripristini usano un `Ring Explosion` violetto chiaro visibile a tutti e `Ring Explosion Sound` soltanto per il player interessato.\n\nAlla morte viene salvata la posizione. Premendo `Jump` a menu chiuso viene scelto un punto casuale entro ±6 m, corretto con `Nearest Walkable Position`, poi il player viene respawnato e teletrasportato al punto sicuro.\n'''
project_path.write_text(project, encoding='utf-8')

tests = test_doc_path.read_text(encoding='utf-8')
for line in (
    '- **Feedback live:** con due player applicare/ripristinare Camera, colore, Unkillable e Voice Modifier; entrambi vedono il visuale ma soltanto chi agisce sente il suono.\n',
    '- **Jump respawn live:** morire vicino a muri, scale e bordi; premere Jump e verificare il respawn vicino senza finire dentro la geometria.\n',
):
    if line not in tests:
        tests += '\n' + line
test_doc_path.write_text(tests, encoding='utf-8')

# Validation report.
data = source_path.read_bytes().replace(b'\r\n', b'\n')
blob = hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()
report = report_path.read_text(encoding='utf-8')
report, n = re.subn(r'```text\n[0-9a-f]{40}\n```', f'```text\n{blob}\n```', report, count=1)
if n != 1:
    raise SystemExit('validation report blob')
rule_count = len(re.findall(r'(?m)^\s*rule\s*\(', src))
report = re.sub(r'Generi: 100 \| Lingue: 3 \| Regole: \d+ \| Raycast camera: 1', f'Generi: 100 | Lingue: 3 | Regole: {rule_count} | Raycast camera: 1', report, count=1)
report_path.write_text(report, encoding='utf-8')
