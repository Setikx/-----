import pymupdf,sys
def rows(page, tol=2.5):
    ws=page.get_text("words")
    ws.sort(key=lambda w:((w[1]+w[3])/2,w[0]))
    out=[]
    for w in ws:
        yc=(w[1]+w[3])/2
        if out and abs(out[-1][0]-yc)<tol: out[-1][1].append(w)
        else: out.append([yc,[w]])
    return [(y,sorted(r,key=lambda w:w[0])) for y,r in out]
if __name__=="__main__":
    d=pymupdf.open(sys.argv[1])
    for pn in sys.argv[2:]:
        p=d[int(pn)-1]
        print("=== page",pn, p.rect)
        for y,r in rows(p):
            print(f"{y:6.1f} | "+"  ".join(f"{w[4]}@{w[0]:.0f}" for w in r))
