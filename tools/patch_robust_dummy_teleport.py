#!/usr/bin/env python3
from pathlib import Path


def replace_between(text: str, start_marker: str, end_marker: str, replacement: str, label: str) -> str:
    start = text.find(start_marker)
    if start < 0:
        raise SystemExit(f"missing start marker: {label}")
    end = text.find(end_marker, start)
    if end < 0:
        raise SystemExit(f"missing end marker: {label}")
    return text[:start] + replacement + text[end:]


it_path = Path("workshop/ruang_irama.it-IT.workshop")
en_path = Path("tests/fixtures/semantic_reference.txt")
test_path = Path("tests/test_dummy_bots.py")

it = it_path.read_text(encoding="utf-8")
en = en_path.read_text(encoding="utf-8")

it_rule = '''regola("03f - Bot/Dummy: Teleport dari ruang spawn ke objektif")
{
\tevento
\t{
\t\tOngoing - Each Player;
\t\tTutti;
\t\tTutti;
\t}

\tcondizioni
\t{
\t\tGlobale.Siap == True;
\t\tIs Dummy Bot(Event Player) == True;
\t\tHas Spawned(Event Player) == True;
\t\tIs Alive(Event Player) == True;
\t\tIs In Spawn Room(Event Player) == True;
\t}

\tazioni
\t{
\t\tEvent Player.PosisiBangkitAman = Vector(0, 0, 0);
\t\tIf(Or(Current Game Mode == Game Mode(Trasporto), Current Game Mode == Game Mode(Ibrida)));
\t\t\tIf(Distance Between(Payload Position, Vector(0, 0, 0)) > 0.100);
\t\t\t\tEvent Player.PosisiBangkitAman = Nearest Walkable Position(Payload Position + Vector(2, 0, 0));
\t\t\t\tIf(Distance Between(Event Player.PosisiBangkitAman, Payload Position + Vector(2, 0, 0)) <= 12);
\t\t\t\t\tIf(Distance Between(Ray Cast Hit Position(Event Player.PosisiBangkitAman + Vector(0, 5, 0), Event Player.PosisiBangkitAman - Vector(0, 20, 0), Empty Array, Empty Array, False), Event Player.PosisiBangkitAman) <= 6);
\t\t\t\t\t\tIf(Distance Between(Event Player.PosisiBangkitAman, Vector(0, 0, 0)) > 0.100);
\t\t\t\t\t\t\tTeleport(Event Player, Event Player.PosisiBangkitAman);
\t\t\t\t\t\tEnd;
\t\t\t\t\tEnd;
\t\t\t\tEnd;
\t\t\tEnd;
\t\tElse If(Current Game Mode == Game Mode(Cattura la Bandiera));
\t\t\tIf(Distance Between(Flag Position(Opposite Team Of(Team Of(Event Player))), Vector(0, 0, 0)) > 0.100);
\t\t\t\tEvent Player.PosisiBangkitAman = Nearest Walkable Position(Flag Position(Opposite Team Of(Team Of(Event Player))) + Vector(2, 0, 0));
\t\t\t\tIf(Distance Between(Event Player.PosisiBangkitAman, Flag Position(Opposite Team Of(Team Of(Event Player))) + Vector(2, 0, 0)) <= 12);
\t\t\t\t\tIf(Distance Between(Ray Cast Hit Position(Event Player.PosisiBangkitAman + Vector(0, 5, 0), Event Player.PosisiBangkitAman - Vector(0, 20, 0), Empty Array, Empty Array, False), Event Player.PosisiBangkitAman) <= 6);
\t\t\t\t\t\tIf(Distance Between(Event Player.PosisiBangkitAman, Vector(0, 0, 0)) > 0.100);
\t\t\t\t\t\t\tTeleport(Event Player, Event Player.PosisiBangkitAman);
\t\t\t\t\t\tEnd;
\t\t\t\t\tEnd;
\t\t\t\tEnd;
\t\t\tEnd;
\t\tElse If(Current Game Mode == Game Mode(Scorta));
\t\t\tIf(Count Of(Filtered Array(All Players(All Teams), And(Has Spawned(Current Array Element) == True, And(Is Alive(Current Array Element) == True, Is On Objective(Current Array Element) == True)))) > 0);
\t\t\t\tEvent Player.PosisiBangkitAman = Nearest Walkable Position(Position Of(First Of(Filtered Array(All Players(All Teams), And(Has Spawned(Current Array Element) == True, And(Is Alive(Current Array Element) == True, Is On Objective(Current Array Element) == True))))) + Vector(2, 0, 0));
\t\t\t\tIf(Distance Between(Event Player.PosisiBangkitAman, Position Of(First Of(Filtered Array(All Players(All Teams), And(Has Spawned(Current Array Element) == True, And(Is Alive(Current Array Element) == True, Is On Objective(Current Array Element) == True))))) + Vector(2, 0, 0)) <= 12);
\t\t\t\t\tIf(Distance Between(Ray Cast Hit Position(Event Player.PosisiBangkitAman + Vector(0, 5, 0), Event Player.PosisiBangkitAman - Vector(0, 20, 0), Empty Array, Empty Array, False), Event Player.PosisiBangkitAman) <= 6);
\t\t\t\t\t\tIf(Distance Between(Event Player.PosisiBangkitAman, Vector(0, 0, 0)) > 0.100);
\t\t\t\t\t\t\tTeleport(Event Player, Event Player.PosisiBangkitAman);
\t\t\t\t\t\tEnd;
\t\t\t\t\tEnd;
\t\t\t\tEnd;
\t\t\tElse If(Distance Between(Objective Position(Objective Index), Vector(0, 0, 0)) > 0.100);
\t\t\t\tEvent Player.PosisiBangkitAman = Nearest Walkable Position(Objective Position(Objective Index));
\t\t\t\tIf(Distance Between(Event Player.PosisiBangkitAman, Objective Position(Objective Index)) <= 12);
\t\t\t\t\tIf(Distance Between(Ray Cast Hit Position(Event Player.PosisiBangkitAman + Vector(0, 5, 0), Event Player.PosisiBangkitAman - Vector(0, 20, 0), Empty Array, Empty Array, False), Event Player.PosisiBangkitAman) <= 6);
\t\t\t\t\t\tIf(Distance Between(Event Player.PosisiBangkitAman, Vector(0, 0, 0)) > 0.100);
\t\t\t\t\t\t\tTeleport(Event Player, Event Player.PosisiBangkitAman);
\t\t\t\t\t\tEnd;
\t\t\t\t\tEnd;
\t\t\t\tEnd;
\t\t\tEnd;
\t\tElse If(Distance Between(Objective Position(Objective Index), Vector(0, 0, 0)) > 0.100);
\t\t\tEvent Player.PosisiBangkitAman = Nearest Walkable Position(Objective Position(Objective Index));
\t\t\tIf(Distance Between(Event Player.PosisiBangkitAman, Objective Position(Objective Index)) <= 12);
\t\t\t\tIf(Distance Between(Ray Cast Hit Position(Event Player.PosisiBangkitAman + Vector(0, 5, 0), Event Player.PosisiBangkitAman - Vector(0, 20, 0), Empty Array, Empty Array, False), Event Player.PosisiBangkitAman) <= 6);
\t\t\t\t\tIf(Distance Between(Event Player.PosisiBangkitAman, Vector(0, 0, 0)) > 0.100);
\t\t\t\t\t\tTeleport(Event Player, Event Player.PosisiBangkitAman);
\t\t\t\t\tEnd;
\t\t\t\tEnd;
\t\t\tEnd;
\t\tEnd;
\t}
}

'''

en_rule = (it_rule.replace("regola(", "rule(")
    .replace("\n\tevento\n", "\n\tevent\n")
    .replace("\n\tcondizioni\n", "\n\tconditions\n")
    .replace("\n\tazioni\n", "\n\tactions\n")
    .replace("\t\tTutti;", "\t\tAll;")
    .replace("Globale.", "Global.")
    .replace("Game Mode(Trasporto)", "Game Mode(Escort)")
    .replace("Game Mode(Ibrida)", "Game Mode(Hybrid)")
    .replace("Game Mode(Cattura la Bandiera)", "Game Mode(Capture The Flag)")
    .replace("Game Mode(Scorta)", "Game Mode(Push)"))

it = replace_between(it, 'regola("03f - Bot/Dummy: Teleport dari ruang spawn ke objektif")', 'regola("03g - Bot/Dummy: Selalu hadap pemain hidup terdekat")', it_rule, "Italian 03f")
en = replace_between(en, 'rule("03f - Bot/Dummy: Teleport dari ruang spawn ke objektif")', 'rule("03g - Bot/Dummy: Selalu hadap pemain hidup terdekat")', en_rule, "English 03f")
it_path.write_text(it, encoding="utf-8")
en_path.write_text(en, encoding="utf-8")

tests = test_path.read_text(encoding="utf-8")
anchor = '        self.assertNotIn("Teleport(Event Player, Objective Position(Objective Index));", self.it)\n'
extra = (
    '        self.assertIn("Event Player.PosisiBangkitAman = Vector(0, 0, 0);", self.it)\n'
    '        self.assertIn("Ray Cast Hit Position(Event Player.PosisiBangkitAman + Vector(0, 5, 0)", self.it)\n'
    '        self.assertIn("Distance Between(Event Player.PosisiBangkitAman, Vector(0, 0, 0)) > 0.100", self.it)\n'
    '        self.assertIn("Teleport(Event Player, Event Player.PosisiBangkitAman);", self.it)\n'
)
if extra.strip() not in tests:
    if anchor not in tests:
        raise SystemExit("missing dummy test anchor")
    tests = tests.replace(anchor, anchor + extra, 1)
test_path.write_text(tests, encoding="utf-8")

Path(__file__).unlink()
