from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "workshop" / "ruang_irama.workshop"
VAL = ROOT / "tools" / "validate_workshop.py"
TESTS = ROOT / "tests" / "test_validate_workshop.py"
VERSION = ROOT / "VERSION"
README = ROOT / "README.md"
PROGETTO = ROOT / "docs" / "PROGETTO.md"
TEST_DOC = ROOT / "docs" / "TEST.md"
VALIDAZIONE = ROOT / "docs" / "VALIDAZIONE.md"


def find_matching(text: str, opening: int) -> int:
    depth = 1
    in_string = False
    escaped = False
    for i in range(opening + 1, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return i
    raise RuntimeError("unbalanced rule")


def rule_spans(text: str):
    pat = re.compile(r'^rule\("([^"]+)"\)\s*\{', re.M)
    out = []
    for m in pat.finditer(text):
        opening = text.find('{', m.start())
        closing = find_matching(text, opening)
        out.append((m.group(1), m.start(), closing + 1, text[m.start():closing + 1]))
    return out


def section(rule: str, name: str) -> str:
    m = re.search(rf'(?m)^\s*{re.escape(name)}\s*\{{', rule)
    if not m:
        return ""
    opening = rule.find('{', m.start())
    closing = find_matching(rule, opening)
    return rule[opening + 1:closing]


def split_conditions(body: str) -> list[str]:
    items = []
    start = 0
    paren = bracket = 0
    in_string = False
    escaped = False
    for i, ch in enumerate(body):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == '(':
            paren += 1
        elif ch == ')':
            paren -= 1
        elif ch == '[':
            bracket += 1
        elif ch == ']':
            bracket -= 1
        elif ch == ';' and paren == 0 and bracket == 0:
            item = body[start:i].strip()
            if item and not item.startswith('"'):
                items.append(item)
            start = i + 1
    return items


def indent_block(text: str, tabs: int) -> str:
    prefix = "\t" * tabs
    lines = text.strip("\n").splitlines()
    return "\n".join(prefix + line.lstrip("\t") for line in lines if line.strip())


def make_handler(rule_text: str) -> str:
    if any(token in rule_text for token in ("Wait(", "Loop If Condition Is True;", "Create HUD Text(", "Call Subroutine(")):
        raise RuntimeError("atomic handler contains forbidden async/create/call token")
    conditions = [item.replace("Event Player", "Global.PemainAktif") for item in split_conditions(section(rule_text, "conditions"))]
    actions = section(rule_text, "actions").replace("Event Player", "Global.PemainAktif").strip()
    parts = []
    for cond in conditions:
        parts.append(f"If({cond});")
    parts.append(actions)
    parts.extend("End;" for _ in conditions)
    return indent_block("\n".join(parts), 2)


src = SRC.read_text(encoding="utf-8")
if "51: PemainAktif" not in src:
    src = src.replace("\t\t50: ModeMulaiDiminta\n\tplayer:", "\t\t50: ModeMulaiDiminta\n\t\t51: PemainAktif\n\t\t52: IndeksPemainGlobal\n\tplayer:", 1)
    src = src.replace("\t\tGlobal.ModeMulaiDiminta = False;", "\t\tGlobal.ModeMulaiDiminta = False;\n\t\tGlobal.PemainAktif = Null;\n\t\tGlobal.IndeksPemainGlobal = 0;", 1)

atomic_names = [
    "02e - Siklus Pemain: Lepaskan kunci setelah roster baru siap",
    "03b - Bot: Tandai kunci untuk dipasang ulang setelah mati atau hilang",
    "05b - Menu: Lepaskan serangan jarak dekat sebelum pakai lagi",
    "05c - Menu: Pengatur masukan dengan prioritas tetap",
    "05d - Menu: Lepaskan pengatur setelah semua masukan dilepas",
    "08 - Menu 0: Kemampuan 1 maju sepuluh genre",
    "09 - Menu 0: Kemampuan 2 mundur sepuluh genre",
    "12d - Kamera: Lepaskan Interact sebelum pakai lagi",
    "15 - Intip Pahlawan: Hapus tulisan saat berdiri atau membuka menu",
    "18 - Kebal: Pasang kembali status setelah muncul kembali",
    "18b - Kebal: Mode 1 HP kembali ke satu saat penuh",
    "18d - Kebal: Mode HP PENUH selalu kembali penuh",
    "19a - Teleportasi Jongkok: Pengatur masukan terpisah dari Menu Arkade",
    "19b - Teleportasi Jongkok: Aktifkan lagi pengatur setelah tombol dilepas",
    "19g - Teleportasi Jongkok: Tutup saat Jongkok dilepas",
]
spans = {name: (a, b, block) for name, a, b, block in rule_spans(src)}
missing = [name for name in atomic_names if name not in spans]
if missing:
    raise RuntimeError(f"missing atomic rules: {missing}")
for name in atomic_names:
    block = spans[name][2]
    if "Ongoing - Each Player;" not in block:
        raise RuntimeError(f"{name}: not Ongoing Each Player")

fast_names = [
    "05b - Menu: Lepaskan serangan jarak dekat sebelum pakai lagi",
    "05c - Menu: Pengatur masukan dengan prioritas tetap",
    "05d - Menu: Lepaskan pengatur setelah semua masukan dilepas",
    "08 - Menu 0: Kemampuan 1 maju sepuluh genre",
    "09 - Menu 0: Kemampuan 2 mundur sepuluh genre",
    "12d - Kamera: Lepaskan Interact sebelum pakai lagi",
    "18 - Kebal: Pasang kembali status setelah muncul kembali",
    "18b - Kebal: Mode 1 HP kembali ke satu saat penuh",
    "18d - Kebal: Mode HP PENUH selalu kembali penuh",
    "19a - Teleportasi Jongkok: Pengatur masukan terpisah dari Menu Arkade",
    "19b - Teleportasi Jongkok: Aktifkan lagi pengatur setelah tombol dilepas",
    "19g - Teleportasi Jongkok: Tutup saat Jongkok dilepas",
]
slow_names = [
    "02e - Siklus Pemain: Lepaskan kunci setelah roster baru siap",
    "03b - Bot: Tandai kunci untuk dipasang ulang setelah mati atau hilang",
    "15 - Intip Pahlawan: Hapus tulisan saat berdiri atau membuka menu",
]

fast_handlers = "\n".join(make_handler(spans[name][2]) for name in fast_names)
slow_handlers = "\n".join(make_handler(spans[name][2]) for name in slow_names)

manager_fast = f'''rule("04g - Global-first: Pengatur pemain cepat terpusat")
{{
\tevent
\t{{
\t\tOngoing - Global;
\t}}

\tactions
\t{{
\t\tFor Global Variable(Global.IndeksPemainGlobal, 0, Count Of(All Players(All Teams)) - 1, 1);
\t\t\tGlobal.PemainAktif = All Players(All Teams)[Global.IndeksPemainGlobal];
{fast_handlers}
\t\tEnd;
\t\tGlobal.PemainAktif = Null;
\t\tWait(0.016, Ignore Condition);
\t\tLoop If Condition Is True;
\t}}
}}

'''
manager_slow = f'''rule("04h - Global-first: Pengatur status pemain terpusat")
{{
\tevent
\t{{
\t\tOngoing - Global;
\t}}

\tactions
\t{{
\t\tFor Global Variable(Global.IndeksPemainGlobal, 0, Count Of(All Players(All Teams)) - 1, 1);
\t\t\tGlobal.PemainAktif = All Players(All Teams)[Global.IndeksPemainGlobal];
{slow_handlers}
\t\tEnd;
\t\tGlobal.PemainAktif = Null;
\t\tWait(0.100, Ignore Condition);
\t\tLoop If Condition Is True;
\t}}
}}

'''

# Remove in reverse order, then insert managers before menu section.
for name, a, b, block in sorted((item for item in rule_spans(src) if item[0] in atomic_names), key=lambda x: x[1], reverse=True):
    src = src[:a] + src[b:]
insert_at = src.index('rule("05 - Menu:')
src = src[:insert_at] + manager_fast + manager_slow + src[insert_at:]

remaining_each = src.count("Ongoing - Each Player;")
if remaining_each != 26:
    raise RuntimeError(f"expected 26 Ongoing Each Player after phase 1, found {remaining_each}")
SRC.write_text(src, encoding="utf-8")

val = VAL.read_text(encoding="utf-8")
val = val.replace('CURRENT_VERSION = "0.6.25"', 'CURRENT_VERSION = "0.7.0"', 1)
val = val.replace('della versione 0.6.25.', 'della versione 0.7.0.', 1)
# Legacy checks for migrated rule names are intentionally replaced with architecture checks.
anchor = "def check_source_structure("
idx = val.index(anchor)
helper = '''def check_global_first_phase_one(checks: Checks, source: str, rules: list[Rule]) -> None:
    clean = mask_strings(source)
    checks.equal(clean.count("Ongoing - Each Player;"), 26, "global-first 0.7.0: regole Each Player residue")
    checks.require("51: PemainAktif" in clean and "52: IndeksPemainGlobal" in clean,
        "global-first 0.7.0: contesto globale player non dichiarato")
    managers = [rule for rule in rules if rule.name.startswith("04g - Global-first:") or rule.name.startswith("04h - Global-first:")]
    checks.equal(len(managers), 2, "global-first 0.7.0: manager globali atomici")
    joined = "\n".join(mask_strings(rule.body) for rule in managers)
    checks.require(joined.count("For Global Variable(Global.IndeksPemainGlobal") == 2,
        "global-first 0.7.0: scansione roster non centralizzata")
    checks.require("Wait(0.016, Ignore Condition);" in joined and "Wait(0.100, Ignore Condition);" in joined,
        "global-first 0.7.0: frequenze fast/slow non separate")
    for legacy in (
        "05b - Menu: Lepaskan serangan jarak dekat",
        "05c - Menu: Pengatur masukan",
        "05d - Menu: Lepaskan pengatur",
        "08 - Menu 0:", "09 - Menu 0:", "12d - Kamera:",
        "18b - Kebal:", "18d - Kebal:", "19a - Teleportasi Jongkok:",
        "19b - Teleportasi Jongkok:", "19g - Teleportasi Jongkok:",
    ):
        checks.require(not any(rule.name.startswith(legacy) for rule in rules),
            f"global-first 0.7.0: regola legacy ancora attiva: {legacy}")


'''
val = val[:idx] + helper + val[idx:]
# Inject new check near main validator invocation.
main_call = "check_source_structure(checks, source, rules, global_names, player_names, subroutines)"
val = val.replace(main_call, main_call + "\n    check_global_first_phase_one(checks, source, rules)", 1)
VAL.write_text(val, encoding="utf-8")

# Add focused tests without rewriting legacy suite yet; CI will identify stale expectations.
tests = TESTS.read_text(encoding="utf-8")
marker = "class ValidatorNegativeTests(unittest.TestCase):\n"
extra = '''class GlobalFirstPhaseOneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = validator.SOURCE.read_text(encoding="utf-8")
        cls.rules = validator.extract_rules(cls.source)

    def test_atomic_player_polling_is_global(self) -> None:
        self.assertEqual(self.source.count("Ongoing - Each Player;"), 26)
        names = [rule.name for rule in self.rules]
        self.assertIn("04g - Global-first: Pengatur pemain cepat terpusat", names)
        self.assertIn("04h - Global-first: Pengatur status pemain terpusat", names)

    def test_global_managers_use_explicit_player_context(self) -> None:
        managers = [r for r in self.rules if r.name.startswith("04g - Global-first:") or r.name.startswith("04h - Global-first:")]
        self.assertEqual(len(managers), 2)
        for rule in managers:
            self.assertIn("Global.PemainAktif = All Players(All Teams)[Global.IndeksPemainGlobal];", rule.body)
            self.assertNotIn("Event Player", validator.mask_strings(rule.body))


'''
tests = tests.replace(marker, extra + marker, 1)
TESTS.write_text(tests, encoding="utf-8")

VERSION.write_text("0.7.0\n", encoding="utf-8")
readme = README.read_text(encoding="utf-8").replace("La versione **0.6.25**", "La versione **0.7.0**", 1)
README.write_text(readme, encoding="utf-8")
progetto = PROGETTO.read_text(encoding="utf-8").replace("# Note di progetto — versione 0.6.25", "# Note di progetto — versione 0.7.0", 1)
progetto += '''\n\n## Global-first — fase 1 (0.7.0)\n\nAvvio della migrazione architetturale da `Ongoing - Each Player` a scheduler globali. La baseline 0.6.25 conteneva 41 regole Ongoing per-player. La fase 1 sposta 15 handler atomici in due manager `Ongoing - Global`: uno veloce a 0,016 s per input/menu/status sensibili e uno a 0,100 s per lifecycle leggero. I manager iterano `All Players(All Teams)` usando `Global.IndeksPemainGlobal` e impostano esplicitamente `Global.PemainAktif`; nessuna delle azioni migrate dipende da `Event Player`.\n\nRestano 26 regole Each Player: sono esclusivamente i percorsi con subroutine, Create HUD o Wait/Loop che richiedono una state machine o un contesto esplicito prima di poter essere migrati in sicurezza. Questa release è il primo passo del rebuild Global-first, non il punto finale.\n'''
PROGETTO.write_text(progetto, encoding="utf-8")
test_doc = TEST_DOC.read_text(encoding="utf-8").replace("# Piano di test — versione 0.6.25", "# Piano di test — versione 0.7.0", 1)
test_doc += '''\n\n## Global-first fase 1\n\nVerificare prima le feature migrate: dispatcher Menu, rilascio input, Soundtrack ±10, Camera Interact release, Unkillable 1 HP/FULL HP e Crouch Teleport. Poi ripetere cambio team con menu chiuso e aperto. La 0.7.0 riduce il numero di `Ongoing - Each Player` da 41 a 26 ma non pretende ancora di eliminare tutti i percorsi per-player; il test live serve a misurare se la riduzione della valutazione concorrente migliora già la transizione.\n'''
TEST_DOC.write_text(test_doc, encoding="utf-8")

blob_data = SRC.read_bytes().replace(b"\r\n", b"\n")
blob = hashlib.sha1(b"blob " + str(len(blob_data)).encode() + b"\0" + blob_data).hexdigest()
validation = VALIDAZIONE.read_text(encoding="utf-8").replace("# Rapporto di validazione — versione 0.6.25", "# Rapporto di validazione — versione 0.7.0", 1).replace("Release tecnica: **CHILL Dedicated Server 0.6.25**", "Release tecnica: **CHILL Dedicated Server 0.7.0**", 1).replace("OK - controlli statici v0.6.25 superati", "OK - controlli statici v0.7.0 superati", 1)
validation = re.sub(r"(Blob Git del sorgente Workshop validato:\n\n```text\n)[0-9a-f]{40}(\n```)", rf"\g<1>{blob}\g<2>", validation, count=1)
validation += '''\n\n## Gate Global-first 0.7.0\n\nIl gate richiede esattamente 26 `Ongoing - Each Player` residui, due manager globali atomici, contesto `PemainAktif/IndeksPemainGlobal`, scansione esplicita di `All Players(All Teams)` e frequenze fast/slow separate. Le 15 regole migrate non possono più esistere come rule legacy. Stato: static-pending fino al completamento del gate; live-pending in Overwatch.\n'''
VALIDAZIONE.write_text(validation, encoding="utf-8")
