"""Shimge: растровые графики с сайта shimgepump.com (карточки серий, вкладка Performance Curve), 50 Гц.
Трассировка по цвету (оранжевые/бирюзовые кривые), привязка кодов Q-H-кВт по номинальной точке."""
import cv2,numpy as np,re,json,sys
sys.path.insert(0,'.')
from rdig import ocr,col_clusters
from vdig import fit_axis
from aq_dig import ptrack,Track,dedup,cut_kinks
from common import rec,save
P=[ # файл, y0, y1, серия, об/мин, страница, коды
 ('20181212131327_8209.jpg',0,731,'WQK',2850,'submersible-sewage-pumps-wqk',['48-25-7.5','36-22-5.5','30-18-3.7','18-15-2.2','15-12-1.5','9.6-10-0.75']),
 ('performance-curve-72850.jpg',0,400,'WQ',1450,'submersible-sewage-pump-wq-1',['150-20-18.5','180-20-18.5','180-25-22','180-15-15','150-17-15','180-11-11','130-15-11','150-13-11']),
 ('performance-curve-72850.jpg',400,800,'WQ',1450,'submersible-sewage-pump-wq-1',['130-30-22','100-37-22','100-32-18.5','100-30-15','250-18-22','250-15-18.5','400-10-22','350-10-18.5','300-6-11','100-23-11','360-6-11','250-11-15','400-7-15']),
 ('performance-curve-689355.jpg',0,450,'WQD-L',2850,'submersible-sewage-pumps-wq-d',['15-40-5.5','40-30-7.5','40-15-4','43-13-3','50-10-3','42-12-2.2']),
 ('performance-curve-689355.jpg',450,900,'WQD-L',2850,'submersible-sewage-pumps-wq-d',['30-30-5.5','15-30-3','20-27-4','20-22-3','9-22-2.2','25-10-1.5','15-9-1.1','10-10-0.75','6-16-0.75','12-15-1.5']),
 ('performance-curve-689355.jpg',900,1350,'WQD-L',2850,'submersible-sewage-pumps-wq-d',['65-15-5.5','60-10-4','35-7-2.2','70-7-3']),
 ('performance-curve-1-674354.jpg',0,480,'WQD-L',2850,'submersible-sewage-pumps-wq-d',['100-15-7.5','80-20-7.5','65-22-7.5','25-17-2.2']),
 ('performance-curve-1-674354.jpg',480,930,'WQD-L',2850,'submersible-sewage-pumps-wq-d',['25-20-3','15-20-2.2','18-15-1.5','6-12-0.55','15-7-0.75','7-15-1.1','25-7-1.1']),
 ('performance-curve-1-674354.jpg',930,1450,'WQD-X2',2850,'submersible-sewage-pumps-wq-d',['6-16-0.75','15-12-1.1','10-8-0.55','10-11-0.75'])]
def num(s):
    try: return float(s)
    except: return None
def calib(a):
    S=3; T=[(t[0]/S,t[1]/S,t[2]/S,t[3]/S,t[4]) for t in ocr(cv2.resize(a,None,fx=S,fy=S,interpolation=cv2.INTER_CUBIC))]
    nums=[t for t in T if num(t[4]) is not None]
    # строки подписей
    rows={}
    for t in nums:
        k=next((k for k in rows if abs(k-(t[1]+t[3])/2)<5),(t[1]+t[3])/2); rows.setdefault(k,[]).append(t)
    cand=[]
    for y,r in rows.items():
        r=sorted(r,key=lambda t:t[0]); v=[num(t[4]) for t in r]
        if len(r)>=4 and v[0]==0 and v==sorted(v) and len(set(v))==len(v): cand.append((y,r))
    cand.sort()
    # верхние строки (US/Imp gpm) над полем, нижние — м³/ч и л/мин; берём первую строку ниже середины
    low=[c for c in cand if c[0]>a.shape[0]*0.5]
    if not low: return None
    y,r=low[0]; x0=r[0][0]
    kq=fit_axis([((t[0]+t[2])/2,num(t[4])) for t in r])
    # столбцы подписей слева: H — ближайший к полю
    left=[t for t in nums if t[2]<x0+15 and t[1]<y-5]
    cols={}
    for t in left:
        k=next((k for k in cols if abs(k-t[2])<8),t[2]); cols.setdefault(k,[]).append(t)
    kc=max([k for k,v in cols.items() if len(v)>=4]) if any(len(v)>=4 for v in cols.values()) else None
    if kc is None: return None
    kh=fit_axis([((t[1]+t[3])/2,num(t[4])) for t in cols[kc]])
    return kq,kh,x0,y
def masks(a):
    b,g,r=[a[:,:,i].astype(int) for i in range(3)]
    orange=((r>200)&(g>80)&(g<190)&(b<110)).astype(np.uint8)
    teal=((r<110)&(g>130)&(b>130)&(np.abs(g-b)<60)).astype(np.uint8)
    return {'orange':orange,'teal':teal}
def trace(m,Z=1.0):
    m=cv2.dilate(m,np.ones((2,2),np.uint8)); H,W=m.shape; X0,X1,Y0,Y1=2,W-3,2,H-3; tracks=[]
    def covered(x,y):
        for t in tracks:
            bb=np.array(t); k=np.abs(bb[:,0]-x)<3
            if k.any() and np.min(np.abs(bb[k,1]-y))<4: return True
        return False
    for f in np.linspace(0.02,0.95,16):
        xs=int(X0+f*(X1-X0))
        for y in col_clusters(m,xs,Y0,Y1,merge=2):
            if covered(xs,y): continue
            nb=col_clusters(m,xs+4,Y0,Y1,merge=2); nb0=col_clusters(m,xs-4,Y0,Y1,merge=2)
            if not nb or not nb0: continue
            y2=min(nb,key=lambda v:abs(v-y)); y0_=min(nb0,key=lambda v:abs(v-y))
            if abs(y2-y)>8 or abs(y0_-y)>8: continue
            F=ptrack(m,(xs,y),(8,y2-y0_),X0,X1,Y0,Y1,R=3,max_jump=24,alpha=0.3)
            B=ptrack(m,(xs,y),(-8,-(y2-y0_)),X0,X1,Y0,Y1,R=3,max_jump=24,alpha=0.3,sgn=-1)
            t=Track(sorted(B[1:],key=lambda q:q[0])+list(F),[])
            if t[-1][0]-t[0][0]<25: continue
            tracks.append(t)
    return [cut_kinks(t,w=6,ang=45) for t in dedup(tracks)]
recs=[];log=[]
SHARED=[{'43-13-3','50-10-3'},{'100-15-7.5','80-20-7.5','65-22-7.5'}]
for fn,y0,y1,ser,rpm,page,codes in P:
    img=cv2.imread('shimge/img/'+fn)[y0:y1]
    cal=calib(img)
    if not cal: log.append((f'{ser} {fn}:{y0}','калибровка осей не удалась')); continue
    kq,kh,x0,yq=cal
    M=masks(img); curves=[]
    for col,m in M.items():
        m[int(yq)-6:]=0; m[:, :int(x0)+2]=0
        for t in trace(m):
            curves.append((col,sorted((kq[0]*x+kq[1],kh[0]*y+kh[1]) for x,y in t)))
    panel_assign={}; start=len(recs)
    for code in codes:
        q,h,kw=[float(x) for x in code.split('-')]
        devs=[]
        for j,(col,cu) in enumerate(curves):
            a=np.array(cu)
            if a[0,0]-1<=q<=a[-1,0]+1: devs.append((abs(np.interp(q,a[:,0],a[:,1])-h)/h,j))
        devs.sort()
        name=f"{ser}{code}"
        if not devs or devs[0][0]>0.04 or (len(devs)>1 and devs[1][0]<max(1.8*devs[0][0],0.03) and abs(np.interp(q,*np.array(curves[devs[1][1]][1]).T)-np.interp(q,*np.array(curves[devs[0][1]][1]).T))>0.3):
            log.append((name,f'кривая через номинальную точку не определена однозначно ({[(round(x,3),j) for x,j in devs[:2]]})')); continue
        panel_assign.setdefault(devs[0][1],[]).append(code)
        col,cu=curves[devs[0][1]]; qh=[]
        for x,y in cu[::2]:
            x=round(max(0,x),2)
            if not qh or x>qh[-1][0]: qh.append((x,round(y,3)))
        if qh[0][0]<=0.03*qh[-1][0]: qh[0]=(0.0,qh[0][1])
        recs.append(rec("Shimge",ser,name,"Китай",Application='канализационный погружной',Impeller='Unknown',DnOut=0,P2Kw=kw,Rpm=rpm,
            Poles=2 if rpm>2000 else 4,Voltage='50 Гц',NominalQ=q,NominalH=h,QH=qh,
            Document=f"Shimge, сайт изготовителя shimgepump.com, серия {ser}, вкладка Performance Curve (график {fn}, 50 Гц)",
            Url=f'https://www.shimgepump.com/{page}.html',
            Notes=f"Кривая оцифрована с растрового графика сайта (изд. 2018–2019); привязана по номинальной точке обозначения Q-H-кВт (отклонение {devs[0][0]*100:.1f} %)."))
    bad=set()
    for j,cs in panel_assign.items():
        if len(cs)>1 and not any(set(cs)<=s for s in SHARED): bad.update(cs)
    if bad:
        keep=[r for r in recs[start:] if r['Model'][len(ser):] not in bad]
        for c in sorted(bad): log.append((f'{ser}{c}','разным насосам досталась одна линия графика — привязка не подтверждена'))
        recs[start:]=keep
seen=set();out=[]
for r in recs:
    if r['Id'] in seen: continue
    seen.add(r['Id']); out.append(r)
save('out/shimge.json',out); json.dump(log,open('out/shimge_excluded.json','w'),ensure_ascii=False,indent=1)
for l in log: print(l)
