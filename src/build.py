"""Build index.html (the published page) from src/page.html + src/data/guests.json + src/config.json.

Usage:  python3 src/build.py            → writes <repo>/index.html
        python3 src/build.py --preview p.html   also writes the page body (no document skeleton, demo form)
Paths are resolved from this file's location, so it can be run from any directory.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

page = open(os.path.join(HERE, "page.html"), encoding="utf-8").read()
guests = json.load(open(os.path.join(HERE, "data", "guests.json"), encoding="utf-8"))
compact = json.dumps(guests, ensure_ascii=False, separators=(",", ":"))
cfg_path = os.path.join(HERE, "config.json")
cfg = json.load(open(cfg_path, encoding="utf-8")) if os.path.exists(cfg_path) else {}


def apply(src, live):
    out = src.replace("__GUESTS__", compact)
    if live and cfg.get("formId"):
        out = out.replace('formId: "",', f'formId: "{cfg["formId"]}",', 1)
    return out


body = apply(page, live=True)
head_end = body.index("</style>") + len("</style>")
head, rest = body[:head_end], body[head_end:]
og = cfg.get("siteUrl", "https://moustafaabiad.github.io").rstrip("/")
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
out_path = os.path.join(ROOT, "index.html")
open(out_path, "w", encoding="utf-8").write(doc)
if "--preview" in sys.argv:
    p = sys.argv[sys.argv.index("--preview") + 1]
    open(p, "w", encoding="utf-8").write(apply(page, live=False))
print(f"index.html: {len(doc)} bytes, {len(guests)} invitations, form: {'live' if cfg.get('formId') else 'demo'}")
