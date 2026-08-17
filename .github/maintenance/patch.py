from pathlib import Path
import hashlib
import re

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "workshop" / "ruang_irama.workshop"
VAL = ROOT / "tools" / "validate_workshop.py"
TST = ROOT / "tests" / "test_validate_workshop.py"


def one(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise RuntimeError(f"{label}: attesa 1 occorrenza, trovate {n}")
    return text.replace(old, new, 1)


def between(text, start, end, new, label):
    a = text.find(start)
    b = text.find(end, a + 1) if a >= 0 else -1
    if a < 0 or b < 0:
        raise RuntimeError(f"{label}: marker non trovato")
    return text[:a] + new + text[b:]


def blob_sha(text):
    data = text.replace("\r\n", "\n").encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


s = SRC.read_text(encoding="utf-8")
s = one(s, "\t\tWait(0.200, Ignore Condition);", "\t\tWait(0.050, Ignore Condition);", "join first wait")
s = one(s, "\t\tWait(0.100, Ignore Condition);\n\t\tAbort If(Entity Exists(Event Player) == False);\n\t\tCall Subroutine(SiapkanPemain);", "\t\tWait(0.050, Ignore Condition);\n\t\tAbort If(Entity Exists(Event Player) == False);\n\t\tCall Subroutine(SiapkanPemain);", "join second wait")
s = one(s, "\t\tWait(0.100, Ignore Condition);\n\t\tCall Subroutine(BersihkanPemain);", "\t\tWait(0.050, Ignore Condition);\n\t\tCall Subroutine(BersihkanPemain);", "leave wait")

quiet = '''rule("93b2 - Subrutin: Tenangkan trigger sebelum cleanup")
{
\tevent
\t{
\t\tSubroutine;
\t\tTenangkanPemain;
\t}

\tactions
\t{
\t\t"Hanya variabel: cegah aksi engine menambah beban pada saat pindah tim."
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
\t}
}

'''
s = between(s, 'rule("93b2 - Subrutin:', 'rule("93c - Subrutin:', quiet, "quiet subroutine")

a = s.index('rule("93c - Subrutin:')
b = s.index('rule("94 - Subrutin:', a)
c = s[a:b]
head = '\t\t"Keadaan aktif sudah ditenangkan sebelum subrutin ini; sekarang hapus data dan objek yang tersisa."\n\t\tEvent Player.PemainDipilih = Null;'
staged = '''\t\t"Pemicu sudah mati; pulihkan engine dalam kelompok kecil dan beri satu bingkai di antaranya."
\t\tStop Camera(Event Player);
\t\tStop Chasing Player Variable(Event Player, WarnaMenu);
\t\tStop Chasing Player Variable(Event Player, RadiusNasib);
\t\tWait(0.016, Ignore Condition);
\t\tClear Status(Event Player, Unkillable);
\t\tSet Damage Received(Event Player, 100);
\t\tSet Move Speed(Event Player, 100);
\t\tStop Modifying Hero Voice Lines(Event Player);
\t\tWait(0.016, Ignore Condition);
\t\tAllow Button(Event Player, Button(Melee));
\t\tAllow Button(Event Player, Button(Jump));
\t\tAllow Button(Event Player, Button(Crouch));
\t\tAllow Button(Event Player, Button(Primary Fire));
\t\tAllow Button(Event Player, Button(Secondary Fire));
\t\tAllow Button(Event Player, Button(Interact));
\t\tAllow Button(Event Player, Button(Reload));
\t\tAllow Button(Event Player, Button(Ability 1));
\t\tAllow Button(Event Player, Button(Ability 2));
\t\tAllow Button(Event Player, Button(Ultimate));
\t\tWait(0.016, Ignore Condition);
\t\tSet Primary Fire Enabled(Event Player, True);
\t\tSet Secondary Fire Enabled(Event Player, True);
\t\tSet Ability 1 Enabled(Event Player, True);
\t\tSet Ability 2 Enabled(Event Player, True);
\t\tSet Ultimate Ability Enabled(Event Player, True);
\t\tSet Melee Enabled(Event Player, True);
\t\tEnable Game Mode HUD(Event Player);
\t\tEnable Game Mode In-World UI(Event Player);
\t\tWait(0.016, Ignore Condition);
\t\tEvent Player.PemainDipilih = Null;'''
c = one(c, head, staged, "cleanup engine staging")
c = one(c, '\t\t\tDestroy HUD Text(Global.HudKiriPemain[Global.IndeksKeluar]);\n\t\t\tDestroy HUD Text(Global.HudKananPemain[Global.IndeksKeluar]);', '\t\t\tDestroy HUD Text(Global.HudKiriPemain[Global.IndeksKeluar]);\n\t\t\tDestroy HUD Text(Global.HudKananPemain[Global.IndeksKeluar]);\n\t\t\tWait(0.016, Ignore Condition);', "social hud yield")
for i in range(13):
    old = f'\t\t\t\tDestroy HUD Text(Player Variable(Global.PemainPembersihan, HudMenuArcade)[{i}]);'
    c = one(c, old, old + '\n\t\t\t\tWait(0.016, Ignore Condition);', f"arcade hud {i}")
c = one(c, '''\t\t\tIf(Global.TeksDiriPemain[Global.IndeksKeluar] != 0);
\t\t\t\tDestroy In-World Text(Global.TeksDiriPemain[Global.IndeksKeluar]);
\t\t\tEnd;
\t\t\tGlobal.SlotHUDTersedia = Sorted Array''', '''\t\t\tIf(Global.TeksDiriPemain[Global.IndeksKeluar] != 0);
\t\t\t\tDestroy In-World Text(Global.TeksDiriPemain[Global.IndeksKeluar]);
\t\t\tEnd;
\t\t\tWait(0.016, Ignore Condition);
\t\t\tGlobal.SlotHUDTersedia = Sorted Array''', "iwt yield")
c = one(c, '''\t\t\tIf(Global.PemainManusia[Global.IndeksPembersihan].TargetBalasDendamTerkunci == Global.PemainPembersihan);
\t\t\t\tSet Player Variable(Global.PemainManusia[Global.IndeksPembersihan], TargetBalasDendamTerkunci, Null);
\t\t\tEnd;
\t\tEnd;''', '''\t\t\tIf(Global.PemainManusia[Global.IndeksPembersihan].TargetBalasDendamTerkunci == Global.PemainPembersihan);
\t\t\t\tSet Player Variable(Global.PemainManusia[Global.IndeksPembersihan], TargetBalasDendamTerkunci, Null);
\t\t\tEnd;
\t\t\tWait(0.016, Ignore Condition);
\t\tEnd;''', "survivor yield")
s = s[:a] + c + s[b:]
SRC.write_text(s, encoding="utf-8")
sha = blob_sha(s)

v = VAL.read_text(encoding="utf-8")
v = one(v, 'CURRENT_VERSION = "0.6.23"', 'CURRENT_VERSION = "0.6.24"', "validator version")
v = one(v, 'Il validatore controlla invarianti strutturali e di progetto della versione 0.6.23.', 'Il validatore controlla invarianti strutturali e di progetto della versione 0.6.24.', "validator doc")
v = v.replace('Wait(0.200, Ignore Condition);', 'Wait(0.050, Ignore Condition);')
v = v.replace('primo yield cambio team da 0,20 s', 'primo yield cambio team da 0,05 s')
v = v.replace('Wait(0.100, Ignore Condition);', 'Wait(0.050, Ignore Condition);')
v = v.replace('secondo yield cambio team da 0,10 s', 'secondo yield cambio team da 0,05 s')
v = v.replace('checks.equal(body.count("Wait(0.050, Ignore Condition);"), 1,', 'checks.equal(body.count("Wait(0.050, Ignore Condition);"), 2,', 2)

old_quiet = '''        for token in (
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
new_quiet = '''        for token in (
            "Event Player.SudahSiap = False;",
            "Event Player.Manusia = False;",
            "Event Player.MenuTerbuka = False;",
            "Event Player.PerintahMenu = 0;",
            "Event Player.TeleportasiJongkokAktif = False;",
            "Event Player.InspeksiAktif = False;",
            "Event Player.KartuNasibAktif = False;",
        ):
            checks.require(token in quiet, f"audit lifecycle: TenangkanPemain incompleto: {token}")
        for forbidden in (
            "Stop Camera(", "Stop Chasing Player Variable(", "Clear Status(",
            "Set Damage", "Set Healing", "Set Knockback", "Set Move Speed(",
            "Allow Button(", "Stop Modifying Hero Voice Lines(", "Enable Game Mode",
            "Destroy HUD Text", "Destroy In-World Text", "Destroy Effect", "Wait(",
            "Loop If Condition Is True;",
        ):
            checks.require(forbidden not in quiet,
                f"audit lifecycle: TenangkanPemain deve usare solo variabili, trovato {forbidden}")'''
v = one(v, old_quiet, new_quiet, "quiet validator")
old_stop = '''        checks.require(
            "Stop Camera(Event Player);" not in leave,
            "cleanup atomico ripete ancora lo stop Camera già eseguito da TenangkanPemain",
        )'''
new_stop = '''        checks.require(
            "Stop Camera(Event Player);" in leave
            and leave.count("Wait(0.016, Ignore Condition);") >= 18,
            "cleanup 0.6.24 non distribuisce ripristini engine/HUD su frame separati",
        )
        for index in range(13):
            checks.require(
                f"Destroy HUD Text(Player Variable(Global.PemainPembersihan, HudMenuArcade)[{index}]);\\n\\t\\t\\t\\tWait(0.016, Ignore Condition);" in leave,
                f"cleanup HUD Arcade {index} non distribuito",
            )'''
v = one(v, old_stop, new_stop, "cleanup validator")
old_names = '''    checks.equal(
        len(call_texts(source, "Enable Nameplates")), 3,
        "Enable Nameplates Crouch, quiescenza e cleanup lifecycle",
    )'''
new_names = '''    checks.equal(
        len(call_texts(source, "Enable Nameplates")), 2,
        "Enable Nameplates Crouch e cleanup lifecycle",
    )'''
v = one(v, old_names, new_names, "nameplates validator")
VAL.write_text(v, encoding="utf-8")

t = TST.read_text(encoding="utf-8")
t = t.replace('Wait(0.200, Ignore Condition);', 'Wait(0.050, Ignore Condition);')
TST.write_text(t, encoding="utf-8")

(ROOT / "VERSION").write_text("0.6.24\n", encoding="utf-8")
p = ROOT / "README.md"; x = p.read_text(encoding="utf-8"); p.write_text(one(x, "La versione **0.6.23**", "La versione **0.6.24**", "README"), encoding="utf-8")
p = ROOT / "docs" / "PROGETTO.md"; x = p.read_text(encoding="utf-8"); x = one(x, "# Note di progetto — versione 0.6.23", "# Note di progetto — versione 0.6.24", "PROGETTO"); x = x.replace("Workshop 0.6.23", "Workshop 0.6.24", 1); x += "\n\n## Team switch a carico distribuito 0.6.24\n\nLa 0.6.23 è live-failed al primo cambio team. `TenangkanPemain` ora modifica soltanto variabili/latch. I ripristini engine e le distruzioni HUD sono spostati in `BersihkanPemain` e separati da yield da 0,016 s; le 13 pagine Arcade cached vengono distrutte una per frame. I due yield del lifecycle tornano a 0,05 s come nella 0.6.22.\n"; p.write_text(x, encoding="utf-8")
p = ROOT / "docs" / "TEST.md"; x = p.read_text(encoding="utf-8"); x = one(x, "# Piano di test — versione 0.6.23", "# Piano di test — versione 0.6.24", "TEST"); x = x.replace("Workshop 0.6.23", "Workshop 0.6.24", 1); x += "\n\n## Team switch 0.6.24\n\nLa 0.6.23 è live-failed al primo cambio team. Provare prima Team 1 → Team 2 senza aprire il Menu Arcade, poi almeno 10 cambi alternati. Ripetere dopo avere visitato tutte le 12 pagine del menu e dopo Camera, Unkillable, Hero Voice, Crouch e Try Your Luck. Nessun `excessive Workshop script load` e una sola registrazione roster dopo ogni spawn.\n"; p.write_text(x, encoding="utf-8")
p = ROOT / "docs" / "VALIDAZIONE.md"; x = p.read_text(encoding="utf-8"); x = one(x, "# Rapporto di validazione — versione 0.6.23", "# Rapporto di validazione — versione 0.6.24", "VALIDAZIONE header"); x = one(x, "Release tecnica: **CHILL Dedicated Server 0.6.23**", "Release tecnica: **CHILL Dedicated Server 0.6.24**", "VALIDAZIONE release"); x = one(x, "OK - controlli statici v0.6.23 superati", "OK - controlli statici v0.6.24 superati", "VALIDAZIONE status"); x, n = re.subn(r"(Blob Git del sorgente Workshop validato:\n\n```text\n)[0-9a-f]{40}(\n```)", rf"\g<1>{sha}\g<2>", x, count=1); assert n == 1; x += "\n\n## Gate team-switch 0.6.24\n\n`TenangkanPemain` deve essere variable-only. `BersihkanPemain` deve distribuire ripristini engine, 13 distruzioni HUD Arcade, IWT e pulizia riferimenti con yield da 0,016 s. Stato: static-ready solo a gate verde; live-pending fino al nuovo test Overwatch.\n"; p.write_text(x, encoding="utf-8")
