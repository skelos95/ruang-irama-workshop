"""Deterministic lowering of the logical Workshop into one global runtime.

The English behavioral input is lowered into the English import and its
runtime reference. --check verifies both deterministic artifacts;
native engine lifetime and rendering still require an in-game test.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
import check_clipboard_import as clipboard
import validate_workshop as validator

ACTOR = "Global.TriggerPlayer"
RECORD = "Global.ActiveEvent"
STATE = f"{ACTOR}.ControllerState"
TIME = f"{ACTOR}.ControllerTimes"
CAPACITY = 256
NATIVE_PERSISTENT = (
    "Create HUD Text", "Create In-World Text", "Create Icon", "Create Effect",
    "Start Camera", "Start Facing", "Start Throttle In Direction", "Start Accelerating",
    "Chase Player Variable At Rate", "Chase Player Variable Over Time",
    "Start Transforming Throttle", "Attach Players", "Start Forcing Dummy Bot Name",
    "Start Forcing Player To Be Hero", "Start Forcing Player Position",
)
EVENT_PREFIXES = ["03i", "04", "12e", "16a", "17", "18f", "89i1"]
# These leave their input/target predicate true while the button/target remains.
LATCH_PREFIXES = {"03g", "03h", "06", "08", "10", "11", "19c", "19e"}
GLOBALS = [
    "TriggerPlayer", "ControllerGeneration", "TeamCyclePhase", "TeamCyclePhaseTime", "TeamCyclePhaseOwner",
    "EventQueue", "EventQueueHead", "EventQueueTail", "EventCount", "InitialEventCount", "EventCursor",
    "ActiveEvent", "DroppedEventCount", "PendingLeaves", "PendingLeaveCursor", "MissingHudDeadlines", "MissingPlayerCursor", "VisibleIconChoices",
]


@dataclass(frozen=True)
class _Node:
    kind: str
    value: str
    children: tuple['_Node', ...] = ()


class _Expression:
    """Parse the emitter's expression grammar without changing literal bytes."""
    def __init__(self, source: str):
        token = re.compile(r'[A-Za-z]+(?:\s+[A-Za-z]+)*-[A-Za-z]+(?:\s+[A-Za-z]+)*|' + clipboard._StructuralExpression.TOKEN.pattern)
        self.tokens = []
        previous = 0
        for match in token.finditer(source):
            if source[previous:match.start()].strip():
                raise ValueError('unrecognized expression token')
            self.tokens.append(match[0].strip())
            previous = match.end()
        if source[previous:].strip():
            raise ValueError('unrecognized expression suffix')
        self.index = 0
        self.tree = self.parse()
        if self.index != len(self.tokens):
            raise ValueError('expression not exhausted: ' + source[:80])

    def peek(self):
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def take(self, expected=None):
        token = self.tokens[self.index]
        self.index += 1
        if expected is not None and token != expected:
            raise ValueError(f'expected {expected}, got {token}')
        return token

    def parse(self, minimum=0):
        token = self.take()
        if token in ('-', '+', '!'):
            left = _Node('unary', token, (self.parse(7),))
        elif token == '(':
            left = self.parse()
            self.take(')')
        elif token.startswith('"') or token[0].isdigit():
            left = _Node('literal', token)
        elif self.peek() == '(':
            self.take('(')
            children = []
            if self.peek() != ')':
                while True:
                    children.append(self.parse())
                    if self.peek() != ',': break
                    self.take(',')
            self.take(')')
            left = _Node('call', token, tuple(children))
        else:
            if token == 'Arrow' and self.peek() == ':':
                self.take(':')
                token += ': ' + self.take()
            left = _Node('name', token)
        while True:
            next_token = self.peek()
            if next_token == '.':
                self.take('.')
                left = _Node('member', self.take(), (left,))
            elif next_token == '[':
                self.take('[')
                left = _Node('index', '', (left, self.parse()))
                self.take(']')
            elif next_token == '?' and minimum <= 1:
                self.take('?')
                yes = self.parse()
                self.take(':')
                left = _Node('conditional', '', (left, yes, self.parse(1)))
            elif next_token in clipboard._StructuralExpression.PRECEDENCE and clipboard._StructuralExpression.PRECEDENCE[next_token] >= minimum:
                operation = self.take()
                left = _Node('binary', operation, (left, self.parse(clipboard._StructuralExpression.PRECEDENCE[operation] + 1)))
            else:
                return left


def _emit(node: _Node) -> str:
    if node.kind in ('literal', 'name'): return node.value
    if node.kind == 'call': return node.value + '(' + ', '.join(map(_emit, node.children)) + ')'
    if node.kind == 'member': return _emit(node.children[0]) + '.' + node.value
    if node.kind == 'index': return _emit(node.children[0]) + '[' + _emit(node.children[1]) + ']'
    if node.kind == 'binary':
        text = _emit(node.children[0]) + ' ' + node.value + ' ' + _emit(node.children[1])
        return text if node.value in ('=', '+=', '-=', '*=', '/=', '%=') else '(' + text + ')'
    if node.kind == 'unary':
        operand = node.children[0]
        if node.value == '+': return _emit(operand)
        if node.value == '!': return 'Not(' + _emit(operand) + ')'
        # The native importer accepts signed number literals, not -(value).
        # Preserve the literal bytes; negate expressions with a native value.
        if operand.kind == 'literal' and operand.value[0].isdigit():
            return '-' + operand.value
        return 'Multiply(-1, ' + _emit(operand) + ')'
    return '(' + _emit(node.children[0]) + ' ? ' + _emit(node.children[1]) + ' : ' + _emit(node.children[2]) + ')'


BOOLEAN_FUNCTIONS = {'And', 'Or', 'Not', 'Entity Exists', 'Has Spawned', 'Is Alive', 'Is Dummy Bot', 'Is Button Held', 'Is In Spawn Room', 'Is In Air', 'Is On Ground', 'Has Status', 'Array Contains', 'Is Duplicating', 'Is Using Ultimate', 'Is Using Ability 1', 'Is Using Ability 2', 'Is Firing Primary', 'Is Firing Secondary', 'Is True For Any', 'Is True For All', 'Is Communicating', 'Is Moving', 'Is On Wall'}


def _is_boolean(node: _Node, fields: frozenset[str]) -> bool:
    if node.kind == 'name': return node.value in {'True', 'False', 'Is Game In Progress', 'Is Assembling Heroes', 'Is Waiting For Players', 'Is Between Rounds'}
    if node.kind == 'member': return node.value in fields
    if node.kind == 'binary': return node.value in {'==', '!=', '<', '>', '<=', '>='}
    if node.kind == 'unary' and node.value == '!': return True
    if node.kind == 'call':
        return node.value in BOOLEAN_FUNCTIONS or (node.value == 'Player Variable' and node.children[1].value in fields)
    if node.kind == 'index' and _emit(node.children[0]) == RECORD:
        return node.children[1].value in {'8','10','11','12','14','15','17'}
    return False


def _boolean_fold(node: _Node, fields: frozenset[str] = frozenset()) -> _Node:
    children = tuple(_boolean_fold(child, fields) for child in node.children)
    node = _Node(node.kind, node.value, children)
    if node.kind == 'binary' and node.value in ('==', '!=') and children[1].kind == 'name' and children[1].value in ('True', 'False') and _is_boolean(children[0], fields):
        positive = (children[1].value == 'True') == (node.value == '==')
        return children[0] if positive else _Node('call', 'Not', (children[0],))
    if node.kind == 'call' and node.value == 'Not' and children[0].kind == 'call' and children[0].value == 'Not' and _is_boolean(children[0].children[0], fields):
        return children[0].children[0]
    return node


def compact_booleans(text: str) -> str:
    """Remove redundant boolean equality nodes in the generated backend only."""
    rules = validator.extract_rules(text)
    masked = validator.mask_strings(text)
    writes = re.findall(r'\.([A-Za-z][A-Za-z0-9_]*)\s*=(?!=)\s*([^;]+);', masked)
    fields = frozenset(field for field, rhs in writes if rhs.strip() in {'True', 'False'})
    # A mixed numeric/string write invalidates a Boolean inference. This also
    # keeps future source extensions from silently coercing non-Boolean data.
    while True:
        excluded = set()
        for field, rhs in writes:
            if field not in fields: continue
            try:
                value = _Expression(rhs).tree
            except (ValueError, IndexError):
                excluded.add(field)
                continue
            if not _is_boolean(value, fields): excluded.add(field)
        if not excluded: break
        fields -= excluded
    for rule in reversed(rules):
        actions_ = validator.rule_block(rule, 'actions') or ''
        uncommented = re.sub(r'(?m)^[ \t]*"(?:\\.|[^"\\])*"[ \t]*(?:\r?\n|$)', '', actions_)
        statements = []
        for statement in validator.split_top_level(uncommented, ';'):
            if statement.strip():
                statements.append('\t\t' + _emit(_boolean_fold(_Expression(statement).tree, fields)) + ';')
        replacement = '\n' + '\n'.join(statements) + '\n\t'
        new_body = rule.body.replace(actions_, replacement)
        text = text[:rule.start] + new_body + text[rule.end:]
    return text


def compact_palette(text: str) -> str:
    """Snapshot each command's colour destination from the logical palette."""
    rule = next(item for item in validator.extract_rules(text) if prefix(item) == '91k')
    body = rule.body
    # Global dispatch clears its actor before the native Chase's next frame.
    # Menu entry/navigation already restarts this 0.180 s interpolation, so
    # evaluate the destination now instead of capturing the cleared pointer
    # during asynchronous destination reevaluation. Other Chases stay live.
    chases = list(validator.iter_calls(body, 'Chase Player Variable Over Time'))
    assert len(chases) == 2
    for chase in reversed(chases):
        values = list(chase.args)
        assert values[1] == 'MenuColor' and values[3] == '0.180'
        values[4] = 'None'
        replacement = 'Chase Player Variable Over Time(' + ', '.join(values) + ')'
        body = body[:chase.start] + replacement + body[chase.end:]
    return text[:rule.start] + body + text[rule.end:]


def compact_icon_visibility(text: str) -> str:
    """Keep per-frame entity validity; share the other visibility predicates."""
    rule = next(item for item in validator.extract_rules(text) if prefix(item) == '89e')
    body = rule.body
    for call in reversed(list(validator.iter_calls(body, 'Create Icon'))):
        args = list(call.args)
        selected = re.search(r'IconIndex\) == (\d+)', args[0])
        assert selected is not None
        args[0] = f'And(Entity Exists(Evaluate Once(Global.ObjectiveIconPlayer)), Global.VisibleIconChoices[Evaluate Once(Global.ObjectiveIconIndex)] == {selected[1]}) ? All Players(All Teams) : Empty Array'
        replacement = 'Create Icon(' + ', '.join(args) + ')'
        body = body[:call.start] + replacement + body[call.end:]
    return text[:rule.start] + body + text[rule.end:]


def compact_fixed_pools(text: str) -> str:
    """Construct fixed-size zero/null pools from already initialized owners."""
    rule = next(item for item in validator.extract_rules(text) if prefix(item) == '00')
    body = rule.body
    initialized: set[str] = set()
    pieces = re.split(r'(Global\.[A-Za-z][A-Za-z0-9_]*\s*=\s*Array\([^;]*\);)', body)
    for index, piece in enumerate(pieces):
        assignment = re.fullmatch(r'(Global\.[A-Za-z][A-Za-z0-9_]*)\s*=\s*Array\(([^;]*)\);', piece)
        if not assignment: continue
        values = [item.strip() for item in validator.split_top_level(assignment[2], ',')]
        owner = 'Global.AvailableHudSlots' if len(values) == 12 else 'Global.TemporaryTextOwners' if len(values) == 24 else ''
        if owner in initialized and len(set(values)) == 1 and values[0] in {'0', 'Null'}:
            pieces[index] = f'{assignment[1]} = Mapped Array({owner}, {values[0]});'
        initialized.add(assignment[1])
    body = ''.join(pieces)
    return text[:rule.start] + body + text[rule.end:]


def compact_unused_constants(text: str) -> str:
    """Drop only pure bootstrap constants whose globals are never read."""
    rule = next(item for item in validator.extract_rules(text) if prefix(item) == '00')
    body = rule.body
    allowed = {'Array', 'Custom String', 'Vector', 'Color', 'Custom Color'}
    def pure(node):
        if node.kind == 'literal': return True
        if node.kind == 'name': return node.value in {'True', 'False', 'Null', 'Empty Array', 'White', 'Black', 'Orange'}
        return node.kind == 'call' and node.value in allowed and all(pure(child) for child in node.children)
    syntax = validator.mask_strings(text)
    pieces = re.split(r'(Global\.[A-Za-z][A-Za-z0-9_]*\s*=(?!=)[^;]*;)', body)
    for index, piece in enumerate(pieces):
        match = re.fullmatch(r'Global\.([A-Za-z][A-Za-z0-9_]*)\s*=(?!=)\s*([^;]*);', piece)
        if not match: continue
        variable, rhs = match.groups()
        if len(re.findall(rf'\bGlobal\.{re.escape(variable)}\b', syntax)) != 1: continue
        if re.search(rf'\b(?:Set|Modify) Global Variable(?: At Index)?\(\s*{re.escape(variable)}\b', syntax): continue
        if pure(_Expression(rhs).tree): pieces[index] = ''
    body = ''.join(pieces)
    return text[:rule.start] + body + text[rule.end:]


def translate(text: str, *, to_italian: bool = False) -> str:
    pieces = re.split(r'("(?:\\.|[^"\\])*")', text)
    pairs = [(b, a) for a, b in clipboard.ITALIAN_TO_ENGLISH_TOKENS] if to_italian else list(clipboard.ITALIAN_TO_ENGLISH_TOKENS)
    for index in range(0, len(pieces), 2):
        segment = pieces[index]
        for source, target in sorted(pairs, key=lambda pair: len(pair[0]), reverse=True):
            if to_italian and source == "Global":
                # Global is localized only as a namespace. Native names such
                # as Ongoing - Global and For Global Variable stay unchanged.
                segment = re.sub(r"\bGlobal(?=\s*\.)", target, segment)
            elif to_italian and source == "All":
                # Event selectors use Tutti; All Players, All Teams and
                # Is True For All are native value/function identifiers.
                segment = re.sub(r"\bAll(?=\s*;)", target, segment)
            else:
                segment = clipboard._replace_token(segment, source, target)
        pieces[index] = segment if to_italian else clipboard._normalize_named_colors(segment)
    return "".join(pieces)


def prefix(rule: validator.Rule) -> str:
    return rule.name.split(" -", 1)[0]


def conjunction(conditions: str | None) -> str:
    items = [x.strip() for x in validator.split_top_level(conditions or "", ";") if x.strip()]
    if not items:
        return "True"
    result = items[-1]
    for item in reversed(items[:-1]):
        result = f"And({item}, {result})"
    return result


def actor_text(text: str) -> str:
    return re.sub(r"\bEvent Player\b", ACTOR, text)


def capture(expression: str, actor: str) -> str:
    frozen = f"Evaluate Once({actor})"
    # Existing captures are retained instead of doubling their source tree.
    saved: list[str] = []
    captured_calls = list(validator.iter_calls(expression, 'Evaluate Once'))
    outer = [call for call in captured_calls if not any(other.start < call.start and other.end >= call.end for other in captured_calls)]
    for call in reversed(outer):
        if call.args and re.search(rf'\b{re.escape(actor)}\b', call.args[0]):
            token = f"__CAPTURED_{len(saved)}__"
            saved.append(call.raw)
            expression = expression[:call.start] + token + expression[call.end:]
    expression = re.sub(rf"\b{re.escape(actor)}\b(?:\.([A-Za-z][A-Za-z0-9_]*))?", lambda m: f"Player Variable({frozen}, {m.group(1)})" if m.group(1) else frozen, expression)
    for index, original in enumerate(saved):
        expression = expression.replace(f"__CAPTURED_{index}__", original)
    return expression


def persistent(text: str) -> str:
    calls = [call for name in NATIVE_PERSISTENT for call in validator.iter_calls(text, name)]
    for call in sorted(calls, key=lambda item: item.start, reverse=True):
        bound = call.raw
        # A private HUD is evaluated by its sole, frozen viewer. Its live text
        # and colour can therefore read Local Player without another capture
        # at every field reference. Public resources retain explicit owners.
        if call.name == "Create HUD Text" and call.args[0].strip() == ACTOR:
            values = list(call.args)
            values[0] = f"Evaluate Once({ACTOR})"
            for index in range(1, len(values)):
                values[index] = re.sub(rf"\b{re.escape(ACTOR)}\.([A-Za-z][A-Za-z0-9_]*)", lambda m: f"Player Variable(Local Player, {m.group(1)})", values[index])
                values[index] = re.sub(rf"\b{re.escape(ACTOR)}\b", "Local Player", values[index])
            bound = "Create HUD Text(" + ", ".join(values) + ")"
        for actor in (ACTOR, "Global.ActivePlayer", "Global.ObjectiveIconPlayer", "Global.CameraPlayer"):
            bound = capture(bound, actor)
        text = text[:call.start] + bound + text[call.end:]
    return text


def subrule(name: str, target: str, actions: str) -> str:
    body = actions.strip("\n")
    return f'rule("{name}")\n{{\n\tevent\n\t{{\n\t\tSubroutine;\n\t\t{target};\n\t}}\n\n\tactions\n\t{{\n{body}\n\t}}\n}}'


def actions(rule: validator.Rule) -> str:
    value = validator.rule_block(rule, "actions")
    assert value is not None
    return value


def controller_name(rule: validator.Rule) -> str:
    return "Controller" + prefix(rule).replace("-", "").capitalize()


def state_controller(rule: validator.Rule, index: int) -> str:
    p = prefix(rule)
    entry = actor_text(conjunction(validator.rule_block(rule, "conditions")))
    if p not in {'01a', '01b', '02', '03c', '03f', '03g', '03h', '18i', '18j'}:
        # The human branch in ProcessGlobalController and its initial existence
        # guard prove these facts once for the whole batch of controllers.
        conditions = [item.strip() for item in validator.split_top_level(validator.rule_block(rule, 'conditions') or '', ';') if item.strip()]
        proven = {'Global.IsReady == True', 'Event Player.IsHuman == True', 'Event Player.IsAutomaticBot == False', 'Is Dummy Bot(Event Player) == False', 'Entity Exists(Event Player) == True'}
        entry = actor_text(conjunction(';'.join(item for item in conditions if item not in proven)))
    code = persistent(actor_text(actions(rule)))
    if p == "01a":
        # Cancel human held-input continuations; serial lifecycle phases live globally.
        code = code.replace("\t\tIf(Entity Exists(" + ACTOR + ") == True);\n\t\t\tStop Chasing Player Variable(" + ACTOR + ", ObjectiveIconPosition);\n\t\tEnd;\n", "")
        code += f"\n\t\t{TIME}[36] = {STATE}[36];\n\t\t{STATE} = Empty Array;\n\t\t{STATE}[36] = {TIME}[36];\n"
        code += f"\t\t{TIME} = Empty Array;\n"
        code += f"\t\tIf(Global.TeamCyclePhaseOwner == {ACTOR});\n\t\t\tGlobal.TeamCyclePhaseOwner = Null;\n\t\t\tGlobal.TeamCyclePhase = 0;\n\t\tEnd;\n"
        return subrule(rule.name, controller_name(rule), f"\t\tAbort If(({entry}) == False);\n" + code)
    if p == "01b":
        waits = list(validator.iter_calls(code, "Wait"))
        assert len(waits) == 2 and all(call.args[0] == "0.050" for call in waits)
        pieces = [code[:waits[0].start], code[waits[0].end:waits[1].start], code[waits[1].end:]]
        pieces = [part.lstrip(";\n\t") for part in pieces]
        pieces = [re.sub(r'(?m)^\s*Abort If\([^\n]*\);\s*', '', part) for part in pieces]
        body = f"\t\tAbort If(({entry}) == False);\n"
        body += f"\t\tIf(Global.TeamCyclePhaseOwner != {ACTOR});\n\t\t\tGlobal.TeamCyclePhaseOwner = {ACTOR};\n\t\t\tGlobal.TeamCyclePhase = 0;\n\t\t\tGlobal.TeamCyclePhaseTime = 0;\n\t\tEnd;\n"
        body += "\t\tAbort If(Total Time Elapsed < Global.TeamCyclePhaseTime);\n"
        for phase, part in enumerate(pieces):
            body += f"\t\t{'If' if phase == 0 else 'Else If'}(Global.TeamCyclePhase == {phase});\n\t\t\t" + part.strip() + "\n"
            body += f"\t\t\tGlobal.TeamCyclePhase = {phase + 1};\n"
            if phase < 2:
                body += "\t\t\tGlobal.TeamCyclePhaseTime = Total Time Elapsed + 0.050;\n"
        body += "\t\tEnd;\n"
        body += f"\t\tIf(Global.TeamCyclePhase == 3);\n\t\t\tGlobal.TeamCyclePhaseOwner = Null;\n\t\t\tGlobal.TeamCyclePhase = 0;\n\t\tEnd;\n"
        return subrule(rule.name, controller_name(rule), body)
    if p == "02":
        wait = next(iter(validator.iter_calls(code, "Wait")))
        cached_start = code.index("\t\tIf(And(" + ACTOR + ".WasPrepared")
        # Known nested IgnoreCondition split. Keep the original guards and tail.
        cached_end = validator.matching_parenthesis(code, code.index("(", cached_start)) + 1
        cached_condition = code[code.index("(", cached_start) + 1:cached_end - 1]
        before = code[:cached_start]
        after_wait = code[wait.end:].lstrip(";\n\t")
        stop = f"Stop Forcing Dummy Bot Name({ACTOR});\n\t\tEnd;"
        stop_index = after_wait.index(stop) + len(stop)
        resumed = after_wait[:stop_index].rsplit("\n\t\tEnd;", 1)[0]
        tail = after_wait[stop_index:]
        pre_wait = code[cached_end:wait.start]
        forcing_start = pre_wait.index("Start Forcing Dummy Bot Name(")
        forcing = pre_wait[forcing_start:].strip()
        body = f"\t\tIf({STATE}[{index}] == 2);\n\t\t\tAbort If(Total Time Elapsed < {TIME}[{index}]);\n\t\t\tIf(Or({ACTOR}.LastTeam != Team Of({ACTOR}), {ACTOR}.TeamCycleTargetTeam != Team Of({ACTOR})));\n\t\t\t\tStop Forcing Dummy Bot Name({ACTOR});\n\t\t\t\t{ACTOR}.IsClassified = False;\n\t\t\t\t{STATE}[{index}] = 0;\n\t\t\t\tAbort;\n\t\t\tEnd;\n\t\t\t{STATE}[{index}] = 1;\n\t\t\t" + resumed.strip() + f"\n\t\t\t{STATE}[{index}] = 3;\n"
        body += f"\t\tElse;\n\t\t\tAbort If(({entry}) == False);\n" + before
        body += f"\t\t\tIf({cached_condition});\n\t\t\t\t{STATE}[{index}] = 3;\n\t\t\tElse;\n\t\t\t\t{forcing}\n\t\t\t\t{STATE}[{index}] = 2;\n\t\t\t\t{TIME}[{index}] = Total Time Elapsed + 0.016;\n\t\t\tEnd;\n\t\tEnd;\n"
        tail = tail.replace(f'{ACTOR}.HudSlot = First Of(Global.AvailableHudSlots);', f'{ACTOR}.HudSlot = First Of(Global.AvailableHudSlots);\n\t\tGlobal.MissingHudDeadlines[{ACTOR}.HudSlot] = 0;')
        body += f"\t\tIf({STATE}[{index}] == 3);\n\t\t\t{STATE}[{index}] = 0;\n" + tail + "\n\t\tEnd;\n"
        return subrule(rule.name, controller_name(rule), body)
    waits = list(validator.iter_calls(code, "Wait"))
    if waits:
        assert p in {"05", "12c"} and len(waits) == 1
        wait = waits[0]
        assert wait.args == ("0.500", "Abort When False")
        pre = code[:wait.start]
        post = code[wait.end:].lstrip(";\n\t")
        body = f"\t\tIf(({entry}) == False);\n\t\t\t{TIME}[{index}] = 0;\n\t\t\tAbort;\n\t\tEnd;\n"
        body += f"\t\tIf({TIME}[{index}] == 0);\n" + pre + f"\t\t\t{TIME}[{index}] = Total Time Elapsed + 0.500;\n\t\t\tAbort;\n\t\tEnd;\n"
        body += f"\t\tAbort If(Total Time Elapsed < {TIME}[{index}]);\n\t\t{TIME}[{index}] = 0;\n\t\t" + post
        return subrule(rule.name, controller_name(rule), body)
    if p in LATCH_PREFIXES:
        body = f"\t\tIf(({entry}) == False);\n\t\t\t{STATE}[{index}] = 0;\n\t\t\tAbort;\n\t\tEnd;\n\t\tAbort If({STATE}[{index}] == 1);\n\t\t{STATE}[{index}] = 1;\n" + code
    else:
        body = f"\t\tAbort If(({entry}) == False);\n" + code
    return subrule(rule.name, controller_name(rule), body)


def event_snapshot(rule: validator.Rule, kind: int) -> str:
    p = prefix(rule)
    data = ["Null"] * 25
    data[0:2] = [str(kind), "Event Player"]
    data[7] = "Total Time Elapsed"
    data[18:23] = ["Hero Of(Event Player)", "Team Of(Event Player)", "Event Player.ControllerState[36]", 'Event Player.IsHuman == True ? Event Player.DisplayName : Custom String("{0}", Event Player)', "Null"]
    if p == "12e":
        data[6] = "Position Of(Event Player)"
    if p == "04":
        data[12:14] = ["Event Player.IsAutomaticBot", "Event Player.LuckVisionText"]
    if p == "17":
        data[2] = "Attacker"
        data[8:12] = ["Event Player.RevengeDeathPending", "Event Player.RevengeClaimant", "And(Event Player.RevengeClaimant != Null, And(Entity Exists(Event Player.RevengeClaimant), Player Variable(Event Player.RevengeClaimant, IsHuman) == True))", "Player Variable(Attacker, IsHuman)"]
        data[17] = "Is Alive(Event Player) == False"
        data[23:25] = ['Player Variable(Event Player.RevengeClaimant, ControllerState)[36]', 'Player Variable(Attacker, ControllerState)[36]']
    if p == "18f":
        data[14] = "Event Player.MenuOpen == False"
    if p == "89i1":
        data[3:6] = ["Victim", "Event Ability", "Event Damage"]
        data[15] = "Or(Has Status(Victim, Phased Out), Or(Has Status(Victim, Unkillable), And(Player Variable(Victim, UnkillableActive), Player Variable(Victim, UnkillableMode) != 0)))"
        data[16] = "Event Player.HudSlot"
        data[22] = "Player Variable(Victim, ControllerState)[36]"
    if p == '04': data = data[:13]
    elif p != '17': data = data[:23] if p == '89i1' else data[:22]
    event = validator.event_block(rule)
    conditions = validator.rule_block(rule, "conditions") or ""
    limit = 192 if p == "89i1" else CAPACITY
    enqueue = f"\t\tIf(Global.EventCount < {limit});\n\t\t\tGlobal.EventQueue[Global.EventQueueTail] = Array(" + ", ".join(data) + ");\n"
    enqueue += f"\t\t\tGlobal.EventQueueTail = (Global.EventQueueTail + 1) % {CAPACITY};\n\t\t\tGlobal.EventCount += 1;\n\t\tElse;\n\t\t\tGlobal.DroppedEventCount += 1;\n\t\tEnd;\n"
    return f'rule("{rule.name}")\n{{\n\tevent\n\t{{{event}\t}}\n\n\tconditions\n\t{{{conditions}\t}}\n\n\tactions\n\t{{\n{enqueue}\t}}\n}}'


def event_worker(rule: validator.Rule) -> str:
    p = prefix(rule)
    code = actor_text(actions(rule))
    code = re.sub(r"\bAttacker\b", f"{RECORD}[2]", code)
    code = re.sub(r"\bVictim\b", f"{RECORD}[3]", code)
    code = code.replace("Event Ability", f"{RECORD}[4]").replace("Event Damage", f"{RECORD}[5]")
    if p == "04":
        # Bot text handles are owned by the global temporary registry; no absent-player reads.
        body = f"\t\tIf({RECORD}[12] == True);\n\t\t\tGlobal.TextCleanupPlayer = {ACTOR};\n\t\t\tCall Subroutine(CleanupOrphanedText);\n\t\tElse;\n\t\t\tGlobal.PendingLeaveCursor = Index Of Array Value(Global.PendingLeaves, Null);\n\t\t\tIf(Global.PendingLeaveCursor < 0);\n\t\t\t\tGlobal.PendingLeaveCursor = Count Of(Global.PendingLeaves);\n\t\t\tEnd;\n\t\t\tIf(Global.PendingLeaveCursor < 24);\n\t\t\t\tGlobal.PendingLeaves[Global.PendingLeaveCursor] = {RECORD};\n\t\t\tElse;\n\t\t\t\tGlobal.DroppedEventCount += 1;\n\t\t\tEnd;\n\t\tEnd;\n"
        return subrule(rule.name + " global", "NativeEvent" + p.capitalize(), body)
    guards = f"\t\tAbort If(Entity Exists({ACTOR}) == False);\n\t\tAbort If({RECORD}[20] != {STATE}[36]);\n\t\tAbort If({RECORD}[21] != ({ACTOR}.IsHuman == True ? {ACTOR}.DisplayName : Custom String(\"{{0}}\", {ACTOR})));\n"
    if p in {'12e', '16a', '17', '18f'}:
        guards += f'\t\tAbort If(Or({ACTOR}.PlayerCycleActive == True, {ACTOR}.LastTeam != Team Of({ACTOR})));\n'
    if p == '89i1':
        guards += f"\t\tAbort If(Or({ACTOR}.LastTeam != Team Of({ACTOR}), {ACTOR}.TeamCycleTargetTeam != Team Of({ACTOR})));\n"
    if p in {"03i", "12e", "18f"}:
        guards += f"\t\tAbort If(Is Alive({ACTOR}) == True);\n"
    if p == "16a":
        guards += f"\t\tAbort If(Hero Of({ACTOR}) != {RECORD}[18]);\n"
    if p == "12e":
        code = code.replace(f"Position Of({ACTOR})", f"{RECORD}[6]")
    if p == "18f":
        code = code.replace(f"{ACTOR}.MenuOpen == False", f"{RECORD}[14]")
    if p == "17":
        code = code.replace(f"If({ACTOR}.RevengeDeathPending == True)", f"If({RECORD}[8] == True)")
        code = code.replace(f"Is Alive({ACTOR}) == False", f"{RECORD}[17] == True")
        code = re.sub(rf"{re.escape(ACTOR)}\.RevengeClaimant(?!\s*=(?!=))", f"{RECORD}[9]", code)
        code = code.replace(f"Player Variable({RECORD}[9], IsHuman) == True", f"{RECORD}[10] == True")
        code = code.replace(f"Player Variable({RECORD}[2], IsHuman) == False", f"{RECORD}[11] == False")
        code = code.replace(f'Entity Exists({RECORD}[9])', f'And(Entity Exists({RECORD}[9]), Player Variable({RECORD}[9], ControllerState)[36] == {RECORD}[23])')
        code = code.replace(f'Abort If({RECORD}[11] == False);', f'Abort If({RECORD}[11] == False);\n\t\tAbort If(Entity Exists({RECORD}[2]) == False);\n\t\tAbort If(Player Variable({RECORD}[2], ControllerState)[36] != {RECORD}[24]);')
    if p == "89i1":
        victim = f"{RECORD}[3]"
        slot = f"{RECORD}[16]"
        guards += f"\t\tAbort If({ACTOR}.HudSlot != {slot});\n\t\tAbort If(Array Contains(Global.SuperPunchPlayers, {ACTOR}) == False);\n"
        code = code.replace(f"{ACTOR}.HudSlot", slot)
        original_if = next(c for c in validator.iter_calls(code, "If") if "Has Status(" in c.raw)
        protected_now = original_if.args[0]
        new_if = f"If(And({RECORD}[15] == False, And(Entity Exists({victim}), And(Has Spawned({victim}), And(Is Alive({victim}), And(Player Variable({victim}, ControllerState)[36] == {RECORD}[22], {protected_now}))))))"
        code = code[:original_if.start] + new_if + code[original_if.end:]
    return subrule(rule.name + " global", "NativeEvent" + p.capitalize(), guards + persistent(code))


def build_english(source: str) -> tuple[str, dict]:
    logical = translate(source)
    rules = validator.extract_rules(logical)
    each = validator.rules_with_event(rules, "Ongoing - Each Player")
    assert len(each) == 36
    callback = [rule for rule in rules if prefix(rule) in EVENT_PREFIXES]
    assert len(callback) == 7
    by_prefix = {prefix(r): r for r in each}
    indices = {prefix(r): i for i, r in enumerate(each)}
    old_globals, old_players, old_subs, _ = validator.declaration_entries(logical)
    targets = [controller_name(r) for r in each] + ["NativeEvent" + p.capitalize() for p in EVENT_PREFIXES] + ["ProcessGlobalController", "ProcessGlobalEventQueue", "ProcessGlobalLeaves", "ProcessVisibleIcons"]
    assert len(old_subs) + len(targets) <= 128
    # Allocate backend fields after the actual logical declarations. UI changes
    # may compact any namespace; no fixed slot or textual anchor is an ABI.
    def namespace(entries, additions, indent):
        names = [entry.name for entry in entries] + list(additions)
        assert len(names) == len(set(names)) and len(names) <= 128
        return ''.join(f'{indent}{index}: {name}\n' for index, name in enumerate(names))
    header = ('variables\n{\n\tglobal:\n' + namespace(old_globals, GLOBALS, '\t\t')
              + '\tplayer:\n' + namespace(old_players, ('ControllerState', 'ControllerTimes'), '\t\t')
              + '}\nsubroutines\n{\n' + namespace(old_subs, targets, '\t') + '}\n\n')

    lowered: list[str] = []
    for original in rules:
        p = prefix(original)
        if original in each:
            lowered.append(state_controller(original, indices[p]))
            continue
        if original in callback:
            lowered.extend([event_snapshot(original, EVENT_PREFIXES.index(p)), event_worker(original)])
            continue
        body = original.body
        if validator.event_type(original) == "Subroutine":
            body = persistent(actor_text(body))
        if p == '93c':
            marker = 'Global.LeavingDebtIndex = Global.PlayerHudSlots[Global.CleanupPlayerIndex];'
            body = body.replace(marker, marker + '\n\t\tGlobal.MissingHudDeadlines[Global.LeavingDebtIndex] = 0;')
        if p == '89a':
            # Losing a lifecycle reservation also invalidates its suspended
            # phase, including team flips before the first roster registration.
            body = body.replace('Global.TeamCyclePlayer = Null;', 'Global.TeamCyclePlayer = Null;\n\t\tGlobal.TeamCyclePhaseOwner = Null;')
        if p == "00":
            init = "".join(f"\t\tGlobal.{name} = {'Empty Array' if name in {'EventQueue','PendingLeaves','MissingHudDeadlines','VisibleIconChoices'} else 'Null' if name in {'TriggerPlayer','TeamCyclePhaseOwner','ActiveEvent'} else '0'};\n" for name in GLOBALS)
            body = body.replace("\t\tGlobal.IsReady = True;", init + "\t\tGlobal.IsReady = True;")
        if p == "04g":
            # Existing global loop remains the sole clock. Events drain before menu/gameplay work.
            body = body.replace('\t\tGlobal.PlayerListSnapshot = All Players(All Teams);\n', '')
            body = body.replace("\t\tGlobal.SchedulerStep =", "\t\tGlobal.PlayerListSnapshot = All Players(All Teams);\n\t\tCall Subroutine(ProcessGlobalEventQueue);\n\t\tCall Subroutine(ProcessGlobalLeaves);\n\t\tGlobal.SchedulerStep =", 1)
            body = body.replace('Has Spawned(Global.TeamCyclePlayer) == False', 'Or(Has Spawned(Global.TeamCyclePlayer) == False, Array Contains(Global.PlayerListSnapshot, Global.TeamCyclePlayer) == False)')
            body = body.replace('Global.TeamCyclePlayer = Null;', 'Global.TeamCyclePlayer = Null;\n\t\tGlobal.TeamCyclePhaseOwner = Null;')
            body = body.replace("\t\t\tGlobal.ActivePlayer = Global.PlayerListSnapshot[Global.SchedulerPlayerIndex];", "\t\t\tGlobal.ActivePlayer = Global.PlayerListSnapshot[Global.SchedulerPlayerIndex];\n\t\t\tGlobal.TriggerPlayer = Global.ActivePlayer;\n\t\t\tCall Subroutine(ProcessGlobalController);")
            body = body.replace("\t\tGlobal.ActivePlayer = Null;", "\t\tGlobal.TriggerPlayer = Null;\n\t\tGlobal.ActivePlayer = Null;")
            body = body.replace('\t\tIf(Global.VoteRecountNeeded == True);', '\t\tCall Subroutine(ProcessVisibleIcons);\n\t\tIf(Global.VoteRecountNeeded == True);')
        lowered.append(persistent(body))

    # Group calls by human/bot state. Inactive human menu/Travel groups are skipped.
    controls = f"\t\tAbort If(Entity Exists({ACTOR}) == False);\n\t\tIf(Count Of({STATE}) < 37);\n\t\t\tGlobal.ControllerGeneration += 1;\n\t\t\t{STATE} = Empty Array;\n\t\t\t{STATE}[36] = Global.ControllerGeneration;\n\t\t\t{TIME} = Empty Array;\n\t\tEnd;\n"
    controls += f"\t\tCall Subroutine({controller_name(by_prefix['01a'])});\n\t\tCall Subroutine({controller_name(by_prefix['01b'])});\n\t\tCall Subroutine({controller_name(by_prefix['02'])});\n"
    controls += f"\t\tIf(Or(Is Dummy Bot({ACTOR}), {ACTOR}.IsAutomaticBot));\n"
    for p in ["03c", "03f", "03g", "03h", "18i", "18j"]:
        controls += f"\t\t\tCall Subroutine({controller_name(by_prefix[p])});\n"
    controls += f"\t\tElse If(And({ACTOR}.IsHuman == True, And(Is Dummy Bot({ACTOR}) == False, {ACTOR}.IsAutomaticBot == False)));\n"
    menu_group = {'05c', '05d', '05e', '05f', '06', '08', '10', '11'}
    travel_group = {'19a', '19b', '19c', '19d', '19e', '19g'}
    for original in each:
        p = prefix(original)
        if p in {"01a", "01b", "02", "03c", "03f", "03g", "03h"}:
            continue
        if p == '05c':
            controls += f'\t\t\tIf(Or({ACTOR}.MenuOpen == True, Or({ACTOR}.MenuCommand != 0, {ACTOR}.MenuInputLocked == True)));\n'
            for member in [item for item in each if prefix(item) in menu_group]:
                controls += f'\t\t\t\tCall Subroutine({controller_name(member)});\n'
            controls += '\t\t\tElse;\n'
            for member in ('06', '08', '10', '11'):
                controls += f'\t\t\t\t{STATE}[{indices[member]}] = 0;\n'
            controls += '\t\t\tEnd;\n'
            continue
        if p in menu_group: continue
        if p == '19a':
            controls += f'\t\t\tIf({ACTOR}.CrouchTravelActive == True);\n'
            for member in [item for item in each if prefix(item) in travel_group]:
                controls += f'\t\t\t\tCall Subroutine({controller_name(member)});\n'
            controls += '\t\t\tEnd;\n'
            controls += f'\t\t\tIf({ACTOR}.CrouchTravelActive == False);\n'
            for member in ('19c', '19e'):
                controls += f'\t\t\t\t{STATE}[{indices[member]}] = 0;\n'
            controls += '\t\t\tEnd;\n'
            continue
        if p in travel_group: continue
        if p in {'19f', '19h'}:
            controls += f'\t\t\tIf({ACTOR}.TravelAttachmentActive == True);\n\t\t\t\tCall Subroutine({controller_name(original)});\n\t\t\tEnd;\n'
            continue
        if p in {'18i', '18j'}:
            controls += f'\t\t\tIf(Or(Count Of(Global.LuckVisionViewers) > 0, And({ACTOR}.LuckVisionText != Null, {ACTOR}.LuckVisionText != 0)));\n\t\t\t\tCall Subroutine({controller_name(original)});\n\t\t\tEnd;\n'
            continue
        controls += f"\t\t\tCall Subroutine({controller_name(original)});\n"
    controls += "\t\tEnd;\n"
    lowered.append(subrule("04h - Subroutine: Control players from global context", "ProcessGlobalController", controls))

    drain = "\t\tGlobal.InitialEventCount = Global.EventCount;\n\t\tFor Global Variable(EventCursor, 0, Global.InitialEventCount, 1);\n"
    drain += f"\t\t\tGlobal.ActiveEvent = Global.EventQueue[Global.EventQueueHead];\n\t\t\tGlobal.EventQueue[Global.EventQueueHead] = Null;\n\t\t\tGlobal.EventQueueHead = (Global.EventQueueHead + 1) % {CAPACITY};\n\t\t\tGlobal.EventCount -= 1;\n\t\t\tGlobal.TriggerPlayer = Global.ActiveEvent[1];\n"
    for kind, p in enumerate(EVENT_PREFIXES):
        drain += f"\t\t\t{'If' if kind == 0 else 'Else If'}(Global.ActiveEvent[0] == {kind});\n\t\t\t\tCall Subroutine(NativeEvent{p.capitalize()});\n"
    drain += "\t\t\tEnd;\n\t\tEnd;\n\t\tGlobal.TriggerPlayer = Null;\n\t\tGlobal.ActiveEvent = Null;\n"
    lowered.append(subrule("04i - Subroutine: Drain the native event queue", "ProcessGlobalEventQueue", drain))

    leaves = "\t\tFor Global Variable(PendingLeaveCursor, 0, Count Of(Global.PendingLeaves), 1);\n\t\t\tIf(Global.PendingLeaves[Global.PendingLeaveCursor] != Null);\n\t\t\t\tGlobal.ActiveEvent = Global.PendingLeaves[Global.PendingLeaveCursor];\n\t\t\t\tIf(Total Time Elapsed >= Global.ActiveEvent[7] + 0.500);\n\t\t\t\t\tGlobal.TriggerPlayer = Global.ActiveEvent[1];\n\t\t\t\t\tGlobal.PendingLeaves[Global.PendingLeaveCursor] = Null;\n\t\t\t\t\tIf(Entity Exists(Global.TriggerPlayer) == False);\n\t\t\t\t\t\tCall Subroutine(CleanupPlayer);\n\t\t\t\t\tEnd;\n\t\t\t\tEnd;\n\t\t\tEnd;\n\t\tEnd;\n"
    leaves += "\t\tIf(Global.SchedulerStep % 20 == 0);\n\t\t\tFor Global Variable(MissingPlayerCursor, Count Of(Global.HumanPlayers) - 1, -1, -1);\n\t\t\t\tGlobal.TriggerPlayer = Global.HumanPlayers[Global.MissingPlayerCursor];\n\t\t\t\tIf(Entity Exists(Global.TriggerPlayer));\n\t\t\t\t\tGlobal.MissingHudDeadlines[Global.PlayerHudSlots[Global.MissingPlayerCursor]] = 0;\n\t\t\t\tElse If(Global.MissingHudDeadlines[Global.PlayerHudSlots[Global.MissingPlayerCursor]] == 0);\n\t\t\t\t\tGlobal.MissingHudDeadlines[Global.PlayerHudSlots[Global.MissingPlayerCursor]] = Total Time Elapsed + 0.500;\n\t\t\t\tElse If(Total Time Elapsed >= Global.MissingHudDeadlines[Global.PlayerHudSlots[Global.MissingPlayerCursor]]);\n\t\t\t\t\tCall Subroutine(CleanupPlayer);\n\t\t\t\tEnd;\n\t\t\tEnd;\n\t\tEnd;\n\t\tGlobal.ActiveEvent = Null;\n\t\tGlobal.TriggerPlayer = Null;\n"
    # Spectators can retain a native entity while no longer belonging to either
    # playing team. Treat that membership loss as departure for global resources.
    present = 'And(Entity Exists(Global.TriggerPlayer), Array Contains(Global.PlayerListSnapshot, Global.TriggerPlayer))'
    leaves = leaves.replace('Entity Exists(Global.TriggerPlayer) == False', f'{present} == False').replace('If(Entity Exists(Global.TriggerPlayer))', f'If({present})')
    lowered.append(subrule("04j - Subroutine: Reconcile departed players from global context", "ProcessGlobalLeaves", leaves))
    icon_cache = '\t\tFor Global Variable(ObjectiveIconIndex, 0, 12, 1);\n\t\t\tGlobal.ObjectiveIconPlayer = Global.ObjectiveIconOwners[Global.ObjectiveIconIndex];\n\t\t\tGlobal.VisibleIconChoices[Global.ObjectiveIconIndex] = And(Entity Exists(Global.ObjectiveIconPlayer), And(Array Contains(Global.HumanPlayers, Global.ObjectiveIconPlayer), And(Global.ObjectiveIconPlayer.IsHuman == True, Distance Between(Objective Position(Objective Index), Vector(0, 0, 0)) > 0.100))) ? Global.ObjectiveIconPlayer.IconIndex : 0;\n\t\tEnd;\n\t\tGlobal.ObjectiveIconPlayer = Null;\n'
    lowered.append(subrule('04k - Subroutine: Cache visible objective icon choices', 'ProcessVisibleIcons', icon_cache))
    output = compact_booleans(compact_unused_constants(compact_fixed_pools(compact_icon_visibility(compact_palette(header + "\n\n".join(lowered) + "\n")))))
    output = number_runtime_rules(output)
    return output, {"controllers": {prefix(r): {"target": controller_name(r), "index": indices[prefix(r)]} for r in each}, "callbacks": {p: i for i, p in enumerate(EVENT_PREFIXES)}, "capacity": CAPACITY, "latches": sorted(LATCH_PREFIXES)}


def number_runtime_rules(text: str) -> str:
    """Give the final import a unique, consecutive display order from zero.

    Logical rule IDs remain compiler inputs; native subroutine declarations and
    controller targets are untouched by this presentation-only final pass.
    """
    rules = validator.extract_rules(text)
    for index, rule in reversed(list(enumerate(rules))):
        _, separator, title = rule.name.partition(" - ")
        if not separator or not title:
            raise ValueError(f"runtime rule has no descriptive title: {rule.name}")
        replacement = rule.body.replace('rule("' + rule.name + '")',
                                        'rule("' + str(index) + ' - ' + title + '")', 1)
        text = text[:rule.start] + replacement + text[rule.end:]
    return text


def build(source: str) -> str:
    runtime, _ = build_english(source)
    return runtime


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=REPO / "source" / "ruang_irama.en-US.source")
    parser.add_argument("--output", type=Path, default=REPO / 'workshop' / 'ruang_irama.en-US.workshop')
    parser.add_argument('--reference', type=Path, default=REPO / 'tests' / 'fixtures' / 'global_runtime_reference.txt')
    parser.add_argument('--check', action='store_true', help='Verify both generated files without writing them.')
    args = parser.parse_args()
    source = args.source.read_text(encoding="utf-8")
    english, _ = build_english(source)
    runtime = english
    parsed = validator.extract_rules(english)
    checks = validator.Checks()
    validator.validate_rule_grammar(checks, parsed)
    checks.finish()
    assert not validator.rules_with_event(parsed, "Ongoing - Each Player")
    assert not validator.global_player_context_errors(parsed)
    assert len(list(validator.iter_calls(english, "Wait"))) == 1
    report = clipboard.check_text(runtime, "en-US")
    reference = runtime
    if args.check:
        if args.output.read_text(encoding='utf-8') != runtime or args.reference.read_text(encoding='utf-8') != reference:
            raise SystemExit('Generated runtime is stale; run tools/build_global_runtime.py.')
        print('OK - both global runtime artifacts are current.')
    else:
        args.output.write_text(runtime, encoding='utf-8', newline='\n')
        args.reference.write_text(reference, encoding='utf-8', newline='\n')
        print(f"Generated {args.output}; {len(parsed)} rules, global-only controllers, sole central Wait.")
    print(f"Preflight: {report.structural_units} proxy, largest {report.largest_structural_rule.structural_units}.")


if __name__ == "__main__":
    main()
