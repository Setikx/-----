import pymupdf,re,glob,os
from fancy import parse_pdf, grp
from common import *
BASE='https://fancy-pump.com/f/'
SER={'fancy_wq_rus':('WQ','MultiChannel','двухлопастное незасоряемое (two vanes, non-clogging)','канализационный погружной',False,'fancy_wq_rus_kanalizacionnye_pogruzhnye_nasosy_1.pdf','каталог FANCY WQ (рус., 10.2023)'),
 'fancy_wqa':('WQA','Unknown','—','канализационный погружной',False,None,'каталог FANCY WQA (10.2023)'),
 'fancy_wqas':('WQAS','Cutter','с режущим механизмом (рабочее колесо и режущая пластина из нерж. стали)','канализационный погружной',True,None,'каталог FANCY WQAS (10.2023)'),
 'fancy_wqb':('WQB','MultiChannel','двухлопастное незасоряемое','канализационный погружной',False,None,'каталог FANCY WQB (10.2023)'),
 'fancy_wqqg':('WQ…QG','Cutter','с режущим механизмом','канализационный погружной',True,None,'каталог FANCY WQQG (10.2023)'),
 'fancy_wqs':('WQS','MultiChannel','двухлопастное незасоряемое; корпус из нерж. стали','канализационный погружной',False,None,'каталог FANCY WQS (10.2023)'),
 'fancy_wqv':('WQV','Vortex','свободновихревое с режущим механизмом','канализационный погружной',True,None,'каталог FANCY WQV 2025'),
 'katalog_fancy_wqk':('WQK','Vortex','открытое вихревое','канализационный погружной',False,None,'каталог FANCY WQK'),
 'katalog_qdx':('QDX/QDXS','Unknown','рабочее колесо из алюминия/пластика; проход ≤0,2 мм','дренажный (чистая вода)',False,None,'каталог FANCY QDX/QDXS'),
 'katalog_vd':('VD','Cutter','полуоткрытое с режущим диском','канализационный погружной (бытовой)',True,None,'каталог FANCY VD'),
 'katalog_wqh':('WQH','Unknown','—','канализационный погружной (высоконапорный)',False,None,'каталог FANCY WQH'),
 'fancy_v-vn':('V/VN','Open','полуоткрытое','дренажный (грязная вода)',False,None,'каталог FANCY V/VN (10.2023)')}
def key(fn):
    return max((k for k in SER if os.path.basename(fn).startswith(k)),key=len)
def ffloat(s):
    m=re.search(r'[\d.]+',s or ''); return float(m.group(0)) if m else 0
recs=[]; seen=set()
def add(series,imp,imptxt,app,cut,url,doc,model,alt,sv,pts,rpm,page,quality='CatalogTable',nom=None,extra=''):
    if model in seen: return
    seen.add(model)
    mp=re.search(r'/(\d)$',model) or re.search(r'S(\d)$',model)
    poles=int(mp.group(1)) if mp else ({2900:2,1450:4,980:6}.get(rpm,2) if rpm else 2)
    if poles not in RPM: poles=2
    kw=ffloat(sv.get('kw')); dn=int(ffloat((sv.get('dn') or '').split('/')[0]))
    fp=ffloat(sv.get('fp'))
    volt='1~220 В / 3~380 В' if alt else '3~380 В'
    if re.search(r'\bV\b',str(sv.get('v',''))) : pass
    notes=f"Рабочее колесо: {imptxt}."
    if alt: notes+=f" Однофазное исполнение: {alt}."
    if '/' in (sv.get('dn') or ''): notes+=f" Патрубок по каталогу: {sv['dn']}."
    if pts and pts[0][0]>0 and quality=='CatalogTable': notes+=" Напор при Q=0 в таблице не приведён."
    if sv.get('amp.'): notes+=f" Iном = {sv['amp.']} А."
    notes+=extra
    kw_=dict(Application=app,Impeller=imp,HasCutter=cut,DnOut=dn,FreePassageMm=fp,P2Kw=kw,Rpm=RPM[poles],Poles=poles,Voltage=volt,
             QH=pts,Document=f"FANCY: {doc}, стр. {page}",Url=url,Quality=quality,Notes=notes)
    if nom: kw_.update(NominalQ=nom[0],NominalH=nom[1])
    recs.append(rec("Fancy",series,model,"Китай",**kw_))
for f in sorted(glob.glob('fancy/*.pdf')):
    k=key(f); series,imp,imptxt,app,cut,fn,doc=SER[k]; url=BASE+(fn or os.path.basename(f))
    if k=='fancy_wqs':
        # таблица: Q,H (ном.), Qm (макс. подача), Hm (макс. напор)
        d=pymupdf.open(f)
        for pi,p in enumerate(d):
            W=p.rect.width; allw=p.get_text('words')
            for x0,x1 in [(0,W/2),(W/2,W)]:
                ws=[w for w in allw if x0<=w[0]<x1]; hdr=None
                for y,r in grp(ws):
                    t=[w[4] for w in r]
                    if 'Qm' in t and 'Hm' in t:
                        hdr={w[4]:(w[0]+w[2])/2 for w in r if w[4] in('DN','Volt.','Q','H','Qm','Hm','n')}; continue
                    if 'kw' in t and 'hp' in t and hdr:
                        for w in r:
                            if w[4] in('kw','hp','Amp.'): hdr[w[4]]=(w[0]+w[2])/2
                        mm=[w for w in r if w[4]=='mm']; 
                        if len(mm)>1: hdr['fp']=(mm[1][0]+mm[1][2])/2
                        continue
                    if hdr and r and re.match(r'^\d+WQ',r[0][4]):
                        v={}
                        for w in r[1:]:
                            xc=(w[0]+w[2])/2; kk=min(hdr,key=lambda z:abs(hdr[z]-xc))
                            if abs(hdr[kk]-xc)<13 and kk not in v: v[kk]=w[4]
                        Q,H,Qm,Hm=[ffloat(v.get(z)) for z in('Q','H','Qm','Hm')]
                        if not(Q and H and Qm and Hm): print('WQS skip',r[0][4],v); continue
                        kq=(Hm-H)/Q**2; qend=min(Qm,(Hm*0.8/kq)**0.5 if kq>0 else Qm)
                        pts=[(qend*i/10,Hm-kq*(qend*i/10)**2) for i in range(11)]
                        rpm=int(ffloat(v.get('n'))) or None
                        one='220' in v.get('Volt.','')
                        add(series,imp,imptxt,app,cut,url,doc,r[0][4],None,{'dn':v.get('DN'),'kw':v.get('kw'),'fp':v.get('fp'),'amp.':v.get('Amp.')},pts,rpm,pi+1,'CatalogNominal',(Q,H),
                            f" {'Однофазный 1~220 В.' if one else ''} Каталог даёт только номинальную точку (Q={Q:g}; H={H:g}), Hmax={Hm:g} м и Qmax={Qm:g} м³/ч; кривая аппроксимирована параболой H=Hmax−k·Q² через номинальную точку.")
                        if one: recs[-1]['Voltage']='1~220 В'
        continue
    for r in parse_pdf(f):
        names=r['names']; model=names[-1]; alt=', '.join(names[:-1]) or None
        pts,rm=despike(sorted(dict(r['pts']).items()))
        ex=(' Исключены точки-опечатки каталога: '+', '.join(f'({q:g}; {h:g})' for q,h in rm)+'.') if rm else ''
        add(series,imp,imptxt,app,cut,url,doc,model,alt,r['spec'],pts,r['rpm'],r['page'],extra=ex)
save('out/fancy.json',recs)
import collections; print(collections.Counter(x['Series'] for x in recs))
for x in recs:
    h=[p['V'] for p in x['Curve']['QH']]
    if any(b>a+0.6 for a,b in zip(h,h[1:])): print('nonmono',x['Model'],x['Curve']['QH'])
    if not x['DnOut'] or not x['P2Kw']: print('chk',x['Model'],x['DnOut'],x['P2Kw'])
