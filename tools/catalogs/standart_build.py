"""Standart Pompa, серия C (dalgıç atık su): векторные графики «Çalışma Alanları» (H и P по кодам колёс) + таблицы."""
import pymupdf,re,json,numpy as np
from vdig import fit_axis
from common import rec,save
URL='https://www.standartpompa.com/tr/images/pdf/sp_urun_katalog.pdf'
d=pymupdf.open('standart/sp_urun_katalog.pdf')
def num(s):
    try: return float(s.replace(',','.'))
    except: return None
def bez(it,n=12):
    a,c1,c2,b=it[1],it[2],it[3],it[4]
    return [(((1-t)**3)*a.x+3*((1-t)**2)*t*c1.x+3*(1-t)*t*t*c2.x+t**3*b.x,((1-t)**3)*a.y+3*((1-t)**2)*t*c1.y+3*(1-t)*t*t*c2.y+t**3*b.y) for t in np.linspace(0,1,n)]
def path_pts(g):
    pts=[]
    for it in g['items']:
        if it[0]=='c': q=bez(it)
        elif it[0]=='l': q=[(it[1].x,it[1].y),(it[2].x,it[2].y)]
        else: continue
        pts+=q if not pts else q[1:]
    return pts
IMP={'B':('SingleChannel','ширококанальное (B)'),'F':('Open','открытое (F)'),'Vx':('Vortex','вихревое (Vx)'),'D':('MultiChannel','закрытое многоканальное (D)'),'K':('Cutter','с режущим механизмом')}
recs=[];log=[]
for pi in (117,118,119):
    p=d[pi]; W=p.get_text('words'); G=[g for g in p.get_drawings() if g['type']=='s' and any(it[0]=='c' for it in g['items']) and abs((g.get('width') or 0)-1.0)<0.05]
    heads=[w for w in W if w[4]=='d/dak']
    for hw in heads:
        rpm=int(num([w for w in W if abs(w[1]-hw[1])<2 and w[2]<=hw[0]+1 and num(w[4])][-1][4]))
        # строка Q под графиком H: ближайшая ниже заголовка строка чисел с «Q»
        qlab=min([w for w in W if w[4]=='Q' and w[1]>hw[1] and abs(w[0]-hw[0])<60],key=lambda w:w[1])
        row=sorted([w for w in W if num(w[4]) is not None and abs(w[1]-qlab[1])<3 and w[0]<qlab[0] and qlab[0]-w[0]<220],key=lambda w:w[0])
        x0=row[0][0]
        kq=fit_axis([((w[0]+w[2])/2,num(w[4])) for w in row])
        hl=[w for w in W if num(w[4]) is not None and x0-20<w[0]<x0-2 and hw[1]-25<w[1]<qlab[1]-3]
        kh=fit_axis([((w[1]+w[3])/2,num(w[4])) for w in hl])
        tt=[w for w in W if w[4]=='Çark' and w[1]>qlab[1] and -10<w[0]-x0<40]
        if not tt: log.append((f'стр.{pi} x={x0:.0f}','таблица колёс не найдена')); continue
        tab=min(tt,key=lambda w:w[1])
        pl=[w for w in W if num(w[4]) is not None and x0-20<w[0]<x0-2 and qlab[1]+3<w[1]<tab[1]-3]
        kp=fit_axis([((w[1]+w[3])/2,num(w[4])) for w in pl])
        # таблица
        rows={}
        for w in W:
            if tab[1]+5<w[1]<tab[1]+70 and x0-10<w[0]<x0+180:
                k=next((k for k in rows if abs(k-w[1])<2.5),w[1]); rows.setdefault(k,[]).append(w)
        T={}
        for y,ws in rows.items():
            ws=sorted(ws,key=lambda w:w[0]); t=[w[4] for w in ws]
            if re.fullmatch(r'\d{3}\.\d',t[0]) and len(t)>=6:
                T[t[0]]=dict(model=t[1]+' '+t[2],vanes=num(t[3]),passage=num(t[4]),hp=num(t[5]))
        codes=[w for w in W if re.fullmatch(r'\d{3}\.\d',w[4]) and hw[1]-20<w[1]<tab[1]-2 and x0<w[0]<qlab[0]+60]
        ok=kq and kh and kp and T
        if not ok: log.append((f'стр.{pi} {hw}','не разобрана калибровка/таблица')); continue
        cur={'H':{},'P':{}}
        for g in G:
            r=g['rect']
            if not (abs(r.x0-x0-2)<6 and hw[1]-25<r.y0 and r.y1<tab[1]): continue
            pts=path_pts(g); kind='H' if r.y1<qlab[1] else 'P'
            ex,ey=max(pts,key=lambda q:q[0])
            cand=[c for c in codes if (c[1]<qlab[1])==(kind=='H') and -4<c[0]-ex<25 and abs((c[1]+c[3])/2-ey)<14]
            if not cand: continue
            c=min(cand,key=lambda c:abs((c[1]+c[3])/2-ey)+0.3*abs(c[0]-ex))
            ky=kh if kind=='H' else kp
            cur[kind].setdefault(c[4],[]).append(sorted((kq[0]*x+kq[1],ky[0]*y+ky[1]) for x,y in pts))
        for code,info in T.items():
            H=cur['H'].get(code); P=cur['P'].get(code)
            if not H or len(H)>1: log.append((f"{info['model']} / {code}",'кривая Q–H не найдена или неоднозначна')); continue
            H=H[0]; P=P[0] if P and len(P)==1 else []
            qh=[];[qh.append((round(max(0,a),2),round(b,3))) for a,b in H[::2] if not qh or a>qh[-1][0]+1e-6]
            qp=[];[qp.append((round(max(0,a),2),round(b*0.7457,3))) for a,b in P[::2] if not qp or a>qp[-1][0]+1e-6]
            m=re.match(r'C\s*(\d+)-(\d+)(\w+)',info['model']); typ=m.group(3) if m else ''
            imp,imptxt=IMP.get(typ,('Unknown',typ))
            pol={1450:4,2900:2}.get(rpm,0)
            recs.append(rec("Standart Pompa","C",f"{info['model']} ({code})","Турция",Application='канализационный погружной',Impeller=imp,HasCutter=imp=='Cutter',
                DnOut=int(m.group(1)) if m else 0,FreePassageMm=info['passage'] or 0,P2Kw=round(info['hp']*0.7457,2),Rpm=rpm,Poles=pol,Voltage='3~400 В 50 Гц',
                QH=qh,QP=qp,Document=f"Standart Pompa, общий каталог продукции 2024 (sp_urun_katalog), серия C «Dalgıç atık su pompaları», стр. {pi} «Çalışma Alanları»",Url=URL,
                Notes=f"Рабочее колесо № {code}: {imptxt}, лопастей {info['vanes']:g}. Мотор {info['hp']:g} HP (P2 пересчитана в кВт ×0,7457). Кривые Q–H и P оцифрованы с векторного графика (кривые Безье каталога); QP — мощность, HP пересчитаны в кВт."))
seen=set();out=[]
for r in recs:
    if r['Id'] in seen: continue
    seen.add(r['Id']); out.append(r)
save('out/standart.json',out); json.dump(log,open('out/standart_excluded.json','w'),ensure_ascii=False,indent=1)
print(log)
