from pathlib import Path

p = Path('workshop/ruang_irama.workshop')
s = p.read_text(encoding='utf-8')

# Remember which hero the active camera was calibrated for.
old = '\t\t43: PosKameraHalus\n'
new = '\t\t43: PosKameraHalus\n\t\t44: HeroKameraTerakhir\n'
if old not in s:
    raise SystemExit('player variable insertion point not found')
s = s.replace(old, new, 1)

# Add a lightweight watcher after the existing target-left camera rule.
marker = '\nrule("17 - Revenge: Catat solo il killer diretto, bukan assist")'
if marker not in s:
    raise SystemExit('camera watcher insertion point not found')

watcher = '''
rule("16b - Kamera: Kalibrasi ulang saat target ganti hero")
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
\t\t"Aspetta due frame per lasciare stabilizzare il nuovo eroe, poi aggiorna solo l'altezza base. Start Camera resta attivo e fluido."
\t\tWait(0.032, Ignore Condition);
\t\tAbort If(Event Player.TargetKamera == Null);
\t\tAbort If(Entity Exists(Event Player.TargetKamera) == False);
\t\tEvent Player.TinggiAnchorKamera = Min(2.200, Max(1.000, Y Component Of(Eye Position(Event Player.TargetKamera)
\t\t\t- Position Of(Event Player.TargetKamera))));
\t\tEvent Player.HeroKameraTerakhir = Hero Of(Event Player.TargetKamera);
\t}
}
'''
s = s.replace(marker, watcher + marker, 1)

# Calibrate hero identity whenever third person starts or changes target.
needle = '''\t\t"Rotazione diretta invariata. Camera un po piu indietro e altezza scalata con Max Health; il punto di mira resta sulla vera altezza occhi per non spostare il mirino."
\t\tEvent Player.TinggiAnchorKamera = Min(2.200, Max(1.000, Y Component Of(Eye Position(Event Player.TargetKamera)'''
replacement = '''\t\t"Rotazione diretta invariata. Camera un po piu indietro e altezza scalata con Max Health; il punto di mira resta sulla vera altezza occhi per non spostare il mirino."
\t\tEvent Player.HeroKameraTerakhir = Hero Of(Event Player.TargetKamera);
\t\tEvent Player.TinggiAnchorKamera = Min(2.200, Max(1.000, Y Component Of(Eye Position(Event Player.TargetKamera)'''
if needle not in s:
    raise SystemExit('camera calibration point not found')
s = s.replace(needle, replacement, 1)

# Initialize the new player variable.
old = '\t\tEvent Player.PosKameraHalus = Vector(0, 0, 0);\n'
new = '\t\tEvent Player.PosKameraHalus = Vector(0, 0, 0);\n\t\tEvent Player.HeroKameraTerakhir = Null;\n'
if old not in s:
    raise SystemExit('camera variable initialization not found')
s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')

Path('.github/scripts/refresh_camera_on_hero_change.py').unlink()
Path('.github/workflows/run-refresh-camera-on-hero-change.yml').unlink()
