"""Разбор карточек tsunami-pump.ru: наименование и таблица характеристик -> tsunami/tsunami_pages.json."""
import re, json, glob, html, collections
keys = collections.Counter(); D = {}
for f in glob.glob('tsunami/pages/*.html'):
    t = open(f, encoding='utf-8', errors='ignore').read()
    m = re.search(r'"additionalProperty":(\[.*?\])', t)
    name = re.search(r'<h1[^>]*>(.*?)</h1>', t, re.S)
    props = {}
    if m:
        for p in json.loads(m.group(1)): props[p['name']] = p['value']; keys[p['name']] += 1
    for a, b in re.findall(r'<tr itemprop="additionalProperty"[^>]*>.*?<t[dh][^>]*>(.*?)</t[dh]>.*?<t[dh][^>]*>(.*?)</t[dh]>', t, re.S):
        a = html.unescape(re.sub(r'<[^>]+>', '', a)).strip(); b = html.unescape(re.sub(r'<[^>]+>', '', b)).strip()
        if a and a not in props: props[a] = b; keys[a] += 1
    D[f.split('tsunami/', 1)[1]] = dict(name=html.unescape(re.sub(r'<[^>]+>', '', name.group(1))).strip() if name else '', props=props)
json.dump(D, open('tsunami/tsunami_pages.json', 'w'), ensure_ascii=False, indent=1)
print(len(D), keys.most_common(30))
