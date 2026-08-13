#!/usr/bin/env python3
"""Validazione statica del sorgente Overwatch Workshop.

Il validatore controlla invarianti strutturali e di progetto della versione 0.5.4.
Non sostituisce l'importazione nel client o le prove live con dodici giocatori.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CURRENT_VERSION = "0.5.4"
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
GENRE_DOC = ROOT / "docs" / "GENERI.md"
VERSION = ROOT / "VERSION"
WORKFLOW = ROOT / ".github" / "workflows" / "validate-workshop.yml"
LEGACY_AUTOMATION = (
    ROOT / ".github" / "trigger-camera-bots",
    ROOT / ".github" / "workflows" / "patch-camera-bots.yml",
)

THAI_RE = re.compile(r"[\u0e00-\u0e7f]")
CUSTOM_STRING_RE = re.compile(
    r'Custom\s+String\s*\(\s*"((?:[^"\\]|\\.)*)"', re.DOTALL
)
VALID_EVENT_TYPES = {
    "Ongoing - Global",
    "Ongoing - Each Player",
    "Player Dealt Damage",
    "Player Dealt Final Blow",
    "Player Dealt Healing",
    "Player Dealt Knockback",
    "Player Died",
    "Player Earned Elimination",
    "Player Joined Match",
    "Player Left Match",
    "Player Received Healing",
    "Player Received Knockback",
    "Player Took Damage",
    "Subroutine",
}


class ParseError(ValueError):
    """Errore strutturale che impedisce un controllo affidabile."""


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


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def find_matching(text: str, opening_index: int, opening: str, closing: str) -> int:
    """Trova la chiusura corrispondente ignorando delimitatori nelle stringhe."""
    if opening_index >= len(text) or text[opening_index] != opening:
        raise ParseError(f"delimitatore {opening!r} assente all'offset {opening_index}")
    depth = 1
    in_string = False
    escaped = False
    for index in range(opening_index + 1, len(text)):
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
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return index
    raise ParseError(
        f"{opening!r} aperto alla riga {line_number(text, opening_index)} non chiuso"
    )


def mask_strings(text: str) -> str:
    """Mantiene offset e newline, nascondendo il contenuto fra virgolette."""
    result: list[str] = []
    in_string = False
    escaped = False
    for char in text:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            result.append("\n" if char == "\n" else " ")
        elif char == '"':
            in_string = True
            result.append(" ")
        else:
            result.append(char)
    if in_string:
        raise ParseError("stringa non chiusa")
    return "".join(result)


def balanced_errors(source: str) -> list[str]:
    errors: list[str] = []
    try:
        clean = mask_strings(source)
    except ParseError as exc:
        return [str(exc)]
    for opening, closing, label in (("{", "}", "graffe"), ("(", ")", "parentesi")):
        stack: list[int] = []
        for index, char in enumerate(clean):
            if char == opening:
                stack.append(index)
            elif char == closing:
                if not stack:
                    errors.append(f"{label} chiuse troppo presto alla riga {line_number(source, index)}")
                    break
                stack.pop()
        if stack:
            errors.append(
                f"{len(stack)} {label} non chiusa/e; prima apertura alla riga "
                f"{line_number(source, stack[0])}"
            )
    return errors


def section_body(source: str, name: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*\{{", source)
    if match is None:
        raise ParseError(f"sezione {name!r} non trovata")
    opening = source.find("{", match.start())
    closing = find_matching(source, opening, "{", "}")
    return source[opening + 1 : closing]


def declaration_tables(source: str) -> tuple[set[str], set[str], set[str]]:
    variables = section_body(source, "variables")
    global_match = re.search(
        r"(?ms)^\s*global\s*:\s*(.*?)(?=^\s*player\s*:)", variables
    )
    player_match = re.search(r"(?ms)^\s*player\s*:\s*(.*)\Z", variables)
    if global_match is None or player_match is None:
        raise ParseError("tabelle global/player non riconosciute nella sezione variables")

    def names(body: str) -> set[str]:
        return set(re.findall(r"(?m)^\s*\d+\s*:\s*([A-Za-z_][A-Za-z0-9_]*)\s*$", body))

    subroutine_names = names(section_body(source, "subroutines"))
    return names(global_match.group(1)), names(player_match.group(1)), subroutine_names


def extract_rules(source: str) -> list[Rule]:
    rules: list[Rule] = []
    pattern = re.compile(r'^\s*rule\s*\(\s*"((?:[^"\\]|\\.)*)"\s*\)\s*\{', re.MULTILINE)
    for match in pattern.finditer(source):
        opening = source.find("{", match.start())
        closing = find_matching(source, opening, "{", "}")
        rules.append(Rule(match.group(1), source[opening + 1 : closing], match.start()))
    return rules


def array_body(source: str, assignment: str) -> str:
    owner, _, name = assignment.partition(".")
    if not owner or not name:
        raise ParseError(f"nome array non valido: {assignment}")
    pattern = re.compile(
        rf"\b{re.escape(owner)}\s*\.\s*{re.escape(name)}\s*=\s*Array\s*\("
    )
    match = pattern.search(source)
    if match is None:
        raise ParseError(f"assegnazione Array non trovata: {assignment}")
    opening = source.rfind("(", match.start(), match.end())
    closing = find_matching(source, opening, "(", ")")
    return source[opening + 1 : closing]


def top_level_items(body: str) -> list[str]:
    items: list[str] = []
    item_start = 0
    stack: list[str] = []
    in_string = False
    escaped = False
    pairs = {")": "(", "]": "[", "}": "{"}
    for index, char in enumerate(body):
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
        elif char in "([{":
            stack.append(char)
        elif char in ")]}":
            if not stack or stack[-1] != pairs[char]:
                raise ParseError(f"delimitatore inatteso {char!r} in un Array")
            stack.pop()
        elif char == "," and not stack:
            items.append(body[item_start:index].strip())
            item_start = index + 1
    if in_string or stack:
        raise ParseError("elemento Array non bilanciato")
    tail = body[item_start:].strip()
    if tail:
        items.append(tail)
    return items


def custom_strings(text: str) -> list[str]:
    return [match.group(1) for match in CUSTOM_STRING_RE.finditer(text)]


def call_texts(source: str, call_name: str) -> list[str]:
    calls: list[str] = []
    pattern = re.compile(rf"\b{re.escape(call_name)}\s*\(")
    for match in pattern.finditer(source):
        opening = source.find("(", match.start(), match.end())
        closing = find_matching(source, opening, "(", ")")
        calls.append(source[match.start() : closing + 1])
    return calls


def whole_call_argument(expression: str, call_name: str) -> str | None:
    """Restituisce l'argomento solo se la chiamata avvolge l'intera espressione."""
    prefix = f"{call_name}("
    if not expression.startswith(prefix):
        return None
    opening = len(call_name)
    closing = find_matching(expression, opening, "(", ")")
    if closing != len(expression) - 1:
        return None
    return expression[opening + 1 : closing]


def rules_containing(rules: list[Rule], *tokens: str) -> list[Rule]:
    return [rule for rule in rules if all(token in rule.body for token in tokens)]


def standalone_comments(source: str) -> list[tuple[int, str]]:
    comments: list[tuple[int, str]] = []
    pattern = re.compile(r'^\s*"((?:[^"\\]|\\.)*)"\s*$', re.MULTILINE)
    for match in pattern.finditer(source):
        comments.append((line_number(source, match.start()), match.group(1)))
    return comments


def word_tokens(text: str) -> list[str]:
    return [token.casefold() for token in re.findall(r"[A-Za-zÀ-ÿ]+", text)]


def identifier_tokens(identifier: str) -> list[str]:
    pieces = re.findall(
        r"[A-ZÀ-Ý]+(?=[A-ZÀ-Ý][a-zà-ÿ]|\d|$)|[A-ZÀ-Ý]?[a-zà-ÿ]+|\d+",
        identifier,
    )
    return [piece.casefold() for piece in pieces]


# Lessico volutamente conservativo: termini inequívocamente italiani nel
# contesto di regole/commenti Workshop. Prestiti tecnici (menu, camera, server,
# bot, target, HUD e simili) sono ammessi.
ITALIAN_WORDS = {
    "abbassa", "aggiorna", "aggiornare", "aggiornato", "aggiornamento",
    "altre", "anche", "annunciatore", "apre", "applica", "assegna",
    "assegnare", "avvia", "barra", "barre", "blocca", "chiude", "chiuso",
    "completamento", "consente", "controlla", "dalla", "davvero", "diretta",
    "durata", "entra", "entrare", "evitando", "finisce", "fino", "gioco",
    "indipendente", "inserire", "italiano", "lasciando", "morte", "musica",
    "nativo", "nativa", "nessuna", "niente", "nostro", "obiettivi", "oltre",
    "partita", "personalizzato", "posizione", "prima", "punteggio", "pulita",
    "può", "ricorda", "riduce", "riavvia", "scegliere", "scelta", "sicura",
    "sinistra", "solo", "sostituisce", "spalla", "spazio", "subito", "targhette",
    "tempo", "terza", "tutte", "troppo", "ultima", "una", "vicino", "vincitore",
}


def italian_hits(text: str) -> set[str]:
    return set(word_tokens(text)) & ITALIAN_WORDS


def translatable_literal(value: str, genres: set[str]) -> bool:
    if value in genres or THAI_RE.search(value):
        return False
    cleaned = re.sub(r"\\[nrt]", " ", value)
    cleaned = re.sub(r"\{\d+\}", " ", cleaned)
    return re.search(r"[A-Za-zÀ-ÿ]{2,}", cleaned) is not None


def check_language_arrays(checks: Checks, source: str) -> tuple[list[str], list[Rule]]:
    genres = custom_strings(array_body(source, "Global.DaftarGenre"))
    checks.equal(len(genres), 100, "numero di generi")
    checks.equal(len(set(genres)), 100, "numero di generi unici")

    languages = custom_strings(array_body(source, "Global.NamaBahasa"))
    checks.equal(languages, ["English", "Bahasa Indonesia", "ไทย"], "lingue HUD")

    colors = top_level_items(array_body(source, "Global.DaftarWarna"))
    checks.equal(len(colors), 20, "numero di colori")
    localized_arrays = {
        "pagine indonesiane": ("Global.NamaHalaman", 10, False),
        "pagine inglesi": ("Global.NamaHalamanEN", 10, False),
        "pagine thailandesi": ("Global.NamaHalamanTH", 10, True),
        "colori indonesiani": ("Global.NamaWarna", 20, False),
        "colori inglesi": ("Global.NamaWarnaEN", 20, False),
        "colori thailandesi": ("Global.NamaWarnaTH", 20, True),
    }
    for label, (assignment, expected, require_thai) in localized_arrays.items():
        values = custom_strings(array_body(source, assignment))
        checks.equal(len(values), expected, label)
        checks.equal(len(set(values)), expected, f"{label} unici")
        if require_thai:
            checks.require(
                all(THAI_RE.search(value) for value in values),
                f"{label}: ogni voce deve contenere testo thai",
            )

    thai_literals = [value for value in custom_strings(source) if THAI_RE.search(value)]
    checks.require(bool(thai_literals), "nessun testo thai trovato nel sorgente")

    user_visible_calls: list[str] = []
    for call_name in ("Create HUD Text", "Create In-World Text", "Small Message", "Big Message"):
        user_visible_calls.extend(call_texts(source, call_name))
    genres_set = set(genres)
    for index, call in enumerate(user_visible_calls, start=1):
        literals = custom_strings(call)
        if not any(translatable_literal(value, genres_set) for value in literals):
            continue
        checks.require(
            THAI_RE.search(call) is not None,
            f"testo visibile localizzabile #{index} privo di variante thai",
        )
        checks.require(
            "IndeksBahasa" in call,
            f"testo visibile localizzabile #{index} non dipende dalla lingua del client",
        )

    return genres, extract_rules(source)


def check_source_structure(
    checks: Checks,
    source: str,
    rules: list[Rule],
    global_names: set[str],
    player_names: set[str],
    subroutines: set[str],
) -> None:
    checks.require(source.lstrip().startswith("variables"), "il sorgente deve iniziare con variables")
    checks.require(
        re.search(r"(?m)^\s*settings\s*\{", source) is None,
        "il progetto deve restare un overlay senza blocco settings",
    )
    checks.require(len(rules) >= 20, f"numero di regole troppo basso: {len(rules)}")
    checks.equal(len({rule.name for rule in rules}), len(rules), "nomi regola unici")

    for rule in rules:
        event_match = re.search(r"(?ms)^\s*event\s*\{\s*([^;\n]+)\s*;", rule.body)
        checks.require(event_match is not None, f"blocco event non riconosciuto in {rule.name!r}")
        if event_match is not None:
            event_type = event_match.group(1).strip()
            checks.require(
                event_type in VALID_EVENT_TYPES,
                f"tipo evento Workshop non valido {event_type!r} in {rule.name!r}",
            )

    for table_name, names in (
        ("global", global_names), ("player", player_names), ("subroutine", subroutines)
    ):
        checks.require(bool(names), f"tabella {table_name} vuota")
        for name in sorted(names):
            hits = set(identifier_tokens(name)) & ITALIAN_WORDS
            checks.require(
                not hits,
                f"identificatore {table_name} non indonesiano {name!r}: {sorted(hits)}",
            )

    for rule in rules:
        hits = italian_hits(rule.name)
        checks.require(
            not hits,
            f"nome regola non indonesiano {rule.name!r}: {sorted(hits)}",
        )
    for number, comment in standalone_comments(source):
        hits = italian_hits(comment)
        checks.require(
            not hits,
            f"commento non indonesiano alla riga {number}: {sorted(hits)}",
        )

    stale_identifiers = {
        "DurataServerMinuti", "MorteRevenge", "KillerRevenge", "JumlahRevenge",
        "DaftarTargetRevenge", "TargetRevenge", "GambarRevenge", "GambarTeleport",
        "PosSpawnRoom", "NomorUrut",
    }
    declared = global_names | player_names | subroutines
    stale = sorted(stale_identifiers & declared)
    checks.require(not stale, f"identificatori legacy non indonesiani: {stale}")

    custom_literals = custom_strings(source)
    too_long = [value for value in custom_literals if len(value) > 128]
    checks.require(
        not too_long,
        f"Custom String oltre 128 caratteri: {too_long[:3]}",
    )
    bad_placeholders = [
        value
        for value in custom_literals
        if any(int(index) > 2 for index in re.findall(r"\{(\d+)\}", value))
    ]
    checks.require(
        not bad_placeholders,
        f"Custom String con placeholder oltre {{2}}: {bad_placeholders[:3]}",
    )

    checks.equal(source.count("\u200b"), 2, "occorrenze della sentinella U+200B")
    checks.equal(
        len(re.findall(r'Custom\s+String\s*\(\s*"\u200b"\s*\)', source)),
        2,
        "sentinelle U+200B racchiuse in Custom String",
    )


def check_timer_and_match(checks: Checks, source: str, rules: list[Rule]) -> None:
    for name in (
        "DurasiServerMenit", "WaktuMulaiServer", "WaktuAkhirServer", "SisaWaktuServer",
        "TeksWaktuServer", "RestartSudahDiminta",
    ):
        checks.require(f"Global.{name}" in source, f"timer: variabile {name} assente")

    checks.require(
        re.search(
            r"Global\.DurasiServerMenit\s*=\s*Workshop Setting Integer\s*\(.*?30\s*,\s*30\s*,\s*90\s*,\s*0\s*\)",
            source,
            re.DOTALL,
        )
        is not None,
        "timer: impostazione durata non vincolata a 30..90 minuti",
    )
    checks.require(
        re.search(r"Global\.WaktuMulaiServer\s*=\s*Total Time Elapsed\s*;", source) is not None,
        "timer: baseline WaktuMulaiServer non inizializzata da Total Time Elapsed",
    )
    checks.require(
        re.search(
            r"Global\.WaktuAkhirServer\s*=\s*Global\.WaktuMulaiServer\s*\+\s*Global\.DurasiServerMenit\s*\*\s*60\s*;",
            source,
        )
        is not None,
        "timer: deadline non derivata da baseline + durata",
    )
    checks.require(
        re.search(
            r"Global\.SisaWaktuServer\s*=.*Global\.WaktuAkhirServer\s*-\s*Total Time Elapsed",
            source,
        )
        is not None,
        "timer: tempo residuo non derivato dalla deadline",
    )

    timer_rules = [
        rule
        for rule in rules_containing(rules, "Global.TeksWaktuServer", "Global.SisaWaktuServer")
        if "Loop If Condition Is True;" in rule.body
    ]
    checks.equal(len(timer_rules), 1, "regole di aggiornamento stringa timer")
    if timer_rules:
        checks.require(
            re.search(r"Wait\s*\(\s*1(?:\.0+)?\s*,", timer_rules[0].body) is not None,
            "timer: la stringa deve aggiornarsi una volta al secondo",
        )
    checks.require(
        any("Global.TeksWaktuServer" in call for call in call_texts(source, "Create HUD Text")),
        "timer: l'HUD non usa la stringa globale precomputata",
    )

    clean = mask_strings(source)
    forbidden_actions = (
        "Declare Match Draw", "Declare Player Victory", "Declare Team Victory",
        "Declare Round Victory", "Declare Round Draw", "Set Team Score", "Modify Team Score",
        "Set Player Score", "Modify Player Score", "End Game",
    )
    for action in forbidden_actions:
        checks.require(
            re.search(rf"\b{re.escape(action)}\s*\(?", clean) is None,
            f"azione di punteggio/vittoria vietata: {action}",
        )
    checks.require(
        "Disable Built-In Game Mode Completion;" in clean,
        "protezione completamento nativo assente",
    )
    checks.require(
        "Disable Built-In Game Mode Scoring;" in clean,
        "protezione punteggio nativo assente",
    )
    checks.require(
        "Enable Built-In Game Mode Completion;" not in clean
        and "Enable Built-In Game Mode Scoring;" not in clean,
        "completion/scoring nativo non deve essere riattivato",
    )
    checks.equal(len(re.findall(r"\bRestart Match\s*;", clean)), 1, "azioni Restart Match")
    restart_rules = rules_containing(rules, "Restart Match;")
    checks.equal(len(restart_rules), 1, "regole che possono riavviare la partita")
    if restart_rules:
        restart = restart_rules[0].body
        checks.require(
            re.search(r"Global\.SisaWaktuServer\s*<=\s*0", restart) is not None,
            "Restart Match non è condizionato dal timer personalizzato a zero",
        )
        checks.require(
            "Global.RestartSudahDiminta == False;" in restart,
            "Restart Match privo di guardia one-shot",
        )
        set_guard = restart.find("Global.RestartSudahDiminta = True;")
        restart_at = restart.find("Restart Match;")
        checks.require(
            0 <= set_guard < restart_at,
            "la guardia RestartSudahDiminta deve essere impostata prima del riavvio",
        )


def check_bot_lifecycle(checks: Checks, source: str, rules: list[Rule]) -> None:
    classification = rules_containing(rules, "Start Forcing Dummy Bot Name", "Stop Forcing Dummy Bot Name")
    checks.equal(len(classification), 1, "regole di classificazione umano/bot")
    if classification:
        body = classification[0].body
        waits = [match.start() for match in re.finditer(r"Wait\s*\(\s*0\.016\s*,", body)]
        entities = [match.start() for match in re.finditer(r"Entity Exists\s*\(\s*Event Player\s*\)", body)]
        checks.equal(len(waits), 2, "Wait(0.016) nella classificazione")
        registration = body.find("Append To Array(Global.PemainManusia, Event Player)")
        checks.require(registration >= 0, "classificazione: registrazione umano non trovata")
        if len(waits) == 2:
            after_first = next((position for position in entities if waits[0] < position < waits[1]), -1)
            after_second = next(
                (position for position in entities if waits[1] < position < registration), -1
            )
            checks.require(after_first >= 0, "classificazione: Entity Exists assente dopo il primo Wait")
            checks.require(after_second >= 0, "classificazione: Entity Exists assente dopo il secondo Wait e prima della registrazione")

    bot_calls = rules_containing(rules, "Call Subroutine(KunciBot)")
    checks.require(len(bot_calls) >= 2, "KunciBot deve essere richiamata da classificazione e riattivazione edge-triggered")
    for rule in bot_calls:
        is_watchdog = (
            re.search(r"Wait\s*\(\s*0\.500\s*,", rule.body) is not None
            and "Loop If Condition Is True;" in rule.body
        )
        checks.require(not is_watchdog, f"watchdog bot periodico ancora presente in {rule.name!r}")
    checks.require("Player Spawned;" not in source, "tipo evento inesistente Player Spawned ancora presente")
    inactive_reset = [
        rule for rule in rules
        if "Ongoing - Each Player;" in rule.body
        and "Event Player.KunciBotAktif = False;" in rule.body
        and "Is Dummy Bot(Event Player)" in rule.body
        and "Event Player.KunciBotAktif == True;" in rule.body
        and "Has Spawned(Event Player) == False" in rule.body
        and "Is Alive(Event Player) == False" in rule.body
    ]
    checks.equal(len(inactive_reset), 1, "reset del latch bot alla morte o al despawn")
    reactivation = [
        rule for rule in bot_calls
        if "Ongoing - Each Player;" in rule.body
        and "Is Alive(Event Player) == True;" in rule.body
        and "Event Player.KunciBotAktif == False" in rule.body
        and "Hero Of(Event Player) != Event Player.PahlawanBotTerakhir" in rule.body
    ]
    checks.equal(len(reactivation), 1, "riattivazione bot dopo respawn o cambio eroe")

    lock_rules = rules_containing(rules, "Subroutine;", "KunciBot;")
    checks.require(bool(lock_rules), "subroutine KunciBot non trovata")
    if lock_rules:
        checks.require(
            "Abort If(Is Alive(Event Player) == False);" in lock_rules[0].body,
            "KunciBot non protegge la race con morte/despawn",
        )
        for action in (
            "Set Primary Fire Enabled(Event Player, False)",
            "Set Secondary Fire Enabled(Event Player, False)",
            "Set Ability 1 Enabled(Event Player, False)",
            "Set Ability 2 Enabled(Event Player, False)",
            "Set Ultimate Ability Enabled(Event Player, False)",
            "Set Melee Enabled(Event Player, False)",
            "Set Damage Dealt(Event Player, 0)",
            "Set Healing Dealt(Event Player, 0)",
            "Set Knockback Dealt(Event Player, 0)",
        ):
            checks.require(action in lock_rules[0].body, f"KunciBot incompleta: {action}")


def check_menus(checks: Checks, source: str, rules: list[Rule], subroutines: set[str]) -> None:
    codes = [re.sub(r"\s+", "", item) for item in top_level_items(array_body(source, "Global.KodeMenu"))]
    checks.equal(codes, ["0", "1", "2", "3", "4", "5"], "codici dei sei menu")
    checks.require(
        re.search(r"KursorUtama\s*=\s*\([^;]+\)\s*%\s*6\s*;", source) is not None,
        "navigazione principale non limitata a sei menu",
    )
    checks.require(
        re.search(r"KursorBahasa\s*=\s*\([^;]+\)\s*%\s*3\s*;", source) is not None,
        "selettore lingua non usa modulo 3",
    )

    expected_renderers = {
        "GambarUtama", "GambarMusik", "GambarKamera", "GambarWarna", "GambarBahasa",
        "GambarBalasDendam", "GambarTeleportasi",
    }
    missing_renderers = sorted(expected_renderers - subroutines)
    checks.require(not missing_renderers, f"renderer menu mancanti: {missing_renderers}")
    router_rules = rules_containing(rules, "Subroutine;", "GambarMenu;")
    checks.equal(len(router_rules), 1, "router GambarMenu")
    if router_rules:
        router = router_rules[0].body
        checks.require("Create HUD Text" not in router, "GambarMenu deve restare un router leggero")
        for renderer in sorted(expected_renderers):
            checks.require(
                f"Call Subroutine({renderer});" in router,
                f"GambarMenu non instrada {renderer}",
            )

    dispatcher_candidates = [
        rule
        for rule in rules
        if "MenuTerbuka == True;" in rule.body
        and all(
            f"Button({button})" in rule.body
            for button in ("Interact", "Reload", "Primary Fire", "Secondary Fire", "Jump", "Crouch")
        )
    ]
    checks.equal(len(dispatcher_candidates), 1, "dispatcher unico degli input menu")
    if dispatcher_candidates:
        dispatcher = dispatcher_candidates[0].body
        positions = [
            dispatcher.find(f"Is Button Held(Event Player, Button({button}))")
            for button in ("Interact", "Reload", "Primary Fire", "Secondary Fire", "Jump", "Crouch")
        ]
        checks.require(
            all(position >= 0 for position in positions) and positions == sorted(positions),
            "priorità dispatcher errata; attesa Interact → Reload → Primary → Secondary → Jump → Crouch",
        )

    release_candidates = [
        rule
        for rule in rules
        if "Event Player.PerintahMenu != 0;" in rule.body
        and "Event Player.PerintahMenu = 0;" in rule.body
        and all(
            f"Is Button Held(Event Player, Button({button})) == False" in rule.body
            for button in ("Interact", "Reload", "Primary Fire", "Secondary Fire", "Jump", "Crouch")
        )
    ]
    checks.equal(len(release_candidates), 1, "release gate chord-safe del dispatcher")
    if release_candidates:
        checks.require(
            re.search(r"Wait\s*\(\s*0\.016\s*,\s*Ignore Condition\s*\)", release_candidates[0].body)
            is not None,
            "release gate dispatcher privo del tick di arbitraggio prima del reset",
        )
    for command in range(1, 7):
        handlers = [rule for rule in rules if f"Event Player.PerintahMenu == {command};" in rule.body]
        checks.equal(len(handlers), 1, f"handler dispatcher comando {command}")
        if handlers:
            checks.require(
                "Event Player.PerintahMenu = 0;" not in handlers[0].body,
                f"handler {command} resetta il dispatcher prima del rilascio di tutti gli input",
            )

    melee_rules = [
        rule for rule in rules
        if "Button(Melee)" in rule.body and "Abort When False" in rule.body
    ]
    checks.equal(len(melee_rules), 1, "gestori pressione lunga Melee")
    if melee_rules:
        checks.require(
            re.search(r"Wait\s*\(\s*0\.500\s*,\s*Abort When False\s*\)", melee_rules[0].body)
            is not None,
            "Melee deve richiedere esattamente 0,5 secondi",
        )
    checks.require("Wait(1.250" not in source, "durata Melee legacy da 1,25 secondi ancora presente")
    checks.require(
        re.search(r"KursorGenre\s*=\s*\([^;]+\+\s*10\)\s*%\s*100", source) is not None,
        "salto musicale +10 assente",
    )
    checks.require(
        re.search(r"KursorGenre\s*=\s*\([^;]+\+\s*90\)\s*%\s*100", source) is not None,
        "salto musicale -10 assente",
    )

    for rule in rules:
        refreshes_dynamic_menu = any(
            token in rule.body
            for token in ("SegarkanTargetBalasDendam", "SegarkanTargetTeleportasi")
        )
        periodic = "Loop If Condition Is True;" in rule.body
        checks.require(
            not (refreshes_dynamic_menu and periodic and "Call Subroutine(GambarMenu);" in rule.body),
            f"ridisegno periodico del menu ancora presente in {rule.name!r}",
        )


def check_camera(
    checks: Checks, source: str, rules: list[Rule], player_names: set[str]
) -> None:
    legacy_cache_names = (
        "TitikJangkarKamera", "TitikIdealKamera", "TitikBenturanKamera", "TitikAkhirKamera",
        "ArahMendatarKamera", "PosisiRelatifKamera", "TinggiJangkarKamera",
    )
    for name in legacy_cache_names:
        checks.require(name not in player_names, f"cache camera server legacy ancora dichiarata: {name}")
        checks.require(f"Event Player.{name}" not in source, f"cache camera server legacy ancora usata: {name}")
    checks.equal(len(call_texts(source, "Ray Cast Hit Position")), 1, "Ray Cast Hit Position nel sorgente")
    ray_rules = rules_containing(rules, "Ray Cast Hit Position")
    checks.equal(len(ray_rules), 1, "regole che eseguono il raycast camera")
    if ray_rules:
        checks.require(
            "Subroutine;" in ray_rules[0].body and "MulaiKamera;" in ray_rules[0].body,
            "raycast camera non confinato alla subroutine MulaiKamera",
        )
    camera_loops = [
        rule for rule in rules
        if "ModeKamera != 0;" in rule.body and "Loop If Condition Is True;" in rule.body
    ]
    checks.equal(len(camera_loops), 0, "loop server di aggiornamento camera")
    camera_starts = call_texts(source, "Start Camera")
    checks.equal(len(camera_starts), 1, "Start Camera nel sorgente")
    if camera_starts:
        opening = camera_starts[0].find("(")
        args = top_level_items(camera_starts[0][opening + 1 : -1])
        checks.equal(len(args), 4, "argomenti Start Camera")
        if len(args) == 4:
            eye = args[1]
            look = args[2]
            eye_inner = whole_call_argument(eye, "Update Every Frame")
            look_inner = whole_call_argument(look, "Update Every Frame")
            checks.require(
                eye_inner is not None and eye_inner.startswith("First Of(Mapped Array(Array(Ray Cast Hit Position("),
                "posizione camera non è un raycast monouso rivalutato interamente per frame",
            )
            checks.equal(len(call_texts(eye, "Ray Cast Hit Position")), 1, "raycast nell'occhio Start Camera")
            for token in (
                "First Of(Mapped Array(Array(Ray Cast Hit Position(",
                "Eye Position(Event Player.TargetKamera)",
                "Max Health(Event Player.TargetKamera)",
                "- Facing Direction Of(Event Player.TargetKamera) * Min(4.500, Max(",
                "Cross Product(", "Empty Array, Empty Array, False", "Current Array Element",
                "Min(Global.BantalanDinding, Distance Between(", "* 0.250",
            ):
                checks.require(token in eye, f"espressione camera diretta incompleta: {token}")
            compact_eye = re.sub(r"\s+", "", eye)
            full_facing = "FacingDirectionOf(EventPlayer.TargetKamera)"
            horizontal_facing = "HorizontalFacingAngleOf(EventPlayer.TargetKamera)"
            checks.equal(compact_eye.count(full_facing), 1, "Facing Direction pitch-aware nell'occhio camera")
            checks.equal(compact_eye.count(horizontal_facing), 1, "yaw stabile nell'offset laterale camera")
            checks.require(
                f"-{full_facing}*Min(4.500,Max(" in compact_eye,
                "braccio posteriore camera non segue il pitch completo",
            )
            checks.require(
                f"CrossProduct(DirectionFromAngles({horizontal_facing},0),Vector(0,1,0))*Min(1.350,Max(" in compact_eye,
                "offset laterale camera non è confinato allo yaw",
            )
            checks.require(
                "HorizontalAngleFromDirection(" not in compact_eye,
                "proiezione yaw legacy instabile ancora presente nella camera",
            )
            checks.require(
                eye.count("Update Every Frame(") == 1,
                "posizione camera contiene rivalutazioni annidate o miste",
            )
            checks.require(
                "Position Of(Event Player.TargetKamera)" not in eye,
                "posizione camera mescola Position Of con la pipeline visuale Eye Position",
            )
            checks.require(
                look_inner is not None
                and look_inner.startswith("Eye Position(Event Player.TargetKamera)")
                and "Facing Direction Of(Event Player.TargetKamera)" in look_inner,
                "punto di mira camera non rivalutato per frame dall'occhio del target",
            )
            eye_player_refs = set(re.findall(r"Event Player\.([A-Za-z_][A-Za-z0-9_]*)", eye))
            eye_global_refs = set(re.findall(r"Global\.([A-Za-z_][A-Za-z0-9_]*)", eye))
            look_player_refs = set(re.findall(r"Event Player\.([A-Za-z_][A-Za-z0-9_]*)", look))
            look_global_refs = set(re.findall(r"Global\.([A-Za-z_][A-Za-z0-9_]*)", look))
            checks.equal(eye_player_refs, {"TargetKamera"}, "riferimenti player nell'occhio camera")
            checks.equal(
                eye_global_refs,
                {"JarakKamera", "GeserKamera", "BantalanDinding"},
                "riferimenti globali nell'occhio camera",
            )
            checks.equal(look_player_refs, {"TargetKamera"}, "riferimenti player nel punto di mira")
            checks.equal(look_global_refs, {"JarakBidik"}, "riferimenti globali nel punto di mira")
            checks.equal(args[3], "0", "blend Start Camera per aggancio diretto tipo prima persona")


def check_crouch(checks: Checks, source: str, rules: list[Rule]) -> None:
    checks.equal(
        len(call_texts(source, "Disable Nameplates")), 1,
        "Disable Nameplates Crouch",
    )
    checks.equal(
        len(call_texts(source, "Enable Nameplates")), 2,
        "Enable Nameplates cleanup",
    )
    checks.equal(
        len(call_texts(source, "Create In-World Text")), 2,
        "testi mondo Crouch",
    )
    checks.equal(
        len(call_texts(source, "Start Forcing Player Outlines")), 0,
        "Start Forcing Player Outlines",
    )
    checks.equal(
        len(call_texts(source, "Stop Forcing Player Outlines")), 0,
        "Stop Forcing Player Outlines",
    )
    checks.require(
        "IndeksGarisLuar" not in source,
        "variabile outline ancora presente",
    )

    registration = rules_containing(
        rules,
        "Append To Array(Global.PemainManusia, Event Player)",
    )
    checks.equal(
        len(registration), 1,
        "regola registrazione HUD sociali",
    )

    if registration:
        huds = call_texts(
            registration[0].body,
            "Create HUD Text",
        )
        checks.equal(
            len(huds), 2,
            "HUD sociali per giocatore",
        )

        for i, call in enumerate(huds, 1):
            checks.require(
                "Hero Icon String" in call,
                f"HUD sociale #{i} privo di icona eroe",
            )

    starts = [
        r for r in rules
        if "Event Player.InspeksiAktif = True;" in r.body
        and "Disable Nameplates" in r.body
        and "Create In-World Text" in r.body
    ]

    checks.equal(
        len(starts), 1,
        "regola avvio Crouch",
    )

    if starts:
        checks.equal(
            len(re.findall(
                r",\s*0\.900\s*,\s*Do Not Clip",
                starts[0].body,
            )),
            2,
            "dimensione testi Crouch",
        )

        checks.require(
            "Color(Orange)" in starts[0].body,
            "testo bot Crouch non arancione",
        )

    refresh = [
        r for r in rules
        if "SegarkanTargetInspeksi" in r.body
        and "Loop If Condition Is True;" in r.body
    ]

    checks.equal(
        len(refresh), 1,
        "loop refresh target Crouch",
    )

    if refresh:
        checks.require(
            re.search(
                r"Wait\s*\(\s*0\.100\s*,",
                refresh[0].body,
            ) is not None,
            "refresh Crouch non a 0,10 s",
        )

    cleanup = [
        r for r in rules_containing(
            rules,
            "Enable Nameplates",
        )
        if "Event Player.InspeksiAktif = False;" in r.body
    ]

    checks.equal(
        len(cleanup), 1,
        "cleanup Crouch",
    )

    if cleanup:
        checks.require(
            cleanup[0].body.count("Destroy In-World Text") >= 2,
            "cleanup non distrugge entrambi i testi",
        )

        checks.require(
            "Event Player.TeksDunia = Null;" in cleanup[0].body
            and "Event Player.TeksDiri = Null;" in cleanup[0].body,
            "cleanup non azzera i testi",
        )


def check_cleanup_and_revenge(checks: Checks, source: str, rules: list[Rule]) -> None:
    checks.require("Global.SlotHUDTersedia" in source, "pool SlotHUDTersedia assente")
    checks.require("Global.SlotHUDPemain" in source, "registro parallelo SlotHUDPemain assente")
    checks.require("Global.NomorUrut" not in source, "contatore HUD NomorUrut non è stato rimosso")
    try:
        slots = [re.sub(r"\s+", "", item) for item in top_level_items(array_body(source, "Global.SlotHUDTersedia"))]
    except ParseError:
        slots = []
    checks.equal(len(slots), 12, "slot HUD preallocati")
    checks.equal(slots, [str(index) for index in range(12)], "pool iniziale degli slot HUD 0..11")
    checks.require(
        "Event Player.UrutanHUD = First Of(Global.SlotHUDTersedia);" in source
        and "Modify Global Variable(SlotHUDTersedia, Remove From Array By Index, 0);" in source,
        "allocazione del primo slot HUD libero assente o non atomica",
    )

    leave_rules = [rule for rule in rules if "Player Left Match;" in rule.body]
    checks.equal(len(leave_rules), 1, "regole Player Left Match")
    if leave_rules:
        leave = leave_rules[0].body
        checks.require(
            leave.find("Global.PemainPembersihan = Event Player;")
            < leave.find("Global.IndeksKeluar = Index Of Array Value(Global.PemainManusia, Event Player);"),
            "cleanup uscita non cattura subito l'identità del giocatore",
        )
        removal_at = leave.find("Modify Global Variable(PemainManusia, Remove From Array By Index")
        checks.require(removal_at >= 0, "cleanup uscita non rimuove il giocatore dal roster")
        if removal_at >= 0:
            checks.require(
                "Event Player." not in leave[removal_at:],
                "cleanup uscita legge variabili dell'entità dopo averla rimossa dal roster",
            )
        for collection in (
            "PemainManusia", "HudKiriPemain", "HudKananPemain", "HudMenuPemain",
            "TeksDuniaPemain", "TeksDiriPemain", "SlotHUDPemain",
        ):
            checks.require(
                re.search(
                    rf"Modify Global Variable\s*\(\s*{collection}\s*,\s*Remove From Array By Index",
                    leave,
                )
                is not None,
                f"cleanup uscita non allineato per Global.{collection}",
            )
        checks.require(
            "Sorted Array(Append To Array(Global.SlotHUDTersedia, Global.SlotHUDPemain[Global.IndeksKeluar])"
            in leave,
            "cleanup uscita non libera lo slot HUD",
        )
        checks.require("For Global Variable" in leave, "cleanup uscita non visita tutti i superstiti")
        checks.require("BalasDendam" in leave, "cleanup uscita non ripulisce i ledger BalasDendam")
        checks.require("Stop Camera" in leave, "cleanup uscita non ferma le camere puntate all'uscente")

    for name in ("TargetBalasDendamDipilih", "TargetBalasDendamTerkunci"):
        checks.require(f"Event Player.{name}" in source, f"Revenge: variabile {name} assente")
    claim_rules = rules_containing(rules, "TargetBalasDendamTerkunci", "Kill(")
    checks.equal(len(claim_rules), 1, "regole claim BalasDendam con target catturato")
    if claim_rules:
        claim = claim_rules[0].body
        capture_match = re.search(
            r"Event Player\.TargetBalasDendamTerkunci\s*=\s*Event Player\.DaftarTargetBalasDendam\s*\[\s*Event Player\.KursorBalasDendam\s*\]\s*;",
            claim,
        )
        capture = -1 if capture_match is None else capture_match.start()
        kill_at = claim.find("Kill(Event Player.TargetBalasDendamTerkunci, Event Player);")
        checks.require(0 <= capture < kill_at, "target BalasDendam non catturato per identità prima del claim")
        wait_at = claim.find("Wait(", capture + 1)
        if wait_at >= 0:
            after_wait = claim[wait_at:]
            checks.require(
                "TargetBalasDendamTerkunci" in after_wait,
                "claim BalasDendam non usa il riferimento catturato dopo il Wait",
            )
            checks.require(
                "TargetBalasDendamDipilih" not in after_wait,
                "claim BalasDendam dipende ancora dalla selezione mutevole dopo il Wait",
            )
    refresh_rules = rules_containing(
        rules, "Event Player.TargetBalasDendamDipilih", "Event Player.DaftarTargetBalasDendam = Filtered Array"
    )
    checks.equal(len(refresh_rules), 1, "refresh BalasDendam che preserva il target per identità")

    death_rules = [rule for rule in rules if "Player Died;" in rule.body]
    checks.require(bool(death_rules), "regola Player Died per BalasDendam assente")
    if death_rules:
        death = "\n".join(rule.body for rule in death_rules)
        checks.require(
            re.search(r"Event Player\.[A-Za-z0-9_]*BalasDendam[A-Za-z0-9_]*\s*=\s*False\s*;", death)
            is not None,
            "Player Died non azzera il flag della morte BalasDendam",
        )


def check_diagnostics(checks: Checks, source: str, rules: list[Rule]) -> None:
    toggle = re.search(
        r"Global\.DiagnostikPerforma\s*=\s*Workshop Setting Toggle\s*\((.*?)\)\s*;",
        source,
        re.DOTALL,
    )
    checks.require(toggle is not None, "toggle Performance diagnostics assente")
    if toggle is not None:
        arguments = top_level_items(toggle.group(1))
        checks.require(
            len(arguments) >= 3 and arguments[2].strip() == "False",
            "Performance diagnostics deve essere OFF per impostazione predefinita",
        )
    for metric in ("Server Load", "Server Load Average", "Server Load Peak"):
        checks.require(metric in source, f"diagnostica priva di {metric}")
    diagnostic_rules = [
        rule for rule in rules
        if "DiagnostikPerforma" in rule.body and "Server Load" in rule.body
    ]
    checks.require(bool(diagnostic_rules), "regola HUD diagnostica non trovata")
    if diagnostic_rules:
        diagnostic = "\n".join(rule.body for rule in diagnostic_rules)
        checks.require("Host Player" in diagnostic, "diagnostica non limitata all'host")
        checks.require(
            (
                (
                    "HudKiriPemain" in diagnostic
                    and ("HudKananPemain" in diagnostic or re.search(r"Count Of\(Global\.HudKiriPemain\)\s*\*\s*2", diagnostic))
                )
                and all(token in diagnostic for token in ("HudMenuPemain", "TeksDuniaPemain", "TeksDiriPemain"))
            ),
            "diagnostica priva dei conteggi HUD/IWT",
        )
    inspector_rules = rules_containing(
        rules, "Global.DiagnostikPerforma == False", "Disable Inspector Recording;"
    )
    checks.equal(len(inspector_rules), 1, "disabilitazione Inspector quando la diagnostica è OFF")


def check_documentation_and_ci(checks: Checks, genres: list[str]) -> None:
    checks.require(VERSION.exists(), f"file VERSION mancante: {VERSION}")
    if VERSION.exists():
        checks.equal(VERSION.read_text(encoding="utf-8").strip(), CURRENT_VERSION, "versione progetto")

    documentation_markers = {
        ROOT / "README.md": f"La versione **{CURRENT_VERSION}**",
        ROOT / "docs" / "PROGETTO.md": f"# Note di progetto — versione {CURRENT_VERSION}",
        ROOT / "docs" / "TEST.md": f"# Piano di test — versione {CURRENT_VERSION}",
        ROOT / "docs" / "VALIDAZIONE.md": f"# Rapporto di validazione — versione {CURRENT_VERSION}",
    }
    for path, marker in documentation_markers.items():
        checks.require(path.exists(), f"documentazione mancante: {path.relative_to(ROOT)}")
        if path.exists():
            checks.require(
                marker in path.read_text(encoding="utf-8"),
                f"versione documentazione non allineata: {path.relative_to(ROOT)}",
            )

    validation_report = ROOT / "docs" / "VALIDAZIONE.md"
    if validation_report.exists():
        report = validation_report.read_text(encoding="utf-8")
        checks.equal(
            report.count(f"OK - controlli statici v{CURRENT_VERSION} superati"),
            1,
            "esito registrato in docs/VALIDAZIONE.md",
        )

    checks.require(GENRE_DOC.exists(), f"documentazione generi mancante: {GENRE_DOC}")
    if GENRE_DOC.exists():
        documented = re.findall(
            r"^\d+\. (.+)$", GENRE_DOC.read_text(encoding="utf-8"), flags=re.MULTILINE
        )
        checks.equal(documented, genres, "docs/GENERI.md rispetto a DaftarGenre")

    for legacy in LEGACY_AUTOMATION:
        checks.require(not legacy.exists(), f"automazione auto-modificante legacy ancora presente: {legacy.relative_to(ROOT)}")
    checks.require(WORKFLOW.exists(), f"workflow read-only mancante: {WORKFLOW.relative_to(ROOT)}")
    if WORKFLOW.exists():
        workflow = WORKFLOW.read_text(encoding="utf-8")
        checks.require(
            re.search(r"(?m)^permissions:\s*\n\s+contents:\s*read\s*$", workflow) is not None,
            "workflow senza permissions.contents: read",
        )
        forbidden = ("contents: write", "git push", "git commit", "p.write_text", "apply_patch")
        for token in forbidden:
            checks.require(token not in workflow, f"workflow non read-only: trovato {token!r}")
        checks.require(
            "python tools/validate_workshop.py" in workflow,
            "workflow non esegue tools/validate_workshop.py",
        )


def main() -> None:
    checks = Checks()
    if not SOURCE.exists():
        checks.require(False, f"sorgente mancante: {SOURCE}")
        checks.finish()
    source = SOURCE.read_text(encoding="utf-8")
    for error in balanced_errors(source):
        checks.require(False, error)

    try:
        global_names, player_names, subroutines = declaration_tables(source)
        genres, rules = check_language_arrays(checks, source)
        check_source_structure(checks, source, rules, global_names, player_names, subroutines)
        check_timer_and_match(checks, source, rules)
        check_bot_lifecycle(checks, source, rules)
        check_menus(checks, source, rules, subroutines)
        check_camera(checks, source, rules, player_names)
        check_crouch(checks, source, rules)
        check_cleanup_and_revenge(checks, source, rules)
        check_diagnostics(checks, source, rules)
        check_documentation_and_ci(checks, genres)
    except ParseError as exc:
        checks.require(False, f"parsing interrotto: {exc}")

    checks.finish()
    print(f"OK - controlli statici v{CURRENT_VERSION} superati")
    print(
        f"Generi: {len(genres)} | Lingue: 3 | Regole: {len(rules)} | "
        f"Raycast camera: {len(call_texts(source, 'Ray Cast Hit Position'))}"
    )
    print("Nota: importazione, stress a 12 giocatori e test modalità restano prove live obbligatorie.")


if __name__ == "__main__":
    main()
