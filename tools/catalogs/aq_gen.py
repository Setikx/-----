"""Обобщённая оцифровка одного графика Aquastrong (стр. 65–67) на базе aq_dig."""
import json,cv2,numpy as np
import aq_dig as A
Z=2.6
REG={65:(630,150,1130,395),66:(620,140,1120,395),67:(640,150,1110,395)}
def setup(pg):
    A.img=cv2.imread(f'aquastrong/p{pg}.png'); A.T=json.load(open(f'aquastrong/ocr{pg}c.json'))
    b,g,r=[A.img[:,:,i].astype(int) for i in range(3)]
    A.blue=((b-r>45)&(b>90)&(b-g>15)).astype(np.uint8)
    a,b_,c,e=REG[pg]; A.COLS=[(int(a*Z),int(c*Z))]; A.ROWS=[(int(b_*Z),int(e*Z))]
    # глобальные b,g,r модуля (используются в chart для серых линий)
    A.b,A.g,A.r=b,g,r
def run(pg, show=None):
    setup(pg); c=A.chart(0,0)
    qs=sorted(v for _,v in c['Q']); step=qs[-1]-qs[-2]
    c['X1']=int(((qs[-1]+0.5*step)-c['bq'])/c['kq'])
    tr=A.dedup(A.curves3(c)); tr=A.cut_foreign(tr); tr=[A.cut_kinks(t) for t in tr]
    cv=[[(c['kq']*x+c['bq'],c['kh']*y+c['bh']) for x,y in t] for t in tr]
    if show:
        v=A.img.copy(); cols=[(0,0,255),(0,170,0),(255,0,255),(0,140,255),(160,0,0),(0,128,128),(255,128,0),(128,0,255),(0,0,0)]
        for k,t in enumerate(tr):
            for x,y in t: cv2.circle(v,(int(x),int(y)),2,cols[k%9],-1)
            cv2.putText(v,str(k),(int(t[-1][0])+4,int(t[-1][1])),cv2.FONT_HERSHEY_SIMPLEX,0.7,cols[k%9],2)
        cv2.imwrite(show,v[c['y0']:c['y1'],c['x0']:c['x1']])
    return c,tr,cv
