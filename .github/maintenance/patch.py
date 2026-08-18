from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
TESTS = ROOT / "tests" / "test_validate_workshop.py"
VERSION = ROOT / "VERSION"
README = ROOT / "README.md"
PROJECT = ROOT / "docs" / "PROGETTO.md"

OLD_BLOB = "f0940e494463c99d395e58ac9de0c67f75b61cb3"
NEW_VERSION = "0.7.1"


def git_blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def replace_exact(text: str, old: str, new: str, expected: int = 1) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"replacement mismatch: expected {expected}, found {count}: {old[:100]!r}")
    return text.replace(old, new)


def rule_bounds(text: str, title: str) -> tuple[int, int]:
    needle = f'rule("{title}")'
    start = text.index(needle)
    next_rule = text.find('\nrule("', start + len(needle))
    return start, len(text) if next_rule < 0 else next_rule


def edit_rule(text: str, title: str, editor) -> str:
    start, end = rule_bounds(text, title)
    block = text[start:end]
    edited = editor(block)
    if edited == block:
        raise RuntimeError(f"rule was not changed: {title}")
    return text[:start] + edited + text[end:]


def remove_rule(text: str, title: str) -> str:
    start, end = rule_bounds(text, title)
    return text[:start] + text[end:]


source = SOURCE.read_text(encoding="utf-8")
if git_blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch a moving target")

# Direct dummy bots have their own lock path. Keep the generic classifier only for
# humans / ordinary AI bots that need the name-probe fallback.
def isolate_direct_dummy(block: str) -> str:
    return replace_exact(
        block,
        "\t\tGlobal.Siap == True;\n\t\tEvent Player.SudahSiap == True;",
        "\t\tGlobal.Siap == True;\n\t\tIs Dummy Bot(Event Player) == False;\n\t\tEvent Player.SudahSiap == True;",
    )


source = edit_rule(source, "02 - Pemain: Pisahkan manusia dari pasukan kaleng", isolate_direct_dummy)
source = replace_exact(
    source,
    'rule("03c - Bot: Kunci saat hidup kembali atau pahlawan berganti")',
    'rule("03c - Bot/Dummy: Kunci saat hidup kembali atau pahlawan berganti")',
)
source = replace_exact(
    source,
    'rule("92 - Subrutin: Kunci bot, kaki tetap bisa bergerak")',
    'rule("92 - Subrutin: Kunci bot/dummy, kaki tetap bisa bergerak")',
)

# A direct dummy leaving never owned the human HUD/menu lifecycle.
def isolate_dummy_leave(block: str) -> str:
    return replace_exact(
        block,
        "\t}\n\n\tactions\n\t{",
        "\t}\n\n\tconditions\n\t{\n\t\tIs Dummy Bot(Event Player) == False;\n\t}\n\n\tactions\n\t{",
    )


source = edit_rule(source, "04 - Pemain Keluar: Tenangkan lalu bersihkan pendaftaran", isolate_dummy_leave)

# Remove periodic per-player polling. These jobs are rebuilt below as shared
# Ongoing Global schedulers, while input/latch rules remain Each Player.
for obsolete in (
    "02c - Ruang Muncul: Perbarui posisi aman setiap kali masuk",
    "03 - Waktu: Hitung menit nongkrong tanpa bikin server ngos-ngosan",
    "07b - Menu kamera: Segarkan pemain dan bot yang bisa ditonton",
    "07c - Menu Balas Dendam: Segarkan data tanpa menggambar ulang",
    "14 - Intip Pahlawan: Perbarui target meski terhalang dinding",
    "16 - Kamera: Target pergi, pulangkan pandangan",
    "19f - Teleportasi Jongkok: Segarkan daftar target tanpa menggambar ulang berkala",
):
    source = remove_rule(source, obsolete)

# Camera target invalidation is lifecycle work, not an input dispatcher: move it
# into the existing 10 Hz global lifecycle manager and also handle dead targets.
def improve_global_lifecycle(block: str) -> str:
    marker = "\t\tIf(Global.PemainAktif.InspeksiAktif == True);"
    camera = '''\t\tIf(Global.PemainAktif.ModeKamera == 2);\n\t\t\tIf(Or(Or(Global.PemainAktif.TargetKamera == Null, Entity Exists(Global.PemainAktif.TargetKamera) == False), Or(\n\t\t\t\tHas Spawned(Global.PemainAktif.TargetKamera) == False, Is Alive(Global.PemainAktif.TargetKamera) == False)) == True);\n\t\t\t\tStop Camera(Global.PemainAktif);\n\t\t\t\tSet Player Variable(Global.PemainAktif, ModeKamera, 0);\n\t\t\t\tSet Player Variable(Global.PemainAktif, TargetKamera, Null);\n\t\t\t\tPlay Effect(All Players(All Teams), Ring Explosion, Global.RGB, Position Of(Global.PemainAktif) + Vector(0, 1, 0), 3);\n\t\t\t\tSmall Message(Global.PemainAktif, Global.PemainAktif.IndeksBahasa == 0 ? Custom String(\n\t\t\t\t\t"Camera target unavailable. Back to normal.") : Global.PemainAktif.IndeksBahasa == 1 ? Custom String(\n\t\t\t\t\t"Target kamera tidak tersedia. Kembali normal.") : Custom String(\n\t\t\t\t\t"เป้าหมายกล้องไม่พร้อมใช้งาน กลับมุมมองปกติแล้ว"));\n\t\t\tEnd;\n\t\tEnd;\n'''
    return replace_exact(block, marker, camera + marker)


source = edit_rule(source, "04h - Global-first: Pengatur lifecycle ringan terpusat", improve_global_lifecycle)

# One global 1 Hz pass replaces Spawn Room + passive Camera/Revenge/Teleport
# refresh loops that previously existed once per player.
global_pollers = r'''
rule("04i - Global-first: Cache dan daftar pasif 1 Hz")
{
	event
	{
		Ongoing - Global;
	}

	conditions
	{
		Global.Siap == True;
	}

	actions
	{
		For Global Variable(IndeksPemainGlobal, 0, Count Of(Global.PemainManusia) - 1, 1);
			Global.PemainAktif = Global.PemainManusia[Global.IndeksPemainGlobal];
			If(And(Global.PemainAktif.Manusia == True, Entity Exists(Global.PemainAktif)));
				If(And(Has Spawned(Global.PemainAktif) == True, Is In Spawn Room(Global.PemainAktif) == True));
					Set Player Variable(Global.PemainAktif, PosisiRuangMuncul, Position Of(Global.PemainAktif));
					Set Player Variable(Global.PemainAktif, PunyaPosisiMuncul, True);
				End;

				If(And(Global.PemainAktif.MenuTerbuka == True, Global.PemainAktif.HalamanMenu == 1));
					If(And(Global.PemainAktif.KursorKamera >= 2, Global.PemainAktif.KursorKamera - 2 < Count Of(Global.PemainAktif.DaftarTargetKamera)));
						Set Player Variable(Global.PemainAktif, CalonTargetKamera, Global.PemainAktif.DaftarTargetKamera[Global.PemainAktif.KursorKamera - 2]);
					Else;
						Set Player Variable(Global.PemainAktif, CalonTargetKamera, Null);
					End;
					Set Player Variable(Global.PemainAktif, DaftarTargetKamera, Filtered Array(All Players(All Teams), And(Current Array Element != Global.PemainAktif,
						And(Entity Exists(Current Array Element), And(Has Spawned(Current Array Element), Is Alive(Current Array Element))))));
					If(And(Global.PemainAktif.CalonTargetKamera != Null, Array Contains(Global.PemainAktif.DaftarTargetKamera, Global.PemainAktif.CalonTargetKamera)));
						Set Player Variable(Global.PemainAktif, KursorKamera, Index Of Array Value(Global.PemainAktif.DaftarTargetKamera, Global.PemainAktif.CalonTargetKamera) + 2);
					Else If(Global.PemainAktif.KursorKamera >= Count Of(Global.PemainAktif.DaftarTargetKamera) + 2);
						Set Player Variable(Global.PemainAktif, KursorKamera, 0);
					End;
				End;

				If(And(Global.PemainAktif.MenuTerbuka == True, Global.PemainAktif.HalamanMenu == 4));
					If(Global.PemainAktif.KursorBalasDendam < Count Of(Global.PemainAktif.DaftarTargetBalasDendam));
						Set Player Variable(Global.PemainAktif, TargetBalasDendamDipilih, Global.PemainAktif.DaftarTargetBalasDendam[Global.PemainAktif.KursorBalasDendam]);
					Else;
						Set Player Variable(Global.PemainAktif, TargetBalasDendamDipilih, Null);
					End;
					Set Player Variable(Global.PemainAktif, DaftarTargetBalasDendam, Filtered Array(Global.PemainManusia, Current Array Element != Global.PemainAktif));
					If(Count Of(Global.PemainAktif.DaftarTargetBalasDendam) == 0);
						Set Player Variable(Global.PemainAktif, KursorBalasDendam, 0);
					Else If(And(Global.PemainAktif.TargetBalasDendamDipilih != Null, Array Contains(Global.PemainAktif.DaftarTargetBalasDendam, Global.PemainAktif.TargetBalasDendamDipilih)));
						Set Player Variable(Global.PemainAktif, KursorBalasDendam, Index Of Array Value(Global.PemainAktif.DaftarTargetBalasDendam, Global.PemainAktif.TargetBalasDendamDipilih));
					Else If(Global.PemainAktif.KursorBalasDendam >= Count Of(Global.PemainAktif.DaftarTargetBalasDendam));
						Set Player Variable(Global.PemainAktif, KursorBalasDendam, 0);
					End;
				End;

				If(Global.PemainAktif.TeleportasiJongkokAktif == True);
					If(And(Global.PemainAktif.KursorTeleportasi >= 0, Global.PemainAktif.KursorTeleportasi < Count Of(Global.PemainAktif.DaftarTargetTeleportasi)));
						Set Player Variable(Global.PemainAktif, CalonTargetTeleportasi, Global.PemainAktif.DaftarTargetTeleportasi[Global.PemainAktif.KursorTeleportasi]);
					Else;
						Set Player Variable(Global.PemainAktif, CalonTargetTeleportasi, Null);
					End;
					Set Player Variable(Global.PemainAktif, DaftarTargetTeleportasi, Append To Array(Array(Global.PemainAktif, Null), Filtered Array(All Players(All Teams),
						And(Current Array Element != Global.PemainAktif, And(Player Variable(Current Array Element, PrivasiInspeksiAktif) == False, And(Entity Exists(Current Array Element),
						And(Has Spawned(Current Array Element), Is Alive(Current Array Element))))))));
					If(Global.PemainAktif.KursorTeleportasi == 1);
					Else If(And(Global.PemainAktif.CalonTargetTeleportasi != Null, Array Contains(Global.PemainAktif.DaftarTargetTeleportasi, Global.PemainAktif.CalonTargetTeleportasi)));
						Set Player Variable(Global.PemainAktif, KursorTeleportasi, Index Of Array Value(Global.PemainAktif.DaftarTargetTeleportasi, Global.PemainAktif.CalonTargetTeleportasi));
					Else If(Global.PemainAktif.KursorTeleportasi >= Count Of(Global.PemainAktif.DaftarTargetTeleportasi));
						Set Player Variable(Global.PemainAktif, KursorTeleportasi, 0);
					End;
				End;
			End;
		End;
		Global.PemainAktif = Null;
		Wait(1, Ignore Condition);
		Loop If Condition Is True;
	}
}

rule("04j - Global-first: Menit lobi terpusat 10 detik")
{
	event
	{
		Ongoing - Global;
	}

	conditions
	{
		Global.Siap == True;
	}

	actions
	{
		For Global Variable(IndeksPemainGlobal, 0, Count Of(Global.PemainManusia) - 1, 1);
			Global.PemainAktif = Global.PemainManusia[Global.IndeksPemainGlobal];
			If(And(Global.PemainAktif.Manusia == True, Entity Exists(Global.PemainAktif)));
				Set Player Variable(Global.PemainAktif, MenitLobi, Max(0, Round To Integer((Total Time Elapsed - Global.PemainAktif.WaktuMasuk) / 60, Down)));
			End;
		End;
		Global.PemainAktif = Null;
		Wait(10, Ignore Condition);
		Loop If Condition Is True;
	}
}

rule("04k - Global-first: Inspeksi aktif terpusat 4 Hz")
{
	event
	{
		Ongoing - Global;
	}

	conditions
	{
		Global.Siap == True;
	}

	actions
	{
		For Global Variable(IndeksPemainGlobal, 0, Count Of(Global.PemainManusia) - 1, 1);
			Global.PemainAktif = Global.PemainManusia[Global.IndeksPemainGlobal];
			If(And(Global.PemainAktif.InspeksiAktif == True, And(Entity Exists(Global.PemainAktif), And(Is Alive(Global.PemainAktif) == True,
				And(Global.PemainAktif.MenuTerbuka == False, Is Button Held(Global.PemainAktif, Button(Crouch)) == True)))));
				Set Player Variable(Global.PemainAktif, DaftarTargetInspeksi, Filtered Array(All Players(All Teams), And(Current Array Element != Global.PemainAktif,
					And(Entity Exists(Current Array Element), And(Has Spawned(Current Array Element), Is Alive(Current Array Element))))));
				If(Count Of(Global.PemainAktif.DaftarTargetInspeksi) == 0);
					Set Player Variable(Global.PemainAktif, TargetInspeksi, Null);
				Else;
					Set Player Variable(Global.PemainAktif, TargetInspeksi, First Of(Sorted Array(Global.PemainAktif.DaftarTargetInspeksi,
						Angle Between Vectors(Facing Direction Of(Global.PemainAktif), Direction Towards(Eye Position(Global.PemainAktif), Eye Position(Current Array Element))))));
				End;
			End;
		End;
		Global.PemainAktif = Null;
		Wait(0.250, Ignore Condition);
		Loop If Condition Is True;
	}
}

'''
source = replace_exact(source, 'rule("05 - Menu: Tahan serangan jarak dekat 0,5 detik untuk buka atau tutup")', global_pollers + 'rule("05 - Menu: Tahan serangan jarak dekat 0,5 detik untuk buka atau tutup")')

# The camera can start immediately after the intentional 0.5 s hold. TargetKamera
# is already assigned; the extra frame yield served no dependency.
def remove_camera_frame_wait(block: str) -> str:
    return replace_exact(
        block,
        "\t\t\tEvent Player.TargetKamera = Event Player;\n\t\t\tWait(0.016, Ignore Condition);\n\t\t\tEvent Player.ModeKamera = 1;",
        "\t\t\tEvent Player.TargetKamera = Event Player;\n\t\t\tEvent Player.ModeKamera = 1;",
    )


source = edit_rule(source, "12c - Kamera: Tahan Interact setengah detik untuk beralih di luar menu", remove_camera_frame_wait)

# Workshop For Variable stop is inclusive. Count Of(...) was one slot too far in
# vote and cleanup loops; use Count-1 consistently with the main global managers.
source = replace_exact(
    source,
    "For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia), 1);",
    "For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia) - 1, 1);",
    expected=2,
)
source = replace_exact(
    source,
    "For Global Variable(IndeksPembersihan, 0, Count Of(Global.PemainManusia), 1);",
    "For Global Variable(IndeksPembersihan, 0, Count Of(Global.PemainManusia) - 1, 1);",
)

# BersihkanPemain used shared Global scratch variables after several yields. Two
# simultaneous leaves/team switches could therefore overwrite each other's
# IndeksKeluar/PemainPembersihan. Keep exactly one yield before the shared
# critical section, and none after the first scratch assignment.
def make_cleanup_atomic(block: str) -> str:
    waits = block.count("\t\tWait(0.016, Ignore Condition);\n")
    if waits < 7:
        raise RuntimeError(f"unexpected cleanup wait count: {waits}")
    block = block.replace("\t\tWait(0.016, Ignore Condition);\n", "")
    marker = "\t\tGlobal.IndeksKeluar = Index Of Array Value(Global.PemainManusia, Event Player);"
    replacement = (
        "\t\t\"Satu yield sebelum bagian kritis; setelah scratch Global dipakai, cleanup harus atomik tanpa Wait.\"\n"
        "\t\tWait(0.016, Ignore Condition);\n" + marker
    )
    return replace_exact(block, marker, replacement)


source = edit_rule(source, "93c - Subrutin: Bersihkan pemain saat keluar atau pindah tim", make_cleanup_atomic)

SOURCE.write_text(source, encoding="utf-8")
new_blob = git_blob_sha(source)

# Versioned static gate: pin the exact source produced above and encode the new
# Global-first invariants so future patches cannot silently regress them.
validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_exact(validator, '"""Static gate for CHILL Dedicated Server 0.7.0 Global-first."""', '"""Static gate for CHILL Dedicated Server 0.7.1 Global-first."""')
validator = replace_exact(validator, 'CURRENT_VERSION = "0.7.0"', f'CURRENT_VERSION = "{NEW_VERSION}"')
validator = replace_exact(validator, f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"', f'EXPECTED_SOURCE_BLOB = "{new_blob}"')
validator = replace_exact(validator, '        "19f - Teleportasi Jongkok:", "19g - Teleportasi Jongkok:",\n', '        "19g - Teleportasi Jongkok:",\n')

validator_insert = '''    periodic_global = ("04i - Global-first:", "04j - Global-first:", "04k - Global-first:")\n    for prefix in periodic_global:\n        rule = find_rule(rules, prefix)\n        checks.require(rule is not None, f"scheduler globale periodico assente: {prefix}")\n        if rule:\n            checks.equal(event_type(rule), "Ongoing - Global", f"{prefix}: scheduler")\n            checks.require("For Global Variable(IndeksPemainGlobal" in rule.body, f"{prefix}: loop globale assente")\n            checks.require("Global.PemainAktif = Global.PemainManusia[Global.IndeksPemainGlobal]" in rule.body, f"{prefix}: contesto umano globale assente")\n    for prefix in ("02c - Ruang Muncul:", "03 - Waktu:", "07b - Menu kamera:", "07c - Menu Balas Dendam:",\n                   "14 - Intip Pahlawan:", "16 - Kamera:", "19f - Teleportasi Jongkok:"):\n        checks.require(find_rule(rules, prefix) is None, f"poller per-player legacy ancora presente: {prefix}")\n'''
validator = replace_exact(
    validator,
    '    checks.require("Global.PemainAktif.InteraksiKameraDipakai = False;" not in source, "release Camera non deve essere nel manager globale")\n',
    validator_insert + '    checks.require("Global.PemainAktif.InteraksiKameraDipakai = False;" not in source, "release Camera non deve essere nel manager globale")\n',
)
validator = replace_exact(
    validator,
    '    if camera_toggle:\n        checks.require("Wait(0.500, Abort When False);" in camera_toggle.body, "hold Camera 0,5 s assente")\n',
    '    if camera_toggle:\n        checks.require("Wait(0.500, Abort When False);" in camera_toggle.body, "hold Camera 0,5 s assente")\n        checks.require("Wait(0.016, Ignore Condition);" not in camera_toggle.body, "Camera mantiene un frame Wait superfluo")\n    lifecycle = find_rule(rules, "04h - Global-first:")\n    if lifecycle:\n        checks.require("Is Alive(Global.PemainAktif.TargetKamera) == False" in lifecycle.body, "Camera globale non rilascia target morto")\n',
)
validator = replace_exact(
    validator,
    '    join = find_rule(rules, "01 - Pemain Masuk")\n    leave = find_rule(rules, "04 - Pemain Keluar")\n',
    '    classifier = find_rule(rules, "02 - Pemain:")\n    if classifier:\n        checks.require("Is Dummy Bot(Event Player) == False;" in classifier.body, "classifier umano non esclude i dummy diretti")\n    join = find_rule(rules, "01 - Pemain Masuk")\n    leave = find_rule(rules, "04 - Pemain Keluar")\n',
)
validator = replace_exact(
    validator,
    '    if leave:\n        checks.require("Call Subroutine(TenangkanPemain);" in leave.body and "Call Subroutine(BersihkanPemain);" in leave.body, "Leave lifecycle incompleto")\n    return checks\n',
    '    if leave:\n        checks.require("Call Subroutine(TenangkanPemain);" in leave.body and "Call Subroutine(BersihkanPemain);" in leave.body, "Leave lifecycle incompleto")\n        checks.require("Is Dummy Bot(Event Player) == False;" in leave.body, "Leave umano non esclude dummy diretti")\n    checks.require("For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia), 1);" not in source, "loop voto fuori limite Count anziché Count-1")\n    checks.require("For Global Variable(IndeksPembersihan, 0, Count Of(Global.PemainManusia), 1);" not in source, "loop cleanup fuori limite Count anziché Count-1")\n    cleanup = find_rule(rules, "93c - Subrutin:")\n    if cleanup:\n        checks.equal(cleanup.body.count("Wait(0.016, Ignore Condition);"), 1, "yield cleanup")\n        critical = cleanup.body[cleanup.body.index("Global.IndeksKeluar = Index Of Array Value"): ]\n        checks.require("Wait(" not in critical, "cleanup usa Wait mentre scratch Global condiviso è attivo")\n    return checks\n',
)
VALIDATOR.write_text(validator, encoding="utf-8")

# Unit tests for the new architectural guarantees.
tests = TESTS.read_text(encoding="utf-8")
tests = tests.replace("class GlobalFirst070Tests", "class GlobalFirst071Tests", 1)
extra_tests = '''    def test_periodic_pollers_are_global(self) -> None:\n        for prefix in ("04i - Global-first:", "04j - Global-first:", "04k - Global-first:"):\n            start = self.source.index(f'rule("{prefix}')\n            pos = self.source.index("Ongoing - Global;", start)\n            mutated = self.source[:pos] + self.source[pos:].replace("Ongoing - Global;", "Ongoing - Each Player;", 1)\n            self.assertTrue(any(prefix in error and "scheduler" in error for error in self.errors(mutated)))\n\n    def test_cleanup_critical_section_has_no_wait(self) -> None:\n        mutated = self.source.replace(\n            "Global.IndeksKeluar = Index Of Array Value(Global.PemainManusia, Event Player);",\n            "Global.IndeksKeluar = Index Of Array Value(Global.PemainManusia, Event Player);\\n\\t\\tWait(0.016, Ignore Condition);",\n            1,\n        )\n        self.assertTrue(any("scratch Global" in error for error in self.errors(mutated)))\n\n    def test_vote_loop_count_stop_is_rejected(self) -> None:\n        mutated = self.source.replace(\n            "For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia) - 1, 1);",\n            "For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia), 1);",\n            1,\n        )\n        self.assertTrue(any("fuori limite" in error for error in self.errors(mutated)))\n\n'''
tests = replace_exact(tests, "    def test_live_confirmed_blob_is_pinned(self) -> None:\n", extra_tests + "    def test_live_confirmed_blob_is_pinned(self) -> None:\n")
TESTS.write_text(tests, encoding="utf-8")

VERSION.write_text(NEW_VERSION + "\n", encoding="utf-8")

readme = README.read_text(encoding="utf-8")
readme = readme.replace("0.6.25", NEW_VERSION)
readme = readme.replace("33 unit test + validatore Workshop", "unit test + validatore Workshop")
readme += f'''\n\n### Audit {NEW_VERSION} — 6v6 / 12 player Global-first\n\n- Cache Spawn Room, refresh passivi Camera/Revenge/Teleport e inspection sono schedulati da regole `Ongoing - Global`, non da un loop periodico per ogni player.\n- Il contatore minuti è un singolo job globale ogni 10 s. Gli input (Menu, hold/release Camera e Teleport) restano `Ongoing - Each Player` perché dipendono dal contesto/latch del singolo client.\n- I dummy bot diretti non attraversano più il classifier/cleanup umano; `03c` + `KunciBot` restano il percorso riservato Bot/Dummy.\n- La Camera spectate torna alla visuale normale anche se il target muore o non è più spawnato; il frame `Wait(0.016)` all'attivazione self-camera è stato rimosso.\n- I loop voto/cleanup usano `Count Of(...) - 1`, coerentemente con lo stop inclusivo di `For Global Variable`.\n- `BersihkanPemain` mantiene un solo yield prima della sezione critica e nessun `Wait` dopo l'uso degli scratch Global, evitando interleaving tra leave/cambi squadra simultanei.\n- I due `Wait(0.050)` del Join/Team Switch e il `Wait(0.050)` del Player Left restano intenzionali: separano gli eventi engine di leave/join durante un cambio squadra.\n\nLa validazione resta **statica**: import reale, resa HUD e stress effettivo 12-client vanno comunque confermati nel client Overwatch.\n'''
README.write_text(readme, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
project = project.replace("0.6.25", NEW_VERSION)
project = project.replace("33 unit test", "unit test")
project = project.replace("inspection a **5 Hz**", "inspection a **4 Hz**")
project = project.replace("Un solo loop globale a 10 Hz aggiorna `Global.RGB`", "Un solo loop globale a 8 Hz aggiorna `Global.RGB`")
project = project.replace("L'incremento è +3 su 1530 step", "L'incremento è +3,75 su 1530 step")
project = project.replace(
    "3. Move Speed e Knockback Received passano a 0 e parte `Start Forcing Player Position`;",
    "3. Move Speed passa a 0; il knockback resta normale e la posizione non viene forzata;",
)
project = project.replace(
    "Il cleanup su morte, leave e cambio team interrompe il chase, ferma il forcing, ripristina Move Speed/Knockback Received a 100 e distrugge entrambi gli effetti.",
    "Il cleanup su morte, leave e cambio team interrompe il chase, ripristina Move Speed a 100 e distrugge entrambi gli effetti.",
)
project += f'''\n\n## Audit {NEW_VERSION} — 6v6 / 12 player Global-first\n\nI poll periodici che non richiedono un `Event Player` di input sono stati consolidati: `04i` gestisce a 1 Hz Spawn Room e liste passive Camera/Revenge/Teleport, `04j` aggiorna i minuti ogni 10 s e `04k` aggiorna l'inspection a 4 Hz. Le regole per input, latch e azioni che richiedono realmente il contesto del player restano `Ongoing - Each Player`.\n\nIl lifecycle Bot/Dummy è separato dal percorso umano: i dummy diretti non passano dal classifier né dal cleanup umano e vengono mantenuti da `03c`/`KunciBot`. Il cleanup umano usa un solo yield prima della sezione critica; dopo l'assegnazione degli scratch Global non contiene `Wait`, così due leave/cambi squadra ravvicinati non possono sovrascrivere gli indici condivisi a metà cleanup.\n\nLa Camera spectate viene rilasciata anche su target morto/non spawnato. I loop `For Global Variable` di voto e pulizia sono inoltre limitati a `Count Of(...) - 1`.\n'''
PROJECT.write_text(project, encoding="utf-8")

print(f"patched {NEW_VERSION}: {OLD_BLOB} -> {new_blob}")
