from pathlib import Path

path = Path('tools/validate_workshop.py')
text = path.read_text(encoding='utf-8')
old = '    classifier = next((rule for rule in rules if event_type(rule) == "Ongoing - Each Player" and "Event Player.NamaTampilan = Evaluate Once(Custom String("{0}", Event Player));" in rule.body and "Global.NamaSlotHUD" in rule.body), None)\n'
new = "    classifier = next((rule for rule in rules if event_type(rule) == \"Ongoing - Each Player\" and 'Event Player.NamaTampilan = Evaluate Once(Custom String(\"{0}\", Event Player));' in rule.body and \"Global.NamaSlotHUD\" in rule.body), None)\n"
if text.count(old) != 1:
    raise SystemExit(f'expected one malformed classifier line, found {text.count(old)}')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
