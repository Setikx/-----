# Pentax (Италия): дренажные и канализационные погружные насосы — таблицы Q–H из
# General Catalogue 50Hz (изд. 2023, стр. 238–281; постраничные выдержки дистрибьютора).
import pymupdf as fitz, re, json
from common import rec, save
P='p3/'
FILES=[('pentax_DP.pdf','DP-DPV'),('pentax_DH.pdf','DH'),('pentax_DC.pdf','DC'),('pentax_dm.pdf','DM'),
       ('pentax_DTR.pdf','DTR-DTRT'),('pentax_DG.pdf','DG'),('pentax_DX.pdf','DX'),('pentax_DV.pdf','DV')]
BASE='https://pentaxmientrung.net/wp-content/uploads/2024/06/'
DOC='Pentax S.p.A., General Catalogue 50Hz (изд. 2023/24)'
def num(s):
    s=s.replace(',','.')
    try: return float(s)
    except: return None
def rows_of(page,tol=2.5):
    R=[]
    for w in sorted(page.get_text('words'),key=lambda w:(w[1],w[0])):
        if R and abs(R[-1][0]-w[1])<tol: R[-1][1].append(w)
        else: R.append([w[1],[w]])
    for r in R: r[1].sort(key=lambda w:w[0])
    return R
# свойства серий (со страниц «Construction features» того же каталога)
def props(model):
    s=re.match(r'[A-Z]+',model).group(0).rstrip('T') or 'D'
    four=model.endswith('-4')
    n=int(re.search(r' (\d+)',model).group(1))
    if s=='DP': return 'Open','дренажный погружной',(4 if n<=60 else 7)
    if s=='DPV': return 'Vortex','дренажный погружной',15
    if s=='DH': return 'Open','дренажный погружной (высоконапорный)',10
    if s=='DC': return 'Open','канализационный погружной (высоконапорный)',10
    if s=='DM': return 'SingleChannel','канализационный погружной',(60 if four and n<=400 else 90 if four else 50)
    if s=='DTR': return 'Grinder','канализационный погружной с измельчителем',0
    if s=='DG': return 'Vortex','дренажный погружной',(35 if n in (80,100) else 50)
    if s=='DX': return 'Vortex','дренажный погружной',28
    if s=='DV': return 'Vortex','канализационный погружной',(45 if n in (400,550) and not four else 50)
    raise ValueError(model)
recs=[];log=[]
for fn,slug in FILES:
    d=fitz.open(P+fn); poles=2
    for pi in range(3,len(d)):
        pg=d[pi]; txt=pg.get_text(); pno=txt.split('\n')[0].strip()
        m=re.search(r'(\d)\s*Poles',txt)
        if m and 'Construction' in txt: poles=int(m.group(1))
        R=rows_of(pg)
        for ih,(yh,wh) in enumerate(R):
            if not any(w[4]=='(m3/h' for w in wh): continue
            xq=[w for w in wh if w[4]=='Q'][0][0]
            # строки расходов (м³/ч, затем л/мин)
            qrows=[]
            for y,ws in R[ih+1:ih+8]:
                nn=[w for w in ws if w[0]>xq-160 and num(w[4]) is not None]
                if len(nn)>=3 and num(nn[0][4])==0 and all(num(a[4])<num(b[4]) for a,b in zip(nn,nn[1:])): qrows.append((y,nn))
            (yq,qw),(yl,lw)=qrows[:2]
            QC=[((w[0]+w[2])/2,num(w[4])) for w in qw]
            for (xc,q),w in zip(QC,lw): assert abs(num(w[4])*0.06-q)<0.03*q+0.05,(fn,pno,q,w[4])
            x0=QC[0][0]
            hdr=[w for y,ws in R if yh-5<y<yl+25 for w in ws if w[0]<x0-15]
            watt=any(w[4]=='W' for w in hdr)
            if watt:
                cols=[('W',w) for w in hdr if w[4]=='W']+[('A'+w[4],w) for w in hdr if w[4] in('1~','3~') and w[0]>[v for v in hdr if v[4]=='W'][0][0]-5 and w[1]<yl+3]
            else:
                hrow=[w for w in hdr if w[4]=='HP'][0]
                cols=[(('P1_'+w[4]) if w[4] in('1~','3~') else w[4],w) for w in hdr if abs(w[1]-hrow[1])<3 and w[4] in('HP','kW','1~','3~')]
            cols=[(k,(w[0]+w[2])/2) for k,w in cols]
            yH=[w for w in hdr+[w for y,ws in R for w in ws] if w[4]=='(m)' and w[1]>yh][0][1]
            for y,ws in R:
                if y<=yH+3 or y>yH+120: continue
                if not ws or ws[0][0]>80 or not (ws[0][4]=='-' or re.match(r'D[A-Z]*$',ws[0][4])): continue
                t=[w for w in ws]; i=0; names=[]
                while i<len(t) and len(names)<2 and (t[i][4]=='-' or re.match(r'D[A-Z]*$',t[i][4])):
                    if t[i][4]=='-': names.append(None); i+=1; continue
                    nm=t[i][4]+' '+t[i+1][4]; i+=2
                    if i<len(t) and t[i][4] in('(G)','G'): nm+=' (G)'; i+=1
                    names.append(nm)
                rest=t[i:]
                mot={};H={}
                for w in rest:
                    xc=(w[0]+w[2])/2
                    if xc<x0-12:
                        k=min(cols,key=lambda c:abs(c[1]-xc))
                        if abs(k[1]-xc)<14: mot[k[0]]=num(w[4]) or 0
                    else:
                        j=min(range(len(QC)),key=lambda j:abs(QC[j][0]-xc))
                        if abs(QC[j][0]-xc)<11 and num(w[4]) is not None: H[j]=num(w[4])
                if len(H)<3: log.append(((' / '.join(n for n in names if n)),f'стр.{pno}: нет таблицы Q–H')); continue
                qh=sorted((QC[j][1],h) for j,h in H.items())
                if any(b>a+0.05 for (_,a),(_,b) in zip(qh,qh[1:])): log.append((' / '.join(n for n in names if n),f'стр.{pno}: напор растёт — проверить')); continue
                if len(names)==1: names=[None]+names  # только трёхфазная
                for ph,nm in zip(('1~','3~'),names):
                    if not nm: continue
                    imp,app,fp=props(nm)
                    if watt: p1=mot.get('W',0)/1000; p2=0; amp=mot.get('A'+ph,0)
                    else: p1=mot.get('P1_'+ph,0); p2=mot.get('kW',0); amp=0
                    hp=mot.get('HP',0)
                    rpm=1450 if poles==4 else 2900
                    notes=f"Точки таблицы каталога (Q, м³/ч — H, м), стр. {pno}. "
                    notes+=(f"P1 {p1*1000:g} Вт, ток {amp:g} А (P2 в каталоге не указана). " if watt else f"P2 {p2:g} кВт ({hp:g} HP), P1 {p1:g} кВт. ")
                    notes+=f"Двигатель {poles}-полюсный 50 Гц; частота вращения {rpm} об/мин принята по числу полюсов (в каталоге не указана)."
                    if '(G)' in nm: notes+=" «(G)» — исполнение с поплавковым выключателем."
                    if p2 and max(9.81*q/3600*h for q,h in qh)/p2>0.55:
                        notes+=" ВНИМАНИЕ: гидравлическая мощность по таблице Q–H превышает 55 % от P2 таблицы; по графику каталога (max η, кривая P1) фактическая мощность на валу выше указанной P2 — при проверке двигателя ориентироваться на P1."

                    recs.append(rec("Pentax",re.match(r'[A-Z]+',nm).group(0),nm,"Италия",Application=app,Impeller=imp,HasCutter=imp=='Grinder',
                        FreePassageMm=fp,P2Kw=p2,P1Kw=round(p1,3),Voltage=('1~230 В' if ph=='1~' else '3~400 В')+' 50 Гц',Rpm=rpm,Poles=poles,QH=qh,
                        Document=f"{DOC}, стр. {pno}",Url=BASE+fn.replace('pentax_','').replace('dm','DM').replace('DP.pdf','DP-DPV.pdf').replace('DTR.pdf','DTR-DTRT.pdf'),Notes=notes))
seen=set();out=[]
for r in recs:
    if r['Id'] in seen: continue
    seen.add(r['Id']); out.append(r)
save('out/pentax.json',out); json.dump(log,open('out/pentax_excluded.json','w'),ensure_ascii=False,indent=1)
print(log)
for r in out: print(r['Model'],r['P2Kw'],r['P1Kw'],r['Poles'],r['FreePassageMm'],[(p['Q'],p['V']) for p in r['Curve']['QH']][:3],'...',r['Curve']['QH'][-1])
