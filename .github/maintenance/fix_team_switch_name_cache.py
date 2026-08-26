from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IT = ROOT / "workshop" / "ruang_irama.it-IT.workshop"
EN = ROOT / "tests" / "fixtures" / "semantic_reference.txt"
RUNTIME_TEST = ROOT / "tests" / "test_runtime_maintenance.py"
CHANGELOG = ROOT / "CHANGELOG.md"


def patch_source(path: Path, global_name: str, rule_kw: str, actions_kw: str) -> None:
    text = path.read_text(encoding="utf-8")
    fast_marker = f'{rule_kw}("89a - Subrutin: Proses status cepat pemain")'
    next_marker = f'{rule_kw}("89b - Subrutin: Proses siklus pemain 10 Hz")'
    start = text.index(fast_marker)
    end = text.index(next_marker, start)
    fast = text[start:end]

    repair = (
        f'\t\tIf(And(Array Contains({global_name}.PemainManusia, {global_name}.PemainAktif) == True, '
        f'And(Or({global_name}.PemainAktif.NamaTampilan == Null, {global_name}.PemainAktif.NamaTampilan == Custom String("")), '
        f'Custom String("{{0}}", {global_name}.PemainAktif) != Custom String(""))));\n'
        f'\t\t\t{global_name}.PemainAktif.NamaTampilan = Evaluate Once(Custom String("{{0}}", {global_name}.PemainAktif));\n'
        f'\t\tEnd;\n'
    )
    actions_anchor = f'\t{actions_kw}\n\t{{\n'
    if repair not in fast:
        if fast.count(actions_anchor) != 1:
            raise RuntimeError(f"{path.name}: fast actions anchor mismatch")
        fast = fast.replace(actions_anchor, actions_anchor + repair, 1)

    old_guard = f'\t\t\tIf({global_name}.PemainAktif.NamaTampilan == Null);\n'
    new_guard = (
        f'\t\t\tIf(And(Or({global_name}.PemainAktif.NamaTampilan == Null, '
        f'{global_name}.PemainAktif.NamaTampilan == Custom String("")), '
        f'Custom String("{{0}}", {global_name}.PemainAktif) != Custom String("")));\n'
    )
    if old_guard in fast:
        fast = fast.replace(old_guard, new_guard, 1)
    elif new_guard not in fast:
        raise RuntimeError(f"{path.name}: nested cache guard not found")

    text = text[:start] + fast + text[end:]

    roster_marker = f'{rule_kw}("02b - HUD Pemain: Buat segera setelah klasifikasi selesai")'
    roster_next = f'{rule_kw}("03c - Bot/Dummy: Kunci saat hidup kembali atau pahlawan berganti")'
    rs = text.index(roster_marker)
    re = text.index(roster_next, rs)
    roster = text[rs:re]
    empty_guard = '\t\tEvent Player.NamaTampilan != Custom String("");\n'
    if empty_guard not in roster:
        anchor = '\t\tEvent Player.NamaTampilan != Null;\n'
        if roster.count(anchor) != 1:
            raise RuntimeError(f"{path.name}: roster name guard mismatch")
        roster = roster.replace(anchor, anchor + empty_guard, 1)
    text = text[:rs] + roster + text[re:]

    path.write_text(text, encoding="utf-8")
    print(f"patched {path.relative_to(ROOT)}")


def patch_test() -> None:
    text = RUNTIME_TEST.read_text(encoding="utf-8")
    roster_old = '            self.assertIn("Event Player.NamaTampilan != Null;", roster)\n'
    roster_new = roster_old + '            self.assertIn(\'Event Player.NamaTampilan != Custom String("");\', roster)\n'
    if 'Event Player.NamaTampilan != Custom String("");' not in text:
        if text.count(roster_old) != 1:
            raise RuntimeError("runtime test roster cache guard anchor mismatch")
        text = text.replace(roster_old, roster_new, 1)

    old = (
        '            self.assertIn(f"If({global_name}.PemainAktif.NamaTampilan == Null);", fast)\n'
        '            self.assertIn(f\'{global_name}.PemainAktif.NamaTampilan = Evaluate Once(Custom String("{{0}}", {global_name}.PemainAktif));\', fast)\n'
    )
    new = (
        '            cache_invalid = f\'Or({global_name}.PemainAktif.NamaTampilan == Null, {global_name}.PemainAktif.NamaTampilan == Custom String("") )\'.replace(\'"") )\', \'""))\')\n'
        '            self.assertIn(cache_invalid, fast)\n'
        '            self.assertIn(f\'Custom String("{{0}}", {global_name}.PemainAktif) != Custom String("")\', fast)\n'
        '            self.assertIn(f\'{global_name}.PemainAktif.NamaTampilan = Evaluate Once(Custom String("{{0}}", {global_name}.PemainAktif));\', fast)\n'
        '            self.assertLess(fast.index(cache_invalid), fast.index(f"{global_name}.PemainAktif.TimTerakhir != Team Of({global_name}.PemainAktif)"))\n'
    )
    if old in text:
        text = text.replace(old, new, 1)
    elif 'cache_invalid =' not in text:
        raise RuntimeError("runtime test fast cache repair anchor mismatch")

    RUNTIME_TEST.write_text(text, encoding="utf-8")
    print("patched tests/test_runtime_maintenance.py")


def patch_changelog() -> None:
    text = CHANGELOG.read_text(encoding="utf-8")
    note = (
        '- Corretto il secondo deadlock live del roster dopo il cambio squadra: `NamaTampilan` viene ora riparato per qualunque membro già presente in `PemainManusia`, anche quando `Manusia` e `PernahDisiapkan` restano `True`. Valori `Null` o stringa vuota non possono più bloccare `02b`; il cache viene scritto solo quando il nome live è nuovamente disponibile.\n'
    )
    if note not in text:
        anchor = 'Stato: **live-pending**.\n\n'
        if text.count(anchor) < 1:
            raise RuntimeError("changelog status anchor missing")
        text = text.replace(anchor, anchor + note, 1)
        CHANGELOG.write_text(text, encoding="utf-8")
        print("patched CHANGELOG.md")


patch_source(IT, "Globale", "regola", "azioni")
patch_source(EN, "Global", "rule", "actions")
patch_test()
patch_changelog()
print("team-switch name-cache repair applied")
