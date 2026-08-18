from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
README = ROOT / "README.md"
PROJECT = ROOT / "docs" / "PROGETTO.md"

OLD_BLOB = "d75a81dd7cf5297b2a326b12a78fd7311592238f"


def git_blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def replace_exact(text: str, old: str, new: str, expected: int = 1) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"replacement mismatch: expected {expected}, found {count}: {old[:160]!r}")
    return text.replace(old, new)


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
        raise RuntimeError(f"rule was not changed: {title}")
    return text[:start] + edited + text[end:]


source = SOURCE.read_text(encoding="utf-8")
if git_blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch a moving target")

# Keep the last selected Teleport page between Crouch sessions.
def keep_page_on_open(block: str) -> str:
    return replace_exact(block, "\t\tEvent Player.KursorTeleportasi = 0;\n", "")

source = edit_rule(source, "19 - Teleportasi Jongkok: Buka tiga halaman selama Jongkok ditahan", keep_page_on_open)

# When page 3 starts, initialize the visible inspection target from the same privacy-filtered
# closest-to-reticle source used by the Teleport itself, instead of the generic inspection list.
def align_initial_target(block: str) -> str:
    old = "\t\tCall Subroutine(SegarkanTargetInspeksi);\n"
    new = '''\t\tIf(And(Event Player.TeleportasiJongkokAktif == True, Event Player.KursorTeleportasi == 2));\n\t\t\tCall Subroutine(SegarkanTargetTeleportasi);\n\t\t\tEvent Player.TargetInspeksi = Event Player.CalonTargetTeleportasi;\n\t\tElse;\n\t\t\tCall Subroutine(SegarkanTargetInspeksi);\n\t\tEnd;\n'''
    return replace_exact(block, old, new)

source = edit_rule(source, "13 - Intip Pahlawan: Tampilkan ikon, nama, dan kesehatan saat ini", align_initial_target)

# Closing Crouch must preserve the page but immediately clean the inspection/nameplate state.
def close_without_reset(block: str) -> str:
    block = replace_exact(block, "\t\tEvent Player.KursorTeleportasi = 0;\n", "")
    old = '''\t\tEvent Player.TargetTeleportasiTerkunci = Null;\n\t\tAllow Button(Event Player, Button(Primary Fire));'''
    new = '''\t\tEvent Player.TargetTeleportasiTerkunci = Null;\n\t\tIf(Event Player.PelatNamaDinonaktifkan == True);\n\t\t\tEnable Nameplates(All Players(All Teams), Event Player);\n\t\t\tEvent Player.PelatNamaDinonaktifkan = False;\n\t\tEnd;\n\t\tIf(Event Player.TeksDunia != Null);\n\t\t\tDestroy In-World Text(Event Player.TeksDunia);\n\t\tEnd;\n\t\tIf(Event Player.TeksDiri != Null);\n\t\t\tDestroy In-World Text(Event Player.TeksDiri);\n\t\tEnd;\n\t\tIf(Index Of Array Value(Global.PemainManusia, Event Player) >= 0);\n\t\t\tGlobal.TeksDuniaPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = 0;\n\t\t\tGlobal.TeksDiriPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = 0;\n\t\tEnd;\n\t\tEvent Player.TeksDunia = Null;\n\t\tEvent Player.TeksDiri = Null;\n\t\tEvent Player.TargetInspeksi = Null;\n\t\tEvent Player.DaftarTargetInspeksi = Empty Array;\n\t\tEvent Player.InspeksiAktif = False;\n\t\tAllow Button(Event Player, Button(Primary Fire));'''
    return replace_exact(block, old, new)

source = edit_rule(source, "19g - Teleportasi Jongkok: Tutup saat Jongkok dilepas", close_without_reset)

SOURCE.write_text(source, encoding="utf-8")
new_blob = git_blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_exact(validator, f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"', f'EXPECTED_SOURCE_BLOB = "{new_blob}"')
anchor = '    interact = find_rule(rules, "10 - Menu:")\n'
guards = '''    teleport_open = find_rule(rules, "19 - Teleportasi Jongkok:")\n    teleport_close = find_rule(rules, "19g - Teleportasi Jongkok:")\n    inspect_rule = find_rule(rules, "13 - Intip Pahlawan:")\n    checks.equal(source.count("Event Player.KursorTeleportasi = 0;"), 1, "reset KursorTeleportasi deve restare solo in SiapkanPemain")\n    if teleport_open:\n        checks.require("Event Player.KursorTeleportasi = 0;" not in teleport_open.body, "apertura Teleport resetta ancora la pagina")\n    if teleport_close:\n        checks.require("Event Player.KursorTeleportasi = 0;" not in teleport_close.body, "chiusura Teleport resetta ancora la pagina")\n        checks.require("Destroy In-World Text(Event Player.TeksDunia);" in teleport_close.body, "chiusura Teleport non distrugge subito il nome inspection")\n        checks.require("Event Player.InspeksiAktif = False;" in teleport_close.body, "chiusura Teleport non resetta subito Inspection")\n    if inspect_rule:\n        checks.require("Call Subroutine(SegarkanTargetTeleportasi);" in inspect_rule.body, "pagina player Teleport non inizializza il target dal reticolo")\n        checks.require("Event Player.TargetInspeksi = Event Player.CalonTargetTeleportasi;" in inspect_rule.body, "nome inspection non è allineato al target Teleport")\n'''
validator = replace_exact(validator, anchor, guards + anchor)
VALIDATOR.write_text(validator, encoding="utf-8")

readme = README.read_text(encoding="utf-8")
readme += '''\n\n### Hotfix Teleport 0.7.2 — pagina persistente\n\nLa pagina Crouch Teleport resta memorizzata tra un rilascio di Crouch e il successivo: se si chiude sulla pagina `All Players`, la riapertura torna direttamente lì. La chiusura rimuove immediatamente il testo Inspection e ripristina le nameplate, evitando nomi residui; sulla pagina player il primo target visualizzato viene inizializzato dalla stessa sorgente privacy-filtered closest-to-reticle usata dal Teleport.\n'''
README.write_text(readme, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
project += '''\n\n### Hotfix 0.7.2 — persistenza pagina Teleport e cleanup Inspection\n\n`KursorTeleportasi` viene inizializzato a 0 solo in `SiapkanPemain` e non viene più azzerato all'apertura/chiusura dell'overlay. `19g` esegue cleanup immediato di nameplate, `TeksDunia/TeksDiri`, `TargetInspeksi` e `InspeksiAktif`. Quando Crouch parte direttamente sulla pagina 3, la regola Inspection usa prima `SegarkanTargetTeleportasi` e allinea `TargetInspeksi = CalonTargetTeleportasi`, evitando un target generico/stale nel primo frame.\n'''
PROJECT.write_text(project, encoding="utf-8")

print(f"hotfixed 0.7.2 teleport persistence: {OLD_BLOB} -> {new_blob}")
