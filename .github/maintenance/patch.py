from __future__ import annotations

from pathlib import Path
import hashlib
import re

SOURCE = Path("workshop/ruang_irama.workshop")
VALIDATOR = Path("tools/validate_workshop.py")
README = Path("README.md")
PROJECT = Path("docs/PROGETTO.md")
TESTS = Path("docs/TEST.md")
REPORT = Path("docs/VALIDAZIONE.md")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 occurrence, found {count}")
    return text.replace(old, new, 1)


# Keep naming aligned with the new semantics across source/tooling/docs.
rename_paths = (SOURCE, VALIDATOR, README, PROJECT, TESTS, REPORT)
for path in rename_paths:
    text = path.read_text(encoding="utf-8")
    text = text.replace("NamaInspeksiTerlihat", "PrivasiInspeksiAktif")
    text = text.replace("KursorPrivasiNama", "KursorPrivasiInspeksi")
    text = text.replace("GambarPrivasiNama", "GambarPrivasiInspeksi")
    path.write_text(text, encoding="utf-8")

src = SOURCE.read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# Crouch inspection privacy:
# - Privacy OFF: every viewer gets the full row.
# - Privacy ON: enemy viewers get an empty string (no icon/name/health).
# - Same-team viewers always get the full row.
# Bots remain visible because the privacy setting belongs to human players.
# ---------------------------------------------------------------------------
start = src.index('rule("13 - Intip Pahlawan:')
end = src.find('\nrule("', start + 1)
if end < 0:
    raise SystemExit("rule 13 end not found")
block = src[start:end]

old_target_text = '''Event Player.TargetInspeksi == Null ? Custom String("") : Custom String("{0}{1} | {2}",
\t\t\tHero Icon String(Is Duplicating(Event Player.TargetInspeksi) ? Hero Being Duplicated(Event Player.TargetInspeksi) : Hero Of(
\t\t\tEvent Player.TargetInspeksi)), Player Variable(Event Player.TargetInspeksi, Manusia) == True ? Player Variable(Event Player.TargetInspeksi, PrivasiInspeksiAktif) == True ? Custom String(" {0}", Event Player.TargetInspeksi) : Custom String("") : Custom String(" {0}", Event Player.TargetInspeksi), Round To Integer(Health(Event Player.TargetInspeksi), Down))'''
new_target_text = '''Event Player.TargetInspeksi == Null ? Custom String("") : And(Player Variable(Event Player.TargetInspeksi, Manusia) == True, And(
\t\t\tPlayer Variable(Event Player.TargetInspeksi, PrivasiInspeksiAktif) == True, Team Of(Event Player.TargetInspeksi) != Team Of(Event Player))) ? Custom String("")
\t\t\t: Custom String("{0} {1} | {2}", Hero Icon String(Is Duplicating(Event Player.TargetInspeksi) ? Hero Being Duplicated(Event Player.TargetInspeksi) : Hero Of(
\t\t\tEvent Player.TargetInspeksi)), Custom String("{0}", Event Player.TargetInspeksi), Round To Integer(Health(Event Player.TargetInspeksi), Down))'''
block = replace_once(block, old_target_text, new_target_text, "enemy-only complete Crouch privacy")
src = src[:start] + block + src[end:]

replacements = {
    '9 - NAME PRIVACY\\nCURRENT: {0}': '9 - CROUCH PRIVACY\\nCURRENT: {0}',
    'Event Player.PrivasiInspeksiAktif ? Custom String("VISIBLE") : Custom String("HIDDEN")': 'Event Player.PrivasiInspeksiAktif ? Custom String("ON") : Custom String("OFF")',
    '9 - PRIVASI NAMA\\nSAAT INI: {0}': '9 - PRIVASI JONGKOK\\nSAAT INI: {0}',
    'Event Player.PrivasiInspeksiAktif ? Custom String("TERLIHAT") : Custom String("TERSEMBUNYI")': 'Event Player.PrivasiInspeksiAktif ? Custom String("AKTIF") : Custom String("MATI")',
    '9 - ความเป็นส่วนตัวชื่อ\\nสถานะ: {0}': '9 - ความเป็นส่วนตัวตอนย่อ\\nสถานะ: {0}',
    'Event Player.PrivasiInspeksiAktif ? Custom String("แสดง") : Custom String("ซ่อน")': 'Event Player.PrivasiInspeksiAktif ? Custom String("เปิด") : Custom String("ปิด")',
    'rule("91m - Subrutin: Gambar privasi nama saat diintip")': 'rule("91m - Subrutin: Gambar privasi inspeksi dari musuh")',
    '9 - NAME PRIVACY {0}/2\\nOTHERS SEE YOUR NAME: {1}': '9 - CROUCH PRIVACY {0}/2\\nHIDE HUD FROM ENEMIES: {1}',
    '9 - PRIVASI NAMA {0}/2\\nORANG LAIN LIHAT NAMA: {1}': '9 - PRIVASI JONGKOK {0}/2\\nSEMBUNYIKAN HUD DARI MUSUH: {1}',
    '9 - ความเป็นส่วนตัวชื่อ {0}/2\\nคนอื่นเห็นชื่อคุณ: {1}': '9 - ความเป็นส่วนตัวตอนย่อ {0}/2\\nซ่อน HUD จากศัตรู: {1}',
    'Crouch name visible. Others can see you.': 'Crouch privacy enabled. Enemies see nothing.',
    'Nama saat intip terlihat. Pemain lain bisa melihatmu.': 'Privasi Jongkok aktif. Musuh tidak melihat apa pun.',
    'แสดงชื่อเมื่อตรวจแล้ว คนอื่นเห็นชื่อคุณได้': 'เปิดความเป็นส่วนตัวตอนย่อ ศัตรูจะไม่เห็นอะไรเลย',
    'Crouch name hidden. Incognito mode.': 'Crouch privacy disabled. HUD visible to everyone.',
    'Nama saat intip disembunyikan. Mode penyamaran.': 'Privasi Jongkok nonaktif. HUD terlihat oleh semua.',
    'ซ่อนชื่อเมื่อตรวจแล้ว โหมดไม่เปิดเผยตัว': 'ปิดความเป็นส่วนตัวตอนย่อ ทุกคนเห็น HUD ได้',
}
for old, new in replacements.items():
    if old not in src:
        raise SystemExit(f"menu 9 wording anchor missing: {old}")
    src = src.replace(old, new)

SOURCE.write_text(src, encoding="utf-8")

val = VALIDATOR.read_text(encoding="utf-8")
val = val.replace(
    'checks.require("9 - NAME PRIVACY" in source and "9 - PRIVASI NAMA" in source and "9 - ความเป็นส่วนตัวชื่อ" in source, "menu 9 non localizzato EN/ID/TH")',
    'checks.require("9 - CROUCH PRIVACY" in source and "9 - PRIVASI JONGKOK" in source and "9 - ความเป็นส่วนตัวตอนย่อ" in source, "menu 9 non localizzato EN/ID/TH")',
)

old_privacy_checks = '''        checks.require("Player Variable(Event Player.TargetInspeksi, PrivasiInspeksiAktif) == True" in body, "menu 9: nome target non dipende dalla privacy")
        checks.require('Custom String("")' in inspect[0].body, "menu 9: ramo nome nascosto assente")
        checks.require("Hero Icon String" in body and "Health(Event Player.TargetInspeksi)" in body, "menu 9: privacy non deve nascondere eroe o salute")'''
new_privacy_checks = '''        raw = inspect[0].body
        checks.require("Player Variable(Event Player.TargetInspeksi, PrivasiInspeksiAktif) == True" in body, "menu 9: target non dipende dalla privacy")
        checks.require("Team Of(Event Player.TargetInspeksi) != Team Of(Event Player)" in body, "menu 9: privacy non limitata ai viewer nemici")
        checks.require('Custom String("")' in raw, "menu 9: ramo HUD nemico completamente vuoto assente")
        privacy_at = body.find("Player Variable(Event Player.TargetInspeksi, PrivasiInspeksiAktif) == True")
        enemy_at = body.find("Team Of(Event Player.TargetInspeksi) != Team Of(Event Player)", privacy_at)
        checks.require(0 <= privacy_at < enemy_at, "menu 9: controllo privacy/squadra in ordine errato")
        checks.require('Custom String("{0} {1} | {2}"' in raw, "menu 9: HUD completo alleato/pubblico assente")
        full_at = raw.find('Custom String("{0} {1} | {2}"')
        full_segment = raw[full_at:full_at + 900]
        checks.require("Hero Icon String" in full_segment and 'Custom String("{0}", Event Player.TargetInspeksi)' in full_segment and "Health(Event Player.TargetInspeksi)" in full_segment, "menu 9: HUD completo alleato/pubblico deve mantenere icona, nome e salute")'''
if old_privacy_checks not in val:
    raise SystemExit("validator old privacy checks not found")
val = val.replace(old_privacy_checks, new_privacy_checks, 1)

needle = '    checks.require("8 - CROUCH TELEPORT" in source and "8 - TELEPORT JONGKOK" in source and "8 - เทเลพอร์ตตอนย่อ" in source, "menu 8 non localizzato EN/ID/TH")\n'
addition = '''    checks.require("Crouch privacy enabled. Enemies see nothing." in source, "menu 9: feedback EN privacy ON assente")
    checks.require("Privasi Jongkok aktif. Musuh tidak melihat apa pun." in source, "menu 9: feedback ID privacy ON assente")
    checks.require("เปิดความเป็นส่วนตัวตอนย่อ ศัตรูจะไม่เห็นอะไรเลย" in source, "menu 9: feedback TH privacy ON assente")
'''
if addition not in val:
    if needle not in val:
        raise SystemExit("validator localization insertion anchor missing")
    val = val.replace(needle, needle + addition, 1)

VALIDATOR.write_text(val, encoding="utf-8")

readme = README.read_text(encoding="utf-8")
readme = readme.replace('`9 - Name Privacy` — decide se gli altri vedono il tuo nome durante Crouch inspection; default OFF.', '`9 - Crouch Privacy` — quando ON nasconde completamente icona/nome/salute ai nemici durante Crouch inspection; i compagni vedono sempre tutto; default OFF.')
readme = readme.replace('| 9 | Name Privacy | OFF / ON, default OFF |', '| 9 | Crouch Privacy | OFF / ON; ON nasconde tutto ai nemici, alleati sempre visibili |')
README.write_text(readme, encoding="utf-8")

project = PROJECT.read_text(encoding="utf-8")
project = project.replace('| 9 | Name Privacy | mostra/nasconde il proprio nome agli altri, default OFF |', '| 9 | Crouch Privacy | ON nasconde l’intero HUD inspection ai nemici; alleati sempre completi; default OFF |')
old_para = '`Menu 9 - Name Privacy` usa `PrivasiInspeksiAktif`: OFF di default. Quando è OFF, gli altri viewer che ispezionano quel player con Crouch vedono ancora icona eroe e salute ma ricevono una stringa nome vuota; quando è ON vedono anche il nome. Il testo personale del viewer e i bot non vengono nascosti da questa impostazione.'
new_para = '`Menu 9 - Crouch Privacy` usa `PrivasiInspeksiAktif`: OFF di default. Quando è ON, un viewer della squadra nemica riceve una stringa completamente vuota per quel target, quindi sopra al player non compaiono icona eroe, nome o salute. Un viewer della stessa squadra vede invece sempre la riga completa `icona + nome + salute`, indipendentemente dalla privacy. Con Privacy OFF la riga completa è visibile anche ai nemici. Il testo personale del viewer e i bot non vengono nascosti da questa impostazione.'
if old_para in project:
    project = project.replace(old_para, new_para)
else:
    pattern = re.compile(r'`Menu 9 - Name Privacy`.*?impostazione\.', re.S)
    project, n = pattern.subn(new_para, project, count=1)
    if n != 1:
        raise SystemExit("project menu 9 paragraph not found")
PROJECT.write_text(project, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
old_test = '- **Menu 9 Name Privacy:** nuovo player = OFF; un secondo player in Crouch inspection deve vedere eroe + salute ma non il nome. Attivare Menu 9: il nome deve comparire live; disattivare: deve sparire senza rimuovere eroe/salute.'
new_test = '- **Menu 9 Crouch Privacy:** nuovo player = OFF e un nemico vede icona + nome + salute. Attivare Privacy: un nemico non deve vedere assolutamente nulla sopra al target; un alleato deve continuare a vedere sempre icona + nome + salute. Disattivare Privacy: anche il nemico torna a vedere la riga completa.'
if old_test in tests:
    tests = tests.replace(old_test, new_test)
else:
    tests = tests.replace(old_test.replace("Name Privacy", "Crouch Privacy"), new_test)
TESTS.write_text(tests, encoding="utf-8")

report = REPORT.read_text(encoding="utf-8")
report = report.replace('Menu 9 Name Privacy, default OFF; eroe/salute restano visibili anche col nome nascosto;', 'Menu 9 Crouch Privacy, default OFF; quando ON i nemici non vedono alcun HUD inspection mentre gli alleati vedono sempre icona/nome/salute;')
data = SOURCE.read_bytes().replace(b"\r\n", b"\n")
blob = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
report, n = re.subn(r"```text\n[0-9a-f]{40}\n```", f"```text\n{blob}\n```", report, count=1)
if n != 1:
    raise SystemExit("validation report blob marker not found")
REPORT.write_text(report, encoding="utf-8")
