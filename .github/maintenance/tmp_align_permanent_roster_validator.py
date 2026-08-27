from pathlib import Path


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1, found {count}')
    return text.replace(old, new, 1)


# Source/mirror cleanup: keep roster visible only to registered humans, keep the
# pending flag as a non-blocking normalization read, and match the ready alias
# contract already used by the validator.
for path, g in ((Path('workshop/ruang_irama.it-IT.workshop'), 'Globale'), (Path('tests/fixtures/semantic_reference.txt'), 'Global')):
    text = path.read_text(encoding='utf-8')
    old_visible = 'Create HUD Text(All Players(All Teams),'
    if text.count(old_visible) != 2:
        raise SystemExit(f'{path}: expected exactly two permanent roster All Players calls, found {text.count(old_visible)}')
    text = text.replace(old_visible, f'Create HUD Text({g}.PemainManusia,')

    old_ready = 'Event Player.HudPemainDibuat = And(And(Event Player.HudKiri != 0, Event Player.HudKiri != Null), And(Event Player.HudKanan != 0, Event Player.HudKanan != Null));'
    new_ready = 'Event Player.HudPemainDibuat = And(And(Event Player.HudKiri != Null, Event Player.HudKiri != 0), And(Event Player.HudKanan != Null, Event Player.HudKanan != 0));'
    text = replace_once(text, old_ready, new_ready, f'{path}: ready alias order')

    old_pending = '\t\tEvent Player.SegarkanRosterTertunda = False;\n\t}\n}\n\n'
    new_pending = '\t\tIf(Event Player.SegarkanRosterTertunda == True);\n\t\t\tEvent Player.SegarkanRosterTertunda = False;\n\t\tEnd;\n\t}\n}\n\n'
    # Restrict replacement to 02b to avoid touching setup initialization.
    s = text.index(('regola' if g == 'Globale' else 'rule') + '("02b - HUD Pemain: Hubungkan ke roster global permanen")')
    e = text.index(('regola' if g == 'Globale' else 'rule') + '("03c - Bot/Dummy', s)
    block = text[s:e]
    if old_pending not in block:
        raise SystemExit(f'{path}: 02b pending normalization not found')
    block = block.replace(old_pending, new_pending, 1)
    text = text[:s] + block + text[e:]
    path.write_text(text, encoding='utf-8')

# Focused runtime tests: permanent rows use the same dynamic human audience as
# the always-working global headers.
runtime = Path('tests/test_runtime_maintenance.py')
r = runtime.read_text(encoding='utf-8')
r = r.replace('self.assertIn("Create HUD Text(All Players(All Teams),", init)', 'self.assertIn(f"Create HUD Text({g}.PemainManusia,", init)')
runtime.write_text(r, encoding='utf-8')

path = Path('tools/validate_workshop.py')
text = path.read_text(encoding='utf-8')

old_detect = '''    global_slot_roster = next(
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
'''
new_detect = '''    global_slot_roster = next(
        (
            rule for rule in rules
            if event_type(rule) == "Ongoing - Global"
            and "For Global Variable(IndeksPemilih, 0, 12, 1);" in rule.body
            and "Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)]" in rule.body
            and "Global.NamaSlotHUD[Evaluate Once(Global.IndeksPemilih)]" in rule.body
            and "Global.HudKiriPemain[Global.IndeksPemilih] = Last Text ID;" in rule.body
            and "Global.HudKananPemain[Global.IndeksPemilih] = Last Text ID;" in rule.body
        ),
        None,
    )
'''
text = replace_once(text, old_detect, new_detect, 'global roster detector')
text = replace_once(
    text,
    '        slot_calls = list(iter_calls(global_slot_roster.body, "Create HUD Text"))\n',
    '        slot_calls = [call for call in iter_calls(global_slot_roster.body, "Create HUD Text") if "Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)]" in call.raw]\n',
    'global roster call filter',
)

# Only the renderer-validation prefix changes from Event Player slot ownership to
# Global.IndeksPemilih ownership. Leave the later player alias checks untouched.
hud_start = text.index('def validate_hud_and_menu(')
hud_binding = text.index('    global_slot_binding = next(', hud_start)
prefix = text[hud_start:hud_binding]
prefix = prefix.replace('Evaluate Once(Event Player.UrutanHUD)', 'Evaluate Once(Global.IndeksPemilih)')
prefix = prefix.replace('"Left": "1 + Evaluate Once(Global.IndeksPemilih)"', '"Left": "1 + Evaluate Once(Global.IndeksPemilih)"')
prefix = prefix.replace('"Right": "-13 + Evaluate Once(Global.IndeksPemilih)"', '"Right": "-13 + Evaluate Once(Global.IndeksPemilih)"')
prefix = prefix.replace(
    '("Global.PemainSlotHUD[Global.PemainPengganti.UrutanHUD] = Global.PemainPengganti;", "rebind entità dopo cambio team"),',
    '("Global.PemainManusia[Global.IndeksKeluar] = Event Player;", "rebind entità immediato dopo cambio team"),',
)
prefix = prefix.replace(
    '("Global.PemainPengganti.NamaTampilan = Global.NamaSlotHUD[Global.PemainPengganti.UrutanHUD];", "ripristino nome dopo cambio team"),',
    '("Event Player.UrutanHUD = Index Of Array Value(Global.NamaSlotHUD, Event Player.NamaTampilan);", "adozione slot persistente dopo cambio team"),',
)
prefix = prefix.replace(
    '        (\'Global.NamaSlotHUD[Global.IndeksUtangKeluar] = Custom String("");\', "pulizia nome al vero leave"),\n',
    '',
)
text = text[:hud_start] + prefix + text[hud_binding:]

old_destroy = '''    checks.equal(source.count("Destroy HUD Text(Global.HudKiriPemain["), 1,
                 "solo il vero leave può distruggere una riga roster Left")
    checks.equal(source.count("Destroy HUD Text(Global.HudKananPemain["), 1,
                 "solo il vero leave può distruggere una riga roster Right")
    for token, label in (
        ("Global.HudKiriPemain[Global.IndeksUtangKeluar] = 0;", "reset handle Left al vero leave"),
        ("Global.HudKananPemain[Global.IndeksUtangKeluar] = 0;", "reset handle Right al vero leave"),
    ):
        checks.require(token in source, f"roster globale lazy: {label} assente")
'''
new_destroy = '''    checks.equal(source.count("Destroy HUD Text(Global.HudKiriPemain["), 0,
                 "roster globale permanente non deve distruggere righe Left")
    checks.equal(source.count("Destroy HUD Text(Global.HudKananPemain["), 0,
                 "roster globale permanente non deve distruggere righe Right")
    for token, label in (
        ("Global.HudKiriPemain[Global.IndeksUtangKeluar] = 0;", "reset handle Left al vero leave"),
        ("Global.HudKananPemain[Global.IndeksUtangKeluar] = 0;", "reset handle Right al vero leave"),
        ('Global.NamaSlotHUD[Global.IndeksUtangKeluar] = Custom String("");', "cancellazione identità riservata al vero leave"),
        ("Append To Array(Global.SlotHUDTersedia, Global.IndeksUtangKeluar)", "riciclo slot prima del restart"),
    ):
        checks.require(token not in source, f"roster globale permanente vieta {label}")
'''
text = replace_once(text, old_destroy, new_destroy, 'permanent cleanup contract')
text = replace_once(text, 'checks.equal(len(init_hud_calls), 10, "numero HUD fissi nella regola iniziale")', 'checks.equal(len(init_hud_calls), 12, "dieci HUD fissi più due renderer roster permanenti nella regola iniziale")', 'init HUD count')

# Special-profile ownership no longer includes the delayed Player Left copier.
text = replace_once(text, 'checks.equal(len(property_writers), 4, "profilo speciale: numero writer property MusikKhusus")', 'checks.equal(len(property_writers), 3, "profilo speciale: numero writer property MusikKhusus")', 'MusikKhusus writer count')
text = replace_once(
    text,
    '== Counter({"Event Player": 2, "Global.PemainAktif": 1, "Global.PemainPengganti": 1}),',
    '== Counter({"Event Player": 2, "Global.PemainAktif": 1}),',
    'MusikKhusus writer ownership',
)

# Lifecycle validator: replacement is performed by classifier immediately, not by
# the stale Player Left event after its grace period.
needle = '    joined = rules_with_event(rules, "Player Joined Match")\n    left = rules_with_event(rules, "Player Left Match")\n'
insert = needle + '''    classifier = next((rule for rule in rules if event_type(rule) == "Ongoing - Each Player" and "Event Player.NamaTampilan = Evaluate Once(Custom String(\"{0}\", Event Player));" in rule.body and "Global.NamaSlotHUD" in rule.body), None)
'''
text = replace_once(text, needle, insert, 'lifecycle classifier lookup')
text = text.replace(
    'checks.require("Global.PemainManusia[Global.IndeksKeluar] = Global.PemainPengganti;" in body,\n                       "team-switch non sostituisce il riferimento entità nel medesimo slot roster")',
    'checks.require(classifier is not None and "Global.PemainManusia[Global.IndeksKeluar] = Event Player;" in classifier.body,\n                       "team-switch non sostituisce immediatamente il riferimento entità nel medesimo slot roster")',
)
text = text.replace(
    'checks.require("Global.PemainPengganti.UrutanHUD = Global.SlotHUDPemain[Global.IndeksKeluar];" in body,\n                       "team-switch non conserva lo slot HUD del profilo")',
    'checks.require(classifier is not None and "Event Player.UrutanHUD = Index Of Array Value(Global.NamaSlotHUD, Event Player.NamaTampilan);" in classifier.body,\n                       "team-switch non riadotta lo slot HUD persistente")',
)
old_vote = '''        checks.require("Global.PemainPengganti.PemainDipilih = Event Player.PemainDipilih;" in body
                       and "Global.PemainManusia[Global.IndeksPemilih].PemainDipilih = Global.PemainPengganti;" in body
                       and "Call Subroutine(HitungPilihan);" in body,
                       "team-switch non migra voto e riferimenti sociali sulla nuova entità")
'''
new_vote = '''        checks.require(classifier is not None
                       and "Global.PemainManusia[Global.IndeksPemilih].PemainDipilih == Global.PemainPengganti" in classifier.body
                       and "Global.PemainManusia[Global.IndeksPemilih].PemainDipilih = Event Player;" in classifier.body
                       and "Call Subroutine(HitungPilihan);" in classifier.body,
                       "team-switch non migra voto e riferimenti sociali sulla nuova entità")
'''
text = replace_once(text, old_vote, new_vote, 'team-switch vote migration')

old_slot_anchor = 'slot_anchor = classifier.body.find("If(Count Of(Global.SlotHUDTersedia) == 0);")'
new_slot_anchor = 'slot_anchor = classifier.body.find("If(And(Count Of(Global.SlotHUDTersedia) == 0, Index Of Array Value(Global.NamaSlotHUD, Evaluate Once(Custom String(\\\"{0}\\\", Event Player))) < 0));")'
text = replace_once(text, old_slot_anchor, new_slot_anchor, 'reserve-aware slot anchor')

# Post-team renderer is now the binding rule; creation lives globally.
text = text.replace('        and "Global.HudKiriPemain[Event Player.UrutanHUD] = Last Text ID;" in rule.body\n', '')
text = text.replace('        and "Global.HudKananPemain[Event Player.UrutanHUD] = Last Text ID;" in rule.body\n', '')

path.write_text(text, encoding='utf-8')
