from pathlib import Path

p = Path('workshop/ruang_irama.workshop')
s = p.read_text(encoding='utf-8')

# Add a one-frame custom-camera prewarm only when enabling third person from camera off.
old_self = '''\t\t\tElse If(Event Player.KursorKamera == 1);
\t\t\t\tEvent Player.TargetKamera = Event Player;
\t\t\t\tEvent Player.ModeKamera = 1;
\t\t\t\tCall Subroutine(MulaiKamera);'''
new_self = '''\t\t\tElse If(Event Player.KursorKamera == 1);
\t\t\t\tIf(Event Player.ModeKamera == 0);
\t\t\t\t\t"Precarica la camera custom sulla visuale corrente per un solo frame: evita il flash del passaggio prima persona -> Start Camera."
\t\t\t\t\tStart Camera(Event Player, Eye Position(Event Player), Eye Position(Event Player)
\t\t\t\t\t\t+ Facing Direction Of(Event Player) * Global.JarakBidik, 0);
\t\t\t\t\tWait(0.016, Ignore Condition);
\t\t\t\tEnd;
\t\t\t\tEvent Player.TargetKamera = Event Player;
\t\t\t\tEvent Player.ModeKamera = 1;
\t\t\t\tCall Subroutine(MulaiKamera);'''
if old_self not in s:
    raise SystemExit('self camera activation block not found')
s = s.replace(old_self, new_self, 1)

old_remote = '''\t\t\t\tIf(And(Event Player.CalonTargetKamera != Null, Entity Exists(Event Player.CalonTargetKamera)));
\t\t\t\t\tEvent Player.TargetKamera = Event Player.CalonTargetKamera;
\t\t\t\t\tEvent Player.ModeKamera = 2;
\t\t\t\t\tCall Subroutine(MulaiKamera);'''
new_remote = '''\t\t\t\tIf(And(Event Player.CalonTargetKamera != Null, Entity Exists(Event Player.CalonTargetKamera)));
\t\t\t\t\tIf(Event Player.ModeKamera == 0);
\t\t\t\t\t\t"Anche quando si inizia a guardare un altro giocatore, assorbe il cambio di rendering sulla visuale corrente per un frame."
\t\t\t\t\t\tStart Camera(Event Player, Eye Position(Event Player), Eye Position(Event Player)
\t\t\t\t\t\t\t+ Facing Direction Of(Event Player) * Global.JarakBidik, 0);
\t\t\t\t\t\tWait(0.016, Ignore Condition);
\t\t\t\t\tEnd;
\t\t\t\t\tEvent Player.TargetKamera = Event Player.CalonTargetKamera;
\t\t\t\t\tEvent Player.ModeKamera = 2;
\t\t\t\t\tCall Subroutine(MulaiKamera);'''
if old_remote not in s:
    raise SystemExit('remote camera activation block not found')
s = s.replace(old_remote, new_remote, 1)

# Return the live camera to the approved direct, wave-free blend value.
old_blend = '''\t\t\tUpdate Every Frame(
\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera, 0)
\t\t\t\t\t+ Facing Direction Of(Event Player.TargetKamera) * Global.JarakBidik), 60);'''
new_blend = '''\t\t\tUpdate Every Frame(
\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera, 0)
\t\t\t\t\t+ Facing Direction Of(Event Player.TargetKamera) * Global.JarakBidik), 0);'''
if old_blend not in s:
    raise SystemExit('camera blend 60 not found')
s = s.replace(old_blend, new_blend, 1)

p.write_text(s, encoding='utf-8')

Path('.github/scripts/prewarm_third_person_camera.py').unlink()
Path('.github/workflows/run-prewarm-third-person-camera.yml').unlink()
