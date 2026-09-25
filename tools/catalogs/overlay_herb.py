import pymupdf as fitz, json
OV=json.load(open('out/herb_overlay.json')); d=fitz.open('p3/P_UNIPUMP_EN_12.pdf')
col={'QH':(1,0,0),'QP':(0,0.6,0),'QEta':(0,0,1),'QNpsh':(1,0,1)}
pan={'QH':'H','QP':'P','QEta':'Eta','QNpsh':'NPSH'}
for o in OV:
    pg=d[o['pi']]
    for k,c in col.items():
        ky,cy=o['P'][pan[k]]
        for q,v in o[k]:
            x=(q-o['cq'])/o['kq']; y=(v-cy)/ky
            pg.draw_circle(fitz.Point(x,y),1.3,color=c,fill=c,width=0)
    q,v=o['QH'][-1]; ky,cy=o['P']['H']
    pg.insert_text(fitz.Point((q-o['cq'])/o['kq']+2,(v-cy)/ky+6),o['m'].split('-')[-1]+'/'+o['m'].split('/')[0],fontsize=5,color=(1,0,0))
for i in range(11,19):
    d[i].get_pixmap(dpi=110,clip=fitz.Rect(30,40,300,842)).save(f'p3/ovh{i}.png')
