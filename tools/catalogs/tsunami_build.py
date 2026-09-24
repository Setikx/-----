import json,re,numpy as np,collections
from common import *
R=json.load(open('out/fancy.json'))+json.load(open('out/purity.json'))
Q=np.round(np.arange(0,1.81,0.1),2); prof=[]
for x in R:
    m=re.match(r'^\d+WQ[A-Z]*?(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)-',x['Model']); qh=x['Curve']['QH']
    if not m or len(qh)<3 or qh[0]['Q']!=0: continue
    qn,hn=float(m.group(1)),float(m.group(2)); a=np.array([(p['Q']/qn,p['V']/hn) for p in qh])
    if a[-1,0]<1.5 or abs(np.interp(1.0,a[:,0],a[:,1])-1)>0.08: continue
    prof.append(np.interp(Q,a[:,0],a[:,1],right=np.nan))
P=np.nanmedian(np.array(prof),axis=0); print('typical WQ profile from',len(prof),'curves:',dict(zip(Q.tolist(),np.round(P,3).tolist())))
D=json.load(open('tsunami/tsunami_pages.json'))
SER={'wq':('WQ','MultiChannel','двухканальное (по описанию серии)','канализационный погружной'),
     'as-wq':('AS-WQ','Cutter','со спиральным режущим механизмом','канализационный погружной'),
     'afp':('AFP','MultiChannel','—','канализационный погружной (с рубашкой охлаждения)'),
     'b':('B','SingleChannel','одноканальное','канализационный погружной'),
     'tu':('TU','Vortex','свободновихревое (Vortex)','канализационный погружной'),
     'wl':('WL','MultiChannel','незасоряемое','канализационный сухой установки (вертикальный)'),
     'krtk':('KRTK','SingleChannel','канальное','канализационный погружной'),
     'krtf':('KRTF','Vortex','свободновихревое','канализационный погружной')}
def v(s):
    m=re.search(r'[\d]+(?:[.,]\d+)?',s or ''); return float(m.group(0).replace(',','.')) if m else 0
recs=[];cnt=collections.Counter()
for f,d in D.items():
    s=re.search(r'pages/_fek_([a-z-]+)_',f).group(1); p=d['props']
    series,imp,imptxt,app=SER[s]
    model=re.sub(r'^Tsunami\s+','',d['name'].split(' — ')[0]).strip()
    qn=v(p.get('Номинальная производительность')) or v(p.get('Производительность')); hn=v(p.get('Номинальный напор')) or v(p.get('Напор'))
    qmax=v(p.get('Максимальная производительность')); hmax=v(p.get('Максимальный напор'))
    kw=v(p.get('Номинальная мощность')) or v(p.get('Мощность')); rpm=int(v(p.get('Скорость')))
    poles=int(v(p.get('Полюсов'))) or ({2:2}.get(0) or (2 if rpm>2000 else 4 if rpm>1200 else 6 if rpm>900 else 8 if rpm>650 else 10 if rpm>500 else 0) if rpm else 0)
    if not qn or not hn: cnt['noq']+=1; continue
    if hmax>hn*1.02 and qmax>qn*1.02:
        k=(hmax-hn)/qn**2; qe=qmax; qs=np.linspace(0,qe,13); pts=[(q,hmax-k*q*q) for q in qs]
        how=f"по каталожным Hmax={hmax:g} м, Qmax={qmax:g} м³/ч и номинальной точке: парабола H=Hmax−k·Q² (принято, что Hmax — напор при Q=0)"
        cnt['3pt']+=1
    else:
        ok=~np.isnan(P); pts=[(float(q)*qn,float(h)*hn) for q,h in zip(Q[ok],P[ok]) if q<=1.6]
        how="по единственной номинальной точке с типовой формой кривой серий WQ (медиана оцифрованных кривых Fancy/Purity WQ; H0≈%.2f·Hном). Реальная кривая может заметно отличаться — уточняйте у поставщика"%P[0]
        cnt['1pt']+=1
    dn=int(v(p.get('Выходной диаметр')) or v(p.get('Диаметр выхода')))
    note=f"Рабочее колесо: {imptxt}. Номинальная точка Q={qn:g} м³/ч, H={hn:g} м. Кривая аппроксимирована {how}."
    if p.get('Рабочее колесо'): note+=f" Диаметр рабочего колеса по сайту: {p['Рабочее колесо']}."
    if p.get('Свободный проход'): note+=f" Свободный проход: {p['Свободный проход']}."
    url='https://tsunami-pump.ru'+f.split('pages/')[1].replace('_','/').replace('.html','')
    recs.append(rec("Tsunami",series,model,"Китай (бренд РФ)",Application=app,Impeller=imp,HasCutter=imp=='Cutter',DnOut=dn,
        FreePassageMm=v(p.get('Свободный проход')),P2Kw=kw,Rpm=rpm,Poles=poles,Voltage='3~'+str(int(v(p.get('Вольтаж')) or 380))+' В',
        WeightKg=v(p.get('Вес')),ImpellerDmm=v(p.get('Рабочее колесо')),NominalQ=qn,NominalH=hn,QH=[(round(a,2),round(b,2)) for a,b in pts],
        Document=f"Сайт производителя tsunami-pump.ru, карточка модели (паспортные данные), серия {series}",Url=url,Quality='CatalogNominal',Notes=note))
seen=set();out=[]
for r in sorted(recs,key=lambda r:(r['Series'],r['Model'])):
    if r['Model'] in seen: continue
    seen.add(r['Model']); out.append(r)
save('out/tsunami.json',out); print(cnt, collections.Counter(r['Series'] for r in out))
