#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"


def replace_exact(text: str, old: str, new: str, label: str, expected: int = 1) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"{label}: attesi {expected} match, trovati {count}")
    return text.replace(old, new, expected)


def git_blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


source = SOURCE.read_text(encoding="utf-8")
validator = VALIDATOR.read_text(encoding="utf-8")

source = replace_exact(
    source,
    "\t\t107: MenuNasibHarusDibuka\n}",
    "\t\t107: MenuNasibHarusDibuka\n\t\t108: HudEfekNasib\n\t\t109: TeksVisiNasib\n}",
    "variabili HUD/Vision",
)
source = replace_exact(
    source,
    "\t\tEvent Player.HasilNasibTerkunci = 0;\n\t\tEvent Player.MenuNasibHarusDibuka = False;\n\t\tEvent Player.PernahDisiapkan = True;",
    "\t\tEvent Player.HasilNasibTerkunci = 0;\n\t\tEvent Player.MenuNasibHarusDibuka = False;\n\t\tEvent Player.HudEfekNasib = Null;\n\t\tEvent Player.TeksVisiNasib = Null;\n\t\tEvent Player.PernahDisiapkan = True;",
    "init HUD/Vision",
)
source = replace_exact(
    source,
    "\t\tElse If(Event Player.EfekNasib == 6);\n\t\t\tEvent Player.PrivasiNasibAktif = True;\n\t\t\tEnable Nameplates(All Players(All Teams), Event Player);\n\t\t\tEvent Player.PelatNamaDinonaktifkan = False;\n\t\t\tEvent Player.EfekNasibBerakhir = Total Time Elapsed + 15;\n\t\t\tSmall Message(Event Player, Custom String(\"TRY YOUR LUCK: ALL PLAYERS REVEALED — 15s\"));",
    "\t\tElse If(Event Player.EfekNasib == 6);\n\t\t\tEvent Player.PrivasiNasibAktif = True;\n\t\t\tEvent Player.EfekNasibBerakhir = Total Time Elapsed + 15;\n\t\t\tSmall Message(Event Player, Custom String(\"TRY YOUR LUCK: ALL PLAYER / BOT NAMES — 15s\"));",
    "Vision custom labels",
)

cleanup_old = (
    "\t\tClear Status(Event Player, Hacked);\n"
    "\t\tStop Accelerating(Event Player);\n"
    "\t\tStop Forcing Player Outlines(All Players(All Teams), Event Player);\n"
    "\t\tEnable Movement Collision With Environment(Event Player);"
)
cleanup_new = (
    "\t\tClear Status(Event Player, Hacked);\n"
    "\t\tStop Accelerating(Event Player);\n"
    "\t\tIf(Event Player.HudEfekNasib != Null);\n"
    "\t\t\tDestroy HUD Text(Event Player.HudEfekNasib);\n"
    "\t\tEnd;\n"
    "\t\tEvent Player.HudEfekNasib = Null;\n"
    "\t\tEnable Movement Collision With Environment(Event Player);"
)
source = replace_exact(source, cleanup_old, cleanup_new, "cleanup HUD morte/scadenza", expected=2)

source = replace_exact(
    source,
    "\t\tEvent Player.MenuTerbuka == False;\n\t\tEvent Player.TeleportasiJongkokAktif == False;\n\t\tEvent Player.TeleportasiJongkokDiaktifkan == True;",
    "\t\tEvent Player.MenuTerbuka == False;\n\t\tEvent Player.KartuNasibAktif == False;\n\t\tEvent Player.TeleportasiJongkokAktif == False;\n\t\tEvent Player.TeleportasiJongkokDiaktifkan == True;",
    "guard Crouch Teleport",
)

new_rules = r'''

rule("18i - Nasib: Vision crea nomi sopra ogni player e bot")
{
\tevent
\t{
\t\tOngoing - Each Player;
\t\tAll;
\t\tAll;
\t}

\tconditions
\t{
\t\tOr(Event Player.TeksVisiNasib == Null, Event Player.TeksVisiNasib == 0) == True;
\t\tIs Alive(Event Player) == True;
\t\tCount Of(Filtered Array(All Players(All Teams), And(Player Variable(Current Array Element, Manusia) == True,
\t\t\tPlayer Variable(Current Array Element, PrivasiNasibAktif) == True))) > 0;
\t}

\tactions
\t{
\t\tCreate In-World Text(Filtered Array(All Players(All Teams), And(Player Variable(Current Array Element, Manusia) == True,
\t\t\tPlayer Variable(Current Array Element, PrivasiNasibAktif) == True)), Custom String("{0}", Event Player),
\t\t\tEye Position(Event Player) + Vector(0, 0.450, 0), 1.100, Do Not Clip, Visible To Position String and Color,
\t\t\tEvent Player.Manusia == True ? Event Player.WarnaNama : Color(Orange), Visible Never);
\t\tEvent Player.TeksVisiNasib = Last Text ID;
\t}
}

rule("18j - Nasib: Vision pulisce i nomi quando non servono")
{
\tevent
\t{
\t\tOngoing - Each Player;
\t\tAll;
\t\tAll;
\t}

\tconditions
\t{
\t\tAnd(Event Player.TeksVisiNasib != Null, Event Player.TeksVisiNasib != 0) == True;
\t\tOr(Is Alive(Event Player) == False, Count Of(Filtered Array(All Players(All Teams), And(Player Variable(Current Array Element, Manusia) == True,
\t\t\tPlayer Variable(Current Array Element, PrivasiNasibAktif) == True))) == 0) == True;
\t}

\tactions
\t{
\t\tDestroy In-World Text(Event Player.TeksVisiNasib);
\t\tEvent Player.TeksVisiNasib = Null;
\t}
}

rule("18k - Nasib: HUD effetto e durata mentre il menu e chiuso")
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
\t\tEvent Player.PutaranKartuNasib == 0;
\t\tOr(Event Player.EfekNasibBerakhir > 0, Event Player.EfekNasib == 7) == True;
\t\tEvent Player.HudEfekNasib == Null;
\t\tIs Alive(Event Player) == True;
\t}

\tactions
\t{
\t\tCreate HUD Text(Event Player, Custom String("TRY YOUR LUCK"),
\t\t\tEvent Player.EfekNasib == 1 ? Custom String("HACKED")
\t\t\t: Event Player.EfekNasib == 2 ? Custom String("ULTIMATE ALWAYS READY")
\t\t\t: Event Player.EfekNasib == 4 ? Custom String("MOVE / JUMP / PROJECTILE x2")
\t\t\t: Event Player.EfekNasib == 5 ? Custom String("GRAVITY 10% / PROJECTILE 10%")
\t\t\t: Event Player.EfekNasib == 6 ? Custom String("VISION: ALL PLAYER / BOT NAMES")
\t\t\t: Event Player.EfekNasib == 7 ? Custom String("FLOOR REMOVED")
\t\t\t: Custom String("AIM-STEERED ACCELERATION"),
\t\t\tEvent Player.EfekNasib == 7 ? Custom String("UNTIL DEATH") : Custom String("{0}s REMAINING",
\t\t\t\tMax(0, Round To Integer(Event Player.EfekNasibBerakhir - Total Time Elapsed, Up))), Top, 100, Color(White),
\t\t\tCustom Color(255, 240, 190, 255), Custom Color(X Component Of(Event Player.WarnaMenu), Y Component Of(Event Player.WarnaMenu),
\t\t\t\tZ Component Of(Event Player.WarnaMenu), 255), Visible To String and Color, Visible Never);
\t\tEvent Player.HudEfekNasib = Last Text ID;
\t}
}
'''.replace('\\t', '\t')
source = replace_exact(
    source,
    '\nrule("19 - Teleportasi Jongkok: Buka tiga halaman selama Jongkok ditahan")',
    new_rules + '\nrule("19 - Teleportasi Jongkok: Buka tiga halaman selama Jongkok ditahan")',
    "insert Vision/HUD rules",
)

validator = replace_exact(
    validator,
    '"HasilNasibTerkunci", "MenuNasibHarusDibuka"):',
    '"HasilNasibTerkunci", "MenuNasibHarusDibuka", "HudEfekNasib", "TeksVisiNasib"):',
    "validator vars",
)
validator = replace_exact(
    validator,
    '    luck_expiry = find_rule(rules, "18h - Nasib:")\n    checks.require(luck is not None and luck_death is not None and luck_reopen is not None and luck_expiry is not None, "pipeline Try Your Luck a dieci risultati assente")',
    '    luck_expiry = find_rule(rules, "18h - Nasib:")\n    luck_vision_create = find_rule(rules, "18i - Nasib:")\n    luck_vision_cleanup = find_rule(rules, "18j - Nasib:")\n    luck_effect_hud = find_rule(rules, "18k - Nasib:")\n    checks.require(luck is not None and luck_death is not None and luck_reopen is not None and luck_expiry is not None and luck_vision_create is not None and luck_vision_cleanup is not None and luck_effect_hud is not None, "pipeline Try Your Luck a dieci risultati assente")',
    "validator pipeline",
)
validator = replace_exact(
    validator,
    '            "Set Projectile Speed(Event Player, 10);",\n            "Enable Nameplates(All Players(All Teams), Event Player);",\n            "Event Player.PelatNamaDinonaktifkan = False;",\n            "Disable Movement Collision With Environment(Event Player, True);",',
    '            "Set Projectile Speed(Event Player, 10);",\n            "Event Player.PrivasiNasibAktif = True;",\n            "Disable Movement Collision With Environment(Event Player, True);",',
    "validator Vision token",
)
validator = replace_exact(
    validator,
    '        checks.require("Start Forcing Player Outlines(" not in luck.body, "Vision Try Your Luck non deve usare outline")',
    '        checks.require("Start Forcing Player Outlines(" not in luck.body, "Vision Try Your Luck non deve usare outline")\n        checks.require("Enable Nameplates(All Players(All Teams), Event Player);" not in luck.body, "Vision Try Your Luck non deve dipendere dai nameplate standard")',
    "validator no nameplates",
)

outline_guard = '            "Stop Forcing Player Outlines(All Players(All Teams), Event Player);",\n'
validator = replace_exact(validator, outline_guard, '', "rimuovi guard cleanup outline legacy", expected=2)

# Specific reset guards without relying on duplicate tuple matchers.
death_anchor = '        checks.require("Call Subroutine(GambarMenu);" not in luck_death.body and "Event Player.MenuTerbuka = True;" not in luck_death.body, "morte Try Your Luck non deve mostrare il menu prima del respawn")\n'
validator = replace_exact(
    validator,
    death_anchor,
    death_anchor + '        checks.require("Destroy HUD Text(Event Player.HudEfekNasib);" in luck_death.body and "Event Player.HudEfekNasib = Null;" in luck_death.body, "morte Try Your Luck non pulisce HUD effetto")\n',
    "validator HUD morte",
)
expiry_anchor = '            checks.require(token in luck_expiry.body, f"18h reset scadenza incompleto: {token}")\n'
validator = replace_exact(
    validator,
    expiry_anchor,
    expiry_anchor + '        checks.require("Destroy HUD Text(Event Player.HudEfekNasib);" in luck_expiry.body and "Event Player.HudEfekNasib = Null;" in luck_expiry.body, "18h non pulisce HUD effetto")\n',
    "validator HUD expiry",
)

extra = '''    if luck_vision_create:\n        checks.equal(event_type(luck_vision_create), "Ongoing - Each Player", "18i Vision labels: scheduler")\n        checks.require("Create In-World Text(" in luck_vision_create.body and 'Custom String("{0}", Event Player)' in luck_vision_create.body, "18i Vision non crea nomi custom")\n        checks.require("Filtered Array(All Players(All Teams)" in luck_vision_create.body and "PrivasiNasibAktif) == True" in luck_vision_create.body, "18i Vision non limita i nomi agli osservatori Vision")\n        checks.require("Eye Position(Event Player) + Vector(0, 0.450, 0)" in luck_vision_create.body, "18i Vision non segue player/bot")\n        checks.require("Wait(" not in luck_vision_create.body and "Loop If Condition Is True;" not in luck_vision_create.body and "For Player Variable(" not in luck_vision_create.body, "18i Vision non deve usare Wait/Loop")\n    if luck_vision_cleanup:\n        checks.equal(event_type(luck_vision_cleanup), "Ongoing - Each Player", "18j Vision cleanup: scheduler")\n        checks.require("Destroy In-World Text(Event Player.TeksVisiNasib);" in luck_vision_cleanup.body, "18j non distrugge label Vision")\n        checks.require("Wait(" not in luck_vision_cleanup.body and "Loop If Condition Is True;" not in luck_vision_cleanup.body, "18j Vision cleanup non deve usare Wait/Loop")\n    if luck_effect_hud:\n        checks.equal(event_type(luck_effect_hud), "Ongoing - Each Player", "18k HUD effetto: scheduler")\n        checks.require('Create HUD Text(Event Player, Custom String("TRY YOUR LUCK")' in luck_effect_hud.body, "18k non crea HUD effetto")\n        checks.require("EfekNasibBerakhir - Total Time Elapsed" in luck_effect_hud.body and "s REMAINING" in luck_effect_hud.body, "18k non mostra countdown")\n        checks.require("UNTIL DEATH" in luck_effect_hud.body, "18k non mostra durata floor removed")\n        checks.require("Wait(" not in luck_effect_hud.body and "Loop If Condition Is True;" not in luck_effect_hud.body, "18k HUD effetto non deve usare Wait/Loop")\n    if teleport_open:\n        checks.require("Event Player.KartuNasibAktif == False;" in teleport_open.body, "Crouch Teleport deve essere disattivato durante Try Your Luck")\n    if luck and luck_expiry:\n        checks.require("TeleportasiJongkokDiaktifkan =" not in luck.body and "TeleportasiJongkokDiaktifkan =" not in luck_expiry.body, "Try Your Luck non deve cambiare la preferenza Crouch Teleport")\n'''
validator = replace_exact(validator, '    if fast_manager:\n', extra + '    if fast_manager:\n', "validator Vision/HUD/Teleport")

blob = git_blob_sha(source)
validator, n = re.subn(r'EXPECTED_SOURCE_BLOB = "[0-9a-f]{40}"', f'EXPECTED_SOURCE_BLOB = "{blob}"', validator, count=1)
if n != 1:
    raise RuntimeError("EXPECTED_SOURCE_BLOB non aggiornato")

SOURCE.write_text(source, encoding="utf-8")
VALIDATOR.write_text(validator, encoding="utf-8")
print(f"patched source blob: {blob}")
