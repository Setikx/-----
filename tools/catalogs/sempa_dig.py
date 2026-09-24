"""Sempa DPT: векторные графики (H, P, η, NPSH) по диаметрам колеса."""
import pymupdf,re,numpy as np,collections
from vdig import fit_axis
def num(s):
    s=s.replace(',','.')
    try: return float(s)
    except: return None
def is_curve(g):
    c=g.get('color')
    return g['type']=='s' and c and c[0]<0.2 and 0.5<c[1]<0.8 and c[2]>0.85 and (g.get('width') or 0)<=0.9 and len(g['items'])>5
def subpaths(g):
    out=[];cur=[]
    for it in g['items']:
        if it[0]!='l': continue
        a,b=it[1],it[2]
        if cur and abs(cur[-1][0]-a.x)<0.3 and abs(cur[-1][1]-a.y)<0.3: cur.append((b.x,b.y))
        else:
            if len(cur)>3: out.append(cur)
            cur=[(a.x,a.y),(b.x,b.y)]
    if len(cur)>3: out.append(cur)
    out.sort(key=lambda c:c[0][0]); res=[]
    for c in out:
        for r in res:
            if abs(r[-1][0]-c[0][0])<0.6 and abs(r[-1][1]-c[0][1])<0.6: r+=c[1:]; break
        else: res.append(list(c))
    return res
def panels(p,W=None):
    W=W or p.get_text('words')
    nums=[w for w in W if num(w[4]) is not None]
    rows=collections.defaultdict(list)
    for w in sorted(nums,key=lambda w:w[1]):
        k=next((k for k in rows if abs(k-w[1])<2.5),None)
        rows[k if k is not None else w[1]].append(w)
    qrows=[]
    for y,r in rows.items():
        r=sorted(r,key=lambda w:w[0]); v=[num(w[4]) for w in r]
        if len(r)>=5 and v==sorted(v) and v[0]==0 and len(set(v))==len(v): qrows.append((y,r))
    qrows.sort(); out=[]; top=60
    for y,row in qrows:
        x0=min(w[0] for w in row)
        ylab=[w for w in nums if w[2]<x0+3 and top<w[1]<y-3 and abs(w[1]-y)>2]
        txt=' '.join(w[4] for w in W if top<w[1]<y+2 and w[2]<x0+2)
        kind='H' if 'Hm' in txt else 'P' if 'Power' in txt else 'E' if 'Effic' in txt else 'N' if 'NPSH' in txt else '?'
        if kind=='?' and len(out)<4: kind='HPEN'[len(out)]
        kq=fit_axis([((w[0]+w[2])/2,num(w[4])) for w in row]); kh=fit_axis([((w[1]+w[3])/2,num(w[4])) for w in ylab]) if len(ylab)>=2 else None
        out.append(dict(kind=kind,top=top,bottom=y,kq=kq,kh=kh,x0=x0))
        top=y+12
    return out
def ocr_words(p,Z=3):
    from rdig import ocr
    pm=p.get_pixmap(matrix=pymupdf.Matrix(Z,Z)); a=np.frombuffer(pm.samples,np.uint8).reshape(pm.h,pm.w,pm.n)[:,:,:3].copy()
    out=[]
    for t in ocr(a):
        x0,y0,x1,y1,s=t[0]/Z,t[1]/Z,t[2]/Z,t[3]/Z,t[4].strip()
        m=re.fullmatch(r'[Ø0oO]\s*(\d{2,3})',s) if s[:1] in 'Øø' else None
        if s[:1] in 'Øø':
            v=re.sub(r'\D','',s)
            if v: out+=[(x0,y0,x0+(x1-x0)*0.3,y1,'Ø'),(x0+(x1-x0)*0.35,y0,x1,y1,v)]
            continue
        out.append((x0,y0,x1,y1,s))
    return out
def page_curves(p,W=None):
    W=W or p.get_text('words'); P=panels(p,W); res={}; labs=[]
    for i,w in enumerate(W):
        if w[4].startswith('Ø'):
            cand=[v for v in W if num(v[4]) is not None and abs((v[1]+v[3])/2-(w[1]+w[3])/2)<2 and w[2]-1<=v[0]<=w[2]+8]
            if w[4][1:] and num(w[4][1:]): cand.append((0,0,0,0,w[4][1:]))
            if cand:
                t=max((v[4] for v in cand),key=len); labs.append(((w[0]+w[2])/2,(w[1]+w[3])/2,int(num(t))))
    if not labs:
        for w in W:
            t=w[4].lstrip('0oO')
            if re.fullmatch(r'\d{2,3}',t) and 90<=int(t)<=700 and w[0]>200:
                labs.append((w[0]-4,(w[1]+w[3])/2,int(t)))
    for pn in P:
        if not pn['kq'] or not pn['kh'] or pn['kind']=='?': continue
        segs=[]
        for g in p.get_drawings():
            if is_curve(g) and pn['top']<g['rect'].y0 and g['rect'].y1<pn['bottom']+2: segs+=subpaths(g)
        # склейка кусков одной кривой: конец ≈ начало (до 2 pt), с продолжением наклона
        segs=[sorted(sg) for sg in segs]; changed=True
        while changed:
            changed=False
            for a in range(len(segs)):
                for b in range(len(segs)):
                    if a==b: continue
                    A,B=segs[a],segs[b]
                    if 0<=B[0][0]-A[-1][0]<7 and abs(B[0][1]-A[-1][1])<3.0:
                        segs[a]=A+B; del segs[b]; changed=True; break
                if changed: break
        cand=[]
        for si,sg in enumerate(segs):
            ex,ey=max(sg,key=lambda q:q[0])
            for l in labs:
                if pn['top']<l[1]<pn['bottom']+4 and abs(l[1]-ey)<16 and -14<l[0]-ex<32:
                    cand.append((abs(l[1]-ey)+0.3*abs(l[0]-ex),si,l[2]))
        cand.sort(); us=set(); ul=set(); cur={}
        for dist,si,dd in cand:
            if si in us or dd in ul: continue
            us.add(si); ul.add(dd)
            cur[dd]=sorted(((pn['kq'][0]*x+pn['kq'][1]),(pn['kh'][0]*y+pn['kh'][1])) for x,y in segs[si])
        res[pn['kind']]=cur
    return res
