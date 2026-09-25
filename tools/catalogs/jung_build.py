"""Jung Pumpen (Pentair): Produktkatalog Abwassertechnik, Ausgabe 2 (11.2019) — таблицы «Förderhöhe H → Fördermenge Q»."""
import pymupdf,re,json
from common import rec,save
URL='https://www.jung-pumpen.de/fileadmin/user_upload/website/Service/Downloads/Prospekte/DE/AT_Katalog_DE_Ausgabe_2.pdf'
d=pymupdf.open('p3/jung_at.pdf')
def num(s):
    try: return float(s.replace(',','.'))
    except: return None
def rows(W,tol=2.5):
    R=[]
    for w in sorted(W,key=lambda w:(w[1]+w[3])/2):
        yc=(w[1]+w[3])/2
        if R and abs(R[-1][0]-yc)<tol: R[-1][1].append(w)
        else: R.append([yc,[w]])
    return [(y,sorted(ws,key=lambda w:w[0])) for y,ws in R]
recs=[];log=[]
for pi,p in enumerate(d):
    W=p.get_text('words'); t=p.get_text()
    if 'Förderhöhe' not in t: continue
    R=rows(W)
    head=[(y,ws) for y,ws in R if any(w[4]=='Förderhöhe' for w in ws)]
    series=re.search(r'\n?([A-ZÄÖÜ][A-ZÄÖÜ0-9 \-–/]{3,40})\n',t)
    ttl=[l for l in t.split('\n') if l.strip()][:3]
    for hy,hws in head:
        k=[i for i,w in enumerate(hws) if w[4]==']' or w[4].endswith('[m]') or w[4]=='[m]']
        Hs=[((w[0]+w[2])/2,num(w[4])) for w in hws if num(w[4]) is not None and w[0]>hws[0][0]+40]
        if len(Hs)<3: continue
        xH0=Hs[0][0]
        # строки моделей до пустого промежутка
        for y,ws in R:
            if not (hy+3<y<hy+120): continue
            if any(w[4] in ('Konstruktionsänderungen','Typ') for w in ws): break
            names=[w for w in ws if w[2]<xH0-15 and num(w[4]) is None or (w[2]<xH0-60)]
            Q={}
            for w in ws:
                v=num(w[4]); xc=(w[0]+w[2])/2
                if v is None or xc<xH0-12: continue
                j=min(range(len(Hs)),key=lambda j:abs(Hs[j][0]-xc))
                if abs(Hs[j][0]-xc)<8: Q[j]=v
            name=' '.join(w[4] for w in ws if w[2]<xH0-12 and not re.match(r'^(Fördermenge|Q|\[m³/h\]|\[m3/h\])$',w[4]))
            name=re.sub(r'\s*Fördermenge.*','',name).strip()
            if not name or len(Q)<2: continue
            pts=sorted((Q[j],Hs[j][1]) for j in Q)
            if any(b[0]<=a[0] for a,b in zip(pts,pts[1:])): log.append((name,f'стр.{pi+1}: Q не убывает с ростом H — проверить')); continue
            recs.append(dict(page=pi+1,name=name,pts=pts,title=' '.join(ttl)))
    # таблица мотора
    for y,ws in R:
        pass
print(len(recs)); 
for r in recs[:15]: print(r['page'],r['name'],r['pts'][:4],r['title'][:60])
json.dump(recs,open('out/jung_raw.json','w'),ensure_ascii=False)
# ---- моторы ----
SPEC={}
for pi,p in enumerate(d):
    for y,ws in rows(p.get_text('words')):
        s=' '.join(w[4] for w in ws)
        kws=re.findall(r'(\d+,\d+|\d+) kW',s)
        if len(kws)<2: continue
        m=re.match(r'^(.+?)\s+(?:JP\d+\s+)?(\d?/?N?/?PE~\d+(?:/\d+)?\s*V|\d/N/PE~|1/N/PE|3/PE|3/N/PE)',s)
        if not m: continue
        name=m.group(1).strip()
        v=re.search(r'(1/N/PE|3/N/PE|3/PE)~?\s*([\d/]+)\s*V',s)
        mm=re.search(r'(\d+)\s*mm',s); dn=re.search(r'DN\s*(\d+)',s); kg=re.search(r'(\d+(?:,\d+)?)\s*kg',s); a=re.search(r'(\d+(?:,\d+)?)\s*A\b',s)
        SPEC.setdefault(name,[]).append(dict(page=pi+1,p1=num(kws[0]),p2=num(kws[1]),volt=(('1~' if v.group(1).startswith('1') else '3~')+v.group(2)+' В') if v else '',
            passage=num(mm.group(1)) if mm else 0,dn=int(dn.group(1)) if dn else 0,kg=num(kg.group(1)) if kg else 0,amp=num(a.group(1)) if a else 0))
print('моторов',len(SPEC))
out=[];miss=[]
for r in recs:
    base=r['name']; pg=r['page']
    m=re.match(r'^(.*?\S)\s+([A-Z]{1,3}(?:/[A-Z]{1,3})+)$',base)
    variants=[m.group(1)+' '+s for s in m.group(2).split('/')] if m else [base]
    t=d[pg-1].get_text()+d[pg-2].get_text()
    rpm=re.search(r'N\s*=\s*(\d{3,4})\s*MIN',t.upper()); rpm=int(rpm.group(1)) if rpm else 0
    CAT={'SCHMUTZWASSERPUMPEN','ABWASSERPUMPEN','BAUPUMPEN','HEISSWASSERPUMPEN','KELLERENTWÄSSERUNGSPUMPEN','DRAINAGEPUMPEN','EX-GESCHÜTZTE','FLACHABSAUGENDE','PUMPE'}
    lines=[l.strip() for l in (d[pg-1].get_text().split('\n')[:5])]
    prod=[l for l in lines if l and not l.isdigit() and not set(l.upper().split())<=CAT and 'JUNG' not in l.upper() and not l.upper().startswith('EX-GESCH')]
    series=prod[0].title().replace('Us ','US ').replace('Ub ','UB ').replace('Uv','UV').replace('Ex-','EX-') if prod else 'Jung'
    series=re.sub(r'\s*\d+.*$','',series) if re.match(r'^Multi',series) else series
    found=False
    for v in variants:
        cand=[s for s in SPEC.get(v,[]) if abs(s['page']-pg)<=4]
        if not cand: continue
        s=min(cand,key=lambda s:abs(s['page']-pg)); found=True
        model=v if not re.match(r'^\d',v) else f"{series} {v}"
        out.append(rec("Jung Pumpen",series,model,"Германия",Application='дренажный/канализационный погружной',P1Kw=s['p1'],P2Kw=s['p2'],
            Voltage=(s['volt']+' 50 Гц').strip(),FreePassageMm=s['passage'],DnOut=s['dn'],WeightKg=s['kg'],Rpm=rpm,Poles=2 if rpm>2000 else 4 if rpm>1000 else 0,
            QH=r['pts'],Document=f"Jung Pumpen «Produktkatalog Abwassertechnik», Ausgabe 2 (11.2019), стр. {pg}",Url=URL,
            Notes=f"Точки таблицы каталога «Förderhöhe H – Fördermenge Q» (для строки «{base}»); точка Q=0 в таблице не дана. Iном {s['amp']:g} А."))
    if not found:
        model=base if not re.match(r'^\d',base) else f"{series} {base}"
        out.append(rec("Jung Pumpen",series,model,"Германия",Application='дренажный/канализационный погружной',Rpm=rpm,Voltage='50 Гц',Poles=2 if rpm>2000 else 4 if rpm>1000 else 0,
            QH=r['pts'],Document=f"Jung Pumpen «Produktkatalog Abwassertechnik», Ausgabe 2 (11.2019), стр. {pg}",Url=URL,
            Notes="Точки таблицы каталога «Förderhöhe H – Fördermenge Q»; точка Q=0 в таблице не дана. Данные мотора рядом с таблицей не найдены (P2=0 — неизвестно)."))
seen=set();res=[]
for x in out:
    if x['Id'] in seen: continue
    seen.add(x['Id']); res.append(x)
save('out/jung.json',res); json.dump(log+miss,open('out/jung_excluded.json','w'),ensure_ascii=False,indent=1)
print('без мотора',len(miss),miss[:12])
