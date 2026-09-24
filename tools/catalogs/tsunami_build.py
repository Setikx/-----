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
EXC=[];recs=[];cnt=collections.Counter()
CH=json.load(open('tsunami/tsunami_charts.json'))
for f,d in D.items():
    s=re.search(r'pages/_fek_([a-z-]+)_',f).group(1); p=d['props']
    series,imp,imptxt,app=SER[s]
    model=re.sub(r'^Tsunami\s+','',d['name'].split(' — ')[0]).strip()
    ch=CH.get(f)
    if not ch: cnt['нет графика']+=1; EXC.append((model,'на странице нет графика')); continue
    P=ch['lines'][0]['points']
    if len(P)<=3: cnt['схема из 3 точек (не заводская кривая)']+=1; EXC.append((model,'на сайте схема из 3 точек, не заводская кривая')); continue
    P=sorted(P,key=lambda z:z['q'])
    qh=[(z['q'],z['h']) for z in P]
    qe=[(z['q'],z['eff']) for z in P if 'eff' in z]; qp=[(z['q'],z['kw']) for z in P if 'kw' in z]
    qn=v(p.get('Номинальная производительность')) or v(p.get('Производительность')); hn=v(p.get('Номинальный напор')) or v(p.get('Напор'))
    kw=v(p.get('Номинальная мощность')) or v(p.get('Мощность')); rpm=int(v(p.get('Скорость')))
    poles=int(v(p.get('Полюсов'))) or ((2 if rpm>2000 else 4 if rpm>1200 else 6 if rpm>900 else 8 if rpm>650 else 10) if rpm else 0)
    dn=int(v(p.get('Выходной диаметр')) or v(p.get('Диаметр выхода')))
    note=f"Рабочее колесо: {imptxt}. Кривая Q–H — точки интерактивного графика на странице модели tsunami-pump.ru («кривые оцифрованы с заводских характеристик»). Номинальная точка: Q={qn:g} м³/ч, H={hn:g} м."
    if qe: note+=" QEta — КПД насоса, QP — мощность на валу (проверено: P=ρgQH/η)."
    if p.get('Рабочее колесо'): note+=f" Диаметр рабочего колеса: {p['Рабочее колесо']}."
    if qh[0][0]>0: note+=" Сайт приводит кривую только в рабочем диапазоне (без Q=0)."
    url='https://tsunami-pump.ru'+ch['lines'][0].get('url','')
    cnt['ok']+=1
    recs.append(rec("Tsunami",series,model,"Китай (бренд РФ)",Application=app,Impeller=imp,HasCutter=imp=='Cutter',DnOut=dn,
        FreePassageMm=v(p.get('Свободный проход')),P2Kw=kw,Rpm=rpm,Poles=poles,Voltage='3~'+str(int(v(p.get('Вольтаж')) or 380))+' В',
        WeightKg=v(p.get('Вес')),ImpellerDmm=v(p.get('Рабочее колесо')),NominalQ=qn,NominalH=hn,QH=qh,QEta=qe,QP=qp,
        Document=f"Сайт производителя tsunami-pump.ru, карточка модели, вкладка «Графики производительности», серия {series}",Url=url,Notes=note))
seen=set();out=[]
for r in sorted(recs,key=lambda r:(r['Series'],r['Model'])):
    if r['Model'] in seen: continue
    seen.add(r['Model']); out.append(r)
save('out/tsunami.json',out); print(cnt, collections.Counter(r['Series'] for r in out))

json.dump(sorted(set(map(tuple,EXC))),open('out/tsunami_excluded.json','w'),ensure_ascii=False,indent=1)
