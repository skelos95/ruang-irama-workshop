from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_exact(text: str, old: str, new: str, label: str, count: int = 1) -> str:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"{label}: expected {count} occurrence(s), found {actual}")
    return text.replace(old, new, count)


for rel in ("workshop/ruang_irama.it-IT.workshop", "tests/fixtures/semantic_reference.txt"):
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    old = '''\t\tElse;
\t\t\tStop Transforming Throttle(Event Player);
\t\t\tSet Gravity(Event Player, 100);'''
    new = '''\t\tElse;
\t\t\tIf(Or(Event Player.EfekNasib != 2, Event Player.EfekNasibBerakhir <= Total Time Elapsed));
\t\t\t\tStop Accelerating(Event Player);
\t\t\tEnd;
\t\t\tStop Transforming Throttle(Event Player);
\t\t\tSet Gravity(Event Player, 100);'''
    text = replace_exact(text, old, new, f"{rel}: Fly off acceleration guard")
    path.write_text(text, encoding="utf-8")

# Keep the focused Ghost/Fly test aligned with the guarded Fly-off cleanup.
p = ROOT / "tests/test_ghost_fly.py"
text = p.read_text(encoding="utf-8")
old = '''            self.assertRegex(
                packed,
                r"Else;StopTransformingThrottle\\(EventPlayer\\);SetGravity\\(EventPlayer,100\\);",
            )'''
new = '''            self.assertRegex(
                packed,
                r"Else;If\\(Or\\(EventPlayer\\.EfekNasib!=2,EventPlayer\\.EfekNasibBerakhir<=TotalTimeElapsed\\)\\);"
                r"StopAccelerating\\(EventPlayer\\);End;StopTransformingThrottle\\(EventPlayer\\);SetGravity\\(EventPlayer,100\\);",
            )'''
text = replace_exact(text, old, new, "ghost fly off test")
p.write_text(text, encoding="utf-8")

# Require the same guard semantically so future changes cannot leave Fly acceleration running.
p = ROOT / "tools/validate_workshop.py"
text = p.read_text(encoding="utf-8")
old = '''            (
                "Else;StopTransformingThrottle(EventPlayer);SetGravity(EventPlayer,100);",
                "ripristino motore Fly",
            ),'''
new = '''            (
                "Else;If(Or(EventPlayer.EfekNasib!=2,EventPlayer.EfekNasibBerakhir<=TotalTimeElapsed));"
                "StopAccelerating(EventPlayer);End;StopTransformingThrottle(EventPlayer);SetGravity(EventPlayer,100);",
                "ripristino motore Fly con arresto rampa senza interrompere Acceleration",
            ),'''
text = replace_exact(text, old, new, "validator Fly off guard")
p.write_text(text, encoding="utf-8")
