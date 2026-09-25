import json,sys
R=json.load(open('out/herborner.json'))
def interp(c,q):
    for a,b in zip(c,c[1:]):
        if a['Q']<=q<=b['Q']: return a['V']+(b['V']-a['V'])*(q-a['Q'])/(b['Q']-a['Q']+1e-12)
    return None
bad=0
for r in R:
    C=r['Curve']; qh=C['QH']
    if not C['QP'] or not C['QEta']: print('нет P/η',r['Model'],len(C['QP']),len(C['QEta']),len(C['QNpsh'])); continue
    qmax=qh[-1]['Q']; rs=[]
    for f in (0.4,0.6,0.8):
        q=qmax*f; h=interp(qh,q); p=interp(C['QP'],q); e=interp(C['QEta'],q)
        if None in (h,p,e) or e<5: continue
        rs.append(9.81*q/3600*h/(e/100)/p)
    flag='  <<<' if not rs or (max(rs)>1.12 or min(rs)<0.88) else ''
    if flag: bad+=1
    if flag or '-v' in sys.argv: print(r['Model'],r['P2Kw'],[round(x,2) for x in rs],flag)
print('bad',bad,len(R))
