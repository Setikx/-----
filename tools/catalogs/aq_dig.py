import json,re,numpy as np,cv2,sys
sys.path.insert(0,'.')
from rdig import col_clusters,multi_tracks,untangle,num_tokens
from vdig import fit_axis,split_run
img=cv2.imread('aquastrong/p62.png'); T=json.load(open('aquastrong/ocr62c.json'))
COLS=[(1600,2080),(2075,2545),(2545,3015)]; ROWS=[(360,830),(900,1380),(1440,1920)]
b,g,r=[img[:,:,i].astype(int) for i in range(3)]
blue=((b-r>45)&(b>90)&(b-g>15)).astype(np.uint8)
def chart(ci,ri):
    x0,x1=COLS[ci]; y0,y1=ROWS[ri]
    toks=[t for t in T if x0<=(t[0]+t[2])/2<=x1 and y0<=(t[1]+t[3])/2<=y1]
    nums=[]
    for t in toks:
        if re.fullmatch(r'\d{5,}',t[4]): nums+=[(x,y,v,t) for x,y,v in (split_run(tuple(t)) or [])]
        else: nums+=num_tokens([tuple(t)])
    # левая ось H: самый левый столбец чисел
    xl=min(n[0] for n in nums if n[1]<y1-60)
    H=[(n[1],n[2]) for n in nums if abs(n[0]-xl)<14]
    kh,bh,nh,eh=fit_axis(H)
    y_zero=-bh/kh
    Q=[(n[0],n[2]) for n in nums if y_zero+5<n[1]<y_zero+45 and n[0]>xl+15]
    kq,bq,nq,eq=fit_axis(Q)
    # привязка к линиям сетки (серые линии внутри поля)
    gray=((np.abs(r-g)<20)&(np.abs(g-b)<20)&(r<215)&(r>60)).astype(np.uint8)
    xz=int(round(-bq/kq)); yz=int(round(-bh/kh)); ytop=int(round((max(v for _,v in H)-bh)/kh))
    xe=int(round((max(v for _,v in Q)-bq)/kq))
    colsum=gray[ytop:yz, xz-5:xe+15].sum(0); vl=[i+xz-5 for i in range(1,len(colsum)-1) if colsum[i]>0.6*(yz-ytop) and colsum[i]>=colsum[i-1] and colsum[i]>=colsum[i+1]]
    rowsum=gray[ytop-5:yz+5, xz:xe].sum(1); hl=[i+ytop-5 for i in range(1,len(rowsum)-1) if rowsum[i]>0.6*(xe-xz) and rowsum[i]>=rowsum[i-1] and rowsum[i]>=rowsum[i+1]]
    def snap(P,lines,k,bb):
        out=[]
        for p,v in P:
            pr=(v-bb)/k; c=min(lines,key=lambda L:abs(L-pr)) if lines else None
            out.append((c,v) if c is not None and abs(c-pr)<10 else (pr,v))
        return out
    Q2=snap(Q,vl,kq,bq); H2=snap(H,hl,kh,bh)
    kq,bq,nq,eq=fit_axis(Q2); kh,bh,nh,eh=fit_axis(H2)
    x_zero=-bq/kq
    return dict(x0=x0,x1=x1,y0=y0,y1=y1,kh=kh,bh=bh,kq=kq,bq=bq,xz=x_zero,yz=y_zero,nh=nh,nq=nq,H=H,Q=Q)
if __name__=='__main__':
    for ri in range(3):
        for ci in range(3):
            c=chart(ci,ri); print(ci,ri,'H',c['nh'],sorted(v for _,v in c['H']),'Q',c['nq'],sorted(v for _,v in c['Q']),'x0',round(c['xz']),'y0',round(c['yz']))
def curves(c):
    xz=int(round(-c['bq']/c['kq'])); yz=int(round(-c['bh']/c['kh']))
    X0=xz+2; X1=c['x1']-110; Y0=c['y0']; Y1=yz+3
    m=blue.copy(); m[:, :X0]=0; m[:, X1:]=0; m[:Y0]=0; m[Y1:]=0
    C={x:col_clusters(m,x,Y0,Y1,merge=3) for x in range(X0,X1)}
    tr=multi_tracks(C,X0,X1,fracs=(0.1,0.25,0.4,0.55,0.7,0.85),min_len=0.15,max_gap=40,tol=4)
    tr=untangle(tr)
    out=[]
    for t in tr:
        out.append([(c['kq']*x+c['bq'], c['kh']*y+c['bh']) for x,y in t])
    return tr,out
def draw(ci,ri,fn):
    c=chart(ci,ri); tr,_=curves(c); v=img.copy()
    cols=[(0,0,255),(0,200,0),(255,0,255),(0,165,255),(128,0,0),(0,128,128),(255,128,0),(128,0,255),(0,0,128)]
    for i,t in enumerate(tr):
        for x,y in t: cv2.circle(v,(int(x),int(y)),1,cols[i%9],-1)
    cv2.imwrite(fn,v[c['y0']:c['y1'],c['x0']:c['x1']]); return tr
LAB={(0,0):['50WQ20-45-7.5','50WQ15-40-5.5','50WQ15-26-3','50WQ15-20-2.2','50WQ8-20-1.5','50WQ8-16-1.1','50WQ10-10-0.75'],
 (0,1):['65WQ25-28-4','65WQ25-22-3','65WQ25-17-2.2','65WQ15-15-1.5','65WQ15-10-1.1'],
 (0,2):['80WQ30-33-7.5','80WQ30-30-5.5','80WQ40-18-4','80WQ40-13-3','80WQ40-9-2.2'],
 (1,0):['100WQ65-22-7.5','100WQ60-9-3'],  # 100WQ65-15-5.5, 100WQ60-13-4, 150WQ100-10-7.5 — кривые сплетены, не разделяются
 (1,1):['100WQ100-36-22(4P)','100WQ100-31-18.5(4P)','100WQ100-27-15(4P)','100WQ100-22-11(4P)','100WQ100-15-7.5(4P)','100WQ65-15-5.5(4P)'],
 (1,2):['150WQ150-40-37(4P)','150WQ150-34-30(4P)','150WQ150-28-22(4P)','150WQ150-24-18.5(4P)','150WQ150-20-15(4P)','150WQ150-15-11(4P)','150WQ150-10-7.5(4P)','150WQ110-10-5.5(4P)'],
 (2,0):['200WQ300-30-45(4P)','200WQ300-25-37(4P)','200WQ300-21-30(4P)','200WQ300-18-22(4P)','200WQ300-15-18.5(4P)','200WQ300-12-15(4P)','200WQ300-9-11(4P)','200WQ250-6-7.5(4P)'],
 (2,1):['250WQ500-21-45(4P)','250WQ500-18-37(4P)','250WQ500-14-30(4P)','250WQ500-11-22(4P)'],
 (2,2):['300WQ800-14-45(4P)','300WQ800-11-37(4P)','300WQ800-8-30(4P)']}
def merge(tr, dx=30, dy=12):
    tr=[list(t) for t in tr]; ch=True
    while ch:
        ch=False
        for i,a in enumerate(tr):
            for j,b in enumerate(tr):
                if i==j: continue
                if 0<b[0][0]-a[-1][0]<=dx and abs(b[0][1]-a[-1][1])<=dy+0.5*(b[0][0]-a[-1][0]):
                    tr[i]=a+b; del tr[j]; ch=True; break
            if ch: break
    return tr
def nominal(m):
    z=re.match(r'\d+WQ(\d+)-(\d+(?:\.\d+)?)-',m); return float(z.group(1)),float(z.group(2))
def assign(M):
    import itertools
    n,m=M.shape; best=(1e9,None)
    if n>=m:
        for rows in itertools.permutations(range(n),m):
            s=sum(M[rows[j],j] for j in range(m))
            if s<best[0]: best=(s,[(rows[j],j) for j in range(m)])
    else:
        for cols in itertools.permutations(range(m),n):
            s=sum(M[i,cols[i]] for i in range(n))
            if s<best[0]: best=(s,[(i,cols[i]) for i in range(n)])
    return best[1]
def digitize(ri,ci):
    c=chart(ci,ri); tr=dedup(curves3(c)); tr=cut_foreign(tr); tr=[cut_kinks(t) for t in tr]; labs=LAB[(ri,ci)]
    cv=[[(c['kq']*x+c['bq'],c['kh']*y+c['bh']) for x,y in t] for t in tr]
    M=np.zeros((len(cv),len(labs)))
    for i,p in enumerate(cv):
        q=np.array([a for a,_ in p]);h=np.array([b for _,b in p])
        for j,l in enumerate(labs):
            qn,hn=nominal(l)
            M[i,j]=abs(np.interp(qn,q,h)-hn)/hn if q[0]<=qn<=q[-1] else 5
    return c,tr,cv,labs,M,assign(M)
class Track(list):
    def __init__(s,pts,jumps): super().__init__(pts); s.jumps=jumps
def ptrack(m, p, d, X0, X1, Y0, Y1, R=5, max_jump=28, amax=50, alpha=0.35, sgn=1):
    """Параметрический трекер: шаг R вдоль кривой, выбор ближайшего к текущему направлению участка маски."""
    H,W=m.shape; pts=[tuple(p)]; jumps=[]; p=np.array(p,float); d=np.array(d,float); d/=np.linalg.norm(d)
    while True:
        best=None
        for r in list(range(R,R+1))+list(range(R+3,max_jump+1,3)):
            angs=np.deg2rad(np.arange(-amax,amax+1,3)); base=np.arctan2(d[1],d[0])
            hits=[]
            for a in angs:
                q=p+r*np.array([np.cos(base+a),np.sin(base+a)]); x,y=int(round(q[0])),int(round(q[1]))
                hits.append(0<=x<W and 0<=y<H and m[y,x]>0)
            runs=[];cur=[]
            for a,h in zip(angs,hits):
                if h: cur.append(a)
                elif cur: runs.append(cur);cur=[]
            if cur: runs.append(cur)
            if runs:
                a=min((np.mean(rn) for rn in runs),key=abs)
                if r>R and abs(a)>np.deg2rad(20): continue
                best=(r,a); break
        if best is None: break
        r,a=best; base=np.arctan2(d[1],d[0])
        if r>R: jumps.append(len(pts))
        nd=np.array([np.cos(base+a),np.sin(base+a)])
        p=p+r*nd; d=(1-alpha)*d+alpha*nd; d/=np.linalg.norm(d)
        if sgn*d[0]<0.02: d[0]=0.02*sgn; d/=np.linalg.norm(d)   # кривые Q–H монотонны по Q
        if not (X0<=p[0]<=X1 and Y0<=p[1]<=Y1): break
        pts.append(tuple(p))
        if len(pts)>3000: break
    return Track(pts,jumps)
def curves2(c):
    xz=int(round(-c['bq']/c['kq'])); yz=int(round(-c['bh']/c['kh']))
    X0=xz+2; X1=c['x1']-110; Y0=c['y0']; Y1=yz+2
    m=blue.copy(); m[:, :X0]=0; m[:, X1:]=0; m[:Y0]=0; m[Y1:]=0
    m=cv2.dilate(m,np.ones((2,2),np.uint8))
    starts=col_clusters(m,X0+3,Y0,Y1,merge=3)
    tr=[]
    for y in starts:
        # начальное направление по первым 12 px
        ys=[col_clusters(m,X0+3+k,Y0,Y1,merge=3) for k in (0,10)]
        y2=min(ys[1],key=lambda v:abs(v-y)) if ys[1] else y
        pts=ptrack(m,(X0+3,y),(10,y2-y),X0,X1,Y0,Y1)
        tr.append(pts)
    return tr

def curves3(c, fracs=(0.02,0.12,0.25,0.4,0.55,0.7,0.85)):
    xz=int(round(-c['bq']/c['kq'])); yz=int(round(-c['bh']/c['kh']))
    X0=xz+2; X1=c.get('X1',c['x1']-110); Y0=c['y0']; Y1=yz+2
    m=blue.copy(); m[:, :X0]=0; m[:, X1:]=0; m[:Y0]=0; m[Y1:]=0
    m=cv2.dilate(m,np.ones((2,2),np.uint8))
    tracks=[]
    def covered(x,y):
        for t in tracks:
            a=np.array(t); k=np.abs(a[:,0]-x)<3
            if k.any() and np.min(np.abs(a[k,1]-y))<5: return True
        return False
    for f in fracs:
        xs=int(X0+3+f*(X1-X0-6))
        for y in col_clusters(m,xs,Y0,Y1,merge=2):
            if covered(xs,y): continue
            nb=[v for v in col_clusters(m,xs+6,Y0,Y1,merge=2)]; y2=min(nb,key=lambda v:abs(v-y)) if nb else y
            nb0=[v for v in col_clusters(m,xs-6,Y0,Y1,merge=2)]; y0_=min(nb0,key=lambda v:abs(v-y)) if nb0 else y
            if abs(y2-y)>8 or abs(y0_-y)>8: continue
            F=ptrack(m,(xs,y),(12,y2-y0_),X0,X1,Y0,Y1)
            B=ptrack(m,(xs,y),(-12,-(y2-y0_)),X0,X1,Y0,Y1,sgn=-1)
            t=Track(sorted(B[1:],key=lambda p:p[0])+list(F),[j+len(B)-1 for j in F.jumps])
            if t[-1][0]-t[0][0]<0.1*(X1-X0): continue
            tracks.append(t)
    return tracks
def show(ri,ci,tr,fn):
    c=chart(ci,ri); v=img.copy()
    cols=[(0,0,255),(0,200,0),(255,0,255),(0,165,255),(128,0,0),(0,128,128),(255,128,0),(128,0,255),(0,0,128)]
    for k,t in enumerate(tr):
        for x,y in t: cv2.circle(v,(int(x),int(y)),1,cols[k%9],-1)
    return v[c['y0']:c['y1'],c['x0']:c['x1']]

def dedup(tr):
    out=[]
    for t in sorted(tr,key=lambda t:-(t[-1][0]-t[0][0])):
        a=np.array(t); dup=False
        for u in out:
            b=np.array(u); lo=max(a[0,0],b[0,0]); hi=min(a[-1,0],b[-1,0])
            if hi-lo>0.6*(a[-1,0]-a[0,0]):
                xs=np.linspace(lo,hi,30)
                if np.median(np.abs(np.interp(xs,a[:,0],a[:,1])-np.interp(xs,b[:,0],b[:,1])))<3: dup=True;break
        if not dup: out.append(t)
    return out

def cut_foreign(tr, tol=4):
    """После прыжка через разрыв трек, идущий дальше по чужой кривой, обрезается в месте прыжка."""
    out=[]
    for k,t in enumerate(tr):
        J=getattr(t,'jumps',[]); cut=None
        for j in J:
            tail=np.array(t[j:],float)
            if len(tail)<3: continue
            for m,u in enumerate(tr):
                if m==k: continue
                b=np.array(u,float); 
                if b[0,0]>tail[0,0]-10: continue   # чужая кривая должна проходить и до точки прыжка
                dd=[np.min(np.hypot(b[:,0]-x,b[:,1]-y)) for x,y in tail]
                if np.median(dd)<tol: cut=j; break
            if cut is not None: break
        out.append(Track(t[:cut],[]) if cut is not None else t)
    return out
def cut_kinks(t, w=8, ang=40):
    """Обрезает трек на резком изломе (переход на чужую кривую)."""
    a=np.array(t,float)
    for i in range(w,len(a)-w):
        d1=a[i]-a[i-w]; d2=a[i+w]-a[i]
        c=np.dot(d1,d2)/(np.linalg.norm(d1)*np.linalg.norm(d2)+1e-9)
        if np.degrees(np.arccos(np.clip(c,-1,1)))>ang: return t[:i+1]
    return t
