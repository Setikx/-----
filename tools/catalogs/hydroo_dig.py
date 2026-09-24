"""Hydroo WDROO 2023: растровая оцифровка сводных графиков Q–H; подписи DN-Q-H привязываются по номинальной точке."""
import pymupdf,numpy as np,cv2,re,json,sys
sys.path.insert(0,'.')
from rdig import ocr,col_clusters
from vdig import fit_axis
from aq_dig import ptrack,Track,dedup,cut_kinks
Z=6
def num(s):
    try: return float(s)
    except: return None
def charts(p):
    """Графики на странице: по заголовкам 'WFxx' (текст) и OCR подписей осей."""
    W=p.get_text('words')
    heads=[w for w in W if re.fullmatch(r'W[FGXV]\d+(/\d+)?',w[4])]
    out=[]
    pm=p.get_pixmap(matrix=pymupdf.Matrix(3,3)); a=np.frombuffer(pm.samples,np.uint8).reshape(pm.h,pm.w,pm.n)[:,:,:3].copy()
    T=[(t[0]/3,t[1]/3,t[2]/3,t[3]/3,t[4]) for t in ocr(a)]
    for h in heads:
        # рамка графика: подписи Q — строка чисел ниже заголовка; H — столбец чисел левее
        below=[t for t in T if num(t[4]) is not None and t[1]>h[3]+20]
        rows={}
        for t in below:
            k=next((k for k in rows if abs(k-t[1])<3),t[1]); rows.setdefault(k,[]).append(t)
        qrow=None
        for y in sorted(rows):
            r=sorted(rows[y],key=lambda t:t[0]); v=[num(t[4]) for t in r]
            if len(r)>=4 and v==sorted(v) and v[0]==0: qrow=(y,r); break
        if not qrow: continue
        y,r=qrow; x0=r[0][0]
        kq=fit_axis([((t[0]+t[2])/2,num(t[4])) for t in r if num(t[4])!=0 or True])
        hl=[t for t in T if num(t[4]) is not None and t[2]<x0+12 and t[0]>x0-40 and h[1]-30<t[1]<y-5]
        kh=fit_axis([((t[1]+t[3])/2,num(t[4])) for t in hl])
        if not kq or not kh: continue
        xr=max(t[2] for t in r)+10
        out.append(dict(title=h[4],clip=pymupdf.Rect(x0+5,h[1]-25,xr+40,y-4),kq=kq,kh=kh,W=W,head=h))
    return out
def trace(p,c):
    pm=p.get_pixmap(matrix=pymupdf.Matrix(Z,Z),clip=c['clip'])
    a=np.frombuffer(pm.samples,np.uint8).reshape(pm.h,pm.w,pm.n)[:,:,:3].copy()
    g=a.astype(int); mx=g.max(2); mn=g.min(2)
    m=((mx<120)&(mx-mn<40)).astype(np.uint8)
    # убрать текст (слова PDF) и сетку (длинные горизонтальные/вертикальные линии)
    for w in c['W']:
        r=pymupdf.Rect(w[:4])
        if r.intersects(c['clip']):
            x0=int((r.x0-c['clip'].x0)*Z)-3; y0=int((r.y0-c['clip'].y0)*Z)-3; x1=int((r.x1-c['clip'].x0)*Z)+3; y1=int((r.y1-c['clip'].y0)*Z)+3
            m[max(0,y0):y1,max(0,x0):x1]=0
    hl=cv2.morphologyEx(m,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(int(Z*12),1)))
    vl=cv2.morphologyEx(m,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(1,int(Z*12))))
    m[(hl>0)|(vl>0)]=0
    m=cv2.dilate(m,np.ones((2,2),np.uint8))
    H,Wd=m.shape; X0,X1,Y0,Y1=2,Wd-3,2,H-3; tracks=[]
    def covered(x,y):
        for t in tracks:
            b=np.array(t); k=np.abs(b[:,0]-x)<Z*0.6
            if k.any() and np.min(np.abs(b[k,1]-y))<Z*0.8: return True
        return False
    for f in np.linspace(0.02,0.9,12):
        xs=int(X0+f*(X1-X0))
        for y in col_clusters(m,xs,Y0,Y1,merge=2):
            if covered(xs,y): continue
            nb=col_clusters(m,xs+int(Z),Y0,Y1,merge=2); nb0=col_clusters(m,xs-int(Z),Y0,Y1,merge=2)
            if not nb or not nb0: continue
            y2=min(nb,key=lambda v:abs(v-y)); y0_=min(nb0,key=lambda v:abs(v-y))
            if abs(y2-y)>Z*1.5 or abs(y0_-y)>Z*1.5: continue
            F=ptrack(m,(xs,y),(2*Z,y2-y0_),X0,X1,Y0,Y1,R=int(Z*0.7),max_jump=int(Z*2.5),alpha=0.3)
            B=ptrack(m,(xs,y),(-2*Z,-(y2-y0_)),X0,X1,Y0,Y1,R=int(Z*0.7),max_jump=int(Z*2.5),alpha=0.3,sgn=-1)
            t=Track(sorted(B[1:],key=lambda q:q[0])+list(F),[])
            if t[-1][0]-t[0][0]<0.12*(X1-X0): continue
            tracks.append(t)
    tracks=dedup(tracks); tracks=[cut_kinks(t,w=int(Z*1.5),ang=40) for t in tracks]
    out=[]
    for t in tracks:
        pts=[]
        for x,y in t:
            X=c['clip'].x0+x/Z; Y=c['clip'].y0+y/Z
            pts.append((c['kq'][0]*X+c['kq'][1],c['kh'][0]*Y+c['kh'][1]))
        out.append(sorted(pts))
    return out,m
