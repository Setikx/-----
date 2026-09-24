"""Распознавание номеров кривых HOMA по эталонам глифов (векторный шрифт один и тот же)."""
import numpy as np,cv2,json,pymupdf,re,collections
from homa_dig import charts,render,digit_layer,Z
from rdig import ocr
def glyphs(page,c):
    render(page,c); dl,nd=digit_layer(page,c)
    if not nd: return []
    gm=(dl.max(2)<200).astype(np.uint8)
    n,lab,st,_=cv2.connectedComponentsWithStats(gm,8); out=[]
    for i in range(1,n):
        x,y,w,h,a=st[i]
        if h<2*Z or h>9*Z or w>7*Z: continue
        out.append(dict(x=x,y=y,w=w,h=h,img=(lab[y:y+h,x:x+w]==i).astype(np.uint8)))
    # «1» может состоять из двух штрихов: объединяем компоненты, перекрывающиеся по x и близкие по y
    return out
def norm(g):
    im=g['img']*255; h,w=im.shape; s=28/max(h,w*28/20)
    im=cv2.resize(im.astype(np.uint8),(max(1,int(w*s)),max(1,int(h*s))),interpolation=cv2.INTER_AREA)
    can=np.zeros((32,24),np.uint8); y0=(32-im.shape[0])//2; x0=(24-im.shape[1])//2
    can[y0:y0+im.shape[0],x0:x0+im.shape[1]]=im
    return can.astype(float)/255
def ocr1(g):
    im=255-g['img']*255; im=cv2.copyMakeBorder(im.astype(np.uint8),int(g['h']*0.8),int(g['h']*0.8),int(g['h']*1.2),int(g['h']*1.2),cv2.BORDER_CONSTANT,value=255)
    im=cv2.resize(im,None,fx=60/g['h'],fy=60/g['h'],interpolation=cv2.INTER_AREA)
    r=[t[4] for t in ocr(cv2.cvtColor(im,cv2.COLOR_GRAY2RGB))]
    r=[t.replace('O','0').replace('o','0').replace('l','1').replace('I','1').replace('|','1') for t in r]
    return r[0] if len(r)==1 and re.fullmatch(r'\d',r[0]) else None
if __name__=='__main__':
    G=[]
    for fn,pages in [('homa/GB_leaflet_wastewater_treatment_DN80_DN150.pdf',range(16,30)),('homa/GB_leaflet_pumps_for_waste_water_systems_DN200_DN500.pdf',range(13,22))]:
        d=pymupdf.open(fn)
        for i in pages:
            for c in charts(d[i]): G+=glyphs(d[i],c)
    print('глифов',len(G))
    V=np.array([norm(g).ravel() for g in G]); V=V-V.mean(1,keepdims=True); V/=np.linalg.norm(V,axis=1,keepdims=True)+1e-9
    cl=[]; lab=[]
    for v in V:
        if cl:
            sims=[float(v@c_['mean']) for c_ in cl]; j=int(np.argmax(sims))
            if sims[j]>0.85: cl[j]['m'].append(v); cl[j]['mean']=np.mean(cl[j]['m'],0); cl[j]['mean']/=np.linalg.norm(cl[j]['mean']); lab.append(j); continue
        cl.append(dict(m=[v],mean=v)); lab.append(len(cl)-1)
    print('кластеров',len(cl),sorted(collections.Counter(lab).values(),reverse=True)[:20])
    votes=collections.defaultdict(collections.Counter)
    rng=np.random.default_rng(0)
    for j in range(len(cl)):
        idx=[k for k,l in enumerate(lab) if l==j]
        for k in rng.choice(idx,min(12,len(idx)),replace=False):
            r=ocr1(G[k]); 
            if r: votes[j][r]+=1
    T={}
    for j in range(len(cl)):
        vc=votes[j].most_common(2); n=len([l for l in lab if l==j])
        print(j,n,vc)
        if vc and vc[0][1]>=2 and (len(vc)==1 or vc[0][1]>=2*vc[1][1]): T[j]=vc[0][0]
    np.save('homa/glyph_templates.npy',np.array([cl[j]['mean'] for j in T])); json.dump([T[j] for j in T],open('homa/glyph_labels.json','w'))
    print(T)
