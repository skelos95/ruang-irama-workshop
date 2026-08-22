#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
fixture_path = root / "tests" / "fixtures" / "semantic_reference.txt"
validator_path = root / "tools" / "validate_workshop.py"
tests_path = root / "tests" / "test_validate_workshop.py"
dummy_tests_path = root / "tests" / "test_dummy_bots.py"


def once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


# Keep the semantic fixture aligned with the already-live safe Italian 03f routing.
fixture = fixture_path.read_text(encoding="utf-8")
old_route = '''\t\tIf(Count Of(All Players On Objective(All Teams)) > 0);
\t\t\tTeleport(Event Player, Position Of(First Of(All Players On Objective(All Teams))));
\t\tElse;
\t\t\tTeleport(Event Player, Objective Position(Objective Index));
\t\tEnd;'''
new_route = '''\t\tIf(Or(Current Game Mode == Game Mode(Escort), Current Game Mode == Game Mode(Hybrid)));
\t\t\tIf(Distance Between(Payload Position, Vector(0, 0, 0)) > 0.100);
\t\t\t\tTeleport(Event Player, Nearest Walkable Position(Payload Position + Vector(2, 0, 0)));
\t\t\tEnd;
\t\tElse If(Current Game Mode == Game Mode(Capture The Flag));
\t\t\tIf(Distance Between(Flag Position(Opposite Team Of(Team Of(Event Player))), Vector(0, 0, 0)) > 0.100);
\t\t\t\tTeleport(Event Player, Nearest Walkable Position(Flag Position(Opposite Team Of(Team Of(Event Player))) + Vector(2, 0, 0)));
\t\t\tEnd;
\t\tElse If(Current Game Mode == Game Mode(Push));
\t\t\tIf(Count Of(Filtered Array(All Players(All Teams), And(Has Spawned(Current Array Element) == True, And(Is Alive(Current Array Element) == True, Is On Objective(Current Array Element) == True)))) > 0);
\t\t\t\tTeleport(Event Player, Nearest Walkable Position(Position Of(First Of(Filtered Array(All Players(All Teams), And(Has Spawned(Current Array Element) == True, And(Is Alive(Current Array Element) == True, Is On Objective(Current Array Element) == True))))) + Vector(2, 0, 0)));
\t\t\tElse If(Distance Between(Objective Position(Objective Index), Vector(0, 0, 0)) > 0.100);
\t\t\t\tTeleport(Event Player, Nearest Walkable Position(Objective Position(Objective Index)));
\t\t\tEnd;
\t\tElse If(Distance Between(Objective Position(Objective Index), Vector(0, 0, 0)) > 0.100);
\t\t\tTeleport(Event Player, Nearest Walkable Position(Objective Position(Objective Index)));
\t\tEnd;'''
fixture = once(fixture, old_route, new_route, "semantic 03f safe routing")
fixture_path.write_text(fixture, encoding="utf-8")

validator = validator_path.read_text(encoding="utf-8")
old_localization = '''        visible_text = call.args[2] + "\\n" + call.args[3]
        if "Custom String" in visible_text and re.search(r"[A-Za-z\\u0e00-\\u0e7f]", visible_text):
            found = language_triads(visible_text)
            selectors = (
                re.search(r"IndeksBahasa\\)?\\s*==\\s*0\\b", visible_text) is not None
                and re.search(r"IndeksBahasa\\)?\\s*==\\s*1\\b", visible_text) is not None
                and (re.search(r"[\\u0e00-\\u0e7f]", visible_text) is not None or "Thai" in visible_text)
            )
            checks.require(bool(found) or selectors, "Create HUD Text con testo non tradotto EN/ID/TH")
            triads.extend(found)'''
new_localization = '''        visible_text = call.args[2] + "\\n" + call.args[3]
        literals = [
            parse_literal(custom.args[0])
            for custom in iter_calls(visible_text, "Custom String")
            if custom.args
        ]
        meaningful_literals = [
            literal for literal in literals
            if literal is not None and re.search(r"[A-Za-z\\u0e00-\\u0e7f]", literal)
        ]
        # These labels are intentionally language-neutral in the live HUD. Blank
        # spacer rows have no meaningful literals and therefore need no language triad.
        language_neutral = {"CHILL DEDICATED SERVER", "MENU"}
        if meaningful_literals and not all(literal in language_neutral for literal in meaningful_literals):
            found = language_triads(visible_text)
            selectors = (
                re.search(r"IndeksBahasa\\)?\\s*==\\s*0\\b", visible_text) is not None
                and re.search(r"IndeksBahasa\\)?\\s*==\\s*1\\b", visible_text) is not None
                and (re.search(r"[\\u0e00-\\u0e7f]", visible_text) is not None or "Thai" in visible_text)
            )
            checks.require(bool(found) or selectors, "Create HUD Text con testo non tradotto EN/ID/TH")
            triads.extend(found)'''
validator = once(validator, old_localization, new_localization, "HUD localization rule")

old_title_check = '''    server_title = next(
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
            any(literal is not None and literal.endswith("\\n ") for literal in title_literals),
            "HUD titolo CHILL deve mantenere una riga vuota prima del menu",
        )'''
new_title_check = '''    def hud_row(position: str, sort_order: str, *needles: str) -> Call | None:
        for call in hud_calls:
            if len(call.args) < 6:
                continue
            if call.args[4].strip() != position or call.args[5].strip() != sort_order:
                continue
            visible = call.args[2] + "\\n" + call.args[3]
            if all(needle in visible for needle in needles):
                return call
        return None

    # Live-tested primary HUD contract: each vertical row is an independent HUD
    # element so spacing/alignment does not depend on embedded newlines.
    checks.require(hud_row("Top", "0", "CHILL DEDICATED SERVER", "Global.TeksWaktuServer") is not None,
                   "HUD server/time deve essere Top 0")
    checks.require(hud_row("Top", "1", "Global.NamaLokasiInggris", "Global.NamaLokasiIndonesia", "Global.NamaLokasiThai") is not None,
                   "HUD location deve essere Top 1")
    checks.require(hud_row("Top", "2", 'Custom String(" ")') is not None,
                   "HUD spacer Top 2 assente")
    checks.require(hud_row("Top", "3", 'Custom String("MENU")') is not None,
                   "HUD MENU deve essere Top 3")

    checks.require(hud_row("Left", "-2", "Button(Crouch)", 'Custom String("HOLD {0}:")') is not None,
                   "HUD HOLD sinistro deve essere Left -2")
    checks.require(hud_row("Left", "-1", 'Custom String(" ")') is not None,
                   "HUD spacer sinistro deve essere Left -1")
    checks.require(hud_row("Left", "0", "LOBBY & CHILL TIME") is not None,
                   "HUD titolo lobby deve essere Left 0")
    checks.require(hud_row("Right", "-2", "Button(Melee)", 'Custom String("HOLD {0} 0.5 SEC")') is not None,
                   "HUD HOLD destro deve essere Right -2")
    checks.require(hud_row("Right", "-1", 'Custom String("  ")') is not None,
                   "HUD spacer destro deve essere Right -1")
    checks.require(hud_row("Right", "0", "PLAYER VIBES") is not None,
                   "HUD titolo Player Vibes deve essere Right 0")

    roster_calls = [
        call for call in hud_calls
        if len(call.args) >= 6 and "Event Player.UrutanHUD" in call.args[5]
    ]
    checks.equal(len(roster_calls), 2, "HUD roster sinistro/destra")
    for position in ("Left", "Right"):
        calls = [call for call in roster_calls if call.args[4].strip() == position]
        checks.equal(len(calls), 1, f"HUD roster {position}")
        if calls:
            checks.equal(calls[0].args[5].strip(), "1 + Event Player.UrutanHUD",
                         f"HUD roster {position} deve iniziare a sort 1")'''
validator = once(validator, old_title_check, new_title_check, "structured primary HUD validator")
validator_path.write_text(validator, encoding="utf-8")

# Migrate unit tests from the embedded-newline HUD contract to independent rows.
tests = tests_path.read_text(encoding="utf-8")ntests = once(
    tests,
    '''        mutated = self.replace_once(
            '\"Hold {0}: inspect hero + HP\"',
            '\"Hold {0}: inspect hero + HP | in menu: modifier for every command\"',
        )''',
    '''        mutated = self.replace_once(
            '\"HOLD {0}:\"',
            '\"HOLD {0}: in menu: modifier for every command\"',
        )''',
    "global HUD modifier test",
)
old_spacer_test = '''    def test_chill_title_requires_a_blank_spacer_line(self) -> None:
        call = next(
            call for call in validator.iter_calls(self.source, "Create HUD Text")
            if len(call.args) >= 4
            and "CHILL DEDICATED SERVER" in call.args[3]
            and "Global.TeksWaktuServer" in call.args[3]
        )
        changed_argument = call.args[3].replace(r"\\n ", "", 1)
        self.assertNotEqual(changed_argument, call.args[3])
        mutated = self.replace_call_argument(call, 3, changed_argument)
        self.assert_rejected(mutated, "riga vuota prima del menu")'''
new_spacer_test = '''    def test_chill_title_requires_a_blank_spacer_line(self) -> None:
        call = next(
            call for call in validator.iter_calls(self.source, "Create HUD Text")
            if len(call.args) >= 6
            and call.args[4].strip() == "Top"
            and call.args[5].strip() == "2"
            and 'Custom String(" ")' in (call.args[2] + call.args[3])
        )
        mutated = self.replace_call_argument(call, 5, "4")
        self.assert_rejected(mutated, "spacer Top 2")'''
tests = once(tests, old_spacer_test, new_spacer_test, "top spacer validator test")
tests_path.write_text(tests, encoding="utf-8")

# Assert the English semantic fixture cannot silently drift back to unsafe routing.
dummy_tests = dummy_tests_path.read_text(encoding="utf-8")
needle = '''        self.assertNotIn("Teleport(Event Player, Objective Position(Objective Index));", self.it)
'''
addition = '''        self.assertNotIn("Teleport(Event Player, Objective Position(Objective Index));", self.it)
        self.assertIn("Current Game Mode == Game Mode(Escort)", self.en)
        self.assertIn("Current Game Mode == Game Mode(Hybrid)", self.en)
        self.assertIn("Current Game Mode == Game Mode(Capture The Flag)", self.en)
        self.assertIn("Current Game Mode == Game Mode(Push)", self.en)
        self.assertIn("Nearest Walkable Position", self.en)
        self.assertNotIn("All Players On Objective(All Teams)", self.en)
        self.assertNotIn("Teleport(Event Player, Objective Position(Objective Index));", self.en)
'''
dummy_tests = once(dummy_tests, needle, addition, "semantic fixture routing regression")
dummy_tests_path.write_text(dummy_tests, encoding="utf-8")
