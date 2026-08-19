from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"

OLD_BLOB = "38d033db93dae7a3fad988f6cdae6f94812805da"


def blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def one(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one match, found {count}: {old[:180]!r}")
    return text.replace(old, new, 1)


def rule_bounds(text: str, title: str) -> tuple[int, int]:
    needle = f'rule("{title}")'
    start = text.index(needle)
    nxt = text.find('\nrule("', start + len(needle))
    return start, len(text) if nxt < 0 else nxt


def edit_rule(text: str, title: str, editor) -> str:
    start, end = rule_bounds(text, title)
    block = text[start:end]
    new = editor(block)
    if new == block:
        raise RuntimeError(f"rule unchanged: {title}")
    return text[:start] + new + text[end:]


def insert_after_rule(text: str, title: str, block: str) -> str:
    _, end = rule_bounds(text, title)
    return text[:end].rstrip() + "\n\n\n" + block.rstrip() + "\n" + text[end:]


source = SOURCE.read_text(encoding="utf-8")
if blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch moving target")

# Dedicated one-shot flag. Global managers can set it; an Each Player event
# owns the actual HUD recreation because GambarMenu depends on Event Player.
source = one(
    source,
    "\t\t106: HasilNasibTerkunci\n}",
    "\t\t106: HasilNasibTerkunci\n\t\t107: MenuNasibHarusDibuka\n}",
)

# New roulette starts with no pending reopen request.
def edit_interact(block: str) -> str:
    old = "\t\t\t\tEvent Player.HasilNasibTerkunci = 0;\n"
    if block.count(old) != 1:
        raise RuntimeError(f"Try Your Luck start marker mismatch: {block.count(old)}")
    return block.replace(old, old + "\t\t\t\tEvent Player.MenuNasibHarusDibuka = False;\n", 1)

source = edit_rule(source, "10 - Menu: Interaksi membuka atau menerapkan pilihan", edit_interact)

# End of roulette: close the menu for real. TutupMenu destroys its HUD and,
# importantly, restores all hero buttons / InputMenuDikunci immediately.
def edit_luck(block: str) -> str:
    old_close = "\t\tEvent Player.EfekNasibBerakhir = 0;\n\t\tEvent Player.HasilNasibTerkunci = 0;\n\n\t\tIf(Event Player.EfekNasib == 1);"
    new_close = "\t\tEvent Player.MenuNasibHarusDibuka = False;\n\t\tCall Subroutine(TutupMenu);\n\t\tEvent Player.EfekNasibBerakhir = 0;\n\t\tEvent Player.HasilNasibTerkunci = 0;\n\n\t\tIf(Event Player.EfekNasib == 1);"
    if block.count(old_close) != 1:
        raise RuntimeError("roulette close marker mismatch")
    block = block.replace(old_close, new_close, 1)

    # Instant outcomes (teleport / heart) reach the common tail with
    # KartuNasibAktif=False. Request reopen only after the final icon linger.
    old_tail = """\t\tEvent Player.PutaranKartuNasib = 0;\n\t\tEvent Player.JedaKartuNasib = 0;\n\t\tIf(And(Event Player.MenuTerbuka == True, Event Player.HalamanMenu == 10));\n\t\t\tCall Subroutine(GambarMenu);\n\t\tEnd;"""
    new_tail = """\t\tEvent Player.PutaranKartuNasib = 0;\n\t\tEvent Player.JedaKartuNasib = 0;\n\t\tIf(Event Player.KartuNasibAktif == False);\n\t\t\tEvent Player.MenuNasibHarusDibuka = True;\n\t\tEnd;"""
    if block.count(old_tail) != 1:
        raise RuntimeError("roulette common-tail marker mismatch")
    return block.replace(old_tail, new_tail, 1)

source = edit_rule(source, "18e - Nasib: Roulette sepuluh efek dengan hasil terkunci", edit_luck)

# Timed outcomes request reopen at the exact expiry from the existing global
# 16 ms manager. It does not render HUD itself.
def edit_fast(block: str) -> str:
    old = "\t\t\t\t\tSet Player Variable(Global.PemainAktif, KartuNasibAktif, False);\n"
    if block.count(old) != 1:
        raise RuntimeError(f"04g expiry marker mismatch: {block.count(old)}")
    new = old + "\t\t\t\t\tSet Player Variable(Global.PemainAktif, MenuNasibHarusDibuka, True);\n"
    return block.replace(old, new, 1)

source = edit_rule(source, "04g - Global-first: Pengatur status cepat terpusat", edit_fast)

# Skull / floor-fall and any other death during an active result reopen only
# after the complete death reset has restored every modifier.
def edit_death(block: str) -> str:
    old = "\t\tEvent Player.KartuNasibAktif = False;\n"
    if block.count(old) != 1:
        raise RuntimeError(f"18f active-reset marker mismatch: {block.count(old)}")
    return block.replace(old, old + "\t\tEvent Player.MenuNasibHarusDibuka = True;\n", 1)

source = edit_rule(source, "18f - Nasib: Reset lengkap semua efek saat pemilik mati", edit_death)

# Single event-driven UI handoff. Crouch and Jump are intentionally untouched;
# all captured hero buttons are explicitly returned before GambarMenu.
reopen_rule = r'''rule("18g - Nasib: Riapri menu solo quando la funzione finisce")
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
\t\tEvent Player.MenuNasibHarusDibuka == True;
\t\tEvent Player.KartuNasibAktif == False;
\t}

\tactions
\t{
\t\tEvent Player.MenuNasibHarusDibuka = False;
\t\tEvent Player.InputMenuDikunci = False;
\t\tEvent Player.PerintahMenu = 0;
\t\tAllow Button(Event Player, Button(Primary Fire));
\t\tAllow Button(Event Player, Button(Secondary Fire));
\t\tAllow Button(Event Player, Button(Interact));
\t\tAllow Button(Event Player, Button(Reload));
\t\tAllow Button(Event Player, Button(Ability 1));
\t\tAllow Button(Event Player, Button(Ability 2));
\t\tAllow Button(Event Player, Button(Ultimate));
\t\tEvent Player.MenuTerbuka = True;
\t\tEvent Player.HalamanMenu = 10;
\t\tEvent Player.HalamanMenuTujuan = 10;
\t\tCall Subroutine(GambarMenu);
\t}
}'''
source = insert_after_rule(source, "18f - Nasib: Reset lengkap semua efek saat pemilik mati", reopen_rule)

# Initialize / cleanup the one-shot flag so join, team switch and leave cannot
# resurrect an old Try Your Luck menu request.
def add_flag_after_result(block: str, label: str) -> str:
    old = "\t\tEvent Player.HasilNasibTerkunci = 0;\n"
    if block.count(old) != 1:
        raise RuntimeError(f"{label} result-state marker mismatch: {block.count(old)}")
    return block.replace(old, old + "\t\tEvent Player.MenuNasibHarusDibuka = False;\n", 1)

source = edit_rule(source, "93c - Subrutin: Bersihkan pemain saat keluar atau pindah tim", lambda b: add_flag_after_result(b, "cleanup"))
source = edit_rule(source, "94 - Subrutin: Siapkan pemain dari ujung rambut sampai variabel", lambda b: add_flag_after_result(b, "init"))

SOURCE.write_text(source, encoding="utf-8")
new_blob = blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = one(validator, f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"', f'EXPECTED_SOURCE_BLOB = "{new_blob}"')
validator = one(
    validator,
    '"PrivasiNasibAktif", "KategoriTeleportNasib", "HasilNasibTerkunci"):',
    '"PrivasiNasibAktif", "KategoriTeleportNasib", "HasilNasibTerkunci", "MenuNasibHarusDibuka"):',
)

old_luck_decl = '    luck = find_rule(rules, "18e - Nasib:")\n    luck_death = find_rule(rules, "18f - Nasib:")\n    checks.require(luck is not None and luck_death is not None, "pipeline Try Your Luck a dieci risultati assente")\n'
new_luck_decl = '    luck = find_rule(rules, "18e - Nasib:")\n    luck_death = find_rule(rules, "18f - Nasib:")\n    luck_reopen = find_rule(rules, "18g - Nasib:")\n    checks.require(luck is not None and luck_death is not None and luck_reopen is not None, "pipeline Try Your Luck a dieci risultati assente")\n'
validator = one(validator, old_luck_decl, new_luck_decl)

validator = one(
    validator,
    '        checks.require("Start Forcing Player Position(" not in luck.body, "Try Your Luck non deve forzare la posizione")\n',
    '        checks.require("Start Forcing Player Position(" not in luck.body, "Try Your Luck non deve forzare la posizione")\n'
    '        checks.require("Call Subroutine(TutupMenu);" in luck.body, "Try Your Luck non chiude il menu alla fine della roulette")\n'
    '        checks.require("Event Player.MenuNasibHarusDibuka = True;" in luck.body, "Try Your Luck istantaneo non richiede la riapertura dopo il risultato")\n',
)

validator = one(
    validator,
    '            checks.require(token in luck_death.body, f"reset morte Try Your Luck incompleto: {token}")\n',
    '            checks.require(token in luck_death.body, f"reset morte Try Your Luck incompleto: {token}")\n'
    '        checks.require("Event Player.MenuNasibHarusDibuka = True;" in luck_death.body, "morte Try Your Luck non richiede la riapertura dopo il reset")\n'
    '    if luck_reopen:\n'
    '        checks.equal(event_type(luck_reopen), "Ongoing - Each Player", "18g riapertura Try Your Luck: scheduler")\n'
    '        checks.require("Event Player.KartuNasibAktif == False;" in luck_reopen.body, "18g riapre il menu prima che la funzione sia finita")\n'
    '        checks.require("Event Player.HalamanMenu = 10;" in luck_reopen.body and "Call Subroutine(GambarMenu);" in luck_reopen.body, "18g non riapre la pagina Try Your Luck")\n'
    '        checks.require("Event Player.InputMenuDikunci = False;" in luck_reopen.body, "18g non libera il latch input del menu")\n'
    '        for button in ("Primary Fire", "Secondary Fire", "Interact", "Reload", "Ability 1", "Ability 2", "Ultimate"):\n'
    '            checks.require(f"Allow Button(Event Player, Button({button}));" in luck_reopen.body, f"18g non restituisce {button}")\n'
    '        checks.require("Disallow Button(Event Player, Button(Crouch));" not in luck_reopen.body and "Disallow Button(Event Player, Button(Jump));" not in luck_reopen.body, "18g non deve bloccare Crouch o Jump")\n',
)

validator = one(
    validator,
    '        checks.require("Global.PemainAktif.EfekNasibBerakhir" in fast_manager.body, "timer Try Your Luck non è Global-first")\n',
    '        checks.require("Global.PemainAktif.EfekNasibBerakhir" in fast_manager.body, "timer Try Your Luck non è Global-first")\n'
    '        checks.require("Set Player Variable(Global.PemainAktif, MenuNasibHarusDibuka, True);" in fast_manager.body, "scadenza Try Your Luck non consegna la riapertura al player")\n',
)

VALIDATOR.write_text(validator, encoding="utf-8")
print(f"Try Your Luck menu lifecycle: {OLD_BLOB} -> {new_blob}")
