from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"

OLD_BLOB = "d1ab0f0537294be81ae7d535635be0122efc0502"


def blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def one(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one match, found {count}: {old[:140]!r}")
    return text.replace(old, new, 1)


def rule_bounds(text: str, title: str) -> tuple[int, int]:
    needle = f'rule("{title}")'
    start = text.index(needle)
    nxt = text.find('\nrule("', start + len(needle))
    return start, len(text) if nxt < 0 else nxt


def replace_rule(text: str, title: str, block: str) -> str:
    start, end = rule_bounds(text, title)
    return text[:start] + block.rstrip() + "\n\n" + text[end:].lstrip("\n")


def edit_rule(text: str, title: str, editor) -> str:
    start, end = rule_bounds(text, title)
    block = text[start:end]
    new = editor(block)
    if new == block:
        raise RuntimeError(f"rule unchanged: {title}")
    return text[:start] + new + text[end:]


source = SOURCE.read_text(encoding="utf-8")
if blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch moving target")

# ---------------------------------------------------------------------------
# Menu page 10: start a ten-outcome roulette. Hero input capture is already
# handled by the validated Crouch menu dispatcher.
# ---------------------------------------------------------------------------
def edit_interact(block: str) -> str:
    start_marker = "\t\tElse If(Event Player.HalamanMenu == 10);"
    end_marker = "\n\t\tElse;\n\t\t\tIf(Count Of(Global.PemainManusia) > 0);"
    start = block.index(start_marker)
    end = block.index(end_marker, start)
    replacement = r'''		Else If(Event Player.HalamanMenu == 10);
			If(Event Player.KartuNasibAktif == True);
				Small Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Try Your Luck is still active. Wait for it to finish.") : Event Player.IndeksBahasa == 1 ? Custom String("Try Your Luck masih aktif. Tunggu sampai selesai.") : Custom String("Try Your Luck ยังทำงานอยู่ รอให้จบก่อน"));
			Else;
				Event Player.KartuNasibAktif = True;
				Event Player.EfekNasib = Random Integer(1, 10);
				Event Player.PutaranKartuNasib = Random Integer(20, 24);
				Event Player.JedaKartuNasib = 0.080;
				Event Player.KartuNasibMerah = False;
				Event Player.EfekNasibBerakhir = 0;
				Event Player.DaftarTujuanNasib = Empty Array;
				Event Player.TujuanNasib = Vector(0, 0, 0);
				Event Player.ArahNasib = Vector(0, 0, 0);
				Event Player.PrivasiNasibAktif = False;
				Event Player.KategoriTeleportNasib = -1;
				Event Player.HasilNasibTerkunci = 0;
				If(Event Player.IkonKartuNasib != Null);
					Destroy Icon(Event Player.IkonKartuNasib);
				End;
				If(Event Player.IkonKartuNasibHijau != Null);
					Destroy Icon(Event Player.IkonKartuNasibHijau);
				End;
				Event Player.IkonKartuNasib = Null;
				Event Player.IkonKartuNasibHijau = Null;
				"Proteksi hanya selama roulette; pilihan Unkillable pemain disimpan di ModeKebalTerakhir."
				Event Player.ModeKebal = 2;
				Event Player.KebalAktif = True;
				Clear Status(Event Player, Unkillable);
				Set Status(Event Player, Null, Unkillable, 9999);
				Set Damage Received(Event Player, 0);
				Set Player Health(Event Player, Max Health(Event Player));
				If(Event Player.IkonKebal != Null);
					Destroy Icon(Event Player.IkonKebal);
				End;
				Create Icon(All Players(All Teams), Event Player, Halo, Visible To and Position, Global.RGB, True);
				Event Player.IkonKebal = Last Created Entity;
				Call Subroutine(GambarMenu);
				Small Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Try Your Luck: ten outcomes are rolling.") : Event Player.IndeksBahasa == 1 ? Custom String("Try Your Luck: sepuluh hasil sedang diacak.") : Custom String("Try Your Luck: กำลังสุ่มสิบผลลัพธ์"));
			End;'''
    return block[:start] + replacement + block[end:]

source = edit_rule(source, "10 - Menu: Interaksi membuka atau menerapkan pilihan", edit_interact)

# ---------------------------------------------------------------------------
# Roulette + all ten outcomes.
# ---------------------------------------------------------------------------
luck_rule = r'''rule("18e - Nasib: Roulette sepuluh efek dengan hasil terkunci")
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
		Event Player.EfekNasib = Random Integer(1, 10);
		If(Event Player.EfekNasib == 1);
			Create Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Poison 2, Visible To and Position, Custom Color(170, 80, 255, 255), False);
		Else If(Event Player.EfekNasib == 2);
			Create Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Halo, Visible To and Position, Custom Color(255, 220, 70, 255), False);
		Else If(Event Player.EfekNasib == 3);
			Create Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Spiral, Visible To and Position, Color(Turquoise), False);
		Else If(Event Player.EfekNasib == 4);
			Create Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Bolt, Visible To and Position, Color(Yellow), False);
		Else If(Event Player.EfekNasib == 5);
			Create Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Moon, Visible To and Position, Color(Sky Blue), False);
		Else If(Event Player.EfekNasib == 6);
			Create Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Eye, Visible To and Position, Color(Aqua), False);
		Else If(Event Player.EfekNasib == 7);
			Create Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Warning, Visible To and Position, Color(Orange), False);
		Else If(Event Player.EfekNasib == 8);
			Create Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Dizzy, Visible To and Position, Color(Violet), False);
		Else If(Event Player.EfekNasib == 9);
			Create Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Skull, Visible To and Position, Custom Color(255, 70, 70, 255), False);
		Else;
			Create Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Heart, Visible To and Position, Custom Color(70, 255, 110, 255), False);
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
		Event Player.EfekNasibBerakhir = 0;
		Event Player.HasilNasibTerkunci = 0;

		If(Event Player.EfekNasib == 1);
			Set Status(Event Player, Null, Hacked, 5);
			Event Player.EfekNasibBerakhir = Total Time Elapsed + 5;
			Small Message(Event Player, Custom String("TRY YOUR LUCK: HACKED — 5s"));
		Else If(Event Player.EfekNasib == 2);
			Event Player.HasilNasibTerkunci = Ultimate Charge Percent(Event Player);
			Set Ultimate Charge(Event Player, 100);
			Event Player.EfekNasibBerakhir = Total Time Elapsed + 10;
			Small Message(Event Player, Custom String("TRY YOUR LUCK: ULTIMATE ALWAYS READY — 10s"));
		Else If(Event Player.EfekNasib == 3);
			Event Player.DaftarTujuanNasib = Empty Array;
			If(Count Of(Filtered Array(All Players(All Teams), And(Current Array Element != Event Player, And(Entity Exists(Current Array Element), And(Is Alive(Current Array Element), Or(Is Dummy Bot(Current Array Element) == True, Player Variable(Current Array Element, BotOtomatis) == True)))))) > 0);
				Event Player.DaftarTujuanNasib = Append To Array(Event Player.DaftarTujuanNasib, 0);
			End;
			If(Or(Current Game Mode == Game Mode(Escort), Current Game Mode == Game Mode(Hybrid)));
				If(Distance Between(Payload Position, Vector(0, 0, 0)) > 0.100);
					Event Player.DaftarTujuanNasib = Append To Array(Event Player.DaftarTujuanNasib, 1);
				End;
			Else If(Current Game Mode == Game Mode(Capture The Flag));
				If(Distance Between(Flag Position(Opposite Team Of(Team Of(Event Player))), Vector(0, 0, 0)) > 0.100);
					Event Player.DaftarTujuanNasib = Append To Array(Event Player.DaftarTujuanNasib, 1);
				End;
			Else If(Distance Between(Objective Position(Objective Index), Vector(0, 0, 0)) > 0.100);
				Event Player.DaftarTujuanNasib = Append To Array(Event Player.DaftarTujuanNasib, 1);
			End;
			If(Count Of(Filtered Array(Global.PemainManusia, And(Current Array Element != Event Player, And(Entity Exists(Current Array Element), Is Alive(Current Array Element))))) > 0);
				Event Player.DaftarTujuanNasib = Append To Array(Event Player.DaftarTujuanNasib, 2);
			End;
			If(Count Of(Spawn Points(Team Of(Event Player))) > 0);
				Event Player.DaftarTujuanNasib = Append To Array(Event Player.DaftarTujuanNasib, 3);
			End;
			If(Count Of(Event Player.DaftarTujuanNasib) == 0);
				Small Message(Event Player, Custom String("TRY YOUR LUCK: no random teleport destination available."));
			Else;
				Event Player.KategoriTeleportNasib = Random Value In Array(Event Player.DaftarTujuanNasib);
				If(Event Player.KategoriTeleportNasib == 0);
					Event Player.TujuanNasib = Position Of(Random Value In Array(Filtered Array(All Players(All Teams), And(Current Array Element != Event Player, And(Entity Exists(Current Array Element), And(Is Alive(Current Array Element), Or(Is Dummy Bot(Current Array Element) == True, Player Variable(Current Array Element, BotOtomatis) == True)))))));
				Else If(Event Player.KategoriTeleportNasib == 1);
					If(Or(Current Game Mode == Game Mode(Escort), Current Game Mode == Game Mode(Hybrid)));
						Event Player.TujuanNasib = Payload Position;
					Else If(Current Game Mode == Game Mode(Capture The Flag));
						Event Player.TujuanNasib = Flag Position(Opposite Team Of(Team Of(Event Player)));
					Else;
						Event Player.TujuanNasib = Objective Position(Objective Index);
					End;
				Else If(Event Player.KategoriTeleportNasib == 2);
					Event Player.TujuanNasib = Position Of(Random Value In Array(Filtered Array(Global.PemainManusia, And(Current Array Element != Event Player, And(Entity Exists(Current Array Element), Is Alive(Current Array Element))))));
				Else;
					Event Player.TujuanNasib = Position Of(Random Value In Array(Spawn Points(Team Of(Event Player))));
				End;
				Teleport(Event Player, Nearest Walkable Position(Event Player.TujuanNasib));
				Small Message(Event Player, Custom String("TRY YOUR LUCK: RANDOM TELEPORT"));
			End;
			Event Player.EfekNasib = 0;
			Event Player.KartuNasibAktif = False;
		Else If(Event Player.EfekNasib == 4);
			Set Move Speed(Event Player, 200);
			Set Jump Vertical Speed(Event Player, 200);
			Set Projectile Speed(Event Player, 200);
			Event Player.EfekNasibBerakhir = Total Time Elapsed + 15;
			Small Message(Event Player, Custom String("TRY YOUR LUCK: MOVE / JUMP / PROJECTILE x2 — 15s"));
		Else If(Event Player.EfekNasib == 5);
			Set Gravity(Event Player, 10);
			Set Projectile Speed(Event Player, 10);
			Event Player.EfekNasibBerakhir = Total Time Elapsed + 20;
			Small Message(Event Player, Custom String("TRY YOUR LUCK: GRAVITY 10% + PROJECTILE SPEED 10% — 20s"));
		Else If(Event Player.EfekNasib == 6);
			Event Player.PrivasiNasibAktif = True;
			Start Forcing Player Outlines(All Players(All Teams), Event Player, True, Color(White), Always);
			Event Player.EfekNasibBerakhir = Total Time Elapsed + 15;
			Small Message(Event Player, Custom String("TRY YOUR LUCK: ALL PLAYERS REVEALED — 15s"));
		Else If(Event Player.EfekNasib == 7);
			Event Player.KebalAktif = False;
			Event Player.ModeKebal = 0;
			Clear Status(Event Player, Unkillable);
			Set Damage Received(Event Player, 100);
			Set Status(Event Player, Null, Knocked Down, 9999);
			Disable Movement Collision With Environment(Event Player, True);
			Apply Impulse(Event Player, Vector(0, -1, 0), 5, To World, Cancel Contrary Motion);
			Small Message(Event Player, Custom String("TRY YOUR LUCK: FLOOR REMOVED"));
		Else If(Event Player.EfekNasib == 8);
			Event Player.ArahNasib = Direction From Angles(Random Real(-180, 180), Random Real(-45, 45));
			Set Move Speed(Event Player, 1000);
			Start Accelerating(Event Player, Event Player.ArahNasib, 50, 25, To World, None);
			Event Player.EfekNasibBerakhir = Total Time Elapsed + 5;
			Small Message(Event Player, Custom String("TRY YOUR LUCK: RANDOM ACCELERATION — 5s"));
		Else If(Event Player.EfekNasib == 9);
			Event Player.KebalAktif = False;
			Event Player.ModeKebal = 0;
			Clear Status(Event Player, Unkillable);
			Set Damage Received(Event Player, 100);
			Small Message(Event Player, Custom String("TRY YOUR LUCK: SKULL"));
			Kill(Event Player, Null);
		Else;
			Set Player Health(All Living Players(Team Of(Event Player)), 9999);
			Small Message(All Living Players(Team Of(Event Player)), Custom String("TRY YOUR LUCK: HEART — TEAM FULL HEAL"));
			Event Player.EfekNasib = 0;
			Event Player.KartuNasibAktif = False;
		End;

		Wait(1, Ignore Condition);
		If(Event Player.IkonKartuNasib != Null);
			Destroy Icon(Event Player.IkonKartuNasib);
		End;
		Event Player.IkonKartuNasib = Null;
		Event Player.IkonKartuNasibHijau = Null;
		Event Player.PutaranKartuNasib = 0;
		Event Player.JedaKartuNasib = 0;
		If(And(Event Player.MenuTerbuka == True, Event Player.HalamanMenu == 10));
			Call Subroutine(GambarMenu);
		End;
	}
}'''
source = replace_rule(source, "18e - Nasib: Undian merah hijau makin lambat", luck_rule)

# ---------------------------------------------------------------------------
# Death reset: every temporary gameplay modification is restored before the
# player's normal Unkillable preference is rebuilt.
# ---------------------------------------------------------------------------
death_rule = r'''rule("18f - Nasib: Reset lengkap semua efek saat pemilik mati")
{
	event
	{
		Player Died;
		All;
		All;
	}

	conditions
	{
		Event Player.KartuNasibAktif == True;
	}

	actions
	{
		If(Event Player.IkonKartuNasib != Null);
			Destroy Icon(Event Player.IkonKartuNasib);
		End;
		If(Event Player.IkonKartuNasibHijau != Null);
			Destroy Icon(Event Player.IkonKartuNasibHijau);
		End;
		If(Event Player.EfekNasib == 2);
			Set Ultimate Charge(Event Player, Event Player.HasilNasibTerkunci);
		End;
		Clear Status(Event Player, Hacked);
		Clear Status(Event Player, Knocked Down);
		Stop Accelerating(Event Player);
		Stop Forcing Player Outlines(All Players(All Teams), Event Player);
		Enable Movement Collision With Environment(Event Player);
		Set Move Speed(Event Player, 100);
		Set Jump Vertical Speed(Event Player, 100);
		Set Projectile Speed(Event Player, 100);
		Set Gravity(Event Player, 100);
		Event Player.PrivasiNasibAktif = False;
		Event Player.EfekNasib = 0;
		Event Player.EfekNasibBerakhir = 0;
		Event Player.DaftarTujuanNasib = Empty Array;
		Event Player.TujuanNasib = Vector(0, 0, 0);
		Event Player.ArahNasib = Vector(0, 0, 0);
		Event Player.KategoriTeleportNasib = -1;
		Event Player.HasilNasibTerkunci = 0;
		Event Player.IkonKartuNasib = Null;
		Event Player.IkonKartuNasibHijau = Null;
		Event Player.KartuNasibAktif = False;
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
		If(And(Event Player.MenuTerbuka == True, Event Player.HalamanMenu == 10));
			Call Subroutine(GambarMenu);
		End;
	}
}'''
source = replace_rule(source, "18f - Nasib: Hapus kartu saat pemilik mati", death_rule)

# ---------------------------------------------------------------------------
# Global-first timer manager: only the 16 ms global manager maintains timed
# effects. No new per-player polling rule is added.
# ---------------------------------------------------------------------------
def edit_fast(block: str) -> str:
    marker = "\t\tGlobal.PemainAktif = Null;\n\t\tWait(0.016, Ignore Condition);"
    extra = r'''		If(And(Global.PemainAktif.Manusia == True, Entity Exists(Global.PemainAktif)));
			If(And(Global.PemainAktif.KartuNasibAktif == True, Global.PemainAktif.PutaranKartuNasib == 0));
				If(And(Global.PemainAktif.EfekNasib == 2, And(Global.PemainAktif.EfekNasibBerakhir > Total Time Elapsed, Is Alive(Global.PemainAktif) == True)));
					Set Ultimate Charge(Global.PemainAktif, 100);
				End;
				If(And(Global.PemainAktif.EfekNasibBerakhir > 0, Total Time Elapsed >= Global.PemainAktif.EfekNasibBerakhir));
					If(Global.PemainAktif.EfekNasib == 1);
						Clear Status(Global.PemainAktif, Hacked);
					Else If(Global.PemainAktif.EfekNasib == 2);
						Set Ultimate Charge(Global.PemainAktif, Global.PemainAktif.HasilNasibTerkunci);
					Else If(Global.PemainAktif.EfekNasib == 4);
						Set Move Speed(Global.PemainAktif, 100);
						Set Jump Vertical Speed(Global.PemainAktif, 100);
						Set Projectile Speed(Global.PemainAktif, 100);
					Else If(Global.PemainAktif.EfekNasib == 5);
						Set Gravity(Global.PemainAktif, 100);
						Set Projectile Speed(Global.PemainAktif, 100);
					Else If(Global.PemainAktif.EfekNasib == 6);
						Stop Forcing Player Outlines(All Players(All Teams), Global.PemainAktif);
						Set Player Variable(Global.PemainAktif, PrivasiNasibAktif, False);
					Else If(Global.PemainAktif.EfekNasib == 8);
						Stop Accelerating(Global.PemainAktif);
						Set Move Speed(Global.PemainAktif, 100);
					End;
					Set Player Variable(Global.PemainAktif, EfekNasib, 0);
					Set Player Variable(Global.PemainAktif, EfekNasibBerakhir, 0);
					Set Player Variable(Global.PemainAktif, HasilNasibTerkunci, 0);
					Set Player Variable(Global.PemainAktif, KartuNasibAktif, False);
				End;
			End;
		End;
'''
    if block.count(marker) != 1:
        raise RuntimeError("04g end marker mismatch")
    return block.replace(marker, extra + marker, 1)

source = edit_rule(source, "04g - Global-first: Pengatur status cepat terpusat", edit_fast)

# ---------------------------------------------------------------------------
# Reveal bypass: outcome 6 ignores the custom Inspection privacy for 15 s.
# Teleport privacy remains unchanged.
# ---------------------------------------------------------------------------
def add_privacy_override(block: str) -> str:
    old = "Player Variable(Current Array Element, PrivasiInspeksiAktif) == False"
    if block.count(old) != 1:
        raise RuntimeError("inspection privacy token mismatch")
    return block.replace(old, "Or(Event Player.PrivasiNasibAktif == True, Player Variable(Current Array Element, PrivasiInspeksiAktif) == False)", 1)

source = edit_rule(source, "13 - Intip Pahlawan: Nama mengikuti target reticolo senza Wait", add_privacy_override)
source = edit_rule(source, "96 - Subrutin: Cari target publik terdekat dari bidikan", add_privacy_override)

# ---------------------------------------------------------------------------
# Leave/team-change cleanup and player initialization.
# ---------------------------------------------------------------------------
def edit_cleanup(block: str) -> str:
    old = "\t\tSet Move Speed(Event Player, 100);\n"
    new = old + (
        "\t\tSet Jump Vertical Speed(Event Player, 100);\n"
        "\t\tSet Projectile Speed(Event Player, 100);\n"
        "\t\tSet Gravity(Event Player, 100);\n"
        "\t\tStop Accelerating(Event Player);\n"
        "\t\tStop Forcing Player Outlines(All Players(All Teams), Event Player);\n"
        "\t\tEnable Movement Collision With Environment(Event Player);\n"
        "\t\tClear Status(Event Player, Hacked);\n"
        "\t\tClear Status(Event Player, Knocked Down);\n"
        "\t\tIf(Event Player.EfekNasib == 2);\n"
        "\t\t\tSet Ultimate Charge(Event Player, Event Player.HasilNasibTerkunci);\n"
        "\t\tEnd;\n"
    )
    if block.count(old) != 1:
        raise RuntimeError("cleanup move-speed marker mismatch")
    block = block.replace(old, new, 1)
    marker = "\t\tEvent Player.JedaKartuNasib = 0;\n"
    extra = marker + (
        "\t\tEvent Player.EfekNasib = 0;\n"
        "\t\tEvent Player.EfekNasibBerakhir = 0;\n"
        "\t\tEvent Player.DaftarTujuanNasib = Empty Array;\n"
        "\t\tEvent Player.TujuanNasib = Vector(0, 0, 0);\n"
        "\t\tEvent Player.ArahNasib = Vector(0, 0, 0);\n"
        "\t\tEvent Player.PrivasiNasibAktif = False;\n"
        "\t\tEvent Player.KategoriTeleportNasib = -1;\n"
        "\t\tEvent Player.HasilNasibTerkunci = 0;\n"
    )
    if block.count(marker) != 1:
        raise RuntimeError("cleanup luck-state marker mismatch")
    return block.replace(marker, extra, 1)

source = edit_rule(source, "93c - Subrutin: Bersihkan pemain saat keluar atau pindah tim", edit_cleanup)


def edit_init(block: str) -> str:
    marker = "\t\tEvent Player.JedaKartuNasib = 0;\n"
    extra = marker + (
        "\t\tEvent Player.EfekNasib = 0;\n"
        "\t\tEvent Player.EfekNasibBerakhir = 0;\n"
        "\t\tEvent Player.DaftarTujuanNasib = Empty Array;\n"
        "\t\tEvent Player.TujuanNasib = Vector(0, 0, 0);\n"
        "\t\tEvent Player.ArahNasib = Vector(0, 0, 0);\n"
        "\t\tEvent Player.PrivasiNasibAktif = False;\n"
        "\t\tEvent Player.KategoriTeleportNasib = -1;\n"
        "\t\tEvent Player.HasilNasibTerkunci = 0;\n"
    )
    if block.count(marker) != 1:
        raise RuntimeError("init luck-state marker mismatch")
    return block.replace(marker, extra, 1)

source = edit_rule(source, "94 - Subrutin: Siapkan pemain dari ujung rambut sampai variabel", edit_init)

# Replace RED/GREEN legacy status text with ROLLING/ACTIVE/READY.
status_replacements = (
    ('Event Player.KartuNasibAktif ? Event Player.PutaranKartuNasib > 0 ? Custom String("ROLLING") : Event Player.KartuNasibMerah ? Custom String("RED") : Custom String("GREEN") : Custom String("READY")',
     'Event Player.KartuNasibAktif ? Event Player.PutaranKartuNasib > 0 ? Custom String("ROLLING") : Custom String("ACTIVE") : Custom String("READY")'),
    ('Event Player.KartuNasibAktif ? Event Player.PutaranKartuNasib > 0 ? Custom String("BERPUTAR") : Event Player.KartuNasibMerah ? Custom String("MERAH") : Custom String("HIJAU") : Custom String("SIAP")',
     'Event Player.KartuNasibAktif ? Event Player.PutaranKartuNasib > 0 ? Custom String("BERPUTAR") : Custom String("AKTIF") : Custom String("SIAP")'),
    ('Event Player.KartuNasibAktif ? Event Player.PutaranKartuNasib > 0 ? Custom String("กำลังสุ่ม") : Event Player.KartuNasibMerah ? Custom String("แดง") : Custom String("เขียว") : Custom String("พร้อม")',
     'Event Player.KartuNasibAktif ? Event Player.PutaranKartuNasib > 0 ? Custom String("กำลังสุ่ม") : Custom String("ทำงาน") : Custom String("พร้อม")'),
)
for old, new in status_replacements:
    count = source.count(old)
    if count != 2:
        raise RuntimeError(f"legacy status replacement mismatch: {count}")
    source = source.replace(old, new)

SOURCE.write_text(source, encoding="utf-8")
new_blob = blob_sha(source)

# ---------------------------------------------------------------------------
# Validator: retire two-outcome assumptions and pin the ten-outcome contract.
# ---------------------------------------------------------------------------
validator = VALIDATOR.read_text(encoding="utf-8")
validator = one(validator, f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"', f'EXPECTED_SOURCE_BLOB = "{new_blob}"')
validator = one(
    validator,
    'for name in ("HalamanMenuTujuan", "HalamanSubmenuPramuat", "TargetTeleportasiTeks", "TeksTeleportasi", "InputMenuDikunci"):',
    'for name in ("HalamanMenuTujuan", "HalamanSubmenuPramuat", "TargetTeleportasiTeks", "TeksTeleportasi", "InputMenuDikunci", "EfekNasib", "EfekNasibBerakhir", "DaftarTujuanNasib", "TujuanNasib", "ArahNasib", "PrivasiNasibAktif", "KategoriTeleportNasib", "HasilNasibTerkunci"):'
)
validator = one(
    validator,
    '    checks.require("Set Move Speed(Event Player, 0);" in source, "Try Your Luck rosso non blocca la velocità")\n',
    ''
)
old_interact_checks = '''    if interact:\n        checks.require('Custom String("□")' not in interact.body and 'Custom String("[")' not in interact.body and 'Custom String("]")' not in interact.body, "Try Your Luck deve mostrare solo l icona senza frame testuale")\n        checks.require("Event Player.TeksKartuNasib = Last Text ID;" not in interact.body and "Event Player.TeksKartuNasibKanan = Last Text ID;" not in interact.body, "Try Your Luck crea ancora world text della carta")\n        checks.require("Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Skull" in interact.body, "Skull Try Your Luck non resta centrato sul reticolo")\n        checks.require("Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Heart" in interact.body, "Heart Try Your Luck non resta centrato sul reticolo")\n        checks.require("Facing Direction Of(Event Player) * 4 - Vector" not in interact.body, "Try Your Luck mantiene ancora un offset sotto il reticolo")\n'''
new_interact_checks = '''    if interact:\n        checks.require('Custom String("□")' not in interact.body and 'Custom String("[")' not in interact.body and 'Custom String("]")' not in interact.body, "Try Your Luck deve mostrare solo l icona senza frame testuale")\n        checks.require("Event Player.TeksKartuNasib = Last Text ID;" not in interact.body and "Event Player.TeksKartuNasibKanan = Last Text ID;" not in interact.body, "Try Your Luck crea ancora world text della carta")\n        checks.require("Event Player.EfekNasib = Random Integer(1, 10);" in interact.body, "Try Your Luck non inizializza dieci risultati")\n        checks.require("Create Icon(" not in interact.body, "Try Your Luck crea icone nel dispatcher menu invece che nella roulette")\n\n    luck = find_rule(rules, "18e - Nasib:")\n    luck_death = find_rule(rules, "18f - Nasib:")\n    checks.require(luck is not None and luck_death is not None, "pipeline Try Your Luck a dieci risultati assente")\n    if luck:\n        checks.equal(event_type(luck), "Ongoing - Each Player", "18e Try Your Luck: scheduler")\n        checks.require("Random Integer(1, 10)" in luck.body, "roulette Try Your Luck non usa dieci risultati")\n        for icon in ("Poison 2", "Halo", "Spiral", "Bolt", "Moon", "Eye", "Warning", "Dizzy", "Skull", "Heart"):\n            checks.require(f", {icon}, Visible To and Position" in luck.body, f"icona Try Your Luck assente: {icon}")\n        for token in (\n            "Set Status(Event Player, Null, Hacked, 5);",\n            "Set Ultimate Charge(Event Player, 100);",\n            "Spawn Points(Team Of(Event Player))",\n            "Objective Position(Objective Index)",\n            "Player Variable(Current Array Element, BotOtomatis) == True",\n            "Filtered Array(Global.PemainManusia",\n            "Set Move Speed(Event Player, 200);",\n            "Set Jump Vertical Speed(Event Player, 200);",\n            "Set Projectile Speed(Event Player, 200);",\n            "Set Gravity(Event Player, 10);",\n            "Set Projectile Speed(Event Player, 10);",\n            "Start Forcing Player Outlines(All Players(All Teams), Event Player, True, Color(White), Always);",\n            "Set Status(Event Player, Null, Knocked Down, 9999);",\n            "Disable Movement Collision With Environment(Event Player, True);",\n            "Start Accelerating(Event Player, Event Player.ArahNasib, 50, 25, To World, None);",\n            "Kill(Event Player, Null);",\n            "Set Player Health(All Living Players(Team Of(Event Player)), 9999);",\n        ):\n            checks.require(token in luck.body, f"Try Your Luck risultato incompleto: {token}")\n        checks.require("Start Forcing Player Position(" not in luck.body, "Try Your Luck non deve forzare la posizione")\n    if luck_death:\n        for token in (\n            "Clear Status(Event Player, Hacked);",\n            "Clear Status(Event Player, Knocked Down);",\n            "Stop Accelerating(Event Player);",\n            "Stop Forcing Player Outlines(All Players(All Teams), Event Player);",\n            "Enable Movement Collision With Environment(Event Player);",\n            "Set Move Speed(Event Player, 100);",\n            "Set Jump Vertical Speed(Event Player, 100);",\n            "Set Projectile Speed(Event Player, 100);",\n            "Set Gravity(Event Player, 100);",\n        ):\n            checks.require(token in luck_death.body, f"reset morte Try Your Luck incompleto: {token}")\n    if fast_manager:\n        checks.require("Set Ultimate Charge(Global.PemainAktif, 100);" in fast_manager.body, "Ultimate always-ready non è gestita dal manager globale")\n        checks.require("Global.PemainAktif.EfekNasibBerakhir" in fast_manager.body, "timer Try Your Luck non è Global-first")\n    if inspect_rule:\n        checks.require("Event Player.PrivasiNasibAktif == True" in inspect_rule.body, "reveal Try Your Luck non bypassa la privacy Inspection")\n    inspect_refresh = find_rule(rules, "96 - Subrutin:")\n    if inspect_refresh:\n        checks.require("Event Player.PrivasiNasibAktif == True" in inspect_refresh.body, "refresh Inspection non rispetta il reveal Try Your Luck")\n    checks.require('KartuNasibMerah ? Custom String("RED")' not in source and 'KartuNasibMerah ? Custom String("MERAH")' not in source, "HUD Try Your Luck usa ancora RED/GREEN")\n'''
validator = one(validator, old_interact_checks, new_interact_checks)
VALIDATOR.write_text(validator, encoding="utf-8")

print(f"Try Your Luck ten outcomes: {OLD_BLOB} -> {new_blob}")
