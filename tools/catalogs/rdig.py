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
def track(C, x0, x1, xs, ys, max_gap=25, tol=3.0):
    """C: dict x->clusters. Старт (xs,ys); идём вправо, выбирая ближайший кластер к экстраполяции."""
    pts=[(xs,ys)]
    for x in range(xs+1,x1+1):
        cands=C.get(x,[])
        lx,ly=pts[-1]
        back=[p for p in pts if lx-p[0]>=4][-1:] 
        slope=(ly-back[0][1])/(lx-back[0][0]) if back else 0
        pred=ly+slope*(x-lx)
        if cands:
            c=min(cands,key=lambda c:abs(c-pred))
            if abs(c-pred)<=tol+0.6*(x-lx): pts.append((x,c)); continue
        if x-lx>max_gap: break
    return pts
