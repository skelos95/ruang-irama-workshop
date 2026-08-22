#!/usr/bin/env python3
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


def replace_between(text: str, start: str, end: str, replacement: str, label: str) -> str:
    a = text.find(start)
    b = text.find(end, a + 1)
    if a < 0 or b < 0:
        raise SystemExit(f"{label}: markers not found")
    return text[:a] + replacement + text[b:]


root = Path.cwd()
it_path = root / "workshop/ruang_irama.it-IT.workshop"
en_path = root / "tests/fixtures/semantic_reference.txt"
tests_path = root / "tests/test_dummy_bots.py"
readme_path = root / "README.md"
project_path = root / "docs/PROGETTO.md"
testdoc_path = root / "docs/TEST.md"
changelog_path = root / "CHANGELOG.md"

it = it_path.read_text(encoding="utf-8")
en = en_path.read_text(encoding="utf-8")

for old, new in (
    ("\\n     PLAYER VIBES", "\\nPLAYER VIBES"),
    ("\\n     MUSIK PEMAIN", "\\nMUSIK PEMAIN"),
    ("\\n     เพลงของผู้เล่น", "\\nเพลงของผู้เล่น"),
):
    it = replace_once(it, old, new, f"it HUD {old}")
    en = replace_once(en, old, new, f"en HUD {old}")

for team in (1, 2):
    old_cond = (
        f"\t\tNumber Of Slots(Team {team}) > 0;\n"
        f"\t\tCount Of(Filtered Array(All Players(Team {team}), Is Dummy Bot(Current Array Element) == True)) == 0;"
    )
    new_cond = (
        f"\t\tNumber Of Slots(Team {team}) > 0;\n"
        f"\t\tCount Of(Spawn Points(Team {team})) > 0;\n"
        f"\t\tCount Of(Filtered Array(All Players(Team {team}), Is Dummy Bot(Current Array Element) == True)) == 0;"
    )
    it = replace_once(it, old_cond, new_cond, f"it team {team} spawn guard")
    en = replace_once(en, old_cond, new_cond, f"en team {team} spawn guard")
    it = replace_once(
        it,
        f"\t\tCreate Dummy Bot(Tutti gli eroi, Team {team}, -1, Null, Null);",
        f"\t\tCreate Dummy Bot(Tutti gli eroi, Team {team}, -1, Position Of(First Of(Spawn Points(Team {team}))), Vector(0, 0, 1));",
        f"it team {team} creation",
    )
    en = replace_once(
        en,
        f"\t\tCreate Dummy Bot(All Heroes, Team {team}, -1, Null, Null);",
        f"\t\tCreate Dummy Bot(All Heroes, Team {team}, -1, Position Of(First Of(Spawn Points(Team {team}))), Vector(0, 0, 1));",
        f"en team {team} creation",
    )

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
\t\tCount Of(Spawn Points(Team Of(Event Player))) > 0;
\t}

\tazioni
\t{
\t\tWait(1.000, Annulla quando è False);
\t\tEvent Player.PosisiMati = Vector(0, 0, 0);
\t\tEvent Player.PosisiBangkitAman = Vector(0, 0, 0);
\t\tIf(Or(Current Game Mode == Game Mode(Trasporto), Current Game Mode == Game Mode(Ibrida)));
\t\t\tIf(Distance Between(Payload Position, Vector(0, 0, 0)) > 0.100);
\t\t\t\tEvent Player.PosisiMati = Payload Position;
\t\t\tEnd;
\t\tElse If(Current Game Mode == Game Mode(Cattura la Bandiera));
\t\t\tIf(Distance Between(Flag Position(Opposite Team Of(Team Of(Event Player))), Vector(0, 0, 0)) > 0.100);
\t\t\t\tEvent Player.PosisiMati = Flag Position(Opposite Team Of(Team Of(Event Player)));
\t\t\tEnd;
\t\tElse If(Current Game Mode == Game Mode(Scorta));
\t\t\tIf(Count Of(Filtered Array(All Players(All Teams), And(Has Spawned(Current Array Element) == True, And(Is Alive(Current Array Element) == True, Is On Objective(Current Array Element) == True)))) > 0);
\t\t\t\tEvent Player.PosisiMati = Position Of(First Of(Filtered Array(All Players(All Teams), And(Has Spawned(Current Array Element) == True, And(Is Alive(Current Array Element) == True, Is On Objective(Current Array Element) == True)))));
\t\t\tElse If(Distance Between(Objective Position(Objective Index), Vector(0, 0, 0)) > 0.100);
\t\t\t\tEvent Player.PosisiMati = Objective Position(Objective Index);
\t\t\tEnd;
\t\tElse If(Distance Between(Objective Position(Objective Index), Vector(0, 0, 0)) > 0.100);
\t\t\tEvent Player.PosisiMati = Objective Position(Objective Index);
\t\tEnd;
\t\tIf(Distance Between(Event Player.PosisiMati, Vector(0, 0, 0)) > 0.100);
\t\t\tEvent Player.PosisiBangkitAman = Nearest Walkable Position(Event Player.PosisiMati + Direction Towards(Event Player.PosisiMati, Position Of(First Of(Spawn Points(Team Of(Event Player))))) * 10);
\t\t\tIf(Distance Between(Event Player.PosisiBangkitAman, Event Player.PosisiMati) >= 6);
\t\t\t\tIf(Distance Between(Event Player.PosisiBangkitAman, Event Player.PosisiMati) <= 16);
\t\t\t\t\tIf(Distance Between(Ray Cast Hit Position(Event Player.PosisiBangkitAman + Vector(0, 5, 0), Event Player.PosisiBangkitAman - Vector(0, 20, 0), Empty Array, Empty Array, False), Event Player.PosisiBangkitAman) <= 6);
\t\t\t\t\t\tIf(Distance Between(Event Player.PosisiBangkitAman, Vector(0, 0, 0)) > 0.100);
\t\t\t\t\t\t\tTeleport(Event Player, Event Player.PosisiBangkitAman);
\t\t\t\t\t\tEnd;
\t\t\t\t\tEnd;
\t\t\t\tEnd;
\t\t\tEnd;
\t\tEnd;
\t}
}

'''
en_rule = (
    it_rule.replace("regola(", "rule(")
    .replace("\n\tevento\n", "\n\tevent\n")
    .replace("\n\tcondizioni\n", "\n\tconditions\n")
    .replace("\n\tazioni\n", "\n\tactions\n")
    .replace("\t\tTutti;", "\t\tAll;")
    .replace("Globale.", "Global.")
    .replace("Game Mode(Trasporto)", "Game Mode(Escort)")
    .replace("Game Mode(Ibrida)", "Game Mode(Hybrid)")
    .replace("Game Mode(Cattura la Bandiera)", "Game Mode(Capture The Flag)")
    .replace("Game Mode(Scorta)", "Game Mode(Push)")
    .replace("Annulla quando è False", "Abort When False")
)
it = replace_between(it, 'regola("03f - Bot/Dummy: Teleport dari ruang spawn ke objektif")', 'regola("03g - Bot/Dummy: Selalu hadap pemain hidup terdekat")', it_rule, "it 03f")
en = replace_between(en, 'rule("03f - Bot/Dummy: Teleport dari ruang spawn ke objektif")', 'rule("03g - Bot/Dummy: Selalu hadap pemain hidup terdekat")', en_rule, "en 03f")

old_lock = "\t\tSet Knockback Dealt(Event Player, 0);\n\t\tSet Damage Received(Event Player, 100);\n\t\tSet Move Speed(Event Player, 10);\n"
new_lock = "\t\tSet Knockback Dealt(Event Player, 0);\n\t\tSet Damage Received(Event Player, 100);\n\t\tSet Knockback Received(Event Player, 0);\n\t\tSet Move Speed(Event Player, 0);\n"
it = replace_once(it, old_lock, new_lock, "it stationary lock")
en = replace_once(en, old_lock, new_lock, "en stationary lock")
jump_anchor = "\t\tDisallow Button(Event Player, Button(Melee));\n"
it = replace_once(it, jump_anchor, jump_anchor + "\t\tDisallow Button(Event Player, Button(Jump));\n", "it jump lock")
en = replace_once(en, jump_anchor, jump_anchor + "\t\tDisallow Button(Event Player, Button(Jump));\n", "en jump lock")

it_path.write_text(it, encoding="utf-8")
en_path.write_text(en, encoding="utf-8")

tests = tests_path.read_text(encoding="utf-8")
tests = tests.replace('self.assertIn("\\\\n     PLAYER VIBES", self.it)', 'self.assertIn("\\\\nPLAYER VIBES", self.it)')
tests = tests.replace('self.assertIn("\\\\n     MUSIK PEMAIN", self.it)', 'self.assertIn("\\\\nMUSIK PEMAIN", self.it)')
tests = tests.replace('self.assertNotIn("\\\\n \\\\n     PLAYER VIBES", self.it)', 'self.assertNotIn("\\\\n     PLAYER VIBES", self.it)')
old_creation = '''        self.assertEqual(self.it.count("Create Dummy Bot(Tutti gli eroi, Team 1, -1, Null, Null);"), 1)\n        self.assertEqual(self.it.count("Create Dummy Bot(Tutti gli eroi, Team 2, -1, Null, Null);"), 1)\n        self.assertEqual(self.en.count("Create Dummy Bot(All Heroes, Team 1, -1, Null, Null);"), 1)\n        self.assertEqual(self.en.count("Create Dummy Bot(All Heroes, Team 2, -1, Null, Null);"), 1)\n'''
new_creation = '''        self.assertEqual(self.it.count("Create Dummy Bot(Tutti gli eroi, Team 1, -1, Position Of(First Of(Spawn Points(Team 1))), Vector(0, 0, 1));"), 1)\n        self.assertEqual(self.it.count("Create Dummy Bot(Tutti gli eroi, Team 2, -1, Position Of(First Of(Spawn Points(Team 2))), Vector(0, 0, 1));"), 1)\n        self.assertEqual(self.en.count("Create Dummy Bot(All Heroes, Team 1, -1, Position Of(First Of(Spawn Points(Team 1))), Vector(0, 0, 1));"), 1)\n        self.assertEqual(self.en.count("Create Dummy Bot(All Heroes, Team 2, -1, Position Of(First Of(Spawn Points(Team 2))), Vector(0, 0, 1));"), 1)\n        self.assertNotIn("Create Dummy Bot(Tutti gli eroi, Team 1, -1, Null, Null);", self.it)\n        self.assertNotIn("Create Dummy Bot(Tutti gli eroi, Team 2, -1, Null, Null);", self.it)\n'''
tests = replace_once(tests, old_creation, new_creation, "creation tests")
tests = replace_once(tests, '        self.assertIn("Is In Spawn Room(Event Player) == True;", self.it)\n', '        self.assertIn("Is In Spawn Room(Event Player) == True;", self.it)\n        self.assertIn("Wait(1.000, Annulla quando è False);", self.it)\n        self.assertIn("Direction Towards(Event Player.PosisiMati, Position Of(First Of(Spawn Points(Team Of(Event Player))))) * 10", self.it)\n        self.assertIn("Distance Between(Event Player.PosisiBangkitAman, Event Player.PosisiMati) >= 6", self.it)\n', "distance tests")
tests = replace_once(tests, '        self.assertNotIn("Set Damage Received(Event Player, 0);", en_lock)\n', '        self.assertNotIn("Set Damage Received(Event Player, 0);", en_lock)\n        self.assertIn("Set Knockback Received(Event Player, 0);", it_lock)\n        self.assertIn("Set Move Speed(Event Player, 0);", it_lock)\n', "stationary tests")
tests_path.write_text(tests, encoding="utf-8")

readme = readme_path.read_text(encoding="utf-8")
readme = replace_once(readme, "- Un dummy nativo per squadra quando esiste uno slot libero, respawn massimo 30 s e uscita dalla Spawn Room verso una destinazione mode-specific percorribile.", "- Un dummy nativo per squadra quando esiste uno slot e uno Spawn Point valido: nasce direttamente nella propria spawn, respawn massimo 30 s e uscita dalla Spawn Room verso una destinazione mode-specific percorribile.", "README summary")
readme = replace_once(readme, "I dummy nativi usano lo stesso principio per uscire dalla Spawn Room: payload per Escort/Hybrid, bandiera nemica per CTF, proxy dell'obiettivo con fallback per Push e obiettivo corrente negli altri casi. Ogni destinazione passa da `Nearest Walkable Position`; se il punto richiesto non è disponibile, il dummy resta in spawn e la regola riprova senza teletrasportarlo a coordinate nulle.", "I dummy nativi nascono su uno Spawn Point reale della propria squadra, evitando l'origine della mappa. Per uscire dalla Spawn Room usano payload per Escort/Hybrid, bandiera nemica per CTF, proxy dell'obiettivo con fallback per Push e obiettivo corrente negli altri casi. Il punto di arrivo viene cercato circa 10 m verso la propria spawn e deve restare almeno 6 m dal target, oltre a passare `Nearest Walkable Position` e il controllo del pavimento; se non esiste un punto valido, il dummy resta in spawn e riprova.", "README routing")
readme_path.write_text(readme, encoding="utf-8")

project = project_path.read_text(encoding="utf-8")
if "### Dummy bot: spawn e distanza sicura" not in project:
    project += "\n\n### Dummy bot: spawn e distanza sicura\n\nI dummy vengono creati soltanto quando esiste uno Spawn Point della squadra e la posizione iniziale è quello Spawn Point, non `Null`. L'uscita automatica dalla spawn attende 1 secondo, cerca una posizione camminabile circa 10 m verso la propria metà mappa e rifiuta destinazioni a meno di 6 m dall'obiettivo/bandiera. I bot restano passivi e fermi, ricevono danno normale e guardano continuamente l'umano vivo più vicino.\n"
project_path.write_text(project, encoding="utf-8")

testdoc = testdoc_path.read_text(encoding="utf-8")
if "### Dummy spawn iniziale" not in testdoc:
    testdoc += "\n\n### Dummy spawn iniziale\n\nVerificare live che entrambi i dummy compaiano vivi nella propria Spawn Room al primo avvio, senza morte all'origine della mappa; dopo circa 1 s devono essere spostati a distanza visibile dall'obiettivo/bandiera (target 10 m, minimo accettato 6 m). Dopo una morte, il respawn resta 30 s e la stessa uscita sicura deve ripetersi.\n"
testdoc_path.write_text(testdoc, encoding="utf-8")

changelog = changelog_path.read_text(encoding="utf-8")
entry = "- Dummy bot: creazione iniziale su Spawn Point reale, uscita dalla spawn ritardata di 1 s e destinazione 6–16 m dal target; riallineato `PLAYER VIBES` senza spazi manuali.\n"
if entry not in changelog:
    changelog = changelog.rstrip() + "\n" + entry
changelog_path.write_text(changelog, encoding="utf-8")

marker = root / "docs/.functional-dummy-spawn-hud-trigger"
if marker.exists():
    marker.unlink()
