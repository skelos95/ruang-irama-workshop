from pathlib import Path

p = Path('workshop/ruang_irama.workshop')
s = p.read_text(encoding='utf-8')

start = s.find('rule("93 - Subrutin: Kamera terza persona dinamica sulla spalla sinistra")')
end = s.find('\nrule("94 - Subrutin:', start)
if start < 0 or end < 0:
    raise SystemExit('camera rule not found')

block = s[start:end]
old = '''\t\t\tUpdate Every Frame(
\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera, 0)
\t\t\t\t\t+ Facing Direction Of(Event Player.TargetKamera) * Global.JarakBidik), 0);'''
new = '''\t\t\tUpdate Every Frame(
\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera, 0)
\t\t\t\t\t+ Facing Direction Of(Event Player.TargetKamera) * Global.JarakBidik), 60);'''
if old not in block:
    raise SystemExit('Start Camera blend parameter not found')
block = block.replace(old, new, 1)
s = s[:start] + block + s[end:]

p.write_text(s, encoding='utf-8')

Path('.github/scripts/set_camera_native_blend.py').unlink()
Path('.github/workflows/run-set-camera-native-blend.yml').unlink()
