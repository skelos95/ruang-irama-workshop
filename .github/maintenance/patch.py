from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
OLD_BLOB = "b7130b2d9478e3cac2a4934c29dc21f10532d59f"


def blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"expected one match: {old[:120]!r}")
    return text.replace(old, new)


source = SOURCE.read_text(encoding="utf-8")
if blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob")

source = replace_once(
    source,
    "\t\t98: InputMenuDikunci\n",
    "\t\t98: InputMenuDikunci\n"
    "\t\t99: EfekNasib\n"
    "\t\t100: EfekNasibBerakhir\n"
    "\t\t101: DaftarTujuanNasib\n"
    "\t\t102: TujuanNasib\n"
    "\t\t103: ArahNasib\n"
    "\t\t104: PrivasiNasibAktif\n"
    "\t\t105: KategoriTeleportNasib\n"
    "\t\t106: HasilNasibTerkunci\n",
)
source = replace_once(source, "\t30: PramuatSubmenu\n", "\t30: PramuatSubmenu\n\t31: TampilkanIkonNasib\n")

icon_rule = r'''

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
'''
source = source.rstrip() + icon_rule + "\n"
SOURCE.write_text(source, encoding="utf-8")
new_blob = blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_once(validator, f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"', f'EXPECTED_SOURCE_BLOB = "{new_blob}"')
validator = replace_once(
    validator,
    'for name in ("HalamanMenuTujuan", "HalamanSubmenuPramuat", "TargetTeleportasiTeks", "TeksTeleportasi", "InputMenuDikunci"): ',
    'for name in ("HalamanMenuTujuan", "HalamanSubmenuPramuat", "TargetTeleportasiTeks", "TeksTeleportasi", "InputMenuDikunci", "EfekNasib", "EfekNasibBerakhir", "PrivasiNasibAktif"): ',
) if False else validator
validator = replace_once(
    validator,
    'for name in ("HalamanMenuTujuan", "HalamanSubmenuPramuat", "TargetTeleportasiTeks", "TeksTeleportasi", "InputMenuDikunci"):',
    'for name in ("HalamanMenuTujuan", "HalamanSubmenuPramuat", "TargetTeleportasiTeks", "TeksTeleportasi", "InputMenuDikunci", "EfekNasib", "EfekNasibBerakhir", "PrivasiNasibAktif"):')
validator = replace_once(
    validator,
    'for name in ("GambarMenu", "GambarHalamanAktif", "PramuatSubmenu"):',
    'for name in ("GambarMenu", "GambarHalamanAktif", "PramuatSubmenu", "TampilkanIkonNasib"):')
VALIDATOR.write_text(validator, encoding="utf-8")
print(f"Try Your Luck icon framework: {OLD_BLOB} -> {new_blob}")
