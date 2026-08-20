#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: atteso 1 match, trovati {count}")
    return text.replace(old, new, 1)


def git_blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


source = SOURCE.read_text(encoding="utf-8")
validator = VALIDATOR.read_text(encoding="utf-8")

# Burning: il damager Null non produce danno affidabile nel live test; usa self-damage esplicito.
source = replace_once(
    source,
    "Damage(Global.PemainAktif, Null, Max Health(Global.PemainAktif) * 0.025);",
    "Damage(Global.PemainAktif, Global.PemainAktif, Max Health(Global.PemainAktif) * 0.025);",
    "Burning self-damage",
)

# Anran: ad ogni morte la carica Ultimate deve andare immediatamente al 100%.
anran_rule = '''\n\nrule("16a - Anran: Ultimate al 100 percento ad ogni morte")\n{\n\tevent\n\t{\n\t\tPlayer Died;\n\t\tAll;\n\t\tAll;\n\t}\n\n\tconditions\n\t{\n\t\tHero Of(Event Player) == Hero(Anran);\n\t}\n\n\tactions\n\t{\n\t\tSet Ultimate Charge(Event Player, 100);\n\t}\n}\n'''
source = replace_once(
    source,
    '\nrule("17 - Balas Dendam: Catat hanya pembunuh langsung")',
    anran_rule + '\nrule("17 - Balas Dendam: Catat hanya pembunuh langsung")',
    "regola morte Anran",
)

# HUD: ogni blocco deve avere uno spacer proprio invece di essere visivamente attaccato al successivo.
source = replace_once(
    source,
    'Custom String("{0}    {1}", Custom String("CHILL DEDICATED SERVER"), Global.TeksWaktuServer),',
    'Custom String("{0}    {1}\\n ", Custom String("CHILL DEDICATED SERVER"), Global.TeksWaktuServer),',
    "spazio HUD centro",
)
for old, new, label in (
    ('Custom String("{0} - {1} MIN", Event Player, Event Player.MenitLobi)', 'Custom String("{0} - {1} MIN\\n ", Event Player, Event Player.MenitLobi)', "spazio HUD sinistra EN"),
    ('Custom String("{0} - {1} MENIT", Event Player, Event Player.MenitLobi)', 'Custom String("{0} - {1} MENIT\\n ", Event Player, Event Player.MenitLobi)', "spazio HUD sinistra ID"),
    ('Custom String("{0} - {1} นาที", Event Player, Event Player.MenitLobi)', 'Custom String("{0} - {1} นาที\\n ", Event Player, Event Player.MenitLobi)', "spazio HUD sinistra TH"),
):
    source = replace_once(source, old, new, label)
source = replace_once(
    source,
    'Custom String("{0} - {1}", Event Player,\n\t\t\tEvent Player.IndeksGenre >= 0 ?',
    'Custom String("{0} - {1}\\n ", Event Player,\n\t\t\tEvent Player.IndeksGenre >= 0 ?',
    "spazio HUD destra",
)

# Validator: Burning deve restare self-damage; Anran deve avere una regola Player Died senza polling.
validator = replace_once(
    validator,
    '"Damage(Global.PemainAktif, Null, Max Health(Global.PemainAktif) * 0.025);"',
    '"Damage(Global.PemainAktif, Global.PemainAktif, Max Health(Global.PemainAktif) * 0.025);"',
    "validator Burning self-damage",
)

marker = '    luck = find_rule(rules, "18e - Nasib:")\n'
anran_checks = '''    anran_death = find_rule(rules, "16a - Anran:")\n    checks.require(anran_death is not None, "regola morte Anran assente")\n    if anran_death:\n        checks.equal(event_type(anran_death), "Player Died", "Anran morte: evento")\n        checks.require("Hero Of(Event Player) == Hero(Anran);" in anran_death.body, "Anran morte non filtra Hero(Anran)")\n        checks.require("Set Ultimate Charge(Event Player, 100);" in anran_death.body, "Anran morte non porta Ultimate al 100%")\n        checks.require("Wait(" not in anran_death.body and "Loop If Condition Is True;" not in anran_death.body, "Anran morte non deve usare Wait o Loop")\n\n'''
validator = replace_once(validator, marker, anran_checks + marker, "validator Anran")

hud_guard_marker = '    checks.require("For Global Variable(Global." not in source, "sintassi For Global Variable(Global.*) non valida")\n'
hud_guards = '''    checks.require('Custom String("{0}    {1}\\\\n ", Custom String("CHILL DEDICATED SERVER"), Global.TeksWaktuServer)' in source, "HUD centro non è separato dal blocco successivo")\n    for token in (\n        'Custom String("{0} - {1} MIN\\\\n ", Event Player, Event Player.MenitLobi)',\n        'Custom String("{0} - {1} MENIT\\\\n ", Event Player, Event Player.MenitLobi)',\n        'Custom String("{0} - {1} นาที\\\\n ", Event Player, Event Player.MenitLobi)',\n        'Custom String("{0} - {1}\\\\n ", Event Player,',\n    ):\n        checks.require(token in source, f"HUD player non separato: {token}")\n'''
validator = replace_once(validator, hud_guard_marker, hud_guard_marker + hud_guards, "validator HUD spacing")

blob = git_blob_sha(source)
validator, n = re.subn(r'EXPECTED_SOURCE_BLOB = "[0-9a-f]{40}"', f'EXPECTED_SOURCE_BLOB = "{blob}"', validator, count=1)
if n != 1:
    raise RuntimeError("EXPECTED_SOURCE_BLOB non aggiornato")

SOURCE.write_text(source, encoding="utf-8")
VALIDATOR.write_text(validator, encoding="utf-8")
print(f"patched source blob: {blob}")
