from pathlib import Path

p = Path('workshop/ruang_irama.workshop')
s = p.read_text(encoding='utf-8')

# Dedicated filtered vertical aim angle for Sierra.
old = '\t\t44: HeroKameraTerakhir\n'
new = '\t\t44: HeroKameraTerakhir\n\t\t45: PitchKameraSierra\n'
if old not in s:
    raise SystemExit('player variable insertion point not found')
s = s.replace(old, new, 1)

# When a camera target changes hero, seed Sierra's filtered pitch from the real current view
# before the continuous filter starts. This avoids a jump from 0 degrees.
old = '''\t\tEvent Player.TinggiAnchorKamera = Min(2.200, Max(1.000, Y Component Of(Eye Position(Event Player.TargetKamera)
\t\t\t- Position Of(Event Player.TargetKamera))));
\t\tEvent Player.HeroKameraTerakhir = Hero Of(Event Player.TargetKamera);
\t}
}

rule("17 - Revenge: Catat solo il killer diretto, bukan assist")'''
new = '''\t\tEvent Player.TinggiAnchorKamera = Min(2.200, Max(1.000, Y Component Of(Eye Position(Event Player.TargetKamera)
\t\t\t- Position Of(Event Player.TargetKamera))));
\t\tIf(Hero Of(Event Player.TargetKamera) == Hero(Sierra));
\t\t\tEvent Player.PitchKameraSierra = Vertical Facing Angle Of(Event Player.TargetKamera);
\t\tEnd;
\t\tEvent Player.HeroKameraTerakhir = Hero Of(Event Player.TargetKamera);
\t}
}

rule("16c - Kamera: Stabilkan arah vertikal Sierra")
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
\t\tEvent Player.HeroKameraTerakhir == Hero(Sierra);
\t\tHero Of(Event Player.TargetKamera) == Hero(Sierra);
\t}

\tactions
\t{
\t\t"Filtra solo il pitch usato dalla camera di Sierra. Yaw e movimento del giocatore restano immediati; filtro esponenziale senza overshoot."
\t\tEvent Player.PitchKameraSierra += (Vertical Facing Angle Of(Event Player.TargetKamera) - Event Player.PitchKameraSierra) * 0.350;
\t\tWait(0.016, Ignore Condition);
\t\tLoop If Condition Is True;
\t}
}

rule("17 - Revenge: Catat solo il killer diretto, bukan assist")'''
if old not in s:
    raise SystemExit('hero-change watcher / rule 17 insertion point not found')
s = s.replace(old, new, 1)

start = s.find('rule("93 - Subrutin: Kamera terza persona dinamica sulla spalla sinistra")')
end = s.find('\nrule("94 - Subrutin:', start)
if start < 0 or end < 0:
    raise SystemExit('camera rule not found')
block = s[start:end]

old_comment = '"Rotazione diretta senza smoothing. Pitch camera 50 percento normalmente; Sierra usa 18 percento per eliminare la sua ondulazione mantenendo la mira verticale completa."'
new_comment = '"Sierra: la camera usa un pitch filtrato dedicato anche per il punto di mira, non solo per la posizione. Yaw resta diretto; gli altri eroi restano invariati."'
if old_comment not in block:
    raise SystemExit('camera comment not found')
block = block.replace(old_comment, new_comment, 1)

# Seed the filtered pitch whenever Start Camera is started/restarted.
old = '\t\tEvent Player.HeroKameraTerakhir = Hero Of(Event Player.TargetKamera);\n\t\tEvent Player.TinggiAnchorKamera ='
new = '\t\tEvent Player.HeroKameraTerakhir = Hero Of(Event Player.TargetKamera);\n\t\tEvent Player.PitchKameraSierra = Vertical Facing Angle Of(Event Player.TargetKamera);\n\t\tEvent Player.TinggiAnchorKamera ='
if old not in block:
    raise SystemExit('camera startup calibration point not found')
block = block.replace(old, new, 1)

# The previous Sierra fix changed only camera-position pitch amplitude. Replace the raw vertical
# Facing Direction with Sierra's filtered view pitch. Keep a reduced physical orbit amplitude.
old = '''Y Component Of(Facing Direction Of(Event Player.TargetKamera))
\t\t\t\t\t\t\t* Min(4.500, Max(Global.JarakKamera,
\t\t\t\t\t\t\t\tGlobal.JarakKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0055)) * (Hero Of(Event Player.TargetKamera) == Hero(Sierra) ? 0.180 : 0.500)'''
new = '''Y Component Of(Hero Of(Event Player.TargetKamera) == Hero(Sierra)
\t\t\t\t\t\t\t? Direction From Angles(Horizontal Facing Angle Of(Event Player.TargetKamera), Event Player.PitchKameraSierra)
\t\t\t\t\t\t\t: Facing Direction Of(Event Player.TargetKamera))
\t\t\t\t\t\t\t* Min(4.500, Max(Global.JarakKamera,
\t\t\t\t\t\t\t\tGlobal.JarakKamera + (Max Health(Event Player.TargetKamera) - 200) * 0.0055))
\t\t\t\t\t\t\t* (Hero Of(Event Player.TargetKamera) == Hero(Sierra) ? 0.300 : 0.500)'''
if block.count(old) != 2:
    raise SystemExit(f'unexpected vertical camera vector count: {block.count(old)}')
block = block.replace(old, new)

# Crucial change: Sierra's camera LOOK-AT used to still consume raw Facing Direction every frame,
# so reducing physical camera pitch could not remove the visible wave. Filter that vertical aim too.
old = '''\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera, 0)
\t\t\t\t\t+ Facing Direction Of(Event Player.TargetKamera) * Global.JarakBidik), 0);'''
new = '''\t\t\t\tPosition Of(Event Player.TargetKamera) + Vector(0, Event Player.TinggiAnchorKamera, 0)
\t\t\t\t\t+ (Hero Of(Event Player.TargetKamera) == Hero(Sierra)
\t\t\t\t\t\t? Direction From Angles(Horizontal Facing Angle Of(Event Player.TargetKamera), Event Player.PitchKameraSierra)
\t\t\t\t\t\t: Facing Direction Of(Event Player.TargetKamera)) * Global.JarakBidik), 0);'''
if old not in block:
    raise SystemExit('camera look-at expression not found')
block = block.replace(old, new, 1)

s = s[:start] + block + s[end:]

# Initialize scalar variable.
old = '\t\tEvent Player.HeroKameraTerakhir = Null;\n'
new = '\t\tEvent Player.HeroKameraTerakhir = Null;\n\t\tEvent Player.PitchKameraSierra = 0;\n'
if old not in s:
    raise SystemExit('camera initialization point not found')
s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')

Path('.github/scripts/stabilize_sierra_aim.py').unlink()
Path('.github/workflows/run-stabilize-sierra-aim.yml').unlink()
