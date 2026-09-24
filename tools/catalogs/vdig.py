"""Оцифровка векторных графиков Q–H/P из PDF: оси калибруются по подписям делений (текст PDF или OCR),
кривые берутся из векторных путей цветных линий."""
import pymupdf, numpy as np, re, math
_ocr=None
def ocr_tokens(page, clip, zoom=4):
    global _ocr
    if _ocr is None:
        from rapidocr_onnxruntime import RapidOCR
        _ocr=RapidOCR()
    pix=page.get_pixmap(matrix=pymupdf.Matrix(zoom,zoom),clip=clip)
    img=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.h,pix.w,pix.n)[:,:,:3].copy()
    res,_=_ocr(img)
    out=[]
    for box,txt,conf in (res or []):
        xs=[b[0] for b in box]; ys=[b[1] for b in box]
        out.append((clip.x0+min(xs)/zoom, clip.y0+min(ys)/zoom, clip.x0+max(xs)/zoom, clip.y0+max(ys)/zoom, txt.strip(), conf))
    return out
def text_tokens(page, clip):
    return [(w[0],w[1],w[2],w[3],w[4],1.0) for w in page.get_text('words',clip=clip)]
NUM=re.compile(r'^-?\d+(?:[.,]\d+)?$')
def split_run(tok, step_hint=None):
    """'100150200250' / '100 150 200' / '10203040Q(м3/ч)' -> [(x,y,v),...]"""
    full=tok[4]
    m=re.match(r'[\d\s.,]+',full)
    if not m: return None
    s=m.group(0).rstrip()
    x0=tok[0]; x1=tok[0]+(tok[2]-tok[0])*len(s)/max(1,len(full)); yc=(tok[1]+tok[3])/2
    n=len(s)
    def pos(i,l): return x0+(x1-x0)*(i+l/2)/n
    parts=s.split()
    if len(parts)>1 and all(re.fullmatch(r'\d+(?:[.,]\d+)?',z) for z in parts) and all(len(z)<=4 for z in parts):
        out=[];p=0
        for z in parts:
            i=s.index(z,p); p=i+len(z); out.append((pos(i,len(z)),yc,float(z.replace(',','.'))))
        return out
    t=s.replace(' ','')
    if not t.isdigit() or len(t)<3: return None
    best=None
    for l1 in range(1,min(5,len(t))):
        for l2 in range(1,min(6,len(t)-l1+1)):
            a=int(t[:l1]); b=int(t[l1:l1+l2]); st=b-a
            if st<=0: continue
            seq=[a]; cur=a; o=str(a)
            while len(o)<len(t):
                cur+=st; o+=str(cur); seq.append(cur)
            if o==t and len(seq)>=3 and (best is None or len(seq)>len(best)): best=seq
    if not best: return None
    out=[];p=0
    for v in best:
        z=str(v); i=s.find(z,p)
        if i<0: i=p
        p=i+len(z); out.append((pos(i,len(z)),yc,float(v)))
    return out
def fit_axis(pairs, min_n=2):
    """pairs: (pos, value). Робастная линейная подгонка; отбрасывает выбросы."""
    P=list(pairs)
    while len(P)>=min_n:
        a=np.array(P); A=np.vstack([a[:,0],np.ones(len(a))]).T
        k,b=np.linalg.lstsq(A,a[:,1],rcond=None)[0]
        res=np.abs(a[:,0]*k+b-a[:,1]); rng=max(1e-9,a[:,1].max()-a[:,1].min())
        if res.max()<=0.02*rng or len(P)==min_n: return k,b,len(P),res.max()/rng
        P.pop(int(res.argmax()))
    return None
def grid_bbox(page, clip, is_grid):
    """Рамка сетки графика: по наиболее частой длине горизонтальных и вертикальных линий."""
    from collections import Counter
    H=[];V=[]
    for g in page.get_drawings():
        r=g['rect']
        if not clip.contains(r) or not is_grid(g): continue
        if g['type']=='f':
            if r.width<0.7 and r.height>5: its=[('l',pymupdf.Point(r.x0,r.y0),pymupdf.Point(r.x0,r.y1))]
            elif r.height<0.7 and r.width>5: its=[('l',pymupdf.Point(r.x0,r.y0),pymupdf.Point(r.x1,r.y0))]
            else: continue
        elif g['type']=='s': its=g['items']
        else: continue
        for it in its:
            if it[0]!='l': continue
            a,b=it[1],it[2]
            if abs(a.y-b.y)<0.3 and abs(a.x-b.x)>5: H.append((round(min(a.x,b.x)),round(max(a.x,b.x)),a.y))
            elif abs(a.x-b.x)<0.3 and abs(a.y-b.y)>5: V.append((round(min(a.y,b.y)),round(max(a.y,b.y)),a.x))
    if len(H)>=3 and len(V)>=3:
        hx=Counter((h[0],h[1]) for h in H).most_common(1)[0][0]
        vy=Counter((v[0],v[1]) for v in V).most_common(1)[0][0]
        hs=[h for h in H if abs(h[0]-hx[0])<=2 and abs(h[1]-hx[1])<=2]
        vs=[v for v in V if abs(v[0]-vy[0])<=2 and abs(v[1]-vy[1])<=2]
        vs2=[v for v in V if hx[0]-2<=v[2]<=hx[1]+2 and v[1]-v[0]>10]
        if len(vs2)>=2:
            vs=vs2
            hs=[h for h in H if min(v[0] for v in vs)-2<=h[2]<=max(v[1] for v in vs)+2 and h[1]-h[0]>10 and h[0]>=hx[0]-3 and h[1]<=hx[1]+3]
        if len(hs)>=3 and len(vs)>=3:
            return pymupdf.Rect(min(min(h[0] for h in hs),min(v[2] for v in vs)),min(min(v[0] for v in vs),min(h[2] for h in hs)),
                                max(max(h[1] for h in hs),max(v[2] for v in vs)),max(max(v[1] for v in vs),max(h[2] for h in hs)))
    xs=[];ys=[]
    for g in page.get_drawings():
        r=g['rect']
        if not clip.contains(r) or g['type']!='s' or not is_grid(g): continue
        for it in g['items']:
            if it[0]=='l': xs+= [it[1].x,it[2].x]; ys+=[it[1].y,it[2].y]
    if not xs: return None
    return pymupdf.Rect(min(xs),min(ys),max(xs),max(ys))
def polylines(page, clip, is_curve, min_extent=3):
    out=[]
    for g in page.get_drawings():
        r=g['rect']
        if not clip.intersects(r) or not is_curve(g): continue
        if g['type']=='fs':
            vs=[]
            for it in g['items']:
                if it[0]=='l': vs+=[(it[1].x,it[1].y),(it[2].x,it[2].y)]
                elif it[0]=='c': vs+=[(it[1].x,it[1].y),(it[4].x,it[4].y)]
            if len(vs)>=4 and r.width>0.8 and r.height<r.width*3+4:
                vs.sort(); bins={}
                for x,y in vs: bins.setdefault(int(x/1.5),[]).append((x,y))
                pl=[(sum(v[0] for v in b)/len(b),sum(v[1] for v in b)/len(b)) for k,b in sorted(bins.items())]
                if len(pl)==1: pl=[(r.x0,pl[0][1]),(r.x1,pl[0][1])]
                out.append(pl)
            continue
        cur=[]
        for it in g['items']:
            if it[0]=='l':
                a,b=it[1],it[2]
                if cur and abs(cur[-1][0]-a.x)<0.05 and abs(cur[-1][1]-a.y)<0.05: cur.append((b.x,b.y))
                else:
                    if len(cur)>1: out.append(cur)
                    cur=[(a.x,a.y),(b.x,b.y)]
            elif it[0]=='c':
                a,c1,c2,b=it[1],it[2],it[3],it[4]
                pts=[(((1-t)**3)*a.x+3*((1-t)**2)*t*c1.x+3*(1-t)*t*t*c2.x+t**3*b.x,((1-t)**3)*a.y+3*((1-t)**2)*t*c1.y+3*(1-t)*t*t*c2.y+t**3*b.y) for t in np.linspace(0,1,6)]
                if cur and abs(cur[-1][0]-a.x)<0.05 and abs(cur[-1][1]-a.y)<0.05: cur+=pts[1:]
                else:
                    if len(cur)>1: out.append(cur)
                    cur=pts
        if len(cur)>1: out.append(cur)
    return out
def chain(polys, max_gap=9.0, max_dy_slope=3.0):
    """Склеивает куски (в т.ч. пунктир) в кривые, идущие слева направо."""
    P=[sorted(p) if p[0][0]>p[-1][0] else p for p in polys]
    P=[p for p in P if p[-1][0]-p[0][0]>0.3]
    P.sort(key=lambda p:p[0][0])
    chains=[]
    for p in P:
        best=None;bd=1e9
        for c in chains:
            e=c[-1]; dx=p[0][0]-e[0]
            if dx<-0.6 or dx>max_gap: continue
            # экстраполяция наклона конца цепочки
            j=len(c)-2
            while j>0 and c[-1][0]-c[j][0]<2.5: j-=1
            if j>=0 and c[-1][0]-c[j][0]>0.5:
                k=(c[-1][1]-c[j][1])/(c[-1][0]-c[j][0])
                k=max(-max_dy_slope,min(max_dy_slope,k))
            else: k=0
            pred=e[1]+k*max(dx,0); dy=abs(p[0][1]-pred)
            if dy<2.0+0.15*max(dx,0) and dy+0.3*dx<bd: bd=dy+0.3*dx; best=c
        if best is not None: best.extend(p if p[0][0]>best[-1][0]-0.6 else p)
        else: chains.append(list(p))
    for c in chains: c.sort()
    return chains
def resample(c, n=None, step=None):
    xs=np.array([q for q,_ in c]); ys=np.array([h for _,h in c])
    xs,idx=np.unique(xs,return_index=True); ys=ys[idx]
    return xs,ys
def merge_chains(chs, tol=1.6, gap=14.0):
    """Сливает дубли (перекрывающиеся по x и близкие по y) и продолжения одной кривой."""
    chs=[sorted(c) for c in chs]
    def yat(c,x):
        a=np.array(c); return float(np.interp(x,a[:,0],a[:,1]))
    changed=True
    while changed:
        changed=False
        for i in range(len(chs)):
            for j in range(len(chs)):
                if i==j: continue
                a,b=chs[i],chs[j]
                lo=max(a[0][0],b[0][0]); hi=min(a[-1][0],b[-1][0])
                ok=False
                if hi-lo>2:
                    xs=np.linspace(lo,hi,8); d=np.mean([abs(yat(a,x)-yat(b,x)) for x in xs]); ok=d<tol
                elif 0<=b[0][0]-a[-1][0]<gap:
                    # продолжение: сравнить экстраполяцию конца a
                    k=(a[-1][1]-a[max(0,len(a)-6)][1])/max(1e-6,a[-1][0]-a[max(0,len(a)-6)][0])
                    ok=abs(a[-1][1]+k*(b[0][0]-a[-1][0])-b[0][1])<2.5
                if ok:
                    chs[i]=sorted(a+b); chs.pop(j); changed=True; break
            if changed: break
    return chs
