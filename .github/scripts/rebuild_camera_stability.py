from pathlib import Path

p = Path('workshop/ruang_irama.workshop')
s = p.read_text(encoding='utf-8')

# Add a dedicated smoothed facing vector. PosKameraHalus remains the optional filtered root.
old = '\t\t44: HeroKameraTerakhir\n'
new = '\t\t44: HeroKameraTerakhir\n\t\t45: DirezioneKameraHalus\n'
if old not in s:
    raise SystemExit('player variable insertion point not found')
s = s.replace(old, new, 1)

# Replace the root stabilizer with a mode-aware one:
# - normal self camera: everything direct (the known smooth setup)
# - Sierra self: only Y/root bob is damped; X/Z and facing remain direct
# - remote spectating: lightly filter both world root and full 3D facing vector
start = s.find('rule("16c - Kamera: Stabilizza root di Sierra e dei target osservati")')
end = s.find('\nrule("17 - Revenge:', start)
if start < 0 or end < 0:
    raise SystemExit('16c stabilizer rule not found')

rule16c = '''rule("16c - Kamera: Stabilizza solo dove serve")
{
\tevent
\t{
\t\tOngoing - Each Player;
\t\tAll;
\t\tAll;
\t}

\tconditions
\t{
\t\tEvent Player.Manusia == True;
\t\tEvent Player.ModeKamera != 0;
\t\tEvent Player.TargetKamera != Null;
\t\tEntity Exists(Event Player.TargetKamera) == True;
\t}

\tactions
\t{
\t\t"Self normale resta completamente diretto. Sierra filtra solo Y per togliere il bob senza ritardo avanti/indietro. I target remoti filtrano root e facing per assorbire correzioni di rete."
\t\tIf(Event Player.ModeKamera == 2);
\t\t\tEvent Player.PosKameraHalus += (Position Of(Event Player.TargetKamera) - Event Player.PosKameraHalus) * 0.600;
\t\t\tEvent Player.DirezioneKameraHalus = Normalize(Event Player.DirezioneKameraHalus
\t\t\t\t+ (Facing Direction Of(Event Player.TargetKamera) - Event Player.DirezioneKameraHalus) * 0.650);
\t\tElse If(Hero Of(Event Player.TargetKamera) == Hero(Sierra));
\t\t\tEvent Player.PosKameraHalus = Vector(X Component Of(Position Of(Event Player.TargetKamera)),
\t\t\t\tY Component Of(Event Player.PosKameraHalus) + (Y Component Of(Position Of(Event Player.TargetKamera))
\t\t\t\t\t- Y Component Of(Event Player.PosKameraHalus)) * 0.180,
\t\t\t\tZ Component Of(Position Of(Event Player.TargetKamera)));
\t\t\tEvent Player.DirezioneKameraHalus = Facing Direction Of(Event Player.TargetKamera);
\t\tElse;
\t\t\tEvent Player.PosKameraHalus = Position Of(Event Player.TargetKamera);
\t\t\tEvent Player.DirezioneKameraHalus = Facing Direction Of(Event Player.TargetKamera);
\t\tEnd;
\t\tWait(0.016, Ignore Condition);
\t\tLoop If Condition Is True;
\t}
}
'''
s = s[:start] + rule16c + s[end + 1:]

# Rebuild camera geometry. The critical part is a FULL 3D backward vector, not yaw-only + partial Y.
# Camera position and look-at use the same direction basis, so extreme up/down aim keeps the hero framed.
start = s.find('rule("93 - Subrutin: Kamera terza persona dinamica sulla spalla sinistra")')
end = s.find('\nrule("94 - Subrutin:', start)
if start < 0 or end < 0:
    raise SystemExit('camera subroutine not found')

base = '(Or(Event Player.ModeKamera == 2, Hero Of(Event Player.TargetKamera) == Hero(Sierra)) ? Event Player.PosKameraHalus : Position Of(Event Player.TargetKamera))'
dirv = '(Event Player.ModeKamera == 2 ? Event Player.DirezioneKameraHalus : Facing Direction Of(Event Player.TargetKamera))'
height = 'Vector(0, Event Player.TinggiAnchorKamera + Min(0.750, Max(0.450, 0.450 + (Max Health(Event Player.TargetKamera) - 200) * 0.0006)), 0)'
distance = 'Min(4.500, Max(Global.JarakKamera, Global.JarakKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0055))'
side = 'Min(1.350, Max(Global.GeserKamera, Global.GeserKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0016))'
left = f'Cross Product(Direction From Angles(Horizontal Angle From Direction({dirv}), 0), Vector(0, 1, 0))'
anchor = f'{base} + {height}'
ideal = f'''{base} + {height}
\t\t\t\t\t\t- {dirv} * {distance}
\t\t\t\t\t\t+ {left} * {side}'''
look = f'''{base} + Vector(0, Event Player.TinggiAnchorKamera, 0)
\t\t\t\t\t+ {dirv} * Global.JarakBidik'''

new93 = f'''rule("93 - Subrutin: Kamera terza persona dinamica sulla spalla sinistra")
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
\t\t"Orbita 3D completa: camera e look-at condividono la stessa direzione, quindi il personaggio resta in quadro anche guardando molto su o giu."
\t\tEvent Player.HeroKameraTerakhir = Hero Of(Event Player.TargetKamera);
\t\tEvent Player.PosKameraHalus = Position Of(Event Player.TargetKamera);
\t\tEvent Player.DirezioneKameraHalus = Facing Direction Of(Event Player.TargetKamera);
\t\tEvent Player.TinggiAnchorKamera = Min(2.200, Max(1.000, Y Component Of(Eye Position(Event Player.TargetKamera)
\t\t\t- Position Of(Event Player.TargetKamera))));
\t\tStart Camera(Event Player,
\t\t\tUpdate Every Frame(
\t\t\t\tRay Cast Hit Position(
\t\t\t\t\t{anchor},
\t\t\t\t\t{ideal},
\t\t\t\t\tEmpty Array, Empty Array, False)
\t\t\t\t+ Direction Towards(
\t\t\t\t\tRay Cast Hit Position(
\t\t\t\t\t\t{anchor},
\t\t\t\t\t\t{ideal},
\t\t\t\t\t\tEmpty Array, Empty Array, False),
\t\t\t\t\t{anchor}) * Global.BantalanDinding),
\t\t\tUpdate Every Frame(
\t\t\t\t{look}), 0);
\t}}
}}
'''
s = s[:start] + new93 + s[end:]

# Initialize the new facing vector.
old = '\t\tEvent Player.HeroKameraTerakhir = Null;\n'
new = '\t\tEvent Player.HeroKameraTerakhir = Null;\n\t\tEvent Player.DirezioneKameraHalus = Vector(0, 0, 1);\n'
if old not in s:
    raise SystemExit('camera init point not found')
s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')

Path('.github/scripts/rebuild_camera_stability.py').unlink()
Path('.github/workflows/run-rebuild-camera-stability.yml').unlink()
