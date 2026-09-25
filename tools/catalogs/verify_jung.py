exec(open('verify_tables.py').read().split('# кэш')[0])
R=json.load(open(REPO+'jung.json')); d=fitz.open('p3/jung_at.pdf'); bad=[]
for r in R:
    p=int(re.search(r'стр\. (\d+)',r['Source']['Document']).group(1)); rr=rows(d[p-1])
    toks=r['Model'].split()
    found=False
    for k,(y,ws) in enumerate(rr):
        txt=' '.join(w[4] for w in ws)
        # строка модели: первые два токена имени + хотя бы одно из чисел Q
        if not ws or not ((ws[0][4]==toks[0] and (len(toks)<2 or toks[1] in txt)) or (len(toks)>1 and ws[0][4]==toks[1])): continue
        hdrs=[(yy,ww) for yy,ww in rr[:k] if any(w[4]=='Förderhöhe' for w in ww)]
        if not hdrs: continue
        hw=hdrs[-1][1]; xm=[w[0] for w in hw if w[4]=='[m]'][0]
        hx={num(w[4]):(w[0]+w[2])/2 for w in hw if num(w[4]) is not None and w[0]>xm}
        ok=True
        for pt in r['Curve']['QH']:
            x=hx.get(pt['V'])
            if x is None: ok=False;break
            if not any(abs((w[0]+w[2])/2-x)<9 and num(w[4]) is not None and abs(num(w[4])-pt['Q'])<0.051 for w in ws): ok=False;break
        if ok: found=True;break
    if not found: bad.append((r['Model'],p))
print('jung',len(R),'не подтверждено:',len(bad),bad)
