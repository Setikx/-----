import json,re,numpy as np,collections
from common import *
D=json.load(open('tsunami/tsunami_pages.json'))
SER={'wq':('WQ','MultiChannel','двухканальное (по описанию серии)','канализационный погружной'),
     'as-wq':('AS-WQ','Cutter','со спиральным режущим механизмом','канализационный погружной'),
     'afp':('AFP','MultiChannel','—','канализационный погружной (с рубашкой охлаждения)'),
     'b':('B','SingleChannel','одноканальное','канализационный погружной'),
     'tu':('TU','Vortex','свободновихревое (Vortex)','канализационный погружной'),
     'wl':('WL','MultiChannel','незасоряемое','канализационный сухой установки (вертикальный)'),
     'krtk':('KRTK','MultiChannel','многоканальное','канализационный погружной'),
     'krtf':('KRTF','Vortex','свободновихревое','канализационный погружной'),
     'v':('V','Unknown','','канализационный погружной'),
     'zgwq':('ZGWQ','Unknown','','канализационный погружной'),
     'gnwq':('GNWQ','Cutter','режущее (по описанию серии)','канализационный погружной'),
     'zw':('ZW','Unknown','','канализационный самовсасывающий'),
     'dcal':('DCAL','Unknown','','дренажный погружной'),'hd':('HD','Unknown','','дренажный погружной высоконапорный'),
     'ktz':('KTZ','Unknown','','дренажный погружной (грязевой)'),'ktze':('KTZE','Unknown','','дренажный погружной (грязевой)'),
     'qxn':('QXN','Unknown','','дренажный погружной промышленный'),
     'gco':('GCO','Unknown','','консольный центробежный (водоснабжение)'),'gf':('GF','Unknown','','консольно-моноблочный (водоснабжение)'),
     'ghfm':('GHF','Unknown','','центробежный компактный (водоснабжение)'),'gsa':('GSA','Unknown','','консольно-моноблочный (водоснабжение)'),
     'gsm':('GS','Unknown','','консольный центробежный (водоснабжение)'),'gem':('GEM','Unknown','','циркуляционный с ЧП'),
     'cpnsc':('CPNSC','Unknown','','шламовый погружной'),'ktd':('KTD','Unknown','','шламовый погружной с агитатором'),
     'ktde':('KTDE','Unknown','','шламовый погружной с агитатором'),'kts':('KTS','Unknown','','шламовый погружной'),
     'ni-hard':('Ni-Hard','Unknown','','шламовый погружной с агитатором'),'ni-hard-jacketed':('Ni-Hard (с рубашкой)','Unknown','','шламовый погружной с агитатором'),
     'ntz':('NTZ','Unknown','','шламовый погружной'),'qns':('QNS','Unknown','','шламовый погружной'),'zjq':('ZJQ','Unknown','','шламовый погружной'),
     'fdm':('FD(M)','Unknown','','шламовый погружной'),'sh':('SH','Unknown','','дренажный высоконапорный'),'sps':('SPS','Unknown','','дренажный погружной'),
     'sps-ic':('SPS-IC','Unknown','','дренажный погружной'),'fs-m':('FS(M)','Unknown','','дренажный погружной (грязевой)'),'lcm':('LCM','Unknown','','дренажный погружной'),
     'lcp':('LCP','Unknown','','дренажный погружной'),'fsr':('FSR','Unknown','','дренажный погружной'),'poluotkrytoe':('IC','Open','полуоткрытое','дренажный погружной'),
     'geb':('GEB','Unknown','','циркуляционный'),'qdt':('QDT','Unknown','','мешалка'),'qjb':('QJB','Unknown','','мешалка'),'qjb-w':('QJB-W','Unknown','','мешалка')}
def v(s):
    m=re.search(r'[\d]+(?:[.,]\d+)?',s or ''); return float(m.group(0).replace(',','.')) if m else 0
EXC=[];recs=[];cnt=collections.Counter()
CH=json.load(open('tsunami/tsunami_charts.json'))
for f,d in D.items():
    s=f.split('_')[2]; p=d['props']
    series,imp,imptxt,app=SER[s]
    model=re.sub(r'^Tsunami\s+','',d['name'].split(' — ')[0]).strip()
    ch=CH.get(f)
    if not ch: cnt['нет графика']+=1; EXC.append((model,'на странице нет графика')); continue
    P=ch['lines'][0]['points']
    if len(P)<=3: cnt['схема из 3 точек (не заводская кривая)']+=1; EXC.append((model,'на сайте схема из 3 точек, не заводская кривая')); continue
    P=sorted(P,key=lambda z:z['q'])
    qh=[(z['q'],z['h']) for z in P]
    _q=np.array([a for a,_ in qh]);_h=np.array([b for _,b in qh])
    if np.max(np.abs(_h-np.interp(_q,[_q[0],_q[-1]],[_h[0],_h[-1]])))<0.01*max(np.ptp(_h),1e-6):
        cnt['прямая линия']+=1; EXC.append((model,'на сайте прямая линия, не заводская кривая')); continue
    qe=[(z['q'],z['eff']) for z in P if 'eff' in z]; qp=[(z['q'],z['kw']) for z in P if 'kw' in z]
    qn=v(p.get('Номинальная производительность')); hn=v(p.get('Номинальный напор'))
    mm=re.search(r'\d+[A-Z]+(?:\(II\))?(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)-',model)
    if not qn and mm: qn,hn=float(mm.group(1)),float(mm.group(2))
    kw=v(p.get('Номинальная мощность')) or v(p.get('Мощность')); rpm=int(v(p.get('Скорость')))
    poles=int(v(p.get('Полюсов'))) or ((2 if rpm>2000 else 4 if rpm>1200 else 6 if rpm>900 else 8 if rpm>650 else 10) if rpm else 0)
    dn=int(v(p.get('Выходной диаметр')) or v(p.get('Диаметр выхода')))
    note=(f"Рабочее колесо: {imptxt}. " if imptxt else "")+f"Кривая Q–H — точки интерактивного графика на странице модели tsunami-pump.ru («кривые оцифрованы с заводских характеристик»). Номинальная точка: Q={qn:g} м³/ч, H={hn:g} м."
    if not qn: note=note.replace(f" Номинальная точка: Q={qn:g} м³/ч, H={hn:g} м.","")
    elif qh[0][0]<=qn<=qh[-1][0]:
        hq=float(np.interp(qn,[a for a,_ in qh],[b for _,b in qh]))
        if abs(hq/hn-1)>0.15: note+=f" ВНИМАНИЕ: кривая сайта при Q={qn:g} м³/ч даёт H={hq:.1f} м, а номинал {hn:g} м (расхождение {100*(hq/hn-1):+.0f} %)."
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
