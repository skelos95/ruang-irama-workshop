from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
README = ROOT / "README.md"
PROGETTO = ROOT / "docs" / "PROGETTO.md"
TEST_DOC = ROOT / "docs" / "TEST.md"
VALIDAZIONE = ROOT / "docs" / "VALIDAZIONE.md"
GENERI = ROOT / "docs" / "GENERI.md"
VERSION = ROOT / "VERSION"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected 1 occurrence, found {count}")
    return text.replace(old, new, 1)


source = SOURCE.read_text(encoding="utf-8")

# Menu aperto: Melee e Jump devono restare azioni reali dell'eroe.
source = replace_once(
    source,
    "\t\t\tDisallow Button(Event Player, Button(Melee));\n\t\t\tDisallow Button(Event Player, Button(Jump));\n\t\t\tDisallow Button(Event Player, Button(Crouch));\n",
    "\t\t\tDisallow Button(Event Player, Button(Crouch));\n",
    "menu open allows Melee and Jump",
)

# Dispatcher Soundtrack: Ability 1 = +10, Ability 2 = -10. Jump/Crouch non sono più input menu.
source = replace_once(
    source,
    "\t\t\tEvent Player.HalamanMenu == 0, Or(Is Button Held(Event Player, Button(Jump)), Is Button Held(Event Player, Button(Crouch)))))) == True;\n",
    "\t\t\tEvent Player.HalamanMenu == 0, Or(Is Button Held(Event Player, Button(Ability 1)), Is Button Held(Event Player, Button(Ability 2)))))) == True;\n",
    "dispatcher soundtrack buttons condition",
)
source = replace_once(
    source,
    "\t\tElse If(And(Is Button Held(Event Player, Button(Jump)), Event Player.HalamanMenu == 0));\n\t\t\tEvent Player.PerintahMenu = 5;\n\t\tElse If(And(Is Button Held(Event Player, Button(Crouch)), Event Player.HalamanMenu == 0));\n\t\t\tEvent Player.PerintahMenu = 6;\n",
    "\t\tElse If(And(Is Button Held(Event Player, Button(Ability 1)), Event Player.HalamanMenu == 0));\n\t\t\tEvent Player.PerintahMenu = 5;\n\t\tElse If(And(Is Button Held(Event Player, Button(Ability 2)), Event Player.HalamanMenu == 0));\n\t\t\tEvent Player.PerintahMenu = 6;\n",
    "dispatcher soundtrack command mapping",
)
source = replace_once(
    source,
    "\t\t\tIs Button Held(Event Player, Button(Jump)) == False, Is Button Held(Event Player, Button(Crouch)) == False))) == True;\n",
    "\t\t\tIs Button Held(Event Player, Button(Ability 1)) == False, Is Button Held(Event Player, Button(Ability 2)) == False))) == True;\n",
    "dispatcher soundtrack release gate",
)

source = replace_once(
    source,
    'rule("08 - Menu 0: Lompat mundur sepuluh genre")',
    'rule("08 - Menu 0: Kemampuan 1 maju sepuluh genre")',
    "rule 08 title",
)
source = replace_once(
    source,
    "\t\tEvent Player.KursorGenre = (Event Player.KursorGenre + 90) % 100;\n\t}\n}\n\nrule(\"09 - Menu 0: Jongkok maju sepuluh genre\")",
    "\t\tEvent Player.KursorGenre = (Event Player.KursorGenre + 10) % 100;\n\t}\n}\n\nrule(\"09 - Menu 0: Kemampuan 2 mundur sepuluh genre\")",
    "rule 08 +10 and rule 09 title",
)
# Il +10 rimasto nella regola 09 diventa -10 (= +90 modulo 100).
needle = 'rule("09 - Menu 0: Kemampuan 2 mundur sepuluh genre")'
start = source.index(needle)
end = source.index('rule("10 - Menu:', start)
rule09 = source[start:end]
rule09 = replace_once(
    rule09,
    "\t\tEvent Player.KursorGenre = (Event Player.KursorGenre + 10) % 100;\n",
    "\t\tEvent Player.KursorGenre = (Event Player.KursorGenre + 90) % 100;\n",
    "rule 09 -10",
)
source = source[:start] + rule09 + source[end:]

# HUD Soundtrack: mostra i nuovi binding in tutte le lingue.
source = replace_once(
    source,
    'Custom String("{0}: back 10 | {1}: forward 10", Input Binding String(Button(Jump)), Input Binding String(Button(Crouch)))',
    'Custom String("{0}: +10 | {1}: -10", Input Binding String(Button(Ability 1)), Input Binding String(Button(Ability 2)))',
    "soundtrack EN x10 help",
)
source = replace_once(
    source,
    'Custom String("{0}: mundur 10 | {1}: maju 10", Input Binding String(Button(Jump)),\n\t\t\tInput Binding String(Button(Crouch)))',
    'Custom String("{0}: +10 | {1}: -10", Input Binding String(Button(Ability 1)),\n\t\t\tInput Binding String(Button(Ability 2)))',
    "soundtrack ID x10 help",
)
source = replace_once(
    source,
    'Custom String("{0}: ย้อน 10 | {1}: เดินหน้า 10", Input Binding String(Button(Jump)),\n\t\t\tInput Binding String(Button(Crouch)))',
    'Custom String("{0}: +10 | {1}: -10", Input Binding String(Button(Ability 1)),\n\t\t\tInput Binding String(Button(Ability 2)))',
    "soundtrack TH x10 help",
)

# Crouch Teleport: una persona con privacy ON non deve apparire come target e non può essere confermata da una lista stale.
old_targets = '''\t\tEvent Player.DaftarTargetTeleportasi = Append To Array(Array(Event Player, Null), Filtered Array(All Players(All Teams),
\t\t\tAnd(Current Array Element != Event Player, And(Entity Exists(Current Array Element), And(Has Spawned(Current Array Element), Is Alive(Current Array Element))))));
'''
new_targets = '''\t\tEvent Player.DaftarTargetTeleportasi = Append To Array(Array(Event Player, Null), Filtered Array(All Players(All Teams),
\t\t\tAnd(Current Array Element != Event Player, And(Player Variable(Current Array Element, PrivasiInspeksiAktif) == False, And(Entity Exists(Current Array Element), And(Has Spawned(Current Array Element), Is Alive(Current Array Element)))))));
'''
source = replace_once(source, old_targets, new_targets, "teleport privacy filter")

SOURCE.write_text(source, encoding="utf-8")

# Validator 0.6.12.
validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_once(validator, "della versione 0.6.11.", "della versione 0.6.12.", "validator doc version")
validator = replace_once(validator, 'CURRENT_VERSION = "0.6.11"', 'CURRENT_VERSION = "0.6.12"', "validator current version")

validator = validator.replace(
    'for button in ("Interact", "Reload", "Primary Fire", "Secondary Fire", "Jump", "Crouch")',
    'for button in ("Interact", "Reload", "Primary Fire", "Secondary Fire", "Ability 1", "Ability 2")',
)
validator = validator.replace(
    'for button in ("Interact", "Reload", "Primary Fire", "Secondary Fire", "Jump", "Crouch")\n        ]',
    'for button in ("Interact", "Reload", "Primary Fire", "Secondary Fire", "Ability 1", "Ability 2")\n        ]',
)
validator = validator.replace(
    '"priorità dispatcher errata; attesa Interact → Reload → Primary → Secondary → Jump → Crouch"',
    '"priorità dispatcher errata; attesa Interact → Reload → Primary → Secondary → Ability 1 → Ability 2"',
)
validator = validator.replace(
    'for label, command in (("Jump x10", 5), ("Crouch x10", 6)):',
    'for label, command in (("Ability 1 +10", 5), ("Ability 2 -10", 6)):',
)

# Associazione semantica dei due comandi Soundtrack.
anchor = '''    for label, command in (("Ability 1 +10", 5), ("Ability 2 -10", 6)):
        handler = handler_by_command[command]
        if handler is not None:
            checks.require(not code_contains(handler.body, "Call Subroutine(GambarMenu);"), f"{label}: redraw HUD inutile")
'''
extra = anchor + '''    if handler_by_command[5] is not None:
        checks.require(
            re.search(r"KursorGenre\\s*=\\s*\\([^;]+\\+\\s*10\\)\\s*%\\s*100", mask_strings(handler_by_command[5].body)) is not None,
            "Ability 1 non esegue +10 nel Soundtrack",
        )
    if handler_by_command[6] is not None:
        checks.require(
            re.search(r"KursorGenre\\s*=\\s*\\([^;]+\\+\\s*90\\)\\s*%\\s*100", mask_strings(handler_by_command[6].body)) is not None,
            "Ability 2 non esegue -10 nel Soundtrack",
        )
'''
validator = replace_once(validator, anchor, extra, "validator soundtrack command semantics")

# Melee/Jump devono rimanere fisicamente utilizzabili; Ability 1/2 restano bloccate come abilità reali per essere usate dal menu.
menu_open_anchor = '''    if menu_open_rules:
        opening = mask_strings(menu_open_rules[0].body)
        checks.require(
            "Event Player.KartuNasibAktif == False;" in opening,
            "Menu 10: Arcade Menu può ancora aprirsi durante la roulette",
        )
'''
menu_open_extra = menu_open_anchor + '''        checks.require(
            "Disallow Button(Event Player, Button(Melee));" not in opening,
            "Menu Arcade blocca ancora l'attacco Melee normale",
        )
        checks.require(
            "Disallow Button(Event Player, Button(Jump));" not in opening,
            "Menu Arcade blocca ancora il Jump normale",
        )
        checks.require(
            "Disallow Button(Event Player, Button(Ability 1));" in opening
            and "Disallow Button(Event Player, Button(Ability 2));" in opening,
            "Ability 1/2 devono restare disabilitate come abilità reali mentre comandano il Soundtrack",
        )
'''
validator = replace_once(validator, menu_open_anchor, menu_open_extra, "validator menu physical buttons")

# Dispatcher non deve più intercettare Jump/Crouch per ±10.
dispatcher_anchor = '''        checks.require(
            all(position >= 0 for position in positions) and positions == sorted(positions),
            "priorità dispatcher errata; attesa Interact → Reload → Primary → Secondary → Ability 1 → Ability 2",
        )
'''
dispatcher_extra = dispatcher_anchor + '''        checks.require(
            "Button(Jump)" not in dispatcher and "Button(Crouch)" not in dispatcher,
            "dispatcher menu intercetta ancora Jump/Crouch",
        )
'''
validator = replace_once(validator, dispatcher_anchor, dispatcher_extra, "validator dispatcher frees jump crouch")

# HUD Soundtrack deve dichiarare esplicitamente A1/A2 e non i vecchi Jump/Crouch.
insert_at = validator.index("    teleport_release = [")
soundtrack_hud_check = '''    soundtrack_renderers = rules_containing(rules, "Subroutine;", "GambarMusik;")
    checks.equal(len(soundtrack_renderers), 1, "renderer Soundtrack")
    if soundtrack_renderers:
        soundtrack_body = soundtrack_renderers[0].body
        checks.require(
            "Input Binding String(Button(Ability 1))" in soundtrack_body
            and "Input Binding String(Button(Ability 2))" in soundtrack_body,
            "HUD Soundtrack non mostra Ability 1/2 per ±10",
        )
        checks.require(
            "Input Binding String(Button(Jump))" not in soundtrack_body
            and "Input Binding String(Button(Crouch))" not in soundtrack_body,
            "HUD Soundtrack mostra ancora Jump/Crouch per ±10",
        )

'''
validator = validator[:insert_at] + soundtrack_hud_check + validator[insert_at:]

# Privacy: il refresh target Teleport deve escludere chi ha PrivasiInspeksiAktif.
teleport_anchor = '''    teleport_open_rules = [rule for rule in rules if code_contains(rule.body, "Event Player.TeleportasiJongkokAktif = True;")]
'''
privacy_check = '''    teleport_refresh_rules = rules_containing(rules, "Subroutine;", "SegarkanTargetTeleportasi;")
    checks.equal(len(teleport_refresh_rules), 1, "refresh target Crouch Teleport")
    if teleport_refresh_rules:
        checks.require(
            code_contains(
                teleport_refresh_rules[0].body,
                "Player Variable(Current Array Element, PrivasiInspeksiAktif) == False",
            ),
            "Crouch Teleport mostra ancora player con privacy attiva",
        )

'''
validator = replace_once(validator, teleport_anchor, privacy_check + teleport_anchor, "validator teleport privacy")

VALIDATOR.write_text(validator, encoding="utf-8")
VERSION.write_text("0.6.12\n", encoding="utf-8")

# Docs.
readme = README.read_text(encoding="utf-8")
readme = replace_once(readme, "La versione **0.6.11** identifica lo stato funzionale e tecnico corrente del repository.", "La versione **0.6.12** identifica lo stato funzionale e tecnico corrente del repository.", "README version")
readme = replace_once(readme, "| Sempre | Tieni Melee 0,5 s | Apre/chiude il Menu Arcade |", "| Sempre | Tieni Melee 0,5 s | Apre/chiude il Menu Arcade; il normale attacco Melee resta utilizzabile a menu aperto |", "README melee control")
readme = replace_once(readme, "| Soundtrack | Jump / Crouch | `−10` / `+10` generi |", "| Soundtrack | Ability 1 / Ability 2 | `+10` / `−10` generi |", "README soundtrack controls")
readme = replace_once(readme, "- player/bot validi.\n", "- player/bot validi, esclusi i player con **Crouch Privacy ON**.\n", "README teleport privacy")
readme += '''\n\n### Controlli menu e privacy Teleport 0.6.12\n\nCon il Menu Arcade aperto, **Melee e Jump restano azioni normali dell'eroe**: Melee può comunque chiudere il menu se viene tenuto per 0,5 s, mentre Jump non viene più intercettato dal dispatcher. Nel Soundtrack i salti rapidi diventano **Ability 1 = +10** e **Ability 2 = −10**; le due abilità reali restano bloccate finché il menu è aperto, quindi la pressione agisce soltanto sul cursore musicale. `SegarkanTargetTeleportasi` filtra inoltre qualunque player con `PrivasiInspeksiAktif == True`: il suo nome non appare nel Crouch Teleport e un target diventato privato prima della conferma viene rifiutato perché non è più presente nella lista aggiornata.\n'''
README.write_text(readme, encoding="utf-8")

progetto = PROGETTO.read_text(encoding="utf-8")
progetto = replace_once(progetto, "# Note di progetto — versione 0.6.11", "# Note di progetto — versione 0.6.12", "PROGETTO title")
progetto = replace_once(progetto, "Workshop 0.6.11.", "Workshop 0.6.12.", "PROGETTO version")
progetto = progetto.replace("Jump / Crouch", "Ability 1 / Ability 2")
progetto += '''\n\n## Input menu e privacy Teleport 0.6.12\n\nIl Menu Arcade non esegue più `Disallow Button` su Melee e Jump. Il dispatcher Soundtrack usa Ability 1/2 come comandi custom (+10/−10) mentre le abilità reali restano disabilitate dal menu. Crouch non è più usato per il salto +10. La lista Crouch Teleport esclude in fase di refresh ogni entità con `PrivasiInspeksiAktif == True`, mantenendo invariati Spawn Room e obiettivo.\n'''
PROGETTO.write_text(progetto, encoding="utf-8")

test_doc = TEST_DOC.read_text(encoding="utf-8")
test_doc = replace_once(test_doc, "# Piano di test — versione 0.6.11", "# Piano di test — versione 0.6.12", "TEST title")
test_doc = replace_once(test_doc, "Workshop 0.6.11.", "Workshop 0.6.12.", "TEST version")
test_doc += '''\n\n## Input menu / Soundtrack / privacy Teleport 0.6.12\n\nTest live: aprire il Menu Arcade e verificare che un tap Melee esegua il normale attacco, mentre un hold di 0,5 s continui a chiudere il menu; Jump deve saltare normalmente e, da morto, continuare a fare respawn manuale. Nel Soundtrack Ability 1 deve avanzare di 10 generi e Ability 2 arretrare di 10 senza attivare le abilità dell'eroe. Attivare Crouch Privacy su un secondo player: quel player non deve comparire nel Crouch Teleport; disattivando privacy deve ricomparire al refresh successivo.\n'''
TEST_DOC.write_text(test_doc, encoding="utf-8")

validazione = VALIDAZIONE.read_text(encoding="utf-8")
validazione = replace_once(validazione, "# Rapporto di validazione — versione 0.6.11", "# Rapporto di validazione — versione 0.6.12", "VALIDAZIONE title")
validazione = replace_once(validazione, "Release tecnica: **CHILL Dedicated Server 0.6.11**", "Release tecnica: **CHILL Dedicated Server 0.6.12**", "VALIDAZIONE release")
validazione = replace_once(validazione, "OK - controlli statici v0.6.11 superati", "OK - controlli statici v0.6.12 superati", "VALIDAZIONE result")
validazione += '''\n\n## Controlli input e privacy 0.6.12\n\nIl gate certifica che l'apertura Menu non disabiliti Melee/Jump, che Ability 1/2 restino disabilitate come abilità reali e siano gli unici comandi ±10 del Soundtrack, che il dispatcher/release gate non usino più Jump/Crouch e che il renderer Soundtrack mostri i binding aggiornati. `SegarkanTargetTeleportasi` deve includere il filtro `PrivasiInspeksiAktif == False`.\n'''

data = SOURCE.read_bytes().replace(b"\r\n", b"\n")
payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
blob = hashlib.sha1(payload).hexdigest()
validazione, count = re.subn(
    r"(Blob Git del sorgente Workshop validato:\n\n```text\n)[0-9a-f]{40}(\n```)",
    rf"\g<1>{blob}\g<2>",
    validazione,
    count=1,
)
if count != 1:
    raise RuntimeError("VALIDAZIONE blob marker not found")
VALIDAZIONE.write_text(validazione, encoding="utf-8")

# GENERI può contenere riferimenti descrittivi ai vecchi tasti; aggiorna solo la nomenclatura se presente.
generi = GENERI.read_text(encoding="utf-8")
generi = generi.replace("Jump / Crouch", "Ability 1 / Ability 2")
generi = generi.replace("Jump/Crouch", "Ability 1/Ability 2")
GENERI.write_text(generi, encoding="utf-8")

print("Applied CHILL 0.6.12 menu controls and teleport privacy update")
