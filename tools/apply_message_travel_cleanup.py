from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATHS = (
    ROOT / "workshop" / "ruang_irama.it-IT.workshop",
    ROOT / "tests" / "fixtures" / "semantic_reference.txt",
)


def matching_delimiter(text: str, opening: int, opener: str, closer: str) -> int:
    depth = 1
    in_string = False
    escaped = False
    for index in range(opening + 1, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return index
    raise RuntimeError(f"unclosed delimiter {opener}{closer}")


def rule_span_containing(text: str, marker: str) -> tuple[int, int]:
    marker_at = text.index(marker)
    starts = [text.rfind('\nrule("', 0, marker_at), text.rfind('\nregola("', 0, marker_at)]
    start = max(starts)
    if start < 0:
        raise RuntimeError(f"rule start not found for {marker!r}")
    start += 1
    opening = text.index("{", start)
    closing = matching_delimiter(text, opening, "{", "}")
    return start, closing + 1


def transform_rule(text: str, marker: str, transform) -> str:
    start, end = rule_span_containing(text, marker)
    body = text[start:end]
    changed = transform(body)
    if changed == body:
        raise RuntimeError(f"rule transform made no change for {marker!r}")
    return text[:start] + changed + text[end:]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected 1 occurrence, found {count}")
    return text.replace(old, new, 1)


def strip_small_messages(text: str, markers: tuple[str, ...]) -> str:
    position = 0
    removed: set[str] = set()
    while True:
        call_at = text.find("Small Message(", position)
        if call_at < 0:
            break
        opening = text.index("(", call_at)
        closing = matching_delimiter(text, opening, "(", ")")
        semi = closing + 1
        while semi < len(text) and text[semi] in " \t\r\n":
            semi += 1
        if semi >= len(text) or text[semi] != ";":
            raise RuntimeError("Small Message without terminating semicolon")
        call = text[call_at:semi + 1]
        matched = [marker for marker in markers if marker in call]
        if not matched:
            position = semi + 1
            continue
        line_start = text.rfind("\n", 0, call_at) + 1
        line_end = text.find("\n", semi + 1)
        if line_end < 0:
            line_end = len(text)
        else:
            line_end += 1
        text = text[:line_start] + text[line_end:]
        removed.update(matched)
        position = line_start
    missing = [marker for marker in markers if marker not in removed]
    if missing:
        raise RuntimeError(f"Small Message markers not removed: {missing}")
    return text


NOISY_SMALL_MESSAGE_MARKERS = (
    "Arcade Menu closed.",
    "Arcade Menu online.",
    "Soundtrack: {0}.",
    "First person restored.",
    "Third person on.",
    "Watching {0}.",
    "Name color: {0}.",
    "HUD language: English.",
    "Unkillable disabled.",
    "Unkillable: 1 HP (HEALABLE) enabled.",
    "Unkillable: FULL HP enabled.",
    "Hero voice updated.",
    "Player icon: {0}.",
    "Crouch Teleport enabled.",
    "Crouch Teleport disabled.",
    "Crouch privacy enabled.",
    "Crouch privacy disabled.",
    "Try Your Luck: six outcomes are rolling.",
    "Vote registered for {0}.",
    "Enemy dummy follow enabled.",
    "Enemy dummy follow disabled",
    "Wall phasing enabled.",
    "Fly enabled.",
    "Third person enabled.",
    "Resurrected safely.",
    "Detached.",
    "Teleported to your Spawn Room.",
    "Teleported near the payload.",
    "Teleported near the enemy flag.",
    "Teleported near the Push objective.",
    "Teleported near the current objective.",
    "Teleported near {0}. Personal space sold separately.",
)

SHORT_TEXT_REPLACEMENTS = (
    ("That player disappeared. Very on-brand for CHILL.", "Camera target unavailable."),
    ("Revenge is still resolving. The debt changes only after full death.", "Revenge is already in progress."),
    ("No revenge targets. Peace has won, temporarily.", "No revenge targets."),
    ("That player owes you nothing. Suspiciously peaceful.", "No revenge debt for that player."),
    ("Revenge debt cleared. Case closed.", "No revenge debt remaining."),
    ("Target is already down. Revenge has office hours.", "Revenge target is already down."),
    ("That target already has a revenge in progress.", "Revenge is already active on that target."),
    ("That target is using Try Your Luck. Wait until it finishes.", "Target is using Try Your Luck."),
    ("Revenge armed on {0}. Waiting for full death.", "Revenge armed on {0}."),
    ("Try Your Luck is still active. Wait for it to finish.", "Try Your Luck is already active."),
    ("A revenge death is still resolving. Try Your Luck is temporarily unavailable.", "Try Your Luck is unavailable while Revenge resolves."),
    ("Resurrect was not ready. Release {0} and try again.", "Resurrect unavailable. Release {0} and retry."),
    ("You are already in the Spawn Room. Mission accomplished.", "Already in Spawn Room."),
    ("Spawn Room unavailable on this map right now.", "Spawn Room unavailable."),
    ("Objective position unavailable right now.", "Objective unavailable."),
    ("Attached above {0}. CROUCH + RELOAD detaches.", "Attached to {0}. CROUCH + RELOAD: detach."),
    ("Self Kill ready in {0} s.", "Self Elimination ready in {0}s."),
    ("Camera target unavailable or private. Back to normal.", "Camera target unavailable or private."),
)

FIXED_PASTEL = (
    "Event Player.KursorTeleportasi == 0 ? Custom Color(205, 255, 225, 255) : "
    "Event Player.KursorTeleportasi == 1 ? Custom Color(200, 245, 255, 255) : "
    "Event Player.KursorTeleportasi == 2 ? Custom Color(215, 225, 255, 255) : "
    "Event Player.KursorTeleportasi == 3 ? Custom Color(235, 215, 255, 255) : "
    "Custom Color(255, 215, 230, 255)"
)
FIXED_NEON = (
    "Event Player.KursorTeleportasi == 0 ? Custom Color(80, 255, 160, 255) : "
    "Event Player.KursorTeleportasi == 1 ? Custom Color(65, 225, 255, 255) : "
    "Event Player.KursorTeleportasi == 2 ? Custom Color(95, 150, 255, 255) : "
    "Event Player.KursorTeleportasi == 3 ? Custom Color(195, 100, 255, 255) : "
    "Custom Color(255, 85, 135, 255)"
)
SMOOTH_PASTEL = (
    "Custom Color(190 + X Component Of(Event Player.WarnaMenu) * 0.250, "
    "190 + Y Component Of(Event Player.WarnaMenu) * 0.250, "
    "190 + Z Component Of(Event Player.WarnaMenu) * 0.250, 255)"
)
SMOOTH_NEON = (
    "Custom Color(X Component Of(Event Player.WarnaMenu), Y Component Of(Event Player.WarnaMenu), "
    "Z Component Of(Event Player.WarnaMenu), 255)"
)
TRAVEL_CHASE = (
    "\t\tIf(Event Player.TeleportasiJongkokAktif == True);\n"
    "\t\t\tChase Player Variable Over Time(Event Player, WarnaMenu, Event Player.KursorTeleportasi == 0 ? Vector(80, 255, 160) : "
    "Event Player.KursorTeleportasi == 1 ? Vector(65, 225, 255) : Event Player.KursorTeleportasi == 2 ? Vector(95, 150, 255) : "
    "Event Player.KursorTeleportasi == 3 ? Vector(195, 100, 255) : Vector(255, 85, 135), 0.180, Destination and Duration);\n"
    "\t\tElse;\n"
)


def patch_source(text: str) -> str:
    text = strip_small_messages(text, NOISY_SMALL_MESSAGE_MARKERS)
    for old, new in SHORT_TEXT_REPLACEMENTS:
        if old not in text:
            raise RuntimeError(f"message replacement source missing: {old}")
        text = text.replace(old, new)

    def transition(body: str) -> str:
        actions = "\n\tazioni\n\t{\n"
        if actions not in body:
            raise RuntimeError("TransisiWarnaMenu actions block missing")
        body = body.replace(actions, actions + TRAVEL_CHASE, 1)
        close = body.rfind("\n\t}\n}")
        if close < 0:
            raise RuntimeError("TransisiWarnaMenu close missing")
        return body[:close] + "\n\t\tEnd;" + body[close:]

    text = transform_rule(text, "\n\t\tTransisiWarnaMenu;", transition)

    def renderer(body: str) -> str:
        body = replace_once(body, FIXED_PASTEL, SMOOTH_PASTEL, "Travel pastel palette")
        body = replace_once(body, FIXED_NEON, SMOOTH_NEON, "Travel neon palette")
        body = replace_once(body, "Visible To and String, Visible Never);", "Visible To String and Color, Visible Never);", "Travel color reevaluation")
        return body

    text = transform_rule(text, "\n\t\tGambarTeleportasi;", renderer)

    def add_transition_before_render(body: str) -> str:
        return replace_once(
            body,
            "\t\tCall Subroutine(GambarTeleportasi);",
            "\t\tCall Subroutine(TransisiWarnaMenu);\n\t\tCall Subroutine(GambarTeleportasi);",
            "Travel transition call",
        )

    text = transform_rule(text, "Event Player.TeleportasiJongkokAktif = True;", add_transition_before_render)
    text = transform_rule(text, "Event Player.KursorTeleportasi = (Event Player.KursorTeleportasi +", add_transition_before_render)

    def arcade_open(body: str) -> str:
        marker = "\t\t\tCall Subroutine(GambarMenu);"
        return replace_once(body, marker, marker + "\n\t\t\tCall Subroutine(TransisiWarnaMenu);", "Arcade open transition")

    text = transform_rule(text, "Event Player.SeranganDekatDipakai = True;", arcade_open)
    return text


for path in SOURCE_PATHS:
    original = path.read_text(encoding="utf-8")
    patched = patch_source(original)
    path.write_text(patched, encoding="utf-8")


validator_path = ROOT / "tools" / "validate_workshop.py"
validator = validator_path.read_text(encoding="utf-8")
menu_pattern = re.compile(
    r"(def validate_hud_and_menu\(checks: Checks, source: str, rules: list\[Rule\], players: set\[str\], subroutines: set\[str\]\) -> None:\n)"
    r"    for text in \(.*?\n    for legacy in \(",
    re.DOTALL,
)
menu_replacement = r'''\1    routine_noise = (
        "Arcade Menu online.",
        "Arcade Menu closed.",
        "Soundtrack: {0}.",
        "Third person on.",
        "Name color: {0}.",
        "Hero voice updated.",
        "Player icon: {0}.",
        "Crouch Teleport enabled.",
        "Crouch privacy enabled.",
        "Vote registered for {0}.",
        "Enemy dummy follow enabled.",
        "Wall phasing enabled.",
        "Fly enabled.",
        "Resurrected safely.",
        "Teleported to your Spawn Room.",
    )
    for text in routine_noise:
        checks.require(text not in source, f"Small Message routine ridondante ancora presente: {text}")
    for legacy in ('''
validator, count = menu_pattern.subn(menu_replacement, validator, count=1)
if count != 1:
    raise RuntimeError(f"validator menu-message block replacement count={count}")

palette_pattern = re.compile(r"                pastel_palette = \(.*?\n    teleport_interact = ", re.DOTALL)
palette_replacement = '''                smooth_pastel = (
                    "Custom Color(190 + X Component Of(Event Player.WarnaMenu) * 0.250, "
                    "190 + Y Component Of(Event Player.WarnaMenu) * 0.250, "
                    "190 + Z Component Of(Event Player.WarnaMenu) * 0.250, 255)"
                )
                smooth_neon = (
                    "Custom Color(X Component Of(Event Player.WarnaMenu), "
                    "Y Component Of(Event Player.WarnaMenu), "
                    "Z Component Of(Event Player.WarnaMenu), 255)"
                )
                checks.equal(
                    teleport_call.args[7].strip(),
                    smooth_pastel,
                    "GambarTeleportasi: tinta pastello fluida guidata da WarnaMenu",
                )
                checks.equal(
                    teleport_call.args[8].strip(),
                    smooth_neon,
                    "GambarTeleportasi: tinta neon fluida guidata da WarnaMenu",
                )
                checks.equal(
                    teleport_call.args[9].strip(),
                    "Visible To String and Color",
                    "GambarTeleportasi: colore deve rivalutarsi durante la chase",
                )
    travel_transition = rule_by_subroutine(rules, "TransisiWarnaMenu")
    checks.require(travel_transition is not None, "transizione Travel assente")
    if travel_transition:
        for token in (
            "Event Player.TeleportasiJongkokAktif == True",
            "Vector(80, 255, 160)",
            "Vector(65, 225, 255)",
            "Vector(95, 150, 255)",
            "Vector(195, 100, 255)",
            "Vector(255, 85, 135)",
            "0.180, Destination and Duration",
        ):
            checks.require(token in travel_transition.body,
                           f"transizione Travel fluida incompleta: {token}")
    travel_open = next((rule for rule in rules if rule.name.startswith("19 - Teleportasi Jongkok: Buka")), None)
    travel_nav = next((rule for rule in rules if rule.name.startswith("19c - Teleportasi Jongkok:")), None)
    checks.require(travel_open is not None and "Call Subroutine(TransisiWarnaMenu);" in travel_open.body,
                   "apertura Travel non avvia la transizione colore")
    checks.require(travel_nav is not None and "Call Subroutine(TransisiWarnaMenu);" in travel_nav.body,
                   "navigazione Travel non avvia la transizione colore")
    teleport_interact = '''
validator, count = palette_pattern.subn(palette_replacement, validator, count=1)
if count != 1:
    raise RuntimeError(f"validator Travel palette replacement count={count}")
validator_path.write_text(validator, encoding="utf-8")


test_validate_path = ROOT / "tests" / "test_validate_workshop.py"
test_validate = test_validate_path.read_text(encoding="utf-8")
open_test_pattern = re.compile(
    r"    def test_menu_open_message_announces_fourteen_pages_in_all_languages\(self\) -> None:\n.*?(?=    def )",
    re.DOTALL,
)
open_test_replacement = '''    def test_routine_small_messages_stay_suppressed(self) -> None:
        noisy = (
            "Arcade Menu online.",
            "Arcade Menu closed.",
            "Soundtrack: {0}.",
            "Third person on.",
            "Name color: {0}.",
            "Hero voice updated.",
            "Player icon: {0}.",
            "Crouch Teleport enabled.",
            "Crouch privacy enabled.",
            "Vote registered for {0}.",
            "Enemy dummy follow enabled.",
            "Wall phasing enabled.",
            "Fly enabled.",
            "Resurrected safely.",
            "Teleported to your Spawn Room.",
        )
        for marker in noisy:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, self.source)

'''
test_validate, count = open_test_pattern.subn(open_test_replacement, test_validate, count=1)
if count != 1:
    raise RuntimeError(f"menu message test replacement count={count}")

palette_test_pattern = re.compile(
    r"    def test_teleport_menu_keeps_pastel_and_neon_page_palettes\(self\) -> None:\n.*?(?=    def )",
    re.DOTALL,
)
palette_test_replacement = '''    def test_teleport_menu_uses_smooth_chased_tint(self) -> None:
        renderer = self.rule(lambda rule: validator.subroutine_target(rule) == "GambarTeleportasi")
        for token in (
            "Custom Color(190 + X Component Of(Event Player.WarnaMenu) * 0.250",
            "Custom Color(X Component Of(Event Player.WarnaMenu)",
            "Visible To String and Color",
        ):
            self.assertIn(token, renderer.body)
        transition = self.rule(lambda rule: validator.subroutine_target(rule) == "TransisiWarnaMenu")
        for token in (
            "Event Player.TeleportasiJongkokAktif == True",
            "Vector(80, 255, 160)",
            "Vector(65, 225, 255)",
            "Vector(95, 150, 255)",
            "Vector(195, 100, 255)",
            "Vector(255, 85, 135)",
            "0.180, Destination and Duration",
        ):
            self.assertIn(token, transition.body)
        mutated = self.replace_in_rule(renderer, "Visible To String and Color", "Visible To and String")
        self.assert_rejected(mutated, "colore deve rivalutarsi")

'''
test_validate, count = palette_test_pattern.subn(palette_test_replacement, test_validate, count=1)
if count != 1:
    raise RuntimeError(f"Travel palette test replacement count={count}")
test_validate_path.write_text(test_validate, encoding="utf-8")


runtime_path = ROOT / "tests" / "test_runtime_maintenance.py"
runtime = runtime_path.read_text(encoding="utf-8")
color_loop_pattern = re.compile(
    r"            for color in \(\n(?:                .*\n)+?            \):\n                self\.assertIn\(color, teleport_render\)\n",
)
color_loop_replacement = '''            self.assertIn("Custom Color(190 + X Component Of(Event Player.WarnaMenu) * 0.250", teleport_render)
            self.assertIn("Custom Color(X Component Of(Event Player.WarnaMenu)", teleport_render)
            self.assertIn("Visible To String and Color", teleport_render)
            transition = source.split(f'{rule_kw}("91k - Subrutin: Transisi warna menu tanpa lompatan")', 1)[1].split(f'{rule_kw}("91l - Subrutin', 1)[0]
            for color in (
                "Vector(80, 255, 160)",
                "Vector(65, 225, 255)",
                "Vector(95, 150, 255)",
                "Vector(195, 100, 255)",
                "Vector(255, 85, 135)",
            ):
                self.assertIn(color, transition)
            self.assertIn("Event Player.TeleportasiJongkokAktif == True", transition)
            self.assertIn("0.180, Destination and Duration", transition)
'''
runtime, count = color_loop_pattern.subn(color_loop_replacement, runtime, count=1)
if count != 1:
    raise RuntimeError(f"runtime Travel color loop replacement count={count}")
runtime_path.write_text(runtime, encoding="utf-8")


changelog_path = ROOT / "CHANGELOG.md"
changelog = changelog_path.read_text(encoding="utf-8")
status = "Stato: **live-pending**.\n"
addition = (
    "\n- Ripuliti gli `Small Message`: le conferme già evidenti da HUD o azione non vengono più accodate; restano errori, cooldown, istruzioni necessarie e risultati di Try Your Luck/Revenge.\n"
    "- Le cinque pagine Crouch Travel & Attach mantengono la palette mint → cyan → blu → viola → rosa ma ora la interpolano in `0,18 s` tramite `WarnaMenu`, con colore HUD rivalutato durante la transizione come nei 14 menu Arcade.\n"
)
if addition.strip() not in changelog:
    changelog = replace_once(changelog, status, status + addition, "CHANGELOG status")
changelog_path.write_text(changelog, encoding="utf-8")

readme_path = ROOT / "README.md"
readme = readme_path.read_text(encoding="utf-8")
needle = "Le cinque pagine dell'overlay Travel usano una terminologia uniforme e specifica in EN/ID/TH: ogni schermata indica pagina, destinazione o posizione, target quando serve e azione."
if needle not in readme:
    raise RuntimeError("README Travel paragraph missing")
readme = readme.replace(
    needle,
    needle + " La palette mint → cyan → blu → viola → rosa viene interpolata in 0,18 s sulla stessa `WarnaMenu` dei menu Arcade; gli `Small Message` sono riservati a errori, cooldown, istruzioni necessarie e risultati non già visibili nel HUD.",
    1,
)
readme_path.write_text(readme, encoding="utf-8")

progetto_path = ROOT / "docs" / "PROGETTO.md"
progetto = progetto_path.read_text(encoding="utf-8")
anchor = "- Crouch Travel & Attach contiene cinque pagine:"
pos = progetto.find(anchor)
if pos < 0:
    raise RuntimeError("PROGETTO Travel bullet missing")
line_end = progetto.find("\n", pos)
progetto = progetto[:line_end + 1] + "- Il renderer Travel usa `WarnaMenu` con chase da 0,18 s per passare fluidamente mint → cyan → blu → viola → rosa; le conferme Small Message ridondanti sono soppresse, mentre errori/cooldown/esiti restano espliciti.\n" + progetto[line_end + 1:]
progetto_path.write_text(progetto, encoding="utf-8")

test_doc_path = ROOT / "docs" / "TEST.md"
test_doc = test_doc_path.read_text(encoding="utf-8")
section = '''\n### Small Message e transizione Crouch Travel\n\n- Navigare rapidamente `1→2→3→4→5→1` e in senso inverso: mint, cyan, blu, viola e rosa devono fondersi in circa 0,18 s senza scatti o ricreazioni extra del renderer.\n- Verificare che apertura/chiusura menu, selezioni riuscite, toggle, camera normale e Teleport riusciti non generino conferme Small Message ridondanti. Errori, cooldown, Attach con istruzione di detach, fallimenti Resurrect e risultati Try Your Luck/Revenge devono invece restare notificati.\n'''
if "### Small Message e transizione Crouch Travel" not in test_doc:
    test_doc += section
test_doc_path.write_text(test_doc, encoding="utf-8")

validation_doc_path = ROOT / "docs" / "VALIDAZIONE.md"
validation_doc = validation_doc_path.read_text(encoding="utf-8")
validation_note = "\n- UX messaggi/Travel: il gate vieta le conferme Small Message ridondanti selezionate e richiede per Crouch Travel la chase `WarnaMenu` da 0,18 s, i cinque target cromatici e `Visible To String and Color`.\n"
if validation_note.strip() not in validation_doc:
    validation_doc += validation_note
validation_doc_path.write_text(validation_doc, encoding="utf-8")
