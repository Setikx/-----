import pymupdf,re,json,numpy as np
from hydroo_dig import charts,trace,num
from common import rec,save
URL='https://alphadynamic.eu/wp-content/uploads/2023/05/Hydroo_WF-WX-WG-WV_compressed.pdf'
d=pymupdf.open('hydroo/wdroo_ad.pdf')
MODEL=re.compile(r'^(W[FGXV])(\d+)-(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)$')
TAB={}
for pi in range(len(d)):
    for w in d[pi].get_text('words'):
        m=MODEL.match(w[4])
        if not m: continue
        row=sorted([v for v in d[pi].get_text('words') if abs(v[1]-w[1])<2 and v[0]>w[0]],key=lambda v:v[0])
        vals=[num(v[4]) for v in row]
        if len(vals)>=8 and all(x is not None for x in vals[:8]):
            TAB[w[4]]=dict(dn=vals[0],q=vals[1],h=vals[2],n=vals[3],p2=vals[4],v=vals[5],i=vals[6],solid=vals[7],wt=vals[8] if len(vals)>8 else 0,page=pi+1)
print('в таблицах',len(TAB))
recs=[];log=[]
for pi in range(12,26):
    p=d[pi]; t=p.get_text()
    if 'Performance curve' not in t: continue
    ser='WG' if 'Grinder' in t else 'WF'
    for c in charts(p):
        cv,_=trace(p,c)
        labs=[w for w in c['W'] if re.fullmatch(r'\d+-\d+(\.\d+)?-\d+(\.\d+)?',w[4]) and c['clip'].x0-60<w[0]<c['clip'].x1+80 and c['clip'].y0-10<w[1]<c['clip'].y1+30]
        assign={}
        for w in labs:
            dn,q,h=[float(x) for x in w[4].split('-')]
            devs=[]
            for j,cu in enumerate(cv):
                a=np.array(cu)
                if a[0,0]-0.5<=q<=a[-1,0]+0.5: devs.append((abs(np.interp(q,a[:,0],a[:,1])-h)/h,j))
            devs.sort()
            name=f"{ser}{int(dn)}-{w[4].split('-',1)[1]}"
            if not devs or devs[0][0]>0.06 or (len(devs)>1 and devs[1][0]<max(2*devs[0][0],0.025)):
                log.append((name,f'стр.{pi+1}: кривая по номинальной точке не определена однозначно ({[(round(x,3),j) for x,j in devs[:2]]})')); continue
            assign[name]=(devs[0][1],devs[0][0],(q,h))
        # одна линия — разные номиналы: конфликт
        by={}
        for n,(j,dv,qh) in assign.items(): by.setdefault(j,set()).add(qh)
        for n,(j,dv,qh) in assign.items():
            if len(by[j])>1: log.append((n,f'стр.{pi+1}: на одну линию претендуют разные номиналы')); continue
            T=TAB.get(n)
            if not T: log.append((n,'нет в таблице технических данных')); continue
            a=cv[j]; qhs=[]
            for x,y in a[::3]:
                x=round(max(0,x),2)
                if not qhs or x>qhs[-1][0]: qhs.append((x,round(y,3)))
            rpm=int(T['n']); pol=2 if rpm>2000 else 4 if rpm>1200 else 6 if rpm>900 else 8
            recs.append(rec("Hydroo",ser,n,"Испания",Application='канализационный погружной'+(' с измельчителем' if ser=='WG' else ''),
                Impeller='Grinder' if ser=='WG' else 'MultiChannel',HasCutter=ser=='WG',DnOut=int(T['dn']),FreePassageMm=T['solid'],P2Kw=T['p2'],Rpm=rpm,Poles=pol,
                Voltage=f"3~{int(T['v'])} В 50 Гц",WeightKg=T['wt'],NominalQ=T['q'],NominalH=T['h'],QH=qhs,
                Document=f"Hydroo «WDROO series. Submersible sewage pump WF, WX, WG, WV 50Hz» (изд. 06.2023), стр. {pi+1} Performance curve; техданные стр. {T['page']}",
                Url=URL,Notes=f"{'Двухканальное колесо (WF)' if ser=='WF' else 'Режущий механизм (WG)'}. Кривая оцифрована с растра сводного графика; привязана по номинальной точке обозначения (отклонение {dv*100:.1f} %). Iном {T['i']:g} А."))
seen=set();out=[]
for r in recs:
    if r['Id'] in seen: continue
    seen.add(r['Id']); out.append(r)
save('out/hydroo.json',out); json.dump(log,open('out/hydroo_excluded.json','w'),ensure_ascii=False,indent=1)
print(len(log)); print(log[:15])
