from pathlib import Path

p = Path('workshop/ruang_irama.workshop')
s = p.read_text(encoding='utf-8')

# Camera variables: keep only sampled hero height + last hero for recalibration.
old = '''\t\t42: TinggiAnchorKamera
\t\t43: PosKameraHalus
\t\t44: HeroKameraTerakhir
\t\t45: DirezioneKameraHalus
'''
new = '''\t\t42: TinggiAnchorKamera
\t\t43: HeroKameraTerakhir
'''
if old not in s:
    raise SystemExit('camera variable block not found')
s = s.replace(old, new, 1)

# Keep hero-change height recalibration, but make it immediate and minimal.
start = s.find('rule("16b - Kamera: Kalibrasi ulang saat target ganti hero")')
end = s.find('\nrule("17 - Revenge:', start)
if start < 0 or end < 0:
    raise SystemExit('camera watcher region not found')

rule16b = '''rule("16b - Kamera: Kalibrasi ulang saat target ganti hero")
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
\t\tHero Of(Event Player.TargetKamera) != Event Player.HeroKameraTerakhir;
\t}

\tactions
\t{
\t\tEvent Player.TinggiAnchorKamera = Min(2.200, Max(1.000, Y Component Of(Eye Position(Event Player.TargetKamera)
\t\t\t- Position Of(Event Player.TargetKamera))));
\t\tEvent Player.HeroKameraTerakhir = Hero Of(Event Player.TargetKamera);
\t}
}
'''
s = s[:start] + rule16b + s[end + 1:]

# One direct camera implementation for self and spectating targets.
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
\t\t"Camera unica e diretta per se stessi e per gli altri: nessun smoothing, wait o loop. Position Of e Facing Direction vengono letti ogni frame."
\t\tEvent Player.HeroKameraTerakhir = Hero Of(Event Player.TargetKamera);
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
\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera, 0)
\t\t\t\t\t+ Facing Direction Of(Event Player.TargetKamera) * Global.JarakBidik), 0);
\t}}
}}
'''
s = s[:start] + rule93 + s[end:]

# Remove old smoothing variable initialization.
s = s.replace('\t\tEvent Player.PosKameraHalus = Vector(0, 0, 0);\n', '', 1)
s = s.replace('\t\tEvent Player.DirezioneKameraHalus = Vector(0, 0, 1);\n', '', 1)

p.write_text(s, encoding='utf-8')

Path('.github/scripts/simplify_third_person_camera.py').unlink()
Path('.github/workflows/run-simplify-third-person-camera.yml').unlink()
