"""Independent gates for the generated, globally executed Workshop.

The behavioural specification retains its existing contracts. These gates read
the actual import artifact, so passing specification tests cannot certify a
broken or stale backend. Native scheduling and engine lifetime still need QA.
"""
from __future__ import annotations

from pathlib import Path
import re
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import check_clipboard_import as clipboard
from tools import validate_workshop as semantic


ROOT = Path(__file__).resolve().parents[1]
ACTORS = ("Global.TriggerPlayer", "Global.ActivePlayer")
PERSISTENT_ACTORS = (*ACTORS, "Global.ObjectiveIconPlayer", "Global.CameraPlayer")
PERSISTENT_ACTIONS = (
    "Create HUD Text", "Create In-World Text", "Create Icon", "Create Effect",
    "Start Camera", "Start Facing", "Start Throttle In Direction",
    "Start Accelerating", "Start Transforming Throttle",
    "Chase Player Variable At Rate", "Chase Player Variable Over Time",
    "Attach Players", "Start Forcing Dummy Bot Name",
    "Start Forcing Player To Be Hero", "Start Forcing Player Position",
)
NATIVE_EVENTS = {"Player Died", "Player Left Match", "Player Dealt Damage"}
RECORD_ACTIONS = {
    "If", "Else If", "Else", "End", "Abort If", "Abort",
    "Set Global Variable", "Set Global Variable At Index",
    "Modify Global Variable", "Modify Global Variable At Index",
}
COLLECTOR_FIELDS = {"EventQueue", "EventQueueTail", "EventCount", "DroppedEventCount"}


def english(text: str) -> str:
    """Translate grammar, leaving quoted strings byte-for-byte unchanged."""
    parts = re.split(r'("(?:\\.|[^"\\])*")', text)
    for index in range(0, len(parts), 2):
        for original, replacement in clipboard.ITALIAN_TO_ENGLISH_TOKENS:
            parts[index] = clipboard._replace_token(parts[index], original, replacement)
    return "".join(parts)


def unfrozen_actors(expression: str) -> list[str]:
    """A frozen owner may still read its player variables dynamically."""
    text = semantic.mask_strings(expression)
    spans = [(call.start, call.end) for call in semantic.iter_calls(text, "Evaluate Once")]
    for start, end in reversed(spans):
        text = text[:start] + " " * (end - start) + text[end:]
    return [actor for actor in PERSISTENT_ACTORS if re.search(rf"{re.escape(actor)}\b", text)]


def validate_runtime(text: str) -> list[str]:
    errors: list[str] = []
    try:
        profile = "it-IT" if text.lstrip().startswith("variabili") else "en-US"
        native_syntax = semantic.mask_strings(text)
        # Parenthesized unary signs parse in our structural AST but the native
        # importer rejects them. Check raw syntax independently of that AST.
        if re.search(r"(?:^|[=,(\[?:<>+*/%\-])\s*[-+]\s*\(", native_syntax, re.M):
            errors.append("runtime globale: segno unario prima di parentesi non importabile; usare un numero con segno o un valore nativo")
        if profile == "it-IT":
            # EN normalization must not hide partial translations of native
            # names. Only the namespace and standalone event selectors differ.
            invalid_native = (
                r"\bOngoing\s*-\s*Globale\b",
                r"\bGlobale\s+Variable\b",
                r"\bTutti\s+(?:(?:Living|Dead)\s+)?Players\b",
                r"\bTutti\s+Teams\b",
                r"\bIs\s+True\s+For\s+Tutti\b",
            )
            if any(re.search(pattern, native_syntax) for pattern in invalid_native):
                errors.append("runtime globale: identificatore nativo tradotto parzialmente")
        clipboard.check_text(text, profile)
        normalized = english(text) if profile == "it-IT" else text
        rules = semantic.extract_rules(normalized)
        globals_, players, subs, _ = semantic.declaration_entries(normalized)
    except (ValueError, clipboard.ClipboardImportError) as exc:
        return [f"runtime globale non analizzabile: {exc}"]
    if not rules:
        return ["runtime globale senza regole"]
    if any(re.fullmatch(rf"{index} - .+", rule.name) is None
           for index, rule in enumerate(rules)):
        errors.append("runtime globale: numerazione regole consecutiva da 0 richiesta, senza duplicati o suffissi")
    checks = semantic.Checks()
    semantic.validate_rule_grammar(checks, rules)
    errors.extend(checks.errors)
    for name, entries in (("global", globals_), ("player", players), ("subroutine", subs)):
        indices = [entry.index for entry in entries]
        names = [entry.name for entry in entries]
        if len(indices) != len(set(indices)) or len(names) != len(set(names)):
            errors.append(f"dichiarazioni {name} duplicate")
        if any(index < 0 or index >= 128 for index in indices):
            errors.append(f"dichiarazioni {name} oltre 128 slot")
        if any(len(value.encode("utf-8")) > 32 for value in names):
            errors.append(f"nome dichiarazione {name} oltre 32 byte")
    errors.extend(semantic.custom_reference_errors(normalized,
        {entry.name for entry in globals_}, {entry.name for entry in players}))
    declared_players = {entry.name for entry in players}
    for field in re.findall(r"\bGlobal\.[A-Za-z][A-Za-z0-9_]*\.([A-Za-z][A-Za-z0-9_]*)",
                            semantic.mask_strings(normalized)):
        if field not in declared_players:
            errors.append(f"riferimento player non dichiarato: {field}")
    declared_subs = {entry.name for entry in subs}
    for call in semantic.iter_calls(normalized, "Call Subroutine"):
        if len(call.args) != 1 or call.args[0] not in declared_subs:
            errors.append(f"subroutine non dichiarata: {call.raw}")
    errors.extend(semantic.global_player_context_errors(rules))
    kinds = [semantic.event_type(rule) for rule in rules]
    if "Ongoing - Each Player" in kinds:
        errors.append("runtime globale: Ongoing - Each Player vietato")
    if any(kind not in NATIVE_EVENTS | {"Ongoing - Global", "Subroutine"} for kind in kinds):
        errors.append("runtime globale: evento non supportato")
    schedulers = [rule for rule in rules if semantic.event_type(rule) == "Ongoing - Global"
                  and semantic.action_loop_count(rule.body) > 0]
    scheduler = schedulers[0] if len(schedulers) == 1 else None
    all_waits = [(rule, call) for rule in rules for call in semantic.wait_calls(rule.body)]
    if len(all_waits) != 1 or not scheduler or all_waits[0][0] is not scheduler:
        errors.append("runtime globale: solo lo scheduler può attendere, una volta")
    elif all_waits[0][1].args != ("0.050", "Ignore Condition"):
        errors.append("runtime globale: cadenza scheduler deve essere 0,050 s")
    if semantic.action_loop_count(normalized) != 1:
        errors.append("runtime globale: unico Loop nello scheduler richiesto")
    if list(semantic.iter_calls(normalized, "Start Rule")):
        errors.append("runtime globale: avvio asincrono con attore condiviso vietato")
    palette = semantic.rule_by_subroutine(rules, "TransitionMenuColor")
    if palette:
        chases = list(semantic.iter_calls(palette.body, "Chase Player Variable Over Time"))
        if len(chases) != 2 or any(len(call.args) != 5 or
                call.args[1] != "MenuColor" or call.args[3:] != ("0.180", "None")
                for call in chases):
            errors.append("runtime globale: colori menu richiedono due destinazioni sincrone con transizione 0.180 e None")
    for rule in rules:
        kind = semantic.event_type(rule)
        actions = semantic.rule_block(rule, "actions") or ""
        masked = semantic.mask_strings(actions)
        for statement in semantic.split_top_level(masked, ";"):
            if statement.lstrip().startswith("("):
                errors.append(f"runtime globale {rule.name}: azione convertita in espressione ({statement.strip()[:75]})")
        if kind in NATIVE_EVENTS:
            if any(re.search(rf"{re.escape(actor)}\b", semantic.mask_strings(rule.body)) for actor in ACTORS):
                errors.append(f"callback {rule.name}: attore dello scheduler condiviso vietato")
            for statement in semantic.split_top_level(masked, ";"):
                statement = statement.strip()
                if not statement:
                    continue
                assignment = re.match(r"Global\.([A-Za-z][A-Za-z0-9_]*)(?:\[[^;]+\])?\s*[+\-*/%]?=(?!=)", statement)
                if assignment:
                    if assignment[1] not in COLLECTOR_FIELDS:
                        errors.append(f"callback {rule.name}: scrittura fuori dalla coda ({assignment[1]})")
                    continue
                match = re.match(r"([A-Za-z][A-Za-z ]*)(?:\(|$)", statement)
                if not match or match[1].strip() not in RECORD_ACTIONS:
                    errors.append(f"callback {rule.name}: deve solo registrare eventi ({statement[:85]})")
                elif match[1].strip() in {"Set Global Variable", "Set Global Variable At Index", "Modify Global Variable", "Modify Global Variable At Index"}:
                    calls = list(semantic.iter_calls(statement, match[1].strip()))
                    if not calls or not calls[0].args or calls[0].args[0] not in COLLECTOR_FIELDS:
                        errors.append(f"callback {rule.name}: scrittura fuori dalla coda")
        else:
            if re.search(r"\b(?:Attacker|Victim|Event (?:Player|Ability|Damage|Direction|Was Critical Hit))\b", masked):
                errors.append(f"runtime globale {rule.name}: valore nativo evento non catturato")
            for action in PERSISTENT_ACTIONS:
                for call in semantic.iter_calls(actions, action):
                    for argument in call.args:
                        if unfrozen_actors(argument):
                            errors.append(f"runtime globale {rule.name}: proprietario non congelato in {action}")
                            break
    if scheduler:
        tail = semantic.mask_strings(semantic.rule_block(scheduler, "actions") or "")
        wait = next(semantic.iter_calls(tail, "Wait"), None)
        if wait:
            before = tail[:wait.start]
            for actor in ACTORS:
                writes = list(re.finditer(rf"{re.escape(actor)}\s*=\s*([^;]+);", before))
                if not writes or writes[-1][1].strip() != "Null" or semantic.conditional_branches_containing(before, writes[-1].start()):
                    errors.append(f"runtime globale: {actor} deve essere svuotato prima del Wait")
    return sorted(set(errors))


def validate_generated(root: Path = ROOT) -> list[str]:
    """Check specification parity, deterministic build and actual runtime gates."""
    errors: list[str] = []
    try:
        from tools import build_global_runtime as compiler
        source = (root / "source/ruang_irama.en-US.source").read_text(encoding="utf-8")
        runtime = (root / "workshop/ruang_irama.en-US.workshop").read_text(encoding="utf-8")
        expected = compiler.build(source)
        if runtime != expected:
            errors.append("runtime globale obsoleto: rigenerare con build_global_runtime.py")
        reference = (root / "tests/fixtures/global_runtime_reference.txt").read_text(encoding="utf-8")
        if english(runtime) != reference:
            errors.append("riferimento runtime EN obsoleto: rigenerare entrambi gli output")
        normalized_source, normalized_runtime = english(source), english(runtime)
        for action in PERSISTENT_ACTIONS:
            before = len(list(semantic.iter_calls(normalized_source, action)))
            after = len(list(semantic.iter_calls(normalized_runtime, action)))
            if before != after:
                errors.append(f"runtime globale: azione nativa persa/duplicata {action} ({before} -> {after})")
        errors.extend(validate_runtime(runtime))
    except (OSError, ValueError, ImportError) as exc:
        errors.append(f"compilazione globale: {exc}")
    return errors


def main() -> int:
    errors = validate_generated()
    for error in errors:
        print(f"ERROR - {error}")
    if not errors:
        print("OK - runtime globale: output attuale, contesti e proprietari verificati")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
