from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
TESTS = ROOT / "tests" / "test_validate_workshop.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected 1 occurrence, found {count}")
    return text.replace(old, new, 1)


def replace_region(text: str, start: str, end: str, replacement: str, label: str) -> str:
    start_at = text.find(start)
    if start_at < 0:
        raise RuntimeError(f"{label}: start marker not found")
    end_at = text.find(end, start_at + len(start))
    if end_at < 0:
        raise RuntimeError(f"{label}: end marker not found")
    return text[:start_at] + replacement + text[end_at:]


source = SOURCE.read_text(encoding="utf-8")
validator = VALIDATOR.read_text(encoding="utf-8")
tests = TESTS.read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# Workshop: persistent player state for Try Your Luck.
# ---------------------------------------------------------------------------
source = replace_once(
    source,
    "\t\t80: JumlahSuara\n",
    "\t\t80: JumlahSuara\n"
    "\t\t81: ModeKebalTerakhir\n"
    "\t\t82: PosisiNasibTerkunci\n"
    "\t\t83: WarnaNasibTerkunci\n"
    "\t\t84: EfekNasibCahaya\n"
    "\t\t85: EfekNasibLingkaran\n"
    "\t\t86: RadiusNasib\n"
    "\t\t87: GerakNasibDikunci\n",
    "declare Try Your Luck state",
)

# While the roulette is active, keep the already-open page 10 locked: no new
# menu command is accepted until the outcome cleanup clears KartuNasibAktif.
source = replace_once(
    source,
    "\t\tEvent Player.MenuTerbuka == True;\n\t\tEvent Player.PerintahMenu == 0;\n",
    "\t\tEvent Player.MenuTerbuka == True;\n"
    "\t\tEvent Player.PerintahMenu == 0;\n"
    "\t\tEvent Player.KartuNasibAktif == False;\n",
    "lock menu dispatcher during roulette",
)

# Only explicit player changes update the remembered Unkillable preference.
source = replace_once(
    source,
    "\t\t\t\t\tEvent Player.ModeKebal = Event Player.KursorKebal;\n"
    "\t\t\t\t\tEvent Player.KebalAktif = Event Player.ModeKebal != 0;\n",
    "\t\t\t\t\tEvent Player.ModeKebalTerakhir = Event Player.KursorKebal;\n"
    "\t\t\t\t\tEvent Player.ModeKebal = Event Player.KursorKebal;\n"
    "\t\t\t\t\tEvent Player.KebalAktif = Event Player.ModeKebal != 0;\n",
    "remember player Unkillable choice",
)

# Replace page 10 activation. The menu stays open, is redrawn as ACTIVE, and
# the roulette temporarily forces FULL HP without overwriting the remembered
# player preference.
menu_start = "\t\tElse If(Event Player.HalamanMenu == 10);\n"
menu_end = "\t\tElse;\n\t\t\tIf(Count Of(Global.PemainManusia) > 0);"
menu_replacement = '''\t\tElse If(Event Player.HalamanMenu == 10);\n\t\t\tIf(Event Player.KartuNasibAktif == True);\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("The luck card is already rolling. Wait for the result.") : Event Player.IndeksBahasa == 1 ? Custom String("Kartu nasib sedang berputar. Tunggu hasilnya.") : Custom String("การ์ดเสี่ยงโชคกำลังสุ่มอยู่ รอผลก่อน"));\n\t\t\tElse;\n\t\t\t\tEvent Player.KartuNasibAktif = True;\n\t\t\t\tEvent Player.KartuNasibMerah = Random Integer(0, 1) == 0;\n\t\t\t\tEvent Player.PutaranKartuNasib = Random Integer(20, 24);\n\t\t\t\tEvent Player.JedaKartuNasib = 0.080;\n\t\t\t\tEvent Player.GerakNasibDikunci = False;\n\t\t\t\tEvent Player.PosisiNasibTerkunci = Position Of(Event Player);\n\t\t\t\tEvent Player.WarnaNasibTerkunci = Global.RGB;\n\t\t\t\tEvent Player.RadiusNasib = 0;\n\t\t\t\tEvent Player.EfekNasibCahaya = Null;\n\t\t\t\tEvent Player.EfekNasibLingkaran = Null;\n\t\t\t\t\"Proteksi roulette bersifat sementara: preferensi pemain tetap di ModeKebalTerakhir.\"\n\t\t\t\tEvent Player.ModeKebal = 2;\n\t\t\t\tEvent Player.KebalAktif = True;\n\t\t\t\tClear Status(Event Player, Unkillable);\n\t\t\t\tSet Status(Event Player, Null, Unkillable, 9999);\n\t\t\t\tSet Damage Received(Event Player, 0);\n\t\t\t\tIf(Is Alive(Event Player) == True);\n\t\t\t\t\tSet Player Health(Event Player, Max Health(Event Player));\n\t\t\t\tEnd;\n\t\t\t\tIf(Event Player.IkonKebal != Null);\n\t\t\t\t\tDestroy Icon(Event Player.IkonKebal);\n\t\t\t\tEnd;\n\t\t\t\tCreate Icon(All Players(All Teams), Event Player, Halo, Visible To and Position, Global.RGB, True);\n\t\t\t\tEvent Player.IkonKebal = Last Created Entity;\n\t\t\t\tCreate In-World Text(All Players(All Teams), Custom String("["), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 - Cross Product(Direction From Angles(Horizontal Facing Angle Of(Event Player), 0), Vector(0, 1, 0)) * 0.300), 2.200, Do Not Clip, Visible To Position String and Color, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Visible Never);\n\t\t\t\tEvent Player.TeksKartuNasib = Last Text ID;\n\t\t\t\tCreate In-World Text(All Players(All Teams), Custom String("]"), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 + Cross Product(Direction From Angles(Horizontal Facing Angle Of(Event Player), 0), Vector(0, 1, 0)) * 0.300), 2.200, Do Not Clip, Visible To Position String and Color, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Visible Never);\n\t\t\t\tEvent Player.TeksKartuNasibKanan = Last Text ID;\n\t\t\t\tCreate Icon(Event Player.KartuNasibMerah ? All Players(All Teams) : Empty Array, Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 - Vector(0, 0.450, 0)), Skull, Visible To and Position, Custom Color(255, 70, 70, 255), False);\n\t\t\t\tEvent Player.IkonKartuNasib = Last Created Entity;\n\t\t\t\tCreate Icon(Event Player.KartuNasibMerah ? Empty Array : All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 - Vector(0, 0.450, 0)), Heart, Visible To and Position, Custom Color(70, 255, 110, 255), False);\n\t\t\t\tEvent Player.IkonKartuNasibHijau = Last Created Entity;\n\t\t\t\tCall Subroutine(GambarMenu);\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Luck roulette started. Red or green?") : Event Player.IndeksBahasa == 1 ? Custom String("Roulette nasib dimulai. Merah atau hijau?") : Custom String("เริ่มรูเล็ตเสี่ยงโชคแล้ว แดงหรือเขียว?"));\n\t\t\tEnd;\n'''
source = replace_region(source, menu_start, menu_end, menu_replacement, "replace Try Your Luck menu branch")

# Replace the outcome rule. Red switches temporary FULL HP to OFF, freezes the
# player and creates RGB-frozen Light Shaft + shrinking floor Ring. Green
# restores the last player-selected Unkillable mode, while preserving the
# existing Spawn Room restriction for 1 HP.
luck_rule_start = 'rule("18e - Nasib: Undian merah hijau makin lambat")\n'
luck_rule_end = 'rule("18f - Nasib: Hapus kartu saat pemilik mati")\n'
luck_rule = '''rule("18e - Nasib: Undian merah hijau makin lambat")\n{\n\tevent\n\t{\n\t\tOngoing - Each Player;\n\t\tAll;\n\t\tAll;\n\t}\n\n\tconditions\n\t{\n\t\tEvent Player.Manusia == True;\n\t\tEvent Player.KartuNasibAktif == True;\n\t\tEvent Player.PutaranKartuNasib > 0;\n\t\tHas Spawned(Event Player) == True;\n\t\tIs Alive(Event Player) == True;\n\t}\n\n\tactions\n\t{\n\t\tWait(Event Player.JedaKartuNasib, Abort When False);\n\t\tEvent Player.KartuNasibMerah = Event Player.KartuNasibMerah == False;\n\t\tModify Player Variable(Event Player, PutaranKartuNasib, Subtract, 1);\n\t\tModify Player Variable(Event Player, JedaKartuNasib, Add, 0.055);\n\t\tLoop If Condition Is True;\n\t\tIf(Event Player.KartuNasibMerah == True);\n\t\t\t\"Il rosso spegne solo la protezione runtime; ModeKebalTerakhir resta la scelta del giocatore.\"\n\t\t\tEvent Player.KebalAktif = False;\n\t\t\tEvent Player.ModeKebal = 0;\n\t\t\tClear Status(Event Player, Unkillable);\n\t\t\tSet Damage Received(Event Player, 100);\n\t\t\tIf(Event Player.IkonKebal != Null);\n\t\t\t\tDestroy Icon(Event Player.IkonKebal);\n\t\t\t\tEvent Player.IkonKebal = Null;\n\t\t\tEnd;\n\t\t\tEvent Player.PosisiNasibTerkunci = Position Of(Event Player);\n\t\t\tEvent Player.WarnaNasibTerkunci = Global.RGB;\n\t\t\tEvent Player.GerakNasibDikunci = True;\n\t\t\tSet Move Speed(Event Player, 0);\n\t\t\tSet Knockback Received(Event Player, 0);\n\t\t\tStart Forcing Player Position(Event Player, Event Player.PosisiNasibTerkunci, False);\n\t\t\tEvent Player.RadiusNasib = 4;\n\t\t\tCreate Effect(All Players(All Teams), Light Shaft, Event Player.WarnaNasibTerkunci, Event Player.PosisiNasibTerkunci, Event Player.RadiusNasib, Visible To Position and Radius);\n\t\t\tEvent Player.EfekNasibCahaya = Last Created Entity;\n\t\t\tCreate Effect(All Players(All Teams), Ring, Event Player.WarnaNasibTerkunci, Event Player.PosisiNasibTerkunci + Vector(0, 0.050, 0), Event Player.RadiusNasib, Visible To Position and Radius);\n\t\t\tEvent Player.EfekNasibLingkaran = Last Created Entity;\n\t\t\tChase Player Variable Over Time(Event Player, RadiusNasib, 0.250, 3, Destination and Duration);\n\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("RED! Death in 3...") : Event Player.IndeksBahasa == 1 ? Custom String("MERAH! Mati dalam 3...") : Custom String("แดง! ตายใน 3..."));\n\t\t\tWait(1, Ignore Condition);\n\t\t\tAbort If(Event Player.KartuNasibAktif == False);\n\t\t\tAbort If(Event Player.PutaranKartuNasib > 0);\n\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("RED! Death in 2...") : Event Player.IndeksBahasa == 1 ? Custom String("MERAH! Mati dalam 2...") : Custom String("แดง! ตายใน 2..."));\n\t\t\tWait(1, Ignore Condition);\n\t\t\tAbort If(Event Player.KartuNasibAktif == False);\n\t\t\tAbort If(Event Player.PutaranKartuNasib > 0);\n\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("RED! Death in 1...") : Event Player.IndeksBahasa == 1 ? Custom String("MERAH! Mati dalam 1...") : Custom String("แดง! ตายใน 1..."));\n\t\t\tWait(1, Ignore Condition);\n\t\t\tAbort If(Event Player.KartuNasibAktif == False);\n\t\t\tAbort If(Event Player.PutaranKartuNasib > 0);\n\t\t\tKill(Event Player, Null);\n\t\t\tAbort;\n\t\tElse;\n\t\t\tClear Status(Event Player, Unkillable);\n\t\t\tEvent Player.ModeKebal = Event Player.ModeKebalTerakhir;\n\t\t\tEvent Player.KursorKebal = Event Player.ModeKebalTerakhir;\n\t\t\tIf(And(Event Player.ModeKebalTerakhir == 1, Is In Spawn Room(Event Player) == True));\n\t\t\t\tEvent Player.KebalAktif = False;\n\t\t\t\tEvent Player.ModeKebal = 0;\n\t\t\t\tSet Damage Received(Event Player, 100);\n\t\t\t\tSet Player Health(Event Player, Max Health(Event Player));\n\t\t\tElse If(Event Player.ModeKebalTerakhir == 0);\n\t\t\t\tEvent Player.KebalAktif = False;\n\t\t\t\tSet Damage Received(Event Player, 100);\n\t\t\t\tSet Player Health(Event Player, Max Health(Event Player));\n\t\t\tElse;\n\t\t\t\tEvent Player.KebalAktif = True;\n\t\t\t\tSet Status(Event Player, Null, Unkillable, 9999);\n\t\t\t\tIf(Event Player.ModeKebalTerakhir == 1);\n\t\t\t\t\tSet Damage Received(Event Player, 100);\n\t\t\t\t\tSet Player Health(Event Player, 1);\n\t\t\t\tElse;\n\t\t\t\t\tSet Damage Received(Event Player, 0);\n\t\t\t\t\tSet Player Health(Event Player, Max Health(Event Player));\n\t\t\t\tEnd;\n\t\t\tEnd;\n\t\t\tIf(Event Player.IkonKebal != Null);\n\t\t\t\tDestroy Icon(Event Player.IkonKebal);\n\t\t\t\tEvent Player.IkonKebal = Null;\n\t\t\tEnd;\n\t\t\tIf(Event Player.KebalAktif == True);\n\t\t\t\tIf(Event Player.ModeKebal == 1);\n\t\t\t\t\tCreate Icon(All Players(All Teams), Event Player, Warning, Visible To and Position, Custom Color(255, 80, 80, 255), True);\n\t\t\t\tElse;\n\t\t\t\t\tCreate Icon(All Players(All Teams), Event Player, Halo, Visible To and Position, Global.RGB, True);\n\t\t\t\tEnd;\n\t\t\t\tEvent Player.IkonKebal = Last Created Entity;\n\t\t\tEnd;\n\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("GREEN! Your last Unkillable setting is back.") : Event Player.IndeksBahasa == 1 ? Custom String("HIJAU! Pengaturan Kebal terakhirmu kembali.") : Custom String("เขียว! คืนค่าฆ่าไม่ตายล่าสุดของคุณแล้ว"));\n\t\t\tWait(1.500, Ignore Condition);\n\t\t\tAbort If(Event Player.KartuNasibAktif == False);\n\t\t\tAbort If(Event Player.PutaranKartuNasib > 0);\n\t\tEnd;\n\t\tIf(Event Player.TeksKartuNasib != Null);\n\t\t\tDestroy In-World Text(Event Player.TeksKartuNasib);\n\t\tEnd;\n\t\tIf(Event Player.TeksKartuNasibKanan != Null);\n\t\t\tDestroy In-World Text(Event Player.TeksKartuNasibKanan);\n\t\tEnd;\n\t\tIf(Event Player.IkonKartuNasib != Null);\n\t\t\tDestroy Icon(Event Player.IkonKartuNasib);\n\t\tEnd;\n\t\tIf(Event Player.IkonKartuNasibHijau != Null);\n\t\t\tDestroy Icon(Event Player.IkonKartuNasibHijau);\n\t\tEnd;\n\t\tEvent Player.TeksKartuNasib = Null;\n\t\tEvent Player.TeksKartuNasibKanan = Null;\n\t\tEvent Player.IkonKartuNasib = Null;\n\t\tEvent Player.IkonKartuNasibHijau = Null;\n\t\tEvent Player.KartuNasibAktif = False;\n\t\tEvent Player.PutaranKartuNasib = 0;\n\t\tEvent Player.JedaKartuNasib = 0;\n\t\tIf(And(Event Player.MenuTerbuka == True, Event Player.HalamanMenu == 10));\n\t\t\tCall Subroutine(GambarMenu);\n\t\tEnd;\n\t}\n}\n\n'''
source = replace_region(source, luck_rule_start, luck_rule_end, luck_rule + luck_rule_end, "replace Try Your Luck outcome")

# Death cleanup must release the forced red-state movement/effects before a
# respawn can inherit them.
death_cleanup_anchor = "\t\tEvent Player.KartuNasibAktif = False;\n\t\tEvent Player.KartuNasibMerah = False;\n"
death_cleanup_replacement = "\t\tStop Chasing Player Variable(Event Player, RadiusNasib);\n\t\tIf(Event Player.GerakNasibDikunci == True);\n\t\t\tStop Forcing Player Position(Event Player);\n\t\t\tSet Move Speed(Event Player, 100);\n\t\t\tSet Knockback Received(Event Player, 100);\n\t\tEnd;\n\t\tIf(Event Player.EfekNasibCahaya != Null);\n\t\t\tDestroy Effect(Event Player.EfekNasibCahaya);\n\t\tEnd;\n\t\tIf(Event Player.EfekNasibLingkaran != Null);\n\t\t\tDestroy Effect(Event Player.EfekNasibLingkaran);\n\t\tEnd;\n\t\tEvent Player.EfekNasibCahaya = Null;\n\t\tEvent Player.EfekNasibLingkaran = Null;\n\t\tEvent Player.RadiusNasib = 0;\n\t\tEvent Player.GerakNasibDikunci = False;\n\t\tEvent Player.KartuNasibAktif = False;\n\t\tEvent Player.KartuNasibMerah = False;\n"
source = replace_once(source, death_cleanup_anchor, death_cleanup_replacement, "death roulette cleanup")

# Common leave/team-switch cleanup gets the same safety release and restores
# knockback received in addition to movement speed.
source = replace_once(
    source,
    "\t\tSet Knockback Dealt(Event Player, 100);\n\t\tSet Damage Received(Event Player, 100);\n\t\tSet Move Speed(Event Player, 100);\n",
    "\t\tSet Knockback Dealt(Event Player, 100);\n"
    "\t\tSet Knockback Received(Event Player, 100);\n"
    "\t\tSet Damage Received(Event Player, 100);\n"
    "\t\tSet Move Speed(Event Player, 100);\n"
    "\t\tStop Forcing Player Position(Event Player);\n"
    "\t\tStop Chasing Player Variable(Event Player, RadiusNasib);\n",
    "restore movement in common cleanup",
)
source = replace_once(
    source,
    "\t\tEvent Player.KartuNasibAktif = False;\n\t\tEvent Player.KartuNasibMerah = False;\n\t\tEvent Player.PutaranKartuNasib = 0;\n\t\tEvent Player.JedaKartuNasib = 0;\n\t\tGlobal.PemainPembersihan = Event Player;\n",
    "\t\tIf(Event Player.EfekNasibCahaya != Null);\n"
    "\t\t\tDestroy Effect(Event Player.EfekNasibCahaya);\n"
    "\t\tEnd;\n"
    "\t\tIf(Event Player.EfekNasibLingkaran != Null);\n"
    "\t\t\tDestroy Effect(Event Player.EfekNasibLingkaran);\n"
    "\t\tEnd;\n"
    "\t\tEvent Player.EfekNasibCahaya = Null;\n"
    "\t\tEvent Player.EfekNasibLingkaran = Null;\n"
    "\t\tEvent Player.RadiusNasib = 0;\n"
    "\t\tEvent Player.GerakNasibDikunci = False;\n"
    "\t\tEvent Player.KartuNasibAktif = False;\n"
    "\t\tEvent Player.KartuNasibMerah = False;\n"
    "\t\tEvent Player.PutaranKartuNasib = 0;\n"
    "\t\tEvent Player.JedaKartuNasib = 0;\n"
    "\t\tGlobal.PemainPembersihan = Event Player;\n",
    "common roulette effect cleanup",
)

# Initialize every new per-player field so lifecycle validation remains strict.
source = replace_once(
    source,
    "\t\tEvent Player.JumlahSuara = 0;\n\t\tEvent Player.KartuNasibMerah = False;\n",
    "\t\tEvent Player.JumlahSuara = 0;\n"
    "\t\tEvent Player.ModeKebalTerakhir = 0;\n"
    "\t\tEvent Player.PosisiNasibTerkunci = Vector(0, 0, 0);\n"
    "\t\tEvent Player.WarnaNasibTerkunci = Color(White);\n"
    "\t\tEvent Player.EfekNasibCahaya = Null;\n"
    "\t\tEvent Player.EfekNasibLingkaran = Null;\n"
    "\t\tEvent Player.RadiusNasib = 0;\n"
    "\t\tEvent Player.GerakNasibDikunci = False;\n"
    "\t\tEvent Player.KartuNasibMerah = False;\n",
    "initialize Try Your Luck state",
)

# Camera and teleport menus should never offer dead entities as candidates.
source = replace_once(
    source,
    "Event Player.DaftarTargetKamera = Filtered Array(All Players(All Teams), And(Current Array Element != Event Player, Has Spawned(\n\t\t\tCurrent Array Element)));",
    "Event Player.DaftarTargetKamera = Filtered Array(All Players(All Teams), And(Current Array Element != Event Player, And(Entity Exists(\n\t\t\tCurrent Array Element), And(Has Spawned(Current Array Element), Is Alive(Current Array Element)))));",
    "camera alive target filter",
)
source = replace_once(
    source,
    "Event Player.DaftarTargetTeleportasi = Append To Array(Array(Event Player, Null), Filtered Array(All Players(All Teams),\n\t\t\tAnd(Current Array Element != Event Player, Has Spawned(Current Array Element))));",
    "Event Player.DaftarTargetTeleportasi = Append To Array(Array(Event Player, Null), Filtered Array(All Players(All Teams),\n\t\t\tAnd(Current Array Element != Event Player, And(Entity Exists(Current Array Element), And(Has Spawned(Current Array Element), Is Alive(Current Array Element))))));",
    "teleport alive target filter",
)

# Capture The Flag execution now gets the same unavailable guard as the HUD.
source = replace_once(
    source,
    "\t\t\tElse If(Current Game Mode == Game Mode(Capture The Flag));\n"
    "\t\t\t\tTeleport(Event Player, Nearest Walkable Position(Flag Position(Opposite Team Of(Team Of(Event Player))) + Vector(2, 0, 0)));\n"
    "\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String(\"Teleported near the enemy flag.\") : Event Player.IndeksBahasa == 1 ? Custom String(\"Teleport dekat bendera musuh.\") : Custom String(\"เทเลพอร์ตใกล้ธงของศัตรูแล้ว\"));\n",
    "\t\t\tElse If(Current Game Mode == Game Mode(Capture The Flag));\n"
    "\t\t\t\tIf(Distance Between(Flag Position(Opposite Team Of(Team Of(Event Player))), Vector(0, 0, 0)) <= 0.100);\n"
    "\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String(\"Enemy flag position unavailable right now.\") : Event Player.IndeksBahasa == 1 ? Custom String(\"Posisi bendera musuh belum tersedia saat ini.\") : Custom String(\"ตำแหน่งธงศัตรูยังไม่พร้อมใช้งานตอนนี้\"));\n"
    "\t\t\t\tElse;\n"
    "\t\t\t\t\tTeleport(Event Player, Nearest Walkable Position(Flag Position(Opposite Team Of(Team Of(Event Player))) + Vector(2, 0, 0)));\n"
    "\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String(\"Teleported near the enemy flag.\") : Event Player.IndeksBahasa == 1 ? Custom String(\"Teleport dekat bendera musuh.\") : Custom String(\"เทเลพอร์ตใกล้ธงของศัตรูแล้ว\"));\n"
    "\t\t\t\tEnd;\n",
    "CTF objective validity guard",
)

# The objective availability text now mirrors the mode-specific execution
# sources: payload, enemy flag, Push player/objective fallback, or objective.
old_hud_guard = "And(Current Game Mode != Game Mode(Capture The Flag), Distance Between(Objective Position(Objective Index), Vector(0, 0, 0)) <= 0.100)"
new_hud_guard = "Or(Or(And(Or(Current Game Mode == Game Mode(Escort), Current Game Mode == Game Mode(Hybrid)), Distance Between(Payload Position, Vector(0, 0, 0)) <= 0.100), And(Current Game Mode == Game Mode(Capture The Flag), Distance Between(Flag Position(Opposite Team Of(Team Of(Event Player))), Vector(0, 0, 0)) <= 0.100)), Or(And(Current Game Mode == Game Mode(Push), And(Count Of(Filtered Array(All Players(All Teams), And(Has Spawned(Current Array Element) == True, And(Is Alive(Current Array Element) == True, Is On Objective(Current Array Element) == True)))) == 0, Distance Between(Objective Position(Objective Index), Vector(0, 0, 0)) <= 0.100)), And(And(Current Game Mode != Game Mode(Escort), Current Game Mode != Game Mode(Hybrid)), And(And(Current Game Mode != Game Mode(Capture The Flag), Current Game Mode != Game Mode(Push)), Distance Between(Objective Position(Objective Index), Vector(0, 0, 0)) <= 0.100))))"
if source.count(old_hud_guard) != 3:
    raise RuntimeError(f"teleport HUD guard: expected 3 occurrences, found {source.count(old_hud_guard)}")
source = source.replace(old_hud_guard, new_hud_guard)

# ---------------------------------------------------------------------------
# Validator: replace the old 'roulette forces OFF + closes menu' invariant
# with the intended locked-menu / temporary FULL HP / red freeze / green
# preference-restore invariants. Keep the confirmed 1 HP max-health behavior.
# ---------------------------------------------------------------------------
old_validator_block = '''        for token in (\n            "Event Player.KebalAktif = False;",\n            "Event Player.ModeKebal = 0;",\n            "Event Player.KursorKebal = 0;",\n            "Clear Status(Event Player, Unkillable);",\n            "Set Damage Received(Event Player, 100);",\n            "Destroy Icon(Event Player.IkonKebal);",\n        ):\n            checks.require(token in before_luck, f"Nasib: avvio carta non forza Unkillable OFF: {token}")\n        checks.require(\n            "Call Subroutine(TutupMenu);" in after_luck,\n            "Nasib: il menu non viene chiuso quando parte la carta",\n        )\n        checks.require(\n            "Call Subroutine(GambarMenu);" not in luck_only,\n            "Nasib: il menu viene ridisegnato dopo l'avvio della carta",\n        )\n'''
new_validator_block = '''        for token in (\n            "Event Player.ModeKebal = 2;",\n            "Event Player.KebalAktif = True;",\n            "Set Status(Event Player, Null, Unkillable, 9999);",\n            "Set Damage Received(Event Player, 0);",\n            "Set Player Health(Event Player, Max Health(Event Player));",\n        ):\n            checks.require(token in luck_only, f"Nasib: avvio carta non forza temporaneamente FULL HP: {token}")\n        checks.require(\n            "Call Subroutine(TutupMenu);" not in luck_only,\n            "Nasib: il menu 10 non deve chiudersi quando parte la carta",\n        )\n        checks.require(\n            "Call Subroutine(GambarMenu);" in luck_only,\n            "Nasib: il menu 10 non resta visibile come ACTIVE durante la roulette",\n        )\n        checks.require(\n            "Event Player.KartuNasibAktif == False;" in mask_strings(next(\n                rule.body for rule in rules if rule.name.startswith("05c - Menu:")\n            )),\n            "Nasib: dispatcher menu non bloccato durante la roulette",\n        )\n'''
validator = replace_once(validator, old_validator_block, new_validator_block, "validator locked Try Your Luck menu")

# Extend validator expectations for the new outcome behavior and robust target
# filters. Insert next to the existing roulette assertions.
validator = replace_once(
    validator,
    "        checks.require(luck_code.count(\"Abort If(Event Player.PutaranKartuNasib > 0);\") >= 4, \"Nasib: una vecchia outcome può interferire con una nuova roulette\")\n",
    "        checks.require(luck_code.count(\"Abort If(Event Player.PutaranKartuNasib > 0);\") >= 4, \"Nasib: una vecchia outcome può interferire con una nuova roulette\")\n"
    "        for token in (\n"
    "            \"Event Player.ModeKebalTerakhir\",\n"
    "            \"Event Player.ModeKebal = 0;\",\n"
    "            \"Set Move Speed(Event Player, 0);\",\n"
    "            \"Set Knockback Received(Event Player, 0);\",\n"
    "            \"Start Forcing Player Position(Event Player, Event Player.PosisiNasibTerkunci, False);\",\n"
    "            \"Create Effect(All Players(All Teams), Light Shaft, Event Player.WarnaNasibTerkunci\",\n"
    "            \"Create Effect(All Players(All Teams), Ring, Event Player.WarnaNasibTerkunci\",\n"
    "            \"Chase Player Variable Over Time(Event Player, RadiusNasib, 0.250, 3, Destination and Duration);\",\n"
    "        ):\n"
    "            checks.require(token in luck_code, f\"Nasib: sequenza rosso/verde incompleta: {token}\")\n",
    "validator roulette red/green invariants",
)

# The old menu validator explicitly required the obsolete Objective Position
# guard three times. It must now require the mode-specific guard instead.
validator = replace_once(
    validator,
    "    checks.equal(\n        source.count('And(Current Game Mode != Game Mode(Capture The Flag), Distance Between(Objective Position(Objective Index), Vector(0, 0, 0)) <= 0.100) ? Custom String('),\n        3,\n        \"HUD teleport CTF non deve mostrare unavailable basandosi su Objective Position\",\n    )\n",
    "    checks.equal(\n"
    "        source.count('Distance Between(Flag Position(Opposite Team Of(Team Of(Event Player))), Vector(0, 0, 0)) <= 0.100'),\n"
    "        4,\n"
    "        \"HUD/esecuzione teleport CTF devono controllare la posizione della bandiera\",\n"
    "    )\n",
    "validator teleport HUD mode guard",
)

# Add explicit positive-alive checks for camera/teleport candidate lists.
validator = replace_once(
    validator,
    "    checks.require(\n        after_refresh.rfind(\"EventPlayer.TargetTeleportasiTerkunci=Null;\")\n        > after_refresh.find(\"Teleport(EventPlayer\"),\n        \"Teleport: identità catturata non azzerata dopo l'azione\",\n    )\n",
    "    checks.require(\n"
    "        after_refresh.rfind(\"EventPlayer.TargetTeleportasiTerkunci=Null;\")\n"
    "        > after_refresh.find(\"Teleport(EventPlayer\"),\n"
    "        \"Teleport: identità catturata non azzerata dopo l'azione\",\n"
    "    )\n"
    "    refresh_rules = rules_containing(rules, \"Subroutine;\", \"SegarkanTargetTeleportasi;\")\n"
    "    checks.equal(len(refresh_rules), 1, \"subroutine target Teleport\")\n"
    "    if refresh_rules:\n"
    "        refresh_code = re.sub(r\"\\s+\", \"\", mask_strings(refresh_rules[0].body))\n"
    "        checks.require(\"EntityExists(CurrentArrayElement)\" in refresh_code and \"IsAlive(CurrentArrayElement)\" in refresh_code, \"Teleport: candidati morti/non esistenti non filtrati\")\n",
    "validator teleport alive candidates",
)

# Camera check already receives all rules; require the positive alive filter in
# SegarkanTargetKamera without changing its camera rendering invariants.
validator = replace_once(
    validator,
    "    camera_loops = [\n",
    "    camera_refresh = rules_containing(rules, \"Subroutine;\", \"SegarkanTargetKamera;\")\n"
    "    checks.equal(len(camera_refresh), 1, \"subroutine target Camera\")\n"
    "    if camera_refresh:\n"
    "        refresh_code = re.sub(r\"\\s+\", \"\", mask_strings(camera_refresh[0].body))\n"
    "        checks.require(\"EntityExists(CurrentArrayElement)\" in refresh_code and \"IsAlive(CurrentArrayElement)\" in refresh_code, \"Camera: candidati morti/non esistenti non filtrati\")\n"
    "    camera_loops = [\n",
    "validator camera alive candidates",
)

# Existing death-reset validator must also require release of red movement and
# destruction of the two persistent effects.
validator = replace_once(
    validator,
    "                \"Event Player.IkonKartuNasibHijau = Null;\",\n            ),\n            \"Nasib: morte prima della fine non resetta completamente la carta\",\n",
    "                \"Event Player.IkonKartuNasibHijau = Null;\",\n"
    "                \"Stop Forcing Player Position(Event Player);\",\n"
    "                \"Set Move Speed(Event Player, 100);\",\n"
    "                \"Set Knockback Received(Event Player, 100);\",\n"
    "                \"Destroy Effect(Event Player.EfekNasibCahaya);\",\n"
    "                \"Destroy Effect(Event Player.EfekNasibLingkaran);\",\n"
    "            ),\n"
    "            \"Nasib: morte prima della fine non resetta completamente la carta\",\n",
    "validator death red-state cleanup",
)

# ---------------------------------------------------------------------------
# Negative tests for the new invariants. Keep the confirmed 1 HP test intact.
# ---------------------------------------------------------------------------
insert_before = "\n    def test_voice_normal_stop_is_required(self) -> None:\n"
new_tests = '''\n    def test_luck_menu_must_stay_open_and_locked(self) -> None:\n        mutated = self.source.replace(\n            "Event Player.KartuNasibAktif == False;",\n            '"Event Player.KartuNasibAktif == False;"',\n            1,\n        )\n        self.assertNotEqual(mutated, self.source)\n        checks = validator.Checks()\n        validator.check_arcade_features(checks, mutated, self.rules(mutated))\n        self.assertTrue(any("dispatcher menu non bloccato" in error for error in checks.errors), checks.errors)\n\n    def test_luck_red_must_force_position_and_shrink_ring(self) -> None:\n        mutated = self.source.replace(\n            "Start Forcing Player Position(Event Player, Event Player.PosisiNasibTerkunci, False);",\n            '"Start Forcing Player Position(Event Player, Event Player.PosisiNasibTerkunci, False);"',\n            1,\n        )\n        self.assertNotEqual(mutated, self.source)\n        checks = validator.Checks()\n        validator.check_arcade_features(checks, mutated, self.rules(mutated))\n        self.assertTrue(any("sequenza rosso/verde incompleta" in error for error in checks.errors), checks.errors)\n\n    def test_camera_dead_candidate_is_rejected(self) -> None:\n        refresh_at = self.source.index('rule("95 - ')\n        mutated = self.source[:refresh_at] + self.source[refresh_at:].replace(\n            "Is Alive(Current Array Element)",\n            "Is Alive(Current Array Element) == False",\n            1,\n        )\n        checks = validator.Checks()\n        _, player_names, _ = validator.declaration_tables(mutated)\n        validator.check_camera(checks, mutated, self.rules(mutated), player_names)\n        self.assertTrue(any("candidati morti" in error for error in checks.errors), checks.errors)\n\n    def test_teleport_dead_candidate_is_rejected(self) -> None:\n        refresh_at = self.source.index('rule("98 - ')\n        mutated = self.source[:refresh_at] + self.source[refresh_at:].replace(\n            "Is Alive(Current Array Element)",\n            "Is Alive(Current Array Element) == False",\n            1,\n        )\n        checks = validator.Checks()\n        validator.check_teleport(checks, mutated, self.rules(mutated))\n        self.assertTrue(any("candidati morti" in error for error in checks.errors), checks.errors)\n'''
if insert_before not in tests:
    raise RuntimeError("test insertion marker not found")
tests = tests.replace(insert_before, new_tests + insert_before, 1)

SOURCE.write_text(source, encoding="utf-8")
VALIDATOR.write_text(validator, encoding="utf-8")
TESTS.write_text(tests, encoding="utf-8")
