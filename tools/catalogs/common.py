import hashlib, json, re
RPM={2:2900,4:1450,6:960,8:725,10:580}
def num(s):
    s=s.replace(',', '.').strip()
    try: return float(s)
    except: return None
def pid(man,model): return hashlib.md5(f"{man}|{model}".encode()).hexdigest()[:8]
def rec(man,series,model,country,**kw):
    r={"Id":pid(man,model),"Manufacturer":man,"Series":series,"Model":model,"Country":country,
       "Application":"канализационный погружной","Impeller":"Unknown","HasCutter":False,"DnOut":0,
       "FreePassageMm":0,"P2Kw":0,"P1Kw":0,"Rpm":2900,"Poles":2,"Voltage":"3~400 В","WeightKg":0,
       "InertiaKgM2":0,"ImpellerDmm":0,"TrimMin":0.85,"SpeedMin":0.6,"NominalQ":0,"NominalH":0,
       "NominalEta":0,"RangeQmin":0,"RangeQmax":0,
       "Curve":{"QH":[],"QP":[],"QEta":[],"QNpsh":[]},
       "Source":{"Document":"","Url":"","Date":"2026-09","Quality":"CatalogTable"},"Notes":""}
    for k,v in kw.items():
        if k in("QH","QP","QEta","QNpsh"): r["Curve"][k]=[{"Q":round(q,3),"V":round(h,3)} for q,h in v]
        elif k in("Document","Url","Quality","Date"): r["Source"][k]=v
        else: r[k]=v
    return r
def save(path,recs):
    ids=set()
    for r in recs:
        assert r["Id"] not in ids,(r["Model"]); ids.add(r["Id"])
        qh=r["Curve"]["QH"]; assert len(qh)>=2,r["Model"]
        qs=[p["Q"] for p in qh]; assert qs==sorted(qs) and len(set(qs))==len(qs),(r["Model"],qs)
    json.dump(recs,open(path,"w"),ensure_ascii=False,indent=2)
    print(path,len(recs))
def despike(pts,rel=0.15):
    """Убирает одиночные выбросы (опечатки каталога): точка выше соседей более чем на rel."""
    pts=list(pts); removed=[]
    changed=True
    while changed and len(pts)>2:
        changed=False
        for i in range(1,len(pts)):
            prev=pts[i-1][1]; cur=pts[i][1]; nxt=pts[i+1][1] if i+1<len(pts) else None
            if cur>prev*(1+rel)+0.3 and (nxt is None or nxt<cur):
                removed.append(pts.pop(i)); changed=True; break
            if nxt is not None and nxt>cur*(1+rel)+0.3 and nxt<=prev+0.01:
                removed.append(pts.pop(i)); changed=True; break
    return pts,removed
