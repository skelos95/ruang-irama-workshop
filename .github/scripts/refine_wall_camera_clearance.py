from pathlib import Path

p = Path('workshop/ruang_irama.workshop')
s = p.read_text(encoding='utf-8')

old_comment = '"Camera diretta. Se un muro accorcia la distanza, abbassa progressivamente la camera fino a 0.40 m per mantenere visibile la schiena dell\'eroe."'
new_comment = '"Camera diretta. Vicino ai muri abbassa solo quanto consente lo spazio reale e riduce il padding quando il muro e troppo vicino, evitando di entrare nel modello."'
if old_comment not in s:
    raise SystemExit('camera wall comment not found')
s = s.replace(old_comment, new_comment, 1)

old_padding = '''\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera
\t\t\t\t\t\t+ Min(0.750, Max(0.450, 0.450 + (Max Health(Event Player.TargetKamera) - 200) * 0.0006)), 0)) * Global.BantalanDinding
\t\t\t\t- Vector(0, Min(0.400, Distance Between('''
new_padding = '''\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera
\t\t\t\t\t\t+ Min(0.750, Max(0.450, 0.450 + (Max Health(Event Player.TargetKamera) - 200) * 0.0006)), 0))
\t\t\t\t\t* Min(Global.BantalanDinding, Distance Between(
\t\t\t\t\t\tRay Cast Hit Position(
\t\t\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera
\t\t\t\t\t\t\t\t+ Min(0.750, Max(0.450, 0.450 + (Max Health(Event Player.TargetKamera) - 200) * 0.0006)), 0),
\t\t\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera
\t\t\t\t\t\t\t\t+ Min(0.750, Max(0.450, 0.450 + (Max Health(Event Player.TargetKamera) - 200) * 0.0006)), 0)
\t\t\t\t\t\t\t\t- Facing Direction Of(Event Player.TargetKamera) * Min(4.500, Max(Global.JarakKamera,
\t\t\t\t\t\t\t\t\tGlobal.JarakKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0055))
\t\t\t\t\t\t\t\t+ Cross Product(Direction From Angles(Horizontal Angle From Direction(Facing Direction Of(Event Player.TargetKamera)), 0),
\t\t\t\t\t\t\t\t\tVector(0, 1, 0)) * Min(1.350, Max(Global.GeserKamera,
\t\t\t\t\t\t\t\t\tGlobal.GeserKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0016)),
\t\t\t\t\t\t\tEmpty Array, Empty Array, False),
\t\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera
\t\t\t\t\t\t\t+ Min(0.750, Max(0.450, 0.450 + (Max Health(Event Player.TargetKamera) - 200) * 0.0006)), 0)) * 0.250)
\t\t\t\t- Vector(0, Min(0.240, Distance Between('''
if old_padding not in s:
    raise SystemExit('wall padding/lowering block start not found')
s = s.replace(old_padding, new_padding, 1)

old_tail = '''\t\t\t\t\t\t+ Cross Product(Direction From Angles(Horizontal Angle From Direction(Facing Direction Of(Event Player.TargetKamera)), 0),
\t\t\t\t\t\t\tVector(0, 1, 0)) * Min(1.350, Max(Global.GeserKamera,
\t\t\t\t\t\t\tGlobal.GeserKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0016))) * 0.300), 0)),'''
new_tail = '''\t\t\t\t\t\t+ Cross Product(Direction From Angles(Horizontal Angle From Direction(Facing Direction Of(Event Player.TargetKamera)), 0),
\t\t\t\t\t\t\tVector(0, 1, 0)) * Min(1.350, Max(Global.GeserKamera,
\t\t\t\t\t\t\tGlobal.GeserKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0016))) * 0.180)
\t\t\t\t\t* Min(1, Distance Between(
\t\t\t\t\t\tRay Cast Hit Position(
\t\t\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera
\t\t\t\t\t\t\t\t+ Min(0.750, Max(0.450, 0.450 + (Max Health(Event Player.TargetKamera) - 200) * 0.0006)), 0),
\t\t\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera
\t\t\t\t\t\t\t\t+ Min(0.750, Max(0.450, 0.450 + (Max Health(Event Player.TargetKamera) - 200) * 0.0006)), 0)
\t\t\t\t\t\t\t\t- Facing Direction Of(Event Player.TargetKamera) * Min(4.500, Max(Global.JarakKamera,
\t\t\t\t\t\t\t\t\tGlobal.JarakKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0055))
\t\t\t\t\t\t\t\t+ Cross Product(Direction From Angles(Horizontal Angle From Direction(Facing Direction Of(Event Player.TargetKamera)), 0),
\t\t\t\t\t\t\t\t\tVector(0, 1, 0)) * Min(1.350, Max(Global.GeserKamera,
\t\t\t\t\t\t\t\t\tGlobal.GeserKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0016)),
\t\t\t\t\t\t\tEmpty Array, Empty Array, False),
\t\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera
\t\t\t\t\t\t\t+ Min(0.750, Max(0.450, 0.450 + (Max Health(Event Player.TargetKamera) - 200) * 0.0006)), 0)) / 1.200), 0)),'''
if old_tail not in s:
    raise SystemExit('wall lowering block tail not found')
s = s.replace(old_tail, new_tail, 1)

p.write_text(s, encoding='utf-8')

Path('.github/scripts/refine_wall_camera_clearance.py').unlink()
Path('.github/workflows/run-refine-wall-camera-clearance.yml').unlink()
