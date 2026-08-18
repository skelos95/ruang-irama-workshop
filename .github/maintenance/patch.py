from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"

OLD_BLOB = "0ad6bd8f555b008e129b3e3525bae0646ac29a4e"


def git_blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def replace_exact(text: str, old: str, new: str, expected: int = 1) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"replacement mismatch: expected {expected}, found {count}: {old[:180]!r}")
    return text.replace(old, new)


def rule_bounds(text: str, title: str) -> tuple[int, int]:
    needle = f'rule("{title}")'
    start = text.index(needle)
    next_rule = text.find('\nrule("', start + len(needle))
    return start, len(text) if next_rule < 0 else next_rule


def replace_rule(text: str, title: str, new_block: str) -> str:
    start, end = rule_bounds(text, title)
    return text[:start] + new_block.rstrip() + "\n" + text[end:]


def edit_rule(text: str, title: str, old: str, new: str) -> str:
    start, end = rule_bounds(text, title)
    block = text[start:end]
    edited = replace_exact(block, old, new)
    return text[:start] + edited + text[end:]


source = SOURCE.read_text(encoding="utf-8")
if git_blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch a moving target")

# Recount votes deterministically. Avoid the live-client fragile Filtered Array
# over another player's player-variable; reset counts, then increment the chosen
# target directly for every voter.
source = replace_rule(source, "91p - Subrutin: Hitung ulang pilihan dan pemimpin tunggal", r'''rule("91p - Subrutin: Hitung ulang pilihan dan pemimpin tunggal")
{
	event
	{
		Subroutine;
		HitungPilihan;
	}

	actions
	{
		Global.PemimpinSuara = Null;
		Global.SuaraTerbanyak = 0;
		Global.SuaraSeri = False;
		For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia) - 1, 1);
			Set Player Variable(Global.PemainManusia[Global.IndeksVote], JumlahSuara, 0);
		End;
		For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia) - 1, 1);
			If(And(Player Variable(Global.PemainManusia[Global.IndeksVote], PemainDipilih) != Null, Array Contains(Global.PemainManusia,
				Player Variable(Global.PemainManusia[Global.IndeksVote], PemainDipilih))));
				Modify Player Variable(Player Variable(Global.PemainManusia[Global.IndeksVote], PemainDipilih), JumlahSuara, Add, 1);
			Else If(Player Variable(Global.PemainManusia[Global.IndeksVote], PemainDipilih) != Null);
				Set Player Variable(Global.PemainManusia[Global.IndeksVote], PemainDipilih, Null);
			End;
		End;
		For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia) - 1, 1);
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

# Joining humans change the candidate set and can invalidate/reorder vote targets;
# always recompute after the player has actually been registered as human.
source = edit_rule(
    source,
    "02 - Pemain: Pisahkan manusia dari pasukan kaleng",
    "\t\tEvent Player.Manusia = True;\n",
    "\t\tEvent Player.Manusia = True;\n\t\tCall Subroutine(HitungPilihan);\n",
)

SOURCE.write_text(source, encoding="utf-8")
new_blob = git_blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_exact(validator, f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"', f'EXPECTED_SOURCE_BLOB = "{new_blob}"')

anchor = '''    checks.require("For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia), 1);" not in source, "loop voto fuori limite Count anziché Count-1")\n'''
addition = anchor + '''    vote_count = find_rule(rules, "91p - Subrutin:")\n    checks.require(vote_count is not None, "subroutine conteggio voti assente")\n    if vote_count:\n        checks.require("Set Player Variable(Global.PemainManusia[Global.IndeksVote], JumlahSuara, 0);" in vote_count.body, "conteggio voti non azzera JumlahSuara prima del recount")\n        checks.require("Modify Player Variable(Player Variable(Global.PemainManusia[Global.IndeksVote], PemainDipilih), JumlahSuara, Add, 1);" in vote_count.body, "conteggio voti non incrementa direttamente il player votato")\n        checks.require("Count Of(Filtered Array(Global.PemainManusia, Player Variable(Current Array Element, PemainDipilih)" not in vote_count.body, "conteggio voti usa ancora il Filtered Array fragile")\n        checks.require("Array Contains(Global.PemainManusia" in vote_count.body, "conteggio voti non valida più il target votato")\n    if classifier:\n        checks.require("Call Subroutine(HitungPilihan);" in classifier.body, "join umano non ricalcola le votazioni")\n'''
validator = replace_exact(validator, anchor, addition)
VALIDATOR.write_text(validator, encoding="utf-8")

print(f"fixed 0.7.2 live vote counting: {OLD_BLOB} -> {new_blob}")
