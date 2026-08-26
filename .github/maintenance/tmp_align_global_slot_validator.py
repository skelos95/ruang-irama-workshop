from pathlib import Path

# Make the per-player compatibility aliases meaningful reads: the ready flag is
# true only when both permanent global handles for that slot exist.
for path in (Path('workshop/ruang_irama.it-IT.workshop'), Path('tests/fixtures/semantic_reference.txt')):
    text = path.read_text(encoding='utf-8')
    old = '\t\tEvent Player.HudPemainDibuat = True;\n\t\tSmall Message(Event Player,'
    new = '\t\tEvent Player.HudPemainDibuat = And(Event Player.HudKiri != Null, Event Player.HudKanan != Null);\n\t\tSmall Message(Event Player,'
    if text.count(old) != 1:
        raise SystemExit(f'{path}: expected one global-slot ready assignment, found {text.count(old)}')
    path.write_text(text.replace(old, new, 1), encoding='utf-8')

path = Path('tools/validate_workshop.py')
text = path.read_text(encoding='utf-8')

# Add explicit architectural checks. These replace the old assumption that an
# Each Player rule owns and recreates its two roster rows.
needle = 'def validate_hud_and_menu(checks: Checks, source: str, rules: list[Rule], players: set[str], subroutines: set[str]) -> None:\n'
if text.count(needle) != 1:
    raise SystemExit('validate_hud_and_menu definition not found exactly once')
insert = r'''def validate_hud_and_menu(checks: Checks, source: str, rules: list[Rule], players: set[str], subroutines: set[str]) -> None:
    global_slot_roster = next(
        (
            rule for rule in rules
            if event_type(rule) == "Ongoing - Global"
            and "Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)]" in rule.body
            and "Global.NamaSlotHUD[Evaluate Once(Global.IndeksPemilih)]" in rule.body
            and "For Global Variable(IndeksPemilih, 0, 12, 1);" in rule.body
        ),
        None,
    )
    checks.require(global_slot_roster is not None,
                   "renderer roster globale persistente a 12 slot assente")
    if global_slot_roster:
        slot_calls = list(iter_calls(global_slot_roster.body, "Create HUD Text"))
        checks.equal(len(slot_calls), 2,
                     "renderer roster globale deve avere esattamente due Create HUD nel loop")
        expected_orders = {
            "Left": "1 + Evaluate Once(Global.IndeksPemilih)",
            "Right": "-13 + Evaluate Once(Global.IndeksPemilih)",
        }
        for side, order in expected_orders.items():
            calls = [call for call in slot_calls if len(call.args) >= 6 and call.args[4].strip() == side]
            checks.equal(len(calls), 1, f"renderer roster globale {side}")
            if calls:
                checks.equal(calls[0].args[0].strip(), "Global.PemainManusia",
                             f"renderer roster globale {side}: pubblico umano dinamico")
                checks.equal(calls[0].args[5].strip(), order,
                             f"renderer roster globale {side}: ordinamento per slot congelato")
                checks.require(
                    "Global.NamaSlotHUD[Evaluate Once(Global.IndeksPemilih)]" in calls[0].raw,
                    f"renderer roster globale {side}: nome non posseduto dallo slot",
                )
                checks.require(
                    "Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)]" in calls[0].raw,
                    f"renderer roster globale {side}: occupante non letto dallo slot",
                )
        checks.require(
            "Player Variable(Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)], WarnaNama)"
            in global_slot_roster.body,
            "renderer roster globale non segue Name Color dell'occupante corrente",
        )
        checks.require(
            "Player Variable(Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)], MusikKhusus)"
            in global_slot_roster.body,
            "renderer roster globale non conserva il profilo musicale speciale",
        )

    checks.require(
        "Global.PemainSlotHUD = Array(Null, Null, Null, Null, Null, Null, Null, Null, Null, Null, Null, Null);"
        in source,
        "tabella globale PemainSlotHUD non inizializzata a 12 slot",
    )
    checks.require(
        source.count('Custom String("")') >= 12
        and "Global.NamaSlotHUD = Array(" in source,
        "tabella globale NamaSlotHUD non inizializzata",
    )
    for token, label in (
        ("Global.PemainSlotHUD[Event Player.UrutanHUD] = Event Player;", "classificazione occupante slot"),
        ("Global.NamaSlotHUD[Event Player.UrutanHUD] = Event Player.NamaTampilan;", "classificazione nome slot"),
        ("Global.PemainSlotHUD[Global.PemainPengganti.UrutanHUD] = Global.PemainPengganti;", "rebind entità dopo cambio team"),
        ("Global.PemainPengganti.NamaTampilan = Global.NamaSlotHUD[Global.PemainPengganti.UrutanHUD];", "ripristino nome dopo cambio team"),
        ("Global.PemainSlotHUD[Global.PemainAktif.UrutanHUD] = Global.PemainAktif;", "rebind same-entity cambio team"),
        ("Global.PemainSlotHUD[Global.IndeksUtangKeluar] = Null;", "pulizia occupante al vero leave"),
        ('Global.NamaSlotHUD[Global.IndeksUtangKeluar] = Custom String("");', "pulizia nome al vero leave"),
        ("Global.NamaSlotHUD[Player Variable(Event Player.TargetInspeksi, UrutanHUD)]", "nome Crouch Inspection da slot"),
        ("Global.NamaSlotHUD[Player Variable(Event Player.CalonTargetTeleportasi, UrutanHUD)]", "nome Crouch Teleport da slot"),
    ):
        checks.require(token in source, f"roster globale persistente: {label} assente")

    for forbidden, label in (
        ("Destroy HUD Text(Global.HudKiriPemain[", "destroy righe Left permanenti"),
        ("Destroy HUD Text(Global.HudKananPemain[", "destroy righe Right permanenti"),
        ("Modify Global Variable(HudKiriPemain, Remove From Array By Index", "rimozione handle Left permanenti"),
        ("Modify Global Variable(HudKananPemain, Remove From Array By Index", "rimozione handle Right permanenti"),
        ("Event Player.HudKiri = Last Text ID;", "ownership roster Left per-player"),
        ("Event Player.HudKanan = Last Text ID;", "ownership roster Right per-player"),
    ):
        checks.require(forbidden not in source, f"roster globale persistente vieta {label}")
'''
text = text.replace(needle, insert, 1)

# Old renderer blocks remain useful for legacy files but must not reject the new
# architecture. Their detailed branches stay skipped because roster_rule is None.
old = '    checks.require(roster_rule is not None, "renderer HUD roster umano assente")\n'
new = '    checks.require(roster_rule is not None or global_slot_roster is not None, "renderer HUD roster umano/globale assente")\n'
if text.count(old) != 1:
    raise SystemExit(f'base roster require count {text.count(old)}')
text = text.replace(old, new, 1)

old = '    checks.require(roster_rule is not None, "profilo speciale: renderer roster assente")\n'
new = '''    checks.require(
        roster_rule is not None
        or any(event_type(rule) == "Ongoing - Global" and "Global.PemainSlotHUD[Evaluate Once(Global.IndeksPemilih)]" in rule.body and "MusikKhusus" in rule.body for rule in rules),
        "profilo speciale: renderer roster globale assente",
    )
'''
if text.count(old) != 1:
    raise SystemExit(f'special roster require count {text.count(old)}')
text = text.replace(old, new, 1)

old = '    checks.require(roster_hud is not None, "renderer roster post-team-switch assente")\n'
new = '''    checks.require(
        roster_hud is not None
        or any(event_type(rule) == "Ongoing - Global" and "Global.NamaSlotHUD[Evaluate Once(Global.IndeksPemilih)]" in rule.body for rule in rules),
        "renderer roster persistente post-team-switch assente",
    )
'''
if text.count(old) != 1:
    raise SystemExit(f'post-team roster require count {text.count(old)}')
text = text.replace(old, new, 1)

old = '        (next((rule for rule in rules if event_type(rule) == "Ongoing - Each Player" and "HudPemainDibuat" in rule.body and "Create HUD Text(" in rule.body), None), "HUD player", True),\n'
new = '        (next((rule for rule in rules if event_type(rule) == "Ongoing - Each Player" and "HudPemainDibuat" in rule.body and "Global.HudKiriPemain[Event Player.UrutanHUD]" in rule.body and "Create HUD Text(" not in rule.body), None), "HUD player", True),\n'
if text.count(old) != 1:
    raise SystemExit(f'entrypoint HUD player count {text.count(old)}')
text = text.replace(old, new, 1)

path.write_text(text, encoding='utf-8')
