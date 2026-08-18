from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"

OLD_BLOB = "2ed0e0eadf56367719d3065493ebd6078c3f7ffc"


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


source = SOURCE.read_text(encoding="utf-8")
if git_blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch a moving target")

source = replace_exact(
    source,
    "\t\t52: IndeksPemainGlobal\n",
    "\t\t52: IndeksPemainGlobal\n\t\t53: IndeksPemilihVote\n",
)

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

		"Buang referensi vote yang sudah tidak menunjuk manusia aktif."
		For Global Variable(IndeksPemilihVote, 0, Count Of(Global.PemainManusia) - 1, 1);
			If(And(Player Variable(Global.PemainManusia[Global.IndeksPemilihVote], PemainDipilih) != Null, Array Contains(Global.PemainManusia,
				Player Variable(Global.PemainManusia[Global.IndeksPemilihVote], PemainDipilih)) == False));
				Set Player Variable(Global.PemainManusia[Global.IndeksPemilihVote], PemainDipilih, Null);
			End;
		End;

		"Recount deterministico: candidato esterno, votanti interni. L'incremento colpisce sempre direttamente il candidato dell'array."
		For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia) - 1, 1);
			Set Player Variable(Global.PemainManusia[Global.IndeksVote], JumlahSuara, 0);
			For Global Variable(IndeksPemilihVote, 0, Count Of(Global.PemainManusia) - 1, 1);
				If(Player Variable(Global.PemainManusia[Global.IndeksPemilihVote], PemainDipilih) == Global.PemainManusia[Global.IndeksVote]);
					Modify Player Variable(Global.PemainManusia[Global.IndeksVote], JumlahSuara, Add, 1);
				End;
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

SOURCE.write_text(source, encoding="utf-8")
new_blob = git_blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_exact(
    validator,
    f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"',
    f'EXPECTED_SOURCE_BLOB = "{new_blob}"',
)
validator = replace_exact(
    validator,
    'for name in ("PemainAktif", "IndeksPemainGlobal"):',
    'for name in ("PemainAktif", "IndeksPemainGlobal", "IndeksPemilihVote"):',
)
validator = replace_exact(
    validator,
    '        checks.require("Modify Player Variable(Player Variable(Global.PemainManusia[Global.IndeksVote], PemainDipilih), JumlahSuara, Add, 1);" in vote_count.body, "conteggio voti non incrementa direttamente il player votato")\n        checks.require("Count Of(Filtered Array(Global.PemainManusia, Player Variable(Current Array Element, PemainDipilih)" not in vote_count.body, "conteggio voti usa ancora il Filtered Array fragile")\n        checks.require("Array Contains(Global.PemainManusia" in vote_count.body, "conteggio voti non valida più il target votato")',
    '        checks.require("For Global Variable(IndeksPemilihVote, 0, Count Of(Global.PemainManusia) - 1, 1);" in vote_count.body, "conteggio voti non scorre esplicitamente i votanti")\n        checks.require("Modify Player Variable(Global.PemainManusia[Global.IndeksVote], JumlahSuara, Add, 1);" in vote_count.body, "conteggio voti non incrementa direttamente il candidato")\n        checks.require("Modify Player Variable(Player Variable(" not in vote_count.body, "conteggio voti usa ancora un player-target indiretto")\n        checks.require("Count Of(Filtered Array(Global.PemainManusia, Player Variable(Current Array Element, PemainDipilih)" not in vote_count.body, "conteggio voti usa ancora il Filtered Array fragile")\n        checks.require("Array Contains(Global.PemainManusia" in vote_count.body, "conteggio voti non valida più il target votato")',
)
validator = replace_exact(
    validator,
    '    checks.require("For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia), 1);" not in source, "loop voto fuori limite Count anziché Count-1")',
    '    checks.require("For Global Variable(IndeksVote, 0, Count Of(Global.PemainManusia), 1);" not in source, "loop voto fuori limite Count anziché Count-1")\n    checks.require("For Global Variable(IndeksPemilihVote, 0, Count Of(Global.PemainManusia), 1);" not in source, "loop votanti fuori limite Count anziché Count-1")',
)
VALIDATOR.write_text(validator, encoding="utf-8")

print(f"fixed direct vote recount: {OLD_BLOB} -> {new_blob}")
