import json, base64, io, sys
from PIL import Image

W = '/home/claude/w'
Q = json.load(open(f'{W}/data/questions_raw.json'))
RU = {}
for f in sys.argv[2:]:
    RU.update(json.load(open(f)))
pages = set(map(int, sys.argv[1].split(','))) if sys.argv[1] != 'all' else None

def section(q):
    p = q['page']
    if p <= 9: return 'Правила'
    if p <= 29: return 'Ситуации'
    if p <= 39: return 'Знаки'
    if p <= 43 or (p == 44 and q['img']): return 'Регулировщик и сигналы'
    return 'Техника и первая помощь'

def img64(fn):
    im = Image.open(f'{W}/data/img/{fn}').convert('RGB')
    if im.width > 640: im = im.resize((640, round(im.height * 640 / im.width)), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, 'WEBP', quality=72)
    return 'data:image/webp;base64,' + base64.b64encode(b.getvalue()).decode()

GLOSS = [
 ('pretic|preticanj|pretek|pretič', 'preticanje', 'обгон (выезд на соседнюю полосу, чтобы опередить движущееся ТС)'),
 ('obilaž|obilaz|obiđ', 'obilaženje', 'объезд стоящего ТС или препятствия'),
 ('mimoilaž|mimoilaz|mimoiđ|mimoiš', 'mimoilaženje', 'встречный разъезд (проезд мимо встречного ТС)'),
 ('prestroj', 'prestrojavanje', 'перестроение из полосы в полосу'),
 ('kolovozn', 'kolovozna traka', 'половина проезжей части для одного направления (может быть из нескольких полос)'),
 ('saobraćajn[a-z]* trak', 'saobraćajna traka', 'полоса движения (одна полоса)'),
 ('kolovoz', 'kolovoz', 'проезжая часть'),
 ('raskrsnic|raskrnic|rasksnic', 'raskrsnica', 'перекрёсток'),
 ('prvenstv', 'prvenstvo prolaza', 'преимущество в проезде, приоритет'),
 ('naselj', 'naselje', 'населённый пункт'),
 ('zaustav', 'zaustavljanje', 'остановка (до 5 минут)'),
 ('parkir', 'parkiranje', 'стоянка, парковка (дольше 5 минут)'),
 ('pješačk[a-z]* prelaz', 'pješački prelaz', 'пешеходный переход'),
 ('pješa|pješak', 'pješak', 'пешеход'),
 ('putničk', 'putničko vozilo', 'легковой автомобиль'),
 ('teretn', 'teretno vozilo', 'грузовой автомобиль'),
 ('priključn', 'priključno vozilo', 'прицеп (прицепное ТС)'),
 ('pokazivač[a-z]* pravca', 'pokazivač pravca', 'указатель поворота, поворотник'),
 ('zadržava[a-z]* pravac', 'zadržava pravac kretanja', 'едет прямо, не меняет направления'),
 ('skreć|skretanj|skrenu', 'skretanje', 'поворот'),
 ('ulijevo|lijev', 'lijevo', 'налево / левый'),
 ('udesno|desn', 'desno', 'направо / правый'),
 ('razdjeln', 'razdjelna linija', 'разделительная линия (разметка между встречными потоками)'),
 ('ivičn', 'ivična linija', 'краевая линия разметки'),
 ('ivic', 'ivica', 'край (проезжей части)'),
 ('ovlašćen', 'ovlašćeni službenik', 'уполномоченный сотрудник (регулировщик, полиция)'),
 ('propust|propuštaj|propuštanj', 'propustiti', 'пропустить, уступить дорогу'),
 ('ne smij', 'ne smije', 'нельзя, не имеет права'),
 ('smij', 'smije', 'можно, имеет право'),
 ('dužan', 'dužan je', 'обязан'),
 ('magistraln', 'magistralni put', 'магистральная дорога (между городами)'),
 ('autoput', 'autoput', 'автомагистраль'),
 ('unazad', 'unazad', 'задним ходом'),
 ('nepregledn', 'nepregledan', 'без обзора (о повороте, участке)'),
 ('semafor', 'semafor', 'светофор'),
 ('tramvaj', 'tramvaj', 'трамвай'),
 ('vozač', 'vozač', 'водитель'),
 ('vozil', 'vozilo', 'транспортное средство (ТС)'),
 ('nastavi|nastaviti', 'nastaviti kretanje', 'продолжить движение'),
 ('naznačen', 'naznačen', 'указанный'),
]
GL = [{'p': p, 'w': w, 'ru': r} for p, w, r in GLOSS]

out = []
for q in Q:
    if pages and q['page'] not in pages: continue
    r = RU.get(str(q['id']), {})
    d = {'id': q['id'], 'sec': section(q), 'q': q['q'], 'qr': r.get('q', ''),
         'o': [{'t': o['t'], 'ok': o['ok'], 'r': (r.get('o') or [''] * 3)[i] if i < len(r.get('o') or []) else ''} for i, o in enumerate(q['opts'])]}
    if q['order']: d['order'] = q['order'].replace(' ', '')
    if q['img']: d['img'] = img64(q['img'])
    if r.get('n'): d['n'] = r['n']
    if r.get('flag'): d['f'] = r['flag']
    out.append(d)

# drop exact duplicates
seen, uniq = set(), []
for d in out:
    k = (d['q'], tuple(o['t'] for o in d['o']), d.get('img', '')[:200])
    if k in seen: continue
    seen.add(k); uniq.append(d)

meta = {'examN': 43, 'examPts': 80, 'examPass': 68, 'foot': f'Источник: билеты GAS auto škola. Вопросов: {len(uniq)}. Прогресс хранится только в этом браузере.'}
html = open(f'{W}/template.html').read()
html = html.replace('/*DATA*/[]', json.dumps(uniq, ensure_ascii=False)).replace('/*GLOSS*/[]', json.dumps(GL, ensure_ascii=False)).replace('/*META*/{}', json.dumps(meta, ensure_ascii=False))
name = sys.argv[1].replace(',', '-')
open(f'{W}/vozacki.html', 'w').write(html)
print(len(uniq), 'questions', round(len(html) / 1e6, 2), 'MB')
