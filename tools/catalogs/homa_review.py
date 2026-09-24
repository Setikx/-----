"""Карточки для визуальной сверки номеров кривых: исходный график + участки линий с буквенными метками."""
import pymupdf,cv2,numpy as np,json,string,sys
from homa_dig import *
def card(p,c,fn):
    tr,dg=trace(p,c); segs=segments(c,tr)
    a=cv2.cvtColor(render(p,c),cv2.COLOR_RGB2BGR)
    cols=[(0,0,230),(0,150,0),(230,0,0),(200,0,200),(0,140,200),(120,60,0),(0,0,0),(150,150,0)]
    L={}
    for n,(k,i) in enumerate(segs):
        lab=string.ascii_uppercase[n]; L[lab]=[k,i]
        x,y=tr[k][i]; col=cols[k%8]
        cv2.circle(a,(int(x),int(y)),int(Z*0.9),col,3)
        cv2.putText(a,lab,(int(x)+10,int(y)+int(Z*3)),cv2.FONT_HERSHEY_SIMPLEX,2.2,col,5)
    for k,t in enumerate(tr):
        for x,y in t[::3]: cv2.circle(a,(int(x),int(y)),2,cols[k%8],-1)
    cv2.imwrite(fn,cv2.resize(a,None,fx=0.42,fy=0.42,interpolation=cv2.INTER_AREA))
    return tr,dg,segs,L
