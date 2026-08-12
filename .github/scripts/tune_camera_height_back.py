from pathlib import Path

p = Path('workshop/ruang_irama.workshop')
s = p.read_text(encoding='utf-8')

# Slightly farther back for every hero, while preserving stronger tank scaling.
old = '\t\tGlobal.JarakKamera = 1.750;'
new = '\t\tGlobal.JarakKamera = 2.000;'
if old not in s:
    raise SystemExit('base camera distance not found')
s = s.replace(old, new, 1)

start = s.find('rule("93 - Subrutin: Kamera terza persona dinamica sulla spalla sinistra")')
end = s.find('\nrule("94 - Subrutin:', start)
if start < 0 or end < 0:
    raise SystemExit('camera rule not found')
block = s[start:end]

# Give the camera a little more room on tanks too.
block = block.replace('Min(4.200, Max(Global.JarakKamera,', 'Min(4.500, Max(Global.JarakKamera,')
if block.count('Min(4.500, Max(Global.JarakKamera,') != 2:
    raise SystemExit('unexpected dynamic distance occurrences')

# Camera height becomes mildly health-scaled: +0.45m on 200 HP, rising up to +0.75m on large tanks.
height_old = 'Vector(0, Event Player.TinggiAnchorKamera + 0.350, 0)'
height_new = ('Vector(0, Event Player.TinggiAnchorKamera + Min(0.750, Max(0.450, 0.450 '
              '+ (Max Health(Event Player.TargetKamera) - 200) * 0.0006)), 0)')
# There are six uses in the camera rule: raise the first five camera/collision anchors,
# but keep the final look-at on the actual eye anchor so the reticle does not drift upward.
if block.count(height_old) != 6:
    raise SystemExit(f'unexpected height anchor count: {block.count(height_old)}')
block = block.replace(height_old, height_new, 5)
block = block.replace(height_old, 'Vector(0, Event Player.TinggiAnchorKamera, 0)', 1)

old_comment = '"Rotazione diretta come prima persona: nessun lerp/chase sull\'offset. Position Of e Facing Direction vengono letti ogni frame; resta solo il raycast anti-muro."'
new_comment = '"Rotazione diretta invariata. Camera un po piu indietro e altezza scalata con Max Health; il punto di mira resta sulla vera altezza occhi per non spostare il mirino."'
if old_comment not in block:
    raise SystemExit('camera comment not found')
block = block.replace(old_comment, new_comment, 1)

s = s[:start] + block + s[end:]
p.write_text(s, encoding='utf-8')

# Remove temporary patch files after the workflow executes.
Path('.github/scripts/tune_camera_height_back.py').unlink()
Path('.github/workflows/run-tune-camera-height-back.yml').unlink()
