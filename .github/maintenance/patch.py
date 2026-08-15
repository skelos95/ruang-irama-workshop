from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
PROJECT = ROOT / "docs" / "PROGETTO.md"
VALIDATION = ROOT / "docs" / "VALIDAZIONE.md"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one occurrence, found {count}")
    return text.replace(old, new, 1)


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    return hashlib.sha1(payload).hexdigest()


source = SOURCE.read_text(encoding="utf-8")

# Roulette state.
source = replace_once(
    source,
    "\t\t70: KartuNasibAktif\n\t\t71: PosisiKartuNasib\n\t\t72: TeksKartuNasib\n",
    "\t\t70: KartuNasibAktif\n\t\t71: PosisiKartuNasib\n\t\t72: TeksKartuNasib\n\t\t73: KartuNasibMerah\n\t\t74: PutaranKartuNasib\n\t\t75: JedaKartuNasib\n",
    "roulette variables",
)

# Menu 10 now starts the roulette immediately; no shooting interaction remains.
source = replace_once(
    source,
    'Small Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("A luck card is already active. Close the menu and shoot it first.") : Event Player.IndeksBahasa == 1 ? Custom String("Kartu nasib masih aktif. Tutup menu lalu tembak dulu.") : Custom String("การ์ดเสี่ยงโชคยังทำงานอยู่ ปิดเมนูแล้วค่อยยิงมันก่อน"));',
    'Small Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("The luck card is already rolling. Wait for the result.") : Event Player.IndeksBahasa == 1 ? Custom String("Kartu nasib sedang berputar. Tunggu hasilnya.") : Custom String("การ์ดเสี่ยงโชคกำลังสุ่มอยู่ รอผลก่อน"));',
    "active roulette message",
)
source = replace_once(
    source,
    "\t\t\t\tEvent Player.KartuNasibAktif = True;\n\t\t\t\tEvent Player.PosisiKartuNasib = Position Of(Event Player) + Direction From Angles(Horizontal Facing Angle Of(Event Player), 0) * 2.500 - Vector(0, 0.450, 0);",
    "\t\t\t\tEvent Player.KartuNasibAktif = True;\n\t\t\t\tEvent Player.KartuNasibMerah = Random Integer(0, 1) == 0;\n\t\t\t\tEvent Player.PutaranKartuNasib = Random Integer(12, 16);\n\t\t\t\tEvent Player.JedaKartuNasib = 0.080;\n\t\t\t\tEvent Player.PosisiKartuNasib = Position Of(Event Player) + Direction From Angles(Horizontal Facing Angle Of(Event Player), 0) * 2.500 - Vector(0, 0.450, 0);",
    "roulette initialization",
)
source = replace_once(
    source,
    'Create In-World Text(All Players(All Teams), Player Variable(Local Player, IndeksBahasa) == 0 ? Custom String("[ ? ]\\nTRY YOUR LUCK\\nSHOOT ME") : Player Variable(Local Player, IndeksBahasa) == 1 ? Custom String("[ ? ]\\nCOBA NASIB\\nTEMBAK") : Custom String("[ ? ]\\nเสี่ยงโชค\\nยิงเลย"), Event Player.PosisiKartuNasib, 3.500, Do Not Clip, Visible To Position String and Color, Global.RGB, Visible Never);',
    'Create In-World Text(All Players(All Teams), Player Variable(Local Player, IndeksBahasa) == 0 ? Custom String("[ ? ]\\nTRY YOUR LUCK") : Player Variable(Local Player, IndeksBahasa) == 1 ? Custom String("[ ? ]\\nCOBA NASIB") : Custom String("[ ? ]\\nเสี่ยงโชค"), Event Player.PosisiKartuNasib, 3.500, Do Not Clip, Visible To Position String and Color, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Visible Never);',
    "roulette dynamic card color",
)
source = replace_once(
    source,
    "Play Effect(All Players(All Teams), Ring Explosion, Global.RGB, Event Player.PosisiKartuNasib + Vector(0, 0.450, 0), 3);",
    "Play Effect(All Players(All Teams), Ring Explosion, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Event Player.PosisiKartuNasib + Vector(0, 0.450, 0), 3);",
    "roulette spawn effect color",
)
source = replace_once(
    source,
    'Small Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Luck card created. Close the menu and shoot it to reveal your fate.") : Event Player.IndeksBahasa == 1 ? Custom String("Kartu nasib dibuat. Tutup menu lalu tembak untuk melihat nasibmu.") : Custom String("สร้างการ์ดเสี่ยงโชคแล้ว ปิดเมนูแล้วยิงเพื่อดูชะตาของคุณ"));',
    'Small Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Luck roulette started. Red or green?") : Event Player.IndeksBahasa == 1 ? Custom String("Roulette nasib dimulai. Merah atau hijau?") : Custom String("เริ่มรูเล็ตเสี่ยงโชคแล้ว แดงหรือเขียว?"));',
    "roulette start message",
)

old_rule = r'''rule("18e - Nasib: Pemilik menembak kartu sendiri")
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
		Event Player.KartuNasibAktif == True;
		Event Player.MenuTerbuka == False;
		Has Spawned(Event Player) == True;
		Is Alive(Event Player) == True;
		Is Firing Primary(Event Player) == True;
		Distance Between(Event Player.PosisiKartuNasib, Eye Position(Event Player) + Facing Direction Of(Event Player) * Distance Between(Eye Position(Event Player), Event Player.PosisiKartuNasib)) <= 1.250;
		Is In Line of Sight(Eye Position(Event Player), Event Player.PosisiKartuNasib, All Barriers Block LOS) == True;
	}

	actions
	{
		Stop Chasing Player Variable(Event Player, PosisiKartuNasib);
		If(Event Player.TeksKartuNasib != Null);
			Destroy In-World Text(Event Player.TeksKartuNasib);
		End;
		Event Player.TeksKartuNasib = Null;
		Event Player.KartuNasibAktif = False;
		Play Effect(All Players(All Teams), Ring Explosion, Global.RGB, Event Player.PosisiKartuNasib, 3);
		If(Random Integer(0, 1) == 0);
			Set Player Health(Event Player, Max Health(Event Player));
			Small Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("LUCK! Full health restored.") : Event Player.IndeksBahasa == 1 ? Custom String("BERUNTUNG! Kesehatan penuh dipulihkan.") : Custom String("โชคดี! ฟื้นพลังชีวิตเต็มแล้ว"));
		Else;
			Small Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("BAD LUCK! The card chose death.") : Event Player.IndeksBahasa == 1 ? Custom String("SIAL! Kartunya memilih kematian.") : Custom String("โชคร้าย! การ์ดเลือกความตาย"));
			Clear Status(Event Player, Unkillable);
			Kill(Event Player, Null);
		End;
	}
}
'''
new_rule = r'''rule("18e - Nasib: Roulette merah hijau makin lambat")
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
		Event Player.KartuNasibAktif == True;
		Event Player.PutaranKartuNasib > 0;
		Has Spawned(Event Player) == True;
		Is Alive(Event Player) == True;
	}

	actions
	{
		Wait(Event Player.JedaKartuNasib, Abort When False);
		Event Player.KartuNasibMerah = Event Player.KartuNasibMerah == False;
		Modify Player Variable(Event Player, PutaranKartuNasib, Subtract, 1);
		Play Effect(All Players(All Teams), Ring Explosion, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Event Player.PosisiKartuNasib, 1.500);
		Modify Player Variable(Event Player, JedaKartuNasib, Add, 0.055);
		Loop If Condition Is True;
		Stop Chasing Player Variable(Event Player, PosisiKartuNasib);
		If(Event Player.KartuNasibMerah == True);
			Small Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("RED! Death in 3...") : Event Player.IndeksBahasa == 1 ? Custom String("MERAH! Mati dalam 3...") : Custom String("แดง! ตายใน 3..."));
			Wait(1, Abort When False);
			Small Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("RED! Death in 2...") : Event Player.IndeksBahasa == 1 ? Custom String("MERAH! Mati dalam 2...") : Custom String("แดง! ตายใน 2..."));
			Wait(1, Abort When False);
			Small Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("RED! Death in 1...") : Event Player.IndeksBahasa == 1 ? Custom String("MERAH! Mati dalam 1...") : Custom String("แดง! ตายใน 1..."));
			Wait(1, Abort When False);
			Clear Status(Event Player, Unkillable);
			Kill(Event Player, Null);
		Else;
			Set Player Health(Event Player, Max Health(Event Player));
			Small Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("GREEN! Full health restored.") : Event Player.IndeksBahasa == 1 ? Custom String("HIJAU! Kesehatan penuh dipulihkan.") : Custom String("เขียว! ฟื้นพลังชีวิตเต็มแล้ว"));
			Wait(1.500, Abort When False);
		End;
		If(Event Player.TeksKartuNasib != Null);
			Destroy In-World Text(Event Player.TeksKartuNasib);
		End;
		Event Player.TeksKartuNasib = Null;
		Event Player.KartuNasibAktif = False;
		Event Player.PutaranKartuNasib = 0;
		Event Player.JedaKartuNasib = 0;
	}
}
'''
source = replace_once(source, old_rule, new_rule, "replace shooting rule with roulette")

# Initialize/reset roulette state explicitly.
source = replace_once(
    source,
    "\t\tEvent Player.KartuNasibAktif = False;\n\t\tEvent Player.PosisiKartuNasib = Vector(0, 0, 0);\n\t\tEvent Player.TeksKartuNasib = Null;",
    "\t\tEvent Player.KartuNasibAktif = False;\n\t\tEvent Player.PosisiKartuNasib = Vector(0, 0, 0);\n\t\tEvent Player.TeksKartuNasib = Null;\n\t\tEvent Player.KartuNasibMerah = False;\n\t\tEvent Player.PutaranKartuNasib = 0;\n\t\tEvent Player.JedaKartuNasib = 0;",
    "roulette player initialization",
)

# Menu 10 HUD describes an automatic roulette rather than a shootable target.
source = replace_once(
    source,
    'Event Player.KartuNasibAktif ? Custom String("SHOOT YOUR CARD") : Custom String("CREATE CARD")',
    'Event Player.KartuNasibAktif ? Custom String("WATCH THE ROULETTE") : Custom String("START ROULETTE")',
    "English Menu 10 action",
)
source = replace_once(
    source,
    'Event Player.KartuNasibAktif ? Custom String("TEMBAK KARTUMU") : Custom String("BUAT KARTU")',
    'Event Player.KartuNasibAktif ? Custom String("LIHAT ROULETTE") : Custom String("MULAI ROULETTE")',
    "Indonesian Menu 10 action",
)
source = replace_once(
    source,
    'Event Player.KartuNasibAktif ? Custom String("ยิงการ์ดของคุณ") : Custom String("สร้างการ์ด")',
    'Event Player.KartuNasibAktif ? Custom String("ดูรูเล็ต") : Custom String("เริ่มรูเล็ต")',
    "Thai Menu 10 action",
)

SOURCE.write_text(source, encoding="utf-8")

# Validator: certify the slowing automatic red/green roulette and reject the old shooting path.
validator = VALIDATOR.read_text(encoding="utf-8")
old_validation = '''    luck = [
        rule for rule in rules
        if code_contains(
            rule.body,
            "Event Player.KartuNasibAktif == True;",
            "Is Firing Primary(Event Player) == True;",
            "Distance Between(Event Player.PosisiKartuNasib, Eye Position(Event Player) + Facing Direction Of(Event Player) * Distance Between(Eye Position(Event Player), Event Player.PosisiKartuNasib)) <= 1.250;",
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
'''
new_validation = '''    luck = [
        rule for rule in rules
        if code_contains(
            rule.body,
            "Event Player.KartuNasibAktif == True;",
            "Event Player.PutaranKartuNasib > 0;",
            "Wait(Event Player.JedaKartuNasib, Abort When False);",
            "Event Player.KartuNasibMerah = Event Player.KartuNasibMerah == False;",
            "Modify Player Variable(Event Player, PutaranKartuNasib, Subtract, 1);",
            "Modify Player Variable(Event Player, JedaKartuNasib, Add, 0.055);",
            "Loop If Condition Is True;",
            "Event Player.KartuNasibMerah == True",
            "Set Player Health(Event Player, Max Health(Event Player));",
            "Clear Status(Event Player, Unkillable);",
            "Kill(Event Player, Null);",
        )
    ]
    checks.equal(len(luck), 1, "Nasib: una sola roulette automatica rosso/verde")
    if luck:
        luck_code = mask_strings(luck[0].body)
        checks.equal(
            len(call_texts(luck[0].body, "Play Effect")),
            1,
            "Nasib: un solo Ring riutilizzato a ogni cambio colore",
        )
        checks.require("Is Firing Primary" not in luck_code, "Nasib: il vecchio sparo non deve più attivare la carta")
        checks.require("Is In Line of Sight" not in luck_code, "Nasib: la roulette non deve dipendere dalla linea di vista")
        checks.require(luck_code.count("Wait(1, Abort When False);") == 3, "Nasib: countdown rosso deve durare tre secondi")
'''
validator = replace_once(validator, old_validation, new_validation, "validator automatic roulette")
validator = replace_once(
    validator,
    '    if card_texts:\n        checks.require(\n            "Event Player.PosisiKartuNasib, 3.500, Do Not Clip" in card_texts[0],\n            "Nasib: la carta pubblica deve usare dimensione 3,5",\n        )',
    '    if card_texts:\n        checks.require(\n            "Event Player.PosisiKartuNasib, 3.500, Do Not Clip" in card_texts[0],\n            "Nasib: la carta pubblica deve usare dimensione 3,5",\n        )\n        checks.require(\n            "Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255)" in card_texts[0],\n            "Nasib: il testo mondo non cambia dinamicamente rosso/verde",\n        )',
    "validator dynamic roulette color",
)
validator = replace_once(
    validator,
    '    if luck:\n        checks.require(\n            "Angle Between Vectors(" not in mask_strings(luck[0].body),\n            "Nasib: il vecchio test angolare fragile non deve restare nella risoluzione",\n        )',
    '    checks.require(\n        "Event Player.KartuNasibMerah = Random Integer(0, 1) == 0;" in clean\n        and "Event Player.PutaranKartuNasib = Random Integer(12, 16);" in clean\n        and "Event Player.JedaKartuNasib = 0.080;" in clean,\n        "Nasib: inizializzazione casuale 50/50 e 12..16 passaggi assente",\n    )',
    "validator roulette initialization",
)
VALIDATOR.write_text(validator, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
project = replace_once(
    project,
    "Interact crea 2,5 m davanti al giocatore una carta virtuale che emerge dal terreno con un `Ring Explosion`. La posizione è calcolata direttamente dal piano dei piedi del proprietario, senza `Nearest Walkable Position`, per evitare agganci a piani superiori. Il testo sale da 0,45 m sotto il suolo fino a circa 0,55 m sopra e usa dimensione 3,5. La carta usa `Create In-World Text`, è visibile a tutti e non occupa slot bot. Ogni giocatore può avere una sola carta attiva.",
    "Interact crea 2,5 m davanti al giocatore una carta virtuale che emerge dal terreno con un `Ring Explosion`. La posizione resta calcolata dal piano dei piedi del proprietario e il testo usa dimensione 3,5. Appena compare, la carta avvia automaticamente una roulette rosso/verde: il colore iniziale è casuale, esegue 12..16 cambi e parte con intervallo 0,08 s aggiungendo 0,055 s a ogni passaggio, quindi rallenta progressivamente. La carta è visibile a tutti e non occupa slot bot.",
    "project roulette behavior",
)
project = replace_once(
    project,
    "L'attivazione è proprietario-only: la regola legge esclusivamente `KartuNasibAktif` e `PosisiKartuNasib` dell'`Event Player`, richiede `Is Firing Primary`, una hitbox virtuale di 1,25 m attorno al punto attraversato dal reticolo alla distanza della carta e linea di vista libera. Il vecchio limite angolare fisso da 7° è stato rimosso. Al colpo estrae `Random Integer(0, 1)`: un esito ripristina la salute massima, l'altro forza la morte del proprietario. Testo e stato vengono ripuliti anche alla morte o all'uscita del giocatore.",
    "Non serve più sparare. Quando la roulette termina, il colore finale decide l'esito: verde ripristina immediatamente la salute massima; rosso mantiene la carta rossa e mostra un countdown di 3 secondi, poi rimuove `Unkillable` e uccide il proprietario. Poiché colore iniziale e numero di cambi sono indipendenti, l'esito finale resta 50/50. Testo e stato vengono ripuliti anche alla morte o all'uscita del giocatore.",
    "project roulette outcome",
)
PROJECT.write_text(project, encoding="utf-8")

validation = VALIDATION.read_text(encoding="utf-8")
old_blob = "c267f266aac75091ac23ea2320f60ebbc9790f39"
new_blob = git_blob_sha(SOURCE)
validation = replace_once(validation, old_blob, new_blob, "validation Workshop blob")
validation = replace_once(
    validation,
    "- Menu 10 Try Your Luck: carta pubblica bassa/grande, hitbox reticolo 1,25 m solo proprietario, esito 50/50;",
    "- Menu 10 Try Your Luck: roulette automatica rosso/verde progressivamente più lenta, verde cura completa, rosso uccide dopo countdown 3 s, esito 50/50;",
    "validation roulette note",
)
VALIDATION.write_text(validation, encoding="utf-8")
