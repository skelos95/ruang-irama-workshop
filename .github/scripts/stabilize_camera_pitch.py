from pathlib import Path

p = Path('workshop/ruang_irama.workshop')
s = p.read_text(encoding='utf-8')

start = s.find('rule("93 - Subrutin: Kamera terza persona dinamica sulla spalla sinistra")')
end = s.find('\nrule("94 - Subrutin:', start)
if start < 0 or end < 0:
    raise SystemExit('camera rule not found')
block = s[start:end]

old = '''- Facing Direction Of(Event Player.TargetKamera) * Min(4.500, Max(Global.JarakKamera,
\t\t\t\t\t\t\tGlobal.JarakKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0055))
\t\t\t\t\t\t+ Cross Product(Direction From Angles(Horizontal Angle From Direction(Facing Direction Of(Event Player.TargetKamera)), 0),'''

new = '''- Direction From Angles(Horizontal Angle From Direction(Facing Direction Of(Event Player.TargetKamera)), 0)
\t\t\t\t\t\t\t* Min(4.500, Max(Global.JarakKamera,
\t\t\t\t\t\t\t\tGlobal.JarakKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0055))
\t\t\t\t\t\t+ Vector(0, 0 - Y Component Of(Facing Direction Of(Event Player.TargetKamera))
\t\t\t\t\t\t\t* Min(4.500, Max(Global.JarakKamera,
\t\t\t\t\t\t\t\tGlobal.JarakKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0055)) * 0.500, 0)
\t\t\t\t\t\t+ Cross Product(Direction From Angles(Horizontal Angle From Direction(Facing Direction Of(Event Player.TargetKamera)), 0),'''

count = block.count(old)
if count != 2:
    raise SystemExit(f'unexpected camera backward-vector count: {count}')
block = block.replace(old, new)

old_comment = '"Rotazione diretta invariata. Camera un po piu indietro e altezza scalata con Max Health; il punto di mira resta sulla vera altezza occhi per non spostare il mirino."'
new_comment = '"Rotazione diretta senza smoothing. Distanza dietro yaw-only stabile; il pitch sposta verticalmente la camera al 50 percento per ridurre recoil/bob senza perdere la visuale su-giu."'
if old_comment not in block:
    raise SystemExit('camera comment not found')
block = block.replace(old_comment, new_comment, 1)

s = s[:start] + block + s[end:]
p.write_text(s, encoding='utf-8')

Path('.github/scripts/stabilize_camera_pitch.py').unlink()
Path('.github/workflows/run-stabilize-camera-pitch.yml').unlink()
