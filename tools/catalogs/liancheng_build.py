"""Shanghai Liancheng WQ: таблицы «WQ type pump performance» (3 рабочие точки Q–H–η) — OCR (текст в PDF в кривых)."""
import pymupdf,numpy as np,json,re,os
from rdig import ocr
from common import rec,save
FILES=[('wq.pdf','WQ','канализационный погружной','https://www.liancheng-pump.com/uploads/202302/WQ-Model-Submersible-sewage-water-pump_1677552539_WNo.pdf','«WQ series submersible sewage pump» (изд. 2020)'),
       ('wqc.pdf','WQC','канализационный погружной (малый)','https://www.liancheng-pump.com/uploads/202303/WQC-Series-Small-Submersible-Sewage-Pump_1677907323_WNo.pdf','«WQC series small submersible sewage pump» (изд. 2021)'),
       ('wl.pdf','WL','канализационный сухой установки (вертикальный)','https://www.liancheng-pump.com/uploads/202302/WL-Model-Dry-type-sewage-water-pump_1677557216_WNo.pdf','«WL dry-type sewage pump» (изд. 2021)')]
Z=3.5
def num(s):
    s=s.replace(',','.').replace('O','0')
    try: return float(s)
    except: return None
recs=[];seen=set();log=[]
for FN,SER,APP,URL,DOC in FILES:
  d=pymupdf.open('liancheng/'+FN); cache=f'liancheng/ocr_{SER}.json'; C=json.load(open(cache)) if os.path.exists(cache) else {}
  for pi in range(len(d)):
      p=d[pi]; W=p.rect.width
      for half,clip in (('L',pymupdf.Rect(30,100,W/2,p.rect.height-60)),('R',pymupdf.Rect(W/2,100,W-30,p.rect.height-60))):
          key=f'{pi}{half}'
          if key not in C:
              pm=p.get_pixmap(matrix=pymupdf.Matrix(Z,Z),clip=clip)
              a=np.frombuffer(pm.samples,np.uint8).reshape(pm.h,pm.w,pm.n)[:,:,:3].copy()
              C[key]=[[t[0],t[1],t[2],t[3],t[4]] for t in ocr(a)]
          T=C[key]
          hd={}
          for t in T:
              s=t[4]; xc=(t[0]+t[2])/2
              if re.fullmatch(r'\(m.{0,2}/h\)',s): hd['Q']=xc
              elif s=='(L/s)': hd['L']=xc
              elif s=='Head': hd['H']=xc
              elif s=='Speed': hd['n']=xc
              elif s=='Power': hd['P']=xc
              elif s.startswith('Effic') or s=='(%)': hd['E']=xc
              elif 'NPSH' in s: hd['N']=xc
              elif s=='Weight': hd['W']=xc
              elif s in('Outlet diameter',): hd['D']=xc
          if not {'Q','H','n','P'}<=set(hd): continue
          ytop=max(t[3] for t in T if t[4] in('(L/s)','Head'))
          models=sorted([t for t in T if re.fullmatch(r'\d{2,3}W[QL][A-Z]?\d+(\.\d+)?-\d+(\.\d+)?-\d+(\.\d+)?(\(G\))?',t[4].replace(' ',''))],key=lambda t:t[1])
          ys=[(t[1]+t[3])/2 for t in models]
          for j,mt in enumerate(models):
              y=ys[j]; y0=(ys[j-1]+y)/2 if j else ytop; y1=(ys[j+1]+y)/2 if j+1<len(ys) else y+(y-y0)
              cell=[t for t in T if y0<(t[1]+t[3])/2<=y1 and t is not mt]
              col={k:[] for k in hd}
              for t in cell:
                  v=num(t[4])
                  if v is None: continue
                  xc=(t[0]+t[2])/2; k=min(hd,key=lambda k:abs(hd[k]-xc))
                  if abs(hd[k]-xc)<40: col[k].append(((t[1]+t[3])/2,v))
              Q=[v for _,v in sorted(col['Q'])]; H=[v for _,v in sorted(col['H'])]; E=[v for _,v in sorted(col.get('E',[]))]; NP=[v for _,v in sorted(col.get('N',[]))]
              L=[v for _,v in sorted(col.get('L',[]))]
              model=mt[4].replace(' ','')
              if len(Q)!=3 and len(L)==3: Q=[round(x*3.6,1) for x in L]
              ok=len(Q)==3 and len(H)==3 and Q==sorted(Q) and H==sorted(H,reverse=True)
              if L and len(L)==len(Q): ok=ok and all(abs(q/3.6-l)<0.02*l+0.2 for q,l in zip(Q,L))
              if not ok:
                log.append((model,f'в таблице только номинальная точка (Q={Q[0]:g}, H={H[0]:g}) — кривой нет' if len(Q)==1 and len(H)==1 else f'стр.{pi+1}{half}: не распознаны 3 точки Q/H ({Q},{H})')); continue
              rpm=[v for _,v in col['n']]; P=[v for _,v in col['P']]; Wt=[v for _,v in col.get('W',[])]; D=[v for _,v in col.get('D',[])]
              m=re.match(r'(\d+)W[QL][A-Z]?(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)',model)
              dn,qn,hn,kw=int(m.group(1)),float(m.group(2)),float(m.group(3)),float(m.group(4))
              if abs(Q[1]-qn)>0.05*qn or abs(H[1]-hn)>0.1*hn: log.append((model,f'стр.{pi+1}: средняя точка ({Q[1]},{H[1]}) не совпадает с обозначением')); continue
              r=int(rpm[0]) if rpm else 0
              if model in seen: continue
              seen.add(model)
              recs.append(rec("Shanghai Liancheng",SER,model,"Китай",Application=APP,Impeller='Unknown',DnOut=dn,
                  P2Kw=P[0] if P else kw,Rpm=r,Poles={2900:2,2950:2,2960:2,1450:4,1480:4,1470:4,980:6,990:6,960:6,740:8,745:8,590:10,595:10}.get(r,0),
                  Voltage='3~380 В 50 Гц',WeightKg=Wt[0] if Wt else 0,NominalQ=Q[1],NominalH=H[1],NominalEta=E[1]/100 if len(E)==3 else 0,
                  RangeQmin=Q[0],RangeQmax=Q[2],QH=list(zip(Q,H)),QEta=list(zip(Q,[e/100 for e in E])) if len(E)==3 else [],QNpsh=list(zip(Q,NP)) if len(NP)==3 and NP==sorted(NP) else [],
                  Document=f"Shanghai Liancheng {DOC}, таблица характеристик, стр. {pi+1}",Url=URL,
                  Notes="Три рабочие точки таблицы изготовителя (левая граница, номинал, правая граница рабочего диапазона); точки Q=0 в каталоге нет. Таблица распознана OCR (текст в PDF в кривых), Q сверен с колонкой л/с."))
  json.dump(C,open(cache,'w'))
save('out/liancheng.json',recs); json.dump(log,open('out/liancheng_excluded.json','w'),ensure_ascii=False,indent=1)
print(len(log)); print(log[:10])
