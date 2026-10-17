"""Builds the offline PWA (pwa/) from the artifact page vozacki.html."""
import re, json, hashlib, shutil, os
W = '/home/claude/w'
OUT = f'{W}/pwa'
h = open(f'{W}/vozacki.html').read()
css = open(f'{W}/twbuild/out.css').read()

# swap the Tailwind play-CDN + runtime config for precompiled CSS (works offline)
h = re.sub(r'<script src="https://cdn\.tailwindcss\.com/[^"]+"></script>\s*<script>\s*tailwind\.config.*?</script>',
           '<style>' + css + '</style>', h, count=1, flags=re.S)
assert 'cdn.tailwindcss.com' not in h

title = re.search(r'<title>(.*?)</title>', h).group(1)
h = re.sub(r'<title>.*?</title>\s*', '', h, count=1)
h = h.replace('<meta name="claude:viewport-fit-sides" content="cover">', '')

head = f'''<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{title}</title>
<meta name="theme-color" content="#1f5fae">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Vozački">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<link rel="apple-touch-icon" href="icon-180.png">
<link rel="icon" href="icon-192.png">
<link rel="manifest" href="manifest.webmanifest">
<style>:root{{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}body{{margin:0;font:14px system-ui}}img{{max-width:100%}}[hidden]{{display:none!important}}</style>
</head><body>'''
tail = '''<script>
if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(() => {});
</script></body></html>'''
html = head + h + tail
open(f'{OUT}/index.html', 'w').write(html)

ver = hashlib.sha1(html.encode()).hexdigest()[:10]
manifest = {"name": "Vozački test — тренажёр B", "short_name": "Vozački", "start_url": "./", "scope": "./",
            "display": "standalone", "background_color": "#eef1f5", "theme_color": "#1f5fae", "lang": "ru",
            "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
                      {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"},
                      {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}]}
json.dump(manifest, open(f'{OUT}/manifest.webmanifest', 'w'), ensure_ascii=False, indent=1)

sw = f'''const CACHE = 'vozacki-{ver}';
const CORE = ['./', 'index.html', 'manifest.webmanifest', 'icon-180.png', 'icon-192.png', 'icon-512.png'];
self.addEventListener('install', e => {{ e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE)).then(() => self.skipWaiting())); }});
self.addEventListener('activate', e => {{ e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); }});
self.addEventListener('fetch', e => {{
  if (e.request.method !== 'GET') return;
  // cache-first: app shell and Google Fonts; refresh in background when online
  e.respondWith(caches.open(CACHE).then(async c => {{
    const hit = await c.match(e.request, {{ ignoreSearch: true }});
    const net = fetch(e.request).then(r => {{ if (r && (r.ok || r.type === 'opaque')) c.put(e.request, r.clone()); return r; }}).catch(() => hit);
    return hit || net;
  }}));
}});
'''
open(f'{OUT}/sw.js', 'w').write(sw)
print('pwa built', round(len(html) / 1e6, 2), 'MB', 'cache', ver)
