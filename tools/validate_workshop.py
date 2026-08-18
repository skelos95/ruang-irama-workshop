#!/usr/bin/env python3
"""Static gate for CHILL Dedicated Server 0.7.2 Global-first."""

from __future__ import annotations

import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VERSION = ROOT / "VERSION"
WORKFLOWS = ROOT / ".github" / "workflows"
EXPORTS = ROOT / "exports"

CURRENT_VERSION = "0.7.2"
EXPECTED_SOURCE_BLOB = "2ed0e0eadf56367719d3065493ebd6078c3f7ffc"
ALLOWED_WORKFLOWS = {"validate-workshop.yml", "maintenance-patch.yml"}


@dataclass(frozen=True)
class Rule:
    name: str
    body: str
    start: int


class Checks:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            self.errors.append(message)

    def equal(self, actual: object, expected: object, label: str) -> None:
        if actual != expected:
            self.errors.append(f"{label}: atteso {expected!r}, trovato {actual!r}")

    def finish(self) -> None:
        if not self.errors:
            return
        print(f"ERRORE - {len(self.errors)} controllo/i non superato/i:", file=sys.stderr)
        for message in self.errors:
            print(f"  - {message}", file=sys.stderr)
        raise SystemExit(1)


def git_blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def matching_brace(text: str, opening: int) -> int:
    depth = 1
    in_string = False
    escaped = False
    for i in range(opening + 1, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
    raise ValueError("graffa non chiusa")


def extract_rules(text: str) -> list[Rule]:
    found: list[Rule] = []
    for match in re.finditer(r'^rule\("([^"]+)"\)\s*\{', text, re.MULTILINE):
        opening = text.find("{", match.start())
        closing = matching_brace(text, opening)
        found.append(Rule(match.group(1), text[match.start(): closing + 1], match.start()))
    return found


def event_type(rule: Rule) -> str:
    match = re.search(r"\bevent\s*\{\s*([^;\n]+);", rule.body, re.DOTALL)
    return match.group(1).strip() if match else ""


def find_rule(rules: list[Rule], prefix: str) -> Rule | None:
    return next((rule for rule in rules if rule.name.startswith(prefix)), None)


def declaration_names(text: str) -> tuple[list[str], list[str], list[str]]:
    variables = re.search(r"variables\s*\{(.*?)\}\s*subroutines", text, re.DOTALL)
    subroutines = re.search(r"subroutines\s*\{(.*?)\}\s*rule\(", text, re.DOTALL)
    if not variables or not subroutines:
        raise ValueError("dichiarazioni variables/subroutines assenti")
    global_names: list[str] = []
    player_names: list[str] = []
    section: str | None = None
    for raw in variables.group(1).splitlines():
        line = raw.strip()
        if line == "global:":
            section = "global"
            continue
        if line == "player:":
            section = "player"
            continue
        match = re.match(r"\d+:\s*([A-Za-z0-9_]+)", line)
        if match:
            (global_names if section == "global" else player_names).append(match.group(1))
    sub_names = [m.group(1) for m in re.finditer(r"(?m)^\s*\d+:\s*([A-Za-z0-9_]+)", subroutines.group(1))]
    return global_names, player_names, sub_names


def validate(source: str) -> Checks:
    checks = Checks()
    rules = extract_rules(source)
    globals_, players, subroutines = declaration_names(source)
    checks.equal(VERSION.read_text(encoding="utf-8").strip(), CURRENT_VERSION, "VERSION")
    checks.equal(git_blob_sha(source), EXPECTED_SOURCE_BLOB, "blob sorgente live-confirmato")
    checks.equal({p.name for p in WORKFLOWS.glob("*.yml")}, ALLOWED_WORKFLOWS, "workflow permanenti")
    checks.require(not EXPORTS.exists(), "directory exports temporanea deve essere assente")
    checks.equal(len(rules), len({rule.name for rule in rules}), "titoli regola univoci")
    checks.require(len(rules) >= 75, "numero regole inatteso")
    for name in ("PemainAktif", "IndeksPemainGlobal"):
        checks.require(name in globals_, f"variabile Global-first assente: {name}")
    for name in ("HalamanMenuTujuan", "HalamanSubmenuPramuat", "TargetTeleportasiTeks", "TeksTeleportasi"):
        checks.require(name in players, f"variabile preload menu assente: {name}")
    for name in ("GambarMenu", "GambarHalamanAktif", "PramuatSubmenu"):
        checks.require(name in subroutines, f"subroutine 0.7.0 assente: {name}")
    checks.require("For Global Variable(Global." not in source, "sintassi For Global Variable(Global.*) non valida")
    managers = [r for r in rules if r.name.startswith("04g - Global-first") or r.name.startswith("04h - Global-first")]
    checks.equal(len(managers), 2, "manager Global-first")
    for manager in managers:
        checks.equal(event_type(manager), "Ongoing - Global", f"{manager.name}: evento")
        checks.require("For Global Variable(IndeksPemainGlobal" in manager.body, f"{manager.name}: loop player globale assente")
        checks.require("Global.PemainAktif = All Players(All Teams)" in manager.body, f"{manager.name}: contesto player assente")
    each_player_pipelines = (
        "05b - Menu:", "05c - Menu:", "05d - Menu:", "06 - Menu:", "07 - Menu:", "08 - Menu 0:", "09 - Menu 0:",
        "10 - Menu:", "11 - Menu:", "12c - Kamera:", "12d - Kamera:",
        "19 - Teleportasi Jongkok:", "19a - Teleportasi Jongkok:", "19b - Teleportasi Jongkok:",
        "19c - Teleportasi Jongkok:", "19d0 - Teleportasi Jongkok:", "19d - Teleportasi Jongkok:", "19e - Teleportasi Jongkok:",
        "19g - Teleportasi Jongkok:",
    )
    for prefix in each_player_pipelines:
        rule = find_rule(rules, prefix)
        checks.require(rule is not None, f"pipeline assente: {prefix}")
        if rule:
            checks.equal(event_type(rule), "Ongoing - Each Player", f"{prefix}: scheduler")
    periodic_global = ("04i - Global-first:", "04j - Global-first:")
    for prefix in periodic_global:
        rule = find_rule(rules, prefix)
        checks.require(rule is not None, f"scheduler globale periodico assente: {prefix}")
        if rule:
            checks.equal(event_type(rule), "Ongoing - Global", f"{prefix}: scheduler")
            checks.require("For Global Variable(IndeksPemainGlobal" in rule.body, f"{prefix}: loop globale assente")
            checks.require("Global.PemainAktif = Global.PemainManusia[Global.IndeksPemainGlobal]" in rule.body, f"{prefix}: contesto umano globale assente")
    for prefix in ("02c - Ruang Muncul:", "03 - Waktu:", "07b - Menu kamera:", "07c - Menu Balas Dendam:",
                   "14 - Intip Pahlawan:", "16 - Kamera:", "19f - Teleportasi Jongkok:"):
        checks.require(find_rule(rules, prefix) is None, f"poller per-player legacy ancora presente: {prefix}")
    checks.require("Global.PemainAktif.InteraksiKameraDipakai = False;" not in source, "release Camera non deve essere nel manager globale")
    checks.require(
        "Global.PemainAktif.PerintahTeleportasi = 1;" not in source
        and "Global.PemainAktif.PerintahTeleportasi = 2;" not in source
        and "Global.PemainAktif.PerintahTeleportasi = 3;" not in source,
        "dispatcher Teleport non deve essere nel manager globale",
    )
    teleport_cycle = find_rule(rules, "19c - Teleportasi Jongkok:")
    teleport_detector = find_rule(rules, "19d0 - Teleportasi Jongkok:")
    teleport_label = find_rule(rules, "19d - Teleportasi Jongkok:")
    teleport_exec = find_rule(rules, "19e - Teleportasi Jongkok:")
    teleport_refresh = find_rule(rules, "98 - Subrutin:")
    teleport_render = find_rule(rules, "91g - Subrutin:")
    teleport_global = find_rule(rules, "04k - Global-first:")
    checks.require(teleport_global is None, "04k polling Inspection/Teleport deve essere rimosso")
    teleport_open = find_rule(rules, "19 - Teleportasi Jongkok:")
    teleport_close = find_rule(rules, "19g - Teleportasi Jongkok:")
    inspect_rule = find_rule(rules, "13 - Intip Pahlawan:")
    checks.require("Event Player.PerintahTeleportasi = 3;" not in source, "Teleport usa ancora il terzo comando legacy")
    checks.equal(source.count("Event Player.KursorTeleportasi = 0;"), 1, "reset KursorTeleportasi deve restare solo in SiapkanPemain")
    checks.require((chr(92) + chr(10)) not in source, "HUD/menu contiene ancora backslash visuali a fine riga")
    if teleport_cycle:
        checks.require("Event Player.KursorTeleportasi = (Event Player.KursorTeleportasi + 1) % 3;" in teleport_cycle.body, "Teleport non cicla tre pagine con Secondary")
        checks.require("Destroy In-World Text(Event Player.TeksTeleportasi);" in teleport_cycle.body, "uscita pagina 3 non rimuove il target world text dedicato")
    if teleport_detector:
        checks.equal(event_type(teleport_detector), "Ongoing - Each Player", "19d0 Teleport detector: scheduler")
        checks.require("Event Player.CalonTargetTeleportasi != First Of(Sorted Array(Filtered Array(All Players(All Teams)" in teleport_detector.body, "19d0 non rileva direttamente il cambio closest-to-reticle")
        checks.require("Call Subroutine(SegarkanTargetTeleportasi);" in teleport_detector.body, "19d0 non aggiorna il candidate Teleport")
        checks.require("Wait(" not in teleport_detector.body and "Loop If Condition Is True;" not in teleport_detector.body, "19d0 non deve usare Wait o Loop")
    if teleport_label:
        checks.equal(event_type(teleport_label), "Ongoing - Each Player", "19d Teleport target label: scheduler")
        checks.require("Event Player.TeleportasiJongkokAktif == True;" in teleport_label.body and "Event Player.KursorTeleportasi == 2;" in teleport_label.body, "19d non è limitata alla pagina 3")
        checks.require("Event Player.TargetTeleportasiTeks != Event Player.CalonTargetTeleportasi;" in teleport_label.body, "19d non rivaluta il target live")
        checks.require("Destroy In-World Text(Event Player.TeksTeleportasi);" in teleport_label.body and "Create In-World Text(" in teleport_label.body, "19d non distrugge e ricrea il nome")
        checks.require("Event Player.TeksTeleportasi = Last Text ID;" in teleport_label.body, "19d non salva il world text nell handle dedicato")
        checks.require(teleport_label.body.index("Event Player.TeksTeleportasi = Last Text ID;") < teleport_label.body.index("Event Player.TargetTeleportasiTeks = Event Player.CalonTargetTeleportasi;"), "19d aggiorna lo snapshot prima di creare il testo")
        checks.require("Wait(" not in teleport_label.body and "Loop If Condition Is True;" not in teleport_label.body, "19d non deve usare Wait o Loop")
        checks.require("Event Player.TeksDunia" not in teleport_label.body, "19d condivide ancora l handle TeksDunia con Inspection")
    if teleport_exec:
        checks.require("Call Subroutine(SegarkanTargetTeleportasi);" in teleport_exec.body, "Primary Teleport non aggiorna il target al click")
        checks.require("TargetTeleportasiTerkunci = Event Player.CalonTargetTeleportasi;" in teleport_exec.body, "Primary Teleport non blocca il closest-to-reticle")
    dummy_eligibility = "Is Dummy Bot(Current Array Element) == True"
    bot_eligibility = "Player Variable(Current Array Element, BotOtomatis) == True"
    privacy = "Player Variable(Current Array Element, PrivasiInspeksiAktif) == False"
    if teleport_refresh:
        checks.require("First Of(Sorted Array(Event Player.DaftarTargetTeleportasi" in teleport_refresh.body, "Teleport non usa closest-to-reticle")
        checks.require(dummy_eligibility in teleport_refresh.body and bot_eligibility in teleport_refresh.body and privacy in teleport_refresh.body, "Teleport refresh: bot pubblici (dummy/automatici) e player privacy OFF richiesti")
        checks.require("Player Variable(Current Array Element, Manusia) == True" not in teleport_refresh.body, "Teleport refresh dipende ancora dal classificatore Manusia")
        checks.require("Has Spawned(Current Array Element)" not in teleport_refresh.body, "Teleport refresh esclude dummy tramite Has Spawned")
    if teleport_render:
        checks.require("Event Player.KursorTeleportasi %= 3;" in teleport_render.body and "ALL PLAYERS" in teleport_render.body, "HUD Teleport non espone tre pagine")
    if teleport_open:
        checks.require("Event Player.KursorTeleportasi = 0;" not in teleport_open.body, "apertura Teleport resetta ancora la pagina")
        checks.require("Event Player.MenuTerbuka == False;" in teleport_open.body, "Crouch Teleport deve restare disattivato mentre il Menu Arcade è aperto")
    if teleport_close:
        checks.require("Event Player.KursorTeleportasi = 0;" not in teleport_close.body, "chiusura Teleport resetta ancora la pagina")
        checks.require("Destroy In-World Text(Event Player.TeksTeleportasi);" in teleport_close.body, "chiusura Teleport non distrugge il target world text dedicato")
    if inspect_rule:
        checks.require("Event Player.MenuTerbuka == False;" in inspect_rule.body, "Crouch Inspection deve restare disattivata mentre il Menu Arcade è aperto")
        checks.require("Event Player.TeleportasiJongkokAktif == False;" in inspect_rule.body, "Inspection generica entra ancora nel Teleport")
        checks.require("Event Player.TeksDiri = Last Text ID;" not in inspect_rule.body, "Crouch normale mostra ancora il proprio nome")
        checks.require("Destroy In-World Text(Event Player.TeksDiri);" in inspect_rule.body, "Crouch normale non pulisce un eventuale nome personale residuo")
        checks.require("Event Player.TeleportasiJongkokDiaktifkan == False;" in inspect_rule.body, "Inspection generica può vincere il primo frame Crouch")
        checks.require("SegarkanTargetTeleportasi" not in inspect_rule.body and "CalonTargetTeleportasi" not in inspect_rule.body, "Inspection generica condivide ancora il target Teleport")
    fast_manager = find_rule(rules, "04g - Global-first:")
    passive_manager = find_rule(rules, "04i - Global-first:")
    checks.require("PosisiRuangMuncul" not in source and "PunyaPosisiMuncul" not in source, "cache Spawn Room legacy ancora presente")
    if teleport_detector:
        checks.require(dummy_eligibility in teleport_detector.body and bot_eligibility in teleport_detector.body and privacy in teleport_detector.body, "19d0 target live: bot pubblici e player privacy OFF richiesti")
    if inspect_rule:
        checks.require("Event Player.TargetInspeksi != First Of(Sorted Array(Filtered Array(All Players(All Teams)" in inspect_rule.body, "Crouch normale non rileva direttamente il cambio closest-to-reticle")
        checks.require("Destroy In-World Text(Event Player.TeksDunia);" in inspect_rule.body and "Create In-World Text(" in inspect_rule.body, "Crouch normale non distrugge e ricrea il nome")
        checks.require("Wait(" not in inspect_rule.body and "Loop If Condition Is True;" not in inspect_rule.body, "Crouch normale non deve usare Wait o Loop")
        checks.require(dummy_eligibility in inspect_rule.body and bot_eligibility in inspect_rule.body and privacy in inspect_rule.body, "Crouch normale non usa lo stesso filtro pubblico del Teleport")
    if teleport_exec:
        checks.require("Teleport(Event Player, Position Of(First Of(Spawn Points(Team Of(Event Player)))));" in teleport_exec.body, "Spawn teleport non usa direttamente Spawn Points")
        checks.require("PosisiRuangMuncul" not in teleport_exec.body and "PunyaPosisiMuncul" not in teleport_exec.body, "Spawn teleport usa ancora cache/registrazione")
    interact = find_rule(rules, "10 - Menu:")
    reload_rule = find_rule(rules, "11 - Menu:")
    preload = find_rule(rules, "91q - SubmenuPreload")
    checks.require(preload is not None, "SubmenuPreload assente")
    if preload:
        checks.require("Count Of(Event Player.HudMenuArcade) > 1" in preload.body, "preload non limita Main + 1 submenu")
        checks.require("Destroy HUD Text(Event Player.HudMenuArcade[1]);" in preload.body, "preload non sostituisce il submenu")
        checks.require("Call Subroutine(GambarHalamanAktif);" in preload.body, "preload non prepara la pagina selezionata")
    for label, rule in (("Interact", interact), ("Reload", reload_rule)):
        if rule:
            checks.require("Create HUD Text(" not in rule.body, f"{label} ricrea HUD durante cambio pagina")
            checks.require("Destroy HUD Text(" not in rule.body, f"{label} distrugge HUD durante cambio pagina")
    if reload_rule:
        checks.require("Event Player.HalamanMenu = -1;" in reload_rule.body, "Reload non torna al Main")
    checks.equal(source.count("Append To Array(Event Player.HudMenuArcade, Event Player.HudMenu)"), 13, "renderer HUD Arcade")
    for rule in rules:
        if "Create HUD Text(" in rule.body:
            checks.require("Wait(" not in rule.body, f"{rule.name}: Create HUD con Wait")
            checks.require("Loop If Condition Is True;" not in rule.body, f"{rule.name}: Create HUD con Loop")
    checks.require("If(Health(Global.PemainAktif) >= Max Health(Global.PemainAktif));" in source, "Unkillable 1 HP non usa >= Max Health")
    checks.require("Set Player Health(Global.PemainAktif, 1);" in source, "Unkillable 1 HP non riporta a 1")
    checks.require("Stop Modifying Hero Voice Lines(Event Player);" in source, "Hero Voice NORMAL assente")
    checks.require("Set Move Speed(Event Player, 0);" in source, "Try Your Luck rosso non blocca la velocità")
    checks.require("Start Forcing Player Position(" not in source, "Try Your Luck non deve forzare la posizione")
    menu_toggle = find_rule(rules, "05 - Menu:")
    camera_toggle = find_rule(rules, "12c - Kamera:")
    if menu_toggle:
        checks.require("Wait(0.500, Abort When False);" in menu_toggle.body, "hold Melee 0,5 s assente")
        checks.require("Disallow Button(Event Player, Button(Crouch));" not in menu_toggle.body, "Menu Arcade non deve bloccare Crouch")
    if camera_toggle:
        checks.require("Wait(0.500, Abort When False);" in camera_toggle.body, "hold Camera 0,5 s assente")
        checks.require("Wait(0.016, Ignore Condition);" not in camera_toggle.body, "Camera mantiene un frame Wait superfluo")
    lifecycle = find_rule(rules, "04h - Global-first:")
    if lifecycle:
        checks.require("Is Alive(Global.PemainAktif.TargetKamera) == False" in lifecycle.body, "Camera globale non rilascia target morto")
        checks.require("Global.PemainAktif.KursorTeleportasi != 2" in lifecycle.body, "Inspection resta visibile fuori dalla pagina player Teleport")
    for rule in rules:
        if event_type(rule) == "Player Died":
            checks.require("Call Subroutine(TutupMenu);" not in rule.body, f"{rule.name}: morte chiude il Menu Arcade")
    respawn = find_rule(rules, "12f - Bangkit Lompat:")
    if respawn:
        checks.require("MenuTerbuka == False" not in respawn.body, "Jump respawn è bloccato con menu aperto")
    classifier = find_rule(rules, "02 - Pemain:")
    if classifier:
        checks.require("Is Dummy Bot(Event Player) == False;" in classifier.body, "classifier umano non esclude i dummy diretti")
    join = find_rule(rules, "01 - Pemain Masuk")
    leave = find_rule(rules, "04 - Pemain Keluar")
    checks.require(join is not None and leave is not None, "lifecycle Join/Leave assente")
    if join:
        for token in ("Call Subroutine(TenangkanPemain);", "Call Subroutine(BersihkanPemain);", "Call Subroutine(SiapkanPemain);"):
            checks.require(token in join.body, f"Join lifecycle incompleto: {token}")
        checks.equal(join.body.count("Wait(0.050, Ignore Condition);"), 2, "yield cambio team")
    if leave:
        checks.require("Call Subroutine(TenangkanPemain);" in leave.body and "Call Subroutine(BersihkanPemain);" in leave.body, "Leave lifecycle incompleto")
        checks.require("Is Dummy Bot(Event Player) == False;" in leave.body, "Leave umano non esclude dummy diretti")
    checks.require("For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia), 1);" not in source, "loop voto fuori limite Count anziché Count-1")
    vote_count = find_rule(rules, "91p - Subrutin:")
    checks.require(vote_count is not None, "subroutine conteggio voti assente")
    if vote_count:
        checks.require("Set Player Variable(Global.PemainManusia[Global.IndeksVote], JumlahSuara, 0);" in vote_count.body, "conteggio voti non azzera JumlahSuara prima del recount")
        checks.require("Modify Player Variable(Player Variable(Global.PemainManusia[Global.IndeksVote], PemainDipilih), JumlahSuara, Add, 1);" in vote_count.body, "conteggio voti non incrementa direttamente il player votato")
        checks.require("Count Of(Filtered Array(Global.PemainManusia, Player Variable(Current Array Element, PemainDipilih)" not in vote_count.body, "conteggio voti usa ancora il Filtered Array fragile")
        checks.require("Array Contains(Global.PemainManusia" in vote_count.body, "conteggio voti non valida più il target votato")
    if classifier:
        checks.require("Call Subroutine(HitungPilihan);" in classifier.body, "join umano non ricalcola le votazioni")
    checks.require("For Global Variable(IndeksPembersihan, 0, Count Of(Global.PemainManusia), 1);" not in source, "loop cleanup fuori limite Count anziché Count-1")
    cleanup = find_rule(rules, "93c - Subrutin:")
    if cleanup:
        checks.equal(cleanup.body.count("Wait(0.016, Ignore Condition);"), 1, "yield cleanup")
        critical = cleanup.body[cleanup.body.index("Global.IndeksKeluar = Index Of Array Value"): ]
        checks.require("Wait(" not in critical, "cleanup usa Wait mentre scratch Global condiviso è attivo")
    return checks


def main() -> int:
    source = SOURCE.read_text(encoding="utf-8")
    checks = validate(source)
    checks.finish()
    print("OK - controlli statici v0.7.2 Global-first superati")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
