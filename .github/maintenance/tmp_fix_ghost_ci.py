from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_exact(path: str, old: str, new: str, expected: int = 1) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"{path}: expected {expected} occurrence(s), found {count}: {old[:120]!r}")
    target.write_text(text.replace(old, new), encoding="utf-8")
    print(f"patched {path}: {count} replacement(s)")


# The old roster-refresh flag is gone. The roster binding rule must not own Ghost state.
replace_exact(
    "tests/test_runtime_maintenance.py",
    '            self.assertIn("Event Player.GhostAktif = False;", roster)\n',
    "",
    expected=2,
)

# Keep the Dummy Follow validator scoped to page 12. Ghost has its own checks immediately below it.
replace_exact(
    "tools/validate_workshop.py",
    '''        for token in (\n            "12 - DUMMY FOLLOW",\n            "ENEMY DUMMY",\n            "12 - DUMMY MENGIKUTI",\n            "DUMMY MUSUH",\n            "12 - ดัมมี่ติดตาม",\n            "13 - GHOST MODE",\n            "13 - MODE GHOST",\n            "13 - โหมดผี",\n        ):\n            checks.require(token in dummy_follow_renderer.body,\n                           f"pagina 12 Dummy Follow non chiarisce il consenso localizzato: {token}")\n''',
    '''        for token in (\n            "12 - DUMMY FOLLOW",\n            "ENEMY DUMMY",\n            "12 - DUMMY MENGIKUTI",\n            "DUMMY MUSUH",\n            "12 - ดัมมี่ติดตาม",\n        ):\n            checks.require(token in dummy_follow_renderer.body,\n                           f"pagina 12 Dummy Follow non chiarisce il consenso localizzato: {token}")\n''',
)

# Mutation tests must target the new 14-page menu and its actual wraparound expression.
replace_exact(
    "tests/test_validate_workshop.py",
    '''    def test_all_thirteen_pages_are_routed(self) -> None:\n        router = self.rule(lambda rule: validator.subroutine_target(rule) == "GambarHalamanAktif")\n        mutated = self.replace_in_rule(router, "HalamanMenu == 12", "HalamanMenu == 13")\n        self.assert_rejected(mutated, "pagina 12")\n\n    def test_main_menu_cycles_exactly_over_pages_zero_through_twelve(self) -> None:\n        navigation = self.rule(\n            lambda rule: "Event Player.KursorUtama = (Event Player.KursorUtama" in rule.body\n        )\n        mutated = self.replace_in_rule(\n            navigation,\n            "(Event Player.PerintahMenu == 3 ? 1 : 12)) % 14;",\n            "(Event Player.PerintahMenu == 3 ? 1 : 11)) % 12;",\n        )\n        self.assert_rejected(mutated, "ciclo esatto 0..13")\n''',
    '''    def test_all_fourteen_pages_are_routed(self) -> None:\n        router = self.rule(lambda rule: validator.subroutine_target(rule) == "GambarHalamanAktif")\n        mutated = self.replace_in_rule(router, "HalamanMenu == 13", "HalamanMenu == 14")\n        self.assert_rejected(mutated, "pagina 13")\n\n    def test_main_menu_cycles_exactly_over_pages_zero_through_thirteen(self) -> None:\n        navigation = self.rule(\n            lambda rule: "Event Player.KursorUtama = (Event Player.KursorUtama" in rule.body\n        )\n        mutated = self.replace_in_rule(\n            navigation,\n            "(Event Player.PerintahMenu == 3 ? 1 : 13)) % 14;",\n            "(Event Player.PerintahMenu == 3 ? 1 : 12)) % 13;",\n        )\n        self.assert_rejected(mutated, "ciclo esatto 0..13")\n''',
)
replace_exact(
    "tests/test_validate_workshop.py",
    "def test_menu_open_message_announces_thirteen_pages_in_all_languages",
    "def test_menu_open_message_announces_fourteen_pages_in_all_languages",
)

# Documentation count must match indices 0..13.
replace_exact(
    "docs/PROGETTO.md",
    "le 13 pagine mantengono gli indici `0..13`",
    "le 14 pagine mantengono gli indici `0..13`",
)

print("Ghost CI repair complete")
