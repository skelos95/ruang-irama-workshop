#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
ERROR = ROOT / ".github" / "maintenance" / "last-patch-error.txt"


def git_blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: atteso 1 match, trovati {count}")
    return text.replace(old, new, 1)


def replace_span(text: str, start: str, end: str, replacement: str, label: str) -> str:
    a = text.find(start)
    if a < 0:
        raise RuntimeError(f"{label}: start non trovato")
    b = text.find(end, a + len(start))
    if b < 0:
        raise RuntimeError(f"{label}: end non trovato")
    return text[:a] + replacement + text[b:]


def transform(source: str, validator: str) -> tuple[str, str, str]:
    # Il vecchio scratch Ultimate diventa il timestamp del prossimo tick Burning.
    source = source.replace("HasilNasibTerkunci", "TickBurnNasib")

    # Avvio roulette: cinque risultati, non dieci.
    source = source.replace("Event Player.EfekNasib = Random Integer(1, 10);", "Event Player.EfekNasib = Random Integer(1, 5);")
    source = source.replace("Try Your Luck: ten outcomes are rolling.", "Try Your Luck: five outcomes are rolling.")
    source = source.replace("Try Your Luck: sepuluh hasil sedang diacak.", "Try Your Luck: lima hasil sedang diacak.")
    source = source.replace("Try Your Luck: กำลังสุ่มสิบผลลัพธ์", "Try Your Luck: กำลังสุ่มห้าผลลัพธ์")

    luck_rule = r'''rule("18e - Nasib: Roulette lima efek con risultato bloccato")
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
		If(Event Player.IkonKartuNasib != Null);
			Destroy Icon(Event Player.IkonKartuNasib);
		End;
		Event Player.EfekNasib = Random Integer(1, 5);
		If(Event Player.EfekNasib == 1);
			Create Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Eye, Visible To and Position, Color(Aqua), False);
		Else If(Event Player.EfekNasib == 2);
			Create Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Dizzy, Visible To and Position, Color(Violet), False);
		Else If(Event Player.EfekNasib == 3);
			Create Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Skull, Visible To and Position, Custom Color(255, 70, 70, 255), False);
		Else If(Event Player.EfekNasib == 4);
			Create Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Heart, Visible To and Position, Custom Color(70, 255, 110, 255), False);
		Else;
			Create Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Fire, Visible To and Position, Color(Orange), False);
		End;
		Event Player.IkonKartuNasib = Last Created Entity;
		Wait(Event Player.JedaKartuNasib, Abort When False);
		Modify Player Variable(Event Player, PutaranKartuNasib, Subtract, 1);
		Modify Player Variable(Event Player, JedaKartuNasib, Add, 0.045);
		Loop If Condition Is True;

		"Roulette selesai: lepaskan proteksi sementara dan kembalikan pilihan Unkillable sebelum menerapkan hasil."
		Clear Status(Event Player, Unkillable);
		Event Player.ModeKebal = Event Player.ModeKebalTerakhir;
		Event Player.KursorKebal = Event Player.ModeKebalTerakhir;
		If(Event Player.ModeKebalTerakhir == 0);
			Event Player.KebalAktif = False;
			Set Damage Received(Event Player, 100);
		Else;
			Event Player.KebalAktif = True;
			Set Status(Event Player, Null, Unkillable, 9999);
			If(Event Player.ModeKebalTerakhir == 1);
				Set Damage Received(Event Player, 100);
				Set Player Health(Event Player, 1);
			Else;
				Set Damage Received(Event Player, 0);
				Set Player Health(Event Player, Max Health(Event Player));
			End;
		End;
		If(Event Player.IkonKebal != Null);
			Destroy Icon(Event Player.IkonKebal);
			Event Player.IkonKebal = Null;
		End;
		If(Event Player.KebalAktif == True);
			If(Event Player.ModeKebal == 1);
				Create Icon(All Players(All Teams), Event Player, Warning, Visible To and Position, Custom Color(255, 80, 80, 255), True);
			Else;
				Create Icon(All Players(All Teams), Event Player, Halo, Visible To and Position, Global.RGB, True);
			End;
			Event Player.IkonKebal = Last Created Entity;
		End;
		Event Player.MenuNasibHarusDibuka = False;
		Call Subroutine(TutupMenu);
		Event Player.EfekNasibBerakhir = 0;
		Event Player.TickBurnNasib = 0;

		If(Event Player.EfekNasib == 1);
			Event Player.PrivasiNasibAktif = True;
			Event Player.EfekNasibBerakhir = Total Time Elapsed + 15;
			Small Message(Event Player, Custom String("TRY YOUR LUCK: ALL PLAYER / BOT NAMES — 15s"));
		Else If(Event Player.EfekNasib == 2);
			Set Move Speed(Event Player, 1000);
			Start Accelerating(Event Player, Facing Direction Of(Event Player), 50, 25, To World, Direction Rate and Max Speed);
			Event Player.EfekNasibBerakhir = Total Time Elapsed + 10;
			Small Message(Event Player, Custom String("TRY YOUR LUCK: AIM-STEERED ACCELERATION — 10s"));
		Else If(Event Player.EfekNasib == 3);
			Event Player.KebalAktif = False;
			Event Player.ModeKebal = 0;
			Clear Status(Event Player, Unkillable);
			Set Damage Received(Event Player, 100);
			If(Event Player.IkonKebal != Null);
				Destroy Icon(Event Player.IkonKebal);
				Event Player.IkonKebal = Null;
			End;
			Small Message(Event Player, Custom String("TRY YOUR LUCK: SKULL"));
			Kill(Event Player, Null);
			Abort;
		Else If(Event Player.EfekNasib == 4);
			Set Player Health(All Living Players(Team Of(Event Player)), 9999);
			Small Message(All Living Players(Team Of(Event Player)), Custom String("TRY YOUR LUCK: HEART — TEAM FULL HEAL"));
			Event Player.EfekNasib = 0;
			Event Player.KartuNasibAktif = False;
		Else;
			"Burning deve poter danneggiare anche chi aveva Unkillable FULL HP: sospendi la protezione e ripristinala alla scadenza."
			Event Player.KebalAktif = False;
			Event Player.ModeKebal = 0;
			Clear Status(Event Player, Unkillable);
			Set Damage Received(Event Player, 100);
			If(Event Player.IkonKebal != Null);
				Destroy Icon(Event Player.IkonKebal);
				Event Player.IkonKebal = Null;
			End;
			Set Status(Event Player, Null, Burning, 10);
			Event Player.EfekNasibBerakhir = Total Time Elapsed + 10;
			Event Player.TickBurnNasib = Total Time Elapsed;
			Small Message(Event Player, Custom String("TRY YOUR LUCK: BURNING — 5% MAX HP / SEC — 10s"));
		End;

		Wait(1, Ignore Condition);
		If(Event Player.IkonKartuNasib != Null);
			Destroy Icon(Event Player.IkonKartuNasib);
		End;
		Event Player.IkonKartuNasib = Null;
		Event Player.IkonKartuNasibHijau = Null;
		Event Player.PutaranKartuNasib = 0;
		Event Player.JedaKartuNasib = 0;
		If(Event Player.KartuNasibAktif == False);
			Event Player.MenuNasibHarusDibuka = True;
		End;
	}
}

'''
    source = replace_span(source, 'rule("18e - Nasib:', 'rule("18f - Nasib:', luck_rule, "18e")

    death_rule = r'''rule("18f - Nasib: Reset completo effetti alla morte")
{
	event
	{
		Player Died;
		All;
		All;
	}

	conditions
	{
		Or(Event Player.KartuNasibAktif == True, Or(Event Player.PutaranKartuNasib > 0, Event Player.EfekNasib != 0)) == True;
	}

	actions
	{
		Event Player.MenuNasibHarusDibuka = False;
		Call Subroutine(TutupMenu);
		If(Event Player.IkonKartuNasib != Null);
			Destroy Icon(Event Player.IkonKartuNasib);
		End;
		If(Event Player.IkonKartuNasibHijau != Null);
			Destroy Icon(Event Player.IkonKartuNasibHijau);
		End;
		Clear Status(Event Player, Burning);
		Stop Accelerating(Event Player);
		If(Event Player.HudEfekNasib != Null);
			Destroy HUD Text(Event Player.HudEfekNasib);
		End;
		Event Player.HudEfekNasib = Null;
		Set Move Speed(Event Player, 100);
		Event Player.PrivasiNasibAktif = False;
		Event Player.EfekNasib = 0;
		Event Player.EfekNasibBerakhir = 0;
		Event Player.TickBurnNasib = 0;
		Event Player.IkonKartuNasib = Null;
		Event Player.IkonKartuNasibHijau = Null;
		Event Player.KartuNasibAktif = False;
		Event Player.MenuNasibHarusDibuka = True;
		Event Player.KartuNasibMerah = False;
		Event Player.PutaranKartuNasib = 0;
		Event Player.JedaKartuNasib = 0;
		Clear Status(Event Player, Unkillable);
		Event Player.ModeKebal = Event Player.ModeKebalTerakhir;
		Event Player.KursorKebal = Event Player.ModeKebalTerakhir;
		If(Event Player.ModeKebalTerakhir == 0);
			Event Player.KebalAktif = False;
			Set Damage Received(Event Player, 100);
		Else;
			Event Player.KebalAktif = True;
			Set Status(Event Player, Null, Unkillable, 9999);
			If(Event Player.ModeKebalTerakhir == 1);
				Set Damage Received(Event Player, 100);
			Else;
				Set Damage Received(Event Player, 0);
			End;
		End;
		If(Event Player.IkonKebal != Null);
			Destroy Icon(Event Player.IkonKebal);
			Event Player.IkonKebal = Null;
		End;
	}
}


'''
    source = replace_span(source, 'rule("18f - Nasib:', 'rule("18g - Nasib:', death_rule, "18f")

    expiry_rule = r'''rule("18h - Nasib: Scadenza effetti temporanei per player")
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
		Event Player.EfekNasibBerakhir > 0;
		Total Time Elapsed >= Event Player.EfekNasibBerakhir;
	}

	actions
	{
		Clear Status(Event Player, Burning);
		Stop Accelerating(Event Player);
		If(Event Player.HudEfekNasib != Null);
			Destroy HUD Text(Event Player.HudEfekNasib);
		End;
		Event Player.HudEfekNasib = Null;
		Set Move Speed(Event Player, 100);
		Event Player.PrivasiNasibAktif = False;
		If(Event Player.EfekNasib == 5);
			"Ripristina l Unkillable che Burning aveva sospeso."
			Clear Status(Event Player, Unkillable);
			Event Player.ModeKebal = Event Player.ModeKebalTerakhir;
			Event Player.KursorKebal = Event Player.ModeKebalTerakhir;
			If(Event Player.ModeKebalTerakhir == 0);
				Event Player.KebalAktif = False;
				Set Damage Received(Event Player, 100);
			Else;
				Event Player.KebalAktif = True;
				Set Status(Event Player, Null, Unkillable, 9999);
				If(Event Player.ModeKebalTerakhir == 1);
					Set Damage Received(Event Player, 100);
					If(Is Alive(Event Player) == True);
						Set Player Health(Event Player, 1);
					End;
				Else;
					Set Damage Received(Event Player, 0);
					If(Is Alive(Event Player) == True);
						Set Player Health(Event Player, Max Health(Event Player));
					End;
				End;
			End;
			If(Event Player.IkonKebal != Null);
				Destroy Icon(Event Player.IkonKebal);
				Event Player.IkonKebal = Null;
			End;
			If(Event Player.KebalAktif == True);
				If(Event Player.ModeKebal == 1);
					Create Icon(All Players(All Teams), Event Player, Warning, Visible To and Position, Custom Color(255, 80, 80, 255), True);
				Else;
					Create Icon(All Players(All Teams), Event Player, Halo, Visible To and Position, Global.RGB, True);
				End;
				Event Player.IkonKebal = Last Created Entity;
			End;
		End;
		Event Player.EfekNasib = 0;
		Event Player.EfekNasibBerakhir = 0;
		Event Player.TickBurnNasib = 0;
		Event Player.KartuNasibAktif = False;
		Event Player.MenuNasibHarusDibuka = True;
	}
}


'''
    source = replace_span(source, 'rule("18h - Nasib:', 'rule("18i - Nasib:', expiry_rule, "18h")

    hud_rule = r'''rule("18k - Nasib: HUD effetto e durata mentre il menu e chiuso")
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
		Event Player.EfekNasibBerakhir > 0;
		Event Player.HudEfekNasib == Null;
		Is Alive(Event Player) == True;
	}

	actions
	{
		Create HUD Text(Event Player, Null, Null, Custom String("\n{0}\n{1}",
			Event Player.EfekNasib == 1 ? Custom String("VISION: ALL PLAYER / BOT NAMES")
			: Event Player.EfekNasib == 2 ? Custom String("AIM-STEERED ACCELERATION")
			: Custom String("BURNING: 5% MAX HP / SEC"),
			Custom String("{0}s REMAINING", Max(0, Round To Integer(Event Player.EfekNasibBerakhir - Total Time Elapsed, Up)))), Top, -99,
			Color(White), Color(White), Global.RGB, Visible To String and Color, Visible Never);
		Event Player.HudEfekNasib = Last Text ID;
	}
}


'''
    source = replace_span(source, 'rule("18k - Nasib:', 'rule("18l - Nasib:', hud_rule, "18k")

    burn_rule = r'''rule("18l - Nasib: Burning proporzionale globale a tick")
{
	event
	{
		Ongoing - Global;
	}

	conditions
	{
		Count Of(Filtered Array(All Players(All Teams), And(Player Variable(Current Array Element, Manusia) == True,
			And(Player Variable(Current Array Element, EfekNasib) == 5, And(Player Variable(Current Array Element, EfekNasibBerakhir) > Total Time Elapsed,
			And(Player Variable(Current Array Element, TickBurnNasib) <= Total Time Elapsed,
			And(Has Spawned(Current Array Element) == True, Is Alive(Current Array Element) == True)))))) > 0;
	}

	actions
	{
		For Global Variable(IndeksPemainGlobal, 0, Count Of(All Players(All Teams)), 1);
			Global.PemainAktif = All Players(All Teams)[Global.IndeksPemainGlobal];
			If(And(Global.PemainAktif.Manusia == True, And(Global.PemainAktif.EfekNasib == 5,
				And(Global.PemainAktif.EfekNasibBerakhir > Total Time Elapsed, And(Global.PemainAktif.TickBurnNasib <= Total Time Elapsed,
				And(Has Spawned(Global.PemainAktif) == True, Is Alive(Global.PemainAktif) == True)))));
				Damage(Global.PemainAktif, Null, Max Health(Global.PemainAktif) * 0.025);
				Set Player Variable(Global.PemainAktif, TickBurnNasib, Total Time Elapsed + 0.500);
			End;
		End;
		Global.PemainAktif = Null;
	}
}


'''
    source = replace_span(source, 'rule("18l - Nasib:', 'rule("19 - Teleportasi Jongkok:', burn_rule, "18l burning")

    # Cleanup cambio team/leave: Burning deve sparire immediatamente; nessun ripristino Ultimate residuo.
    quiet_start = source.find('rule("93b2 - Subrutin:')
    quiet_end = source.find('rule("93c - Subrutin:', quiet_start)
    if quiet_start < 0 or quiet_end < 0:
        raise RuntimeError("TenangkanPemain non trovato")
    quiet = source[quiet_start:quiet_end]
    quiet = quiet.replace("Clear Status(Event Player, Hacked);", "Clear Status(Event Player, Burning);")
    source = source[:quiet_start] + quiet + source[quiet_end:]

    clean_start = source.find('rule("93c - Subrutin:')
    clean_end = source.find('rule("94 - Subrutin:', clean_start)
    if clean_start < 0 or clean_end < 0:
        raise RuntimeError("BersihkanPemain non trovato")
    clean = source[clean_start:clean_end]
    clean = clean.replace("Clear Status(Event Player, Hacked);", "Clear Status(Event Player, Burning);")
    clean = re.sub(r'\n\t\tIf\(Event Player\.EfekNasib == 2\);\n\t\t\tSet Ultimate Charge\(Event Player, Event Player\.TickBurnNasib\);\n\t\tEnd;', '', clean, count=1)
    source = source[:clean_start] + clean + source[clean_end:]

    # Validator Try Your Luck: nuova pipeline a cinque effetti.
    validator_chunk = r'''    luck = find_rule(rules, "18e - Nasib:")
    luck_death = find_rule(rules, "18f - Nasib:")
    luck_reopen = find_rule(rules, "18g - Nasib:")
    luck_expiry = find_rule(rules, "18h - Nasib:")
    luck_vision_create = find_rule(rules, "18i - Nasib:")
    luck_vision_cleanup = find_rule(rules, "18j - Nasib:")
    luck_effect_hud = find_rule(rules, "18k - Nasib:")
    luck_burn_global = find_rule(rules, "18l - Nasib:")
    checks.require(all(x is not None for x in (luck, luck_death, luck_reopen, luck_expiry, luck_vision_create, luck_vision_cleanup, luck_effect_hud, luck_burn_global)), "pipeline Try Your Luck a cinque risultati assente")
    if luck:
        checks.equal(event_type(luck), "Ongoing - Each Player", "18e Try Your Luck: scheduler")
        checks.require("Random Integer(1, 5)" in luck.body and "Random Integer(1, 10)" not in luck.body, "roulette Try Your Luck non usa cinque risultati")
        for icon in ("Eye", "Dizzy", "Skull", "Heart", "Fire"):
            checks.require(f", {icon}, Visible To and Position" in luck.body, f"icona Try Your Luck assente: {icon}")
        for removed in ("Poison 2", "Asterisk", "Spiral", "Bolt", "Moon", "Arrow: Down"):
            checks.require(f", {removed}, Visible To and Position" not in luck.body, f"vecchio effetto Try Your Luck ancora presente: {removed}")
        for token in (
            "Event Player.PrivasiNasibAktif = True;",
            "Start Accelerating(Event Player, Facing Direction Of(Event Player), 50, 25, To World, Direction Rate and Max Speed);",
            "Event Player.EfekNasibBerakhir = Total Time Elapsed + 10;",
            "Kill(Event Player, Null);",
            "Set Player Health(All Living Players(Team Of(Event Player)), 9999);",
            "Set Status(Event Player, Null, Burning, 10);",
            "Event Player.TickBurnNasib = Total Time Elapsed;",
        ):
            checks.require(token in luck.body, f"Try Your Luck risultato incompleto: {token}")
        for removed in ("Hacked", "Set Ultimate Charge(", "RANDOM TELEPORT", "Set Jump Vertical Speed(Event Player, 200)", "Set Gravity(Event Player, 10)", "Disable Movement Collision With Environment(Event Player, True)"):
            checks.require(removed not in luck.body, f"vecchio effetto Try Your Luck non eliminato: {removed}")
        checks.require("Call Subroutine(TutupMenu);" in luck.body, "Try Your Luck non chiude il menu alla fine della roulette")
        checks.require("Kill(Event Player, Null);\n\t\t\tAbort;" in luck.body, "Skull Try Your Luck non interrompe subito la pipeline dopo la morte")
    if luck_death:
        checks.require("Clear Status(Event Player, Burning);" in luck_death.body, "morte Try Your Luck non pulisce Burning")
        checks.require("Stop Accelerating(Event Player);" in luck_death.body and "Set Move Speed(Event Player, 100);" in luck_death.body, "morte Try Your Luck non pulisce accelerazione")
        checks.require("Event Player.MenuNasibHarusDibuka = True;" in luck_death.body, "morte Try Your Luck non richiede la riapertura dopo il reset")
        checks.require("Call Subroutine(TutupMenu);" in luck_death.body, "morte Try Your Luck non chiude e libera il menu prima della riapertura")
        checks.require("Wait(" not in luck_death.body and "Loop If Condition Is True;" not in luck_death.body, "morte Try Your Luck deve resettare subito senza Wait o Loop")
        checks.require("Call Subroutine(GambarMenu);" not in luck_death.body and "Event Player.MenuTerbuka = True;" not in luck_death.body, "morte Try Your Luck non deve mostrare il menu prima del respawn")
    if luck_reopen:
        checks.equal(event_type(luck_reopen), "Ongoing - Each Player", "18g riapertura Try Your Luck: scheduler")
        checks.require("Event Player.KartuNasibAktif == False;" in luck_reopen.body, "18g riapre il menu prima che la funzione sia finita")
        checks.require("Has Spawned(Event Player) == True;" in luck_reopen.body and "Is Alive(Event Player) == True;" in luck_reopen.body, "18g deve attendere il respawn vivo prima di consumare la riapertura")
        checks.require("Event Player.HalamanMenu = 10;" in luck_reopen.body and "Call Subroutine(GambarMenu);" in luck_reopen.body and "Call Subroutine(GambarNasib);" in luck_reopen.body, "18g non riapre visivamente la pagina Try Your Luck")
        checks.require("Wait(" not in luck_reopen.body and "Loop If Condition Is True;" not in luck_reopen.body, "18g riapertura al respawn non deve usare Wait o Loop")
    if luck_expiry:
        checks.equal(event_type(luck_expiry), "Ongoing - Each Player", "18h scadenza Try Your Luck: scheduler")
        checks.require("Event Player.EfekNasibBerakhir > 0;" in luck_expiry.body and "Total Time Elapsed >= Event Player.EfekNasibBerakhir;" in luck_expiry.body, "18h non scade sul timestamp per-player")
        checks.require("Wait(" not in luck_expiry.body and "Loop If Condition Is True;" not in luck_expiry.body, "18h scadenza Try Your Luck non deve usare Wait o Loop")
        for token in ("Clear Status(Event Player, Burning);", "Stop Accelerating(Event Player);", "Set Move Speed(Event Player, 100);", "Event Player.PrivasiNasibAktif = False;", "Event Player.TickBurnNasib = 0;", "Event Player.KartuNasibAktif = False;", "Event Player.MenuNasibHarusDibuka = True;"):
            checks.require(token in luck_expiry.body, f"18h reset scadenza incompleto: {token}")
        checks.require("Event Player.EfekNasib == 5" in luck_expiry.body and "Event Player.ModeKebal = Event Player.ModeKebalTerakhir;" in luck_expiry.body, "18h non ripristina Unkillable dopo Burning")
    if luck_vision_create:
        checks.equal(event_type(luck_vision_create), "Ongoing - Each Player", "18i Vision labels: scheduler")
        checks.require("Create In-World Text(" in luck_vision_create.body and 'Custom String("{0}", Event Player)' in luck_vision_create.body, "18i Vision non crea nomi custom")
        checks.require("PrivasiNasibAktif) == True" in luck_vision_create.body, "18i Vision non limita i nomi agli osservatori Vision")
    if luck_vision_cleanup:
        checks.equal(event_type(luck_vision_cleanup), "Ongoing - Each Player", "18j Vision cleanup: scheduler")
        checks.require("Destroy In-World Text(Event Player.TeksVisiNasib);" in luck_vision_cleanup.body, "18j non distrugge label Vision")
    if luck_effect_hud:
        checks.equal(event_type(luck_effect_hud), "Ongoing - Each Player", "18k HUD effetto: scheduler")
        for token in ("VISION: ALL PLAYER / BOT NAMES", "AIM-STEERED ACCELERATION", "BURNING: 5% MAX HP / SEC", "EfekNasibBerakhir - Total Time Elapsed", "Global.RGB"):
            checks.require(token in luck_effect_hud.body, f"18k HUD effetto incompleto: {token}")
        for removed in ("HACKED", "ULTIMATE ALWAYS READY", "MOVE / JUMP / PROJECTILE x2", "GRAVITY 10%", "FLOOR REMOVED"):
            checks.require(removed not in luck_effect_hud.body, f"18k mostra ancora vecchio effetto: {removed}")
        checks.require("Wait(" not in luck_effect_hud.body and "Loop If Condition Is True;" not in luck_effect_hud.body, "18k HUD effetto non deve usare Wait/Loop")
    if luck_burn_global:
        checks.equal(event_type(luck_burn_global), "Ongoing - Global", "18l Burning globale: scheduler")
        for token in ("Player Variable(Current Array Element, EfekNasib) == 5", "Player Variable(Current Array Element, TickBurnNasib) <= Total Time Elapsed", "Damage(Global.PemainAktif, Null, Max Health(Global.PemainAktif) * 0.025);", "Set Player Variable(Global.PemainAktif, TickBurnNasib, Total Time Elapsed + 0.500);", "For Global Variable(IndeksPemainGlobal, 0, Count Of(All Players(All Teams)), 1);"):
            checks.require(token in luck_burn_global.body, f"18l Burning globale incompleto: {token}")
        checks.require("Wait(" not in luck_burn_global.body and "Loop If Condition Is True;" not in luck_burn_global.body, "18l Burning globale non deve usare Wait o Loop")
        checks.require("Ongoing - Each Player" not in luck_burn_global.body, "18l Burning non deve diventare Each Player")
    if teleport_open:
        checks.require("Event Player.KartuNasibAktif == False;" in teleport_open.body, "Crouch Teleport deve essere disattivato durante Try Your Luck")
    quiet_player = find_rule(rules, "93b2 - Subrutin:")
    checks.require(quiet_player is not None, "TenangkanPemain assente")
    if quiet_player:
        checks.require("Wait(" not in quiet_player.body and "Loop If Condition Is True;" not in quiet_player.body, "TenangkanPemain deve pulire il cambio team senza Wait o Loop")
        for token in ("Destroy Icon(Event Player.IkonKartuNasib);", "Destroy HUD Text(Event Player.HudEfekNasib);", "Clear Status(Event Player, Burning);", "Clear Status(Event Player, Unkillable);", "Stop Accelerating(Event Player);", "Event Player.KartuNasibAktif = False;", "Event Player.EfekNasib = 0;", "Event Player.TickBurnNasib = 0;", "Event Player.MenuNasibHarusDibuka = False;"):
            checks.require(token in quiet_player.body, f"cambio team non ripulisce Try Your Luck: {token}")
    if fast_manager:
        checks.require("Set Ultimate Charge(" not in fast_manager.body, "04g contiene ancora Ultimate Try Your Luck rimossa")
        checks.require("Global.PemainAktif.EfekNasib ==" not in fast_manager.body, "04g non deve più gestire effetti Try Your Luck")
'''
    start = '    luck = find_rule(rules, "18e - Nasib:")'
    end = '    if inspect_rule:'
    a = validator.find(start)
    b = validator.find(end, a)
    if a < 0 or b < 0:
        raise RuntimeError("chunk validator Try Your Luck non trovato")
    validator = validator[:a] + validator_chunk + validator[b:]

    blob = git_blob_sha(source)
    validator, n = re.subn(r'EXPECTED_SOURCE_BLOB = "[0-9a-f]{40}"', f'EXPECTED_SOURCE_BLOB = "{blob}"', validator, count=1)
    if n != 1:
        raise RuntimeError("EXPECTED_SOURCE_BLOB non aggiornato")
    return source, validator, blob


original_source = SOURCE.read_text(encoding="utf-8")
original_validator = VALIDATOR.read_text(encoding="utf-8")
try:
    source, validator, blob = transform(original_source, original_validator)
    SOURCE.write_text(source, encoding="utf-8")
    VALIDATOR.write_text(validator, encoding="utf-8")
    subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "tools/validate_workshop.py"], cwd=ROOT, check=True)
    if ERROR.exists():
        ERROR.unlink()
    print(f"patched source blob: {blob}")
except Exception:
    SOURCE.write_text(original_source, encoding="utf-8")
    VALIDATOR.write_text(original_validator, encoding="utf-8")
    ERROR.write_text(traceback.format_exc(), encoding="utf-8")
    print(ERROR.read_text(encoding="utf-8"), file=sys.stderr)
