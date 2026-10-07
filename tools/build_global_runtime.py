"""Deterministic lowering of the logical Workshop into one global runtime.

The explicit behavioral input is lowered into the Italian import and its
English runtime reference. --check verifies both deterministic artifacts;
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

ACTOR = "Global.PemainPemicu"
RECORD = "Global.PeristiwaAktif"
STATE = f"{ACTOR}.StatusPengatur"
TIME = f"{ACTOR}.WaktuPengatur"
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
    "PemainPemicu", "GenerasiPengatur", "FaseSiklusGlobal", "WaktuFaseSiklusGlobal", "PemilikFaseSiklus",
    "AntreanPeristiwa", "KepalaPeristiwa", "EkorPeristiwa", "JumlahPeristiwa", "JumlahPeristiwaAwal", "KursorPeristiwa",
    "PeristiwaAktif", "PeristiwaTerlewat", "KeluarTertunda", "KursorKeluarTertunda", "WaktuHilangHUD", "KursorDaftarHilang", "PilihanIkonTerlihat",
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
    if node.kind == 'unary': return node.value + '(' + _emit(node.children[0]) + ')'
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
    """Factor the identical name-colour blend shared by sixteen menu pages."""
    rule = next(item for item in validator.extract_rules(text) if prefix(item) == '91k')
    call = list(validator.iter_calls(rule.body, 'Chase Player Variable Over Time'))[-1]
    # Palette values come from the logical expression, not a second manual list.
    vectors = [item.raw for item in validator.iter_calls(call.args[2], 'Vector')]
    assert len(vectors) == 15
    owner = f'Evaluate Once({ACTOR})'
    index = f'(Player Variable({owner}, HalamanMenu) == -1 ? Player Variable({owner}, KursorUtama) : Player Variable({owner}, HalamanMenu))'
    color = f'Global.DaftarWarnaRGB[Player Variable({owner}, IndeksWarna)]'
    palette = 'Array(Vector(0, 0, 0), ' + ', '.join(vectors) + ')'
    args = list(call.args)
    args[2] = f'{index} == 0 ? Global.DaftarWarnaRGB[Player Variable({owner}, KursorWarna)] : And({index} >= 1, {index} <= 15) ? {color} * 0.680 + {palette}[{index}] * 0.320 : {color}'
    changed = 'Chase Player Variable Over Time(' + ', '.join(args) + ')'
    body = rule.body[:call.start] + changed + rule.body[call.end:]
    return text[:rule.start] + body + text[rule.end:]


def compact_icon_visibility(text: str) -> str:
    """Keep per-frame entity validity; share the other visibility predicates."""
    rule = next(item for item in validator.extract_rules(text) if prefix(item) == '89e')
    body = rule.body
    for call in reversed(list(validator.iter_calls(body, 'Create Icon'))):
        args = list(call.args)
        selected = re.search(r'IndeksIkon\) == (\d+)', args[0])
        assert selected is not None
        args[0] = f'And(Entity Exists(Evaluate Once(Global.PemainIkonPilar)), Global.PilihanIkonTerlihat[Evaluate Once(Global.IndeksIkonPilar)] == {selected[1]}) ? All Players(All Teams) : Empty Array'
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
        owner = 'Global.SlotHUDTersedia' if len(values) == 12 else 'Global.PemilikTeksSementara' if len(values) == 24 else ''
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
        for actor in (ACTOR, "Global.PemainAktif", "Global.PemainIkonPilar"):
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
    return "Pengatur" + prefix(rule).replace("-", "").capitalize()


def state_controller(rule: validator.Rule, index: int) -> str:
    p = prefix(rule)
    entry = actor_text(conjunction(validator.rule_block(rule, "conditions")))
    if p not in {'01a', '01b', '02', '03c', '03f', '03g', '03h', '18i', '18j'}:
        # The human branch in ProsesPengaturGlobal and its initial existence
        # guard prove these facts once for the whole batch of controllers.
        conditions = [item.strip() for item in validator.split_top_level(validator.rule_block(rule, 'conditions') or '', ';') if item.strip()]
        proven = {'Global.Siap == True', 'Event Player.Manusia == True', 'Event Player.BotOtomatis == False', 'Is Dummy Bot(Event Player) == False', 'Entity Exists(Event Player) == True'}
        entry = actor_text(conjunction(';'.join(item for item in conditions if item not in proven)))
    code = persistent(actor_text(actions(rule)))
    if p == "01a":
        # Cancel human held-input continuations; serial lifecycle phases live globally.
        code = code.replace("\t\tIf(Entity Exists(" + ACTOR + ") == True);\n\t\t\tStop Chasing Player Variable(" + ACTOR + ", PosisiIkonPilar);\n\t\tEnd;\n", "")
        code += f"\n\t\t{TIME}[36] = {STATE}[36];\n\t\t{STATE} = Empty Array;\n\t\t{STATE}[36] = {TIME}[36];\n"
        code += f"\t\t{TIME} = Empty Array;\n"
        code += f"\t\tIf(Global.PemilikFaseSiklus == {ACTOR});\n\t\t\tGlobal.PemilikFaseSiklus = Null;\n\t\t\tGlobal.FaseSiklusGlobal = 0;\n\t\tEnd;\n"
        return subrule(rule.name, controller_name(rule), f"\t\tAbort If(({entry}) == False);\n" + code)
    if p == "01b":
        waits = list(validator.iter_calls(code, "Wait"))
        assert len(waits) == 2 and all(call.args[0] == "0.050" for call in waits)
        pieces = [code[:waits[0].start], code[waits[0].end:waits[1].start], code[waits[1].end:]]
        pieces = [part.lstrip(";\n\t") for part in pieces]
        pieces = [re.sub(r'(?m)^\s*Abort If\([^\n]*\);\s*', '', part) for part in pieces]
        body = f"\t\tAbort If(({entry}) == False);\n"
        body += f"\t\tIf(Global.PemilikFaseSiklus != {ACTOR});\n\t\t\tGlobal.PemilikFaseSiklus = {ACTOR};\n\t\t\tGlobal.FaseSiklusGlobal = 0;\n\t\t\tGlobal.WaktuFaseSiklusGlobal = 0;\n\t\tEnd;\n"
        body += "\t\tAbort If(Total Time Elapsed < Global.WaktuFaseSiklusGlobal);\n"
        for phase, part in enumerate(pieces):
            body += f"\t\t{'If' if phase == 0 else 'Else If'}(Global.FaseSiklusGlobal == {phase});\n\t\t\t" + part.strip() + "\n"
            body += f"\t\t\tGlobal.FaseSiklusGlobal = {phase + 1};\n"
            if phase < 2:
                body += "\t\t\tGlobal.WaktuFaseSiklusGlobal = Total Time Elapsed + 0.050;\n"
        body += "\t\tEnd;\n"
        body += f"\t\tIf(Global.FaseSiklusGlobal == 3);\n\t\t\tGlobal.PemilikFaseSiklus = Null;\n\t\t\tGlobal.FaseSiklusGlobal = 0;\n\t\tEnd;\n"
        return subrule(rule.name, controller_name(rule), body)
    if p == "02":
        wait = next(iter(validator.iter_calls(code, "Wait")))
        cached_start = code.index("\t\tIf(And(" + ACTOR + ".PernahDisiapkan")
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
        body = f"\t\tIf({STATE}[{index}] == 2);\n\t\t\tAbort If(Total Time Elapsed < {TIME}[{index}]);\n\t\t\tIf(Or({ACTOR}.TimTerakhir != Team Of({ACTOR}), {ACTOR}.TimSiklusTarget != Team Of({ACTOR})));\n\t\t\t\tStop Forcing Dummy Bot Name({ACTOR});\n\t\t\t\t{ACTOR}.SudahDiperiksa = False;\n\t\t\t\t{STATE}[{index}] = 0;\n\t\t\t\tAbort;\n\t\t\tEnd;\n\t\t\t{STATE}[{index}] = 1;\n\t\t\t" + resumed.strip() + f"\n\t\t\t{STATE}[{index}] = 3;\n"
        body += f"\t\tElse;\n\t\t\tAbort If(({entry}) == False);\n" + before
        body += f"\t\t\tIf({cached_condition});\n\t\t\t\t{STATE}[{index}] = 3;\n\t\t\tElse;\n\t\t\t\t{forcing}\n\t\t\t\t{STATE}[{index}] = 2;\n\t\t\t\t{TIME}[{index}] = Total Time Elapsed + 0.016;\n\t\t\tEnd;\n\t\tEnd;\n"
        tail = tail.replace(f'{ACTOR}.UrutanHUD = First Of(Global.SlotHUDTersedia);', f'{ACTOR}.UrutanHUD = First Of(Global.SlotHUDTersedia);\n\t\tGlobal.WaktuHilangHUD[{ACTOR}.UrutanHUD] = 0;')
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
    data[18:23] = ["Hero Of(Event Player)", "Team Of(Event Player)", "Event Player.StatusPengatur[36]", 'Event Player.Manusia == True ? Event Player.NamaTampilan : Custom String("{0}", Event Player)', "Null"]
    if p == "12e":
        data[6] = "Position Of(Event Player)"
    if p == "04":
        data[12:14] = ["Event Player.BotOtomatis", "Event Player.TeksVisiNasib"]
    if p == "17":
        data[2] = "Attacker"
        data[8:12] = ["Event Player.KematianBalasDendam", "Event Player.PenagihBalasDendam", "And(Event Player.PenagihBalasDendam != Null, And(Entity Exists(Event Player.PenagihBalasDendam), Player Variable(Event Player.PenagihBalasDendam, Manusia) == True))", "Player Variable(Attacker, Manusia)"]
        data[17] = "Is Alive(Event Player) == False"
        data[23:25] = ['Player Variable(Event Player.PenagihBalasDendam, StatusPengatur)[36]', 'Player Variable(Attacker, StatusPengatur)[36]']
    if p == "18f":
        data[14] = "Event Player.MenuTerbuka == False"
    if p == "89i1":
        data[3:6] = ["Victim", "Event Ability", "Event Damage"]
        data[15] = "Or(Has Status(Victim, Phased Out), Or(Has Status(Victim, Unkillable), And(Player Variable(Victim, KebalAktif), Player Variable(Victim, ModeKebal) != 0)))"
        data[16] = "Event Player.UrutanHUD"
        data[22] = "Player Variable(Victim, StatusPengatur)[36]"
    if p == '04': data = data[:13]
    elif p != '17': data = data[:23] if p == '89i1' else data[:22]
    event = validator.event_block(rule)
    conditions = validator.rule_block(rule, "conditions") or ""
    limit = 192 if p == "89i1" else CAPACITY
    enqueue = f"\t\tIf(Global.JumlahPeristiwa < {limit});\n\t\t\tGlobal.AntreanPeristiwa[Global.EkorPeristiwa] = Array(" + ", ".join(data) + ");\n"
    enqueue += f"\t\t\tGlobal.EkorPeristiwa = (Global.EkorPeristiwa + 1) % {CAPACITY};\n\t\t\tGlobal.JumlahPeristiwa += 1;\n\t\tElse;\n\t\t\tGlobal.PeristiwaTerlewat += 1;\n\t\tEnd;\n"
    return f'rule("{rule.name}")\n{{\n\tevent\n\t{{{event}\t}}\n\n\tconditions\n\t{{{conditions}\t}}\n\n\tactions\n\t{{\n{enqueue}\t}}\n}}'


def event_worker(rule: validator.Rule) -> str:
    p = prefix(rule)
    code = actor_text(actions(rule))
    code = re.sub(r"\bAttacker\b", f"{RECORD}[2]", code)
    code = re.sub(r"\bVictim\b", f"{RECORD}[3]", code)
    code = code.replace("Event Ability", f"{RECORD}[4]").replace("Event Damage", f"{RECORD}[5]")
    if p == "04":
        # Bot text handles are owned by the global temporary registry; no absent-player reads.
        body = f"\t\tIf({RECORD}[12] == True);\n\t\t\tGlobal.PemainTeksPembersihan = {ACTOR};\n\t\t\tCall Subroutine(BersihkanTeksYatim);\n\t\tElse;\n\t\t\tGlobal.KursorKeluarTertunda = Index Of Array Value(Global.KeluarTertunda, Null);\n\t\t\tIf(Global.KursorKeluarTertunda < 0);\n\t\t\t\tGlobal.KursorKeluarTertunda = Count Of(Global.KeluarTertunda);\n\t\t\tEnd;\n\t\t\tIf(Global.KursorKeluarTertunda < 24);\n\t\t\t\tGlobal.KeluarTertunda[Global.KursorKeluarTertunda] = {RECORD};\n\t\t\tElse;\n\t\t\t\tGlobal.PeristiwaTerlewat += 1;\n\t\t\tEnd;\n\t\tEnd;\n"
        return subrule(rule.name + " global", "Peristiwa" + p.capitalize(), body)
    guards = f"\t\tAbort If(Entity Exists({ACTOR}) == False);\n\t\tAbort If({RECORD}[20] != {STATE}[36]);\n\t\tAbort If({RECORD}[21] != ({ACTOR}.Manusia == True ? {ACTOR}.NamaTampilan : Custom String(\"{{0}}\", {ACTOR})));\n"
    if p in {'12e', '16a', '17', '18f'}:
        guards += f'\t\tAbort If(Or({ACTOR}.SiklusPemainAktif == True, {ACTOR}.TimTerakhir != Team Of({ACTOR})));\n'
    if p == '89i1':
        guards += f"\t\tAbort If(Or({ACTOR}.TimTerakhir != Team Of({ACTOR}), {ACTOR}.TimSiklusTarget != Team Of({ACTOR})));\n"
    if p in {"03i", "12e", "18f"}:
        guards += f"\t\tAbort If(Is Alive({ACTOR}) == True);\n"
    if p == "16a":
        guards += f"\t\tAbort If(Hero Of({ACTOR}) != {RECORD}[18]);\n"
    if p == "12e":
        code = code.replace(f"Position Of({ACTOR})", f"{RECORD}[6]")
    if p == "18f":
        code = code.replace(f"{ACTOR}.MenuTerbuka == False", f"{RECORD}[14]")
    if p == "17":
        code = code.replace(f"If({ACTOR}.KematianBalasDendam == True)", f"If({RECORD}[8] == True)")
        code = code.replace(f"Is Alive({ACTOR}) == False", f"{RECORD}[17] == True")
        code = re.sub(rf"{re.escape(ACTOR)}\.PenagihBalasDendam(?!\s*=(?!=))", f"{RECORD}[9]", code)
        code = code.replace(f"Player Variable({RECORD}[9], Manusia) == True", f"{RECORD}[10] == True")
        code = code.replace(f"Player Variable({RECORD}[2], Manusia) == False", f"{RECORD}[11] == False")
        code = code.replace(f'Entity Exists({RECORD}[9])', f'And(Entity Exists({RECORD}[9]), Player Variable({RECORD}[9], StatusPengatur)[36] == {RECORD}[23])')
        code = code.replace(f'Abort If({RECORD}[11] == False);', f'Abort If({RECORD}[11] == False);\n\t\tAbort If(Entity Exists({RECORD}[2]) == False);\n\t\tAbort If(Player Variable({RECORD}[2], StatusPengatur)[36] != {RECORD}[24]);')
    if p == "89i1":
        victim = f"{RECORD}[3]"
        slot = f"{RECORD}[16]"
        guards += f"\t\tAbort If({ACTOR}.UrutanHUD != {slot});\n\t\tAbort If(Array Contains(Global.PemainPukulanSuper, {ACTOR}) == False);\n"
        code = code.replace(f"{ACTOR}.UrutanHUD", slot)
        original_if = next(c for c in validator.iter_calls(code, "If") if "Has Status(" in c.raw)
        protected_now = original_if.args[0]
        new_if = f"If(And({RECORD}[15] == False, And(Entity Exists({victim}), And(Has Spawned({victim}), And(Is Alive({victim}), And(Player Variable({victim}, StatusPengatur)[36] == {RECORD}[22], {protected_now}))))))"
        code = code[:original_if.start] + new_if + code[original_if.end:]
    return subrule(rule.name + " global", "Peristiwa" + p.capitalize(), guards + persistent(code))


def build_english(source: str) -> tuple[str, dict]:
    logical = translate(source)
    rules = validator.extract_rules(logical)
    each = validator.rules_with_event(rules, "Ongoing - Each Player")
    assert len(each) == 36
    callback = [rule for rule in rules if prefix(rule) in EVENT_PREFIXES]
    assert len(callback) == 7
    by_prefix = {prefix(r): r for r in each}
    indices = {prefix(r): i for i, r in enumerate(each)}
    header = logical[:rules[0].start]
    header = header.replace("\t\t59: PrivasiInspeksiAktif\n", "\t\t59: PrivasiInspeksiAktif\n\t\t60: StatusPengatur\n")
    header = header.replace("\t\t91: IzinkanBotBuatanMengikuti\n", "\t\t91: IzinkanBotBuatanMengikuti\n\t\t92: WaktuPengatur\n")
    old_subs = validator.declaration_entries(logical)[2]
    targets = [controller_name(r) for r in each] + ["Peristiwa" + p.capitalize() for p in EVENT_PREFIXES] + ["ProsesPengaturGlobal", "ProsesAntreanGlobal", "ProsesKeluarGlobal", "ProsesIkonTerlihat"]
    assert len(old_subs) + len(targets) <= 128
    header = header.replace("\t\t80: PemainIkonPilar\n", "\t\t80: PemainIkonPilar\n" + "".join(f"\t\t{81+i}: {name}\n" for i, name in enumerate(GLOBALS)))
    header = header.replace("\t66: BersihkanIkonPilar\n", "\t66: BersihkanIkonPilar\n" + "".join(f"\t{67+i}: {name}\n" for i, name in enumerate(targets)))

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
            marker = 'Global.IndeksUtangKeluar = Global.SlotHUDPemain[Global.IndeksPembersihan];'
            body = body.replace(marker, marker + '\n\t\tGlobal.WaktuHilangHUD[Global.IndeksUtangKeluar] = 0;')
        if p == '89a':
            # Losing a lifecycle reservation also invalidates its suspended
            # phase, including team flips before the first roster registration.
            body = body.replace('Global.PemainSiklusGlobal = Null;', 'Global.PemainSiklusGlobal = Null;\n\t\tGlobal.PemilikFaseSiklus = Null;')
        if p == "00":
            init = "".join(f"\t\tGlobal.{name} = {'Empty Array' if name in {'AntreanPeristiwa','KeluarTertunda','WaktuHilangHUD','PilihanIkonTerlihat'} else 'Null' if name in {'PemainPemicu','PemilikFaseSiklus','PeristiwaAktif'} else '0'};\n" for name in GLOBALS)
            body = body.replace("\t\tGlobal.Siap = True;", init + "\t\tGlobal.Siap = True;")
        if p == "04g":
            # Existing global loop remains the sole clock. Events drain before menu/gameplay work.
            body = body.replace('\t\tGlobal.SalinanDaftarPemain = All Players(All Teams);\n', '')
            body = body.replace("\t\tGlobal.LangkahPenjadwal =", "\t\tGlobal.SalinanDaftarPemain = All Players(All Teams);\n\t\tCall Subroutine(ProsesAntreanGlobal);\n\t\tCall Subroutine(ProsesKeluarGlobal);\n\t\tGlobal.LangkahPenjadwal =", 1)
            body = body.replace('Has Spawned(Global.PemainSiklusGlobal) == False', 'Or(Has Spawned(Global.PemainSiklusGlobal) == False, Array Contains(Global.SalinanDaftarPemain, Global.PemainSiklusGlobal) == False)')
            body = body.replace('Global.PemainSiklusGlobal = Null;', 'Global.PemainSiklusGlobal = Null;\n\t\tGlobal.PemilikFaseSiklus = Null;')
            body = body.replace("\t\t\tGlobal.PemainAktif = Global.SalinanDaftarPemain[Global.IndeksPemainGlobal];", "\t\t\tGlobal.PemainAktif = Global.SalinanDaftarPemain[Global.IndeksPemainGlobal];\n\t\t\tGlobal.PemainPemicu = Global.PemainAktif;\n\t\t\tCall Subroutine(ProsesPengaturGlobal);")
            body = body.replace("\t\tGlobal.PemainAktif = Null;", "\t\tGlobal.PemainPemicu = Null;\n\t\tGlobal.PemainAktif = Null;")
            body = body.replace('\t\tIf(Global.PilihanPerluDihitung == True);', '\t\tCall Subroutine(ProsesIkonTerlihat);\n\t\tIf(Global.PilihanPerluDihitung == True);')
        lowered.append(body)

    # Group calls by human/bot state. Inactive human menu/Travel groups are skipped.
    controls = f"\t\tAbort If(Entity Exists({ACTOR}) == False);\n\t\tIf(Count Of({STATE}) < 37);\n\t\t\tGlobal.GenerasiPengatur += 1;\n\t\t\t{STATE} = Empty Array;\n\t\t\t{STATE}[36] = Global.GenerasiPengatur;\n\t\t\t{TIME} = Empty Array;\n\t\tEnd;\n"
    controls += f"\t\tCall Subroutine({controller_name(by_prefix['01a'])});\n\t\tCall Subroutine({controller_name(by_prefix['01b'])});\n\t\tCall Subroutine({controller_name(by_prefix['02'])});\n"
    controls += f"\t\tIf(Or(Is Dummy Bot({ACTOR}), {ACTOR}.BotOtomatis));\n"
    for p in ["03c", "03f", "03g", "03h", "18i", "18j"]:
        controls += f"\t\t\tCall Subroutine({controller_name(by_prefix[p])});\n"
    controls += f"\t\tElse If(And({ACTOR}.Manusia == True, And(Is Dummy Bot({ACTOR}) == False, {ACTOR}.BotOtomatis == False)));\n"
    menu_group = {'05c', '05d', '05e', '05f', '06', '08', '10', '11'}
    travel_group = {'19a', '19b', '19c', '19d', '19e', '19g'}
    for original in each:
        p = prefix(original)
        if p in {"01a", "01b", "02", "03c", "03f", "03g", "03h"}:
            continue
        if p == '05c':
            controls += f'\t\t\tIf(Or({ACTOR}.MenuTerbuka == True, Or({ACTOR}.PerintahMenu != 0, {ACTOR}.MasukanMenuDikunci == True)));\n'
            for member in [item for item in each if prefix(item) in menu_group]:
                controls += f'\t\t\t\tCall Subroutine({controller_name(member)});\n'
            controls += '\t\t\tElse;\n'
            for member in ('06', '08', '10', '11'):
                controls += f'\t\t\t\t{STATE}[{indices[member]}] = 0;\n'
            controls += '\t\t\tEnd;\n'
            continue
        if p in menu_group: continue
        if p == '19a':
            controls += f'\t\t\tIf({ACTOR}.TeleportasiJongkokAktif == True);\n'
            for member in [item for item in each if prefix(item) in travel_group]:
                controls += f'\t\t\t\tCall Subroutine({controller_name(member)});\n'
            controls += '\t\t\tEnd;\n'
            controls += f'\t\t\tIf({ACTOR}.TeleportasiJongkokAktif == False);\n'
            for member in ('19c', '19e'):
                controls += f'\t\t\t\t{STATE}[{indices[member]}] = 0;\n'
            controls += '\t\t\tEnd;\n'
            continue
        if p in travel_group: continue
        if p in {'19f', '19h'}:
            controls += f'\t\t\tIf({ACTOR}.LampiranTeleportasiAktif == True);\n\t\t\t\tCall Subroutine({controller_name(original)});\n\t\t\tEnd;\n'
            continue
        if p in {'18i', '18j'}:
            controls += f'\t\t\tIf(Or(Count Of(Global.PenontonVisiNasib) > 0, And({ACTOR}.TeksVisiNasib != Null, {ACTOR}.TeksVisiNasib != 0)));\n\t\t\t\tCall Subroutine({controller_name(original)});\n\t\t\tEnd;\n'
            continue
        controls += f"\t\t\tCall Subroutine({controller_name(original)});\n"
    controls += "\t\tEnd;\n"
    lowered.append(subrule("04h - Subrutin: Pengatur pemain dari konteks global", "ProsesPengaturGlobal", controls))

    drain = "\t\tGlobal.JumlahPeristiwaAwal = Global.JumlahPeristiwa;\n\t\tFor Global Variable(KursorPeristiwa, 0, Global.JumlahPeristiwaAwal, 1);\n"
    drain += f"\t\t\tGlobal.PeristiwaAktif = Global.AntreanPeristiwa[Global.KepalaPeristiwa];\n\t\t\tGlobal.AntreanPeristiwa[Global.KepalaPeristiwa] = Null;\n\t\t\tGlobal.KepalaPeristiwa = (Global.KepalaPeristiwa + 1) % {CAPACITY};\n\t\t\tGlobal.JumlahPeristiwa -= 1;\n\t\t\tGlobal.PemainPemicu = Global.PeristiwaAktif[1];\n"
    for kind, p in enumerate(EVENT_PREFIXES):
        drain += f"\t\t\t{'If' if kind == 0 else 'Else If'}(Global.PeristiwaAktif[0] == {kind});\n\t\t\t\tCall Subroutine(Peristiwa{p.capitalize()});\n"
    drain += "\t\t\tEnd;\n\t\tEnd;\n\t\tGlobal.PemainPemicu = Null;\n\t\tGlobal.PeristiwaAktif = Null;\n"
    lowered.append(subrule("04i - Subrutin: Proses antrean peristiwa yang dibekukan", "ProsesAntreanGlobal", drain))

    leaves = "\t\tFor Global Variable(KursorKeluarTertunda, 0, Count Of(Global.KeluarTertunda), 1);\n\t\t\tIf(Global.KeluarTertunda[Global.KursorKeluarTertunda] != Null);\n\t\t\t\tGlobal.PeristiwaAktif = Global.KeluarTertunda[Global.KursorKeluarTertunda];\n\t\t\t\tIf(Total Time Elapsed >= Global.PeristiwaAktif[7] + 0.500);\n\t\t\t\t\tGlobal.PemainPemicu = Global.PeristiwaAktif[1];\n\t\t\t\t\tGlobal.KeluarTertunda[Global.KursorKeluarTertunda] = Null;\n\t\t\t\t\tIf(Entity Exists(Global.PemainPemicu) == False);\n\t\t\t\t\t\tCall Subroutine(BersihkanPemain);\n\t\t\t\t\tEnd;\n\t\t\t\tEnd;\n\t\t\tEnd;\n\t\tEnd;\n"
    leaves += "\t\tIf(Global.LangkahPenjadwal % 20 == 0);\n\t\t\tFor Global Variable(KursorDaftarHilang, Count Of(Global.PemainManusia) - 1, -1, -1);\n\t\t\t\tGlobal.PemainPemicu = Global.PemainManusia[Global.KursorDaftarHilang];\n\t\t\t\tIf(Entity Exists(Global.PemainPemicu));\n\t\t\t\t\tGlobal.WaktuHilangHUD[Global.SlotHUDPemain[Global.KursorDaftarHilang]] = 0;\n\t\t\t\tElse If(Global.WaktuHilangHUD[Global.SlotHUDPemain[Global.KursorDaftarHilang]] == 0);\n\t\t\t\t\tGlobal.WaktuHilangHUD[Global.SlotHUDPemain[Global.KursorDaftarHilang]] = Total Time Elapsed + 0.500;\n\t\t\t\tElse If(Total Time Elapsed >= Global.WaktuHilangHUD[Global.SlotHUDPemain[Global.KursorDaftarHilang]]);\n\t\t\t\t\tCall Subroutine(BersihkanPemain);\n\t\t\t\tEnd;\n\t\t\tEnd;\n\t\tEnd;\n\t\tGlobal.PeristiwaAktif = Null;\n\t\tGlobal.PemainPemicu = Null;\n"
    # Spectators can retain a native entity while no longer belonging to either
    # playing team. Treat that membership loss as departure for global resources.
    present = 'And(Entity Exists(Global.PemainPemicu), Array Contains(Global.SalinanDaftarPemain, Global.PemainPemicu))'
    leaves = leaves.replace('Entity Exists(Global.PemainPemicu) == False', f'{present} == False').replace('If(Entity Exists(Global.PemainPemicu))', f'If({present})')
    lowered.append(subrule("04j - Subrutin: Bersihkan keluar tertunda tanpa konteks pemain", "ProsesKeluarGlobal", leaves))
    icon_cache = '\t\tFor Global Variable(IndeksIkonPilar, 0, 12, 1);\n\t\t\tGlobal.PemainIkonPilar = Global.PemilikIkonPilar[Global.IndeksIkonPilar];\n\t\t\tGlobal.PilihanIkonTerlihat[Global.IndeksIkonPilar] = And(Entity Exists(Global.PemainIkonPilar), And(Array Contains(Global.PemainManusia, Global.PemainIkonPilar), And(Global.PemainIkonPilar.Manusia == True, Distance Between(Objective Position(Objective Index), Vector(0, 0, 0)) > 0.100))) ? Global.PemainIkonPilar.IndeksIkon : 0;\n\t\tEnd;\n\t\tGlobal.PemainIkonPilar = Null;\n'
    lowered.append(subrule('04k - Subrutin: Simpan visibilitas ikon setelah semua perintah', 'ProsesIkonTerlihat', icon_cache))
    output = compact_booleans(compact_unused_constants(compact_fixed_pools(compact_icon_visibility(compact_palette(header + "\n\n".join(lowered) + "\n")))))
    return output, {"controllers": {prefix(r): {"target": controller_name(r), "index": indices[prefix(r)]} for r in each}, "callbacks": {p: i for i, p in enumerate(EVENT_PREFIXES)}, "capacity": CAPACITY, "latches": sorted(LATCH_PREFIXES)}


def build(source: str) -> str:
    runtime, _ = build_english(source)
    return translate(runtime, to_italian=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=REPO / "source" / "ruang_irama.it-IT.source")
    parser.add_argument("--output", type=Path, default=REPO / 'workshop' / 'ruang_irama.it-IT.workshop')
    parser.add_argument('--reference', type=Path, default=REPO / 'tests' / 'fixtures' / 'global_runtime_reference.txt')
    parser.add_argument('--check', action='store_true', help='Verify both generated files without writing them.')
    args = parser.parse_args()
    source = args.source.read_text(encoding="utf-8")
    english, _ = build_english(source)
    runtime = translate(english, to_italian=True)
    parsed = validator.extract_rules(english)
    checks = validator.Checks()
    validator.validate_rule_grammar(checks, parsed)
    checks.finish()
    assert not validator.rules_with_event(parsed, "Ongoing - Each Player")
    assert not validator.global_player_context_errors(parsed)
    assert len(list(validator.iter_calls(english, "Wait"))) == 1
    report = clipboard.check_text(runtime, "it-IT")
    reference = translate(runtime)
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
