from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"

OLD_BLOB = "4848ec9a689ee9ab2d9e6f7ee9c1dc61e4131c3c"


def blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def replace_exact(text: str, old: str, new: str, expected: int = 1) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"replacement mismatch: expected {expected}, found {count}: {old[:220]!r}")
    return text.replace(old, new)


def rule_bounds(text: str, title: str) -> tuple[int, int]:
    needle = f'rule("{title}")'
    start = text.index(needle)
    nxt = text.find('\nrule("', start + len(needle))
    return start, len(text) if nxt < 0 else nxt


def replace_rule(text: str, title: str, new_block: str) -> str:
    start, end = rule_bounds(text, title)
    return text[:start] + new_block.rstrip() + "\n" + text[end:]


def edit_rule(text: str, title: str, editor) -> str:
    start, end = rule_bounds(text, title)
    block = text[start:end]
    changed = editor(block)
    if changed == block:
        raise RuntimeError(f"rule unchanged: {title}")
    return text[:start] + changed + text[end:]


source = SOURCE.read_text(encoding="utf-8")
if blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch moving target")

# ---------------------------------------------------------------------------
# Declarations
# ---------------------------------------------------------------------------
source = replace_exact(
    source,
    "\t\t97: TeksTeleportasi\n",
    "\t\t97: TeksTeleportasi\n"
    "\t\t98: EfekNasib\n"
    "\t\t99: EfekNasibBerakhir\n"
    "\t\t100: DaftarTujuanNasib\n"
    "\t\t101: TujuanNasib\n"
    "\t\t102: ArahNasib\n"
    "\t\t103: InputMenuDikunci\n"
    "\t\t104: PrivasiNasibAktif\n"
    "\t\t105: KategoriTeleportNasib\n"
    "\t\t106: HasilNasibTerkunci\n",
)
source = replace_exact(
    source,
    "\t30: PramuatSubmenu\n",
    "\t30: PramuatSubmenu\n\t31: TampilkanIkonNasib\n\t32: PulihkanEfekNasib\n",
)

# ---------------------------------------------------------------------------
# Menu: hero inputs stay live unless Crouch is held.
# ---------------------------------------------------------------------------
def edit_menu_toggle(block: str) -> str:
    for line in (
        "\t\t\tDisallow Button(Event Player, Button(Primary Fire));\n",
        "\t\t\tDisallow Button(Event Player, Button(Secondary Fire));\n",
        "\t\t\tDisallow Button(Event Player, Button(Interact));\n",
        "\t\t\tDisallow Button(Event Player, Button(Reload));\n",
        "\t\t\tDisallow Button(Event Player, Button(Ability 1));\n",
        "\t\t\tDisallow Button(Event Player, Button(Ability 2));\n",
        "\t\t\tDisallow Button(Event Player, Button(Ultimate));\n",
    ):
        block = replace_exact(block, line, "")
    return block

source = edit_rule(source, "05 - Menu: Tahan serangan jarak dekat 0,5 detik untuk buka atau tutup", edit_menu_toggle)


def edit_dispatcher(block: str) -> str:
    marker = "\t\tEvent Player.MenuTerbuka == True;\n\t\tEvent Player.PerintahMenu == 0;"
    return replace_exact(
        block,
        marker,
        "\t\tEvent Player.MenuTerbuka == True;\n\t\tIs Button Held(Event Player, Button(Crouch)) == True;\n\t\tEvent Player.PerintahMenu == 0;",
    )

source = edit_rule(source, "05c - Menu: Pengatur masukan dengan prioritas tetap", edit_dispatcher)

menu_lock_rules = r'''
rule("05e - Menu: Crouch mengunci input hero hanya saat navigasi")
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
		Event Player.MenuTerbuka == True;
		Event Player.InputMenuDikunci == False;
		Is Button Held(Event Player, Button(Crouch)) == True;
	}

	actions
	{
		Event Player.InputMenuDikunci = True;
		Disallow Button(Event Player, Button(Primary Fire));
		Disallow Button(Event Player, Button(Secondary Fire));
		Disallow Button(Event Player, Button(Interact));
		Disallow Button(Event Player, Button(Reload));
		Disallow Button(Event Player, Button(Ability 1));
		Disallow Button(Event Player, Button(Ability 2));
		Disallow Button(Event Player, Button(Ultimate));
	}
}

rule("05f - Menu: Lepaskan Crouch mengembalikan subito input hero")
{
	event
	{
		Ongoing - Each Player;
		All;
		All;
	}

	conditions
	{
		Event Player.InputMenuDikunci == True;
		Or(Event Player.MenuTerbuka == False, Is Button Held(Event Player, Button(Crouch)) == False) == True;
	}

	actions
	{
		Allow Button(Event Player, Button(Primary Fire));
		Allow Button(Event Player, Button(Secondary Fire));
		Allow Button(Event Player, Button(Interact));
		Allow Button(Event Player, Button(Reload));
		Allow Button(Event Player, Button(Ability 1));
		Allow Button(Event Player, Button(Ability 2));
		Allow Button(Event Player, Button(Ultimate));
		Event Player.InputMenuDikunci = False;
		Event Player.PerintahMenu = 0;
	}
}

'''
insert_at = source.index('rule("06 - Menu:')
source = source[:insert_at] + menu_lock_rules + source[insert_at:]

# ---------------------------------------------------------------------------
# Try Your Luck start: ten outcomes, one icon at reticle.
# ---------------------------------------------------------------------------
old_luck_branch = '''\t\tElse If(Event Player.HalamanMenu == 10);\n\t\t\tIf(Event Player.KartuNasibAktif == True);\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("The luck card is already rolling. Wait for the result.") : Event Player.IndeksBahasa == 1 ? Custom String("Kartu nasib sedang berputar. Tunggu hasilnya.") : Custom String("การ์ดเสี่ยงโชคกำลังสุ่มอยู่ รอผลก่อน"));\n\t\t\tElse;\n\t\t\t\tEvent Player.KartuNasibAktif = True;\n\t\t\t\tEvent Player.KartuNasibMerah = Random Integer(0, 1) == 0;\n\t\t\t\tEvent Player.PutaranKartuNasib = Random Integer(20, 24);\n\t\t\t\tEvent Player.JedaKartuNasib = 0.080;\n\t\t\t\tEvent Player.GerakNasibDikunci = False;\n\t\t\t\tEvent Player.PosisiNasibTerkunci = Position Of(Event Player);\n\t\t\t\tEvent Player.WarnaNasibTerkunci = Global.RGB;\n\t\t\t\tEvent Player.RadiusNasib = 0;\n\t\t\t\tEvent Player.EfekNasibCahaya = Null;\n\t\t\t\tEvent Player.EfekNasibLingkaran = Null;\n\t\t\t\t"Perlindungan undian hanya sementara; pilihan pemain tetap disimpan di ModeKebalTerakhir."\n\t\t\t\tEvent Player.ModeKebal = 2;\n\t\t\t\tEvent Player.KebalAktif = True;\n\t\t\t\tClear Status(Event Player, Unkillable);\n\t\t\t\tSet Status(Event Player, Null, Unkillable, 9999);\n\t\t\t\tSet Damage Received(Event Player, 0);\n\t\t\t\tIf(Is Alive(Event Player) == True);\n\t\t\t\t\tSet Player Health(Event Player, Max Health(Event Player));\n\t\t\t\tEnd;\n\t\t\t\tIf(Event Player.IkonKebal != Null);\n\t\t\t\t\tDestroy Icon(Event Player.IkonKebal);\n\t\t\t\tEnd;\n\t\t\t\tCreate Icon(All Players(All Teams), Event Player, Halo, Visible To and Position, Global.RGB, True);\n\t\t\t\tEvent Player.IkonKebal = Last Created Entity;\n\t\t\t\t"Try Your Luck memakai hanya ikon Skull/Heart tepat di reticolo; tidak ada frame atau world text."\n\t\t\t\tEvent Player.TeksKartuNasib = Null;\n\t\t\t\tEvent Player.TeksKartuNasibKanan = Null;\n\t\t\t\tCreate Icon(Event Player.KartuNasibMerah ? All Players(All Teams) : Empty Array, Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Skull, Visible To and Position, Custom Color(255, 70, 70, 255), False);\n\t\t\t\tEvent Player.IkonKartuNasib = Last Created Entity;\n\t\t\t\tCreate Icon(Event Player.KartuNasibMerah ? Empty Array : All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Heart, Visible To and Position, Custom Color(70, 255, 110, 255), False);\n\t\t\t\tEvent Player.IkonKartuNasibHijau = Last Created Entity;\n\t\t\t\tCall Subroutine(GambarMenu);\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Luck roulette started. Red or green?") : Event Player.IndeksBahasa == 1 ? Custom String("Roulette nasib dimulai. Merah atau hijau?") : Custom String("เริ่มรูเล็ตเสี่ยงโชคแล้ว แดงหรือเขียว?"));\n\t\t\tEnd;'''
new_luck_branch = '''\t\tElse If(Event Player.HalamanMenu == 10);\n\t\t\tIf(Event Player.KartuNasibAktif == True);\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Try Your Luck is already rolling. Wait for the result.") : Event Player.IndeksBahasa == 1 ? Custom String("Try Your Luck sedang berputar. Tunggu hasilnya.") : Custom String("Try Your Luck กำลังสุ่มอยู่ รอผลก่อน"));\n\t\t\tElse;\n\t\t\t\tIf(Or(Event Player.EfekNasib != 0, Event Player.PrivasiNasibAktif == True));\n\t\t\t\t\tCall Subroutine(PulihkanEfekNasib);\n\t\t\t\tEnd;\n\t\t\t\tEvent Player.KartuNasibAktif = True;\n\t\t\t\tEvent Player.EfekNasib = Random Integer(1, 10);\n\t\t\t\tEvent Player.PutaranKartuNasib = Random Integer(20, 24);\n\t\t\t\tEvent Player.JedaKartuNasib = 0.080;\n\t\t\t\tEvent Player.KartuNasibMerah = False;\n\t\t\t\tEvent Player.EfekNasibBerakhir = 0;\n\t\t\t\tEvent Player.HasilNasibTerkunci = 0;\n\t\t\t\t"Proteksi hanya selama roulette; ModeKebalTerakhir tetap menyimpan pilihan Unkillable pemain."\n\t\t\t\tEvent Player.ModeKebal = 2;\n\t\t\t\tEvent Player.KebalAktif = True;\n\t\t\t\tClear Status(Event Player, Unkillable);\n\t\t\t\tSet Status(Event Player, Null, Unkillable, 9999);\n\t\t\t\tSet Damage Received(Event Player, 0);\n\t\t\t\tSet Player Health(Event Player, Max Health(Event Player));\n\t\t\t\tIf(Event Player.IkonKebal != Null);\n\t\t\t\t\tDestroy Icon(Event Player.IkonKebal);\n\t\t\t\tEnd;\n\t\t\t\tCreate Icon(All Players(All Teams), Event Player, Halo, Visible To and Position, Global.RGB, True);\n\t\t\t\tEvent Player.IkonKebal = Last Created Entity;\n\t\t\t\tEvent Player.TeksKartuNasib = Null;\n\t\t\t\tEvent Player.TeksKartuNasibKanan = Null;\n\t\t\t\tEvent Player.IkonKartuNasibHijau = Null;\n\t\t\t\tCall Subroutine(TampilkanIkonNasib);\n\t\t\t\tCall Subroutine(GambarMenu);\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Try Your Luck: ten outcomes are rolling.") : Event Player.IndeksBahasa == 1 ? Custom String("Try Your Luck: sepuluh hasil sedang diacak.") : Custom String("Try Your Luck: กำลังสุ่มสิบผลลัพธ์"));\n\t\t\tEnd;'''
source = replace_exact(source, old_luck_branch, new_luck_branch)

# ---------------------------------------------------------------------------
# Fast manager: Ultimate loop + timeout restoration for all temporary outcomes.
# ---------------------------------------------------------------------------
def edit_fast_manager(block: str) -> str:
    marker = "\t\tGlobal.PemainAktif = Null;\n\t\tWait(0.016, Ignore Condition);"
    extra = '''\t\tIf(And(Global.PemainAktif.Manusia == True, Entity Exists(Global.PemainAktif)));\n\t\t\tIf(And(Global.PemainAktif.EfekNasib == 2, And(Global.PemainAktif.EfekNasibBerakhir > Total Time Elapsed, Is Alive(Global.PemainAktif) == True)));\n\t\t\t\tSet Ultimate Charge(Global.PemainAktif, 100);\n\t\t\tEnd;\n\t\t\tIf(And(Global.PemainAktif.EfekNasibBerakhir > 0, Total Time Elapsed >= Global.PemainAktif.EfekNasibBerakhir));\n\t\t\t\tIf(Global.PemainAktif.EfekNasib == 1);\n\t\t\t\t\tClear Status(Global.PemainAktif, Hacked);\n\t\t\t\tElse If(Global.PemainAktif.EfekNasib == 4);\n\t\t\t\t\tSet Move Speed(Global.PemainAktif, 100);\n\t\t\t\t\tSet Jump Vertical Speed(Global.PemainAktif, 100);\n\t\t\t\t\tSet Projectile Speed(Global.PemainAktif, 100);\n\t\t\t\tElse If(Global.PemainAktif.EfekNasib == 5);\n\t\t\t\t\tSet Gravity(Global.PemainAktif, 100);\n\t\t\t\t\tSet Projectile Speed(Global.PemainAktif, 100);\n\t\t\t\tElse If(Global.PemainAktif.EfekNasib == 6);\n\t\t\t\t\tSet Player Variable(Global.PemainAktif, PrivasiNasibAktif, False);\n\t\t\t\t\tIf(Global.PemainAktif.InspeksiAktif == True);\n\t\t\t\t\t\tDisable Nameplates(All Players(All Teams), Global.PemainAktif);\n\t\t\t\t\t\tSet Player Variable(Global.PemainAktif, PelatNamaDinonaktifkan, True);\n\t\t\t\t\tElse;\n\t\t\t\t\t\tEnable Nameplates(All Players(All Teams), Global.PemainAktif);\n\t\t\t\t\t\tSet Player Variable(Global.PemainAktif, PelatNamaDinonaktifkan, False);\n\t\t\t\t\tEnd;\n\t\t\t\tElse If(Global.PemainAktif.EfekNasib == 8);\n\t\t\t\t\tStop Accelerating(Global.PemainAktif);\n\t\t\t\t\tSet Move Speed(Global.PemainAktif, 100);\n\t\t\t\tEnd;\n\t\t\t\tSet Player Variable(Global.PemainAktif, EfekNasib, 0);\n\t\t\t\tSet Player Variable(Global.PemainAktif, EfekNasibBerakhir, 0);\n\t\t\tEnd;\n\t\tEnd;\n'''
    return replace_exact(block, marker, extra + marker)

source = edit_rule(source, "04g - Global-first: Pengatur status cepat terpusat", edit_fast_manager)

# ---------------------------------------------------------------------------
# Privacy-bypass outcome: keep all nameplates and allow Crouch inspection too.
# ---------------------------------------------------------------------------
def edit_inspection(block: str) -> str:
    block = replace_exact(
        block,
        "Or(Player Variable(Current Array Element, BotOtomatis) == True, Player Variable(Current Array Element, PrivasiInspeksiAktif) == False)",
        "Or(Player Variable(Current Array Element, BotOtomatis) == True, Or(Event Player.PrivasiNasibAktif == True, Player Variable(Current Array Element, PrivasiInspeksiAktif) == False))",
        1,
    )
    block = replace_exact(
        block,
        "\t\t\tDisable Nameplates(All Players(All Teams), Event Player);\n\t\t\tEvent Player.PelatNamaDinonaktifkan = True;",
        "\t\t\tIf(Event Player.PrivasiNasibAktif == False);\n\t\t\t\tDisable Nameplates(All Players(All Teams), Event Player);\n\t\t\t\tEvent Player.PelatNamaDinonaktifkan = True;\n\t\t\tElse;\n\t\t\t\tEnable Nameplates(All Players(All Teams), Event Player);\n\t\t\t\tEvent Player.PelatNamaDinonaktifkan = False;\n\t\t\tEnd;",
        1,
    )
    return block

source = edit_rule(source, "13 - Intip Pahlawan: Nama mengikuti target reticolo senza Wait", edit_inspection)


def edit_inspection_refresh(block: str) -> str:
    return replace_exact(
        block,
        "Or(Player Variable(Current Array Element, BotOtomatis) == True, Player Variable(Current Array Element, PrivasiInspeksiAktif) == False)",
        "Or(Player Variable(Current Array Element, BotOtomatis) == True, Or(Event Player.PrivasiNasibAktif == True, Player Variable(Current Array Element, PrivasiInspeksiAktif) == False))",
        1,
    )

source = edit_rule(source, "96 - Subrutin: Cari target publik terdekat dari bidikan", edit_inspection_refresh)

# ---------------------------------------------------------------------------
# Ten-outcome roulette and death reset.
# ---------------------------------------------------------------------------
source = replace_rule(source, "18e - Nasib: Undian merah hijau makin lambat", r'''rule("18e - Nasib: Roulette sepuluh hasil makin lambat")
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
		Event Player.EfekNasib = Random Integer(1, 10);
		Call Subroutine(TampilkanIkonNasib);
		Modify Player Variable(Event Player, PutaranKartuNasib, Subtract, 1);
		Modify Player Variable(Event Player, JedaKartuNasib, Add, 0.055);
		Loop If Condition Is True;

		"Kunci hasil akhir lalu kembalikan proteksi roulette ke pengaturan normal sebelum menerapkan hadiah/hukuman."
		Event Player.HasilNasibTerkunci = Event Player.EfekNasib;
		Call Subroutine(PulihkanEfekNasib);
		Event Player.EfekNasib = Event Player.HasilNasibTerkunci;
		Event Player.HasilNasibTerkunci = 0;

		If(Event Player.EfekNasib == 1);
			Set Status(Event Player, Null, Hacked, 5);
			Event Player.EfekNasibBerakhir = Total Time Elapsed + 5;
			Small Message(Event Player, Custom String("TRY YOUR LUCK: HACKED - 5 SEC"));
		Else If(Event Player.EfekNasib == 2);
			Set Ultimate Charge(Event Player, 100);
			Event Player.EfekNasibBerakhir = Total Time Elapsed + 10;
			Small Message(Event Player, Custom String("TRY YOUR LUCK: ULTIMATE ALWAYS READY - 10 SEC"));
		Else If(Event Player.EfekNasib == 3);
			Event Player.KategoriTeleportNasib = Random Integer(0, 3);
			Event Player.DaftarTujuanNasib = Empty Array;
			Event Player.TujuanNasib = Position Of(Event Player);
			If(Event Player.KategoriTeleportNasib == 0);
				Event Player.DaftarTujuanNasib = Filtered Array(All Players(All Teams), And(Current Array Element != Event Player,
					And(Entity Exists(Current Array Element), And(Is Alive(Current Array Element), Or(Is Dummy Bot(Current Array Element) == True,
					Player Variable(Current Array Element, BotOtomatis) == True)))));
				If(Count Of(Event Player.DaftarTujuanNasib) > 0);
					Event Player.TujuanNasib = Position Of(Random Value In Array(Event Player.DaftarTujuanNasib)) + Vector(2, 0, 0);
				Else If(Count Of(Spawn Points(Team Of(Event Player))) > 0);
					Event Player.TujuanNasib = Position Of(Random Value In Array(Spawn Points(Team Of(Event Player))));
				End;
			Else If(Event Player.KategoriTeleportNasib == 1);
				Event Player.DaftarTujuanNasib = Filtered Array(Global.PemainManusia, And(Current Array Element != Event Player,
					And(Entity Exists(Current Array Element), Is Alive(Current Array Element))));
				If(Count Of(Event Player.DaftarTujuanNasib) > 0);
					Event Player.TujuanNasib = Position Of(Random Value In Array(Event Player.DaftarTujuanNasib)) + Vector(2, 0, 0);
				Else If(Count Of(Spawn Points(Team Of(Event Player))) > 0);
					Event Player.TujuanNasib = Position Of(Random Value In Array(Spawn Points(Team Of(Event Player))));
				End;
			Else If(Event Player.KategoriTeleportNasib == 2);
				If(Or(Current Game Mode == Game Mode(Escort), Current Game Mode == Game Mode(Hybrid)));
					Event Player.TujuanNasib = Payload Position;
				Else If(Current Game Mode == Game Mode(Capture The Flag));
					Event Player.TujuanNasib = Flag Position(Opposite Team Of(Team Of(Event Player)));
				Else If(Current Game Mode == Game Mode(Push));
					If(Count Of(Filtered Array(All Players(All Teams), And(Is Alive(Current Array Element) == True, Is On Objective(Current Array Element) == True))) > 0);
						Event Player.TujuanNasib = Position Of(Random Value In Array(Filtered Array(All Players(All Teams), And(Is Alive(Current Array Element) == True, Is On Objective(Current Array Element) == True))));
					Else;
						Event Player.TujuanNasib = Objective Position(Objective Index);
					End;
				Else;
					Event Player.TujuanNasib = Objective Position(Objective Index);
				End;
				If(And(Distance Between(Event Player.TujuanNasib, Vector(0, 0, 0)) <= 0.100, Count Of(Spawn Points(Team Of(Event Player))) > 0));
					Event Player.TujuanNasib = Position Of(Random Value In Array(Spawn Points(Team Of(Event Player))));
				End;
			Else If(Count Of(Spawn Points(Team Of(Event Player))) > 0);
				Event Player.TujuanNasib = Position Of(Random Value In Array(Spawn Points(Team Of(Event Player))));
			End;
			Teleport(Event Player, Nearest Walkable Position(Event Player.TujuanNasib));
			Event Player.EfekNasib = 0;
			Small Message(Event Player, Custom String("TRY YOUR LUCK: RANDOM TELEPORT"));
		Else If(Event Player.EfekNasib == 4);
			Set Move Speed(Event Player, 200);
			Set Jump Vertical Speed(Event Player, 200);
			Set Projectile Speed(Event Player, 200);
			Event Player.EfekNasibBerakhir = Total Time Elapsed + 15;
			Small Message(Event Player, Custom String("TRY YOUR LUCK: X2 MOVE / JUMP / PROJECTILES - 15 SEC"));
		Else If(Event Player.EfekNasib == 5);
			Set Gravity(Event Player, 10);
			Set Projectile Speed(Event Player, 10);
			Event Player.EfekNasibBerakhir = Total Time Elapsed + 20;
			Small Message(Event Player, Custom String("TRY YOUR LUCK: GRAVITY 10 / PROJECTILES 10 - 20 SEC"));
		Else If(Event Player.EfekNasib == 6);
			Event Player.PrivasiNasibAktif = True;
			Enable Nameplates(All Players(All Teams), Event Player);
			Event Player.PelatNamaDinonaktifkan = False;
			Event Player.EfekNasibBerakhir = Total Time Elapsed + 15;
			Small Message(Event Player, Custom String("TRY YOUR LUCK: SEE EVERY PLAYER - 15 SEC"));
		Else If(Event Player.EfekNasib == 7);
			Event Player.KebalAktif = False;
			Event Player.ModeKebal = 0;
			Clear Status(Event Player, Unkillable);
			Set Damage Received(Event Player, 100);
			If(Event Player.IkonKebal != Null);
				Destroy Icon(Event Player.IkonKebal);
				Event Player.IkonKebal = Null;
			End;
			Set Status(Event Player, Null, Knocked Down, 9999);
			Disable Movement Collision With Environment(Event Player, True);
			Event Player.EfekNasibBerakhir = 0;
			Small Message(Event Player, Custom String("TRY YOUR LUCK: THE FLOOR IS GONE"));
			Abort;
		Else If(Event Player.EfekNasib == 8);
			Event Player.ArahNasib = Vector(Random Real(-1, 1), Random Real(-0.500, 0.800), Random Real(-1, 1));
			Set Move Speed(Event Player, 300);
			Start Accelerating(Event Player, Event Player.ArahNasib, 50, 30, To World, Direction Rate and Max Speed);
			Event Player.EfekNasibBerakhir = Total Time Elapsed + 5;
			Small Message(Event Player, Custom String("TRY YOUR LUCK: RANDOM ACCELERATION - 5 SEC"));
		Else If(Event Player.EfekNasib == 9);
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
		Else;
			Set Player Health(Event Player, Max Health(Event Player));
			Heal(All Players(Team Of(Event Player)), Event Player, 10000);
			Event Player.EfekNasib = 0;
			Small Message(Event Player, Custom String("TRY YOUR LUCK: HEART - FULL TEAM HEAL"));
		End;

		Wait(1, Ignore Condition);
		If(Event Player.IkonKartuNasib != Null);
			Destroy Icon(Event Player.IkonKartuNasib);
		End;
		Event Player.IkonKartuNasib = Null;
		Event Player.IkonKartuNasibHijau = Null;
		Event Player.KartuNasibAktif = False;
		Event Player.PutaranKartuNasib = 0;
		Event Player.JedaKartuNasib = 0;
		If(And(Event Player.MenuTerbuka == True, Event Player.HalamanMenu == 10));
			Call Subroutine(GambarMenu);
		End;
	}
}''')

source = replace_rule(source, "18f - Nasib: Hapus kartu saat pemilik mati", r'''rule("18f - Nasib: Kematian selalu memulihkan semua efek sementara")
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
	}

	actions
	{
		If(Event Player.IkonKartuNasib != Null);
			Destroy Icon(Event Player.IkonKartuNasib);
		End;
		If(Event Player.IkonKartuNasibHijau != Null);
			Destroy Icon(Event Player.IkonKartuNasibHijau);
		End;
		Event Player.IkonKartuNasib = Null;
		Event Player.IkonKartuNasibHijau = Null;
		Event Player.TeksKartuNasib = Null;
		Event Player.TeksKartuNasibKanan = Null;
		Event Player.KartuNasibAktif = False;
		Event Player.PutaranKartuNasib = 0;
		Event Player.JedaKartuNasib = 0;
		Call Subroutine(PulihkanEfekNasib);
		Allow Button(Event Player, Button(Primary Fire));
		Allow Button(Event Player, Button(Secondary Fire));
		Allow Button(Event Player, Button(Interact));
		Allow Button(Event Player, Button(Reload));
		Allow Button(Event Player, Button(Ability 1));
		Allow Button(Event Player, Button(Ability 2));
		Allow Button(Event Player, Button(Ultimate));
		Event Player.InputMenuDikunci = False;
		Event Player.PerintahMenu = 0;
		If(And(Event Player.MenuTerbuka == True, Event Player.HalamanMenu == 10));
			Call Subroutine(GambarMenu);
		End;
	}
}''')

# ---------------------------------------------------------------------------
# Initialization and lifecycle cleanup.
# ---------------------------------------------------------------------------
def edit_setup(block: str) -> str:
    marker = "\t\tEvent Player.TeksTeleportasi = Null;\n\t\tEvent Player.TargetBalasDendamTerkunci = Null;"
    added = '''\t\tEvent Player.TeksTeleportasi = Null;\n\t\tEvent Player.EfekNasib = 0;\n\t\tEvent Player.EfekNasibBerakhir = 0;\n\t\tEvent Player.DaftarTujuanNasib = Empty Array;\n\t\tEvent Player.TujuanNasib = Vector(0, 0, 0);\n\t\tEvent Player.ArahNasib = Vector(0, 0, 0);\n\t\tEvent Player.InputMenuDikunci = False;\n\t\tEvent Player.PrivasiNasibAktif = False;\n\t\tEvent Player.KategoriTeleportNasib = 0;\n\t\tEvent Player.HasilNasibTerkunci = 0;\n\t\tEvent Player.TargetBalasDendamTerkunci = Null;'''
    return replace_exact(block, marker, added)

source = edit_rule(source, "94 - Subrutin: Siapkan pemain dari ujung rambut sampai variabel", edit_setup)


def edit_quiet(block: str) -> str:
    marker = "\t\tEvent Player.KartuNasibAktif = False;\n\t\tEvent Player.PutaranKartuNasib = 0;"
    return replace_exact(
        block,
        marker,
        "\t\tEvent Player.KartuNasibAktif = False;\n\t\tEvent Player.EfekNasib = 0;\n\t\tEvent Player.EfekNasibBerakhir = 0;\n\t\tEvent Player.InputMenuDikunci = False;\n\t\tEvent Player.PrivasiNasibAktif = False;\n\t\tEvent Player.PutaranKartuNasib = 0;",
    )

source = edit_rule(source, "93b2 - Subrutin: Tenangkan trigger sebelum cleanup", edit_quiet)


def edit_cleanup(block: str) -> str:
    block = replace_exact(
        block,
        "\t\tSet Move Speed(Event Player, 100);\n\t\tStop Modifying Hero Voice Lines(Event Player);",
        "\t\tSet Move Speed(Event Player, 100);\n\t\tSet Jump Vertical Speed(Event Player, 100);\n\t\tSet Projectile Speed(Event Player, 100);\n\t\tSet Gravity(Event Player, 100);\n\t\tStop Accelerating(Event Player);\n\t\tEnable Movement Collision With Environment(Event Player);\n\t\tClear Status(Event Player, Hacked);\n\t\tClear Status(Event Player, Knocked Down);\n\t\tStop Modifying Hero Voice Lines(Event Player);",
    )
    marker = "\t\tEvent Player.KartuNasibAktif = False;\n\t\tEvent Player.KartuNasibMerah = False;"
    block = replace_exact(
        block,
        marker,
        "\t\tEvent Player.KartuNasibAktif = False;\n\t\tEvent Player.EfekNasib = 0;\n\t\tEvent Player.EfekNasibBerakhir = 0;\n\t\tEvent Player.DaftarTujuanNasib = Empty Array;\n\t\tEvent Player.TujuanNasib = Vector(0, 0, 0);\n\t\tEvent Player.ArahNasib = Vector(0, 0, 0);\n\t\tEvent Player.InputMenuDikunci = False;\n\t\tEvent Player.PrivasiNasibAktif = False;\n\t\tEvent Player.KategoriTeleportNasib = 0;\n\t\tEvent Player.HasilNasibTerkunci = 0;\n\t\tEvent Player.KartuNasibMerah = False;",
    )
    return block

source = edit_rule(source, "93c - Subrutin: Bersihkan pemain saat keluar atau pindah tim", edit_cleanup)

# ---------------------------------------------------------------------------
# Subroutines for icon rendering and full effect reset.
# ---------------------------------------------------------------------------
subroutines = r'''

rule("99 - Subrutin: Tampilkan satu ikon Try Your Luck di reticolo")
{
	event
	{
		Subroutine;
		TampilkanIkonNasib;
	}

	actions
	{
		If(Event Player.IkonKartuNasib != Null);
			Destroy Icon(Event Player.IkonKartuNasib);
		End;
		Event Player.IkonKartuNasib = Null;
		If(Event Player.EfekNasib == 1);
			Create Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Poison 2, Visible To and Position, Custom Color(205, 90, 255, 255), False);
		Else If(Event Player.EfekNasib == 2);
			Create Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Halo, Visible To and Position, Custom Color(255, 205, 70, 255), False);
		Else If(Event Player.EfekNasib == 3);
			Create Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Spiral, Visible To and Position, Custom Color(70, 230, 255, 255), False);
		Else If(Event Player.EfekNasib == 4);
			Create Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Bolt, Visible To and Position, Custom Color(255, 170, 40, 255), False);
		Else If(Event Player.EfekNasib == 5);
			Create Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Moon, Visible To and Position, Custom Color(130, 160, 255, 255), False);
		Else If(Event Player.EfekNasib == 6);
			Create Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Eye, Visible To and Position, Custom Color(80, 255, 225, 255), False);
		Else If(Event Player.EfekNasib == 7);
			Create Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Arrow: Down, Visible To and Position, Custom Color(255, 90, 60, 255), False);
		Else If(Event Player.EfekNasib == 8);
			Create Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Dizzy, Visible To and Position, Custom Color(255, 235, 90, 255), False);
		Else If(Event Player.EfekNasib == 9);
			Create Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Skull, Visible To and Position, Custom Color(255, 70, 70, 255), False);
		Else;
			Create Icon(All Players(All Teams), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Heart, Visible To and Position, Custom Color(70, 255, 110, 255), False);
		End;
		Event Player.IkonKartuNasib = Last Created Entity;
	}
}

rule("99a - Subrutin: Pulihkan semua efek sementara Try Your Luck")
{
	event
	{
		Subroutine;
		PulihkanEfekNasib;
	}

	actions
	{
		Clear Status(Event Player, Hacked);
		Clear Status(Event Player, Knocked Down);
		Enable Movement Collision With Environment(Event Player);
		Stop Accelerating(Event Player);
		Set Move Speed(Event Player, 100);
		Set Jump Vertical Speed(Event Player, 100);
		Set Projectile Speed(Event Player, 100);
		Set Gravity(Event Player, 100);
		Event Player.PrivasiNasibAktif = False;
		If(Event Player.InspeksiAktif == True);
			Disable Nameplates(All Players(All Teams), Event Player);
			Event Player.PelatNamaDinonaktifkan = True;
		Else;
			Enable Nameplates(All Players(All Teams), Event Player);
			Event Player.PelatNamaDinonaktifkan = False;
		End;

		"Ripristina la scelta Unkillable persistente dopo protezioni o risultati letali della roulette."
		Clear Status(Event Player, Unkillable);
		Event Player.ModeKebal = Event Player.ModeKebalTerakhir;
		Event Player.KursorKebal = Event Player.ModeKebalTerakhir;
		If(And(Event Player.ModeKebalTerakhir == 1, And(Is Alive(Event Player) == True, Is In Spawn Room(Event Player) == True)));
			Event Player.KebalAktif = False;
			Event Player.ModeKebal = 0;
			Set Damage Received(Event Player, 100);
		Else If(Event Player.ModeKebalTerakhir == 0);
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
		If(And(Event Player.KebalAktif == True, Is Alive(Event Player) == True));
			If(Event Player.ModeKebal == 1);
				Create Icon(All Players(All Teams), Event Player, Warning, Visible To and Position, Custom Color(255, 80, 80, 255), True);
			Else;
				Create Icon(All Players(All Teams), Event Player, Halo, Visible To and Position, Global.RGB, True);
			End;
			Event Player.IkonKebal = Last Created Entity;
		End;
		Event Player.EfekNasib = 0;
		Event Player.EfekNasibBerakhir = 0;
		Event Player.DaftarTujuanNasib = Empty Array;
		Event Player.TujuanNasib = Vector(0, 0, 0);
		Event Player.ArahNasib = Vector(0, 0, 0);
		Event Player.KategoriTeleportNasib = 0;
	}
}
'''
source = source.rstrip() + subroutines + "\n"

SOURCE.write_text(source, encoding="utf-8")
new_blob = blob_sha(source)

# ---------------------------------------------------------------------------
# Validator follows the new live architecture.
# ---------------------------------------------------------------------------
validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_exact(
    validator,
    f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"',
    f'EXPECTED_SOURCE_BLOB = "{new_blob}"',
)
validator = replace_exact(
    validator,
    'for name in ("HalamanMenuTujuan", "HalamanSubmenuPramuat", "TargetTeleportasiTeks", "TeksTeleportasi"):',
    'for name in ("HalamanMenuTujuan", "HalamanSubmenuPramuat", "TargetTeleportasiTeks", "TeksTeleportasi", "EfekNasib", "EfekNasibBerakhir", "InputMenuDikunci", "PrivasiNasibAktif"):')
validator = replace_exact(
    validator,
    'for name in ("GambarMenu", "GambarHalamanAktif", "PramuatSubmenu"):',
    'for name in ("GambarMenu", "GambarHalamanAktif", "PramuatSubmenu", "TampilkanIkonNasib", "PulihkanEfekNasib"):')
validator = replace_exact(
    validator,
    '"05b - Menu:", "05c - Menu:", "05d - Menu:", "06 - Menu:", "07 - Menu:", "08 - Menu 0:", "09 - Menu 0:",',
    '"05b - Menu:", "05c - Menu:", "05d - Menu:", "05e - Menu:", "05f - Menu:", "06 - Menu:", "07 - Menu:", "08 - Menu 0:", "09 - Menu 0:",')

old_checks = '''    checks.require("Set Move Speed(Event Player, 0);" in source, "Try Your Luck rosso non blocca la velocità")\n    checks.require('Custom String("□")' not in source, "Try Your Luck crea ancora il quadrato della carta")\n    checks.require("Start Forcing Player Position(" not in source, "Try Your Luck non deve forzare la posizione")\n    if interact:\n        checks.require('Custom String("□")' not in interact.body and 'Custom String("[")' not in interact.body and 'Custom String("]")' not in interact.body, "Try Your Luck deve mostrare solo l icona senza frame testuale")\n        checks.require("Event Player.TeksKartuNasib = Last Text ID;" not in interact.body and "Event Player.TeksKartuNasibKanan = Last Text ID;" not in interact.body, "Try Your Luck crea ancora world text della carta")\n        checks.require("Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Skull" in interact.body, "Skull Try Your Luck non resta centrato sul reticolo")\n        checks.require("Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), Heart" in interact.body, "Heart Try Your Luck non resta centrato sul reticolo")\n        checks.require("Facing Direction Of(Event Player) * 4 - Vector" not in interact.body, "Try Your Luck mantiene ancora un offset sotto il reticolo")\n'''
new_checks = '''    checks.require('Custom String("□")' not in source, "Try Your Luck crea ancora il quadrato della carta")\n    checks.require("Start Forcing Player Position(" not in source, "Try Your Luck non deve forzare la posizione")\n    luck_roll = find_rule(rules, "18e - Nasib:")\n    luck_death = find_rule(rules, "18f - Nasib:")\n    luck_icon = find_rule(rules, "99 - Subrutin:")\n    luck_restore = find_rule(rules, "99a - Subrutin:")\n    checks.require(luck_roll is not None and luck_death is not None and luck_icon is not None and luck_restore is not None, "Try Your Luck 10-outcome pipeline incompleta")\n    if luck_icon:\n        for icon in ("Poison 2", "Halo", "Spiral", "Bolt", "Moon", "Eye", "Arrow: Down", "Dizzy", "Skull", "Heart"):\n            checks.require(icon in luck_icon.body, f"Try Your Luck icona mancante: {icon}")\n        checks.equal(luck_icon.body.count("Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4)"), 10, "icone Try Your Luck centrate sul reticolo")\n    if luck_roll:\n        for token in (\n            "Set Status(Event Player, Null, Hacked, 5);",\n            "Set Ultimate Charge(Event Player, 100);",\n            "Random Integer(0, 3)",\n            "Set Move Speed(Event Player, 200);",\n            "Set Jump Vertical Speed(Event Player, 200);",\n            "Set Projectile Speed(Event Player, 200);",\n            "Set Gravity(Event Player, 10);",\n            "Set Projectile Speed(Event Player, 10);",\n            "Event Player.PrivasiNasibAktif = True;",\n            "Disable Movement Collision With Environment(Event Player, True);",\n            "Start Accelerating(Event Player, Event Player.ArahNasib, 50, 30, To World, Direction Rate and Max Speed);",\n            "Kill(Event Player, Null);",\n            "Heal(All Players(Team Of(Event Player)), Event Player, 10000);",\n        ):\n            checks.require(token in luck_roll.body, f"Try Your Luck outcome mancante: {token}")\n    if luck_restore:\n        for token in ("Clear Status(Event Player, Hacked);", "Clear Status(Event Player, Knocked Down);", "Enable Movement Collision With Environment(Event Player);", "Stop Accelerating(Event Player);", "Set Move Speed(Event Player, 100);", "Set Jump Vertical Speed(Event Player, 100);", "Set Projectile Speed(Event Player, 100);", "Set Gravity(Event Player, 100);"):\n            checks.require(token in luck_restore.body, f"reset Try Your Luck incompleto: {token}")\n    if luck_death:\n        checks.require("Call Subroutine(PulihkanEfekNasib);" in luck_death.body, "morte non ripristina gli effetti Try Your Luck")\n'''
validator = replace_exact(validator, old_checks, new_checks)

# Menu guards: no permanent lock on open, Crouch-only router, Jump/Crouch always free.
menu_guard_old = '''    if menu_toggle:\n        checks.require("Wait(0.500, Abort When False);" in menu_toggle.body, "hold Melee 0,5 s assente")\n        checks.require("Disallow Button(Event Player, Button(Crouch));" not in menu_toggle.body, "Menu Arcade non deve bloccare Crouch")\n'''
menu_guard_new = '''    if menu_toggle:\n        checks.require("Wait(0.500, Abort When False);" in menu_toggle.body, "hold Melee 0,5 s assente")\n        checks.require("Disallow Button(Event Player, Button(Crouch));" not in menu_toggle.body and "Disallow Button(Event Player, Button(Jump));" not in menu_toggle.body, "Menu Arcade non deve bloccare Crouch o Jump")\n        for button in ("Primary Fire", "Secondary Fire", "Interact", "Reload", "Ability 1", "Ability 2", "Ultimate"):\n            checks.require(f"Disallow Button(Event Player, Button({button}));" not in menu_toggle.body, f"Menu aperto blocca permanentemente {button}")\n    menu_dispatch = find_rule(rules, "05c - Menu:")\n    menu_lock = find_rule(rules, "05e - Menu:")\n    menu_unlock = find_rule(rules, "05f - Menu:")\n    if menu_dispatch:\n        checks.require("Is Button Held(Event Player, Button(Crouch)) == True;" in menu_dispatch.body, "dispatcher menu non richiede Crouch")\n    if menu_lock:\n        checks.require("Disallow Button(Event Player, Button(Crouch));" not in menu_lock.body and "Disallow Button(Event Player, Button(Jump));" not in menu_lock.body, "navigazione menu blocca Crouch o Jump")\n        for button in ("Primary Fire", "Secondary Fire", "Interact", "Reload", "Ability 1", "Ability 2", "Ultimate"):\n            checks.require(f"Disallow Button(Event Player, Button({button}));" in menu_lock.body, f"Crouch menu non cattura {button}")\n    if menu_unlock:\n        checks.require("Is Button Held(Event Player, Button(Crouch)) == False" in menu_unlock.body, "rilascio Crouch non restituisce gli input hero")\n        for button in ("Primary Fire", "Secondary Fire", "Interact", "Reload", "Ability 1", "Ability 2", "Ultimate"):\n            checks.require(f"Allow Button(Event Player, Button({button}));" in menu_unlock.body, f"rilascio Crouch non restituisce {button}")\n'''
validator = replace_exact(validator, menu_guard_old, menu_guard_new)

# Ensure the fast global manager keeps the ultimate topped up and expires timers.
manager_guard = '    checks.require("Global.PemainAktif.InteraksiKameraDipakai = False;" not in source, "release Camera non deve essere nel manager globale")\n'
validator = replace_exact(
    validator,
    manager_guard,
    manager_guard + '    checks.require("Set Ultimate Charge(Global.PemainAktif, 100);" in source and "EfekNasibBerakhir" in source, "manager globale Try Your Luck temporaneo assente")\n',
)

VALIDATOR.write_text(validator, encoding="utf-8")
print(f"expanded Try Your Luck + Crouch menu control: {OLD_BLOB} -> {new_blob}")
