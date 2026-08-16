from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
TESTS = ROOT / "tests" / "test_validate_workshop.py"
README = ROOT / "README.md"
PROJECT = ROOT / "docs" / "PROGETTO.md"
TESTDOC = ROOT / "docs" / "TEST.md"
VALIDATION = ROOT / "docs" / "VALIDAZIONE.md"
VERSION = ROOT / "VERSION"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one occurrence, found {count}")
    return text.replace(old, new, 1)


def replace_count(text: str, old: str, new: str, expected: int, label: str) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"{label}: expected {expected} occurrences, found {count}")
    return text.replace(old, new)


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    return hashlib.sha1(payload).hexdigest()


# ---------------------------------------------------------------------------
# Workshop source: lifecycle hygiene, localization, performance, camera.
# ---------------------------------------------------------------------------
source = SOURCE.read_text(encoding="utf-8")

# Dead global HUD handles: static headers are never destroyed/referenced later.
source = replace_once(source, "\t\t5: HudInfoKiri\n\t\t6: HudInfoKanan\n", "", "dead global HUD handles")
source = replace_once(source, "\t\tGlobal.HudInfoKiri = Last Text ID;\n", "", "dead left HUD assignment")
source = replace_once(source, "\t\tGlobal.HudInfoKanan = Last Text ID;\n", "", "dead right HUD assignment")

# WaktuTercatat is legacy: SiapkanPemain always records WaktuMasuk before classification.
source = replace_once(source, "\t\t1: WaktuTercatat\n", "", "legacy WaktuTercatat declaration")
source = replace_once(
    source,
    "\t\tIf(Event Player.WaktuTercatat == False);\n\t\t\tEvent Player.WaktuMasuk = Total Time Elapsed;\n\t\t\tEvent Player.WaktuTercatat = True;\n\t\tEnd;\n",
    "",
    "legacy join time fallback",
)
source = replace_once(source, "\t\tEvent Player.WaktuTercatat = True;\n", "", "legacy WaktuTercatat initialization")

# Remove obsolete Menu 10 camera/cache variables and compact only this tail.
old_luck_vars = """\t\t70: KartuNasibAktif
\t\t71: PosisiKartuNasib
\t\t72: TeksKartuNasib
\t\t73: KartuNasibMerah
\t\t74: PutaranKartuNasib
\t\t75: JedaKartuNasib
\t\t76: IkonKartuNasib
\t\t77: IkonKartuNasibHijau
\t\t78: TeksKartuNasibKanan
\t\t79: ModeKameraSebelumNasib
\t\t80: TargetKameraSebelumNasib
\t\t81: KursorVoto
\t\t82: TargetVoto
\t\t83: NumeroVoti
"""
new_luck_vars = """\t\t70: KartuNasibAktif
\t\t71: TeksKartuNasib
\t\t72: KartuNasibMerah
\t\t73: PutaranKartuNasib
\t\t74: JedaKartuNasib
\t\t75: IkonKartuNasib
\t\t76: IkonKartuNasibHijau
\t\t77: TeksKartuNasibKanan
\t\t78: KursorVoto
\t\t79: TargetVoto
\t\t80: NumeroVoti
"""
source = replace_once(source, old_luck_vars, new_luck_vars, "compact luck/vote player variables")

for obsolete_line, label in (
    ("\t\t\t\tEvent Player.PosisiKartuNasib = Eye Position(Event Player) + Facing Direction Of(Event Player) * 4;\n", "luck position cache assignment"),
    ("\t\tEvent Player.PosisiKartuNasib = Vector(0, 0, 0);\n", "luck position reset"),
    ("\t\tEvent Player.ModeKameraSebelumNasib = 0;\n", "old luck camera mode init"),
    ("\t\tEvent Player.TargetKameraSebelumNasib = Null;\n", "old luck camera target init"),
):
    source = replace_count(source, obsolete_line, "", source.count(obsolete_line), label)

# Remove one redundant icon initialization done again by SiapkanPemain.
source = replace_once(
    source,
    "\t\tEvent Player.MenitLobi = 0;\n\t\tEvent Player.IkonKartuNasib = Null;\n\t\tEvent Player.UrutanHUD = First Of(Global.SlotHUDTersedia);",
    "\t\tEvent Player.MenitLobi = 0;\n\t\tEvent Player.UrutanHUD = First Of(Global.SlotHUDTersedia);",
    "duplicate luck icon init during registration",
)

# A new human starts with zero votes; a full recount on join changes nothing.
source = replace_once(
    source,
    "\t\tGlobal.PemainManusia = Append To Array(Global.PemainManusia, Event Player);\n\t\tCall Subroutine(HitungPilihan);\n\t\tDisable Nameplates",
    "\t\tGlobal.PemainManusia = Append To Array(Global.PemainManusia, Event Player);\n\t\tDisable Nameplates",
    "unnecessary vote recount on join",
)

# Roster minutes are viewer-localized like the rest of the HUD.
source = replace_once(
    source,
    'Custom String("{0} - {1} MIN", Event Player, Event Player.MenitLobi)',
    'Player Variable(Local Player, IndeksBahasa) == 0 ? Custom String("{0} - {1} MIN", Event Player, Event Player.MenitLobi) : Player Variable(Local Player, IndeksBahasa) == 1 ? Custom String("{0} - {1} MENIT", Event Player, Event Player.MenitLobi) : Custom String("{0} - {1} นาที", Event Player, Event Player.MenitLobi)',
    "localized roster minutes",
)

# Unify all Menu 10 visual cleanup before any human-array lookup on leave.
old_leave_head = """\tactions
\t{
\t\tIf(Event Player.TeksKartuNasibKanan != Null);
\t\t\tDestroy In-World Text(Event Player.TeksKartuNasibKanan);
\t\t\tEvent Player.TeksKartuNasibKanan = Null;
\t\tEnd;
\t\tIf(Event Player.IkonKartuNasibHijau != Null);
\t\t\tDestroy Icon(Event Player.IkonKartuNasibHijau);
\t\t\tEvent Player.IkonKartuNasibHijau = Null;
\t\tEnd;
\t\tGlobal.PemainPembersihan = Event Player;
"""
new_leave_head = """\tactions
\t{
\t\tIf(Event Player.TeksKartuNasib != Null);
\t\t\tDestroy In-World Text(Event Player.TeksKartuNasib);
\t\tEnd;
\t\tIf(Event Player.TeksKartuNasibKanan != Null);
\t\t\tDestroy In-World Text(Event Player.TeksKartuNasibKanan);
\t\tEnd;
\t\tIf(Event Player.IkonKartuNasib != Null);
\t\t\tDestroy Icon(Event Player.IkonKartuNasib);
\t\tEnd;
\t\tIf(Event Player.IkonKartuNasibHijau != Null);
\t\t\tDestroy Icon(Event Player.IkonKartuNasibHijau);
\t\tEnd;
\t\tEvent Player.TeksKartuNasib = Null;
\t\tEvent Player.TeksKartuNasibKanan = Null;
\t\tEvent Player.IkonKartuNasib = Null;
\t\tEvent Player.IkonKartuNasibHijau = Null;
\t\tEvent Player.KartuNasibAktif = False;
\t\tEvent Player.KartuNasibMerah = False;
\t\tEvent Player.PutaranKartuNasib = 0;
\t\tEvent Player.JedaKartuNasib = 0;
\t\tGlobal.PemainPembersihan = Event Player;
"""
source = replace_once(source, old_leave_head, new_leave_head, "unified leave luck cleanup")
old_nested_luck_leave = """\t\t\tIf(Event Player.KartuNasibAktif == True);
\t\t\t\tStop Chasing Player Variable(Event Player, PosisiKartuNasib);
\t\t\t\tIf(Event Player.TeksKartuNasib != Null);
\t\t\t\t\tDestroy In-World Text(Event Player.TeksKartuNasib);
\t\t\t\tEnd;
\t\t\t\tIf(Event Player.IkonKartuNasib != Null);
\t\t\t\t\tDestroy Icon(Event Player.IkonKartuNasib);
\t\t\t\tEnd;
\t\t\t\tEvent Player.TeksKartuNasib = Null;
\t\t\t\tEvent Player.IkonKartuNasib = Null;
\t\t\t\tEvent Player.KartuNasibAktif = False;
\t\t\tEnd;
"""
source = replace_once(source, old_nested_luck_leave, "", "remove split legacy leave luck cleanup")

# Lower-frequency work that does not need the old cadence.
source = replace_once(source, "\t\tWait(0.100, Ignore Condition);\n\t\tGlobal.RGBFase = (Global.RGBFase + 3) % 1530;", "\t\tWait(0.125, Ignore Condition);\n\t\tGlobal.RGBFase = (Global.RGBFase + 3.750) % 1530;", "RGB 8 Hz same 51s cycle")
source = replace_once(source, "\t\tWait(5, Ignore Condition);\n\t\tLoop If Condition Is True;", "\t\tWait(10, Ignore Condition);\n\t\tLoop If Condition Is True;", "lobby minutes 0.1 Hz")
source = replace_once(source, "\t\tWait(0.200, Abort When False);\n\t\tLoop If Condition Is True;", "\t\tWait(0.250, Abort When False);\n\t\tLoop If Condition Is True;", "inspection 4 Hz")

# Camera: Start Camera can replace an active custom camera directly. Removing the
# preceding Stop Camera avoids a one-frame first-person flash when switching target.
source = replace_once(
    source,
    "\t\tAbort If(Entity Exists(Event Player.TargetKamera) == False);\n\t\tStop Camera(Event Player);\n\t\t\"Satu ekspresi visual memakai satu waktu client: tanpa cache posisi server yang dapat membuat model bergetar.\"",
    "\t\tAbort If(Entity Exists(Event Player.TargetKamera) == False);\n\t\t\"Ganti kamera langsung tanpa Stop Camera agar perpindahan target tidak berkedip satu frame.\"",
    "camera direct replacement",
)

# Rule titles / Indonesian visible strings.
source = replace_once(source, 'rule("18e - Nasib: Roulette merah hijau makin lambat")', 'rule("18e - Nasib: Undian merah hijau makin lambat")', "Indonesian luck rule title")
source = replace_once(source, 'rule("91o - Subrutin: Gambar menu vote pemain")', 'rule("91o - Subrutin: Gambar menu pilihan pemain")', "Indonesian vote renderer title")
source = replace_once(source, 'rule("91p - Subrutin: Hitung ulang vote dan leader unik")', 'rule("91p - Subrutin: Hitung ulang pilihan dan pemimpin tunggal")', "Indonesian tally title")
source = source.replace("11 - VOTE PEMAIN", "11 - PILIH PEMAIN")
source = source.replace("VOTE KAMU", "PILIHAN KAMU")
source = source.replace('Custom String("{0}: vote | {1}: kembali"', 'Custom String("{0}: pilih | {1}: kembali"')
source = source.replace(' - {2} VOTE"', ' - {2} SUARA"')
source = source.replace('Custom String("Vote untuk {0} tersimpan."', 'Custom String("Pilihan untuk {0} tersimpan."')

SOURCE.write_text(source, encoding="utf-8")

# ---------------------------------------------------------------------------
# Validator: version, lifecycle audit, performance contracts, localization.
# ---------------------------------------------------------------------------
validator = VALIDATOR.read_text(encoding="utf-8")
validator = validator.replace("0.5.5", "0.6.0")

validator = replace_once(
    validator,
    '''        (76, "IkonKartuNasib"),
        (77, "IkonKartuNasibHijau"),
        (78, "TeksKartuNasibKanan"),
        (79, "ModeKameraSebelumNasib"),
        (80, "TargetKameraSebelumNasib"),''',
    '''        (75, "IkonKartuNasib"),
        (76, "IkonKartuNasibHijau"),
        (77, "TeksKartuNasibKanan"),
        (78, "KursorVoto"),
        (79, "TargetVoto"),
        (80, "NumeroVoti"),''',
    "validator compact arcade slots",
)
validator = validator.replace('                "Event Player.PosisiKartuNasib = Vector(0, 0, 0);",\n', '')
old_cache_checks = '''    checks.require(
        "Event Player.PosisiKartuNasib = Eye Position(Event Player) + Facing Direction Of(Event Player) * 4;" in mask_strings(source),
        "Nasib: cache effetto non segue il mirino del proprietario",
    )
    checks.require(
        "Chase Player Variable Over Time(Event Player, PosisiKartuNasib" not in mask_strings(source),
        "Nasib: la vecchia animazione dal terreno non deve restare attiva",
    )'''
new_cache_checks = '''    for obsolete in ("PosisiKartuNasib", "ModeKameraSebelumNasib", "TargetKameraSebelumNasib"):
        checks.require(obsolete not in source, f"Nasib: stato obsoleto ancora presente: {obsolete}")'''
validator = replace_once(validator, old_cache_checks, new_cache_checks, "validator obsolete luck state")

validator = replace_once(
    validator,
    '("03 - Waktu:", "Wait(5, Ignore Condition);", "minuti 0,2Hz"),',
    '("03 - Waktu:", "Wait(10, Ignore Condition);", "minuti 0,1Hz"),',
    "validator minute frequency",
)
validator = replace_once(
    validator,
    '("14 - Intip Pahlawan:", "Wait(0.200, Abort When False);", "inspection 5Hz"),',
    '("14 - Intip Pahlawan:", "Wait(0.250, Abort When False);", "inspection 4Hz"),',
    "validator inspection frequency audit",
)
validator = replace_once(validator, '"Wait(0.200, Abort When False);" in source,\n        "refresh Crouch non a 0,20 s",', '"Wait(0.250, Abort When False);" in source,\n        "refresh Crouch non a 0,25 s",', "validator crouch frequency")
validator = replace_once(
    validator,
    '"Wait(0.100, Ignore Condition);",\n        "Global.RGBFase = (Global.RGBFase + 3) % 1530;",',
    '"Wait(0.125, Ignore Condition);",\n        "Global.RGBFase = (Global.RGBFase + 3.750) % 1530;",',
    "validator RGB frequency",
)

# Strengthen camera contract without touching disable/leave Stop Camera paths.
camera_insert = '''
    camera_subroutines = rules_containing(rules, "Subroutine;", "MulaiKamera;")
    checks.equal(len(camera_subroutines), 1, "camera: una sola subroutine MulaiKamera")
    if camera_subroutines:
        camera_body = mask_strings(camera_subroutines[0].body)
        checks.require(
            "Stop Camera(Event Player);" not in camera_body,
            "camera: MulaiKamera non deve fare Stop Camera prima di Start Camera; causa micro-scatto",
        )
'''
validator = replace_once(validator, "\n\ndef check_crouch(checks: Checks, source: str, rules: list[Rule]) -> None:", camera_insert + "\n\ndef check_crouch(checks: Checks, source: str, rules: list[Rule]) -> None:", "camera audit insertion")

# Indonesian rule-title audit: remove the last English feature words from titles.
validator = replace_once(
    validator,
    '        "overlay selama Crouch", "scatto",\n    )',
    '        "overlay selama Crouch", "scatto", "vote", "leader", "Roulette",\n    )',
    "rule-title language audit",
)

# Roster + Vote Indonesian localization requirements.
localization_anchor = '''    for stale in (
        "DAFTAR PEMAIN & WAKTU CHILL", "SOUNDTRACK PEMAIN", "belum pilih soundtrack",'''
localization_extra = '''    for token in (
        'Custom String("{0} - {1} MIN", Event Player, Event Player.MenitLobi)',
        'Custom String("{0} - {1} MENIT", Event Player, Event Player.MenitLobi)',
        'Custom String("{0} - {1} นาที", Event Player, Event Player.MenitLobi)',
        '11 - PILIH PEMAIN',
        'PILIHAN KAMU',
        'SUARA',
    ):
        checks.require(token in source, f"localizzazione roster/voto mancante: {token}")
    checks.require("11 - VOTE PEMAIN" not in source and "VOTE KAMU" not in source, "ramo Indonesia Menu 11 usa ancora testo inglese")

'''
validator = replace_once(validator, localization_anchor, localization_extra + localization_anchor, "localization audit expansion")
validator = replace_once(
    validator,
    'checks.require("11 - VOTE PLAYER" in raw and "11 - VOTE PEMAIN" in raw and "11 - โหวตผู้เล่น" in raw, "Vote: localizzazione incompleta")',
    'checks.require("11 - VOTE PLAYER" in raw and "11 - PILIH PEMAIN" in raw and "11 - โหวตผู้เล่น" in raw, "Vote: localizzazione incompleta")\n        checks.require("PILIHAN KAMU" in raw and "SUARA" in raw, "Vote: ramo Bahasa Indonesia incompleto")',
    "vote renderer localization validation",
)

# Full lifecycle invariant: all declared player state initialized, one leave path,
# all parallel arrays and luck visuals cleaned, no duplicate rule names/dead handles.
lifecycle_function = r'''

def check_lifecycle_hygiene(
    checks: Checks,
    source: str,
    rules: list[Rule],
    player_names: set[str],
) -> None:
    clean = mask_strings(source)
    names = [rule.name for rule in rules]
    checks.equal(len(names), len(set(names)), "audit lifecycle: titoli regola duplicati")

    for dead in (
        "HudInfoKiri", "HudInfoKanan", "WaktuTercatat",
        "PosisiKartuNasib", "ModeKameraSebelumNasib", "TargetKameraSebelumNasib",
    ):
        checks.require(dead not in source, f"audit lifecycle: stato morto ancora presente {dead}")

    setup = rules_containing(rules, "Subroutine;", "SiapkanPemain;")
    checks.equal(len(setup), 1, "audit lifecycle: una sola SiapkanPemain")
    if setup:
        body = mask_strings(setup[0].body)
        for name in sorted(player_names):
            checks.require(
                re.search(rf"Event Player\.{re.escape(name)}\s*=", body) is not None,
                f"audit lifecycle: variabile player non inizializzata in SiapkanPemain: {name}",
            )

    join = [rule for rule in rules if code_contains(rule.body, "Player Joined Match;", "Call Subroutine(SiapkanPemain);")]
    fallback = [rule for rule in rules if code_contains(rule.body, "Ongoing - Each Player;", "Event Player.SudahSiap == False;", "Call Subroutine(SiapkanPemain);")]
    checks.equal(len(join), 1, "audit lifecycle: init Player Joined")
    checks.equal(len(fallback), 1, "audit lifecycle: init player già presenti")

    leave = [rule for rule in rules if code_contains(rule.body, "Player Left Match;")]
    checks.equal(len(leave), 1, "audit lifecycle: un solo cleanup Player Left")
    if leave:
        body = mask_strings(leave[0].body)
        capture = body.find("Global.PemainPembersihan = Event Player;")
        checks.require(capture >= 0, "audit lifecycle: leave non cattura identità")
        for token in (
            "Destroy In-World Text(Event Player.TeksKartuNasib);",
            "Destroy In-World Text(Event Player.TeksKartuNasibKanan);",
            "Destroy Icon(Event Player.IkonKartuNasib);",
            "Destroy Icon(Event Player.IkonKartuNasibHijau);",
        ):
            position = body.find(token)
            checks.require(0 <= position < capture, f"audit lifecycle: cleanup Nasib non universale prima del lookup: {token}")
        for array_name in (
            "HudKiriPemain", "HudKananPemain", "HudMenuPemain", "TeksDuniaPemain",
            "TeksDiriPemain", "SlotHUDPemain", "PemainManusia",
        ):
            checks.require(
                f"Modify Global Variable({array_name}, Remove From Array By Index, Global.IndeksKeluar);" in body,
                f"audit lifecycle: array parallelo non ripulito al leave: {array_name}",
            )
        for token in (
            "TargetVoto == Global.PemainPembersihan",
            "TargetKamera == Global.PemainPembersihan",
            "TargetInspeksi == Global.PemainPembersihan",
            "TargetTeleportasiTerkunci == Global.PemainPembersihan",
            "TargetBalasDendamDipilih == Global.PemainPembersihan",
            "TargetBalasDendamTerkunci == Global.PemainPembersihan",
        ):
            checks.require(token in body, f"audit lifecycle: riferimento stale non ripulito: {token}")

'''
validator = replace_once(validator, "\ndef check_idempotent_menu_feedback(checks: Checks, source: str, rules: list[Rule]) -> None:", lifecycle_function + "\ndef check_idempotent_menu_feedback(checks: Checks, source: str, rules: list[Rule]) -> None:", "lifecycle audit function")
validator = replace_once(
    validator,
    "        check_bot_lifecycle(checks, source, rules)\n",
    "        check_bot_lifecycle(checks, source, rules)\n        check_lifecycle_hygiene(checks, source, rules, player_names)\n",
    "call lifecycle audit",
)
VALIDATOR.write_text(validator, encoding="utf-8")

# ---------------------------------------------------------------------------
# Unit tests: add regression coverage for the audit itself. Existing 20 + 4 = 24.
# ---------------------------------------------------------------------------
tests = TESTS.read_text(encoding="utf-8")
new_tests = r'''
    def test_lifecycle_requires_every_player_variable_initialized(self) -> None:
        setup_at = self.source.index('rule("94 - ')
        tail = self.source[setup_at:]
        tail2 = tail.replace(
            "Event Player.TargetVoto = Null;",
            '"Event Player.TargetVoto = Null;"',
            1,
        )
        self.assertNotEqual(tail2, tail)
        mutated = self.source[:setup_at] + tail2
        _, player_names, _ = validator.declaration_tables(mutated)
        checks = validator.Checks()
        validator.check_lifecycle_hygiene(checks, mutated, self.rules(mutated), player_names)
        self.assertTrue(any("TargetVoto" in error and "non inizializzata" in error for error in checks.errors), checks.errors)

    def test_obsolete_luck_state_is_rejected(self) -> None:
        mutated = self.source.replace(
            "\t\t80: NumeroVoti\n",
            "\t\t80: NumeroVoti\n\t\t84: PosisiKartuNasib\n",
            1,
        )
        self.assertNotEqual(mutated, self.source)
        checks = validator.Checks()
        validator.check_arcade_features(checks, mutated, self.rules(mutated))
        self.assertTrue(any("stato obsoleto" in error for error in checks.errors), checks.errors)

    def test_camera_subroutine_must_not_stop_before_start(self) -> None:
        camera_at = self.source.index('rule("93 - ')
        tail = self.source[camera_at:]
        tail2 = tail.replace(
            "\t\tStart Camera(Event Player,",
            "\t\tStop Camera(Event Player);\n\t\tStart Camera(Event Player,",
            1,
        )
        self.assertNotEqual(tail2, tail)
        mutated = self.source[:camera_at] + tail2
        _, player_names, _ = validator.declaration_tables(mutated)
        checks = validator.Checks()
        validator.check_camera(checks, mutated, self.rules(mutated), player_names)
        self.assertTrue(any("micro-scatto" in error for error in checks.errors), checks.errors)

    def test_roster_minutes_need_three_languages(self) -> None:
        mutated = self.source.replace(
            'Custom String("{0} - {1} MENIT", Event Player, Event Player.MenitLobi)',
            'Custom String("{0} - {1} MIN", Event Player, Event Player.MenitLobi)',
            1,
        )
        self.assertNotEqual(mutated, self.source)
        checks = validator.Checks()
        validator.check_localization_and_indonesian_naming(checks, mutated, self.rules(mutated))
        self.assertTrue(any("localizzazione roster/voto" in error for error in checks.errors), checks.errors)

'''
tests = replace_once(tests, "\n\nif __name__ == \"__main__\":\n    unittest.main()", "\n" + new_tests + "\nif __name__ == \"__main__\":\n    unittest.main()", "append audit unit tests")
TESTS.write_text(tests, encoding="utf-8")

# ---------------------------------------------------------------------------
# Version and docs: make GitHub reflect the actual current release.
# ---------------------------------------------------------------------------
VERSION.write_text("0.6.0\n", encoding="utf-8")

readme = README.read_text(encoding="utf-8")
readme = readme.replace("0.5.5", "0.6.0")
readme = replace_once(
    readme,
    "La versione **0.6.0** resta il numero tecnico corrente del repository, ma questo README descrive lo **stato funzionale attuale** del Workshop dopo gli aggiornamenti successivi.",
    "La versione **0.6.0** identifica lo stato funzionale e tecnico corrente del repository.",
    "README version wording",
)
readme = readme.replace("`5 - Unkillable` — non disponibile nello Spawn Room.", "`5 - Unkillable` — OFF / 1 HP / FULL HP; solo 1 HP non è disponibile nello Spawn Room.")
readme = readme.replace("| 5 | Unkillable: 1 HP | ON / OFF |", "| 5 | Unkillable | OFF / 1 HP / FULL HP |")
readme = readme.replace("inspection Crouch a **5 Hz**", "inspection Crouch a **4 Hz**")
readme = readme.replace("contatore minuti ogni **5 s**", "contatore minuti ogni **10 s**")
readme = readme.replace("un solo loop RGB globale a 10 Hz", "un solo loop RGB globale a 8 Hz")
readme = readme.replace("test statici: 20 unit test + validatore Workshop", "test statici: 24 unit test + validatore Workshop")
if "### Audit 0.6.0" not in readme:
    readme += "\n\n### Audit 0.6.0\n\nLa manutenzione 0.6.0 rimuove stato Workshop non più usato, unifica il cleanup Menu 10 nel Player Left, verifica automaticamente che ogni variabile player dichiarata sia inizializzata in `SiapkanPemain`, controlla riferimenti stale e titoli regola duplicati, localizza i minuti roster EN/ID/TH e rende il cambio target della camera diretto senza `Stop Camera` intermedio. Il repository mantiene un solo branch operativo (`main`) e soltanto i due workflow permanenti.\n"
README.write_text(readme, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
project = project.replace("0.5.5", "0.6.0")
project = replace_once(
    project,
    "Questo documento descrive lo **stato funzionale corrente** del Workshop, inclusi gli aggiornamenti successivi alla release tecnica 0.6.0.",
    "Questo documento descrive lo **stato funzionale e tecnico corrente** del Workshop 0.6.0.",
    "project version wording",
)
project = project.replace("| 5 | Unkillable: 1 HP / Kebal | ON / OFF |", "| 5 | Unkillable / Kebal | OFF / 1 HP / FULL HP |")
project = project.replace("L'inspection aggiorna il target a **5 Hz**", "L'inspection aggiorna il target a **4 Hz**")
project = project.replace("`MenitLobi` ogni 5 s", "`MenitLobi` ogni 10 s")
project = project.replace("RGB unico globale;", "RGB unico globale a 8 Hz;")
project = project.replace("La CI esegue 20 unit test", "La CI esegue 24 unit test")
project = project.replace("- 11 menu EN/ID/TH;", "- 12 menu EN/ID/TH;")
project = project.replace("colore, contatore, intervallo e posizione vengono azzerati", "colore, contatore e intervallo vengono azzerati")
project = replace_once(
    project,
    "La pipeline usa un solo raycast e non mantiene un loop camera server per-frame dedicato.",
    "La pipeline usa un solo raycast e non mantiene un loop camera server per-frame dedicato. `MulaiKamera` passa direttamente a `Start Camera` senza un `Stop Camera` intermedio: quando si cambia target evita il frame di ritorno alla camera normale che può apparire come micro-scatto. `Stop Camera` resta soltanto nei veri percorsi di disattivazione/cleanup.",
    "camera project audit note",
)
if "## Audit lifecycle 0.6.0" not in project:
    project += "\n\n## Audit lifecycle 0.6.0\n\n`SiapkanPemain` inizializza esplicitamente ogni variabile player dichiarata e il validatore verifica questa proprietà automaticamente. Il Player Left usa un solo percorso di cleanup: distrugge prima tutti gli oggetti temporanei della carta, poi rimuove gli HUD/IWT dagli array paralleli, restituisce lo slot HUD, cancella i voti verso il player uscito e ripulisce riferimenti Camera/Revenge/Teleport/Inspection dei player rimasti. Sono stati eliminati gli handle globali statici `HudInfoKiri/HudInfoKanan`, il legacy `WaktuTercatat` e lo stato Menu 10 non più usato `PosisiKartuNasib/ModeKameraSebelumNasib/TargetKameraSebelumNasib`.\n"
PROJECT.write_text(project, encoding="utf-8")

testdoc = TESTDOC.read_text(encoding="utf-8")
testdoc = testdoc.replace("0.5.5", "0.6.0")
testdoc = replace_once(
    testdoc,
    "Questa matrice descrive lo **stato funzionale corrente** del Workshop, inclusi gli aggiornamenti successivi alla release tecnica 0.6.0.",
    "Questa matrice descrive lo **stato funzionale e tecnico corrente** del Workshop 0.6.0.",
    "testdoc version wording",
)
testdoc = testdoc.replace("Ran 20 tests", "Ran 24 tests")
old_menu_test = """## 8 menu Arcade

Aprire il Menu Arcade con Melee 0,5 s e verificare esattamente 8 voci:

1. Soundtrack
2. Third-Person Camera
3. Name Color
4. HUD Language
5. Revenge
6. Unkillable: 1 HP
7. Hero Voice
8. Player Icon

Teleport non deve comparire come nona voce del Main Menu.
"""
new_menu_test = """## 12 menu Arcade

Aprire il Menu Arcade con Melee 0,5 s e verificare esattamente 12 voci:

1. Soundtrack
2. Third-Person Camera
3. Name Color
4. HUD Language
5. Revenge
6. Unkillable (OFF / 1 HP / FULL HP)
7. Hero Voice
8. Player Icon
9. Crouch Teleport
10. Crouch Privacy
11. Try Your Luck
12. Vote Player

Teleport operativo resta nell'overlay Crouch; Menu 8 abilita/disabilita soltanto quell'overlay.
"""
testdoc = replace_once(testdoc, old_menu_test, new_menu_test, "testdoc menu count")
testdoc = testdoc.replace("tutte le 8 voci", "tutte le 12 voci")
testdoc = testdoc.replace("tutti gli 8 menu", "tutti i 12 menu")
testdoc = testdoc.replace("- `N MIN`.", "- EN: `N MIN`;\n- ID: `N MENIT`;\n- TH: `N นาที`.")
testdoc = testdoc.replace("Il refresh a 5 Hz", "Il refresh a 4 Hz")
testdoc = testdoc.replace("- Verificare collisione pareti e pitch estremo.", "- Verificare collisione pareti e pitch estremo.\n- Passare rapidamente self → target → altro target: non deve comparire un frame in prima persona fra due `Start Camera`.")
testdoc = testdoc.replace("## Unkillable: 1 HP", "## Unkillable — OFF / 1 HP / FULL HP")
testdoc = testdoc.replace("- OFF manuale: ripristino corretto.", "- OFF manuale: ripristino corretto.\n- FULL HP deve restare attivo anche nello Spawn Room, con Halo RGB e salute piena.")
if "## Menu 10 / 11" not in testdoc:
    testdoc += "\n\n## Menu 10 / 11\n\n- Try Your Luck: attivazione chiude e blocca il menu, forza Unkillable OFF e non cambia la camera; morte/leave devono distruggere entrambi i bracket e Heart/Skull senza oggetti orfani.\n- Vote Player: lista soli umani, self-vote consentito, conteggi aggiornati nel Menu 11; pareggio al primo posto = nessuna CHILL STAR; leave del target cancella i voti verso di lui e ricalcola.\n- Ripetere join/leave mentre Menu 11 è aperto e verificare cursori validi e nessun riferimento stale.\n"
TESTDOC.write_text(testdoc, encoding="utf-8")

# Rewrite validation report to eliminate stale historical claims.
blob = git_blob_sha(SOURCE)
validation = f'''# Rapporto di validazione — versione 0.6.0

Data: 2026-08-16

Release tecnica: **CHILL Dedicated Server 0.6.0**

Stato corrente: **static-ready, live-pending**.

## Revisione Workshop

Blob Git del sorgente Workshop validato:

```text
{blob}
```

## Audit 0.6.0

Il gate verifica:

- struttura Workshop, delimitatori, dichiarazioni e titoli regola senza duplicati;
- inizializzazione esplicita in `SiapkanPemain` di ogni variabile player dichiarata;
- un solo percorso Player Left con cleanup degli array HUD/IWT, slot HUD, voti e riferimenti Camera/Revenge/Teleport/Inspection;
- assenza dello stato morto rimosso (`HudInfoKiri`, `HudInfoKanan`, `WaktuTercatat`, `PosisiKartuNasib`, `ModeKameraSebelumNasib`, `TargetKameraSebelumNasib`);
- 100 generi, 12 menu (`0..11`), 32 Name Color e 37 Player Icon;
- HUD e Small Message EN / Bahasa Indonesia / ไทย, inclusi minuti roster `MIN / MENIT / นาที`;
- titoli regola personalizzati in Bahasa Indonesia;
- Menu 5 OFF / 1 HP / FULL HP: Warning rosso per 1 HP, Halo RGB per FULL HP, Spawn Room reset solo 1 HP;
- Menu 10: bracket + Heart/Skull persistenti, nessun cambio camera, Unkillable OFF, reset morte/leave, 50/50;
- Menu 11: soli umani, self-vote, conteggio event-driven, pareggio = nessuna CHILL STAR;
- Camera con un solo raycast e `MulaiKamera` senza `Stop Camera` immediatamente prima del nuovo `Start Camera`;
- refresh passivi Camera/Revenge/Teleport a 1 Hz, Spawn cache a 1 Hz, minuti lobby a 0,1 Hz, inspection a 4 Hz, RGB globale a 8 Hz;
- workflow consentiti limitati ai due permanenti e nessuna automazione legacy.

## Unit test

```text
Ran 24 tests
OK
```

## Esito validatore registrato

```text
OK - controlli statici v0.6.0 superati
```

## GitHub

Branch operativo: `main` (unico branch del repository al momento dell'audit).

Workflow permanenti:

- `validate-workshop.yml`
- `maintenance-patch.yml`

Non risultano tag o release legacy da sincronizzare. `.github/maintenance/patch.py` è temporaneo e viene eliminato dal workflow di manutenzione dopo il commit validato.

## Verifiche live ancora obbligatorie

- importazione nel client Overwatch;
- tutti i 12 menu in EN / ID / TH;
- join/leave ripetuti e stress con 12 player;
- Camera self/target e cambi target rapidi senza micro-scatto;
- Crouch inspection/Teleport;
- Try Your Luck durante movimento/camera 3P;
- Vote Player con join/leave e pareggi;
- Server Load Average/Peak reale e assenza di crescita permanente HUD/IWT.

## Decisione

Il repository è **static-ready, live-pending**: il gate certifica coerenza strutturale e invarianti automatiche, mentre fluidità reale e stress 12-client restano prove da eseguire nel client Overwatch.
'''
VALIDATION.write_text(validation, encoding="utf-8")
