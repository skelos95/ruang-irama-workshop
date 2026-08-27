from pathlib import Path

# Keep SegarkanRosterTertunda as a legacy normalization flag, but do not let it
# gate whether the roster exists. Reading/clearing it in the binder prevents a
# stale per-player value from leaking forward after team transitions.
for path, rule_kw in ((Path('workshop/ruang_irama.it-IT.workshop'), 'regola'), (Path('tests/fixtures/semantic_reference.txt'), 'rule')):
    text = path.read_text(encoding='utf-8')
    start = text.index(f'{rule_kw}("02b - HUD Pemain: Hubungkan ke slot global")')
    end = text.index(f'{rule_kw}("03c - Bot/Dummy', start)
    rule = text[start:end]
    anchor = '\t\t"Buat pasangan HUD hanya setelah slot berisi identitas valid. Setelah dibuat, pasangan tetap hidup selama pindah tim dan hanya dihancurkan saat benar-benar keluar."\n'
    insert = anchor + '\t\tIf(Event Player.SegarkanRosterTertunda == True);\n\t\t\tEvent Player.SegarkanRosterTertunda = False;\n\t\tEnd;\n'
    if rule.count(anchor) != 1:
        raise SystemExit(f'{path}: roster action anchor count {rule.count(anchor)}')
    rule = rule.replace(anchor, insert, 1)
    path.write_text(text[:start] + rule + text[end:], encoding='utf-8')

vp = Path('tools/validate_workshop.py')
v = vp.read_text(encoding='utf-8')
old = '''        for token in (
            "Has Spawned(Event Player) == True;",
            "Event Player.TimTerakhir == Team Of(Event Player);",
            "Event Player.SegarkanRosterTertunda == False;",
        ):
            checks.require(token in roster_conditions, f"renderer roster senza guardia stabile: {token}")
        for token in (
            "Event Player.NamaTampilan != Null;",
            'Event Player.NamaTampilan != Custom String("");',
            "Event Player.UrutanHUD >= 0;",
            "Global.PemainSlotHUD[Event Player.UrutanHUD] == Event Player;",
        ):
            checks.require(token in roster_conditions,
                           f"renderer roster lazy senza guardia identità: {token}")
'''
new = '''        for token in (
            "Event Player.UrutanHUD >= 0;",
            "Event Player.UrutanHUD < 12;",
            "Global.PemainSlotHUD[Event Player.UrutanHUD] == Event Player;",
        ):
            checks.require(token in roster_conditions, f"renderer roster senza guardia slot stabile: {token}")
        for token in (
            'Global.NamaSlotHUD[Event Player.UrutanHUD] != Custom String("");',
        ):
            checks.require(token in roster_conditions,
                           f"renderer roster lazy senza identità globale: {token}")
        for forbidden in (
            "Has Spawned(Event Player) == True;",
            "Event Player.TimTerakhir == Team Of(Event Player);",
            "Event Player.SegarkanRosterTertunda == False;",
            "Event Player.NamaTampilan != Null;",
            'Event Player.NamaTampilan != Custom String("");',
        ):
            checks.require(forbidden not in roster_conditions,
                           f"renderer roster non deve dipendere da stato player transitorio: {forbidden}")
'''
if v.count(old) != 1:
    raise SystemExit(f'validator roster guard block count {v.count(old)}')
v = v.replace(old, new, 1)
vp.write_text(v, encoding='utf-8')
