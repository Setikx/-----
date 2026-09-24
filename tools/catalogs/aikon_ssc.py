import pymupdf,cv2,numpy as np,re,sys,json,collections
from rdig import *
from common import *
from fancy import grp
MRE=re.compile(r'^\d+SSC[\d\s.,\-]+(?:OG|G)?$')
def norm(s): return re.sub(r'\s+','',s).replace(',','.')
def tables(d,pages):
    T={}
    for pn in pages:
        p=d[pn-1]; W=p.rect.width
        halves=[(0,W)] if 'Подача' in p.get_text() else [(0,W/2),(W/2,W)]
        for x0,x1 in halves:
            for y,r in grp([w for w in p.get_text('words') if x0<=w[0]<x1]):
                t=[w[4] for w in r]
                if not t or not re.match(r'^\d+SSC',t[0]): continue
                name=t[0]; rest=t[1:]
                if rest and re.match(r'^[\d.,]+-[\d.,\-]+(OG|G)?$',rest[0]): name+=rest[0]; rest=rest[1:]
                vals=[num(z) for z in rest]
                T[norm(name)]=vals
    return T
def clean_tok(s): return s.strip('-—–|.·: ')
def digitize(img, want=('H','EFF','P','NPSH')):
    Hh,Ww=img.shape[:2]
    T=ocr(img)
    T=[(t[0],t[1],t[2],t[3],clean_tok(t[4]) if re.match(r'^[-—–|]*\d',t[4]) or re.search(r'\d[-—–|]+$',t[4]) else t[4],t[5]) for t in T]
    lab={}
    for t in T:
        s=t[4].upper().replace(' ','')
        for k,pat in [('QH',r'^Q-?H$'),('QEFF',r'^Q-?EFF'),('QP',r'^Q-?P$'),('QNPSH',r'^Q-?NPSH')]:
            if re.match(pat,s): lab[k]=t
        if s.startswith('P(K') or s=='P(KW)': lab['Paxis']=t
        if s.startswith('NPSH'): lab['Naxis']=t
    ysplit=min([lab[k][1] for k in ('Paxis','Naxis') if k in lab] or [Hh*0.68])
    N=[n for n in num_tokens(T) if n[3][5]>0.6]
    L=[n for n in N if n[0]<0.09*Ww]; R=[n for n in N if n[0]>0.86*Ww and n[3][2]<Ww*0.99 or (n[0]>0.86*Ww and 'm' not in n[3][4])]
    up=lambda n:n[1]<ysplit-4; lo=lambda n:n[1]>ysplit+4
    # ось Q: строка чисел под верхним графиком
    B=[n for n in N if 0.05*Ww<n[0]<0.95*Ww and up(n)]
    if not B: return None
    yb=max(n[1] for n in B); B=[n for n in B if abs(n[1]-yb)<6]
    B2=[n for n in N if 0.05*Ww<n[0]<0.95*Ww and lo(n)]
    if B2: yb2=max(n[1] for n in B2); B2=[n for n in B2 if abs(n[1]-yb2)<6]
    fq=fit_axis([(n[0],n[2]) for n in B]); fq2=fit_axis([(n[0],n[2]) for n in B2]) if len(B2)>=2 else fq
    fH=fit_axis([(n[1],n[2]) for n in L if up(n) and n[1]<yb-3])
    fE=fit_axis([(n[1],n[2]) for n in R if up(n) and n[1]<yb-3])
    fP=fit_axis([(n[1],n[2]) for n in L if lo(n) and (not B2 or n[1]<yb2-3)])
    fN=fit_axis([(n[1],n[2]) for n in R if lo(n) and (not B2 or n[1]<yb2-3)])
    if not fq or not fH: return None
    # маска тёмных линий без текста
    m=dark_mask(img,thr=232,sat_max=18)
    for t in T:
        x0,y0,x1,y1=[int(v) for v in t[:4]]; m[max(0,y0-2):y1+3,max(0,x0-2):x1+3]=0
    xq0=int(round((0-fq[1])/fq[0])); xqmax=max(n[0] for n in B)
    # убрать оси: длинные вертикальные/горизонтальные линии
    colsum=m.sum(0); rowsum=m.sum(1)
    for x in range(Ww):
        if colsum[x]>0.25*Hh: m[:,max(0,x-1):x+2]=0
    for y in range(Hh):
        if rowsum[y]>0.5*Ww: m[max(0,y-1):y+2,:]=0
    out={}
    def val(f,y): return f[0]*y+f[1]
    xq1=int(xqmax)+2; x0=max(0,xq0-1)
    ytop_up=int(min([n[1] for n in L if up(n)]+[ysplit])-6); ybot_up=int(yb-6)
    lo_top=int(ysplit+8); lo_bot=int((yb2 if B2 else Hh)-6)
    def run(y0,y1,region):
        C={x:col_clusters(m,x,max(0,y0),y1) for x in range(x0,min(Ww,xq1+1))}
        tracks=[]; used=set()
        for it in range(3):
            # старт: самый левый столбец с кластером, не занятым имеющимися треками
            seed=None
            for x in range(x0,min(Ww,xq1)):
                cs=[c for c in C.get(x,[]) if all(abs(c-dict(tr).get(x,-99))>3 for tr in tracks)]
                if cs:
                    seed=(x,min(cs) if it==0 else max(cs)); break
            if not seed: break
            tr=track(C,x0,xq1,seed[0],seed[1])
            if tr[-1][0]-tr[0][0]<0.25*(xq1-x0):
                # отбросить короткий обрывок
                for (x,y) in tr: C[x]=[c for c in C.get(x,[]) if abs(c-y)>2]
                continue
            tracks.append(tr)
            for (x,y) in tr: C[x]=[c for c in C.get(x,[]) if abs(c-y)>1.5]
        return tracks
    def near_label(tr,key):
        if key not in lab: return 1e9
        t=lab[key]; cx,cy=(t[0]+t[2])/2,(t[1]+t[3])/2
        return min(abs(px-cx)+abs(py-cy) for px,py in tr[::2])
    tu=run(ytop_up,ybot_up,'up')
    if tu:
        if len(tu)>=2 and 'QH' in lab and 'QEFF' in lab:
            a,b=tu[0],tu[1]
            if near_label(a,'QH')+near_label(b,'QEFF')>near_label(b,'QH')+near_label(a,'QEFF'): a,b=b,a
            pairs=[('QH',a),('QEFF',b)]
        else: pairs=[('QH',tu[0])]
        for k,tr in pairs:
            f=fH if k=='QH' else fE
            if f: out[k]=[(val(fq,px),val(f,py)) for px,py in tr]
    tl=run(lo_top,lo_bot,'lo')
    if tl:
        if len(tl)>=2 and 'QNPSH' in lab:
            a,b=tl[0],tl[1]
            if near_label(a,'QP')+near_label(b,'QNPSH')>near_label(b,'QP')+near_label(a,'QNPSH'): a,b=b,a
            pairs=[('QP',a),('QNPSH',b)]
        elif len(tl)>=2 and 'QP' in lab:
            pairs=[('QP',min(tl,key=lambda tr:near_label(tr,'QP')))]
        else: pairs=[('QP',tl[0])]
        for k,tr in pairs:
            f=fP if k=='QP' else fN
            if f: out[k]=[(val(fq2,px),val(f,py)) for px,py in tr]
    return out
def resamp(pts,n=16,nd=2):
    a=np.array(sorted(pts)); a=a[a[:,0]>=-0.02*a[-1,0]]
    if len(a)<2: return []
    a[:,0]=np.maximum(a[:,0],0)
    qs=np.linspace(a[0,0],a[-1,0],n)
    return [(round(float(q),2),round(float(np.interp(q,a[:,0],a[:,1])),nd)) for q in qs]
