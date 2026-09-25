# Независимая сверка табличных записей с исходными PDF: значения H (и Q) записи
# должны встречаться подряд в одной строке страницы рядом с именем модели.
import pymupdf as fitz, json, re, glob
REPO='/home/user/-----/data/catalogs/'
def fmt(v): 
    s=('%g'%v); return {s, s.replace('.',','), ('%.1f'%v), ('%.1f'%v).replace('.',','), ('%.2f'%v).rstrip('0').rstrip('.').replace('.',','), ('%.2f'%v).rstrip('0').rstrip('.')}
def num(t):
    t=t.replace(',','.')
    try: return float(t)
    except: return None
def rows(page):
    R=[]
    for w in sorted(page.get_text('words'),key=lambda w:((w[1]+w[3])/2,w[0])):
        yc=(w[1]+w[3])/2
        if R and abs(R[-1][0]-yc)<3.2: R[-1][1].append(w)
        else: R.append([yc,[w]])
    return [(y,sorted(ws,key=lambda w:w[0])) for y,ws in R]
def subseq(vals,toks):
    it=iter(toks)
    return all(any(abs(v-t)<0.051 for t in it) for v in vals)
# кэш страниц
PENTAX={}
for f in glob.glob('p3/pentax_*.pdf'):
    d=fitz.open(f)
    for i in range(len(d)):
        first=d[i].get_text().split('\n')[0].strip()
        if first.isdigit(): PENTAX[int(first)]=(f,i)
SRC={'speroni':lambda p:('p3/speroni2021.pdf',p-1),'jung':lambda p:('p3/jung_at.pdf',p-1),'pentax':lambda p:PENTAX[p],
     'espa':lambda p:('p3/espa/ede2026.pdf',p-1),'etna':lambda p:('p3/etna/etna_sewage.pdf',p-1)}
docs={}
res={}
for b,fn in SRC.items():
    R=json.load(open(REPO+b+'.json')); bad=[]
    for r in R:
        p=int(re.search(r'стр\. (\d+)',r['Source']['Document']).group(1))
        f,i=fn(p); d=docs.setdefault(f,fitz.open(f)); rr=rows(d[i])
        Q=[x['Q'] for x in r['Curve']['QH']]; H=[x['V'] for x in r['Curve']['QH']]
        key=r['Model'].replace(' (G)','').replace(' M','').replace(' T','') if b=='espa' else r['Model'].replace(' (G)','')
        toks_key=key.split()
        ok=False
        if b=='jung':
            # Jung: строка модели содержит Q, строка «Förderhöhe» — H
            for y,ws in rr:
                txt=' '.join(w[4] for w in ws)
                if toks_key[0] in txt and subseq(Q,[num(w[4]) for w in ws if num(w[4]) is not None]): ok=True;break
            okH=any('Förderhöhe' in ' '.join(w[4] for w in ws) and subseq(sorted(set(H),reverse=False),sorted(num(w[4]) for w in ws if num(w[4]) is not None)) for y,ws in rr)
            if not okH: ok=False
        else:
            for k,(y,ws) in enumerate(rr):
                txt=' '.join(w[4] for w in ws)
                name_ok=all(t in txt for t in toks_key[:2]) or (k>0 and all(t in ' '.join(w[4] for w in rr[k-1][1]) for t in toks_key[:2]))
                nums=[num(w[4]) for w in ws if num(w[4]) is not None]
                if name_ok and subseq(H,nums): ok=True;break
            # Q-заголовок
            okQ=any(subseq(Q,[num(w[4]) for w in ws if num(w[4]) is not None]) for y,ws in rr)
            ok=ok and okQ
        if not ok: bad.append((r['Model'],p))
    res[b]=(len(R),bad)
    print(b,len(R),'не подтверждено:',len(bad),bad[:15])
