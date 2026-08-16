from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "workshop" / "ruang_irama.workshop"
VAL = ROOT / "tools" / "validate_workshop.py"
TESTS = ROOT / "tests" / "test_validate_workshop.py"
README = ROOT / "README.md"
PROGETTO = ROOT / "docs" / "PROGETTO.md"
TEST_DOC = ROOT / "docs" / "TEST.md"
VALIDAZIONE = ROOT / "docs" / "VALIDAZIONE.md"
VERSION = ROOT / "VERSION"


def once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected 1 occurrence, found {count}")
    return text.replace(old, new, 1)


src = SRC.read_text(encoding="utf-8")
src = once(src, "\t\t50: ModeMulaiDiminta\n\tplayer:\n", "\t\t50: ModeMulaiDiminta\n\t\t51: IndeksSinkronTim\n\tplayer:\n", "global sync index")
src = once(src, "\t\t92: PernahDisiapkan\n}\n", "\t\t92: PernahDisiapkan\n\t\t93: AntarmukaModeDiterapkan\n}\n", "UI latch")
src = once(src, "\t\tGlobal.ModeMulaiDiminta = False;\n\t\tGlobal.RGBFase = 0;\n", "\t\tGlobal.ModeMulaiDiminta = False;\n\t\tGlobal.IndeksSinkronTim = -1;\n\t\tGlobal.RGBFase = 0;\n", "sync index init")

old_join = '''rule("01 - Pemain Masuk atau Pindah Tim: Jangan bangun ulang pemain yang sudah terdaftar")
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
\t}

\tactions
\t{
\t\t"Pindah tim mempertahankan HUD, menu, pilihan, dan pendaftaran. Pembersihan penuh hanya untuk pemain yang benar-benar keluar."
\t\tIf(Array Contains(Global.PemainManusia, Event Player));
\t\t\t"Overwatch membuang dua HUD roster yang dibuat dari konteks pemain saat pindah tim. Jangan cleanup penuh: kosongkan hanya ID lama lalu biarkan 02b membuat dua baris lagi."
\t\t\tGlobal.HudKiriPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = 0;
\t\t\tGlobal.HudKananPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = 0;
\t\t\tEvent Player.HudKiri = Null;
\t\t\tEvent Player.HudKanan = Null;
\t\t\tEvent Player.HudPemainDibuat = False;
\t\t\tEvent Player.SiklusPemainAktif = False;
\t\t\tEvent Player.SudahSiap = True;
\t\t\tEvent Player.SudahDiperiksa = True;
\t\t\tEvent Player.Manusia = True;
\t\t\tDisable Game Mode HUD(Event Player);
\t\t\tDisable Game Mode In-World UI(Event Player);
\t\t\tAbort;
\t\tEnd;
\t\tAbort If(Event Player.SiklusPemainAktif == True);
\t\tEvent Player.SiklusPemainAktif = True;
\t\tCall Subroutine(SiapkanPemain);
\t}
}
'''
new_join = '''rule("01 - Pemain Masuk atau Pindah Tim: Sinkronkan pemain tanpa bangun ulang")
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
\t}

\tactions
\t{
\t\t"Cari referensi yang masih aktif lebih dulu. Jika Overwatch mengganti konteks pemain saat pindah tim, slot HUD lama menjadi kunci cadangan yang stabil."
\t\tGlobal.IndeksSinkronTim = Index Of Array Value(Global.PemainManusia, Event Player);
\t\tIf(And(Global.IndeksSinkronTim < 0, Event Player.PernahDisiapkan == True));
\t\t\tGlobal.IndeksSinkronTim = Index Of Array Value(Global.SlotHUDPemain, Event Player.UrutanHUD);
\t\tEnd;
\t\tIf(Global.IndeksSinkronTim >= 0);
\t\t\tGlobal.PemainManusia[Global.IndeksSinkronTim] = Event Player;
\t\t\tGlobal.HudKiriPemain[Global.IndeksSinkronTim] = 0;
\t\t\tGlobal.HudKananPemain[Global.IndeksSinkronTim] = 0;
\t\t\tEvent Player.HudKiri = Null;
\t\t\tEvent Player.HudKanan = Null;
\t\t\tEvent Player.HudPemainDibuat = False;
\t\t\tEvent Player.AntarmukaModeDiterapkan = False;
\t\t\tEvent Player.SiklusPemainAktif = False;
\t\t\tEvent Player.SudahSiap = True;
\t\t\tEvent Player.SudahDiperiksa = True;
\t\t\tEvent Player.Manusia = True;
\t\t\tGlobal.IndeksSinkronTim = -1;
\t\t\tAbort;
\t\tEnd;
\t\tGlobal.IndeksSinkronTim = -1;
\t\tAbort If(Event Player.SiklusPemainAktif == True);
\t\tEvent Player.SiklusPemainAktif = True;
\t\tCall Subroutine(SiapkanPemain);
\t}
}
'''
src = once(src, old_join, new_join, "team reference sync")

src = once(src,
    "\t\tDisable Game Mode HUD(Event Player);\n\t\tDisable Game Mode In-World UI(Event Player);\n\t\tEvent Player.IndeksGenre = -1;\n",
    "\t\tDisable Game Mode HUD(Event Player);\n\t\tDisable Game Mode In-World UI(Event Player);\n\t\tEvent Player.AntarmukaModeDiterapkan = True;\n\t\tEvent Player.IndeksGenre = -1;\n",
    "initial UI applied latch")

post_spawn = '''rule("02d - Antarmuka: Terapkan kembali setelah pemain muncul")
{
\tevent
\t{
\t\tOngoing - Each Player;
\t\tAll;
\t\tAll;
\t}

\tconditions
\t{
\t\tGlobal.Siap == True;
\t\tEvent Player.Manusia == True;
\t\tIs Dummy Bot(Event Player) == False;
\t\tHas Spawned(Event Player) == True;
\t\tEvent Player.AntarmukaModeDiterapkan == False;
\t}

\tactions
\t{
\t\t"Jangan ubah antarmuka bawaan ketika layar pemilihan pahlawan masih aktif. Terapkan kembali hanya sesudah pemain benar-benar muncul."
\t\tDisable Game Mode HUD(Event Player);
\t\tDisable Game Mode In-World UI(Event Player);
\t\tEvent Player.AntarmukaModeDiterapkan = True;
\t}
}

'''
src = once(src, 'rule("03 - Waktu: Hitung menit nongkrong tanpa bikin server ngos-ngosan")', post_spawn + 'rule("03 - Waktu: Hitung menit nongkrong tanpa bikin server ngos-ngosan")', "post-spawn UI rule")
src = once(src,
    "\t\tEvent Player.PernahDisiapkan = True;\n\t\tEvent Player.SiklusPemainAktif = False;\n",
    "\t\tEvent Player.PernahDisiapkan = True;\n\t\tEvent Player.AntarmukaModeDiterapkan = False;\n\t\tEvent Player.SiklusPemainAktif = False;\n",
    "fresh UI latch init")
SRC.write_text(src, encoding="utf-8")

val = VAL.read_text(encoding="utf-8")
val = once(val, "della versione 0.6.19.", "della versione 0.6.20.", "validator doc version")
val = once(val, 'CURRENT_VERSION = "0.6.19"', 'CURRENT_VERSION = "0.6.20"', "validator version")
old_audit = '''    if join:
        body = mask_strings(join[0].body)
        duplicate_at = body.find("If(Array Contains(Global.PemainManusia, Event Player));")
        abort_registered = body.find("Abort;", duplicate_at)
        setup_at = body.find("Call Subroutine(SiapkanPemain);", abort_registered)
        checks.require(
            0 <= duplicate_at < abort_registered < setup_at,
            "audit lifecycle: player già registrato non esce prima del setup",
        )
        checks.require(
            "Call Subroutine(BersihkanPemain);" not in body,
            "audit lifecycle: cambio team esegue ancora cleanup completo",
        )
        checks.require(
            "Destroy HUD Text" not in body and "Create HUD Text" not in body,
            "audit lifecycle: cambio team crea/distrugge HUD direttamente",
        )
        social_rearm_tokens = (
            "Global.HudKiriPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = 0;",
            "Global.HudKananPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = 0;",
            "Event Player.HudKiri = Null;",
            "Event Player.HudKanan = Null;",
            "Event Player.HudPemainDibuat = False;",
        )
        social_rearm_positions = [body.find(token, duplicate_at) for token in social_rearm_tokens]
        checks.require(
            all(duplicate_at < position < abort_registered for position in social_rearm_positions),
            "audit lifecycle: cambio team non riarma i due HUD sociali prima dell'uscita leggera",
        )
        for token in (
            "Event Player.SudahSiap = True;",
            "Event Player.SudahDiperiksa = True;",
            "Event Player.Manusia = True;",
            "Disable Game Mode HUD(Event Player);",
            "Disable Game Mode In-World UI(Event Player);",
        ):
            checks.require(token in body, f"audit lifecycle: refresh leggero cambio team incompleto: {token}")
'''
new_audit = '''    if join:
        body = mask_strings(join[0].body)
        direct_lookup = body.find("Global.IndeksSinkronTim = Index Of Array Value(Global.PemainManusia, Event Player);")
        slot_lookup = body.find("Global.IndeksSinkronTim = Index Of Array Value(Global.SlotHUDPemain, Event Player.UrutanHUD);")
        registered_at = body.find("If(Global.IndeksSinkronTim >= 0);")
        replace_ref = body.find("Global.PemainManusia[Global.IndeksSinkronTim] = Event Player;", registered_at)
        abort_registered = body.find("Abort;", registered_at)
        setup_at = body.find("Call Subroutine(SiapkanPemain);", abort_registered)
        checks.require(0 <= direct_lookup < slot_lookup < registered_at < replace_ref < abort_registered < setup_at,
            "audit lifecycle: cambio team non sincronizza il riferimento roster prima del ramo leggero")
        checks.require("Event Player.PernahDisiapkan == True" in body,
            "audit lifecycle: fallback per slot non è limitato a player già inizializzati")
        checks.require("Call Subroutine(BersihkanPemain);" not in body,
            "audit lifecycle: cambio team esegue ancora cleanup completo")
        checks.require("Destroy HUD Text" not in body and "Create HUD Text" not in body,
            "audit lifecycle: cambio team crea/distrugge HUD direttamente")
        tokens = (
            "Global.HudKiriPemain[Global.IndeksSinkronTim] = 0;",
            "Global.HudKananPemain[Global.IndeksSinkronTim] = 0;",
            "Event Player.HudKiri = Null;", "Event Player.HudKanan = Null;",
            "Event Player.HudPemainDibuat = False;", "Event Player.AntarmukaModeDiterapkan = False;",
        )
        checks.require(all(registered_at < body.find(token, registered_at) < abort_registered for token in tokens),
            "audit lifecycle: cambio team non riarma roster/UI prima dell'uscita leggera")
        checks.require("Disable Game Mode HUD(Event Player);" not in body and "Disable Game Mode In-World UI(Event Player);" not in body,
            "audit lifecycle: cambio team modifica la UI nativa durante la selezione eroe")
        for token in ("Event Player.SudahSiap = True;", "Event Player.SudahDiperiksa = True;", "Event Player.Manusia = True;"):
            checks.require(token in body, f"audit lifecycle: refresh leggero cambio team incompleto: {token}")

    post_spawn_ui = [rule for rule in rules if rule.name.startswith("02d - Antarmuka:")]
    checks.equal(len(post_spawn_ui), 1, "audit lifecycle: riapplicazione UI post-spawn")
    if post_spawn_ui:
        ui_body = mask_strings(post_spawn_ui[0].body)
        for token in ("Event Player.Manusia == True;", "Has Spawned(Event Player) == True;",
                      "Event Player.AntarmukaModeDiterapkan == False;", "Disable Game Mode HUD(Event Player);",
                      "Disable Game Mode In-World UI(Event Player);", "Event Player.AntarmukaModeDiterapkan = True;"):
            checks.require(token in ui_body, f"audit lifecycle: UI post-spawn incompleta: {token}")
        checks.require("Wait(" not in ui_body and "Loop If Condition Is True;" not in ui_body,
            "audit lifecycle: UI post-spawn non deve usare Wait/Loop")
'''
val = once(val, old_audit, new_audit, "reference sync validator")
VAL.write_text(val, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
tests = once(tests,
    'any("non riarma i due HUD sociali" in error for error in checks.errors)',
    'any("non riarma roster/UI" in error for error in checks.errors)',
    "legacy roster rearm expectation")
anchor = '''    def test_vote_change_must_clear_previous_choice(self) -> None:
'''
new_test = '''    def test_team_rejoin_must_sync_roster_reference_by_existing_slot(self) -> None:
        join_at = self.source.index('rule("01 - Pemain Masuk atau Pindah Tim:')
        join_end = self.source.index('\\nrule("01b - ', join_at)
        join_rule = self.source[join_at:join_end]
        mutated_join = join_rule.replace("\\t\\t\\tGlobal.PemainManusia[Global.IndeksSinkronTim] = Event Player;\\n", "", 1)
        self.assertNotEqual(mutated_join, join_rule)
        mutated = self.source[:join_at] + mutated_join + self.source[join_end:]
        _, player_names, _ = validator.declaration_tables(mutated)
        checks = validator.Checks()
        validator.check_lifecycle_hygiene(checks, mutated, self.rules(mutated), player_names)
        self.assertTrue(any("sincronizza il riferimento roster" in error for error in checks.errors), checks.errors)

'''
tests = once(tests, anchor, new_test + anchor, "reference sync regression test")
TESTS.write_text(tests, encoding="utf-8")

VERSION.write_text("0.6.20\n", encoding="utf-8")
readme = README.read_text(encoding="utf-8")
readme = once(readme, "La versione **0.6.19** identifica lo stato funzionale e tecnico corrente del repository.", "La versione **0.6.20** identifica lo stato funzionale e tecnico corrente del repository.", "README version")
readme += '''\n\n### Sincronizzazione riferimento team 0.6.20\n\nIl cambio team sincronizza in-place il riferimento del player dentro `Global.PemainManusia`: lookup diretto, poi fallback sullo slot HUD persistente per player già inizializzati. Le due righe sociali vengono riarmate senza cleanup/setup completi. `Disable Game Mode HUD` e `Disable Game Mode In-World UI` non vengono più eseguiti nella schermata hero-select: una regola senza Wait/Loop li riapplica soltanto dopo `Has Spawned == True`.\n'''
README.write_text(readme, encoding="utf-8")

progetto = PROGETTO.read_text(encoding="utf-8")
progetto = once(progetto, "# Note di progetto — versione 0.6.19", "# Note di progetto — versione 0.6.20", "PROGETTO title")
progetto = once(progetto, "Workshop 0.6.19.", "Workshop 0.6.20.", "PROGETTO version")
progetto += '''\n\n## Riferimento roster dopo team switch 0.6.20\n\n`IndeksSinkronTim` usa prima l'identità corrente e poi `UrutanHUD/SlotHUDPemain` come chiave di sessione. Il riferimento roster viene sostituito senza riallocare gli array. `AntarmukaModeDiterapkan` sposta la soppressione UI nativa a dopo lo spawn.\n'''
PROGETTO.write_text(progetto, encoding="utf-8")

test_doc = TEST_DOC.read_text(encoding="utf-8")
test_doc = once(test_doc, "# Piano di test — versione 0.6.19", "# Piano di test — versione 0.6.20", "TEST title")
test_doc = once(test_doc, "Workshop 0.6.19.", "Workshop 0.6.20.", "TEST version")
test_doc += '''\n\n## Team switch: roster + hero-select 0.6.20\n\nAlternare Team 1 ↔ Team 2 più volte. Dopo lo spawn le righe sociali devono tornare nello stesso slot con nome/icona/minuti/soundtrack. Nella schermata scelta eroe non deve più comparire il riquadro anomalo `0`. Il server deve restare stabile senza excessive Workshop script load.\n'''
TEST_DOC.write_text(test_doc, encoding="utf-8")

validazione = VALIDAZIONE.read_text(encoding="utf-8")
validazione = once(validazione, "# Rapporto di validazione — versione 0.6.19", "# Rapporto di validazione — versione 0.6.20", "VALIDAZIONE title")
validazione = once(validazione, "Release tecnica: **CHILL Dedicated Server 0.6.19**", "Release tecnica: **CHILL Dedicated Server 0.6.20**", "VALIDAZIONE release")
validazione = once(validazione, "Ran 34 tests", "Ran 35 tests", "test count")
validazione = once(validazione, "OK - controlli statici v0.6.19 superati", "OK - controlli statici v0.6.20 superati", "validator result")
validazione += '''\n\n## Gate sincronizzazione team 0.6.20\n\nIl gate richiede lookup diretto + fallback slot, sostituzione in-place del riferimento roster, rearm HUD sociali e UI nativa solo post-spawn.\n'''
data = SRC.read_bytes().replace(b"\r\n", b"\n")
payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
blob = hashlib.sha1(payload).hexdigest()
validazione, n = re.subn(r"(Blob Git del sorgente Workshop validato:\n\n```text\n)[0-9a-f]{40}(\n```)", rf"\g<1>{blob}\g<2>", validazione, count=1)
if n != 1:
    raise RuntimeError("VALIDAZIONE blob marker not found")
VALIDAZIONE.write_text(validazione, encoding="utf-8")

print("Applied CHILL 0.6.20 team-reference sync and post-spawn UI restore")
