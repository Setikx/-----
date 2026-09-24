import pymupdf,cv2,numpy as np,re,collections
from aikon_ssc import *
from common import *
def page_charts(p):
    ims=[(p.get_image_bbox(im),im) for im in p.get_images(full=True)]
    ims=[(r,im) for r,im in ims if r.width>150 and r.height>50]
    ims.sort(key=lambda z:(round(z[0].x0),z[0].y0))
    rects=[]
    for r,_ in ims:
        if rects and abs(rects[-1].x0-r.x0)<2 and abs(rects[-1].x1-r.x1)<2 and -3<=r.y0-rects[-1].y1<3: rects[-1]=rects[-1]|r
        else: rects.append(pymupdf.Rect(r))
    words=[w for w in p.get_text('words')]
    out=[]
    for r in rects:
        # заголовок: ближайшее название модели над картинкой
        cands=[]
        ws=[w for w in words if w[3]<=r.y0+3 and r.y0-40<w[1] and w[0]<r.x1 and w[2]>r.x0]
        for y,row in grp(ws):
            s=''.join(w[4] for w in row)
            if re.match(r'^\d+SSC',s): cands.append((r.y0-y,norm(s)))
        if cands: out.append((min(cands)[1],r))
    return out
def build(f,url,doc,table_pages,chart_pages,series,app,dry=False):
    d=pymupdf.open(f); T=tables(d,table_pages); recs=[]; bad=[]
    for pn in chart_pages:
        p=d[pn-1]
        for name,r in page_charts(p):
            z=2.4; pix=p.get_pixmap(matrix=pymupdf.Matrix(z,z),clip=r)
            img=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.h,pix.w,pix.n)[:,:,:3][:,:,::-1].copy()
            o=digitize(img)
            if not o or 'QH' not in o or len(o['QH'])<20: bad.append((pn,name,list(o or {}))); continue
            qh=resamp(o['QH'])
            tv=T.get(name)
            m=re.match(r'^(\d+)SSC\s*([\d.]+)-([\d.]+)-([\d.]+)',name)
            dn=int(m.group(1)); qn,hn,pw=float(m.group(2)),float(m.group(3)),float(m.group(4))
            rpm=0;fp=0
            if tv:
                if len(tv)>=4 and not dry: qn,hn,pw,dn=tv[0] or qn,tv[1] or hn,tv[2] or pw,int(tv[3] or dn); rpm=int(tv[4] or 0) if len(tv)>4 and tv[4] and tv[4]>500 else 0; fp=tv[5] if len(tv)>5 and tv[5] else (tv[4] if len(tv)==5 and tv[4] and tv[4]<500 else 0)
                elif dry: fp=tv[0] or 0
            poles={2900:2,2950:2,1450:4,1470:4,1480:4,980:6,960:6,740:8}.get(rpm,0)
            imp='MultiChannel'; imptxt='незасоряемое (двухканальное по описанию серии)'
            if dry:
                if name.endswith('OG'): imp,imptxt='Open','полуоткрытое (OG)'
                else: imp,imptxt='SingleChannel','канальное (G)'
            # проверка номинальной точки
            h_at=float(np.interp(qn,[a for a,_ in qh],[b for _,b in qh]))
            err=abs(h_at-hn)/hn
            note=f"Рабочее колесо: {imptxt}. Кривые Q–H{', КПД' if 'QEFF' in o else ''}{', P' if 'QP' in o else ''}{', NPSHr' if 'QNPSH' in o else ''} оцифрованы с растрового графика каталога (оси по OCR подписей делений). Номинальная точка по каталогу: Q={qn:g} м³/ч, H={hn:g} м (по кривой {h_at:.1f} м, расхождение {err*100:.1f} %)."
            if err>0.1: note+=" ВНИМАНИЕ: расхождение с номинальной точкой >10 % — проверьте по каталогу."
            eta=0
            qe=resamp(o['QEFF'],12,1) if 'QEFF' in o else []
            if qe: eta=round(float(np.interp(qn,[a for a,_ in qe],[b for _,b in qe])),1)
            rec_=rec("Aikon",series,name,"Китай",Application=app,Impeller=imp,DnOut=dn,FreePassageMm=fp,P2Kw=pw,Rpm=rpm,Poles=poles,
                Voltage='3~380 В',NominalQ=qn,NominalH=hn,NominalEta=eta,QH=qh,QP=resamp(o['QP'],12,3) if 'QP' in o else [],
                QEta=qe,QNpsh=resamp(o['QNPSH'],10,2) if 'QNPSH' in o else [],Document=f"{doc}, стр. {pn}",Url=url,Notes=note)
            if not rpm: rec_['Notes']+=" Частота вращения в каталоге не указана (0 — неизвестно)."
            recs.append(rec_)
    return recs,bad,T
if __name__=='__main__':
    all_=[]
    r1,b1,T1=build('aikon/ssc_220925.pdf','https://www.cnprussia.ru/upload/iblock/98b/fd4psm44p9aatuxcn3jh7slctp3et9cl/SSC_220925.pdf',
        'Aikon «Погружные канализационные насосы SSC», каталог 22.09.2025',[8,9,10,11],range(14,49),'SSC','канализационный погружной')
    print('SSC',len(r1),'bad',b1,'table',len(T1))
    r2,b2,T2=build('aikon/scgog_85c.pdf','https://www.cnprussia.ru/upload/iblock/85c/sy4ayu42ho00223kulz2ytpxblsajk9n.pdf',
        'Aikon «Канализационные насосы с рубашкой охлаждения SSC-G/OG», каталог 01.2025',[8],range(13,30),'SSC-G/OG','канализационный сухой установки (с рубашкой охлаждения)',dry=True)
    print('SSC-G/OG',len(r2),'bad',b2,'table',len(T2))
    json.dump(r1+r2,open('out/aikon_ssc.json','w'),ensure_ascii=False,indent=1)
