from common import *
G=0.0037854118; FT=0.3048
MAN='https://cdn.shopify.com/s/files/1/0608/6043/2486/files/'
D=[# model, hp, kw, amps, volt, dn, hmax_ft, [(ft,gph)], manual, impeller, series, note
 ('SES050',0.5,0.37,5,'1~115 В 60 Гц',40,25,[(5,3830),(10,3750),(15,3050),(20,2250)],'SES050_manual.pdf','Unknown','SES (дренажный/канализационный)',''),
 ('SES050V',0.5,0.37,5,'1~115 В 60 Гц',40,25,[(5,3830),(10,3750),(15,3050),(20,2250)],'SES050V_manual.pdf','Unknown','SES (дренажный/канализационный)','Вертикальный поплавок.'),
 ('SES050P',0.5,0.37,5,'1~115 В 60 Гц',40,25,[(5,3450),(10,3200),(15,2850),(20,2260)],'SES050P_manual.pdf','Unknown','SES (дренажный/канализационный)','Корпус нерж. сталь/термопласт.'),
 ('SES075',0.75,0.55,7,'1~115 В 60 Гц',40,30,[(5,4890),(10,4360),(15,4000),(20,3450)],'SES075_manual.pdf','Unknown','SES (дренажный/канализационный)',''),
 ('SES075V',0.75,0.55,7,'1~115 В 60 Гц',40,30,[(5,4890),(10,4360),(15,4000),(20,3450)],'SES075V_manual.pdf','Unknown','SES (дренажный/канализационный)','Вертикальный поплавок.'),
 ('SES075P',0.75,0.55,7,'1~115 В 60 Гц',40,30,[(5,4200),(10,4100),(15,3990),(20,3580)],'SES075P_manual.pdf','Unknown','SES (дренажный/канализационный)','В инструкции при 20 ft напечатано «35800» — принято 3580 GPH (опечатка).'),
 ('SWG075A',1.0,0.75,0,'1~115 В 60 Гц',50,56,[(5,5238),(10,4213),(20,3127),(30,2310)],'SWG075CA_manual.pdf','Unknown','SWG','Max. head 56 ft — по описанию товара на aquastrong.co.'),
 ('SWG075CA',1.0,0.75,0,'1~115 В 60 Гц',50,46,[(5,3962),(10,3147),(20,2385),(30,1695)],'SWG075CA_manual.pdf','Grinder','SWG (с режущим механизмом)','Max. head 46 ft — по описанию товара.'),
]
recs=[]
for m,hp,kw,a,v,dn,hmax,pts,man,imp,ser,note in D:
    qh=[(0.0,hmax*FT)]+sorted(((g*G,f*FT) for f,g in pts))
    recs.append(rec("Aquastrong",ser,m,"Китай",Application='дренажный/канализационный погружной (бытовой)',Impeller=imp,HasCutter=imp=='Grinder',
        DnOut=dn,P2Kw=kw,Rpm=3450,Poles=2,Voltage=v,QH=qh,Document=f"Aquastrong, инструкция {man} (таблица PERFORMANCE: GPH @ ft)",Url=MAN+man,
        Notes=(f"Насос рынка США, 60 Гц (при 50 Гц характеристика ниже: Q×0,83, H×0,69). Мощность {hp} HP. Пересчёт GPH→м³/ч и ft→м; точка Q=0 — Max.Head по паспорту. "+(f"Iном {a} А. " if a else '')+note).strip()))
recs.append(rec("Aquastrong","SEP","SEP100CA","Китай",Application='канализационный погружной (бытовой)',Impeller='Grinder',HasCutter=True,DnOut=50,P2Kw=0.75,Rpm=3450,Poles=2,
    Voltage='1~220 В 60 Гц',QH=[(q*4200*G,40*FT*(1-q*q)) for q in [0,0.2,0.4,0.6,0.8,0.9,1.0]],Quality='CatalogNominal',
    Document="Aquastrong, инструкция SEP100CA_manual.pdf (Max.Head 40 ft, Max.Flow 4200 GPH)",Url=MAN+'SEP100CA_manual.pdf',
    Notes="Насос рынка США, 60 Гц. В каталоге только Hmax=40 ft и Qmax=4200 GPH; кривая аппроксимирована параболой H=Hmax·(1−(Q/Qmax)²). 1 HP, 4,1 А."))
save('out/aquastrong.json',recs)
