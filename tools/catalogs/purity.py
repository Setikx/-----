import pymupdf,re,numpy as np,json,itertools
from purity_dec import font_offsets, spans
from vdig import *
from common import *
F='purity/PURITY-SEWAGE-PUMP.pdf'; URL='https://www.puritypumps.com/uploads/PURITY-SEWAGE-PUMP.pdf'
d=pymupdf.open(F); off=font_offsets(d)
MRE=re.compile(r'^\d+WQ')
def key(n): return re.sub(r'\(D\)|/\d$|\s','',n).replace('WQD','WQ')
gray=lambda g: g['type']=='s' and g.get('color') and abs(g['color'][0]-g['color'][1])<0.05 and 0.5<g['color'][0]<0.9
blue=lambda g: g['type'] in('s','fs') and g.get('color') and g['color'][2]>0.55 and g['color'][0]<0.2
def rows_of(S,tol=3.5):
    S=sorted(S,key=lambda s:((s[1]+s[3])/2,s[0])); out=[]
    for s in S:
        yc=(s[1]+s[3])/2
        if out and abs(out[-1][0]-yc)<tol: out[-1][1].append(s)
        else: out.append([yc,[s]])
    return [sorted(r,key=lambda s:s[0]) for _,r in out]
# ---- таблицы
SPEC={}
for pn,kind in [(5,'p5'),(9,'p9')]:
    p=d[pn-1]; S=spans(p,off)
    for fr in find_frames(p,gray):
        ss=[s for s in S if fr.x0-5<=s[0]<=fr.x1 and fr.y0-5<=s[1]<=fr.y1+5]
        for r in rows_of(ss):
            t=[s[4] for s in r]
            if not t or not (MRE.match(t[0]) or t[0]=='-'): continue
            if kind=='p5':
                names=[z for z in t if MRE.match(z)]; nums=[num(z) for z in t if num(z) is not None]
                if len(nums)<6 or not names: continue
                hp,kw,q,h,rpm,dn=nums[-6:]
                single=t[0] if MRE.match(t[0]) and len(names)>1 else None
                SPEC[key(names[-1])]=dict(name=names[-1],single=single,kw=kw,q=q,h=h,rpm=rpm,dn=dn,page=pn)
            else:
                nums=[num(z) for z in t[1:] if num(z) is not None]
                if len(nums)<4: continue
                dn,q,h,kw=nums[:4]; rpm=nums[4] if len(nums)>4 else 0
                SPEC[key(t[0])]=dict(name=t[0],single=('(D)' in t[0]),kw=kw,q=q,h=h,rpm=rpm,dn=dn,page=pn)
print('spec',len(SPEC))
# ---- графики
def charts_on(pn, use_ocr=False):
    p=d[pn-1]; S=spans(p,off) if not use_ocr else []
    res=[]
    for fr in find_frames(p,gray):
        clip=pymupdf.Rect(fr.x0-45,fr.y0-25,fr.x1+12,fr.y1+48)
        ch=[c for c in merge_chains(chain(polylines(p,pymupdf.Rect(fr.x0-1,fr.y0-1,fr.x1+1,fr.y1+1),blue))) if c[-1][0]-c[0][0]>0.15*fr.width]
        if not ch: continue
        if use_ocr:
            T=ocr_tokens(p,pymupdf.Rect(fr.x0-40,fr.y0-25,fr.x1+12,fr.y1+48),zoom=4)
        else:
            T=[s[:5] for s in S if clip.contains(pymupdf.Rect(s[:4]))]
        L=[];B=[];labels=[]
        for t in T:
            xc=(t[0]+t[2])/2; yc=(t[1]+t[3])/2; s=t[4].replace(' ','')
            if MRE.match(s): labels.append((t,s)); continue
            v=num(s)
            if v is None: 
                sr=split_run(t) if fr.y1<yc<fr.y1+48 else None
                if sr: B+= [(x,val,yy) for x,yy,val in sr]
                continue
            if xc<fr.x0-1 and fr.y0-10<yc<fr.y1+25: L.append((yc,v,xc))
            elif fr.y1+1<yc<fr.y1+48 and fr.x0-8<xc<fr.x1+8: B.append((xc,v,yc))
        def rowB(B):
            if not B: return []
            y0=min(b[2] for b in B); return [(b[0],b[1]) for b in B if b[2]-y0<5]
        def colL(L):
            if not L: return []
            x1=max(l[2] for l in L); return [(l[0],l[1]) for l in L if x1-l[2]<12]
        fy=fit_axis(colL(L)); fx=fit_axis(rowB(B))
        if (not fy or not fx) and not use_ocr:
            T2=ocr_tokens(p,pymupdf.Rect(fr.x0-40,fr.y0-10,fr.x1+8,fr.y1+48),zoom=4)
            L2=[];B2=[]
            for t in T2:
                xc=(t[0]+t[2])/2; yc=(t[1]+t[3])/2; s=t[4].replace(' ','')
                v=num(s)
                if v is None:
                    sr=split_run(t) if fr.y1<yc<fr.y1+48 else None
                    if sr: B2+= [(x,val,yy) for x,yy,val in sr]
                    continue
                if xc<fr.x0-1 and fr.y0-10<yc<fr.y1+25: L2.append((yc,v,xc))
                elif fr.y1+1<yc<fr.y1+48 and fr.x0-8<xc<fr.x1+8: B2.append((xc,v,yc))
            fy=fy or fit_axis(colL(L2)); fx=fx or fit_axis(rowB(B2))
        if not fy or not fx: res.append((fr,None,labels,ch)); continue
        if not use_ocr and len([l for l in labels if re.search(r'-',l[1])])<len(ch):
            T3=ocr_tokens(p,pymupdf.Rect(fr.x0-5,fr.y0-15,fr.x1+12,fr.y1+5),zoom=4)
            have={l[1] for l in labels}
            for t in T3:
                s_=t[4].replace(' ','')
                if MRE.match(s_) and re.search(r'-\d',s_) and s_ not in have: labels.append((t[:4],s_))
        res.append((fr,(fx,fy),labels,ch))
    return res
def rect_dist(r,pts):
    x0,y0,x1,y1=r[:4]
    return min(max(x0-px,0,px-x1)+max(y0-py,0,py-y1) for px,py in pts)
curves={}
for pn,uo in [(4,False),(5,False),(6,False),(10,False),(11,True)]:
    for fr,ax,labels,ch in charts_on(pn,uo):
        if not ax: print('noaxis',pn,fr,[l[1] for l in labels]); continue
        fx,fy=ax
        CH=[[(fx[0]*x+fx[1],fy[0]*y+fy[1]) for x,y in sorted(c)] for c in ch]
        def nomerr(name,c):
            m=re.match(r'^\d+WQV?(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)-',key(name))
            if not m: return 1.0
            sp=SPEC.get(key(name)) or {}
            qn=sp.get('q') or float(m.group(1)); hn=sp.get('h') or float(m.group(2))
            a=np.array(c)
            if qn>a[:,0].max()*1.03 or qn<a[:,0].min()-0.03*a[:,0].max(): return 1.0
            return abs(float(np.interp(qn,a[:,0],a[:,1]))-hn)/hn
        names=[]
        for t,s_ in labels:
            if re.search(r'-\d',s_) and key(s_) not in [key(n[1]) for n in names]: names.append((t,s_))
        cost=sorted(((min(nomerr(s_,CH[j]),1.0)+0.004*rect_dist(t,ch[j]),i,j) for i,(t,s_) in enumerate(names) for j in range(len(ch))))
        ui=set();uj=set()
        for cst,i,j in cost:
            if i in ui or j in uj: continue
            ui.add(i);uj.add(j)
            curves[key(names[i][1])]=(pn,CH[j],names[i][1])
        miss=[names[i][1] for i in range(len(names)) if i not in ui]
        if miss or len(uj)<len(ch): print('page',pn,'unmatched labels',miss,'curves',len(ch)-len(uj))
print('curves',len(curves))
json.dump({k:v for k,v in curves.items()},open('purity_curves.json','w'))
