"""Build index.html (the invitation) from src/page.html + src/data/guests.json + src/config.json.
Run from anywhere:  python3 src/build.py
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
page = open(os.path.join(HERE, 'page.html'), encoding='utf-8').read()
guests = json.load(open(os.path.join(HERE, 'data', 'guests.json'), encoding='utf-8'))
cfg = json.load(open(os.path.join(HERE, 'config.json'), encoding='utf-8'))
body = page.replace('__GUESTS__', json.dumps(guests, ensure_ascii=False, separators=(',', ':')))
if cfg.get('formId'):
    body = body.replace('formId: "",', f'formId: "{cfg["formId"]}",', 1)
head_end = body.index('</style>') + len('</style>')
head, rest = body[:head_end], body[head_end:]
og = cfg.get('siteUrl', 'https://moustafaabiad.github.io').rstrip('/')
doc = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
       '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
       '<meta name="robots" content="noindex,nofollow">\n'
       '<meta property="og:title" content="Moustafa &amp; Dana">\n'
       '<meta property="og:description" content="Tuesday 29 December 2026 · Kasr Fakhreddine, Saifi, Beirut">\n'
       f'<meta property="og:image" content="{og}/assets/og.jpg">\n'
       '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">\n'
       '<meta name="theme-color" content="#E0CDA8">\n'
       '<link rel="icon" href="assets/favicon.png" type="image/png">\n'
       + head.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', '') +
       '\n</head>\n<body>\n' + rest + '\n</body>\n</html>\n')
open(os.path.join(ROOT, 'index.html'), 'w', encoding='utf-8').write(doc)
print('index.html written:', len(doc), 'bytes; guests:', len(guests), '; form:', 'live' if cfg.get('formId') else 'demo')
