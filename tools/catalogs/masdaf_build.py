import pymupdf,re,numpy as np,json
from masdaf import load_chart, digitize_masdaf
from common import *
pymupdf.TOOLS.mupdf_display_errors(False)
URL='https://web.archive.org/web/20231002140925/https://masdaf.com/_upload/pdf/TR_ENDURO_TD.pdf'
PASS={(2900,'50-160','D'):10,(2900,'50-160','X'):12,(2900,'50-160','PB'):10,(2900,'50-200','D'):18,(2900,'50-200','PB'):18,(2900,'80-190','D'):32,(2900,'80-250','D'):42,
      (1450,'80-190','D'):64,(1450,'80-250','D'):42,(1450,'80-250','X'):43,(1450,'100-240','D'):50,(1450,'100-240','X'):55,(1450,'100-250','D'):68,(1450,'100-250','X'):65,(1450,'100-315','D'):68,(1450,'150-315','D'):78,(1450,'150-315','X'):70}
IMP={'D':('MultiChannel','двухлопастное (тип D)'),'X':('Vortex','свободновихревое (тип X)'),'PB':('Cutter','с режущими ножами (тип PB)')}
def clean(pts):
    a=sorted(pts); out=[]
    for q,h in a:
        if h<0.3: break
        if out and h>out[-1][1]+0.03*out[0][1]+0.3: break
        out.append((q,h))
    return out
def rs(pts,n=16,nd=2):
    a=np.array(pts); a[:,0]=np.maximum(a[:,0],0)
    if a[0,0]<0.02*a[-1,0]: a[0,0]=0
    qs=np.linspace(a[0,0],a[-1,0],n); return [(round(float(q),2),round(float(np.interp(q,a[:,0],a[:,1])),nd)) for q in qs]
d=pymupdf.open('masdaf/TR_ENDURO_TD.pdf'); recs=[]; log=[]
for pn in range(21,38):
    img,txt=load_chart(d,pn)
    m=re.search(r'ENDURO\s+(\d+-\d+)\s+(D|X|PB)\s*[–-]\s*(\d{4})',txt)
    typ,imp,rpm=m.group(1),m.group(2),int(m.group(3))
    o,st=digitize_masdaf(img)
    if not o: log.append((pn,typ,imp,st)); continue
    H={dia:clean(v) for dia,v in o['H'].items()}
    # дубликаты / порядок: больший диаметр — выше
    dias=sorted(H,reverse=True)
    for i,a in enumerate(dias):
        for b in dias[i+1:]:
            A=np.array(H[a]); B=np.array(H[b])
            if len(A)<5 or len(B)<5: continue
            lo=max(A[0,0],B[0,0]); hi=min(A[-1,0],B[-1,0])
            if hi<=lo: continue
            qs=np.linspace(lo,hi,10); dd=np.interp(qs,A[:,0],A[:,1])-np.interp(qs,B[:,0],B[:,1])
            if np.mean(dd)<0.2: log.append((pn,typ,imp,f'Ø{a} ниже/совпадает с Ø{b} — отброшен Ø{b}')); H[b]=[]
    for dia,pts in H.items():
        if len(pts)<15 or pts[-1][0]-pts[0][0]<5: log.append((pn,typ,imp,f'Ø{dia} короткая')); continue
        P=o['P'].get(dia); kw=P[1] if P else 0
        qp=[]
        if P:
            pp=sorted(p for p in P[0] if p[1]>0)
            if len(pp)>10: qp=rs(pp,12,3)
        qh=rs(pts)
        poles=2 if rpm>2000 else 4
        fp=PASS.get((2900 if rpm>2000 else 1450,typ,imp),0)
        model=f"Enduro {typ} {imp} Ø{dia}"
        note=(f"Рабочее колесо: {IMP[imp][1]}, диаметр {dia} мм (обточка стандартного колеса). Кривые Q–H и P2 оцифрованы с растрового графика "
              f"технического документа (стр. {pn-1}); на графике указано {rpm} об/мин 50 Гц (частота по заголовку листа). ")
        if qh[0][0]>0.05*qh[-1][0]: note+="Начальный участок у Q=0 закрыт подписью диаметра и не оцифрован. "
        note+="Двигатель P2 — по подписи кривой мощности."
        recs.append(rec("MASDAF","Enduro",model,"Турция",Impeller=IMP[imp][0],HasCutter=imp=='PB',DnOut=int(typ.split('-')[0]),FreePassageMm=fp,
            P2Kw=kw,Rpm=rpm,Poles=poles,ImpellerDmm=dia,TrimMin=0.85,QH=qh,QP=qp,
            Document=f"MASDAF (Mas Grup) «Enduro serisi dalgıç kanalizasyon ve atıksu pompaları — Teknik doküman», rev. 03, 06.2018, стр. {pn-1} (архивная копия; актуальная техдокументация на сайте не опубликована)",
            Url=URL,Notes=note.strip()))
print(log)
save('out/masdaf.json',recs)
