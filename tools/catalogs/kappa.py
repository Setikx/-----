import pymupdf,re,numpy as np,json,collections
from vdig import *
from common import *
from fancy import grp
d=pymupdf.open('Kappa_2024.pdf')
URL='https://www.drenopompe.it/wp-content/uploads/2024/02/Kappa_2024.pdf'
# (стр., индекс графика сверху вниз) -> {подпись: модель}
MAP0={(8,0):{'N040':'K040.2.50 N','K075':'K075.2.50 N','N075':'K075.2.50 N'},(8,1):{'H':'K120.2.50 H','N':'K150.2.50 N'},(8,2):{'N':'K220.2.80 N','H':'K220.2.80 H'},
     (9,0):{'N':'K420.2.80 N','C':'K420.2.80 C'},(9,1):{'SH':'K560.2.80 SH','H':'K560.2.80 H','N':'K560.2.100 N','C':'K560.2.100 C'},(9,2):{'N':'K920.2.100 N','C':'K920.2.100 C'}}
def is_curve(g):
    c=g.get('color')
    return g['type']=='s' and c is not None and not (abs(c[0]-0.14)<0.02 and abs(c[1]-0.12)<0.02)
MAP=MAP0
recs=[]
for pn in (8,9):
    p=d[pn-1]; W=p.get_text('words')
    revs=sorted([w for w in W if w[4]=='Rev.'],key=lambda w:w[1])
    for ci,rv in enumerate(revs):
        top=rv[1]-5; bot=(revs[ci+1][1]-20) if ci+1<len(revs) else 800
        region=pymupdf.Rect(250,top,440,bot)
        ws=[w for w in W if region.contains(pymupdf.Rect(w[:4]))]
        nums=[((w[0]+w[2])/2,(w[1]+w[3])/2,num(w[4])) for w in ws if num(w[4]) is not None and w[4]!='0' or w[4]=='0']
        nums=[n for n in nums if n[2] is not None]
        left=[n for n in nums if n[0]<275]
        rl=[]
        for n in sorted([n for n in nums if n[0]>270],key=lambda n:n[1]):
            if rl and abs(rl[-1][-1][1]-n[1])<3: rl[-1].append(n)
            else: rl.append([n])
        brows=sorted([r for r in rl if len(r)>=3],key=lambda r:r[0][1])
        mrow=brows[-1]  # нижняя строка — м³/ч
        ybot=brows[0][0][1]
        fq=fit_axis([(n[0],n[2]) for n in mrow]); fH=fit_axis([(n[1],n[2]) for n in left if n[1]<ybot-2])
        plot=pymupdf.Rect(270,top+5,440,ybot-4)
        ch=[c for c in merge_chains(chain(polylines(p,plot,is_curve))) if c[-1][0]-c[0][0]>20 and abs(c[-1][1]-c[0][1])>5]
        labs=[w for w in ws if w[4] in MAP[(pn,ci)] and plot.x0-5<w[0]]
        used=set()
        for w in labs:
            cx,cy=(w[0]+w[2])/2,(w[1]+w[3])/2
            best=min((min(abs(px-cx)+abs(py-cy) for px,py in c[-8:]),j) for j,c in enumerate(ch) if j not in used) if len(used)<len(ch) else None
            if not best or best[0]>30: print('nolabel',pn,ci,w[4]); continue
            used.add(best[1]); c=sorted(ch[best[1]])
            pts=[(fq[0]*x+fq[1],fH[0]*y+fH[1]) for x,y in c]
            a=np.array(pts); a[:,0]=np.maximum(a[:,0],0)
            if a[0,0]<0.03*a[-1,0]: a[0,0]=0
            qs=np.linspace(a[0,0],a[-1,0],14); qh=[(round(float(q),2),round(float(np.interp(q,a[:,0],a[:,1])),2)) for q in qs]
            model=MAP[(pn,ci)][w[4]]
            recs.append((model,qh,pn))
            print(model,qh[0],qh[-1])
json.dump(recs,open('kappa_curves.json','w'))
