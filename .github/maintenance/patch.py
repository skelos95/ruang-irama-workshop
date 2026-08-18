from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"

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


source = SOURCE.read_text(encoding="utf-8")
if blob_sha(source) != OLD_BLOB:
    raise RuntimeError("unexpected Workshop blob; refusing to patch moving target")

old_vote = '''\t\tElse;\n\t\t\tIf(Count Of(Global.PemainManusia) > 0);\n\t\t\t\tEvent Player.KursorPilihan %= Count Of(Global.PemainManusia);\n\t\t\t\tIf(Event Player.PemainDipilih != Global.PemainManusia[Event Player.KursorPilihan]);\n\t\t\t\t\tEvent Player.PemainDipilih = Null;\n\t\t\t\t\tEvent Player.PemainDipilih = Global.PemainManusia[Event Player.KursorPilihan];\n\t\t\t\t\tCall Subroutine(HitungPilihan);\n\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Vote registered for {0}.", Event Player.PemainDipilih) : Event Player.IndeksBahasa == 1 ? Custom String("Pilihan untuk {0} tersimpan.", Event Player.PemainDipilih) : Custom String("โหวตให้ {0} แล้ว", Event Player.PemainDipilih));\n\t\t\t\tEnd;\n\t\t\tEnd;\n\t\t\tCall Subroutine(GambarMenu);\n\t\tEnd;'''

new_vote = '''\t\tElse;\n\t\t\tIf(Count Of(Global.PemainManusia) > 0);\n\t\t\t\tEvent Player.KursorPilihan %= Count Of(Global.PemainManusia);\n\t\t\t\tIf(Event Player.PemainDipilih != Global.PemainManusia[Event Player.KursorPilihan]);\n\t\t\t\t\t"Un player possiede un solo voto attivo: togli il precedente, salva il nuovo e aggiungi esattamente un voto. Self-vote consentito."\n\t\t\t\t\tIf(And(Event Player.PemainDipilih != Null, Array Contains(Global.PemainManusia, Event Player.PemainDipilih)));\n\t\t\t\t\t\tModify Player Variable(Global.PemainManusia[Index Of Array Value(Global.PemainManusia, Event Player.PemainDipilih)], JumlahSuara, Subtract, 1);\n\t\t\t\t\t\tIf(Global.PemainManusia[Index Of Array Value(Global.PemainManusia, Event Player.PemainDipilih)].JumlahSuara < 0);\n\t\t\t\t\t\t\tSet Player Variable(Global.PemainManusia[Index Of Array Value(Global.PemainManusia, Event Player.PemainDipilih)], JumlahSuara, 0);\n\t\t\t\t\t\tEnd;\n\t\t\t\t\tEnd;\n\t\t\t\t\tEvent Player.PemainDipilih = Global.PemainManusia[Event Player.KursorPilihan];\n\t\t\t\t\tModify Player Variable(Global.PemainManusia[Event Player.KursorPilihan], JumlahSuara, Add, 1);\n\t\t\t\t\tCall Subroutine(HitungPilihan);\n\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Vote registered for {0}.", Event Player.PemainDipilih) : Event Player.IndeksBahasa == 1 ? Custom String("Pilihan untuk {0} tersimpan.", Event Player.PemainDipilih) : Custom String("โหวตให้ {0} แล้ว", Event Player.PemainDipilih));\n\t\t\t\tEnd;\n\t\t\tEnd;\n\t\t\tCall Subroutine(GambarMenu);\n\t\tEnd;'''
source = replace_exact(source, old_vote, new_vote)

source = replace_rule(source, "91p - Subrutin: Hitung ulang pilihan dan pemimpin tunggal", r'''rule("91p - Subrutin: Hitung ulang pilihan dan pemimpin tunggal")
{
	event
	{
		Subroutine;
		HitungPilihan;
	}

	actions
	{
		"JumlahSuara non viene mai ricostruito qui: è stato transazionale aggiornato esattamente al click del voto."
		Global.PemimpinSuara = Null;
		Global.SuaraTerbanyak = 0;
		Global.SuaraSeri = False;
		If(Count Of(Global.PemainManusia) > 0);
			Global.PemimpinSuara = First Of(Sorted Array(Global.PemainManusia, 0 - Player Variable(Current Array Element, JumlahSuara)));
			Global.SuaraTerbanyak = Player Variable(Global.PemimpinSuara, JumlahSuara);
			If(Global.SuaraTerbanyak > 0);
				Global.SuaraSeri = Count Of(Filtered Array(Global.PemainManusia, Player Variable(Current Array Element, JumlahSuara) == Global.SuaraTerbanyak)) > 1;
				If(Global.SuaraSeri == True);
					Global.PemimpinSuara = Null;
				End;
			Else;
				Global.PemimpinSuara = Null;
			End;
		End;
	}
}''')

# On leave/team switch, remove the player's outgoing vote before clearing PemainDipilih.
source = replace_exact(
    source,
    '''\t\tEnable Game Mode HUD(Event Player);\n\t\tEnable Game Mode In-World UI(Event Player);\n\t\tEvent Player.PemainDipilih = Null;\n\t\tEvent Player.JumlahSuara = 0;''',
    '''\t\tEnable Game Mode HUD(Event Player);\n\t\tEnable Game Mode In-World UI(Event Player);\n\t\tIf(And(Event Player.PemainDipilih != Null, And(Event Player.PemainDipilih != Event Player, Array Contains(Global.PemainManusia, Event Player.PemainDipilih))));\n\t\t\tModify Player Variable(Global.PemainManusia[Index Of Array Value(Global.PemainManusia, Event Player.PemainDipilih)], JumlahSuara, Subtract, 1);\n\t\t\tIf(Global.PemainManusia[Index Of Array Value(Global.PemainManusia, Event Player.PemainDipilih)].JumlahSuara < 0);\n\t\t\t\tSet Player Variable(Global.PemainManusia[Index Of Array Value(Global.PemainManusia, Event Player.PemainDipilih)], JumlahSuara, 0);\n\t\t\tEnd;\n\t\tEnd;\n\t\tEvent Player.PemainDipilih = Null;\n\t\tEvent Player.JumlahSuara = 0;''')

SOURCE.write_text(source, encoding="utf-8")
new_blob = blob_sha(source)

validator = VALIDATOR.read_text(encoding="utf-8")
validator = replace_exact(validator, f'EXPECTED_SOURCE_BLOB = "{OLD_BLOB}"', f'EXPECTED_SOURCE_BLOB = "{new_blob}"')

new_vote_checks = '''    if vote_count:\n        checks.require("Set Player Variable(" not in vote_count.body and "Modify Player Variable(" not in vote_count.body, "HitungPilihan non deve più ricontare o modificare JumlahSuara")\n        checks.require("First Of(Sorted Array(Global.PemainManusia" in vote_count.body, "HitungPilihan non seleziona CHILL STAR dai contatori correnti")\n        checks.require("Count Of(Filtered Array(Global.PemainManusia" in vote_count.body, "HitungPilihan non rileva il pareggio dai contatori correnti")\n    if interact:\n        checks.require("Modify Player Variable(Global.PemainManusia[Event Player.KursorPilihan], JumlahSuara, Add, 1);" in interact.body, "voto non incrementa direttamente il nuovo target")\n        checks.require("Modify Player Variable(Global.PemainManusia[Index Of Array Value(Global.PemainManusia, Event Player.PemainDipilih)], JumlahSuara, Subtract, 1);" in interact.body, "cambio voto non sottrae il voto precedente")\n        checks.require("Event Player.PemainDipilih = Global.PemainManusia[Event Player.KursorPilihan];" in interact.body, "voto singolo non salva il nuovo target")\n        checks.require("If(Event Player.PemainDipilih != Global.PemainManusia[Event Player.KursorPilihan]);" in interact.body, "votare di nuovo lo stesso player non è idempotente")\n'''
pattern = r'    if vote_count:\n.*?(?=    if classifier:\n)'
validator, changed = re.subn(pattern, new_vote_checks, validator, count=1, flags=re.DOTALL)
if changed != 1:
    raise RuntimeError(f"validator vote block replacement mismatch: {changed}")

VALIDATOR.write_text(validator, encoding="utf-8")
print(f"transactional single-choice votes without recount loops: {OLD_BLOB} -> {new_blob}")
