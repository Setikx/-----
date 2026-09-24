"""Aquastrong WQ 50 Гц: оцифровка графиков «Hydraulic Performance Curves» (стр. 119) и таблица (стр. 118–119)
каталога Aquastrong Commercial Pumps (50 Hz)."""
import json,re,numpy as np
from common import rec,save
from aq_dig import LAB,digitize,nominal
URL='https://mipower.co.za/wp-content/uploads/documents/downloads/aquastrong-commercial-pumps.pdf'
DOC='Aquastrong Commercial Pumps (50 Hz), раздел Submersible Sewage Pumps WQ, стр. 118–119 (таблица и Hydraulic Performance Curves)'
# таблица: строки OCR
rows=[]
for fn,xlim in (('aquastrong/ocr61.json',(1550,9999)),('aquastrong/ocr62.json',(0,1550))):
    T=[t for t in json.load(open(fn)) if xlim[0]<=t[0]<xlim[1]]; T.sort(key=lambda t:(t[1]+t[3])/2); groups=[]
    for t in T:
        y=(t[1]+t[3])/2
        if groups and abs(groups[-1][0]-y)<10: groups[-1][1].append(t)
        else: groups.append([y,[t]])
    for y,g in groups:
        g.sort(key=lambda t:t[0]); txt=[t[4].replace('（','(') for t in g]
        if re.match(r'^\d+WQ',txt[0]) and len(txt)>5: rows.append(txt)
TAB={}
for r in rows:
    m=r[0]; rest=r[1:]
    if rest and rest[0] in('380','220'): volt=rest[0]; rest=rest[1:]
    else: volt='220' if 'WQD' in m else '380'
    if not rest or rest[0] not in('1450','2850'): continue
    rpm=int(rest[0]); rest=rest[1:]
    k=next((i for i,s in enumerate(rest) if re.fullmatch(r'\d{2,3}-\d{2,3}',s)),None)
    if k is None: continue
    before=rest[:k]; after=rest[k+1:]
    d=dict(model=m,volt=volt,rpm=rpm)
    if len(before)==5: d.update(qmax=float(before[0]),hmax=float(before[1]))
    try: d['passage']=float(after[0]); d['nw']=float(after[1])
    except: pass
    TAB[m]=d
def key(m): return m.replace('(F)','').replace('WQD','WQ')
recs=[];skipped=[]
BAD=set()
SKIP=['100WQ65-15-5.5','100WQ60-13-4','150WQ100-10-7.5']  # на графике сплетены, однозначно не разделяются
for (ri,ci),labs in LAB.items():
    c,tr,cv,L,M,A=digitize(ri,ci)
    for i,j in A:
        lab=L[j]
        if lab in BAD: skipped.append(lab); continue
        pts=sorted(cv[i]); q=np.array([p[0] for p in pts]); h=np.array([p[1] for p in pts])
        # выборка равномерно по длине дуги (в долях осей), чтобы сохранить крутой конец кривой
        sx=(q-q.min())/max(np.ptp(q),1e-9); sy=(h-h.min())/max(np.ptp(h),1e-9)
        s=np.r_[0,np.cumsum(np.hypot(np.diff(sx),np.diff(sy)))]; ss=np.linspace(0,s[-1],20)
        qq=np.interp(ss,s,q); hh=np.interp(ss,s,h); qh=[]
        for a,b_ in zip(qq,hh):
            a=round(float(a),2)
            if not qh or (a>qh[-1][0] and b_<qh[-1][1]+0.05): qh.append((a,float(b_)))
        if qh[0][0]<=0.03*qh[-1][0]: qh[0]=(0.0,qh[0][1])   # линия начинается от оси H
        qn,hn=nominal(lab); hq_n=float(np.interp(qn,q,h)); dev=100*(hq_n/hn-1)
        rpm=1450 if '4P' in lab else 2850
        base=key(lab)
        variants=[t for t in TAB.values() if key(t['model'])==base] or [dict(model=re.sub(r'\(F\)','',lab),volt='380',rpm=rpm)]
        for t in variants:
            model=t['model'].replace('(4P)','(4P)')
            kw=float(re.search(r'-(\d+(?:\.\d+)?)(?:\(|$)',re.sub(r'\(F\)','',model)).group(1))
            note=(f"Кривая Q–H оцифрована с графика каталога ({'1450' if rpm==1450 else '2850'} об/мин, 50 Гц). "
                  f"Проверка по номиналу из обозначения: при Q={qn:g} м³/ч по кривой H={hq_n:.1f} м (номинал {hn:g} м, {dev:+.0f} %). ")
            if abs(dev)>10: note+="ВНИМАНИЕ: график каталога отличается от номинала в обозначении более чем на 10 %. "
            if 'qmax' in t: note+=f"Таблица: Qmax={t['qmax']:g} м³/ч, Hmax={t['hmax']:g} м. "
            if 'WQD' in model: note+="Однофазное исполнение; кривая общая с трёхфазным (одна линия на графике). "
            recs.append(rec("Aquastrong","WQ",model,"Китай",Application='канализационный погружной',Impeller='Unknown',
                DnOut=int(re.match(r'\d+',model).group(0)),FreePassageMm=t.get('passage',0),P2Kw=kw,Rpm=rpm,Poles=4 if rpm==1450 else 2,
                Voltage=('1~220 В' if t['volt']=='220' else '3~380 В')+' 50 Гц',WeightKg=t.get('nw',0),NominalQ=qn,NominalH=hn,
                QH=qh,Document=DOC,Url=URL,Notes=note.strip()))
save('out/aquastrong.json',recs); json.dump([(m,'кривые на графике каталога сплетены — однозначно не разделяются') for m in SKIP],open('out/aquastrong_excluded.json','w'),ensure_ascii=False)
print( 'в таблице:',len(TAB))

# ---- KBZ (дренажные) и KBS (шламовые), стр. 124–129 ----
import aq_gen as G
TABK={ # модель: (стр., DN, P2 кВт, Hmax, Qmax, проход, масса нетто, серия, назначение)
 'KBZ21.5':(65,50,1.5,22,27,8.5,0),'KBZ22.2':(65,50,2.2,26,27,8.5,0),'KBZ23.7':(65,50,3.7,34,29,8.5,0),
 'KBZ31.5':(65,80,1.5,14.5,40,8.5,0),'KBZ32.2':(65,80,2.2,21,50,8.5,0),'KBZ33.7':(65,80,3.7,29,55,8.5,0),
 'KBZ35.5':(65,80,5.5,32,70,8.5,0),'KBZ43.7':(65,100,3.7,18,90,8.5,0),'KBZ45.5':(65,100,5.5,23,105,8.5,0),
 'KBZ47.5':(66,100,7.5,40,84,11.5,105),'KBZ411':(66,100,11,48.5,86.4,11.5,130),'KBZ415':(66,100,15,56,86.4,11.5,142),
 'KBZ67.5':(66,150,7.5,31,124.8,19.5,106),'KBZ611':(66,150,11,32,147,19.5,133),'KBZ615':(66,150,15,40,156,19.5,145),
 '80KBS44':(67,80,4,14.8,99,30,105),'100KBS46':(67,100,6,16.9,150,30,145),'150KBS49':(67,150,9,21.5,168,30,170)}
AMBIG={'KBZ23.7','KBZ35.5','KBZ32.2','KBZ43.7'}
PAGES={65:'стр. 124–125',66:'стр. 126–127',67:'стр. 128–129'}
import itertools
for pg in (65,66,67):
    c,tr,cv=G.run(pg)
    models=[m for m,v in TABK.items() if v[0]==pg]
    # сопоставление по началу кривой и Qmax (перебор)
    def cost(p,m): v=TABK[m]; return abs(p[0][1]-v[3])/v[3]+abs(p[-1][0]-v[4])/v[4]
    best=min(itertools.permutations(range(len(cv)),min(len(cv),len(models))),
             key=lambda P:sum(cost(cv[i],models[j]) for j,i in enumerate(P)) if len(cv)>=len(models) else 0) if len(cv)>=len(models) else None
    if best is None:
        best=min(itertools.permutations(models,len(cv)),key=lambda P:sum(cost(cv[i],m) for i,m in enumerate(P)))
        pairs=[(i,m) for i,m in enumerate(best)]
    else: pairs=[(i,models[j]) for j,i in enumerate(best)]
    for i,m in pairs:
        if m in AMBIG: skipped.append(m); continue
        v=TABK[m]; p=sorted(cv[i]); q=np.array([a for a,_ in p]); h=np.array([b for _,b in p])
        sx=(q-q.min())/max(np.ptp(q),1e-9); sy=(h-h.min())/max(np.ptp(h),1e-9)
        s=np.r_[0,np.cumsum(np.hypot(np.diff(sx),np.diff(sy)))]; ss=np.linspace(0,s[-1],18); qh=[]
        for a,b_ in zip(np.interp(ss,s,q),np.interp(ss,s,h)):
            a=round(float(a),2)
            if not qh or (a>qh[-1][0] and b_<qh[-1][1]+0.05): qh.append((a,float(b_)))
        kbs='KBS' in m
        note=(f"Кривая Q–H оцифрована с графика каталога (50 Гц); на графике кривая начинается с Q≈{qh[0][0]:.0f} м³/ч. "
              f"Таблица: Hmax={v[3]:g} м, Qmax={v[4]:g} м³/ч; по графику H({qh[0][0]:.0f})={qh[0][1]:.1f} м, конец кривой Q={qh[-1][0]:.0f} м³/ч. ")
        if kbs: note+="Шламовый насос с агитатором, колесо из хромистого чугуна; 4-полюсный двигатель (по коду обозначения). "
        else: note+="Частота вращения в каталоге не указана. "
        recs.append(rec("Aquastrong","KBS" if kbs else "KBZ",m,"Китай",
            Application='шламовый погружной' if kbs else 'дренажный погружной (грязевой)',Impeller='Open' if kbs else 'Unknown',
            DnOut=v[1],FreePassageMm=v[5],P2Kw=v[2],Rpm=0 if not kbs else 1450,Poles=0 if not kbs else 4,Voltage='3~380 В 50 Гц',
            WeightKg=v[6],QH=qh,Document=f"Aquastrong Commercial Pumps (50 Hz), {'Submersible Slurry Pumps' if kbs else 'Submersible Dewatering Pumps'}, {PAGES[pg]}",
            Url=URL,Notes=note.strip()))
json.dump([(m,'кривые на графике каталога сплетены/касаются — однозначно не разделяются') for m in SKIP+sorted(AMBIG)],open('out/aquastrong_excluded.json','w'),ensure_ascii=False)
save('out/aquastrong.json',recs)
print('KBZ/KBS добавлены; исключены:',sorted(set(skipped)))
