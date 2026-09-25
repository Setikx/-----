# ESPA (Испания): дренажные и канализационные погружные насосы — таблицы Q–H
# из каталога «Catálogo EDE 2026» (ESPA, 05.2026), раздел «Evacuación | Drenaje».
import pymupdf as fitz, re, json
from common import rec, save
PDF='p3/espa/ede2026.pdf'
URL='https://www.espa.com/download/docs/7645/cata-logo-ede-2026-esp.pdf'
PAGES=[75,76,77,78,79,80,82,84,86,88,91,92,94,95,97]
def num(s):
    s=s.replace('.','').replace(',','.') if re.fullmatch(r'\d{1,3}(\.\d{3})+',s) else s.replace(',','.')
    try: return float(s)
    except: return None
def rows_of(page,tol=2.5):
    R=[]
    for w in sorted(page.get_text('words'),key=lambda w:(w[1],w[0])):
        if R and abs(R[-1][0]-w[1])<tol: R[-1][1].append(w)
        else: R.append([w[1],[w]])
    for r in R: r[1].sort(key=lambda w:w[0])
    return R
d=fitz.open(PDF); recs=[]; log=[]
for pi in PAGES:
    pg=d[pi]; R=rows_of(pg); txt=pg.get_text(); pno=pi+1
    series=R[0][1][0][4] if R[0][1][0][4] not in ('Tabla',) else None
    title=' '.join(l for l in txt.split('\n')[:12]).lower()
    pas=re.search(r'Paso máximo de sólidos\s*Ø\s*(\d+)',txt)
    for k,(yq,wq) in enumerate(R):
        mt=[w for w in wq if w[4] in ('m3/h','m³/h')]
        if not mt: continue
        xm=mt[0][0]
        QC=[((w[0]+w[2])/2,num(w[4])) for w in wq if w[0]>xm and num(w[4]) is not None]
        if len(QC)<3: continue
        x0=QC[0][0]
        # число оборотов — ближайший заголовок «... NNNN rpm» выше таблицы
        rp=[(y,int(re.search(r'(\d{3,4})',' '.join(w[4] for w in ws)).group(1))) for y,ws in R if y<yq and any(w[4]=='rpm' for w in ws)]
        rpm=max(rp)[1] if rp else 0
        if not rpm:
            m=re.search(r'Curvas? de funcionamiento a (\d{3,4}) rpm',txt); rpm=int(m.group(1)) if m else 0
        # колонки двигателя
        hdr=[w for y,ws in R if yq-30<y<yq+18 for w in ws if w[2]<x0-8]
        xI=[w[0] for w in hdr if w[4]=='I']; xP1=[w[0] for w in hdr if w[4]=='P1']
        cols=[]
        for w in hdr:
            xc=(w[0]+w[2])/2
            if w[4] in('1~','3~'):
                if xP1 and (not xI or abs(w[0]-xP1[0])<abs(w[0]-xI[0])-10 or w[0]>xP1[0]-5): cols.append(('P1'+w[4],xc))
            elif w[4]=='[kW]' and abs(w[1]-yq)<10: cols.append(('P2',xc))
            elif w[4]=='[kW]' and not xP1: cols.append(('P2',xc))
            elif w[4]=='[HP]': cols.append(('HP',xc))
            elif w[4] in('paso','Ø') : cols.append(('PASO',xc))
        # для строк 1~/3~ под «P1»: оставляем фазовые метки правее P1
        if xP1: cols=[c for c in cols if not c[0].startswith('P1') or c[1]>xP1[0]-15]
        xname=min([c[1] for c in cols]+[x0]+[x-4 for x in xI])-12
        phases=sorted({c[0][2:] for c in cols if c[0].startswith('P1')})
        yend=min([y for y,ws in R if y>yq+22 and ws[0][4] in('Curva','Curvas','Tabla','Bombas','Modelo')]+[1e9])
        for y,ws in R[k+1:]:
            if y>=yend: break
            if not re.match(r'[A-Z][A-Za-z]+\d*$',ws[0][4]) or ws[0][0]>75: continue
            names=[w for w in ws if w[0]<xname and num(w[4]) is None or w is ws[0] or (len(ws)>1 and w is ws[1] and w[0]<xname and ',' not in w[4])]
            model=' '.join(w[4] for w in names)
            if not re.search(r'\d',model) and model not in('Vigicor','Draincor'): continue
            H={};mot={}
            for w in ws[len(names):]:
                xc=(w[0]+w[2])/2; v=num(w[4])
                if v is None: continue
                if xc>x0-6:
                    j=min(range(len(QC)),key=lambda j:abs(QC[j][0]-xc))
                    if abs(QC[j][0]-xc)<6: H[j]=v
                else:
                    c=min(cols,key=lambda c:abs(c[1]-xc)) if cols else None
                    if c and abs(c[1]-xc)<12 and c[0] not in mot: mot[c[0]]=v
            if len(H)<3: log.append((model,f'стр.{pno}: мало точек')); continue
            qh=sorted((QC[j][1],h) for j,h in H.items())
            if any(b>a+0.05 for (_,a),(_,b) in zip(qh,qh[1:])): log.append((model,f'стр.{pno}: напор растёт — проверить')); continue
            ser=model.split()[0]
            low=title
            imp='Grinder' if ('triturador' in low or ser in('Vigicor','Draincor')) else 'Vortex' if ('vortex' in low or 'vórtex' in low) else 'SingleChannel' if 'monocanal' in low else 'Unknown'
            fp=int(mot.get('PASO',0)) or (int(pas.group(1)) if pas else 0)
            p2=mot.get('P2',0)
            vars_=[(ph,f'{model} {"M" if ph=="1~" else "T"}' if len(phases)>1 else model) for ph in (phases or ['3~'])]
            for ph,mname in vars_:
                p1=mot.get('P1'+ph,0)
                notes=f"Точки таблицы каталога (Q, м³/ч — H, м), стр. {pno}. P2 {p2:g} кВт"+(f", P1 {p1:g} кВт" if p1 else "")+"."
                if p1 and p2 and p1<p2: notes+=" P1 в каталоге меньше P2: P2 — номинальная мощность двигателя (общая для типоразмеров серии), P1 — потребляемая мощность данного исполнения." 
                if len(phases)>1: notes+=" Суффикс M — однофазное исполнение 230 В (M/MA), T — трёхфазное 400 В (обозначения каталога)."
                notes+=f" Частота вращения {rpm} мин⁻¹ по каталогу." if rpm else ""
                recs.append(rec('ESPA',ser,mname,'Испания',Application='канализационный погружной' if ser in('DCM2','DCV2','DCM','DCV','Draincor','Vigicor') else 'дренажный погружной',
                    Impeller=imp,HasCutter=imp=='Grinder',FreePassageMm=fp,P2Kw=p2,P1Kw=p1,Voltage=('1~230 В' if ph=='1~' else '3~400 В')+' 50 Гц',
                    Rpm=rpm,Poles={2900:2,1450:4,950:6}.get(rpm,0),QH=qh,Document=f'ESPA, Catálogo EDE 2026 (05.2026), стр. {pno}',Url=URL,Notes=notes))
seen=set();out=[]
for r in recs:
    if r['Id'] in seen: log.append((r['Model'],'дубликат')); continue
    seen.add(r['Id']); out.append(r)
save('out/espa.json',out); json.dump(log,open('out/espa_excluded.json','w'),ensure_ascii=False,indent=1)
print(log)
for r in out: print(r['Model'],r['P1Kw'],r['P2Kw'],r['Rpm'],r['FreePassageMm'],r['Impeller'],len(r['Curve']['QH']),r['Curve']['QH'][0],r['Curve']['QH'][-1])
