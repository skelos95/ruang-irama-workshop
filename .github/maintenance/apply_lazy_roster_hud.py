from pathlib import Path
import re

ZERO12 = "Array(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 occurrence, found {count}")
    return text.replace(old, new, 1)


def rule_slice(text: str, marker: str, keyword: str) -> tuple[int, int, str]:
    start = text.index(marker)
    next_marker = f"\n\n{keyword}(\""
    end = text.index(next_marker, start + len(marker))
    return start, end, text[start:end]


def patch_source(path: Path, italian: bool) -> None:
    text = path.read_text(encoding="utf-8")
    g = "Globale" if italian else "Global"
    keyword = "regola" if italian else "rule"
    event_kw = "evento" if italian else "event"
    cond_kw = "condizioni" if italian else "conditions"
    act_kw = "azioni" if italian else "actions"
    all_kw = "Tutti" if italian else "All"

    # Freeze handle tables at 12 stable indices, but leave them empty until a real player owns a slot.
    old_init = (
        f'{g}.NamaSlotHUD = Array(Custom String(""), Custom String(""), Custom String(""), Custom String(""), Custom String(""), Custom String(""), Custom String(""), Custom String(""), Custom String(""), Custom String(""), Custom String(""), Custom String(""));\n'
        f'\t\t{g}.HudKiriPemain = Empty Array;\n'
        f'\t\t{g}.HudKananPemain = Empty Array;\n'
        f'\t\t{g}.JarakKamera = 2.000;'
    )
    new_init = (
        f'{g}.NamaSlotHUD = Array(Custom String(""), Custom String(""), Custom String(""), Custom String(""), Custom String(""), Custom String(""), Custom String(""), Custom String(""), Custom String(""), Custom String(""), Custom String(""), Custom String(""));\n'
        f'\t\t{g}.HudKiriPemain = {ZERO12};\n'
        f'\t\t{g}.HudKananPemain = {ZERO12};\n'
        f'\t\t{g}.JarakKamera = 2.000;'
    )
    text = replace_once(text, old_init, new_init, f"{path.name}: fixed handle tables")

    # Extract the existing renderer so its visual contract stays byte-for-byte equivalent apart from the frozen slot index.
    marker_00b = f'{keyword}("00b - HUD Roster: Dua belas slot global permanen")'
    s0, e0, old_roster = rule_slice(text, marker_00b, keyword)
    create_lines = [line.strip() for line in old_roster.splitlines() if line.strip().startswith("Create HUD Text(")]
    if len(create_lines) != 2:
        raise SystemExit(f"{path.name}: expected two roster Create HUD calls, found {len(create_lines)}")
    frozen_old = f"Evaluate Once({g}.IndeksPemilih)"
    frozen_new = "Evaluate Once(Event Player.UrutanHUD)"
    left_call = create_lines[0].replace(frozen_old, frozen_new)
    right_call = create_lines[1].replace(frozen_old, frozen_new)
    text = text[:s0] + text[e0:]

    # Replace the alias-only rule with a lazy creator: rows are born only after slot/name/player are valid.
    marker_02b = f'{keyword}("02b - HUD Pemain: Hubungkan ke slot global")'
    s2, e2, _ = rule_slice(text, marker_02b, keyword)
    lazy_rule = f'''{keyword}("02b - HUD Pemain: Hubungkan ke slot global")
{{
\t{event_kw}
\t{{
\t\tOngoing - Each Player;
\t\t{all_kw};
\t\t{all_kw};
\t}}

\t{cond_kw}
\t{{
\t\t{g}.Siap == True;
\t\tEvent Player.Manusia == True;
\t\tEvent Player.BotOtomatis == False;
\t\tIs Dummy Bot(Event Player) == False;
\t\tArray Contains({g}.PemainManusia, Event Player) == True;
\t\tHas Spawned(Event Player) == True;
\t\tEvent Player.TimTerakhir == Team Of(Event Player);
\t\tEvent Player.SegarkanRosterTertunda == False;
\t\tEvent Player.NamaTampilan != Null;
\t\tEvent Player.NamaTampilan != Custom String("");
\t\tEvent Player.UrutanHUD >= 0;
\t\t{g}.PemainSlotHUD[Event Player.UrutanHUD] == Event Player;
\t\tEvent Player.HudPemainDibuat == False;
\t}}

\t{act_kw}
\t{{
\t\t"Buat pasangan HUD hanya setelah slot berisi identitas valid. Setelah dibuat, pasangan tetap hidup selama pindah tim dan hanya dihancurkan saat benar-benar keluar."
\t\tIf(Or({g}.HudKiriPemain[Event Player.UrutanHUD] == 0, {g}.HudKiriPemain[Event Player.UrutanHUD] == Null));
\t\t\t{left_call}
\t\t\t{g}.HudKiriPemain[Event Player.UrutanHUD] = Last Text ID;
\t\tEnd;
\t\tIf(Or({g}.HudKananPemain[Event Player.UrutanHUD] == 0, {g}.HudKananPemain[Event Player.UrutanHUD] == Null));
\t\t\t{right_call}
\t\t\t{g}.HudKananPemain[Event Player.UrutanHUD] = Last Text ID;
\t\tEnd;
\t\tEvent Player.HudKiri = {g}.HudKiriPemain[Event Player.UrutanHUD];
\t\tEvent Player.HudKanan = {g}.HudKananPemain[Event Player.UrutanHUD];
\t\tEvent Player.HudPemainDibuat = And(And(Event Player.HudKiri != Null, Event Player.HudKiri != 0), And(Event Player.HudKanan != Null, Event Player.HudKanan != 0));
\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Welcome to CHILL. Pick a vibe, pick a color, stay weird.") : Event Player.IndeksBahasa == 1 ? Custom String("Selamat datang di CHILL. Pilih vibe, pilih warna, tetap aneh.") : Custom String("ยินดีต้อนรับสู่ CHILL เลือกเพลง เลือกสี แล้วกวนแบบพอดี ๆ"));
\t}}
}}'''
    text = text[:s2] + lazy_rule + text[e2:]

    # A true leave may recycle a slot. Destroy that slot's pair so the next occupant is created from a non-empty identity.
    cleanup_anchor = (
        f'\t\t\tIf({g}.TeksDuniaPemain[{g}.IndeksPembersihan] != 0);\n'
        f'\t\t\t\tDestroy In-World Text({g}.TeksDuniaPemain[{g}.IndeksPembersihan]);\n'
        f'\t\t\tEnd;\n'
        f'\t\t\t{g}.PemainSlotHUD[{g}.IndeksUtangKeluar] = Null;'
    )
    cleanup_new = (
        f'\t\t\tIf({g}.TeksDuniaPemain[{g}.IndeksPembersihan] != 0);\n'
        f'\t\t\t\tDestroy In-World Text({g}.TeksDuniaPemain[{g}.IndeksPembersihan]);\n'
        f'\t\t\tEnd;\n'
        f'\t\t\tIf({g}.HudKiriPemain[{g}.IndeksUtangKeluar] != 0);\n'
        f'\t\t\t\tDestroy HUD Text({g}.HudKiriPemain[{g}.IndeksUtangKeluar]);\n'
        f'\t\t\t\t{g}.HudKiriPemain[{g}.IndeksUtangKeluar] = 0;\n'
        f'\t\t\tEnd;\n'
        f'\t\t\tIf({g}.HudKananPemain[{g}.IndeksUtangKeluar] != 0);\n'
        f'\t\t\t\tDestroy HUD Text({g}.HudKananPemain[{g}.IndeksUtangKeluar]);\n'
        f'\t\t\t\t{g}.HudKananPemain[{g}.IndeksUtangKeluar] = 0;\n'
        f'\t\t\tEnd;\n'
        f'\t\t\t{g}.PemainSlotHUD[{g}.IndeksUtangKeluar] = Null;'
    )
    text = replace_once(text, cleanup_anchor, cleanup_new, f"{path.name}: true-leave slot HUD cleanup")
    path.write_text(text, encoding="utf-8")


for p, it in ((Path("workshop/ruang_irama.it-IT.workshop"), True), (Path("tests/fixtures/semantic_reference.txt"), False)):
    patch_source(p, it)

# Validator: the two roster Create HUD calls now live in the per-player slot binder and use a frozen numeric slot.
vp = Path("tools/validate_workshop.py")
v = vp.read_text(encoding="utf-8")
v = replace_once(v,
'''    global_slot_roster = next(
        (
            rule for rule in rules
            if event_type(rule) == "Ongoing - Global"
            and "Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)]" in rule.body
            and "Global.NamaSlotHUD[Evaluate Once(Global.IndeksPemilih)]" in rule.body
            and "For Global Variable(IndeksPemilih, 0, 12, 1);" in rule.body
        ),
        None,
    )
''',
'''    global_slot_roster = next(
        (
            rule for rule in rules
            if event_type(rule) == "Ongoing - Each Player"
            and "Global.PemainSlotHUD[Evaluate Once(Event Player.UrutanHUD)]" in rule.body
            and "Global.NamaSlotHUD[Evaluate Once(Event Player.UrutanHUD)]" in rule.body
            and "Global.HudKiriPemain[Event Player.UrutanHUD] = Last Text ID;" in rule.body
            and "Global.HudKananPemain[Event Player.UrutanHUD] = Last Text ID;" in rule.body
        ),
        None,
    )
''', "validator roster finder")
v = v.replace("renderer roster globale deve avere esattamente due Create HUD nel loop", "renderer roster globale deve avere esattamente due Create HUD nel binder")
v = v.replace('"Left": "1 + Evaluate Once(Global.IndeksPemilih)",', '"Left": "1 + Evaluate Once(Event Player.UrutanHUD)",')
v = v.replace('"Right": "-13 + Evaluate Once(Global.IndeksPemilih)",', '"Right": "-13 + Evaluate Once(Event Player.UrutanHUD)",')
v = v.replace("Global.NamaSlotHUD[Evaluate Once(Global.IndeksPemilih)]", "Global.NamaSlotHUD[Evaluate Once(Event Player.UrutanHUD)]")
v = v.replace("Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)]", "Global.PemainSlotHUD[Evaluate Once(Event Player.UrutanHUD)]")
v = v.replace("Evaluate Once(Global.IndeksPemilih) == Global.SlotHUDTerakhir", "Evaluate Once(Event Player.UrutanHUD) == Global.SlotHUDTerakhir")
v = replace_once(v,
'''    checks.require(
        "Global.PemainSlotHUD = Array(Null, Null, Null, Null, Null, Null, Null, Null, Null, Null, Null, Null);"
        in source,
        "tabella globale PemainSlotHUD non inizializzata a 12 slot",
    )
''',
'''    checks.require(
        "Global.PemainSlotHUD = Array(Null, Null, Null, Null, Null, Null, Null, Null, Null, Null, Null, Null);"
        in source,
        "tabella globale PemainSlotHUD non inizializzata a 12 slot",
    )
    checks.require(
        "Global.HudKiriPemain = Array(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);" in source
        and "Global.HudKananPemain = Array(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);" in source,
        "tabelle handle roster devono avere 12 slot vuoti stabili",
    )
''', "validator handle table init")
v = replace_once(v,
'''        ready_alias = "Event Player.HudPemainDibuat = And(Event Player.HudKiri != Null, Event Player.HudKanan != Null);"
''',
'''        ready_alias = "Event Player.HudPemainDibuat = And(And(Event Player.HudKiri != Null, Event Player.HudKiri != 0), And(Event Player.HudKanan != Null, Event Player.HudKanan != 0));"
''', "validator ready alias")
v = replace_once(v,
'''    for forbidden, label in (
        ("Destroy HUD Text(Global.HudKiriPemain[", "destroy righe Left permanenti"),
        ("Destroy HUD Text(Global.HudKananPemain[", "destroy righe Right permanenti"),
        ("Modify Global Variable(HudKiriPemain, Remove From Array By Index", "rimozione handle Left permanenti"),
        ("Modify Global Variable(HudKananPemain, Remove From Array By Index", "rimozione handle Right permanenti"),
        ("Event Player.HudKiri = Last Text ID;", "ownership roster Left per-player"),
        ("Event Player.HudKanan = Last Text ID;", "ownership roster Right per-player"),
    ):
        checks.require(forbidden not in source, f"roster globale persistente vieta {label}")
''',
'''    checks.equal(source.count("Destroy HUD Text(Global.HudKiriPemain["), 1,
                 "solo il vero leave può distruggere una riga roster Left")
    checks.equal(source.count("Destroy HUD Text(Global.HudKananPemain["), 1,
                 "solo il vero leave può distruggere una riga roster Right")
    for token, label in (
        ("Global.HudKiriPemain[Global.IndeksUtangKeluar] = 0;", "reset handle Left al vero leave"),
        ("Global.HudKananPemain[Global.IndeksUtangKeluar] = 0;", "reset handle Right al vero leave"),
    ):
        checks.require(token in source, f"roster globale lazy: {label} assente")
    for forbidden, label in (
        ("Modify Global Variable(HudKiriPemain, Remove From Array By Index", "rimozione handle Left per indice"),
        ("Modify Global Variable(HudKananPemain, Remove From Array By Index", "rimozione handle Right per indice"),
        ("Event Player.HudKiri = Last Text ID;", "ownership roster Left per-player"),
        ("Event Player.HudKanan = Last Text ID;", "ownership roster Right per-player"),
    ):
        checks.require(forbidden not in source, f"roster globale persistente vieta {label}")
''', "validator cleanup ownership")
vp.write_text(v, encoding="utf-8")

# Runtime/static tests: frozen order and identity now use Event Player.UrutanHUD at creation time.
p = Path("tests/test_dummy_bots.py")
t = p.read_text(encoding="utf-8")
t = t.replace('"1 + Evaluate Once(Globale.IndeksPemilih)" if source is self.it else "1 + Evaluate Once(Global.IndeksPemilih)"', '"1 + Evaluate Once(Event Player.UrutanHUD)"')
t = t.replace('"-13 + Evaluate Once(Globale.IndeksPemilih)" if source is self.it else "-13 + Evaluate Once(Global.IndeksPemilih)"', '"-13 + Evaluate Once(Event Player.UrutanHUD)"')
t = t.replace('"-99 + Evaluate Once(Globale.IndeksPemilih)" if source is self.it else "-99 + Evaluate Once(Global.IndeksPemilih)"', '"-99 + Evaluate Once(Event Player.UrutanHUD)"')
p.write_text(t, encoding="utf-8")

p = Path("tests/test_runtime_maintenance.py")
t = p.read_text(encoding="utf-8")
start = t.index("    def test_cached_player_name_drives_roster_and_world_text(self):\n")
end = t.index("    def test_aim_scans_are_scheduler_cached(self):\n", start)
replacement = '''    def test_cached_player_name_drives_roster_and_world_text(self):
        for source, global_name, rule_kw in ((self.it, "Globale", "regola"), (self.en, "Global", "rule")):
            self.assertIn("107: NamaTampilan", source)
            self.assertIn("63: PemainSlotHUD", source)
            self.assertIn("64: NamaSlotHUD", source)

            classifier = source.split(f'{rule_kw}("02 - Pemain: Pisahkan manusia dari pasukan kaleng")', 1)[1].split(f'{rule_kw}("02b - HUD Pemain', 1)[0]
            self.assertIn('Event Player.NamaTampilan = Evaluate Once(Custom String("{0}", Event Player));', classifier)
            self.assertIn(f'{global_name}.PemainSlotHUD[Event Player.UrutanHUD] = Event Player;', classifier)
            self.assertIn(f'{global_name}.NamaSlotHUD[Event Player.UrutanHUD] = Event Player.NamaTampilan;', classifier)

            roster = source.split(f'{rule_kw}("02b - HUD Pemain: Hubungkan ke slot global")', 1)[1].split(f'{rule_kw}("03c - Bot/Dummy', 1)[0]
            slot = 'Evaluate Once(Event Player.UrutanHUD)'
            self.assertIn(f'{global_name}.NamaSlotHUD[{slot}] != Custom String("")', roster)
            self.assertIn(f'Custom String("{{0}} - {{1}} MIN", {global_name}.NamaSlotHUD[{slot}]', roster)
            self.assertIn(f'Custom String("{{0}} - {{1}}", {global_name}.NamaSlotHUD[{slot}]', roster)
            self.assertIn(f'{global_name}.PemainSlotHUD[{slot}]', roster)
            self.assertIn(f'{global_name}.HudKiriPemain[Event Player.UrutanHUD] = Last Text ID;', roster)
            self.assertIn(f'{global_name}.HudKananPemain[Event Player.UrutanHUD] = Last Text ID;', roster)

            inspect = source.split(f'{rule_kw}("13 - Intip Pahlawan: Nama mengikuti target bidikan tanpa Wait")', 1)[1].split(f'{rule_kw}("16a - Anran', 1)[0]
            self.assertIn(f'{global_name}.NamaSlotHUD[Player Variable(Event Player.TargetInspeksi, UrutanHUD)]', inspect)

            teleport = source.split(f'{rule_kw}("19d - Teleportasi Jongkok: Buat ulang nama saat target berubah")', 1)[1].split(f'{rule_kw}("19e - Teleportasi Jongkok', 1)[0]
            self.assertIn(f'{global_name}.NamaSlotHUD[Player Variable(Event Player.CalonTargetTeleportasi, UrutanHUD)]', teleport)

            fast = source.split(f'{rule_kw}("89a - Subrutin: Proses status cepat pemain")', 1)[1].split(f'{rule_kw}("89b - Subrutin', 1)[0]
            cache_invalid = f'Or({global_name}.PemainAktif.NamaTampilan == Null, {global_name}.PemainAktif.NamaTampilan == Custom String(""))'
            self.assertIn(cache_invalid, fast)
            self.assertIn(f'{global_name}.NamaSlotHUD[{global_name}.PemainAktif.UrutanHUD] != Custom String("")', fast)
            self.assertIn(f'{global_name}.PemainAktif.NamaTampilan = {global_name}.NamaSlotHUD[{global_name}.PemainAktif.UrutanHUD];', fast)
            self.assertIn(f'Custom String("{{0}}", {global_name}.PemainAktif) != Custom String("")', fast)
            self.assertIn(f'{global_name}.PemainAktif.NamaTampilan = Evaluate Once(Custom String("{{0}}", {global_name}.PemainAktif));', fast)
            self.assertLess(fast.index(cache_invalid), fast.index(f"{global_name}.PemainAktif.TimTerakhir != Team Of({global_name}.PemainAktif)"))

'''
t = t[:start] + replacement + t[end:]
p.write_text(t, encoding="utf-8")

# Mutation tests: point renderer mutations at the lazy global-slot binder.
p = Path("tests/test_validate_workshop.py")
t = p.read_text(encoding="utf-8")
t = t.replace('validator.event_type(rule) == "Ongoing - Global"\n            and "Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)]" in rule.body\n            and "Global.HudKananPemain = Append To Array" in rule.body', 'validator.event_type(rule) == "Ongoing - Each Player"\n            and "Global.PemainSlotHUD[Evaluate Once(Event Player.UrutanHUD)]" in rule.body\n            and "Global.HudKananPemain[Event Player.UrutanHUD] = Last Text ID;" in rule.body')
t = t.replace("Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)]", "Global.PemainSlotHUD[Evaluate Once(Event Player.UrutanHUD)]")
t = t.replace("Global.NamaSlotHUD[Evaluate Once(Global.IndeksPemilih)]", "Global.NamaSlotHUD[Evaluate Once(Event Player.UrutanHUD)]")
t = t.replace("Evaluate Once(Global.IndeksPemilih) == Global.SlotHUDTerakhir", "Evaluate Once(Event Player.UrutanHUD) == Global.SlotHUDTerakhir")
t = t.replace('validator.event_type(rule) == "Ongoing - Global" and "Global.HudKiriPemain = Append To Array" in rule.body', 'validator.event_type(rule) == "Ongoing - Each Player" and "Global.HudKiriPemain[Event Player.UrutanHUD] = Last Text ID;" in rule.body')
t = t.replace('validator.event_type(rule) == "Ongoing - Global" and "Global.HudKananPemain = Append To Array" in rule.body', 'validator.event_type(rule) == "Ongoing - Each Player" and "Global.HudKananPemain[Event Player.UrutanHUD] = Last Text ID;" in rule.body')
t = t.replace("1 + Evaluate Once(Global.IndeksPemilih)", "1 + Evaluate Once(Event Player.UrutanHUD)")
t = t.replace("-13 + Evaluate Once(Global.IndeksPemilih)", "-13 + Evaluate Once(Event Player.UrutanHUD)")
t = t.replace('ready = "\\t\\tEvent Player.HudPemainDibuat = And(Event Player.HudKiri != Null, Event Player.HudKanan != Null);\\n"', 'ready = "\\t\\tEvent Player.HudPemainDibuat = And(And(Event Player.HudKiri != Null, Event Player.HudKiri != 0), And(Event Player.HudKanan != Null, Event Player.HudKanan != 0));\\n"')
p.write_text(t, encoding="utf-8")

# Changelog: record the live evidence and the architectural correction.
p = Path("CHANGELOG.md")
t = p.read_text(encoding="utf-8")
anchor = "Stato: **live-pending**.\n\n"
entry = "- Corretto il rendering iniziale delle righe roster globali: le coppie Left/Right non vengono più create quando `PemainSlotHUD`/`NamaSlotHUD` sono ancora vuoti. Ogni slot crea i propri due handle solo dopo l'assegnazione di un'identità valida; il cambio squadra riusa gli stessi handle, mentre un vero leave distrugge soltanto la coppia dello slot liberato. Questo elimina il caso live in cui la riga occupava spazio ma il nome restava invisibile finché `Name Color` non forzava una rivalutazione HUD.\n"
t = replace_once(t, anchor, anchor + entry, "changelog live blank-row fix")
p.write_text(t, encoding="utf-8")

print("lazy roster HUD patch applied")
