from pathlib import Path

p = Path('workshop/ruang_irama.workshop')
s = p.read_text(encoding='utf-8')

start = s.find('rule("93 - Subrutin: Kamera terza persona dinamica sulla spalla sinistra")')
end = s.find('\nrule("94 - Subrutin:', start)
if start < 0 or end < 0:
    raise SystemExit('camera rule not found')

anchor = '''Position Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera
\t\t\t\t\t\t+ Min(0.750, Max(0.450, 0.450 + (Max Health(Event Player.TargetKamera) - 200) * 0.0006)), 0)'''
distance = '''Min(4.500, Max(Global.JarakKamera,
\t\t\t\t\t\t\tGlobal.JarakKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0055))'''
side = '''Min(1.350, Max(Global.GeserKamera,
\t\t\t\t\t\t\tGlobal.GeserKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0016))'''
left = '''Cross Product(Direction From Angles(Horizontal Angle From Direction(Facing Direction Of(Event Player.TargetKamera)), 0),
\t\t\t\t\t\t\tVector(0, 1, 0))'''
ideal = f'''{anchor}
\t\t\t\t\t\t- Facing Direction Of(Event Player.TargetKamera) * {distance}
\t\t\t\t\t\t+ {left} * {side}'''
hit = f'''Ray Cast Hit Position(
\t\t\t\t\t\t{anchor},
\t\t\t\t\t\t{ideal},
\t\t\t\t\t\tEmpty Array, Empty Array, False)'''

rule93 = f'''rule("93 - Subrutin: Kamera terza persona dinamica sulla spalla sinistra")
{{
\tevent
\t{{
\t\tSubroutine;
\t\tMulaiKamera;
\t}}

\tactions
\t{{
\t\tAbort If(Event Player.TargetKamera == Null);
\t\tStop Camera(Event Player);
\t\t"Camera diretta. Se un muro accorcia la distanza, abbassa progressivamente la camera fino a 0.40 m per mantenere visibile la schiena dell'eroe."
\t\tEvent Player.HeroKameraTerakhir = Hero Of(Event Player.TargetKamera);
\t\tEvent Player.TinggiAnchorKamera = Min(2.200, Max(1.000, Y Component Of(Eye Position(Event Player.TargetKamera)
\t\t\t- Position Of(Event Player.TargetKamera))));
\t\tStart Camera(Event Player,
\t\t\tUpdate Every Frame(
\t\t\t\t{hit}
\t\t\t\t+ Direction Towards(
\t\t\t\t\t{hit},
\t\t\t\t\t{anchor}) * Global.BantalanDinding
\t\t\t\t- Vector(0, Min(0.400, Distance Between(
\t\t\t\t\t{hit},
\t\t\t\t\t{ideal}) * 0.300), 0)),
\t\t\tUpdate Every Frame(
\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera, 0)
\t\t\t\t\t+ Facing Direction Of(Event Player.TargetKamera) * Global.JarakBidik), 0);
\t}}
}}
'''

s = s[:start] + rule93 + s[end:]
p.write_text(s, encoding='utf-8')

Path('.github/scripts/lower_camera_near_walls.py').unlink()
Path('.github/workflows/run-lower-camera-near-walls.yml').unlink()
