"""HOMA: оцифровка векторных графиков (обводки разбиты на треугольники) через растр.
Калибровка осей — по текстовым подписям PDF; номера кривых — OCR по растру после удаления длинных линий."""
import re,json,numpy as np,cv2,pymupdf,sys
sys.path.insert(0,'.')
from vdig import fit_axis
from aq_dig import ptrack,Track,dedup,cut_foreign,cut_kinks
from rdig import ocr, col_clusters
Z=8
def num(s):
    try: return float(s.replace(',','.'))
    except: return None
def charts(page):
    """Находит графики: ярлык оси Y ('H(m)', 'P2(kW)') и ближайшая строка подписей Q в м³/h под ним."""
    W=page.get_text('words'); out=[]
    for w in W:
        t=w[4].replace(' ','')
        if t in('H(m)',) or re.fullmatch(r'P2?\((?:kW|KW)\)',t) or t in('P2(kW)','P2(KW)'):
            kind='H' if t.startswith('H') else 'P'
            x0,y0=w[0],w[1]
            # подписи оси Y: числа ниже ярлыка, выровненные по правому краю около ярлыка
            ys=[(v[1]+v[3])/2 for v in W]
            cand=[v for v in W if num(v[4]) is not None and v[1]>y0 and v[1]<y0+260 and v[0]>=w[0]-10 and v[2]<=w[2]+8]
            if not cand: continue
            from collections import Counter
            xr=Counter(round(v[2]) for v in cand).most_common(1)[0][0]
            col=[v for v in cand if abs(v[2]-xr)<2.5]
            # непрерывная колонка сверху вниз (обрываем на первом большом разрыве)
            col.sort(key=lambda v:v[1]); keep=[col[0]]
            for v in col[1:]:
                if v[1]-keep[-1][1]<40: keep.append(v)
                else: break
            yl=[((v[1]+v[3])/2,num(v[4])) for v in keep]
            if len(yl)<3: continue
            ybot=max(y for y,_ in yl)
            # строка м³/h: ярлык (m3/h) ниже
            m3=[v for v in W if 'm3/h' in v[4].replace('³','3') and v[1]>ybot and v[1]<ybot+40 and v[0]>x0]
            if not m3: continue
            m3=min(m3,key=lambda v:v[1]); ym=(m3[1]+m3[3])/2
            ql=[((v[0]+v[2])/2,num(v[4])) for v in W if num(v[4]) is not None and abs((v[1]+v[3])/2-ym)<2.5 and x0-15<v[0]<m3[0]]
            out.append(dict(kind=kind,yl=yl,ql=ql,x0=x0,y0=y0,m3=m3))
    return out
def calib(c):
    kh=fit_axis([(y,v) for y,v in c['yl']]); kq=fit_axis(c['ql'])
    return kh,kq
def render(page,c):
    kh,kq=calib(c); c['kh'],c['kq']=kh,kq
    yv=[v for _,v in c['yl']]; qv=[v for _,v in c['ql']]
    ys_=sorted(yv); ytop=(max(yv)+0.9*(ys_[-1]-ys_[-2])-kh[1])/kh[0]; ybot=(0-kh[1])/kh[0]; xl=(0-kq[1])/kq[0]; xr=(max(qv)-kq[1])/kq[0]
    # поле графика: до последней подписи Q + полшага
    step=sorted(qv)[-1]-sorted(qv)[-2]; xr=(max(qv)+0.6*step-kq[1])/kq[0]
    clip=pymupdf.Rect(xl-2,ytop-4,xr+2,ybot+2); c['clip']=clip
    pm=page.get_pixmap(matrix=pymupdf.Matrix(Z,Z),clip=clip)
    a=np.frombuffer(pm.samples,np.uint8).reshape(pm.h,pm.w,pm.n)[:,:,:3].copy()
    return a
def to_pdf(c,x,y): return c['clip'].x0+x/Z, c['clip'].y0+y/Z
def val(c,x,y):
    X,Y=to_pdf(c,x,y); return c['kq'][0]*X+c['kq'][1], c['kh'][0]*Y+c['kh'][1]
def digit_layer(page,c):
    """Растр только тонких обводок с многими сегментами (глифы номеров кривых)."""
    doc=pymupdf.open(); q=doc.new_page(width=page.rect.width,height=page.rect.height); sh=q.new_shape(); n=0
    for g in page.get_drawings():
        if not c['clip'].intersects(g['rect']) or len(g['items'])<5: continue
        if g['type']!='s': continue
        col=g.get('color') or (0,0,0)
        if max(col)-min(col)>0.12: continue      # цветная сетка
        for it in g['items']:
            if it[0]=='l': sh.draw_line(it[1],it[2])
            elif it[0]=='c': sh.draw_bezier(it[1],it[2],it[3],it[4])
        sh.finish(color=(0,0,0),width=max(0.35,g.get('width') or 0.3)); n+=1
    sh.commit()
    pm=q.get_pixmap(matrix=pymupdf.Matrix(Z,Z),clip=c['clip'])
    return np.frombuffer(pm.samples,np.uint8).reshape(pm.h,pm.w,pm.n)[:,:,:3].copy(),n
def trace(page,c,dbg=None):
    a=render(page,c); g=a.astype(int)
    mx=g.max(2); mn=g.min(2)
    dark=((mx<130)&(mx-mn<45)).astype(np.uint8)
    n,lab,st,_=cv2.connectedComponentsWithStats(dark,8)
    dl,nd=digit_layer(page,c)
    if nd:
        gl=(dl.max(2)<200).astype(np.uint8)
        nq,lq,sq,_=cv2.connectedComponentsWithStats(gl,8); keep=np.zeros_like(gl)
        for i in range(1,nq):
            x,y,w,h,ar=sq[i]
            if 2*Z<=h<=9*Z and w<=7*Z: keep[lq==i]=1
        dl=np.where(keep[:,:,None]>0,0,255).astype(np.uint8).repeat(3,2); nd=int(keep.any())
    if nd:
        im=dl; glyph=(dl.max(2)<200).astype(np.uint8)
        dark[cv2.dilate(glyph,np.ones((3,3),np.uint8))>0]=0
        n,lab,st,_=cv2.connectedComponentsWithStats(dark,8)
    else:
        ink=((mx<215)&(mx-mn<40)).astype(np.uint8)
        n2,lab2,st2,_=cv2.connectedComponentsWithStats(ink,8)
        im=np.full(ink.shape,255,np.uint8)
        for i in range(1,n2):
            x,y,w,h,ar=st2[i]
            if w<8*Z and h<8*Z and h>2.5*Z: im[lab2==i]=0
        im=cv2.cvtColor(im,cv2.COLOR_GRAY2RGB)
    c['digimg']=im
    det=[]
    if nd:
        TT=np.load('homa/glyph_templates.npy'); TL=json.load(open('homa/glyph_labels.json'))
        gm=(im.max(2)<200).astype(np.uint8)
        nn,ll,ss,_=cv2.connectedComponentsWithStats(gm,8); G=[]
        for i in range(1,nn):
            x,y,w,h,ar=ss[i]
            if h<2*Z or h>9*Z or w>7*Z: continue
            img=(ll[y:y+h,x:x+w]==i).astype(np.uint8)*255; s_=28/max(h,w*28/20)
            r=cv2.resize(img,(max(1,int(w*s_)),max(1,int(h*s_))),interpolation=cv2.INTER_AREA)
            can=np.zeros((32,24),np.uint8); y0=(32-r.shape[0])//2; x0=(24-r.shape[1])//2; can[y0:y0+r.shape[0],x0:x0+r.shape[1]]=r
            v=can.astype(float).ravel()/255; v-=v.mean(); v/=np.linalg.norm(v)+1e-9
            sims=TT@v; j=int(np.argmax(sims))
            if sims[j]>0.85: G.append([x,y,w,h,TL[j]])
        # цифры одного номера: рядом по горизонтали, одна строка
        G.sort(key=lambda g:g[0]); used=set()
        for a in range(len(G)):
            if a in used: continue
            grp=[G[a]]; used.add(a)
            for b in range(a+1,len(G)):
                if b in used: continue
                last=grp[-1]; gb=G[b]
                if abs((gb[1]+gb[3]/2)-(last[1]+last[3]/2))<0.35*last[3] and 0<=gb[0]-(last[0]+last[2])<0.7*last[3]:
                    grp.append(gb); used.add(b)
            if len(grp)>2: continue
            x0=min(g[0] for g in grp); y0=min(g[1] for g in grp); x1=max(g[0]+g[2] for g in grp); y1=max(g[1]+g[3] for g in grp)
            det.append([x0,y0,x1,y1,int(''.join(g[4] for g in grp))])
    else:
      for sc in (0.5,0.6,0.7,0.8,0.9,1.0,1.2):
        for t in ocr(cv2.resize(im,None,fx=sc,fy=sc)):
            if re.fullmatch(r'\d{1,2}',t[4]):
                x0,y0,x1,y1=[v/sc for v in t[:4]]; det.append([x0,y0,x1,y1,int(t[4])])
    # кластеры по положению, значение — голосованием
    cl=[]
    for dt in det:
        cx,cy=(dt[0]+dt[2])/2,(dt[1]+dt[3])/2
        for g in cl:
            if abs(g['cx']-cx)<Z*1.5 and abs(g['cy']-cy)<Z*1.5: g['v'].append(dt[4]); g['b'].append(dt[:4]); break
        else: cl.append(dict(cx=cx,cy=cy,v=[dt[4]],b=[dt[:4]]))
    digits=[]; m=dark.copy()
    from collections import Counter
    for g in cl:
        vc=Counter(g['v']).most_common()
        if len(vc)>1 and vc[0][1]==vc[1][1]: continue
        # «1» внутри двузначного числа: предпочитаем более длинное чтение, если оно встречается
        v=vc[0][0]
        b=np.array(g['b']); x0,y0=b[:,0].min(),b[:,1].min(); x1,y1=b[:,2].max(),b[:,3].max()
        pad=int(Z*0.3)
        sub=lab[max(0,int(y0)-pad):int(y1)+pad,max(0,int(x0)-pad):int(x1)+pad]
        for i in np.unique(sub):
            if i and st[i][2]<8*Z and st[i][3]<8*Z: m[lab==i]=0
        digits.append(((x0+x1)/2,(y0+y1)/2,v,(x1-x0,y1-y0)))
    c['mask']=m
    H,W=m.shape; X0,X1,Y0,Y1=2,W-3,2,H-3
    tracks=[]
    def covered(x,y):
        for t in tracks:
            b=np.array(t); k=np.abs(b[:,0]-x)<Z*0.6
            if k.any() and np.min(np.abs(b[k,1]-y))<Z*0.8: return True
        return False
    for f in (0.02,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9):
        xs=int(X0+f*(X1-X0))
        for y in col_clusters(m,xs,Y0,Y1,merge=2):
            if covered(xs,y): continue
            nb=col_clusters(m,xs+int(Z),Y0,Y1,merge=2); nb0=col_clusters(m,xs-int(Z),Y0,Y1,merge=2)
            if not nb or not nb0: continue
            y2=min(nb,key=lambda v:abs(v-y)); y0_=min(nb0,key=lambda v:abs(v-y))
            if abs(y2-y)>Z*1.5 or abs(y0_-y)>Z*1.5: continue
            F=ptrack(m,(xs,y),(2*Z,y2-y0_),X0,X1,Y0,Y1,R=int(Z*0.7),max_jump=int(Z*4),alpha=0.3)
            B=ptrack(m,(xs,y),(-2*Z,-(y2-y0_)),X0,X1,Y0,Y1,R=int(Z*0.7),max_jump=int(Z*4),alpha=0.3,sgn=-1)
            t=Track(sorted(B[1:],key=lambda p:p[0])+list(F),[j+len(B)-1 for j in F.jumps])
            if t[-1][0]-t[0][0]<0.12*(X1-X0): continue
            tracks.append(t)
    tracks=dedup(tracks); tracks=cut_foreign(tracks,tol=Z*0.5); tracks=[cut_kinks(t,w=int(Z*1.5),ang=40) for t in tracks]
    if dbg is not None:
        v=a.copy(); cols=[(255,0,0),(0,160,0),(0,0,255),(255,0,255),(0,150,150),(200,120,0),(120,0,200),(0,0,0),(255,120,120),(0,255,0),(120,120,255),(180,180,0)]
        for k,t in enumerate(tracks):
            for x,y in t: cv2.circle(v,(int(x),int(y)),3,cols[k%12],-1)
        for x,y,dg,_ in digits: cv2.putText(v,str(dg),(int(x)+20,int(y)),cv2.FONT_HERSHEY_SIMPLEX,1.5,(255,0,0),3)
        cv2.imwrite(dbg,cv2.cvtColor(cv2.resize(v,None,fx=0.35,fy=0.35),cv2.COLOR_RGB2BGR))
    return tracks,digits

def ticks(m,t,off=(1.2,2.6)):
    """Поперечные штрихи на треке: тёмные пиксели по обе стороны на расстоянии off (pt) по нормали."""
    a=np.array(t,float); H,W=m.shape; side=np.zeros((len(a),2),bool)
    for i in range(3,len(a)-3):
        d=a[i+3]-a[i-3]; d/=np.linalg.norm(d)+1e-9; nrm=np.array([-d[1],d[0]])
        for j,sgn in enumerate((1,-1)):
            for r in np.linspace(off[0]*Z,off[1]*Z,6):
                x,y=(a[i]+sgn*r*nrm).astype(int)
                if 0<=x<W and 0<=y<H and m[y,x]: side[i,j]=True;break
    res=[i for i in range(3,len(a)-3) if side[max(0,i-2):i+3,0].any() and side[max(0,i-2):i+3,1].any() and (side[i,0] or side[i,1])]
    # группируем
    out=[]
    for i in res:
        if out and i-out[-1][-1]<=3: out[-1].append(i)
        else: out.append([i])
    return [int(np.mean(g)) for g in out]

def segments(c,tracks):
    """Линия → кривые: от начала до каждого штриха и до конца. Возвращает список (track_idx, i_end)."""
    segs=[]
    for k,t in enumerate(tracks):
        tk=ticks(c['mask'],t)
        # штрих на пересечении с другой линией — не штрих
        tk=[i for i in tk if not any(np.min(np.hypot(np.array(u)[:,0]-t[i][0],np.array(u)[:,1]-t[i][1]))<Z*1.2 for j,u in enumerate(tracks) if j!=k)]
        tk=[i for i in tk if i<len(t)-4]
        for i in tk+[len(t)-1]: segs.append((k,i))
    return segs
def number(c,tracks,digits,n_expected):
    segs=segments(c,tracks)
    def h_at_start(k): return -tracks[k][0][1]
    order=sorted(segs,key=lambda s:(round(h_at_start(s[0])/Z/0.8),s[1]))   # снизу вверх, затем короче→длиннее
    # порядок линий снизу вверх: по y в начале (больше y = ниже)
    lines=sorted(set(k for k,_ in segs),key=lambda k:-tracks[k][0][1])
    order=[]
    for k in lines: order+=sorted([s for s in segs if s[0]==k],key=lambda s:s[1])
    num={i+1:s for i,s in enumerate(order)}
    # проверка по OCR: цифра → линия под ней, ближайший штрих/конец справа
    conflicts=[]; checked=0
    for x,y,dg,_ in digits:
        best=None
        for k,t in enumerate(tracks):
            a=np.array(t)
            if not (a[0,0]<=x<=a[-1,0]): continue
            yy=np.interp(x,a[:,0],a[:,1])
            if yy>y-Z*0.5 and yy-y<Z*6 and (best is None or yy-y<best[1]): best=(k,yy-y)
        if best is None: continue
        k=best[0]; cand=[s for s in segs if s[0]==k and tracks[k][s[1]][0]>x]
        if not cand: continue
        seg=min(cand,key=lambda s:s[1]); checked+=1
        if num.get(dg)!=seg: conflicts.append((dg,[n for n,s in num.items() if s==seg]))
    return num,len(order)==n_expected,checked,conflicts

def number_ocr(c,tracks,digits,n_expected):
    """Номер кривой → участок: линия под цифрой, до первого штриха/конца справа от цифры."""
    segs=segments(c,tracks); got={}; bad=set()
    for x,y,dg,_ in digits:
        if not 1<=dg<=n_expected: continue
        best=None
        for k,t in enumerate(tracks):
            a=np.array(t)
            if not (a[0,0]<=x<=a[-1,0]): continue
            yy=np.interp(x,a[:,0],a[:,1])
            if yy>y-Z*0.5 and yy-y<Z*6 and (best is None or yy-y<best[1]): best=(k,yy-y)
        if best is None: continue
        k=best[0]; cand=[s for s in segs if s[0]==k and tracks[k][s[1]][0]>x]
        if not cand: continue
        seg=min(cand,key=lambda s:s[1])
        if dg in got and got[dg]!=seg: bad.add(dg)
        got[dg]=seg
    # один участок — два номера: неоднозначно
    inv={}
    for dg,sg in got.items(): inv.setdefault(sg,[]).append(dg)
    for sg,l in inv.items():
        if len(l)>1: bad.update(l)
    return {k:v for k,v in got.items() if k not in bad},sorted(bad)

def assign_by_table(c,tracks,rows):
    """Линии ↔ гидравлические коды (по возрастанию диаметра = по напору при Q=0), штрихи ↔ моторы (по P2)."""
    import re as _re
    groups={}
    for k,r in enumerate(rows,1):
        code=r['model'].split('-')[0]; groups.setdefault(code,[]).append(k)
    codes=sorted(groups,key=lambda s:(_re.sub(r'\d+$','',s),int(_re.search(r'(\d+)$',s).group(1))))
    if len(tracks)!=len(codes): return None,f'линий {len(tracks)} ≠ гидравлик {len(codes)}'
    starts=[t[0][0] for t in tracks]
    if max(starts)-min(starts)>Z*6: return None,'не все линии начинаются у оси H'
    lines=sorted(range(len(tracks)),key=lambda k:-tracks[k][0][1])
    out={}
    for code,k in zip(codes,lines):
        t=tracks[k]; tk=ticks(c['mask'],t)
        tk=[i for i in tk if not any(np.min(np.hypot(np.array(u)[:,0]-t[i][0],np.array(u)[:,1]-t[i][1]))<Z*1.2 for j,u in enumerate(tracks) if j!=k)]
        tk=[i for i in tk if 4<i<len(t)-4]
        need=len(groups[code])-1
        if len(tk)!=need: return None,f'{code}: штрихов {len(tk)}, нужно {need}'
        ends=sorted(tk)+[len(t)-1]
        rs=sorted(groups[code],key=lambda n:(rows[n-1]['P2'],n))
        for n,i in zip(rs,ends): out[n]=(k,i)
    return out,'ok'
def check_ocr(c,tracks,digits,mapping,n_expected):
    got,bad=number_ocr(c,tracks,digits,n_expected)
    agree=sum(1 for d_,s_ in got.items() if mapping.get(d_)==s_); conf=[d_ for d_,s_ in got.items() if d_ in mapping and mapping[d_]!=s_]
    return agree,conf
