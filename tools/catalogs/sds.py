import pymupdf,re,numpy as np,json
from vdig import *
from fancy import grp
from common import *
F='aikon/sds_14102024.pdf'; URL='https://www.cnprussia.ru/upload/iblock/c77/94isdom43gn8arq83sn48eauch0a387j/%D0%9A%D0%B0%D1%82%D0%B0%D0%BB%D0%BE%D0%B3_SDS_14102024.pdf'
d=pymupdf.open(F)
is_grid=lambda g: g['type']=='s' and max(g.get('color') or (1,1,1))<0.8 and (g.get('color') or (1,1,1))[0]<0.8
is_red=lambda g: g['type']=='s' and (g.get('color') or (0,0,0))[0]>0.8 and (g.get('color') or (0,0,0))[1]<0.3
charts={}
for pn in range(16,24):
    p=d[pn-1]; W=p.get_text('words')
    titles=[w for w in W if re.fullmatch(r'SDS\d+(\.\d+)?',w[4]) and (w[3]-w[1])>12]
    titles.sort(key=lambda w:w[1])
    for k,t in enumerate(titles):
        y0=t[1]-45; y1=(titles[k+1][1]-45) if k+1<len(titles) else p.rect.height-20
        clip=pymupdf.Rect(20,y0,p.rect.width-10,y1)
        gb=grid_bbox(p,clip,is_grid)
        ws=[w for w in W if clip.contains(pymupdf.Rect(w[:4]))]
        nums=[((w[0]+w[2])/2,(w[1]+w[3])/2,num(w[4])) for w in ws if num(w[4]) is not None and w[4]!=t[4]]
        left=[n for n in nums if n[0]<gb.x0-3 and gb.y0-5<n[1]<gb.y1+5]
        xs=sorted(set(round(n[0]/12) for n in left))
        cols={}
        for n in left: cols.setdefault(round(n[0]/12),[]).append(n)
        cx=sorted(cols,key=lambda c:-np.mean([n[0] for n in cols[c]]))  # от сетки влево: H, P1, η
        fH=fit_axis([(n[1],n[2]) for n in cols[cx[0]]]) if cx else None
        fP=fit_axis([(n[1],n[2]) for n in cols[cx[1]]]) if len(cx)>1 else None
        fE=fit_axis([(n[1],n[2]) for n in cols[cx[2]]]) if len(cx)>2 else None
        bot=[n for n in nums if gb.y1+2<n[1]<gb.y1+22]
        fq=fit_axis([(n[0],n[2]) for n in bot])
        labs={}
        for w in ws:
            if gb.contains(pymupdf.Rect(w[:4])) and w[4] in('H','η','Ƞ','P1'): labs['H' if w[4]=='H' else 'P1' if w[4]=='P1' else 'E']=((w[0]+w[2])/2,(w[1]+w[3])/2)
        ch=[c for c in merge_chains(chain(polylines(p,gb,is_red))) if c[-1][0]-c[0][0]>0.3*gb.width]
        res={}
        dec=[i for i,c in enumerate(ch) if np.polyfit([q[0] for q in c],[q[1] for q in c],1)[0]>0]
        for k2,(lx,ly) in sorted(labs.items(),key=lambda z:z[0]!='H'):
            if not ch: break
            cand=range(len(ch)) if k2!='H' or not dec else dec
            j=min(cand,key=lambda i:min(abs(px-lx)+abs(py-ly) for px,py in ch[i]))
            f={'H':fH,'P1':fP,'E':fE}[k2]
            res[k2]=[(fq[0]*x+fq[1], f[0]*y+f[1]) for x,y in sorted(ch[j])] if f and fq else None
        charts[t[4]]=(pn,res,[len(cols[c]) for c in cx])
for k,(pn,res,nc) in charts.items():
    print(k,pn,nc,{a:(len(b) if b else None, b and (round(b[0][0],2),round(b[0][1],2),round(b[-1][0],2),round(b[-1][1],2))) for a,b in res.items()})
json.dump({k:v[:2] for k,v in charts.items()},open('sds_curves.json','w'))
# ---- записи
def nrm(s): return re.sub(r'\s+','',s)
t15=' '.join(d[14].get_text().split())
el=re.findall(r'(SDS\s?M?F?\s?\d+\.?\d*)\s+([\d,]+)\s+(220|400)\s+([\d,]+)',t15)
t14=' '.join(d[13].get_text().split())
fp={nrm(a):num(b) for a,b in re.findall(r'(SDS\s?M?F?\s?\d+\.\d+|SDS\s?\d{3})\s+([\d,]+)',t14)}
t26=' '.join(d[25].get_text().split())
wt={nrm(a):(int(b),num(c)) for a,b,c in re.findall(r'(SDS\s?M?F?\s?\d+\.?\d*)\s+(\d{2,3})\s+\d+\s+\d+x\d+x\d+\s+([\d,]+)',t26)}
t25=' '.join(d[24].get_text().split())
dn25={nrm(a):int(b) for a,b in re.findall(r'(SDS\s?M?F?\s?\d+\.?\d*)\s+(\d{2,3})\s+\d{3}',t25)}
recs=[]
for name,kw,v,cur in el:
    n=nrm(name); hyd='SDS'+re.sub(r'^SDSM?F?','',n)
    # «SDS 67.5» и т.п.
    c=charts.get(hyd)
    if not c: print('no chart',n,hyd); continue
    pn,res,_=c
    if not res.get('H'): print('noH',n); continue
    def rs(pts,nn=16,nd=2):
        a=np.array(sorted(pts)); a[:,0]=np.maximum(a[:,0],0); qs=np.linspace(a[0,0],a[-1,0],nn)
        return [(round(float(q),2),round(float(np.interp(q,a[:,0],a[:,1])),nd)) for q in qs]
    qh=rs(res['H']); qe=rs(res['E'],12,1) if res.get('E') else []
    one=v=='220'
    dnv=wt.get(n,(dn25.get(n,0),0))[0] or dn25.get(n,0); w=wt.get(n,(0,0))[1]
    note=("Рабочее колесо полуоткрытое (износостойкий высокохромистый сплав), патрубок под шланг. "
          f"Кривые H, η насоса оцифрованы с векторного графика каталога ({hyd}); кривая мощности в каталоге дана как P1 (потребляемая) и в QP не перенесена. "
          f"Iном = {cur} А. "+("M — однофазный 1×220 В. " if 'M' in n[3:] else "")+("F — с поплавковым выключателем." if 'F' in n[3:] else ""))
    recs.append(rec("Aikon","SDS",n,"Китай",Application='дренажный погружной (грязная вода)',Impeller='Open',DnOut=dnv,FreePassageMm=fp.get(n,0) or 0,
        P2Kw=num(kw),Rpm=2900,Poles=2,Voltage='1~220 В' if one else '3~400 В',WeightKg=w or 0,QH=qh,QEta=qe,
        Document=f"Aikon «Погружные дренажные насосы SDS», каталог 14.10.2024, стр. {pn}",Url=URL,Notes=note.strip()))
json.dump(recs,open('out/aikon_sds.json','w'),ensure_ascii=False,indent=1)
print('SDS records',len(recs))
for r in recs[:3]: print(r['Model'],r['DnOut'],r['FreePassageMm'],r['WeightKg'],r['P2Kw'],r['Voltage'])
