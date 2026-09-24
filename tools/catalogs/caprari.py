import pymupdf,re,json
from rows import rows
from common import *
F='KC-GBFI-996485X_09-24_compressed.pdf'
URL='https://www.caprari.com/wp-content/uploads/2024/09/KC-GBFI-996485X_09-24_compressed.pdf'
d=pymupdf.open(F)
CODE=re.compile(r'^K[A-Z]{2}\d{3}[A-Z]{2}\+\d{6}[NX]\d$')
curves={}; qvals_all={}; free={}; weight={}; motors={}; etas={}
for pi,p in enumerate(d):
    R=rows(p); t=p.get_text()
    # efficiency labels
    if 'max %' in t:
        m=re.search(r'H\n\[ft\]\n(.*?)\nη\nmax %',t,re.S)
        fam=None
        if m:
            last=None; em={}
            for tok in m.group(1).split():
                if re.fullmatch(r'\d+\.\d+',tok): last=float(tok)
                elif re.fullmatch(r'\d+',tok) and last is not None: em[int(tok)]=last; last=None
            etas[pi]=em
    qrow=None
    for y,r in R:
        txt=[w[4] for w in r]
        if '[m3/h]' in txt:
            qrow=[(w[0]+w[2])/2 for w in r if num(w[4]) is not None and w[0]>(r[txt.index('[m3/h]')][2])]
            qvals=[num(w[4]) for w in r if num(w[4]) is not None and w[0]>(r[txt.index('[m3/h]')][2])]
            continue
        codes=[w for w in r if CODE.match(w[4])]
        if not codes: continue
        c=codes[0]; code=c[4]; after=[w for w in r if w[0]>c[2]]
        at=[w[4] for w in after]
        if qrow and '[m]' in at:
            k=at.index('[m]')
            curve_no=int(at[0]); p2=num(at[1])
            pts=[]
            for w in after[k+1:]:
                v=num(w[4]); xc=(w[0]+w[2])/2
                j=min(range(len(qrow)),key=lambda j:abs(qrow[j]-xc))
                if abs(qrow[j]-xc)<11 and v is not None: pts.append((qvals[j],v))
            curves.setdefault(code,(pi+1,curve_no,p2,pts)); qvals_all[pi+1]=qvals
        elif at[:1]==['Ø'] and len(at)>2:
            free.setdefault(code,min(num(x) for x in at[1].split('x'))); weight.setdefault(code,num(at[2]))
    for y,r in R:
        for i,w in enumerate(r):
            m=re.fullmatch(r'KC(\d{5})\.\.[A-Z]\d{3}\.\.',w[4])
            if m and i+2<len(r):
                v=[num(x[4]) for x in r[i+1:i+4]]
                if v[0] and v[1]: motors.setdefault(m.group(1),(v[0],v[1],v[2]))
IMP={'W':('Vortex','свободновихревое (torque-flow recessed)'),'M':('SingleChannel','одноканальное'),
     'D':('MultiChannel','двухканальное'),'A':('Open','открытое двухлопастное (twin blade)')}
recs=[]
for code,(page,cn,p2,pts) in curves.items():
    fam=code[:7]; dig=code[code.index('+')+1:]; mot=dig[:5]; poles=int(dig[4])
    ptsd=sorted(dict(pts).items())
    tq=[q for q,_ in ptsd]; qmin=qmax=0
    if len(tq)>1 and tq[0]==0 and qvals_all[page][1]<tq[1]-1e-6: qmin=tq[1]
    if tq[-1]<qvals_all[page][-1]-1e-6: qmax=tq[-1]
    imp,imptxt=IMP[code[2]]
    p1=motors.get(mot,(0,0,0))[0]
    eta=etas.get(page-1,{}).get(cn,0)
    atex=code[-2]=='X'
    notes=[f"Рабочее колесо: {imptxt}. Кривая №{cn} на графике {fam} (стр. {page})."]
    if eta: notes.append(f"NominalEta = ηmax гидравлики по графику каталога ({eta} %).")
    if qmin or qmax: notes.append("RangeQmin/RangeQmax — границы, в которых каталог приводит напоры (пустые ячейки таблицы вне диапазона).")
    if atex: notes.append("Взрывозащищённое исполнение (ATEX, *X).")
    notes.append("Колёса обтачиваются под рабочую точку (по каталогу).") if code[2] in 'WDA' else None
    recs.append(rec("Caprari","K+ "+code[:3],code,"Италия",Impeller=imp,DnOut=int(code[3:6]),
        FreePassageMm=free.get(code,0) or 0,P2Kw=p2,P1Kw=p1,Rpm=RPM[poles],Poles=poles,
        WeightKg=weight.get(code,0) or 0,NominalEta=eta,QH=ptsd,RangeQmin=qmin,RangeQmax=qmax,
        Document=f"Caprari «K+ Electric submersible sewage pumps 50 Hz», cod. 996485X/09-24 — таблица Q–H, стр. {page}; размеры/масса и данные двигателей — там же",
        Url=URL,Notes=" ".join(notes)))
recs.sort(key=lambda r:(int(r["Model"][3:6]),r["Model"]))
missing=[r["Model"] for r in recs if not r["FreePassageMm"] or not r["P1Kw"] or not r["WeightKg"]]
print("missing extras:",len(missing),missing[:10])
save('out/caprari.json',recs)
for r in recs[:3]+recs[-2:]: print(r["Model"],r["P2Kw"],r["P1Kw"],r["FreePassageMm"],r["WeightKg"],r["NominalEta"],r["Curve"]["QH"][:3],len(r["Curve"]["QH"]))
