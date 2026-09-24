import pymupdf,re,itertools,numpy as np,sys,json
from vdig import *
from fancy import grp
from common import *
MRE=re.compile(r'^\d*WQ[0-9A-Z/.\-]*\d$')
PAIR=re.compile(r'(\d+(?:[.,]\d+)?)\s*[—–-]\s*(\d+(?:[.,]\d+)?)')
def is_grid(g):
    if g['type']=='f':
        c=g.get('fill') or (1,1,1); return max(c)<0.3
    c=g.get('color') or (1,1,1)
    return max(c)<0.3 and (g.get('width') or 0)<=0.6
def is_curve(g):
    c=g.get('color') or (0,0,0)
    r=g['rect']
    return g['type'] in('s','fs') and c[2]>0.6 and c[0]<0.35 and not (r.width<3.5 and r.height>2)
def cell_num(s):
    if s is None: return None
    s=s.replace('\n',' ').strip()
    m=re.findall(r'\d+(?:[.,]\d+)?',s.replace(' ','') if re.fullmatch(r'\d \d{3}',s) else s)
    return num(m[-1]) if m else None
def parse_half(p, hx0, hx1, dbg=False):
    W=[w for w in p.get_text('words') if hx0<=w[0]<hx1 and 60<w[1]<460]
    rows=grp(W)
    models=[]
    for y,r in rows:
        if y<150: continue
        for w in r:
            if MRE.match(w[4]) and w[4] not in [m[0] for m in models] and not re.search(r'EC2\d\d-',w[4]) :
                models.append((w[4],w[0],y)); break
    # отбрасываем «первоначальную модель» (второй столбец) — она правее первой
    if not models: return None
    x_first=min(m[1] for m in models)
    models=[m for m in models if m[1]<x_first+40 and m[2]>150]
    if not models: return None
    txt=' '.join(w[4] for w in W)
    m=re.search(r'патрубка:?\s*(\d+)\s*мм',txt); dn=int(m.group(1)) if m else 0
    # пары Q—H по строкам
    pairs=[]
    for y,r in rows:
        s=' '.join(w[4] for w in r if w[0]>x_first-30)
        ps=[(num(a),num(b)) for a,b in PAIR.findall(s)]
        ps=[q for q in ps if q[0] is not None and q[1] is not None and not (q[0]>1000)]
        if len(ps)>=2 and not re.search(r'[A-Za-z]',s.replace('WQ','')): pairs.append(ps)
    # характеристики из таблиц
    spec=[{} for _ in models]
    tabs=[t for t in p.find_tables(clip=pymupdf.Rect(hx0,100,hx1,460)).tables]
    for t in tabs:
        X=t.extract(); cols={}; k=0
        for row in X:
            hdr=' '.join((c or '').replace('\n',' ') for c in row)
            if re.search(r'Мощность|Масса|ток|КПД|вращ',hdr) and not re.search(r'\d{2,}\s*$',hdr.split('Масса')[0][-3:] if 'Масса' in hdr else ''):
                if re.search(r'[А-Яа-я]{4}',hdr):
                    cols={}
                    for j,c in enumerate(row):
                        c=(c or '').replace('\n',' ')
                        if re.search(r'(?i)^(номинальная\s+)?мощность',c.strip()): cols['p2']=j
                        elif re.search(r'Масса',c): cols['mass']=j
                        elif re.search(r'вращ',c): cols['rpm']=j
                        elif re.search(r'проход|проточного',c): cols['fp']=j
                        elif re.search(r'ток',c): cols['cur']=j
                        elif re.search(r'КПД',c): cols['eff']=j
                    k=0; continue
            if cols and any(cell_num(row[j]) is not None for j in cols.values() if j<len(row)):
                if k<len(spec):
                    for key,j in cols.items():
                        if j<len(row) and key not in spec[k]:
                            c=row[j]
                            if key=='fp' and c and 'Овал' in c:
                                v=[num(z) for z in re.findall(r'\d+(?:[.,]\d+)?',c)]; spec[k]['fp']=min(v) if v else None; spec[k]['fpraw']=c
                            else:
                                v=cell_num(c)
                                if v is not None: spec[k][key]=v
                k+=1
    # график
    nos=[w[0] for w in W if w[4] in('№','No','N°') and w[1]>120]
    tx0=(min(nos)-3) if nos and min(nos)<x_first else x_first-8
    ys=[w[1] for w in p.get_text('words') if hx0<=w[0]<hx1 and w[4] in('Установочные','Монтажные','Габаритные','Размеры','Установочный') and w[1]>200]
    clip=pymupdf.Rect(hx0+10,110,tx0,(min(ys)-4) if ys else 445)
    gb=grid_bbox(p,clip,is_grid)
    if gb is None or gb.width<60: return dict(models=models,dn=dn,pairs=pairs,spec=spec,err='nogrid')
    tclip=pymupdf.Rect(gb.x0-40,gb.y0-25,min(gb.x1+45,tx0),gb.y1+18)
    def classify(toks):
        L=[];B=[];R=[];lab=[]
        for t in toks:
            xc=(t[0]+t[2])/2; yc=(t[1]+t[3])/2; s=t[4].replace(',','.')
            if not NUM.match(s):
                sr=split_run(t)
                if sr and yc>gb.y1: B+= [(x,v) for x,_,v in sr]
                continue
            v=float(s)
            if xc<gb.x0-1 and gb.y0-3<yc<gb.y1+3: L.append((yc,v))
            elif yc>gb.y1+1 and gb.x0-8<xc<gb.x1+8: B.append((xc,v))
            elif xc>gb.x1+1 and gb.y0-3<yc<gb.y1+3: R.append((yc,v))
            elif gb.x0<xc<gb.x1 and gb.y0<yc<gb.y1 and s.isdigit() and 1<=v<=9: lab.append((xc,yc,int(v)))
        return L,B,R,lab
    toks=[t for t in text_tokens(p,tclip) if NUM.match(t[4])]
    L,B,R,lab=classify(toks)
    if len(L)<2 or len(B)<2:
        toks=ocr_tokens(p,tclip); L,B,R,lab=classify(toks)
    fx=fit_axis(B); fy=fit_axis(L); fr=fit_axis(R) if len(R)>=2 else None
    if not fx or not fy: return dict(models=models,dn=dn,pairs=pairs,spec=spec,err='axis',L=L,B=B,gb=gb,toks=[(round(t[0]),round(t[1]),t[4]) for t in toks])
    polys=polylines(p,pymupdf.Rect(gb.x0-2,gb.y0-2,gb.x1+2,gb.y1+2),is_curve)
    ch=[c for c in merge_chains(chain(polys)) if c[-1][0]-c[0][0]>0.25*gb.width]
    qh=[];pw=[]
    def rdist(y,P):
        if not P: return 1e9
        lo=min(q[0] for q in P); hi=max(q[0] for q in P)
        return 0 if lo<=y<=hi else min(abs(y-lo),abs(y-hi))
    for c in ch:
        a=np.array(c); k=np.polyfit(a[:,0],a[:,1],1)[0]; ym=a[:,1].mean()
        dl=rdist(ym,L); dr=rdist(ym,R)
        if dl<dr-3: qh.append(c)
        elif dr<dl-3: pw.append(c)
        else: (qh if k>0 else pw).append(c)
    return dict(models=models,dn=dn,pairs=pairs,spec=spec,fx=fx,fy=fy,fr=fr,qh=qh,pw=pw,lab=lab,gb=gb)
def to_qh(c,fx,fy):
    return [(fx[0]*x+fx[1], fy[0]*y+fy[1]) for x,y in c]
if __name__=='__main__':
    f=sys.argv[1]; d=pymupdf.open(f)
    for pn in map(int,sys.argv[2:]):
        p=d[pn-1]; Wd=p.rect.width
        for hx0,hx1 in [(0,Wd/2),(Wd/2,Wd)]:
            R=parse_half(p,hx0,hx1)
            if not R: continue
            print('--',pn,R.get('L'),R.get('B'),[m[0] for m in R['models']],'dn',R['dn'],'pairs',R['pairs'],'spec',R['spec'],R.get('err'))
            if 'fx' in R:
                print('   fx',R['fx'],'fy',R['fy'],'fr',R['fr'],'nqh',len(R['qh']),'npw',len(R['pw']),'lab',R['lab'])
                for c in R['qh']:
                    q=to_qh(c,R['fx'],R['fy']); print('   QH',[ (round(a,1),round(b,1)) for a,b in q[::max(1,len(q)//6)]])
