from pathlib import Path

path = Path(__file__).resolve().parents[1] / "tests/test_validate_workshop.py"
text = path.read_text(encoding="utf-8")
old = '''    def test_at_most_seven_waits_are_allowed(self) -> None:
        scheduler = self.rule(lambda rule: validator.action_loop_count(rule.body) == 1)
        mutated = self.inject_action(scheduler, "Wait(0.001, Ignore Condition);")
        self.assert_rejected(mutated, "Wait oltre")
'''
new = '''    def test_at_most_seven_waits_are_allowed(self) -> None:
        scheduler = self.rule(lambda rule: validator.action_loop_count(rule.body) == 1)
        mutated = self.source
        for delay in ("0.001", "0.002", "0.003"):
            current = next(
                rule for rule in validator.extract_rules(mutated)
                if validator.action_loop_count(rule.body) == 1
            )
            closing = current.body.rfind("\\n\\t}")
            changed = current.body[:closing] + f"\\n\\t\\tWait({delay}, Ignore Condition);" + current.body[closing:]
            mutated = mutated[:current.start] + changed + mutated[current.end:]
        self.assertGreater(len(validator.wait_calls(mutated)), 7)
        self.assert_rejected(mutated, "Wait oltre")
'''
if text.count(old) != 1:
    raise SystemExit(f"Wait limit test block mismatch: {text.count(old)}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("Updated Wait limit regression for five-Wait baseline")
