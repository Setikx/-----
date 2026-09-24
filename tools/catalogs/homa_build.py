"""HOMA: сборка PumpRecord из каталогов (кривые Q–H и P2 по номерам кривых, таблицы моделей)."""
import re,json,numpy as np,pymupdf,sys
import re as _re
from homa_dig import charts,trace,number,number_ocr,val,Z,assign_by_table,check_ocr,segments
import string
MAN=json.load(open('homa/manual.json'))
from common import rec,save
BASE='https://www.homa-pumpen.de/fileadmin/user_upload/07-Download/Prospekte/'
CATS=[('GB_leaflet_wastewater_treatment_DN80_DN150.pdf',range(16,30),'HOMA «Pumps for wastewater treatment. Submersible sewage pumps MXS, V(X), K(X), DN 80–DN 150»'),
      ('GB_leaflet_pumps_for_waste_water_systems_DN200_DN500.pdf',range(13,22),'HOMA «Pumps for waste water systems. KX series, DN 200–DN 500»')]
MOD=re.compile(r'^[A-Z]{1,4}\d{3,5}-[A-Z]{1,3}\d{2,3}[A-Z]?$')
def f(s):
    try: return float(s.replace(',','.'))
    except: return None
def tables(p):
    W=p.get_text('words'); T={}
    heads=[w for w in W if w[4] in('WET','DRY') and w[0]>300]
    for h in heads:
        kind='wet' if h[4]=='WET' else 'dry'
        nxt=[g[1] for g in heads if g[1]>h[1]+5]; ylim=min(nxt) if nxt else h[1]+200
        ws=sorted([w for w in W if w[0]>270 and h[1]+20<w[1]<ylim],key=lambda w:(w[1]+w[3])/2)
        # строки: кластеры по центру y с допуском 2 pt
        rows=[]
        for w in ws:
            yc=(w[1]+w[3])/2
            if rows and yc-rows[-1]['y']<2.2: rows[-1]['w'].append(w)
            else: rows.append(dict(y=yc,w=[w]))
        out=[]
        for r in rows:
            toks=[]
            for w in sorted(r['w'],key=lambda w:w[0]):
                t=w[4]
                for suf in ('(S)(Ex)','(Ex)','(S)'):
                    if t.endswith(suf) and len(t)>len(suf): toks+=[t[:-len(suf)],suf]; break
                else: toks.append(t)
            # «KX 6678-G156» → «KX6678-G156»
            j=0; tt=[]
            while j<len(toks):
                if j+1<len(toks) and _re.fullmatch(r'[A-Z]{1,4}',toks[j]) and _re.match(r'^\d{3,5}-',toks[j+1]): tt.append(toks[j]+toks[j+1]); j+=2
                else: tt.append(toks[j]); j+=1
            k=next((i for i,t in enumerate(tt) if MOD.match(t)),None)
            if k is None: continue
            nums=[f(t) for t in tt[k+1:] if f(t) is not None]
            if len(nums)<4: nums=[f(t) for t in tt if f(t) is not None and t not in tt[:k]]
            nums=[x for x in nums]
            if len(nums)<3: continue
            out.append(dict(model=tt[k],P1=nums[0],P2=nums[1],I=nums[2],W=nums[3] if len(nums)>3 else 0,ex='Ex' in ''.join(tt)))
        T[kind]=out
    return T
def header(p):
    t=p.get_text()
    rpm=re.search(r'(\d{3,4})\s*rpm',t); pas=re.search(r'(\d{2,3})\s*mm\s*Ø',t); dn=re.search(r'DN\s*(\d{2,3})',t)
    imp='Unknown'; low=t.lower()
    if 'vortex' in low: imp='Vortex'
    elif 'single channel' in low or 'single-channel' in low: imp='SingleChannel'
    elif 'two channel' in low or 'two-channel' in low or 'multi channel' in low or 'multi-channel' in low: imp='MultiChannel'
    title=re.search(r'DN\s*\d+\s*-\s*[A-Z()]+\d*\.\.\.-\d\s*POLE',t)
    return dict(rpm=int(rpm.group(1)) if rpm else 0,passage=float(pas.group(1)) if pas else 0,dn=int(dn.group(1)) if dn else 0,imp=imp,
                title=title.group(0) if title else '',imptxt=next((l for l in t.split('\n') if 'impeller' in l.lower()),''))
def curve_pts(c,t,iend,n=20):
    P=[val(c,x,y) for x,y in t[:iend+1]]; q=np.array([a for a,_ in P]); h=np.array([b for _,b in P])
    sx=(q-q.min())/max(np.ptp(q),1e-9); sy=(h-h.min())/max(np.ptp(h),1e-9)
    s=np.r_[0,np.cumsum(np.hypot(np.diff(sx),np.diff(sy)))]; ss=np.linspace(0,s[-1],n); out=[]
    for a,b in zip(np.interp(ss,s,q),np.interp(ss,s,h)):
        a=round(float(a),2)
        if a<0: a=0.0
        if not out or a>out[-1][0]: out.append((a,round(float(b),3)))
    if out[0][0]<=0.02*out[-1][0]: out[0]=(0.0,out[0][1])
    return out
recs=[];report=[];missing=[]
def main():
  pass
for fn,pages,doc in (CATS if __name__=="__main__" else []):
    d=pymupdf.open('homa/'+fn); date=d.metadata.get('creationDate','')[2:8]
    for i in pages:
        p=d[i]; T=tables(p); hd=header(p); wet=T.get('wet',[]); dry=T.get('dry',[])
        if not wet: report.append((fn,i+1,'нет таблицы')); continue
        N=len(wet); CH={c['kind']:c for c in charts(p)}
        if 'H' not in CH: report.append((fn,i+1,'нет графика H')); continue
        c=CH['H']; tr,dg=trace(p,c)
        tb,why=assign_by_table(c,tr,wet)
        if tb:
            agree,conf=check_ocr(c,tr,dg,tb,N)
            if conf: src={}; how='таблица'; status=f"H: по таблице, но OCR противоречит {conf} — страница отклонена"
            else: src=tb; how='таблица+OCR' if agree else 'таблица'; status=f"H: {len(src)}/{N} (по гидравлике из таблицы; OCR подтвердил {agree})"
        else:
            src={}; how='—'; status=f"H: не разобрано ({why})"
        key=('ww' if 'treatment' in fn else 'kx')+str(i+1)+'H'
        if not src and key in MAN:
            sg=segments(c,tr); L={string.ascii_uppercase[n]:s for n,s in enumerate(sg)}
            src={int(k):L[v] for k,v in MAN[key].items() if v in L}; how='визуально'
            status=f"H: {len(src)}/{N} (визуальная сверка номеров по графику; авто: {why})"
        QH={k:curve_pts(c,tr[s[0]],s[1]) for k,s in src.items()}
        QP={}
        if 'P' in CH:
            cp=CH['P']; trp,dgp=trace(p,cp); tbp,whyp=assign_by_table(cp,trp,wet)
            srcp={}
            if tbp:
                ag,cf=check_ocr(cp,trp,dgp,tbp,N)
                if not cf: srcp=tbp
            kp=key[:-1]+'P'
            if not srcp and kp in MAN:
                sg=segments(cp,trp); L={string.ascii_uppercase[n]:s for n,s in enumerate(sg)}
                srcp={int(k):L[v] for k,v in MAN[kp].items() if v in L}
            for k,s in srcp.items():
                pts=curve_pts(cp,trp[s[0]],s[1]); pmax=max(v for _,v in pts)
                if pmax<=wet[k-1]['P2']*1.08: QP[k]=pts
                else: status+=f"; P2 кривой {k} ({pmax:.1f}) > номинала {wet[k-1]['P2']} — P2 не взята"
            status+=f"; P2: {len(QP)}/{N}"
        report.append((fn,i+1,status))
        for kind,rows in (('wet',wet),('dry',dry)):
            if len(rows)!=N: continue
            for k,r in enumerate(rows,1):
                if k not in QH: missing.append((r['model'],f'стр. {i+1}: номер кривой {k} не распознан однозначно')); continue
                qh=QH[k]; qp=QP.get(k,[])
                if qp:
                    e1,e2=qh[-1][0],qp[-1][0]
                    if abs(e1-e2)/max(e1,e2)>=0.04: missing.append((r['model'],f'стр. {i+1}: конец Q–H ({e1:.0f}) и P2 ({e2:.0f}) не совпадают — привязка не подтверждена')); continue
                elif how not in('таблица+OCR','визуально'): missing.append((r['model'],f'стр. {i+1}: нет кривой P2 для перекрёстной проверки номера кривой')); continue
                poles={2900:2,2850:2,1450:4,1460:4,960:6,980:6,970:6,720:8,730:8,710:8,680:8,700:8}.get(hd['rpm'],0)
                ser=re.match(r'[A-Z]+\d{2}',r['model']).group(0)
                note=(f"{hd['imptxt'].strip()}. Кривая № {k} на странице {i+1} каталога; Q–H{' и P2' if qp else ''} оцифрованы с векторного графика "
                      f"(номер кривой определён по таблице: одна линия на гидравлику, штрихи — пределы моторов; подтверждён {('совпадением концов кривых Q–H и P2' if qp else 'визуально') if how=='визуально' else ('OCR и совпадением концов кривых Q–H и P2' if qp else 'OCR')}). Пунктирный участок каталожной кривой — вне рекомендуемого диапазона. "
                      f"{'Установка сухая (dry installation).' if kind=='dry' else 'Установка погружная (wet well).'} Iном {r['I']:g} А, P1 {r['P1']:g} кВт."
                      +(" Исполнение Ex доступно." if r['ex'] else ""))
                recs.append(rec("HOMA",ser,r['model'],"Германия",Application='канализационный '+('погружной' if kind=='wet' else 'сухой установки'),
                    Impeller=hd['imp'],DnOut=hd['dn'],FreePassageMm=hd['passage'],P2Kw=r['P2'],P1Kw=r['P1'],Rpm=hd['rpm'],Poles=poles,
                    Voltage='3~400 В 50 Гц',WeightKg=r['W'],QH=qh,QP=qp,RangeQmax=qh[-1][0],
                    Document=f"{doc}, изд. {date[:4]}-{date[4:6]}, стр. {i+1}",Url=BASE+fn,Notes=note))
if __name__=="__main__":
  for r in report: print(r)
seen=set(); out=[]
for r in recs:
    if r['Id'] in seen: continue
    seen.add(r['Id']); out.append(r)
save('out/homa.json',out)
json.dump(report,open('out/homa_report.json','w'),ensure_ascii=False,indent=1)

json.dump(missing,open('out/homa_excluded.json','w'),ensure_ascii=False,indent=1); print('без кривой:',len(missing))
