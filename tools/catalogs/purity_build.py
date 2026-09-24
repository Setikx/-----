import json,re,numpy as np
exec(open('purity.py').read().split('# ---- графики')[0])
from common import *
C=json.load(open('purity_curves.json'))
recs=[];bad=[]
for k,(pn,pts,label) in sorted(C.items()):
    sp=SPEC.get(k) or SPEC.get(k+'/2') or {}
    m=re.match(r'^(\d+)WQ(V)?(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)(QG|A)?',k)
    if not m: print('skip',k); continue
    dn=int(m.group(1)); qn=float(m.group(3)); hn=float(m.group(4)); kw=float(m.group(5)); suf=m.group(6) or ''
    pm=re.search(r'/(\d)$',label); poles=int(pm.group(1)) if pm else 2
    rpm=int(sp.get('rpm') or RPM[poles]); poles={2900:2,1450:4,980:6,960:6}.get(rpm,poles)
    if sp: qn,hn,kw,dn=sp['q'],sp['h'],sp['kw'],int(sp['dn'] or dn)
    a=np.array(sorted(pts)); a=a[a[:,0]>-0.03*a[-1,0]]; a[:,0]=np.maximum(a[:,0],0)
    if a[0,0]<0.02*a[-1,0]: a[0,0]=0
    qs=np.linspace(a[0,0],a[-1,0],16); qh=[(round(float(q),2),round(float(np.interp(q,a[:,0],a[:,1])),2)) for q in qs]
    h_at=float(np.interp(qn,a[:,0],a[:,1])); err=abs(h_at-hn)/hn if qn<=a[-1,0]*1.02 else 9
    if err>0.2: bad.append((k,round(err,2),pn)); continue
    if m.group(2): series,imp,imptxt='WQV','Vortex','свободновихревое'
    elif suf=='QG': series,imp,imptxt='WQ…QG','Cutter','с режущим механизмом'
    elif suf=='A': series,imp,imptxt='WQ…A (новая серия)','MultiChannel','двухлопастное незасоряемое'
    else: series,imp,imptxt='WQ','MultiChannel','двухлопастное незасоряемое'
    model=sp.get('name') or label
    note=(f"Рабочее колесо: {imptxt}. Кривая Q–H оцифрована с векторного графика каталога (стр. {pn}); подпись кривой сопоставлена по близости. "
          f"Номинальная точка: Q={qn:g} м³/ч, H={hn:g} м (по кривой {h_at:.1f} м, расхождение {err*100:.1f} %).")
    if not sp: note+=" Параметры DN, Q, H, P2 — из обозначения модели (в таблице каталога модель не найдена)."
    if sp.get('single'): note+=f" Есть однофазное исполнение{': '+sp['single'] if isinstance(sp['single'],str) else ' (WQD)'}."
    recs.append(rec("Purity",series,model,"Китай",Impeller=imp,HasCutter=imp=='Cutter',DnOut=dn,P2Kw=kw,Rpm=rpm,Poles=poles,
        Voltage='3~380 В',NominalQ=qn,NominalH=hn,QH=qh,Document=f"PURITY «Sewage Pump» каталог 2024.03, стр. PDF {pn}",Url=URL,Notes=note))
print('bad (curve/label mismatch >20%)',bad)
save('out/purity.json',recs)
import collections; print(collections.Counter(r['Series'] for r in recs))
