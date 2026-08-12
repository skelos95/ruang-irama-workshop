from pathlib import Path
import re

p = Path('workshop/ruang_irama.workshop')
s = p.read_text(encoding='utf-8')

# Remove the interpolation rule that causes the wave/lag while rotating.
start = s.find('rule("16b - Kamera: Haluskan offset, tapi ikuti gerakan pemain secara langsung")')
end = s.find('\nrule("17 - Revenge:', start)
if start < 0 or end < 0:
    raise SystemExit('16b smoothing rule not found')
s = s[:start] + s[end + 1:]

# Replace camera subroutine with fully direct per-frame rotation/position.
start = s.find('rule("93 - Subrutin: Kamera terza persona dinamica sulla spalla sinistra")')
end = s.find('\nrule("94 - Subrutin:', start)
if start < 0 or end < 0:
    raise SystemExit('camera subroutine not found')

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
\t\t"Rotazione diretta come prima persona: nessun lerp/chase sull'offset. Position Of e Facing Direction vengono letti ogni frame; resta solo il raycast anti-muro."
\t\tEvent Player.TinggiAnchorKamera = Min(2.200, Max(1.000, Y Component Of(Eye Position(Event Player.TargetKamera)
\t\t\t- Position Of(Event Player.TargetKamera))));
\t\tStart Camera(Event Player,
\t\t\tUpdate Every Frame(
\t\t\t\tRay Cast Hit Position(
\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera + 0.350, 0),
\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera + 0.350, 0)
\t\t\t\t\t\t- Facing Direction Of(Event Player.TargetKamera) * Min(4.200, Max(Global.JarakKamera,
\t\t\t\t\t\t\tGlobal.JarakKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0055))
\t\t\t\t\t\t+ Cross Product(Direction From Angles(Horizontal Angle From Direction(Facing Direction Of(Event Player.TargetKamera)), 0),
\t\t\t\t\t\t\tVector(0, 1, 0)) * Min(1.350, Max(Global.GeserKamera, Global.GeserKamera
\t\t\t\t\t\t\t+ (Max Health(Event Player.TargetKamera) - 200) * 0.0016)),
\t\t\t\t\tEmpty Array, Empty Array, False)
\t\t\t\t+ Direction Towards(
\t\t\t\t\tRay Cast Hit Position(
\t\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera + 0.350, 0),
\t\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera + 0.350, 0)
\t\t\t\t\t\t\t- Facing Direction Of(Event Player.TargetKamera) * Min(4.200, Max(Global.JarakKamera,
\t\t\t\t\t\t\t\tGlobal.JarakKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0055))
\t\t\t\t\t\t\t+ Cross Product(Direction From Angles(Horizontal Angle From Direction(Facing Direction Of(Event Player.TargetKamera)), 0),
\t\t\t\t\t\t\t\tVector(0, 1, 0)) * Min(1.350, Max(Global.GeserKamera, Global.GeserKamera
\t\t\t\t\t\t\t\t+ (Max Health(Event Player.TargetKamera) - 200) * 0.0016)),
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
        '- Menu `1 - Third-Person Camera`: camera sulla spalla con distanza e offset scalati sulla salute massima. Movimento e rotazione seguono direttamente `Position Of` e `Facing Direction` ogni frame, senza interpolazione dell’offset, per una risposta alla mira il più simile possibile alla prima persona; resta il raycast anti-muro.\n',
        r,
        count=1,
    )
    readme.write_text(r, encoding='utf-8')

Path('.github/scripts/remove_camera_wave.py').unlink()
Path('.github/workflows/run-remove-camera-wave.yml').unlink()
