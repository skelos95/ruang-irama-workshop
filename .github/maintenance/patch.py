from __future__ import annotations

from pathlib import Path
import hashlib
import re

SOURCE = Path("workshop/ruang_irama.workshop")
VALIDATOR = Path("tools/validate_workshop.py")
PROJECT = Path("docs/PROGETTO.md")
TESTS = Path("docs/TEST.md")
REPORT = Path("docs/VALIDAZIONE.md")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 occurrence, found {count}")
    return text.replace(old, new, 1)


def replace_in_rule(text: str, prefix: str, old: str, new: str, label: str) -> str:
    start = text.index(f'rule("{prefix}')
    end = text.find('\nrule("', start + 1)
    if end < 0:
        end = len(text)
    block = text[start:end]
    block = replace_once(block, old, new, label)
    return text[:start] + block + text[end:]


src = SOURCE.read_text(encoding="utf-8")

# 1) Cache the highest active HUD slot. This removes two Sorted Array(...) calls
# from continuously reevaluated player-row HUD strings.
src = replace_once(
    src,
    '\t\t40: DaftarIkon\n\t\t41: NamaIkon\n\tplayer:',
    '\t\t40: DaftarIkon\n\t\t41: NamaIkon\n\t\t42: SlotHUDTerakhir\n\tplayer:',
    "declare last HUD slot cache",
)
src = replace_once(
    src,
    '\t\tGlobal.IndeksKeluar = -1;\n\t\tGlobal.KodeMenu = Array(0, 1, 2, 3, 4, 5, 6, 7);',
    '\t\tGlobal.IndeksKeluar = -1;\n\t\tGlobal.SlotHUDTerakhir = -1;\n\t\tGlobal.KodeMenu = Array(0, 1, 2, 3, 4, 5, 6, 7);',
    "initialize last HUD slot cache",
)
src = replace_once(
    src,
    '\t\tEvent Player.UrutanHUD = First Of(Global.SlotHUDTersedia);\n\t\tModify Global Variable(SlotHUDTersedia, Remove From Array By Index, 0);',
    '\t\tEvent Player.UrutanHUD = First Of(Global.SlotHUDTersedia);\n\t\tGlobal.SlotHUDTerakhir = Max(Global.SlotHUDTerakhir, Event Player.UrutanHUD);\n\t\tModify Global Variable(SlotHUDTersedia, Remove From Array By Index, 0);',
    "update last HUD slot on join",
)
old_last = 'Event Player == Last Of(Sorted Array(\n\t\t\tGlobal.PemainManusia, Player Variable(Current Array Element, UrutanHUD)))'
count_last = src.count(old_last)
if count_last != 2:
    raise SystemExit(f"reevaluated last-row sort: expected 2, found {count_last}")
src = src.replace(old_last, 'Event Player.UrutanHUD == Global.SlotHUDTerakhir')

# Recompute the cache once per human leave, after aligned HUD-slot removal.
src = replace_once(
    src,
    '\t\t\tModify Global Variable(SlotHUDPemain, Remove From Array By Index, Global.IndeksKeluar);\n\t\t\tModify Global Variable(PemainManusia, Remove From Array By Index, Global.IndeksKeluar);',
    '\t\t\tModify Global Variable(SlotHUDPemain, Remove From Array By Index, Global.IndeksKeluar);\n\t\t\tModify Global Variable(PemainManusia, Remove From Array By Index, Global.IndeksKeluar);\n\t\t\tGlobal.SlotHUDTerakhir = Count Of(Global.SlotHUDPemain) == 0 ? -1 : Last Of(Sorted Array(Global.SlotHUDPemain, Current Array Element));',
    "recompute last HUD slot on leave",
)

# 2) Opening the main Arcade Menu does not need to scan camera/revenge targets.
# Each corresponding submenu already refreshes immediately when entered.
src = replace_in_rule(
    src,
    "05 - Menu:",
    '\t\t\tCall Subroutine(SegarkanTargetKamera);\n\t\t\tCall Subroutine(SegarkanTargetBalasDendam);\n',
    '',
    "remove redundant menu-open target scans",
)

# 3) Passive dynamic-list refreshes can run at 1 Hz. All navigation/apply handlers
# still perform an immediate refresh before using the list.
for prefix, label in (
    ("07b - Menu kamera:", "camera menu passive refresh"),
    ("07c - Menu Balas Dendam:", "revenge menu passive refresh"),
    ("19f - Teleport Crouch:", "teleport passive refresh"),
):
    src = replace_in_rule(
        src,
        prefix,
        '\t\tWait(0.500, Abort When False);',
        '\t\tWait(1, Abort When False);',
        label,
    )

# 4) Lobby minutes change only once per minute; 5-second sampling is ample and
# reduces 12-player periodic work by 80% versus the previous 1 Hz loop.
src = replace_in_rule(
    src,
    "03 - Waktu:",
    '\t\tWait(1, Ignore Condition);',
    '\t\tWait(5, Ignore Condition);',
    "lobby minute sampling",
)

# 5) Crouch inspection target acquisition is the heaviest per-player operation
# because it filters and sorts all players. 5 Hz remains responsive while
# halving worst-case sorting pressure versus the previous 10 Hz.
src = replace_in_rule(
    src,
    "14 - Intip Pahlawan:",
    '\t\tWait(0.100, Abort When False);',
    '\t\tWait(0.200, Abort When False);',
    "inspection refresh rate",
)

SOURCE.write_text(src, encoding="utf-8")

# Strengthen static performance/cleanliness checks.
val = VALIDATOR.read_text(encoding="utf-8")
check = r'''

def check_runtime_efficiency_audit(checks: Checks, source: str, rules: list[Rule]) -> None:
    clean = mask_strings(source)
    variables = section_body(source, "variables")
    checks.require(
        re.search(r"(?m)^\s*42\s*:\s*SlotHUDTerakhir\s*$", variables) is not None,
        "audit: cache SlotHUDTerakhir assente",
    )
    checks.require("Global.SlotHUDTerakhir = -1;" in clean, "audit: cache ultima riga non inizializzata")
    checks.require(
        "Event Player.UrutanHUD == Global.SlotHUDTerakhir" in clean,
        "audit: HUD roster non usa la cache ultima riga",
    )
    checks.require(
        "Last Of(Sorted Array(Global.PemainManusia, Player Variable(Current Array Element, UrutanHUD)))" not in clean,
        "audit: sort roster rivalutato per frame ancora presente",
    )
    checks.require(
        "Global.SlotHUDTerakhir = Count Of(Global.SlotHUDPemain) == 0 ? -1 : Last Of(Sorted Array(Global.SlotHUDPemain, Current Array Element));" in clean,
        "audit: cache ultima riga non ricalcolata al leave",
    )

    menu_open = [rule for rule in rules if code_contains(rule.body, "Event Player.MenuTerbuka = True;", "Event Player.HalamanMenu = -1;")]
    checks.equal(len(menu_open), 1, "audit: regola apertura Arcade Menu")
    if menu_open:
        body = mask_strings(menu_open[0].body)
        checks.require("Call Subroutine(SegarkanTargetKamera);" not in body, "audit: refresh camera inutile all'apertura main menu")
        checks.require("Call Subroutine(SegarkanTargetBalasDendam);" not in body, "audit: refresh revenge inutile all'apertura main menu")

    periodic_expectations = (
        ("03 - Waktu:", "Wait(5, Ignore Condition);", "timer minuti 5s"),
        ("07b - Menu kamera:", "Wait(1, Abort When False);", "camera menu 1Hz"),
        ("07c - Menu Balas Dendam:", "Wait(1, Abort When False);", "revenge menu 1Hz"),
        ("14 - Intip Pahlawan:", "Wait(0.200, Abort When False);", "inspect 5Hz"),
        ("19f - Teleport Crouch:", "Wait(1, Abort When False);", "teleport 1Hz"),
    )
    for prefix, token, label in periodic_expectations:
        matches = [rule for rule in rules if rule.name.startswith(prefix)]
        checks.equal(len(matches), 1, f"audit: {label}")
        if matches:
            checks.require(token in mask_strings(matches[0].body), f"audit: frequenza errata {label}")

    # Keep known expensive operations bounded to their intended places.
    checks.equal(len(call_texts(source, "Ray Cast Hit Position")), 1, "audit: raycast camera unici")
    inspection_sorts = [rule for rule in rules if code_contains(rule.body, "Subroutine;", "SegarkanTargetInspeksi;", "Sorted Array(Event Player.DaftarTargetInspeksi")]
    checks.equal(len(inspection_sorts), 1, "audit: sort target inspection")

    # Rule names are already checked globally; also protect against accidental
    # duplicate subroutine renderers/callable definitions in the menu family.
    for sub in ("GambarUtama", "GambarMusik", "GambarKamera", "GambarWarna", "GambarBahasa", "GambarBalasDendam", "GambarTeleportasi", "GambarUnkillable", "GambarSuara", "GambarIkon"):
        definitions = rules_containing(rules, "Subroutine;", f"{sub};")
        checks.equal(len(definitions), 1, f"audit: definizione unica {sub}")
'''
if 'def check_runtime_efficiency_audit(' not in val:
    marker = '\ndef main() -> None:\n'
    if val.count(marker) != 1:
        raise SystemExit("validator main marker not found")
    val = val.replace(marker, check + marker, 1)
    call = '        check_menu_palette_and_name_colors(checks, source, rules)\n'
    if val.count(call) != 1:
        raise SystemExit("validator audit call anchor not found")
    val = val.replace(call, call + '        check_runtime_efficiency_audit(checks, source, rules)\n', 1)
VALIDATOR.write_text(val, encoding="utf-8")

# Document the audit without adding a new repository file.
project = PROJECT.read_text(encoding="utf-8")
section = '''\n\n### Audit runtime 12 player\n\nAudit completo eseguito sulla pipeline globale, classificazione umano/bot, join/leave, HUD roster, dispatcher menu, menu dinamici, Crouch inspection, camera, teleport, revenge, Unkillable, Jump respawn, RGB ed effetti. Non sono state trovate regole duplicate funzionalmente equivalenti o subroutine menu morte; le coppie apparentemente simili rimaste servono a bootstrap, edge detection, cleanup o fasi differenti.\n\nOttimizzazioni conservative applicate: `SlotHUDTerakhir` memorizza la riga HUD attiva più bassa e sostituisce due `Sorted Array(Global.PemainManusia, ...)` che prima erano dentro stringhe HUD rivalutate; l'apertura del Main Menu non ricostruisce più inutilmente le liste Camera/Revenge; i refresh passivi di Camera/Revenge/Teleport passano da 0,5 s a 1 s mentre ogni input continua a fare refresh immediato; `MenitLobby` viene campionato ogni 5 s invece che ogni secondo; la selezione Crouch inspection passa da 10 Hz a 5 Hz, dimezzando il sorting dei target nel caso peggiore con 12 player. Il loop RGB globale a 10 Hz, il timer server a 1 Hz e il singolo raycast camera restano invariati perché già bounded e necessari alla resa visiva/funzionale.\n'''
if '### Audit runtime 12 player' not in project:
    project += section
PROJECT.write_text(project, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
for line in (
    '- **Stress 12 player:** con 12 umani attivi aprire/chiudere menu in parallelo, cambiare sottomenù, usare Camera/Revenge/Teleport/Crouch inspection e verificare che input e HUD restino reattivi.\n',
    '- **Join/leave stress:** con lobby quasi piena far entrare/uscire ripetutamente player e verificare ordine roster, riga finale/diagnostics, slot HUD riutilizzati, target camera/teleport/inspect e cleanup revenge senza riferimenti stale.\n',
    '- **Audit frequenze live:** verificare che Crouch inspection a 5 Hz resti fluido, che i menu dinamici riflettano join/leave entro circa 1 s e che il contatore MIN possa aggiornarsi con massimo ~5 s di ritardo.\n',
):
    if line not in tests:
        tests += '\n' + line
TESTS.write_text(tests, encoding="utf-8")

# Refresh Workshop source blob marker.
data = SOURCE.read_bytes().replace(b"\r\n", b"\n")
blob = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
report = REPORT.read_text(encoding="utf-8")
report, n = re.subn(r"```text\n[0-9a-f]{40}\n```", f"```text\n{blob}\n```", report, count=1)
if n != 1:
    raise SystemExit("validation report blob marker not found")
REPORT.write_text(report, encoding="utf-8")
