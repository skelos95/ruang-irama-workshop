#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"


def git_blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def matching_brace(text: str, opening: int) -> int:
    depth = 1
    in_string = False
    escaped = False
    for i in range(opening + 1, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
    raise RuntimeError("graffa rule non chiusa")


def replace_rule(text: str, prefix: str, new_rule: str) -> str:
    marker = f'rule("{prefix}'
    start = text.find(marker)
    if start < 0:
        raise RuntimeError(f"rule non trovata: {prefix}")
    opening = text.find("{", start)
    end = matching_brace(text, opening) + 1
    return text[:start] + new_rule.rstrip() + text[end:]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: atteso 1 match, trovati {count}")
    return text.replace(old, new, 1)


source = SOURCE.read_text(encoding="utf-8")
validator = VALIDATOR.read_text(encoding="utf-8")

# 1) Accelerazione guidata dalla mira: 10 secondi.
source = replace_once(
    source,
    '\t\t\tStart Accelerating(Event Player, Facing Direction Of(Event Player), 50, 25, To World, Direction Rate and Max Speed);\n\t\t\tEvent Player.EfekNasibBerakhir = Total Time Elapsed + 5;\n\t\t\tSmall Message(Event Player, Custom String("TRY YOUR LUCK: AIM-STEERED ACCELERATION — 5s"));',
    '\t\t\tStart Accelerating(Event Player, Facing Direction Of(Event Player), 50, 25, To World, Direction Rate and Max Speed);\n\t\t\tEvent Player.EfekNasibBerakhir = Total Time Elapsed + 10;\n\t\t\tSmall Message(Event Player, Custom String("TRY YOUR LUCK: AIM-STEERED ACCELERATION — 10s"));',
    "durata accelerazione",
)

# 2) Cambio team/uscita: reset immediato Try Your Luck prima dei Wait del lifecycle.
quiet_rule = r'''rule("93b2 - Subrutin: Tenangkan trigger sebelum cleanup")
{
	event
	{
		Subroutine;
		TenangkanPemain;
	}

	actions
	{
		"Reset Try Your Luck immediato prima della re-registrazione del team; nessun Wait o Loop in questa sezione."
		If(Or(Event Player.KartuNasibAktif == True, Or(Event Player.PutaranKartuNasib > 0, Event Player.EfekNasib != 0)) == True);
			If(Event Player.IkonKartuNasib != Null);
				Destroy Icon(Event Player.IkonKartuNasib);
			End;
			If(Event Player.IkonKartuNasibHijau != Null);
				Destroy Icon(Event Player.IkonKartuNasibHijau);
			End;
			If(Event Player.HudEfekNasib != Null);
				Destroy HUD Text(Event Player.HudEfekNasib);
			End;
			If(Event Player.IkonKebal != Null);
				Destroy Icon(Event Player.IkonKebal);
			End;
			If(Event Player.EfekNasibCahaya != Null);
				Destroy Effect(Event Player.EfekNasibCahaya);
			End;
			If(Event Player.EfekNasibLingkaran != Null);
				Destroy Effect(Event Player.EfekNasibLingkaran);
			End;
			Clear Status(Event Player, Hacked);
			Clear Status(Event Player, Unkillable);
			Stop Accelerating(Event Player);
			Enable Movement Collision With Environment(Event Player);
			Set Damage Received(Event Player, 100);
			Set Move Speed(Event Player, 100);
			Set Jump Vertical Speed(Event Player, 100);
			Set Projectile Speed(Event Player, 100);
			Set Gravity(Event Player, 100);
			Event Player.KebalAktif = False;
			Event Player.ModeKebal = 0;
			Event Player.KursorKebal = 0;
			Event Player.ModeKebalTerakhir = 0;
			Event Player.IkonKebal = Null;
			Event Player.IkonKartuNasib = Null;
			Event Player.IkonKartuNasibHijau = Null;
			Event Player.HudEfekNasib = Null;
			Event Player.EfekNasibCahaya = Null;
			Event Player.EfekNasibLingkaran = Null;
			Event Player.RadiusNasib = 0;
			Event Player.GerakNasibDikunci = False;
			Event Player.KartuNasibAktif = False;
			Event Player.KartuNasibMerah = False;
			Event Player.PutaranKartuNasib = 0;
			Event Player.JedaKartuNasib = 0;
			Event Player.EfekNasib = 0;
			Event Player.EfekNasibBerakhir = 0;
			Event Player.DaftarTujuanNasib = Empty Array;
			Event Player.TujuanNasib = Vector(0, 0, 0);
			Event Player.ArahNasib = Vector(0, 0, 0);
			Event Player.PrivasiNasibAktif = False;
			Event Player.KategoriTeleportNasib = -1;
			Event Player.HasilNasibTerkunci = 0;
			Event Player.MenuNasibHarusDibuka = False;
		End;
		"Spegni i trigger prima che Player Left/Joined completi il cleanup e la nuova registrazione."
		Event Player.SudahSiap = False;
		Event Player.Manusia = False;
		Event Player.PerintahMenu = 0;
		Event Player.InputMenuDikunci = False;
		Event Player.SeranganDekatDipakai = False;
		Event Player.MenuTerbuka = False;
		Event Player.TeleportasiJongkokAktif = False;
		Event Player.PerintahTeleportasi = 0;
		Event Player.InspeksiAktif = False;
		Event Player.TargetInspeksi = Null;
		Event Player.InteraksiKameraDipakai = False;
		Event Player.KartuNasibAktif = False;
		Event Player.PutaranKartuNasib = 0;
	}
}'''
source = replace_rule(source, "93b2 - Subrutin:", quiet_rule)

# 3) HUD effetto: tutto nel campo Text, una riga vuota dopo TRY YOUR LUCK, colore RGB globale.
effect_hud_rule = r'''rule("18k - Nasib: HUD effetto e durata mentre il menu e chiuso")
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
		Event Player.PutaranKartuNasib == 0;
		Or(Event Player.EfekNasibBerakhir > 0, Event Player.EfekNasib == 7) == True;
		Event Player.HudEfekNasib == Null;
		Is Alive(Event Player) == True;
	}

	actions
	{
		Create HUD Text(Event Player, Null, Null, Custom String("TRY YOUR LUCK\n \n{0}\n{1}",
			Event Player.EfekNasib == 1 ? Custom String("HACKED")
			: Event Player.EfekNasib == 2 ? Custom String("ULTIMATE ALWAYS READY")
			: Event Player.EfekNasib == 4 ? Custom String("MOVE / JUMP / PROJECTILE x2")
			: Event Player.EfekNasib == 5 ? Custom String("GRAVITY 10% / PROJECTILE 10%")
			: Event Player.EfekNasib == 6 ? Custom String("VISION: ALL PLAYER / BOT NAMES")
			: Event Player.EfekNasib == 7 ? Custom String("FLOOR REMOVED")
			: Custom String("AIM-STEERED ACCELERATION"),
			Event Player.EfekNasib == 7 ? Custom String("UNTIL DEATH") : Custom String("{0}s REMAINING",
				Max(0, Round To Integer(Event Player.EfekNasibBerakhir - Total Time Elapsed, Up)))), Top, 100,
			Color(White), Color(White), Global.RGB, Visible To String and Color, Visible Never);
		Event Player.HudEfekNasib = Last Text ID;
	}
}'''
source = replace_rule(source, "18k - Nasib:", effect_hud_rule)

# Validator: accelerazione 10 s.
validator = replace_once(
    validator,
    'checks.require("AIM-STEERED ACCELERATION — 5s" in luck.body, "Accelerazione Try Your Luck non è etichettata come guidata dalla mira")',
    'checks.require("AIM-STEERED ACCELERATION — 10s" in luck.body and "Event Player.EfekNasibBerakhir = Total Time Elapsed + 10;" in luck.body, "Accelerazione Try Your Luck non dura 10 secondi o non è guidata dalla mira")',
    "validator accelerazione 10s",
)

# Validator: HUD esclusivamente Text + RGB globale.
validator = replace_once(
    validator,
    '        checks.require(\'Create HUD Text(Event Player, Custom String("TRY YOUR LUCK")\' in luck_effect_hud.body, "18k non crea HUD effetto")\n        checks.require("EfekNasibBerakhir - Total Time Elapsed" in luck_effect_hud.body and "s REMAINING" in luck_effect_hud.body, "18k non mostra countdown")\n        checks.require("UNTIL DEATH" in luck_effect_hud.body, "18k non mostra durata floor removed")',
    '        checks.require(\'Create HUD Text(Event Player, Null, Null, Custom String("TRY YOUR LUCK\\\\n \\\\n{0}\\\\n{1}"\' in luck_effect_hud.body, "18k deve usare solo il campo Text con spazio dopo TRY YOUR LUCK")\n        checks.require("EfekNasibBerakhir - Total Time Elapsed" in luck_effect_hud.body and "s REMAINING" in luck_effect_hud.body, "18k non mostra countdown")\n        checks.require("UNTIL DEATH" in luck_effect_hud.body, "18k non mostra durata floor removed")\n        checks.require("Color(White), Color(White), Global.RGB, Visible To String and Color" in luck_effect_hud.body, "18k testo effetto non usa Global.RGB")',
    "validator HUD testo RGB",
)

# Validator: il cambio team deve pulire Try Your Luck prima dei Wait del lifecycle.
anchor = '    if fast_manager:\n'
quiet_checks = '''    quiet_player = find_rule(rules, "93b2 - Subrutin:")\n    checks.require(quiet_player is not None, "TenangkanPemain assente")\n    if quiet_player:\n        checks.require("Wait(" not in quiet_player.body and "Loop If Condition Is True;" not in quiet_player.body, "TenangkanPemain deve pulire il cambio team senza Wait o Loop")\n        for token in (\n            "Destroy Icon(Event Player.IkonKartuNasib);",\n            "Destroy HUD Text(Event Player.HudEfekNasib);",\n            "Clear Status(Event Player, Hacked);",\n            "Clear Status(Event Player, Unkillable);",\n            "Stop Accelerating(Event Player);",\n            "Enable Movement Collision With Environment(Event Player);",\n            "Set Damage Received(Event Player, 100);",\n            "Set Move Speed(Event Player, 100);",\n            "Set Jump Vertical Speed(Event Player, 100);",\n            "Set Projectile Speed(Event Player, 100);",\n            "Set Gravity(Event Player, 100);",\n            "Event Player.KebalAktif = False;",\n            "Event Player.ModeKebal = 0;",\n            "Event Player.KartuNasibAktif = False;",\n            "Event Player.EfekNasib = 0;",\n            "Event Player.MenuNasibHarusDibuka = False;",\n        ):\n            checks.require(token in quiet_player.body, f"cambio team non ripulisce Try Your Luck: {token}")\n'''
if anchor not in validator:
    raise RuntimeError("anchor fast_manager validator non trovato")
validator = validator.replace(anchor, quiet_checks + anchor, 1)

blob = git_blob_sha(source)
validator, n = re.subn(r'EXPECTED_SOURCE_BLOB = "[0-9a-f]{40}"', f'EXPECTED_SOURCE_BLOB = "{blob}"', validator, count=1)
if n != 1:
    raise RuntimeError("EXPECTED_SOURCE_BLOB non aggiornato")

SOURCE.write_text(source, encoding="utf-8")
VALIDATOR.write_text(validator, encoding="utf-8")
print(f"patched source blob: {blob}")
