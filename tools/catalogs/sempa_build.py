"""Sempa DPT: записи по диаметрам колеса; проверка графиков балансом мощности."""
import pymupdf,re,json,numpy as np
from sempa_dig import page_curves,num,ocr_words
from common import rec,save
URL='https://sempapompa.com/writable/uploads/medias/files/katalog/DPT%20KATALOG.pdf'
d=pymupdf.open('sempa/dpt.pdf')
IMP={'BC.1':('Cutter','открытое с режущим ножом'),'BC.2':('Cutter','открытое с режущим ножом'),'BC.3':('Cutter','открытое с износной плитой и режущим ножом'),
     'SO':('Open','полуоткрытое'),'VX':('Vortex','свободновихревое'),'Vx':('Vortex','свободновихревое'),
     'D':('Unknown','закрытое ширококанальное'),'L':('Unknown','закрытое ширококанальное'),'DS':('Unknown','закрытое двустороннего входа')}
TIT=re.compile(r'DPT-F\d\s+\d+(?:-\d+)?\s+(?:BC\.\d|SO|Vx|VX|DS|D|L)?\s*\d?P?(?:/\dP)?')
def motors(t):
    toks=[x.strip() for x in t.split('\n') if x.strip()]; out=[]
    for i,x in enumerate(toks):
        if x=='kW':
            kw=[];j=i+1
            while j<len(toks) and num(toks[j]) is not None: kw.append(num(toks[j])); j+=1
            rp=[]
            if j<len(toks) and toks[j]=='rpm/P':
                j+=1
                while j<len(toks) and re.fullmatch(r'\d{3,4}/\d',toks[j]): rp.append(toks[j]); j+=1
            if kw and rp and len(kw)==len(rp): out+= [(k,int(r.split('/')[0]),int(r.split('/')[1])) for k,r in zip(kw,rp)]
    return out
def rho_check(C):
    """КПД по кривым H,P против кривой η — при верной шкале отношение ≈1."""
    rs=[]
    for dd,E in C.get('E',{}).items():
        if dd not in C.get('H',{}) or dd not in C.get('P',{}): continue
        H=np.array(C['H'][dd]); P=np.array(C['P'][dd]); E=np.array(E)
        qe=E[np.argmax(E[:,1]),0]; e=E[:,1].max()/100
        if not (H[0,0]<=qe<=H[-1,0] and P[0,0]<=qe<=P[-1,0]): continue
        h=np.interp(qe,H[:,0],H[:,1]); p=np.interp(qe,P[:,0],P[:,1])
        rs.append(9.81*qe/3600*h/e/p)
    return rs
recs=[];log=[];title=None;spec=''
for i,p in enumerate(d):
    t=p.get_text()
    m=TIT.search(t.replace('\n',' '))
    if 'rpm/P' in t: spec=t; title=m.group(0).strip() if m else title
    if 'Selection Charts' not in t: continue
    if m: title=m.group(0).strip()
    C=page_curves(p)
    ocrd=False
    if not C.get('H'): C=page_curves(p,ocr_words(p)); ocrd=True
    if not C.get('H'): log.append((f'стр. {i+1} {title}','кривые Q–H не выделены')); continue
    rs=rho_check(C)
    if not rs or not all(0.8<r<1.25 for r in rs):
        log.append((f'стр. {i+1} {title}',f'баланс мощности не сходится (ρgQH/η/P = {[round(r,2) for r in rs]}) — ошибка шкалы в каталоге или нет кривой КПД')); continue
    poles=[int(x) for x in re.findall(r'(\d)P',title.split()[-1])] if title else []
    lab_p=re.findall(r'\b\d+(?:[.,]\d+)?/(\d)\b',t)
    if lab_p: poles=[int(max(set(lab_p),key=lab_p.count))]
    if len(poles)!=1: log.append((f'стр. {i+1} {title}','не определено число полюсов для графика')); continue
    pol=poles[0]; mot=[x for x in motors(spec) if x[2]==pol]
    rpm=int(np.median([x[1] for x in mot])) if mot else {2:2900,4:1450,6:960}[pol]
    parts=title.split(); code=next((x for x in parts if x in IMP),None)
    imp,imptxt=IMP.get(code,('Unknown',''))
    dn=int(re.search(r'\s(\d+)(?:-\d+)?\s',' '+title+' ').group(1)) if re.search(r'\s(\d+)(?:-\d+)?\s',' '+title+' ') else 0
    base=re.sub(r'\s*\d?P(?:/\dP)?$','',title).strip()
    for dd,H in C['H'].items():
        P=C.get('P',{}).get(dd,[]); E=C.get('E',{}).get(dd,[]); N=C.get('N',{}).get(dd,[])
        def thin(c,n=25):
            c=[(max(0.0,round(a,3)),round(b,3)) for a,b in c]; idx=np.linspace(0,len(c)-1,min(n,len(c))).astype(int); out=[]
            for k in idx:
                if not out or c[k][0]>out[-1][0]: out.append(c[k])
            return out
        pmax=max(v for _,v in P) if P else 0
        mk=[x for x in mot if x[0]>=pmax*0.98] if P else []
        p2=min(mk)[0] if mk else 0
        model=f"{base} {pol}P Ø{dd}"
        note=(f"Рабочее колесо {code}: {imptxt}, диаметр {dd} мм. Кривые оцифрованы с векторного графика «Selection Charts» (стр. {i+1}); "
              f"{'подписи осей и диаметров распознаны OCR (в PDF они в кривых); ' if ocrd else ''}шкала проверена балансом мощности ρgQH/η≈P (отклонение {abs(np.mean(rs)-1)*100:.0f} %). ")
        if mot: note+=f"Моторы в каталоге для этого насоса ({pol}P): {', '.join(f'{x[0]:g}' for x in mot)} кВт; P2Kw — наименьший из них, покрывающий кривую мощности (макс. {pmax:.1f} кВт). "
        recs.append(rec("Sempa","DPT",model,"Турция",Application='канализационный погружной',Impeller=imp,HasCutter=imp=='Cutter',DnOut=dn,
            P2Kw=p2,Rpm=rpm,Poles=pol,Voltage='3~400 В 50 Гц',ImpellerDmm=dd,QH=thin(H),QP=thin(P),QEta=[(q,e/100) for q,e in thin(E)],QNpsh=thin(N),
            Document=f"Sempa «DPT Series. Submersible waste water centrifugal pump», изд. 01.2024 v1, стр. {i+1}",Url=URL,Notes=note.strip()))
seen=set();out=[]
for r in recs:
    if r['Id'] in seen: continue
    seen.add(r['Id']); out.append(r)
save('out/sempa.json',out); json.dump(log,open('out/sempa_excluded.json','w'),ensure_ascii=False,indent=1)
for l in log: print(l)
