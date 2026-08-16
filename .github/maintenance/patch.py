from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "workshop" / "ruang_irama.workshop"
VAL = ROOT / "tools" / "validate_workshop.py"
README = ROOT / "README.md"
PROGETTO = ROOT / "docs" / "PROGETTO.md"
TEST = ROOT / "docs" / "TEST.md"
VALIDAZIONE = ROOT / "docs" / "VALIDAZIONE.md"
VERSION = ROOT / "VERSION"


def once(s, a, b, label):
    n = s.count(a)
    if n != 1:
        raise RuntimeError(f"{label}: expected 1, found {n}")
    return s.replace(a, b, 1)


def mask(s):
    out=[]; q=False; esc=False
    for c in s:
        if q:
            if esc: esc=False
            elif c == "\\": esc=True
            elif c == '"': q=False
            out.append("\n" if c == "\n" else " ")
        elif c == '"': q=True; out.append(" ")
        else: out.append(c)
    if q: raise RuntimeError("unclosed string")
    return "".join(out)


def match(s, op, l="{", r="}"):
    clean=mask(s); d=1
    for i in range(op+1,len(clean)):
        if clean[i] == l: d+=1
        elif clean[i] == r:
            d-=1
            if d==0: return i
    raise RuntimeError("unclosed block")


def rule_span(s,name):
    st=s.index(f'rule("{name}")'); op=s.index("{",st); en=match(s,op)+1
    return st,en,s[st:en]


def put_rule(s,name,r):
    st,en,_=rule_span(s,name); return s[:st]+r+s[en:]


def actions(rule,new):
    clean=mask(rule); m=re.search(r"(?m)^\s*actions\s*\{",clean)
    if not m: raise RuntimeError("actions missing")
    op=clean.find("{",m.start()); cl=match(rule,op)
    return rule[:op+1]+"\n"+new.rstrip()+"\n\t"+rule[cl:]


def call_end(s,at):
    op=s.index("(",at); cl=match(s,op,"(",")"); semi=s.find(";",cl)
    if semi<0: raise RuntimeError("semicolon missing")
    return semi+1


src=SRC.read_text(encoding="utf-8")

# Remove 0.6.14 timed preload.
name="05e - Menu: Muat halaman lain bertahap setelah menu utama tampil"
st,en,_=rule_span(src,name)
while en < len(src) and src[en] == "\n": en+=1
src=src[:st]+src[en:]

# New edge preloader subroutine.
src=once(src,"\t27: BersihkanPemain\n","\t27: BersihkanPemain\n\t28: PramuatHalamanTerpilih\n","subroutine")
preload=r'''rule("91p - Subrutin: Pramuat halaman menu yang sedang dipilih")
{
	event
	{
		Subroutine;
		PramuatHalamanTerpilih;
	}

	actions
	{
		"Buat HUD submenu sebelum pemain membukanya. Tidak ada tunda dan tidak ada pengulangan; daftar halaman mencegah pembuatan ganda."
		If(Array Contains(Event Player.HalamanHudMenuArcade, Event Player.KursorUtama) == False);
			If(Event Player.KursorUtama == 0);
				Call Subroutine(GambarMusik);
			Else If(Event Player.KursorUtama == 1);
				Call Subroutine(GambarKamera);
			Else If(Event Player.KursorUtama == 2);
				Call Subroutine(GambarWarna);
			Else If(Event Player.KursorUtama == 3);
				Call Subroutine(GambarBahasa);
			Else If(Event Player.KursorUtama == 4);
				Call Subroutine(GambarBalasDendam);
			Else If(Event Player.KursorUtama == 5);
				Call Subroutine(GambarKebal);
			Else If(Event Player.KursorUtama == 6);
				Call Subroutine(GambarSuara);
			Else If(Event Player.KursorUtama == 7);
				Call Subroutine(GambarIkon);
			Else If(Event Player.KursorUtama == 8);
				Call Subroutine(GambarSakelarTeleportasi);
			Else If(Event Player.KursorUtama == 9);
				Call Subroutine(GambarPrivasiInspeksi);
			Else If(Event Player.KursorUtama == 10);
				Call Subroutine(GambarNasib);
			Else If(Event Player.KursorUtama == 11);
				Call Subroutine(GambarPilihan);
			End;
		End;
	}
}

'''
src=once(src,'rule("91k - Subrutin: Transisi warna menu tanpa lompatan")',preload+'rule("91k - Subrutin: Transisi warna menu tanpa lompatan")',"preloader")

# GambarMenu no longer creates anything.
rname="91 - Subrutin: Pilih gambar menu yang sedang dibuka"
_,_,r=rule_span(src,rname)
r=actions(r,'''\t\tCall Subroutine(TransisiWarnaMenu);
\t\tIf(Index Of Array Value(Global.PemainManusia, Event Player) >= 0);
\t\t\tGlobal.HudMenuPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = Count Of(Event Player.HudMenuArcade) > 0 ? First Of(Event Player.HudMenuArcade) : 0;
\t\tEnd;''')
src=put_rule(src,rname,r)

# Pre-create hidden Main + highlighted submenu as soon as Melee hold begins.
preopen=r'''rule("05a - Menu: Siapkan HUD tersembunyi saat Melee mulai ditahan")
{
	event
	{
		Ongoing - Each Player;
		All;
		All;
	}

	conditions
	{
		Event Player.Manusia == True;
		Event Player.BotOtomatis == False;
		Is Dummy Bot(Event Player) == False;
		Is Alive(Event Player) == True;
		Event Player.SeranganDekatDipakai == False;
		Event Player.MenuTerbuka == False;
		Event Player.TeleportasiJongkokAktif == False;
		Event Player.KartuNasibAktif == False;
		Is Button Held(Event Player, Button(Melee)) == True;
		Or(Array Contains(Event Player.HalamanHudMenuArcade, -1) == False, Array Contains(Event Player.HalamanHudMenuArcade,
			Event Player.KursorUtama) == False) == True;
	}

	actions
	{
		"HUD dibuat tersembunyi selama penghitung tahan Melee berjalan; pada 0,5 detik hanya visibilitas yang berubah."
		If(Array Contains(Event Player.HalamanHudMenuArcade, -1) == False);
			Call Subroutine(GambarUtama);
		End;
		Call Subroutine(PramuatHalamanTerpilih);
	}
}

'''
src=once(src,'rule("05b - Menu: Lepaskan serangan jarak dekat sebelum pakai lagi")',preopen+'rule("05b - Menu: Lepaskan serangan jarak dekat sebelum pakai lagi")',"preopen")

src=once(src,"\t\tIf(Event Player.HalamanMenu == -1);\n\t\t\tEvent Player.KursorUtama = (Event Player.KursorUtama + 1) % 12;\n","\t\tIf(Event Player.HalamanMenu == -1);\n\t\t\tEvent Player.KursorUtama = (Event Player.KursorUtama + 1) % 12;\n\t\t\tCall Subroutine(PramuatHalamanTerpilih);\n","next preload")
src=once(src,"\t\tIf(Event Player.HalamanMenu == -1);\n\t\t\tEvent Player.KursorUtama = (Event Player.KursorUtama + 11) % 12;\n","\t\tIf(Event Player.HalamanMenu == -1);\n\t\t\tEvent Player.KursorUtama = (Event Player.KursorUtama + 11) % 12;\n\t\t\tCall Subroutine(PramuatHalamanTerpilih);\n","prev preload")

# Move the two player social HUDs out of classifier rule 02 (which legitimately waits).
cname="02 - Pemain: Pisahkan manusia dari pasukan kaleng"
_,_,c=rule_span(src,cname)
c=once(c,"\t\tEvent Player.Manusia = True;\n","","defer human edge")
cc=mask(c); at=cc.find("Create HUD Text(")
if at<0: raise RuntimeError("social HUD block missing")
ls=c.rfind("\n",0,at)+1
sm=cc.find("Small Message(",at)
if sm<0: raise RuntimeError("welcome missing")
be=call_end(c,sm)
hud=c[ls:be]
hud=once(hud,"\t\tGlobal.HudKiriPemain = Append To Array(Global.HudKiriPemain, Event Player.HudKiri);\n","\t\tGlobal.HudKiriPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = Event Player.HudKiri;\n","left indexed")
hud=once(hud,"\t\tGlobal.HudKananPemain = Append To Array(Global.HudKananPemain, Event Player.HudKanan);\n","\t\tGlobal.HudKananPemain[Index Of Array Value(Global.PemainManusia, Event Player)] = Event Player.HudKanan;\n","right indexed")
for line in ("\t\tGlobal.HudMenuPemain = Append To Array(Global.HudMenuPemain, 0);\n","\t\tGlobal.TeksDuniaPemain = Append To Array(Global.TeksDuniaPemain, 0);\n","\t\tGlobal.TeksDiriPemain = Append To Array(Global.TeksDiriPemain, 0);\n","\t\tGlobal.SlotHUDPemain = Append To Array(Global.SlotHUDPemain, Event Player.UrutanHUD);\n"):
    hud=once(hud,line,"","remove moved placeholder")
ph='''\t\tGlobal.HudKiriPemain = Append To Array(Global.HudKiriPemain, 0);
\t\tGlobal.HudKananPemain = Append To Array(Global.HudKananPemain, 0);
\t\tGlobal.HudMenuPemain = Append To Array(Global.HudMenuPemain, 0);
\t\tGlobal.TeksDuniaPemain = Append To Array(Global.TeksDuniaPemain, 0);
\t\tGlobal.TeksDiriPemain = Append To Array(Global.TeksDiriPemain, 0);
\t\tGlobal.SlotHUDPemain = Append To Array(Global.SlotHUDPemain, Event Player.UrutanHUD);
\t\tEvent Player.Manusia = True;'''
c=c[:ls]+ph+c[be:]
src=put_rule(src,cname,c)

hudrule=f'''rule("02b - HUD Pemain: Buat segera setelah klasifikasi selesai")
{{
\tevent
\t{{
\t\tOngoing - Each Player;
\t\tAll;
\t\tAll;
\t}}

\tconditions
\t{{
\t\tGlobal.Siap == True;
\t\tEvent Player.Manusia == True;
\t\tEvent Player.BotOtomatis == False;
\t\tIs Dummy Bot(Event Player) == False;
\t\tArray Contains(Global.PemainManusia, Event Player) == True;
\t\tEvent Player.HudKiri == Null;
\t\tEvent Player.HudKanan == Null;
\t}}

\tactions
\t{{
\t\t"Klasifikasi manusia dan bot sudah selesai. HUD pemain dibuat pada aturan terpisah tanpa tunda dan tanpa pengulangan."
{hud.rstrip()}
\t}}
}}

'''
src=once(src,'rule("02c - Ruang Muncul: Perbarui posisi aman setiap kali masuk")',hudrule+'rule("02c - Ruang Muncul: Perbarui posisi aman setiap kali masuk")',"player HUD rule")
SRC.write_text(src,encoding="utf-8")

# Validator migration.
v=VAL.read_text(encoding="utf-8")
v=once(v,"della versione 0.6.14.","della versione 0.6.15.","doc version")
v=once(v,'CURRENT_VERSION = "0.6.14"','CURRENT_VERSION = "0.6.15"',"version")
bs=v.index("    preload_rules = ["); be=v.index("    router_rules = rules_containing",bs); v=v[:bs]+v[be:]
old='''        checks.require(
            "HalamanHudMenuArcade" in router_code
            and "Array Contains" in router_code
            and "TransisiWarnaMenu" in router_code,
            "GambarMenu non usa il gate lazy per pagina",
        )
        checks.require(
            "Count Of(Event Player.HudMenuArcade) == 0" not in router_code,
            "GambarMenu non deve pre-caricare tutte le pagine all'apertura",
        )
        checks.require(len(router.encode("utf-8")) < 12000, "GambarMenu è tornato troppo grande")
        for renderer, page in page_by_renderer.items():
            checks.require(f"Event Player.HalamanMenu == {page}" in router_code, f"GambarMenu non instrada pagina {page}")
            checks.require(f"Call Subroutine({renderer});" in router_code, f"GambarMenu non inizializza {renderer} on demand")
'''
new='''        checks.require("Call Subroutine(TransisiWarnaMenu);" in router_code, "GambarMenu non aggiorna la transizione colore")
        checks.require("Create HUD Text" not in router_code, "GambarMenu non deve creare HUD")
        checks.require("Array Contains" not in router_code, "GambarMenu non deve gestire la creazione HUD")
        checks.require(len(router.encode("utf-8")) < 5000, "GambarMenu è tornato troppo grande")
        for renderer in page_by_renderer:
            checks.require(f"Call Subroutine({renderer});" not in router_code, f"GambarMenu richiama ancora {renderer}")
'''
v=once(v,old,new,"router validator")

# Existing social HUD checks must follow the new 02b rule, while human registration/nameplate remains in 02.
v=v.replace('classification = [rule for rule in rules if rule.name.startswith("02 - Pemain:")]','classification = [rule for rule in rules if rule.name.startswith("02b - HUD Pemain:")]')
oldreg='''    registration = rules_containing(
        rules,
        "Append To Array(Global.PemainManusia, Event Player)",
    )
    checks.equal(
        len(registration), 1,
        "regola registrazione HUD sociali",
    )

    if registration:
        huds = call_texts(
            registration[0].body,
            "Create HUD Text",
        )
        checks.equal(
            len(huds), 2,
            "HUD sociali per giocatore",
        )

        for i, call in enumerate(huds, 1):
            checks.require(
                "Hero Icon String" in call,
                f"HUD sociale #{i} privo di icona eroe",
            )
        checks.require(
            code_contains(
                registration[0].body,
                "Disable Nameplates(Event Player",
                "Global.PemainManusia",
                "InspeksiAktif",
            ),
            "registrazione umano non nasconde la nameplate ai viewer che ispezionano",
        )
'''
newreg='''    registration = rules_containing(rules, "Append To Array(Global.PemainManusia, Event Player)")
    checks.equal(len(registration), 1, "regola registrazione umano")
    social_hud = [rule for rule in rules if rule.name.startswith("02b - HUD Pemain:")]
    checks.equal(len(social_hud), 1, "regola HUD sociali separata")
    if social_hud:
        huds = call_texts(social_hud[0].body, "Create HUD Text")
        checks.equal(len(huds), 2, "HUD sociali per giocatore")
        for i, call in enumerate(huds, 1):
            checks.require("Hero Icon String" in call, f"HUD sociale #{i} privo di icona eroe")
    if registration:
        checks.require(
            code_contains(registration[0].body, "Disable Nameplates(Event Player", "Global.PemainManusia", "InspeksiAktif"),
            "registrazione umano non nasconde la nameplate ai viewer che ispezionano",
        )
'''
v=once(v,oldreg,newreg,"crouch social validator")

# Global zero-wait/no-loop audit.
ins=v.index("    dispatcher_candidates = [")
audit='''    hud_creator_rules = [rule for rule in rules if code_contains(rule.body, "Create HUD Text(")]
    checks.require(len(hud_creator_rules) > 0, "nessuna regola Create HUD Text trovata")
    for hud_rule in hud_creator_rules:
        hud_code = mask_strings(hud_rule.body)
        checks.require("Wait(" not in hud_code, f"HUD creato dentro Wait in {hud_rule.name!r}")
        checks.require("Loop If Condition Is True;" not in hud_code, f"HUD creato dentro Loop in {hud_rule.name!r}")
    checks.equal(len([r for r in rules if r.name.startswith("05e - Menu: Muat halaman lain bertahap")]), 0, "preload 0.6.14 ancora presente")
    pre_open=[r for r in rules if r.name.startswith("05a - Menu: Siapkan HUD tersembunyi")]
    checks.equal(len(pre_open),1,"pre-creazione Main Menu")
    if pre_open:
        pc=mask_strings(pre_open[0].body)
        checks.require("Wait(" not in pc and "Loop If Condition Is True;" not in pc,"pre-creazione Main contiene Wait/Loop")
        checks.require("Call Subroutine(GambarUtama);" in pc and "Call Subroutine(PramuatHalamanTerpilih);" in pc,"pre-creazione Main/submenu incompleta")
    selected=rules_containing(rules,"Subroutine;","PramuatHalamanTerpilih;")
    checks.equal(len(selected),1,"PramuatHalamanTerpilih")
    if selected:
        sc=mask_strings(selected[0].body)
        checks.require("Wait(" not in sc and "Loop If Condition Is True;" not in sc,"preload selezionato contiene Wait/Loop")
    classifier=[r for r in rules if r.name.startswith("02 - Pemain: Pisahkan manusia")]
    checks.equal(len(classifier),1,"classificatore umano/bot")
    if classifier: checks.require("Create HUD Text" not in mask_strings(classifier[0].body),"classificatore con Wait crea HUD")
    player_hud=[r for r in rules if r.name.startswith("02b - HUD Pemain:")]
    checks.equal(len(player_hud),1,"HUD player separato")
    if player_hud:
        pc=mask_strings(player_hud[0].body)
        checks.equal(pc.count("Create HUD Text("),2,"HUD player sinistro/destra")
        checks.require("Wait(" not in pc and "Loop If Condition Is True;" not in pc,"HUD player contiene Wait/Loop")

'''
v=v[:ins]+audit+v[ins:]
VAL.write_text(v,encoding="utf-8")
VERSION.write_text("0.6.15\n",encoding="utf-8")

# Docs.
for path,old,new in [
    (README,"La versione **0.6.14** identifica lo stato funzionale e tecnico corrente del repository.","La versione **0.6.15** identifica lo stato funzionale e tecnico corrente del repository."),
    (PROGETTO,"# Note di progetto — versione 0.6.14","# Note di progetto — versione 0.6.15"),
    (TEST,"# Piano di test — versione 0.6.14","# Piano di test — versione 0.6.15"),
    (VALIDAZIONE,"# Rapporto di validazione — versione 0.6.14","# Rapporto di validazione — versione 0.6.15"),
]:
    t=path.read_text(encoding="utf-8"); t=once(t,old,new,str(path)); path.write_text(t,encoding="utf-8")

p=PROGETTO.read_text(encoding="utf-8"); p=once(p,"Workshop 0.6.14.","Workshop 0.6.15.","progetto version"); PROGETTO.write_text(p,encoding="utf-8")
t=TEST.read_text(encoding="utf-8"); t=once(t,"Workshop 0.6.14.","Workshop 0.6.15.","test version"); TEST.write_text(t,encoding="utf-8")
vdoc=VALIDAZIONE.read_text(encoding="utf-8"); vdoc=once(vdoc,"Release tecnica: **CHILL Dedicated Server 0.6.14**","Release tecnica: **CHILL Dedicated Server 0.6.15**","release"); vdoc=once(vdoc,"OK - controlli statici v0.6.14 superati","OK - controlli statici v0.6.15 superati","result")
README.write_text(README.read_text(encoding="utf-8")+'\n\n### HUD edge-triggered 0.6.15\nIl Main Menu viene creato invisibile mentre inizia il hold Melee e a 0,5 s cambia solo la visibilità. I sottomenu vengono preparati quando sono evidenziati. Nessuna regola che esegue `Create HUD Text` contiene `Wait` o `Loop`. Anche gli HUD sociali del giocatore sono separati dalla classificazione umano/bot.\n',encoding="utf-8")
PROGETTO.write_text(PROGETTO.read_text(encoding="utf-8")+'\n\n## HUD edge-triggered 0.6.15\nLa creazione HUD è separata da timer e loop. 05a prepara Main + pagina selezionata senza attese; 02b crea i due HUD sociali dopo la classificazione, anch’essa senza attese nella regola HUD.\n',encoding="utf-8")
TEST.write_text(TEST.read_text(encoding="utf-8")+'\n\n## Timing HUD 0.6.15\nVerificare che il Main compaia esattamente alla soglia Melee di 0,5 s, che i sottomenu non abbiano pop al primo accesso e che i due HUD sociali compaiano dopo la classificazione senza ritardo aggiuntivo.\n',encoding="utf-8")
vdoc += '\n\n## Audit HUD 0.6.15\nIl gate rifiuta qualsiasi regola `Create HUD Text` che contenga `Wait` o `Loop If Condition Is True`.\n'
data=SRC.read_bytes().replace(b"\r\n",b"\n"); blob=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest(); vdoc,n=re.subn(r"(Blob Git del sorgente Workshop validato:\n\n```text\n)[0-9a-f]{40}(\n```)",rf"\g<1>{blob}\g<2>",vdoc,count=1)
if n!=1: raise RuntimeError("blob marker")
VALIDAZIONE.write_text(vdoc,encoding="utf-8")
print("Applied CHILL 0.6.15 zero-wait HUD creation architecture")
