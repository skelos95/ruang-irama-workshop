#!/usr/bin/env python3
"""Static preflight for Workshop text copied into Overwatch.

Overwatch's Workshop clipboard grammar is localized. The canonical project source
is kept in en-US syntax, while the Italian client must receive the generated
it-IT clipboard variant. This checker validates either profile without pretending
to reproduce the client's compiled Element Count or Largest Rule metrics.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "workshop" / "ruang_irama.it-IT.workshop"
ITALIAN_SOURCE = ROOT / "workshop" / "ruang_irama.it-IT.workshop"

CLIENT_LARGEST_RULE_LIMIT_BYTES = 98_000
SOURCE_RULE_SAFETY_TARGET_BYTES = 80_000


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


@dataclass(frozen=True)
class RuleSize:
    name: str
    bytes_utf8: int


@dataclass(frozen=True)
class Report:
    language: str
    source_bytes_utf8: int
    rule_count: int
    largest_rule: RuleSize


class ClipboardImportError(ValueError):
    pass


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
        rules.append(RuleSize(match.group(1), len(block.encode("utf-8"))))

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

    if largest.bytes_utf8 >= CLIENT_LARGEST_RULE_LIMIT_BYTES:
        raise ClipboardImportError(
            f"regola {largest.name!r} usa {largest.bytes_utf8} byte di testo: "
            "supera il limite client di 98 KB"
        )
    if largest.bytes_utf8 > SOURCE_RULE_SAFETY_TARGET_BYTES:
        raise ClipboardImportError(
            f"regola {largest.name!r} usa {largest.bytes_utf8} byte di testo: "
            "supera il target statico di sicurezza di 80 KB"
        )

    return Report(
        language=language,
        source_bytes_utf8=len(text.encode("utf-8")),
        rule_count=len(rules),
        largest_rule=largest,
    )


def check_path(path: Path = DEFAULT_SOURCE, language: str | None = None) -> Report:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ClipboardImportError("BOM UTF-8 prima del blocco iniziale")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ClipboardImportError(f"file non UTF-8: {exc}") from exc
    return check_text(text, language)


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
        "NOTE - Element Count e Largest Rule compilato devono essere verificati "
        "nel client dopo il paste (hard limits: 32768 elementi, <98 KB/rule)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
