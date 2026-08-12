from pathlib import Path

p = Path('workshop/ruang_irama.workshop')
s = p.read_text(encoding='utf-8')

for old, new in [
    ('Global.JarakKamera = 1.650;', 'Global.JarakKamera = 1.350;'),
    ('Global.GeserKamera = 0.700;', 'Global.GeserKamera = 0.550;'),
    ('Global.JarakBidik = 300;', 'Global.JarakBidik = 25;'),
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
\t\t"Fluida e vicina: 1,35-2,80 m dietro; 0,55-1,20 m a sinistra. Entrambi scalano con Max Health. Look stabile a 25 m, blend 12."
\t\tStart Camera(Event Player,
\t\t\tUpdate Every Frame(
\t\t\t\tRay Cast Hit Position(
\t\t\t\t\tEye Position(Event Player.TargetKamera) + World Vector Of(Vector(
\t\t\t\t\t\t0 - Min(1.200, Max(Global.GeserKamera, Global.GeserKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0010)),
\t\t\t\t\t\t0, 0), Event Player.TargetKamera, Rotation),
\t\t\t\t\tEye Position(Event Player.TargetKamera) + World Vector Of(Vector(
\t\t\t\t\t\t0 - Min(1.200, Max(Global.GeserKamera, Global.GeserKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0010)),
\t\t\t\t\t\t0, 0), Event Player.TargetKamera, Rotation)
\t\t\t\t\t\t- Facing Direction Of(Event Player.TargetKamera) * Min(2.800, Max(Global.JarakKamera,
\t\t\t\t\t\t\tGlobal.JarakKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0019)),
\t\t\t\t\tEmpty Array, Empty Array, False)
\t\t\t\t+ Direction Towards(
\t\t\t\t\tRay Cast Hit Position(
\t\t\t\t\t\tEye Position(Event Player.TargetKamera) + World Vector Of(Vector(
\t\t\t\t\t\t\t0 - Min(1.200, Max(Global.GeserKamera, Global.GeserKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0010)),
\t\t\t\t\t\t\t0, 0), Event Player.TargetKamera, Rotation),
\t\t\t\t\t\tEye Position(Event Player.TargetKamera) + World Vector Of(Vector(
\t\t\t\t\t\t\t0 - Min(1.200, Max(Global.GeserKamera, Global.GeserKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0010)),
\t\t\t\t\t\t\t0, 0), Event Player.TargetKamera, Rotation)
\t\t\t\t\t\t\t- Facing Direction Of(Event Player.TargetKamera) * Min(2.800, Max(Global.JarakKamera,
\t\t\t\t\t\t\t\tGlobal.JarakKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0019)),
\t\t\t\t\t\tEmpty Array, Empty Array, False),
\t\t\t\t\tEye Position(Event Player.TargetKamera) + World Vector Of(Vector(
\t\t\t\t\t\t0 - Min(1.200, Max(Global.GeserKamera, Global.GeserKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0010)),
\t\t\t\t\t\t0, 0), Event Player.TargetKamera, Rotation)) * Global.BantalanDinding),
\t\t\tUpdate Every Frame(Eye Position(Event Player.TargetKamera)
\t\t\t\t+ Facing Direction Of(Event Player.TargetKamera) * Global.JarakBidik), 12);
\t}
}
'''

s = s[:start] + new_rule + s[end:]
p.write_text(s, encoding='utf-8')

readme = Path('README.md')
r = readme.read_text(encoding='utf-8')
start_r = r.find('- Menu `1 - Third-Person Camera`:')
end_r = r.find('\n', start_r)
if start_r >= 0 and end_r >= 0:
    line = ('- Menu `1 - Third-Person Camera`: camera molto più vicina e fluida, con distanza dietro circa 1,35–2,80 m e offset sinistro circa 0,55–1,20 m; entrambi scalano con Max Health. Il look usa una convergenza stabile a 25 m per ridurre il parallax senza gli scatti del raycast di mira, mentre un raycast separato evita i muri.\n')
    r = r[:start_r] + line + r[end_r+1:]
readme.write_text(r, encoding='utf-8')

Path('.github/scripts/final_camera_smooth.py').unlink()
