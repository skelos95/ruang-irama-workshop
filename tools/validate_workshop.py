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
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VERSION = ROOT / "VERSION"
WORKFLOWS = ROOT / ".github" / "workflows"

CURRENT_VERSION = "0.8.0"
ALLOWED_WORKFLOWS = {"validate-workshop.yml"}
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
    "TerapkanHalamanTeleportasiJongkok",
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
    "Disable Built-In Game Mode Completion;",
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
        # Property syntax (Global.X / Event Player.X / player-expression.X)
        # is unambiguous. A property in the value argument of Set Player
        # Variable is still a read and must not be hidden by that outer call.
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
    # Properties after a known player-bearing global are player variables too.
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
        # Descend once through an outer function call. Iterating every nested
        # call again at every level makes the large menu expressions quadratic.
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


def validate_declarations(checks: Checks, source: str, rules: list[Rule], globals_: list[Declaration],
                          players: list[Declaration], subroutines: list[Declaration], declaration_span: tuple[int, int]) -> None:
    for label, entries in (("global", globals_), ("player", players), ("subroutine", subroutines)):
        indices = [entry.index for entry in entries]
        checks.equal(indices, list(range(len(entries))), f"indici {label} compatti")
        names = [entry.name for entry in entries]
        checks.equal(len(names), len(set(names)), f"nomi {label} univoci")

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
    hud_calls = list(iter_calls(source, "Create HUD Text"))
    checks.require(bool(hud_calls), "nessun HUD testuale trovato")
    for call in hud_calls:
        checks.require(len(call.args) >= 4, "Create HUD Text malformato")
        if len(call.args) >= 2:
            checks.equal(call.args[1].strip(), "Null", "Header Create HUD Text deve essere Null")

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
        checks.require("Event Player.MenuTerbuka == False;" in camera.body,
                       "camera Interact deve funzionare soltanto a menu chiuso")
        checks.require("Is Button Held(Event Player, Button(Crouch)) == False;" in camera.body,
                       "camera Interact interferisce con il modificatore Crouch")

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
    checks.require(len(waits) <= 10, f"Wait oltre il massimo consentito: {len(waits)} > 10")
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
        ("Set Player Health(All Living Players(Team Of(Global.PemainAktif)), 9999)", "cura completa team"),
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
            "TeleportasiJongkokDiaktifkan = False;", "PrivasiInspeksiAktif = False;",
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


def validate_modes_and_camera(checks: Checks, source: str, rules: list[Rule]) -> None:
    objective_rule = next((rule for rule in rules if "Payload Position" in rule.body and "Flag Position(" in rule.body and "Objective Position(Objective Index)" in rule.body), None)
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
    checks.equal(source.count("Ray Cast Hit Position("), 1, "raycast Camera")


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
