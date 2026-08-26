from pathlib import Path


def once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {text.count(old)}")
    return text.replace(old, new, 1)


def patch_source(path: Path, g: str, actions_word: str, wait_ignore: str) -> None:
    text = path.read_text(encoding="utf-8")
    text = once(text, "\t\t55: WaktuSiklusGlobal\n", "\t\t55: WaktuSiklusGlobal\n\t\t56: ProfilNama\n\t\t57: ProfilPreferensiA\n\t\t58: ProfilPreferensiB\n\t\t59: ProfilStatus\n\t\t60: ProfilSosial\n\t\t61: ProfilPilihanNama\n", f"{path}: profile declarations")
    init = f"\t\t{g}.SlotHUDPemain = Empty Array;\n"
    text = once(text, init, init + f"\t\t{g}.ProfilNama = Empty Array;\n\t\t{g}.ProfilPreferensiA = Empty Array;\n\t\t{g}.ProfilPreferensiB = Empty Array;\n\t\t{g}.ProfilStatus = Empty Array;\n\t\t{g}.ProfilSosial = Empty Array;\n\t\t{g}.ProfilPilihanNama = Empty Array;\n", f"{path}: profile init")
    text = once(text, "\t\tDisable Built-In Game Mode Completion;\n", "\t\tDisable Built-In Game Mode Completion;\n\t\tPause Match Time;\n", f"{path}: pause match time")

    idx = f"Index Of Array Value({g}.ProfilNama, Event Player.NamaTampilan)"
    old = f"\t\tEvent Player.MenitLobi = 0;\n\t\tEvent Player.UrutanHUD = First Of({g}.SlotHUDTersedia);"
    new = (
        "\t\t\"Profil pemain bertahan sampai pertandingan dimulai ulang; masuk kembali memulihkan pilihan yang sudah diterapkan.\"\n"
        f"\t\tIf({idx} >= 0);\n"
        f"\t\t\tEvent Player.WaktuMasuk = X Component Of({g}.ProfilPreferensiA[{idx}]);\n"
        f"\t\t\tEvent Player.IndeksGenre = Y Component Of({g}.ProfilPreferensiA[{idx}]);\n"
        f"\t\t\tEvent Player.IndeksWarna = Z Component Of({g}.ProfilPreferensiA[{idx}]);\n"
        f"\t\t\tEvent Player.IndeksBahasa = X Component Of({g}.ProfilPreferensiB[{idx}]);\n"
        f"\t\t\tEvent Player.IndeksSuara = Y Component Of({g}.ProfilPreferensiB[{idx}]);\n"
        f"\t\t\tEvent Player.IndeksIkon = Z Component Of({g}.ProfilPreferensiB[{idx}]);\n"
        f"\t\t\tEvent Player.TeleportasiJongkokDiaktifkan = X Component Of({g}.ProfilStatus[{idx}]) == 1;\n"
        f"\t\t\tEvent Player.PrivasiInspeksiAktif = Y Component Of({g}.ProfilStatus[{idx}]) == 1;\n"
        f"\t\t\tEvent Player.ModeKebal = Z Component Of({g}.ProfilStatus[{idx}]);\n"
        f"\t\t\tEvent Player.IzinkanDummyMengikuti = X Component Of({g}.ProfilSosial[{idx}]) == 1;\n"
        f"\t\t\tEvent Player.JumlahPilihan = Y Component Of({g}.ProfilSosial[{idx}]);\n"
        f"\t\t\tEvent Player.KursorKamera = Z Component Of({g}.ProfilSosial[{idx}]);\n"
        "\t\t\tEvent Player.KursorGenre = Max(0, Event Player.IndeksGenre);\n"
        "\t\t\tEvent Player.KursorWarna = Event Player.IndeksWarna;\n"
        f"\t\t\tEvent Player.WarnaNama = {g}.DaftarWarna[Event Player.IndeksWarna];\n"
        f"\t\t\tEvent Player.WarnaMenu = {g}.DaftarWarnaRGB[Event Player.IndeksWarna];\n"
        "\t\t\tEvent Player.KursorBahasa = Event Player.IndeksBahasa;\n"
        "\t\t\tEvent Player.KursorSuara = Event Player.IndeksSuara;\n"
        "\t\t\tEvent Player.KursorIkon = Event Player.IndeksIkon;\n"
        "\t\t\tEvent Player.KursorTeleportasiJongkok = Event Player.TeleportasiJongkokDiaktifkan ? 1 : 0;\n"
        "\t\t\tEvent Player.KursorPrivasiInspeksi = Event Player.PrivasiInspeksiAktif ? 1 : 0;\n"
        "\t\t\tEvent Player.KursorKebal = Event Player.ModeKebal;\n"
        "\t\t\tEvent Player.KursorIkutiDummy = Event Player.IzinkanDummyMengikuti ? 1 : 0;\n"
        "\t\tElse;\n"
        f"\t\t\t{g}.ProfilNama = Append To Array({g}.ProfilNama, Event Player.NamaTampilan);\n"
        f"\t\t\t{g}.ProfilPreferensiA = Append To Array({g}.ProfilPreferensiA, Vector(Event Player.WaktuMasuk, Event Player.IndeksGenre, Event Player.IndeksWarna));\n"
        f"\t\t\t{g}.ProfilPreferensiB = Append To Array({g}.ProfilPreferensiB, Vector(Event Player.IndeksBahasa, Event Player.IndeksSuara, Event Player.IndeksIkon));\n"
        f"\t\t\t{g}.ProfilStatus = Append To Array({g}.ProfilStatus, Vector(Event Player.TeleportasiJongkokDiaktifkan ? 1 : 0, Event Player.PrivasiInspeksiAktif ? 1 : 0, Event Player.ModeKebal));\n"
        f"\t\t\t{g}.ProfilSosial = Append To Array({g}.ProfilSosial, Vector(Event Player.IzinkanDummyMengikuti ? 1 : 0, Event Player.JumlahPilihan, Event Player.KursorKamera));\n"
        f"\t\t\t{g}.ProfilPilihanNama = Append To Array({g}.ProfilPilihanNama, Custom String(\"\"));\n"
        "\t\tEnd;\n"
        "\t\tEvent Player.MenitLobi = Max(0, Round To Integer((Total Time Elapsed - Event Player.WaktuMasuk) / 60, Down));\n"
        f"\t\tEvent Player.UrutanHUD = First Of({g}.SlotHUDTersedia);"
    )
    text = once(text, old, new, f"{path}: classifier profile restore")

    tail_old = "\t\tEvent Player.Manusia = True;\n\t\tEvent Player.PahlawanTerakhir = Hero Of(Event Player);\n\t\tCall Subroutine(HitungPilihan);"
    tail_new = (
        "\t\tEvent Player.Manusia = True;\n\t\tEvent Player.PahlawanTerakhir = Hero Of(Event Player);\n"
        f"\t\tIf(And({idx} >= 0, {g}.ProfilPilihanNama[{idx}] != Custom String(\"\")));\n"
        f"\t\t\tEvent Player.PemainDipilih = First Of(Filtered Array({g}.PemainManusia, Player Variable(Current Array Element, NamaTampilan) == {g}.ProfilPilihanNama[{idx}]));\n"
        "\t\tEnd;\n\t\tCall Subroutine(HitungPilihan);"
    )
    text = once(text, tail_old, tail_new, f"{path}: restore vote target")

    event = text.index("Player Left Match;")
    marker = f"\t{actions_word}\n\t{{\n"
    pos = text.index(marker, event) + len(marker)
    save = (
        "\t\t\"Simpan profil sebelum masa tunggu keluar; perubahan tim tidak boleh menghapus identitas yang sudah terdaftar.\"\n"
        "\t\tIf(And(Event Player.BotOtomatis == False, Is Dummy Bot(Event Player) == False));\n"
        "\t\t\tIf(Or(Event Player.NamaTampilan == Null, Event Player.NamaTampilan == Custom String(\"\")));\n"
        "\t\t\t\tEvent Player.NamaTampilan = Evaluate Once(Custom String(\"{0}\", Event Player));\n\t\t\tEnd;\n"
        f"\t\t\tIf(Index Of Array Value({g}.ProfilNama, Event Player.NamaTampilan) < 0);\n"
        f"\t\t\t\t{g}.ProfilNama = Append To Array({g}.ProfilNama, Event Player.NamaTampilan);\n"
        f"\t\t\t\t{g}.ProfilPreferensiA = Append To Array({g}.ProfilPreferensiA, Vector(Event Player.WaktuMasuk, Event Player.IndeksGenre, Event Player.IndeksWarna));\n"
        f"\t\t\t\t{g}.ProfilPreferensiB = Append To Array({g}.ProfilPreferensiB, Vector(Event Player.IndeksBahasa, Event Player.IndeksSuara, Event Player.IndeksIkon));\n"
        f"\t\t\t\t{g}.ProfilStatus = Append To Array({g}.ProfilStatus, Vector(Event Player.TeleportasiJongkokDiaktifkan ? 1 : 0, Event Player.PrivasiInspeksiAktif ? 1 : 0, Event Player.ModeKebal));\n"
        f"\t\t\t\t{g}.ProfilSosial = Append To Array({g}.ProfilSosial, Vector(Event Player.IzinkanDummyMengikuti ? 1 : 0, Event Player.JumlahPilihan, Event Player.KursorKamera));\n"
        f"\t\t\t\t{g}.ProfilPilihanNama = Append To Array({g}.ProfilPilihanNama, Event Player.PemainDipilih != Null ? Player Variable(Event Player.PemainDipilih, NamaTampilan) : Custom String(\"\"));\n"
        "\t\t\tElse;\n"
        f"\t\t\t\t{g}.ProfilPreferensiA[Index Of Array Value({g}.ProfilNama, Event Player.NamaTampilan)] = Vector(Event Player.WaktuMasuk, Event Player.IndeksGenre, Event Player.IndeksWarna);\n"
        f"\t\t\t\t{g}.ProfilPreferensiB[Index Of Array Value({g}.ProfilNama, Event Player.NamaTampilan)] = Vector(Event Player.IndeksBahasa, Event Player.IndeksSuara, Event Player.IndeksIkon);\n"
        f"\t\t\t\t{g}.ProfilStatus[Index Of Array Value({g}.ProfilNama, Event Player.NamaTampilan)] = Vector(Event Player.TeleportasiJongkokDiaktifkan ? 1 : 0, Event Player.PrivasiInspeksiAktif ? 1 : 0, Event Player.ModeKebal);\n"
        f"\t\t\t\t{g}.ProfilSosial[Index Of Array Value({g}.ProfilNama, Event Player.NamaTampilan)] = Vector(Event Player.IzinkanDummyMengikuti ? 1 : 0, Event Player.JumlahPilihan, Event Player.KursorKamera);\n"
        f"\t\t\t\t{g}.ProfilPilihanNama[Index Of Array Value({g}.ProfilNama, Event Player.NamaTampilan)] = Event Player.PemainDipilih != Null ? Player Variable(Event Player.PemainDipilih, NamaTampilan) : {g}.ProfilPilihanNama[Index Of Array Value({g}.ProfilNama, Event Player.NamaTampilan)];\n"
        "\t\t\tEnd;\n\t\tEnd;\n"
    )
    text = text[:pos] + save + text[pos:]

    old_tail = f"\t\tWait(0.500, {wait_ignore});\n\t\tAbort If(Entity Exists(Event Player) == True);\n\t\tCall Subroutine(BersihkanPemain);"
    new_tail = (
        f"\t\tWait(0.500, {wait_ignore});\n\t\tAbort If(Entity Exists(Event Player) == True);\n"
        "\t\t\"Jika identitas yang sama sudah aktif lagi, kejadian ini hanya perpindahan tim dan roster lama tidak boleh dibersihkan.\"\n"
        "\t\tAbort If(Count Of(Filtered Array(All Players(All Teams), And(Is Dummy Bot(Current Array Element) == False, Or(Player Variable(Current Array Element, NamaTampilan) == Event Player.NamaTampilan, Custom String(\"{0}\", Current Array Element) == Event Player.NamaTampilan)))) > 0);\n"
        "\t\tCall Subroutine(BersihkanPemain);"
    )
    text = once(text, old_tail, new_tail, f"{path}: replacement guard")
    path.write_text(text, encoding="utf-8")


patch_source(Path("tests/fixtures/semantic_reference.txt"), "Global", "actions", "Ignore Condition")
patch_source(Path("workshop/ruang_irama.it-IT.workshop"), "Globale", "azioni", "Ignora condizione")

validator = Path("tools/validate_workshop.py")
text = validator.read_text(encoding="utf-8")
text = once(text, '    checks.equal(source.count("Disable Built-In Game Mode Completion;"), 1, "blocco completamento nativo fino al timer CHILL")\n', '    checks.equal(source.count("Disable Built-In Game Mode Completion;"), 1, "blocco completamento nativo fino al timer CHILL")\n    checks.equal(source.count("Pause Match Time;"), 1, "timer nativo deve restare in pausa fino al restart CHILL")\n', "validator timer")
text = once(text, '        checks.require("Abort If(Entity Exists(Event Player) == True);" in body,\n                       "leave deve ignorare ogni entità ancora valida dopo il grace period")\n', '        checks.require("Abort If(Entity Exists(Event Player) == True);" in body,\n                       "leave deve ignorare ogni entità ancora valida dopo il grace period")\n        replacement_guard = (\n            "Abort If(Count Of(Filtered Array(All Players(All Teams), And(Is Dummy Bot(Current Array Element) == False, "\n            "Or(Player Variable(Current Array Element, NamaTampilan) == Event Player.NamaTampilan, "\n            "Custom String(\\\"{0}\\\", Current Array Element) == Event Player.NamaTampilan)))) > 0);"\n        )\n        checks.require(replacement_guard in body,\n                       "leave non distingue il cambio squadra dalla vera uscita tramite identità persistente")\n        checks.require(all(token in body for token in ("Global.ProfilNama", "Global.ProfilPreferensiA", "Global.ProfilPreferensiB", "Global.ProfilStatus", "Global.ProfilSosial", "Global.ProfilPilihanNama")),\n                       "leave non salva il profilo persistente prima del grace period")\n', "validator leave")
anchor = '    classifier = next((rule for rule in rules if "Append To Array(Global.PemainManusia, Event Player)" in rule.body), None)\n'
if anchor not in text:
    raise SystemExit("validator classifier anchor missing")
text = text.replace(anchor, anchor + '    if classifier:\n        checks.require("Index Of Array Value(Global.ProfilNama, Event Player.NamaTampilan) >= 0" in classifier.body,\n                       "classifier non ripristina il profilo persistente al rejoin")\n        checks.require("Event Player.WaktuMasuk = X Component Of(Global.ProfilPreferensiA" in classifier.body\n                       and "Event Player.JumlahPilihan = Y Component Of(Global.ProfilSosial" in classifier.body,\n                       "rejoin non ripristina tempo CHILL e stato sociale persistente")\n', 1)
text = once(text, '            minute = classifier.body.find("Event Player.MenitLobi = 0;")\n', '            minute = classifier.body.find("Event Player.MenitLobi = ")\n', "validator special profile ordering")
text = once(text, '    allowed_follow_writers = required_follow_writers | {("TenangkanPemain", "False")}\n', '    allowed_follow_writers = required_follow_writers | {\n        ("TenangkanPemain", "False"),\n        ("02 - Pemain: Pisahkan manusia dari pasukan kaleng", "X Component Of(Global.ProfilSosial[Index Of Array Value(Global.ProfilNama, Event Player.NamaTampilan)]) == 1"),\n    }\n', "validator persistent dummy follow writer")
validator.write_text(text, encoding="utf-8")

tests = Path("tests/test_validate_workshop.py")
text = tests.read_text(encoding="utf-8")
anchor = "    def test_builtin_completion_is_disabled_exactly_once(self) -> None:\n"
if anchor not in text:
    raise SystemExit("tests anchor missing")
added = '''    def test_native_match_time_is_paused_until_chill_restart(self) -> None:\n        mutated = self.source.replace("Pause Match Time;", "", 1)\n        self.assert_rejected(mutated, "timer nativo deve restare in pausa")\n\n    def test_leave_distinguishes_team_switch_from_true_exit(self) -> None:\n        left = self.rule(lambda rule: validator.event_type(rule) == "Player Left Match")\n        token = 'Abort If(Count Of(Filtered Array(All Players(All Teams), And(Is Dummy Bot(Current Array Element) == False, Or(Player Variable(Current Array Element, NamaTampilan) == Event Player.NamaTampilan, Custom String("{0}", Current Array Element) == Event Player.NamaTampilan)))) > 0);'\n        mutated = self.replace_in_rule(left, token, 'Abort If(False);')\n        self.assert_rejected(mutated, "vera uscita tramite identità persistente")\n\n    def test_rejoin_requires_persistent_profile_restore(self) -> None:\n        classifier = self.rule(lambda rule: "Append To Array(Global.PemainManusia, Event Player)" in rule.body)\n        mutated = self.replace_in_rule(classifier, "Event Player.WaktuMasuk = X Component Of(Global.ProfilPreferensiA", "Event Player.WaktuMasuk = X Component Of(Global.ProfilPreferensiB")\n        self.assert_rejected(mutated, "tempo CHILL e stato sociale persistente")\n\n'''
text = text.replace(anchor, added + anchor, 1)
tests.write_text(text, encoding="utf-8")

docs = Path("docs/VALIDAZIONE.md")
text = docs.read_text(encoding="utf-8")
text = text.replace("Un cambio squadra leggero conserva preferenze e cursori; leave e rejoin eseguono invece cleanup e setup fresco.", "Un cambio squadra leggero conserva preferenze e cursori; un vero leave salva un profilo persistente per nome e un rejoin prima del restart CHILL ripristina preferenze, tempo lobby, stato sociale e voto.")
text = text.replace("un leave/rejoin o un fallback di nuova identità passa invece dal setup fresco;", "un vero leave rimuove soltanto l’entità attiva e conserva il profilo globale; il rejoin prima del restart CHILL ripristina quel profilo;")
docs.write_text(text, encoding="utf-8")

changelog = Path("CHANGELOG.md")
text = changelog.read_text(encoding="utf-8")
if "profilo persistente per rejoin" not in text:
    pos = text.find("## 0.8.1")
    end = text.find("\n## ", pos + 1)
    if end < 0:
        end = len(text)
    text = text[:end] + "\n- Lifecycle player: il cambio squadra non viene più scambiato per un vero leave; i veri leave salvano un profilo persistente per rejoin nella stessa partita, e il timer nativo resta in pausa fino allo zero del timer CHILL.\n" + text[end:]
changelog.write_text(text, encoding="utf-8")
