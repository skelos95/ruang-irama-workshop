from pathlib import Path

p = Path('workshop/ruang_irama.workshop')
s = p.read_text(encoding='utf-8')

old = '''\tactions
\t{
\t\tEvent Player.TinggiAnchorKamera = Min(2.200, Max(1.000, Y Component Of(Eye Position(Event Player.TargetKamera)
\t\t\t- Position Of(Event Player.TargetKamera))));
\t\tEvent Player.HeroKameraTerakhir = Hero Of(Event Player.TargetKamera);
\t}
}
rule("17 - Revenge: Catat solo il killer diretto, bukan assist")'''

new = '''\tactions
\t{
\t\t"Hero Of cambia prima che Eye Position del nuovo modello sia sempre stabile. Aspetta solo durante il cambio eroe, poi ricalibra una volta."
\t\tWait(0.100, Ignore Condition);
\t\tAbort If(Event Player.ModeKamera == 0);
\t\tAbort If(Event Player.TargetKamera == Null);
\t\tAbort If(Entity Exists(Event Player.TargetKamera) == False);
\t\tEvent Player.TinggiAnchorKamera = Min(2.200, Max(1.000, Y Component Of(Eye Position(Event Player.TargetKamera)
\t\t\t- Position Of(Event Player.TargetKamera))));
\t\tEvent Player.HeroKameraTerakhir = Hero Of(Event Player.TargetKamera);
\t}
}
rule("17 - Revenge: Catat solo il killer diretto, bukan assist")'''

if old not in s:
    raise SystemExit('hero recalibration rule body not found')

s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')

Path('.github/scripts/fix_camera_hero_recalibration.py').unlink()
Path('.github/workflows/run-fix-camera-hero-recalibration.yml').unlink()
