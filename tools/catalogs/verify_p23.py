import json,collections,re,sys
B=['aquario','speroni','jung','pentax','herborner','kessel','espa','etna']
REQ=["Id","Manufacturer","Series","Model","Country","Application","Impeller","HasCutter","DnOut","FreePassageMm","P2Kw","P1Kw","Rpm","Poles","Voltage","WeightKg","Curve","Source","Notes"]
sample=json.load(open('data/pumps.sample.json')); sample=sample[0] if isinstance(sample,list) else sample
REQ=list(sample.keys()) if isinstance(sample,dict) else REQ
iss=collections.defaultdict(list); tot=0
for b in B:
    R=json.load(open(f'data/catalogs/{b}.json')); tot+=len(R)
    curves=collections.defaultdict(list)
    for r in R:
        m=r['Model']; C=r['Curve']; qh=C['QH']
        miss=[k for k in REQ if k not in r]
        if miss: iss[b].append((m,'нет полей '+str(miss)))
        if r['Source']['Quality']!='CatalogTable': iss[b].append((m,'Quality'))
        if not r['Source']['Document'] or not r['Source']['Url']: iss[b].append((m,'нет Document/Url'))
        if '60' in r['Voltage'] and 'Гц' in r['Voltage'] and '50' not in r['Voltage']: iss[b].append((m,'60 Гц'))
        Q=[p['Q'] for p in qh]; H=[p['V'] for p in qh]
        if len(qh)<3: iss[b].append((m,f'точек {len(qh)}'))
        if Q!=sorted(Q) or len(set(Q))<len(Q): iss[b].append((m,'Q не возрастает'))
        if any(h2>h1+0.05 for h1,h2 in zip(H,H[1:])): iss[b].append((m,'H растёт'))
        if min(H)<0 or max(H)>200: iss[b].append((m,f'H вне диапазона {min(H)}..{max(H)}'))
        if Q[0]>0.35*Q[-1]: iss[b].append((m,f'кривая начинается далеко от нуля Q0={Q[0]} Qmax={Q[-1]}'))
        # мощность: гидравлическая не должна превышать P2 (или P1)
        P=r['P2Kw'] or r['P1Kw']
        if P:
            ph=max(9.81*q/3600*h for q,h in zip(Q,H))
            if ph>0.95*P: iss[b].append((m,f'гидр. мощность {ph:.2f} кВт > P ({P})'))
            if ph<0.03*P and P>0.3: iss[b].append((m,f'гидр. мощность {ph:.3f} кВт ≪ P ({P}) — проверить единицы'))
        if r['P1Kw'] and r['P2Kw'] and r['P1Kw']<r['P2Kw']*0.98: iss[b].append((m,f'P1 {r["P1Kw"]} < P2 {r["P2Kw"]}'))
        if r['Rpm'] and r['Poles'] and abs(r['Rpm']-3000*2/r['Poles'])/(3000*2/r['Poles'])>0.12: iss[b].append((m,f'Rpm {r["Rpm"]} ≠ полюса {r["Poles"]}'))
        for k in ('QP','QEta','QNpsh'):
            c=C[k]
            if c:
                qs=[p['Q'] for p in c]
                if qs!=sorted(qs): iss[b].append((m,k+' Q не возрастает'))
                if c[-1]['Q']>Q[-1]*1.05: iss[b].append((m,k+' длиннее Q–H'))
        if C['QEta'] and max(p['V'] for p in C['QEta'])>95: iss[b].append((m,'η>95'))
        curves[tuple(round(h,2) for h in H)+tuple(round(q,2) for q in Q)].append(m)
    for k,v in curves.items():
        if len(v)>1: iss[b].append(('/'.join(v),'одинаковые кривые'))
print('записей',tot)
for b in B:
    print(f'== {b}: {len(iss[b])} замечаний')
    for x in iss[b]: print('   ',x)
