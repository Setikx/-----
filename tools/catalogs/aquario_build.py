"""Aquario (РФ): интерактивные графики Q–H на карточках aquario.ru (атрибут data-praph, Q в л/мин)."""
import json,re
from common import rec,save
R=json.load(open('p2/aquario.json'))
def fld(b,name):
    m=re.search(re.escape(name)+r'[\s|]+([\d.,x]+)',b); return m.group(1).replace(',','.') if m else None
recs=[];log=[]
for u,v in R.items():
    b=v['body']; slug=u.rstrip('/').split('/')[-1]
    i=b.find('ХАРАКТЕРИСТИКИ'); spec=b[i:i+1500] if i>=0 else ''
    typ=re.search(r'Тип насоса[\s|]+(\w+)',spec); typ=typ.group(1) if typ else ''
    if typ!='Погружной': log.append((slug,f'тип насоса «{typ}» — не погружной дренажный/фекальный')); continue
    d=v['series']
    if len(d)!=1: log.append((slug,'несколько скоростей/нет графика')); continue
    pts=[]
    for pq in d[0].split(';'):
        if ':' not in pq: continue
        a,h=pq.split(':'); 
        try: pts.append((float(a.replace(',','.'))*0.06,float(h.replace(',','.'))))
        except: pass
    if len(pts)<3: log.append((slug,'менее 3 точек')); continue
    k=b.find('Область применения'); desc=b[k:k+3000]
    p1=fld(spec,'Потребляемая мощность'); volt=fld(spec,'Напряжение'); w=(re.search(r'Вес[^0-9]{0,60}?([0-9]+(?:\.[0-9]+)?)\s*\|?\s*кг',spec) or [None,None])[1]
    part=re.search(r'(?:размер|диаметр)[^|]{0,40}?частиц[^|\d]{0,30}(\d+)\s*мм',desc)
    cutter='режущ' in desc.lower(); vortex='вихрев' in desc.lower() or 'vortex' in slug
    imp='Grinder' if cutter else 'Vortex' if vortex else ('Open' if 'открыт' in desc.lower() else 'Unknown')
    model=slug.upper().replace('ECOMPACT','E COMPACT')
    recs.append(rec("Aquario","ADS/GRINDER/VORTEX/SAND".split('/')[0] if slug.startswith('ads') else slug.split('-')[0].upper(),model,"Россия (бренд)",
        Application='дренажный/фекальный погружной (бытовой)',Impeller=imp,HasCutter=cutter,FreePassageMm=float(part.group(1)) if part else 0,
        P1Kw=round(float(p1)/1000,3) if p1 else 0,Voltage=(('1~' if volt and volt.startswith('1x') else '3~')+(volt.split('x')[-1] if volt else '')+' В 50 Гц'),
        WeightKg=float(w) if w else 0,QH=pts,Document=f"Aquario, сайт aquario.ru, карточка {model}, «Гидравлический график»",Url=u,
        Notes="Точки Q–H интерактивного графика на карточке изготовителя (Q в л/мин пересчитан в м³/ч). P2 в карточке не указана; P1 — потребляемая мощность."))
save('out/aquario.json',recs); json.dump(log,open('out/aquario_excluded.json','w'),ensure_ascii=False,indent=1)
print(log)
