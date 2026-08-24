from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def expect_replace(text: str, old: str, new: str, *, count: int = 1, label: str = "replace") -> str:
    found = text.count(old)
    if found != count:
        raise SystemExit(f"{label}: expected {count} occurrence(s), found {found}: {old[:120]!r}")
    return text.replace(old, new, count)


def matching_brace(text: str, opening: int) -> int:
    depth = 1
    in_string = False
    escaped = False
    for i in range(opening + 1, len(text)):
        c = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                in_string = False
            continue
        if c == '"':
            in_string = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
    raise SystemExit("unclosed rule block")


def edit_rule(text: str, keyword: str, name: str, fn) -> str:
    marker = f'{keyword}("{name}")'
    start = text.find(marker)
    if start < 0:
        raise SystemExit(f"rule not found: {name}")
    opening = text.find("{", start)
    closing = matching_brace(text, opening)
    block = text[start:closing + 1]
    changed = fn(block)
    if changed == block:
        raise SystemExit(f"rule unchanged unexpectedly: {name}")
    return text[:start] + changed + text[closing + 1:]


def patch_workshop(path: Path, keyword: str, g: str) -> None:
    text = path.read_text(encoding="utf-8")
    text = expect_replace(
        text,
        "\t\t53: JarakBidik\n",
        "\t\t53: JarakBidik\n\t\t54: PemainSiklusGlobal\n\t\t55: WaktuSiklusGlobal\n",
        label=f"{path.name} global declarations",
    )
    text = expect_replace(
        text,
        f"\t\t{g}.LangkahPenjadwal = 0;\n",
        f"\t\t{g}.LangkahPenjadwal = 0;\n\t\t{g}.PemainSiklusGlobal = Null;\n\t\t{g}.WaktuSiklusGlobal = 0;\n",
        label=f"{path.name} global init",
    )

    def cleanup_worker(block: str) -> str:
        block = expect_replace(
            block,
            "\t\tEvent Player.PindahTimDiproses == True;\n\t\tEvent Player.SiklusPemainAktif == True;",
            f"\t\tEvent Player.PindahTimDiproses == True;\n\t\t{g}.PemainSiklusGlobal == Event Player;\n\t\tEvent Player.SiklusPemainAktif == True;",
            label="cleanup worker global owner",
        )
        block = block.replace("Total Time Elapsed + 0.100;", "Total Time Elapsed + 0.250;")
        if "Total Time Elapsed + 0.250;" not in block:
            raise SystemExit("cleanup worker cooldown not updated")
        return block

    def setup_worker(block: str) -> str:
        return expect_replace(
            block,
            "\t\tEvent Player.PindahTimDiproses == True;\n\t\tEvent Player.SiklusPemainAktif == False;",
            f"\t\tEvent Player.PindahTimDiproses == True;\n\t\t{g}.PemainSiklusGlobal == Event Player;\n\t\tEvent Player.SiklusPemainAktif == False;",
            label="setup worker global owner",
        )

    text = edit_rule(text, keyword, "01 - Siklus tim: Pekerja pembersihan dari penjadwal global", cleanup_worker)
    text = edit_rule(text, keyword, "01b - Siklus tim: Pekerja penyiapan dari penjadwal global", setup_worker)

    def left_rule(block: str) -> str:
        if "Wait(0.100," not in block:
            raise SystemExit("leave wait 0.100 not found")
        block = block.replace("Wait(0.100,", "Wait(0.500,", 1)
        anchor = "\t\tCall Subroutine(BersihkanPemain);\n"
        if block.count(anchor) != 1:
            raise SystemExit(f"leave cleanup anchor count {block.count(anchor)}")
        extra = (
            anchor
            + f"\t\tIf({g}.PemainSiklusGlobal == Event Player);\n"
            + f"\t\t\t{g}.PemainSiklusGlobal = Null;\n"
            + f"\t\t\t{g}.WaktuSiklusGlobal = Total Time Elapsed + 0.250;\n"
            + "\t\tEnd;\n"
        )
        return block.replace(anchor, extra, 1)

    text = edit_rule(text, keyword, "04 - Pemain Keluar: Bersihkan hanya saat benar-benar keluar", left_rule)

    def scheduler(block: str) -> str:
        scan_anchor = "\t\t\"Indeks dan pemain aktif hanya dimiliki penjadwal; tidak ada jeda selama pemindaian.\"\n"
        stale = (
            f"\t\tIf(And({g}.PemainSiklusGlobal != Null, Entity Exists({g}.PemainSiklusGlobal) == False));\n"
            f"\t\t\t{g}.PemainSiklusGlobal = Null;\n"
            f"\t\t\t{g}.WaktuSiklusGlobal = Total Time Elapsed + 0.250;\n"
            "\t\tEnd;\n"
        )
        block = expect_replace(block, scan_anchor, stale + scan_anchor, label="scheduler stale lifecycle owner")
        block = expect_replace(
            block,
            "\t\t\tCall Subroutine(ProsesNasibPemain);\n",
            f"\t\t\tIf(Or({g}.PemainSiklusGlobal == Null, {g}.PemainAktif == {g}.PemainSiklusGlobal));\n\t\t\t\tCall Subroutine(ProsesNasibPemain);\n\t\t\tEnd;\n",
            label="scheduler luck lifecycle gate",
        )
        block = expect_replace(
            block,
            f"\t\t\tIf({g}.LangkahPenjadwal % 2 == 0);\n\t\t\t\tCall Subroutine(ProsesSiklusPemain);\n\t\t\tEnd;",
            f"\t\t\tIf(And({g}.LangkahPenjadwal % 2 == 0, Or({g}.PemainSiklusGlobal == Null, {g}.PemainAktif == {g}.PemainSiklusGlobal)));\n\t\t\t\tCall Subroutine(ProsesSiklusPemain);\n\t\t\tEnd;",
            label="scheduler 10Hz lifecycle gate",
        )
        block = expect_replace(
            block,
            f"\t\t\tIf({g}.LangkahPenjadwal % 20 == 0);\n\t\t\t\tCall Subroutine(ProsesCachePemain);\n\t\t\tEnd;",
            f"\t\t\tIf(And({g}.LangkahPenjadwal % 20 == 0, {g}.PemainSiklusGlobal == Null));\n\t\t\t\tCall Subroutine(ProsesCachePemain);\n\t\t\tEnd;",
            label="scheduler cache lifecycle gate",
        )
        return block

    text = edit_rule(text, keyword, "04g - Utama global: Penjadwal pusat 20 Hz", scheduler)

    def fast(block: str) -> str:
        if "WaktuSiklusTim = Total Time Elapsed + 0.100;" not in block:
            raise SystemExit("fast lifecycle timestamp not found")
        block = block.replace("WaktuSiklusTim = Total Time Elapsed + 0.100;", "WaktuSiklusTim = Total Time Elapsed + 0.250;", 1)
        anchor = f"\t\tIf(And({g}.PemainAktif.Manusia == True, Or("
        pos = block.find(anchor)
        if pos < 0:
            raise SystemExit("fast post-detection anchor not found")
        acquire = (
            f"\t\tIf(And({g}.PemainSiklusGlobal == Null, And({g}.PemainAktif.PindahTimDiproses == True, And({g}.PemainAktif.BotOtomatis == False, And(Entity Exists({g}.PemainAktif) == True, And(Total Time Elapsed >= {g}.WaktuSiklusGlobal, Server Load < 150))))));\n"
            f"\t\t\t{g}.PemainSiklusGlobal = {g}.PemainAktif;\n"
            "\t\tEnd;\n"
        )
        block = block[:pos] + acquire + block[pos:]
        return block

    text = edit_rule(text, keyword, "89a - Subrutin: Proses status cepat pemain", fast)

    def cycle(block: str) -> str:
        anchor = f"\t\t\t{g}.PemainAktif.WaktuSiklusTim = 0;\n"
        if block.count(anchor) != 1:
            raise SystemExit(f"cycle release timestamp anchor count {block.count(anchor)}")
        repl = (
            anchor
            + f"\t\t\tIf({g}.PemainSiklusGlobal == {g}.PemainAktif);\n"
            + f"\t\t\t\t{g}.PemainSiklusGlobal = Null;\n"
            + f"\t\t\t\t{g}.WaktuSiklusGlobal = Total Time Elapsed + 0.250;\n"
            + "\t\t\tEnd;\n"
        )
        return block.replace(anchor, repl, 1)

    text = edit_rule(text, keyword, "89b - Subrutin: Proses siklus pemain 10 Hz", cycle)
    path.write_text(text, encoding="utf-8")


patch_workshop(ROOT / "workshop" / "ruang_irama.it-IT.workshop", "regola", "Globale")
patch_workshop(ROOT / "tests" / "fixtures" / "semantic_reference.txt", "rule", "Global")

# Version + validator contract.
version = ROOT / "VERSION"
version.write_text("0.8.1\n", encoding="utf-8")
validator = ROOT / "tools" / "validate_workshop.py"
v = validator.read_text(encoding="utf-8")
v = v.replace("Workshop 0.8.0", "Workshop 0.8.1", 1)
v = expect_replace(v, 'CURRENT_VERSION = "0.8.0"', 'CURRENT_VERSION = "0.8.1"', label="validator version")
v = expect_replace(v, '("leave ordering", ("0.100", "Ignore Condition")): 1,', '("leave ordering", ("0.500", "Ignore Condition")): 1,', label="validator leave wait")
v = v.replace('"Global.PemainAktif.WaktuSiklusTim = Total Time Elapsed + 0.100;",', '"Global.PemainAktif.WaktuSiklusTim = Total Time Elapsed + 0.250;",', 1)
v = v.replace('"Event Player.WaktuSiklusTim = Total Time Elapsed + 0.100;" in cleanup_worker.body,\n                       "worker cleanup non separa cleanup/setup di 0,100 s"', '"Event Player.WaktuSiklusTim = Total Time Elapsed + 0.250;" in cleanup_worker.body,\n                       "worker cleanup non separa cleanup/setup di 0,250 s"', 1)
# Add global owner requirement to both lifecycle workers.
v = v.replace('"Event Player.PindahTimDiproses == True;",\n            "Event Player.SiklusPemainAktif == True;",', '"Event Player.PindahTimDiproses == True;",\n            "Global.PemainSiklusGlobal == Event Player;",\n            "Event Player.SiklusPemainAktif == True;",', 1)
v = v.replace('"Event Player.PindahTimDiproses == True;",\n            "Event Player.SiklusPemainAktif == False;",', '"Event Player.PindahTimDiproses == True;",\n            "Global.PemainSiklusGlobal == Event Player;",\n            "Event Player.SiklusPemainAktif == False;",', 1)
# Extend fast-dispatch contract with lock acquisition.
needle = '"Global.PemainAktif.WaktuSiklusTim = Total Time Elapsed + 0.250;",\n        ):'
if needle not in v:
    raise SystemExit("validator fast token tuple anchor missing")
v = v.replace(needle, '"Global.PemainAktif.WaktuSiklusTim = Total Time Elapsed + 0.250;",\n            "Global.PemainSiklusGlobal == Null",\n            "Global.PemainSiklusGlobal = Global.PemainAktif;",\n            "Global.WaktuSiklusGlobal",\n        ):', 1)
# Extend stable release contract.
needle = '(r"Global\\.PemainAktif\\.WaktuSiklusTim\\s*=\\s*0;", "rilascio timestamp lifecycle"),'
if needle not in v:
    raise SystemExit("validator stable pattern anchor missing")
v = v.replace(needle, needle + '\n            (r"Global\\.PemainSiklusGlobal\\s*=\\s*Null;", "rilascio lock lifecycle globale"),\n            (r"Global\\.WaktuSiklusGlobal\\s*=\\s*Total Time Elapsed \\+ 0\\.250;", "cooldown lifecycle globale"),', 1)
# Require scheduler throttling during a lifecycle transaction.
scheduler_anchor = 'checks.require(fast is not None, "dispatcher lifecycle globale ProsesCepatPemain assente")\n'
if scheduler_anchor not in v:
    raise SystemExit("validator lifecycle scheduler anchor missing")
v = v.replace(scheduler_anchor, scheduler_anchor + '    scheduler = next((rule for rule in rules if event_type(rule) == "Ongoing - Global" and action_loop_count(rule.body) == 1), None)\n    checks.require(scheduler is not None, "scheduler globale lifecycle assente")\n    if scheduler:\n        for token in (\n            "Global.PemainSiklusGlobal != Null",\n            "Entity Exists(Global.PemainSiklusGlobal) == False",\n            "Or(Global.PemainSiklusGlobal == Null, Global.PemainAktif == Global.PemainSiklusGlobal)",\n            "And(Global.LangkahPenjadwal % 20 == 0, Global.PemainSiklusGlobal == Null)",\n        ):\n            checks.require(token in scheduler.body, f"scheduler non serializza/throttla il lifecycle: {token}")\n', 1)
validator.write_text(v, encoding="utf-8")

# Runtime regression test: replace the existing team-switch method (last method in file).
test_path = ROOT / "tests" / "test_runtime_maintenance.py"
t = test_path.read_text(encoding="utf-8")
start = t.index("    def test_team_switch_lifecycle_is_global_first_and_load_guarded")
end = t.index("\nif __name__ == \"__main__\":", start)
method = '''    def test_team_switch_lifecycle_is_globally_serialized_and_load_guarded(self):
        for source, global_name, rule_kw in ((self.it, "Globale", "regola"), (self.en, "Global", "rule")):
            self.assertNotIn("Player Joined Match;", source)
            self.assertIn("54: PemainSiklusGlobal", source)
            self.assertIn("55: WaktuSiklusGlobal", source)
            self.assertIn(f"{global_name}.PemainSiklusGlobal = Null;", source)

            fast = source.split(f'{rule_kw}("89a - Subrutin: Proses status cepat pemain")', 1)[1].split(f'{rule_kw}("89b - Subrutin: Proses siklus pemain 10 Hz")', 1)[0]
            self.assertIn(f"{global_name}.PemainAktif.TimTerakhir != Team Of({global_name}.PemainAktif)", fast)
            self.assertIn(f"{global_name}.PemainAktif.PindahTimDiproses = True;", fast)
            self.assertIn(f"{global_name}.PemainAktif.WaktuSiklusTim = Total Time Elapsed + 0.250;", fast)
            self.assertIn(f"{global_name}.PemainSiklusGlobal == Null", fast)
            self.assertIn(f"{global_name}.PemainSiklusGlobal = {global_name}.PemainAktif;", fast)
            self.assertIn("Server Load < 150", fast)

            cleanup = source.split(f'{rule_kw}("01 - Siklus tim: Pekerja pembersihan dari penjadwal global")', 1)[1].split(f'{rule_kw}("01b - Siklus tim: Pekerja penyiapan dari penjadwal global")', 1)[0]
            self.assertIn(f"{global_name}.PemainSiklusGlobal == Event Player;", cleanup)
            self.assertIn("Event Player.SiklusPemainAktif == True;", cleanup)
            self.assertIn("Server Load < 150;", cleanup)
            self.assertIn("Event Player.WaktuSiklusTim = Total Time Elapsed + 0.250;", cleanup)
            self.assertNotIn("Wait(", cleanup)

            setup = source.split(f'{rule_kw}("01b - Siklus tim: Pekerja penyiapan dari penjadwal global")', 1)[1].split(f'{rule_kw}("02 - Pemain: Pisahkan manusia dari pasukan kaleng")', 1)[0]
            self.assertIn(f"{global_name}.PemainSiklusGlobal == Event Player;", setup)
            self.assertIn("Event Player.SiklusPemainAktif == False;", setup)
            self.assertIn("Server Load < 150;", setup)
            self.assertNotIn("Wait(", setup)

            scheduler = source.split(f'{rule_kw}("04g - Utama global: Penjadwal pusat 20 Hz")', 1)[1].split(f'{rule_kw}("05 -', 1)[0]
            self.assertIn(f"Entity Exists({global_name}.PemainSiklusGlobal) == False", scheduler)
            self.assertIn(f"Or({global_name}.PemainSiklusGlobal == Null, {global_name}.PemainAktif == {global_name}.PemainSiklusGlobal)", scheduler)
            self.assertIn(f"And({global_name}.LangkahPenjadwal % 20 == 0, {global_name}.PemainSiklusGlobal == Null)", scheduler)

            cycle = source.split(f'{rule_kw}("89b - Subrutin: Proses siklus pemain 10 Hz")', 1)[1].split(f'{rule_kw}("89c - Subrutin', 1)[0]
            self.assertIn(f"{global_name}.PemainSiklusGlobal = Null;", cycle)
            self.assertIn(f"{global_name}.WaktuSiklusGlobal = Total Time Elapsed + 0.250;", cycle)

            left = source.split(f'{rule_kw}("04 - Pemain Keluar: Bersihkan hanya saat benar-benar keluar")', 1)[1].split(f'{rule_kw}("04g - Utama global: Penjadwal pusat 20 Hz")', 1)[0]
            self.assertIn("Wait(0.500,", left)
            self.assertIn("Event Player.TimTerakhir != Team Of(Event Player)", left)
            self.assertIn(f"{global_name}.PemainSiklusGlobal == Event Player", left)
'''
t = t[:start] + method + t[end:]
test_path.write_text(t, encoding="utf-8")

# Workflow: only validate pushes to main, cancel superseded runs, more timeout margin.
workflow = ROOT / ".github" / "workflows" / "validate-workshop.yml"
workflow.write_text('''name: Validate Workshop

on:
  push:
    branches:
      - main
  pull_request:
  workflow_dispatch:

concurrency:
  group: validate-workshop-${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  validate:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - name: Check out repository
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false

      - name: Set up Python
        uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0
        with:
          python-version: '3.12'

      - name: Run validator unit tests
        run: python -m unittest discover -s tests -p 'test_*.py'

      - name: Validate Workshop source
        run: python tools/validate_workshop.py

      - name: Preflight Italian clipboard source
        run: python tools/check_clipboard_import.py workshop/ruang_irama.it-IT.workshop --language it-IT
''', encoding="utf-8")

# Documentation version bump + source-of-truth corrections.
for rel in ("README.md", "docs/PROGETTO.md", "docs/VALIDAZIONE.md", "docs/TEST.md"):
    p = ROOT / rel
    s = p.read_text(encoding="utf-8")
    s = s.replace("0.8.0", "0.8.1")
    p.write_text(s, encoding="utf-8")

# README controls/Burning/lifecycle.
p = ROOT / "README.md"
s = p.read_text(encoding="utf-8")
s = s.replace("| Overlay Teleport | Crouch + Secondary / Primary | cambia pagina / teletrasporta |", "| Crouch Travel & Attach | Crouch + Primary / Secondary | pagina successiva / precedente |\n| Crouch Travel & Attach | Crouch + Interact | esegue la pagina attiva (Spawn / Objective / Player-Bot Travel / Player-Bot Attach) |\n| Attaccato, Menu Arcade chiuso | Crouch + Reload | sgancia dal player/bot; Reload senza Crouch resta nativo |")
s = s.replace("5% max HP al secondo per 10 s, con tick da 2,5% ogni 0,5 s; non bypassa Unkillable", "5% max HP ogni 1 s per 10 s; sospende temporaneamente Unkillable e Damage Received per applicare il danno")
s = s.replace("5% max HP al secondo per 10 s, in tick da 2,5% ogni 0,5 s; non bypassa Unkillable", "5% max HP ogni 1 s per 10 s; sospende temporaneamente Unkillable e Damage Received durante ciascun tick")
s = s.replace("nei cinque esiti non-Skull", "negli esiti non letali; Burning invece sospende temporaneamente la protezione per applicare il proprio danno")
s = s.replace("Burning non usa questo bypass: in `FULL HP` il danno viene annullato, mentre in `1 HP` resta soggetto allo status Unkillable.", "Burning usa un bypass temporaneo dedicato: rimuove Unkillable e normalizza Damage Received soltanto per il tick da 5% Max Health, poi il scheduler riapplica la modalità scelta.")
s = s.replace("Le scansioni globali non cedono l'esecuzione mentre usano il player e l'indice correnti.", "Le scansioni globali non cedono l'esecuzione mentre usano il player e l'indice correnti. Il lifecycle join/cambio squadra è inoltre serializzato da un lock globale: un solo player alla volta esegue cleanup/setup, con 0,25 s tra le fasi e sospensione delle cache pesanti durante la transazione.")
p.write_text(s, encoding="utf-8")

# PROGETTO corrections.
p = ROOT / "docs" / "PROGETTO.md"
s = p.read_text(encoding="utf-8")
s = s.replace("| Burning | 10 s | infligge il 5% della salute massima al secondo, come 2,5% ogni 0,5 s, senza bypassare Unkillable |", "| Burning | 10 s | infligge il 5% della salute massima ogni 1 s; sospende temporaneamente Unkillable e Damage Received per ciascun tick |")
s = s.replace("Il tempo massimo di respawn è 30 secondi.", "Il tempo massimo di respawn è 3 secondi.")
s = s.replace("Il cambio Team 1 ↔ Team 2 usa lo stesso cleanup completo del leave seguito da setup fresco. Il reset totale delle preferenze è intenzionale. La sequenza impedisce doppioni anche durante transizioni simultanee o una cascata full-lobby.", "Il cambio Team 1 ↔ Team 2 usa lo stesso cleanup completo del leave seguito da setup fresco. Il reset totale delle preferenze è intenzionale. Un lock globale assegna il lifecycle a un solo player per volta: cleanup e setup sono separati da 0,25 s, il player successivo riceve il lock soltanto dopo la stabilizzazione del precedente e le cache pesanti vengono sospese durante la transazione.")
p.write_text(s, encoding="utf-8")

# VALIDAZIONE corrections.
p = ROOT / "docs" / "VALIDAZIONE.md"
s = p.read_text(encoding="utf-8")
s = s.replace("| Burning | 5% max HP al secondo per 10 s, implementato come 2,5% ogni 0,5 s, senza rimuovere status o modificatori Unkillable |", "| Burning | 5% max HP ogni 1 s per 10 s; rimuove temporaneamente Unkillable e normalizza Damage Received per applicare ciascun tick |")
s = s.replace("Burning non può eseguire `Clear/Set Status(Unkillable)`, cambiare Damage/Knockback Received o collisione: FULL HP annulla i tick di danno e 1 HP conserva lo status.", "Burning è l'eccezione non-Skull esplicitamente autorizzata a eseguire `Clear Status(Unkillable)` e `Damage Received = 100` per il solo tick da 5% Max Health; modalità/cursore restano invariati e il tick globale riapplica subito la protezione selezionata.")
s = s.replace("ordine atomico delle operazioni sensibili e rilascio dei latch;", "ordine atomico delle operazioni sensibili, lock lifecycle globale esclusivo e rilascio dei latch;")
s = s.replace("uscita dummy stabilizzata da un timestamp di 1 secondo, riarmato alla morte/respawn", "uscita dummy stabilizzata da un timestamp di 1 secondo, respawn massimo 3 secondi e riarmo alla morte/respawn")
p.write_text(s, encoding="utf-8")

# TEST corrections + attach/team-switch regression plan.
p = ROOT / "docs" / "TEST.md"
s = p.read_text(encoding="utf-8")
s = s.replace("| Burning | 5% max HP al secondo per 10 s, con tick da 2,5% ogni 0,5 s; non bypassa Unkillable; stop alla scadenza/morte |", "| Burning | 5% max HP ogni 1 s per 10 s; bypass temporaneo di Unkillable/Damage Received durante il tick; stop alla scadenza/morte |")
s = s.replace("con 1 HP e FULL HP, Vision, Acceleration, Team Heal, Burning e Hacked non devono mai rimuovere status", "con 1 HP e FULL HP, Vision, Acceleration, Team Heal e Hacked non devono mai rimuovere status")
s = s.replace("con FULL HP, Burning deve produrre zero perdita di salute; con 1 HP deve restare soggetto allo status Unkillable e non può completare la morte;", "con Burning, verificare che ogni secondo venga applicato il 5% della Max Health anche partendo da 1 HP/FULL HP, senza modificare Mode/Kursor e con ripristino della protezione fra i tick;")
insert_anchor = "### Camera\n"
attach_tests = '''### Crouch Travel & Attach\n\n- Tenere Crouch e verificare le quattro pagine: Spawn Travel, Objective Travel, Player/Bot Travel, Player/Bot Attach.\n- Primary avanza, Secondary torna indietro e Interact esegue sempre la pagina attiva.\n- Agganciarsi a un umano e a un dummy: i piedi devono restare separati dalla testa del target tramite l'offset previsto.\n- Da attaccati, Reload senza Crouch deve restare l'azione nativa dell'eroe.\n- Con Menu Arcade Melee chiuso, Crouch + Reload deve sganciare; con Menu Arcade Melee aperto non deve sganciare.\n- Morte, leave/despawn, cambio eroe proprio o del target e Privacy ON del target umano devono sganciare automaticamente.\n\n### Cambio squadra / lifecycle 0.8.1\n\n- Ripetere Team 1 → Team 2 → Team 1 almeno 20 volte con un solo umano, controllando che non compaia `excessive Workshop script load`.\n- Ripetere con 2, 6 e 12 umani cambiando squadra quasi simultaneamente: il lifecycle deve processare un solo player per volta.\n- Durante la transazione verificare che HUD/roster del player corrente vengano ricreati una volta sola e che gli altri player restino stabili.\n- Verificare che il lock globale venga rilasciato anche se il player esce durante cleanup/setup.\n- Con diagnostica host attiva, confermare che le cache 1 Hz e il lavoro periodico non essenziale restino sospesi mentre il lock lifecycle è occupato.\n\n'''
if insert_anchor not in s:
    raise SystemExit("TEST camera anchor missing")
s = s.replace(insert_anchor, attach_tests + insert_anchor, 1)
p.write_text(s, encoding="utf-8")

# Dummy documentation.
p = ROOT / "docs" / "DUMMY_BOTS.md"
s = p.read_text(encoding="utf-8").replace("30 secondi", "3 secondi").replace("30 s", "3 s")
p.write_text(s, encoding="utf-8")

# Changelog 0.8.1 entry.
p = ROOT / "CHANGELOG.md"
s = p.read_text(encoding="utf-8")
entry = '''## 0.8.1 — 2026-08-24\n\nStato: **live-pending**.\n\n- Cambio squadra reso global-first seriale: un lock globale assegna cleanup/setup a un solo player per volta, con 0,25 s fra le fasi e cooldown prima del player successivo.\n- Durante una transazione lifecycle il scheduler sospende il lavoro periodico non essenziale per gli altri player e le cache 1 Hz, riducendo il picco di carico che poteva mandare offline il server durante il cambio team.\n- La discriminazione `Player Left Match` attende 0,5 s prima del cleanup, così una transizione di squadra ha più tempo per riapparire come entità valida e non percorre accidentalmente anche il cleanup di leave.\n- Documentazione riallineata al runtime reale: dummy respawn 3 s, Burning 5% Max Health ogni secondo con bypass temporaneo di Unkillable/Damage Received, e controlli completi Crouch Travel & Attach.\n- GitHub Actions limitato ai push su `main` e alle PR, con concurrency/cancel-in-progress e timeout 15 minuti per evitare run duplicati e X rossi obsoleti.\n\n'''
anchor = "## 0.8.0 — 2026-08-24\n"
if anchor not in s:
    raise SystemExit("CHANGELOG 0.8.0 anchor missing")
s = s.replace(anchor, entry + anchor, 1)
p.write_text(s, encoding="utf-8")

print("Applied 0.8.1 serial lifecycle, docs and GitHub workflow maintenance")
