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
    a = text.find(start)
    if a < 0:
        raise RuntimeError(f"{label}: marker iniziale non trovato")
    b = text.find(end, a)
    if b < 0:
        raise RuntimeError(f"{label}: marker finale non trovato")
    return text[:a] + replacement + text[b:]


def git_blob_sha_text(text: str) -> str:
    data = text.replace("\r\n", "\n").encode("utf-8")
    payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    return hashlib.sha1(payload).hexdigest()


source = WORKSHOP.read_text(encoding="utf-8")
source = replace_once(
    source,
    "\t28: PramuatHalamanTerpilih\n",
    "\t28: GambarHalamanAktif\n",
    "subroutine active page",
)

preopen = '''rule("05a - Menu: Siapkan hanya HUD utama saat Melee mulai ditahan")
{
\tevent
\t{
\t\tOngoing - Each Player;
\t\tAll;
\t\tAll;
\t}

\tconditions
\t{
\t\tEvent Player.Manusia == True;
\t\tEvent Player.BotOtomatis == False;
\t\tIs Dummy Bot(Event Player) == False;
\t\tIs Alive(Event Player) == True;
\t\tEvent Player.SeranganDekatDipakai == False;
\t\tEvent Player.MenuTerbuka == False;
\t\tEvent Player.TeleportasiJongkokAktif == False;
\t\tEvent Player.KartuNasibAktif == False;
\t\tIs Button Held(Event Player, Button(Melee)) == True;
\t\tArray Contains(Event Player.HalamanHudMenuArcade, -1) == False;
\t}

\tactions
\t{
\t\t"Hanya HUD utama dibuat tersembunyi saat tahan Melee; submenu tidak lagi dipramuat agar setiap pemain memiliki paling banyak satu HUD Arkade."
\t\tCall Subroutine(GambarUtama);
\t}
}

'''
source = replace_between(
    source,
    'rule("05a - Menu:',
    'rule("05b - Menu:',
    preopen,
    "single HUD preopen",
)

old_preload_call = "\n\t\t\tCall Subroutine(PramuatHalamanTerpilih);"
if source.count(old_preload_call) != 2:
    raise RuntimeError(f"main navigation preload: attese 2 occorrenze, trovate {source.count(old_preload_call)}")
source = source.replace(old_preload_call, "")

router = '''rule("91 - Subrutin: Pilih gambar menu yang sedang dibuka")
{
\tevent
\t{
\t\tSubroutine;
\t\tGambarMenu;
\t}

\tactions
\t{
\t\t"Sostituisci HUD hanya quando cambia halaman; perubahan nilai di halaman yang sama restano dinamiche tanpa redraw."
\t\tIf(Or(Count Of(Event Player.HalamanHudMenuArcade) == 0, First Of(Event Player.HalamanHudMenuArcade) != Event Player.HalamanMenu));
\t\t\tCall Subroutine(GambarHalamanAktif);
\t\tEnd;
\t\tCall Subroutine(TransisiWarnaMenu);
\t\tIf(Index Of Array Value(Global.PemainManusia, Event Player) >= 0);
\t\t\tGlobal.HudMenuPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = Count Of(Event Player.HudMenuArcade) > 0 ? First Of(Event Player.HudMenuArcade) : 0;
\t\tEnd;
\t}
}

'''
source = replace_between(
    source,
    'rule("91 - Subrutin: Pilih gambar menu yang sedang dibuka")',
    'rule("91a - Subrutin:',
    router,
    "GambarMenu router",
)

active_router = '''rule("91p - Subrutin: Gambar hanya halaman menu aktif")
{
\tevent
\t{
\t\tSubroutine;
\t\tGambarHalamanAktif;
\t}

\tactions
\t{
\t\t"Buang satu-satunya HUD Arkade lama sebelum membuat halaman baru; cache tidak pernah boleh tumbuh melebihi satu elemen."
\t\tIf(Count Of(Event Player.HudMenuArcade) > 0);
\t\t\tDestroy HUD Text(Event Player.HudMenuArcade[0]);
\t\tEnd;
\t\tEvent Player.HudMenuArcade = Empty Array;
\t\tEvent Player.HalamanHudMenuArcade = Empty Array;
\t\tIf(Index Of Array Value(Global.PemainManusia, Event Player) >= 0);
\t\t\tGlobal.HudMenuPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = 0;
\t\tEnd;
\t\tIf(Event Player.HalamanMenu == -1);
\t\t\tCall Subroutine(GambarUtama);
\t\tElse If(Event Player.HalamanMenu == 0);
\t\t\tCall Subroutine(GambarMusik);
\t\tElse If(Event Player.HalamanMenu == 1);
\t\t\tCall Subroutine(GambarKamera);
\t\tElse If(Event Player.HalamanMenu == 2);
\t\t\tCall Subroutine(GambarWarna);
\t\tElse If(Event Player.HalamanMenu == 3);
\t\t\tCall Subroutine(GambarBahasa);
\t\tElse If(Event Player.HalamanMenu == 4);
\t\t\tCall Subroutine(GambarBalasDendam);
\t\tElse If(Event Player.HalamanMenu == 5);
\t\t\tCall Subroutine(GambarKebal);
\t\tElse If(Event Player.HalamanMenu == 6);
\t\t\tCall Subroutine(GambarSuara);
\t\tElse If(Event Player.HalamanMenu == 7);
\t\t\tCall Subroutine(GambarIkon);
\t\tElse If(Event Player.HalamanMenu == 8);
\t\t\tCall Subroutine(GambarSakelarTeleportasi);
\t\tElse If(Event Player.HalamanMenu == 9);
\t\t\tCall Subroutine(GambarPrivasiInspeksi);
\t\tElse If(Event Player.HalamanMenu == 10);
\t\t\tCall Subroutine(GambarNasib);
\t\tElse If(Event Player.HalamanMenu == 11);
\t\t\tCall Subroutine(GambarPilihan);
\t\tEnd;
\t}
}

'''
source = replace_between(
    source,
    'rule("91p - Subrutin:',
    'rule("91k - Subrutin:',
    active_router,
    "active menu renderer router",
)

append_footer = "Event Player.HudMenuArcade = Append To Array(Event Player.HudMenuArcade, Event Player.HudMenu);"
if source.count(append_footer) != 13:
    raise RuntimeError(f"renderer HUD footer: attesi 13, trovati {source.count(append_footer)}")
source = source.replace(append_footer, "Event Player.HudMenuArcade = Array(Event Player.HudMenu);")
source, page_footer_count = re.subn(
    r"Event Player\.HalamanHudMenuArcade = Append To Array\(Event Player\.HalamanHudMenuArcade, (-?\d+)\);",
    r"Event Player.HalamanHudMenuArcade = Array(\1);",
    source,
)
if page_footer_count != 13:
    raise RuntimeError(f"renderer page footer: attesi 13, trovati {page_footer_count}")

close_start = '''\t\tIf(Count Of(Event Player.HudMenuArcade) > 0);
\t\t\tDestroy HUD Text(Event Player.HudMenuArcade[0]);
\t\tEnd;
'''
close_marker = "\t\tEvent Player.HudMenuArcade = Empty Array;\n\t\tEvent Player.HalamanHudMenuArcade = Empty Array;"
close_rule_at = source.index('rule("90 - Subrutin: Tutup menu')
close_cache_at = source.index(close_start, close_rule_at)
close_clear_at = source.index(close_marker, close_cache_at)
source = (
    source[:close_cache_at]
    + close_start
    + close_marker
    + source[close_clear_at + len(close_marker):]
)

cleanup_rule_at = source.index('rule("93c - Subrutin: Bersihkan pemain saat keluar atau pindah tim")')
cleanup_first = '''\t\t\tIf(Count Of(Player Variable(Global.PemainPembersihan, HudMenuArcade)) > 0);
\t\t\t\tDestroy HUD Text(Player Variable(Global.PemainPembersihan, HudMenuArcade)[0]);
\t\t\t\tWait(0.016, Ignore Condition);
\t\t\tEnd;
'''
cleanup_start = source.index(cleanup_first, cleanup_rule_at)
cleanup_clear = "\t\t\tGlobal.PemainPembersihan.HudMenuArcade = Empty Array;\n\t\t\tGlobal.PemainPembersihan.HalamanHudMenuArcade = Empty Array;"
cleanup_clear_at = source.index(cleanup_clear, cleanup_start)
source = (
    source[:cleanup_start]
    + cleanup_first
    + cleanup_clear
    + source[cleanup_clear_at + len(cleanup_clear):]
)

if "PramuatHalamanTerpilih" in source:
    raise RuntimeError("legacy PramuatHalamanTerpilih ancora presente")
WORKSHOP.write_text(source, encoding="utf-8")
blob = git_blob_sha_text(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_once(validator, 'CURRENT_VERSION = "0.6.24"', 'CURRENT_VERSION = "0.6.25"', "validator version")
validator = replace_once(
    validator,
    "Il validatore controlla invarianti strutturali e di progetto della versione 0.6.24.",
    "Il validatore controlla invarianti strutturali e di progetto della versione 0.6.25.",
    "validator docstring",
)

old_router_validation = '''    router_rules = rules_containing(rules, "Subroutine;", "GambarMenu;")
    checks.equal(len(router_rules), 1, "router split GambarMenu")
    if router_rules:
        router = router_rules[0].body
        router_code = mask_strings(router)
        checks.require("Create HUD Text" not in router_code, "GambarMenu non deve contenere un HUD monolitico")
        checks.require("Custom String" not in router_code, "GambarMenu non deve duplicare i testi delle pagine")
        checks.require("Call Subroutine(TransisiWarnaMenu);" in router_code, "GambarMenu non aggiorna la transizione colore")
        checks.require("Create HUD Text" not in router_code, "GambarMenu non deve creare HUD")
        checks.require("Array Contains" not in router_code, "GambarMenu non deve gestire la creazione HUD")
        checks.require(len(router.encode("utf-8")) < 5000, "GambarMenu è tornato troppo grande")
        for renderer in page_by_renderer:
            checks.require(f"Call Subroutine({renderer});" not in router_code, f"GambarMenu richiama ancora {renderer}")
'''
new_router_validation = '''    router_rules = rules_containing(rules, "Subroutine;", "GambarMenu;")
    checks.equal(len(router_rules), 1, "router split GambarMenu")
    if router_rules:
        router = router_rules[0].body
        router_code = mask_strings(router)
        checks.require("Create HUD Text" not in router_code, "GambarMenu non deve contenere un HUD monolitico")
        checks.require("Custom String" not in router_code, "GambarMenu non deve duplicare i testi delle pagine")
        checks.require("Call Subroutine(TransisiWarnaMenu);" in router_code, "GambarMenu non aggiorna la transizione colore")
        checks.require("Call Subroutine(GambarHalamanAktif);" in router_code, "GambarMenu non sostituisce HUD quando cambia pagina")
        checks.require(
            "Count Of(Event Player.HalamanHudMenuArcade) == 0" in router_code
            and "First Of(Event Player.HalamanHudMenuArcade) != Event Player.HalamanMenu" in router_code,
            "GambarMenu non limita il redraw ai soli cambi pagina",
        )
        checks.require(len(router.encode("utf-8")) < 5000, "GambarMenu è tornato troppo grande")
        for renderer in page_by_renderer:
            checks.require(f"Call Subroutine({renderer});" not in router_code, f"GambarMenu richiama direttamente {renderer}")
'''
validator = replace_once(validator, old_router_validation, new_router_validation, "menu router validator")

old_footer_validation = '''            checks.require(
                code_contains(
                    body,
                    "Event Player.HudMenuArcade = Append To Array(Event Player.HudMenuArcade, Event Player.HudMenu);",
                    f"Event Player.HalamanHudMenuArcade = Append To Array(Event Player.HalamanHudMenuArcade, {page});",
                    "Event Player.HudMenu = Null;",
                ),
                f"{renderer}: ID/pagina HUD non salvati nella cache lazy",
            )
'''
new_footer_validation = '''            checks.require(
                code_contains(
                    body,
                    "Event Player.HudMenuArcade = Array(Event Player.HudMenu);",
                    f"Event Player.HalamanHudMenuArcade = Array({page});",
                    "Event Player.HudMenu = Null;",
                ),
                f"{renderer}: HUD attivo non salvato come cache singola",
            )
            checks.require("Append To Array(Event Player.HudMenuArcade" not in mask_strings(body),
                f"{renderer}: cache HUD può ancora crescere oltre un elemento")
'''
validator = replace_once(validator, old_footer_validation, new_footer_validation, "renderer single cache validator")
validator = replace_once(
    validator,
    'checks.require(close_code.count("Destroy HUD Text(Event Player.HudMenuArcade[") == 13, "TutupMenu non distrugge tutte le pagine HUD caricate")',
    'checks.require(close_code.count("Destroy HUD Text(Event Player.HudMenuArcade[") == 1, "TutupMenu deve distruggere un solo HUD Arcade attivo")',
    "close single HUD validator",
)

old_preload_validation = '''    pre_open=[r for r in rules if r.name.startswith("05a - Menu: Siapkan HUD tersembunyi")]
    checks.equal(len(pre_open),1,"pre-creazione Main Menu")
    if pre_open:
        pc=mask_strings(pre_open[0].body)
        checks.require("Wait(" not in pc and "Loop If Condition Is True;" not in pc,"pre-creazione Main contiene Wait/Loop")
        checks.require("Call Subroutine(GambarUtama);" in pc and "Call Subroutine(PramuatHalamanTerpilih);" in pc,"pre-creazione Main/submenu incompleta")
    selected=rules_containing(rules,"Subroutine;","PramuatHalamanTerpilih;")
    checks.equal(len(selected),1,"PramuatHalamanTerpilih")
    if selected:
        sc=mask_strings(selected[0].body)
        checks.require("Wait(" not in sc and "Loop If Condition Is True;" not in sc,"preload selezionato contiene Wait/Loop")
'''
new_preload_validation = '''    pre_open=[r for r in rules if r.name.startswith("05a - Menu: Siapkan hanya HUD utama")]
    checks.equal(len(pre_open),1,"pre-creazione Main Menu a HUD singolo")
    if pre_open:
        pc=mask_strings(pre_open[0].body)
        checks.require("Wait(" not in pc and "Loop If Condition Is True;" not in pc,"pre-creazione Main contiene Wait/Loop")
        checks.require("Call Subroutine(GambarUtama);" in pc,"pre-creazione Main assente")
        checks.require("GambarHalamanAktif" not in pc,"pre-creazione apre ancora un submenu")
    checks.require("PramuatHalamanTerpilih" not in source,"preload submenu legacy ancora presente")
    active=rules_containing(rules,"Subroutine;","GambarHalamanAktif;")
    checks.equal(len(active),1,"GambarHalamanAktif")
    if active:
        sc=mask_strings(active[0].body)
        checks.require("Wait(" not in sc and "Loop If Condition Is True;" not in sc,"sostituzione pagina contiene Wait/Loop")
        checks.equal(sc.count("Destroy HUD Text(Event Player.HudMenuArcade["),1,"sostituzione pagina distrugge più di un HUD")
        checks.require(
            sc.find("Destroy HUD Text(Event Player.HudMenuArcade[0]);")
            < sc.find("Event Player.HudMenuArcade = Empty Array;")
            < sc.find("Call Subroutine(GambarUtama);"),
            "GambarHalamanAktif non libera il vecchio HUD prima del nuovo renderer",
        )
        for renderer in page_by_renderer:
            checks.require(f"Call Subroutine({renderer});" in sc, f"GambarHalamanAktif non instrada {renderer}")
'''
validator = replace_once(validator, old_preload_validation, new_preload_validation, "preload validator")

old_cleanup_validation = '''        checks.require(
            "Stop Camera(Event Player);" in leave
            and leave.count("Wait(0.016, Ignore Condition);") >= 18,
            "cleanup 0.6.24 non distribuisce ripristini engine/HUD su frame separati",
        )
        for index in range(13):
            checks.require(
                f"Destroy HUD Text(Player Variable(Global.PemainPembersihan, HudMenuArcade)[{index}]);\\n\\t\\t\\t\\tWait(0.016, Ignore Condition);" in leave,
                f"cleanup HUD Arcade {index} non distribuito",
            )
'''
new_cleanup_validation = '''        checks.require(
            "Stop Camera(Event Player);" in leave
            and leave.count("Wait(0.016, Ignore Condition);") >= 8,
            "cleanup 0.6.25 non distribuisce ripristini engine/HUD su frame separati",
        )
        checks.equal(
            leave.count("Destroy HUD Text(Player Variable(Global.PemainPembersihan, HudMenuArcade)["),
            1,
            "cleanup team-switch deve gestire un solo HUD Arcade",
        )
        checks.require(
            "Destroy HUD Text(Player Variable(Global.PemainPembersihan, HudMenuArcade)[0]);\\n\\t\\t\\t\\tWait(0.016, Ignore Condition);" in leave,
            "cleanup HUD Arcade singolo non distribuito",
        )
'''
validator = replace_once(validator, old_cleanup_validation, new_cleanup_validation, "cleanup cache validator")
VALIDATOR.write_text(validator, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
insert_marker = '''    def test_team_rejoin_must_defer_cleanup_and_fresh_setup(self) -> None:
'''
new_test = '''    def test_arcade_menu_cache_must_stay_single_hud(self) -> None:
        _, _, subroutines = validator.declaration_tables(self.source)
        self.assertNotIn("PramuatHalamanTerpilih", subroutines)
        self.assertIn("GambarHalamanAktif", subroutines)
        self.assertNotIn("Append To Array(Event Player.HudMenuArcade", self.source)
        self.assertEqual(self.source.count("Event Player.HudMenuArcade = Array(Event Player.HudMenu);"), 13)

        mutated = self.source.replace(
            "Event Player.HudMenuArcade = Array(Event Player.HudMenu);",
            "Event Player.HudMenuArcade = Append To Array(Event Player.HudMenuArcade, Event Player.HudMenu);",
            1,
        )
        checks = validator.Checks()
        validator.check_menus(checks, mutated, self.rules(mutated), subroutines)
        self.assertTrue(any("cache HUD può ancora crescere" in error for error in checks.errors), checks.errors)

    def test_main_navigation_must_not_preload_submenus(self) -> None:
        primary_at = self.source.index('rule("06 - Menu:')
        secondary_at = self.source.index('rule("07 - Menu:', primary_at)
        after_secondary = self.source.index('rule("07b - ', secondary_at)
        nav = self.source[primary_at:after_secondary]
        self.assertNotIn("GambarHalamanAktif", nav)
        self.assertNotIn("GambarMusik", nav)
        self.assertNotIn("GambarKamera", nav)

'''
if insert_marker not in tests:
    raise RuntimeError("test insertion marker missing")
tests = tests.replace(insert_marker, new_test + insert_marker, 1)
TESTS.write_text(tests, encoding="utf-8")

VERSION.write_text("0.6.25\n", encoding="utf-8")
readme = README.read_text(encoding="utf-8")
readme = replace_once(readme, "La versione **0.6.24**", "La versione **0.6.25**", "README version")
README.write_text(readme, encoding="utf-8")

progetto = PROGETTO.read_text(encoding="utf-8")
progetto = replace_once(progetto, "# Note di progetto — versione 0.6.24", "# Note di progetto — versione 0.6.25", "PROGETTO header")
progetto = progetto.replace("Workshop 0.6.24", "Workshop 0.6.25", 1)
progetto += '''

## Menu Arcade a HUD singolo 0.6.25

Il test live della 0.6.24 ha isolato il crash: il cambio team funziona se il player non usa Menu Arcade/modifiche, mentre può chiudere il server al primo cambio dopo l'uso del menu. La causa più forte nel sorgente era la cache lazy: scorrendo le dodici voci, `HudMenuArcade` conservava fino a tredici `Create HUD Text` persistenti per player.

La 0.6.25 elimina quella crescita. `HudMenuArcade` e `HalamanHudMenuArcade` restano array per compatibilità del lifecycle, ma contengono al massimo un elemento. Durante il hold Melee viene creato soltanto il Main Menu nascosto; Primary/Secondary sul Main modificano solo `KursorUtama` e colore. Entrando o tornando da un submenu, `GambarHalamanAktif` distrugge l'unico HUD corrente e crea il nuovo renderer senza `Wait`. Le modifiche di valore dentro la stessa pagina continuano a usare il testo dinamico e non ricreano l'HUD.

Di conseguenza `TutupMenu` e `BersihkanPemain` devono distruggere al massimo un HUD Arcade per player. Restano invariati il hold Melee da 0,5 s, il dispatcher input, Try Your Luck, Hero Voice NORMAL, Unkillable 1 HP e il menu visibile da morto.
'''
PROGETTO.write_text(progetto, encoding="utf-8")

test_doc = TEST_DOC.read_text(encoding="utf-8")
test_doc = replace_once(test_doc, "# Piano di test — versione 0.6.24", "# Piano di test — versione 0.6.25", "TEST header")
test_doc = test_doc.replace("Workshop 0.6.24", "Workshop 0.6.25", 1)
test_doc += '''

## Test live cache HUD singola 0.6.25

La 0.6.24 è live-parzialmente confermata: cambio team senza usare il Menu Arcade funziona, ma dopo l'uso del menu il primo cambio può ancora chiudere il server per carico Workshop eccessivo. Per la 0.6.25 aprire il menu, scorrere tutte e dodici le voci del Main senza entrarci, quindi cambiare team: il server deve restare attivo. Ripetere entrando in ogni submenu uno alla volta, tornando al Main con Reload e cambiando team dopo ogni pagina.

Poi applicare Camera 3P, Name Color, Language, Unkillable, Hero Voice, Player Icon, Crouch Teleport/Privacy, Vote e Try Your Luck, chiudere il menu e fare almeno dieci cambi Team 1 ↔ Team 2. Interact/Reload devono restare immediati: è ammesso al massimo un singolo frame di sostituzione visiva fra Main e submenu, mai il vecchio ritardo da circa 0,5 s. Stato 0.6.25: static-ready dopo gate, live-pending fino a questa prova.
'''
TEST_DOC.write_text(test_doc, encoding="utf-8")

validation = VALIDAZIONE.read_text(encoding="utf-8")
validation = replace_once(validation, "# Rapporto di validazione — versione 0.6.24", "# Rapporto di validazione — versione 0.6.25", "VALIDAZIONE header")
validation = replace_once(validation, "Release tecnica: **CHILL Dedicated Server 0.6.24**", "Release tecnica: **CHILL Dedicated Server 0.6.25**", "VALIDAZIONE release")
validation = replace_once(validation, "OK - controlli statici v0.6.24 superati", "OK - controlli statici v0.6.25 superati", "VALIDAZIONE status")
validation, n = re.subn(
    r"(Blob Git del sorgente Workshop validato:\n\n```text\n)[0-9a-f]{40}(\n```)",
    rf"\g<1>{blob}\g<2>",
    validation,
    count=1,
)
if n != 1:
    raise RuntimeError("validation blob marker missing")
validation += '''

## Gate cache Menu Arcade 0.6.25

Il gate richiede tredici renderer separati ma una sola istanza HUD attiva per player: ogni renderer assegna `HudMenuArcade = Array(HudMenu)` e `HalamanHudMenuArcade = Array(pagina)`, mentre `Append To Array(HudMenuArcade, ...)` è vietato. `GambarHalamanAktif` deve distruggere solo indice 0, svuotare la cache e instradare il renderer della nuova pagina senza Wait/Loop. Il Main Menu non può più pre-caricare submenu durante Primary/Secondary.

`TutupMenu` e il cleanup team-switch possono distruggere un solo HUD Arcade. Restano obbligatorie le invarianti globali: nessuna regola con `Create HUD Text` può contenere Wait o Loop, e il test live Overwatch resta necessario per dichiarare risolto il crash.
'''
VALIDAZIONE.write_text(validation, encoding="utf-8")

# retrigger 2026-08-17
