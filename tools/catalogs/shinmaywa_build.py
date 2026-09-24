"""ShinMaywa CN/CN-MT/CNH (каталог дистрибьютора, изд. 03.2021): векторный график 50 Гц, логарифмическая шкала расхода."""
import pymupdf,re,json,numpy as np
from vdig import fit_axis
from common import rec,save
URL='https://chainaris.co.th/sites/5086/files/u/products/Shinmaywa/Sub_CN_CN-MT_CNH_CNL.pdf'
d=pymupdf.open('shinmaywa/CN.pdf'); p=d[4]; W=p.get_text('words')
def num(s):
    try: return float(s)
    except: return None
def bez(it,n=16):
    a,c1,c2,b=it[1],it[2],it[3],it[4]
    return [(((1-t)**3)*a.x+3*((1-t)**2)*t*c1.x+3*(1-t)*t*t*c2.x+t**3*b.x,((1-t)**3)*a.y+3*((1-t)**2)*t*c1.y+3*(1-t)*t*t*c2.y+t**3*b.y) for t in np.linspace(0,1,n)]
# оси нижнего графика 50 Гц (левая половина страницы)
ql=[w for w in W if w[0]<280 and abs(w[1]-362)<2 and num(w[4])]
kq=fit_axis([((w[0]+w[2])/2,np.log10(num(w[4]))) for w in ql])
hl=[w for w in W if w[0]<56 and 200<w[1]<360 and num(w[4]) is not None]
kh=fit_axis([((w[1]+w[3])/2,num(w[4])) for w in hl])
print('оси',kq,kh)
curves=[]
for g in p.get_drawings():
    c=g.get('color'); r=g['rect']
    if g['type']=='s' and c and abs(c[1]-0.58)<0.03 and c[0]<0.05 and r.x1<300 and 200<r.y0 and r.y1<365:
        pts=[]
        for it in g['items']:
            q=bez(it) if it[0]=='c' else [(it[1].x,it[1].y),(it[2].x,it[2].y)]
            pts+=q if not pts else q[1:]
        curves.append(sorted(pts))
circ=[((g['rect'].x0+g['rect'].x1)/2,(g['rect'].y0+g['rect'].y1)/2) for g in p.get_drawings() if g['type']=='fs' and g['rect'].width<6 and g['rect'].x1<300 and 200<g['rect'].y0<365]
left=sorted([c for c in circ if c[1]<340],key=lambda c:-c[1])      # снизу вверх: ①..⑩
bottom=sorted([c for c in circ if c[1]>=340],key=lambda c:c[0])    # слева направо: ⑪..⑮
N={}
for k,c in enumerate(left,1):
    j=min(range(len(curves)),key=lambda j:np.hypot(curves[j][0][0]-c[0],curves[j][0][1]-c[1])); N[k]=(j,np.hypot(curves[j][0][0]-c[0],curves[j][0][1]-c[1]))
for k,c in enumerate(bottom,11):
    j=min(range(len(curves)),key=lambda j:abs(curves[j][-1][0]-c[0])+0.3*abs(curves[j][-1][1]-c[1])); N[k]=(j,abs(curves[j][-1][0]-c[0]))
print({k:(v[0],round(v[1],1)) for k,v in N.items()}, len(set(v[0] for v in N.values())))
leg={}
for w in W:
    m=re.match(r'^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮]$',w[4])
    if m and w[1]>370 and w[0]<300:
        k='①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮'.index(w[4])+1
        t=[v for v in W if abs(v[1]-w[1])<2 and 0<v[0]-w[0]<12]
        leg[k]=t[0][4] if t else None
print(leg)
recs=[]
for k,(j,dist) in N.items():
    name=leg[k]; mm=re.match(r'(CNH?)(\d+)(-MT)?-(\d+(?:\.\d+)?)kW(?:〔(\d)〕)?',name)
    pts=curves[j]; qh=[]
    for x,y in pts[::2]:
        q=round(60*10**(kq[0]*x+kq[1]),2); h=round(kh[0]*y+kh[1],3)
        if not qh or q>qh[-1][0]: qh.append((q,h))
    model=name.replace('〔','[').replace('〕',']')
    kw=float(mm.group(4)); pol=4 if mm.group(1)=='CNH' or kw>=11 else 0
    recs.append(rec("ShinMaywa",mm.group(1)+(mm.group(3) or ''),model,"Япония",Application='канализационный погружной (шламовый)',Impeller='SingleChannel',
        DnOut=int(mm.group(2)),P2Kw=kw,Rpm=0,Poles=0,Voltage='3~ 50 Гц',QH=qh,
        Document="ShinMaywa «Submersible sludge pump CN/CN-MT/CNH・CNL series» (каталог, 03.2021; копия дистрибьютора chainaris.co.th), стр. 5, Performance Curves 50 Hz",
        Url=URL,Notes=f"Канальное колесо (channel impeller){', рабочее колесо № '+mm.group(5) if mm.group(5) else ''}. Кривая № {k} векторного графика 50 Гц; шкала расхода логарифмическая (m³/min → м³/ч). Кривая начинается с минимального расхода графика (без точки Q=0)."))
save('out/shinmaywa.json',recs)
# верхний график (малые насосы), линейная шкала
ql2=[w for w in W if w[0]<280 and abs(w[1]-190)<2 and num(w[4]) is not None]
kq2=fit_axis([((w[0]+w[2])/2,num(w[4])) for w in ql2])
hl2=[w for w in W if w[0]<56 and 60<w[1]<190 and num(w[4]) is not None]
kh2=fit_axis([((w[1]+w[3])/2,num(w[4])) for w in hl2])
C2=[]
for g in p.get_drawings():
    c=g.get('color'); r=g['rect']
    if g['type']=='s' and c and abs(c[1]-0.58)<0.03 and c[0]<0.05 and r.x1<300 and r.y1<185 and r.y0>60:
        pts=[]
        for it in g['items']:
            q=bez(it) if it[0]=='c' else [(it[1].x,it[1].y),(it[2].x,it[2].y)]
            pts+=q if not pts else q[1:]
        C2.append(sorted(pts))
ORDER=['CN651-MT-1.5kW','CN501-MT-0.75kW','CN501T-MT-0.4kW','CN401T-MT-0.25kW']   # сверху вниз по графику (сверено визуально)
C2.sort(key=lambda c:c[0][1])
if len(C2)==4:
  for lab,c in zip(ORDER,C2):
    mm=re.match(r'(CN)(\d+)T?(-MT)-(\d+(?:\.\d+)?)kW',lab)
    qh=[]
    for x,y in c[::2]:
        q=round(60*(kq2[0]*x+kq2[1]),2); h=round(kh2[0]*y+kh2[1],3)
        if not qh or q>qh[-1][0]: qh.append((max(q,0),h))
    recs.append(rec("ShinMaywa","CN-MT",lab,"Япония",Application='канализационный погружной (шламовый)',Impeller='SingleChannel',
        DnOut={'CN401':40,'CN501':50,'CN651':65}[re.match(r'CN\d+',lab).group(0)],P2Kw=float(mm.group(4)),Rpm=0,Poles=2,Voltage='3~ 50 Гц',QH=qh,
        Document="ShinMaywa «Submersible sludge pump CN/CN-MT/CNH・CNL series» (каталог, 03.2021; копия дистрибьютора chainaris.co.th), стр. 5, Performance Curves 50 Hz",
        Url=URL,Notes="Канальное колесо. Верхний график 50 Гц (линейная шкала m³/min → м³/ч); подписи вдоль кривых сопоставлены визуально по порядку линий."))
    print(lab,qh[0],qh[-1])
save('out/shinmaywa.json',recs)
