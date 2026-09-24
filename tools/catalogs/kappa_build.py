import json
from common import *
C=json.load(open('kappa_curves.json'))
URL='https://www.drenopompe.it/wp-content/uploads/2024/02/Kappa_2024.pdf'
SPEC={'K040.2.50 N':(0.40,50,'1~230 В / 3~400 В',18.6),'K075.2.50 N':(0.75,50,'1~230 В / 3~400 В',20),'K120.2.50 H':(1.2,50,'1~230 В / 3~400 В',19),'K150.2.50 N':(1.5,50,'1~230 В / 3~400 В',19),
      'K220.2.80 N':(2.2,80,'1~230 В / 3~400 В',33.5),'K220.2.80 H':(2.2,80,'1~230 В / 3~400 В',33.5),'K420.2.80 N':(4.2,80,'1~230 В / 3~400 В',37),'K420.2.80 C':(4.2,80,'1~230 В / 3~400 В',37),
      'K560.2.100 N':(5.6,100,'1~230 В / 3~400 В',63),'K560.2.100 C':(5.6,100,'1~230 В / 3~400 В',63),'K920.2.100 N':(9.2,100,'1~230 В / 3~400 В',70),'K920.2.100 C':(9.2,100,'1~230 В / 3~400 В',70)}
recs=[]
for model,qh,pn in C:
    if model not in SPEC: continue
    kw,dn,v,wt=SPEC[model]
    recs.append(rec("Dreno Pompe","Kappa",model,"Италия",Application='дренажный погружной (строительный, «контракторный»)',Impeller='Open',DnOut=dn,FreePassageMm=8,
        P2Kw=kw,Rpm=2900,Poles=2,Voltage=v,WeightKg=wt,QH=[tuple(x) for x in qh],Document=f"Dreno Pompe «KAPPA — contractor pumps», каталог 2024, стр. {pn}",Url=URL,
        Notes="Кривая Q–H оцифрована с векторного графика каталога. Сетчатый фильтр 8×22 мм (проход твёрдых частиц ограничен сеткой). Корпус из алюминиевого сплава, колесо износостойкое. N — средний напор, H — высокий напор, C — высокая подача."))
save('out/dreno_kappa.json',recs)
