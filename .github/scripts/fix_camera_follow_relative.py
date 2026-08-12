from pathlib import Path
import re

p = Path('workshop/ruang_irama.workshop')
s = p.read_text(encoding='utf-8')

# The old Chase Player Variable approach did not reliably follow moving world-space destinations in game.
s = s.replace('\t\t\t\tStop Chasing Player Variable(Event Player, PosKameraHalus);\n', '', 1)
s = s.replace('\t\tStop Chasing Player Variable(Event Player, PosKameraHalus);\n', '', 1)

# Insert deterministic smoothing rule after target-left handling and before Revenge.
marker = '\nrule("17 - Revenge: Catat solo il killer diretto, bukan assist")'
if marker not in s:
    raise SystemExit('Revenge rule insertion marker not found')

smooth_rule = '''
rule("16b - Kamera: Haluskan offset, tapi ikuti gerakan pemain secara langsung")
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
\t\tEvent Player.BotAI == False;
\t\tIs Dummy Bot(Event Player) == False;
\t\tEvent Player.ModeKamera != 0;
\t\tEvent Player.TargetKamera != Null;
\t\tEntity Exists(Event Player.TargetKamera) == True;
\t}

\tactions
\t{
\t\t"PosKameraHalus ora e un OFFSET relativo: il root del bersaglio viene seguito senza ritardo. Solo rotazione/pitch/shoulder vengono filtrati."
\t\tEvent Player.PosKameraHalus = Event Player.PosKameraHalus + (Vector(0, Event Player.TinggiAnchorKamera + 0.350, 0)
\t\t\t- Facing Direction Of(Event Player.TargetKamera) * Min(4.200, Max(Global.JarakKamera,
\t\t\t\tGlobal.JarakKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0055))
\t\t\t+ Cross Product(Direction From Angles(Horizontal Angle From Direction(Facing Direction Of(Event Player.TargetKamera)), 0),
\t\t\t\tVector(0, 1, 0)) * Min(1.350, Max(Global.GeserKamera, Global.GeserKamera
\t\t\t\t+ (Max Health(Event Player.TargetKamera) - 200) * 0.0016)) - Event Player.PosKameraHalus) * 0.300;
\t\tWait(0.016, Ignore Condition);
\t\tLoop If Condition Is True;
\t}
}
'''
s = s.replace(marker, smooth_rule + marker, 1)

# Replace the camera subroutine: initialize relative offset once, then Start Camera adds current root position every frame.
start = s.find('rule("93 - Subrutin: Kamera terza persona dinamica sulla spalla sinistra")')
end = s.find('\nrule("94 - Subrutin:', start)
if start < 0 or end < 0:
    raise SystemExit('camera subroutine boundaries not found')

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
\t\t"Follow ibrido: Position Of segue il bersaglio direttamente; PosKameraHalus contiene solo l'offset relativo filtrato. Niente camera statica e niente ritardo avanti/indietro."
\t\tEvent Player.TinggiAnchorKamera = Min(2.200, Max(1.000, Y Component Of(Eye Position(Event Player.TargetKamera)
\t\t\t- Position Of(Event Player.TargetKamera))));
\t\tEvent Player.PosKameraHalus = Vector(0, Event Player.TinggiAnchorKamera + 0.350, 0)
\t\t\t- Facing Direction Of(Event Player.TargetKamera) * Min(4.200, Max(Global.JarakKamera,
\t\t\t\tGlobal.JarakKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0055))
\t\t\t+ Cross Product(Direction From Angles(Horizontal Angle From Direction(Facing Direction Of(Event Player.TargetKamera)), 0),
\t\t\t\tVector(0, 1, 0)) * Min(1.350, Max(Global.GeserKamera, Global.GeserKamera
\t\t\t\t+ (Max Health(Event Player.TargetKamera) - 200) * 0.0016));
\t\tStart Camera(Event Player,
\t\t\tUpdate Every Frame(
\t\t\t\tRay Cast Hit Position(
\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera + 0.350, 0),
\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Event Player.PosKameraHalus,
\t\t\t\t\tEmpty Array, Empty Array, False)
\t\t\t\t+ Direction Towards(
\t\t\t\t\tRay Cast Hit Position(
\t\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera + 0.350, 0),
\t\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Event Player.PosKameraHalus,
\t\t\t\t\t\tEmpty Array, Empty Array, False),
\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera + 0.350, 0)) * Global.BantalanDinding),
\t\t\tUpdate Every Frame(
\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera + 0.350, 0)
\t\t\t\t\t+ Facing Direction Of(Event Player.TargetKamera) * Global.JarakBidik), 0);
\t}
}
'''
s = s[:start] + new_rule + s[end:]

p.write_text(s, encoding='utf-8')

readme = Path('README.md')
if readme.exists():
    r = readme.read_text(encoding='utf-8')
    r = re.sub(
        r'- Menu `1 - Third-Person Camera`:.*?\n',
        '- Menu `1 - Third-Person Camera`: camera sulla spalla con distanza/offset scalati sulla salute massima. La posizione base del bersaglio viene seguita direttamente senza ritardo; soltanto l’offset relativo della camera viene filtrato a 60 Hz, così camminata e strafing restano agganciati al personaggio mentre rotazione e pitch rimangono morbidi.\n',
        r,
        count=1,
    )
    readme.write_text(r, encoding='utf-8')

Path('.github/scripts/fix_camera_follow_relative.py').unlink()
Path('.github/workflows/run-fix-camera-follow-relative.yml').unlink()
