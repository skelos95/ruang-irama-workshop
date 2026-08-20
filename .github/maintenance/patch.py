#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
ERROR = ROOT / ".github" / "maintenance" / "last-patch-error.txt"


def blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def rule_bounds(text: str, prefix: str) -> tuple[int, int]:
    start = text.index(f'rule("{prefix}')
    nxt = text.find('\nrule("', start + 1)
    return start, len(text) if nxt < 0 else nxt + 1


def replace_once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise RuntimeError(f"{label}: atteso 1 match, trovati {n}")
    return text.replace(old, new, 1)


source = SOURCE.read_text(encoding="utf-8")
validator = VALIDATOR.read_text(encoding="utf-8")

# --- Menu pagina 10: sei risultati e Unkillable disattivato in modo persistente. ---
start, end = rule_bounds(source, "10 - Menu:")
rule10 = source[start:end]
p10_start = rule10.index("\t\tElse If(Event Player.HalamanMenu == 10);")
p10_end = rule10.index("\n\t\tElse;\n\t\t\tIf(Count Of(Global.PemainManusia) > 0);", p10_start)
page10 = '''\t\tElse If(Event Player.HalamanMenu == 10);
\t\t\tIf(Event Player.KartuNasibAktif == True);
\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Try Your Luck is still active. Wait for it to finish.") : Event Player.IndeksBahasa == 1 ? Custom String("Try Your Luck masih aktif. Tunggu sampai selesai.") : Custom String("Try Your Luck ยังทำงานอยู่ รอให้จบก่อน"));
\t\t\tElse;
\t\t\t\tEvent Player.KartuNasibAktif = True;
\t\t\t\tEvent Player.EfekNasib = Random Integer(1, 6);
\t\t\t\tEvent Player.PutaranKartuNasib = Random Integer(20, 24);
\t\t\t\tEvent Player.JedaKartuNasib = 0.080;
\t\t\t\tEvent Player.KartuNasibMerah = False;
\t\t\t\tEvent Player.EfekNasibBerakhir = 0;
\t\t\t\tEvent Player.DaftarTujuanNasib = Empty Array;
\t\t\t\tEvent Player.TujuanNasib = Vector(0, 0, 0);
\t\t\t\tEvent Player.ArahNasib = Vector(0, 0, 0);
\t\t\t\tEvent Player.PrivasiNasibAktif = False;
\t\t\t\tEvent Player.KategoriTeleportNasib = -1;
\t\t\t\tEvent Player.TickBurnNasib = 0;
\t\t\t\tEvent Player.MenuNasibHarusDibuka = False;
\t\t\t\tIf(Event Player.IkonKartuNasib != Null);
\t\t\t\t\tDestroy Icon(Event Player.IkonKartuNasib);
\t\t\t\tEnd;
\t\t\t\tIf(Event Player.IkonKartuNasibHijau != Null);
\t\t\t\t\tDestroy Icon(Event Player.IkonKartuNasibHijau);
\t\t\t\tEnd;
\t\t\t\tEvent Player.IkonKartuNasib = Null;
\t\t\t\tEvent Player.IkonKartuNasibHijau = Null;
\t\t\t\t"Try Your Luck spegne definitivamente 1 HP / FULL HP; il player potrà riattivarli solo dal menu Unkillable."
\t\t\t\tEvent Player.KebalAktif = False;
\t\t\t\tEvent Player.ModeKebal = 0;
\t\t\t\tEvent Player.KursorKebal = 0;
\t\t\t\tEvent Player.ModeKebalTerakhir = 0;
\t\t\t\tClear Status(Event Player, Unkillable);
\t\t\t\tSet Damage Received(Event Player, 100);
\t\t\t\tIf(Is Alive(Event Player) == True);
\t\t\t\t\tSet Player Health(Event Player, Max Health(Event Player));
\t\t\t\tEnd;
\t\t\t\tIf(Event Player.IkonKebal != Null);
\t\t\t\t\tDestroy Icon(Event Player.IkonKebal);
\t\t\t\tEnd;
\t\t\t\tEvent Player.IkonKebal = Null;
\t\t\t\tCall Subroutine(GambarMenu);
\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Try Your Luck: six outcomes are rolling.") : Event Player.IndeksBahasa == 1 ? Custom String("Try Your Luck: enam hasil sedang diacak.") : Custom String("Try Your Luck: กำลังสุ่มหกผลลัพธ์"));
\t\t\tEnd;'''
rule10 = rule10[:p10_start] + page10 + rule10[p10_end:]
source = source[:start] + rule10 + source[end:]

# --- 18e: roulette a sei risultati. ---
new_luck = '''rule("18e - Nasib: Roulette sei effetti con risultato bloccato")
{
\tevent
\t{
\t\tOngoing - Each Player;
\t\tAll;
\t\tAll;
\t}

\tconditions
\t{
\t\tEvent Player.Manusia == True;
\t\tEvent Player.KartuNasibAktif == True;
\t\tEvent Player.PutaranKartuNasib > 0;
\t\tHas Spawned(Event Player) == True;
\t\tIs Alive(Event Player) == True;
\t}

\tactions
\t{
\t\tIf(Event Player.IkonKartuNasib != Null);
\t\t\tDestroy Icon(Event Player.IkonKartuNasib);
\t\tEnd;
\t\tEvent Player.EfekNasib = Random Integer(1, 6);
\t\tIf(Event Player.EfekNasib == 1);
\t\t\tCreate Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Eye, Visible To and Position, Color(Aqua), False);
\t\tElse If(Event Player.EfekNasib == 2);
\t\t\tCreate Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Dizzy, Visible To and Position, Color(Violet), False);
\t\tElse If(Event Player.EfekNasib == 3);
\t\t\tCreate Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Skull, Visible To and Position, Custom Color(255, 70, 70, 255), False);
\t\tElse If(Event Player.EfekNasib == 4);
\t\t\tCreate Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Heart, Visible To and Position, Custom Color(70, 255, 110, 255), False);
\t\tElse If(Event Player.EfekNasib == 5);
\t\t\tCreate Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Fire, Visible To and Position, Color(Orange), False);
\t\tElse;
\t\t\tCreate Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Poison 2, Visible To and Position, Custom Color(170, 80, 255, 255), False);
\t\tEnd;
\t\tEvent Player.IkonKartuNasib = Last Created Entity;
\t\tWait(Event Player.JedaKartuNasib, Abort When False);
\t\tModify Player Variable(Event Player, PutaranKartuNasib, Subtract, 1);
\t\tModify Player Variable(Event Player, JedaKartuNasib, Add, 0.045);
\t\tLoop If Condition Is True;

\t\t"La roulette non ripristina mai Unkillable: resta OFF finché il player non lo riattiva dal menu dedicato."
\t\tClear Status(Event Player, Unkillable);
\t\tEvent Player.KebalAktif = False;
\t\tEvent Player.ModeKebal = 0;
\t\tEvent Player.KursorKebal = 0;
\t\tEvent Player.ModeKebalTerakhir = 0;
\t\tSet Damage Received(Event Player, 100);
\t\tIf(Event Player.IkonKebal != Null);
\t\t\tDestroy Icon(Event Player.IkonKebal);
\t\tEnd;
\t\tEvent Player.IkonKebal = Null;
\t\tEvent Player.MenuNasibHarusDibuka = False;
\t\tCall Subroutine(TutupMenu);
\t\tEvent Player.EfekNasibBerakhir = 0;
\t\tEvent Player.TickBurnNasib = 0;

\t\tIf(Event Player.EfekNasib == 1);
\t\t\tEvent Player.PrivasiNasibAktif = True;
\t\t\tEvent Player.EfekNasibBerakhir = Total Time Elapsed + 15;
\t\t\tSmall Message(Event Player, Custom String("TRY YOUR LUCK: ALL PLAYER / BOT NAMES — 15s"));
\t\tElse If(Event Player.EfekNasib == 2);
\t\t\tSet Move Speed(Event Player, 1000);
\t\t\tStart Accelerating(Event Player, Facing Direction Of(Event Player), 50, 25, To World, Direction Rate and Max Speed);
\t\t\tEvent Player.EfekNasibBerakhir = Total Time Elapsed + 10;
\t\t\tSmall Message(Event Player, Custom String("TRY YOUR LUCK: AIM-STEERED ACCELERATION — 10s"));
\t\tElse If(Event Player.EfekNasib == 3);
\t\t\tSmall Message(Event Player, Custom String("TRY YOUR LUCK: SKULL"));
\t\t\tKill(Event Player, Null);
\t\t\tAbort;
\t\tElse If(Event Player.EfekNasib == 4);
\t\t\tSet Player Health(All Living Players(Team Of(Event Player)), 9999);
\t\t\tSmall Message(All Living Players(Team Of(Event Player)), Custom String("TRY YOUR LUCK: HEART — TEAM FULL HEAL"));
\t\t\tEvent Player.EfekNasib = 0;
\t\t\tEvent Player.KartuNasibAktif = False;
\t\tElse If(Event Player.EfekNasib == 5);
\t\t\tSet Status(Event Player, Null, Burning, 10);
\t\t\tEvent Player.EfekNasibBerakhir = Total Time Elapsed + 10;
\t\t\tEvent Player.TickBurnNasib = Total Time Elapsed;
\t\t\tSmall Message(Event Player, Custom String("TRY YOUR LUCK: BURNING — 5% MAX HP / SEC — 10s"));
\t\tElse;
\t\t\tSet Status(Event Player, Null, Hacked, 5);
\t\t\tEvent Player.EfekNasibBerakhir = Total Time Elapsed + 5;
\t\t\tSmall Message(Event Player, Custom String("TRY YOUR LUCK: HACKED — 5s"));
\t\tEnd;

\t\tWait(1, Ignore Condition);
\t\tIf(Event Player.IkonKartuNasib != Null);
\t\t\tDestroy Icon(Event Player.IkonKartuNasib);
\t\tEnd;
\t\tEvent Player.IkonKartuNasib = Null;
\t\tEvent Player.IkonKartuNasibHijau = Null;
\t\tEvent Player.PutaranKartuNasib = 0;
\t\tEvent Player.JedaKartuNasib = 0;
\t\tIf(Event Player.KartuNasibAktif == False);
\t\t\tEvent Player.MenuNasibHarusDibuka = True;
\t\tEnd;
\t}
}
'''
start, end = rule_bounds(source, "18e - Nasib:")
source = source[:start] + new_luck + source[end:]

# --- 18f: morte pulisce Burning/Hacked e lascia Unkillable OFF. ---
start, end = rule_bounds(source, "18f - Nasib:")
death = source[start:end]
death = replace_once(death, "\t\tClear Status(Event Player, Burning);\n", "\t\tClear Status(Event Player, Burning);\n\t\tClear Status(Event Player, Hacked);\n", "18f Hacked cleanup")
restore_start = death.index("\t\tClear Status(Event Player, Unkillable);")
restore_end = death.index("\n\t}\n}", restore_start)
new_death_tail = '''\t\tClear Status(Event Player, Unkillable);
\t\tEvent Player.KebalAktif = False;
\t\tEvent Player.ModeKebal = 0;
\t\tEvent Player.KursorKebal = 0;
\t\tEvent Player.ModeKebalTerakhir = 0;
\t\tSet Damage Received(Event Player, 100);
\t\tIf(Event Player.IkonKebal != Null);
\t\t\tDestroy Icon(Event Player.IkonKebal);
\t\t\tEvent Player.IkonKebal = Null;
\t\tEnd;'''
death = death[:restore_start] + new_death_tail + death[restore_end:]
source = source[:start] + death + source[end:]

# --- 18h: scadenza pulisce entrambi gli status senza ripristinare Unkillable. ---
start, end = rule_bounds(source, "18h - Nasib:")
expiry = source[start:end]
expiry = replace_once(expiry, "\t\tClear Status(Event Player, Burning);\n", "\t\tClear Status(Event Player, Burning);\n\t\tClear Status(Event Player, Hacked);\n", "18h Hacked cleanup")
restore_start = expiry.index("\t\tIf(Event Player.EfekNasib == 5);")
restore_end = expiry.index("\t\tEvent Player.EfekNasib = 0;", restore_start)
expiry = expiry[:restore_start] + expiry[restore_end:]
source = source[:start] + expiry + source[end:]

# --- 18k: HUD Hacked. ---
start, end = rule_bounds(source, "18k - Nasib:")
hud = source[start:end]
hud = replace_once(
    hud,
    ': Event Player.EfekNasib == 2 ? Custom String("AIM-STEERED ACCELERATION")\n\t\t\t: Custom String("BURNING: 5% MAX HP / SEC"),',
    ': Event Player.EfekNasib == 2 ? Custom String("AIM-STEERED ACCELERATION")\n\t\t\t: Event Player.EfekNasib == 5 ? Custom String("BURNING: 5% MAX HP / SEC")\n\t\t\t: Custom String("HACKED"),',
    "18k Hacked HUD",
)
source = source[:start] + hud + source[end:]

# Team-change / leave cleanup: Hacked deve sparire insieme a Burning.
for prefix in ("93b2 - Subrutin:", "93c - Subrutin:"):
    start, end = rule_bounds(source, prefix)
    block = source[start:end]
    if "Clear Status(Event Player, Hacked);" not in block:
        block = replace_once(block, "\t\t\tClear Status(Event Player, Burning);\n" if prefix.startswith("93b2") else "\t\tClear Status(Event Player, Burning);\n",
                             "\t\t\tClear Status(Event Player, Burning);\n\t\t\tClear Status(Event Player, Hacked);\n" if prefix.startswith("93b2") else "\t\tClear Status(Event Player, Burning);\n\t\tClear Status(Event Player, Hacked);\n",
                             f"{prefix} Hacked cleanup")
    source = source[:start] + block + source[end:]

# --- Validator: sei risultati, Hacked e Unkillable mai ripristinato. ---
validator = replace_once(
    validator,
    'checks.require("Event Player.EfekNasib = Random Integer(1, 5);" in interact.body, "Try Your Luck non inizializza cinque risultati")',
    'checks.require("Event Player.EfekNasib = Random Integer(1, 6);" in interact.body, "Try Your Luck non inizializza sei risultati")\n        for token in ("Event Player.KebalAktif = False;", "Event Player.ModeKebal = 0;", "Event Player.KursorKebal = 0;", "Event Player.ModeKebalTerakhir = 0;", "Clear Status(Event Player, Unkillable);", "Set Damage Received(Event Player, 100);", "Set Player Health(Event Player, Max Health(Event Player));"):\n            checks.require(token in interact.body, f"avvio Try Your Luck non disattiva Unkillable: {token}")\n        checks.require("Try Your Luck spegne definitivamente 1 HP / FULL HP" in interact.body, "avvio Try Your Luck non documenta Unkillable persistente OFF")',
    "validator avvio sei risultati",
)

vstart = validator.index('    luck = find_rule(rules, "18e - Nasib:")')
vend = validator.index('    if inspect_rule:\n        checks.require("Event Player.PrivasiNasibAktif == True"', vstart)
new_validation = '''    luck = find_rule(rules, "18e - Nasib:")
    luck_death = find_rule(rules, "18f - Nasib:")
    luck_reopen = find_rule(rules, "18g - Nasib:")
    luck_expiry = find_rule(rules, "18h - Nasib:")
    luck_vision_create = find_rule(rules, "18i - Nasib:")
    luck_vision_cleanup = find_rule(rules, "18j - Nasib:")
    luck_effect_hud = find_rule(rules, "18k - Nasib:")
    luck_burn_global = find_rule(rules, "18l - Nasib:")
    checks.require(all(x is not None for x in (luck, luck_death, luck_reopen, luck_expiry, luck_vision_create, luck_vision_cleanup, luck_effect_hud, luck_burn_global)), "pipeline Try Your Luck a sei risultati assente")
    if luck:
        checks.equal(event_type(luck), "Ongoing - Each Player", "18e Try Your Luck: scheduler")
        checks.require("Random Integer(1, 6)" in luck.body and "Random Integer(1, 5)" not in luck.body and "Random Integer(1, 10)" not in luck.body, "roulette Try Your Luck non usa sei risultati")
        for icon in ("Eye", "Dizzy", "Skull", "Heart", "Fire", "Poison 2"):
            checks.require(f", {icon}, Visible To and Position" in luck.body, f"icona Try Your Luck assente: {icon}")
        for removed in ("Asterisk", "Spiral", "Bolt", "Moon", "Arrow: Down"):
            checks.require(f", {removed}, Visible To and Position" not in luck.body, f"vecchio effetto Try Your Luck ancora presente: {removed}")
        for token in (
            "Event Player.PrivasiNasibAktif = True;",
            "Start Accelerating(Event Player, Facing Direction Of(Event Player), 50, 25, To World, Direction Rate and Max Speed);",
            "Kill(Event Player, Null);",
            "Set Player Health(All Living Players(Team Of(Event Player)), 9999);",
            "Set Status(Event Player, Null, Burning, 10);",
            "Event Player.TickBurnNasib = Total Time Elapsed;",
            "Set Status(Event Player, Null, Hacked, 5);",
            "Event Player.EfekNasibBerakhir = Total Time Elapsed + 5;",
        ):
            checks.require(token in luck.body, f"Try Your Luck risultato incompleto: {token}")
        for removed in ("Set Ultimate Charge(", "RANDOM TELEPORT", "Set Jump Vertical Speed(Event Player, 200)", "Set Gravity(Event Player, 10)", "Disable Movement Collision With Environment(Event Player, True)"):
            checks.require(removed not in luck.body, f"vecchio effetto Try Your Luck non eliminato: {removed}")
        checks.require("Call Subroutine(TutupMenu);" in luck.body, "Try Your Luck non chiude il menu alla fine della roulette")
        checks.require("Kill(Event Player, Null);\\n\\t\\t\\tAbort;" in luck.body, "Skull Try Your Luck non interrompe subito la pipeline dopo la morte")
        checks.require("Event Player.ModeKebal = Event Player.ModeKebalTerakhir;" not in luck.body and "Set Status(Event Player, Null, Unkillable, 9999);" not in luck.body, "18e ripristina ancora Unkillable automaticamente")
        for token in ("Event Player.KebalAktif = False;", "Event Player.ModeKebal = 0;", "Event Player.KursorKebal = 0;", "Event Player.ModeKebalTerakhir = 0;", "Set Damage Received(Event Player, 100);"):
            checks.require(token in luck.body, f"18e non mantiene Unkillable OFF: {token}")
    if luck_death:
        for token in ("Clear Status(Event Player, Burning);", "Clear Status(Event Player, Hacked);", "Stop Accelerating(Event Player);", "Set Move Speed(Event Player, 100);"):
            checks.require(token in luck_death.body, f"morte Try Your Luck cleanup incompleto: {token}")
        checks.require("Event Player.MenuNasibHarusDibuka = True;" in luck_death.body, "morte Try Your Luck non richiede la riapertura dopo il reset")
        checks.require("Call Subroutine(TutupMenu);" in luck_death.body, "morte Try Your Luck non chiude e libera il menu prima della riapertura")
        checks.require("Wait(" not in luck_death.body and "Loop If Condition Is True;" not in luck_death.body, "morte Try Your Luck deve resettare subito senza Wait o Loop")
        checks.require("Call Subroutine(GambarMenu);" not in luck_death.body and "Event Player.MenuTerbuka = True;" not in luck_death.body, "morte Try Your Luck non deve mostrare il menu prima del respawn")
        checks.require("Event Player.ModeKebal = Event Player.ModeKebalTerakhir;" not in luck_death.body and "Set Status(Event Player, Null, Unkillable, 9999);" not in luck_death.body, "morte Try Your Luck ripristina ancora Unkillable")
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
        for token in ("Clear Status(Event Player, Burning);", "Clear Status(Event Player, Hacked);", "Stop Accelerating(Event Player);", "Set Move Speed(Event Player, 100);", "Event Player.PrivasiNasibAktif = False;", "Event Player.TickBurnNasib = 0;", "Event Player.KartuNasibAktif = False;", "Event Player.MenuNasibHarusDibuka = True;"):
            checks.require(token in luck_expiry.body, f"18h reset scadenza incompleto: {token}")
        checks.require("ModeKebalTerakhir" not in luck_expiry.body and "Set Status(Event Player, Null, Unkillable" not in luck_expiry.body, "18h non deve riattivare Unkillable")
    if luck_vision_create:
        checks.equal(event_type(luck_vision_create), "Ongoing - Each Player", "18i Vision labels: scheduler")
        checks.require("Create In-World Text(" in luck_vision_create.body and 'Custom String("{0}", Event Player)' in luck_vision_create.body, "18i Vision non crea nomi custom")
        checks.require("PrivasiNasibAktif) == True" in luck_vision_create.body, "18i Vision non limita i nomi agli osservatori Vision")
    if luck_vision_cleanup:
        checks.equal(event_type(luck_vision_cleanup), "Ongoing - Each Player", "18j Vision cleanup: scheduler")
        checks.require("Destroy In-World Text(Event Player.TeksVisiNasib);" in luck_vision_cleanup.body, "18j non distrugge label Vision")
    if luck_effect_hud:
        checks.equal(event_type(luck_effect_hud), "Ongoing - Each Player", "18k HUD effetto: scheduler")
        for token in ("VISION: ALL PLAYER / BOT NAMES", "AIM-STEERED ACCELERATION", "BURNING: 5% MAX HP / SEC", "HACKED", "EfekNasibBerakhir - Total Time Elapsed", "Global.RGB"):
            checks.require(token in luck_effect_hud.body, f"18k HUD effetto incompleto: {token}")
        for removed in ("ULTIMATE ALWAYS READY", "MOVE / JUMP / PROJECTILE x2", "GRAVITY 10%", "FLOOR REMOVED"):
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
        for token in ("Destroy Icon(Event Player.IkonKartuNasib);", "Destroy HUD Text(Event Player.HudEfekNasib);", "Clear Status(Event Player, Burning);", "Clear Status(Event Player, Hacked);", "Clear Status(Event Player, Unkillable);", "Stop Accelerating(Event Player);", "Event Player.KartuNasibAktif = False;", "Event Player.EfekNasib = 0;", "Event Player.TickBurnNasib = 0;", "Event Player.MenuNasibHarusDibuka = False;"):
            checks.require(token in quiet_player.body, f"cambio team non ripulisce Try Your Luck: {token}")
    if fast_manager:
        checks.require("Set Ultimate Charge(" not in fast_manager.body, "04g contiene ancora Ultimate Try Your Luck rimossa")
        checks.require("Global.PemainAktif.EfekNasib ==" not in fast_manager.body, "04g non deve più gestire effetti Try Your Luck")
'''
validator = validator[:vstart] + new_validation + validator[vend:]

# Aggiorna pin sorgente e rimuovi diagnostico precedente su successo.
blob = blob_sha(source)
validator, n = re.subn(r'EXPECTED_SOURCE_BLOB = "[0-9a-f]{40}"', f'EXPECTED_SOURCE_BLOB = "{blob}"', validator, count=1)
if n != 1:
    raise RuntimeError("EXPECTED_SOURCE_BLOB non aggiornato")

SOURCE.write_text(source, encoding="utf-8")
VALIDATOR.write_text(validator, encoding="utf-8")
ERROR.unlink(missing_ok=True)
print(f"patched source blob: {blob}")
