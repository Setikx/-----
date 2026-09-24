import json,re,numpy as np
import vandjord as V
from common import *
C=json.load(open('vj_curves.json'))
def rs(pts,n=16,nd=2):
    a=np.array(sorted(pts)); a=a[a[:,0]>=-0.02*max(1,a[-1,0])]; a[:,0]=np.maximum(a[:,0],0)
    if a[0,0]<0.015*a[-1,0]: a[0,0]=0
    qs=np.linspace(a[0,0],a[-1,0],n); return [(round(float(q),2),round(float(np.interp(q,a[:,0],a[:,1])),nd)) for q in qs]
recs=[];miss=[]
for name,(pn,res) in C.items():
    if 'QH' not in res or len(res['QH'])<20: miss.append(name); continue
    el=V.EL.get(name) or V.EL.get(name+'(T)') or next((v for k,v in V.EL.items() if k.startswith(name)),None)
    s=' '.join(el['raw']) if el else ''
    m=re.search(r'([13])\s*[хx×]\s*(\d{3})',s)
    volt=(f"{m.group(1)}~{m.group(2)} В") if m else ('1~220 В' if '.1.502' in name else '3~380 В')
    nums=[num(z) for z in (el['raw'][1:] if el else []) if num(z) is not None and not re.search(r'[хx×]',z)]
    p1n=p2n=0;poles=0;rpm=0;inom=0
    if len(nums)>=5: p1n,p2n,poles,rpm,inom=nums[0],nums[1],int(nums[2]),int(nums[3]),nums[4]
    mm=re.match(r'^(SG|VSV|VSL)\.(\d+)\.(?:(\d+)\.)?(\d+)L?\.?(A\.)?(\d)\.',name)
    ser=mm.group(1) if mm else name.split('.')[0]
    dn=int(mm.group(2)) if mm else 0
    if not poles and mm: poles=int(mm.group(6))
    if not rpm: rpm=RPM.get(poles,0)
    fp=0
    for k,(pp,row) in V.SOL.items():
        if name.startswith(k) and len(row)>1 and num(row[1]) is not None: fp=num(row[1]); break
    if ser=='VSV': fp=float(mm.group(3)) if mm and mm.group(3) else fp
    imp={'SG':('Grinder','с режущим механизмом (измельчитель)'),'VSV':('Vortex','свободновихревое'),'VSL':('MultiChannel' if '.75.' not in name or 'поколения' else 'SingleChannel','двухканальное')}[ser]
    if re.match(r'^VSL\.\d+\.75\.',name): imp=('SingleChannel','одноканальное (VSL 2-го поколения)')
    qh=rs(res['QH']); qp=[]
    hh=[v for _,v in qh]
    if any(b>a+0.03*hh[0] for a,b in zip(hh,hh[1:])): miss.append(name+' (немонотонная — перепутаны кривые)'); continue
    note=f"Рабочее колесо: {imp[1]}. Кривая Q–H оцифрована с графика технического каталога VANDJORD 2026 (стр. {pn})."
    if res.get('P1') and p1n and p2n:
        r_=p2n/p1n; qp=[(q,round(v*r_,3)) for q,v in rs(res['P1'],12,3)]
        note+=f" QP — пересчёт кривой P1 каталога в P2 по номинальному отношению P2/P1={r_:.2f} (приближённо)."
    if res.get('E'):
        e=rs(res['E'],12,1); emax=max(v for _,v in e)
        note+=f" Максимальный КПД агрегата (Eta 1, по P1) ≈ {emax:.0f} %."
    if inom: note+=f" Iном = {inom:g} А; P1 = {p1n:g} кВт."
    if qh[0][0]>0.05*qh[-1][0]: note+=" Начальный участок кривой у Q=0 на графике не распознан."
    recs.append(rec("Vandjord",ser,name,"Россия (производство Китай)",Impeller=imp[0],HasCutter=ser=='SG',DnOut=dn,FreePassageMm=fp,
        P2Kw=p2n,P1Kw=p1n,Rpm=rpm,Poles=poles,Voltage=volt,QH=qh,QP=qp,
        Document=f"VANDJORD «Технический каталог: насосы и насосные установки для дренажа и канализации», 2026 (зеркало c-o-k.ru), стр. {pn}",Url=V.URL,Notes=note))
print('missing QH',len(miss),miss[:20])
save('out/vandjord.json',recs)
import collections;print(collections.Counter(r['Series'] for r in recs))
