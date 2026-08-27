from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 occurrence, found {count}")
    return text.replace(old, new, 1)


path = Path("tools/validate_workshop.py")
text = path.read_text(encoding="utf-8")

# 1) Special-profile roster validation: the Player Vibes row now lives in the lazy
# per-player binder but reads the globally owned slot payload.
profile_start = text.index("def validate_special_player_profile")
start = text.index("    roster_rule = next(\n", profile_start)
end = text.index('    main_menu = rule_by_subroutine(rules, "GambarUtama")', start)
profile_block = '''    roster_rule = next(
        (
            rule for rule in rules
            if event_type(rule) == "Ongoing - Each Player"
            and "Global.HudKananPemain[Event Player.UrutanHUD] = Last Text ID;" in rule.body
            and "Global.PemainSlotHUD[Evaluate Once(Event Player.UrutanHUD)]" in rule.body
            and "MusikKhusus" in rule.body
        ),
        None,
    )
    checks.require(roster_rule is not None, "profilo speciale: renderer roster globale assente")
    if roster_rule:
        right_calls = [
            call for call in iter_calls(roster_rule.body, "Create HUD Text")
            if len(call.args) >= 5 and call.args[4].strip() == "Right"
        ]
        checks.equal(len(right_calls), 1, "profilo speciale: renderer roster Right")
        if right_calls:
            slot = "Global.PemainSlotHUD[Evaluate Once(Event Player.UrutanHUD)]"
            special_music = (
                f"Player Variable({slot}, MusikKhusus) != Null ? "
                f"Player Variable({slot}, MusikKhusus) : Player Variable({slot}, IndeksGenre)"
            )
            checks.require(
                special_music in right_calls[0].args[2],
                "profilo speciale roster globale: condizione profilo speciale",
            )
            for fallback in ("no soundtrack yet", "belum pilih musik", "ยังไม่ได้เลือกเพลง"):
                checks.require(
                    fallback in right_calls[0].args[2],
                    f"profilo speciale roster: fallback localizzato invariato: {fallback}",
                )

'''
text = text[:start] + profile_block + text[end:]

# 2) Lifecycle validation: the renderer creates a pair lazily once identity is valid,
# then aliases those globally owned handles. Team switches reuse them.
lifecycle_start = text.index("def validate_lifecycle")
start = text.index("    roster_hud = next((\n", lifecycle_start)
end = text.index("    cleanup_worker = next((\n", start)
lifecycle_block = '''    roster_hud = next((
        rule for rule in rules
        if event_type(rule) == "Ongoing - Each Player"
        and "Global.HudKiriPemain[Event Player.UrutanHUD] = Last Text ID;" in rule.body
        and "Global.HudKananPemain[Event Player.UrutanHUD] = Last Text ID;" in rule.body
        and "Event Player.HudKiri = Global.HudKiriPemain[Event Player.UrutanHUD];" in rule.body
        and "Event Player.HudKanan = Global.HudKananPemain[Event Player.UrutanHUD];" in rule.body
    ), None)
    checks.require(roster_hud is not None, "renderer roster persistente post-team-switch assente")
    if roster_hud:
        roster_conditions = rule_block(roster_hud, "conditions") or ""
        for token in (
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
        checks.require(
            "Is Alive(Event Player) == True;" not in roster_conditions,
            "renderer roster non deve attendere Is Alive e bloccare il lifecycle globale",
        )
        checks.require("Server Load < 150" not in roster_conditions,
                       "renderer roster non deve dipendere dal carico server")
        checks.require(
            "Or(Global.HudKiriPemain[Event Player.UrutanHUD] == 0, Global.HudKiriPemain[Event Player.UrutanHUD] == Null)" in roster_hud.body
            and "Or(Global.HudKananPemain[Event Player.UrutanHUD] == 0, Global.HudKananPemain[Event Player.UrutanHUD] == Null)" in roster_hud.body,
            "renderer roster lazy deve creare soltanto handle slot ancora vuoti",
        )
        ready = "Event Player.HudPemainDibuat = And(And(Event Player.HudKiri != Null, Event Player.HudKiri != 0), And(Event Player.HudKanan != Null, Event Player.HudKanan != 0));"
        ready_order = tuple(
            roster_hud.body.find(token)
            for token in (
                "Global.HudKiriPemain[Event Player.UrutanHUD] = Last Text ID;",
                "Global.HudKananPemain[Event Player.UrutanHUD] = Last Text ID;",
                "Event Player.HudKiri = Global.HudKiriPemain[Event Player.UrutanHUD];",
                "Event Player.HudKanan = Global.HudKananPemain[Event Player.UrutanHUD];",
                ready,
            )
        )
        checks.require(
            all(position >= 0 for position in ready_order)
            and ready_order == tuple(sorted(ready_order)),
            "renderer roster deve dichiararsi pronto dopo entrambi gli handle",
        )

'''
text = text[:start] + lifecycle_block + text[end:]

# 3) Bot isolation still treats this renderer as a human-only entrypoint, but it now
# contains the two Create HUD calls instead of only aliasing pre-created rows.
old_entry = '''        (next((rule for rule in rules if event_type(rule) == "Ongoing - Each Player" and "HudPemainDibuat" in rule.body and "Global.HudKiriPemain[Event Player.UrutanHUD]" in rule.body and "Create HUD Text(" not in rule.body), None), "HUD player", True),
'''
new_entry = '''        (next((rule for rule in rules if event_type(rule) == "Ongoing - Each Player" and "HudPemainDibuat" in rule.body and "Global.HudKiriPemain[Event Player.UrutanHUD] = Last Text ID;" in rule.body and "Global.HudKananPemain[Event Player.UrutanHUD] = Last Text ID;" in rule.body), None), "HUD player", True),
'''
text = replace_once(text, old_entry, new_entry, "human HUD entrypoint")
path.write_text(text, encoding="utf-8")

# Add a mutation test for the exact live failure: creation must be gated by a populated identity.
path = Path("tests/test_validate_workshop.py")
tests = path.read_text(encoding="utf-8")
anchor = '''    def test_classifier_rearms_when_a_roster_slot_is_temporarily_unavailable(self) -> None:
'''
new_test = '''    def test_lazy_roster_rows_require_assigned_identity_before_creation(self) -> None:
        renderer = self.rule(
            lambda rule: validator.event_type(rule) == "Ongoing - Each Player"
            and "Global.HudKiriPemain[Event Player.UrutanHUD] = Last Text ID;" in rule.body
            and "Global.HudKananPemain[Event Player.UrutanHUD] = Last Text ID;" in rule.body
        )
        conditions = validator.rule_block(renderer, "conditions") or ""
        for guard in (
            "Event Player.NamaTampilan != Null;",
            'Event Player.NamaTampilan != Custom String("");',
            "Event Player.UrutanHUD >= 0;",
            "Global.PemainSlotHUD[Event Player.UrutanHUD] == Event Player;",
        ):
            with self.subTest(guard=guard):
                self.assertIn(guard, conditions)
                mutated = self.replace_in_rule(renderer, guard, "")
                self.assert_rejected(mutated, "renderer roster lazy senza guardia identità")

'''
tests = replace_once(tests, anchor, new_test + anchor, "lazy identity mutation test")
path.write_text(tests, encoding="utf-8")

print("final lazy roster validator alignment applied")
