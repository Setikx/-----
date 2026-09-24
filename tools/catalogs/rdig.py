"""Оцифровка растровых графиков: OCR подписей осей + выделение тёмных кривых связными компонентами."""
import cv2, numpy as np, re
from vdig import fit_axis, split_run, NUM
_ocr=None
def ocr(img):
    global _ocr
    if _ocr is None:
        from rapidocr_onnxruntime import RapidOCR
        _ocr=RapidOCR()
    res,_=_ocr(img)
    out=[]
    for box,txt,conf in (res or []):
        xs=[b[0] for b in box]; ys=[b[1] for b in box]
        out.append((min(xs),min(ys),max(xs),max(ys),txt.strip(),conf))
    return out
def num_tokens(toks):
    out=[]
    for t in toks:
        s=t[4]
        if re.fullmatch(r'\d{1,3}(,\d{3})+',s): s=s.replace(',','')
        s=s.replace(',','.').replace('O','0').replace('o','0')
        m=re.match(r'^(-?\d+(?:\.\d+)?)',s)
        if m and (len(m.group(1))==len(s) or re.match(r'^\d+(?:\.\d+)?\s*[a-zA-Zm³%/()]',s)):
            if len(m.group(1))<len(s) and not re.search(r'm|%',s[len(m.group(1)):]): continue
            # у числа с хвостом («0m³/h») уточняем бокс пропорционально
            frac=len(m.group(1))/max(1,len(s)); x1=t[0]+(t[2]-t[0])*frac
            out.append(((t[0]+x1)/2,(t[1]+t[3])/2,float(m.group(1)),t))
        else:
            sr=split_run(t)
            if sr: out+= [(x,y,v,t) for x,y,v in sr]
    return out
def dark_mask(img, thr=100, sat_max=80):
    b,g,r=[img[:,:,i].astype(int) for i in range(3)]
    mx=np.maximum(np.maximum(r,g),b); mn=np.minimum(np.minimum(r,g),b)
    return ((mx<thr)&((mx-mn)<sat_max)).astype(np.uint8)
def components(mask, min_w=15, min_px=30):
    n,lab,st,_=cv2.connectedComponentsWithStats(mask,8)
    out=[]
    for i in range(1,n):
        x,y,w,h,a=st[i]
        if w>=min_w and a>=min_px: out.append((i,x,y,w,h,a))
    return lab,out
def trace(lab, i, x0, x1, step=1):
    pts=[]
    sub=(lab==i)
    for x in range(x0,x1+1,step):
        ys=np.nonzero(sub[:,x])[0]
        if len(ys): pts.append((x,float(np.median(ys))))
    return pts
def col_clusters(m, x, y0, y1, merge=2):
    ys=np.nonzero(m[y0:y1,x])[0]+y0
    out=[];cur=[]
    for y in ys:
        if cur and y-cur[-1]>merge: out.append(sum(cur)/len(cur)); cur=[]
        cur.append(y)
    if cur: out.append(sum(cur)/len(cur))
    return out
def track(C, x0, x1, xs, ys, max_gap=25, tol=3.0, base=18):
    """C: dict x->clusters. Старт (xs,ys); идём вправо, выбирая ближайший кластер к экстраполяции
    (наклон и кривизна по последним ~base пикселям)."""
    pts=[(xs,ys)]
    for x in range(xs+1,x1+1):
        cands=C.get(x,[])
        lx,ly=pts[-1]
        recent=[p for p in pts if lx-p[0]<=base]
        if len(recent)>=6 and recent[-1][0]-recent[0][0]>=5:
            a=np.array(recent,dtype=float)
            deg=2 if len(recent)>=12 else 1
            cf=np.polyfit(a[:,0]-lx,a[:,1],deg)
            pred=float(np.polyval(cf,x-lx))
        else:
            back=[p for p in pts if lx-p[0]>=4][-1:]
            slope=(ly-back[0][1])/(lx-back[0][0]) if back else 0
            pred=ly+slope*(x-lx)
        if cands:
            c=min(cands,key=lambda c:abs(c-pred))
            if abs(c-pred)<=tol+0.3*(x-lx): pts.append((x,c)); continue
        if x-lx>max_gap: break
    return pts
def track_lr(C, x0, x1, xs, ys, max_gap=25, tol=3.0):
    """Трек в обе стороны от затравки."""
    R=track(C,x0,x1,xs,ys,max_gap,tol)
    Cm={(-x):v for x,v in C.items()}
    Lr=track(Cm,-x1,-x0,-xs,ys,max_gap,tol)
    L=[(-x,y) for x,y in Lr[1:]]
    return sorted(L+R)
def multi_tracks(C, x0, x1, fracs=(0.5,0.3,0.7,0.15,0.85), min_len=0.3, max_gap=30, tol=4):
    tracks=[]
    W=x1-x0
    for f in fracs:
        xs=int(x0+f*W)
        # ближайший столбец с кластерами
        for dx in range(0,15):
            if C.get(xs+dx): xs=xs+dx; break
        for c in C.get(xs,[]):
            if any(abs(dict(t).get(xs,-999)-c)<4 for t in tracks): continue
            tr=track_lr(C,x0,x1,xs,c,max_gap,tol)
            if tr[-1][0]-tr[0][0]>=min_len*W:
                # не дубликат ли
                dt=dict(tr); dup=False
                for t in tracks:
                    d2=dict(t); common=[x for x in dt if x in d2]
                    if len(common)>0.7*len(dt) and np.mean([abs(dt[x]-d2[x]) for x in common])<3: dup=True; break
                if not dup: tracks.append(tr)
    return tracks
def untangle(tracks, w=25, close=3.5):
    """На пересечениях двух треков меняет «хвосты» местами, если так сохраняется непрерывность наклона."""
    T=[dict(t) for t in tracks]
    def slope(d,xa,xb):
        xs=[x for x in range(xa,xb+1) if x in d]
        if len(xs)<4: return None
        return np.polyfit(xs,[d[x] for x in xs],1)[0]
    changed=True; guard=0
    while changed and guard<20:
        changed=False; guard+=1
        for i in range(len(T)):
            for j in range(i+1,len(T)):
                A,B=T[i],T[j]
                common=sorted(x for x in A if x in B)
                xs=[x for x in common if abs(A[x]-B[x])<close]
                # группы соседних x — отдельные пересечения
                groups=[];cur=[]
                for x in xs:
                    if cur and x-cur[-1]>3: groups.append(cur);cur=[]
                    cur.append(x)
                if cur: groups.append(cur)
                for g in groups:
                    xc=g[len(g)//2]; a0=g[0]; a1=g[-1]
                    sA=slope(A,a0-w,a0-1); sB=slope(B,a0-w,a0-1); sA2=slope(A,a1+1,a1+w); sB2=slope(B,a1+1,a1+w)
                    if None in (sA,sB,sA2,sB2): continue
                    if abs(sA-sB2)+abs(sB-sA2)+1e-6 < abs(sA-sA2)+abs(sB-sB2):
                        tA={x:y for x,y in A.items() if x>xc}; tB={x:y for x,y in B.items() if x>xc}
                        for x in tA: del A[x]
                        for x in tB: del B[x]
                        A.update(tB); B.update(tA); changed=True
                        break
                if changed: break
            if changed: break
    return [sorted(d.items()) for d in T]
def run_filter(m, lo=3, hi=25):
    """Оставляет только вертикальные «пробежки» длиной lo..hi пикселей (толстые кривые без тонкой сетки)."""
    out=np.zeros_like(m)
    H,W=m.shape
    for x in range(W):
        col=m[:,x]; ys=np.nonzero(col)[0]
        if len(ys)==0: continue
        br=np.where(np.diff(ys)>1)[0]
        starts=np.r_[ys[0],ys[br+1]]; ends=np.r_[ys[br],ys[-1]]
        for s,e in zip(starts,ends):
            if lo<=e-s+1<=hi: out[s:e+1,x]=1
    return out
