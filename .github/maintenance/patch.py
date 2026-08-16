from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "workshop" / "ruang_irama.workshop"
VALIDATOR = ROOT / "tools" / "validate_workshop.py"
README = ROOT / "README.md"
PROGETTO = ROOT / "docs" / "PROGETTO.md"
TEST_DOC = ROOT / "docs" / "TEST.md"
VALIDAZIONE = ROOT / "docs" / "VALIDAZIONE.md"
VERSION = ROOT / "VERSION"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"{label}: expected one occurrence, found {text.count(old)}")
    return text.replace(old, new, 1)


def mask_strings(text: str) -> str:
    out=[]; quoted=False; escaped=False
    for ch in text:
        if quoted:
            if escaped: escaped=False
            elif ch == "\\": escaped=True
            elif ch == '"': quoted=False
            out.append("\n" if ch == "\n" else " ")
        elif ch == '"': quoted=True; out.append(" ")
        else: out.append(ch)
    return "".join(out)


def matching(text: str, opening: int, left: str, right: str) -> int:
    clean=mask_strings(text); depth=1
    for i in range(opening+1, len(clean)):
        if clean[i] == left: depth += 1
        elif clean[i] == right:
            depth -= 1
            if depth == 0: return i
    raise RuntimeError(f"unclosed {left}")


def rule_spans(text: str):
    for m in re.finditer(r'^rule\("([^"]+)"\)\s*\{', text, re.M):
        opening=text.find("{", m.start(), m.end()); end=matching(text, opening, "{", "}")+1
        yield m.group(1), m.start(), end, text[m.start():end]


def get_rule(text: str, name: str):
    for n,s,e,r in rule_spans(text):
        if n == name: return s,e,r
    raise RuntimeError(f"rule not found: {name}")


def find_subroutine_rule(text: str, subroutine: str):
    token=f"\t\t{subroutine};"
    found=[]
    for n,s,e,r in rule_spans(text):
        clean=mask_strings(r)
        if "Subroutine;" in clean and token in clean:
            found.append((n,s,e,r))
    if len(found) != 1:
        raise RuntimeError(f"subroutine rule {subroutine}: found {len(found)}")
    return found[0]


def replace_actions(rule: str, actions: str) -> str:
    clean=mask_strings(rule); m=re.search(r'(?m)^\s*actions\s*\{', clean)
    if not m: raise RuntimeError("actions missing")
    opening=clean.find("{", m.start()); closing=matching(rule, opening, "{", "}")
    return rule[:opening+1] + "\n" + actions.rstrip() + "\n\t" + rule[closing:]


def top_items(body: str):
    items=[]; start=0; stack=[]; quoted=False; escaped=False; pairs={')':'(',']':'[','}':'{'}
    for i,ch in enumerate(body):
        if quoted:
            if escaped: escaped=False
            elif ch == "\\": escaped=True
            elif ch == '"': quoted=False
            continue
        if ch == '"': quoted=True
        elif ch in '([{': stack.append(ch)
        elif ch in ')]}':
            if not stack or stack[-1] != pairs[ch]: raise RuntimeError("unbalanced args")
            stack.pop()
        elif ch == ',' and not stack: items.append(body[start:i].strip()); start=i+1
    items.append(body[start:].strip())
    return items


def hud_args(rule: str):
    clean=mask_strings(rule); at=clean.find("Create HUD Text(")
    if at < 0 or clean.find("Create HUD Text(", at+1) >= 0: raise RuntimeError("renderer HUD count != 1")
    opening=clean.find("(", at); closing=matching(rule, opening, "(", ")")
    return top_items(rule[opening+1:closing])


def ternary(values):
    parts=[]
    for code,value in values[:-1]: parts.append(f"Event Player.HalamanMenu == {code} ? ({value})")
    return " : ".join(parts) + f" : ({values[-1][1]})"


source=SOURCE.read_text(encoding="utf-8")
renderers=[(-1,"GambarUtama"),(0,"GambarMusik"),(1,"GambarKamera"),(2,"GambarWarna"),(3,"GambarBahasa"),(4,"GambarBalasDendam"),(5,"GambarKebal"),(6,"GambarSuara"),(7,"GambarIkon"),(8,"GambarSakelarTeleportasi"),(9,"GambarPrivasiInspeksi"),(10,"GambarNasib"),(11,"GambarPilihan")]

help_values=[]; body_values=[]; second_values=[]; main_values=[]; rule_names=[]
for code,sub in renderers:
    name,_,_,rule=find_subroutine_rule(source,sub); rule_names.append((sub,name))
    args=hud_args(rule)
    if len(args) != 11: raise RuntimeError(f"{name}: HUD args {len(args)}")
    help_values.append((code,args[2])); body_values.append((code,args[3])); second_values.append((code,args[7])); main_values.append((code,args[8]))

router_name="91 - Subrutin: Pilih gambar menu yang sedang dibuka"
s,e,router=get_rule(source,router_name)
actions=f'''\t\tCall Subroutine(TransisiWarnaMenu);
\t\tIf(Event Player.HudMenu == Null);
\t\t\tCreate HUD Text(Event Player, Null,
\t\t\t\t{ternary(help_values)},
\t\t\t\t{ternary(body_values)},
\t\t\t\tTop, 100, Color(White),
\t\t\t\t{ternary(second_values)},
\t\t\t\t{ternary(main_values)},
\t\t\t\tVisible To String and Color, Visible Never);
\t\t\tEvent Player.HudMenu = Last Text ID;
\t\tEnd;
\t\tIf(Index Of Array Value(Global.PemainManusia, Event Player) >= 0);
\t\t\tGlobal.HudMenuPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = Event Player.HudMenu;
\t\tEnd;'''
source=source[:s]+replace_actions(router,actions)+source[e:]

for sub,name in rule_names:
    source=source.replace(f"Call Subroutine({sub});", "Call Subroutine(GambarMenu);")
    s,e,_=get_rule(source,name); source=source[:s]+source[e:]
    source,count=re.subn(rf'(?m)^\s*\d+\s*:\s*{re.escape(sub)}\s*$\n?', '', source, count=1)
    if count != 1: raise RuntimeError(f"declaration missing {sub}")

_,_,router=get_rule(source,router_name)
clean_router=mask_strings(router)
if "Destroy HUD Text" in clean_router: raise RuntimeError("persistent router destroys HUD")
if clean_router.count("Create HUD Text(") != 1: raise RuntimeError("persistent router HUD count")
for sub,_ in rule_names:
    if re.search(rf'\b{re.escape(sub)}\b', mask_strings(source)): raise RuntimeError(f"legacy renderer remains {sub}")
SOURCE.write_text(source,encoding="utf-8")

validator=VALIDATOR.read_text(encoding="utf-8")
validator=replace_once(validator,"della versione 0.6.8.","della versione 0.6.9.","validator doc")
validator=replace_once(validator,'CURRENT_VERSION = "0.6.8"','CURRENT_VERSION = "0.6.9"',"validator version")
start=validator.index("    expected_renderers = {"); end=validator.index("    dispatcher_candidates = [",start)
legacy="\n".join(f'        "{sub}",' for sub,_ in rule_names)
new=f'''    legacy_arcade_renderers = {{
{legacy}
    }}
    checks.require(not (legacy_arcade_renderers & subroutines), f"renderer Arcade legacy ancora dichiarati: {{sorted(legacy_arcade_renderers & subroutines)}}")
    router_rules = rules_containing(rules, "Subroutine;", "GambarMenu;")
    checks.equal(len(router_rules), 1, "renderer persistente GambarMenu")
    if router_rules:
        router = router_rules[0].body
        huds = call_texts(router, "Create HUD Text")
        checks.equal(len(huds), 1, "HUD persistente unico del Menu Arcade")
        checks.require("Destroy HUD Text" not in mask_strings(router), "GambarMenu non deve distruggere l'HUD durante i cambi pagina")
        checks.require(code_contains(router, "Event Player.HudMenu == Null;", "Event Player.HudMenu = Last Text ID;", "Call Subroutine(TransisiWarnaMenu);"), "GambarMenu non usa creazione lazy persistente")
        if huds:
            hud = huds[0]
            checks.require("Visible To String and Color" in hud, "HUD persistente non rivaluta pagina/stringhe/colori")
            for page in range(-1, 11):
                checks.require(f"Event Player.HalamanMenu == {{page}}" in hud, f"HUD persistente privo del ramo pagina {{page}}")
            for text in ("4 - REVENGE", "4 - BALAS DENDAM", "4 - ล้างแค้น"):
                checks.require(f'Custom String("{{text}}")' in hud, "BalasDendam: stato vuoto non localizzato in tutte e tre le lingue")

'''
validator=validator[:start]+new+validator[end:]
marker='    revenge_renderers = rules_containing(rules, "Subroutine;", "GambarBalasDendam;")'
if marker in validator:
    a=validator.index(marker); b=validator.index("\n\ndef check_camera",a); validator=validator[:a]+validator[b:]
VALIDATOR.write_text(validator,encoding="utf-8")
VERSION.write_text("0.6.9\n",encoding="utf-8")

readme=README.read_text(encoding="utf-8")
readme=replace_once(readme,"La versione **0.6.8** identifica lo stato funzionale e tecnico corrente del repository.","La versione **0.6.9** identifica lo stato funzionale e tecnico corrente del repository.","README version")
readme += "\n\n### HUD persistente 0.6.9\n\nIl Menu Arcade usa un solo HUD persistente: `Interact` e `Reload` cambiano `HalamanMenu` senza `Destroy HUD Text` / `Create HUD Text`. Le 13 viste sono rivalutate nello stesso elemento HUD.\n"
README.write_text(readme,encoding="utf-8")

progetto=PROGETTO.read_text(encoding="utf-8"); progetto=replace_once(progetto,"# Note di progetto — versione 0.6.8","# Note di progetto — versione 0.6.9","PROGETTO title"); progetto=replace_once(progetto,"Workshop 0.6.8.","Workshop 0.6.9.","PROGETTO version"); progetto += "\n\n## HUD Arcade persistente 0.6.9\n\nIl cambio pagina non ricrea più l'HUD: `GambarMenu` crea lazy un solo HUD e `HalamanMenu` seleziona la pagina live.\n"; PROGETTO.write_text(progetto,encoding="utf-8")

test=TEST_DOC.read_text(encoding="utf-8"); test=replace_once(test,"# Piano di test — versione 0.6.8","# Piano di test — versione 0.6.9","TEST title"); test=replace_once(test,"Workshop 0.6.8.","Workshop 0.6.9.","TEST version"); test += "\n\n## Cambio pagina immediato 0.6.9\n\nPremere rapidamente `Interact` e `Reload`: il cambio Main/submenu deve avvenire senza la precedente pausa percepita e senza flash HUD.\n"; TEST_DOC.write_text(test,encoding="utf-8")

valid=VALIDAZIONE.read_text(encoding="utf-8"); valid=replace_once(valid,"# Rapporto di validazione — versione 0.6.8","# Rapporto di validazione — versione 0.6.9","VALIDAZIONE title"); valid=replace_once(valid,"Release tecnica: **CHILL Dedicated Server 0.6.8**","Release tecnica: **CHILL Dedicated Server 0.6.9**","VALIDAZIONE release"); valid=replace_once(valid,"OK - controlli statici v0.6.8 superati","OK - controlli statici v0.6.9 superati","VALIDAZIONE result"); valid += "\n\n## HUD persistente 0.6.9\n\nIl gate richiede un solo HUD Arcade persistente e nessun renderer per-pagina legacy.\n"
data=SOURCE.read_bytes().replace(b"\r\n",b"\n"); payload=b"blob "+str(len(data)).encode()+b"\0"+data; blob=hashlib.sha1(payload).hexdigest(); valid,count=re.subn(r'(Blob Git del sorgente Workshop validato:\n\n```text\n)[0-9a-f]{40}(\n```)',rf'\g<1>{blob}\g<2>',valid,count=1)
if count != 1: raise RuntimeError("VALIDAZIONE blob marker")
VALIDAZIONE.write_text(valid,encoding="utf-8")
print("Applied CHILL 0.6.9 persistent Arcade Menu HUD")
