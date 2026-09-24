"""Скачивает все карточки товаров tsunami-pump.ru по карте сайта (sitemap-products.xml) в tsunami/pages/.
Далее: tsunami_pages.py (характеристики), tsunami_charts.py (точки графиков), tsunami_build.py (PumpRecord)."""
import os, re, subprocess
from concurrent.futures import ThreadPoolExecutor
os.makedirs('tsunami/pages', exist_ok=True)
sm = subprocess.run(['curl', '-sSL', '-m', '120', '-A', 'Mozilla/5.0', 'https://tsunami-pump.ru/sitemaps/sitemap-products.xml'],
                    capture_output=True, text=True).stdout
urls = [u.replace('https://tsunami-pump.ru', '') for u in re.findall(r'<loc>([^<]+)</loc>', sm)]
def get(u):
    fn = 'tsunami/pages/' + u.replace('/', '_') + '.html'
    if not os.path.exists(fn) or os.path.getsize(fn) == 0:
        subprocess.run(['curl', '-sSL', '-m', '60', '-A', 'Mozilla/5.0', '-o', fn, 'https://tsunami-pump.ru' + u])
with ThreadPoolExecutor(8) as ex: list(ex.map(get, urls))
print(len(urls))
