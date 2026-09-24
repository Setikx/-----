import pymupdf,re,collections
def font_offsets(doc):
    """для каждого шрифта подбираем сдвиг кода символа, дающий «читаемый» текст"""
    cnt=collections.defaultdict(collections.Counter)
    for p in doc:
        for b in p.get_text('rawdict')['blocks']:
            for l in b.get('lines',[]):
                for s in l['spans']:
                    for c in s['chars']: cnt[s['font']][ord(c['c'])]+=1
    off={}
    good=set(map(ord,'0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz .,-/()%:'))
    for f,C in cnt.items():
        best=max(range(0,40),key=lambda o:sum(v for k,v in C.items() if (k+o) in good)-0.001*o)
        off[f]=best
    return off
def spans(p,off):
    out=[]
    for b in p.get_text('rawdict')['blocks']:
        for l in b.get('lines',[]):
            for s in l['spans']:
                o=off.get(s['font'],0)
                t=''.join(chr(ord(c['c'])+o) if ord(c['c'])<0x2000 else c['c'] for c in s['chars'])
                if t.strip(): out.append((s['bbox'][0],s['bbox'][1],s['bbox'][2],s['bbox'][3],t.strip(),s['font']))
    return out
if __name__=='__main__':
    import sys
    d=pymupdf.open(sys.argv[1]); off=font_offsets(d); print(off)
    for pn in map(int,sys.argv[2:]):
        S=sorted(spans(d[pn-1],off),key=lambda s:(round(s[1]/3),s[0]))
        for s in S: print(round(s[0]),round(s[1]),s[4])
