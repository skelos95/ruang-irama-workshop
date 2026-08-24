from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


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
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return i
    raise RuntimeError("unclosed brace")


def replace_rule(text: str, keyword: str, name: str, replacement: str) -> str:
    marker = f'{keyword}("{name}")'
    start = text.find(marker)
    if start < 0:
        raise RuntimeError(f"rule not found: {name}")
    opening = text.find('{', start)
    end = matching_brace(text, opening) + 1
    return text[:start] + replacement.rstrip() + text[end:]


def get_rule(text: str, keyword: str, name: str):
    marker = f'{keyword}("{name}")'
    start = text.find(marker)
    if start < 0:
        raise RuntimeError(f"rule not found: {name}")
    opening = text.find('{', start)
    end = matching_brace(text, opening) + 1
    return start, end, text[start:end]


def update_rule(text: str, keyword: str, name: str, fn) -> str:
    start, end, block = get_rule(text, keyword, name)
    return text[:start] + fn(block) + text[end:]


def add_condition(block: str, section: str, condition: str) -> str:
    marker = f"\t{section}\n\t{{"
    pos = block.find(marker)
    if pos < 0:
        raise RuntimeError(f"section {section} missing")
    opening = block.find('{', pos)
    closing = matching_brace(block, opening)
    body = block[opening + 1:closing]
    if condition in body:
        return block
    return block[:closing] + f"\n\t\t{condition}" + block[closing:]


def patch_workshop(path: Path, italian: bool) -> None:
    text = path.read_text(encoding="utf-8")
    keyword = "regola" if italian else "rule"
    event = "evento" if italian else "event"
    conditions = "condizioni" if italian else "conditions"
    actions = "azioni" if italian else "actions"
    all_word = "Tutti" if italian else "All"
    glob = "Globale" if italian else "Global"
    ignore = "Ignora condizione" if italian else "Ignore Condition"

    decl_old = "\t\t102: PahlawanLampiranTarget\n"
    decl_new = decl_old + "\t\t103: WaktuSiklusTim\n"
    if text.count(decl_old) != 1:
        raise RuntimeError(f"unexpected declaration count in {path}")
    text = text.replace(decl_old, decl_new, 1)

    old_01 = "01 - Pemain Masuk atau Pindah Tim: Tunggu pembersihan lalu masuk kembali"
    worker_cleanup = f'''{keyword}("01 - Lifecycle tim: Worker cleanup dari scheduler global")
{{
\t{event}
\t{{
\t\tOngoing - Each Player;
\t\t{all_word};
\t\t{all_word};
\t}}

\t{conditions}
\t{{
\t\tIs Dummy Bot(Event Player) == False;
\t\tEvent Player.BotOtomatis == False;
\t\tEvent Player.PindahTimDiproses == True;
\t\tEvent Player.SiklusPemainAktif == True;
\t\tEvent Player.SudahSiap == False;
\t\tTotal Time Elapsed >= Event Player.WaktuSiklusTim;
\t\tServer Load < 150;
\t}}

\t{actions}
\t{{
\t\tCall Subroutine(TenangkanPemain);
\t\tIf(Or(Array Contains({glob}.PemainManusia, Event Player), And(Event Player.PernahDisiapkan == True, Array Contains({glob}.SlotHUDPemain, Event Player.UrutanHUD))));
\t\t\tCall Subroutine(BersihkanPemain);
\t\tEnd;
\t\tEvent Player.SiklusPemainAktif = False;
\t\tEvent Player.WaktuSiklusTim = Total Time Elapsed + 0.100;
\t}}
}}'''
    text = replace_rule(text, keyword, old_01, worker_cleanup)

    old_01b = "01b - Pemain Lama: Siapkan juga yang sudah telanjur ada"
    worker_setup = f'''{keyword}("01b - Lifecycle tim: Worker setup dari scheduler global")
{{
\t{event}
\t{{
\t\tOngoing - Each Player;
\t\t{all_word};
\t\t{all_word};
\t}}

\t{conditions}
\t{{
\t\tIs Dummy Bot(Event Player) == False;
\t\tEvent Player.BotOtomatis == False;
\t\tEvent Player.PindahTimDiproses == True;
\t\tEvent Player.SiklusPemainAktif == False;
\t\tEvent Player.SudahSiap == False;
\t\tTotal Time Elapsed >= Event Player.WaktuSiklusTim;
\t\tServer Load < 150;
\t}}

\t{actions}
\t{{
\t\tCall Subroutine(SiapkanPemain);
\t}}
}}'''
    text = replace_rule(text, keyword, old_01b, worker_setup)

    old_04 = "04 - Pemain Keluar: Tenangkan lalu bersihkan pendaftaran"
    left_rule = f'''{keyword}("04 - Pemain Keluar: Cleanup hanya jika benar-benar keluar")
{{
\t{event}
\t{{
\t\tPlayer Left Match;
\t\t{all_word};
\t\t{all_word};
\t}}

\t{conditions}
\t{{
\t\tIs Dummy Bot(Event Player) == False;
\t\tOr(Event Player.BotOtomatis == True, Or(Event Player.Manusia == True, Array Contains({glob}.PemainManusia, Event Player))) == True;
\t}}

\t{actions}
\t{{
\t\tIf(Event Player.BotOtomatis == True);
\t\t\tIf(Event Player.TeksVisiNasib != Null);
\t\t\t\tDestroy In-World Text(Event Player.TeksVisiNasib);
\t\t\tEnd;
\t\t\tEvent Player.TeksVisiNasib = Null;
\t\t\tAbort;
\t\tEnd;
\t\tWait(0.100, {ignore});
\t\tAbort If(And(Entity Exists(Event Player) == True, Event Player.TimTerakhir != Team Of(Event Player)));
\t\tCall Subroutine(TenangkanPemain);
\t\tCall Subroutine(BersihkanPemain);
\t}}
}}'''
    text = replace_rule(text, keyword, old_04, left_rule)

    def patch_fast(block: str) -> str:
        marker = f"\t{actions}\n\t{{\n"
        if marker not in block:
            raise RuntimeError("fast actions marker missing")
        detector = (
            f"\t\tIf(And(Is Dummy Bot({glob}.PemainAktif) == False, And({glob}.PemainAktif.BotOtomatis == False, And({glob}.PemainAktif.PindahTimDiproses == False, "
            f"Or(And({glob}.PemainAktif.PernahDisiapkan == False, {glob}.PemainAktif.SudahSiap == False), And({glob}.PemainAktif.PernahDisiapkan == True, {glob}.PemainAktif.TimTerakhir != Team Of({glob}.PemainAktif)))))));\n"
            f"\t\t\t{glob}.PemainAktif.PindahTimDiproses = True;\n"
            f"\t\t\t{glob}.PemainAktif.SiklusPemainAktif = {glob}.PemainAktif.PernahDisiapkan == True;\n"
            f"\t\t\t{glob}.PemainAktif.SudahSiap = False;\n"
            f"\t\t\t{glob}.PemainAktif.Manusia = False;\n"
            f"\t\t\t{glob}.PemainAktif.WaktuSiklusTim = Total Time Elapsed + 0.100;\n"
            f"\t\tEnd;\n"
        )
        return block.replace(marker, marker + detector, 1)
    text = update_rule(text, keyword, "89a - Subrutin: Proses status cepat pemain", patch_fast)

    def patch_cycle(block: str) -> str:
        token = f"\t\t\t{glob}.PemainAktif.PindahTimDiproses = False;"
        repl = token + f"\n\t\t\t{glob}.PemainAktif.SiklusPemainAktif = False;\n\t\t\t{glob}.PemainAktif.WaktuSiklusTim = 0;"
        if block.count(token) != 1:
            raise RuntimeError("team lock release count mismatch")
        return block.replace(token, repl, 1)
    text = update_rule(text, keyword, "89b - Subrutin: Proses siklus pemain 10 Hz", patch_cycle)

    def slim_quiet(block: str) -> str:
        token = "\t\tCall Subroutine(PulihkanNasibPemain);\n"
        if block.count(token) != 1:
            raise RuntimeError("quiet luck reset call mismatch")
        return block.replace(token, "", 1)
    text = update_rule(text, keyword, "93b2 - Subrutin: Tenangkan pemicu sebelum pembersihan", slim_quiet)

    def init_time(block: str) -> str:
        token = "\t\tEvent Player.PahlawanLampiranTarget = Null;\n"
        if block.count(token) != 1:
            raise RuntimeError("setup attach tail mismatch")
        return block.replace(token, token + "\t\tEvent Player.WaktuSiklusTim = 0;\n", 1)
    text = update_rule(text, keyword, "94 - Subrutin: Siapkan pemain dari ujung rambut sampai variabel", init_time)

    for rule_name in (
        "02 - Pemain: Pisahkan manusia dari pasukan kaleng",
        "02b - HUD Pemain: Buat segera setelah klasifikasi selesai",
    ):
        text = update_rule(text, keyword, rule_name, lambda b, s=conditions: add_condition(b, s, "Server Load < 150;"))

    path.write_text(text, encoding="utf-8")


patch_workshop(ROOT / "workshop/ruang_irama.it-IT.workshop", True)
patch_workshop(ROOT / "tests/fixtures/semantic_reference.txt", False)

# Validator: team lifecycle must be global-first, with only true leaves owning Player Left cleanup.
validator_path = ROOT / "tools/validate_workshop.py"
v = validator_path.read_text(encoding="utf-8")

old_wait = '''    expected_wait_signatures: Counter[tuple[str | None, tuple[str, ...]]] = Counter({
        ("scheduler", ("0.050", "Ignore Condition")): 1,
        ("join ordering", ("0.050", "Ignore Condition")): 2,
        ("leave ordering", ("0.050", "Ignore Condition")): 1,
        ("bot classification", ("0.016", "Ignore Condition")): 1,
        ("menu hold", ("0.500", "Abort When False")): 1,
        ("camera hold", ("0.500", "Abort When False")): 1,
    })'''
new_wait = '''    expected_wait_signatures: Counter[tuple[str | None, tuple[str, ...]]] = Counter({
        ("scheduler", ("0.050", "Ignore Condition")): 1,
        ("leave ordering", ("0.100", "Ignore Condition")): 1,
        ("bot classification", ("0.016", "Ignore Condition")): 1,
        ("menu hold", ("0.500", "Abort When False")): 1,
        ("camera hold", ("0.500", "Abort When False")): 1,
    })'''
if v.count(old_wait) != 1:
    raise RuntimeError("validator wait signature block mismatch")
v = v.replace(old_wait, new_wait, 1)

# Replace the old Player Joined ownership contract at the start of validate_lifecycle.
pattern = re.compile(
    r'    joined = rules_with_event\(rules, "Player Joined Match"\)\n'
    r'    left = rules_with_event\(rules, "Player Left Match"\)\n'
    r'    checks\.equal\(len\(joined\), 1, "regola Player Joined Match unica"\)\n'
    r'    checks\.equal\(len\(left\), 1, "regola Player Left Match unica"\)\n'
    r'    if joined:\n.*?'
    r'(?=    if left:)',
    re.DOTALL,
)
replacement = '''    joined = rules_with_event(rules, "Player Joined Match")
    left = rules_with_event(rules, "Player Left Match")
    checks.equal(len(joined), 0, "lifecycle join/team-switch deve essere global-first senza Player Joined Match")
    checks.equal(len(left), 1, "regola Player Left Match unica")
'''
v, count = pattern.subn(replacement, v, count=1)
if count != 1:
    raise RuntimeError(f"validator lifecycle joined block mismatch: {count}")

# Strengthen the left rule contract with the team-switch abort gate and timestamp ordering.
needle = '        checks.require("Call Subroutine(TenangkanPemain);" in body and "Call Subroutine(BersihkanPemain);" in body,\n                       "leave non esegue quiete + cleanup")\n'
extra = needle + '''        checks.require("Wait(0.100, Ignore Condition);" in body,
                       "leave deve distinguere una vera uscita dal cambio squadra con 0,100 s")
        checks.require("Abort If(And(Entity Exists(Event Player) == True, Event Player.TimTerakhir != Team Of(Event Player)));" in body,
                       "leave non delega il cambio squadra al lifecycle globale")
'''
if v.count(needle) != 1:
    raise RuntimeError("validator left contract mismatch")
v = v.replace(needle, extra, 1)

# Insert global-first lifecycle checks immediately after cycle discovery.
needle = '    cycle = rule_by_subroutine(rules, "ProsesSiklusPemain")\n    checks.require(cycle is not None, "ProsesSiklusPemain assente")\n'
insert = needle + '''    fast = rule_by_subroutine(rules, "ProsesCepatPemain")
    checks.require(fast is not None, "dispatcher lifecycle globale ProsesCepatPemain assente")
    if fast:
        for token in (
            "Global.PemainAktif.PindahTimDiproses == False",
            "Global.PemainAktif.PernahDisiapkan == False",
            "Global.PemainAktif.TimTerakhir != Team Of(Global.PemainAktif)",
            "Global.PemainAktif.PindahTimDiproses = True;",
            "Global.PemainAktif.SiklusPemainAktif = Global.PemainAktif.PernahDisiapkan == True;",
            "Global.PemainAktif.SudahSiap = False;",
            "Global.PemainAktif.Manusia = False;",
            "Global.PemainAktif.WaktuSiklusTim = Total Time Elapsed + 0.100;",
        ):
            checks.require(token in fast.body, f"dispatcher lifecycle globale incompleto: {token}")

    cleanup_worker = next((
        rule for rule in rules
        if event_type(rule) == "Ongoing - Each Player"
        and "Call Subroutine(BersihkanPemain);" in rule.body
        and "Event Player.WaktuSiklusTim" in rule.body
    ), None)
    setup_worker = next((
        rule for rule in rules
        if event_type(rule) == "Ongoing - Each Player"
        and "Call Subroutine(SiapkanPemain);" in rule.body
        and "Event Player.WaktuSiklusTim" in rule.body
    ), None)
    checks.require(cleanup_worker is not None, "worker cleanup lifecycle accodato dal globale assente")
    checks.require(setup_worker is not None, "worker setup lifecycle accodato dal globale assente")
    if cleanup_worker:
        cleanup_conditions = rule_block(cleanup_worker, "conditions") or ""
        for token in (
            "Event Player.PindahTimDiproses == True;",
            "Event Player.SiklusPemainAktif == True;",
            "Event Player.SudahSiap == False;",
            "Total Time Elapsed >= Event Player.WaktuSiklusTim;",
            "Server Load < 150;",
        ):
            checks.require(token in cleanup_conditions, f"worker cleanup lifecycle senza guardia: {token}")
        checks.require(not wait_calls(cleanup_worker.body), "worker cleanup lifecycle non deve usare Wait")
        checks.require("Event Player.SiklusPemainAktif = False;" in cleanup_worker.body,
                       "worker cleanup non passa alla fase setup")
        checks.require("Event Player.WaktuSiklusTim = Total Time Elapsed + 0.100;" in cleanup_worker.body,
                       "worker cleanup non separa cleanup/setup di 0,100 s")
    if setup_worker:
        setup_conditions = rule_block(setup_worker, "conditions") or ""
        for token in (
            "Event Player.PindahTimDiproses == True;",
            "Event Player.SiklusPemainAktif == False;",
            "Event Player.SudahSiap == False;",
            "Total Time Elapsed >= Event Player.WaktuSiklusTim;",
            "Server Load < 150;",
        ):
            checks.require(token in setup_conditions, f"worker setup lifecycle senza guardia: {token}")
        checks.require(not wait_calls(setup_worker.body), "worker setup lifecycle non deve usare Wait")

    quiet = rule_by_subroutine(rules, "TenangkanPemain")
    if quiet:
        checks.require("Call Subroutine(PulihkanNasibPemain);" not in quiet.body,
                       "TenangkanPemain non deve duplicare il reset pesante già eseguito da BersihkanPemain")
'''
if v.count(needle) != 1:
    raise RuntimeError("validator cycle insertion point mismatch")
v = v.replace(needle, insert, 1)

# Release must clear both phase and timestamp after stable classification/HUD.
needle = '            (r"Global\\.PemainAktif\\.PindahTimDiproses\\s*=\\s*False;", "rilascio PindahTimDiproses"),\n'
repl = needle + '            (r"Global\\.PemainAktif\\.SiklusPemainAktif\\s*=\\s*False;", "rilascio fase lifecycle"),\n            (r"Global\\.PemainAktif\\.WaktuSiklusTim\\s*=\\s*0;", "rilascio timestamp lifecycle"),\n'
if v.count(needle) != 1:
    raise RuntimeError("validator stable pattern insertion mismatch")
v = v.replace(needle, repl, 1)

# Bot isolation must inspect the global dispatcher instead of a removed Player Joined rule.
old = '''    joined = rules_with_event(rules, "Player Joined Match")
    if joined:
        checks.require("Is Dummy Bot(Event Player) == False;" in joined[0].body,
                       "join/team-switch umano non esclude dummy nativi")
        checks.require("Event Player.BotOtomatis == False;" in joined[0].body,
                       "join/team-switch umano può riattivare il lifecycle di un iBot")
'''
new = '''    lifecycle_dispatcher = rule_by_subroutine(rules, "ProsesCepatPemain")
    if lifecycle_dispatcher:
        checks.require("Is Dummy Bot(Global.PemainAktif) == False" in lifecycle_dispatcher.body,
                       "dispatcher lifecycle globale non esclude dummy nativi")
        checks.require("Global.PemainAktif.BotOtomatis == False" in lifecycle_dispatcher.body,
                       "dispatcher lifecycle globale può riattivare il lifecycle di un iBot")
'''
if v.count(old) != 1:
    raise RuntimeError("validator bot isolation joined block mismatch")
v = v.replace(old, new, 1)

validator_path.write_text(v, encoding="utf-8")

# Update negative lifecycle tests that previously mutated Player Joined Match.
test_path = ROOT / "tests/test_validate_workshop.py"
t = test_path.read_text(encoding="utf-8")
pat = re.compile(r'    def test_join_requires_duplicate_guard\(self\) -> None:\n.*?(?=    def test_team_switch_lifecycle_excludes_classified_ibots)', re.DOTALL)
rep = '''    def test_global_lifecycle_dispatch_requires_duplicate_guard(self) -> None:
        fast = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesCepatPemain")
        mutated = self.replace_in_rule(
            fast,
            "Global.PemainAktif.PindahTimDiproses == False",
            "Global.PemainAktif.PindahTimDiproses == True",
        )
        self.assert_rejected(mutated, "dispatcher lifecycle globale")

'''
t, count = pat.subn(rep, t, count=1)
if count != 1:
    raise RuntimeError("test join guard method mismatch")
pat = re.compile(r'    def test_team_switch_lifecycle_excludes_classified_ibots\(self\) -> None:\n.*?(?=    def test_leave_cleanup_is_limited_to_the_human_roster)', re.DOTALL)
rep = '''    def test_global_lifecycle_dispatch_excludes_classified_ibots(self) -> None:
        fast = self.rule(lambda rule: validator.subroutine_target(rule) == "ProsesCepatPemain")
        mutated = self.replace_in_rule(
            fast,
            "Global.PemainAktif.BotOtomatis == False",
            "Global.PemainAktif.BotOtomatis == True",
        )
        self.assert_rejected(mutated, "dispatcher lifecycle globale")

'''
t, count = pat.subn(rep, t, count=1)
if count != 1:
    raise RuntimeError("test team switch ibot method mismatch")
test_path.write_text(t, encoding="utf-8")

# Add focused runtime coverage.
runtime_path = ROOT / "tests/test_runtime_maintenance.py"
r = runtime_path.read_text(encoding="utf-8")
method = r'''
    def test_team_switch_lifecycle_is_global_first_and_load_guarded(self):
        for source, global_name, rule_kw in ((self.it, "Globale", "regola"), (self.en, "Global", "rule")):
            self.assertNotIn("Player Joined Match;", source)
            fast = source.split(f'{rule_kw}("89a - Subrutin: Proses status cepat pemain")', 1)[1].split(f'{rule_kw}("89b - Subrutin: Proses siklus pemain 10 Hz")', 1)[0]
            self.assertIn(f"{global_name}.PemainAktif.TimTerakhir != Team Of({global_name}.PemainAktif)", fast)
            self.assertIn(f"{global_name}.PemainAktif.PindahTimDiproses = True;", fast)
            self.assertIn(f"{global_name}.PemainAktif.WaktuSiklusTim = Total Time Elapsed + 0.100;", fast)

            cleanup = source.split(f'{rule_kw}("01 - Lifecycle tim: Worker cleanup dari scheduler global")', 1)[1].split(f'{rule_kw}("01b - Lifecycle tim: Worker setup dari scheduler global")', 1)[0]
            self.assertIn("Event Player.SiklusPemainAktif == True;", cleanup)
            self.assertIn("Server Load < 150;", cleanup)
            self.assertIn("Event Player.WaktuSiklusTim = Total Time Elapsed + 0.100;", cleanup)
            self.assertNotIn("Wait(", cleanup)

            setup = source.split(f'{rule_kw}("01b - Lifecycle tim: Worker setup dari scheduler global")', 1)[1].split(f'{rule_kw}("02 - Pemain: Pisahkan manusia dari pasukan kaleng")', 1)[0]
            self.assertIn("Event Player.SiklusPemainAktif == False;", setup)
            self.assertIn("Server Load < 150;", setup)
            self.assertNotIn("Wait(", setup)

            left = source.split(f'{rule_kw}("04 - Pemain Keluar: Cleanup hanya jika benar-benar keluar")', 1)[1].split(f'{rule_kw}("04g - Utama global: Penjadwal pusat 20 Hz")', 1)[0]
            self.assertIn("0.100", left)
            self.assertIn("Event Player.TimTerakhir != Team Of(Event Player)", left)
'''
if "test_team_switch_lifecycle_is_global_first_and_load_guarded" not in r:
    marker = '\nif __name__ == "__main__":'
    if marker not in r:
        raise RuntimeError("runtime test insertion marker missing")
    r = r.replace(marker, "\n" + method + marker, 1)
runtime_path.write_text(r, encoding="utf-8")

# Changelog note.
changelog = ROOT / "CHANGELOG.md"
c = changelog.read_text(encoding="utf-8")
entry = "- Cambio squadra reso global-first: il scheduler globale accoda il lifecycle, cleanup e setup sono separati da timestamp da 0,1 s e protetti da Server Load; Player Left evita il doppio cleanup quando l'entità esiste ancora sulla nuova squadra.\n"
anchor = "## 0.7.2 — baseline"
if entry not in c:
    c = c.replace(anchor, entry + "\n" + anchor, 1)
changelog.write_text(c, encoding="utf-8")

print("Applied global-first team-switch lifecycle and load guards")
