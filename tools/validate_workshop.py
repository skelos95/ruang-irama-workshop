#!/usr/bin/env python3
"""Validazione statica del sorgente Overwatch Workshop.

Il validatore controlla invarianti strutturali e di progetto della versione 0.5.5.
Non sostituisce l'importazione nel client o le prove live con dodici giocatori.
"""

from __future__ import annotations

import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CURRENT_VERSION = "0.5.5"
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
GENRE_DOC = ROOT / "docs" / "GENERI.md"
VERSION = ROOT / "VERSION"
WORKFLOW = ROOT / ".github" / "workflows" / "validate-workshop.yml"
MAINTENANCE_WORKFLOW = ROOT / ".github" / "workflows" / "maintenance-patch.yml"
ALLOWED_WORKFLOW_NAMES = {"validate-workshop.yml", "maintenance-patch.yml"}
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


def git_blob_sha(path: Path) -> str:
    """Calcola lo SHA-1 del blob Git, normalizzando le line ending testuali."""
    data = path.read_bytes().replace(b"\r\n", b"\n")
    payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    return hashlib.sha1(payload).hexdigest()


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
    openings = {"{": "}", "(": ")", "[": "]"}
    closings = {closing: opening for opening, closing in openings.items()}
    labels = {"{": "graffa", "(": "parentesi", "[": "parentesi quadra"}
    stack: list[tuple[str, int]] = []
    for index, char in enumerate(clean):
        if char in openings:
            stack.append((char, index))
        elif char in closings:
            if not stack:
                errors.append(
                    f"{labels[closings[char]]} chiusa troppo presto alla riga "
                    f"{line_number(source, index)}"
                )
                continue
            opening, opening_at = stack[-1]
            if opening != closings[char]:
                errors.append(
                    f"delimitatori annidati male alla riga {line_number(source, index)}: "
                    f"{opening!r} aperto alla riga {line_number(source, opening_at)} "
                    f"e chiuso con {char!r}"
                )
                stack.pop()
                continue
            stack.pop()
    for opening, opening_at in stack:
        errors.append(
            f"{labels[opening]} non chiusa; apertura alla riga "
            f"{line_number(source, opening_at)}"
        )
    return errors


def section_body(source: str, name: str) -> str:
    clean = mask_strings(source)
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*\{{", clean)
    if match is None:
        raise ParseError(f"sezione {name!r} non trovata")
    opening = clean.find("{", match.start())
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

    def names(body: str, label: str) -> set[str]:
        entries: list[tuple[int, str]] = []
        for line_offset, line in enumerate(body.splitlines(), start=1):
            if not line.strip():
                continue
            match = re.fullmatch(
                r"\s*(\d+)\s*:\s*([A-Za-z_][A-Za-z0-9_]*)\s*", line
            )
            if match is None:
                raise ParseError(
                    f"dichiarazione {label} malformata alla riga relativa {line_offset}: "
                    f"{line.strip()!r}"
                )
            entries.append((int(match.group(1)), match.group(2)))

        slots = [slot for slot, _ in entries]
        declared_names = [name for _, name in entries]
        duplicate_slots = sorted({slot for slot in slots if slots.count(slot) > 1})
        duplicate_names = sorted(
            {name for name in declared_names if declared_names.count(name) > 1}
        )
        if duplicate_slots:
            raise ParseError(f"slot {label} duplicati: {duplicate_slots}")
        if duplicate_names:
            raise ParseError(f"nomi {label} duplicati: {duplicate_names}")
        return set(declared_names)

    subroutine_names = names(section_body(source, "subroutines"), "subroutine")
    return (
        names(global_match.group(1), "global"),
        names(player_match.group(1), "player"),
        subroutine_names,
    )


def rule_section_names(body: str, rule_name: str) -> list[str]:
    """Estrae e valida i blocchi top-level di una regola Workshop."""
    clean = mask_strings(body)
    sections: list[str] = []
    index = 0
    while index < len(clean):
        while index < len(clean) and clean[index].isspace():
            index += 1
        if index >= len(clean):
            break
        name_match = re.match(r"[A-Za-z][A-Za-z0-9_-]*", clean[index:])
        if name_match is None:
            raise ParseError(
                f"token top-level inatteso nella regola {rule_name!r} alla riga relativa "
                f"{line_number(body, index)}"
            )
        name = name_match.group(0)
        index += len(name)
        while index < len(clean) and clean[index].isspace():
            index += 1
        if index >= len(clean) or clean[index] != "{":
            raise ParseError(
                f"blocco top-level {name!r} malformato nella regola {rule_name!r}"
            )
        closing = find_matching(clean, index, "{", "}")
        sections.append(name)
        index = closing + 1

    allowed_orders = (["event", "actions"], ["event", "conditions", "actions"])
    if sections not in allowed_orders:
        raise ParseError(
            f"blocchi top-level non validi nella regola {rule_name!r}: {sections!r}; "
            "attesi event, conditions opzionale, actions in quest'ordine e una sola volta"
        )
    return sections


def extract_rules(source: str) -> list[Rule]:
    rules: list[Rule] = []
    pattern = re.compile(r'^\s*rule\s*\(\s*"((?:[^"\\]|\\.)*)"\s*\)\s*\{', re.MULTILINE)
    matches = list(pattern.finditer(source))
    clean = mask_strings(source)
    declarations = list(re.finditer(r"(?m)^\s*rule\b", clean))
    matched_starts = {match.start() for match in matches}
    malformed = [match for match in declarations if match.start() not in matched_starts]
    if malformed:
        raise ParseError(
            "dichiarazione rule malformata alla riga "
            f"{line_number(source, malformed[0].start())}"
        )
    for match in matches:
        opening = source.find("{", match.start())
        closing = find_matching(source, opening, "{", "}")
        body = source[opening + 1 : closing]
        rule_section_names(body, match.group(1))
        rules.append(Rule(match.group(1), body, match.start()))
    return rules


def array_body(source: str, assignment: str) -> str:
    owner, _, name = assignment.partition(".")
    if not owner or not name:
        raise ParseError(f"nome array non valido: {assignment}")
    pattern = re.compile(
        rf"\b{re.escape(owner)}\s*\.\s*{re.escape(name)}\s*=\s*Array\s*\("
    )
    clean = mask_strings(source)
    match = pattern.search(clean)
    if match is None:
        raise ParseError(f"assegnazione Array non trovata: {assignment}")
    opening = clean.rfind("(", match.start(), match.end())
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
    clean = mask_strings(source)
    for match in pattern.finditer(clean):
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
    return [
        rule
        for rule in rules
        if all(token in mask_strings(rule.body) for token in tokens)
    ]


def code_contains(text: str, *tokens: str) -> bool:
    """Cerca token solo nel codice, mai dentro stringhe/commenti Workshop."""
    clean = mask_strings(text)
    return all(token in clean for token in tokens)


def custom_string_placeholder_errors(source: str) -> list[str]:
    """Valida l'arità dei placeholder nelle chiamate Custom String reali."""
    errors: list[str] = []
    for call in call_texts(source, "Custom String"):
        opening = call.find("(")
        arguments = top_level_items(call[opening + 1 : -1])
        if not arguments:
            errors.append("Custom String senza argomenti")
            continue
        literal = re.fullmatch(r'\s*"((?:[^"\\]|\\.)*)"\s*', arguments[0], re.DOTALL)
        if literal is None:
            continue
        indexes = [int(index) for index in re.findall(r"\{(\d+)\}", literal.group(1))]
        supplied = len(arguments) - 1
        missing = sorted({index for index in indexes if index >= supplied})
        if missing:
            errors.append(
                f"Custom String {literal.group(1)!r}: placeholder {missing} senza "
                f"argomento (forniti {supplied})"
            )
    return errors


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
    checks.equal(len(colors), 32, "numero di colori")
    localized_arrays = {
        "pagine indonesiane": ("Global.NamaHalaman", 10, False),
        "pagine inglesi": ("Global.NamaHalamanEN", 10, False),
        "pagine thailandesi": ("Global.NamaHalamanTH", 10, True),
        "colori indonesiani": ("Global.NamaWarna", 32, False),
        "colori inglesi": ("Global.NamaWarnaEN", 32, False),
        "colori thailandesi": ("Global.NamaWarnaTH", 32, True),
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
        has_latin_variant = any(
            translatable_literal(value, genres_set) for value in literals
        )
        has_thai_variant = any(THAI_RE.search(value) for value in literals)
        if has_thai_variant:
            checks.require(
                has_latin_variant,
                f"testo visibile localizzabile #{index} contiene solo una variante thai",
            )
        if not has_latin_variant:
            continue
        checks.require(
            THAI_RE.search(call) is not None,
            f"testo visibile localizzabile #{index} privo di variante thai",
        )
        checks.require(
            "IndeksBahasa" in call,
            f"testo visibile localizzabile #{index} non dipende dalla lingua del client",
        )
        language_code = mask_strings(call)
        language_branches = {
            branch: re.search(
                rf"IndeksBahasa\)*\s*==\s*{branch}\b",
                language_code,
            )
            is not None
            for branch in (0, 1, 2)
        }
        checks.require(
            (language_branches[0] and language_branches[1])
            or language_branches[2],
            f"testo visibile localizzabile #{index} privo dei rami lingua EN/ID/TH "
            "o del fallback latino condiviso con ramo thai",
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
    clean = mask_strings(source)
    checks.require(source.lstrip().startswith("variables"), "il sorgente deve iniziare con variables")
    checks.require(
        re.search(r"(?m)^\s*settings\s*\{", clean) is None,
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
    placeholder_errors = custom_string_placeholder_errors(source)
    checks.require(
        not placeholder_errors,
        f"arità placeholder Custom String non valida: {placeholder_errors[:3]}",
    )

    checks.equal(source.count("\u200b"), 2, "occorrenze della sentinella U+200B")
    checks.equal(
        len(re.findall(r'Custom\s+String\s*\(\s*"\u200b"\s*\)', source)),
        2,
        "sentinelle U+200B racchiuse in Custom String",
    )


def check_timer_and_match(checks: Checks, source: str, rules: list[Rule]) -> None:
    clean = mask_strings(source)
    for name in (
        "DurasiServerMenit", "WaktuMulaiServer", "WaktuAkhirServer", "SisaWaktuServer",
        "TeksWaktuServer", "MulaiUlangSudahDiminta",
    ):
        checks.require(f"Global.{name}" in clean, f"timer: variabile {name} assente")

    checks.require(
        re.search(
            r"Global\.DurasiServerMenit\s*=\s*Workshop Setting Integer\s*\(.*?30\s*,\s*30\s*,\s*90\s*,\s*0\s*\)",
            clean,
            re.DOTALL,
        )
        is not None,
        "timer: impostazione durata non vincolata a 30..90 minuti",
    )
    checks.require(
        re.search(r"Global\.WaktuMulaiServer\s*=\s*Total Time Elapsed\s*;", clean) is not None,
        "timer: baseline WaktuMulaiServer non inizializzata da Total Time Elapsed",
    )
    checks.require(
        re.search(
            r"Global\.WaktuAkhirServer\s*=\s*Global\.WaktuMulaiServer\s*\+\s*Global\.DurasiServerMenit\s*\*\s*60\s*;",
            clean,
        )
        is not None,
        "timer: deadline non derivata da baseline + durata",
    )
    checks.require(
        re.search(
            r"Global\.SisaWaktuServer\s*=.*Global\.WaktuAkhirServer\s*-\s*Total Time Elapsed",
            clean,
        )
        is not None,
        "timer: tempo residuo non derivato dalla deadline",
    )

    timer_rules = [
        rule
        for rule in rules_containing(rules, "Global.TeksWaktuServer", "Global.SisaWaktuServer")
        if code_contains(rule.body, "Loop If Condition Is True;")
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
        restart = mask_strings(restart_rules[0].body)
        checks.require(
            re.search(r"Global\.SisaWaktuServer\s*<=\s*0", restart) is not None,
            "Restart Match non è condizionato dal timer personalizzato a zero",
        )
        checks.require(
            "Global.MulaiUlangSudahDiminta == False;" in restart,
            "Restart Match privo di guardia one-shot",
        )
        set_guard = restart.find("Global.MulaiUlangSudahDiminta = True;")
        restart_at = restart.find("Restart Match;")
        checks.require(
            0 <= set_guard < restart_at,
            "la guardia MulaiUlangSudahDiminta deve essere impostata prima del riavvio",
        )



def check_instant_start(checks: Checks, source: str, rules: list[Rule]) -> None:
    waiting = [
        rule for rule in rules
        if code_contains(
            rule.body,
            "Ongoing - Global;",
            "Global.Siap == True;",
            "Is Waiting For Players == True;",
            "Start Game Mode;",
        )
    ]
    checks.equal(len(waiting), 1, "avvio immediato da Waiting For Players")

    assembling = [
        rule for rule in rules
        if code_contains(
            rule.body,
            "Ongoing - Global;",
            "Global.Siap == True;",
            "Is Assembling Heroes == True;",
            "Set Match Time(0);",
        )
    ]
    checks.equal(len(assembling), 1, "skip Assemble Heroes")

    setup = [
        rule for rule in rules
        if code_contains(
            rule.body,
            "Ongoing - Global;",
            "Global.Siap == True;",
            "Is In Setup == True;",
            "Set Match Time(0);",
        )
    ]
    checks.equal(len(setup), 1, "skip fase Setup")

    checks.require(
        assembling and setup and assembling[0].name != setup[0].name,
        "Assemble Heroes e Setup devono restare in regole separate",
    )

def check_bot_lifecycle(checks: Checks, source: str, rules: list[Rule]) -> None:
    clean = mask_strings(source)
    classification = rules_containing(rules, "Start Forcing Dummy Bot Name", "Stop Forcing Dummy Bot Name")
    checks.equal(len(classification), 1, "regole di classificazione umano/bot")
    if classification:
        body = classification[0].body
        code = mask_strings(body)
        checks.require(
            "If(Is Dummy Bot(Event Player));" not in code,
            "classificazione: ramo dummy irraggiungibile ancora presente",
        )
        waits = [match.start() for match in re.finditer(r"Wait\s*\(\s*0\.016\s*,", code)]
        entities = [match.start() for match in re.finditer(r"Entity Exists\s*\(\s*Event Player\s*\)", code)]
        checks.equal(len(waits), 2, "Wait(0.016) nella classificazione")
        registration = code.find("Append To Array(Global.PemainManusia, Event Player)")
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
            re.search(r"Wait\s*\(\s*0\.500\s*,", mask_strings(rule.body)) is not None
            and code_contains(rule.body, "Loop If Condition Is True;")
        )
        checks.require(not is_watchdog, f"watchdog bot periodico ancora presente in {rule.name!r}")
    checks.require("Player Spawned;" not in clean, "tipo evento inesistente Player Spawned ancora presente")
    inactive_reset = [
        rule for rule in rules
        if code_contains(
            rule.body,
            "Ongoing - Each Player;",
            "Event Player.KunciBotAktif = False;",
            "Is Dummy Bot(Event Player)",
            "Event Player.KunciBotAktif == True;",
            "Has Spawned(Event Player) == False",
            "Is Alive(Event Player) == False",
        )
    ]
    checks.equal(len(inactive_reset), 1, "reset del latch bot alla morte o al despawn")
    reactivation = [
        rule for rule in bot_calls
        if code_contains(
            rule.body,
            "Ongoing - Each Player;",
            "Is Alive(Event Player) == True;",
            "Event Player.KunciBotAktif == False",
            "Hero Of(Event Player) != Event Player.PahlawanBotTerakhir",
        )
    ]
    checks.equal(len(reactivation), 1, "riattivazione bot dopo respawn o cambio eroe")

    lock_rules = rules_containing(rules, "Subroutine;", "KunciBot;")
    checks.require(bool(lock_rules), "subroutine KunciBot non trovata")
    if lock_rules:
        lock = mask_strings(lock_rules[0].body)
        checks.require(
            "Abort If(Is Alive(Event Player) == False);" in lock,
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
            checks.require(action in lock, f"KunciBot incompleta: {action}")
        checks.require(
            code_contains(
                lock_rules[0].body,
                "Disable Nameplates(Event Player",
                "Global.PemainManusia",
                "InspeksiAktif",
            ),
            "KunciBot non nasconde la nameplate ai viewer che stanno ispezionando",
        )


def check_menus(checks: Checks, source: str, rules: list[Rule], subroutines: set[str]) -> None:
    clean = mask_strings(source)
    codes = [re.sub(r"\s+", "", item) for item in top_level_items(array_body(source, "Global.KodeMenu"))]
    checks.equal(codes, ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"], "codici dei dodici menu")
    checks.require(
        re.search(r"KursorUtama\s*=\s*\([^;]+\)\s*%\s*12\s*;", clean) is not None,
        "navigazione principale non limitata a dodici menu",
    )
    checks.require(
        re.search(r"KursorBahasa\s*=\s*\([^;]+\)\s*%\s*3\s*;", clean) is not None,
        "selettore lingua non usa modulo 3",
    )

    expected_renderers = {
        "GambarUtama", "GambarMusik", "GambarKamera", "GambarWarna", "GambarBahasa",
        "GambarBalasDendam", "GambarKebal", "GambarSuara", "GambarIkon",
        "GambarSakelarTeleportasi", "GambarPrivasiInspeksi", "GambarNasib", "GambarVoto",
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
        if code_contains(rule.body, "MenuTerbuka == True;")
        and all(
            code_contains(rule.body, f"Button({button})")
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
        if code_contains(
            rule.body,
            "Event Player.PerintahMenu != 0;",
            "Event Player.PerintahMenu = 0;",
        )
        and all(
            code_contains(
                rule.body,
                f"Is Button Held(Event Player, Button({button})) == False",
            )
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
        handlers = [
            rule
            for rule in rules
            if code_contains(rule.body, f"Event Player.PerintahMenu == {command};")
        ]
        checks.equal(len(handlers), 1, f"handler dispatcher comando {command}")
        if handlers:
            checks.require(
                "Event Player.PerintahMenu = 0;" not in handlers[0].body,
                f"handler {command} resetta il dispatcher prima del rilascio di tutti gli input",
            )

    melee_rules = [
        rule for rule in rules
        if code_contains(rule.body, "Button(Melee)", "Abort When False")
    ]
    checks.equal(len(melee_rules), 1, "gestori pressione lunga Melee")
    if melee_rules:
        checks.require(
            re.search(r"Wait\s*\(\s*0\.500\s*,\s*Abort When False\s*\)", melee_rules[0].body)
            is not None,
            "Melee deve richiedere esattamente 0,5 secondi",
        )
    checks.require("Wait(1.250" not in clean, "durata Melee legacy da 1,25 secondi ancora presente")
    checks.require(
        re.search(r"KursorGenre\s*=\s*\([^;]+\+\s*10\)\s*%\s*100", clean) is not None,
        "salto musicale +10 assente",
    )
    checks.require(
        re.search(r"KursorGenre\s*=\s*\([^;]+\+\s*90\)\s*%\s*100", clean) is not None,
        "salto musicale -10 assente",
    )
    menu_open_rules = [
        rule for rule in rules
        if code_contains(rule.body, "Event Player.MenuTerbuka = True;", "Event Player.HalamanMenu = -1;")
    ]
    checks.equal(len(menu_open_rules), 1, "apertura Arcade Menu")
    if menu_open_rules:
        opening = mask_strings(menu_open_rules[0].body)
        checks.require(
            "Event Player.KartuNasibAktif == False;" in opening,
            "Menu 10: Arcade Menu può ancora aprirsi durante la roulette",
        )
        for forbidden in (
            "Event Player.KursorUtama = 0;",
            "Event Player.KursorGenre = Event Player.IndeksGenre",
            "Event Player.KursorKamera = 0;",
            "Event Player.KursorWarna = Event Player.IndeksWarna;",
            "Event Player.KursorBahasa = Event Player.IndeksBahasa;",
            "Event Player.KursorBalasDendam = 0;",
                "Event Player.KursorSuara = Event Player.IndeksSuara;",
            "Event Player.KursorTeleportasiJongkok = Event Player.TeleportasiJongkokDiaktifkan;",
            "Event Player.KursorPrivasiInspeksi = Event Player.PrivasiInspeksiAktif;",
        ):
            checks.require(forbidden not in opening, f"menu reopen resetta il cursore: {forbidden}")

    interact_rules = [rule for rule in rules if code_contains(rule.body, "Event Player.PerintahMenu == 1;", "Event Player.HalamanMenu = Global.KodeMenu[Event Player.KursorUtama];")]
    checks.equal(len(interact_rules), 1, "dispatcher Interact menu")
    if interact_rules:
        body = mask_strings(interact_rules[0].body)
        for forbidden in (
            "Event Player.KursorGenre = Event Player.IndeksGenre",
            "Event Player.KursorKamera = 0;",
            "Event Player.KursorBahasa = Event Player.IndeksBahasa;",
            "Event Player.KursorBalasDendam = 0;",
                "Event Player.KursorSuara = Event Player.IndeksSuara;",
            "Event Player.KursorTeleportasiJongkok = Event Player.TeleportasiJongkokDiaktifkan;",
            "Event Player.KursorPrivasiInspeksi = Event Player.PrivasiInspeksiAktif;",
        ):
            checks.require(forbidden not in body, f"submenu resetta il cursore: {forbidden}")

    teleport_open_rules = [rule for rule in rules if code_contains(rule.body, "Event Player.TeleportasiJongkokAktif = True;")]
    checks.equal(len(teleport_open_rules), 1, "apertura teleport Crouch")
    if teleport_open_rules:
        checks.require(
            "Event Player.KursorTeleportasi = 0;" not in mask_strings(teleport_open_rules[0].body),
            "teleport Crouch resetta ancora il cursore a zero",
        )

    checks.equal(
        source.count('And(Current Game Mode != Game Mode(Capture The Flag), Distance Between(Objective Position(Objective Index), Vector(0, 0, 0)) <= 0.100) ? Custom String('),
        3,
        "HUD teleport CTF non deve mostrare unavailable basandosi su Objective Position",
    )

    for rule in rules:
        refreshes_dynamic_menu = any(
            code_contains(rule.body, token)
            for token in ("SegarkanTargetBalasDendam", "SegarkanTargetTeleportasi")
        )
        periodic = code_contains(rule.body, "Loop If Condition Is True;")
        checks.require(
            not (
                refreshes_dynamic_menu
                and periodic
                and code_contains(rule.body, "Call Subroutine(GambarMenu);")
            ),
            f"ridisegno periodico del menu ancora presente in {rule.name!r}",
        )

    close_rules = rules_containing(rules, "Subroutine;", "TutupMenu;")
    checks.equal(len(close_rules), 1, "subroutine TutupMenu")
    if close_rules:
        close = mask_strings(close_rules[0].body)
        held = close.find("If(Is Button Held(Event Player, Button(Melee)));")
        latch_true = close.find("Event Player.SeranganDekatDipakai = True;", held)
        otherwise = close.find("Else;", held)
        allow = close.find("Allow Button(Event Player, Button(Melee));", otherwise)
        latch_false = close.find("Event Player.SeranganDekatDipakai = False;", otherwise)
        checks.require(
            0 <= held < latch_true < otherwise < allow < latch_false,
            "TutupMenu non arma il latch Melee se il tasto resta premuto e non lo "
            "ripristina subito altrimenti",
        )

    invalid_state_cleanup = [
        rule
        for rule in rules_containing(rules, "Event Player.MenuTerbuka == True;", "Call Subroutine(TutupMenu);")
        if code_contains(
            rule.body,
            "Has Spawned(Event Player) == False",
            "Is Alive(Event Player) == False",
        )
    ]
    checks.equal(
        len(invalid_state_cleanup),
        1,
        "cleanup menu su morte, despawn, hero-select o passaggio spettatore",
    )
    if invalid_state_cleanup:
        conditions = re.sub(
            r"\s+",
            "",
            mask_strings(section_body(invalid_state_cleanup[0].body, "conditions")),
        )
        checks.require(
            conditions
            == (
                "EventPlayer.MenuTerbuka==True;"
                "Or(HasSpawned(EventPlayer)==False,IsAlive(EventPlayer)==False)==True;"
            ),
            "cleanup menu: despawn e morte devono restare alternative OR",
        )

    revenge_renderers = rules_containing(rules, "Subroutine;", "GambarBalasDendam;")
    checks.equal(len(revenge_renderers), 1, "renderer BalasDendam")
    if revenge_renderers:
        body = revenge_renderers[0].body
        empty_at = body.rfind("Count Of(Event Player.DaftarTargetBalasDendam) == 0")
        empty_state = body[empty_at : empty_at + 700] if empty_at >= 0 else ""
        checks.require(
            "IndeksBahasa" in empty_state
            and all(
                f'Custom String("{text}")' in empty_state
                for text in ("4 - REVENGE", "4 - BALAS DENDAM", "4 - ล้างแค้น")
            ),
            "BalasDendam: stato vuoto non localizzato in tutte e tre le lingue",
        )


def check_camera(
    checks: Checks, source: str, rules: list[Rule], player_names: set[str]
) -> None:
    clean_source = mask_strings(source)
    legacy_cache_names = (
        "TitikJangkarKamera", "TitikIdealKamera", "TitikBenturanKamera", "TitikAkhirKamera",
        "ArahMendatarKamera", "PosisiRelatifKamera", "TinggiJangkarKamera",
    )
    for name in legacy_cache_names:
        checks.require(name not in player_names, f"cache camera server legacy ancora dichiarata: {name}")
        checks.require(f"Event Player.{name}" not in clean_source, f"cache camera server legacy ancora usata: {name}")
    checks.equal(len(call_texts(source, "Ray Cast Hit Position")), 1, "Ray Cast Hit Position nel sorgente")
    ray_rules = rules_containing(rules, "Ray Cast Hit Position")
    checks.equal(len(ray_rules), 1, "regole che eseguono il raycast camera")
    if ray_rules:
        checks.require(
            code_contains(ray_rules[0].body, "Subroutine;", "MulaiKamera;"),
            "raycast camera non confinato alla subroutine MulaiKamera",
        )
    camera_loops = [
        rule for rule in rules
        if code_contains(rule.body, "ModeKamera != 0;", "Loop If Condition Is True;")
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

    checks.require("InteraksiKameraDipakai" in player_names, "camera shortcut: latch InteraksiKameraDipakai assente")
    shortcut_rules = [
        rule for rule in rules
        if code_contains(
  rule.body,
  "Event Player.MenuTerbuka == False;",
  "Event Player.TeleportasiJongkokAktif == False;",
  "Event Player.InteraksiKameraDipakai == False;",
  "Is Button Held(Event Player, Button(Interact)) == True;",
  "Wait(0.500, Abort When False);",
  "Event Player.TargetKamera = Event Player;",
  "Event Player.ModeKamera = 1;",
  "Call Subroutine(MulaiKamera);",
  "Stop Camera(Event Player);",
  "Event Player.ModeKamera = 0;",
  "Event Player.TargetKamera = Null;",
        )
    ]
    checks.equal(len(shortcut_rules), 1, "camera shortcut Interact 0,5 s fuori menu")
    if shortcut_rules:
        checks.require(
  code_contains(shortcut_rules[0].body, "If(Event Player.ModeKamera == 0);", "Else;"),
  "camera shortcut non alterna prima persona e camera attiva",
        )
    release_rules = [
        rule for rule in rules
        if code_contains(
  rule.body,
  "Event Player.InteraksiKameraDipakai == True;",
  "Is Button Held(Event Player, Button(Interact)) == False;",
  "Event Player.InteraksiKameraDipakai = False;",
        )
    ]
    checks.equal(len(release_rules), 1, "release latch Interact camera")
    menu_camera_rules = [
        rule for rule in rules
        if code_contains(
  rule.body,
  "Event Player.MenuTerbuka == True;",
  "Event Player.PerintahMenu == 1;",
  "Else If(Event Player.HalamanMenu == 1);",
  "Event Player.KursorKamera",
        )
    ]
    checks.equal(len(menu_camera_rules), 1, "Interact camera nel menu resta gestito dal dispatcher")


def check_crouch(checks: Checks, source: str, rules: list[Rule]) -> None:
    checks.equal(
        len(call_texts(source, "Disable Nameplates")), 3,
        "Disable Nameplates Crouch, registrazione umano e lock bot",
    )
    checks.equal(
        len(call_texts(source, "Enable Nameplates")), 2,
        "Enable Nameplates cleanup",
    )
    checks.equal(
        len(call_texts(source, "Create In-World Text")), 4,
        "due testi mondo Crouch più due parentesi Nasib",
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
        checks.require(
            code_contains(
                registration[0].body,
                "Disable Nameplates(Event Player",
                "Global.PemainManusia",
                "InspeksiAktif",
            ),
            "registrazione umano non nasconde la nameplate ai viewer che ispezionano",
        )

    starts = [
        r for r in rules
        if code_contains(
            r.body,
            "Event Player.InspeksiAktif = True;",
            "Disable Nameplates",
            "Create In-World Text",
        )
    ]

    checks.equal(
        len(starts), 1,
        "regola avvio Crouch",
    )

    if starts:
        start_code = mask_strings(starts[0].body)
        checks.equal(
            len(re.findall(
                r",\s*1\.100\s*,\s*Do Not Clip",
                start_code,
            )),
            2,
            "dimensione testi Crouch",
        )

        checks.require(
            "Color(Orange)" in start_code,
            "testo bot Crouch non arancione",
        )

    refresh = [
        r for r in rules
        if code_contains(r.body, "SegarkanTargetInspeksi", "Loop If Condition Is True;")
    ]

    checks.equal(
        len(refresh), 1,
        "loop refresh target Crouch",
    )

    if refresh:
        checks.require(
        "Wait(0.200, Abort When False);" in source,
        "refresh Crouch non a 0,20 s",
    )

    cleanup = [
        r for r in rules_containing(
            rules,
            "Enable Nameplates",
        )
        if code_contains(r.body, "Event Player.InspeksiAktif = False;")
    ]

    checks.equal(
        len(cleanup), 1,
        "cleanup Crouch",
    )

    if cleanup:
        checks.require(
            len(call_texts(cleanup[0].body, "Destroy In-World Text")) >= 2,
            "cleanup non distrugge entrambi i testi",
        )

        checks.require(
            code_contains(
                cleanup[0].body,
                "Event Player.TeksDunia = Null;",
                "Event Player.TeksDiri = Null;",
            ),
            "cleanup non azzera i testi",
        )
        checks.require(
            code_contains(
                cleanup[0].body,
                "Has Spawned(Event Player) == False",
                "Is Alive(Event Player) == False",
            ),
            "cleanup Crouch non copre despawn, hero-select e spettatore",
        )
        cleanup_conditions = re.sub(
            r"\s+",
            "",
            mask_strings(section_body(cleanup[0].body, "conditions")),
        )
        checks.require(
            cleanup_conditions
            == (
                "EventPlayer.InspeksiAktif==True;"
                "Or(Or(Or(Or(IsButtonHeld(EventPlayer,Button(Crouch))==False,"
                "EventPlayer.MenuTerbuka==True),HasSpawned(EventPlayer)==False),"
                "IsAlive(EventPlayer)==False),EventPlayer.ModeKamera==2)==True;"
            ),
            "cleanup Crouch: rilascio/menu, despawn/morte e camera devono restare "
            "alternative OR",
        )

    player_table = re.search(
        r"(?ms)^\s*player\s*:\s*(.*)\Z",
        section_body(source, "variables"),
    )
    checks.require(
        player_table is not None
        and re.search(
            r"(?m)^\s*47\s*:\s*DaftarTargetInspeksi\s*$",
            player_table.group(1),
        )
        is not None,
        "Crouch: lo slot player 47 deve essere DaftarTargetInspeksi",
    )

    target_refresh = rules_containing(rules, "Subroutine;", "SegarkanTargetInspeksi;")
    checks.equal(len(target_refresh), 1, "subroutine target Crouch")
    if target_refresh:
        body = target_refresh[0].body
        clean_body = mask_strings(body)
        compact = re.sub(r"\s+", "", clean_body)
        candidates = "EventPlayer.DaftarTargetInspeksi=FilteredArray(AllPlayers(AllTeams),"
        checks.require(candidates in compact, "Crouch: array candidati non filtrato prima della selezione")
        filter_match = re.search(
            r"Event Player\.DaftarTargetInspeksi\s*=\s*Filtered Array\s*\(",
            clean_body,
        )
        predicate_compact = ""
        if filter_match is not None:
            opening = clean_body.rfind("(", filter_match.start(), filter_match.end())
            closing = find_matching(body, opening, "(", ")")
            arguments = top_level_items(body[opening + 1 : closing])
            checks.equal(len(arguments), 2, "argomenti Filtered Array Crouch")
            if len(arguments) == 2:
                checks.equal(
                    re.sub(r"\s+", "", mask_strings(arguments[0])),
                    "AllPlayers(AllTeams)",
                    "sorgente candidati Crouch",
                )
                predicate_compact = re.sub(r"\s+", "", mask_strings(arguments[1]))
        expected_predicate = (
            "And(CurrentArrayElement!=EventPlayer,"
            "And(EntityExists(CurrentArrayElement),"
            "And(HasSpawned(CurrentArrayElement),"
            "IsAlive(CurrentArrayElement))))"
        )
        checks.equal(
            predicate_compact,
            expected_predicate,
            "predicate positivo Filtered Array Crouch",
        )
        checks.require(
            "IsInLineofSight(" not in predicate_compact,
            "Crouch: il filtro non deve richiedere linea di vista; i muri non bloccano l'ispezione",
        )
        ordered = (
            "FirstOf(SortedArray(EventPlayer.DaftarTargetInspeksi,"
            "AngleBetweenVectors(FacingDirectionOf(EventPlayer),"
            "DirectionTowards(EyePosition(EventPlayer),EyePosition(CurrentArrayElement))))"
        )
        checks.require(ordered in compact, "Crouch: target non scelto per angolo minimo dal reticolo")
        filter_at = compact.find(candidates)
        selection_at = compact.find("EventPlayer.TargetInspeksi=FirstOf(SortedArray(")
        checks.require(
            0 <= filter_at < selection_at,
            "Crouch: la selezione deve avvenire dopo il filtro completo dei candidati",
        )
        checks.require(
            "PlayerClosestToReticle" not in compact,
            "Crouch: selezione legacy prima del filtro ancora presente",
        )
        checks.require(
            "DistanceBetween(" not in compact,
            "Crouch: non sono ammesse soglie di distanza",
        )
        checks.equal(
            compact.count("AngleBetweenVectors("),
            1,
            "Crouch: Angle Between Vectors deve servire solo all'ordinamento",
        )


def check_cleanup_and_revenge(checks: Checks, source: str, rules: list[Rule]) -> None:
    clean_source = mask_strings(source)
    checks.require("Global.SlotHUDTersedia" in clean_source, "pool SlotHUDTersedia assente")
    checks.require("Global.SlotHUDPemain" in clean_source, "registro parallelo SlotHUDPemain assente")
    checks.require("Global.NomorUrut" not in clean_source, "contatore HUD NomorUrut non è stato rimosso")
    try:
        slots = [re.sub(r"\s+", "", item) for item in top_level_items(array_body(source, "Global.SlotHUDTersedia"))]
    except ParseError:
        slots = []
    checks.equal(len(slots), 12, "slot HUD preallocati")
    checks.equal(slots, [str(index) for index in range(12)], "pool iniziale degli slot HUD 0..11")
    checks.require(
        "Event Player.UrutanHUD = First Of(Global.SlotHUDTersedia);" in clean_source
        and "Modify Global Variable(SlotHUDTersedia, Remove From Array By Index, 0);" in clean_source,
        "allocazione del primo slot HUD libero assente o non atomica",
    )

    leave_rules = [rule for rule in rules if code_contains(rule.body, "Player Left Match;")]
    checks.equal(len(leave_rules), 1, "regole Player Left Match")
    if leave_rules:
        leave = mask_strings(leave_rules[0].body)
        capture_at = leave.find("Global.PemainPembersihan = Event Player;")
        index_at = leave.find(
            "Global.IndeksKeluar = Index Of Array Value(Global.PemainManusia, Event Player);"
        )
        checks.require(
            0 <= capture_at < index_at,
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
        checks.require(f"Event Player.{name}" in clean_source, f"Revenge: variabile {name} assente")
    claim_rules = rules_containing(rules, "TargetBalasDendamTerkunci", "Kill(")
    checks.equal(len(claim_rules), 1, "regole claim BalasDendam con target catturato")
    if claim_rules:
        claim = mask_strings(claim_rules[0].body)
        capture_match = re.search(
            r"Event Player\.TargetBalasDendamTerkunci\s*=\s*Event Player\.DaftarTargetBalasDendam\s*\[\s*Event Player\.KursorBalasDendam\s*\]\s*;",
            claim,
        )
        capture = -1 if capture_match is None else capture_match.start()
        kill_at = claim.find("Kill(Event Player.TargetBalasDendamTerkunci, Event Player);")
        checks.require(0 <= capture < kill_at, "target BalasDendam non catturato per identità prima del claim")
        wait_at = claim.find("Wait(", capture + 1)
        if 0 <= wait_at < kill_at:
            after_wait = claim[wait_at:kill_at]
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

    death_rules = [rule for rule in rules if code_contains(rule.body, "Player Died;")]
    checks.require(bool(death_rules), "regola Player Died per BalasDendam assente")
    if death_rules:
        death = "\n".join(mask_strings(rule.body) for rule in death_rules)
        checks.require(
            re.search(r"Event Player\.[A-Za-z0-9_]*BalasDendam[A-Za-z0-9_]*\s*=\s*False\s*;", death)
            is not None,
            "Player Died non azzera il flag della morte BalasDendam",
        )


def check_teleport(checks: Checks, source: str, rules: list[Rule]) -> None:
    player_table = re.search(
        r"(?ms)^\s*player\s*:\s*(.*)\Z",
        section_body(source, "variables"),
    )
    for slot, name in (
        (49, "JenisTeleportasiTerkunci"),
        (50, "TargetTeleportasiTerkunci"),
    ):
        checks.require(
            player_table is not None
            and re.search(
                rf"(?m)^\s*{slot}\s*:\s*{name}\s*$",
                player_table.group(1),
            )
            is not None,
            f"Teleport: lo slot player {slot} deve essere {name}",
        )

    apply_rules = rules_containing(
        rules,
        "Event Player.JenisTeleportasiTerkunci",
        "Event Player.TargetTeleportasiTerkunci",
        "Call Subroutine(SegarkanTargetTeleportasi);",
        "Teleport(Event Player",
    )
    checks.equal(len(apply_rules), 1, "handler Teleport con destinazione catturata")
    if not apply_rules:
        return

    code = mask_strings(apply_rules[0].body)
    compact = re.sub(r"\s+", "", code)
    kind_statement = (
        "EventPlayer.JenisTeleportasiTerkunci="
        "EventPlayer.KursorTeleportasi<2?EventPlayer.KursorTeleportasi:2;"
    )
    kind_capture = compact.find(kind_statement)
    capture_guard = (
        "If(And(EventPlayer.JenisTeleportasiTerkunci==2,"
        "And(EventPlayer.KursorTeleportasi>=0,"
        "EventPlayer.KursorTeleportasi<CountOf(EventPlayer.DaftarTargetTeleportasi))));"
    )
    guard_at = compact.find(capture_guard, kind_capture)
    target_capture = compact.find(
        "EventPlayer.TargetTeleportasiTerkunci=EventPlayer.DaftarTargetTeleportasi[EventPlayer.KursorTeleportasi];",
        guard_at,
    )
    refresh = compact.find("CallSubroutine(SegarkanTargetTeleportasi);", kind_capture)
    checks.require(
        kind_capture >= 0,
        "Teleport: il tipo deve essere catturato esattamente come cursore < 2 ? cursore : 2",
    )
    checks.require(
        0 <= kind_capture < guard_at < target_capture < refresh,
        "Teleport: identità non catturata prima del refresh sotto guardia kind == 2 "
        "e limiti del cursore",
    )

    after_refresh = compact[refresh:] if refresh >= 0 else compact
    checks.require(
        "EventPlayer.DaftarTargetTeleportasi[EventPlayer.KursorTeleportasi]" not in after_refresh,
        "Teleport: il target viene riletto per indice dopo il refresh",
    )
    checks.require(
        "If(EventPlayer.JenisTeleportasiTerkunci==0);" in after_refresh
        and "ElseIf(EventPlayer.JenisTeleportasiTerkunci==1);" in after_refresh,
        "Teleport: spawn e obiettivo non usano il tipo di destinazione catturato",
    )
    for token in (
        "CurrentGameMode==GameMode(Escort)",
        "CurrentGameMode==GameMode(Hybrid)",
        "PayloadPosition+Vector(2,0,0)",
        "CurrentGameMode==GameMode(CaptureTheFlag)",
        "FlagPosition(OppositeTeamOf(TeamOf(EventPlayer)))+Vector(2,0,0)",
        "CurrentGameMode==GameMode(Push)",
        "IsOnObjective(CurrentArrayElement)==True",
        "PositionOf(FirstOf(FilteredArray(AllPlayers(AllTeams)",
        "ObjectivePosition(ObjectiveIndex)",
    ):
        checks.require(token in after_refresh, f"Teleport obiettivo dinamico incompleto: {token}")
    for token in (
        "EventPlayer.TargetTeleportasiTerkunci==Null",
        "EntityExists(EventPlayer.TargetTeleportasiTerkunci)==False",
        "IsAlive(EventPlayer.TargetTeleportasiTerkunci)==False",
        "ArrayContains(EventPlayer.DaftarTargetTeleportasi,EventPlayer.TargetTeleportasiTerkunci)==False",
    ):
        checks.require(token in after_refresh, f"Teleport: validazione identità incompleta: {token}")
    checks.require(
        "PositionOf(EventPlayer.TargetTeleportasiTerkunci)" in after_refresh
        and "FacingDirectionOf(EventPlayer.TargetTeleportasiTerkunci)" in after_refresh,
        "Teleport: destinazione player non usa esclusivamente l'identità catturata",
    )
    checks.require(
        "PositionOf(EventPlayer.CalonTargetTeleportasi)" not in after_refresh,
        "Teleport: destinazione player usa ancora il candidato aggiornabile",
    )
    checks.require(
        after_refresh.rfind("EventPlayer.JenisTeleportasiTerkunci=-1;")
        > after_refresh.find("Teleport(EventPlayer"),
        "Teleport: tipo catturato non azzerato dopo l'azione",
    )
    checks.require(
        after_refresh.rfind("EventPlayer.TargetTeleportasiTerkunci=Null;")
        > after_refresh.find("Teleport(EventPlayer"),
        "Teleport: identità catturata non azzerata dopo l'azione",
    )

    leave_rules = [rule for rule in rules if code_contains(rule.body, "Player Left Match;")]
    if leave_rules:
        checks.require(
            code_contains(
                leave_rules[0].body,
                "TargetTeleportasiTerkunci == Global.PemainPembersihan",
                "TargetTeleportasiTerkunci, Null",
            ),
            "Teleport: uscita del target non annulla l'identità bloccata",
        )



def check_arcade_features(checks: Checks, source: str, rules: list[Rule]) -> None:
    clean = mask_strings(source)
    player_table = re.search(
        r"(?ms)^\s*player\s*:\s*(.*)\Z",
        section_body(source, "variables"),
    )
    for slot, name in (
        (51, "KebalAktif"),
        (52, "KursorKebal"),
        (53, "IndeksSuara"),
        (54, "KursorSuara"),
        (76, "IkonKartuNasib"),
        (77, "IkonKartuNasibHijau"),
        (78, "TeksKartuNasibKanan"),
        (79, "ModeKameraSebelumNasib"),
        (80, "TargetKameraSebelumNasib"),
    ):
        checks.require(
            player_table is not None
            and re.search(rf"(?m)^\s*{slot}\s*:\s*{name}\s*$", player_table.group(1)) is not None,
            f"fitur arcade: slot player {slot} deve essere {name}",
        )
    for token in (
        "Set Status(Event Player, Null, Unkillable, 9999);",
        "Clear Status(Event Player, Unkillable);",
        "Set Player Health(Event Player, 1);",
        "Health(Event Player) >= Max Health(Event Player);",
        "Stop Modifying Hero Voice Lines(Event Player);",
        "Start Modifying Hero Voice Lines(Event Player, 0.500, False);",
        "Start Modifying Hero Voice Lines(Event Player, 0.750, False);",
        "Start Modifying Hero Voice Lines(Event Player, 1.250, False);",
        "Start Modifying Hero Voice Lines(Event Player, 1.500, False);",
    ):
        checks.require(token in clean, f"fitur arcade mancante: {token}")
    router = rules_containing(rules, "Subroutine;", "GambarMenu;")
    if router:
        checks.require(
            "Call Subroutine(GambarTeleportasi);" not in mask_strings(router[0].body),
            "Teleport non deve più essere instradato dal menu principale",
        )
    checks.require(
        not any(code_contains(rule.body, "Event Player.HalamanMenu == 5;", "SegarkanTargetTeleportasi") for rule in rules),
        "menu 5 non deve più eseguire il refresh Teleport",
    )
    checks.require(
        "Else If(Event Player.HalamanMenu == 5);" in source,
        "Kebal: pagina menu 5 assente dal dispatcher",
    )
    spawn_disable = [
        rule
        for rule in rules
        if code_contains(
            rule.body,
            "Event Player.ModeKebal == 1;",
            "Is In Spawn Room(Event Player) == True;",
            "Event Player.KebalAktif = False;",
            "Event Player.ModeKebal = 0;",
            "Clear Status(Event Player, Unkillable);",
            "Set Damage Received(Event Player, 100);",
            "Set Player Health(Event Player, Max Health(Event Player));",
            "Destroy Icon(Event Player.IkonKebal);",
        )
    ]
    checks.equal(len(spawn_disable), 1, "regola auto-disattivazione solo 1 HP in Spawn Room")

    one_hp = [rule for rule in rules if rule.name.startswith("18b - Kebal:")]
    checks.equal(len(one_hp), 1, "regola 1 HP per guard Spawn Room")
    if one_hp:
        checks.require(
            code_contains(one_hp[0].body, "Is In Spawn Room(Event Player) == False;"),
            "1 HP deve restare escluso dalla Spawn Room",
        )

    reapply = [rule for rule in rules if rule.name.startswith("18 - Kebal:")]
    checks.equal(len(reapply), 1, "regola riapplicazione Unkillable")
    if reapply:
        body = mask_strings(reapply[0].body)
        checks.require(
            "Or(Event Player.ModeKebal == 2, Is In Spawn Room(Event Player) == False) == True;" in body,
            "riapplicazione: FULL HP non resta valido in Spawn Room",
        )

    full_hp = [rule for rule in rules if rule.name.startswith("18d - Kebal:")]
    checks.equal(len(full_hp), 1, "regola FULL HP per Spawn Room")
    if full_hp:
        checks.require(
            "Is In Spawn Room(Event Player) == False;" not in mask_strings(full_hp[0].body),
            "FULL HP non deve essere escluso dalla Spawn Room",
        )

    luck = [
        rule for rule in rules
        if code_contains(
            rule.body,
            "Event Player.KartuNasibAktif == True;",
            "Event Player.PutaranKartuNasib > 0;",
            "Wait(Event Player.JedaKartuNasib, Abort When False);",
            "Event Player.KartuNasibMerah = Event Player.KartuNasibMerah == False;",
            "Modify Player Variable(Event Player, PutaranKartuNasib, Subtract, 1);",
            "Modify Player Variable(Event Player, JedaKartuNasib, Add, 0.055);",
            "Loop If Condition Is True;",
            "Event Player.KartuNasibMerah == True",
            "Set Player Health(Event Player, Max Health(Event Player));",
            "Clear Status(Event Player, Unkillable);",
            "Kill(Event Player, Null);",
        )
    ]
    checks.equal(len(luck), 1, "Nasib: una sola roulette automatica rosso/verde")
    if luck:
        luck_code = mask_strings(luck[0].body)
        checks.equal(len(call_texts(luck[0].body, "Play Effect")), 0, "Nasib: nessun Ring Explosion deve essere usato")
        checks.require("Is Firing Primary" not in luck_code, "Nasib: il vecchio sparo non deve più attivare la carta")
        checks.require("Is In Line of Sight" not in luck_code, "Nasib: la roulette non deve dipendere dalla linea di vista")
        checks.require(luck_code.count("Wait(1, Ignore Condition);") == 3, "Nasib: countdown rosso deve durare tre secondi anche dopo Putaran == 0")
        checks.require(luck_code.count("Abort If(Event Player.KartuNasibAktif == False);") >= 4, "Nasib: outcome non si annulla dopo morte/reset")
        checks.require(luck_code.count("Abort If(Event Player.PutaranKartuNasib > 0);") >= 4, "Nasib: una vecchia outcome può interferire con una nuova roulette")
    card_texts = [
        call for call in call_texts(source, "Create In-World Text")
        if "All Players(All Teams)" in call
        and ("Custom String(\"[\")" in call or "Custom String(\"]\")" in call)
    ]
    checks.equal(len(card_texts), 2, "Nasib: due parentesi world-space separate")
    if len(card_texts) == 2:
        joined = "\n".join(card_texts)
        checks.require("Custom String(\"[\")" in joined and "Custom String(\"]\")" in joined, "Nasib: bracket sinistro/destro mancanti")
        checks.require(joined.count("* 0.300") == 2, "Nasib: bracket non distanziati fisicamente di 0,30 m")
        checks.require(joined.count("Update Every Frame(") >= 2, "Nasib: bracket non aggiornati ogni frame")
    luck_icons = [call for call in call_texts(source, "Create Icon") if ", Skull," in call or ", Heart," in call]
    checks.equal(len(luck_icons), 2, "Nasib: Heart e Skull devono essere due icone persistenti")
    if len(luck_icons) == 2:
        skull = next(call for call in luck_icons if ", Skull," in call)
        heart = next(call for call in luck_icons if ", Heart," in call)
        checks.require("Update Every Frame(" in skull and "Update Every Frame(" in heart, "Nasib: icone non agganciate client-side ogni frame")
        checks.require("Event Player.KartuNasibMerah ? All Players(All Teams) : Empty Array" in skull, "Nasib: visibilità Skull non dinamica")
        checks.require("Event Player.KartuNasibMerah ? Empty Array : All Players(All Teams)" in heart, "Nasib: visibilità Heart non dinamica")
        checks.require("Custom Color(255, 70, 70, 255)" in skull, "Nasib: Skull non rosso")
        checks.require("Custom Color(70, 255, 110, 255)" in heart, "Nasib: Heart non verde")
    if luck:
        pre_loop = mask_strings(luck[0].body).split("Loop If Condition Is True;")[0]
        checks.require("Create Icon(" not in pre_loop and "Destroy Icon(" not in pre_loop, "Nasib: icone ancora ricreate durante i tick")
    checks.require(
        "Destroy Icon(Event Player.IkonKartuNasib);" in clean
        and "Destroy Icon(Event Player.IkonKartuNasibHijau);" in clean,
        "Nasib: cleanup icone persistenti incompleto",
    )

    checks.require(
        "Event Player.PosisiKartuNasib = Eye Position(Event Player) + Facing Direction Of(Event Player) * 4;" in mask_strings(source),
        "Nasib: cache effetto non segue il mirino del proprietario",
    )
    checks.require(
        "Chase Player Variable Over Time(Event Player, PosisiKartuNasib" not in mask_strings(source),
        "Nasib: la vecchia animazione dal terreno non deve restare attiva",
    )
    checks.require(
        "Event Player.KartuNasibMerah = Random Integer(0, 1) == 0;" in clean
        and "Event Player.PutaranKartuNasib = Random Integer(20, 24);" in clean
        and "Event Player.JedaKartuNasib = 0.080;" in clean,
        "Nasib: inizializzazione casuale 50/50 e 20..24 passaggi assente",
    )
    death_reset = [rule for rule in rules if rule.name.startswith("18f - Nasib:")]
    checks.equal(len(death_reset), 1, "Nasib: una sola regola reset alla morte")
    if death_reset:
        checks.require(
            code_contains(
                death_reset[0].body,
                "Event Player.KartuNasibAktif = False;",
                "Event Player.KartuNasibMerah = False;",
                "Event Player.PutaranKartuNasib = 0;",
                "Event Player.JedaKartuNasib = 0;",
                "Event Player.PosisiKartuNasib = Vector(0, 0, 0);",
                "Destroy In-World Text(Event Player.TeksKartuNasib);",
                "Destroy In-World Text(Event Player.TeksKartuNasibKanan);",
                "Destroy Icon(Event Player.IkonKartuNasib);",
                "Destroy Icon(Event Player.IkonKartuNasibHijau);",
                "Event Player.IkonKartuNasib = Null;",
                "Event Player.IkonKartuNasibHijau = Null;",
            ),
            "Nasib: morte prima della fine non resetta completamente la carta",
        )

    menu_interact = next(rule.body for rule in rules if rule.name.startswith("10 - Menu:"))
    luck_start = menu_interact.find("Event Player.KartuNasibAktif = True;")
    checks.require(luck_start >= 0, "Nasib: avvio carta non trovato nel dispatcher")
    if luck_start >= 0:
        masked_menu_interact = mask_strings(menu_interact)
        before_luck = masked_menu_interact[max(0, luck_start - 900):luck_start]
        after_luck = mask_strings(menu_interact[luck_start:])
        vote_branch_at = after_luck.find("Event Player.KursorVoto %=")
        luck_only = after_luck[:vote_branch_at] if vote_branch_at >= 0 else after_luck
        for token in (
            "Event Player.KebalAktif = False;",
            "Event Player.ModeKebal = 0;",
            "Event Player.KursorKebal = 0;",
            "Clear Status(Event Player, Unkillable);",
            "Set Damage Received(Event Player, 100);",
            "Destroy Icon(Event Player.IkonKebal);",
        ):
            checks.require(token in before_luck, f"Nasib: avvio carta non forza Unkillable OFF: {token}")
        checks.require(
            "Call Subroutine(TutupMenu);" in after_luck,
            "Nasib: il menu non viene chiuso quando parte la carta",
        )
        checks.require(
            "Call Subroutine(GambarMenu);" not in luck_only,
            "Nasib: il menu viene ridisegnato dopo l'avvio della carta",
        )

    checks.require(
        "Event Player.ModeKameraSebelumNasib = Event Player.ModeKamera;" not in menu_interact
        and "Event Player.TargetKameraSebelumNasib = Event Player.TargetKamera;" not in menu_interact,
        "Nasib: l'avvio salva ancora una camera che non deve modificare",
    )
    luck_start_at = menu_interact.find("Event Player.KartuNasibAktif = True;")
    if luck_start_at >= 0:
        luck_activation_tail = menu_interact[max(0, luck_start_at - 500):luck_start_at + 500]
        checks.require(
            "Stop Camera(Event Player);" not in luck_activation_tail
            and "Event Player.ModeKamera = 0;" not in luck_activation_tail
            and "Event Player.TargetKamera = Null;" not in luck_activation_tail,
            "Nasib: attivazione cambia ancora la camera e può causare uno scatto",
        )
    restore_rules = [rule for rule in rules if rule.name.startswith("18g - Nasib:")]
    checks.equal(len(restore_rules), 0, "Nasib: la vecchia regola ripristino camera non deve più esistere")

    blocked_one_hp = menu_interact[
        menu_interact.find("If(And(Event Player.KursorKebal == 1"):
        menu_interact.find("Else;", menu_interact.find("If(And(Event Player.KursorKebal == 1"))
    ]
    checks.require(
        "Event Player.KursorKebal = Event Player.ModeKebal;" not in mask_strings(blocked_one_hp),
        "Kebal: il rifiuto 1 HP nello Spawn Room non deve spostare il cursore",
    )



def check_server_location_setting(checks: Checks, source: str) -> None:
    expected = ['Bangladesh', 'Bhutan', 'Brunei', 'Cambodia', 'Hong Kong', 'India', 'Indonesia', 'Japan', 'Kazakhstan', 'Kyrgyzstan', 'Laos', 'Malaysia', 'Maldives', 'Myanmar', 'Mongolia', 'Nepal', 'Pakistan', 'Philippines', 'Singapore', 'South Korea', 'Sri Lanka', 'Tajikistan', 'Taiwan', 'Thailand', 'Uzbekistan', 'Vietnam']
    try:
        countries = custom_strings(array_body(source, "Global.DaftarLokasiServer"))
    except ParseError as exc:
        checks.require(False, f"Server Location countries: {exc}")
        return
    checks.equal(countries, expected, "lista Server Location Asia")
    checks.equal(len(countries), 26, "paesi Server Location Asia")
    checks.equal(countries.index("Indonesia") if "Indonesia" in countries else -1, 6, "indice Server Location predefinito Indonesia")
    checks.require(
        'Global.IndeksLokasiServer = Workshop Setting Combo' in mask_strings(source),
        "Server Location: Workshop Setting Combo non assegnato a Global.IndeksLokasiServer",
    )
    checks.require(
        'Custom String("Server location (Asia)")' in source,
        "Server Location: nome della combo Asia non trovato",
    )
    checks.require(
        'Global.IndeksLokasiServer = Workshop Setting Integer' not in mask_strings(source),
        "Server Location: la vecchia impostazione numerica non deve essere presente",
    )
    combos = [call for call in call_texts(source, "Workshop Setting Combo") if 'Server location (Asia)' in call]
    checks.equal(len(combos), 1, "Workshop Setting Combo Server Location Asia")
    if combos:
        opening = combos[0].find("(")
        args = top_level_items(combos[0][opening + 1 : -1])
        checks.equal(len(args), 5, "argomenti Workshop Setting Combo Server Location Asia")
        if len(args) == 5:
            checks.equal(args[2].strip(), "6", "default Workshop Setting Combo Server Location Asia")
            checks.equal(custom_strings(args[3]), expected, "opzioni Workshop Setting Combo Server Location Asia")
    checks.require(
        'Custom String("SERVER LOCATION: {0}", Global.DaftarLokasiServer[Global.IndeksLokasiServer])' in source
        and 'Custom String("LOKASI SERVER: {0}", Global.DaftarLokasiServer[Global.IndeksLokasiServer])' in source
        and 'Custom String("ตำแหน่งเซิร์ฟเวอร์: {0}", Global.DaftarLokasiServer[Global.IndeksLokasiServer])' in source,
        "HUD SERVER LOCATION non usa il paese configurato",
    )


def check_diagnostics(checks: Checks, source: str, rules: list[Rule]) -> None:
    clean_source = mask_strings(source)
    checks.require(
        "Global.DiagnostikPerforma = Workshop Setting Toggle" in clean_source,
        "toggle Performance diagnostics non assegnato a Global.DiagnostikPerforma",
    )
    toggles = [
        call for call in call_texts(source, "Workshop Setting Toggle")
        if "Performance diagnostics" in call
    ]
    checks.equal(len(toggles), 1, "Workshop Setting Toggle Performance diagnostics")
    if toggles:
        opening = toggles[0].find("(")
        arguments = top_level_items(toggles[0][opening + 1 : -1])
        checks.require(
            len(arguments) >= 3 and arguments[2].strip() == "False",
            "Performance diagnostics deve essere OFF per impostazione predefinita",
        )
    for metric in ("Server Load", "Server Load Average", "Server Load Peak"):
        checks.require(metric in clean_source, f"diagnostica priva di {metric}")

    left_hud_rules = [
        rule for rule in rules
        if code_contains(
            rule.body,
            "Global.HudKiriPemain = Append To Array",
            "Global.DiagnostikPerforma == True",
            "Local Player == Host Player",
            "Server Load",
            "Server Load Average",
            "Server Load Peak",
        )
    ]
    checks.equal(len(left_hud_rules), 1, "diagnostica integrata nella lista sinistra")
    if left_hud_rules:
        diagnostic = mask_strings(left_hud_rules[0].body)
        checks.require(
        "Event Player.UrutanHUD == Global.SlotHUDTerakhir" in source,
        "diagnostica non ancorata alla cache dell'ultimo player della lista sinistra",
    )
        checks.require(
            all(token in diagnostic for token in (
                "HudKiriPemain", "HudMenuPemain", "TeksDuniaPemain", "TeksDiriPemain",
            )),
            "diagnostica priva dei conteggi HUD/IWT",
        )
    checks.require(
        'LOAD {0}% | AVG {1}% | MAX {2}%' in source,
        "diagnostica priva della riga LOAD compatta",
    )
    checks.require(
        'Custom String("HUD {0} | IWT {1}"' in source,
        "diagnostica priva della riga HUD/IWT compatta",
    )
    checks.require(
        ')) : Custom String(" "), Left, -99 + Event Player.UrutanHUD' in source,
        "diagnostica OFF deve usare testo vuoto esplicito e non Null/0",
    )
    checks.require(
        ')) : Null, Left, -99 + Event Player.UrutanHUD' not in source,
        "diagnostica OFF usa ancora Null e può renderizzare 0 nel roster",
    )
    checks.require(
        'rule("00d - Umum: Tampilkan diagnostik performa hanya kepada host")' not in source,
        "vecchio HUD diagnostica separato ancora presente",
    )
    inspector_rules = rules_containing(
        rules, "Global.DiagnostikPerforma == False", "Disable Inspector Recording;"
    )
    checks.require(bool(inspector_rules), "Inspector Recording non disattivato con diagnostica OFF")


def strip_yaml_comments(text: str) -> str:
    """Rimuove commenti YAML senza troncare i caratteri # dentro stringhe."""
    cleaned_lines: list[str] = []
    for line in text.splitlines():
        result: list[str] = []
        in_single = False
        in_double = False
        escaped = False
        index = 0
        while index < len(line):
            char = line[index]
            if in_double:
                result.append(char)
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_double = False
            elif in_single:
                result.append(char)
                if char == "'":
                    if index + 1 < len(line) and line[index + 1] == "'":
                        result.append("'")
                        index += 1
                    else:
                        in_single = False
            elif char == '"':
                in_double = True
                result.append(char)
            elif char == "'":
                in_single = True
                result.append(char)
            elif char == "#" and (index == 0 or line[index - 1].isspace()):
                break
            else:
                result.append(char)
            index += 1
        cleaned_lines.append("".join(result).rstrip())
    return "\n".join(cleaned_lines)


def check_workflow_text(checks: Checks, workflow: str) -> None:
    """Valida il workflow CI con una grammatica stretta e comment-safe."""
    workflow_code = strip_yaml_comments(workflow)
    lines = workflow_code.splitlines()
    checks.require("\t" not in workflow_code, "workflow: i rientri devono usare solo spazi")

    def root_block(key: str) -> list[str]:
        header_indexes = [
            index
            for index, line in enumerate(lines)
            if re.fullmatch(rf"{re.escape(key)}:\s*", line)
        ]
        checks.equal(len(header_indexes), 1, f"workflow: blocchi root {key}")
        if len(header_indexes) != 1:
            return []
        start = header_indexes[0] + 1
        end = len(lines)
        for index in range(start, len(lines)):
            if lines[index].strip() and not lines[index].startswith(" "):
                end = index
                break
        return [line for line in lines[start:end] if line.strip()]

    trigger_lines = root_block("on")
    checks.equal(
        trigger_lines,
        ["  push:", "  pull_request:", "  workflow_dispatch:"],
        "workflow: trigger repository completi",
    )
    checks.require(
        not any(re.match(r"^\s+paths(?:-ignore)?\s*:", line) for line in lines),
        "workflow: i filtri paths non devono limitare il gate",
    )

    permission_lines = [
        line for line in lines if re.match(r"^\s*permissions\s*:", line)
    ]
    checks.equal(
        permission_lines,
        ["permissions:"],
        "workflow: permissions deve esistere solo alla root",
    )
    checks.equal(
        root_block("permissions"),
        ["  contents: read"],
        "workflow: sole permissions root contents: read",
    )
    checks.require(
        not any(
            re.search(r"(?:write-all|read-all|contents\s*:\s*write)\s*$", line)
            for line in lines
        ),
        "workflow: permessi write-all/read-all o contents: write vietati",
    )

    checkout = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
    setup_python = "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97"
    uses_values = [
        match.group(1)
        for line in lines
        if (match := re.fullmatch(r"\s+uses:\s*(\S+)\s*", line)) is not None
    ]
    checks.equal(
        uses_values,
        [checkout, setup_python],
        "workflow: actions ancorate agli SHA approvati",
    )

    step_starts = [
        index for index, line in enumerate(lines) if re.match(r"^\s{6}-\s+", line)
    ]
    step_blocks: list[list[str]] = []
    for position, start in enumerate(step_starts):
        end = step_starts[position + 1] if position + 1 < len(step_starts) else len(lines)
        step_blocks.append(lines[start:end])
    checkout_steps = [block for block in step_blocks if any(f"uses: {checkout}" in line for line in block)]
    setup_steps = [block for block in step_blocks if any(f"uses: {setup_python}" in line for line in block)]
    checks.equal(len(checkout_steps), 1, "workflow: step checkout")
    if checkout_steps:
        checks.require(
            any(re.fullmatch(r"\s+persist-credentials:\s*false\s*", line) for line in checkout_steps[0]),
            "workflow: checkout deve usare persist-credentials: false",
        )
    checks.equal(len(setup_steps), 1, "workflow: step setup-python")
    if setup_steps:
        checks.require(
            any(re.fullmatch(r"\s+python-version:\s*'3\.12'\s*", line) for line in setup_steps[0]),
            "workflow: setup-python deve usare Python 3.12",
        )

    run_values = [
        match.group(1).strip()
        for line in lines
        if (match := re.fullmatch(r"\s+run:\s*(.*?)\s*", line)) is not None
    ]
    checks.equal(
        run_values,
        [
            "python -m unittest discover -s tests -p 'test_*.py'",
            "python tools/validate_workshop.py",
        ],
        "workflow: comandi run esatti",
    )


def check_maintenance_workflow_text(checks: Checks, workflow: str) -> None:
    """Valida il runner permanente usato per applicare patch senza YAML dinamico."""
    clean = strip_yaml_comments(workflow)
    checks.require("\t" not in clean, "maintenance workflow: vietati tab YAML")
    for token in (
        "name: Apply Maintenance Patch",
        "      - '.github/maintenance/patch.py'",
        "  contents: write",
        "  group: maintenance-patch-main",
        "  cancel-in-progress: false",
        "    if: github.actor != 'github-actions[bot]'",
        "    timeout-minutes: 10",
        "uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
        "uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97",
        "run: python .github/maintenance/patch.py",
        "run: python -m unittest discover -s tests -p 'test_*.py'",
        "run: python tools/validate_workshop.py",
        "Maintenance patches may not modify workflow files.",
        "git diff --check",
        "rm -f .github/maintenance/patch.py",
        "git diff --cached --check",
        "git commit -m \"Apply validated maintenance patch\"",
        "git push origin HEAD:main",
    ):
        checks.require(token in clean, f"maintenance workflow incompleto: {token}")

    checks.require(
        "workflow_dispatch:" not in clean,
        "maintenance workflow non deve poter essere avviato senza un patch.py versionato",
    )
    checks.require(
        "pull_request:" not in clean,
        "maintenance workflow non deve girare sulle pull request",
    )


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
        expected_blob = git_blob_sha(SOURCE)
        checks.require(
            "WORKSHOP_BLOB_SHA" not in report and expected_blob in report,
            f"docs/VALIDAZIONE.md non registra il blob Workshop effettivo {expected_blob}",
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
        check_workflow_text(checks, WORKFLOW.read_text(encoding="utf-8"))

    checks.require(
        MAINTENANCE_WORKFLOW.exists(),
        f"workflow manutenzione permanente mancante: {MAINTENANCE_WORKFLOW.relative_to(ROOT)}",
    )
    if MAINTENANCE_WORKFLOW.exists():
        check_maintenance_workflow_text(
            checks, MAINTENANCE_WORKFLOW.read_text(encoding="utf-8")
        )

    workflow_dir = ROOT / ".github" / "workflows"
    workflow_names = {
        path.name
        for path in workflow_dir.iterdir()
        if path.is_file() and path.suffix in {".yml", ".yaml"}
    } if workflow_dir.exists() else set()
    checks.equal(
        workflow_names,
        ALLOWED_WORKFLOW_NAMES,
        "workflow consentiti; i runner temporanei sono vietati",
    )



def check_feedback_and_jump_respawn(checks: Checks, source: str, rules: list[Rule]) -> None:
    clean = mask_strings(source)
    for token in (
        "58: PosisiMati", "59: PosisiBangkitAman", "60: BangkitLompatDipakai",
        "18: EfekTerapkan", "19: EfekPulihkan",
        "Play Effect(All Players(All Teams), Ring Explosion, Global.RGB",
        "Event Player.PosisiMati = Position Of(Event Player);",
        "Nearest Walkable Position(Event Player.PosisiMati + Vector(Random Real(-6, 6), 0, Random Real(-6, 6)))",
        "Respawn(Event Player);",
        "Teleport(Event Player, Event Player.PosisiBangkitAman);",
    ):
        checks.require(token in clean, f"feedback/respawn mancante: {token}")
    effect_calls = call_texts(source, "Play Effect")
    checks.equal(len(effect_calls), 2, "feedback: solo i due Ring RGB generici; Menu 10 non usa effetti")
    system_effects = [call for call in effect_calls if "Global.RGB" in call]
    checks.equal(len(system_effects), 2, "feedback: esattamente due Ring RGB di sistema")
    checks.equal(
        len([call for call in effect_calls if "KartuNasibMerah" in call]),
        0,
        "Nasib: nessun Ring rosso/verde deve restare nel Menu 10",
    )
    for index, call in enumerate(system_effects, 1):
        checks.require(
            "Ring Explosion" in call
            and "All Players(All Teams)" in call
            and "Sound" not in call,
            f"feedback sistema #{index}: deve essere Ring Explosion RGB visivo",
        )
    for forbidden in ("Good Explosion", "Buff Impact Sound", "Ring Explosion Sound"):
        checks.require(forbidden not in clean, f"feedback vietato ancora presente: {forbidden}")
    apply = rules_containing(rules, "Subroutine;", "EfekTerapkan;")
    restore = rules_containing(rules, "Subroutine;", "EfekPulihkan;")
    checks.equal(len(apply), 1, "subroutine EfekTerapkan")
    checks.equal(len(restore), 1, "subroutine EfekPulihkan")
    for label, matches in (("EfekTerapkan", apply), ("EfekPulihkan", restore)):
        if matches:
            calls = call_texts(matches[0].body, "Play Effect")
            checks.equal(len(calls), 1, f"{label}: un solo effetto visivo")
            if calls:
                checks.require(
                    "Ring Explosion" in calls[0]
                    and "Global.RGB" in calls[0]
                    and "Sound" not in calls[0],
                    f"{label}: effetto diverso da Ring RGB visivo",
                )
    death = rules_containing(rules, "Player Died;", "Event Player.PosisiMati = Position Of(Event Player);")
    checks.equal(len(death), 1, "cattura posizione morte")
    jump = [rule for rule in rules if code_contains(rule.body, "Is Alive(Event Player) == False;", "Button(Jump)", "Respawn(Event Player);", "PosisiBangkitAman")]
    checks.equal(len(jump), 1, "Jump respawn")
    if jump:
        body = mask_strings(jump[0].body)
        checks.require(
            body.find("Nearest Walkable Position") < body.find("Respawn(Event Player);") < body.find("Teleport(Event Player, Event Player.PosisiBangkitAman);"),
            "Jump respawn: ordine posizione sicura -> respawn -> teleport errato",
        )


def check_rgb_system(checks: Checks, source: str, rules: list[Rule]) -> None:
    globals_body = section_body(source, "variables")
    for slot, name in ((38, "RGB"), (39, "RGBFase")):
        checks.require(
            re.search(rf"(?m)^\s*{slot}\s*:\s*{name}\s*$", globals_body) is not None,
            f"RGB: slot global {slot} deve essere {name}",
        )
    clean = mask_strings(source)
    checks.require("Global.RGBFase = 0;" in clean, "RGB: fase iniziale assente")
    checks.require("80 + (Global.RGBFase" in clean and "* 0.686" in clean, "RGB: floor pastel/neon 80..255 assente")
    checks.require("Global.RGB = Custom Color(255, 80, 80, 255);" in clean, "RGB: colore iniziale pastel-neon assente")
    rgb_rules = [rule for rule in rules if code_contains(
        rule.body,
        "Ongoing - Global;",
        "Global.RGB = Custom Color(",
        "Wait(0.100, Ignore Condition);",
        "Global.RGBFase = (Global.RGBFase + 3) % 1530;",
        "Loop If Condition Is True;",
    )]
    checks.equal(len(rgb_rules), 1, "loop RGB globale")
    hud = [call for call in call_texts(source, "Create HUD Text") if "CHILL DEDICATED SERVER" in call and "Global.TeksWaktuServer" in call]
    checks.equal(len(hud), 1, "HUD principale RGB")
    if hud:
        checks.require("Global.RGB" in hud[0] and "Visible To String and Color" in hud[0], "titolo/timer non rivalutano Global.RGB")
    apply = rules_containing(rules, "Subroutine;", "EfekTerapkan;")
    restore = rules_containing(rules, "Subroutine;", "EfekPulihkan;")
    if apply:
        checks.require(code_contains(apply[0].body, "Ring Explosion, Global.RGB"), "effetto applicazione non usa Ring RGB")
    if restore:
        checks.require(code_contains(restore[0].body, "Ring Explosion, Global.RGB"), "effetto ripristino non usa Ring RGB")


def check_player_icon_menu(checks: Checks, source: str, rules: list[Rule], subroutines: set[str]) -> None:
    expected_icons = [
        'Custom String("")',
        "Icon String(Arrow: Down)",
        "Icon String(Arrow: Left)",
        "Icon String(Arrow: Right)",
        "Icon String(Arrow: Up)",
        "Icon String(Asterisk)",
        "Icon String(Bolt)",
        "Icon String(Checkmark)",
        "Icon String(Circle)",
        "Icon String(Club)",
        "Icon String(Diamond)",
        "Icon String(Dizzy)",
        "Icon String(Exclamation Mark)",
        "Icon String(Eye)",
        "Icon String(Fire)",
        "Icon String(Flag)",
        "Icon String(Halo)",
        "Icon String(Happy)",
        "Icon String(Heart)",
        "Icon String(Moon)",
        "Icon String(No)",
        "Icon String(Plus)",
        "Icon String(Poison)",
        "Icon String(Poison 2)",
        "Icon String(Question Mark)",
        "Icon String(Radioactive)",
        "Icon String(Recycle)",
        "Icon String(Ring Thick)",
        "Icon String(Ring Thin)",
        "Icon String(Sad)",
        "Icon String(Skull)",
        "Icon String(Spade)",
        "Icon String(Spiral)",
        "Icon String(Stop)",
        "Icon String(Trashcan)",
        "Icon String(Warning)",
        "Icon String(X)",
    ]
    expected_names = [
        "NOTHING",
        "ARROW: DOWN",
        "ARROW: LEFT",
        "ARROW: RIGHT",
        "ARROW: UP",
        "ASTERISK",
        "BOLT",
        "CHECKMARK",
        "CIRCLE",
        "CLUB",
        "DIAMOND",
        "DIZZY",
        "EXCLAMATION MARK",
        "EYE",
        "FIRE",
        "FLAG",
        "HALO",
        "HAPPY",
        "HEART",
        "MOON",
        "NO",
        "PLUS",
        "POISON",
        "POISON 2",
        "QUESTION MARK",
        "RADIOACTIVE",
        "RECYCLE",
        "RING THICK",
        "RING THIN",
        "SAD",
        "SKULL",
        "SPADE",
        "SPIRAL",
        "STOP",
        "TRASHCAN",
        "WARNING",
        "X",
    ]
    actual_icons = [re.sub(r"\s+", " ", item).strip() for item in top_level_items(array_body(source, "Global.DaftarIkon"))]
    checks.equal(actual_icons, expected_icons, "37 voci menu 7: niente + 36 icone Workshop")
    checks.equal(custom_strings(array_body(source, "Global.NamaIkon")), expected_names, "nomi delle 37 voci icona")

    variables = section_body(source, "variables")
    for slot, name in ((40, "DaftarIkon"), (41, "NamaIkon")):
        checks.require(re.search(rf"(?m)^\s*{slot}\s*:\s*{name}\s*$", variables) is not None, f"icone: slot global {slot} deve essere {name}")
    for slot, name in ((61, "IndeksIkon"), (62, "KursorIkon")):
        checks.require(re.search(rf"(?m)^\s*{slot}\s*:\s*{name}\s*$", variables) is not None, f"icone: slot player {slot} deve essere {name}")
    checks.require("GambarIkon" in subroutines, "icone: subroutine GambarIkon assente")
    checks.require("Event Player.IndeksIkon = 0;" in source and "Event Player.KursorIkon = 0;" in source, "icone: default NOTHING non inizializzato")

    classification = [rule for rule in rules if rule.name.startswith("02 - Pemain:")]
    checks.equal(len(classification), 1, "regola roster per icona player")
    if classification:
        body = classification[0].body
        checks.require(body.count("Global.DaftarIkon[Event Player.IndeksIkon]") >= 2, "icona player non presente in entrambe le liste")
        for segment in re.findall(r'Custom String\(\"\{0\} \{1\} \{2\}[^;]+', body):
            icon_at = segment.find("Global.DaftarIkon[Event Player.IndeksIkon]")
            hero_at = segment.find("Hero Icon String")
            checks.require(0 <= icon_at < hero_at, "icona player deve precedere l'icona eroe")
        checks.require("CHILL for" not in body and " - CHILL " not in body, "roster sinistro contiene ancora CHILL for")
        checks.require(" - soundtrack:" not in body and " - เพลงประกอบ:" not in body, "roster destro contiene ancora il prefisso soundtrack")
        checks.require("Global.RGB" not in body, "roster: RGB non deve colorare il nome player")
        checks.require(body.count("Event Player.WarnaNama") >= 2, "roster: entrambe le liste devono usare il colore nome scelto")
        checks.require('Custom String("{0} - {1} MIN", Event Player, Event Player.MenitLobi)' in body, "roster sinistro: MIN assente")

    next_rules = [rule for rule in rules if code_contains(rule.body, "Event Player.PerintahMenu == 3;", "Event Player.KursorIkon = (Event Player.KursorIkon + 1) % Count Of(Global.DaftarIkon);")]
    prev_rules = [rule for rule in rules if code_contains(rule.body, "Event Player.PerintahMenu == 4;", "Event Player.KursorIkon = (Event Player.KursorIkon + Count Of(Global.DaftarIkon) - 1) % Count Of(Global.DaftarIkon);")]
    checks.equal(len(next_rules), 1, "menu 7: navigazione icona successiva")
    checks.equal(len(prev_rules), 1, "menu 7: navigazione icona precedente")

    interact = [rule for rule in rules if code_contains(rule.body, "Event Player.PerintahMenu == 1;", "Event Player.IndeksIkon = Event Player.KursorIkon;", "Call Subroutine(EfekTerapkan);")]
    checks.equal(len(interact), 1, "menu 7: applicazione icona")
    renderers = rules_containing(rules, "Subroutine;", "GambarIkon;")
    checks.equal(len(renderers), 1, "renderer menu 7")
    if renderers:
        checks.require("/37" in renderers[0].body, "menu 7 non mostra 37 voci")
        checks.require("Global.RGB" not in renderers[0].body, "menu 7: RGB deve restare fuori dal menu icone")
        checks.require("NOTHING" in renderers[0].body and "TIDAK ADA" in renderers[0].body and "ไม่มี" in renderers[0].body, "menu 7: voce niente non localizzata")



def check_idempotent_menu_feedback(checks: Checks, source: str, rules: list[Rule]) -> None:
    handlers = [
        rule for rule in rules
        if code_contains(rule.body, "Event Player.PerintahMenu == 1;", "Event Player.HalamanMenu = Global.KodeMenu")
    ]
    checks.equal(len(handlers), 1, "handler Interact idempotente")
    if not handlers:
        return
    body = mask_strings(handlers[0].body)
    for token in (
        "If(Event Player.IndeksGenre != Event Player.KursorGenre);",
        "If(Event Player.ModeKamera != 0);",
        "If(Or(Event Player.ModeKamera != 1, Event Player.TargetKamera != Event Player));",
        "If(Or(Event Player.ModeKamera != 2, Event Player.TargetKamera != Event Player.CalonTargetKamera));",
        "If(Event Player.IndeksWarna != Event Player.KursorWarna);",
        "If(Event Player.IndeksBahasa != Event Player.KursorBahasa);",
        "If(Event Player.ModeKebal != Event Player.KursorKebal);",
        "If(Event Player.IndeksSuara != Event Player.KursorSuara);",
        "If(Event Player.IndeksIkon != Event Player.KursorIkon);",
        "If(Event Player.TeleportasiJongkokDiaktifkan != (Event Player.KursorTeleportasiJongkok == 1));",
        "If(Event Player.PrivasiInspeksiAktif != (Event Player.KursorPrivasiInspeksi == 1));",
    ):
        checks.require(token in body, f"feedback menu non protetto da cambio reale: {token}")

    # Each state assignment must occur after its corresponding inequality guard.
    ordered_pairs = (
        ("If(Event Player.IndeksGenre != Event Player.KursorGenre);", "Event Player.IndeksGenre = Event Player.KursorGenre;"),
        ("If(Event Player.IndeksWarna != Event Player.KursorWarna);", "Event Player.IndeksWarna = Event Player.KursorWarna;"),
        ("If(Event Player.IndeksBahasa != Event Player.KursorBahasa);", "Event Player.IndeksBahasa = Event Player.KursorBahasa;"),
        ("If(Event Player.ModeKebal != Event Player.KursorKebal);", "Event Player.ModeKebal = Event Player.KursorKebal;"),
        ("If(Event Player.IndeksSuara != Event Player.KursorSuara);", "Event Player.IndeksSuara = Event Player.KursorSuara;"),
        ("If(Event Player.IndeksIkon != Event Player.KursorIkon);", "Event Player.IndeksIkon = Event Player.KursorIkon;"),
        ("If(Event Player.TeleportasiJongkokDiaktifkan != (Event Player.KursorTeleportasiJongkok == 1));", "Event Player.TeleportasiJongkokDiaktifkan = Event Player.KursorTeleportasiJongkok == 1;"),
        ("If(Event Player.PrivasiInspeksiAktif != (Event Player.KursorPrivasiInspeksi == 1));", "Event Player.PrivasiInspeksiAktif = Event Player.KursorPrivasiInspeksi == 1;"),
    )
    for guard, assignment in ordered_pairs:
        checks.require(0 <= body.find(guard) < body.find(assignment), f"assegnazione menu fuori dalla guardia: {assignment}")


def check_menu_palette_and_name_colors(checks: Checks, source: str, rules: list[Rule]) -> None:
    colors = [re.sub(r"\s+", " ", item).strip() for item in top_level_items(array_body(source, "Global.DaftarWarna"))]
    id_names = custom_strings(array_body(source, "Global.NamaWarna"))
    en_names = custom_strings(array_body(source, "Global.NamaWarnaEN"))
    th_names = custom_strings(array_body(source, "Global.NamaWarnaTH"))
    checks.equal(len(colors), 32, "Name Color: 32 colori")
    checks.equal(len(id_names), 32, "Name Color: 32 nomi ID")
    checks.equal(len(en_names), 32, "Name Color: 32 nomi EN")
    checks.equal(len(th_names), 32, "Name Color: 32 nomi TH")

    expected_tail = [
        "Custom Color(255, 180, 145, 255)",
        "Custom Color(255, 145, 90, 255)",
        "Custom Color(255, 165, 205, 255)",
        "Custom Color(255, 70, 220, 255)",
        "Custom Color(230, 100, 255, 255)",
        "Custom Color(155, 165, 255, 255)",
        "Custom Color(105, 100, 255, 255)",
        "Custom Color(80, 110, 255, 255)",
        "Custom Color(70, 255, 255, 255)",
        "Custom Color(110, 245, 210, 255)",
        "Custom Color(80, 240, 170, 255)",
        "Custom Color(190, 255, 80, 255)",
    ]
    checks.equal(colors[-12:], expected_tail, "Name Color: nuove 12 tonalità")
    checks.equal(
        en_names[-12:],
        ["Peach Glow", "Apricot Neon", "Cherry Blossom", "Hot Magenta", "Fuchsia Dream", "Soft Periwinkle", "Electric Indigo", "Royal Blue", "Cyan Neon", "Seafoam", "Jade Glow", "Neon Chartreuse"],
        "Name Color: nomi EN nuove tonalità",
    )

    def renderer(subroutine: str) -> str:
        matches = rules_containing(rules, "Subroutine;", f"{subroutine};")
        checks.equal(len(matches), 1, f"palette renderer {subroutine}")
        return matches[0].body if matches else ""

    main = renderer("GambarUtama")
    soundtrack = renderer("GambarMusik")
    camera = renderer("GambarKamera")
    name_color = renderer("GambarWarna")
    language = renderer("GambarBahasa")
    revenge = renderer("GambarBalasDendam")
    unkillable = renderer("GambarKebal")
    voice = renderer("GambarSuara")
    icon = renderer("GambarIkon")
    crouch_teleport = renderer("GambarSakelarTeleportasi")
    name_privacy = renderer("GambarPrivasiInspeksi")

    # Inputs/subheaders keep their established light colors.
    for body, token, label in (
        (main, "Custom Color(210, 230, 255, 255)", "main"),
        (soundtrack, "Custom Color(205, 235, 255, 255)", "soundtrack"),
        (camera, "Custom Color(205, 235, 255, 255)", "camera"),
        (name_color, "Custom Color(220, 235, 255, 255)", "name color"),
        (language, "Custom Color(225, 210, 255, 255)", "language"),
        (revenge, "Custom Color(255, 220, 220, 255)", "revenge"),
        (unkillable, "Custom Color(255, 220, 220, 255)", "unkillable"),
        (voice, "Custom Color(225, 215, 255, 255)", "voice"),
        (icon, "Custom Color(225, 215, 255, 255)", "player icon"),
        (crouch_teleport, "Custom Color(230, 255, 210, 255)", "crouch teleport"),
        (name_privacy, "Custom Color(255, 220, 238, 255)", "name privacy"),
    ):
        checks.require(token in body, f"palette input modificata per {label}")

    transition = renderer("TransisiWarnaMenu")
    for body, label in (
        (main, "main"),
        (soundtrack, "soundtrack"),
        (camera, "camera"),
        (name_color, "name color"),
        (language, "language"),
        (revenge, "revenge"),
        (unkillable, "unkillable"),
        (voice, "voice"),
        (icon, "player icon"),
        (crouch_teleport, "crouch teleport"),
        (name_privacy, "name privacy"),
    ):
        checks.require("Event Player.WarnaMenu" in body, f"palette animata assente per {label}")
        checks.require("Visible To String and Color" in body, f"rivalutazione colore assente per {label}")

    for token in (
        "Vector(55, 235, 245)",
        "Vector(90, 180, 255)",
        "Global.DaftarWarnaRGB[Event Player.KursorWarna]",
        "Vector(190, 120, 255)",
        "Vector(255, 80, 80)",
        "Vector(255, 185, 90)",
        "Vector(115, 235, 170)",
        "Vector(235, 135, 255)",
        "Vector(190, 255, 80)",
        "Vector(255, 120, 190)",
    ):
        checks.require(token in transition, f"palette transizione incompleta: {token}")


def check_runtime_efficiency_audit(checks: Checks, source: str, rules: list[Rule]) -> None:
    clean = mask_strings(source)
    variables = section_body(source, "variables")
    checks.require(re.search(r"(?m)^\s*42\s*:\s*SlotHUDTerakhir\s*$", variables) is not None, "audit: SlotHUDTerakhir assente")
    checks.require("Global.SlotHUDTerakhir = -1;" in clean, "audit: cache ultima riga non inizializzata")
    checks.require("Global.SlotHUDTerakhir = Max(Global.SlotHUDTerakhir, Event Player.UrutanHUD);" in clean, "audit: cache ultima riga non aggiornata al join")
    checks.require("Event Player.UrutanHUD == Global.SlotHUDTerakhir" in clean, "audit: roster non usa cache ultima riga")
    checks.require("Last Of(Sorted Array(Global.PemainManusia, Player Variable(Current Array Element, UrutanHUD)))" not in clean, "audit: sort roster rivalutato ancora presente")
    checks.require("Global.SlotHUDTerakhir = Count Of(Global.SlotHUDPemain) == 0 ? -1 : Last Of(Sorted Array(Global.SlotHUDPemain, Current Array Element));" in clean, "audit: cache ultima riga non ricalcolata al leave")

    menu_open = [rule for rule in rules if code_contains(rule.body, "Event Player.MenuTerbuka = True;", "Event Player.HalamanMenu = -1;")]
    checks.equal(len(menu_open), 1, "audit: apertura Arcade Menu")
    if menu_open:
        body = mask_strings(menu_open[0].body)
        checks.require("Call Subroutine(SegarkanTargetKamera);" not in body, "audit: refresh camera inutile nel main menu")
        checks.require("Call Subroutine(SegarkanTargetBalasDendam);" not in body, "audit: refresh revenge inutile nel main menu")

    expected = (
        ("02c - Ruang Muncul:", "Wait(1, Abort When False);", "spawn cache 1Hz"),
        ("03 - Waktu:", "Wait(5, Ignore Condition);", "minuti 0,2Hz"),
        ("07b - Menu kamera:", "Wait(1, Abort When False);", "camera passive 1Hz"),
        ("07c - Menu Balas Dendam:", "Wait(1, Abort When False);", "revenge passive 1Hz"),
        ("14 - Intip Pahlawan:", "Wait(0.200, Abort When False);", "inspection 5Hz"),
        ("19f - Teleportasi Jongkok:", "Wait(1, Abort When False);", "teleport passive 1Hz"),
    )
    for prefix, token, label in expected:
        matches = [rule for rule in rules if rule.name.startswith(prefix)]
        checks.equal(len(matches), 1, f"audit: {label}")
        if matches:
            body = mask_strings(matches[0].body)
            checks.require(token in body, f"audit: frequenza errata {label}")
            if prefix.startswith("02c"):
                checks.require("Loop If Condition Is True;" in body, "audit: spawn cache senza loop bounded")

    checks.equal(len(call_texts(source, "Ray Cast Hit Position")), 1, "audit: raycast camera")
    inspection_sorts = [rule for rule in rules if code_contains(rule.body, "Subroutine;", "SegarkanTargetInspeksi;", "Sorted Array(Event Player.DaftarTargetInspeksi")]
    checks.equal(len(inspection_sorts), 1, "audit: sort inspection")

    for sub in ("GambarUtama", "GambarMusik", "GambarKamera", "GambarWarna", "GambarBahasa", "GambarBalasDendam", "GambarTeleportasi", "GambarKebal", "GambarSuara", "GambarIkon"):
        checks.equal(len(rules_containing(rules, "Subroutine;", f"{sub};")), 1, f"audit: definizione unica {sub}")




def check_smooth_menu_color_transition(checks: Checks, source: str, rules: list[Rule], subroutines: set[str]) -> None:
    clean = mask_strings(source)
    variables = section_body(source, "variables")
    checks.require(re.search(r"(?m)^\s*43\s*:\s*DaftarWarnaRGB\s*$", variables) is not None, "menu smooth: global DaftarWarnaRGB assente")
    checks.require(re.search(r"(?m)^\s*63\s*:\s*WarnaMenu\s*$", variables) is not None, "menu smooth: player WarnaMenu assente")
    rgb_vectors = [re.sub(r"\s+", " ", item).strip() for item in top_level_items(array_body(source, "Global.DaftarWarnaRGB"))]
    checks.equal(len(rgb_vectors), 32, "menu smooth: 32 vettori RGB name-color")
    checks.require("Event Player.WarnaMenu = Vector(55, 235, 245);" in clean, "menu smooth: WarnaMenu deve iniziare come Vector")
    checks.require("TransisiWarnaMenu" in subroutines, "menu smooth: subroutine TransisiWarnaMenu assente")
    checks.require("Event Player.KursorWarna = Event Player.KursorWarna;" in clean, "menu smooth: Name Color deve conservare il cursore")

    transition = rules_containing(rules, "Subroutine;", "TransisiWarnaMenu;")
    checks.equal(len(transition), 1, "menu smooth: renderer transizione")
    if transition:
        body = mask_strings(transition[0].body)
        checks.require("Chase Player Variable Over Time(Event Player, WarnaMenu," in body and "0.350, Destination and Duration);" in body, "menu smooth: chase 0,35 s assente")
        for token in (
            "Vector(55, 235, 245)",
            "Vector(90, 180, 255)",
            "Global.DaftarWarnaRGB[Event Player.KursorWarna]",
            "Vector(190, 120, 255)",
            "Vector(255, 80, 80)",
            "Vector(255, 185, 90)",
            "Vector(115, 235, 170)",
            "Vector(235, 135, 255)",
            "Vector(190, 255, 80)",
            "Vector(255, 120, 190)",
        ):
            checks.require(token in body, f"menu smooth: destinazione vector assente {token}")
        checks.require("Custom Color(" not in body, "menu smooth: Chase non deve ricevere Color")
        checks.require("Global.DaftarWarna[Event Player.KursorWarna]" not in body, "menu smooth: Chase non deve ricevere un Color da DaftarWarna")
        checks.require("Loop If Condition Is True;" not in body, "menu smooth: transizione non deve usare loop")

    router = rules_containing(rules, "Subroutine;", "GambarMenu;")
    checks.equal(len(router), 1, "menu smooth: router GambarMenu")
    if router:
        checks.require("Call Subroutine(TransisiWarnaMenu);" in mask_strings(router[0].body), "menu smooth: GambarMenu non aggiorna destinazione")

    converted = "Custom Color(X Component Of(Event Player.WarnaMenu), Y Component Of(Event Player.WarnaMenu), Z Component Of(Event Player.WarnaMenu), 255)"
    for sub in ("GambarUtama", "GambarMusik", "GambarKamera", "GambarWarna", "GambarBahasa", "GambarBalasDendam", "GambarKebal", "GambarSuara", "GambarIkon", "GambarSakelarTeleportasi", "GambarPrivasiInspeksi"):
        matches = rules_containing(rules, "Subroutine;", f"{sub};")
        checks.equal(len(matches), 1, f"menu smooth: renderer {sub}")
        if matches:
            body = mask_strings(matches[0].body)
            checks.require(converted in body, f"menu smooth: {sub} non converte WarnaMenu Vector in Custom Color")
            checks.require("Visible To String and Color" in body, f"menu smooth: {sub} non rivaluta il colore")
    checks.require("Event Player.WarnaMenu, Visible To" not in clean, "menu smooth: Color raw non valido ancora passato agli HUD")


def check_localization_and_indonesian_naming(checks: Checks, source: str, rules: list[Rule]) -> None:
    variables = section_body(source, "variables")
    for old in (
        "RestartSudahDiminta", "DaftarNegaraVPN", "IndeksNegaraVPN", "BotAI", "MenitLobby",
        "UnkillableAktif", "KursorUnkillable", "TeleportCrouchAktif", "PosisiRespawnAman",
        "RespawnJumpDipakai", "GambarUnkillable",
    ):
        checks.require(old not in variables and old not in source, f"nomenclatura lama ancora presente: {old}")

    for new in (
        "MulaiUlangSudahDiminta", "DaftarLokasiServer", "IndeksLokasiServer", "BotOtomatis", "MenitLobi",
        "KebalAktif", "KursorKebal", "TeleportasiJongkokAktif", "PosisiBangkitAman",
        "BangkitLompatDipakai", "GambarKebal",
    ):
        checks.require(new in source, f"nomenclatura Indonesia mancante: {new}")

    banned_rule_fragments = (
        " - Global:", "lento", "Respawn Jump:", "Unkillable:", "Teleport Crouch:",
        "Dispatcher input", "dispatcher", "separato", "Riattiva", "destinazione", "precedente",
        "successiva", "esegue il teletrasporto", "lista target", "senza ridisegno", "Chiudi appena",
        "overlay selama Crouch", "scatto",
    )
    names = "\n".join(rule.name for rule in rules)
    for fragment in banned_rule_fragments:
        checks.require(fragment not in names, f"titolo regola non completamente indonesiano: {fragment}")

    for required in (
        "00 - Umum:", "RGB pastel neon lambat untuk judul, waktu, dan efek",
        "Bangkit Lompat:", "Kebal:", "Teleportasi Jongkok:",
        "Pengatur masukan terpisah dari Menu Arcade", "tujuan berikutnya", "tujuan sebelumnya",
        "Interact menjalankan teleportasi", "tanpa menggambar ulang berkala", "tanpa lompatan",
    ):
        checks.require(required in names, f"titolo regola Indonesia mancante: {required}")

    small_messages = call_texts(source, "Small Message")
    checks.require(len(small_messages) > 0, "nessun Small Message trovato")
    for call in small_messages:
        checks.require("IndeksBahasa" in call, "Small Message non localizzato in base alla lingua")

    # Three-language HUD anchors: global info, menus and diagnostics.
    for token in (
        "Hold {0}: inspect hero + HP",
        "Tahan {0}: cek pahlawan + HP",
        "กด {0} ค้าง: ดูฮีโร่ + HP",
        "LOBBY & CHILL TIME",
        "LOBI & WAKTU SANTAI",
        "ล็อบบี้ & เวลาชิล",
        "PLAYER VIBES",
        "MUSIK PEMAIN",
        "เพลงของผู้เล่น",
        "BEBAN {0}% | RATA {1}% | PUNCAK {2}%",
        "LOAD {0}% | AVG {1}% | MAX {2}%",
        "โหลด {0}% | เฉลี่ย {1}% | สูงสุด {2}%",
        "0 - MUSIK",
        "5 - KEBAL",
        "5 - ฆ่าไม่ตาย",
        "6 - SUARA PAHLAWAN",
        "6 - เสียงฮีโร่",
    ):
        checks.require(token in source, f"localizzazione HUD mancante: {token}")

    for stale in (
        "DAFTAR PEMAIN & WAKTU CHILL", "SOUNDTRACK PEMAIN", "belum pilih soundtrack",
        "Tahan {0}: lihat pemain, hero & kesehatan", "Unkillable + 1 HP aktif.",
        "Pengubah suara hero diterapkan.", "Respawn Jump:", "Teleport Crouch:",
    ):
        checks.require(stale not in source, f"testo vecchio/non localizzato ancora presente: {stale}")


def check_crouch_toggle_and_name_privacy(checks: Checks, source: str, rules: list[Rule], subroutines: set[str]) -> None:
    variables = section_body(source, "variables")
    for slot, name in (
        (64, "TeleportasiJongkokDiaktifkan"),
        (65, "KursorTeleportasiJongkok"),
        (66, "PrivasiInspeksiAktif"),
        (67, "KursorPrivasiInspeksi"),
    ):
        checks.require(re.search(rf"(?m)^\s*{slot}\s*:\s*{name}\s*$", variables) is not None, f"menu 8/9: slot player {slot} deve essere {name}")

    for token in (
        "Event Player.TeleportasiJongkokDiaktifkan = False;",
        "Event Player.KursorTeleportasiJongkok = 0;",
        "Event Player.PrivasiInspeksiAktif = False;",
        "Event Player.KursorPrivasiInspeksi = 0;",
    ):
        checks.require(token in mask_strings(source), f"menu 8/9: default OFF mancante {token}")

    open_rules = [rule for rule in rules if rule.name.startswith("19 - Teleportasi Jongkok:")]
    checks.equal(len(open_rules), 1, "menu 8: regola apertura Teleport Jongkok")
    if open_rules:
        checks.require("Event Player.TeleportasiJongkokDiaktifkan == True;" in mask_strings(open_rules[0].body), "menu 8: Crouch apre Teleport anche quando OFF")

    for sub in ("GambarSakelarTeleportasi", "GambarPrivasiInspeksi"):
        checks.require(sub in subroutines, f"menu 8/9: subroutine {sub} assente")
        renderers = rules_containing(rules, "Subroutine;", f"{sub};")
        checks.equal(len(renderers), 1, f"menu 8/9: renderer {sub}")
        if renderers:
            checks.require("/2" in renderers[0].body, f"menu 8/9: {sub} non mostra 2 voci")

    checks.require("8 - CROUCH TELEPORT" in source and "8 - TELEPORT JONGKOK" in source and "8 - เทเลพอร์ตตอนย่อ" in source, "menu 8 non localizzato EN/ID/TH")
    checks.require("Crouch privacy enabled. Enemies see nothing." in source, "menu 9: feedback EN privacy ON assente")
    checks.require("Privasi Jongkok aktif. Musuh tidak melihat apa pun." in source, "menu 9: feedback ID privacy ON assente")
    checks.require("เปิดความเป็นส่วนตัวตอนย่อ ศัตรูจะไม่เห็นอะไรเลย" in source, "menu 9: feedback TH privacy ON assente")
    checks.require("9 - CROUCH PRIVACY" in source and "9 - PRIVASI JONGKOK" in source and "9 - ความเป็นส่วนตัวตอนย่อ" in source, "menu 9 non localizzato EN/ID/TH")

    inspect = [rule for rule in rules if rule.name.startswith("13 - Intip Pahlawan:")]
    checks.equal(len(inspect), 1, "menu 9: regola testo inspection")
    if inspect:
        body = mask_strings(inspect[0].body)
        raw = inspect[0].body
        checks.require("Player Variable(Event Player.TargetInspeksi, PrivasiInspeksiAktif) == True" in body, "menu 9: target non dipende dalla privacy")
        checks.require("Team Of(Event Player.TargetInspeksi) != Team Of(Event Player)" in body, "menu 9: privacy non limitata ai viewer nemici")
        checks.require('Custom String("")' in raw, "menu 9: ramo HUD nemico completamente vuoto assente")
        privacy_at = body.find("Player Variable(Event Player.TargetInspeksi, PrivasiInspeksiAktif) == True")
        enemy_at = body.find("Team Of(Event Player.TargetInspeksi) != Team Of(Event Player)", privacy_at)
        checks.require(0 <= privacy_at < enemy_at, "menu 9: controllo privacy/squadra in ordine errato")
        checks.require('Custom String("{0} {1} | {2}"' in raw, "menu 9: HUD completo alleato/pubblico assente")
        full_at = raw.find('Custom String("{0} {1} | {2}"')
        full_segment = raw[full_at:full_at + 900]
        checks.require("Hero Icon String" in full_segment and 'Custom String("{0}", Event Player.TargetInspeksi)' in full_segment and "Health(Event Player.TargetInspeksi)" in full_segment, "menu 9: HUD completo alleato/pubblico deve mantenere icona, nome e salute")

    handler = [rule for rule in rules if code_contains(rule.body, "Event Player.PerintahMenu == 1;", "Event Player.HalamanMenu = Global.KodeMenu")]
    checks.equal(len(handler), 1, "menu 8/9: handler Interact")
    if handler:
        body = mask_strings(handler[0].body)
        for token in (
            "Event Player.TeleportasiJongkokDiaktifkan = Event Player.KursorTeleportasiJongkok == 1;",
            "Event Player.PrivasiInspeksiAktif = Event Player.KursorPrivasiInspeksi == 1;",
        ):
            checks.require(token in body, f"menu 8/9: applicazione mancante {token}")


def check_unkillable_three_modes(checks: Checks, source: str, rules: list[Rule]) -> None:
    clean = mask_strings(source)
    variables = section_body(source, "variables")
    for slot, name in ((68, "ModeKebal"), (69, "IkonKebal")):
        checks.require(re.search(rf"(?m)^\s*{slot}\s*:\s*{name}\s*$", variables) is not None, f"Unkillable: slot {slot} deve essere {name}")
    checks.require("Event Player.ModeKebal = 0;" in clean and "Event Player.IkonKebal = Null;" in clean, "Unkillable: default OFF/icon Null")
    checks.require("Event Player.KursorKebal = (Event Player.KursorKebal + 1) % 3;" in clean, "Unkillable: next non usa 3 modalità")
    checks.require("Event Player.KursorKebal = (Event Player.KursorKebal + 2) % 3;" in clean, "Unkillable: previous non usa 3 modalità")

    renderer = rules_containing(rules, "Subroutine;", "GambarKebal;")
    checks.equal(len(renderer), 1, "Unkillable renderer")
    if renderer:
        checks.require("/3" in renderer[0].body and "FULL HP" in renderer[0].body and "1 HP" in renderer[0].body, "Unkillable: menu non mostra OFF/1HP/FULLHP")

    handlers = [r for r in rules if code_contains(r.body, "Event Player.PerintahMenu == 1;", "Event Player.HalamanMenu = Global.KodeMenu")]
    checks.equal(len(handlers), 1, "Unkillable handler menu")
    if handlers:
        raw = handlers[0].body
        body = mask_strings(raw)
        compact = re.sub(r"\s+", "", body)

        # Opening page 5 only mirrors the applied mode; it must never apply it.
        checks.require(
            "ElseIf(EventPlayer.HalamanMenu==5);EventPlayer.KursorKebal=EventPlayer.ModeKebal;ElseIf(EventPlayer.HalamanMenu==6);" in compact,
            "Unkillable: apertura menu 5 non sincronizza soltanto il cursore",
        )
        checks.equal(body.count("Event Player.ModeKebal = Event Player.KursorKebal;"), 1, "Unkillable: una sola assegnazione modalità nel dispatcher")
        checks.require("KebalAktif != And(Event Player.KursorKebal == 1" not in body, "Unkillable: logica legacy ON/OFF ancora presente")
        checks.require("KebalAktif = And(Event Player.KursorKebal == 1" not in body, "Unkillable: assegnazione legacy ON/OFF ancora presente")

        # 1 HP cannot be enabled inside Spawn Room; FULL HP remains selectable.
        for token in (
            "If(Event Player.ModeKebal != Event Player.KursorKebal);",
            "If(And(Event Player.KursorKebal == 1, Is In Spawn Room(Event Player) == True));",
            "Event Player.KursorKebal = Event Player.ModeKebal;",
            "Event Player.ModeKebal = Event Player.KursorKebal;",
            "Event Player.KebalAktif = Event Player.ModeKebal != 0;",
            "If(Event Player.ModeKebal == 0);",
            "If(Event Player.ModeKebal == 1);",
            "Set Damage Received(Event Player, 100);",
            "Set Player Health(Event Player, 1);",
            "Set Damage Received(Event Player, 0);",
            "Set Player Health(Event Player, Max Health(Event Player));",
            "Create Icon(All Players(All Teams), Event Player, Warning, Visible To and Position, Custom Color(255, 80, 80, 255), True);",
            "Create Icon(All Players(All Teams), Event Player, Halo, Visible To and Position, Global.RGB, True);",
            "Event Player.IkonKebal = Last Created Entity;",
            "Destroy Icon(Event Player.IkonKebal);",
        ):
            checks.require(token in body, f"Unkillable menu incompleto: {token}")

        mode_assignment = body.find("Event Player.ModeKebal = Event Player.KursorKebal;")
        one_hp_branch = body.find("If(Event Player.ModeKebal == 1);", mode_assignment)
        damage_100 = body.find("Set Damage Received(Event Player, 100);", one_hp_branch)
        hp_one = body.find("Set Player Health(Event Player, 1);", damage_100)
        full_else = body.find("Else;", hp_one)
        damage_zero = body.find("Set Damage Received(Event Player, 0);", full_else)
        hp_full = body.find("Set Player Health(Event Player, Max Health(Event Player));", damage_zero)
        checks.require(
            0 <= mode_assignment < one_hp_branch < damage_100 < hp_one < full_else < damage_zero < hp_full,
            "Unkillable: transizione esclusiva 1 HP / FULL HP in ordine errato",
        )

    one_hp = [r for r in rules if r.name.startswith("18b - Kebal:")]
    checks.equal(len(one_hp), 1, "Unkillable 1 HP guard")
    if one_hp:
        body = mask_strings(one_hp[0].body)
        checks.require("Event Player.ModeKebal == 1;" in body and "Is In Spawn Room(Event Player) == False;" in body, "Unkillable: 1 HP non confinato fuori Spawn Room")

    full = [r for r in rules if r.name.startswith("18d - Kebal:")]
    checks.equal(len(full), 1, "Unkillable FULL HP guard")
    if full:
        body = mask_strings(full[0].body)
        checks.require("Event Player.ModeKebal == 2;" in body and "Health(Event Player) < Max Health(Event Player);" in body and "Set Player Health(Event Player, Max Health(Event Player));" in body, "Unkillable FULL HP guard incompleta")
        checks.require("Is In Spawn Room(Event Player) == False;" not in body, "Unkillable FULL HP si resetta ancora in Spawn Room")

    spawn = [r for r in rules if r.name.startswith("18c - Kebal:")]
    checks.equal(len(spawn), 1, "Unkillable Spawn Room reset")
    if spawn:
        body = mask_strings(spawn[0].body)
        checks.require("Event Player.ModeKebal == 1;" in body, "Spawn Room reset non limitato a 1 HP")
        checks.require("Event Player.ModeKebal == 2;" not in body, "Spawn Room reset coinvolge FULL HP")
        checks.require("Event Player.HalamanMenu = -1;" not in body, "Spawn Room non deve chiudere il menu 5 per FULL HP")

    halo_calls = [call for call in call_texts(source, "Create Icon") if ", Halo," in call and "Event Player" in call]
    warning_calls = [call for call in call_texts(source, "Create Icon") if ", Warning," in call and "Event Player" in call]
    checks.equal(len(halo_calls), 1, "Unkillable FULL HP Halo public icon")
    checks.equal(len(warning_calls), 1, "Unkillable 1 HP Warning public icon")
    if halo_calls:
        checks.require("All Players(All Teams)" in halo_calls[0] and "Global.RGB" in halo_calls[0] and "Visible To and Position" in halo_calls[0], "Unkillable FULL HP Halo non è pubblico/RGB/follow")
    if warning_calls:
        checks.require("All Players(All Teams)" in warning_calls[0] and "Custom Color(255, 80, 80, 255)" in warning_calls[0] and "Visible To and Position" in warning_calls[0], "Unkillable 1 HP Warning non è pubblico/rosso/follow")

    leave = [r for r in rules if code_contains(r.body, "Player Left Match;")]
    checks.require(bool(leave) and "Destroy Icon(Event Player.IkonKebal);" in mask_strings(leave[0].body), "Unkillable Halo cleanup leave assente")


def check_vote_menu(checks: Checks, source: str, rules: list[Rule], subroutines: set[str]) -> None:
    clean = mask_strings(source)
    checks.require("GambarVoto" in subroutines and "HitungPilihan" in subroutines, "Vote: subroutine mancanti")
    checks.require("Global.KodeMenu = Array(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11);" in clean, "Vote: Menu 11 non registrato")
    renderer = rules_containing(rules, "Subroutine;", "GambarVoto;")
    checks.equal(len(renderer), 1, "Vote: renderer")
    if renderer:
        raw = renderer[0].body
        checks.require("11 - VOTE PLAYER" in raw and "11 - VOTE PEMAIN" in raw and "11 - โหวตผู้เล่น" in raw, "Vote: localizzazione incompleta")
        checks.require(raw.count("NumeroVoti") >= 12, "Vote: lista conteggi incompleta")
    tally = rules_containing(rules, "Subroutine;", "HitungPilihan;")
    checks.equal(len(tally), 1, "Vote: tally")
    if tally:
        body = mask_strings(tally[0].body)
        checks.require("Filtered Array(Global.PemainManusia" in body and "Global.PariVoti = True;" in body and "Global.LeaderVoto = Null;" in body, "Vote: tally/pareggio incompleto")
    handlers = [r for r in rules if code_contains(r.body, "Event Player.PerintahMenu == 1;", "Event Player.HalamanMenu = Global.KodeMenu")]
    checks.equal(len(handlers), 1, "Vote: handler")
    if handlers:
        body = mask_strings(handlers[0].body)
        checks.require("Event Player.TargetVoto = Global.PemainManusia[Event Player.KursorVoto];" in body and "Call Subroutine(HitungPilihan);" in body, "Vote: applicazione voto incompleta")
    checks.require("MOST VOTED:" in source and "PALING BANYAK DIPILIH:" in source and "โหวตสูงสุด:" in source, "Vote: HUD leader assente")
    checks.require("Event Player.UrutanHUD == Global.SlotHUDTerakhir" in clean and "Global.LeaderVoto != Null" in clean, "Vote: leader non ancorato/nascosto in pareggio")
    leave = [r for r in rules if code_contains(r.body, "Player Left Match;")]
    checks.require(bool(leave) and "TargetVoto == Global.PemainPembersihan" in mask_strings(leave[0].body), "Vote: cleanup leave assente")

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
        check_instant_start(checks, source, rules)
        check_bot_lifecycle(checks, source, rules)
        check_menus(checks, source, rules, subroutines)
        check_menu_palette_and_name_colors(checks, source, rules)
        check_runtime_efficiency_audit(checks, source, rules)
        check_smooth_menu_color_transition(checks, source, rules, subroutines)
        check_localization_and_indonesian_naming(checks, source, rules)
        check_camera(checks, source, rules, player_names)
        check_crouch(checks, source, rules)
        check_cleanup_and_revenge(checks, source, rules)
        check_arcade_features(checks, source, rules)
        check_unkillable_three_modes(checks, source, rules)
        check_feedback_and_jump_respawn(checks, source, rules)
        check_rgb_system(checks, source, rules)
        check_player_icon_menu(checks, source, rules, subroutines)
        check_idempotent_menu_feedback(checks, source, rules)
        check_vote_menu(checks, source, rules, subroutines)
        check_crouch_toggle_and_name_privacy(checks, source, rules, subroutines)
        check_server_location_setting(checks, source)
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
