#!/usr/bin/env python3
"""Static preflight for Workshop text copied into Overwatch.

Overwatch's Workshop clipboard grammar is localized. The user-facing project
source is the it-IT Workshop file; the en-US profile is retained only for the
internal semantic fixture and regression tests. This checker validates either
profile without pretending to reproduce the client's compiled Element Count or
Largest Rule metrics.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import argparse
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "workshop" / "ruang_irama.it-IT.workshop"
ITALIAN_SOURCE = ROOT / "workshop" / "ruang_irama.it-IT.workshop"
SEMANTIC_REFERENCE = ROOT / "tests" / "fixtures" / "semantic_reference.txt"

CLIENT_LARGEST_RULE_LIMIT_BYTES = 98_000
CLIENT_ELEMENT_LIMIT = 32_768
SOURCE_RULE_SAFETY_TARGET_BYTES = 80_000
# Offline guardrails, not measurements or limits of the client's compiler.
# The total budget is deliberately below the client element limit; unknown
# compiler details still require native verification. The per-rule budget is
# an independent complexity ceiling, not a conversion to bytes.
SOURCE_TOTAL_STRUCTURAL_TARGET = 32_000
SOURCE_RULE_STRUCTURAL_TARGET = 5_000


@dataclass(frozen=True)
class LanguageProfile:
    variables: str
    subroutines: str
    rule: str
    event: str
    conditions: str
    actions: str


LANGUAGE_PROFILES: dict[str, LanguageProfile] = {
    "en-US": LanguageProfile(
        variables="variables",
        subroutines="subroutines",
        rule="rule",
        event="event",
        conditions="conditions",
        actions="actions",
    ),
    "it-IT": LanguageProfile(
        variables="variabili",
        subroutines="subroutine",
        rule="regola",
        event="evento",
        conditions="condizioni",
        actions="azioni",
    ),
}

FORBIDDEN_OUTSIDE_STRINGS = {
    "\ufeff": "BOM UTF-8",
    "\u00a0": "spazio non separabile (NBSP)",
    "“": "virgolette tipografiche aperte",
    "”": "virgolette tipografiche chiuse",
    "‘": "apostrofo tipografico aperto",
    "’": "apostrofo tipografico chiuso",
}

# The Workshop clipboard grammar localizes only these tokens between the
# maintained en-US semantic fixture and the user-facing it-IT source. Runtime
# strings (including rule titles and Workshop comments) are deliberately not
# translated here: the semantic gate compares them byte-for-byte.
ITALIAN_TO_ENGLISH_TOKENS: tuple[tuple[str, str], ...] = (
    ("Regina dei Junker", "Junker Queen"),
    ("Cattura la Bandiera", "Capture The Flag"),
    ("Schermaglia", "Skirmish"),
    ("Annulla quando è False", "Abort When False"),
    ("Tutti gli eroi", "All Heroes"),
    ("Ignora condizione", "Ignore Condition"),
    ("Punto Critico", "Flashpoint"),
    ("subroutine", "subroutines"),
    ("condizioni", "conditions"),
    ("variabili", "variables"),
    ("giocatore", "player"),
    ("Trasporto", "Escort"),
    ("Conquista", "Assault"),
    ("Globale", "Global"),
    ("globale", "global"),
    ("Scorta", "Push"),
    ("Controllo", "Control"),
    ("Scontro", "Clash"),
    ("Ibrida", "Hybrid"),
    ("regola", "rule"),
    ("evento", "event"),
    ("azioni", "actions"),
    ("Tutti", "All"),
    ("Bianco", "White"),
    ("Grigio", "Gray"),
)

FORBIDDEN_ENGLISH_IN_ITALIAN_SYNTAX: tuple[tuple[str, str], ...] = (
    (r"\bHero\s*\(\s*Junker\s+Queen\s*\)", "eroe Junker Queen en-US"),
    (r"(?m)^\s*(?:global|player)\s*:\s*$", "namespace global/player en-US"),
    (r"(?m)^\s*All\s*;\s*$", "selettore All en-US"),
    (r"\bGlobal\s*\.", "namespace Global en-US"),
    (r"\bAll\s+Heroes\b", "selettore All Heroes en-US"),
    (r"\bAbort\s+When\s+False\b", "policy Abort When False en-US"),
    (r"\bIgnore\s+Condition\b", "policy Ignore Condition en-US"),
    (
        r"\bColor\s*\(\s*(?:White|Gray)\s*\)",
        "colore nominale Color(...) en-US",
    ),
    (
        r"\bGame\s+Mode\s*\(\s*(?:Skirmish|Push|Flashpoint|Capture\s+The\s+Flag|Control|Clash|Hybrid|Escort|Assault)\s*\)",
        "modalità Game Mode en-US",
    ),
)

EQUIVALENT_NAMED_COLORS: tuple[tuple[tuple[int, int, int, int], str], ...] = (
    ((255, 255, 255, 255), "White"),
    ((255, 255, 0, 255), "Yellow"),
    ((236, 153, 0, 255), "Orange"),
    ((255, 50, 145, 255), "Rose"),
    ((100, 50, 255, 255), "Violet"),
    ((108, 190, 244, 255), "Sky Blue"),
    ((0, 234, 234, 255), "Aqua"),
    ((0, 230, 151, 255), "Turquoise"),
    ((160, 232, 27, 255), "Lime Green"),
)


@dataclass(frozen=True)
class RuleSize:
    name: str
    bytes_utf8: int
    structural_units: int = 0


@dataclass(frozen=True)
class Report:
    language: str
    source_bytes_utf8: int
    rule_count: int
    largest_rule: RuleSize
    structural_units: int
    largest_structural_rule: RuleSize


class ClipboardImportError(ValueError):
    pass


class _StructuralExpression:
    """Count syntax nodes without evaluating code or importing test helpers.

    These are weighted source AST nodes, not an exact native Element Count.
    Node weights follow the public OverPy emitter's treatment of numbers,
    variable references, comparisons, arrays, Evaluate Once and top-level action
    discounts. Known String/Custom String placeholders are included even when
    omitted from the clipboard, as in OverPy's four-argument string nodes.
    Other implicit defaults, hero/model overhead and compiler transforms are
    not modeled. This metric detects expression duplication
    even when shorter identifiers or rule splitting shrink the clipboard text.
    Primary reference: github.com/Zezombye/overpy/blob/master/src/compiler/astToWorkshop.ts
    """

    TOKEN = re.compile(
        r'"(?:\\.|[^"\\])*"|\d+(?:\.\d*)?(?:[eE][+-]?\d+)?'
        r'|[A-Za-z_][A-Za-z_0-9]*(?:\s+[A-Za-z_0-9]+)*'
        r'|==|!=|>=|<=|\+=|-=|\*=|/=|%=|&&|\|\||[()\[\],.?:+\-*/%<>=!]'
    )
    PRECEDENCE = {"=": 0, "+=": 0, "-=": 0, "*=": 0, "/=": 0, "%=": 0,
                  "||": 2, "&&": 3, "==": 4, "!=": 4, ">=": 4, "<=": 4,
                  ">": 4, "<": 4, "+": 5, "-": 5, "*": 6, "/": 6, "%": 6}

    def __init__(self, source: str):
        self.tokens: list[str] = []
        previous = 0
        for match in self.TOKEN.finditer(source):
            if source[previous:match.start()].strip():
                raise ClipboardImportError("sintassi non analizzabile dal budget strutturale")
            self.tokens.append(match.group(0).strip())
            previous = match.end()
        if source[previous:].strip():
            raise ClipboardImportError("sintassi non analizzabile dal budget strutturale")
        self.index = 0
        self.tree = self.parse()
        if self.index != len(self.tokens):
            raise ClipboardImportError("espressione incompleta nel budget strutturale")

    def take(self, expected: str | None = None) -> str:
        if self.index >= len(self.tokens):
            raise ClipboardImportError("espressione troncata nel budget strutturale")
        token = self.tokens[self.index]
        self.index += 1
        if expected is not None and token != expected:
            raise ClipboardImportError(f"budget strutturale: atteso {expected!r}, trovato {token!r}")
        return token

    def peek(self) -> str | None:
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def parse(self, minimum: int = 0):
        token = self.take()
        if token in ("-", "+", "!"):
            left = ("unary", token, self.parse(7))
        elif token == "(":
            left = self.parse()
            self.take(")")
        elif token.startswith('"'):
            left = ("string",)
        elif token[0].isdigit():
            left = ("number",)
        elif self.peek() == "(":
            self.take("(")
            args = []
            if self.peek() != ")":
                while True:
                    args.append(self.parse())
                    if self.peek() != ",":
                        break
                    self.take(",")
            self.take(")")
            left = ("call", re.sub(r"\s+", "", token), tuple(args))
        else:
            # The colon is part of the native Arrow icon enum, not a ternary.
            if token == "Arrow" and self.peek() == ":":
                self.take(":")
                self.take()
            left = ("name", re.sub(r"\s+", "", token))
        while True:
            if self.peek() == ".":
                self.take(".")
                left = ("member", left, self.take())
            elif self.peek() == "[":
                self.take("[")
                left = ("index", left, self.parse())
                self.take("]")
            elif self.peek() == "?" and minimum <= 1:
                self.take("?")
                yes = self.parse()
                self.take(":")
                left = ("conditional", left, yes, self.parse(1))
            elif self.peek() in self.PRECEDENCE and self.PRECEDENCE[self.peek()] >= minimum:
                operator = self.take()
                left = ("binary", operator, left, self.parse(self.PRECEDENCE[operator] + 1))
            else:
                return left

    @staticmethod
    def units(node) -> int:
        kind = node[0]
        if kind == "number":
            return 2
        if kind in ("name", "string"):
            return 1
        if kind == "member":
            owner = node[1]
            # Global/Globale are namespaces, not value nodes. Player Variable
            # includes the owner expression and its variable identifier.
            if owner[0] == "name" and owner[1] in ("Global", "Globale"):
                return 2
            return 2 + _StructuralExpression.units(owner)
        if kind == "call":
            extra = max(0, 4 - len(node[2])) if node[1] in ("String", "CustomString") else 0
            # A localized String literal counts twice in the public emitter.
            if node[1] == "String":
                extra += 1
            return extra + (2 if node[1] in ("Array", "EvaluateOnce") else 1) + sum(
                _StructuralExpression.units(arg) for arg in node[2])
        if kind == "binary":
            return (2 if node[1] in ("==", "!=", ">", "<", ">=", "<=") else 1) + sum(
                _StructuralExpression.units(arg) for arg in node[2:])
        if kind == "unary":
            return 1 + _StructuralExpression.units(node[2])
        return 1 + sum(_StructuralExpression.units(arg) for arg in node[1:])

    @staticmethod
    def statement_units(node, action: bool) -> int:
        """Account for the emitter's native statement lowering."""
        if action and node[0] == "binary" and node[1] in ("=", "+=", "-=", "*=", "/=", "%="):
            owner, rhs = node[2:]
            index_units = 0
            while owner[0] == "index":
                index_units += _StructuralExpression.units(owner[2]) - 1
                owner = owner[1]
            if owner[0] == "member":
                player = owner[1]
                owner_units = (0 if player[0] == "name" and player[1] in ("Global", "Globale")
                               else _StructuralExpression.units(player) - 1)
                return _StructuralExpression.units(rhs) + owner_units + index_units
            # Unrecognized assignment shapes retain their full syntax cost.
        result = _StructuralExpression.units(node)
        if action and node[0] == "call":
            result -= len(node[2])
        elif not action and node[0] == "binary" and node[1] in ("==", "!=", ">", "<", ">=", "<="):
            result -= 3
        return result


@lru_cache(maxsize=512)
def structural_rule_units(block: str, profile: LanguageProfile) -> int:
    """Return a stable offline script-size proxy; comments and titles cost zero."""
    total = 1  # Rule itself; native event selectors are not expression nodes.
    for keyword in (profile.conditions, profile.actions):
        masked = _mask_quoted_text(block)
        match = re.search(rf"\b{re.escape(keyword)}\s*\{{", masked)
        if match is None:
            continue
        opening = masked.find("{", match.start())
        body = block[opening + 1:_find_matching_brace(block, opening)]
        if profile == LANGUAGE_PROFILES["it-IT"]:
            segments = re.split(r'("(?:\\.|[^"\\])*")', body)
            for index in range(0, len(segments), 2):
                for original, translated in ITALIAN_TO_ENGLISH_TOKENS:
                    segments[index] = _replace_token(segments[index], original, translated)
            body = "".join(segments)
        # Workshop action comments are standalone quoted lines. A Custom
        # String argument ending with ',' or ')' cannot match this pattern.
        body = re.sub(r'(?m)^[ \t]*"(?:\\.|[^"\\])*"[ \t]*(?:\r?\n|$)', "", body)
        # A quoted semicolon remains inside its string token.
        statements = re.findall(r'(?:"(?:\\.|[^"\\])*"|[^";])+', body)
        for statement in statements:
            if statement.strip():
                try:
                    total += _StructuralExpression.statement_units(
                        _StructuralExpression(statement).tree, keyword == profile.actions)
                except (RecursionError, ClipboardImportError) as exc:
                    raise ClipboardImportError(
                        f"budget strutturale non calcolabile: {statement.strip()[:100]!r}: {exc}"
                    ) from exc
    return total


def _replace_token(segment: str, source: str, target: str) -> str:
    """Replace one localized token without touching longer identifiers."""

    phrase_pattern = re.escape(source).replace(r"\ ", r"\s+")
    if source[0].isalnum():
        phrase_pattern = rf"(?<!\w){phrase_pattern}"
    if source[-1].isalnum():
        phrase_pattern = rf"{phrase_pattern}(?!\w)"
    return re.sub(phrase_pattern, lambda _match: target, segment)


def _normalize_named_colors(segment: str) -> str:
    """Canonicalize the project's existing RGBA equivalents of named colors."""

    for components, color_name in EQUIVALENT_NAMED_COLORS:
        component_pattern = r"\s*,\s*".join(str(value) for value in components)
        pattern = rf"(?<!\w)Custom\s+Color\s*\(\s*{component_pattern}\s*\)(?!\w)"
        segment = re.sub(
            pattern,
            lambda _match, name=color_name: f"Color({name})",
            segment,
        )
    return segment


def _canonicalize_outside_strings(segment: str, language: str) -> str:
    if language == "it-IT":
        for source, target in sorted(
            ITALIAN_TO_ENGLISH_TOKENS,
            key=lambda replacement: len(replacement[0]),
            reverse=True,
        ):
            segment = _replace_token(segment, source, target)
    segment = _normalize_named_colors(segment)
    return re.sub(r"\s+", "", segment)


def canonical_semantic_text(text: str, language: str) -> str:
    """Return a semantic comparison stream while preserving quoted text.

    Only known it-IT grammar tokens and equivalent color spellings are
    canonicalized. Whitespace is ignored exclusively outside quoted strings;
    every quoted character, including titles and runtime text, remains exact.
    """

    if language not in LANGUAGE_PROFILES:
        raise ClipboardImportError(f"profilo lingua non supportato: {language}")

    result: list[str] = []
    outside: list[str] = []
    quoted: list[str] = []
    in_string = False
    escaped = False

    for char in text:
        if in_string:
            quoted.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                result.append("".join(quoted))
                quoted.clear()
                in_string = False
            continue

        if char == '"':
            result.append(
                _canonicalize_outside_strings("".join(outside), language)
            )
            outside.clear()
            quoted.append(char)
            in_string = True
        else:
            outside.append(char)

    if in_string:
        raise ClipboardImportError("stringa Workshop non chiusa: copia/incolla incompleto")
    result.append(_canonicalize_outside_strings("".join(outside), language))
    return "".join(result)


def semantic_equivalence_error(reference: str, italian: str) -> str | None:
    """Describe the first EN/IT semantic mismatch, or return ``None``."""

    english_stream = canonical_semantic_text(reference, "en-US")
    italian_stream = canonical_semantic_text(italian, "it-IT")
    if english_stream == italian_stream:
        return None

    mismatch = next(
        (
            index
            for index, (english_char, italian_char) in enumerate(
                zip(english_stream, italian_stream)
            )
            if english_char != italian_char
        ),
        min(len(english_stream), len(italian_stream)),
    )
    context_start = max(0, mismatch - 45)
    context_end = mismatch + 45
    english_context = english_stream[context_start:context_end]
    italian_context = italian_stream[context_start:context_end]
    return (
        "equivalenza semantica EN/IT fallita all'offset canonico "
        f"{mismatch}: EN={english_context!r}; IT={italian_context!r}"
    )


def require_semantic_equivalence(reference: str, italian: str) -> None:
    error = semantic_equivalence_error(reference, italian)
    if error is not None:
        raise ClipboardImportError(error)


def _mask_quoted_text(text: str) -> str:
    out: list[str] = []
    in_string = False
    escaped = False

    for char in text:
        if in_string:
            if char == "\n":
                out.append("\n")
                escaped = False
                continue
            if escaped:
                out.append(" ")
                escaped = False
                continue
            if char == "\\":
                out.append(" ")
                escaped = True
                continue
            if char == '"':
                out.append('"')
                in_string = False
            else:
                out.append(" ")
            continue

        if char == '"':
            out.append('"')
            in_string = True
        else:
            out.append(char)

    if in_string:
        raise ClipboardImportError("stringa Workshop non chiusa: copia/incolla incompleto")
    return "".join(out)


def _scan_balanced(text: str) -> None:
    stack: list[tuple[str, int]] = []
    pairs = {"}": "{", ")": "(", "]": "["}
    opening = set(pairs.values())
    in_string = False
    escaped = False

    for index, char in enumerate(text):
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
            continue
        if char in opening:
            stack.append((char, index))
        elif char in pairs:
            if not stack or stack[-1][0] != pairs[char]:
                raise ClipboardImportError(
                    f"delimitatore {char!r} non bilanciato alla posizione {index}"
                )
            stack.pop()

    if in_string:
        raise ClipboardImportError("stringa Workshop non chiusa: copia/incolla incompleto")
    if stack:
        char, index = stack[-1]
        raise ClipboardImportError(
            f"delimitatore {char!r} aperto e non chiuso alla posizione {index}"
        )


def _find_matching_brace(text: str, opening_index: int) -> int:
    depth = 0
    in_string = False
    escaped = False

    for index in range(opening_index, len(text)):
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
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    raise ClipboardImportError("blocco regola senza graffa finale")


def _detect_language(syntax: str) -> str:
    first_code = syntax.lstrip()
    for language, profile in LANGUAGE_PROFILES.items():
        if re.match(rf"{re.escape(profile.variables)}\b", first_code):
            return language
    expected = ", ".join(
        f"{language}:{profile.variables}" for language, profile in LANGUAGE_PROFILES.items()
    )
    raise ClipboardImportError(
        f"inizio clipboard non riconosciuto; atteso uno dei profili {expected}"
    )


def _extract_rule_sizes(text: str, profile: LanguageProfile) -> list[RuleSize]:
    rules: list[RuleSize] = []
    pattern = re.compile(
        rf'(?m)^{re.escape(profile.rule)}\("([^"\n]+)"\)\s*\{{'
    )

    for match in pattern.finditer(text):
        opening = text.find("{", match.start(), match.end())
        if opening < 0:
            raise ClipboardImportError(
                f"{profile.rule} {match.group(1)!r} senza graffa iniziale"
            )
        closing = _find_matching_brace(text, opening)
        block = text[match.start() : closing + 1]
        rules.append(RuleSize(match.group(1), len(block.encode("utf-8")),
                              structural_rule_units(block, profile)))

    if not rules:
        raise ClipboardImportError(
            f"nessuna {profile.rule} Workshop trovata per il profilo selezionato"
        )
    return rules


def _require_structural_grammar(syntax: str, language: str) -> None:
    profile = LANGUAGE_PROFILES[language]
    expected_lines = (
        profile.variables,
        profile.subroutines,
        profile.event,
        profile.conditions,
        profile.actions,
    )
    for token in expected_lines:
        if not re.search(rf"(?m)^\s*{re.escape(token)}\s*$", syntax):
            raise ClipboardImportError(
                f"keyword strutturale {token!r} assente per il profilo {language}"
            )

    if not re.search(
        rf'(?m)^{re.escape(profile.rule)}\(\"\s*\"\)\s*$', syntax
    ):
        raise ClipboardImportError(
            f"header {profile.rule}(\"...\") assente per il profilo {language}"
        )

    for other_language, other in LANGUAGE_PROFILES.items():
        if other_language == language:
            continue
        foreign_tokens = (
            other.variables,
            other.subroutines,
            other.event,
            other.conditions,
            other.actions,
        )
        for token in foreign_tokens:
            if re.search(rf"(?m)^\s*{re.escape(token)}\s*$", syntax):
                raise ClipboardImportError(
                    f"formato misto {language}/{other_language}: trovato {token!r}"
                )
        if re.search(rf'(?m)^{re.escape(other.rule)}\(\"', syntax):
            raise ClipboardImportError(
                f"formato misto {language}/{other_language}: trovato {other.rule!r}"
            )


    if language == "it-IT":
        for pattern, label in FORBIDDEN_ENGLISH_IN_ITALIAN_SYNTAX:
            if re.search(pattern, syntax):
                raise ClipboardImportError(
                    f"formato misto it-IT/en-US: trovato {label}"
                )


def check_text(text: str, language: str | None = None) -> Report:
    if not text:
        raise ClipboardImportError("sorgente Workshop vuoto")
    if text.startswith("\ufeff"):
        raise ClipboardImportError("BOM UTF-8 prima del blocco iniziale")
    if "\x00" in text:
        raise ClipboardImportError("byte NUL nel sorgente: clipboard non valida")
    if "```" in text:
        raise ClipboardImportError(
            "fence Markdown trovata: copiare solo il contenuto del file Workshop"
        )

    try:
        text.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ClipboardImportError(f"testo non codificabile in UTF-8: {exc}") from exc

    _scan_balanced(text)
    syntax = _mask_quoted_text(text)
    detected = _detect_language(syntax)

    if language is not None:
        if language not in LANGUAGE_PROFILES:
            raise ClipboardImportError(f"profilo lingua non supportato: {language}")
        if detected != language:
            raise ClipboardImportError(
                f"clipboard {detected} fornita al controllo {language}"
            )
    else:
        language = detected

    _require_structural_grammar(syntax, language)

    for char, label in FORBIDDEN_OUTSIDE_STRINGS.items():
        if char in syntax:
            raise ClipboardImportError(f"{label} fuori da una stringa Workshop")

    profile = LANGUAGE_PROFILES[language]
    first_code = syntax.lstrip()
    if not first_code.startswith(profile.variables):
        raise ClipboardImportError(
            f"il clipboard {language} deve iniziare da {profile.variables!r}"
        )

    rules = _extract_rule_sizes(text, profile)
    largest = max(rules, key=lambda item: item.bytes_utf8)

    if largest.bytes_utf8 > SOURCE_RULE_SAFETY_TARGET_BYTES:
        raise ClipboardImportError(
            f"regola {largest.name!r} usa {largest.bytes_utf8} byte di testo: "
            "supera il target statico di sicurezza di 80 KB"
        )

    structural_units = sum(rule.structural_units for rule in rules)
    largest_structural = max(rules, key=lambda item: item.structural_units)
    if structural_units > SOURCE_TOTAL_STRUCTURAL_TARGET:
        raise ClipboardImportError(
            f"stima strutturale offline {structural_units}: supera il budget locale "
            f"di {SOURCE_TOTAL_STRUCTURAL_TARGET} unità (non è l'Element Count del client)"
        )
    if largest_structural.structural_units > SOURCE_RULE_STRUCTURAL_TARGET:
        raise ClipboardImportError(
            f"regola {largest_structural.name!r}: stima strutturale offline "
            f"{largest_structural.structural_units}, oltre il budget locale di "
            f"{SOURCE_RULE_STRUCTURAL_TARGET} unità/regola"
        )

    return Report(
        language=language,
        source_bytes_utf8=len(text.encode("utf-8")),
        rule_count=len(rules),
        largest_rule=largest,
        structural_units=structural_units,
        largest_structural_rule=largest_structural,
    )


def check_path(path: Path = DEFAULT_SOURCE, language: str | None = None) -> Report:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ClipboardImportError("BOM UTF-8 prima del blocco iniziale")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ClipboardImportError(f"file non UTF-8: {exc}") from exc
    report = check_text(text, language)

    if path.resolve() == ITALIAN_SOURCE.resolve():
        reference_raw = SEMANTIC_REFERENCE.read_bytes()
        if reference_raw.startswith(b"\xef\xbb\xbf"):
            raise ClipboardImportError("BOM UTF-8 nel riferimento semantico EN")
        try:
            reference = reference_raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ClipboardImportError(
                f"riferimento semantico EN non UTF-8: {exc}"
            ) from exc
        check_text(reference, "en-US")
        require_semantic_equivalence(reference, text)

    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Workshop clipboard preflight")
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--language", choices=sorted(LANGUAGE_PROFILES))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        report = check_path(args.path, args.language)
    except (OSError, ClipboardImportError) as exc:
        print(f"ERROR - clipboard import: {exc}", file=sys.stderr)
        return 1

    print(
        "OK - clipboard import preflight: "
        f"{report.language}, {report.rule_count} rules, "
        f"source {report.source_bytes_utf8} bytes UTF-8, "
        f"largest source rule {report.largest_rule.bytes_utf8} bytes "
        f"({report.largest_rule.name})"
    )
    print(
        f"OK - offline structural proxy: {report.structural_units} units total; "
        f"largest rule {report.largest_structural_rule.structural_units} units "
        f"({report.largest_structural_rule.name}); local budgets "
        f"{SOURCE_TOTAL_STRUCTURAL_TARGET}/{SOURCE_RULE_STRUCTURAL_TARGET}."
    )
    print(
        "NOTE - Element Count e Largest Rule compilato devono essere verificati "
        "nel client dopo il paste (hard limits: 32768 elementi, <98 KB/rule)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
