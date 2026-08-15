from __future__ import annotations

from pathlib import Path
import hashlib
import re

source_path = Path('workshop/ruang_irama.workshop')
validator_path = Path('tools/validate_workshop.py')
readme_path = Path('README.md')
test_doc_path = Path('docs/TEST.md')
project_path = Path('docs/PROGETTO.md')
report_path = Path('docs/VALIDAZIONE.md')

src = source_path.read_text(encoding='utf-8')
old = '''\t\tElse If(Event Player.JenisTeleportasiTerkunci == 1);\n\t\t\tIf(Distance Between(Objective Position(Objective Index), Vector(0, 0, 0)) <= 0.100);\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Objective position unavailable in this mode. The objective is being mysterious.") : Event Player.IndeksBahasa == 1 ? Custom String("Posisi objektif tidak tersedia di mode ini. Objektifnya sedang misterius.") : Custom String("ตำแหน่งเป้าหมายใช้ไม่ได้ในโหมดนี้ เป้าหมายกำลังเล่นซ่อนหา"));\n\t\t\tElse;\n\t\t\t\tTeleport(Event Player, Nearest Walkable Position(Objective Position(Objective Index)));\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Teleported near the current objective. Heroic entrance not included.") : Event Player.IndeksBahasa == 1 ? Custom String("Teleport dekat objektif saat ini. Pose heroik tidak termasuk.") : Custom String("เทเลพอร์ตใกล้เป้าหมายปัจจุบันแล้ว ไม่มีท่าเปิดตัวฮีโร่แถมให้"));\n\t\t\tEnd;\n'''

push_players = '''Filtered Array(All Players(All Teams), And(Has Spawned(Current Array Element) == True, And(Is Alive(Current Array Element) == True, Is On Objective(Current Array Element) == True)))'''
new = f'''\t\tElse If(Event Player.JenisTeleportasiTerkunci == 1);\n\t\t\tIf(Or(Current Game Mode == Game Mode(Escort), Current Game Mode == Game Mode(Hybrid)));\n\t\t\t\tIf(Distance Between(Payload Position, Vector(0, 0, 0)) <= 0.100);\n\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Payload position unavailable right now.") : Event Player.IndeksBahasa == 1 ? Custom String("Posisi payload belum tersedia saat ini.") : Custom String("ตำแหน่งเพย์โหลดยังไม่พร้อมใช้งานตอนนี้"));\n\t\t\t\tElse;\n\t\t\t\t\tTeleport(Event Player, Nearest Walkable Position(Payload Position + Vector(2, 0, 0)));\n\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Teleported near the payload.") : Event Player.IndeksBahasa == 1 ? Custom String("Teleport dekat payload.") : Custom String("เทเลพอร์ตใกล้เพย์โหลดแล้ว"));\n\t\t\t\tEnd;\n\t\t\tElse If(Current Game Mode == Game Mode(Capture The Flag));\n\t\t\t\tTeleport(Event Player, Nearest Walkable Position(Flag Position(Opposite Team Of(Team Of(Event Player))) + Vector(2, 0, 0)));\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Teleported near the enemy flag.") : Event Player.IndeksBahasa == 1 ? Custom String("Teleport dekat bendera musuh.") : Custom String("เทเลพอร์ตใกล้ธงของศัตรูแล้ว"));\n\t\t\tElse If(Current Game Mode == Game Mode(Push));\n\t\t\t\tIf(Count Of({push_players}) > 0);\n\t\t\t\t\tTeleport(Event Player, Nearest Walkable Position(Position Of(First Of({push_players})) + Vector(2, 0, 0)));\n\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Teleported near the Push robot.") : Event Player.IndeksBahasa == 1 ? Custom String("Teleport dekat robot Push.") : Custom String("เทเลพอร์ตใกล้หุ่นยนต์ Push แล้ว"));\n\t\t\t\tElse If(Distance Between(Objective Position(Objective Index), Vector(0, 0, 0)) > 0.100);\n\t\t\t\t\tTeleport(Event Player, Nearest Walkable Position(Objective Position(Objective Index)));\n\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Robot position unavailable; using the current objective.") : Event Player.IndeksBahasa == 1 ? Custom String("Posisi robot belum tersedia; memakai objektif saat ini.") : Custom String("ไม่พบตำแหน่งหุ่นยนต์ ใช้เป้าหมายปัจจุบันแทน"));\n\t\t\t\tElse;\n\t\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Push robot position unavailable right now.") : Event Player.IndeksBahasa == 1 ? Custom String("Posisi robot Push belum tersedia saat ini.") : Custom String("ตำแหน่งหุ่นยนต์ Push ยังไม่พร้อมใช้งานตอนนี้"));\n\t\t\t\tEnd;\n\t\t\tElse If(Distance Between(Objective Position(Objective Index), Vector(0, 0, 0)) <= 0.100);\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Objective position unavailable in this mode. The objective is being mysterious.") : Event Player.IndeksBahasa == 1 ? Custom String("Posisi objektif tidak tersedia di mode ini. Objektifnya sedang misterius.") : Custom String("ตำแหน่งเป้าหมายใช้ไม่ได้ในโหมดนี้ เป้าหมายกำลังเล่นซ่อนหา"));\n\t\t\tElse;\n\t\t\t\tTeleport(Event Player, Nearest Walkable Position(Objective Position(Objective Index)));\n\t\t\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String("Teleported near the current objective.") : Event Player.IndeksBahasa == 1 ? Custom String("Teleport dekat objektif saat ini.") : Custom String("เทเลพอร์ตใกล้เป้าหมายปัจจุบันแล้ว"));\n\t\t\tEnd;\n'''

if src.count(old) != 1:
    raise SystemExit(f'objective teleport branch: expected 1, found {src.count(old)}')
src = src.replace(old, new, 1)
source_path.write_text(src, encoding='utf-8')

val = validator_path.read_text(encoding='utf-8')
anchor = '''    checks.require(\n        "If(EventPlayer.JenisTeleportasiTerkunci==0);" in after_refresh\n        and "ElseIf(EventPlayer.JenisTeleportasiTerkunci==1);" in after_refresh,\n        "Teleport: spawn e obiettivo non usano il tipo di destinazione catturato",\n    )\n'''
extra = anchor + '''    for token in (\n        "CurrentGameMode==GameMode(Escort)",\n        "CurrentGameMode==GameMode(Hybrid)",\n        "PayloadPosition+Vector(2,0,0)",\n        "CurrentGameMode==GameMode(CaptureTheFlag)",\n        "FlagPosition(OppositeTeamOf(TeamOf(EventPlayer)))+Vector(2,0,0)",\n        "CurrentGameMode==GameMode(Push)",\n        "IsOnObjective(CurrentArrayElement)==True",\n        "PositionOf(FirstOf(FilteredArray(AllPlayers(AllTeams)",\n        "ObjectivePosition(ObjectiveIndex)",\n    ):\n        checks.require(token in after_refresh, f"Teleport obiettivo dinamico incompleto: {token}")\n'''
if val.count(anchor) != 1:
    raise SystemExit('teleport validator anchor not found')
val = val.replace(anchor, extra, 1)
validator_path.write_text(val, encoding='utf-8')

readme = readme_path.read_text(encoding='utf-8')
needle = 'Current Objective'
if needle in readme and 'payload' not in readme.lower()[max(0, readme.find(needle)-150):readme.find(needle)+300]:
    readme = readme.replace(needle, 'Current Objective (payload / enemy flag when available)', 1)
readme_path.write_text(readme, encoding='utf-8')

project = project_path.read_text(encoding='utf-8')
section = '''\n\n### Teleport obiettivo dinamico\n\nLa destinazione `Current Objective` ora usa il payload reale in Escort/Hybrid, la bandiera della squadra avversaria in Capture the Flag e, in Push, un player vivo attualmente sull'obiettivo come proxy della posizione del robot. Se in Push nessuno è sul robot, resta il fallback alla posizione obiettivo disponibile. Le altre modalità continuano a usare `Objective Position(Objective Index)`.\n'''
if '### Teleport obiettivo dinamico' not in project:
    project += section
project_path.write_text(project, encoding='utf-8')

tests = test_doc_path.read_text(encoding='utf-8')
line = '- **Teleport obiettivo dinamico live:** Escort/Hybrid deve portare vicino al payload; CTF vicino alla bandiera nemica; Push vicino al robot quando almeno un player è sull’obiettivo e al fallback obiettivo quando il robot è solo; Control/Flashpoint/Clash mantengono il comportamento obiettivo precedente.\n'
if line not in tests:
    tests += '\n' + line
test_doc_path.write_text(tests, encoding='utf-8')

data = source_path.read_bytes().replace(b'\r\n', b'\n')
blob = hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()
report = report_path.read_text(encoding='utf-8')
report, n = re.subn(r'```text\n[0-9a-f]{40}\n```', f'```text\n{blob}\n```', report, count=1)
if n != 1:
    raise SystemExit('validation report blob marker not found')
report_path.write_text(report, encoding='utf-8')
