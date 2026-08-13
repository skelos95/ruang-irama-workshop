from pathlib import Path

p = Path('workshop/ruang_irama.workshop')
s = p.read_text(encoding='utf-8')

marker = '''rule("01 - Pemain Masuk: Mulai jam nongkrong")
'''
rule = '''rule("00c - Global: Avvia subito la partita senza Assemble Heroes o countdown")
{
\tevent
\t{
\t\tOngoing - Global;
\t}

\tconditions
\t{
\t\tGlobal.Siap == True;
\t\tIs Game In Progress == False;
\t}

\tactions
\t{
\t\t"Forza tutte le modalita oltre Waiting/Assemble Heroes/setup finche il gameplay e realmente iniziato."
\t\tStart Game Mode;
\t\tWait(0.050, Ignore Condition);
\t\tLoop If Condition Is True;
\t}
}

'''

if 'rule("00c - Global: Avvia subito la partita senza Assemble Heroes o countdown")' in s:
    raise SystemExit('immediate start rule already exists')
if marker not in s:
    raise SystemExit('player join marker not found')
s = s.replace(marker, rule + marker, 1)

# Preserve the independent server-duration system from the previous patch.
for required in [
    'Global.DurataServerMinuti = Workshop Setting Integer',
    'Disable Built-In Game Mode Completion;',
    'Disable Built-In Game Mode Scoring;',
    'Restart Match;'
]:
    if required not in s:
        raise SystemExit(f'missing required endless-server behavior: {required}')

# Preserve the tested third-person activation delay.
required_camera = '''Event Player.TargetKamera = Event Player;
\t\t\t\t"Lascia terminare il frame di Interact prima di cambiare rendering della camera."
\t\t\t\tWait(0.016, Ignore Condition);
\t\t\t\tEvent Player.ModeKamera = 1;'''
if required_camera not in s:
    raise SystemExit('tested camera activation delay is missing')

p.write_text(s, encoding='utf-8')

Path('.github/scripts/force_immediate_game_start.py').unlink()
Path('.github/workflows/run-force-immediate-game-start.yml').unlink()
