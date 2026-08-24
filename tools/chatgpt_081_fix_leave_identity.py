from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

for rel in ("workshop/ruang_irama.it-IT.workshop", "tests/fixtures/semantic_reference.txt"):
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    old = (
        "\t\tAbort If(And(Entity Exists(Event Player) == True, Event Player.TimTerakhir != Team Of(Event Player)));\n"
        "\t\tCall Subroutine(TenangkanPemain);\n"
    )
    new = (
        "\t\tAbort If(And(Entity Exists(Event Player) == True, Event Player.TimTerakhir != Team Of(Event Player)));\n"
        "\t\tEvent Player.UrutanHUD = -1;\n"
        "\t\tCall Subroutine(TenangkanPemain);\n"
    )
    if text.count(old) != 1:
        raise SystemExit(f"{rel}: leave identity anchor count {text.count(old)}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")

validator = ROOT / "tools" / "validate_workshop.py"
v = validator.read_text(encoding="utf-8")
anchor = '''        checks.require("Abort If(And(Entity Exists(Event Player) == True, Event Player.TimTerakhir != Team Of(Event Player)));" in body,
                       "leave non delega il cambio squadra al lifecycle globale")'''
extra = anchor + '''
        checks.require("Event Player.UrutanHUD = -1;" in body,
                       "leave stale può ancora usare il fallback slot HUD e colpire la nuova entità")
        checks.require(body.find("Event Player.UrutanHUD = -1;") < body.find("Call Subroutine(BersihkanPemain);"),
                       "leave deve disabilitare il fallback slot prima del cleanup")'''
if v.count(anchor) != 1:
    raise SystemExit(f"validator leave identity anchor count {v.count(anchor)}")
validator.write_text(v.replace(anchor, extra, 1), encoding="utf-8")

runtime = ROOT / "tests" / "test_runtime_maintenance.py"
t = runtime.read_text(encoding="utf-8")
anchor = '''            self.assertIn("Event Player.TimTerakhir != Team Of(Event Player)", left)
            self.assertIn(f"{global_name}.PemainSiklusGlobal == Event Player", left)'''
extra = '''            self.assertIn("Event Player.TimTerakhir != Team Of(Event Player)", left)
            self.assertIn("Event Player.UrutanHUD = -1;", left)
            self.assertLess(left.index("Event Player.UrutanHUD = -1;"), left.index("Call Subroutine(BersihkanPemain);"))
            self.assertIn(f"{global_name}.PemainSiklusGlobal == Event Player", left)'''
if t.count(anchor) != 1:
    raise SystemExit(f"runtime leave identity anchor count {t.count(anchor)}")
runtime.write_text(t.replace(anchor, extra, 1), encoding="utf-8")

changelog = ROOT / "CHANGELOG.md"
s = changelog.read_text(encoding="utf-8")
anchor = "- La discriminazione `Player Left Match` attende 0,5 s prima del cleanup, così una transizione di squadra ha più tempo per riapparire come entità valida e non percorre accidentalmente anche il cleanup di leave.\n"
extra = anchor + "- Il cleanup `Player Left Match` disabilita il fallback per slot HUD prima di rimuovere il roster: una vecchia entità distrutta dal cambio team non può più eliminare la nuova entità che eredita lo stesso slot.\n"
if s.count(anchor) != 1:
    raise SystemExit(f"changelog leave identity anchor count {s.count(anchor)}")
changelog.write_text(s.replace(anchor, extra, 1), encoding="utf-8")

print("Hardened Player Left identity against team-switch slot reuse")
