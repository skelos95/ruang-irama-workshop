#!/usr/bin/env python3
"""Static preflight for pasting the canonical Workshop source into Overwatch.

The Italian Overwatch client localizes the editor UI/descriptions, but Workshop
programming tokens remain English. This checker protects the text format that is
safe to copy from the repository and paste into the in-game Workshop editor.

It intentionally does *not* claim to reproduce the in-client Element Count or
compiled Largest Rule diagnostics. Those values must still be read from the
client after import. The per-rule byte check below is a conservative source-text
proxy with an 80 KB safety target below the client's 98 KB Largest Rule limit.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "workshop" / "ruang_irama.workshop"

# The client screenshot reports Largest Rule must stay below 98 KB. We keep the
# canonical text well below that value because compiled Workshop size is not
# identical to source UTF-8 size.
CLIENT_LARGEST_RULE_LIMIT_BYTES = 98_000
SOURCE_RULE_SAFETY_TARGET_BYTES = 80_000

ITALIAN_STRUCTURAL_TOKENS = (
    "variabili",
    "sottoprogrammi",
    "regola",
    "evento",
    "condizioni",
    "azioni",
)

# These characters are common copy/paste corruption outside quoted strings.
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
    source_bytes_utf8: int
    rule_count: int
    largest_rule: RuleSize


class ClipboardImportError(ValueError):
    pass


def _mask_quoted_text(text: str) -> str:
    """Replace string contents with spaces while preserving layout and quotes."""
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
    raise ClipboardImportError("blocco rule senza graffa finale")


def _extract_rule_sizes(text: str) -> list[RuleSize]:
    rules: list[RuleSize] = []
    pattern = re.compile(r'(?m)^rule\("([^"\n]+)"\)\s*\{')

    for match in pattern.finditer(text):
        opening = text.find("{", match.start(), match.end())
        if opening < 0:
            raise ClipboardImportError(f"rule {match.group(1)!r} senza graffa iniziale")
        closing = _find_matching_brace(text, opening)
        block = text[match.start() : closing + 1]
        rules.append(RuleSize(match.group(1), len(block.encode("utf-8"))))

    if not rules:
        raise ClipboardImportError("nessuna rule Workshop trovata")
    return rules


def check_text(text: str) -> Report:
    if not text:
        raise ClipboardImportError("sorgente Workshop vuoto")
    if text.startswith("\ufeff"):
        raise ClipboardImportError("BOM UTF-8 prima di 'variables': rimuoverlo prima del paste")
    if "\x00" in text:
        raise ClipboardImportError("byte NUL nel sorgente: clipboard non valida")
    if "```" in text:
        raise ClipboardImportError("fence Markdown trovata: copiare solo il contenuto del file Workshop")

    try:
        text.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ClipboardImportError(f"testo non codificabile in UTF-8: {exc}") from exc

    _scan_balanced(text)
    syntax = _mask_quoted_text(text)

    # Canonical clipboard grammar. These words are intentionally English even
    # when the Overwatch UI is Italian.
    if not re.search(r"(?m)^variables\s*$", syntax):
        raise ClipboardImportError("blocco English 'variables' assente")
    if not re.search(r"(?m)^subroutines\s*$", syntax):
        raise ClipboardImportError("blocco English 'subroutines' assente")
    if not re.search(r"(?m)^rule\(\"\s*\"\)\s*$", syntax):
        # The title was masked but the quote delimiters remain, so any canonical
        # rule header becomes rule("   ").
        raise ClipboardImportError("header English 'rule(\"...\")' assente")

    for token in ("event", "conditions", "actions"):
        if not re.search(rf"(?m)^\s*{token}\s*$", syntax):
            raise ClipboardImportError(f"keyword Workshop English {token!r} assente")

    for token in ITALIAN_STRUCTURAL_TOKENS:
        if re.search(rf"(?mi)^\s*{re.escape(token)}(?:\s*\(|\s*$)", syntax):
            raise ClipboardImportError(
                f"token strutturale italiano {token!r} trovato: la sintassi da incollare deve restare English"
            )

    for char, label in FORBIDDEN_OUTSIDE_STRINGS.items():
        if char in syntax:
            raise ClipboardImportError(f"{label} fuori da una stringa Workshop")

    first_code = syntax.lstrip()
    if not first_code.startswith("variables"):
        raise ClipboardImportError("il clipboard deve iniziare dal blocco 'variables', senza testo introduttivo")

    rules = _extract_rule_sizes(text)
    largest = max(rules, key=lambda item: item.bytes_utf8)

    if largest.bytes_utf8 >= CLIENT_LARGEST_RULE_LIMIT_BYTES:
        raise ClipboardImportError(
            f"rule {largest.name!r} usa {largest.bytes_utf8} byte di testo: supera il limite client di 98 KB"
        )
    if largest.bytes_utf8 > SOURCE_RULE_SAFETY_TARGET_BYTES:
        raise ClipboardImportError(
            f"rule {largest.name!r} usa {largest.bytes_utf8} byte di testo: supera il target statico di sicurezza di 80 KB"
        )

    return Report(
        source_bytes_utf8=len(text.encode("utf-8")),
        rule_count=len(rules),
        largest_rule=largest,
    )


def check_path(path: Path = DEFAULT_SOURCE) -> Report:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ClipboardImportError("BOM UTF-8 prima di 'variables': rimuoverlo prima del paste")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ClipboardImportError(f"file non UTF-8: {exc}") from exc
    return check_text(text)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    path = Path(args[0]) if args else DEFAULT_SOURCE
    try:
        report = check_path(path)
    except (OSError, ClipboardImportError) as exc:
        print(f"ERROR - clipboard import: {exc}", file=sys.stderr)
        return 1

    print(
        "OK - clipboard import preflight: "
        f"{report.rule_count} rules, source {report.source_bytes_utf8} bytes UTF-8, "
        f"largest source rule {report.largest_rule.bytes_utf8} bytes "
        f"({report.largest_rule.name})"
    )
    print(
        "NOTE - Element Count e Largest Rule compilato devono essere verificati "
        "nel client dopo il paste (hard limits mostrati dal client: 32768 elementi, <98 KB/rule)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
