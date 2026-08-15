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

# Player state for jump-respawn.
old_vars = '\t\t57: InteraksiKameraDipakai\n}'
new_vars = '\t\t57: InteraksiKameraDipakai\n\t\t58: PosisiMati\n\t\t59: PosisiRespawnAman\n\t\t60: RespawnJumpDipakai\n}'
if src.count(old_vars) != 1:
    raise SystemExit(f'player variables anchor: expected 1, found {src.count(old_vars)}')
src = src.replace(old_vars, new_vars, 1)

# Shared feedback subroutines.
old_subs = '\t17: GambarSuara\n}'
new_subs = '\t17: GambarSuara\n\t18: EfekTerapkan\n\t19: EfekPulihkan\n}'
if src.count(old_subs) != 1:
    raise SystemExit(f'subroutine anchor: expected 1, found {src.count(old_subs)}')
src = src.replace(old_subs, new_subs, 1)

# Initialize the new variables for humans.
init_anchor = '\t\tEvent Player.InteraksiKameraDipakai = False;\n\t}\n}\n\nrule("95 - Subrutin:'
init_new = ('\t\tEvent Player.InteraksiKameraDipakai = False;\n'
            '\t\tEvent Player.PosisiMati = Vector(0, 0, 0);\n'
            '\t\tEvent Player.PosisiRespawnAman = Vector(0, 0, 0);\n'
            '\t\tEvent Player.RespawnJumpDipakai = False;\n'
            '\t}\n}\n\nrule("95 - Subrutin:')
if src.count(init_anchor) != 1:
    raise SystemExit(f'player init anchor: expected 1, found {src.count(init_anchor)}')
src = src.replace(init_anchor, init_new, 1)

# Insert audiovisual feedback subroutines before player initialization.
feedback_rules = r'''rule("93a - Subrutin: Efek perubahan diterapkan")
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
insert_at = src.index('rule("94 - Subrutin: Siapkan pemain')
src = src[:insert_at] + feedback_rules + src[insert_at:]

# Jump respawn: remember death point, respawn, then move to a nearby safe walkable position.
respawn_rules = r'''rule("12e - Respawn Jump: Simpan posisi kematian")
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
respawn_at = src.index('rule("13 - Intip Pahlawan:')
src = src[:respawn_at] + respawn_rules + src[respawn_at:]

# Add feedback to menu apply/restore actions, scoped to the Interact handler.
rule10_start = src.index('rule("10 - Menu: Interaksi membuka atau menerapkan pilihan")')
rule10_end = src.index('\nrule("11 - Menu:', rule10_start)
rule10 = src[rule10_start:rule10_end]

def replace_once(block: str, old: str, new: str, label: str) -> str:
    count = block.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1, found {count}')
    return block.replace(old, new, 1)

rule10 = replace_once(
    rule10,
    '\t\t\tEvent Player.IndeksGenre = Event Player.KursorGenre;\n',
    '\t\t\tEvent Player.IndeksGenre = Event Player.KursorGenre;\n\t\t\tCall Subroutine(EfekTerapkan);\n',
    'soundtrack feedback',
)
rule10 = replace_once(
    rule10,
    '\t\t\t\tEvent Player.TargetKamera = Null;\n\t\t\t\tSmall Message',
    '\t\t\t\tEvent Player.TargetKamera = Null;\n\t\t\t\tCall Subroutine(EfekPulihkan);\n\t\t\t\tSmall Message',
    'camera restore feedback',
)
# Two successful camera activation paths: own hero and spectate target.
old_camera_apply = '\t\t\t\tCall Subroutine(MulaiKamera);\n\t\t\t\tSmall Message'
if rule10.count(old_camera_apply) != 2:
    raise SystemExit(f'camera apply feedback: expected 2, found {rule10.count(old_camera_apply)}')
rule10 = rule10.replace(old_camera_apply, '\t\t\t\tCall Subroutine(MulaiKamera);\n\t\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\t\tSmall Message', 1)
old_camera_apply_target = '\t\t\t\t\tCall Subroutine(MulaiKamera);\n\t\t\t\t\tSmall Message'
if rule10.count(old_camera_apply_target) != 1:
    raise SystemExit(f'camera target feedback: expected 1, found {rule10.count(old_camera_apply_target)}')
rule10 = rule10.replace(old_camera_apply_target, '\t\t\t\t\tCall Subroutine(MulaiKamera);\n\t\t\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\t\t\tSmall Message', 1)

rule10 = replace_once(
    rule10,
    '\t\t\tEvent Player.WarnaNama = Global.DaftarWarna[Event Player.IndeksWarna];\n',
    '\t\t\tEvent Player.WarnaNama = Global.DaftarWarna[Event Player.IndeksWarna];\n\t\t\tIf(Event Player.IndeksWarna == 0);\n\t\t\t\tCall Subroutine(EfekPulihkan);\n\t\t\tElse;\n\t\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\tEnd;\n',
    'name color feedback',
)
rule10 = replace_once(
    rule10,
    '\t\t\tEvent Player.IndeksBahasa = Event Player.KursorBahasa;\n',
    '\t\t\tEvent Player.IndeksBahasa = Event Player.KursorBahasa;\n\t\t\tCall Subroutine(EfekTerapkan);\n',
    'language feedback',
)
rule10 = replace_once(
    rule10,
    '\t\t\t\t\tModify Player Variable At Index(Event Player, JumlahBalasDendam, Event Player.IndeksBalasDendam, Subtract, 1);\n',
    '\t\t\t\t\tModify Player Variable At Index(Event Player, JumlahBalasDendam, Event Player.IndeksBalasDendam, Subtract, 1);\n\t\t\t\t\tCall Subroutine(EfekTerapkan);\n',
    'revenge feedback',
)
rule10 = replace_once(
    rule10,
    '\t\t\tIf(Event Player.UnkillableAktif == True);\n\t\t\t\tSet Status',
    '\t\t\tIf(Event Player.UnkillableAktif == True);\n\t\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\t\tSet Status',
    'unkillable enable feedback',
)
rule10 = replace_once(
    rule10,
    '\t\t\tElse;\n\t\t\t\tClear Status(Event Player, Unkillable);',
    '\t\t\tElse;\n\t\t\t\tCall Subroutine(EfekPulihkan);\n\t\t\t\tClear Status(Event Player, Unkillable);',
    'unkillable disable feedback',
)
rule10 = replace_once(
    rule10,
    '\t\t\tEvent Player.IndeksSuara = Event Player.KursorSuara;\n',
    '\t\t\tEvent Player.IndeksSuara = Event Player.KursorSuara;\n\t\t\tIf(Event Player.IndeksSuara == 0);\n\t\t\t\tCall Subroutine(EfekPulihkan);\n\t\t\tElse;\n\t\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\tEnd;\n',
    'voice feedback',
)
src = src[:rule10_start] + rule10 + src[rule10_end:]

# Outside-menu Interact camera shortcut gets the same feedback.
cam_start = src.index('rule("12c - Kamera: Tahan Interact')
cam_end = src.index('\nrule("12d - Kamera:', cam_start)
cam = src[cam_start:cam_end]
cam = replace_once(
    cam,
    '\t\t\tCall Subroutine(MulaiKamera);\n\t\t\tSmall Message',
    '\t\t\tCall Subroutine(MulaiKamera);\n\t\t\tCall Subroutine(EfekTerapkan);\n\t\t\tSmall Message',
    'outside camera apply feedback',
)
cam = replace_once(
    cam,
    '\t\t\tEvent Player.TargetKamera = Null;\n\t\t\tSmall Message',
    '\t\t\tEvent Player.TargetKamera = Null;\n\t\t\tCall Subroutine(EfekPulihkan);\n\t\t\tSmall Message',
    'outside camera restore feedback',
)
src = src[:cam_start] + cam + src[cam_end:]

# Automatic camera restoration when the spectated target leaves.
rule16_start = src.index('rule("16 - Kamera: Target pergi')
rule16_end = src.index('\nrule("17 - Balas Dendam:', rule16_start)
rule16 = src[rule16_start:rule16_end]
rule16 = replace_once(
    rule16,
    '\t\tEvent Player.TargetKamera = Null;\n\t\tSmall Message',
    '\t\tEvent Player.TargetKamera = Null;\n\t\tCall Subroutine(EfekPulihkan);\n\t\tSmall Message',
    'camera target-left restore feedback',
)
src = src[:rule16_start] + rule16 + src[rule16_end:]

# Automatic Unkillable disable in spawn is a restoration too.
rule18c_start = src.index('rule("18c - Unkillable:')
rule18c_end = src.index('\nrule("19 - Teleport Crouch:', rule18c_start)
rule18c = src[rule18c_start:rule18c_end]
rule18c = replace_once(
    rule18c,
    '\t\t\tEvent Player.KursorUnkillable = 0;\n\t\t\tClear Status',
    '\t\t\tEvent Player.KursorUnkillable = 0;\n\t\t\tCall Subroutine(EfekPulihkan);\n\t\t\tClear Status',
    'spawn auto restore feedback',
)
src = src[:rule18c_start] + rule18c + src[rule18c_end:]

source_path.write_text(src, encoding='utf-8')

# Static validation for visibility/audio scope and jump-respawn safety.
val = validator_path.read_text(encoding='utf-8')
new_check = r'''

def check_feedback_and_jump_respawn(checks: Checks, source: str, rules: list[Rule]) -> None:
    clean = mask_strings(source)
    for slot, name in (
        (58, "PosisiMati"),
        (59, "PosisiRespawnAman"),
        (60, "RespawnJumpDipakai"),
    ):
        checks.require(
            re.search(rf"(?m)^\s*{slot}\s*:\s*{name}\s*$", section_body(source, "variables")) is not None,
            f"jump respawn: slot player {slot} deve essere {name}",
        )
    for slot, name in ((18, "EfekTerapkan"), (19, "EfekPulihkan")):
        checks.require(
            re.search(rf"(?m)^\s*{slot}\s*:\s*{name}\s*$", section_body(source, "subroutines")) is not None,
            f"feedback: subroutine {slot} deve essere {name}",
        )

    apply = rules_containing(rules, "Subroutine;", "EfekTerapkan;")
    restore = rules_containing(rules, "Subroutine;", "EfekPulihkan;")
    checks.equal(len(apply), 1, "subroutine feedback applicazione")
    checks.equal(len(restore), 1, "subroutine feedback ripristino")
    if apply:
        checks.require(
            code_contains(
                apply[0].body,
                "Play Effect(All Players(All Teams), Good Explosion",
                "Custom Color(80, 220, 255, 255)",
                "Play Effect(Event Player, Buff Impact Sound",
            ),
            "feedback applicazione: visuale globale o audio personale mancanti",
        )
    if restore:
        checks.require(
            code_contains(
                restore[0].body,
                "Play Effect(All Players(All Teams), Ring Explosion",
                "Custom Color(205, 160, 255, 255)",
                "Play Effect(Event Player, Ring Explosion Sound",
            ),
            "feedback ripristino: visuale globale o audio personale mancanti",
        )
    checks.require(
        "Play Effect(All Players(All Teams), Buff Impact Sound" not in clean
        and "Play Effect(All Players(All Teams), Ring Explosion Sound" not in clean,
        "feedback audio non deve essere udibile dagli altri player",
    )

    interact = [
        rule for rule in rules
        if code_contains(rule.body, "Event Player.PerintahMenu == 1;", "Event Player.HalamanMenu = Global.KodeMenu")
    ]
    checks.equal(len(interact), 1, "handler menu per feedback")
    if interact:
        body = mask_strings(interact[0].body)
        for token in (
            "Call Subroutine(EfekTerapkan);",
            "Call Subroutine(EfekPulihkan);",
            "Event Player.IndeksGenre = Event Player.KursorGenre;",
            "Event Player.IndeksWarna = Event Player.KursorWarna;",
            "Event Player.IndeksBahasa = Event Player.KursorBahasa;",
            "Event Player.IndeksSuara = Event Player.KursorSuara;",
            "Event Player.UnkillableAktif = And(",
        ):
            checks.require(token in body, f"feedback menu incompleto: {token}")

    death_capture = [
        rule for rule in rules
        if code_contains(
            rule.body,
            "Player Died;",
            "Event Player.PosisiMati = Position Of(Event Player);",
            "Event Player.RespawnJumpDipakai = False;",
        )
    ]
    checks.equal(len(death_capture), 1, "cattura posizione morte per Jump respawn")

    jump_respawn = [
        rule for rule in rules
        if code_contains(
            rule.body,
            "Is Alive(Event Player) == False;",
            "Event Player.MenuTerbuka == False;",
            "Event Player.TeleportCrouchAktif == False;",
            "Is Button Held(Event Player, Button(Jump)) == True;",
            "Nearest Walkable Position(Event Player.PosisiMati + Vector(Random Real(-6, 6), 0, Random Real(-6, 6)))",
            "Respawn(Event Player);",
            "Wait(0.016, Ignore Condition);",
            "Teleport(Event Player, Event Player.PosisiRespawnAman);",
            "Call Subroutine(EfekPulihkan);",
        )
    ]
    checks.equal(len(jump_respawn), 1, "Jump respawn su posizione camminabile sicura")
    if jump_respawn:
        body = mask_strings(jump_respawn[0].body)
        checks.require(
            body.find("Event Player.PosisiRespawnAman = Nearest Walkable Position")
            < body.find("Respawn(Event Player);")
            < body.find("Teleport(Event Player, Event Player.PosisiRespawnAman);"),
            "Jump respawn: posizione sicura deve essere catturata prima del Respawn e usata dopo",
        )
'''

main_marker = '\ndef main() -> None:\n'
if val.count(main_marker) != 1:
    raise SystemExit('validator main marker not found')
val = val.replace(main_marker, new_check + main_marker, 1)
call_anchor = '        check_arcade_features(checks, source, rules)\n'
if val.count(call_anchor) != 1:
    raise SystemExit('validator call anchor not found')
val = val.replace(call_anchor, call_anchor + '        check_feedback_and_jump_respawn(checks, source, rules)\n', 1)
validator_path.write_text(val, encoding='utf-8')

# Documentation.
readme = readme_path.read_text(encoding='utf-8')
feedback_line = '- Le modifiche/ripristini del menu hanno feedback audiovisivo: effetto visivo visibile a tutti, suono udibile solo dal player che esegue l’azione.'
respawn_line = '- Quando un player è morto può premere `Jump` per rinascere vicino al punto di morte in una posizione corretta con `Nearest Walkable Position`.'
for line in (feedback_line, respawn_line):
    if line not in readme:
        readme += '\n' + line
readme += '\n'
readme_path.write_text(readme, encoding='utf-8')

project = project_path.read_text(encoding='utf-8')
section = '''\n\n### Feedback modifiche e Jump respawn\n\nLe azioni applicate usano un `Good Explosion` azzurro-turchese visibile a tutti e `Buff Impact Sound` soltanto per il player che ha eseguito l’azione. I ripristini usano un `Ring Explosion` violetto chiaro visibile a tutti e `Ring Explosion Sound` soltanto per il player interessato. Camera, soundtrack, colore nome, lingua HUD, revenge riuscita, Unkillable e Voice Modifier condividono queste subroutine.\n\nAlla morte viene salvata `PosisiMati`. Con `Jump` e menu chiuso viene calcolato un punto casuale entro ±6 m e convertito tramite `Nearest Walkable Position`; il player viene poi `Respawn` e teletrasportato al punto catturato. Se il candidato restituisce il vettore zero, viene usato il punto camminabile più vicino alla posizione di morte.\n'''
if '### Feedback modifiche e Jump respawn' not in project:
    project += section
project_path.write_text(project, encoding='utf-8')

tests = test_doc_path.read_text(encoding='utf-8')
for line in (
    '- **Feedback live:** applicare e ripristinare Camera, Name Color, Unkillable e Voice Modifier con almeno due player; entrambi devono vedere il visuale, ma soltanto chi agisce deve sentire il suono.\n',
    '- **Jump respawn live:** morire su terreno normale, vicino a muri/scale e vicino a un bordo; con menu chiuso premere Jump e verificare respawn vicino al punto di morte senza finire dentro geometria o fuori mappa.\n',
):
    if line not in tests:
        tests += '\n' + line
test_doc_path.write_text(tests, encoding='utf-8')

# Validation report source blob + rule count.
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
