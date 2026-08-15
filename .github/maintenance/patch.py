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


def rule_region(text: str, prefix: str) -> tuple[int, int, str]:
    start = text.index(f'rule("{prefix}')
    end = text.find('\nrule("', start + 1)
    if end < 0:
        end = len(text)
    return start, end, text[start:end]


def replace_in_rule(text: str, prefix: str, old: str, new: str, label: str) -> str:
    start, end, region = rule_region(text, prefix)
    region2 = replace_once(region, old, new, label)
    return text[:start] + region2 + text[end:]


def insert_after_actions_open(text: str, prefix: str, addition: str, label: str) -> str:
    start, end, region = rule_region(text, prefix)
    marker = "\tactions\n\t{\n"
    if region.count(marker) != 1:
        raise RuntimeError(f"{label}: actions marker count {region.count(marker)}")
    region = region.replace(marker, marker + addition, 1)
    return text[:start] + region + text[end:]


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    return hashlib.sha1(payload).hexdigest()


source = SOURCE.read_text(encoding="utf-8")

# Dedicated handles for persistent Heart, right bracket, and temporary camera restore.
source = replace_once(
    source,
    "\t\t76: IkonKartuNasib\n",
    "\t\t76: IkonKartuNasib\n\t\t77: IkonKartuNasibHijau\n\t\t78: TeksKartuNasibKanan\n\t\t79: ModeKameraSebelumNasib\n\t\t80: TargetKameraSebelumNasib\n",
    "luck stable variables",
)

# Save the custom camera and temporarily use first person. This gives every card
# element the same simple Eye/Facing anchor and removes shoulder-camera jitter.
source = replace_once(
    source,
    "\t\t\t\tEvent Player.KartuNasibAktif = True;\n\t\t\t\tEvent Player.KartuNasibMerah = Random Integer(0, 1) == 0;",
    "\t\t\t\tEvent Player.ModeKameraSebelumNasib = Event Player.ModeKamera;\n\t\t\t\tEvent Player.TargetKameraSebelumNasib = Event Player.TargetKamera;\n\t\t\t\tIf(Event Player.ModeKamera != 0);\n\t\t\t\t\tStop Camera(Event Player);\n\t\t\t\t\tEvent Player.ModeKamera = 0;\n\t\t\t\t\tEvent Player.TargetKamera = Null;\n\t\t\t\t\tWait(0.016, Ignore Condition);\n\t\t\t\tEnd;\n\t\t\t\tEvent Player.KartuNasibAktif = True;\n\t\t\t\tEvent Player.KartuNasibMerah = Random Integer(0, 1) == 0;",
    "luck first person lock",
)

old_card = '''\t\t\t\tEvent Player.PosisiKartuNasib = Eye Position(Event Player) + Facing Direction Of(Event Player) * 4;
\t\t\t\tCreate In-World Text(All Players(All Teams), Custom String("[     ]"), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), 2.200, Do Not Clip, Visible To Position String and Color, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Visible Never);
\t\t\t\tEvent Player.TeksKartuNasib = Last Text ID;
\t\t\t\tIf(Event Player.KartuNasibMerah == True);
\t\t\t\t\tCreate Icon(All Players(All Teams), Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 - Vector(0, 0.450, 0), Skull, Visible To and Position, Custom Color(255, 70, 70, 255), False);
\t\t\t\tElse;
\t\t\t\t\tCreate Icon(All Players(All Teams), Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 - Vector(0, 0.450, 0), Heart, Visible To and Position, Custom Color(70, 255, 110, 255), False);
\t\t\t\tEnd;
\t\t\t\tEvent Player.IkonKartuNasib = Last Created Entity;'''
new_card = '''\t\t\t\tEvent Player.PosisiKartuNasib = Eye Position(Event Player) + Facing Direction Of(Event Player) * 4;
\t\t\t\tCreate In-World Text(All Players(All Teams), Custom String("["), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 - Cross Product(Direction From Angles(Horizontal Facing Angle Of(Event Player), 0), Vector(0, 1, 0)) * 0.800), 2.200, Do Not Clip, Visible To Position String and Color, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Visible Never);
\t\t\t\tEvent Player.TeksKartuNasib = Last Text ID;
\t\t\t\tCreate In-World Text(All Players(All Teams), Custom String("]"), Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 + Cross Product(Direction From Angles(Horizontal Facing Angle Of(Event Player), 0), Vector(0, 1, 0)) * 0.800), 2.200, Do Not Clip, Visible To Position String and Color, Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255), Visible Never);
\t\t\t\tEvent Player.TeksKartuNasibKanan = Last Text ID;
\t\t\t\tCreate Icon(Event Player.KartuNasibMerah ? All Players(All Teams) : Empty Array, Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 - Vector(0, 0.450, 0), Skull, Visible To and Position, Custom Color(255, 70, 70, 255), False);
\t\t\t\tEvent Player.IkonKartuNasib = Last Created Entity;
\t\t\t\tCreate Icon(Event Player.KartuNasibMerah ? Empty Array : All Players(All Teams), Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 - Vector(0, 0.450, 0), Heart, Visible To and Position, Custom Color(70, 255, 110, 255), False);
\t\t\t\tEvent Player.IkonKartuNasibHijau = Last Created Entity;'''
source = replace_once(source, old_card, new_card, "split bracket persistent card")

# Heart and Skull are persistent. Changing KartuNasibMerah only reevaluates Visible To.
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
source = replace_in_rule(
    source,
    "18e - Nasib:",
    old_tick,
    "\t\tEvent Player.KartuNasibMerah = Event Player.KartuNasibMerah == False;\n\t\tModify Player Variable(Event Player, PutaranKartuNasib, Subtract, 1);",
    "persistent roulette icons",
)

# Normal resolution cleanup destroys all four visual handles and restores the prior camera.
old_normal_cleanup = '''\t\tIf(Event Player.TeksKartuNasib != Null);
\t\t\tDestroy In-World Text(Event Player.TeksKartuNasib);
\t\tEnd;
\t\tIf(Event Player.IkonKartuNasib != Null);
\t\t\tDestroy Icon(Event Player.IkonKartuNasib);
\t\tEnd;
\t\tEvent Player.TeksKartuNasib = Null;
\t\tEvent Player.IkonKartuNasib = Null;
\t\tEvent Player.KartuNasibAktif = False;
\t\tEvent Player.PutaranKartuNasib = 0;
\t\tEvent Player.JedaKartuNasib = 0;'''
new_normal_cleanup = '''\t\tIf(Event Player.TeksKartuNasib != Null);
\t\t\tDestroy In-World Text(Event Player.TeksKartuNasib);
\t\tEnd;
\t\tIf(Event Player.TeksKartuNasibKanan != Null);
\t\t\tDestroy In-World Text(Event Player.TeksKartuNasibKanan);
\t\tEnd;
\t\tIf(Event Player.IkonKartuNasib != Null);
\t\t\tDestroy Icon(Event Player.IkonKartuNasib);
\t\tEnd;
\t\tIf(Event Player.IkonKartuNasibHijau != Null);
\t\t\tDestroy Icon(Event Player.IkonKartuNasibHijau);
\t\tEnd;
\t\tEvent Player.TeksKartuNasib = Null;
\t\tEvent Player.TeksKartuNasibKanan = Null;
\t\tEvent Player.IkonKartuNasib = Null;
\t\tEvent Player.IkonKartuNasibHijau = Null;
\t\tEvent Player.KartuNasibAktif = False;
\t\tEvent Player.PutaranKartuNasib = 0;
\t\tEvent Player.JedaKartuNasib = 0;
\t\tIf(And(Is Alive(Event Player) == True, Event Player.ModeKameraSebelumNasib != 0));
\t\t\tIf(Event Player.ModeKameraSebelumNasib == 1);
\t\t\t\tEvent Player.TargetKamera = Event Player;
\t\t\t\tWait(0.016, Ignore Condition);
\t\t\t\tEvent Player.ModeKamera = 1;
\t\t\t\tCall Subroutine(MulaiKamera);
\t\t\tElse If(And(Event Player.TargetKameraSebelumNasib != Null, Entity Exists(Event Player.TargetKameraSebelumNasib)));
\t\t\t\tEvent Player.TargetKamera = Event Player.TargetKameraSebelumNasib;
\t\t\t\tWait(0.016, Ignore Condition);
\t\t\t\tEvent Player.ModeKamera = 2;
\t\t\t\tCall Subroutine(MulaiKamera);
\t\t\tEnd;
\t\tEnd;
\t\tEvent Player.ModeKameraSebelumNasib = 0;
\t\tEvent Player.TargetKameraSebelumNasib = Null;'''
source = replace_in_rule(source, "18e - Nasib:", old_normal_cleanup, new_normal_cleanup, "normal stable cleanup and camera restore")

# Death reset removes the new persistent visuals and forgets the camera snapshot.
old_death_cleanup = '''\t\tIf(Event Player.TeksKartuNasib != Null);
\t\t\tDestroy In-World Text(Event Player.TeksKartuNasib);
\t\tEnd;
\t\tIf(Event Player.IkonKartuNasib != Null);
\t\t\tDestroy Icon(Event Player.IkonKartuNasib);
\t\tEnd;
\t\tEvent Player.TeksKartuNasib = Null;
\t\tEvent Player.IkonKartuNasib = Null;'''
new_death_cleanup = '''\t\tIf(Event Player.TeksKartuNasib != Null);
\t\t\tDestroy In-World Text(Event Player.TeksKartuNasib);
\t\tEnd;
\t\tIf(Event Player.TeksKartuNasibKanan != Null);
\t\t\tDestroy In-World Text(Event Player.TeksKartuNasibKanan);
\t\tEnd;
\t\tIf(Event Player.IkonKartuNasib != Null);
\t\t\tDestroy Icon(Event Player.IkonKartuNasib);
\t\tEnd;
\t\tIf(Event Player.IkonKartuNasibHijau != Null);
\t\t\tDestroy Icon(Event Player.IkonKartuNasibHijau);
\t\tEnd;
\t\tEvent Player.TeksKartuNasib = Null;
\t\tEvent Player.TeksKartuNasibKanan = Null;
\t\tEvent Player.IkonKartuNasib = Null;
\t\tEvent Player.IkonKartuNasibHijau = Null;
\t\tEvent Player.ModeKameraSebelumNasib = 0;
\t\tEvent Player.TargetKameraSebelumNasib = Null;'''
source = replace_in_rule(source, "18f - Nasib:", old_death_cleanup, new_death_cleanup, "death stable cleanup")

# Leaving already cleans the old left/red handles; add only the new right/green handles.
source = insert_after_actions_open(
    source,
    "04 - Pemain Keluar:",
    '''\t\tIf(Event Player.TeksKartuNasibKanan != Null);\n\t\t\tDestroy In-World Text(Event Player.TeksKartuNasibKanan);\n\t\t\tEvent Player.TeksKartuNasibKanan = Null;\n\t\tEnd;\n\t\tIf(Event Player.IkonKartuNasibHijau != Null);\n\t\t\tDestroy Icon(Event Player.IkonKartuNasibHijau);\n\t\t\tEvent Player.IkonKartuNasibHijau = Null;\n\t\tEnd;\n''',
    "leave new luck visuals cleanup",
)

# Initialize new state in SiapkanPemain.
source = replace_once(
    source,
    "\t\tEvent Player.TeksKartuNasib = Null;\n\t\tEvent Player.KartuNasibMerah = False;\n\t\tEvent Player.PutaranKartuNasib = 0;\n\t\tEvent Player.JedaKartuNasib = 0;",
    "\t\tEvent Player.TeksKartuNasib = Null;\n\t\tEvent Player.TeksKartuNasibKanan = Null;\n\t\tEvent Player.IkonKartuNasib = Null;\n\t\tEvent Player.IkonKartuNasibHijau = Null;\n\t\tEvent Player.ModeKameraSebelumNasib = 0;\n\t\tEvent Player.TargetKameraSebelumNasib = Null;\n\t\tEvent Player.KartuNasibMerah = False;\n\t\tEvent Player.PutaranKartuNasib = 0;\n\t\tEvent Player.JedaKartuNasib = 0;",
    "initialize stable luck state",
)

SOURCE.write_text(source, encoding="utf-8")

# Validator: certify the architecture that live testing actually needs.
validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_once(
    validator,
    '        (76, "IkonKartuNasib"),\n    ):',
    '        (76, "IkonKartuNasib"),\n        (77, "IkonKartuNasibHijau"),\n        (78, "TeksKartuNasibKanan"),\n        (79, "ModeKameraSebelumNasib"),\n        (80, "TargetKameraSebelumNasib"),\n    ):',
    "validator stable luck slots",
)

old_cards = '''    card_texts = [
        call for call in call_texts(source, "Create In-World Text")
        if "KartuNasib" in call and "All Players(All Teams)" in call
    ]
    checks.equal(len(card_texts), 1, "Nasib: una sola carta pubblica")
    if card_texts:
        checks.require(
            "Update Every Frame(Eye Position(Event Player) + Facing Direction Of(Event Player) * 4), 2.200, Do Not Clip" in card_texts[0],
            "Nasib: le parentesi della carta devono restare agganciate al mirino a 4 m e usare dimensione 2,2",
        )
        checks.require(
            "Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255)" in card_texts[0],
            "Nasib: le parentesi non cambiano dinamicamente rosso/verde",
        )
        checks.require(
            "Custom String(\\\"[     ]\\\")" in card_texts[0]
            and "Icon String(" not in card_texts[0]
            and "☠" not in card_texts[0]
            and "♥" not in card_texts[0]
            and "TRY YOUR LUCK" not in card_texts[0]
            and "COBA NASIB" not in card_texts[0],
            "Nasib: le parentesi devono essere testo semplice; il simbolo è un Create Icon nativo",
        )
    luck_icons = [call for call in call_texts(source, "Create Icon") if ", Skull," in call or ", Heart," in call]
    checks.equal(len(luck_icons), 4, "Nasib: due Create Icon iniziali più due per i cambi roulette")
    if luck_icons:
        checks.equal(len([call for call in luck_icons if ", Skull," in call]), 2, "Nasib: due rami Skull nativi")
        checks.equal(len([call for call in luck_icons if ", Heart," in call]), 2, "Nasib: due rami Heart nativi")
        for call in luck_icons:
            checks.require(
                "All Players(All Teams)" in call
                and "Eye Position(Event Player) + Facing Direction Of(Event Player) * 4 - Vector(0, 0.450, 0)" in call
                and "Visible To and Position" in call,
                "Nasib: icona nativa non è pubblica, non segue il mirino o manca la compensazione verticale da 0,45 m",
            )
        for call in [call for call in luck_icons if ", Skull," in call]:
            checks.require("Custom Color(255, 70, 70, 255)" in call, "Nasib: Skull non rosso")
        for call in [call for call in luck_icons if ", Heart," in call]:
            checks.require("Custom Color(70, 255, 110, 255)" in call, "Nasib: Heart non verde")
    checks.require(
        "Destroy Icon(Event Player.IkonKartuNasib);" in clean,
        "Nasib: cleanup icona nativa assente",
    )
'''
new_cards = '''    card_texts = [
        call for call in call_texts(source, "Create In-World Text")
        if "All Players(All Teams)" in call and ("Custom String(\\\"[\\\")" in call or "Custom String(\\\"]\\\")" in call)
    ]
    checks.equal(len(card_texts), 2, "Nasib: due parentesi separate e realmente distanziate")
    if len(card_texts) == 2:
        joined_cards = "\\n".join(card_texts)
        checks.require("Custom String(\\\"[\\\")" in joined_cards and "Custom String(\\\"]\\\")" in joined_cards, "Nasib: parentesi sinistra/destra mancanti")
        checks.require(joined_cards.count("* 0.800") == 2, "Nasib: parentesi non separate fisicamente di 0,8 m dal centro")
        checks.require(joined_cards.count("2.200, Do Not Clip") == 2, "Nasib: dimensione parentesi deve restare 2,2")
        checks.require(joined_cards.count("Event Player.KartuNasibMerah ? Custom Color(255, 70, 70, 255) : Custom Color(70, 255, 110, 255)") == 2, "Nasib: entrambe le parentesi devono seguire il colore")
    luck_icons = [call for call in call_texts(source, "Create Icon") if ", Skull," in call or ", Heart," in call]
    checks.equal(len(luck_icons), 2, "Nasib: Heart e Skull devono essere persistenti, non ricreati a ogni tick")
    if len(luck_icons) == 2:
        skull = next(call for call in luck_icons if ", Skull," in call)
        heart = next(call for call in luck_icons if ", Heart," in call)
        checks.require("Event Player.KartuNasibMerah ? All Players(All Teams) : Empty Array" in skull, "Nasib: Skull non alterna visibilità")
        checks.require("Event Player.KartuNasibMerah ? Empty Array : All Players(All Teams)" in heart, "Nasib: Heart non alterna visibilità")
        checks.require("Custom Color(255, 70, 70, 255)" in skull, "Nasib: Skull non rosso")
        checks.require("Custom Color(70, 255, 110, 255)" in heart, "Nasib: Heart non verde")
    if luck:
        pre_loop = mask_strings(luck[0].body).split("Loop If Condition Is True;")[0]
        checks.require("Create Icon(" not in pre_loop and "Destroy Icon(" not in pre_loop, "Nasib: Heart/Skull vengono ancora ricreati durante la roulette e possono vibrare")
    checks.require(
        "Destroy Icon(Event Player.IkonKartuNasib);" in clean
        and "Destroy Icon(Event Player.IkonKartuNasibHijau);" in clean,
        "Nasib: cleanup delle due icone persistenti assente",
    )
'''
validator = replace_once(validator, old_cards, new_cards, "validator split stable card")

validator = replace_once(
    validator,
    '                "Destroy In-World Text(Event Player.TeksKartuNasib);",\n                "Destroy Icon(Event Player.IkonKartuNasib);",\n                "Event Player.IkonKartuNasib = Null;",',
    '                "Destroy In-World Text(Event Player.TeksKartuNasib);",\n                "Destroy In-World Text(Event Player.TeksKartuNasibKanan);",\n                "Destroy Icon(Event Player.IkonKartuNasib);",\n                "Destroy Icon(Event Player.IkonKartuNasibHijau);",\n                "Event Player.IkonKartuNasib = Null;",\n                "Event Player.IkonKartuNasibHijau = Null;",',
    "validator complete death visual cleanup",
)

# The start of Menu 10 must freeze the custom camera into stable first person and save it for restore.
needle = '''        checks.require(
            "Call Subroutine(TutupMenu);" in after_luck,
            "Nasib: il menu non viene chiuso quando parte la carta",
        )'''
extra = '''        checks.require(
            "Event Player.ModeKameraSebelumNasib = Event Player.ModeKamera;" in before_luck
            and "Event Player.TargetKameraSebelumNasib = Event Player.TargetKamera;" in before_luck
            and "Stop Camera(Event Player);" in before_luck
            and "Event Player.ModeKamera = 0;" in before_luck,
            "Nasib: camera custom non viene salvata e bloccata in prima persona prima della carta",
        )
''' + needle
validator = replace_once(validator, needle, extra, "validator first person lock")
checks_restore_marker = '    blocked_one_hp = menu_interact['
restore_checks = '''    luck_rule_text = mask_strings(luck[0].body) if luck else ""
    checks.require(
        "Event Player.ModeKameraSebelumNasib == 1" in luck_rule_text
        and "Call Subroutine(MulaiKamera);" in luck_rule_text
        and "Event Player.ModeKameraSebelumNasib = 0;" in luck_rule_text
        and "Event Player.TargetKameraSebelumNasib = Null;" in luck_rule_text,
        "Nasib: camera precedente non viene ripristinata/azzerata dopo il risultato",
    )

'''
validator = replace_once(validator, checks_restore_marker, restore_checks + checks_restore_marker, "validator camera restore")
VALIDATOR.write_text(validator, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
old_doc = "Interact crea una carta virtuale agganciata al mirino del proprietario, circa 4 m davanti agli occhi, rivalutata ogni frame e visibile a tutti. La carta usa parentesi separate (`[     ]`, dimensione 2,2) e un vero `Create Icon` nativo: `Heart` verde oppure `Skull` rosso. Poiché `Create Icon` viene renderizzato visivamente più in alto rispetto all'In-World Text alla stessa coordinata, l'ancora dell'icona è compensata di `Vector(0, -0.450, 0)` rispetto al punto del mirino, così il simbolo cade dentro le parentesi. L'icona viene distrutta e ricreata a ogni cambio della roulette per garantire simbolo e colore corretti. Il Menu 10 non usa più alcun `Ring Explosion`. La roulette parte con colore casuale, esegue 20..24 cambi e parte da 0,08 s aggiungendo 0,055 s a ogni passaggio, quindi dura sensibilmente più a lungo e rallenta progressivamente."
new_doc = "Interact crea una carta virtuale centrata sul mirino e visibile a tutti. Per eliminare il jitter della camera custom, all'avvio viene salvato l'eventuale stato terza-persona/spettatore e la roulette usa temporaneamente la prima persona; al termine verde la camera precedente viene ripristinata. Le parentesi non dipendono più dagli spazi del font: sono due `Create In-World Text` separati, `[` e `]`, posti fisicamente a ±0,8 m dal centro della carta. `Heart` verde e `Skull` rosso sono due `Create Icon` persistenti creati una sola volta; il cambio rosso/verde rivaluta soltanto la loro visibilità, eliminando il precedente ciclo Destroy/Create che causava tremolio. Il Menu 10 non usa `Ring Explosion`. La roulette resta a 20..24 cambi con intervallo iniziale 0,08 s e +0,055 s per passaggio."
project = replace_once(project, old_doc, new_doc, "project stable card architecture")
PROJECT.write_text(project, encoding="utf-8")

validation = VALIDATION.read_text(encoding="utf-8")
validation = re.sub(
    r"- Menu 10 Try Your Luck: .*?esito 50/50;",
    "- Menu 10 Try Your Luck: parentesi `[` e `]` separate fisicamente a ±0,8 m, Heart/Skull persistenti senza ricreazione per tick, prima persona temporanea durante la roulette con ripristino camera precedente, Unkillable OFF, menu bloccato, reset alla morte, verde cura completa, rosso uccide dopo countdown 3 s, esito 50/50;",
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
