# ETNA (Турция): дренажные и канализационные погружные насосы — таблицы Q–H
# из технического буклета «Sewage & Drainage Pumps» (EN01, 12.2025).
import pymupdf as fitz, re, json
from common import rec, save
PDF='p3/etna/etna_sewage.pdf'
URL='https://www.etna.com.tr/en/uploads/source/TeknikBrosurler/AtiksisuDrenajPompasi_TeknikBrosuru_EN01.pdf'
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
d=fitz.open(PDF); recs=[]; log=[]
for pi in range(len(d)):
    pg=d[pi]; R=rows_of(pg); pno=pi+1; txt=pg.get_text()
    for k,(yq,wq) in enumerate(R):
        mt=[w for w in wq if w[4]=='m3/h']
        if not mt: continue
        xm=mt[0][0]
        QW=[w for w in wq if w[0]>xm and num(w[4]) is not None]
        if len(QW)<3 and k+1<len(R) and R[k+1][0]-yq<6: QW=[w for w in R[k+1][1] if w[0]>xm and num(w[4]) is not None]
        QC=[((w[0]+w[2])/2,num(w[4])) for w in QW]
        if len(QC)<3: continue
        x0=QC[0][0]
        hdr=[w for y,ws in R if yq-25<y<yq+5 for w in ws]
        xV=[(w[0]+w[2])/2 for w in hdr if w[4]=='V']; pw=[(w[4],(w[0]+w[2])/2) for w in hdr if w[4] in('Hp','kW')]
        # строки моделей
        MR=[]
        for y,ws in R[k+1:]:
            if y-yq>90 or any(w[4] in('L/min','lt/min','m3/h') for w in ws): break
            if ws[0][4] in('EFP','ETN') or ws[0][4].startswith(('EFP-','ETN-')): MR.append([y,list(ws)])
            elif MR and y-MR[-1][0]<5 and all(num(w[4]) is not None for w in ws): MR[-1][1]+=ws
        for y,ws in MR:
            ws=[w for w in ws if w[4] not in('Hm','(mwc)','(mSS)')]
            lim=(min(xV)-12) if xV else x0-12
            names=[w for w in ws if w[0]<lim]
            model=re.sub(r'\s+',' ',' '.join(w[4] for w in names)).replace('*','').strip()
            H={};V=0;P=0
            for w in ws[len(names):]:
                v=num(w[4]); xc=(w[0]+w[2])/2
                if v is None: continue
                if xc>x0-12:
                    j=min(range(len(QC)),key=lambda j:abs(QC[j][0]-xc))
                    if abs(QC[j][0]-xc)<11: H[j]=v
                elif xV and abs(xc-xV[0])<15: V=v
                elif pw and abs(xc-pw[0][1])<15: P=v
            if len(H)<3: log.append((model,f'стр.{pno}: мало точек')); continue
            qh=sorted((QC[j][1],h) for j,h in H.items())
            if qh[0][0]>0 and False: pass
            if any(b>a+0.05 for (_,a),(_,b) in zip(qh,qh[1:])): log.append((model,f'стр.{pno}: напор растёт — проверить')); continue
            p2=round(P*0.7457,2) if pw and pw[0][0]=='Hp' else P
            four='-4P' in model
            imp='Grinder' if re.search(r'\dDP\b|DP-|DP$',model.replace(' ','')) else 'Vortex' if re.search(r'DV\b|GF',model) or model.endswith('DV') else 'Unknown'
            ph='1~220 В' if V==220 else '3~380 В' if V==380 else ''
            notes=f"Точки таблицы каталога (Q, м³/ч — H, м), стр. {pno}."
            if pw: notes+=f" Мощность по каталогу {P:g} {'л.с.' if pw[0][0]=='Hp' else 'кВт'}"+(f" (≈{p2:g} кВт)" if pw[0][0]=='Hp' else '')+"."
            else:
                m=re.search(r'(\d+)DP?-[24]P',model.replace(' ',''))
                p2=int(m.group(1))/10; ph='3~380 В'
                notes+=f" Мощность в таблице не указана; P2 {p2:g} кВт принята по обозначению модели (число/10 — совпадает с диапазоном мощностей серии, указанным в каталоге). Питание 3~380 В 50 Гц по каталогу."
            if imp=='Grinder': notes+=" Исполнение DP — с режущим механизмом (grinder)."
            recs.append(rec('ETNA',model.split()[0].split('-')[0] if ' ' in model else model.split('-')[0],model,'Турция',
                Application='канализационный погружной' if imp=='Grinder' or re.search(r'D[TV]?\b|D-',model) else 'дренажный погружной',
                Impeller=imp,HasCutter=imp=='Grinder',P2Kw=p2,Voltage=(ph+' 50 Гц').strip(),Rpm=1450 if four else 2900,Poles=4 if four else 2,QH=qh,
                Document=f'ETNA, Sewage & Drainage Pumps, Technical Brochure EN01 (12.2025), стр. {pno}',Url=URL,Notes=notes))
seen=set();out=[]
for r in recs:
    if r['Id'] in seen: log.append((r['Model'],'дубликат')); continue
    seen.add(r['Id']); out.append(r)
save('out/etna.json',out); json.dump(log,open('out/etna_excluded.json','w'),ensure_ascii=False,indent=1)
print(log)
for r in out: print(r['Model'],r['Voltage'],r['P2Kw'],r['Impeller'],len(r['Curve']['QH']),r['Curve']['QH'][0],r['Curve']['QH'][-1])
