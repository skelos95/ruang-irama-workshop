from pathlib import Path

p = Path('workshop/ruang_irama.workshop')
s = p.read_text(encoding='utf-8')

old_self = '''\t\t\tElse If(Event Player.KursorKamera == 1);
\t\t\t\tEvent Player.TargetKamera = Event Player;
\t\t\t\tEvent Player.ModeKamera = 1;
\t\t\t\tCall Subroutine(MulaiKamera);'''
new_self = '''\t\t\tElse If(Event Player.KursorKamera == 1);
\t\t\t\tEvent Player.TargetKamera = Event Player;
\t\t\t\t"Lascia terminare il frame di Interact prima di cambiare rendering della camera."
\t\t\t\tWait(0.016, Ignore Condition);
\t\t\t\tEvent Player.ModeKamera = 1;
\t\t\t\tCall Subroutine(MulaiKamera);'''
if old_self not in s:
    raise SystemExit('self activation block not found')
s = s.replace(old_self, new_self, 1)

old_remote = '''\t\t\t\tIf(And(Event Player.CalonTargetKamera != Null, Entity Exists(Event Player.CalonTargetKamera)));
\t\t\t\t\tEvent Player.TargetKamera = Event Player.CalonTargetKamera;
\t\t\t\t\tEvent Player.ModeKamera = 2;
\t\t\t\t\tCall Subroutine(MulaiKamera);'''
new_remote = '''\t\t\t\tIf(And(Event Player.CalonTargetKamera != Null, Entity Exists(Event Player.CalonTargetKamera)));
\t\t\t\t\tEvent Player.TargetKamera = Event Player.CalonTargetKamera;
\t\t\t\t\t"Stesso ritardo di un frame quando si entra nello spectating dalla prima persona."
\t\t\t\t\tWait(0.016, Ignore Condition);
\t\t\t\t\tEvent Player.ModeKamera = 2;
\t\t\t\t\tCall Subroutine(MulaiKamera);'''
if old_remote not in s:
    raise SystemExit('remote activation block not found')
s = s.replace(old_remote, new_remote, 1)

p.write_text(s, encoding='utf-8')

Path('.github/scripts/delay_camera_start_one_frame.py').unlink()
Path('.github/workflows/run-delay-camera-start-one-frame.yml').unlink()
