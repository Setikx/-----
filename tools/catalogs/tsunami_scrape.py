import re,html,json,subprocess,os,glob
UA="Mozilla/5.0"
def get(url,fn):
    if not os.path.exists(fn): subprocess.run(['curl','-sSL','-m','60','-A',UA,'-o',fn,url])
    return open(fn,encoding='utf-8',errors='ignore').read()
out={}
series=['wq','tu','afp','b','krtf','krtk','qh','qz','as-wq','wl','rubashka','suhoy']
for s in series:
    t=get(f'https://tsunami-pump.ru/fek/{s}/',f's_{s}.html')
    prods=sorted(set(re.findall(r'href="(/fek/[^"]+/tsunami-[^"]+/)"',t)))
    if not prods: print(s,'no products'); continue
    t2=get('https://tsunami-pump.ru'+prods[0],f'p_{s}.html')
    heads=re.findall(r'<span title="([^"]+)" short="[^"]*" unit="([^"]*)">',t2)
    rows=re.findall(r'<a class="product_list_table_tr" href="([^"]+)">(.*?)</a>',t2,re.S)
    for href,body in rows:
        cells=[html.unescape(re.sub(r'<[^>]+>','',c)).strip() for c in re.findall(r'<span>(.*?)</span>',body,re.S)]
        rec={h[0]+(' ,'+h[1] if h[1] else ''):c for h,c in zip(heads,cells)}
        rec['_href']=href; rec['_series']=s
        out[href]=rec
    print(s,len(prods),'rows',len(rows),heads[:3])
json.dump(out,open('tsunami_rows.json','w'),ensure_ascii=False,indent=1)
print(len(out))
