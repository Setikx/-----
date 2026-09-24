import json,glob,os,csv,collections,numpy as np
from common import despike
BR=['caprari','dreno','masdaf','tsunami','purity','aikon','aquastrong','vandjord','fancy','kq']
allr=[];log=collections.defaultdict(list);ids=set()
for b in BR:
    R=json.load(open(f'out/{b}.json')); keep=[]
    for r in R:
        if r['Source']['Quality']!='CatalogTable': log[b].append((r['Model'],'нет заводской кривой (только номинал) — исключено')); continue
        qh=[(p['Q'],p['V']) for p in r['Curve']['QH']]
        qh=[(q,h) for q,h in qh if h>=0]
        qh,rm=despike(qh,0.12) if r['Source']['Quality']=='CatalogTable' and ('оцифрован' not in r['Notes']) else (qh,[])
        if rm: r['Notes']+=' Исключены точки-опечатки таблицы: '+', '.join(f'({q:g}; {h:g})' for q,h in rm)+'.'
        qs=[q for q,_ in qh]
        if len(qh)<3 or qs!=sorted(qs) or len(set(qs))!=len(qs): log[b].append((r['Model'],'мало точек/порядок Q')); continue
        h=[x for _,x in qh]
        if any(y>x+0.05*max(h)+0.2 for x,y in zip(h,h[1:])): log[b].append((r['Model'],'немонотонная Q–H')); continue
        r['Curve']['QH']=[{'Q':q,'V':v} for q,v in qh]
        for k in ('QP','QEta','QNpsh'):
            c=[p for p in r['Curve'][k] if p['V']>=0]
            qq=[p['Q'] for p in c]
            if qq!=sorted(qq) or len(set(qq))!=len(qq): c=[]
            r['Curve'][k]=c
        if r['Id'] in ids: log[b].append((r['Model'],'дубль Id')); continue
        ids.add(r['Id']); keep.append(r)
    json.dump(keep,open(f'final/{b}.json','w'),ensure_ascii=False,indent=2)
    allr+=keep
    print(b,len(R),'->',len(keep),log[b][:6])
json.dump(allr,open('final/pumps.catalogs.json','w'),ensure_ascii=False,indent=2)
with open('final/summary.csv','w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f,delimiter=';')
    w.writerow(['Manufacturer','Series','Model','Impeller','DnOut','FreePassageMm','P2Kw','Rpm','Voltage','Qmax_m3h','H0_m','QH_points','QP','QEta','QNpsh','Quality','Document'])
    for r in allr:
        c=r['Curve']; w.writerow([r['Manufacturer'],r['Series'],r['Model'],r['Impeller'],r['DnOut'],r['FreePassageMm'],r['P2Kw'],r['Rpm'],r['Voltage'],
            c['QH'][-1]['Q'],c['QH'][0]['V'] if c['QH'][0]['Q']==0 else '',len(c['QH']),len(c['QP']),len(c['QEta']),len(c['QNpsh']),r['Source']['Quality'],r['Source']['Document']])
log['tsunami']+=[tuple(x) for x in json.load(open('out/tsunami_excluded.json'))]
json.dump({k:v for k,v in log.items()},open('final/excluded.json','w'),ensure_ascii=False,indent=1)
print('TOTAL',len(allr))
