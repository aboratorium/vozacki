"""Builds the app (index.html, sw.js, manifest) from data/ and tools/template.html.

Run from anywhere:  python3 tools/build.py
Fails if a data check (T1, T2, T5 in docs/ARCHITECTURE.md) does not pass.
"""
import base64, hashlib, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA, TOOLS = ROOT / 'data', ROOT / 'tools'

Q = json.loads((DATA / 'questions.json').read_text())
GLOSS = json.loads((DATA / 'glossary.json').read_text())
CSS = (TOOLS / 'tailwind' / 'out.css').read_text()
TPL = (TOOLS / 'template.html').read_text()
EXAM = {'examN': 43, 'examPts': 80, 'examPass': 68}   # docs/adr/0008

# ---- data checks ----
errors = []
ids = [q['id'] for q in Q]
if len(ids) != len(set(ids)): errors.append('T0: duplicate ids')
for q in Q:
    tag = f"{q['id']} (p.{q['page']})"
    if not q.get('order') and sum(o['ok'] for o in q['o']) != 1: errors.append(f'T1 key: {tag}')
    if not q.get('order') and len(q['o']) != 3: errors.append(f'T1 options: {tag}')
    if not q.get('qr') or any(not o.get('r') for o in q['o']): errors.append(f'T2 translation: {tag}')
    if re.search(r'na slic|kao na slici|prikazan', q['q'], re.I) and not q.get('img'): errors.append(f'T5 image missing: {tag}')
    if q.get('img') and not (DATA / 'img' / q['img']).exists(): errors.append(f"T5 image file: {q['img']}")
if errors:
    print('BUILD FAILED\n  ' + '\n  '.join(errors)); sys.exit(1)

# ---- assemble ----
def b64(name):
    return 'data:image/webp;base64,' + base64.b64encode((DATA / 'img' / name).read_bytes()).decode()

out = []
for q in Q:
    d = {k: q[k] for k in ('id', 'legacy', 'sec', 'q', 'qr', 'o') }
    for k in ('order', 'n', 'f', 's'):
        if q.get(k): d[k] = q[k]
    if q.get('img'): d['img'] = b64(q['img'])
    out.append(d)

meta = dict(EXAM, foot=f'Официальный каталог вопросов, Ministarstvo prosvjete, maj 2023. Ключ ответов — GAS auto škola. Вопросов: {len(out)}. Прогресс хранится на этом устройстве.')
html = (TPL.replace('/*TAILWIND*/', CSS)
           .replace('/*DATA*/[]', json.dumps(out, ensure_ascii=False))
           .replace('/*GLOSS*/[]', json.dumps(GLOSS, ensure_ascii=False))
           .replace('/*META*/{}', json.dumps(meta, ensure_ascii=False)))
for marker in ('/*TAILWIND*/', '/*DATA*/', '/*GLOSS*/', '/*META*/'):
    assert marker not in html, marker
(ROOT / 'index.html').write_text(html)

ver = hashlib.sha1(html.encode()).hexdigest()[:10]
manifest = {'name': 'Vozački test — тренажёр B', 'short_name': 'Vozački', 'start_url': './', 'scope': './',
            'display': 'standalone', 'background_color': '#eef1f5', 'theme_color': '#1f5fae', 'lang': 'ru',
            'icons': [{'src': 'icon-192.png', 'sizes': '192x192', 'type': 'image/png'},
                      {'src': 'icon-512.png', 'sizes': '512x512', 'type': 'image/png'},
                      {'src': 'icon-512.png', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'}]}
(ROOT / 'manifest.webmanifest').write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
(ROOT / 'sw.js').write_text((TOOLS / 'sw.template.js').read_text().replace('__VERSION__', ver))
print(f'OK: {len(out)} questions, index.html {len(html)/1e6:.2f} MB, cache vozacki-{ver}')
