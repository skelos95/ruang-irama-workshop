"""Select actual emitted rules by their behavior rather than display numbers.

The logical source retains stable compiler IDs. Tests may use those IDs to find
the corresponding specification, then resolve an emitted subroutine or native
event. The final artifact's rule labels are never rewritten by this helper.
"""
from functools import lru_cache
from pathlib import Path

from tools import validate_workshop as semantic


@lru_cache(maxsize=1)
def logical_rules():
    path = Path(__file__).resolve().parents[1] / "source/ruang_irama.en-US.source"
    return semantic.extract_rules(path.read_text(encoding="utf-8"))


def rule_for_logical_id(rules, logical_id, event_type=None):
    specification = [rule for rule in logical_rules()
                     if rule.name.partition(" - ")[0] == logical_id]
    if len(specification) != 1:
        raise AssertionError(f"expected one logical rule {logical_id}")
    original = specification[0]
    original_kind = semantic.event_type(original)
    if original_kind == "Subroutine":
        target = semantic.subroutine_target(original)
    elif original_kind == "Ongoing - Each Player":
        target = "Controller" + logical_id.capitalize()
    else:
        target = "NativeEvent" + logical_id.capitalize()
    if original_kind == "Subroutine" or event_type == "Subroutine":
        matches = [rule for rule in rules if semantic.event_type(rule) == "Subroutine"
                   and semantic.subroutine_target(rule) == target]
    else:
        title = original.name.partition(" - ")[2]
        matches = [rule for rule in rules
                   if semantic.event_type(rule) == (event_type or original_kind)
                   and rule.name.partition(" - ")[2] == title]
        if not matches and original_kind == "Ongoing - Each Player":
            matches = [rule for rule in rules if semantic.event_type(rule) == "Subroutine"
                       and semantic.subroutine_target(rule) == target]
    if len(matches) != 1:
        raise AssertionError(f"expected one rule for {logical_id}: {[rule.name for rule in matches]}")
    return matches[0]
