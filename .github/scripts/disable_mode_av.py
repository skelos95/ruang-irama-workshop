from pathlib import Path

p = Path('workshop/ruang_irama.workshop')
s = p.read_text(encoding='utf-8')

# Global: silence built-in game-mode announcer and music.
old_global = '''\t\tDisable Built-In Game Mode Completion;
\t\tDisable Built-In Game Mode Scoring;
'''
new_global = '''\t\tDisable Built-In Game Mode Completion;
\t\tDisable Built-In Game Mode Scoring;
\t\t"Modalita muta e pulita: niente announcer e niente musica nativa della modalita."
\t\tDisable Built-In Game Mode Announcer;
\t\tDisable Built-In Game Mode Music;
'''
if old_global not in s:
    raise SystemExit('global endless mode block not found')
s = s.replace(old_global, new_global, 1)

# Per human player: hide both normal game-mode HUD and in-world objective UI/icons.
old_player = '''\t\tEvent Player.Manusia = True;
\t\tDisable Game Mode HUD(Event Player);
\t\tEvent Player.IndeksGenre = -1;'''
new_player = '''\t\tEvent Player.Manusia = True;
\t\t"Nasconde barre, obiettivi e icone in-world della modalita, lasciando intatto l'HUD eroe e il nostro HUD custom."
\t\tDisable Game Mode HUD(Event Player);
\t\tDisable Game Mode In-World UI(Event Player);
\t\tEvent Player.IndeksGenre = -1;'''
if old_player not in s:
    raise SystemExit('human HUD block not found')
s = s.replace(old_player, new_player, 1)

# Preserve tested camera activation delay and endless timer system.
for required in [
    'Wait(0.016, Ignore Condition);',
    'Global.DurataServerMinuti = Workshop Setting Integer',
    'Disable Built-In Game Mode Completion;',
    'Disable Built-In Game Mode Scoring;',
    'Start Game Mode;',
    'Restart Match;'
]:
    if required not in s:
        raise SystemExit(f'missing required stable behavior: {required}')

p.write_text(s, encoding='utf-8')

Path('.github/scripts/disable_mode_av.py').unlink()
Path('.github/workflows/run-disable-mode-av.yml').unlink()
