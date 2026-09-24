import pymupdf,re,json,sys
from common import *
F='Dreno_catalogue_2022_rev0.pdf'; URL='https://www.drenopompe.it/pdf/Dreno_catalogue_2022_rev0.pdf'
d=pymupdf.open(F)
SECT=[(13,20,'Compatta','Vortex','свободновихревое','канализационный погружной (бытовой)'),
 (21,26,'Compatta PRO','Vortex','свободновихревое','канализационный погружной (бытовой)'),
 (27,34,'Alpha V','Vortex','свободновихревое','канализационный погружной (бытовой)'),
 (35,40,'Alpha V PRO','Vortex','свободновихревое','канализационный погружной (бытовой)'),
 (41,54,'DNA','Vortex','свободновихревое','канализационный погружной'),
 (55,64,'V2','Vortex','свободновихревое','канализационный погружной'),
 (65,72,'VTH','Vortex','свободновихревое','канализационный погружной'),
 (73,88,'V4','Vortex','свободновихревое','канализационный погружной'),
 (89,100,'DNB','MultiChannel','двухканальное S-Flow','канализационный погружной'),
 (101,110,'A2','SingleChannel','одноканальное открытое','канализационный погружной'),
 (111,130,'A4','SingleChannel','одноканальное открытое','канализационный погружной'),
 (131,140,'ATH','MultiChannel','двухканальное центробежное','канализационный погружной (чистая вода / слабозагрязнённые стоки)'),
 (141,156,'Grinder','Grinder','измельчитель на входе','канализационный погружной (напорная канализация)'),
 (157,168,'BIC / BIC PRO','MultiChannel','двухканальное «a rasamento»','дренажный (чистая / слабозагрязнённая вода)'),
 (169,174,'APX','MultiChannel','двухканальное «a rasamento»','дренажный (высоконапорный)'),
 (175,180,'APX PRO','MultiChannel','двухканальное «a rasamento»','дренажный (высоконапорный)'),
 (181,188,'H2','MultiChannel','двух-/четырёхканальное','дренажный (высоконапорный)'),
 (197,202,'Perfecta','Unknown','—','дренажный (коррозионностойкий)')]
def sect(pn):
    for a,b,*r in SECT:
        if a<=pn<=b: return r
def clean(s): return re.sub(r'\s+',' ',s or '').strip()
recs={}; specs={}
for pi,p in enumerate(d):
    pn=pi+1; S=sect(pn)
    if not S: continue
    tabs=[t.extract() for t in p.find_tables().tables]
    hdr=' '.join(clean(c) for t in tabs[:1] for r in t for c in r if c)
    for x in tabs:
        # ---- QH table
        qi=next((i for i,r in enumerate(x) if any(clean(c)=='m3/h' for c in r)),None)
        if qi is not None and any(clean(c)=='mt' for r in x for c in r):
            qr=x[qi]; qcol={j:num(clean(c)) for j,c in enumerate(qr) if c and num(clean(c)) is not None}
            li=next((i for i,r in enumerate(x) if any(clean(c)=='l/s' for c in r)),None)
            if li is not None:
                ls={j:num(clean(c)) for j,c in enumerate(x[li]) if c and num(clean(c)) is not None}
                for j in qcol:
                    if j in ls and abs(ls[j]*3.6-qcol[j])>0.06*max(1,qcol[j]):
                        print('Q MISMATCH p',pn,ls[j],qcol[j]); qcol[j]=round(ls[j]*3.6,2)
            for r in x[qi+1:]:
                if not r[0] or not re.fullmatch(r'\d+',clean(r[0])): continue
                typ=clean(r[1]); pts=[]
                for j,q in qcol.items():
                    v=num(clean(r[j])) if j<len(r) and r[j] else None
                    if v is not None: pts.append((q,v))
                if typ and pts: recs.setdefault(typ,(pn,clean(r[0]),pts,hdr))
        # ---- spec table
        hi=next((i for i,r in enumerate(x) if any('Passaggio' in (c or '') for c in r)),None)
        if hi is not None:
            H=[clean(a)+' '+clean(b) for a,b in zip(x[hi],x[hi+1])]
            def col(pat):
                return next((j for j,h in enumerate(H) if re.search(pat,h)),None)
            cols={k:col(v) for k,v in dict(dn='Mandata|Delivery',fp='Passaggio',p1=r'\bP1\b',p2=r'^\s*P2\b|\bP2\s*$',rpm='R\.P\.M',i1='1 Phase',i3='3 Phase',kw=r'^kW').items()}
            if cols['p2'] is None: cols['p2']=col(r'\bP2\b')
            if cols['p2']==cols['p1']:
                cols['p2']=next((j for j,h in enumerate(H) if j>cols['p1'] and re.search(r'\bP2\b',h)),cols['p1']+1)
            if cols['p1'] is None and cols['kw'] is not None: cols['p1']=cols['kw']
            last={}
            for r in x[hi+2:]:
                if not r[0] or not re.fullmatch(r'\d+',clean(r[0])): continue
                typ=clean(r[1]); v={}
                for k,j in cols.items():
                    if j is None or j>=len(r): continue
                    c=r[j]
                    if c is None: c,idx=last.get(k,('',0)); idx+=1
                    else: idx=0
                    last[k]=(c,idx)
                    parts=[z for z in (c or '').split('\n') if z.strip()]
                    v[k]=clean(parts[min(idx,len(parts)-1)]) if len(parts)>1 and k not in('dn','fp') else clean(c)
                if typ: specs.setdefault(typ,v)
# стр. 127: в PDF две наложенные версии таблицы двигателей; берём видимую (верхний слой), сверено по растру
for t,(p1,p2) in {'AT 150/4/340 C.285':('33','30'),'AT 150/4/340 C.290':('42','40'),'AT 150/4/340 C.295':('54,6','51'),'AT 150/4/340 C.300':('64','60')}.items():
    specs[t].update(p1=p1,p2=p2)
# APX PRO (стр. 179): таблица без линеек — перенесено вручную с раскладки слов
QA=[1.8,3.6,5.4,7.2,9,10.8,12.6,14.4,16.2,18,19.8,21.6,25.2,28.8]
for t,h,p1,p2 in [('APX PRO 50-2/110 M/T',[17,15.5,14,12,11,9.5,8.5,7,6,5,4],'1,5','1,1'),
                  ('APX PRO 50-2/150 M/T',[21,19,17,16,14.5,13,12,10.5,9.5,8.5,7,5,4],'2,1','1,5'),
                  ('APX PRO 50-2/220 T',[26.5,24.5,22.5,21,19,17.5,16,14.5,13,12,10.5,9,6.5,4],'2,5','2,2')]:
    recs[t]=(179,'',list(zip(QA,h)),'')
    specs[t]=dict(dn='DN32 - PN6 G 2”',fp='-',p1=p1,p2=p2,rpm='2850',i1='8,0' if 'M/T' in t else '',i3='x')
def inch_dn(s):
    m=re.search(r'DN\s?(\d+)',s)
    if m: return int(m.group(1))
    m=re.search(r'(?:G|NPT)\s*(\d)\s*[”"]?\s*(?:(\d)\s*/\s*(\d))?',s)
    if not m: return 0
    v=int(m.group(1))+(int(m.group(2))/int(m.group(3)) if m.group(2) else 0)
    return {1:25,1.25:32,1.5:40,2:50,2.5:65,3:80}.get(v,0)
out=[]
for typ,(pn,no,pts,hdr) in recs.items():
    series,imp,imptxt,app=sect(pn)
    s=specs.get(typ,{})
    if not s: print('NO SPEC',pn,typ)
    dn=inch_dn(s.get('dn',''))
    m=re.search(r'([\d,]+)(?:\s*x\s*([\d,]+))?\s*mm',s.get('fp',''))
    fp=min(num(z) for z in m.groups() if z) if m else 0
    rpm=int(num(s.get('rpm','').split()[0]) or 0) if s.get('rpm') else 0
    mp=re.search(r'\d+\s*[-/]\s*(\d)\s*[-/]',typ)
    poles=int(mp.group(1)) if mp else (2 if rpm>2000 else 4 if rpm>1000 else 2)
    if not rpm: rpm=RPM[poles]
    nf=lambda z: num((z or '').split()[0]) if (z or '').split() else None
    p1=nf(s.get('p1')) or 0; p2=nf(s.get('p2')) or 0
    one=bool(re.search(r'\d',s.get('i1','') or '')) or bool(re.search(r'\bV?M\b|\bM/T|\bM$|[A-Z]M-',typ))
    three=bool(re.search(r'\d',s.get('i3','') or '')) or 'T' in typ.split()[-1]
    volt='1~230 В / 3~400 В' if one and three else ('1~230 В' if one else '3~400 В')
    fp_note=f" Свободный проход {s.get('fp')}." if s.get('fp') and not fp else ''
    notes=f"Рабочее колесо: {imptxt}. Таблица каталога начинается не с Q=0 (напор при закрытой задвижке не приведён)." if pts[0][0]>0 else f"Рабочее колесо: {imptxt}."
    notes+=f" Патрубок: {s.get('dn','')}."+fp_note+" M — 1~230 В, T — 3~400 В; ATEX по запросу."
    out.append(rec("Dreno Pompe",series,typ,"Италия",Application=app,Impeller=imp,HasCutter=imp=='Grinder',
        DnOut=dn,FreePassageMm=fp,P2Kw=p2,P1Kw=p1,Rpm=rpm,Poles=poles,Voltage=volt,QH=sorted(pts),
        Document=f"Dreno Pompe «Catalogo – Catalogue 50Hz 2022 rev.0», серия {series}, стр. {pn} (печатн. {pn-1})",Url=URL,Notes=notes))
save('out/dreno.json',out)
import collections
print(collections.Counter(r['Series'] for r in out))
for r in out:
    if not r['P2Kw'] or not r['DnOut'] : print('chk',r['Model'],r['P2Kw'],r['DnOut'],r['FreePassageMm'],r['Rpm'],r['Notes'][-80:])
