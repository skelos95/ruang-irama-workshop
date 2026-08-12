from pathlib import Path
import re

workshop = Path('workshop/ruang_irama.workshop')
s = workshop.read_text(encoding='utf-8')

# New smoothed camera position variable.
old = '\t\t42: TinggiAnchorKamera\n'
new = '\t\t42: TinggiAnchorKamera\n\t\t43: PosKameraHalus\n'
if old not in s:
    raise SystemExit('camera variable insertion point not found')
s = s.replace(old, new, 1)

# Move every camera farther back. Health scaling still adds more distance for tanks.
if '\t\tGlobal.JarakKamera = 1.350;\n' not in s:
    raise SystemExit('camera base distance not found')
s = s.replace('\t\tGlobal.JarakKamera = 1.350;\n', '\t\tGlobal.JarakKamera = 1.750;\n', 1)

# Stop smoothing whenever third person is disabled.
old = '''\t\t\tIf(Event Player.KursorKamera == 0);
\t\t\t\tStop Camera(Event Player);
\t\t\t\tEvent Player.ModeKamera = 0;'''
new = '''\t\t\tIf(Event Player.KursorKamera == 0);
\t\t\t\tStop Chasing Player Variable(Event Player, PosKameraHalus);
\t\t\t\tStop Camera(Event Player);
\t\t\t\tEvent Player.ModeKamera = 0;'''
if old not in s:
    raise SystemExit('camera off branch not found')
s = s.replace(old, new, 1)

old = '''\tactions
\t{
\t\tStop Camera(Event Player);
\t\tEvent Player.ModeKamera = 0;
\t\tEvent Player.TargetKamera = Null;
\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String(
\t\t\t"Camera target left. First person has reclaimed you.")'''
new = '''\tactions
\t{
\t\tStop Chasing Player Variable(Event Player, PosKameraHalus);
\t\tStop Camera(Event Player);
\t\tEvent Player.ModeKamera = 0;
\t\tEvent Player.TargetKamera = Null;
\t\tSmall Message(Event Player, Event Player.IndeksBahasa == 0 ? Custom String(
\t\t\t"Camera target left. First person has reclaimed you.")'''
if old not in s:
    raise SystemExit('camera target-left branch not found')
s = s.replace(old, new, 1)

# Replace camera implementation. The ideal point still follows full aim pitch.
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
\t\tStop Chasing Player Variable(Event Player, PosKameraHalus);
\t\tStop Camera(Event Player);
\t\t"Compromesso fluidita: la posizione ideale viene filtrata in 0,08 s. Root stabile, +0,35 m in altezza, pitch completo, raycast muri immediato."
\t\tEvent Player.TinggiAnchorKamera = Min(2.200, Max(1.000, Y Component Of(Eye Position(Event Player.TargetKamera)
\t\t\t- Position Of(Event Player.TargetKamera))));
\t\tEvent Player.PosKameraHalus = Position Of(Event Player.TargetKamera)
\t\t\t+ Vector(0, Event Player.TinggiAnchorKamera + 0.350, 0)
\t\t\t- Facing Direction Of(Event Player.TargetKamera) * Min(4.200, Max(Global.JarakKamera,
\t\t\t\tGlobal.JarakKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0055))
\t\t\t+ Cross Product(Direction From Angles(Horizontal Angle From Direction(Facing Direction Of(Event Player.TargetKamera)), 0),
\t\t\t\tVector(0, 1, 0)) * Min(1.350, Max(Global.GeserKamera, Global.GeserKamera
\t\t\t\t+ (Max Health(Event Player.TargetKamera) - 200) * 0.0016));
\t\tChase Player Variable Over Time(Event Player, PosKameraHalus,
\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera + 0.350, 0)
\t\t\t\t- Facing Direction Of(Event Player.TargetKamera) * Min(4.200, Max(Global.JarakKamera,
\t\t\t\t\tGlobal.JarakKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0055))
\t\t\t\t+ Cross Product(Direction From Angles(Horizontal Angle From Direction(Facing Direction Of(Event Player.TargetKamera)), 0),
\t\t\t\t\tVector(0, 1, 0)) * Min(1.350, Max(Global.GeserKamera, Global.GeserKamera
\t\t\t\t\t+ (Max Health(Event Player.TargetKamera) - 200) * 0.0016)), 0.080, Destination and Duration);
\t\tStart Camera(Event Player,
\t\t\tUpdate Every Frame(
\t\t\t\tRay Cast Hit Position(
\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera + 0.350, 0),
\t\t\t\t\tEvent Player.PosKameraHalus,
\t\t\t\t\tEmpty Array, Empty Array, False)
\t\t\t\t+ Direction Towards(
\t\t\t\t\tRay Cast Hit Position(
\t\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera + 0.350, 0),
\t\t\t\t\t\tEvent Player.PosKameraHalus,
\t\t\t\t\t\tEmpty Array, Empty Array, False),
\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera + 0.350, 0)) * Global.BantalanDinding),
\t\t\tUpdate Every Frame(
\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera + 0.350, 0)
\t\t\t\t\t+ Facing Direction Of(Event Player.TargetKamera) * Global.JarakBidik), 0);
\t}
}
'''
s = s[:start] + new_rule + s[end:]

# Initialize vector type before any chase can start.
old = '\t\tEvent Player.TinggiAnchorKamera = 1.500;\n'
new = '\t\tEvent Player.TinggiAnchorKamera = 1.500;\n\t\tEvent Player.PosKameraHalus = Vector(0, 0, 0);\n'
if old not in s:
    raise SystemExit('camera initialization point not found')
s = s.replace(old, new, 1)

workshop.write_text(s, encoding='utf-8')

# Keep README in sync if the camera bullet exists.
readme = Path('README.md')
if readme.exists():
    r = readme.read_text(encoding='utf-8')
    r = re.sub(
        r'- Menu `1 - Third-Person Camera`:.*?\n',
        '- Menu `1 - Third-Person Camera`: camera sulla spalla con distanza e offset laterale scalati sulla salute massima. La posizione è più alta e più arretrata per tutti e viene filtrata con un inseguimento di circa 0,08 s per ridurre la vibrazione; il pitch della mira resta completo e il raycast anti-muro rimane immediato.\n',
        r,
        count=1,
    )
    readme.write_text(r, encoding='utf-8')

# Self-delete patch files after the workflow runs.
Path('.github/scripts/smooth_camera_chase.py').unlink()
Path('.github/workflows/run-smooth-camera-chase.yml').unlink()
