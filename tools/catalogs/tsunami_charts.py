"""Извлекает точки графиков «Графики производительности» из сохранённых карточек tsunami-pump.ru
(атрибут d у тега <vr-chart>, HTML-экранированный JSON) -> tsunami/tsunami_charts.json."""
import glob, html, json, re
out = {}
for f in sorted(glob.glob('tsunami/pages/*.html')):
    m = re.search(r'<vr-chart d="([^"]+)"', open(f, encoding='utf-8').read())
    if m:
        out[f.split('tsunami/', 1)[1]] = json.loads(html.unescape(m.group(1)))
json.dump(out, open('tsunami/tsunami_charts.json', 'w'), ensure_ascii=False)
print(len(out))
