from pathlib import Path

path = Path(__file__).resolve().parents[1] / "tools" / "validate_workshop.py"
text = path.read_text(encoding="utf-8")
old = '''            (
                "Or(Global.PemainAktif.EfekNasib!=2,"
                "Global.PemainAktif.EfekNasibBerakhir<=TotalTimeElapsed)",
                "eccezione per l'esito Acceleration ancora attivo",
            ),
            ("MagnitudeOf(ThrottleOf(Global.PemainAktif))<=0.050", "soglia input fermo"),
            ("MagnitudeOf(VelocityOf(Global.PemainAktif))>0.010", "soglia deriva"),'''
new = '''            (
                "If(And(Global.PemainAktif.ModeTerbangAktif==True,"
                "And(Or(Global.PemainAktif.EfekNasib!=2,"
                "Global.PemainAktif.EfekNasibBerakhir<=TotalTimeElapsed),"
                "And(MagnitudeOf(ThrottleOf(Global.PemainAktif))<=0.050,"
                "MagnitudeOf(VelocityOf(Global.PemainAktif))>0.010))));",
                "eccezione per l'esito Acceleration ancora attivo nel freno idle Fly",
            ),'''
if text.count(old) != 1:
    raise SystemExit(f"expected one generic idle guard block, found {text.count(old)}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
