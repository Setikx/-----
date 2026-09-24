import pymupdf,re,itertools,numpy as np,glob,os,collections
from kq import *
CATS=[('kq/baum_katalog-kq-wq-menee-7-5-kvt.pdf','https://baumgroup.ru/assets/files/katalog-kq-wq-menee-7-5-kvt.pdf','KQ (Kaiquan) «WQ/EC — погружные канализационные насосы мощностью до 7,5 кВт», рус. изд. 10.2022','WQ/EC','SingleChannel','канальное (одноканальное) с защитой от засорения',False),
      ('kq/baum_katalog-kq-wq-11-22-kvt.pdf','https://baumgroup.ru/assets/files/katalog-kq-wq-11-22-kvt.pdf','KQ (Kaiquan) «WQ — погружные канализационные насосы 11–22 кВт», рус. изд. 10.2022','WQ (11–22 кВт)','Unknown','—',False),
      ('kq/baum_katalog-kq-wq-30-kvt.pdf','https://baumgroup.ru/assets/files/katalog-kq-wq-30-kvt.pdf','KQ (Kaiquan) «WQ — погружные канализационные насосы 30 кВт и выше», рус. изд. 10.2022','WQ (30 кВт и выше)','Unknown','—',False),
      ('kq/baum_katalog-kq-wq-s-rezhuschim-mekhanizmom.pdf','https://baumgroup.ru/assets/files/katalog-kq-wq-s-rezhuschim-mekhanizmom.pdf','KQ (Kaiquan) «WQ/S — погружные канализационные насосы с режущим механизмом», рус. изд. 10.2022','WQ/S','Cutter','двухлопастное с режущими кромками',True),
      ('kq/aqua_WQES-malye-pogruzhnye-kanalizatsionnye-nasosy-s-rezhushchim-mekhanizmom.pdf','https://www.aquanvk.ru/upload/iblock/8f5/3tuejs41c3j03h9s1fl7q7dufl6tjtyb/WQES-malye-pogruzhnye-kanalizatsionnye-nasosy-s-rezhushchim-mekhanizmom.pdf','KQ (Kaiquan) «WQ/ES — малые погружные канализационные насосы с режущим механизмом», рус. изд. 10.2022','WQ/ES','Cutter','с независимым режущим механизмом',True)]
def n_models_gt1(m): return len(m)>1
def interp(c,q):
    a=np.array(c); i=np.argsort(a[:,0]); return float(np.interp(q,a[i,0],a[i,1]))
def assign(models,curves,pairs,spec,labels,chains_pg):
    n=len(models); m=len(curves)
    if m==0: return {}
    if pairs and len(pairs)==n and m>=n:
        best=None
        for perm in itertools.permutations(range(m),n):
            e=sum(abs(interp(curves[perm[i]],q)-h)/max(h,1) for i in range(n) for q,h in pairs[i])
            if best is None or e<best[0]: best=(e,perm)
        if best[0]/max(1,sum(len(x) for x in pairs))<0.08: METHOD[0]='pairs'; return {i:best[1][i] for i in range(n)}
    # по меткам номера кривой
    lab={}
    for (x,y,v) in labels:
        dist=[min(abs(px-x)+abs(py-y) for px,py in c) for c in chains_pg]
        j=int(np.argmin(dist))
        if dist[j]<25 and j<m: lab.setdefault(v,j)
    if all((i+1) in lab for i in range(n)) and len(set(lab[i+1] for i in range(n)))==n:
        METHOD[0]='labels'; return {i:lab[i+1] for i in range(n)}
    # запасной вариант: больше мощность — выше напор
    if m!=n: return None
    METHOD[0]='power'+('-TIE' if len(set(sp.get('p2') for sp in spec[:n]))<n else '')
    mid=np.median([np.mean([p[0] for p in c]) for c in curves])
    order_c=sorted(range(m),key=lambda j:-interp(curves[j],mid))
    order_m=sorted(range(n),key=lambda i:-(spec[i].get('p2') or 0))
    return {order_m[k]:order_c[k] for k in range(n)}
recs=[];log=collections.Counter();errs=[];METHOD=['']
for f,url,doc,series,imp,imptxt,cut in CATS:
    d=pymupdf.open(f)
    for pi,p in enumerate(d):
        Wd=p.rect.width
        for hx0,hx1 in [(0,Wd/2),(Wd/2,Wd)]:
            try: R=parse_half(p,hx0,hx1)
            except Exception as e: print('ERR',f,pi+1,e); continue
            if not R: continue
            models=[m[0] for m in R['models']]
            if 'fx' not in R: print('NOCHART',os.path.basename(f),pi+1,models,R.get('err'),R.get('toks','')[:0]); log['nochart']+=len(models); continue
            fx,fy,fr=R['fx'],R['fy'],R['fr']
            qh=[to_qh(c,fx,fy) for c in R['qh']]
            pr=[[(fx[0]*x+fx[1], fr[0]*y+fr[1]) for x,y in c] for c in R['pw']] if fr else []
            pairs=R['pairs'] if len(R['pairs'])==len(models) else []
            METHOD[0]='';A=assign(models,qh,pairs,R['spec'],R['lab'],R['qh']+R['pw'])
            if 0: print('ASSIGN',METHOD[0],os.path.basename(f)[:22],pi+1,models,[s_.get('p2') for s_ in R['spec']],'labels',R['lab'])
            if not A: print('NOASSIGN',os.path.basename(f),pi+1,models,len(qh)); log['noassign']+=len(models); continue
            # мощность: сопоставляем по уровню
            AP={}
            if pr and len(pr)>=len(models):
                mid=np.median([np.mean([p[0] for p in c]) for c in pr])
                oc=sorted(range(len(pr)),key=lambda j:-interp(pr[j],mid)); om=sorted(range(len(models)),key=lambda i:-(R['spec'][i].get('p2') or 0))
                AP={om[k]:oc[k] for k in range(len(models))}
            for i,mname in enumerate(models):
                c=sorted(qh[A[i]]); s=R['spec'][i] if i<len(R['spec']) else {}
                c=[(max(0,q),h) for q,h in c if q>=-0.02*c[-1][0]]
                if c and c[0][0]<0.01*c[-1][0]: c[0]=(0.0,c[0][1])
                qs=np.linspace(c[0][0],c[-1][0],16); a=np.array(c)
                pts=[(round(float(q),2),round(float(np.interp(q,a[:,0],a[:,1])),2)) for q in qs]
                note=f"Рабочее колесо: {imptxt}. Кривая Q–H оцифрована с векторного графика каталога (оси откалиброваны по подписям делений)."
                qmin=qmax=0
                if METHOD[0].startswith('power') and len(models)>1: note+=" Кривая сопоставлена модели по мощности двигателя (бо́льшая мощность — бо́льший напор; при равной мощности — по порядку строк таблицы)."
                elif METHOD[0]=='labels' and len(models)>1: note+=" Кривая сопоставлена модели по номеру на графике." 
                e=max(abs(interp(c,q)-h)/h for q,h in pairs[i]) if pairs else None
                if pairs and e>0.15:
                    note+=f" Внимание: табличные точки каталога {', '.join(f'{q:g}—{h:g}' for q,h in pairs[i])} (м³/ч — м) не согласуются с графиком (расхождение до {e*100:.0f} %); принята кривая графика."
                elif pairs:
                    errs.append(e)
                    note+=f" Проверка по табличным точкам каталога {', '.join(f'{q:g}—{h:g}' for q,h in pairs[i])} (м³/ч — м): расхождение ≤{e*100:.1f} %."
                    qmin=pairs[i][0][0]; qmax=pairs[i][-1][0]
                    note+=" RangeQmin/RangeQmax — крайние левая и правая точки рабочей зоны по таблице каталога."
                qp=[]
                if i in AP:
                    cp=sorted(pr[AP[i]]); b=np.array(cp)
                    if len(b)>3 and b[:,1].min()>0:
                        axis=' '.join(t[4] for t in text_tokens(p,pymupdf.Rect(hx0,100,hx1,460)))
                        qs2=np.linspace(max(0,b[0,0]),b[-1,0],10)
                        eta=(s.get('eff') or 0)/100
                        isP1=('P1' in axis) or series.startswith('WQ (')
                        if isP1 and eta>0:
                            qp=[(round(float(q),2),round(float(np.interp(q,b[:,0],b[:,1]))*eta,3)) for q in qs2]
                            note+=f" QP: пересчёт кривой P1 каталога в P2 по номинальному КПД двигателя ({eta*100:g} %) — приближённо."
                        elif not isP1:
                            qp=[(round(float(q),2),round(float(np.interp(q,b[:,0],b[:,1])),3)) for q in qs2]
                            note+=" QP: кривая мощности каталога (Pa)."
                rpm=int(s.get('rpm') or 0); poles=2 if rpm>2000 else 4 if rpm>1200 else 6 if rpm>900 else 8 if rpm else 2
                if s.get('fpraw'): note+=f" Проточный канал: {s['fpraw']} мм."
                if s.get('eff'): note+=f" КПД двигателя {s['eff']:g} %, Iном {s.get('cur',0):g} А."
                recs.append(rec("KQ (Kaiquan)",series,mname,"Китай",Impeller=imp,HasCutter=cut,DnOut=R['dn'],FreePassageMm=s.get('fp') or 0,
                    P2Kw=s.get('p2') or 0,Rpm=rpm or RPM[poles],Poles=poles,Voltage='3~380 В',WeightKg=s.get('mass') or 0,
                    RangeQmin=qmin,RangeQmax=qmax,QH=pts,QP=qp,Document=f"{doc}, стр. PDF {pi+1}",Url=url,Notes=note))
                log['ok']+=1
seen=set(); out=[]
for r in recs:
    if r['Model'] in seen: print('dup',r['Model']); continue
    seen.add(r['Model']); out.append(r)
save('out/kq.json',out)
print(log, 'pairs max err: median %.3f max %.3f'%(np.median(errs),max(errs)) if errs else '')
print(collections.Counter(r['Series'] for r in out))
