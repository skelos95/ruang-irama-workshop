#!/usr/bin/env python3
"""Semantic static gate for Cozywatch Workshop 0.8.1.

The behavioral contracts validate the explicit logical input, while main also
checks its English source parity and the real generated global runtime. No compiled
output is projected back into player-local input for validation. The gate uses
the Python standard library locally and in GitHub Actions.
"""

from __future__ import annotations

import ast
import re
import sys
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Iterator

try:
    from tools import check_clipboard_import as clipboard_import
except ImportError:  # Direct execution: python tools/validate_workshop.py
    import check_clipboard_import as clipboard_import

ROOT = Path(__file__).resolve().parents[1]
BEHAVIORAL_SOURCE = clipboard_import.BEHAVIORAL_SOURCE
BEHAVIORAL_REFERENCE = clipboard_import.BEHAVIORAL_REFERENCE
# Existing behavioral evaluators use SOURCE; it always denotes the logical EN input.
SOURCE = BEHAVIORAL_REFERENCE
VERSION = ROOT / "VERSION"
WORKFLOWS = ROOT / ".github" / "workflows"

CURRENT_VERSION = "0.8.1"
ALLOWED_WORKFLOWS = {"validate-workshop.yml"}
MAX_DECLARATION_NAME_BYTES = 32
CORE_DOCS = (
    "README.md",
    "docs/PROGETTO.md",
    "docs/VALIDAZIONE.md",
    "docs/TEST.md",
)

OBSOLETE_CURRENT_TEXT_PATTERNS = (
    (
        "team-switch attende spawned e vivo prima di ogni refresh",
        re.compile(
            r"(?i)refresh\s+leggero\s+attende\s+che\s+il\s+player\s+sia\s+"
            r"spawned\s+e\s+vivo"
        ),
    ),
    (
        "team-switch senza alcuna ricostruzione HUD",
        re.compile(
            r"(?i)cambio\s+squadra[^.\r\n]*senza\s+cleanup/setup\s+completo,\s*"
            r"ricostruzione\s+HUD\s+o\s+reset\s+engine"
        ),
    ),
    (
        "team-switch descritto come solo aggiornamento dei campi Team",
        re.compile(r"(?i)cambio\s+squadra[^.\r\n]*aggiorna\s+soltanto\s+i\s+campi\s+Team"),
    ),
    (
        "Jump Resurrect descritto erroneamente con Teleport anche su terreno sicuro",
        re.compile(
            r"(?i)(?:teletrasporta|teleport)\s+sempre"
            r"[^.;\r\n]{0,80}nearest\s+walkable"
        ),
    ),
    (
        "Jump Resurrect descritto con fallimento ammesso prima del ritorno in vita",
        re.compile(
            r"(?i)se\s+non\s+(?:esiste|viene\s+trovato)[^.\r\n]{0,100}"
            r"(?:resta|rimane)\s+morto"
        ),
    ),
    (
        "Jump Resurrect descritto con destinazione calcolata dalla snapshot morta",
        re.compile(
            r"(?i)nearest\s+walkable\s+position\s*\(\s*(?:posisimati|deathposition)\s*\)"
        ),
    ),
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
MENU_CROUCH_INSTRUCTIONS = ("Hold CROUCH",)
SCHEDULER_SUBROUTINES = {
    "ProcessPlayerFastState",
    "ProcessPlayerCycle",
    "ProcessPlayerMaintenance",
    "ProcessPlayerLuck",
    "ProcessPlayerFlight",
    "ProcessPlayerBot",
    "MaintainDummyBots",
    "ProcessMultijump",
}
SETUP_WORKER_CONDITIONS = (
    "Global.IsReady == True;",
    "Entity Exists(Event Player) == True;",
    "Is Dummy Bot(Event Player) == False;",
    "Event Player.IsAutomaticBot == False;",
    "Event Player.IsHuman == False;",
    "Event Player.TeamChangeProcessed == True;",
    "Global.TeamCyclePlayer == Event Player;",
    "Event Player.TeamCycleTargetTeam == Team Of(Event Player);",
    "Has Spawned(Event Player) == True;",
    "Event Player.IsPrepared == False;",
    "Total Time Elapsed >= Event Player.TeamCycleDeadline;",
)
SETUP_WORKER_WAKE_GUARDS = (
    "Abort If(Global.IsReady == False)",
    "Abort If(Entity Exists(Event Player) == False)",
    "Abort If(Is Dummy Bot(Event Player) == True)",
    "Abort If(Event Player.IsAutomaticBot == True)",
    "Abort If(Event Player.IsHuman == True)",
    "Abort If(Event Player.TeamChangeProcessed == False)",
    "Abort If(Global.TeamCyclePlayer != Event Player)",
    "Abort If(Event Player.TeamCycleTargetTeam != Team Of(Event Player))",
    "Abort If(Has Spawned(Event Player) == False)",
    "Abort If(Event Player.IsPrepared == True)",
    "Abort If(Total Time Elapsed < Event Player.TeamCycleDeadline)",
)
PAGE_APPLY_SUBROUTINES = {
    "ApplySoundtrackPage",
    "ApplyCameraPage",
    "ApplyNameColorPage",
        "ApplyRevengePage",
    "ApplyUnkillablePage",
    "ApplyHeroVoicePage",
    "ApplyPlayerIconPage",
    "ApplyCrouchTravel",
    "ApplyInspectionPrivacyPage",
    "ApplyLuckPage",
    "ApplyVotePage",
    "ApplyDummyBotFollowPage",
    "ApplyGhostFlyPage",
    "ApplyMultijumpPage",
    "ApplySuperPunchPage",
}
MENU_OWNER_STATE_VARIABLES = {
    "MenuOpen",
    "MenuHud",
    "MenuPage",
    "MainMenuCursor",
    "MenuCommand",
    "MenuInputLocked",
    "MultijumpEnabled",
    "MultijumpCursor",
    "MultijumpLevel",
    "MultijumpConsumed",
    "GenreCursor",
    "GenreIndex",
    "CameraCursor",
    "CameraMode",
    "CameraTarget",
    "ColorCursor",
    "ColorIndex",
    "RevengeCursor",
    "UnkillableCursor",
    "UnkillableMode",
    "UnkillableActive",
    "VoiceCursor",
    "VoiceIndex",
    "IconCursor",
    "IconIndex",
    "CrouchTravelEnabled",
    "InspectionPrivacyActive",
    "VoteCursor",
    "VotedPlayer",
    "AllowDummyBotFollow",
    "GhostFlyCursor",
    "GhostModeActive",
    "FlyModeActive",
    "GhostFlyPhysicsApplied",
}
LIFECYCLE_SUBROUTINES = {"PreparePlayer", "QuiescePlayer", "CleanupPlayer"}
LUCK_TIMESTAMP_VARIABLES = {
    "NextLuckSpinTime",
    "LuckIconEndTime",
    "LuckEffectEndTime",
    "NextLuckBurnTime",
}
LOCALIZED_ARRAY_SIZES = {"IconNames": 37}
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


@lru_cache(maxsize=512)
def mask_strings(text: str) -> str:
    # Validators repeatedly inspect the same immutable rule bodies. Cache by
    # complete text so mutations always get their own result; bound retained
    # entries because mutation tests validate many different source strings.
    if '"' not in text:
        return text
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


def conditional_branch_spans(text: str) -> list[tuple[int, int]]:
    """Return balanced If/Else-If/Else branches with offsets in *text*.

    Workshop uses the same ``End;`` token for conditionals and For loops. Keep
    both on the stack so an action cannot be matched to a sibling branch merely
    because the same token exists elsewhere in the rule.
    """
    stack: list[tuple[str, int | None]] = []
    spans: list[tuple[int, int]] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        stripped = mask_strings(line).strip()
        if re.match(r"For (?:Global|Player) Variable", stripped):
            stack.append(("for", None))
        elif stripped.startswith("If("):
            stack.append(("if", offset))
        elif stripped.startswith("Else If(") or stripped == "Else;":
            if stack and stack[-1][0] == "if":
                _, branch_start = stack[-1]
                if branch_start is not None:
                    spans.append((branch_start, offset))
                stack[-1] = ("if", offset)
        elif stripped == "End;" and stack:
            kind, branch_start = stack.pop()
            if kind == "if" and branch_start is not None:
                spans.append((branch_start, offset + len(line)))
        offset += len(line)
    return spans


def conditional_branches_containing(text: str, position: int) -> list[str]:
    """Return enclosing conditional branches, innermost first."""
    spans = [
        (start, end)
        for start, end in conditional_branch_spans(text)
        if start <= position < end
    ]
    return [text[start:end] for start, end in sorted(spans, key=lambda span: span[1] - span[0])]


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
            # The engine reads and increments the counter even if the body
            # does not reference it (a bounded repetition is a valid use).
            return True
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
    for name in re.findall(r"\bGlobal\.(?:ActivePlayer|CleanupSubject|CameraPlayer)\.([A-Za-z][A-Za-z0-9_]*)", masked):
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
    if event_type(rule) == "Player Joined Match":
        return "join ordering"
    if event_type(rule) == "Player Left Match":
        return "leave ordering"
    if rule.name.startswith("01b -") and event_type(rule) == "Ongoing - Each Player":
        return "lifecycle stages"
    if "Abort When False" in body and "Button(Melee)" in body:
        return "menu hold"
    if "Abort When False" in body and "Button(Interact)" in body:
        return "camera hold"
    if "IsClassified" in body and "Is Dummy Bot" in body:
        return "bot classification"
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
            checks.require(bool(text.strip()), f"documento obbligatorio vuoto: {relative}")
            # VERSION identifies the nominal release, not the live-test status of
            # later revisions. Operational docs need not repeat either marker.
            # Release existence is remote state, not an offline source invariant.
            for label, pattern in OBSOLETE_CURRENT_TEXT_PATTERNS:
                checks.require(
                    pattern.search(text) is None,
                    f"documento contiene testo lifecycle obsoleto ({relative}): {label}",
                )

    changelog = root / "CHANGELOG.md"
    checks.require(changelog.is_file(), "CHANGELOG.md assente")
    if changelog.is_file():
        changelog_text = changelog.read_text(encoding="utf-8")
        release_section_match = re.search(
            rf"(?ms)^##\s+v?{re.escape(CURRENT_VERSION)}\b.*?(?=^##\s+|\Z)",
            changelog_text,
        )
        checks.require(
            release_section_match is not None,
            f"CHANGELOG.md senza sezione storica {CURRENT_VERSION}",
        )
        if release_section_match is not None:
            release_section = release_section_match.group(0)
            for label, pattern in OBSOLETE_CURRENT_TEXT_PATTERNS:
                checks.require(
                    pattern.search(release_section) is None,
                    f"CHANGELOG.md contiene testo lifecycle obsoleto: {label}",
                )

    github = root / ".github"
    github_entries = {
        path.relative_to(github).as_posix()
        for path in github.rglob("*")
    } if github.is_dir() else set()
    checks.equal(
        github_entries,
        {"workflows", "workflows/validate-workshop.yml"},
        "contenuti permanenti .github",
    )

    workflows = github / "workflows"
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
        # Removed toggle cursors leave their original player IDs free. Preserve
        # every other ID so importing this revision does not reshuffle variables.
        expected_indices = list(range(len(entries)))
        checks.equal(indices, expected_indices, f"indici {label} compatti")
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

    setup = rule_by_subroutine(rules, "PreparePlayer")
    checks.require(setup is not None, "PreparePlayer assente per verifica inizializzazione")
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
                           f"variabile player non inizializzata in PreparePlayer: {entry.name}")


def workshop_setting_text_errors(call: Call) -> list[str]:
    """Check the constant category/name keys used by this project's settings."""
    errors: list[str] = []
    for index, field in enumerate(("categoria", "nome")):
        label = f"{field} {call.name}"
        if len(call.args) <= index:
            errors.append(f"{label} assente")
            continue
        expression = call.args[index].strip()
        custom = next(iter(iter_calls(expression, "Custom String")), None)
        if not (
            custom is not None
            and custom.start == 0
            and custom.end == len(expression)
            and len(custom.args) == 1
            and re.fullmatch(r'"(?:\\.|[^"\\])*"', custom.args[0], re.DOTALL)
        ):
            errors.append(f"{label} deve essere un Custom String letterale senza sostituzioni")
            continue
        literal = parse_literal(custom.args[0])
        if literal is None or not literal.strip():
            errors.append(f"{label} vuoto o non valido")
        elif any(char in literal for char in "{}:"):
            errors.append(f"{label} contiene un carattere vietato: {{, }} o :")
    return errors


def validate_localization(checks: Checks, source: str, globals_: set[str]) -> None:
    """The interface and native clipboard grammar use English only."""
    retired = ("IndeksBahasa", "KursorBahasa", "NamaBahasa", "NamaWarna", "NamaWarnaThai",
               "NamaHalaman", "NamaHalamanThai", "NamaIkonIndonesia", "NamaIkonThai",
               "NamaLokasiInggris", "NamaLokasiIndonesia", "NamaLokasiThai", "IndeksLokasiServer",
               "GambarBahasa", "TerapkanHalamanBahasa")
    syntax = mask_strings(source)
    for name in retired:
        checks.require(re.search(rf"\b{re.escape(name)}\b", syntax) is None,
                       f"English UI: stato lingua/località rimosso ancora presente: {name}")
    for name, expected_size in LOCALIZED_ARRAY_SIZES.items():
        checks.require(name in globals_, f"array inglese dichiarato assente: {name}")
        items = array_assignment_items(source, name)
        checks.require(items is not None, f"array inglese non inizializzato: {name}")
        if items is not None:
            checks.equal(len(items), expected_size, f"numero voci {name}")
    checks.require("Global.IconNames[" in source, "nomi icona inglesi mai selezionati")
    for action, english in (("Workshop Setting Integer", "Duration (min)"), ("Workshop Setting Toggle", "Diagnostics")):
        calls = list(iter_calls(source, action))
        checks.equal(len(calls), 1, f"numero {action}")
        for call in calls:
            checks.errors.extend(workshop_setting_text_errors(call))
            if len(call.args) >= 2:
                label_call = next(iter(iter_calls(call.args[1], "Custom String")), None)
                label = parse_literal(label_call.args[0]) if label_call and label_call.args else None
                checks.equal(label, english, f"label {action} deve essere inglese")
    checks.equal(len(list(iter_calls(source, "Workshop Setting Combo"))), 0,
                 "impostazione località rimossa")
    for action, positions in (("Small Message", (1,)), ("Create HUD Text", (1, 2, 3)),
                              ("Create In-World Text", (1,))):
        for call in iter_calls(source, action):
            for position in positions:
                if position >= len(call.args):
                    checks.require(False, f"{action} malformato")
                    continue
                for literal in iter_calls(call.args[position], "Custom String"):
                    if literal.args:
                        value = parse_literal(literal.args[0])
                        checks.require(value is None or re.search(r"[\u0e00-\u0e7f]", value) is None,
                                       f"English UI: testo Thai visibile in {action}")
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


def validate_hud_and_menu(checks: Checks, source: str, rules: list[Rule], players: set[str], subroutines: set[str]) -> None:
    routine_noise = (
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
    for legacy in (
        "Thirteen extremely important decisions",
        "Tiga belas keputusan",
        "มีสิบสามตัวเลือก",
        "Twelve extremely important decisions",
        "Dua belas keputusan",
        "มีสิบสองตัวเลือก",
    ):
        checks.require(legacy not in source, f"messaggio apertura menu obsoleto: {legacy}")

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
            and "COZYWATCH" in call.args[3]
            and "Global.ServerTimeText" in call.args[3]
        ),
        None,
    )
    checks.require(server_title is not None, "HUD titolo Cozywatch e timer server assente")
    if server_title:
        checks.equal(server_title.args[2].strip(), "Null", "HUD titolo Cozywatch: Subheader")
        checks.equal(server_title.args[4].strip(), "Top", "HUD titolo Cozywatch: posizione")
        checks.equal(server_title.args[5].strip(), "0", "HUD titolo Cozywatch: ordinamento")
        checks.require('Custom String("COZYWATCH [{0}]"' in server_title.args[3],
                       "HUD titolo Cozywatch deve mostrare il timer tra parentesi quadre")
        checks.require("\\n" not in server_title.args[3],
                       "HUD titolo Cozywatch non deve contenere spaziatura incorporata")

    init_rule = next(
        (
            rule for rule in rules
            if event_type(rule) == "Ongoing - Global"
            and "COZYWATCH" in rule.body
            and "Global.IsReady = True;" in rule.body
        ),
        None,
    )
    checks.require(init_rule is not None, "regola inizializzazione griglia HUD assente")
    if init_rule:
        init_hud_calls = list(iter_calls(init_rule.body, "Create HUD Text"))
        checks.equal(len(init_hud_calls), 6, "numero HUD fissi nella regola iniziale")

    global_hud_calls = [
        call for call in hud_calls
        if call.args and call.args[0].strip() == "Global.HumanPlayers"
    ]
    checks.equal(len(global_hud_calls), 7, "numero HUD globali: sei fissi e un roster")

    slot_assignments = re.findall(
        r"Global\.AvailableHudSlots\s*=\s*Array\(([^;]*)\);",
        mask_strings(source),
    )
    checks.equal(len(slot_assignments), 1, "inizializzazione slot HUD roster")
    if slot_assignments:
        try:
            roster_slots = [int(value.strip()) for value in slot_assignments[0].split(",")]
        except ValueError:
            roster_slots = []
        checks.equal(roster_slots, list(range(12)), "slot HUD roster devono essere esattamente 0..11")

    fixed_slots = {
        ("Left", "0"),
        ("Left", "13"),
        ("Right", "0"),
        ("Top", "0"),
        ("Top", "1"),
        ("Top", "2"),
    }
    fixed_hud: dict[tuple[str, str], Call] = {}
    for slot in sorted(fixed_slots):
        matches = [
            call for call in hud_calls
            if len(call.args) >= 6
            and call.args[0].strip() == "Global.HumanPlayers"
            and call.args[4].strip() == slot[0]
            and call.args[5].strip() == slot[1]
        ]
        checks.equal(len(matches), 1, f"HUD fisso {slot[0]} sort {slot[1]}")
        if matches:
            fixed_hud[slot] = matches[0]
    checks.equal(len(fixed_hud), 6, "griglia HUD fissa Top/Left/Right")

    field_contract = {
        ("Left", "0"): ("text", "PLAYER VIBES"),
        ("Left", "13"): ("subheader", "Global.VoteLeaderName"),
        ("Right", "0"): ("text", "Host:"),
        ("Top", "0"): ("text", "COZYWATCH"),
        ("Top", "1"): ("subheader", 'Custom String("cozywatch.org")'),
        ("Top", "2"): ("text", 'Custom String("  ")'),
    }
    for slot, (field, token) in field_contract.items():
        call = fixed_hud.get(slot)
        if not call:
            continue
        field_index = 2 if field == "subheader" else 3
        other_index = 3 if field == "subheader" else 2
        if slot in {("Left", "-1"), ("Top", "2")}:
            checks.equal(call.args[field_index].strip(), token,
                         f"HUD fisso {slot[0]} sort {slot[1]}: contenuto {field} errato")
        else:
            checks.require(token in call.args[field_index],
                           f"HUD fisso {slot[0]} sort {slot[1]}: contenuto {field} errato")
        checks.equal(call.args[other_index].strip(), "Null",
                     f"HUD fisso {slot[0]} sort {slot[1]}: campo non usato")

    for slot, (field, expected_labels) in {
        ("Left", "0"): ("text", ("PLAYER VIBES",)),
        ("Left", "13"): ("subheader", ("CHILL STAR: {0}",)),
    }.items():
        call = fixed_hud.get(slot)
        if not call:
            continue
        localized_field = call.args[2] if field == "subheader" else call.args[3]
        for label in expected_labels:
            checks.require(label in localized_field,
                           f"HUD fisso {slot[0]} sort {slot[1]}: testo localizzato assente: {label}")

    server_location = fixed_hud.get(("Top", "1"))
    player_vibes = fixed_hud.get(("Left", "0"))
    if server_location:
        checks.equal(
            re.sub(r"\s+", "", server_location.args[7]),
            "CustomColor(255,205,110,255)",
            'WEBSITE: colore subheader pastel gold esatto',
        )
    if server_location and player_vibes:
        checks.require(
            re.sub(r"\s+", "", server_location.args[7])
            != re.sub(r"\s+", "", player_vibes.args[8]),
            'WEBSITE deve avere un colore distinto da PLAYER VIBES',
        )

    host = fixed_hud.get(("Right", "0"))
    if host:
        for token in ("Entity Exists(Host Player)", 'Custom String("Host:")',
                      "Hero Icon String(Hero Of(Host Player))", "Player Variable(Host Player, DisplayName)",
                      'Custom String("{0}", Host Player)'):
            checks.require(token in host.args[3], f"HUD Host: riferimento dinamico assente: {token}")
        checks.require('Custom String(" \\n{0} {1} {2}\\n "' in host.args[3],
                       "HUD Host: Text deve mantenere una riga vuota sopra e sotto")
        checks.require("Evaluate Once(" not in host.args[3], "HUD Host: nome e icona devono seguire l'host corrente")
        checks.require(host.args[3].strip().endswith(': Custom String("")'),
                       "HUD Host: fallback senza host deve essere stringa vuota")
        checks.equal(host.args[8].strip(), "Global.RGB", "HUD Host: colore RGB globale del titolo")
        checks.equal(host.args[9].strip(), "Visible To String and Color", "HUD Host: rivalutazione testo e colore")

    chill_star = fixed_hud.get(("Left", "13"))
    checks.require(chill_star is not None, "HUD CHILL STAR dedicato assente")
    if chill_star:
        checks.require(chill_star.args[2].strip().startswith("Global.VoteLeaderName != Custom String(\"\")"),
                       "HUD CHILL STAR: guardia nome cache assente")
        checks.require("Global.VoteLeaderName" in chill_star.args[2],
                       "HUD CHILL STAR: Subheader deve usare la cache nome leader")
        checks.equal(chill_star.args[3].strip(), "Null", "HUD CHILL STAR: Text deve restare vuoto")
        checks.equal(chill_star.args[7].strip(), "Global.VoteLeaderColor",
                     "HUD CHILL STAR: colore Subheader deve usare la cache leader")
        checks.equal(chill_star.args[9].strip(), "Visible To String and Color",
                     "HUD CHILL STAR: deve rivalutare testo e colore")
        checks.require("Player Variable(Global.VoteLeader, DisplayName)" not in chill_star.args[2],
                       "HUD CHILL STAR non deve dereferenziare direttamente VoteLeader per il nome")
        checks.require("Player Variable(Global.VoteLeader, NameColor)" not in chill_star.args[2],
                       "HUD CHILL STAR non deve dereferenziare direttamente VoteLeader per il colore")
    checks.require("Global.VoteLeaderName = Custom String(\"\");" in source,
                   "cache nome CHILL STAR deve essere sempre inizializzata/resettata")
    checks.require("Global.VoteLeaderColor = Color(White);" in source,
                   "cache colore CHILL STAR deve essere sempre inizializzata/resettata")
    checks.require("Global.VoteLeaderName = Player Variable(Global.VoteLeader, DisplayName);" in source,
                   "RecountVotes deve aggiornare la cache nome CHILL STAR")
    checks.require("Global.VoteLeaderColor = Player Variable(Global.VoteLeader, NameColor);" in source,
                   "RecountVotes deve aggiornare la cache colore CHILL STAR")
    color_page = rule_by_subroutine(rules, "ApplyNameColorPage")
    checks.require(color_page is not None, "subroutine ApplyNameColorPage assente")
    if color_page:
        checks.require("If(Global.VoteLeader == Event Player);" in color_page.body,
                       "pagina colore deve verificare se sta modificando il CHILL STAR corrente")
        checks.require("Global.VoteLeaderColor = Event Player.NameColor;" in color_page.body,
                       "pagina colore deve sincronizzare il colore CHILL STAR quando cambia il leader")

    def full_custom_string(expression: str) -> Call | None:
        expression = expression.strip()
        return next(
            (
                call for call in iter_calls(expression, "Custom String")
                if call.start == 0 and call.end == len(expression)
            ),
            None,
        )

    for call in global_hud_calls:
        checks.require((call.args[4].strip(), call.args[5].strip()) not in
                       {("Left", "-2"), ("Left", "-1"), ("Right", "-16")},
                       "help HUD statici rimossi: usare Info / Controls")

    checks.require("6 + Count Of(Filtered Array(Global.PlayerListHudIds" in mask_strings(source),
                   "diagnostica HUD non include gli sei handle fissi")

    roster_rule = next(
        (
            rule for rule in rules
            if event_type(rule) == "Ongoing - Each Player"
            and "Event Player.PlayerHudCreated = True;" in rule.body
            and "Event Player.PlayerListHud = Last Text ID;" in rule.body
        ),
        None,
    )
    checks.require(roster_rule is not None, "renderer HUD roster umano assente")
    if roster_rule:
        roster_calls = list(iter_calls(roster_rule.body, "Create HUD Text"))
        checks.equal(len(roster_calls), 1, "renderer HUD roster: numero handle")
        roster_orders = {
            "Left": "1 + Event Player.HudSlot",
        }
        for side in ("Left",):
            side_calls = [call for call in roster_calls if len(call.args) >= 6 and call.args[4].strip() == side]
            checks.equal(len(side_calls), 1, f"renderer HUD roster {side}")
            if not side_calls:
                continue
            call = side_calls[0]
            checks.equal(len(call.args), 11, f"renderer HUD roster {side}: firma Create HUD Text")
            if len(call.args) != 11:
                continue
            checks.equal(call.args[5].strip(), roster_orders[side],
                         f"renderer HUD roster {side}: ordinamento")
            row_literals = [
                parse_literal(custom.args[0])
                for custom in iter_calls(call.args[2], "Custom String")
                if custom.args
            ]
            checks.require(not any(literal is not None and literal.endswith("\n ") for literal in row_literals),
                           f"renderer HUD roster {side}: riga fantasma incorporata")
            if side == "Left":
                for legacy_token in ("CHILL STAR:", "BINTANG CHILL:", "ดาวสายชิล:"):
                    checks.require(legacy_token not in call.args[2],
                                   "renderer HUD roster Left non deve incorporare la riga CHILL STAR")
                player_row = full_custom_string(call.args[2])
                checks.require(player_row is not None and len(player_row.args) == 4
                               and parse_literal(player_row.args[0]) == "{0} {1} {2}",
                               "renderer HUD roster Left: Subheader deve contenere soltanto la riga player")
                if player_row and len(player_row.args) == 4:
                    checks.equal(player_row.args[1].strip(), "Global.PlayerIcons[Event Player.IconIndex]",
                                 "renderer HUD roster Left: icona player invariata")
                    checks.equal(
                        re.sub(r"\s+", "", player_row.args[2]),
                        "HeroIconString(IsDuplicating(EventPlayer)?HeroBeingDuplicated(EventPlayer):HeroOf(EventPlayer))",
                        "renderer HUD roster Left: icona hero corrente invariata",
                    )
                    name_and_vibe = full_custom_string(player_row.args[3])
                    checks.require(name_and_vibe is not None and len(name_and_vibe.args) == 3
                                   and parse_literal(name_and_vibe.args[0]) == "{0} - {1}",
                                   "renderer HUD roster Left: riga nome e soundtrack invariata")
                    if name_and_vibe and len(name_and_vibe.args) == 3:
                        checks.equal(name_and_vibe.args[1].strip(), "Evaluate Once(Event Player.DisplayName)",
                                     "renderer HUD roster Left: nome player stabile invariato")
                checks.require("PerformanceDiagnostics" not in mask_strings(call.args[2]),
                               "renderer HUD roster Left: diagnostica deve essere separata nel Text")
                checks.equal(call.args[7].strip(), "Event Player.NameColor",
                             "renderer HUD roster Left: colore Subheader deve usare NameColor")
                checks.equal(clipboard_import.canonical_semantic_text(call.args[8], "en-US"), "Color(White)",
                             "renderer HUD roster Left: diagnostica Text deve essere sempre bianca")
                diagnostic_branches = parse_top_level_ternary(call.args[3])
                checks.require(diagnostic_branches is not None,
                               "renderer HUD roster Left: ternario diagnostica nel Text assente")
                if diagnostic_branches:
                    diagnostic_condition, diagnostic_text, diagnostic_fallback = diagnostic_branches
                    checks.equal(
                        re.sub(r"\s+", "", diagnostic_condition),
                        "And(Global.PerformanceDiagnostics==True,And(LocalPlayer==HostPlayer,"
                        "EventPlayer.HudSlot==Global.LastHudSlot))",
                        "renderer HUD roster Left: guardia diagnostica richiede toggle, host e ultimo slot",
                    )
                    diagnostic = full_custom_string(diagnostic_text)
                    checks.require(diagnostic is not None and len(diagnostic.args) == 3
                                   and parse_literal(diagnostic.args[0]) == "{0}\n{1}",
                                   "renderer HUD roster Left: ramo visibile diagnostica deve essere stringa")
                    checks.require(re.search(r"\bNull\b", mask_strings(diagnostic_text)) is None,
                                   "renderer HUD roster Left: ramo visibile diagnostica non deve usare Null")
                    counts = full_custom_string(diagnostic.args[2]) if diagnostic and len(diagnostic.args) == 3 else None
                    checks.require(counts is not None and len(counts.args) == 3
                                   and parse_literal(counts.args[0]) == "HUD {0} | IWT {1}",
                                   "renderer HUD roster Left: conteggi diagnostica non nel ramo visibile")
                    if counts and len(counts.args) == 3:
                        checks.equal(
                            re.sub(r"\s+", "", counts.args[1]),
                            "6+CountOf(FilteredArray(Global.PlayerListHudIds,CurrentArrayElement!=0))"
                            "+CountOf(FilteredArray(Global.MenuHudIds,CurrentArrayElement!=0))"
                            "+CountOf(FilteredArray(Global.TemporaryEffectHudIds,CurrentArrayElement!=0))",
                            "renderer HUD roster Left: conteggio HUD diagnostica deve includere sei fissi e tutti gli handle",
                        )
                        checks.equal(
                            re.sub(r"\s+", "", counts.args[2]),
                            "CountOf(FilteredArray(Global.InspectionTextIds,CurrentArrayElement!=0))"
                            "+CountOf(FilteredArray(Global.TemporaryTravelTextIds,CurrentArrayElement!=0))"
                            "+CountOf(FilteredArray(Global.TemporaryVisionTextIds,CurrentArrayElement!=0))",
                            "renderer HUD roster Left: conteggio IWT diagnostica deve includere tutti gli handle",
                        )
                    checks.equal(diagnostic_fallback.strip(), 'Custom String("")',
                                 "renderer HUD roster Left: fallback diagnostica deve essere stringa vuota")

    for retired in ("WaktuMasuk", "MenitLobi", "HudKanan", "HudKananPemain"):
        checks.require(re.search(rf"\b{retired}\b", mask_strings(source)) is None,
                       f"roster unico: stato rimosso ancora presente: {retired}")
    checks.require("LOBBY & CHILL TIME" not in source,
                   "roster unico: vecchia lista minuti ancora presente")
    checks.require("Event Player.CustomSoundtrack" in roster_rule.body if roster_rule else False,
                   "roster unico: Player Vibes deve mantenere il soundtrack")

    checks.require("MenuHud" in players, "handle menu unico MenuHud assente")
    for name in ("AllowDummyBotFollow",):
        checks.require(name in players, f"stato pagina 12 Dummy Follow assente: {name}")
    for retired in ("KursorTeleportasiJongkok", "KursorPrivasiInspeksi", "KursorIkutiBotBuatan"):
        checks.require(retired not in mask_strings(source), f"toggle diretto: cursore ON/OFF obsoleto: {retired}")
    checks.require("DrawMenu" in subroutines and "DrawActiveMenuPage" in subroutines,
                   "router menu DrawMenu/DrawActiveMenuPage assente")
    menu_renderers = [
        rule for rule in rules
        if subroutine_target(rule) and "Create HUD Text(" in rule.body and "Event Player.MenuHud = Last Text ID;" in rule.body
    ]
    arcade_renderers = [rule for rule in menu_renderers if subroutine_target(rule) != "DrawTravelMenu"]
    checks.equal(len(arcade_renderers), 13, "renderer menu principale + dodici pagine con opzioni")
    direct_pages = {8, 9, 12, 15}
    for retired in ("GambarSakelarTeleportasi", "GambarPrivasiInspeksi",
                    "GambarIkutiBotBuatan", "GambarPukulanSuper"):
        checks.require(retired not in subroutines and rule_by_subroutine(rules, retired) is None,
                       f"toggle principale: renderer ON/OFF obsoleto: {retired}")
    teleport_renderer = rule_by_subroutine(rules, "DrawTravelMenu")
    checks.require(teleport_renderer is not None, "renderer DrawTravelMenu assente")
    if teleport_renderer:
        checks.require('Custom String("{0}n{1}"' not in teleport_renderer.body,
                       "menu Teleport non deve lasciare lettere n da vecchi escape")
        teleport_calls = list(iter_calls(teleport_renderer.body, "Create HUD Text"))
        if len(teleport_calls) == 1:
            teleport_call = teleport_calls[0]
            checks.equal(len(teleport_call.args), 11, "DrawTravelMenu: firma Create HUD Text")
            if len(teleport_call.args) >= 9:
                page_tokens = (
                    "1/5 | TELEPORT: SPAWN ROOM", "TEAM SPAWN",
                    "2/5 | TELEPORT: OBJECTIVE", "3/5 | TELEPORT TO PLAYER/BOT",
                    "BESIDE: {0}", "4/5 | ATTACH TO PLAYER/BOT", "ABOVE: {0}",
                    "5/5 | SELF ELIMINATION", "CURRENT HERO FORM | COOLDOWN: 3s",
                )
                for token in page_tokens:
                    checks.require(token in teleport_call.args[3],
                                   f"DrawTravelMenu: English page content missing: {token}")
                for token in ("Hold {0} / release: close", "{0}: next / {1}: prev",
                              "{0}: use / {1}+{2}: detach"):
                    checks.require(token in teleport_call.args[2],
                                   f"DrawTravelMenu: controls missing: {token}")
                smooth_pastel = (
                    "Custom Color(190 + X Component Of(Event Player.MenuColor) * 0.250, "
                    "190 + Y Component Of(Event Player.MenuColor) * 0.250, "
                    "190 + Z Component Of(Event Player.MenuColor) * 0.250, 255)"
                )
                smooth_neon = (
                    "Custom Color(X Component Of(Event Player.MenuColor), "
                    "Y Component Of(Event Player.MenuColor), "
                    "Z Component Of(Event Player.MenuColor), 255)"
                )
                checks.equal(
                    teleport_call.args[7].strip(),
                    smooth_pastel,
                    "DrawTravelMenu: tinta pastello fluida guidata da MenuColor",
                )
                checks.equal(
                    teleport_call.args[8].strip(),
                    smooth_neon,
                    "DrawTravelMenu: tinta neon fluida guidata da MenuColor",
                )
                checks.equal(
                    teleport_call.args[9].strip(),
                    "Visible To String and Color",
                    "DrawTravelMenu: colore deve rivalutarsi dopo la selezione",
                )
    travel_transition = rule_by_subroutine(rules, "TransitionMenuColor")
    checks.require(travel_transition is not None, "transizione Travel assente")
    if travel_transition:
        for token in (
            "Event Player.CrouchTravelActive == True",
            "Vector(80, 255, 160)",
            "Vector(65, 225, 255)",
            "Vector(95, 150, 255)",
            "Vector(195, 100, 255)",
            "Vector(255, 85, 135)",
            "Chase Player Variable Over Time(Event Player, MenuColor, Event Player.TravelCursor",
            "0.180, Destination and Duration",
        ):
            checks.require(token in travel_transition.body,
                           f"colore Travel incompleto: {token}")
    travel_open = next((rule for rule in rules if rule.name.startswith("19 -")), None)
    travel_nav = next((rule for rule in rules if rule.name.startswith("19c -")), None)
    checks.require(travel_open is not None and "Call Subroutine(TransitionMenuColor);" in travel_open.body,
                   "apertura Travel non avvia la transizione colore")
    checks.require(travel_nav is not None and "Call Subroutine(TransitionMenuColor);" in travel_nav.body,
                   "navigazione Travel non avvia la transizione colore")
    for prefix in ("05f", "18j", "19", "19a", "19c", "19e", "19f", "19g", "19h"):
        handler = next((rule for rule in rules if rule.name.startswith(prefix + " -")), None)
        checks.require(handler is not None, f"controller menu/Travel: handler {prefix} assente")
        if handler:
            conditions = rule_block(handler, "conditions") or ""
            guards = ("Event Player.TeamChangeProcessed == False;", "Event Player.PlayerCycleActive == False;")
            if prefix != "18j":
                guards += ("Event Player.IsHuman == True;",)
            else:
                checks.require("Event Player.IsHuman" not in conditions,
                               "cleanup Vision 18j deve conservare anche gli owner bot")
            for token in guards:
                checks.require(token in conditions, f"controller {prefix}: escludere owner in quarantena: {token}")
    if travel_nav:
        checks.require(
            "Event Player.TravelCursor = (Event Player.TravelCursor + (Event Player.TravelCommand == 1 ? 1 : 4)) % 5;"
            in travel_nav.body,
            "Travel: navigazione deve includere cinque pagine avanti e indietro",
        )
    if teleport_renderer:
        normalization = "Event Player.TravelCursor %= 5;"
        checks.require(normalization in teleport_renderer.body
                       and "Create HUD Text(" in teleport_renderer.body
                       and teleport_renderer.body.index(normalization) < teleport_renderer.body.index("Create HUD Text("),
                       "Travel: normalizzare il cursore a cinque pagine prima del rendering")
        checks.require("/6 |" not in teleport_renderer.body,
                       "Travel: pagina Forward rimossa dal menu")
    retired_forward = "ProsesTeleportasiMaju"
    checks.require(retired_forward not in subroutines and rule_by_subroutine(rules, retired_forward) is None,
                   "Travel: subroutine Forward deve restare rimossa")
    forward_callers = [rule for rule in rules for action in ("Call Subroutine", "Start Rule")
                      for call in iter_calls(rule.body, action) if call.args and call.args[0] == retired_forward]
    checks.require(not forward_callers, "Travel: nessun caller della subroutine Forward rimossa")
    teleport_interact = next((rule for rule in rules if rule.name.startswith("19e -")), None)
    checks.require(teleport_interact is not None, "handler Interact Teleport assente")
    if teleport_interact:
        checks.equal(teleport_interact.body.count("Kill(Event Player, Null);"), 1,
                     "Self Kill deve eseguire una sola Kill immediata")
        checks.require("Wait(" not in teleport_interact.body and "Loop;" not in teleport_interact.body,
                       "Self Kill deve essere senza Wait/Loop")
        checks.require("BunuhDiriDiminta" not in teleport_interact.body,
                       "Self Kill non deve usare la coda di morte Skull/Revenge")
    checks.require("BunuhDiriDiminta" not in source,
                   "stato legacy BunuhDiriDiminta deve essere rimosso")
    checks.require("Kill(Global.ActivePlayer, Global.ActivePlayer.RevengeDeathPending == True ?" in source,
                   "Skull/Revenge devono conservare la propria macchina di morte completa")
    for rule in menu_renderers:
        calls = list(iter_calls(rule.body, "Create HUD Text"))
        checks.equal(len(calls), 1, f"{subroutine_target(rule)}: un solo Create HUD")
        if calls:
            checks.equal(calls[0].args[0].strip(), "Event Player",
                         f"{subroutine_target(rule)}: HUD menu non deve essere nascosto/precaricato")
            checks.equal(calls[0].args[1].strip(), "Null",
                         f"{subroutine_target(rule)}: keep the Header empty")
            checks.require(calls[0].args[3].strip() != "Null",
                           f"{subroutine_target(rule)}: menu content missing")
            checks.equal(calls[0].args[4].strip(), "Top", f"{subroutine_target(rule)}: HUD location")
            checks.equal(calls[0].args[5].strip(), "3", f"{subroutine_target(rule)}: HUD order")
            paired_rows = [custom for custom in iter_calls(calls[0].args[3], "Custom String")
                           if custom.args and parse_literal(custom.args[0]) == "{0} | {1}"]
            if subroutine_target(rule) == "DrawInfoMenu":
                checks.equal(calls[0].args[2].strip(), "Null", "Info: no redundant command subtitle")
                checks.require(not paired_rows, "Info: do not duplicate commands in a side column")
                info_controls = (
                    ("Hold {0} + {1} / {2}: next / previous", ("Crouch", "Primary Fire", "Secondary Fire")),
                    ("Hold {0} + {1}: select / apply | + {2}: back", ("Crouch", "Interact", "Reload")),
                    ("Hold {0} 0.5s: open / close Arcade", ("Melee",)),
                    ("Hold {0} 0.5s with {1} released: toggle camera", ("Interact", "Crouch")),
                    ("Menu closed: hold {0}: inspect hero + HP (Travel OFF)", ("Crouch",)),
                    ("Soundtrack: hold {0} + {1} / {2}: +10 / -10", ("Crouch", "Ability 1", "Ability 2")),
                    ("Menu closed, Travel ON: hold {0}; {1} / {2}: next / previous", ("Crouch", "Primary Fire", "Secondary Fire")),
                    ("Travel: {0}: use | release {1}: close", ("Interact", "Crouch")),
                    ("Attached, menu closed: hold {0} + {1}: detach", ("Crouch", "Reload")),
                    ("Dead: press {0} to resurrect on safe ground", ("Jump",)),
                    ("Multijump ON: tap / hold {0} in air to boost", ("Jump",)),
                    ("Superman Punch ON: use {0} to punch", ("Melee",)),
                )
                for description, buttons in info_controls:
                    lines = [custom for custom in iter_calls(calls[0].args[3], "Custom String")
                             if custom.args and parse_literal(custom.args[0]) == description]
                    checks.equal(len(lines), 1, f"Info: exactly one instruction for {description}")
                    if lines:
                        bindings = tuple(binding.args[0].strip()
                                         for argument in lines[0].args[1:]
                                         for binding in iter_calls(argument, "Input Binding String")
                                         if binding.args)
                        checks.equal(bindings, tuple(f"Button({button})" for button in buttons),
                                     f"Info: input binding order for {description}")
                for token in ("0 - INFO / CONTROLS", "0.5s", "with {1} released",
                              "inspect hero + HP", "+10 / -10", "detach", "resurrect",
                              "Multijump ON", "Superman Punch ON"):
                    checks.require(token in calls[0].args[3], f"Info: description missing: {token}")
            else:
                subtitle = calls[0].args[2]
                checks.require(subtitle.strip() != "Null" and "Input Binding String(" in subtitle,
                               f"{subroutine_target(rule)}: commands must use Subheader")
                checks.require("Input Binding String(" not in calls[0].args[3],
                               f"{subroutine_target(rule)}: function Text must not duplicate input hints")
                literals = [parse_literal(custom.args[0]) for custom in iter_calls(subtitle, "Custom String")
                            if custom.args]
                checks.require(not any(literal is not None and literal.startswith("\n") for literal in literals),
                               f"{subroutine_target(rule)}: subtitle cannot start with an artificial blank line")
                if subroutine_target(rule) != "DrawTravelMenu":
                    close_controls = [custom for custom in iter_calls(subtitle, "Custom String")
                                      if len(custom.args) == 2
                                      and parse_literal(custom.args[0]) == "Hold {0} 0.5s: close"
                                      and custom.args[1].strip() == "Input Binding String(Button(Melee))"]
                    checks.require(bool(close_controls),
                                   f"{subroutine_target(rule)}: subtitle close command must bind Melee with a 0.5s hold")
                for button in (("Crouch", "Primary Fire", "Secondary Fire", "Interact", "Reload")
                               if subroutine_target(rule) == "DrawTravelMenu"
                               else ("Crouch", "Interact", "Reload", "Melee")
                               if subroutine_target(rule) != "DrawLuckMenu"
                               else ("Crouch", "Interact", "Reload", "Melee")):
                    checks.require(f"Input Binding String(Button({button}))" in subtitle,
                                   f"{subroutine_target(rule)}: subtitle binding missing: {button}")
                if subroutine_target(rule) == "DrawSoundtrackMenu":
                    for button in ("Ability 1", "Ability 2"):
                        checks.require(f"Input Binding String(Button({button}))" in subtitle,
                                       f"Soundtrack: subtitle binding missing: {button}")

    info_renderer = rule_by_subroutine(rules, "DrawInfoMenu")
    checks.require(info_renderer is not None, "Info / Controls renderer missing")
    if roster_rule:
        registration_actions = rule_block(roster_rule, "actions") or ""
        opening = ("Event Player.MainMenuCursor = 0;", "Event Player.MenuPage = -1;",
                   "Event Player.MenuOpen = True;", "Call Subroutine(DrawMenu);")
        positions = [registration_actions.find(token, registration_actions.find("Event Player.PlayerHudCreated = True;"))
                     for token in opening]
        checks.require(all(position >= 0 for position in positions) and positions == sorted(positions),
                       "Registration must open the main menu with Info / Controls selected after the player HUD is created")

    luck_hud_rule = next((rule for rule in rules if "Event Player.LuckEffectHud = Last Text ID;" in rule.body), None)
    checks.require(luck_hud_rule is not None, "HUD effetto Try Your Luck assente")
    if luck_hud_rule:
        luck_calls = list(iter_calls(luck_hud_rule.body, "Create HUD Text"))
        checks.equal(len(luck_calls), 1, "HUD effetto Try Your Luck: numero handle")
        if luck_calls:
            luck_call = luck_calls[0]
            checks.equal(luck_call.args[4].strip(), "Top", "HUD effetto Try Your Luck: posizione")
            checks.equal(luck_call.args[5].strip(), "3", "HUD effetto Try Your Luck: ordinamento")
            effect_literals = [
                parse_literal(custom.args[0])
                for custom in iter_calls(luck_call.args[3], "Custom String")
                if custom.args
            ]
            checks.require(not any(literal is not None and literal.startswith("\n") for literal in effect_literals),
                           "HUD effetto Try Your Luck inizia con una riga vuota artificiale")

    revenge_renderer = rule_by_subroutine(rules, "DrawRevengeMenu")
    checks.require(revenge_renderer is not None, "renderer Revenge assente")
    if revenge_renderer:
        revenge_calls = list(iter_calls(revenge_renderer.body, "Create HUD Text"))
        checks.require(bool(revenge_calls), "Revenge renderer has no HUD")
        if revenge_calls:
            content = revenge_calls[0].args[3]
            checks.require("Count Of(Event Player.RevengeTargets) == 0" in content,
                           "Revenge must retain the empty target state")
            checks.require("RevengeTargets" not in mask_strings(revenge_calls[0].args[2]),
                           "Revenge commands must stay available when there are no targets")

    checks.require("Append To Array(Event Player.MenuHud" not in source,
                   "MenuHud non deve diventare un array di handle")
    checks.require("HudMenuArcade" not in source and "PramuatSubmenu" not in source,
                   "preload/array di HUD menu ancora presente")
    for rule in rules:
        if ("Button(Primary Fire)" in rule.body or "Button(Secondary Fire)" in rule.body) and "MenuCommand" in rule.body and event_type(rule) == "Ongoing - Each Player":
            checks.require("Create HUD Text(" not in rule.body and "Destroy HUD Text(" not in rule.body,
                           f"{rule.name}: Primary/Secondary non devono ricreare HUD")

    router = rule_by_subroutine(rules, "DrawActiveMenuPage")
    checks.require(router is not None, "subroutine router pagine assente")
    if router:
        checks.require(
            re.search(
                r"If\(Event Player\.MenuPage\s*==\s*-1\);\s*"
                r"Call Subroutine\(DrawMainMenu\);\s*"
                r"Else If\(Event Player\.MenuPage\s*==\s*0\);",
                router.body,
            ) is not None,
            "router menu: il Main Menu deve usare sempre il renderer dinamico DrawMainMenu",
        )
        checks.require(
            "MainMenuCursor" not in router.body,
            "router menu: il renderer principale non deve essere scelto staticamente dal cursore",
        )
        checks.equal(
            router.body.count("Call Subroutine(DrawGhostFlyMenu);"),
            1,
            "router menu: DrawGhostFlyMenu deve essere chiamato soltanto dalla pagina 13 aperta",
        )
        for page in range(16):
            route = re.search(rf"MenuPage\s*==\s*{page}\b", router.body)
            if page in direct_pages:
                checks.require(route is None, f"toggle principale: pagina {page} non deve avere un sottomenu")
            else:
                checks.require(route is not None, f"router menu non copre pagina {page}")
        checks.require(
            re.search(r"MenuPage\s*==\s*1.*?Call Subroutine\(DrawNameColorMenu\);", router.body, re.DOTALL) is not None,
            "router menu: pagina 1 deve aprire Name Color",
        )
        checks.require(
            re.search(r"MenuPage\s*==\s*3.*?Call Subroutine\(DrawSoundtrackMenu\);", router.body, re.DOTALL) is not None,
            "router menu: pagina 3 deve aprire Soundtrack",
        )
        checks.require(
            re.search(r"MenuPage\s*==\s*13.*?Call Subroutine\(DrawGhostFlyMenu\);", router.body, re.DOTALL) is not None,
            "router menu: pagina 13 deve aprire Ghost Mode / Fly",
        )

    main_renderer = rule_by_subroutine(rules, "DrawMainMenu")
    checks.require(main_renderer is not None, "renderer menu principale assente")
    if main_renderer:
        for token in ("0 - INFO / CONTROLS", "1 - NAME COLOR", "2 - 3P CAMERA",
                      "3 - SOUNDTRACK", "4 - REVENGE", "5 - UNKILLABLE", "6 - HERO VOICE",
                      "7 - ICON", "8 - CROUCH: TELEPORT / ATTACH / SELF KILL", "9 - CROUCH PRIVACY",
                      "10 - TRY YOUR LUCK", "11 - VOTE", "12 - DUMMY FOLLOW",
                      "13 - GHOST MODE / FLY", "14 - MULTIJUMP", "15 - SUPERMAN PUNCH"):
            checks.require(token in main_renderer.body, f"Main menu page missing: {token}")
        for state in ("GhostModeActive", "FlyModeActive", "CrouchTravelEnabled",
                      "InspectionPrivacyActive", "AllowDummyBotFollow"):
            checks.equal(main_renderer.body.count(f"Event Player.{state}"), 1,
                         f"Main menu: one English preview of applied {state}")
        checks.require("LET ENEMY DUMMY FOLLOW YOU" in main_renderer.body,
                       "Main menu: Dummy Follow description missing")
        checks.require('Event Player.MainMenuCursor == 12 ? Custom String("12 - DUMMY FOLLOW' in main_renderer.body,
                       "pagina 12 e pagina 13 non sono distinte")
        checks.require("HERO + HP INSPECTION" in main_renderer.body
                       and "ARCADE MENU / CAMERA QUICK TOGGLE" in main_renderer.body
                       and "Select for all controls" in main_renderer.body,
                       "Info preview must include the descriptions removed from the fixed HUDs")

    ghost_fly_renderer = rule_by_subroutine(rules, "DrawGhostFlyMenu")
    checks.require(ghost_fly_renderer is not None, "renderer pagina 13 Ghost Mode / Fly assente")
    if ghost_fly_renderer:
        checks.require("Event Player.MenuPage == -1" not in mask_strings(ghost_fly_renderer.body),
                       "renderer pagina 13: rami del menu principale irraggiungibili")
        for token in (
            "13 - GHOST MODE / FLY",
            "WALL PHASING",
            "FLY MODE",
            "KEEP MOVING: 100% > 1000% / 20s",
        ):
            checks.require(token in ghost_fly_renderer.body,
                           f"pagina 13 Ghost/Fly non localizzata o incompleta: {token}")

    navigation_rule = next(
        (
            rule for rule in rules
            if event_type(rule) == "Ongoing - Each Player"
            and "Event Player.MainMenuCursor = (Event Player.MainMenuCursor" in rule.body
            and "Event Player.MenuCommand == 3" in rule.body
            and "Event Player.MenuCommand == 4" in rule.body
        ),
        None,
    )
    checks.require(navigation_rule is not None, "navigazione menu principale assente")
    if navigation_rule:
        checks.require(
            "Event Player.MainMenuCursor = (Event Player.MainMenuCursor + (Event Player.MenuCommand == 3 ? 1 : 15)) % 16;"
            in navigation_rule.body,
            "navigazione menu principale non usa ciclo esatto 0..15",
        )
        checks.require(
            re.search(r"MenuPage\s*==\s*1.*?ColorCursor\s*=", navigation_rule.body, re.DOTALL) is not None,
            "navigazione menu: pagina 1 deve muovere ColorCursor",
        )
        checks.require(
            re.search(r"MenuPage\s*==\s*3.*?GenreCursor\s*=", navigation_rule.body, re.DOTALL) is not None,
            "navigazione menu: pagina 3 deve muovere GenreCursor",
        )
        checks.require(not any(re.search(rf"MenuPage\s*!=\s*{page}\b", navigation_rule.body)
                               for page in direct_pages),
                       "toggle principale: guardie navigazione dei sottomenu ON/OFF obsolete")
        checks.require(
            re.search(
                r"MenuPage\s*==\s*13.*?GhostFlyCursor\s*=\s*"
                r"\(Event Player\.GhostFlyCursor\s*\+\s*1\)\s*%\s*2;",
                navigation_rule.body,
                re.DOTALL,
            ) is not None,
            "navigazione menu: pagina 13 deve alternare le due voci Ghost/Fly",
        )

    input_router = next(
        (
            rule for rule in rules
            if event_type(rule) == "Ongoing - Each Player"
            and "Event Player.MenuCommand == 0;" in rule.body
            and "Event Player.MenuCommand = 5;" in rule.body
            and "Event Player.MenuCommand = 6;" in rule.body
        ),
        None,
    )
    checks.require(input_router is not None, "router input menu assente")
    if input_router:
        checks.require(
            re.search(
                r"MenuPage\s*==\s*3\s*,\s*Or\(\s*"
                r"Is Button Held\(Event Player, Button\(Ability 1\)\).*?"
                r"Is Button Held\(Event Player, Button\(Ability 2\)\)",
                input_router.body,
                re.DOTALL,
            ) is not None,
            "router input: Ability 1/2 devono armarsi sulla pagina 3 Soundtrack",
        )
        for button, command in (("Ability 1", 5), ("Ability 2", 6)):
            checks.require(
                re.search(
                    rf"Is Button Held\(Event Player, Button\({re.escape(button)}\)\)\s*,\s*"
                    rf"Event Player\.MenuPage\s*==\s*3\).*?MenuCommand\s*=\s*{command};",
                    input_router.body,
                    re.DOTALL,
                ) is not None,
                f"router input: {button} non produce il comando {command} sulla pagina 3 Soundtrack",
            )

    soundtrack_jump = next(
        (
            rule for rule in rules
            if event_type(rule) == "Ongoing - Each Player"
            and "Event Player.GenreCursor = (Event Player.GenreCursor" in rule.body
            and "Event Player.MenuCommand == 5" in rule.body
            and "Event Player.MenuCommand == 6" in rule.body
        ),
        None,
    )
    checks.require(soundtrack_jump is not None, "salto Soundtrack ±10 assente")
    if soundtrack_jump:
        checks.require(
            "Event Player.MenuPage == 3;" in soundtrack_jump.body,
            "salto Soundtrack ±10 deve consumare i comandi sulla pagina 3",
        )

    apply_dispatcher = next(
        (
            rule for rule in rules
            if event_type(rule) == "Ongoing - Each Player"
            and "Event Player.MenuCommand == 1;" in rule.body
            and "Event Player.MenuOpen == True;" in rule.body
            and "Call Subroutine(Apply" in rule.body
        ),
        None,
    )
    checks.require(apply_dispatcher is not None, "dispatcher apply menu assente")
    if apply_dispatcher:
        checks.require(
            re.search(r"MenuPage\s*==\s*1.*?Call Subroutine\(ApplyNameColorPage\);", apply_dispatcher.body, re.DOTALL) is not None,
            "apply menu: pagina 1 deve usare ApplyNameColorPage",
        )
        checks.require(
            re.search(r"MenuPage\s*==\s*3.*?Call Subroutine\(ApplySoundtrackPage\);", apply_dispatcher.body, re.DOTALL) is not None,
            "apply menu: pagina 3 deve usare ApplySoundtrackPage",
        )
        for page, name in ((8, "ApplyCrouchTravel"), (9, "ApplyInspectionPrivacyPage"),
                           (12, "ApplyDummyBotFollowPage"), (15, "ApplySuperPunchPage")):
            calls = [call for call in iter_calls(apply_dispatcher.body, "Call Subroutine")
                     if call.args == (name,)]
            checks.equal(len(calls), 1, f"toggle principale: pagina {page} deve usare {name} una sola volta")
            if calls:
                branches = conditional_branches_containing(apply_dispatcher.body, calls[0].start)
                headers = [re.sub(r"\s+", "", branch.splitlines()[0]).removeprefix("Else")
                           for branch in branches]
                checks.require("If(EventPlayer.MenuPage==-1);" in headers
                               and f"If(EventPlayer.MainMenuCursor=={page});" in headers,
                               f"toggle principale: pagina {page} deve agire dal cursore principale")
                branch = branches[0] if branches else ""
                checks.require("Call Subroutine(DrawMenu)" not in mask_strings(branch)
                               and re.search(r"Event Player\.(?:MenuPage|MainMenuCursor)\s*=(?!=)",
                                             mask_strings(branch)) is None,
                               f"toggle principale: pagina {page} deve conservare schermata, cursore e HUD")
            checks.require(re.search(rf"MenuPage\s*==\s*{page}\b", apply_dispatcher.body) is None,
                           f"toggle principale: apply sottomenu {page} obsoleto")
        checks.require(
            re.search(
                r"MenuPage\s*==\s*13.*?Call Subroutine\(ApplyGhostFlyPage\);",
                apply_dispatcher.body,
                re.DOTALL,
            ) is not None,
            "apply menu: pagina 13 deve usare ApplyGhostFlyPage",
        )

    checks.require(PAGE_APPLY_SUBROUTINES <= subroutines,
                   "dispatcher Interact must cover the fifteen pages with actions")
    for name in sorted(PAGE_APPLY_SUBROUTINES):
        rule = rule_by_subroutine(rules, name)
        if rule:
            checks.require(not wait_calls(rule.body) and action_loop_count(rule.body) == 0,
                           f"{name}: handler pagina deve essere senza Wait/Loop")
            checks.require("Create HUD Text(" not in rule.body and "Destroy HUD Text(" not in rule.body,
                           f"{name}: applicare una preferenza non deve ricreare HUD")

    owner_subroutines = PAGE_APPLY_SUBROUTINES | {
        "DrawMenu",
        "DrawActiveMenuPage",
        "CloseMenu",
        "TransitionMenuColor",
    } | {
        target
        for rule in menu_renderers
        if (target := subroutine_target(rule)) is not None
    }
    owner_engine_actions = (
        "Small Message",
        "Start Camera",
        "Stop Camera",
        "Set Gravity",
        "Set Move Speed",
        "Set Jump Vertical Speed",
        "Set Projectile Speed",
        "Set Damage Received",
        "Set Knockback Received",
        "Set Player Health",
        "Set Status",
        "Clear Status",
        "Enable Movement Collision With Players",
        "Disable Movement Collision With Players",
        "Enable Movement Collision With Environment",
        "Disable Movement Collision With Environment",
        "Start Modifying Hero Voice Lines",
        "Stop Modifying Hero Voice Lines",
        "Start Accelerating",
        "Stop Accelerating",
        "Start Transforming Throttle",
        "Stop Transforming Throttle",
        "Apply Impulse",
        "Teleport",
        "Kill",
        "Resurrect",
    )
    for name in sorted(owner_subroutines):
        rule = rule_by_subroutine(rules, name)
        if not rule:
            continue
        owned_masked = mask_strings(rule.body)
        checks.require(
            "Global.ActivePlayer" not in owned_masked and "Local Player" not in owned_masked,
            f"isolamento menu per-player: {name} usa scratch globale o viewer locale",
        )
        if name not in PAGE_APPLY_SUBROUTINES:
            continue
        for action in owner_engine_actions:
            for call in iter_calls(rule.body, action):
                if call.args:
                    checks.equal(
                        call.args[0].strip(),
                        "Event Player",
                        f"isolamento menu per-player: {name}/{action} owner",
                    )
        for action in ("Set Player Variable", "Modify Player Variable"):
            for call in iter_calls(rule.body, action):
                if len(call.args) >= 2 and call.args[1].strip() in MENU_OWNER_STATE_VARIABLES:
                    checks.equal(
                        call.args[0].strip(),
                        "Event Player",
                        f"isolamento menu per-player: {name}/{call.args[1].strip()} owner",
                    )

    menu_control_rules = [
        rule
        for rule in rules
        if event_type(rule) == "Ongoing - Each Player"
        and any(
            token in mask_strings(rule.body)
            for token in (
                "Event Player.MenuOpen",
                "Event Player.MenuPage",
                "Event Player.MenuCommand",
                "Event Player.MenuInputLocked",
                "Event Player.MenuHud",
            )
        )
    ]
    checks.require(bool(menu_control_rules), "isolamento menu per-player: controller assenti")
    for rule in menu_control_rules:
        control_body = rule.body
        # The player roster includes host-only diagnostics with Local Player.
        # Remove HUD argument expressions before checking controller state ownership.
        for hud in reversed(list(iter_calls(control_body, "Create HUD Text"))):
            control_body = control_body[:hud.start] + " " * (hud.end - hud.start) + control_body[hud.end:]
        control_masked = mask_strings(control_body)
        checks.require(
            "Global.ActivePlayer" not in control_masked and "Local Player" not in control_masked,
            f"isolamento menu per-player: controller {rule.name} usa stato di un altro player",
        )

    dummy_follow_apply = rule_by_subroutine(rules, "ApplyDummyBotFollowPage")
    if dummy_follow_apply:
        availability_guard = (
            "Abort If(And(Event Player.AllowDummyBotFollow == False, "
            "Is True For Any(All Players(Opposite Team Of(Team Of(Event Player))), "
            "And(Entity Exists(Current Array Element), Is Dummy Bot(Current Array Element) == True)) == False));"
        )
        follow_actions = mask_strings(rule_block(dummy_follow_apply, "actions") or "")
        checks.require(re.sub(r"\s+", "", follow_actions).startswith(re.sub(r"\s+", "", availability_guard)),
                       "Dummy Follow: ON richiede un dummy nemico presente prima di stato e feedback; OFF libero")
    for name, state in (("ApplyCrouchTravel", "CrouchTravelEnabled"),
                        ("ApplyInspectionPrivacyPage", "InspectionPrivacyActive"),
                        ("ApplyDummyBotFollowPage", "AllowDummyBotFollow")):
        apply = rule_by_subroutine(rules, name)
        checks.require(apply is not None, f"toggle diretto: handler assente: {name}")
        if apply:
            checks.equal(apply.body.count(f"Event Player.{state} = Event Player.{state} == False;"), 1,
                         f"toggle diretto: {name} deve invertire lo stato applicato una sola volta")

    follow_cache = rule_by_subroutine(rules, "ProcessPlayerMaintenance")
    if follow_cache:
        cache_program = re.sub(r"\s+", "", mask_strings(rule_block(follow_cache, "actions") or ""))
        automatic_off = (
            "If(And(Global.ActivePlayer.IsHuman==True,EntityExists(Global.ActivePlayer)));"
            "If(Global.ActivePlayer.AllowDummyBotFollow==True);"
            "If(IsTrueForAny(AllPlayers(OppositeTeamOf(TeamOf(Global.ActivePlayer))),"
            "And(EntityExists(CurrentArrayElement),IsDummyBot(CurrentArrayElement)==True))==False);"
            "SetPlayerVariable(Global.ActivePlayer,AllowDummyBotFollow,False);End;End;"
        )
        checks.require(cache_program.startswith(automatic_off),
                       "Dummy Follow: OFF automatico 1 Hz deve usare umano presente e dummy nemico live solo se ON")

    follow_writers: list[tuple[str, str]] = []
    for rule in rules:
        owner = subroutine_target(rule) or rule.name
        for match in re.finditer(
            r"Event Player\.AllowDummyBotFollow\s*=(?!=)\s*([^;\r\n]+);",
            mask_strings(rule.body),
        ):
            follow_writers.append((owner, match.group(1).strip()))
    required_follow_writers = {
        ("PreparePlayer", "False"),
        ("ApplyDummyBotFollowPage", "Event Player.AllowDummyBotFollow == False"),
    }
    allowed_follow_writers = required_follow_writers | {("QuiescePlayer", "False")}
    checks.require(required_follow_writers <= set(follow_writers),
                   "Dummy Follow non ha writer setup/apply obbligatori")
    checks.require(set(follow_writers) <= allowed_follow_writers,
                   f"Dummy Follow scritto fuori da setup/apply/quiete: {follow_writers}")
    checks.equal(len(follow_writers), len(set(follow_writers)),
                 "Dummy Follow ha writer duplicati")

    color_transition = rule_by_subroutine(rules, "TransitionMenuColor")
    checks.require(color_transition is not None, "transizione colore menu assente")
    if color_transition:
        checks.require(
            re.search(
                r"\(Event Player\.MenuPage == -1 \? Event Player\.MainMenuCursor : "
                r"Event Player\.MenuPage\) == 12 \?",
                color_transition.body,
            ) is not None,
            "pagina 12 Dummy Follow non ha una tinta menu dedicata",
        )
        checks.require(
            re.search(
                r"\(Event Player\.MenuPage == -1 \? Event Player\.MainMenuCursor : "
                r"Event Player\.MenuPage\) == 13",
                color_transition.body,
            ) is not None,
            "pagina 13 Ghost/Fly non ha una tinta menu dedicata",
        )



def validate_super_punch(checks: Checks, source: str, rules: list[Rule], global_entries: list[Declaration], subroutines: set[str]) -> None:
    """Keep page 15's toggle local and its enabled registry bounded by human slots."""
    def code(expression: str) -> str:
        return re.sub(r"\s+", "", mask_strings(expression))

    declared = {entry.name: entry.index for entry in global_entries}
    for name, index in {"SuperPunchPlayers": 61, "SuperPunchTimes": 62, "SuperPunchTarget": 63}.items():
        checks.equal(declared.get(name), index, f"Super Punch: campo global {name}")
    for name in ("ApplySuperPunchPage", "ProcessSuperPunch"):
        checks.require(name in subroutines, f"Super Punch: subroutine {name} assente")
    checks.require("Global.SuperPunchPlayers=EmptyArray;" in code(source),
                   "Super Punch: registro deve iniziare vuoto OFF")
    timers = array_assignment_items(source, "SuperPunchTimes")
    checks.equal([code(item) for item in timers] if timers is not None else None, ["0"] * 12,
                 "Super Punch: dodici timer slot devono iniziare a zero")

    main = rule_by_subroutine(rules, "DrawMainMenu")
    apply = rule_by_subroutine(rules, "ApplySuperPunchPage")
    if main:
        for title in ("15 - SUPERMAN PUNCH",):
            checks.require(f'Event Player.MainMenuCursor == 15 ? Custom String("{title}' in main.body,
                           f"Super Punch: anteprima principale pagina 15 inglese: {title}")
        checks.equal(main.body.count("Array Contains(Global.SuperPunchPlayers, Event Player)"), 1,
                     "Super Punch: anteprima inglese dello stato applicato")
    checks.require(apply is not None, "Super Punch: handler toggle assente")
    if apply:
        expected = (
            "AbortIf(ArrayContains(Global.HumanPlayers,EventPlayer)==False);"
            "AbortIf(Or(EventPlayer.HudSlot<0,EventPlayer.HudSlot>=12));"
            "If(ArrayContains(Global.SuperPunchPlayers,EventPlayer));"
            "ModifyGlobalVariable(SuperPunchPlayers,RemoveFromArrayByValue,EventPlayer);"
            "Global.SuperPunchTimes[EventPlayer.HudSlot]=0;Else;"
            "ModifyGlobalVariable(SuperPunchPlayers,AppendToArray,EventPlayer);"
            "Global.SuperPunchTimes[EventPlayer.HudSlot]=-1;End;"
        )
        checks.equal(code(rule_block(apply, "actions") or ""), expected,
                     "Super Punch: toggle registrato locale unico e timer OFF 0 / ON -1")
    team_detector = team_switch_worker(rules)
    for rule in rules:
        owner = subroutine_target(rule)
        for call in iter_calls(rule.body, "Modify Global Variable"):
            if call.args and call.args[0].strip() == "SuperPunchPlayers":
                checks.require(owner in {"ApplySuperPunchPage", "QuiescePlayer", "CleanupPlayer"},
                               f"Super Punch: writer registro non autorizzato: {rule.name}")
                checks.require(len(call.args) == 3 and call.args[2].strip() == "Event Player",
                               "Super Punch: registro deve mutare solo identità Event Player")
        for match in re.finditer(r"Global\.SuperPunchPlayers\s*=(?!=)\s*([^;]+);", mask_strings(rule.body)):
            initial = event_type(rule) == "Ongoing - Global" and match.group(1).strip() == "Empty Array"
            cleanup = (owner in {"QuiescePlayer", "CleanupPlayer"} or rule is team_detector) and code(match.group(1)) == (
                "RemoveFromArray(Global.SuperPunchPlayers,EventPlayer)")
            checks.require(initial or cleanup,
                           "Super Punch: assegnazione registro fuori inizializzazione OFF o cleanup locale")

    runtime = rule_by_subroutine(rules, "ProcessSuperPunch")
    checks.require(runtime is not None, "Super Punch: motore ayunan assente")
    if runtime:
        packed = code(runtime.body)
        slot = "Global.SuperPunchTimes[Global.ActivePlayer.HudSlot]"
        for token, label in (
            (f"If(IsMeleeing(Global.ActivePlayer)==False);{slot}=0;Abort;End;", "rilascio native melee riarmo"),
            (f"If({slot}==0);Global.SuperPunchTarget=FirstOf(", "ricerca immediata durante ayunan"),
            (f"If(Global.SuperPunchTarget!=Null);{slot}=-1;End;", "consumo soltanto dopo contatto"),
            ("FilteredArray(AllPlayers(AllTeams),And(CurrentArrayElement!=Global.ActivePlayer", "entrambi i team senza self"),
            ("DistanceBetween(PositionOf(Global.ActivePlayer),PositionOf(CurrentArrayElement))<=2.500", "portata melee limitata"),
            ("IsInViewAngle(Global.ActivePlayer,EyePosition(CurrentArrayElement),90)", "cone frontale"),
            ("IsInLineOfSight(EyePosition(Global.ActivePlayer),EyePosition(CurrentArrayElement),BarriersDoNotBlockLOS)", "muri proteggono entrambi i team"),
            ("HasStatus(Global.SuperPunchTarget,PhasedOut)==False", "protezione Phased Out"),
            ("HasStatus(Global.SuperPunchTarget,Unkillable)==False", "protezione stato Unkillable"),
            ("Or(PlayerVariable(Global.SuperPunchTarget,UnkillableActive)==False,PlayerVariable(Global.SuperPunchTarget,UnkillableMode)==0)", "protezione modalità Unkillable"),
            ("Global.SuperPunchTarget=Null;", "rilascio scratch target"),
        ):
            checks.require(token in packed, f"Super Punch: {label}")
        for field in ("IsHuman==False", "IsAutomaticBot==True", "PlayerCycleActive==True", "TeamChangeProcessed==True",
                      "MeleeConsumed==True"):
            checks.require("Global.ActivePlayer." + field in packed, f"Super Punch: guardia owner {field}")
        checks.require("MenuOpen" not in packed,
                       "Super Punch: menu aperto non deve bloccare l'ayunan")
        checks.require("CrouchTravelActive" not in packed,
                       "Super Punch: Travel attivo non deve bloccare l'ayunan")
        checks.equal(len(list(iter_calls(runtime.body, "Sorted Array"))), 1,
                     "Super Punch: unico target più vicino per ayunan")
        checks.require("TeamOf(" not in packed and "OppositeTeamOf(" not in packed,
                       "Super Punch: alleati e nemici devono seguire lo stesso impatto")
        checks.require(not wait_calls(runtime.body) and action_loop_count(runtime.body) == 0,
                        "Super Punch: motore senza Wait/Loop")
        checks.require("TotalTimeElapsed" not in packed, "Super Punch: nessun ritardo artificiale sull'impatto")
    impact = next((rule for rule in rules if rule.name.startswith("89i1 -")), None)
    checks.require(impact is not None, "Super Punch: evento impatto nativo assente")
    if impact:
        checks.equal(event_type(impact), "Player Dealt Damage", "Super Punch: impatto su evento danno")
        condition_code = code(rule_block(impact, "conditions"))
        for token in ("ArrayContains(Global.SuperPunchPlayers,EventPlayer)==True;",
                      "EventAbility==Button(Melee);", "HeroOf(EventPlayer)!=Hero(JunkerQueen);", "EventDamage>0;",
                      "EventPlayer.IsHuman==True;", "EventPlayer.IsAutomaticBot==False;",
                      "IsDummyBot(EventPlayer)==False;", "EntityExists(EventPlayer)==True;",
                      "HasSpawned(EventPlayer)==True;", "IsAlive(EventPlayer)==True;",
                      "EventPlayer.PlayerCycleActive==False;", "EventPlayer.TeamChangeProcessed==False;",
                      "EventPlayer.MeleeConsumed==False;", "Victim!=Null;", "Victim!=EventPlayer;",
                      "EntityExists(Victim)==True;", "HasSpawned(Victim)==True;", "IsAlive(Victim)==True;"):
            checks.require(token in condition_code, f"Super Punch: guardia impatto {token}")
        checks.require("MenuOpen" not in condition_code,
                       "Super Punch: menu aperto non deve bloccare l'impatto nativo")
        checks.require("CrouchTravelActive" not in condition_code,
                       "Super Punch: Travel attivo non deve bloccare l'impatto nativo")
        impact_code = code(impact.body)
        for token in ("AbortIf(Or(EventPlayer.HudSlot<0,EventPlayer.HudSlot>=CountOf(Global.SuperPunchTimes)));",
                      "AbortIf(Global.SuperPunchTimes[EventPlayer.HudSlot]<0);",
                      "Global.SuperPunchTimes[EventPlayer.HudSlot]=-1;",
                      "HasStatus(Victim,PhasedOut)==False", "HasStatus(Victim,Unkillable)==False",
                      "Or(PlayerVariable(Victim,UnkillableActive)==False,PlayerVariable(Victim,UnkillableMode)==0)",
                      "Kill(Victim,EventPlayer);"):
            checks.require(token in impact_code, f"Super Punch: contratto impatto {token}")
        checks.require("Global.ActivePlayer" not in impact_code and "Global.SuperPunchTarget" not in impact_code,
                       "Super Punch: evento indipendente dallo scratch scheduler")
        checks.require(not wait_calls(impact.body) and action_loop_count(impact.body) == 0,
                       "Super Punch: impatto atomico senza Wait/Loop")
    callers = [(rule, call) for rule in rules for call in iter_calls(rule.body, "Call Subroutine")
               if call.args == ("ProcessSuperPunch",)]
    checks.equal(len(callers), 1, "Super Punch: unico caller scheduler")
    if callers:
        caller, call = callers[0]
        headers = [code(branch.splitlines()[0]) for branch in conditional_branches_containing(caller.body, call.start)]
        checks.require(action_loop_count(caller.body) == 1
                       and "If(ArrayContains(Global.SuperPunchPlayers,Global.ActivePlayer));" in headers,
                       "Super Punch: scheduler chiama motore solo per identità ON")
    for name in ("QuiescePlayer", "CleanupPlayer"):
        lifecycle = rule_by_subroutine(rules, name)
        checks.require(lifecycle is not None and
                       "Global.SuperPunchPlayers=RemoveFromArray(Global.SuperPunchPlayers,EventPlayer);" in code(lifecycle.body),
                       f"Super Punch: cleanup identità in {name}")


def validate_social_beacon(checks: Checks, source: str, rules: list[Rule], global_entries: list[Declaration]) -> None:
    """Guard at most twelve RGB icons floating within ten metres of the objective."""
    def code(expression: str) -> str:
        return re.sub(r"\s+", "", mask_strings(expression))

    declared = {entry.name: entry.index for entry in global_entries}
    fields = ("ObjectiveIconOwners", "ObjectiveIconIds", "ObjectiveIconTimes",
              "ObjectiveIconIndex", "ObjectiveIconChoices", "ObjectiveIconPlayer")
    for index, name in enumerate(fields, 64):
        checks.equal(declared.get(name), index, f"Pilar: campo global {name}")
    for name, initial in (("ObjectiveIconOwners", "Null"), ("ObjectiveIconIds", "0"),
                          ("ObjectiveIconChoices", "0"),
                          ("ObjectiveIconTimes", "0")):
        values = array_assignment_items(source, name)
        checks.equal([code(value) for value in values] if values is not None else None, [initial] * 12,
                     f"Pilar: array dodici slot inizializzati {name}")
    for removed in ("DaftarWarnaPilar", "SkalaIkonPilar", "TujuanIkonPilar"):
        checks.require(removed not in code(source), f"Pilar: stato Light Shaft e destinazioni duplicate rimosso {removed}")
    effects = [(rule, call) for rule in rules for call in iter_calls(rule.body, "Create Effect")]
    checks.equal(len(effects), 0, "Pilar: nessun Light Shaft o Create Effect persistente")

    manager = rule_by_subroutine(rules, "UpdateSocialObjectiveIcons")
    cleanup = rule_by_subroutine(rules, "CleanupObjectiveIcon")
    checks.require(manager is not None and cleanup is not None, "Pilar: manager e cleanup separati obbligatori")
    for rule in (manager, cleanup):
        if rule:
            checks.require("ForGlobalVariable(ObjectiveIconIndex,0,12,1);" in code(rule.body),
                           "Pilar: manutenzione e cleanup limitati a dodici slot")
            checks.require(not wait_calls(rule.body) and action_loop_count(rule.body) == 0,
                           "Pilar: manutenzione atomica senza Wait/Loop")
    if manager:
        checks.equal(len(list(iter_calls(manager.body, "Create In-World Text"))), 0,
                     "Pilar: Icon String nei testi resta bianco; usare entità icona native")
        choices = array_assignment_items(source, "PlayerIcons") or []
        icon_types = [next(iter_calls(choice, "Icon String")).args[0]
                      for choice in choices[1:] if list(iter_calls(choice, "Icon String"))]
        calls = list(iter_calls(manager.body, "Create Icon"))
        checks.equal(len(calls), 36, "Pilar: trentasei tipi icona nativi esclusivi")
        checks.equal([call.args[2] for call in calls if len(call.args) == 6], icon_types,
                     "Pilar: ciascuna scelta deve conservare lo stesso tipo icona")
        for index, call in enumerate(calls, 1):
            checks.equal(len(call.args), 6, "Pilar: firma Create Icon")
            if len(call.args) == 6:
                owner = "EvaluateOnce(Global.ObjectiveIconPlayer)"
                checks.equal(code(call.args[4]), f"PlayerVariable({owner},NameColor)", "Pilar: RGB icona segue owner")
                checks.equal(call.args[3].strip(), "Visible To Position and Color", "Pilar: rivalutazione RGB icona completa")
                checks.equal(call.args[5].strip(), "False", "Pilar: nessun indicatore icona fuori schermo")
                checks.equal(code(call.args[1]), f"ObjectivePosition(ObjectiveIndex)+PlayerVariable({owner},ObjectiveIconPosition)",
                             "Pilar: posizione fluida condivisa senza duplicare interpolazione per tipo")
                checks.require(f"PlayerVariable({owner},IconIndex)=={index}" in code(call.args[0]),
                               "Pilar: tipo obsoleto nascosto subito prima della ricreazione")
                for required in (f"EntityExists({owner})", f"PlayerVariable({owner},IsHuman)==True"):
                    checks.require(required in code(call.args[0]), "Pilar: owner in uscita o cambio squadra nascosto subito")
                checks.require(f"ArrayContains(Global.HumanPlayers,{owner})" in code(call.args[0])
                               and "DistanceBetween(ObjectivePosition(ObjectiveIndex),Vector(0,0,0))>0.100" in code(call.args[0]),
                               "Pilar: visibilita richiede owner nel roster e obiettivo valido")
                branches = [code(branch.splitlines()[0]) for branch in conditional_branches_containing(manager.body, call.start)]
                checks.require("If(Global.ObjectiveIconIds[Global.ObjectiveIconIndex]==0);" in branches,
                                "Pilar: creazione soltanto per slot senza handle")
                expected = f"{'If' if index == 1 else 'ElseIf'}(Global.ObjectiveIconChoices[Global.ObjectiveIconIndex]=={index});"
                checks.require(expected in branches, "Pilar: un solo tipo creato per scelta selezionata")
        packed = code(manager.body)
        for token in (
            "If(Global.ObjectiveIconChoices[Global.ObjectiveIconIndex]!=PlayerVariable(Global.ObjectiveIconOwners[Global.ObjectiveIconIndex],IconIndex));",
            "DestroyIcon(Global.ObjectiveIconIds[Global.ObjectiveIconIndex]);",
            "Global.ObjectiveIconChoices[Global.ObjectiveIconIndex]=PlayerVariable(Global.ObjectiveIconOwners[Global.ObjectiveIconIndex],IconIndex);",
            "Global.ObjectiveIconIds[Global.ObjectiveIconIndex]=LastCreatedEntity;",
            "Global.ObjectiveIconPlayer=Global.ObjectiveIconOwners[Global.ObjectiveIconIndex];",
            "Global.ObjectiveIconPlayer=Null;",
            "RandomReal(0,10)", "RandomReal(0.500,8)",
        ):
            checks.require(token in packed, f"Pilar: gestione entità e traiettoria mancanti {token}")
        for field in ("PlayerListUpdatePending", "TeamChangeProcessed"):
            checks.require(f"PlayerVariable(Global.ObjectiveIconOwners[Global.ObjectiveIconIndex],{field})==False" in packed
                           and f"PlayerVariable(CurrentArrayElement,{field})==False" in packed,
                           "Pilar: manager blocca owner in quarantena e nuove creazioni durante riclassificazione")
        chases = list(iter_calls(manager.body, "Chase Player Variable Over Time"))
        checks.equal(len(chases), 2, "Pilar: avvio e rinnovo percorso condivisi per tutti i tipi")
        for chase in chases:
            checks.equal(tuple(code(arg) for arg in chase.args), (
                "Global.ObjectiveIconOwners[Global.ObjectiveIconIndex]", "ObjectiveIconPosition",
                "DirectionFromAngles(RandomReal(0,360),0)*RandomReal(0,10)+Vector(0,RandomReal(0.500,8),0)", "4.500", "None"),
                "Pilar: chase Vector nativo congela destinazione e durata 4,5 secondi")
        renewal = "If(TotalTimeElapsed>=Global.ObjectiveIconTimes[Global.ObjectiveIconIndex]+3);"
        checks.require(renewal in packed, "Pilar: rinnovo anticipato dopo tre secondi mantiene il controllo a un Hz")
        if chases:
            branch = next((branch for branch in conditional_branches_containing(manager.body, chases[-1].start)
                           if code(branch.splitlines()[0]) == renewal), None)
            checks.require(branch is not None and "SetPlayerVariable(" not in code(branch),
                           "Pilar: rinnovo parte dalla posizione corrente senza reset o teletrasporto")
        checks.require("SetPlayerVariable(Global.ObjectiveIconOwners[Global.ObjectiveIconIndex],ObjectiveIconPosition,DirectionFromAngles(" in packed,
                       "Pilar: inizializzazione Vector prima della chase")
        checks.require("StopChasingPlayerVariable(Global.ObjectiveIconOwners[Global.ObjectiveIconIndex],ObjectiveIconPosition);" in packed,
                       "Pilar: manutenzione ferma la chase del vecchio owner")
    _, player_entries, _, _ = declaration_entries(source)
    checks.equal(next((entry.index for entry in player_entries if entry.name == "ObjectiveIconPosition"), None), 56,
                 "Pilar: unico campo Vector player nell'indice compatto 56")
    for routine in ("PreparePlayer", "QuiescePlayer"):
        setup = rule_by_subroutine(rules, routine)
        checks.require(setup is not None and "EventPlayer.ObjectiveIconPosition=Vector(0,0.500,0);" in code(setup.body),
                       f"Pilar: Vector inizializzato nel lifecycle {routine}")
    for name in ("QuiescePlayer", "CleanupPlayer"):
        lifecycle = rule_by_subroutine(rules, name)
        checks.require(lifecycle is not None and "Call Subroutine(CleanupObjectiveIcon);" in lifecycle.body,
                       f"Pilar: cleanup nel lifecycle {name}")
    worker = next((rule for rule in rules if rule.name.startswith("01b -")), None)
    if worker:
        ordered = [call.args[0] for call in iter_calls(worker.body, "Call Subroutine")]
        checks.require("QuiescePlayer" in ordered and "PreparePlayer" in ordered
                       and ordered.index("QuiescePlayer") < ordered.index("PreparePlayer"),
                       "Pilar: cleanup team precedente deve avvenire prima della nuova classificazione")
    if cleanup:
        checks.require("If(Global.ObjectiveIconOwners[Global.ObjectiveIconIndex]==EventPlayer);" in code(cleanup.body),
                       "Pilar: cleanup deve toccare soltanto l'owner uscente")
        checks.require("DestroyIcon(Global.ObjectiveIconIds[Global.ObjectiveIconIndex]);" in code(cleanup.body)
                       and "Global.ObjectiveIconChoices[Global.ObjectiveIconIndex]=0;" in code(cleanup.body),
                       "Pilar: cleanup distrugge l'entità nativa e azzera la selezione")
        checks.require("StopChasingPlayerVariable(Global.ObjectiveIconOwners[Global.ObjectiveIconIndex],ObjectiveIconPosition);" in code(cleanup.body),
                       "Pilar: cleanup ferma esclusivamente la chase dell'owner")


def validate_multijump(checks: Checks, source: str, rules: list[Rule], player_entries: list[Declaration], subroutines: set[str]) -> None:
    """Guard bounded per-player air jumps, timed hold input and ephemeral rings."""
    def code(expression: str) -> str:
        return re.sub(r"\s+", "", expression)
    fields = {"MultijumpEnabled": 118, "MultijumpCursor": 119,
              "MultijumpLevel": 120, "MultijumpConsumed": 121, "JumpWasGrounded": 122,
              "NextMultijumpTime": 123}
    declared = {entry.name: entry.index for entry in player_entries}
    for name, index in fields.items():
        checks.equal(declared.get(name), index, f"Multijump: campo player {name}")
    for name in ("DrawMultijumpMenu", "ApplyMultijumpPage", "ProcessMultijump"):
        checks.require(name in subroutines, f"Multijump: subroutine {name} assente")
    runtime = rule_by_subroutine(rules, "ProcessMultijump")
    apply = rule_by_subroutine(rules, "ApplyMultijumpPage")
    renderer = rule_by_subroutine(rules, "DrawMultijumpMenu")
    scheduler = next((rule for rule in rules if rule.name.startswith("04g -")), None)
    if scheduler:
        checks.require("If(Global.ActivePlayer.MultijumpEnabled==True);CallSubroutine(ProcessMultijump);End;" in code(mask_strings(scheduler.body)),
                       "Multijump: scheduler deve chiamare il motore solo ON")
        callers = [(owner, call) for owner in rules for call in iter_calls(owner.body, "Call Subroutine")
                   if call.args == ("ProcessMultijump",)]
        checks.require(len(callers) == 1 and callers[0][0] == scheduler,
                       "Multijump: unico owner del motore deve essere lo scheduler")
    if runtime:
        packed = code(mask_strings(runtime.body))
        held = "If(IsButtonHeld(Global.ActivePlayer,Button(Jump))==True);"
        due = "If(Or(Global.ActivePlayer.MultijumpConsumed==False,TotalTimeElapsed>=Global.ActivePlayer.NextMultijumpTime));"
        ground = "And(Global.ActivePlayer.JumpWasGrounded==False,IsOnGround(Global.ActivePlayer)==False)"
        repeat = "Or(Global.ActivePlayer.MultijumpConsumed==False," + ground + ")"
        next_jump = "Global.ActivePlayer.NextMultijumpTime=TotalTimeElapsed+0.300;"
        for token in (
            held, due, due + next_jump,
            "Global.ActivePlayer.MultijumpConsumed=True;",
            "Global.ActivePlayer.MultijumpConsumed=False;",
            "Global.ActivePlayer.IsHuman==True", "HasSpawned(Global.ActivePlayer)==True",
            "IsAlive(Global.ActivePlayer)==True",
            "Global.ActivePlayer.FlyModeActive==False", "Global.ActivePlayer.TravelAttachmentActive==False",
            "Global.ActivePlayer.JumpReviveConsumed==False",
            "Or(Global.ActivePlayer.LuckEffect!=2,Global.ActivePlayer.LuckEffectEndTime<=TotalTimeElapsed)",
            repeat, "If(" + ground + ");",
            "Else;Global.ActivePlayer.MultijumpConsumed=False;Global.ActivePlayer.NextMultijumpTime=0;End;",
            "Global.ActivePlayer.JumpWasGrounded=IsOnGround(Global.ActivePlayer);",
        ):
            checks.require(token in packed, f"Multijump: guardia input o fisica assente {token}")
        checks.require("MenuOpen" not in mask_strings(runtime.body),
                       "Multijump: Jump deve funzionare anche con menu aperto")
        checks.equal(packed.count("Global.ActivePlayer.MultijumpConsumed=True;"), 2,
                     "Multijump: consumare sia input valido sia input bloccato")
        checks.require("Else;Global.ActivePlayer.MultijumpConsumed=True;End;" in packed,
                       "Multijump: input bloccato va consumato senza impulso o ring")
        checks.require(not wait_calls(runtime.body) and action_loop_count(runtime.body) == 0,
                       "Multijump: nessun Wait/Loop nel motore")
        impulses = list(iter_calls(runtime.body, "Apply Impulse"))
        checks.equal(len(impulses), 1, "Multijump: unico impulso verticale")
        delta = "6*Global.ActivePlayer.MultijumpLevel-YComponentOf(VelocityOf(Global.ActivePlayer))"
        if impulses:
            checks.equal(tuple(code(arg) for arg in impulses[0].args),
                         ("Global.ActivePlayer", delta + ">=0?Vector(0,1,0):Vector(0,-1,0)",
                          "AbsoluteValue(" + delta + ")", "ToWorld", "IncorporateContraryMotion"),
                         "Multijump: correzione verticale 6..60 m/s senza accumulo")
        rings = list(iter_calls(runtime.body, "Play Effect"))
        checks.equal(len(rings), 1, "Multijump: unico ring temporaneo per salto")
        if rings:
            checks.equal(tuple(code(arg) for arg in rings[0].args),
                         ("AllPlayers(AllTeams)", "RingExplosion", "Global.RGB",
                          "PositionOf(Global.ActivePlayer)+Vector(0,0.050,0)", "1.500"),
                         "Multijump: ring RGB globale sotto i piedi")
        for call in (*impulses, *rings):
            headers = [code(branch.splitlines()[0]) for branch in
                       conditional_branches_containing(runtime.body, call.start)]
            checks.require(held in headers and due in headers,
                           "Multijump: azione nativa richiede Jump e pressione nuova o cooldown scaduto")
            guarded = next((header for header in headers if "Global.ActivePlayer.IsHuman==True" in header), "")
            for token in ("HasSpawned(Global.ActivePlayer)==True", "IsAlive(Global.ActivePlayer)==True",
                          "Global.ActivePlayer.FlyModeActive==False",
                          "Global.ActivePlayer.TravelAttachmentActive==False", "Global.ActivePlayer.JumpReviveConsumed==False",
                          "Or(Global.ActivePlayer.LuckEffect!=2,Global.ActivePlayer.LuckEffectEndTime<=TotalTimeElapsed)", repeat):
                checks.require(token in guarded, f"Multijump: guardia effettiva azione nativa {token}")
        if impulses:
            headers = [code(branch.splitlines()[0]) for branch in
                       conditional_branches_containing(runtime.body, impulses[0].start)]
            checks.require("If(" + ground + ");" in headers,
                           "Multijump: impulso solo sui salti successivi in aria")
        latch = runtime.body.find("Global.ActivePlayer.MultijumpConsumed = True;")
        checks.require(latch >= 0 and all(latch < call.start for call in (*impulses, *rings)),
                       "Multijump: consumare la pressione prima di impulso e ring")
        checks.require("Create Effect(" not in runtime.body and "Create HUD Text(" not in runtime.body,
                       "Multijump: il salto non deve creare entità persistenti")
    if apply:
        packed = code(mask_strings(apply.body))
        for token in ("EventPlayer.MultijumpCursor%=11;",
                      "EventPlayer.MultijumpEnabled=EventPlayer.MultijumpCursor!=0;",
                      "If(EventPlayer.MultijumpEnabled==True);EventPlayer.MultijumpLevel=EventPlayer.MultijumpCursor;End;",
                      "EventPlayer.MultijumpConsumed=IsButtonHeld(EventPlayer,Button(Jump));",
                      "EventPlayer.JumpWasGrounded=IsOnGround(EventPlayer);",
                      "EventPlayer.NextMultijumpTime=TotalTimeElapsed+0.300;"):
            checks.require(token in packed, f"Multijump: apply deve mantenere livello e sincronizzare Jump {token}")
    for name in ("PreparePlayer", "QuiescePlayer"):
        cleanup = rule_by_subroutine(rules, name)
        if cleanup:
            for token in ("EventPlayer.MultijumpEnabled=False;", "EventPlayer.MultijumpCursor=0;",
                          "EventPlayer.MultijumpLevel=1;", "EventPlayer.MultijumpConsumed=False;",
                          "EventPlayer.JumpWasGrounded=True;", "EventPlayer.NextMultijumpTime=0;"):
                checks.require(token in code(mask_strings(cleanup.body)), f"Multijump: reset {name} {token}")
    for owner in rules:
        writers = re.findall(r"\.(MultijumpLevel)\s*=(?!=)", mask_strings(owner.body))
        checks.require(not writers or subroutine_target(owner) in
                       {"PreparePlayer", "QuiescePlayer", "ApplyMultijumpPage"},
                       "Multijump: spinta fissa, il salto non deve cambiare il livello scelto")
        cooldown_writes = re.findall(r"\.NextMultijumpTime\s*=(?!=)", mask_strings(owner.body))
        checks.require(not cooldown_writes or subroutine_target(owner) in
                       {"PreparePlayer", "QuiescePlayer", "ApplyMultijumpPage", "ProcessMultijump"},
                       "Multijump: cooldown per player deve avere owner locali espliciti")
    checks.require("EventPlayer.MultijumpCursor=(EventPlayer.MultijumpCursor+(EventPlayer.MenuCommand==3?1:10))%11;"
                   in code(mask_strings(source)), "Multijump: navigazione OFF + dieci valori deve avvolgersi in entrambe le direzioni")
    if renderer:
        calls = list(iter_calls(renderer.body, "Create HUD Text"))
        checks.equal(len(calls), 1, "Multijump: unico HUD menu")
        for token in ("14 - MULTIJUMP", "AIR BOOST", "IN AIR: TAP / HOLD JUMP"):
            checks.require(token in renderer.body, f"Multijump: menu inglese {token}")
        checks.equal(renderer.body.count("Event Player.MultijumpCursor * 100"), 1,
                     "Multijump: preview 100..1000% in passi100")
        checks.equal(renderer.body.count("Event Player.MultijumpLevel * 100"), 1,
                     "Multijump: spinta applicata fissa")
        checks.equal(renderer.body.count("{0}/11"), 1, "Multijump: undici scelte menu")

def validate_ghost_fly(
    checks: Checks,
    source: str,
    rules: list[Rule],
    player_entries: list[Declaration],
    subroutines: set[str],
) -> None:
    """Validate page 13, its independent states and exclusive physics ownership."""

    def packed(expression: str) -> str:
        return re.sub(r"\s+", "", mask_strings(expression))

    expected_variables = {
        "GhostModeActive": 101,
        "FlyModeActive": 102,
        "GhostFlyCursor": 103,
        "GhostFlyPhysicsApplied": 104,
        "FlyRampStartTime": 106,
        "FlyPercent": 107,
        "FlyDirection": 108,
        "FlyVelocityDelta": 109,
    }
    for name, index in expected_variables.items():
        declarations = [entry for entry in player_entries if entry.name == name]
        checks.equal(len(declarations), 1, f"Ghost/Fly: dichiarazione {name}")
        if declarations:
            checks.equal(declarations[0].index, index, f"Ghost/Fly: indice {name}")

    required_subroutines = {
        "DrawGhostFlyMenu",
        "ApplyGhostFlyPage",
        "ApplyGhostFlyPhysics",
        "ProcessPlayerFlight",
    }
    checks.require(required_subroutines <= subroutines,
                   "Ghost/Fly: subroutine pagina 13 incomplete")
    checks.require("ProcessPlayerFlight" in subroutines,
                   "Fly: dichiarazione subroutine motore 20 Hz assente")

    apply = rule_by_subroutine(rules, "ApplyGhostFlyPage")
    physics = rule_by_subroutine(rules, "ApplyGhostFlyPhysics")
    cycle = rule_by_subroutine(rules, "ProcessPlayerCycle")
    motor = rule_by_subroutine(rules, "ProcessPlayerFlight")
    setup = rule_by_subroutine(rules, "PreparePlayer")
    quiet = rule_by_subroutine(rules, "QuiescePlayer")
    fast = rule_by_subroutine(rules, "ProcessPlayerFastState")

    checks.require(apply is not None, "Ghost/Fly: handler applicazione assente")
    if apply:
        apply_packed = packed(apply.body)
        for token, label in (
            ("If(EventPlayer.GhostFlyCursor==0);", "selezione riga"),
            ("EventPlayer.GhostModeActive=EventPlayer.GhostModeActive==False;", "toggle pareti"),
            ("EventPlayer.FlyModeActive=EventPlayer.FlyModeActive==False;", "toggle volo"),
            ("EventPlayer.GhostFlyPhysicsApplied=False;", "riarmo fisica"),
            ("CallSubroutine(ApplyGhostFlyPhysics);", "applicazione fisica immediata"),
        ):
            checks.require(token in apply_packed, f"Ghost/Fly applicazione incompleta: {label}")
        checks.require(not wait_calls(apply.body) and action_loop_count(apply.body) == 0,
                       "Ghost/Fly: handler applicazione deve essere atomico")

    checks.require(physics is not None, "Ghost/Fly: controller fisica locale assente")
    if physics:
        physics_packed = packed(physics.body)
        for token, label in (
            (
                "If(EventPlayer.GhostModeActive==True);"
                "DisableMovementCollisionWithEnvironment(EventPlayer,False);"
                "Else;EnableMovementCollisionWithEnvironment(EventPlayer);End;",
                "collisione pareti indipendente con pavimenti solidi",
            ),
            (
                "If(EventPlayer.FlyModeActive==True);"
                "If(Or(EventPlayer.LuckEffect!=2,EventPlayer.LuckEffectEndTime<=TotalTimeElapsed));"
                "SetMoveSpeed(EventPlayer,0);End;SetGravity(EventPlayer,0);",
                "locomozione nativa disabilitata e gravità zero nel volo 3D",
            ),
            (
                "Else;If(Or(EventPlayer.LuckEffect!=2,EventPlayer.LuckEffectEndTime<=TotalTimeElapsed));"
                "SetMoveSpeed(EventPlayer,100);",
                "ripristino motore Fly senza interrompere Acceleration di Try Your Luck",
            ),
            (
                "If(MagnitudeOf(VelocityOf(EventPlayer))>0.010);"
                "ApplyImpulse(EventPlayer,VelocityOf(EventPlayer)*-1,MagnitudeOf(VelocityOf(EventPlayer)),"
                "ToWorld,IncorporateContraryMotion);End;",
                "arresto deriva locale a Fly disattivato",
            ),
            ("EventPlayer.GhostFlyPhysicsApplied=True;", "latch applicato"),
            ("StopTransformingThrottle(EventPlayer);", "input locali non trasformati"),
            ("EventPlayer.FlyRampStartTime=-1;", "riarmo rampa"),
            ("SetGravity(EventPlayer,100);", "ripristino gravità a Fly OFF"),
        ):
            checks.require(token in physics_packed, f"Ghost/Fly fisica locale incompleta: {label}")
        checks.require(
            "StartAccelerating(" not in physics_packed and "StopAccelerating(" not in physics_packed,
            "Ghost/Fly: il controller locale non deve possedere Start/Stop Accelerating",
        )
        checks.require("MovementCollisionWithPlayers" not in physics_packed,
                       "Ghost/Fly non deve modificare la collisione fra giocatori")
        checks.require(not wait_calls(physics.body) and action_loop_count(physics.body) == 0,
                       "Ghost/Fly: controller fisica locale deve essere atomico")
        for call in iter_calls(physics.body, "Apply Impulse"):
            headers = [packed(branch.splitlines()[0]) for branch in
                       conditional_branches_containing(physics.body, call.start)]
            checks.require(
                "If(Or(EventPlayer.LuckEffect!=2,EventPlayer.LuckEffectEndTime<=TotalTimeElapsed));" in headers,
                "Fly OFF: il freno locale non deve cancellare Acceleration di Try Your Luck",
            )

    checks.require(cycle is not None, "Ghost/Fly: controller globale 10 Hz assente")
    if cycle:
        cycle_packed = packed(cycle.body)
        for token, label in (
            ("Global.ActivePlayer.IsHuman==True", "guardia umano"),
            ("Global.ActivePlayer.IsAutomaticBot==False", "esclusione iBot"),
            ("IsDummyBot(Global.ActivePlayer)==False", "esclusione dummy"),
            ("Global.ActivePlayer.GhostFlyPhysicsApplied==False", "riapplicazione a latch"),
            ("DisableMovementCollisionWithEnvironment(Global.ActivePlayer,False);", "riapplicazione pareti"),
            ("SetGravity(Global.ActivePlayer,0);", "riapplicazione gravità zero"),
            ("SetMoveSpeed(Global.ActivePlayer,Global.ActivePlayer.FlyModeActive==True?0:100);",
             "riapplicazione motore 3D senza locomozione nativa"),
        ):
            checks.require(token in cycle_packed, f"Ghost/Fly controller 10 Hz incompleto: {label}")
        checks.require("StartForcingPlayerPosition(" not in cycle_packed,
                       "Fly non deve immobilizzare con forcing di posizione")
        checks.require("FacingDirectionOf(Global.ActivePlayer)*-1" not in cycle_packed,
                       "Fly non deve forzare input indietro sulla visuale")
        checks.require(
            "DotProduct(ThrottleOf(Global.ActivePlayer),FacingDirectionOf(Global.ActivePlayer))"
            not in cycle_packed,
            "Fly non deve mescolare il throttle locale con una direzione world-space",
        )
        checks.require(
            "StartAccelerating(" not in cycle_packed and "StopAccelerating(" not in cycle_packed,
            "Ghost/Fly: il ciclo globale non deve possedere Start/Stop Accelerating",
        )
        checks.equal(len(list(iter_calls(cycle.body, "Apply Impulse"))), 0,
                     "Fly: il ciclo 10 Hz non deve possedere impulsi del motore 20 Hz")

    checks.require(motor is not None, "Fly: motore 3D per-player 20 Hz assente")
    if motor:
        motor_packed = packed(motor.body)
        guard_tokens = (
            "Global.ActivePlayer.IsHuman==True",
            "Global.ActivePlayer.IsAutomaticBot==False",
            "IsDummyBot(Global.ActivePlayer)==False",
            "HasSpawned(Global.ActivePlayer)==True",
            "IsAlive(Global.ActivePlayer)==True",
            "Global.ActivePlayer.FlyModeActive==True",
            "Global.ActivePlayer.GhostFlyPhysicsApplied==True",
        )
        direction_guard = (
            "If(MagnitudeOf(Vector(XComponentOf(ThrottleOf(Global.ActivePlayer)),0,"
            "ZComponentOf(ThrottleOf(Global.ActivePlayer))))>0.050);"
        )
        ramp = (
            "Global.ActivePlayer.FlyPercent=Min(1000,100+Max(0,TotalTimeElapsed-"
            "Global.ActivePlayer.FlyRampStartTime)*45);"
        )
        for token, label in (
            (direction_guard, "rampa con qualsiasi input direzionale locale oltre la zona morta"),
            ("If(Global.ActivePlayer.FlyRampStartTime<0);"
             "Global.ActivePlayer.FlyRampStartTime=TotalTimeElapsed;End;",
             "timestamp per-player avviato al primo input direzionale"),
            (ramp, "rampa Fly lineare 100%-1000% in 20 secondi"),
            ("Else;Global.ActivePlayer.FlyRampStartTime=-1;"
             "Global.ActivePlayer.FlyPercent=100;End;",
             "solo assenza di input direzionale deve riarmare timestamp e velocità 100%"),
            ("Global.ActivePlayer.FlyDirection=FacingDirectionOf(Global.ActivePlayer)*"
             "Max(0,ZComponentOf(ThrottleOf(Global.ActivePlayer)))+DirectionFromAngles("
             "HorizontalFacingAngleOf(Global.ActivePlayer),0)*Min(0,ZComponentOf(ThrottleOf("
             "Global.ActivePlayer)))+CrossProduct(Vector(0,1,0),DirectionFromAngles(HorizontalFacingAngleOf("
             "Global.ActivePlayer),0))*XComponentOf(ThrottleOf(Global.ActivePlayer));",
             "direzione Fly: solo l'input avanti usa il pitch, mentre indietro/strafe restano orizzontali"),
            ("If(MagnitudeOf(Global.ActivePlayer.FlyDirection)>0.050);"
             "Global.ActivePlayer.FlyVelocityDelta=Normalize(Global.ActivePlayer.FlyDirection)*5.500*"
             "Global.ActivePlayer.FlyPercent/100*Min(1,MagnitudeOf(ThrottleOf(Global.ActivePlayer)))-"
             "VelocityOf(Global.ActivePlayer);",
             "velocità target 3D con baseline 5.5 m/s, limite diagonale e sottrazione velocità attuale"),
            ("Else;Global.ActivePlayer.FlyVelocityDelta=VelocityOf(Global.ActivePlayer)*-1;End;",
             "impulso esattamente opposto alla deriva senza input"),
            ("If(MagnitudeOf(Global.ActivePlayer.FlyVelocityDelta)>0.010);"
             "ApplyImpulse(Global.ActivePlayer,Global.ActivePlayer.FlyVelocityDelta,"
             "MagnitudeOf(Global.ActivePlayer.FlyVelocityDelta),ToWorld,IncorporateContraryMotion);End;",
             "correzione velocità tramite unico impulso delta non nullo"),
        ):
            checks.require(token in motor_packed, f"Fly motore 3D incompleto: {label}")

        luck_prefix = (
            "If(And(Global.ActivePlayer.LuckEffect==2,"
            "Global.ActivePlayer.LuckEffectEndTime>TotalTimeElapsed));"
            "Global.ActivePlayer.FlyRampStartTime=-1;"
            "Global.ActivePlayer.FlyPercent=100;"
            "Global.ActivePlayer.FlyDirection=Vector(0,0,0);"
            "Global.ActivePlayer.FlyVelocityDelta=Vector(0,0,0);"
            "Else;SetMoveSpeed(Global.ActivePlayer,0);"
        )
        checks.require(luck_prefix in motor_packed,
                       "Fly: Try Your Luck Acceleration deve avere precedenza senza scritture fisiche")
        motor_actions = list(iter_calls(motor.body, "Apply Impulse")) + list(iter_calls(motor.body, "Set Move Speed"))
        checks.equal(len(list(iter_calls(motor.body, "Apply Impulse"))), 1,
                     "Fly deve avere un solo impulso delta nel motore 20 Hz")
        checks.equal(len(list(iter_calls(motor.body, "Set Move Speed"))), 1,
                     "Fly deve disabilitare una sola volta la locomozione nativa nel motore 20 Hz")
        for call in motor_actions:
            branches = conditional_branches_containing(motor.body, call.start)
            headers = [packed(branch.splitlines()[0]) for branch in branches]
            checks.require(any(all(token in header for token in guard_tokens) for header in headers),
                           "motore Fly deve restare nella guardia per-player umano vivo Fly ON con latch")
            checks.require(any(packed(branch).startswith("Else;SetMoveSpeed(Global.ActivePlayer,0);")
                               for branch in branches),
                           "motore e freno Fly devono saltare l'esito Acceleration ancora attivo")
        ramp_matches = list(re.finditer(r"Global\.ActivePlayer\.FlyPercent\s*=\s*Min\(", mask_strings(motor.body)))
        checks.equal(len(ramp_matches), 1, "Fly deve avere una sola rampa percentuale progressiva")
        if ramp_matches:
            headers = [packed(branch.splitlines()[0]) for branch in
                       conditional_branches_containing(motor.body, ramp_matches[0].start())]
            checks.require(direction_guard in headers,
                           "rampa percentuale deve restare nella guardia di qualsiasi input direzionale")
        for forbidden, label in (
            ("StartAccelerating(", "Start/Stop Accelerating"),
            ("StopAccelerating(", "Start/Stop Accelerating"),
            ("StartForcingPlayerPosition(", "forcing di posizione"),
            ("StartForcingThrottle(", "forcing degli input"),
            ("StartThrottleInDirection(", "forcing degli input"),
            ("FacingDirectionOf(Global.ActivePlayer)*-1", "input indietro forzato"),
        ):
            checks.require(forbidden not in motor_packed, f"Fly: il motore non deve usare {label}")
        checks.require(not wait_calls(motor.body) and action_loop_count(motor.body) == 0,
                       "Fly: motore 3D deve essere atomico senza Wait/Loop")

    for owner, label in ((setup, "setup iniziale"), (quiet, "quiete uscita/rejoin")):
        checks.require(owner is not None, f"Ghost/Fly: {label} assente")
        if owner:
            owner_packed = packed(owner.body)
            for token in (
                "EventPlayer.GhostModeActive=False;",
                "EventPlayer.FlyModeActive=False;",
                "EventPlayer.GhostFlyCursor=0;",
                "EventPlayer.GhostFlyPhysicsApplied=False;",
                "EventPlayer.FlyRampStartTime=-1;",
                "EventPlayer.FlyPercent=100;",
                "EventPlayer.FlyDirection=Vector(0,0,0);",
                "EventPlayer.FlyVelocityDelta=Vector(0,0,0);",
                "SetMoveSpeed(EventPlayer,100);",
                "StopTransformingThrottle(EventPlayer);",
                "SetGravity(EventPlayer,100);",
                "EnableMovementCollisionWithEnvironment(EventPlayer);",
            ):
                checks.require(token in owner_packed,
                               f"Ghost/Fly {label} incompleto: {token}")

    team_switch = team_switch_worker(rules)
    checks.require(team_switch is not None, "Ghost/Fly: lifecycle cambio squadra Each Player assente")
    if team_switch:
        masked_switch = mask_strings(team_switch.body)
        checks.require("Call Subroutine(QuiescePlayer);" not in masked_switch,
                       "Ghost/Fly: detector team-switch non deve resettare engine durante transizione nativa")
        checks.require("Call Subroutine(CleanupPlayer);" not in masked_switch,
                       "Ghost/Fly: detector team-switch non deve fare cleanup durante transizione nativa")
        setup_worker = next((
            rule for rule in rules
            if event_type(rule) == "Ongoing - Each Player"
            and "Call Subroutine(PreparePlayer);" in rule.body
            and "Event Player.TeamCycleDeadline" in rule.body
        ), None)
        checks.require(setup_worker is not None, "Ghost/Fly: worker setup serializzato team-switch assente")
        if setup_worker:
            masked_setup = mask_strings(setup_worker.body)
            checks.require("Call Subroutine(QuiescePlayer);" in masked_setup,
                           "Ghost/Fly: reset engine team-switch deve avvenire nel worker serializzato")
            checks.require("Call Subroutine(CleanupPlayer);" in masked_setup,
                           "Ghost/Fly: cleanup team-switch deve avvenire nel worker serializzato")

    timestamp_writers: list[tuple[str, str]] = []
    for rule in rules:
        owner = subroutine_target(rule) or rule.name
        for target in ("Event Player", "Global.ActivePlayer"):
            for match in re.finditer(
                rf"{re.escape(target)}\.FlyRampStartTime\s*=(?!=)\s*([^;\r\n]+);",
                mask_strings(rule.body),
            ):
                timestamp_writers.append((owner, re.sub(r"\s+", "", match.group(1))))
    checks.equal(len(timestamp_writers), 10, "Fly: numero writer timestamp setup/lifecycle/runtime")
    checks.equal(
        sum(value == "-1" for _, value in timestamp_writers),
        9,
        "Fly: reset timestamp a -1",
    )
    checks.equal(
        sum(value == "TotalTimeElapsed" for _, value in timestamp_writers),
        1,
        "Fly: unico avvio timestamp da Total Time Elapsed",
    )
    checks.require(
        ("ProcessPlayerFlight", "TotalTimeElapsed") in timestamp_writers,
        "Fly: timestamp Forward deve essere avviato dal motore per-player 20 Hz",
    )
    for variable, count in (("FlyPercent", 5), ("FlyDirection", 4), ("FlyVelocityDelta", 5)):
        writers = []
        all_writes = 0
        for rule in rules:
            all_writes += len(re.findall(rf"\b{variable}\s*=(?!=)", mask_strings(rule.body)))
            for action in ("Set Player Variable", "Modify Player Variable", "Set Player Variable At Index",
                           "Modify Player Variable At Index"):
                all_writes += sum(len(call.args) >= 2 and call.args[1].strip() == variable
                                  for call in iter_calls(rule.body, action))
            for match in re.finditer(
                rf"(Event Player|Global\.ActivePlayer)\.{variable}\s*=(?!=)", mask_strings(rule.body)
            ):
                writers.append((subroutine_target(rule), match.group(1)))
        checks.equal(len(writers), count, f"Fly: numero writer {variable}")
        checks.equal(all_writes, len(writers), f"Fly: scritture {variable} fuori dai target per-player autorizzati")
        checks.equal(set(writers), {
            ("PreparePlayer", "Event Player"),
            ("QuiescePlayer", "Event Player"),
            ("ProcessPlayerFlight", "Global.ActivePlayer"),
        }, f"Fly: owner per-player esclusivi di {variable}")

    for variable in ("GhostModeActive", "FlyModeActive"):
        writers: list[tuple[str, str]] = []
        for rule in rules:
            owner = subroutine_target(rule) or rule.name
            for match in re.finditer(
                rf"Event Player\.{variable}\s*=(?!=)\s*([^;\r\n]+);",
                mask_strings(rule.body),
            ):
                writers.append((owner, re.sub(r"\s+", "", match.group(1))))
        expected = {
            ("PreparePlayer", "False"),
            ("QuiescePlayer", "False"),
            ("ApplyGhostFlyPage", f"EventPlayer.{variable}==False"),
        }
        checks.equal(set(writers), expected, f"Ghost/Fly: owner writer {variable}")
        checks.equal(len(writers), len(expected), f"Ghost/Fly: numero writer {variable}")

    zero_gravity_owners = [
        (subroutine_target(rule) or rule.name, tuple(argument.strip() for argument in call.args))
        for rule in rules
        for call in iter_calls(rule.body, "Set Gravity")
        if len(call.args) >= 2 and call.args[1].strip() == "0"
    ]
    checks.equal(
        set(zero_gravity_owners),
        {
            ("ApplyGhostFlyPhysics", ("Event Player", "0")),
            ("ProcessPlayerCycle", ("Global.ActivePlayer", "0")),
        },
        "Ghost/Fly: gravità zero scritta fuori dai due controller dedicati",
    )
    checks.equal(len(zero_gravity_owners), 2, "Ghost/Fly: numero writer gravità zero")

    throttle_owners = [
        (subroutine_target(rule) or rule.name, tuple(argument.strip() for argument in call.args))
        for rule in rules
        for call in iter_calls(rule.body, "Start Transforming Throttle")
    ]
    checks.equal(throttle_owners, [], "Fly: input devono restare locali senza Start Transforming Throttle")

    for luck_owner in (
        "ApplyLuckPage",
        "ProcessPlayerLuck",
        "RestorePlayerLuck",
        "RestoreActivePlayerLuck",
    ):
        luck_rule = rule_by_subroutine(rules, luck_owner)
        checks.require(luck_rule is not None, f"Try Your Luck: owner {luck_owner} assente")
        if luck_rule:
            luck_packed = packed(luck_rule.body)
            for forbidden, label in (
                ("SetGravity(", "gravità"),
                ("StartTransformingThrottle(", "avvio throttle Fly"),
                ("StopTransformingThrottle(", "arresto throttle Fly"),
                ("StartForcingPlayerPosition(", "posizione forzata"),
            ):
                checks.require(forbidden not in luck_packed,
                               f"Try Your Luck non deve modificare {label}: {luck_owner}")
            for variable, label in (
                ("GhostModeActive", "toggle Ghost"),
                ("FlyModeActive", "toggle Fly"),
                ("GhostFlyPhysicsApplied", "latch fisica Fly"),
            ):
                checks.require(
                    re.search(rf"{variable}=(?!=)", luck_packed) is None,
                    f"Try Your Luck non deve modificare {label}: {luck_owner}",
                )

def validate_special_player_profile(
    checks: Checks,
    source: str,
    rules: list[Rule],
    player_entries: list[Declaration],
) -> None:
    """Validate the isolated defaults and soundtrack lock for player งูแรร์."""

    def code(expression: str) -> str:
        return re.sub(r"\s+", "", mask_strings(expression))

    def full_custom_string(expression: str) -> Call | None:
        expression = trim_outer_parentheses(expression)
        return next(
            (
                call
                for call in iter_calls(expression, "Custom String")
                if call.start == 0 and call.end == len(expression)
            ),
            None,
        )

    def direct_assignment_values(rule: Rule, name: str) -> list[str]:
        masked = mask_strings(rule.body)
        values: list[str] = []
        for match in re.finditer(
            rf"\bEvent Player\.{re.escape(name)}\s*=(?!=)\s*([^;\r\n]+);",
            masked,
        ):
            start, end = match.span(1)
            values.append(rule.body[start:end].strip())
        return values

    def soundtrack_choice(expression: str, label: str) -> str | None:
        special = parse_top_level_ternary(expression)
        checks.require(special is not None, f"{label}: ternario CustomSoundtrack assente")
        if special is None:
            return None
        special_condition, special_value, ordinary = special
        checks.equal(
            code(special_condition),
            "EventPlayer.CustomSoundtrack!=Null",
            f"{label}: condizione profilo speciale",
        )
        checks.equal(
            code(special_value),
            "EventPlayer.CustomSoundtrack",
            f"{label}: valore profilo speciale",
        )
        generic = parse_top_level_ternary(ordinary)
        checks.require(generic is not None, f"{label}: fallback generi ordinari assente")
        if generic is None:
            return None
        genre_condition, genre_value, fallback = generic
        checks.equal(
            code(genre_condition),
            "EventPlayer.GenreIndex>=0",
            f"{label}: condizione genere ordinario",
        )
        checks.equal(
            code(genre_value),
            "Global.GenreNames[EventPlayer.GenreIndex]",
            f"{label}: lookup genere ordinario",
        )
        return fallback

    declarations = [entry for entry in player_entries if entry.name == "CustomSoundtrack"]
    checks.equal(len(declarations), 1, "profilo speciale: dichiarazione CustomSoundtrack")
    if declarations:
        checks.equal(declarations[0].index, 98, "profilo speciale: indice CustomSoundtrack")

    setup = rule_by_subroutine(rules, "PreparePlayer")
    checks.require(setup is not None, "profilo speciale: PreparePlayer assente")
    if setup:
        checks.equal(
            direct_assignment_values(setup, "CustomSoundtrack"),
            ["Null"],
            "profilo speciale: inizializzazione CustomSoundtrack",
        )

    classifier = next(
        (rule for rule in rules if "Append To Array(Global.HumanPlayers, Event Player)" in rule.body),
        None,
    )
    checks.require(classifier is not None, "profilo speciale: classifier umano assente")
    profile_match: re.Match[str] | None = None
    if classifier:
        profile_match = re.search(
            r'If\s*\(\s*Event Player\.DisplayName\s*'
            r'==\s*Custom String\s*\(\s*"งูแรร์"\s*\)\s*\)\s*;',
            classifier.body,
        )
        checks.require(profile_match is not None, "profilo speciale: matcher งูแรร์ deve usare DisplayName stabile")
        checks.require(
            'If(Custom String("{0}", Event Player) == Custom String("งูแรร์"));' not in classifier.body,
            "profilo speciale: vietato usare il token player live dopo la cache Nome",
        )
        checks.equal(classifier.body.count('Custom String("งูแรร์")'), 1,
                     "profilo speciale: numero matcher Unicode งูแรร์")
        if profile_match:
            enclosing = conditional_branches_containing(classifier.body, profile_match.start())
            checks.require(bool(enclosing), "profilo speciale: matcher fuori da un ramo If isolato")
            if enclosing:
                expected_branch = '''
If(Event Player.DisplayName == Custom String("งูแรร์"));
    Event Player.CustomSoundtrack = Custom String("Draconian");
    Event Player.ColorIndex = 2;
    Event Player.ColorCursor = 2;
    Event Player.NameColor = Global.NameColors[2];
    Event Player.MenuColor = Global.NameColorRGBValues[2];
    Event Player.IconIndex = 23;
    Event Player.IconCursor = 23;
End;
'''
                checks.equal(
                    clipboard_import.canonical_semantic_text(enclosing[0], "en-US"),
                    clipboard_import.canonical_semantic_text(expected_branch, "en-US"),
                    "profilo speciale: blocco default isolato",
                )

            spans = [
                span for span in conditional_branch_spans(classifier.body)
                if span[0] <= profile_match.start() < span[1]
            ]
            profile_end = min(spans, key=lambda span: span[1] - span[0])[1] if spans else -1
            bot_match = re.search(
                r"If\s*\(\s*Event Player\.IsAutomaticBot\s*==\s*True\s*\)\s*;",
                classifier.body,
            )
            bot_spans = [
                span for span in conditional_branch_spans(classifier.body)
                if bot_match is not None and span[0] <= bot_match.start() < span[1]
            ]
            bot_end = min(bot_spans, key=lambda span: span[1] - span[0])[1] if bot_spans else -1
            checks.require(0 <= bot_end < profile_match.start(),
                           "profilo speciale: matcher deve seguire esclusione/Abort degli iBot")
            conditions = rule_block(classifier, "conditions") or ""
            checks.require("Is Dummy Bot(Event Player) == False;" in conditions,
                           "profilo speciale: matcher non protetto dall'esclusione dummy")

            ordered_defaults = (
                "Event Player.GenreIndex = -1;",
                "Event Player.ColorIndex = 0;",
                "Event Player.NameColor = Global.NameColors[Event Player.ColorIndex];",
            )
            positions = [classifier.body.find(token) for token in ordered_defaults]
            checks.require(
                all(position >= 0 for position in positions)
                and positions == sorted(positions)
                and positions[-1] < profile_match.start(),
                "profilo speciale: matcher deve seguire i default generici",
            )
            roster = classifier.body.find("Append To Array(Global.HumanPlayers, Event Player)")
            checks.require(
                profile_end >= 0 and profile_end < roster,
                "profilo speciale: matcher deve precedere inserimento roster/HUD",
            )

    direct_writers = [
        (subroutine_target(rule) or rule.name, value)
        for rule in rules
        for value in direct_assignment_values(rule, "CustomSoundtrack")
    ]
    checks.equal(len(direct_writers), 2, "profilo speciale: numero writer CustomSoundtrack")

    fast = rule_by_subroutine(rules, "ProcessPlayerFastState")
    checks.require(fast is not None, "profilo speciale: repair lifecycle assente")
    repair_match: re.Match[str] | None = None
    if fast:
        repair_match = re.search(
            r'If\s*\(\s*Global\.ActivePlayer\.DisplayName\s*'
            r'==\s*Custom String\s*\(\s*"งูแรร์"\s*\)\s*\)\s*;',
            fast.body,
        )
        checks.require(repair_match is not None, "profilo speciale: repair Unicode งูแรร์ assente")
        checks.equal(
            fast.body.count('Custom String("งูแรร์")'),
            1,
            "profilo speciale: numero matcher repair Unicode งูแรร์",
        )
        if repair_match:
            repair_spans = [
                span for span in conditional_branch_spans(fast.body)
                if span[0] <= repair_match.start() < span[1]
            ]
            checks.require(bool(repair_spans), "profilo speciale: repair fuori da un ramo If")
            if repair_spans:
                repair_start, repair_end = min(
                    repair_spans,
                    key=lambda span: span[1] - span[0],
                )
                repair_branch = fast.body[repair_start:repair_end]
                expected_repair = '''
If(Global.ActivePlayer.DisplayName == Custom String("งูแรร์"));
    Global.ActivePlayer.CustomSoundtrack = Custom String("Draconian");
    If(Global.ActivePlayer.WasPrepared == False);
        Global.ActivePlayer.ColorIndex = 2;
        Global.ActivePlayer.ColorCursor = 2;
        Global.ActivePlayer.NameColor = Global.NameColors[2];
        Global.ActivePlayer.MenuColor = Global.NameColorRGBValues[2];
        Global.ActivePlayer.IconIndex = 23;
        Global.ActivePlayer.IconCursor = 23;
    End;
End;
'''
                checks.equal(
                    clipboard_import.canonical_semantic_text(repair_branch, "en-US"),
                    clipboard_import.canonical_semantic_text(expected_repair, "en-US"),
                    "profilo speciale: repair default/lock isolato",
                )
            checks.require(
                any(
                    start <= repair_match.start() < end
                    and "Global.ActivePlayer.IsAutomaticBot == False" in fast.body[start:end]
                    and "Array Contains(Global.HumanPlayers, Global.ActivePlayer) == True"
                    in fast.body[start:end]
                    and "Global.ActivePlayer.WasPrepared == False" in fast.body[start:end]
                    for start, end in repair_spans
                ),
                "profilo speciale: repair deve seguire esclusione bot e stato registrato degradato",
            )

    property_writers = [
        (subroutine_target(rule) or rule.name, match.group("receiver").strip())
        for rule in rules
        for match in re.finditer(
            r"(?m)^[ \t]*(?P<receiver>[^;\r\n=]+?)\.CustomSoundtrack"
            r"(?:\s*\[[^\]\r\n]+\])?\s*=(?!=)",
            mask_strings(rule.body),
        )
    ]
    checks.equal(len(property_writers), 3, "profilo speciale: numero writer property CustomSoundtrack")
    checks.require(
        Counter(receiver for _, receiver in property_writers)
        == Counter({"Event Player": 2, "Global.ActivePlayer": 1}),
        f"profilo speciale: receiver writer inattesi CustomSoundtrack: {property_writers}",
    )
    action_writers = [
        (subroutine_target(rule) or rule.name, action)
        for rule in rules
        for action in (
            "Set Player Variable",
            "Set Player Variable At Index",
            "Modify Player Variable",
            "Modify Player Variable At Index",
            "Chase Player Variable At Rate",
            "Chase Player Variable Over Time",
            "Stop Chasing Player Variable",
        )
        for call in iter_calls(rule.body, action)
        if len(call.args) >= 2 and call.args[1].strip() == "CustomSoundtrack"
    ]
    checks.require(not action_writers, f"profilo speciale: writer azione inattesi CustomSoundtrack: {action_writers}")

    draconian_calls = [
        call
        for call in iter_calls(source, "Custom String")
        if call.args and parse_literal(call.args[0]) == "Draconian"
    ]
    checks.equal(len(draconian_calls), 2, "profilo speciale: Draconian deve coprire setup e repair")
    genres = array_assignment_items(source, "GenreNames")
    checks.require(genres is not None, "profilo speciale: array dei 200 generi assente")
    if genres is not None:
        checks.equal(len(genres), 200, "profilo speciale: numero generi ordinari")
        genre_literals = {
            parse_literal(call.args[0])
            for item in genres
            for call in iter_calls(item, "Custom String")
            if call.args
        }
        checks.equal(len(genre_literals), 200, "catalogo musicale: 200 nomi unici")
        checks.require(all(isinstance(label, str) and label.strip() for label in genre_literals),
                       "catalogo musicale: nomi non vuoti")
        checks.require("Draconian" not in genre_literals,
                       "profilo speciale: Draconian inserito nei 200 generi ordinari")

    color_names = array_assignment_items(source, "ColorNames")
    checks.require(color_names is not None and len(color_names) > 1,
                   "profilo speciale: nomi colore inglesi assenti")
    if color_names is not None and len(color_names) > 1:
        silver = next(iter(iter_calls(color_names[1], "Custom String")), None)
        checks.equal(
            parse_literal(silver.args[0]) if silver and silver.args else None,
            "Silver Mist",
            "profilo speciale: colore indice 1",
        )
    colors = array_assignment_items(source, "NameColors")
    checks.require(colors is not None and len(colors) > 1,
                   "profilo speciale: palette colori non copre indice 1")
    if colors is not None and len(colors) > 1:
        checks.equal(
            code(colors[1]),
            "CustomColor(190,210,230,255)",
            "profilo speciale: valore Silver Mist indice 1",
        )
    color_vectors = array_assignment_items(source, "NameColorRGBValues")
    checks.require(color_vectors is not None and len(color_vectors) > 1,
                   "profilo speciale: palette RGB non copre indice 1")
    if color_vectors is not None and len(color_vectors) > 1:
        checks.equal(
            code(color_vectors[1]),
            "Vector(190,210,230)",
            "profilo speciale: vettore Silver Mist indice 1",
        )
    icons = array_assignment_items(source, "PlayerIcons")
    checks.require(icons is not None and len(icons) > 23,
                   "profilo speciale: array icone non copre indice 23")
    if icons is not None and len(icons) > 23:
        checks.equal(code(icons[23]), "IconString(Poison2)", "profilo speciale: icona indice 23")

    roster_rule = next(
        (
            rule for rule in rules
            if "Event Player.PlayerHudCreated = True;" in rule.body
        ),
        None,
    )
    checks.require(roster_rule is not None, "profilo speciale: renderer roster assente")
    if roster_rule:
        vibe_roster_calls = [
            call for call in iter_calls(roster_rule.body, "Create HUD Text")
            if len(call.args) >= 5 and call.args[4].strip() == "Left"
        ]
        checks.equal(len(vibe_roster_calls), 1, "profilo speciale: renderer roster Left")
        vibe_calls = [
            call
            for call in iter_calls(vibe_roster_calls[0].args[2], "Custom String")
            if vibe_roster_calls and len(call.args) == 3
            and parse_literal(call.args[0]) == "{0} - {1}"
            and call.args[1].strip() in {
                "Event Player",
                "Event Player.DisplayName",
                "Evaluate Once(Event Player.DisplayName)",
            }
        ] if vibe_roster_calls else []
        checks.equal(len(vibe_calls), 1, "profilo speciale: espressione Player Vibes roster")
        if vibe_calls:
            fallback = soundtrack_choice(vibe_calls[0].args[2], "profilo speciale roster")
            custom = full_custom_string(fallback) if fallback is not None else None
            checks.equal(parse_literal(custom.args[0]) if custom and custom.args else None,
                         "no soundtrack yet", "Special profile roster: ordinary English fallback")

    main_menu = rule_by_subroutine(rules, "DrawMainMenu")
    checks.require(main_menu is not None, "profilo speciale: DrawMainMenu assente")
    if main_menu:
        main_calls = list(iter_calls(main_menu.body, "Create HUD Text"))
        main_text = main_calls[0].args[3] if main_calls and len(main_calls[0].args) >= 4 else ""
        soundtrack_values = [
            call for call in iter_calls(main_text, "Custom String")
            if len(call.args) == 2 and parse_literal(call.args[0]) == "NOW: {0}"
            and "Event Player.CustomSoundtrack" in call.args[1]
        ]
        checks.equal(len(soundtrack_values), 1, "Special profile: one main Soundtrack preview")
        if soundtrack_values:
            fallback = soundtrack_choice(soundtrack_values[0].args[1], "Special profile main menu")
            custom = full_custom_string(fallback) if fallback is not None else None
            checks.equal(parse_literal(custom.args[0]) if custom and custom.args else None,
                         "no soundtrack yet", "Special profile main menu: ordinary English fallback")

    music_page = rule_by_subroutine(rules, "DrawSoundtrackMenu")
    checks.require(music_page is not None, "Special profile: Soundtrack renderer missing")
    if music_page:
        page_calls = list(iter_calls(music_page.body, "Create HUD Text"))
        checks.equal(len(page_calls), 1, "Special profile: one Soundtrack HUD")
        if page_calls and len(page_calls[0].args) >= 4:
            def content_parts(expression: str) -> list[str]:
                custom = full_custom_string(expression)
                if custom and len(custom.args) == 3 and parse_literal(custom.args[0]) in ("{0} | {1}", "{0}\n{1}"):
                    return content_parts(custom.args[1]) + content_parts(custom.args[2])
                return [expression]

            subtitle = page_calls[0].args[2]
            checks.require(subtitle.strip() != "Null", "Locked Soundtrack: command subtitle missing")
            functions = content_parts(page_calls[0].args[3])
            subtitle_choice = parse_top_level_ternary(subtitle)
            checks.require(subtitle_choice is not None,
                           "Soundtrack commands must branch on the owner's soundtrack lock")
            if subtitle_choice:
                condition, locked_subtitle, ordinary_subtitle = subtitle_choice
                checks.equal(code(condition), "EventPlayer.CustomSoundtrack!=Null",
                             "Soundtrack commands must branch on the owner's soundtrack lock")
            else:
                locked_subtitle = ordinary_subtitle = subtitle
            checks.equal(len(content_parts(locked_subtitle)), 3, "Locked Soundtrack: three compact command groups")
            checks.equal(len(content_parts(ordinary_subtitle)), 5, "Soundtrack: five command groups in Subheader")
            checks.equal(len(functions), 4, "Soundtrack: four function rows in Text")
            locked_bindings = [call.args[0].strip() for call in iter_calls(locked_subtitle, "Input Binding String")
                               if call.args]
            locked_values = []
            unlocked_values = [ordinary_subtitle]
            for part in functions:
                choice = parse_top_level_ternary(part)
                if choice is None:
                    continue
                condition, locked, unlocked = choice
                checks.equal(code(condition), "EventPlayer.CustomSoundtrack!=Null",
                             "Soundtrack rows must branch on the owner's soundtrack lock")
                locked_bindings += [call.args[0].strip() for call in iter_calls(locked, "Input Binding String")
                                    if call.args]
                locked_values += [parse_literal(call.args[0]) for call in iter_calls(locked, "Custom String")
                                  if call.args]
                unlocked_values.append(unlocked)
            checks.equal(tuple(locked_bindings), ("Button(Crouch)", "Button(Reload)", "Button(Melee)"),
                         "Locked Soundtrack: only Crouch, back and close commands")
            checks.require("SOUNDTRACK LOCKED" in locked_values and "NOW: {0}" in locked_values,
                           "Locked Soundtrack: English heading and current value")
            checks.require(any("Event Player.CustomSoundtrack" in part for part in functions),
                           "Locked Soundtrack: display the custom soundtrack value")
            ordinary = " ".join(unlocked_values)
            for token in ("Event Player.GenreCursor", "Global.GenreNames", "{0}/{1}",
                          "Count Of(Global.GenreNames)", "Event Player.GenreCursor / 20"):
                checks.require(token in ordinary, f"Soundtrack: ordinary branch missing: {token}")
            for button in ("Crouch", "Primary Fire", "Secondary Fire", "Ability 1", "Ability 2",
                           "Interact", "Reload", "Melee"):
                checks.require(f"Input Binding String(Button({button}))" in ordinary,
                               f"Soundtrack: ordinary controls missing: {button}")

    navigation = next(
        (
            rule for rule in rules
            if "Event Player.GenreCursor = (Event Player.GenreCursor" in rule.body
            and "Event Player.MenuCommand == 3" in rule.body
            and "Event Player.MenuCommand == 4" in rule.body
        ),
        None,
    )
    checks.require(navigation is not None, "profilo speciale: navigazione Soundtrack ±1 assente")
    if navigation:
        update = navigation.body.find("Event Player.GenreCursor = (Event Player.GenreCursor")
        branches = conditional_branches_containing(navigation.body, update) if update >= 0 else []
        checks.require(bool(branches), "profilo speciale: update Soundtrack ±1 fuori da un ramo")
        if branches:
            checks.require(
                re.search(
                    r"Else If\s*\(\s*And\s*\(\s*Event Player\.MenuPage\s*==\s*3\s*,\s*"
                    r"Event Player\.CustomSoundtrack\s*==\s*Null\s*\)\s*\)\s*;",
                    branches[0],
                ) is not None,
                "profilo speciale: guardia Soundtrack ±1",
            )

    jump = next(
        (
            rule for rule in rules
            if "Event Player.GenreCursor = (Event Player.GenreCursor" in rule.body
            and "Event Player.MenuCommand == 5" in rule.body
            and "Event Player.MenuCommand == 6" in rule.body
        ),
        None,
    )
    checks.require(jump is not None, "profilo speciale: navigazione Soundtrack ±10 assente")
    if jump:
        conditions = rule_block(jump, "conditions") or ""
        checks.require(
            "EventPlayer.CustomSoundtrack==Null;" in code(conditions),
            "profilo speciale: guardia Soundtrack ±10",
        )

    apply_music = rule_by_subroutine(rules, "ApplySoundtrackPage")
    checks.require(apply_music is not None, "profilo speciale: ApplySoundtrackPage assente")
    if apply_music:
        actions = rule_block(apply_music, "actions") or ""
        checks.require(
            re.match(
                r"\s*Abort If\s*\(\s*Event Player\.CustomSoundtrack\s*!=\s*Null\s*\)\s*;",
                actions,
            ) is not None,
            "profilo speciale: ApplySoundtrackPage deve iniziare con la guardia locked",
        )


def validate_catalog_feedback(checks: Checks, source: str, rules: list[Rule]) -> None:
    """Keep catalog indexing aligned and reserve ephemeral rings for jump feedback."""
    palettes = {}
    for name in ("NameColors", "NameColorRGBValues", "ColorNames"):
        items = array_assignment_items(source, name)
        palettes[name] = items
        checks.equal(len(items) if items is not None else None, 40, f"palette: 40 voci allineate in {name}")
        checks.require(items is not None and all(item.strip() for item in items),
                       f"palette: 40 voci non vuote in {name}")
    for name in ("ColorNames",):
        items = palettes[name]
        if items is None:
            continue
        labels = []
        for item in items:
            calls = list(iter_calls(item, "Custom String"))
            labels.append(parse_literal(calls[0].args[0])
                          if len(calls) == 1 and len(calls[0].args) == 1 else None)
        checks.require(all(isinstance(label, str) and label.strip() for label in labels),
                       f"palette: nomi colore non vuoti in {name}")
        checks.equal(len(set(labels)), len(items), f"palette: nomi colore unici in {name}")

    def palette_components(item: str, function: str, count: int) -> tuple[int, ...] | None:
        if function == "Custom Color":
            named = list(iter_calls(item, "Color"))
            if len(named) == 1 and len(named[0].args) == 1 and named[0].raw == item.strip():
                color_name = re.sub(r"\s+", "", named[0].args[0])
                return next((components for components, name in clipboard_import.EQUIVALENT_NAMED_COLORS
                             if re.sub(r"\s+", "", name) == color_name), None)
        calls = list(iter_calls(item, function))
        if len(calls) != 1 or len(calls[0].args) != count or calls[0].raw != item.strip():
            return None
        if not all(re.fullmatch(r"\d+", argument.strip()) for argument in calls[0].args):
            return None
        return tuple(int(argument.strip()) for argument in calls[0].args)

    colors, vectors = palettes["NameColors"], palettes["NameColorRGBValues"]
    if colors is not None and vectors is not None:
        for index, (color, vector) in enumerate(zip(colors, vectors)):
            rgba = palette_components(color, "Custom Color", 4)
            rgb = palette_components(vector, "Vector", 3)
            checks.require(rgba is not None and rgba[3] == 255
                           and all(0 <= component <= 255 for component in rgba[:3]),
                           f"palette: colore RGB valido indice {index}")
            checks.require(rgb is not None and all(0 <= component <= 255 for component in rgb),
                           f"palette: vettore RGB valido indice {index}")
            if rgba is not None and rgb is not None:
                checks.equal(rgb, rgba[:3], f"palette: RGB nome e menu allineati indice {index}")
    for name in ("MenuPageNames",):
        items = array_assignment_items(source, name)
        checks.equal(len(items) if items is not None else None, 10, f"catalogo musicale: dieci gruppi in {name}")
    for rule in rules:
        masked = mask_strings(rule.body)
        if "Event Player.GenreCursor = (Event Player.GenreCursor" in masked:
            checks.require("% Count Of(Global.GenreNames)" in masked,
                           "catalogo musicale: navigazione limitata alla lunghezza corrente")
            checks.require("Count Of(Global.GenreNames) -" in masked,
                           "catalogo musicale: passo indietro dinamico")
        effects = list(iter_calls(rule.body, "Play Effect"))
        persistent = list(iter_calls(rule.body, "Create Effect"))
        beacon = (len(persistent) == 1 and event_type(rule) == "Ongoing - Global"
                  and "Global.IsReady = True;" in rule.body and len(persistent[0].args) == 6
                  and persistent[0].args[1].strip() == "Light Shaft")
        checks.require(not persistent or beacon, f"feedback visuale: nessun effetto persistente fuori dal pilar iniziale in {rule.name}")
        checks.require(not effects or subroutine_target(rule) == "ProcessMultijump",
                       f"feedback visuale: effetti consentiti soltanto per Multijump, trovato {rule.name}")
        checks.require("EfekTerapkan" not in masked,
                       "feedback visuale: vecchio impulso menu ancora presente")
        for action in ("Chase Player Variable Over Time", "Chase Player Variable At Rate", "Stop Chasing Player Variable"):
            for call in iter_calls(rule.body, action):
                if len(call.args) < 2 or call.args[1].strip() != "MenuColor":
                    continue
                expected_owner = "QuiescePlayer" if action == "Stop Chasing Player Variable" else "TransitionMenuColor"
                checks.require(action != "Chase Player Variable At Rate" and subroutine_target(rule) == expected_owner,
                               "feedback visuale: transizione colore fuori dal proprietario consentito")
                checks.equal(call.args[0].strip(), "Event Player", "feedback visuale: colore deve essere individuale")
                if action == "Chase Player Variable Over Time":
                    checks.equal(len(call.args), 5, "feedback visuale: argomenti transizione colore")
                    if len(call.args) == 5:
                        checks.equal(call.args[3].strip(), "0.180", "feedback visuale: transizione colore di 0.180 s")
                        checks.equal(call.args[4].strip(), "Destination and Duration", "feedback visuale: destinazione colore rivalutata")
    transition = rule_by_subroutine(rules, "TransitionMenuColor")
    if transition:
        transition_code = re.sub(r"\s+", "", mask_strings(transition.body))
        selector = "(Event Player.MenuPage == -1 ? Event Player.MainMenuCursor : Event Player.MenuPage)"
        checks.require(
            re.sub(r"\s+", "", f"{selector} == 1 ? Global.NameColorRGBValues[Event Player.ColorCursor] :")
            in transition_code,
            "feedback visuale: Name Color deve mostrare il colore esatto della preview",
        )
        checks.require(re.sub(r"\s+", "", f"{selector} == 0 ? Vector(160, 195, 235) :")
                       in transition_code, "Info: light blue menu accent")
        anchors = {
            2: (190, 210, 230), 3: (100, 110, 120),
            4: (255, 245, 215), 5: (255, 200, 70), 6: (236, 153, 0),
            7: (255, 120, 105), 8: (255, 75, 75), 9: (255, 50, 145),
            10: (205, 160, 255), 11: (100, 50, 255), 12: (70, 145, 255),
            13: (0, 234, 234), 14: (70, 220, 110), 15: (65, 155, 110),
        }
        for page, anchor in anchors.items():
            expected = (
                f"{selector} == {page} ? Global.NameColorRGBValues[Event Player.ColorIndex] * 0.680 + "
                f"Vector({', '.join(str(component) for component in anchor)}) * 0.320 :"
            )
            checks.require(re.sub(r"\s+", "", expected) in transition_code,
                           f"Menu color: blended accent for page {page}")
        selector_pattern = re.escape(re.sub(r"\s+", "", selector)) + r"==(\d+)\?"
        checks.equal([int(page) for page in re.findall(selector_pattern, transition_code)], list(range(16)),
                     "feedback visuale: sedici tinte menu in ordine senza duplicati")
        checks.equal(len(list(iter_calls(transition.body, "Chase Player Variable Over Time"))), 2,
                     "feedback visuale: due transizioni fluide senza override duplicato")
        checks.equal(mask_strings(transition.body).count("Event Player.MenuColor ="), 0,
                     "feedback visuale: nessuna assegnazione immediata nella transizione colore")
    quiet = rule_by_subroutine(rules, "QuiescePlayer")
    if quiet:
        stops = [call for call in iter_calls(quiet.body, "Stop Chasing Player Variable")
                 if len(call.args) == 2 and call.args[1].strip() == "MenuColor"]
        checks.equal(len(stops), 1, "feedback visuale: cleanup transizione colore individuale")
    music = rule_by_subroutine(rules, "DrawSoundtrackMenu")
    if music:
        back_controls = [call for call in iter_calls(music.body, "Custom String")
                         if len(call.args) == 2 and parse_literal(call.args[0]) == "{0}: back"
                         and re.sub(r"\s+", "", call.args[1]) == "InputBindingString(Button(Reload))"]
        checks.equal(len(back_controls), 1, "Locked Soundtrack: one English Reload back command")
        checks.require('Custom String("Hold {0}", Input Binding String(Button(Crouch)))' in music.body,
                       "Locked Soundtrack: command subtitle must show the Crouch modifier")


def validate_input_contract(checks: Checks, rules: list[Rule]) -> None:
    def code(expression: str) -> str:
        return re.sub(r"\s+", "", mask_strings(expression))

    menu_toggle = next((rule for rule in rules if "Button(Melee)" in rule.body and "Wait(0.500, Abort When False)" in rule.body and "MenuOpen" in rule.body), None)
    checks.require(menu_toggle is not None, "hold Melee 0,5 s per apertura/chiusura menu assente")
    if menu_toggle:
        checks.equal(event_type(menu_toggle), "Ongoing - Each Player", "hold Melee: evento")

    dispatcher = next((rule for rule in rules if event_type(rule) == "Ongoing - Each Player" and "MenuCommand" in rule.body and all(f"Button({button})" in rule.body for button in MENU_ACTION_BUTTONS)), None)
    checks.require(dispatcher is not None, "dispatcher input menu completo assente")
    if dispatcher:
        checks.require("Is Button Held(Event Player, Button(Crouch)) == True;" in dispatcher.body,
                       "azioni menu non protette dal modificatore Crouch")
        checks.require("Is Alive(Event Player) == True;" in dispatcher.body,
                       "menu morto non è congelato")
        checks.require("Event Player.CameraInteractConsumed == False;" in dispatcher.body,
                       "dispatcher menu non blocca Interact già consumato dalla Camera")
        interact_branch = re.search(
            r"If\(Is Button Held\(Event Player, Button\(Interact\)\)\);(.*?)Else If",
            dispatcher.body,
            re.DOTALL,
        )
        checks.require(interact_branch is not None, "ramo Interact del dispatcher menu assente")
        if interact_branch:
            checks.require("Event Player.MenuCommand = 1;" in interact_branch.group(1),
                           "ramo Interact del dispatcher non seleziona MenuCommand 1")
            checks.require("Event Player.CameraInteractConsumed = True;" in interact_branch.group(1),
                           "ramo Interact del dispatcher non acquisisce il latch Camera")

    lock_rule = next((rule for rule in rules if "Disallow Button(Event Player" in rule.body and "MenuInputLocked" in rule.body), None)
    unlock_rule = next((rule for rule in rules if "Allow Button(Event Player" in rule.body and "MenuInputLocked" in rule.body and "Crouch" in rule.body), None)
    checks.require(lock_rule is not None and unlock_rule is not None, "coppia lock/unlock input menu assente")
    if lock_rule and unlock_rule:
        disallowed = set(re.findall(r"Disallow Button\(Event Player, Button\(([^)]+)\)\);", lock_rule.body))
        allowed = set(re.findall(r"Allow Button\(Event Player, Button\(([^)]+)\)\);", unlock_rule.body))
        checks.require(MENU_ACTION_BUTTONS <= disallowed, "lock Crouch non cattura tutti gli input menu")
        checks.equal(disallowed, allowed, "simmetria Disallow/Allow input menu")
        checks.require(not (NATIVE_BUTTONS & disallowed), "Melee, Jump e Crouch non devono essere bloccati")

    camera = next((rule for rule in rules if "Button(Interact)" in rule.body and "Wait(0.500, Abort When False)" in rule.body and "CameraMode" in rule.body), None)
    checks.require(camera is not None, "hold Interact 0,5 s camera assente")
    if camera:
        checks.require("MenuOpen" not in mask_strings(camera.body),
                       "camera Interact non deve dipendere dallo stato aperto/chiuso del menu")
        checks.require("Is Button Held(Event Player, Button(Crouch)) == False;" in camera.body,
                       "camera Interact interferisce con il modificatore Crouch")
        checks.require("Event Player.CameraInteractConsumed == False;" in camera.body,
                       "camera Interact non verifica il latch condiviso col menu")
        checks.require("Event Player.CameraInteractConsumed = True;" in camera.body,
                       "camera Interact non acquisisce il latch dopo il hold")
        if dispatcher:
            checks.require(camera.start != dispatcher.start,
                           "camera hold e dispatcher Crouch+Interact non devono condividere la stessa regola")

    camera_release = next(
        (
            rule for rule in rules
            if event_type(rule) == "Ongoing - Each Player"
            and "Event Player.CameraInteractConsumed == True;" in rule.body
            and "Is Button Held(Event Player, Button(Interact)) == False;" in rule.body
            and "Event Player.CameraInteractConsumed = False;" in rule.body
        ),
        None,
    )
    checks.require(camera_release is not None,
                   "rilascio Interact non azzera il latch condiviso menu/Camera")

    crouch_features = [rule for rule in rules if event_type(rule) == "Ongoing - Each Player" and "Button(Crouch)" in rule.body and ("InspectionActive = True" in rule.body or "CrouchTravelActive = True" in rule.body)]
    checks.require(bool(crouch_features), "inspection/teleport Crouch assenti")
    for rule in crouch_features:
        checks.require("Event Player.MenuOpen == False;" in rule.body,
                       f"{rule.name}: Crouch inspection/teleport deve essere disattivato col menu")
        checks.require("Event Player.LuckPrivacyActive == False;" in rule.body,
                       f"{rule.name}: Crouch inspection/teleport deve essere disattivato durante Vision")

    for rule in rules_with_event(rules, "Player Died"):
        checks.require("Call Subroutine(CloseMenu);" not in rule.body,
                       f"{rule.name}: la morte non deve chiudere il menu")
        checks.require("Destroy HUD Text(Event Player.MenuHud);" not in rule.body,
                       f"{rule.name}: la morte non deve nascondere il menu")
        checks.require(
            "JumpReviveConsumed" not in mask_strings(rule_block(rule, "actions") or ""),
            f"{rule.name}: la morte non deve riarmare il latch Resurrect durante Jump premuto",
        )
    resurrect = next(
        (
            rule for rule in rules
            if event_type(rule) == "Ongoing - Each Player"
            and "Resurrect(Event Player);" in rule.body
            and "Button(Jump)" in rule.body
        ),
        None,
    )
    checks.require(resurrect is not None, "Resurrect da morto con Jump assente")
    checks.require(not any("Respawn(" in rule.body for rule in rules),
                   "Jump deve usare Resurrect senza azioni Respawn")
    if resurrect:
        checks.require("MenuOpen == False" not in resurrect.body,
                       "Jump Resurrect deve funzionare anche col menu visibile")
        conditions = rule_block(resurrect, "conditions") or ""
        required_conditions = (
            "Event Player.IsHuman == True;",
            "Event Player.IsAutomaticBot == False;",
            "Is Dummy Bot(Event Player) == False;",
            "Is Alive(Event Player) == False;",
            "Event Player.JumpReviveConsumed == False;",
            "Is Button Held(Event Player, Button(Jump)) == True;",
        )
        for token in required_conditions:
            checks.require(token in conditions, f"Jump Resurrect senza guardia: {token}")
        actual_conditions = tuple(
            line.strip()
            for line in mask_strings(conditions).splitlines()
            if line.strip()
        )
        checks.equal(
            actual_conditions,
            required_conditions,
            "Jump Resurrect deve dipendere solo da identità umana, morte, latch e Jump",
        )

        actions = rule_block(resurrect, "actions") or ""
        masked = mask_strings(actions)
        live_nearest_assignment = (
            "Event Player.SafeRevivePosition = Nearest Walkable Position(Position Of(Event Player));"
        )
        unsafe_assignment = (
            "Event Player.ReviveTeleportNeeded = Or(Distance Between(Ray Cast Hit Position("
            "Event Player.DeathPosition + Vector(0, 1, 0), "
            "Event Player.DeathPosition - Vector(0, 3, 0), "
            "Empty Array, Empty Array, False), Event Player.DeathPosition) > 2.500, "
            "Distance Between(Event Player.SafeRevivePosition, Event Player.DeathPosition) > 0.500);"
        )
        unsafe_guard = "If(Event Player.ReviveTeleportNeeded == True);"
        safe_teleport = "Teleport(Event Player, Event Player.SafeRevivePosition + Vector(0, 0.500, 0));"
        recovery = (
            "Event Player.JumpReviveConsumed = True;",
            live_nearest_assignment,
            unsafe_assignment,
            unsafe_guard,
            safe_teleport,
            "End;",
            "Resurrect(Event Player);",
            unsafe_guard,
            safe_teleport,
            "End;",
            "Event Player.ReviveTeleportNeeded = False;",
        )
        checks.require(
            code(masked).startswith(code("\n".join(recovery))),
            "Jump Resurrect: candidato e guardia sicurezza freschi prima di Teleport/Resurrect/Teleport, poi reset flag",
        )
        ordered = (
            "Event Player.JumpReviveConsumed = True;",
            live_nearest_assignment,
            unsafe_assignment,
            "Resurrect(Event Player);",
            "Event Player.ReviveTeleportNeeded = False;",
            "If(Is Alive(Event Player) == True);",
            "Event Player.GhostFlyPhysicsApplied = False;",
            "Call Subroutine(ApplyGhostFlyPhysics);",
        )
        positions = [masked.find(token) for token in ordered]
        checks.require(
            all(position >= 0 for position in positions) and positions == sorted(positions),
            "Jump Resurrect deve calcolare il punto dalla posizione live, tornare in vita e riapplicare Fly",
        )
        checks.equal(masked.count(unsafe_assignment), 1, "Jump Resurrect: guardia sicurezza include vuoto verticale e distanza dal punto camminabile")
        checks.equal(masked.count("Ray Cast Hit Position("), 1, "Jump Resurrect: unico raycast vuoto")
        checks.equal(
            masked.count(live_nearest_assignment),
            1,
            "Jump Resurrect: candidato fresco dalla posizione live, calcolato una sola volta",
        )
        checks.require("Nearest Walkable Position(Event Player.DeathPosition)" not in masked,
                       "Jump Resurrect non deve calcolare Nearest Walkable dalla snapshot DeathPosition")
        checks.require("Call Subroutine(FindSafeTravelPosition);" not in masked,
                       "Jump Resurrect non deve dipendere dal validatore Teleport che può annullare il recupero")
        checks.require("Abort;" not in masked and "Abort If(" not in masked,
                       "Jump Resurrect non deve avere percorsi Abort prima del ritorno in vita")
        checks.require("Spawn Points(Team Of(Event Player))" not in masked,
                       "Jump Resurrect non deve usare fallback Spawn Room")
        checks.require("Random Real(" not in masked,
                       "Jump Resurrect sicuro non deve usare offset casuali")
        teleport_calls = list(iter_calls(actions, "Teleport"))
        resurrect_calls = list(iter_calls(actions, "Resurrect"))
        nearest_calls = list(iter_calls(actions, "Nearest Walkable Position"))
        checks.equal(len(teleport_calls), 2, "Jump Resurrect: Teleport prima e dopo Resurrect riservati al recupero sicuro")
        checks.equal(len(resurrect_calls), 1, "Jump Resurrect: deve esistere un solo Resurrect")
        checks.equal(len(nearest_calls), 1, "Jump Resurrect: unico Nearest Walkable dalla posizione corrente")
        if len(teleport_calls) == 2 and len(resurrect_calls) == 1:
            checks.require(teleport_calls[0].start < resurrect_calls[0].start < teleport_calls[1].start,
                           "Jump Resurrect deve avere Teleport prima e dopo il ritorno in vita")
            checks.require(
                not conditional_branches_containing(actions, resurrect_calls[0].start),
                "Jump Resurrect deve essere incondizionato e fuori dal solo ramo vuoto",
            )
        for teleport in teleport_calls:
            teleport_branches = conditional_branches_containing(actions, teleport.start)
            checks.require(
                len(teleport_branches) == 1
                and code(teleport_branches[0]).startswith(code(unsafe_guard)),
                "Jump Resurrect: Teleport deve essere confinato alla guardia sicurezza",
            )
            checks.require(
                len(teleport.args) == 2
                and code(teleport.args[0]) == "EventPlayer"
                and code(teleport.args[1]) == "EventPlayer.SafeRevivePosition+Vector(0,0.500,0)",
                "Jump Resurrect: entrambi i Teleport devono usare lo stesso candidato fresco con margine verticale",
            )
        if nearest_calls:
            checks.require(
                not conditional_branches_containing(actions, nearest_calls[0].start),
                "Jump Resurrect: candidato fresco deve essere calcolato senza condizioni",
            )
        checks.require("Start Forcing Player Position(" not in masked,
                       "Jump Resurrect non deve usare forcing di posizione")
        checks.require(
            "Small Message(" not in masked,
            "Jump Resurrect non deve mostrare Small Message dopo il tentativo",
        )
        for forbidden_text, language in (
            ("Resurrect unavailable", "EN"),
            ("Bangkit belum siap", "ID"),
            ("การฟื้นยังไม่พร้อม", "TH"),
        ):
            checks.require(
                forbidden_text not in resurrect.body,
                f"Jump Resurrect conserva il vecchio messaggio unavailable {language}",
            )
        checks.require(not wait_calls(resurrect.body) and action_loop_count(resurrect.body) == 0,
                       "Jump Resurrect deve funzionare senza Wait/Loop")
        checks.require("Event Player.JumpReviveConsumed = False;" not in masked,
                       "Jump Resurrect non deve riarmarsi durante la stessa pressione")
        for lifecycle_name in ("PreparePlayer", "QuiescePlayer"):
            lifecycle = rule_by_subroutine(rules, lifecycle_name)
            resets = re.findall(
                r"\bEvent Player\.ReviveTeleportNeeded\s*=(?!=)\s*([^;]+);",
                mask_strings(rule_block(lifecycle, "actions") or "") if lifecycle else "",
            )
            checks.equal(resets, ["False"], f"Jump Resurrect: reset flag recupero in {lifecycle_name}")
        for rule in rules:
            writes = re.findall(r"\bReviveTeleportNeeded\s*=(?!=)", mask_strings(rule.body))
            if writes:
                checks.require(
                    rule.start == resurrect.start
                    or subroutine_target(rule) in {"PreparePlayer", "QuiescePlayer"},
                    f"{rule.name}: writer flag recupero Resurrect fuori dal tentativo o lifecycle",
                )
        death_rearm = next((rule for rule in rules if event_type(rule) == "Player Died" and "Event Player.DeathPosition = Position Of(Event Player);" in rule.body), None)
        checks.require(death_rearm is not None, "morte umana per Jump Resurrect assente")
        if death_rearm:
            death_actions = rule_block(death_rearm, "actions") or ""
            death_masked = mask_strings(death_actions)
            death_normalization = (
                "Stop Accelerating(Event Player);",
                "Set Move Speed(Event Player, 100);",
                "Stop Transforming Throttle(Event Player);",
                "Set Gravity(Event Player, 100);",
                "Enable Movement Collision With Environment(Event Player);",
                "Event Player.GhostFlyPhysicsApplied = False;",
                "Event Player.FlyRampStartTime = -1;",
            )
            death_positions = [death_masked.find(token) for token in death_normalization]
            checks.require(
                all(position >= 0 for position in death_positions)
                and death_positions == sorted(death_positions),
                "morte deve normalizzare accelerazione, throttle, gravità e collisione prima di riarmare Ghost/Fly",
            )
            for prompt, language in (
                ('Press {0}: revive here. Void death? Back to walkable ground.', "EN"),
            ):
                checks.require(
                    prompt in death_rearm.body,
                    f"prompt morte non descrive il recupero automatico dal vuoto: {language}",
                )

    resurrect_release = next(
        (
            rule for rule in rules
            if event_type(rule) == "Ongoing - Each Player"
            and "Event Player.JumpReviveConsumed = False;" in (rule_block(rule, "actions") or "")
            and "Is Button Held(Event Player, Button(Jump)) == False;" in (rule_block(rule, "conditions") or "")
        ),
        None,
    )
    checks.require(
        resurrect_release is not None,
        "rilascio Jump deve riarmare il latch Resurrect dopo un tentativo fallito",
    )
    if resurrect_release:
        release_conditions = rule_block(resurrect_release, "conditions") or ""
        for token in (
            "Event Player.IsHuman == True;",
            "Event Player.IsAutomaticBot == False;",
            "Is Dummy Bot(Event Player) == False;",
            "Event Player.JumpReviveConsumed == True;",
            "Is Button Held(Event Player, Button(Jump)) == False;",
        ):
            checks.require(token in release_conditions, f"rilascio latch Resurrect senza guardia: {token}")
        checks.require(
            "Is Alive(" not in mask_strings(release_conditions),
            "rilascio latch Resurrect deve funzionare da vivo e da morto",
        )
        release_actions = rule_block(resurrect_release, "actions") or ""
        checks.equal(
            re.sub(r"\s+", "", release_actions),
            "EventPlayer.JumpReviveConsumed=False;",
            "rilascio Jump deve soltanto riarmare il latch Resurrect",
        )


def validate_unkillable_full_hp(checks: Checks, rules: list[Rule]) -> None:
    """FULL HP owns damage, knockback and player-collision immunity as one state."""

    local_protection = (
        "Set Damage Received(Event Player, 0);",
        "Set Knockback Received(Event Player, 0);",
        "Disable Movement Collision With Players(Event Player);",
    )
    active_protection = (
        "Set Damage Received(Global.ActivePlayer, 0);",
        "Set Knockback Received(Global.ActivePlayer, 0);",
        "Disable Movement Collision With Players(Global.ActivePlayer);",
    )
    local_restore = (
        "Set Damage Received(Event Player, 100);",
        "Set Knockback Received(Event Player, 100);",
        "Enable Movement Collision With Players(Event Player);",
    )
    active_restore = (
        "Set Damage Received(Global.ActivePlayer, 100);",
        "Set Knockback Received(Global.ActivePlayer, 100);",
        "Enable Movement Collision With Players(Global.ActivePlayer);",
    )

    def require_enclosing_branch(
        rule: Rule | None,
        anchor: str,
        tokens: tuple[str, ...],
        label: str,
    ) -> None:
        checks.require(rule is not None, f"{label}: regola assente")
        if not rule:
            return
        masked = mask_strings(rule.body)
        position = masked.find(anchor)
        checks.require(position >= 0, f"{label}: ramo assente")
        if position < 0:
            return
        branches = conditional_branches_containing(rule.body, position)
        checks.require(bool(branches), f"{label}: azioni fuori da un ramo condizionale")
        branch = mask_strings(branches[0]) if branches else ""
        for token in tokens:
            checks.require(token in branch, f"{label}: protezione/ripristino assente: {token}")

    apply = rule_by_subroutine(rules, "ApplyUnkillablePage")
    processor = rule_by_subroutine(rules, "ProcessPlayerFastState")
    require_enclosing_branch(
        apply,
        "Set Damage Received(Event Player, 0);",
        local_protection,
        "FULL HP applicazione",
    )
    require_enclosing_branch(
        processor,
        "Set Damage Received(Global.ActivePlayer, 0);",
        active_protection,
        "FULL HP riapplicazione globale",
    )
    require_enclosing_branch(
        apply,
        "If(Event Player.UnkillableMode == 0);",
        local_restore,
        "FULL HP uscita OFF",
    )
    require_enclosing_branch(
        apply,
        "If(Event Player.UnkillableMode == 1);",
        local_restore,
        "FULL HP passaggio a 1 HP",
    )
    require_enclosing_branch(
        processor,
        "If(And(Global.ActivePlayer.UnkillableMode == 1,",
        active_restore,
        "FULL HP riapplicazione modalità 1 HP",
    )

    expected_zero_calls = {
        "Set Damage Received": {
            ("ApplyUnkillablePage", ("Event Player", "0")),
            ("ProcessPlayerFastState", ("Global.ActivePlayer", "0")),
        },
        "Set Knockback Received": {
            ("ApplyUnkillablePage", ("Event Player", "0")),
            ("ProcessPlayerFastState", ("Global.ActivePlayer", "0")),
        },
        "Disable Movement Collision With Players": {
            ("ApplyUnkillablePage", ("Event Player",)),
            ("ProcessPlayerFastState", ("Global.ActivePlayer",)),
        },
    }
    for action, expected in expected_zero_calls.items():
        actual_items = [
            (
                subroutine_target(rule) or rule.name,
                tuple(argument.strip() for argument in call.args),
            )
            for rule in rules
            for call in iter_calls(rule.body, action)
            if (action == "Disable Movement Collision With Players")
            or (len(call.args) >= 2 and call.args[1].strip() == "0")
        ]
        checks.equal(len(actual_items), 2, f"FULL HP: numero azioni {action}")
        checks.equal(set(actual_items), expected, f"FULL HP: ownership esclusiva di {action}")

    for subroutine, tokens in (
        ("PreparePlayer", local_restore),
        ("RestorePlayerLuck", local_restore),
        ("RestoreActivePlayerLuck", active_restore),
    ):
        rule = rule_by_subroutine(rules, subroutine)
        checks.require(rule is not None, f"FULL HP cleanup: subroutine {subroutine} assente")
        if rule:
            masked = mask_strings(rule.body)
            for token in tokens:
                checks.require(token in masked, f"FULL HP cleanup {subroutine} incompleto: {token}")

    luck_apply = rule_by_subroutine(rules, "ApplyLuckPage")
    checks.require(luck_apply is not None, "Try Your Luck: subroutine di avvio assente")
    if luck_apply:
        luck_apply_masked = mask_strings(luck_apply.body)
        for field in ("UnkillableActive", "UnkillableMode", "UnkillableCursor", "UnkillableIcon"):
            checks.require(
                re.search(rf"Event Player\.{field}\s*=(?!=)", luck_apply_masked) is None,
                f"Try Your Luck non deve modificare {field} all'avvio",
            )
        for token, label in (
            ("Clear Status(Event Player, Unkillable);", "status Unkillable"),
            ("Set Status(Event Player, Null, Unkillable", "status Unkillable"),
            ("Set Damage Received(Event Player", "Damage Received"),
            ("Set Knockback Received(Event Player", "Knockback Received"),
            ("Enable Movement Collision With Players(Event Player);", "collisione player"),
            ("Disable Movement Collision With Players(Event Player);", "collisione player"),
            ("Set Player Health(Event Player", "salute Unkillable"),
            ("Destroy Icon(Event Player.UnkillableIcon);", "icona Unkillable"),
        ):
            checks.require(
                token not in luck_apply_masked,
                f"Try Your Luck non deve sospendere {label} all'avvio",
            )

    for subroutine, target in (
        ("RestorePlayerLuck", "Event Player"),
        ("RestoreActivePlayerLuck", "Global.ActivePlayer"),
    ):
        cleanup = rule_by_subroutine(rules, subroutine)
        if not cleanup:
            continue
        cleanup_masked = mask_strings(cleanup.body)
        for field in ("UnkillableMode", "UnkillableCursor"):
            checks.require(
                re.search(rf"{re.escape(target)}\.{field}\s*=(?!=)", cleanup_masked) is None,
                f"{subroutine} non deve cancellare la preferenza {field}",
            )
        checks.require(
            f"{target}.UnkillableActive = {target}.UnkillableMode != 0;" in cleanup_masked,
            f"{subroutine} deve riattivare logicamente Kebal dalla preferenza UnkillableMode",
        )
        logical_restore = f"{target}.UnkillableActive = {target}.UnkillableMode != 0;"
        clear_status = f"Clear Status({target}, Unkillable);"
        checks.require(
            cleanup_masked.find(clear_status) < cleanup_masked.find(logical_restore),
            f"{subroutine} deve riattivare Kebal dopo la normalizzazione dello stato motore",
        )

    active_cleanup = rule_by_subroutine(rules, "RestoreActivePlayerLuck")
    if active_cleanup:
        active_cleanup_masked = mask_strings(active_cleanup.body)
        clear_position = active_cleanup_masked.find(
            "Clear Status(Global.ActivePlayer, Unkillable);"
        )
        cleanup_branches = conditional_branches_containing(active_cleanup.body, clear_position)
        cleanup_branch = mask_strings(cleanup_branches[0]) if cleanup_branches else ""
        for token in (
            "Global.ActivePlayer.UnkillableMode == 0",
            "Is Alive(Global.ActivePlayer) == False",
        ):
            checks.require(
                token in cleanup_branch,
                "cleanup Try vivo non deve sospendere Unkillable durante hero swap/timeout: " + token,
            )

    if processor:
        processor_masked = mask_strings(processor.body)
        icon_guard = (
            "If(Or(Global.ActivePlayer.UnkillableIcon == Null, "
            "Entity Exists(Global.ActivePlayer.UnkillableIcon) == False));"
        )
        icon_store = "Global.ActivePlayer.UnkillableIcon = Last Created Entity;"
        checks.require(icon_guard in processor_masked,
                       "riapplicazione globale Kebal non ricrea in sicurezza un'icona assente o non più esistente")
        checks.equal(processor_masked.count(icon_store), 1,
                     "riapplicazione globale Kebal: salvataggio handle icona")
        restore_icons = [
            call for call in iter_calls(processor.body, "Create Icon")
            if len(call.args) >= 6
            and call.args[2].strip() in {"Warning", "Halo"}
        ]
        checks.equal(len(restore_icons), 2,
                     "riapplicazione globale Kebal deve ricreare le icone 1 HP e FULL HP")
        expected_icons = {
            "Warning": "CustomColor(255,80,80,255)",
            "Halo": "Global.RGB",
        }
        for icon in restore_icons:
            icon_type = icon.args[2].strip()
            checks.equal(icon.args[1].strip(), "Evaluate Once(Global.ActivePlayer)",
                         f"icona Kebal {icon_type}: identità owner catturata")
            captures = list(iter_calls(icon.args[1], "Evaluate Once"))
            checks.equal(len(captures), 1,
                         f"icona Kebal {icon_type}: identità owner catturata")
            if captures:
                checks.equal(
                    tuple(argument.strip() for argument in captures[0].args),
                    ("Global.ActivePlayer",),
                    f"icona Kebal {icon_type}: cattura owner",
                )
            checks.equal(icon.args[0].strip(), "All Players(All Teams)",
                         f"icona Kebal {icon_type}: pubblico")
            checks.equal(icon.args[3].strip(), "Visible To and Position",
                         f"icona Kebal {icon_type}: reevaluation")
            checks.equal(icon.args[5].strip(), "True",
                         f"icona Kebal {icon_type}: visibilità off-screen")
            checks.equal(re.sub(r"\s+", "", icon.args[4]), expected_icons[icon_type],
                         f"icona Kebal {icon_type}: colore")
        guard_position = processor_masked.find(icon_guard)
        store_position = processor_masked.find(icon_store)
        checks.require(0 <= guard_position < store_position,
                       "riapplicazione globale Kebal salva l'icona fuori dalla guardia non-Null")
        if store_position >= 0:
            icon_branches = conditional_branches_containing(processor.body, store_position)
            icon_branch = next(
                (mask_strings(branch) for branch in icon_branches if icon_guard in mask_strings(branch)),
                "",
            )
            checks.require(bool(icon_branch),
                           "riapplicazione globale Kebal: ricreazione icona fuori dalla guardia")
            checks.require("If(Global.ActivePlayer.UnkillableMode == 1);" in icon_branch,
                           "riapplicazione globale Kebal non distingue icona 1 HP/FULL HP")

    spawn_exit = next(
        (
            rule for rule in rules
            if "Event Player.UnkillableMode == 1;" in (rule_block(rule, "conditions") or "")
            and "Is In Spawn Room(Event Player) == True;" in (rule_block(rule, "conditions") or "")
        ),
        None,
    )
    checks.require(spawn_exit is not None, "ripristino modalità 1 HP in Spawn Room assente")
    if spawn_exit:
        masked = mask_strings(spawn_exit.body)
        for token in local_restore:
            checks.require(token in masked, f"ripristino modalità 1 HP in Spawn Room incompleto: {token}")


def global_player_context_errors(rules: list[Rule]) -> list[str]:
    """Follow the call graph: subroutines inherit, never create, Event Player."""
    subroutine_rules = {subroutine_target(rule): rule for rule in rules
                        if subroutine_target(rule) is not None}
    errors: list[str] = []
    for origin in rules_with_event(rules, "Ongoing - Global"):
        pending = [(origin, (origin.name,))]
        visited: set[int] = set()
        while pending:
            rule, path = pending.pop()
            if rule.start in visited:
                continue
            visited.add(rule.start)
            masked = mask_strings(rule.body)
            if re.search(r"\bEvent\s+Player\b", masked):
                errors.append(
                    "contesto Event Player non disponibile da Ongoing - Global: "
                    + " -> ".join(path)
                )
            # Start Rule copies the same context, even though execution is asynchronous.
            for action in ("Call Subroutine", "Start Rule"):
                for call in iter_calls(masked, action):
                    if call.args and call.args[0].strip() in subroutine_rules:
                        name = call.args[0].strip()
                        pending.append((subroutine_rules[name], path + (name,)))
    return errors


def team_switch_worker(rules: list[Rule]) -> Rule | None:
    return next((rule for rule in rules
                 if event_type(rule) == "Ongoing - Each Player"
                 and "Event Player.LastTeam != Team Of(Event Player)"
                 in (rule_block(rule, "conditions") or "")), None)


def validate_inspector_recording(checks: Checks, source: str, rules: list[Rule]) -> None:
    """Telemetry must not enable the more expensive Inspector recording path."""
    masked = mask_strings(source)
    token = "Disable Inspector Recording;"
    checks.equal(masked.count(token), 1, "registrazione Inspector disabilitata una volta")
    checks.require("Enable Inspector Recording;" not in masked,
                   "la diagnostica non deve abilitare la registrazione Inspector")
    bootstrap = next((rule for rule in rules if rule.name.startswith("00 - ")), None)
    checks.require(bootstrap is not None, "inizializzazione Inspector assente")
    if bootstrap is not None:
        body = mask_strings(bootstrap.body)
        position = body.find(token)
        ready = body.find("Global.IsReady = True;")
        checks.require(0 <= position < ready,
                       "disabilitare Inspector prima di avviare il runtime")
        checks.require(not conditional_branches_containing(body, position),
                       "registrazione Inspector indipendente dal toggle diagnostica")


def validate_hero_selection_timeout(checks: Checks, rules: list[Rule]) -> None:
    """Keep the first hero timeout reachable before spawn, bounded and one-shot."""
    player = "Global.ActivePlayer"
    clock, latch = f"{player}.AutoHeroSelectionDeadline", f"{player}.AutoHeroSelectionComplete"

    def packed(value: str) -> str:
        return re.sub(r"\s+", "", mask_strings(value))

    fast = rule_by_subroutine(rules, "ProcessPlayerFastState")
    setup = rule_by_subroutine(rules, "PreparePlayer")
    scheduler = next((rule for rule in rules if rule.name.startswith("04g -")), None)
    checks.require(all(rule is not None for rule in (fast, setup, scheduler)),
                   "scelta eroe: fast worker, setup o scheduler assente")
    if not all(rule is not None for rule in (fast, setup, scheduler)):
        return

    arm = f"{clock} = Total Time Elapsed + 60;"
    fast_actions = mask_strings(rule_block(fast, "actions") or "")
    arm_position = fast_actions.find(arm)
    checks.equal(fast_actions.count(arm), 1, "scelta eroe: unica scadenza ingresso di 60 s")
    arm_headers = [packed(branch.splitlines()[0]) for branch in
                   conditional_branches_containing(fast_actions, arm_position)]
    checks.require(packed(f"If(And({latch} == False, {clock} == 0));") in arm_headers,
                   "scelta eroe: scadenza armata una sola volta prima del completamento")
    checks.require(arm_position >= 0 and all(token not in fast_actions[:arm_position]
                                           for token in ("IsHuman", "Has Spawned", "Entity Exists")),
                   "scelta eroe: ingresso deve precedere classificazione e guardie spawn")
    checks.require(not wait_calls(fast.body), "scelta eroe: arming senza Wait")

    starts = [(rule, call) for rule in rules for call in iter_calls(rule.body, "Start Forcing Player To Be Hero")]
    stops = [(rule, call) for rule in rules for call in iter_calls(rule.body, "Stop Forcing Player To Be Hero")]
    checks.equal(len(starts), 1, "scelta eroe: unico Start Forcing")
    checks.equal(len(stops), 1, "scelta eroe: unico Stop Forcing")
    if len(starts) == len(stops) == 1:
        start_rule, start = starts[0]
        stop_rule, stop = stops[0]
        checks.require(start_rule == stop_rule == scheduler,
                       "scelta eroe: forcing posseduto solo dallo scheduler")
        checks.equal(tuple(packed(arg) for arg in start.args),
                     (packed(player), "Hero(Shion)"), "scelta eroe: default Shion per il giocatore corrente")
        checks.equal(tuple(packed(arg) for arg in stop.args), (packed(player),),
                     "scelta eroe: rilascio dello stesso giocatore")
        checks.require(packed(start.raw + ";" + stop.raw + ";") in packed(scheduler.body),
                       "scelta eroe: Start/Stop adiacenti senza attesa o lock")
        branches = conditional_branches_containing(start_rule.body, start.start)
        headers = [packed(branch.splitlines()[0]) for branch in branches]
        cadence = f"If(Global.SchedulerStep % 20 == ({player}.IsHuman == True ? {player}.HudSlot : Slot Of({player})) % 20);"
        for header, label in (
            (f"If(And(Is Dummy Bot({player}) == False, {player}.IsAutomaticBot == False));", "esclusione bot"),
            (cadence, "cadenza 1 Hz"),
            (f"If({latch} == False);", "completamento one-shot"),
            (f"If(Or(Team Of({player}) == Team 1, Team Of({player}) == Team 2));", "esclusione spettatori"),
            (f"If(And({clock} > 0, Total Time Elapsed >= {clock}));", "scadenza individuale"),
        ):
            checks.require(packed(header) in headers, f"scelta eroe: {label}")
        checks.require(all(("IsHuman" not in header or header == packed(cadence))
                           and "HasSpawned" not in header and "EntityExists" not in header
                           for header in headers),
                       "scelta eroe: forcing raggiungibile per ingressi non spawned/non classificati")
        deadline_branch = branches[0] if branches else ""
        checks.require(packed(f"{latch} = True;") in packed(deadline_branch.split(start.raw)[0]),
                       "scelta eroe: consumare il latch prima del forcing")
        cancel = f"If(Has Spawned({player}) == True);{latch} = True;{clock} = 0;Else;"
        latch_branch = next((branch for branch in branches
                            if packed(branch.splitlines()[0]) == packed(f"If({latch} == False);")), "")
        checks.require(packed(latch_branch).startswith(packed(f"If({latch} == False);" + cancel)),
                       "scelta eroe: annullare prima se il giocatore ha scelto e spawned")
        checks.require(not any(wait_calls(branch) for branch in branches),
                       "scelta eroe: timeout senza nuovi Wait")
    checks.equal(len(wait_calls(scheduler.body)), 1, "scelta eroe: nessuna attesa scheduler aggiunta")

    for field, value in (("AutoHeroSelectionDeadline", "0"), ("AutoHeroSelectionComplete", "True")):
        checks.require(packed(f"Event Player.{field} = {value};") in packed(setup.body),
                       f"scelta eroe: setup completa {field}")
    for rule in rules:
        owner = subroutine_target(rule) or rule.name
        for match in re.finditer(r"\.(AutoHeroSelectionDeadline|AutoHeroSelectionComplete)\s*=(?!=)\s*([^;]+);",
                                 mask_strings(rule.body)):
            field, value = match.group(1), packed(match.group(2))
            allowed = (owner == "ProcessPlayerFastState" and field == "AutoHeroSelectionDeadline" and value == "TotalTimeElapsed+60"
                       or rule == scheduler and value == ("True" if field == "AutoHeroSelectionComplete" else "0")
                       or owner == "PreparePlayer" and value == ("True" if field == "AutoHeroSelectionComplete" else "0"))
            checks.require(allowed, f"scelta eroe: writer non autorizzato {field} in {owner}")
        for action in ("Set Player Variable", "Modify Player Variable"):
            for call in iter_calls(rule.body, action):
                checks.require(len(call.args) < 2 or call.args[1].strip() not in
                               ("AutoHeroSelectionDeadline", "AutoHeroSelectionComplete"),
                               "scelta eroe: stato scritto fuori dai writer diretti verificati")


def validate_scheduler(checks: Checks, source: str, rules: list[Rule], globals_: set[str], subroutines: set[str]) -> None:
    for error in global_player_context_errors(rules):
        checks.require(False, error)
    masked = mask_strings(source)
    checks.equal(action_loop_count(source), 1, "numero Loop Workshop")
    scheduler_candidates = [rule for rule in rules if action_loop_count(rule.body) == 1]
    checks.equal(len(scheduler_candidates), 1, "scheduler periodico unico")
    scheduler = scheduler_candidates[0] if len(scheduler_candidates) == 1 else None
    checks.require("SchedulerStep" in globals_, "contatore scheduler SchedulerStep assente")
    checks.require("PlayerListSnapshot" in globals_, "snapshot roster scheduler assente")
    if scheduler:
        checks.equal(event_type(scheduler), "Ongoing - Global", "scheduler 20 Hz: evento")
        checks.require("Wait(0.050, Ignore Condition);" in scheduler.body,
                       "scheduler non gira a 20 Hz")
        checks.require("Global.SchedulerStep" in scheduler.body,
                       "scheduler non incrementa SchedulerStep")
        for token in (
            "Global.PlayerListSnapshot = All Players(All Teams);",
            "For Global Variable(SchedulerPlayerIndex, 0, Count Of(Global.PlayerListSnapshot), 1);",
            "Global.ActivePlayer = Global.PlayerListSnapshot[Global.SchedulerPlayerIndex];",
            "Global.PlayerListSnapshot = Empty Array;",
        ):
            checks.require(token in scheduler.body, f"scheduler snapshot roster incompleto: {token}")
        checks.require("All Players(All Teams)[Global.SchedulerPlayerIndex]" not in scheduler.body,
                       "scheduler non deve iterare direttamente la lista nativa mentre cambia team")
        vision_cache = (
            "Global.LuckVisionViewers = Filtered Array(Global.PlayerListSnapshot, "
            "And(Entity Exists(Current Array Element), And(Player Variable(Current Array Element, IsHuman) == True, "
            "Player Variable(Current Array Element, LuckPrivacyActive) == True)));"
        )
        checks.require(vision_cache in scheduler.body,
                       "Vision: cache pubblico deve filtrare lo snapshot una volta per tick")
        if vision_cache in scheduler.body:
            checks.require(scheduler.body.index(vision_cache) < scheduler.body.index("For Global Variable(SchedulerPlayerIndex"),
                           "Vision: cache pubblico deve essere costruita prima del ciclo giocatori")
        for name in sorted(SCHEDULER_SUBROUTINES):
            checks.require(f"Call Subroutine({name});" in scheduler.body,
                           f"scheduler non chiama {name}")
        scheduler_packed = re.sub(r"\s+", "", mask_strings(scheduler.body))
        for gate, label in (
            ("If(And(Is Dummy Bot(Global.ActivePlayer) == False, Global.ActivePlayer.IsAutomaticBot == False));Call Subroutine(ProcessPlayerFastState);", "classificazione e isolamento bot"),
            ("If(Or(Global.ActivePlayer.LuckActive == True, Or(Global.ActivePlayer.LuckSpinCount > 0, Or(Global.ActivePlayer.LuckEffect != 0, Global.ActivePlayer.LuckIconEndTime > 0))));Call Subroutine(ProcessPlayerLuck);End;", "Luck attivo o pulizia icona pendente"),
            ("If(And(Global.ActivePlayer.IsHuman == True, Global.ActivePlayer.FlyModeActive == True));Call Subroutine(ProcessPlayerFlight);End;", "Fly solo umano attivo"),
            ("If(And(Global.ActivePlayer.IsHuman == True, Or(Global.ActivePlayer.AllowDummyBotFollow == True, And(Global.ActivePlayer.MenuOpen == True, Or(Global.ActivePlayer.MenuPage == 2, Global.ActivePlayer.MenuPage == 4)))));Call Subroutine(ProcessPlayerMaintenance);End;", "cache solo menu Camera/Revenge o consenso Dummy Follow ON"),
            ("Else;If(Global.SchedulerStep % 2 == Slot Of(Global.ActivePlayer) % 2);Call Subroutine(ProcessPlayerBot);End;End;", "manutenzione bot isolata 10 Hz"),
            ("If(Global.SchedulerStep % 20 == 0);Call Subroutine(MaintainDummyBots);Call Subroutine(UpdateSocialObjectiveIcons);Global.TextCleanupPlayer = Null;Call Subroutine(CleanupOrphanedText);End;", "slot dummy, pulizia e pilar 1 Hz"),
        ):
            checks.require(re.sub(r"\s+", "", gate) in scheduler_packed,
                           f"scheduler a stati: {label}")
        calls_in_order = [scheduler.body.find(f"Call Subroutine({name});") for name in
                          ("ProcessPlayerFastState", "ProcessPlayerLuck", "ProcessPlayerFlight")]
        checks.require(calls_in_order == sorted(calls_in_order),
                       "Fly: scheduler deve chiamare il motore dopo Try Your Luck")
        vision_guard = "If(Is True For Any(Global.PlayerListSnapshot, Player Variable(Current Array Element, LuckPrivacyActive) == True));"
        checks.require(re.sub(r"\s+", "", vision_guard + vision_cache) in scheduler_packed,
                       "Vision: filtro pubblico solo con Vision attiva")
        checks.require("Else;If(CountOf(Global.LuckVisionViewers)>0);Global.LuckVisionViewers=EmptyArray;End;End;" in scheduler_packed,
                       "Vision: svuotare il pubblico residuo una sola volta")
        bot_cycle = rule_by_subroutine(rules, "ProcessPlayerBot")
        checks.require(bot_cycle is not None, "manutenzione bot dedicata assente")
        if bot_cycle:
            target_call = next(iter(iter_calls(bot_cycle.body, "Filtered Array")), None)
            phase = "If(Global.SchedulerStep % 4 == Slot Of(Global.ActivePlayer) % 4);"
            checks.require(target_call is not None and any(phase in branch.splitlines()[0]
                for branch in conditional_branches_containing(bot_cycle.body, target_call.start)),
                "target dummy: fase 5 Hz assente")
            checks.require("Global.ActivePlayer.BotLocked = False;" in bot_cycle.body
                           and "Has Spawned(Global.ActivePlayer) == False" in bot_cycle.body
                           and "Is Alive(Global.ActivePlayer) == False" in bot_cycle.body,
                           "manutenzione bot: riarmo morte/rinascita assente")
        motor_calls = [(rule, call) for rule in rules for call in iter_calls(rule.body, "Call Subroutine")
                       if call.args == ("ProcessPlayerFlight",)]
        checks.require(len(motor_calls) == 1 and motor_calls[0][0].start == scheduler.start,
                       "Fly: unico owner chiamante motore deve essere lo scheduler globale")
        for cadence in (2, 20):
            checks.require(re.search(rf"SchedulerStep\s*%\s*{cadence}\b", scheduler.body) is not None,
                           f"cadenza scheduler %{cadence} assente")
        for routine, period in (("ProcessPlayerCycle", 2), ("ProcessPlayerMaintenance", 20)):
            phase = f"If(Global.SchedulerStep % {period} == (Global.ActivePlayer.IsHuman == True ? Global.ActivePlayer.HudSlot : Slot Of(Global.ActivePlayer)) % {period});"
            calls = [call for call in iter_calls(scheduler.body, "Call Subroutine")
                     if call.args == (routine,)]
            checks.equal(len(calls), 1, f"carico distribuito: chiamata unica {routine}")
            for call in calls:
                checks.require(any(phase in branch.splitlines()[0]
                                   for branch in conditional_branches_containing(scheduler.body, call.start)),
                               f"carico distribuito: fase individuale assente per {routine}")
        recount_calls = [(rule, call) for rule in rules for call in iter_calls(rule.body, "Call Subroutine")
                         if call.args == ("RecountVotes",)]
        checks.require(len(recount_calls) == 1 and recount_calls[0][0] == scheduler,
                       "conteggio voti: deve essere accorpato nel solo scheduler")
        checks.require(
            "If(Global.VoteRecountNeeded==True);Global.VoteRecountNeeded=False;CallSubroutine(RecountVotes);End;"
            in scheduler_packed,
            "conteggio voti: richiesta pendente deve essere consumata una sola volta",
        )
        for prefix in ("02 -", "99l -", "93c -"):
            owner = next((rule for rule in rules if rule.name.startswith(prefix)), None)
            if prefix == "93c -":
                owner = rule_by_subroutine(rules, "CleanupPlayer")
            checks.require(owner is not None and "Global.VoteRecountNeeded = True;" in mask_strings(owner.body),
                           f"conteggio voti: richiesta assente in {prefix}")

    waits = wait_calls(source)
    checks.require(len(waits) <= 7, f"Wait oltre il massimo consentito: {len(waits)} > 7")
    wait_signatures: Counter[tuple[str | None, tuple[str, ...]]] = Counter()
    for rule in rules:
        calls = wait_calls(rule.body)
        if not calls:
            continue
        role = wait_role(rule, scheduler)
        checks.require(role is not None, f"Wait non allowlisted in regola: {rule.name}")
        for call in calls:
            signature = tuple(re.sub(r"\s+", " ", argument).strip() for argument in call.args)
            wait_signatures[(role, signature)] += 1
    expected_wait_signatures: Counter[tuple[str | None, tuple[str, ...]]] = Counter({
        ("scheduler", ("0.050", "Ignore Condition")): 1,
        ("leave ordering", ("0.500", "Ignore Condition")): 1,
        ("bot classification", ("0.016", "Ignore Condition")): 1,
        ("menu hold", ("0.500", "Abort When False")): 1,
        ("camera hold", ("0.500", "Abort When False")): 1,
        ("lifecycle stages", ("0.050", "Abort When False")): 2,
    })
    checks.equal(
        wait_signatures,
        expected_wait_signatures,
        "Wait nominativamente consentiti per ruolo, durata e quantità",
    )
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
            writes_active = re.findall(r"Global\.ActivePlayer\s*=(?!=)\s*([^;]+);", mask_strings(rule.body))
            checks.require(not writes_active or (writes_active == ["Null"] and "Global.IsReady = True;" in rule.body),
                           f"{rule.name}: scrittura ActivePlayer fuori dallo scheduler")
            checks.require("For Global Variable(SchedulerPlayerIndex" not in rule.body,
                           f"{rule.name}: SchedulerPlayerIndex posseduto solo dallo scheduler")
    checks.require("For Global Variable(Global." not in masked,
                   "sintassi For Global Variable(Global.*) non valida")


def validate_try_your_luck(checks: Checks, source: str, rules: list[Rule], players: set[str]) -> None:
    for name in sorted(LUCK_TIMESTAMP_VARIABLES):
        checks.require(name in players, f"timestamp Try Your Luck assente: {name}")
    checks.require(re.search(r"LuckEffect\s*=\s*Random Integer\(1,\s*6\)", source) is not None or
                   "Set Player Variable(Event Player, LuckEffect, Random Integer(1, 6));" in source,
                   "Try Your Luck non estrae esattamente sei esiti")
    for outcome in range(1, 6):
        checks.require(re.search(rf"LuckEffect\s*==\s*{outcome}\b", source) is not None,
                       f"Try Your Luck esito {outcome} assente")
    checks.require("Else;" in (rule_by_subroutine(rules, "ProcessPlayerLuck") or Rule("", "", 0, 0)).body,
                   "Try Your Luck esito 6/fallback assente")
    for token, label in (
        ("Start Accelerating(", "accelerazione 10 s"),
        ("Burning", "Burning 10 s"),
        ("Hacked", "Hacked 5 s"),
        ("LuckPrivacyActive", "Vision 15 s"),
    ):
        checks.require(token in source, f"Try Your Luck esito mancante: {label}")
    checks.require(
        not any(
            "Start Forcing Player Position(" in rule.body
            and any(token in rule.body for token in ("LuckActive", "LuckSpinCount", "LuckEffect"))
            for rule in rules
        ),
        "Try Your Luck non deve forzare la posizione",
    )
    checks.require("Custom String(\"□\")" not in source,
                   "Try Your Luck non deve creare una carta testuale")
    for rule in rules:
        if any(token in rule.body for token in ("LuckActive", "LuckSpinCount", "LuckEffect")) and not rule.name.startswith("04g -"):
            checks.require(action_loop_count(rule.body) == 0,
                           f"{rule.name}: Try Your Luck deve essere a stati, senza Loop")
            if subroutine_target(rule) == "ProcessPlayerLuck":
                checks.require(not wait_calls(rule.body), "ProcessPlayerLuck deve usare timestamp, non Wait")
    state_machine = rule_by_subroutine(rules, "ProcessPlayerLuck")
    checks.require(state_machine is not None, "macchina a stati ProcessPlayerLuck assente")
    if state_machine:
        masked_state_machine = mask_strings(state_machine.body)
        for token, label in (
            ("Set Status(Global.ActivePlayer, Null, Unkillable", "Set Status Unkillable"),
            ("Set Knockback Received(Global.ActivePlayer", "Knockback Received"),
            ("Enable Movement Collision With Players(Global.ActivePlayer);", "collisione player"),
            ("Disable Movement Collision With Players(Global.ActivePlayer);", "collisione player"),
        ):
            checks.require(
                token not in masked_state_machine,
                f"Try Your Luck: {label} non appartiene al bypass Burning",
            )
        checks.require(masked_state_machine.count("Clear Status(Global.ActivePlayer, Unkillable);") >= 2,
                       "Burning deve sospendere Unkillable all'applicazione e prima di ogni tick")
        checks.require(masked_state_machine.count("Set Damage Received(Global.ActivePlayer, 100);") >= 2,
                       "Burning deve ripristinare Damage Received prima dei tick")
        checks.require(
            "Damage(Global.ActivePlayer, Global.ActivePlayer, Max Health(Global.ActivePlayer) * 0.050);"
            in masked_state_machine,
            "Burning deve infliggere il 5% della Max Health per tick",
        )
        checks.require(
            "Global.ActivePlayer.NextLuckBurnTime = Total Time Elapsed + 1.000;"
            in masked_state_machine,
            "Burning deve usare tick da un secondo",
        )

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
                checks.equal(icon.args[0].strip(), "Global.HumanPlayers",
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
                            ("Global.ActivePlayer",),
                            f"icona roulette {index}: Evaluate Once deve catturare Global.ActivePlayer",
                        )
                    compact_position = re.sub(r"\s+", "", dynamic_position.args[0]) if dynamic_position.args else ""
                    expected_position = (
                        "EyePosition(EvaluateOnce(Global.ActivePlayer))+"
                        "FacingDirectionOf(EvaluateOnce(Global.ActivePlayer))*4"
                    )
                    checks.equal(compact_position, expected_position,
                                 f"icona roulette {index}: ancoraggio fluido a occhio e mirino del beneficiario")
                    uncaptured = re.sub(
                        r"Evaluate\s+Once\(\s*Global\.ActivePlayer\s*\)",
                        "",
                        dynamic_position.args[0] if dynamic_position.args else "",
                    )
                    checks.require("Global.ActivePlayer" not in uncaptured,
                                   f"icona roulette {index}: scratch Global.ActivePlayer dinamico senza Evaluate Once")
                checks.equal(icon.args[3].strip(), "Visible To and Position",
                             f"icona roulette {index}: reevaluation deve essere Visible To and Position")
                checks.equal(icon.args[5].strip(), "True",
                             f"icona roulette {index}: Show When Offscreen deve essere True")
        checks.equal(tuple(actual_icon_types), expected_icon_types,
                     "ordine tipi icona per esiti roulette 1..6")
        checks.equal(len(actual_icon_types), len(set(actual_icon_types)),
                     "icone roulette univoche per i sei esiti")

        rolling_block = if_block_containing("Global.ActivePlayer.LuckSpinCount > 0")
        checks.require(rolling_block is not None, "blocco sostituzione icona roulette non analizzabile")
        if rolling_block:
            rolling_masked = mask_strings(rolling_block)
            rolling_header = re.sub(r"\s+", "", rolling_masked.split(";", 1)[0])
            checks.equal(
                rolling_header,
                "If(And(Global.SchedulerStep%4==Global.ActivePlayer.HudSlot%4,"
                "And(Global.ActivePlayer.LuckSpinCount>0,"
                "TotalTimeElapsed>=Global.ActivePlayer.NextLuckSpinTime)))",
                "rotazione icona roulette distribuita in quattro fasi slot stabili",
            )
            checks.equal(
                len(re.findall(r"\bGlobal\.SchedulerStep\b", masked_state_machine)), 1,
                "fase slot roulette limitata alla rotazione icona, senza ritardare esiti o cleanup",
            )
            rolling_icons = list(iter_calls(rolling_block, "Create Icon"))
            rolling_destroys = list(iter_calls(rolling_block, "Destroy Icon"))
            checks.equal(len(rolling_icons), 6, "icone create nel blocco di sostituzione roulette")
            checks.equal(len(rolling_destroys), 1, "destroy-before-replace icona roulette")
            if rolling_icons and len(rolling_destroys) == 1:
                checks.equal(
                    tuple(argument.strip() for argument in rolling_destroys[0].args),
                    ("Global.ActivePlayer.LuckIcon",),
                    "destroy-before-replace usa l'handle roulette corrente",
                )
                checks.require(rolling_destroys[0].end < rolling_icons[0].start,
                               "handle roulette distrutto dopo la creazione sostitutiva")
                guard_position = rolling_masked.find("If(Global.ActivePlayer.LuckIcon != Null);")
                checks.require(0 <= guard_position < rolling_destroys[0].start,
                               "destroy-before-replace icona roulette non protetto da handle non-Null")
            store_token = "Global.ActivePlayer.LuckIcon = Last Created Entity;"
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
            and ("LuckIcon" in rule.body or "LuckEffect" in rule.body)
            and ("Create Icon(" in rule.body or "Start Accelerating(" in rule.body)
        ]
        checks.require(not player_bound_roulette_rules,
                       "icone/accelerazione roulette devono restare global-first, senza regole Each Player")

        global_acceleration_calls = list(iter_calls(source, "Start Accelerating"))
        checks.equal(len(global_acceleration_calls), 1, "Start Accelerating globale riservato a Try Your Luck")
        fly_cycle = next((rule for rule in rules if subroutine_target(rule) == "ProcessPlayerCycle"), None)
        fly_acceleration_calls = list(iter_calls(fly_cycle.body, "Start Accelerating")) if fly_cycle else []
        checks.equal(len(fly_acceleration_calls), 0, "Fly normale non deve usare Start Accelerating")
        acceleration_calls = list(iter_calls(state_machine.body, "Start Accelerating"))
        checks.equal(len(acceleration_calls), 1, "accelerazione Try Your Luck unica")
        if len(acceleration_calls) == 1:
            acceleration = acceleration_calls[0]
            checks.equal(len(acceleration.args), 6, "accelerazione Try Your Luck: numero argomenti")
            if len(acceleration.args) == 6:
                expected_acceleration = (
                    "Global.ActivePlayer",
                    "FacingDirectionOf(EvaluateOnce(Global.ActivePlayer))",
                    "50",
                    "25",
                    "ToWorld",
                    "DirectionRateandMaxSpeed",
                )
                compact_acceleration = tuple(re.sub(r"\s+", "", argument) for argument in acceleration.args)
                checks.equal(compact_acceleration, expected_acceleration,
                             "accelerazione automatica 3D nella Facing Direction del beneficiario")
                uncaptured_direction = re.sub(
                    r"Evaluate\s+Once\(\s*Global\.ActivePlayer\s*\)",
                    "",
                    acceleration.args[1],
                )
                checks.require("Global.ActivePlayer" not in uncaptured_direction,
                               "direzione accelerazione usa scratch Global.ActivePlayer senza Evaluate Once")

            branch_start = state_machine.body.rfind(
                "Else If(Global.ActivePlayer.LuckEffect == 2);", 0, acceleration.start
            )
            branch_end = state_machine.body.find(
                "Else If(Global.ActivePlayer.LuckEffect == 3);", acceleration.end
            )
            checks.require(branch_start >= 0 and branch_end > branch_start,
                           "ramo esito 2 dell'accelerazione non analizzabile")
            if branch_start >= 0 and branch_end > branch_start:
                acceleration_branch = state_machine.body[branch_start:branch_end]
                acceleration_branch_masked = mask_strings(acceleration_branch)
                acceleration_branch_compact = re.sub(r"\s+", "", acceleration_branch_masked)
                checks.require("Set Move Speed(Global.ActivePlayer, 1000);" in acceleration_branch_masked,
                               "accelerazione esito 2 non imposta Move Speed 1000")
                checks.require(
                    "StartAccelerating(" in acceleration_branch_compact,
                    "accelerazione esito 2 deve restare automatica",
                )
                checks.require(
                    "If(Global.ActivePlayer.FlyModeActive==False);" not in acceleration_branch_compact,
                    "accelerazione esito 2 deve restare automatica anche in Fly",
                )
                checks.require(
                    "Global.ActivePlayer.LuckEffectEndTime = Total Time Elapsed + 10;" in acceleration_branch_masked,
                    "accelerazione esito 2 non usa timestamp esatto di 10 secondi",
                )
                for forbidden_input in ("Throttle Of(", "Is Button Held(", "Button(", "Apply Impulse("):
                    checks.require(forbidden_input not in acceleration_branch_masked,
                                   f"accelerazione esito 2 dipende da input/impulsi: {forbidden_input}")

        checks.require("Apply Impulse(" not in mask_strings(state_machine.body),
                       "Try Your Luck non deve simulare l'accelerazione con Apply Impulse")
        checks.require("AkselerasiNasibAktif" not in mask_strings(source),
                       "accelerazione global-first non richiede latch/player variable dedicata")

        expiry_cleanup = if_block_containing("Total Time Elapsed >= Global.ActivePlayer.LuckEffectEndTime")
        checks.require(expiry_cleanup is not None, "cleanup timestamp Try Your Luck non analizzabile")
        if expiry_cleanup:
            expiry_cleanup_masked = mask_strings(expiry_cleanup)
            for token, label in (
                ("Stop Accelerating(Global.ActivePlayer);", "Stop Accelerating"),
                ("Set Move Speed(Global.ActivePlayer, 100);", "ripristino Move Speed 100"),
                ("Global.ActivePlayer.LuckEffect = 0;", "reset effetto"),
                ("Global.ActivePlayer.LuckEffectEndTime = 0;", "reset timestamp"),
            ):
                checks.require(token in expiry_cleanup_masked,
                               f"cleanup scadenza accelerazione incompleto: {label}")
            expiry_stop_calls = list(iter_calls(expiry_cleanup, "Stop Accelerating"))
            expiry_speed_calls = [
                call for call in iter_calls(expiry_cleanup, "Set Move Speed")
                if len(call.args) == 2 and call.args[1].strip() == "100"
            ]
            checks.equal(len(expiry_stop_calls), 1,
                         "cleanup scadenza: unico Stop Accelerating per l'esito 2")
            checks.equal(len(expiry_speed_calls), 1,
                         "cleanup scadenza: unico Move Speed 100 per l'esito 2")
            for call, label in (
                *((call, "Stop Accelerating") for call in expiry_stop_calls),
                *((call, "Move Speed 100") for call in expiry_speed_calls),
            ):
                branches = conditional_branches_containing(expiry_cleanup, call.start)
                checks.require(
                    any(
                        "Global.ActivePlayer.LuckEffect == 2" in mask_strings(branch)
                        for branch in branches
                    ),
                    f"cleanup scadenza: {label} deve appartenere soltanto a Luck Acceleration",
                )

        final_icon_cleanup = if_block_containing("Global.ActivePlayer.LuckIconEndTime > 0")
        checks.require(final_icon_cleanup is not None, "cleanup finale handle icona roulette non analizzabile")
        if final_icon_cleanup:
            final_icon_cleanup_masked = mask_strings(final_icon_cleanup)
            destroy_token = "Destroy Icon(Global.ActivePlayer.LuckIcon);"
            null_token = "Global.ActivePlayer.LuckIcon = Null;"
            timer_token = "Global.ActivePlayer.LuckIconEndTime = 0;"
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

        player_luck_reset = rule_by_subroutine(rules, "RestorePlayerLuck")
        checks.require(player_luck_reset is not None, "subroutine RestorePlayerLuck assente")
        player_luck_reset_masked = mask_strings(player_luck_reset.body) if player_luck_reset else ""

        for reset_name, player_expression in (
            ("RestorePlayerLuck", "Event Player"),
            ("RestoreActivePlayerLuck", "Global.ActivePlayer"),
        ):
            reset_rule = rule_by_subroutine(rules, reset_name)
            checks.require(reset_rule is not None, f"subroutine {reset_name} assente")
            if not reset_rule:
                continue
            stop_calls = list(iter_calls(reset_rule.body, "Stop Accelerating"))
            speed_calls = [
                call for call in iter_calls(reset_rule.body, "Set Move Speed")
                if len(call.args) == 2
                and call.args[0].strip() == player_expression
                and call.args[1].strip() == "100"
            ]
            checks.equal(len(stop_calls), 1, f"{reset_name}: unico Stop Accelerating")
            checks.equal(len(speed_calls), 1, f"{reset_name}: unico Move Speed 100")
            for call, label in (
                *((call, "Stop Accelerating") for call in stop_calls),
                *((call, "Move Speed 100") for call in speed_calls),
            ):
                branches = conditional_branches_containing(reset_rule.body, call.start)
                checks.require(
                    any(
                        f"{player_expression}.LuckEffect == 2" in mask_strings(branch)
                        for branch in branches
                    ),
                    f"{reset_name}: {label} deve essere riservato all'esito Acceleration",
                )

        death_cleanup = next(
            (rule for rule in rules_with_event(rules, "Player Died") if "LuckActive" in rule.body),
            None,
        )
        checks.require(death_cleanup is not None, "cleanup accelerazione alla morte assente")
        for cleanup_rule, label in (
            (death_cleanup, "morte"),
            (rule_by_subroutine(rules, "QuiescePlayer"), "quiete iniziale"),
        ):
            checks.require(cleanup_rule is not None, f"cleanup accelerazione {label} assente")
            if cleanup_rule:
                cleanup_masked = mask_strings(cleanup_rule.body)
                uses_shared_reset = "Call Subroutine(RestorePlayerLuck);" in cleanup_masked
                checks.require(
                    "Stop Accelerating(Event Player);" in cleanup_masked
                    or (uses_shared_reset and "Stop Accelerating(Event Player);" in player_luck_reset_masked),
                    f"cleanup accelerazione {label}: Stop Accelerating assente",
                )
                checks.require(
                    "Set Move Speed(Event Player, 100);" in cleanup_masked
                    or (uses_shared_reset and "Set Move Speed(Event Player, 100);" in player_luck_reset_masked),
                    f"cleanup accelerazione {label}: Move Speed 100 assente",
                )
                destroy_icon = "Destroy Icon(Event Player.LuckIcon);"
                null_icon = "Event Player.LuckIcon = Null;"
                checks.require(
                    destroy_icon in cleanup_masked
                    or (uses_shared_reset and destroy_icon in player_luck_reset_masked),
                    f"cleanup icona roulette {label}: Destroy Icon assente",
                )
                checks.require(
                    null_icon in cleanup_masked
                    or (uses_shared_reset and null_icon in player_luck_reset_masked),
                    f"cleanup icona roulette {label}: azzeramento handle assente",
                )
                if destroy_icon in cleanup_masked and null_icon in cleanup_masked:
                    checks.require(
                        cleanup_masked.index(destroy_icon) < cleanup_masked.index(null_icon),
                        f"cleanup icona roulette {label}: handle azzerato prima del destroy",
                    )
                elif uses_shared_reset and destroy_icon in player_luck_reset_masked and null_icon in player_luck_reset_masked:
                    checks.require(
                        player_luck_reset_masked.index(destroy_icon) < player_luck_reset_masked.index(null_icon),
                        f"cleanup icona roulette {label}: handle azzerato prima del destroy",
                    )

        health_calls = list(iter_calls(state_machine.body, "Set Player Health"))
        checks.equal(len(health_calls), 1, "cura completa self della roulette")
        if health_calls:
            checks.equal(
                tuple(argument.strip() for argument in health_calls[0].args),
                ("All Living Players(Team Of(Global.ActivePlayer))", "9999"),
                "Heart roulette deve curare al massimo tutta la squadra del proprietario",
            )
        heart_messages = [
            call for call in iter_calls(state_machine.body, "Small Message")
            if len(call.args) >= 2 and "HEART" in call.args[1]
        ]
        checks.equal(len(heart_messages), 1, "messaggio Heart roulette")
        if heart_messages:
            checks.equal(heart_messages[0].args[0].strip(), "Global.ActivePlayer",
                         "Heart roulette deve notificare soltanto il proprietario")
            checks.equal(
                trim_outer_parentheses(heart_messages[0].args[1]),
                'Custom String("TRY YOUR LUCK: HEART — FULL TEAM HEAL")',
                "Heart team-heal: unico messaggio inglese senza stato lingua o Local Player",
            )

        checks.equal(state_machine.body.count("Kill("), 0,
                     "Skull deve delegare la morte completa alla macchina globale")
        for token, label in (
            ("Global.ActivePlayer.NextForcedRevengeTime = Total Time Elapsed;", "timestamp primo tentativo"),
            ("Global.ActivePlayer.ForcedRevengeEndTime = Total Time Elapsed + 5;", "deadline anti-blocco"),
        ):
            checks.require(token in state_machine.body, f"Skull non arma {label}")
        checks.require("Total Time Elapsed" in state_machine.body,
                       "macchina Try Your Luck non confronta timestamp")
    for duration in (15, 10, 5):
        checks.require(re.search(rf"(?:Total Time Elapsed\s*\+\s*{duration}\b|(?:Burning|Hacked),\s*{duration}\))", source) is not None,
                       f"durata Try Your Luck {duration} s assente")


def validate_forced_death(checks: Checks, source: str, rules: list[Rule], players: set[str]) -> None:
    for name in ("RevengeClaimant", "NextForcedRevengeTime", "ForcedRevengeEndTime"):
        checks.require(name in players, f"stato morte completa assente: {name}")
    checks.require("NextSuicideTime" in players,
                   "cooldown Self Kill per-player assente")

    self_kill_rules = [
        rule
        for rule in rules
        if any(
            tuple(argument.strip() for argument in call.args) == ("Event Player", "Null")
            for call in iter_calls(rule.body, "Kill")
        )
    ]
    checks.equal(len(self_kill_rules), 1,
                 "Self Kill deve avere un solo owner single-shot")
    if self_kill_rules:
        self_kill = self_kill_rules[0]
        self_kill_calls = [
            call
            for call in iter_calls(self_kill.body, "Kill")
            if tuple(argument.strip() for argument in call.args) == ("Event Player", "Null")
        ]
        checks.equal(len(self_kill_calls), 1,
                     "Self Kill deve contenere un solo Kill(Event Player, Null)")
        if self_kill_calls:
            branches = conditional_branches_containing(self_kill.body, self_kill_calls[0].start)
            cooldown_branch = next(
                (
                    mask_strings(branch)
                    for branch in branches
                    if "Total Time Elapsed >= Event Player.NextSuicideTime" in mask_strings(branch)
                ),
                "",
            )
            checks.require(bool(cooldown_branch),
                           "Self Kill non è protetto dal cooldown per-player")
            kill_position = cooldown_branch.find("Kill(Event Player, Null);")
            for token, label in (
                (
                    "If(Total Time Elapsed >= Event Player.NextSuicideTime);",
                    "guardia timestamp",
                ),
                (
                    "Event Player.NextSuicideTime = Total Time Elapsed + 3;",
                    "arming esatto a 3 secondi",
                ),
                ("Clear Status(Event Player, Unkillable);", "rimozione Unkillable"),
                ("Set Damage Received(Event Player, 100);", "ripristino danni"),
            ):
                position = cooldown_branch.find(token)
                checks.require(
                    0 <= position < kill_position,
                    f"Self Kill cooldown incompleto: {label} deve precedere Kill",
                )
        checks.require('Self Elimination: ready in {0}s.' in self_kill.body,
                       "Self Kill cooldown: messaggio inglese dei secondi residui assente")
        checks.require(
            "Round To Integer(Event Player.NextSuicideTime - Total Time Elapsed, Up)"
            in self_kill.body,
            "Self Kill cooldown non mostra i secondi residui arrotondati",
        )
        checks.require(not wait_calls(self_kill.body) and action_loop_count(self_kill.body) == 0,
                       "Self Kill cooldown deve restare senza Wait/Loop")

    cooldown_writers: list[tuple[str, str]] = []
    for rule in rules:
        owner = subroutine_target(rule) or rule.name
        for match in re.finditer(
            r"Event Player\.NextSuicideTime\s*=(?!=)\s*([^;\r\n]+);",
            mask_strings(rule.body),
        ):
            cooldown_writers.append((owner, re.sub(r"\s+", "", match.group(1))))
    checks.equal(len(cooldown_writers), 3,
                 "Self Kill cooldown: numero writer setup/quiete/arming")
    checks.equal(sum(value == "0" for _, value in cooldown_writers), 2,
                 "Self Kill cooldown: reset consentiti solo a setup e rejoin")
    checks.equal(sum(value == "TotalTimeElapsed+3" for _, value in cooldown_writers), 1,
                 "Self Kill cooldown: arming esatto e unico a 3 secondi")
    for reset_owner in ("PreparePlayer", "QuiescePlayer"):
        checks.require((reset_owner, "0") in cooldown_writers,
                       f"Self Kill cooldown: reset {reset_owner} assente")

    active_luck_reset = rule_by_subroutine(rules, "RestoreActivePlayerLuck")
    checks.require(active_luck_reset is not None, "subroutine RestoreActivePlayerLuck assente")
    active_luck_reset_masked = mask_strings(active_luck_reset.body) if active_luck_reset else ""

    player_luck_reset = rule_by_subroutine(rules, "RestorePlayerLuck")
    checks.require(player_luck_reset is not None, "subroutine RestorePlayerLuck assente")
    player_luck_reset_masked = mask_strings(player_luck_reset.body) if player_luck_reset else ""

    processor = rule_by_subroutine(rules, "ProcessPlayerFastState")
    checks.require(processor is not None, "macchina globale morte completa assente")
    if processor:
        processor_masked = mask_strings(processor.body)
        kill_calls = list(iter_calls(processor.body, "Kill"))
        checks.equal(len(kill_calls), 1, "morte forzata deve avere un solo Kill nel processor globale")
        if len(kill_calls) == 1:
            checks.equal(
                tuple(argument.strip() for argument in kill_calls[0].args),
                (
                    "Global.ActivePlayer",
                    "Global.ActivePlayer.RevengeDeathPending == True ? Global.ActivePlayer.RevengeClaimant : Null",
                ),
                "Kill globale deve scegliere solo claimant Revenge oppure Null per Skull",
            )
            kill_position = kill_calls[0].start
            kill_branches = conditional_branches_containing(processor.body, kill_position)
            checks.require(bool(kill_branches), "morte completa: Kill non appartiene a un ramo condizionale")
            kill_branch = mask_strings(kill_branches[0]) if kill_branches else ""
            for token, label in (
                ("Has Spawned(Global.ActivePlayer) == True", "guardia spawn nello stesso ramo di Kill"),
                ("Is Alive(Global.ActivePlayer) == True", "retry soltanto se ancora vivo nello stesso ramo di Kill"),
                ("Global.ActivePlayer.NextForcedRevengeTime = Total Time Elapsed + 0.250;", "retry a timestamp"),
                ("Clear Status(Global.ActivePlayer, Unkillable);", "rimozione Unkillable"),
                ("Set Damage Received(Global.ActivePlayer, 100);", "ripristino danno ricevuto"),
            ):
                position = kill_branch.find(token)
                branch_kill_position = kill_branch.find("Kill(")
                checks.require(
                    0 <= position < branch_kill_position,
                    f"morte completa: {label} deve precedere Kill",
                )

        revenge_timeout_anchor = (
            "Set Player Variable(Global.ActivePlayer.RevengeClaimant, "
            "LockedRevengeTarget, Null);"
        )
        revenge_timeout_position = processor_masked.find(revenge_timeout_anchor)
        checks.require(revenge_timeout_position >= 0, "timeout Revenge: cleanup target claimant assente")
        if revenge_timeout_position >= 0:
            revenge_timeout_branches = conditional_branches_containing(
                processor.body, revenge_timeout_position
            )
            revenge_timeout_branch = (
                mask_strings(revenge_timeout_branches[0]) if revenge_timeout_branches else ""
            )
            checks.require(
                "Global.ActivePlayer.RevengeDeathPending == True" in revenge_timeout_branch,
                "timeout Revenge: cleanup non appartiene al ramo pending",
            )
            for token, label in (
                ("Global.ActivePlayer.RevengeDeathPending = False;", "flag pending"),
                ("Global.ActivePlayer.RevengeClaimant = Null;", "claimant"),
            ):
                checks.require(token in revenge_timeout_branch, f"timeout Revenge non azzera {label}")
            checks.require(
                any(
                    "Total Time Elapsed >= Global.ActivePlayer.ForcedRevengeEndTime" in mask_strings(branch)
                    for branch in revenge_timeout_branches[1:]
                ),
                "cleanup Revenge non appartiene al ramo di timeout",
            )

        skull_timeout_anchor = "Global.ActivePlayer.LuckActive = False;"
        skull_timeout_call = "Call Subroutine(RestoreActivePlayerLuck);"
        skull_timeout_position = processor_masked.find(skull_timeout_anchor)
        if skull_timeout_position < 0:
            skull_timeout_position = processor_masked.find(skull_timeout_call)
        checks.require(skull_timeout_position >= 0, "timeout Skull: rilascio stato assente")
        if skull_timeout_position >= 0:
            skull_timeout_branches = conditional_branches_containing(processor.body, skull_timeout_position)
            skull_timeout_branch = mask_strings(skull_timeout_branches[0]) if skull_timeout_branches else ""
            destroy_icon = "Destroy Icon(Global.ActivePlayer.LuckIcon);"
            direct_cleanup_ordered = (
                0 <= skull_timeout_branch.find(destroy_icon) < skull_timeout_branch.find(skull_timeout_anchor)
            )
            shared_cleanup_ordered = (
                skull_timeout_call in skull_timeout_branch
                and destroy_icon in active_luck_reset_masked
                and "Global.ActivePlayer.LuckActive = False;" in active_luck_reset_masked
                and active_luck_reset_masked.index(destroy_icon)
                < active_luck_reset_masked.index("Global.ActivePlayer.LuckActive = False;")
            )
            checks.require(
                direct_cleanup_ordered or shared_cleanup_ordered,
                "timeout Skull deve distruggere l'icona prima del rilascio",
            )
            checks.require(
                any(
                    "Total Time Elapsed >= Global.ActivePlayer.ForcedRevengeEndTime" in mask_strings(branch)
                    for branch in skull_timeout_branches[1:]
                ),
                "cleanup Skull non appartiene al ramo di timeout",
            )
        for token, label in (
            ("Global.ActivePlayer.RevengeDeathPending == True", "stato Revenge"),
            ("Global.ActivePlayer.LuckActive == True", "stato Try Your Luck"),
            ("Global.ActivePlayer.LuckEffect == 3", "esito Skull"),
            (
                "And(Global.ActivePlayer.LuckSpinCount == 0, Global.ActivePlayer.ForcedRevengeEndTime > 0)",
                "Skull finale armato dopo la roulette",
            ),
            ("Has Spawned(Global.ActivePlayer) == True", "guardia spawn"),
            ("Is Alive(Global.ActivePlayer) == True", "retry soltanto se ancora vivo"),
            ("Global.ActivePlayer.ForcedRevengeEndTime > 0", "deadline armata"),
            ("Total Time Elapsed >= Global.ActivePlayer.ForcedRevengeEndTime", "scadenza deadline"),
            ("Global.ActivePlayer.RevengeDeathPending == False", "blocco riapplicazione Kebal Revenge"),
            (
                "And(And(Global.ActivePlayer.LuckActive == True, Global.ActivePlayer.LuckSpinCount == 0), "
                "Or(And(Global.ActivePlayer.LuckEffect == 3, Global.ActivePlayer.ForcedRevengeEndTime > 0), "
                "And(Global.ActivePlayer.LuckEffect == 5, Global.ActivePlayer.LuckEffectEndTime > Total Time Elapsed))) == False",
                "blocco riapplicazione Kebal durante Skull/Burning finali",
            ),
        ):
            checks.require(token in processor_masked, f"morte completa: {label} assente")
        checks.require(
            "Global.ActivePlayer.LuckActive = False;" in processor_masked
            or (
                "Call Subroutine(RestoreActivePlayerLuck);" in processor_masked
                and "Global.ActivePlayer.LuckActive = False;" in active_luck_reset_masked
            ),
            "morte completa: rilascio Try Your Luck al timeout assente",
        )
        checks.require(
            "Global.ActivePlayer.MenuInputLocked = False;" in processor_masked
            or (
                "Call Subroutine(RestoreActivePlayerLuck);" in processor_masked
                and "Global.ActivePlayer.MenuInputLocked = False;" in active_luck_reset_masked
            ),
            "morte completa: rilascio input al timeout assente",
        )
        checks.require("Is In Alternate Form" not in processor_masked and "Hero(D.Va)" not in processor_masked,
                       "morte completa non deve dipendere da eroi o forme specifiche")

    punch = rule_by_subroutine(rules, "ProcessSuperPunch")
    punch_kills = list(iter_calls(punch.body, "Kill")) if punch else []
    checks.equal(len(punch_kills), 1, "Super Punch: unico Kill per ayunan nativo")
    if punch_kills:
        checks.equal(tuple(arg.strip() for arg in punch_kills[0].args),
                     ("Global.SuperPunchTarget", "Global.ActivePlayer"),
                     "Super Punch: Kill target selezionato attribuito al puncher")
    checks.equal(len(list(iter_calls(source, "Kill"))), 4,
                 "Kill deve esistere soltanto in Self Kill, Skull/Revenge e Super Punch")

    revenge_apply = rule_by_subroutine(rules, "ApplyRevengePage")
    checks.require(revenge_apply is not None, "dispatcher Revenge assente")
    if revenge_apply:
        apply_masked = mask_strings(revenge_apply.body)
        checks.require("Kill(" not in apply_masked,
                       "Revenge non deve uccidere direttamente al click")
        checks.require("Modify Player Variable At Index(Event Player, RevengeDebts" not in apply_masked,
                       "Revenge non deve consumare il debito prima della morte completa")
        checks.require('Revenge on {0}: paid!' not in revenge_apply.body,
                       "Revenge non deve annunciare successo prima della morte completa")
        for token, label in (
            ("Set Player Variable(Event Player.LockedRevengeTarget, RevengeDeathPending, True);", "flag pending"),
            ("Set Player Variable(Event Player.LockedRevengeTarget, RevengeClaimant, Event Player);", "claimant"),
            ("Set Player Variable(Event Player.LockedRevengeTarget, NextForcedRevengeTime, Total Time Elapsed);", "primo retry"),
            ("Set Player Variable(Event Player.LockedRevengeTarget, ForcedRevengeEndTime, Total Time Elapsed + 5);", "deadline"),
            ("Player Variable(Event Player.LockedRevengeTarget, RevengeDeathPending) == True", "blocco doppio claim"),
            ("Player Variable(Event Player.LockedRevengeTarget, LuckActive) == True", "blocco conflitto Try Your Luck"),
        ):
            checks.require(token in apply_masked, f"Revenge arming incompleto: {label}")

    death_recorder = next(
        (
            rule for rule in rules_with_event(rules, "Player Died")
            if "RevengeKillers" in rule.body and "RevengeDeathPending" in rule.body
        ),
        None,
    )
    checks.require(death_recorder is not None, "commit Revenge su Player Died assente")
    if death_recorder:
        recorder_masked = mask_strings(death_recorder.body)
        recompute = (
            "Index Of Array Value(Player Variable(Event Player.RevengeClaimant, "
            "RevengeKillers), Event Player)"
        )
        decrement = "Modify Player Variable At Index(Event Player.RevengeClaimant, RevengeDebts"
        for token, label in (
            ("If(Is Alive(Event Player) == False);", "conferma Is Alive falso"),
            ("Attacker == Event Player.RevengeClaimant", "coincidenza attacker-claimant"),
            (recompute, "ricalcolo indice debito al commit"),
            (decrement, "decremento al commit"),
            ("Event Player.RevengeDeathPending = False;", "rilascio flag pending"),
            ("Event Player.RevengeClaimant = Null;", "rilascio claimant"),
        ):
            checks.require(token in recorder_masked, f"commit Revenge incompleto: {label}")
        decrement_calls = [
            call for call in iter_calls(death_recorder.body, "Modify Player Variable At Index")
            if len(call.args) >= 2
            and call.args[0].strip() == "Event Player.RevengeClaimant"
            and call.args[1].strip() == "RevengeDebts"
        ]
        checks.equal(len(decrement_calls), 1, "commit Revenge deve avere un solo decremento debito")
        if len(decrement_calls) == 1:
            commit_branches = conditional_branches_containing(
                death_recorder.body, decrement_calls[0].start
            )
            attacker_branch = next(
                (
                    mask_strings(branch)
                    for branch in commit_branches
                    if "Attacker == Event Player.RevengeClaimant" in mask_strings(branch)
                ),
                "",
            )
            checks.require(bool(attacker_branch), "commit Revenge non è nel ramo attacker-claimant")
            recompute_position = attacker_branch.find(recompute)
            decrement_position = attacker_branch.find(decrement)
            abort_position = attacker_branch.find("Abort;", decrement_position + len(decrement))
            checks.require(
                0 <= recompute_position < decrement_position,
                "Revenge decrementa prima di ricalcolare l'indice nello stesso ramo",
            )
            checks.require(
                abort_position > decrement_position,
                "commit Revenge deve eseguire Abort prima del recorder naturale",
            )
        checks.require('Revenge on {0}: paid!' in death_recorder.body,
                       "successo Revenge non viene annunciato alla morte completa")

    luck_death = next(
        (
            rule for rule in rules_with_event(rules, "Player Died")
            if (
                "Destroy Icon(Event Player.LuckIcon);" in rule.body
                and "Event Player.LuckActive = False;" in rule.body
            )
            or (
                "Call Subroutine(RestorePlayerLuck);" in rule.body
                and "LuckActive" in rule.body
            )
        ),
        None,
    )
    checks.require(luck_death is not None, "cleanup morte Try Your Luck assente")
    if luck_death:
        conditions = rule_block(luck_death, "conditions") or ""
        checks.require("Is Alive(Event Player) == False;" in conditions,
                       "cleanup Try Your Luck deve attendere la morte completa")
        luck_death_masked = mask_strings(luck_death.body)
        uses_shared_reset = "Call Subroutine(RestorePlayerLuck);" in luck_death_masked
        for token, label in (
            ("Event Player.NextForcedRevengeTime = 0;", "reset retry"),
            ("Event Player.ForcedRevengeEndTime = 0;", "reset deadline"),
            ("Event Player.MenuInputLocked = False;", "rilascio latch input"),
            ("Event Player.MenuCommand = 0;", "rilascio comando menu"),
        ):
            checks.require(
                token in luck_death_masked
                or (uses_shared_reset and token in player_luck_reset_masked),
                f"cleanup morte Try Your Luck: {label} assente",
            )
        for button in ("Primary Fire", "Secondary Fire", "Interact", "Reload", "Ability 1", "Ability 2", "Ultimate"):
            token = f"Allow Button(Event Player, Button({button}));"
            checks.require(
                token in luck_death_masked
                or (uses_shared_reset and token in player_luck_reset_masked),
                f"cleanup morte Try Your Luck non riabilita {button}",
            )

    jump_respawn_death = next(
        (
            rule for rule in rules_with_event(rules, "Player Died")
            if "Event Player.DeathPosition = Position Of(Event Player);" in rule.body
        ),
        None,
    )
    checks.require(jump_respawn_death is not None, "regola morte Bangkit Lompat assente")
    if jump_respawn_death:
        conditions = rule_block(jump_respawn_death, "conditions") or ""
        checks.require(
            "Is Alive(Event Player) == False;" in conditions,
            "Bangkit Lompat deve attendere la morte completa",
        )

    dummy_death_stop = next(
        (
            rule for rule in rules_with_event(rules, "Player Died")
            if "Is Dummy Bot(Event Player) == True;" in (rule_block(rule, "conditions") or "")
            and "Stop Facing(Event Player);" in rule.body
            and "Stop Throttle In Direction(Event Player);" in rule.body
        ),
        None,
    )
    checks.require(dummy_death_stop is not None, "regola arresto dummy morto assente")
    if dummy_death_stop:
        conditions = rule_block(dummy_death_stop, "conditions") or ""
        checks.require(
            "Is Alive(Event Player) == False;" in conditions,
            "arresto dummy morto deve attendere la morte completa",
        )

    for subroutine in ("PreparePlayer", "QuiescePlayer"):
        lifecycle = rule_by_subroutine(rules, subroutine)
        checks.require(lifecycle is not None, f"lifecycle morte completa assente: {subroutine}")
        if lifecycle:
            lifecycle_masked = mask_strings(lifecycle.body)
            uses_shared_reset = "Call Subroutine(RestorePlayerLuck);" in lifecycle_masked
            for token in (
                "Event Player.RevengeDeathPending = False;",
                "Event Player.RevengeClaimant = Null;",
                "Event Player.NextForcedRevengeTime = 0;",
                "Event Player.ForcedRevengeEndTime = 0;",
            ):
                checks.require(
                    token in lifecycle_masked
                    or (uses_shared_reset and token in player_luck_reset_masked),
                    f"{subroutine}: reset morte completa assente: {token}",
                )

    luck_apply = rule_by_subroutine(rules, "ApplyLuckPage")
    if luck_apply:
        checks.require("Else If(Event Player.RevengeDeathPending == True);" in luck_apply.body,
                       "Try Your Luck può partire durante una Revenge pending")


def validate_cleanup_registry_guard(checks: Checks, cleanup: Rule) -> None:
    """Keep the bounded fallback reachable before any canonical-array lookup."""
    masked = mask_strings(cleanup.body)
    marker = "Global.LeavingPlayerIndex = -2;"
    checks.equal(masked.count(marker), 1, "cleanup leave: selezione fallback registro incompleto")
    if marker not in masked:
        return
    position = masked.index(marker)
    branches = conditional_branches_containing(cleanup.body, position)
    expected = (
        "If(Or(Global.LeavingPlayerIndex >= Count Of(Global.PlayerHudSlots), "
        "Or(Global.LeavingPlayerIndex >= Count Of(Global.PlayerListHudIds), "
        "Or(Global.LeavingPlayerIndex >= Count Of(Global.MenuHudIds), "
        "Global.LeavingPlayerIndex >= Count Of(Global.InspectionTextIds)))));"
    )
    packed = lambda text: re.sub(r"\s+", "", mask_strings(text))
    guarded = [branch for branch in branches if packed(branch.splitlines()[0]) == packed(expected)]
    checks.equal(len(guarded), 1, "cleanup leave: guardia lunghezze per tutti gli array canonici")
    if guarded:
        body = packed(guarded[0])
        checks.require("Global.CleanupPlayerIndex=Global.LeavingPlayerIndex;Global.LeavingPlayerIndex=-2;" in body,
                       "cleanup leave: fallback deve conservare indice originale prima del sentinel")
    normal = masked.find("If(Global.LeavingPlayerIndex >= 0);")
    slot_read = masked.find("Global.LeavingDebtIndex = Global.PlayerHudSlots[Global.CleanupPlayerIndex];")
    checks.require(0 <= position < normal < slot_read,
                   "cleanup leave: guardia registro deve precedere accessi canonici")
    checks.require(any(packed(branch.splitlines()[0]) == "If(Global.LeavingPlayerIndex>-1);" for branch in branches),
                   "cleanup leave: fallback limitato a identità ancora registrata")


def validate_lifecycle(checks: Checks, rules: list[Rule], subroutines: set[str]) -> None:
    checks.require(LIFECYCLE_SUBROUTINES <= subroutines,
                   "subroutine lifecycle Siapkan/Tenangkan/Bersihkan incomplete")
    joined = rules_with_event(rules, "Player Joined Match")
    left = rules_with_event(rules, "Player Left Match")
    checks.equal(len(joined), 0, "lifecycle join deve essere global-first senza Player Joined Match")
    checks.equal(len(left), 1, "regola Player Left Match unica")
    if left:
        body = left[0].body
        checks.require("Wait(0.500, Ignore Condition);" in body,
                       "leave deve attendere 0,500 s prima di distinguere uscita e cambio team")
        checks.require("Abort If(Entity Exists(Event Player) == True);" in body,
                       "leave deve ignorare ogni entità ancora valida dopo il grace period")
        checks.require("Call Subroutine(CleanupPlayer);" in body,
                       "leave vero non esegue cleanup esatto roster/HUD")
        checks.require("Call Subroutine(QuiescePlayer);" not in body,
                       "leave vero non deve normalizzare engine state")
        checks.require("Event Player.HudSlot = -1;" not in body,
                       "leave non deve alterare lo slot prima della lookup per identità esatta")
        conditions = rule_block(left[0], "conditions") or ""
        checks.require(
            "Is Dummy Bot(Event Player) == False;" in conditions
            and "Event Player.IsAutomaticBot == True" in conditions
            and "Event Player.IsHuman == True" in conditions
            and "Array Contains(Global.HumanPlayers, Event Player)" in conditions,
            "Player Left Match deve includere iBot e umani registrati, escludendo i dummy nativi",
        )
        bot_anchor = body.find("If(Event Player.IsAutomaticBot == True);")
        bot_branches = conditional_branches_containing(body, bot_anchor) if bot_anchor >= 0 else []
        bot_branch = mask_strings(bot_branches[0]) if bot_branches else ""
        checks.require(bool(bot_branch), "Player Left Match non ha un ramo iniziale dedicato agli iBot")
        destroy = bot_branch.find("Destroy In-World Text(Event Player.LuckVisionText);")
        clear = bot_branch.find("Event Player.LuckVisionText = Null;")
        abort = bot_branch.find("Abort;")
        checks.require(0 <= destroy < clear < abort,
                       "leave iBot deve distruggere LuckVisionText, azzerarlo e Abort")
        checks.require("Call Subroutine(CleanupPlayer);" not in bot_branch,
                       "leave iBot non deve entrare nel cleanup umano")

    classifier = next((rule for rule in rules if "Append To Array(Global.HumanPlayers, Event Player)" in rule.body), None)
    checks.require(classifier is not None, "registrazione roster umano assente")
    if classifier:
        checks.require("Abort If(Array Contains(Global.HumanPlayers, Event Player));" in classifier.body,
                       "join duplicato può aggiungere due volte il roster")
        checks.require("Array Contains(Global.HumanPlayers, Event Player) == False;" in classifier.body,
                       "classifier non deve rieseguire sui player già registrati nel roster")
        slot_anchor = classifier.body.find("If(Count Of(Global.AvailableHudSlots) == 0);")
        slot_branches = (
            conditional_branches_containing(classifier.body, slot_anchor)
            if slot_anchor >= 0 else []
        )
        checks.require(bool(slot_branches), "classifier: retry senza slot non isolato")
        if slot_branches:
            slot_retry = mask_strings(min(slot_branches, key=len))
            retry_order = tuple(
                slot_retry.find(token)
                for token in (
                    "Event Player.IsClassified = False;",
                    "Event Player.IsPrepared = False;",
                    "Event Player.TeamChangeProcessed = False;",
                    "Event Player.PlayerCycleActive = False;",
                    "Event Player.TeamCycleDeadline = Total Time Elapsed + 0.250;",
                    "Global.TeamCyclePlayer = Null;",
                    "Global.TeamCycleTime = Total Time Elapsed + 0.250;",
                    "Abort;",
                )
            )
            checks.require(
                all(position >= 0 for position in retry_order)
                and retry_order == tuple(sorted(retry_order)),
                "classifier senza slot deve liberare lifecycle/lock e riarmare un retry temporizzato",
            )
            checks.require(
                "If(Global.TeamCyclePlayer == Event Player);" in slot_retry,
                "classifier senza slot può liberare soltanto il proprio lock globale",
            )
        classifier_bot_anchor = classifier.body.find("If(Event Player.IsAutomaticBot == True);")
        classifier_bot_branches = (
            conditional_branches_containing(classifier.body, classifier_bot_anchor)
            if classifier_bot_anchor >= 0 else []
        )
        checks.require(
            bool(classifier_bot_branches)
            and min(classifier_bot_branches, key=len).find("Abort;") >= 0
            and classifier_bot_anchor < slot_anchor,
            "iBot può raggiungere il roster umano: esclusione/Abort deve precedere il gate slot umano",
        )
        checks.require(
            "Abort If(Count Of(Global.AvailableHudSlots) == 0);" not in classifier.body,
            "classifier non deve bloccarsi dopo aver consumato il tentativo senza slot roster",
        )
        checks.require(classifier.body.find("Event Player.IsHuman = True;") < classifier.body.find("Event Player.LastHero = Hero Of(Event Player);"),
                       "classificazione umana non inizializza LastHero dopo IsHuman=True")
        name_guard = "If(Or(Event Player.WasPrepared == False, Or(Event Player.DisplayName == Null, Event Player.DisplayName == Custom String(\"\"))));"
        name_assign = "Event Player.DisplayName = Evaluate Once(Custom String(\"{0}\", Event Player));"
        name_empty = "If(Or(Event Player.DisplayName == Null, Event Player.DisplayName == Custom String(\"\")));"
        guard_pos = classifier.body.find(name_guard)
        assign_pos = classifier.body.find(name_assign)
        empty_pos = classifier.body.find(name_empty)
        checks.require(guard_pos >= 0, "classifier deve proteggere DisplayName cache durante team-switch")
        checks.require(assign_pos >= 0, "classifier deve poter acquisire DisplayName su join iniziale")
        checks.require(empty_pos >= 0, "classifier senza guardia nome vuoto")
        checks.require(guard_pos < assign_pos < empty_pos,
                       "classifier deve aggiornare DisplayName solo sotto guardia e prima del check nome vuoto")

    setup = rule_by_subroutine(rules, "PreparePlayer")
    checks.require(setup is not None, "PreparePlayer assente")
    if setup:
        reset_tokens = (
            "MainMenuCursor = 0;",
            "GenreIndex = -1;", "CameraMode = 0;", "ColorIndex = 0;",
            "VotedPlayer = Null;", "UnkillableMode = 0;", "VoiceIndex = 0;", "IconIndex = 0;",
            "CrouchTravelEnabled = False;", "InspectionPrivacyActive = False;",
            "AllowDummyBotFollow = False;",
            "LuckActive = False;", "MenuHud = Null;",
            "PlayerListUpdatePending = False;",
        )
        for token in reset_tokens:
            checks.require(token in setup.body, f"reset setup iniziale mancante: {token}")

    quiet = rule_by_subroutine(rules, "QuiescePlayer")
    checks.require(quiet is not None, "QuiescePlayer assente")
    if quiet:
        checks.require(not wait_calls(quiet.body) and action_loop_count(quiet.body) == 0,
                       "QuiescePlayer deve essere atomica e senza Wait/Loop")
        quiet_masked = mask_strings(quiet.body)
        for token in (
            "Call Subroutine(CloseMenu);",
            "Allow Button(Event Player, Button(Melee));",
            "Stop Camera(Event Player);",
            "Stop Modifying Hero Voice Lines(Event Player);",
            "Stop Chasing Player Variable(Event Player, MenuColor);",
            "Detach Players(Event Player);",
            "Enable Nameplates(All Players(All Teams), Event Player);",
            "Event Player.NameplatesDisabled = False;",
            "Event Player.TravelAttachmentActive = False;",
            "Event Player.TravelAttachmentTarget = Null;",
            "Event Player.UnkillableMode = 0;",
            "Call Subroutine(RestorePlayerLuck);",
        ):
            checks.require(token in quiet_masked, f"reset engine completo mancante: {token}")
        # Flow is delimited by semicolons, not newlines: an inline If must not hide a gated reset.
        required_unconditional = {"Call Subroutine(CloseMenu)": [],
                                  "Call Subroutine(RestorePlayerLuck)": []}
        depth = 0
        for statement in mask_strings(rule_block(quiet, "actions") or "").split(";"):
            statement = statement.strip()
            if re.match(r"^(?:If|While|For Global Variable|For Player Variable)\s*\(", statement):
                depth += 1
            elif statement == "End":
                depth -= 1
            elif statement in required_unconditional:
                required_unconditional[statement].append(depth)
        for token, levels in required_unconditional.items():
            checks.require(bool(levels) and all(level == 0 for level in levels),
                           f"reset engine completo deve essere incondizionato: {token};")
        checks.require(0 <= quiet_masked.find("Event Player.UnkillableMode = 0;")
                       < quiet_masked.find("Call Subroutine(RestorePlayerLuck);"),
                       "reset engine completo deve spegnere Unkillable prima del ripristino condiviso")
        for engine_action, field_reset in (
            ("Detach Players(Event Player);", "Event Player.TravelAttachmentActive = False;"),
            ("Enable Nameplates(All Players(All Teams), Event Player);", "Event Player.NameplatesDisabled = False;"),
        ):
            checks.require(0 <= quiet_masked.find(engine_action) < quiet_masked.find(field_reset),
                           f"reset engine completo azzera il latch prima del ripristino: {field_reset}")
        checks.require("Event Player.UnkillableIcon = Null;" not in quiet_masked,
                       "reset engine deve conservare UnkillableIcon fino alla distruzione canonica")

    close_menu = rule_by_subroutine(rules, "CloseMenu")
    if close_menu:
        masked = mask_strings(close_menu.body)
        canonical = "Global.MenuHudIds[Index Of Array Value(Global.HumanPlayers, Event Player)]"
        positions = tuple(masked.find(token) for token in (
            f"Destroy HUD Text({canonical});",
            f"If(Event Player.MenuHud == {canonical});",
            "Event Player.MenuHud = Null;",
            f"{canonical} = 0;",
            "Destroy HUD Text(Event Player.MenuHud);",
        ))
        checks.require(all(position >= 0 for position in positions) and positions == tuple(sorted(positions)),
                       "chiusura menu deve distruggere prima il canonico, evitare doppio destroy e poi liberare il fallback locale")

    cleanup = rule_by_subroutine(rules, "CleanupPlayer")
    checks.require(cleanup is not None, "CleanupPlayer assente")
    if cleanup:
        validate_cleanup_registry_guard(checks, cleanup)
        checks.require(not wait_calls(cleanup.body) and action_loop_count(cleanup.body) == 0,
                       "CleanupPlayer deve essere atomica e senza Wait/Loop")
        cleanup_masked = mask_strings(cleanup.body)
        for token in (
            "Global.CleanupSubject = Event Player;",
            "Global.LeavingPlayerIndex = Index Of Array Value(Global.HumanPlayers, Global.CleanupSubject);",
            "Global.CleanupPlayerIndex = Global.LeavingPlayerIndex;",
            "Global.LeavingDebtIndex = Global.PlayerHudSlots[Global.CleanupPlayerIndex];",
            "Remove From Array By Index",
        ):
            checks.require(token in cleanup.body, f"cleanup leave esatto incompleto: {token}")
        checks.require("Index Of Array Value(Global.PlayerHudSlots" not in cleanup.body,
                       "cleanup leave non deve usare fallback slot HUD")
        recycle = ("Global.AvailableHudSlots = Sorted Array(Append To Array("
                   "Global.AvailableHudSlots, Global.LeavingDebtIndex), Current Array Element);")
        recycle_position = cleanup_masked.find(recycle)
        checks.require(recycle_position >= 0, "cleanup leave non ricicla lo slot HUD canonico")
        if recycle_position >= 0:
            headers = [re.sub(r"\s+", "", branch.splitlines()[0]) for branch in
                       conditional_branches_containing(cleanup.body, recycle_position)]
            checks.require("If(Global.LeavingPlayerIndex>=0);" in headers,
                           "cleanup leave: riciclo slot deve essere idempotente e protetto da identità registrata")
        slot_read = cleanup_masked.find("Global.LeavingDebtIndex = Global.PlayerHudSlots[Global.CleanupPlayerIndex];")
        removal_positions = []
        for array, destroy_action in (
            ("PlayerListHudIds", "Destroy HUD Text"),
            ("MenuHudIds", "Destroy HUD Text"),
            ("InspectionTextIds", "Destroy In-World Text"),
        ):
            destroy = f"{destroy_action}(Global.{array}[Global.CleanupPlayerIndex]);"
            removal = f"Modify Global Variable({array}, Remove From Array By Index, Global.CleanupPlayerIndex);"
            positions = tuple(cleanup_masked.find(token) for token in (destroy, recycle, removal))
            checks.require(all(position >= 0 for position in positions) and positions == tuple(sorted(positions)),
                           f"cleanup leave: distruzione handle prima del riciclo/rimozione richiesta: {array}")
            removal_positions.append(positions[-1])
        slot_remove = cleanup_masked.find("Modify Global Variable(PlayerHudSlots, Remove From Array By Index, Global.CleanupPlayerIndex);")
        roster_remove = cleanup_masked.find("Modify Global Variable(HumanPlayers, Remove From Array By Index, Global.CleanupPlayerIndex);")
        checks.require(0 <= slot_read < recycle_position < slot_remove < roster_remove
                       and all(0 <= position < roster_remove for position in removal_positions),
                       "cleanup leave: rimuovere roster soltanto dopo handle paralleli e slot canonico")
        vote_cleanup = list(iter_calls(cleanup.body, "Filtered Array"))
        checks.equal(len(vote_cleanup), 1,
                     "cleanup leave: numero filtri per cancellare voti verso il leaver")
        if vote_cleanup:
            checks.equal(vote_cleanup[0].args[0].strip(), "Global.HumanPlayers",
                         "cleanup leave: filtro voti limitato al roster umano")
            checks.equal(
                re.sub(r"\s+", "", vote_cleanup[0].args[1]),
                re.sub(
                    r"\s+",
                    "",
                    "Player Variable(Current Array Element, VotedPlayer) == Global.CleanupSubject",
                ),
                "cleanup leave: filtro voti deve puntare esattamente al giocatore uscito",
            )
        vote_reset = (
            "Set Player Variable(Filtered Array(Global.HumanPlayers, "
            "Player Variable(Current Array Element, VotedPlayer) == Global.CleanupSubject), "
            "VotedPlayer, Null);"
        )
        checks.require(vote_reset in cleanup.body,
                       "cleanup leave non azzera i riferimenti VotedPlayer verso il leaver")
        checks.require(
            cleanup.body.find(vote_reset) < cleanup.body.find("Remove From Array By Index"),
            "cleanup leave azzera i voti dopo aver rimosso il giocatore dal roster",
        )
        recount = rule_by_subroutine(rules, "RecountVotes")
        recount_token = (
            "Set Player Variable(Global.HumanPlayers[Global.VoterIndex], VoteCount, "
            "Count Of(Filtered Array(Global.HumanPlayers, Player Variable(Current Array Element, "
            "VotedPlayer) == Global.HumanPlayers[Global.VoterIndex])));"
        )
        checks.require(
            recount is not None and recount_token in mask_strings(recount.body),
            "conteggio voti deve derivare dai riferimenti dei voter rimasti nel roster",
        )
        checks.require("Global.CleanupSubject.VotedPlayer" not in cleanup_masked,
                       "cleanup leave non deve leggere il voto dall'entità uscita")

        for rule in rules:
            if rule == cleanup:
                continue
            for assignment in re.finditer(
                r"(Event Player|Global\.ActivePlayer)\.(UnkillableIcon|LuckIcon) = (Last Created Entity|Null);",
                mask_strings(rule.body),
            ):
                owner, handle, value = assignment.groups()
                registry = {"UnkillableIcon": "UnkillableIconIds", "LuckIcon": "LuckIconIds"}[handle]
                mirror = (f"If(Array Contains(Global.HumanPlayers, {owner}));"
                          f"Global.{registry}[Global.PlayerHudSlots["
                          f"Index Of Array Value(Global.HumanPlayers, {owner})]] = "
                          + ("0;" if value == "Null" else f"{owner}.{handle};"))
                following = re.sub(r"\s+", "", rule.body[assignment.end():])
                checks.require(following.startswith(re.sub(r"\s+", "", mirror)),
                               f"{rule.name}: mirror icona canonico mancante dopo {handle} = {value}")

        for handle, destroy_action in (
            ("LuckIcon", "Destroy Icon"),
            ("UnkillableIcon", "Destroy Icon"),
            ("LuckEffectHud", "Destroy HUD Text"),
            ("LuckVisionText", "Destroy In-World Text"),
            ("TravelText", "Destroy In-World Text"),
        ):
            if destroy_action == "Destroy Icon":
                registry = {"UnkillableIcon": "UnkillableIconIds", "LuckIcon": "LuckIconIds"}[handle]
                owner = f"Global.{registry}[Global.LeavingDebtIndex]"
                guard = f"If({owner} != 0);"
                destroy = f"Destroy Icon({owner});"
                clear = f"{owner} = 0;"
            else:
                guard = f"If(Global.CleanupSubject.{handle} != Null);"
                destroy = f"{destroy_action}(Global.CleanupSubject.{handle});"
                clear = f"Global.CleanupSubject.{handle} = Null;"
            positions = tuple(cleanup_masked.find(token) for token in (guard, destroy, clear))
            checks.require(
                all(position >= 0 for position in positions)
                and positions[0] < positions[1] < positions[2],
                f"cleanup leave non distrugge e azzera handle orfano: {handle}",
            )

        revenge_loops = list(iter_calls(cleanup.body, "For Global Variable"))
        checks.equal(len(revenge_loops), 1,
                     "cleanup leave: una sola scansione atomica dei survivor Revenge")
        if revenge_loops:
            checks.equal(
                tuple(argument.strip() for argument in revenge_loops[0].args),
                ("VoterIndex", "0", "Count Of(Global.HumanPlayers)", "1"),
                "cleanup leave: scansione survivor Revenge",
            )
        for token, label in (
            (
                "Global.LeavingRevengeIndex = Index Of Array Value(Player Variable("
                "Global.HumanPlayers[Global.VoterIndex], RevengeKillers), "
                "Global.CleanupSubject);",
                "indice debito del leaver",
            ),
            (
                "Modify Player Variable(Global.HumanPlayers[Global.VoterIndex], "
                "RevengeKillers, Remove From Array By Index, Global.LeavingRevengeIndex);",
                "rimozione attacker",
            ),
            (
                "Modify Player Variable(Global.HumanPlayers[Global.VoterIndex], "
                "RevengeDebts, Remove From Array By Index, Global.LeavingRevengeIndex);",
                "rimozione debito parallela",
            ),
            (
                "Set Player Variable(Global.HumanPlayers[Global.VoterIndex], "
                "LockedRevengeTarget, Null);",
                "rilascio target locked",
            ),
            (
                "Set Player Variable(Global.HumanPlayers[Global.VoterIndex], "
                "RevengeClaimant, Null);",
                "rilascio claimant",
            ),
            (
                "Set Player Variable(Global.HumanPlayers[Global.VoterIndex], "
                "RevengeDeathPending, False);",
                "annullamento morte Revenge",
            ),
        ):
            checks.require(token in cleanup_masked,
                           f"cleanup leave Revenge incompleto: {label}")
        debt_remove = cleanup_masked.find(
            "Modify Player Variable(Global.HumanPlayers[Global.VoterIndex], "
            "RevengeKillers, Remove From Array By Index, Global.LeavingRevengeIndex);"
        )
        count_remove = cleanup_masked.find(
            "Modify Player Variable(Global.HumanPlayers[Global.VoterIndex], "
            "RevengeDebts, Remove From Array By Index, Global.LeavingRevengeIndex);"
        )
        roster_remove = cleanup_masked.find(
            "Modify Global Variable(HumanPlayers, Remove From Array By Index, "
            "Global.CleanupPlayerIndex);"
        )
        checks.require(
            0 <= debt_remove < count_remove < roster_remove,
            "cleanup leave deve rimuovere in tandem attacker/debito prima del roster",
        )
        for forbidden in (
            "Allow Button(", "Clear Status(",
            "Set Move Speed(", "Set Damage Received(", "Set Knockback Received(",
            "Call Subroutine(RestorePlayerLuck);", "Call Subroutine(QuiescePlayer);",
        ):
            checks.require(forbidden not in cleanup.body, f"cleanup leave troppo pesante: {forbidden}")

    fast = rule_by_subroutine(rules, "ProcessPlayerFastState")
    checks.require(fast is not None, "dispatcher globale ProcessPlayerFastState assente")
    if fast:
        for token in (
            "Array Contains(Global.HumanPlayers, Global.ActivePlayer) == True",
            "Global.ActivePlayer.PlayerCycleActive == False",
            "Global.ActivePlayer.WasPrepared == False",
            "Global.ActivePlayer.PlayerCycleActive = False;",
            "Global.ActivePlayer.TeamCycleTargetTeam = Team Of(Global.ActivePlayer);",
            "Global.ActivePlayer.TeamCycleDeadline = Total Time Elapsed + 0.250;",
            "Array Contains(Global.HumanPlayers, Global.ActivePlayer) == False",
            "Global.ActivePlayer.TeamChangeProcessed == False",
            "Global.ActivePlayer.TeamChangeProcessed = True;",
            "Global.ActivePlayer.IsPrepared = False;",
            "Global.ActivePlayer.IsHuman = False;",
            "Global.ActivePlayer.TeamCycleDeadline = Total Time Elapsed + 0.250;",
            "Global.TeamCyclePlayer == Null",
            "Or(Array Contains(Global.HumanPlayers, Global.ActivePlayer) == False, Global.ActivePlayer.PlayerCycleActive == True)",
            "Global.ActivePlayer.TeamCycleTargetTeam == Team Of(Global.ActivePlayer)",
            "Global.TeamCyclePlayer = Global.ActivePlayer;",
            "Has Spawned(Global.ActivePlayer) == True",
        ):
            checks.require(token in fast.body, f"dispatcher team-switch cleanup incompleto: {token}")

        checks.require(
            "Server Load < 150" not in fast.body,
            "dispatcher team-switch non deve dipendere da Server Load < 150",
        )
        checks.require(
            "Global.ActivePlayer.PlayerListUpdatePending = True;" not in fast.body,
            "dispatcher team-switch non deve più usare pending roster ringan",
        )
        checks.require(
            fast.body.count("Global.ActivePlayer.IsAutomaticBot == False") >= 3,
            "dispatcher team-switch deve escludere gli iBot in tutti i gate essenziali",
        )
        checks.require(
            "Call Subroutine(PreparePlayer);" not in fast.body,
            "team switch non deve chiamare PreparePlayer",
        )

        checks.require("Global.ActivePlayer.LastTeam != Team Of(Global.ActivePlayer)"
                       not in mask_strings(fast.body),
                       "team switch registrato deve essere gestito nel contesto Each Player")
        repair_position = fast.body.find("Global.ActivePlayer.IsHuman = True;")
        repair_branches = conditional_branches_containing(fast.body, repair_position) if repair_position >= 0 else []
        repair = mask_strings(min(repair_branches, key=len)) if repair_branches else ""
        checks.require("Global.ActivePlayer.PlayerCycleActive == False" in repair,
                       "repair roster non deve riattivare un player mentre il team-switch è in quarantena")
        pending_position = fast.body.find("Global.ActivePlayer.TeamCycleTargetTeam = Team Of(Global.ActivePlayer);")
        pending_branches = conditional_branches_containing(fast.body, pending_position) if pending_position >= 0 else []
        pending = mask_strings(min(pending_branches, key=len)) if pending_branches else ""
        checks.require("Or(Global.ActivePlayer.TeamChangeProcessed == False, Global.ActivePlayer.TeamCycleTargetTeam != Team Of(Global.ActivePlayer))" in pending,
                       "lifecycle pending deve aggiornare il target dopo un secondo cambio squadra")
        for token in ("If(Global.TeamCyclePlayer == Global.ActivePlayer);",
                      "Global.TeamCyclePlayer = Null;",
                      "Global.TeamCycleTime = Total Time Elapsed + 0.250;"):
            checks.require(token in pending, "lifecycle pending deve rilasciare la propria vecchia prenotazione")
        claim_position = fast.body.find("Global.TeamCyclePlayer = Global.ActivePlayer;")
        claim_branches = conditional_branches_containing(fast.body, claim_position) if claim_position >= 0 else []
        claim = mask_strings(min(claim_branches, key=len)) if claim_branches else ""
        checks.require("Or(Array Contains(Global.HumanPlayers, Global.ActivePlayer) == False, Global.ActivePlayer.PlayerCycleActive == True)" in claim,
                       "lifecycle prenotazione deve accettare join iniziale o quarantena team-switch")
        checks.require("Global.ActivePlayer.TeamCycleTargetTeam == Team Of(Global.ActivePlayer)" in claim,
                       "lifecycle prenotazione deve richiedere team target stabile")
        checks.require("And(Total Time Elapsed >= Global.TeamCycleTime, Total Time Elapsed >= Global.ActivePlayer.TeamCycleDeadline)" in claim,
                       "lifecycle prenotazione deve attendere entrambe le scadenze prima del lock")

    team_switch = team_switch_worker(rules)
    checks.require(team_switch is not None, "detector team-switch Each Player assente")
    if team_switch:
        conditions = mask_strings(rule_block(team_switch, "conditions") or "")
        for token in (
            "Global.IsReady == True;",
            "Is Dummy Bot(Event Player) == False;",
            "Event Player.IsAutomaticBot == False;",
            "Array Contains(Global.HumanPlayers, Event Player) == True;",
            "Event Player.LastTeam != Team Of(Event Player);",
        ):
            checks.require(token in conditions,
                           f"detector team-switch senza guardia: {token}")
        actions = mask_strings(rule_block(team_switch, "actions") or "")
        for token in (
            "Event Player.PlayerListUpdatePending = False;",
            "Event Player.TeamChangeProcessed = True;",
            "Event Player.PlayerCycleActive = True;",
            "Event Player.IsPrepared = False;",
            "Event Player.IsHuman = False;",
            "Event Player.LastTeam = Team Of(Event Player);",
            "Event Player.TeamCycleTargetTeam = Team Of(Event Player);",
            "Event Player.TeamCycleDeadline = Total Time Elapsed + 0.500;",
            "If(Global.TeamCyclePlayer == Event Player);",
            "Global.TeamCyclePlayer = Null;",
            "Global.TeamCycleTime = Total Time Elapsed + 0.250;",
        ):
            checks.require(token in actions, f"detector team-switch cleanup incompleto: {token}")
        order = tuple(actions.find(token) for token in (
            "Event Player.TeamChangeProcessed = True;",
            "Event Player.PlayerCycleActive = True;",
            "Event Player.IsPrepared = False;",
            "Event Player.IsHuman = False;",
            "Event Player.LastTeam = Team Of(Event Player);",
        ))
        checks.require(all(position >= 0 for position in order) and order == tuple(sorted(order)),
                       "detector team-switch deve attivare quarantena prima del commit del team")
        removal = "Global.SuperPunchPlayers = Remove From Array(Global.SuperPunchPlayers, Event Player);"
        stop = "Stop Chasing Player Variable(Event Player, ObjectiveIconPosition);"
        quiescence_order = tuple(actions.find(token) for token in (
            "Event Player.TeamChangeProcessed = True;",
            "Event Player.PlayerCycleActive = True;",
            "Event Player.IsHuman = False;",
            removal,
            stop,
            "Event Player.LastTeam = Team Of(Event Player);",
            "Event Player.TeamCycleTargetTeam = Team Of(Event Player);",
            "Event Player.TeamCycleDeadline = Total Time Elapsed + 0.500;",
        ))
        checks.require(all(position >= 0 for position in quiescence_order)
                       and quiescence_order == tuple(sorted(quiescence_order)),
                       "detector team-switch deve fermare icona e registro Punch dopo quarantena e prima del commit/scadenza")
        stops = list(iter_calls(actions, "Stop Chasing Player Variable"))
        checks.require(len(stops) == 1 and stops[0].args == ("Event Player", "ObjectiveIconPosition"),
                       "detector team-switch: unica chase fermata deve essere ObjectiveIconPosition del proprio Event Player")
        if stops:
            branches = conditional_branches_containing(actions, stops[0].start)
            checks.require(len(branches) == 1
                           and re.sub(r"\s+", "", branches[0]).startswith("If(EntityExists(EventPlayer)==True);"),
                           "detector team-switch: Stop chase richiede la guardia Entity Exists locale")
        depth, removal_depths = 0, []
        for statement in actions.split(";"):
            statement = statement.strip()
            if re.match(r"^(?:If|While|For Global Variable|For Player Variable)\s*\(", statement):
                depth += 1
            elif statement == "End":
                depth -= 1
            elif statement == removal[:-1]:
                removal_depths.append(depth)
            call = re.match(r"^\s*([A-Za-z][A-Za-z ]*)\s*\(", statement)
            if call:
                checks.require(call.group(1).strip() in {"If", "Else If", "Stop Chasing Player Variable"},
                               "detector team-switch: unica azione engine consentita è Stop chase locale senza cleanup")
        checks.require(removal_depths == [0],
                       "detector team-switch: rimozione registro Punch deve essere unica e incondizionata")
        checks.require(re.search(r"Event Player\.ObjectiveIconPosition\s*=(?!=)", actions) is None,
                       "detector team-switch: non deve resettare ObjectiveIconPosition prima del worker stabile")
        for target in re.findall(r"Global\.([A-Za-z][A-Za-z0-9_]*(?:\[[^\]]+\])?)\s*=(?!=)", actions):
            checks.require(target in {"SuperPunchPlayers", "TeamCyclePlayer", "TeamCycleTime"},
                           "detector team-switch: nessuna nuova assegnazione scratch o registro globale")
        checks.require(not wait_calls(team_switch.body) and action_loop_count(team_switch.body) == 0,
                       "detector team-switch deve essere atomico senza Wait/Loop")
        checks.require(re.search(r"\bAbort(?:\s+If)?\s*(?:\(|;)", actions) is None,
                       "detector team-switch: il detector non deve usare Abort")
        checks.require("Server Load" not in conditions,
                       "detector team-switch non deve dipendere dal carico server")
        checks.require("Call Subroutine(QuiescePlayer);" not in actions,
                       "detector team-switch non deve fare reset engine durante la transizione nativa")
        checks.require("Call Subroutine(CleanupPlayer);" not in actions,
                       "detector team-switch non deve fare cleanup roster durante la transizione nativa")
        checks.require("Event Player.PlayerListUpdatePending = True;" not in actions,
                       "detector team-switch non deve usare pending roster ringan")
        checks.require("Call Subroutine(PreparePlayer);" not in actions,
                       "team switch deve attendere il worker di setup serializzato")
        checks.require("Global.ActivePlayer" not in actions,
                       "detector team-switch non deve riusare lo scratch del scheduler")

    roster_hud_rules = [
        rule for rule in rules
        if event_type(rule) == "Ongoing - Each Player"
        and "Create HUD Text(" in rule.body
        and "Event Player.PlayerListHud = Last Text ID;" in rule.body
        and "Event Player.PlayerHudCreated = True;" in rule.body
    ]
    checks.require(bool(roster_hud_rules), "renderer roster post-team-switch assente")
    checks.require(
        len(roster_hud_rules) == 1,
        "classifier e renderer roster devono restare nella stessa regola per evitare il retrigger asincrono post team-switch",
    )
    roster_hud = roster_hud_rules[0] if roster_hud_rules else None
    if classifier and roster_hud:
        checks.require(
            classifier.start == roster_hud.start,
            "classifier e renderer roster devono restare nella stessa regola per evitare il retrigger asincrono post team-switch",
        )
    if roster_hud:
        roster_conditions = rule_block(roster_hud, "conditions") or ""
        for token in (
            "Has Spawned(Event Player) == True;",
            "Event Player.LastTeam == Team Of(Event Player);",
            "Event Player.PlayerListUpdatePending == False;",
        ):
            checks.require(token in roster_conditions, f"renderer roster senza guardia stabile: {token}")
        checks.require(
            "Is Alive(Event Player) == True;" not in roster_conditions,
            "renderer roster non deve attendere Is Alive e bloccare il lifecycle globale",
        )
        checks.require("Server Load < 150" not in roster_conditions,
                       "renderer roster non deve dipendere dal carico server")
        ready_order = tuple(
            roster_hud.body.find(token)
            for token in (
                "Event Player.PlayerListHud = Last Text ID;",
                "Global.PlayerListHudIds[Index Of Array Value(Global.HumanPlayers, Event Player)] = Event Player.PlayerListHud;",
                "Event Player.PlayerHudCreated = True;",
            )
        )
        checks.require(
            all(position >= 0 for position in ready_order)
            and ready_order == tuple(sorted(ready_order)),
            "renderer roster deve dichiararsi pronto dopo la registrazione del singolo handle",
        )

    cleanup_workers = [rule for rule in rules
                       if event_type(rule) == "Ongoing - Each Player"
                       and "Call Subroutine(CleanupPlayer);" in mask_strings(rule.body)]
    checks.require(len(cleanup_workers) == 1,
                   "cleanup team-switch deve avere un solo worker Each Player serializzato")

    setup_worker = next((
        rule for rule in rules
        if event_type(rule) == "Ongoing - Each Player"
        and "Call Subroutine(PreparePlayer);" in rule.body
        and "Event Player.TeamCycleDeadline" in rule.body
    ), None)
    checks.require(setup_worker is not None, "worker setup iniziale accodato dal globale assente")
    if setup_worker:
        conditions = rule_block(setup_worker, "conditions") or ""
        for token in SETUP_WORKER_CONDITIONS:
            checks.require(token in conditions, f"worker setup iniziale senza guardia: {token}")
        checks.require("Server Load < 150" not in conditions,
                       "worker setup iniziale non deve dipendere dal carico server")
        checks.require("Call Subroutine(QuiescePlayer);" in setup_worker.body,
                       "setup iniziale deve quietare la nuova entità")
        checks.require("If(Array Contains(Global.HumanPlayers, Event Player));" in setup_worker.body,
                       "worker setup iniziale deve separare il path team-switch dal join iniziale")
        checks.require("Call Subroutine(CleanupPlayer);" in setup_worker.body,
                       "worker setup iniziale deve fare cleanup solo dopo stabilizzazione")
        checks.require("Call Subroutine(PreparePlayer);" in setup_worker.body,
                       "setup iniziale non chiama PreparePlayer")
        checks.require("Disable Game Mode HUD(Event Player);" not in setup_worker.body,
                       "worker setup iniziale non deve toccare HUD nativo prima di PreparePlayer")
        checks.require("Disable Game Mode In-World UI(Event Player);" not in setup_worker.body,
                       "worker setup iniziale non deve toccare objective marker prima di PreparePlayer")
        order = tuple(
            setup_worker.body.find(token)
            for token in (
                "Call Subroutine(QuiescePlayer);",
                "If(Array Contains(Global.HumanPlayers, Event Player));",
                "Call Subroutine(CleanupPlayer);",
                "Call Subroutine(PreparePlayer);",
            )
        )
        checks.require(all(position >= 0 for position in order) and order == tuple(sorted(order)),
                       "worker setup iniziale deve seguire ordine tenangkan -> cleanup opzionale -> siapkan")
        checks.require(len(cleanup_workers) == 1 and cleanup_workers[0] == setup_worker,
                       "cleanup team-switch deve vivere solo nel worker setup serializzato")
        stage_waits = wait_calls(setup_worker.body)
        checks.require(len(stage_waits) == 2
                       and all(call.args == ("0.050", "Abort When False") for call in stage_waits),
                       "worker setup iniziale: soltanto due Wait 0.050 Abort When False tra le fasi atomiche")
        for call in stage_waits:
            checks.require(not conditional_branches_containing(setup_worker.body, call.start),
                           "worker setup iniziale: i Wait devono separare le fasi anche al join iniziale")
        stage_tokens = tuple(re.sub(r"\s+", "", token.strip())
                             for token in mask_strings(rule_block(setup_worker, "actions") or "").split(";")
                             if token.strip())
        expected_stage_tokens = (
            "Call Subroutine(QuiescePlayer)", "Wait(0.050, Abort When False)",
            *SETUP_WORKER_WAKE_GUARDS,
            "If(Array Contains(Global.HumanPlayers, Event Player))",
            "Call Subroutine(CleanupPlayer)", "End", "Wait(0.050, Abort When False)",
            *SETUP_WORKER_WAKE_GUARDS,
            "Call Subroutine(PreparePlayer)",
        )
        checks.equal(stage_tokens, tuple(re.sub(r"\s+", "", token) for token in expected_stage_tokens),
                     "worker setup iniziale: Tenangkan -> Wait/guardie complete -> Bersihkan -> Wait/guardie complete -> Siapkan")

    scheduler = next((rule for rule in rules if event_type(rule) == "Ongoing - Global" and action_loop_count(rule.body) == 1), None)
    checks.require(scheduler is not None, "scheduler globale lifecycle assente")
    if scheduler:
        for token in (
            "Global.TeamCyclePlayer != Null",
            "Entity Exists(Global.TeamCyclePlayer) == False",
            "Call Subroutine(ProcessPlayerFastState);",
            "Call Subroutine(ProcessPlayerLuck);",
            "If(Global.SchedulerStep % 20 == (Global.ActivePlayer.IsHuman == True ? Global.ActivePlayer.HudSlot : Slot Of(Global.ActivePlayer)) % 20);",
            "Global.PlayerListSnapshot = All Players(All Teams);",
            "Count Of(Global.PlayerListSnapshot)",
            "Global.ActivePlayer = Global.PlayerListSnapshot[Global.SchedulerPlayerIndex];",
        ):
            checks.require(token in scheduler.body, f"scheduler lifecycle iniziale incompleto: {token}")
        checks.require("Or(Entity Exists(Global.TeamCyclePlayer) == False, Has Spawned(Global.TeamCyclePlayer) == False)" in mask_strings(scheduler.body),
                       "scheduler lifecycle deve rilasciare la prenotazione di un player non spawned")
        for call in iter_calls(scheduler.body, "Call Subroutine"):
            if call.args and call.args[0].strip() in SCHEDULER_SUBROUTINES:
                branches = conditional_branches_containing(scheduler.body, call.start)
                checks.require(all("TeamCyclePlayer" not in branch.splitlines()[0] for branch in branches),
                               "scheduler non deve sospendere gli altri player durante una registrazione")

    cycle = rule_by_subroutine(rules, "ProcessPlayerCycle")
    checks.require(cycle is not None, "ProcessPlayerCycle assente")
    if cycle:
        checks.require("Global.ActivePlayer.PlayerHudCreated == True" in cycle.body,
                       "rilascio stabile lock umano richiede PlayerHudCreated == True")
        bot_cycle = rule_by_subroutine(rules, "ProcessPlayerBot")
        checks.require(bot_cycle is not None and all(token in bot_cycle.body for token in (
            "Global.ActivePlayer.IsAutomaticBot == True", "Global.ActivePlayer.IsClassified == True",
            "Global.ActivePlayer.BotLocked == True", "Global.ActivePlayer.TeamChangeProcessed = False;",
            "Global.ActivePlayer.PlayerCycleActive = False;", "Global.TeamCyclePlayer = Null;")),
            "registrazione bot IsAutomaticBot/IsClassified/BotLocked incompleta")
        for pattern, label in (
            (r"Global\.ActivePlayer\.TeamChangeProcessed\s*==\s*True", "TeamChangeProcessed == True"),
            (r"Global\.ActivePlayer\.TeamChangeProcessed\s*=\s*False;", "rilascio TeamChangeProcessed"),
            (r"Global\.TeamCyclePlayer\s*=\s*Null;", "rilascio lock globale"),
        ):
            checks.require(re.search(pattern, cycle.body, re.DOTALL) is not None,
                           f"rilascio setup iniziale incompleto: {label}")
        hero_swap_pattern = re.compile(
            r"Global\.ActivePlayer\.IsHuman\s*==\s*True.*?"
            r"Has Spawned\(Global\.ActivePlayer\)\s*==\s*True.*?"
            r"Hero Of\(Global\.ActivePlayer\)\s*!=\s*Global\.ActivePlayer\.LastHero.*?"
            r"Global\.ActivePlayer\.LastHero\s*=\s*Hero Of\(Global\.ActivePlayer\);.*?"
            r"Global\.ActivePlayer\.LuckActive\s*==\s*True.*?"
            r"Call Subroutine\(RestoreActivePlayerLuck\);",
            re.DOTALL,
        )
        checks.require(hero_swap_pattern.search(cycle.body) is not None,
                       "hero swap umano non pulisce Try Your Luck nello scheduler globale")


def validate_target_label_budget(checks: Checks, rules: list[Rule]) -> None:
    """Keep target invalidation immediate while bounding shared IWT allocation."""
    clock = "Event Player.NextTargetTextTime"

    def packed(value: str) -> str:
        return re.sub(r"\s+", "", value)

    def invalid(identity: str) -> str:
        return (
            f"Or(Entity Exists({identity}) == False, Or(Has Spawned({identity}) == False, "
            f"Or(Is Alive({identity}) == False, And(And(Is Dummy Bot({identity}) == False, "
            f"Player Variable({identity}, IsAutomaticBot) == False), Or(Player Variable({identity}, IsHuman) == False, "
            f"Or(Player Variable({identity}, InspectionPrivacyActive) == True, "
            f"Player Variable({identity}, PlayerListUpdatePending) == True))))))"
        )

    for prefix, target, candidate, handle, identity in (
        ("13", "InspectionTarget", "InspectionTargetCandidate", "InspectionText", "InspectionTarget"),
        ("19d", "TravelTextTarget", "TravelTargetCandidate", "TravelText", "TravelTargetCandidate"),
    ):
        rule = next((rule for rule in rules if rule.name.startswith(prefix + " -")), None)
        checks.require(rule is not None, f"budget targhette: renderer {prefix} assente")
        if rule is None:
            continue
        actions = rule_block(rule, "actions")
        condition = (
            f"Or(Event Player.{target} != Event Player.{candidate}, "
            f"Or(And(Event Player.{handle} != Null, {invalid('Event Player.' + target)}), "
            f"And(Event Player.{handle} == Null, And(Event Player.{candidate} != Null, "
            f"Total Time Elapsed >= {clock})))) == True;"
        )
        checks.require(packed(condition) in packed(rule_block(rule, "conditions")),
                       f"budget targhette {prefix}: invalidazione immediata o risveglio alla scadenza assente")
        order = (
            f"Destroy In-World Text(Event Player.{handle});",
            f"Event Player.{handle} = Null;",
            f"Abort If(Total Time Elapsed < {clock});",
            f"{clock} = Total Time Elapsed + 0.250;",
            "Create In-World Text(",
        )
        positions = [actions.find(token) for token in order]
        checks.require(all(index >= 0 for index in positions) and positions == sorted(positions),
                       f"budget targhette {prefix}: distruzione prima del limite condiviso di 0.250 s")
        checks.require(not list(iter_calls(actions, "Wait")) and "Loop" not in mask_strings(actions),
                       f"budget targhette {prefix}: attese o loop aggiuntivi vietati")
        validation = rule_by_subroutine(rules, "RefreshInspectionTarget") if prefix == "13" else rule
        checks.require(validation is not None and packed(invalid("Event Player." + candidate)) in packed(validation.body),
                       f"budget targhette {prefix}: validazione target prima della creazione assente")
        if validation:
            for field in (target, candidate):
                checks.require(f"Event Player.{field} = Null;" in validation.body,
                               f"budget targhette {prefix}: invalidazione non azzera {field}")
        creates = list(iter_calls(actions, "Create In-World Text"))
        if len(creates) == 1 and len(creates[0].args) > 1:
            text = creates[0].args[1]
            for function in ("Is Duplicating", "Hero Being Duplicated", "Hero Of", "Health"):
                checks.require(packed(f"{function}(Evaluate Once(Event Player.{identity}))") in packed(text),
                               f"budget targhette {prefix}: {function} deve seguire l'identità catturata")
            captures = list(iter_calls(text, "Evaluate Once"))
            outer = [call for call in captures if not any(
                other.start < call.start and other.end >= call.end for other in captures)]
            for call in reversed(outer):
                text = text[:call.start] + "captured" + text[call.end:]
            checks.require(packed("Event Player." + identity) not in packed(text),
                           f"budget targhette {prefix}: testo live legge ancora il target mutabile")

    writers = [rule for rule in rules if re.search(r"Event Player\.NextTargetTextTime\s*=", mask_strings(rule.body))]
    checks.equal({rule.name.split(" -", 1)[0] for rule in writers}, {"13", "19d", "93b2", "94"},
                 "budget targhette: soltanto renderer e setup possono scrivere la scadenza condivisa")


def validate_privacy(checks: Checks, rules: list[Rule]) -> None:
    setup = rule_by_subroutine(rules, "PreparePlayer")
    checks.require(setup is not None, "PreparePlayer assente per default privacy")
    if setup:
        checks.require("Event Player.InspectionPrivacyActive = False;" in setup.body,
                       "Privacy deve essere OFF di default per ogni umano")

    privacy_filter_tokens = (
        "Is Dummy Bot(Current Array Element) == True",
        "Player Variable(Current Array Element, IsAutomaticBot) == True",
        "Player Variable(Current Array Element, IsHuman) == True",
        "Player Variable(Current Array Element, InspectionPrivacyActive) == False",
        "Player Variable(Current Array Element, PlayerListUpdatePending) == False",
    )
    human_public_pattern_text = (
        r"And\(\s*Player Variable\(\s*Current Array Element\s*,\s*IsHuman\)\s*==\s*True\s*,\s*"
        r"And\(\s*Player Variable\(\s*Current Array Element\s*,\s*InspectionPrivacyActive\)\s*==\s*False\s*,\s*"
        r"Player Variable\(\s*Current Array Element\s*,\s*PlayerListUpdatePending\)\s*==\s*False\s*\)\s*\)"
    )
    human_public_pattern = re.compile(human_public_pattern_text, re.DOTALL)
    public_target_pattern = re.compile(
        r"Or\(\s*Is Dummy Bot\(Current Array Element\)\s*==\s*True\s*,\s*"
        r"Or\(\s*Player Variable\(\s*Current Array Element\s*,\s*IsAutomaticBot\)\s*==\s*True\s*,\s*"
        + human_public_pattern_text
        + r"\s*\)\s*\)",
        re.DOTALL,
    )
    vision_subject_pattern = re.compile(
        r"Or\(\s*Is Dummy Bot\(Event Player\)\s*==\s*True\s*,\s*"
        r"Or\(\s*Event Player\.IsAutomaticBot\s*==\s*True\s*,\s*"
        r"Event Player\.IsHuman\s*==\s*True\s*\)\s*\)",
        re.DOTALL,
    )

    def validate_fluid_iwt(rule: Rule | None, label: str, identity: str) -> None:
        if rule is None:
            return
        calls = list(iter_calls(rule.body, "Create In-World Text"))
        checks.equal(
            len(calls),
            1,
            f"IWT {label}: icona, nome e salute devono restare in un solo testo",
        )
        if len(calls) != 1:
            return
        call = calls[0]
        checks.require(
            len(call.args) >= 6,
            f"IWT {label}: Create In-World Text malformato",
        )
        if len(call.args) < 6:
            return

        text = call.args[1].strip()
        outer_texts = [
            nested
            for nested in iter_calls(text, "Custom String")
            if nested.start == 0 and nested.end == len(text)
        ]
        single_text = len(outer_texts) == 1
        if single_text:
            outer_text = outer_texts[0]
            single_text = (
                len(outer_text.args) == 4
                and parse_literal(outer_text.args[0]) == "{0} {1} | {2}"
                and "Hero Icon String(" in outer_text.args[1]
                and "DisplayName" in outer_text.args[2]
                and "Health(" in outer_text.args[3]
            )
        checks.require(
            single_text,
            f"IWT {label}: icona, nome e salute devono restare in un solo testo",
        )

        position = call.args[2].strip()
        frame_updates = list(iter_calls(position, "Update Every Frame"))
        full_frame_update = (
            len(frame_updates) == 1
            and frame_updates[0].start == 0
            and frame_updates[0].end == len(position)
            and len(frame_updates[0].args) == 1
        )
        checks.require(
            full_frame_update,
            f"IWT {label}: posizione fluida Update Every Frame",
        )
        if full_frame_update:
            dynamic_position = frame_updates[0].args[0]
            expected_position = (
                f"Eye Position(Evaluate Once({identity})) + Vector(0, 0.450, 0)"
            )
            checks.equal(
                re.sub(r"\s+", "", dynamic_position),
                re.sub(r"\s+", "", expected_position),
                f"IWT {label}: ancoraggio fluido sopra l'identità",
            )
            captures = list(iter_calls(dynamic_position, "Evaluate Once"))
            identity_capture = (
                len(captures) == 1
                and len(captures[0].args) == 1
                and re.sub(r"\s+", "", captures[0].args[0]) == re.sub(r"\s+", "", identity)
            )
            if identity_capture:
                without_capture = (
                    dynamic_position[:captures[0].start]
                    + dynamic_position[captures[0].end:]
                )
                identity_capture = re.sub(r"\s+", "", identity) not in re.sub(
                    r"\s+", "", without_capture
                )
            checks.require(
                identity_capture,
                f"IWT {label}: Evaluate Once deve catturare soltanto l'identità",
            )

        checks.equal(
            call.args[5].strip(),
            "Visible To Position String and Color",
            f"IWT {label}: reevaluation completa",
        )

    privacy_false_pattern = re.compile(
        r"Player Variable\(\s*Current Array Element\s*,\s*InspectionPrivacyActive\)\s*==\s*False",
        re.DOTALL,
    )
    pending_false_pattern = re.compile(
        r"Player Variable\(\s*Current Array Element\s*,\s*PlayerListUpdatePending\)\s*==\s*False",
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
                f"{rule.name}: ogni Privacy OFF target richiede IsHuman=True e pending roster False",
            )
            checks.equal(
                len(pending_false_pattern.findall(rule.body)),
                privacy_reads,
                f"{rule.name}: ogni target pubblico deve escludere il pending team-switch",
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
    checks.equal(privacy_read_total, 2, "numero filtri Privacy target-aware condivisi")
    checks.equal(parsed_privacy_filter_total, 2, "filtri Privacy condivisi strutturalmente analizzabili")
    camera_targets = rule_by_subroutine(rules, "RefreshCameraTargets")
    checks.require(camera_targets is not None, "RefreshCameraTargets assente per filtro Privacy")
    if camera_targets:
        checks.require("Call Subroutine(RefreshPlayerPublicTargets);" in camera_targets.body,
                       "lista target Camera non riusa la subroutine pubblica condivisa")
        checks.require("Filtered Array(Event Player.InspectionTargets, Has Spawned(Current Array Element) == True)" in camera_targets.body,
                       "lista target Camera non deriva dai target pubblici spawnati")

    cache = rule_by_subroutine(rules, "ProcessPlayerMaintenance")
    checks.require(cache is not None, "ProcessPlayerMaintenance assente per cache Camera")
    if cache:
        checks.require("Call Subroutine(RefreshActivePlayerPublicTargets);" in cache.body,
                       "cache target Camera non riusa la subroutine pubblica globale")
        checks.require("Set Player Variable(Global.ActivePlayer, CameraTargets, Global.ActivePlayer.InspectionTargets);" in cache.body,
                       "cache target Camera non copia la lista pubblica condivisa")

    inspection_refresh = rule_by_subroutine(rules, "RefreshInspectionTarget")
    checks.require(inspection_refresh is not None, "RefreshInspectionTarget assente per filtro Privacy")
    if inspection_refresh:
        checks.require("Event Player.InspectionTargetCandidate" in inspection_refresh.body,
                       "inspection non consuma il candidato cache del scheduler")
        checks.require("Filtered Array(" not in inspection_refresh.body and "Sorted Array(" not in inspection_refresh.body,
                       "inspection refresh reintroduce una scansione pesante fuori dallo scheduler")
        checks.require("Event Player.LuckPrivacyActive == True" not in inspection_refresh.body,
                       "inspection reintroduce il bypass Privacy tramite Vision")

    inspection_live = next(
        (
            rule for rule in rules
            if event_type(rule) == "Ongoing - Each Player"
            and "Event Player.InspectionTarget != Event Player.InspectionTargetCandidate" in rule.body
        ),
        None,
    )
    checks.require(inspection_live is not None, "aggiornamento live inspection cache assente")
    if inspection_live:
        checks.require("Sorted Array(Filtered Array(" not in inspection_live.body,
                       "inspection live ricalcola ancora i target fuori dallo scheduler")
        checks.require("Event Player.LuckPrivacyActive == True" not in inspection_live.body,
                       "inspection live reintroduce il bypass Privacy tramite Vision")
        checks.require("Event Player.LuckPrivacyActive == False;" in inspection_live.body,
                       "inspection Crouch non è bloccata durante Vision")
        checks.require("Disable Nameplates(All Players(All Teams), Event Player);" in inspection_live.body,
                       "inspection non disabilita i nameplate nativi")
        checks.require("Enable Nameplates(All Players(All Teams), Event Player);" not in inspection_live.body,
                       "inspection può mostrare nameplate di umani privati")
        checks.require(
            "Evaluate Once(Array Contains(Global.HumanPlayers, Event Player.InspectionTarget) == True ? "
            "Player Variable(Event Player.InspectionTarget, DisplayName) : "
            'Custom String("{0}", Is Duplicating(Event Player.InspectionTarget) ? Hero Being Duplicated(Event Player.InspectionTarget) : Hero Of(Event Player.InspectionTarget)))' in inspection_live.body,
            "inspection deve usare Evaluate Once sul nome target",
        )
        checks.require(
            "Evaluate Once(Array Contains(Global.HumanPlayers, Event Player.InspectionTarget) == True ? "
            "Player Variable(Event Player.InspectionTarget, NameColor)" in inspection_live.body,
            "inspection deve usare Evaluate Once sul colore target",
        )
        checks.require(
            "Player Variable(Event Player.InspectionTarget, IsHuman) == True ? "
            "Player Variable(Event Player.InspectionTarget, DisplayName)" not in inspection_live.body,
            "inspection non deve usare IsHuman come guardia DisplayName",
        )
        checks.require(
            'Custom String("{0}", Event Player.InspectionTarget))' not in inspection_live.body,
            "inspection non deve mostrare identity token grezzo ai dummy",
        )
    validate_fluid_iwt(inspection_live, "inspection", "Event Player.InspectionTarget")

    cycle_targets = rule_by_subroutine(rules, "ProcessPlayerCycle")
    checks.require(cycle_targets is not None, "scheduler 10 Hz assente per target cache")
    if cycle_targets:
        checks.require("Call Subroutine(RefreshActivePlayerPublicTargets);" in cycle_targets.body,
                       "scheduler target non riusa il filtro pubblico condiviso")
        checks.require("Set Player Variable(Global.ActivePlayer, InspectionTargetCandidate," in cycle_targets.body,
                       "scheduler 10 Hz non aggiorna InspectionTargetCandidate")
        checks.require("Set Player Variable(Global.ActivePlayer, TravelTargetCandidate," in cycle_targets.body,
                       "scheduler 10 Hz non aggiorna TravelTargetCandidate")
        checks.require("Angle Between Vectors(Facing Direction Of(Global.ActivePlayer)" in cycle_targets.body,
                       "scheduler target non conserva l'ordinamento angolare originale")

    teleport_refresh = rule_by_subroutine(rules, "RefreshTravelTarget")
    checks.require(teleport_refresh is not None, "RefreshTravelTarget assente per filtro Privacy")
    if teleport_refresh:
        checks.require("Call Subroutine(RefreshPlayerPublicTargets);" in teleport_refresh.body,
                       "teleport discreto non riusa la subroutine pubblica condivisa")
        checks.require("Event Player.TravelTargets = Event Player.InspectionTargets;" in teleport_refresh.body,
                       "teleport discreto non usa la lista pubblica condivisa")

    heavy_live_target_rules = [
        rule for rule in rules
        if event_type(rule) == "Ongoing - Each Player"
        and "Sorted Array(Filtered Array(All Players(All Teams)" in rule.body
        and ("InspectionTarget" in rule.body or "TravelTargetCandidate" in rule.body)
    ]
    checks.equal(len(heavy_live_target_rules), 0,
                 "inspection/teleport non devono fare scansioni target pesanti nelle regole live")

    teleport_entry = next(
        (
            rule for rule in rules
            if event_type(rule) == "Ongoing - Each Player"
            and "Event Player.CrouchTravelActive = True;" in rule.body
            and "Button(Crouch)" in rule.body
        ),
        None,
    )
    checks.require(teleport_entry is not None, "apertura Teleport Crouch assente")
    if teleport_entry:
        checks.require("Event Player.LuckPrivacyActive == False;" in teleport_entry.body,
                       "Teleport Crouch non è bloccato durante Vision")

    teleport_text = next(
        (
            rule for rule in rules
            if "Event Player.TravelTextTarget != Event Player.TravelTargetCandidate" in rule.body
            and "Create In-World Text(Event Player" in rule.body
        ),
        None,
    )
    checks.require(teleport_text is not None, "testo live teleport assente")
    if teleport_text:
        checks.require("Disable Nameplates(All Players(All Teams), Event Player);" in teleport_text.body,
                       "teleport non disabilita i nameplate nativi")
        checks.require("Enable Nameplates(All Players(All Teams), Event Player);" not in teleport_text.body,
                       "teleport può mostrare nameplate di umani privati")
        checks.require(
            "Evaluate Once(Array Contains(Global.HumanPlayers, Event Player.TravelTargetCandidate) == True ? "
            "Player Variable(Event Player.TravelTargetCandidate, DisplayName) : "
            'Custom String("{0}", Is Duplicating(Event Player.TravelTargetCandidate) ? Hero Being Duplicated(Event Player.TravelTargetCandidate) : Hero Of(Event Player.TravelTargetCandidate)))' in teleport_text.body,
            "teleport deve usare Evaluate Once sul nome target",
        )
        checks.require(
            "Evaluate Once(Array Contains(Global.HumanPlayers, Event Player.TravelTargetCandidate) == True ? "
            "Player Variable(Event Player.TravelTargetCandidate, NameColor)" in teleport_text.body,
            "teleport deve usare Evaluate Once sul colore target",
        )
        checks.require(
            "Player Variable(Event Player.TravelTargetCandidate, IsHuman) == True ? "
            "Player Variable(Event Player.TravelTargetCandidate, DisplayName)" not in teleport_text.body,
            "teleport non deve usare IsHuman come guardia DisplayName",
        )
        checks.require(
            'Custom String("{0}", Event Player.TravelTargetCandidate))' not in teleport_text.body,
            "teleport non deve mostrare identity token grezzo ai dummy",
        )
    validate_fluid_iwt(teleport_text, "Teleport", "Event Player.TravelTargetCandidate")
    validate_target_label_budget(checks, rules)

    vision_names = next(
        (
            rule for rule in rules
            if "Event Player.LuckVisionText = Last Text ID;" in rule.body
            and "Create In-World Text(" in rule.body
        ),
        None,
    )
    checks.require(vision_names is not None, "IWT nomi Vision assente")
    vision_contract_text = "\n".join(rule.body for rule in rules)
    checks.require('VISION: ALL PLAYER/BOT NAMES' in vision_contract_text,
                   "testo Vision inglese non dichiara tutti i nomi")
    if vision_names:
        checks.require(
            vision_subject_pattern.search(vision_names.body) is not None,
            "Vision deve coprire bot/dummy e tutti gli umani anche con Privacy ON",
        )
        vision_conditions = rule_block(vision_names, "conditions") or ""
        checks.require(
            "Event Player.InspectionPrivacyActive" not in vision_conditions,
            "Vision non deve filtrare gli umani che hanno Privacy ON",
        )
        vision_calls = list(iter_calls(vision_names.body, "Create In-World Text"))
        checks.equal(len(vision_calls), 1, "Vision deve creare un solo IWT per soggetto")
        if len(vision_calls) == 1:
            vision_call = vision_calls[0]
            checks.require(len(vision_call.args) >= 6, "IWT Vision malformato")
            if len(vision_call.args) >= 6:
                compact_vision = lambda expression: re.sub(r"\s+", "", expression)
                expected_recipient = compact_vision(
                    "Filtered Array(Global.LuckVisionViewers, And(Current Array Element != Event Player, "
                    "And(Entity Exists(Current Array Element), And(Player Variable(Current Array Element, IsHuman) == True, "
                    "Player Variable(Current Array Element, LuckPrivacyActive) == True))))"
                )
                checks.equal(
                    compact_vision(vision_call.args[0]),
                    expected_recipient,
                    "destinatari Vision devono essere gli altri umani con Vision attiva",
                )
                vision_text = vision_call.args[1]
                for token, label in (
                    ("Hero Icon String(", "icona eroe"),
                    ("Hero Being Duplicated(Event Player)", "icona forma duplicata"),
                    (
                        'Event Player.IsHuman == True ? Event Player.DisplayName : Custom String("{0}", Event Player)',
                        "nome roster stabile per gli umani e nome live per bot/dummy",
                    ),
                    ("Round To Integer(Health(Event Player), Down)", "salute live"),
                ):
                    checks.require(token in vision_text, f"Vision non mostra {label}")
                outer_text = next(
                    (
                        call for call in iter_calls(vision_text, "Custom String")
                        if call.start == 0 and call.end == len(vision_text)
                    ),
                    None,
                )
                checks.require(outer_text is not None, "testo Vision deve avere un solo wrapper Custom String")
                if outer_text:
                    expected_values = (
                        "HeroIconString(IsDuplicating(EventPlayer)?HeroBeingDuplicated(EventPlayer):HeroOf(EventPlayer))",
                        'EventPlayer.IsHuman==True?EventPlayer.DisplayName:CustomString("{0}",EventPlayer)',
                        "RoundToInteger(Health(EventPlayer),Down)",
                    )
                    checks.require(
                        len(outer_text.args) == 4
                        and parse_literal(outer_text.args[0]) == "{0} {1} | {2}"
                        and tuple(compact_vision(value) for value in outer_text.args[1:]) == expected_values,
                        "Vision deve mantenere ordine icona, nome e salute",
                    )
                checks.equal(vision_call.args[5].strip(), "Visible To Position String and Color",
                             "Vision deve rivalutare destinatari, posizione, testo e colore")
    validate_fluid_iwt(vision_names, "Vision", "Event Player")

    vision_cleanup = next(
        (
            rule for rule in rules
            if "Destroy In-World Text(Event Player.LuckVisionText);" in rule.body
            and "Event Player.LuckVisionText = Null;" in rule.body
            and event_type(rule) == "Ongoing - Each Player"
        ),
        None,
    )
    checks.require(vision_cleanup is not None, "cleanup IWT Vision assente")
    if vision_cleanup:
        cleanup_conditions = rule_block(vision_cleanup, "conditions") or ""
        checks.require(
            "Event Player.InspectionPrivacyActive" not in cleanup_conditions,
            "cleanup Vision non deve rimuovere un umano che attiva Privacy",
        )
        checks.require(
            "Is Alive(Event Player) == False" in cleanup_conditions
            and "LuckPrivacyActive" in cleanup_conditions,
            "cleanup Vision deve restare legato a morte soggetto o assenza osservatori Vision",
        )

    cycle = rule_by_subroutine(rules, "ProcessPlayerCycle")
    checks.require(cycle is not None, "ProcessPlayerCycle assente per stop osservatore Privacy")
    if cycle:
        checks.require("Global.ActivePlayer.LuckPrivacyActive == True" in cycle.body,
                       "cleanup inspection non reagisce all'avvio di Vision")
        privacy_guard = re.search(
            r"Global\.ActivePlayer\.CameraMode\s*==\s*2.*?"
            r"Global\.ActivePlayer\.CameraTarget\.IsHuman\s*==\s*True.*?"
            r"Global\.ActivePlayer\.CameraTarget\.InspectionPrivacyActive\s*==\s*True.*?"
            r"Stop Camera\(Global\.ActivePlayer\);",
            cycle.body,
            re.DOTALL,
        )
        checks.require(privacy_guard is not None,
                       "osservatore attivo non viene fermato quando il target umano abilita Privacy")
        mode_reset = (
            "Set Player Variable(Global.ActivePlayer, CameraMode, 0);" in cycle.body
            or "Global.ActivePlayer.CameraMode = 0;" in cycle.body
        )
        target_reset = (
            "Set Player Variable(Global.ActivePlayer, CameraTarget, Null);" in cycle.body
            or "Global.ActivePlayer.CameraTarget = Null;" in cycle.body
        )
        checks.require(mode_reset and target_reset,
                       "stop osservatore Privacy non ripristina CameraMode e CameraTarget")

    teleport_cleanup = next(
        (
            rule for rule in rules
            if event_type(rule) == "Ongoing - Each Player"
            and "Event Player.CrouchTravelActive == True;" in rule.body
            and "Event Player.CrouchTravelActive = False;" in rule.body
            and "Destroy HUD Text(Event Player.MenuHud);" in rule.body
        ),
        None,
    )
    checks.require(teleport_cleanup is not None, "cleanup Teleport Crouch assente")
    if teleport_cleanup:
        checks.require("Event Player.LuckPrivacyActive == True" in teleport_cleanup.body,
                       "cleanup Teleport Crouch non reagisce all'avvio di Vision")


def validate_dummy_slot_management(
    checks: Checks,
    rules: list[Rule],
    compact,
) -> None:
    managers = [rule for rule in rules if subroutine_target(rule) == "MaintainDummyBots"]
    checks.equal(len(managers), 1, "numero manutenzioni slot dummy")
    if managers:
        manager = managers[0]
        checks.equal(compact(event_block(manager)), compact("Subroutine; MaintainDummyBots;"),
                     "slot dummy: evento subroutine esatto")
        expected = """
            Abort If(Global.IsReady == False);
            Abort If(Is Game In Progress == False);
            Abort If(Global.TeamCyclePlayer != Null);
        """
        for team in (1, 2):
            expected += f"""
                If(Number Of Players(Team {team}) >= Number Of Slots(Team {team}));
                    If(Count Of(Filtered Array(All Players(Team {team}), Is Dummy Bot(Current Array Element) == True)) > 0);
                        Global.ActiveDummyBotTeam = Team {team};
                        Global.Team{team}DummyBotRetryTime = Total Time Elapsed + 1;
                        Call Subroutine(RemoveTeamDummyBot);
                    End;
                Else;
                    If(And(Current Game Mode == Game Mode(Skirmish), And(Number Of Players(Team {team}) < Number Of Slots(Team {team}) - 1, And(Count Of(Spawn Points(Team {team})) > 0, And(Count Of(Filtered Array(All Players(Team {team}), Is Dummy Bot(Current Array Element) == True)) == 0, Total Time Elapsed >= Global.Team{team}DummyBotRetryTime)))));
                        Global.ActiveDummyBotTeam = Team {team};
                        Global.Team{team}DummyBotRetryTime = Total Time Elapsed + 1;
                        Call Subroutine(CreateTeamDummyBot);
                    End;
                End;
            """
            initializer = next((r for r in rules if r.name.startswith("00 -")), None)
            checks.require(initializer is not None and f"Global.Team{team}DummyBotRetryTime = 0;" in initializer.body,
                           f"cooldown dummy Team {team}: inizializzazione assente")
        checks.equal(compact(mask_strings(rule_block(manager, "actions") or "")), compact(expected),
                     "slot dummy: condizioni, cooldown e azioni esatte")
        for routine in ("CreateTeamDummyBot", "RemoveTeamDummyBot"):
            owners = [(rule, call) for rule in rules for call in iter_calls(rule.body, "Call Subroutine")
                      if call.args == (routine,)]
            checks.require(len(owners) == 2 and all(rule == manager for rule, _ in owners),
                           f"slot dummy: {routine} deve essere chiamata solo dalla manutenzione 1 Hz")

    create_dummy = rule_by_subroutine(rules, "CreateTeamDummyBot")
    checks.require(create_dummy is not None, "subroutine CreateTeamDummyBot assente")
    if create_dummy:
        create_actions = rule_block(create_dummy, "actions")
        checks.require(create_actions is not None, "CreateTeamDummyBot: blocco actions assente")
        if create_actions is not None:
            expected_create_dummy = (
                "Create Dummy Bot(All Heroes, Global.ActiveDummyBotTeam, -1, "
                "Position Of(First Of(Spawn Points(Global.ActiveDummyBotTeam))), Vector(0, 0, 1));"
            )
            checks.equal(
                compact(create_actions),
                compact(expected_create_dummy),
                "CreateTeamDummyBot: azione esatta senza abort",
            )

    release_dummy = rule_by_subroutine(rules, "RemoveTeamDummyBot")
    checks.require(release_dummy is not None, "subroutine RemoveTeamDummyBot assente")
    if release_dummy:
        release_actions = rule_block(release_dummy, "actions")
        checks.require(release_actions is not None, "RemoveTeamDummyBot: blocco actions assente")
        for token in (
            "Abort If(Count Of(Filtered Array(All Players(Global.ActiveDummyBotTeam), Is Dummy Bot(Current Array Element) == True)) == 0);",
            "Destroy In-World Text(Player Variable(",
            "Stop Facing(First Of(Filtered Array(",
            "Stop Throttle In Direction(First Of(Filtered Array(",
            "Destroy Dummy Bot(Global.ActiveDummyBotTeam, Slot Of(",
        ):
            checks.require(token in release_dummy.body, f"RemoveTeamDummyBot incompleta: {token}")
        facing_stop = release_dummy.body.find("Stop Facing(First Of(Filtered Array(")
        throttle_stop = release_dummy.body.find("Stop Throttle In Direction(First Of(Filtered Array(")
        destroy_dummy = release_dummy.body.find("Destroy Dummy Bot(Global.ActiveDummyBotTeam, Slot Of(")
        checks.require(0 <= facing_stop < throttle_stop < destroy_dummy,
                       "RemoveTeamDummyBot: facing/throttle devono fermarsi prima della distruzione")
        if release_actions is not None:
            dummy = "First Of(Filtered Array(All Players(Global.ActiveDummyBotTeam), Is Dummy Bot(Current Array Element) == True))"
            expected_release_dummy = f"""
                Abort If(Count Of(Filtered Array(All Players(Global.ActiveDummyBotTeam), Is Dummy Bot(Current Array Element) == True)) == 0);
                If(Player Variable({dummy}, LuckVisionText) != Null);
                    If(Index Of Array Value(Global.TemporaryTextOwners, {dummy}) >= 0);
                    If(Global.TemporaryVisionTextIds[Index Of Array Value(Global.TemporaryTextOwners, {dummy})] == Player Variable({dummy}, LuckVisionText));
                    Destroy In-World Text(Player Variable({dummy}, LuckVisionText));
                    Global.TemporaryVisionTextIds[Index Of Array Value(Global.TemporaryTextOwners, {dummy})] = 0;
                    End;
                    End;
                End;
                Stop Facing({dummy});
                Stop Throttle In Direction({dummy});
                Destroy Dummy Bot(Global.ActiveDummyBotTeam, Slot Of({dummy}));
            """
            checks.equal(
                compact(release_actions),
                compact(expected_release_dummy),
                "RemoveTeamDummyBot: cleanup atomico esatto senza abort",
            )


def validate_bot_isolation(checks: Checks, rules: list[Rule]) -> None:
    def compact(expression: str) -> str:
        return re.sub(r"\s+", "", expression)

    def require_human_guards(rule: Rule | None, label: str, *, triple: bool) -> None:
        checks.require(rule is not None, f"entrypoint umano assente: {label}")
        if not rule:
            return
        create_hud_pos = rule.body.find("Create HUD Text(")

        human_guard = "Event Player.IsHuman == True;" in rule.body
        if not human_guard and label == "HUD player":
            human_assign = rule.body.find("Event Player.IsHuman = True;")
            human_guard = human_assign >= 0 and (create_hud_pos < 0 or human_assign < create_hud_pos)
        checks.require(human_guard, f"{label} non isola bot/dummy: Event Player.IsHuman == True;")

        if triple:
            bot_guard = "Event Player.IsAutomaticBot == False;" in rule.body
            if not bot_guard and label == "HUD player":
                bot_assign = rule.body.find("Event Player.IsAutomaticBot = False;")
                bot_guard = bot_assign >= 0 and (create_hud_pos < 0 or bot_assign < create_hud_pos)
            checks.require(bot_guard, f"{label} non isola bot/dummy: Event Player.IsAutomaticBot == False;")

            checks.require(
                "Is Dummy Bot(Event Player) == False;" in rule.body,
                f"{label} non isola bot/dummy: Is Dummy Bot(Event Player) == False;",
            )

    classifier = next(
        (
            rule for rule in rules
            if event_type(rule) == "Ongoing - Each Player"
            and "Start Forcing Dummy Bot Name(Event Player" in rule.body
            and "Append To Array(Global.HumanPlayers, Event Player)" in rule.body
        ),
        None,
    )
    bot_abort = None
    checks.require(classifier is not None, "classificatore dedicato umano/iBot assente")
    if classifier:
        checks.require("Is Dummy Bot(Event Player) == False;" in classifier.body,
                       "classificatore umano/iBot non esclude i dummy nativi")
        bot_abort = re.search(
            r"If\(Event Player\.IsAutomaticBot\s*==\s*True\);.*?"
            r"Call Subroutine\(LockBot\);.*?Abort;.*?End;",
            classifier.body,
            re.DOTALL,
        )
        roster_append = classifier.body.find("Append To Array(Global.HumanPlayers, Event Player)")
        checks.require(
            bot_abort is not None and roster_append >= 0 and bot_abort.end() < roster_append,
            "iBot può raggiungere il roster umano prima dell'Abort dedicato",
        )

    human_writers = [
        rule for rule in rules
        if re.search(r"Event Player\.IsHuman\s*=\s*True;", mask_strings(rule.body)) is not None
        or "Set Player Variable(Event Player, IsHuman, True);" in rule.body
    ]
    checks.equal(len(human_writers), 1, "numero writer di IsHuman=True")
    if human_writers and classifier:
        checks.equal(human_writers[0].start, classifier.start,
                     "IsHuman=True scritto fuori dal classificatore umano/iBot")
        human_write = max(
            classifier.body.find("Event Player.IsHuman = True;"),
            classifier.body.find("Set Player Variable(Event Player, IsHuman, True);"),
        )
        checks.require(
            bot_abort is not None and human_write > bot_abort.end(),
            "IsHuman=True viene scritto prima dell'Abort iBot",
        )

    roster_writers = [
        rule for rule in rules
        if "Append To Array(Global.HumanPlayers, Event Player)" in rule.body
    ]
    checks.equal(len(roster_writers), 1, "numero regole che inseriscono nel roster umano")
    if roster_writers and classifier:
        checks.equal(roster_writers[0].start, classifier.start,
                     "roster umano scritto fuori dal classificatore dedicato")

    lifecycle_dispatcher = rule_by_subroutine(rules, "ProcessPlayerFastState")
    if lifecycle_dispatcher:
        checks.require("Is Dummy Bot(Global.ActivePlayer) == False" in lifecycle_dispatcher.body,
                       "dispatcher lifecycle globale non esclude dummy nativi")
        checks.require(lifecycle_dispatcher.body.count("Global.ActivePlayer.IsAutomaticBot == False") >= 2,
                       "dispatcher lifecycle globale può riattivare il lifecycle di un iBot")
    left = rules_with_event(rules, "Player Left Match")
    if left:
        for token in (
            "Is Dummy Bot(Event Player) == False;",
            "Event Player.IsAutomaticBot == True",
            "Event Player.IsHuman == True",
            "Array Contains(Global.HumanPlayers, Event Player)",
        ):
            checks.require(token in left[0].body,
                           f"leave non isola correttamente dummy/iBot/umani: {token}")

    setup = rule_by_subroutine(rules, "PreparePlayer")
    if setup:
        checks.require("Abort If(Is Dummy Bot(Event Player));" in setup.body,
                       "PreparePlayer non interrompe immediatamente i dummy nativi")

    entrypoints = (
        (next((rule for rule in rules if event_type(rule) == "Ongoing - Each Player" and "PlayerHudCreated" in rule.body and "Create HUD Text(" in rule.body), None), "HUD player", True),
        (next((rule for rule in rules if event_type(rule) == "Ongoing - Each Player" and "Button(Melee)" in rule.body and "Wait(0.500, Abort When False)" in rule.body and "Call Subroutine(DrawMenu);" in rule.body), None), "toggle menu", True),
        (next((rule for rule in rules if event_type(rule) == "Ongoing - Each Player" and "MenuCommand" in rule.body and all(f"Button({button})" in rule.body for button in MENU_ACTION_BUTTONS)), None), "dispatcher menu", False),
        (next((rule for rule in rules if event_type(rule) == "Ongoing - Each Player" and "Button(Interact)" in rule.body and "Wait(0.500, Abort When False)" in rule.body and "CameraMode" in rule.body), None), "toggle Camera", True),
        (next((rule for rule in rules if event_type(rule) == "Ongoing - Each Player" and "InspectionActive = True;" in rule.body and "Button(Crouch)" in rule.body), None), "inspection Crouch", False),
        (next((rule for rule in rules if event_type(rule) == "Ongoing - Each Player" and "CrouchTravelActive = True;" in rule.body and "Button(Crouch)" in rule.body), None), "teleport Crouch", True),
        (next((rule for rule in rules if event_type(rule) == "Player Died" and "Hero(Anran)" in rule.body and "Set Ultimate Charge(Event Player, 100);" in rule.body), None), "passiva Anran", True),
        (next((rule for rule in rules if event_type(rule) == "Ongoing - Each Player" and "Resurrect(Event Player);" in rule.body and "Button(Jump)" in rule.body), None), "Resurrect Jump", True),
    )
    for rule, label, triple in entrypoints:
        require_human_guards(rule, label, triple=triple)

    player_hud_calls = list(iter_calls("\n".join(rule.body for rule in rules), "Create HUD Text"))
    for call in player_hud_calls:
        if call.args:
            checks.require(
                call.args[0].strip() in {"Global.HumanPlayers", "Event Player"},
                f"Create HUD Text visibile a bot/dummy: {call.args[0].strip()}",
            )

    bot_rule = next(
        (
            rule for rule in rules
            if event_type(rule) == "Ongoing - Each Player"
            and "Or(Is Dummy Bot(Event Player), Event Player.IsAutomaticBot) == True;" in rule.body
            and "Call Subroutine(LockBot);" in rule.body
        ),
        None,
    )
    checks.require(bot_rule is not None, "regola dedicata di lock bot/dummy assente")
    if bot_rule:
        checks.require(not any(token in bot_rule.body for token in ("Create HUD Text(", "Small Message(", "DrawMenu", "Start Camera(", "Respawn(", "Resurrect(")),
                       "regola dedicata bot/dummy avvia HUD/menu/funzioni umane")
        checks.equal(
            compact(event_block(bot_rule)),
            compact("Ongoing - Each Player; All; All;"),
            "bot/dummy: evento esatto per entrambe le squadre",
        )
        bot_conditions = rule_block(bot_rule, "conditions")
        checks.require(bot_conditions is not None,
                       "bot/dummy: blocco conditions assente")
        if bot_conditions is not None:
            expected_bot_conditions = """
                Global.IsReady == True;
                Or(Is Dummy Bot(Event Player), Event Player.IsAutomaticBot) == True;
                Has Spawned(Event Player) == True;
                Is Alive(Event Player) == True;
                Or(Event Player.BotLocked == False, Hero Of(Event Player) != Event Player.LastHero) == True;
            """
            checks.equal(
                compact(bot_conditions),
                compact(expected_bot_conditions),
                "bot/dummy: condizioni esatte e raggiungibili",
            )

    environment_collision_calls = [
        (rule, call)
        for rule in rules
        for call in iter_calls(rule.body, "Disable Movement Collision With Environment")
    ]
    checks.equal(len(environment_collision_calls), 2,
                 "numero disattivazioni collisione ambiente: solo Ghost locale/globale")
    collision_actions = (
        "Enable Movement Collision With Environment(",
        "Disable Movement Collision With Environment(",
        "Enable Movement Collision With Players(",
        "Disable Movement Collision With Players(",
    )
    if bot_rule:
        checks.require(not any(token in bot_rule.body for token in collision_actions),
                       "bot/dummy: conservare le collisioni native senza riapplicarle")
        bot_actions = rule_block(bot_rule, "actions")
        checks.require(bot_actions is not None, "bot/dummy: blocco actions assente")
        if bot_actions is not None:
            expected_bot_actions = """
                Call Subroutine(LockBot);
                If(Is Dummy Bot(Event Player) == True);
                    Event Player.DummyBotTravelTime = Total Time Elapsed + 1;
                    Event Player.DummyBotTravelCursor = 0;
                    Set Respawn Max Time(Event Player, 3);
                End;
            """
            checks.equal(compact(bot_actions), compact(expected_bot_actions),
                         "bot/dummy: sequenza raggiungibile e isolata")

    ghost_physics = rule_by_subroutine(rules, "ApplyGhostFlyPhysics")
    cycle = rule_by_subroutine(rules, "ProcessPlayerCycle")
    for owner, target, label in (
        (ghost_physics, "Event Player", "Ghost locale"),
        (cycle, "Global.ActivePlayer", "Ghost globale 10 Hz"),
    ):
        checks.require(owner is not None, f"{label}: owner collisione ambiente assente")
        if owner:
            calls = list(iter_calls(owner.body, "Disable Movement Collision With Environment"))
            checks.equal(len(calls), 1, f"{label}: numero disattivazioni collisione ambiente")
            if calls:
                checks.equal(calls[0].args, (target, "False"),
                             f"{label}: deve attraversare pareti ma non pavimenti")

    checks.require(
        not any(len(call.args) >= 2 and call.args[1].strip() != "False"
                for _, call in environment_collision_calls),
        "collisione ambiente: Include Floors deve restare False in ogni owner",
    )

    bot_lock = rule_by_subroutine(rules, "LockBot")
    checks.require(bot_lock is not None, "subroutine dedicata LockBot assente")
    if bot_lock:
        checks.require(not any(token in bot_lock.body for token in ("Create HUD Text(", "Create In-World Text(", "Small Message(", "Start Camera(", "Teleport(", "Respawn(", "Resurrect(")),
                       "LockBot crea HUD/menu/funzioni per bot/dummy")
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
            checks.require(token in bot_lock.body, f"LockBot incompleto: {token}")
        for action, expected, label in (
            ("Set Damage Received", ("Event Player", "100"), "danni ricevuti normali"),
            ("Set Knockback Received", ("Event Player", "100"), "urti ricevuti normali"),
        ):
            calls = list(iter_calls(bot_lock.body, action))
            checks.equal(len(calls), 1, f"LockBot: numero impostazioni {label}")
            if calls:
                checks.equal(tuple(argument.strip() for argument in calls[0].args), expected,
                             f"LockBot: {label}")
        checks.require(not any(token in bot_lock.body for token in collision_actions),
                       "LockBot: conservare le collisioni native senza riapplicarle")
        move_speed_calls = list(iter_calls(bot_lock.body, "Set Move Speed"))
        checks.equal(len(move_speed_calls), 1, "LockBot: numero impostazioni velocità")
        if move_speed_calls:
            checks.equal(move_speed_calls[0].args[0].strip(), "Event Player",
                         "LockBot: destinatario velocità")
            checks.equal(move_speed_calls[0].args[1].strip(), "20",
                         "LockBot: velocità bot/dummy")

    validate_dummy_slot_management(checks, rules, compact)

    expected_enemy_predicate = (
        "And(Entity Exists(Current Array Element), "
        "And(Player Variable(Current Array Element, IsHuman) == True, "
        "And(Player Variable(Current Array Element, AllowDummyBotFollow) == True, "
        "And(Has Spawned(Current Array Element), "
        "And(Is Alive(Current Array Element), "
        "Team Of(Current Array Element) == Opposite Team Of(Team Of(Global.ActivePlayer)))))))"
    )
    dummy_cycle = rule_by_subroutine(rules, "ProcessPlayerBot")
    checks.require(dummy_cycle is not None, "cache target dummy 5 Hz assente")
    if dummy_cycle:
        target_filters = [
            call for call in iter_calls(dummy_cycle.body, "Filtered Array")
            if len(call.args) >= 2 and call.args[0].strip() == "Global.HumanPlayers"
            and "AllowDummyBotFollow" in call.raw
        ]
        checks.equal(len(target_filters), 1,
                     "cache target dummy deve filtrare gli umani opt-in una sola volta per ciclo")
        if target_filters:
            checks.equal(compact(target_filters[0].args[1]), compact(expected_enemy_predicate),
                         "cache target dummy: filtro deve essere l'umano nemico vivo opt-in")
        checks.require(
            "Set Player Variable(Global.ActivePlayer, DummyBotFollowTarget, First Of(Sorted Array(Global.ActivePlayer.InspectionTargets, Distance Between(Global.ActivePlayer, Current Array Element))));"
            in dummy_cycle.body,
            "cache target dummy non seleziona il più vicino a 5 Hz",
        )

    dummy_movement = next(
        (
            rule for rule in rules
            if event_type(rule) == "Ongoing - Each Player"
            and "Start Facing(Event Player," in rule.body
            and "Start Throttle In Direction(Event Player," in rule.body
        ),
        None,
    )
    checks.require(dummy_movement is not None, "movimento automatico dummy assente")
    if dummy_movement:
        checks.equal(compact(event_block(dummy_movement)), compact("Ongoing - Each Player; All; All;"),
                     "movimento dummy: evento esatto per entrambe le squadre")
        for token in (
            "Is Dummy Bot(Event Player) == True;",
            "Has Spawned(Event Player) == True;",
            "Is Alive(Event Player) == True;",
            "Event Player.DummyBotFollowTarget != Null;",
            "Entity Exists(Event Player.DummyBotFollowTarget) == True;",
            "Player Variable(Event Player.DummyBotFollowTarget, AllowDummyBotFollow) == True;",
            "Team Of(Event Player.DummyBotFollowTarget) == Opposite Team Of(Team Of(Event Player));",
        ):
            checks.require(token in dummy_movement.body, f"movimento automatico dummy incompleto: {token}")
        checks.require("Filtered Array(Global.HumanPlayers" not in dummy_movement.body,
                       "movimento dummy ricalcola ancora il roster invece di usare DummyBotFollowTarget")
        checks.require("Sorted Array(" not in dummy_movement.body,
                       "movimento dummy riordina ancora i target per-frame")

        facing_calls = list(iter_calls(dummy_movement.body, "Start Facing"))
        checks.equal(len(facing_calls), 1, "movimento dummy: numero facing automatici")
        if facing_calls:
            facing = facing_calls[0]
            checks.equal(len(facing.args), 5, "movimento dummy: argomenti facing")
            if len(facing.args) == 5:
                for index, expected in (
                    (0, "Event Player"),
                    (2, "1000"),
                    (3, "To World"),
                    (4, "Direction and Turn Rate"),
                ):
                    checks.equal(facing.args[index].strip(), expected,
                                 f"movimento dummy: facing argomento {index}")
                checks.equal(compact(facing.args[1]),
                             compact("Direction Towards(Eye Position(Event Player), Eye Position(Event Player.DummyBotFollowTarget))"),
                             "movimento dummy: facing deve usare il target cache")

        throttle_calls = list(iter_calls(dummy_movement.body, "Start Throttle In Direction"))
        checks.equal(len(throttle_calls), 1, "movimento dummy: numero throttle automatici")
        if throttle_calls:
            throttle = throttle_calls[0]
            checks.equal(len(throttle.args), 6, "movimento dummy: argomenti throttle")
            if len(throttle.args) == 6:
                for index, expected in (
                    (0, "Event Player"),
                    (1, "Forward"),
                    (3, "To Player"),
                    (4, "Replace Existing Throttle"),
                    (5, "Direction and Magnitude"),
                ):
                    checks.equal(throttle.args[index].strip(), expected,
                                 f"movimento dummy: throttle argomento {index}")
            magnitude = parse_top_level_ternary(throttle.args[2]) if len(throttle.args) >= 3 else None
            checks.require(magnitude is not None, "movimento dummy: ternario arresto assente")
            if magnitude:
                stop_condition, stopped, moving = magnitude
                checks.equal(stopped, "0", "movimento dummy: magnitudine entro quattro metri")
                checks.equal(moving, "1", "movimento dummy: magnitudine oltre quattro metri")
                checks.equal(compact(stop_condition),
                             compact("Or(Is In Spawn Room(Event Player), Distance Between(Event Player, Event Player.DummyBotFollowTarget) <= 4)"),
                             "movimento dummy: arresto deve usare il target cache")
        checks.require("Abort;" not in dummy_movement.body
                       and "Stop Facing(Event Player);" not in dummy_movement.body
                       and "Stop Throttle In Direction(Event Player);" not in dummy_movement.body,
                       "movimento dummy: azioni esatte senza abort o arresti aggiuntivi")
        checks.require(not wait_calls(dummy_movement.body) and action_loop_count(dummy_movement.body) == 0,
                       "movimento automatico dummy non deve usare Wait/Loop")

    no_target_cleanup = next(
        (
            rule for rule in rules
            if event_type(rule) == "Ongoing - Each Player"
            and "Is Dummy Bot(Event Player) == True;" in rule.body
            and "Event Player.DummyBotFollowTarget == Null" in rule.body
            and "Stop Facing(Event Player);" in rule.body
        ),
        None,
    )
    checks.require(no_target_cleanup is not None, "cleanup movimento dummy cache senza target assente")
    if no_target_cleanup:
        checks.equal(compact(event_block(no_target_cleanup)), compact("Ongoing - Each Player; All; All;"),
                     "cleanup movimento dummy: evento esatto per entrambe le squadre")
        checks.require("Filtered Array(Global.HumanPlayers" not in no_target_cleanup.body,
                       "cleanup movimento dummy non deve rifiltrare il roster")
        for token in (
            "Event Player.DummyBotFollowTarget == Null",
            "Entity Exists(Event Player.DummyBotFollowTarget) == False",
            "Player Variable(Event Player.DummyBotFollowTarget, IsHuman) == False",
            "Player Variable(Event Player.DummyBotFollowTarget, AllowDummyBotFollow) == False",
            "Has Spawned(Event Player.DummyBotFollowTarget) == False",
            "Is Alive(Event Player.DummyBotFollowTarget) == False",
            "Team Of(Event Player.DummyBotFollowTarget) != Opposite Team Of(Team Of(Event Player))",
            "Stop Facing(Event Player);",
            "Stop Throttle In Direction(Event Player);",
        ):
            checks.require(token in no_target_cleanup.body,
                           f"cleanup movimento dummy cache incompleto: {token}")

    dummy_arming = next(
        (
            rule for rule in rules
            if "If(Event Player.DummyBotTravelTime == 0);" in rule.body
            and "Event Player.DummyBotTravelTime = Total Time Elapsed + 1;" in rule.body
        ),
        None,
    )
    checks.require(dummy_arming is not None, "arming timestamp teleport dummy assente")
    if dummy_arming:
        for token in (
            "Is Dummy Bot(Event Player) == True;",
            "Has Spawned(Event Player) == True;",
            "Is Alive(Event Player) == True;",
            "Is In Spawn Room(Event Player) == True;",
        ):
            checks.require(token in dummy_arming.body, f"arming timestamp dummy incompleto: {token}")
        checks.require(not wait_calls(dummy_arming.body), "arming timestamp dummy non deve usare Wait")

    dummy_teleport = next(
        (
            rule for rule in rules
            if "Position Of(First Of(Spawn Points(Team Of(Event Player))))" in rule.body
            and "Event Player.DummyBotTravelTime == 0" in rule.body
        ),
        None,
    )
    checks.require(dummy_teleport is not None, "teleport dummy a timestamp assente")
    if dummy_teleport:
        expected_conditions = """
            Global.IsReady == True;
            Is Dummy Bot(Event Player) == True;
            Current Game Mode == Game Mode(Skirmish);
            Has Spawned(Event Player) == True;
            Is Alive(Event Player) == True;
            Is In Spawn Room(Event Player) == True;
            Count Of(Spawn Points(Team Of(Event Player))) > 0;
            Or(Event Player.DummyBotTravelTime == 0, Total Time Elapsed >= Event Player.DummyBotTravelTime) == True;
        """
        checks.equal(compact(rule_block(dummy_teleport, "conditions") or ""),
                     compact(expected_conditions),
                     "teleport dummy: condizioni esatte solo Schermaglia")
        checks.equal(dummy_teleport.body.count(
            "Event Player.DeathPosition = Objective Position(Objective Index);"), 1,
            "teleport dummy: un solo ancoraggio all'obiettivo corrente")
        checks.require(not any(token in mask_strings(dummy_teleport.body)
                               for token in ("Flag Position(", "Payload Position", "Is On Objective(")),
                       "teleport dummy: rami delle altre modalità non ammessi")
        checks.require(
            "Or(Event Player.DummyBotTravelTime == 0, Total Time Elapsed >= Event Player.DummyBotTravelTime) == True;"
            in dummy_teleport.body,
                       "teleport dummy non attende il timestamp")
        checks.require("Event Player.DummyBotTravelTime = Total Time Elapsed + 1;" in dummy_teleport.body,
                       "teleport dummy non pianifica un retry sicuro")
        checks.require("Abort;" in dummy_teleport.body,
                       "teleport dummy non interrompe il primo tick di arming")
        checks.require(not wait_calls(dummy_teleport.body), "teleport dummy non deve usare Wait")

    dummy_death = next(
        (
            rule for rule in rules_with_event(rules, "Player Died")
            if "Is Dummy Bot(Event Player) == True;" in rule.body
            and "Stop Facing(Event Player);" in rule.body
        ),
        None,
    )
    checks.require(dummy_death is not None, "cleanup morte dummy assente")
    if dummy_death:
        checks.equal(
            compact(event_block(dummy_death)),
            compact("Player Died; All; All;"),
            "cleanup morte dummy: evento esatto per entrambe le squadre",
        )
        checks.require("Stop Throttle In Direction(Event Player);" in dummy_death.body,
                       "cleanup morte dummy non ferma il throttle")
        checks.require("Event Player.DummyBotTravelTime = 0;" in dummy_death.body,
                       "morte dummy non riarma il delay del prossimo spawn")
        death_conditions = rule_block(dummy_death, "conditions")
        death_actions = rule_block(dummy_death, "actions")
        checks.require(death_conditions is not None,
                       "cleanup morte dummy: blocco conditions assente")
        checks.require(death_actions is not None,
                       "cleanup morte dummy: blocco actions assente")
        if death_conditions is not None:
            checks.equal(
                compact(death_conditions),
                compact(
                    "Is Dummy Bot(Event Player) == True; "
                    "Is Alive(Event Player) == False;"
                ),
                "cleanup morte dummy: condizioni esatte dopo la morte completa",
            )
        if death_actions is not None:
            checks.equal(
                compact(death_actions),
                compact(
                    "Stop Facing(Event Player); "
                    "Stop Throttle In Direction(Event Player); "
                    "Event Player.DummyBotTravelTime = 0; "
                    "Event Player.DummyBotTravelCursor = 0; "
                    "Event Player.DummyBotFollowTarget = Null;"
                ),
                "cleanup morte dummy: azioni esatte senza abort",
            )


def validate_modes_and_camera(checks: Checks, source: str, rules: list[Rule]) -> None:
    def camera_code(expression: str) -> str:
        return re.sub(r"\s+", "", mask_strings(expression))

    objective_rule = rule_by_subroutine(rules, "TravelToObjective")
    checks.require(objective_rule is not None, "dispatcher destinazione obiettivo assente")
    if objective_rule:
        objective_actions = rule_block(objective_rule, "actions") or ""
        for call in reversed(list(iter_calls(objective_actions, "Small Message"))):
            objective_actions = objective_actions[:call.start] + objective_actions[call.end + 1:]
        expected_objective_actions = """
            Event Player.TravelDestination = Objective Position(Objective Index);
            If(Distance Between(Event Player.TravelDestination, Vector(0, 0, 0)) <= 0.100);
                Abort;
            End;
            Call Subroutine(FindSafeTravelPosition);
            If(Distance Between(Event Player.SafeRevivePosition, Vector(0, 0, 0)) <= 0.100);
                Abort;
            End;
            If(Event Player.CameraMode != 0);
                Stop Camera(Event Player);
            End;
            Teleport(Event Player, Event Player.SafeRevivePosition);
            If(Event Player.CameraMode != 0);
                Global.CameraPlayer = Event Player;
                Call Subroutine(StartCamera);
                Global.CameraPlayer = Null;
            End;
        """
        checks.equal(re.sub(r"\s+", "", mask_strings(objective_actions)),
                     re.sub(r"\s+", "", expected_objective_actions),
                     "destinazione obiettivo: obiettivo corrente, controlli anti-origine e sicurezza obbligatori")
        safe_position = rule_by_subroutine(rules, "FindSafeTravelPosition")
        checks.require(safe_position is not None, "subroutine comune posizione teleport sicura assente")
        checks.require("Call Subroutine(FindSafeTravelPosition);" in objective_rule.body,
                       "teleport obiettivo non usa la subroutine comune di sicurezza")
        if safe_position:
            checks.require("Nearest Walkable Position(" in safe_position.body,
                           "subroutine teleport sicura non verifica una posizione percorribile")
            checks.require("Ray Cast Hit Position(" in safe_position.body,
                           "subroutine teleport sicura non verifica terreno/percorso")
            safe_calls = list(iter_calls(safe_position.body, "Ray Cast Hit Position"))
            checks.require(len(safe_calls) >= 16,
                           "subroutine teleport sicura ha perso una verifica raycast obbligatoria")
            safe_packed = re.sub(r"\s+", "", mask_strings(safe_position.body))
            floor_branch = (
                "If(DistanceBetween(RayCastHitPosition("
                "EventPlayer.SafeRevivePosition+Vector(0,5,0),"
                "EventPlayer.SafeRevivePosition-Vector(0,20,0),"
                "EmptyArray,EmptyArray,False),EventPlayer.SafeRevivePosition)>6);"
                "EventPlayer.SafeRevivePosition=Vector(0,0,0);Abort;End;"
            )
            path_branch = (
                "If(DistanceBetween(RayCastHitPosition("
                "EventPlayer.TravelDestination+Vector(0,1,0),"
                "EventPlayer.SafeRevivePosition+Vector(0,1,0),"
                "EmptyArray,EmptyArray,False),"
                "EventPlayer.SafeRevivePosition+Vector(0,1,0))>0.750);"
                "EventPlayer.SafeRevivePosition=Vector(0,0,0);End;"
            )
            checks.require(floor_branch in safe_packed,
                           "subroutine teleport sicura non invalida il vuoto con il raycast terreno verticale")
            checks.require(path_branch in safe_packed,
                           "subroutine teleport sicura non invalida il percorso finale ostruito")
            checks.require("Vector(1.500, 1, 0)" in safe_position.body and "Vector(-1.500, 1, 0)" in safe_position.body,
                           "subroutine teleport sicura non mantiene distanza laterale dalle pareti")
            checks.require("Vector(0, 1, 1.500)" in safe_position.body and "Vector(0, 1, -1.500)" in safe_position.body,
                           "subroutine teleport sicura non mantiene distanza frontale/posteriore dalle pareti")
            checks.require("Vector(0, 2.750, 0)" in safe_position.body,
                           "subroutine teleport sicura non verifica spazio sopra la capsula finale")
            checks.require("SafeRevivePosition += Vector(0, 0.500, 0);" in safe_position.body,
                           "subroutine teleport sicura non rialza di 0,5 m il punto finale dal pavimento")
        click_dispatch = next(
            (
                rule
                for rule in rules
                if "TravelCommand == 3" in rule.body
                and "Call Subroutine(TravelToObjective);" in rule.body
            ),
            None,
        )
        checks.require(
            click_dispatch is not None
            or "TravelCommand == 3" in objective_rule.body
            or "Button(Interact)" in objective_rule.body,
            "destinazione teleport non viene valutata al click",
        )
    before_travel = "If(EventPlayer.CameraMode!=0);StopCamera(EventPlayer);End;"
    after_travel = (
        "If(EventPlayer.CameraMode!=0);Global.CameraPlayer=EventPlayer;"
        "CallSubroutine(StartCamera);Global.CameraPlayer=Null;End;"
    )
    for name in ("TravelToSpawn", "TravelToObjective", "TravelToPlayer"):
        travel = rule_by_subroutine(rules, name)
        checks.require(travel is not None, f"Camera Travel: routine {name} assente")
        if travel is None:
            continue
        teleports = list(iter_calls(travel.body, "Teleport"))
        stops = list(iter_calls(travel.body, "Stop Camera"))
        restarts = [call for call in iter_calls(travel.body, "Call Subroutine")
                    if call.args == ("StartCamera",)]
        checks.equal((len(teleports), len(stops), len(restarts)), (1, 1, 1),
                     f"Camera Travel {name}: un solo teleport e reset nativo")
        for teleport in teleports:
            checks.require(camera_code(travel.body[:teleport.start]).endswith(before_travel),
                           f"Camera Travel {name}: Stop Camera protetto immediatamente prima del teleport riuscito")
            checks.require(camera_code(travel.body[teleport.end:]).startswith(";" + after_travel),
                           f"Camera Travel {name}: riavvio protetto immediatamente dopo il teleport riuscito")
            checks.require("If(EventPlayer.CameraMode!=0);" not in
                           [camera_code(branch.splitlines()[0]) for branch in
                            conditional_branches_containing(travel.body, teleport.start)],
                           f"Camera Travel {name}: Camera OFF non deve impedire il teleport")
        checks.require(re.search(r"\.(?:CameraMode|CameraTarget)\s*=(?!=)", mask_strings(travel.body)) is None,
                       f"Camera Travel {name}: preservare modalità e bersaglio")
        checks.require(not wait_calls(travel.body) and action_loop_count(travel.body) == 0,
                       f"Camera Travel {name}: reset atomico senza Wait/Loop")

    cycle = rule_by_subroutine(rules, "ProcessPlayerCycle")
    checks.require(cycle is not None, "Camera hero: controller lifecycle assente")
    if cycle:
        hero_restarts = [call for call in iter_calls(cycle.body, "Call Subroutine")
                         if call.args == ("StartCamera",)]
        checks.equal(len(hero_restarts), 1, "Camera hero: unico riavvio al cambio del proprio eroe")
        reset_guard = (
            "If(And(Global.ActivePlayer.CameraMode!=0,"
            "And(Global.ActivePlayer.CameraTarget!=Null,EntityExists(Global.ActivePlayer.CameraTarget))));"
        )
        reset_actions = (
            reset_guard + "StopCamera(Global.ActivePlayer);Global.CameraPlayer=Global.ActivePlayer;"
            "CallSubroutine(StartCamera);Global.CameraPlayer=Null;End;"
        )
        checks.require(reset_actions in camera_code(cycle.body),
                       "Camera hero: fermare e ricreare soltanto la Camera attiva con bersaglio esistente")
        for restart in hero_restarts:
            branches = conditional_branches_containing(cycle.body, restart.start)
            hero_branch = next((branch for branch in branches if
                                "HeroOf(Global.ActivePlayer)!=Global.ActivePlayer.LastHero" in
                                camera_code(branch.splitlines()[0])), None)
            checks.require(hero_branch is not None,
                           "Camera hero: riavvio protetto dal cambio eroe, mai a ogni tick")
            if hero_branch:
                hero_packed = camera_code(hero_branch)
                checks.require(hero_packed.find("Global.ActivePlayer.LastHero=HeroOf(Global.ActivePlayer);")
                               < hero_packed.find("CallSubroutine(StartCamera);")
                               and "Global.ActivePlayer.LastHero=HeroOf(Global.ActivePlayer);" in hero_packed,
                               "Camera hero: registrare il nuovo eroe prima del singolo riavvio")

    bootstrap_skip_token = "Set Match Time(0);"
    checks.equal(
        source.count(bootstrap_skip_token),
        2,
        "bootstrap skip fase awal harus tepat dua Set Match Time(0)",
    )
    bootstrap_skip_heroes = next(
        (rule for rule in rules if rule.name.startswith("00a2 - Global: Skip hero selection")),
        None,
    )
    checks.require(bootstrap_skip_heroes is not None, "rule 00a2 bootstrap Assemble Heroes assente")
    if bootstrap_skip_heroes:
        checks.equal(
            bootstrap_skip_heroes.body.count(bootstrap_skip_token),
            1,
            "00a2 harus menembak Set Match Time(0) tepat sekali",
        )
        for guard in (
            "Global.HeroSelectionSkipped == False;",
            "Count Of(Global.HumanPlayers) == 0;",
            "Global.TeamCyclePlayer == Null;",
            "Is Game In Progress == False;",
            "Is Assembling Heroes == True;",
        ):
            checks.require(guard in bootstrap_skip_heroes.body, f"00a2 guard bootstrap hilang: {guard}")
        hero_latch_position = bootstrap_skip_heroes.body.find("Global.HeroSelectionSkipped = True;")
        hero_skip_position = bootstrap_skip_heroes.body.find(bootstrap_skip_token)
        checks.require(
            0 <= hero_latch_position < hero_skip_position,
            "00a2 harus menulis latch sebelum Set Match Time(0)",
        )

    bootstrap_skip_setup = next(
        (rule for rule in rules if rule.name.startswith("00a3 - Global: Skip initial setup")),
        None,
    )
    checks.require(bootstrap_skip_setup is not None, "rule 00a3 bootstrap Setup assente")
    if bootstrap_skip_setup:
        checks.equal(
            bootstrap_skip_setup.body.count(bootstrap_skip_token),
            1,
            "00a3 harus menembak Set Match Time(0) tepat sekali",
        )
        for guard in (
            "Global.SetupSkipped == False;",
            "Count Of(Global.HumanPlayers) == 0;",
            "Global.TeamCyclePlayer == Null;",
            "Is Game In Progress == False;",
            "Is In Setup == True;",
        ):
            checks.require(guard in bootstrap_skip_setup.body, f"00a3 guard bootstrap hilang: {guard}")
        setup_latch_position = bootstrap_skip_setup.body.find("Global.SetupSkipped = True;")
        setup_skip_position = bootstrap_skip_setup.body.find(bootstrap_skip_token)
        checks.require(
            0 <= setup_latch_position < setup_skip_position,
            "00a3 harus menulis latch sebelum Set Match Time(0)",
        )

    bootstrap_lock_rule = next(
        (rule for rule in rules if rule.name.startswith('00a4 - Global: Lock initial phase skipping after the game starts')),
        None,
    )
    checks.require(bootstrap_lock_rule is not None, "rule 00a4 lock bootstrap assente")
    if bootstrap_lock_rule:
        checks.equal(
            bootstrap_lock_rule.body.count(bootstrap_skip_token),
            0,
            "00a4 tidak boleh menembak Set Match Time(0)",
        )
        for guard in (
            "Is Game In Progress == True;",
            "Or(Global.HeroSelectionSkipped == False, Global.SetupSkipped == False) == True;",
        ):
            checks.require(guard in bootstrap_lock_rule.body, f"00a4 guard lock hilang: {guard}")
    for token in FORBIDDEN_RESULT_ACTIONS:
        checks.require(token not in source, f"risultato deve restare alla modalità nativa: {token}")
    completion_token = "Disable Built-In Game Mode Completion;"
    checks.equal(source.count(completion_token), 1, "blocco completamento nativo fino al timer CHILL")
    checks.require(
        "ServerTimeRemaining + 5" not in source,
        "sinkronisasi timer mode tidak boleh menambah offset +5",
    )
    timer_sync_rule = next(
        (
            rule
            for rule in rules_with_event(rules, "Ongoing - Global")
            if completion_token in rule.body
            and "Set Match Time(Max(1, Global.ServerTimeRemaining));" in rule.body
        ),
        None,
    )
    checks.require(
        timer_sync_rule is not None,
        "timer mode bawaan tidak disinkronkan ke countdown CHILL",
    )
    if timer_sync_rule:
        checks.require(
            "Is Game In Progress == True" in timer_sync_rule.body,
            "sinkronisasi timer mode harus aktif hanya saat pertandingan berjalan",
        )
        checks.require(
            "Global.RestartRequested == False" in timer_sync_rule.body,
            "sinkronisasi timer mode harus berhenti setelah restart diminta",
        )
        checks.require(
            "Global.ServerTimeRemaining > 0" in timer_sync_rule.body,
            "sinkronisasi timer mode harus menjaga timer custom sebagai pemicu tunggal restart",
        )
        timer_packed = re.sub(r"\s+", "", mask_strings(timer_sync_rule.body))
        cadence_token = (
            "If(And(Global.SchedulerStep%20==0,"
            "Global.RestartRequested==False));"
        )
        cadence_position = timer_packed.find(cadence_token)
        for action_token, label in (
            (completion_token, "blocco completion"),
            ("Set Match Time(Max(1, Global.ServerTimeRemaining));", "Set Match Time"),
        ):
            action_position = timer_sync_rule.body.find(action_token)
            branches = (
                conditional_branches_containing(timer_sync_rule.body, action_position)
                if action_position >= 0
                else []
            )
            cadence_branch = next(
                (
                    mask_strings(branch)
                    for branch in branches
                    if "Global.SchedulerStep % 20 == 0" in mask_strings(branch)
                    and "Global.RestartRequested == False" in mask_strings(branch)
                ),
                "",
            )
            progress_branch = next(
                (
                    mask_strings(branch)
                    for branch in branches
                    if "Is Game In Progress == True" in mask_strings(branch)
                    and "Global.ServerTimeRemaining > 0" in mask_strings(branch)
                ),
                "",
            )
            checks.require(
                cadence_position >= 0 and bool(cadence_branch),
                f"sincronizzazione timer mode: {label} fuori dal ramo scheduler 1 Hz",
            )
            checks.require(
                bool(progress_branch),
                f"sincronizzazione timer mode: {label} fuori dalla guardia partita attiva",
            )
    camera_rule = rule_by_subroutine(rules, "StartCamera")
    checks.require(camera_rule is not None, "subroutine Camera assente")
    camera_calls = [
        (rule, call)
        for rule in rules
        for call in iter_calls(rule.body, "Start Camera")
    ]
    checks.equal(
        len(camera_calls),
        1,
        "Camera deve avere un solo Start Camera in StartCamera",
    )
    if len(camera_calls) == 1:
        checks.require(
            subroutine_target(camera_calls[0][0]) == "StartCamera",
            "Camera deve avere un solo Start Camera in StartCamera",
        )
    if camera_rule:
        camera_packed = camera_code(camera_rule.body)
        for guard in (
            "AbortIf(Global.CameraPlayer==Null);",
            "AbortIf(EntityExists(Global.CameraPlayer)==False);",
            "AbortIf(Global.CameraPlayer.CameraMode==0);",
            "AbortIf(Global.CameraPlayer.CameraTarget==Null);",
            "AbortIf(EntityExists(Global.CameraPlayer.CameraTarget)==False);",
        ):
            checks.require(guard in camera_packed and camera_packed.find(guard) < camera_packed.find("StartCamera("),
                           f"Camera centralizzata: guardia proprietario/bersaglio prima di Start Camera {guard}")
        checks.require("Event Player" not in mask_strings(camera_rule.body),
                       "Camera centralizzata: proprietario esplicito riutilizzabile dal contesto globale")
        checks.equal(camera_rule.body.count("Ray Cast Hit Position("), 1, "raycast Camera")
        start_calls = list(iter_calls(camera_rule.body, "Start Camera"))
        checks.equal(
            len(start_calls),
            1,
            "Camera deve avere un solo Start Camera in StartCamera",
        )
        if len(start_calls) == 1:
            checks.require(
                len(start_calls[0].args) == 4
                and start_calls[0].args[1].strip().startswith("Update Every Frame(")
                and start_calls[0].args[2].strip().startswith("Update Every Frame(")
                and start_calls[0].args[3].strip() == "0",
                "Camera per-frame deve usare Blend Speed 0 per non inseguire la traslazione del target",
            )
        callers = [rule for rule in rules if list(iter_calls(rule.body, "Call Subroutine"))
                   and any(call.args == ("StartCamera",) for call in iter_calls(rule.body, "Call Subroutine"))]
        checks.require(bool(callers), "Camera: StartCamera mai chiamata")
        apply_camera = rule_by_subroutine(rules, "ApplyCameraPage")
        quick_camera = next((rule for rule in rules if rule.name.startswith("12c - Camera:")), None)
        checks.require(apply_camera is not None and quick_camera is not None
                       and apply_camera.body.count("Call Subroutine(StartCamera);") == 2
                       and quick_camera.body.count("Call Subroutine(StartCamera);") == 1,
                       "Camera personale, watch e toggle rapido devono condividere StartCamera")
        for rule in callers:
            actions = rule_block(rule, "actions") or ""
            for call in iter_calls(actions, "Call Subroutine"):
                if call.args != ("StartCamera",):
                    continue
                before, after = actions[:call.start], actions[call.end:]
                assignments = list(re.finditer(r"Global\.CameraPlayer\s*=\s*([^;]+);", before))
                checks.require(bool(assignments) and assignments[-1][1].strip() in
                               {"Event Player", "Global.ActivePlayer"},
                               "Camera: proprietario esplicito prima di StartCamera")
                checks.require(re.match(r"\s*;\s*Global\.CameraPlayer\s*=\s*Null;", after) is not None,
                               "Camera: proprietario azzerato dopo StartCamera")



def validate_english_and_duplicates(checks: Checks, source: str, rules: list[Rule]) -> None:
    """Reject duplicate rules and leftover translated rule titles or comments."""
    names = [rule.name for rule in rules]
    checks.equal(len(names), len(set(names)), "titoli regola univoci")
    bodies = [normalized_rule_body(rule) for rule in rules]
    checks.require(not [body for body, count in Counter(bodies).items() if count > 1],
                   "regole duplicate con corpo identico")
    legacy_prose = re.compile(
        r"\b(?:Umum|Pemain|Jangan|Siapkan|Bersihkan|Pembersihan|Penjadwal|"
        r"Teleportasi|Terapkan|Gambar|Perbarui|Tenangkan|Kembalikan|"
        r"Hapus|Matikan|Pengenal|pemilik|bahasa|pahlawan|sumber|"
        r"rilascia|restituisci|senza|scadenza|temporanei|pulisce|"
        r"aggiorna|distruggi|ricrea)\b",
        re.IGNORECASE,
    )
    for rule in rules:
        checks.require(legacy_prose.search(rule.name) is None,
                       f"titolo regola non interamente inglese: {rule.name}")
    standalone_comments = re.findall(r'(?m)^\s*"((?:[^"\\]|\\.)*)"\s*$', source)
    for comment in standalone_comments:
        checks.require(legacy_prose.search(comment) is None,
                       f"commento Workshop non interamente inglese: {comment[:80]}")


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
    validate_ghost_fly(checks, source, rules, player_entries, subroutines)
    validate_multijump(checks, source, rules, player_entries, subroutines)
    validate_super_punch(checks, source, rules, globals_entries, subroutines)
    validate_social_beacon(checks, source, rules, globals_entries)
    validate_special_player_profile(checks, source, rules, player_entries)
    validate_catalog_feedback(checks, source, rules)
    validate_input_contract(checks, rules)
    validate_unkillable_full_hp(checks, rules)
    validate_inspector_recording(checks, source, rules)
    validate_scheduler(checks, source, rules, globals_, subroutines)
    validate_hero_selection_timeout(checks, rules)
    validate_try_your_luck(checks, source, rules, players)
    validate_forced_death(checks, source, rules, players)
    validate_lifecycle(checks, rules, subroutines)
    validate_privacy(checks, rules)
    validate_bot_isolation(checks, rules)
    validate_modes_and_camera(checks, source, rules)
    validate_english_and_duplicates(checks, source, rules)
    return checks


def main() -> int:
    source = BEHAVIORAL_REFERENCE.read_text(encoding="utf-8")
    checks = validate(source)
    try:
        english_input = BEHAVIORAL_SOURCE.read_text(encoding="utf-8")
        clipboard_import.check_text(english_input, "en-US")
        checks.equal(source, english_input, "English behavioral source must match its reference")
    except (OSError, clipboard_import.ClipboardImportError) as error:
        checks.require(False, f"English behavioral input invalid: {error}")
    try:
        from tools import validate_global_runtime
    except ImportError:  # Direct execution: python tools/validate_workshop.py
        import validate_global_runtime
    for error in validate_global_runtime.validate_generated(ROOT):
        checks.require(False, f"output globale compilato: {error}")
    checks.finish()
    rules = extract_rules(source)
    print(
        "OK - English behavioral contracts v0.8.1 and source parity verified "
        f"({len(rules)} regole, {len(wait_calls(source))} Wait, {action_loop_count(source)} Loop)"
    )
    print("OK - gate dell'output globale compilato e aggiornamento della generazione superati")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
