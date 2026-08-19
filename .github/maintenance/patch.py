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

# Ultimate Always Ready must be controlled only by its effect id + timestamp,
# never by the roulette/menu lifecycle flag.
old_ultimate = '''\t\tIf(And(Global.PemainAktif.Manusia == True, Entity Exists(Global.PemainAktif)));
\t\t\tIf(And(Global.PemainAktif.KartuNasibAktif == True, Global.PemainAktif.PutaranKartuNasib == 0));
\t\t\t\tIf(And(Global.PemainAktif.EfekNasib == 2, And(Global.PemainAktif.EfekNasibBerakhir > Total Time Elapsed, Is Alive(Global.PemainAktif) == True)));
\t\t\t\t\tSet Ultimate Charge(Global.PemainAktif, 100);
\t\t\t\tEnd;
\t\t\tEnd;
\t\tEnd;'''
new_ultimate = '''\t\tIf(And(Global.PemainAktif.Manusia == True, Entity Exists(Global.PemainAktif)));
\t\t\tIf(And(Global.PemainAktif.EfekNasib == 2, And(Global.PemainAktif.EfekNasibBerakhir > Total Time Elapsed,
\t\t\t\tAnd(Has Spawned(Global.PemainAktif) == True, Is Alive(Global.PemainAktif) == True))));
\t\t\t\tSet Ultimate Charge(Global.PemainAktif, 100);
\t\t\tEnd;
\t\tEnd;'''
source = replace_once(source, old_ultimate, new_ultimate, "Ultimate always-ready indipendente dalla roulette")

# Effect HUD: only effect + remaining time. The leading blank line places it
# visually below CHILL DEDICATED SERVER (Top -100 -> effect Top -99).
source = replace_once(
    source,
    'Create HUD Text(Event Player, Null, Null, Custom String("TRY YOUR LUCK\\n \\n{0}\\n{1}",',
    'Create HUD Text(Event Player, Null, Null, Custom String("\\n{0}\\n{1}",',
    "HUD effetto senza TRY YOUR LUCK",
)
source = replace_once(
    source,
    'Max(0, Round To Integer(Event Player.EfekNasibBerakhir - Total Time Elapsed, Up)))), Top, 100,\n\t\t\tColor(White), Color(White), Global.RGB, Visible To String and Color, Visible Never);',
    'Max(0, Round To Integer(Event Player.EfekNasibBerakhir - Total Time Elapsed, Up)))), Top, -99,\n\t\t\tColor(White), Color(White), Global.RGB, Visible To String and Color, Visible Never);',
    "HUD effetto sotto titolo server",
)

# Validator: require the exact stronger Ultimate lifecycle.
old_fast = '''    if fast_manager:\n        checks.require("Set Ultimate Charge(Global.PemainAktif, 100);" in fast_manager.body, "Ultimate always-ready non è gestita dal manager globale")\n        checks.require("Total Time Elapsed >= Global.PemainAktif.EfekNasibBerakhir" not in fast_manager.body, "04g gestisce ancora la scadenza Try Your Luck condivisa")'''
new_fast = '''    if fast_manager:\n        checks.require("Set Ultimate Charge(Global.PemainAktif, 100);" in fast_manager.body, "Ultimate always-ready non è gestita dal manager globale")\n        checks.require("Global.PemainAktif.EfekNasib == 2" in fast_manager.body and "Global.PemainAktif.EfekNasibBerakhir > Total Time Elapsed" in fast_manager.body, "Ultimate always-ready non resta legata al timestamp effetto")\n        checks.require("Global.PemainAktif.KartuNasibAktif == True" not in fast_manager.body, "Ultimate always-ready dipende ancora dal flag roulette/menu")\n        checks.require("Has Spawned(Global.PemainAktif) == True" in fast_manager.body and "Is Alive(Global.PemainAktif) == True" in fast_manager.body, "Ultimate always-ready non verifica player vivo e spawnato")\n        checks.require("Total Time Elapsed >= Global.PemainAktif.EfekNasibBerakhir" not in fast_manager.body, "04g gestisce ancora la scadenza Try Your Luck condivisa")'''
validator = replace_once(validator, old_fast, new_fast, "validator Ultimate always-ready")

old_hud = '''        checks.require('Create HUD Text(Event Player, Null, Null, Custom String("TRY YOUR LUCK\\\\n \\\\n{0}\\\\n{1}"' in luck_effect_hud.body, "18k deve usare solo il campo Text con spazio dopo TRY YOUR LUCK")\n        checks.require("EfekNasibBerakhir - Total Time Elapsed" in luck_effect_hud.body and "s REMAINING" in luck_effect_hud.body, "18k non mostra countdown")'''
new_hud = '''        checks.require('Create HUD Text(Event Player, Null, Null, Custom String("\\\\n{0}\\\\n{1}"' in luck_effect_hud.body, "18k deve mostrare solo effetto e durata nel campo Text")\n        checks.require('Custom String("TRY YOUR LUCK' not in luck_effect_hud.body, "18k mostra ancora TRY YOUR LUCK")\n        checks.require("Top, -99" in luck_effect_hud.body, "18k non lascia lo spazio sotto CHILL DEDICATED SERVER")\n        checks.require("EfekNasibBerakhir - Total Time Elapsed" in luck_effect_hud.body and "s REMAINING" in luck_effect_hud.body, "18k non mostra countdown")'''
validator = replace_once(validator, old_hud, new_hud, "validator HUD effetto")

blob = git_blob_sha(source)
validator, n = re.subn(r'EXPECTED_SOURCE_BLOB = "[0-9a-f]{40}"', f'EXPECTED_SOURCE_BLOB = "{blob}"', validator, count=1)
if n != 1:
    raise RuntimeError("EXPECTED_SOURCE_BLOB non aggiornato")

SOURCE.write_text(source, encoding="utf-8")
VALIDATOR.write_text(validator, encoding="utf-8")
print(f"patched source blob: {blob}")
