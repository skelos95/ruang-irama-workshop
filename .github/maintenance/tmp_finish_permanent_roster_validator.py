from pathlib import Path

path = Path('tools/validate_workshop.py')
text = path.read_text(encoding='utf-8')


def replace_once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected 1, found {count}')
    text = text.replace(old, new, 1)

# Special soundtrack roster: renderer now lives inside global initialization.
old = '''    roster_rule = next(
        (
            rule for rule in rules
            if event_type(rule) == "Ongoing - Each Player"
                and "Global.PemainSlotHUD[Evaluate Once(Event Player.UrutanHUD)]" in rule.body
            and "MusikKhusus" in rule.body
        ),
        None,
    )
'''
new = '''    roster_rule = next(
        (
            rule for rule in rules
            if event_type(rule) == "Ongoing - Global"
            and "For Global Variable(IndeksPemilih, 0, 12, 1);" in rule.body
            and "Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)]" in rule.body
            and "MusikKhusus" in rule.body
        ),
        None,
    )
'''
replace_once(old, new, 'special soundtrack global renderer detector')
replace_once(
'''        right_calls = [
            call for call in iter_calls(roster_rule.body, "Create HUD Text")
            if len(call.args) >= 5 and call.args[4].strip() == "Right"
        ]
''',
'''        right_calls = [
            call for call in iter_calls(roster_rule.body, "Create HUD Text")
            if len(call.args) >= 5
            and call.args[4].strip() == "Right"
            and "Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)]" in call.raw
        ]
''',
'special soundtrack right roster call',
)
replace_once(
'            slot = "Global.PemainSlotHUD[Evaluate Once(Event Player.UrutanHUD)]"\n',
'            slot = "Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)]"\n',
'special soundtrack slot expression',
)

# Post-team rule is now a pure binder. Name visibility and HUD creation are owned
# by the permanent global renderer, not this player lifecycle rule.
old_identity = '''        for token in (
            'Global.NamaSlotHUD[Event Player.UrutanHUD] != Custom String("");',
        ):
            checks.require(token in roster_conditions,
                           f"renderer roster lazy senza identità globale: {token}")
'''
replace_once(old_identity, '', 'remove lazy name condition')

old_lazy = '''        checks.require(
            "Or(Global.HudKiriPemain[Event Player.UrutanHUD] == 0, Global.HudKiriPemain[Event Player.UrutanHUD] == Null)" in roster_hud.body
            and "Or(Global.HudKananPemain[Event Player.UrutanHUD] == 0, Global.HudKananPemain[Event Player.UrutanHUD] == Null)" in roster_hud.body,
            "renderer roster lazy deve creare soltanto handle slot ancora vuoti",
        )
'''
new_lazy = '''        checks.require(
            "Create HUD Text(" not in roster_hud.body
            and "Global.HudKiriPemain[Event Player.UrutanHUD]" in roster_hud.body
            and "Global.HudKananPemain[Event Player.UrutanHUD]" in roster_hud.body,
            "binder roster permanente deve soltanto collegare i due handle globali",
        )
'''
replace_once(old_lazy, new_lazy, 'replace lazy handle creation check')

old_order = '''        ready_order = tuple(
            roster_hud.body.find(token)
            for token in (
                "Global.HudKiriPemain[Event Player.UrutanHUD] = Last Text ID;",
                "Global.HudKananPemain[Event Player.UrutanHUD] = Last Text ID;",
                "Event Player.HudKiri = Global.HudKiriPemain[Event Player.UrutanHUD];",
                "Event Player.HudKanan = Global.HudKananPemain[Event Player.UrutanHUD];",
                ready,
            )
        )
'''
new_order = '''        ready_order = tuple(
            roster_hud.body.find(token)
            for token in (
                "Event Player.HudKiri = Global.HudKiriPemain[Event Player.UrutanHUD];",
                "Event Player.HudKanan = Global.HudKananPemain[Event Player.UrutanHUD];",
                ready,
            )
        )
'''
replace_once(old_order, new_order, 'binder ready ordering')

# Bot-isolation entrypoint identifies the binder rather than the removed lazy renderer.
old_entry = '        (next((rule for rule in rules if event_type(rule) == "Ongoing - Each Player" and "HudPemainDibuat" in rule.body and "Global.HudKiriPemain[Event Player.UrutanHUD] = Last Text ID;" in rule.body and "Global.HudKananPemain[Event Player.UrutanHUD] = Last Text ID;" in rule.body), None), "HUD player", True),\n'
new_entry = '        (next((rule for rule in rules if event_type(rule) == "Ongoing - Each Player" and "HudPemainDibuat" in rule.body and "Event Player.HudKiri = Global.HudKiriPemain[Event Player.UrutanHUD];" in rule.body and "Event Player.HudKanan = Global.HudKananPemain[Event Player.UrutanHUD];" in rule.body and "Create HUD Text(" not in rule.body), None), "HUD player", True),\n'
replace_once(old_entry, new_entry, 'HUD player entrypoint detector')

path.write_text(text, encoding='utf-8')
