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


def replace_check_by_label(text: str, label: str, replacement: str) -> str:
    label_at = text.find(label)
    if label_at < 0:
        raise SystemExit(f"validator label not found: {label}")
    start = text.rfind("    checks.require(", 0, label_at)
    if start < 0:
        raise SystemExit(f"checks.require start not found: {label}")
    opening = text.find("(", start)
    depth = 1
    quote: str | None = None
    escaped = False
    closing = -1
    for i in range(opening + 1, len(text)):
        ch = text[i]
        if quote is not None:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            continue
        if ch in ('"', "'"):
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                closing = i + 1
                break
    if closing < 0 or not (start < label_at < closing):
        raise SystemExit(f"checks.require block not resolved: {label}")
    return text[:start] + replacement + text[closing:]


src = SOURCE.read_text(encoding="utf-8")

# Cache the highest occupied roster slot. This replaces two Sorted Array calls
# that were previously embedded in continuously reevaluated HUD expressions.
src = replace_once(
    src,
    '\t\t40: DaftarIkon\n\t\t41: NamaIkon\n\tplayer:',
    '\t\t40: DaftarIkon\n\t\t41: NamaIkon\n\t\t42: SlotHUDTerakhir\n\tplayer:',
    "declare SlotHUDTerakhir",
)
src = replace_once(
    src,
    '\t\tGlobal.IndeksKeluar = -1;\n\t\tGlobal.KodeMenu = Array(0, 1, 2, 3, 4, 5, 6, 7);',
    '\t\tGlobal.IndeksKeluar = -1;\n\t\tGlobal.SlotHUDTerakhir = -1;\n\t\tGlobal.KodeMenu = Array(0, 1, 2, 3, 4, 5, 6, 7);',
    "initialize SlotHUDTerakhir",
)
src = replace_once(
    src,
    '\t\tEvent Player.UrutanHUD = First Of(Global.SlotHUDTersedia);\n\t\tModify Global Variable(SlotHUDTersedia, Remove From Array By Index, 0);',
    '\t\tEvent Player.UrutanHUD = First Of(Global.SlotHUDTersedia);\n\t\tGlobal.SlotHUDTerakhir = Max(Global.SlotHUDTerakhir, Event Player.UrutanHUD);\n\t\tModify Global Variable(SlotHUDTersedia, Remove From Array By Index, 0);',
    "update SlotHUDTerakhir on join",
)
old_last = 'Event Player == Last Of(Sorted Array(\n\t\t\tGlobal.PemainManusia, Player Variable(Current Array Element, UrutanHUD)))'
if src.count(old_last) != 2:
    raise SystemExit(f"last-row Sorted Array: expected 2, found {src.count(old_last)}")
src = src.replace(old_last, 'Event Player.UrutanHUD == Global.SlotHUDTerakhir')
src = replace_once(
    src,
    '\t\t\tModify Global Variable(SlotHUDPemain, Remove From Array By Index, Global.IndeksKeluar);\n\t\t\tModify Global Variable(PemainManusia, Remove From Array By Index, Global.IndeksKeluar);',
    '\t\t\tModify Global Variable(SlotHUDPemain, Remove From Array By Index, Global.IndeksKeluar);\n\t\t\tModify Global Variable(PemainManusia, Remove From Array By Index, Global.IndeksKeluar);\n\t\t\tGlobal.SlotHUDTerakhir = Count Of(Global.SlotHUDPemain) == 0 ? -1 : Last Of(Sorted Array(Global.SlotHUDPemain, Current Array Element));',
    "recompute SlotHUDTerakhir on leave",
)

# Main menu opening does not need Camera/Revenge scans; submenu entry does an
# immediate refresh before rendering/using those lists.
src = replace_in_rule(
    src,
    "05 - Menu:",
    '\t\t\tCall Subroutine(SegarkanTargetKamera);\n\t\t\tCall Subroutine(SegarkanTargetBalasDendam);\n',
    '',
    "remove redundant main-menu scans",
)

# Passive list refreshes are safety nets for live join/leave. Inputs themselves
# still refresh immediately, so 1 Hz is sufficient and cuts idle scans in half.
for prefix, label in (
    ("07b - Menu kamera:", "camera passive refresh"),
    ("07c - Menu Balas Dendam:", "revenge passive refresh"),
    ("19f - Teleport Crouch:", "teleport passive refresh"),
):
    src = replace_in_rule(src, prefix, '\t\tWait(0.500, Abort When False);', '\t\tWait(1, Abort When False);', label)

# Lobby minutes only change once per minute. Five-second sampling preserves the
# display while reducing the 12-player periodic workload by about 80%.
src = replace_in_rule(src, "03 - Waktu:", '\t\tWait(1, Ignore Condition);', '\t\tWait(5, Ignore Condition);', "lobby minute sampling")

# Spawn-room return point is saved immediately, then refreshed at 1 Hz instead
# of being rewritten every evaluation frame while a player remains in spawn.
src = replace_in_rule(
    src,
    "02c - Ruang Muncul:",
    '\t\tEvent Player.PunyaPosisiMuncul = True;\n',
    '\t\tEvent Player.PunyaPosisiMuncul = True;\n\t\tWait(1, Abort When False);\n\t\tLoop If Condition Is True;\n',
    "spawn room cache frequency",
)

# Crouch target acquisition filters + sorts the player set; 5 Hz stays visually
# responsive and halves worst-case sorting pressure versus 10 Hz.
src = replace_in_rule(src, "14 - Intip Pahlawan:", '\t\tWait(0.100, Abort When False);', '\t\tWait(0.200, Abort When False);', "inspection 5Hz")
SOURCE.write_text(src, encoding="utf-8")

val = VALIDATOR.read_text(encoding="utf-8")

# Replace two old expectations whose exact pre-audit implementation changed.
val = replace_check_by_label(
    val,
    "refresh Crouch non a 0,10 s",
    '''    checks.require(\n        "Wait(0.200, Abort When False);" in source,\n        "refresh Crouch non a 0,20 s",\n    )''',
)
val = replace_check_by_label(
    val,
    "diagnostica non ancorata all'ultimo player della lista sinistra",
    '''    checks.require(\n        "Event Player.UrutanHUD == Global.SlotHUDTerakhir" in source,\n        "diagnostica non ancorata alla cache dell'ultimo player della lista sinistra",\n    )''',
)

audit_check = r'''

def check_runtime_efficiency_audit(checks: Checks, source: str, rules: list[Rule]) -> None:
    clean = mask_strings(source)
    variables = section_body(source, "variables")
    checks.require(re.search(r"(?m)^\s*42\s*:\s*SlotHUDTerakhir\s*$", variables) is not None, "audit: SlotHUDTerakhir assente")
    checks.require("Global.SlotHUDTerakhir = -1;" in clean, "audit: cache ultima riga non inizializzata")
    checks.require("Global.SlotHUDTerakhir = Max(Global.SlotHUDTerakhir, Event Player.UrutanHUD);" in clean, "audit: cache ultima riga non aggiornata al join")
    checks.require("Event Player.UrutanHUD == Global.SlotHUDTerakhir" in clean, "audit: roster non usa cache ultima riga")
    checks.require("Last Of(Sorted Array(Global.PemainManusia, Player Variable(Current Array Element, UrutanHUD)))" not in clean, "audit: sort roster rivalutato ancora presente")
    checks.require("Global.SlotHUDTerakhir = Count Of(Global.SlotHUDPemain) == 0 ? -1 : Last Of(Sorted Array(Global.SlotHUDPemain, Current Array Element));" in clean, "audit: cache ultima riga non ricalcolata al leave")

    menu_open = [rule for rule in rules if code_contains(rule.body, "Event Player.MenuTerbuka = True;", "Event Player.HalamanMenu = -1;")]
    checks.equal(len(menu_open), 1, "audit: apertura Arcade Menu")
    if menu_open:
        body = mask_strings(menu_open[0].body)
        checks.require("Call Subroutine(SegarkanTargetKamera);" not in body, "audit: refresh camera inutile nel main menu")
        checks.require("Call Subroutine(SegarkanTargetBalasDendam);" not in body, "audit: refresh revenge inutile nel main menu")

    expected = (
        ("02c - Ruang Muncul:", "Wait(1, Abort When False);", "spawn cache 1Hz"),
        ("03 - Waktu:", "Wait(5, Ignore Condition);", "minuti 0,2Hz"),
        ("07b - Menu kamera:", "Wait(1, Abort When False);", "camera passive 1Hz"),
        ("07c - Menu Balas Dendam:", "Wait(1, Abort When False);", "revenge passive 1Hz"),
        ("14 - Intip Pahlawan:", "Wait(0.200, Abort When False);", "inspection 5Hz"),
        ("19f - Teleport Crouch:", "Wait(1, Abort When False);", "teleport passive 1Hz"),
    )
    for prefix, token, label in expected:
        matches = [rule for rule in rules if rule.name.startswith(prefix)]
        checks.equal(len(matches), 1, f"audit: {label}")
        if matches:
            body = mask_strings(matches[0].body)
            checks.require(token in body, f"audit: frequenza errata {label}")
            if prefix.startswith("02c"):
                checks.require("Loop If Condition Is True;" in body, "audit: spawn cache senza loop bounded")

    checks.equal(len(call_texts(source, "Ray Cast Hit Position")), 1, "audit: raycast camera")
    inspection_sorts = [rule for rule in rules if code_contains(rule.body, "Subroutine;", "SegarkanTargetInspeksi;", "Sorted Array(Event Player.DaftarTargetInspeksi")]
    checks.equal(len(inspection_sorts), 1, "audit: sort inspection")

    for sub in ("GambarUtama", "GambarMusik", "GambarKamera", "GambarWarna", "GambarBahasa", "GambarBalasDendam", "GambarTeleportasi", "GambarUnkillable", "GambarSuara", "GambarIkon"):
        checks.equal(len(rules_containing(rules, "Subroutine;", f"{sub};")), 1, f"audit: definizione unica {sub}")
'''
if 'def check_runtime_efficiency_audit(' not in val:
    marker = '\ndef main() -> None:\n'
    if val.count(marker) != 1:
        raise SystemExit("validator main marker not found")
    val = val.replace(marker, audit_check + marker, 1)
    call_anchor = '        check_menu_palette_and_name_colors(checks, source, rules)\n'
    if val.count(call_anchor) != 1:
        raise SystemExit("validator audit call anchor not found")
    val = val.replace(call_anchor, call_anchor + '        check_runtime_efficiency_audit(checks, source, rules)\n', 1)
VALIDATOR.write_text(val, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
section = '''\n\n### Audit runtime 12 player\n\nAudit completo eseguito su inizializzazione, classificazione umano/bot, join/leave, HUD roster, dispatcher e renderer menu, Camera, Revenge, Teleport, Crouch inspection, Unkillable, Jump respawn, RGB, timer ed effetti. Non risultano regole funzionalmente duplicate o renderer/subroutine menu morti; le regole simili rimaste coprono bootstrap, edge detection, cleanup o fasi diverse e sono intenzionali.\n\nOttimizzazioni conservative: `SlotHUDTerakhir` sostituisce due sort del roster dentro HUD rivalutati; il Main Menu non scansiona più Camera/Revenge inutilmente; refresh passivi Camera/Revenge/Teleport da 0,5 s a 1 s con refresh immediato conservato sugli input; `MenitLobby` da 1 s a 5 s; posizione Spawn Room salvata subito e poi a 1 Hz invece che continuamente; Crouch inspection da 10 Hz a 5 Hz. Restano invariati il RGB globale a 10 Hz, il timer server a 1 Hz e il singolo raycast camera, già bounded.\n'''
if '### Audit runtime 12 player' not in project:
    project += section
PROJECT.write_text(project, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
for line in (
    '- **Stress 12 player:** con 12 umani attivi aprire/chiudere menu in parallelo, cambiare sottomenu e usare Camera/Revenge/Teleport/Crouch inspection verificando input e HUD reattivi.\n',
    '- **Join/leave stress:** con lobby quasi piena far entrare/uscire ripetutamente player e verificare ordine roster, diagnostics sull’ultima riga, riuso slot HUD e cleanup di Camera/Revenge/Teleport/Inspection.\n',
    '- **Audit frequenze live:** Crouch inspection a 5 Hz deve restare fluido; menu dinamici devono riflettere join/leave entro circa 1 s; MIN può aggiornarsi con massimo ~5 s di ritardo; Spawn Room deve registrare subito la posizione e aggiornarla poi ogni secondo.\n',
):
    if line not in tests:
        tests += '\n' + line
TESTS.write_text(tests, encoding="utf-8")

# Keep the validation report tied to the exact Workshop blob.
data = SOURCE.read_bytes().replace(b"\r\n", b"\n")
blob = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
report = REPORT.read_text(encoding="utf-8")
report, n = re.subn(r"```text\n[0-9a-f]{40}\n```", f"```text\n{blob}\n```", report, count=1)
if n != 1:
    raise SystemExit("docs/VALIDAZIONE.md blob marker not found")
REPORT.write_text(report, encoding="utf-8")
