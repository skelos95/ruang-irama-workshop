#!/usr/bin/env python3
"""Validazione statica del sorgente Overwatch Workshop.

Il validatore controlla invarianti strutturali e di progetto della versione 0.5.2.
Non sostituisce l'importazione nel client o le prove live con dodici giocatori.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
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


def rules_containing(rules: list[Rule], *tokens: str) -> list[Rule]:
    return [rule for rule in rules if all(token in rule.body for token in tokens)]


def standalone_comments(source: str) -> list[tuple[int, str]]:
    comments: list[tuple[int, str]] = []
    pattern = re.compile(r'^\s*"((?:[^"\\]|\\.)*)"\s*$', re.MULTILINE)
    for match in pattern.finditer(source):
        comments.append((line_number(source, match.start()), match.group(1)))
    return comments


def word_tokens(text: str) -> list[str]:
    return [token.casefold() for token in re.findall(r"[A-Za-zÃ€-Ã¿]+", text)]


def identifier_tokens(identifier: str) -> list[str]:
    pieces = re.findall(
        r"[A-ZÃ€-Ã]+(?=[A-ZÃ€-Ã][a-zÃ -Ã¿]|\d|$)|[A-ZÃ€-Ã]?[a-zÃ -Ã¿]+|\d+",
        identifier,
    )
    return [piece.casefold() for piece in pieces]


# Lessico volutamente conservativo: termini inequÃ­vocamente italiani nel
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
    "puÃ²", "ricorda", "riduce", "riavvia", "scegliere", "scelta", "sicura",
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
    return re.search(r"[A-Za-zÃ€-Ã¿]{2,}", cleaned) is not None


def check_language_arrays(checks: Checks, source: str) -> tuple[list[str], list[Rule]]:
    genres = custom_strings(array_body(source, "Global.DaftarGenre"))
    checks.equal(len(genres), 100, "numero di generi")
    checks.equal(len(set(genres)), 100, "numero di generi unici")

    languages = custom_strings(array_body(source, "Global.NamaBahasa"))
    checks.equal(languages, ["English", "Bahasa Indonesia", "à¹„à¸—à¸¢"], "lingue HUD")

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
       çž;¶‰žËkºwµç@‰…É½µ•¹Ñ¤MÑ…ÉÐ…µ•É„ˆ¤(€€€€€€€¥˜±•¸¡…ÉÌ¤€ôô€Ðè(€€€€€€€€€€€¡•­Ì¹É•ÅÕ¥É” (€€€€€€€€€€€€€€€€‰UÁ‘…Ñ”Ù•ÉäÉ…µ”¡A½Í¥Ñ¥½¸=˜¡Ù•¹ÐA±…å•È¹Q…É•Ñ-…µ•É„¤€¬Ù•¹ÐA±…å•È¹A½Í¥Í¥I•±…Ñ¥™-…µ•É„¤ˆ¥¸…ÉÍlÅt°(€€€€€€€€€€€€€€€€‰MÑ…ÉÐ…µ•É„¹½¸½µ‰¥¹„ÑÉ…Í±…é¥½¹”Á•Èµ™É…µ””½™Í•ÐÉ•±…Ñ¥Ù¼¥¸…¡”ˆ°(€€€€€€€€€€€€¤(€€€€€€€€€€€¡•­Ì¹É•ÅÕ¥É” (€€€€€€€€€€€€€€€€‰UÁ‘…Ñ”Ù•ÉäÉ…µ” ˆ¥¸…ÉÍlÉt…¹€‰å”A½Í¥Ñ¥½¸¡Ù•¹ÐA±…å•È¹Q…É•Ñ-…µ•É„¤ˆ¥¸…ÉÍlÉt°(€€€€€€€€€€€€€€€€‰ÁÕ¹Ñ¼‘¤µ¥É„…µ•É„¹½¸É¥Ù…±ÕÑ…Ñ¼Á•È™É…µ”‘…±°½¡¥¼‘•°Ñ…É•Ðˆ°(€€€€€€€€€€€€¤(€€€€€€€€€€€¡•­Ì¹•ÅÕ…°¡…ÉÍlÍt°€ˆàÀˆ°€‰‰±•¹¹…Ñ¥Ù¼MÑ…ÉÐ…µ•É„ˆ¤(€€€ÍÑ½Á}Á…Ñ¡Ì€ôl(€€€€€€€ÉÕ±”™½ÈÉÕ±”¥¸ÉÕ±•Ì(€€€€€€€¥˜€‰MÑ½À…µ•É„¡Ù•¹ÐA±…å•È¤ìˆ¥¸ÉÕ±”¹‰½‘ä(€€€€€€€…¹€‰Ù•¹ÐA±…å•È¹5½‘•-…µ•É„€ô€Àìˆ¥¸ÉÕ±”¹‰½‘ä(€€€€€€€…¹€‰Ù•¹ÐA±…å•È¹Q…É•Ñ-…µ•É„€ô9Õ±°ìˆ¥¸ÉÕ±”¹‰½‘ä(€€€t(€€€¡•­Ì¹É•ÅÕ¥É”¡±•¸¡ÍÑ½Á}Á…Ñ¡Ì¤€øô€È°€‰Á•É½ÉÍ¤‘¤É¥Ñ½É¹¼…±±„ÁÉ¥µ„Á•ÉÍ½¹„¹½¸ÑÉ½Ù…Ñ¤ˆ¤(€€€™½ÈÉÕ±”¥¸ÍÑ½Á}Á…Ñ¡Ìè(€€€€€€€¡•­Ì¹É•ÅÕ¥É” (€€€€€€€€€€€…±°¡˜‰Ù•¹ÐA±…å•È¹í¹…µ•ô€ôY•Ñ½È À°€À°€À¤ìˆ¥¸ÉÕ±”¹‰½‘ä™½È¹…µ”¥¸…¡•}¹…µ•Ì¤°(€€€€€€€€€€€˜‰…¡”…µ•É„¹½¸…éé•É…Ñ”¹•°Á•É½ÉÍ¼íÉÕ±”¹¹…µ”…Éôˆ°(€€€€€€€€¤(()‘•˜¡•­}É½Õ ¡¡•­Ìè¡•­Ì°Í½ÕÉ”èÍÑÈ°ÉÕ±•Ìè±¥ÍÑmIÕ±•t¤€´ø9½¹”è(€€€¡•­Ì¹•ÅÕ…° (€€€€€€€±•¸¡…±±}Ñ•áÑÌ¡Í½ÕÉ”°€‰¥Í…‰±”9…µ•Á±…Ñ•Ìˆ¤¤°€Ä°(€€€€€€€€‰¥Í…‰±”9…µ•Á±…Ñ•Ì€¡‘•Ù”…ÙÙ•¹¥É”Õ¹„Í½±„Ù½±Ñ„…±°…ÙÙ¥¼É½Õ ¤ˆ°(€€€€¤(€€€¡•­Ì¹•ÅÕ…° (€€€€€€€±•¸¡…±±}Ñ•áÑÌ¡Í½ÕÉ”°€‰¹…‰±”9…µ•Á±…Ñ•Ìˆ¤¤°€È°(€€€€€€€€‰¹…‰±”9…µ•Á±…Ñ•Ì¹•¤±•…¹ÕÀÉ½Õ ”A±…å•È1•™Ðˆ°(€€€€¤(€€€¡•­Ì¹•ÅÕ…°¡±•¸¡…±±}Ñ•áÑÌ¡Í½ÕÉ”°€‰É•…Ñ”%¸µ]½É±Q•áÐˆ¤¤°€È°€‰Ñ•ÍÑ¤µ½¹‘¼É½Õ ˆ¤(€€€¡•­Ì¹É•ÅÕ¥É”¡‰½½°¡…±±}Ñ•áÑÌ¡Í½ÕÉ”°€‰MÑ…ÉÐ½É¥¹œA±…å•È=ÕÑ±¥¹•Ìˆ¤¤°€‰½ÕÑ±¥¹”É½Õ …ÍÍ•¹Ñ¤ˆ¤(€€€¡•­Ì¹É•ÅÕ¥É”¡‰½½°¡…±±}Ñ•áÑÌ¡Í½ÕÉ”°€‰MÑ½À½É¥¹œA±…å•È=ÕÑ±¥¹•Ìˆ¤¤°€‰±•…¹ÕÀ½ÕÑ±¥¹”É½Õ …ÍÍ•¹Ñ”ˆ¤((€€€É½Õ¡}ÍÑ…ÉÐ€ôl(€€€€€€€ÉÕ±”(€€€€€€€™½ÈÉÕ±”¥¸ÉÕ±•Ì(€€€€€€€¥˜€‰Ù•¹ÐA±…å•È¹%¹ÍÁ•­Í¥­Ñ¥˜€ôQÉÕ”ìˆ¥¸ÉÕ±”¹‰½‘ä(€€€€€€€…¹€‰¥Í…‰±”9…µ•Á±…Ñ•Ìˆ¥¸ÉÕ±”¹‰½‘ä(€€€€€€€…¹€‰MÑ…ÉÐ½É¥¹œA±…å•È=ÕÑ±¥¹•Ìˆ¥¸ÉÕ±”¹‰½‘ä(€€€t(€€€¡•­Ì¹•ÅÕ…°¡±•¸¡É½Õ¡}ÍÑ…ÉÐ¤°€Ä°€‰É•½±„‘¤…ÙÙ¥¼½ÕÑ±¥¹”É½Õ ˆ¤(€€€¥˜É½Õ¡}ÍÑ…ÉÐè(€€€€€€€½ÕÑ±¥¹”€ôÉ½Õ¡}ÍÑ…ÉÑlÁt¹‰½‘ä(€€€€€€€¡•­Ì¹É•ÅÕ¥É” (€€€€€€€€€€€€‰½Õ¹Ð=˜¡±°A±…å•ÉÌ¡±°Q•…µÌ¤¤ˆ¥¸½ÕÑ±¥¹”°(€€€€€€€€€€€€‰½ÕÑ±¥¹”É½Õ ¹½¸¥Ñ•É…¹¼ÍÕ±±”Í½±”•¹Ñ¥Ó€ÁÉ•Í•¹Ñ¤ˆ°(€€€€€€€€¤(€€€€€€€¡•­Ì¹É•ÅÕ¥É” (€€€€€€€€€€€É”¹Í•…É  (€€€€€€€€€€€€€€€È‰MÑ…ÉÐ½É¥¹œA±…å•È=ÕÑ±¥¹•ÍqÌ©p¡mxít©½±½ÉqÌ©p¡qÌ©=É…¹•qÌ©p¤ˆ°(€€€€€€€€€€€€€€€½ÕÑ±¥¹”°(€€€€€€€€€€€€€€€É”¹=Q10°(€€€€€€€€€€€€¤(€€€€€€€€€€€¥Ì¹½Ð9½¹”°(€€€€€€€€€€€€‰‰½ÐÍ•¹é„½ÕÑ±¥¹”…É…¹¥½¹”ˆ°(€€€€€€€€¤(€€€€€€€¡•­Ì¹É•ÅÕ¥É” (€€€€€€€€€€€€‰A±…å•ÈY…É¥…‰±”¡q¹qÑqÑqÑqÑqÑ±°A±…å•ÉÌ¡±°Q•…µÌ¥mÙ•¹ÐA±…å•È¹%¹‘•­Í…É¥Í1Õ…Ét°]…É¹…9…µ„¤ˆ¥¸½ÕÑ±¥¹”(€€€€€€€€€€€½ÈÉ”¹Í•…É  (€€€€€€€€€€€€€€€È‰A±…å•ÈY…É¥…‰±•qÌ©p¡qÌ©±°A±…å•ÉÍp¡±°Q•…µÍp¥qÌ©ql¸¨ýquqÌ¨±qÌ©]…É¹…9…µ…qÌ©p¤ˆ°(€€€€€€€€€€€€€€€½ÕÑ±¥¹”°(€€€€€€€€€€€€€€€É”¹=Q10°(€€€€€€€€€€€€¤(€€€€€€€€€€€¥Ì¹½Ð9½¹”°(€€€€€€€€€€€€‰½ÕÑ±¥¹”‘•±¤Õµ…¹¤¹½¸ÕÍ„¥°½±½É”Á•ÉÍ½¹…±”ˆ°(€€€€€€€€¤((€€€±…ÍÍ¥™¥…Ñ¥½¹}ÉÕ±•Ì€ôÉÕ±•Í}½¹Ñ…¥¹¥¹œ¡ÉÕ±•Ì°€‰ÁÁ•¹Q¼ÉÉ…ä¡±½‰…°¹A•µ…¥¹5…¹ÕÍ¥„°Ù•¹ÐA±…å•È¤ˆ¤(€€€¡•­Ì¹É•ÅÕ¥É” (€€€€€€€‰½½°¡±…ÍÍ¥™¥…Ñ¥½¹}ÉÕ±•Ì¤(€€€€€€€…¹€‰MÑ…ÉÐ½É¥¹œA±…å•È=ÕÑ±¥¹•Ìˆ¥¸±…ÍÍ¥™¥…Ñ¥½¹}ÉÕ±•ÍlÁt¹‰½‘ä(€€€€€€€…¹€‰%¹ÍÁ•­Í¥­Ñ¥˜ˆ¥¸±…ÍÍ¥™¥…Ñ¥½¹}ÉÕ±•ÍlÁt¹‰½‘ä°(€€€€€€€€‰©½¥¸Õµ…¹¼¹½¸…¥½É¹„±¤½ÕÑ±¥¹”‘•¤Ù¥•Ý•È…ÑÑ¥Ù¤ˆ°(€€€€¤(€€€½±½É}ÉÕ±•Ì€ôÉÕ±•Í}½¹Ñ…¥¹¥¹œ¡ÉÕ±•Ì°€‰Ù•¹ÐA±…å•È¹%¹‘•­Í]…É¹„€ôÙ•¹ÐA±…å•È¹-ÕÉÍ½É]…É¹„ìˆ¤(€€€¡•­Ì¹É•ÅÕ¥É” (€€€€€€€‰½½°¡½±½É}ÉÕ±•Ì¤(€€€€€€€…¹€‰MÑ…ÉÐ½É¥¹œA±…å•È=ÕÑ±¥¹•Ìˆ¥¸½±½É}ÉÕ±•ÍlÁt¹‰½‘ä(€€€€€€€…¹€‰%¹ÍÁ•­Í¥­Ñ¥˜ˆ¥¸½±½É}ÉÕ±•ÍlÁt¹‰½‘ä°(€€€€€€€€‰…µ‰¥¼½±½É”¹½¸…¥½É¹„±¤½ÕÑ±¥¹”‘•¤Ù¥•Ý•È…ÑÑ¥Ù¤ˆ°(€€€€¤((€€€É•™É•Í¡}ÉÕ±•Ì€ôl(€€€€€€€ÉÕ±”™½ÈÉÕ±”¥¸ÉÕ±•Ì(€€€€€€€¥˜€‰M•…É­…¹Q…É•Ñ%¹ÍÁ•­Í¤ˆ¥¸ÉÕ±”¹‰½‘ä…¹€‰1½½À%˜½¹‘¥Ñ¥½¸%ÌQÉÕ”ìˆ¥¸ÉÕ±”¹‰½‘ä(€€€t(€€€¡•­Ì¹•ÅÕ…°¡±•¸¡É•™É•Í¡}ÉÕ±•Ì¤°€Ä°€‰±½½ÀÉ•™É•Í Ñ…É•ÐÉ½Õ ˆ¤(€€€¥˜É•™É•Í¡}ÉÕ±•Ìè(€€€€€€€¡•­Ì¹É•ÅÕ¥É” (€€€€€€€€€€€É”¹Í•…É ¡È‰]…¥ÑqÌ©p¡qÌ¨Áp¸ÄÀÁqÌ¨°ˆ°É•™É•Í¡}ÉÕ±•ÍlÁt¹‰½‘ä¤¥Ì¹½Ð9½¹”°(€€€€€€€€€€€€‰Ñ…É•ÐÉ½Õ ¹½¸…¥½É¹…Ñ¼½¹¤€À°ÄÀÍ•½¹‘¤ˆ°(€€€€€€€€¤((€€€±•…¹ÕÁ}ÉÕ±•Ì€ôl(€€€€€€€ÉÕ±”(€€€€€€€™½ÈÉÕ±”¥¸ÉÕ±•Í}½¹Ñ…¥¹¥¹œ¡ÉÕ±•Ì°€‰¹…‰±”9…µ•Á±…Ñ•Ìˆ°€‰MÑ½À½É¥¹œA±…å•È=ÕÑ±¥¹•Ìˆ¤(€€€€€€€¥˜€‰Ù•¹ÐA±…å•È¹%¹ÍÁ•­Í¥­Ñ¥˜€ô…±Í”ìˆ¥¸ÉÕ±”¹‰½‘ä(€€€t(€€€¡•­Ì¹•ÅÕ…°¡±•¸¡±•…¹ÕÁ}ÉÕ±•Ì¤°€Ä°€‰±•…¹ÕÀÉ½Õ ˆ¤(€€€¥˜±•…¹ÕÁ}ÉÕ±•Ìè(€€€€€€€±•…¹ÕÀ€ô±•…¹ÕÁ}ÉÕ±•ÍlÁt¹‰½‘ä(€€€€€€€¡•­Ì¹É•ÅÕ¥É” (€€€€€€€€€€€±•…¹ÕÀ¹½Õ¹Ð ‰•ÍÑÉ½ä%¸µ]½É±Q•áÐˆ¤€øô€È°(€€€€€€€€€€€€‰±•…¹ÕÀÉ½Õ ¹½¸‘¥ÍÑÉÕ”•¹ÑÉ…µ‰¤¤Ñ•ÍÑ¤µ½¹‘¼ˆ°(€€€€€€€€¤(€€€€€€€¡•­Ì¹É•ÅÕ¥É” (€€€€€€€€€€€€‰Ù•¹ÐA±…å•È¹Q•­ÍÕ¹¥„€ô9Õ±°ìˆ¥¸±•…¹ÕÀ…¹€‰Ù•¹ÐA±…å•È¹Q•­Í¥É¤€ô9Õ±°ìˆ¥¸±•…¹ÕÀ°(€€€€€€€€€€€€‰±•…¹ÕÀÉ½Õ ¹½¸…éé•É„•¹ÑÉ…µ‰¤¤É¥™•É¥µ•¹Ñ¤Ñ•ÍÑ¼ˆ°(€€€€€€€€¤(()‘•˜¡•­}±•…¹ÕÁ}…¹‘}É•Ù•¹”¡¡•­Ìè¡•­Ì°Í½ÕÉ”èÍÑÈ°ÉÕ±•Ìè±¥ÍÑmIÕ±•t¤€´ø9½¹”è(€€€¡•­Ì¹É•ÅÕ¥É” ‰±½‰…°¹M±½Ñ!UQ•ÉÍ•‘¥„ˆ¥¸Í½ÕÉ”°€‰Á½½°M±½Ñ!UQ•ÉÍ•‘¥„…ÍÍ•¹Ñ”ˆ¤(€€€¡•­Ì¹É•ÅÕ¥É” ‰±½‰…°¹M±½Ñ!UA•µ…¥¸ˆ¥¸Í½ÕÉ”°€‰É•¥ÍÑÉ¼Á…É…±±•±¼M±½Ñ!UA•µ…¥¸…ÍÍ•¹Ñ”ˆ¤(€€€¡•­Ì¹É•ÅÕ¥É” ‰±½‰…°¹9½µ½ÉUÉÕÐˆ¹½Ð¥¸Í½ÕÉ”°€‰½¹Ñ…Ñ½É”!U9½µ½ÉUÉÕÐ¹½¸ƒ ÍÑ…Ñ¼É¥µ½ÍÍ¼ˆ¤(€€€ÑÉäè(€€€€€€€Í±½ÑÌ€ômÉ”¹ÍÕˆ¡È‰qÌ¬ˆ°€ˆˆ°¥Ñ•´¤™½È¥Ñ•´¥¸Ñ½Á}±•Ù•±}¥Ñ•µÌ¡…ÉÉ…å}‰½‘ä¡Í½ÕÉ”°€‰±½‰…°¹M±½Ñ!UQ•ÉÍ•‘¥„ˆ¤¥t(€€€•á•ÁÐA…ÉÍ•ÉÉ½Èè(€€€€€€€Í±½ÑÌ€ômt(€€€¡•­Ì¹•ÅÕ…°¡±•¸¡Í±½ÑÌ¤°€ÄÈ°€‰Í±½Ð!UÁÉ•…±±½…Ñ¤ˆ¤(€€€¡•­Ì¹•ÅÕ…°¡Í±½ÑÌ°mÍÑÈ¡¥¹‘•à¤™½È¥¹‘•à¥¸É…¹” ÄÈ¥t°€‰Á½½°¥¹¥é¥…±”‘•±¤Í±½Ð!U€À¸¸ÄÄˆ¤(€€€¡•­Ì¹É•ÅÕ¥É” (€€€€€€€€‰Ù•¹ÐA±…å•È¹UÉÕÑ…¹!U€ô¥ÉÍÐ=˜¡±½‰…°¹M±½Ñ!UQ•ÉÍ•‘¥„¤ìˆ¥¸Í½ÕÉ”(€€€€€€€…¹€‰5½‘¥™ä±½‰…°Y…É¥…‰±”¡M±½Ñ!UQ•ÉÍ•‘¥„°I•µ½Ù”É½´ÉÉ…ä	ä%¹‘•à°€À¤ìˆ¥¸Í½ÕÉ”°(€€€€€€€€‰…±±½…é¥½¹”‘•°ÁÉ¥µ¼Í±½Ð!U±¥‰•É¼…ÍÍ•¹Ñ”¼¹½¸…Ñ½µ¥„ˆ°(€€€€¤((€€€±•…Ù•}ÉÕ±•Ì€ômÉÕ±”™½ÈÉÕ±”¥¸ÉÕ±•Ì¥˜€‰A±…å•È1•™Ð5…Ñ ìˆ¥¸ÉÕ±”¹‰½‘åt(€€€¡•­Ì¹•ÅÕ…°¡±•¸¡±•…Ù•}ÉÕ±•Ì¤°€Ä°€‰É•½±”A±…å•È1•™Ð5…Ñ ˆ¤(€€€¥˜±•…Ù•}ÉÕ±•Ìè(€€€€€€€±•…Ù”€ô±•…Ù•}ÉÕ±•ÍlÁt¹‰½‘ä(€€€€€€€¡•­Ì¹É•ÅÕ¥É” (€€€€€€€€€€€±•…Ù”¹™¥¹ ‰±½‰…°¹A•µ…¥¹A•µ‰•ÉÍ¥¡…¸€ôÙ•¹ÐA±…å•Èìˆ¤(€€€€€€€€€€€€ð±•…Ù”¹™¥¹ ‰±½‰…°¹%¹‘•­Í-•±Õ…È€ô%¹‘•à=˜ÉÉ…äY…±Õ”¡±½‰…°¹A•µ…¥¹5…¹ÕÍ¥„°Ù•¹ÐA±…å•È¤ìˆ¤°(€€€€€€€€€€€€‰±•…¹ÕÀÕÍ¥Ñ„¹½¸…ÑÑÕÉ„ÍÕ‰¥Ñ¼°¥‘•¹Ñ¥Ó€‘•°¥½…Ñ½É”ˆ°(€€€€€€€€¤(€€€€€€€É•µ½Ù…±}…Ð€ô±•…Ù”¹™¥¹ ‰5½‘¥™ä±½‰…°Y…É¥…‰±”¡A•µ…¥¹5…¹ÕÍ¥„°I•µ½Ù”É½´ÉÉ…ä	ä%¹‘•àˆ¤(€€€€€€€¡•­Ì¹É•ÅÕ¥É”¡É•µ½Ù…±}…Ð€øô€À°€‰±•…¹ÕÀÕÍ¥Ñ„¹½¸É¥µÕ½Ù”¥°¥½…Ñ½É”‘…°É½ÍÑ•Èˆ¤(€€€€€€€¥˜É•µ½Ù…±}…Ð€øô€Àè(€€€€€€€€€€€¡•­Ì¹É•ÅÕ¥É” (€€€€€€€€€€€€€€€€‰Ù•¹ÐA±…å•È¸ˆ¹½Ð¥¸±•…Ù•mÉ•µ½Ù…±}…Ðét°(€€€€€€€€€€€€€€€€‰±•…¹ÕÀÕÍ¥Ñ„±•”Ù…É¥…‰¥±¤‘•±°•¹Ñ¥Ó€‘½Á¼…Ù•É±„É¥µ½ÍÍ„‘…°É½ÍÑ•Èˆ°(€€€€€€€€€€€€¤(€€€€€€€™½È½±±•Ñ¥½¸¥¸€ (€€€€€€€€€€€€‰A•µ…¥¹5…¹ÕÍ¥„ˆ°€‰!Õ‘-¥É¥A•µ…¥¸ˆ°€‰!Õ‘-…¹…¹A•µ…¥¸ˆ°€‰!Õ‘5•¹ÕA•µ…¥¸ˆ°(€€€€€€€€€€€€‰Q•­ÍÕ¹¥…A•µ…¥¸ˆ°€‰Q•­Í¥É¥A•µ…¥¸ˆ°€‰M±½Ñ!UA•µ…¥¸ˆ°(€€€€€€€€¤è(€€€€€€€€€€€¡•­Ì¹É•ÅÕ¥É” (€€€€€€€€€€€€€€€É”¹Í•…É  (€€€€€€€€€€€€€€€€€€€É˜‰5½‘¥™ä±½‰…°Y…É¥…‰±•qÌ©p¡qÌ©í½±±•Ñ¥½¹õqÌ¨±qÌ©I•µ½Ù”É½´ÉÉ…ä	ä%¹‘•àˆ°(€€€€€€€€€€€€€€€€€€€±•…Ù”°(€€€€€€€€€€€€€€€€¤(€€€€€€€€€€€€€€€¥Ì¹½Ð9½¹”°(€€€€€€€€€€€€€€€˜‰±•…¹ÕÀÕÍ¥Ñ„¹½¸…±±¥¹•…Ñ¼Á•È±½‰…°¹í½±±•Ñ¥½¹ôˆ°(€€€€€€€€€€€€¤(€€€€€€€¡•­Ì¹É•ÅÕ¥É” (€€€€€€€€€€€€‰M½ÉÑ•ÉÉ…ä¡ÁÁ•¹Q¼ÉÉ…ä¡±½‰…°¹M±½Ñ!UQ•ÉÍ•‘¥„°±½‰…°¹M±½Ñ!UA•µ…¥¹m±½‰…°¹%¹‘•­Í-•±Õ…Ét¤ˆ(€€€€€€€€€€€¥¸±•…Ù”°(€€€€€€€€€€€€‰±•…¹ÕÀÕÍ¥Ñ„¹½¸±¥‰•É„±¼Í±½Ð!Uˆ°(€€€€€€€€¤(€€€€€€€¡•­Ì¹É•ÅÕ¥É” ‰½È±½‰…°Y…É¥…‰±”ˆ¥¸±•…Ù”°€‰±•…¹ÕÀÕÍ¥Ñ„¹½¸Ù¥Í¥Ñ„ÑÕÑÑ¤¤ÍÕÁ•ÉÍÑ¥Ñ¤ˆ¤(€€€€€€€¡•­Ì¹É•ÅÕ¥É” ‰	…±…Í•¹‘…´ˆ¥¸±•…Ù”°€‰±•…¹ÕÀÕÍ¥Ñ„¹½¸É¥ÁÕ±¥Í”¤±•‘•È	…±…Í•¹‘…´ˆ¤(€€€€€€€¡•­Ì¹É•ÅÕ¥É” (€€€€€€€€€€€…±°¡¹…µ”¥¸±•…Ù”™½È¹…µ”¥¸€ (€€€€€€€€€€€€€€€€‰Q¥Ñ¥­)…¹­…É-…µ•É„ˆ°€‰Q¥Ñ¥­%‘•…±-…µ•É„ˆ°€‰Q¥Ñ¥­	•¹ÑÕÉ…¹-…µ•É„ˆ°€‰Q¥Ñ¥­­¡¥É-…µ•É„ˆ°(€€€€€€€€€€€€€€€€‰É…¡5•¹‘…Ñ…É-…µ•É„ˆ°€‰A½Í¥Í¥I•±…Ñ¥™-…µ•É„ˆ°(€€€€€€€€€€€€¤¤°(€€€€€€€€€€€€‰±•…¹ÕÀÕÍ¥Ñ„¹½¸¥¹Ù…±¥‘„ÑÕÑÑ”±”…¡”…µ•É„‘•¤Ù¥•Ý•Èˆ°(€€€€€€€€¤(€€€€€€€¡•­Ì¹É•ÅÕ¥É” ‰MÑ½À…µ•É„ˆ¥¸±•…Ù”°€‰±•…¹ÕÀÕÍ¥Ñ„¹½¸™•Éµ„±”…µ•É”ÁÕ¹Ñ…Ñ”…±°ÕÍ•¹Ñ”ˆ¤((€€€™½È¹…µ”¥¸€ ‰Q…É•Ñ	…±…Í•¹‘…µ¥Á¥±¥ ˆ°€‰Q…É•Ñ	…±…Í•¹‘…µQ•É­Õ¹¤ˆ¤è(€€€€€€€¡•­Ì¹É•ÅÕ¥É”¡˜‰Ù•¹ÐA±…å•È¹í¹…µ•ôˆ¥¸Í½ÕÉ”°˜‰I•Ù•¹”èÙ…É¥…‰¥±”í¹…µ•ô…ÍÍ•¹Ñ”ˆ¤(€€€±…¥µ}ÉÕ±•Ì€ôÉÕ±•Í}½¹Ñ…¥¹¥¹œ¡ÉÕ±•Ì°€‰Q…É•Ñ	…±…Í•¹‘…µQ•É­Õ¹¤ˆ°€‰-¥±° ˆ¤(€€€¡•­Ì¹•ÅÕ…°¡±•¸¡±…¥µ}ÉÕ±•Ì¤°€Ä°€‰É•½±”±…¥´	…±…Í•¹‘…´½¸Ñ…É•Ð…ÑÑÕÉ…Ñ¼ˆ¤(€€€¥˜±…¥µ}ÉÕ±•Ìè(€€€€€€€±…¥´€ô±…¥µ}ÉÕ±•ÍlÁt¹‰½‘ä(€€€€€€€…ÁÑÕÉ•}µ…Ñ €ôÉ”¹Í•…É  (€€€€€€€€€€€È‰Ù•¹ÐA±…å•Ép¹Q…É•Ñ	…±…Í•¹‘…µQ•É­Õ¹¥qÌ¨õqÌ©Ù•¹ÐA±…å•Ép¹…™Ñ…ÉQ…É•Ñ	…±…Í•¹‘…µqÌ©qmqÌ©Ù•¹ÐA±…å•Ép¹-ÕÉÍ½É	…±…Í•¹‘…µqÌ©quqÌ¨ìˆ°(€€€€€€€€€€€±…¥´°(€€€€€€€€¤(€€€€€€€…ÁÑÕÉ”€ô€´Ä¥˜…ÁÑÕÉ•}µ…Ñ ¥Ì9½¹”•±Í”…ÁÑÕÉ•}µ…Ñ ¹ÍÑ…ÉÐ ¤(€€€€€€€­¥±±}…Ð€ô±…¥´¹™¥¹ ‰-¥±°¡Ù•¹ÐA±…å•È¹Q…É•Ñ	…±…Í•¹‘…µQ•É­Õ¹¤°Ù•¹ÐA±…å•È¤ìˆ¤(€€€€€€€¡•­Ì¹É•ÅÕ¥É” À€ðô…ÁÑÕÉ”€ð­¥±±}…Ð°€‰Ñ…É•Ð	…±…Í•¹‘…´¹½¸…ÑÑÕÉ…Ñ¼Á•È¥‘•¹Ñ¥Ó€ÁÉ¥µ„‘•°±…¥´ˆ¤(€€€€€€€Ý…¥Ñ}…Ð€ô±…¥´¹™¥¹ ‰]…¥Ð ˆ°…ÁÑÕÉ”€¬€Ä¤(€€€€€€€¥˜Ý…¥Ñ}…Ð€øô€Àè(€€€€€€€€€€€…™Ñ•É}Ý…¥Ð€ô±…¥µmÝ…¥Ñ}…Ðét(€€€€€€€€€€€¡•­Ì¹É•ÅÕ¥É” (€€€€€€€€€€€€€€€€‰Q…É•Ñ	…±…Í•¹‘…µQ•É­Õ¹¤ˆ¥¸…™Ñ•É}Ý…¥Ð°(€€€€€€€€€€€€€€€€‰±…¥´	…±…Í•¹‘…´¹½¸ÕÍ„¥°É¥™•É¥µ•¹Ñ¼…ÑÑÕÉ…Ñ¼‘½Á¼¥°]…¥Ðˆ°(€€€€€€€€€€€€¤(€€€€€€€€€€€¡•­Ì¹É•ÅÕ¥É” (€€€€€€€€€€€€€€€€‰Q…É•Ñ	…±…Í•¹‘…µ¥Á¥±¥ ˆ¹½Ð¥¸…™Ñ•É}Ý…¥Ð°(€€€€€€€€€€€€€€€€‰±…¥´	…±…Í•¹‘…´‘¥Á•¹‘”…¹½É„‘…±±„Í•±•é¥½¹”µÕÑ•Ù½±”‘½Á¼¥°]…¥Ðˆ°(€€€€€€€€€€€€¤(€€€É•™É•Í¡}ÉÕ±•Ì€ôÉÕ±•Í}½¹Ñ…¥¹¥¹œ (€€€€€€€ÉÕ±•Ì°€‰Ù•¹ÐA±…å•È¹Q…É•Ñ	…±…Í•¹‘…µ¥Á¥±¥ ˆ°€‰Ù•¹ÐA±…å•È¹…™Ñ…ÉQ…É•Ñ	…±…Í•¹‘…´€ô¥±Ñ•É•ÉÉ…äˆ(€€€€¤(€€€¡•­Ì¹•ÅÕ…°¡±•¸¡É•™É•Í¡}ÉÕ±•Ì¤°€Ä°€‰É•™É•Í 	…±…Í•¹‘…´¡”ÁÉ•Í•ÉÙ„¥°Ñ…É•ÐÁ•È¥‘•¹Ñ¥Ó€ˆ¤((€€€‘•…Ñ¡}ÉÕ±•Ì€ômÉÕ±”™½ÈÉÕ±”¥¸ÉÕ±•Ì¥˜€‰A±…å•È¥•ìˆ¥¸ÉÕ±”¹‰½‘åt(€€€¡•­Ì¹É•ÅÕ¥É”¡‰½½°¡‘•…Ñ¡}ÉÕ±•Ì¤°€‰É•½±„A±…å•È¥•Á•È	…±…Í•¹‘…´…ÍÍ•¹Ñ”ˆ¤(€€€¥˜‘•…Ñ¡}ÉÕ±•Ìè(€€€€€€€‘•…Ñ €ô€‰q¸ˆ¹©½¥¸¡ÉÕ±”¹‰½‘ä™½ÈÉÕ±”¥¸‘•…Ñ¡}ÉÕ±•Ì¤(€€€€€€€¡•­Ì¹É•ÅÕ¥É” (€€€€€€€€€€€É”¹Í•…É ¡È‰Ù•¹ÐA±…å•Ép¹mµi„µèÀ´å}t©	…±…Í•¹‘…µmµi„µèÀ´å}t©qÌ¨õqÌ©…±Í•qÌ¨ìˆ°‘•…Ñ ¤(€€€€€€€€€€€¥Ì¹½Ð9½¹”°(€€€€€€€€€€€€‰A±…å•È¥•¹½¸…éé•É„¥°™±…œ‘•±±„µ½ÉÑ”	…±…Í•¹‘…´ˆ°(€€€€€€€€¤(()‘•˜¡•­}‘¥…¹½ÍÑ¥Ì¡¡•­Ìè¡•­Ì°Í½ÕÉ”èÍÑÈ°ÉÕ±•Ìè±¥ÍÑmIÕ±•t¤€´ø9½¹”è(€€€Ñ½±”€ôÉ”¹Í•…É  (€€€€€€€È‰±½‰…±p¹¥…¹½ÍÑ¥­A•É™½Éµ…qÌ¨õqÌ©]½É­Í¡½ÀM•ÑÑ¥¹œQ½±•qÌ©p  ¸¨ü¥p¥qÌ¨ìˆ°(€€€€€€€Í½ÕÉ”°(€€€€€€€É”¹=Q10°(€€€€¤(€€€¡•­Ì¹É•ÅÕ¥É”¡Ñ½±”¥Ì¹½Ð9½¹”°€‰Ñ½±”A•É™½Éµ…¹”‘¥…¹½ÍÑ¥Ì…ÍÍ•¹Ñ”ˆ¤(€€€¥˜Ñ½±”¥Ì¹½Ð9½¹”è(€€€€€€€…ÉÕµ•¹ÑÌ€ôÑ½Á}±•Ù•±}¥Ñ•µÌ¡Ñ½±”¹É½ÕÀ Ä¤¤(€€€€€€€¡•­Ì¹É•ÅÕ¥É” (€€€€€€€€€€€±•¸¡…ÉÕµ•¹ÑÌ¤€øô€Ì…¹…ÉÕµ•¹ÑÍlÉt¹ÍÑÉ¥À ¤€ôô€‰…±Í”ˆ°(€€€€€€€€€€€€‰A•É™½Éµ…¹”‘¥…¹½ÍÑ¥Ì‘•Ù”•ÍÍ•É”=Á•È¥µÁ½ÍÑ…é¥½¹”ÁÉ•‘•™¥¹¥Ñ„ˆ°(€€€€€€€€¤(€€€™½Èµ•ÑÉ¥Œ¥¸€ ‰M•ÉÙ•È1½…ˆ°€‰M•ÉÙ•È1½…Ù•É…”ˆ°€‰M•ÉÙ•È1½…A•…¬ˆ¤è(€€€€€€€¡•­Ì¹É•ÅÕ¥É”¡µ•ÑÉ¥Œ¥¸Í½ÕÉ”°˜‰‘¥…¹½ÍÑ¥„ÁÉ¥Ù„‘¤íµ•ÑÉ¥ôˆ¤(€€€‘¥…¹½ÍÑ¥}ÉÕ±•Ì€ôl(€€€€€€€ÉÕ±”™½ÈÉÕ±”¥¸ÉÕ±•Ì(€€€€€€€¥˜€‰¥…¹½ÍÑ¥­A•É™½Éµ„ˆ¥¸ÉÕ±”¹‰½‘ä…¹€‰M•ÉÙ•È1½…ˆ¥¸ÉÕ±”¹‰½‘ä(€€€t(€€€¡•­Ì¹É•ÅÕ¥É”¡‰½½°¡‘¥…¹½ÍÑ¥}ÉÕ±•Ì¤°€‰É•½±„!U‘¥…¹½ÍÑ¥„¹½¸ÑÉ½Ù…Ñ„ˆ¤(€€€¥˜‘¥…¹½ÍÑ¥}ÉÕ±•Ìè(€€€€€€€‘¥…¹½ÍÑ¥Œ€ô€‰q¸ˆ¹©½¥¸¡ÉÕ±”¹‰½‘ä™½ÈÉÕ±”¥¸‘¥…¹½ÍÑ¥}ÉÕ±•Ì¤(€€€€€€€¡•­Ì¹É•ÅÕ¥É” ‰!½ÍÐA±…å•Èˆ¥¸‘¥…¹½ÍÑ¥Œ°€‰‘¥…¹½ÍÑ¥„¹½¸±¥µ¥Ñ…Ñ„…±°¡½ÍÐˆ¤(€€€€€€€¡•­Ì¹É•ÅÕ¥É” (€€€€€€€€€€€€ (€€€€€€€€€€€€€€€€ (€€€€€€€€€€€€€€€€€€€€‰!Õ‘-¥É¥A•µ…¥¸ˆ¥¸‘¥…¹½ÍÑ¥Œ(€€€€€€€€€€€€€€€€€€€…¹€ ‰!Õ‘-…¹…¹A•µ…¥¸ˆ¥¸‘¥…¹½ÍÑ¥Œ½ÈÉ”¹Í•…É ¡È‰½Õ¹Ð=™p¡±½‰…±p¹!Õ‘-¥É¥A•µ…¥¹p¥qÌ©p©qÌ¨Èˆ°‘¥…¹½ÍÑ¥Œ¤¤(€€€€€€€€€€€€€€€€¤(€€€€€€€€€€€€€€€…¹…±°¡Ñ½­•¸¥¸‘¥…¹½ÍÑ¥Œ™½ÈÑ½­•¸¥¸€ ‰!Õ‘5•¹ÕA•µ…¥¸ˆ°€‰Q•­ÍÕ¹¥…A•µ…¥¸ˆ°€‰Q•­Í¥É¥A•µ…¥¸ˆ¤¤(€€€€€€€€€€€€¤°(€€€€€€€€€€€€‰‘¥…¹½ÍÑ¥„ÁÉ¥Ù„‘•¤½¹Ñ•¤!U½%]Pˆ°(€€€€€€€€¤(€€€¥¹ÍÁ•Ñ½É}ÉÕ±•Ì€ôÉÕ±•Í}½¹Ñ…¥¹¥¹œ (€€€€€€€ÉÕ±•Ì°€‰±½‰…°¹¥…¹½ÍÑ¥­A•É™½Éµ„€ôô…±Í”ˆ°€‰¥Í…‰±”%¹ÍÁ•Ñ½ÈI•½É‘¥¹œìˆ(€€€€¤(€€€¡•­Ì¹•ÅÕ…°¡±•¸¡¥¹ÍÁ•Ñ½É}ÉÕ±•Ì¤°€Ä°€‰‘¥Í…‰¥±¥Ñ…é¥½¹”%¹ÍÁ•Ñ½ÈÅÕ…¹‘¼±„‘¥…¹½ÍÑ¥„ƒ =ˆ¤(()‘•˜¡•­}‘½Õµ•¹Ñ…Ñ¥½¹}…¹‘}¤¡¡•­Ìè¡•­Ì°•¹É•Ìè±¥ÍÑmÍÑÉt¤€´ø9½¹”è(€€€¡•­Ì¹É•ÅÕ¥É”¡YIM%=8¹•á¥ÍÑÌ ¤°˜‰™¥±”YIM%=8µ…¹…¹Ñ”èíYIM%=9ôˆ¤(€€€¥˜YIM%=8¹•á¥ÍÑÌ ¤è(€€€€€€€¡•­Ì¹•ÅÕ…°¡YIM%=8¹É•…‘}Ñ•áÐ¡•¹½‘¥¹œô‰ÕÑ˜´àˆ¤¹ÍÑÉ¥À ¤°€ˆÀ¸Ô¸Èˆ°€‰Ù•ÉÍ¥½¹”ÁÉ½•ÑÑ¼ˆ¤((€€€¡•­Ì¹É•ÅÕ¥É”¡9I}=¹•á¥ÍÑÌ ¤°˜‰‘½Õµ•¹Ñ…é¥½¹”•¹•É¤µ…¹…¹Ñ”èí9I}=ôˆ¤(€€€¥˜9I}=¹•á¥ÍÑÌ ¤è(€€€€€€€‘½Õµ•¹Ñ•€ôÉ”¹™¥¹‘…±° (€€€€€€€€€€€È‰yq­p¸€ ¸¬¤ˆ°9I}=¹É•…‘}Ñ•áÐ¡•¹½‘¥¹œô‰ÕÑ˜´àˆ¤°™±…ÌõÉ”¹5U1Q%1%9(€€€€€€€€¤(€€€€€€€¡•­Ì¹•ÅÕ…°¡‘½Õµ•¹Ñ•°•¹É•Ì°€‰‘½Ì½9I$¹µÉ¥ÍÁ•ÑÑ¼„…™Ñ…É•¹É”ˆ¤((€€€™½È±•…ä¥¸1e}UQ=5Q%=8è(€€€€€€€¡•­Ì¹É•ÅÕ¥É”¡¹½Ð±•…ä¹•á¥ÍÑÌ ¤°˜‰…ÕÑ½µ…é¥½¹”…ÕÑ¼µµ½‘¥™¥…¹Ñ”±•…ä…¹½É„ÁÉ•Í•¹Ñ”èí±•…ä¹É•±…Ñ¥Ù•}Ñ¼¡I==P¥ôˆ¤(€€€¡•­Ì¹É•ÅÕ¥É”¡]=I-1=\¹•á¥ÍÑÌ ¤°˜‰Ý½É­™±½ÜÉ•…µ½¹±äµ…¹…¹Ñ”èí]=I-1=\¹É•±…Ñ¥Ù•}Ñ¼¡I==P¥ôˆ¤(€€€¥˜]=I-1=\¹•á¥ÍÑÌ ¤è(€€€€€€€Ý½É­™±½Ü€ô]=I-1=\¹É•…‘}Ñ•áÐ¡•¹½‘¥¹œô‰ÕÑ˜´àˆ¤(€€€€€€€¡•­Ì¹É•ÅÕ¥É” (€€€€€€€€€€€É”¹Í•…É ¡Èˆ ý´¥yÁ•Éµ¥ÍÍ¥½¹ÌéqÌ©q¹qÌ­½¹Ñ•¹ÑÌéqÌ©É•…‘qÌ¨ˆ°Ý½É­™±½Ü¤¥Ì¹½Ð9½¹”°(€€€€€€€€€€€€‰Ý½É­™±½ÜÍ•¹é„Á•Éµ¥ÍÍ¥½¹Ì¹½¹Ñ•¹ÑÌèÉ•…ˆ°(€€€€€€€€¤(€€€€€€€™½É‰¥‘‘•¸€ô€ ‰½¹Ñ•¹ÑÌèÝÉ¥Ñ”ˆ°€‰¥ÐÁÕÍ ˆ°€‰¥Ð½µµ¥Ðˆ°€‰À¹ÝÉ¥Ñ•}Ñ•áÐˆ°€‰…ÁÁ±å}Á…Ñ ˆ¤(€€€€€€€™½ÈÑ½­•¸¥¸™½É‰¥‘‘•¸è(€€€€€€€€€€€¡•­Ì¹É•ÅÕ¥É”¡Ñ½­•¸¹½Ð¥¸Ý½É­™±½Ü°˜‰Ý½É­™±½Ü¹½¸É•…µ½¹±äèÑÉ½Ù…Ñ¼íÑ½­•¸…Éôˆ¤(€€€€€€€¡•­Ì¹É•ÅÕ¥É” (€€€€€€€€€€€€‰ÁåÑ¡½¸Ñ½½±Ì½Ù…±¥‘…Ñ•}Ý½É­Í¡½À¹Áäˆ¥¸Ý½É­™±½Ü°(€€€€€€€€€€€€‰Ý½É­™±½Ü¹½¸•Í•Õ”Ñ½½±Ì½Ù…±¥‘…Ñ•}Ý½É­Í¡½À¹Áäˆ°(€€€€€€€€¤(()‘•˜µ…¥¸ ¤€´ø9½¹”è(€€€¡•­Ì€ô¡•­Ì ¤(€€€¥˜¹½ÐM=UI¹•á¥ÍÑÌ ¤è(€€€€€€€¡•­Ì¹É•ÅÕ¥É”¡…±Í”°˜‰Í½É•¹Ñ”µ…¹…¹Ñ”èíM=UIôˆ¤(€€€€€€€¡•­Ì¹™¥¹¥Í  ¤(€€€Í½ÕÉ”€ôM=UI¹É•…‘}Ñ•áÐ¡•¹½‘¥¹œô‰ÕÑ˜´àˆ¤(€€€™½È•ÉÉ½È¥¸‰…±…¹•‘}•ÉÉ½ÉÌ¡Í½ÕÉ”¤è(€€€€€€€¡•­Ì¹É•ÅÕ¥É”¡…±Í”°•ÉÉ½È¤((€€€ÑÉäè(€€€€€€€±½‰…±}¹…µ•Ì°Á±…å•É}¹…µ•Ì°ÍÕ‰É½ÕÑ¥¹•Ì€ô‘•±…É…Ñ¥½¹}Ñ…‰±•Ì¡Í½ÕÉ”¤(€€€€€€€•¹É•Ì°ÉÕ±•Ì€ô¡•­}±…¹Õ…•}…ÉÉ…åÌ¡¡•­Ì°Í½ÕÉ”¤(€€€€€€€¡•­}Í½ÕÉ•}ÍÑÉÕÑÕÉ”¡¡•­Ì°Í½ÕÉ”°ÉÕ±•Ì°±½‰…±}¹…µ•Ì°Á±…å•É}¹…µ•Ì°ÍÕ‰É½ÕÑ¥¹•Ì¤(€€€€€€€¡•­}Ñ¥µ•É}…¹‘}µ…Ñ ¡¡•­Ì°Í½ÕÉ”°ÉÕ±•Ì¤(€€€€€€€¡•­}‰½Ñ}±¥™•å±”¡¡•­Ì°Í½ÕÉ”°ÉÕ±•Ì¤(€€€€€€€¡•­}µ•¹ÕÌ¡¡•­Ì°Í½ÕÉ”°ÉÕ±•Ì°ÍÕ‰É½ÕÑ¥¹•Ì¤(€€€€€€€¡•­}…µ•É„¡¡•­Ì°Í½ÕÉ”°ÉÕ±•Ì°Á±…å•É}¹…µ•Ì¤(€€€€€€€¡•­}É½Õ ¡¡•­Ì°Í½ÕÉ”°ÉÕ±•Ì¤(€€€€€€€¡•­}±•…¹ÕÁ}…¹‘}É•Ù•¹”¡¡•­Ì°Í½ÕÉ”°ÉÕ±•Ì¤(€€€€€€€¡•­}‘¥…¹½ÍÑ¥Ì¡¡•­Ì°Í½ÕÉ”°ÉÕ±•Ì¤(€€€€€€€¡•­}‘½Õµ•¹Ñ…Ñ¥½¹}…¹‘}¤¡¡•­Ì°•¹É•Ì¤(€€€•á•ÁÐA…ÉÍ•ÉÉ½È…Ì•áŒè(€€€€€€€¡•­Ì¹É•ÅÕ¥É”¡…±Í”°˜‰Á…ÉÍ¥¹œ¥¹Ñ•ÉÉ½ÑÑ¼èí•áôˆ¤((€€€¡•­Ì¹™¥¹¥Í  ¤(€€€ÁÉ¥¹Ð ‰=,€´½¹ÑÉ½±±¤ÍÑ…Ñ¥¤ØÀ¸Ô¸ÈÍÕÁ•É…Ñ¤ˆ¤(€€€ÁÉ¥¹Ð (€€€€€€€˜‰•¹•É¤èí±•¸¡•¹É•Ì¥ôð1¥¹Õ”è€ÌðI•½±”èí±•¸¡ÉÕ±•Ì¥ôð€ˆ(€€€€€€€˜‰I…å…ÍÐ…µ•É„èí±•¸¡…±±}Ñ•áÑÌ¡Í½ÕÉ”°€I…ä…ÍÐ!¥ÐA½Í¥Ñ¥½¸œ¤¥ôˆ(€€€€¤(€€€ÁÉ¥¹Ð ‰9½Ñ„è¥µÁ½ÉÑ…é¥½¹”°ÍÑÉ•ÍÌ„€ÄÈ¥½…Ñ½É¤”Ñ•ÍÐµ½‘…±¥Ó€É•ÍÑ…¹¼ÁÉ½Ù”±¥Ù”½‰‰±¥…Ñ½É¥”¸ˆ¤(()¥˜}}¹…µ•}|€ôô€‰}}µ…¥¹}|ˆè(€€€µ…¥¸ ¤(