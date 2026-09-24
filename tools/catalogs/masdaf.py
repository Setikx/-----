import pymupdf,cv2,numpy as np,re,json,sys
from rdig import *
from vdig import fit_axis
pymupdf.TOOLS.mupdf_display_errors(False)
def load_chart(d,pn):
    p=d[pn-1]; best=None
    for im in p.get_images(full=True):
        x=d.extract_image(im[0])
        if best is None or x['width']*x['height']>best['width']*best['height']: best=x
    img=cv2.imdecode(np.frombuffer(best['image'],np.uint8),cv2.IMREAD_COLOR)
    return img,p.get_text()
def digitize_masdaf(img, dbg=False):
    H,W=img.shape[:2]
    T=ocr(img)
    lab=[]; N=[]
    for t in T:
        s=t[4].replace(' ','')
        m=re.match(r'^(\d{2,3})[gøo0°@]?(?:-?([\d.,]+)K[wW])?$',s)
        if re.match(r'^\d{2,3}[gøo°@]',s) or re.search(r'K[wW]$',s):
            mm=re.match(r'^(\d{2,3})[^\d]',s)
            kw=re.search(r'([\d.,]+)K[wW]',s)
            if mm: lab.append((t,int(mm.group(1)),float(kw.group(1).replace(',','.')) if kw else None))
            continue
        s2=s.strip('-—|')
        if re.fullmatch(r'\d+(\.\d+)?',s2): N.append(((t[0]+t[2])/2,(t[1]+t[3])/2,float(s2),t))
    # ось Q: самая нижняя «строка» чисел, у которой ≥4 числа
    rows={}
    for n in N: rows.setdefault(round(n[1]/12),[]).append(n)
    qrow=max((r for r in rows.values() if len(r)>=4 and len(set(x[2] for x in r))>=4),key=lambda r:np.mean([x[1] for x in r]),default=None)
    if not qrow: return None,'noQ'
    yq=np.mean([x[1] for x in qrow]); fq=fit_axis([(x[0],x[2]) for x in qrow])
    left=[n for n in N if n[0]<0.13*W and n[1]<yq-10]
    ptxt=[t for t in T if re.search(r'P2|GUC|GÜC|KW\)',t[4],re.I) and (t[3]-t[1])>(t[2]-t[0])]
    ysplit=min(t[1] for t in ptxt) if ptxt else None
    if ysplit is None: return None,'nosplit'
    fH=fit_axis([(n[1],n[2]) for n in left if n[1]<ysplit])
    fP=fit_axis([(n[1],n[2]) for n in left if ysplit<n[1]<yq-10])
    if not fq or not fH: return None,'noaxis'
    m=dark_mask(img,thr=140,sat_max=80)
    for t in T:
        x0,y0,x1,y1=[int(v) for v in t[:4]]; m[max(0,y0-2):y1+3,max(0,x0-2):x1+3]=0
    dt=cv2.distanceTransform(m,cv2.DIST_L2,3)
    thick=cv2.dilate((dt>=1.4).astype(np.uint8),np.ones((2,2),np.uint8))
    x_q0=int((0-fq[1])/fq[0])
    C={x:col_clusters(thick,x,0,int(yq-8),merge=3) for x in range(max(0,x_q0-2),W)}
    out={'H':{},'P':{}}
    Hl=[l for l in lab if l[2] is None and l[0][1]<ysplit]; Pl=[l for l in lab if l[2] is not None]
    for (t,dia,_) in Hl:
        cy=(t[1]+t[3])/2; xs=int(t[2])+4
        for dx in range(0,30):
            cs=[c for c in C.get(xs+dx,[]) if abs(c-cy)<22]
            if cs: xs=xs+dx; c=min(cs,key=lambda c:abs(c-cy)); break
        else: continue
        tr=track_lr(C,x_q0,W-1,xs,c,max_gap=80,tol=4)
        out['H'][dia]=[(fq[0]*x+fq[1],fH[0]*y+fH[1]) for x,y in tr]
    if not out['H']:
        Cu={x:[c for c in v if c<ysplit-5] for x,v in C.items()}
        trs=multi_tracks(Cu,max(0,x_q0),W-1,max_gap=60,tol=4)
        trs=[t for t in trs if t[-1][1]>t[0][1]+15]
        if trs:
            tr=max(trs,key=len); out['H'][0]=[(fq[0]*x+fq[1],fH[0]*y+fH[1]) for x,y in tr]
    if fP:
        if not Pl:
            Cl={x:[c for c in v if c>ysplit+5] for x,v in C.items()}
            trs=[t for t in multi_tracks(Cl,max(0,x_q0),W-1,max_gap=60,tol=4) if abs(t[-1][1]-t[0][1])>8]
            if trs:
                tr=max(trs,key=len); out['P'][0]=([(fq[0]*x+fq[1],fP[0]*y+fP[1]) for x,y in tr],None)
        for (t,dia,kw) in Pl:
            cy=(t[1]+t[3])/2; xs=int(t[0])-4
            for dx in range(0,40):
                cs=[c for c in C.get(xs-dx,[]) if abs(c-cy)<14 and c>ysplit]
                if cs: xs=xs-dx; c=min(cs,key=lambda c:abs(c-cy)); break
            else: continue
            tr=track_lr(C,x_q0,W-1,xs,c,max_gap=80,tol=4)
            out['P'][dia]=([(fq[0]*x+fq[1],fP[0]*y+fP[1]) for x,y in tr],kw)
    return out,'ok'
if __name__=='__main__':
    d=pymupdf.open(sys.argv[1])
    for pn in map(int,sys.argv[2:]):
        img,txt=load_chart(d,pn); o,st=digitize_masdaf(img)
        print(pn,st, o and {k:{dd:(len(v) if k=='H' else (len(v[0]),v[1])) for dd,v in o[k].items()} for k in o})
        if o:
            for dd,v in o['H'].items(): print('  H',dd,[(round(a,1),round(b,1)) for a,b in v[::60]])
