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
        raise RuntimeError(f"{label}: expected exactly one occurrence, found {count}")
    return text.replace(old, new, 1)


def replace_count(text: str, old: str, new: str, expected: int, label: str) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"{label}: expected {expected} occurrences, found {count}")
    return text.replace(old, new)


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    return hashlib.sha1(payload).hexdigest()


source = SOURCE.read_text(encoding="utf-8")

# A second persistent icon lets us keep Heart and Skull alive for the whole
# roulette and swap only visibility. This removes the destroy/create flicker.
source = replace_once(
    source,
    "\t\t76: IkonKartuNasib\n",
    "\t\t76: IkonKartuNasib\n\t\t77: IkonKartuNasibHijau\n",
    "green luck icon variable",
)

# Camera-aware reticle anchor. In first person it is the normal eye/facing ray.
# In custom camera modes it reuses the exact shoulder-camera origin and look-at
# line from MulaiKamera, then places the card 4 m along that screen-center ray.
camera_origin = '''First Of(Mapped Array(Array(Ray Cast Hit Position(Eye Position(Event Player.TargetKamera)
					+ Vector(0, Min(0.750, Max(0.450, 0.450 + (Max Health(Event Player.TargetKamera) - 200) * 0.0006)), 0), Eye Position(
					Event Player.TargetKamera) + Vector(0, Min(0.750, Max(0.450, 0.450 + (Max Health(Event Player.TargetKamera) - 200) * 0.0006)), 0)
					- Facing Direction Of(Event Player.TargetKamera) * Min(4.500, Max(Global.JarakKamera, Global.JarakKamera + (Max Health(
					Event Player.TargetKamera) - 200) * 0.0055)) + Cross Product(Direction From Angles(Horizontal Facing Angle Of(Event Player.TargetKamera), 0),
					Vector(0, 1, 0)) * Min(1.350, Max(Global.GeserKamera, Global.GeserKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0016)),
					Empty Array, Empty Array, False)), Current Array Element + Direction Towards(Current Array Element, Eye Position(Event Player.TargetKamera)
					+ Vector(0, Min(0.750, Max(0.450, 0.450 + (Max Health(Event Player.TargetKamera) - 200) * 0.0006)), 0)) * Min(Global.BantalanDinding,
					Distance Between(Current Array Element, Eye Position(Event Player.TargetKamera) + Vector(0, Min(0.750, Max(0.450, 0.450 + (Max Health(
					Event Player.TargetKamera) - 200) * 0.0006)), 0)) * 0.250))))'''
anchor = f'''Or(Event Player.ModeKamera == 0, Event Player.TargetKamera == Null) ? Eye Position(Event Player) + Facing Direction Of(Event Player) * 4
					: First Of(Mapped Array(Array({camera_origin}), Current Array Element + Direction Towards(Current Array Element, Eye Position(
					Event Player.TargetKamera) + Facing Direction Of(Event Player.TargetKamera) * Global.JarakBidik) * 4))'''

old_creation = '''\t\t\t\tEvent Player.PosisiKartuNasib = Eye Position(Event Player) + Facing Direction Of(Event Player) * 4;
\t\t\t\tCreate In-World Text(All Players(All Teams), Custom String("[     ]"), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), 2.200, Do Not Clip, Visible To Position String and Color, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Visible Never);
\t\t\t\tEvent Player.TeksKartuNasib = Last Text ID;
\t\t\t\tIf(Event Player.KartuNasibMerah == True);
\t\t\t\t\tCreate Icon(All Players(All Teams), Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 - Vector(0, 0.450, 0), Skull, Visible To and Position, Custom Color(255, 70, 70, 255), False);
\t\t\t\tElse;
\t\t\t\t\tCreate Icon(All Players(All Teams), Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 - Vector(0, 0.450, 0), Heart, Visible To and Position, Custom Color(70, 255, 110, 255), False);
\t\t\t\tEnd;
\t\t\t\tEvent Player.IkonKartuNasib = Last Created Entity;'''
new_creation = f'''\t\t\t\tEvent Player.PosisiKartuNasib = Eye Position(Event Player) + Facing Direction Of(Event Player) * 4;
\t\t\t\tCreate In-World Text(All Players(All Teams), Custom String("[            ]"), Update Every Frame({anchor}), 2.200, Do Not Clip, Visible To Position String and Color, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Visible Never);
\t\t\t\tEvent Player.TeksKartuNasib = Last Text ID;
\t\t\t\tCreate Icon(Event Player.KartuNasibMerah ? All Players(All Teams) : Empty Array, {anchor} - Vector(0, 0.450, 0), Skull, Visible To and Position, Custom Color(255, 70, 70, 255), False);
\t\t\t\tEvent Player.IkonKartuNasib = Last Created Entity;
\t\t\t\tCreate Icon(Event Player.KartuNasibMerah ? Empty Array : All Players(All Teams), {anchor} - Vector(0, 0.450, 0), Heart, Visible To and Position, Custom Color(70, 255, 110, 255), False);
\t\t\t\tEvent Player.IkonKartuNasibHijau = Last Created Entity;'''
source = replace_once(source, old_creation, new_creation, "persistent camera-aware card creation")

# No icon recreation during roulette: toggling KartuNasibMerah automatically
# reevaluates Visible To for the two persistent icons.
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
new_tick = '''\t\tEvent Player.KartuNasibMerah = Event Player.KartuNasibMerah == False;
\t\tModify Player Variable(Event Player, PutaranKartuNasib, Subtract, 1);'''
source = replace_once(source, old_tick, new_tick, "remove roulette icon recreation")

# Every cleanup that destroys the red icon must also destroy the persistent green icon.
cleanup_old = '''\t\tIf(Event Player.IkonKartuNasib != Null);
\t\t\tDestroy Icon(Event Player.IkonKartuNasib);
\t\tEnd;
\t\tEvent Player.TeksKartuNasib = Null;
\t\tEvent Player.IkonKartuNasib = Null;'''
cleanup_new = '''\t\tIf(Event Player.IkonKartuNasib != Null);
\t\t\tDestroy Icon(Event Player.IkonKartuNasib);
\t\tEnd;
\t\tIf(Event Player.IkonKartuNasibHijau != Null);
\t\t\tDestroy Icon(Event Player.IkonKartuNasibHijau);
\t\tEnd;
\t\tEvent Player.TeksKartuNasib = Null;
\t\tEvent Player.IkonKartuNasib = Null;
\t\tEvent Player.IkonKartuNasibHijau = Null;'''
source = replace_count(source, cleanup_old, cleanup_new, 2, "normal and death green icon cleanup")

leave_old = '''\t\t\t\tIf(Event Player.IkonKartuNasib != Null);
\t\t\t\t\tDestroy Icon(Event Player.IkonKartuNasib);
\t\t\t\tEnd;
\t\t\t\tEvent Player.TeksKartuNasib = Null;
\t\t\t\tEvent Player.IkonKartuNasib = Null;'''
leave_new = '''\t\t\t\tIf(Event Player.IkonKartuNasib != Null);
\t\t\t\t\tDestroy Icon(Event Player.IkonKartuNasib);
\t\t\t\tEnd;
\t\t\t\tIf(Event Player.IkonKartuNasibHijau != Null);
\t\t\t\t\tDestroy Icon(Event Player.IkonKartuNasibHijau);
\t\t\t\tEnd;
\t\t\t\tEvent Player.TeksKartuNasib = Null;
\t\t\t\tEvent Player.IkonKartuNasib = Null;
\t\t\t\tEvent Player.IkonKartuNasibHijau = Null;'''
source = replace_once(source, leave_old, leave_new, "leave green icon cleanup")

# Human setup initializes both persistent icon handles.
source = replace_once(
    source,
    "\t\tEvent Player.IkonKartuNasib = Null;\n\t\tEvent Player.UrutanHUD = First Of(Global.SlotHUDTersedia);",
    "\t\tEvent Player.IkonKartuNasib = Null;\n\t\tEvent Player.IkonKartuNasibHijau = Null;\n\t\tEvent Player.UrutanHUD = First Of(Global.SlotHUDTersedia);",
    "green icon initialization",
)

SOURCE.write_text(source, encoding="utf-8")

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_once(
    validator,
    '        (76, "IkonKartuNasib"),\n    ):',
    '        (76, "IkonKartuNasib"),\n        (77, "IkonKartuNasibHijau"),\n    ):',
    "validator green icon slot",
)
validator = replace_once(
    validator,
    '            "Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), 2.200, Do Not Clip" in card_texts[0],\n            "Nasib: le parentesi della carta devono restare agganciate al mirino a 4 m e usare dimensione 2,2",',
    '            "Custom String(\\\"[            ]\\\")" in card_texts[0]\n            and "Update Every Frame(Or(Event Player.ModeKamera == 0, Event Player.TargetKamera == Null) ? Eye Position(Event Player) + Facing Direction Of(Event Player) * 4" in card_texts[0]\n            and "Global.JarakBidik) * 4" in card_texts[0],\n            "Nasib: parentesi larghe o aggancio camera-aware al mirino assenti",',
    "validator stable wide brackets",
)
validator = replace_once(
    validator,
    '            "Custom String(\\\"[     ]\\\")" in card_texts[0]\n            and "Icon String(" not in card_texts[0]',
    '            "Custom String(\\\"[            ]\\\")" in card_texts[0]\n            and "Icon String(" not in card_texts[0]',
    "validator wider bracket string",
)

# Replace the old four-call/recreation contract with two persistent conditional icons.
start = validator.index('    luck_icons = [call for call in call_texts(source, "Create Icon") if ", Skull," in call or ", Heart," in call]')
end = validator.index('    checks.require(\n        "Event Player.PosisiKartuNasib', start)
old_block = validator[start:end]
new_block = '''    luck_icons = [call for call in call_texts(source, "Create Icon") if ", Skull," in call or ", Heart," in call]\n    checks.equal(len(luck_icons), 2, "Nasib: esattamente due icone persistenti, Skull e Heart")\n    if luck_icons:\n        checks.equal(len([call for call in luck_icons if ", Skull," in call]), 1, "Nasib: un solo Skull persistente")\n        checks.equal(len([call for call in luck_icons if ", Heart," in call]), 1, "Nasib: un solo Heart persistente")\n        for call in luck_icons:\n            checks.require(\n                "Visible To and Position" in call\n                and "Or(Event Player.ModeKamera == 0, Event Player.TargetKamera == Null)" in call\n                and "Global.JarakBidik) * 4" in call,\n                "Nasib: icona persistente non segue il centro reale della camera",\n            )\n        skull = next(call for call in luck_icons if ", Skull," in call)\n        heart = next(call for call in luck_icons if ", Heart," in call)\n        checks.require(\n            "Event Player.KartuNasibMerah ? All Players(All Teams) : Empty Array" in skull\n            and "Custom Color(255, 70, 70, 255)" in skull,\n            "Nasib: Skull persistente non usa visibilità/colore rosso dinamici",\n        )\n        checks.require(\n            "Event Player.KartuNasibMerah ? Empty Array : All Players(All Teams)" in heart\n            and "Custom Color(70, 255, 110, 255)" in heart,\n            "Nasib: Heart persistente non usa visibilità/colore verde dinamici",\n        )\n    if luck:\n        luck_code = mask_strings(luck[0].body)\n        checks.require("Create Icon(" not in luck_code, "Nasib: la roulette ricrea ancora le icone e può vibrare")\n        checks.require("Destroy Icon(" not in luck_code.split("Loop If Condition Is True;")[0], "Nasib: la roulette distrugge ancora icone durante i cambi colore")\n    checks.require(\n        "Destroy Icon(Event Player.IkonKartuNasib);" in clean\n        and "Destroy Icon(Event Player.IkonKartuNasibHijau);" in clean,\n        "Nasib: cleanup delle due icone persistenti assente",\n    )\n\n'''
validator = validator[:start] + new_block + validator[end:]
validator = replace_once(
    validator,
    '                "Destroy Icon(Event Player.IkonKartuNasib);",\n                "Event Player.IkonKartuNasib = Null;",',
    '                "Destroy Icon(Event Player.IkonKartuNasib);",\n                "Destroy Icon(Event Player.IkonKartuNasibHijau);",\n                "Event Player.IkonKartuNasib = Null;",\n                "Event Player.IkonKartuNasibHijau = Null;",',
    "validator death persistent icons cleanup",
)
VALIDATOR.write_text(validator, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
old_doc = "La carta usa parentesi separate (`[     ]`, dimensione 2,2) e un vero `Create Icon` nativo: `Heart` verde oppure `Skull` rosso. Poiché `Create Icon` viene renderizzato visivamente più in alto rispetto all'In-World Text alla stessa coordinata, l'ancora dell'icona è compensata di `Vector(0, -0.450, 0)` rispetto al punto del mirino, così il simbolo cade dentro le parentesi. L'icona viene distrutta e ricreata a ogni cambio della roulette per garantire simbolo e colore corretti."
new_doc = "La carta usa parentesi più larghe (`[            ]`, dimensione 2,2) e due `Create Icon` nativi persistenti: `Heart` verde e `Skull` rosso. Le due icone vengono create una sola volta; `KartuNasibMerah` rivaluta soltanto `Visible To`, eliminando il flicker causato dal precedente ciclo Destroy/Create. In prima persona l'ancora segue `Eye Position + Facing Direction`; nelle modalità camera custom riusa esattamente origine e linea di mira di `MulaiKamera`, così la carta resta sul centro reale dello schermo anche con la camera sulla spalla. L'offset verticale dell'icona resta -0,45 m per centrarla nelle parentesi."
project = replace_once(project, old_doc, new_doc, "project stable camera card")
PROJECT.write_text(project, encoding="utf-8")

validation = VALIDATION.read_text(encoding="utf-8")
validation = re.sub(
    r"parentesi colorate \+ icona nativa `Heart` verde / `Skull` rossa agganciata al mirino(?: con compensazione verticale -0,45 m)?",
    "parentesi larghe + Heart/Skull persistenti agganciati alla linea reale della camera, senza ricreazione durante la roulette",
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
    raise RuntimeError("validation blob: expected one documented Workshop SHA")
VALIDATION.write_text(validation, encoding="utf-8")
