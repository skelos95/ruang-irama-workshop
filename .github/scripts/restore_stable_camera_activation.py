from pathlib import Path

p = Path('workshop/ruang_irama.workshop')
s = p.read_text(encoding='utf-8')

# Remove the one-frame prewarm added to self activation.
old_self = '''\t\t\tElse If(Event Player.KursorKamera == 1);
\t\t\t\tIf(Event Player.ModeKamera == 0);
\t\t\t\t\t"Precarica la camera custom sulla visuale corrente per un solo frame: evita il flash del passaggio prima persona -> Start Camera."
\t\t\t\t\tStart Camera(Event Player, Eye Position(Event Player), Eye Position(Event Player)
\t\t\t\t\t\t+ Facing Direction Of(Event Player) * Global.JarakBidik, 0);
\t\t\t\t\tWait(0.016, Ignore Condition);
\t\t\t\tEnd;
\t\t\t\tEvent Player.TargetKamera = Event Player;
\t\t\t\tEvent Player.ModeKamera = 1;
\t\t\t\tCall Subroutine(MulaiKamera);'''
new_self = '''\t\t\tElse If(Event Player.KursorKamera == 1);
\t\t\t\tEvent Player.TargetKamera = Event Player;
\t\t\t\tEvent Player.ModeKamera = 1;
\t\t\t\tCall Subroutine(MulaiKamera);'''
if old_self not in s:
    raise SystemExit('self prewarm block not found')
s = s.replace(old_self, new_self, 1)

# Remove the one-frame prewarm added to remote spectating activation.
old_remote = '''\t\t\t\tIf(And(Event Player.CalonTargetKamera != Null, Entity Exists(Event Player.CalonTargetKamera)));
\t\t\t\t\tIf(Event Player.ModeKamera == 0);
\t\t\t\t\t\t"Anche quando si inizia a guardare un altro giocatore, assorbe il cambio di rendering sulla visuale corrente per un frame."
\t\t\t\t\t\tStart Camera(Event Player, Eye Position(Event Player), Eye Position(Event Player)
\t\t\t\t\t\t\t+ Facing Direction Of(Event Player) * Global.JarakBidik, 0);
\t\t\t\t\t\tWait(0.016, Ignore Condition);
\t\t\t\t\tEnd;
\t\t\t\t\tEvent Player.TargetKamera = Event Player.CalonTargetKamera;
\t\t\t\t\tEvent Player.ModeKamera = 2;
\t\t\t\t\tCall Subroutine(MulaiKamera);'''
new_remote = '''\t\t\t\tIf(And(Event Player.CalonTargetKamera != Null, Entity Exists(Event Player.CalonTargetKamera)));
\t\t\t\t\tEvent Player.TargetKamera = Event Player.CalonTargetKamera;
\t\t\t\t\tEvent Player.ModeKamera = 2;
\t\t\t\t\tCall Subroutine(MulaiKamera);'''
if old_remote not in s:
    raise SystemExit('remote prewarm block not found')
s = s.replace(old_remote, new_remote, 1)

# Restore the original stable activation reset inside MulaiKamera.
marker = '''\tactions
\t{
\t\tAbort If(Event Player.TargetKamera == Null);
\t\t"Camera diretta. Vicino ai muri abbassa solo quanto consente lo spazio reale e riduce il padding quando il muro e troppo vicino, evitando di entrare nel modello."'''
replacement = '''\tactions
\t{
\t\tAbort If(Event Player.TargetKamera == Null);
\t\tStop Camera(Event Player);
\t\t"Camera diretta. Vicino ai muri abbassa solo quanto consente lo spazio reale e riduce il padding quando il muro e troppo vicino, evitando di entrare nel modello."'''
if marker not in s:
    raise SystemExit('MulaiKamera activation marker not found')
s = s.replace(marker, replacement, 1)

# The live camera must remain direct, with no native blend.
if '''+ Facing Direction Of(Event Player.TargetKamera) * Global.JarakBidik), 60);''' in s:
    s = s.replace('''+ Facing Direction Of(Event Player.TargetKamera) * Global.JarakBidik), 60);''',
                  '''+ Facing Direction Of(Event Player.TargetKamera) * Global.JarakBidik), 0);''', 1)

p.write_text(s, encoding='utf-8')

Path('.github/scripts/restore_stable_camera_activation.py').unlink()
Path('.github/workflows/run-restore-stable-camera-activation.yml').unlink()
