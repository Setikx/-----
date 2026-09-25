"""Speroni (Италия): таблицы Q–H общего каталога 2021 (rev15, FR/ES), погружные дренажные и канализационные насосы."""
import pymupdf,re,json
from common import rec,save
URL='https://www.speroni.it/pub/media/cataloghi/SPERONI-cat-Gen-2021-FR-ES-rev15.pdf'
d=pymupdf.open('p3/speroni2021.pdf')
PAGES=[175,177,179,181,183,185,187,191,193,195,197,199,201,203,205,207,209,211,213,215,217,219,221,223,225,227]
def num(s):
    try: return float(s.replace(',','.'))
    except: return None
def rows(W,tol=2.2):
    R=[]
    for w in sorted(W,key=lambda w:(w[1]+w[3])/2):
        yc=(w[1]+w[3])/2
        if R and abs(R[-1][0]-yc)<tol: R[-1][1].append(w)
        else: R.append([yc,[w]])
    return [(y,sorted(ws,key=lambda w:w[0])) for y,ws in R]
recs=[];log=[]
for pi in PAGES:
    p=d[pi]; W=[w for w in p.get_text('words') if w[4] not in ('H','(m)','(ft)')]; R=rows(W)
    # заголовок страницы-описания (предыдущая) → тип
    prev=d[pi-1].get_text().replace('\n',' ')
    title=re.search(r'ÉLECTROPOMPES?[^.]{0,120}?(?=APPLICATIONS|APLICACIONES|LIMITES|$)',prev); title=title.group(0).strip() if title else ''
    # строка расходов м³/ч
    qrow=None
    for y,ws in R:
        t=[w[4] for w in ws]
        if any(x in ('m3/h','m³/h') for x in t):
            k=[i for i,x in enumerate(t) if x in ('m3/h','m³/h')][0]
            qs=[(w,num(w[4])) for w in ws[k+1:] if num(w[4]) is not None]
            if len(qs)>=3: qrow=(y,[((w[0]+w[2])/2,v) for w,v in qs]); break
    if not qrow: log.append((f'стр.{pi+1}','нет строки расходов')); continue
    yq,QC=qrow; x0q=QC[0][0]
    hp=[w for y,ws in R for w in ws if w[4]=='HP' and abs(y-yq)<30]
    mono=[(w[0]+w[2])/2 for w in W if re.match(r'Mono',w[4]) and yq-40<w[1]<yq+25]
    tri=[(w[0]+w[2])/2 for w in W if re.match(r'Tri',w[4]) and yq-40<w[1]<yq+25]
    ph_=[w[0] for w in W if w[4] in ('HP','PUISSANCE','POTENZA','POTENCIA','P1','P2') and yq-60<w[1]<yq+10]
    xhp=min(ph_) if ph_ else (hp[0][0] if hp else x0q-120)
    # строки моделей: ниже заголовка, до таблицы размеров
    ystop=min([y for y,ws in R if y>yq and any(w[4] in ('DIMENSIONS','DIMENSIONES','DIMENSIONI') for w in ws)]+[1e9])
    RR=[[y,list(ws)] for y,ws in R if yq+12<y<ystop]
    used=set()
    for i,(y,ws) in enumerate(RR):
        onlyname=all(w[2]<xhp-2 for w in ws); onlynum=all(w[0]>=xhp-2 for w in ws)
        if onlyname:
            c=[j for j,(y2,ws2) in enumerate(RR) if j!=i and abs(y2-y)<5 and all(w[0]>=xhp-2 for w in ws2) and j not in used]
            if c:
                j=min(c,key=lambda j:abs(RR[j][0]-y)); RR[j][1]+=ws; used.add(j); RR[i][1]=[]
    for y,ws in RR:
        if not ws: continue
        names=[w for w in ws if w[2]<xhp-2]
        nums=[(w,num(w[4])) for w in ws if w[0]>=xhp-2 and num(w[4]) is not None]
        if not names or not nums: continue
        # H — числа под столбцами расхода
        H={}
        for w,v in nums:
            xc=(w[0]+w[2])/2
            j=min(range(len(QC)),key=lambda j:abs(QC[j][0]-xc))
            if abs(QC[j][0]-xc)<9 and xc>x0q-12: H[j]=v
        pre=[v for w,v in nums if (w[0]+w[2])/2<x0q-12]
        if len(H)<3 or len(pre)<2: continue
        qh=sorted((QC[j][1],h) for j,h in H.items())
        if any(b>a+0.05 for (_,a),(_,b) in zip(qh,qh[1:])): log.append((' '.join(w[4] for w in names),f'стр.{pi+1}: напор растёт — проверить')); continue
        # имена: разделяем моно/трёхфазные по разрыву x
        names.sort(key=lambda w:w[0]); groups=[[names[0]]]
        for w in names[1:]:
            if w[0]-groups[-1][-1][2]>8: groups.append([w])
            else: groups[-1].append(w)
        models=[(' '.join(w[4] for w in g),(g[0][0]+g[-1][2])/2) for g in groups]
        watt=any(w[4]=='W' for w in ws)
        if watt: hpv,kw,p1=0,0,pre[0]/1000
        else: hpv,kw,p1=pre[0],pre[1],0
        for k,(m,xm) in enumerate(models):
            if not re.search(r'[A-Z]{2}',m): continue
            dm=min([abs(x-xm) for x in mono]+[1e9]); dt=min([abs(x-xm) for x in tri]+[1e9])
            ph='1~230 В' if dm<dt else '3~400 В' if dt<1e9 else ''
            imp='Vortex' if 'VORTEX' in title.upper() else 'SingleChannel' if 'MONOCANAL' in title.upper() else 'Grinder' if 'BROYEUR' in title.upper() else 'Open' if 'DRAINAGE' in title.upper() else 'Unknown'
            recs.append(rec("Speroni",re.match(r'[A-Z]+',m).group(0),m,"Италия",Application='дренажный/канализационный погружной',Impeller=imp,
                HasCutter=imp=='Grinder',P2Kw=kw,P1Kw=p1,Voltage=(ph+' 50 Гц').strip(),Rpm=2900,Poles=2,QH=qh,
                Document=f"Speroni, Catalogue général 2021 (rev.15), стр. {pi+1}: {title[:80]}",Url=URL,
                Notes=f"Точки таблицы каталога (Q, м³/ч — H, м). "+(f"Мощность {hpv:g} HP / P2 {kw:g} кВт." if kw else f"P1 {p1*1000:g} Вт (P2 в каталоге не указана).")+" Двигатель 2-полюсный 50 Гц (по каталогу — 2900 об/мин для погружных серий)."))
seen=set();out=[]
for r in recs:
    if r['Id'] in seen: continue
    seen.add(r['Id']); out.append(r)
save('out/speroni.json',out); json.dump(log,open('out/speroni_excluded.json','w'),ensure_ascii=False,indent=1)
print(log[:10])
