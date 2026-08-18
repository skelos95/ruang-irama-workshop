from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
TESTS = ROOT / "tests" / "test_validate_workshop.py"
README = ROOT / "README.md"
PROJECT = ROOT / "docs" / "PROGETTO.md"

OLD_BLOB = "49a8d2d9c07680061b9d8d76931a1723fdf2ec01"


def git_blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def replace_exact(text: str, old: str, new: str, expected: int = 1) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"replacement mismatch: expected {expected}, found {count}: {old[:180]!r}")
    return text.replace(old, new)


source = SOURCE.read_text(encoding="utf-8")
if git_blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch a moving target")

# Prevent the generic Inspection rule from winning the first Crouch frame when
# Crouch Teleport is enabled. Page 3 has its own dedicated world-label rule.
source = replace_exact(
    source,
    "\t\tEvent Player.TeleportasiJongkokAktif == False;\n\t\tEvent Player.ModeKamera != 2;",
    "\t\tEvent Player.TeleportasiJongkokAktif == False;\n\t\tEvent Player.TeleportasiJongkokDiaktifkan == False;\n\t\tEvent Player.ModeKamera != 2;",
)

# Global 4 Hz target filter: dummy bots do not need Has Spawned or player privacy vars.
old_global = '''\t\t\t\tSet Player Variable(Global.PemainAktif, DaftarTargetTeleportasi, Filtered Array(All Players(All Teams), And(Current Array Element != Global.PemainAktif,\n\t\t\t\t\tAnd(Entity Exists(Current Array Element), And(Has Spawned(Current Array Element), And(Is Alive(Current Array Element),\n\t\t\t\t\tOr(Is Dummy Bot(Current Array Element) == True, Or(Player Variable(Current Array Element, BotOtomatis) == True,\n\t\t\t\t\tAnd(Player Variable(Current Array Element, Manusia) == True, Player Variable(Current Array Element, PrivasiInspeksiAktif) == False)))))))));'''
new_global = '''\t\t\t\tSet Player Variable(Global.PemainAktif, DaftarTargetTeleportasi, Filtered Array(All Players(All Teams), And(Current Array Element != Global.PemainAktif,\n\t\t\t\t\tAnd(Entity Exists(Current Array Element), And(Is Alive(Current Array Element), Or(Is Dummy Bot(Current Array Element) == True,\n\t\t\t\t\tAnd(Player Variable(Current Array Element, Manusia) == True, Player Variable(Current Array Element, PrivasiInspeksiAktif) == False)))))));'''
source = replace_exact(source, old_global, new_global)

# Immediate refresh used on Primary Fire and when page 3 opens: same eligibility.
old_refresh = '''\t\tEvent Player.DaftarTargetTeleportasi = Filtered Array(All Players(All Teams), And(Current Array Element != Event Player,\n\t\t\tAnd(Entity Exists(Current Array Element), And(Has Spawned(Current Array Element), And(Is Alive(Current Array Element),\n\t\t\tOr(Is Dummy Bot(Current Array Element) == True, Or(Player Variable(Current Array Element, BotOtomatis) == True,\n\t\t\tAnd(Player Variable(Current Array Element, Manusia) == True, Player Variable(Current Array Element, PrivasiInspeksiAktif) == False))))))));'''
new_refresh = '''\t\tEvent Player.DaftarTargetTeleportasi = Filtered Array(All Players(All Teams), And(Current Array Element != Event Player,\n\t\t\tAnd(Entity Exists(Current Array Element), And(Is Alive(Current Array Element), Or(Is Dummy Bot(Current Array Element) == True,\n\t\t\tAnd(Player Variable(Current Array Element, Manusia) == True, Player Variable(Current Array Element, PrivasiInspeksiAktif) == False))))));'''
source = replace_exact(source, old_refresh, new_refresh)

# When entering page 3, explicitly discard any stale first-frame Inspection handle.
old_enter_page3 = '''\t\tElse;\n\t\t\tCall Subroutine(SegarkanTargetTeleportasi);\n\t\tEnd;'''
new_enter_page3 = '''\t\tElse;\n\t\t\tIf(Event Player.TeksDunia != Null);\n\t\t\t\tDestroy In-World Text(Event Player.TeksDunia);\n\t\t\tEnd;\n\t\t\tIf(Index Of Array Value(Global.PemainManusia, Event Player) >= 0);\n\t\t\t\tGlobal.TeksDuniaPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = 0;\n\t\t\tEnd;\n\t\t\tEvent Player.TeksDunia = Null;\n\t\t\tEvent Player.TargetInspeksi = Null;\n\t\t\tEvent Player.InspeksiAktif = False;\n\t\t\tCall Subroutine(SegarkanTargetTeleportasi);\n\t\tEnd;'''
source = replace_exact(source, old_enter_page3, new_enter_page3)

SOURCE.write_text(source, encoding="utf-8")
new_blob = git_blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_exact(validator, f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"', f'EXPECTED_SOURCE_BLOB = "{new_blob}"')
validator = replace_exact(
    validator,
    '    eligibility = "Or(Is Dummy Bot(Current Array Element) == True, Or(Player Variable(Current Array Element, BotOtomatis) == True"\n    privacy = "And(Player Variable(Current Array Element, Manusia) == True, Player Variable(Current Array Element, PrivasiInspeksiAktif) == False)"\n',
    '    eligibility = "Or(Is Dummy Bot(Current Array Element) == True, And(Player Variable(Current Array Element, Manusia) == True"\n    privacy = "Player Variable(Current Array Element, PrivasiInspeksiAktif) == False"\n',
)
validator = replace_exact(
    validator,
    '        checks.require(eligibility in teleport_refresh.body and privacy in teleport_refresh.body, "Teleport refresh non distingue bot pubblici e umani privacy OFF")\n',
    '        checks.require(eligibility in teleport_refresh.body and privacy in teleport_refresh.body, "Teleport refresh non distingue dummy pubblici e umani privacy OFF")\n        checks.require("Has Spawned(Current Array Element)" not in teleport_refresh.body, "Teleport refresh esclude dummy tramite Has Spawned")\n',
)
validator = replace_exact(
    validator,
    '        checks.require(eligibility in teleport_global.body and privacy in teleport_global.body, "Teleport globale non distingue bot pubblici e umani privacy OFF")\n',
    '        checks.require(eligibility in teleport_global.body and privacy in teleport_global.body, "Teleport globale non distingue dummy pubblici e umani privacy OFF")\n',
)
validator = replace_exact(
    validator,
    '        checks.require("Event Player.TeleportasiJongkokAktif == False;" in inspect_rule.body, "Inspection generica entra ancora nel Teleport")\n',
    '        checks.require("Event Player.TeleportasiJongkokAktif == False;" in inspect_rule.body, "Inspection generica entra ancora nel Teleport")\n        checks.require("Event Player.TeleportasiJongkokDiaktifkan == False;" in inspect_rule.body, "Inspection generica può vincere il primo frame Crouch")\n',
)
validator = replace_exact(
    validator,
    '        checks.require("Destroy In-World Text(Event Player.TeksDunia);" in teleport_cycle.body, "uscita pagina 3 non rimuove il target world text")\n',
    '        checks.require(teleport_cycle.body.count("Destroy In-World Text(Event Player.TeksDunia);") >= 2, "cambio pagina non ripulisce handle Inspection/Teleport")\n',
)
VALIDATOR.write_text(validator, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
anchor = "    def test_teleport_privacy_filter_is_required(self) -> None:\n"
extra = '''    def test_generic_inspection_cannot_race_crouch_teleport(self) -> None:\n        start = self.source.index('rule("13 - Intip Pahlawan:')\n        pos = self.source.index("Event Player.TeleportasiJongkokDiaktifkan == False;", start)\n        mutated = self.source[:pos] + self.source[pos:].replace("Event Player.TeleportasiJongkokDiaktifkan == False;", "Event Player.TeleportasiJongkokDiaktifkan == True;", 1)\n        self.assertTrue(any("primo frame Crouch" in error for error in self.errors(mutated)))\n\n    def test_dummy_teleport_filter_does_not_require_has_spawned(self) -> None:\n        start = self.source.index('rule("98 - Subrutin:')\n        insert = self.source.index("Is Alive(Current Array Element)", start)\n        mutated = self.source[:insert] + "Has Spawned(Current Array Element), " + self.source[insert:]\n        self.assertTrue(any("Has Spawned" in error for error in self.errors(mutated)))\n\n'''
tests = replace_exact(tests, anchor, extra + anchor)
TESTS.write_text(tests, encoding="utf-8")

readme = README.read_text(encoding="utf-8")
readme += '''\n\n### Hotfix Crouch 0.7.2 — first-frame race\n\nQuando Crouch Teleport è abilitato, l'Inspection generica non può più partire nel primo frame di Crouch: il world text della pagina 3 appartiene esclusivamente a `19d`. Il filtro player della pagina 3 non usa più `Has Spawned` sui dummy: target validi sono dummy bot vivi oppure player umani vivi con privacy OFF. Entrando nella pagina 3 viene inoltre eliminato qualunque handle Inspection residuo prima del refresh del closest-to-reticle.\n'''
README.write_text(readme, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
project += '''\n\n### Hotfix 0.7.2 — race Crouch e dummy target\n\nLa regola 13 richiede ora `TeleportasiJongkokDiaktifkan == False`, eliminando la race con la regola 19 sul primo frame del tasto Crouch. I filtri `04k` e `98` accettano dummy bot vivi senza dipendere da `Has Spawned` o dalle variabili privacy; per gli umani resta obbligatorio `Manusia == True && PrivasiInspeksiAktif == False`. Il passaggio alla pagina 3 pulisce esplicitamente eventuali `TeksDunia/TargetInspeksi` residui.\n'''
PROJECT.write_text(project, encoding="utf-8")

print(f"hotfixed 0.7.2 crouch race/dummy target: {OLD_BLOB} -> {new_blob}")
