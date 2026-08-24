from pathlib import Path

path = Path(__file__).resolve().parent / "chatgpt_global_first_team_switch.py"
text = path.read_text(encoding="utf-8")

replacements = {
    '01 - Lifecycle tim: Worker cleanup dari scheduler global': '01 - Siklus tim: Pekerja pembersihan dari penjadwal global',
    '01b - Lifecycle tim: Worker setup dari scheduler global': '01b - Siklus tim: Pekerja penyiapan dari penjadwal global',
    '04 - Pemain Keluar: Cleanup hanya jika benar-benar keluar': '04 - Pemain Keluar: Bersihkan hanya saat benar-benar keluar',
}
for old, new in replacements.items():
    if old not in text:
        raise SystemExit(f"missing rule title: {old}")
    text = text.replace(old, new)

old = '''    def slim_quiet(block: str) -> str:
        token = "\\t\\tCall Subroutine(PulihkanNasibPemain);\\n"
        if block.count(token) != 1:
            raise RuntimeError("quiet luck reset call mismatch")
        return block.replace(token, "", 1)
'''
new = '''    def slim_quiet(block: str) -> str:
        token = "\\t\\tCall Subroutine(PulihkanNasibPemain);\\n"
        if block.count(token) != 1:
            raise RuntimeError("quiet luck reset call mismatch")
        lightweight = (
            "\\t\\tIf(Event Player.IkonKartuNasib != Null);\\n"
            "\\t\\t\\tDestroy Icon(Event Player.IkonKartuNasib);\\n"
            "\\t\\tEnd;\\n"
            "\\t\\tEvent Player.IkonKartuNasib = Null;\\n"
            "\\t\\tStop Accelerating(Event Player);\\n"
            "\\t\\tSet Move Speed(Event Player, 100);\\n"
            "\\t\\tEvent Player.WaktuPaksaBerikut = 0;\\n"
            "\\t\\tEvent Player.WaktuPaksaBerakhir = 0;\\n"
        )
        return block.replace(token, lightweight, 1)
'''
if text.count(old) != 1:
    raise SystemExit(f"slim_quiet block mismatch: {text.count(old)}")
text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
print("Updated lifecycle patcher with lightweight quiet cleanup and Indonesian rule titles")
