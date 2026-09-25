# Herborner UNIPUMP (Германия): блочные канализационные насосы сухой установки.
# Векторные кривые Q–H, P, η, NPSH (50 Гц) из проспекта UNIPUMP EN, ред. 12 (09.2026).
import pymupdf as fitz, re, json, math
from common import rec, save
PDF='p3/P_UNIPUMP_EN_12.pdf'
URL='https://www.herborner-pumpen.com/download/prospekt/P_UNIPUMP_EN_12.pdf'
d=fitz.open(PDF)
def num(s):
    try: return float(s.replace(',','.'))
    except: return None
# P2 по таблице двигателей IE3 50 Гц (стр. 28): блоки 1 (1500) и 3 (3000)
t=d[27].get_text().split('\n'); blocks=[];cur=None
for i,s in enumerate(t):
    if s=='Model': cur=[];blocks.append(cur)
    elif cur is not None and s.startswith('/'):
        cur.append((t[i-1]+s,num(t[i+1]),num(t[i+2])))
P2={}
for b in (blocks[0],blocks[2]):
    for m,p2,a in b: P2[m]=(p2,a)
def lines(pg):
    out=[]
    for b in pg.get_text('dict')['blocks']:
        for l in b.get('lines',[]):
            s=''.join(sp['text'] for sp in l['spans']).replace('\xa0',' ').strip()
            if s: out.append((s,fitz.Rect(l['bbox']),l['dir']))
    return out
def chains(segs,tol=0.35):
    # склейка отрезков в полилинии
    segs=[s for s in segs if (s[0]-s[1]).__abs__()>1e-3]
    polys=[]
    for a,b in segs:
        if polys and (polys[-1][-1]-a).__abs__()<0.05: polys[-1].append(b)
        else: polys.append([a,b])
    merged=True
    while merged:
        merged=False
        for i in range(len(polys)):
            for j in range(len(polys)):
                if i!=j and (polys[i][-1]-polys[j][0]).__abs__()<tol:
                    polys[i]+=polys[j][1:]; polys.pop(j); merged=True; break
            if merged: break
    return [p for p in polys if len(p)>3]
def fit(pairs):
    n=len(pairs); sx=sum(a for a,_ in pairs); sy=sum(b for _,b in pairs)
    sxx=sum(a*a for a,_ in pairs); sxy=sum(a*b for a,b in pairs)
    k=(n*sxy-sx*sy)/(n*sxx-sx*sx); c=(sy-k*sx)/n
    res=max(abs(k*a+c-b) for a,b in pairs)
    tol=0.01*max(abs(b) for _,b in pairs)+1e-6
    if res>tol and n>4:
        worst=max(pairs,key=lambda p:abs(k*p[0]+c-p[1]))
        return fit([p for p in pairs if p is not worst])
    return k,c,res
def dist_pl(pt,poly):
    best=1e9
    for a,b in zip(poly,poly[1:]):
        ab=b-a; L=ab.x**2+ab.y**2
        u=0 if L==0 else max(0,min(1,((pt.x-a.x)*ab.x+(pt.y-a.y)*ab.y)/L))
        q=a+ab*u; best=min(best,(pt-q).__abs__())
    return best
recs=[];log=[];dbg=[];OV=[]
for pi in range(11,19):
    pg=d[pi]; W=pg.rect.width; L=lines(pg); words=pg.get_text('words')
    heads=[(s,r) for s,r,_ in L if re.match(r'(1500|3000) rpm \(400 V - 50 Hz\)',s)]
    series_titles=[(s,r) for s,r,_ in L if re.fullmatch(r'(HK|K|QSH)\s?\d+',s)]
    for hs,hr in heads:
        rpm=int(hs[:4]); y0=hr.y1
        ys=sorted(r.y0 for s,r in heads if r.y0>hr.y0+5)+[pg.rect.height]; y1=ys[0]
        inq=lambda r: r.x1<W/2 and y0<r.y0<y1
        lab={s:r for s,r,_ in L if s in('H','P','Eta','NPSH') and inq(r) and r.x0<60}
        if len(lab)<4: log.append((f'стр.{pi+1}',f'{hs}: нет подписей панелей')); continue
        order=sorted(lab,key=lambda k:lab[k].y0)
        # ось Q (м³/ч) — строка с «Q [m»
        qlab=[r for s,r,_ in L if s.startswith('Q [m') and inq(r)][0]
        qt=[((w[0]+w[2])/2,num(w[4])) for w in words if abs((w[1]+w[3])/2-(qlab.y0+qlab.y1)/2)<3 and w[2]<qlab.x0 and num(w[4]) is not None]
        kq,cq,rq=fit(qt); assert rq<0.02*max(v for _,v in qt),(pi,hs,'Q axis')
        # панели и их шкалы
        panels={}
        for i,k in enumerate(order):
            top=lab[k].y0-8; bot=(lab[order[i+1]].y0-8) if i+1<len(order) else min(y1,lab[k].y0+55)
            tk=[((w[1]+w[3])/2,num(w[4])) for w in words if 40<w[0] and w[2]<67 and top<(w[1]+w[3])/2<bot and num(w[4]) is not None]
            ky,cy,ry=fit(tk); assert ry<0.02*max(v for _,v in tk)+1e-6,(pi,hs,k,tk)
            panels[k]=(top,bot,ky,cy)
        segs=[];ticks=[]
        for dr in pg.get_drawings():
            if not dr.get('width') or dr['width']<0.2 or dr.get('color') in (None,(1.0,1.0,1.0)): continue
            r=dr['rect']
            if len(dr['items'])<=2 and r.width<15 and r.height<15:
                if r.x1<W/2 and y0<r.y0<y1: ticks.append(fitz.Point((r.x0+r.x1)/2,(r.y0+r.y1)/2))
                continue
            if r.x1>W/2 or not (y0<r.y0<y1): continue
            for it in dr['items']:
                if it[0]=='l': segs.append((it[1],it[2]))
                elif it[0]=='c':
                    P=[it[1],it[2],it[3],it[4]]; prev=P[0]
                    for s in range(1,9):
                        u=s/8; q=P[0]*(1-u)**3+P[1]*3*u*(1-u)**2+P[2]*3*u*u*(1-u)+P[3]*u**3; segs.append((prev,q)); prev=q
        polys=chains(segs)
        byp={k:[] for k in panels}
        for p in polys:
            ym=sum(v.y for v in p)/len(p)
            for k,(top,bot,ky,cy) in panels.items():
                if top<ym<bot: byp[k].append(p)
        # подписи моделей на панели H и «ø D» на остальных
        mlabels=[(s,r) for s,r,_ in L if inq(r) and re.match(r'[\d,.]+/(HK|K|QSH)\s?\d+-\d-\d+',s)]
        if not mlabels: log.append((f'стр.{pi+1}',f'{hs}: нет подписей моделей')); continue
        top,bot,ky,cy=panels['H']
        hp=byp['H']
        dia=lambda m:int(re.search(r'-\d-(\d+)',m).group(1))
        Ds=sorted({dia(m) for m,_ in mlabels},reverse=True)
        if len(hp)!=len(Ds): log.append((f'стр.{pi+1}',f'{hs}: кривых H {len(hp)} ≠ диаметров {len(Ds)}')); continue
        xm=max(min(v.x for v in p) for p in hp)+3
        def yat(poly,x):
            return min(poly,key=lambda v:abs(v.x-x)).y
        cs=sorted(hp,key=lambda p:yat(p,xm))
        curveD=dict(zip(Ds,cs))
        assign={}
        for m,r in mlabels:
            c=fitz.Point((r.x0+r.x1)/2,(r.y0+r.y1)/2); pp=curveD[dia(m)]
            dd=dist_pl(c,pp)
            if dd>12 and min(dist_pl(c,q) for q in hp)<dd-3: log.append((m,f'стр.{pi+1}: подпись ближе к другой кривой — проверить'))
            assign[m]=pp
        # остальные панели: по подписи «ø D» у конца кривой
        other={};amb=[]
        for k in ('P','Eta','NPSH'):
            top_,bot_,_,_=panels[k]
            dl=[(int(re.search(r'\d+',s).group()),r) for s,r,_ in L if inq(r) and s.startswith('ø') and top_<(r.y0+r.y1)/2<bot_]
            cand=byp[k]; mp={}
            ex=lambda p:(min(v.x for v in p),max(v.x for v in p))
            lblpt={D:fitz.Point((r.x0+r.x1)/2,(r.y0+r.y1)/2) for D,r in dl}
            used=set()
            for D,hc in sorted(curveD.items()):
                hx=ex(hc)
                cc=[i for i,p in enumerate(cand) if i not in used and abs(ex(p)[1]-hx[1])<2.5 and abs(ex(p)[0]-hx[0])<4]
                if len(cc)>1 and D in lblpt:
                    cc=sorted(cc,key=lambda i:min((v-lblpt[D]).__abs__() for v in (cand[i][0],cand[i][-1])))[:1]
                    amb.append((D,k))
                if len(cc)==1: mp[D]=cand[cc[0]]; used.add(cc[0])
            other[k]=mp
        tr=lambda poly,pk:[((v.x-cq)/1 if False else kq*v.x+cq, panels[pk][2]*v.y+panels[pk][3]) for v in poly]
        def clean(pts):
            pts=sorted(pts); out=[]
            for q,v in pts:
                if q<-0.01: continue
                if out and q-out[-1][0]<1e-3: continue
                out.append((max(q,0),v))
            return out
        def thin(pts,n=16):
            if len(pts)<=n: return pts
            q0,q1=pts[0][0],pts[-1][0]; res=[]
            for i in range(n):
                qq=q0+(q1-q0)*i/(n-1); j=min(range(len(pts)),key=lambda j:abs(pts[j][0]-qq)); res.append(pts[j])
            return sorted(set(res))
        for lbl,p in assign.items():
          for m in re.findall(r'[\d,.]+/(?:HK|K|QSH)\s?\d+-\d-\d+',lbl):
            m=m.replace(' ','')
            full=clean(tr(p,'H')); qcut=None
            twins=[l for l in assign if l!=lbl and '(' not in l and '(' not in lbl and dia(l)==dia(lbl)]
            if twins:
                hpw=lambda x:float(x.split('/')[0].replace(',','.'))
                tk=[t_ for t_ in ticks if dist_pl(t_,p)<5]
                if len(tk)!=1: log.append((m,f'стр.{pi+1}: общая кривая без отметки границы двигателя')); continue
                if hpw(lbl)<max(hpw(l) for l in twins): qcut=kq*tk[0].x+cq
            if qcut is not None:
                hcut=next(h0+(h1-h0)*(qcut-q0)/(q1-q0) for (q0,h0),(q1,h1) in zip(full,full[1:]) if q0<=qcut<=q1)
                full=[x for x in full if x[0]<qcut]+[(qcut,hcut)]
            qh=thin(full)
            if any(b>a+0.05 for (_,a),(_,b) in zip(qh,qh[1:])): log.append((m,f'стр.{pi+1}: напор растёт')); continue
            D=dia(m); extra={}; nb=m.split('-')[1]
            for k,key in (('P','QP'),('Eta','QEta'),('NPSH','QNpsh')):
                if D in other[k]: extra[key]=thin([x for x in clean(tr(other[k][D],k)) if qcut is None or x[0]<=qcut+1e-6])
            ser=re.search(r'/(HK|K|QSH)\s?(\d+)',m); code=m.split('-')[0].replace(',','.')
            p2,amp=P2.get(code,(0,0))
            if not p2: log.append((m,'нет P2 в таблице двигателей'))
            dn={'25':25,'50':50,'80':80,'101':100}[ser.group(2)]
            model=m.replace('/',' / ').replace('  ',' ')
            model=re.sub(r'(HK|K|QSH)(\d+)',r'\1 \2',m)
            recs.append(rec('Herborner','UNIPUMP '+ser.group(1),model,'Германия',Application='канализационный блочный (сухая установка)',
                Impeller='Open',DnOut=dn,P2Kw=p2,Rpm=rpm,Poles=4 if rpm==1500 else 2,
                Voltage='3~400 В 50 Гц',ImpellerDmm=D,QH=qh,**extra,
                Document=f'Herborner, проспект UNIPUMP (EN, ред. 12, 09.2026), стр. {pi+1}',Url=URL,
                Notes=f'Векторные кривые каталога (Q, м³/ч). Частота вращения {rpm} мин⁻¹ — синхронная, по каталогу. P — мощность на валу по графику каталога. Рабочее колесо открытое {nb}-лопастное с системой резки волокон (non-clogging), Ø{D} мм. P2 двигателя {p2:g} кВт (IE3, стр. 28).'+(f' Кривая общая с более мощным двигателем, обрезана по отметке предела двигателя (Q={qcut:.1f} м³/ч).' if qcut else '')))
            dbg.append((pi,m,qh[0],qh[-1],len(extra)))
            OV.append(dict(pi=pi,m=m,kq=kq,cq=cq,P={k:(v[2],v[3]) for k,v in panels.items()},QH=qh,**{k:extra.get(k,[]) for k in ('QP','QEta','QNpsh')}))
seen=set();out=[]
for r in recs:
    if r['Id'] in seen: log.append((r['Model'],'дубликат')); continue
    seen.add(r['Id']); out.append(r)
save('out/herborner.json',out); json.dump(log,open('out/herborner_excluded.json','w'),ensure_ascii=False,indent=1)
print(log)
for x in dbg: print(x)

json.dump(OV,open('out/herb_overlay.json','w'))
