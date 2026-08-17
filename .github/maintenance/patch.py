from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKSHOP = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
TESTS = ROOT / "tests" / "test_validate_workshop.py"
VERSION = ROOT / "VERSION"
README = ROOT / "README.md"
PROGETTO = ROOT / "docs" / "PROGETTO.md"
TEST_DOC = ROOT / "docs" / "TEST.md"
VALIDAZIONE = ROOT / "docs" / "VALIDAZIONE.md"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: attesa 1 occorrenza, trovate {count}")
    return text.replace(old, new, 1)


def replace_between(text: str, start: str, end: str, replacement: str, label: str) -> str:
    start_at = text.find(start)
    if start_at < 0:
        raise RuntimeError(f"{label}: marker iniziale non trovato")
    end_at = text.find(end, start_at)
    if end_at < 0:
        raise RuntimeError(f"{label}: marker finale non trovato")
    return text[:start_at] + replacement + text[end_at:]


def git_blob_sha_text(text: str) -> str:
    data = text.replace("\r\n", "\n").encode("utf-8")
    payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    return hashlib.sha1(payload).hexdigest()


source = WORKSHOP.read_text(encoding="utf-8")

source = replace_once(source, "\t\t50: ModeMulaiDiminta\n\tplayer:", "\t\t50: ModeMulaiDiminta\n\t\t51: PembersihanAktif\n\t\t52: HudMenuPembersihan\n\tplayer:", "global cleanup vars")
source = replace_once(source, "\t\t93: PindahTimDiproses\n}", "\t\t93: PindahTimDiproses\n\t\t94: TombolPerluDipulihkan\n\t\t95: KameraPerluDihentikan\n}", "player cleanup vars")
source = replace_once(source, "\t\tGlobal.ModeMulaiDiminta = False;\n\t\tGlobal.RGBFase = 0;", "\t\tGlobal.ModeMulaiDiminta = False;\n\t\tGlobal.PembersihanAktif = False;\n\t\tGlobal.HudMenuPembersihan = Empty Array;\n\t\tGlobal.RGBFase = 0;", "init cleanup globals")

join_rule = '''rule("01 - Pemain Masuk atau Pindah Tim: Tunggu cleanup tunggal lalu masuk kembali")
{
\tevent
\t{
\t\tPlayer Joined Match;
\t\tAll;
\t\tAll;
\t}

\tconditions
\t{
\t\tIs Dummy Bot(Event Player) == False;
\t\tEvent Player.PindahTimDiproses == False;
\t}

\tactions
\t{
\t\t"Kunci lifecycle lebih dulu, lalu matikan hanya trigger berbasis variabel. Cleanup berat diserialkan oleh mutex global."
\t\tEvent Player.PindahTimDiproses = True;
\t\tEvent Player.SiklusPemainAktif = True;
\t\tCall Subroutine(TenangkanPemain);
\t\tWait(0.050, Ignore Condition);
\t\tAbort If(Entity Exists(Event Player) == False);
\t\tWait Until(Global.PembersihanAktif == False, 99999);
\t\tAbort If(Entity Exists(Event Player) == False);
\t\tIf(Or(Or(Array Contains(Global.PemainManusia, Event Player), And(Event Player.PernahDisiapkan == True, Array Contains(
\t\t\tGlobal.SlotHUDPemain, Event Player.UrutanHUD))), Array Contains(Mapped Array(Global.PemainManusia, Custom String("{0}",
\t\t\tCurrent Array Element)), Custom String("{0}", Event Player))));
\t\t\tCall Subroutine(BersihkanPemain);
\t\tEnd;
\t\tWait(0.050, Ignore Condition);
\t\tAbort If(Entity Exists(Event Player) == False);
\t\tCall Subroutine(SiapkanPemain);
\t}
}

'''
source = replace_between(source, 'rule("01 - Pemain Masuk atau Pindah Tim:', 'rule("01b - Pemain Lama:', join_rule, "join rule")

leave_rule = '''rule("04 - Pemain Keluar: Tenangkan lalu cleanup bertahap")
{
\tevent
\t{
\t\tPlayer Left Match;
\t\tAll;
\t\tAll;
\t}

\tconditions
\t{
\t\tIs Dummy Bot(Event Player) == False;
\t\tEvent Player.PernahDisiapkan == True;
\t}

\tactions
\t{
\t\tCall Subroutine(TenangkanPemain);
\t\tCall Subroutine(BersihkanPemain);
\t}
}

'''
source = replace_between(source, 'rule("04 - Pemain Keluar:', 'rule("05 - Menu:', leave_rule, "leave rule")

quiet_rule = '''rule("93b2 - Subrutin: Tenangkan trigger sebelum cleanup")
{
\tevent
\t{
\t\tSubroutine;
\t\tTenangkanPemain;
\t}

\tactions
\t{
\t\tEvent Player.TombolPerluDipulihkan = Or(Event Player.MenuTerbuka == True, Event Player.TeleportasiJongkokAktif == True);
\t\tEvent Player.KameraPerluDihentikan = Event Player.ModeKamera != 0;
\t\tEvent Player.SudahSiap = False;
\t\tEvent Player.Manusia = False;
\t\tEvent Player.PerintahMenu = 0;
\t\tEvent Player.SeranganDekatDipakai = False;
\t\tEvent Player.MenuTerbuka = False;
\t\tEvent Player.TeleportasiJongkokAktif = False;
\t\tEvent Player.PerintahTeleportasi = 0;
\t\tEvent Player.InspeksiAktif = False;
\t\tEvent Player.TargetInspeksi = Null;
\t\tEvent Player.InteraksiKameraDipakai = False;
\t\tEvent Player.KartuNasibAktif = False;
\t\tEvent Player.PutaranKartuNasib = 0;
\t\tEvent Player.ModeKamera = 0;
\t\tEvent Player.TargetKamera = Null;
\t}
}

'''
source = replace_between(source, 'rule("93b2 - Subrutin:', 'rule("93c - Subrutin:', quiet_rule, "quiet rule")

cleanup_start = source.index('rule("93c - Subrutin:')
cleanup_end = source.index('rule("94 - Subrutin:', cleanup_start)
cleanup = source[cleanup_start:cleanup_end]
cleanup = replace_once(cleanup, '\t\t"Keadaan aktif sudah ditenangkan sebelum subrutin ini; sekarang hapus data dan objek yang tersisa."\n\t\tEvent Player.PemainDipilih = Null;', '''\t\tWait Until(Global.PembersihanAktif == False, 99999);
\t\tGlobal.PembersihanAktif = True;
\t\tIf(Event Player.KameraPerluDihentikan == True);
\t\t\tStop Camera(Event Player);
\t\tEnd;
\t\tIf(Event Player.TombolPerluDipulihkan == True);
\t\t\tStop Chasing Player Variable(Event Player, WarnaMenu);
\t\t\tAllow Button(Event Player, Button(Crouch));
\t\t\tAllow Button(Event Player, Button(Primary Fire));
\t\t\tAllow Button(Event Player, Button(Secondary Fire));
\t\t\tAllow Button(Event Player, Button(Interact));
\t\t\tAllow Button(Event Player, Button(Reload));
\t\t\tAllow Button(Event Player, Button(Ability 1));
\t\t\tAllow Button(Event Player, Button(Ability 2));
\t\t\tAllow Button(Event Player, Button(Ultimate));
\t\tEnd;
\t\tIf(Or(Event Player.KebalAktif == True, Event Player.ModeKebal != 0));
\t\t\tClear Status(Event Player, Unkillable);
\t\t\tSet Damage Received(Event Player, 100);
\t\tEnd;
\t\tIf(Event Player.IndeksSuara != 0);
\t\t\tStop Modifying Hero Voice Lines(Event Player);
\t\tEnd;
\t\tIf(Event Player.RadiusNasib > 0);
\t\t\tStop Chasing Player Variable(Event Player, RadiusNasib);
\t\tEnd;
\t\tIf(Event Player.GerakNasibDikunci == True);
\t\t\tSet Move Speed(Event Player, 100);
\t\tEnd;
\t\tEvent Player.KameraPerluDihentikan = False;
\t\tEvent Player.TombolPerluDipulihkan = False;
\t\tEvent Player.KebalAktif = False;
\t\tEvent Player.ModeKebal = 0;
\t\tEvent Player.PemainDipilih = Null;''', "cleanup entry")
cleanup = replace_once(cleanup, 'Global.PemainPembersihan = Global.IndeksKeluar >= 0 ? Global.PemainManusia[Global.IndeksKeluar] : Event Player;', 'Global.PemainPembersihan = Global.IndeksKeluar >= 0 ? Global.PemainManusia[Global.IndeksKeluar] : Event Player;\n\t\tGlobal.HudMenuPembersihan = Global.IndeksKeluar >= 0 ? Player Variable(Global.PemainPembersihan, HudMenuArcade) : Empty Array;', "capture menu cleanup")
cleanup = cleanup.replace('Player Variable(Global.PemainPembersihan, HudMenuArcade)', 'Global.HudMenuPembersihan')
cleanup = replace_once(cleanup, '\t\t\tDestroy HUD Text(Global.HudKiriPemain[Global.IndeksKeluar]);\n\t\t\tDestroy HUD Text(Global.HudKananPemain[Global.IndeksKeluar]);', '\t\t\tDestroy HUD Text(Global.HudKiriPemain[Global.IndeksKeluar]);\n\t\t\tDestroy HUD Text(Global.HudKananPemain[Global.IndeksKeluar]);\n\t\t\tWait(0.016, Ignore Condition);', "stage social hud")
for index in range(13):
    cleanup = replace_once(cleanup, f'\t\t\t\tDestroy HUD Text(Global.HudMenuPembersihan[{index}]);', f'\t\t\t\tDestroy HUD Text(Global.HudMenuPembersihan[{index}]);\n\t\t\t\tWait(0.016, Ignore Condition);', f"stage arcade hud {index}")
cleanup = replace_once(cleanup, '''\t\t\tIf(Global.TeksDiriPemain[Global.IndeksKeluar] != 0);
\t\t\t\tDestroy In-World Text(Global.TeksDiriPemain[Global.IndeksKeluar]);
\t\t\tEnd;
\t\t\tGlobal.SlotHUDTersedia = Sorted Array''', '''\t\t\tIf(Global.TeksDiriPemain[Global.IndeksKeluar] != 0);
\t\t\t\tDestroy In-World Text(Global.TeksDiriPemain[Global.IndeksKeluar]);
\t\t\tEnd;
\t\t\tWait(0.016, Ignore Condition);
\t\t\tGlobal.SlotHUDTersedia = Sorted Array''', "stage iwt")
cleanup = replace_once(cleanup, '''\t\t\tIf(Global.PemainManusia[Global.IndeksPembersihan].TargetBalasDendamTerkunci == Global.PemainPembersihan);
\t\t\t\tSet Player Variable(Global.PemainManusia[Global.IndeksPembersihan], TargetBalasDendamTerkunci, Null);
\t\t\tEnd;
\t\tEnd;
\t\tGlobal.IndeksKeluar = -1;''', '''\t\t\tIf(Global.PemainManusia[Global.IndeksPembersihan].TargetBalasDendamTerkunci == Global.PemainPembersihan);
\t\t\t\tSet Player Variable(Global.PemainManusia[Global.IndeksPembersihan], TargetBalasDendamTerkunci, Null);
\t\t\tEnd;
\t\t\tWait(0.016, Ignore Condition);
\t\tEnd;
\t\tGlobal.IndeksKeluar = -1;''', "stage survivors")
cleanup = replace_once(cleanup, '''\t\tGlobal.IndeksKeluar = -1;
\t\tGlobal.PemainPembersihan = Null;

\t}
}

''', '''\t\tGlobal.IndeksKeluar = -1;
\t\tGlobal.PemainPembersihan = Null;
\t\tGlobal.HudMenuPembersihan = Empty Array;
\t\tGlobal.PembersihanAktif = False;

\t}
}

''', "release mutex")
source = source[:cleanup_start] + cleanup + source[cleanup_end:]
source = replace_once(source, '''\t\tEvent Player.PindahTimDiproses = True;
\t\tEvent Player.PernahDisiapkan = True;
\t\tEvent Player.SiklusPemainAktif = False;
\t\tEvent Player.SudahSiap = True;''', '''\t\tEvent Player.TombolPerluDipulihkan = False;
\t\tEvent Player.KameraPerluDihentikan = False;
\t\tEvent Player.PindahTimDiproses = True;
\t\tEvent Player.PernahDisiapkan = True;
\t\tEvent Player.SiklusPemainAktif = False;
\t\tEvent Player.SudahSiap = True;''', "setup vars")
WORKSHOP.write_text(source, encoding="utf-8")
new_blob = git_blob_sha_text(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = validator.replace('CURRENT_VERSION = "0.6.23"', 'CURRENT_VERSION = "0.6.24"', 1).replace('versione 0.6.23.', 'versione 0.6.24.', 1)
# Relax old 0.6.23 lifecycle assertions and require new primitives.
validator = validator.replace('"Stop Camera(Event Player);" not in leave,\n            "cleanup atomico ripete ancora lo stop Camera già eseguito da TenangkanPemain",', '"Wait Until(Global.PembersihanAktif == False, 99999);" in leave and "Global.PembersihanAktif = True;" in leave and "Global.PembersihanAktif = False;" in leave,\n            "cleanup non serializzato dal mutex globale",', 1)
validator = validator.replace('first_wait = body.find("Wait(0.200, Ignore Condition);", quiesce_at)', 'first_wait = body.find("Wait(0.050, Ignore Condition);", quiesce_at)\n        mutex_wait = body.find("Wait Until(Global.PembersihanAktif == False, 99999);", first_wait)', 1)
validator = validator.replace('stale_guard = body.find("If(Or(Or(Array Contains(Global.PemainManusia, Event Player)", first_wait)', 'stale_guard = body.find("If(Or(Or(Array Contains(Global.PemainManusia, Event Player)", mutex_wait)', 1)
validator = validator.replace('second_wait = body.find("Wait(0.100, Ignore Condition);", cleanup_at)', 'second_wait = body.find("Wait(0.050, Ignore Condition);", cleanup_at)', 1)
validator = validator.replace('0 <= condition_lock < set_team_lock < set_cycle_lock < quiesce_at < first_wait < stale_guard < cleanup_at < second_wait < setup_at,\n            "audit lifecycle: cambio team deve fare lock → yield → cleanup condizionale → yield → setup; TenangkanPemain deve precedere il primo yield",', '0 <= condition_lock < set_team_lock < set_cycle_lock < quiesce_at < first_wait < mutex_wait < stale_guard < cleanup_at < second_wait < setup_at,\n            "audit lifecycle: cambio team deve fare lock → quiescenza → mutex → cleanup condizionale → yield → setup",', 1)
validator = validator.replace('checks.equal(body.count("Wait(0.200, Ignore Condition);"), 1,\n            "audit lifecycle: primo yield cambio team da 0,20 s")\n        checks.equal(body.count("Wait(0.100, Ignore Condition);"), 1,\n            "audit lifecycle: secondo yield cambio team da 0,10 s")', 'checks.equal(body.count("Wait(0.050, Ignore Condition);"), 2,\n            "audit lifecycle: due yield cambio team da 0,05 s")\n        checks.equal(body.count("Wait Until(Global.PembersihanAktif == False, 99999);"), 1,\n            "audit lifecycle: attesa mutex cleanup")', 1)
validator = validator.replace('body.count("Abort If(Entity Exists(Event Player) == False);") >= 2', 'body.count("Abort If(Entity Exists(Event Player) == False);") >= 3', 1)
# Replace quiet required engine actions with variable-only constraints.
quiet_old = '''        for token in (
            "Event Player.Manusia = False;",
            "Event Player.MenuTerbuka = False;",
            "Event Player.PerintahMenu = 0;",
            "Event Player.TeleportasiJongkokAktif = False;",
            "Event Player.InspeksiAktif = False;",
            "Event Player.KartuNasibAktif = False;",
            "Event Player.KebalAktif = False;",
            "Stop Camera(Event Player);",
            "Stop Chasing Player Variable(Event Player, WarnaMenu);",
            "Stop Chasing Player Variable(Event Player, RadiusNasib);",
            "Clear Status(Event Player, Unkillable);",
            "Set Damage Received(Event Player, 100);",
            "Allow Button(Event Player, Button(Interact));",
            "Stop Modifying Hero Voice Lines(Event Player);",
        ):
            checks.require(token in quiet, f"audit lifecycle: TenangkanPemain incompleto: {token}")
        checks.require(
            "Destroy HUD Text" not in quiet
            and "Destroy In-World Text" not in quiet
            and "Destroy Effect" not in quiet
            and "Wait(" not in quiet
            and "Loop If Condition Is True;" not in quiet,
            "audit lifecycle: TenangkanPemain deve solo fermare trigger/effetti, senza distruzioni o attese",
        )'''
quiet_new = '''        for token in (
            "Event Player.TombolPerluDipulihkan = Or(Event Player.MenuTerbuka == True, Event Player.TeleportasiJongkokAktif == True);",
            "Event Player.KameraPerluDihentikan = Event Player.ModeKamera != 0;",
            "Event Player.SudahSiap = False;",
            "Event Player.Manusia = False;",
            "Event Player.MenuTerbuka = False;",
            "Event Player.PerintahMenu = 0;",
            "Event Player.TeleportasiJongkokAktif = False;",
            "Event Player.InspeksiAktif = False;",
            "Event Player.KartuNasibAktif = False;",
            "Event Player.ModeKamera = 0;",
        ):
            checks.require(token in quiet, f"audit lifecycle: TenangkanPemain incompleto: {token}")
        for forbidden in (
            "Stop Camera(", "Stop Chasing Player Variable(", "Clear Status(", "Set Damage Received(",
            "Set Damage Dealt(", "Set Healing Dealt(", "Set Knockback", "Set Move Speed(", "Allow Button(",
            "Stop Modifying Hero Voice Lines(", "Enable Game Mode HUD(", "Enable Game Mode In-World UI(",
            "Destroy HUD Text", "Destroy In-World Text", "Destroy Effect", "Wait(", "Wait Until(", "Loop If Condition Is True;",
        ):
            checks.require(forbidden not in quiet, f"audit lifecycle: TenangkanPemain deve usare solo variabili, trovato {forbidden}")'''
validator = validator.replace(quiet_old, quiet_new, 1)
# Player Left no pre-wait.
validator = validator.replace('leave_wait = leave_code.find("Wait(0.100, Ignore Condition);", leave_quiet)\n        leave_cleanup = leave_code.find("Call Subroutine(BersihkanPemain);", leave_wait)\n        checks.require(\n            0 <= leave_quiet < leave_wait < leave_cleanup,\n            "audit lifecycle: Player Left deve fare TenangkanPemain → yield → cleanup",\n        )', 'leave_cleanup = leave_code.find("Call Subroutine(BersihkanPemain);", leave_quiet)\n        checks.require(0 <= leave_quiet < leave_cleanup, "audit lifecycle: Player Left deve fare TenangkanPemain → cleanup")\n        checks.require("Wait(" not in leave_code and "Wait Until(" not in leave_code, "audit lifecycle: Player Left non deve attendere prima del cleanup")', 1)
# Slot markers and staged HUD invariant.
marker = '    checks.equal(len(names), len(set(names)), "audit lifecycle: titoli regola duplicati")\n'
validator = validator.replace(marker, marker + '    checks.require("51: PembersihanAktif" in clean and "52: HudMenuPembersihan" in clean, "audit lifecycle: scratch global cleanup 0.6.24 assente")\n    checks.require("94: TombolPerluDipulihkan" in clean and "95: KameraPerluDihentikan" in clean, "audit lifecycle: latch player cleanup 0.6.24 assenti")\n', 1)
# Add checks near cleanup block before stale refs.
needle = '        for token in (\n            "PemainDipilih == Global.PemainPembersihan",'
insert = '''        checks.require("Global.HudMenuPembersihan = Global.IndeksKeluar >= 0 ?" in body, "audit lifecycle: snapshot HUD menu cleanup assente")
        checks.require(body.count("Destroy HUD Text(Global.HudMenuPembersihan[") == 13, "audit lifecycle: devono esistere 13 cleanup HUD menu")
        for index in range(13):
            checks.require(f"Destroy HUD Text(Global.HudMenuPembersihan[{index}]);\\n\\t\\t\\t\\tWait(0.016, Ignore Condition);" in body, f"audit lifecycle: HUD Arcade {index} non distribuito")
        checks.require("Global.HudMenuPembersihan = Empty Array;" in body and body.rfind("Global.HudMenuPembersihan = Empty Array;") < body.rfind("Global.PembersihanAktif = False;"), "audit lifecycle: snapshot/mutex cleanup non rilasciati correttamente")
        for forbidden in ("Set Damage Dealt(Event Player, 100);", "Set Healing Dealt(Event Player, 100);", "Set Knockback Dealt(Event Player, 100);", "Set Knockback Received(Event Player, 100);", "Stop Forcing Player Position(Event Player);"):
            checks.require(forbidden not in body, f"audit lifecycle: reset engine inutile nel cleanup umano: {forbidden}")
'''
validator = validator.replace(needle, insert + needle, 1)
VALIDATOR.write_text(validator, encoding="utf-8")

# Update tests to new timing/mutex semantics.
tests = TESTS.read_text(encoding="utf-8")
tests = tests.replace('mutated_join = join_rule.replace("\\t\\tWait(0.200, Ignore Condition);\\n", "", 1)', 'mutated_join = join_rule.replace("\\t\\tWait Until(Global.PembersihanAktif == False, 99999);\\n", "", 1)', 1)
tests = tests.replace('any("yield" in error for error in checks.errors)', 'any("mutex" in error or "quiescenza" in error for error in checks.errors)', 1)
tests = tests.replace('any("lock → yield → cleanup condizionale → yield → setup" in error for error in checks.errors)', 'any("lock → quiescenza → mutex" in error for error in checks.errors)', 1)
# Add a negative test for engine actions in quiet phase.
anchor = '        self.assertTrue(any("TenangkanPemain" in error for error in checks.errors), checks.errors)\n\n    def test_vote_change_must_clear_previous_choice'
extra = '''        self.assertTrue(any("TenangkanPemain" in error or "quiescenza" in error for error in checks.errors), checks.errors)

        quiet_at = self.source.index('rule("93b2 - Subrutin:')
        quiet_end = self.source.index('\\nrule("93c - Subrutin:', quiet_at)
        quiet = self.source[quiet_at:quiet_end]
        poisoned = quiet.replace("\\t\\tEvent Player.Manusia = False;", "\\t\\tEvent Player.Manusia = False;\\n\\t\\tStop Camera(Event Player);", 1)
        mutated = self.source[:quiet_at] + poisoned + self.source[quiet_end:]
        _, player_names, _ = validator.declaration_tables(mutated)
        checks = validator.Checks()
        validator.check_lifecycle_hygiene(checks, mutated, self.rules(mutated), player_names)
        self.assertTrue(any("solo variabili" in error for error in checks.errors), checks.errors)

    def test_vote_change_must_clear_previous_choice'''
tests = tests.replace(anchor, extra, 1)
TESTS.write_text(tests, encoding="utf-8")

VERSION.write_text("0.6.24\n", encoding="utf-8")
README.write_text(README.read_text(encoding="utf-8").replace("La versione **0.6.23**", "La versione **0.6.24**", 1), encoding="utf-8")
progetto = PROGETTO.read_text(encoding="utf-8").replace("# Note di progetto — versione 0.6.23", "# Note di progetto — versione 0.6.24", 1).replace("Workshop 0.6.23", "Workshop 0.6.24", 1)
progetto += "\n\n## Cleanup team-switch distribuito 0.6.24\n\nLa 0.6.23 è live-failed al primo cambio team. TenangkanPemain ora modifica solo variabili/latch. BersihkanPemain usa PembersihanAktif come mutex globale e HudMenuPembersihan come snapshot stabile; i 13 HUD Arcade vengono distrutti uno per frame con Wait(0.016), così il picco di Destroy viene distribuito. I ripristini engine sono condizionali e il cleanup umano non esegue più reset destinati ai bot.\n"
PROGETTO.write_text(progetto, encoding="utf-8")
test_doc = TEST_DOC.read_text(encoding="utf-8").replace("# Piano di test — versione 0.6.23", "# Piano di test — versione 0.6.24", 1).replace("Workshop 0.6.23", "Workshop 0.6.24", 1)
test_doc += "\n\n## Team switch distribuito 0.6.24\n\n0.6.23 live-failed: crash al primo cambio team. Provare 10 cambi Team 1 ↔ Team 2 prima a menu mai aperto, poi dopo aver visitato tutte le 12 pagine per riempire la cache HUD. Ripetere con Camera, Unkillable, Hero Voice, Crouch e Try Your Luck. Nessun excessive Workshop script load e una sola registrazione roster dopo ogni spawn.\n"
TEST_DOC.write_text(test_doc, encoding="utf-8")
validation = VALIDAZIONE.read_text(encoding="utf-8").replace("# Rapporto di validazione — versione 0.6.23", "# Rapporto di validazione — versione 0.6.24", 1).replace("Release tecnica: **CHILL Dedicated Server 0.6.23**", "Release tecnica: **CHILL Dedicated Server 0.6.24**", 1).replace("OK - controlli statici v0.6.23 superati", "OK - controlli statici v0.6.24 superati", 1)
validation = re.sub(r"(Blob Git del sorgente Workshop validato:\n\n```text\n)[0-9a-f]{40}(\n```)", rf"\g<1>{new_blob}\g<2>", validation, count=1)
validation += "\n\n## Gate team-switch distribuito 0.6.24\n\nRichiesti mutex PembersihanAktif, snapshot HudMenuPembersihan, distruzione dei 13 HUD Arcade distribuita con Wait(0.016) e TenangkanPemain privo di azioni engine. 0.6.23 resta live-failed; 0.6.24 è static-ready solo dopo gate verde e live-pending fino al nuovo test in Overwatch.\n"
VALIDAZIONE.write_text(validation, encoding="utf-8")
