from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
TESTS = ROOT / "tests" / "test_validate_workshop.py"

OLD_BLOB = "a17b1bcb4ffd75e9613b87a44d1c95f153c47727"


def blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def replace_exact(text: str, old: str, new: str, count: int = 1) -> str:
    actual = text.count(old)
    if actual != count:
        raise RuntimeError(f"expected {count} occurrence(s), found {actual}: {old[:180]!r}")
    return text.replace(old, new)


def bounds(text: str, title: str) -> tuple[int, int]:
    start = text.index(f'rule("{title}")')
    end = text.find('\nrule("', start + 1)
    return start, len(text) if end < 0 else end


def replace_rule(text: str, title: str, block: str) -> str:
    start, end = bounds(text, title)
    return text[:start] + block.rstrip() + "\n" + text[end:]


def edit_rule(text: str, title: str, editor) -> str:
    start, end = bounds(text, title)
    block = text[start:end]
    changed = editor(block)
    if changed == block:
        raise RuntimeError(f"rule not changed: {title}")
    return text[:start] + changed + text[end:]


source = SOURCE.read_text(encoding="utf-8")
if blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch moving target")

old_vote = '''\t\tElse;\n\t\t\tIf(Count Of(Global.PemainManusia) > 0);\n\t\t\t\tEvent Player.KursorPilihan %= Count Of(Global.PemainManusia);\n\t\t\t\tIf(Event Player.PemainDipilih != Global.PemainManusia[Event Player.KursorPilihan]);\n\t\t\t\t\tEvent Player.PemainDipilih = Null;\n\t\t\t\t\tEvent Player.PemainDipilih = Global.PemainManusia[Event Player.KursorPilihan];\n\t\t\t\t\tCall Subroutine(HitungPilihan);\n\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Vote registered for {0}.", Event Player.PemainDipilih) : Event Player.IndeksBahasa == 1 ? Custom String("Pilihan untuk {0} tersimpan.", Event Player.PemainDipilih) : Custom String("โหวตให้ {0} แล้ว", Event Player.PemainDipilih));\n\t\t\t\tEnd;\n\t\t\tEnd;\n\t\t\tCall Subroutine(GambarMenu);\n\t\tEnd;'''

new_vote = '''\t\tElse;\n\t\t\tIf(Count Of(Global.PemainManusia) > 0);\n\t\t\t\tEvent Player.KursorPilihan %= Count Of(Global.PemainManusia);\n\t\t\t\tIf(Event Player.PemainDipilih != Global.PemainManusia[Event Player.KursorPilihan]);\n\t\t\t\t\t"Satu player = satu vote aktif. Vote lama dikurangi sebelum vote baru ditambah; self-vote sah."\n\t\t\t\t\tIf(And(Event Player.PemainDipilih != Null, Array Contains(Global.PemainManusia, Event Player.PemainDipilih)));\n\t\t\t\t\t\tModify Player Variable(Global.PemainManusia[Index Of Array Value(Global.PemainManusia, Event Player.PemainDipilih)], JumlahSuara, Subtract, 1);\n\t\t\t\t\t\tIf(Global.PemainManusia[Index Of Array Value(Global.PemainManusia, Event Player.PemainDipilih)].JumlahSuara < 0);\n\t\t\t\t\t\t\tSet Player Variable(Global.PemainManusia[Index Of Array Value(Global.PemainManusia, Event Player.PemainDipilih)], JumlahSuara, 0);\n\t\t\t\t\t\tEnd;\n\t\t\t\t\tEnd;\n\t\t\t\t\tEvent Player.PemainDipilih = Global.PemainManusia[Event Player.KursorPilihan];\n\t\t\t\t\tModify Player Variable(Global.PemainManusia[Event Player.KursorPilihan], JumlahSuara, Add, 1);\n\t\t\t\t\tCall Subroutine(HitungPilihan);\n\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Vote registered for {0}.", Event Player.PemainDipilih) : Event Player.IndeksBahasa == 1 ? Custom String("Pilihan untuk {0} tersimpan.", Event Player.PemainDipilih) : Custom String("โหวตให้ {0} แล้ว", Event Player.PemainDipilih));\n\t\t\t\tEnd;\n\t\t\tEnd;\n\t\t\tCall Subroutine(GambarMenu);\n\t\tEnd;'''
source = replace_exact(source, old_vote, new_vote)

# Range Stop in Workshop For loops is exclusive. Count is therefore the correct stop for indices 0..Count-1.
source = replace_rule(source, "91p - Subrutin: Hitung ulang pilihan dan pemimpin tunggal", r'''rule("91p - Subrutin: Hitung ulang pilihan dan pemimpin tunggal")
{
	event
	{
		Subroutine;
		HitungPilihan;
	}

	actions
	{
		"JumlahSuara diperbarui langsung saat vote berubah; subroutine ini hanya mencari leader unik. Range Stop For bersifat eksklusif."
		Global.PemimpinSuara = Null;
		Global.SuaraTerbanyak = 0;
		Global.SuaraSeri = False;
		For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia), 1);
			If(Global.PemainManusia[Global.IndeksVote].JumlahSuara > Global.SuaraTerbanyak);
				Global.SuaraTerbanyak = Global.PemainManusia[Global.IndeksVote].JumlahSuara;
				Global.PemimpinSuara = Global.PemainManusia[Global.IndeksVote];
				Global.SuaraSeri = False;
			Else If(And(Global.PemainManusia[Global.IndeksVote].JumlahSuara == Global.SuaraTerbanyak, Global.SuaraTerbanyak > 0));
				Global.SuaraSeri = True;
			End;
		End;
		If(Or(Global.SuaraTerbanyak <= 0, Global.SuaraSeri == True));
			Global.PemimpinSuara = Null;
		End;
	}
}''')

# Remove the departing player's outgoing vote before clearing their selected target.
source = replace_exact(
    source,
    '''\t\tEnable Game Mode HUD(Event Player);\n\t\tEnable Game Mode In-World UI(Event Player);\n\t\tEvent Player.PemainDipilih = Null;\n\t\tEvent Player.JumlahSuara = 0;''',
    '''\t\tEnable Game Mode HUD(Event Player);\n\t\tEnable Game Mode In-World UI(Event Player);\n\t\tIf(And(Event Player.PemainDipilih != Null, And(Event Player.PemainDipilih != Event Player, Array Contains(Global.PemainManusia, Event Player.PemainDipilih))));\n\t\t\tModify Player Variable(Global.PemainManusia[Index Of Array Value(Global.PemainManusia, Event Player.PemainDipilih)], JumlahSuara, Subtract, 1);\n\t\t\tIf(Global.PemainManusia[Index Of Array Value(Global.PemainManusia, Event Player.PemainDipilih)].JumlahSuara < 0);\n\t\t\t\tSet Player Variable(Global.PemainManusia[Index Of Array Value(Global.PemainManusia, Event Player.PemainDipilih)], JumlahSuara, 0);\n\t\t\tEnd;\n\t\tEnd;\n\t\tEvent Player.PemainDipilih = Null;\n\t\tEvent Player.JumlahSuara = 0;''')

# The cleanup loop that clears votes pointing at a departed player must also use exclusive stop Count.
def fix_cleanup_vote_loop(block: str) -> str:
    old = '''\t\tFor Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia) - 1, 1);\n\t\t\tIf(Global.PemainManusia[Global.IndeksVote].PemainDipilih == Global.PemainPembersihan);'''
    new = '''\t\tFor Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia), 1);\n\t\t\tIf(Global.PemainManusia[Global.IndeksVote].PemainDipilih == Global.PemainPembersihan);'''
    return replace_exact(block, old, new)

source = edit_rule(source, "93c - Subrutin: Bersihkan pemain saat keluar atau pindah tim", fix_cleanup_vote_loop)

SOURCE.write_text(source, encoding="utf-8")
new_blob = blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_exact(validator, f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"', f'EXPECTED_SOURCE_BLOB = "{new_blob}"')

# Remove the old backwards guard that treated Count as out-of-range for vote loops.
validator = replace_exact(
    validator,
    '    checks.require("For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia), 1);" not in source, "loop voto fuori limite Count anziché Count-1")\n',
    '')

old_checks = '''    if vote_count:\n        checks.require("Set Player Variable(Global.PemainManusia[Global.IndeksVote], JumlahSuara, 0);" in vote_count.body, "conteggio voti non azzera JumlahSuara prima del recount")\n        checks.require("Modify Player Variable(Global.PemainManusia[Global.IndeksVote], JumlahSuara, Add, 1);" in vote_count.body, "conteggio voti non incrementa direttamente il candidato")\n        checks.require("For Global Variable(IndeksPemilihVote" in vote_count.body, "conteggio voti non usa il doppio ciclo candidato/votante")\n        checks.require("Modify Player Variable(Player Variable(" not in vote_count.body, "conteggio voti usa ancora un player-target indiretto fragile")\n        checks.require("Count Of(Filtered Array(Global.PemainManusia, Player Variable(Current Array Element, PemainDipilih)" not in vote_count.body, "conteggio voti usa ancora il Filtered Array fragile")\n        checks.require("Array Contains(Global.PemainManusia" in vote_count.body, "conteggio voti non valida più il target votato")'''
new_checks = '''    if vote_count:\n        checks.require("Set Player Variable(" not in vote_count.body and "Modify Player Variable(" not in vote_count.body, "HitungPilihan non deve più ricontare o modificare i voti")\n        checks.require("For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia), 1);" in vote_count.body, "loop leader voto deve usare Range Stop Count perché lo stop è esclusivo")\n        checks.require("Global.PemainManusia[Global.IndeksVote].JumlahSuara > Global.SuaraTerbanyak" in vote_count.body, "HitungPilihan non calcola il leader dai contatori transazionali")\n    if interact:\n        checks.require("Modify Player Variable(Global.PemainManusia[Event Player.KursorPilihan], JumlahSuara, Add, 1);" in interact.body, "voto non incrementa direttamente il nuovo target")\n        checks.require("Index Of Array Value(Global.PemainManusia, Event Player.PemainDipilih)" in interact.body, "cambio voto non trova e decrementa il vecchio target")\n        checks.require("Event Player.PemainDipilih = Global.PemainManusia[Event Player.KursorPilihan];" in interact.body, "voto singolo non salva il nuovo target")'''
validator = replace_exact(validator, old_checks, new_checks)

# Cleanup vote-reference loop must also include the last player.
validator = replace_exact(
    validator,
    '''    if cleanup:\n        checks.equal(cleanup.body.count("Wait(0.016, Ignore Condition);"), 1, "yield cleanup")''',
    '''    if cleanup:\n        checks.require("For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia), 1);" in cleanup.body, "cleanup voti usa ancora Count-1 con Range Stop esclusivo")\n        checks.equal(cleanup.body.count("Wait(0.016, Ignore Condition);"), 1, "yield cleanup")''')
VALIDATOR.write_text(validator, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
old_test = '''    def test_vote_loop_count_stop_is_rejected(self) -> None:\n        mutated = self.source.replace(\n            "For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia) - 1, 1);",\n            "For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia), 1);",\n            1,\n        )\n        self.assertTrue(any("fuori limite" in error for error in self.errors(mutated)))'''
new_test = '''    def test_vote_loop_count_minus_one_stop_is_rejected(self) -> None:\n        start = self.source.index('rule("91p - Subrutin:')\n        pos = self.source.index("For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia), 1);", start)\n        mutated = self.source[:pos] + self.source[pos:].replace(\n            "For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia), 1);",\n            "For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia) - 1, 1);",\n            1,\n        )\n        self.assertTrue(any("Range Stop Count" in error for error in self.errors(mutated)))'''
tests = replace_exact(tests, old_test, new_test)
TESTS.write_text(tests, encoding="utf-8")

print(f"transactional single-choice votes + exclusive loop bound fix: {OLD_BLOB} -> {new_blob}")
