from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IT = ROOT / "workshop" / "ruang_irama.it-IT.workshop"
EN = ROOT / "tests" / "fixtures" / "semantic_reference.txt"
RUNTIME_TEST = ROOT / "tests" / "test_runtime_maintenance.py"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"


def refine_source(path: Path, global_name: str) -> None:
    text = path.read_text(encoding="utf-8")

    standalone = (
        f'\t\tIf(And(Is Dummy Bot({global_name}.PemainAktif) == False, And({global_name}.PemainAktif.BotOtomatis == False, '
        f'And(Array Contains({global_name}.PemainManusia, {global_name}.PemainAktif) == True, {global_name}.PemainAktif.NamaTampilan == Null))));\n'
        f'\t\t\tIf(Custom String("{{0}}", {global_name}.PemainAktif) != Custom String(""));\n'
        f'\t\t\t\t{global_name}.PemainAktif.NamaTampilan = Evaluate Once(Custom String("{{0}}", {global_name}.PemainAktif));\n'
        f'\t\t\tEnd;\n'
        f'\t\tEnd;\n'
    )
    if standalone in text:
        text = text.replace(standalone, "", 1)

    registered = (
        f'\t\tIf(And(Is Dummy Bot({global_name}.PemainAktif) == False, And({global_name}.PemainAktif.BotOtomatis == False, '
        f'And(Array Contains({global_name}.PemainManusia, {global_name}.PemainAktif) == True, Or({global_name}.PemainAktif.Manusia == False, '
        f'{global_name}.PemainAktif.PernahDisiapkan == False)))));\n'
    )
    cache_repair = (
        f'\t\t\tIf({global_name}.PemainAktif.NamaTampilan == Null);\n'
        f'\t\t\t\t{global_name}.PemainAktif.NamaTampilan = Evaluate Once(Custom String("{{0}}", {global_name}.PemainAktif));\n'
        f'\t\t\tEnd;\n'
    )
    if cache_repair not in text:
        if text.count(registered) != 1:
            raise RuntimeError(f"{path.name}: registered repair anchor mismatch")
        text = text.replace(registered, registered + cache_repair, 1)

    cached_vision = (
        'Event Player.Manusia == True ? Event Player.NamaTampilan : Custom String("{0}", Event Player), '
        'Round To Integer(Health(Event Player), Down)'
    )
    live_vision = 'Custom String("{0}", Event Player), Round To Integer(Health(Event Player), Down)'
    if cached_vision in text:
        text = text.replace(cached_vision, live_vision, 1)

    path.write_text(text, encoding="utf-8")


def refine_runtime_test() -> None:
    text = RUNTIME_TEST.read_text(encoding="utf-8")
    start = text.find("    def test_cached_player_name_drives_roster_and_world_text(self):\n")
    end = text.find("    def test_aim_scans_are_scheduler_cached(self):\n", start)
    if start < 0 or end < 0:
        raise RuntimeError("runtime cached-name regression test block not found")
    replacement = '''    def test_cached_player_name_drives_roster_and_world_text(self):\n        for source, global_name, rule_kw in ((self.it, "Globale", "regola"), (self.en, "Global", "rule")):\n            self.assertIn("107: NamaTampilan", source)\n\n            classifier = source.split(f'{rule_kw}("02 - Pemain: Pisahkan manusia dari pasukan kaleng")', 1)[1].split(f'{rule_kw}("02b - HUD Pemain', 1)[0]\n            self.assertIn('Event Player.NamaTampilan = Evaluate Once(Custom String("{0}", Event Player));', classifier)\n\n            roster = source.split(f'{rule_kw}("02b - HUD Pemain', 1)[1].split(f'{rule_kw}("03c - Bot/Dummy', 1)[0]\n            self.assertIn("Event Player.NamaTampilan != Null;", roster)\n            self.assertIn('Custom String("{0} - {1} MIN", Event Player.NamaTampilan, Event Player.MenitLobi)', roster)\n            self.assertIn('Custom String("{0} - {1}", Event Player.NamaTampilan,', roster)\n\n            inspect = source.split(f'{rule_kw}("13 - Intip Pahlawan: Nama mengikuti target bidikan senza Wait")', 1)[1].split(f'{rule_kw}("16a - Anran', 1)[0]\n            self.assertIn("Player Variable(Event Player.TargetInspeksi, NamaTampilan)", inspect)\n\n            teleport = source.split(f'{rule_kw}("19d - Teleportasi Jongkok: Buat ulang nama saat target berubah")', 1)[1].split(f'{rule_kw}("19e - Teleportasi Jongkok', 1)[0]\n            self.assertIn("Player Variable(Event Player.CalonTargetTeleportasi, NamaTampilan)", teleport)\n\n            fast = source.split(f'{rule_kw}("89a - Subrutin: Proses status cepat pemain")', 1)[1].split(f'{rule_kw}("89b - Subrutin', 1)[0]\n            self.assertIn(f"If({global_name}.PemainAktif.NamaTampilan == Null);", fast)\n            self.assertIn(f'{global_name}.PemainAktif.NamaTampilan = Evaluate Once(Custom String("{{0}}", {global_name}.PemainAktif));', fast)\n\n'''
    text = text[:start] + replacement + text[end:]
    RUNTIME_TEST.write_text(text, encoding="utf-8")


def refine_validator() -> None:
    text = VALIDATOR.read_text(encoding="utf-8")
    marker = 'checks.equal(len(vibe_calls), 1, "profilo speciale: espressione Player Vibes roster")'
    marker_at = text.find(marker)
    if marker_at < 0:
        raise RuntimeError("validator Player Vibes marker not found")
    old = 'and call.args[1].strip() == "Event Player"'
    pos = text.rfind(old, max(0, marker_at - 1200), marker_at)
    if pos < 0:
        raise RuntimeError("validator Player Vibes player-argument gate not found")
    new = 'and call.args[1].strip() in {"Event Player", "Event Player.NamaTampilan"}'
    text = text[:pos] + new + text[pos + len(old):]
    VALIDATOR.write_text(text, encoding="utf-8")


refine_source(IT, "Globale")
refine_source(EN, "Global")
refine_runtime_test()
refine_validator()
print("Cached-name patch refined for semantic validator")
