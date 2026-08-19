from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
TESTS = ROOT / "tests" / "test_validate_workshop.py"

OLD_BLOB = "ab3617a0c2f08e7e435c6bf19ce45258c9f4a7af"


def blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def one(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one match, found {count}: {old[:180]!r}")
    return text.replace(old, new, 1)


source = SOURCE.read_text(encoding="utf-8")
if blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch moving target")

# Death must reset immediately and leave only the reopen request pending.
# No HUD is drawn while dead; 18g owns the only redraw once alive/spawned.
start = source.index('rule("18f - Nasib:')
end = source.index('\n\n\nrule("18g - Nasib:', start)
death = source[start:end]
old_tail = '''\t\tWait(0.100, Ignore Condition);
\t\tEvent Player.InputMenuDikunci = False;
\t\tEvent Player.PerintahMenu = 0;
\t\tAllow Button(Event Player, Button(Primary Fire));
\t\tAllow Button(Event Player, Button(Secondary Fire));
\t\tAllow Button(Event Player, Button(Interact));
\t\tAllow Button(Event Player, Button(Reload));
\t\tAllow Button(Event Player, Button(Ability 1));
\t\tAllow Button(Event Player, Button(Ability 2));
\t\tAllow Button(Event Player, Button(Ultimate));
\t\tEvent Player.MenuTerbuka = True;
\t\tEvent Player.HalamanMenu = 10;
\t\tEvent Player.HalamanMenuTujuan = 10;
\t\tCall Subroutine(GambarMenu);
'''
if old_tail not in death:
    raise RuntimeError("18f death-screen redraw block not found")
death = death.replace(old_tail, "", 1)
if "Wait(" in death or "Loop If Condition Is True;" in death or "Call Subroutine(GambarMenu);" in death:
    raise RuntimeError("18f must remain immediate and must not draw HUD while dead")
source = source[:start] + death + source[end:]

SOURCE.write_text(source, encoding="utf-8")
new_blob = blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = one(validator, f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"', f'EXPECTED_SOURCE_BLOB = "{new_blob}"')
validator = one(
    validator,
    '        checks.require("Wait(0.100, Ignore Condition);" in luck_death.body, "morte Try Your Luck non attende la transizione HUD prima del redraw")\n'
    '        checks.require("Event Player.HalamanMenu = 10;" in luck_death.body and "Call Subroutine(GambarMenu);" in luck_death.body, "morte Try Your Luck non ridisegna il menu nella death screen")\n',
    '        checks.require("Wait(" not in luck_death.body and "Loop If Condition Is True;" not in luck_death.body, "morte Try Your Luck deve resettare subito senza Wait o Loop")\n'
    '        checks.require("Call Subroutine(GambarMenu);" not in luck_death.body and "Event Player.MenuTerbuka = True;" not in luck_death.body, "morte Try Your Luck non deve mostrare il menu prima del respawn")\n',
)
validator = one(
    validator,
    '        checks.require("Event Player.InputMenuDikunci = False;" in luck_reopen.body, "18g non libera il latch input del menu")\n',
    '        checks.require("Event Player.InputMenuDikunci = False;" in luck_reopen.body, "18g non libera il latch input del menu")\n'
    '        checks.require("Wait(" not in luck_reopen.body and "Loop If Condition Is True;" not in luck_reopen.body, "18g riapertura al respawn non deve usare Wait o Loop")\n',
)
VALIDATOR.write_text(validator, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
anchor = '''    def test_try_your_luck_reopen_waits_for_alive_respawn(self) -> None:
        start = self.source.index('rule(\\"18g - Nasib:')
        pos = self.source.index("Is Alive(Event Player) == True;", start)
        mutated = self.source[:pos] + self.source[pos:].replace(
            "Is Alive(Event Player) == True;",
            "Is Alive(Event Player) == False;",
            1,
        )
        self.assertTrue(any("respawn vivo" in error for error in self.errors(mutated)))

'''
extra = anchor + '''    def test_try_your_luck_death_never_draws_menu(self) -> None:
        start = self.source.index('rule(\\"18f - Nasib:')
        end = self.source.index('rule(\\"18g - Nasib:', start)
        death = self.source[start:end]
        self.assertNotIn("Wait(", death)
        self.assertNotIn("Loop If Condition Is True;", death)
        self.assertNotIn("Call Subroutine(GambarMenu);", death)
        self.assertNotIn("Event Player.MenuTerbuka = True;", death)

'''
tests = one(tests, anchor, extra)
TESTS.write_text(tests, encoding="utf-8")

print(f"patched Workshop blob: {new_blob}")
