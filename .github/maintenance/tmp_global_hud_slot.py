from pathlib import Path
import re

FILES = (
    (Path('workshop/ruang_irama.it-IT.workshop'), 'Globale', 'regola', 'evento', 'condizioni', 'azioni', 'Custom Color(255, 255, 255, 255)'),
    (Path('tests/fixtures/semantic_reference.txt'), 'Global', 'rule', 'event', 'conditions', 'actions', 'Color(White)'),
)


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1, found {count}')
    return text.replace(old, new, 1)


def replace_rule(text, rule_kw, start_name, next_name, replacement, label):
    start = text.find(f'{rule_kw}("{start_name}')
    end = text.find(f'{rule_kw}("{next_name}', start)
    if start < 0 or end < 0:
        raise SystemExit(f'{label}: rule bounds not found')
    return text[:start] + replacement.rstrip() + '\n\n' + text[end:]


for path, g, rule_kw, event_kw, conditions_kw, actions_kw, white in FILES:
    text = path.read_text(encoding='utf-8')

    # Two persistent 12-slot identity tables, independent from the transient player entity.
    decl = f'\t\t62: PemainPengganti\n'
    text = replace_once(
        text,
        decl,
        decl + '\t\t63: PemainSlotHUD\n\t\t64: NamaSlotHUD\n',
        f'{path}: global slot declarations',
    )

    slot_init = f'\t\t{g}.SlotHUDTersedia = Array(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11);\n'
    persistent_init = (
        slot_init
        + f'\t\t{g}.PemainSlotHUD = Array(Null, Null, Null, Null, Null, Null, Null, Null, Null, Null, Null, Null);\n'
        + f'\t\t{g}.NamaSlotHUD = Array(Custom String(""), Custom String(""), Custom String(""), Custom String(""), Custom String(""), Custom String(""), Custom String(""), Custom String(""), Custom String(""), Custom String(""), Custom String(""), Custom String(""));\n'
        + f'\t\t{g}.HudKiriPemain = Empty Array;\n'
        + f'\t\t{g}.HudKananPemain = Empty Array;\n'
    )
    text = replace_once(text, slot_init, persistent_init, f'{path}: global slot initialization')

    slot = f'Evaluate Once({g}.IndeksPemilih)'
    occupant = f'{g}.PemainSlotHUD[{slot}]'
    stable_name = f'{g}.NamaSlotHUD[{slot}]'
    lang = 'Player Variable(Local Player, IndeksBahasa)'
    icon = f'{occupant} != Null ? {g}.DaftarIkon[Player Variable({occupant}, IndeksIkon)] : Custom String("")'
    hero = f'{occupant} != Null ? Hero Icon String(Is Duplicating({occupant}) ? Hero Being Duplicated({occupant}) : Hero Of({occupant})) : Custom String("")'
    minutes = f'{occupant} != Null ? Player Variable({occupant}, MenitLobi) : 0'
    name_line = (
        f'{lang} == 0 ? Custom String("{{0}} - {{1}} MIN", {stable_name}, {minutes}) : '
        f'{lang} == 1 ? Custom String("{{0}} - {{1}} MENIT", {stable_name}, {minutes}) : '
        f'Custom String("{{0}} - {{1}} นาที", {stable_name}, {minutes})'
    )
    chill_star = (
        f'{slot} == {g}.SlotHUDTerakhir ? {g}.PemimpinPilihan != Null ? '
        f'{lang} == 2 ? Custom String("\\n \\nดาวสายชิล: {{0}}", {g}.PemimpinPilihan) : '
        f'{lang} == 1 ? Custom String("\\n \\nBINTANG CHILL: {{0}}", {g}.PemimpinPilihan) : '
        f'Custom String("\\n \\nCHILL STAR: {{0}}", {g}.PemimpinPilihan) : Custom String("") : Custom String("")'
    )
    diagnostic = (
        f'And({g}.DiagnostikPerforma == True, And(Local Player == Host Player, {slot} == {g}.SlotHUDTerakhir)) ? Custom String("{{0}}\\n{{1}}", '
        f'{lang} == 2 ? Custom String("\\n \\nโหลด {{0}}% | เฉลี่ย {{1}}% | สูงสุด {{2}}%", Server Load, Server Load Average, Server Load Peak) : '
        f'{lang} == 1 ? Custom String("\\n \\nBEBAN {{0}}% | RATA {{1}}% | PUNCAK {{2}}%", Server Load, Server Load Average, Server Load Peak) : '
        f'Custom String("\\n \\nLOAD {{0}}% | AVG {{1}}% | MAX {{2}}%", Server Load, Server Load Average, Server Load Peak), '
        f'Custom String("HUD {{0}} | IWT {{1}}", 10 + Count Of(Filtered Array({g}.HudKiriPemain, Current Array Element != 0)) + Count Of(Filtered Array({g}.HudKananPemain, Current Array Element != 0)) + Count Of(Filtered Array({g}.HudMenuPemain, Current Array Element != 0)) + Count Of(Filtered Array({g}.PemainManusia, And(Player Variable(Current Array Element, HudEfekNasib) != Null, Player Variable(Current Array Element, HudEfekNasib) != 0))), Count Of(Filtered Array({g}.TeksDuniaPemain, Current Array Element != 0)) + Count Of(Filtered Array({g}.PemainManusia, And(Player Variable(Current Array Element, TeksTeleportasi) != Null, Player Variable(Current Array Element, TeksTeleportasi) != 0))) + Count Of(Filtered Array(All Players(All Teams), And(Player Variable(Current Array Element, TeksVisiNasib) != Null, Player Variable(Current Array Element, TeksVisiNasib) != 0))))) : Custom String("")'
    )
    left_text = f'{stable_name} != Custom String("") ? Custom String("{{0}}{{1}}{{2}}", Custom String("{{0}} {{1}} {{2}}", {icon}, {hero}, {name_line}), {chill_star}, {diagnostic}) : Custom String("")'
    soundtrack = (
        f'{occupant} != Null ? Player Variable({occupant}, MusikKhusus) != Null ? Player Variable({occupant}, MusikKhusus) : '
        f'Player Variable({occupant}, IndeksGenre) >= 0 ? {g}.DaftarGenre[Player Variable({occupant}, IndeksGenre)] : '
        f'{lang} == 0 ? Custom String("no soundtrack yet") : {lang} == 1 ? Custom String("belum pilih musik") : Custom String("ยังไม่ได้เลือกเพลง") : Custom String("")'
    )
    right_text = f'{stable_name} != Custom String("") ? Custom String("{{0}} {{1}} {{2}}", {icon}, {hero}, Custom String("{{0}} - {{1}}", {stable_name}, {soundtrack})) : Custom String("")'
    row_color = f'{occupant} != Null ? Player Variable({occupant}, WarnaNama) : {white}'

    roster_global_rule = f'''{rule_kw}("00b - HUD Roster: Dua belas slot global permanen")
{{
\t{event_kw}
\t{{
\t\tOngoing - Global;
\t}}

\t{conditions_kw}
\t{{
\t\t{g}.Siap == True;
\t\tCount Of({g}.HudKiriPemain) == 0;
\t\tCount Of({g}.HudKananPemain) == 0;
\t}}

\t{actions_kw}
\t{{
\t\t"Dua belas pasangan HUD dimiliki konteks global. Entitas pemain hanya mengisi slot; pindah tim tidak pernah menciptakan ulang baris."
\t\t{g}.HudKiriPemain = Empty Array;
\t\t{g}.HudKananPemain = Empty Array;
\t\tFor Global Variable(IndeksPemilih, 0, 12, 1);
\t\t\tCreate HUD Text({g}.PemainManusia, Null, {left_text}, Null, Left, 1 + {slot}, {white}, {row_color}, {white}, Visible To String and Color, Visible Never);
\t\t\t{g}.HudKiriPemain = Append To Array({g}.HudKiriPemain, Last Text ID);
\t\t\tCreate HUD Text({g}.PemainManusia, Null, {right_text}, Null, Right, -13 + {slot}, {white}, {row_color}, {white}, Visible To String and Color, Visible Never);
\t\t\t{g}.HudKananPemain = Append To Array({g}.HudKananPemain, Last Text ID);
\t\tEnd;
\t}}
}}
'''
    insert_anchor = f'{rule_kw}("00a1 - Umum: Mulai mode segera saat menunggu pemain")'
    if insert_anchor not in text:
        raise SystemExit(f'{path}: roster global insertion anchor missing')
    text = text.replace(insert_anchor, roster_global_rule + '\n' + insert_anchor, 1)

    # Classification fills the persistent slot tables instead of growing the HUD handle arrays.
    old_class = (
        f'\t\t{g}.PemainManusia = Append To Array({g}.PemainManusia, Event Player);\n'
        f'\t\tDisable Nameplates(Event Player, Filtered Array({g}.PemainManusia, Player Variable(Current Array Element, InspeksiAktif) == True));\n\n'
        f'\t\t{g}.HudKiriPemain = Append To Array({g}.HudKiriPemain, 0);\n'
        f'\t\t{g}.HudKananPemain = Append To Array({g}.HudKananPemain, 0);\n'
        f'\t\t{g}.HudMenuPemain = Append To Array({g}.HudMenuPemain, 0);'
    )
    new_class = (
        f'\t\t{g}.PemainSlotHUD[Event Player.UrutanHUD] = Event Player;\n'
        f'\t\t{g}.NamaSlotHUD[Event Player.UrutanHUD] = Event Player.NamaTampilan;\n'
        f'\t\t{g}.PemainManusia = Append To Array({g}.PemainManusia, Event Player);\n'
        f'\t\tDisable Nameplates(Event Player, Filtered Array({g}.PemainManusia, Player Variable(Current Array Element, InspeksiAktif) == True));\n\n'
        f'\t\t{g}.HudMenuPemain = Append To Array({g}.HudMenuPemain, 0);'
    )
    text = replace_once(text, old_class, new_class, f'{path}: classifier slot ownership')

    # The Each Player rule only binds aliases to already-existing global handles.
    bind_rule = f'''{rule_kw}("02b - HUD Pemain: Hubungkan ke slot global")
{{
\t{event_kw}
\t{{
\t\tOngoing - Each Player;
\t\tAll;
\t\tAll;
\t}}

\t{conditions_kw}
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
\t\tCount Of({g}.HudKiriPemain) == 12;
\t\tCount Of({g}.HudKananPemain) == 12;
\t\tEvent Player.HudPemainDibuat == False;
\t}}

\t{actions_kw}
\t{{
\t\t"Baris roster sudah dimiliki slot global; player hanya menyimpan alias handle untuk kompatibilitas lifecycle."
\t\tEvent Player.HudKiri = {g}.HudKiriPemain[Event Player.UrutanHUD];
\t\tEvent Player.HudKanan = {g}.HudKananPemain[Event Player.UrutanHUD];
\t\tEvent Player.HudPemainDibuat = True;
\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Welcome to CHILL. Pick a vibe, pick a color, stay weird.") : Event Player.IndeksBahasa == 1 ? Custom String("Selamat datang di CHILL. Pilih vibe, pilih warna, tetap aneh.") : Custom String("ยินดีต้อนรับสู่ CHILL เลือกเพลง เลือกสี แล้วกวนแบบพอดี ๆ"));
\t}}
}}
'''
    text = replace_rule(text, rule_kw, '02b - HUD Pemain', '03c - Bot/Dummy', bind_rule, f'{path}: replace player roster renderer')

    # Team-switch replacement rebinds the existing global slot and restores the stable name from it.
    old_rebind = (
        f'\t\t\t\t{g}.PemainPengganti.UrutanHUD = {g}.SlotHUDPemain[{g}.IndeksKeluar];\n'
        f'\t\t\t\t{g}.PemainManusia[{g}.IndeksKeluar] = {g}.PemainPengganti;'
    )
    new_rebind = (
        f'\t\t\t\t{g}.PemainPengganti.UrutanHUD = {g}.SlotHUDPemain[{g}.IndeksKeluar];\n'
        f'\t\t\t\t{g}.PemainSlotHUD[{g}.PemainPengganti.UrutanHUD] = {g}.PemainPengganti;\n'
        f'\t\t\t\t{g}.PemainPengganti.NamaTampilan = {g}.NamaSlotHUD[{g}.PemainPengganti.UrutanHUD];\n'
        f'\t\t\t\t{g}.PemainManusia[{g}.IndeksKeluar] = {g}.PemainPengganti;'
    )
    text = replace_once(text, old_rebind, new_rebind, f'{path}: team replacement slot rebind')

    # Same-entity team changes also reassert slot ownership and restore the name from global storage.
    team_comment = '"Pemain terdaftar mempertahankan dua baris daftar yang sama saat berganti tim; hanya keadaan mesin sementara yang dinormalisasi."\n'
    team_insert = (
        team_comment
        + f'\t\t\tIf(And({g}.PemainAktif.UrutanHUD >= 0, {g}.PemainAktif.UrutanHUD < 12));\n'
        + f'\t\t\t\t{g}.PemainSlotHUD[{g}.PemainAktif.UrutanHUD] = {g}.PemainAktif;\n'
        + f'\t\t\t\tIf({g}.NamaSlotHUD[{g}.PemainAktif.UrutanHUD] != Custom String(""));\n'
        + f'\t\t\t\t\t{g}.PemainAktif.NamaTampilan = {g}.NamaSlotHUD[{g}.PemainAktif.UrutanHUD];\n'
        + f'\t\t\t\tEnd;\n'
        + f'\t\t\tEnd;\n'
    )
    text = replace_once(text, team_comment, team_insert, f'{path}: same entity slot repair')

    # If the cached player name disappears, prefer the persistent global slot name over the live player token.
    old_repair = (
        f'\t\tIf(And(Array Contains({g}.PemainManusia, {g}.PemainAktif) == True, And(Or({g}.PemainAktif.NamaTampilan == Null, {g}.PemainAktif.NamaTampilan == Custom String("")), Custom String("{{0}}", {g}.PemainAktif) != Custom String(""))));\n'
        f'\t\t\t{g}.PemainAktif.NamaTampilan = Evaluate Once(Custom String("{{0}}", {g}.PemainAktif));\n'
        f'\t\tEnd;'
    )
    new_repair = (
        f'\t\tIf(And(Array Contains({g}.PemainManusia, {g}.PemainAktif) == True, Or({g}.PemainAktif.NamaTampilan == Null, {g}.PemainAktif.NamaTampilan == Custom String(""))));\n'
        f'\t\t\tIf(And({g}.PemainAktif.UrutanHUD >= 0, And({g}.PemainAktif.UrutanHUD < 12, {g}.NamaSlotHUD[{g}.PemainAktif.UrutanHUD] != Custom String(""))));\n'
        f'\t\t\t\t{g}.PemainAktif.NamaTampilan = {g}.NamaSlotHUD[{g}.PemainAktif.UrutanHUD];\n'
        f'\t\t\tElse If(Custom String("{{0}}", {g}.PemainAktif) != Custom String(""));\n'
        f'\t\t\t\t{g}.PemainAktif.NamaTampilan = Evaluate Once(Custom String("{{0}}", {g}.PemainAktif));\n'
        f'\t\t\tEnd;\n'
        f'\t\tEnd;'
    )
    text = replace_once(text, old_repair, new_repair, f'{path}: fast stable name repair')

    # Crouch inspection and Crouch teleport read the persistent slot name for humans.
    old_inspect_name = 'Player Variable(Event Player.TargetInspeksi, Manusia) == True ? Player Variable(Event Player.TargetInspeksi, NamaTampilan) : Custom String("{0}", Event Player.TargetInspeksi)'
    new_inspect_name = f'Player Variable(Event Player.TargetInspeksi, Manusia) == True ? {g}.NamaSlotHUD[Player Variable(Event Player.TargetInspeksi, UrutanHUD)] : Custom String("{{0}}", Event Player.TargetInspeksi)'
    text = replace_once(text, old_inspect_name, new_inspect_name, f'{path}: crouch inspect stable name')

    old_tele_name = 'Player Variable(Event Player.CalonTargetTeleportasi, Manusia) == True ? Player Variable(Event Player.CalonTargetTeleportasi, NamaTampilan) : Custom String("{0}", Event Player.CalonTargetTeleportasi)'
    new_tele_name = f'Player Variable(Event Player.CalonTargetTeleportasi, Manusia) == True ? {g}.NamaSlotHUD[Player Variable(Event Player.CalonTargetTeleportasi, UrutanHUD)] : Custom String("{{0}}", Event Player.CalonTargetTeleportasi)'
    text = replace_once(text, old_tele_name, new_tele_name, f'{path}: crouch teleport stable name')

    # Real leave clears the slot payload but never destroys/removes the permanent roster HUD handles.
    old_cleanup_destroy = (
        f'\t\t\tIf({g}.HudKiriPemain[{g}.IndeksPembersihan] != 0);\n'
        f'\t\t\t\tDestroy HUD Text({g}.HudKiriPemain[{g}.IndeksPembersihan]);\n'
        f'\t\t\tEnd;\n'
        f'\t\t\tIf({g}.HudKananPemain[{g}.IndeksPembersihan] != 0);\n'
        f'\t\t\t\tDestroy HUD Text({g}.HudKananPemain[{g}.IndeksPembersihan]);\n'
        f'\t\t\tEnd;\n'
    )
    text = replace_once(text, old_cleanup_destroy, '', f'{path}: cleanup persistent row destroy')

    old_cleanup_arrays = (
        f'\t\t\t{g}.SlotHUDTersedia = Sorted Array(Append To Array({g}.SlotHUDTersedia, {g}.IndeksUtangKeluar), Current Array Element);\n'
        f'\t\t\tModify Global Variable(HudKiriPemain, Remove From Array By Index, {g}.IndeksPembersihan);\n'
        f'\t\t\tModify Global Variable(HudKananPemain, Remove From Array By Index, {g}.IndeksPembersihan);'
    )
    new_cleanup_arrays = (
        f'\t\t\t{g}.PemainSlotHUD[{g}.IndeksUtangKeluar] = Null;\n'
        f'\t\t\t{g}.NamaSlotHUD[{g}.IndeksUtangKeluar] = Custom String("");\n'
        f'\t\t\t{g}.SlotHUDTersedia = Sorted Array(Append To Array({g}.SlotHUDTersedia, {g}.IndeksUtangKeluar), Current Array Element);'
    )
    text = replace_once(text, old_cleanup_arrays, new_cleanup_arrays, f'{path}: cleanup persistent slot payload')

    path.write_text(text, encoding='utf-8')

# Add a focused runtime contract. Validator-specific tests will be aligned after the first staging run.
runtime_path = Path('tests/test_runtime_maintenance.py')
runtime = runtime_path.read_text(encoding='utf-8')
marker = '    def test_registered_team_switch_never_destroys_roster_or_hides_crouch_target(self):\n'
if marker not in runtime:
    raise SystemExit('runtime insertion marker missing')
new_test = '''    def test_roster_is_owned_by_persistent_global_hud_slots(self):
        for source, global_name, rule_kw in ((self.it, "Globale", "regola"), (self.en, "Global", "rule")):
            self.assertIn("63: PemainSlotHUD", source)
            self.assertIn("64: NamaSlotHUD", source)
            self.assertIn(f"{global_name}.PemainSlotHUD = Array(Null, Null, Null, Null, Null, Null, Null, Null, Null, Null, Null, Null);", source)
            self.assertIn(f'{rule_kw}("00b - HUD Roster: Dua belas slot global permanen")', source)
            global_rows = source.split(f'{rule_kw}("00b - HUD Roster: Dua belas slot global permanen")', 1)[1].split(f'{rule_kw}("00a1 - Umum:', 1)[0]
            self.assertIn("Ongoing - Global;", global_rows)
            self.assertIn("For Global Variable(IndeksPemilih, 0, 12, 1);", global_rows)
            self.assertEqual(global_rows.count("Create HUD Text("), 2)
            self.assertIn(f"{global_name}.PemainSlotHUD[Evaluate Once({global_name}.IndeksPemilih)]", global_rows)
            self.assertIn(f"{global_name}.NamaSlotHUD[Evaluate Once({global_name}.IndeksPemilih)]", global_rows)

            player_bind = source.split(f'{rule_kw}("02b - HUD Pemain: Hubungkan ke slot global")', 1)[1].split(f'{rule_kw}("03c - Bot/Dummy', 1)[0]
            self.assertNotIn("Create HUD Text(", player_bind)
            self.assertIn(f"Event Player.HudKiri = {global_name}.HudKiriPemain[Event Player.UrutanHUD];", player_bind)
            self.assertIn(f"Event Player.HudKanan = {global_name}.HudKananPemain[Event Player.UrutanHUD];", player_bind)

            self.assertIn(f"{global_name}.PemainSlotHUD[Event Player.UrutanHUD] = Event Player;", source)
            self.assertIn(f"{global_name}.NamaSlotHUD[Event Player.UrutanHUD] = Event Player.NamaTampilan;", source)
            self.assertNotIn("Modify Global Variable(HudKiriPemain, Remove From Array By Index", source)
            self.assertNotIn("Modify Global Variable(HudKananPemain, Remove From Array By Index", source)
            self.assertIn(f"{global_name}.PemainSlotHUD[{global_name}.IndeksUtangKeluar] = Null;", source)
            self.assertIn(f"{global_name}.NamaSlotHUD[{global_name}.IndeksUtangKeluar] = Custom String(\"\");", source)
            self.assertIn(f"{global_name}.PemainSlotHUD[{global_name}.PemainPengganti.UrutanHUD] = {global_name}.PemainPengganti;", source)
            self.assertIn(f"{global_name}.PemainPengganti.NamaTampilan = {global_name}.NamaSlotHUD[{global_name}.PemainPengganti.UrutanHUD];", source)
            self.assertIn(f"{global_name}.NamaSlotHUD[Player Variable(Event Player.TargetInspeksi, UrutanHUD)]", source)
            self.assertIn(f"{global_name}.NamaSlotHUD[Player Variable(Event Player.CalonTargetTeleportasi, UrutanHUD)]", source)

'''
if 'def test_roster_is_owned_by_persistent_global_hud_slots' not in runtime:
    runtime = runtime.replace(marker, new_test + marker, 1)
runtime_path.write_text(runtime, encoding='utf-8')
