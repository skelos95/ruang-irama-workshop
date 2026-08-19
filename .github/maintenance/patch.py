from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"

OLD_BLOB = "ab3617a0c2f08e7e435c6bf19ce45258c9f4a7af"


def blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def one(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one match, found {count}: {old[:160]!r}")
    return text.replace(old, new, 1)


source = SOURCE.read_text(encoding="utf-8")
if blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch moving target")

# 18f: death resets immediately. Never draw the Arcade menu while dead.
start = source.index('rule("18f - Nasib:')
end = source.index('\n\n\nrule("18g - Nasib:', start)
death = source[start:end]
old = '''\t\tWait(0.100, Ignore Condition);
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
if death.count(old) != 1:
    raise RuntimeError("18f death-screen menu block mismatch")
death = death.replace(old, "", 1)
if "Wait(" in death or "Loop If Condition Is True;" in death:
    raise RuntimeError("18f must not use Wait/Loop")
if "Call Subroutine(GambarMenu);" in death or "Event Player.MenuTerbuka = True;" in death:
    raise RuntimeError("18f must not draw/open menu while dead")
source = source[:start] + death + source[end:]
SOURCE.write_text(source, encoding="utf-8")
new_blob = blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = one(validator, f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"', f'EXPECTED_SOURCE_BLOB = "{new_blob}"')
old_checks = '''        checks.require("Wait(0.100, Ignore Condition);" in luck_death.body, "morte Try Your Luck non attende la transizione HUD prima del redraw")
        checks.require("Event Player.HalamanMenu = 10;" in luck_death.body and "Call Subroutine(GambarMenu);" in luck_death.body, "morte Try Your Luck non ridisegna il menu nella death screen")
'''
new_checks = '''        checks.require("Wait(" not in luck_death.body and "Loop If Condition Is True;" not in luck_death.body, "morte Try Your Luck deve resettare subito senza Wait o Loop")
        checks.require("Call Subroutine(GambarMenu);" not in luck_death.body and "Event Player.MenuTerbuka = True;" not in luck_death.body, "morte Try Your Luck non deve mostrare il menu prima del respawn")
'''
validator = one(validator, old_checks, new_checks)
old_reopen_guard = '        checks.require("Event Player.InputMenuDikunci = False;" in luck_reopen.body, "18g non libera il latch input del menu")\n'
new_reopen_guard = old_reopen_guard + '        checks.require("Wait(" not in luck_reopen.body and "Loop If Condition Is True;" not in luck_reopen.body, "18g riapertura al respawn non deve usare Wait o Loop")\n'
validator = one(validator, old_reopen_guard, new_reopen_guard)
VALIDATOR.write_text(validator, encoding="utf-8")

print(f"patched Workshop blob: {new_blob}")
