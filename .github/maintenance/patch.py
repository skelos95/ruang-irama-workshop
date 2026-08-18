from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
README = ROOT / "README.md"

OLD_BLOB = "4d5b46c8606c368fb65066a16a4f0d4c96be7ac6"


def git_blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def replace_exact(text: str, old: str, new: str, expected: int = 1) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"replacement mismatch: expected {expected}, found {count}: {old[:160]!r}")
    return text.replace(old, new)


source = SOURCE.read_text(encoding="utf-8")
if git_blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch a moving target")

# Remove the legacy Spawn Room coordinate cache completely.
source = replace_exact(source, "\t\t39: PosisiRuangMuncul\n", "")
source = replace_exact(source, "\t\t40: PunyaPosisiMuncul\n", "")

spawn_cache = '''\t\tIf(And(Global.PemainAktif.Manusia == True, And(Has Spawned(Global.PemainAktif) == True, Is In Spawn Room(Global.PemainAktif) == True)));\n\t\t\tSet Player Variable(Global.PemainAktif, PosisiRuangMuncul, Position Of(Global.PemainAktif));\n\t\t\tSet Player Variable(Global.PemainAktif, PunyaPosisiMuncul, True);\n\t\tEnd;\n'''
source = replace_exact(source, spawn_cache, "")

source = replace_exact(source, "\t\tEvent Player.PosisiRuangMuncul = Vector(0, 0, 0);\n", "")
source = replace_exact(source, "\t\tEvent Player.PunyaPosisiMuncul = False;\n", "")

old_spawn = '''\t\tIf(Event Player.JenisTeleportasiTerkunci == 0);\n\t\t\tIf(Is In Spawn Room(Event Player) == True);\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("You are already in the Spawn Room. Mission accomplished.") : Event Player.IndeksBahasa == 1 ? Custom String("Kamu sudah di ruang muncul. Misi selesai.") : Custom String("คุณอยู่ในห้องเกิดแล้ว ภารกิจสำเร็จ"));\n\t\t\tElse If(Event Player.PunyaPosisiMuncul == False);\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Spawn Room not registered yet. Visit spawn first.") : Event Player.IndeksBahasa == 1 ? Custom String("Posisi ruang muncul belum tersimpan. Masuk ke sana dulu.") : Custom String("ยังไม่ได้บันทึกห้องเกิด กรุณาไปที่ห้องเกิดก่อน"));\n\t\t\tElse;\n\t\t\t\tTeleport(Event Player, Nearest Walkable Position(Event Player.PosisiRuangMuncul));\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Back to the Spawn Room. Tactical retreat complete.") : Event Player.IndeksBahasa == 1 ? Custom String("Kembali ke ruang muncul. Mundur taktis selesai.") : Custom String("กลับสู่ห้องเกิดแล้ว การถอยเชิงกลยุทธ์เสร็จสิ้น"));\n\t\t\tEnd;\n'''
new_spawn = '''\t\tIf(Event Player.JenisTeleportasiTerkunci == 0);\n\t\t\tIf(Is In Spawn Room(Event Player) == True);\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("You are already in the Spawn Room. Mission accomplished.") : Event Player.IndeksBahasa == 1 ? Custom String("Kamu sudah di ruang muncul. Misi selesai.") : Custom String("คุณอยู่ในห้องเกิดแล้ว ภารกิจสำเร็จ"));\n\t\t\tElse If(Count Of(Spawn Points(Team Of(Event Player))) == 0);\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Spawn Room unavailable on this map right now.") : Event Player.IndeksBahasa == 1 ? Custom String("Ruang muncul tidak tersedia di map ini saat ini.") : Custom String("ห้องเกิดยังไม่พร้อมใช้งานบนแผนที่นี้"));\n\t\t\tElse;\n\t\t\t\tTeleport(Event Player, Position Of(First Of(Spawn Points(Team Of(Event Player)))));\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Teleported to your Spawn Room.") : Event Player.IndeksBahasa == 1 ? Custom String("Teleport ke ruang muncul timmu.") : Custom String("เทเลพอร์ตไปห้องเกิดของทีมแล้ว"));\n\t\t\tEnd;\n'''
source = replace_exact(source, old_spawn, new_spawn)

# Page 1 is always directly usable now; no registration state is shown.
source = replace_exact(
    source,
    'Event Player.PunyaPosisiMuncul ? Custom String("READY") : Custom String("VISIT SPAWN TO REGISTER IT")',
    'Custom String("PRIMARY FIRE: TELEPORT")',
)
source = replace_exact(
    source,
    'Event Player.PunyaPosisiMuncul ? Custom String("SIAP") : Custom String("MASUK SPAWN UNTUK MENYIMPANNYA")',
    'Custom String("PRIMARY FIRE: TELEPORT")',
)
source = replace_exact(
    source,
    'Event Player.PunyaPosisiMuncul ? Custom String("พร้อม") : Custom String("ไปห้องเกิดเพื่อบันทึกตำแหน่ง")',
    'Custom String("ยิงหลัก: เทเลพอร์ต")',
)

if "PosisiRuangMuncul" in source or "PunyaPosisiMuncul" in source:
    raise RuntimeError("legacy Spawn Room cache references remain")
if "Teleport(Event Player, Position Of(First Of(Spawn Points(Team Of(Event Player)))));" not in source:
    raise RuntimeError("direct Spawn Points teleport was not installed")

SOURCE.write_text(source, encoding="utf-8")
new_blob = git_blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_exact(
    validator,
    f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"',
    f'EXPECTED_SOURCE_BLOB = "{new_blob}"',
)

old_spawn_checks = '''    fast_manager = find_rule(rules, "04g - Global-first:")\n    if fast_manager:\n        checks.require("Set Player Variable(Global.PemainAktif, PosisiRuangMuncul, Position Of(Global.PemainAktif));" in fast_manager.body, "Spawn Room non viene registrata nel manager rapido")\n        checks.require("Set Player Variable(Global.PemainAktif, PunyaPosisiMuncul, True);" in fast_manager.body, "flag Spawn Room non viene registrato nel manager rapido")\n    passive_manager = find_rule(rules, "04i - Global-first:")\n    if passive_manager:\n        checks.require("PosisiRuangMuncul" not in passive_manager.body, "Spawn Room è ancora aggiornata dal manager lento 1 Hz")\n'''
new_spawn_checks = '''    fast_manager = find_rule(rules, "04g - Global-first:")\n    passive_manager = find_rule(rules, "04i - Global-first:")\n    checks.require("PosisiRuangMuncul" not in source and "PunyaPosisiMuncul" not in source, "cache Spawn Room legacy ancora presente")\n'''
validator = replace_exact(validator, old_spawn_checks, new_spawn_checks)

validator = replace_exact(
    validator,
    '        checks.require("Nearest Walkable Position(Event Player.PosisiRuangMuncul)" in teleport_exec.body, "Spawn teleport non usa una posizione camminabile")',
    '        checks.require("Teleport(Event Player, Position Of(First Of(Spawn Points(Team Of(Event Player)))));" in teleport_exec.body, "Spawn teleport non usa direttamente Spawn Points")\n        checks.require("PosisiRuangMuncul" not in teleport_exec.body and "PunyaPosisiMuncul" not in teleport_exec.body, "Spawn teleport usa ancora cache/registrazione")',
)
VALIDATOR.write_text(validator, encoding="utf-8")

readme = README.read_text(encoding="utf-8")
readme = replace_exact(
    readme,
    "- cache Spawn Room a **1 Hz**;",
    "- Spawn Room Teleport diretto via `Spawn Points(Team Of(Event Player))`, senza cache o `Wait`;",
)
readme = readme.replace(
    "L'overlay Teleport ha **tre pagine fisse**: `Spawn Room`, `Objective / Flag` e `All Players`. Tenendo Crouch, **Secondary Fire** passa alla pagina successiva e **Primary Fire** esegue subito il teleport della pagina attiva.",
    "L'overlay Teleport ha **tre pagine fisse**: `Spawn Room`, `Objective / Flag` e `All Players`. Tenendo Crouch, **Secondary Fire** passa alla pagina successiva e **Primary Fire** esegue subito il teleport della pagina attiva. `Spawn Room` usa direttamente il primo `Spawn Points(Team Of(Event Player))`: non registra coordinate e non usa `Wait`.",
)
README.write_text(readme, encoding="utf-8")

print(f"simplified 0.7.2 spawn teleport: {OLD_BLOB} -> {new_blob}")
