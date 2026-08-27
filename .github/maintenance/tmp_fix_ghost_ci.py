from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def replace_exact(path: str, old: str, new: str, expected: int = 1) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise SystemExit(f"{path}: expected {expected} occurrence(s), found {count}: {old[:160]!r}")
    target.write_text(text.replace(old, new), encoding="utf-8")
    print(f"patched {path}: {count} exact replacement(s)")


def replace_regex(path: str, pattern: str, replacement: str, expected: int = 1) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    new_text, count = re.subn(pattern, replacement, text, flags=re.MULTILINE | re.DOTALL)
    if count != expected:
        raise SystemExit(f"{path}: expected {expected} regex replacement(s), found {count}: {pattern[:160]!r}")
    target.write_text(new_text, encoding="utf-8")
    print(f"patched {path}: {count} regex replacement(s)")


# The old roster-refresh flag is gone. The roster binding rule must not own Ghost state.
replace_exact(
    "tests/test_runtime_maintenance.py",
    '            self.assertIn("Event Player.GhostAktif = False;", roster)\n',
    "",
    expected=2,
)

# Keep the Dummy Follow validator scoped to page 12. Ghost has its own checks.
replace_exact(
    "tools/validate_workshop.py",
    '''        for token in (\n            "12 - DUMMY FOLLOW",\n            "ENEMY DUMMY",\n            "12 - DUMMY MENGIKUTI",\n            "DUMMY MUSUH",\n            "12 - ดัมมี่ติดตาม",\n            "13 - GHOST MODE",\n            "13 - MODE GHOST",\n            "13 - โหมดผี",\n        ):\n            checks.require(token in dummy_follow_renderer.body,\n                           f"pagina 12 Dummy Follow non chiarisce il consenso localizzato: {token}")\n''',
    '''        for token in (\n            "12 - DUMMY FOLLOW",\n            "ENEMY DUMMY",\n            "12 - DUMMY MENGIKUTI",\n            "DUMMY MUSUH",\n            "12 - ดัมมี่ติดตาม",\n        ):\n            checks.require(token in dummy_follow_renderer.body,\n                           f"pagina 12 Dummy Follow non chiarisce il consenso localizzato: {token}")\n''',
)

# Page 13 is a first-class apply subroutine and inherits the no-Wait/no-Loop/no-HUD contract.
replace_exact(
    "tools/validate_workshop.py",
    '    "TerapkanHalamanIkutiDummy",\n}\n',
    '    "TerapkanHalamanIkutiDummy",\n    "TerapkanHalamanGhost",\n}\n',
)
replace_exact(
    "tools/validate_workshop.py",
    '"dispatcher Interact non suddiviso nelle 13 subroutine pagina"',
    '"dispatcher Interact non suddiviso nelle 14 subroutine pagina"',
)

# Main-menu announcement must describe 14 pages (indices 0..13), and stale 12/13-page wording is forbidden.
replace_exact(
    "tools/validate_workshop.py",
    '''    for text in (\n        "Arcade Menu online. Thirteen extremely important decisions await.",\n        "Menu Arcade online. Tiga belas keputusan yang sangat penting menunggu.",\n        "เปิดเมนูอาร์เคดแล้ว มีสิบสามตัวเลือกสำคัญรอคุณอยู่",\n    ):\n        checks.require(text in source, f"messaggio apertura menu a 13 pagine assente: {text}")\n    for legacy in ("Twelve extremely important decisions", "Dua belas keputusan", "มีสิบสองตัวเลือก"):\n        checks.require(legacy not in source, f"messaggio apertura menu ancora fermo a 12: {legacy}")\n''',
    '''    for text in (\n        "Arcade Menu online. Fourteen extremely important decisions await.",\n        "Menu Arcade online. Empat belas keputusan yang sangat penting menunggu.",\n        "เปิดเมนูอาร์เคดแล้ว มีสิบสี่ตัวเลือกสำคัญรอคุณอยู่",\n    ):\n        checks.require(text in source, f"messaggio apertura menu a 14 pagine assente: {text}")\n    for legacy in (\n        "Twelve extremely important decisions",\n        "Dua belas keputusan",\n        "มีสิบสองตัวเลือก",\n        "Thirteen extremely important decisions",\n        "Tiga belas keputusan",\n        "มีสิบสามตัวเลือก",\n    ):\n        checks.require(legacy not in source, f"messaggio apertura menu con conteggio legacy: {legacy}")\n''',
)

# Mutation tests must target the new 14-page menu and its actual wraparound expression.
replace_exact(
    "tests/test_validate_workshop.py",
    '''    def test_all_thirteen_pages_are_routed(self) -> None:\n        router = self.rule(lambda rule: validator.subroutine_target(rule) == "GambarHalamanAktif")\n        mutated = self.replace_in_rule(router, "HalamanMenu == 12", "HalamanMenu == 13")\n        self.assert_rejected(mutated, "pagina 12")\n\n    def test_main_menu_cycles_exactly_over_pages_zero_through_twelve(self) -> None:\n        navigation = self.rule(\n            lambda rule: "Event Player.KursorUtama = (Event Player.KursorUtama" in rule.body\n        )\n        mutated = self.replace_in_rule(\n            navigation,\n            "(Event Player.PerintahMenu == 3 ? 1 : 12)) % 14;",\n            "(Event Player.PerintahMenu == 3 ? 1 : 11)) % 12;",\n        )\n        self.assert_rejected(mutated, "ciclo esatto 0..13")\n''',
    '''    def test_all_fourteen_pages_are_routed(self) -> None:\n        router = self.rule(lambda rule: validator.subroutine_target(rule) == "GambarHalamanAktif")\n        mutated = self.replace_in_rule(router, "HalamanMenu == 13", "HalamanMenu == 14")\n        self.assert_rejected(mutated, "pagina 13")\n\n    def test_main_menu_cycles_exactly_over_pages_zero_through_thirteen(self) -> None:\n        navigation = self.rule(\n            lambda rule: "Event Player.KursorUtama = (Event Player.KursorUtama" in rule.body\n        )\n        mutated = self.replace_in_rule(\n            navigation,\n            "(Event Player.PerintahMenu == 3 ? 1 : 13)) % 14;",\n            "(Event Player.PerintahMenu == 3 ? 1 : 12)) % 13;",\n        )\n        self.assert_rejected(mutated, "ciclo esatto 0..13")\n''',
)
replace_exact(
    "tests/test_validate_workshop.py",
    "def test_menu_open_message_announces_thirteen_pages_in_all_languages",
    "def test_menu_open_message_announces_fourteen_pages_in_all_languages",
)
replace_exact(
    "tests/test_validate_workshop.py",
    'self.assert_rejected(mutated, "messaggio apertura menu a 13 pagine assente")',
    'self.assert_rejected(mutated, "messaggio apertura menu a 14 pagine assente")',
    expected=3,
)
replace_exact(
    "tests/test_validate_workshop.py",
    '''        for legacy in (\n            "Twelve extremely important decisions",\n            "Dua belas keputusan",\n            "มีสิบสองตัวเลือก",\n        ):\n''',
    '''        for legacy in (\n            "Twelve extremely important decisions",\n            "Dua belas keputusan",\n            "มีสิบสองตัวเลือก",\n            "Thirteen extremely important decisions",\n            "Tiga belas keputusan",\n            "มีสิบสามตัวเลือก",\n        ):\n''',
)
replace_exact(
    "tests/test_validate_workshop.py",
    'self.assert_rejected(mutated, "messaggio apertura menu ancora fermo a 12")',
    'self.assert_rejected(mutated, "messaggio apertura menu con conteggio legacy")',
)

# PROGETTO: current contract must describe 14 pages, permanent global roster rows and profile persistence.
replace_exact(
    "docs/PROGETTO.md",
    "le 13 pagine mantengono gli indici `0..13`",
    "le 14 pagine mantengono gli indici `0..13`",
)
replace_exact(
    "docs/PROGETTO.md",
    "Il ciclo del Main Menu è esattamente modulo 13; pagina 12 dispone di cursore OFF/ON separato dallo stato applicato, renderer EN/ID/TH e tinta dedicata. Soltanto setup, applicazione della pagina e quiete lifecycle possono scrivere la preferenza Dummy Follow, impedendo che Camera o altri latch la modifichino accidentalmente.",
    "Il ciclo del Main Menu è esattamente modulo 14. Pagina 12 mantiene Dummy Follow con cursore OFF/ON separato dallo stato applicato; pagina 13 mantiene Ghost Mode con lo stesso modello di cursore/applicazione, renderer EN/ID/TH e tinta dedicata. Ghost modifica soltanto la collisione con l'ambiente: ON disabilita muri e soffitti con `Include Floors = False`, OFF ripristina la collisione ambiente normale. La collisione con player/bot resta indipendente.",
)
replace_regex(
    "docs/PROGETTO.md",
    r"### Cambio squadra\n\nIl cambio Team 1 ↔ Team 2.*?\n\nNel caso limite senza slot",
    """### Cambio squadra\n\nIl cambio Team 1 ↔ Team 2 di un umano già registrato usa un rebind leggero. Le 12 coppie roster Left/Right appartengono agli slot globali permanenti (`PemainSlotHUD` / `NamaSlotHUD`): non vengono distrutte né ricreate durante il cambio squadra. Il runtime riassocia l'entità corrente allo stesso `UrutanHUD`, ripristina il nome dalla cache globale, chiude soltanto UI transitoria come Menu Arcade/Teleport e riasserisce gli stati engine che possono essere persi dal cambio entità, incluso Ghost Mode. `HudKiri`/`HudKanan` restano alias dei due handle globali dello slot e `HudPemainDibuat` funge da ready flag, senza gate `Is Alive` o `Server Load`. Un vero leave rimuove il player dai roster/cache dinamici ma lascia intatte le righe HUD permanenti; il profilo per nome viene conservato per un rejoin nello stesso match.\n\nNel caso limite senza slot""",
)
replace_exact(
    "docs/PROGETTO.md",
    "Il matching usa esclusivamente il nome visibile, non un identificatore account: due omonimi esatti ricevono lo stesso profilo, mentre una rinomina non viene riconosciuta. Il cambio squadra leggero conserva colore e icona eventualmente scelti e mantiene il Vibes bloccato; un leave vero seguito da rejoin esegue nuovamente il setup e riapplica `Silver Mist`, `Poison 2` e `Caladan Brood`.",
    "Il matching usa esclusivamente il nome visibile, non un identificatore account: due omonimi esatti condividono lo stesso profilo, mentre una rinomina non viene riconosciuta. Il cambio squadra leggero conserva colore e icona eventualmente scelti e mantiene il Vibes bloccato. Un leave vero salva il profilo per nome e un rejoin nello stesso match ripristina le ultime preferenze salvate; soltanto un nuovo match/restart, che svuota le cache profilo, riparte dai default `Silver Mist`, `Poison 2` e `Caladan Brood`.",
)

# VALIDAZIONE: align page count and lifecycle invariants with the current global-slot architecture.
replace_exact(
    "docs/VALIDAZIONE.md",
    "Data: 2026-08-25",
    "Data: 2026-08-27",
)
replace_exact(
    "docs/VALIDAZIONE.md",
    "- pagina 12 Dummy Follow completa di renderer, cursore OFF/ON, dispatcher, tinta dedicata e default OFF; il messaggio di apertura deve annunciare tredici pagine in EN/ID/TH e non può contenere le vecchie forme Twelve/Dua belas/สิบสอง;",
    "- pagina 12 Dummy Follow e pagina 13 Ghost Mode complete di renderer, cursore OFF/ON, dispatcher, tinta dedicata e default OFF; il messaggio di apertura deve annunciare quattordici pagine in EN/ID/TH e non può contenere le vecchie forme a 12/13 pagine; Ghost deve modificare solo la collisione ambiente e mantenere solidi i pavimenti;",
)
replace_regex(
    "docs/VALIDAZIONE.md",
    r"- cambio squadra di un umano registrato implementato come refresh leggero differito:.*?\n- recovery non-roster del pending, così un riferimento cambiato viene riaccodato al setup e non resta invisibile sia nelle due liste sia nei target Crouch; se le player variables sono state sostituite, questo fallback riapplica i default;",
    """- cambio squadra di un umano registrato implementato come rebind leggero: `PemainSlotHUD` viene aggiornato senza distruggere le 12 coppie roster globali permanenti, `NamaSlotHUD` conserva l'identità stabile e il percorso non dipende da `Server Load`;\n- `HudKiri`/`HudKanan` sono soltanto alias dei due handle globali dello slot e `HudPemainDibuat` diventa vero solo dopo entrambi gli alias, senza gate `Is Alive`; Menu Arcade e overlay Teleport possono essere chiusi/riarmati senza ricreare il roster;\n- il fast repair del nome preferisce `NamaSlotHUD`; Crouch inspection/Teleport leggono la stessa identità globale e il vero leave svuota solo il payload occupante senza distruggere gli handle roster permanenti;""",
)

# TEST: 14 menu, Ghost coverage and current rejoin semantics.
replace_exact(
    "docs/TEST.md",
    "I test live della 0.8.0 erano stati completati; la 0.8.1 introduce il refresh leggero del cambio squadra e il profilo dedicato `งูแท้`, quindi deve completare nuovamente la matrice nel client. Eventuali valori diagnostici numerici non forniti non vengono inventati.",
    "I test live della 0.8.0 erano stati completati; la 0.8.1 introduce il roster globale permanente, il profilo dedicato `งูแท้` e Menu 13 Ghost Mode, quindi deve completare nuovamente la matrice nel client. Eventuali valori diagnostici numerici non forniti non vengono inventati.",
)
replace_exact(
    "docs/TEST.md",
    '''Verificare esattamente 13 voci, indici e contenuti:\n\n1. Name Color — 32 colori.\n2. Third-Person Camera — OFF, self e target valido.\n3. Soundtrack — 100 generi.\n4. HUD Language — English, Bahasa Indonesia, ไทย.\n5. Revenge — debiti da kill dirette.\n6. Unkillable — OFF, 1 HP, FULL HP.\n7. Hero Voice — 5 preset.\n8. Player Icon — Nothing + 36 icone.\n9. Crouch Teleport — OFF/ON.\n10. Crouch Privacy — OFF/ON (default OFF).\n11. Try Your Luck — sei esiti.\n12. Vote Player — umani, self-vote incluso.\n13. Dummy Follow — il dummy nemico può seguire il player, OFF/ON (default OFF).\n''',
    '''Verificare esattamente 14 voci, indici e contenuti:\n\n1. Name Color — 32 colori.\n2. Third-Person Camera — OFF, self e target valido.\n3. Soundtrack — 100 generi.\n4. HUD Language — English, Bahasa Indonesia, ไทย.\n5. Revenge — debiti da kill dirette.\n6. Unkillable — OFF, 1 HP, FULL HP.\n7. Hero Voice — 5 preset.\n8. Player Icon — Nothing + 36 icone.\n9. Crouch Teleport — OFF/ON.\n10. Crouch Privacy — OFF/ON (default OFF).\n11. Try Your Luck — sei esiti.\n12. Vote Player — umani, self-vote incluso.\n13. Dummy Follow — il dummy nemico può seguire il player, OFF/ON (default OFF).\n14. Ghost Mode — OFF/ON (default OFF); ON attraversa muri e soffitti mantenendo solidi i pavimenti.\n''',
)
replace_exact(
    "docs/TEST.md",
    "- Uscire davvero dalla lobby e rientrare con lo stesso nome: il setup deve riapplicare `Silver Mist`, `Poison 2` e il Vibes bloccato.",
    "- Uscire davvero dalla lobby e rientrare con lo stesso nome nello stesso match: devono tornare le ultime scelte salvate di colore/icona e il Vibes deve restare `Caladan Brood`; dopo un nuovo match/restart i default tornano `Silver Mist` e `Poison 2`.",
)
replace_exact(
    "docs/TEST.md",
    "- Camera, status, effetti e voti attivi restano invariati; soltanto Menu Arcade e overlay Teleport vengono chiusi/riarmati e `HudKiri/HudKanan` vengono ricreati quando necessario;",
    "- Camera, status, effetti e voti attivi restano invariati; soltanto Menu Arcade e overlay Teleport vengono chiusi/riarmati, mentre le righe roster globali permanenti non vengono distrutte o ricreate;",
)
replace_exact(
    "docs/TEST.md",
    "- tutte le preferenze e i cursori restano invariati, inclusi lingua, colore, genere, icona, Teleport, Privacy, Dummy Follow e il profilo dedicato `งูแท้`; soltanto stato dipendente dal Team e riferimenti transitori vengono aggiornati;",
    "- tutte le preferenze e i cursori restano invariati, inclusi lingua, colore, genere, icona, Teleport, Privacy, Dummy Follow, Ghost Mode e il profilo dedicato `งูแท้`; soltanto stato dipendente dal Team e riferimenti transitori vengono aggiornati;",
)
replace_exact(
    "docs/TEST.md",
    "Eseguire separatamente un leave vero seguito da rejoin: non devono restare riferimenti stale e tutte le preferenze devono tornare ai default di setup; per `งูแท้` ciò significa `Silver Mist`, `Poison 2` e `Caladan Brood` bloccato.",
    "Eseguire separatamente un leave vero seguito da rejoin nello stesso match: non devono restare riferimenti stale e il profilo salvato deve ripristinare le preferenze precedenti, incluso Ghost Mode. Eseguire poi un nuovo match/restart e verificare il reset dei profili ai default di setup; per `งูแท้` ciò significa `Silver Mist`, `Poison 2` e `Caladan Brood` bloccato.",
)

# README: same-match rejoin restores the saved profile; fresh match restores defaults.
replace_exact(
    "README.md",
    "Un leave seguito da un vero rejoin esegue un nuovo setup e riapplica `Silver Mist`, `Poison 2` e il Vibes bloccato.",
    "Un leave seguito da un vero rejoin nello stesso match esegue un nuovo setup ma ripristina le ultime preferenze salvate dal profilo; un nuovo match/restart svuota le cache profilo e riparte da `Silver Mist`, `Poison 2` e dal Vibes bloccato.",
)

# Changelog entry for the current audit/feature without rewriting historical bullets.
replace_exact(
    "CHANGELOG.md",
    "Stato: **live-pending**.\n",
    "Stato: **live-pending**.\n\n- Audit runtime e Menu 13 Ghost Mode: il Main Menu ora copre 14 pagine (`0..13`). Ghost OFF/ON modifica soltanto la collisione ambiente (`Include Floors = False` quando ON), quindi attraversa muri e soffitti mantenendo solidi i pavimenti e senza toccare la collisione player/bot. Lo stato persiste nel profilo e viene riapplicato dopo cambio squadra/cambio eroe; il vecchio flag roster morto `SegarkanRosterTertunda` è stato riutilizzato senza aggiungere un nuovo array globale. L'audit non ha rilevato titoli di regola duplicati né corpi di regola esattamente duplicati.\n",
    expected=1,
)

print("Ghost CI repair complete")
