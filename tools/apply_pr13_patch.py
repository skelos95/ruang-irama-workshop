from pathlib import Path

ITALIAN = Path("workshop/ruang_irama.it-IT.workshop")
ENGLISH = Path("tests/fixtures/semantic_reference.txt")

it = ITALIAN.read_text(encoding="utf-8")
en = ENGLISH.read_text(encoding="utf-8")

# Visually move only the right section heading toward its player rows.
for old, new in [
    ('"\\n \\nPLAYER VIBES"', '"\\n \\n     PLAYER VIBES"'),
    ('"\\n \\nMUSIK PEMAIN"', '"\\n \\n     MUSIK PEMAIN"'),
    ('"\\n \\nเพลงของผู้เล่น"', '"\\n \\n     เพลงของผู้เล่น"'),
]:
    for label, text in (("Italian", it), ("English fixture", en)):
        count = text.count(old)
        if count != 1:
            raise SystemExit(f"{label} HUD literal {old!r}: expected 1, found {count}")
    it = it.replace(old, new, 1)
    en = en.replace(old, new, 1)

old_it = '''\tazioni
\t{
\t\tCall Subroutine(KunciBot);
\t}
}

regola("04 - Pemain Keluar: Tenangkan lalu bersihkan pendaftaran")'''
new_it = '''\tazioni
\t{
\t\tCall Subroutine(KunciBot);
\t\tIf(Is Dummy Bot(Event Player) == True);
\t\t\tSet Respawn Max Time(Event Player, 30);
\t\tEnd;
\t}
}

regola("03d - Bot/Dummy: Buat satu bot acak untuk Squadra 1")
{
\tevento
\t{
\t\tOngoing - Global;
\t}

\tcondizioni
\t{
\t\tGlobale.Siap == True;
\t\tIs Game In Progress == True;
\t\tNumber Of Slots(Squadra 1) > 0;
\t\tCount Of(Filtered Array(All Players(Squadra 1), Is Dummy Bot(Current Array Element) == True)) == 0;
\t}

\tazioni
\t{
\t\tCreate Dummy Bot(Tutti gli eroi, Squadra 1, -1, Null, Null);
\t}
}

regola("03e - Bot/Dummy: Buat satu bot acak untuk Squadra 2")
{
\tevento
\t{
\t\tOngoing - Global;
\t}

\tcondizioni
\t{
\t\tGlobale.Siap == True;
\t\tIs Game In Progress == True;
\t\tNumber Of Slots(Squadra 2) > 0;
\t\tCount Of(Filtered Array(All Players(Squadra 2), Is Dummy Bot(Current Array Element) == True)) == 0;
\t}

\tazioni
\t{
\t\tCreate Dummy Bot(Tutti gli eroi, Squadra 2, -1, Null, Null);
\t}
}

regola("03f - Bot/Dummy: Teletrasporta dalla spawn all'obiettivo")
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
\t\tIf(Count Of(All Players On Objective(All Teams)) > 0);
\t\t\tTeleport(Event Player, Position Of(First Of(All Players On Objective(All Teams))));
\t\tElse;
\t\t\tTeleport(Event Player, Objective Position(0));
\t\tEnd;
\t}
}

regola("03g - Bot/Dummy: Guarda sempre il giocatore vivo piu vicino")
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
\t\tCount Of(Filtered Array(Globale.PemainManusia, And(Entity Exists(Current Array Element), And(Has Spawned(Current Array Element), Is Alive(Current Array Element))))) > 0;
\t}

\tazioni
\t{
\t\tStart Facing(Event Player, Direction Towards(Eye Position(Event Player), Eye Position(First Of(Sorted Array(Filtered Array(Globale.PemainManusia, And(Entity Exists(Current Array Element), And(Has Spawned(Current Array Element), Is Alive(Current Array Element)))), Distance Between(Event Player, Current Array Element))))), 1000, To World, Direction and Turn Rate);
\t}
}

regola("03h - Bot/Dummy: Ferma lo sguardo senza giocatori vivi")
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
\t\tCount Of(Filtered Array(Globale.PemainManusia, And(Entity Exists(Current Array Element), And(Has Spawned(Current Array Element), Is Alive(Current Array Element))))) == 0;
\t}

\tazioni
\t{
\t\tStop Facing(Event Player);
\t}
}

regola("03i - Bot/Dummy: Ferma lo sguardo alla morte")
{
\tevento
\t{
\t\tPlayer Died;
\t\tTutti;
\t\tTutti;
\t}

\tcondizioni
\t{
\t\tIs Dummy Bot(Event Player) == True;
\t}

\tazioni
\t{
\t\tStop Facing(Event Player);
\t}
}

regola("04 - Pemain Keluar: Tenangkan lalu bersihkan pendaftaran")'''
if it.count(old_it) != 1:
    raise SystemExit(f"Italian 03c anchor expected once, found {it.count(old_it)}")
it = it.replace(old_it, new_it, 1)

old_en = '''\tactions
\t{
\t\tCall Subroutine(KunciBot);
\t}
}

rule("04 - Pemain Keluar: Tenangkan lalu bersihkan pendaftaran")'''
new_en = '''\tactions
\t{
\t\tCall Subroutine(KunciBot);
\t\tIf(Is Dummy Bot(Event Player) == True);
\t\t\tSet Respawn Max Time(Event Player, 30);
\t\tEnd;
\t}
}

rule("03d - Bot/Dummy: Buat satu bot acak untuk Team 1")
{
\tevent
\t{
\t\tOngoing - Global;
\t}

\tconditions
\t{
\t\tGlobal.Siap == True;
\t\tIs Game In Progress == True;
\t\tNumber Of Slots(Team 1) > 0;
\t\tCount Of(Filtered Array(All Players(Team 1), Is Dummy Bot(Current Array Element) == True)) == 0;
\t}

\tactions
\t{
\t\tCreate Dummy Bot(All Heroes, Team 1, -1, Null, Null);
\t}
}

rule("03e - Bot/Dummy: Buat satu bot acak untuk Team 2")
{
\tevent
\t{
\t\tOngoing - Global;
\t}

\tconditions
\t{
\t\tGlobal.Siap == True;
\t\tIs Game In Progress == True;
\t\tNumber Of Slots(Team 2) > 0;
\t\tCount Of(Filtered Array(All Players(Team 2), Is Dummy Bot(Current Array Element) == True)) == 0;
\t}

\tactions
\t{
\t\tCreate Dummy Bot(All Heroes, Team 2, -1, Null, Null);
\t}
}

rule("03f - Bot/Dummy: Teletrasporta dalla spawn all'obiettivo")
{
\tevent
\t{
\t\tOngoing - Each Player;
\t\tAll;
\t\tAll;
\t}

\tconditions
\t{
\t\tGlobal.Siap == True;
\t\tIs Dummy Bot(Event Player) == True;
\t\tHas Spawned(Event Player) == True;
\t\tIs Alive(Event Player) == True;
\t\tIs In Spawn Room(Event Player) == True;
\t}

\tactions
\t{
\t\tIf(Count Of(All Players On Objective(All Teams)) > 0);
\t\t\tTeleport(Event Player, Position Of(First Of(All Players On Objective(All Teams))));
\t\tElse;
\t\t\tTeleport(Event Player, Objective Position(0));
\t\tEnd;
\t}
}

rule("03g - Bot/Dummy: Guarda sempre il giocatore vivo piu vicino")
{
\tevent
\t{
\t\tOngoing - Each Player;
\t\tAll;
\t\tAll;
\t}

\tconditions
\t{
\t\tGlobal.Siap == True;
\t\tIs Dummy Bot(Event Player) == True;
\t\tHas Spawned(Event Player) == True;
\t\tIs Alive(Event Player) == True;
\t\tCount Of(Filtered Array(Global.PemainManusia, And(Entity Exists(Current Array Element), And(Has Spawned(Current Array Element), Is Alive(Current Array Element))))) > 0;
\t}

\tactions
\t{
\t\tStart Facing(Event Player, Direction Towards(Eye Position(Event Player), Eye Position(First Of(Sorted Array(Filtered Array(Global.PemainManusia, And(Entity Exists(Current Array Element), And(Has Spawned(Current Array Element), Is Alive(Current Array Element)))), Distance Between(Event Player, Current Array Element))))), 1000, To World, Direction and Turn Rate);
\t}
}

rule("03h - Bot/Dummy: Ferma lo sguardo senza giocatori vivi")
{
\tevent
\t{
\t\tOngoing - Each Player;
\t\tAll;
\t\tAll;
\t}

\tconditions
\t{
\t\tGlobal.Siap == True;
\t\tIs Dummy Bot(Event Player) == True;
\t\tCount Of(Filtered Array(Global.PemainManusia, And(Entity Exists(Current Array Element), And(Has Spawned(Current Array Element), Is Alive(Current Array Element))))) == 0;
\t}

\tactions
\t{
\t\tStop Facing(Event Player);
\t}
}

rule("03i - Bot/Dummy: Ferma lo sguardo alla morte")
{
\tevent
\t{
\t\tPlayer Died;
\t\tAll;
\t\tAll;
\t}

\tconditions
\t{
\t\tIs Dummy Bot(Event Player) == True;
\t}

\tactions
\t{
\t\tStop Facing(Event Player);
\t}
}

rule("04 - Pemain Keluar: Tenangkan lalu bersihkan pendaftaran")'''
if en.count(old_en) != 1:
    raise SystemExit(f"English 03c anchor expected once, found {en.count(old_en)}")
en = en.replace(old_en, new_en, 1)

ITALIAN.write_text(it, encoding="utf-8")
ENGLISH.write_text(en, encoding="utf-8")

Path("tests/test_dummy_bots.py").write_text('''from pathlib import Path\nimport unittest\n\nROOT = Path(__file__).resolve().parents[1]\n\nclass DummyBotFeatureTests(unittest.TestCase):\n    @classmethod\n    def setUpClass(cls):\n        cls.it = (ROOT / "workshop" / "ruang_irama.it-IT.workshop").read_text(encoding="utf-8")\n        cls.en = (ROOT / "tests" / "fixtures" / "semantic_reference.txt").read_text(encoding="utf-8")\n\n    def test_player_vibes_title_is_shifted_right(self):\n        self.assertIn("\\n \\n     PLAYER VIBES", self.it)\n        self.assertIn("\\n \\n     MUSIK PEMAIN", self.it)\n\n    def test_exactly_one_creation_rule_per_team(self):\n        self.assertEqual(self.it.count("Create Dummy Bot(Tutti gli eroi, Squadra 1, -1, Null, Null);"), 1)\n        self.assertEqual(self.it.count("Create Dummy Bot(Tutti gli eroi, Squadra 2, -1, Null, Null);"), 1)\n        self.assertEqual(self.en.count("Create Dummy Bot(All Heroes, Team 1, -1, Null, Null);"), 1)\n        self.assertEqual(self.en.count("Create Dummy Bot(All Heroes, Team 2, -1, Null, Null);"), 1)\n\n    def test_dummy_respawn_is_30_seconds(self):\n        self.assertIn("Set Respawn Max Time(Event Player, 30);", self.it)\n\n    def test_spawn_teleport_targets_objective(self):\n        self.assertIn("Is In Spawn Room(Event Player) == True;", self.it)\n        self.assertIn("All Players On Objective(All Teams)", self.it)\n        self.assertIn("Objective Position(0)", self.it)\n\n    def test_dummy_faces_nearest_living_human_without_extra_loop(self):\n        self.assertIn("Start Facing(Event Player", self.it)\n        self.assertIn("Sorted Array(Filtered Array(Globale.PemainManusia", self.it)\n        self.assertIn("Direction and Turn Rate", self.it)\n        self.assertIn("Stop Facing(Event Player);", self.it)\n        self.assertEqual(self.it.count("Loop;"), 1)\n\nif __name__ == "__main__":\n    unittest.main()\n''', encoding="utf-8")

marker = Path("docs/HUD_DUMMY_BOTS_WORK.md")
if marker.exists():
    marker.unlink()

# Self-remove after a successful patch; the runner will commit the deletion.
Path(__file__).unlink()
