import pymupdf,re,numpy as np,cv2,json,collections
from rdig import *
from vdig import fit_axis
from fancy import grp
from common import *
F='vandjord/vj_kanal_2026.pdf'; URL='https://www.c-o-k.ru/library/catalogs/vandjord/143674.pdf'
d=pymupdf.open(F)
DBG=[]
MRE=re.compile(r'^(SG|VSV|VSL)\.[\dA-Z.()]+$')
def charts(p):
    W=p.get_text('words')
    # подписи оси Q: строка с 'Q' или 'м3/ч' — низ графика
    qrows=[w for w in W if w[4] in('Q','м3/ч','[м3/ч]')]
    out=[]
    for qr in qrows:
        if qr[4]=='[м3/ч]' and any(abs(z[1]-qr[1])<3 and z[4]=='Q' for z in W): continue
        yb=(qr[1]+qr[3])/2
        # сверху: ближайшая рамка — берём область 190pt выше
        top=yb-175
        titles=[w for w in W if MRE.match(w[4]) and top-40<w[1]<yb and w[0]>350]
        region=pymupdf.Rect(60,top-30,560,yb+10)
        out.append((region,yb,titles))
    return out,W
def val(f,y): return f[0]*y+f[1]
def dig(p,region,yb,W):
    ws=[w for w in W if region.contains(pymupdf.Rect(w[:4]))]
    def axes(nums):
        Qr=[n for n in nums if abs(n[1]-yb)<5 and n[0]>160]
        fq=fit_axis([(n[0],n[2]) for n in Qr])
        left=[n for n in nums if n[1]<yb-6 and n[0]<170]
        cols=collections.defaultdict(list)
        for n in left: cols[round(n[0]/10)].append(n)
        cx=sorted(cols,key=lambda c:-np.mean([n[0] for n in cols[c]]))
        fH=fit_axis([(n[1],n[2]) for n in cols[cx[0]]]) if cx else None
        fP=fit_axis([(n[1],n[2]) for n in cols[cx[1]]]) if len(cx)>1 else None
        fE=fit_axis([(n[1],n[2]) for n in cols[cx[2]]]) if len(cx)>2 else None
        return fq,fH,fP,fE
    nums=[((w[0]+w[2])/2,(w[1]+w[3])/2,num(w[4]),w) for w in ws if num(w[4]) is not None and not MRE.match(w[4])]
    fq,fH,fP,fE=axes(nums)
    if not fq or not fH:
        from vdig import ocr_tokens, split_run
        T=ocr_tokens(p,pymupdf.Rect(region.x0,region.y0,region.x1,yb+8),zoom=4)
        nums=[]
        for t in T:
            v=num(t[4].replace(' ',''))
            if v is not None: nums.append(((t[0]+t[2])/2,(t[1]+t[3])/2,v,t))
            else:
                sr=split_run(t)
                if sr: nums+= [(x,y,vv,t) for x,y,vv in sr]
        fq,fH,fP,fE=axes(nums)
    if not fq or not fH: return None
    x0p=(0-fq[1])/fq[0]
    z=3; clip=pymupdf.Rect(x0p-2,region.y0,region.x1-2,yb-7)
    pix=p.get_pixmap(matrix=pymupdf.Matrix(z,z),clip=clip)
    img=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.h,pix.w,pix.n)[:,:,:3].copy()
    m=dark_mask(img,thr=110,sat_max=60)
    for w in ws:
        a=[int((w[0]-clip.x0)*z)-3,int((w[1]-clip.y0)*z)-3,int((w[2]-clip.x0)*z)+3,int((w[3]-clip.y0)*z)+3]
        if a[2]<=0 or a[3]<=0: continue
        m[max(0,a[1]):a[3],max(0,a[0]):a[2]]=0
    Hh,Ww=m.shape
    for x in range(Ww):
        if m[:,x].sum()>0.3*Hh: m[:,max(0,x-1):x+2]=0
    for y in range(Hh):
        if m[y,:].sum()>0.35*Ww: m[max(0,y-1):y+2,:]=0
    C={x:col_clusters(m,x,0,Hh,merge=3) for x in range(Ww)}
    tracks=untangle(multi_tracks(C,0,Ww-1,max_gap=60,tol=4))
    DBG.append(('tracks',len(tracks),[ (t[0],t[-1],len(t)) for t in tracks]))
    # подписи
    lab={}
    for w in ws:
        if w[4]=='QH': lab['QH']=w
        elif w[4]=='P1' and w[1]<yb-10 and w[0]>170: lab['P1']=w
        elif w[4]=='Eta': lab['E']=w
    res={}
    used=set()
    for k in ['QH','E','P1']:
        if k not in lab: continue
        w=lab[k]; cx_=((w[0]+w[2])/2-clip.x0)*z; cy_=((w[1]+w[3])/2-clip.y0)*z
        best=None
        for i,tr in enumerate(tracks):
            if i in used: continue
            dd=min(abs(px-cx_)+abs(py-cy_) for px,py in tr[::3])
            if best is None or dd<best[0]: best=(dd,i)
        if best and best[0]<60*z/3*2:
            used.add(best[1]); f={'QH':fH,'E':fE,'P1':fP}[k]
            if f: res[k]=[(val(fq,clip.x0+px/z),val(f,clip.y0+py/z)) for px,py in tracks[best[1]]]
    return res
# таблицы электрооборудования и данных насоса
EL={};SOL={}
for pi,p in enumerate(d):
    t=p.get_text()
    if 'Данные электрооборудования' not in t: continue
    for y,r in grp(p.get_text('words')):
        s=[w[4] for w in r]
        if s and MRE.match(s[0]) and len(s)>=8:
            nums=[num(z) for z in s[1:] if num(z) is not None]
            volt=' '.join(s[1:3])
            try:
                i=next(k for k,z in enumerate(s) if re.match(r'^\d[х×x]',z) or z in('3','1'))
            except StopIteration: i=1
            EL[s[0]]=dict(raw=s,page=pi+1)
        elif s and MRE.match(s[0]) and len(s)>=2:
            SOL.setdefault(s[0],(pi+1,s))
print('electric rows',len(EL))
ALL={}
for pi in (range(32,98) if __name__=="__main__" else []):
    p=d[pi]; ch,W=charts(p)
    for region,yb,titles in ch:
        res=dig(p,region,yb,W)
        names=[t[4] for t in sorted(titles,key=lambda t:t[1])]
        ALL.setdefault(pi+1,[]).append((names,res and {k:len(v) for k,v in res.items()}))
        if res and names: 
            for nm in names: ALL[nm]=(pi+1,res)
for k in list(ALL)[:0]: pass
if __name__=='__main__': json.dump({k:v for k,v in ALL.items() if isinstance(k,str)},open('vj_curves.json','w'))
print(sum(1 for k in ALL if isinstance(k,str)),'model curve sets')
for k,v in ALL.items():
    if isinstance(k,int):
        for names,r in v:
            if not r or 'QH' not in r: print('p',k,names,r)
