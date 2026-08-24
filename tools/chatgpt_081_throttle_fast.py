from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

for rel, g in (("workshop/ruang_irama.it-IT.workshop", "Globale"), ("tests/fixtures/semantic_reference.txt", "Global")):
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    old = (
        "\t\t\tCall Subroutine(ProsesCepatPemain);\n"
        f"\t\t\tIf(Or({g}.PemainSiklusGlobal == Null, {g}.PemainAktif == {g}.PemainSiklusGlobal));\n"
        "\t\t\t\tCall Subroutine(ProsesNasibPemain);\n"
        "\t\t\tEnd;\n"
    )
    new = (
        f"\t\t\tIf(Or({g}.PemainSiklusGlobal == Null, {g}.PemainAktif == {g}.PemainSiklusGlobal));\n"
        "\t\t\t\tCall Subroutine(ProsesCepatPemain);\n"
        "\t\t\t\tCall Subroutine(ProsesNasibPemain);\n"
        "\t\t\tEnd;\n"
    )
    if text.count(old) != 1:
        raise SystemExit(f"{rel}: fast throttle anchor count {text.count(old)}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")

validator = ROOT / "tools" / "validate_workshop.py"
v = validator.read_text(encoding="utf-8")
anchor = '''            "Or(Global.PemainSiklusGlobal == Null, Global.PemainAktif == Global.PemainSiklusGlobal)",
            "And(Global.LangkahPenjadwal % 20 == 0, Global.PemainSiklusGlobal == Null)",'''
repl = '''            "Or(Global.PemainSiklusGlobal == Null, Global.PemainAktif == Global.PemainSiklusGlobal)",
            "Call Subroutine(ProsesCepatPemain);",
            "Call Subroutine(ProsesNasibPemain);",
            "And(Global.LangkahPenjadwal % 20 == 0, Global.PemainSiklusGlobal == Null)",'''
if v.count(anchor) != 1:
    raise SystemExit(f"validator scheduler token anchor count {v.count(anchor)}")
v = v.replace(anchor, repl, 1)
# Require both fast and luck to be inside the same owner gate.
needle = '''        for token in (
            "Global.PemainSiklusGlobal != Null",'''
if v.count(needle) != 1:
    raise SystemExit(f"validator scheduler owner block count {v.count(needle)}")
extra_check = '''        checks.require(
            scheduler.body.count("Or(Global.PemainSiklusGlobal == Null, Global.PemainAktif == Global.PemainSiklusGlobal)") >= 2,
            "scheduler non limita fast-path e ciclo al proprietario lifecycle",
        )
'''
# Insert immediately before the next lifecycle check section by finding end of token loop.
end_anchor = '''            checks.require(token in scheduler.body, f"scheduler non serializza/throttla il lifecycle: {token}")
'''
if v.count(end_anchor) != 1:
    raise SystemExit(f"validator scheduler end anchor count {v.count(end_anchor)}")
v = v.replace(end_anchor, end_anchor + extra_check, 1)
validator.write_text(v, encoding="utf-8")

runtime = ROOT / "tests" / "test_runtime_maintenance.py"
t = runtime.read_text(encoding="utf-8")
anchor = '''            self.assertIn(f"Or({global_name}.PemainSiklusGlobal == Null, {global_name}.PemainAktif == {global_name}.PemainSiklusGlobal)", scheduler)
            self.assertIn(f"And({global_name}.LangkahPenjadwal % 20 == 0, {global_name}.PemainSiklusGlobal == Null)", scheduler)'''
repl = '''            owner_gate = f"Or({global_name}.PemainSiklusGlobal == Null, {global_name}.PemainAktif == {global_name}.PemainSiklusGlobal)"
            self.assertGreaterEqual(scheduler.count(owner_gate), 2)
            self.assertIn("Call Subroutine(ProsesCepatPemain);", scheduler)
            self.assertIn("Call Subroutine(ProsesNasibPemain);", scheduler)
            self.assertIn(f"And({global_name}.LangkahPenjadwal % 20 == 0, {global_name}.PemainSiklusGlobal == Null)", scheduler)'''
if t.count(anchor) != 1:
    raise SystemExit(f"runtime scheduler throttle anchor count {t.count(anchor)}")
runtime.write_text(t.replace(anchor, repl, 1), encoding="utf-8")

changelog = ROOT / "CHANGELOG.md"
s = changelog.read_text(encoding="utf-8")
old = "- Durante una transazione lifecycle il scheduler sospende il lavoro periodico non essenziale per gli altri player e le cache 1 Hz, riducendo il picco di carico che poteva mandare offline il server durante il cambio team.\n"
new = "- Durante una transazione lifecycle il scheduler sospende per gli altri player anche il fast-path 20 Hz, oltre al ciclo 10 Hz e alle cache 1 Hz; resta attivo quasi soltanto il proprietario del cambio squadra, riducendo il picco di carico critico.\n"
if s.count(old) != 1:
    raise SystemExit(f"changelog fast throttle anchor count {s.count(old)}")
changelog.write_text(s.replace(old, new, 1), encoding="utf-8")

print("Throttled non-owner 20 Hz work during serialized lifecycle")
