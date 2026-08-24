from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

source_paths = [
    ROOT / "workshop" / "ruang_irama.it-IT.workshop",
    ROOT / "tests" / "fixtures" / "semantic_reference.txt",
]

old_failure = '''\t\tIf(Distance Between(Event Player.PosisiBangkitAman, Vector(0, 0, 0)) <= 0.100);\n\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("No safe resurrection position was found. Release Jump and try again.") : Event Player.IndeksBahasa == 1 ? Custom String("Tidak ada posisi bangkit yang aman. Lepaskan Jump lalu coba lagi.") : Custom String("ไม่พบตำแหน่งฟื้นคืนชีพที่ปลอดภัย ปล่อยปุ่มกระโดดแล้วลองอีกครั้ง"));\n\t\t\tAbort;\n\t\tEnd;\n\t\tResurrect(Event Player);\n\t\tTeleport(Event Player, Event Player.PosisiBangkitAman);'''

new_failure = '''\t\tIf(Distance Between(Event Player.PosisiBangkitAman, Vector(0, 0, 0)) <= 0.100);\n\t\t\tEvent Player.PosisiBangkitAman = Nearest Walkable Position(Event Player.PosisiMati);\n\t\tEnd;\n\t\tIf(Distance Between(Event Player.PosisiBangkitAman, Vector(0, 0, 0)) <= 0.100);\n\t\t\tEvent Player.PosisiBangkitAman = Nearest Walkable Position(Position Of(First Of(Spawn Points(Team Of(Event Player)))));\n\t\tEnd;\n\t\tIf(Distance Between(Event Player.PosisiBangkitAman, Vector(0, 0, 0)) <= 0.100);\n\t\t\tEvent Player.PosisiBangkitAman = Event Player.PosisiMati;\n\t\tEnd;\n\t\tResurrect(Event Player);\n\t\tTeleport(Event Player, Event Player.PosisiBangkitAman);'''

for path in source_paths:
    text = path.read_text(encoding="utf-8")
    if text.count("Set Respawn Max Time(Event Player, 30);") != 1:
        raise SystemExit(f"expected one 30s dummy respawn in {path}, found {text.count('Set Respawn Max Time(Event Player, 30);')}")
    text = text.replace("Set Respawn Max Time(Event Player, 30);", "Set Respawn Max Time(Event Player, 3);", 1)
    if text.count(old_failure) != 1:
        raise SystemExit(f"expected one Jump resurrect failure block in {path}, found {text.count(old_failure)}")
    text = text.replace(old_failure, new_failure, 1)
    path.write_text(text, encoding="utf-8")

validator = ROOT / "tools" / "validate_workshop.py"
text = validator.read_text(encoding="utf-8")
if text.count("Set Respawn Max Time(Event Player, 30);") != 1:
    raise SystemExit(f"expected one validator 30s respawn expectation, found {text.count('Set Respawn Max Time(Event Player, 30);')}")
text = text.replace("Set Respawn Max Time(Event Player, 30);", "Set Respawn Max Time(Event Player, 3);", 1)
validator.write_text(text, encoding="utf-8")

dummy_tests = ROOT / "tests" / "test_dummy_bots.py"
text = dummy_tests.read_text(encoding="utf-8")
old_test = '''    def test_dummy_respawn_is_30_seconds(self):\n        self.assertIn("Set Respawn Max Time(Event Player, 30);", self.it)'''
new_test = '''    def test_dummy_respawn_is_3_seconds(self):\n        for source in (self.it, self.en):\n            self.assertIn("Set Respawn Max Time(Event Player, 3);", source)\n            self.assertNotIn("Set Respawn Max Time(Event Player, 30);", source)'''
if text.count(old_test) != 1:
    raise SystemExit(f"expected one dummy respawn test, found {text.count(old_test)}")
text = text.replace(old_test, new_test, 1)
dummy_tests.write_text(text, encoding="utf-8")

runtime_tests = ROOT / "tests" / "test_runtime_maintenance.py"
text = runtime_tests.read_text(encoding="utf-8")
anchor = '''    def test_custom_string_uses_at_most_three_substitution_values(self):'''
new_runtime_test = '''    def test_jump_resurrect_always_has_non_aborting_fallbacks(self):\n        for source in (self.it, self.en):\n            self.assertNotIn("No safe resurrection position was found.", source)\n            self.assertNotIn("Tidak ada posisi bangkit yang aman.", source)\n            self.assertIn("Event Player.PosisiBangkitAman = Nearest Walkable Position(Event Player.PosisiMati);", source)\n            self.assertIn("Event Player.PosisiBangkitAman = Nearest Walkable Position(Position Of(First Of(Spawn Points(Team Of(Event Player)))));", source)\n            self.assertIn("Event Player.PosisiBangkitAman = Event Player.PosisiMati;", source)\n            self.assertIn("Resurrect(Event Player);\\n\\t\\tTeleport(Event Player, Event Player.PosisiBangkitAman);", source)\n\n\n'''
if anchor not in text:
    raise SystemExit("runtime test insertion anchor not found")
if "test_jump_resurrect_always_has_non_aborting_fallbacks" not in text:
    text = text.replace(anchor, new_runtime_test + anchor, 1)
runtime_tests.write_text(text, encoding="utf-8")

changelog = ROOT / "CHANGELOG.md"
text = changelog.read_text(encoding="utf-8")
old_dummy = "- Confermati massimo un dummy nativo per squadra e respawn massimo 30 secondi."
new_dummy = "- Confermati massimo un dummy nativo per squadra e respawn massimo 3 secondi."
if old_dummy not in text:
    raise SystemExit("changelog dummy respawn line not found")
text = text.replace(old_dummy, new_dummy, 1)
old_jump = "- Sostituito il Jump `Respawn` con `Resurrect`: Resurrect, teleport sicuro e verifica del successo avvengono nello stesso tick senza `Wait`. Un fallimento può essere ritentato soltanto dopo aver rilasciato Jump, senza spam durante lo stesso hold."
new_jump = "- Sostituito il Jump `Respawn` con `Resurrect`: Resurrect, teleport e verifica del successo avvengono nello stesso tick senza `Wait`. Se il controllo sicuro rifiuta il punto casuale e il punto di morte, il sistema prova `Nearest Walkable Position`, poi lo spawn e infine il punto di morte; Jump non viene più bloccato da un errore di posizione sicura."
if old_jump not in text:
    raise SystemExit("changelog Jump resurrect line not found")
text = text.replace(old_jump, new_jump, 1)
old_attach = "Reload sgancia e morte/leave/cambio eroe di uno dei due interrompono automaticamente il collegamento."
new_attach = "Crouch + Reload sgancia soltanto con il menu Melee chiuso; morte/leave/cambio eroe di uno dei due interrompono automaticamente il collegamento."
if old_attach in text:
    text = text.replace(old_attach, new_attach, 1)
changelog.write_text(text, encoding="utf-8")

print("Dummy respawn set to 3s; Jump resurrect now uses non-aborting fallbacks")
