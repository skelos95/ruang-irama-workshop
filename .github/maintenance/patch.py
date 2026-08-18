from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"

OLD_BLOB = "3d72da2b4da10ba90a351529a65c073b58fbd117"


def git_blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected 1 match, found {count}")
    return text.replace(old, new, 1)


def rule_bounds(text: str, title: str) -> tuple[int, int]:
    needle = f'rule("{title}")'
    start = text.index(needle)
    next_rule = text.find('\nrule("', start + len(needle))
    return start, len(text) if next_rule < 0 else next_rule


def edit_rule(text: str, title: str, editor) -> str:
    start, end = rule_bounds(text, title)
    block = text[start:end]
    edited = editor(block)
    if edited == block:
        raise RuntimeError(f"rule unchanged: {title}")
    return text[:start] + edited + text[end:]


source = SOURCE.read_text(encoding="utf-8")
if git_blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch a moving target")

# Dedicated memory for the target currently represented by the page-3 world label.
source = replace_once(
    source,
    "\t\t95: HalamanSubmenuPramuat\n}",
    "\t\t95: HalamanSubmenuPramuat\n\t\t96: TargetTeleportasiTeks\n}",
    "player variable declaration",
)

# Capture Spawn Room almost immediately while the human is physically inside it.
def patch_fast_manager(block: str) -> str:
    anchor = "\t\t\tGlobal.PemainAktif = All Players(All Teams)[Global.IndeksPemainGlobal];\n"
    addition = '''\t\t\tGlobal.PemainAktif = All Players(All Teams)[Global.IndeksPemainGlobal];\n\t\tIf(And(Global.PemainAktif.Manusia == True, And(Has Spawned(Global.PemainAktif) == True, Is In Spawn Room(Global.PemainAktif) == True)));\n\t\t\tSet Player Variable(Global.PemainAktif, PosisiRuangMuncul, Position Of(Global.PemainAktif));\n\t\t\tSet Player Variable(Global.PemainAktif, PunyaPosisiMuncul, True);\n\t\tEnd;\n'''
    return replace_once(block, anchor, addition, "04g fast spawn cache")

source = edit_rule(source, "04g - Global-first: Pengatur status cepat terpusat", patch_fast_manager)

# Remove the redundant 1 Hz Spawn Room cache now that 04g owns it.
def patch_passive_manager(block: str) -> str:
    old = '''\t\t\t\tIf(And(Has Spawned(Global.PemainAktif) == True, Is In Spawn Room(Global.PemainAktif) == True));\n\t\t\t\t\tSet Player Variable(Global.PemainAktif, PosisiRuangMuncul, Position Of(Global.PemainAktif));\n\t\t\t\t\tSet Player Variable(Global.PemainAktif, PunyaPosisiMuncul, True);\n\t\t\t\tEnd;\n\n'''
    return replace_once(block, old, "", "04i old spawn cache")

source = edit_rule(source, "04i - Global-first: Cache dan daftar pasif 1 Hz", patch_passive_manager)

# Explicitly invalidate the old label whenever the closest-to-reticle target changes.
def patch_reticle_manager(block: str) -> str:
    old = '''\t\t\t\tIf(Count Of(Global.PemainAktif.DaftarTargetTeleportasi) == 0);\n\t\t\t\t\tSet Player Variable(Global.PemainAktif, CalonTargetTeleportasi, Null);\n\t\t\t\tElse;\n\t\t\t\t\tSet Player Variable(Global.PemainAktif, CalonTargetTeleportasi, First Of(Sorted Array(Global.PemainAktif.DaftarTargetTeleportasi,\n\t\t\t\t\t\tAngle Between Vectors(Facing Direction Of(Global.PemainAktif), Direction Towards(Eye Position(Global.PemainAktif), Eye Position(Current Array Element))))));\n\t\t\t\tEnd;\n'''
    new = old + '''\t\t\t\tIf(Global.PemainAktif.TargetTeleportasiTeks != Global.PemainAktif.CalonTargetTeleportasi);\n\t\t\t\t\tIf(Global.PemainAktif.TeksDunia != Null);\n\t\t\t\t\t\tDestroy In-World Text(Global.PemainAktif.TeksDunia);\n\t\t\t\t\tEnd;\n\t\t\t\t\tIf(Index Of Array Value(Global.PemainManusia, Global.PemainAktif) >= 0);\n\t\t\t\t\t\tGlobal.TeksDuniaPemain[Index Of Array Value(Global.PemainManusia, Global.PemainAktif)] = 0;\n\t\t\t\t\tEnd;\n\t\t\t\t\tSet Player Variable(Global.PemainAktif, TeksDunia, Null);\n\t\t\t\t\tSet Player Variable(Global.PemainAktif, TargetTeleportasiTeks, Global.PemainAktif.CalonTargetTeleportasi);\n\t\t\t\tEnd;\n'''
    return replace_once(block, old, new, "04k live label invalidation")

source = edit_rule(source, "04k - Global-first: Inspeksi dan target teleport terpusat 4 Hz", patch_reticle_manager)

# When changing pages, clear the dedicated label target outside page 3 and seed it immediately on entry.
def patch_page_cycle(block: str) -> str:
    block = replace_once(
        block,
        "\t\t\tEvent Player.TeksDunia = Null;\n\t\t\tIf(Event Player.PelatNamaDinonaktifkan == True);",
        "\t\t\tEvent Player.TeksDunia = Null;\n\t\t\tEvent Player.TargetTeleportasiTeks = Null;\n\t\t\tIf(Event Player.PelatNamaDinonaktifkan == True);",
        "19c leave page 3 label reset",
    )
    block = replace_once(
        block,
        "\t\t\tCall Subroutine(SegarkanTargetTeleportasi);\n\t\tEnd;",
        "\t\t\tCall Subroutine(SegarkanTargetTeleportasi);\n\t\t\tEvent Player.TargetTeleportasiTeks = Event Player.CalonTargetTeleportasi;\n\t\tEnd;",
        "19c enter page 3 label seed",
    )
    return block

source = edit_rule(source, "19c - Teleportasi Jongkok: Secondary Fire mengganti tiga halaman", patch_page_cycle)

# The label is recreated from an explicit snapshot whenever 04k invalidates it.
def patch_target_label(block: str) -> str:
    old_actions = '''\t\tDisable Nameplates(All Players(All Teams), Event Player);\n\t\tEvent Player.PelatNamaDinonaktifkan = True;\n\t\tCall Subroutine(SegarkanTargetTeleportasi);\n\t\tCreate In-World Text(Event Player, Event Player.CalonTargetTeleportasi == Null ? Custom String("") : Custom String("{0} {1} | {2}",\n\t\t\tHero Icon String(Is Duplicating(Event Player.CalonTargetTeleportasi) ? Hero Being Duplicated(Event Player.CalonTargetTeleportasi) : Hero Of(Event Player.CalonTargetTeleportasi)),\n\t\t\tCustom String("{0}", Event Player.CalonTargetTeleportasi), Round To Integer(Health(Event Player.CalonTargetTeleportasi), Down)),\n\t\t\tEvent Player.CalonTargetTeleportasi == Null ? Eye Position(Event Player) : Eye Position(Event Player.CalonTargetTeleportasi) + Vector(0, 0.450, 0),\n\t\t\t1.100, Do Not Clip, Visible To Position String and Color, Event Player.CalonTargetTeleportasi == Null ? Color(White)\n\t\t\t: Player Variable(Event Player.CalonTargetTeleportasi, Manusia) == True ? Player Variable(Event Player.CalonTargetTeleportasi, WarnaNama) : Color(Orange), Visible Never);'''
    new_actions = '''\t\tDisable Nameplates(All Players(All Teams), Event Player);\n\t\tEvent Player.PelatNamaDinonaktifkan = True;\n\t\tCall Subroutine(SegarkanTargetTeleportasi);\n\t\tEvent Player.TargetTeleportasiTeks = Event Player.CalonTargetTeleportasi;\n\t\tAbort If(Event Player.TargetTeleportasiTeks == Null);\n\t\tCreate In-World Text(Event Player, Custom String("{0} {1} | {2}",\n\t\t\tHero Icon String(Is Duplicating(Event Player.TargetTeleportasiTeks) ? Hero Being Duplicated(Event Player.TargetTeleportasiTeks) : Hero Of(Event Player.TargetTeleportasiTeks)),\n\t\t\tCustom String("{0}", Event Player.TargetTeleportasiTeks), Round To Integer(Health(Event Player.TargetTeleportasiTeks), Down)),\n\t\t\tEye Position(Event Player.TargetTeleportasiTeks) + Vector(0, 0.450, 0), 1.100, Do Not Clip, Visible To Position String and Color,\n\t\t\tPlayer Variable(Event Player.TargetTeleportasiTeks, Manusia) == True ? Player Variable(Event Player.TargetTeleportasiTeks, WarnaNama) : Color(Orange), Visible Never);'''
    return replace_once(block, old_actions, new_actions, "19d explicit target snapshot")

source = edit_rule(source, "19d - Teleportasi Jongkok: Nama target publik mengikuti reticolo", patch_target_label)

# Spawn teleport uses the cached point but resolves it to a valid walkable position.
def patch_teleport_execute(block: str) -> str:
    return replace_once(
        block,
        "\t\t\t\tTeleport(Event Player, Event Player.PosisiRuangMuncul);",
        "\t\t\t\tTeleport(Event Player, Nearest Walkable Position(Event Player.PosisiRuangMuncul));",
        "19e spawn nearest walkable",
    )

source = edit_rule(source, "19e - Teleportasi Jongkok: Primary Fire menjalankan halaman aktif", patch_teleport_execute)

# Closing Crouch also clears the label snapshot.
def patch_teleport_close(block: str) -> str:
    return replace_once(
        block,
        "\t\tEvent Player.CalonTargetTeleportasi = Null;\n\t\tEvent Player.JenisTeleportasiTerkunci = -1;",
        "\t\tEvent Player.CalonTargetTeleportasi = Null;\n\t\tEvent Player.TargetTeleportasiTeks = Null;\n\t\tEvent Player.JenisTeleportasiTerkunci = -1;",
        "19g label snapshot cleanup",
    )

source = edit_rule(source, "19g - Teleportasi Jongkok: Tutup saat Jongkok dilepas", patch_teleport_close)

SOURCE.write_text(source, encoding="utf-8")
new_blob = git_blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_once(
    validator,
    f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"',
    f'EXPECTED_SOURCE_BLOB = "{new_blob}"',
    "validator blob",
)
validator = replace_once(
    validator,
    '    for name in ("HalamanMenuTujuan", "HalamanSubmenuPramuat"):\n',
    '    for name in ("HalamanMenuTujuan", "HalamanSubmenuPramuat", "TargetTeleportasiTeks"):\n',
    "validator player variable",
)
anchor = '    interact = find_rule(rules, "10 - Menu:")\n'
guards = '''    fast_manager = find_rule(rules, "04g - Global-first:")\n    if fast_manager:\n        checks.require("Set Player Variable(Global.PemainAktif, PosisiRuangMuncul, Position Of(Global.PemainAktif));" in fast_manager.body, "Spawn Room non viene registrata nel manager rapido")\n        checks.require("Set Player Variable(Global.PemainAktif, PunyaPosisiMuncul, True);" in fast_manager.body, "flag Spawn Room non viene registrato nel manager rapido")\n    passive_manager = find_rule(rules, "04i - Global-first:")\n    if passive_manager:\n        checks.require("PosisiRuangMuncul" not in passive_manager.body, "Spawn Room è ancora aggiornata dal manager lento 1 Hz")\n    if teleport_global:\n        checks.require("TargetTeleportasiTeks != Global.PemainAktif.CalonTargetTeleportasi" in teleport_global.body, "target label Teleport non rileva il cambio sotto il mirino")\n        checks.require("Destroy In-World Text(Global.PemainAktif.TeksDunia);" in teleport_global.body, "target label Teleport non viene invalidato al cambio target")\n    if teleport_label:\n        checks.require("Event Player.TargetTeleportasiTeks = Event Player.CalonTargetTeleportasi;" in teleport_label.body, "19d non fotografa il target corrente")\n        checks.require("Eye Position(Event Player.TargetTeleportasiTeks)" in teleport_label.body, "19d non usa il target label dedicato")\n    if teleport_exec:\n        checks.require("Nearest Walkable Position(Event Player.PosisiRuangMuncul)" in teleport_exec.body, "Spawn teleport non usa una posizione camminabile")\n'''
validator = replace_once(validator, anchor, guards + anchor, "validator hotfix guards")
VALIDATOR.write_text(validator, encoding="utf-8")

print(f"hotfixed 0.7.2 live labels + spawn: {OLD_BLOB} -> {new_blob}")
