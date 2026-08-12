from pathlib import Path
import re

p = Path('workshop/ruang_irama.workshop')
s = p.read_text(encoding='utf-8')

for old, new in [
    ('Global.JarakKamera = 3.000;', 'Global.JarakKamera = 1.650;'),
    ('Global.GeserKamera = 1.150;', 'Global.GeserKamera = 0.700;'),
    ('Global.JarakBidik = 1000;', 'Global.JarakBidik = 300;'),
]:
    if old not in s:
        raise SystemExit(f'missing global pattern: {old}')
    s = s.replace(old, new, 1)

start = s.find('rule("93 - Subrutin: Kamera terza persona dinamica sulla spalla sinistra")')
end = s.find('\nrule("94 - Subrutin:', start)
if start < 0 or end < 0:
    raise SystemExit('camera rule boundaries not found')

new_rule = '''rule("93 - Subrutin: Kamera terza persona dinamica sulla spalla sinistra")
{
\tevent
\t{
\t\tSubroutine;
\t\tMulaiKamera;
\t}

\tactions
\t{
\t\tAbort If(Event Player.TargetKamera == Null);
\t\tStop Camera(Event Player);
\t\t"Camera fluida: distanza 1,65-3,60 m e offset sinistro 0,70-1,45 m, entrambi scalati con Max Health. Blend 50 riduce gli scatti."
\t\tStart Camera(Event Player,
\t\t\tRay Cast Hit Position(
\t\t\t\tEye Position(Event Player.TargetKamera) + World Vector Of(Vector(
\t\t\t\t\t0 - Min(1.450, Max(Global.GeserKamera, Global.GeserKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0012)),
\t\t\t\t\t0, 0), Event Player.TargetKamera, Rotation),
\t\t\t\tEye Position(Event Player.TargetKamera) + World Vector Of(Vector(
\t\t\t\t\t0 - Min(1.450, Max(Global.GeserKamera, Global.GeserKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0012)),
\t\t\t\t\t0, 0), Event Player.TargetKamera, Rotation)
\t\t\t\t\t- Facing Direction Of(Event Player.TargetKamera) * Min(3.600, Max(Global.JarakKamera,
\t\t\t\t\t\tGlobal.JarakKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0024)),
\t\t\t\tNull, All Players(All Teams), True)
\t\t\t+ Direction Towards(
\t\t\t\tRay Cast Hit Position(
\t\t\t\t\tEye Position(Event Player.TargetKamera) + World Vector Of(Vector(
\t\t\t\t\t\t0 - Min(1.450, Max(Global.GeserKamera, Global.GeserKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0012)),
\t\t\t\t\t\t0, 0), Event Player.TargetKamera, Rotation),
\t\t\t\t\tEye Position(Event Player.TargetKamera) + World Vector Of(Vector(
\t\t\t\t\t\t0 - Min(1.450, Max(Global.GeserKamera, Global.GeserKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0012)),
\t\t\t\t\t\t0, 0), Event Player.TargetKamera, Rotation)
\t\t\t\t\t\t- Facing Direction Of(Event Player.TargetKamera) * Min(3.600, Max(Global.JarakKamera,
\t\t\t\t\t\t\tGlobal.JarakKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0024)),
\t\t\t\t\tNull, All Players(All Teams), True),
\t\t\t\tEye Position(Event Player.TargetKamera) + World Vector Of(Vector(
\t\t\t\t\t0 - Min(1.450, Max(Global.GeserKamera, Global.GeserKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0012)),
\t\t\t\t\t0, 0), Event Player.TargetKamera, Rotation)) * Global.BantalanDinding,
\t\t\tRay Cast Hit Position(Eye Position(Event Player.TargetKamera),
\t\t\t\tEye Position(Event Player.TargetKamera) + Facing Direction Of(Event Player.TargetKamera) * Global.JarakBidik,
\t\t\t\tAll Players(All Teams), Event Player.TargetKamera, True), 50);
\t}
}
'''

s = s[:start] + new_rule + s[end:]
p.write_text(s, encoding='utf-8')

readme = Path('README.md')
r = readme.read_text(encoding='utf-8')
r = re.sub(
    r'- Menu `1 - Third-Person Camera`:.*?\n',
    '- Menu `1 - Third-Person Camera`: prima persona, terza persona sul proprio eroe o visuale di un altro player/bot. La camera usa un blend fluido, parte da circa 1,65 m dietro e arriva fino a circa 3,60 m in base alla salute massima; anche l’offset a sinistra scala con Max Health (circa 0,70–1,45 m). Il mirino converge sul raycast reale della mira e il raycast della camera evita i muri.\n',
    r,
    count=1,
)
readme.write_text(r, encoding='utf-8')

Path('.github/scripts/refine_fluid_camera.py').unlink()
Path('.github/workflows/refine-fluid-camera.yml').unlink()
