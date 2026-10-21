"""Guest list → src/data/guests.json (the copy the invitation page embeds).

Source: the Google Sheet "Invitation - guest list (live)", tab "Guests", given as ONE of
  • a Drive export saved by the assistant harness: a JSON file {content: <base64>, id, mimeType, title}
    produced by the Google Drive tool download_file_content (exportMimeType "application/zip" or "text/csv")
  • a .zip "Web page" export of the spreadsheet (contains Guests.html)
  • a .html page of the Guests tab, a .csv export of the tab, or a markdown table (.md/.txt)
With no argument the newest Drive export found in the harness tool-results folders is used.

Usage:  python3 sync_guests.py [<file>] [--dry-run] [--force] [--out <guests.json>]
Exit:   0 = guests.json changed (written unless --dry-run)   3 = no changes   1 = error / refused (nothing written)

Sheet columns (matched by header name, order free):
  id | Guest | First name (EN) | First name (AR) | Gender | Plus one | Plus-one first name (EN) |
  Plus-one first name (AR) | Plus-one full name | Group | Side          (one row = one invitation: guest + optional +1)
"""
import base64, csv, glob, io, json, os, re, sys, zipfile
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DEFAULT = os.path.join(HERE, "data", "guests.json")
SHEET_ID = "1ruCmz4hsgPHLVRd02krjs9Y7AHy-BTTqxnCxp9N0euQ"          # "Invitation - guest list (live)"
TOOL_RESULTS = "/root/.claude/projects/**/tool-results/mcp-Google_Drive-download_file_content-*.txt"
REQUIRED = ("id", "guest", "first name (en)")
SHRINK_GUARD = 0.7      # refuse (without --force) if the list drops below 70 % of the previous count


# ----------------------------------------------------------------------------- input readers
class _Table(HTMLParser):
    """Rows of the first <table> in a Google Sheets HTML export (row-header <th> cells skipped)."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self._row, self._cell, self._in_td, self._skip = [], None, [], False, 0
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "tr":
            self._row = []
        elif tag == "td" and self._row is not None:
            self._in_td, self._cell, self._span = True, [], int(a.get("colspan") or 1)
        elif tag == "br" and self._in_td:
            self._cell.append("\n")
        elif tag in ("style", "script", "svg"):
            self._skip += 1
    def handle_endtag(self, tag):
        if tag == "td" and self._in_td:
            txt = "".join(self._cell).strip()
            self._row.extend([txt] + [""] * (self._span - 1))
            self._in_td = False
        elif tag == "tr" and self._row is not None:
            if any(c for c in self._row):
                self.rows.append(self._row)
            self._row = None
        elif tag in ("style", "script", "svg") and self._skip:
            self._skip -= 1
    def handle_data(self, data):
        if self._in_td and not self._skip:
            self._cell.append(data)


def rows_from_html(text):
    p = _Table(); p.feed(text); return p.rows


def rows_from_csv(text):
    return [r for r in csv.reader(io.StringIO(text))]


def rows_from_markdown(text):
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or set(line.replace("|", "").strip()) <= set(":- "):
            continue
        rows.append([c.strip() for c in line.strip("|").split("|")])
    return rows


def rows_from_zip(data):
    z = zipfile.ZipFile(io.BytesIO(data))
    pages = [n for n in z.namelist() if n.lower().endswith(".html")]
    for name in sorted(pages, key=lambda n: (not n.lower().startswith("guests"), n)):
        rows = rows_from_html(z.read(name).decode("utf-8"))
        if rows and header_index(rows) is not None:
            return rows, name
    raise SystemExit("error: no sheet with an 'id | Guest | …' header in the export (" + ", ".join(pages) + ")")


def rows_from_bytes(data, label):
    if data[:2] == b"PK":
        rows, name = rows_from_zip(data); return rows, f"{label} › {name}"
    text = data.decode("utf-8-sig")
    if "<table" in text[:200000] and "<td" in text:
        return rows_from_html(text), label
    if text.lstrip().startswith("|"):
        return rows_from_markdown(text), label
    return rows_from_csv(text), label


def load_rows(path):
    """→ (rows, description).  Handles the harness-saved JSON wrapper around a Drive export."""
    if path is None:
        found = sorted(glob.glob(TOOL_RESULTS, recursive=True), key=os.path.getmtime)
        if not found:
            raise SystemExit("error: no Drive export found; pass the exported file as argument")
        path = found[-1]
    raw = open(path, "rb").read()
    if raw[:1] == b"{":
        try:
            wrapper = json.loads(raw.decode("utf-8"))
        except Exception:
            wrapper = None
        if isinstance(wrapper, dict) and "content" in wrapper:
            if wrapper.get("id") and wrapper["id"] != SHEET_ID:
                raise SystemExit(f"error: export is of another file ({wrapper.get('title')!r}, id {wrapper['id']}); "
                                 f"expected the guest list sheet {SHEET_ID}")
            data = base64.b64decode(wrapper["content"])
            return rows_from_bytes(data, f"Drive export of {wrapper.get('title') or 'sheet'} ({wrapper.get('mimeType')})")
    return rows_from_bytes(raw, os.path.basename(path))


# ----------------------------------------------------------------------------- guest model
def header_index(rows):
    for i, r in enumerate(rows):
        if r and r[0].strip().lower() == "id" and len(r) > 2:
            return i
    return None


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def parse_guests(rows):
    hi = header_index(rows)
    if hi is None:
        raise SystemExit("error: header row starting with 'id' not found")
    hdr = [h.strip().lower() for h in rows[hi]]
    missing = [c for c in REQUIRED if c not in hdr]
    if missing:
        raise SystemExit("error: missing column(s) " + ", ".join(missing))
    col = {h: i for i, h in enumerate(hdr) if h}

    def get(r, name):
        i = col.get(name)
        return r[i].strip() if i is not None and i < len(r) else ""

    guests, seen = [], {}
    for r in rows[hi + 1:]:
        name = get(r, "guest")
        if not name:
            continue
        if r[0].strip().lower() == "id":          # a second header (another tab) – stop here
            break
        gid = get(r, "id")
        gid = slug(name) if (not gid or gid.startswith("=")) else gid
        if gid in seen:                           # duplicate names get -2, -3 …
            seen[gid] += 1; gid = f"{gid}-{seen[gid]}"
        else:
            seen[gid] = 1
        plus = get(r, "plus one").lower() in ("yes", "y", "true", "1")
        people = [{"first": get(r, "first name (en)") or name.split(" ")[0],
                   "firstAr": get(r, "first name (ar)"),
                   "gender": (get(r, "gender") or "M").upper()[:1]}]
        pf, pfa, pfull = get(r, "plus-one first name (en)"), get(r, "plus-one first name (ar)"), get(r, "plus-one full name")
        open_seats, invite = 0, name
        if plus:
            if pf or pfa:
                people.append({"first": pf or pfa, "firstAr": pfa, "gender": ""})
                sur = name.split(" ", 1)[1] if " " in name else ""
                psur = pfull.split(" ", 1)[1] if " " in pfull else ""
                invite = f"{people[0]['first']} & {pf} {sur}".strip() if (sur and psur == sur) else f"{name} & {pfull or pf}"
            else:
                open_seats = 1
        guests.append({"id": gid, "invite": invite, "group": get(r, "group"), "people": people, "open": open_seats})
    return guests


def stats(guests):
    seats = sum(len(g["people"]) + g["open"] for g in guests)
    plus = sum(1 for g in guests if len(g["people"]) + g["open"] > 1)
    return f"{len(guests)} invitations, {seats} seats, {plus} with +1"


def describe_change(old, new):
    fmt = lambda p: p["first"] + (f" ({p['firstAr']})" if p.get("firstAr") else "")
    op, np_, out = old["people"], new["people"], []
    if len(np_) > len(op):
        out.append("+1 named: " + ", ".join(fmt(p) for p in np_[len(op):]))
    elif len(np_) < len(op):
        out.append("+1 removed: " + ", ".join(fmt(p) for p in op[len(np_):]))
    else:
        for a, b in zip(op, np_):
            if a != b:
                out.append(f"{fmt(a)} → {fmt(b)}" if fmt(a) != fmt(b) else f"gender of {fmt(a)} changed")
    if old["open"] != new["open"] and len(np_) == len(op):
        out.append("unnamed +1 " + ("added" if new["open"] else "removed"))
    if old["invite"] != new["invite"]:
        out.append(f"“{old['invite']}” → “{new['invite']}”")
    if old["group"] != new["group"]:
        out.append(f"group {old['group'] or '—'} → {new['group'] or '—'}")
    return "; ".join(out) or "updated"


def diff(old_list, new_list):
    old, new = {g["id"]: g for g in old_list}, {g["id"]: g for g in new_list}
    added = [new[k] for k in new if k not in old]
    removed = [old[k] for k in old if k not in new]
    changed = [(old[k], new[k]) for k in new if k in old and old[k] != new[k]]
    lines = [f"  + {g['invite']}  ({g['id']})" for g in added]
    lines += [f"  − {g['invite']}  ({g['id']})" for g in removed]
    lines += [f"  ~ {n['invite']}  ({n['id']}): {describe_change(o, n)}" for o, n in changed]
    return added, removed, changed, lines


# ----------------------------------------------------------------------------- main
def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    dry, force = "--dry-run" in argv, "--force" in argv
    out = argv[argv.index("--out") + 1] if "--out" in argv else OUT_DEFAULT
    if "--out" in argv:
        args = [a for a in args if a != out]
    rows, label = load_rows(args[0] if args else None)
    guests = parse_guests(rows)
    if not guests:
        raise SystemExit("error: the export contains no guests – refusing to publish an empty list")
    previous = json.load(open(out, encoding="utf-8")) if os.path.exists(out) else []
    print(f"source: {label}")
    print(f"guest list: {stats(guests)}" + (f" (was {stats(previous)})" if previous else ""))
    if previous and len(guests) < SHRINK_GUARD * len(previous) and not force:
        raise SystemExit(f"refused: the list shrank from {len(previous)} to {len(guests)} invitations; "
                         "check the sheet, then re-run with --force if this is intended")
    added, removed, changed, lines = diff(previous, guests)
    if previous and not (added or removed or changed):
        print("no changes"); return 3
    print(f"changes: {len(added)} added, {len(removed)} removed, {len(changed)} changed")
    print("\n".join(lines))
    if dry:
        print("dry run – nothing written"); return 0
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(guests, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"written: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
