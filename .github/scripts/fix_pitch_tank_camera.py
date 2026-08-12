from pathlib import Path

p = Path('workshop/ruang_irama.workshop')
s = p.read_text(encoding='utf-8')

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
\t\t"Root stabile senza head-bob. Il vettore indietro segue anche il pitch della mira; l'offset sinistro resta orizzontale. Tank molto piu lontani in base a Max Health. Blend 50 filtra solo la micro-vibrazione."
\t\tEvent Player.TinggiAnchorKamera = Min(2.200, Max(1.000, Y Component Of(Eye Position(Event Player.TargetKamera)
\t\t\t- Position Of(Event Player.TargetKamera))));
\t\tStart Camera(Event Player,
\t\t\tUpdate Every Frame(
\t\t\t\tRay Cast Hit Position(
\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera, 0),
\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera, 0)
\t\t\t\t\t\t- Facing Direction Of(Event Player.TargetKamera) * Min(3.800, Max(Global.JarakKamera,
\t\t\t\t\t\t\tGlobal.JarakKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0050))
\t\t\t\t\t\t+ Cross Product(Direction From Angles(Horizontal Angle From Direction(Facing Direction Of(Event Player.TargetKamera)), 0),
\t\t\t\t\t\t\tVector(0, 1, 0)) * Min(1.350, Max(Global.GeserKamera, Global.GeserKamera
\t\t\t\t\t\t\t+ (Max Health(Event Player.TargetKamera) - 200) * 0.0016)),
\t\t\t\t\tEmpty Array, Empty Array, False)
\t\t\t\t+ Direction Towards(
\t\t\t\t\tRay Cast Hit Position(
\t\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera, 0),
\t\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera, 0)
\t\t\t\t\t\t\t- Facing Direction Of(Event Player.TargetKamera) * Min(3.800, Max(Global.JarakKamera,
\t\t\t\t\t\t\t\tGlobal.JarakKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0050))
\t\t\t\t\t\t\t+ Cross Product(Direction From Angles(Horizontal Angle From Direction(Facing Direction Of(Event Player.TargetKamera)), 0),
\t\t\t\t\t\t\t\tVector(0, 1, 0)) * Min(1.350, Max(Global.GeserKamera, Global.GeserKamera
\t\t\t\t\t\t\t\t+ (Max Health(Event Player.TargetKamera) - 200) * 0.0016)),
\t\t\t\t\t\tEmpty Array, Empty Array, False),
\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera, 0)) * Global.BantalanDinding),
\t\t\tUpdate Every Frame(
\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera, 0)
\t\t\t\t\t+ Facing Direction Of(Event Player.TargetKamera) * Global.JarakBidik), 50);
\t}
}
'''

s = s[:start] + new_rule + s[end:]
p.write_text(s, encoding='utf-8')

Path('.github/scripts/fix_pitch_tank_camera.py').unlink()
Path('.github/workflows/run-fix-pitch-tank-camera.yml').unlink()
