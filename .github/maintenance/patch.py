from pathlib import Path

p = Path('.github/maintenance/patch.py')
raise RuntimeError('self-wrapper should never be executed')
