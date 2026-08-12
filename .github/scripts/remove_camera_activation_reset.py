from pathlib import Path

p = Path('workshop/ruang_irama.workshop')
s = p.read_text(encoding='utf-8')

start = s.find('rule("93 - Subrutin: Kamera terza persona dinamica sulla spalla sinistra")')
end = s.find('\nrule("94 - Subrutin:', start)
if start < 0 or end < 0:
    raise SystemExit('camera rule not found')

block = s[start:end]
old = '\t\tAbort If(Event Player.TargetKamera == Null);\n\t\tStop Camera(Event Player);\n'
new = '\t\tAbort If(Event Player.TargetKamera == Null);\n'
if old not in block:
    raise SystemExit('activation Stop Camera not found in rule 93')
block = block.replace(old, new, 1)
s = s[:start] + block + s[end:]

p.write_text(s, encoding='utf-8')

Path('.github/scripts/remove_camera_activation_reset.py').unlink()
Path('.github/workflows/run-remove-camera-activation-reset.yml').unlink()
