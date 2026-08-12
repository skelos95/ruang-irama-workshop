from pathlib import Path

p = Path('workshop/ruang_irama.workshop')
s = p.read_text(encoding='utf-8')

start = s.find('rule("93 - Subrutin: Kamera terza persona dinamica sulla spalla sinistra")')
end = s.find('\nrule("94 - Subrutin:', start)
if start < 0 or end < 0:
    raise SystemExit('camera rule not found')
block = s[start:end]

old = '* 0.500, 0)'
new = '* (Hero Of(Event Player.TargetKamera) == Hero(Sierra) ? 0.180 : 0.500), 0)'
if block.count(old) != 2:
    raise SystemExit(f'unexpected pitch factor count: {block.count(old)}')
block = block.replace(old, new)

old_comment = '"Rotazione diretta senza smoothing. Distanza dietro yaw-only stabile; il pitch sposta verticalmente la camera al 50 percento per ridurre recoil/bob senza perdere la visuale su-giu."'
new_comment = '"Rotazione diretta senza smoothing. Pitch camera 50 percento normalmente; Sierra usa 18 percento per eliminare la sua ondulazione mantenendo la mira verticale completa."'
if old_comment not in block:
    raise SystemExit('camera comment not found')
block = block.replace(old_comment, new_comment, 1)

s = s[:start] + block + s[end:]
p.write_text(s, encoding='utf-8')

Path('.github/scripts/stabilize_sierra_camera.py').unlink()
Path('.github/workflows/run-stabilize-sierra-camera.yml').unlink()
