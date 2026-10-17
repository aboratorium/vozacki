import pymupdf as fitz, json, re, sys, os

SRC = sys.argv[1] if len(sys.argv) > 1 else 'src.pdf'
OUT = 'data'
os.makedirs(f'{OUT}/img', exist_ok=True)
doc = fitz.open(SRC)

def clean(t):
    t = re.sub(r'[\.…]{2,}.*$', '', t)          # leader dots
    t = re.sub(r'\s*[\.…]+\s*$', '', t)
    t = t.replace('…', '').strip()
    return re.sub(r'\s+', ' ', t)

questions, anomalies = [], []
seen_img = {}
for pn, page in enumerate(doc):
    # answer marks: black filled small squares on right side
    marks = [d['rect'] for d in page.get_drawings()
             if d.get('fill') == (0.0, 0.0, 0.0) and 8 < d['rect'].width < 16
             and 8 < d['rect'].height < 16 and d['rect'].x0 > 500]
    imgs = [i for i in page.get_image_info(xrefs=True)
            if i['xref'] not in (0, 22) and (i['bbox'][2]-i['bbox'][0]) > 20]
    lines = []
    for b in page.get_text('dict')['blocks']:
        if b['type'] != 0: continue
        for l in b['lines']:
            t = ''.join(s['text'] for s in l['spans']).strip()
            if t and l['bbox'][1] < 815:
                lines.append((l['bbox'], t))
    lines.sort(key=lambda x: (round(x[0][1]), x[0][0]))
    dashes = [fitz.Rect(bb) for bb, t in lines if t == '-']
    merged = [(fitz.Rect(bb), t) for bb, t in lines if t != '-']
    cur = None
    def complete(c):
        return c is not None and (len(c['opts']) >= 3 or c['order'] is not None)
    for bb, t in merged:
        t = re.sub(r'\s*[\.…]{2,}[\.… ]*', ' ', t).strip()
        isq = t.startswith('-') or (not t.startswith('*') and not re.fullmatch(r'[\d\s\.…]+', t)
               and (cur is None or complete(cur))
               and any(bb.y0-15 < (d.y0+d.y1)/2 < bb.y1+15 for d in dashes))
        if isq:
            body = t.lstrip('-').strip()
            cur = dict(page=pn+1, q=body, opts=[], ans=None, order=None, y0=bb.y0, y1=bb.y1, img=None)
            questions.append(cur)
            continue
        if cur is None: continue
        if t.startswith('*'):
            hit = any(bb.y0-4 < (m.y0+m.y1)/2 < bb.y1+4 for m in marks)
            cur['opts'].append(dict(t=t.lstrip('*').strip(), ok=hit))
        elif re.fullmatch(r'[\d\s\.…]+', t):
            if not cur['opts']:
                cur['order'] = ' '.join(re.findall(r'\d', t))
        else:
            if cur['opts']:
                if len(t) > 1 and t[0].isupper() and t[1].islower(): t = t[0].lower() + t[1:]
                cur['opts'][-1]['t'] += ' ' + t
            else: cur['q'] += ' ' + t
        cur['y1'] = bb.y1
    # images -> questions on this page by vertical overlap
    pq = [q for q in questions if q['page'] == pn+1]
    for q in pq:
        best, bo = None, 0
        for im in imgs:
            y0, y1 = im['bbox'][1], im['bbox'][3]
            ov = min(q['y1'], y1) - max(q['y0'], y0)
            if ov > bo: best, bo = im, ov
        if best:
            # cluster: images touching the primary one (supplementary plates under signs)
            grp = [best]; changed = True
            while changed:
                changed = False
                for im in imgs:
                    if im in grp or (im['bbox'][3]-im['bbox'][1]) > 35: continue
                    for g in grp:
                        a, b = fitz.Rect(im['bbox']), fitz.Rect(g['bbox'])
                        hov = min(a.x1, b.x1) - max(a.x0, b.x0) > 0
                        vgap = a.y0 - b.y1  # plate must sit just below
                        if hov and -2 < vgap < 6:
                            grp.append(im); changed = True; break
            key = tuple(sorted(i['xref'] for i in grp))
            if key not in seen_img:
                from PIL import Image
                def pil(x):
                    pix = fitz.Pixmap(doc, x)
                    if pix.n - pix.alpha > 3: pix = fitz.Pixmap(fitz.csRGB, pix)
                    if pix.alpha: pix = fitz.Pixmap(pix, 0)
                    return Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
                if len(grp) == 1:
                    im = pil(best['xref'])
                else:
                    U = fitz.Rect(grp[0]['bbox'])
                    for g in grp[1:]: U |= fitz.Rect(g['bbox'])
                    k = 4
                    im = Image.new('RGB', (int(U.width*k)+1, int(U.height*k)+1), 'white')
                    for g in grp:
                        r = fitz.Rect(g['bbox']); part = pil(g['xref']).resize((max(1,int(r.width*k)), max(1,int(r.height*k))))
                        im.paste(part, (int((r.x0-U.x0)*k), int((r.y0-U.y0)*k)))
                fn = f'p{pn+1}_' + '_'.join(map(str, key)) + '.png'
                im.save(f'{OUT}/img/{fn}')
                seen_img[key] = fn
            q['img'] = seen_img[key]

for i, q in enumerate(questions):
    q['id'] = i + 1
    q['q'] = clean(q['q'])
    for o in q['opts']: o['t'] = clean(o['t'])
    n = sum(o['ok'] for o in q['opts'])
    if q['order'] is None and (len(q['opts']) != 3 or n != 1):
        anomalies.append((q['id'], q['page'], len(q['opts']), n, q['q'][:60]))
    del q['y0'], q['y1']

json.dump(questions, open(f'{OUT}/questions_raw.json', 'w'), ensure_ascii=False, indent=1)
print('questions', len(questions), 'images', len(seen_img), 'order', sum(1 for q in questions if q['order']))
for a in anomalies: print('ANOM', a)
