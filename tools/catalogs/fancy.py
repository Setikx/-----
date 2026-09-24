import pymupdf,re,glob,os
from common import *
QU={'m³/h','mĨ/h','m3/h','m³/h','м³/ч','m3/h.'}
MODEL=re.compile(r'^[0-9]*[A-Z]{1,6}[0-9][0-9A-Za-z.\-/]*$')
def grp(ws,tol=3.2):
    ws=sorted(ws,key=lambda w:((w[1]+w[3])/2,w[0])); out=[]
    for w in ws:
        yc=(w[1]+w[3])/2
        if out and abs(out[-1][0]-yc)<tol: out[-1][1].append(w)
        else: out.append([yc,[w]])
    return [(y,sorted(r,key=lambda w:w[0])) for y,r in out]
def isnum(s): return num(s) is not None
def parse_pdf(path):
    d=pymupdf.open(path); res=[]
    for pi,p in enumerate(d):
        W=p.rect.width; allw=p.get_text('words')
        halves=[(0,W/2),(W/2,W)] if W>900 else [(0,W)]
        for x0,x1 in halves:
            ws=[w for w in allw if x0<=w[0]<x1]
            rpm=None; qcols=None; lcols=None; spec=None
            for y,r in grp(ws):
                t=[w[4] for w in r]
                for s in t:
                    m=re.search(r'n≈(\d{3,4})',s)
                    if m: rpm=int(m.group(1))
                # header rows
                for i,w in enumerate(r):
                    if w[4] in QU or w[4].lower() in('l/min','gpm') or w[4].startswith('GPM'):
                        rest=[z for z in r[i+1:] if isnum(z[4])]
                        if w[4].startswith('GPM') and len(w[4])>3: rest=[(w[0]+20,w[1],w[2],w[3],w[4][3:])]+rest
                        if len(rest)>=4:
                            vals=[((z[0]+z[2])/2,num(z[4])) for z in rest]
                            if w[4] in QU: qcols=vals
                            elif w[4].lower()=='l/min': lcols=[(x,v*0.06) for x,v in vals]
                            else: gcols=[(x,v*0.2271) for x,v in vals]
                        break
                if 'kw' in [s.lower() for s in t] and 'hp' in [s.lower() for s in t]:
                    spec=[]; mmn=0
                    for w in r:
                        k=w[4].lower()
                        if k=='mm': spec.append(((w[0]+w[2])/2,'dn' if mmn==0 else 'fp')); mmn+=1
                        elif k in('kw','hp','amp.'): spec.append(((w[0]+w[2])/2,k))
                    continue
                r=[w for w in r if not (w[4]=='-' and spec and w[0]<min(x for x,_ in spec)-20)]
                if not r or not MODEL.match(r[0][4]) or not (qcols or lcols): continue
                if r[0][4] in('DN','GPM','MODEL','H','Q'): continue
                Q=qcols or lcols
                lim=(min(x for x,_ in spec)-12) if spec else Q[0][0]-30
                names=[w for w in r if MODEL.match(w[4]) and (w[0]+w[2])/2<lim]
                if not names: continue
                if any(w[4]=='-' and w[0]<names[0][0] for w in r): pass
                qx0=Q[0][0]-9
                sv={}
                for w in r:
                    if w in names or (w[0]+w[2])/2>=qx0 or not spec: continue
                    xc=(w[0]+w[2])/2; k=min(spec,key=lambda s:abs(s[0]-xc))
                    if abs(k[0]-xc)<14: sv[k[1]]=w[4]
                pts=[]
                for w in r:
                    xc=(w[0]+w[2])/2
                    if xc<qx0 or not isnum(w[4]): continue
                    j=min(range(len(Q)),key=lambda j:abs(Q[j][0]-xc))
                    if abs(Q[j][0]-xc)<10: pts.append((round(Q[j][1],2),num(w[4])))
                if len(pts)>=2: res.append(dict(page=pi+1,names=[w[4] for w in names],spec=sv,pts=pts,rpm=rpm,unit='m3/h' if qcols else 'l/min'))
    return res
if __name__=="__main__":
    import sys,json
    for f in sys.argv[1:]:
        R=parse_pdf(f)
        print('##',os.path.basename(f),len(R))
        for r in R[:3]+R[-2:]: print('  ',r)
