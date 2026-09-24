"""Извлекает точки графиков «Графики производительности» из сохранённых карточек tsunami-pump.ru
(атрибут d у тега <vr-chart>, HTML-экранированный JSON) -> tsunami/tsunami_charts.json."""
import glob, html, json, re
out = {}
for f in sorted(glob.glob('tsunami/pages/*.html')):
    m = re.search(r'<vr-chart d="([^"]+)"', open(f, encoding='utf-8').read())
    if m:
        j = html.unescape(m.group(1))
        # на сайте встречаются неэкранированные кавычки в имени (V1500-3"(F)) — чистим поле name
        j = re.sub(r'"name":"(.*?)","points"', lambda z: '"name":' + json.dumps(z.group(1)) + ',"points"', j)
        out[f.split('tsunami/', 1)[1]] = json.loads(j)
json.dump(out, open('tsunami/tsunami_charts.json', 'w'), ensure_ascii=False)
print(len(out))
