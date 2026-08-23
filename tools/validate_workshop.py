#!/usr/bin/env python3
"""Semantic static gate for CHILL Dedicated Server Workshop 0.8.0.

The validator deliberately checks behaviour and ownership boundaries instead of
pinning the complete Workshop export or rule-number prefixes. It only uses the
Python standard library so the same gate can run locally and in GitHub Actions.
"""

from __future__ import annotations

import ast
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests" / "fixtures" / "semantic_reference.txt"
VERSION = ROOT / "VERSION"
WORKFLOWS = ROOT / ".github" / "workflows"

CURRENT_VERSION = "0.8.0"
ALLOWED_WORKFLOWS = {"validate-workshop.yml"}
MAX_DECLARATION_NAME_BYTES = 32
CORE_DOCS = (
    "README.md",
    "docs/PROGETTO.md",
    "docs/VALIDAZIONE.md",
    "docs/TEST.md",
)

MENU_ACTION_BUTTONS = {
    "Primary Fire",
    "Secondary Fire",
    "Interact",
    "Reload",
    "Ability 1",
    "Ability 2",
}
NATIVE_BUTTONS = {"Melee", "Jump", "Crouch"}
GLOBAL_MODIFIER_CLAUSES = (
    "in menu: modifier for every command",
    "di menu: pengubah semua perintah",
    "ในเมนู: ใช้ร่วมกับทุกคำสั่ง",
)
MENU_CROUCH_INSTRUCTIONS = (
    "Hold CROUCH + command",
    "Tahan JONGKOK + perintah",
    "กด ย่อ + คำสั่ง",
)
SCHEDULER_SUBROUTINES = {
    "ProsesCepatPemain",
    "ProsesSiklusPemain",
    "ProsesCachePemain",
    "ProsesNasibPemain",
}
PAGE_APPLY_SUBROUTINES = {
    "TerapkanHalamanMusik",
    "TerapkanHalamanKamera",
    "TerapkanHalamanWarna",
    "TerapkanHalamanBahasa",
    "TerapkanHalamanBalasDendam",
    "TerapkanHalamanKebal",
    "TerapkanHalamanSuara",
    "TerapkanHalamanIkon",
    "TerapkanTeleportasiJongkok",
    "TerapkanHalamanPrivasiInspeksi",
    "TerapkanHalamanNasib",
    "TerapkanHalamanPilihan",
}
LIFECYCLE_SUBROUTINES = {"SiapkanPemain", "TenangkanPemain", "BersihkanPemain"}
LUCK_TIMESTAMP_VARIABLES = {
    "WaktuPutaranNasibBerikut",
    "WaktuIkonNasibBerakhir",
    "EfekNasibBerakhir",
    "WaktuBakarNasibBerikut",
}
LOCALIZED_ARRAY_SIZES = {
    "NamaIkonInggris": 37,
    "NamaIkonIndonesia": 37,
    "NamaIkonThai": 37,
    "NamaLokasiInggris": 26,
    "NamaLokasiIndonesia": 26,
    "NamaLokasiThai": 26,
}
GAME_MODES = (
    "Push",
    "Flashpoint",
    "Capture The Flag",
    "Control",
    "Clash",
    "Hybrid",
    "Escort",
    "Assault",
)
FORBIDDEN_LEGACY_IDENTIFIERS = {
    "HudMenuArcade",
    "HalamanHudMenuArcade",
    "HalamanMenuTujuan",
    "HalamanSubmenuPramuat",
    "PramuatSubmenu",
    "IndeksVote",
    "TickBurnNasib",
    "TeksKartuNasib",
    "TeksKartuNasibKanan",
    "TeksDiri",
    "TeksDiriPemain",
    "IkonKartuNasibHijau",
    "ModeKebalTerakhir",
    "PosisiNasibTerkunci",
    "WarnaNasibTerkunci",
    "EfekNasibCahaya",
    "EfekNasibLingkaran",
    "RadiusNasib",
    "GerakNasibDikunci",
    "DaftarTujuanNasib",
    "TujuanNasib",
    "ArahNasib",
    "KategoriTeleportNasib",
}
FORBIDDEN_PROSE = re.compile(
    r"\b(?:rilascia|restituisci|reticolo|senza|roulette|sei effetti|risultato|"
    r"reset completo|alla morte|riapri|solo quando|scadenza|temporanei|pulisce|"
    r"proporzionale|aggiorna|distruggi|ricrea|menu ?render|target ?page ?render|"
    r"submenu ?preload|preload|cleanup|english comment|italian comment)\b",
    re.IGNORECASE,
)
FORBIDDEN_RESULT_ACTIONS = (
    "Declare Match Draw(",
    "Declare Player Victory(",
    "Declare Round Victory(",
    "Declare Team Victory(",
    "Set Team Score(",
    "Modify Team Score(",
    "Disable Built-In Game Mode Scoring;",
)


@dataclass(frozen=True)
class Rule:
    name: str
    body: str
    start: int
    end: int


@dataclass(frozen=True)
class Call:
    name: str
    raw: str
    args: tuple[str, ...]
    start: int
    end: int


@dataclass(frozen=True)
class Declaration:
    index: int
    name: str


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
    raise ValueError(f"delimitatore {opener}{closer} non chiuso")


def matching_brace(text: str, opening: int) -> int:
    return matching_delimiter(text, opening, "{", "}")


def matching_parenthesis(text: str, opening: int) -> int:
    return matching_delimiter(text, opening, "(", ")")


def mask_strings(text: str) -> str:
    chars = list(text)
    in_string = False
    escaped = False
    for index, char in enumerate(text):
        if in_string:
            if char not in "\r\n":
                chars[index] = " "
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            chars[index] = " "
            in_string = True
    return "".join(chars)


def split_top_level(text: str, delimiter: str = ",") -> list[str]:
    parts: list[str] = []
    start = 0
    round_depth = square_depth = brace_depth = 0
    in_string = False
    escaped = False
    ternary_depth = 0
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
        elif char == "(":
            round_depth += 1
        elif char == ")":
            round_depth -= 1
        elif char == "[":
            square_depth += 1
        elif char == "]":
            square_depth -= 1
        elif char == "{":
            brace_depth += 1
        elif char == "}":
            brace_depth -= 1
        elif char == "?" and round_depth == square_depth == brace_depth == 0:
            ternary_depth += 1
        elif char == ":" and round_depth == square_depth == brace_depth == 0 and ternary_depth:
            ternary_depth -= 1
        elif char == delimiter and round_depth == square_depth == brace_depth == ternary_depth == 0:
            parts.append(text[start:index].strip())
            start = index + 1
    parts.append(text[start:].strip())
    return parts


def iter_calls(text: str, name: str, *, masked_text: str | None = None) -> Iterator[Call]:
    pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(name)}\s*\(")
    masked_text = mask_strings(text) if masked_text is None else masked_text
    for match in pattern.finditer(masked_text):
        opening = text.find("(", match.start())
        try:
            closing = matching_parenthesis(text, opening)
        except ValueError:
            continue
        raw = text[match.start():closing + 1]
        yield Call(name, raw, tuple(split_top_level(text[opening + 1:closing])), match.start(), closing + 1)


def extract_rules(text: str) -> list[Rule]:
    found: list[Rule] = []
    for match in re.finditer(r'^rule\("([^"\r\n]+)"\)\s*\{', text, re.MULTILINE):
        opening = text.find("{", match.start())
        closing = matching_brace(text, opening)
        found.append(Rule(match.group(1), text[match.start():closing + 1], match.start(), closing + 1))
    return found


def event_block(rule: Rule) -> str:
    match = re.search(r"\bevent\s*\{", rule.body)
    if not match:
        return ""
    opening = rule.body.find("{", match.start())
    return rule.body[opening + 1:matching_brace(rule.body, opening)]


def rule_block(rule: Rule, name: str) -> str | None:
    masked = mask_strings(rule.body)
    match = re.search(rf"\b{re.escape(name)}\s*\{{", masked)
    if not match:
        return None
    opening = masked.find("{", match.start())
    return rule.body[opening + 1:matching_brace(rule.body, opening)]


def delimiter_error(text: str) -> str | None:
    """Return the first unbalanced ()/[] error outside Workshop strings."""
    masked = mask_strings(text)
    pairs = {"(": ")", "[": "]"}
    closing_to_opening = {closing: opening for opening, closing in pairs.items()}
    stack: list[tuple[str, int]] = []
    for index, char in enumerate(masked):
        if char == ";" and stack:
            opening, opening_index = stack[-1]
            line = masked.count("\n", 0, index) + 1
            opening_line = masked.count("\n", 0, opening_index) + 1
            return (
                f"terminatore statement ';' alla riga locale {line} con delimitatore "
                f"{opening!r} ancora aperto dalla riga locale {opening_line}"
            )
        if char in pairs:
            stack.append((char, index))
            continue
        if char not in closing_to_opening:
            continue
        line = masked.count("\n", 0, index) + 1
        if not stack:
            return f"delimitatore {char!r} inatteso alla riga locale {line}"
        opening, opening_index = stack.pop()
        if opening != closing_to_opening[char]:
            opening_line = masked.count("\n", 0, opening_index) + 1
            return (
                f"delimitatore {char!r} non chiude {opening!r} "
                f"aperto alla riga locale {opening_line}"
            )
    if stack:
        opening, opening_index = stack[-1]
        opening_line = masked.count("\n", 0, opening_index) + 1
        return f"delimitatore {opening!r} non chiuso dalla riga locale {opening_line}"
    return None


def event_type(rule: Rule) -> str:
    block = event_block(rule)
    match = re.search(r"([^;\r\n]+);", block)
    return match.group(1).strip() if match else ""


def subroutine_target(rule: Rule) -> str | None:
    if event_type(rule) != "Subroutine":
        return None
    statements = [part.strip() for part in event_block(rule).split(";") if part.strip()]
    return statements[1] if len(statements) > 1 else None


def declaration_entries(text: str) -> tuple[list[Declaration], list[Declaration], list[Declaration], tuple[int, int]]:
    variables = re.search(r"\bvariables\s*\{", text)
    subroutines = re.search(r"\bsubroutines\s*\{", text)
    if not variables or not subroutines:
        raise ValueError("dichiarazioni variables/subroutines assenti")
    variables_open = text.find("{", variables.start())
    variables_close = matching_brace(text, variables_open)
    sub_open = text.find("{", subroutines.start())
    sub_close = matching_brace(text, sub_open)
    global_entries: list[Declaration] = []
    player_entries: list[Declaration] = []
    section: str | None = None
    for raw in text[variables_open + 1:variables_close].splitlines():
        line = raw.strip()
        if line == "global:":
            section = "global"
            continue
        if line == "player:":
            section = "player"
            continue
        match = re.fullmatch(r"(\d+):\s*([A-Za-z][A-Za-z0-9_]*)", line)
        if match and section:
            entry = Declaration(int(match.group(1)), match.group(2))
            (global_entries if section == "global" else player_entries).append(entry)
    sub_entries = [
        Declaration(int(match.group(1)), match.group(2))
        for match in re.finditer(r"(?m)^\s*(\d+):\s*([A-Za-z][A-Za-z0-9_]*)\s*$", text[sub_open + 1:sub_close])
    ]
    return global_entries, player_entries, sub_entries, (variables.start(), sub_close + 1)


def rule_by_subroutine(rules: Iterable[Rule], name: str) -> Rule | None:
    return next((rule for rule in rules if subroutine_target(rule) == name), None)


def rules_with_event(rules: Iterable[Rule], kind: str) -> list[Rule]:
    return [rule for rule in rules if event_type(rule) == kind]


def action_loop_count(text: str) -> int:
    return len(re.findall(r"(?m)^\s*Loop(?: If Condition Is (?:True|False))?;\s*$", mask_strings(text)))


def wait_calls(text: str) -> list[Call]:
    return list(iter_calls(text, "Wait"))


def for_spans(rule: Rule) -> list[str]:
    """Return balanced Workshop For blocks, including nested If blocks."""
    stack: list[tuple[str, int]] = []
    spans: list[str] = []
    offset = 0
    for line in rule.body.splitlines(keepends=True):
        stripped = mask_strings(line).strip()
        if re.match(r"For (?:Global|Player) Variable", stripped):
            stack.append(("for", offset))
        elif stripped.startswith("If("):
            stack.append(("if", offset))
        elif stripped == "End;" and stack:
            kind, start = stack.pop()
            if kind == "for":
                spans.append(rule.body[start:offset + len(line)])
        offset += len(line)
    return spans


def normalized_rule_body(rule: Rule) -> str:
    body = re.sub(r'^rule\("[^"\r\n]+"\)', 'rule("")', rule.body, count=1)
    return re.sub(r"\s+", "", body)


def is_read_reference(code: str, name: str, *, masked_code: str | None = None) -> bool:
    masked = mask_strings(code) if masked_code is None else masked_code
    for match in re.finditer(rf"\b{re.escape(name)}\b", masked):
        start, end = match.span()
        suffix = masked[end:end + 80]
        prefix = masked[max(0, start - 160):start]
        if re.match(r"\s*(?:\[[^\]\r\n]+\])?\s*=(?!=)", suffix):
            continue
        if start > 0 and masked[start - 1] == ".":
            return True
        if re.search(
            r"(?:Set|Modify|Chase|Stop Chasing) (?:Global|Player) Variable(?: At Index)?\([^;\r\n]*$",
            prefix,
        ):
            continue
        if re.search(r"For (?:Global|Player) Variable\([^;\r\n]*$", prefix):
            continue
        return True
    return False


def no_op_assignments(source: str, *, masked_source: str | None = None) -> list[str]:
    masked = mask_strings(source) if masked_source is None else masked_source
    found: list[str] = []
    for match in re.finditer(
        r"\b(Global|Event Player)\.([A-Za-z][A-Za-z0-9_]*)\s*=\s*\1\.\2\s*;",
        masked,
    ):
        found.append(source[match.start():match.end()].strip())
    for scope, action in (
        ("player", "Set Player Variable"),
        ("global", "Set Global Variable"),
    ):
        for call in iter_calls(source, action, masked_text=masked):
            if scope == "player" and len(call.args) >= 3:
                player, name, value = (argument.strip() for argument in call.args[:3])
                if value == f"{player}.{name}":
                    found.append(call.raw)
            elif scope == "global" and len(call.args) >= 2:
                name, value = (argument.strip() for argument in call.args[:2])
                if value == f"Global.{name}":
                    found.append(call.raw)
    return found


def custom_reference_errors(source: str, globals_: set[str], players: set[str]) -> list[str]:
    """Find custom variable references that have no matching declaration."""
    masked = mask_strings(source)
    errors: set[str] = set()
    for name in re.findall(r"\bGlobal\.([A-Za-z][A-Za-z0-9_]*)", masked):
        if name not in globals_:
            errors.add(f"riferimento Global non dichiarato: {name}")
    for name in re.findall(r"\bEvent Player\.([A-Za-z][A-Za-z0-9_]*)", masked):
        if name not in players:
            errors.add(f"riferimento player non dichiarato: {name}")
    for name in re.findall(r"\bGlobal\.(?:PemainAktif|PemainPembersihan)\.([A-Za-z][A-Za-z0-9_]*)", masked):
        if name not in players:
            errors.add(f"riferimento player non dichiarato: {name}")

    player_actions = (
        "Player Variable",
        "Set Player Variable",
        "Set Player Variable At Index",
        "Modify Player Variable",
        "Modify Player Variable At Index",
        "Chase Player Variable At Rate",
        "Chase Player Variable Over Time",
        "Stop Chasing Player Variable",
        "For Player Variable",
    )
    for action in player_actions:
        for call in iter_calls(source, action, masked_text=masked):
            if len(call.args) >= 2:
                name = call.args[1].strip()
                if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name) and name not in players:
                    errors.add(f"riferimento player non dichiarato: {name}")

    global_actions = (
        "Set Global Variable",
        "Set Global Variable At Index",
        "Modify Global Variable",
        "Modify Global Variable At Index",
        "Chase Global Variable At Rate",
        "Chase Global Variable Over Time",
        "Stop Chasing Global Variable",
        "For Global Variable",
    )
    for action in global_actions:
        for call in iter_calls(source, action, masked_text=masked):
            if call.args:
                name = call.args[0].strip()
                if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name) and name not in globals_:
                    errors.add(f"riferimento Global non dichiarato: {name}")
    return sorted(errors)


def parse_literal(argument: str) -> str | None:
    argument = argument.strip()
    if not argument.startswith('"'):
        return None
    escaped = False
    for index in range(1, len(argument)):
        char = argument[index]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            try:
                return ast.literal_eval(argument[:index + 1])
            except (SyntaxError, ValueError):
                return None
    return None


def placeholder_signature(text: str) -> tuple[int, ...]:
    return tuple(sorted(int(value) for value in re.findall(r"(?<!\{)\{(\d+)\}(?!\})", text)))


def format_signatures(expression: str) -> Counter[tuple[int, ...]]:
    signatures: Counter[tuple[int, ...]] = Counter()
    for call in iter_calls(expression, "Custom String"):
        if not call.args:
            continue
        literal = parse_literal(call.args[0])
        if literal is not None:
            signatures[placeholder_signature(literal)] += 1
    return signatures


def outer_format_signature(expression: str) -> tuple[int, ...] | None:
    """Return the format of a branch's outer Custom String, if it has one."""
    expression = trim_outer_parentheses(expression)
    match = re.match(r"Custom String\s*\(", expression)
    if not match:
        return None
    opening = expression.find("(", match.start())
    try:
        closing = matching_parenthesis(expression, opening)
    except ValueError:
        return None
    if expression[closing + 1:].strip():
        return None
    args = split_top_level(expression[opening + 1:closing])
    literal = parse_literal(args[0]) if args else None
    return placeholder_signature(literal) if literal is not None else None


def trim_outer_parentheses(expression: str) -> str:
    expression = expression.strip()
    while expression.startswith("("):
        try:
            closing = matching_parenthesis(expression, 0)
        except ValueError:
            break
        if closing != len(expression) - 1:
            break
        expression = expression[1:-1].strip()
    return expression


def parse_top_level_ternary(expression: str) -> tuple[str, str, str] | None:
    expression = trim_outer_parentheses(expression)
    in_string = False
    escaped = False
    round_depth = square_depth = brace_depth = 0
    question: int | None = None
    nested = 0
    for index, char in enumerate(expression):
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
        elif char == "(":
            round_depth += 1
        elif char == ")":
            round_depth -= 1
        elif char == "[":
            square_depth += 1
        elif char == "]":
            square_depth -= 1
        elif char == "{":
            brace_depth += 1
        elif char == "}":
            brace_depth -= 1
        elif round_depth == square_depth == brace_depth == 0:
            if char == "?":
                if question is None:
                    question = index
                else:
                    nested += 1
            elif char == ":" and question is not None:
                if nested:
                    nested -= 1
                else:
                    return expression[:question].strip(), expression[question + 1:index].strip(), expression[index + 1:].strip()
    return None


def language_triads(expression: str) -> list[tuple[str, str, str]]:
    found: list[tuple[str, str, str]] = []
    visited: set[str] = set()

    def visit(part: str) -> None:
        part = trim_outer_parentheses(part)
        if not part or part in visited:
            return
        visited.add(part)
        ternary = parse_top_level_ternary(part)
        if ternary:
            condition, when_true, when_false = ternary
            second = parse_top_level_ternary(when_false)
            if re.search(r"IndeksBahasa\)?\s*==\s*0\b", condition) and second and re.search(
                r"IndeksBahasa\)?\s*==\s*1\b", second[0]
            ):
                found.append((when_true, second[1], second[2]))
                visit(when_true)
                visit(second[1])
                visit(second[2])
                return
            visit(when_true)
            visit(when_false)
        match = re.match(r"[A-Za-z][A-Za-z0-9 ]*\s*\(", mask_strings(part))
        if match:
            opening = part.find("(", match.start())
            try:
                closing = matching_parenthesis(part, opening)
            except ValueError:
                return
            if not part[closing + 1:].strip():
                for argument in split_top_level(part[opening + 1:closing]):
                    visit(argument)

    visit(expression)
    return found


def array_assignment_items(source: str, name: str) -> list[str] | None:
    masked = mask_strings(source)
    match = re.search(rf"Global\.{re.escape(name)}\s*=\s*Array\s*\(", masked)
    if not match:
        return None
    opening = source.find("(", match.start())
    closing = matching_parenthesis(source, opening)
    return split_top_level(source[opening + 1:closing])


def wait_role(rule: Rule, scheduler: Rule | None) -> str | None:
    body = rule.body
    if scheduler is not None and rule.start == scheduler.start:
        return "scheduler"
    if event_type(rule) in {"Player Joined Match", "Player Left Match"}:
        return "join/leave ordering"
    if "Abort When False" in body and ("Button(Melee)" in body or "Button(Interact)" in body):
        return "hold input"
    if "SudahDiperiksa" in body and "Is Dummy Bot" in body:
        return "bot classification"
    if rule.name == "03f - Bot/Dummy: Teleport dari ruang spawn ke objektif":
        return "dummy spawn stabilization"
    if "Respawn(" in body or "BangkitLompat" in body:
        return "respawn"
    if subroutine_target(rule) == "BersihkanPemain":
        return "atomic cleanup"
    return None


def validate_metadata(checks: Checks, root: Path) -> None:
    version_file = root / "VERSION"
    checks.require(version_file.is_file(), "VERSION assente")
    if version_file.is_file():
        checks.equal(version_file.read_text(encoding="utf-8").strip(), CURRENT_VERSION, "VERSION")

    for relative in CORE_DOCS:
        path = root / relative
        checks.require(path.is_file(), f"documento obbligatorio assente: {relative}")
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            checks.require(CURRENT_VERSION in text, f"documento non allineato a {CURRENT_VERSION}: {relative}")

    combined_docs = "\n".join(
        (root / relative).read_text(encoding="utf-8")
        for relative in CORE_DOCS
        if (root / relative).is_file()
    ).lower()
    checks.require("static-ready" in combined_docs and "live-pending" in combined_docs,
                   "documentazione deve dichiarare static-ready / live-pending")

    workflows = root / ".github" / "workflows"
    found = {path.name for path in workflows.glob("*.yml")} | {path.name for path in workflows.glob("*.yaml")}
    checks.equal(found, ALLOWED_WORKFLOWS, "workflow permanenti")
    validation = workflows / "validate-workshop.yml"
    if validation.is_file():
        workflow_text = validation.read_text(encoding="utf-8")
        checks.require(re.search(r"(?m)^\s*push\s*:", workflow_text) is not None,
                       "workflow validazione deve attivarsi su push")
        checks.require("tools/validate_workshop.py" in workflow_text,
                       "workflow non esegue il validatore semantico")
        checks.require("unittest" in workflow_text,
                       "workflow non esegue gli unit test")
        checks.require("git add -A" not in workflow_text and "git push" not in workflow_text,
                       "workflow validazione non deve modificare o pubblicare il repository")


def validate_rule_grammar(checks: Checks, rules: list[Rule]) -> None:
    """Reject malformed condition/action expressions before semantic call parsing."""
    for rule in rules:
        for section in ("conditions", "actions"):
            block = rule_block(rule, section)
            if block is None:
                if section == "actions":
                    checks.require(False, f"{rule.name}: blocco actions assente")
                continue
            error = delimiter_error(block)
            checks.require(error is None, f"{rule.name}: sintassi {section} non bilanciata: {error}")


def validate_declarations(checks: Checks, source: str, rules: list[Rule], globals_: list[Declaration],
                          players: list[Declaration], subroutines: list[Declaration], declaration_span: tuple[int, int]) -> None:
    for label, entries in (("global", globals_), ("player", players), ("subroutine", subroutines)):
        indices = [entry.index for entry in entries]
        checks.equal(indices, list(range(len(entries))), f"indici {label} compatti")
        names = [entry.name for entry in entries]
        checks.equal(len(names), len(set(names)), f"nomi {label} univoci")
        for entry in entries:
            encoded_size = len(entry.name.encode("utf-8"))
            checks.require(
                encoded_size <= MAX_DECLARATION_NAME_BYTES,
                f"nome {label} oltre {MAX_DECLARATION_NAME_BYTES} byte UTF-8: "
                f"indice {entry.index}, {entry.name} ({encoded_size} byte)",
            )

    all_names = {entry.name for entry in globals_ + players + subroutines}
    for legacy in sorted(FORBIDDEN_LEGACY_IDENTIFIERS):
        checks.require(legacy not in all_names and re.search(rf"\b{re.escape(legacy)}\b", mask_strings(source)) is None,
                       f"identificatore legacy o non indonesiano presente: {legacy}")

    code = source[:declaration_span[0]] + source[declaration_span[1]:]
    masked_code = mask_strings(code)
    for entry in globals_ + players:
        checks.require(re.search(rf"\b{re.escape(entry.name)}\b", masked_code) is not None,
                       f"variabile dichiarata ma mai riferita: {entry.name}")
        checks.require(is_read_reference(code, entry.name, masked_code=masked_code),
                       f"variabile soltanto inizializzata/pulita e mai letta: {entry.name}")

    global_names = {entry.name for entry in globals_}
    player_names = {entry.name for entry in players}
    for error in custom_reference_errors(code, global_names, player_names):
        checks.require(False, error)
    for assignment in no_op_assignments(code, masked_source=masked_code):
        checks.require(False, f"self-assignment no-op vietato: {assignment}")

    declarations = {entry.name for entry in subroutines}
    calls = [call.args[0].strip() for call in iter_calls(source, "Call Subroutine") if call.args]
    implementations = [subroutine_target(rule) for rule in rules if subroutine_target(rule)]
    for name in sorted(declarations):
        checks.equal(implementations.count(name), 1, f"implementazione subroutine {name}")
        checks.require(name in calls, f"subroutine dichiarata ma mai chiamata: {name}")
    for name in sorted(set(calls) - declarations):
        checks.require(False, f"chiamata a subroutine non dichiarata: {name}")
    for name in sorted(set(implementations) - declarations):
        checks.require(False, f"implementazione di subroutine non dichiarata: {name}")

    setup = rule_by_subroutine(rules, "SiapkanPemain")
    checks.require(setup is not None, "SiapkanPemain assente per verifica inizializzazione")
    if setup:
        setup_masked = mask_strings(setup.body)
        setup_action_vars = {
            call.args[1].strip()
            for call in iter_calls(setup.body, "Set Player Variable", masked_text=setup_masked)
            if len(call.args) >= 2 and call.args[0].strip() == "Event Player"
        }
        for entry in players:
            direct = re.search(rf"\bEvent Player\.{re.escape(entry.name)}\s*=(?!=)", setup_masked)
            via_action = entry.name in setup_action_vars
            checks.require(bool(direct or via_action),
                           f"variabile player non inizializzata in SiapkanPemain: {entry.name}")


def validate_localization(checks: Checks, source: str, globals_: set[str]) -> None:
    for name, expected_size in LOCALIZED_ARRAY_SIZES.items():
        checks.require(name in globals_, f"array localizzato dichiarato assente: {name}")
        items = array_assignment_items(source, name)
        checks.require(items is not None, f"array localizzato non inizializzato: {name}")
        if items is not None:
            checks.equal(len(items), expected_size, f"numero voci {name}")
    checks.require("Global.NamaIkonInggris" in source and "Global.NamaIkonIndonesia" in source and "Global.NamaIkonThai" in source,
                   "selettore runtime EN/ID/TH per i 37 nomi icona incompleto")
    checks.require("Global.NamaLokasiInggris" in source and "Global.NamaLokasiIndonesia" in source and "Global.NamaLokasiThai" in source,
                   "selettore runtime EN/ID/TH per le 26 località incompleto")

    setting_specs = (
        ("Workshop Setting Integer", "duration", "durasi"),
        ("Workshop Setting Combo", "location", "lokasi"),
        ("Workshop Setting Toggle", "diagnostics", "diagnostik"),
    )
    for action, english, indonesian in setting_specs:
        calls = list(iter_calls(source, action))
        checks.equal(len(calls), 1, f"numero {action}")
        if calls and len(calls[0].args) >= 2:
            label_call = next(iter(iter_calls(calls[0].args[1], "Custom String")), None)
            label = parse_literal(label_call.args[0]) if label_call and label_call.args else None
            normalized = (label or "").lower()
            checks.require(
                english in normalized and indonesian in normalized and re.search(r"[\u0e00-\u0e7f]", normalized) is not None,
                f"label {action} non contiene EN/ID/TH",
            )

    for call in iter_calls(source, "Custom String"):
        if not call.args:
            checks.require(False, "Custom String senza formato")
            continue
        literal = parse_literal(call.args[0])
        if literal is None:
            continue
        signature = placeholder_signature(literal)
        argument_count = len(call.args) - 1
        if signature:
            checks.require(max(signature) < argument_count,
                           f"placeholder fuori intervallo in Custom String: {literal!r}")
            checks.require(set(signature) == set(range(max(signature) + 1)),
                           f"placeholder non contigui in Custom String: {literal!r}")
        checks.require(argument_count == (max(signature) + 1 if signature else 0),
                       f"numero argomenti/placeholder incoerente in Custom String: {literal!r}")

    triads: list[tuple[str, str, str]] = []
    for call in iter_calls(source, "Small Message"):
        checks.require(len(call.args) >= 2, "Small Message malformato")
        if len(call.args) < 2:
            continue
        found = language_triads(call.args[1])
        checks.require(bool(found), "Small Message senza traduzione EN/ID/TH")
        triads.extend(found)

    for call in iter_calls(source, "Create HUD Text"):
        if len(call.args) < 4:
            checks.require(False, "Create HUD Text malformato")
            continue
        visible_text = call.args[2] + "\n" + call.args[3]
        if "Custom String" in visible_text and re.search(r"[A-Za-z\u0e00-\u0e7f]", visible_text):
            found = language_triads(visible_text)
            selectors = (
                re.search(r"IndeksBahasa\)?\s*==\s*0\b", visible_text) is not None
                and re.search(r"IndeksBahasa\)?\s*==\s*1\b", visible_text) is not None
                and (re.search(r"[\u0e00-\u0e7f]", visible_text) is not None or "Thai" in visible_text)
            )
            checks.require(bool(found) or selectors, "Create HUD Text con testo non tradotto EN/ID/TH")
            triads.extend(found)

    for call in iter_calls(source, "Create In-World Text"):
        if len(call.args) < 2:
            continue
        literals = [parse_literal(custom.args[0]) for custom in iter_calls(call.args[1], "Custom String") if custom.args]
        prose = [literal for literal in literals if literal and re.search(r"[A-Za-z]{3,}", literal) and literal not in {"{0}", "{0} HP", "HP"}]
        if prose:
            found = language_triads(call.args[1])
            checks.require(bool(found), "Create In-World Text con prosa non tradotta EN/ID/TH")
            triads.extend(found)

    checks.require(bool(triads), "nessuna terna di localizzazione EN/ID/TH rilevata")
    for english, indonesian, thai in triads:
        checks.require("ไทย" in thai or "Thai" in thai or re.search(r"[\u0e00-\u0e7f]", thai) is not None,
                       "ramo Thai assente o non riconoscibile")
        signatures = (outer_format_signature(english), outer_format_signature(indonesian), outer_format_signature(thai))
        if all(signature is not None for signature in signatures):
            checks.equal(signatures[0], signatures[1], "parità placeholder EN/ID")
            checks.equal(signatures[0], signatures[2], "parità placeholder EN/TH")

    localized_families = (
        ("icone", "NamaIkonInggris", "NamaIkonIndonesia", "NamaIkonThai"),
        ("località", "NamaLokasiInggris", "NamaLokasiIndonesia", "NamaLokasiThai"),
    )
    for label, english_name, indonesian_name, thai_name in localized_families:
        names = (english_name, indonesian_name, thai_name)
        relevant = [
            branches
            for branches in triads
            if all(any(f"Global.{name}" in branch for name in names) for branch in branches)
        ]
        checks.require(bool(relevant),
                       f"array {label} mai selezionati nei rami runtime IndeksBahasa 0/1/2")
        for english, indonesian, thai in relevant:
            checks.require(
                f"Global.{english_name}" in english
                and f"Global.{indonesian_name}" not in english
                and f"Global.{thai_name}" not in english,
                f"ramo IndeksBahasa 0 usa array {label} errato",
            )
            checks.require(
                f"Global.{indonesian_name}" in indonesian
                and f"Global.{english_name}" not in indonesian
                and f"Global.{thai_name}" not in indonesian,
                f"ramo IndeksBahasa 1 usa array {label} errato",
            )
            checks.require(
                f"Global.{thai_name}" in thai
                and f"Global.{english_name}" not in thai
                and f"Global.{indonesian_name}" not in thai,
                f"ramo IndeksBahasa 2 usa array {label} errato",
            )


def validate_hud_and_menu(checks: Checks, source: str, rules: list[Rule], players: set[str], subroutines: set[str]) -> None:
    checks.require("Big Message(" not in mask_strings(source), "Big Message/titolo vietato")
    lowered_source = source.lower()
    for clause in GLOBAL_MODIFIER_CLAUSES:
        checks.require(
            clause.lower() not in lowered_source,
            f"clausola modifier Crouch duplicata nell'HUD globale: {clause}",
        )
    hud_calls = list(iter_calls(source, "Create HUD Text"))
    checks.require(bool(hud_calls), "nessun HUD testuale trovato")
    for call in hud_calls:
        checks.require(len(call.args) >= 4, "Create HUD Text malformato")
        if len(call.args) >= 2:
            checks.equal(call.args[1].strip(), "Null", "Header Create HUD Text deve essere Null")

    server_title = next(
        (
            call for call in hud_calls
            if len(call.args) >= 4
            and "CHILL DEDICATED SERVER" in call.args[3]
            and "Global.TeksWaktuServer" in call.args[3]
        ),
        None,
    )
    checks.require(server_title is not None, "HUD titolo CHILL e timer server assente")
    if server_title:
        title_literals = [
            parse_literal(custom.args[0])
            for custom in iter_calls(server_title.args[3], "Custom String")
            if custom.args
        ]
        checks.require(
            any(literal is not None and literal.endswith("\n ") for literal in title_literals),
            "HUD titolo CHILL deve mantenere una riga vuota prima del menu",
        )

    checks.require("HudMenu" in players, "handle menu unico HudMenu assente")
    checks.require("GambarMenu" in subroutines and "GambarHalamanAktif" in subroutines,
                   "router menu GambarMenu/GambarHalamanAktif assente")
    menu_renderers = [
        rule for rule in rules
        if subroutine_target(rule) and "Create HUD Text(" in rule.body and "Event Player.HudMenu = Last Text ID;" in rule.body
    ]
    arcade_renderers = [rule for rule in menu_renderers if subroutine_target(rule) != "GambarTeleportasi"]
    checks.equal(len(arcade_renderers), 13, "renderer menu principale + pagine 0..11")
    for rule in menu_renderers:
        calls = list(iter_calls(rule.body, "Create HUD Text"))
        checks.equal(len(calls), 1, f"{subroutine_target(rule)}: un solo Create HUD")
        if calls:
            checks.equal(calls[0].args[0].strip(), "Event Player",
                         f"{subroutine_target(rule)}: HUD menu non deve essere nascosto/precaricato")
            checks.require("\\n" in calls[0].args[2],
                           f"{subroutine_target(rule)}: sottotitolo menu senza spaziatura")
            checks.require(calls[0].args[3].strip() != "Null",
                           f"{subroutine_target(rule)}: contenuto menu assente")
            if rule in arcade_renderers:
                for instruction in MENU_CROUCH_INSTRUCTIONS:
                    checks.require(
                        instruction in calls[0].args[2],
                        f"{subroutine_target(rule)}: istruzione Crouch menu assente: {instruction}",
                    )
                instruction_literals = [
                    parse_literal(custom.args[0])
                    for custom in iter_calls(calls[0].args[2], "Custom String")
                    if custom.args
                ]
                checks.require(
                    not any(literal is not None and literal.startswith("\n") for literal in instruction_literals),
                    f"{subroutine_target(rule)}: sottotitolo menu inizia con una riga vuota artificiale",
                )

    revenge_renderer = rule_by_subroutine(rules, "GambarBalasDendam")
    checks.require(revenge_renderer is not None, "renderer Revenge assente")
    if revenge_renderer:
        revenge_calls = list(iter_calls(revenge_renderer.body, "Create HUD Text"))
        no_target_branch = parse_top_level_ternary(revenge_calls[0].args[2]) if revenge_calls else None
        checks.require(no_target_branch is not None, "renderer Revenge senza ramo no-target")
        if no_target_branch:
            condition, empty_targets, _ = no_target_branch
            checks.require("Count Of(Event Player.DaftarTargetBalasDendam) == 0" in condition,
                           "renderer Revenge non identifica il ramo no-target")
            for instruction in MENU_CROUCH_INSTRUCTIONS:
                checks.require(
                    instruction in empty_targets,
                    f"Revenge no-target senza istruzione Crouch: {instruction}",
                )

    checks.require("Append To Array(Event Player.HudMenu" not in source,
                   "HudMenu non deve diventare un array di handle")
    checks.require("HudMenuArcade" not in source and "PramuatSubmenu" not in source,
                   "preload/array di HUD menu ancora presente")
    for rule in rules:
        if ("Button(Primary Fire)" in rule.body or "Button(Secondary Fire)" in rule.body) and "PerintahMenu" in rule.body and event_type(rule) != "Subroutine":
            checks.require("Create HUD Text(" not in rule.body and "Destroy HUD Text(" not in rule.body,
                           f"{rule.name}: Primary/Secondary non devono ricreare HUD")

    router = rule_by_subroutine(rules, "GambarHalamanAktif")
    checks.require(router is not None, "subroutine router pagine assente")
    if router:
        for page in range(12):
            checks.require(re.search(rf"HalamanMenu\s*==\s*{page}\b", router.body) is not None,
                           f"router menu non copre pagina {page}")

    checks.require(PAGE_APPLY_SUBROUTINES <= subroutines,
                   "dispatcher Interact non suddiviso nelle 12 subroutine pagina")
    for name in sorted(PAGE_APPLY_SUBROUTINES):
        rule = rule_by_subroutine(rules, name)
        if rule:
            checks.require(not wait_calls(rule.body) and action_loop_count(rule.body) == 0,
                           f"{name}: handler pagina deve essere senza Wait/Loop")
            checks.require("Create HUD Text(" not in rule.body and "Destroy HUD Text(" not in rule.body,
                           f"{name}: applicare una preferenza non deve ricreare HUD")


def validate_input_contract(checks: Checks, rules: list[Rule]) -> None:
    menu_toggle = next((rule for rule in rules if "Button(Melee)" in rule.body and "Wait(0.500, Abort When False)" in rule.body and "MenuTerbuka" in rule.body), None)
    checks.require(menu_toggle is not None, "hold Melee 0,5 s per apertura/chiusura menu assente")
    if menu_toggle:
        checks.equal(event_type(menu_toggle), "Ongoing - Each Player", "hold Melee: evento")

    dispatcher = next((rule for rule in rules if event_type(rule) == "Ongoing - Each Player" and "PerintahMenu" in rule.body and all(f"Button({button})" in rule.body for button in MENU_ACTION_BUTTONS)), None)
    checks.require(dispatcher is not None, "dispatcher input menu completo assente")
    if dispatcher:
        checks.require("Is Button Held(Event Player, Button(Crouch)) == True;" in dispatcher.body,
                       "azioni menu non protette dal modificatore Crouch")
        checks.require("Is Alive(Event Player) == True;" in dispatcher.body,
                       "menu morto non è congelato")
        checks.require("Event Player.InteraksiKameraDipakai == False;" in dispatcher.body,
                       "dispatcher menu non blocca Interact già consumato dalla Camera")
        interact_branch = re.search(
            r"If\(Is Button Held\(Event Player, Button\(Interact\)\)\);(.*?)Else If",
            dispatcher.body,
            re.DOTALL,
        )
        checks.require(interact_branch is not None, "ramo Interact del dispatcher menu assente")
        if interact_branch:
            checks.require("Event Player.PerintahMenu = 1;" in interact_branch.group(1),
                           "ramo Interact del dispatcher non seleziona PerintahMenu 1")
            checks.require("Event Player.InteraksiKameraDipakai = True;" in interact_branch.group(1),
                           "ramo Interact del dispatcher non acquisisce il latch Camera")

    lock_rule = next((rule for rule in rules if "Disallow Button(Event Player" in rule.body and "InputMenuDikunci" in rule.body), None)
    unlock_rule = next((rule for rule in rules if "Allow Button(Event Player" in rule.body and "InputMenuDikunci" in rule.body and "Crouch" in rule.body), None)
    checks.require(lock_rule is not None and unlock_rule is not None, "coppia lock/unlock input menu assente")
    if lock_rule and unlock_rule:
        disallowed = set(re.findall(r"Disallow Button\(Event Player, Button\(([^)]+)\)\);", lock_rule.body))
        allowed = set(re.findall(r"Allow Button\(Event Player, Button\(([^)]+)\)\);", unlock_rule.body))
        checks.require(MENU_ACTION_BUTTONS <= disallowed, "lock Crouch non cattura tutti gli input menu")
        checks.equal(disallowed, allowed, "simmetria Disallow/Allow input menu")
        checks.require(not (NATIVE_BUTTONS & disallowed), "Melee, Jump e Crouch non devono essere bloccati")

    camera = next((rule for rule in rules if "Button(Interact)" in rule.body and "Wait(0.500, Abort When False)" in rule.body and "ModeKamera" in rule.body), None)
    checks.require(camera is not None, "hold Interact 0,5 s camera assente")
    if camera:
        checks.require("MenuTerbuka" not in mask_strings(camera.body),
                       "camera Interact non deve dipendere dallo stato aperto/chiuso del menu")
        checks.require("Is Button Held(Event Player, Button(Crouch)) == False;" in camera.body,
                       "camera Interact interferisce con il modificatore Crouch")
        checks.require("Event Player.InteraksiKameraDipakai == False;" in camera.body,
                       "camera Interact non verifica il latch condiviso col menu")
        checks.require("Event Player.InteraksiKameraDipakai = True;" in camera.body,
                       "camera Interact non acquisisce il latch dopo il hold")
        if dispatcher:
            checks.require(camera.start != dispatcher.start,
                           "camera hold e dispatcher Crouch+Interact non devono condividere la stessa regola")

    camera_release = next(
        (
            rule for rule in rules
            if event_type(rule) == "Ongoing - Each Player"
            and "Event Player.InteraksiKameraDipakai == True;" in rule.body
            and "Is Button Held(Event Player, Button(Interact)) == False;" in rule.body
            and "Event Player.InteraksiKameraDipakai = False;" in rule.body
        ),
        None,
    )
    checks.require(camera_release is not None,
                   "rilascio Interact non azzera il latch condiviso menu/Camera")

    crouch_features = [rule for rule in rules if event_type(rule) == "Ongoing - Each Player" and "Button(Crouch)" in rule.body and ("InspeksiAktif = True" in rule.body or "TeleportasiJongkokAktif = True" in rule.body)]
    checks.require(bool(crouch_features), "inspection/teleport Crouch assenti")
    for rule in crouch_features:
        checks.require("Event Player.MenuTerbuka == False;" in rule.body,
                       f"{rule.name}: Crouch inspection/teleport deve essere disattivato col menu")

    for rule in rules_with_event(rules, "Player Died"):
        checks.require("Call Subroutine(TutupMenu);" not in rule.body,
                       f"{rule.name}: la morte non deve chiudere il menu")
        checks.require("Destroy HUD Text(Event Player.HudMenu);" not in rule.body,
                       f"{rule.name}: la morte non deve nascondere il menu")
    respawn = next((rule for rule in rules if "Respawn(Event Player)" in rule.body and "Button(Jump)" in rule.body), None)
    checks.require(respawn is not None, "respawn da morto con Jump assente")
    if respawn:
        checks.require("MenuTerbuka == False" not in respawn.body,
                       "Jump respawn deve funzionare anche col menu visibile")


def validate_scheduler(checks: Checks, source: str, rules: list[Rule], globals_: set[str], subroutines: set[str]) -> None:
    masked = mask_strings(source)
    checks.equal(action_loop_count(source), 1, "numero Loop Workshop")
    scheduler_candidates = [rule for rule in rules if action_loop_count(rule.body) == 1]
    checks.equal(len(scheduler_candidates), 1, "scheduler periodico unico")
    scheduler = scheduler_candidates[0] if len(scheduler_candidates) == 1 else None
    checks.require("LangkahPenjadwal" in globals_, "contatore scheduler LangkahPenjadwal assente")
    if scheduler:
        checks.equal(event_type(scheduler), "Ongoing - Global", "scheduler 20 Hz: evento")
        checks.require("Wait(0.050, Ignore Condition);" in scheduler.body,
                       "scheduler non gira a 20 Hz")
        checks.require("Global.LangkahPenjadwal" in scheduler.body,
                       "scheduler non incrementa LangkahPenjadwal")
        for name in sorted(SCHEDULER_SUBROUTINES):
            checks.require(f"Call Subroutine({name});" in scheduler.body,
                           f"scheduler non chiama {name}")
        for cadence in (2, 20):
            checks.require(re.search(rf"LangkahPenjadwal\s*%\s*{cadence}\b", scheduler.body) is not None,
                           f"cadenza scheduler %{cadence} assente")
        checks.require("Global.LangkahPenjadwal == 0" in scheduler.body,
                       "cadenza scheduler 10 secondi assente")

    waits = wait_calls(source)
    checks.require(len(waits) <= 11, f"Wait oltre il massimo consentito: {len(waits)} > 11")
    for rule in rules:
        calls = wait_calls(rule.body)
        if not calls:
            continue
        checks.require(wait_role(rule, scheduler) is not None, f"Wait non allowlisted in regola: {rule.name}")
    for rule in rules:
        for span in for_spans(rule):
            checks.require("Wait(" not in mask_strings(span),
                           f"{rule.name}: yield durante scansione For")

    for name in sorted(SCHEDULER_SUBROUTINES):
        checks.require(name in subroutines, f"subroutine scheduler assente: {name}")
        rule = rule_by_subroutine(rules, name)
        if rule:
            checks.require(not wait_calls(rule.body) and action_loop_count(rule.body) == 0,
                           f"{name}: subroutine scheduler deve essere senza Wait/Loop")

    if scheduler:
        for rule in rules:
            if rule.start == scheduler.start:
                continue
            writes_active = re.findall(r"Global\.PemainAktif\s*=(?!=)\s*([^;]+);", mask_strings(rule.body))
            checks.require(not writes_active or (writes_active == ["Null"] and "Global.Siap = True;" in rule.body),
                           f"{rule.name}: scrittura PemainAktif fuori dallo scheduler")
            checks.require("For Global Variable(IndeksPemainGlobal" not in rule.body,
                           f"{rule.name}: IndeksPemainGlobal posseduto solo dallo scheduler")
    checks.require("For Global Variable(Global." not in masked,
                   "sintassi For Global Variable(Global.*) non valida")


def validate_try_your_luck(checks: Checks, source: str, rules: list[Rule], players: set[str]) -> None:
    for name in sorted(LUCK_TIMESTAMP_VARIABLES):
        checks.require(name in players, f"timestamp Try Your Luck assente: {name}")
    checks.require(re.search(r"EfekNasib\s*=\s*Random Integer\(1,\s*6\)", source) is not None or
                   "Set Player Variable(Event Player, EfekNasib, Random Integer(1, 6));" in source,
                   "Try Your Luck non estrae esattamente sei esiti")
    for outcome in range(1, 6):
        checks.require(re.search(rf"EfekNasib\s*==\s*{outcome}\b", source) is not None,
                       f"Try Your Luck esito {outcome} assente")
    checks.require("Else;" in (rule_by_subroutine(rules, "ProsesNasibPemain") or Rule("", "", 0, 0)).body,
                   "Try Your Luck esito 6/fallback assente")
    for token, label in (
        ("Start Accelerating(", "accelerazione 10 s"),
        ("Burning", "Burning 10 s"),
        ("Hacked", "Hacked 5 s"),
        ("PrivasiNasibAktif", "Vision 15 s"),
    ):
        checks.require(token in source, f"Try Your Luck esito mancante: {label}")
    checks.require("Clear Status(Event Player, Unkillable);" in source,
                   "Try Your Luck non disattiva Unkillable all'avvio")
    checks.require("Start Forcing Player Position(" not in source,
                   "Try Your Luck non deve forzare la posizione")
    checks.require("Custom String(\"□\")" not in source,
                   "Try Your Luck non deve creare una carta testuale")
    for rule in rules:
        if any(token in rule.body for token in ("KartuNasibAktif", "PutaranKartuNasib", "EfekNasib")):
            checks.require(action_loop_count(rule.body) == 0,
                           f"{rule.name}: Try Your Luck deve essere a stati, senza Loop")
            if subroutine_target(rule) == "ProsesNasibPemain":
                checks.require(not wait_calls(rule.body), "ProsesNasibPemain deve usare timestamp, non Wait")
    state_machine = rule_by_subroutine(rules, "ProsesNasibPemain")
    checks.require(state_machine is not None, "macchina a stati ProsesNasibPemain assente")
    if state_machine:
        masked_state_machine = mask_strings(state_machine.body)

        def if_block_containing(condition_fragment: str) -> str | None:
            condition_position = masked_state_machine.find(condition_fragment)
            if condition_position < 0:
                return None
            starts = list(re.finditer(r"(?m)^\s*If\(", masked_state_machine[:condition_position]))
            if not starts:
                return None
            start = starts[-1].start()
            depth = 0
            offset = start
            for line in masked_state_machine[start:].splitlines(keepends=True):
                stripped = line.strip()
                if stripped.startswith("If("):
                    depth += 1
                elif stripped == "End;":
                    depth -= 1
                    if depth == 0:
                        return state_machine.body[start:offset + len(line)]
                offset += len(line)
            return None

        roulette_icons = list(iter_calls(state_machine.body, "Create Icon"))
        checks.equal(len(roulette_icons), 6, "numero icone dei sei esiti roulette")
        expected_icon_types = ("Eye", "Dizzy", "Skull", "Heart", "Fire", "Poison 2")
        actual_icon_types: list[str] = []
        for index, icon in enumerate(roulette_icons, start=1):
            checks.require(len(icon.args) >= 6, f"icona roulette {index} malformata")
            if len(icon.args) >= 6:
                actual_icon_types.append(icon.args[2].strip())
                checks.equal(icon.args[0].strip(), "Global.PemainManusia",
                             f"icona roulette {index}: visibilità riservata agli umani")
                dynamic_positions = list(iter_calls(icon.args[1], "Update Every Frame"))
                checks.equal(len(dynamic_positions), 1,
                             f"icona roulette {index}: posizione fluida Update Every Frame")
                dynamic_position = dynamic_positions[0] if len(dynamic_positions) == 1 else None
                if dynamic_position:
                    checks.equal(dynamic_position.raw.strip(), icon.args[1].strip(),
                                 f"icona roulette {index}: Update Every Frame deve racchiudere tutta la posizione")
                    captures = list(iter_calls(dynamic_position.args[0], "Evaluate Once")) if dynamic_position.args else []
                    checks.equal(len(captures), 2,
                                 f"icona roulette {index}: catture identità player")
                    for capture in captures:
                        checks.equal(
                            tuple(argument.strip() for argument in capture.args),
                            ("Global.PemainAktif",),
                            f"icona roulette {index}: Evaluate Once deve catturare Global.PemainAktif",
                        )
                    compact_position = re.sub(r"\s+", "", dynamic_position.args[0]) if dynamic_position.args else ""
                    expected_position = (
                        "EyePosition(EvaluateOnce(Global.PemainAktif))+"
                        "FacingDirectionOf(EvaluateOnce(Global.PemainAktif))*4"
                    )
                    checks.equal(compact_position, expected_position,
                                 f"icona roulette {index}: ancoraggio fluido a occhio e mirino del beneficiario")
                    uncaptured = re.sub(
                        r"Evaluate\s+Once\(\s*Global\.PemainAktif\s*\)",
                        "",
                        dynamic_position.args[0] if dynamic_position.args else "",
                    )
                    checks.require("Global.PemainAktif" not in uncaptured,
                                   f"icona roulette {index}: scratch Global.PemainAktif dinamico senza Evaluate Once")
                checks.equal(icon.args[3].strip(), "Position",
                             f"icona roulette {index}: reevaluation deve essere Position")
                checks.equal(icon.args[5].strip(), "True",
                             f"icona roulette {index}: Show When Offscreen deve essere True")
        checks.equal(tuple(actual_icon_types), expected_icon_types,
                     "ordine tipi icona per esiti roulette 1..6")
        checks.equal(len(actual_icon_types), len(set(actual_icon_types)),
                     "icone roulette univoche per i sei esiti")

        rolling_block = if_block_containing("Global.PemainAktif.PutaranKartuNasib > 0")
        checks.require(rolling_block is not None, "blocco sostituzione icona roulette non analizzabile")
        if rolling_block:
            rolling_masked = mask_strings(rolling_block)
            rolling_icons = list(iter_calls(rolling_block, "Create Icon"))
            rolling_destroys = list(iter_calls(rolling_block, "Destroy Icon"))
            checks.equal(len(rolling_icons), 6, "icone create nel blocco di sostituzione roulette")
            checks.equal(len(rolling_destroys), 1, "destroy-before-replace icona roulette")
            if rolling_icons and len(rolling_destroys) == 1:
                checks.equal(
                    tuple(argument.strip() for argument in rolling_destroys[0].args),
                    ("Global.PemainAktif.IkonKartuNasib",),
                    "destroy-before-replace usa l'handle roulette corrente",
                )
                checks.require(rolling_destroys[0].end < rolling_icons[0].start,
                               "handle roulette distrutto dopo la creazione sostitutiva")
                guard_position = rolling_masked.find("If(Global.PemainAktif.IkonKartuNasib != Null);")
                checks.require(0 <= guard_position < rolling_destroys[0].start,
                               "destroy-before-replace icona roulette non protetto da handle non-Null")
            store_token = "Global.PemainAktif.IkonKartuNasib = Last Created Entity;"
            checks.equal(rolling_masked.count(store_token), 1,
                         "salvataggio handle della nuova icona roulette")
            store_position = rolling_masked.find(store_token)
            if rolling_icons and store_position >= 0:
                between_create_and_store = mask_strings(rolling_block[rolling_icons[-1].end:store_position])
                checks.require(
                    re.fullmatch(r"\s*;\s*End;\s*", between_create_and_store) is not None,
                    "handle roulette non salvato immediatamente dopo la creazione",
                )

        player_bound_roulette_rules = [
            rule for rule in rules
            if event_type(rule) == "Ongoing - Each Player"
            and ("IkonKartuNasib" in rule.body or "EfekNasib" in rule.body)
            and ("Create Icon(" in rule.body or "Start Accelerating(" in rule.body)
        ]
        checks.require(not player_bound_roulette_rules,
                       "icone/accelerazione roulette devono restare global-first, senza regole Each Player")

        global_acceleration_calls = list(iter_calls(source, "Start Accelerating"))
        checks.equal(len(global_acceleration_calls), 1, "Start Accelerating globale unico")
        acceleration_calls = list(iter_calls(state_machine.body, "Start Accelerating"))
        checks.equal(len(acceleration_calls), 1, "accelerazione Try Your Luck unica")
        if len(acceleration_calls) == 1:
            acceleration = acceleration_calls[0]
            checks.equal(len(acceleration.args), 6, "accelerazione Try Your Luck: numero argomenti")
            if len(acceleration.args) == 6:
                expected_acceleration = (
                    "Global.PemainAktif",
                    "FacingDirectionOf(EvaluateOnce(Global.PemainAktif))",
                    "50",
                    "25",
                    "ToWorld",
                    "DirectionRateandMaxSpeed",
                )
                compact_acceleration = tuple(re.sub(r"\s+", "", argument) for argument in acceleration.args)
                checks.equal(compact_acceleration, expected_acceleration,
                             "accelerazione automatica 3D nella Facing Direction del beneficiario")
                uncaptured_direction = re.sub(
                    r"Evaluate\s+Once\(\s*Global\.PemainAktif\s*\)",
                    "",
                    acceleration.args[1],
                )
                checks.require("Global.PemainAktif" not in uncaptured_direction,
                               "direzione accelerazione usa scratch Global.PemainAktif senza Evaluate Once")

            branch_start = state_machine.body.rfind(
                "Else If(Global.PemainAktif.EfekNasib == 2);", 0, acceleration.start
            )
            branch_end = state_machine.body.find(
                "Else If(Global.PemainAktif.EfekNasib == 3);", acceleration.end
            )
            checks.require(branch_start >= 0 and branch_end > branch_start,
                           "ramo esito 2 dell'accelerazione non analizzabile")
            if branch_start >= 0 and branch_end > branch_start:
                acceleration_branch = state_machine.body[branch_start:branch_end]
                acceleration_branch_masked = mask_strings(acceleration_branch)
                checks.require("Set Move Speed(Global.PemainAktif, 1000);" in acceleration_branch_masked,
                               "accelerazione esito 2 non imposta Move Speed 1000")
                checks.require(
                    "Global.PemainAktif.EfekNasibBerakhir = Total Time Elapsed + 10;" in acceleration_branch_masked,
                    "accelerazione esito 2 non usa timestamp esatto di 10 secondi",
                )
                for forbidden_input in ("Throttle Of(", "Is Button Held(", "Button(", "Apply Impulse("):
                    checks.require(forbidden_input not in acceleration_branch_masked,
                                   f"accelerazione esito 2 dipende da input/impulsi: {forbidden_input}")

        checks.require("Apply Impulse(" not in mask_strings(state_machine.body),
                       "Try Your Luck non deve simulare l'accelerazione con Apply Impulse")
        checks.require("AkselerasiNasibAktif" not in mask_strings(source),
                       "accelerazione global-first non richiede latch/player variable dedicata")

        expiry_cleanup = if_block_containing("Total Time Elapsed >= Global.PemainAktif.EfekNasibBerakhir")
        checks.require(expiry_cleanup is not None, "cleanup timestamp Try Your Luck non analizzabile")
        if expiry_cleanup:
            expiry_cleanup_masked = mask_strings(expiry_cleanup)
            for token, label in (
                ("Stop Accelerating(Global.PemainAktif);", "Stop Accelerating"),
                ("Set Move Speed(Global.PemainAktif, 100);", "ripristino Move Speed 100"),
                ("Global.PemainAktif.EfekNasib = 0;", "reset effetto"),
                ("Global.PemainAktif.EfekNasibBerakhir = 0;", "reset timestamp"),
            ):
                checks.require(token in expiry_cleanup_masked,
                               f"cleanup scadenza accelerazione incompleto: {label}")

        final_icon_cleanup = if_block_containing("Global.PemainAktif.WaktuIkonNasibBerakhir > 0")
        checks.require(final_icon_cleanup is not None, "cleanup finale handle icona roulette non analizzabile")
        if final_icon_cleanup:
            final_icon_cleanup_masked = mask_strings(final_icon_cleanup)
            destroy_token = "Destroy Icon(Global.PemainAktif.IkonKartuNasib);"
            null_token = "Global.PemainAktif.IkonKartuNasib = Null;"
            timer_token = "Global.PemainAktif.WaktuIkonNasibBerakhir = 0;"
            for token, label in (
                (destroy_token, "Destroy Icon"),
                (null_token, "azzeramento handle"),
                (timer_token, "azzeramento timer"),
            ):
                checks.require(token in final_icon_cleanup_masked,
                               f"cleanup finale icona roulette incompleto: {label}")
            if destroy_token in final_icon_cleanup_masked and null_token in final_icon_cleanup_masked:
                checks.require(final_icon_cleanup_masked.index(destroy_token) < final_icon_cleanup_masked.index(null_token),
                               "cleanup finale azzera handle roulette prima di distruggerlo")

        death_cleanup = next(
            (rule for rule in rules_with_event(rules, "Player Died") if "KartuNasibAktif" in rule.body),
            None,
        )
        checks.require(death_cleanup is not None, "cleanup accelerazione alla morte assente")
        for cleanup_rule, label in (
            (death_cleanup, "morte"),
            (rule_by_subroutine(rules, "TenangkanPemain"), "quiete lifecycle"),
            (rule_by_subroutine(rules, "BersihkanPemain"), "cleanup lifecycle"),
        ):
            checks.require(cleanup_rule is not None, f"cleanup accelerazione {label} assente")
            if cleanup_rule:
                cleanup_masked = mask_strings(cleanup_rule.body)
                checks.require("Stop Accelerating(Event Player);" in cleanup_masked,
                               f"cleanup accelerazione {label}: Stop Accelerating assente")
                checks.require("Set Move Speed(Event Player, 100);" in cleanup_masked,
                               f"cleanup accelerazione {label}: Move Speed 100 assente")
                destroy_icon = "Destroy Icon(Event Player.IkonKartuNasib);"
                null_icon = "Event Player.IkonKartuNasib = Null;"
                checks.require(destroy_icon in cleanup_masked,
                               f"cleanup icona roulette {label}: Destroy Icon assente")
                checks.require(null_icon in cleanup_masked,
                               f"cleanup icona roulette {label}: azzeramento handle assente")
                if destroy_icon in cleanup_masked and null_icon in cleanup_masked:
                    checks.require(cleanup_masked.index(destroy_icon) < cleanup_masked.index(null_icon),
                                   f"cleanup icona roulette {label}: handle azzerato prima del destroy")

        health_calls = [
            call for call in iter_calls(state_machine.body, "Set Player Health")
            if len(call.args) >= 2 and call.args[1].strip() == "9999"
        ]
        checks.equal(len(health_calls), 1, "cura completa team della roulette")
        def human_recipient(expression: str) -> bool:
            return "Global.PemainManusia" in expression or re.search(
                r"Filtered Array\(.*?Player Variable\(Current Array Element,\s*Manusia\)\s*==\s*True",
                expression,
                re.DOTALL,
            ) is not None
        if health_calls:
            checks.require(human_recipient(health_calls[0].args[0]),
                           "Heart roulette cura anche bot/dummy invece dei soli umani")
        heart_messages = [
            call for call in iter_calls(state_machine.body, "Small Message")
            if len(call.args) >= 2 and "HEART" in call.args[1]
        ]
        checks.equal(len(heart_messages), 1, "messaggio Heart roulette")
        if heart_messages:
            checks.require(human_recipient(heart_messages[0].args[0]),
                           "Heart roulette invia HUD anche a bot/dummy")

        checks.equal(
            state_machine.body.count("Kill(Global.PemainAktif, Null);"),
            1,
            "Skull deve uccidere esattamente Global.PemainAktif nella macchina Coba Nasib",
        )
        checks.require("Total Time Elapsed" in state_machine.body,
                       "macchina Try Your Luck non confronta timestamp")
    for duration in (15, 10, 5):
        checks.require(re.search(rf"(?:Total Time Elapsed\s*\+\s*{duration}\b|(?:Burning|Hacked),\s*{duration}\))", source) is not None,
                       f"durata Try Your Luck {duration} s assente")


def validate_lifecycle(checks: Checks, rules: list[Rule], subroutines: set[str]) -> None:
    checks.require(LIFECYCLE_SUBROUTINES <= subroutines,
                   "subroutine lifecycle Siapkan/Tenangkan/Bersihkan incomplete")
    joined = rules_with_event(rules, "Player Joined Match")
    left = rules_with_event(rules, "Player Left Match")
    checks.equal(len(joined), 1, "regola Player Joined Match unica")
    checks.equal(len(left), 1, "regola Player Left Match unica")
    if joined:
        body = joined[0].body
        for token in ("Event Player.PindahTimDiproses == False;", "SiklusPemainAktif", "Array Contains(Global.PemainManusia, Event Player)"):
            checks.require(token in body, f"join/team switch senza guardia duplicati: {token}")
        for name in ("TenangkanPemain", "BersihkanPemain", "SiapkanPemain"):
            checks.require(f"Call Subroutine({name});" in body, f"join/team switch non chiama {name}")
    if left:
        body = left[0].body
        checks.require("Call Subroutine(TenangkanPemain);" in body and "Call Subroutine(BersihkanPemain);" in body,
                       "leave non esegue quiete + cleanup")
    classifier = next((rule for rule in rules if "Append To Array(Global.PemainManusia, Event Player)" in rule.body), None)
    checks.require(classifier is not None, "registrazione roster umano assente")
    if classifier:
        checks.require("Abort If(Array Contains(Global.PemainManusia, Event Player));" in classifier.body,
                       "join duplicato può aggiungere due volte il roster")

    setup = rule_by_subroutine(rules, "SiapkanPemain")
    checks.require(setup is not None, "SiapkanPemain assente")
    if setup:
        reset_tokens = (
            "IndeksGenre = -1;", "ModeKamera = 0;", "IndeksWarna = 0;", "IndeksBahasa = 0;",
            "PemainDipilih = Null;", "ModeKebal = 0;", "IndeksSuara = 0;", "IndeksIkon = 0;",
            "TeleportasiJongkokDiaktifkan = False;", "PrivasiInspeksiAktif = True;",
            "KursorPrivasiInspeksi = 1;",
            "KartuNasibAktif = False;", "HudMenu = Null;",
        )
        for token in reset_tokens:
            checks.require(token in setup.body, f"reset completo cambio squadra mancante: {token}")
    quiet = rule_by_subroutine(rules, "TenangkanPemain")
    cleanup = rule_by_subroutine(rules, "BersihkanPemain")
    if quiet:
        checks.require(not wait_calls(quiet.body) and action_loop_count(quiet.body) == 0,
                       "TenangkanPemain deve essere atomica e senza Wait/Loop")
    if cleanup:
        critical = cleanup.body[cleanup.body.find("Global.IndeksKeluar ="):]
        checks.require("Wait(" not in critical,
                       "cleanup usa Wait dopo l'acquisizione scratch Global")
        checks.require("Remove From Array By Index" in critical,
                       "cleanup non compatta roster/handle paralleli")

    cycle = rule_by_subroutine(rules, "ProsesSiklusPemain")
    checks.require(cycle is not None, "ProsesSiklusPemain assente")
    if setup:
        checks.require("Event Player.PindahTimDiproses = False;" not in setup.body,
                       "SiapkanPemain rilascia troppo presto il lock team-switch")
    if cycle:
        human_stable = (
            r"Global\.PemainAktif\.Manusia\s*==\s*True.*?"
            r"Has Spawned\(\s*Global\.PemainAktif\s*\)\s*==\s*True.*?"
            r"Global\.PemainAktif\.HudPemainDibuat\s*==\s*True"
        )
        bot_stable = (
            r"Global\.PemainAktif\.BotOtomatis\s*==\s*True.*?"
            r"Global\.PemainAktif\.SudahDiperiksa\s*==\s*True.*?"
            r"Has Spawned\(\s*Global\.PemainAktif\s*\)\s*==\s*True.*?"
            r"Is Alive\(\s*Global\.PemainAktif\s*\)\s*==\s*True.*?"
            r"Global\.PemainAktif\.KunciBotAktif\s*==\s*True"
        )
        stable_patterns = (
            (r"Global\.PemainAktif\.PindahTimDiproses\s*==\s*True", "PindahTimDiproses == True"),
            (human_stable, "registrazione umana Manusia/Spawn/HUD"),
            (bot_stable, "registrazione bot BotOtomatis/SudahDiperiksa/Spawn/Alive/KunciBotAktif"),
            (r"Global\.PemainAktif\.PindahTimDiproses\s*=\s*False;", "rilascio PindahTimDiproses"),
        )
        for pattern, label in stable_patterns:
            checks.require(re.search(pattern, cycle.body, re.DOTALL) is not None,
                           f"rilascio stabile lock team-switch incompleto: {label}")


def validate_privacy(checks: Checks, rules: list[Rule]) -> None:
    setup = rule_by_subroutine(rules, "SiapkanPemain")
    checks.require(setup is not None, "SiapkanPemain assente per default privacy")
    if setup:
        checks.require("Event Player.PrivasiInspeksiAktif = True;" in setup.body,
                       "Privacy deve essere ON di default per ogni umano")
        checks.require("Event Player.KursorPrivasiInspeksi = 1;" in setup.body,
                       "cursore Privacy deve iniziare su ON (1)")

    privacy_filter_tokens = (
        "Is Dummy Bot(Current Array Element) == True",
        "Player Variable(Current Array Element, BotOtomatis) == True",
        "Player Variable(Current Array Element, Manusia) == True",
        "Player Variable(Current Array Element, PrivasiInspeksiAktif) == False",
    )
    human_public_pattern_text = (
        r"And\(\s*Player Variable\(\s*Current Array Element\s*,\s*Manusia\)\s*==\s*True\s*,\s*"
        r"Player Variable\(\s*Current Array Element\s*,\s*PrivasiInspeksiAktif\)\s*==\s*False\s*\)"
    )
    human_public_pattern = re.compile(human_public_pattern_text, re.DOTALL)
    public_target_pattern = re.compile(
        r"Or\(\s*Is Dummy Bot\(Current Array Element\)\s*==\s*True\s*,\s*"
        r"Or\(\s*Player Variable\(\s*Current Array Element\s*,\s*BotOtomatis\)\s*==\s*True\s*,\s*"
        + human_public_pattern_text
        + r"\s*\)\s*\)",
        re.DOTALL,
    )
    vision_target_pattern = re.compile(
        r"Or\(\s*Is Dummy Bot\(Current Array Element\)\s*==\s*True\s*,\s*"
        r"Or\(\s*Player Variable\(\s*Current Array Element\s*,\s*BotOtomatis\)\s*==\s*True\s*,\s*"
        r"Or\(\s*Event Player\.PrivasiNasibAktif\s*==\s*True\s*,\s*"
        + human_public_pattern_text
        + r"\s*\)\s*\)\s*\)",
        re.DOTALL,
    )

    privacy_false_pattern = re.compile(
        r"Player Variable\(\s*Current Array Element\s*,\s*PrivasiInspeksiAktif\)\s*==\s*False",
        re.DOTALL,
    )
    privacy_read_total = 0
    parsed_privacy_filter_total = 0
    for rule in rules:
        privacy_reads = len(privacy_false_pattern.findall(rule.body))
        if privacy_reads:
            privacy_read_total += privacy_reads
            checks.equal(
                len(human_public_pattern.findall(rule.body)),
                privacy_reads,
                f"{rule.name}: ogni Privacy OFF target richiede Manusia=True",
            )
            parsed_filters = [
                call for call in iter_calls(rule.body, "Filtered Array")
                if privacy_false_pattern.search(call.raw) is not None
            ]
            parsed_privacy_filter_total += len(parsed_filters)
            checks.equal(
                len(parsed_filters),
                privacy_reads,
                f"{rule.name}: filtro Privacy non analizzabile come chiamata bilanciata",
            )
    checks.equal(privacy_read_total, 6, "numero filtri Privacy target-aware")
    checks.equal(parsed_privacy_filter_total, 6, "filtri Privacy strutturalmente analizzabili")
    camera_targets = rule_by_subroutine(rules, "SegarkanTargetKamera")
    checks.require(camera_targets is not None, "SegarkanTargetKamera assente per filtro Privacy")
    if camera_targets:
        checks.require("Filtered Array(" in camera_targets.body,
                       "lista target Camera non usa un filtro")
        for token in privacy_filter_tokens:
            checks.require(token in camera_targets.body,
                           f"lista target Camera non esclude umani privati: {token}")
        checks.require(public_target_pattern.search(camera_targets.body) is not None,
                       "lista target Camera non usa Dummy OR iBot OR (umano AND Privacy OFF)")

    cache = rule_by_subroutine(rules, "ProsesCachePemain")
    checks.require(cache is not None, "ProsesCachePemain assente per cache Camera")
    if cache:
        for token in privacy_filter_tokens:
            checks.require(token in cache.body,
                           f"cache target Camera non esclude umani privati: {token}")
        checks.require(public_target_pattern.search(cache.body) is not None,
                       "cache target Camera non usa Dummy OR iBot OR (umano AND Privacy OFF)")

    inspection_refresh = rule_by_subroutine(rules, "SegarkanTargetInspeksi")
    checks.require(inspection_refresh is not None, "SegarkanTargetInspeksi assente per filtro Privacy")
    if inspection_refresh:
        checks.require(vision_target_pattern.search(inspection_refresh.body) is not None,
                       "inspection non usa Dummy OR iBot OR Vision OR (umano AND Privacy OFF)")

    inspection_live = next(
        (
            rule for rule in rules
            if event_type(rule) == "Ongoing - Each Player"
            and "Event Player.TargetInspeksi != First Of(Sorted Array(Filtered Array(" in rule.body
        ),
        None,
    )
    checks.require(inspection_live is not None, "aggiornamento live inspection assente")
    if inspection_live:
        checks.require(vision_target_pattern.search(inspection_live.body) is not None,
                       "inspection live non usa Dummy OR iBot OR Vision OR (umano AND Privacy OFF)")

    teleport_refresh = rule_by_subroutine(rules, "SegarkanTargetTeleportasi")
    checks.require(teleport_refresh is not None, "SegarkanTargetTeleportasi assente per filtro Privacy")
    if teleport_refresh:
        checks.require(public_target_pattern.search(teleport_refresh.body) is not None,
                       "teleport non usa Dummy OR iBot OR (umano AND Privacy OFF)")

    teleport_live = next(
        (
            rule for rule in rules
            if event_type(rule) == "Ongoing - Each Player"
            and "Event Player.CalonTargetTeleportasi != First Of(Sorted Array(Filtered Array(" in rule.body
        ),
        None,
    )
    checks.require(teleport_live is not None, "aggiornamento live teleport assente")
    if teleport_live:
        checks.require(public_target_pattern.search(teleport_live.body) is not None,
                       "teleport live non usa Dummy OR iBot OR (umano AND Privacy OFF)")

    cycle = rule_by_subroutine(rules, "ProsesSiklusPemain")
    checks.require(cycle is not None, "ProsesSiklusPemain assente per stop osservatore Privacy")
    if cycle:
        privacy_guard = re.search(
            r"Global\.PemainAktif\.ModeKamera\s*==\s*2.*?"
            r"Global\.PemainAktif\.TargetKamera\.Manusia\s*==\s*True.*?"
            r"Global\.PemainAktif\.TargetKamera\.PrivasiInspeksiAktif\s*==\s*True.*?"
            r"Stop Camera\(Global\.PemainAktif\);",
            cycle.body,
            re.DOTALL,
        )
        checks.require(privacy_guard is not None,
                       "osservatore attivo non viene fermato quando il target umano abilita Privacy")
        mode_reset = (
            "Set Player Variable(Global.PemainAktif, ModeKamera, 0);" in cycle.body
            or "Global.PemainAktif.ModeKamera = 0;" in cycle.body
        )
        target_reset = (
            "Set Player Variable(Global.PemainAktif, TargetKamera, Null);" in cycle.body
            or "Global.PemainAktif.TargetKamera = Null;" in cycle.body
        )
        checks.require(mode_reset and target_reset,
                       "stop osservatore Privacy non ripristina ModeKamera e TargetKamera")


def validate_bot_isolation(checks: Checks, rules: list[Rule]) -> None:
    def require_human_guards(rule: Rule | None, label: str, *, triple: bool) -> None:
        checks.require(rule is not None, f"entrypoint umano assente: {label}")
        if not rule:
            return
        tokens = ["Event Player.Manusia == True;"]
        if triple:
            tokens.extend((
                "Event Player.BotOtomatis == False;",
                "Is Dummy Bot(Event Player) == False;",
            ))
        for token in tokens:
            checks.require(token in rule.body, f"{label} non isola bot/dummy: {token}")

    classifier = next(
        (
            rule for rule in rules
            if event_type(rule) == "Ongoing - Each Player"
            and "Start Forcing Dummy Bot Name(Event Player" in rule.body
            and "Append To Array(Global.PemainManusia, Event Player)" in rule.body
        ),
        None,
    )
    bot_abort = None
    checks.require(classifier is not None, "classificatore dedicato umano/iBot assente")
    if classifier:
        checks.require("Is Dummy Bot(Event Player) == False;" in classifier.body,
                       "classificatore umano/iBot non esclude i dummy nativi")
        bot_abort = re.search(
            r"If\(Event Player\.BotOtomatis\s*==\s*True\);.*?"
            r"Call Subroutine\(KunciBot\);.*?Abort;.*?End;",
            classifier.body,
            re.DOTALL,
        )
        roster_append = classifier.body.find("Append To Array(Global.PemainManusia, Event Player)")
        checks.require(
            bot_abort is not None and roster_append >= 0 and bot_abort.end() < roster_append,
            "iBot può raggiungere il roster umano prima dell'Abort dedicato",
        )

    human_writers = [
        rule for rule in rules
        if re.search(r"Event Player\.Manusia\s*=\s*True;", mask_strings(rule.body)) is not None
        or "Set Player Variable(Event Player, Manusia, True);" in rule.body
    ]
    checks.equal(len(human_writers), 1, "numero writer di Manusia=True")
    if human_writers and classifier:
        checks.equal(human_writers[0].start, classifier.start,
                     "Manusia=True scritto fuori dal classificatore umano/iBot")
        human_write = max(
            classifier.body.find("Event Player.Manusia = True;"),
            classifier.body.find("Set Player Variable(Event Player, Manusia, True);"),
        )
        checks.require(
            bot_abort is not None and human_write > bot_abort.end(),
            "Manusia=True viene scritto prima dell'Abort iBot",
        )

    roster_writers = [
        rule for rule in rules
        if "Append To Array(Global.PemainManusia, Event Player)" in rule.body
    ]
    checks.equal(len(roster_writers), 1, "numero regole che inseriscono nel roster umano")
    if roster_writers and classifier:
        checks.equal(roster_writers[0].start, classifier.start,
                     "roster umano scritto fuori dal classificatore dedicato")

    joined = rules_with_event(rules, "Player Joined Match")
    if joined:
        checks.require("Is Dummy Bot(Event Player) == False;" in joined[0].body,
                       "join/team-switch umano non esclude dummy nativi")
        checks.require("Event Player.BotOtomatis == False;" in joined[0].body,
                       "join/team-switch umano può riattivare il lifecycle di un iBot")
    left = rules_with_event(rules, "Player Left Match")
    if left:
        for token in (
            "Is Dummy Bot(Event Player) == False;",
            "Event Player.BotOtomatis == False;",
            "Or(Event Player.Manusia == True, Array Contains(Global.PemainManusia, Event Player)) == True;",
        ):
            checks.require(token in left[0].body,
                           f"leave/cleanup umano può essere eseguito da bot/dummy: {token}")

    setup = rule_by_subroutine(rules, "SiapkanPemain")
    if setup:
        checks.require("Abort If(Is Dummy Bot(Event Player));" in setup.body,
                       "SiapkanPemain non interrompe immediatamente i dummy nativi")

    entrypoints = (
        (next((rule for rule in rules if event_type(rule) == "Ongoing - Each Player" and "HudPemainDibuat" in rule.body and "Create HUD Text(" in rule.body), None), "HUD player", True),
        (next((rule for rule in rules if event_type(rule) == "Ongoing - Each Player" and "Button(Melee)" in rule.body and "Wait(0.500, Abort When False)" in rule.body and "Call Subroutine(GambarMenu);" in rule.body), None), "toggle menu", True),
        (next((rule for rule in rules if event_type(rule) == "Ongoing - Each Player" and "PerintahMenu" in rule.body and all(f"Button({button})" in rule.body for button in MENU_ACTION_BUTTONS)), None), "dispatcher menu", False),
        (next((rule for rule in rules if event_type(rule) == "Ongoing - Each Player" and "Button(Interact)" in rule.body and "Wait(0.500, Abort When False)" in rule.body and "ModeKamera" in rule.body), None), "toggle Camera", True),
        (next((rule for rule in rules if event_type(rule) == "Ongoing - Each Player" and "InspeksiAktif = True;" in rule.body and "Button(Crouch)" in rule.body), None), "inspection Crouch", False),
        (next((rule for rule in rules if event_type(rule) == "Ongoing - Each Player" and "TeleportasiJongkokAktif = True;" in rule.body and "Button(Crouch)" in rule.body), None), "teleport Crouch", True),
        (next((rule for rule in rules if event_type(rule) == "Player Died" and "Hero(Anran)" in rule.body and "Set Ultimate Charge(Event Player, 100);" in rule.body), None), "passiva Anran", True),
        (next((rule for rule in rules if event_type(rule) == "Ongoing - Each Player" and "Respawn(Event Player);" in rule.body and "Button(Jump)" in rule.body), None), "respawn Jump", True),
    )
    for rule, label, triple in entrypoints:
        require_human_guards(rule, label, triple=triple)

    player_hud_calls = list(iter_calls("\n".join(rule.body for rule in rules), "Create HUD Text"))
    for call in player_hud_calls:
        if call.args:
            checks.require(
                call.args[0].strip() in {"Global.PemainManusia", "Event Player"},
                f"Create HUD Text visibile a bot/dummy: {call.args[0].strip()}",
            )

    bot_rule = next(
        (
            rule for rule in rules
            if event_type(rule) == "Ongoing - Each Player"
            and "Or(Is Dummy Bot(Event Player), Event Player.BotOtomatis) == True;" in rule.body
            and "Call Subroutine(KunciBot);" in rule.body
        ),
        None,
    )
    checks.require(bot_rule is not None, "regola dedicata di lock bot/dummy assente")
    if bot_rule:
        checks.require(not any(token in bot_rule.body for token in ("Create HUD Text(", "Small Message(", "GambarMenu", "Start Camera(", "Respawn(")),
                       "regola dedicata bot/dummy avvia HUD/menu/funzioni umane")

    bot_lock = rule_by_subroutine(rules, "KunciBot")
    checks.require(bot_lock is not None, "subroutine dedicata KunciBot assente")
    if bot_lock:
        checks.require(not any(token in bot_lock.body for token in ("Create HUD Text(", "Create In-World Text(", "Small Message(", "Start Camera(", "Teleport(", "Respawn(")),
                       "KunciBot crea HUD/menu/funzioni per bot/dummy")
        for token in (
            "Set Primary Fire Enabled(Event Player, False);",
            "Set Secondary Fire Enabled(Event Player, False);",
            "Set Ability 1 Enabled(Event Player, False);",
            "Set Ability 2 Enabled(Event Player, False);",
            "Set Ultimate Ability Enabled(Event Player, False);",
            "Set Melee Enabled(Event Player, False);",
            "Disallow Button(Event Player, Button(Interact));",
            "Set Damage Dealt(Event Player, 0);",
            "Set Healing Dealt(Event Player, 0);",
            "Set Knockback Dealt(Event Player, 0);",
        ):
            checks.require(token in bot_lock.body, f"KunciBot incompleto: {token}")


def validate_modes_and_camera(checks: Checks, source: str, rules: list[Rule]) -> None:
    objective_rule = next((rule for rule in rules if "PerintahTeleportasi == 1" in rule.body and "Payload Position" in rule.body and "Flag Position(" in rule.body and "Objective Position(Objective Index)" in rule.body), None)
    checks.require(objective_rule is not None, "dispatcher destinazione obiettivo assente")
    if objective_rule:
        for mode in GAME_MODES:
            checks.require(f"Game Mode({mode})" in objective_rule.body,
                           f"destinazione obiettivo non copre {mode}")
        checks.require("Is On Objective(" in objective_rule.body,
                       "Push non usa proxy robot/fallback obiettivo")
        checks.require("Nearest Walkable Position(" in objective_rule.body,
                       "teleport obiettivo non verifica una posizione percorribile")
        checks.require("Button(Primary Fire)" in objective_rule.body or "PerintahTeleportasi == 1" in objective_rule.body or event_type(objective_rule) == "Subroutine",
                       "destinazione teleport non viene valutata al click")
    for token in FORBIDDEN_RESULT_ACTIONS:
        checks.require(token not in source, f"risultato deve restare alla modalità nativa: {token}")
    checks.equal(source.count("Disable Built-In Game Mode Completion;"), 1, "blocco completamento nativo fino al timer CHILL")
    camera_rule = rule_by_subroutine(rules, "MulaiKamera")
    checks.require(camera_rule is not None, "subroutine Camera assente")
    if camera_rule:
        checks.equal(camera_rule.body.count("Ray Cast Hit Position("), 1, "raycast Camera")


def validate_indonesian_and_duplicates(checks: Checks, source: str, rules: list[Rule]) -> None:
    names = [rule.name for rule in rules]
    checks.equal(len(names), len(set(names)), "titoli regola univoci")
    bodies = [normalized_rule_body(rule) for rule in rules]
    checks.require(not [body for body, count in Counter(bodies).items() if count > 1],
                   "regole duplicate con corpo identico")
    for rule in rules:
        checks.require(FORBIDDEN_PROSE.search(rule.name) is None,
                       f"titolo regola non interamente indonesiano: {rule.name}")
    standalone_comments = re.findall(r'(?m)^\s*"((?:[^"\\]|\\.)*)"\s*$', source)
    for comment in standalone_comments:
        checks.require(FORBIDDEN_PROSE.search(comment) is None,
                       f"commento Workshop non interamente indonesiano: {comment[:80]}")


def validate(source: str, root: Path = ROOT, *, include_metadata: bool = True) -> Checks:
    checks = Checks()
    try:
        rules = extract_rules(source)
        globals_entries, player_entries, sub_entries, declaration_span = declaration_entries(source)
    except ValueError as error:
        checks.require(False, f"sorgente Workshop non analizzabile: {error}")
        return checks

    checks.require(bool(rules), "nessuna regola Workshop trovata")
    checks.require(re.search(r"(?im)^\s*disabled\s*(?:\r?\n\s*)?rule\s*\(", source) is None,
                   "disabled rule vietata: rimuovere codice morto")
    if rules:
        largest = max(len(rule.body.encode("utf-8")) for rule in rules)
        checks.require(largest <= 80 * 1024,
                       f"largest rule oltre obiettivo 80 KB: {largest} byte")
    validate_rule_grammar(checks, rules)
    if include_metadata:
        validate_metadata(checks, root)
    validate_declarations(checks, source, rules, globals_entries, player_entries, sub_entries, declaration_span)
    globals_ = {entry.name for entry in globals_entries}
    players = {entry.name for entry in player_entries}
    subroutines = {entry.name for entry in sub_entries}
    validate_localization(checks, source, globals_)
    validate_hud_and_menu(checks, source, rules, players, subroutines)
    validate_input_contract(checks, rules)
    validate_scheduler(checks, source, rules, globals_, subroutines)
    validate_try_your_luck(checks, source, rules, players)
    validate_lifecycle(checks, rules, subroutines)
    validate_privacy(checks, rules)
    validate_bot_isolation(checks, rules)
    validate_modes_and_camera(checks, source, rules)
    validate_indonesian_and_duplicates(checks, source, rules)
    return checks


def main() -> int:
    source = SOURCE.read_text(encoding="utf-8")
    checks = validate(source)
    checks.finish()
    rules = extract_rules(source)
    print(
        "OK - gate semantici v0.8.0 superati "
        f"({len(rules)} regole, {len(wait_calls(source))} Wait, {action_loop_count(source)} Loop)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
