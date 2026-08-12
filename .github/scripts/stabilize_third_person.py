from pathlib import Path
import re

p = Path('workshop/ruang_irama.workshop')
s = p.read_text(encoding='utf-8')

# Add one player variable used to freeze the target eye-height at camera activation.
old = '\t\t41: CalonTargetTeleport\n'
new = '\t\t41: CalonTargetTeleport\n\t\t42: TinggiAnchorKamera\n'
if old not in s:
    raise SystemExit('player variable insertion point not found')
s = s.replace(old, new, 1)

# Replace the whole third-person camera rule.
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
\t\t"Altezza campionata una volta per eliminare il bob della Eye Position. Posizione camera agganciata al root, yaw-only, blend 0: nessun ritardo avanti/indietro."
\t\tEvent Player.TinggiAnchorKamera = Min(2.200, Max(1.000, Y Component Of(Eye Position(Event Player.TargetKamera)
\t\t\t- Position Of(Event Player.TargetKamera))));
\t\tStart Camera(Event Player,
\t\t\tUpdate Every Frame(
\t\t\t\tRay Cast Hit Position(
\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera, 0),
\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera, 0)
\t\t\t\t\t\t- Direction From Angles(Horizontal Angle From Direction(Facing Direction Of(Event Player.TargetKamera)), 0)
\t\t\t\t\t\t\t* Min(2.800, Max(Global.JarakKamera, Global.JarakKamera
\t\t\t\t\t\t\t\t+ (Max Health(Event Player.TargetKamera) - 200) * 0.0019))
\t\t\t\t\t\t+ Cross Product(Direction From Angles(Horizontal Angle From Direction(Facing Direction Of(Event Player.TargetKamera)), 0),
\t\t\t\t\t\t\tVector(0, 1, 0)) * Min(1.200, Max(Global.GeserKamera, Global.GeserKamera
\t\t\t\t\t\t\t+ (Max Health(Event Player.TargetKamera) - 200) * 0.0010)),
\t\t\t\t\tEmpty Array, Empty Array, False)
\t\t\t\t+ Direction Towards(
\t\t\t\t\tRay Cast Hit Position(
\t\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera, 0),
\t\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera, 0)
\t\t\t\t\t\t\t- Direction From Angles(Horizontal Angle From Direction(Facing Direction Of(Event Player.TargetKamera)), 0)
\t\t\t\t\t\t\t\t* Min(2.800, Max(Global.JarakKamera, Global.JarakKamera
\t\t\t\t\t\t\t\t\t+ (Max Health(Event Player.TargetKamera) - 200) * 0.0019))
\t\t\t\t\t\t\t+ Cross Product(Direction From Angles(Horizontal Angle From Direction(Facing Direction Of(Event Player.TargetKamera)), 0),
\t\t\t\t\t\t\t\tVector(0, 1, 0)) * Min(1.200, Max(Global.GeserKamera, Global.GeserKamera
\t\t\t\t\t\t\t\t+ (Max Health(Event Player.TargetKamera) - 200) * 0.0010)),
\t\t\t\t\t\tEmpty Array, Empty Array, False),
\t\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera, 0)) * Global.BantalanDinding),
\t\t\tUpdate Every Frame(
\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera, 0)
\t\t\t\t\t+ Facing Direction Of(Event Player.TargetKamera) * Global.JarakBidik), 0);
\t}
}
'''
s = s[:start] + new_rule + s[end:]

# Initialize the new variable for human players.
old = '\t\tEvent Player.CalonTargetTeleport = Null;\n\t}\n}\n\nrule("95 - Subrutin:'
new = '\t\tEvent Player.CalonTargetTeleport = Null;\n\t\tEvent Player.TinggiAnchorKamera = 1.500;\n\t}\n}\n\nrule("95 - Subrutin:'
if old not in s:
    raise SystemExit('camera-height initialization point not found')
s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')

# Keep README aligned with the implementation.
readme = Path('README.md')
r = readme.read_text(encoding='utf-8')
r = re.sub(
    r'- Menu `1 - Third-Person Camera`:.*?\n',
    '- Menu `1 - Third-Person Camera`: prima persona, terza persona sul proprio eroe o visuale di un altro player/bot. La distanza resta circa 1,35–2,80 m e l’offset sinistro circa 0,55–1,20 m in base alla salute massima. La camera è agganciata alla posizione base del bersaglio con altezza occhi campionata all’attivazione, rotazione orizzontale stabile e nessun blend di inseguimento, per eliminare vibrazione e ritardo avanti/indietro; il raycast evita i muri.\n',
    r,
    count=1,
)
readme.write_text(r, encoding='utf-8')

# Remove temporary patch files after execution.
Path('.github/scripts/stabilize_third_person.py').unlink()
Path('.github/workflows/run-stabilize-third-person.yml').unlink()
