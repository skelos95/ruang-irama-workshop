from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IT = ROOT / "workshop" / "ruang_irama.it-IT.workshop"
EN = ROOT / "tests" / "fixtures" / "semantic_reference.txt"
RUNTIME_TEST = ROOT / "tests" / "test_runtime_maintenance.py"
CHANGELOG = ROOT / "CHANGELOG.md"
VALIDATION = ROOT / "docs" / "VALIDAZIONE.md"


def replace_exact(text: str, old: str, new: str, label: str, expected: int = 1) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"{label}: expected {expected} occurrence(s), found {count}")
    return text.replace(old, new, expected)


def patch_source(path: Path, global_name: str) -> None:
    text = path.read_text(encoding="utf-8")
    if "107: NamaTampilan" in text:
        print(f"{path.name}: cached-name patch already present")
        return

    text = replace_exact(
        text,
        "\t\t106: SegarkanRosterTertunda\n}",
        "\t\t106: SegarkanRosterTertunda\n\t\t107: NamaTampilan\n}",
        f"{path.name}: player variable declaration",
    )

    text = replace_exact(
        text,
        "\t\tEvent Player.MusikKhusus = Null;\n\t\tEvent Player.SegarkanRosterTertunda = False;\n",
        "\t\tEvent Player.MusikKhusus = Null;\n\t\tEvent Player.SegarkanRosterTertunda = False;\n\t\tEvent Player.NamaTampilan = Null;\n",
        f"{path.name}: cached-name initialization",
    )

    slot_anchor = '''\t\t\tAbort;\n\t\tEnd;\n\t\t"Sembunyikan bilah, objektif, dan ikon mode tanpa mengganggu HUD pahlawan serta HUD buatan kita."\n'''
    slot_replacement = '''\t\t\tAbort;\n\t\tEnd;\n\t\t"Bekukan nama manusia sekali saat identitasnya valid. HUD roster dan teks dunia memakai salinan ini agar token player tidak kosong setelah pindah tim."\n\t\tEvent Player.NamaTampilan = Evaluate Once(Custom String("{0}", Event Player));\n\t\t"Sembunyikan bilah, objektif, dan ikon mode tanpa mengganggu HUD pahlawan serta HUD buatan kita."\n'''
    text = replace_exact(text, slot_anchor, slot_replacement, f"{path.name}: capture display name")

    text = replace_exact(
        text,
        "\t\tEvent Player.SegarkanRosterTertunda == False;\n\t\tEvent Player.HudPemainDibuat == False;",
        "\t\tEvent Player.SegarkanRosterTertunda == False;\n\t\tEvent Player.NamaTampilan != Null;\n\t\tEvent Player.HudPemainDibuat == False;",
        f"{path.name}: roster cached-name gate",
    )

    for suffix in ("MIN", "MENIT", "นาที"):
        text = replace_exact(
            text,
            f'Custom String("{{0}} - {{1}} {suffix}", Event Player, Event Player.MenitLobi)',
            f'Custom String("{{0}} - {{1}} {suffix}", Event Player.NamaTampilan, Event Player.MenitLobi)',
            f"{path.name}: left roster name {suffix}",
        )

    text = replace_exact(
        text,
        'Custom String("{0} - {1}", Event Player,\n\t\t\tEvent Player.MusikKhusus != Null ?',
        'Custom String("{0} - {1}", Event Player.NamaTampilan,\n\t\t\tEvent Player.MusikKhusus != Null ?',
        f"{path.name}: right roster name",
    )

    text = replace_exact(
        text,
        'Custom String("{0}", Event Player.TargetInspeksi), Round To Integer(Health(Event Player.TargetInspeksi), Down)',
        'Player Variable(Event Player.TargetInspeksi, Manusia) == True ? Player Variable(Event Player.TargetInspeksi, NamaTampilan) : Custom String("{0}", Event Player.TargetInspeksi), Round To Integer(Health(Event Player.TargetInspeksi), Down)',
        f"{path.name}: crouch inspection cached name",
    )

    text = replace_exact(
        text,
        'Custom String("{0}", Event Player), Round To Integer(Health(Event Player), Down)',
        'Event Player.Manusia == True ? Event Player.NamaTampilan : Custom String("{0}", Event Player), Round To Integer(Health(Event Player), Down)',
        f"{path.name}: luck vision cached name",
    )

    text = replace_exact(
        text,
        'Custom String("{0}", Event Player.CalonTargetTeleportasi), Round To Integer(Health(Event Player.CalonTargetTeleportasi), Down)',
        'Player Variable(Event Player.CalonTargetTeleportasi, Manusia) == True ? Player Variable(Event Player.CalonTargetTeleportasi, NamaTampilan) : Custom String("{0}", Event Player.CalonTargetTeleportasi), Round To Integer(Health(Event Player.CalonTargetTeleportasi), Down)',
        f"{path.name}: crouch teleport cached name",
    )

    repair_anchor = (
        f'\t\tIf(And(Is Dummy Bot({global_name}.PemainAktif) == False, And({global_name}.PemainAktif.BotOtomatis == False, '
        f'And(Array Contains({global_name}.PemainManusia, {global_name}.PemainAktif) == True, Or({global_name}.PemainAktif.Manusia == False, '
        f'{global_name}.PemainAktif.PernahDisiapkan == False)))));\n'
    )
    repair_prefix = (
        f'\t\tIf(And(Is Dummy Bot({global_name}.PemainAktif) == False, And({global_name}.PemainAktif.BotOtomatis == False, '
        f'And(Array Contains({global_name}.PemainManusia, {global_name}.PemainAktif) == True, {global_name}.PemainAktif.NamaTampilan == Null))));\n'
        f'\t\t\tIf(Custom String("{{0}}", {global_name}.PemainAktif) != Custom String(""));\n'
        f'\t\t\t\t{global_name}.PemainAktif.NamaTampilan = Evaluate Once(Custom String("{{0}}", {global_name}.PemainAktif));\n'
        f'\t\t\tEnd;\n'
        f'\t\tEnd;\n'
    )
    text = replace_exact(text, repair_anchor, repair_prefix + repair_anchor, f"{path.name}: cached-name repair")

    path.write_text(text, encoding="utf-8")
    print(f"patched {path.relative_to(ROOT)}")


def patch_runtime_test() -> None:
    text = RUNTIME_TEST.read_text(encoding="utf-8")
    if "test_cached_player_name_drives_roster_and_world_text" in text:
        return
    anchor = "    def test_aim_scans_are_scheduler_cached(self):\n"
    test = '''    def test_cached_player_name_drives_roster_and_world_text(self):\n        for source, global_name, rule_kw in ((self.it, "Globale", "regola"), (self.en, "Global", "rule")):\n            self.assertIn("107: NamaTampilan", source)\n\n            classifier = source.split(f'{rule_kw}("02 - Pemain: Pisahkan manusia dari pasukan kaleng")', 1)[1].split(f'{rule_kw}("02b - HUD Pemain', 1)[0]\n            self.assertIn('Event Player.NamaTampilan = Evaluate Once(Custom String("{0}", Event Player));', classifier)\n\n            roster = source.split(f'{rule_kw}("02b - HUD Pemain', 1)[1].split(f'{rule_kw}("03c - Bot/Dummy', 1)[0]\n            self.assertIn("Event Player.NamaTampilan != Null;", roster)\n            self.assertIn('Custom String("{0} - {1} MIN", Event Player.NamaTampilan, Event Player.MenitLobi)', roster)\n            self.assertIn('Custom String("{0} - {1}", Event Player.NamaTampilan,', roster)\n\n            inspect = source.split(f'{rule_kw}("13 - Intip Pahlawan: Nama mengikuti target bidikan tanpa Wait")', 1)[1].split(f'{rule_kw}("16a - Anran', 1)[0]\n            self.assertIn("Player Variable(Event Player.TargetInspeksi, NamaTampilan)", inspect)\n\n            vision = source.split(f'{rule_kw}("18i - Nasib: Visi menampilkan nama publik dan bot")', 1)[1].split(f'{rule_kw}("18j - Nasib', 1)[0]\n            self.assertIn('Event Player.Manusia == True ? Event Player.NamaTampilan : Custom String("{0}", Event Player)', vision)\n\n            teleport = source.split(f'{rule_kw}("19d - Teleportasi Jongkok: Buat ulang nama saat target berubah")', 1)[1].split(f'{rule_kw}("19e - Teleportasi Jongkok', 1)[0]\n            self.assertIn("Player Variable(Event Player.CalonTargetTeleportasi, NamaTampilan)", teleport)\n\n            fast = source.split(f'{rule_kw}("89a - Subrutin: Proses status cepat pemain")', 1)[1].split(f'{rule_kw}("89b - Subrutin', 1)[0]\n            self.assertIn(f"{global_name}.PemainAktif.NamaTampilan == Null", fast)\n            self.assertIn(f'{global_name}.PemainAktif.NamaTampilan = Evaluate Once(Custom String("{{0}}", {global_name}.PemainAktif));', fast)\n\n'''
    text = replace_exact(text, anchor, test + anchor, "runtime regression test")
    RUNTIME_TEST.write_text(text, encoding="utf-8")


def update_docs_hash() -> None:
    data = IT.read_bytes().replace(b"\r\n", b"\n")
    payload = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    blob = hashlib.sha1(payload).hexdigest()
    text = VALIDATION.read_text(encoding="utf-8")
    updated, count = re.subn(
        r"(Blob Git del sorgente Workshop validato:\n\n```text\n)[0-9a-f]{40}(\n```)",
        rf"\g<1>{blob}\g<2>",
        text,
        count=1,
    )
    if count != 1:
        raise RuntimeError("validation document: Workshop blob marker not found")
    VALIDATION.write_text(updated, encoding="utf-8")


def update_changelog() -> None:
    text = CHANGELOG.read_text(encoding="utf-8")
    note = "- Corretto il nome dopo il cambio squadra: gli umani salvano `NamaTampilan` con `Evaluate Once` durante la classificazione e le due righe roster, Crouch Inspect, Crouch Teleport e Try Your Luck Vision usano la copia stabile invece del token player live; il refresh differito esistente resta invariato.\n"
    if note in text:
        return
    anchor = "Stato: **live-pending**.\n\n"
    text = replace_exact(text, anchor, anchor + note, "changelog cached-name note")
    CHANGELOG.write_text(text, encoding="utf-8")


patch_source(IT, "Globale")
patch_source(EN, "Global")
patch_runtime_test()
update_changelog()
update_docs_hash()
print("Cached player-name team-switch fix applied")
