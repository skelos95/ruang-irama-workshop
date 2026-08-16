from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
PROJECT = ROOT / "docs" / "PROGETTO.md"
VALIDATION = ROOT / "docs" / "VALIDAZIONE.md"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one occurrence, found {count}")
    return text.replace(old, new, 1)


def rule_region(text: str, prefix: str) -> tuple[int, int, str]:
    start = text.index(f'rule("{prefix}')
    end = text.find('\nrule("', start + 1)
    if end < 0:
        end = len(text)
    return start, end, text[start:end]


def replace_in_rule(text: str, prefix: str, old: str, new: str, label: str) -> str:
    start, end, region = rule_region(text, prefix)
    region = replace_once(region, old, new, label)
    return text[:start] + region + text[end:]


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    return hashlib.sha1(payload).hexdigest()


source = SOURCE.read_text(encoding="utf-8")

# Extra handles for a fully persistent card and temporary camera state.
source = replace_once(
    source,
    "\t\t76: IkonKartuNasib\n",
    "\t\t76: IkonKartuNasib\n\t\t77: IkonKartuNasibHijau\n\t\t78: TeksKartuNasibKanan\n\t\t79: ModeKameraSebelumNasib\n\t\t80: TargetKameraSebelumNasib\n",
    "luck variables",
)

# Save camera state and enter first person for the duration of the roulette.
source = replace_once(
    source,
    "\t\t\t\tEvent Player.KartuNasibAktif = True;\n\t\t\t\tEvent Player.KartuNasibMerah = Random Integer(0, 1) == 0;",
    "\t\t\t\tEvent Player.ModeKameraSebelumNasib = Event Player.ModeKamera;\n\t\t\t\tEvent Player.TargetKameraSebelumNasib = Event Player.TargetKamera;\n\t\t\t\tIf(Event Player.ModeKamera != 0);\n\t\t\t\t\tStop Camera(Event Player);\n\t\t\t\t\tEvent Player.ModeKamera = 0;\n\t\t\t\t\tEvent Player.TargetKamera = Null;\n\t\t\t\t\tWait(0.016, Ignore Condition);\n\t\t\t\tEnd;\n\t\t\t\tEvent Player.KartuNasibAktif = True;\n\t\t\t\tEvent Player.KartuNasibMerah = Random Integer(0, 1) == 0;",
    "first person lock",
)

old_visual = '''\t\t\t\tEvent Player.PosisiKartuNasib = Eye Position(Event Player) + Facing Direction Of(Event Player) * 4;
\t\t\t\tCreate In-World Text(All Players(All Teams), Custom String("[     ]"), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), 2.200, Do Not Clip, Visible To Position String and Color, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Visible Never);
\t\t\t\tEvent Player.TeksKartuNasib = Last Text ID;
\t\t\t\tIf(Event Player.KartuNasibMerah == True);
\t\t\t\t\tCreate Icon(All Players(All Teams), Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 - Vector(0, 0.450, 0), Skull, Visible To and Position, Custom Color(255, 70, 70, 255), False);
\t\t\t\tElse;
\t\t\t\t\tCreate Icon(All Players(All Teams), Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 - Vector(0, 0.450, 0), Heart, Visible To and Position, Custom Color(70, 255, 110, 255), False);
\t\t\t\tEnd;
\t\t\t\tEvent Player.IkonKartuNasib = Last Created Entity;'''
new_visual = '''\t\t\t\tEvent Player.PosisiKartuNasib = Eye Position(Event Player) + Facing Direction Of(Event Player) * 4;
\t\t\t\tCreate In-World Text(All Players(All Teams), Custom String("["), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 - Cross Product(Direction From Angles(Horizontal Facing Angle Of(Event Player), 0), Vector(0, 1, 0)) * 0.300), 2.200, Do Not Clip, Visible To Position String and Color, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Visible Never);
\t\t\t\tEvent Player.TeksKartuNasib = Last Text ID;
\t\t\t\tCreate In-World Text(All Players(All Teams), Custom String("]"), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 + Cross Product(Direction From Angles(Horizontal Facing Angle Of(Event Player), 0), Vector(0, 1, 0)) * 0.300), 2.200, Do Not Clip, Visible To Position String and Color, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Visible Never);
\t\t\t\tEvent Player.TeksKartuNasibKanan = Last Text ID;
\t\t\t\tCreate Icon(Event Player.KartuNasibMerah ? All Players(All Teams) : Empty Array, Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 - Vector(0, 0.450, 0)), Skull, Visible To and Position, Custom Color(255, 70, 70, 255), False);
\t\t\t\tEvent Player.IkonKartuNasib = Last Created Entity;
\t\t\t\tCreate Icon(Event Player.KartuNasibMerah ? Empty Array : All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 - Vector(0, 0.450, 0)), Heart, Visible To and Position, Custom Color(70, 255, 110, 255), False);
\t\t\t\tEvent Player.IkonKartuNasibHijau = Last Created Entity;'''
source = replace_once(source, old_visual, new_visual, "split persistent visuals")

# Do not destroy/recreate icons on every color change.
old_tick = '''\t\tEvent Player.KartuNasibMerah = Event Player.KartuNasibMerah == False;
\t\tIf(Event Player.IkonKartuNasib != Null);
\t\t\tDestroy Icon(Event Player.IkonKartuNasib);
\t\tEnd;
\t\tIf(Event Player.KartuNasibMerah == True);
\t\t\tCreate Icon(All Players(All Teams), Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 - Vector(0, 0.450, 0), Skull, Visible To and Position, Custom Color(255, 70, 70, 255), False);
\t\tElse;
\t\t\tCreate Icon(All Players(All Teams), Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 - Vector(0, 0.450, 0), Heart, Visible To and Position, Custom Color(70, 255, 110, 255), False);
\t\tEnd;
\t\tEvent Player.IkonKartuNasib = Last Created Entity;
\t\tModify Player Variable(Event Player, PutaranKartuNasib, Subtract, 1);'''
source = replace_in_rule(
    source,
    "18e - Nasib:",
    old_tick,
    "\t\tEvent Player.KartuNasibMerah = Event Player.KartuNasibMerah == False;\n\t\tModify Player Variable(Event Player, PutaranKartuNasib, Subtract, 1);",
    "persistent icon tick",
)

# End-of-roulette cleanup and camera restore if the owner survived.
old_cleanup = '''\t\tIf(Event Player.TeksKartuNasib != Null);
\t\t\tDestroy In-World Text(Event Player.TeksKartuNasib);
\t\tEnd;
\t\tIf(Event Player.IkonKartuNasib != Null);
\t\t\tDestroy Icon(Event Player.IkonKartuNasib);
\t\tEnd;
\t\tEvent Player.TeksKartuNasib = Null;
\t\tEvent Player.IkonKartuNasib = Null;
\t\tEvent Player.KartuNasibAktif = False;
\t\tEvent Player.PutaranKartuNasib = 0;
\t\tEvent Player.JedaKartuNasib = 0;'''
new_cleanup = '''\t\tIf(Event Player.TeksKartuNasib != Null);
\t\t\tDestroy In-World Text(Event Player.TeksKartuNasib);
\t\tEnd;
\t\tIf(Event Player.TeksKartuNasibKanan != Null);
\t\t\tDestroy In-World Text(Event Player.TeksKartuNasibKanan);
\t\tEnd;
\t\tIf(Event Player.IkonKartuNasib != Null);
\t\t\tDestroy Icon(Event Player.IkonKartuNasib);
\t\tEnd;
\t\tIf(Event Player.IkonKartuNasibHijau != Null);
\t\t\tDestroy Icon(Event Player.IkonKartuNasibHijau);
\t\tEnd;
\t\tEvent Player.TeksKartuNasib = Null;
\t\tEvent Player.TeksKartuNasibKanan = Null;
\t\tEvent Player.IkonKartuNasib = Null;
\t\tEvent Player.IkonKartuNasibHijau = Null;
\t\tEvent Player.KartuNasibAktif = False;
\t\tEvent Player.PutaranKartuNasib = 0;
\t\tEvent Player.JedaKartuNasib = 0;
\t\tIf(And(Is Alive(Event Player) == True, Event Player.ModeKameraSebelumNasib != 0));
\t\t\tIf(Event Player.ModeKameraSebelumNasib == 1);
\t\t\t\tEvent Player.TargetKamera = Event Player;
\t\t\t\tWait(0.016, Ignore Condition);
\t\t\t\tEvent Player.ModeKamera = 1;
\t\t\t\tCall Subroutine(MulaiKamera);
\t\t\tElse If(And(Event Player.TargetKameraSebelumNasib != Null, Entity Exists(Event Player.TargetKameraSebelumNasib)));
\t\t\t\tEvent Player.TargetKamera = Event Player.TargetKameraSebelumNasib;
\t\t\t\tWait(0.016, Ignore Condition);
\t\t\t\tEvent Player.ModeKamera = 2;
\t\t\t\tCall Subroutine(MulaiKamera);
\t\t\tEnd;
\t\t\tEvent Player.ModeKameraSebelumNasib = 0;
\t\t\tEvent Player.TargetKameraSebelumNasib = Null;
\t\tEnd;'''
source = replace_in_rule(source, "18e - Nasib:", old_cleanup, new_cleanup, "roulette cleanup")

# Death-before-finish resets all visuals. Keep saved camera state for respawn restore.
old_death = '''\t\tIf(Event Player.TeksKartuNasib != Null);
\t\t\tDestroy In-World Text(Event Player.TeksKartuNasib);
\t\tEnd;
\t\tIf(Event Player.IkonKartuNasib != Null);
\t\t\tDestroy Icon(Event Player.IkonKartuNasib);
\t\tEnd;
\t\tEvent Player.TeksKartuNasib = Null;
\t\tEvent Player.IkonKartuNasib = Null;'''
new_death = '''\t\tIf(Event Player.TeksKartuNasib != Null);
\t\t\tDestroy In-World Text(Event Player.TeksKartuNasib);
\t\tEnd;
\t\tIf(Event Player.TeksKartuNasibKanan != Null);
\t\t\tDestroy In-World Text(Event Player.TeksKartuNasibKanan);
\t\tEnd;
\t\tIf(Event Player.IkonKartuNasib != Null);
\t\t\tDestroy Icon(Event Player.IkonKartuNasib);
\t\tEnd;
\t\tIf(Event Player.IkonKartuNasibHijau != Null);
\t\t\tDestroy Icon(Event Player.IkonKartuNasibHijau);
\t\tEnd;
\t\tEvent Player.TeksKartuNasib = Null;
\t\tEvent Player.TeksKartuNasibKanan = Null;
\t\tEvent Player.IkonKartuNasib = Null;
\t\tEvent Player.IkonKartuNasibHijau = Null;'''
source = replace_in_rule(source, "18f - Nasib:", old_death, new_death, "death cleanup")

# Restore saved camera after respawn if the roulette ended in death/reset.
restore_rule = r'''
rule("18g - Nasib: Pulihkan kamera setelah respawn")
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
		Event Player.KartuNasibAktif == False;
		Event Player.ModeKameraSebelumNasib != 0;
		Has Spawned(Event Player) == True;
		Is Alive(Event Player) == True;
		Event Player.ModeKamera == 0;
	}

	actions
	{
		If(Event Player.ModeKameraSebelumNasib == 1);
			Event Player.TargetKamera = Event Player;
			Wait(0.016, Ignore Condition);
			Event Player.ModeKamera = 1;
			Call Subroutine(MulaiKamera);
		Else If(And(Event Player.TargetKameraSebelumNasib != Null, Entity Exists(Event Player.TargetKameraSebelumNasib)));
			Event Player.TargetKamera = Event Player.TargetKameraSebelumNasib;
			Wait(0.016, Ignore Condition);
			Event Player.ModeKamera = 2;
			Call Subroutine(MulaiKamera);
		End;
		Event Player.ModeKameraSebelumNasib = 0;
		Event Player.TargetKameraSebelumNasib = Null;
	}
}

'''
source = replace_once(
    source,
    'rule("19 - Teleportasi Jongkok: Buka tampilan selama Jongkok ditahan")',
    restore_rule + 'rule("19 - Teleportasi Jongkok: Buka tampilan selama Jongkok ditahan")',
    "camera restore rule",
)

# Player-leave cleanup for the extra right bracket and green icon.
leave_start, leave_end, leave = rule_region(source, "04 - Pemain Keluar:")
leave_marker = "\tactions\n\t{\n"
leave_extra = '''\t\tIf(Event Player.TeksKartuNasibKanan != Null);\n\t\t\tDestroy In-World Text(Event Player.TeksKartuNasibKanan);\n\t\t\tEvent Player.TeksKartuNasibKanan = Null;\n\t\tEnd;\n\t\tIf(Event Player.IkonKartuNasibHijau != Null);\n\t\t\tDestroy Icon(Event Player.IkonKartuNasibHijau);\n\t\t\tEvent Player.IkonKartuNasibHijau = Null;\n\t\tEnd;\n'''
leave = replace_once(leave, leave_marker, leave_marker + leave_extra, "leave cleanup insertion")
source = source[:leave_start] + leave + source[leave_end:]

# Initialize new handles/state in SiapkanPemain.
source = replace_once(
    source,
    "\t\tEvent Player.TeksKartuNasib = Null;\n\t\tEvent Player.KartuNasibMerah = False;",
    "\t\tEvent Player.TeksKartuNasib = Null;\n\t\tEvent Player.TeksKartuNasibKanan = Null;\n\t\tEvent Player.IkonKartuNasib = Null;\n\t\tEvent Player.IkonKartuNasibHijau = Null;\n\t\tEvent Player.ModeKameraSebelumNasib = 0;\n\t\tEvent Player.TargetKameraSebelumNasib = Null;\n\t\tEvent Player.KartuNasibMerah = False;",
    "initialize extra luck state",
)

SOURCE.write_text(source, encoding="utf-8")

validator = VALIDATOR.read_text(encoding="utf-8")

# New player variables.
validator = replace_once(
    validator,
    '        (76, "IkonKartuNasib"),\n    ):',
    '        (76, "IkonKartuNasib"),\n        (77, "IkonKartuNasibHijau"),\n        (78, "TeksKartuNasibKanan"),\n        (79, "ModeKameraSebelumNasib"),\n        (80, "TargetKameraSebelumNasib"),\n    ):',
    "validator luck slots",
)

# Crouch + two separate luck brackets = four IWT total.
validator = replace_once(
    validator,
    '        len(call_texts(source, "Create In-World Text")), 3,\n        "due testi mondo Crouch più una carta Nasib",',
    '        len(call_texts(source, "Create In-World Text")), 4,\n        "due testi mondo Crouch più due parentesi Nasib",',
    "validator IWT count",
)

# Balas Dendam only needs a post-Wait captured-reference check if that Wait happens before Kill.
validator = replace_once(
    validator,
    '''        wait_at = claim.find("Wait(", capture + 1)
        if wait_at >= 0:
            after_wait = claim[wait_at:]
            checks.require(
                "TargetBalasDendamTerkunci" in after_wait,
                "claim BalasDendam non usa il riferimento catturato dopo il Wait",
            )
            checks.require(
                "TargetBalasDendamDipilih" not in after_wait,
                "claim BalasDendam dipende ancora dalla selezione mutevole dopo il Wait",
            )''',
    '''        wait_at = claim.find("Wait(", capture + 1)
        if 0 <= wait_at < kill_at:
            after_wait = claim[wait_at:kill_at]
            checks.require(
                "TargetBalasDendamTerkunci" in after_wait,
                "claim BalasDendam non usa il riferimento catturato dopo il Wait",
            )
            checks.require(
                "TargetBalasDendamDipilih" not in after_wait,
                "claim BalasDendam dipende ancora dalla selezione mutevole dopo il Wait",
            )''',
    "validator revenge wait scope",
)

# Replace the old single-card / recreate-every-tick checks.
start = validator.index('    card_texts = [\n        call for call in call_texts(source, "Create In-World Text")')
end = validator.index('    checks.require(\n        "Event Player.PosisiKartuNasib', start)
new_card_checks = '''    card_texts = [
        call for call in call_texts(source, "Create In-World Text")
        if "All Players(All Teams)" in call
        and ("Custom String(\\\"[\\\")" in call or "Custom String(\\\"]\\\")" in call)
    ]
    checks.equal(len(card_texts), 2, "Nasib: due parentesi world-space separate")
    if len(card_texts) == 2:
        joined = "\\n".join(card_texts)
        checks.require("Custom String(\\\"[\\\")" in joined and "Custom String(\\\"]\\\")" in joined, "Nasib: bracket sinistro/destro mancanti")
        checks.require(joined.count("* 0.300") == 2, "Nasib: bracket non distanziati fisicamente di 0,30 m")
        checks.require(joined.count("Update Every Frame(") >= 2, "Nasib: bracket non aggiornati ogni frame")
    luck_icons = [call for call in call_texts(source, "Create Icon") if ", Skull," in call or ", Heart," in call]
    checks.equal(len(luck_icons), 2, "Nasib: Heart e Skull devono essere due icone persistenti")
    if len(luck_icons) == 2:
        skull = next(call for call in luck_icons if ", Skull," in call)
        heart = next(call for call in luck_icons if ", Heart," in call)
        checks.require("Update Every Frame(" in skull and "Update Every Frame(" in heart, "Nasib: icone non agganciate client-side ogni frame")
        checks.require("Event Player.KartuNasibMerah ? All Players(All Teams) : Empty Array" in skull, "Nasib: visibilità Skull non dinamica")
        checks.require("Event Player.KartuNasibMerah ? Empty Array : All Players(All Teams)" in heart, "Nasib: visibilità Heart non dinamica")
        checks.require("Custom Color(255, 70, 70, 255)" in skull, "Nasib: Skull non rosso")
        checks.require("Custom Color(70, 255, 110, 255)" in heart, "Nasib: Heart non verde")
    if luck:
        pre_loop = mask_strings(luck[0].body).split("Loop If Condition Is True;")[0]
        checks.require("Create Icon(" not in pre_loop and "Destroy Icon(" not in pre_loop, "Nasib: icone ancora ricreate durante i tick")
    checks.require(
        "Destroy Icon(Event Player.IkonKartuNasib);" in clean
        and "Destroy Icon(Event Player.IkonKartuNasibHijau);" in clean,
        "Nasib: cleanup icone persistenti incompleto",
    )

'''
validator = validator[:start] + new_card_checks + validator[end:]

# Death cleanup must include all new visuals.
validator = replace_once(
    validator,
    '                "Destroy In-World Text(Event Player.TeksKartuNasib);",\n                "Destroy Icon(Event Player.IkonKartuNasib);",\n                "Event Player.IkonKartuNasib = Null;",',
    '                "Destroy In-World Text(Event Player.TeksKartuNasib);",\n                "Destroy In-World Text(Event Player.TeksKartuNasibKanan);",\n                "Destroy Icon(Event Player.IkonKartuNasib);",\n                "Destroy Icon(Event Player.IkonKartuNasibHijau);",\n                "Event Player.IkonKartuNasib = Null;",\n                "Event Player.IkonKartuNasibHijau = Null;",',
    "validator death cleanup",
)

# Ensure first-person lock and restore rule are present.
menu_marker = '    blocked_one_hp = menu_interact['
restore_checks = '''    checks.require(
        "Event Player.ModeKameraSebelumNasib = Event Player.ModeKamera;" in menu_interact
        and "Stop Camera(Event Player);" in menu_interact
        and "Event Player.ModeKamera = 0;" in menu_interact,
        "Nasib: camera non viene temporaneamente bloccata in prima persona",
    )
    restore_rules = [rule for rule in rules if rule.name.startswith("18g - Nasib:")]
    checks.equal(len(restore_rules), 1, "Nasib: una sola regola ripristino camera dopo respawn")
    if restore_rules:
        checks.require(
            code_contains(restore_rules[0].body, "ModeKameraSebelumNasib", "Call Subroutine(MulaiKamera);"),
            "Nasib: ripristino camera incompleto",
        )

'''
validator = replace_once(validator, menu_marker, restore_checks + menu_marker, "validator camera lock restore")
VALIDATOR.write_text(validator, encoding="utf-8")

# Documentation and recorded blob.
project = PROJECT.read_text(encoding="utf-8")
project = re.sub(
    r"Interact crea una carta virtuale agganciata al mirino.*?La roulette parte con colore casuale, esegue 20\.\.24 cambi e parte da 0,08 s aggiungendo 0,055 s a ogni passaggio, quindi dura sensibilmente più a lungo e rallenta progressivamente\.",
    "Interact crea una carta virtuale centrata sul mirino e visibile a tutti. Durante la roulette l'eventuale camera custom viene temporaneamente sospesa per usare la prima persona, poi ripristinata se il player sopravvive o al respawn. Le parentesi sono due In-World Text distinti posti fisicamente a ±0,30 m dal centro, quindi la loro apertura non dipende dagli spazi del font. Heart e Skull sono due Create Icon persistenti, entrambi con posizione racchiusa in Update Every Frame; il cambio rosso/verde alterna soltanto la visibilità, senza Destroy/Create per tick. La roulette resta a 20..24 cambi con intervallo iniziale 0,08 s e +0,055 s per passaggio.",
    project,
    count=1,
    flags=re.DOTALL,
)
PROJECT.write_text(project, encoding="utf-8")

validation = VALIDATION.read_text(encoding="utf-8")
validation = re.sub(
    r"- Menu 10 Try Your Luck: .*?esito 50/50;",
    "- Menu 10 Try Your Luck: due bracket separati a ±0,30 m, Heart/Skull persistenti con Update Every Frame, prima persona temporanea e ripristino camera, Unkillable OFF, menu bloccato, reset alla morte, verde cura completa, rosso uccide dopo countdown 3 s, esito 50/50;",
    validation,
    count=1,
)
new_blob = git_blob_sha(SOURCE)
validation, count = re.subn(
    r"(?s)(Blob Git del sorgente Workshop validato:\s*```text\s*)[0-9a-f]{40}(\s*```)",
    rf"\g<1>{new_blob}\g<2>",
    validation,
    count=1,
)
if count != 1:
    raise RuntimeError("validation blob not found")
VALIDATION.write_text(validation, encoding="utf-8")
