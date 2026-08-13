from pathlib import Path

p = Path('workshop/ruang_irama.workshop')
s = p.read_text(encoding='utf-8')

# 1) Global setting variable.
old_vars = '''\t\t21: NamaHalamanEN
\t\t22: TeksDiriPemain
'''
new_vars = '''\t\t21: NamaHalamanEN
\t\t22: TeksDiriPemain
\t\t23: DurataServerMinuti
'''
if old_vars not in s:
    raise SystemExit('global variable block not found')
s = s.replace(old_vars, new_vars, 1)

# 2) Replace the old fixed Match Time with an independent Workshop duration
#    and globally disable built-in completion/scoring for every game mode.
old_init = '''\t\tGlobal.JarakKamera = 2.000;
\t\tGlobal.GeserKamera = 0.550;
\t\tGlobal.BantalanDinding = 0.200;
\t\tGlobal.JarakBidik = 25;
\t\tSet Match Time(1800);
'''
new_init = '''\t\tGlobal.JarakKamera = 2.000;
\t\tGlobal.GeserKamera = 0.550;
\t\tGlobal.BantalanDinding = 0.200;
\t\tGlobal.JarakBidik = 25;
\t\t"Timer del server indipendente dal timer nativo della modalita. Il lobby host puo scegliere da 30 a 90 minuti."
\t\tGlobal.DurataServerMinuti = Workshop Setting Integer(Custom String("AFK DEDICATED SERVER"), Custom String("Server duration (minutes)"), 30, 30, 90, 0);
\t\t"Nessuna modalita puo chiudere la partita o assegnare punteggio: Hybrid, CTF, Push, Escort, Deathmatch e tutte le altre restano endless."
\t\tDisable Built-In Game Mode Completion;
\t\tDisable Built-In Game Mode Scoring;
'''
if old_init not in s:
    raise SystemExit('old fixed match time block not found')
s = s.replace(old_init, new_init, 1)

# 3) Make the top HUD show the independent countdown instead of Match Time.
old_hud = '''\t\t\tCustom String("{0}    {1}", Custom String("AFK DEDICATED SERVER"),
\t\t\t\tRound To Integer(Match Time % 60, Down) < 10 ? Custom String("{0}:0{1}", Round To Integer(Match Time / 60, Down),
\t\t\t\t\tRound To Integer(Match Time % 60, Down)) : Custom String("{0}:{1}", Round To Integer(Match Time / 60, Down),
\t\t\t\t\tRound To Integer(Match Time % 60, Down))),
'''
remaining = 'Max(0, Global.DurataServerMinuti * 60 - Round To Integer(Total Time Elapsed, Down))'
new_hud = f'''\t\t\tCustom String("{{0}}    {{1}}", Custom String("AFK DEDICATED SERVER"),
\t\t\t\t{remaining} % 60 < 10 ? Custom String("{{0}}:0{{1}}", Round To Integer({remaining} / 60, Down),
\t\t\t\t\t{remaining} % 60) : Custom String("{{0}}:{{1}}", Round To Integer({remaining} / 60, Down),
\t\t\t\t\t{remaining} % 60)),
'''
if old_hud not in s:
    raise SystemExit('top HUD Match Time block not found')
s = s.replace(old_hud, new_hud, 1)

# 4) Restart only when the independent server countdown reaches zero.
insert_before = '''rule("01 - Pemain Masuk: Mulai jam nongkrong")
'''
restart_rule = '''rule("00b - Global: Riavvia il server solo quando il timer personalizzato finisce")
{
\tevent
\t{
\t\tOngoing - Global;
\t}

\tconditions
\t{
\t\tGlobal.Siap == True;
\t\tTotal Time Elapsed >= Global.DurataServerMinuti * 60;
\t}

\tactions
\t{
\t\t"Restart Match non dichiara un vincitore: resetta semplicemente la sessione quando il countdown AFK arriva a zero."
\t\tRestart Match;
\t}
}

'''
if insert_before not in s:
    raise SystemExit('player join rule marker not found')
if 'rule("00b - Global: Riavvia il server solo quando il timer personalizzato finisce")' in s:
    raise SystemExit('restart timer rule already exists')
s = s.replace(insert_before, restart_rule + insert_before, 1)

# Safety: the tested camera activation delay must remain untouched.
required_camera = '''Event Player.TargetKamera = Event Player;
\t\t\t\t"Lascia terminare il frame di Interact prima di cambiare rendering della camera."
\t\t\t\tWait(0.016, Ignore Condition);
\t\t\t\tEvent Player.ModeKamera = 1;'''
if required_camera not in s:
    raise SystemExit('tested camera activation delay is missing')

p.write_text(s, encoding='utf-8')

Path('.github/scripts/add_endless_server_timer.py').unlink()
Path('.github/workflows/run-add-endless-server-timer.yml').unlink()
