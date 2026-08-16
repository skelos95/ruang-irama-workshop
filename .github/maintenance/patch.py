from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
README = ROOT / "README.md"
PROGETTO = ROOT / "docs" / "PROGETTO.md"
TEST_DOC = ROOT / "docs" / "TEST.md"
VALIDAZIONE = ROOT / "docs" / "VALIDAZIONE.md"
VERSION = ROOT / "VERSION"


def once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise RuntimeError(f"{label}: expected 1 occurrence, found {n}")
    return text.replace(old, new, 1)


def mask(text: str) -> str:
    out: list[str] = []
    quoted = False
    escaped = False
    for ch in text:
        if quoted:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                quoted = False
            out.append("\n" if ch == "\n" else " ")
        elif ch == '"':
            quoted = True
            out.append(" ")
        else:
            out.append(ch)
    if quoted:
        raise RuntimeError("unclosed string")
    return "".join(out)


def matching(text: str, opening: int, left: str, right: str) -> int:
    clean = mask(text)
    depth = 1
    for i in range(opening + 1, len(clean)):
        if clean[i] == left:
            depth += 1
        elif clean[i] == right:
            depth -= 1
            if depth == 0:
                return i
    raise RuntimeError(f"unclosed {left}")


def rule_span(text: str, name: str) -> tuple[int, int, str]:
    marker = f'rule("{name}")'
    start = text.index(marker)
    opening = text.index("{", start)
    end = matching(text, opening, "{", "}") + 1
    return start, end, text[start:end]


def replace_rule(text: str, name: str, rule: str) -> str:
    start, end, _ = rule_span(text, name)
    return text[:start] + rule + text[end:]


def replace_actions(rule: str, actions: str) -> str:
    clean = mask(rule)
    m = re.search(r"(?m)^\s*actions\s*\{", clean)
    if m is None:
        raise RuntimeError("actions block missing")
    opening = clean.find("{", m.start())
    closing = matching(rule, opening, "{", "}")
    return rule[: opening + 1] + "\n" + actions.rstrip() + "\n\t" + rule[closing:]


def call_end(text: str, call_start: int) -> int:
    opening = text.index("(", call_start)
    closing = matching(text, opening, "(", ")")
    semi = text.find(";", closing)
    if semi < 0:
        raise RuntimeError("call semicolon missing")
    return semi + 1


source = SOURCE.read_text(encoding="utf-8")

# 1) Remove the 0.6.14 wait/loop preload entirely.
preload_name = "05e - Menu: Muat halaman lain bertahap setelah menu utama tampil"
start, end, _ = rule_span(source, preload_name)
while end < len(source) and source[end] == "\n":
    end += 1
source = source[:start] + source[end:]

# 2) Add an edge-triggered submenu preloader subroutine. No Wait, no Loop.
source = once(
    source,
    "\t27: BersihkanPemain\n",
    "\t27: BersihkanPemain\n\t28: PramuatHalamanTerpilih\n",
    "subroutine declaration",
)

preload_sub = r'''rule("91p - Subrutin: Pramuat halaman menu yang sedang dipilih")
{
	event
	{
		Subroutine;
		PramuatHalamanTerpilih;
	}

	actions
	{
		"Buat HUD submenu sebelum pemain membukanya. Tidak ada tunda dan tidak ada pengulangan; cache mencegah pembuatan ganda."
		If(Array Contains(Event Player.HalamanHudMenuArcade, Event Player.KursorUtama) == False);
			If(Event Player.KursorUtama == 0);
				Call Subroutine(GambarMusik);
			Else If(Event Player.KursorUtama == 1);
				Call Subroutine(GambarKamera);
			Else If(Event Player.KursorUtama == 2);
				Call Subroutine(GambarWarna);
			Else If(Event Player.KursorUtama == 3);
				Call Subroutine(GambarBahasa);
			Else If(Event Player.KursorUtama == 4);
				Call Subroutine(GambarBalasDendam);
			Else If(Event Player.KursorUtama == 5);
				Call Subroutine(GambarKebal);
			Else If(Event Player.KursorUtama == 6);
				Call Subroutine(GambarSuara);
			Else If(Event Player.KursorUtama == 7);
				Call Subroutine(GambarIkon);
			Else If(Event Player.KursorUtama == 8);
				Call Subroutine(GambarSakelarTeleportasi);
			Else If(Event Player.KursorUtama == 9);
				Call Subroutine(GambarPrivasiInspeksi);
			Else If(Event Player.KursorUtama == 10);
				Call Subroutine(GambarNasib);
			Else If(Event Player.KursorUtama == 11);
				Call Subroutine(GambarPilihan);
			End;
		End;
	}
}

'''
source = once(
    source,
    'rule("91k - Subrutin: Transisi warna menu tanpa lompatan")',
    preload_sub + 'rule("91k - Subrutin: Transisi warna menu tanpa lompatan")',
    "insert selected-page preloader",
)

# 3) GambarMenu becomes a pure state/color router. It never creates HUDs.
router_name = "91 - Subrutin: Pilih gambar menu yang sedang dibuka"
_, _, router = rule_span(source, router_name)
router = replace_actions(
    router,
    '''\t\tCall Subroutine(TransisiWarnaMenu);
\t\tIf(Index Of Array Value(Global.PemainManusia, Event Player) >= 0);
\t\t\tGlobal.HudMenuPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = Count Of(Event Player.HudMenuArcade) > 0 ? First Of(Event Player.HudMenuArcade) : 0;
\t\tEnd;''',
)
source = replace_rule(source, router_name, router)

# 4) While the 0.5 s hold timer runs in rule 05, a separate rule creates the hidden Main
# HUD and currently highlighted submenu. This does not delay the hold timer.
pre_open_rule = r'''rule("05a - Menu: Siapkan HUD tersembunyi saat Melee mulai ditahan")
{
	event
	{
		Ongoing - Each Player;
		All;
		All;
	}

	conditions
	{
		Event Player.Manusia == True;
		Event Player.BotOtomatis == False;
		Is Dummy Bot(Event Player) == False;
		Is Alive(Event Player) == True;
		Event Player.SeranganDekatDipakai == False;
		Event Player.MenuTerbuka == False;
		Event Player.TeleportasiJongkokAktif == False;
		Event Player.KartuNasibAktif == False;
		Is Button Held(Event Player, Button(Melee)) == True;
		Or(Array Contains(Event Player.HalamanHudMenuArcade, -1) == False, Array Contains(Event Player.HalamanHudMenuArcade,
			Event Player.KursorUtama) == False) == True;
	}

	actions
	{
		"HUD dibuat tersembunyi selama penghitung tahan Melee berjalan; pada 0,5 detik hanya visibilitas yang berubah."
		If(Array Contains(Event Player.HalamanHudMenuArcade, -1) == False);
			Call Subroutine(GambarUtama);
		End;
		Call Subroutine(PramuatHalamanTerpilih);
	}
}

'''
source = once(
    source,
    'rule("05b - Menu: Lepaskan serangan jarak dekat sebelum pakai lagi")',
    pre_open_rule + 'rule("05b - Menu: Lepaskan serangan jarak dekat sebelum pakai lagi")',
    "insert pre-open HUD rule",
)

# Cursor movement on Main preloads the newly highlighted submenu before Interact can be pressed.
source = once(
    source,
    "\t\tIf(Event Player.HalamanMenu == -1);\n\t\t\tEvent Player.KursorUtama = (Event Player.KursorUtama + 1) % 12;\n",
    "\t\tIf(Event Player.HalamanMenu == -1);\n\t\t\tEvent Player.KursorUtama = (Event Player.KursorUtama + 1) % 12;\n\t\t\tCall Subroutine(PramuatHalamanTerpilih);\n",
    "Primary main cursor preload",
)
source = once(
    source,
    "\t\tIf(Event Player.HalamanMenu == -1);\n\t\t\tEvent Player.KursorUtama = (Event Player.KursorUtama + 11) % 12;\n",
    "\t\tIf(Event Player.HalamanMenu == -1);\n\t\t\tEvent Player.KursorUtama = (Event Player.KursorUtama + 11) % 12;\n\t\t\tCall Subroutine(PramuatHalamanTerpilih);\n",
    "Secondary main cursor preload",
)

# 5) Split player HUD creation out of rule 02, whose bot/human classifier legitimately uses two Waits.
class_name = "02 - Pemain: Pisahkan manusia dari pasukan kaleng"
_, _, classifier = rule_span(source, class_name)
classifier = once(classifier, "\t\tEvent Player.Manusia = True;\n", "", "defer Manusia edge until roster ready")
clean_classifier = mask(classifier)
create_at = clean_classifier.find("Create HUD Text(")
if create_at < 0:
    raise RuntimeError("rule 02 no longer contains expected player HUD block")
line_start = classifier.rfind("\n", 0, create_at) + 1
small_at = clean_classifier.find("Small Message(", create_at)
if small_at < 0:
    raise RuntimeError("player welcome Small Message not found")
block_end = call_end(classifier, small_at)
hud_block = classifier[line_start:block_end]

hud_block = once(
    hud_block,
    "\t\tGlobal.HudKiriPemain = Append To Array(Global.HudKiriPemain, Event Player.HudKiri);\n",
    "\t\tGlobal.HudKiriPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = Event Player.HudKiri;\n",
    "left HUD indexed assignment",
)
hud_block = once(
    hud_block,
    "\t\tGlobal.HudKananPemain = Append To Array(Global.HudKananPemain, Event Player.HudKanan);\n",
    "\t\tGlobal.HudKananPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = Event Player.HudKanan;\n",
    "right HUD indexed assignment",
)
for line in (
    "\t\tGlobal.HudMenuPemain = Append To Array(Global.HudMenuPemain, 0);\n",
    "\t\tGlobal.TeksDuniaPemain = Append To Array(Global.TeksDuniaPemain, 0);\n",
    "\t\tGlobal.TeksDiriPemain = Append To Array(Global.TeksDiriPemain, 0);\n",
    "\t\tGlobal.SlotHUDPemain = Append To Array(Global.SlotHUDPemain, Event Player.UrutanHUD);\n",
):
    hud_block = once(hud_block, line, "", "move roster placeholder")

placeholders = '''\t\tGlobal.HudKiriPemain = Append To Array(Global.HudKiriPemain, 0);
\t\tGlobal.HudKananPemain = Append To Array(Global.HudKananPemain, 0);
\t\tGlobal.HudMenuPemain = Append To Array(Global.HudMenuPemain, 0);
\t\tGlobal.TeksDuniaPemain = Append To Array(Global.TeksDuniaPemain, 0);
\t\tGlobal.TeksDiriPemain = Append To Array(Global.TeksDiriPemain, 0);
\t\tGlobal.SlotHUDPemain = Append To Array(Global.SlotHUDPemain, Event Player.UrutanHUD);
\t\tEvent Player.Manusia = True;'''
classifier = classifier[:line_start] + placeholders + classifier[block_end:]
source = replace_rule(source, class_name, classifier)

player_hud_rule = f'''rule("02b - HUD Pemain: Buat segera setelah klasifikasi selesai")
{{
\tevent
\t{{
\t\tOngoing - Each Player;
\t\tAll;
\t\tAll;
\t}}

\tconditions
\t{{
\t\tGlobal.Siap == True;
\t\tEvent Player.Manusia == True;
\t\tEvent Player.BotOtomatis == False;
\t\tIs Dummy Bot(Event Player) == False;
\t\tArray Contains(Global.PemainManusia, Event Player) == True;
\t\tEvent Player.HudKiri == Null;
\t\tEvent Player.HudKanan == Null;
\t}}

\tactions
\t{{
\t\t"Klasifikasi manusia/bot sudah selesai. HUD pemain dibuat pada aturan terpisah tanpa tunda dan tanpa pengulangan."
{hud_block.rstrip()}
\t}}
}}

'''
source = once(
    source,
    'rule("02c - Ruang Muncul: Perbarui posisi aman setiap kali masuk")',
    player_hud_rule + 'rule("02c - Ruang Muncul: Perbarui posisi aman setiap kali masuk")',
    "insert player HUD edge rule",
)

# Source-level architectural assertions.
if preload_name in source:
    raise RuntimeError("legacy progressive preload survived")
_, _, router = rule_span(source, router_name)
router_code = mask(router)
if "Create HUD Text" in router_code or any(
    f"Call Subroutine({name});" in router_code
    for name in ("GambarUtama", "GambarMusik", "GambarKamera", "GambarWarna", "GambarBahasa", "GambarBalasDendam", "GambarKebal", "GambarSuara", "GambarIkon", "GambarSakelarTeleportasi", "GambarPrivasiInspeksi", "GambarNasib", "GambarPilihan")
):
    raise RuntimeError("GambarMenu still creates HUDs")
_, _, classifier = rule_span(source, class_name)
if "Create HUD Text" in mask(classifier):
    raise RuntimeError("rule 02 still creates HUD after classifier waits")

SOURCE.write_text(source, encoding="utf-8")

# 6) Validator 0.6.15: global invariant for every HUD creation rule.
validator = VALIDATOR.read_text(encoding="utf-8")
validator = once(validator, "della versione 0.6.14.", "della versione 0.6.15.", "validator doc version")
validator = once(validator, 'CURRENT_VERSION = "0.6.14"', 'CURRENT_VERSION = "0.6.15"', "validator current version")

# Remove the 0.6.14 progressive-preload contract.
block_start = validator.index("    preload_rules = [")
block_end = validator.index("    router_rules = rules_containing", block_start)
validator = validator[:block_start] + validator[block_end:]

# Replace lazy router expectations with pure-router + edge-preload expectations.
old_gate = '''        checks.require(
            "HalamanHudMenuArcade" in router_code
            and "Array Contains" in router_code
            and "TransisiWarnaMenu" in router_code,
            "GambarMenu non usa il gate lazy per pagina",
        )
        checks.require(
            "Count Of(Event Player.HudMenuArcade) == 0" not in router_code,
            "GambarMenu non deve pre-caricare tutte le pagine all'apertura",
        )
        checks.require(len(router.encode("utf-8")) < 12000, "GambarMenu è tornato troppo grande")
        for renderer, page in page_by_renderer.items():
            checks.require(f"Event Player.HalamanMenu == {page}" in router_code, f"GambarMenu non instrada pagina {page}")
            checks.require(f"Call Subroutine({renderer});" in router_code, f"GambarMenu non inizializza {renderer} on demand")
'''
new_gate = '''        checks.require(
            "Call Subroutine(TransisiWarnaMenu);" in router_code,
            "GambarMenu non aggiorna la transizione colore",
        )
        checks.require("Create HUD Text" not in router_code, "GambarMenu non deve creare HUD")
        checks.require("Array Contains" not in router_code, "GambarMenu non deve più gestire la cache di creazione")
        checks.require(len(router.encode("utf-8")) < 5000, "GambarMenu è tornato troppo grande")
        for renderer in page_by_renderer:
            checks.require(
                f"Call Subroutine({renderer});" not in router_code,
                f"GambarMenu richiama ancora renderer HUD {renderer}",
            )
'''
validator = once(validator, old_gate, new_gate, "validator pure GambarMenu")

# Add global zero-wait/zero-loop HUD creator audit near menu checks.
insert_at = validator.index("    dispatcher_candidates = [")
audit = '''    # 0.6.15: nessuna regola che crea HUD può contenere Wait o Loop.
    hud_creator_rules = [rule for rule in rules if code_contains(rule.body, "Create HUD Text(")]
    checks.require(len(hud_creator_rules) > 0, "nessuna regola Create HUD Text trovata")
    for hud_rule in hud_creator_rules:
        hud_code = mask_strings(hud_rule.body)
        checks.require("Wait(" not in hud_code, f"HUD creato dopo/dentro Wait in {hud_rule.name!r}")
        checks.require("Loop If Condition Is True;" not in hud_code, f"HUD creato dentro Loop in {hud_rule.name!r}")

    legacy_progressive = [rule for rule in rules if rule.name.startswith("05e - Menu: Muat halaman lain bertahap")]
    checks.equal(len(legacy_progressive), 0, "preload HUD con Wait/Loop 0.6.14 ancora presente")

    pre_open = [rule for rule in rules if rule.name.startswith("05a - Menu: Siapkan HUD tersembunyi")]
    checks.equal(len(pre_open), 1, "pre-creazione Main Menu durante hold Melee")
    if pre_open:
        pre_code = mask_strings(pre_open[0].body)
        checks.require("Wait(" not in pre_code and "Loop If Condition Is True;" not in pre_code, "pre-creazione Main Menu contiene Wait/Loop")
        checks.require("Call Subroutine(GambarUtama);" in pre_code, "Main Menu non viene preparato prima dei 0,5 s")
        checks.require("Call Subroutine(PramuatHalamanTerpilih);" in pre_code, "submenu selezionato non viene preparato durante hold")

    selected_preload = rules_containing(rules, "Subroutine;", "PramuatHalamanTerpilih;")
    checks.equal(len(selected_preload), 1, "subroutine PramuatHalamanTerpilih")
    if selected_preload:
        selected_code = mask_strings(selected_preload[0].body)
        checks.require("Wait(" not in selected_code and "Loop If Condition Is True;" not in selected_code, "preload pagina selezionata contiene Wait/Loop")
        for renderer in page_by_renderer:
            if renderer != "GambarUtama":
                checks.require(f"Call Subroutine({renderer});" in selected_code, f"preload selezionato non prepara {renderer}")

    classifier_rules = [rule for rule in rules if rule.name.startswith("02 - Pemain: Pisahkan manusia")]
    checks.equal(len(classifier_rules), 1, "classificatore umano/bot")
    if classifier_rules:
        checks.require("Create HUD Text" not in mask_strings(classifier_rules[0].body), "classificatore con Wait crea ancora HUD")
    player_hud_rules = [rule for rule in rules if rule.name.startswith("02b - HUD Pemain:")]
    checks.equal(len(player_hud_rules), 1, "creazione HUD giocatore separata")
    if player_hud_rules:
        body = mask_strings(player_hud_rules[0].body)
        checks.equal(body.count("Create HUD Text("), 2, "HUD giocatore sinistro/destra")
        checks.require("Wait(" not in body and "Loop If Condition Is True;" not in body, "HUD giocatore separato contiene Wait/Loop")

'''
validator = validator[:insert_at] + audit + validator[insert_at:]
VALIDATOR.write_text(validator, encoding="utf-8")

VERSION.write_text("0.6.15\n", encoding="utf-8")

# Documentation.
readme = README.read_text(encoding="utf-8")
readme = once(readme, "La versione **0.6.14** identifica lo stato funzionale e tecnico corrente del repository.", "La versione **0.6.15** identifica lo stato funzionale e tecnico corrente del repository.", "README version")
readme += '''\n\n### Creazione HUD senza Wait/Loop 0.6.15\n\nLa creazione del Main Menu non avviene più dopo il `Wait(0.500)`. Una regola separata, attivata nello stesso momento in cui inizia il hold Melee, crea **invisibili** il Main HUD e il sottomenu attualmente evidenziato; il timer da 0,5 s continua in parallelo nella regola 05. Quando scade, viene soltanto impostato `MenuTerbuka = True`, quindi il Main diventa visibile senza dover essere costruito in quel momento. Spostando il cursore nel Main, il relativo sottomenu viene pre-creato senza timer prima di poter premere Interact.\n\nÈ stato inoltre eliminato il preload 0.6.14 con `Wait(0.016) + Loop`. `GambarMenu` è ora un router puro di stato/colore e non può creare HUD. Anche i due HUD permanenti del giocatore sono stati estratti dalla regola 02 di classificazione umano/bot: i due `Wait(0.016)` necessari alla classificazione restano, ma la creazione HUD avviene nella nuova regola 02b, priva di Wait e Loop. Il validatore applica ora questa regola a **ogni** `Create HUD Text` del progetto.\n'''
README.write_text(readme, encoding="utf-8")

progetto = PROGETTO.read_text(encoding="utf-8")
progetto = once(progetto, "# Note di progetto — versione 0.6.14", "# Note di progetto — versione 0.6.15", "PROGETTO title")
progetto = once(progetto, "Workshop 0.6.14.", "Workshop 0.6.15.", "PROGETTO version")
progetto += '''\n\n## Architettura HUD edge-triggered 0.6.15\n\nIl preload progressivo 05e è stato rimosso. La regola 05 conserva il solo `Wait(0.500)` necessario al gesto hold, ma non è più responsabile della creazione HUD: 05a prepara Main + pagina evidenziata senza Wait/Loop mentre 05 sta contando. `PramuatHalamanTerpilih` prepara i sottomenu sui cambi cursore; `GambarMenu` non chiama più alcun renderer. La regola 02 mantiene i due piccoli Wait richiesti dal riconoscimento umano/bot ma registra prima i placeholder delle liste; 02b crea poi HudKiri/HudKanan senza timer e sostituisce i placeholder per indice.\n'''
PROGETTO.write_text(progetto, encoding="utf-8")

test_doc = TEST_DOC.read_text(encoding="utf-8")
test_doc = once(test_doc, "# Piano di test — versione 0.6.14", "# Piano di test — versione 0.6.15", "TEST title")
test_doc = once(test_doc, "Workshop 0.6.14.", "Workshop 0.6.15.", "TEST version")
test_doc += '''\n\n## Timing Main Menu e audit HUD 0.6.15\n\nTest live prioritario: da menu chiuso premere e tenere Melee. Il Main HUD può essere preparato internamente subito, ma deve restare invisibile fino alla soglia; a **0,5 s** deve comparire senza ulteriore ritardo. Tenendo Melee da menu aperto, la chiusura deve restare a 0,5 s. Nel Main scorrere rapidamente le voci e aprire ciascun sottomenu: la pagina evidenziata viene preparata sul movimento cursore, quindi Interact non deve introdurre pop di creazione. Verificare anche ingresso di un nuovo player: gli HUD laterali devono apparire appena conclusa la classificazione umano/bot, senza ulteriori Wait dedicati all'HUD.\n'''
TEST_DOC.write_text(test_doc, encoding="utf-8")

validazione = VALIDAZIONE.read_text(encoding="utf-8")
validazione = once(validazione, "# Rapporto di validazione — versione 0.6.14", "# Rapporto di validazione — versione 0.6.15", "VALIDAZIONE title")
validazione = once(validazione, "Release tecnica: **CHILL Dedicated Server 0.6.14**", "Release tecnica: **CHILL Dedicated Server 0.6.15**", "VALIDAZIONE release")
validazione = once(validazione, "OK - controlli statici v0.6.14 superati", "OK - controlli statici v0.6.15 superati", "VALIDAZIONE result")
validazione += '''\n\n## Audit zero-Wait HUD 0.6.15\n\nIl gate scansiona tutte le regole che contengono `Create HUD Text`: nessuna può contenere `Wait(` o `Loop If Condition Is True`. Verifica inoltre l'assenza della vecchia regola 05e, la pre-creazione 05a senza timer, la subroutine `PramuatHalamanTerpilih` senza loop, `GambarMenu` privo di renderer e la separazione degli HUD player dalla classificazione 02. I Wait che restano nel progetto appartengono a timer/gameplay/classificazione e non alla costruzione degli HUD.\n'''

data = SOURCE.read_bytes().replace(b"\r\n", b"\n")
payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
blob = hashlib.sha1(payload).hexdigest()
validazione, n = re.subn(
    r"(Blob Git del sorgente Workshop validato:\n\n```text\n)[0-9a-f]{40}(\n```)",
    rf"\g<1>{blob}\g<2>",
    validazione,
    count=1,
)
if n != 1:
    raise RuntimeError("VALIDAZIONE blob marker not found")
VALIDAZIONE.write_text(validazione, encoding="utf-8")

print("Applied CHILL 0.6.15 zero-wait HUD creation architecture")
