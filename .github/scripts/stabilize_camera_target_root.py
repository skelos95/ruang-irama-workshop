from pathlib import Path

p = Path('workshop/ruang_irama.workshop')
s = p.read_text(encoding='utf-8')

# Remove the Sierra-only pitch variable. PosKameraHalus is repurposed as a filtered target root.
s = s.replace('\t\t45: PitchKameraSierra\n', '', 1)

# Replace the hero-change calibration + old Sierra pitch filter with a universal root stabilizer.
start = s.find('rule("16b - Kamera: Kalibrasi ulang saat target ganti hero")')
end = s.find('\nrule("17 - Revenge:', start)
if start < 0 or end < 0:
    raise SystemExit('camera watcher block not found')

watchers = '''rule("16b - Kamera: Kalibrasi ulang saat target ganti hero")
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
\t\t"Dopo un cambio eroe ricalibra soltanto l'altezza. Il root filtrato viene mantenuto dalla regola 16c."
\t\tWait(0.032, Ignore Condition);
\t\tAbort If(Event Player.TargetKamera == Null);
\t\tAbort If(Entity Exists(Event Player.TargetKamera) == False);
\t\tEvent Player.TinggiAnchorKamera = Min(2.200, Max(1.000, Y Component Of(Eye Position(Event Player.TargetKamera)
\t\t\t- Position Of(Event Player.TargetKamera))));
\t\tEvent Player.HeroKameraTerakhir = Hero Of(Event Player.TargetKamera);
\t}
}

rule("16c - Kamera: Stabilizza root di Sierra e dei target osservati")
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
\t\t"Position Of remoto puo ricevere piccole correzioni di rete; Sierra mostra inoltre un root molto mobile. Filtra il root senza usare Chase, cosi continua davvero a seguire il bersaglio."
\t\tIf(Event Player.ModeKamera == 2);
\t\t\tEvent Player.PosKameraHalus += (Position Of(Event Player.TargetKamera) - Event Player.PosKameraHalus)
\t\t\t\t* (Hero Of(Event Player.TargetKamera) == Hero(Sierra) ? 0.300 : 0.420);
\t\tElse If(Hero Of(Event Player.TargetKamera) == Hero(Sierra));
\t\t\tEvent Player.PosKameraHalus += (Position Of(Event Player.TargetKamera) - Event Player.PosKameraHalus) * 0.300;
\t\tElse;
\t\t\t"Per la propria camera sugli altri eroi nessun ritardo: tieni il root sincronizzato esattamente."
\t\t\tEvent Player.PosKameraHalus = Position Of(Event Player.TargetKamera);
\t\tEnd;
\t\tWait(0.016, Ignore Condition);
\t\tLoop If Condition Is True;
\t}
}
'''
s = s[:start] + watchers + s[end + 1:]

# Replace the complete camera subroutine with a clean version using the filtered root only
# when spectating somebody else or when the target hero is Sierra.
start = s.find('rule("93 - Subrutin: Kamera terza persona dinamica sulla spalla sinistra")')
end = s.find('\nrule("94 - Subrutin:', start)
if start < 0 or end < 0:
    raise SystemExit('camera subroutine not found')

base = '(Or(Event Player.ModeKamera == 2, Hero Of(Event Player.TargetKamera) == Hero(Sierra)) ? Event Player.PosKameraHalus : Position Of(Event Player.TargetKamera))'
height = 'Vector(0, Event Player.TinggiAnchorKamera + Min(0.750, Max(0.450, 0.450 + (Max Health(Event Player.TargetKamera) - 200) * 0.0006)), 0)'
distance = 'Min(4.500, Max(Global.JarakKamera, Global.JarakKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0055))'
side = 'Min(1.350, Max(Global.GeserKamera, Global.GeserKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0016))'
yaw = 'Direction From Angles(Horizontal Angle From Direction(Facing Direction Of(Event Player.TargetKamera)), 0)'
left = f'Cross Product({yaw}, Vector(0, 1, 0))'
pitchfactor = '(Hero Of(Event Player.TargetKamera) == Hero(Sierra) ? 0.300 : 0.500)'
ideal = f'''{base} + {height}
\t\t\t\t\t\t- {yaw} * {distance}
\t\t\t\t\t\t+ Vector(0, 0 - Y Component Of(Facing Direction Of(Event Player.TargetKamera)) * {distance} * {pitchfactor}, 0)
\t\t\t\t\t\t+ {left} * {side}'''
anchor = f'{base} + {height}'
look = f'''{base} + Vector(0, Event Player.TinggiAnchorKamera, 0)
\t\t\t\t\t+ Facing Direction Of(Event Player.TargetKamera) * Global.JarakBidik'''

new_rule = f'''rule("93 - Subrutin: Kamera terza persona dinamica sulla spalla sinistra")
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
\t\t"Camera diretta per se stessi; root filtrato manualmente per Sierra e quando si osservano altri. Nessun Chase e nessun filtro sulla rotazione."
\t\tEvent Player.HeroKameraTerakhir = Hero Of(Event Player.TargetKamera);
\t\tEvent Player.PosKameraHalus = Position Of(Event Player.TargetKamera);
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
s = s[:start] + new_rule + s[end:]

# Remove obsolete Sierra pitch initialization if present; keep root vector initialization.
s = s.replace('\t\tEvent Player.PitchKameraSierra = 0;\n', '', 1)

p.write_text(s, encoding='utf-8')

Path('.github/scripts/stabilize_camera_target_root.py').unlink()
Path('.github/workflows/run-stabilize-camera-target-root.yml').unlink()
