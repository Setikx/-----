# KESSEL (Германия): насосы для систем водоотведения — векторные диаграммы Q–H
# из «Programmübersicht 2023» (стр. 94–95 «Leistungsdiagramme», стр. 66 SPZ; постраничные PDF kessel.at).
import pymupdf as fitz, re, json, itertools
from common import rec, save
P='p3/kessel/'
BASE='https://www.kessel.at/fileadmin/assets/katalog/PUE23/'
def num(s):
    try: return float(s.replace(',','.'))
    except: return None
def fit(pairs):
    n=len(pairs); sx=sum(a for a,_ in pairs); sy=sum(b for _,b in pairs)
    sxx=sum(a*a for a,_ in pairs); sxy=sum(a*b for a,b in pairs)
    k=(n*sxy-sx*sy)/(n*sxx-sx*sx); c=(sy-k*sx)/n
    res=max(abs(k*a+c-b) for a,b in pairs)
    if res>0.01*max(abs(b) for _,b in pairs)+1e-6 and n>3:
        worst=max(pairs,key=lambda p:abs(k*p[0]+c-p[1])); return fit([p for p in pairs if p is not worst])
    return k,c,res
def dist_pl(pt,poly):
    best=1e9
    for a,b in zip(poly,poly[1:]):
        ab=b-a; L=ab.x**2+ab.y**2
        u=0 if L==0 else max(0,min(1,((pt.x-a.x)*ab.x+(pt.y-a.y)*ab.y)/L))
        best=min(best,abs(pt-(a+ab*u)))
    return best
def subpaths(dr):
    out=[];cur=[]
    for it in dr['items']:
        if it[0]=='l': pts=[it[1],it[2]]
        elif it[0]=='c':
            A,B,C,D=it[1:5]; pts=[A*(1-u)**3+B*3*u*(1-u)**2+C*3*u*u*(1-u)+D*u**3 for u in [i/8 for i in range(9)]]
        else: continue
        if cur and abs(cur[-1]-pts[0])<0.05: cur+=pts[1:]
        else:
            if cur: out.append(cur)
            cur=list(pts)
    if cur: out.append(cur)
    return out
def join(polys,tol=0.6):
    polys=[list(p) for p in polys]; merged=True
    while merged:
        merged=False
        for i,j in itertools.permutations(range(len(polys)),2):
            if abs(polys[i][-1]-polys[j][0])<tol: polys[i]+=polys[j][1:]; polys.pop(j); merged=True; break
    return polys
PAGES=['094','095','066']
recs=[];log=[];dbg=[];OV=[]
for pg_no in PAGES:
    pg=fitz.open(f'{P}PUE23_{pg_no}.pdf')[0]
    words=pg.get_text('words'); drs=pg.get_drawings()
    bgs=[dr['rect'] for dr in drs if dr['type']=='f' and dr.get('fill') and abs(dr['fill'][0]-0.93)<0.02 and dr['rect'].width>150 and dr['rect'].height>80]
    if pg_no=='066':  # Ecolift: одна кривая насоса SPZ 1000 без подписи на поле графика
        bgs=[dr['rect'] for dr in drs if dr['type']=='f' and dr.get('fill')==(1.0,1.0,1.0) and dr['rect'].width>100 and dr['rect'].height>50]
    for bg in bgs:
        # подписи моделей: текст вида «GTF 1000»
        L=[]
        for b in pg.get_text('dict')['blocks']:
            for l in b.get('lines',[]):
                s=''.join(sp['text'] for sp in l['spans']).strip(); r=fitz.Rect(l['bbox'])
                if re.fullmatch(r'(KTP|GTF|GTK|SPF|SPZ|STZ)\s?\d+',s) and bg.contains(r): L.append((s.replace(' ',' '),r))
        if pg_no=='066': L=[('SPZ 1000',fitz.Rect(bg.x0,bg.y0,bg.x0+1,bg.y0+1))]
        if not L: continue
        # шкалы
        ht=[((w[1]+w[3])/2,num(w[4])) for w in words if w[2]<bg.x0+2 and w[0]>bg.x0-22 and bg.y0-3<(w[1]+w[3])/2<bg.y1+3 and num(w[4]) is not None]
        qlab=[w for w in words if w[4] in('Q','Q[m3/h]') and bg.y1<w[1]<bg.y1+30 and bg.x0<w[0]<bg.x1+30]
        qlab=min(qlab,key=lambda w:w[1])
        qt=[((w[0]+w[2])/2,num(w[4])) for w in words if abs((w[1]+w[3])/2-(qlab[1]+qlab[3])/2)<2.5 and w[2]<qlab[0] and w[0]>bg.x0-10 and num(w[4]) is not None]
        kh,ch,rh=fit(ht); kq,cq,rq=fit(qt)
        # кривые: чёрные линии ≥1 pt внутри поля графика
        polys=[]
        for dr in drs:
            if dr['type']!='s' or not dr.get('color') or max(dr['color'])>0.1 or (dr.get('width') or 0)<0.9: continue
            if not bg.intersects(dr['rect']): continue
            for sp in subpaths(dr):
                if max(v.x for v in sp)-min(v.x for v in sp)>1: polys.append(sp)
        polys=[p for p in join(polys) if max(v.x for v in p)-min(v.x for v in p)>15]
        polys=[p if p[0].x<p[-1].x else p[::-1] for p in polys]
        if len(polys)<len(L):
            # часть кривых нарисована контуром из мелких заливок — собираем их центры в треки
            C=sorted(((d['rect'].x0+d['rect'].x1)/2,(d['rect'].y0+d['rect'].y1)/2) for d in drs
                     if d['type']=='f' and d.get('fill') and max(d['fill'])<0.1 and d['rect'].width<4 and d['rect'].height<4 and bg.contains(d['rect']))
            C=[fitz.Point(x,y) for x,y in C if all(dist_pl(fitz.Point(x,y),p)>1.5 for p in polys)]
            tracks=[]
            for c in C:
                cand=[t for t in tracks if 0<=c.x-t[-1].x<3.5 and abs(c.y-t[-1].y)<2.5]
                if cand: min(cand,key=lambda t:abs(c-t[-1])).append(c)
                elif not any(abs(c-t[-1])<0.6 for t in tracks): tracks.append([c])
            tracks=[t for t in tracks if t[-1].x-t[0].x>15]
            polys+=tracks
        if len(polys)!=len(L):
            log.append((' / '.join(s for s,_ in L),f'PÜ 2023 стр.{int(pg_no)}: кривых {len(polys)} ≠ подписей {len(L)}')); continue
        best=None
        for perm in itertools.permutations(range(len(polys))):
            cost=sum(dist_pl(fitz.Point((r.x0+r.x1)/2,(r.y0+r.y1)/2),polys[i]) for (s,r),i in zip(L,perm))
            if best is None or cost<best[0]: best=(cost,perm)
        for (s,r),i in zip(L,best[1]):
            p=polys[i]; d0=dist_pl(fitz.Point((r.x0+r.x1)/2,(r.y0+r.y1)/2),p)
            others=[dist_pl(fitz.Point((r.x0+r.x1)/2,(r.y0+r.y1)/2),q) for j,q in enumerate(polys) if j!=i]
            amb=others and min(others)<d0+2
            pts=sorted((kq*v.x+cq,kh*v.y+ch) for v in p)
            out=[]
            for q,h in pts:
                if out and q-out[-1][0]<0.02*(pts[-1][0]-pts[0][0]+1e-9)/1: continue
                out.append((max(q,0),h))
            # прореживание до ~16 точек
            if len(out)>16:
                idx=sorted({round(i*(len(out)-1)/15) for i in range(16)}); out=[out[i] for i in idx]
            dbg.append((pg_no,s,round(d0,1),amb,out[0],out[-1]))
            recs.append((s,out,int(pg_no),amb)); OV.append(dict(pg=pg_no,m=s,kq=kq,cq=cq,kh=kh,ch=ch,QH=out))

# двигатели — по таблицам PÜ 2023 (P1, P2 кВт; напряжение; ток; об/мин; стр.)
MOT={'KTP 300':(0.34,0.21,'1~230 В',1.6,2800,159),'GTF 500':(0.60,0.36,'1~230 В',2.7,2800,159),'GTF 600':(0.65,0.40,'1~230 В',2.9,2750,117),
 'GTF 1000':(1.27,0.73,'1~230 В',5.6,2800,160),'GTF 1200':(1.4,0.84,'1~230 В',6.2,2650,110),'GTF 1250':(1.3,0.8,'1~230 В',5.4,2700,117),
 'GTF 1400':(1.5,1.1,'1~230 В',6.5,0,145),'GTF 1600':(1.6,1.2,'3~400 В',2.9,0,145),'GTF 2600':(2.6,2.1,'3~400 В',4.5,0,145),
 'GTF 4000':(4.0,3.4,'3~400 В',6.6,0,145),'GTF 5200':(5.2,4.4,'3~400 В',8.7,0,147),
 'GTK 1300':(1.3,1.0,'3~400 В',2.5,0,145),'GTK 2600':(2.6,2.1,'3~400 В',4.9,0,145),'GTK 3700':(3.7,3.1,'3~400 В',6.5,0,145),'GTK 5200':(5.2,4.4,'3~400 В',8.7,0,147),
 'SPF 1400':(1.6,1.1,'1~230 В',7.3,0,126),'SPF 1500':(1.4,1.1,'3~400 В',2.7,0,126),'SPF 3000':(3.2,2.7,'3~400 В',5.4,0,126),'SPF 4500':(4.5,3.7,'3~400 В',7.5,0,126),
 'SPZ 1000':(1.2,0.69,'1~230 В',5.2,2800,108),
 'STZ 1300':(1.3,0.9,'3~400 В',2.5,0,143),'STZ 2500':(2.5,1.9,'3~400 В',4.4,0,143),'STZ 3700':(3.7,3.1,'3~400 В',6.4,0,143),
 'STZ 4400':(4.4,3.7,'3~400 В',7.5,0,146),'STZ 5200':(5.2,4.4,'3~400 В',8.7,0,146),'STZ 7500':(7.5,6.4,'3~400 В',13,0,146),'STZ 11000':(11,9.5,'3~400 В',18.8,0,146)}
KIND={'KTP':('Unknown','дренажный погружной (чистая/слабозагрязнённая вода)',False,'KESSEL Tauchpumpe'),
 'GTF':('Vortex','дренажный погружной (серые стоки)',False,'погружной насос для серых стоков со свободновихревым колесом'),
 'GTK':('Unknown','канализационный погружной (серые стоки)',False,'погружной насос для серых стоков с канальным колесом'),
 'SPF':('Vortex','канализационный погружной (чёрные стоки)',False,'насос для чёрных стоков со свободновихревым колесом'),
 'SPZ':('Grinder','канализационный с измельчителем',True,'насос для чёрных стоков с режущим колесом'),
 'STZ':('Grinder','канализационный погружной с измельчителем',True,'погружной насос для чёрных стоков с измельчителем')}
out=[]
for s_,pts,pno,amb in recs:
    ser=s_.split()[0]; imp,app,cut,desc=KIND[ser]; p1,p2,v,a,rpm,mp=MOT[s_]
    notes=f"Оцифровка векторной кривой каталога (Q, м³/ч — H, м), PÜ 2023 стр. {pno}. {desc[0].upper()+desc[1:]}. P1 {p1:g} кВт / P2 {p2:g} кВт, {a:g} А (стр. {mp})."
    notes+=f" Частота вращения {rpm} мин⁻¹ по каталогу." if rpm else " Частота вращения в каталоге не указана."
    if s_=='SPZ 1000': notes+=" Кривая из раздела «Rückstauhebeanlage Ecolift» (единственный насос установки)."
    out.append(rec('KESSEL',ser,s_,'Германия',Application=app,Impeller=imp,HasCutter=cut,P1Kw=p1,P2Kw=p2,Voltage=v+' 50 Гц',Rpm=rpm,Poles=2 if rpm else 0,QH=pts,
        Document=f'KESSEL AG, Programmübersicht 2023 (PÜ 2023), стр. {pno}',Url=f'{BASE}PUE23_{pno:03d}.pdf',Notes=notes))
save('out/kessel.json',out)
excl=log+[('KESSEL — вся программа','PÜ 2026 опубликована только в онлайн-просмотрщике Oxomi (без PDF); использована PÜ 2023 — последняя скачиваемая')]
json.dump(excl,open('out/kessel_excluded.json','w'),ensure_ascii=False,indent=1)
print(log)
for r in out: print(r['Model'],r['Curve']['QH'][0],r['Curve']['QH'][-1])

json.dump(OV,open('out/kessel_overlay.json','w'))
